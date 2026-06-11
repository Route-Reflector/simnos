"""
Network Operating Systems (NOS). Base class to build NOS plugins instances to use with SIMNOS.
"""

import copy
import importlib.util
import logging
import os
import types

import yaml

from simnos.core.platform_loader import load_platform_dir
from simnos.core.pydantic_models import ModelNosAttributes
from simnos.core.resolved_command import ResolvedPlatform

log = logging.getLogger(__name__)


def _find_device_classes(module: types.ModuleType) -> list[type]:
    """Return the BaseDevice subclasses defined locally in `module`.

    Locally defined means ``obj.__module__ == module.__name__``: a class
    defined while executing the module carries the module's own name
    (the fixed spec name under `_from_module`, the package name under a
    regular import — both sides of the comparison track the same load
    mechanism), while an imported class keeps its origin module name.
    Import-mixins (helper devices, type-annotation imports) are
    therefore never picked up (#241 / D5). Shared with the platform
    contract test (tests/plugins/test_platforms.py), which applies the
    same criterion over package-imported plugin modules.

    Deduplicated by class object: an alias to a local class
    (``Device = LocalDevice``) appears twice in ``vars(module)`` but is
    one definition, not a second subclass (3rd code review 🦊 #1).
    """
    # Lazy import: `simnos.plugins` must not be imported while this module
    # itself is still initializing — see the `available_platforms`
    # re-export at the end of this file, which is deferred for the same
    # circular-import reason.
    from simnos.plugins.nos.platforms_py._templates.base_template import BaseDevice

    return list(
        dict.fromkeys(
            obj
            for obj in vars(module).values()
            if isinstance(obj, type)
            and issubclass(obj, BaseDevice)
            and obj is not BaseDevice
            and obj.__module__ == module.__name__
        )
    )


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
        # Constructor-passed commands are an inflow like any other: keep
        # the caller's dict untouched and normalize the runtime copy
        # (#244 / D3). A non-dict value is passed through for the trailing
        # `validate()` to reject with the usual ValidationError.
        commands = commands or {}
        if isinstance(commands, dict):
            commands = self.normalize_command_prompts(copy.deepcopy(commands))
        self.commands = commands
        self.initial_prompt = initial_prompt
        self.auth: str | None = None
        self.enable_prompt: str | None = None
        self.config_prompt: str | None = None
        self.device = None
        self.configuration_file = configuration_file
        # A3 form (#264 / PR-2): an A3 platform dir loads straight into a
        # `ResolvedPlatform` (modes + resolved commands) here, instead of the
        # legacy `self.commands` dict + scalar prompts. None until an A3 dir is
        # loaded; the shell branches on it (D4, D6). A py module loaded *after*
        # an A3 dir still populates `self.commands` (its dynamic handlers), which
        # the shell merges over the A3 statics — the legacy py-override precedence.
        self.resolved_platform: ResolvedPlatform | None = None
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

        Only the schema fields are passed (explicitly extracted via
        `ModelNosAttributes.model_fields`) — `self.__dict__` also holds
        non-schema runtime state (`device`, `configuration_file`) that
        must never reach the model (#244 / D8).
        """
        ModelNosAttributes(**{field: getattr(self, field) for field in ModelNosAttributes.model_fields})
        log.debug("%s NOS attributes validation succeeded", self.name)

    @staticmethod
    def normalize_command_prompts(commands: dict) -> dict:
        """Normalize each command's `prompt` to `list[str] | None`.

        Called on a deepcopied candidate (never on caller-owned dicts or
        module-level `commands` constants). Authoring accepts both a bare
        str (sugar) and a list; runtime consumers see lists only, so
        read-side isinstance branches are unnecessary (#244 / P-12c).
        """
        for cmd in commands.values():
            if not isinstance(cmd, dict):
                # Malformed value — left for the ModelNosAttributes
                # validation to reject (one error surface, not two).
                continue
            prompt = cmd.get("prompt")
            if isinstance(prompt, str):
                cmd["prompt"] = [prompt]
        return commands

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
        :raises ValueError: if the 'commands' value is not a mapping, or
            if `data` holds a top-level key outside the
            `ModelNosAttributes` schema (a typo like `enable_promt` used
            to be dropped silently, #244 / D8)
        :raises pydantic.ValidationError: if the merged result would not
            satisfy `ModelNosAttributes` — validated before any attribute
            is committed, so malformed data never leaves partial state
            behind (same no-partial-state contract as `_from_module`,
            #232); this also covers the hot-reload path, which calls
            `from_file` directly and never reaches `__init__`'s trailing
            `validate()` (#244 / D8)
        """
        unknown = data.keys() - ModelNosAttributes.model_fields.keys()
        if unknown:
            raise ValueError(f"NOS data has unknown top-level field(s): {sorted(unknown)}")
        commands = data.get("commands", {})
        if not isinstance(commands, dict):
            raise ValueError(f"NOS data 'commands' must be a mapping (got {type(commands).__name__})")
        # Normalize a deepcopied candidate — never the caller's dict, which
        # stays in its original authoring form (#244 / D3).
        candidate = self.normalize_command_prompts(copy.deepcopy(commands))
        # Validate the exact post-commit state (a merged view, not `data`
        # alone): commands merge cumulatively across multi-file loads and
        # scalars keep their current value when absent from `data`.
        merged_name = data.get("name", self.name)
        merged_initial_prompt = data.get("initial_prompt", self.initial_prompt)
        merged_auth = data.get("auth", self.auth)
        merged_enable_prompt = data.get("enable_prompt", self.enable_prompt)
        merged_config_prompt = data.get("config_prompt", self.config_prompt)
        ModelNosAttributes(
            name=merged_name,
            initial_prompt=merged_initial_prompt,
            auth=merged_auth,
            enable_prompt=merged_enable_prompt,
            config_prompt=merged_config_prompt,
            commands={**self.commands, **candidate},
        )
        # Commit phase — mirrors the validated merged view (normalized
        # candidate included), so the validated state and the committed
        # state cannot drift apart.
        self.name = merged_name
        self.commands.update(candidate)
        self.initial_prompt = merged_initial_prompt
        self.auth = merged_auth
        self.enable_prompt = merged_enable_prompt
        self.config_prompt = merged_config_prompt

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
        ``DEFAULT_CONFIGURATION``) and a ``commands`` dict; the device class
        is auto-detected as the module's single locally-defined `BaseDevice`
        subclass, if any (see `_find_device_classes` — the legacy
        ``DEVICE_NAME`` constant is ignored with a warning since #241).
        See :mod:`simnos.plugins.nos.platforms_py.cisco_ios` for a live example.

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
        # Build/validate everything that can still fail BEFORE mutating self,
        # so a broken plugin raises without leaving partial state behind
        # (#232 cross-review: attrs/commands used to be committed before the
        # device-class validation, so the hot-reload per-file guard skipped
        # the file but a later `commands.update(nos.commands)` leaked the
        # broken plugin's commands into the running shell).
        module_commands = getattr(module, "commands", {})
        if not isinstance(module_commands, dict):
            raise ValueError(f"Module '{filename}' 'commands' must be a mapping (got {type(module_commands).__name__})")
        # Normalize a deepcopied candidate — never the module-level
        # `commands` constant, which stays in its authoring form (#244 /
        # D3; deepcopy treats callables as atomic, so handler identity is
        # preserved).
        candidate_commands = self.normalize_command_prompts(copy.deepcopy(module_commands))
        # Validate the exact post-commit state before committing, mirroring
        # `from_dict`'s merged view (#244 / D8) — this also covers hot
        # reload, which calls `from_file` directly. No top-level key check
        # here: unrelated module-level names are legitimate in a py plugin
        # (only `_MODULE_ATTR_MAP` constants are mapped).
        ModelNosAttributes(
            **{
                self_attr: getattr(module, module_attr, getattr(self, self_attr))
                for module_attr, self_attr in self._MODULE_ATTR_MAP.items()
            },
            commands={**self.commands, **candidate_commands},
        )
        device_classes = _find_device_classes(module)
        if len(device_classes) > 1:
            raise ValueError(
                f"Module '{filename}' defines multiple BaseDevice subclasses "
                f"({', '.join(sorted(c.__name__ for c in device_classes))}); expected exactly one"
            )
        if hasattr(module, "DEVICE_NAME"):
            # G4 (#241) removed the DEVICE_NAME indirection; the device class
            # is auto-detected now. Nudge plugin authors to drop the leftover.
            log.warning(
                "Module '%s' still defines DEVICE_NAME; it is deprecated and ignored (auto-detection is used)",
                filename,
            )
        device = None
        if device_classes:
            configuration_file = self.configuration_file or getattr(module, "DEFAULT_CONFIGURATION", None)
            device = device_classes[0](configuration_file=configuration_file)
        else:
            log.warning("Module '%s' defines no BaseDevice subclass; no device will be set from this module", filename)
        # Commit phase — nothing below is expected to raise.
        for module_attr, self_attr in self._MODULE_ATTR_MAP.items():
            setattr(self, self_attr, getattr(module, module_attr, getattr(self, self_attr)))
        # P-7 (#241): a py module replaces same-named already-loaded
        # commands wholesale (typically yaml-defined ones, but multi-file
        # py loads count too; per-command full replacement, no deep
        # merge) — make the implicit precedence observable for authors.
        overridden = self.commands.keys() & candidate_commands.keys()
        if overridden:
            log.debug(
                "module '%s' overrides %d already-loaded command(s): %s",
                filename,
                len(overridden),
                sorted(overridden),
            )
        self.commands.update(candidate_commands)
        if self.name == "SimNOS":
            log.warning(
                "Module '%s' does not define NAME; falling back to default 'SimNOS' "
                "(plugin will be registered under that key)",
                filename,
            )
        if device_classes:
            # Only a detected class updates the device — a no-device module
            # keeps whatever a previously loaded file set (same "existing
            # device survives" semantics as the pre-#241
            # `if classname is not None` commit).
            self.device = device

    def _from_platform_dir(self, path: str) -> None:
        """Load an A3 platform directory into `self.resolved_platform` (#264 / D6).

        Unlike the legacy `_from_yaml` / `_from_module` paths, this does not
        populate `self.commands` / the scalar prompts — the A3 form normalizes
        straight to a `ResolvedPlatform`. The platform name is the directory
        name (D1); a py module loaded after this dir still fills `self.commands`
        with its dynamic handlers, which the shell merges over the A3 statics.

        :param path: directory holding ``platform.yaml`` + ``commands/``
        :raises ValueError: on any A3 schema / reference / render violation
        """
        self.resolved_platform = load_platform_dir(path)
        self.name = os.path.basename(os.path.normpath(path))

    def from_file(self, filename: str) -> None:
        """
        Method to load NOS from an A3 platform directory, a YAML file, or a Python file

        :param filename: OS path string to an A3 platform dir, or a
            `.yaml/.yml` / `.py` file with NOS data
        """
        # An A3 platform is a directory (holds platform.yaml + commands/), not a
        # file — dispatch on that before the extension check (#264 / D6).
        if os.path.isdir(filename):
            self._from_platform_dir(filename)
            return
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
