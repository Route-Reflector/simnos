"""Unit tests for the async push session driver (#297 Stage 2, §3a).

Pin the wire contract of ``run_async_push_session`` + ``async_interactive_login``
in isolation (fake transport + fake shell), so a regression in the byte state
machine is caught here without spinning a real asyncssh server. The byte-exact
parity with the paramiko push path is pinned separately by the byte-parity
goldens; these pin the driver's branch behaviour (echo / NUL / close / EOF /
malformed UTF-8 / login skip_lf).
"""

import asyncio

import pytest

from simnos.core.resolved_command import ResolvedChallenge, ResolvedOutput, Transition
from simnos.plugins.servers.async_session import (
    _CSI_ACTIONS,
    _LINE_MAX,
    _consume_escape,
    _consume_terminator,
    _read_challenge_line,
    _resolve_rows,
    async_interactive_login,
    run_async_push_session,
)
from simnos.plugins.shell.cmd_shell import DispatchResult, PendingChallenge


class _FakeShell:
    """PushShell stub: ``dispatch`` echoes the line, ``exit`` closes."""

    intro: str | None = "Custom SSH Shell"  # annotated to the invariant PushShell.intro type (ty 0.0.55)
    prompt = "device>"
    newline = "\r\n"
    # Paging surface (#307). Defaults keep the existing tests non-paged: a fake
    # transport reporting `page_rows() is None` means the gate is off, so the
    # driver takes the byte-identical `_render_response` path regardless of these.
    paging_disabled = False
    more_prompt = " --More-- "
    page_default_rows = 24

    def dispatch(self, line: str) -> DispatchResult:
        if line == "exit":
            return DispatchResult(body=None, prompt=self.prompt, close=True, mode="user")
        if line == "":
            return DispatchResult(body=None, prompt=self.prompt, close=False, mode="user")
        return DispatchResult(body=f"out:{line}", prompt=self.prompt, close=False, mode="user")

    def completion_candidates(self, prefix: str) -> list[str]:
        return []  # these tests drive the push path with editing off; Tab is never consulted


class _FakeTransport:
    """AsyncPushTransport over a scripted byte stream; records writes.

    ``recv(n)`` returns up to *n* bytes from one chunk at a time (respecting ``n``
    like the real ``AsyncSSHProcessTransport``), so the channel-login path that
    reads one byte at a time behaves faithfully. Chunk boundaries are preserved
    (not flattened): a test can place a CR in one chunk and its LF in the next to
    pin the driver's cross-chunk skip_lf handling (#307, phantom-Enter keystone).
    """

    io_errors: tuple[type[BaseException], ...] = (OSError,)  # match invariant AsyncPushTransport.io_errors (ty 0.0.55)
    nul_resets_skip_lf = False
    name = "ssh"

    def __init__(
        self,
        chunks: list[bytes],
        *,
        fail_on: bytes | None = None,
        rows: int | None = None,
        nul_resets_skip_lf: bool = False,
        fail_drain_on: bytes | None = None,
    ) -> None:
        # `chunks` is preserved as a list (not flattened) so a test can pin
        # cross-chunk boundaries: recv() yields one chunk at a time, so a CR in
        # one chunk and its LF in the next reach the driver across two reads
        # (#307, the phantom-Enter keystone, codex 4th#4).
        self._chunks = list(chunks)
        self.out = bytearray()
        self.drains = 0  # drain() call count — pins the echo backpressure sites (#347)
        self._fail_on = fail_on
        # page_rows() return value: None = paging off (the default, byte-identical
        # path); a positive int makes the driver page over-long bodies (#307).
        self._rows = rows
        self.nul_resets_skip_lf = nul_resets_skip_lf
        # When set, drain() raises once the given marker has been written — lets a
        # test pin that a write-side drain failure (not just send) tears the session
        # down via the main loop's io_errors handler (#307, codex 2nd#1).
        self._fail_drain_on = fail_drain_on

    async def recv(self, n: int) -> bytes:
        while self._chunks and self._chunks[0] == b"":
            self._chunks.pop(0)  # skip empty chunks (cosmetic test convenience)
        if not self._chunks:
            return b""  # EOF
        head = self._chunks[0]
        chunk, rest = head[:n], head[n:]
        self._chunks[0] = rest
        if not rest:
            self._chunks.pop(0)
        return chunk

    def send(self, data: bytes) -> None:
        if self._fail_on is not None and self._fail_on in data:
            raise OSError("simulated write failure")
        self.out += data

    async def drain(self) -> None:
        self.drains += 1
        if self._fail_drain_on is not None and self._fail_drain_on in self.out:
            raise OSError("simulated drain failure")

    def page_rows(self) -> int | None:
        return self._rows


def _drive(transport: _FakeTransport, shell: _FakeShell, **kwargs) -> bytes:
    async def _dispatch(line: str):
        return shell.dispatch(line)

    asyncio.run(run_async_push_session(transport, shell, _dispatch, **kwargs))
    return bytes(transport.out)


# ---------------------------------------------------------------- shared byte step functions (#350)
@pytest.mark.parametrize(
    ("byte", "skip_lf", "nul_resets", "expected"),
    [
        # NUL is always dropped; nul_resets (Telnet) clears a pending skip_lf, SSH preserves it.
        (b"\x00", False, False, ("drop", False)),
        (b"\x00", False, True, ("drop", False)),
        (b"\x00", True, True, ("drop", False)),  # Telnet CR NUL: clear the pending skip_lf
        (b"\x00", True, False, ("drop", True)),  # SSH: NUL preserves the pending skip_lf
        # A pending skip_lf consumes the LF half of a CR LF (nul_resets irrelevant).
        (b"\n", True, False, ("drop", False)),
        (b"\n", True, True, ("drop", False)),
        # CR / LF terminate the line; CR arms skip_lf for the next byte.
        (b"\r", False, False, ("line", True)),
        (b"\r", True, False, ("line", True)),  # CR always arms, even clearing a pending skip_lf
        (b"\n", False, False, ("line", False)),
        # Data byte -> char; a pending skip_lf is cleared (only valid 1 byte after CR).
        (b"a", False, False, ("char", False)),
        (b"a", True, False, ("char", False)),
    ],
)
def test_consume_terminator_truth_table(byte, skip_lf, nul_resets, expected):
    """Every cell of the §1 truth table — the SSoT for all four byte consumers (#350)."""
    assert _consume_terminator(byte, skip_lf, nul_resets) == expected


