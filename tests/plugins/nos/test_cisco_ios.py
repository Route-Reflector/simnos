"""
Device-class unit tests for the cisco_ios Python plugin (T-14 / #230).

Producer-side pins for the callable outputs: each callable is invoked
with the same 4-arg contract as `cmd_shell.default` (device,
base_prompt=, current_prompt=, command=). Full render comparison would
be a tautology against the Jinja2 template, so these tests pin
meaningful invariants instead: key substrings, `{{base_prompt}}`
resolution, and (for time-dependent outputs) the format shape.
"""

import re

import pytest

from simnos.core.nos import Nos
from simnos.plugins.nos import nos_plugins
from simnos.plugins.nos.platforms_py.cisco_ios import ENABLE_PROMPT
from tests.plugins.nos.device_helpers import BASE_PROMPT, call_command

ENABLE = ENABLE_PROMPT.format(base_prompt=BASE_PROMPT)


@pytest.fixture(scope="module")
def nos() -> Nos:
    """Merged Nos via the same wiring the server uses (Host.start equivalent)."""
    return Nos(filename=nos_plugins["cisco_ios"])


def test_show_clock_format(nos):
    """Time-dependent output (e2e denylist): pin the strftime shape.

    Example: '*11:54:03.000 UTC Sat Apr 16 2022'.
    """
    out = call_command(nos, "show clock", ENABLE)
    assert re.match(r"^\*\d{2}:\d{2}:\d{2}\.000 .+ \d{4}$", out)


def test_show_version_content(nos):
    out = call_command(nos, "show version", ENABLE)
    assert "Cisco IOS XE Software" in out
    assert f"{BASE_PROMPT} uptime is" in out  # {{base_prompt}} resolved
    assert "{" not in out  # no unresolved placeholder survives rendering


def test_show_running_config_content(nos):
    out = call_command(nos, "show running-config", ENABLE)
    assert f"hostname {BASE_PROMPT}" in out
    assert "{" not in out
