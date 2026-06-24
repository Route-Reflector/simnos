"""
Test cases for the ssh_server_paramiko plugin.
"""

import concurrent.futures
import logging
import os
import socket
import tempfile
import threading
import time
import unittest
from unittest import mock
from unittest.mock import MagicMock, Mock

import paramiko
import pytest

from simnos.core.timeouts import SHUTDOWN_IO_TIMEOUT
from simnos.plugins.servers.ssh_server_paramiko import (
    _BUNDLED_MODULI,
    ParamikoChannelAdapter,
    ParamikoSshServer,
    ParamikoSshServerInterface,
)
from simnos.plugins.servers.tap_bridge import client_to_shell_tap, read_line, shell_to_client_tap
from simnos.plugins.servers.tap_io import TapIO
from simnos.plugins.shell.cmd_shell import DispatchResult
from tests.plugins.tap_test_helpers import countdown_run_srv, live_run_srv


class _PushConvergenceShell:
    """Minimal real push shell for the SSH teardown-convergence tests (#297).

    Implements the surface `run_push_session` needs (intro / prompt / newline /
    dispatch). The server constructs it with the usual shell kwargs (stdin /
    stdout / nos / is_running / ...), all ignored except `is_running`.
    """

    def __init__(self, *, is_running, **kwargs):
        self.intro = "Test Shell"
        self.prompt = "Router>"
        self.newline = "\r\n"
        self.is_running = is_running

    def dispatch(self, line: str) -> DispatchResult:
        return DispatchResult(body=f"echo: {line}", prompt=self.prompt, close=False, mode="user")


class ParamikoSshServerInterfaceTest(unittest.TestCase):
    """
    Test cases for the ParamikoSshServerInterface class.
    """

    def test_create_server_with_banner(self):
        """Create a ParamikoSshServerInterface object with a banner."""
        paramiko_server: ParamikoSshServerInterface = ParamikoSshServerInterface("banner")
        self.assertEqual(paramiko_server.ssh_banner, "banner")

    def test_create_server_with_username(self):
        """Create a ParamikoSshServerInterface object with a username."""
        paramiko_server: ParamikoSshServerInterface = ParamikoSshServerInterface(username="username")
        self.assertEqual(paramiko_server.username, "username")

    def test_create_server_with_password(self):
        """Create a ParamikoSshServerInterface object with a password."""
        paramiko_server: ParamikoSshServerInterface = ParamikoSshServerInterface(password="password")
        self.assertEqual(paramiko_server.password, "password")

    def test_create_server_with_username_and_password(self):
        """Create a ParamikoSshServerInterface object with a username and password."""
        paramiko_server: ParamikoSshServerInterface = ParamikoSshServerInterface(
            username="username", password="password"
        )
        self.assertEqual(paramiko_server.username, "username")
        self.assertEqual(paramiko_server.password, "password")

    def test_create_server_with_banner_username_and_password(self):
        """Create a ParamikoSshServerInterface object with a banner, username, and password."""
        paramiko_server: ParamikoSshServerInterface = ParamikoSshServerInterface("banner", "username", "password")
        self.assertEqual(paramiko_server.ssh_banner, "banner")
        self.assertEqual(paramiko_server.username, "username")
        self.assertEqual(paramiko_server.password, "password")

    def test_check_channel_request_is_correct_when_session_request(self):
        """Check that the channel request is correct when the session request is made."""
        paramiko_server: ParamikoSshServerInterface = ParamikoSshServerInterface()
        self.assertEqual(
            paramiko_server.check_channel_request(kind="session", chanid=1),
            paramiko.OPEN_SUCCEEDED,
        )

    def test_check_channel_request_is_incorrect_when_session_is_not_request(self):
        """Check that the channel request is incorrect when the session request is not made."""
        paramiko_server: ParamikoSshServerInterface = ParamikoSshServerInterface()
        self.assertEqual(
            paramiko_server.check_channel_request(kind="shell", chanid=1),
            paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED,
        )

    def test_check_channel_pty_request_returns_always_true(self):
        """Check that the channel pty request always returns True."""
        paramiko_server: ParamikoSshServerInterface = ParamikoSshServerInterface()
        self.assertTrue(
            paramiko_server.check_channel_pty_request(
                channel=1,
                term="xterm",
                width=80,
                height=24,
                pixelwidth=0,
                pixelheight=0,
                modes=None,
            )
        )

    def test_check_channel_shell_request_returns_always_true(self):
        """Check that the channel shell request always returns True."""
        paramiko_server: ParamikoSshServerInterface = ParamikoSshServerInterface()
        self.assertTrue(paramiko_server.check_channel_shell_request(channel=1))

    def test_check_auth_username_incorrect(self):
        """Check that the authentication username is incorrect."""
        paramiko_server: ParamikoSshServerInterface = ParamikoSshServerInterface(
            username="username", password="password"
        )
        self.assertEqual(
            paramiko_server.check_auth_password(username="incorrect", password="password"),
            paramiko.AUTH_FAILED,
        )

    def test_check_auth_password_incorrect(self):
        """Check that the authentication password is incorrect."""
        paramiko_server: ParamikoSshServerInterface = ParamikoSshServerInterface(
            username="username", password="password"
        )
        self.assertEqual(
            paramiko_server.check_auth_password(username="username", password="incorrect"),
            paramiko.AUTH_FAILED,
        )

    def test_check_auth_username_and_password_incorrect(self):
        """Check that the authentication username and password are incorrect."""
        paramiko_server: ParamikoSshServerInterface = ParamikoSshServerInterface(
            username="username", password="password"
        )
        self.assertEqual(
            paramiko_server.check_auth_password(username="incorrect", password="incorrect"),
            paramiko.AUTH_FAILED,
        )

    def test_check_auth_correct(self):
        """Check that the authentication is correct."""
        paramiko_server: ParamikoSshServerInterface = ParamikoSshServerInterface(
            username="username", password="password"
        )
        self.assertEqual(
            paramiko_server.check_auth_password(username="username", password="password"),
            paramiko.AUTH_SUCCESSFUL,
        )

    def test_get_allowed_auths(self):
        """Check that allowed auth methods include password and keyboard-interactive."""
        paramiko_server: ParamikoSshServerInterface = ParamikoSshServerInterface(username="user")
        self.assertEqual(paramiko_server.get_allowed_auths("user"), "password,keyboard-interactive")

    def test_check_auth_interactive_valid_username(self):
        """Check that keyboard-interactive auth returns a query for a valid username."""
        paramiko_server: ParamikoSshServerInterface = ParamikoSshServerInterface(
            username="username", password="password"
        )
        result = paramiko_server.check_auth_interactive("username", "")
        self.assertIsInstance(result, paramiko.InteractiveQuery)

    def test_check_auth_interactive_invalid_username(self):
        """Check that keyboard-interactive auth fails for an invalid username."""
        paramiko_server: ParamikoSshServerInterface = ParamikoSshServerInterface(
            username="username", password="password"
        )
        self.assertEqual(
            paramiko_server.check_auth_interactive("wrong", ""),
            paramiko.AUTH_FAILED,
        )

    def test_check_auth_interactive_response_correct_password(self):
        """Check that keyboard-interactive response succeeds with the correct password."""
        paramiko_server: ParamikoSshServerInterface = ParamikoSshServerInterface(
            username="username", password="password"
        )
        self.assertEqual(
            paramiko_server.check_auth_interactive_response(["password"]),
            paramiko.AUTH_SUCCESSFUL,
        )

    def test_check_auth_interactive_response_incorrect_password(self):
        """Check that keyboard-interactive response fails with an incorrect password."""
        paramiko_server: ParamikoSshServerInterface = ParamikoSshServerInterface(
            username="username", password="password"
        )
        self.assertEqual(
            paramiko_server.check_auth_interactive_response(["wrong"]),
            paramiko.AUTH_FAILED,
        )

    def test_check_auth_interactive_response_empty(self):
        """Check that keyboard-interactive response fails with no responses."""
        paramiko_server: ParamikoSshServerInterface = ParamikoSshServerInterface(
            username="username", password="password"
        )
        self.assertEqual(
            paramiko_server.check_auth_interactive_response([]),
            paramiko.AUTH_FAILED,
        )

    def test_check_auth_interactive_response_multiple(self):
        """Check that keyboard-interactive response fails with multiple responses."""
        paramiko_server: ParamikoSshServerInterface = ParamikoSshServerInterface(
            username="username", password="password"
        )
        self.assertEqual(
            paramiko_server.check_auth_interactive_response(["password", "extra"]),
            paramiko.AUTH_FAILED,
        )

    def test_get_banner(self):
        """Check that the banner is returned."""
        paramiko_server: ParamikoSshServerInterface = ParamikoSshServerInterface("banner")
        self.assertEqual(paramiko_server.get_banner(), ("banner\r\n", "en-US"))


class TapIOTest(unittest.TestCase):
    """
    Test cases for the TapIO class.
    """

    def test_init(self):
        """Check that the TapIO object is initialized correctly."""
        run_srv: threading.Event = threading.Event()
        run_srv.set()
        tap_io: TapIO = TapIO(run_srv=run_srv)
        self.assertTrue(tap_io.run_srv)
        self.assertEqual(len(tap_io.lines), 0)
        self.assertEqual(tap_io.closed, False)
        run_srv.clear()

    def test_readline(self):
        """Check that the readline method returns the correct line."""
        mock_run_srv: Mock = Mock()
        mock_run_srv.is_set.side_effect = [True] * 10 + [False]
        tap_io: TapIO = TapIO(run_srv=mock_run_srv)
        tap_io.write("line1")
        tap_io.write("line2")

        self.assertEqual(tap_io.readline(), "line1")
        self.assertEqual(tap_io.readline(), "line2")
        self.assertEqual(tap_io.readline(), "")

        self.assertEqual(mock_run_srv.is_set.call_count, 11)

    def test_write(self):
        """Check that the write method appends the line to the lines list."""
        tap_io: TapIO = TapIO(run_srv=threading.Event())
        tap_io.write("line1")
        self.assertEqual(list(tap_io.lines), ["line1"])

    def test_drain_returns_fifo_order(self):
        """drain() returns all buffered items in FIFO order (oldest first)."""
        tap_io: TapIO = TapIO(run_srv=threading.Event())
        tap_io.write("first")
        tap_io.write("second")
        tap_io.write("third")
        self.assertEqual(tap_io.drain(), ["first", "second", "third"])

    def test_drain_empties_buffer(self):
        """drain() leaves the buffer empty after returning all items."""
        tap_io: TapIO = TapIO(run_srv=threading.Event())
        tap_io.write("a")
        tap_io.write("b")
        tap_io.drain()
        self.assertEqual(len(tap_io.lines), 0)

    def test_drain_after_readline(self):
        """readline() consumes one item; drain() returns the rest."""
        run_srv: Mock = Mock()
        run_srv.is_set.return_value = True
        tap_io: TapIO = TapIO(run_srv=run_srv)
        tap_io.write("first")
        tap_io.write("second")
        tap_io.write("third")
        self.assertEqual(tap_io.readline(), "first")
        self.assertEqual(tap_io.drain(), ["second", "third"])

    def test_drain_empty(self):
        """drain() on an empty buffer returns an empty list."""
        tap_io: TapIO = TapIO(run_srv=threading.Event())
        self.assertEqual(tap_io.drain(), [])