def test_consume_escape_seed_starts_and_restarts_collection():
    """An ESC byte seeds the buffer, and a second ESC restarts it (abandons a partial)."""
    esc = bytearray()
    assert _consume_escape(esc, b"\x1b") == "consumed"
    assert bytes(esc) == b"\x1b"
    esc += b"["  # pretend a partial CSI accumulated
    assert _consume_escape(esc, b"\x1b") == "consumed"
    assert bytes(esc) == b"\x1b"  # restarted from scratch


def test_consume_escape_no_pending_passes_byte():
    """With no escape pending a normal byte returns "pass" (process it normally)."""
    esc = bytearray()
    assert _consume_escape(esc, b"a") == "pass"
    assert bytes(esc) == b""


def test_consume_escape_lone_esc_then_non_csi_passes():
    """ESC followed by a non-CSI/SS3 byte is a lone ESC: cleared and the byte passes."""
    esc = bytearray(b"\x1b")
    assert _consume_escape(esc, b"a") == "pass"
    assert bytes(esc) == b""  # cleared so the byte reprocesses on the normal path


def test_consume_escape_completes_action_then_discards_unknown():
    """A complete CSI maps to its action; a complete-but-unknown CSI is swallowed."""
    esc = bytearray(b"\x1b[")
    assert _consume_escape(esc, b"D") == "left"  # CSI D -> cursor left
    assert bytes(esc) == b""
    esc = bytearray(b"\x1b[")
    assert _consume_escape(esc, b"Z") == "consumed"  # complete but unhandled -> discard
    assert bytes(esc) == b""


def test_consume_escape_collecting_and_maxlen_drop():
    """Mid-collection returns "consumed"; an over-long unterminated escape is dropped."""
    esc = bytearray(b"\x1b")
    assert _consume_escape(esc, b"[") == "consumed"  # still collecting
    assert bytes(esc) == b"\x1b["
    esc = bytearray(b"\x1b[" + b"1" * 5)  # 7 bytes; the 8th hits _MAX_ESC_LEN
    assert _consume_escape(esc, b"2") == "consumed"  # incomplete at maxlen -> dropped
    assert bytes(esc) == b""


def test_consume_escape_control_byte_mid_csi_passes():
    """A control byte mid-CSI cannot continue the sequence: cleared, byte passes."""
    esc = bytearray(b"\x1b[")
    assert _consume_escape(esc, b"\r") == "pass"
    assert bytes(esc) == b""  # cleared so the CR reprocesses on the normal path


def test_csi_actions_disjoint_from_reserved_verdicts():
    """Action names must stay disjoint from the control verdicts sharing the str
    namespace, or a new `_CSI_ACTIONS` entry would be misread as a verdict (§3)."""
    reserved = {"pass", "consumed", "incomplete", "discard"}
    assert reserved.isdisjoint(_CSI_ACTIONS.values())


def test_intro_then_echo_and_response():
    """Intro + prompt, per-char echo, then newline echo + body + next prompt."""
    shell = _FakeShell()
    out = _drive(_FakeTransport([b"show vlan\r"]), shell)
    assert out == b"Custom SSH Shell\r\ndevice>show vlan\r\nout:show vlan\r\ndevice>"


def test_empty_line_emits_newline_and_prompt_only():
    """An empty line dispatches with no body: just the newline echo + prompt."""
    out = _drive(_FakeTransport([b"\r"]), _FakeShell())
    assert out == b"Custom SSH Shell\r\ndevice>\r\ndevice>"


def test_nul_byte_is_dropped_midline():
    """A NUL mid-line is dropped (no echo, not buffered); the command still runs."""
    out = _drive(_FakeTransport([b"sh\x00ow vlan\r"]), _FakeShell())
    # NUL absent from echo + the dispatched line is "show vlan".
    assert b"\x00" not in out
    assert b"out:show vlan" in out


def test_crlf_pair_dispatches_once():
    """CR LF is one terminator: a single dispatch, the LF consumed (skip_lf)."""
    out = _drive(_FakeTransport([b"show vlan\r\n"]), _FakeShell())
    assert out.count(b"out:show vlan") == 1


def test_close_writes_only_newline_then_returns():
    """A close result emits just the newline echo (no body/prompt) and stops."""
    out = _drive(_FakeTransport([b"exit\r", b"ignored\r"]), _FakeShell())
    # "exit" echoed + newline, then close — no body, no trailing prompt, and the
    # second chunk is never read.
    assert out.endswith(b"exit\r\n")
    assert b"ignored" not in out


def test_eof_drops_partial_line():
    """An unterminated line at EOF is echoed but not dispatched (no spurious out)."""
    out = _drive(_FakeTransport([b"show ver"]), _FakeShell())
    assert out == b"Custom SSH Shell\r\ndevice>show ver"  # echo only, no response


# ---------------------------------------------------------------- editing flag (#303 P3-1)
def test_editing_off_treats_esc_bs_tab_as_literal_bytes():
    """With editing=False (Telnet) ESC / BS / Tab are ordinary bytes: echoed raw and
    carried into the dispatched line — no cursor/edit interception (codex 1st#1).

    This pins the byte-parity contract on the editing=False side: the editing
    branches are bypassed entirely, so the wire matches the pre-P3-1 machine.
    """
    payload = b"a\tb\x7fc\x1b[D"  # Tab, DEL, and a cursor-left CSI as literal input
    out = _drive(_FakeTransport([payload + b"\r"]), _FakeShell(), editing=False)
    assert payload in out  # every byte echoed verbatim
    assert b"out:" + payload in out  # and the whole payload reached dispatch


def test_editing_lone_esc_then_enter_still_dispatches():
    """A lone ESC before Enter must abort the (empty) escape and dispatch the line,
    not swallow the CR (gemini 1st#1 / claude 1st#2)."""
    out = _drive(_FakeTransport([b"show vlan\x1b\r"]), _FakeShell(), editing=True)
    assert b"out:show vlan" in out


