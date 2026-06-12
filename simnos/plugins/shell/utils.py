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
    # output file must trigger a reload like editing its yaml does.
    files = [file for file in files if file.endswith((".py", ".j2", ".yaml", ".txt"))]
    files = [file for file in files if not file.endswith("__init__.py")]
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


def _legacy_jinja_to_py(filepath: str) -> str:
    """Map one legacy py-plugin `.j2` template to its corresponding `.py` module.

    Preserves the pre-#274 conversion: a `configurations/<platform>.yaml.j2`
    config template and a `templates/<platform>/<cmd>.j2` output template both
    reload by re-importing the platform's `.py` module. Only reached for `.j2`
    paths that are NOT under an A3 platform dir (those are rolled up to the dir
    by `resolve_reload_targets` first — A3 priority).
    """
    if "configurations" in filepath:
        base_filepath = filepath.rsplit("/", 2)[0]
        platform = os.path.basename(filepath).replace(".yaml.j2", "").replace(".yaml", "")
        return f"{base_filepath}/{platform}.py"
    split = filepath.rsplit("/", 3)
    return f"{split[0]}/{split[2]}.py"


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
    the legacy `.j2` mapping. py plugins (and their adjacent `.j2`
    config/templates) map to their `.py` module. A path that is neither — a
    non-plugin file, or a whole-platform deletion whose dir is gone — is dropped
    (`from_file` would only raise on it) and logged for "why didn't my edit
    reload?" troubleshooting. Targets are deduped and sorted (deterministic
    order; the merge is order-invariant for commands, last-writer for scalars).
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
                log.debug("hot-reload: ignoring path of deleted platform %s", file)
        elif file.endswith(".j2"):
            targets.add(_legacy_jinja_to_py(file))
        elif file.endswith(".py"):
            targets.add(file)
        else:
            log.debug("hot-reload: ignoring non-reloadable changed path %s", file)
    return sorted(targets)


# Module-level cache for get_files_changed. Previously stored as a
# function attribute (get_files_changed.files_lasttime_changed_old),
# which defeats static type analysis. Moved to module scope so ty can
# track the type properly. `_watch_root` pairs the snapshot with the directory
# it was taken under so a changed watch root re-seeds instead of reporting every
# prior-root path as a deletion (#274 / D7).
_files_lasttime_changed_old: dict[str, float] = {}
_watch_root: str | None = None


def get_files_changed(directory: str) -> list[str]:
    """Return the reload targets for files changed under `directory` (#274 / D1, D7).

    First observation of a (new) watch root only seeds the snapshot and returns
    no targets — a diff needs a prior baseline. Subsequent polls report new,
    modified, and deleted paths, rolled up to reload targets by
    `resolve_reload_targets`. Deletion matters for A3 (a removed `commands/*`
    file is a command removal); the platform dir is still healthy so the rollup
    reloads it and the removal propagates.
    """
    global _files_lasttime_changed_old, _watch_root
    files_under_directory = get_files_under_directory(directory)
    # Re-seed (no diff) on first ever poll or when the watch root changes, so a
    # stale prior-root snapshot does not surface every old path as a deletion.
    if _watch_root != directory or not _files_lasttime_changed_old:
        _watch_root = directory
        _files_lasttime_changed_old = get_files_lasttime_changed(files_under_directory)
        return []
    files_changed: list[str] = []
    files_changed += get_new_files(list(_files_lasttime_changed_old.keys()), files_under_directory)
    files_changed += get_files_recently_modified(files_under_directory, _files_lasttime_changed_old)
    # Deletion (D7): paths in the prior snapshot that are gone from this walk.
    current = set(files_under_directory)
    files_changed += [path for path in _files_lasttime_changed_old if path not in current]
    targets = resolve_reload_targets(files_changed, directory)
    _files_lasttime_changed_old = get_files_lasttime_changed(files_under_directory)
    return targets
