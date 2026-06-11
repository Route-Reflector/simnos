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

    Each variant points at a literal output file; `.j2` templates in variants
    are out of scope for P1-1 (Decision 6) and rejected by the loader.
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
    (`output` / `output_template` / `variants`); all absent = no output. An
    `alias` is a pure reference: it may carry only `command` + `help`
    (Decision 6). `_default_` is the unconditional fallback, so authoring a
    `mode` / `new_mode` on it is rejected (dead data — Decision 7).
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
        if self.command == "_default_" and (self.mode is not None or self.new_mode is not None):
            raise ValueError(
                "command '_default_': `mode` / `new_mode` are rejected — the fallback is mode-agnostic "
                "(runtime never matches its mode, would be dead data) (#264 / Decision 7)"
            )
        return self


class ModelModeDef(BaseModel):
    """One mode declaration: a prompt template rendered with `base_prompt` (#264 / D2)."""

    model_config = ConfigDict(extra="forbid")

    prompt: StrictStr


class ModelPlatformMeta(BaseModel):
    """A3 per-platform metadata schema (`platform.yaml`, #264 / D2).

    Modes are declared centrally (name -> prompt template); commands reference
    mode names only (M2). No `name` field — the platform name is the directory
    name (D1). `netmiko_device_type` / `ntc_platform` are data placeholders the
    consumer side wires up in #266.
    """

    model_config = ConfigDict(extra="forbid")

    modes: dict[StrictStr, ModelModeDef]
    initial_mode: StrictStr
    auth: StrictStr | None = None
    netmiko_device_type: StrictStr | None = None
    ntc_platform: StrictStr | None = None

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
    platform: StrictStr | None = None


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


class ParamikoSshServerConfig(BaseModel):
    """
    Pydantic model for Paramiko SSH server configuration.
    """

    ssh_key_file: StrictStr | None = None
    ssh_key_file_password: StrictStr | None = None
    ssh_banner: StrictStr | None = "SIMNOS Paramiko SSH Server"
    timeout: StrictInt | None = 1
    address: Literal["localhost"] | IPvAnyAddress | None = None
    watchdog_interval: StrictInt | None = 1
    authorized_keys: StrictStr | None = None


class ParamikoSshServerPlugin(BaseModel):
    """
    Pydantic model for Paramiko SSH server plugin.
    """

    plugin: Literal["ParamikoSshServer"]
    configuration: ParamikoSshServerConfig | None = None


class TelnetServerConfig(BaseModel):
    """
    Pydantic model for Telnet server configuration.
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
    """
    Pydantic model for CMD shell configuration.
    """

    intro: StrictStr | None = "Custom SSH Shell"
    ruler: StrictStr | None = ""
    completekey: StrictStr | None = "tab"
    newline: StrictStr | None = "\r\n"


class CMDShellPlugin(BaseModel):
    """
    Pydantic model for CMD shell plugin.
    """

    plugin: Literal["CMDShell"]
    configuration: CMDShellConfig | None = None


class InventoryDefaultSection(BaseModel):
    """
    Pydantic model for SimNOS inventory default section.
    """

    model_config = ConfigDict(extra="forbid")

    username: StrictStr | None = None
    password: StrictStr | None = None
    port: Port | list[Port] | None = None
    configuration_file: StrictStr | None = None
    platform: StrictStr | None = None
    server: ParamikoSshServerPlugin | TelnetServerPlugin | None = None
    shell: CMDShellPlugin | None = None
    nos: NosPlugin | None = None


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
