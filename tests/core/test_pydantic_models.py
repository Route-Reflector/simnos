"""
Test module for simnos.core.pydantic_models.
This module can be found at simnos/core/pydantic_models.py
"""

from pydantic import ValidationError
import pytest

from simnos.core.pydantic_models import InventoryDefaultSection, ModelHost


class TestPortRange:
    """Pins for the TCP port range constraint on the `Port` type (#237).

    The pydantic v1 -> v2 migration silently dropped the v1-era
    `conint(strict=True, gt=0, le=65535)` range, leaving bare `StrictInt`
    fields that accepted 0, negatives and > 65535. These tests pin the
    restored 1-65535 range on both port-bearing models.
    """

    HOST_KWARGS = {"name": "r1", "username": "u", "password": "p"}

    @pytest.mark.parametrize("port", [1, 22, 65535])
    def test_model_host_accepts_valid_ports(self, port):
        """Boundary and typical in-range ports pass validation."""
        assert ModelHost(**self.HOST_KWARGS, port=port).port == port

    @pytest.mark.parametrize("port", [0, -1, 65536])
    def test_model_host_rejects_out_of_range_ports(self, port):
        """Zero, negative and > 65535 ports are rejected."""
        with pytest.raises(ValidationError, match="port"):
            ModelHost(**self.HOST_KWARGS, port=port)

    def test_inventory_default_accepts_valid_port_list(self):
        """The replicas-style list[Port] variant accepts in-range ports."""
        assert InventoryDefaultSection(port=[6000, 6001]).port == [6000, 6001]

    @pytest.mark.parametrize("ports", [[6000, 0], [65536]])
    def test_inventory_default_rejects_out_of_range_port_list(self, ports):
        """A single out-of-range element fails the whole list."""
        with pytest.raises(ValidationError, match="port"):
            InventoryDefaultSection(port=ports)