class ParamikoChannelAdapterTest(unittest.TestCase):
    """Direct pins for ParamikoChannelAdapter (mirrors TelnetSocketAdapterTest).

    recv_byte's b"" -> None EOF normalization (D3) and the is_closed()
    closed-or-inactive truth table (U2) are pinned at the adapter level so a
    regression cannot hide behind the loop tests' implicit coverage.
    """

    def setUp(self):
        self.mock_channel: Mock = Mock()
        self.adapter = ParamikoChannelAdapter(self.mock_channel)

    def test_recv_byte_normalizes_empty_to_none(self):
        """D3: b"" (paramiko EOF) is normalized to None."""
        self.mock_channel.recv.return_value = b""
        self.assertIsNone(self.adapter.recv_byte())

    def test_recv_byte_passes_data_through(self):
        """Regular bytes pass through unchanged."""
        self.mock_channel.recv.return_value = b"x"
        self.assertEqual(self.adapter.recv_byte(), b"x")

    def test_is_closed_truth_table(self):
        """U2: is_closed() == closed or not active (OR short-circuit)."""
        cases = [
            (False, True, False),
            (True, True, True),
            (False, False, True),
            (True, False, True),
        ]
        for closed, active, expected in cases:
            with self.subTest(closed=closed, active=active):
                self.mock_channel.closed = closed
                self.mock_channel.active = active
                self.assertEqual(self.adapter.is_closed(), expected)


class ChannelToShellTapTest(unittest.TestCase):
    """
    Test cases for client_to_shell_tap driven through a ParamikoChannelAdapter.
    """

    def setUp(self):
        """Set up the mock channel object wrapped in a ParamikoChannelAdapter."""
        self.mock_channel: Mock = Mock()
        self.mock_channel.recv.return_value = b"b"
        # is_closed() reads both flags; default to a live channel.
        self.mock_channel.closed = False
        self.mock_channel.active = True
        self.adapter = ParamikoChannelAdapter(self.mock_channel)
        self.mock_shell_stdin: Mock = Mock()
        self.mock_shell_replied_event: Mock = Mock()
        # T-9 default: run_srv stays live, loops exit via the recv script's EOF.
        self.mock_run_srv: Mock = live_run_srv()

    def test_client_to_shell_tap_received_byte(self):
        """Check that client_to_shell_tap receives a byte via channel.recv."""
        self.mock_channel.recv.side_effect = [b"b", b""]
        client_to_shell_tap(
            transport=self.adapter,
            shell_stdin=self.mock_shell_stdin,
            shell_replied_event=self.mock_shell_replied_event,
            run_srv=self.mock_run_srv,
        )
        self.mock_channel.recv.assert_called_with(1)

    def test_client_to_shell_tap_shell_replied_event_wait(self):
        """Check that client_to_shell_tap waits for the shell_replied_event."""
        self.mock_channel.recv.side_effect = [b"b", b""]
        client_to_shell_tap(
            transport=self.adapter,
            shell_stdin=self.mock_shell_stdin,
            shell_replied_event=self.mock_shell_replied_event,
            run_srv=self.mock_run_srv,
        )
        self.mock_shell_replied_event.wait.assert_called_with(timeout=SHUTDOWN_IO_TIMEOUT)

    def test_client_to_shell_tap_break_loop_when_channel_not_active(self):
        """Check that client_to_shell_tap breaks the loop when the channel is not active."""
        self.mock_channel.recv.return_value = b"a"
        self.mock_channel.active = False
        client_to_shell_tap(
            transport=self.adapter,
            shell_stdin=self.mock_shell_stdin,
            shell_replied_event=self.mock_shell_replied_event,
            run_srv=self.mock_run_srv,
        )
        # Breaks at is_closed() before echoing or buffering the byte
        self.mock_channel.sendall.assert_not_called()
        self.mock_shell_stdin.write.assert_not_called()
        self.mock_run_srv.clear.assert_called_once()

    def test_client_to_shell_tap_break_loop_when_channel_closed_but_active(self):
        """U2 widening pin: closed=True is detected even while the transport is alive.

        Pre-G3, the client->shell loop only checked `channel.active`; the shared
        is_closed() now also breaks on `channel.closed` (channel closed while the
        underlying transport is still alive). Pins the OR short-circuit of
        ParamikoChannelAdapter.is_closed() in the client->shell direction.
        """
        self.mock_channel.recv.return_value = b"a"
        self.mock_channel.closed = True
        self.mock_channel.active = True
        client_to_shell_tap(
            transport=self.adapter,
            shell_stdin=self.mock_shell_stdin,
            shell_replied_event=self.mock_shell_replied_event,
            run_srv=self.mock_run_srv,
        )
        # Breaks at is_closed() before echoing or buffering the byte
        self.mock_channel.sendall.assert_not_called()
        self.mock_shell_stdin.write.assert_not_called()
        self.mock_run_srv.clear.assert_called_once()

    def test_client_to_shell_tap_break_loop_if_os_error(self):
        """Check that client_to_shell_tap breaks the loop if an OSError occurs."""
        self.mock_channel.sendall.side_effect = OSError
        client_to_shell_tap(
            transport=self.adapter,
            shell_stdin=self.mock_shell_stdin,
            shell_replied_event=self.mock_shell_replied_event,
            run_srv=self.mock_run_srv,
        )
        # Echo send raised: the byte reached sendall, never the shell.
        self.mock_channel.sendall.assert_called_once_with(b"b")
        self.mock_shell_stdin.write.assert_not_called()
        self.mock_run_srv.clear.assert_called_once()

    def test_client_to_shell_tap_break_loop_if_eof_error(self):
        """Check that client_to_shell_tap breaks the loop if an EOFError occurs."""
        self.mock_channel.sendall.side_effect = EOFError
        client_to_shell_tap(
            transport=self.adapter,
            shell_stdin=self.mock_shell_stdin,
            shell_replied_event=self.mock_shell_replied_event,
            run_srv=self.mock_run_srv,
        )
        # Echo send raised: the byte reached sendall, never the shell.
        self.mock_channel.sendall.assert_called_once_with(b"b")
        self.mock_shell_stdin.write.assert_not_called()
        self.mock_run_srv.clear.assert_called_once()

    def test_client_to_shell_tap_break_loop_if_ssh_exception(self):
        """SSHException on sendall should break the loop (#85)."""
        self.mock_channel.sendall.side_effect = paramiko.SSHException("Transport closed")
        client_to_shell_tap(
            transport=self.adapter,
            shell_stdin=self.mock_shell_stdin,
            shell_replied_event=self.mock_shell_replied_event,
            run_srv=self.mock_run_srv,
        )
        # Echo send raised: the byte reached sendall, never the shell.
        self.mock_channel.sendall.assert_called_once_with(b"b")
        self.mock_shell_stdin.write.assert_not_called()
        self.mock_run_srv.clear.assert_called_once()

    def test_client_to_shell_tap_recv_ssh_exception_breaks(self):
        """SSHException on recv should break the tap loop (#85)."""
        self.mock_channel.recv.side_effect = paramiko.SSHException("Transport closed")
        client_to_shell_tap(
            transport=self.adapter,
            shell_stdin=self.mock_shell_stdin,
            shell_replied_event=self.mock_shell_replied_event,
            run_srv=self.mock_run_srv,
        )
        self.mock_channel.recv.assert_called_once_with(1)
        self.mock_run_srv.clear.assert_called_once()

    def test_client_to_shell_tap_byte_return_character(self):
        """CRLF should be treated as a single line terminator (skip_lf consumes LF)."""
        self.mock_channel.recv.side_effect = [b"\r", b"\n", b""]
        client_to_shell_tap(
            transport=self.adapter,
            shell_stdin=self.mock_shell_stdin,
            shell_replied_event=self.mock_shell_replied_event,
            run_srv=self.mock_run_srv,
        )
        self.mock_channel.sendall.assert_called_once_with(b"\r\n")

        self.mock_shell_stdin.write.assert_called_once_with("\r")

        self.assertEqual(self.mock_shell_replied_event.clear.call_count, 1)

    def test_client_to_shell_tap_crlf_single_line(self):
        """CRLF after data should produce one line, not two."""
        self.mock_channel.recv.side_effect = [b"h", b"i", b"\r", b"\n", b""]
        client_to_shell_tap(
            transport=self.adapter,
            shell_stdin=self.mock_shell_stdin,
            shell_replied_event=self.mock_shell_replied_event,
            run_srv=self.mock_run_srv,
        )
        self.mock_shell_stdin.write.assert_called_once_with("hi\r")
        self.assertEqual(self.mock_channel.sendall.call_count, 3)  # h, i, \r\n

    def test_client_to_shell_tap_cr_nul_lf_keeps_skip_lf(self):
        """SSH NUL does not reset skip_lf (unlike Telnet CR NUL)."""
        self.mock_channel.recv.side_effect = [b"a", b"\r", b"\x00", b"\n", b""]
        client_to_shell_tap(
            transport=self.adapter,
            shell_stdin=self.mock_shell_stdin,
            shell_replied_event=self.mock_shell_replied_event,
            run_srv=self.mock_run_srv,
        )
        self.mock_shell_stdin.write.assert_called_once_with("a\r")

    def test_client_to_shell_tap_cr_followed_by_data(self):
        """CR followed by non-LF data should produce two lines."""
        self.mock_channel.recv.side_effect = [b"x", b"\r", b"y", b"\n", b""]
        client_to_shell_tap(
            transport=self.adapter,
            shell_stdin=self.mock_shell_stdin,
            shell_replied_event=self.mock_shell_replied_event,
            run_srv=self.mock_run_srv,
        )
        calls = [c[0][0] for c in self.mock_shell_stdin.write.call_args_list]
        self.assertEqual(calls, ["x\r", "y\n"])

    def test_client_to_shell_tap_initial_skip_lf(self):
        """initial_skip_lf=True should consume a leading LF."""
        self.mock_channel.recv.side_effect = [b"\n", b"a", b"\r", b""]
        client_to_shell_tap(
            transport=self.adapter,
            shell_stdin=self.mock_shell_stdin,
            shell_replied_event=self.mock_shell_replied_event,
            run_srv=self.mock_run_srv,
            initial_skip_lf=True,
        )
        self.mock_shell_stdin.write.assert_called_once_with("a\r")

    def test_client_to_shell_tap_nul_bytes_are_dropped(self):
        """NUL bytes should be silently dropped (not echoed, not buffered)."""
        self.mock_channel.recv.side_effect = [b"\x00", b"a", b"\n", b""]
        client_to_shell_tap(
            transport=self.adapter,
            shell_stdin=self.mock_shell_stdin,
            shell_replied_event=self.mock_shell_replied_event,
            run_srv=self.mock_run_srv,
        )
        # NUL byte must NOT be echoed to channel
        for call_args in self.mock_channel.sendall.call_args_list:
            self.assertNotEqual(call_args, mock.call(b"\x00"))
        # "a" echoed + "\r\n" for newline = 2 writes
        self.assertEqual(self.mock_channel.sendall.call_count, 2)
        self.mock_shell_stdin.write.assert_called_with("a\n")

    def test_client_to_shell_tap_empty_byte_causes_exit(self):
        """Empty byte (EOF) should cause the loop to exit."""
        self.mock_channel.recv.side_effect = [b""]
        client_to_shell_tap(
            transport=self.adapter,
            shell_stdin=self.mock_shell_stdin,
            shell_replied_event=self.mock_shell_replied_event,
            run_srv=self.mock_run_srv,
        )
        # Empty byte triggers break before any write
        self.mock_channel.sendall.assert_not_called()

    def test_client_to_shell_tap_byte_return_other(self):
        """Check that client_to_shell_tap echoes bytes via channel.sendall."""
        self.mock_channel.recv.side_effect = [b"b", b"c", b"\n", b""]
        client_to_shell_tap(
            transport=self.adapter,
            shell_stdin=self.mock_shell_stdin,
            shell_replied_event=self.mock_shell_replied_event,
            run_srv=self.mock_run_srv,
        )
        self.mock_channel.sendall.assert_any_call(b"b")
        self.mock_channel.sendall.assert_any_call(b"c")
        self.assertEqual(self.mock_channel.sendall.call_count, 3)

        self.assertEqual(self.mock_shell_stdin.write.call_count, 1)

    def test_client_to_shell_tap_exit_run_srv(self):
        """run_srv cleared after one NUL byte: the loop exits without echoing.

        countdown(1): the loop head consumes the True (the NUL is dropped
        before the shell-wait guard); the second loop head gets the first
        False. No EOF tail: a mistuned countdown fails visibly with
        StopIteration.
        """
        self.mock_run_srv = countdown_run_srv(1)
        self.mock_channel.recv.side_effect = [b"\x00"]
        client_to_shell_tap(
            transport=self.adapter,
            shell_stdin=self.mock_shell_stdin,
            shell_replied_event=self.mock_shell_replied_event,
            run_srv=self.mock_run_srv,
        )
        self.assertEqual(self.mock_channel.recv.call_count, 1)
        self.mock_channel.sendall.assert_not_called()
        self.mock_run_srv.clear.assert_called_once()

    def test_client_to_shell_tap_timeout_error_continues_loop(self):
        """TimeoutError on recv() should be caught and the loop should continue."""
        self.mock_channel.recv.side_effect = [TimeoutError, b"a", b"\x00", b""]
        client_to_shell_tap(
            transport=self.adapter,
            shell_stdin=self.mock_shell_stdin,
            shell_replied_event=self.mock_shell_replied_event,
            run_srv=self.mock_run_srv,
        )
        # recv called 4 times: TimeoutError, b"a", b"\x00", b"" (EOF) —
        # the timeout did not abort the loop.
        self.assertEqual(self.mock_channel.recv.call_count, 4)
        # b"a" should be echoed back
        self.mock_channel.sendall.assert_any_call(b"a")

    def test_client_to_shell_tap_shell_stdout_receives_echo(self):
        """When shell_stdout is provided, newline echo goes to shell_stdout, not channel (#96)."""
        self.mock_channel.recv.side_effect = [b"\r", b"\n", b""]
        mock_shell_stdout: Mock = Mock()
        client_to_shell_tap(
            transport=self.adapter,
            shell_stdin=self.mock_shell_stdin,
            shell_replied_event=self.mock_shell_replied_event,
            run_srv=self.mock_run_srv,
            shell_stdout=mock_shell_stdout,
        )
        mock_shell_stdout.write.assert_called_once_with("\r\n")
        self.mock_channel.sendall.assert_not_called()

    def test_client_to_shell_tap_shell_stdout_data_then_newline(self):
        """With shell_stdout, regular bytes echo to channel; only newline goes to shell_stdout (#96)."""
        self.mock_channel.recv.side_effect = [b"a", b"\r", b"\n", b""]
        mock_shell_stdout: Mock = Mock()
        client_to_shell_tap(
            transport=self.adapter,
            shell_stdin=self.mock_shell_stdin,
            shell_replied_event=self.mock_shell_replied_event,
            run_srv=self.mock_run_srv,
            shell_stdout=mock_shell_stdout,
        )
        self.mock_channel.sendall.assert_called_once_with(b"a")
        mock_shell_stdout.write.assert_called_once_with("\r\n")

    def test_client_to_shell_tap_no_shell_stdout_echo_to_channel(self):
        """When shell_stdout is None (default), newline echo goes to channel.sendall (#96)."""
        self.mock_channel.recv.side_effect = [b"\r", b"\n", b""]
        client_to_shell_tap(
            transport=self.adapter,
            shell_stdin=self.mock_shell_stdin,
            shell_replied_event=self.mock_shell_replied_event,
            run_srv=self.mock_run_srv,
        )
        self.mock_channel.sendall.assert_called_once_with(b"\r\n")

    def test_client_to_shell_tap_shell_stdout_event_clear_order(self):
        """shell_replied_event.clear() is called after shell_stdin.write, with shell_stdout (#96)."""
        self.mock_channel.recv.side_effect = [b"\r", b"\n", b""]
        mock_shell_stdout: Mock = Mock()
        call_order: list[str] = []
        self.mock_shell_stdin.write.side_effect = lambda x: call_order.append("shell_stdin.write")
        mock_shell_stdout.write.side_effect = lambda x: call_order.append("shell_stdout.write")
        self.mock_shell_replied_event.clear.side_effect = lambda: call_order.append("event.clear")
        client_to_shell_tap(
            transport=self.adapter,
            shell_stdin=self.mock_shell_stdin,
            shell_replied_event=self.mock_shell_replied_event,
            run_srv=self.mock_run_srv,
            shell_stdout=mock_shell_stdout,
        )
        self.assertEqual(call_order, ["shell_stdout.write", "shell_stdin.write", "event.clear"])


