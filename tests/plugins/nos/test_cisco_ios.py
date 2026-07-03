"""
Device-class unit tests for the cisco_ios Python plugin (T-14 / #230).

Producer-side pins for the remaining dynamic handler (`make_show_clock`,
invoked with the same contract as `CMDShell._invoke_handler`). The formerly
callable statics (`show version` / `show running-config`) migrated to A3
`output_template` files (#317 P-2); their content pins moved onto the A3
render (the migration's byte-level parity fixtures retired with the
legacy inflow, #317 P-4).
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
    # #328: the two long lines real IOS-XE emits as one must stay unbroken — no
    # `\` line-continuation artifact (NTC raw carries zero). Assert each line is
    # whole, not just that `\` is absent.
    assert "\\" not in out
    assert "Cisco IOS Software [Amsterdam], Virtual XE Software (X86_64_LINUX_IOSD-UNIVERSALK9-M)" in out
    assert "cisco CSR1000V (VXE) processor (revision VXE) with 715705K/3075K bytes of memory." in out


def test_show_running_config_content(platform):
    out = platform.commands["show running-config"].output.render(BASE_PROMPT)
    assert f"hostname {BASE_PROMPT}" in out
    assert "{" not in out
