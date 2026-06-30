"""End-to-end pin for the user overlay (#286 / P1-2a — custom data layering).

Drives a real netmiko session against a SimNOS host whose inventory opts into
the overlay (`overlay.override_commands`) with output files under
`sys_config.data_dir/<registry-key>/`. Pins the full carrier path
(Host -> server -> build_shared_platform -> shell) the unit tests cannot reach:
the captured `.txt` must replace the packaged output over the wire, and the map
form must let a host choose a specific capture file (the R11 case).
"""

from typing import cast

from netmiko import ConnectHandler
import pytest

from simnos import SimNOS
from simnos.core.pydantic_models import EPHEMERAL_PORT
from tests.utils import TEST_PASSWORD, TEST_USERNAME, creds_from_host, netmiko_device

OVERLAY_MARKER = "OVERLAY-CAPTURE-cisco-ios-9999"


@pytest.fixture
def _overlay_data_dir(tmp_path):
    """A data_dir with a cisco_ios overlay output file; returns (data_dir, filename)."""
    platform_dir = tmp_path / "cisco_ios"
    platform_dir.mkdir(parents=True)
    (platform_dir / "show_version_custom.txt").write_text(f"Cisco IOS Software [{OVERLAY_MARKER}]\n", encoding="utf-8")
    return str(tmp_path), "show_version_custom.txt"


def _show_version_over_wire(data_dir: str, *, overlay: dict | None = None) -> str:
    """Start a cisco_ios host (optionally opted into `overlay`) and return its
    `show version` output over a real netmiko session, stopping the server after.
    """
    host_cfg = {
        "username": TEST_USERNAME,
        "password": TEST_PASSWORD,
        "port": EPHEMERAL_PORT,
        "device_type": "cisco_ios",
    }
    if overlay is not None:
        host_cfg["overlay"] = overlay
    net = SimNOS(inventory={"hosts": {"device": host_cfg}}, sys_config={"data_dir": data_dir})
    net.start()
    try:
        host = net.hosts["device"]
        device = netmiko_device("cisco_ios", creds_from_host(host))
        with ConnectHandler(**device) as conn:
            # send_command's default (no textfsm/genie) returns str; the stub's
            # union covers the parse modes this test does not use.
            return cast(str, conn.send_command("show version"))
    finally:
        net.stop()


@pytest.mark.timeout(60)
def test_overlay_map_replaces_output_over_wire(_overlay_data_dir):
    """A host pulling a mapped capture file serves it instead of the packaged output."""
    data_dir, filename = _overlay_data_dir
    output = _show_version_over_wire(data_dir, overlay={"override_commands": {"show version": filename}})
    assert OVERLAY_MARKER in output


@pytest.mark.timeout(60)
def test_no_overlay_serves_packaged_output(_overlay_data_dir):
    """A host that does not opt in keeps the packaged output (the overlay marker is absent)."""
    data_dir, _filename = _overlay_data_dir
    output = _show_version_over_wire(data_dir)
    assert OVERLAY_MARKER not in output
