"""telnetlib3-backed Telnet server plugin (#297 Stage 3, §2 Telnet).

Replaces the raw-socket Telnet server (TCPServerBase + manual IAC handling + two
tap threads + ``TapIO``) with a telnetlib3 server on the SimNOS-owned shared event
loop — the same architecture as :class:`AsyncSshServer` (Stage 2). The shared
lifecycle (start/stop/aclose, session registry, dispatch wiring) lives in
:class:`AsyncServerBase`; this module only supplies the Telnet transport + the
in-band login.

Why telnetlib3 (#296 spike F7 + #297 Stage 3 先行検証):

- ``encoding=False`` gives a **transparent binary** byte stream: the server reader
  sees the client's raw CR / LF / NUL bytes (IAC stripped), and the writer sends
  bytes verbatim (no ``\\n``→``\\r\\n`` translation). So the **same**
  :func:`run_async_push_session` + ``_render_*`` wire assembly the SSH path uses
  produces a byte-identical application-layer wire here — only the transport-level
  IAC negotiation differs (telnetlib3 negotiates ``WILL ECHO`` / ``WILL SGA`` /
  ``BINARY`` itself, matching the old server's char-at-a-time + server echo).
- The raw-socket server's ``_drain_pending_input`` (RST→FIN guarantee, #268) is
  **not** needed: asyncio's StreamReader continuously drains the kernel receive
  buffer into an in-memory buffer, so unread input never sits in the kernel buffer
  at ``close()`` time and the close is a graceful FIN (verified on the auth-failure
  path, Stage 3 先行検証 ``s3_close_path.py``).
"""

import asyncio
import contextlib
import ipaddress
import logging
import socket
from typing import TYPE_CHECKING

import telnetlib3

from simnos.core.nos import Nos
from simnos.plugins.servers.async_server_base import AsyncServerBase, Listener
from simnos.plugins.servers.async_session import async_interactive_login

if TYPE_CHECKING:
    from simnos.core.host import HostRenderConfig
    from simnos.core.simnos import SimNOS

log = logging.getLogger(__name__)

#: Negotiation settle budget (seconds) before telnetlib3 runs the shell. The
#: telnetlib3 default (4.0) is generous; this lower bound keeps the login prompt
#: responsive. The shell (``_handle_client``) is what sends the banner + login
#: prompts, so a client that does NOT fully answer negotiation waits up to this
#: budget before seeing the banner / ``Username:`` prompt. A responsive client
#: (netmiko, a telnetlib3 client) settles well before this and is unaffected.
_CONNECT_MAXWAIT = 1.0


def _is_loopback(address: str) -> bool:
    """Check whether *address* resolves to a loopback IP."""
    try:
        info = socket.getaddrinfo(address, None, type=socket.SOCK_STREAM)
        return all(ipaddress.ip_address(ai[4][0]).is_loopback for ai in info)
    except (OSError, ValueError):
        return False


class TelnetPushTransport:
    """AsyncPushTransport over a telnetlib3 binary (``encoding=False``) stream.

    The reader/writer are byte-transparent (see the module docstring), so the
    session driver's byte state machine (per-char echo, CR-LF / CR-NUL handling)
    works exactly as on SSH. ``nul_resets_skip_lf=True`` is the only transport
    difference: RFC 854 makes CR NUL a complete line terminator, so a NUL clears
    the pending skip_lf (SSH has no such convention).
    """

    # ConnectionError is a subclass of OSError, so (OSError, EOFError) already
    # covers it; EOFError is listed because telnetlib3's binary reader can raise
    # it on an abrupt peer close (not an OSError subclass).
    io_errors = (OSError, EOFError)
    nul_resets_skip_lf = True  # RFC 854: CR NUL is a complete sequence
    name = "telnet"

    def __init__(self, reader: "telnetlib3.TelnetReader", writer: "telnetlib3.TelnetWriter") -> None:
        self._reader = reader
        self._writer = writer

    async def recv(self, n: int) -> bytes:
        return await self._reader.read(n)

    def send(self, data: bytes) -> None:
        self._writer.write(data)

    async def drain(self) -> None:
        await self._writer.drain()


