"""In-band line editing for the SSH push session (issue #303 P3-1).

Two layers:

- **Unit** — drive ``_LineEditor`` / ``_parse_escape`` directly (capturing the
  echo bytes) to pin the editing primitives: raw echo at the line end (the
  byte-parity-preserving fast path), backspace, mid-line insert, cursor moves,
  history, and the escape-sequence classifier.
- **Integration** — a raw paramiko channel against a live SSH host: an interactive
  client that backspaces a typo, recalls history, and Tab-completes must end up
  dispatching the *corrected* command, while editing keystrokes never corrupt the
  dispatched line.

The scraper-facing wire (whole-line sends) is pinned separately by
``test_ssh_byte_parity.py``; editing only fires on interactive keys a scraper never
sends, so those goldens are unaffected (and telnet keeps editing off entirely).
"""

import time

import pytest

from simnos.plugins.servers.async_session import _complete, _LineEditor, _parse_escape
from simnos.plugins.servers.ssh_server_asyncssh import AsyncSshServer
from simnos.plugins.servers.telnet_server import TelnetServer
from tests.plugins.test_async_session import _FakeShell, _FakeTransport
from tests.plugins.test_ssh_byte_parity import _open_shell_channel, _running_host


# ---------------------------------------------------------------- unit: _parse_escape
@pytest.mark.parametrize(
    ("seq", "expected"),
    [
        (b"\x1b[A", "up"),
        (b"\x1b[B", "down"),
        (b"\x1b[C", "right"),
        (b"\x1b[D", "left"),
        (b"\x1b[H", "home"),
        (b"\x1b[F", "end"),
        (b"\x1b[1~", "home"),
        (b"\x1b[4~", "end"),
        (b"\x1b[3~", "delete"),
        (b"\x1bOA", "up"),  # SS3 (application cursor mode)
        (b"\x1bOD", "left"),
    ],
)
def test_parse_escape_known_sequences(seq, expected):
    assert _parse_escape(seq) == expected


@pytest.mark.parametrize("seq", [b"\x1b", b"\x1b[", b"\x1b[1", b"\x1b[3"])
def test_parse_escape_incomplete(seq):
    assert _parse_escape(seq) == "incomplete"


@pytest.mark.parametrize("seq", [b"\x1b[Z", b"\x1bX", b"\x1b[2~", b"\x1ba"])
def test_parse_escape_unknown_is_discarded(seq):
    """A complete-but-unhandled escape is discarded (swallowed, never echoed)."""
    assert _parse_escape(seq) == "discard"


# ---------------------------------------------------------------- unit: _LineEditor
def _editor():
    sent: list[bytes] = []
    return _LineEditor(sent.append), sent


def _feed(editor, text: bytes):
    for i in range(len(text)):
        editor.insert(text[i : i + 1])


def test_insert_at_end_echoes_raw_byte():
    """The fast path (cursor at end) echoes the raw byte — the byte-parity contract."""
    editor, sent = _editor()
    _feed(editor, b"show")
    assert b"".join(sent) == b"show"  # one raw echo per byte, nothing extra
    assert editor.line_text == "show"
    assert editor.take_line() == b"show"


def test_backspace_deletes_last_char():
    editor, sent = _editor()
    _feed(editor, b"shox")
    sent.clear()
    editor.backspace()  # delete the typo 'x'
    _feed(editor, b"w")
    assert editor.take_line() == b"show"
    # backspace redraw moves the cursor back, clears the freed cell
    assert b"\x08" in sent[0]


def test_delete_key_removes_char_under_cursor():
    editor, _ = _editor()
    _feed(editor, b"sshow")
    editor.cursor_home()
    editor.delete()  # remove the leading duplicate 's'
    assert editor.take_line() == b"show"


def test_cursor_home_and_end():
    editor, sent = _editor()
    _feed(editor, b"abc")
    editor.cursor_home()
    assert sent[-1] == b"\b" * 3
    editor.cursor_end()
    assert sent[-1] == b"abc"


def test_cursor_right_echoes_char_under_cursor():
    editor, sent = _editor()
    _feed(editor, b"ab")
    editor.cursor_home()
    sent.clear()
    editor.cursor_right()  # re-echo 'a' to advance the cursor
    assert b"".join(sent) == b"a"


def test_midline_insert_redraws_tail():
    """Inserting mid-line echoes the char + the shifted tail, then steps back over it."""
    editor, sent = _editor()
    _feed(editor, b"shw")
    editor.cursor_left()  # cursor between 'sh' and 'w'
    sent.clear()
    editor.insert(b"o")
    assert b"".join(sent) == b"ow\b"  # echo "o"+tail "w", then \b back over "w"
    assert editor.line_text == "show"


def test_delete_redraws_shifted_tail():
    editor, sent = _editor()
    _feed(editor, b"sshow")
    editor.cursor_home()
    sent.clear()
    editor.delete()  # remove the leading duplicate 's'
    assert b"".join(sent) == b"show \b\b\b\b\b"  # rewrite tail + clear cell, cursor back
    assert editor.line_text == "show"


