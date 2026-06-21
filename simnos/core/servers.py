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

from simnos.core.timeouts import (
    SHUTDOWN_IO_TIMEOUT,
    SHUTDOWN_SERVER_PER_THREAD_JOIN,
    SHUTDOWN_SERVER_STOP_DEADLINE,
)

log = logging.getLogger(__name__)


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
        and the safety-net timeout for select() (seconds).
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
            # _bind_sockets() assigns self._socket; narrow for ty.
            assert self._socket is not None  # noqa: S101 — post-condition of _bind_sockets
            self._socket.listen()

            self._wakeup_r, self._wakeup_w = socket.socketpair()
            self._wakeup_r.setblocking(False)

            self._selector = selectors.DefaultSelector()
            self._selector.register(self._socket, selectors.EVENT_READ, data="listen")
            self._selector.register(self._wakeup_r, selectors.EVENT_READ, data="wakeup")

            self._listen_thread = threading.Thread(target=self._listen)
            self._listen_thread.start()
        except BaseException:
            # BaseException, not Exception: a KeyboardInterrupt mid-start (the
            # operator aborts startup) must still roll the partial start back.
            # Mirror stop()'s teardown ORDER — signal the listen loop to stop
            # (clear the flag + wake select()), join the listen thread, THEN
            # close sockets — so a listen thread that already spawned does not
            # race `_cleanup_resources()` closing the selector/socket out from
            # under its `select()` loop. `_signal_listen_stop()` clearing
            # `_is_running` first also guarantees a later stop() early-returns
            # instead of tripping its `_listen_thread is not None` assertion.
            #
            # `_cleanup_resources()` runs in a `finally` so the sockets are freed
            # even if the clear/wake/join is cut short by a second interrupt. The
            # `is_alive()` guard is required: if `start()` itself raised, the
            # thread object exists but was never started, and joining an
            # unstarted thread raises RuntimeError — which would mask the
            # original error and skip cleanup (#291). We re-raise immediately.
            try:
                self._signal_listen_stop()
                if self._listen_thread is not None and self._listen_thread.is_alive():
                    self._listen_thread.join(timeout=SHUTDOWN_IO_TIMEOUT)
            finally:
                self._cleanup_resources()
            raise

    def _signal_listen_stop(self):
        """Signal the listen loop to stop: clear the running flag and wake select().

        Shared by stop() and start()'s rollback — the one byte sent over the
        wakeup socketpair unblocks the listen thread's select() instantly
        instead of waiting out the safety-net timeout. The caller is responsible
        for joining the listen thread afterwards (the join differs between the
        two paths: stop() asserts the thread exists, the rollback guards on
        is_alive() because start() may have raised before the thread started).

        The wakeup send is best-effort: a broken wakeup socket must not stop
        shutdown — the caller still falls back to the SHUTDOWN_IO_TIMEOUT-bounded
        join. The OSError is logged at debug rather than suppressed silently so a
        slow shutdown (select() exiting via timeout instead of the wakeup) leaves
        a diagnostic breadcrumb (#294).
        """
        self._is_running.clear()
        if self._wakeup_w is not None:
            try:
                self._wakeup_w.send(b"\x00")
            except OSError:
                log.debug("wakeup send failed; listen thread will exit via select() timeout", exc_info=True)

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

        # `_signal_listen_stop()` (clear + wakeup) + the thread joins all run
        # under the cleanup try/finally so `_cleanup_resources()` still frees the
        # sockets if an interrupt lands anywhere in the teardown. Clearing inside
        # the try also means a retry stop() (which only proceeds while
        # `_is_running` is set) can still clean up after an interrupted attempt
        # (#291, symmetric with start()'s rollback).
        try:
            self._signal_listen_stop()

            # fail-safe join — wakeup socket may have failed; bound by SHUTDOWN_IO_TIMEOUT.
            # _is_running.is_set() guard at the top of stop() returns early if start()
            # hasn't been called, so self._listen_thread is set here; narrow for ty.
            assert self._listen_thread is not None  # noqa: S101 — post-condition of start()
            self._listen_thread.join(timeout=SHUTDOWN_IO_TIMEOUT)

            alive = join_threads_with_deadline(
                self._connection_threads,
                SHUTDOWN_SERVER_STOP_DEADLINE,
                SHUTDOWN_SERVER_PER_THREAD_JOIN,
            )
            if alive:
                log.warning(
                    "%d connection thread(s) did not exit within %ds",
                    len(alive),
                    SHUTDOWN_SERVER_STOP_DEADLINE,
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
        # _listen only runs from the thread started by start(), where both
        # self._socket and self._selector are non-None; narrow for ty.
        assert self._selector is not None  # noqa: S101 — post-condition of start()
        assert self._socket is not None  # noqa: S101 — post-condition of start()
        while self._is_running.is_set():
            try:
                # select(timeout) is a safety net. Normal shutdown is
                # signalled via the wakeup socket and returns immediately.
                events = self._selector.select(timeout=self.timeout)
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