def test_editing_incomplete_csi_then_enter_still_dispatches():
    """An incomplete CSI (ESC [) before Enter aborts the escape and dispatches."""
    out = _drive(_FakeTransport([b"show vlan\x1b[\r"]), _FakeShell(), editing=True)
    assert b"out:show vlan" in out


def test_editing_lone_esc_then_letter_inserts_the_letter():
    """A lone ESC before a printable key drops the ESC and keeps the key, rather than
    swallowing it (only ESC [ / ESC O begin a sequence) — claude 2nd#4."""
    out = _drive(_FakeTransport([b"show vla\x1bn\r"]), _FakeShell(), editing=True)
    assert b"out:show vlan" in out


def test_editing_runaway_escape_resyncs():
    """An unterminated escape is dropped at _MAX_ESC_LEN and the session recovers,
    so the following real command still dispatches (codex 1st#4)."""
    junk = b"\x1b[" + b"1" * 6  # 8 bytes: fills the escape buffer, dropped at maxlen
    out = _drive(_FakeTransport([junk + b"show vlan\r"]), _FakeShell(), editing=True)
    assert b"out:show vlan" in out


def test_malformed_utf8_does_not_crash():
    """A malformed UTF-8 line is decoded with replacement, not a crash (gemini#2)."""
    captured: list[str] = []
    shell = _FakeShell()

    async def _dispatch(line: str):
        captured.append(line)
        return shell.dispatch(line)

    transport = _FakeTransport([b"a\xffb\r"])
    asyncio.run(run_async_push_session(transport, shell, _dispatch))
    assert captured == ["a�b"]  # U+FFFD replacement, session survived


def test_write_failure_ends_session():
    """An io_errors raise on a response write tears the session down cleanly."""
    transport = _FakeTransport([b"show vlan\r"], fail_on=b"out:show vlan")
    # Intro write succeeds, the response write raises -> driver returns (no crash).
    out = _drive(transport, _FakeShell())
    assert out.startswith(b"Custom SSH Shell\r\ndevice>show vlan")


# ---------------------------------------------------------------- line buffer bound + echo backpressure (#347)
def test_line_cap_truncates_input_and_echo():
    """A CR-less byte flood stops accumulating AND echoing at `_LINE_MAX`; the
    eventual CR dispatches the truncated line. Pins the #347 unbounded-line
    bound; the cap (4096) is ~120x the longest golden line, so the scraper wire
    never reaches this branch and byte parity is untouched."""
    seen: list[str] = []

    async def _dispatch(line: str):
        seen.append(line)
        return DispatchResult(body=None, prompt="device>", close=True, mode="user")

    transport = _FakeTransport([b"a" * (_LINE_MAX + 100) + b"\r"])
    asyncio.run(run_async_push_session(transport, _FakeShell(), _dispatch))
    assert len(seen) == 1 and len(seen[0]) == _LINE_MAX  # excess bytes dropped
    assert transport.out.count(b"a") == _LINE_MAX  # ...and never echoed
    # Dropped bytes cost no drain either (1st round codex #4): intro(1) +
    # one per accepted char (_LINE_MAX) + response(1).
    assert transport.drains == _LINE_MAX + 2


def test_line_cap_backspace_reopens_the_line():
    """At the cap the line is still editable (real-device behaviour, 1st round
    codex #2): backspace frees a byte, the next byte is accepted and echoed
    again, and CR dispatches the edited line."""
    seen: list[str] = []

    async def _dispatch(line: str):
        seen.append(line)
        return DispatchResult(body=None, prompt="device>", close=True, mode="user")

    flood = b"a" * (_LINE_MAX + 10) + b"\x7f" + b"b" + b"\r"
    transport = _FakeTransport([flood])
    asyncio.run(run_async_push_session(transport, _FakeShell(), _dispatch, editing=True))
    assert len(seen[0]) == _LINE_MAX
    assert seen[0].endswith("ab")  # freed cell refilled with the new byte
    assert transport.out.count(b"b") == 1  # the replacement byte echoed


def test_challenge_answer_cap_backspace_reopens():
    """The challenge answer stays editable at its cap too (1st round codex #2):
    backspace frees a byte and the next byte lands."""
    transport = _FakeTransport([])
    data = b"y" * (_LINE_MAX + 5) + b"\x08" + b"n" + b"\r"
    stream = iter(data[i : i + 1] for i in range(len(data)))

    async def _read_byte():
        return next(stream, None)

    entered, _skip = asyncio.run(_read_challenge_line(transport, _read_byte, False, echo=True))
    assert entered is not None and len(entered) == _LINE_MAX
    assert entered.endswith("yn")


def test_challenge_answer_cap_echo_off_silent():
    """echo=False (password) at the cap: the buffer is bounded and nothing at
    all reaches the wire — no echo, no drain (1st round gemini #1)."""
    transport = _FakeTransport([])
    data = b"p" * (_LINE_MAX + 50) + b"\r"
    stream = iter(data[i : i + 1] for i in range(len(data)))

    async def _read_byte():
        return next(stream, None)

    entered, _skip = asyncio.run(_read_challenge_line(transport, _read_byte, False, echo=False))
    assert entered is not None and len(entered) == _LINE_MAX
    assert bytes(transport.out) == b""
    assert transport.drains == 0


def test_set_line_refuses_oversized_replacement():
    """`set_line` (the Tab-completion inflow that bypasses `insert`) refuses an
    oversized replacement as a no-op — truncating would complete to a
    *different* command (1st round codex #1)."""
    from simnos.plugins.servers.async_session import _LineEditor

    sent = bytearray()
    editor = _LineEditor(sent.extend)
    editor.insert(b"s")
    editor.insert(b"h")
    sent.clear()
    editor.set_line(b"x" * (_LINE_MAX + 1))
    assert editor.line_text == "sh"  # refused: the existing line is preserved
    assert bytes(sent) == b""  # ...and nothing echoed (no clear-on-reject either)
    editor.set_line(b"x" * _LINE_MAX)  # exactly at the cap is still accepted
    assert len(editor.line_text) == _LINE_MAX


