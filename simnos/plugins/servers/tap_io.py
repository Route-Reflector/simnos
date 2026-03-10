"""
Thread-safe StringIO subclass with blocking readline and deque buffer.

Extracted from ssh_server_paramiko.py for shared use by both
SSH and Telnet server implementations.
"""

from collections import deque
import io
import threading


class TapIO(io.StringIO):
    """
    Class to implement StringIO subclass but with blocking readline method
    and a deque to buffer lines on write.

    Uses ``collections.deque`` for thread-safe, O(1) append/pop operations
    (CPython's GIL guarantees atomicity for deque ``append``/``pop``).

    A ``threading.Condition`` is used to wake ``readline()`` immediately
    when ``write()`` adds data, eliminating the polling delay that caused
    intermittent empty output in netmiko ``send_command()`` (#87).
    """

    def __init__(self, run_srv: threading.Event, initial_value: str = "", newline: str = "\n"):
        self.lines: deque[str] = deque()
        self.run_srv: threading.Event = run_srv
        self._cond: threading.Condition = threading.Condition()
        super().__init__(initial_value, newline)

    def readline(self):
        """Block until a line is available or the server shuts down."""
        with self._cond:
            while self.run_srv.is_set():
                if self.lines:
                    return self.lines.pop()
                self._cond.wait(timeout=0.1)
        if self.lines:
            return self.lines.pop()
        return ""

    def drain(self) -> list[str]:
        """Pop all buffered lines without blocking.

        Returns a list in FIFO order (oldest first).
        """
        items: list[str] = []
        while self.lines:
            items.append(self.lines.pop())
        return items

    def write(self, value: str):
        """Append *value* to the buffer and wake any blocked ``readline()``."""
        self.lines.appendleft(value)
        with self._cond:
            self._cond.notify()


def process_tap_line(line: str) -> str:
    """Sanitise a single line from shell stdout for the network client.

    - Strips NUL bytes.
    - Converts bare ``\\n`` to ``\\r\\n`` (leaves existing ``\\r\\n`` intact).

    Shared by both SSH and Telnet tap functions.
    """
    if "\x00" in line:
        line = line.replace("\x00", "")
    if "\r\n" not in line and "\n" in line:
        line = line.replace("\n", "\r\n")
    return line
