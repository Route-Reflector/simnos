"""
File to contain pydantic models for plugins input/output data validation
"""

import os
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    GetPydanticSchema,
    IPvAnyAddress,
    StrictBool,
    StrictInt,
    StrictStr,
    field_validator,
    model_validator,
)
from pydantic_core import core_schema

from simnos.core.command_contract import CommandHandler

# Valid TCP port. Restores the range constraint lost in the pydantic v1 -> v2
# migration (v1 used `conint(strict=True, gt=0, le=65535)`); #237 / #199 C-15.
Port = Annotated[StrictInt, Field(ge=1, le=65535)]

# Dynamic command output. The type annotation documents the G4 contract
# (`CommandHandler` Protocol — signature and return shape, #241); pydantic
# cannot derive a schema from a Protocol, so the attached schema keeps the
# runtime validation at "is callable", identical to the bare `Callable`
# this replaces. Signature/return conformance is checked statically and by
# the e2e callable sweep, not here.
CommandHandlerField = Annotated[
    CommandHandler,
    GetPydanticSchema(lambda tp, handler: core_schema.callable_schema()),
]

# ---------------------------------------------------------------------------------------
# NOS plugin commands model
# ---------------------------------------------------------------------------------------


class ModelNosCommand(BaseModel):
    """
    Pydantic model for NOS command attributes.

    Unknown fields are rejected loudly (`extra="forbid"`, #244 / D5) so a
    typo'd field (`outptu`) fails the pre-commit validation instead of
    being dropped silently. Safe because every load path validates a
    merged view before commit and `Nos.validate()` passes schema fields
    only (#244 / D8).
    """

    model_config = ConfigDict(extra="forbid")

    output: StrictStr | CommandHandlerField | None = None
    exit: StrictBool | None = None
    help: StrictStr | None = None
    prompt: StrictStr | list[StrictStr] | None = None
    new_prompt: StrictStr | None = None
    alias: StrictStr | None = None
    # Data-only field: alternate captures of the same command's output
    # (16 platform yamls, #234). Not consumed by the runtime — declared
    # so `extra="forbid"` keeps accepting the existing data while still
    # rejecting typos.
    output_variants: list[StrictStr] | None = None


class ModelNosAttributes(BaseModel):
    """
    Pydantic model for NOS attributes.

    `extra="forbid"` (#244 / D5) restores symmetry with the inventory
    models below; safe only because `Nos.validate()` extracts schema
    fields explicitly (never `**self.__dict__`, which also carries
    `device` / `configuration_file`, #244 / D8).

    Kept after the A3 migration removed the legacy yaml loader (#264 / PR-3):
    `Nos.from_dict` / `validate` (inventory + constructor) and `_from_module`
    (py plugin) still validate their boundary through this model. Slated for
    removal when the inventory commands path is reworked in #266; until then
    deleting it would break py-plugin / inventory loading (Decision 9).
    """

    model_config = ConfigDict(extra="forbid")

    commands: dict[StrictStr, ModelNosCommand]
    name: StrictStr
    initial_prompt: StrictStr
    auth: StrictStr | None = None
    enable_prompt: StrictStr | None = None
    config_prompt: StrictStr | None = None


# ---------------------------------------------------------------------------------------
# A3 authoring schema (#264 / P1-1 D2, D3) — the new per-platform on-disk form
# (`platforms/<nos>/platform.yaml` + `commands/*.yaml`). Validated at load; the
# loader then normalizes to `ResolvedCommand` / `ResolvedPlatform`, so the shell
# never sees this authoring form (D4). Kept structural here (types, exclusivity,
# alias purity, path shape); semantic checks that need the filesystem or jinja2
# (file existence, `.j2` syntax, mode-name existence, prompt render) live in the
# loader (`simnos.core.platform_loader`).
# ---------------------------------------------------------------------------------------


def _reject_unsafe_output_ref(value: str | None) -> str | None:
    """Reject an output file reference that escapes the command's own dir.

    Output files are adjacent to their command yaml (D1): a bare filename, no
    path separators, no ``..``, not absolute. This blocks references into
    packaged-data-外 paths at the authoring boundary (#264 / D1).
    """
    if value is None:
        return value
    if value != os.path.basename(value) or value in ("", ".", "..") or os.path.isabs(value):
        raise ValueError(f"output reference {value!r} must be a bare filename in the command's own directory")
    return value


