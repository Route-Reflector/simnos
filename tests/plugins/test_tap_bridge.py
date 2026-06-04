"""
Test cases for the transport-agnostic tap functions in tap_bridge (G3 / #225).

Uses an in-memory FakeTransport so the shared loop logic is tested without
any real transport. Transport-specific behaviour (paramiko exceptions, IAC
handling) stays pinned in test_ssh_server_paramiko.py / test_telnet_server.py.

Pinned contracts:
- D11: each send attempt is gated on a preceding run_srv.is_set() check
  (SSH retry-loop form adopted for both transports).
- U1: a batch-send TimeoutError is retried, not treated as a disconnect.
- U2: is_closed() True breaks both loops early.
- Q1: nul_resets_skip_lf quirk switches the CR NUL behaviour per transport.
- Exception-policy table: TimeoutError handling differs per operation and
  must be caught BEFORE transport.io_errors (TimeoutError ⊂ OSError).
"""

import unittest
from unittest.mock import Mock

from simnos.plugins.servers.tap_bridge import client_to_shell_tap, shell_to_client_tap


class FakeTransport:
    """In-memory TransportAdapter with per-operation exception injection."""

    io_errors = (OSError,)
    name = "fake"

    def __init__(self, recv_script=None, *, nul_resets_skip_lf=False):
        # recv_script: list of bytes / None (EOF) / Exception instances to raise
        self.recv_script = list(recv_script or [])
        self.nul_resets_skip_lf = nul_resets_skip_lf
        self.sent: list[bytes] = []
        self.send_errors: list[BaseException] = []  # popped per sendall call
        self.closed = False

    def recv_byte(self):
        if not self.recv_script:
            return None  # EOF when script is exhausted
        item = self.recv_script.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item

    def sendall(self, data: bytes) -> None:
        if self.send_errors:
            raise self.send_errors.pop(0)
        self.sent.append(data)

    def is_closed(self) -> bool:
        return self.closed


def _events(is_set_fuel=None):
    """Build (shell_replied_event, run_srv) mocks. wait() returns True."""
    shell_replied_event = Mock()
    shell_replied_event.wait.return_value = True
    run_srv = Mock()
    if is_set_fuel is not None:
        run_srv.is_set.side_effect = is_set_fuel
    else:
        run_srv.is_set.return_value = True
    return shell_replied_event, run_srv


class ClientToShellTapQuirkTest(unittest.TestCase):
    """Q1: nul_resets_skip_lf switches CR NUL semantics in the shared loop."""

    def test_nul_preserves_skip_lf_when_flag_false(self):
        """SSH semantics: CR NUL LF — NUL keeps skip_lf, LF is consumed."""
        transport = FakeTransport([b"a", b"\r", b"\x00", b"\n"], nul_resets_skip_lf=False)
        shell_stdin = Mock()
        ev, run_srv = _events()
        client_to_shell_tap(transport, shell_stdin, ev, run_srv)
        shell_stdin.write.assert_called_once_with("a\r")

    def test_nul_resets_skip_lf_when_flag_true(self):
        """Telnet semantics (RFC 854): CR NUL completes the sequence, LF is a new line."""
        transport = FakeTransport([b"a", b"\r", b"\x00", b"\n"], nul_resets_skip_lf=True)
        shell_stdin = Mock()
        ev, run_srv = _events()
        client_to_shell_tap(transport, shell_stdin, ev, run_srv)
        self.assertEqual(shell_stdin.write.call_count, 2)
        shell_stdin.write.assert_any_call("a\r")
        shell_stdin.write.assert_any_call("\n")


