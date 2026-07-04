"""
Module to test the cmd_shell plugin.

The fixture platform is the synthetic external custom asset
(``tests/assets/synthetic_custom/`` + ``synthetic_custom_handlers.py``) — the
same A3 dir + handler py shape every platform has since #317 P-4 (the legacy
py-dict / ``from_dict`` vehicles this module used to build shells from are
gone with the legacy base layer).
"""

import cmd
import contextlib
import importlib
import os
import pathlib
import tempfile
import threading
import time
from unittest import TestCase
from unittest.mock import Mock, patch

from netmiko import ConnectHandler
import pytest

from simnos.core.nos import Nos
from simnos.core.pydantic_models import EPHEMERAL_PORT
from simnos.core.simnos import SimNOS

# The module itself is imported too (as `cmd_shell_module` / `nos_registry`) so the
# hot-reload e2e can monkeypatch the watcher's registry + package-root lookups.
import simnos.plugins.nos as nos_registry
from simnos.plugins.nos import nos_plugins
import simnos.plugins.shell.cmd_shell as cmd_shell_module
from simnos.plugins.shell.cmd_shell import HANDLER_ERROR_OUTPUT, CMDShell, build_resolved_platform
from tests.utils import SYNTHETIC_CUSTOM_A3_DIR, SYNTHETIC_CUSTOM_HANDLERS, set_attr


def _nos_from_synthetic_asset() -> Nos:
    """Build a Nos from the committed synthetic custom platform (A3 dir + handler py)."""
    return Nos(filename=[SYNTHETIC_CUSTOM_A3_DIR, SYNTHETIC_CUSTOM_HANDLERS])


def make_cmd_shell_args() -> dict:
    """Build the CMDShell constructor kwargs shared across cmd_shell tests (SSoT)."""
    return {
        "nos": _nos_from_synthetic_asset(),
        "nos_inventory_config": {},
        "base_prompt": "test",
        "is_running": threading.Event(),
    }


@pytest.fixture
def cmd_shell_args():
    """CMDShell kwargs as a fixture (thin wrapper over make_cmd_shell_args)."""
    return make_cmd_shell_args()


def _expected_baseline(args: dict) -> dict:
    """Attribute values a CMDShell takes with no optional kwargs.

    `ruler` / `completekey` were removed with the cmd.Cmd base in #303 P3-3.
    """
    return {
        "intro": "Custom SSH Shell",
        "newline": "\r\n",
        "prompt": "test>",
        "base_prompt": args["base_prompt"],
    }


@pytest.mark.parametrize(
    "override_kwargs, expected_override",
    [
        ({}, {}),  # no optional kwargs (baseline)
        ({"intro": "Test Intro"}, {"intro": "Test Intro"}),
        ({"newline": "Test Newline"}, {"newline": "Test Newline"}),
        (
            {
                "intro": "Test Intro",
                "newline": "Test Newline",
            },
            {
                "intro": "Test Intro",
                "newline": "Test Newline",
            },
        ),
    ],
    ids=["baseline", "intro", "newline", "all"],
)
def test_init_kwargs(cmd_shell_args, override_kwargs, expected_override):
    """baseline + each optional kwarg; untouched attrs stay at their defaults."""
    shell = CMDShell(**cmd_shell_args, **override_kwargs)
    expected = {**_expected_baseline(cmd_shell_args), **expected_override}
    for attr, value in expected.items():
        assert getattr(shell, attr) == value
    # identity-pinned attrs (excluded from the equality table)
    assert shell.is_running is cmd_shell_args["is_running"]
    assert shell.nos is cmd_shell_args["nos"]
    assert shell.commands != {}


@pytest.mark.parametrize(
    "line",
    [
        "",
        "   ",
        "\t",
        "show version",
        "show  version",
        "sh ver",
        "?",
        "?show version",
        "? show version",
        "!foo",
        "! foo",
        "/foo",
        "-x",
        "1cmd",
        "show-version",
        "show ?",
        "EOF",
        "exit\r",
    ],
)
def test_parseline_matches_stdlib_oracle(cmd_shell_args, line):
    """`_parseline` stays byte-identical to the cmd.Cmd.parseline it replaced (#303 P3-3).

    Production no longer depends on stdlib `cmd`; this test imports it only as a
    reference oracle so any drift from the historical lexing contract (strip,
    leading ``?`` -> ``help ``, no-``do_shell`` ``!`` fall-through, identchars
    scan) fails loudly. SIMNOS defines no `do_shell`, matching a bare `cmd.Cmd()`.
    """
    shell = CMDShell(**cmd_shell_args)
    assert shell._parseline(line) == cmd.Cmd().parseline(line)


def test_no_do_shell_keeps_bang_fall_through():
    """CMDShell defines no `do_shell`, which `_parseline`'s `!` branch relies on (#303 P3-3).

    `_parseline` maps a leading `!` to `(None, None, line)` (fall-through to
    `_default_`) precisely because there is no `do_shell` to route to, and
    `dispatch` special-cases only EOF / help. This guards that contract: the
    oracle test compares against a bare `cmd.Cmd()`, so a `do_shell` added to
    CMDShell would silently change the `!` wire without failing it.
    """
    assert not hasattr(CMDShell, "do_shell")


def _merged_platform(platform: str):
    """Build the merged (BASIC < A3) `ResolvedPlatform` for a packaged platform.

    Runs the same `Nos -> build_resolved_platform` path a connection takes, but
    over the packaged registry entry (`nos_plugins[...]`) and without a server,
    so a data-level merge assertion stays fast. No overlay / inventory layer.
    """
    return build_resolved_platform(Nos(filename=nos_plugins[platform]), {})


