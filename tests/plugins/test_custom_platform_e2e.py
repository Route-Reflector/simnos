"""End-to-end pin for an external custom platform (A3 dir + handler py, #277 / #317 P-4).

Every shipped platform lives inside the package tree, so the registry → shell
→ wire path for a platform whose sources live OUTSIDE the package — the
"bring your own platform" story an integration user follows — is otherwise
unexercised end to end. Since #317 P-4 that story is A3-only: the custom dir
authors the commands and a co-loaded handler module supplies the dynamic
behavior (the py-only form this file used to pin no longer exists).

The synthetic platform (``tests/assets/synthetic_custom/`` +
``synthetic_custom_handlers.py``) is injected into the registry for the
duration of one test, then driven over a real netmiko session. The registry
mutation is undone on teardown (``monkeypatch``), so the registry-invariant
tests in ``tests/core/test_simnos.py`` — which run without this fixture — are
unaffected (pytest-xdist workers are separate processes too).
"""

import os

from netmiko import ConnectHandler
import pytest

from simnos import SimNOS
from simnos.core.nos import Nos
from simnos.core.pydantic_models import EPHEMERAL_PORT
import simnos.plugins.nos as nos_registry
from simnos.plugins.nos import nos_plugins
from tests.assets.synthetic_custom_handlers import SYNTHETIC_DEFAULT, SYNTHETIC_MARKER
from tests.utils import SYNTHETIC_CUSTOM_A3_DIR, SYNTHETIC_CUSTOM_HANDLERS, creds_from_host, netmiko_device

# The injection key mirrors the real registry, which keys a platform on its A3
# dir basename. The markers are imported from the handler module (single
# source); their wire-delivered values are still asserted independently over
# the channel.
CUSTOM_NAME = "synthetic_custom"
CUSTOM_A3_DIR = SYNTHETIC_CUSTOM_A3_DIR
CUSTOM_HANDLERS = SYNTHETIC_CUSTOM_HANDLERS


@pytest.fixture
def register_custom(monkeypatch):
    """Register the synthetic custom platform in the registry for one test.

    Mirrors what the import-time registry does for a real platform:
    ``nos_plugins[name] = [<a3_dir>, <handlers>.py]`` (A3 dir first, py module
    appended) and the name joins ``available_platforms`` (the tuple
    ``assert_platform_supported`` gates host platforms against). The tuple is
    re-sorted to preserve its ``tuple(sorted(nos_plugins.keys()))`` invariant
    (1st round 🦊#2). ``monkeypatch`` restores both on teardown.
    """
    monkeypatch.setitem(nos_plugins, CUSTOM_NAME, [CUSTOM_A3_DIR, CUSTOM_HANDLERS])
    monkeypatch.setattr(
        nos_registry, "available_platforms", tuple(sorted((*nos_registry.available_platforms, CUSTOM_NAME)))
    )
    return CUSTOM_NAME


def test_custom_platform_loads_a3_dir_and_handler_module(register_custom):
    """A registry entry of [A3 dir, handler py] builds the expected Nos.

    Pins the registry contract: the platform name is the A3 dir basename (the
    real registry's key), the dir loads into ``resolved_platform``, and the
    handler module contributes the ``handler:`` namespace — no legacy command
    surface is involved (#317 P-4).
    """
    nos = Nos(filename=nos_plugins[register_custom])
    # name==dir-basename pin (1st round 🐙#6): the real registry keys on the A3
    # dir basename, so comparing against the basename derived from the path
    # (not a hardcoded constant) catches a drifted dir name.
    assert nos.name == os.path.basename(CUSTOM_A3_DIR)
    assert nos.resolved_platform is not None
    assert "show marker" in nos.resolved_platform.commands
    # The dynamic command is an unbound `handler:` ref at load; the merge
    # (`build_resolved_platform`) binds it from `nos.handlers` — the custom
    # platform's dynamic-behavior channel (#317 P-1/P-4).
    assert nos.resolved_platform.commands["show marker"].output.handler_ref == "make_show_marker"
    assert "make_show_marker" in nos.handlers
    assert nos.device is not None


@pytest.mark.timeout(60)
def test_custom_platform_serves_dynamic_command_over_wire(register_custom, simnos_factory):
    """The registered custom platform answers commands over the wire.

    registry → SimNOS server → netmiko session → bound-handler dispatch, end
    to end. Driven with the `cisco_ios` netmiko driver (the synthetic prompts
    mirror cisco_ios). The unique marker proves the handler's return value
    reached the client unmodified; the unknown-command check proves the
    platform's own `_default_` wins the merge over the shell's BASIC default
    ("Unknown command"), not just that some default answered (#277,
    1st round 🦊#3).
    """
    net = simnos_factory(register_custom)
    host = next(iter(net.hosts.values()))
    device = netmiko_device("cisco_ios", creds_from_host(host))
    with ConnectHandler(**device) as conn:
        marker_output = conn.send_command("show marker")
        default_output = conn.send_command("definitely not a real command")
    assert SYNTHETIC_MARKER in marker_output
    assert SYNTHETIC_DEFAULT in default_output
    assert "Unknown command" not in default_output


def test_py_only_platform_overlay_optin_is_loud_at_start(register_custom, monkeypatch):
    """Opting a py-only (no A3 data) platform into the overlay fails loudly at start (#286).

    A py-only platform can no longer come from the packaged registry (#317 P-4
    warns and skips it), but a runtime-injected entry can still be py-only —
    this drives the real ``Host.start()`` wiring, which builds the `Nos`
    (``resolved_platform`` stays None) and then resolves the overlay root — so
    the A3-only guard must fire before the merge's own A3-required error,
    keeping the message focused on the unsatisfiable overlay opt-in (2nd round
    codex #5).
    """
    monkeypatch.setitem(nos_plugins, register_custom, [CUSTOM_HANDLERS])
    inventory = {
        "hosts": {
            "device": {
                "username": "u",
                "password": "p",
                "port": EPHEMERAL_PORT,
                "device_type": register_custom,
                "overlay": {"override_commands": "all"},
            }
        }
    }
    net = SimNOS(inventory=inventory)
    with pytest.raises(ValueError, match=r"no A3 command data.*A3 platforms only"):
        net.start()


def test_py_only_platform_is_loud_at_start(register_custom, monkeypatch):
    """A py-only registry entry (no A3 dir) fails loudly at Host.start (#317 P-4).

    The packaged registry refuses to create such an entry, but a runtime
    injection (this fixture) or an external tool can — the merge's A3-required
    guard is the backstop that keeps it fail-at-startup instead of a silently
    command-less session.
    """
    monkeypatch.setitem(nos_plugins, register_custom, [CUSTOM_HANDLERS])
    inventory = {
        "hosts": {
            "device": {
                "username": "u",
                "password": "p",
                "port": EPHEMERAL_PORT,
                "device_type": register_custom,
            }
        }
    }
    net = SimNOS(inventory=inventory)
    with pytest.raises(ValueError, match=r"has no A3 platform dir"):
        net.start()