def test_challenge_answer_cap():
    """The challenge answer buffer shares the `_LINE_MAX` bound (#347): a CR-less
    flood mid-challenge cannot grow the answer (nor its echo) without limit."""
    transport = _FakeTransport([])
    data = b"y" * (_LINE_MAX + 50) + b"\r"
    stream = iter(data[i : i + 1] for i in range(len(data)))

    async def _read_byte():
        return next(stream, None)

    entered, _skip = asyncio.run(_read_challenge_line(transport, _read_byte, False, echo=True))
    assert entered is not None and len(entered) == _LINE_MAX
    assert transport.out.count(b"y") == _LINE_MAX


def test_interactive_echo_drains_per_key():
    """Every interactive echo site is followed by a drain (#347): regular char,
    backspace, Tab, escape action. A client that stops reading is paced by the
    transport's backpressure instead of growing the user-space write buffer.
    `drain` writes nothing, so the wire byte stream is unchanged."""
    # intro(1) + 'a'(1) + 'b'(1) + backspace(1) + Tab(1) + Up action(1) + response(1)
    transport = _FakeTransport([b"ab\x7f\t\x1b[A\r"])
    _drive(transport, _FakeShell(), editing=True)
    assert transport.drains == 7


def test_scraper_path_drains_per_char():
    """The non-editing (Telnet / scraper) char echo drains too — the #347 bound
    is not gated on the editing flag."""
    transport = _FakeTransport([b"hi\r"])
    _drive(transport, _FakeShell())
    # intro(1) + 'h'(1) + 'i'(1) + response(1)
    assert transport.drains == 4


def test_async_interactive_login_success_and_skip_lf():
    """Channel login authenticates and reports skip_lf after the password CR."""

    async def _run():
        transport = _FakeTransport([b"admin\r", b"secret\r"])
        ok, skip_lf = await async_interactive_login(
            transport, "admin", "secret", user_prompt=b"User: ", pass_prompt=b"Pass: "
        )
        return ok, skip_lf, bytes(transport.out)

    ok, skip_lf, out = asyncio.run(_run())
    assert ok is True
    assert skip_lf is True  # password line ended on CR
    # Username echoed, password NOT echoed, prompts sent.
    assert b"User: admin\r\n" in out
    assert b"Pass: " in out
    assert b"secret" not in out


def test_async_interactive_login_wrong_password_fails():
    """A wrong password fails authentication."""

    async def _run():
        transport = _FakeTransport([b"admin\r", b"wrong\r"])
        return await async_interactive_login(transport, "admin", "secret", user_prompt=b"User: ", pass_prompt=b"Pass: ")

    ok, _ = asyncio.run(_run())
    assert ok is False


@pytest.mark.parametrize("nul_resets", [False, True])
def test_async_login_nul_dropped_from_username(nul_resets):
    """A NUL mid-username is dropped, never buffered into the credential (#350 login
    bug fix). The old `_async_read_line` only checked NUL inside the skip_lf branch, so
    a non-adjacent NUL fell through, echoed, and corrupted the credential comparison."""

    async def _run():
        transport = _FakeTransport([b"us\x00er\r", b"pw\r"], nul_resets_skip_lf=nul_resets)
        ok, _ = await async_interactive_login(transport, "user", "pw", user_prompt=b"User: ", pass_prompt=b"Pass: ")
        return ok, bytes(transport.out)

    ok, out = asyncio.run(_run())
    assert ok is True  # username parsed as "user" (the NUL dropped, not buffered)
    assert b"\x00" not in out  # NUL never echoed


def test_async_login_ssh_nul_lf_after_username_cr_password_intact():
    """Consumer-level 4-condition pin (#350 login bug, codex 1st#5): on SSH, a NUL then
    the LF half of the username's CR (``\\x00\\n``) before the password must be fully
    consumed — NUL dropped, skip_lf preserved across the NUL, LF consumed as the CR
    half — so the password parses cleanly, auth succeeds, and the final skip_lf is True.
    The old code buffered the NUL into the password and terminated early on the LF."""

    async def _run():
        # One chunk: username "admin\r", then the SSH CR-pair tail "\x00\n" and the
        # password "secret\r" (recv(1) feeds the login readers one byte at a time).
        transport = _FakeTransport([b"admin\r\x00\nsecret\r"], nul_resets_skip_lf=False)
        ok, skip_lf = await async_interactive_login(
            transport, "admin", "secret", user_prompt=b"User: ", pass_prompt=b"Pass: "
        )
        return ok, skip_lf, bytes(transport.out)

    ok, skip_lf, out = asyncio.run(_run())
    assert ok is True  # password parsed as "secret" (NUL + LF consumed, not buffered)
    assert skip_lf is True  # password line ended on CR
    assert b"\x00" not in out  # NUL never echoed
    assert b"secret" not in out  # password (echo off) never on the wire
    assert b"User: admin\r\n" in out  # username echo carries no extra NUL/LF artifact


# ------------------------------------------------ pre-auth input bound (#269)
def test_async_login_username_cap_and_terminator_survival():
    """The pre-auth username read shares the `_LINE_MAX` bound (#269): a CR-less
    flood stops accumulating AND echoing at the cap, yet the terminator machine
    still runs ahead of it, so the CR ends the line and the password read follows.
    That ordering is the contract: moving the cap check above `_consume_terminator`
    would strand a capped session with no way to submit."""

    async def _run():
        # `x` appears in neither prompt, so counting it isolates the username echo.
        transport = _FakeTransport([b"x" * (_LINE_MAX + 100) + b"\r", b"pw\r"])
        ok, skip_lf = await async_interactive_login(
            transport, "admin", "pw", user_prompt=b"User: ", pass_prompt=b"Pass: "
        )
        return ok, skip_lf, transport

    ok, skip_lf, transport = asyncio.run(_run())
    assert ok is False  # the capped credential is not "admin"
    assert skip_lf is True  # ...but the password line WAS read, and ended on CR
    assert transport.out.count(b"x") == _LINE_MAX  # excess never echoed
    # One drain per accepted+echoed byte (_LINE_MAX); the 100 dropped bytes cost
    # no await, the password read is silent (echo off), + the closing drain(1).
    assert transport.drains == _LINE_MAX + 1


