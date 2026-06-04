"""run_srv mock constructors for the tap-loop tests (T-9 / #228).

Default idiom: data sources (recv / readline scripts) are finite and
EOF-terminated, so the tap loops exit via their EOF path and run_srv can
stay live for the whole test — loop-internal is_set() consumption counts
are NOT part of the test contract. Use countdown_run_srv() ONLY when the
run_srv-cleared exit path itself is the behaviour under test.
"""

from itertools import chain, repeat
from unittest.mock import Mock

__all__ = ["countdown_run_srv", "live_run_srv"]


def live_run_srv() -> Mock:
    """run_srv that stays set; the loop must exit via data-source EOF.

    A loop regression that ignores EOF exhausts the source's side_effect
    script and fails visibly with StopIteration — no watchdog fuel needed.
    """
    run_srv = Mock()
    run_srv.is_set.return_value = True
    return run_srv


def countdown_run_srv(true_count: int) -> Mock:
    """run_srv whose is_set() returns True *true_count* times, then False forever.

    For shutdown-path pins only: the test asserts the loop exits because
    run_srv was cleared, so the True-count is part of the test's intent.
    true_count=0 means "already shut down before the first check".
    Callers MUST document the consumption mapping (which is_set() call gets
    the first False) in the test docstring, and MUST assert an observable
    invariant for the exit position — loop changes still require updating
    *true_count* by hand, which is acceptable only because these tests pin
    the shutdown path itself.
    """
    if true_count < 0:
        raise ValueError(f"true_count must be >= 0, got {true_count}")
    run_srv = Mock()
    run_srv.is_set.side_effect = chain(repeat(True, true_count), repeat(False))
    return run_srv
