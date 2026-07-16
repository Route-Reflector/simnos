"""
This is a testing handler module (device class + DEFAULT_CONFIGURATION only).

Since #317 P-4 a py module supplies dynamic behavior only — the device class
(whose methods form the A3 ``handler:`` namespace) and an optional
``DEFAULT_CONFIGURATION`` constant. It authors no commands.
"""

import time

from simnos.plugins.nos.base_device import BaseDevice

DEFAULT_CONFIGURATION: str = "tests/assets/test_module.yaml.j2"


# pylint: disable=unused-argument
class TestModule(BaseDevice):
    """
    Class that keeps track of the state of the TestModule device.
    """

    def make_show_clock(self, base_prompt, current_mode, current_prompt, command):
        """Return the current time."""
        return str(time.ctime())

    def make_show_version(self, base_prompt, current_mode, current_prompt, command):
        """Return the system version."""
        return "TestModule version 1.0"