class ShellToChannelTapTest(unittest.TestCase):
    """
    Test cases for shell_to_client_tap driven through a ParamikoChannelAdapter.
    """

    def setUp(self):
        """Set up the mock channel object wrapped in a ParamikoChannelAdapter."""
        self.mock_channel: Mock = Mock()
        # is_closed() reads both flags; default to a live channel.
        self.mock_channel.closed = False
        self.mock_channel.active = True
        self.adapter = ParamikoChannelAdapter(self.mock_channel)
        self.mock_shell_stdout: Mock = Mock()
        self.mock_shell_stdout.drain.return_value = []
        self.mock_shell_replied_event: Mock = Mock()
        # T-9 default: run_srv stays live, loops exit via readline's "" EOF.
        self.mock_run_srv: Mock = live_run_srv()

    def test_shell_to_client_tap_channel_closed(self):
        """Check that shell_to_client_tap exits when channel.closed is True."""
        self.mock_channel.closed = True
        shell_to_client_tap(
            transport=self.adapter,
            shell_stdout=self.mock_shell_stdout,
            shell_replied_event=self.mock_shell_replied_event,
            run_srv=self.mock_run_srv,
        )
        self.mock_channel.sendall.assert_not_called()
        self.mock_run_srv.clear.assert_called_once()

    def test_shell_to_client_tap_shell_stdout_readline_return_none(self):
        """
        Check that shell_to_client_tap exits when readline returns None.
        """
        self.mock_shell_stdout.readline.return_value = None
        shell_to_client_tap(
            transport=self.adapter,
            shell_stdout=self.mock_shell_stdout,
            shell_replied_event=self.mock_shell_replied_event,
            run_srv=self.mock_run_srv,
        )
        self.mock_shell_stdout.readline.assert_called_once()
        self.mock_channel.sendall.assert_not_called()
        self.mock_run_srv.clear.assert_called_once()

    def test_shell_to_client_tap_shell_stdout_readline_return_carry_return(self):
        """
        Check that echo-only readline triggers a second readline for the prompt.

        When the first readline returns whitespace-only (echo \\r\\n), a
        second readline is performed to wait for the prompt so they are
        sent together in one sendall().
        """
        self.mock_shell_stdout.readline.side_effect = ["\r\n", "Router>", ""]
        shell_to_client_tap(
            transport=self.adapter,
            shell_stdout=self.mock_shell_stdout,
            shell_replied_event=self.mock_shell_replied_event,
            run_srv=self.mock_run_srv,
        )
        self.mock_channel.sendall.assert_called_once_with(b"\r\nRouter>")

    def test_shell_to_client_tap_shell_stdout_readline_return_newline(self):
        """
        Check that LF echo triggers a second readline and LF is converted to CRLF.
        """
        self.mock_shell_stdout.readline.side_effect = ["\n", "Router>", ""]
        shell_to_client_tap(
            transport=self.adapter,
            shell_stdout=self.mock_shell_stdout,
            shell_replied_event=self.mock_shell_replied_event,
            run_srv=self.mock_run_srv,
        )
        self.mock_channel.sendall.assert_called_once_with(b"\r\nRouter>")

    def test_shell_to_client_tap_shell_stdout_readline_return_other(self):
        """
        Check that shell_to_client_tap sends data via channel.sendall.
        """
        self.mock_shell_stdout.readline.side_effect = ["b", ""]
        shell_to_client_tap(
            transport=self.adapter,
            shell_stdout=self.mock_shell_stdout,
            shell_replied_event=self.mock_shell_replied_event,
            run_srv=self.mock_run_srv,
        )
        self.mock_channel.sendall.assert_called_once_with(b"b")

    def test_shell_to_client_tap_socket_error(self):
        """Check that shell_to_client_tap breaks the loop if a socket error occurs."""
        self.mock_shell_stdout.readline.return_value = "b"
        self.mock_channel.sendall.side_effect = OSError(104, "Connection reset by peer")
        shell_to_client_tap(
            transport=self.adapter,
            shell_stdout=self.mock_shell_stdout,
            shell_replied_event=self.mock_shell_replied_event,
            run_srv=self.mock_run_srv,
        )
        # Batch send raised: nothing was delivered, the reply flag stays unset.
        self.mock_channel.sendall.assert_called_once_with(b"b")
        self.mock_shell_replied_event.set.assert_not_called()
        self.mock_run_srv.clear.assert_called_once()

    def test_shell_to_client_tap_ssh_exception(self):
        """Check that shell_to_client_tap breaks the loop if SSHException occurs (#85)."""
        self.mock_shell_stdout.readline.return_value = "b"
        self.mock_channel.sendall.side_effect = paramiko.SSHException("Transport closed")
        shell_to_client_tap(
            transport=self.adapter,
            shell_stdout=self.mock_shell_stdout,
            shell_replied_event=self.mock_shell_replied_event,
            run_srv=self.mock_run_srv,
        )
        # Batch send raised: nothing was delivered, the reply flag stays unset.
        self.mock_channel.sendall.assert_called_once_with(b"b")
        self.mock_shell_replied_event.set.assert_not_called()
        self.mock_run_srv.clear.assert_called_once()

    def test_shell_to_client_tap_set_replied_flag(self):
        """Check that shell_to_client_tap sets the replied flag."""
        self.mock_shell_stdout.readline.side_effect = ["b", ""]
        shell_to_client_tap(
            transport=self.adapter,
            shell_stdout=self.mock_shell_stdout,
            shell_replied_event=self.mock_shell_replied_event,
            run_srv=self.mock_run_srv,
        )
        self.mock_shell_replied_event.set.assert_called_once()

    def test_shell_to_client_tap_exit_run_srv(self):
        """One batch is sent, then run_srv is cleared and the loop exits.

        countdown(3) bookkeeping for the current loop shape: outer head,
        retry entry and the post-send retry re-check consume the Trues; the
        second outer head gets the first False. The contract pinned here is
        only "one batch sent, then shutdown" — the D11 send-gate structure
        itself is pinned by the policy tests in test_tap_bridge.py.
        """
        self.mock_run_srv = countdown_run_srv(3)
        self.mock_shell_stdout.readline.return_value = "b"
        shell_to_client_tap(
            transport=self.adapter,
            shell_stdout=self.mock_shell_stdout,
            shell_replied_event=self.mock_shell_replied_event,
            run_srv=self.mock_run_srv,
        )
        self.mock_channel.sendall.assert_called_once_with(b"b")
        self.mock_shell_replied_event.set.assert_called_once()
        self.mock_run_srv.clear.assert_called_once()


