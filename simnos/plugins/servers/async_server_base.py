"""Shared lifecycle for async server plugins on the shared loop (#297 Stage 3, §1/§2).

``AsyncSshServer`` (Stage 2) and ``TelnetServer`` (Stage 3) are the same shape:
a listener + per-session push driver on the SimNOS-owned shared event loop
(:mod:`simnos.core.shared_loop`), driven by :func:`run_async_push_session` with
only the blocking ``shell.dispatch`` off-loaded to the bounded executor (§2a).
The only real differences are the transport (asyncssh vs telnetlib3) and the auth
flow (SSH protocol-level vs Telnet in-band). Everything else — start/stop/aclose,
the late-acceptor reclaim on a failed start, the session registry, and the
dispatch wiring — is identical, so it lives here once instead of being copied into
both plugins (design §3a 三層責務 / claude#3 "SSH/telnet 二重実装を防ぐ").

Subclasses implement two hooks:

- :meth:`_create_listener` — create the transport's listener on the loop, store
  it on ``self._acceptor``, and return it (the returned object must expose
  ``close()`` + ``wait_closed()``, which both asyncssh ``SSHAcceptor`` and the
  telnetlib3 ``asyncio.Server`` do).
- :meth:`_close_session` — close one active session handle (asyncssh process /
  telnetlib3 writer).

and drive each accepted connection through :meth:`_session_scope` +
:meth:`_drive_session`.
"""

import asyncio
import concurrent.futures
import contextlib
import io
import logging
import threading
from typing import TYPE_CHECKING, Protocol

from simnos.core.nos import Nos
from simnos.core.timeouts import SHUTDOWN_IO_TIMEOUT
from simnos.plugins.servers.async_session import run_async_push_session

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Awaitable, Callable

    from simnos.core.host import HostRenderConfig
    from simnos.core.shared_loop import SharedLoop
    from simnos.core.simnos import SimNOS
    from simnos.plugins.servers.async_session import AsyncPushTransport
    from simnos.plugins.shell.cmd_shell import DispatchResult

log = logging.getLogger(__name__)

#: Per-host listener creation budget (seconds): create runs on the shared loop and
#: is awaited synchronously by start() (a bounded analogue of a blocking bind).
_CREATE_LISTENER_TIMEOUT = 30


class Listener(Protocol):
    """The minimal listener surface the base lifecycle needs (asyncssh / asyncio)."""

    def close(self) -> None: ...

    async def wait_closed(self) -> None: ...