def test_async_login_password_cap_is_silent():
    """The password read (echo off) is capped too, and stays wire-silent: no echo,
    no drain — a CR-less flood past the cap costs neither bytes nor awaits (#269)."""

    async def _run():
        # Lowercase `p` appears in neither prompt (`Pass: ` is capitalised), so
        # asserting its absence isolates the password echo the same way test 1
        # isolates the username echo with `x`.
        transport = _FakeTransport([b"admin\r", b"p" * (_LINE_MAX + 50) + b"\r"])
        ok, _ = await async_interactive_login(
            transport, "admin", "p" * _LINE_MAX, user_prompt=b"User: ", pass_prompt=b"Pass: "
        )
        return ok, transport

    ok, transport = asyncio.run(_run())
    assert b"p" not in transport.out  # echo off: never on the wire, capped or not
    # username echo (5) + closing drain (1); the password read adds none.
    assert transport.drains == 6
    # An over-long password is REFUSED, not silently truncated to its first
    # _LINE_MAX bytes — otherwise this input (a correct _LINE_MAX-byte password
    # plus 50 bytes of junk) would authenticate against the configured one
    # (#269, codex 1st#3).
    assert ok is False


def test_async_login_overflow_refused_even_when_prefix_matches():
    """Overflow refusal is decided by the overflow flag, not by the compared text:
    the truncated credential here is byte-for-byte the configured one, and it still
    fails (#269, codex 1st#3). Pins that the cap cannot be used as a prefix oracle."""

    async def _run():
        # Username is exactly _LINE_MAX correct bytes + 1 extra byte before the CR.
        name = "u" * _LINE_MAX
        transport = _FakeTransport([name.encode() + b"Z\r", b"pw\r"])
        return await async_interactive_login(transport, name, "pw", user_prompt=b"User: ", pass_prompt=b"Pass: ")

    ok, _ = asyncio.run(_run())
    assert ok is False


def test_async_login_echo_drains_per_byte():
    """Every echoed pre-auth byte is followed by a drain (#269), so a client that
    stops reading is paced by transport backpressure instead of growing the
    user-space write buffer. `drain` writes nothing, so the wire is unchanged."""

    async def _run():
        transport = _FakeTransport([b"admin\r", b"secret\r"])
        await async_interactive_login(transport, "admin", "secret", user_prompt=b"User: ", pass_prompt=b"Pass: ")
        return transport

    transport = asyncio.run(_run())
    # 'a','d','m','i','n' echoed (5) + the closing `\r\n` drain (1). The CR
    # terminator and the echo-off password contribute none.
    assert transport.drains == 6


class _HangingTransport(_FakeTransport):
    """Transport whose ``recv`` never completes — a client that opens the
    connection and then says nothing (#269 deadline)."""

    async def recv(self, n: int) -> bytes:
        await asyncio.Event().wait()  # never set
        raise AssertionError("unreachable")  # pragma: no cover


class _FloodTransport(_FakeTransport):
    """Transport that answers every read with a non-terminator byte (#269 deadline).

    The ``sleep(0)`` models the real readers, which suspend once their buffer
    empties (``StreamReader.read`` awaits ``_wait_for_data``) — that suspension is
    what lets the deadline's timer run. A fake returning bytes with no suspension
    at all would spin forever, which is a property of the fake, not of the
    transports this bounds; the live end-to-end pin is
    ``test_telnet_server.py::test_preauth_flood_is_closed_at_the_deadline``
    (codex 1st#1).
    """

    async def recv(self, n: int) -> bytes:
        await asyncio.sleep(0)
        return b"a"  # never a terminator


class _TimingOutTransport(_FakeTransport):
    """Transport that raises ``TimeoutError`` itself, as a socket ETIMEDOUT does."""

    async def recv(self, n: int) -> bytes:
        raise TimeoutError("simulated socket ETIMEDOUT")


@pytest.mark.timeout(30)  # a lost deadline must fail fast here, not stall the run
def test_async_login_deadline_folds_into_failed_auth(monkeypatch):
    """A client that never answers is cut loose at `_LOGIN_DEADLINE`, and the
    timeout is folded into `(False, False)` rather than raised (#269) — that is
    what lets both call sites stay unchanged and reuse their close-on-failure path."""
    monkeypatch.setattr("simnos.plugins.servers.async_session._LOGIN_DEADLINE", 0.05)

    async def _run():
        transport = _HangingTransport([])
        return await async_interactive_login(transport, "admin", "secret", user_prompt=b"User: ", pass_prompt=b"Pass: ")

    ok, skip_lf = asyncio.run(_run())
    assert ok is False
    assert skip_lf is False


@pytest.mark.timeout(30)  # ditto: without the deadline this loop never returns
def test_async_login_deadline_bounds_a_capped_flood(monkeypatch):
    """The cap alone bounds memory; the deadline bounds *time*. A client that
    floods past the cap forever still never completes a line, so only the deadline
    ends the session (#269) — the two bounds are complementary, not redundant."""
    monkeypatch.setattr("simnos.plugins.servers.async_session._LOGIN_DEADLINE", 0.05)

    async def _run():
        return await async_interactive_login(
            _FloodTransport([]), "admin", "secret", user_prompt=b"User: ", pass_prompt=b"Pass: "
        )

    ok, _ = asyncio.run(_run())
    assert ok is False


@pytest.mark.timeout(30)
def test_async_login_transport_timeout_is_not_swallowed_as_the_deadline():
    """A `TimeoutError` raised by the transport itself propagates to the caller's
    I/O handler instead of being reported as the login deadline (#269, claude
    1st#2). The builtin is an `OSError` subclass, so a socket ETIMEDOUT arrives as
    one; `asyncio.timeout().expired()` is what tells the two apart."""

    async def _run():
        return await async_interactive_login(
            _TimingOutTransport([]), "admin", "secret", user_prompt=b"User: ", pass_prompt=b"Pass: "
        )

    with pytest.raises(TimeoutError, match="simulated socket ETIMEDOUT"):
        asyncio.run(_run())


