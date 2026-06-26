"""Async push-dispatch session driver (#297 Stage 2 / 3, §3 / §3a).

Drives one client session over an event-driven transport (asyncssh process /
telnetlib3 stream) using the wire-assembly helpers (``_render_intro`` /
``_render_response``), so the byte stream is identical across the SSH and Telnet
transports — pinned by the byte-parity goldens in
``tests/plugins/test_ssh_byte_parity.py`` /
``tests/plugins/test_telnet_byte_parity.py``.

The spike (#296) proved that bridging a *blocking* shell loop per session is the
100-host failure source, so here the read loop is event-driven on the event-loop
thread and **only the blocking ``shell.dispatch``** is off-loaded to the bounded
executor (§2a). There is no per-session thread.

Two collaborators are injected so the driver stays transport- and
executor-agnostic (and unit-testable with fakes):

- ``transport``: an :class:`AsyncPushTransport` wrapping the real async I/O.
- ``dispatch``: an async callable that runs ``shell.dispatch(line)`` on the
  bounded executor and returns the :class:`DispatchResult`.
"""

from collections import deque
from collections.abc import Awaitable, Callable
import logging
from typing import TYPE_CHECKING, Protocol

from simnos.plugins.servers.tap_bridge import _render_intro, _render_response

if TYPE_CHECKING:
    from simnos.plugins.servers.tap_bridge import PushShell
    from simnos.plugins.shell.cmd_shell import DispatchResult

log = logging.getLogger(__name__)

# asyncssh stdin reads arrive in chunks; one read may carry several bytes/lines.
# The §3a byte state machine iterates the chunk byte-by-byte so per-character echo
# stays byte-stable regardless of how the transport segments the stream.
_READ_CHUNK = 4096


class AsyncPushTransport(Protocol):
    """Minimal async transport surface the session driver needs (§3a, claude#3).

    The ``recv`` is event-driven (an async read, not a blocking pull). ``send``
    buffers a write; ``drain`` applies flow-control backpressure at response
    boundaries so a slow client cannot make the server buffer without bound under
    the 100-host load.
    """

    #: Exceptions that mean "I/O failed / peer gone" for this transport.
    io_errors: tuple[type[BaseException], ...]

    #: RFC 854 CR NUL quirk switch (False for SSH, True for Telnet): True makes a
    #: NUL clear the pending CR-LF skip (CR NUL is a complete Telnet sequence).
    nul_resets_skip_lf: bool

    #: Short name for log messages ("ssh").
    name: str

    async def recv(self, n: int) -> bytes:
        """Read up to *n* bytes. Returns ``b""`` on EOF (peer closed)."""
        ...

    def send(self, data: bytes) -> None:
        """Queue *data* for the client (flushed by the transport / ``drain``)."""
        ...

    async def drain(self) -> None:
        """Wait until queued writes have drained below the transport's limit."""
        ...


# --------------------------------------------------------------------- line editor
# Interactive line editing for the SSH push session (#303 P3-1). This rides ON TOP
# of the binary byte machine in run_async_push_session and only fires on keystrokes
# a scraper never sends — cursor moves, history, backspace, Tab. Regular characters
# (appended at the line end) and the CR/LF/NUL terminators are echoed/handled exactly
# as before, so the byte-parity goldens (which send only whole lines) are unchanged.
# Editing is gated by the `editing` flag (SSH=True, Telnet=False).
#
# Two simplifications, both interactive-only (a scraper never edits, so the wire
# contract is unaffected either way):
#   - Terminal-width wrapping is NOT modelled — the redraw assumes the line fits on
#     one row, so a line longer than the terminal miscounts its \b-based redraw
#     (horizontal-scroll/wrap is a P3-4 follow-up).
#   - The cursor moves by BYTE, not grapheme — ASCII-exact, multibyte best-effort
#     (editing a multibyte character may split it). Network CLIs are ASCII.

