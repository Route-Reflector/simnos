"""asyncssh-backed SSH server plugin (#297 Stage 2, §2).

The SSH server plugin (it replaced the former paramiko server in #297 Stage 4):
the ``__init__`` signature ``Host.start`` builds against, the NOS data / CMDShell /
render_config wiring, and the wire bytes (pinned by the byte-parity goldens) are
all transport-independent. The transport is asyncssh on the SimNOS-owned shared
event loop (:mod:`simnos.core.shared_loop`), one task per connection rather than a
thread per connection.

The spike (#296) proved the shape: asyncssh handles 100 concurrent connections at
the transport layer; the failures came from bridging a *blocking* shell loop per
session. So here each session is driven by :func:`run_async_push_session` (W3 push
dispatch), with only the blocking ``shell.dispatch`` off-loaded to the bounded
executor (§2a). No per-session thread.

The lifecycle (start/stop/aclose, late-acceptor reclaim, session registry, dispatch
wiring) lives in :class:`AsyncServerBase`, shared with the telnetlib3 ``TelnetServer``
(Stage 3); this module only supplies the SSH transport + auth.

GEX: asyncssh handles moduli itself, so the paramiko GEX workaround
(``_DISABLED_GEX_ALGORITHMS`` / bundled moduli) was removed wholesale with the
paramiko server in Stage 4.
"""

import asyncio
import logging
import threading
from typing import TYPE_CHECKING

import asyncssh

from simnos.core.nos import Nos
from simnos.plugins.servers.async_server_base import AsyncServerBase
from simnos.plugins.servers.async_session import async_interactive_login

if TYPE_CHECKING:
    from simnos.core.host import HostRenderConfig
    from simnos.core.simnos import SimNOS

log = logging.getLogger(__name__)


class AsyncSSHProcessTransport:
    """AsyncPushTransport over an asyncssh ``SSHServerProcess`` (binary channel).

    ``encoding=None`` makes the channel binary so the byte stream is byte-exact
    (pinned by the byte-parity goldens). The PTY signal events asyncssh surfaces
    from ``read`` (window resize,
    Ctrl-C/Break, soft EOF) are *not* disconnects, so ``recv`` swallows them and
    keeps reading — only a real EOF (``b""``) or an ``io_errors`` raise ends the
    session.
    """

    # Explicit annotation matches the invariant `AsyncPushTransport.io_errors`
    # protocol member type (`tuple[type[BaseException], ...]`); without it the
    # inferred narrow tuple type fails ty's protocol-conformance check (ty 0.0.55).
    io_errors: tuple[type[BaseException], ...] = (OSError, EOFError, ConnectionError, asyncssh.Error)
    nul_resets_skip_lf = False  # SSH has no CR NUL convention (RFC 854 is Telnet-only)
    name = "ssh"

    def __init__(self, process: "asyncssh.SSHServerProcess") -> None:
        self._process = process

    async def recv(self, n: int) -> bytes:
        while True:
            try:
                return await self._process.stdin.read(n)
            except (asyncssh.TerminalSizeChanged, asyncssh.SignalReceived, asyncssh.BreakReceived):
                continue  # PTY control event, not a disconnect — keep reading

    def send(self, data: bytes) -> None:
        self._process.stdout.write(data)

    async def drain(self) -> None:
        await self._process.stdout.drain()

    def page_rows(self) -> int | None:
        """Pty height for paging, or None when the client requested no pty (#307).

        No pty (``get_terminal_type()`` is None) → None → the gate is off and the
        driver never pages (exec-style / non-interactive clients). With a pty the
        reported height is returned as-is; a 0/unknown height is left for the
        driver's ``_resolve_rows`` to fall back to ``page_default_rows``.
        """
        if self._process.get_terminal_type() is None:
            return None
        # get_terminal_size() -> (width, height, pixwidth, pixheight).
        return self._process.get_terminal_size()[1]


