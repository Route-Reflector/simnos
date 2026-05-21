"""Utility helpers for SimNOS core."""

from pathlib import Path


def _is_in_docker() -> bool:
    """Detect whether the current process is running inside a Docker container.

    Replaces the previously-used ``detect.docker`` from the unmaintained
    ``detect`` package (last release 2020-12-03). Uses two independent
    heuristics; any positive match returns ``True``:

    1. ``/.dockerenv`` exists. Docker creates this file at the container
       root for every container it starts.
    2. ``/proc/1/cgroup`` contains ``docker`` or ``containerd``. PID 1's
       cgroup membership reveals the container runtime on Linux even when
       ``/.dockerenv`` is missing (e.g. rootless or non-Docker runtimes
       that still inherit the namespace).

    Both checks degrade gracefully on platforms where the paths do not
    exist (Windows host without WSL, plain macOS, BSD): the function
    simply returns ``False``.
    """
    if Path("/.dockerenv").exists():
        return True
    try:
        cgroup = Path("/proc/1/cgroup").read_text()
    except OSError:
        return False
    return "docker" in cgroup or "containerd" in cgroup
