"""Integration tests for the A3 platform path through Nos -> CMDShell (#264 / PR-2).

PR-1 covered the legacy adapter end of `_rebuild`; these pin the new A3 branch:
`Nos._from_platform_dir` loads a platform dir into `resolved_platform`, and the
shell merges the still-legacy inflows (BASIC, py-module commands, inventory)
over the A3 statics with the right precedence and the A3 modes.
"""

import threading

import pytest

from simnos.core.nos import Nos
from simnos.plugins.shell.cmd_shell import CMDShell, build_resolved_platform


def _write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _a3_platform(tmp_path, *, auth=None):
    """A minimal A3 cisco-like platform dir with user/enable/config modes."""
    root = tmp_path / "cisco_ios"
    meta = (
        "modes:\n"
        '  user:\n    prompt: "{{ base_prompt }}>"\n'
        '  enable:\n    prompt: "{{ base_prompt }}#"\n'
        '  config:\n    prompt: "{{ base_prompt }}(config)#"\n'
        "initial_mode: user\n"
    )
    if auth is not None:
        meta += f"auth: {auth}\n"
    _write(root / "platform.yaml", meta)
    commands = root / "commands"
    _write(
        commands / "show_version.yaml", "command: show version\ntype: ntc\nmode: [enable]\noutput: show_version.txt\n"
    )
    _write(commands / "show_version.txt", "Cisco IOS Software, Version 15.0\n")
    _write(commands / "enable.yaml", "command: enable\ntype: simnos\nmode: [user]\nnew_mode: enable\n")
    _write(commands / "default.yaml", "command: _default_\ntype: simnos\noutput: default.txt\n")
    _write(commands / "default.txt", "% Invalid input detected\n")
    return root


def _shell_for(nos, *, inventory_config=None):
    return CMDShell(
        stdin=None,
        stdout=None,
        nos=nos,
        nos_inventory_config=inventory_config or {},
        base_prompt="R1",
        is_running=threading.Event(),
    )


class TestNosFromPlatformDir:
    def test_loads_resolved_platform(self, tmp_path):
        root = _a3_platform(tmp_path)
        nos = Nos(filename=str(root))
        assert nos.resolved_platform is not None
        assert nos.name == "cisco_ios"
        assert set(nos.resolved_platform.modes) == {"user", "enable", "config"}
        assert nos.resolved_platform.initial_mode == "user"
        assert "show version" in nos.resolved_platform.commands

    def test_legacy_commands_stay_empty(self, tmp_path):
        # The A3 path does not populate the legacy command dict / scalar prompts.
        nos = Nos(filename=str(_a3_platform(tmp_path)))
        assert nos.commands == {}

    def test_auth_is_wired_from_platform_meta(self, tmp_path):
        # `auth` has live SSH behavior, so it must reach nos.auth, not be a dead
        # schema field (#264 / claude #2).
        nos = Nos(filename=str(_a3_platform(tmp_path, auth="none")))
        assert nos.auth == "none"
        assert nos.resolved_platform.auth == "none"

    def test_auth_defaults_none(self, tmp_path):
        nos = Nos(filename=str(_a3_platform(tmp_path)))
        assert nos.auth is None

    def test_shell_merged_platform_carries_auth(self, tmp_path):
        # The merged ResolvedPlatform the shell builds must mirror the A3 auth,
        # not silently drop it (2nd round codex/claude #3).
        shell = _shell_for(Nos(filename=str(_a3_platform(tmp_path, auth="none"))))
        assert shell.platform.auth == "none"


