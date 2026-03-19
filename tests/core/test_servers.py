"""
Test module for simnos.core.servers.
The file can be found under simnos/core/servers.py
"""

import socket
import sys
import threading
import unittest
from unittest.mock import MagicMock, patch

import pytest

from simnos.core.servers import TCPServerBase


class StubServer(TCPServerBase):
    """
    StubServer class that inherits from TCPServerBase
    to test the abstract class.
    """

    def __init__(self):
        super().__init__()
        self.timeout = 1
        self.address = "127.0.0.1"
        self.port = 22

    def connection_function(self, client, is_running):
        pass


class ServersTest(unittest.TestCase):
    """
    Test class for the TCPServerBase class.
    """

    @patch("threading.Event")
    def test_init(self, mock_thread_event):
        """
        Test that the init method works as
        expected creating the needed threads.
        """
        servers = StubServer()

        assert servers._is_running == mock_thread_event.return_value
        mock_thread_event.assert_called_once()
        assert servers._socket is None
        assert servers.client_shell is None
        assert servers._listen_thread is None
        assert not servers._connection_threads
        assert servers._wakeup_r is None
        assert servers._wakeup_w is None
        assert servers._selector is None

    @patch("threading.Event")
    @patch("threading.Thread")
    @patch("simnos.core.servers.TCPServerBase._bind_sockets")
    @patch("simnos.core.servers.socket.socketpair")
    @patch("simnos.core.servers.selectors.DefaultSelector")
    def test_start_executed_without_arguments(
        self,
        mock_selector_cls,
        mock_socketpair,
        mock_bind_sockets,
        mock_thread,
        mock_thread_event,
    ):
        """
        It passes if the start can be executed correctly
        if no arguments are given.
        """
        mock_thread_event().is_set.return_value = False
        mock_socket = MagicMock()
        mock_wakeup_r = MagicMock()
        mock_wakeup_w = MagicMock()
        mock_socketpair.return_value = (mock_wakeup_r, mock_wakeup_w)

        servers = StubServer()
        servers._socket = mock_socket
        servers.start()

        mock_bind_sockets.assert_called_once()
        mock_socket.listen.assert_called_once()
        mock_thread_event().set.assert_called_once()
        mock_socketpair.assert_called_once()
        mock_wakeup_r.setblocking.assert_called_once_with(False)
        mock_selector_cls.assert_called_once()
        mock_thread.assert_called_once_with(target=servers._listen)
        mock_thread().start.assert_called_once()

    @patch("threading.Event")
    def test_start_does_not_execute_thread_if_running(self, mock_thread_event):
        """
        It passes if the start does not execute the
        thread if the server is already running.
        """
        mock_thread_event().is_set.return_value = True

        servers = StubServer()
        servers.start()

        mock_thread_event().set.assert_not_called()

    @pytest.mark.skipif(sys.platform == "win32", reason="Test only works in Linux")
    @patch("socket.socket")
    @patch("sys.platform", "linux")
    def test_bind_sockets_works_in_linux(self, mock_socket):
        """
        It passes if the socket is created and the
        setsockopt is called with the right parameters
        in Linux.
        """
        servers = StubServer()
        servers._bind_sockets()

        mock_socket.assert_called_once_with(socket.AF_INET, socket.SOCK_STREAM)
        mock_socket().setsockopt.assert_any_call(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        mock_socket().setsockopt.assert_any_call(socket.SOL_SOCKET, socket.SO_REUSEPORT, True)
        mock_socket().setblocking.assert_called_once_with(False)
        mock_socket().bind.assert_called_once_with((servers.address, servers.port))

    @patch("socket.socket")
    @patch("sys.platform", "darwin")
    def test_bind_sockets_works_in_osx(self, mock_socket):
        """
        It passes if the socket is created and the
        setsockopt is called with the right parameters
        in OSX.
        """
        servers = StubServer()
        servers._bind_sockets()

        mock_socket.assert_called_once_with(socket.AF_INET, socket.SOCK_STREAM)
        mock_socket().setsockopt.assert_any_call(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        mock_socket().setblocking.assert_called_once_with(False)
        mock_socket().bind.assert_called_once_with((servers.address, servers.port))

    @patch("socket.socket")
    @patch("sys.platform", "win32")
    def test_bind_sockets_works_in_windows(self, mock_socket):
        """
        It passes if the socket is created and the
        setsockopt is called with the right parameters
        in Windows.
        """
        servers = StubServer()
        servers._bind_sockets()

        mock_socket.assert_called_once_with(socket.AF_INET, socket.SOCK_STREAM)
        mock_socket().setsockopt.assert_called_once_with(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        mock_socket().setblocking.assert_called_once_with(False)
        mock_socket().bind.assert_called_once_with((servers.address, servers.port))

    @patch("threading.Event")
    def test_stop_works_does_not_stop_if_not_running(self, mock_thread_event):
        """
        It passes if the functions exits correctly when
        the is_running flag is set to false.
        """
        mock_thread_event().is_set.return_value = False

        servers = StubServer()
        servers.stop()

        mock_thread_event().clear.assert_not_called()

    @patch("threading.Event")
    @patch("threading.Thread")
    @patch("socket.socket")
    def test_stop_works_stop_if_running_is_set(self, mock_socket, mock_thread, mock_thread_event):
        """
        It passes if the functions exits correctly when
        the is_running flag is still set to true.
        """
        mock_thread_event().is_set.return_value = True
        servers = StubServer()
        servers._listen_thread = mock_thread()
        servers._socket = mock_socket()
        servers._wakeup_w = MagicMock()
        servers._wakeup_r = MagicMock()
        servers._selector = MagicMock()
        servers.stop()

        mock_thread_event().clear.assert_called_once()

    @patch("threading.Event")
    @patch("threading.Thread")
    @patch("socket.socket")
    def test_stop_works_closing_sockets(self, mock_socket, mock_thread, mock_thread_event):
        """
        It passes if the sockets have the close() being
        called.
        """
        mock_thread_event().is_set.return_value = True
        servers = StubServer()
        servers._listen_thread = mock_thread()
        servers._socket = mock_socket()
        mock_wakeup_w = MagicMock()
        mock_wakeup_r = MagicMock()
        servers._wakeup_w = mock_wakeup_w
        servers._wakeup_r = mock_wakeup_r
        servers._selector = MagicMock()

        servers.stop()
        mock_socket().close.assert_called_once()
        mock_wakeup_w.close.assert_called_once()
        mock_wakeup_r.close.assert_called_once()

    @patch("threading.Event")
    @patch("threading.Thread")
    @patch("socket.socket")
    def test_stop_sends_wakeup(self, mock_socket, mock_thread, mock_thread_event):
        """Stop should send a wakeup byte to unblock select()."""
        mock_thread_event().is_set.return_value = True
        servers = StubServer()
        servers._listen_thread = mock_thread()
        servers._socket = mock_socket()
        mock_wakeup_w = MagicMock()
        servers._wakeup_w = mock_wakeup_w
        servers._wakeup_r = MagicMock()
        servers._selector = MagicMock()

        servers.stop()
        mock_wakeup_w.send.assert_called_once_with(b"\x00")

    @patch("threading.Event")
    @patch("threading.Thread")
    @patch("socket.socket")
    def test_stop_works_joining_threads(self, mock_socket, mock_thread, mock_thread_event):
        """
        It passes if the connection threads are joined
        after the program is interrupted.
        """
        mock_thread_event().is_set.return_value = True
        servers = StubServer()
        servers._listen_thread = mock_thread()
        servers._socket = mock_socket()
        servers._wakeup_w = MagicMock()
        servers._wakeup_r = MagicMock()
        servers._selector = MagicMock()

        # Add mock connection threads so the join loop is exercised
        mock_conn_thread1 = MagicMock()
        mock_conn_thread2 = MagicMock()
        servers._connection_threads = [mock_conn_thread1, mock_conn_thread2]

        servers.stop()
        mock_conn_thread1.join.assert_called_once_with(timeout=2)
        mock_conn_thread2.join.assert_called_once_with(timeout=2)

    @patch("threading.Event")
    @patch("socket.socket")
    def test_stop_deadline_caps_join_time(self, mock_socket, mock_thread_event):
        """Deadline should cap total join time: threads past deadline are skipped."""
        mock_thread_event().is_set.return_value = True
        servers = StubServer()
        servers._listen_thread = MagicMock()
        servers._socket = mock_socket()
        servers._wakeup_w = MagicMock()
        servers._wakeup_r = MagicMock()
        servers._selector = MagicMock()

        # Create 5 mock connection threads
        mock_threads = [MagicMock() for _ in range(5)]
        servers._connection_threads = mock_threads

        # Mock time.monotonic to simulate deadline expiration after 2nd thread
        call_count = [0]
        base_time = 1000.0

        def mock_monotonic():
            call_count[0] += 1
            if call_count[0] == 1:
                return base_time  # deadline = base_time + 10
            if call_count[0] <= 3:
                return base_time + 3  # remaining = 7 (within deadline)
            return base_time + 11  # past deadline

        with patch("simnos.core.servers.time.monotonic", side_effect=mock_monotonic):
            servers.stop()

        # First 2 threads should have been joined, rest skipped
        mock_threads[0].join.assert_called_once()
        mock_threads[1].join.assert_called_once()
        mock_threads[2].join.assert_not_called()
        mock_threads[3].join.assert_not_called()
        mock_threads[4].join.assert_not_called()

    def test_stop_cleanup_resources_on_exception(self):
        """_cleanup_resources should run even if join_threads raises."""
        servers = StubServer()
        servers._is_running.set()
        servers._listen_thread = MagicMock()
        servers._socket = MagicMock()
        servers._wakeup_w = MagicMock()
        servers._wakeup_r = MagicMock()
        servers._selector = MagicMock()

        # Simulate an exception in join_threads_with_deadline
        bad_thread = MagicMock()
        bad_thread.join.side_effect = RuntimeError("unexpected")
        servers._connection_threads = [bad_thread]

        with pytest.raises(RuntimeError, match="unexpected"):
            servers.stop()

        # Resources should still be cleaned up
        assert servers._socket is None
        assert servers._selector is None
        assert servers._wakeup_r is None
        assert servers._wakeup_w is None


class ListenSelectorsTest(unittest.TestCase):
    """Tests for the selectors-based _listen() method."""

    def _make_server_with_selector(self, events_sequence):
        """Helper to create a StubServer with a mocked selector."""
        servers = StubServer()
        servers._is_running = threading.Event()
        servers._is_running.set()
        servers._socket = MagicMock()
        servers._selector = MagicMock()
        servers._selector.select.side_effect = events_sequence
        return servers

    def test_listen_wakeup_exits_immediately(self):
        """_listen should return immediately when wakeup event is received."""
        wakeup_key = MagicMock()
        wakeup_key.data = "wakeup"

        servers = self._make_server_with_selector([[(wakeup_key, None)]])
        servers._listen()

        servers._selector.select.assert_called_once_with(timeout=1)
        servers._socket.accept.assert_not_called()

    def test_listen_accept_creates_thread(self):
        """_listen should create a connection thread on accept event."""
        listen_key = MagicMock()
        listen_key.data = "listen"

        mock_client = MagicMock()
        servers = self._make_server_with_selector(
            [
                [(listen_key, None)],  # first iteration: accept
            ]
        )
        servers._socket.accept.return_value = (mock_client, ("127.0.0.1", 12345))
        # Stop after first iteration
        servers._is_running.is_set = MagicMock(side_effect=[True, False])

        with patch("threading.Thread") as mock_thread:
            servers._listen()

        mock_client.setblocking.assert_called_once_with(True)
        mock_thread.assert_called_once_with(
            target=servers.connection_function,
            args=(mock_client, servers._is_running),
        )
        mock_thread().start.assert_called_once()

    def test_listen_setblocking_before_thread_start(self):
        """client.setblocking(True) must be called before thread.start()."""
        listen_key = MagicMock()
        listen_key.data = "listen"

        mock_client = MagicMock()
        call_order = []
        mock_client.setblocking.side_effect = lambda v: call_order.append("setblocking")

        servers = self._make_server_with_selector([[(listen_key, None)]])
        servers._socket.accept.return_value = (mock_client, ("127.0.0.1", 12345))
        servers._is_running.is_set = MagicMock(side_effect=[True, False])

        with patch("threading.Thread") as mock_thread:
            mock_thread().start.side_effect = lambda: call_order.append("thread_start")
            servers._listen()

        assert call_order == ["setblocking", "thread_start"]

    def test_listen_wakeup_takes_priority_over_accept(self):
        """When both wakeup and listen fire, wakeup should win."""
        wakeup_key = MagicMock()
        wakeup_key.data = "wakeup"
        listen_key = MagicMock()
        listen_key.data = "listen"

        servers = self._make_server_with_selector(
            [
                [(listen_key, None), (wakeup_key, None)],
            ]
        )
        servers._listen()

        servers._socket.accept.assert_not_called()

    def test_listen_blocking_io_error_continues(self):
        """BlockingIOError on accept should continue the loop."""
        listen_key = MagicMock()
        listen_key.data = "listen"

        servers = self._make_server_with_selector(
            [
                [(listen_key, None)],
                [(listen_key, None)],
            ]
        )
        servers._socket.accept.side_effect = [BlockingIOError, MagicMock()]
        # Patch accept to return properly on second call
        mock_client = MagicMock()
        servers._socket.accept.side_effect = [BlockingIOError, (mock_client, ("127.0.0.1", 12345))]
        servers._is_running.is_set = MagicMock(side_effect=[True, True, False])

        with patch("threading.Thread"):
            servers._listen()

        assert servers._socket.accept.call_count == 2

    def test_listen_os_error_breaks(self):
        """OSError on accept (socket closed) should break the loop."""
        listen_key = MagicMock()
        listen_key.data = "listen"

        servers = self._make_server_with_selector([[(listen_key, None)]])
        servers._socket.accept.side_effect = OSError("socket closed")
        servers._is_running.is_set = MagicMock(side_effect=[True, False])

        servers._listen()

        servers._socket.accept.assert_called_once()

    def test_listen_selector_closed_breaks(self):
        """ValueError from select (selector closed) should break the loop."""
        servers = self._make_server_with_selector([ValueError("selector closed")])

        servers._listen()

        servers._selector.select.assert_called_once()

    def test_listen_empty_events_continues(self):
        """Empty events (timeout) should loop back."""
        servers = self._make_server_with_selector(
            [
                [],  # timeout, no events
                [],  # timeout again
            ]
        )
        servers._is_running.is_set = MagicMock(side_effect=[True, True, False])

        servers._listen()

        assert servers._selector.select.call_count == 2


class StartFailureRollbackTest(unittest.TestCase):
    """Tests for start() failure rollback."""

    @patch("simnos.core.servers.selectors.DefaultSelector")
    @patch("simnos.core.servers.socket.socketpair")
    @patch("simnos.core.servers.TCPServerBase._bind_sockets")
    def test_start_rollback_on_socketpair_failure(self, mock_bind_sockets, mock_socketpair, mock_selector_cls):
        """If socketpair() fails, resources should be cleaned up."""
        mock_socketpair.side_effect = OSError("socketpair failed")
        servers = StubServer()
        servers._socket = MagicMock()  # simulate _bind_sockets success

        with pytest.raises(OSError, match="socketpair failed"):
            servers.start()

        assert not servers._is_running.is_set()
        assert servers._selector is None
        assert servers._wakeup_r is None
        assert servers._wakeup_w is None

    @patch("simnos.core.servers.selectors.DefaultSelector")
    @patch("simnos.core.servers.socket.socketpair")
    @patch("simnos.core.servers.TCPServerBase._bind_sockets")
    def test_start_rollback_on_selector_failure(self, mock_bind_sockets, mock_socketpair, mock_selector_cls):
        """If selector.register() fails, resources should be cleaned up."""
        mock_wakeup_r = MagicMock()
        mock_wakeup_w = MagicMock()
        mock_socketpair.return_value = (mock_wakeup_r, mock_wakeup_w)
        mock_selector_cls().register.side_effect = [None, OSError("register failed")]

        servers = StubServer()
        servers._socket = MagicMock()

        with pytest.raises(OSError, match="register failed"):
            servers.start()

        assert not servers._is_running.is_set()
        mock_wakeup_r.close.assert_called()
        mock_wakeup_w.close.assert_called()
