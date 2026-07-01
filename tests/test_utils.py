"""Unit tests for the test helpers in ``tests/utils.py``."""

from types import SimpleNamespace
from typing import cast

from simnos.core.host import Host
from tests.utils import get_host_commands


class TestGetHostCommandsChangesPrompt:
    """Regression pin for the `changes_prompt` filter in `get_host_commands` (#115).

    huawei_smartax's `return` / `disable` are callable-output commands whose
    transition (`new_mode`/`exit`) is decided at dispatch time, so it is invisible
    to the static legacy-dict read the sweep does. Without the `changes_prompt`
    skip the sweep would run them and hit a netmiko ReadTimeout. Previously this
    was only pinned indirectly by the slow huawei integration sweep; this test
    pins the filter directly. #317 removes the need once A3 authors handlers with
    a static new_mode.
    """

    @staticmethod
    def _legacy_host(commands: dict) -> Host:
        """A minimal duck-typed host exposing a legacy (no-A3) nos to the sweep."""
        nos = SimpleNamespace(
            name="t",
            initial_prompt="R1>",
            enable_prompt=None,
            config_prompt=None,
            resolved_platform=None,
            commands=commands,
        )
        return cast(Host, SimpleNamespace(nos=nos))

    def test_changes_prompt_command_is_skipped(self):
        """A `changes_prompt` command is excluded from every bucket; a sibling isn't."""
        host = self._legacy_host(
            {
                "show version": {"output": "v", "prompt": "R1>"},
                "return": {"output": "x", "prompt": "R1>", "changes_prompt": True},
            }
        )
        initial, enable, config = get_host_commands(host)
        assert "show version" in initial
        assert "return" not in initial + enable + config
