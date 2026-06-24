"""asyncssh-backed SSH server plugin (#297 Stage 2, §2).

Drop-in replacement for :class:`ParamikoSshServer`: the same ``__init__``
signature so ``Host.start`` builds it identically, the same NOS data / CMDShell /
render_config, the same wire bytes (pinned by the byte-parity goldens). Only the
transport differs — asyncssh on the SimNOS-owned shared event loop
(:mod:`simnos.core.shared_loop`) instead of a paramiko thread per connection.

The spike (#296) proved the shape: asyncssh handles 100 concurrent connections at
the transport layer; the failures came from bridging a *blocking* shell loop per
session. So here each session is driven by :func:`run_async_push_session` (W3 push
dispatch), with only the blocking ``shell.dispatch`` off-loaded to the bounded
executor (§2a). No per-session thread.

GEX: asyncssh handles moduli itself, so the paramiko GEX workaround
(``_DISABLED_GEX_ALGORITHMS`` / bundled moduli) is not referenced on this path
(removed wholesale in Stage 4).
"""

import asyncio
import contextlib
import io
import logging
import sys
import threading
from typing import TYPE_CHECKING

import asyncssh

from simnos.core.nos import Nos
from simnos.core.timeouts import SHUTDOWN_IO_TIMEOUT
from simnos.plugins.servers.async_session import (
    async_interactive_login,
    run_async_push_session,
)

if TYPE_CHECKING:
    from simnos.core.host import HostRenderConfig
    from simnos.core.shared_loop import SharedLoop
    from simnos.core.simnos import SimNOS

log = logging.getLogger(__name__)

#: Per-host listener creation budget (seconds): create_server runs on the shared
#: loop and is awaited synchronously by start() (parity with paramiko bind).
_CREATE_SERVER_TIMEOUT = 30


class AsyncSSHProcessTransport:
    """AsyncPushTransport over an asyncssh ``SSHServerProcess`` (binary channel).

    ``encoding=None`` makes the channel binary so the byte stream matches paramiko
    exactly. The PTY signal events asyncssh surfaces from ``read`` (window resize,
    Ctrl-C/Break, soft EOF) are *not* disconnects, so ``recv`` swallows them and
    keeps reading — only a real EOF (``b""``) or an ``io_errors`` raise ends the
    session.
    """

    io_errors = (OSError, EOFError, ConnectionError, asyncssh.Error)
    nul_resets_skip_lf = False  # SSH has no CR NUL convention (parity with paramiko adapter)
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


