"""SimNOS-owned shared asyncio event loop (#297 Stage 2, §1 / §1a / §2a).

The spike (#296) proved that one event loop multiplexing every async listener and
session — not one loop per host — is the architecture v3 should build. This module
owns that single loop as a **SimNOS-scoped resource** (Decision 2): one dedicated
thread runs the loop, one bounded ``ThreadPoolExecutor`` runs the blocking
dispatch off the loop thread (§2a), and a single-lock registry tracks the active
async listeners so partial stop / restart / double stop stay coherent (§1a).

The public ``SimNOS`` API stays fully synchronous (``start()`` / ``stop()``); the
sync↔async boundary lives here behind ``run_coro`` / ``submit_coro``.

Lifecycle (§1a):

- ``RUNNING``  — loop thread alive, accepting registrations.
- ``STOPPING`` — global teardown in progress.
- ``STOPPED``  — loop thread joined + loop closed; a later ``ensure_running`` lazily
  recreates everything (restart).
- ``FAILED``   — teardown could not fully release the loop thread; ``ensure_running``
  refuses to restart (no silent restart), ``teardown`` may be retried.
"""

import asyncio
from collections.abc import Awaitable
import concurrent.futures
import enum
import logging
import os
import threading
import time
from typing import Protocol, TypeVar

from simnos.core.timeouts import (
    SHUTDOWN_IO_TIMEOUT,
    SHUTDOWN_SERVER_STOP_DEADLINE,
)

log = logging.getLogger(__name__)

_T = TypeVar("_T")

#: Loop-thread startup budget (seconds). The thread only has to create the loop
#: and signal readiness, so this is generous.
_LOOP_START_TIMEOUT = 10


def _default_max_workers() -> int:
    """Default bounded-executor size (§2a). Overridable via init arg / env.

    CPU-based so CI (2 vCPU) and a real host (8+ vCPU) get a sensible default;
    the 100-host stress (Stage 2) tunes the recommended value documented for
    ``SIMNOS_DISPATCH_WORKERS``. Bounded (not unbounded) is the whole point — an
    unbounded executor would reintroduce the W3 thread-per-session explosion.
    """
    return min(64, max(8, (os.cpu_count() or 4) * 4))


class LoopState(enum.Enum):
    """Lifecycle state of the shared loop (§1a)."""

    STOPPED = "stopped"
    RUNNING = "running"
    STOPPING = "stopping"
    FAILED = "failed"


class AsyncListener(Protocol):
    """An async host listener the shared loop can drain on stop (§1a).

    ``AsyncSshServer`` implements it: ``aclose`` stops accepting, closes the
    listener socket, and drains the host's active sessions — the host-scope (5a)
    cleanup that must run even on a partial stop.
    """

    async def aclose(self) -> None:
        """Close the listener + drain this host's active sessions."""
        ...


