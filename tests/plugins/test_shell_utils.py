"""
Test module fpr the tests of the shell utils
"""

import os
import random
import time
from unittest import TestCase
from unittest.mock import patch

from simnos.plugins.shell.utils import (
    get_files_changed,
    get_files_lasttime_changed,
    get_files_recently_modified,
    get_files_under_directory,
    get_files_under_roots,
    get_new_files,
    platform_watch_roots,
    resolve_reload_targets,
)

RANDOM_FILE: str = random.choice(
    [file for file in get_files_under_directory("simnos/plugins/nos") if file.endswith((".py", ".yaml"))]
)


class MockStatResult:
    """Mocking class for os.stat"""

    def __init__(self, original_stat_result, file):
        """Mocking class for os.stat"""
        self._original_stat_result = original_stat_result
        self._file = file

    @property
    def st_mtime(self):
        """Mocking st_mtime"""
        if self._file == RANDOM_FILE:
            return time.time()
        return self._original_stat_result.st_mtime

    def __getattr__(self, name):
        return getattr(self._original_stat_result, name)


def mock_os_stat(file):
    """Mocking os.stat"""
    original_stat_result = original_os_stat(file)
    return MockStatResult(original_stat_result, file)


original_os_stat = os.stat


class ShellUtilsTest(TestCase):
    """Test class for the shell utils.

    `get_files_changed` is a pure function since #281 (no module-global snapshot),
    so these tests need no reset fixture: each call diffs an explicit caller-owned
    snapshot against the current walk.
    """

    def test_get_files_under_directory(self):
        """
        Test method for the get_files_under_directory
        """
        files = get_files_under_directory("simnos/plugins/nos")
        self.assertTrue(files)
        self.assertTrue(all(not file.endswith("__init__.py") for file in files))
        # Every returned file is a watched extension; `.txt` is watched so an A3
        # literal-capture edit triggers a reload (#274 / D2), and `.json` so a
        # #287 sidecar value edit reloads too.
        self.assertTrue(all(file.endswith((".py", ".j2", ".yaml", ".txt", ".json")) for file in files))
        self.assertTrue(any(file.endswith(".txt") for file in files))
        self.assertTrue(any(file.endswith(".json") for file in files))

    def test_get_files_lasttime_changed(self):
        """
        Test to check if we get the last time
        that the files has been changed correctly.
        """
        files = get_files_under_directory("simnos/plugins/nos")
        files_lasttime_changed = get_files_lasttime_changed(files)
        self.assertTrue(files_lasttime_changed)
        self.assertTrue(all(file in files_lasttime_changed for file in files))
        self.assertTrue(all(files_lasttime_changed[file] for file in files))
        self.assertTrue(all(files_lasttime_changed[file] > 0 for file in files))

    def test_get_new_files(self):
        """
        Test to check if we get the new files
        """
        old_files = ["file1", "file2"]
        new_files = ["file2", "file3"]
        self.assertEqual(get_new_files(old_files, new_files), ["file3"])

    def test_get_files_recently_modified(self):
        """
        Test to check if we get the files that have been recently modified
        """
        files = get_files_under_directory("simnos/plugins/nos")
        files_lasttime_changed = get_files_lasttime_changed(files)
        with patch("os.stat", side_effect=mock_os_stat):
            files = get_files_recently_modified(files, files_lasttime_changed)
        self.assertTrue(files)
        self.assertIn(RANDOM_FILE, files)
        self.assertTrue(all(files_lasttime_changed[file] != 0 for file in files))

    def test_get_files_lasttime_changed_vanished_file_skipped(self):
        """A file that vanished between walk and stat is skipped, not raised.

        Pins the FileNotFoundError tolerance (#232): another process may
        remove or replace a file after the directory walk collected it;
        the stat used to propagate and crash the hot-reload caller.
        """
        files = get_files_under_directory("simnos/plugins/nos")
        vanished = "simnos/plugins/nos/platforms/vanished_after_walk/platform.yaml"
        files_lasttime_changed = get_files_lasttime_changed([*files, vanished])
        self.assertNotIn(vanished, files_lasttime_changed)
        self.assertTrue(all(file in files_lasttime_changed for file in files))

    def test_get_files_recently_modified_vanished_file_skipped(self):
        """A vanished file is not reported as modified, not raised.

        Same FileNotFoundError tolerance as `get_files_lasttime_changed`
        (#232) — the stat used to raise before the mtime comparison was
        ever reached.
        """
        files = get_files_under_directory("simnos/plugins/nos")
        vanished = "simnos/plugins/nos/platforms/vanished_after_walk/platform.yaml"
        files_lasttime_changed = get_files_lasttime_changed(files)
        modified = get_files_recently_modified([*files, vanished], files_lasttime_changed)
        self.assertNotIn(vanished, modified)

    def test_get_files_changed(self):
        """A changed file rolls up to its reload target against a caller snapshot.

        `get_files_changed` returns (reload targets, new snapshot) (#281 / D3): a
        changed A3 command file is rolled up to its platform dir, a `.py` module
        stays itself. The caller owns the baseline snapshot (seeded at connection
        time), so the test seeds it explicitly, then diffs with RANDOM_FILE bumped.
        """
        roots = ["simnos/plugins/nos"]
        package_root = "simnos/plugins/nos"
        snapshot = get_files_lasttime_changed(get_files_under_roots(roots))  # baseline (real mtimes)
        with patch("os.stat", side_effect=mock_os_stat):
            targets, _new_snapshot = get_files_changed(roots, package_root, snapshot)
        # RANDOM_FILE is the only change, so the result is exactly its rollup target.
        self.assertEqual(targets, resolve_reload_targets([RANDOM_FILE], package_root))

    def test_get_files_changed_null(self):
        """No change against a freshly-seeded snapshot yields no reload targets."""
        roots = ["simnos/plugins/nos"]
        snapshot = get_files_lasttime_changed(get_files_under_roots(roots))
        targets, _new_snapshot = get_files_changed(roots, "simnos/plugins/nos", snapshot)
        self.assertFalse(targets)