@pytest.mark.parametrize(
    ("platform", "command", "paging", "modes", "body_lines"),
    [
        # huawei `scroll` / arista `terminal length 0` carry `disables_paging:
        # true` only in their A3 command; the empty legacy py stubs used to
        # shadow them (py wins the merge and cannot carry the flag), so the P3-4
        # pager never disabled at runtime. #320 dropped the stubs so A3 wins.
        ("huawei_smartax", "scroll", True, {"user", "enable"}, None),
        ("arista_eos", "terminal length 0", True, {"user", "enable"}, ["Pagination disabled."]),
        # The `term …` alias inherits the target's flag + modes + body via the loader.
        ("arista_eos", "term length 0", True, {"user", "enable"}, ["Pagination disabled."]),
        # `terminal width 511` moved to A3 in the same sweep (its alias `term
        # width 0` would otherwise dangle); it carries no flag, so pin False to
        # guard against an over-broad disable.
        ("arista_eos", "terminal width 511", False, {"user", "enable"}, ["Width set to 511 columns."]),
        ("arista_eos", "term width 0", False, {"user", "enable"}, ["Width set to 511 columns."]),
    ],
)
def test_a3_paging_flag_and_output_reach_merged_runtime(platform, command, paging, modes, body_lines):
    """A3 `disables_paging` + modes + output reach the merged runtime (#320).

    Originally pinned against the py-inflow shadowing bug class; that inflow is
    gone (#317 P-3/P-4, a py `commands` dict is rejected at load), so these now
    pin the A3 data end to end against any future merge rework.
    `_render_response` joins body lines with the newline and absorbs trailing
    newlines (via `splitlines()`), so the projected `body_lines` are the wire
    lines a client sees — pinning the `.txt` bytes the py stubs used to serve.
    The `modes` assert pins the mode constraint the py `prompt: [...]` used to
    carry, so an A3 `mode:` narrowing (e.g. dropping `user`) fails here.
    """
    rc = _merged_platform(platform).commands[command]
    assert rc.disables_paging is paging
    assert rc.modes == modes
    rendered = rc.output.render("x")
    assert (rendered.splitlines() if rendered is not None else None) == body_lines


# --- #317 P-3: native BASIC_COMMANDS (案F) ---


def test_basic_commands_are_native_resolved_commands():
    """BASIC_COMMANDS are frozen `ResolvedCommand` constants, valid in every mode (#317 P-3).

    Being born resolved (no legacy-adapter round trip) they can be shared into
    every merge without copying; empty `modes` keeps them reachable everywhere,
    and platform data / overlay / inventory still override them by key.
    """
    basic = cmd_shell_module.BASIC_COMMANDS
    assert set(basic) == {"exit", "_default_", "_ambiguous_", "_incomplete_"}
    for name, rc in basic.items():
        assert rc.name == name
        assert rc.modes == frozenset()  # valid in every mode
        assert rc.new_mode is None and rc.transitions is None
    assert basic["exit"].exit is True
    assert basic["_default_"].output.render("R1") == "Unknown command"


def test_basic_ambiguous_placeholder_is_plain_literal():
    """The `_ambiguous_` placeholder is a plain single-brace `{input}` literal (#317 P-3).

    The `{{input}}` escape existed only for the legacy adapter's
    `str.format`-field detection; native literal text carries the placeholder
    dispatch actually substitutes (`str.replace`), so a reintroduced escape
    would reach the wire as `{{input}}` garbage — pinned here.
    """
    out = cmd_shell_module.BASIC_COMMANDS["_ambiguous_"].output
    assert out.kind == "literal"
    assert out.text == '% Ambiguous command:  "{input}"'


# --- #317 P-1: A3 handler channel + transitions (synthetic asset e2e) ---


def _synthetic_a3_handler_platform(tmp_path, *, handler_ref="make_greeting"):
    """Build a synthetic A3 dir + handler py exercising the P-1 channels (#317).

    The A3 platform authors a `handler:` command (dynamic output), a `transitions:`
    command (mode-conditional exit / new_mode), and an alias with a `mode:`
    override; the py module ships the device class + the referenced handler. Returns
    ``(a3_dir, py_file)`` for ``Nos(filename=[...])``.
    """
    root = tmp_path / "synplat"
    (root / "commands").mkdir(parents=True)
    (root / "platform.yaml").write_text(
        "modes:\n"
        '  user: {prompt: "{{ base_prompt }}>"}\n'
        '  enable: {prompt: "{{ base_prompt }}#"}\n'
        '  config: {prompt: "{{ base_prompt }}(config)#"}\n'
        "initial_mode: user\n",
        encoding="utf-8",
    )
    cmds = root / "commands"
    cmds.joinpath("greet.yaml").write_text(
        f"command: greet\ntype: simnos\nmode: [user, enable]\nhandler: {handler_ref}\n", encoding="utf-8"
    )
    cmds.joinpath("leave.yaml").write_text(
        "command: leave\ntype: simnos\nmode: [user, enable, config]\ntransitions:\n"
        "  user: {exit: true}\n  enable: {exit: true}\n  config: {new_mode: enable}\n",
        encoding="utf-8",
    )
    cmds.joinpath("goto.yaml").write_text(
        "command: goto enable\ntype: simnos\nmode: [user]\nnew_mode: enable\n", encoding="utf-8"
    )
    # A partial `transitions` map: valid in user+enable but keyed on enable only,
    # so in user mode `eff` is None and the command stays put (#317 P-1, claude#3).
    cmds.joinpath("partial.yaml").write_text(
        "command: partial\ntype: simnos\nmode: [user, enable]\ntransitions:\n  enable: {new_mode: user}\n",
        encoding="utf-8",
    )
    # A command carrying BOTH a dynamic `handler:` output and a `transitions:`
    # transition — the two channels are orthogonal (#317 P-1, claude#2).
    cmds.joinpath("dyn.yaml").write_text(
        f"command: dyn\ntype: simnos\nmode: [enable]\nhandler: {handler_ref}\n"
        "transitions:\n  enable: {new_mode: user}\n",
        encoding="utf-8",
    )
    py = tmp_path / "synplat_handlers.py"
    py.write_text(
        "from simnos.plugins.nos.platforms_py._templates.base_template import BaseDevice\n"
        "class SynDev(BaseDevice):\n"
        "    def make_greeting(self, device=None, *, base_prompt, current_mode, current_prompt, command):\n"
        '        return f"hello from {current_mode}"\n'
        # A vestigial *empty* dict must not trip the "py dict authoring was
        # removed" load guard (only a non-empty one is an authoring attempt;
        # merge-time in P-3, moved to `_from_module` in P-4).
        "commands = {}\n",
        encoding="utf-8",
    )
    return str(root), str(py)


