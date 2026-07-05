"""
Test the platforms that are supported by SimNOS.
Currently, it checks if the platforms are correctly set
in the yaml and python files.
"""

from importlib import import_module
import os
import re
from typing import Any

from netmiko import ConnectHandler
import pytest

from a3_paths import PLATFORMS_DIR
from simnos.core.nos import Nos, _find_device_classes
from simnos.core.platform_loader import load_platform_dir
from simnos.plugins.nos import nos_plugins
from tests._platform_quirks import SKIP_ENABLE, XFAIL_PY_ALL_COMMANDS
from tests.utils import creds_from_host, get_host_commands, get_py_platforms, netmiko_device


def get_non_py_platforms() -> list[str]:
    """Return platforms with A3 static data but no Python module (sorted).

    Their netmiko command sweep is driven entirely by the A3 statics (#264); the
    py-backed platforms are swept by ``test_platforms_py_all_commands_are_running``.
    """
    py_modules = set(get_py_platforms())
    return [p for p in sorted(nos_plugins) if p not in py_modules]


def default_output_for(platform: str) -> str:
    """Return a platform's A3 `_default_` literal output text (#264).

    The A3 form keeps it in an adjacent file, read via the loader. The trailing
    newline the ``.txt`` carries is stripped — wire comparisons use substring /
    are newline-insensitive.
    """
    default_output = load_platform_dir(os.path.join(PLATFORMS_DIR, platform)).commands["_default_"].output
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

    @pytest.mark.parametrize("platform", get_py_platforms())
    def test_platforms_py_has_correct_format(self, platform: str):
        """The shipped py module is handler-only (#317 P-2): device class, no authoring.

        Command authoring (the `commands` dict + `NAME` / `*_PROMPT` scalars)
        moved to the A3 platform dir; a py module that re-grows them would
        silently shadow the A3 data again (the #320 bug class), so their
        absence is pinned here.
        """
        try:
            module = import_module(f"simnos.plugins.nos.platforms_py.{platform}")
        except ImportError:
            pytest.fail(f"Failed to import platform module for {platform}")

        assert module.__name__ == f"simnos.plugins.nos.platforms_py.{platform}"
        for authoring_attr in ("commands", "NAME", "INITIAL_PROMPT", "ENABLE_PROMPT", "CONFIG_PROMPT"):
            assert not hasattr(module, authoring_attr), (
                f"{platform}: py module defines {authoring_attr!r}; authoring belongs in the A3 dir (#317 P-2)"
            )
        # #241/D5 contract: exactly one locally-defined BaseDevice subclass,
        # detected by the same criterion `Nos._from_module` uses (the
        # `__module__` guard holds under package import too — both sides of
        # the comparison track the load mechanism).
        assert len(_find_device_classes(module)) == 1
        # The legacy DEVICE_NAME indirection must not creep back in.
        assert not hasattr(module, "DEVICE_NAME")

    @pytest.mark.parametrize("platform", get_py_platforms())
    def test_platforms_py_handlers_are_referenced(self, platform: str):
        """Every A3 `handler:` ref resolves and every shipped handler is used.

        The forward direction re-pins the merge-time bind (`_bind_handler_refs`
        is loud on a miss); the reverse direction catches a dead handler left
        behind on the device class after its command was dropped or renamed
        (#317 P-2).
        """
        nos = Nos(filename=nos_plugins[platform])
        resolved = nos.resolved_platform  # the A3 dir, loaded by the same registry wiring
        assert resolved is not None
        refs = {
            rc.output.handler_ref
            for rc in resolved.commands.values()
            if rc.output.kind == "handler" and rc.output.handler_ref
        }
        assert refs <= set(nos.handlers), f"{platform}: unresolved handler ref(s) {sorted(refs - set(nos.handlers))}"
        unused = set(nos.handlers) - refs
        assert not unused, f"{platform}: handler(s) {sorted(unused)} are referenced by no A3 command"

    @pytest.mark.timeout(600)
    @pytest.mark.parametrize("platform", get_non_py_platforms())
    def test_platform_static_commands_are_running(self, platform: str, simnos_factory):
        """
        Test that all A3 static commands of a py-less platform can
        run without any error via netmiko (#264).
        """
        net = simnos_factory(platform)
        host = next(iter(net.hosts.values()))
        initial_commands, enable_commands, config_commands = get_host_commands(host)
        with ConnectHandler(**netmiko_device(platform, creds_from_host(host))) as conn:
            for command in initial_commands:
                output = conn.send_command(command)
                assert isinstance(output, str)
            # `SKIP_ENABLE` is a (currently empty) registry hook for platforms
            # whose enable()/config_mode() cannot be exercised. Since #338 (the
            # challenge mechanism) every enable-secret / sudo platform models its
            # sub-prompt as A3 `challenge:` data that netmiko's enable() drives,
            # so the guard passes every platform through today; it is kept so a
            # future genuinely-unreachable platform can opt out again.
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
    # its expectation from the A3 data (SSoT), so it confirms the plumbing but
    # NOT that the wording itself stays vendor-accurate — a regression that
    # also rewrites the output file would pass it (cross-review 🦊#5). These
    # literals guard the distinctive signatures that are easy to drift back
    # to a Cisco-style copy: "command" vs "input" (NX-OS), the `%%` double
    # percent (EXOS), the `"^"` double-quoted caret (Force10), the two-line
    # IronWare block (Brocade) and the multi-line listing (D-Link flat CLI).
    # An intentional wording change updates both this map and the A3 output file.
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
        generic Cisco-style one — the wire test reads from the A3 data so it
        cannot catch that (cross-review 🦊#5). A deliberate wording change
        must update both this expectation and the A3 ``_default_`` output file.
        """
        assert default_output_for(platform) == self._VENDOR_SIGNATURE_DEFAULTS[platform]

    @pytest.mark.timeout(300)
    # cisco_ios: single Cisco-style line / juniper_junos: lowercase + trailing
    # period / brocade_netiron: two-line block / dell_force10: escaped `"^"`
    # caret (the one wire pin that exercises a backslash-escaped scalar over
    # the SSH channel, cross-review 🐙#5).
    @pytest.mark.parametrize("platform", ["cisco_ios", "juniper_junos", "brocade_netiron", "dell_force10"])
    def test_platform_default_wording_reaches_the_wire(self, platform: str, simnos_factory):
        """The A3 `_default_` answers an unknown command verbatim (#244 / D6, #264).

        Pins the wording end to end over a real netmiko session, one platform
        per output shape (see the parametrize comment). The expected text is
        read from the A3 ``_default_`` output file (SSoT) so the pin survives
        future wording refinements without duplicating data; the vendor-signature
        literals are guarded separately by test_default_wording_keeps_vendor_signature.
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