def test_get_files_under_directory_filters_extensions(tmp_path):
    """Watched extensions are included and everything else is excluded (#274 / D2).

    Pinned against a tmp tree because the real `plugins/nos` tree contains no
    non-watched files, making an `all(endswith(...))` over it vacuously true for
    exclusion. `.bak` exclusion is load-bearing: the hot-reload integration test
    (`HotReloadTest._atomic_write`) parks backup copies on `.bak` precisely so a
    mid-write file is never visible to a reload watcher (#232).
    """
    for name in ("keep.py", "keep.j2", "keep.yaml", "keep.txt", "skip.bak", "skip.md", "__init__.py"):
        (tmp_path / name).write_text("x", encoding="utf-8")
    files = {os.path.basename(f) for f in get_files_under_directory(str(tmp_path))}
    assert files == {"keep.py", "keep.j2", "keep.yaml", "keep.txt"}


# --- resolve_reload_targets (#274 / D1) --------------------------------------
#
# `resolve_reload_targets` maps changed files to the reload units `from_file`
# accepts: an A3 file rolls up to its platform dir (`from_file` reloads a dir,
# not a single command file), a `.py` module stays itself, a legacy py-plugin
# `.j2` maps to its `.py`, everything else is dropped. These replace the old
# `change_jinja_to_corresponding_py` tests, using a tmp tree for precision.


def _make_nos_tree(base):
    """Build a minimal ``plugins/nos``-shaped tree under ``base``; return its root."""
    root = base / "nos"
    cisco = root / "platforms" / "cisco_ios" / "commands"
    cisco.mkdir(parents=True)
    (root / "platforms" / "cisco_ios" / "platform.yaml").write_text("modes: {}\n", encoding="utf-8")
    (cisco / "show.yaml").write_text("command: show\n", encoding="utf-8")
    (cisco / "show.txt").write_text("out\n", encoding="utf-8")
    (cisco / "show.j2").write_text("{{ base_prompt }}\n", encoding="utf-8")
    (root / "platforms_py").mkdir(parents=True)
    (root / "platforms_py" / "cisco_ios.py").write_text("NAME = 'cisco_ios'\n", encoding="utf-8")
    return root


