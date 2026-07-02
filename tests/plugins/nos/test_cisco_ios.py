"""
Device-class unit tests for the cisco_ios Python plugin (T-14 / #230).

Producer-side pins for the remaining dynamic handler (`make_show_clock`,
invoked with the same contract as `CMDShell._invoke_handler`). The formerly
callable statics (`show version` / `show running-config`) migrated to A3
`output_template` files (#317 P-2); their content pins moved onto the A3
render (byte parity vs the old handlers is pinned separately in
tests/plugins/test_p2_migration_parity.py).
"""

import os
import re

import pytest

from a3_paths import PLATFORMS_DIR
from simnos.core.nos import Nos
from simnos.core.platform_loader import load_platform_dir
from simnos.plugins.nos import nos_plugins
from tests.plugins.nos.device_helpers import BASE_PROMPT, call_handler


@pytest.fixture(scope="module")
def nos() -> Nos:
    """Merged Nos via the same wiring the server uses (Host.start equivalent)."""
    return Nos(filename=nos_plugins["cisco_ios"])


@pytest.fixture(scope="module")
def platform():
    return load_platform_dir(os.path.join(PLATFORMS_DIR, "cisco_ios"))


def test_show_clock_format(nos):
    """Time-dependent output (e2e denylist): pin the strftime shape.

    Example: '*11:54:03.000 UTC Sat Apr 16 2022'.
    """
    out = call_handler(nos, "make_show_clock", "show clock", "enable")
    assert re.match(r"^\*\d{2}:\d{2}:\d{2}\.000 .+ \d{4}$", out)


def test_show_version_content(platform):
    out = platform.commands["show version"].output.render(BASE_PROMPT)
    assert "Cisco IOS XE Software" in out
    assert f"{BASE_PROMPT} uptime is" in out  # {{base_prompt}} resolved
    assert "{" not in out  # no unresolved placeholder survives rendering


def test_show_running_config_content(platform):
    out = platform.commands["show running-config"].output.render(BASE_PROMPT)
    assert f"hostname {BASE_PROMPT}" in out
    assert "{" not in out
