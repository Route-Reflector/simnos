"""
This module implements an SSH server done using
paramiko as the SSH connection library.
"""

import io
import logging
from pathlib import Path
import socket
import threading
from typing import TYPE_CHECKING

import paramiko
import paramiko.rsakey

from simnos.core.nos import Nos
from simnos.core.servers import TCPServerBase
from simnos.core.timeouts import SHUTDOWN_IO_TIMEOUT
from simnos.plugins.servers.tap_bridge import (
    interactive_login,
    run_push_session,
)

if TYPE_CHECKING:
    from simnos.core.host import HostRenderConfig

log = logging.getLogger(__name__)

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

# Path to bundled moduli file (concatenated 2048 + 3072 + 4096-bit primes).
# Used as fallback when no system moduli (e.g. /etc/ssh/moduli) is available
# — typically on Windows / macOS hosts.
# See docs/development/regenerate_moduli.md for the rotation procedure.
_BUNDLED_MODULI = Path(__file__).parent / "moduli"


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


class ParamikoChannelAdapter:
    """TransportAdapter implementation wrapping a paramiko Channel (G3 / #225).

    Used by the shared tap functions in tap_bridge; keeps all paramiko
    specifics (exception types, channel liveness flags) in this module.
    """

    io_errors = (OSError, EOFError, paramiko.SSHException)
    nul_resets_skip_lf = False  # SSH has no CR NUL convention (RFC 854 is Telnet-only)
    name = "ssh"

    def __init__(self, channel: paramiko.Channel):
        self._channel = channel

    def recv_byte(self) -> bytes | None:
        byte = self._channel.recv(1)
        return byte if byte else None  # normalize b"" (EOF) to None

    def sendall(self, data: bytes) -> None:
        self._channel.sendall(data)

    def is_closed(self) -> bool:
        # Known-dead early check: closed channel or dead transport.
        # channel.active also reflects peer-side EOF paramiko already knows;
        # authoritative peer-disconnect detection stays recv/send based.
        return self._channel.closed or not self._channel.active


