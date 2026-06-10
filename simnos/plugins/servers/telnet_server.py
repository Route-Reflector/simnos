"""
Telnet server plugin for SIMNOS.

Implements a minimal Telnet server (RFC 854, 857, 858) using raw sockets
and the existing TCPServerBase + TapIO architecture. No external dependencies.
"""

import contextlib
import ipaddress
import logging
import socket
import threading
import time
from typing import Any

from simnos.core.nos import Nos
from simnos.core.servers import TCPServerBase
from simnos.core.timeouts import SHUTDOWN_IO_TIMEOUT
from simnos.plugins.servers.tap_bridge import (
    client_to_shell_tap,
    interactive_login,
    shell_to_client_tap,
)
from simnos.plugins.servers.tap_io import TapIO

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Telnet protocol constants (RFC 854, 857, 858)
# ---------------------------------------------------------------------------
IAC = 0xFF  # Interpret As Command
WILL = 0xFB
WONT = 0xFC
DO = 0xFD
DONT = 0xFE
SB = 0xFA  # Subnegotiation Begin
SE = 0xF0  # Subnegotiation End
SGA = 0x03  # Suppress Go Ahead
ECHO = 0x01  # Echo
NAWS = 0x1F  # Negotiate About Window Size

# Short timeout (seconds) for draining initial IAC negotiation responses.
# Must be long enough for TCP-fragmented IAC sequences to arrive completely,
# but short enough not to delay the login prompt noticeably.  Loopback RTT
# is sub-millisecond, so 50 ms gives ample margin.
_IAC_DRAIN_TIMEOUT = 0.05


def _is_loopback(address: str) -> bool:
    """Check whether *address* resolves to a loopback IP."""
    try:
        info = socket.getaddrinfo(address, None, type=socket.SOCK_STREAM)
        return all(ipaddress.ip_address(ai[4][0]).is_loopback for ai in info)
    except (OSError, ValueError):
        return False


class TelnetSocketAdapter:
    """TransportAdapter implementation wrapping a raw Telnet socket (G3 / #225).

    Delegates byte reads to ``TelnetServer._recv_byte`` (private by design)
    so IAC negotiation handling stays inside the Telnet protocol layer.
    """

    io_errors = (OSError,)
    nul_resets_skip_lf = True  # RFC 854: CR NUL is a complete sequence
    name = "telnet"

    def __init__(self, sock: socket.socket, server: "TelnetServer"):
        self._sock = sock
        self._server = server

    def recv_byte(self) -> bytes | None:
        return self._server._recv_byte(self._sock)

    def sendall(self, data: bytes) -> None:
        self._sock.sendall(data)

    def is_closed(self) -> bool:
        # U2: known-local-closed early check only (peer disconnect is
        # detected via recv_byte() -> None / send io_errors).
        return self._sock.fileno() == -1


