"""
Test cases for the ssh_server_paramiko plugin.
"""

import io
import threading
import unittest
from unittest import mock
from unittest.mock import MagicMock, Mock

import paramiko

from simnos.plugins.servers.ssh_server_paramiko import (
    DEFAULT_SSH_KEY,
    ParamikoSshServer,
    ParamikoSshServerInterface,
    TapIO,
    channel_to_shell_tap,
    shell_to_channel_tap,
)


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
        tap_io.lines = ["line1", "line2"]

        self.assertEqual(tap_io.readline(), "line2")
        self.assertEqual(tap_io.readline(), "line1")
        self.assertEqual(tap_io.readline(), None)

        self.assertEqual(mock_run_srv.is_set.call_count, 11)

    def test_write(self):
        """Check that the write method appends the line to the lines list."""
        tap_io: TapIO = TapIO(run_srv=threading.Event())
        tap_io.write("line1")
        self.assertEqual(list(tap_io.lines), ["line1"])


class ChannelToShellTapTest(unittest.TestCase):
    """
    Test cases for the ChannelToShellTap class.
    """

    def setUp(self):
        """Set up the ChannelToShellTap object."""
        self.mock_channel_stdio: Mock = Mock()
        self.mock_channel_stdio.read.return_value = b"b"
        self.mock_shell_stdin: Mock = Mock()
        self.mock_shell_replied_event: Mock = Mock()
        self.mock_run_srv: Mock = Mock()

    def test_channel_to_shell_tap_received_byte(self):
        """Check that the ChannelToShellTap object receives a byte."""
        self.mock_run_srv.is_set.side_effect = [True] * 10 + [False]
        channel_to_shell_tap(
            channel_stdio=self.mock_channel_stdio,
            shell_stdin=self.mock_shell_stdin,
            shell_replied_event=self.mock_shell_replied_event,
            run_srv=self.mock_run_srv,
        )
        self.mock_channel_stdio.read.assert_called_with(1)

    def test_channel_to_shell_tap_shell_replied_event_wait(self):
        """Check that the ChannelToShellTap object waits for the shell_replied_event."""
        self.mock_run_srv.is_set.side_effect = [True] * 10 + [False]
        channel_to_shell_tap(
            channel_stdio=self.mock_channel_stdio,
            shell_stdin=self.mock_shell_stdin,
            shell_replied_event=self.mock_shell_replied_event,
            run_srv=self.mock_run_srv,
        )
        self.mock_shell_replied_event.wait.assert_called_with(10)

    def test_channel_to_shell_tap_break_loop_when_channel_stdio_not_active(self):
        """Check that the ChannelToShellTap object breaks the loop when the channel_stdio is not active."""
        self.mock_channel_stdio.read.return_value = b""
        self.mock_channel_stdio.channel.active = False
        channel_to_shell_tap(
            channel_stdio=self.mock_channel_stdio,
            shell_stdin=self.mock_shell_stdin,
            shell_replied_event=self.mock_shell_replied_event,
            run_srv=self.mock_run_srv,
        )
        self.assertEqual(self.mock_run_srv.is_set.call_count, 1)

    def test_channel_to_shell_tap_break_loop_if_os_error(self):
        """Check that the ChannelToShellTap object breaks the loop if an OSError occurs."""
        self.mock_channel_stdio.write.side_effect = OSError
        channel_to_shell_tap(
            channel_stdio=self.mock_channel_stdio,
            shell_stdin=self.mock_shell_stdin,
            shell_replied_event=self.mock_shell_replied_event,
            run_srv=self.mock_run_srv,
        )
        self.assertEqual(self.mock_run_srv.is_set.call_count, 1)

    def test_channel_to_shell_tap_break_loop_if_eof_error(self):
        """Check that the ChannelToShellTap object breaks the loop if an EOFError occurs."""
        self.mock_channel_stdio.write.side_effect = EOFError
        channel_to_shell_tap(
            channel_stdio=self.mock_channel_stdio,
            shell_stdin=self.mock_shell_stdin,
            shell_replied_event=self.mock_shell_replied_event,
            run_srv=self.mock_run_srv,
        )
        self.assertEqual(self.mock_run_srv.is_set.call_count, 1)

    def test_channel_to_shell_tap_byte_return_character(self):
        """Check that the ChannelToShellTap object returns a character."""
        self.mock_run_srv.is_set.side_effect = [True] * 2 + [False]
        self.mock_channel_stdio.read.side_effect = [b"\r", b"\n"]
        channel_to_shell_tap(
            channel_stdio=self.mock_channel_stdio,
            shell_stdin=self.mock_shell_stdin,
            shell_replied_event=self.mock_shell_replied_event,
            run_srv=self.mock_run_srv,
        )
        self.mock_channel_stdio.write.assert_called_with(b"\r\n")
        self.assertEqual(self.mock_channel_stdio.write.call_count, 2)

        self.mock_shell_stdin.write.assert_called_with("\n")
        self.assertEqual(self.mock_shell_stdin.write.call_count, 2)

        self.assertEqual(self.mock_shell_replied_event.clear.call_count, 2)

    def test_channel_to_shell_tap_nul_bytes_are_dropped(self):
        """NUL bytes should be silently dropped (not echoed, not buffered)."""
        self.mock_run_srv.is_set.side_effect = [True, True, True, False]
        self.mock_channel_stdio.read.side_effect = [b"\x00", b"a", b"\n"]
        channel_to_shell_tap(
            channel_stdio=self.mock_channel_stdio,
            shell_stdin=self.mock_shell_stdin,
            shell_replied_event=self.mock_shell_replied_event,
            run_srv=self.mock_run_srv,
        )
        # NUL byte must NOT be echoed to channel
        for call_args in self.mock_channel_stdio.write.call_args_list:
            self.assertNotEqual(call_args, unittest.mock.call(b"\x00"))
        # "a" echoed + "\r\n" for newline = 2 writes
        self.assertEqual(self.mock_channel_stdio.write.call_count, 2)
        self.mock_shell_stdin.write.assert_called_with("a\n")

    def test_channel_to_shell_tap_empty_byte_causes_exit(self):
        """Empty byte (EOF) should cause the loop to exit."""
        self.mock_run_srv.is_set.side_effect = [True, True]
        self.mock_channel_stdio.read.side_effect = [b"", b"\n"]
        channel_to_shell_tap(
            channel_stdio=self.mock_channel_stdio,
            shell_stdin=self.mock_shell_stdin,
            shell_replied_event=self.mock_shell_replied_event,
            run_srv=self.mock_run_srv,
        )
        # Empty byte triggers break before any write
        self.mock_channel_stdio.write.assert_not_called()

    def test_channel_to_shell_tap_byte_return_other(self):
        """Check that the ChannelToShellTap object returns a character."""
        self.mock_run_srv.is_set.side_effect = [True] * 3 + [False]
        self.mock_channel_stdio.read.side_effect = [b"b", b"c", b"\n"]
        channel_to_shell_tap(
            channel_stdio=self.mock_channel_stdio,
            shell_stdin=self.mock_shell_stdin,
            shell_replied_event=self.mock_shell_replied_event,
            run_srv=self.mock_run_srv,
        )
        self.mock_channel_stdio.write.assert_any_call(b"b")
        self.mock_channel_stdio.write.assert_any_call(b"c")
        self.assertEqual(self.mock_channel_stdio.write.call_count, 3)

        self.assertEqual(self.mock_shell_stdin.write.call_count, 1)

    def test_channel_to_shell_tap_exit_run_srv(self):
        """Check that the ChannelToShellTap object exits the run_srv."""
        self.mock_run_srv.is_set.side_effect = [True, False]
        self.mock_channel_stdio.read.side_effect = [b"\x00"]
        channel_to_shell_tap(
            channel_stdio=self.mock_channel_stdio,
            shell_stdin=self.mock_shell_stdin,
            shell_replied_event=self.mock_shell_replied_event,
            run_srv=self.mock_run_srv,
        )
        self.assertEqual(self.mock_run_srv.is_set.call_count, 2)
        self.assertEqual(self.mock_channel_stdio.read.call_count, 1)