class ModelCommandVariant(BaseModel):
    """One alternate capture of a multi-output command (#264 / D3).

    Each variant points at an output file read verbatim as literal wire text:
    the authoring *field* decides the channel, not the extension (the loader's
    `_resolve_output_file` reads variants with ``as_template=False``). ``.j2``
    templates in variants are out of scope for P1-1 (Decision 6) — a variant
    must reference a literal ``.txt`` (the file-name convention is enforced by
    the data lint, not the loader).
    """

    model_config = ConfigDict(extra="forbid")

    name: StrictStr
    output: StrictStr

    @field_validator("output")
    @classmethod
    def _safe_output(cls, value: str) -> str:
        # A variant output is always present (non-optional str); validate for
        # the side-effect and return the value unchanged.
        _reject_unsafe_output_ref(value)
        return value


class ModelCommandAuthoring(BaseModel):
    """A3 per-command authoring schema (#264 / D3).

    One file = one command; `command` is the SSoT key (Decision 1), the
    filename is non-semantic. Exactly one output channel may be set
    (`output` / `output_template` / `variants`, and `variants` may not be the
    empty list); all absent = no output. An `alias` is a pure reference: it may
    carry only `command` + `help` (Decision 6). `_default_` is the unconditional
    fallback, so authoring a `mode` / `new_mode` / `alias` on it is rejected — it
    must stay mode-agnostic and must not inherit a target's modes (Decision 7).
    """

    model_config = ConfigDict(extra="forbid")

    command: StrictStr
    # Required for a real command, forbidden on an alias (validated below).
    type: Literal["ntc", "simnos", "custom"] | None = None
    source: dict | None = None
    help: StrictStr | None = None
    mode: list[StrictStr] | None = None
    new_mode: StrictStr | None = None
    output: StrictStr | None = None
    output_template: StrictStr | None = None
    variants: list[ModelCommandVariant] | None = None
    exit: StrictBool | None = None
    alias: StrictStr | None = None
    # Session-level "disable paging" flag (#307 / P3-4). Set on the real command
    # whose output stubs paging off (e.g. `terminal length 0`); the shell flips a
    # sticky session flag when it runs in-mode and the push driver then skips the
    # `--More--` pager. Forbidden on an alias (it inherits the target's value via
    # the loader's `replace`, see `_check_combination`).
    disables_paging: StrictBool | None = None

    @field_validator("output", "output_template")
    @classmethod
    def _safe_output(cls, value: str | None) -> str | None:
        return _reject_unsafe_output_ref(value)

    @field_validator("mode")
    @classmethod
    def _reject_empty_mode(cls, value: list[str] | None) -> list[str] | None:
        # An explicit empty list reads as "runnable in no mode"; "all modes" is
        # expressed by omitting `mode`. Reject `[]` so the two never blur
        # (Decision 7, symmetric with the legacy adapter's `prompt: []` reject).
        if value is not None and not value:
            raise ValueError("mode: [] is rejected — omit `mode` to mean all modes (#264 / Decision 7)")
        return value

    @field_validator("variants")
    @classmethod
    def _check_variants(cls, value: list[ModelCommandVariant] | None) -> list[ModelCommandVariant] | None:
        # `variants: []` would pass the channel-exclusivity check as "present"
        # yet leave the loader's `variants[0]` with a bare IndexError — reject it
        # loudly here (1st round codex/claude #1). Duplicate variant names break
        # the (name, output) selection contract, so reject those too.
        if value is None:
            return value
        if not value:
            raise ValueError("variants: [] is rejected — omit `variants` for a no-output command (#264 / Decision 6)")
        names = [v.name for v in value]
        duplicates = sorted({name for name in names if names.count(name) > 1})
        if duplicates:
            raise ValueError(f"variants have duplicate name(s) {duplicates} — each variant name must be unique")
        return value

    @model_validator(mode="after")
    def _check_combination(self) -> "ModelCommandAuthoring":
        if self.alias is not None:
            forbidden = {
                "type": self.type,
                "source": self.source,
                "mode": self.mode,
                "new_mode": self.new_mode,
                "output": self.output,
                "output_template": self.output_template,
                "variants": self.variants,
                "exit": self.exit,
                "disables_paging": self.disables_paging,
            }
            present = sorted(k for k, v in forbidden.items() if v is not None)
            if present:
                raise ValueError(
                    f"command {self.command!r}: alias is a pure reference and cannot also set {present} "
                    "(only `command` and `help` are allowed alongside `alias`) (#264 / Decision 6)"
                )
        else:
            if self.type is None:
                raise ValueError(f"command {self.command!r}: `type` is required (ntc | simnos | custom)")
            channels = sorted(
                name
                for name, v in (
                    ("output", self.output),
                    ("output_template", self.output_template),
                    ("variants", self.variants),
                )
                if v is not None
            )
            if len(channels) > 1:
                raise ValueError(
                    f"command {self.command!r}: at most one output channel allowed, got {channels} (#264 / Decision 6)"
                )
        if self.command == "_default_":
            if self.mode is not None or self.new_mode is not None:
                raise ValueError(
                    "command '_default_': `mode` / `new_mode` are rejected — the fallback is mode-agnostic "
                    "(runtime never matches its mode, would be dead data) (#264 / Decision 7)"
                )
            # An aliased `_default_` would inherit the target's modes/new_mode via
            # the loader's `replace(target, ...)`, splitting `_default_` semantics
            # from the legacy adapter (which forces empty modes). Reject so the
            # fallback can never become mode-bearing through the alias backdoor
            # (1st round claude #6).
            if self.alias is not None:
                raise ValueError(
                    "command '_default_': `alias` is rejected — the fallback must not inherit a target's "
                    "modes / transition (#264 / Decision 7)"
                )
        return self


