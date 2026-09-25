"""Shared fixtures for compatibility tests.

These tests exercise simnos against external automation libraries
(netmiko / scrapli / ansible) and are gated behind workflow_dispatch
CI; they are skipped by default in the normal test suite via
`pytest.mark.compatibility` (see pyproject `markers`).
"""

import pytest

from simnos import SimNOS
from tests.utils import TEST_PASSWORD, TEST_USERNAME, build_inventory


@pytest.fixture
def cisco_ios_simnos():
    """Start a simnos cisco_ios instance on an ephemeral port; yield connection creds."""
    inventory = build_inventory("cisco_ios")  # ephemeral port (#271)
    with SimNOS(inventory=inventory) as net:
        # Read the real OS-assigned port back after start, then build creds.
        creds = {
            # Pin IPv4: the listener binds 127.0.0.1 only, and ansible's libssh
            # backend resolves "localhost" to ::1 first without falling back.
            "host": "127.0.0.1",
            "username": TEST_USERNAME,
            "password": TEST_PASSWORD,
            "port": net.hosts["device"].port,
        }
        yield creds