class ShellToChannelTapTest(unittest.TestCase):
    """
    Test cases for the ShellToChannelTap class.
    """

    def setUp(self):
        """Set up the ShellToChannelTap object."""
        self.mock_channel_stdio: Mock = Mock()
        self.mock_channel_stdio.closed = False
        self.mock_shell_stdout: Mock = Mock()
        self.mock_shell_replied_event: Mock = Mock()
        self.mock_run_srv: Mock = Mock()

    def test_shell_to_channel_tap_channel_stdio_closed(self):
        """Check that the ShellToChannelTap object closes the channel_stdio."""
        self.mock_channel_stdio.closed = True
        shell_to_channel_tap(
            channel_stdio=self.mock_channel_stdio,
            shell_stdout=self.mock_shell_stdout,
            shell_replied_event=self.mock_shell_replied_event,
            run_srv=self.mock_run_srv,
        )
        self.mock_run_srv.is_set.assert_called_once()

    def test_shell_to_channel_tap_shell_stdout_readline_return_none(self):
        """
        Check that the ShellToChannelTap object reads a line
        from the shell_stdout that is None.
        """
        self.mock_shell_stdout.readline.return_value = None
        shell_to_channel_tap(
            channel_stdio=self.mock_channel_stdio,
            shell_stdout=self.mock_shell_stdout,
            shell_replied_event=self.mock_shell_replied_event,
            run_srv=self.mock_run_srv,
        )
        self.mock_shell_stdout.readline.assert_called_once()
        self.mock_run_srv.is_set.assert_called_once()

    def test_shell_to_channel_tap_shell_stdout_readline_return_carry_return(self):
        """
        Check that the ShellToChannelTap object reads a line
        from the shell_stdout that is a carriage return and newline.
        """
        self.mock_run_srv.is_set.side_effect = [True, False]
        self.mock_shell_stdout.readline.return_value = "\r\n"
        shell_to_channel_tap(
            channel_stdio=self.mock_channel_stdio,
            shell_stdout=self.mock_shell_stdout,
            shell_replied_event=self.mock_shell_replied_event,
            run_srv=self.mock_run_srv,
        )
        self.mock_shell_stdout.readline.assert_called_once()
        self.mock_channel_stdio.write.assert_called_once_with(b"\r\n")

    def test_shell_to_channel_tap_shell_stdout_readline_return_newline(self):
        """
        Check that the ShellToChannelTap object reads a line
        from the shell_stdout that is a newline.
        """
        self.mock_run_srv.is_set.side_effect = [True, False]
        self.mock_shell_stdout.readline.return_value = "\n"
        shell_to_channel_tap(
            channel_stdio=self.mock_channel_stdio,
            shell_stdout=self.mock_shell_stdout,
            shell_replied_event=self.mock_shell_replied_event,
            run_srv=self.mock_run_srv,
        )
        self.mock_shell_stdout.readline.assert_called_once()
        self.mock_channel_stdio.write.assert_called_once_with(b"\r\n")

    def test_shell_to_channel_tap_shell_stdout_readline_return_other(self):
        """
        Check that the ShellToChannelTap object reads a line
        from the shell_stdout that is a character.
        """
        self.mock_run_srv.is_set.side_effect = [True, False]
        self.mock_shell_stdout.readline.return_value = "b"
        shell_to_channel_tap(
            channel_stdio=self.mock_channel_stdio,
            shell_stdout=self.mock_shell_stdout,
            shell_replied_event=self.mock_shell_replied_event,
            run_srv=self.mock_run_srv,
        )
        self.mock_shell_stdout.readline.assert_called_once()
        self.mock_channel_stdio.write.assert_called_once_with(b"b")

    def test_shell_to_channel_tap_socket_error(self):
        """Check that the ShellToChannelTap object breaks the loop if a socket error occurs."""
        self.mock_shell_stdout.readline.return_value = "b"
        self.mock_channel_stdio.write.side_effect = OSError(104, "Connection reset by peer")
        shell_to_channel_tap(
            channel_stdio=self.mock_channel_stdio,
            shell_stdout=self.mock_shell_stdout,
            shell_replied_event=self.mock_shell_replied_event,
            run_srv=self.mock_run_srv,
        )
        self.mock_run_srv.is_set.assert_called_once()

    def test_shell_to_channel_tap_set_replied_flag(self):
        """Check that the ShellToChannelTap object sets the replied flag."""
        self.mock_run_srv.is_set.side_effect = [True, False]
        self.mock_shell_stdout.readline.return_value = "b"
        shell_to_channel_tap(
            channel_stdio=self.mock_channel_stdio,
            shell_stdout=self.mock_shell_stdout,
            shell_replied_event=self.mock_shell_replied_event,
            run_srv=self.mock_run_srv,
        )
        self.mock_shell_replied_event.set.assert_called_once()

    def test_shell_to_channel_tap_exit_run_srv(self):
        """Check that the ShellToChannelTap object exits the run_srv."""
        self.mock_run_srv.is_set.side_effect = [True, False]
        self.mock_shell_stdout.readline.return_value = "b"
        shell_to_channel_tap(
            channel_stdio=self.mock_channel_stdio,
            shell_stdout=self.mock_shell_stdout,
            shell_replied_event=self.mock_shell_replied_event,
            run_srv=self.mock_run_srv,
        )
        self.assertEqual(self.mock_run_srv.is_set.call_count, 2)


