"""
Test cases for the telnet_server plugin.
"""

import contextlib
import socket
import threading
import time
import unittest
from unittest import mock
from unittest.mock import MagicMock

from simnos.core.pydantic_models import ModelSimnosInventory
from simnos.core.timeouts import SHUTDOWN_IO_TIMEOUT
from simnos.plugins.servers import servers_plugins
from simnos.plugins.servers.tap_bridge import client_to_shell_tap, read_line, shell_to_client_tap
from simnos.plugins.servers.telnet_server import (
    _IAC_DRAIN_TIMEOUT,
    DO,
    DONT,
    ECHO,
    IAC,
    NAWS,
    SB,
    SE,
    SGA,
    WILL,
    WONT,
    TelnetServer,
    TelnetSocketAdapter,
    _is_loopback,
)
from tests.plugins.tap_test_helpers import countdown_run_srv, live_run_srv


def _make_server(**kwargs) -> TelnetServer:
    """Create a TelnetServer instance with sensible defaults for testing."""
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


class RecvByteTest(unittest.TestCase):
    """Test cases for TelnetServer._recv_byte()."""

    def setUp(self):
        self.server = _make_server()
        self.sock = MagicMock(spec=socket.socket)

    def test_recv_byte_normal_data(self):
        """Normal bytes are returned as-is."""
        self.sock.recv.return_value = b"A"
        result = self.server._recv_byte(self.sock)
        self.assertEqual(result, b"A")

    def test_recv_byte_iac_iac_escape(self):
        """IAC IAC is returned as literal 0xFF."""
        self.sock.recv.side_effect = [bytes([IAC]), bytes([IAC])]
        result = self.server._recv_byte(self.sock)
        self.assertEqual(result, b"\xff")

    def test_recv_byte_filters_will_wont_do_dont(self):
        """3-byte IAC negotiation commands are filtered; next data byte is returned."""
        # IAC WILL SGA → filtered, then normal byte 'X'
        self.sock.recv.side_effect = [
            bytes([IAC]),
            bytes([WILL]),
            bytes([SGA]),
            b"X",
        ]
        result = self.server._recv_byte(self.sock)
        self.assertEqual(result, b"X")

    def test_recv_byte_filters_subnegotiation(self):
        """SB...SE subnegotiation is skipped; next data byte is returned."""
        # IAC SB NAWS <4 bytes data> IAC SE → filtered, then 'Y'
        self.sock.recv.side_effect = [
            bytes([IAC]),
            bytes([SB]),
            # _skip_subnegotiation reads until IAC SE
            bytes([NAWS]),
            b"\x00",
            b"\x50",
            b"\x00",
            b"\x18",
            bytes([IAC]),
            bytes([SE]),
            b"Y",
        ]
        result = self.server._recv_byte(self.sock)
        self.assertEqual(result, b"Y")

    def test_recv_byte_connection_closed(self):
        """Empty bytes (EOF) returns None."""
        self.sock.recv.return_value = b""
        result = self.server._recv_byte(self.sock)
        self.assertIsNone(result)


class SkipSubnegotiationTest(unittest.TestCase):
    """Test cases for TelnetServer._skip_subnegotiation()."""

    def setUp(self):
        self.server = _make_server()
        self.sock = MagicMock(spec=socket.socket)

    def test_skip_subnegotiation_normal(self):
        """Normal SB data followed by IAC SE is consumed."""
        self.sock.recv.side_effect = [
            b"\x00",  # data
            b"\x50",  # data
            bytes([IAC]),
            bytes([SE]),
        ]
        self.server._skip_subnegotiation(self.sock)
        self.assertEqual(self.sock.recv.call_count, 4)

    def test_skip_subnegotiation_iac_iac_escape(self):
        """IAC IAC inside SB data is treated as escaped 0xFF and skipped."""
        self.sock.recv.side_effect = [
            b"\x01",  # data
            bytes([IAC]),
            bytes([IAC]),  # escaped 0xFF
            b"\x02",  # more data
            bytes([IAC]),
            bytes([SE]),  # end
        ]
        self.server._skip_subnegotiation(self.sock)
        self.assertEqual(self.sock.recv.call_count, 6)

    def test_skip_subnegotiation_eof(self):
        """EOF during subnegotiation returns silently."""
        self.sock.recv.side_effect = [
            b"\x01",  # data
            b"",  # EOF
        ]
        # Should not raise
        self.server._skip_subnegotiation(self.sock)


