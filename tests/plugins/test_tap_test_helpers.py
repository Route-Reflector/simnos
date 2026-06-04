"""
Direct contract pins for tap_test_helpers (T-9 / #228).

The tap-loop tests rely on these helpers indirectly through the current
loop shapes; these tests pin the helper contracts themselves so a future
helper change fails here first, not in some consuming loop test.
"""

import unittest

from tests.plugins.tap_test_helpers import countdown_run_srv, live_run_srv


class LiveRunSrvTest(unittest.TestCase):
    """live_run_srv() must stay set for any number of checks."""

    def test_is_set_returns_true_repeatedly(self):
        """No hidden countdown: every is_set() call returns True."""
        run_srv = live_run_srv()
        self.assertTrue(all(run_srv.is_set() for _ in range(50)))


class CountdownRunSrvTest(unittest.TestCase):
    """countdown_run_srv(n) returns True n times, then False forever."""

    def test_zero_is_false_from_the_first_check(self):
        """countdown(0) = already shut down before the first check."""
        run_srv = countdown_run_srv(0)
        self.assertFalse(run_srv.is_set())

    def test_returns_false_repeatedly_after_exhaustion(self):
        """After the Trues run out, False keeps coming (no StopIteration).

        Pins the chain(repeat(True, n), repeat(False)) form: loops that
        re-check is_set() after the first False (e.g. an inner wait guard
        plus the outer guard) must keep seeing False.
        """
        run_srv = countdown_run_srv(2)
        observed = [run_srv.is_set() for _ in range(5)]
        self.assertEqual(observed, [True, True, False, False, False])

    def test_negative_true_count_raises_value_error(self):
        """A negative count is a test bug, not an empty countdown."""
        with self.assertRaisesRegex(ValueError, r"true_count must be >= 0, got -1"):
            countdown_run_srv(-1)
