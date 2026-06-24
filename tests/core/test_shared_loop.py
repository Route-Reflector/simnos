"""Unit tests for the SimNOS-owned shared asyncio loop (#297 Stage 2, §1 / §1a).

These pin the loop's lifecycle contract in isolation from asyncssh: lazy start,
state machine, listener registry / refcount, partial-vs-global teardown,
restart-after-stop, and the no-thread-leak guarantee that ``SimNOS.stop`` relies
on. The async-server integration (real listeners, byte parity, 100-host stress)
lives in the SSH tests; here a fake ``AsyncListener`` stands in.
"""

import threading

import pytest

from simnos.core.shared_loop import LoopState, SharedLoop


class _FakeListener:
    """Minimal AsyncListener: records that aclose ran on the loop."""

    def __init__(self) -> None:
        self.closed = threading.Event()

    async def aclose(self) -> None:
        self.closed.set()


@pytest.fixture
def loop():
    """A SharedLoop torn down after the test even if an assertion fails."""
    sl = SharedLoop(max_workers=4)
    try:
        yield sl
    finally:
        # Best-effort: drain any registered listeners then tear down the loop.
        for listener in list(sl._listeners.values()):
            sl.drain_host(listener)
        sl.teardown_if_idle()


def test_starts_stopped_and_lazy(loop):
    """A fresh SharedLoop is STOPPED and spawns no thread until ensure_running."""
    assert loop.state is LoopState.STOPPED
    assert loop.refcount == 0
    base = threading.active_count()
    loop.ensure_running()
    assert loop.state is LoopState.RUNNING
    assert threading.active_count() == base + 1  # one loop thread


def test_ensure_running_is_idempotent(loop):
    """Repeated ensure_running returns the same loop without extra threads."""
    first = loop.ensure_running()
    base = threading.active_count()
    second = loop.ensure_running()
    assert first is second
    assert threading.active_count() == base


def test_run_coro_executes_on_loop(loop):
    """run_coro runs a coroutine on the loop thread and returns its result."""
    loop.ensure_running()

    async def _work():
        return threading.current_thread().name, 21 * 2

    name, value = loop.run_coro(_work(), timeout=5)
    assert value == 42
    assert name == "simnos-shared-loop"


def test_register_increments_refcount(loop):
    """Registering listeners tracks refcount; draining decrements it."""
    loop.ensure_running()
    a, b = _FakeListener(), _FakeListener()
    loop.register(a)
    loop.register(b)
    assert loop.refcount == 2
    loop.drain_host(a)
    assert loop.refcount == 1
    assert a.closed.is_set()  # aclose ran on the loop


def test_partial_stop_keeps_loop_running(loop):
    """Draining one of two listeners must NOT tear the loop down (partial stop)."""
    loop.ensure_running()
    a, b = _FakeListener(), _FakeListener()
    loop.register(a)
    loop.register(b)
    loop.drain_host(a)
    assert loop.teardown_if_idle() is False  # b still registered -> no teardown
    assert loop.state is LoopState.RUNNING
    assert loop.refcount == 1


def test_global_teardown_when_idle(loop):
    """teardown_if_idle tears down once the last listener is drained (§1a 5b)."""
    base = threading.active_count()
    loop.ensure_running()
    a = _FakeListener()
    loop.register(a)
    loop.drain_host(a)
    assert loop.teardown_if_idle() is True
    assert loop.state is LoopState.STOPPED
    assert loop.refcount == 0
    assert threading.active_count() == base  # loop thread joined, no leak


def test_double_stop_is_idempotent(loop):
    """A second drain of an already-drained listener is a no-op (double stop)."""
    loop.ensure_running()
    a = _FakeListener()
    loop.register(a)
    loop.drain_host(a)
    loop.drain_host(a)  # must not raise
    assert loop.refcount == 0
    assert loop.teardown_if_idle() is True
    assert loop.teardown_if_idle() is False  # already STOPPED


def test_restart_after_stop(loop):
    """ensure_running recreates the loop after a full stop (restart)."""
    loop.ensure_running()
    first = loop.loop
    a = _FakeListener()
    loop.register(a)
    loop.drain_host(a)
    loop.teardown_if_idle()
    assert loop.state is LoopState.STOPPED

    loop.ensure_running()  # restart
    assert loop.state is LoopState.RUNNING
    assert loop.loop is not first  # a fresh loop object
    assert loop.run_coro(_one(), timeout=5) == 1


async def _one() -> int:
    return 1


def test_failed_state_refuses_restart(loop):
    """A FAILED loop refuses ensure_running (no silent restart, §1a)."""
    loop.ensure_running()
    # Force the FAILED state directly (a real un-joinable loop thread is hard to
    # produce deterministically); the contract is what we pin.
    with loop._lock:
        loop._state = LoopState.FAILED
    with pytest.raises(RuntimeError, match="FAILED"):
        loop.ensure_running()


def test_failed_state_recovers_via_teardown(loop):
    """A FAILED loop is recoverable: teardown_if_idle retries the join (gemini 1st#2).

    ensure_running's FAILED message tells the caller to retry stop(); that retry
    (SimNOS.stop -> teardown_if_idle) must actually re-run the teardown. The refs
    are kept on FAILED, so when the (here actually joinable) loop thread exits the
    retry reaches STOPPED and the loop is restartable again.
    """
    loop.ensure_running()
    with loop._lock:
        loop._state = LoopState.FAILED  # simulate a prior teardown that could not join
    assert loop.teardown_if_idle() is True
    assert loop.state is LoopState.STOPPED
    loop.ensure_running()
    assert loop.state is LoopState.RUNNING


def test_invalid_max_workers_rejected():
    """max_workers < 1 is a loud error."""
    with pytest.raises(ValueError, match="max_workers"):
        SharedLoop(max_workers=0)


def test_max_workers_env_override(monkeypatch):
    """SIMNOS_DISPATCH_WORKERS overrides the default executor size."""
    monkeypatch.setenv("SIMNOS_DISPATCH_WORKERS", "3")
    sl = SharedLoop()
    assert sl._max_workers == 3
