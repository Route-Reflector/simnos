"""Shared fixtures for compatibility tests.

These tests exercise simnos against external automation libraries
(netmiko / scrapli / ansible) and are gated behind workflow_dispatch
CI; they are skipped by default in the normal test suite via
`pytest.mark.compatibility` (see pyproject `markers`).
"""

import pytest

from simnos import SimNOS
from tests.utils import TEST_PASSWORD, TEST_USERNAME, build_inventory, get_free_port


@pytest.fixture
def cisco_ios_simnos():
    """Start a simnos cisco_ios instance on a free port; yield connection creds."""
    port = get_free_port()
    inventory = build_inventory("cisco_ios", port=port)
    creds = {
        "host": "localhost",
        "username": TEST_USERNAME,
        "password": TEST_PASSWORD,
        "port": port,
    }
    with SimNOS(inventory=inventory) as _net:
        yield creds
