"""
Base model for any server implemented as a plugin. To see an example
look for simnos/plugins/servers/ssh_server_paramiko.py
"""

from abc import ABC, abstractmethod
import contextlib
import logging
import selectors
import socket
import sys
import threading
import time

log = logging.getLogger(__name__)

# Timeout constants for shutdown
_SHUTDOWN_TIMEOUT = 2  # Bounded timeout (seconds) for shutdown-critical I/O paths
_STOP_DEADLINE = 10  # Total wall-clock budget for joining connection threads
_PER_THREAD_JOIN = 2  # Max join timeout per individual connection thread


def join_threads_with_deadline(
    threads: list[threading.Thread],
    total_timeout: float,
    per_thread_timeout: float,
) -> list[threading.Thread]:
    """Join threads with a total wall-clock deadline.

    Iterates over *threads*, joining each with at most *per_thread_timeout*
    seconds.  Stops early when the cumulative elapsed time exceeds
    *total_timeout*.

    :returns: list of threads that are still alive after the deadline.
    """
    deadline = time.monotonic() + total_timeout
    alive: list[threading.Thread] = []
    skipped = False
    for thread in threads:
        if not skipped:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                skipped = True
            else:
                thread.join(timeout=min(per_thread_timeout, remaining))
        if thread.is_alive():
            alive.append(thread)
    return alive


class TCPServerBase(ABC):
    """
    Base class for a TCP Server.
    It provides the methods to start and stop the server.
    """

    def __init__(self, address="localhost", port=6000, timeout=1):
        """
        Initialize the server with the address and port
        and the timeout for the socket.
        """
        self.address = address
        self.port = port
        self.timeout = timeout
        self._is_running = threading.Event()
        self._socket = None
        self.client_shell = None
        self._listen_thread = None
        self._connection_threads = []
        self._wakeup_r: socket.socket | None = None
        self._wakeup_w: socket.socket | None = None
        self._selector: selectors.BaseSelector | None = None

    def start(self):
        """
        Start Server which distributes the connections.
        It handles the creation of the socket, binding to the address and port,
        and starting the listening thread.
        """
        if self._is_running.is_set():
            return

        self._is_running.set()
        try:
            self._bind_sockets()
            self._socket.listen()

            self._wakeup_r, self._wakeup_w = socket.socketpair()
            self._wakeup_r.setblocking(False)

            self._selector = selectors.DefaultSelector()
            self._selector.register(self._socket, selectors.EVENT_READ, data="listen")
            self._selector.register(self._wakeup_r, selectors.EVENT_READ, data="wakeup")

            self._listen_thread = threading.Thread(target=self._listen)
            self._listen_thread.start()
        except Exception:
            self._cleanup_resources()
            self._is_running.clear()
            raise

    def _bind_sockets(self):
        """
        It binds the sockets to the corresponding IPs and Ports.
        In Linux and OSX it reuses the port if needed but
        not in Windows
        """
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)

        if sys.platform in ["linux"]:
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, True)

        self._socket.setblocking(False)
        self._socket.bind((self.address, self.port))

    @property
    def managed_threads(self) -> list[threading.Thread]:
        """Return all threads managed by this server (listen + connections)."""
        threads = list(self._connection_threads)
        if self._listen_thread is not None:
            threads.append(self._listen_thread)
        return threads

    def stop(self):
        """
        It stops the server joining the threads
        and closing the corresponding sockets.
        """
        if not self._is_running.is_set():
            return

        self._is_running.clear()

        if self._wakeup_w is not None:
            with contextlib.suppress(OSError):
                self._wakeup_w.send(b"\x00")

        self._listen_thread.join(timeout=2)

        try:
            alive = join_threads_with_deadline(self._connection_threads, _STOP_DEADLINE, _PER_THREAD_JOIN)
            if alive:
                log.warning(
                    "%d connection thread(s) did not exit within %ds",
                    len(alive),
                    _STOP_DEADLINE,
                )
        finally:
            self._cleanup_resources()

    def _cleanup_resources(self):
        """Safely close selector, wakeup socketpair, and listen socket."""
        if self._selector is not None:
            with contextlib.suppress(Exception):
                self._selector.close()
            self._selector = None
        if self._socket is not None:
            with contextlib.suppress(OSError):
                self._socket.close()
            self._socket = None
        for sock in (self._wakeup_r, self._wakeup_w):
            if sock is not None:
                with contextlib.suppress(OSError):
                    sock.close()
        self._wakeup_r = self._wakeup_w = None

    def _listen(self):
        """
        Wait for connections using selectors.
        A wakeup socketpair allows stop() to unblock select() instantly
        instead of waiting for the timeout to expire.
        """
        while self._is_running.is_set():
            try:
                # select(timeout=1) is a safety net. Normal shutdown is
                # signalled via the wakeup socket and returns immediately.
                events = self._selector.select(timeout=1)
            except (OSError, ValueError):
                break  # selector was closed

            # Check wakeup first: if shutdown and accept fire simultaneously,
            # skip accept and exit immediately.
            for key, _ in events:
                if key.data == "wakeup":
                    return

            # No wakeup — process accept events.
            for key, _ in events:
                if key.data == "listen":
                    try:
                        client, _ = self._socket.accept()
                    except BlockingIOError:
                        continue  # spurious wakeup
                    except OSError:
                        break  # socket was closed (shutdown path)

                    # listen socket is non-blocking, so accepted client
                    # inherits that mode (OS-dependent). Restore blocking
                    # before handing to connection_function (e.g. paramiko).
                    client.setblocking(True)

                    connection_thread = threading.Thread(
                        target=self.connection_function,
                        args=(client, self._is_running),
                    )
                    connection_thread.start()
                    self._connection_threads.append(connection_thread)

            # Prune finished threads to prevent unbounded growth
            self._connection_threads = [t for t in self._connection_threads if t.is_alive()]

    @abstractmethod
    def connection_function(self, client, is_running):
        """
        This abstract method is called when a new connection
        is made. The implementation should handle the
        connection afterwards.
        """
