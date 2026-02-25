"""
This module is the point of entry for server plugins in SIMNOS.

"""

from .ssh_server_paramiko import ParamikoSshServer

servers_plugins = {"ParamikoSshServer": ParamikoSshServer}