def make_paramiko_server_args() -> dict:
    """Build the ParamikoSshServer constructor kwargs (SSoT, no side effects)."""
    return {
        "shell": Mock(),
        "nos": Mock(),
        "nos_inventory_config": {},
        "port": 22,
        "username": "admin",
        "password": "admin",
    }


@pytest.fixture
def paramiko_server_args():
    """ParamikoSshServer kwargs; the class-state reset lives here, not in the builder."""
    ParamikoSshServer._default_key = None
    ParamikoSshServer._moduli_loaded = None
    return make_paramiko_server_args()


def _expected_baseline(args: dict) -> dict:
    """Attribute values a ParamikoSshServer takes with no optional kwargs."""
    return {
        "nos": args["nos"],
        "nos_inventory_config": args["nos_inventory_config"],
        "shell": args["shell"],
        "shell_configuration": {},
        "ssh_banner": "SIMNOS Paramiko SSH Server",
        "username": args["username"],
        "password": args["password"],
        "port": args["port"],
        "address": "127.0.0.1",
        "timeout": 1,
        "watchdog_interval": 1,
    }


@pytest.mark.parametrize(
    "override_kwargs, expected_override",
    [
        ({}, {}),  # minimum arguments (baseline)
        ({"ssh_banner": "SSH Banner"}, {"ssh_banner": "SSH Banner"}),
        ({"shell_configuration": {"shell": "configuration"}}, {"shell_configuration": {"shell": "configuration"}}),
        ({"address": "127.0.0.2"}, {"address": "127.0.0.2"}),
        ({"timeout": 2}, {"timeout": 2}),
        ({"watchdog_interval": 2}, {"watchdog_interval": 2}),
        (
            {
                "ssh_banner": "SSH Banner",
                "shell_configuration": {"shell": "configuration"},
                "address": "127.0.0.2",
                "timeout": 2,
                "watchdog_interval": 2,
            },
            {
                "ssh_banner": "SSH Banner",
                "shell_configuration": {"shell": "configuration"},
                "address": "127.0.0.2",
                "timeout": 2,
                "watchdog_interval": 2,
            },
        ),
    ],
    ids=["baseline", "ssh_banner", "shell_configuration", "address", "timeout", "watchdog_interval", "all"],
)
def test_init_kwargs(paramiko_server_args, override_kwargs, expected_override):
    """baseline + each optional kwarg; the default-key identity is pinned per case."""
    server = ParamikoSshServer(**paramiko_server_args, **override_kwargs)
    expected = {**_expected_baseline(paramiko_server_args), **expected_override}
    for attr, value in expected.items():
        assert getattr(server, attr) == value
    # No ssh_key_file: a generated RSAKey shared via the class-level cache.
    assert isinstance(server._ssh_server_key, paramiko.RSAKey)
    assert server._ssh_server_key is ParamikoSshServer._default_key


def test_init_with_ssh_key_file(paramiko_server_args):
    """ssh_key_file loads the key from disk instead of the default cache."""
    server = ParamikoSshServer(**paramiko_server_args, ssh_key_file="tests/assets/ssh_host_rsa_key")
    for attr, value in _expected_baseline(paramiko_server_args).items():
        assert getattr(server, attr) == value
    assert server._ssh_server_key == paramiko.RSAKey(filename="tests/assets/ssh_host_rsa_key")


def test_init_with_ssh_key_file_and_password(paramiko_server_args):
    """ssh_key_file + password loads the encrypted key from disk."""
    server = ParamikoSshServer(
        **paramiko_server_args,
        ssh_key_file="tests/assets/ssh_host_rsa_key_with_password",
        ssh_key_file_password="password",
    )
    for attr, value in _expected_baseline(paramiko_server_args).items():
        assert getattr(server, attr) == value
    assert server._ssh_server_key == paramiko.RSAKey(
        filename="tests/assets/ssh_host_rsa_key_with_password",
        password="password",
    )


