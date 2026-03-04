"""
This module implements an SSH server done using
paramiko as the SSH connection library.
"""

import io
import logging
import socket
import threading
import time
from typing import Any

import paramiko
import paramiko.channel
import paramiko.rsakey

from simnos.core.nos import Nos
from simnos.core.servers import TCPServerBase
from simnos.plugins.servers.tap_io import TapIO

log = logging.getLogger(__name__)

# Bounded timeout (seconds) for shutdown-critical paths: SSH handshake, accept,
# and watchdog sleep cap.  Kept short so that stop() converges quickly even when
# user-configured self.timeout is large.
_SHUTDOWN_TIMEOUT = 2

# DH Group Exchange algorithms to disable when server moduli are unavailable.
# Workaround for Paramiko server-mode bug where GEX algorithms are advertised
# in KEXINIT despite the server being unable to handle them without moduli,
# causing MessageOrderError when a client selects GEX.
_DISABLED_GEX_ALGORITHMS = {
    "kex": [
        "diffie-hellman-group-exchange-sha256",
        "diffie-hellman-group-exchange-sha1",
    ]
}


class ParamikoSshServerInterface(paramiko.ServerInterface):
    """
    Class to implement the SSH server interface
    using paramiko as the SSH connection library.
    """

    def __init__(
        self,
        ssh_banner: str = "SIMNOS Paramiko SSH Server",
        username: str | None = None,
        password: str | None = None,
        allow_auth_none: bool = False,
        authorized_keys: set[tuple[str, str]] | None = None,
    ):
        self.ssh_banner = ssh_banner
        self.username = username
        self.password = password
        self.allow_auth_none = allow_auth_none
        self.authorized_keys = authorized_keys
        self.auth_method_used: str | None = None

    def check_channel_request(self, kind, chanid):
        """
        This will allow the SSH server to provide a channel for the client
        to communicate over. By default, this will return
        OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED, so we have to override it
        to return OPEN_SUCCEEDED when the kind of channel
        requested is "session".
        """
        if kind == "session":
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_channel_pty_request(self, channel, term, width, height, pixelwidth, pixelheight, modes):
        """
        AFAIK, pty (pseudo-tty (TeleTYpewriter))
        will allow our client to interact with our shell.
        """
        return True

    def check_channel_shell_request(self, channel):
        """
        This allows us to provide the channel
        with a shell we can connect to it.
        """
        return True

    def get_allowed_auths(self, username):
        """Return the authentication methods supported by this server."""
        methods = "password,keyboard-interactive"
        if self.authorized_keys:
            methods = "publickey," + methods
        if self.allow_auth_none:
            methods = "none," + methods
        return methods

    def check_auth_none(self, username):
        """Allow auth_none if configured (e.g. for Dell PowerConnect)."""
        if self.allow_auth_none:
            self.auth_method_used = "none"
            return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_FAILED

    def check_auth_publickey(self, username, key):
        """Validate public key authentication."""
        if not self.authorized_keys:
            return paramiko.AUTH_FAILED
        if not self._match_username(username):
            return paramiko.AUTH_FAILED
        if (key.get_name(), key.get_base64()) in self.authorized_keys:
            self.auth_method_used = "publickey"
            return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_FAILED

    def _match_username(self, username: str) -> bool:
        """Check whether *username* matches the configured username.

        Tries an exact match first.  If that fails, strips a MikroTik-style
        ``+`` suffix (e.g. ``admin+ct511w4098h``) and retries so that
        usernames containing ``+`` as a legitimate character are never
        falsely truncated.
        """
        if username == self.username:
            return True
        base, sep, _ = username.partition("+")
        return bool(sep) and base == self.username

    def check_auth_password(self, username, password):
        """Validate username/password for standard password authentication."""
        if self._match_username(username) and (password == self.password):
            self.auth_method_used = "password"
            return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_FAILED

    def check_auth_interactive(self, username, submethods):
        """Begin keyboard-interactive authentication by sending a password prompt."""
        if self._match_username(username):
            query = paramiko.InteractiveQuery()
            query.add_prompt("Password: ", echo=False)
            return query
        return paramiko.AUTH_FAILED

    def check_auth_interactive_response(self, responses):
        """Validate the password response from keyboard-interactive authentication."""
        if len(responses) == 1 and responses[0] == self.password:
            self.auth_method_used = "keyboard-interactive"
            return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_FAILED

    def get_banner(self):
        """
        String that will display when a client connects,
        before authentication has happened. This is different
        than the shell's intro property, which is displayed
        after the authentication.
        """
        return (self.ssh_banner + "\r\n", "en-US")