class _SimnosSSHServer(asyncssh.SSHServer):
    """Connection-level SSH auth (§2).

    password / publickey / keyboard-interactive / none, plus MikroTik-style ``+``
    suffix username matching.

    publickey is advertised **only when authorized_keys is configured**. This
    matters for the asyncssh↔paramiko-client interop (#297 テーマE / E2): a paramiko
    client that fails one auth method and
    retries another resends ``SERVICE_REQUEST(ssh-userauth)``, which asyncssh
    rejects (``Unexpected service in service request``) — a hardcoded protocol
    check with no public-API override. So advertising publickey on a host with no
    keys would only lure a key-offering client (e.g. ansible's default probe) into
    that failing retry. Password-first clients (netmiko/scrapli) never retry and
    are unaffected; a key-offering client against simnos must use a non-paramiko
    backend (ansible → ansible-pylibssh).
    """

    def __init__(
        self,
        username: str,
        password: str,
        allow_auth_none: bool,
        authorized_keys: "set[bytes]",
        ssh_banner: str,
    ) -> None:
        self._username = username
        self._password = password
        self._allow_auth_none = allow_auth_none
        self._authorized_keys = authorized_keys
        self._ssh_banner = ssh_banner
        self._conn: asyncssh.SSHServerConnection | None = None
        self._banner_sent = False

    def connection_made(self, conn: "asyncssh.SSHServerConnection") -> None:
        self._conn = conn

    def begin_auth(self, username: str) -> bool:
        # Pre-auth banner (sent before authentication, distinct from the shell
        # intro): sent once at the start of auth, consumed by the client's auth handler
        # (so it never appears on the post-auth shell channel / byte-parity golden).
        if self._ssh_banner and not self._banner_sent and self._conn is not None:
            self._conn.send_auth_banner(f"{self._ssh_banner}\r\n", lang="en-US")
            self._banner_sent = True
        # False = no SSH-level auth required (auth_none platforms: the Dell-style
        # channel login then runs inside the session, see _handle_process).
        return not self._allow_auth_none

    def password_auth_supported(self) -> bool:
        return True

    def validate_password(self, username: str, password: str) -> bool:
        return self._match_username(username) and password == self._password

    def kbdint_auth_supported(self) -> bool:
        return True

    def get_kbdint_challenge(self, username: str, lang: str, submethods: str):
        # Single hidden Password prompt for keyboard-interactive auth. An unknown
        # user gets no challenge (False) so the method fails cleanly.
        if self._match_username(username):
            return "", "", "", (("Password: ", False),)
        return False

    def validate_kbdint_response(self, username: str, responses) -> bool:
        return len(responses) == 1 and responses[0] == self._password

    def public_key_auth_supported(self) -> bool:
        # Advertise publickey only when keys are configured; see the class
        # docstring for the auth-retry-disconnect rationale.
        return bool(self._authorized_keys)

    def validate_public_key(self, username: str, key) -> bool:
        if not self._authorized_keys or not self._match_username(username):
            return False
        return key.export_public_key("openssh").split()[1] in self._authorized_keys

    def _match_username(self, username: str) -> bool:
        if username == self._username:
            return True
        base, sep, _ = username.partition("+")
        return bool(sep) and base == self._username


