"""Synthetic py-only platform for the #277 end-to-end pin.

Deliberately has NO A3 dir (`platforms/synthetic_py_only/`) — it exists only as
this module, so it exercises the registry's py-only branch
(`simnos/plugins/nos/__init__.py`, the `not in nos_plugins` append) and the
legacy `build_resolved_platform` path (`nos.resolved_platform is None` →
`adapt_legacy_commands`). That path is otherwise unexercised end to end because
every shipped platform ships an A3 dir; #266's inventory/adapter rework could
silently break it.

Prompts mirror cisco_ios so a netmiko `cisco_ios` driver can connect and drive
it (`terminal length 0` / `terminal width 511` answer netmiko's session prep).
This is NOT a shipped platform — a test injects it into the registry with
monkeypatch and removes it on teardown.
"""

from simnos.plugins.nos.platforms_py._templates.base_template import BaseDevice

NAME: str = "synthetic_py_only"
INITIAL_PROMPT: str = "{base_prompt}>"
ENABLE_PROMPT: str = "{base_prompt}#"
CONFIG_PROMPT: str = "{base_prompt}(config)#"

# The dynamic handler's return value — the test asserts this reaches the wire,
# proving registry → shell → callable-output dispatch works for a py-only NOS.
PY_ONLY_MARKER: str = "SYNTHETIC-PY-ONLY-MARKER"

# This module's own `_default_` output. Distinct from the shell's BASIC_COMMANDS
# default ("Unknown command"); the test asserts an unknown command returns THIS,
# pinning that a py-only module's `_default_` wins the legacy merge precedence.
PY_ONLY_DEFAULT: str = "% Invalid input detected at '^' marker."


class SyntheticPyOnly(BaseDevice):
    """Minimal device exposing one dynamic command for the e2e pin."""

    def make_show_marker(self, base_prompt, current_mode, current_prompt, command):
        """Return a unique marker proving the dynamic handler reached the wire."""
        return PY_ONLY_MARKER


commands = {
    "enable": {
        "output": None,
        "new_prompt": ENABLE_PROMPT,
        "help": "enter exec prompt",
        "prompt": INITIAL_PROMPT,
    },
    "show py-only": {
        "output": SyntheticPyOnly.make_show_marker,
        "help": "dynamic py-only marker command",
        "prompt": [INITIAL_PROMPT, ENABLE_PROMPT],
    },
    "_default_": {
        "output": PY_ONLY_DEFAULT,
        "help": "Output to print for unknown commands",
        "prompt": [INITIAL_PROMPT, ENABLE_PROMPT],
    },
    "terminal width 511": {
        "output": "",
        "help": "Set terminal width to 511",
        "prompt": [INITIAL_PROMPT, ENABLE_PROMPT],
    },
    "terminal length 0": {
        "output": "",
        "help": "Set terminal length to 0",
        "prompt": [INITIAL_PROMPT, ENABLE_PROMPT],
    },
}