class ParamikoSshServerTest(unittest.TestCase):
    """
    Test cases for the ParamikoSshServer class.
    """

    def setUp(self):
        """Set up the ParamikoSshServer tests."""
        ParamikoSshServer._default_key = None
        ParamikoSshServer._moduli_loaded = None
        self.arguments: dict = make_paramiko_server_args()

    @mock.patch("simnos.plugins.servers.ssh_server_paramiko.run_push_session")
    @mock.patch("paramiko.Transport")
    def test_connection_function(
        self,
        mock_transport: MagicMock,
        mock_run_push_session: MagicMock,
    ):
        """connection_function drives the session via the push driver (#297).

        The two tap threads + watchdog were folded into `run_push_session`,
        which runs on this connection thread; assert it is invoked once with the
        shell and the server's `is_running` flag.
        """
        mock_client: MagicMock = MagicMock()
        mock_is_running = Mock()
        paramiko_server: ParamikoSshServer = ParamikoSshServer(**self.arguments)
        paramiko_server.connection_function(mock_client, mock_is_running)

        mock_transport.assert_called_once()
        mock_run_push_session.assert_called_once()
        # is_running is forwarded as the session's run flag (3rd positional arg).
        self.assertIs(mock_run_push_session.call_args.args[2], mock_is_running)

    @mock.patch("paramiko.Transport")
    def test_connection_function_accept_returns_none(self, mock_transport_cls: MagicMock):
        """session.accept() returning None should close session when is_running clears."""
        mock_session = MagicMock()
        mock_session.accept.return_value = None
        mock_transport_cls.return_value = mock_session

        mock_client = MagicMock()
        mock_is_running = Mock()
        mock_is_running.is_set.side_effect = [True, False]
        paramiko_server: ParamikoSshServer = ParamikoSshServer(**self.arguments)
        paramiko_server.connection_function(mock_client, mock_is_running)

        mock_session.accept.assert_called_once()
        mock_session.close.assert_called_once()

    def test_default_ssh_key_emits_warning(self):
        """Creating a server without ssh_key_file should emit a security warning."""
        with self.assertLogs("simnos.plugins.servers.ssh_server_paramiko", level=logging.WARNING) as cm:
            ParamikoSshServer(**self.arguments)
        self.assertTrue(any("auto-generated SSH host key" in msg for msg in cm.output))

    def test_custom_ssh_key_no_warning(self):
        """Creating a server with a custom ssh_key_file should not emit the default key warning."""
        with self.assertNoLogs("simnos.plugins.servers.ssh_server_paramiko", level=logging.WARNING):
            ParamikoSshServer(**self.arguments, ssh_key_file="tests/assets/ssh_host_rsa_key")

    @mock.patch("simnos.plugins.servers.ssh_server_paramiko.paramiko.RSAKey.generate")
    def test_default_key_is_cached_across_instances(self, mock_generate):
        """Multiple servers without ssh_key_file should share one generated key."""
        sentinel_key = MagicMock(spec=paramiko.RSAKey)
        mock_generate.return_value = sentinel_key
        self.addCleanup(setattr, ParamikoSshServer, "_default_key", None)

        server1 = ParamikoSshServer(**self.arguments)
        server2_args = make_paramiko_server_args()
        server2_args["port"] = 23
        server2 = ParamikoSshServer(**server2_args)

        mock_generate.assert_called_once_with(2048)
        self.assertIs(server1._ssh_server_key, sentinel_key)
        self.assertIs(server2._ssh_server_key, sentinel_key)
        self.assertIs(server1._ssh_server_key, server2._ssh_server_key)

    def test_custom_key_does_not_affect_default_cache(self):
        """A server with custom ssh_key_file should not populate the class default key."""
        self.addCleanup(setattr, ParamikoSshServer, "_default_key", None)
        ParamikoSshServer(**self.arguments, ssh_key_file="tests/assets/ssh_host_rsa_key")
        self.assertIsNone(ParamikoSshServer._default_key)

    def test_default_key_generation_is_thread_safe(self):
        """Concurrent instantiation should produce the same key for all instances."""
        self.addCleanup(setattr, ParamikoSshServer, "_default_key", None)
        num_threads = 8
        barrier = threading.Barrier(num_threads)

        def create_server(port):
            barrier.wait()
            # port は仮引数 (literal でない) なので spread しても ty の union widening を誘発しない。
            # helper 化すると make_paramiko_server_args() が thread ごとに走り共有 mock 前提が変わるため、
            # この concurrency test では inline spread を維持する。
            return ParamikoSshServer(**{**self.arguments, "port": port})

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as ex:
            futures = [ex.submit(create_server, 6000 + i) for i in range(num_threads)]
            servers = [f.result() for f in futures]

        keys = {id(s._ssh_server_key) for s in servers}
        self.assertEqual(len(keys), 1, f"Expected all servers to share the same key, got {len(keys)} distinct keys")

    # ---- moduli load fallback (issue #189) ----
    # Pin 4 fallback paths so future paramiko / packaging regressions surface in unit tests.

    @mock.patch("paramiko.Transport.load_server_moduli")
    def test_moduli_load_system_success(self, mock_load):
        """System moduli load success skips the bundled fallback path entirely."""
        ParamikoSshServer._moduli_loaded = None
        self.addCleanup(setattr, ParamikoSshServer, "_moduli_loaded", None)
        mock_load.return_value = True

        ParamikoSshServer(**self.arguments)

        mock_load.assert_called_once_with()
        self.assertTrue(ParamikoSshServer._moduli_loaded)

    @mock.patch("simnos.plugins.servers.ssh_server_paramiko._BUNDLED_MODULI")
    @mock.patch("paramiko.Transport.load_server_moduli")
    def test_moduli_load_system_fail_bundled_success(self, mock_load, mock_bundled):
        """When system moduli is missing, the bundled file is loaded and no error is logged."""
        ParamikoSshServer._moduli_loaded = None
        self.addCleanup(setattr, ParamikoSshServer, "_moduli_loaded", None)
        mock_load.side_effect = [False, True]
        mock_bundled.is_file.return_value = True

        with self.assertNoLogs("simnos.plugins.servers.ssh_server_paramiko", level=logging.ERROR):
            ParamikoSshServer(**self.arguments)

        self.assertEqual(mock_load.call_count, 2)
        # The second call must pass `filename=` as a keyword argument so a
        # future "positional" or "filename forgotten" regression is caught.
        self.assertIn("filename", mock_load.call_args_list[1].kwargs)
        self.assertTrue(ParamikoSshServer._moduli_loaded)

    @mock.patch("simnos.plugins.servers.ssh_server_paramiko._BUNDLED_MODULI")
    @mock.patch("paramiko.Transport.load_server_moduli")
    def test_moduli_load_system_fail_bundled_missing(self, mock_load, mock_bundled):
        """When both system and bundled moduli are missing, log.error 'missing' and fall back to workaround."""
        ParamikoSshServer._moduli_loaded = None
        self.addCleanup(setattr, ParamikoSshServer, "_moduli_loaded", None)
        mock_load.return_value = False
        mock_bundled.is_file.return_value = False

        with self.assertLogs("simnos.plugins.servers.ssh_server_paramiko", level=logging.ERROR) as cm:
            ParamikoSshServer(**self.arguments)

        # System moduli load attempted once; bundled load skipped because is_file()=False
        mock_load.assert_called_once_with()
        self.assertFalse(ParamikoSshServer._moduli_loaded)
        self.assertTrue(any("missing" in msg for msg in cm.output))

    @mock.patch("simnos.plugins.servers.ssh_server_paramiko._BUNDLED_MODULI")
    @mock.patch("paramiko.Transport.load_server_moduli")
    def test_moduli_load_system_fail_bundled_corrupted(self, mock_load, mock_bundled):
        """When bundled moduli exists but fails to load (corrupted/unreadable), log.error 'corrupted'."""
        ParamikoSshServer._moduli_loaded = None
        self.addCleanup(setattr, ParamikoSshServer, "_moduli_loaded", None)
        mock_load.side_effect = [False, False]
        mock_bundled.is_file.return_value = True

        with self.assertLogs("simnos.plugins.servers.ssh_server_paramiko", level=logging.ERROR) as cm:
            ParamikoSshServer(**self.arguments)

        self.assertEqual(mock_load.call_count, 2)
        # Same `filename=` kwarg invariant as the success case.
        self.assertIn("filename", mock_load.call_args_list[1].kwargs)
        self.assertFalse(ParamikoSshServer._moduli_loaded)
        self.assertTrue(any("corrupted" in msg for msg in cm.output))

    def test_moduli_load_lock_is_thread_safe(self):
        """Concurrent instantiation should call paramiko.Transport.load_server_moduli once.

        Mirrors `test_default_key_generation_is_thread_safe` to pin that
        `_moduli_lock` serializes the class-level one-shot load.
        """
        self.addCleanup(setattr, ParamikoSshServer, "_moduli_loaded", None)
        num_threads = 8
        barrier = threading.Barrier(num_threads)

        with mock.patch("paramiko.Transport.load_server_moduli", return_value=True) as mock_load:
            ParamikoSshServer._moduli_loaded = None

            def create_server(port):
                barrier.wait()
                # port は仮引数 (literal でない) なので spread しても ty の union widening を誘発しない。
                # helper 化すると make_paramiko_server_args() が thread ごとに走り共有 mock 前提が変わるため、
                # この concurrency test では inline spread を維持する。
                return ParamikoSshServer(**{**self.arguments, "port": port})

            with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as ex:
                futures = [ex.submit(create_server, 7000 + i) for i in range(num_threads)]
                [f.result() for f in futures]

            self.assertEqual(
                mock_load.call_count,
                1,
                f"Expected load_server_moduli to be called once under the lock, got {mock_load.call_count}",
            )
            self.assertTrue(ParamikoSshServer._moduli_loaded)

    # ---- bundled moduli content (issue #189 + #193) ----
    # Pin the data invariant so accidental truncation or partial regeneration is caught.

    def test_bundled_moduli_contains_expected_bit_sizes(self):
        """Bundled moduli file ships with 2048, 3072, and 4096 bit safe primes.

        OpenSSH moduli format stores `bits - 1` in column 5 (e.g. 4095 = 4096-bit prime).
        Pins both the set of bit sizes AND a per-size minimum count so that an
        accidental truncation that leaves e.g. only 1 entry of each size still fails.
        """
        from collections import Counter

        bit_size_counts: Counter[int] = Counter()
        with open(_BUNDLED_MODULI, encoding="ascii") as f:
            for line in f:
                if line.startswith("#") or not line.strip():
                    continue
                parts = line.split()
                if len(parts) >= 7:
                    bit_size_counts[int(parts[4])] += 1
        self.assertEqual(set(bit_size_counts), {2047, 3071, 4095})
        # Minimum counts are intentionally conservative: 4096-bit batch is only 37 entries
        # (single sieve run from a Windows host), so the floor is set well below the
        # committed counts (2048: 1177, 3072: 521, 4096: 37) to avoid false positives on
        # legitimate future regeneration while still catching partial truncation.
        self.assertGreaterEqual(bit_size_counts[2047], 100)
        self.assertGreaterEqual(bit_size_counts[3071], 100)
        self.assertGreaterEqual(bit_size_counts[4095], 30)


class ParamikoSshServerInterfaceAuthNoneTest(unittest.TestCase):
    """Test cases for auth_none support in ParamikoSshServerInterface."""

    def test_check_auth_none_allowed(self):
        """auth_none should return AUTH_SUCCESSFUL when allow_auth_none=True."""
        server = ParamikoSshServerInterface(username="admin", password="admin", allow_auth_none=True)
        self.assertEqual(server.check_auth_none("admin"), paramiko.AUTH_SUCCESSFUL)

    def test_check_auth_none_not_allowed(self):
        """auth_none should return AUTH_FAILED by default."""
        server = ParamikoSshServerInterface(username="admin", password="admin")
        self.assertEqual(server.check_auth_none("admin"), paramiko.AUTH_FAILED)

    def test_get_allowed_auths_with_auth_none(self):
        """Allowed auths should include 'none' when allow_auth_none=True."""
        server = ParamikoSshServerInterface(username="admin", password="admin", allow_auth_none=True)
        allowed = server.get_allowed_auths("admin")
        self.assertIn("none", allowed)
        self.assertIn("password", allowed)
        self.assertIn("keyboard-interactive", allowed)

    def test_get_allowed_auths_default(self):
        """Allowed auths should not include 'none' by default."""
        server = ParamikoSshServerInterface(username="admin", password="admin")
        allowed = server.get_allowed_auths("admin")
        self.assertNotIn("none", allowed)

    def test_auth_method_used_tracking_none(self):
        """auth_method_used should be set to 'none' after check_auth_none succeeds."""
        server = ParamikoSshServerInterface(username="admin", password="admin", allow_auth_none=True)
        self.assertIsNone(server.auth_method_used)
        server.check_auth_none("admin")
        self.assertEqual(server.auth_method_used, "none")

    def test_auth_method_used_tracking_password(self):
        """auth_method_used should be set to 'password' after check_auth_password succeeds."""
        server = ParamikoSshServerInterface(username="admin", password="admin")
        self.assertIsNone(server.auth_method_used)
        server.check_auth_password("admin", "admin")
        self.assertEqual(server.auth_method_used, "password")

    def test_auth_method_used_tracking_keyboard_interactive(self):
        """auth_method_used should be set to 'keyboard-interactive' after interactive auth succeeds."""
        server = ParamikoSshServerInterface(username="admin", password="admin")
        self.assertIsNone(server.auth_method_used)
        server.check_auth_interactive_response(["admin"])
        self.assertEqual(server.auth_method_used, "keyboard-interactive")

    def test_auth_method_used_not_set_on_failure(self):
        """auth_method_used should remain None when authentication fails."""
        server = ParamikoSshServerInterface(username="admin", password="admin")
        server.check_auth_password("admin", "wrong")
        self.assertIsNone(server.auth_method_used)


