"""
This module provides the main classes of the FakeNOS library.
It provides the FakeNOS class for creating a fake network
operating system and the Nos class for creating a network
operating system object.
"""

from simnos.core.simnos import FakeNOS
from simnos.core.nos import Nos

__all__ = ("FakeNOS", "Nos")