class ModelModeDef(BaseModel):
    """One mode declaration: a prompt template rendered with `base_prompt` (#264 / D2)."""

    model_config = ConfigDict(extra="forbid")

    prompt: StrictStr


class ModelPlatformPaging(BaseModel):
    """A3 per-platform paging settings (`platform.yaml` `paging:`, #307 / P3-4).

    Only the `--More--` prompt string is per-platform (Cisco ``" --More-- "`` /
    Juniper ``"---(more)---"`` / Huawei ``"---- More ----"``). The page height
    source (pty/NAWS rows, falling back to `sys_config.paging.default_rows`) is an
    environment concern, not a platform one, so it lives in `ModelPaging` instead.
    """

    model_config = ConfigDict(extra="forbid")

    more_prompt: StrictStr = " --More-- "


class ModelPlatformMeta(BaseModel):
    """A3 per-platform metadata schema (`platform.yaml`, #264 / D2).

    Modes are declared centrally (name -> prompt template); commands reference
    mode names only (M2). No `name` field — the platform name is the directory
    name (D1). `netmiko_device_type` / `ntc_platform` are data placeholders the
    consumer side wires up in #266. `paging` is the optional P3-4 pager settings
    (#307); omitted = the Cisco-style default `--More--` prompt.
    """

    model_config = ConfigDict(extra="forbid")

    modes: dict[StrictStr, ModelModeDef]
    initial_mode: StrictStr
    auth: StrictStr | None = None
    netmiko_device_type: StrictStr | None = None
    ntc_platform: StrictStr | None = None
    paging: ModelPlatformPaging | None = None

    @model_validator(mode="after")
    def _check_modes(self) -> "ModelPlatformMeta":
        if not self.modes:
            raise ValueError("platform.yaml: `modes` must declare at least one mode")
        if self.initial_mode not in self.modes:
            raise ValueError(
                f"platform.yaml: initial_mode {self.initial_mode!r} is not in modes {sorted(self.modes)!r}"
            )
        return self


class ModelHost(BaseModel):
    """
    Pydantic model for Host Attributes
    """

    name: StrictStr
    username: StrictStr
    password: StrictStr
    port: Port
    device_type: StrictStr | None = None


# ---------------------------------------------------------------------------------------
# SimNOS inventory data model components
# ---------------------------------------------------------------------------------------


class NosPluginConfig(BaseModel):
    """
    Pydantic model for NOS plugin configuration.
    """

    commands: dict[StrictStr, ModelNosCommand] | None = None


class NosPlugin(BaseModel):
    """
    Pydantic model for NOS plugin.
    """

    plugin: StrictStr
    configuration: NosPluginConfig | None = None


class AsyncSshServerConfig(BaseModel):
    """Pydantic model for the asyncssh SSH server configuration (#297 Stage 2).

    ``timeout`` / ``watchdog_interval`` are accepted for signature parity (the
    async path drives shutdown via loop close, not a recv poll), so they are inert
    here but kept for drop-in inventory compatibility.
    """

    ssh_key_file: StrictStr | None = None
    ssh_key_file_password: StrictStr | None = None
    ssh_banner: StrictStr | None = "SIMNOS AsyncSSH Server"
    timeout: StrictInt | None = 1
    address: Literal["localhost"] | IPvAnyAddress | None = None
    watchdog_interval: StrictInt | None = 1
    authorized_keys: StrictStr | None = None


class AsyncSshServerPlugin(BaseModel):
    """Pydantic model for the asyncssh SSH server plugin (#297 Stage 2)."""

    plugin: Literal["AsyncSshServer"]
    configuration: AsyncSshServerConfig | None = None