def test_p1_handler_ref_binds_at_merge(tmp_path):
    """An A3 `handler:` ref is bound to the py callable at `build_resolved_platform` (#317 P-1)."""
    a3_dir, py = _synthetic_a3_handler_platform(tmp_path)
    nos = Nos(filename=[a3_dir, py])
    platform = build_resolved_platform(nos, {})
    greet = platform.commands["greet"]
    assert greet.output.kind == "handler"
    assert greet.output.handler is not None  # bound
    assert greet.output.handler_ref == "make_greeting"


def test_p1_unresolved_handler_ref_is_loud(tmp_path):
    """A `handler:` ref with no matching py callable fails loudly at merge (#317 P-1)."""
    a3_dir, py = _synthetic_a3_handler_platform(tmp_path, handler_ref="does_not_exist")
    nos = Nos(filename=[a3_dir, py])
    with pytest.raises(ValueError, match="not defined in the platform's py handler namespace"):
        build_resolved_platform(nos, {})


def _synthetic_shell(tmp_path):
    a3_dir, py = _synthetic_a3_handler_platform(tmp_path)
    nos = Nos(filename=[a3_dir, py])
    running = threading.Event()
    running.set()  # unset would make `_dispatch_general` treat every line as a shutdown close
    return CMDShell(nos=nos, nos_inventory_config={}, base_prompt="R1", is_running=running)


def test_p1_bound_handler_dispatches(tmp_path):
    """The merge-bound handler produces dynamic output through `_dispatch_general` (#317 P-1)."""
    shell = _synthetic_shell(tmp_path)  # starts in `user`
    body, close, _challenge = shell._dispatch_general("greet")
    assert body == "hello from user"
    assert close is False


def test_p1_transitions_exit_and_new_mode(tmp_path):
    """A `transitions` map drives a per-mode exit / new_mode in dispatch (#317 P-1)."""
    shell = _synthetic_shell(tmp_path)
    # user mode: transitions[user] = exit -> session closes, no body.
    body, close, _challenge = shell._dispatch_general("leave")
    assert close is True
    assert body is None
    # config mode: transitions[config] = new_mode enable (no exit).
    shell.current_mode = "config"
    body, close, _challenge = shell._dispatch_general("leave")
    assert close is False
    assert shell.current_mode == "enable"


def test_p1_static_new_mode_dispatch(tmp_path):
    """A plain static `new_mode` still transitions unchanged (baseline byte-parity, #317 P-1)."""
    shell = _synthetic_shell(tmp_path)
    _body, close, _challenge = shell._dispatch_general("goto enable")
    assert close is False
    assert shell.current_mode == "enable"


def test_p1_partial_transitions_map_stays_when_mode_absent(tmp_path):
    """A `transitions` map missing the current mode = no transition (#317 P-1, claude#3)."""
    shell = _synthetic_shell(tmp_path)  # user mode; `partial` keys enable only
    _body, close, _challenge = shell._dispatch_general("partial")
    assert close is False
    assert shell.current_mode == "user"  # stayed — no entry for user
    # And in enable mode its one entry fires.
    shell.current_mode = "enable"
    shell.prompt = "R1#"
    shell._dispatch_general("partial")
    assert shell.current_mode == "user"


def test_p1_handler_and_transitions_are_orthogonal(tmp_path):
    """A command with both `handler:` and `transitions:` renders handler output AND transitions (#317 P-1, claude#2)."""
    shell = _synthetic_shell(tmp_path)
    shell.current_mode = "enable"  # `dyn` is enable-only
    shell.prompt = "R1#"
    body, close, _challenge = shell._dispatch_general("dyn")
    assert body == "hello from enable"  # handler output rendered
    assert close is False
    assert shell.current_mode == "user"  # transitions[enable] = new_mode user applied


# --- #317 P-4: py module `commands` dict rejected at load ---