# ---------------------------------------------------------------- paging (#307 P3-4)
class _PagingShell(_FakeShell):
    """PushShell stub whose ``dispatch`` returns a fixed multi-line body.

    Inherits the paging surface (more_prompt / page_default_rows / paging_disabled)
    from ``_FakeShell``; the body line count vs the transport's ``page_rows`` drives
    the line-count gate.
    """

    def __init__(self, body: str) -> None:
        self._body = body

    def dispatch(self, line: str) -> DispatchResult:
        # The long (paging) body is returned for "show"; any other line gets a short
        # single-line body so a command typed AFTER a pager quit does not itself page
        # (used by the buffered-tail regression test). All other paging tests use "show".
        body = self._body if line == "show" else f"out:{line}"
        return DispatchResult(body=body, prompt=self.prompt, close=False, mode="user")


def test_resolve_rows():
    """None (no pty/NAWS) -> off; non-positive -> default; positive -> as-is (#307)."""
    assert _resolve_rows(None, 24) is None  # gate off
    assert _resolve_rows(0, 24) == 24  # pty present, height unknown -> default
    assert _resolve_rows(-5, 24) == 24  # negative normalized to default
    assert _resolve_rows(40, 24) == 40  # reported rows used as-is


_MORE = b" --More-- "
_ERASE = b"\b" * 10 + b" " * 10 + b"\b" * 10  # erase " --More-- " (len 10): \b*N + ' '*N + \b*N


def test_paging_off_when_page_rows_none_is_byte_identical():
    """No pty / NAWS (page_rows None): an over-long body still uses the non-paged path."""
    out = _drive(_FakeTransport([b"show\r"], rows=None), _PagingShell("L1\nL2\nL3\nL4\nL5"))
    # Byte-identical to _render_response: \r\n echo + all five lines + prompt, no --More--.
    assert out == b"Custom SSH Shell\r\ndevice>show\r\nL1\r\nL2\r\nL3\r\nL4\r\nL5\r\ndevice>"
    assert _MORE not in out


def test_paging_short_body_within_rows_not_paged():
    """A body that fits in `rows` takes the byte-identical path (line-count gate keystone)."""
    out = _drive(_FakeTransport([b"show\r"], rows=3), _PagingShell("L1\nL2\nL3"))  # 3 == rows
    assert out == b"Custom SSH Shell\r\ndevice>show\r\nL1\r\nL2\r\nL3\r\ndevice>"
    assert _MORE not in out


def test_paging_space_advances_full_page_then_prompt():
    """Space emits the next `rows` lines; the completing write ends with the prompt."""
    out = _drive(_FakeTransport([b"show\r", b" "], rows=3), _PagingShell("L1\nL2\nL3\nL4\nL5"))
    assert out == (b"Custom SSH Shell\r\ndevice>show\r\nL1\r\nL2\r\nL3\r\n" + _MORE + _ERASE + b"L4\r\nL5\r\ndevice>")


def test_paging_enter_advances_one_line():
    """Enter (CR) emits exactly one more line and re-shows --More-- while lines remain."""
    # rows=3 -> first page L1..L3 (2 remain); CR -> L4 (1 remains -> --More--); Space -> L5 -> prompt.
    out = _drive(_FakeTransport([b"show\r", b"\r", b" "], rows=3), _PagingShell("L1\nL2\nL3\nL4\nL5"))
    assert out == (
        b"Custom SSH Shell\r\ndevice>show"
        b"\r\nL1\r\nL2\r\nL3\r\n" + _MORE + _ERASE + b"L4\r\n" + _MORE + _ERASE + b"L5\r\ndevice>"
    )


def test_paging_q_quits_with_prompt_and_discards_rest():
    """q erases --More--, sends the prompt, and discards the remaining body."""
    out = _drive(_FakeTransport([b"show\r", b"q"], rows=3), _PagingShell("L1\nL2\nL3\nL4\nL5"))
    assert out == b"Custom SSH Shell\r\ndevice>show\r\nL1\r\nL2\r\nL3\r\n" + _MORE + _ERASE + b"device>"
    assert b"L4" not in out and b"L5" not in out


def test_paging_drain_failure_ends_session_cleanly():
    """A drain failure after a page send (write-side io_error) tears the session down
    via the main loop's per-byte io_errors handler, not an unhandled exception (codex 2nd#1)."""
    # drain raises once the first page (containing --More--) is written; the intro
    # drain (no --More-- yet) succeeds, so the session reaches the pager first.
    out = _drive(_FakeTransport([b"show\r", b" "], rows=3, fail_drain_on=_MORE), _PagingShell("L1\nL2\nL3\nL4\nL5"))
    assert out.endswith(_MORE)  # first page emitted, then its drain raised -> clean return
    assert b"L4" not in out  # the Space advance never ran (session ended at the failed drain)


def test_paging_q_then_buffered_tail_command_runs():
    """Bytes pipelined after a pager `q` in the SAME recv chunk are processed by the
    main loop as a normal command — the payoff of the shared `read_byte` source (codex 1st#8)."""
    # "show\r" pages; then "q" quits and the trailing "x\r" (same chunk) dispatches as "x".
    out = _drive(_FakeTransport([b"show\r", b"qx\r"], rows=3), _PagingShell("L1\nL2\nL3\nL4\nL5"))
    assert (
        out
        == (
            b"Custom SSH Shell\r\ndevice>show"
            b"\r\nL1\r\nL2\r\nL3\r\n" + _MORE + _ERASE + b"device>"  # first page + q-quit (erase + prompt)
            b"x\r\nout:x\r\ndevice>"  # tail "x" echoed + dispatched normally (not re-paged)
        )
    )


def test_paging_unknown_key_ignored_no_echo():
    """A non-Space/Enter/q key at --More-- is ignored (no echo, no advance)."""
    # 'x' is ignored (not echoed), then 'q' quits.
    out = _drive(_FakeTransport([b"show\r", b"xq"], rows=3), _PagingShell("L1\nL2\nL3\nL4\nL5"))
    assert out == b"Custom SSH Shell\r\ndevice>show\r\nL1\r\nL2\r\nL3\r\n" + _MORE + _ERASE + b"device>"


