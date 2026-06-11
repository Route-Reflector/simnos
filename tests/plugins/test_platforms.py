"""
Test the platforms that are supported by SimNOS.
Currently, it checks if the platforms are correctly set
in the yaml and python files.
"""

from importlib import import_module
import os
import re
import types
from typing import Any

from netmiko import ConnectHandler
import pytest
import yaml

from simnos.core.nos import _find_device_classes
from simnos.core.platform_loader import load_platform_dir
from simnos.plugins.nos import nos_plugins
from tests._platform_quirks import SKIP_ENABLE, XFAIL_PY_ALL_COMMANDS
from tests.utils import creds_from_host, get_host_commands, get_py_platforms, netmiko_device


def get_yaml_only_platforms() -> list[str]:
    """Return platforms that have YAML definitions but no Python module."""
    py_modules = set(get_py_platforms())
    return [p for p in sorted(nos_plugins) if p not in py_modules]


def get_legacy_yaml_platforms() -> list[str]:
    """Return platforms still authored as a legacy ``platforms_yaml/<p>.yaml``.

    A3-migrated platforms (#264) have no legacy yaml — their on-disk format is
    validated by the authoring schema + loader (and the oracle/encoding lint),
    so the legacy-yaml format checks below skip them.
    """
    return sorted(p for p, sources in nos_plugins.items() if any(s.endswith(".yaml") for s in sources))


def default_output_for(platform: str) -> str:
    """Return a platform's `_default_` output text, legacy yaml or A3 form (#264).

    The legacy yaml stored it inline; the A3 form keeps it in an adjacent file
    (read via the loader). The trailing newline the A3 ``.txt`` carries is
    stripped — wire comparisons use substring / are newline-insensitive.
    """
    legacy = f"simnos/plugins/nos/platforms_yaml/{platform}.yaml"
    if os.path.isfile(legacy):
        with open(legacy, encoding="utf-8") as file:
            return yaml.safe_load(file)["commands"]["_default_"]["output"]
    default_output = load_platform_dir(f"simnos/plugins/nos/platforms/{platform}").commands["_default_"].output
    # A non-literal `_default_` (output_template / no output) would make the
    # caller's `expected in output` vacuously pass on ""; the schema allows it,
    # so fail loudly instead of silently asserting nothing (2nd round claude #8).
    if default_output.kind != "literal" or not default_output.text:
        raise AssertionError(f"{platform}: _default_ has no literal output to pin (kind={default_output.kind})")
    return default_output.text.rstrip("\n")


def has_single_curly_brackets(text: Any, exceptions: list[str]) -> bool:
    """
    It returns False if the single curly
    brackets are in the text.
    The strategy is to check if the text has
    the curly brackets and if so it checks that
    those are double, otherwise returns True.
    """
    pattern = r"\{\{[^\{\}]*\}\}"
    if not text or isinstance(text, bool) or callable(text):
        return False
    if isinstance(text, str):
        text = [text]
    for t in text:
        if "{" not in t or "}" not in t or any(e in t for e in exceptions):
            continue
        matches = re.search(pattern, t)
        if not matches:
            return True
    return False


