"""Async push-dispatch session driver (#297 Stage 2, §3 / §3a).

The async counterpart to ``tap_bridge.run_push_session``: it drives one client
session over an event-driven transport (asyncssh process in Stage 2) using the
**same** wire-assembly helpers (``_render_intro`` / ``_render_response``), so the
byte stream is identical to the paramiko push path — pinned by the byte-parity
goldens in ``tests/plugins/test_ssh_byte_parity.py``.

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
# stays byte-identical to the synchronous paramiko path.
_READ_CHUNK = 4096


class AsyncPushTransport(Protocol):
    """Minimal async transport surface the session driver needs (§3a, claude#3).

    Mirrors ``tap_bridge.TransportAdapter`` but with an async ``recv`` (the read
    is event-driven, not a blocking pull). ``send`` buffers a write; ``drain``
    applies flow-control backpressure at response boundaries so a slow client
    cannot make the server buffer without bound under the 100-host load.
    """

    #: Exceptions that mean "I/O failed / peer gone" for this transport.
    io_errors: tuple[type[BaseException], ...]

    #: RFC 854 CR NUL quirk switch (False for SSH, True for Telnet) — same
    #: contract as ``TransportAdapter.nul_resets_skip_lf``.
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


async def run_async_push_session(
    transport: AsyncPushTransport,
    shell: "PushShell",
    dispatch: Callable[[str], Awaitable["DispatchResult"]],
    *,
    initial_skip_lf: bool = False,
) -> None:
    """Drive one client session with async push dispatch (#297 Stage 2, §3a).

    The state machine is identical to ``run_push_session`` (regular char =
    immediate echo; line terminator = held ``\\r\\n`` echo + body + prompt in one
    write), so the wire bytes match the paramiko push path. The differences are
    structural, not behavioural on the wire:

    - the read is ``await transport.recv(...)`` (event-driven) instead of a
      blocking per-byte pull, so the event-loop thread is free between bytes;
    - ``shell.dispatch`` runs via the injected ``dispatch`` coroutine (bounded
      executor), so a slow handler does not block the loop (§2a);
    - shutdown is propagated by the transport closing (``recv`` -> ``b""`` / an
      ``io_errors`` raise) rather than a polled ``is_running`` flag — the shared
      loop closes the session on stop (§1a).

    ``initial_skip_lf`` consumes a trailing LF/NUL left by a preceding channel
    login (auth_none), matching ``run_push_session``.
    """
    try:
        transport.send(_render_intro(shell))
        await transport.drain()
    except transport.io_errors:
        log.debug("async_session [%s] intro write closed", transport.name)
        return

    buffer = bytearray()
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
                # session (parity with run_push_session, gemini#2).
                line = bytes(buffer).decode("utf-8", errors="replace")
                buffer.clear()
                result = await dispatch(line)
                try:
                    transport.send(_render_response(shell, result))
                    await transport.drain()
                except transport.io_errors as e:
                    log.error("async_session [%s] client write error: %s", transport.name, e)
                    return
                if result.close:
                    return
            else:
                # Regular character: immediate echo (interactive latency
                # unchanged). The raw byte is echoed, matching run_push_session.
                try:
                    transport.send(byte)
                except transport.io_errors as e:
                    log.error("async_session [%s] client write error: %s", transport.name, e)
                    return
                buffer += byte


async def _async_read_line(transport: AsyncPushTransport, *, echo: bool, skip_lf: bool) -> tuple[str, bool]:
    """Read one line byte-by-byte (async mirror of ``tap_bridge.read_line``).

    Returns ``(line without trailing CR/LF, next_skip_lf)``; a CR sets
    ``next_skip_lf=True`` so the next read consumes the LF half of a CR LF pair.
    Reads one byte per ``recv`` (login is short and not perf-critical, so this
    avoids a leftover-buffer between the two reads). EOF returns the partial line
    (same contract as the sync ``read_line``).
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
    """Async channel-level login (mirror of ``tap_bridge.interactive_login``).

    Used for auth_none platforms (e.g. Dell PowerConnect) before the shell.
    Returns ``(authenticated, skip_lf)``; ``skip_lf`` is forwarded to
    ``run_async_push_session`` as ``initial_skip_lf`` so it consumes the trailing
    LF/NUL left by the final CR of the password line. The wire interaction is
    byte-identical to the sync path.
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
