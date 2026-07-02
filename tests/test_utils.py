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
from tests.utils import get_host_commands


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