class AsyncServerBase:
    """Shared async-server lifecycle on the SimNOS-owned shared loop (§1 / §2).

    Not a ``TCPServerBase``: listening + sessions live on the shared asyncio loop,
    not a thread per connection. ``managed_threads`` is empty — the loop thread is
    a SimNOS-scoped resource joined once by ``SimNOS.stop()`` (Decision 2).
    """

    def __init__(
        self,
        shell: type,
        nos: Nos,
        nos_inventory_config: dict,
        port: int,
        username: str,
        password: str,
        *,
        shell_configuration: dict | None = None,
        address: str = "127.0.0.1",
        timeout: int = 1,
        watchdog_interval: float = 1,
        render_config: "HostRenderConfig | None" = None,
        simnos: "SimNOS | None" = None,
    ) -> None:
        self.nos: Nos = nos
        self.nos_inventory_config: dict = nos_inventory_config
        self.shell: type = shell
        self.shell_configuration: dict = shell_configuration or {}
        self._render_config: HostRenderConfig | None = render_config
        # Normalize the merged platform once at Host.start (per-host invariant,
        # surfaces malformed data at startup rather than on the first connection).
        build_shared = getattr(self.shell, "build_shared_platform", None)
        self._shared_platform = build_shared(nos, self.nos_inventory_config, render_config) if build_shared else None
        self.username: str = username
        self.password: str = password
        self.address: str = address
        self.port: int = port
        # timeout / watchdog_interval are inert on the async path (shutdown is
        # driven by closing the listener/sessions on the shared loop, not a recv
        # poll); kept for sync-plugin signature + config parity.
        self.timeout: int = timeout
        self.watchdog_interval: float = watchdog_interval
        self._simnos = simnos

        self._shared_loop: SharedLoop | None = None
        self._acceptor: Listener | None = None
        # Per-server run flag the shells observe: cleared on stop so an in-flight
        # dispatch returns close (cooperative stop, §1a).
        self._is_running = threading.Event()
        # Set once aclose starts so a session that begins handshaking *after* the
        # drain snapshot bows out instead of leaking past teardown (claude 1st#1).
        self._closing = False
        # Active session handles (asyncssh process / telnetlib3 writer), drained on
        # aclose (§1a host-scope 5a), plus their driving tasks.
        self._sessions: set[object] = set()
        self._tasks: set[asyncio.Task] = set()

    @property
    def managed_threads(self) -> list[threading.Thread]:
        """No SimNOS-managed threads: the loop is owned by SimNOS, not the plugin.

        Returning [] keeps ``_collect_server_threads`` from joining the shared loop
        thread once per async host — it is joined once by ``SimNOS.stop()``
        (Decision 2).
        """
        return []

    # ------------------------------------------------------------------ lifecycle
    def start(self) -> None:
        """Register this host's listener on the shared loop (§1).

        On a failed/timed-out create the pending coroutine is cancelled and any
        listener it managed to create is closed, so a failed start leaves no orphan
        listener socket (codex 1st#1) — including the case where the create
        completes *after* ``result()`` gave up: a done-callback closes that late
        acceptor (codex 2nd#1). The loop-idle cleanup — when this failure leaves the
        loop with refcount 0 — is ``SimNOS.stop()``'s job (``teardown_if_idle``),
        reached via the caller's ``stop()`` / context manager ``__exit__``.
        """
        if self._simnos is None:
            raise RuntimeError(f"{type(self).__name__} requires a SimNOS reference (set by Host.start)")
        self._shared_loop = self._simnos.ensure_shared_loop()
        self._closing = False  # fresh start (defensive if an instance is reused, codex 2nd#4)
        self._is_running.set()
        future = self._shared_loop.submit_coro(self._create_listener())
        try:
            future.result(timeout=_CREATE_LISTENER_TIMEOUT)
        except BaseException:
            future.cancel()
            # If the create still completes after we gave up (cancellation lost the
            # race, or it finished right at the timeout), close the acceptor it
            # yields so no listener leaks (codex 2nd#1).
            future.add_done_callback(self._discard_late_acceptor)
            self._abort_failed_start()
            raise
        self._shared_loop.register(self)

    def _discard_late_acceptor(self, future: "concurrent.futures.Future") -> None:
        """Close a listener a cancelled/timed-out start produced after giving up.

        This done-callback usually runs on the loop thread (the create coroutine
        completes there after ``start`` gave up waiting), but it can ALSO run
        synchronously on the calling thread: ``concurrent.futures.Future``
        invokes a callback inline when the future is *already* done at
        ``add_done_callback`` time (e.g. the create finished right at the timeout
        boundary, gemini 1st#1). ``acceptor.close()`` is not thread-safe (it drives
        ``loop.remove_reader`` on the selector), so it is always routed onto the
        loop via ``call_soon_threadsafe`` rather than called inline. A cancelled
        future has no acceptor to reclaim; a completed one is closed (idempotent
        with ``_abort_failed_start`` if both fire).
        """
        if future.cancelled():
            return
        # suppress(Exception), not BaseException: future.result() re-raises the create
        # coroutine's failure (OSError / asyncssh.Error) and call_soon_threadsafe raises
        # RuntimeError if the loop has since closed — both are Exception subclasses.
        # KeyboardInterrupt / SystemExit are deliberately NOT suppressed: this can run
        # inline on the caller thread (the future was already done at add_done_callback
        # time), where an operator's Ctrl-C must still abort (gemini 2nd#1).
        with contextlib.suppress(Exception):
            acceptor = future.result()
            shared_loop = self._shared_loop
            if acceptor is not None and shared_loop is not None:
                # Route close onto the loop thread — acceptor.close() drives the
                # selector (remove_reader) and is not safe to call from the caller
                # thread. A closed loop raises RuntimeError here, caught by the suppress
                # above, so no (racy) is_closed() pre-check is needed (gemini 2nd#1).
                shared_loop.loop.call_soon_threadsafe(acceptor.close)

    def _abort_failed_start(self) -> None:
        """Close a listener left by a failed/timed-out start (codex 1st#1).

        ``_create_listener`` stores the acceptor on ``self`` as soon as it exists,
        so even when ``result()`` gave up waiting (and the coroutine then completed)
        the listener is reachable here and closed on the loop. Best-effort: a stuck
        loop must not turn a start failure into a hang.
        """
        loop = self._shared_loop
        if loop is None:
            return
        with contextlib.suppress(Exception):
            loop.run_coro(self._aclose_acceptor(), timeout=SHUTDOWN_IO_TIMEOUT)

    async def _aclose_acceptor(self) -> None:
        """Close + await the listener socket (on the loop thread)."""
        acceptor, self._acceptor = self._acceptor, None
        if acceptor is not None:
            acceptor.close()
            with contextlib.suppress(Exception):
                await acceptor.wait_closed()

    def stop(self) -> None:
        """Stop this host: drain its listener + sessions on the shared loop (§1a 5a).

        Per-host scope only — the global loop teardown is ``SimNOS.stop()``'s job
        (``teardown_if_idle``) once no async hosts remain. Idempotent via
        ``drain_host`` (double stop is a no-op).
        """
        self._is_running.clear()
        if self._shared_loop is not None:
            self._shared_loop.drain_host(self)
        # Do NOT null self._acceptor here: if drain_host timed out, the queued
        # aclose runs later and still needs the reference to close the listener
        # socket (clearing it would leak the socket → EADDRINUSE, gemini 1st#1).
        # The instance is discarded by Host.start after stop(), so no leak.

    async def aclose(self) -> None:
        """Close the listener + drain active sessions (called by the shared loop).

        Runs on the loop thread. Marks the server closing (so a session that begins
        handshaking after the snapshot below bows out, claude 1st#1), stops
        accepting, signals in-flight dispatch to close (``_is_running`` cleared),
        closes each active session so its read returns EOF, then waits on the
        session tasks with a bounded budget — cancelling any stragglers and giving
        them a bounded moment to run their ``finally`` (gemini 1st#3) — leaving no
        orphaned task or listener.
        """
        self._closing = True
        self._is_running.clear()
        if self._acceptor is not None:
            self._acceptor.close()
        for session in list(self._sessions):
            with contextlib.suppress(Exception):
                self._close_session(session)
        tasks = [t for t in self._tasks if not t.done()]
        if tasks:
            _, pending = await asyncio.wait(tasks, timeout=SHUTDOWN_IO_TIMEOUT)
            for t in pending:
                t.cancel()
            if pending:
                # Give the cancelled tasks a brief, BOUNDED moment to run their
                # finally (gemini 1st#3) — but do not block on a non-cooperative
                # dispatch whose executor job cannot be cancelled. Such a handler is
                # detached (§1a, codex 1st#3) so stop converges within the budget;
                # its late result lands on the now-closed transport and is discarded
                # (generation isolation via per-session shell + transport close).
                await asyncio.wait(pending, timeout=SHUTDOWN_IO_TIMEOUT)
        if self._acceptor is not None:
            # Bounded: wait_closed can otherwise block on a detached session's
            # connection (a non-cooperative dispatch above), which would defeat the
            # detach and stall stop to the drain budget. The listening socket is
            # already closed by acceptor.close(); this just confirms shutdown.
            with contextlib.suppress(Exception):
                await asyncio.wait_for(self._acceptor.wait_closed(), timeout=SHUTDOWN_IO_TIMEOUT)

    # ------------------------------------------------------------------ per-session
    def _bow_out_if_closing(self, session: object) -> bool:
        """Close + skip a connection that arrived after teardown began (claude 1st#1).

        A connection that finishes handshaking/negotiation *after* ``aclose`` took
        its drain snapshot must not start a session on a stopping host. Returns True
        (and closes the session handle) when the server is already closing, so the
        per-session handler can bow out before registering anything.
        """
        if self._closing:
            with contextlib.suppress(Exception):
                self._close_session(session)
            return True
        return False

    @contextlib.asynccontextmanager
    async def _session_scope(self, session: object) -> "AsyncIterator[None]":
        """Register the current task + session handle, and clean up on exit (§1a).

        The session task and handle are tracked in ``_tasks`` / ``_sessions`` so
        ``aclose`` can drain them, and the handle is closed in ``finally`` so a
        normal session end (or crash) always releases its transport.
        """
        task = asyncio.current_task()
        if task is not None:
            self._tasks.add(task)
        self._sessions.add(session)
        try:
            yield
        finally:
            if task is not None:
                self._tasks.discard(task)
            self._sessions.discard(session)
            with contextlib.suppress(Exception):
                self._close_session(session)

    def _build_shell(self):
        """Build the per-session shell (shared NOS data + per-host render config)."""
        return self.shell(
            stdin=io.StringIO(),
            stdout=io.StringIO(),
            nos=self.nos,
            nos_inventory_config=self.nos_inventory_config,
            is_running=self._is_running,
            resolved_platform=self._shared_platform,
            render_config=self._render_config,
            **self.shell_configuration,
        )

    def _make_dispatch(self, client_shell) -> "Callable[[str], Awaitable[DispatchResult]]":
        """Build the async dispatch closure that off-loads blocking work (§2a).

        ``shell.dispatch`` (custom handlers / hot-reload) runs on the bounded
        executor so the loop thread stays free. A non-cooperative handler that
        outlives stop (its executor job cannot be cancelled) completes after the
        loop is torn down; the run_in_executor done-callback then logs a harmless
        "Event loop is closed" — the late result lands nowhere (the awaiting task
        was cancelled and the transport is closed = generation isolation,
        claude 2nd#2).
        """
        shared_loop = self._shared_loop
        assert shared_loop is not None  # noqa: S101 — set in start() before any session
        loop = shared_loop.loop
        executor = shared_loop.executor

        async def dispatch(line: str) -> "DispatchResult":
            return await loop.run_in_executor(executor, client_shell.dispatch, line)

        return dispatch

    async def _drive_session(self, transport: "AsyncPushTransport", *, skip_lf: bool = False) -> None:
        """Drive one authenticated session with the shared push driver (§3a).

        Builds the per-session shell + dispatch closure and runs the W3 push
        session — byte-identical to the SSH path (the wire assembly lives in
        ``run_async_push_session`` + ``_render_*``, shared by both transports).
        """
        client_shell = self._build_shell()
        dispatch = self._make_dispatch(client_shell)
        await run_async_push_session(transport, client_shell, dispatch, initial_skip_lf=skip_lf)

    # ------------------------------------------------------------------ hooks
    async def _create_listener(self) -> Listener:
        """Create the transport listener on the loop; store + return it.

        Must set ``self._acceptor`` to the created listener *before* returning so
        ``_abort_failed_start`` can close it even when ``start``'s ``result()``
        already timed out (codex 1st#1).
        """
        raise NotImplementedError

    def _close_session(self, session: object) -> None:
        """Close one active session handle (asyncssh process / telnetlib3 writer)."""
        raise NotImplementedError
