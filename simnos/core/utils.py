"""Utility helpers for SimNOS core."""

import os
from pathlib import Path


def _is_unsafe_bare_ref(ref: str) -> bool:
    """Whether ``ref`` escapes its own directory (the root-confinement invariant).

    A safe reference is a bare filename adjacent to its owner: not empty, not
    ``.`` / ``..``, no path separators, not absolute. Shared by the A3 authoring
    schema (`pydantic_models._reject_unsafe_output_ref`) and the overlay loader
    (`overlay_loader._validate_overlay_ref`) so the one path-traversal defense has
    a single definition; each caller keeps its own error message (and the overlay
    its extra ``.txt`` / ``.j2`` extension rule).
    """
    return not ref or ref in (".", "..") or ref != os.path.basename(ref) or os.path.isabs(ref)


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
