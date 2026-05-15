"""Shared fixtures for compatibility tests.

These tests exercise simnos against external automation libraries
(netmiko / scrapli / ansible) and are gated behind workflow_dispatch
CI; they are skipped by default in the normal test suite via
`pytest.mark.compatibility` (see pyproject `markers`).
"""

import pytest

from simnos import SimNOS
from tests.utils import get_free_port


@pytest.fixture
def cisco_ios_simnos():
    """Start a simnos cisco_ios instance on a free port; yield connection creds."""
    creds = {
        "host": "localhost",
        "username": "test_user",
        "password": "test_pass",
        "port": get_free_port(),
    }
    inventory = {
        "hosts": {
            "test_device": {
                **{k: creds[k] for k in ("username", "password", "port")},
                "platform": "cisco_ios",
            }
        }
    }
    with SimNOS(inventory=inventory) as _net:
        yield creds