class TestShellA3Path:
    def test_modes_and_prompt_from_a3(self, tmp_path):
        shell = _shell_for(Nos(filename=str(_a3_platform(tmp_path))))
        assert shell.current_mode == "user"
        assert shell.prompt == "R1>"
        assert set(shell.platform.modes) == {"user", "enable", "config"}

    def test_a3_static_command_resolved(self, tmp_path):
        shell = _shell_for(Nos(filename=str(_a3_platform(tmp_path))))
        cmd = shell.commands["show version"]
        assert cmd.modes == frozenset({"enable"})
        assert cmd.output.render("R1") == "Cisco IOS Software, Version 15.0\n"

    def test_a3_default_overrides_basic_default(self, tmp_path):
        # BASIC contributes a generic _default_; the A3 platform's own _default_
        # sits above it (BASIC < A3) and wins.
        shell = _shell_for(Nos(filename=str(_a3_platform(tmp_path))))
        assert shell.commands["_default_"].output.render("R1") == "% Invalid input detected\n"

    def test_basic_exit_still_present(self, tmp_path):
        shell = _shell_for(Nos(filename=str(_a3_platform(tmp_path))))
        assert shell.commands["exit"].exit is True

    def test_py_module_command_overrides_a3_static(self, tmp_path):
        # Simulate a py module loaded after the A3 dir: it fills nos.commands
        # with a dynamic handler that overrides the A3 static `show version`.
        nos = Nos(filename=str(_a3_platform(tmp_path)))
        handler = lambda **kwargs: "dynamic"  # noqa: E731 — minimal handler stand-in
        nos.commands = {"show version": {"output": handler, "help": "dyn", "prompt": "{base_prompt}#"}}
        shell = _shell_for(nos)
        cmd = shell.commands["show version"]
        assert cmd.output.kind == "handler"  # py handler won over the A3 literal
        assert cmd.modes == frozenset({"enable"})  # reverse-mapped via A3 modes

    def test_inventory_command_merges_over_a3(self, tmp_path):
        nos = Nos(filename=str(_a3_platform(tmp_path)))
        inventory = {"commands": {"show inventory": {"output": "INV", "help": "inv", "prompt": "{base_prompt}>"}}}
        shell = _shell_for(nos, inventory_config=inventory)
        assert shell.commands["show inventory"].output.render("R1") == "INV"
        assert shell.commands["show inventory"].modes == frozenset({"user"})

    def test_shell_reuses_shared_platform(self, tmp_path):
        # The server builds the merged platform once (per host) and passes it in;
        # the shell installs that exact object instead of re-normalizing (#264 / Impact).
        nos = Nos(filename=str(_a3_platform(tmp_path)))
        shared = build_resolved_platform(nos, {})
        shell = CMDShell(
            stdin=None,
            stdout=None,
            nos=nos,
            nos_inventory_config={},
            base_prompt="R1",
            is_running=threading.Event(),
            resolved_platform=shared,
        )
        assert shell.platform is shared
        assert shell.current_mode == "user"
        assert shell.prompt == "R1>"

    def test_build_shared_platform_none_when_reload_enabled(self, tmp_path, monkeypatch):
        # Dev hot-reload mode: no frozen snapshot, so each connection rebuilds
        # from live nos and file edits propagate to new connections.
        nos = Nos(filename=str(_a3_platform(tmp_path)))
        monkeypatch.setenv("SIMNOS_RELOAD_COMMANDS", "1")
        assert CMDShell.build_shared_platform(nos, {}) is None
        monkeypatch.delenv("SIMNOS_RELOAD_COMMANDS")
        assert CMDShell.build_shared_platform(nos, {}) is not None

    def test_a3_rebuild_is_atomic_on_broken_inflow(self, tmp_path):
        # A broken legacy inflow (canonical-外 prompt the A3 reverse map cannot
        # resolve) must raise without leaving self.* half-updated — same atomic
        # contract the legacy path keeps (#264 / claude #7, D5).
        shell = _shell_for(Nos(filename=str(_a3_platform(tmp_path))))
        good_commands = shell.commands
        good_prompt = shell.prompt
        shell._inventory_commands = {"bad": {"output": "x", "prompt": "{base_prompt}@@unmappable"}}
        with pytest.raises(ValueError):
            shell._rebuild()
        assert shell.commands is good_commands  # unchanged reference
        assert shell.prompt == good_prompt
