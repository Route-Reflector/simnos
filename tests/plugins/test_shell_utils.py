"""
Test module fpr the tests of the shell utils
"""

import os
import random
import time
from unittest import TestCase
from unittest.mock import patch

from simnos.plugins.shell import utils as shell_utils
from simnos.plugins.shell.utils import (
    change_jinja_to_corresponding_py,
    get_files_changed,
    get_files_lasttime_changed,
    get_files_recently_modified,
    get_files_under_directory,
    get_new_files,
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
    """
    Test class for the shell utils
    """

    def setUp(self):
        """Reset the stateful get_files_changed cache before each test.

        Other tests in the same pytest-xdist worker (e.g. the hot-reload
        integration tests, which exercise `get_files_changed` via `precmd`
        with the absolute `nos.__path__[0]`) may have primed the
        module-level `_files_lasttime_changed_old` snapshot; without a
        reset, the relative-path calls below would treat every file as
        "new" and the first-call-returns-empty contract breaks.
        """
        shell_utils._files_lasttime_changed_old.clear()

    def tearDown(self):
        """Avoid leaking the stateful cache to other tests.

        Note: the previous implementation deleted the function attribute
        `get_files_changed.files_lasttime_changed_old`, which silently
        became a no-op when the cache moved to the module-level
        `_files_lasttime_changed_old` (ty adoption, M-9).
        """
        shell_utils._files_lasttime_changed_old.clear()

    def test_get_files_under_directory(self):
        """
        Test method for the get_files_under_directory
        """
        files = get_files_under_directory("simnos/plugins/nos")
        self.assertTrue(files)
        self.assertTrue(all(not file.endswith("__init__.py") for file in files))
        self.assertTrue(all(file for file in files if file.endswith((".py", ".j2", ".yaml"))))

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

    def test_change_jinja_to_corresponding_py(self):
        """
        Test to check if we change j2 files to corresponding py files
        """
        files = get_files_under_directory("simnos/plugins/nos")
        files = [file for file in files if "cisco_ios" in file]
        files = [file for file in files if file.endswith(".j2")]
        files = change_jinja_to_corresponding_py(files)
        self.assertTrue(files)
        self.assertTrue(all(not file.endswith(".j2") for file in files))
        self.assertTrue(all(file for file in files if file.endswith(".py")))
        self.assertTrue(all("cisco_ios" in file for file in files))

    def test_change_jinja_to_corresponding_py_null(self):
        """
        Test to check if we don't change any j2 files to corresponding py files
        """
        files = get_files_under_directory("simnos/plugins/nos")
        files = [file for file in files if "cisco_ios" in file]
        files = [file for file in files if file.endswith(".py")]
        files = change_jinja_to_corresponding_py(files)
        self.assertTrue(files)
        self.assertTrue(all(not file.endswith(".j2") for file in files))
        self.assertTrue(all(file for file in files if file.endswith(".py")))
        self.assertTrue(all("cisco_ios" in file for file in files))

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

    def test_get_files_changed(self):
        """
        Test to check if we get the files that have been changed
        """
        files = get_files_changed("simnos/plugins/nos")
        self.assertFalse(files)
        with patch("os.stat", side_effect=mock_os_stat):
            files = get_files_changed("simnos/plugins/nos")
        self.assertTrue(files)
        self.assertIn(RANDOM_FILE, files)
        files = get_files_changed("simnos/plugins/nos")

    def test_get_files_changed_null(self):
        """
        Test to check if we don't get the files that have been changed
        """
        files = get_files_changed("simnos/plugins/nos")
        self.assertFalse(files)
        files = get_files_changed("simnos/plugins/nos")
        self.assertFalse(files)