class SharedLoop:
    """One asyncio loop + bounded executor + listener registry, owned by SimNOS."""

    def __init__(self, max_workers: int | None = None) -> None:
        env_workers = os.environ.get("SIMNOS_DISPATCH_WORKERS")
        if max_workers is None and env_workers:
            max_workers = int(env_workers)
        if max_workers is not None and max_workers < 1:
            raise ValueError(f"max_workers must be >= 1, got {max_workers}")
        self._max_workers = max_workers or _default_max_workers()

        self._lock = threading.Lock()
        self._state = LoopState.STOPPED
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._executor: concurrent.futures.ThreadPoolExecutor | None = None
        # Active async listeners keyed by object identity (one per host). refcount
        # = len(registry); "all async hosts stopped" is registry-empty, not a scan
        # of configured-host running flags (§1, codex#3).
        self._listeners: dict[int, AsyncListener] = {}

    # ------------------------------------------------------------------ state
    @property
    def state(self) -> LoopState:
        with self._lock:
            return self._state

    @property
    def refcount(self) -> int:
        """Number of registered async listeners (active hosts on this loop)."""
        with self._lock:
            return len(self._listeners)

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        """The running loop. Raises if not started (call ``ensure_running`` first)."""
        if self._loop is None:
            raise RuntimeError("shared loop is not running")
        return self._loop

    @property
    def executor(self) -> concurrent.futures.ThreadPoolExecutor:
        """The bounded dispatch executor (§2a)."""
        if self._executor is None:
            raise RuntimeError("shared loop executor is not running")
        return self._executor

    # ------------------------------------------------------------------ startup
    def ensure_running(self) -> asyncio.AbstractEventLoop:
        """Lazily start the loop thread + executor; return the running loop.

        Idempotent while ``RUNNING``. Recreates everything after ``STOPPED``
        (restart). Refuses to restart from ``FAILED`` (no silent restart, §1a).
        """
        with self._lock:
            if self._state is LoopState.RUNNING:
                assert self._loop is not None  # noqa: S101 — RUNNING invariant
                return self._loop
            if self._state is LoopState.STOPPING:
                raise RuntimeError("shared loop is stopping; cannot start")
            if self._state is LoopState.FAILED:
                raise RuntimeError(
                    "shared loop is in FAILED state (a previous teardown could not release it); "
                    "retry stop() before starting again"
                )
            self._start_locked()
            return self._loop  # type: ignore[return-value]  # set by _start_locked

    def _start_locked(self) -> None:
        """Start the loop thread + executor (caller holds the lock)."""
        ready = threading.Event()
        start_error: list[BaseException] = []

        def _run() -> None:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                self._loop = loop
            except BaseException as exc:
                start_error.append(exc)
                ready.set()
                return
            ready.set()
            try:
                loop.run_forever()
            finally:
                # Own the loop's full lifecycle on this thread so teardown is a
                # deterministic join. shutdown_default_executor joins the loop's
                # internal executor threads (asyncssh's getaddrinfo etc.) that a
                # bare loop.close() would leave lingering; without it a stopped
                # SimNOS keeps an `asyncio_N` worker alive (thread-count leak).
                try:
                    loop.run_until_complete(loop.shutdown_asyncgens())
                    # `timeout` is a real 3.12+ parameter; ty's stdlib stub lags.
                    loop.run_until_complete(
                        loop.shutdown_default_executor(timeout=SHUTDOWN_IO_TIMEOUT)  # type: ignore[unknown-argument]
                    )
                except Exception:
                    log.debug("shared loop cleanup error", exc_info=True)
                finally:
                    loop.close()

        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=self._max_workers, thread_name_prefix="simnos-dispatch"
        )
        self._thread = threading.Thread(target=_run, daemon=True, name="simnos-shared-loop")
        self._thread.start()
        if not ready.wait(timeout=_LOOP_START_TIMEOUT):
            raise RuntimeError(f"shared loop failed to start within {_LOOP_START_TIMEOUT}s")
        if start_error:
            raise start_error[0]
        self._state = LoopState.RUNNING

    # ------------------------------------------------------------------ submit
    def submit_coro(self, coro: Awaitable[_T]) -> "concurrent.futures.Future[_T]":
        """Schedule *coro* on the loop from a sync caller (run_coroutine_threadsafe)."""
        return asyncio.run_coroutine_threadsafe(coro, self.loop)  # type: ignore[arg-type]

    def run_coro(self, coro: Awaitable[_T], timeout: float | None = None) -> _T:
        """Run *coro* on the loop and block for its result (sync facade)."""
        return self.submit_coro(coro).result(timeout=timeout)

    # ------------------------------------------------------------------ registry
    def register(self, listener: AsyncListener) -> None:
        """Register an active async listener (refcount += 1)."""
        with self._lock:
            if self._state is not LoopState.RUNNING:
                raise RuntimeError(f"cannot register a listener while loop is {self._state.value}")
            self._listeners[id(listener)] = listener

    def drain_host(self, listener: AsyncListener, deadline: float | None = None) -> None:
        """Host-scope stop (§1a 5a): close + drain one listener; idempotent.

        Pops the listener (so a double stop is a no-op) and runs its ``aclose`` on
        the loop, bounded by *deadline*. This MUST run even on a partial stop so
        the host's listener socket is released (else restart hits EADDRINUSE,
        gemini#1). A drain error is logged, not raised — the host reference is
        already removed, and a stuck close must not block stopping other hosts.
        """
        with self._lock:
            listener = self._listeners.pop(id(listener), None)  # type: ignore[assignment]
        if listener is None:
            return  # already drained
        loop = self._loop
        if loop is None or loop.is_closed():
            return
        budget = self._remaining(deadline)
        try:
            self.submit_coro(listener.aclose()).result(timeout=budget)
        except Exception:
            log.exception("shared loop: draining host listener failed")

    def teardown_if_idle(self, deadline: float | None = None) -> bool:
        """Global teardown (§1a 5b) when no async listeners remain.

        Called by ``SimNOS.stop()`` after stopping the requested hosts. Tears the
        loop down only when the registry is empty (refcount == 0); otherwise other
        async hosts are still running and the loop must stay up (partial stop).
        Returns True when a teardown ran.
        """
        with self._lock:
            if self._state is not LoopState.RUNNING:
                return False
            if self._listeners:
                return False  # other async hosts still running
            self._state = LoopState.STOPPING
        self._global_teardown(deadline)
        return True

    # ------------------------------------------------------------------ teardown
    def _global_teardown(self, deadline: float | None) -> None:
        """Stop the loop, join the thread, detach (§1a 5b).

        The loop thread closes the loop + joins its internal executor in its own
        ``finally`` (see ``_start_locked``), so this only has to stop the loop and
        join the thread. Emergency cleanup runs in ``finally`` so the bounded
        executor + loop refs are released even if something above raises. If the
        loop thread cannot be joined within budget the state goes ``FAILED``.
        """
        loop = self._loop
        executor = self._executor
        thread = self._thread
        try:
            # Bounded executor shutdown: cancel queued dispatch, do not wait for an
            # in-flight (possibly non-cooperative) handler — same policy as the
            # legacy parallel-stop path (cancel_futures, no block).
            if executor is not None:
                executor.shutdown(wait=False, cancel_futures=True)
        finally:
            alive = False
            if loop is not None and not loop.is_closed():
                loop.call_soon_threadsafe(loop.stop)
            if thread is not None:
                thread.join(timeout=self._remaining(deadline))
                alive = thread.is_alive()
            with self._lock:
                self._loop = None
                self._thread = None
                self._executor = None
                self._listeners.clear()
                self._state = LoopState.FAILED if alive else LoopState.STOPPED
            if alive:
                log.warning("shared loop thread did not exit within timeout; loop left in FAILED state")

    @staticmethod
    def _remaining(deadline: float | None) -> float:
        """Seconds left until *deadline* (monotonic), or the per-server budget when unset."""
        if deadline is None:
            return SHUTDOWN_SERVER_STOP_DEADLINE
        return max(SHUTDOWN_IO_TIMEOUT, deadline - time.monotonic())