class ParamikoSshServerInterfaceUsernameMatchTest(unittest.TestCase):
    """Test cases for username matching in ParamikoSshServerInterface.

    MikroTik RouterOS appends terminal options to the SSH username
    (e.g. ``admin+ct511w4098h``).  The server tries an exact match first
    and falls back to stripping the ``+`` suffix, so that usernames
    legitimately containing ``+`` are never falsely truncated.
    """

    # -- _match_username ----------------------------------------------------

    def test_match_exact(self):
        """Exact match should succeed."""
        server = ParamikoSshServerInterface(username="admin", password="pw")
        self.assertTrue(server._match_username("admin"))

    def test_match_mikrotik_suffix(self):
        """MikroTik-style suffix should match via fallback."""
        server = ParamikoSshServerInterface(username="admin", password="pw")
        self.assertTrue(server._match_username("admin+ct511w4098h"))

    def test_match_wrong_username(self):
        """Completely wrong username should not match."""
        server = ParamikoSshServerInterface(username="admin", password="pw")
        self.assertFalse(server._match_username("wrong"))

    def test_match_wrong_base_with_suffix(self):
        """Wrong base username with suffix should not match."""
        server = ParamikoSshServerInterface(username="admin", password="pw")
        self.assertFalse(server._match_username("wrong+ct511w4098h"))

    def test_match_username_containing_plus(self):
        """A configured username containing ``+`` should match exactly."""
        server = ParamikoSshServerInterface(username="user+name", password="pw")
        self.assertTrue(server._match_username("user+name"))

    def test_match_username_containing_plus_not_truncated(self):
        """A username containing ``+`` should not falsely match its prefix."""
        server = ParamikoSshServerInterface(username="user+name", password="pw")
        self.assertFalse(server._match_username("user"))

    def test_match_empty_username(self):
        """Empty username should only match empty configured username."""
        server = ParamikoSshServerInterface(username="", password="pw")
        self.assertTrue(server._match_username(""))

    def test_match_plus_only_suffix(self):
        """``+suffix`` should match configured empty username via fallback."""
        server = ParamikoSshServerInterface(username="", password="pw")
        self.assertTrue(server._match_username("+ct511w4098h"))

    # -- check_auth_password with suffix ------------------------------------

    def test_password_auth_with_mikrotik_suffix(self):
        """Password auth should succeed when username has a MikroTik suffix."""
        server = ParamikoSshServerInterface(username="usertest", password="passtest")
        self.assertEqual(
            server.check_auth_password("usertest+ct511w4098h", "passtest"),
            paramiko.AUTH_SUCCESSFUL,
        )

    def test_password_auth_with_suffix_wrong_password(self):
        """Password auth should fail when the password is wrong even with a valid suffix."""
        server = ParamikoSshServerInterface(username="usertest", password="passtest")
        self.assertEqual(
            server.check_auth_password("usertest+ct511w4098h", "wrong"),
            paramiko.AUTH_FAILED,
        )

    def test_password_auth_with_suffix_wrong_base_username(self):
        """Password auth should fail when the base username (before ``+``) is wrong."""
        server = ParamikoSshServerInterface(username="usertest", password="passtest")
        self.assertEqual(
            server.check_auth_password("wrong+ct511w4098h", "passtest"),
            paramiko.AUTH_FAILED,
        )

    def test_password_auth_exact_match_with_plus_in_username(self):
        """Password auth should succeed for a username containing ``+`` via exact match."""
        server = ParamikoSshServerInterface(username="user+name", password="passtest")
        self.assertEqual(
            server.check_auth_password("user+name", "passtest"),
            paramiko.AUTH_SUCCESSFUL,
        )

    # -- check_auth_interactive with suffix ---------------------------------

    def test_interactive_auth_with_mikrotik_suffix(self):
        """Interactive auth should accept a username with a MikroTik suffix."""
        server = ParamikoSshServerInterface(username="usertest", password="passtest")
        result = server.check_auth_interactive("usertest+ct511w4098h", "")
        self.assertIsInstance(result, paramiko.InteractiveQuery)

    def test_interactive_auth_with_suffix_wrong_username(self):
        """Interactive auth should reject when the base username is wrong."""
        server = ParamikoSshServerInterface(username="usertest", password="passtest")
        self.assertEqual(
            server.check_auth_interactive("wrong+ct511w4098h", ""),
            paramiko.AUTH_FAILED,
        )

    def test_interactive_auth_exact_match_with_plus_in_username(self):
        """Interactive auth should accept a username containing ``+`` via exact match."""
        server = ParamikoSshServerInterface(username="user+name", password="passtest")
        result = server.check_auth_interactive("user+name", "")
        self.assertIsInstance(result, paramiko.InteractiveQuery)


class ParamikoSshServerChannelLoginTest(unittest.TestCase):
    """Test cases for _channel_login in ParamikoSshServer."""

    def setUp(self):
        self.arguments: dict = make_paramiko_server_args()

    def _make_channel(self, input_bytes: bytes):
        """Create a mock channel that returns input_bytes one byte at a time."""
        mock_channel = MagicMock()
        # iter(bytes) yields int; wrap each in bytes() so recv returns bytes
        byte_list = [bytes([b]) for b in input_bytes]
        byte_iter = iter(byte_list)
        mock_channel.recv.side_effect = lambda n: next(byte_iter, b"")
        mock_channel.sendall = MagicMock()
        return mock_channel

    def test_channel_login_success(self):
        """Correct credentials should return (True, skip_lf)."""
        server = ParamikoSshServer(**self.arguments)
        channel = self._make_channel(b"admin\radmin\r")
        authenticated, skip_lf = server._channel_login(channel)
        self.assertTrue(authenticated)
        self.assertTrue(skip_lf)

    def test_channel_login_wrong_password(self):
        """Wrong password should return (False, skip_lf)."""
        server = ParamikoSshServer(**self.arguments)
        channel = self._make_channel(b"admin\rwrong\r")
        authenticated, skip_lf = server._channel_login(channel)
        self.assertFalse(authenticated)
        self.assertTrue(skip_lf)

    def test_channel_login_wrong_username(self):
        """Wrong username should return (False, skip_lf)."""
        server = ParamikoSshServer(**self.arguments)
        channel = self._make_channel(b"wrong\radmin\r")
        authenticated, skip_lf = server._channel_login(channel)
        self.assertFalse(authenticated)
        self.assertTrue(skip_lf)

    def test_channel_login_sends_prompts(self):
        """_channel_login should send User Name: and Password: prompts."""
        server = ParamikoSshServer(**self.arguments)
        channel = self._make_channel(b"admin\radmin\r")
        server._channel_login(channel)
        calls = [c[0][0] for c in channel.sendall.call_args_list]
        self.assertEqual(calls[0], b"\r\nUser Name:")
        self.assertIn(b"\r\nPassword:", calls)

    def test_channel_login_no_password_echo(self):
        """Password input should not be echoed back (no per-byte sendall for password)."""
        server = ParamikoSshServer(**self.arguments)
        channel = self._make_channel(b"admin\radmin\r")
        server._channel_login(channel)
        # Collect all sendall args
        calls = [c[0][0] for c in channel.sendall.call_args_list]
        # Username "admin" chars should be echoed individually (5 echo calls)
        # Password chars should NOT be echoed
        username_echo_count = sum(1 for c in calls if c in (b"a", b"d", b"m", b"i", b"n"))
        self.assertEqual(username_echo_count, 5)

    def test_channel_login_crlf_skip_lf_propagation(self):
        """CRLF line endings should be handled; trailing LF consumed between calls."""
        server = ParamikoSshServer(**self.arguments)
        channel = self._make_channel(b"admin\r\nadmin\r\n")
        authenticated, skip_lf = server._channel_login(channel)
        self.assertTrue(authenticated)
        self.assertTrue(skip_lf)


class ReadLineTest(unittest.TestCase):
    """CRLF/skip_lf pins for the shared read_line via ParamikoChannelAdapter.

    Replaces the former ParamikoSshServer._read_channel_line tests (PR2 #225);
    the assertions are unchanged — the SSH semantics carried over verbatim.
    """

    def _make_channel(self, data: bytes):
        """Create a mock channel whose recv returns bytes one at a time."""
        mock_channel = MagicMock()
        byte_list = [bytes([b]) for b in data]
        byte_iter = iter(byte_list)
        mock_channel.recv.side_effect = lambda n: next(byte_iter, b"")
        mock_channel.sendall = MagicMock()
        return mock_channel

    def test_read_line_bare_cr(self):
        """Bare CR should return (line, True) without blocking."""
        channel = self._make_channel(b"test\r")
        line, skip_lf = read_line(ParamikoChannelAdapter(channel))
        self.assertEqual(line, "test")
        self.assertTrue(skip_lf)

    def test_read_line_bare_lf(self):
        """Bare LF should return (line, False)."""
        channel = self._make_channel(b"test\n")
        line, skip_lf = read_line(ParamikoChannelAdapter(channel))
        self.assertEqual(line, "test")
        self.assertFalse(skip_lf)

    def test_read_line_skip_lf_consumes_lf(self):
        """skip_lf=True should consume a leading LF, then read normally."""
        channel = self._make_channel(b"\nnext\r")
        line, skip_lf = read_line(ParamikoChannelAdapter(channel), skip_lf=True)
        self.assertEqual(line, "next")
        self.assertTrue(skip_lf)

    def test_read_line_skip_lf_non_lf(self):
        """skip_lf=True with non-LF first byte should not consume it."""
        channel = self._make_channel(b"Pass\r")
        line, skip_lf = read_line(ParamikoChannelAdapter(channel), skip_lf=True)
        self.assertEqual(line, "Pass")
        self.assertTrue(skip_lf)

    def test_read_line_nul_preserved(self):
        """NUL bytes should be preserved in login input to prevent auth bypass."""
        channel = self._make_channel(b"ad\x00min\r")
        line, skip_lf = read_line(ParamikoChannelAdapter(channel))
        self.assertEqual(line, "ad\x00min")
        self.assertTrue(skip_lf)

    def test_read_line_eof(self):
        """EOF should return accumulated buffer with skip_lf=False."""
        channel = self._make_channel(b"partial")
        line, skip_lf = read_line(ParamikoChannelAdapter(channel))
        self.assertEqual(line, "partial")
        self.assertFalse(skip_lf)