class ParamikoSshServerTest(unittest.TestCase):
    """
    Test cases for the ParamikoSshServer class.
    """

    def setUp(self):
        """Set up the ParamikoSshServer tests."""
        self.arguments: dict = {
            "shell": Mock(),
            "nos": Mock(),
            "nos_inventory_config": {},
            "port": 22,
            "username": "admin",
            "password": "admin",
        }

    def test_init_with_minimum_arguments(self):
        """
        Check that the ParamikoSshServer object is initialized correctly with
        the minimum parameters needed.
        """
        paramiko_server: ParamikoSshServer = ParamikoSshServer(**self.arguments)
        self.assertEqual(paramiko_server.nos, self.arguments["nos"])
        self.assertEqual(paramiko_server.nos_inventory_config, self.arguments["nos_inventory_config"])
        self.assertEqual(paramiko_server.shell, self.arguments["shell"])
        self.assertEqual(paramiko_server.shell_configuration, {})
        self.assertEqual(paramiko_server.ssh_banner, "SIMNOS Paramiko SSH Server")
        self.assertEqual(paramiko_server.username, self.arguments["username"])
        self.assertEqual(paramiko_server.password, self.arguments["password"])
        self.assertEqual(paramiko_server.port, self.arguments["port"])
        self.assertEqual(paramiko_server.address, "127.0.0.1")
        self.assertEqual(paramiko_server.timeout, 1)
        self.assertEqual(paramiko_server.watchdog_interval, 1)
        self.assertEqual(
            paramiko_server._ssh_server_key,
            paramiko.RSAKey(file_obj=io.StringIO(DEFAULT_SSH_KEY)),
        )

    def test_init_with_ssh_key_file(self):
        """
        Check that the ParamikoSshServer object is initialized correctly with
        the ssh_key_file parameter.
        """
        paramiko_server: ParamikoSshServer = ParamikoSshServer(
            **self.arguments,
            ssh_key_file="tests/assets/ssh_host_rsa_key",
        )
        self.assertEqual(paramiko_server.nos, self.arguments["nos"])
        self.assertEqual(paramiko_server.nos_inventory_config, self.arguments["nos_inventory_config"])
        self.assertEqual(paramiko_server.shell, self.arguments["shell"])
        self.assertEqual(paramiko_server.shell_configuration, {})
        self.assertEqual(paramiko_server.ssh_banner, "SIMNOS Paramiko SSH Server")
        self.assertEqual(paramiko_server.username, self.arguments["username"])
        self.assertEqual(paramiko_server.password, self.arguments["password"])
        self.assertEqual(paramiko_server.port, self.arguments["port"])
        self.assertEqual(paramiko_server.address, "127.0.0.1")
        self.assertEqual(paramiko_server.timeout, 1)
        self.assertEqual(paramiko_server.watchdog_interval, 1)
        self.assertEqual(
            paramiko_server._ssh_server_key,
            paramiko.RSAKey(filename="tests/assets/ssh_host_rsa_key"),
        )

    def test_init_with_ssh_key_file_and_password(self):
        """
        Check that the ParamikoSshServer object is initialized correctly with
        the ssh_key_file and ssh_key_password parameters.
        """
        paramiko_server: ParamikoSshServer = ParamikoSshServer(
            **self.arguments,
            ssh_key_file="tests/assets/ssh_host_rsa_key_with_password",
            ssh_key_file_password="password",
        )
        self.assertEqual(paramiko_server.nos, self.arguments["nos"])
        self.assertEqual(paramiko_server.nos_inventory_config, self.arguments["nos_inventory_config"])
        self.assertEqual(paramiko_server.shell, self.arguments["shell"])
        self.assertEqual(paramiko_server.shell_configuration, {})
        self.assertEqual(paramiko_server.ssh_banner, "SIMNOS Paramiko SSH Server")
        self.assertEqual(paramiko_server.username, self.arguments["username"])
        self.assertEqual(paramiko_server.password, self.arguments["password"])
        self.assertEqual(paramiko_server.port, self.arguments["port"])
        self.assertEqual(paramiko_server.address, "127.0.0.1")
        self.assertEqual(paramiko_server.timeout, 1)
        self.assertEqual(paramiko_server.watchdog_interval, 1)
        self.assertEqual(
            paramiko_server._ssh_server_key,
            paramiko.RSAKey(
                filename="tests/assets/ssh_host_rsa_key_with_password",
                password="password",
            ),
        )

    def test_init_with_ssh_banner(self):
        """
        Check that the ParamikoSshServer object is initialized correctly with
        the ssh_banner parameter.
        """
        paramiko_server: ParamikoSshServer = ParamikoSshServer(
            **self.arguments,
            ssh_banner="SSH Banner",
        )
        self.assertEqual(paramiko_server.nos, self.arguments["nos"])
        self.assertEqual(paramiko_server.nos_inventory_config, self.arguments["nos_inventory_config"])
        self.assertEqual(paramiko_server.shell, self.arguments["shell"])
        self.assertEqual(paramiko_server.shell_configuration, {})
        self.assertEqual(paramiko_server.ssh_banner, "SSH Banner")
        self.assertEqual(paramiko_server.username, self.arguments["username"])
        self.assertEqual(paramiko_server.password, self.arguments["password"])
        self.assertEqual(paramiko_server.port, self.arguments["port"])
        self.assertEqual(paramiko_server.address, "127.0.0.1")
        self.assertEqual(paramiko_server.timeout, 1)
        self.assertEqual(paramiko_server.watchdog_interval, 1)
        self.assertEqual(
            paramiko_server._ssh_server_key,
            paramiko.RSAKey(file_obj=io.StringIO(DEFAULT_SSH_KEY)),
        )

    def test_init_with_shell_configuration(self):
        """
        Check that the ParamikoSshServer object is initialized correctly with
        the shell_configuration parameter.
        """
        paramiko_server: ParamikoSshServer = ParamikoSshServer(
            **self.arguments,
            shell_configuration={"shell": "configuration"},
        )
        self.assertEqual(paramiko_server.nos, self.arguments["nos"])
        self.assertEqual(paramiko_server.nos_inventory_config, self.arguments["nos_inventory_config"])
        self.assertEqual(paramiko_server.shell, self.arguments["shell"])
        self.assertEqual(paramiko_server.shell_configuration, {"shell": "configuration"})
        self.assertEqual(paramiko_server.ssh_banner, "SIMNOS Paramiko SSH Server")
        self.assertEqual(paramiko_server.username, self.arguments["username"])
        self.assertEqual(paramiko_server.password, self.arguments["password"])
        self.assertEqual(paramiko_server.port, self.arguments["port"])
        self.assertEqual(paramiko_server.address, "127.0.0.1")
        self.assertEqual(paramiko_server.timeout, 1)
        self.assertEqual(paramiko_server.watchdog_interval, 1)
        self.assertEqual(
            paramiko_server._ssh_server_key,
            paramiko.RSAKey(file_obj=io.StringIO(DEFAULT_SSH_KEY)),
        )

    def test_init_with_address(self):
        """
        Check that the ParamikoSshServer object is initialized correctly with
        the address parameter.
        """
        paramiko_server: ParamikoSshServer = ParamikoSshServer(
            **self.arguments,
            address="127.0.0.2",
        )
        self.assertEqual(paramiko_server.nos, self.arguments["nos"])
        self.assertEqual(paramiko_server.nos_inventory_config, self.arguments["nos_inventory_config"])
        self.assertEqual(paramiko_server.shell, self.arguments["shell"])
        self.assertEqual(paramiko_server.shell_configuration, {})
        self.assertEqual(paramiko_server.ssh_banner, "SIMNOS Paramiko SSH Server")
        self.assertEqual(paramiko_server.username, self.arguments["username"])
        self.assertEqual(paramiko_server.password, self.arguments["password"])
        self.assertEqual(paramiko_server.port, self.arguments["port"])
        self.assertEqual(paramiko_server.address, "127.0.0.2")
        self.assertEqual(paramiko_server.timeout, 1)
        self.assertEqual(paramiko_server.watchdog_interval, 1)
        self.assertEqual(
            paramiko_server._ssh_server_key,
            paramiko.RSAKey(file_obj=io.StringIO(DEFAULT_SSH_KEY)),
        )

    def test_init_with_timeout(self):
        """
        Check that the ParamikoSshServer object is initialized correctly with
        the timeout parameter.
        """
        paramiko_server: ParamikoSshServer = ParamikoSshServer(
            **self.arguments,
            timeout=2,
        )
        self.assertEqual(paramiko_server.nos, self.arguments["nos"])
        self.assertEqual(paramiko_server.nos_inventory_config, self.arguments["nos_inventory_config"])
        self.assertEqual(paramiko_server.shell, self.arguments["shell"])
        self.assertEqual(paramiko_server.shell_configuration, {})
        self.assertEqual(paramiko_server.ssh_banner, "SIMNOS Paramiko SSH Server")
        self.assertEqual(paramiko_server.username, self.arguments["username"])
        self.assertEqual(paramiko_server.password, self.arguments["password"])
        self.assertEqual(paramiko_server.port, self.arguments["port"])
        self.assertEqual(paramiko_server.address, "127.0.0.1")
        self.assertEqual(paramiko_server.timeout, 2)
        self.assertEqual(paramiko_server.watchdog_interval, 1)
        self.assertEqual(
            paramiko_server._ssh_server_key,
            paramiko.RSAKey(file_obj=io.StringIO(DEFAULT_SSH_KEY)),
        )

    def test_init_with_watchdog_interval(self):
        """
        Check that the ParamikoSshServer object is initialized correctly with
        the watchdog_interval parameter.
        """
        paramiko_server: ParamikoSshServer = ParamikoSshServer(
            **self.arguments,
            watchdog_interval=2,
        )
        self.assertEqual(paramiko_server.nos, self.arguments["nos"])
        self.assertEqual(paramiko_server.nos_inventory_config, self.arguments["nos_inventory_config"])
        self.assertEqual(paramiko_server.shell, self.arguments["shell"])
        self.assertEqual(paramiko_server.shell_configuration, {})
        self.assertEqual(paramiko_server.ssh_banner, "SIMNOS Paramiko SSH Server")
        self.assertEqual(paramiko_server.username, self.arguments["username"])
        self.assertEqual(paramiko_server.password, self.arguments["password"])
        self.assertEqual(paramiko_server.port, self.arguments["port"])
        self.assertEqual(paramiko_server.address, "127.0.0.1")
        self.assertEqual(paramiko_server.timeout, 1)
        self.assertEqual(paramiko_server.watchdog_interval, 2)
        self.assertEqual(
            paramiko_server._ssh_server_key,
            paramiko.RSAKey(file_obj=io.StringIO(DEFAULT_SSH_KEY)),
        )

    def test_init_with_all_parameters(self):
        """
        Check that the ParamikoSshServer object is initialized correctly with
        all the parameters.
        """
        paramiko_server: ParamikoSshServer = ParamikoSshServer(
            **self.arguments,
            ssh_banner="SSH Banner",
            shell_configuration={"shell": "configuration"},
            address="127.0.0.2",
            timeout=2,
            watchdog_interval=2,
        )
        self.assertEqual(paramiko_server.nos, self.arguments["nos"])
        self.assertEqual(paramiko_server.nos_inventory_config, self.arguments["nos_inventory_config"])
        self.assertEqual(paramiko_server.shell, self.arguments["shell"])
        self.assertEqual(paramiko_server.shell_configuration, {"shell": "configuration"})
        self.assertEqual(paramiko_server.ssh_banner, "SSH Banner")
        self.assertEqual(paramiko_server.username, self.arguments["username"])
        self.assertEqual(paramiko_server.password, self.arguments["password"])
        self.assertEqual(paramiko_server.port, self.arguments["port"])
        self.assertEqual(paramiko_server.address, "127.0.0.2")
        self.assertEqual(paramiko_server.timeout, 2)
        self.assertEqual(paramiko_server.watchdog_interval, 2)
        self.assertEqual(
            paramiko_server._ssh_server_key,
            paramiko.RSAKey(file_obj=io.StringIO(DEFAULT_SSH_KEY)),
        )

    def test_watchdog_run_srv_loop(self):
        """Check that the watchdog run_srv loop is executed."""
        paramiko_server: ParamikoSshServer = ParamikoSshServer(**self.arguments, watchdog_interval=0.01)
        mock_is_running: Mock = Mock()
        mock_run_srv: Mock = Mock()
        mock_session: Mock = Mock()
        mock_shell: Mock = Mock()
        mock_run_srv.is_set.side_effect = [True, False]
        paramiko_server.watchdog(mock_is_running, mock_run_srv, mock_session, mock_shell)
        self.assertEqual(mock_run_srv.is_set.call_count, 2)

    def test_watchdog_session_is_not_alive(self):
        """Check that the watchdog session is not alive."""
        paramiko_server: ParamikoSshServer = ParamikoSshServer(**self.arguments, watchdog_interval=0.01)
        mock_is_running: Mock = Mock()
        mock_run_srv: Mock = Mock()
        mock_session: Mock = Mock()
        mock_shell: Mock = Mock()
        mock_session.is_alive.return_value = False
        paramiko_server.watchdog(mock_is_running, mock_run_srv, mock_session, mock_shell)
        mock_session.is_alive.assert_called_once()
        mock_run_srv.is_set.assert_called_once()
        mock_shell.stop.assert_called_once()

    def test_watchdog_shell_stop_when_is_running_false(self):
        """Check that the watchdog shell is stopped when is_running is False."""
        paramiko_server: ParamikoSshServer = ParamikoSshServer(**self.arguments, watchdog_interval=0.01)
        mock_is_running: Mock = Mock()
        mock_run_srv: Mock = Mock()
        mock_session: Mock = Mock()
        mock_shell: Mock = Mock()
        mock_run_srv.is_set.side_effect = [True] * 2 + [False]
        mock_is_running.is_set.side_effect = [True] * 1 + [False]
        paramiko_server.watchdog(mock_is_running, mock_run_srv, mock_session, mock_shell)
        mock_shell.stop.assert_called_once()

    def test_watchdog_shell_stop_when_session_is_alive_false(self):
        """Check that the watchdog shell is stopped when the session is alive is False."""
        paramiko_server: ParamikoSshServer = ParamikoSshServer(**self.arguments, watchdog_interval=0.01)
        mock_is_running: Mock = Mock()
        mock_run_srv: Mock = Mock()
        mock_session: Mock = Mock()
        mock_shell: Mock = Mock()
        mock_session.is_alive.side_effect = [True] * 1 + [False]
        paramiko_server.watchdog(mock_is_running, mock_run_srv, mock_session, mock_shell)
        mock_shell.stop.assert_called_once()

    @mock.patch("simnos.plugins.servers.ssh_server_paramiko.channel_to_shell_tap")
    @mock.patch("simnos.plugins.servers.ssh_server_paramiko.shell_to_channel_tap")
    @mock.patch("paramiko.Transport")
    def test_connection_function(
        self,
        mock_transport: MagicMock,
        mock_shell_to_channel_tap: MagicMock,
        mock_channel_to_shell_tap: MagicMock,
    ):
        """Check that the connection function is executed correctly."""
        mock_client: MagicMock = MagicMock()
        mock_is_running = Mock()
        paramiko_server: ParamikoSshServer = ParamikoSshServer(**self.arguments)
        paramiko_server.connection_function(mock_client, mock_is_running)

        mock_transport.assert_called_once()
        mock_shell_to_channel_tap.assert_called_once()
        mock_channel_to_shell_tap.assert_called_once()

    @mock.patch("paramiko.Transport")
    def test_connection_function_accept_returns_none(self, mock_transport_cls: MagicMock):
        """session.accept() returning None should close session and return early."""
        mock_session = MagicMock()
        mock_session.accept.return_value = None
        mock_transport_cls.return_value = mock_session

        mock_client = MagicMock()
        mock_is_running = Mock()
        paramiko_server: ParamikoSshServer = ParamikoSshServer(**self.arguments)
        paramiko_server.connection_function(mock_client, mock_is_running)

        mock_session.accept.assert_called_once()
        mock_session.close.assert_called_once()


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
        self.arguments = {
            "shell": Mock(),
            "nos": Mock(),
            "nos_inventory_config": {},
            "port": 22,
            "username": "admin",
            "password": "admin",
        }

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
        """Correct credentials should return True."""
        server = ParamikoSshServer(**self.arguments)
        channel = self._make_channel(b"admin\radmin\r")
        result = server._channel_login(channel)
        self.assertTrue(result)

    def test_channel_login_wrong_password(self):
        """Wrong password should return False."""
        server = ParamikoSshServer(**self.arguments)
        channel = self._make_channel(b"admin\rwrong\r")
        result = server._channel_login(channel)
        self.assertFalse(result)

    def test_channel_login_wrong_username(self):
        """Wrong username should return False."""
        server = ParamikoSshServer(**self.arguments)
        channel = self._make_channel(b"wrong\radmin\r")
        result = server._channel_login(channel)
        self.assertFalse(result)

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