# ---------------------------------------------------------------- unit: _complete (Tab)
class _CompShell(_FakeShell):
    """A _FakeShell (conforms to PushShell) with a configurable completion source."""

    def __init__(self, commands):
        self._commands = commands

    def completion_candidates(self, prefix):
        return sorted(c for c in self._commands if c.startswith(prefix))


def test_complete_single_candidate_completes_line():
    tr = _FakeTransport([])
    editor = _LineEditor(tr.send)
    _feed(editor, b"show ve")
    _complete(editor, _CompShell(["show version", "show vlan"]), tr)  # only "show version" matches
    assert editor.take_line() == b"show version "  # completed + trailing space


def test_complete_multiple_candidates_lists_then_redraws():
    tr = _FakeTransport([])
    editor = _LineEditor(tr.send)
    _feed(editor, b"show v")
    tr.out.clear()
    _complete(editor, _CompShell(["show version", "show vlan"]), tr)
    # candidates on a fresh line (sorted: "version" < "vlan"), then prompt + line redrawn
    assert bytes(tr.out) == b"\r\nshow version  show vlan\r\ndevice>show v"
    assert editor.line_text == "show v"  # the line itself is unchanged


def test_complete_no_match_rings_bell():
    tr = _FakeTransport([])
    editor = _LineEditor(tr.send)
    _feed(editor, b"xyz")
    tr.out.clear()
    _complete(editor, _CompShell(["show version"]), tr)
    assert bytes(tr.out) == b"\x07"  # bell, line untouched


def test_history_recall_and_restore():
    editor, _ = _editor()
    _feed(editor, b"show vlan")
    assert editor.take_line() == b"show vlan"
    _feed(editor, b"ena")  # a fresh, in-progress line
    editor.history_prev()  # recall "show vlan"
    assert editor.line_text == "show vlan"
    editor.history_next()  # past newest -> restore the stashed "ena"
    assert editor.line_text == "ena"


def test_history_dedups_consecutive_and_skips_blank():
    editor, _ = _editor()
    _feed(editor, b"show vlan")
    editor.take_line()
    _feed(editor, b"show vlan")
    editor.take_line()  # duplicate -> not re-appended
    editor.take_line()  # blank -> not appended
    editor.history_prev()
    assert editor.line_text == "show vlan"
    editor.history_prev()  # only one entry -> stays
    assert editor.line_text == "show vlan"


# ---------------------------------------------------------------- gating pin
def test_editing_is_ssh_only():
    """Line editing is enabled for SSH and disabled for Telnet (#303 P3-1)."""
    assert AsyncSshServer._editing is True
    assert TelnetServer._editing is False


# ---------------------------------------------------------------- integration (paramiko)
def _drain(channel, wait=0.5) -> bytes:
    channel.settimeout(wait)
    buf = bytearray()
    try:
        while True:
            chunk = channel.recv(4096)
            if not chunk:
                break
            buf.extend(chunk)
    except TimeoutError:
        pass
    return bytes(buf)


@pytest.fixture
def cisco_ios_channel():
    with _running_host("cisco_ios") as port:
        transport, channel = _open_shell_channel(port)
        _drain(channel)  # intro + first prompt
        try:
            yield channel
        finally:
            channel.close()
            transport.close()


def test_editing_backspace_corrects_typo(cisco_ios_channel):
    """A backspaced typo dispatches the corrected command."""
    cisco_ios_channel.sendall(b"shox")
    time.sleep(0.1)
    cisco_ios_channel.sendall(b"\x7f")  # backspace deletes 'x'
    cisco_ios_channel.sendall(b"w vlan\r")
    assert b"VLAN Name" in _drain(cisco_ios_channel)


def test_editing_history_recall(cisco_ios_channel):
    """Up-arrow recalls the previous command, which re-dispatches correctly."""
    cisco_ios_channel.sendall(b"show vlan\r")
    assert b"VLAN Name" in _drain(cisco_ios_channel)
    cisco_ios_channel.sendall(b"\x1b[A")  # up: recall "show vlan"
    assert b"show vlan" in _drain(cisco_ios_channel)
    cisco_ios_channel.sendall(b"\r")
    assert b"VLAN Name" in _drain(cisco_ios_channel)


def test_editing_tab_single_completion(cisco_ios_channel):
    """Tab on a unique prefix completes the command, which then dispatches."""
    cisco_ios_channel.sendall(b"show ip interface b\t")
    completed = _drain(cisco_ios_channel)
    assert b"show ip interface brief" in completed
    cisco_ios_channel.sendall(b"\r")
    assert b"Interface" in _drain(cisco_ios_channel)


def test_editing_unknown_escape_does_not_corrupt_dispatch(cisco_ios_channel):
    """An unhandled escape sequence is swallowed, not injected into the line."""
    cisco_ios_channel.sendall(b"show vlan")
    cisco_ios_channel.sendall(b"\x1b[Z")  # unknown escape (shift-Tab) — must be dropped
    cisco_ios_channel.sendall(b"\r")
    assert b"VLAN Name" in _drain(cisco_ios_channel)  # dispatched "show vlan", not a corrupted line
