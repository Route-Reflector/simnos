"""Acceptance pins for ephemeral-port allocation (#271).

`port=0` (the `build_inventory` / default-inventory default since #271) asks the OS
to assign a free port atomically at bind time, eliminating the `get_free_port`
TOCTOU race that flaked the macOS matrix. These tests pin the observable contract:

- an ephemeral start resolves `host.port` to a real OS-assigned port and is
  reachable (SSH + Telnet — both transports read the bound port back, so a
  per-transport readback gap is caught here);
- an explicit (non-zero) port is honored verbatim — readback is a no-op, so the
  resolved port is stable across a stop→start;
- several ephemeral hosts coexist on distinct ports (the default-inventory shape);
- an explicit port that is already in use fails loudly (no silent re-pick).
"""

import socket

from netmiko import ConnectHandler
import pytest

from simnos import SimNOS
from tests.utils import build_inventory, creds_from_host, netmiko_device

_TELNET_SERVER = {"plugin": "TelnetServer", "configuration": {}}


@pytest.mark.timeout(30)
def test_ssh_ephemeral_start_resolves_real_port_and_connects():
    """port=0 → host.port is a real port (1-65535) reachable over netmiko (SSH)."""
    net = SimNOS(inventory=build_inventory("cisco_ios"))  # ephemeral
    net.start()
    try:
        host = net.hosts["device"]
        assert 0 < host.port <= 65535
        with ConnectHandler(**netmiko_device("cisco_ios", creds_from_host(host))):
            pass
    finally:
        net.stop()


@pytest.mark.timeout(30)
def test_telnet_ephemeral_start_resolves_real_port():
    """port=0 → host.port is a real, connectable port over the Telnet transport.

    A bare TCP connect is enough to prove the listener bound the resolved port (the
    full Telnet wire is exercised by the byte-parity suite); this pin specifically
    guards the telnetlib3 readback path against the asyncssh one drifting apart.
    """
    net = SimNOS(inventory=build_inventory("cisco_ios", server=_TELNET_SERVER))
    net.start()
    try:
        host = net.hosts["device"]
        assert 0 < host.port <= 65535
        with socket.create_connection(("127.0.0.1", host.port), timeout=5):
            pass
    finally:
        net.stop()


@pytest.mark.timeout(30)
def test_ephemeral_resolved_port_is_stable_across_restart():
    """An ephemeral host keeps its resolved port across stop→start (readback no-op).

    The first start resolves port 0 to a real port P; ``stop()`` does not reset
    ``host.port`` (D4), so the second start re-binds P as an explicit (non-zero)
    port and the readback returns P unchanged — proving fixed ports are honored
    verbatim, deterministically and without a TOCTOU window (same process re-binds
    its own just-released port).
    """
    net = SimNOS(inventory=build_inventory("cisco_ios"))
    net.start()
    try:
        first_port = net.hosts["device"].port
        assert 0 < first_port <= 65535
        net.stop(hosts="device")
        net.start(hosts="device")
        assert net.hosts["device"].port == first_port
    finally:
        net.stop()


@pytest.mark.timeout(30)
def test_multiple_ephemeral_hosts_get_distinct_ports():
    """Several hosts all requesting port=0 bind distinct real ports (no collision).

    Mirrors the default inventory (3 hosts, all ephemeral, #271 / M1): the allocator
    skips dedup for port 0 and the OS hands out a unique port per bind.
    """
    inventory = {
        "hosts": {
            "a": {"port": 0, "username": "u", "password": "p", "device_type": "cisco_ios"},
            "b": {"port": 0, "username": "u", "password": "p", "device_type": "cisco_ios"},
            "c": {"port": 0, "username": "u", "password": "p", "device_type": "cisco_ios"},
        }
    }
    net = SimNOS(inventory=inventory)
    net.start()
    try:
        ports = [net.hosts[name].port for name in ("a", "b", "c")]
        assert all(0 < p <= 65535 for p in ports)
        assert len(set(ports)) == 3
    finally:
        net.stop()


@pytest.mark.timeout(30)
def test_explicit_port_in_use_fails_loudly():
    """An explicit port already held by a live listener fails loudly (no silent re-pick).

    The occupying socket sets neither SO_REUSEADDR nor SO_REUSEPORT, so the SimNOS
    bind collides on every platform (even Linux, where the server's own
    SO_REUSEPORT would otherwise let two co-operating listeners share a port). This
    pins that an explicit port is never silently swapped for a free one — the
    ephemeral readback only ever resolves port 0.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as occupied:
        occupied.bind(("127.0.0.1", 0))
        occupied.listen(1)
        port = occupied.getsockname()[1]

        net = SimNOS(inventory=build_inventory("cisco_ios", port=port))
        with pytest.raises(OSError):
            net.start()
        net.stop()  # idempotent cleanup of any partial start