def test_paging_eof_mid_pager_sends_no_prompt():
    """EOF while waiting at --More-- discards the rest and sends NO prompt (peer gone)."""
    out = _drive(_FakeTransport([b"show\r"], rows=3), _PagingShell("L1\nL2\nL3\nL4\nL5"))
    assert out == b"Custom SSH Shell\r\ndevice>show\r\nL1\r\nL2\r\nL3\r\n" + _MORE
    assert b"L4" not in out


def test_paging_splitlines_normalization_matches_render():
    """Paged body uses the same splitlines() normalization as _render_response:
    an interior blank line is preserved and a trailing newline is dropped (codex 2nd#4)."""
    # "L1\n\nL3\nL4\n".splitlines() -> [L1, "", L3, L4]; rows=3 -> first page L1/blank/L3.
    out = _drive(_FakeTransport([b"show\r", b" "], rows=3), _PagingShell("L1\n\nL3\nL4\n"))
    assert out == (b"Custom SSH Shell\r\ndevice>show\r\nL1\r\n\r\nL3\r\n" + _MORE + _ERASE + b"L4\r\ndevice>")


def test_paging_crlf_split_across_chunks_no_phantom_enter():
    """Keystone (#307, codex 4th#4): the launching CR-LF split across chunks must NOT
    auto-advance the first page — the LF half is consumed via the shared read_byte."""
    # "show\r" | "\n" -> launching CRLF split; then Space advances L4+L5 -> prompt.
    out = _drive(_FakeTransport([b"show\r", b"\n", b" "], rows=3), _PagingShell("L1\nL2\nL3\nL4\nL5"))
    assert out == (b"Custom SSH Shell\r\ndevice>show\r\nL1\r\nL2\r\nL3\r\n" + _MORE + _ERASE + b"L4\r\nL5\r\ndevice>")


def test_paging_final_enter_lf_not_dispatched_as_blank_line():
    """A final pager Enter that completes the body returns skip_lf, so the trailing LF
    (next chunk) is swallowed by the main loop, not dispatched as a phantom blank line."""
    # rows=3 -> first page L1..L3 (1 remains); CR completes (L4 -> prompt); LF carried out.
    out = _drive(_FakeTransport([b"show\r", b"\r", b"\n"], rows=3), _PagingShell("L1\nL2\nL3\nL4"))
    assert out == (b"Custom SSH Shell\r\ndevice>show\r\nL1\r\nL2\r\nL3\r\n" + _MORE + _ERASE + b"L4\r\ndevice>")
    assert out.count(b"device>") == 2  # intro prompt + final paged prompt only (no phantom)


def test_paging_telnet_enter_cr_nul_consumed():
    """On Telnet (nul_resets_skip_lf), a pager Enter's CR NUL advances one line and the
    NUL is consumed, symmetric with the main loop's CR-NUL handling (claude 3rd#2)."""
    # Telnet Enter = CR NUL. Launching "show\r\x00"; pager Enter "\r\x00" completes L4.
    out = _drive(
        _FakeTransport([b"show\r\x00", b"\r\x00"], rows=3, nul_resets_skip_lf=True),
        _PagingShell("L1\nL2\nL3\nL4"),
    )
    assert out == (b"Custom SSH Shell\r\ndevice>show\r\nL1\r\nL2\r\nL3\r\n" + _MORE + _ERASE + b"L4\r\ndevice>")


def test_paging_ssh_nul_in_skip_lf_no_phantom_enter():
    """SSH bug fix (#350): a NUL arriving while skip_lf is pending must NOT clear the
    pending state (SSH preserves it), so the following LF is consumed as the CR half
    and does NOT phantom-advance the pager. The old `_emit_paged` cleared skip_lf on
    every byte and mis-fired the LF as a pager Enter (advancing one line early)."""
    # Launching "show\r" arms skip_lf; SSH "\x00\n" (a NUL, then the LF half of the CR)
    # must both be consumed, then Space advances the remaining lines to the prompt.
    out = _drive(
        _FakeTransport([b"show\r", b"\x00\n", b" "], rows=3, nul_resets_skip_lf=False),
        _PagingShell("L1\nL2\nL3\nL4\nL5"),
    )
    assert out == (b"Custom SSH Shell\r\ndevice>show\r\nL1\r\nL2\r\nL3\r\n" + _MORE + _ERASE + b"L4\r\nL5\r\ndevice>")


def test_paging_disabled_flag_skips_pager():
    """`shell.paging_disabled` True forces the non-paged path even with a small pty."""
    shell = _PagingShell("L1\nL2\nL3\nL4\nL5")
    shell.paging_disabled = True  # as if a `terminal length 0` command ran earlier
    out = _drive(_FakeTransport([b"show\r"], rows=3), shell)
    assert out == b"Custom SSH Shell\r\ndevice>show\r\nL1\r\nL2\r\nL3\r\nL4\r\nL5\r\ndevice>"
    assert _MORE not in out


# ---------------------------------------------------------------- challenge (#338)
_SEKRET = b"sekret"  # the password the fake challenge accepts; must never appear echoed


def _password_pending() -> PendingChallenge:
    """A fired password challenge: prompt `Password: `, echo off, success -> enable."""
    spec = ResolvedChallenge(
        kind="password",
        prompt=ResolvedOutput(kind="literal", text="Password: "),
        modes=frozenset({"user"}),
        auth="password",
        success=Transition(new_mode="enable"),
        failure_output="Bad password",
    )
    return PendingChallenge(spec=spec, command="enable", prompt_text="Password: ", echo=False)


class _ChallengeShell(_FakeShell):
    """dispatch('enable') fires a password challenge; `complete_challenge` accepts `sekret`."""

    prompt = "device>"
    _enable_prompt = "device#"

    def dispatch(self, line: str) -> DispatchResult:
        if line == "enable":
            return DispatchResult(
                body=None, prompt=self.prompt, close=False, mode="user", challenge=_password_pending()
            )
        return super().dispatch(line)

    def complete_challenge(self, pending: PendingChallenge, entered: str) -> DispatchResult:
        if entered == "sekret":
            return DispatchResult(body=None, prompt=self._enable_prompt, close=False, mode="enable")
        return DispatchResult(body=pending.spec.failure_output, prompt=self.prompt, close=False, mode="user")


