"""
NOS module for Arista EOS.

Command authoring lives in the A3 platform dir (``platforms/arista_eos/``);
this module only ships the device class whose methods back the A3
``handler:`` commands (#317 / P-2).
"""

import time

from simnos.plugins.nos.base_device import BaseDevice


class AristaEOS(BaseDevice):
    """
    Class that keeps track of the state of the Arista EOS device.
    """

    def make_show_clock(self, base_prompt, current_mode, current_prompt, command):
        """Return the current time."""
        return self.render("arista_eos/show_clock.j2", time=time.strftime("%a %b %d %H:%M:%S %Y"))
