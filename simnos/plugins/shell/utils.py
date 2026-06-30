"""
This module is intended to be used
a collection of utilities for the shell.
"""

import logging
import os

log = logging.getLogger(__name__)


def get_files_under_directory(directory):
    """Method to get files under a directory"""
    files: list = []
    for root, _, filenames in os.walk(directory):
        if "__pycache__" in root:
            continue
        files += [os.path.join(root, filename) for filename in filenames]
    files = [file for file in files if os.path.isfile(file)]
    # `.txt` is the A3 literal-capture extension (#274 / D2): editing a command's
    # output file must trigger a reload like editing its yaml does. `.json` is the
    # #287 sidecar (the render values for a `.j2`): editing a value (e.g. version)
    # must likewise reload, since that round-trip edit is the feature's whole
    # point — `resolve_reload_targets` rolls a `commands/*.json` change up to its
    # platform dir, whose rebuild re-reads the sidecar (#287 / D5, codex#4).
    files = [file for file in files if file.endswith((".py", ".j2", ".yaml", ".txt", ".json"))]
    files = [file for file in files if not file.endswith("__init__.py")]
    return files


def platform_watch_roots(sources: list[str]) -> list[str]:
    """Walk targets for one platform's `nos_plugins` source list (#281 / D4).

    `sources` is the registry entry `nos_plugins[<platform>]`: an A3 platform dir
    and/or a legacy `platforms_py/<name>.py` module. Each maps to its watch
    target(s):

    - an A3 dir            -> the dir itself (recursively walked)
    - a legacy `<name>.py` -> the `.py` plus its jinja inputs
      (`configurations/<name>.yaml.j2`, `templates/<name>/`), mirroring the
      `_legacy_jinja_to_py` reverse map so editing a template reloads the module.

    A dual-source platform (e.g. cisco_ios = A3 dir + py module) yields both,
    preserving the prior whole-tree watcher's coverage. Existence is NOT checked
    here — a jinja input does not exist for every legacy platform;
    `get_files_under_roots` skips non-existent roots at walk time (#281 / Risks).
    """
    roots: list[str] = []
    for source in sources:
        if source.endswith(".py"):
            base = os.path.dirname(source)
            name = os.path.basename(source)[: -len(".py")]
            roots.append(source)
            roots.append(os.path.join(base, "configurations", f"{name}.yaml.j2"))
            roots.append(os.path.join(base, "templates", name))
        else:
            roots.append(source)
    return roots


def get_files_under_roots(roots: list[str]) -> list[str]:
    """Collect watched files across `roots` (dir walked / file as-is / missing skipped).

    A root is a directory (recursively walked with `get_files_under_directory`'s
    extension filter) or an individual file (a legacy py module / jinja input,
    taken as-is when it exists). A non-existent root is silently skipped — the
    dev watcher's normal state, since `platform_watch_roots` emits jinja paths
    that only some platforms ship (#281 / D4, Risks).
    """
    files: list[str] = []
    for root in roots:
        if os.path.isdir(root):
            files += get_files_under_directory(root)
        elif os.path.isfile(root):
            files.append(root)
    return files


def _get_mtime(file: str) -> float | None:
    """Return the file's st_mtime, or None if the file vanished.

    A file may vanish between the directory walk and the stat (e.g.
    another process replaces or removes it); callers skip such files and
    the next poll picks up their final state.
    """
    try:
        return os.stat(file).st_mtime
    except FileNotFoundError:
        return None


def get_files_lasttime_changed(files: list[str]):
    """Method to get files last time changed

    Files that vanished since the walk are skipped (see `_get_mtime`).
    """
    files_lasttime_changed: dict[str, float] = {}
    for file in files:
        mtime = _get_mtime(file)
        if mtime is not None:
            files_lasttime_changed[file] = mtime
    return files_lasttime_changed


def get_new_files(old_files: list[str], new_files: list[str]):
    """Compare old files with new files and return new files"""
    return [file for file in new_files if file not in old_files]


def get_files_recently_modified(files: list[str], files_lasttime_changed_old: dict[str, float]):
    """Method to get files recently modified

    Files that vanished since the walk are not reported as modified
    (see `_get_mtime`).
    """
    files_recently_modified: list[str] = []
    for file in files:
        mtime = _get_mtime(file)
        if mtime is not None and mtime != files_lasttime_changed_old.get(file, 0):
            files_recently_modified.append(file)
    return files_recently_modified