class TestPlatforms:
    """
    This class tests all the platforms that are supported by SimNOS
    and checks if they are correctly set
    """

    @pytest.mark.parametrize("platform", get_legacy_yaml_platforms())
    def test_platforms_yaml_has_correct_format(self, platform: str):
        """
        It checks if the platform yaml file can be opened correctly using
        the yaml library.
        """
        with open(f"simnos/plugins/nos/platforms_yaml/{platform}.yaml", encoding="utf-8") as file:
            data: dict = yaml.safe_load(file)
            for key in data:
                assert key in [
                    "name",
                    "initial_prompt",
                    "enable_prompt",
                    "config_prompt",
                    "commands",
                    "auth",
                ]

    @pytest.mark.parametrize("platform", get_legacy_yaml_platforms())
    def test_platforms_yaml_commands_has_correct_format(self, platform: str):
        """
        It checks if the platform has the commands correctly set.
        At least all the commands need to have the following with any conflict:
        - output
        - help
        - prompt (except `_default_`, see below)
        """
        with open(f"simnos/plugins/nos/platforms_yaml/{platform}.yaml", encoding="utf-8") as file:
            data = yaml.safe_load(file)
            exceptions: list[str] = [data["initial_prompt"]]
            if "enable_prompt" in data:
                exceptions.append(data["enable_prompt"])
            if "config_prompt" in data:
                exceptions.append(data["config_prompt"])
            for command, values in data["commands"].items():
                assert "output" in values or "exit" in values
                if "output" in values:
                    assert not has_single_curly_brackets(values["output"], exceptions)
                assert "help" in values
                assert not has_single_curly_brackets(values["help"], exceptions)
                # `_default_` is the unknown-command fallback: the shell
                # answers with its output regardless of the current prompt
                # (mismatch path), so a `prompt` key is meaningless there —
                # BASIC_COMMANDS' own `_default_` carries none either. The
                # #244 / D6 wording entries are authored minimal (no prompt);
                # pre-#244 entries that still carry one stay valid.
                if command != "_default_":
                    assert "prompt" in values
                if "prompt" in values:
                    assert not has_single_curly_brackets(values["prompt"], exceptions)

    @pytest.mark.parametrize("platform", get_py_platforms())
    def test_platforms_py_has_correct_format(self, platform: str):
        """
        It checks if the platform python file can be imported correctly.
        """
        try:
            module = import_module(f"simnos.plugins.nos.platforms_py.{platform}")
        except ImportError:
            pytest.fail(f"Failed to import platform module for {platform}")

        assert module.__name__ == f"simnos.plugins.nos.platforms_py.{platform}"
        assert hasattr(module, "commands")
        assert hasattr(module, "INITIAL_PROMPT")
        # #241/D5 contract: exactly one locally-defined BaseDevice subclass,
        # detected by the same criterion `Nos._from_module` uses (the
        # `__module__` guard holds under package import too — both sides of
        # the comparison track the load mechanism).
        assert len(_find_device_classes(module)) == 1
        # The legacy DEVICE_NAME indirection must not creep back in.
        assert not hasattr(module, "DEVICE_NAME")

    @pytest.mark.parametrize("platform", get_py_platforms())
    def test_platforms_py_commands_has_correct_format(self, platform: str):
        """
        It checks if the platform has the commands correctly set.
        At least all the commands need to have the following with any conflict:
        - output
        - help
        - prompt
        """
        try:
            module = import_module(f"simnos.plugins.nos.platforms_py.{platform}")
        except ImportError:
            pytest.fail(f"Failed to import platform module for {platform}")

        # Same detection criterion as `Nos._from_module` (#241/D5); the
        # exactly-one contract is pinned in test_platforms_py_has_correct_format.
        module_class = _find_device_classes(module)[0]

        for value in module.commands.values():
            if "alias" in value:
                continue
            exceptions: list[str] = [module.INITIAL_PROMPT]
            if hasattr(module, "ENABLE_PROMPT"):
                exceptions.append(module.ENABLE_PROMPT)
            if hasattr(module, "CONFIG_PROMPT"):
                exceptions.append(module.CONFIG_PROMPT)
            assert "output" in value or "exit" in value
            if "output" in value:
                if callable(value["output"]):
                    assert isinstance(value["output"], types.FunctionType)
                    assert value["output"].__name__ in dir(module_class)
                else:
                    assert not has_single_curly_brackets(value["output"], exceptions)
            assert "help" in value
            assert not has_single_curly_brackets(value["help"], exceptions)
            assert "prompt" in value

    @pytest.mark.timeout(600)
    @pytest.mark.parametrize("platform", get_yaml_only_platforms())
    def test_platforms_yaml_all_commands_are_running(self, platform: str, simnos_factory):
        """
        Test that all YAML-only platform commands can
        run without any error via netmiko.
        """
        net = simnos_factory(platform)
        host = next(iter(net.hosts.values()))
        initial_commands, enable_commands, config_commands = get_host_commands(host)
        with ConnectHandler(**netmiko_device(platform, creds_from_host(host))) as conn:
            for command in initial_commands:
                output = conn.send_command(command)
                assert isinstance(output, str)
            # SKIP_ENABLE platforms cannot enter enable()/config_mode() (need a
            # secret or sudo); their initial (show) commands above still run.
            if enable_commands and platform not in SKIP_ENABLE:
                conn.enable()
                for command in enable_commands:
                    output = conn.send_command(command)
                    assert isinstance(output, str)
            if config_commands and platform not in SKIP_ENABLE:
                conn.config_mode()
                for command in config_commands:
                    output = conn.send_command(command)
                    assert isinstance(output, str)

    # Vendor-signature literal pins (#244 / D6): the wire test below reads
    # its expectation from the yaml (SSoT), so it confirms the plumbing but
    # NOT that the wording itself stays vendor-accurate — a regression that
    # also rewrites the yaml would pass it (cross-review 🦊#5). These
    # literals guard the distinctive signatures that are easy to drift back
    # to a Cisco-style copy: "command" vs "input" (NX-OS), the `%%` double
    # percent (EXOS), the `"^"` double-quoted caret (Force10), the two-line
    # IronWare block (Brocade) and the multi-line listing (D-Link flat CLI).
    # An intentional wording change updates both this map and the yaml.
    _VENDOR_SIGNATURE_DEFAULTS = {
        "cisco_nxos": "% Invalid command at '^' marker.",
        "extreme_exos": "%% Invalid input detected at '^' marker.",
        "dell_force10": '% Error: Invalid input at "^" marker.',
        "brocade_netiron": "Invalid input ->\nType ? for a list",
        "dlink_ds": (
            "Available commands:\n"
            "..                  ?                   cable_diag          clear\n"
            "config              create              delete              dir\n"
            "disable             download            drv                 enable\n"
            "login               logout              ping                reboot\n"
            "reconfig            reset               save                show\n"
            "telnet              upload"
        ),
    }

    @pytest.mark.parametrize("platform", sorted(_VENDOR_SIGNATURE_DEFAULTS))
    def test_default_wording_keeps_vendor_signature(self, platform: str):
        """The `_default_` output keeps its distinctive vendor signature (#244 / D6).

        Literal guard against drifting a vendor-specific message back to a
        generic Cisco-style one — the wire test reads from the yaml so it
        cannot catch that (cross-review 🦊#5). A deliberate wording change
        must update both this expectation and the yaml.
        """
        with open(f"simnos/plugins/nos/platforms_yaml/{platform}.yaml", encoding="utf-8") as file:
            actual = yaml.safe_load(file)["commands"]["_default_"]["output"]
        assert actual == self._VENDOR_SIGNATURE_DEFAULTS[platform]

    @pytest.mark.timeout(300)
    # cisco_ios: single Cisco-style line / juniper_junos: lowercase + trailing
    # period / brocade_netiron: two-line block / dell_force10: escaped `"^"`
    # caret (the one wire pin that exercises a backslash-escaped scalar over
    # the SSH channel, cross-review 🐙#5).
    @pytest.mark.parametrize("platform", ["cisco_ios", "juniper_junos", "brocade_netiron", "dell_force10"])
    def test_platforms_yaml_default_wording_reaches_the_wire(self, platform: str, simnos_factory):
        """The yaml-authored `_default_` answers an unknown command verbatim (#244 / D6).

        Pins the wording PR end to end over a real netmiko session, one
        platform per output shape (see the parametrize comment). The
        expected text is read from the platform yaml itself (SSoT) so the
        pin survives future wording refinements without duplicating data;
        the vendor-signature literals are guarded separately by
        test_default_wording_keeps_vendor_signature.
        """
        expected = default_output_for(platform)
        net = simnos_factory(platform)
        host = next(iter(net.hosts.values()))
        with ConnectHandler(**netmiko_device(platform, creds_from_host(host))) as conn:
            output = conn.send_command("simnos pin unknown command")
            assert expected in output

    @pytest.mark.timeout(60)
    def test_a3_raw_brace_fixture_reaches_wire_verbatim(self, simnos_factory):
        """An A3 ``.txt`` with literal braces reaches the wire unmodified (#264 AC).

        The legacy yaml had to escape braces for ``str.format`` (``{{...}}``);
        the A3 form stores the raw NTC capture verbatim and renders nothing for
        a literal output. cisco_ios ``show crypto ipsec sa detail`` carries
        ``flags={origin_is_acl,}`` — a single-brace run that must survive the
        round trip (no ``{{`` doubling, no collapsing) over a real SSH session.
        """
        net = simnos_factory("cisco_ios")
        host = next(iter(net.hosts.values()))
        with ConnectHandler(**netmiko_device("cisco_ios", creds_from_host(host))) as conn:
            output = conn.send_command("show crypto ipsec sa detail")
            assert "flags={origin_is_acl,}" in output
            assert "in use settings ={Transport UDP-Encaps, }" in output

    @pytest.mark.timeout(600)
    @pytest.mark.parametrize("platform", get_py_platforms())
    def test_platforms_py_all_commands_are_running(self, platform: str, simnos_factory):
        """
        Test that all the platforms commands can
        run without any error.
        """
        if platform in XFAIL_PY_ALL_COMMANDS:
            pytest.xfail(XFAIL_PY_ALL_COMMANDS[platform].reason)
        net = simnos_factory(platform)
        host = next(iter(net.hosts.values()))
        initial_commands, enable_commands, config_commands = get_host_commands(host)
        with ConnectHandler(**netmiko_device(platform, creds_from_host(host))) as conn:
            for command in initial_commands:
                output = conn.send_command(command)
                assert isinstance(output, str)
            if enable_commands:
                conn.enable()
                for command in enable_commands:
                    output = conn.send_command(command)
                    assert isinstance(output, str)
            if config_commands:
                conn.config_mode()
                for command in config_commands:
                    output = conn.send_command(command)
                    assert isinstance(output, str)
