"""Compatibility check: scrapli × cisco_ios."""

import pytest

pytest.importorskip("scrapli")
from scrapli.driver.core import IOSXEDriver  # ty: ignore[unresolved-import]


def _scrapli_creds(creds: dict) -> dict:
    return {
        "host": creds["host"],
        "auth_username": creds["username"],
        "auth_password": creds["password"],
        "auth_strict_key": False,
        "port": creds["port"],
        "transport": "paramiko",
    }


@pytest.mark.compatibility
def test_scrapli_connect_and_show_version(cisco_ios_simnos):
    creds = cisco_ios_simnos
    with IOSXEDriver(**_scrapli_creds(creds)) as conn:
        resp = conn.send_command("show version")
        assert not resp.failed
        assert "Cisco IOS" in resp.result


@pytest.mark.compatibility
def test_scrapli_show_running_config(cisco_ios_simnos):
    creds = cisco_ios_simnos
    with IOSXEDriver(**_scrapli_creds(creds)) as conn:
        resp = conn.send_command("show running-config")
        assert not resp.failed
        assert "hostname" in resp.result