class ClientToShellTapPolicyTest(unittest.TestCase):
    """Exception-policy table pins for the client→shell direction."""

    def test_recv_timeout_continues(self):
        """recv TimeoutError → continue (line still assembled afterwards)."""
        transport = FakeTransport([TimeoutError(), b"a", b"\n"])
        shell_stdin = Mock()
        ev, run_srv = _events()
        client_to_shell_tap(transport, shell_stdin, ev, run_srv)
        shell_stdin.write.assert_called_once_with("a\n")

    def test_recv_io_error_breaks(self):
        """recv io_errors → break (disconnect)."""
        transport = FakeTransport([OSError("gone")])
        shell_stdin = Mock()
        ev, run_srv = _events()
        client_to_shell_tap(transport, shell_stdin, ev, run_srv)
        shell_stdin.write.assert_not_called()
        run_srv.clear.assert_called_once()

    def test_echo_send_timeout_breaks(self):
        """Echo-send TimeoutError → break (pre-G3 behaviour kept; NOT retried)."""
        transport = FakeTransport([b"a", b"b"])
        transport.send_errors = [TimeoutError()]
        shell_stdin = Mock()
        ev, run_srv = _events()
        client_to_shell_tap(transport, shell_stdin, ev, run_srv)
        # First echo raised → loop broke → nothing was sent, no line reached the shell
        self.assertEqual(transport.sent, [])
        shell_stdin.write.assert_not_called()
        run_srv.clear.assert_called_once()

    def test_echo_send_io_error_breaks(self):
        """Echo-send io_errors → break."""
        transport = FakeTransport([b"a", b"b"])
        transport.send_errors = [OSError("reset")]
        shell_stdin = Mock()
        ev, run_srv = _events()
        client_to_shell_tap(transport, shell_stdin, ev, run_srv)
        shell_stdin.write.assert_not_called()
        run_srv.clear.assert_called_once()

    def test_is_closed_breaks_loop(self):
        """U2: is_closed() True breaks before processing the byte."""
        transport = FakeTransport([b"a"])
        transport.closed = True
        shell_stdin = Mock()
        ev, run_srv = _events()
        client_to_shell_tap(transport, shell_stdin, ev, run_srv)
        self.assertEqual(transport.sent, [])
        shell_stdin.write.assert_not_called()


class ShellToClientTapPolicyTest(unittest.TestCase):
    """Exception-policy + D11/U1 pins for the shell→client direction."""

    def _stdout(self, lines):
        shell_stdout = Mock()
        shell_stdout.readline.side_effect = lines
        shell_stdout.drain.return_value = []
        return shell_stdout

    def test_batch_send_timeout_retries(self):
        """U1: batch-send TimeoutError → retry the same batch (both transports)."""
        transport = FakeTransport()
        transport.send_errors = [TimeoutError()]
        shell_stdout = self._stdout(["hello\r\n", ""])
        ev, run_srv = _events()
        shell_to_client_tap(transport, shell_stdout, ev, run_srv)
        # Retried after the timeout: the batch eventually arrived exactly once
        self.assertEqual(transport.sent, [b"hello\r\n"])
        ev.set.assert_called_once()

    def test_batch_send_io_error_breaks(self):
        """Batch-send io_errors → break (no retry, no replied event)."""
        transport = FakeTransport()
        transport.send_errors = [OSError("reset")]
        shell_stdout = self._stdout(["hello\r\n", ""])
        ev, run_srv = _events()
        shell_to_client_tap(transport, shell_stdout, ev, run_srv)
        self.assertEqual(transport.sent, [])
        ev.set.assert_not_called()
        run_srv.clear.assert_called_once()

    def test_d11_no_send_when_cleared_before_attempt(self):
        """D11: if run_srv is cleared before the send attempt, nothing is sent."""
        transport = FakeTransport()
        shell_stdout = self._stdout(["hello\r\n", ""])
        # outer loop True, retry-loop gate False
        ev, run_srv = _events([True, False])
        shell_to_client_tap(transport, shell_stdout, ev, run_srv)
        self.assertEqual(transport.sent, [])
        ev.set.assert_not_called()

    def test_d11_no_resend_when_cleared_during_retry(self):
        """D11: if run_srv is cleared during a TimeoutError retry, no resend happens."""
        transport = FakeTransport()
        transport.send_errors = [TimeoutError()]
        shell_stdout = self._stdout(["hello\r\n", ""])
        # outer True, retry gate True (send raises), retry re-gate False
        ev, run_srv = _events([True, True, False])
        shell_to_client_tap(transport, shell_stdout, ev, run_srv)
        self.assertEqual(transport.sent, [])
        ev.set.assert_not_called()

    def test_is_closed_breaks_loop(self):
        """U2: is_closed() True breaks before reading from the shell."""
        transport = FakeTransport()
        transport.closed = True
        shell_stdout = self._stdout(["hello\r\n", ""])
        ev, run_srv = _events()
        shell_to_client_tap(transport, shell_stdout, ev, run_srv)
        shell_stdout.readline.assert_not_called()
        self.assertEqual(transport.sent, [])


if __name__ == "__main__":
    unittest.main()
