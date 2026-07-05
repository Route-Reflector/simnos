"""
This module contains utility functions for the tests.
"""

import os
import random
import string

from simnos.core.host import Host
from simnos.core.platform_loader import PLATFORM_META_FILENAME, _load_platform_meta
from simnos.core.pydantic_models import EPHEMERAL_PORT
from simnos.core.resolved_command import ModeDef, ResolvedPlatform, compile_template
from simnos.plugins.nos import nos_plugins

# Default credentials used to build single-host test inventories.
TEST_USERNAME = "test_user"
TEST_PASSWORD = "test_password"

# The committed synthetic external custom platform (A3 dir + handler py,
# #317 P-4) — the shared fixture platform of the cmd_shell tests and the
# custom-platform e2e. One spelling of the paths so the consumers cannot drift.
ASSETS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "assets"))
SYNTHETIC_CUSTOM_A3_DIR = os.path.join(ASSETS_DIR, "synthetic_custom")
SYNTHETIC_CUSTOM_HANDLERS = os.path.join(ASSETS_DIR, "synthetic_custom_handlers.py")


def build_synthetic_platform(mode_prompts: dict[str, str], *, initial_mode: str = "user") -> ResolvedPlatform:
    """An in-memory `ResolvedPlatform` (modes only) for synthetic-shell tests.

    Successor of the removed ``from_dict`` / ``dict_args`` test vehicles
    (#317 P-4): assign it to ``nos.resolved_platform`` and feed commands
    through the inventory inflow, or hand a native `ResolvedCommand` dict to
    `dataclasses.replace`. ``mode_prompts`` maps mode name -> jinja2 prompt
    source (e.g. ``{"user": "{{ base_prompt }}>"}``).
    """
    modes = {
        name: ModeDef(name=name, prompt_template=compile_template(source)[0]) for name, source in mode_prompts.items()
    }
    return ResolvedPlatform(modes=modes, initial_mode=initial_mode, commands={})


def netmiko_device_type_of(device_type: str) -> str:
    """Return the netmiko canonical device_type for a simnos ``device_type``.

    Replaces the old hardcoded NETMIKO_DEVICE_TYPE_MAP (#266 / D3): the
    simnos→netmiko mapping now lives in each platform's ``platform.yaml``
    (``netmiko_device_type``), the data SSoT. Falls back to ``device_type``
    itself when the platform has no A3 metadata or no explicit
    ``netmiko_device_type`` (the identity case, which is most platforms).
    """
    for path in nos_plugins.get(device_type, []):
        meta_path = os.path.join(path, PLATFORM_META_FILENAME)
        if os.path.isfile(meta_path):
            return _load_platform_meta(meta_path).netmiko_device_type or device_type
    return device_type


def build_inventory(
    device_type: str,
    *,
    host_key: str = "device",
    username: str = TEST_USERNAME,
    password: str = TEST_PASSWORD,
    port: int | None = None,
    **extra,
) -> dict:
    """Build a single-host SimNOS inventory dict (test SSoT).

    Single-host only -- multi-host inventories are out of scope here.
    Defaults to ``EPHEMERAL_PORT`` (0) when ``port`` is not given: the OS assigns a
    free port at bind time (#271), eliminating the TOCTOU race the old
    ``get_free_port`` helper carried. Read the real port back from
    ``net.hosts[host_key].port`` after ``start()`` — the inventory dict keeps 0.
    """
    port = port if port is not None else EPHEMERAL_PORT
    host = {"username": username, "password": password, "port": port, "device_type": device_type, **extra}
    return {"hosts": {host_key: host}}


def creds_from_host(host: Host) -> dict:
    """Return the username/password/secret/port a netmiko client needs to reach ``host``."""
    return {"username": host.username, "password": host.password, "secret": host.secret, "port": host.port}


def netmiko_device(device_type: str, creds: dict, **extra) -> dict:
    """Build netmiko ``ConnectHandler`` kwargs (maps the simnos ``device_type``
    to netmiko's canonical device_type via platform.yaml, #266 / D3).

    ``secret`` is the enable/sudo credential netmiko sends when driving a
    `challenge:` command's password sub-prompt (#338). It mirrors the server's
    案F resolution: an explicit ``host.secret`` when set (``is not None``, so an
    empty secret is honoured verbatim), else the login password (the fallback the
    server also uses for `auth: secret` when no secret is configured).
    ``**extra`` merges additional kwargs such as ``session_log``.
    """
    secret = creds.get("secret")
    return {
        "host": "localhost",
        "username": creds["username"],
        "password": creds["password"],
        "secret": secret if secret is not None else creds["password"],
        "port": creds["port"],
        "device_type": netmiko_device_type_of(device_type),
        **extra,
    }


