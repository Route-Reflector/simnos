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


def make_cmd_shell_args() -> dict:
    """Build the CMDShell constructor kwargs shared across cmd_shell tests (SSoT)."""
    return {
        "stdin": None,
        "stdout": None,
        "nos": Nos(filename="tests/assets/yaml_nos.yaml"),
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
            CMDShell()

    def test_init_error_if_nos_inventory_config_not_provided(self):
        """Test the init method raises an error if nos_inventory_config is not provided."""
        with self.assertRaises(TypeError):
            # pylint: disable=no-value-for-parameter
            CMDShell(nos=Nos(filename="tests/assets/yaml_nos.yaml"))

    def test_init_error_if_base_prompt_not_provided(self):
        """Test the init method raises an error if base_prompt is not provided."""
        with self.assertRaises(TypeError):
            # pylint: disable=no-value-for-parameter
            CMDShell(nos=Nos(filename="tests/assets/yaml_nos.yaml"), nos_inventory_config={})

    def test_init_error_if_is_running_not_provided(self):
        """Test the init method raises an error if is_running is not provided."""
        with self.assertRaises(TypeError):
            # pylint: disable=no-value-for-parameter
            CMDShell(
                nos=Nos(filename="tests/assets/yaml_nos.yaml"),
                nos_inventory_config={},
                base_prompt="test",
            )

    def test_init_broken_initial_prompt_falls_back_to_raw(self):
        """A malformed initial_prompt template must not crash construction.

        Pins #172: `__init__` used to call `.format()` unguarded, so a
        broken template killed every connection to the host. The lenient
        fallback keeps the session usable (raw template as prompt) and
        logs the error for diagnosis.
        """
        self.arguments["nos"] = Nos(
            dict_args={
                "name": "synth",
                "initial_prompt": "{base_prompt.foo}>",
                "commands": {"_default_": {"output": "% Unknown", "help": "default"}},
            }
        )
        with self.assertLogs("simnos.plugins.shell.cmd_shell", level="ERROR") as captured:
            shell = CMDShell(**self.arguments)
        self.assertEqual(shell.prompt, "{base_prompt.foo}>")
        self.assertEqual(len(captured.output), 1)
        self.assertTrue(any("error formatting initial_prompt" in msg for msg in captured.output))

    def test_start(self):
        """Test that the start method calls cmdloop."""
        shell = CMDShell(**self.arguments)
        mock_cmdloop = Mock()
        shell.cmdloop = mock_cmdloop
        shell.start()
        mock_cmdloop.assert_called_once()

    def test_stop(self):
        """Test that the stop method writes "exit" to stdin."""
        shell = CMDShell(**self.arguments)
        shell.stdin = Mock()
        shell.stop()
        shell.stdin.write.assert_called_once_with("exit\r\n")

    def test_writeline(self):
        """Test that the writeline method writes a line to stdout with a newline at the end."""
        shell = CMDShell(**self.arguments)
        shell.stdout = Mock()
        shell.writeline("test")
        shell.stdout.write.assert_called_once_with("test\r\n")

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
        shell.writeline = Mock()
        shell.do_help("")
        expected_output: list[str] = [
            "exit                Exit commands shell",
            "enable              enter exec prompt",
            "sh clock            ",
            "show clock          Display the system clock",
            "terminal width 511  Set terminal width to 511",
            "terminal length 0   Set terminal length to 0",
        ]
        shell.writeline.assert_called_once_with("\r\n".join(expected_output))

    def test__check_prompt_is_none(self):
        """Test that the _check_prompt method returns the prompt."""
        shell = CMDShell(**self.arguments)
        # pylint: disable=protected-access
        self.assertTrue(shell._check_prompt(None))

    def test__check_prompt_str_is_normalized_before_reaching_here(self):
        """A bare-str prompt never reaches `_check_prompt` at runtime.

        Pins the lists-only read-side contract (#244 / D3): every load
        path (yaml/py via `Nos`, inventory commands at shell init)
        normalizes str -> [str] before commit, so the str branch was
        removed here. The authoring sugar itself is covered end-to-end by
        test_default_prompt_str_authoring_dispatches.
        """
        self.arguments["is_running"].set()
        shell = CMDShell(**self.arguments)
        # yaml_nos.yaml authors prompts as bare strings; the shell must
        # see them as lists after the load-path normalization.
        prompt = shell.commands["show clock"]["prompt"]
        self.assertIsInstance(prompt, list)

    def test__check_prompt_is_list(self):
        """Test that the _check_prompt method returns the prompt."""
        shell = CMDShell(**self.arguments)
        # pylint: disable=protected-access
        self.assertTrue(shell._check_prompt(["{base_prompt}>"]))

    def test__check_prompt_is_not_prompt(self):
        """Test that the _check_prompt method returns False."""
        shell = CMDShell(**self.arguments)
        # pylint: disable=protected-access
        self.assertFalse(shell._check_prompt("{base_prompt}"))

    def test_default_command_correct(self):
        """Test that the default method does nothing."""
        self.arguments["is_running"].set()
        shell = CMDShell(**self.arguments)
        shell.writeline = Mock()
        shell.default("show clock")
        shell.writeline.assert_called_once_with("*21:01:33.000 AET 01 01 01 2022")

    def test_default_command_with_alias(self):
        """Test that the default method does nothing."""
        self.arguments["is_running"].set()
        shell = CMDShell(**self.arguments)
        shell.writeline = Mock()
        shell.default("sh clock")
        shell.writeline.assert_called_once_with("*21:01:33.000 AET 01 01 01 2022")

    def test_default_command_is_function(self):
        """Test that the default method does nothing."""
        self.arguments["is_running"].set()
        self.arguments["nos"] = Nos(filename="tests/assets/module.py")
        shell = CMDShell(**self.arguments)
        shell.writeline = Mock()
        shell.default("show clock")
        shell.writeline.assert_called_once_with(time.ctime())

    def _make_callable_dict_shell(self, output_callable):
        """Build a shell whose 'cmd' command output is `output_callable`.

        Consumer-side pins for the callable dispatch branch of
        `default()` — originally the dict-returning cases (new_prompt
        update / exit / output extraction, the counterpart of the
        producer-side device-class tests in tests/plugins/nos/, T-14 /
        #230), since #241 also the str-passthrough (D-b) and crash (D4)
        pins. Plugin-loaded str returns are additionally covered by
        test_default_command_is_function above.
        """
        self.arguments["is_running"].set()
        self.arguments["nos"] = Nos(
            dict_args={
                "name": "synth",
                "initial_prompt": "{base_prompt}>",
                "commands": {
                    "cmd": {
                        "output": output_callable,
                        "help": "dict-returning callable",
                        "prompt": "{base_prompt}>",
                    },
                    "_default_": {
                        "output": "% Unknown",
                        "help": "default",
                        "prompt": "{base_prompt}>",
                    },
                },
            }
        )
        shell = CMDShell(**self.arguments)
        shell.writeline = Mock()
        return shell

    def test_default_callable_dict_new_prompt(self):
        """Callable dict with new_prompt updates the prompt (formatted)."""
        shell = self._make_callable_dict_shell(lambda device, **kwargs: {"output": "", "new_prompt": "{base_prompt}#"})
        stop = shell.default("cmd")
        self.assertFalse(stop)
        self.assertEqual(shell.prompt, "test#")
        shell.writeline.assert_called_once_with("")

    def test_default_callable_dict_exit(self):
        """Callable dict with exit=True signals shell termination."""
        shell = self._make_callable_dict_shell(lambda device, **kwargs: {"exit": True})
        stop = shell.default("cmd")
        self.assertTrue(stop)
        shell.writeline.assert_not_called()

    def test_default_callable_dict_output_only(self):
        """Callable dict with output only writes it, prompt unchanged."""
        shell = self._make_callable_dict_shell(lambda device, **kwargs: {"output": "dynamic body"})
        stop = shell.default("cmd")
        self.assertFalse(stop)
        self.assertEqual(shell.prompt, "test>")
        shell.writeline.assert_called_once_with("dynamic body")

    def _make_prompt_form_shell(self, prompt_value):
        """Build a shell whose 'cmd' command uses the given `prompt` authoring form.

        Both a bare str and a list are valid authoring sugar for `prompt`
        (#244 / P-12c); these pins guard that the two forms keep
        dispatching identically across the load-path normalization
        (str -> [str] inside `Nos`).
        """
        self.arguments["is_running"].set()
        self.arguments["nos"] = Nos(
            dict_args={
                "name": "synth",
                "initial_prompt": "{base_prompt}>",
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
        shell.writeline = Mock()
        return shell

    def test_default_prompt_str_authoring_dispatches(self):
        """A bare-str `prompt` matches the current prompt and dispatches."""
        shell = self._make_prompt_form_shell("{base_prompt}>")
        stop = shell.default("cmd")
        self.assertFalse(stop)
        shell.writeline.assert_called_once_with("form ok")

    def test_default_prompt_list_authoring_dispatches(self):
        """A list `prompt` matches the current prompt and dispatches."""
        shell = self._make_prompt_form_shell(["{base_prompt}>", "{base_prompt}#"])
        stop = shell.default("cmd")
        self.assertFalse(stop)
        shell.writeline.assert_called_once_with("form ok")

    def test_inventory_commands_prompt_str_is_normalized_and_dispatches(self):
        """Inventory-defined commands get the same str -> [str] normalization.

        Pins the third commands inflow (#244 / D3, found during
        implementation): `nos_inventory_config["commands"]` bypasses the
        `Nos` load path, so the shell normalizes it at init — without
        this, a bare-str prompt would be iterated char by char after the
        read-side isinstance branch removal (a silent never-match).
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
        shell.writeline = Mock()
        self.assertEqual(shell.commands["inv cmd"]["prompt"], ["{base_prompt}>"])
        stop = shell.default("inv cmd")
        self.assertFalse(stop)
        shell.writeline.assert_called_once_with("inventory ok")

    def test_default_command_not_matching_prompt(self):
        """Test that the default method does nothing."""
        self.arguments["is_running"].set()
        shell = CMDShell(**self.arguments)
        shell.writeline = Mock()
        shell.default("show version")
        shell.writeline.assert_called_once_with("% Invalid input detected at '^' marker.")

    def test_default_command_incorrect(self):
        """Test that the default method does nothing."""
        self.arguments["is_running"].set()
        shell = CMDShell(**self.arguments)
        shell.writeline = Mock()
        shell.default("test")
        shell.writeline.assert_called_once_with("% Invalid input detected at '^' marker.")

    def test_default_alias_target_missing_falls_back_default(self):
        """An alias whose target command is gone degrades to `_default_`.

        Pins #241 (G4/D4 例外境界): the alias-merge KeyError is a lenient
        unknown-command path — it must answer with the `_default_` output
        like any unknown command, never with the handler-crash response.
        Guards the `_resolve_command` decomposition against widening the
        exception boundary (1st design review 🦊 #2).
        """
        self.arguments["is_running"].set()
        shell = CMDShell(**self.arguments)
        shell.writeline = Mock()
        shell.commands["broken alias"] = {"alias": "no such target"}
        shell.default("broken alias")
        shell.writeline.assert_called_once_with("% Invalid input detected at '^' marker.")

    def test_resolve_command_unknown_returns_none(self):
        """`_resolve_command` degrades an unknown command to None.

        Unit pin for the #241 decomposition: the unknown-command KeyError
        is consumed inside the helper so `default()` needs no try block
        around resolution.
        """
        shell = CMDShell(**self.arguments)
        # pylint: disable=protected-access
        self.assertIsNone(shell._resolve_command("no such command"))

    def test_resolve_command_alias_target_missing_returns_none(self):
        """`_resolve_command` degrades a missing alias target to None.

        Unit counterpart of test_default_alias_target_missing_falls_back
        _default (#241): the alias-merge KeyError must stay inside the
        helper, on the same lenient path as an unknown command.
        """
        shell = CMDShell(**self.arguments)
        shell.commands["broken alias"] = {"alias": "no such target"}
        # pylint: disable=protected-access
        self.assertIsNone(shell._resolve_command("broken alias"))

    def test_resolve_command_alias_merges_target(self):
        """`_resolve_command` merges the alias target under the alias keys.

        Pins the `{**commands[target], **cmd_data}` merge order (#241):
        the alias entry's own keys win over the target's.
        """
        shell = CMDShell(**self.arguments)
        # pylint: disable=protected-access
        merged = shell._resolve_command("sh clock")
        self.assertEqual(merged["output"], "*21:01:33.000 AET 01 01 01 2022")
        self.assertEqual(merged["alias"], "show clock")

    def test_invoke_callable_str_return_normalized(self):
        """`_invoke_callable` wraps a str return into a CommandResult dict.

        Pins the #241/D2 consumer-side normalization: a plain str return
        is sugar for `{"output": <str>}`, so the dispatch body only ever
        consumes the dict form.
        """
        shell = CMDShell(**self.arguments)
        # pylint: disable=protected-access
        result = shell._invoke_callable(lambda device, **kwargs: "body", "cmd")
        self.assertEqual(result, {"output": "body"})

    def test_invoke_callable_none_return_normalized(self):
        """`_invoke_callable` wraps a None return (= write nothing) too."""
        shell = CMDShell(**self.arguments)
        # pylint: disable=protected-access
        result = shell._invoke_callable(lambda device, **kwargs: None, "cmd")
        self.assertEqual(result, {"output": None})

    def test_invoke_callable_dict_return_passthrough(self):
        """`_invoke_callable` passes a CommandResult dict through unchanged."""
        shell = CMDShell(**self.arguments)
        # pylint: disable=protected-access
        result = shell._invoke_callable(lambda device, **kwargs: {"output": "x", "exit": True}, "cmd")
        self.assertEqual(result, {"output": "x", "exit": True})

    def _make_callable_default_shell(self):
        """Build a shell whose `_default_` output is a callable.

        No shipped plugin has a callable `_default_` (yaml cannot express
        one; the py plugins use strings), but the Python API
        (`SimNOS(inventory=dict)`) can reach it — these pins fix the #241
        unification: both the unknown-command and the prompt-mismatch
        fallback invoke the callable through `_invoke_callable` (the old
        code degraded to a fixed error string / leaked the function repr
        respectively).
        """
        self.arguments["is_running"].set()
        self.arguments["nos"] = Nos(
            dict_args={
                "name": "synth",
                "initial_prompt": "{base_prompt}>",
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
        shell.writeline = Mock()
        return shell

    def test_default_callable_default_invoked_on_unknown_command(self):
        """An unknown command invokes a callable `_default_` (#241)."""
        shell = self._make_callable_default_shell()
        stop = shell.default("nope")
        self.assertFalse(stop)
        shell.writeline.assert_called_once_with("dynamic unknown: nope")

    def test_default_callable_default_invoked_on_prompt_mismatch(self):
        """A prompt mismatch invokes a callable `_default_` (#241).

        The old code never invoked it on this path — `_safe_format`
        swallowed the AttributeError and the function repr leaked to the
        wire. The unification fixes that display bug.
        """
        shell = self._make_callable_default_shell()
        stop = shell.default("known")  # requires "test#", current prompt is "test>"
        self.assertFalse(stop)
        shell.writeline.assert_called_once_with("dynamic unknown: known")

    def test_default_callable_default_dict_return_gets_full_dispatch(self):
        """A dict-returning callable `_default_` gets the same dispatch (#241).

        Pins that the unification is complete: a callable `_default_`
        flows through `_invoke_callable` like any handler, so its dict
        return's `new_prompt` (and `exit`) take effect. Unreachable in
        the old code (the callable was never invoked on these paths).
        """
        self.arguments["is_running"].set()
        self.arguments["nos"] = Nos(
            dict_args={
                "name": "synth",
                "initial_prompt": "{base_prompt}>",
                "commands": {
                    "_default_": {
                        "output": lambda device, **kwargs: {"output": "locked out", "new_prompt": "{base_prompt}#"},
                        "help": "dict-returning callable default",
                    },
                },
            }
        )
        shell = CMDShell(**self.arguments)
        shell.writeline = Mock()
        stop = shell.default("nope")
        self.assertFalse(stop)
        self.assertEqual(shell.prompt, "test#")
        shell.writeline.assert_called_once_with("locked out")

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
        with self.assertLogs("simnos.plugins.shell.cmd_shell", level="ERROR"):
            stop = shell.default("cmd")
        self.assertFalse(stop)
        shell.writeline.assert_called_once_with(HANDLER_ERROR_OUTPUT)

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
        with self.assertLogs("simnos.plugins.shell.cmd_shell", level="ERROR") as captured:
            shell.default("cmd")
        self.assertEqual(len(captured.output), 1)
        self.assertIn("handler crashed", captured.output[0])
        self.assertIn("RuntimeError: boom-for-log", captured.output[0])
        self.assertIn("Traceback", captured.output[0])

    def test_default_silent_fallback_on_keyerror(self):
        """`KeyError` failure mode of `.format()` is silently logged.

        Pins #162: `cmd_shell.default()` is intentionally lenient about
        yaml format errors (silent log + raw passthrough), in contrast
        to `tasks.render_template` which raises `RuntimeError` at build
        time. The runtime catch set is kept aligned with the build-time
        counterpart at `(KeyError, IndexError, ValueError)`, so both
        paths cover the same `str.format()` failure modes; only the
        action (raise vs silent) differs.
        """
        self.arguments["is_running"].set()
        shell = CMDShell(**self.arguments)
        shell.writeline = Mock()
        shell.commands["broken_key_cmd"] = {
            "output": "value is {unknown_key}",
            "prompt": ["{base_prompt}>"],
        }
        with self.assertLogs("simnos.plugins.shell.cmd_shell", level="ERROR") as captured:
            shell.default("broken_key_cmd")
        self.assertEqual(len(captured.output), 1)
        self.assertTrue(any("error formatting output" in msg and "broken_key_cmd" in msg for msg in captured.output))
        shell.writeline.assert_called_once_with("value is {unknown_key}")

    def test_default_silent_fallback_on_valueerror(self):
        """`ValueError` failure mode of `.format()` is silently logged.

        Pins #162: covers the malformed-brace path (a bare `{` with no
        closing `}`). Same lenient-runtime contract as the `KeyError`
        case — the catch set `(KeyError, IndexError, ValueError)`
        mirrors `tasks.render_template`.
        """
        self.arguments["is_running"].set()
        shell = CMDShell(**self.arguments)
        shell.writeline = Mock()
        shell.commands["broken_brace_cmd"] = {
            "output": "value is {broken",
            "prompt": ["{base_prompt}>"],
        }
        with self.assertLogs("simnos.plugins.shell.cmd_shell", level="ERROR") as captured:
            shell.default("broken_brace_cmd")
        self.assertEqual(len(captured.output), 1)
        self.assertTrue(any("error formatting output" in msg and "broken_brace_cmd" in msg for msg in captured.output))
        shell.writeline.assert_called_once_with("value is {broken")

    def test_default_silent_fallback_on_indexerror(self):
        """`IndexError` failure mode of `.format()` is silently logged.

        Pins #162: covers the positional-placeholder path (`{}` / `{N}`
        against an empty positional-args tuple). Same lenient-runtime
        contract as the other two cases; together the three tests pin
        each member of the catch set `(KeyError, IndexError, ValueError)`
        shared with `tasks.render_template`.
        """
        self.arguments["is_running"].set()
        shell = CMDShell(**self.arguments)
        shell.writeline = Mock()
        shell.commands["broken_pos_cmd"] = {
            "output": "value is {}",
            "prompt": ["{base_prompt}>"],
        }
        with self.assertLogs("simnos.plugins.shell.cmd_shell", level="ERROR") as captured:
            shell.default("broken_pos_cmd")
        self.assertEqual(len(captured.output), 1)
        self.assertTrue(any("error formatting output" in msg and "broken_pos_cmd" in msg for msg in captured.output))
        shell.writeline.assert_called_once_with("value is {}")

    def test_default_silent_fallback_on_attributeerror(self):
        """`AttributeError` failure mode of `.format()` is silently logged.

        Pins #171: attribute access (`{base_prompt.foo}`) used to escape
        the 3-tuple catch set — and the output format sits *outside* the
        broad try block of `default()`, so this crashed the whole shell
        session instead of just leaking a traceback. Now covered by the
        shared 5-tuple `FORMAT_ERRORS`.
        """
        self.arguments["is_running"].set()
        shell = CMDShell(**self.arguments)
        shell.writeline = Mock()
        shell.commands["broken_attr_cmd"] = {
            "output": "value is {base_prompt.foo}",
            "prompt": ["{base_prompt}>"],
        }
        with self.assertLogs("simnos.plugins.shell.cmd_shell", level="ERROR") as captured:
            shell.default("broken_attr_cmd")
        self.assertEqual(len(captured.output), 1)
        self.assertTrue(any("error formatting output" in msg and "broken_attr_cmd" in msg for msg in captured.output))
        shell.writeline.assert_called_once_with("value is {base_prompt.foo}")

    def test_default_silent_fallback_on_typeerror(self):
        """`TypeError` failure mode of `.format()` is silently logged.

        Pins #171: item access on the str argument (`{base_prompt[bad]}`)
        raises `TypeError` ("string indices must be integers"), the fifth
        and last member of `FORMAT_ERRORS`. Together the five fallback
        tests pin every member of the catch set shared with
        `tasks.render_template`.
        """
        self.arguments["is_running"].set()
        shell = CMDShell(**self.arguments)
        shell.writeline = Mock()
        shell.commands["broken_item_cmd"] = {
            "output": "value is {base_prompt[bad]}",
            "prompt": ["{base_prompt}>"],
        }
        with self.assertLogs("simnos.plugins.shell.cmd_shell", level="ERROR") as captured:
            shell.default("broken_item_cmd")
        self.assertEqual(len(captured.output), 1)
        self.assertTrue(any("error formatting output" in msg and "broken_item_cmd" in msg for msg in captured.output))
        shell.writeline.assert_called_once_with("value is {base_prompt[bad]}")

    def test_default_new_prompt_format_failure_keeps_prompt(self):
        """A broken cmd_data new_prompt does not transition the prompt.

        Pins #172: the new_prompt format used to bubble into the broad
        `except Exception`, leaking a traceback into the user output.
        Now the failure is a silent log, the session stays on the current
        prompt, and the command output is still written normally.
        """
        self.arguments["is_running"].set()
        shell = CMDShell(**self.arguments)
        shell.writeline = Mock()
        shell.commands["broken_np_cmd"] = {
            "output": "mode change attempted",
            "prompt": ["{base_prompt}>"],
            "new_prompt": "{base_prompt.foo}#",
        }
        with self.assertLogs("simnos.plugins.shell.cmd_shell", level="ERROR") as captured:
            stop = shell.default("broken_np_cmd")
        self.assertFalse(stop)
        self.assertEqual(shell.prompt, "test>")
        self.assertEqual(len(captured.output), 1)
        self.assertTrue(any("error formatting new_prompt" in msg and "broken_np_cmd" in msg for msg in captured.output))
        shell.writeline.assert_called_once_with("mode change attempted")

    def test_default_callable_dict_new_prompt_format_failure(self):
        """A broken callable-dict new_prompt does not transition the prompt.

        Pins #172 (callable dict path, symmetric to the cmd_data path
        above): format failure is a silent log + no transition, and no
        traceback reaches the wire. The callable's own exceptions are
        out of scope here — they answer with HANDLER_ERROR_OUTPUT since
        #241/D4 (see test_default_handler_crash_writes_fixed_error_line).
        """
        shell = self._make_callable_dict_shell(
            lambda device, **kwargs: {"output": "body", "new_prompt": "{base_prompt.foo}#"}
        )
        with self.assertLogs("simnos.plugins.shell.cmd_shell", level="ERROR") as captured:
            stop = shell.default("cmd")
        self.assertFalse(stop)
        self.assertEqual(shell.prompt, "test>")
        self.assertEqual(len(captured.output), 1)
        self.assertTrue(any("error formatting new_prompt" in msg and "'cmd'" in msg for msg in captured.output))
        shell.writeline.assert_called_once_with("body")

    def test_default_callable_dict_output_passed_through_unformatted(self):
        """Callable-dict output skips `_safe_format` entirely (#241 / D-b).

        New contract pin (rewritten from the pre-#241 raw-fallback pin):
        handlers format themselves, so brace-containing device output is
        written verbatim — no format attempt, hence **no error log**
        (the old chain logged a FORMAT_ERRORS failure before falling back
        to the same raw string). The skip applies to dict output exactly
        like str returns: the flag is set at invoke time, not by return
        shape.
        """
        shell = self._make_callable_dict_shell(lambda device, **kwargs: {"output": "value is {base_prompt.foo}"})
        with self.assertNoLogs("simnos.plugins.shell.cmd_shell", level="ERROR"):
            stop = shell.default("cmd")
        self.assertFalse(stop)
        shell.writeline.assert_called_once_with("value is {base_prompt.foo}")

    def test_default_callable_str_output_passed_through_unformatted(self):
        """Callable str output skips `_safe_format` too (#241 / D-b).

        The str-return twin of the dict pin above: literal braces in a
        handler's rendered output (e.g. JSON-ish device output) reach the
        wire untouched instead of tripping FORMAT_ERRORS into a logged
        raw fallback.
        """
        shell = self._make_callable_dict_shell(lambda device, **kwargs: "literal {brace} stays")
        with self.assertNoLogs("simnos.plugins.shell.cmd_shell", level="ERROR"):
            stop = shell.default("cmd")
        self.assertFalse(stop)
        shell.writeline.assert_called_once_with("literal {brace} stays")

    def test_default_broken_prompt_treated_as_non_match(self):
        """A command with a broken prompt template is just unreachable.

        Pins #172: `_check_prompt` used to leak the format error into the
        broad `except Exception` (traceback in output). Now the broken
        candidate is a logged non-match and the shell answers with the
        unknown-command output, session intact.
        """
        self.arguments["is_running"].set()
        shell = CMDShell(**self.arguments)
        shell.writeline = Mock()
        # Injected directly into shell.commands (bypassing the load
        # paths), so the list form is used per the #244 / D3 contract.
        shell.commands["broken_prompt_cmd"] = {
            "output": "should not appear",
            "prompt": ["{base_prompt.foo}>"],
        }
        with self.assertLogs("simnos.plugins.shell.cmd_shell", level="ERROR") as captured:
            shell.default("broken_prompt_cmd")
        self.assertEqual(len(captured.output), 1)
        self.assertTrue(any("error formatting prompt" in msg and "broken_prompt_cmd" in msg for msg in captured.output))
        shell.writeline.assert_called_once_with("% Invalid input detected at '^' marker.")

    def test_do_help_broken_prompt_command_hidden(self):
        """`do_help` survives a broken prompt template (command hidden).

        Pins #172: the `do_help` -> `_check_prompt` path had *no* guard at
        all — a single broken prompt yaml crashed the session on `help`.
        Now the broken command is silently omitted from the help listing.
        """
        self.arguments["is_running"].set()
        shell = CMDShell(**self.arguments)
        shell.writeline = Mock()
        # Direct injection -> list form per the #244 / D3 contract.
        shell.commands["broken_prompt_cmd"] = {
            "output": "x",
            "prompt": ["{base_prompt.foo}>"],
            "help": "never listed",
        }
        with self.assertLogs("simnos.plugins.shell.cmd_shell", level="ERROR") as captured:
            shell.do_help("")
        self.assertEqual(len(captured.output), 1)
        help_text = shell.writeline.call_args[0][0]
        self.assertNotIn("broken_prompt_cmd", help_text)
        self.assertIn("show clock", help_text)  # healthy commands still listed

    def test_default_list_prompt_partial_breakage_still_matches(self):
        """A broken candidate in a prompt list does not poison the rest.

        Pins the per-candidate independent evaluation of `_check_prompt`
        (#172 design improvement): previously one broken element raised
        out of the `any()` generator and failed the whole match; now the
        healthy element still matches and the command works.
        """
        self.arguments["is_running"].set()
        shell = CMDShell(**self.arguments)
        shell.writeline = Mock()
        shell.commands["partial_prompt_cmd"] = {
            "output": "reached",
            "prompt": ["{base_prompt.foo}>", "{base_prompt}>"],
        }
        with self.assertLogs("simnos.plugins.shell.cmd_shell", level="ERROR") as captured:
            shell.default("partial_prompt_cmd")
        self.assertEqual(len(captured.output), 1)  # the broken candidate, once
        shell.writeline.assert_called_once_with("reached")

    def test_default_command_new_prompt(self):
        """Test that the default method does nothing."""
        self.arguments["is_running"].set()
        shell = CMDShell(**self.arguments)
        shell.writeline = Mock()
        shell.default("enable")
        shell.prompt = "test#"

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
        mock_get_files_changed = Mock()
        shell = CMDShell(**self.arguments)
        shell.get_files_changed = mock_get_files_changed
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
        shell.nos.from_file = Mock(side_effect=[ValueError("boom"), None])
        shell.nos.commands = {"healthy": {"output": "ok"}}
        with self.assertLogs("simnos.plugins.shell.cmd_shell", level="ERROR") as captured:
            shell.reload_commands(["broken.yaml", "healthy.yaml"])
        self.assertEqual(len(captured.output), 1)
        self.assertIn("broken.yaml", captured.output[0])
        self.assertIn("healthy", shell.commands)

    def test_reload_commands_broken_file_last_still_applies_rest(self):
        """The per-file guard is order-independent: broken file last.

        Complements `test_reload_commands_broken_file_logs_and_continues`
        (broken first): the healthy file's commands are applied before the
        broken file raises, and the error is still logged.
        """
        shell = CMDShell(**self.arguments)
        shell.nos.from_file = Mock(side_effect=[None, ValueError("boom")])
        shell.nos.commands = {"healthy": {"output": "ok"}}
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
    @simnos(platform="cisco_ios", return_instance=True)
    def test_hot_reload_integration_yaml(self, net: SimNOS):
        """
        Test that the hot reload feature works correctly

        Both hot-reload integration tests mutate the same real
        `simnos/plugins/nos/` tree that every reload-enabled server in
        the worker process watches, so they are serialized onto one
        worker via `xdist_group` and keep their backup copies on a
        non-watched `.bak` extension (#232: a sibling worker observed
        a mid-`copyfile` empty `.yaml` and crashed its shell thread).
        """
        original_filename = "simnos/plugins/nos/platforms_yaml/cisco_ios.yaml"
        copy_filename = "simnos/plugins/nos/platforms_yaml/cisco_ios.yaml.bak"
        test_commands = {
            "test": {
                "output": "test output",
                "help": "test help",
                "prompt": ["{base_prompt}>"],
            }
        }

        def change_file():
            shutil.copyfile(original_filename, copy_filename)
            with open(original_filename, encoding="utf-8") as file:
                values = yaml.safe_load(file)
            values["commands"].update(test_commands)
            self._atomic_write(original_filename, yaml.dump(values), suffix=".yaml.bak")

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
            output = conn.send_command("test")
            assert output == "% Invalid input detected at '^' marker."
            change_file()
            try:
                output = conn.send_command("test")
                assert output == "test output"
            finally:
                undo_change_file()

    @pytest.mark.skipif(sys.platform == "win32", reason="Windows does not allow file movement on Github runners")
    @pytest.mark.xdist_group("hot-reload-fs")
    @simnos(platform="cisco_ios", return_instance=True)
    def test_hot_reload_integration_py_jinja(self, net: SimNOS):
        """
        Test that the hot reload feature works correctly

        See `test_hot_reload_integration_yaml` for why both hot-reload
        integration tests share an `xdist_group` and use `.bak` backups
        (#232 cross-worker file race).
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