class AsyncSshServer(AsyncServerBase):
    """asyncssh SSH server plugin on the SimNOS-owned shared loop (§1 / §2).

    The constructor signature ``Host.start`` builds against, plus a ``simnos`` back
    reference (added by ``Host.start``) so it can reach the shared loop. The generic
    lifecycle is in :class:`AsyncServerBase`; this class supplies the asyncssh
    listener + auth.
    """

    # In-band line editing is SSH-only (#303 P3-1): the binary push driver layers
    # cursor / history / backspace / Tab on interactive keystrokes. Telnet keeps the
    # base default (False). Scrapers never send editing keys, so the byte-parity
    # goldens are unaffected.
    _editing = True

    # One auto-generated RSA-2048 host key shared across the process (class-level,
    # regenerated each run).
    _default_key = None
    _default_key_lock = threading.Lock()

    def __init__(
        self,
        shell: type,
        nos: Nos,
        nos_inventory_config: dict,
        port: int,
        username: str,
        password: str,
        secret: str | None = None,
        ssh_key_file: str | None = None,
        ssh_key_file_password: str | None = None,
        ssh_banner: str = "SIMNOS AsyncSSH Server",
        shell_configuration: dict | None = None,
        address: str = "127.0.0.1",
        timeout: int = 1,
        watchdog_interval: float = 1,
        authorized_keys: str | None = None,
        render_config: "HostRenderConfig | None" = None,
        simnos: "SimNOS | None" = None,
        page_default_rows: int = 24,
        reload_lock: "threading.Lock | None" = None,
    ) -> None:
        super().__init__(
            shell,
            nos,
            nos_inventory_config,
            port,
            username,
            password,
            secret=secret,
            shell_configuration=shell_configuration,
            address=address,
            timeout=timeout,
            watchdog_interval=watchdog_interval,
            render_config=render_config,
            simnos=simnos,
            page_default_rows=page_default_rows,
            reload_lock=reload_lock,
        )
        self.ssh_banner: str = ssh_banner
        self._authorized_keys = self._load_authorized_keys(authorized_keys)
        self._host_key = self._get_host_key(ssh_key_file, ssh_key_file_password)
        # auth_none (Dell PowerConnect channel login): nos.auth == "none".
        self._allow_auth_none = getattr(nos, "auth", None) == "none"

    @staticmethod
    def _load_authorized_keys(path: str | None) -> "set[bytes]":
        """Parse an OpenSSH authorized_keys file into a set of base64 key blobs.

        Bare key lines; comment / blank / marker lines are skipped. Stored value =
        the base64 middle field of the OpenSSH line, matched in
        ``validate_public_key``.
        """
        keys: set[bytes] = set()
        if not path:
            return keys
        with open(path) as fh:
            for raw in fh:
                line = raw.strip()
                if not line or line.startswith(("#", "@")):
                    continue
                try:
                    key = asyncssh.import_public_key(line)
                    keys.add(key.export_public_key("openssh").split()[1])
                except (asyncssh.KeyImportError, ValueError, IndexError) as exc:
                    log.warning("Skipping unparseable authorized_keys line: %s", exc)
        return keys

    @classmethod
    def _get_host_key(cls, key_file: str | None, key_pw: str | None):
        if key_file:
            return asyncssh.read_private_key(key_file, key_pw)
        with cls._default_key_lock:
            if cls._default_key is None:
                cls._default_key = asyncssh.generate_private_key("ssh-rsa", key_size=2048)
                log.warning(
                    "Using auto-generated SSH host key. This key is not persisted and "
                    "will change on restart. Provide a custom key via ssh_key_file "
                    "for non-local use."
                )
        return cls._default_key

    # ------------------------------------------------------------------ hooks
    async def _create_listener(self) -> "asyncssh.SSHAcceptor":
        # Store on self before returning so _abort_failed_start can close it even
        # if start()'s result() already timed out (codex 1st#1).
        self._acceptor = await asyncssh.create_server(
            lambda: _SimnosSSHServer(
                self.username, self.password, self._allow_auth_none, self._authorized_keys, self.ssh_banner
            ),
            self.address,
            self.port,
            server_host_keys=[self._host_key],
            encoding=None,  # binary channel → byte-exact wire (pinned by the goldens)
            process_factory=self._handle_process,
            allow_pty=True,
            # Restart-friendly bind: SO_REUSEADDR alone covers stop→start
            # EADDRINUSE (listening sockets do not enter TIME_WAIT). SO_REUSEPORT
            # was dropped (#347): it let a second SIMNOS instance bind the SAME
            # port with no error, and the kernel then load-balanced incoming
            # connections between the two — a silent double-start that bypassed
            # the #271 port-collision hardening. Now the second bind fails loud.
            reuse_address=True,
        )
        # Read back the bound port so port=0 (ephemeral, #271) resolves to the real
        # OS-assigned port. Done here on the loop thread (the create coroutine), so
        # the start thread never touches the socket. A fixed port reads back its own
        # value (no-op). `host.port` picks this up after start (Host.start / D4).
        self.port = self._acceptor.get_port()
        return self._acceptor  # SSHAcceptor satisfies the Listener protocol

    def _close_session(self, session: object) -> None:
        session.close()  # ty: ignore[unresolved-attribute]  # session is an SSHServerProcess

    # ------------------------------------------------------------------ per-session
    async def _handle_process(self, process: "asyncssh.SSHServerProcess") -> None:
        """asyncssh process handler: one interactive shell session (§3a).

        Per-connection handler (async): optional auth_none channel login, then the
        push session driving ``shell.dispatch`` via the bounded executor. asyncssh
        closes ``process`` when this returns.
        """
        if self._bow_out_if_closing(process):
            return
        async with self._session_scope(process):
            transport = AsyncSSHProcessTransport(process)
            try:
                skip_lf = False
                if self._allow_auth_none:
                    try:
                        authenticated, skip_lf = await async_interactive_login(
                            transport,
                            self.username,
                            self.password,
                            user_prompt=b"\r\nUser Name:",
                            pass_prompt=b"\r\nPassword:",
                        )
                    except (OSError, asyncssh.Error) as exc:
                        log.debug("auth_none channel login error: %s", exc)
                        return
                    if not authenticated:
                        log.warning("auth_none channel login failed, closing session")
                        return

                await self._drive_session(transport, skip_lf=skip_lf)
            except asyncio.CancelledError:
                raise
            except Exception:
                # A session-level crash must not take down the loop; log + tear down
                # this session only (§3a observability, #294-aligned).
                log.exception("AsyncSshServer session crashed")
