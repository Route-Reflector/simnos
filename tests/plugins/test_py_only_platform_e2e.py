"""End-to-end pin for a py-only platform (#277).

Every shipped platform ships an A3 dir (`platforms/<p>/`), so the
registry → shell → wire path for a platform that is ONLY a
`platforms_py/<p>.py` module — no A3 dir — is otherwise unexercised end to end.
That path is the legacy `build_resolved_platform` branch
(`nos.resolved_platform is None` → `adapt_legacy_commands`), which #266's
inventory/adapter rework could silently break.

A synthetic py-only platform (`tests/assets/synthetic_py_only.py`) is injected
into the registry for the duration of one test, then driven over a real netmiko
session. The registry mutation is undone on teardown (`monkeypatch`), so the
registry-invariant tests in `tests/core/test_simnos.py` — which run without this
fixture — are unaffected (pytest-xdist workers are separate processes too).
"""

import os

from netmiko import ConnectHandler
import pytest

from simnos import SimNOS
from simnos.core.nos import Nos
import simnos.plugins.nos as nos_registry
from simnos.plugins.nos import nos_plugins
from tests.assets.synthetic_py_only import PY_ONLY_DEFAULT, PY_ONLY_MARKER
from tests.utils import creds_from_host, get_free_port, netmiko_device

# The injection key mirrors the real registry, which keys a py-only module on
# its filename stem. The markers are imported from the asset (single source);
# their wire-delivered values are still asserted independently over the channel.
PY_ONLY_NAME = "synthetic_py_only"
PY_ONLY_MODULE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "synthetic_py_only.py"))


@pytest.fixture
def register_py_only(monkeypatch):
    """Register the synthetic py-only platform in the registry for one test.

    Mirrors what the import-time registry does for a real py-only module:
    `nos_plugins[name] = [<p>.py]` and the name joins `available_platforms`
    (the tuple `assert_platform_supported` gates host platforms against). The
    tuple is re-sorted to preserve its `tuple(sorted(nos_plugins.keys()))`
    invariant (1st round 🦊#2). `monkeypatch` restores both on teardown.
    """
    monkeypatch.setitem(nos_plugins, PY_ONLY_NAME, [PY_ONLY_MODULE])
    monkeypatch.setattr(
        nos_registry, "available_platforms", tuple(sorted((*nos_registry.available_platforms, PY_ONLY_NAME)))
    )
    return PY_ONLY_NAME


def test_py_only_platform_takes_legacy_resolved_platform_path(register_py_only):
    """A py-only NOS builds via the legacy path, not the A3 ResolvedPlatform.

    Pins the registry contract: the module's `NAME` matches the filename stem
    (the real registry's key), the dynamic command is loaded, and
    `resolved_platform` stays None so the shell routes it through
    `adapt_legacy_commands` (#277).
    """
    nos = Nos(filename=nos_plugins[register_py_only])
    # NAME==stem pin (1st round 🐙#6): the real registry keys on the filename
    # stem, so the module's NAME must equal it — comparing against the stem
    # derived from the path (not a hardcoded constant) catches a typo'd NAME.
    assert nos.name == os.path.basename(PY_ONLY_MODULE).removesuffix(".py")
    assert nos.resolved_platform is None
    assert "show py-only" in nos.commands
    # The dynamic output is a callable handler, not a literal — the py-only
    # value proposition (dynamic behavior with no A3 statics).
    assert callable(nos.commands["show py-only"]["output"])
    # The 3 scalar prompts the legacy adapter consumes (build_resolved_platform
    # passes exactly these to adapt_legacy_commands) are wired from the module.
    assert nos.initial_prompt == "{base_prompt}>"
    assert nos.enable_prompt == "{base_prompt}#"
    assert nos.config_prompt == "{base_prompt}(config)#"


@pytest.mark.timeout(60)
def test_py_only_platform_serves_dynamic_command_over_wire(register_py_only, simnos_factory):
    """The registered py-only platform answers commands over the wire.

    registry → SimNOS server → netmiko session → callable-output dispatch, end
    to end. Driven with the `cisco_ios` netmiko driver (the synthetic prompts
    mirror cisco_ios). The unique marker proves the dynamic handler's return
    value reached the client unmodified; the unknown-command check proves the
    module's own `_default_` wins the legacy merge over the shell's BASIC
    default ("Unknown command"), not just that some default answered (#277,
    1st round 🦊#3).
    """
    net = simnos_factory(register_py_only)
    host = next(iter(net.hosts.values()))
    device = netmiko_device("cisco_ios", creds_from_host(host))
    with ConnectHandler(**device) as conn:
        marker_output = conn.send_command("show py-only")
        default_output = conn.send_command("definitely not a real command")
    assert PY_ONLY_MARKER in marker_output
    assert PY_ONLY_DEFAULT in default_output
    assert "Unknown command" not in default_output


def test_py_only_platform_overlay_optin_is_loud_at_start(register_py_only):
    """Opting a py-only (legacy) platform into the overlay fails loudly at start (#286).

    Complements the direct `_resolve_overlay_root` unit test: this drives the real
    `Host.start()` wiring, which builds the `Nos` (resolved_platform stays None for
    py-only) and then resolves the overlay root — so the A3-only guard must fire
    before the server is built, never silently serving the packaged output (the
    legacy `build_resolved_platform` branch drops the overlay layer). Pins the
    firing path against a future reorder of `Host.start` (2nd round codex #5).
    """
    inventory = {
        "hosts": {
            "device": {
                "username": "u",
                "password": "p",
                "port": get_free_port(),
                "device_type": register_py_only,
                "overlay": {"override_commands": "all"},
            }
        }
    }
    net = SimNOS(inventory=inventory)
    with pytest.raises(ValueError, match=r"legacy / py-only.*A3 platforms only"):
        net.start()
