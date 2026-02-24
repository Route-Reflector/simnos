"""
File to contain pydantic models for plugins input/output data validation
"""

from collections.abc import Callable
from typing import Literal

from pydantic import (
    BaseModel,
    IPvAnyAddress,
    StrictBool,
    StrictInt,
    StrictStr,
    model_validator,
)

# ---------------------------------------------------------------------------------------
# NOS plugin commands model
# ---------------------------------------------------------------------------------------


class ModelNosCommand(BaseModel):
    """
    Pydantic model for NOS command attributes.
    """

    output: StrictStr | Callable | StrictBool | None = None
    help: StrictStr | None = None
    prompt: StrictStr | list[StrictStr] | None = None
    new_prompt: StrictStr | None = None
    alias: StrictStr | None = None


class ModelNosAttributes(BaseModel):
    """
    Pydantic model for NOS attributes.
    """

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
    port: StrictInt
    platform: StrictStr | None = None


# ---------------------------------------------------------------------------------------
# FakeNOS inventory data model components
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
    ssh_banner: StrictStr | None = "FakeNOS Paramiko SSH Server"
    timeout: StrictInt | None = 1
    address: Literal["localhost"] | IPvAnyAddress | None = None
    watchdog_interval: StrictInt | None = 1


class ParamikoSshServerPlugin(BaseModel):
    """
    Pydantic model for Paramiko SSH server plugin.
    """

    plugin: Literal["ParamikoSshServer"]
    configuration: ParamikoSshServerConfig | None = None


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
    Pydantic model for FakeNOS inventory default section.
    """

    username: StrictStr | None = None
    password: StrictStr | None = None
    # port: Optional[Union[conint(strict=True, gt=0, le=65535),
    # conlist(conint(strict=True, gt=0, le=65535),
    # min_items=2, max_items=2, unique_items=True)]]
    # use this for now, mkdocstring having issue with pydantic
    # https://github.com/mkdocstrings/griffe/issues/66
    port: StrictInt | list[StrictInt] | None = None
    configuration_file: StrictStr | None = None
    server: ParamikoSshServerPlugin | None = None
    shell: CMDShellPlugin | None = None
    nos: NosPlugin | None = None


class HostConfig(InventoryDefaultSection):
    """
    Pydantic model for FakeNOS inventory host configuration.
    """

    # count: Optional[conint(strict=True, gt=0)]
    # use this for now, mkdocstring having issue with pydantic
    # https://github.com/mkdocstrings/griffe/issues/66
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


class ModelFakenosInventory(BaseModel):
    """FakeNOS inventory data schema"""

    default: InventoryDefaultSection | None = None
    hosts: dict[StrictStr, HostConfig]

    # pylint: disable=too-few-public-methods
    class ConfigDict:
        """Pydantic model configuration"""

        extra = "forbid"