class PublicKeyAuthTest(unittest.TestCase):
    """Test cases for SSH public key authentication."""

    def setUp(self):
        """Generate a test RSA key pair and create an authorized_keys file."""
        self.test_key = paramiko.RSAKey.generate(2048)
        self.key_type = self.test_key.get_name()
        self.key_base64 = self.test_key.get_base64()
        self.authorized_keys_set = {(self.key_type, self.key_base64)}

    def _write_authorized_keys(self, content: str) -> str:
        """Write content to a temporary authorized_keys file and register cleanup.

        Returns the file path.
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".pub", delete=False) as f:
            f.write(content)
            path = f.name
        self.addCleanup(os.unlink, path)
        return path

    def test_check_auth_publickey_success(self):
        """Registered key should return AUTH_SUCCESSFUL."""
        server = ParamikoSshServerInterface(
            username="user",
            password="pass",
            authorized_keys=self.authorized_keys_set,
        )
        result = server.check_auth_publickey("user", self.test_key)
        self.assertEqual(result, paramiko.AUTH_SUCCESSFUL)

    def test_check_auth_publickey_unknown_key(self):
        """Unregistered key should return AUTH_FAILED."""
        other_key = paramiko.RSAKey.generate(2048)
        server = ParamikoSshServerInterface(
            username="user",
            password="pass",
            authorized_keys=self.authorized_keys_set,
        )
        result = server.check_auth_publickey("user", other_key)
        self.assertEqual(result, paramiko.AUTH_FAILED)

    def test_check_auth_publickey_wrong_username(self):
        """Wrong username should return AUTH_FAILED."""
        server = ParamikoSshServerInterface(
            username="user",
            password="pass",
            authorized_keys=self.authorized_keys_set,
        )
        result = server.check_auth_publickey("wrong_user", self.test_key)
        self.assertEqual(result, paramiko.AUTH_FAILED)

    def test_check_auth_publickey_no_keys_configured(self):
        """No authorized_keys configured should return AUTH_FAILED."""
        server = ParamikoSshServerInterface(
            username="user",
            password="pass",
        )
        result = server.check_auth_publickey("user", self.test_key)
        self.assertEqual(result, paramiko.AUTH_FAILED)

    def test_check_auth_publickey_sets_auth_method(self):
        """Successful publickey auth should set auth_method_used."""
        server = ParamikoSshServerInterface(
            username="user",
            password="pass",
            authorized_keys=self.authorized_keys_set,
        )
        server.check_auth_publickey("user", self.test_key)
        self.assertEqual(server.auth_method_used, "publickey")

    def test_get_allowed_auths_includes_publickey(self):
        """get_allowed_auths should include publickey when keys are configured."""
        server = ParamikoSshServerInterface(
            username="user",
            password="pass",
            authorized_keys=self.authorized_keys_set,
        )
        auths = server.get_allowed_auths("user")
        self.assertIn("publickey", auths)

    def test_get_allowed_auths_excludes_publickey(self):
        """get_allowed_auths should not include publickey when no keys are configured."""
        server = ParamikoSshServerInterface(
            username="user",
            password="pass",
        )
        auths = server.get_allowed_auths("user")
        self.assertNotIn("publickey", auths)

    def test_load_authorized_keys_parses_file(self):
        """Parser should handle comments, blank lines, and multiple keys."""
        key2 = paramiko.RSAKey.generate(2048)
        content = (
            f"# comment line\n\n{self.key_type} {self.key_base64} user@host\n{key2.get_name()} {key2.get_base64()}\n"
        )
        path = self._write_authorized_keys(content)
        keys = ParamikoSshServer._load_authorized_keys(path)
        self.assertEqual(len(keys), 2)
        self.assertIn((self.key_type, self.key_base64), keys)
        self.assertIn((key2.get_name(), key2.get_base64()), keys)

    def test_load_authorized_keys_with_options(self):
        """Parser should handle lines with leading options."""
        content = f'command="/bin/sh",no-pty {self.key_type} {self.key_base64} user@host\n'
        path = self._write_authorized_keys(content)
        keys = ParamikoSshServer._load_authorized_keys(path)
        self.assertEqual(len(keys), 1)
        self.assertIn((self.key_type, self.key_base64), keys)

    def test_load_authorized_keys_file_not_found(self):
        """Non-existent file should raise FileNotFoundError (fail-fast)."""
        with self.assertRaises(FileNotFoundError):
            ParamikoSshServer._load_authorized_keys("/nonexistent/authorized_keys")

    def test_load_authorized_keys_skips_marker_lines(self):
        """@marker lines should be skipped with a warning."""
        content = f"@cert-authority {self.key_type} {self.key_base64}\n{self.key_type} {self.key_base64} normal-key\n"
        path = self._write_authorized_keys(content)
        with self.assertLogs("simnos.plugins.servers.ssh_server_paramiko", level="WARNING") as cm:
            keys = ParamikoSshServer._load_authorized_keys(path)
        self.assertEqual(len(keys), 1)
        self.assertTrue(any("Skipping unsupported marker line" in msg for msg in cm.output))

    def test_load_authorized_keys_warns_on_missing_base64(self):
        """Key type found but base64 missing should emit a warning."""
        content = f"{self.key_type}\n"
        path = self._write_authorized_keys(content)
        with self.assertLogs("simnos.plugins.servers.ssh_server_paramiko", level="WARNING") as cm:
            keys = ParamikoSshServer._load_authorized_keys(path)
        self.assertEqual(len(keys), 0)
        self.assertTrue(any("base64 data missing" in msg for msg in cm.output))

    def test_check_auth_publickey_mikrotik_suffix(self):
        """MikroTik-style user+suffix should succeed with publickey auth."""
        server = ParamikoSshServerInterface(
            username="admin",
            password="pass",
            authorized_keys=self.authorized_keys_set,
        )
        result = server.check_auth_publickey("admin+ct511w4098h", self.test_key)
        self.assertEqual(result, paramiko.AUTH_SUCCESSFUL)

    def test_publickey_auth_bypasses_channel_login_with_auth_none(self):
        """When auth_none and publickey are both enabled, publickey auth should
        bypass channel-level login — SSH-level identity is already verified."""
        server = ParamikoSshServerInterface(
            username="user",
            password="pass",
            allow_auth_none=True,
            authorized_keys=self.authorized_keys_set,
        )
        server.check_auth_publickey("user", self.test_key)
        self.assertEqual(server.auth_method_used, "publickey")
        # auth_method_used != "none" means _channel_login is skipped
        self.assertNotEqual(server.auth_method_used, "none")

    def test_server_passes_authorized_keys_to_interface(self):
        """connection_function should pass authorized_keys to ParamikoSshServerInterface."""
        content = f"{self.key_type} {self.key_base64} user@host\n"
        path = self._write_authorized_keys(content)
        server = ParamikoSshServer(
            shell=Mock(),
            nos=Mock(),
            nos_inventory_config={},
            port=22,
            username="user",
            password="pass",
            authorized_keys=path,
        )
        expected_keys = {(self.key_type, self.key_base64)}
        mock_transport = Mock()
        mock_transport.accept.return_value = None
        with (
            mock.patch("simnos.plugins.servers.ssh_server_paramiko.ParamikoSshServerInterface") as mock_interface,
            mock.patch(
                "simnos.plugins.servers.ssh_server_paramiko.paramiko.Transport",
                return_value=mock_transport,
            ),
        ):
            mock_interface.return_value = Mock(auth_method_used="password")
            mock_is_running = Mock()
            mock_is_running.is_set.side_effect = [True, False]
            server.connection_function(Mock(), mock_is_running)
        mock_interface.assert_called_once()
        self.assertEqual(mock_interface.call_args.kwargs.get("authorized_keys"), expected_keys)


class TeardownFixTests(unittest.TestCase):
    """Tests for Issue #65 — stop() teardown hang fixes."""

    def setUp(self):
        """Set up common fixtures."""
        ParamikoSshServer._default_key = None
        self.arguments: dict = make_paramiko_server_args()

    # Watchdog tests removed with the watchdog method (#297 / §3): the push
    # session loop propagates stop via the channel recv timeout + is_running
    # re-check (covered by RunPushSessionTest and SshIntegrationTests).

    # -- client_to_shell_tap tests -------------------------------------------

    def test_client_to_shell_tap_oserror_breaks(self):
        """OSError on recv should break the tap loop."""
        mock_channel = Mock()
        mock_channel.recv.side_effect = OSError("channel closed")
        mock_shell_stdin = Mock()
        mock_shell_replied_event = Mock()
        mock_run_srv = Mock()
        client_to_shell_tap(
            ParamikoChannelAdapter(mock_channel), mock_shell_stdin, mock_shell_replied_event, mock_run_srv
        )
        mock_run_srv.clear.assert_called_once()

    def test_client_to_shell_tap_clears_run_srv(self):
        """client_to_shell_tap should call run_srv.clear() on exit."""
        mock_channel = Mock()
        mock_channel.recv.return_value = b""  # EOF
        mock_shell_stdin = Mock()
        mock_shell_replied_event = Mock()
        mock_run_srv = Mock()
        client_to_shell_tap(
            ParamikoChannelAdapter(mock_channel), mock_shell_stdin, mock_shell_replied_event, mock_run_srv
        )
        mock_run_srv.clear.assert_called_once()

    # -- shell_to_client_tap tests -------------------------------------------

    def test_shell_to_client_tap_clears_run_srv(self):
        """shell_to_client_tap should call run_srv.clear() on exit."""
        mock_channel = Mock()
        mock_channel.closed = False
        mock_shell_stdout = Mock()
        mock_shell_stdout.drain.return_value = []
        mock_shell_stdout.readline.return_value = None  # EOF
        mock_shell_replied_event = Mock()
        mock_run_srv = Mock()
        shell_to_client_tap(
            ParamikoChannelAdapter(mock_channel), mock_shell_stdout, mock_shell_replied_event, mock_run_srv
        )
        mock_run_srv.clear.assert_called_once()

    def test_shell_to_client_tap_breaks_on_non_timeout_oserror(self):
        """Non-TimeoutError OSError should break and reach run_srv.clear()."""
        mock_channel = Mock()
        mock_channel.closed = False
        mock_shell_stdout = Mock()
        mock_shell_stdout.drain.return_value = []
        mock_shell_stdout.readline.return_value = "test line"
        mock_channel.sendall.side_effect = OSError(32, "Broken pipe")
        mock_shell_replied_event = Mock()
        mock_run_srv = Mock()
        shell_to_client_tap(
            ParamikoChannelAdapter(mock_channel), mock_shell_stdout, mock_shell_replied_event, mock_run_srv
        )
        mock_run_srv.clear.assert_called_once()

    def test_shell_to_client_tap_retries_on_timeout(self):
        """Write-side TimeoutError should retry same line without loss."""
        mock_channel = Mock()
        mock_channel.closed = False
        mock_shell_stdout = Mock()
        mock_shell_stdout.drain.return_value = []
        mock_shell_stdout.readline.side_effect = ["hello\r\n", None]
        # First sendall times out, second succeeds
        mock_channel.sendall.side_effect = [TimeoutError(), None]
        mock_shell_replied_event = Mock()
        mock_run_srv = Mock()
        shell_to_client_tap(
            ParamikoChannelAdapter(mock_channel), mock_shell_stdout, mock_shell_replied_event, mock_run_srv
        )
        # sendall should have been called twice with the same data
        assert mock_channel.sendall.call_count == 2
        mock_channel.sendall.assert_any_call(b"hello\r\n")
        mock_shell_replied_event.set.assert_called_once()

    # -- connection_function tests --------------------------------------------

    @mock.patch("simnos.plugins.servers.ssh_server_paramiko.run_push_session")
    @mock.patch("paramiko.Transport")
    def test_channel_settimeout_is_clamped_for_shutdown(
        self,
        mock_transport_cls: MagicMock,
        mock_run_push_session: MagicMock,
    ):
        """The channel recv timeout (= the push loop's shutdown-poll interval) is
        clamped to min(timeout, watchdog_interval, SHUTDOWN_IO_TIMEOUT) so a large
        configured timeout cannot delay stop convergence (#297, codex#1)."""
        mock_session = MagicMock()
        mock_channel = MagicMock()
        mock_session.accept.return_value = mock_channel
        mock_transport_cls.return_value = mock_session

        # timeout=30 (>> SHUTDOWN_IO_TIMEOUT) must be clamped down to the poll bound.
        # (make_paramiko_server_args omits timeout/watchdog_interval, so these are
        # not duplicate kwargs.)
        server = ParamikoSshServer(**self.arguments, timeout=30, watchdog_interval=0.5)
        server.connection_function(MagicMock(), Mock())

        expected = min(server.timeout, server.watchdog_interval, SHUTDOWN_IO_TIMEOUT)
        assert expected == 0.5  # sanity: the clamp actually bites here
        mock_channel.settimeout.assert_called_once_with(expected)

    @mock.patch("simnos.plugins.servers.ssh_server_paramiko.run_push_session")
    @mock.patch("paramiko.Transport")
    def test_channel_login_send_error_closes_connection(
        self,
        mock_transport_cls: MagicMock,
        mock_run_push_session: MagicMock,
    ):
        """PR2 caller-wrap pin: a send error during channel login closes the
        connection without starting the push session and without propagating."""
        mock_session = MagicMock()
        mock_channel = MagicMock()
        mock_session.accept.return_value = mock_channel
        mock_transport_cls.return_value = mock_session

        server = ParamikoSshServer(**self.arguments)
        with (
            mock.patch("simnos.plugins.servers.ssh_server_paramiko.ParamikoSshServerInterface") as mock_iface_cls,
            mock.patch.object(
                ParamikoSshServer,
                "_channel_login",
                side_effect=paramiko.SSHException("send failed"),
            ),
        ):
            mock_iface_cls.return_value.auth_method_used = "none"
            server.connection_function(MagicMock(), Mock())  # must not raise

        mock_run_push_session.assert_not_called()
        mock_session.close.assert_called_once()

    @mock.patch("paramiko.Transport")
    def test_session_accept_bounded(self, mock_transport_cls: MagicMock):
        """session.accept() should be called with SHUTDOWN_IO_TIMEOUT."""
        mock_session = MagicMock()
        mock_session.accept.return_value = None
        mock_transport_cls.return_value = mock_session

        mock_is_running = Mock()
        mock_is_running.is_set.side_effect = [True, False]
        server = ParamikoSshServer(**self.arguments)
        server.connection_function(MagicMock(), mock_is_running)

        mock_session.accept.assert_called_with(SHUTDOWN_IO_TIMEOUT)

    @mock.patch("paramiko.Transport")
    def test_session_accept_returns_on_stop(self, mock_transport_cls: MagicMock):
        """accept loop should exit when is_running clears and close transport."""
        mock_session = MagicMock()
        mock_session.accept.return_value = None
        mock_transport_cls.return_value = mock_session

        mock_is_running = Mock()
        mock_is_running.is_set.side_effect = [True, False]
        server = ParamikoSshServer(**self.arguments)
        server.connection_function(MagicMock(), mock_is_running)

        mock_session.close.assert_called_once()

    @mock.patch("paramiko.Transport")
    def test_session_accept_returns_on_transport_dead(self, mock_transport_cls: MagicMock):
        """accept loop should exit when session.is_alive() returns False."""
        mock_session = MagicMock()
        mock_session.accept.return_value = None
        mock_session.is_alive.side_effect = [True, False]
        mock_transport_cls.return_value = mock_session

        mock_is_running = Mock()
        server = ParamikoSshServer(**self.arguments)
        server.connection_function(MagicMock(), mock_is_running)

        mock_session.close.assert_called_once()

    @mock.patch("paramiko.Transport")
    def test_handshake_timeout_is_set(self, mock_transport_cls: MagicMock):
        """connection_function should set banner_timeout and handshake_timeout."""
        mock_session = MagicMock()
        mock_session.accept.return_value = None
        mock_transport_cls.return_value = mock_session

        mock_is_running = Mock()
        mock_is_running.is_set.return_value = False
        server = ParamikoSshServer(**self.arguments)
        server.connection_function(MagicMock(), mock_is_running)

        assert mock_session.banner_timeout == SHUTDOWN_IO_TIMEOUT
        assert mock_session.handshake_timeout == SHUTDOWN_IO_TIMEOUT

    @mock.patch("simnos.plugins.servers.ssh_server_paramiko.run_push_session")
    @mock.patch("paramiko.Transport")
    def test_connection_function_spawns_no_inner_threads(
        self,
        mock_transport_cls: MagicMock,
        mock_run_push_session: MagicMock,
    ):
        """The push driver runs on the connection thread itself (#297 / §3).

        The old two tapper threads + watchdog are gone; connection_function
        must not spawn any inner thread (the connection thread's daemon-ness is
        owned by TCPServerBase._listen, pinned in test_servers.py).
        """
        mock_session = MagicMock()
        mock_channel = MagicMock()
        mock_session.accept.return_value = mock_channel
        mock_transport_cls.return_value = mock_session

        server = ParamikoSshServer(**self.arguments)
        with mock.patch(
            "simnos.plugins.servers.ssh_server_paramiko.threading.Thread", side_effect=AssertionError("no inner thread")
        ):
            server.connection_function(MagicMock(), Mock())

        mock_run_push_session.assert_called_once()

    @mock.patch("paramiko.Transport")
    def test_start_server_exception_triggers_cleanup(self, mock_transport_cls: MagicMock):
        """start_server() raising SSHException should still close session via finally."""
        mock_session = MagicMock()
        mock_session.start_server.side_effect = paramiko.SSHException("handshake failed")
        mock_transport_cls.return_value = mock_session

        server = ParamikoSshServer(**self.arguments)
        server.connection_function(MagicMock(), Mock())

        mock_session.close.assert_called_once()

    @mock.patch("paramiko.Transport")
    def test_unexpected_exception_triggers_cleanup(self, mock_transport_cls: MagicMock):
        """Unexpected exception after start_server should still close session."""
        mock_session = MagicMock()
        mock_session.accept.side_effect = RuntimeError("unexpected")
        mock_transport_cls.return_value = mock_session

        server = ParamikoSshServer(**self.arguments)
        with self.assertRaises(RuntimeError):
            server.connection_function(MagicMock(), Mock())

        mock_session.close.assert_called_once()


