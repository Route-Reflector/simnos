"""Tests for the telnetlib3-backed Telnet server plugin (#297 Stage 3).

The raw-socket IAC / tap-thread unit tests were retired with the raw-socket
implementation; the Telnet wire is now pinned by ``test_telnet_byte_parity.py``
(application-layer transcript) and the shared push driver by the SSH goldens.
What remains here is Telnet-specific behaviour: plugin/inventory wiring, the
plaintext security warning, an end-to-end login + command over a real telnetlib3
client, and the auth-failure close path (message delivered + graceful FIN).
"""

import asyncio
from contextlib import contextmanager
import socket
import time
import unittest
from unittest.mock import MagicMock

import pytest

from simnos import SimNOS
from simnos.core.pydantic_models import ModelSimnosInventory
from simnos.plugins.servers import servers_plugins
from simnos.plugins.servers.telnet_server import TelnetServer, _is_loopback
from tests.plugins.telnet_test_helpers import telnet_login_run
from tests.utils import TEST_PASSWORD, TEST_USERNAME, build_inventory

_TELNET_SERVER = {"plugin": "TelnetServer", "configuration": {}}


def _make_server(**kwargs) -> TelnetServer:
    """Construct a TelnetServer with test defaults (construction only, no start)."""
    defaults: dict = {
        "shell": MagicMock,
        "nos": MagicMock(),
        "nos_inventory_config": {},
        "port": 0,
        "username": "admin",
        "password": "admin",
        "address": "127.0.0.1",
    }
    defaults.update(kwargs)
    return TelnetServer(**defaults)


@contextmanager
def _running_telnet_host(device_type: str = "cisco_ios"):
    """Start a single Telnet SimNOS host and yield its port; auto-stop."""
    inventory = build_inventory(device_type, server=_TELNET_SERVER)
    net = SimNOS(inventory=inventory)
    net.start()
    try:
        yield inventory["hosts"]["device"]["port"]
    finally:
        net.stop()


class PluginRegistrationTest(unittest.TestCase):
    """TelnetServer is registered in the plugin dict."""

    def test_telnet_server_in_plugins_dict(self):
        self.assertIn("TelnetServer", servers_plugins)
        self.assertIs(servers_plugins["TelnetServer"], TelnetServer)


class InventoryValidationTest(unittest.TestCase):
    """Pydantic inventory validation with TelnetServer."""

    def test_inventory_telnet_server_validates(self):
        data: dict = {
            "hosts": {
                "router1": {
                    "username": "admin",
                    "password": "admin",
                    "port": 6023,
                    "device_type": "cisco_ios",
                    "server": {"plugin": "TelnetServer", "configuration": {"banner": "Welcome", "timeout": 1}},
                }
            }
        }
        inventory = ModelSimnosInventory(**data)
        server = inventory.hosts["router1"].server
        assert server is not None
        self.assertEqual(server.plugin, "TelnetServer")

    def test_inventory_ssh_server_still_validates(self):
        data: dict = {
            "hosts": {
                "switch1": {
                    "username": "admin",
                    "password": "admin",
                    "port": 6022,
                    "device_type": "cisco_ios",
                    "server": {"plugin": "ParamikoSshServer", "configuration": {"ssh_banner": "SSH", "timeout": 1}},
                }
            }
        }
        inventory = ModelSimnosInventory(**data)
        server = inventory.hosts["switch1"].server
        assert server is not None
        self.assertEqual(server.plugin, "ParamikoSshServer")


class SecurityWarningTest(unittest.TestCase):
    """Non-local bind emits the plaintext warning; loopback does not."""

    def test_non_local_address_warns(self):
        with self.assertLogs("simnos.plugins.servers.telnet_server", level="WARNING") as cm:
            _make_server(address="192.168.1.1")
        self.assertTrue(any("plaintext" in msg for msg in cm.output), f"got: {cm.output}")

    def test_loopback_address_no_warning(self):
        with (
            self.assertRaises(AssertionError),
            self.assertLogs("simnos.plugins.servers.telnet_server", level="WARNING"),
        ):
            _make_server(address="127.0.0.1")