class TelnetServerConfig(BaseModel):
    """Pydantic model for the (telnetlib3) Telnet server configuration.

    ``timeout`` / ``watchdog_interval`` are accepted for inventory compatibility
    but inert on the async path (#297 Stage 3): shutdown is driven by closing the
    listener/sessions on the shared loop, not a recv poll.
    """

    banner: StrictStr | None = "SIMNOS Telnet Server"
    timeout: StrictInt | None = 1
    address: Literal["localhost"] | IPvAnyAddress | None = None
    watchdog_interval: StrictInt | None = 1


class TelnetServerPlugin(BaseModel):
    """
    Pydantic model for Telnet server plugin.
    """

    plugin: Literal["TelnetServer"]
    configuration: TelnetServerConfig | None = None


class CMDShellConfig(BaseModel):
    """Pydantic model for CMD shell configuration.

    `ruler` / `completekey` were cmd.Cmd cmdloop-only knobs and were removed with
    the cmd.Cmd base in #303 P3-3; `extra="forbid"` now rejects them (and any
    other unknown key) at load time rather than letting it reach
    `CMDShell.__init__` as an unexpected keyword and crash at connect time.
    `base_prompt` is injected by `Host` (`shell.configuration` setdefault) and
    may also be set in inventory to override the host-name prompt, so it is an
    explicit field here to stay forbid-compatible.
    """

    model_config = ConfigDict(extra="forbid")

    intro: StrictStr | None = "Custom SSH Shell"
    newline: StrictStr | None = "\r\n"
    base_prompt: StrictStr | None = Field(default=None, description="Overrides the default host-name base prompt")


class CMDShellPlugin(BaseModel):
    """
    Pydantic model for CMD shell plugin.
    """

    plugin: Literal["CMDShell"]
    configuration: CMDShellConfig | None = None


class ModelVariantsPolicy(BaseModel):
    """Typed variant-selection policy (#287 / D6, D8).

    Promotes the #266 permissive ``variants_policy`` mapping to a committed
    schema now that #287 consumes it. Two dials:

    - ``select`` — a non-negative ``int`` (default ``0``) pins one variant index
      (fully deterministic, the legacy ``variants[0]`` behaviour); the literal
      ``"random"`` defers the choice to ``seed``.
    - ``seed`` — only meaningful when ``select == "random"``: set = reproducible
      per-host sticky selection (``hash(seed, host, command)``); unset = a fresh
      random draw per connection (realism, non-reproducible).

    ``select`` is a `StrictInt` so ``True``/``1.0`` are rejected (a bool index is
    a config mistake, not "index 1"), and ``ge=0`` forbids negatives — a negative
    modulo would silently pick a tail variant and hide the error (#287 / D6 J).
    ``extra="forbid"`` makes a mistyped key (``selct``) loud rather than inert.
    """

    model_config = ConfigDict(extra="forbid")

    select: Annotated[StrictInt, Field(ge=0)] | Literal["random"] = 0
    seed: StrictInt | None = None


class ModelOverlay(BaseModel):
    """User overlay control (custom data layering, #286 / P1-2a).

    Per-host control for the output-only override: drop a captured ``.txt`` /
    ``.j2`` under ``<sys_config.data_dir>/<registry-key>/`` and list it here to
    replace a packaged command's wire output (or add a command absent from the
    package). The overlay *directory* is environment-global (``sys_config.data_dir``,
    not per-host) — the #266-reserved per-host ``dir`` field is removed; what each
    host pulls from it is the per-host control below.

    ``override_commands`` (Decision 5) selects the commands this host pulls from
    the overlay dir, in three forms:

    - ``all`` — apply every ``.txt`` / ``.j2`` in the dir (stem ``_``->space is the
      command name).
    - a list — apply these commands by their default-name file (``show version``
      -> ``show_version.txt`` / ``.j2``).
    - a map — ``{command: filename}`` for an explicit per-host capture choice
      (the R11 case: host A pulls ``show_version_A.txt``, host B ``_B``).

    A command found in the base is an output-only override (only its output is
    swapped); one absent from the base is a new command (all-modes, ``type=custom``).
    Unset / empty = the overlay is not applied (this field is the opt-in). yaml
    full-replacement is deferred to a future issue — #286 reads ``.txt`` / ``.j2``
    output files only.

    ``random_commands`` is the vessel for a *future* per-command variant policy
    axis (which commands opt into random selection). #287 wires only host-wide
    ``variants_policy``; ``random_commands`` stays validated-but-inert with its
    load-time warning maintained until that future per-command issue (#287 / D8 C).
    """

    model_config = ConfigDict(extra="forbid")

    override_commands: Literal["all"] | list[StrictStr] | dict[StrictStr, StrictStr] | None = None
    random_commands: list[StrictStr] | None = None  # future per-command 器 (warning 維持)


