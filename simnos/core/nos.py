"""
Network Operating Systems (NOS). Base class to build NOS plugins instances to use with SIMNOS.
"""

import importlib.util
import logging
import os

import yaml

from simnos.core.pydantic_models import ModelNosAttributes

log = logging.getLogger(__name__)


class Nos:
    """
    Base class to build NOS plugins instances to use with SIMNOS.
    """

    # Mapping of module-level UPPERCASE constants in a Python plugin file
    # to the corresponding lowercase attribute on the Nos instance.
    # Used by `_from_module` to sync module constants into self.
    _MODULE_ATTR_MAP: dict[str, str] = {
        "NAME": "name",
        "INITIAL_PROMPT": "initial_prompt",
        "AUTH": "auth",
        "ENABLE_PROMPT": "enable_prompt",
        "CONFIG_PROMPT": "config_prompt",
    }

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

        The per-command schema follows :class:`simnos.core.pydantic_models.ModelNosCommand`;
        a live Python plugin example is :mod:`simnos.plugins.nos.platforms_py.cisco_ios`.

        Minimal sample::

            nos_plugin_dict = {
                "name": "MySimNOSPlugin",
                "initial_prompt": "{base_prompt}>",
                "commands": {
                    "show clock": {"output": "12:00:00", "help": "Show clock"},
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

    def _from_yaml(self, filepath: str) -> None:
        """
        Method to build NOS from YAML file.

        The YAML mirrors the dict schema accepted by :meth:`from_dict`;
        see :class:`simnos.core.pydantic_models.ModelNosCommand` for the
        per-command schema and ``simnos/plugins/nos/platforms_yaml/cisco_ios.yaml``
        for a live example.

        :param filepath: OS path to YAML file with NOS data
        :raises ValueError: if the file holds no YAML mapping (empty file
            or a non-dict top level), e.g. a half-written file caught
            mid-save — `yaml.safe_load` returns None for it and
            :meth:`from_dict` would crash on `data.get`
        """
        with open(filepath, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict):
            raise ValueError(f"NOS YAML file '{filepath}' does not contain a mapping (got {type(data).__name__})")
        self.from_dict(data)

    def _from_module(self, filename: str) -> None:
        """
        Method to import NOS data from python file or python module.

        Loads from the .py file using the recipe:
        https://docs.python.org/3/library/importlib.html#importing-a-source-file-directly

        The module is expected to define module-level constants (``NAME``,
        ``INITIAL_PROMPT``, optional ``ENABLE_PROMPT`` / ``CONFIG_PROMPT`` /
        ``DEVICE_NAME`` / ``DEFAULT_CONFIGURATION``) and a ``commands`` dict;
        see :mod:`simnos.plugins.nos.platforms_py.cisco_ios` for a live example.

        :param filename: OS path string to Python .py file
        """
        spec = importlib.util.spec_from_file_location("module.name", filename)
        if spec is None or spec.loader is None:
            raise ValueError(f"Cannot load NOS module from '{filename}' (spec_from_file_location returned None)")
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except FileNotFoundError:
            # Preserve FileNotFoundError as-is so callers can distinguish
            # "path does not exist" from "plugin code itself failed".
            raise
        except Exception as e:
            raise RuntimeError(f"Failed to load NOS plugin '{filename}': {e}") from e
        for module_attr, self_attr in self._MODULE_ATTR_MAP.items():
            setattr(self, self_attr, getattr(module, module_attr, getattr(self, self_attr)))
        self.commands.update(getattr(module, "commands", self.commands))
        if self.name == "SimNOS":
            log.warning(
                "Module '%s' does not define NAME; falling back to default 'SimNOS' "
                "(plugin will be registered under that key)",
                filename,
            )
        classname = getattr(module, "DEVICE_NAME", None)
        if classname is None:
            log.warning("Module '%s' does not define DEVICE_NAME; device will be None", filename)
        else:
            device_class = getattr(module, classname, None)
            if device_class is None:
                raise AttributeError(
                    f"Module '{filename}' defines DEVICE_NAME='{classname}' but class '{classname}' was not found"
                )
            configuration_file = self.configuration_file or getattr(module, "DEFAULT_CONFIGURATION", None)
            self.device = device_class(configuration_file=configuration_file)

    def from_file(self, filename: str) -> None:
        """
        Method to load NOS from YAML or Python file

        :param filename: OS path string to `.yaml/.yml` or `.py` file with NOS data
        """
        if not self._is_file_ending_correct(filename):
            raise ValueError(f'Unsupported "{filename}" file extension. Supported: .py, .yml, .yaml')
        if not os.path.isfile(filename):
            raise FileNotFoundError(filename)
        if filename.endswith((".yaml", ".yml")):
            self._from_yaml(filename)
        elif filename.endswith(".py"):
            self._from_module(filename)

    def _is_file_ending_correct(self, filename: str) -> bool:
        """
        Method to check if file extension is supported.
        Supported types are: .yaml, .yml and .py
        """
        return filename.endswith((".yaml", ".yml", ".py"))


# Re-export `available_platforms` from simnos.plugins.nos so existing callers
# (e.g. `from simnos.core.nos import available_platforms`) keep working after
# the source of truth was moved to the dynamically-derived registry. Placed
# at file end to avoid circular import with simnos.plugins.nos.
# `import X as X` + explicit `__all__` keeps mypy strict mode happy about
# implicit re-export.
from simnos.plugins.nos import available_platforms as available_platforms  # noqa: E402

__all__ = ["Nos", "available_platforms"]
