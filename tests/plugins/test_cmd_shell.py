"""
Module to test the cmd_shell plugin.
"""

import importlib
import os
import shutil
import sys
import tempfile
import threading
import time
from unittest import TestCase
from unittest.mock import Mock, patch

from netmiko import ConnectHandler
import pytest
import yaml

from simnos.core.nos import Nos
from simnos.core.simnos import SimNOS, simnos
from simnos.plugins.shell.cmd_shell import HANDLER_ERROR_OUTPUT, CMDShell
from tests.utils import set_attr


def _nos_from_yaml_asset(path: str = "tests/assets/yaml_nos.yaml") -> Nos:
    """Build a Nos from a yaml *asset* via the surviving ``from_dict`` path.

    The legacy ``from_file(.yaml)`` loader was removed in v3 (#264); this test
    vehicle keeps the shared fixture data but loads it through ``from_dict`` (the
    inventory/constructor inflow), which the legacy shell still consumes.
    """
    with open(path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    nos = Nos()
    nos.from_dict(data)
    return nos


def make_cmd_shell_args() -> dict:
    """Build the CMDShell constructor kwargs shared across cmd_shell tests (SSoT)."""
    return {
        "stdin": None,
        "stdout": None,
        "nos": _nos_from_yaml_asset(),
        "nos_inventory_config": {},
        "base_prompt": "test",
        "is_running": threading.Event(),
    }


@pytest.fixture
def cmd_shell_args():
    """CMDShell kwargs as a fixture (thin wrapper over make_cmd_shell_args)."""
    return make_cmd_shell_args()


def _expected_baseline(args: dict) -> dict:
    """Attribute values a CMDShell takes with no optional kwargs."""
    return {
        "intro": "Custom SSH Shell",
        "ruler": "",
        "completekey": "tab",
        "newline": "\r\n",
        "prompt": "test>",
        "base_prompt": args["base_prompt"],
    }


@pytest.mark.parametrize(
    "override_kwargs, expected_override",
    [
        ({}, {}),  # no optional kwargs (baseline)
        ({"intro": "Test Intro"}, {"intro": "Test Intro"}),
        ({"ruler": "Test Ruler"}, {"ruler": "Test Ruler"}),
        ({"completekey": "Test Completekey"}, {"completekey": "Test Completekey"}),
        ({"newline": "Test Newline"}, {"newline": "Test Newline"}),
        (
            {
                "intro": "Test Intro",
                "ruler": "Test Ruler",
                "completekey": "Test Completekey",
                "newline": "Test Newline",
            },
            {
                "intro": "Test Intro",
                "ruler": "Test Ruler",
                "completekey": "Test Completekey",
                "newline": "Test Newline",
            },
        ),
    ],
    ids=["baseline", "intro", "ruler", "completekey", "newline", "all"],
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
            CMDShell(nos=_nos_from_yaml_asset())  # ty: ignore[missing-argument]

    def test_init_error_if_base_prompt_not_provided(self):
        """Test the init method raises an error if base_prompt is not provided."""
        with self.assertRaises(TypeError):
            # pylint: disable=no-value-for-parameter
            CMDShell(nos=_nos_from_yaml_asset(), nos_inventory_config={})  # ty: ignore[missing-argument]

    def test_init_error_if_is_running_not_provided(self):
        """Test the init method raises an error if is_running is not provided."""
        with self.assertRaises(TypeError):
            # pylint: disable=no-value-for-parameter
            CMDShell(  # ty: ignore[missing-argument]
                nos=_nos_from_yaml_asset(),
                nos_inventory_config={},
                base_prompt="test",
            )

    def test_init_broken_initial_prompt_is_loud(self):
        """A malformed initial_prompt template now fails loudly at construction.

        Inverts the old #172 lenient fallback: prompt templates are load-time
        validated (#264 / D5), so a broken one (`{base_prompt.foo}>` — an
        unsupported attribute access) raises in the adapter via `_rebuild`
        instead of degrading to a raw-template prompt.
        """
        self.arguments["nos"] = Nos(
            dict_args={
                "name": "synth",
                "initial_prompt": "{base_prompt.foo}>",
                "commands": {"_default_": {"output": "% Unknown", "help": "default"}},
            }
        )
        with self.assertRaises(ValueError):
            CMDShell(**self.arguments)

    def test_start(self):
        """Test that the start method calls cmdloop."""
        shell = CMDShell(**self.arguments)
        mock_cmdloop = set_attr(shell, "cmdloop", Mock())
        shell.start()
        mock_cmdloop.assert_called_once()

    def test_stop(self):
        """Test that the stop method writes "exit" to stdin."""
        shell = CMDShell(**self.arguments)
        stdin = set_attr(shell, "stdin", Mock())
        shell.stop()
        stdin.write.assert_called_once_with("exit\r\n")

    def test_writeline(self):
        """Test that the writeline method writes a line to stdout with a newline at the end."""
        shell = CMDShell(**self.arguments)
        stdout = set_attr(shell, "stdout", Mock())
        shell.writeline("test")
        stdout.write.assert_called_once_with("test\r\n")

    def test_emptyline(self):
        """Test that the emptyline method does nothing."""
        shell = CMDShell(**self.arguments)
        result = shell.emptyline()
        self.assertIsNone(result)

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

    def test_do_help(self):
        """Test that the do_help method writes the help message to stdout."""
        shell = CMDShell(**self.arguments)
        writeline = set_attr(shell, "writeline", Mock())
        shell.do_help("")
        expected_output: list[str] = [
            "exit                Exit commands shell",
            "enable              enter exec prompt",
            "sh clock            ",
            "show clock          Display the system clock",
            "terminal width 511  Set terminal width to 511",
            "terminal length 0   Set terminal length to 0",
        ]
        writeline.assert_called_once_with("\r\n".join(expected_output))

    def test_do_help_alias_hidden_outside_target_modes(self):
        """do_help lists a prompt-less alias only in its target modes (#264 / claude #2).

        Intentional refinement over v2 (which listed prompt-less aliases in
        every mode via the raw unmerged entry): `sh clock` aliases `show clock`
        (modes user/enable), so it is listed in user mode but hidden in config.
        Dispatch was already mode-scoped in v2; only the help listing changes.
        """
        shell = CMDShell(**self.arguments)  # current_mode == "user"
        writeline = set_attr(shell, "writeline", Mock())
        shell.do_help("")
        self.assertIn("sh clock", writeline.call_args[0][0])
        shell.current_mode = "config"
        writeline.reset_mock()
        shell.do_help("")
        self.assertNotIn("sh clock", writeline.call_args[0][0])

    def test__in_current_mode_empty_modes_always_visible(self):
        """A command with no declared modes is valid in every mode (#264 / D5).

        Successor of the old `_check_prompt(None) -> True`: a command whose
        authoring omitted `prompt` resolves to an empty mode set, which the
        engine treats as "valid everywhere" (BASIC `exit` is such a command).
        """
        shell = CMDShell(**self.arguments)
        self.assertEqual(shell.commands["exit"].modes, frozenset())
        self.assertTrue(shell._in_current_mode(shell.commands["exit"]))
        shell.current_mode = "config"
        self.assertTrue(shell._in_current_mode(shell.commands["exit"]))

    def test__in_current_mode_membership(self):
        """A command is visible only in the modes it declares (#264 / D5).

        Replaces the `_check_prompt` string-match unit: `show clock`
        (authored for the user/enable prompts) is visible in those modes and
        hidden in config.
        """
        shell = CMDShell(**self.arguments)  # current_mode == "user"
        clock = shell.commands["show clock"]
        self.assertEqual(clock.modes, frozenset({"user", "enable"}))
        self.assertTrue(shell._in_current_mode(clock))
        shell.current_mode = "config"
        self.assertFalse(shell._in_current_mode(clock))

    def test_default_command_correct(self):
        """Test that the default method does nothing."""
        self.arguments["is_running"].set()
        shell = CMDShell(**self.arguments)
        writeline = set_attr(shell, "writeline", Mock())
        shell.default("show clock")
        writeline.assert_called_once_with("*21:01:33.000 AET 01 01 01 2022")

    def test_default_command_with_alias(self):
        """Test that the default method does nothing."""
        self.arguments["is_running"].set()
        shell = CMDShell(**self.arguments)
        writeline = set_attr(shell, "writeline", Mock())
        shell.default("sh clock")
        writeline.assert_called_once_with("*21:01:33.000 AET 01 01 01 2022")

    def test_default_command_is_function(self):
        """Test that the default method does nothing."""
        self.arguments["is_running"].set()
        self.arguments["nos"] = Nos(filename="tests/assets/module.py")
        shell = CMDShell(**self.arguments)
        writeline = set_attr(shell, "writeline", Mock())
        shell.default("show clock")
        writeline.assert_called_once_with(time.ctime())

    def _make_callable_dict_shell(self, output_callable):
        """Build a shell whose 'cmd' command output is `output_callable`.

        Consumer-side pins for the handler dispatch branch of `default()` —
        the dict-returning cases (new_mode transition / exit / output
        extraction, the counterpart of the producer-side device-class tests
        in tests/plugins/nos/, T-14 / #230), plus the str-passthrough (D-b)
        and crash (D4) pins. The synthetic platform declares all three
        canonical modes so handlers can transition (#264 / D5).
        """
        self.arguments["is_running"].set()
        self.arguments["nos"] = Nos(
            dict_args={
                "name": "synth",
                "initial_prompt": "{base_prompt}>",
                "enable_prompt": "{base_prompt}#",
                "config_prompt": "{base_prompt}(config)#",
                "commands": {
                    "cmd": {
                        "output": output_callable,
                        "help": "dict-returning callable",
                        "prompt": "{base_prompt}>",
                    },
                    "_default_": {"output": "% Unknown", "help": "default"},
                },
            }
        )
        shell = CMDShell(**self.arguments)
        return shell

    def test_default_callable_dict_new_mode(self):
        """Callable dict with new_mode transitions the shell to that mode."""
        shell = self._make_callable_dict_shell(lambda device, **kwargs: {"output": "", "new_mode": "enable"})
        writeline = set_attr(shell, "writeline", Mock())
        stop = shell.default("cmd")
        self.assertFalse(stop)
        self.assertEqual(shell.current_mode, "enable")
        self.assertEqual(shell.prompt, "test#")
        writeline.assert_called_once_with("")

    def test_default_callable_dict_unknown_new_mode_is_lenient(self):
        """A handler returning an unknown mode logs and stays put (#264 / D5)."""
        shell = self._make_callable_dict_shell(lambda device, **kwargs: {"output": "body", "new_mode": "nope"})
        writeline = set_attr(shell, "writeline", Mock())
        with self.assertLogs("simnos.plugins.shell.cmd_shell", level="ERROR") as captured:
            stop = shell.default("cmd")
        self.assertFalse(stop)
        self.assertEqual(shell.current_mode, "user")  # unchanged
        self.assertTrue(any("unknown mode 'nope'" in msg for msg in captured.output))
        writeline.assert_called_once_with("body")

    def test_default_static_new_mode_wins_over_handler(self):
        """A command's static new_mode overrides a handler-returned one (#264 / claude #8).

        Replicates v2's write order (handler new_prompt applied first, the
        command's own new_prompt last): when a command declares new_mode AND
        its handler returns a different one, the static one is the final state.
        """
        self.arguments["is_running"].set()
        self.arguments["nos"] = Nos(
            dict_args={
                "name": "synth",
                "initial_prompt": "{base_prompt}>",
                "enable_prompt": "{base_prompt}#",
                "config_prompt": "{base_prompt}(config)#",
                "commands": {
                    "cmd": {
                        "output": lambda device, **kwargs: {"output": "", "new_mode": "config"},
                        "new_prompt": "{base_prompt}#",  # static -> enable, wins
                        "prompt": "{base_prompt}>",
                    },
                },
            }
        )
        shell = CMDShell(**self.arguments)
        set_attr(shell, "writeline", Mock())
        shell.default("cmd")
        self.assertEqual(shell.current_mode, "enable")  # static new_mode, not handler's "config"

    def test_default_callable_dict_exit(self):
        """Callable dict with exit=True signals shell termination."""
        shell = self._make_callable_dict_shell(lambda device, **kwargs: {"exit": True})
        writeline = set_attr(shell, "writeline", Mock())
        stop = shell.default("cmd")
        self.assertTrue(stop)
        writeline.assert_not_called()

    def test_default_callable_dict_output_only(self):
        """Callable dict with output only writes it, prompt unchanged."""
        shell = self._make_callable_dict_shell(lambda device, **kwargs: {"output": "dynamic body"})
        writeline = set_attr(shell, "writeline", Mock())
        stop = shell.default("cmd")
        self.assertFalse(stop)
        self.assertEqual(shell.prompt, "test>")
        writeline.assert_called_once_with("dynamic body")

    def _make_prompt_form_shell(self, prompt_value):
        """Build a shell whose 'cmd' command uses the given `prompt` authoring form.

        Both a bare str and a list are valid authoring sugar for `prompt`;
        these pins guard that the two forms resolve to the same mode set and
        dispatch identically through the adapter (#264 / D6).
        """
        self.arguments["is_running"].set()
        self.arguments["nos"] = Nos(
            dict_args={
                "name": "synth",
                "initial_prompt": "{base_prompt}>",
                "enable_prompt": "{base_prompt}#",
                "commands": {
                    "cmd": {
                        "output": "form ok",
                        "help": "prompt-form pin",
                        "prompt": prompt_value,
                    },
                },
            }
        )
        shell = CMDShell(**self.arguments)
        return shell

    def test_default_prompt_str_authoring_dispatches(self):
        """A bare-str `prompt` resolves to the current mode and dispatches."""
        shell = self._make_prompt_form_shell("{base_prompt}>")
        writeline = set_attr(shell, "writeline", Mock())
        stop = shell.default("cmd")
        self.assertFalse(stop)
        writeline.assert_called_once_with("form ok")

    def test_default_prompt_list_authoring_dispatches(self):
        """A list `prompt` resolves to a mode set including the current mode."""
        shell = self._make_prompt_form_shell(["{base_prompt}>", "{base_prompt}#"])
        writeline = set_attr(shell, "writeline", Mock())
        stop = shell.default("cmd")
        self.assertFalse(stop)
        writeline.assert_called_once_with("form ok")

    def test_inventory_commands_resolve_through_adapter_and_dispatch(self):
        """Inventory-defined commands are normalized through the adapter too.

        Pins the third commands inflow (#264 / D6): `nos_inventory_config
        ["commands"]` is merged and adapted at shell (re)build like the BASIC
        and NOS inflows, so its prompt resolves to a mode set and dispatches.
        """
        self.arguments["is_running"].set()
        self.arguments["nos_inventory_config"] = {
            "commands": {
                "inv cmd": {
                    "output": "inventory ok",
                    "help": "inventory-defined",
                    "prompt": "{base_prompt}>",
                },
            },
        }
        shell = CMDShell(**self.arguments)
        writeline = set_attr(shell, "writeline", Mock())
        # The inventory command is normalized through the adapter like any
        # inflow: its "{base_prompt}>" prompt resolves to the user mode.
        self.assertEqual(shell.commands["inv cmd"].modes, frozenset({"user"}))
        stop = shell.default("inv cmd")
        self.assertFalse(stop)
        writeline.assert_called_once_with("inventory ok")

    def test_default_command_not_matching_prompt(self):
        """Test that the default method does nothing."""
        self.arguments["is_running"].set()
        shell = CMDShell(**self.arguments)
        writeline = set_attr(shell, "writeline", Mock())
        shell.default("show version")
        writeline.assert_called_once_with("% Invalid input detected at '^' marker.")

    def test_default_command_incorrect(self):
        """Test that the default method does nothing."""
        self.arguments["is_running"].set()
        shell = CMDShell(**self.arguments)
        writeline = set_attr(shell, "writeline", Mock())
        shell.default("test")
        writeline.assert_called_once_with("% Invalid input detected at '^' marker.")

    def test_default_alias_target_missing_falls_back_default(self):
        """An alias whose target command is gone degrades to `_default_`.

        The adapter drops a broken alias at load (logged), so it never reaches
        `self.commands`; typing it is then an unknown command answered with the
        `_default_` output, never a handler-crash response (#264 / D6).
        """
        self.arguments["is_running"].set()
        with self.assertLogs("simnos.core.command_adapter", level="WARNING"):
            self.arguments["nos"] = Nos(
                dict_args={
                    "name": "synth",
                    "initial_prompt": "{base_prompt}>",
                    "commands": {
                        "broken alias": {"alias": "no such target"},
                        "_default_": {"output": "% Invalid input", "help": "default"},
                    },
                }
            )
            shell = CMDShell(**self.arguments)
        self.assertNotIn("broken alias", shell.commands)
        writeline = set_attr(shell, "writeline", Mock())
        shell.default("broken alias")
        writeline.assert_called_once_with("% Invalid input")

    def test_invoke_handler_str_return_normalized(self):
        """`_invoke_handler` wraps a str return into a CommandResult dict.

        Pins the consumer-side normalization (#241/D2, #264): a plain str
        return is sugar for `{"output": <str>}`, so the dispatch body only
        ever consumes the dict form.
        """
        shell = CMDShell(**self.arguments)
        result = shell._invoke_handler(lambda device, **kwargs: "body", "cmd")
        self.assertEqual(result, {"output": "body"})

    def test_invoke_handler_none_return_normalized(self):
        """`_invoke_handler` wraps a None return (= write nothing) too."""
        shell = CMDShell(**self.arguments)
        result = shell._invoke_handler(lambda device, **kwargs: None, "cmd")
        self.assertEqual(result, {"output": None})

    def test_invoke_handler_dict_return_passthrough(self):
        """`_invoke_handler` passes a CommandResult dict through unchanged."""
        shell = CMDShell(**self.arguments)
        result = shell._invoke_handler(lambda device, **kwargs: {"output": "x", "exit": True}, "cmd")
        self.assertEqual(result, {"output": "x", "exit": True})

    def test_invoke_handler_receives_current_mode(self):
        """`_invoke_handler` passes the current mode name to the handler (#264)."""
        shell = CMDShell(**self.arguments)
        seen = {}

        def handler(device, **kwargs):
            seen.update(kwargs)
            return "ok"

        shell._invoke_handler(handler, "cmd")
        self.assertEqual(seen["current_mode"], shell.current_mode)

    def _make_callable_default_shell(self):
        """Build a shell whose `_default_` output is a callable.

        No shipped plugin has a callable `_default_` (yaml cannot express
        one; the py plugins use strings), but the Python API
        (`SimNOS(inventory=dict)`) can reach it — these pins fix the #241
        unification: both the unknown-command and the mode-mismatch fallback
        invoke the callable through `_invoke_handler`.
        """
        self.arguments["is_running"].set()
        self.arguments["nos"] = Nos(
            dict_args={
                "name": "synth",
                "initial_prompt": "{base_prompt}>",
                "enable_prompt": "{base_prompt}#",
                "commands": {
                    "known": {
                        "output": "static",
                        "help": "enable-mode only",
                        "prompt": "{base_prompt}#",
                    },
                    "_default_": {
                        "output": lambda device, **kwargs: f"dynamic unknown: {kwargs['command']}",
                        "help": "callable default",
                    },
                },
            }
        )
        shell = CMDShell(**self.arguments)
        return shell

    def test_default_callable_default_invoked_on_unknown_command(self):
        """An unknown command invokes a callable `_default_` (#241)."""
        shell = self._make_callable_default_shell()
        writeline = set_attr(shell, "writeline", Mock())
        stop = shell.default("nope")
        self.assertFalse(stop)
        writeline.assert_called_once_with("dynamic unknown: nope")

    def test_default_callable_default_invoked_on_mode_mismatch(self):
        """A mode mismatch invokes a callable `_default_` (#241 / #264).

        `known` is enable-only; typed in user mode it misses, and the fallback
        invokes the callable `_default_` through `_invoke_handler`.
        """
        shell = self._make_callable_default_shell()
        writeline = set_attr(shell, "writeline", Mock())
        stop = shell.default("known")  # valid only in enable, current mode is user
        self.assertFalse(stop)
        writeline.assert_called_once_with("dynamic unknown: known")

    def test_default_callable_default_dict_return_gets_full_dispatch(self):
        """A dict-returning callable `_default_` gets the same dispatch (#241 / #264).

        Pins that the unification is complete: a callable `_default_` flows
        through `_invoke_handler` like any handler, so its dict return's
        `new_mode` (and `exit`) take effect.
        """
        self.arguments["is_running"].set()
        self.arguments["nos"] = Nos(
            dict_args={
                "name": "synth",
                "initial_prompt": "{base_prompt}>",
                "enable_prompt": "{base_prompt}#",
                "commands": {
                    "_default_": {
                        "output": lambda device, **kwargs: {"output": "locked out", "new_mode": "enable"},
                        "help": "dict-returning callable default",
                    },
                },
            }
        )
        shell = CMDShell(**self.arguments)
        writeline = set_attr(shell, "writeline", Mock())
        stop = shell.default("nope")
        self.assertFalse(stop)
        self.assertEqual(shell.current_mode, "enable")
        self.assertEqual(shell.prompt, "test#")
        writeline.assert_called_once_with("locked out")

    def test_default_handler_crash_writes_fixed_error_line(self):
        """A crashing handler answers with HANDLER_ERROR_OUTPUT only.

        Pins #241/D4: real NOSes never print Python tracebacks, and the
        old behavior (traceback.format_exc() sent to the SSH client) made
        Netmiko-side parsers chew on stack frames and leaked internal
        paths. The wire now gets the fixed one-liner; the session stays up.
        """

        def crash(device, **kwargs):
            raise RuntimeError("boom")

        shell = self._make_callable_dict_shell(crash)
        writeline = set_attr(shell, "writeline", Mock())
        with self.assertLogs("simnos.plugins.shell.cmd_shell", level="ERROR"):
            stop = shell.default("cmd")
        self.assertFalse(stop)
        writeline.assert_called_once_with(HANDLER_ERROR_OUTPUT)

    def test_default_handler_crash_logs_full_traceback(self):
        """A crashing handler's traceback goes to the server log.

        Pins #241/D4 (the diagnosability half): dropping the wire
        traceback must not lose the information — the log carries the
        full `traceback.format_exc()` including the original exception,
        same shape as the hot-reload guard (#232).
        """

        def crash(device, **kwargs):
            raise RuntimeError("boom-for-log")

        shell = self._make_callable_dict_shell(crash)
        # crash-path guard: default() writes HANDLER_ERROR_OUTPUT via writeline,
        # and stdout is None, so writeline must be mocked even though this test
        # only asserts on the log (return unused → bare set_attr).
        set_attr(shell, "writeline", Mock())
        with self.assertLogs("simnos.plugins.shell.cmd_shell", level="ERROR") as captured:
            shell.default("cmd")
        self.assertEqual(len(captured.output), 1)
        self.assertIn("handler crashed", captured.output[0])
        self.assertIn("RuntimeError: boom-for-log", captured.output[0])
        self.assertIn("Traceback", captured.output[0])

    def test_default_callable_dict_output_passed_through_unformatted(self):
        """Callable-dict output is written verbatim, never re-rendered (#241 / D-b).

        Handlers render themselves, so brace-containing device output reaches
        the wire untouched — the shell applies no template step to handler
        output, hence **no error log**. Holds for dict and str returns alike.
        """
        shell = self._make_callable_dict_shell(lambda device, **kwargs: {"output": "value is {base_prompt.foo}"})
        writeline = set_attr(shell, "writeline", Mock())
        with self.assertNoLogs("simnos.plugins.shell.cmd_shell", level="ERROR"):
            stop = shell.default("cmd")
        self.assertFalse(stop)
        writeline.assert_called_once_with("value is {base_prompt.foo}")

    def test_default_callable_str_output_passed_through_unformatted(self):
        """Callable str output is written verbatim too (#241 / D-b).

        The str-return twin of the dict pin above: literal braces in a
        handler's rendered output (e.g. JSON-ish device output) reach the
        wire untouched, with no render step and no error log.
        """
        shell = self._make_callable_dict_shell(lambda device, **kwargs: "literal {brace} stays")
        writeline = set_attr(shell, "writeline", Mock())
        with self.assertNoLogs("simnos.plugins.shell.cmd_shell", level="ERROR"):
            stop = shell.default("cmd")
        self.assertFalse(stop)
        writeline.assert_called_once_with("literal {brace} stays")

    def test_default_command_transitions_mode(self):
        """A command with a new_mode transitions the shell and re-renders the prompt.

        `enable` (yaml_nos) declares new_mode=enable; dispatching it from the
        initial user mode moves current_mode to enable and the prompt to
        "test#" (the enable prompt rendered at base_prompt "test").
        """
        self.arguments["is_running"].set()
        shell = CMDShell(**self.arguments)
        set_attr(shell, "writeline", Mock())  # stdout is None; guard only
        shell.default("enable")
        self.assertEqual(shell.current_mode, "enable")
        self.assertEqual(shell.prompt, "test#")

    def test_default_command_exit(self):
        """Test that the default method does nothing."""
        self.arguments["is_running"].set()
        shell = CMDShell(**self.arguments)
        self.assertTrue(shell.default("exit"))

    def test_do_eof(self):
        """Test that do_EOF returns True to exit cmdloop gracefully."""
        self.arguments["is_running"].set()
        shell = CMDShell(**self.arguments)
        self.assertTrue(shell.do_EOF(""))


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
        """Test that the if is not set  hot_reload method does nothing."""
        os.environ.pop("SIMNOS_RELOAD_COMMANDS")
        shell = CMDShell(**self.arguments)
        mock_get_files_changed = set_attr(shell, "get_files_changed", Mock())
        shell.precmd("show clock")
        mock_get_files_changed.assert_not_called()

    @patch("simnos.plugins.shell.cmd_shell.get_files_changed")
    def test_hot_reload_activated_does_enter(self, mock_get_files_changed):
        """Test that if there are no changed files, nothing happens."""
        mock_get_files_changed.return_value = []
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
        mock_get_files_changed.return_value = [changed_module.replace(".", "/") + ".py"]
        shell = CMDShell(**self.arguments)
        shell.precmd("show clock")
        module = importlib.import_module(changed_module)
        mock_from_file.assert_called_once()
        mock_from_file.assert_called_once_with(module.__name__.replace(".", "/") + ".py")
        assert all(key in shell.commands for key in module.commands)

    def test_reload_commands_broken_file_logs_and_continues(self):
        """One broken file does not kill the session nor block the rest.

        Pins the per-file lenient guard in `reload_commands` (#232): a
        half-written or malformed plugin file observed by hot reload used
        to raise out of `precmd` and crash the whole shell thread. Now the
        broken file is logged and skipped while remaining files reload.
        """
        shell = CMDShell(**self.arguments)
        set_attr(shell.nos, "from_file", Mock(side_effect=[ValueError("boom"), None]))
        set_attr(shell.nos, "commands", {"healthy": {"output": "ok"}})
        with self.assertLogs("simnos.plugins.shell.cmd_shell", level="ERROR") as captured:
            shell.reload_commands(["broken.yaml", "healthy.yaml"])
        self.assertEqual(len(captured.output), 1)
        self.assertIn("broken.yaml", captured.output[0])
        self.assertIn("healthy", shell.commands)

    def test_reload_commands_adapter_failure_rolls_back_and_unblocks_rest(self):
        """A file that loads but fails normalization is rolled back from nos (#264 / codex #1).

        `from_file` commits to `self.nos` before `_rebuild` validates via the
        adapter, so a canonical-外 prompt that passes the legacy schema but
        fails normalization would, without rollback, persist in `nos.commands`
        and re-fail every later file in the batch. The per-file rollback must
        drop it so a following healthy file still applies.
        """
        shell = CMDShell(**self.arguments)

        def fake_from_file(filename):
            if filename == "bad.yaml":
                # passes pydantic, fails the adapter (no mode renders to this)
                shell.nos.commands["bad cmd"] = {"output": "x", "prompt": "{base_prompt}ALIEN>"}
            else:
                shell.nos.commands["good cmd"] = {"output": "ok", "prompt": "{base_prompt}>"}

        set_attr(shell.nos, "from_file", Mock(side_effect=fake_from_file))
        with self.assertLogs("simnos.plugins.shell.cmd_shell", level="ERROR") as captured:
            shell.reload_commands(["bad.yaml", "good.yaml"])
        self.assertEqual(len(captured.output), 1)  # only the bad file
        self.assertNotIn("bad cmd", shell.nos.commands)  # rolled back, not poisoning the batch
        self.assertIn("good cmd", shell.commands)  # the healthy file still applied

    def test_reload_commands_broken_file_last_still_applies_rest(self):
        """The per-file guard is order-independent: broken file last.

        Complements `test_reload_commands_broken_file_logs_and_continues`
        (broken first): the healthy file's commands are applied before the
        broken file raises, and the error is still logged.
        """
        shell = CMDShell(**self.arguments)
        set_attr(shell.nos, "from_file", Mock(side_effect=[None, ValueError("boom")]))
        set_attr(shell.nos, "commands", {"healthy": {"output": "ok"}})
        with self.assertLogs("simnos.plugins.shell.cmd_shell", level="ERROR") as captured:
            shell.reload_commands(["healthy.yaml", "broken.yaml"])
        self.assertEqual(len(captured.output), 1)
        self.assertIn("broken.yaml", captured.output[0])
        self.assertIn("healthy", shell.commands)

    def test_reload_commands_broken_py_plugin_does_not_leak_commands(self):
        """A broken py plugin skipped by the guard never reaches the shell.

        Pins the #232 cross-review hole: `_from_module` used to commit
        attrs/commands before the device-class validation, so a broken py
        plugin polluted `nos.commands` even though the per-file guard
        skipped it — and the next successful reload then leaked the broken
        plugin's commands into the shell via `commands.update(nos.commands)`.
        The broken asset raises the #241/D5 multiple-subclass ValueError;
        like the pre-#241 DEVICE_NAME AttributeError it fires in the build
        phase, before any commit, so the leak check is equivalent.
        """
        shell = CMDShell(**self.arguments)
        with self.assertLogs("simnos.plugins.shell.cmd_shell", level="ERROR") as captured:
            shell.reload_commands(["tests/assets/broken_multi_device_module.py", "tests/assets/module.py"])
        self.assertEqual(len(captured.output), 1)
        self.assertNotIn("polluting command", shell.commands)  # broken plugin never leaks
        self.assertIn("show version", shell.commands)  # healthy reload still applied

    @staticmethod
    def _atomic_write(path: str, content: str, suffix: str) -> None:
        """Write `content` to `path` atomically (tempfile + `os.replace`).

        `suffix` must be a non-watched `.bak`-based extension so neither
        the tempfile nor an empty/partial target is ever visible to a
        hot-reload watcher (#232).
        """
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix=suffix)
        try:
            file = os.fdopen(fd, "w", encoding="utf-8")
        except BaseException:
            # `fd` is only ours to close until fdopen takes ownership.
            os.close(fd)
            os.unlink(tmp)
            raise
        try:
            with file:
                file.write(content)
            os.replace(tmp, path)
        except BaseException:
            os.unlink(tmp)
            raise

    @pytest.mark.skipif(sys.platform == "win32", reason="Windows does not allow file movement on Github runners")
    @pytest.mark.xdist_group("hot-reload-fs")
    @simnos(device_type="cisco_ios", return_instance=True)
    def test_hot_reload_integration_py_jinja(self, net: SimNOS):
        """
        Test that the hot reload feature works correctly for a py-template edit.

        Mutates the real `simnos/plugins/nos/` tree that every reload-enabled
        server in the worker process watches, so it is serialized onto one
        worker via `xdist_group` and keeps its backup on a non-watched `.bak`
        extension (#232: a sibling worker observed a mid-`copyfile` empty file
        and crashed its shell thread).

        A3 platform-dir hot reload (editing `platforms/<p>/commands/*`) is a
        separate, deferred capability (#274 / PR-4) — the legacy monolithic-yaml
        hot-reload integration test was removed with that data form (#264).
        """
        original_filename = "simnos/plugins/nos/platforms_py/templates/cisco_ios/show_version.j2"
        copy_filename = "simnos/plugins/nos/platforms_py/templates/cisco_ios/show_version.j2.bak"

        def change_file():
            shutil.copyfile(original_filename, copy_filename)
            self._atomic_write(original_filename, "test output", suffix=".j2.bak")

        def undo_change_file():
            # Atomic restore: no window where the original is missing.
            os.replace(copy_filename, original_filename)

        device = list(net.hosts.values())
        credentials = {
            "host": "localhost",
            "username": device[0].username,
            "password": device[0].password,
            "port": device[0].port,
            "device_type": "cisco_ios",
        }
        with ConnectHandler(**credentials) as conn:
            conn.enable()
            output = conn.send_command("show version")
            assert output != "test output"
            change_file()
            try:
                output = conn.send_command("show version")
                assert output == "test output"
            finally:
                undo_change_file()
