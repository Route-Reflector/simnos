"""Compatibility check: netmiko × cisco_ios."""

import pytest

pytest.importorskip("netmiko")
from netmiko import ConnectHandler


@pytest.mark.compatibility
def test_netmiko_connect_and_show_version(cisco_ios_simnos):
    creds = cisco_ios_simnos
    device = {**creds, "device_type": "cisco_ios"}
    with ConnectHandler(**device) as conn:
        conn.enable()
        out = conn.send_command("show version")
        assert "Cisco IOS" in out


@pytest.mark.compatibility
def test_netmiko_config_mode_round_trip(cisco_ios_simnos):
    creds = cisco_ios_simnos
    device = {**creds, "device_type": "cisco_ios"}
    with ConnectHandler(**device) as conn:
        conn.enable()
        conn.config_mode()
        assert conn.check_config_mode()
        conn.exit_config_mode()
        assert not conn.check_config_mode()
