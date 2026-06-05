"""
This module is intended to be used
a collection of utilities for the shell.
"""

import os


def get_files_under_directory(directory):
    """Method to get files under a directory"""
    files: list = []
    for root, _, filenames in os.walk(directory):
        if "__pycache__" in root:
            continue
        files += [os.path.join(root, filename) for filename in filenames]
    files = [file for file in files if os.path.isfile(file)]
    files = [file for file in files if file.endswith((".py", ".j2", ".yaml"))]
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


def change_jinja_to_corresponding_py(files: list[str]):
    """Method to change j2 files to corresponding py files"""
    jinja_files = [file for file in files if file.endswith(".j2")]
    files: set = {file for file in files if not file.endswith(".j2")}
    for filepath in jinja_files:
        if "configurations" in filepath:
            base_filepath = filepath.rsplit("/", 2)[0]
            platform = os.path.basename(filepath).replace(".yaml.j2", "").replace(".yaml", "")
            files.add(f"{base_filepath}/{platform}.py")
        else:
            split: list[str] = filepath.rsplit("/", 3)
            corresponding_py_module = f"{split[0]}/{split[2]}.py"
            files.add(corresponding_py_module)
    return list(files)


# Module-level cache for get_files_changed. Previously stored as a
# function attribute (get_files_changed.files_lasttime_changed_old),
# which defeats static type analysis. Moved to module scope so ty can
# track the type properly.
_files_lasttime_changed_old: dict[str, float] = {}


def get_files_changed(directory: str):
    """Method to get files changed under a directory"""
    global _files_lasttime_changed_old
    files_changed: list[str] = []
    files_under_directory: list[str] = get_files_under_directory(directory)
    if not _files_lasttime_changed_old:
        _files_lasttime_changed_old = get_files_lasttime_changed(files_under_directory)
    files_changed += get_new_files(list(_files_lasttime_changed_old.keys()), files_under_directory)
    files_changed += get_files_recently_modified(files_under_directory, _files_lasttime_changed_old)
    files_changed = change_jinja_to_corresponding_py(files_changed)
    _files_lasttime_changed_old = get_files_lasttime_changed(files_under_directory)
    return files_changed
