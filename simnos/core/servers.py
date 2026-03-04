"""
Base model for any server implemented as a plugin. To see an example
look for simnos/plugins/servers/ssh_server_paramiko.py
"""

from abc import ABC, abstractmethod
import logging
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

    Note: We are looking to switch to socketserver as it is
    the standard library in python.
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

    def start(self):
        """
        Start Server which distributes the connections.
        It handles the creation of the socket, binding to the address and port,
        and starting the listening thread.
        """
        if self._is_running.is_set():
            return

        self._is_running.set()

        self._bind_sockets()
        self._socket.listen()

        self._listen_thread = threading.Thread(target=self._listen)
        self._listen_thread.start()

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

        self._socket.settimeout(self.timeout)
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
        self._listen_thread.join(timeout=5)
        self._socket.close()

        alive = join_threads_with_deadline(
            self._connection_threads, _STOP_DEADLINE, _PER_THREAD_JOIN
        )
        if alive:
            log.warning("%d connection thread(s) did not exit within %ds", len(alive), _STOP_DEADLINE)

    def _listen(self):
        """
        This function is constantly running if the server is running.
        It waits for a connection, and if a connection is made, it will
        call the connection function.
        """
        while self._is_running.is_set():
            try:
                client, _ = self._socket.accept()
                connection_thread = threading.Thread(
                    target=self.connection_function,
                    args=(
                        client,
                        self._is_running,
                    ),
                )
                connection_thread.start()
                self._connection_threads.append(connection_thread)
            except TimeoutError:
                pass
            finally:
                # Prune finished threads to prevent unbounded growth
                self._connection_threads = [t for t in self._connection_threads if t.is_alive()]

    @abstractmethod
    def connection_function(self, client, is_running):
        """
        This abstract method is called when a new connection
        is made. The implementation should handle the
        connection afterwards.
        """
