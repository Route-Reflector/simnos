"""
File to contain pydantic models for plugins input/output data validation
"""

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
