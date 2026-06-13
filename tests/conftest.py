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
