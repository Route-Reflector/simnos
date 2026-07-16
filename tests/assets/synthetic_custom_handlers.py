"""Handler module of the synthetic external custom platform (A3 dir + handler py).

Pairs with ``tests/assets/synthetic_custom/`` — the A3 dir authors the static
commands and a ``handler: make_show_marker`` command; this module supplies the
device class whose method backs that ref, exactly like a shipped
``platforms_py/<name>.py`` (#317 P-4: the py module is the dynamic-behavior
channel only, it authors no commands). Loaded as
``Nos(filename=[A3_DIR, THIS_FILE])`` / registry-injected by the e2e.
"""

from simnos.plugins.nos.base_device import BaseDevice

# The dynamic handler's return value — the e2e asserts this reaches the wire,
# proving registry → merge bind → handler dispatch works for a custom platform.
SYNTHETIC_MARKER: str = "SYNTHETIC-CUSTOM-MARKER"

# The A3 `_default_` output (tests/assets/synthetic_custom/commands/default.txt).
# Distinct from the shell's BASIC default ("Unknown command"); the e2e asserts an
# unknown command returns THIS, pinning that the platform's `_default_` wins the
# merge precedence. Mirrored here so the test imports one source of truth.
SYNTHETIC_DEFAULT: str = "% Invalid input detected at '^' marker."


class SyntheticCustom(BaseDevice):
    """Minimal device exposing one dynamic handler for the e2e pin."""

    def make_show_marker(self, base_prompt, current_mode, current_prompt, command):
        """Return a unique marker proving the dynamic handler reached the wire."""
        return SYNTHETIC_MARKER
