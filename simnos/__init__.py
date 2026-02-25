"""
This module provides the main classes of the SimNOS library.
It provides the SimNOS class for creating a fake network
operating system and the Nos class for creating a network
operating system object.
"""

from simnos.core.nos import Nos
from simnos.core.simnos import SimNOS

__all__ = ("Nos", "SimNOS")