def test_resolve_targets_a3_files_roll_up_to_platform_dir(tmp_path):
    """Every A3 file (yaml/txt/j2/platform.yaml) rolls up to its platform dir."""
    root = _make_nos_tree(tmp_path)
    platform_dir = str(root / "platforms" / "cisco_ios")
    for rel in ("platform.yaml", "commands/show.yaml", "commands/show.txt", "commands/show.j2"):
        changed = str(root / "platforms" / "cisco_ios" / rel)
        assert resolve_reload_targets([changed], str(root)) == [platform_dir]


def test_resolve_targets_dedup_same_platform(tmp_path):
    """Multiple edits in one platform collapse to a single dir target."""
    root = _make_nos_tree(tmp_path)
    platform_dir = str(root / "platforms" / "cisco_ios")
    changed = [
        str(root / "platforms" / "cisco_ios" / "commands" / "show.yaml"),
        str(root / "platforms" / "cisco_ios" / "commands" / "show.txt"),
        str(root / "platforms" / "cisco_ios" / "platform.yaml"),
    ]
    assert resolve_reload_targets(changed, str(root)) == [platform_dir]


def test_resolve_targets_py_module_passthrough(tmp_path):
    """A `platforms_py/<p>.py` edit stays itself (not mistaken for an A3 dir)."""
    root = _make_nos_tree(tmp_path)
    pyfile = str(root / "platforms_py" / "cisco_ios.py")
    assert resolve_reload_targets([pyfile], str(root)) == [pyfile]


def test_resolve_targets_legacy_jinja_configurations(tmp_path):
    """A legacy `configurations/<p>.yaml.j2` maps to its `.py` module."""
    root = _make_nos_tree(tmp_path)
    j2 = str(root / "platforms_py" / "configurations" / "huawei_smartax.yaml.j2")
    assert resolve_reload_targets([j2], str(root)) == [str(root / "platforms_py" / "huawei_smartax.py")]


def test_resolve_targets_legacy_jinja_templates(tmp_path):
    """A legacy `templates/<p>/<cmd>.j2` maps to its `.py` module."""
    root = _make_nos_tree(tmp_path)
    j2 = str(root / "platforms_py" / "templates" / "cisco_ios" / "show_run.j2")
    assert resolve_reload_targets([j2], str(root)) == [str(root / "platforms_py" / "cisco_ios.py")]


def test_resolve_targets_drops_non_plugin_and_stray(tmp_path):
    """Non-plugin files and a stray file directly under `platforms/` are dropped."""
    root = _make_nos_tree(tmp_path)
    assert resolve_reload_targets([str(root / "README.txt")], str(root)) == []
    # `platforms/foo.yaml` has no `<p>/` level (min-segment guard) -> dropped.
    assert resolve_reload_targets([str(root / "platforms" / "foo.yaml")], str(root)) == []


def test_resolve_targets_drops_unrecognized_jinja(tmp_path):
    """A `.j2` outside the two legacy py-plugin shapes is dropped, not mapped.

    Blindly mapping (the old behavior) would fabricate a bogus `.py` target for
    e.g. a stray `README.j2` and re-introduce the every-poll error log the drop
    branch exists to prevent (1st code review codex #1).
    """
    root = _make_nos_tree(tmp_path)
    stray = str(root / "README.j2")
    unknown_shape = str(root / "platforms_py" / "notes" / "foo.j2")
    # In the configurations dir but not a `<platform>.yaml.j2` — without the
    # suffix check this would fabricate `README.j2.py` (2nd round codex #1).
    non_config = str(root / "platforms_py" / "configurations" / "README.j2")
    assert resolve_reload_targets([stray, unknown_shape, non_config], str(root)) == []


