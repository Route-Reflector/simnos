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
    async_interactive_login,
    run_async_push_session,
)
from simnos.plugins.shell.cmd_shell import DispatchResult


class _FakeShell:
    """PushShell stub: ``dispatch`` echoes the line, ``exit`` closes."""

    intro = "Custom SSH Shell"
    prompt = "device>"
    newline = "\r\n"

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

    ``recv(n)`` returns up to *n* bytes (respecting ``n`` like the real
    ``AsyncSSHProcessTransport``), so the channel-login path that reads one byte
    at a time behaves faithfully. The chunk list is flattened — the session
    driver iterates byte-by-byte, so chunk boundaries do not affect its output.
    """

    io_errors = (OSError,)
    nul_resets_skip_lf = False
    name = "ssh"

    def __init__(self, chunks: list[bytes], *, fail_on: bytes | None = None) -> None:
        self._buf = b"".join(chunks)
        self.out = bytearray()
        self._fail_on = fail_on

    async def recv(self, n: int) -> bytes:
        if not self._buf:
            return b""  # EOF
        chunk, self._buf = self._buf[:n], self._buf[n:]
        return chunk

    def send(self, data: bytes) -> None:
        if self._fail_on is not None and self._fail_on in data:
            raise OSError("simulated write failure")
        self.out += data

    async def drain(self) -> None:
        pass


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
