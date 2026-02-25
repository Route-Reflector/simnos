"""
Network Operating Systems (NOS). Base class to build NOS plugins instances to use with SIMNOS.
"""

import importlib.util
import logging
import os

import yaml

from simnos.core.pydantic_models import ModelNosAttributes

log = logging.getLogger(__name__)

available_platforms: list[str] = [
    "alcatel_aos",
    "alcatel_sros",
    "allied_telesis_awplus",
    "arista_eos",
    "aruba_os",
    "avaya_ers",
    "avaya_vsp",
    "broadcom_icos",
    "brocade_fastiron",
    "brocade_netiron",
    "checkpoint_gaia",
    "ciena_saos",
    "cisco_asa",
    "cisco_ftd",
    "cisco_ios",
    "cisco_nxos",
    "cisco_s300",
    "cisco_xr",
    "dell_force10",
    "dell_powerconnect",
    "dlink_ds",
    "eltex",
    "ericsson_ipos",
    "extreme_exos",
    "fortinet",
    "hp_comware",
    "hp_procurve",
    "huawei_smartax",
    "huawei_vrp",
    "ipinfusion_ocnos",
    "juniper_junos",
    "juniper_screenos",
    "linux",
    "mikrotik_routeros",
    "paloalto_panos",
    "ruckus_fastiron",
    "ubiquiti_edgerouter",
    "ubiquiti_edgeswitch",
    "vyatta_vyos",
    "yamaha",
    "zyxel_os",
]


class Nos:
    """
    Base class to build NOS plugins instances to use with SIMNOS.
    """

    def __init__(
        self,
        name: str = "SimNOS",
        commands: dict | None = None,
        initial_prompt: str = "SimNOS>",
        filename: str | list[str] | None = None,
        configuration_file: str | None = None,
        dict_args: dict | None = None,
    ) -> None:
        """
        Method to instantiate Nos Instance

        :param name: NOS plugin name
        :param commands: dictionary of NOS commands
        :param initial_prompt: NOS initial prompt
        """
        self.name = name
        self.commands = commands or {}
        self.initial_prompt = initial_prompt
        self.auth: str | None = None
        self.enable_prompt: str | None = None
        self.config_prompt: str | None = None
        self.device = None
        self.configuration_file = configuration_file
        if isinstance(filename, str):
            self.from_file(filename)
        elif isinstance(filename, list):
            for file in filename:
                self.from_file(file)
        elif dict_args:
            self.from_dict(dict_args)

        self.validate()

    def validate(self) -> None:
        """
        Method to validate NOS attributes: commands, name,
        initial prompt - using Pydantic models,
        raises ValidationError on failure.
        """
        ModelNosAttributes(**self.__dict__)
        log.debug("%s NOS attributes validation succeeded", self.name)

    def from_dict(self, data: dict) -> None:
        """
        Method to build NOS from dictionary data.

        Sample NOS dictionary::

            nos_plugin_dict = {
                "name": "MySimNOSPlugin",
                "initial_prompt": "{base_prompt}>",
                "commands": {
                    "terminal width 511": {
                        "output": "",
                        "help": "Set terminal width to 511",
                        "prompt": "{base_prompt}>",
                    },
                    "terminal length 0": {
                        "output": "",
                        "help": "Set terminal length to 0",
                        "prompt": "{base_prompt}>",
                    },
                    "show clock": {
                        "output": "MySimNOSPlugin system time is 00:00:00",
                        "help": "Show system time",
                        "prompt": "{base_prompt}>",
                    },
                },
            }

        :param data: NOS dictionary
        """
        self.name = data.get("name", self.name)
        self.commands.update(data.get("commands", self.commands))
        self.initial_prompt = data.get("initial_prompt", self.initial_prompt)
        self.auth = data.get("auth", self.auth)
        self.enable_prompt = data.get("enable_prompt", self.enable_prompt)
        self.config_prompt = data.get("config_prompt", self.config_prompt)

    def _from_yaml(self, data: str) -> None:
        """
        Method to build NOS from YAML data.

        Sample NOS YAML file content::

            name: "MySimNOSPlugin"
            initial_prompt: "{base_prompt}>"
            commands:
                terminal width 511: {
                    "output": "",
                    "help": "Set terminal width to 511",
                    "prompt": "{base_prompt}>",
                }
                terminal length 0: {
                    "output": "",
                    "help": "Set terminal length to 0",
                    "prompt": "{base_prompt}>",
                }
                show clock: {
                    "output": "MySimNOSPlugin system time is 00:00:00",
                    "help": "Show system time",
                    "prompt": "{base_prompt}>",
                }

        :param data: YAML structured text
        """
        with open(data, encoding="utf-8") as f:
            self.from_dict(yaml.safe_load(f))

    def _from_module(self, filename: str) -> None:
        """
        Method to import NOS data from python file or python module.

        Loads from the .py file using the recipe:
        https://docs.python.org/3/library/importlib.html#importing-a-source-file-directly

        Sample Python NOS plugin file::

            name = "MySimNOSPlugin"

            INITIAL_PROMPT = "{base_prompt}>"

            commands = {
                "terminal width 511": {
                    "output": "",
                    "help": "Set terminal width to 511",
                    "prompt": "{base_prompt}>",
                },
                "terminal length 0": {
                    "output": "",
                    "help": "Set terminal length to 0",
                    "prompt": "{base_prompt}>",
                },
                "show clock": {
                    "output": "MySimNOSPlugin system time is 00:00:00",
                    "help": "Show system time",
                    "prompt": "{base_prompt}>",
                },
            }

        :param filename: OS path string to Python .py file
        """
        spec = importlib.util.spec_from_file_location("module.name", filename)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.name = getattr(module, "NAME", self.name)
        self.commands.update(getattr(module, "commands", self.commands))
        self.initial_prompt = getattr(module, "INITIAL_PROMPT", self.initial_prompt)
        self.auth = getattr(module, "AUTH", self.auth)
        self.enable_prompt = getattr(module, "ENABLE_PROMPT", self.enable_prompt)
        self.config_prompt = getattr(module, "CONFIG_PROMPT", self.config_prompt)
        classname = getattr(module, "DEVICE_NAME", None)
        if classname is not None:
            device_class = getattr(module, classname, None)
            if device_class is None:
                raise AttributeError(
                    f"Module '{filename}' defines DEVICE_NAME='{classname}' "
                    f"but class '{classname}' was not found"
                )
            configuration_file = self.configuration_file or getattr(module, "DEFAULT_CONFIGURATION", None)
            self.device = device_class(configuration_file=configuration_file)

    def from_file(self, filename: str) -> None:
        """
        Method to load NOS from YAML or Python file

        :param filename: OS path string to `.yaml/.yml` or `.py` file with NOS data
        """
        if not self.is_file_ending_correct(filename):
            raise ValueError(
                f'Unsupported "{filename}" file extension.\
                              Supported: .py, .yml, .yaml'
            )
        if not os.path.isfile(filename):
            raise FileNotFoundError(filename)
        if filename.endswith((".yaml", ".yml")):
            self._from_yaml(filename)
        elif filename.endswith(".py"):
            self._from_module(filename)

    def is_file_ending_correct(self, filename: str) -> bool:
        """
        Method to check if file extension is correct and load NOS data.
        Correct types are: .yaml, .yml and .py
        """
        return filename.endswith((".yaml", ".yml", ".py"))