def test_resolve_targets_drops_deleted_platform_dir(tmp_path):
    """An old-only path whose whole platform dir is gone is dropped (not reloaded).

    The `.j2` case pins that a deleted platform's A3 path never falls through to
    the legacy `.j2`->py mapping (which would fabricate a bogus py target).
    """
    root = _make_nos_tree(tmp_path)
    ghost_yaml = str(root / "platforms" / "ghost" / "commands" / "show.yaml")
    ghost_j2 = str(root / "platforms" / "ghost" / "commands" / "show.j2")
    assert resolve_reload_targets([ghost_yaml, ghost_j2], str(root)) == []


# --- platform_watch_roots / get_files_under_roots (#281 / D4) ----------------


def test_platform_watch_roots_a3_dir():
    """An A3 dir source maps to the dir itself (recursively walked)."""
    a3_dir = os.path.join("x", "platforms", "cisco_ios")
    assert platform_watch_roots([a3_dir]) == [a3_dir]


def test_platform_watch_roots_legacy_py():
    """A legacy `<name>.py` maps to the `.py` plus its jinja inputs."""
    py = os.path.join("x", "platforms_py", "foo.py")
    base = os.path.join("x", "platforms_py")
    assert platform_watch_roots([py]) == [
        py,
        os.path.join(base, "configurations", "foo.yaml.j2"),
        os.path.join(base, "templates", "foo"),
    ]


def test_platform_watch_roots_dual_source():
    """A dual-source platform (A3 dir + py) yields both, the py expanded to its jinja."""
    a3_dir = os.path.join("x", "platforms", "cisco_ios")
    py = os.path.join("x", "platforms_py", "cisco_ios.py")
    base = os.path.join("x", "platforms_py")
    assert platform_watch_roots([a3_dir, py]) == [
        a3_dir,
        py,
        os.path.join(base, "configurations", "cisco_ios.yaml.j2"),
        os.path.join(base, "templates", "cisco_ios"),
    ]


def test_platform_watch_roots_unregistered_empty():
    """An unregistered platform (empty sources) yields no watch roots (graceful, #281 / D4)."""
    assert platform_watch_roots([]) == []


def test_get_files_under_roots_mixes_dir_file_and_skips_missing(tmp_path):
    """A dir root is walked, a file root is taken as-is, a missing root is skipped (#281 / D4)."""
    d = tmp_path / "dir"
    d.mkdir()
    (d / "a.yaml").write_text("x", encoding="utf-8")
    mod = tmp_path / "mod.py"
    mod.write_text("x", encoding="utf-8")
    missing = str(tmp_path / "nope" / "x.yaml.j2")
    files = set(get_files_under_roots([str(d), str(mod), missing]))
    assert files == {str(d / "a.yaml"), str(mod)}


# --- get_files_changed pure-function diffs (#281 / D3) -----------------------


def test_get_files_changed_detects_deletion(tmp_path):
    """Deleting a command file rolls up to the (healthy) platform dir (#281 / D3)."""
    root = _make_nos_tree(tmp_path)
    platform_dir = str(root / "platforms" / "cisco_ios")
    roots = [platform_dir]  # per-platform watch root (D2)
    snapshot = get_files_lasttime_changed(get_files_under_roots(roots))  # baseline
    (root / "platforms" / "cisco_ios" / "commands" / "show.yaml").unlink()
    targets, _new_snapshot = get_files_changed(roots, str(root), snapshot)
    assert targets == [platform_dir]


def test_get_files_changed_new_file_detected(tmp_path):
    """A file added after the baseline seed is detected as a new reload target (#281 / D3).

    Mirrors the connection-time seed (an initially-empty snapshot) followed by a
    new `.py` plugin appearing — the per-shell baseline diffs it as new.
    """
    root = tmp_path / "nos"
    pyroot = root / "platforms_py"
    pyroot.mkdir(parents=True)
    roots = [str(pyroot)]
    snapshot = get_files_lasttime_changed(get_files_under_roots(roots))  # empty but valid baseline
    newplugin = pyroot / "newplugin.py"
    newplugin.write_text("NAME = 'x'\n", encoding="utf-8")
    targets, _new_snapshot = get_files_changed(roots, str(root), snapshot)
    assert targets == [str(newplugin)]
