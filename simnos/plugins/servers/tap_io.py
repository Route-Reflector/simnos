"""
Thread-safe StringIO subclass with blocking readline and deque buffer.

Extracted from ssh_server_paramiko.py for shared use by both
SSH and Telnet server implementations.
"""

from collections import deque
import io
import threading
import time


class TapIO(io.StringIO):
    """
    Class to implement StringIO subclass but with blocking readline method
    and a deque to buffer lines on write.

    Uses ``collections.deque`` for thread-safe, O(1) append/pop operations
    (CPython's GIL guarantees atomicity for deque ``append``/``pop``).
    """

    def __init__(self, run_srv: threading.Event, initial_value: str = "", newline: str = "\n"):
        self.lines: deque[str] = deque()
        self.run_srv: threading.Event = run_srv
        super().__init__(initial_value, newline)

    def readline(self):
        """method to readline in indefinite block mode"""
        while self.run_srv.is_set():
            if self.lines:
                return self.lines.pop()
            time.sleep(0.01)
        return None

    def write(self, value: str):
        """
        :param value: line to add to self.lines buffer
        """
        self.lines.appendleft(value)
