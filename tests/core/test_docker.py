"""
Module tests for compatibility with Docker containers.
"""

# pylint: disable=unused-argument
import logging
import os
import socket
import subprocess
import time

from netmiko import ConnectHandler
import paramiko
import pytest

# Readiness polling completes a few SSH handshakes before the server is up,
# which paramiko logs as noisy banner-read tracebacks; silence them.
logging.getLogger("paramiko.transport").setLevel(logging.CRITICAL)

IN_GITHUB_ACTIONS: bool = os.getenv("GITHUB_ACTIONS") is not None

router1 = {
    "device_type": "cisco_ios",
    "host": "localhost",
    "username": "user",
    "password": "user",
    "port": 12723,
}

router2 = {
    "device_type": "cisco_ios",
    "host": "localhost",
    "username": "user",
    "password": "user",
    "port": 12724,
}


def _skip_docker_tests() -> bool:
    """Return True if Docker tests should be skipped."""
    if IN_GITHUB_ACTIONS:
        return True
    try:
        subprocess.run(
            ["docker", "info"],
            check=True,
            capture_output=True,
        )
        return False
    except (subprocess.CalledProcessError, FileNotFoundError):
        return True


def _wait_for_ssh(host, port, timeout=30, interval=0.3):
    """Wait until the container's SSH server can complete a protocol banner exchange.

    A published Docker port is accepted by the proxy the instant the container
    starts — long before SIMNOS binds and starts speaking SSH inside it (host
    key generation + platform load take ~2s). A plain TCP probe therefore
    returns far too early and the test connects before the server is ready
    ("Error reading SSH protocol banner"). Probe an actual SSH handshake so the
    test proceeds only once the server can serve one.
    """
    deadline = time.monotonic() + timeout
    last_err: Exception | None = None
    while time.monotonic() < deadline:
        try:
            sock = socket.create_connection((host, port), timeout=2)
        except OSError as e:
            last_err = e
            time.sleep(interval)
            continue
        transport = paramiko.Transport(sock)
        try:
            transport.start_client(timeout=3)
            return
        except Exception as e:  # banner not ready yet / connection reset
            last_err = e
            time.sleep(interval)
        finally:
            transport.close()
    raise TimeoutError(f"SSH on {host}:{port} not ready after {timeout}s ({last_err})")


@pytest.fixture
def setup():
    """Starts the docker containers."""
    try:
        subprocess.run(
            ["docker", "compose", "-f", "docker/docker-compose.yaml", "up", "-d"],
            check=True,
        )
        _wait_for_ssh("localhost", 12723)
        _wait_for_ssh("localhost", 12724)
        yield
    finally:
        subprocess.run(
            ["docker", "compose", "-f", "docker/docker-compose.yaml", "down"],
            check=True,
        )


@pytest.mark.skipif(_skip_docker_tests(), reason="Docker is not available or in CI.")
@pytest.mark.timeout(600)  # cold `docker compose up` (image build) can exceed the global 300s (#233)
def test_container(setup):
    """
    Test that we can connect to the device and run a command
    in the case that the device is a container.

    Specifically, in this test will connect to a Cisco IOS
    device running in a container and run the command "show clock".
    """
    times_to_collect: int = 100

    device = ConnectHandler(**router1)

    outputs = [device.send_command("show clock") for _ in range(times_to_collect)]

    assert len(outputs) == times_to_collect
    assert all(isinstance(i, str) for i in outputs)
    assert all("Traceback" not in i for i in outputs)


@pytest.mark.skipif(_skip_docker_tests(), reason="Docker is not available or in CI.")
@pytest.mark.timeout(600)  # cold `docker compose up` (image build) can exceed the global 300s (#233)
def test_container_multiple_connections(setup):
    """
    Similar to test_container, but it runs multiple
    connections to the device.
    """
    connections_count = 10
    times_to_collect = 5

    outputs = {"device1": [], "device2": []}

    for _ in range(connections_count):
        device1 = ConnectHandler(**router1)
        device2 = ConnectHandler(**router2)

        for _ in range(times_to_collect):
            outputs["device1"].append(device1.send_command("show clock"))
            outputs["device2"].append(device2.send_command("show clock"))

        device1.disconnect()
        device2.disconnect()

    assert len(outputs["device1"]) == connections_count * times_to_collect
    assert all("Traceback" not in i for i in outputs["device1"])
    assert all(isinstance(i, str) for i in outputs["device1"])

    assert len(outputs["device2"]) == connections_count * times_to_collect
    assert all("Traceback" not in i for i in outputs["device2"])
    assert all(isinstance(i, str) for i in outputs["device2"])