#: CSI/SS3 final sequence (after the ``\x1b[`` / ``\x1bO`` prefix) → editor action.
_CSI_ACTIONS = {
    b"A": "up",
    b"B": "down",
    b"C": "right",
    b"D": "left",
    b"H": "home",
    b"F": "end",
    b"1~": "home",
    b"4~": "end",
    b"3~": "delete",
}
_MAX_ESC_LEN = 8  # give up on an unterminated escape past this many bytes
_HISTORY_MAX = 1000  # per-session command-history cap (bounds long-session memory)


def _parse_escape(seq: bytes) -> str:
    """Classify an accumulating escape sequence (starts with ``\\x1b``).

    Returns ``"incomplete"`` while more bytes are needed, a known action name
    (``"left"`` / ``"up"`` / ...), or ``"discard"`` for a complete-but-unhandled
    sequence (swallowed, never echoed).
    """
    if len(seq) < 2:
        return "incomplete"
    if seq[1:2] not in (b"[", b"O"):
        return "discard"  # ESC + non-CSI/SS3 — not an editing key
    if len(seq) < 3:
        return "incomplete"
    if 0x40 <= seq[-1] <= 0x7E:  # CSI/SS3 final byte → sequence complete
        return _CSI_ACTIONS.get(bytes(seq[2:]), "discard")
    return "incomplete"  # still collecting parameter bytes


