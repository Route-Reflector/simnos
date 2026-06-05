"""
Device-class unit tests for the arista_eos Python plugin (T-14 / #230).

Producer-side pins for the callable outputs: str-returning make_* are
pinned on meaningful invariants (key substrings + `{{base_prompt}}`
resolution), and the dict-returning mode callable (`make_exit`) is
pinned per current_prompt branch — the consumer side of those dicts is
pinned separately in tests/plugins/test_cmd_shell.py.
"""

import re

import pytest

from simnos.core.nos import Nos
from simnos.plugins.nos import nos_plugins
from simnos.plugins.nos.platforms_py.arista_eos import (
    CONFIG_PROMPT,
    ENABLE_PROMPT,
    INITIAL_PROMPT,
)
from tests.plugins.nos.device_helpers import BASE_PROMPT, call_command

INITIAL = INITIAL_PROMPT.format(base_prompt=BASE_PROMPT)
ENABLE = ENABLE_PROMPT.format(base_prompt=BASE_PROMPT)
CONFIG = CONFIG_PROMPT.format(base_prompt=BASE_PROMPT)


@pytest.fixture(scope="module")
def nos() -> Nos:
    """Merged Nos via the same wiring the server uses (Host.start equivalent)."""
    return Nos(filename=nos_plugins["arista_eos"])


def test_show_clock_format(nos):
    """Time-dependent output (e2e denylist): pin time-line shape + static tail.

    The first line renders time.strftime("%a %b %d %H:%M:%S %Y"), e.g.
    'Sat Apr 16 11:54:03 2022' (same shape as tests/core/test_netmiko.py
    pins for the test-asset show clock).
    """
    out = call_command(nos, "show clock", ENABLE)
    assert re.match(r"^\w{3} \w{3} \d{2} \d{2}:\d{2}:\d{2} \d{4}$", out.splitlines()[0])
    assert "Timezone: UTC" in out
    assert "Clock source: local" in out


def test_show_version_content(nos):
    out = call_command(nos, "show version", ENABLE)
    assert "cEOSLab" in out
    assert "{" not in out


def test_show_running_config_content(nos):
    out = call_command(nos, "show running-config", ENABLE)
    assert f"hostname {BASE_PROMPT}" in out  # {{base_prompt}} resolved
    assert "{" not in out


@pytest.mark.parametrize("command", ["show ip int brief", "show ip interface brief"])
def test_show_ip_int_brief_content(nos, command):
    """Both spellings are distinct entries backed by the same make_show_ip_int_br."""
    out = call_command(nos, command, ENABLE)
    assert "Interface" in out
    assert "Ethernet1" in out
    assert "{" not in out


class TestMakeExit:
    """Pin the per-prompt branches of the dict-returning `make_exit`."""

    def test_initial_prompt_exits(self, nos):
        assert call_command(nos, "exit", INITIAL) == {"exit": True}

    def test_enable_prompt_exits(self, nos):
        assert call_command(nos, "exit", ENABLE) == {"exit": True}

    def test_config_prompt_drops_to_enable(self, nos):
        assert call_command(nos, "exit", CONFIG) == {"output": "", "new_prompt": ENABLE_PROMPT}

    def test_unknown_prompt_raises(self, nos):
        with pytest.raises(RuntimeError, match=r"make_exit does not know how to handle 'bogus\$' prompt"):
            call_command(nos, "exit", "bogus$")
