"""
This module contains utility functions for the tests.
"""

import random
import socket
import string

from simnos.core.host import Host
from simnos.plugins.nos import nos_plugins

# Platforms where the simnos platform name differs from netmiko's device_type.
# netmiko expects its own canonical device_type string, so these must be mapped
# before building ConnectHandler kwargs (see netmiko_device()).
# netmiko canonical names: https://github.com/ktbyers/netmiko/blob/master/PLATFORMS.md
NETMIKO_DEVICE_TYPE_MAP: dict[str, str] = {
    "edgecore": "edgecore_sonic",
    "extreme_slxos": "extreme_slx",
    "watchguard_firebox": "watchguard_fireware",
}

# Default credentials used to build single-host test inventories.
TEST_USERNAME = "test_user"
TEST_PASSWORD = "test_password"


def build_inventory(
    platform: str,
    *,
    host_key: str = "device",
    username: str = TEST_USERNAME,
    password: str = TEST_PASSWORD,
    port: int | None = None,
    **extra,
) -> dict:
    """Build a single-host SimNOS inventory dict (test SSoT).

    Single-host only -- multi-host inventories are out of scope here.
    A free port is allocated when ``port`` is not given.
    """
    port = port if port is not None else get_free_port()
    host = {"username": username, "password": password, "port": port, "platform": platform, **extra}
    return {"hosts": {host_key: host}}


def creds_from_host(host: Host) -> dict:
    """Return the username/password/port a netmiko client needs to reach ``host``."""
    return {"username": host.username, "password": host.password, "port": host.port}


def netmiko_device(platform: str, creds: dict, **extra) -> dict:
    """Build netmiko ``ConnectHandler`` kwargs (applies NETMIKO_DEVICE_TYPE_MAP).

    ``**extra`` merges additional kwargs such as ``session_log``.
    """
    return {
        "host": "localhost",
        "username": creds["username"],
        "password": creds["password"],
        "port": creds["port"],
        "device_type": NETMIKO_DEVICE_TYPE_MAP.get(platform, platform),
        **extra,
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
    uses): values are lists of absolute plugin file paths, and authoring
    templates (`platforms_py/_templates/`) are already outside the registry
    glob, so no manual listdir filtering is needed here.
    """
    return sorted(p for p, files in nos_plugins.items() if any(f.endswith(".py") for f in files))


def get_host_commands(host: Host) -> tuple[list[str], list[str], list[str]]:
    """
    Get the commands of the host.
    It gets the initial, enable and config commands.
    """
    initial_commands, enable_commands, config_commands = [], [], []
    nos = host.nos
    assert nos is not None
    for command, options in nos.commands.items():
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
            if prompt == nos.initial_prompt:
                initial_commands.append(command)
            elif nos.enable_prompt and prompt == nos.enable_prompt:
                enable_commands.append(command)
            elif nos.config_prompt and prompt == nos.config_prompt:
                config_commands.append(command)
    return initial_commands, enable_commands, config_commands


def set_attr[T](obj: object, name: str, value: T) -> T:
    """Test helper: assign ``value`` to ``obj.name`` (ty-clean, no cast/B010) and return it.

    For tests only — it deliberately bypasses static type checks, so do not use
    it in production code. Tests mock attributes that are typed as methods
    (e.g. ``shell.writeline``), which ty rejects on plain assignment and ruff
    B010 rejects via ``setattr(obj, "literal", ...)``. Routing the assignment
    through this helper (variable ``name`` → not B010; ``obj: object`` → ty
    accepts) sidesteps both.

    ``value`` is generic so a single helper covers every test assignment:
    ``Mock()``, ``Mock(side_effect=...)``, a plain function, or a dict literal.

    Two call styles are both intended:
    - bound: ``wl = set_attr(shell, "writeline", Mock())`` then ``wl.assert_*``
      — the ``-> T`` return drops the access-side ``cast(Mock, ...)``.
    - bare: ``set_attr(shell, "writeline", Mock())`` — return ignored, used when
      the mock only guards a side effect (e.g. stdout=None) and is not asserted.
    """
    setattr(obj, name, value)
    return value
