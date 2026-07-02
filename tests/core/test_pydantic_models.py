"""
Test module for simnos.core.pydantic_models.
This module can be found at simnos/core/pydantic_models.py
"""

from pydantic import ValidationError
import pytest

from simnos.core.pydantic_models import (
    CMDShellConfig,
    HostConfig,
    InventoryDefaultSection,
    ModelCommandAuthoring,
    ModelHost,
    ModelInventoryCommand,
    ModelNosCommand,
    ModelPlatformMeta,
    ModelTransition,
    NosPluginConfig,
)


class TestPortRange:
    """Pins for the TCP port range constraint on the port types (#237 / #271).

    The pydantic v1 -> v2 migration silently dropped the v1-era
    `conint(strict=True, gt=0, le=65535)` range, leaving bare `StrictInt`
    fields that accepted 0, negatives and > 65535. The range was restored
    (1-65535), then #271 added `EphemeralPort` (ge=0) for the single-port
    path: port=0 is now a valid ephemeral request (OS-assigned at bind), while
    the replicas list path keeps `Port` (ge=1) — an ephemeral port range is
    meaningless.
    """

    HOST_KWARGS = {"name": "r1", "username": "u", "password": "p"}

    @pytest.mark.parametrize("port", [0, 1, 22, 65535])
    def test_model_host_accepts_valid_ports(self, port):
        """Boundary and typical in-range ports pass validation; 0 = ephemeral (#271)."""
        assert ModelHost(**self.HOST_KWARGS, port=port).port == port

    @pytest.mark.parametrize("port", [-1, 65536])
    def test_model_host_rejects_out_of_range_ports(self, port):
        """Negative and > 65535 ports are rejected (0 is now valid, #271)."""
        with pytest.raises(ValidationError, match="port"):
            ModelHost(**self.HOST_KWARGS, port=port)

    def test_inventory_default_accepts_valid_port_list(self):
        """The replicas-style list[Port] variant accepts in-range ports."""
        assert InventoryDefaultSection(port=[6000, 6001]).port == [6000, 6001]

    @pytest.mark.parametrize("ports", [[6000, 0], [65536]])
    def test_inventory_default_rejects_out_of_range_port_list(self, ports):
        """A single out-of-range element fails the whole list (the list path keeps ge=1, #271)."""
        with pytest.raises(ValidationError, match="port"):
            InventoryDefaultSection(port=ports)

    def test_host_config_rejects_replicas_with_scalar_zero_port(self):
        """`replicas` + `port: 0` is rejected (port must be a list).

        Guards the #271 `check_port_value` fix: the truthy check `if port:` treated
        0 as unset and let `replicas` + port=0 slip past the "must be a list" branch.
        The `port is not None` form pins the rejection here, so a regression back to
        `if port:` is caught directly.
        """
        with pytest.raises(ValidationError, match="must be a list"):
            HostConfig(replicas=2, port=0)


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
        with pytest.raises(ValidationError, match="alias cannot also set"):
            ModelCommandAuthoring(command="x", alias="y", output="a.txt")

    def test_rejects_alias_with_type(self):
        with pytest.raises(ValidationError, match="alias cannot also set"):
            ModelCommandAuthoring(command="x", alias="y", type="ntc")

    def test_accepts_alias_with_mode_override(self):
        # #317 / P-1: `mode:` is the one dispatch field an alias may re-author —
        # a mode-set override (e.g. arista `do show ip int brief`, config-only).
        model = ModelCommandAuthoring(command="do show x", alias="show x", mode=["config"])
        assert model.alias == "show x"
        assert model.mode == ["config"]

    def test_rejects_alias_with_handler(self):
        with pytest.raises(ValidationError, match="alias cannot also set"):
            ModelCommandAuthoring(command="x", alias="y", handler="make_x")

    def test_rejects_alias_with_transitions(self):
        with pytest.raises(ValidationError, match="alias cannot also set"):
            # pydantic coerces the nested dict into ModelTransition at runtime; ty
            # only sees the dict literal (same pattern as the variants test above).
            ModelCommandAuthoring(command="x", alias="y", transitions={"user": {"exit": True}})  # ty: ignore[invalid-argument-type]

    def test_accepts_disables_paging_on_real_command(self):
        # #307 / P3-4: a session-disable command flags itself; the loader carries
        # it to ResolvedCommand and the shell flips a sticky session flag.
        model = ModelCommandAuthoring(command="terminal length 0", type="simnos", disables_paging=True)
        assert model.disables_paging is True

    def test_rejects_alias_with_disables_paging(self):
        # An alias inherits the target's disables_paging via the loader's `replace`;
        # authoring it on the alias row is rejected (#307).
        with pytest.raises(ValidationError, match="alias cannot also set"):
            ModelCommandAuthoring(command="term len 0", alias="terminal length 0", disables_paging=True)

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
            # pydantic coerces the dicts into ModelCommandVariant at runtime; ty
            # only sees the dict literals (same pattern as the modes dict above).
            ModelCommandAuthoring(
                command="x",
                type="ntc",
                variants=[{"name": "default", "output": "a.txt"}, {"name": "default", "output": "b.txt"}],  # ty: ignore[invalid-argument-type]
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

    # --- handler channel (#317 / P-1) ---

    def test_accepts_handler_channel(self):
        model = ModelCommandAuthoring(command="show clock", type="simnos", handler="make_show_clock")
        assert model.handler == "make_show_clock"

    def test_rejects_non_identifier_handler(self):
        with pytest.raises(ValidationError, match="valid Python identifier"):
            ModelCommandAuthoring(command="x", type="simnos", handler="make.show clock")

    def test_rejects_keyword_handler(self):
        # A keyword passes `str.isidentifier()` but can never name a real py
        # function, so it is rejected at the authoring boundary (#317 P-1, codex#5).
        with pytest.raises(ValidationError, match="valid Python identifier"):
            ModelCommandAuthoring(command="x", type="simnos", handler="class")

    def test_rejects_handler_with_other_output_channel(self):
        with pytest.raises(ValidationError, match="at most one output channel"):
            ModelCommandAuthoring(command="x", type="simnos", handler="h", output="a.txt")

    # --- transitions map (#317 / P-1) ---

    def test_accepts_transitions_map(self):
        model = ModelCommandAuthoring(
            command="exit",
            type="simnos",
            mode=["user", "config"],
            transitions={"user": {"exit": True}, "config": {"new_mode": "enable"}},  # ty: ignore[invalid-argument-type]
        )
        assert model.transitions is not None
        assert model.transitions["user"].exit is True
        assert model.transitions["config"].new_mode == "enable"

    def test_rejects_transitions_with_static_new_mode(self):
        with pytest.raises(ValidationError, match="`transitions` is exclusive"):
            ModelCommandAuthoring(
                command="x",
                type="simnos",
                new_mode="enable",
                transitions={"user": {"exit": True}},  # ty: ignore[invalid-argument-type]
            )

    def test_rejects_transitions_with_static_exit(self):
        with pytest.raises(ValidationError, match="`transitions` is exclusive"):
            ModelCommandAuthoring(
                command="x",
                type="simnos",
                exit=True,
                transitions={"user": {"new_mode": "enable"}},  # ty: ignore[invalid-argument-type]
            )

    def test_rejects_empty_transitions(self):
        with pytest.raises(ValidationError, match="is empty"):
            ModelCommandAuthoring(command="x", type="simnos", transitions={})

    def test_rejects_default_with_transitions(self):
        with pytest.raises(ValidationError, match="mode-agnostic"):
            ModelCommandAuthoring(
                command="_default_",
                type="simnos",
                transitions={"user": {"exit": True}},  # ty: ignore[invalid-argument-type]
            )


class TestModelInventoryCommand:
    """Structural validation for the inventory command schema (#317 / P-3, 案E).

    The inventory inflow speaks the A3 dialect (mode names / transitions /
    inline output); the removed legacy fields (`prompt` / `new_prompt` /
    `alias` / `output_variants`) must be rejected loudly, not silently
    dropped — that is the breaking edge of P-3 (changelog migration row).
    The `_default_` special rule lives on `NosPluginConfig` (which sees the
    command names as mapping keys).
    """

    def test_minimal_command(self):
        model = ModelInventoryCommand(output="hello", help="h", mode=["user"])
        assert model.output == "hello"
        assert model.mode == ["user"]

    def test_all_fields_default_none(self):
        model = ModelInventoryCommand()
        assert model.output is None and model.output_template is None
        assert model.mode is None and model.new_mode is None and model.transitions is None

    @pytest.mark.parametrize(
        "legacy_field",
        [
            {"prompt": "{base_prompt}>"},
            {"new_prompt": "{base_prompt}#"},
            {"alias": "show version"},
            {"output_variants": ["alt"]},
        ],
        ids=["prompt", "new_prompt", "alias", "output_variants"],
    )
    def test_rejects_legacy_fields(self, legacy_field):
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            ModelInventoryCommand(**legacy_field)

    def test_rejects_empty_mode_list(self):
        with pytest.raises(ValidationError, match=r"mode: \[\] is rejected"):
            ModelInventoryCommand(mode=[])

    def test_rejects_two_output_channels(self):
        with pytest.raises(ValidationError, match="at most one of"):
            ModelInventoryCommand(output="text", output_template="{{ base_prompt }}")

    def test_accepts_transitions_map(self):
        model = ModelInventoryCommand(transitions={"user": {"exit": True}})  # ty: ignore[invalid-argument-type]
        assert model.transitions is not None
        assert model.transitions["user"].exit is True

    def test_rejects_transitions_with_static_new_mode(self):
        with pytest.raises(ValidationError, match="exclusive with"):
            ModelInventoryCommand(
                new_mode="enable",
                transitions={"user": {"exit": True}},  # ty: ignore[invalid-argument-type]
            )

    def test_rejects_transitions_with_static_exit(self):
        with pytest.raises(ValidationError, match="exclusive with"):
            ModelInventoryCommand(
                exit=True,
                transitions={"user": {"exit": True}},  # ty: ignore[invalid-argument-type]
            )

    def test_rejects_empty_transitions(self):
        with pytest.raises(ValidationError, match="is empty"):
            ModelInventoryCommand(transitions={})


class TestNosPluginConfigDefaultRules:
    """`_default_` special rule on the inventory commands mapping (#317 / P-3).

    A3-identical (2nd round claude#5): the fallback is mode-agnostic, so a
    `mode` / `new_mode` / `transitions` on the `_default_` override is dead
    data and rejected. The rule lives here (not on `ModelInventoryCommand`)
    because the command name is the mapping key.
    """

    @pytest.mark.parametrize(
        "default_entry",
        [
            {"mode": ["user"]},
            {"new_mode": "enable"},
            {"transitions": {"user": {"exit": True}}},
        ],
        ids=["mode", "new_mode", "transitions"],
    )
    def test_rejects_default_with_mode_or_transition(self, default_entry):
        with pytest.raises(ValidationError, match="mode-agnostic"):
            NosPluginConfig(commands={"_default_": {"output": "?", **default_entry}})  # ty: ignore[invalid-argument-type]

    def test_accepts_plain_default_override(self):
        config = NosPluginConfig(commands={"_default_": {"output": "% Unknown"}})  # ty: ignore[invalid-argument-type]
        assert config.commands is not None
        assert config.commands["_default_"].output == "% Unknown"

    def test_accepts_none_commands(self):
        assert NosPluginConfig().commands is None


class TestModelTransition:
    """One `transitions` map entry — exactly one of new_mode / exit (#317 / P-1)."""

    def test_accepts_exit(self):
        assert ModelTransition(exit=True).exit is True

    def test_accepts_new_mode(self):
        assert ModelTransition(new_mode="enable").new_mode == "enable"

    def test_rejects_both(self):
        with pytest.raises(ValidationError, match="exactly one"):
            ModelTransition(new_mode="enable", exit=True)

    def test_rejects_neither(self):
        with pytest.raises(ValidationError, match="exactly one"):
            ModelTransition()

    def test_rejects_exit_false(self):
        with pytest.raises(ValidationError, match="`exit` must be true"):
            ModelTransition(exit=False)


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

    def test_paging_more_prompt_default_and_override(self):
        """`paging.more_prompt` is optional (Cisco-style default) and overridable (#307)."""
        modes = {"user": {"prompt": ">"}}
        default = ModelPlatformMeta(modes=modes, initial_mode="user")  # ty: ignore[invalid-argument-type]
        assert default.paging is None  # omitted -> ResolvedPlatform applies the default
        juniper = ModelPlatformMeta(modes=modes, initial_mode="user", paging={"more_prompt": "---(more)---"})  # ty: ignore[invalid-argument-type]
        assert juniper.paging is not None and juniper.paging.more_prompt == "---(more)---"

    @pytest.mark.parametrize(
        ("bad", "match"),
        [
            ("", "must not be empty"),
            ("もっと", "must be ASCII"),  # wide glyphs break the \b-based erase width
            ("a\nb", "single line"),
        ],
    )
    def test_paging_more_prompt_rejects_non_ascii_single_line(self, bad, match):
        """`more_prompt` must be a non-empty single-line ASCII string so the pager's
        `\\b`*N erase matches the displayed width (#307 / P3-4, codex#3)."""
        with pytest.raises(ValidationError, match=match):
            ModelPlatformMeta(modes={"user": {"prompt": ">"}}, initial_mode="user", paging={"more_prompt": bad})  # ty: ignore[invalid-argument-type]


class TestCMDShellConfig:
    """Schema pins for the shell configuration after the cmd.Cmd removal (#303 P3-3).

    `ruler` / `completekey` were cmd.Cmd cmdloop-only knobs and were removed with
    the base class; `extra="forbid"` now rejects them (and any other unknown key)
    at load time rather than letting them reach `CMDShell.__init__` as unexpected
    keywords and crash at connect time. `base_prompt` stays an accepted field
    because `Host` injects it (and inventory may override it).
    """

    def test_accepts_supported_fields(self):
        """intro / newline / base_prompt are the surviving live knobs."""
        cfg = CMDShellConfig(intro="hi", newline="\n", base_prompt="r1")
        assert cfg.intro == "hi"
        assert cfg.newline == "\n"
        assert cfg.base_prompt == "r1"

    def test_empty_config_is_valid(self):
        """A bare `{}` (the default inventory shell config) validates."""
        assert CMDShellConfig().base_prompt is None

    @pytest.mark.parametrize("removed_key", ["ruler", "completekey"])
    def test_rejects_removed_cmdloop_knobs(self, removed_key):
        """The removed cmd.Cmd knobs are now loud ValidationErrors, not silent."""
        with pytest.raises(ValidationError):
            CMDShellConfig(**{removed_key: "x"})

    def test_rejects_unknown_key(self):
        """Any unknown key is rejected at load time (extra='forbid')."""
        with pytest.raises(ValidationError):
            CMDShellConfig(typo="x")  # ty: ignore[unknown-argument]  # intentional: forbid pin