def test_py_module_commands_dict_is_loud_at_load(tmp_path):
    """A py module defining a non-empty `commands` dict fails `from_file` (#317 P-4).

    P-3 rejected the dict at the merge (`nos.commands` was still an attribute);
    P-4 removed the attribute, so the guard moved to the load boundary — the
    "loads but never merges" silent-ignore window stays closed either way.
    """
    py = tmp_path / "dict_author.py"
    py.write_text('commands = {"show x": {"output": "x"}}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="py dict authoring was removed"):
        Nos(filename=str(py))


@contextlib.contextmanager
def tempfile_dir():
    """A `tmp_path`-like context manager for the unittest-style classes.

    The `TestCase` classes cannot take pytest fixtures; this provides the same
    auto-cleaned temp dir for the helpers that build tmp A3 platforms.
    """
    with tempfile.TemporaryDirectory() as tmp:
        yield pathlib.Path(tmp)


def _handler_dispatch_platform(tmp_path):
    """A tmp A3 dir + handler py covering the handler dispatch contract cases.

    Successor of the legacy dict-built `_make_callable_shell` platforms: each
    command routes to a named handler function exercising one branch of the
    `str | None` contract (#317 P-2) or the crash boundary (#241 / D4). The
    `known` command is enable-only static output for the mode-mismatch case,
    and `_default_` itself is a `handler:` command (dynamic fallback).
    """
    root = tmp_path / "handlerplat"
    cmds = root / "commands"
    cmds.mkdir(parents=True)
    (root / "platform.yaml").write_text(
        "modes:\n"
        '  user: {prompt: "{{ base_prompt }}>"}\n'
        '  enable: {prompt: "{{ base_prompt }}#"}\n'
        "initial_mode: user\n",
        encoding="utf-8",
    )
    table = {
        "cmd str": ("ret_str", None),
        "cmd brace": ("ret_brace", None),
        "cmd dict": ("ret_dict", None),
        "cmd crash": ("crash", None),
        "cmd transition": ("ret_empty", "enable"),
    }
    for name, (handler, new_mode) in table.items():
        body = f"command: {name}\ntype: simnos\nmode: [user]\nhandler: {handler}\n"
        if new_mode:
            body += f"new_mode: {new_mode}\n"
        cmds.joinpath(name.replace(" ", "_") + ".yaml").write_text(body, encoding="utf-8")
    cmds.joinpath("known.yaml").write_text(
        "command: known\ntype: simnos\nmode: [enable]\noutput: known.txt\n", encoding="utf-8"
    )
    cmds.joinpath("known.txt").write_text("static\n", encoding="utf-8")
    cmds.joinpath("default.yaml").write_text(
        "command: _default_\ntype: simnos\nhandler: dyn_default\n", encoding="utf-8"
    )
    py = tmp_path / "handlerplat_handlers.py"
    py.write_text(
        "def ret_str(device, **kwargs):\n"
        '    return "dynamic body"\n'
        "def ret_brace(device, **kwargs):\n"
        '    return "literal {brace} stays"\n'
        "def ret_dict(device, **kwargs):\n"
        '    return {"output": "", "new_mode": "enable"}\n'
        "def ret_empty(device, **kwargs):\n"
        '    return ""\n'
        "def crash(device, **kwargs):\n"
        '    raise RuntimeError("boom-for-log")\n'
        "def dyn_default(device, **kwargs):\n"
        "    return f\"dynamic unknown: {kwargs['command']}\"\n",
        encoding="utf-8",
    )
    return str(root), str(py)


# pylint: disable=too-many-public-methods
class TestCmdShell(TestCase):
    """Test the CmdShell class."""

    def setUp(self):
        """Setup the test."""
        self.arguments = make_cmd_shell_args()

    def test_init_error_if_nos_not_provided(self):
        """Test the init method raises an error if nos is not provided."""
        with self.assertRaises(TypeError):
            # pylint: disable=no-value-for-parameter
            CMDShell()  # ty: ignore[missing-argument]  # intentional: missing required kwargs

    def test_init_error_if_nos_inventory_config_not_provided(self):
        """Test the init method raises an error if nos_inventory_config is not provided."""
        with self.assertRaises(TypeError):
            # pylint: disable=no-value-for-parameter
            CMDShell(nos=_nos_from_synthetic_asset())  # ty: ignore[missing-argument]

    def test_init_error_if_base_prompt_not_provided(self):
        """Test the init method raises an error if base_prompt is not provided."""
        with self.assertRaises(TypeError):
            # pylint: disable=no-value-for-parameter
            CMDShell(nos=_nos_from_synthetic_asset(), nos_inventory_config={})  # ty: ignore[missing-argument]

    def test_init_error_if_is_running_not_provided(self):
        """Test the init method raises an error if is_running is not provided."""
        with self.assertRaises(TypeError):
            # pylint: disable=no-value-for-parameter
            CMDShell(  # ty: ignore[missing-argument]
                nos=_nos_from_synthetic_asset(),
                nos_inventory_config={},
                base_prompt="test",
            )

    def test_dispatch_blank_line_no_output(self):
        """A blank line dispatches to no output and does not close (was test_emptyline).

        The cmd.Cmd `emptyline` hook was removed in #303 P3-3; `dispatch` now
        handles the empty case via `_parseline` returning a falsy parsed line.
        """
        shell = CMDShell(**self.arguments)
        shell.is_running.set()
        result = shell.dispatch("")
        self.assertIsNone(result.body)
        self.assertFalse(result.close)

    def test_precmd(self):
        """Test that the precmd method returns the line."""
        shell = CMDShell(**self.arguments)
        self.assertEqual(shell.precmd("test"), "test")

    def test_postcmd(self):
        """Test that the postcmd method returns the stop and line."""
        shell = CMDShell(**self.arguments)
        self.assertEqual(shell.postcmd(False, "test"), False)

    def test_postcmd_with_stop(self):
        """Test that the postcmd method returns the stop and line."""
        shell = CMDShell(**self.arguments)
        self.assertEqual(shell.postcmd(True, "test"), True)

    def test_postcmd_with_stop_and_line(self):
        """Test that the postcmd method returns the stop and line."""
        shell = CMDShell(**self.arguments)
        self.assertEqual(shell.postcmd(True, "exit"), True)

    def test_postcmd_with_line(self):
        """Test that the postcmd method returns the stop and line."""
        shell = CMDShell(**self.arguments)
        self.assertEqual(shell.postcmd(False, "exit"), False)

    def test_postcmd_with_no_line(self):
        """Test that the postcmd method returns the stop and line."""
        shell = CMDShell(**self.arguments)
        self.assertEqual(shell.postcmd(False, ""), False)

    def test_help_body(self):
        """`_help_body` builds the current-mode help listing (was do_help).

        `do_help` was removed in #303 P3-3; `dispatch` calls `_help_body`
        directly when the parsed command is `help` (a leading `?` or `help`).
        Listing order is the merged-dict insertion order: the BASIC `exit`
        first, then the A3 commands (loader order: real commands by file stem,
        aliases resolved last).
        """
        shell = CMDShell(**self.arguments)
        expected_output: list[str] = [
            "exit                Exit commands shell",
            "enable              enter exec prompt",
            "show clock          Display the system clock",
            "show marker         dynamic handler marker command",
            "terminal length 0   Set terminal length to 0",
            "terminal width 511  Set terminal width to 511",
            "sh clock            ",
        ]
        self.assertEqual(shell._help_body(), "\r\n".join(expected_output))

    def test_help_body_alias_hidden_outside_target_modes(self):
        """`_help_body` lists an alias only in its target modes (#264 / claude #2).

        Intentional refinement over v2 (which listed prompt-less aliases in
        every mode via the raw unmerged entry): `sh clock` aliases `show clock`
        (modes user/enable), so it is listed in user mode but hidden in config.
        Dispatch was already mode-scoped in v2; only the help listing changes.
        """
        shell = CMDShell(**self.arguments)  # current_mode == "user"
        self.assertIn("sh clock", shell._help_body())
        shell.current_mode = "config"
        self.assertNotIn("sh clock", shell._help_body())

    def test__in_current_mode_empty_modes_always_visible(self):
        """A command with no declared modes is valid in every mode (#264 / D5).

        A command whose authoring omitted `mode` resolves to an empty mode set,
        which the engine treats as "valid everywhere" (BASIC `exit` is such a
        command).
        """
        shell = CMDShell(**self.arguments)
        self.assertEqual(shell.commands["exit"].modes, frozenset())
        self.assertTrue(shell._in_current_mode(shell.commands["exit"]))
        shell.current_mode = "config"
        self.assertTrue(shell._in_current_mode(shell.commands["exit"]))

    def test__in_current_mode_membership(self):
        """A command is visible only in the modes it declares (#264 / D5).

        `show clock` (authored for user/enable) is visible in those modes and
        hidden in config.
        """
        shell = CMDShell(**self.arguments)  # current_mode == "user"
        clock = shell.commands["show clock"]
        self.assertEqual(clock.modes, frozenset({"user", "enable"}))
        self.assertTrue(shell._in_current_mode(clock))
        shell.current_mode = "config"
        self.assertFalse(shell._in_current_mode(clock))

    def test_dispatch_general_command_correct(self):
        """A known command returns its rendered body and does not close (was default)."""
        self.arguments["is_running"].set()
        shell = CMDShell(**self.arguments)
        body, close, _challenge = shell._dispatch_general("show clock")
        self.assertEqual(body, "*21:01:33.000 AET 01 01 01 2022\n")
        self.assertFalse(close)

    def test_dispatch_general_command_with_alias(self):
        """An alias resolves to the same body as its target (was default)."""
        self.arguments["is_running"].set()
        shell = CMDShell(**self.arguments)
        body, close, _challenge = shell._dispatch_general("sh clock")
        self.assertEqual(body, "*21:01:33.000 AET 01 01 01 2022\n")
        self.assertFalse(close)

    def test_dispatch_general_command_is_handler(self):
        """A bound-handler command returns its computed body (was default)."""
        self.arguments["is_running"].set()
        shell = CMDShell(**self.arguments)
        body, close, _challenge = shell._dispatch_general("show marker")
        self.assertEqual(body, "SYNTHETIC-CUSTOM-MARKER")
        self.assertFalse(close)

    def _make_handler_shell(self, tmp_path):
        """Build a shell over the handler-dispatch tmp platform.

        Consumer-side pins for the handler dispatch branch of
        `_dispatch_general`: the str / None returns, the crash boundary (D4)
        and the str|None contract violation (#317 P-2 — the dict-return
        `CommandResult` form is gone; a transition rides the command's own
        static `new_mode`).
        """
        a3_dir, py = _handler_dispatch_platform(tmp_path)
        self.arguments["is_running"].set()
        self.arguments["nos"] = Nos(filename=[a3_dir, py])
        return CMDShell(**self.arguments)

    def test_dispatch_handler_with_static_new_mode_transitions(self):
        """A handler command's static new_mode transitions the shell (#317 P-2).

        The former dict-return `new_mode` is gone; the transition is the
        command's own static data and applies alongside the handler body.
        """
        with tempfile_dir() as tmp_path:
            shell = self._make_handler_shell(tmp_path)
            body, close, _challenge = shell._dispatch_general("cmd transition")
            self.assertFalse(close)
            self.assertEqual(shell.current_mode, "enable")
            self.assertEqual(shell.prompt, "test#")
            self.assertEqual(body, "")

    def test_dispatch_handler_str_output(self):
        """A str-returning handler's body is served, prompt unchanged."""
        with tempfile_dir() as tmp_path:
            shell = self._make_handler_shell(tmp_path)
            body, close, _challenge = shell._dispatch_general("cmd str")
            self.assertFalse(close)
            self.assertEqual(shell.prompt, "test>")
            self.assertEqual(body, "dynamic body")

    def test_dispatch_handler_dict_return_is_contract_violation(self):
        """A dict-returning handler answers HANDLER_ERROR_OUTPUT (#317 P-2).

        The `CommandResult` dict form was removed with the legacy py-dict
        authoring; a plugin still returning one must fail loud in the log and
        real-NOS-style on the wire — with no transition side effect.
        """
        with tempfile_dir() as tmp_path:
            shell = self._make_handler_shell(tmp_path)
            with self.assertLogs("simnos.plugins.shell.cmd_shell", level="ERROR") as captured:
                body, close, _challenge = shell._dispatch_general("cmd dict")
            self.assertFalse(close)
            self.assertEqual(body, HANDLER_ERROR_OUTPUT)
            self.assertEqual(shell.current_mode, "user")  # the dict's new_mode is dead
            self.assertTrue(any("contract is str | None" in msg for msg in captured.output))

    def test_dispatch_command_not_matching_mode(self):
        """A command not valid in the current mode answers with `_default_`."""
        self.arguments["is_running"].set()
        shell = CMDShell(**self.arguments)
        body, _close, _challenge = shell._dispatch_general("show version")
        self.assertEqual(body, "% Invalid input detected at '^' marker.\n")

    def test_dispatch_command_incorrect(self):
        """An unknown command answers with the `_default_` output."""
        self.arguments["is_running"].set()
        shell = CMDShell(**self.arguments)
        body, _close, _challenge = shell._dispatch_general("test")
        self.assertEqual(body, "% Invalid input detected at '^' marker.\n")

    def test_invoke_handler_str_return_passthrough(self):
        """`_invoke_handler` returns a str body verbatim (#317 P-2 output-only contract)."""
        shell = CMDShell(**self.arguments)
        self.assertEqual(shell._invoke_handler(lambda device, **kwargs: "body", "cmd"), "body")

    def test_invoke_handler_none_return_passthrough(self):
        """`_invoke_handler` returns None (= write nothing) verbatim."""
        shell = CMDShell(**self.arguments)
        self.assertIsNone(shell._invoke_handler(lambda device, **kwargs: None, "cmd"))

    def test_invoke_handler_non_str_return_is_loud(self):
        """A non-str|None return answers HANDLER_ERROR_OUTPUT with an ERROR log (#317 P-2).

        Same shape as the crash boundary: broken plugin code never puts
        garbage (or a stringified dict/list) on the wire.
        """
        shell = CMDShell(**self.arguments)
        with self.assertLogs("simnos.plugins.shell.cmd_shell", level="ERROR") as captured:
            # ty flags the deliberate contract break (list is not str | None) — that
            # break is exactly what this test pins.
            result = shell._invoke_handler(lambda device, **kwargs: ["not", "a", "str"], "cmd")  # ty: ignore[invalid-argument-type]
        self.assertEqual(result, HANDLER_ERROR_OUTPUT)
        self.assertTrue(any("contract is str | None" in msg for msg in captured.output))

    def test_invoke_handler_receives_current_mode(self):
        """`_invoke_handler` passes the current mode name to the handler (#264)."""
        shell = CMDShell(**self.arguments)
        seen = {}

        def handler(device, **kwargs):
            seen.update(kwargs)
            return "ok"

        shell._invoke_handler(handler, "cmd")
        self.assertEqual(seen["current_mode"], shell.current_mode)

    def test_dispatch_handler_default_invoked_on_unknown_command(self):
        """An unknown command invokes a `handler:` `_default_` (#241).

        No shipped platform has a dynamic `_default_`, but the A3 `handler:`
        channel can author one — these pins fix the #241 unification: both the
        unknown-command and the mode-mismatch fallback invoke it through
        `_invoke_handler`.
        """
        with tempfile_dir() as tmp_path:
            shell = self._make_handler_shell(tmp_path)
            body, close, _challenge = shell._dispatch_general("nope")
            self.assertFalse(close)
            self.assertEqual(body, "dynamic unknown: nope")

    def test_dispatch_handler_default_invoked_on_mode_mismatch(self):
        """A mode mismatch invokes a `handler:` `_default_` (#241 / #264).

        `known` is enable-only; typed in user mode it misses, and the fallback
        invokes the dynamic `_default_` through `_invoke_handler`.
        """
        with tempfile_dir() as tmp_path:
            shell = self._make_handler_shell(tmp_path)
            body, close, _challenge = shell._dispatch_general("known")  # valid only in enable, current mode is user
            self.assertFalse(close)
            self.assertEqual(body, "dynamic unknown: known")

    def test_dispatch_handler_crash_writes_fixed_error_line(self):
        """A crashing handler answers with HANDLER_ERROR_OUTPUT only.

        Pins #241/D4: real NOSes never print Python tracebacks, and the
        old behavior (traceback.format_exc() sent to the SSH client) made
        Netmiko-side parsers chew on stack frames and leaked internal
        paths. The wire now gets the fixed one-liner; the session stays up.
        """
        with tempfile_dir() as tmp_path:
            shell = self._make_handler_shell(tmp_path)
            with self.assertLogs("simnos.plugins.shell.cmd_shell", level="ERROR"):
                body, close, _challenge = shell._dispatch_general("cmd crash")
            self.assertFalse(close)
            self.assertEqual(body, HANDLER_ERROR_OUTPUT)

    def test_dispatch_handler_crash_logs_full_traceback(self):
        """A crashing handler's traceback goes to the server log.

        Pins #241/D4 (the diagnosability half): dropping the wire
        traceback must not lose the information — the log carries the
        full `traceback.format_exc()` including the original exception,
        same shape as the hot-reload guard (#232).
        """
        with tempfile_dir() as tmp_path:
            shell = self._make_handler_shell(tmp_path)
            with self.assertLogs("simnos.plugins.shell.cmd_shell", level="ERROR") as captured:
                shell._dispatch_general("cmd crash")
            self.assertEqual(len(captured.output), 1)
            self.assertIn("handler crashed", captured.output[0])
            self.assertIn("RuntimeError: boom-for-log", captured.output[0])
            self.assertIn("Traceback", captured.output[0])

    def test_dispatch_handler_str_output_passed_through_unformatted(self):
        """Handler str output is written verbatim (#241 / D-b).

        Handlers render themselves, so literal braces in a handler's output
        (e.g. JSON-ish device output) reach the wire untouched, with no
        render step and no error log.
        """
        with tempfile_dir() as tmp_path:
            shell = self._make_handler_shell(tmp_path)
            with self.assertNoLogs("simnos.plugins.shell.cmd_shell", level="ERROR"):
                body, close, _challenge = shell._dispatch_general("cmd brace")
            self.assertFalse(close)
            self.assertEqual(body, "literal {brace} stays")

    def test_dispatch_command_transitions_mode(self):
        """A command with a new_mode transitions the shell and re-renders the prompt.

        `enable` (synthetic_custom) declares new_mode=enable; dispatching it
        from the initial user mode moves current_mode to enable and the prompt
        to "test#" (the enable prompt rendered at base_prompt "test").
        """
        self.arguments["is_running"].set()
        shell = CMDShell(**self.arguments)
        shell._dispatch_general("enable")
        self.assertEqual(shell.current_mode, "enable")
        self.assertEqual(shell.prompt, "test#")

    def test_dispatch_command_exit(self):
        """An exit command closes the session (was default returning True)."""
        self.arguments["is_running"].set()
        shell = CMDShell(**self.arguments)
        _body, close, _challenge = shell._dispatch_general("exit")
        self.assertTrue(close)

    def test_dispatch_eof_closes_session(self):
        """`dispatch("EOF")` closes the session (was do_EOF returning True)."""
        self.arguments["is_running"].set()
        shell = CMDShell(**self.arguments)
        self.assertTrue(shell.dispatch("EOF").close)


class HotReloadTest(TestCase):
    """
    Test class for the hot reload feature
    """

    def setUp(self):
        self.arguments = make_cmd_shell_args()
        os.environ["SIMNOS_RELOAD_COMMANDS"] = "ON"

    def tearDown(self):
        if "SIMNOS_RELOAD_COMMANDS" in os.environ:
            os.environ.pop("SIMNOS_RELOAD_COMMANDS")

    def test_hot_reload_not_activated_doesnt_enter(self):
        """Test that precmd's hot-reload branch is skipped when SIMNOS_RELOAD_COMMANDS is unset."""
        os.environ.pop("SIMNOS_RELOAD_COMMANDS")
        shell = CMDShell(**self.arguments)
        mock_get_files_changed = set_attr(shell, "get_files_changed", Mock())
        shell.precmd("show clock")
        mock_get_files_changed.assert_not_called()

    @patch("simnos.plugins.shell.cmd_shell.get_files_changed")
    def test_hot_reload_activated_does_enter(self, mock_get_files_changed):
        """Test that if there are no changed files, nothing happens."""
        # #281: get_files_changed is now pure, returning (targets, new_snapshot).
        mock_get_files_changed.return_value = ([], {})
        shell = CMDShell(**self.arguments)
        shell.precmd("show clock")
        mock_get_files_changed.assert_called_once()

    @patch("simnos.core.nos.Nos.from_file")
    @patch("simnos.plugins.shell.cmd_shell.get_files_changed")
    def test_hot_reload_activated_update_commands(self, mock_get_files_changed, mock_from_file):
        """
        Test that if there are change files,
        the nos_from_file is called
        and the commands are updated correctly.
        """
        changed_module = "simnos.plugins.nos.platforms_py.cisco_ios"
        # #281: get_files_changed is now pure, returning (targets, new_snapshot).
        mock_get_files_changed.return_value = ([changed_module.replace(".", "/") + ".py"], {})
        shell = CMDShell(**self.arguments)
        shell.precmd("show clock")
        module = importlib.import_module(changed_module)
        mock_from_file.assert_called_once()
        mock_from_file.assert_called_once_with(module.__name__.replace(".", "/") + ".py")
        # The rebuild kept serving the shell's own (synthetic-asset) commands —
        # a handler module carries no command data to cross-check (#317 P-2/P-4).
        assert "show clock" in shell.commands
        assert "show version" in shell.commands

    def _tmp_healthy_platform(self, tmp_path) -> str:
        """A loadable tmp A3 dir whose reload proves 'the healthy file applied'."""
        root = tmp_path / "healthy_platform"
        cmds = root / "commands"
        cmds.mkdir(parents=True)
        (root / "platform.yaml").write_text(
            'modes:\n  user:\n    prompt: "{{ base_prompt }}>"\ninitial_mode: user\n', encoding="utf-8"
        )
        cmds.joinpath("healthy.yaml").write_text(
            "command: healthy\ntype: simnos\nmode: [user]\noutput: healthy.txt\n", encoding="utf-8"
        )
        cmds.joinpath("healthy.txt").write_text("ok\n", encoding="utf-8")
        return str(root)

    def test_reload_commands_broken_file_logs_and_continues(self):
        """One broken file does not kill the session nor block the rest.

        Pins the per-file lenient guard in `reload_commands` (#232): a
        half-written or malformed plugin file observed by hot reload used
        to raise out of `precmd` and crash the whole shell thread. Now the
        broken file is logged and skipped while remaining files reload —
        proven by the healthy tmp platform's command landing in the shell.
        """
        with tempfile_dir() as tmp_path:
            shell = CMDShell(**self.arguments)
            healthy = self._tmp_healthy_platform(tmp_path)
            with self.assertLogs("simnos.plugins.shell.cmd_shell", level="ERROR") as captured:
                # A `.yaml` file is not a loadable reload unit (`from_file` rejects
                # the extension) — a stand-in for any per-file load failure.
                shell.reload_commands(["broken.yaml", healthy])
            self.assertEqual(len(captured.output), 1)
            self.assertIn("broken.yaml", captured.output[0])
            self.assertIn("healthy", shell.commands)

    def test_reload_commands_broken_file_last_still_applies_rest(self):
        """The per-file guard is order-independent: broken file last.

        Complements `test_reload_commands_broken_file_logs_and_continues`
        (broken first): the healthy file's commands are applied before the
        broken file raises, and the error is still logged.
        """
        with tempfile_dir() as tmp_path:
            shell = CMDShell(**self.arguments)
            healthy = self._tmp_healthy_platform(tmp_path)
            with self.assertLogs("simnos.plugins.shell.cmd_shell", level="ERROR") as captured:
                shell.reload_commands([healthy, "broken.yaml"])
            self.assertEqual(len(captured.output), 1)
            self.assertIn("broken.yaml", captured.output[0])
            self.assertIn("healthy", shell.commands)

    def test_reload_commands_broken_py_plugin_is_contained(self):
        """A broken py module skipped by the guard never corrupts the shell.

        Pins the #232 cross-review hole shape on the P-4 surface: the broken
        asset raises the #241/D5 multiple-subclass ValueError in
        `_from_module`'s build phase, before any commit, so the running
        shell keeps its platform and a following healthy reload still applies.
        """
        with tempfile_dir() as tmp_path:
            shell = CMDShell(**self.arguments)
            healthy = self._tmp_healthy_platform(tmp_path)
            with self.assertLogs("simnos.plugins.shell.cmd_shell", level="ERROR") as captured:
                shell.reload_commands(["tests/assets/broken_multi_device_module.py", healthy])
            self.assertEqual(len(captured.output), 1)
            self.assertIn("broken_multi_device_module.py", captured.output[0])
            self.assertIn("healthy", shell.commands)  # healthy reload still applied


def _synthetic_reload_platform(watch_root) -> str:
    """Build `<watch_root>/platforms/synth_reload/` (a minimal A3 dir) and return it.

    Laid out under a `platforms/` segment so the changed-file rollup
    (`resolve_reload_targets` against the patched package root) folds an edited
    `commands/*.j2` to this platform dir. The `_default_` answers netmiko's
    session-preparation commands (`terminal length 0` etc.), same as the
    custom-platform e2e.
    """
    platform_dir = watch_root / "platforms" / "synth_reload"
    cmds = platform_dir / "commands"
    cmds.mkdir(parents=True)
    platform_dir.joinpath("platform.yaml").write_text(
        'modes:\n  user:\n    prompt: "{{ base_prompt }}>"\ninitial_mode: user\n', encoding="utf-8"
    )
    cmds.joinpath("show_version.yaml").write_text(
        "command: show version\ntype: simnos\nmode: [user]\noutput_template: show_version.j2\n", encoding="utf-8"
    )
    cmds.joinpath("show_version.j2").write_text("SYNTH-BEFORE\n", encoding="utf-8")
    cmds.joinpath("default.yaml").write_text(
        "command: _default_\ntype: simnos\noutput: default.txt\n", encoding="utf-8"
    )
    cmds.joinpath("default.txt").write_text("% synth unknown\n", encoding="utf-8")
    return str(platform_dir)


@pytest.mark.timeout(60)
def test_hot_reload_integration_a3_edit(tmp_path, monkeypatch):
    """An A3 `.j2` edit reaches a live SSH session through the hot-reload watcher.

    Runs on a tmp synthetic platform registered for this test only. Until #317
    P-2 this e2e edited the real cisco_ios py template (serialized via
    `xdist_group`); its successor is the A3 `commands/show_version.j2`, which is
    global state — editing the packaged copy would race sibling xdist workers
    whose `load_platform_dir` cache first loads cisco_ios inside the edit
    window. The tmp platform keeps the end-to-end chain (watcher poll -> rollup
    -> `from_file(dir)` -> rebuild -> wire) with zero shared-tree mutation.
    """
    watch_root = tmp_path / "nos"
    platform_dir = _synthetic_reload_platform(watch_root)
    # Register like the custom-platform e2e (global registry via setitem, restored
    # on teardown) + point the watcher's rollup root at the tmp tree.
    monkeypatch.setitem(nos_plugins, "synth_reload", [platform_dir])
    monkeypatch.setattr(
        nos_registry, "available_platforms", tuple(sorted((*nos_registry.available_platforms, "synth_reload")))
    )
    monkeypatch.setattr(cmd_shell_module.nos_pkg, "__path__", [str(watch_root)])
    monkeypatch.setenv("SIMNOS_RELOAD_COMMANDS", "1")

    inventory = {
        "hosts": {
            "device": {
                "username": "test",
                "password": "test",
                "port": EPHEMERAL_PORT,
                "device_type": "synth_reload",
            }
        }
    }
    with SimNOS(inventory=inventory) as net:
        host = net.hosts["device"]
        credentials = {
            "host": "localhost",
            "username": host.username,
            "password": host.password,
            "port": host.port,
            "device_type": "cisco_ios",  # netmiko driver; the synthetic prompt mirrors cisco_ios
        }
        with ConnectHandler(**credentials) as conn:
            assert conn.send_command("show version") == "SYNTH-BEFORE"
            target = os.path.join(platform_dir, "commands", "show_version.j2")
            with open(target, "w", encoding="utf-8") as fh:
                fh.write("SYNTH-AFTER\n")
            # Nudge the mtime past the seeded baseline in case the edit lands
            # within the filesystem's mtime resolution of the connect-time walk.
            future = time.time() + 5
            os.utime(target, (future, future))
            assert conn.send_command("show version") == "SYNTH-AFTER"
