"""Shutdown timeout constants for SimNOS.

Shutdown timeout hierarchy. Outer (SimNOS-global) deadlines bound the inner
(per-server / per-thread) budgets, leaving headroom for sockets and event waits
to complete.

| Tier | Constant                            | Value | Owner / role                                      |
|------|-------------------------------------|------:|---------------------------------------------------|
| 1    | ``SHUTDOWN_GLOBAL_DEADLINE``        |  60s  | ``SimNOS.stop()`` total wall-clock budget.        |
| 2    | ``SHUTDOWN_SAFETY_NET_DEADLINE``    |  15s  | ``SimNOS._join_threads`` safety-net join budget.  |
| 3    | ``SHUTDOWN_SERVER_STOP_DEADLINE``   |  10s  | Shared-loop per-host drain budget (``SharedLoop``).|
| 4    | ``SHUTDOWN_SAFETY_NET_PER_THREAD``  |   5s  | Per-thread cap inside SimNOS safety-net join.     |
| 5    | ``SHUTDOWN_IO_TIMEOUT``             |   2s  | Bounded I/O wait on shutdown paths (public API).  |

Ordering: 60s >= 15s >= 10s >= 5s >= 2s.

``SHUTDOWN_IO_TIMEOUT`` is the public API consumed by the async server lifecycle
(``simnos.plugins.servers.async_server_base``) and the shared loop
(``simnos.core.shared_loop``). The other constants are used internally by
``simnos.core.shared_loop`` / ``simnos.core.simnos`` but are re-exported here as
the single source of truth.
"""

SHUTDOWN_GLOBAL_DEADLINE = 60
SHUTDOWN_SAFETY_NET_DEADLINE = 15
SHUTDOWN_SERVER_STOP_DEADLINE = 10
SHUTDOWN_SAFETY_NET_PER_THREAD = 5
SHUTDOWN_IO_TIMEOUT = 2

__all__ = [
    "SHUTDOWN_GLOBAL_DEADLINE",
    "SHUTDOWN_IO_TIMEOUT",
    "SHUTDOWN_SAFETY_NET_DEADLINE",
    "SHUTDOWN_SAFETY_NET_PER_THREAD",
    "SHUTDOWN_SERVER_STOP_DEADLINE",
]
