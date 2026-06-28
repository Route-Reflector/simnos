"""Unit tests for the async push session driver (#297 Stage 2, §3a).

Pin the wire contract of ``run_async_push_session`` + ``async_interactive_login``
in isolation (fake transport + fake shell), so a regression in the byte state
machine is caught here without spinning a real asyncssh server. The byte-exact
parity with the paramiko push path is pinned separately by the byte-parity
goldens; these pin the driver's branch behaviour (echo / NUL / close / EOF /
malformed UTF-8 / login skip_lf).
"""

import asyncio

from simnos.plugins.servers.async_session import (
    _resolve_rows,
    async_interactive_login,
    run_async_push_session,
)
from simnos.plugins.shell.cmd_shell import DispatchResult


class _FakeShell:
    """PushShell stub: ``dispatch`` echoes the line, ``exit`` closes."""

    intro = "Custom SSH Shell"
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

    io_errors = (OSError,)
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
        if self._fail_drain_on is not None and self._fail_drain_on in self.out:
            raise OSError("simulated drain failure")

    def page_rows(self) -> int | None:
        return self._rows


def _drive(transport: _FakeTransport, shell: _FakeShell, **kwargs) -> bytes:
    async def _dispatch(line: str):
        return shell.dispatch(line)

    asyncio.run(run_async_push_session(transport, shell, _dispatch, **kwargs))
    return bytes(transport.out)


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


def test_paging_disabled_flag_skips_pager():
    """`shell.paging_disabled` True forces the non-paged path even with a small pty."""
    shell = _PagingShell("L1\nL2\nL3\nL4\nL5")
    shell.paging_disabled = True  # as if a `terminal length 0` command ran earlier
    out = _drive(_FakeTransport([b"show\r"], rows=3), shell)
    assert out == b"Custom SSH Shell\r\ndevice>show\r\nL1\r\nL2\r\nL3\r\nL4\r\nL5\r\ndevice>"
    assert _MORE not in out