class ParamikoSshServer(TCPServerBase):
    """
    Class to implement an SSH server using paramiko
    as the SSH connection library.
    """

    _moduli_loaded: bool | None = None
    _moduli_lock: threading.Lock = threading.Lock()
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
        render_config: "HostRenderConfig | None" = None,
    ):
        super().__init__(address=address, port=port, timeout=timeout)

        self.nos: Nos = nos
        self.nos_inventory_config: dict = nos_inventory_config
        self.shell: type = shell
        self.shell_configuration: dict = shell_configuration or {}
        # Per-host overlay/render config (#286), carried to every connection's shell.
        self._render_config: HostRenderConfig | None = render_config
        # Normalize the merged command platform once, here at Host.start, instead
        # of per connection: it is per-host invariant (#264 / Impact). This also
        # surfaces malformed inventory/data at startup rather than on the first
        # connection. Optional so a shell without the hook still self-builds.
        build_shared = getattr(self.shell, "build_shared_platform", None)
        self._shared_platform = build_shared(nos, self.nos_inventory_config, render_config) if build_shared else None
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

        # Load SSH moduli once for DH Group Exchange (GEX) support in server mode.
        # Prefer system moduli (live, distro-rotated) when available; fall back to
        # the moduli file bundled with the package on hosts without /etc/ssh/moduli
        # (Windows / macOS). Result is cached at the class level under a lock.
        #
        # `_moduli_lock` only serializes SIMNOS-internal init; the underlying
        # `paramiko.Transport._modulus_pack` is a paramiko-global state and is
        # not lockable from here. If another thread loads moduli via paramiko
        # directly (outside SIMNOS), it can still race. Mirrors the
        # `_default_key_lock` pattern in scope, not in coverage.
        with ParamikoSshServer._moduli_lock:
            if ParamikoSshServer._moduli_loaded is None:
                ok = paramiko.Transport.load_server_moduli()
                if not ok:
                    # `is_file()` returns False for missing path, directory, or
                    # broken symlink. The latter two are extreme edge cases for
                    # a package-bundled file; treating them as "missing" is fine.
                    if _BUNDLED_MODULI.is_file():
                        ok = paramiko.Transport.load_server_moduli(filename=str(_BUNDLED_MODULI))
                        if not ok:
                            log.error(
                                "Bundled moduli at %s exists but failed to load "
                                "(possibly corrupted or unreadable). Falling back "
                                "to GEX-disable workaround.",
                                _BUNDLED_MODULI,
                            )
                    else:
                        log.error(
                            "Bundled moduli file missing at %s — falling back to "
                            "GEX-disable workaround. This indicates a packaging "
                            "regression, please report.",
                            _BUNDLED_MODULI,
                        )
                ParamikoSshServer._moduli_loaded = ok

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

    def _channel_login(self, channel) -> tuple[bool, bool]:
        """
        Perform channel-level login for auth_none platforms (e.g. Dell PowerConnect).

        Thin wrapper around tap_bridge.interactive_login supplying the
        Dell-style prompts; the interaction itself is shared with Telnet.
        Expects the channel timeout to be configured by the caller
        (connection_function) beforehand.

        :param channel: paramiko Channel
        :return: (authenticated, skip_lf) — skip_lf should be forwarded to
                 client_to_shell_tap so it can consume a trailing LF after
                 the final CR of the password line.
        """
        return interactive_login(
            ParamikoChannelAdapter(channel),
            self.username,
            self.password,
            user_prompt=b"\r\nUser Name:",
            pass_prompt=b"\r\nPassword:",
        )

    def connection_function(self, client: socket.socket, is_running: threading.Event):
        # determine if this NOS requires auth_none
        allow_auth_none = getattr(self.nos, "auth", None) == "none"

        # create the SSH transport object
        session = paramiko.Transport(client)
        if not ParamikoSshServer._moduli_loaded:
            session.disabled_algorithms = _DISABLED_GEX_ALGORITHMS
        session.add_server_key(self._ssh_server_key)
        session.banner_timeout = SHUTDOWN_IO_TIMEOUT
        session.handshake_timeout = SHUTDOWN_IO_TIMEOUT

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

            # wait for the client to open a channel
            channel = None
            while channel is None and is_running.is_set() and session.is_alive():
                channel = session.accept(SHUTDOWN_IO_TIMEOUT)
            if channel is None:
                log.warning("session.accept() returned None or server stopping, closing transport")
                return

            # Timeout responsibility lives here (not in the adapter / shared
            # helpers): configure it before any channel I/O below.
            channel.settimeout(self.timeout)

            # For auth_none platforms (e.g. Dell PowerConnect), perform channel-level
            # login before starting the shell.  When publickey auth is also configured,
            # clients that authenticate via publickey bypass this channel-level login
            # intentionally — SSH-level publickey auth already verified the identity.
            skip_lf = False
            if server.auth_method_used == "none":
                try:
                    authenticated, skip_lf = self._channel_login(channel)
                except (TimeoutError, OSError, EOFError, paramiko.SSHException):
                    log.debug("Client disconnected during channel login")
                    return
                if not authenticated:
                    log.warning("Channel login failed, closing connection")
                    return

            # bridge the channel and the shell through the push session driver
            transport_adapter = ParamikoChannelAdapter(channel)

            # Create the client shell. The push driver calls `shell.dispatch`
            # directly (W3, #297); cmd.Cmd's stdin/stdout are vestigial on this
            # path (no cmdloop), so they are stub StringIO streams. `is_running`
            # is the server-level run flag the dispatch core and the session
            # loop both observe for shutdown.
            client_shell = self.shell(
                stdin=io.StringIO(),
                stdout=io.StringIO(),
                nos=self.nos,
                nos_inventory_config=self.nos_inventory_config,
                is_running=is_running,
                resolved_platform=self._shared_platform,
                render_config=self._render_config,
                **self.shell_configuration,
            )

            # Drive the session on this connection thread: read -> echo ->
            # dispatch -> write. Blocks until the client disconnects, the shell
            # closes, or the server stops (channel recv timeout + is_running
            # re-check replace the old watchdog thread, §3).
            run_push_session(transport_adapter, client_shell, is_running, initial_skip_lf=skip_lf)
            log.debug("ParamikoSshServer.connection_function session ended")

        finally:
            session.close()
            log.debug("ParamikoSshServer.connection_function closed transport %s", session)