class SshIntegrationTests(unittest.TestCase):
    """Integration tests using real Paramiko connections (design tests 14 & 15)."""

    def setUp(self):
        ParamikoSshServer._default_key = None
        nos = MagicMock()
        nos.initial_prompt = "Router>"
        nos.commands = {}
        nos.auth = None

        self.shell_cls = _PushConvergenceShell

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            self.port = s.getsockname()[1]

        self.server = ParamikoSshServer(
            shell=self.shell_cls,
            nos=nos,
            nos_inventory_config={},
            port=self.port,
            username="admin",
            password="admin",
            address="127.0.0.1",
            timeout=1,
            watchdog_interval=0.1,
        )
        self.server.port = self.port

    def _connect_and_wait_for_intro(self, port: int | None = None) -> paramiko.SSHClient:
        """Open a real SSH shell and read until the intro/prompt arrives.

        Receiving the intro proves the push session loop sent it and is now
        blocked in recv — the precondition for a meaningful teardown test.
        """
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # noqa: S507
        client.connect("127.0.0.1", port=port or self.port, username="admin", password="admin", timeout=5)
        channel = client.invoke_shell()
        channel.settimeout(5)
        received = b""
        while b"Router>" not in received:
            received += channel.recv(1024)
        return client

    def _assert_threads_converged(self):
        """Assert all server connection threads have exited."""
        alive = [t for t in self.server._connection_threads if t.is_alive()]
        self.assertEqual(len(alive), 0, f"Threads still alive: {alive}")

    def _wait_threads_converged(self, timeout: float):
        """Poll until every connection thread has exited or *timeout* elapses."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if not any(t.is_alive() for t in self.server._connection_threads):
                return
            time.sleep(0.05)

    def _assert_stop_time(self, elapsed):
        """Assert stop() completed within the expected time budget."""
        budget = SHUTDOWN_IO_TIMEOUT * 3 + 2
        self.assertLess(elapsed, budget, f"stop() took {elapsed:.1f}s, expected < {budget}s")

    def test_ssh_session_converges_on_client_disconnect(self):
        """A client disconnect ends the push session loop and the connection thread converges (#297).

        Replaces the old shell.stop()-propagation pin: the push loop has no
        blocking cmdloop to interrupt — it exits when recv sees EOF.
        """
        self.server.start()
        try:
            client = self._connect_and_wait_for_intro()
            client.close()  # disconnect -> server-side recv EOF -> push loop exits
            self._wait_threads_converged(timeout=5)
            self._assert_threads_converged()  # converged on disconnect alone, before server.stop()
        finally:
            self.server.stop()

    def test_ssh_server_stop_converges_with_client_connected(self):
        """server.stop() while a client is connected converges the push session within budget (#297).

        stop() clears is_running; the push loop's channel recv timeout re-checks
        it and exits (replacing the old watchdog's stop propagation, §3).
        """
        self.server.start()
        client = self._connect_and_wait_for_intro()
        try:
            t0 = time.monotonic()
            self.server.stop()
            elapsed = time.monotonic() - t0

            self._assert_stop_time(elapsed)
            self._assert_threads_converged()
        finally:
            client.close()
            self.server.stop()

    def test_ssh_large_timeout_still_converges_on_stop(self):
        """A large channel `timeout` must not delay stop convergence (#297, codex#1).

        The push loop wakes on the channel recv timeout to re-check is_running.
        Without bounding it, a `timeout` above SHUTDOWN_SERVER_PER_THREAD_JOIN (2s)
        would leave the connection thread parked past the join budget. The clamp
        in connection_function (min(timeout, watchdog_interval, SHUTDOWN_IO_TIMEOUT))
        keeps convergence within budget; this builds a server with timeout=30 to
        pin it (without the clamp the thread would survive ~30s and fail).
        """
        nos = MagicMock()
        nos.initial_prompt = "Router>"
        nos.commands = {}
        nos.auth = None
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        server = ParamikoSshServer(
            shell=_PushConvergenceShell,
            nos=nos,
            nos_inventory_config={},
            port=port,
            username="admin",
            password="admin",
            address="127.0.0.1",
            timeout=30,  # >> SHUTDOWN_SERVER_PER_THREAD_JOIN; the clamp must rescue convergence
            watchdog_interval=0.1,
        )
        server.port = port
        server.start()
        client = self._connect_and_wait_for_intro(port=port)
        try:
            t0 = time.monotonic()
            server.stop()
            elapsed = time.monotonic() - t0
            self._assert_stop_time(elapsed)
            alive = [t for t in server._connection_threads if t.is_alive()]
            self.assertEqual(alive, [], f"connection thread parked by large timeout: {alive}")
        finally:
            client.close()
            server.stop()

    def test_ssh_incomplete_handshake_stop_converges(self):
        """TCP-only connection (no SSH handshake) + stop() should converge."""
        self.server.start()
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect(("127.0.0.1", self.port))
            try:
                time.sleep(0.5)
            finally:
                sock.close()

            t0 = time.monotonic()
            self.server.stop()
            self._assert_stop_time(time.monotonic() - t0)
        finally:
            self.server.stop()

        self._assert_threads_converged()

    def test_ssh_incomplete_handshake_server_stop_first_converges(self):
        """server.stop() with raw TCP socket still open should converge."""
        self.server.start()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        try:
            sock.connect(("127.0.0.1", self.port))
            time.sleep(0.5)

            t0 = time.monotonic()
            self.server.stop()
            self._assert_stop_time(time.monotonic() - t0)
        finally:
            sock.close()
            self.server.stop()

        self._assert_threads_converged()
