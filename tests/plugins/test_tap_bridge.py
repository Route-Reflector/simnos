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
- U3: read_line propagates skip_lf instead of blocking for the CR follower.
- U4: read_line returns the partial line on recv io_errors.
- Q1: nul_resets_skip_lf quirk switches the CR NUL behaviour per transport.
- Exception-policy table: TimeoutError handling differs per operation and
  must be caught BEFORE transport.io_errors (TimeoutError ⊂ OSError).
"""

import unittest
from unittest.mock import Mock

from simnos.plugins.servers.tap_bridge import (
    client_to_shell_tap,
    interactive_login,
    read_line,
    shell_to_client_tap,
)


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


def _bytes_script(data: bytes) -> list[bytes]:
    """Split *data* into a per-byte recv script."""
    return [bytes([b]) for b in data]


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


class ReadLinePolicyTest(unittest.TestCase):
    """read_line (PR2): U3 skip_lf propagation, U4 partial line, exception policy."""

    def test_cr_sets_skip_lf(self):
        """A CR terminator reports skip_lf=True for the next call (U3)."""
        transport = FakeTransport(_bytes_script(b"hi\r"))
        self.assertEqual(read_line(transport, echo=False), ("hi", True))

    def test_skip_lf_consumes_lf(self):
        """skip_lf=True consumes a leading LF (second half of CR LF)."""
        transport = FakeTransport(_bytes_script(b"\nok\r"))
        self.assertEqual(read_line(transport, echo=False, skip_lf=True), ("ok", True))

    def test_skip_lf_nul_quirk_true_consumes(self):
        """Q1 Telnet: skip_lf=True consumes a leading NUL (RFC 854 CR NUL)."""
        transport = FakeTransport(_bytes_script(b"\x00ok\r"), nul_resets_skip_lf=True)
        self.assertEqual(read_line(transport, echo=False, skip_lf=True), ("ok", True))

    def test_skip_lf_nul_quirk_false_keeps_byte(self):
        """Q1 SSH: skip_lf=True does NOT consume a NUL — it joins the line."""
        transport = FakeTransport(_bytes_script(b"\x00ok\r"), nul_resets_skip_lf=False)
        self.assertEqual(read_line(transport, echo=False, skip_lf=True), ("\x00ok", True))

    def test_skip_lf_cr_is_line_terminator(self):
        """skip_lf=True with a CR: skip_lf clears and the CR terminates an empty line."""
        transport = FakeTransport(_bytes_script(b"\rok\r"))
        self.assertEqual(read_line(transport, echo=False, skip_lf=True), ("", True))

    def test_skip_lf_regular_byte_processed_normally(self):
        """skip_lf=True with a regular byte: the byte belongs to the line."""
        transport = FakeTransport(_bytes_script(b"Xok\n"))
        self.assertEqual(read_line(transport, echo=False, skip_lf=True), ("Xok", False))

    def test_recv_timeout_continues(self):
        """recv TimeoutError -> retry."""
        transport = FakeTransport([TimeoutError(), b"a", b"\n"])
        self.assertEqual(read_line(transport, echo=False), ("a", False))

    def test_recv_io_error_returns_partial(self):
        """U4: recv io_errors -> the partial line read so far is returned."""
        transport = FakeTransport([b"a", b"b", OSError("gone")])
        self.assertEqual(read_line(transport, echo=False), ("ab", False))

    def test_eof_returns_partial(self):
        """EOF (None) -> the partial line read so far is returned."""
        transport = FakeTransport([b"a", b"b"])  # script exhaustion = EOF
        self.assertEqual(read_line(transport, echo=False), ("ab", False))

    def test_echo_send_error_propagates(self):
        """Echo send errors are NOT caught — they propagate to the caller."""
        transport = FakeTransport(_bytes_script(b"ab\r"))
        transport.send_errors = [OSError("reset")]
        with self.assertRaises(OSError):
            read_line(transport, echo=True)


class InteractiveLoginTest(unittest.TestCase):
    """interactive_login (PR2): boundary patterns per the G3 design.

    CR LF / CR NUL / CR + regular byte at the username/password boundary,
    for both nul_resets_skip_lf settings.
    """

    def _login(self, data: bytes, *, nul_resets_skip_lf: bool):
        transport = FakeTransport(_bytes_script(data), nul_resets_skip_lf=nul_resets_skip_lf)
        result = interactive_login(
            transport,
            "admin",
            "secret",
            user_prompt=b"Username: ",
            pass_prompt=b"Password: ",
        )
        return result, transport

    def test_cr_lf_boundary_both_quirks(self):
        """CR LF at the boundary authenticates for both transports."""
        for quirk in (False, True):
            with self.subTest(nul_resets_skip_lf=quirk):
                (auth_ok, skip_lf), _ = self._login(b"admin\r\nsecret\r\n", nul_resets_skip_lf=quirk)
                self.assertTrue(auth_ok)
                # Final \n is left for the tap (skip_lf=True from the final CR)
                self.assertTrue(skip_lf)

    def test_cr_nul_boundary_quirk_true(self):
        """Q1 Telnet: CR NUL at the boundary — NUL consumed, auth succeeds."""
        (auth_ok, skip_lf), _ = self._login(b"admin\r\x00secret\r", nul_resets_skip_lf=True)
        self.assertTrue(auth_ok)
        self.assertTrue(skip_lf)

    def test_cr_nul_boundary_quirk_false(self):
        """Q1 SSH: CR NUL at the boundary — NUL joins the password, auth fails.

        Faithful to the pre-G3 SSH behaviour (no CR NUL convention); SSH
        clients never send CR NUL so this only pins the quirk split.
        """
        (auth_ok, _), _ = self._login(b"admin\r\x00secret\r", nul_resets_skip_lf=False)
        self.assertFalse(auth_ok)

    def test_cr_data_boundary(self):
        """CR + regular byte at the boundary: the byte joins the password."""
        (auth_ok, _), _ = self._login(b"admin\rXsecret\r", nul_resets_skip_lf=True)
        self.assertFalse(auth_ok)  # password read as "Xsecret"

    def test_prompts_and_password_not_echoed(self):
        """Prompts are sent; username echoes, password does not."""
        (auth_ok, _), transport = self._login(b"admin\rsecret\r", nul_resets_skip_lf=False)
        self.assertTrue(auth_ok)
        sent = b"".join(transport.sent)
        self.assertIn(b"Username: ", sent)
        self.assertIn(b"Password: ", sent)
        self.assertIn(b"admin", sent.replace(b"Username: ", b""))  # echoed per byte
        self.assertNotIn(b"secret", sent)

    def test_prompt_send_error_propagates(self):
        """Prompt send errors propagate to the caller (caller wraps)."""
        transport = FakeTransport(_bytes_script(b"admin\r"))
        transport.send_errors = [OSError("reset")]
        with self.assertRaises(OSError):
            interactive_login(
                transport,
                "admin",
                "secret",
                user_prompt=b"Username: ",
                pass_prompt=b"Password: ",
            )

    def test_exact_credential_then_eof_authenticates(self):
        """U4 pin: exact credential + abrupt disconnect (no terminator) authenticates.

        read_line cannot distinguish a terminated line from a truncated one,
        so this matches — the pre-G3 SSH behaviour, kept for equivalence.
        The connection still tears down right after via the taps' EOF path.
        """
        (auth_ok, skip_lf), _ = self._login(b"admin\rsecret", nul_resets_skip_lf=False)
        self.assertTrue(auth_ok)
        self.assertFalse(skip_lf)

    def test_truncated_credential_then_eof_fails(self):
        """U4 pin: a truncated credential fails the comparison."""
        (auth_ok, _), _ = self._login(b"admin\rsecr", nul_resets_skip_lf=False)
        self.assertFalse(auth_ok)


class LoginToTapBoundaryTest(unittest.TestCase):
    """Password→tap boundary pins (G3 design acceptance: 3 patterns × both quirks).

    Wires interactive_login's returned skip_lf into client_to_shell_tap
    (initial_skip_lf) on the same transport — mirroring connection_function —
    and asserts the password line's CR follower is consumed/kept correctly
    by the tap. Complements InteractiveLoginTest, which covers the
    username→password boundary.
    """

    def _run(self, data: bytes, *, nul_resets_skip_lf: bool) -> list[str]:
        transport = FakeTransport(_bytes_script(data), nul_resets_skip_lf=nul_resets_skip_lf)
        auth_ok, skip_lf = interactive_login(
            transport,
            "admin",
            "secret",
            user_prompt=b"Username: ",
            pass_prompt=b"Password: ",
        )
        self.assertTrue(auth_ok)
        shell_stdin = Mock()
        ev, run_srv = _events()
        client_to_shell_tap(transport, shell_stdin, ev, run_srv, initial_skip_lf=skip_lf)
        return [c.args[0] for c in shell_stdin.write.call_args_list]

    def test_password_cr_lf_boundary(self):
        """CR LF: the trailing LF is consumed by the tap via initial_skip_lf (both quirks)."""
        for quirk in (False, True):
            with self.subTest(nul_resets_skip_lf=quirk):
                writes = self._run(b"admin\r\nsecret\r\ncmd\n", nul_resets_skip_lf=quirk)
                self.assertEqual(writes, ["cmd\n"])

    def test_password_cr_nul_lf_boundary_quirk_split(self):
        """CR NUL LF: quirk True treats LF as a new line, quirk False consumes it."""
        writes_telnet = self._run(b"admin\r\nsecret\r\x00\ncmd\n", nul_resets_skip_lf=True)
        self.assertEqual(writes_telnet, ["\n", "cmd\n"])
        writes_ssh = self._run(b"admin\r\nsecret\r\x00\ncmd\n", nul_resets_skip_lf=False)
        self.assertEqual(writes_ssh, ["cmd\n"])

    def test_password_cr_data_boundary(self):
        """CR + regular byte: the byte reaches the shell as line data (both quirks)."""
        for quirk in (False, True):
            with self.subTest(nul_resets_skip_lf=quirk):
                writes = self._run(b"admin\r\nsecret\rXcmd\n", nul_resets_skip_lf=quirk)
                self.assertEqual(writes, ["Xcmd\n"])
