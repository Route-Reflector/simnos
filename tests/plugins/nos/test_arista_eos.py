"""
Device-class unit tests for the arista_eos Python plugin (T-14 / #230).

Producer-side pins for the remaining dynamic handler (`make_show_clock`). The
formerly callable statics (`show version` / `show running-config` /
`show ip int brief`) and the dict-returning `make_exit` migrated to A3 static
data (#317 P-2): content pins moved onto the A3 render below (the migration's
byte-level parity fixtures retired with the legacy inflow, #317 P-4).
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
    return Nos(filename=nos_plugins["arista_eos"])


@pytest.fixture(scope="module")
def platform():
    return load_platform_dir(os.path.join(PLATFORMS_DIR, "arista_eos"))


def test_show_clock_format(nos):
    """Time-dependent output (e2e denylist): pin time-line shape + static tail.

    The first line renders time.strftime("%a %b %d %H:%M:%S %Y"), e.g.
    'Sat Apr 16 11:54:03 2022' (same shape as tests/core/test_netmiko.py
    pins for the test-asset show clock).
    """
    out = call_handler(nos, "make_show_clock", "show clock", "enable")
    assert re.match(r"^\w{3} \w{3} \d{2} \d{2}:\d{2}:\d{2} \d{4}$", out.splitlines()[0])
    assert "Timezone: UTC" in out
    assert "Clock source: local" in out


def test_show_version_content(platform):
    out = platform.commands["show version"].output.render(BASE_PROMPT)
    assert "cEOSLab" in out


def test_show_running_config_content(platform):
    out = platform.commands["show running-config"].output.render(BASE_PROMPT)
    assert f"hostname {BASE_PROMPT}" in out  # {{base_prompt}} resolved
    assert "{" not in out


@pytest.mark.parametrize("command", ["show ip int brief", "show ip interface brief"])
def test_show_ip_int_brief_content(platform, command):
    """Both spellings stay distinct real commands with identical output (#317 P-2)."""
    out = platform.commands[command].output.render(BASE_PROMPT)
    assert "Interface" in out
    assert "Ethernet1" in out
    assert "{" not in out


def test_show_ip_int_brief_txt_pair_stays_byte_identical():
    """The two int-brief spellings' `.txt` files are byte-for-byte identical.

    Both are REAL commands (alias-izing one would change the #303 P3-2
    canonical-only abbreviation space) and the lint's 1-yaml:1-output rule
    forbids sharing one output file, so the duplicated captures carry a
    cross-sync comment in both yamls. This is the permanent identity gate the
    retired P-2 migration fixtures used to provide (#317 P-4) — an edit to one
    file without the other fails here.
    """
    commands_dir = os.path.join(PLATFORMS_DIR, "arista_eos", "commands")
    with open(os.path.join(commands_dir, "show_ip_int_brief.txt"), "rb") as short_file:
        short = short_file.read()
    with open(os.path.join(commands_dir, "show_ip_interface_brief.txt"), "rb") as long_file:
        assert short == long_file.read()