class _LineEditor:
    """The line being typed: buffer + cursor + history, with echo via ``send``.

    For input arriving at the line end (a scraper's whole-line send) ``insert``
    echoes the raw byte and appends — byte-identical to the pre-P3-1 machine. The
    redraw paths (mid-line insert, backspace, cursor, history, completion) only run
    for interactive keys, so the byte-parity goldens are unaffected.
    """

    def __init__(self, send: "Callable[[bytes], None]") -> None:
        self._send = send
        self._line = bytearray()
        self._pos = 0  # cursor byte offset within the line
        # Bounded so a long-lived session's history cannot grow without limit
        # (gemini/claude 1st: drops the oldest entry past _HISTORY_MAX).
        self._history: deque[bytes] = deque(maxlen=_HISTORY_MAX)
        self._hist_idx: int | None = None  # None = editing a fresh (non-history) line
        self._saved = b""  # the in-progress line stashed when browsing history

    @property
    def line_text(self) -> str:
        return self._line.decode("utf-8", errors="replace")

    def insert(self, byte: bytes) -> None:
        if self._pos == len(self._line):
            self._send(byte)  # fast path: raw echo at end (byte-parity preserved)
            self._line += byte
            self._pos += 1
            return
        # Mid-line insert (only after a cursor move): echo the tail, then step back.
        self._line[self._pos : self._pos] = byte
        self._pos += 1
        tail = bytes(self._line[self._pos - 1 :])
        self._send(tail)
        self._send(b"\b" * (len(tail) - 1))

    def backspace(self) -> None:
        if self._pos == 0:
            return
        del self._line[self._pos - 1 : self._pos]
        self._pos -= 1
        tail = bytes(self._line[self._pos :])
        self._send(b"\b" + tail + b" ")  # move left, rewrite tail, clear the freed cell
        self._send(b"\b" * (len(tail) + 1))  # cursor back to the edit point

    def delete(self) -> None:
        if self._pos >= len(self._line):
            return
        del self._line[self._pos : self._pos + 1]
        tail = bytes(self._line[self._pos :])
        self._send(tail + b" ")
        self._send(b"\b" * (len(tail) + 1))

    def cursor_left(self) -> None:
        if self._pos > 0:
            self._pos -= 1
            self._send(b"\b")

    def cursor_right(self) -> None:
        if self._pos < len(self._line):
            self._send(bytes(self._line[self._pos : self._pos + 1]))
            self._pos += 1

    def cursor_home(self) -> None:
        if self._pos:
            self._send(b"\b" * self._pos)
            self._pos = 0

    def cursor_end(self) -> None:
        if self._pos < len(self._line):
            self._send(bytes(self._line[self._pos :]))
            self._pos = len(self._line)

    def _replace_line(self, new: bytes) -> None:
        """Erase the displayed line and draw ``new`` (cursor at end) in one write.

        Cursor to start (``\\b`` * pos) -> overwrite old glyphs with spaces -> back
        to start -> draw ``new``, coalesced into a single ``send`` so a chunking
        transport cannot split the redraw into micro-packets (gemini 2nd#4).
        """
        old_len = len(self._line)
        self._send(b"\b" * self._pos + b" " * old_len + b"\b" * old_len + new)
        self._line = bytearray(new)
        self._pos = len(self._line)

    def set_line(self, new: bytes) -> None:
        """Replace the line (Tab completion)."""
        self._replace_line(new)

    def history_prev(self) -> None:
        if not self._history:
            return
        if self._hist_idx is None:
            self._hist_idx = len(self._history)
            self._saved = bytes(self._line)  # stash the fresh line to restore later
        if self._hist_idx > 0:
            self._hist_idx -= 1
            self._replace_line(self._history[self._hist_idx])

    def history_next(self) -> None:
        if self._hist_idx is None:
            return
        if self._hist_idx < len(self._history) - 1:
            self._hist_idx += 1
            self._replace_line(self._history[self._hist_idx])
        else:  # past the newest entry → restore the stashed in-progress line
            self._hist_idx = None
            self._replace_line(self._saved)

    def redraw(self) -> None:
        """Re-emit the current line (cursor preserved) after foreign output."""
        self._send(bytes(self._line))
        back = len(self._line) - self._pos
        if back:
            self._send(b"\b" * back)

    def apply_action(self, action: str) -> None:
        """Dispatch a parsed escape action to the matching edit operation."""
        if action == "left":
            self.cursor_left()
        elif action == "right":
            self.cursor_right()
        elif action == "up":
            self.history_prev()
        elif action == "down":
            self.history_next()
        elif action == "home":
            self.cursor_home()
        elif action == "end":
            self.cursor_end()
        elif action == "delete":
            self.delete()
        # "discard" / unknown: swallow (no echo)

    def take_line(self) -> bytes:
        """Return the finished line and reset; non-blank lines enter history."""
        line = bytes(self._line)
        if line.strip() and (not self._history or self._history[-1] != line):
            self._history.append(line)
        self._line = bytearray()
        self._pos = 0
        self._hist_idx = None
        return line


def _complete(editor: _LineEditor, shell: "PushShell", transport: AsyncPushTransport) -> None:
    """Tab completion: exact-prefix over the current-mode command names (#303 P3-1).

    One candidate completes the line (+ a trailing space); several are listed on a
    fresh line and the prompt + line are redrawn; none rings the bell. None of this
    is byte-parity-pinned: the contract rests on a scraper never sending Tab (nor
    BS / ESC). The goldens contain none; a platform that one day embeds a literal
    tab in a command payload would be intercepted here and diverge — out of P3-1
    scope (claude 1st#5). Completion uses the whole line (cursor-position-aware
    completion is P3-2, gemini/claude 1st).
    """
    candidates = shell.completion_candidates(editor.line_text)
    if len(candidates) == 1:
        editor.set_line(candidates[0].encode("utf-8") + b" ")
    elif len(candidates) > 1:
        listing = "  ".join(candidates)
        transport.send(b"\r\n" + listing.encode("utf-8") + b"\r\n" + shell.prompt.encode("utf-8"))
        editor.redraw()
    else:
        transport.send(b"\x07")  # bell — no match


