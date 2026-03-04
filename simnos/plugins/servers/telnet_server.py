"""
Telnet server plugin for SIMNOS.

Implements a minimal Telnet server (RFC 854, 857, 858) using raw sockets
and the existing TCPServerBase + TapIO architecture. No external dependencies.
"""

import contextlib
import io
import ipaddress
import logging
import socket
import threading
import time
from typing import Any

from simnos.core.nos import Nos
from simnos.core.servers import TCPServerBase
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

_SHUTDOWN_TIMEOUT = 2  # Bounded timeout for shutdown-critical paths (watchdog sleep cap)

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
    # Line reading and authentication
    # ------------------------------------------------------------------

    def _read_line(self, sock: socket.socket, echo: bool = True) -> str:
        """
        Read a single line from the socket byte-by-byte using _recv_byte.

        Handles CR LF, CR NUL (RFC 854), and bare LF as line terminators.

        :param sock: client socket
        :param echo: if True, echo each byte back to the client
        :return: the line read (without trailing CR/LF)
        """
        buf = b""
        while True:
            try:
                byte = self._recv_byte(sock)
            except TimeoutError:
                continue
            if byte is None:
                break
            if byte == b"\r":
                if echo:
                    sock.sendall(b"\r\n")
                # Consume trailing LF or NUL after CR (RFC 854).
                # Non-standard followers are discarded for simplicity;
                # in practice, clients always send CR LF or CR NUL.
                try:
                    self._recv_byte(sock)
                except TimeoutError:
                    pass
                break
            if byte == b"\n":
                if echo:
                    sock.sendall(b"\r\n")
                break
            if echo:
                sock.sendall(byte)
            buf += byte
        return buf.decode("utf-8", errors="replace")

    def _authenticate(self, sock: socket.socket) -> bool:
        """
        Perform username/password authentication over the Telnet connection.

        :param sock: client socket
        :return: True if authentication succeeded
        """
        sock.sendall(b"Username: ")
        username = self._read_line(sock, echo=True)
        sock.sendall(b"Password: ")
        password = self._read_line(sock, echo=False)
        sock.sendall(b"\r\n")
        return username == self.username and password == self.password

    # ------------------------------------------------------------------
    # Tap functions (socket ↔ shell bridge)
    # ------------------------------------------------------------------

    def socket_to_shell_tap(
        self,
        sock: socket.socket,
        shell_stdin: TapIO,
        shell_replied_event: threading.Event,
        run_srv: threading.Event,
    ) -> None:
        """Read bytes from socket and forward complete lines to shell stdin."""
        buffer: io.BytesIO = io.BytesIO()
        while run_srv.is_set():
            try:
                byte = self._recv_byte(sock)
            except TimeoutError:
                continue
            except OSError:
                log.error("telnet_server.socket_to_shell_tap socket read error")
                break

            # EOF / connection closed
            if byte is None:
                break

            # Drop NUL bytes completely
            if byte == b"\x00":
                continue

            shell_replied_event.wait(10)

            try:
                if byte in (b"\r", b"\n"):
                    sock.sendall(b"\r\n")
                    log.debug("telnet_server.socket_to_shell_tap echoing newline to socket")
                    buffer.write(byte)
                    buffer.seek(0)
                    line = buffer.read().decode(encoding="utf-8")
                    buffer.seek(0)
                    buffer.truncate()
                    log.debug(
                        "telnet_server.socket_to_shell_tap sending line to shell: %s",
                        [line],
                    )
                    shell_stdin.write(line)
                    shell_replied_event.clear()
                else:
                    sock.sendall(byte)
                    log.debug(
                        "telnet_server.socket_to_shell_tap echoing byte to socket: %s",
                        [byte],
                    )
                    buffer.write(byte)
                time.sleep(0.01)
            except OSError as e:
                log.error("telnet_server.socket_to_shell_tap socket write error: %s", e)
                break

        # Signal all threads to stop
        run_srv.clear()

    def shell_to_socket_tap(
        self,
        sock: socket.socket,
        shell_stdout: TapIO,
        shell_replied_event: threading.Event,
        run_srv: threading.Event,
    ) -> None:
        """Read lines from shell stdout and send them to the socket."""
        while run_srv.is_set():
            line = shell_stdout.readline()
            if line is None:
                break
            if "\x00" in line:
                line = line.replace("\x00", "")
            if "\r\n" not in line and "\n" in line:
                line = line.replace("\n", "\r\n")
            log.debug("telnet_server.shell_to_socket_tap sending line to socket: %s", [line])
            try:
                sock.sendall(line.encode(encoding="utf-8"))
            except OSError as e:
                log.error("telnet_server.shell_to_socket_tap socket write error: %s", e)
                break
            shell_replied_event.set()

        # Signal all threads to stop
        run_srv.clear()

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
            time.sleep(min(self.watchdog_interval, _SHUTDOWN_TIMEOUT))
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
            # A short blocking timeout is used instead of non-blocking mode
            # so that multi-byte IAC sequences split across TCP segments
            # are received completely rather than raising mid-sequence.
            time.sleep(0.1)
            client.settimeout(_IAC_DRAIN_TIMEOUT)
            try:
                while True:
                    if self._recv_byte(client) is None:
                        break  # EOF — client disconnected
            except TimeoutError:
                pass  # No more data available — expected
            finally:
                client.settimeout(self.timeout)

            # Send banner
            if self.banner:
                client.sendall((self.banner + "\r\n").encode("utf-8"))

            # Authenticate
            try:
                auth_ok = self._authenticate(client)
            except (TimeoutError, OSError):
                log.debug("Client disconnected during authentication")
                return
            if not auth_ok:
                log.warning("Telnet authentication failed, closing connection")
                client.sendall(b"Authentication failed.\r\n")
                return

            # Create stdio for the shell
            shell_stdin, shell_stdout = TapIO(run_srv), TapIO(run_srv)

            # Start socket→shell tap thread
            socket_to_shell_tapper = threading.Thread(
                target=self.socket_to_shell_tap,
                args=(client, shell_stdin, shell_replied_event, run_srv),
                daemon=True,
            )
            socket_to_shell_tapper.start()

            # Start shell→socket tap thread
            shell_to_socket_tapper = threading.Thread(
                target=self.shell_to_socket_tap,
                args=(client, shell_stdout, shell_replied_event, run_srv),
                daemon=True,
            )
            shell_to_socket_tapper.start()

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
