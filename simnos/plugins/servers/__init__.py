"""
This module is the point of entry for server plugins in SIMNOS.

"""

from .ssh_server_paramiko import ParamikoSshServer
from .telnet_server import TelnetServer

servers_plugins = {
    "ParamikoSshServer": ParamikoSshServer,
    "TelnetServer": TelnetServer,
}