class TelnetServer(AsyncServerBase):
    """Telnet server plugin (telnetlib3) on the SimNOS-owned shared loop (§1 / §2).

    Same constructor signature as the legacy raw-socket server (so the inventory
    ``plugin: TelnetServer`` is unchanged) plus the ``simnos`` back reference added
    by ``Host.start``. The generic lifecycle is in :class:`AsyncServerBase`; this
    class supplies the telnetlib3 listener + the in-band Username/Password login.
    """

    def __init__(
        self,
        shell: type,
        nos: Nos,
        nos_inventory_config: dict,
        port: int,
        username: str,
        password: str,
        banner: str = "SIMNOS Telnet Server",
        shell_configuration: dict | None = None,
        address: str = "127.0.0.1",
        timeout: int = 1,
        watchdog_interval: float = 1,
        render_config: "HostRenderConfig | None" = None,
        simnos: "SimNOS | None" = None,
    ) -> None:
        super().__init__(
            shell,
            nos,
            nos_inventory_config,
            port,
            username,
            password,
            shell_configuration=shell_configuration,
            address=address,
            timeout=timeout,
            watchdog_interval=watchdog_interval,
            render_config=render_config,
            simnos=simnos,
        )
        self.banner: str = banner
        if not _is_loopback(address):
            log.warning(
                "Telnet transmits all data (including credentials) in plaintext. "
                "Binding to non-local address %s is insecure. "
                "Use SSH (AsyncSshServer) for non-local access.",
                address,
            )

    # ------------------------------------------------------------------ hooks
    async def _create_listener(self) -> Listener:
        # Store on self before returning so _abort_failed_start can close it even
        # if start()'s result() already timed out (codex 1st#1). telnetlib3 returns
        # an asyncio.Server (close() + wait_closed() = the Listener protocol);
        # asyncio's create_server defaults reuse_address=True on POSIX, so stop→start
        # does not hit EADDRINUSE (parity with the asyncssh reuse_address bind).
        self._acceptor = await telnetlib3.create_server(
            host=self.address,
            port=self.port,
            shell=self._handle_client,
            encoding=False,  # binary, byte-transparent → shared wire assembly
            connect_maxwait=_CONNECT_MAXWAIT,
        )
        return self._acceptor

    def _close_session(self, session: object) -> None:
        session.close()  # type: ignore[attr-defined]  # session is a telnetlib3 writer

    # ------------------------------------------------------------------ per-session
    async def _handle_client(self, reader: "telnetlib3.TelnetReader", writer: "telnetlib3.TelnetWriter") -> None:
        """telnetlib3 shell handler: one interactive Telnet session (§3a).

        telnetlib3 has finished IAC negotiation before this runs. The flow mirrors
        the legacy ``connection_function`` at the application layer: banner →
        in-band Username/Password login → push session. On auth failure the message
        is written and the connection closed; asyncio's continuous read keeps the
        kernel receive buffer empty, so the close is a graceful FIN that delivers
        the message (Stage 3 先行検証, no explicit drain needed).
        """
        if self._bow_out_if_closing(writer):
            return
        async with self._session_scope(writer):
            transport = TelnetPushTransport(reader, writer)
            try:
                if self.banner:
                    transport.send((self.banner + "\r\n").encode("utf-8"))
                    await transport.drain()
                authenticated, skip_lf = await async_interactive_login(
                    transport,
                    self.username,
                    self.password,
                    user_prompt=b"Username: ",
                    pass_prompt=b"Password: ",
                )
                if not authenticated:
                    log.warning("Telnet authentication failed, closing connection")
                    with contextlib.suppress(*transport.io_errors):
                        transport.send(b"Authentication failed.\r\n")
                        await transport.drain()
                    # No explicit receive-buffer drain before close (the raw-socket
                    # server's _drain_pending_input, #268): asyncio's StreamReader has
                    # already pulled any unread client bytes off the kernel socket, so
                    # _session_scope's writer.close() is a graceful FIN that delivers
                    # the message — pinned by test_telnet_auth_failure_delivers_
                    # message_and_fin (incl. surplus unread input).
                    return
                await self._drive_session(transport, skip_lf=skip_lf)
            except asyncio.CancelledError:
                raise
            except transport.io_errors as exc:
                # Peer gone during banner/login is normal; log at debug, tear down
                # quietly (an in-session disconnect is already absorbed by the push
                # driver, which catches transport.io_errors and returns).
                log.debug("Telnet session I/O ended: %s", exc)
            except Exception:
                # A session-level crash must not take down the loop; log + tear
                # down this session only (§3a observability, #294-aligned).
                log.exception("TelnetServer session crashed")