def channel_to_shell_tap(channel_stdio, shell_stdin, shell_replied_event, run_srv):
    """
    Method to tap into the channel_stdio and send it to the shell
    """
    buffer: io.BytesIO = io.BytesIO()
    while run_srv.is_set():
        try:
            byte: bytes = channel_stdio.read(1)
        except TimeoutError:
            continue
        except (OSError, EOFError):
            log.debug("ssh_server.channel_to_shell_tap channel read closed")
            break
        log.debug("ssh_server.channel_to_shell_tap received from channel: %s", [byte])

        # EOF / channel closed
        if byte in (b"", None):
            break

        # Drop NUL bytes completely (don't echo, don't buffer)
        if byte == b"\x00":
            continue

        # Wait for the shell to reply, but check run_srv periodically
        # so that shutdown is not blocked for the full wait duration.
        while not shell_replied_event.wait(timeout=_SHUTDOWN_TIMEOUT):
            if not run_srv.is_set():
                break
        if not channel_stdio.channel.active:
            log.error("SSH channel is not active. Exiting.")
            break
        try:
            if byte in (b"\r", b"\n"):
                channel_stdio.write(b"\r\n")
                log.debug(
                    "ssh_server.channel_to_shell_tap echoing new line to channel: %s",
                    [b"\r\n"],
                )
                buffer.write(byte)
                buffer.seek(0)
                line = buffer.read().decode(encoding="utf-8")
                buffer.seek(0)
                buffer.truncate()
                log.debug("ssh_server.channel_to_shell_tap sending line to shell: %s", [line])
                shell_stdin.write(line)
                shell_replied_event.clear()
            else:
                channel_stdio.write(byte)
                log.debug(
                    "ssh_server.channel_to_shell_tap echoing byte to channel: %s",
                    [byte],
                )
                buffer.write(byte)
            time.sleep(0.01)
        except (OSError, EOFError) as e:
            log.error("ssh_server.channel_to_shell_tap channel write error: %s", e)
            break

    run_srv.clear()


def shell_to_channel_tap(
    channel_stdio: paramiko.channel.ChannelFile,
    shell_stdout: TapIO,
    shell_replied_event: threading.Event,
    run_srv: threading.Event,
):
    """
    Method to tap into the shell_stdout and send it to the channel
    """
    while run_srv.is_set():
        if channel_stdio.closed:
            break
        line = shell_stdout.readline()
        if line is None:
            break
        if "\x00" in line:
            line = line.replace("\x00", "")
        if "\r\n" not in line and "\n" in line:
            line = line.replace("\n", "\r\n")
        log.debug("ssh_server.shell_to_channel_tap sending line to channel %s", [line])
        written = False
        while run_srv.is_set() and not written:
            try:
                channel_stdio.write(line.encode(encoding="utf-8"))
                written = True
            except TimeoutError:
                log.debug("ssh_server.shell_to_channel_tap write timeout, retrying")
                continue
            except (OSError, EOFError) as e:
                log.error("ssh_server.shell_to_channel_tap channel write error: %s", e)
                break
        if not written:
            break
        shell_replied_event.set()

    run_srv.clear()