def _legacy_jinja_to_py(filepath: str) -> str | None:
    """Map a legacy py-plugin `.j2` template to its `.py` module, or None.

    Recognizes the two shipped legacy shapes only, by segment position:

    - ``<base>/configurations/<platform>.yaml.j2`` -> ``<base>/<platform>.py``
    - ``<base>/templates/<platform>/<cmd>.j2``     -> ``<base>/<platform>.py``

    Any other `.j2` (e.g. a stray ``README.j2`` under the watch root) returns
    None so the caller drops it — mapping it blindly would fabricate a bogus
    py path that `from_file` can only fail on (1st round codex #1). Only
    reached for `.j2` paths NOT under an A3 platform dir (those are rolled up
    by `resolve_reload_targets` first — A3 priority). POSIX ``/`` separators
    are a pre-existing assumption of the legacy py-plugin layout (unlike the
    ``os.sep``-aware `_a3_platform_dir`).
    """
    parts = filepath.split("/")
    if len(parts) >= 3 and parts[-2] == "configurations" and parts[-1].endswith(".yaml.j2"):
        platform = parts[-1][: -len(".yaml.j2")]
        return "/".join([*parts[:-2], f"{platform}.py"])
    if len(parts) >= 4 and parts[-3] == "templates":
        return "/".join([*parts[:-3], f"{parts[-2]}.py"])
    return None


def _a3_platform_dir(parts: list[str], root_parts: list[str]) -> str | None:
    """Return the A3 platform dir a changed-file path belongs to, or None.

    `parts` / `root_parts` are `os.sep`-split paths. A match needs the path to be
    `<root>/platforms/<p>/<at least one more segment>` — the `len >= n + 3` guard
    keeps a stray `platforms/foo.yaml` (a file directly under `platforms/`) from
    being rolled up to a bogus dir, and the exact `"platforms"` segment match
    (not substring) keeps `platforms_py/...` out (#274 / D1).
    """
    n = len(root_parts)
    if len(parts) >= n + 3 and parts[:n] == root_parts and parts[n] == "platforms":
        return os.sep.join(parts[: n + 2])
    return None


def resolve_reload_targets(files: list[str], root: str) -> list[str]:
    """Map changed files to the reload units `Nos.from_file` accepts (#274 / D1).

    A3 command data lives in `<root>/platforms/<p>/{platform.yaml,commands/*}`;
    `from_file` reloads a *platform dir*, not an individual command file, so any
    changed file under `platforms/<p>/` is rolled up to that dir. This branch is
    first (A3 priority) so an A3 `commands/*.j2` is not misrouted to a py path by
    the legacy `.j2` mapping. py plugins (and their adjacent legacy-shape `.j2`
    config/templates) map to their `.py` module. Everything else is dropped — a
    non-plugin file, an unrecognized `.j2`, or a whole-platform deletion whose
    dir is gone (`from_file` would only raise on it) — and logged for "why
    didn't my edit reload?" troubleshooting. Targets are deduped and sorted
    (deterministic order; the merge is order-invariant for commands,
    last-writer for scalars).
    """
    root_parts = os.path.normpath(root).split(os.sep)
    targets: set[str] = set()
    for file in files:
        parts = os.path.normpath(file).split(os.sep)
        platform_dir = _a3_platform_dir(parts, root_parts)
        if platform_dir is not None:
            # An A3 path is claimed here even when its platform dir is gone
            # (whole-platform deletion): falling through to the legacy `.j2`
            # branch would fabricate a bogus py path for an A3 `commands/*.j2`.
            if os.path.isdir(platform_dir):
                targets.add(platform_dir)
            else:
                log.debug("hot-reload: ignoring %s (platform dir %s is gone)", file, platform_dir)
        elif file.endswith(".j2") and (py_target := _legacy_jinja_to_py(file)) is not None:
            targets.add(py_target)
        elif file.endswith(".py"):
            targets.add(file)
        else:
            log.debug("hot-reload: ignoring non-reloadable changed path %s", file)
    return sorted(targets)


def get_files_changed(
    watch_roots: list[str], package_root: str, snapshot: dict[str, float]
) -> tuple[list[str], dict[str, float]]:
    """Diff the watched files against `snapshot`; return (reload targets, new snapshot).

    Pure function (#281 / D3): no module-global state and no in-place mutation of
    `snapshot`. The caller — the per-shell `precmd` — owns the snapshot dict and
    swaps in the returned one, so each shell tracks its own platform subtree
    independently (no consume-once sharing, the #281 fix). New, modified, and
    deleted paths are rolled up to reload units by `resolve_reload_targets`
    against `package_root` (the `plugins/nos` tree, so an A3 file still folds to
    its platform dir, D8). Deletion matters for A3 (a removed `commands/*` file
    is a command removal); the platform dir is still healthy so the rollup
    reloads it and the removal propagates.

    Unlike the #274 module-global watcher, there is no first-poll re-seed branch:
    the per-shell baseline is seeded once at connection time (`__init__`, D5), so
    every `precmd` poll diffs against that baseline and the first command can
    already reflect an edit.
    """
    files = get_files_under_roots(watch_roots)
    current = set(files)
    changed: list[str] = []
    changed += get_new_files(list(snapshot), files)
    changed += get_files_recently_modified(files, snapshot)
    # Deletion: paths in the prior snapshot that are gone from this walk.
    changed += [path for path in snapshot if path not in current]
    targets = resolve_reload_targets(changed, package_root)
    return targets, get_files_lasttime_changed(files)