class InventoryDefaultSection(BaseModel):
    """
    Pydantic model for SimNOS inventory default section.
    """

    model_config = ConfigDict(extra="forbid")

    username: StrictStr | None = None
    password: StrictStr | None = None
    port: Port | list[Port] | None = None
    configuration_file: StrictStr | None = None
    device_type: StrictStr | None = None
    server: AsyncSshServerPlugin | TelnetServerPlugin | None = None
    shell: CMDShellPlugin | None = None
    nos: NosPlugin | None = None
    # Inventory render fields. `overlay` is consumed by #286 (Host.start resolves
    # the overlay dir and threads it to the shell). `facts` / `variants_policy`
    # remain #287 reservations — accepted + validated here so the inventory schema
    # never breaks again when #287 wires them up, but consumed by nobody until then;
    # a non-None value is surfaced at host load with `log.warning` (Host.__init__)
    # so a "set but silently inert" config is loud, not a silent no-op
    # (anti-silent-bug). `facts` is a free mapping (render variables, shape owned by
    # the Layer-2 follow-up issue); `variants_policy` is now a committed schema
    # (`ModelVariantsPolicy`, #287 / D8) since #287 consumes it; only `facts`
    # stays permissive until Layer 2 (R4).
    facts: dict | None = Field(None, description="Layer 2 (global facts) で有効化、現在 no-op (host render facts)")
    overlay: ModelOverlay | None = Field(None, description="#286 で有効化 (custom overlay / output override)")
    variants_policy: ModelVariantsPolicy | None = Field(None, description="#287 で有効化 (variant 選択方針)")


class HostConfig(InventoryDefaultSection):
    """
    Pydantic model for SimNOS inventory host configuration.
    """

    replicas: StrictInt | None = None

    @model_validator(mode="before")
    @classmethod
    def check_port_value(cls, values):
        """
        Method to validate port value based on 'replicas' value.
        """
        port = values.get("port")
        if "replicas" not in values and port:
            if not isinstance(port, int):
                raise ValueError("If no host 'replicas' given, port must be an integer")
        elif "replicas" in values and port and not isinstance(port, list):
            raise ValueError("If host 'replicas' given, port must be a list")
        return values


class ModelSimnosInventory(BaseModel):
    """SimNOS inventory data schema"""

    default: InventoryDefaultSection | None = None
    hosts: dict[StrictStr, HostConfig]

    model_config = ConfigDict(extra="forbid")


class ModelPaging(BaseModel):
    """Environment-wide paging settings (`sys_config.yaml` `paging:`, #307 / P3-4).

    `default_rows` is the page height the push driver falls back to when a client
    requests a pty (SSH) / negotiates NAWS (Telnet) but reports no usable row
    count. `gt=0` makes a 0/negative value loud rather than silently breaking the
    pager (a 0-row page would loop forever / draw nothing). Always materialized
    (default_factory) so `sys_config["paging"]["default_rows"]` is present even
    when the file omits `paging:` entirely.
    """

    model_config = ConfigDict(extra="forbid")

    default_rows: int = Field(default=24, gt=0)


class ModelSysConfig(BaseModel):
    """SimNOS environment config schema (`sys_config.yaml`, #266 / D4, Decision 6).

    The minimal "environment vs topology" split: `sys_config.yaml` holds
    environment-wide settings, the inventory holds topology. #266 introduced it
    with two fields only — `data_dir` (the environment-global overlay base dir)
    and `variants_policy` (global default for the inventory per-host field of the
    same name). `data_dir` is consumed by the overlay loader in #286 (a host opts
    in via `overlay.override_commands`, which resolves `<data_dir>/<registry-key>/`);
    `variants_policy` is now consumed by #287 as the global default under the
    inventory; it shares the inventory field's committed `ModelVariantsPolicy`
    schema (#287 / D8). The whole dict flows through the
    ``inventory(default) > sys_config`` precedence as one unit before validation,
    so ``select`` and ``seed`` must co-reside in one source mapping (D8 C).
    """

    model_config = ConfigDict(extra="forbid")

    data_dir: StrictStr | None = None
    variants_policy: ModelVariantsPolicy | None = None
    paging: ModelPaging = Field(default_factory=ModelPaging)
