"""
This module is the point of entry for server plugins in SIMNOS.

"""

from .ssh_server_asyncssh import AsyncSshServer
from .telnet_server import TelnetServer

servers_plugins = {
    "AsyncSshServer": AsyncSshServer,
    "TelnetServer": TelnetServer,
}