class DrainPendingInputTest(unittest.TestCase):
    """Test cases for TelnetServer._drain_pending_input() (#268 regression pin).

    The auth-failure path must consume input left pending by read_line's
    skip_lf deferral; closing with unread receive data RSTs the connection
    and Windows clients never see the failure message.
    """

    def setUp(self):
        self.server = _make_server()
        self.sock = MagicMock(spec=socket.socket)
        self.sock.gettimeout.return_value = 7  # Distinct sentinel for restore

    def test_drains_until_quiet_and_restores_timeout(self):
        """Pending bytes are consumed until the socket goes quiet; the
        drain timeout is applied and the original timeout restored."""
        self.sock.recv.side_effect = [b"\n", b"x", TimeoutError()]
        self.server._drain_pending_input(self.sock)
        self.assertEqual(self.sock.recv.call_count, 3)
        # Contract: short drain timeout applied, then original restored.
        self.sock.settimeout.assert_has_calls([mock.call(_IAC_DRAIN_TIMEOUT), mock.call(7)])

    def test_drain_stops_at_eof_and_restores_timeout(self):
        """EOF (empty recv) stops the drain without raising."""
        self.sock.recv.side_effect = [b"\n", b""]
        self.server._drain_pending_input(self.sock)
        self.sock.settimeout.assert_has_calls([mock.call(_IAC_DRAIN_TIMEOUT), mock.call(7)])

    def test_drain_exits_at_total_budget_with_noisy_client(self):
        """A client that never goes quiet cannot pin the thread: the drain
        exits once _DRAIN_TOTAL_BUDGET elapses (#268 cross-review)."""
        self.sock.recv.return_value = b"x"  # Endless chatter
        with mock.patch(
            "simnos.plugins.servers.telnet_server.time.monotonic",
            # deadline calc at t=0 (budget 1.0), loop checks at 0.1 / 0.5
            # (recv), then 1.5 (>= deadline -> exit)
            side_effect=[0.0, 0.1, 0.5, 1.5],
        ):
            self.server._drain_pending_input(self.sock)
        self.assertEqual(self.sock.recv.call_count, 2)
        self.sock.settimeout.assert_called_with(7)


class HandleNegotiationTest(unittest.TestCase):
    """Test cases for TelnetServer._handle_negotiation()."""

    def setUp(self):
        self.server = _make_server()
        self.sock = MagicMock(spec=socket.socket)

    def test_handle_negotiation_refuses_unsupported_do(self):
        """Unsupported DO option gets WONT response."""
        self.server._handle_negotiation(self.sock, DO, 0x18)  # TERMINAL-TYPE
        self.sock.sendall.assert_called_once_with(bytes([IAC, WONT, 0x18]))

    def test_handle_negotiation_silent_for_supported_do(self):
        """DO SGA and DO ECHO don't send a response (already WILL'd)."""
        self.server._handle_negotiation(self.sock, DO, SGA)
        self.sock.sendall.assert_not_called()
        self.server._handle_negotiation(self.sock, DO, ECHO)
        self.sock.sendall.assert_not_called()

    def test_handle_negotiation_accepts_naws(self):
        """WILL NAWS gets DO NAWS response."""
        self.server._handle_negotiation(self.sock, WILL, NAWS)
        self.sock.sendall.assert_called_once_with(bytes([IAC, DO, NAWS]))

    def test_handle_negotiation_refuses_unknown_will(self):
        """Unknown WILL option gets DONT response."""
        self.server._handle_negotiation(self.sock, WILL, 0x18)  # TERMINAL-TYPE
        self.sock.sendall.assert_called_once_with(bytes([IAC, DONT, 0x18]))

    def test_handle_negotiation_dont_wont_silent(self):
        """DONT and WONT don't trigger any response."""
        self.server._handle_negotiation(self.sock, DONT, SGA)
        self.sock.sendall.assert_not_called()
        self.server._handle_negotiation(self.sock, WONT, ECHO)
        self.sock.sendall.assert_not_called()


class AuthenticateTest(unittest.TestCase):
    """Test cases for TelnetServer._authenticate() (interactive_login wrapper).

    Since PR2 (#225) _authenticate returns (authenticated, skip_lf): the
    trailing LF/NUL after the password line's CR is reported via skip_lf
    instead of being consumed with a blocking read (U3).
    """

    def setUp(self):
        self.server = _make_server(username="admin", password="secret")

    def test_authenticate_success(self):
        """Correct credentials return (True, skip_lf=True after a CR-terminated password)."""
        sock = MagicMock(spec=socket.socket)
        sock.recv.side_effect = [bytes([b]) for b in b"admin\r\n"] + [bytes([b]) for b in b"secret\r\n"]
        auth_ok, skip_lf = self.server._authenticate(sock)
        self.assertTrue(auth_ok)
        # U3: the final \n is NOT consumed here — reported for the tap to skip
        self.assertTrue(skip_lf)

    def test_authenticate_failure(self):
        """Wrong credentials return (False, skip_lf)."""
        sock = MagicMock(spec=socket.socket)
        sock.recv.side_effect = [bytes([b]) for b in b"admin\r\n"] + [bytes([b]) for b in b"wrong\r\n"]
        auth_ok, _skip_lf = self.server._authenticate(sock)
        self.assertFalse(auth_ok)

    def test_authenticate_echo_disabled_for_password(self):
        """Password input should not be echoed back."""
        sock = MagicMock(spec=socket.socket)
        sock.recv.side_effect = [bytes([b]) for b in b"admin\r\n"] + [bytes([b]) for b in b"secret\r\n"]
        self.server._authenticate(sock)

        # Collect all sendall calls
        sent_data = b"".join(call.args[0] for call in sock.sendall.call_args_list)
        # Username "admin" should be echoed
        self.assertIn(b"admin", sent_data)
        # Password "secret" should NOT be echoed (only the trailing \r\n)
        self.assertNotIn(b"secret", sent_data)