async def run_async_push_session(
    transport: AsyncPushTransport,
    shell: "PushShell",
    dispatch: Callable[[str], Awaitable["DispatchResult"]],
    *,
    initial_skip_lf: bool = False,
    editing: bool = False,
) -> None:
    """Drive one client session with async push dispatch (#297 Stage 2, §3a).

    The wire state machine is: regular char = immediate echo; line terminator =
    held ``\\r\\n`` echo + body + prompt in one write (the wire assembly lives in
    ``_render_intro`` / ``_render_response``). It is event-driven, not a blocking
    loop:

    - the read is ``await transport.recv(...)`` (event-driven) so the event-loop
      thread is free between bytes;
    - ``shell.dispatch`` runs via the injected ``dispatch`` coroutine (bounded
      executor), so a slow handler does not block the loop (§2a);
    - shutdown is propagated by the transport closing (``recv`` -> ``b""`` / an
      ``io_errors`` raise) rather than a polled ``is_running`` flag — the shared
      loop closes the session on stop (§1a).

    **Write-failure policy (§3a, codex/claude 1st):** there is no per-write timeout
    here. asyncssh / telnetlib3 apply backpressure through ``drain`` flow-control,
    so a slow client never produces a write timeout to retry; a real write failure
    surfaces as an ``io_errors`` raise and is treated as a disconnect for both echo
    and response.

    ``initial_skip_lf`` consumes a trailing LF/NUL left by a preceding channel
    login (auth_none).

    ``editing`` (SSH=True, Telnet=False, #303 P3-1) enables in-band line editing —
    cursor moves, history, backspace, Tab — driven by the :class:`_LineEditor`.
    These fire ONLY on interactive keys a scraper never sends; regular characters
    and the CR/LF/NUL terminators are echoed/handled byte-for-byte as before, so the
    byte-parity goldens hold whether editing is on or off.
    """
    try:
        transport.send(_render_intro(shell))
        await transport.drain()
    except transport.io_errors:
        log.debug("async_session [%s] intro write closed", transport.name)
        return

    editor = _LineEditor(transport.send)
    esc = bytearray()  # accumulates an in-flight escape sequence (editing only)
    skip_lf = initial_skip_lf
    while True:
        try:
            data = await transport.recv(_READ_CHUNK)
        except transport.io_errors:
            log.debug("async_session [%s] read closed", transport.name)
            return
        if not data:
            return  # EOF / peer gone

        for i in range(len(data)):
            byte = data[i : i + 1]
            try:
                # Interactive escape sequence (cursor / history / delete). A scraper
                # sends no ESC, so editing=False (and a non-editing session) never
                # enters here and the byte falls through to the unchanged machine.
                if editing and byte == b"\x1b":
                    esc = bytearray(b"\x1b")  # (re)start; abandon any partial sequence
                    continue
                if esc:
                    if len(esc) == 1 and byte not in (b"[", b"O"):
                        # The byte right after ESC must be '[' or 'O' to begin a
                        # CSI/SS3 sequence. Anything else means the ESC was lone (a
                        # stray ESC, or an unhandled meta-key like Alt+key): drop the
                        # ESC and reprocess this byte on the normal path below, so a
                        # lone ESC neither swallows the following character (claude
                        # 2nd#4) nor the following Enter/Backspace.
                        esc.clear()
                    elif b"\x20" <= byte <= b"\x7e":  # a CSI/SS3 continuation byte
                        esc += byte
                        action = _parse_escape(bytes(esc))
                        if action == "incomplete" and len(esc) < _MAX_ESC_LEN:
                            continue  # still collecting
                        esc.clear()
                        if action not in ("incomplete", "discard"):
                            editor.apply_action(action)
                        continue  # escape consumed (applied / discarded / maxlen-dropped)
                    else:
                        # A control byte mid-CSI cannot continue the escape: abandon
                        # the malformed sequence and reprocess this byte on the normal
                        # path below instead of swallowing it until the escape buffer
                        # fills (gemini 1st#1 / claude 1st#2).
                        esc.clear()

                # Drop NUL completely (no echo, no buffer). Telnet (RFC 854): CR NUL
                # is a complete sequence, so reset skip_lf; SSH preserves it.
                if byte == b"\x00":
                    if transport.nul_resets_skip_lf:
                        skip_lf = False
                    continue

                # Consume the LF half of a CR LF pair.
                if skip_lf:
                    skip_lf = False
                    if byte == b"\n":
                        continue

                if byte in (b"\r", b"\n"):
                    skip_lf = byte == b"\r"
                    # errors="replace" keeps malformed UTF-8 from crashing the
                    # session (gemini#2).
                    line = editor.take_line().decode("utf-8", errors="replace")
                    result = await dispatch(line)
                    transport.send(_render_response(shell, result))
                    await transport.drain()
                    if result.close:
                        return
                elif editing and byte in (b"\x08", b"\x7f"):
                    editor.backspace()
                elif editing and byte == b"\t":
                    _complete(editor, shell, transport)
                else:
                    # Regular character: immediate raw echo at the line end
                    # (interactive latency + byte-parity unchanged).
                    editor.insert(byte)
            except transport.io_errors as e:
                log.error("async_session [%s] client write error: %s", transport.name, e)
                return