class _SimnosSSHServer(asyncssh.SSHServer):
    """Connection-level auth (parity with ``ParamikoSshServerInterface``, §2).

    password / publickey / keyboard-interactive / none, plus MikroTik-style ``+``
    suffix username matching.

    publickey is advertised **only when authorized_keys is configured** — the same
    rule as paramiko's ``get_allowed_auths`` (which prepends ``publickey`` only
    when keys are loaded). This matters for the asyncssh↔paramiko-client
    interop (#297 テーマE / E2): a paramiko client that fails one auth method and
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
    ) -> None:
        self._username = username
        self._password = password
        self._allow_auth_none = allow_auth_none
        self._authorized_keys = authorized_keys

    def begin_auth(self, username: str) -> bool:
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
        # Single hidden Password prompt (parity with the paramiko
        # keyboard-interactive InteractiveQuery). An unknown user gets no
        # challenge (False) so the method fails cleanly.
        if self._match_username(username):
            return "", "", "", (("Password: ", False),)
        return False

    def validate_kbdint_response(self, username: str, responses) -> bool:
        return len(responses) == 1 and responses[0] == self._password

    def public_key_auth_supported(self) -> bool:
        # Advertise publickey only when keys are configured (paramiko parity); see
        # the class docstring for the auth-retry-disconnect rationale.
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


class AsyncSshServer:
    """asyncssh SSH server plugin on the SimNOS-owned shared loop (§1 / §2).

    Same constructor signature as ``ParamikoSshServer`` plus a ``simnos`` back
    reference (added by ``Host.start``) so it can reach the shared loop. Not a
    ``TCPServerBase`` — listening + sessions live on the shared asyncio loop, not
    a thread per connection. ``managed_threads`` is empty: the loop thread is a
    SimNOS-scoped resource joined once by ``SimNOS.stop()`` (Decision 2).
    """

    # One auto-generated RSA-2048 host key per process (parity with paramiko's
    # shared _default_key: same alg + size, so KEX cost is comparable).
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
    ) -> None:
        self.nos: Nos = nos
        self.nos_inventory_config: dict = nos_inventory_config
        self.shell: type = shell
        self.shell_configuration: dict = shell_configuration or {}
        self._render_config: HostRenderConfig | None = render_config
        # Normalize the merged platform once at Host.start (per-host invariant,
        # surfaces malformed data at startup) — parity with ParamikoSshServer.
        build_shared = getattr(self.shell, "build_shared_platform", None)
        self._shared_platform = build_shared(nos, self.nos_inventory_config, render_config) if build_shared else None
        self.ssh_banner: str = ssh_banner
        self.username: str = username
        self.password: str = password
        self.address: str = address
        self.port: int = port
        self.timeout: int = timeout
        self.watchdog_interval: float = watchdog_interval
        self._simnos = simnos
        self._authorized_keys = self._load_authorized_keys(authorized_keys)
        self._host_key = self._get_host_key(ssh_key_file, ssh_key_file_password)
        # auth_none (Dell PowerConnect channel login): nos.auth == "none"
        # (parity with ParamikoSshServer.connection_function).
        self._allow_auth_none = getattr(nos, "auth", None) == "none"

        self._shared_loop: SharedLoop | None = None
        self._acceptor: asyncssh.SSHAcceptor | None = None
        # Per-server run flag the shells observe: cleared on stop so an in-flight
        # dispatch returns close (cooperative stop, §1a).
        self._is_running = threading.Event()
        # Active sessions, drained on aclose (§1a host-scope 5a).
        self._processes: set[asyncssh.SSHServerProcess] = set()
        self._tasks: set = set()

    @property
    def managed_threads(self) -> list[threading.Thread]:
        """No SimNOS-managed threads: the loop is owned by SimNOS, not the plugin.

        Returning [] keeps ``_collect_server_threads`` from joining the shared loop
        thread once per async host (it is joined once by ``SimNOS.stop()``), and
        lets it coexist with paramiko-era telnet servers that still return real
        threads during the Stage 2-3 migration (Decision 2).
        """
        return []

    @staticmethod
    def _load_authorized_keys(path: str | None) -> "set[bytes]":
        """Parse an OpenSSH authorized_keys file into a set of base64 key blobs.

        Mirrors ``ParamikoSshServer._load_authorized_keys`` in intent (bare key
        lines, skip comment/blank/marker lines). Stored value = the base64 middle
        field of the OpenSSH line, matched in ``validate_public_key``.
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

    # ------------------------------------------------------------------ lifecycle
    def start(self) -> None:
        """Register this host's listener on the shared loop (§1)."""
        if self._simnos is None:
            raise RuntimeError("AsyncSshServer requires a SimNOS reference (set by Host.start)")
        self._shared_loop = self._simnos.ensure_shared_loop()
        self._is_running.set()
        self._acceptor = self._shared_loop.run_coro(self._create_server(), timeout=_CREATE_SERVER_TIMEOUT)
        self._shared_loop.register(self)

    async def _create_server(self) -> "asyncssh.SSHAcceptor":
        return await asyncssh.create_server(
            lambda: _SimnosSSHServer(self.username, self.password, self._allow_auth_none, self._authorized_keys),
            self.address,
            self.port,
            server_host_keys=[self._host_key],
            encoding=None,  # binary channel → byte-exact parity with paramiko
            process_factory=self._handle_process,
            allow_pty=True,
            # Restart-friendly bind (parity with TCPServerBase SO_REUSEADDR/PORT)
            # so stop→start does not hit EADDRINUSE.
            reuse_address=True,
            reuse_port=(sys.platform == "linux"),
        )

    def stop(self) -> None:
        """Stop this host: drain its listener + sessions on the shared loop (§1a 5a).

        Per-host scope only — the global loop teardown is ``SimNOS.stop()``'s job
        (``teardown_if_idle``) once no async hosts remain. Idempotent via
        ``drain_host`` (double stop is a no-op).
        """
        self._is_running.clear()
        if self._shared_loop is not None:
            self._shared_loop.drain_host(self)
        self._acceptor = None

    async def aclose(self) -> None:
        """Close the listener + drain active sessions (called by the shared loop).

        Runs on the loop thread. Stops accepting, signals in-flight dispatch to
        close (``_is_running`` cleared in ``stop``), closes each active session so
        its read returns EOF, then awaits the session tasks with a bounded budget
        (cancelling any stragglers) so teardown leaves no orphaned tasks.
        """
        self._is_running.clear()
        if self._acceptor is not None:
            self._acceptor.close()
        for process in list(self._processes):
            with contextlib.suppress(Exception):
                process.close()
        tasks = [t for t in self._tasks if not t.done()]
        if tasks:
            _, pending = await asyncio.wait(tasks, timeout=SHUTDOWN_IO_TIMEOUT)
            for t in pending:
                t.cancel()
        if self._acceptor is not None:
            with contextlib.suppress(Exception):
                await self._acceptor.wait_closed()

    # ------------------------------------------------------------------ per-session
    async def _handle_process(self, process: "asyncssh.SSHServerProcess") -> None:
        """asyncssh process handler: one interactive shell session (§3a).

        Parity with ``ParamikoSshServer.connection_function`` but async: optional
        auth_none channel login, then the push session driving ``shell.dispatch``
        via the bounded executor. asyncssh closes ``process`` when this returns.
        """
        task = asyncio.current_task()
        self._tasks.add(task)
        self._processes.add(process)
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

            client_shell = self.shell(
                stdin=io.StringIO(),
                stdout=io.StringIO(),
                nos=self.nos,
                nos_inventory_config=self.nos_inventory_config,
                is_running=self._is_running,
                resolved_platform=self._shared_platform,
                render_config=self._render_config,
                **self.shell_configuration,
            )
            shared_loop = self._shared_loop
            assert shared_loop is not None  # noqa: S101 — set in start() before any session
            loop = shared_loop.loop
            executor = shared_loop.executor

            async def dispatch(line: str):
                # Off-load the blocking dispatch (custom handlers / hot-reload) to
                # the bounded executor so the loop thread stays free (§2a).
                return await loop.run_in_executor(executor, client_shell.dispatch, line)

            await run_async_push_session(transport, client_shell, dispatch, initial_skip_lf=skip_lf)
        except asyncio.CancelledError:
            raise
        except Exception:
            # A session-level crash must not take down the loop; log + tear down
            # this session only (§3a observability, #294-aligned).
            log.exception("AsyncSshServer session crashed")
        finally:
            self._tasks.discard(task)
            self._processes.discard(process)
            with contextlib.suppress(Exception):
                process.close()