class TelnetServer(TCPServerBase):
    """
    Telnet server plugin using raw sockets.

    Follows the same plugin architecture as ParamikoSshServer:
    TCPServerBase → connection_function() → TapIO → CMDShell.
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
    ):
        super().__init__(address=address, port=port, timeout=timeout)

        self.nos: Nos = nos
        self.nos_inventory_config: dict = nos_inventory_config
        self.shell: type = shell
        self.shell_configuration: dict = shell_configuration or {}
        self.banner: str = banner
        self.username: str = username
        self.password: str = password
        self.watchdog_interval: float = watchdog_interval

        if not _is_loopback(address):
            log.warning(
                "Telnet transmits all data (including credentials) in plaintext. "
                "Binding to non-local address %s is insecure. "
                "Use SSH (ParamikoSshServer) for non-local access.",
                address,
            )

    # ------------------------------------------------------------------
    # IAC handling
    # ------------------------------------------------------------------

    def _recv_byte(self, sock: socket.socket) -> bytes | None:
        """Read one data byte, transparently handling IAC sequences."""
        while True:
            byte = sock.recv(1)
            if not byte:
                return None
            if byte[0] != IAC:
                return byte
            # IAC handling
            cmd = sock.recv(1)
            if not cmd:
                return None
            if cmd[0] == IAC:  # IAC IAC → literal 0xFF
                return b"\xff"
            if cmd[0] in (WILL, WONT, DO, DONT):  # 3-byte negotiation
                opt = sock.recv(1)
                if opt:
                    self._handle_negotiation(sock, cmd[0], opt[0])
                continue
            if cmd[0] == SB:  # Subnegotiation → skip until IAC SE
                self._skip_subnegotiation(sock)
                continue
            continue  # Other IAC commands (NOP, GA) → skip

    def _drain_pending_input(self, sock: socket.socket) -> None:
        """Drain bytes the client already sent, answering IAC sequences.

        Used after the initial negotiation window (answering queued IAC
        responses) and right before abandoning a connection on the
        authentication-failure path. The failure-path call matters because
        closing a socket whose receive buffer still holds unread data makes
        TCP send RST instead of FIN (RFC 2525 2.17); on Windows an RST also
        discards data the client has not read yet, so anything we just sent
        (e.g. ``Authentication failed.``) silently disappears (#268). A
        short blocking timeout is used instead of non-blocking mode so that
        multi-byte IAC sequences split across TCP segments are received
        completely rather than raising mid-sequence.
        """
        sock.settimeout(_IAC_DRAIN_TIMEOUT)
        try:
            while True:
                if self._recv_byte(sock) is None:
                    break  # EOF — client disconnected
        except TimeoutError:
            pass  # No more data available — expected
        finally:
            sock.settimeout(self.timeout)

    def _handle_negotiation(self, sock: socket.socket, cmd: int, opt: int) -> None:
        """Respond to a Telnet negotiation command."""
        if cmd == DO:
            if opt not in (SGA, ECHO):
                sock.sendall(bytes([IAC, WONT, opt]))  # Refuse unsupported
        elif cmd == WILL:
            if opt == NAWS:
                sock.sendall(bytes([IAC, DO, opt]))  # Accept NAWS
            else:
                sock.sendall(bytes([IAC, DONT, opt]))  # Refuse others
        # DONT, WONT → no response needed (already off)

    def _skip_subnegotiation(self, sock: socket.socket) -> None:
        """Skip subnegotiation data until IAC SE, handling IAC IAC escapes."""
        while True:
            byte = sock.recv(1)
            if not byte:
                return  # EOF → silently return (disconnect detected upstream)
            if byte[0] == IAC:
                next_byte = sock.recv(1)
                if not next_byte:
                    return  # EOF
                if next_byte[0] == SE:
                    return  # Normal end of subnegotiation
                # IAC IAC → escaped 0xFF in SB data, ignore and continue
                # IAC + other → protocol violation, tolerate and continue
                continue

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def _authenticate(self, sock: socket.socket) -> tuple[bool, bool]:
        """
        Perform username/password authentication over the Telnet connection.

        Thin wrapper around tap_bridge.interactive_login supplying the
        Telnet prompts; the interaction itself is shared with SSH channel
        login. The trailing LF/NUL after a CR is no longer consumed with a
        blocking read — it is reported via skip_lf and must be forwarded to
        client_to_shell_tap (initial_skip_lf), matching SSH (U3).

        :param sock: client socket
        :return: (authenticated, skip_lf)
        """
        return interactive_login(
            TelnetSocketAdapter(sock, self),
            self.username,
            self.password,
            user_prompt=b"Username: ",
            pass_prompt=b"Password: ",
        )

    # ------------------------------------------------------------------
    # Watchdog
    # ------------------------------------------------------------------

    def watchdog(
        self,
        is_running: threading.Event,
        run_srv: threading.Event,
        shell: Any,
    ) -> None:
        """Monitor server liveness and ensure shell stops on disconnect.

        The loop exits when either ``run_srv`` is cleared (client disconnect
        detected by a tap function) or ``is_running`` is cleared (server-wide
        shutdown).  In both cases ``shell.stop()`` must be called so that
        ``CMDShell.cmdloop()`` unblocks and ``connection_function`` can return.
        """
        while run_srv.is_set():
            if not is_running.is_set():
                break
            time.sleep(min(self.watchdog_interval, SHUTDOWN_IO_TIMEOUT))
        # Always stop the shell — whether run_srv or is_running caused the exit.
        shell.stop()

    # ------------------------------------------------------------------
    # Connection handler
    # ------------------------------------------------------------------

    def connection_function(self, client: socket.socket, is_running: threading.Event) -> None:
        shell_replied_event = threading.Event()
        run_srv = threading.Event()
        run_srv.set()

        try:
            client.settimeout(self.timeout)

            # Initiate Telnet negotiation: character-at-a-time mode
            client.sendall(bytes([IAC, WILL, SGA]))
            client.sendall(bytes([IAC, WILL, ECHO]))

            # Give the client a moment to send initial IAC responses,
            # then drain them using _recv_byte so that negotiation commands
            # (e.g. DO SGA, DO ECHO, WILL NAWS) are properly answered via
            # _handle_negotiation instead of being silently discarded.
            time.sleep(0.1)
            self._drain_pending_input(client)

            # Send banner
            if self.banner:
                client.sendall((self.banner + "\r\n").encode("utf-8"))

            # Authenticate
            try:
                auth_ok, skip_lf = self._authenticate(client)
            except (TimeoutError, OSError):
                log.debug("Client disconnected during authentication")
                return
            if not auth_ok:
                log.warning("Telnet authentication failed, closing connection")
                with contextlib.suppress(OSError):
                    client.sendall(b"Authentication failed.\r\n")
                # Consume the input left pending on the failure path (the
                # LF/NUL that read_line's skip_lf defers from the password
                # line's CR is forwarded to client_to_shell_tap only on
                # success) — otherwise close() RSTs and the failure message
                # never reaches Windows clients (#268).
                with contextlib.suppress(OSError):
                    self._drain_pending_input(client)
                return

            # Create stdio for the shell
            shell_stdin, shell_stdout = TapIO(run_srv), TapIO(run_srv)

            # Bridge the socket and the shell through the shared tap pair
            transport_adapter = TelnetSocketAdapter(client, self)

            # Start client→shell tap thread (skip_lf forwards the pending
            # LF/NUL from the password line's CR — U3, matches SSH)
            client_to_shell_tapper = threading.Thread(
                target=client_to_shell_tap,
                args=(transport_adapter, shell_stdin, shell_replied_event, run_srv),
                kwargs={"initial_skip_lf": skip_lf, "shell_stdout": shell_stdout},
                daemon=True,
            )
            client_to_shell_tapper.start()

            # Start shell→client tap thread
            shell_to_client_tapper = threading.Thread(
                target=shell_to_client_tap,
                args=(transport_adapter, shell_stdout, shell_replied_event, run_srv),
                daemon=True,
            )
            shell_to_client_tapper.start()

            # Create the client shell
            client_shell = self.shell(
                stdin=shell_stdin,
                stdout=shell_stdout,
                nos=self.nos,
                nos_inventory_config=self.nos_inventory_config,
                is_running=is_running,
                **self.shell_configuration,
            )

            # Start watchdog thread
            watchdog_thread = threading.Thread(
                target=self.watchdog,
                args=(is_running, run_srv, client_shell),
                daemon=True,
            )
            watchdog_thread.start()

            # Block until shell exits
            client_shell.start()
            log.debug("TelnetServer.connection_function stopped shell thread")

        finally:
            # Stop all server threads
            run_srv.clear()
            log.debug("TelnetServer.connection_function stopped server threads")

            with contextlib.suppress(OSError):
                client.close()
            log.debug("TelnetServer.connection_function closed socket")
