"""Unit tests for the test helpers in ``tests/utils.py``."""

from types import SimpleNamespace
from typing import cast

from simnos.core.host import Host
from simnos.core.resolved_command import (
    NO_OUTPUT,
    ModeDef,
    ResolvedCommand,
    ResolvedPlatform,
    Transition,
    compile_template,
)
from simnos.plugins.nos.platforms_py import huawei_smartax
from tests.utils import get_host_commands


class TestGetHostCommandsChangesPrompt:
    """Regression pin for the `changes_prompt` filter in `get_host_commands` (#115).

    huawei_smartax's `return` / `disable` are callable-output commands whose
    transition (`new_mode`/`exit`) is decided at dispatch time, so it is invisible
    to the static legacy-dict read the sweep does. Without the `changes_prompt`
    skip the sweep would run them and hit a netmiko ReadTimeout. Previously this
    was only pinned indirectly by the slow huawei integration sweep; these tests
    pin the filter and the real authoring data directly. #317 removes the need
    once A3 authors handlers with a static new_mode.
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

    def test_changes_prompt_is_the_sole_reason_the_command_is_skipped(self):
        """A `changes_prompt` command is excluded from every bucket; a plain sibling isn't.

        The flagged command uses a neutral name (`widget reset`) that is not in the
        exit-name set and carries no `new_prompt`/`alias`/`exit`, so `changes_prompt`
        is the *only* condition that can drive its exclusion — the test cannot pass
        falsely via a different filter branch (1st round codex/claude).
        """
        host = self._legacy_host(
            {
                "show widget": {"output": "v", "prompt": "R1>"},
                "widget reset": {"output": "x", "prompt": "R1>", "changes_prompt": True},
            }
        )
        initial, enable, config = get_host_commands(host)
        assert "show widget" in initial  # plain sibling is swept
        assert "widget reset" not in initial + enable + config  # flagged command is skipped

    def test_huawei_transition_commands_carry_the_marker(self):
        """The real huawei_smartax authoring data flags its callable transitions (#115).

        Pins the actual `commands` dict (not a synthetic one) so a marker dropped
        from `return` / `disable` is caught here directly, instead of only by the
        slow netmiko sweep (1st round codex/claude).
        """
        for name in ("return", "disable"):
            assert huawei_smartax.commands[name]["changes_prompt"] is True


class TestGetHostCommandsA3Transitions:
    """The A3 sweep skips `transitions` commands like static `new_mode`/`exit` (#317 P-1).

    A `transitions` command changes mode / closes the session at dispatch time, so
    running it in the flat netmiko sweep would trip a mode change / ReadTimeout —
    the same reason `new_mode` / `exit` are skipped. Pins the `rc.transitions`
    branch added to `get_host_commands`.
    """

    @staticmethod
    def _a3_host(commands: dict[str, ResolvedCommand]) -> Host:
        template, _ = compile_template("{{ base_prompt }}>")
        platform = ResolvedPlatform(
            modes={"user": ModeDef(name="user", prompt_template=template)},
            initial_mode="user",
            commands=commands,
        )
        # `get_host_commands` walks the legacy `nos.commands` dict first, then the
        # A3 `resolved_platform`; give the fake nos an empty legacy dict so only
        # the A3 branch contributes.
        nos = SimpleNamespace(name="t", commands={}, resolved_platform=platform)
        return cast(Host, SimpleNamespace(nos=nos))

    def test_transitions_command_is_skipped(self):
        plain = ResolvedCommand(
            name="show widget",
            modes=frozenset({"user"}),
            new_mode=None,
            output=NO_OUTPUT,
            variants=(),
            help="",
            exit=False,
            type="simnos",
        )
        transitioning = ResolvedCommand(
            name="toggle",
            modes=frozenset({"user"}),
            new_mode=None,
            output=NO_OUTPUT,
            variants=(),
            help="",
            exit=False,
            type="simnos",
            transitions={"user": Transition(exit=True)},
        )
        host = self._a3_host({"show widget": plain, "toggle": transitioning})
        initial, enable, config = get_host_commands(host)
        assert "show widget" in initial  # plain command is swept
        assert "toggle" not in initial + enable + config  # transitions command is skipped