async def _async_read_line(transport: AsyncPushTransport, *, echo: bool, skip_lf: bool) -> tuple[str, bool]:
    """Read one line byte-by-byte for the in-band login.

    Returns ``(line without trailing CR/LF, next_skip_lf)``; a CR sets
    ``next_skip_lf=True`` so the next read consumes the LF half of a CR LF pair.
    Reads one byte per ``recv`` (login is short and not perf-critical, so this
    avoids a leftover-buffer between the two reads). EOF returns the partial line.
    """
    buf = b""
    while True:
        byte = await transport.recv(1)
        if not byte:  # EOF
            return buf.decode("utf-8", errors="replace"), False
        if skip_lf:
            skip_lf = False
            if byte == b"\n":
                continue
            if byte == b"\x00" and transport.nul_resets_skip_lf:
                continue
        if byte == b"\r":
            if echo:
                transport.send(b"\r\n")
            return buf.decode("utf-8", errors="replace"), True
        if byte == b"\n":
            if echo:
                transport.send(b"\r\n")
            return buf.decode("utf-8", errors="replace"), False
        if echo:
            transport.send(byte)
        buf += byte


async def async_interactive_login(
    transport: AsyncPushTransport,
    username: str,
    password: str,
    *,
    user_prompt: bytes,
    pass_prompt: bytes,
) -> tuple[bool, bool]:
    """Async in-band login (username/password prompts over the data channel).

    Used for auth_none platforms (e.g. Dell PowerConnect) before the shell, and
    for the Telnet in-band login (#297 Stage 3). Returns ``(authenticated,
    skip_lf)``; ``skip_lf`` is forwarded to ``run_async_push_session`` as
    ``initial_skip_lf`` so it consumes the trailing LF/NUL left by the final CR of
    the password line.

    Each prompt is ``send``-buffered without an explicit ``drain``; the prompt
    still reaches the client because the following ``await _async_read_line``
    yields to the loop, which flushes the (small) write before the read blocks for
    input. The single ``drain`` after the closing ``\\r\\n`` provides the one
    backpressure point.
    """
    transport.send(user_prompt)
    entered_user, skip_lf = await _async_read_line(transport, echo=True, skip_lf=False)
    transport.send(pass_prompt)
    entered_pass, skip_lf = await _async_read_line(transport, echo=False, skip_lf=skip_lf)
    transport.send(b"\r\n")
    await transport.drain()
    authenticated = entered_user == username and entered_pass == password
    log.debug(
        "async_session.async_interactive_login [%s] %s for user %s",
        transport.name,
        "succeeded" if authenticated else "failed",
        entered_user,
    )
    return authenticated, skip_lf