class IsLoopbackTest(unittest.TestCase):
    """The _is_loopback helper."""

    def test_loopback_127_0_0_1(self):
        self.assertTrue(_is_loopback("127.0.0.1"))

    def test_loopback_127_0_0_2(self):
        self.assertTrue(_is_loopback("127.0.0.2"))

    def test_non_loopback(self):
        self.assertFalse(_is_loopback("192.168.1.1"))

    def test_loopback_localhost(self):
        self.assertTrue(_is_loopback("localhost"))


def test_managed_threads_empty():
    """The async Telnet server registers no SimNOS-managed threads (on the loop)."""
    assert _make_server().managed_threads == []


def test_telnet_login_and_command():
    """End-to-end: a telnetlib3 client logs in and runs a command (#297 Stage 3)."""
    with _running_telnet_host() as port:
        out = asyncio.run(telnet_login_run(port, b"show vlan\r", marker=b"device>"))
    assert b"VLAN Name" in out
    assert out.rstrip(b" ").endswith(b"device>")


def test_telnet_auth_failure_delivers_message_and_fin():
    """Wrong credentials: the failure message reaches the client and the close is a
    graceful FIN, not an RST (Stage 3 先行検証 — asyncio keeps the kernel receive
    buffer empty so there is no unread-data RST, replacing the raw-socket
    ``_drain_pending_input`` mechanism, #268)."""
    with _running_telnet_host() as port:
        sock = socket.create_connection(("127.0.0.1", port), timeout=8)
        sock.settimeout(8)
        try:
            # Wrong username + wrong password. telnetlib3 buffers these until the
            # shell runs (the client does not answer negotiation); async_interactive
            # _login then reads them, fails, and the server closes.
            sock.sendall(b"wrong\r\nwrong\r\n")
            buf = b""
            eof = False
            deadline = time.monotonic() + 6.0
            while time.monotonic() < deadline:
                try:
                    chunk = sock.recv(4096)
                except TimeoutError:
                    continue
                except ConnectionResetError:
                    break  # RST (pre-async this could happen); eof stays False
                if not chunk:
                    eof = True
                    break
                buf += chunk
        finally:
            sock.close()
    assert b"Authentication failed" in buf  # (1) message delivered
    assert eof  # (2) graceful FIN, not RST


@pytest.mark.parametrize("device_type", ["cisco_ios"])
def test_telnet_serves_after_restart(device_type):
    """A Telnet host survives stop→start on the shared loop (no EADDRINUSE)."""
    inventory = build_inventory(device_type, server=_TELNET_SERVER)
    port = inventory["hosts"]["device"]["port"]
    net = SimNOS(inventory=inventory)
    net.start()
    net.stop()
    net.start()
    try:
        out = asyncio.run(telnet_login_run(port, b"show vlan\r", marker=b"device>"))
        assert b"VLAN Name" in out
    finally:
        net.stop()


@pytest.mark.timeout(120)
def test_netmiko_telnet_cisco_ios_compat():
    """Stage 3 compat(telnet 経路) gate: a real netmiko ``cisco_ios_telnet`` client
    negotiates IAC, logs in via the Username/Password prompts, enters enable, and
    runs commands against the telnetlib3 server (#297 §4/§5)."""
    connect_handler = pytest.importorskip("netmiko").ConnectHandler
    with _running_telnet_host("cisco_ios") as port:
        conn = connect_handler(
            device_type="cisco_ios_telnet",
            host="127.0.0.1",
            port=port,
            username=TEST_USERNAME,
            password=TEST_PASSWORD,
            fast_cli=False,
        )
        try:
            assert conn.find_prompt() == "device>"
            assert "VLAN Name" in conn.send_command("show vlan")
            conn.enable()
            assert conn.send_command("show version")  # non-empty in enable mode
        finally:
            conn.disconnect()
