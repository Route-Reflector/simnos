"""
NOS module for Cisco IOS.

Command authoring lives in the A3 platform dir (``platforms/cisco_ios/``);
this module only ships the device class whose methods back the A3
``handler:`` commands (#317 / P-2).
"""

import time

from simnos.plugins.nos.platforms_py._templates.base_template import BaseDevice


class CiscoIOS(BaseDevice):
    """
    Class that keeps track of the state of the Cisco IOS device.
    """

    def make_show_clock(self, base_prompt, current_mode, current_prompt, command):
        "Return String in format '*11:54:03.018 UTC Sat Apr 16 2022'"
        return time.strftime("*%H:%M:%S.000 %Z %a %b %d %Y")
