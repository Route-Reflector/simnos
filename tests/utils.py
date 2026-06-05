"""
This module contains utility functions for the tests.
"""

import random
import socket
import string

from simnos.core.host import Host
from simnos.plugins.nos import nos_plugins

# Mapping for platforms where simnos name differs from netmiko device_type
NETMIKO_DEVICE_TYPE_MAP: dict[str, str] = {
    "edgecore": "edgecore_sonic",
    "extreme_slxos": "extreme_slx",
    "watchguard_firebox": "watchguard_fireware",
}


def get_running_hosts(hosts: dict[str, Host]) -> dict[str, bool]:
    """
    Get the running hosts in the network.
    """
    return {host_name: host.running for host_name, host in hosts.items()}


def get_free_port():
    """Return a free port.

    Note: There is an inherent TOCTOU race between closing this socket
    and the caller binding to the returned port.  This is acceptable
    for test usage in controlled environments.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        s.bind(("", 0))
        return s.getsockname()[1]


def generate_random_string(length):
    """Generate a random string with the given length."""
    letters = string.ascii_letters
    return "".join(random.choice(letters) for i in range(length))


def get_random_available_platform():
    """Get a random available platform."""
    platforms = get_platforms_from_md()
    return random.choice(platforms)


def get_platforms_from_md() -> list[str]:
    """Get the platforms in the platforms.md file.

    Supports both list format ('- [name](link)') and
    table format ('| [name](link) | ...').
    """
    platforms = []
    with open("docs/platforms/index.md", encoding="utf-8") as file:
        for line in file:
            stripped = line.strip()
            if stripped.startswith("- [") or stripped.startswith("| ["):
                if "❌" in stripped:
                    continue
                platform = stripped.split("[")[1].split("]")[0]
                platforms.append(platform)
    return platforms


def get_py_platforms() -> list[str]:
    """Return platforms that have a Python plugin module (sorted).

    Derived from the `nos_plugins` registry (the same source the server
    uses): values are lists of absolute plugin file paths, and
    `base_template.py` is already excluded at registry build time, so
    no manual listdir filtering is needed here.
    """
    return sorted(p for p, files in nos_plugins.items() if any(f.endswith(".py") for f in files))


def get_host_commands(host: Host) -> tuple[list[str], list[str], list[str]]:
    """
    Get the commands of the host.
    It gets the initial, enable and config commands.
    """
    initial_commands, enable_commands, config_commands = [], [], []
    for command, options in host.nos.commands.items():
        if command.startswith("_") and command.endswith("_"):
            continue
        if "prompt" not in options:
            continue
        prompts = options["prompt"]
        new_prompt = options.get("new_prompt")
        if new_prompt or "alias" in options or options.get("exit") or command in {"exit", "quit", "logout"}:
            continue
        if isinstance(prompts, str):
            prompts = [prompts]
        for prompt in prompts:
            if prompt == host.nos.initial_prompt:
                initial_commands.append(command)
            elif host.nos.enable_prompt and prompt == host.nos.enable_prompt:
                enable_commands.append(command)
            elif host.nos.config_prompt and prompt == host.nos.config_prompt:
                config_commands.append(command)
    return initial_commands, enable_commands, config_commands