class ReadLineTest(unittest.TestCase):
    """Line-termination pins for the shared read_line via TelnetSocketAdapter.

    Replaces the former TelnetServer._read_line tests. U3 changed the CR
    follower handling: the LF/NUL after a CR is no longer consumed with a
    blocking read inside the call — it is consumed by the NEXT read_line
    call via skip_lf propagation (boundary patterns pinned per the G3
    design: CR LF / CR NUL / CR + regular byte).
    """

    def setUp(self):
        self.server = _make_server()

    def _adapter(self, input_bytes: bytes) -> TelnetSocketAdapter:
        sock = MagicMock(spec=socket.socket)
        sock.recv.side_effect = [bytes([b]) for b in input_bytes]
        return TelnetSocketAdapter(sock, self.server)

    def test_read_line_cr_lf_boundary(self):
        """CR LF across a boundary: LF is consumed by the next call via skip_lf."""
        adapter = self._adapter(b"hi\r\nok\r")
        line, skip_lf = read_line(adapter, echo=False)
        self.assertEqual((line, skip_lf), ("hi", True))
        line, skip_lf = read_line(adapter, echo=False, skip_lf=skip_lf)
        self.assertEqual((line, skip_lf), ("ok", True))

    def test_read_line_cr_nul_boundary(self):
        """CR NUL (RFC 854): NUL is consumed by the next call (nul_resets_skip_lf=True)."""
        adapter = self._adapter(b"hi\r\x00ok\r")
        line, skip_lf = read_line(adapter, echo=False)
        self.assertEqual((line, skip_lf), ("hi", True))
        line, skip_lf = read_line(adapter, echo=False, skip_lf=skip_lf)
        self.assertEqual((line, skip_lf), ("ok", True))

    def test_read_line_cr_then_data_boundary(self):
        """CR followed by a regular byte: the byte belongs to the next line."""
        adapter = self._adapter(b"hi\rXok\n")
        line, skip_lf = read_line(adapter, echo=False)
        self.assertEqual((line, skip_lf), ("hi", True))
        line, skip_lf = read_line(adapter, echo=False, skip_lf=skip_lf)
        self.assertEqual((line, skip_lf), ("Xok", False))

    def test_read_line_bare_lf(self):
        """Bare LF terminates the line with no pending skip_lf."""
        adapter = self._adapter(b"hi\n")
        line, skip_lf = read_line(adapter, echo=False)
        self.assertEqual((line, skip_lf), ("hi", False))


class PluginRegistrationTest(unittest.TestCase):
    """Test that TelnetServer is registered in the plugin dict."""

    def test_telnet_server_in_plugins_dict(self):
        self.assertIn("TelnetServer", servers_plugins)
        self.assertIs(servers_plugins["TelnetServer"], TelnetServer)


class InventoryValidationTest(unittest.TestCase):
    """Test Pydantic inventory validation with TelnetServer."""

    def test_inventory_telnet_server_validates(self):
        """Inventory with TelnetServer plugin should validate."""
        data: dict = {
            "hosts": {
                "router1": {
                    "username": "admin",
                    "password": "admin",
                    "port": 6023,
                    "platform": "cisco_ios",
                    "server": {
                        "plugin": "TelnetServer",
                        "configuration": {
                            "banner": "Welcome",
                            "timeout": 1,
                        },
                    },
                }
            }
        }
        inventory = ModelSimnosInventory(**data)
        server = inventory.hosts["router1"].server
        assert server is not None
        self.assertEqual(server.plugin, "TelnetServer")

    def test_inventory_ssh_server_still_validates(self):
        """Existing SSH server inventory should not regress."""
        data: dict = {
            "hosts": {
                "switch1": {
                    "username": "admin",
                    "password": "admin",
                    "port": 6022,
                    "platform": "cisco_ios",
                    "server": {
                        "plugin": "ParamikoSshServer",
                        "configuration": {
                            "ssh_banner": "SSH Server",
                            "timeout": 1,
                        },
                    },
                }
            }
        }
        inventory = ModelSimnosInventory(**data)
        server = inventory.hosts["switch1"].server
        assert server is not None
        self.assertEqual(server.plugin, "ParamikoSshServer")


class SecurityWarningTest(unittest.TestCase):
    """Test non-local address warning."""

    def test_non_local_address_warns(self):
        """Binding to a non-local address should emit a warning."""
        with self.assertLogs("simnos.plugins.servers.telnet_server", level="WARNING") as cm:
            _make_server(address="192.168.1.1")
        self.assertTrue(
            any("plaintext" in msg for msg in cm.output),
            f"Expected plaintext warning, got: {cm.output}",
        )

    def test_loopback_address_no_warning(self):
        """Binding to 127.0.0.1 should not emit a warning."""
        with (
            self.assertRaises(AssertionError),
            self.assertLogs("simnos.plugins.servers.telnet_server", level="WARNING"),
        ):
            _make_server(address="127.0.0.1")


class IsLoopbackTest(unittest.TestCase):
    """Test the _is_loopback helper function."""

    def test_loopback_127_0_0_1(self):
        self.assertTrue(_is_loopback("127.0.0.1"))

    def test_loopback_127_0_0_2(self):
        self.assertTrue(_is_loopback("127.0.0.2"))

    def test_non_loopback(self):
        self.assertFalse(_is_loopback("192.168.1.1"))

    def test_loopback_localhost(self):
        self.assertTrue(_is_loopback("localhost"))


