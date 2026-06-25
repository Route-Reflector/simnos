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
import threading
import time
import unittest
from unittest.mock import MagicMock

import pytest

from simnos import SimNOS
from simnos.core.pydantic_models import ModelSimnosInventory
from simnos.core.shared_loop import LoopState
from simnos.plugins.servers import servers_plugins
from simnos.plugins.servers.telnet_server import TelnetServer, _is_loopback
from tests.plugins.telnet_test_helpers import open_and_login, telnet_login_run
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


def test_telnet_auth_failure_raw_surplus_delivers_message_and_fin():
    """Wrong credentials: the failure message reaches the client and the close is a
    graceful FIN, not an RST (Stage 3 先行検証 — asyncio keeps the kernel receive
    buffer empty so there is no unread-data RST, replacing the raw-socket
    ``_drain_pending_input`` mechanism, #268).

    The #268 RST happens when the server closes a socket that still has *unread*
    bytes in its kernel receive buffer, so the regression must put surplus data
    there: after the wrong credentials the client sends a burst it never lets the
    server consume cooperatively. The close must still be a FIN that delivers
    ``Authentication failed.`` — which holds because asyncio's StreamReader has
    already pulled those bytes off the kernel socket (codex 1st#1)."""
    surplus = b"x" * 16384  # unread bytes left in the server's receive path at close
    with _running_telnet_host() as port:
        sock = socket.create_connection(("127.0.0.1", port), timeout=8)
        sock.settimeout(8)
        try:
            # Wrong username + wrong password, then a surplus burst. telnetlib3
            # buffers all of it (the client does not answer negotiation);
            # async_interactive_login reads the credentials, fails, and the server
            # closes while the surplus is still in flight / buffered.
            sock.sendall(b"wrong\r\nwrong\r\n" + surplus)
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
    assert eof  # (2) graceful FIN, not RST, despite surplus unread input


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


def test_telnet_stop_drains_active_session():
    """Stopping a Telnet host with a live, mid-session client tears the session down
    and converges to STOPPED — the telnet-transport-specific active-session drain
    (claude 1st#4). ``aclose`` closes the telnetlib3 writer, which feeds EOF to the
    session's reader so ``run_async_push_session`` returns; the client observes the
    same EOF. SSH lifecycle tests cover the shared base path, but the telnetlib3
    close→reader-EOF coupling is pinned here so a telnetlib3 close-semantics change
    cannot regress it silently."""
    logged_in = threading.Event()
    release = threading.Event()
    saw_eof = threading.Event()

    inventory = build_inventory("cisco_ios", server=_TELNET_SERVER)
    port = inventory["hosts"]["device"]["port"]
    net = SimNOS(inventory=inventory)
    net.start()

    def _client():
        async def _run():
            reader, writer = await open_and_login(port)
            try:
                logged_in.set()
                # Stay connected until the server closes us (EOF) or the test releases.
                while not release.is_set():
                    try:
                        chunk = await asyncio.wait_for(reader.read(1024), timeout=0.2)
                    except TimeoutError:
                        continue
                    if not chunk:
                        saw_eof.set()  # server closed the session (aclose)
                        break
            finally:
                writer.close()

        asyncio.new_event_loop().run_until_complete(_run())

    client = threading.Thread(target=_client, daemon=True)
    client.start()
    try:
        assert logged_in.wait(timeout=10), "telnet client did not log in"
        assert net._shared_loop.refcount == 1
        net.stop()  # aclose closes the active session -> client reader hits EOF
        assert net._shared_loop.state is LoopState.STOPPED
        assert saw_eof.wait(timeout=10), "active telnet session was not closed by stop()"
    finally:
        release.set()
        client.join(timeout=5)
        if net._shared_loop.state is not LoopState.STOPPED:
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