class ParamikoSshServer(TCPServerBase):
    """
    Class to implement an SSH server using paramiko
    as the SSH connection library.
    """

    _moduli_loaded: bool | None = None
    _default_key: paramiko.rsakey.RSAKey | None = None
    _default_key_lock: threading.Lock = threading.Lock()
    _KNOWN_KEY_TYPES = (
        "ssh-rsa",
        "ssh-ed25519",
        "ssh-dss",
        "ecdsa-sha2-",
        "sk-ssh-ed25519",
        "sk-ecdsa-sha2-",
    )

    def __init__(
        self,
        shell: type,
        nos: Nos,
        nos_inventory_config: dict,
        port: int,
        username: str,
        password: str,
        ssh_key_file: str | None = None,
        ssh_key_file_password: str | None = None,
        ssh_banner: str = "SIMNOS Paramiko SSH Server",
        shell_configuration: dict | None = None,
        address: str = "127.0.0.1",
        timeout: int = 1,
        watchdog_interval: float = 1,
        authorized_keys: str | None = None,
    ):
        super().__init__(address=address, port=port, timeout=timeout)

        self.nos: Nos = nos
        self.nos_inventory_config: dict = nos_inventory_config
        self.shell: type = shell
        self.shell_configuration: dict = shell_configuration or {}
        self.ssh_banner: str = ssh_banner
        self.username: str = username
        self.password: str = password
        self.watchdog_interval: float = watchdog_interval
        self._authorized_keys = self._load_authorized_keys(authorized_keys) if authorized_keys else None

        if ssh_key_file:
            self._ssh_server_key: paramiko.rsakey.RSAKey = paramiko.RSAKey.from_private_key_file(
                ssh_key_file, ssh_key_file_password
            )
        else:
            with ParamikoSshServer._default_key_lock:
                if ParamikoSshServer._default_key is None:
                    ParamikoSshServer._default_key = paramiko.RSAKey.generate(2048)
            self._ssh_server_key = ParamikoSshServer._default_key
            log.warning(
                "Using auto-generated SSH host key. This key is not persisted and "
                "will change on restart. Provide a custom key via ssh_key_file "
                "for non-local use."
            )

        # Load SSH moduli once for DH Group Exchange support in server mode.
        # Result is cached at the class level so subsequent instances skip the file I/O.
        if ParamikoSshServer._moduli_loaded is None:
            ParamikoSshServer._moduli_loaded = paramiko.Transport.load_server_moduli()

    @staticmethod
    def _load_authorized_keys(path: str) -> set[tuple[str, str]]:
        """Parse an OpenSSH authorized_keys file.

        Supports bare key lines and lines with leading options.
        Skips comment lines, blank lines, and @marker lines.
        File not found / permission errors propagate as-is (fail-fast).

        Returns a set of (key_type, base64_data) tuples.
        """
        keys: set[tuple[str, str]] = set()
        with open(path) as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("@"):
                    log.warning("Skipping unsupported marker line: %s", line)
                    continue
                parts = line.split()
                for i, part in enumerate(parts):
                    if any(part.startswith(prefix) for prefix in ParamikoSshServer._KNOWN_KEY_TYPES):
                        if i + 1 < len(parts):
                            keys.add((part, parts[i + 1]))
                        else:
                            log.warning("Key type found but base64 data missing, skipping line: %s", line)
                        break
                else:
                    log.warning("No known key type found, skipping line: %s", line)
        return keys

    def watchdog(
        self,
        is_running: threading.Event,
        run_srv: threading.Event,
        session: paramiko.Transport,
        shell: Any,
    ):
        """
        Method to monitor server liveness and recover where possible.
        """
        while run_srv.is_set():
            if not session.is_alive():
                log.warning("ParamikoSshServer.watchdog - session not alive, stopping shell")
                break

            if not is_running.is_set():
                break

            time.sleep(min(self.watchdog_interval, _SHUTDOWN_TIMEOUT))

        shell.stop()

    def _read_channel_line(self, channel, echo: bool = True) -> str:
        """
        Read a single line from the channel byte-by-byte.

        :param channel: paramiko Channel
        :param echo: if True, echo each byte back to the client
        :return: the line read (without trailing CR/LF)
        """
        channel.settimeout(self.timeout)
        buf = b""
        while True:
            try:
                byte = channel.recv(1)
            except TimeoutError:
                continue
            if byte in (b"", None):
                break
            if byte in (b"\r", b"\n"):
                if echo:
                    channel.sendall(b"\r\n")
                break
            if echo:
                channel.sendall(byte)
            buf += byte
        return buf.decode("utf-8", errors="replace")

    def _channel_login(self, channel) -> bool:
        """
        Perform channel-level login for auth_none platforms (e.g. Dell PowerConnect).

        Sends "User Name:" / "Password:" prompts and validates credentials.

        :param channel: paramiko Channel
        :return: True if login succeeded, False otherwise
        """
        channel.sendall(b"\r\nUser Name:")
        username = self._read_channel_line(channel, echo=True)
        channel.sendall(b"\r\nPassword:")
        password = self._read_channel_line(channel, echo=False)
        channel.sendall(b"\r\n")

        if username == self.username and password == self.password:
            log.debug("Channel login succeeded for user %s", username)
            return True

        log.warning("Channel login failed for user %s", username)
        return False

    def connection_function(self, client: socket.socket, is_running: threading.Event):
        shell_replied_event = threading.Event()
        run_srv = threading.Event()
        run_srv.set()

        # determine if this NOS requires auth_none
        allow_auth_none = getattr(self.nos, "auth", None) == "none"

        # create the SSH transport object
        session = paramiko.Transport(client)
        if not self._moduli_loaded:
            session.disabled_algorithms = _DISABLED_GEX_ALGORITHMS
        session.add_server_key(self._ssh_server_key)
        session.banner_timeout = _SHUTDOWN_TIMEOUT
        session.handshake_timeout = _SHUTDOWN_TIMEOUT

        try:
            # create the server
            server = ParamikoSshServerInterface(
                ssh_banner=self.ssh_banner,
                username=self.username,
                password=self.password,
                allow_auth_none=allow_auth_none,
                authorized_keys=self._authorized_keys,
            )

            # start the SSH server — may raise SSHException if the client
            # disconnects during handshake or if stop() races with accept.
            try:
                session.start_server(server=server)
            except paramiko.SSHException as e:
                log.debug("SSH handshake failed (likely client disconnect or stop): %s", e)
                return

            # create the channel and get the stdio
            channel = None
            while channel is None and is_running.is_set() and session.is_alive():
                channel = session.accept(_SHUTDOWN_TIMEOUT)
            if channel is None:
                log.warning("session.accept() returned None or server stopping, closing transport")
                return

            # For auth_none platforms (e.g. Dell PowerConnect), perform channel-level
            # login before starting the shell.  When publickey auth is also configured,
            # clients that authenticate via publickey bypass this channel-level login
            # intentionally — SSH-level publickey auth already verified the identity.
            if server.auth_method_used == "none" and not self._channel_login(channel):
                log.warning("Channel login failed, closing connection")
                return

            channel.settimeout(self.timeout)
            channel_stdio = channel.makefile("rw")

            # create stdio for the shell
            shell_stdin, shell_stdout = TapIO(run_srv), TapIO(run_srv)

            # start intermediate thread to tap into
            # the channel_stdio->shell_stdin bytes stream
            channel_to_shell_tapper = threading.Thread(
                target=channel_to_shell_tap,
                args=(channel_stdio, shell_stdin, shell_replied_event, run_srv),
                daemon=True,
            )
            channel_to_shell_tapper.start()

            # start intermediate thread to tap into
            # the shell_stdout->channel_stdio bytes stream
            shell_to_channel_tapper = threading.Thread(
                target=shell_to_channel_tap,
                args=(channel_stdio, shell_stdout, shell_replied_event, run_srv),
                daemon=True,
            )
            shell_to_channel_tapper.start()

            # create the client shell
            client_shell = self.shell(
                stdin=shell_stdin,
                stdout=shell_stdout,
                nos=self.nos,
                nos_inventory_config=self.nos_inventory_config,
                is_running=is_running,
                **self.shell_configuration,
            )

            # start watchdog thread
            watchdog_thread = threading.Thread(
                target=self.watchdog, args=(is_running, run_srv, session, client_shell), daemon=True
            )
            watchdog_thread.start()

            # running this command will block this function until shell exits
            client_shell.start()
            log.debug("ParamikoSshServer.connection_function stopped shell thread")

        finally:
            # Stop all server threads
            run_srv.clear()
            log.debug("ParamikoSshServer.connection_function stopped server threads")

            session.close()
            log.debug("ParamikoSshServer.connection_function closed transport %s", session)
