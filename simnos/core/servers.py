"""Thread-join helper shared by SimNOS shutdown paths.

``TCPServerBase`` (the thread-per-connection base for the paramiko SSH / raw-socket
Telnet servers) was retired in #297 Stage 4 when both transports moved to the
shared asyncio loop (:mod:`simnos.core.shared_loop`). Only the bounded thread-join
helper remains — used by ``SimNOS.stop`` to join any straggler managed threads
within a wall-clock deadline.
"""

import threading
import time


def join_threads_with_deadline(
    threads: list[threading.Thread],
    total_timeout: float,
    per_thread_timeout: float,
) -> list[threading.Thread]:
    """Join threads with a total wall-clock deadline.

    Iterates over *threads*, joining each with at most *per_thread_timeout*
    seconds.  Stops early when the cumulative elapsed time exceeds
    *total_timeout*.

    :returns: list of threads that are still alive after the deadline.
    """
    deadline = time.monotonic() + total_timeout
    alive: list[threading.Thread] = []
    skipped = False
    for thread in threads:
        if not skipped:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                skipped = True
            else:
                thread.join(timeout=min(per_thread_timeout, remaining))
        if thread.is_alive():
            alive.append(thread)
    return alive
