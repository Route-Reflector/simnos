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

from simnos.core.nos import Nos
import simnos.plugins.nos as nos_registry
from simnos.plugins.nos import nos_plugins
from tests.utils import creds_from_host

PY_ONLY_NAME = "synthetic_py_only"
PY_ONLY_MODULE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "synthetic_py_only.py"))
PY_ONLY_MARKER = "SYNTHETIC-PY-ONLY-MARKER"


@pytest.fixture
def register_py_only(monkeypatch):
    """Register the synthetic py-only platform in the registry for one test.

    Mirrors what the import-time registry does for a real py-only module:
    `nos_plugins[name] = [<p>.py]` and the name joins `available_platforms`
    (the tuple `assert_platform_supported` gates host platforms against).
    `monkeypatch` restores both on teardown.
    """
    monkeypatch.setitem(nos_plugins, PY_ONLY_NAME, [PY_ONLY_MODULE])
    monkeypatch.setattr(nos_registry, "available_platforms", (*nos_registry.available_platforms, PY_ONLY_NAME))
    return PY_ONLY_NAME


def test_py_only_platform_takes_legacy_resolved_platform_path(register_py_only):
    """A py-only NOS builds via the legacy path, not the A3 ResolvedPlatform.

    Pins the registry contract: the module's `NAME` matches the registry key
    (the filename stem), the dynamic command is loaded, and `resolved_platform`
    stays None so the shell routes it through `adapt_legacy_commands` (#277).
    """
    nos = Nos(filename=nos_plugins[PY_ONLY_NAME])
    assert nos.name == PY_ONLY_NAME
    assert nos.resolved_platform is None
    assert "show py-only" in nos.commands
    # The dynamic output is a callable handler, not a literal — the py-only
    # value proposition (dynamic behavior with no A3 statics).
    assert callable(nos.commands["show py-only"]["output"])


@pytest.mark.timeout(60)
def test_py_only_platform_serves_dynamic_command_over_wire(register_py_only, simnos_factory):
    """The registered py-only platform answers a dynamic command over the wire.

    registry → SimNOS server → netmiko session → callable-output dispatch, end
    to end. Driven with the `cisco_ios` netmiko driver (the synthetic prompts
    mirror cisco_ios); the unique marker proves the dynamic handler's return
    value reached the client unmodified (#277).
    """
    net = simnos_factory(PY_ONLY_NAME)
    host = next(iter(net.hosts.values()))
    creds = creds_from_host(host)
    device = {
        "device_type": "cisco_ios",
        "host": "localhost",
        "username": creds["username"],
        "password": creds["password"],
        "port": creds["port"],
    }
    with ConnectHandler(**device) as conn:
        output = conn.send_command("show py-only")
    assert PY_ONLY_MARKER in output
