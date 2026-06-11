"""
Test module for simnos.core.pydantic_models.
This module can be found at simnos/core/pydantic_models.py
"""

from pydantic import ValidationError
import pytest

from simnos.core.pydantic_models import (
    InventoryDefaultSection,
    ModelCommandAuthoring,
    ModelHost,
    ModelNosCommand,
    ModelPlatformMeta,
)


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


class TestCommandHandlerField:
    """Pins for the `output` field's CommandHandlerField annotation (#241).

    `CommandHandlerField = Annotated[CommandHandler, GetPydanticSchema(
    callable_schema)]` exists to keep the runtime validation at "is
    callable" — identical to the bare `Callable` it replaced — while the
    annotation documents the G4 contract. These pins fix that equivalence
    directly so a future change to the schema hook (e.g. attempting
    signature validation) is a conscious decision, not a drive-by.
    """

    def test_output_accepts_callable(self):
        """A callable output passes validation and survives round-trip."""
        handler = lambda device, **kwargs: "body"  # noqa: E731 — minimal contract-shaped stand-in
        model = ModelNosCommand(output=handler)
        assert model.output is handler

    def test_output_rejects_non_callable_non_str(self):
        """A non-callable, non-str output (int) is rejected."""
        with pytest.raises(ValidationError, match="output"):
            ModelNosCommand(output=42)  # ty: ignore[invalid-argument-type]


class TestModelCommandAuthoring:
    """Structural validation surface for the A3 per-command schema (#264 / D3).

    These pin the boundary validation done by the model itself; the
    filesystem/jinja semantic checks (file existence, mode-name resolution)
    live in `test_platform_loader.py`.
    """

    def test_minimal_real_command(self):
        model = ModelCommandAuthoring(command="show version", type="ntc", output="show_version.txt")
        assert model.command == "show version"

    def test_pure_alias(self):
        model = ModelCommandAuthoring(command="sh ver", alias="show version", help="abbrev")
        assert model.alias == "show version"

    def test_rejects_two_output_channels(self):
        with pytest.raises(ValidationError, match="at most one output channel"):
            ModelCommandAuthoring(command="x", type="ntc", output="a.txt", output_template="a.j2")

    def test_rejects_empty_mode_list(self):
        with pytest.raises(ValidationError, match=r"mode: \[\] is rejected"):
            ModelCommandAuthoring(command="x", type="ntc", mode=[])

    def test_rejects_missing_type_on_real_command(self):
        with pytest.raises(ValidationError, match="`type` is required"):
            ModelCommandAuthoring(command="x", output="a.txt")

    def test_rejects_alias_with_dispatch_fields(self):
        with pytest.raises(ValidationError, match="pure reference"):
            ModelCommandAuthoring(command="x", alias="y", output="a.txt")

    def test_rejects_alias_with_type(self):
        with pytest.raises(ValidationError, match="pure reference"):
            ModelCommandAuthoring(command="x", alias="y", type="ntc")

    def test_rejects_default_with_mode(self):
        with pytest.raises(ValidationError, match="mode-agnostic"):
            ModelCommandAuthoring(command="_default_", type="simnos", mode=["user"])

    def test_rejects_default_with_alias(self):
        # An aliased _default_ would inherit the target's modes via the loader,
        # splitting _default_ semantics from the legacy adapter (#264 / claude #6).
        with pytest.raises(ValidationError, match="must not inherit"):
            ModelCommandAuthoring(command="_default_", alias="show version")

    def test_rejects_empty_variants(self):
        # variants: [] would pass the channel-exclusivity check yet leave the
        # loader's variants[0] a bare IndexError (#264 / codex+claude #1).
        with pytest.raises(ValidationError, match=r"variants: \[\] is rejected"):
            ModelCommandAuthoring(command="x", type="ntc", variants=[])

    def test_rejects_duplicate_variant_names(self):
        with pytest.raises(ValidationError, match="duplicate name"):
            ModelCommandAuthoring(
                command="x",
                type="ntc",
                variants=[{"name": "default", "output": "a.txt"}, {"name": "default", "output": "b.txt"}],
            )

    def test_allows_default_without_mode(self):
        model = ModelCommandAuthoring(command="_default_", type="simnos", output="d.txt")
        assert model.command == "_default_"

    @pytest.mark.parametrize("ref", ["../evil.txt", "/etc/passwd", "sub/a.txt"])
    def test_rejects_unsafe_output_path(self, ref):
        with pytest.raises(ValidationError, match="bare filename"):
            ModelCommandAuthoring(command="x", type="ntc", output=ref)

    def test_rejects_unknown_field(self):
        with pytest.raises(ValidationError, match="bogus"):
            ModelCommandAuthoring(command="x", type="ntc", bogus=1)  # ty: ignore[unknown-argument]

    def test_rejects_bad_type_literal(self):
        with pytest.raises(ValidationError):
            ModelCommandAuthoring(command="x", type="bogus")  # ty: ignore[invalid-argument-type]


class TestModelPlatformMeta:
    """Structural validation for the A3 per-platform schema (#264 / D2)."""

    def test_minimal_platform(self):
        # pydantic coerces the nested dict into ModelModeDef at runtime; ty only
        # sees the dict literal, hence the ignore (same pattern as ModelNosCommand above).
        model = ModelPlatformMeta(modes={"user": {"prompt": "{{ base_prompt }}>"}}, initial_mode="user")  # ty: ignore[invalid-argument-type]
        assert model.initial_mode == "user"

    def test_rejects_empty_modes(self):
        with pytest.raises(ValidationError, match="at least one mode"):
            ModelPlatformMeta(modes={}, initial_mode="user")

    def test_rejects_initial_mode_not_in_modes(self):
        with pytest.raises(ValidationError, match="initial_mode"):
            ModelPlatformMeta(modes={"user": {"prompt": ">"}}, initial_mode="enable")  # ty: ignore[invalid-argument-type]