class TelnetIntegrationTest(unittest.TestCase):
    """Integration tests using real sockets."""

    def _create_server_on_free_port(self, **kwargs):
        """Create a TelnetServer bound to a random free port."""
        nos = MagicMock()
        nos.initial_prompt = "Router>"
        nos.commands = {}

        shell_cls = MagicMock()

        server = TelnetServer(
            shell=shell_cls,
            nos=nos,
            nos_inventory_config={},
            port=0,  # Will be overridden
            username="admin",
            password="admin",
            address="127.0.0.1",
            timeout=1,
            **kwargs,
        )

        # Find a free port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]

        server.port = port
        return server, port, shell_cls

    def _telnet_connect(self, port, timeout=5):
        """Connect to the server and drain initial IAC negotiation + banner."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect(("127.0.0.1", port))
        time.sleep(0.3)  # Wait for IAC negotiation + banner
        # Drain initial data (IAC sequences + banner + Username prompt)
        try:
            data = sock.recv(4096)
        except TimeoutError:
            data = b""
        return sock, data

    def test_telnet_connection_wrong_credentials(self):
        """Wrong credentials should result in authentication failure message."""
        server, port, shell_cls = self._create_server_on_free_port()
        server.start()
        try:
            sock, _initial_data = self._telnet_connect(port)
            try:
                # Send wrong username
                sock.sendall(b"wrong\r\n")
                time.sleep(0.2)
                # Drain Password prompt
                with contextlib.suppress(TimeoutError):
                    sock.recv(4096)
                # Send wrong password
                sock.sendall(b"wrong\r\n")
                time.sleep(0.3)
                # Read response
                try:
                    response = sock.recv(4096)
                    self.assertIn(b"Authentication failed", response)
                except TimeoutError:
                    pass  # Connection may have been closed
                # Shell should NOT have been started
                shell_cls.assert_not_called()
            finally:
                sock.close()
        finally:
            server.stop()

    def test_telnet_wrong_credentials_drains_before_close(self):
        """Auth failure must deliver the message and close with FIN (#268 pin).

        read_line's skip_lf defers the password line's trailing LF to the
        next reader; on the failure path that reader never comes, and
        closing with unread receive data makes TCP RST the connection —
        Windows clients then never see ``Authentication failed.``. Pins:
        (1) the failure message reaches the client, (2) the close is a
        graceful FIN — the RST is sent on Linux too, so pre-fix the second
        recv raised ConnectionResetError even here — and (3) the structural
        shape: _drain_pending_input runs twice (negotiation window +
        auth-failure path).
        """
        server, port, shell_cls = self._create_server_on_free_port()
        with mock.patch.object(server, "_drain_pending_input", wraps=server._drain_pending_input) as drain:
            server.start()
            try:
                sock, _initial_data = self._telnet_connect(port)
                try:
                    sock.sendall(b"wrong\r\n")
                    time.sleep(0.2)
                    with contextlib.suppress(TimeoutError):
                        sock.recv(4096)  # Drain Password prompt
                    sock.sendall(b"wrong\r\n")
                    # (1) The failure message must arrive (collect until seen)
                    deadline = time.monotonic() + 3.0
                    buf = b""
                    while time.monotonic() < deadline and b"Authentication failed" not in buf:
                        try:
                            chunk = sock.recv(4096)
                        except TimeoutError:
                            continue
                        if not chunk:
                            break  # FIN before message — assertIn below fails loudly
                        buf += chunk
                    self.assertIn(b"Authentication failed", buf)
                    # (2) Graceful FIN, not RST (pre-fix: ConnectionResetError)
                    self.assertEqual(sock.recv(4096), b"")
                    # (3) Drain ran after negotiation AND on the failure path
                    self.assertEqual(drain.call_count, 2)
                    shell_cls.assert_not_called()
                finally:
                    sock.close()
            finally:
                server.stop()

    def test_telnet_connection_auth_starts_shell(self):
        """Successful auth should start the shell."""
        server, port, shell_cls = self._create_server_on_free_port()

        # Make the shell mock block until run_srv is cleared
        def shell_start_block(*args, **kwargs):
            shell_instance = MagicMock()
            shell_instance.start.side_effect = lambda: time.sleep(2)
            return shell_instance

        shell_cls.side_effect = shell_start_block

        server.start()
        try:
            sock, _initial_data = self._telnet_connect(port)
            try:
                # Send correct username
                sock.sendall(b"admin\r\n")
                time.sleep(0.2)
                # Drain Password prompt
                with contextlib.suppress(TimeoutError):
                    sock.recv(4096)
                # Send correct password
                sock.sendall(b"admin\r\n")
                time.sleep(0.5)
                # Shell should have been called
                self.assertTrue(shell_cls.called)
            finally:
                sock.close()
        finally:
            server.stop()

    def test_client_disconnect_stops_shell(self):
        """Closing the client socket should propagate to shell.stop()."""
        server, port, shell_cls = self._create_server_on_free_port()

        shell_stop_called = threading.Event()
        shell_started = threading.Event()

        def shell_factory(*args, **kwargs):
            shell_instance = MagicMock()

            def blocking_start():
                shell_started.set()
                # Block until stop() is called (simulating cmdloop)
                shell_stop_called.wait(timeout=5)

            shell_instance.start.side_effect = blocking_start
            shell_instance.stop.side_effect = lambda: shell_stop_called.set()
            return shell_instance

        shell_cls.side_effect = shell_factory

        server.start()
        try:
            sock, _initial_data = self._telnet_connect(port)
            try:
                # Authenticate
                sock.sendall(b"admin\r\n")
                time.sleep(0.2)
                with contextlib.suppress(TimeoutError):
                    sock.recv(4096)
                sock.sendall(b"admin\r\n")
                # Wait for the shell to start
                self.assertTrue(shell_started.wait(timeout=5), "shell did not start")
            finally:
                # Disconnect the client
                sock.close()

            # shell.stop() should be called within watchdog_interval + margin
            self.assertTrue(
                shell_stop_called.wait(timeout=5),
                "shell.stop() was not called after client disconnect",
            )
        finally:
            server.stop()

    def test_initial_iac_drain_uses_negotiation(self):
        """Initial IAC drain should respond to client negotiation via _handle_negotiation."""
        server, port, shell_cls = self._create_server_on_free_port()

        # Shell that blocks briefly then exits
        def shell_factory(*args, **kwargs):
            shell_instance = MagicMock()
            shell_instance.start.side_effect = lambda: time.sleep(1)
            return shell_instance

        shell_cls.side_effect = shell_factory

        server.start()
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect(("127.0.0.1", port))
            try:
                # Send WILL NAWS — server should respond with DO NAWS
                sock.sendall(bytes([IAC, WILL, NAWS]))
                time.sleep(0.5)
                # Read all available data (server's initial WILL SGA, WILL ECHO,
                # banner, DO NAWS response, Username prompt, etc.)
                data = b""
                while True:
                    try:
                        chunk = sock.recv(4096)
                        if not chunk:
                            break
                        data += chunk
                    except TimeoutError:
                        break

                # Verify IAC DO NAWS is present in the response
                self.assertIn(
                    bytes([IAC, DO, NAWS]),
                    data,
                    f"Expected IAC DO NAWS in response, got: {data!r}",
                )
            finally:
                sock.close()
        finally:
            server.stop()


class SocketToShellTapTest(unittest.TestCase):
    """Test cases for client_to_shell_tap() via TelnetSocketAdapter."""

    def setUp(self):
        self.server = _make_server()
        self.sock = MagicMock(spec=socket.socket)
        self.adapter = TelnetSocketAdapter(self.sock, self.server)
        self.shell_stdin = MagicMock()
        self.shell_replied_event = MagicMock()
        self.shell_replied_event.wait.return_value = True
        # T-9 default: run_srv stays live, loops exit via the recv script's EOF.
        self.run_srv = live_run_srv()

    @mock.patch("simnos.plugins.servers.tap_bridge.time.sleep")
    @mock.patch.object(TelnetServer, "_recv_byte")
    def test_normal_byte_echoed_to_socket(self, mock_recv, _mock_sleep):
        """A normal byte is echoed to the socket and buffered."""
        mock_recv.side_effect = [b"a", None]  # One byte, then EOF
        client_to_shell_tap(self.adapter, self.shell_stdin, self.shell_replied_event, self.run_srv)
        self.sock.sendall.assert_called_with(b"a")

    @mock.patch("simnos.plugins.servers.tap_bridge.time.sleep")
    @mock.patch.object(TelnetServer, "_recv_byte")
    def test_newline_sends_line_to_shell(self, mock_recv, _mock_sleep):
        """Receiving a newline sends the buffered line to the shell and clears replied event."""
        mock_recv.side_effect = [b"h", b"i", b"\r", None]
        client_to_shell_tap(self.adapter, self.shell_stdin, self.shell_replied_event, self.run_srv)
        self.shell_stdin.write.assert_called_once_with("hi\r")
        self.shell_replied_event.clear.assert_called_once()
        # Newline echo: \r\n sent to socket for the newline character
        self.sock.sendall.assert_any_call(b"\r\n")

    @mock.patch("simnos.plugins.servers.tap_bridge.time.sleep")
    @mock.patch.object(TelnetServer, "_recv_byte")
    def test_crlf_sends_single_line_to_shell(self, mock_recv, _mock_sleep):
        """CRLF input: \\r triggers line send, trailing \\n is consumed (RFC 854)."""
        mock_recv.side_effect = [b"h", b"i", b"\r", b"\n", None]
        client_to_shell_tap(self.adapter, self.shell_stdin, self.shell_replied_event, self.run_srv)
        self.shell_stdin.write.assert_called_once_with("hi\r")

    @mock.patch("simnos.plugins.servers.tap_bridge.time.sleep")
    @mock.patch.object(TelnetServer, "_recv_byte")
    def test_cr_nul_resets_skip_lf(self, mock_recv, _mock_sleep):
        """CR NUL is a complete sequence (RFC 854); a subsequent LF is a new line."""
        mock_recv.side_effect = [b"a", b"\r", b"\x00", b"\n", None]
        client_to_shell_tap(self.adapter, self.shell_stdin, self.shell_replied_event, self.run_srv)
        self.assertEqual(self.shell_stdin.write.call_count, 2)
        self.shell_stdin.write.assert_any_call("a\r")
        self.shell_stdin.write.assert_any_call("\n")

    @mock.patch("simnos.plugins.servers.tap_bridge.time.sleep")
    @mock.patch.object(TelnetServer, "_recv_byte")
    def test_cr_followed_by_data_preserves_data(self, mock_recv, _mock_sleep):
        """CR followed by a non-LF byte: line is sent, next byte is not lost."""
        mock_recv.side_effect = [b"x", b"\r", b"y", None]
        client_to_shell_tap(self.adapter, self.shell_stdin, self.shell_replied_event, self.run_srv)
        self.shell_stdin.write.assert_called_once_with("x\r")
        self.sock.sendall.assert_any_call(b"y")

    @mock.patch("simnos.plugins.servers.tap_bridge.time.sleep")
    @mock.patch.object(TelnetServer, "_recv_byte")
    def test_eof_breaks_loop(self, mock_recv, _mock_sleep):
        """EOF (None) breaks the loop and clears run_srv."""
        mock_recv.return_value = None
        client_to_shell_tap(self.adapter, self.shell_stdin, self.shell_replied_event, self.run_srv)
        self.run_srv.clear.assert_called_once()

    @mock.patch("simnos.plugins.servers.tap_bridge.time.sleep")
    @mock.patch.object(TelnetServer, "_recv_byte")
    def test_nul_bytes_dropped(self, mock_recv, _mock_sleep):
        """NUL bytes (0x00) are dropped and not echoed."""
        mock_recv.side_effect = [b"\x00", b"a", None]
        client_to_shell_tap(self.adapter, self.shell_stdin, self.shell_replied_event, self.run_srv)
        self.sock.sendall.assert_called_once_with(b"a")

    @mock.patch("simnos.plugins.servers.tap_bridge.time.sleep")
    @mock.patch.object(TelnetServer, "_recv_byte")
    def test_oserror_on_recv_breaks_loop(self, mock_recv, _mock_sleep):
        """OSError during recv breaks the loop."""
        mock_recv.side_effect = OSError("Read error")
        client_to_shell_tap(self.adapter, self.shell_stdin, self.shell_replied_event, self.run_srv)
        self.run_srv.clear.assert_called_once()

    @mock.patch("simnos.plugins.servers.tap_bridge.time.sleep")
    @mock.patch.object(TelnetServer, "_recv_byte")
    def test_oserror_on_sendall_breaks_loop(self, mock_recv, _mock_sleep):
        """OSError during sendall breaks the loop."""
        mock_recv.side_effect = [b"a", b"b"]
        self.sock.sendall.side_effect = OSError("Write error")
        client_to_shell_tap(self.adapter, self.shell_stdin, self.shell_replied_event, self.run_srv)
        self.run_srv.clear.assert_called_once()

    @mock.patch("simnos.plugins.servers.tap_bridge.time.sleep")
    @mock.patch.object(TelnetServer, "_recv_byte")
    def test_run_srv_clear_exits_loop(self, mock_recv, _mock_sleep):
        """If run_srv is already cleared, the loop exits without reading.

        countdown(0): the loop head gets the first False — nothing is read.
        """
        mock_recv.return_value = b"a"
        self.run_srv = countdown_run_srv(0)
        client_to_shell_tap(self.adapter, self.shell_stdin, self.shell_replied_event, self.run_srv)
        mock_recv.assert_not_called()

    @mock.patch("simnos.plugins.servers.tap_bridge.time.sleep")
    @mock.patch.object(TelnetServer, "_recv_byte")
    def test_shutdown_during_shell_wait(self, mock_recv, _mock_sleep):
        """If run_srv is cleared while waiting for shell reply, the loop exits.

        countdown(2): loop head + first inner-wait guard consume the Trues;
        the second inner-wait guard gets the first False (wait() keeps
        timing out), and the post-wait guard sees False again — the byte
        must not be echoed. No EOF tail: a mistuned countdown fails
        visibly with StopIteration.
        """
        mock_recv.side_effect = [b"a"]
        # wait() returns False (timeout), then run_srv is checked and found False
        self.shell_replied_event.wait.return_value = False
        self.run_srv = countdown_run_srv(2)
        client_to_shell_tap(self.adapter, self.shell_stdin, self.shell_replied_event, self.run_srv)
        # Should exit without processing the byte 'a' because the inner wait loop breaks
        self.sock.sendall.assert_not_called()
        # Verify the interruptible wait uses SHUTDOWN_IO_TIMEOUT
        self.shell_replied_event.wait.assert_called_with(timeout=SHUTDOWN_IO_TIMEOUT)

    @mock.patch("simnos.plugins.servers.tap_bridge.time.sleep")
    @mock.patch.object(TelnetServer, "_recv_byte")
    def test_timeout_error_continues_loop(self, mock_recv, _mock_sleep):
        """TimeoutError during _recv_byte is caught and loop continues."""
        mock_recv.side_effect = [TimeoutError(), b"a", None]
        client_to_shell_tap(self.adapter, self.shell_stdin, self.shell_replied_event, self.run_srv)
        self.sock.sendall.assert_called_once_with(b"a")

    @mock.patch("simnos.plugins.servers.tap_bridge.time.sleep")
    @mock.patch.object(TelnetServer, "_recv_byte")
    def test_shell_replied_event_cleared_on_newline(self, mock_recv, _mock_sleep):
        """Receiving a newline clears the shell_replied_event."""
        mock_recv.side_effect = [b"\n", None]
        client_to_shell_tap(self.adapter, self.shell_stdin, self.shell_replied_event, self.run_srv)
        self.shell_replied_event.clear.assert_called_once()


class ShellToSocketTapTest(unittest.TestCase):
    """Test cases for shell_to_client_tap() via TelnetSocketAdapter."""

    def setUp(self):
        self.server = _make_server()
        self.sock = MagicMock(spec=socket.socket)
        self.adapter = TelnetSocketAdapter(self.sock, self.server)
        self.shell_stdout = MagicMock()
        self.shell_stdout.drain.return_value = []
        self.shell_replied_event = MagicMock()
        # T-9 default: run_srv stays live, loops exit via readline's "" EOF.
        self.run_srv = live_run_srv()

    def test_line_forwarded_to_socket(self):
        """A line from the shell is forwarded to the socket and event is set."""
        self.shell_stdout.readline.side_effect = ["Router>\r\n", ""]
        shell_to_client_tap(self.adapter, self.shell_stdout, self.shell_replied_event, self.run_srv)
        self.sock.sendall.assert_called_once_with(b"Router>\r\n")
        self.shell_replied_event.set.assert_called_once()

    def test_empty_line_breaks_loop(self):
        """Empty line from shell (EOF) breaks the loop and clears run_srv."""
        self.shell_stdout.readline.return_value = ""
        shell_to_client_tap(self.adapter, self.shell_stdout, self.shell_replied_event, self.run_srv)
        self.run_srv.clear.assert_called_once()

    def test_run_srv_cleared_skips_sendall(self):
        """When run_srv is cleared after readline, sendall is skipped (D11).

        countdown(1): the loop head consumes the True; the retry-loop gate
        gets the first False — the send attempt must not happen. No EOF
        tail: a mistuned countdown would exhaust the script and fail
        visibly with StopIteration instead of silently exiting via EOF.
        """
        self.shell_stdout.readline.side_effect = ["Router>\r\n"]
        self.run_srv = countdown_run_srv(1)
        shell_to_client_tap(self.adapter, self.shell_stdout, self.shell_replied_event, self.run_srv)
        self.sock.sendall.assert_not_called()

    def test_nul_stripped_from_line(self):
        """NUL bytes are stripped from the shell output."""
        self.shell_stdout.readline.side_effect = ["abc\x00def\r\n", ""]
        shell_to_client_tap(self.adapter, self.shell_stdout, self.shell_replied_event, self.run_srv)
        self.sock.sendall.assert_called_once_with(b"abcdef\r\n")

    def test_lf_converted_to_crlf(self):
        """Bare LF from shell is converted to CRLF."""
        self.shell_stdout.readline.side_effect = ["line\n", ""]
        shell_to_client_tap(self.adapter, self.shell_stdout, self.shell_replied_event, self.run_srv)
        self.sock.sendall.assert_called_once_with(b"line\r\n")

    def test_oserror_on_sendall_breaks_loop(self):
        """OSError during sendall breaks the loop."""
        self.shell_stdout.readline.return_value = "Router>\r\n"
        self.sock.sendall.side_effect = OSError("Write error")
        shell_to_client_tap(self.adapter, self.shell_stdout, self.shell_replied_event, self.run_srv)
        self.run_srv.clear.assert_called_once()

    def test_shell_replied_event_set_after_send(self):
        """Successfully sending a line to the socket sets the replied event."""
        self.shell_stdout.readline.side_effect = ["hi\r\n", ""]
        shell_to_client_tap(self.adapter, self.shell_stdout, self.shell_replied_event, self.run_srv)
        self.shell_replied_event.set.assert_called_once()

    def test_echo_only_blocks_for_prompt(self):
        """Whitespace-only first line blocks on second readline for prompt."""
        self.shell_stdout.readline.side_effect = ["\r\n", "Router>", ""]
        self.shell_stdout.drain.side_effect = [[], [], []]
        shell_to_client_tap(self.adapter, self.shell_stdout, self.shell_replied_event, self.run_srv)
        # Echo and prompt are sent together in one sendall
        self.sock.sendall.assert_called_once_with(b"\r\nRouter>")

    def test_drain_coalesces_multiple_lines(self):
        """Drained lines are coalesced into a single sendall."""
        self.shell_stdout.readline.side_effect = ["line1\r\n", ""]
        self.shell_stdout.drain.side_effect = [["line2\r\n", "Router>"], []]
        shell_to_client_tap(self.adapter, self.shell_stdout, self.shell_replied_event, self.run_srv)
        self.sock.sendall.assert_called_once_with(b"line1\r\nline2\r\nRouter>")

    def test_prompt_separator_prevents_concatenation(self):
        """Consecutive prompts without trailing newline get \\r\\n separator."""
        self.shell_stdout.readline.side_effect = ["Router>", ""]
        self.shell_stdout.drain.side_effect = [["Router>"], []]
        shell_to_client_tap(self.adapter, self.shell_stdout, self.shell_replied_event, self.run_srv)
        # Prompts are separated, not concatenated as "Router>Router>"
        self.sock.sendall.assert_called_once_with(b"Router>\r\nRouter>")


class TelnetSocketAdapterTest(unittest.TestCase):
    """U2 pins for TelnetSocketAdapter.is_closed() (real fileno() == -1 detection).

    The FakeTransport tests in test_tap_bridge.py pin that the shared loops
    consult is_closed(); these tests pin the Telnet adapter's actual
    implementation so a regression to `return False` cannot pass unnoticed.
    """

    def setUp(self):
        self.server = _make_server()

    def test_is_closed_false_on_live_socket(self):
        """A live (open) socket reports is_closed() == False."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            adapter = TelnetSocketAdapter(sock, self.server)
            self.assertFalse(adapter.is_closed())
        finally:
            sock.close()

    def test_is_closed_true_after_local_close(self):
        """A locally closed socket (fileno() == -1) reports is_closed() == True."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.close()
        adapter = TelnetSocketAdapter(sock, self.server)
        self.assertTrue(adapter.is_closed())

    def test_shell_to_client_tap_stops_on_closed_socket(self):
        """U2: a locally-closed socket stops the shell->client loop before any read."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.close()
        adapter = TelnetSocketAdapter(sock, self.server)
        shell_stdout = MagicMock()
        run_srv = live_run_srv()
        shell_to_client_tap(adapter, shell_stdout, MagicMock(), run_srv)
        shell_stdout.readline.assert_not_called()


class SocketToShellTapShellStdoutTest(unittest.TestCase):
    """Test echo routing via shell_stdout parameter."""

    def setUp(self):
        self.server = _make_server()
        self.sock = MagicMock(spec=socket.socket)
        self.adapter = TelnetSocketAdapter(self.sock, self.server)
        self.shell_stdin = MagicMock()
        self.shell_stdout = MagicMock()
        self.shell_replied_event = MagicMock()
        self.shell_replied_event.wait.return_value = True
        # T-9 default: run_srv stays live, loops exit via the recv script's EOF.
        self.run_srv = live_run_srv()

    @mock.patch("simnos.plugins.servers.tap_bridge.time.sleep")
    @mock.patch.object(TelnetServer, "_recv_byte")
    def test_newline_echo_routed_to_shell_stdout(self, mock_recv, _mock_sleep):
        """When shell_stdout is provided, newline echo goes to shell_stdout, not socket."""
        mock_recv.side_effect = [b"\r", None]
        client_to_shell_tap(
            self.adapter,
            self.shell_stdin,
            self.shell_replied_event,
            self.run_srv,
            shell_stdout=self.shell_stdout,
        )
        self.shell_stdout.write.assert_called_once_with("\r\n")
        # Socket should NOT receive the newline echo
        sendall_args = [call.args[0] for call in self.sock.sendall.call_args_list]
        self.assertNotIn(b"\r\n", sendall_args)

    @mock.patch("simnos.plugins.servers.tap_bridge.time.sleep")
    @mock.patch.object(TelnetServer, "_recv_byte")
    def test_newline_echo_to_socket_without_shell_stdout(self, mock_recv, _mock_sleep):
        """Without shell_stdout, newline echo goes directly to socket."""
        mock_recv.side_effect = [b"\r", None]
        client_to_shell_tap(
            self.adapter,
            self.shell_stdin,
            self.shell_replied_event,
            self.run_srv,
        )
        self.sock.sendall.assert_any_call(b"\r\n")

    @mock.patch("simnos.plugins.servers.tap_bridge.time.sleep")
    @mock.patch.object(TelnetServer, "_recv_byte")
    def test_normal_byte_still_echoed_to_socket(self, mock_recv, _mock_sleep):
        """Normal bytes are always echoed directly to socket, even with shell_stdout."""
        mock_recv.side_effect = [b"a", None]
        client_to_shell_tap(
            self.adapter,
            self.shell_stdin,
            self.shell_replied_event,
            self.run_srv,
            shell_stdout=self.shell_stdout,
        )
        self.sock.sendall.assert_called_with(b"a")


class WatchdogTest(unittest.TestCase):
    """Test cases for TelnetServer.watchdog()."""

    def setUp(self):
        self.server = _make_server(watchdog_interval=0.01)
        self.is_running = MagicMock()
        self.run_srv = MagicMock()
        self.shell = MagicMock()

    @mock.patch("simnos.plugins.servers.telnet_server.time.sleep")
    def test_run_srv_loop(self, mock_sleep):
        """Watchdog loops while run_srv is set, then stops shell."""
        self.run_srv.is_set.side_effect = [True, True, False]
        self.is_running.is_set.return_value = True
        self.server.watchdog(self.is_running, self.run_srv, self.shell)
        self.assertEqual(mock_sleep.call_count, 2)
        self.shell.stop.assert_called_once()

    @mock.patch("simnos.plugins.servers.telnet_server.time.sleep")
    def test_breaks_when_is_running_cleared(self, _mock_sleep):
        """Watchdog breaks when is_running is cleared, then stops shell."""
        self.run_srv.is_set.return_value = True
        self.is_running.is_set.return_value = False
        self.server.watchdog(self.is_running, self.run_srv, self.shell)
        self.shell.stop.assert_called_once()

    @mock.patch("simnos.plugins.servers.telnet_server.time.sleep")
    def test_shell_stop_called_on_exit(self, _mock_sleep):
        """shell.stop() is always called on watchdog exit."""
        # Case: run_srv cleared
        self.run_srv.is_set.return_value = False
        self.server.watchdog(self.is_running, self.run_srv, self.shell)
        self.assertEqual(self.shell.stop.call_count, 1)

    @mock.patch("simnos.plugins.servers.telnet_server.time.sleep")
    def test_sleep_interval_capped_by_shutdown_timeout(self, mock_sleep):
        """Sleep interval is the minimum of watchdog_interval and SHUTDOWN_IO_TIMEOUT."""
        self.server.watchdog_interval = 10.0  # Larger than SHUTDOWN_IO_TIMEOUT
        self.run_srv.is_set.side_effect = [True, False]
        self.is_running.is_set.return_value = True
        self.server.watchdog(self.is_running, self.run_srv, self.shell)
        mock_sleep.assert_called_once_with(SHUTDOWN_IO_TIMEOUT)
