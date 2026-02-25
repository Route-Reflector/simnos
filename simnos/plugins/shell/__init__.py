"""
This module is the point of entry for shell plugins in SIMNOS.
"""

from .cmd_shell import CMDShell

shell_plugins = {"CMDShell": CMDShell}
