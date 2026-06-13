"""Top-level pytest fixtures shared across the suite.

`simnos_factory` is the auto-lifecycle counterpart to the `build_inventory`
pure function in `tests.utils`: use the factory when a test wants a started
SimNOS that is torn down automatically, and the pure function when the test
manages start/stop itself (e.g. tests that stop mid-body or pre-allocate the
port for a client before starting).
"""

import pytest

from simnos import SimNOS
from tests.utils import build_inventory


@pytest.fixture(autouse=True)
def _isolate_sys_config_env(monkeypatch):
    """Clear SimNOS sys_config env vars so the suite is hermetic (#266 / D4).

    `SimNOS.__init__` now runs `_load_sys_config` on every construction, which
    reads `SIMNOS_SYS_CONFIG` (a config-file path) and `SIMNOS_DATA_DIR`. A value
    leaking from the developer / CI shell would make `sys_config`-asserting tests
    flaky (a stray file seeds `variants_policy`, or `data_dir` defaults shift).
    Strip both by default; a test that exercises them sets them via
    `monkeypatch.setenv`, which applies after this autouse fixture.
    """
    monkeypatch.delenv("SIMNOS_SYS_CONFIG", raising=False)
    monkeypatch.delenv("SIMNOS_DATA_DIR", raising=False)


@pytest.fixture
def simnos_factory():
    """Factory fixture: start a SimNOS for a device_type, auto-stop on teardown."""
    started: list[SimNOS] = []

    def _make(device_type: str, **overrides) -> SimNOS:
        net = SimNOS(inventory=build_inventory(device_type, **overrides))
        # Register before start() so a mid-start failure (partly-started hosts)
        # is still torn down. SimNOS.stop() is a no-op for unstarted hosts.
        started.append(net)
        net.start()
        return net

    yield _make
    for net in started:
        net.stop()
