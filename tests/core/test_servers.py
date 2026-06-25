"""Test module for simnos.core.servers.
The file can be found under simnos/core/servers.py

``TCPServerBase`` (the thread-per-connection base for the retired paramiko SSH /
raw-socket Telnet servers) was removed in #297 Stage 4 when both transports moved
to the shared asyncio loop. The only surviving symbol is the bounded thread-join
helper ``join_threads_with_deadline`` used by ``SimNOS.stop``; these tests pin its
per-thread cap, total-deadline skip, and still-alive reporting directly (the
integration path through ``SimNOS._join_threads`` is covered in test_simnos.py).
"""

import threading
from typing import cast
import unittest
from unittest.mock import patch

from simnos.core.servers import join_threads_with_deadline


class FakeThread:
    """Minimal ``threading.Thread`` stand-in: records the join() timeout and
    reports a fixed liveness so the deadline logic can be tested deterministically
    without real threads."""

    def __init__(self, *, alive_after_join: bool = False) -> None:
        self._alive_after_join = alive_after_join
        self.join_timeout: float | None = None
        self.join_called = False

    def join(self, timeout: float | None = None) -> None:
        self.join_called = True
        self.join_timeout = timeout

    def is_alive(self) -> bool:
        return self._alive_after_join


def _join(threads: list[FakeThread], total_timeout: float, per_thread_timeout: float) -> list[threading.Thread]:
    """Call the helper with the FakeThread stand-ins (cast to satisfy ty: FakeThread
    duck-types the ``join`` / ``is_alive`` surface the helper actually uses)."""
    return join_threads_with_deadline(cast(list[threading.Thread], threads), total_timeout, per_thread_timeout)


class JoinThreadsWithDeadlineTest(unittest.TestCase):
    """join_threads_with_deadline: per-thread cap, deadline skip, alive reporting."""

    def test_empty_list_returns_empty(self):
        """No threads -> nothing joined, empty alive list."""
        self.assertEqual(_join([], 10, 2), [])

    def test_all_join_within_budget_returns_empty(self):
        """Every thread joins and exits -> empty alive list."""
        threads = [FakeThread(), FakeThread()]
        alive = _join(threads, 10, 2)
        self.assertEqual(alive, [])
        for t in threads:
            self.assertTrue(t.join_called)

    def test_join_capped_at_per_thread_timeout(self):
        """With ample total budget, each join is capped at per_thread_timeout."""
        t = FakeThread()
        _join([t], total_timeout=10, per_thread_timeout=2)
        self.assertEqual(t.join_timeout, 2)

    def test_join_capped_at_remaining_when_below_per_thread(self):
        """When the remaining budget is smaller than the per-thread cap, the join
        timeout is the remaining budget (deadline takes precedence)."""
        t = FakeThread()
        # monotonic: deadline base, then a remaining of ~1s (< per_thread 5).
        with patch("simnos.core.servers.time.monotonic", side_effect=[100.0, 102.0]):
            _join([t], total_timeout=3, per_thread_timeout=5)
        # deadline = 103; remaining = 103 - 102 = 1 -> min(5, 1) = 1.
        self.assertEqual(t.join_timeout, 1.0)

    def test_still_alive_thread_is_returned(self):
        """A thread that is still alive after its join is reported as alive."""
        live = FakeThread(alive_after_join=True)
        dead = FakeThread(alive_after_join=False)
        alive = _join([live, dead], 10, 2)
        self.assertEqual(alive, [live])

    def test_deadline_exceeded_skips_remaining_joins(self):
        """Once the total deadline is past, remaining threads are not joined but
        are still reported as alive if they are."""
        joined = FakeThread(alive_after_join=False)
        skipped = FakeThread(alive_after_join=True)
        # monotonic: [deadline base, remaining for #1 (ok), remaining for #2 (past)].
        with patch("simnos.core.servers.time.monotonic", side_effect=[0.0, 5.0, 11.0]):
            alive = _join([joined, skipped], total_timeout=10, per_thread_timeout=2)
        self.assertTrue(joined.join_called)
        self.assertFalse(skipped.join_called)
        self.assertEqual(alive, [skipped])


if __name__ == "__main__":
    unittest.main()