def get_running_hosts(hosts: dict[str, Host]) -> dict[str, bool]:
    """
    Get the running hosts in the network.
    """
    return {host_name: host.running for host_name, host in hosts.items()}


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
    """Collect a host's per-mode runnable commands for a netmiko sweep.

    Returns ``(initial, enable, config)`` command-name lists, bucketed from the
    platform's A3 command data (`nos.resolved_platform`, the only command
    inflow since #317 P-4) by each command's resolved `modes` (empty = all
    modes, reachable from the initial mode). Aliases are already resolved into
    their target's dispatch fields by the loader, so they sweep as ordinary
    commands here (no alias concept survives in `ResolvedCommand`).

    Transition (`new_mode` / `transitions`) and exit commands are skipped
    (they change the prompt or close the session, so a flat sweep cannot run
    them safely).

    The sweep buckets only the canonical user/enable/config modes; a command
    valid in any other mode is asserted-out loudly rather than silently dropped
    from the sweep (the PR-2 "sweep silently shrank" regression, 1st round claude #5).
    """
    initial_commands, enable_commands, config_commands = [], [], []
    nos = host.nos
    assert nos is not None
    resolved = nos.resolved_platform
    assert resolved is not None, f"{nos.name}: no A3 platform data (resolved_platform is None)"
    buckets = {"user": initial_commands, "enable": enable_commands, "config": config_commands}
    for command, rc in resolved.commands.items():
        if command.startswith("_") and command.endswith("_"):
            continue
        # `transitions` is the mode-conditional successor to `new_mode` /
        # `exit` (#317 / P-1): a transitions command changes mode or closes
        # the session at dispatch time just like the static forms, so the
        # flat sweep must skip it too (e.g. arista_eos `exit`, whose user /
        # enable entries close the session — P-2 migrated it to `transitions`).
        # A `challenge:` command (#338) waits for interactive input (a password
        # prompt) and then transitions, so a non-interactive `send_command` sweep
        # would hang on it — skip it too (the netmiko enable() path exercises it).
        if rc.new_mode or rc.exit or rc.transitions or rc.challenge or command in {"exit", "quit", "logout"}:
            continue
        # Empty `modes` = valid in every mode; a flat sweep reaches it from the
        # initial mode.
        modes = rc.modes or {resolved.initial_mode}
        unknown = modes - buckets.keys()
        assert not unknown, (
            f"{nos.name}: command {command!r} is valid in non-canonical mode(s) {sorted(unknown)} "
            f"outside the netmiko sweep buckets {sorted(buckets)}; extend get_host_commands"
        )
        for mode_name, bucket in buckets.items():
            if mode_name in modes:
                bucket.append(command)
    return initial_commands, enable_commands, config_commands


def set_attr[T](obj: object, name: str, value: T) -> T:
    """Test helper: assign ``value`` to ``obj.name`` (ty-clean, no cast/B010) and return it.

    For tests only — it deliberately bypasses static type checks, so do not use
    it in production code. Tests mock attributes that are typed as methods
    (e.g. ``shell.get_files_changed``), which ty rejects on plain assignment and
    ruff B010 rejects via ``setattr(obj, "literal", ...)``. Routing the
    assignment through this helper (variable ``name`` → not B010; ``obj: object``
    → ty accepts) sidesteps both.

    ``value`` is generic so a single helper covers every test assignment:
    ``Mock()``, ``Mock(side_effect=...)``, a plain function, or a dict literal.

    Two call styles are both intended:
    - bound: ``m = set_attr(shell, "get_files_changed", Mock())`` then
      ``m.assert_*`` — the ``-> T`` return drops the access-side ``cast(Mock, ...)``.
    - bare: ``set_attr(shell.nos, "from_file", Mock(side_effect=...))`` — return
      ignored, used when the mock only drives a side effect and is not asserted.
    """
    setattr(obj, name, value)
    return value