def _drive_challenge(transport: _FakeTransport, shell: _ChallengeShell, **kwargs) -> bytes:
    async def _dispatch(line: str):
        return shell.dispatch(line)

    async def _complete(pending: PendingChallenge, entered: str):
        return shell.complete_challenge(pending, entered)

    asyncio.run(run_async_push_session(transport, shell, _dispatch, complete=_complete, **kwargs))
    return bytes(transport.out)


def test_challenge_password_success_wire():
    """A correct password: the held `\\r\\n` + prompt, the answer NOT echoed, then the
    single held-echo newline + the new (enable) prompt — exactly one `\\r\\n` per Enter."""
    out = _drive_challenge(_FakeTransport([b"enable\r", _SEKRET + b"\r"]), _ChallengeShell())
    assert out == b"Custom SSH Shell\r\ndevice>enable\r\nPassword: \r\ndevice#"
    assert _SEKRET not in out  # echo off: the password never reaches the wire


def test_challenge_password_wrong_wire():
    """A wrong password: the failure body + the original prompt, answer not echoed."""
    out = _drive_challenge(_FakeTransport([b"enable\r", b"nope\r"]), _ChallengeShell())
    assert out == b"Custom SSH Shell\r\ndevice>enable\r\nPassword: \r\nBad password\r\ndevice>"
    assert b"nope" not in out


def test_challenge_eof_mid_challenge_sends_nothing():
    """EOF while waiting for the answer ends the session after the prompt, with no
    render (a synthesized close would leak a stray `\\r\\n`) — the sentinel-None path."""
    out = _drive_challenge(_FakeTransport([b"enable\r"]), _ChallengeShell())
    assert out == b"Custom SSH Shell\r\ndevice>enable\r\nPassword: "  # prompt sent, then EOF, nothing more


def test_challenge_backspace_edits_answer_off_echo():
    """Backspace edits the answer buffer with no echo (echo off), so a typo-corrected
    password still verifies and no byte of it reaches the wire."""
    # Type "sekXX", backspace twice, then "ret" -> "sekret".
    out = _drive_challenge(_FakeTransport([b"enable\r", b"sekXX\x08\x08ret\r"]), _ChallengeShell())
    assert out.endswith(b"\r\ndevice#")  # verified -> enable prompt
    assert b"sek" not in out and b"XX" not in out  # nothing of the answer echoed


def test_challenge_escape_sequence_discarded_from_answer():
    """An arrow-key escape mid-answer is swallowed, not injected into the password."""
    # "sek" + left-arrow (ESC [ D) + "ret" -> "sekret" (escape discarded).
    out = _drive_challenge(_FakeTransport([b"enable\r", b"sek\x1b[Dret\r"]), _ChallengeShell())
    assert out.endswith(b"\r\ndevice#")  # escape did not corrupt the answer


def test_challenge_skip_lf_carry_cross_chunk():
    """The launching command's CR-LF split across chunks: the LF half is consumed by
    the answer reader (carried skip_lf), not mistaken for part of the password."""
    out = _drive_challenge(_FakeTransport([b"enable\r", b"\n", _SEKRET + b"\r"]), _ChallengeShell())
    assert out == b"Custom SSH Shell\r\ndevice>enable\r\nPassword: \r\ndevice#"


def test_challenge_answer_not_in_editor_history():
    """The answer is read outside the line editor, so Up after the challenge replays
    the launching command, never the password (history non-leak, editing on)."""
    # enable\r (enters editor history) -> sekret\r (read by _read_challenge_line, NOT
    # the editor) -> Up arrow (ESC [ A): the editor replays "enable", not the password.
    out = _drive_challenge(_FakeTransport([b"enable\r", _SEKRET + b"\r", b"\x1b[A"]), _ChallengeShell(), editing=True)
    assert _SEKRET not in out  # never on the wire, including the history redraw
    assert out.endswith(b"enable")  # Up replayed the launching command


def test_read_challenge_line_echo_on_echoes_chars_and_backspace():
    """`_read_challenge_line(echo=True)` (the Phase 3 confirm path): regular chars
    echo raw, backspace emits `\\b \\b`, and the terminating CR is NOT echoed (the
    held-echo principle). Phase 1 only reaches echo=False (password), so this pins
    the echo-on byte behaviour now for the Phase 3 confirm reuse (claude 1st#2)."""
    transport = _FakeTransport([])  # only its `send` + flags are used; read_byte is injected
    data = b"yeXX\x08\x08s\r"  # 'y','e', typo 'XX', two backspaces, 's', CR -> "yes"
    stream = iter(data[i : i + 1] for i in range(len(data)))

    async def _read_byte():
        return next(stream, None)

    entered, next_skip_lf = asyncio.run(_read_challenge_line(transport, _read_byte, False, echo=True))
    assert entered == "yes"
    assert next_skip_lf is True  # terminated on CR
    # chars echoed raw, each backspace erased with `\b \b`, CR not echoed.
    assert bytes(transport.out) == b"yeXX\b \b\b \bs"


def test_read_challenge_line_eof_returns_sentinel():
    """EOF mid-answer returns `(None, skip_lf)` — the sentinel the driver turns into
    a no-render session end (echo-on path, symmetric with the echo-off driver test)."""
    transport = _FakeTransport([])
    stream = iter([b"a", b"b"])  # no terminator, then EOF

    async def _read_byte():
        return next(stream, None)

    entered, _skip = asyncio.run(_read_challenge_line(transport, _read_byte, False, echo=True))
    assert entered is None
    assert bytes(transport.out) == b"ab"  # the two chars echoed before EOF


def test_challenge_no_complete_callable_closes():
    """A challenge with no `complete` wired (a bare test fake) closes the session
    loudly rather than crashing the driver."""

    async def _dispatch(line: str):
        return _ChallengeShell().dispatch(line)

    transport = _FakeTransport([b"enable\r", _SEKRET + b"\r"])
    asyncio.run(run_async_push_session(transport, _ChallengeShell(), _dispatch))  # complete=None
    out = bytes(transport.out)
    assert out == b"Custom SSH Shell\r\ndevice>enable"  # fired, no complete -> returned before the prompt
