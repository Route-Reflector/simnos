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
            "host": "localhost",
            "username": TEST_USERNAME,
            "password": TEST_PASSWORD,
            "port": net.hosts["device"].port,
        }
        yield creds
