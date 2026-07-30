"""
Network Operating Systems (NOS). Base class to build NOS plugins instances to use with SIMNOS.
"""

import importlib.util
import inspect
import logging
import os
import threading
import types
from typing import TYPE_CHECKING

from simnos.core.platform_loader import load_platform_dir
from simnos.core.resolved_command import ResolvedPlatform

if TYPE_CHECKING:
    from simnos.core.command_contract import CommandHandler

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
    from simnos.plugins.nos.base_device import BaseDevice

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


def _build_handler_namespace(module: types.ModuleType, device_classes: list[type]) -> dict[str, "CommandHandler"]:
    """Collect the A3 ``handler:`` name -> callable namespace from a py module (#317 / P-1, 案D).

    An A3 command's ``handler: <name>`` is resolved against this namespace at
    merge time. `device_classes` is the caller's already-validated list (0 or 1
    entries — `_from_module` rejects >1 local `BaseDevice` subclass before
    calling this), so the per-class loop is effectively single-class; it is
    written as a loop only to no-op cleanly on the no-device case. Two channels:

    - **device-class methods**: walk the device class MRO, skipping ``BaseDevice``
      / ``object`` (so base utilities like ``render`` are never handlers), and
      take each non-``_`` name defined on that class. A more-derived class's
      override wins (normal Python method resolution — an MRO same-name is NOT a
      collision). A ``classmethod`` is rejected loudly: its first arg binds to
      ``cls``, which breaks the `CommandHandler` contract (the shell passes the
      device as the first positional). Only a plain method or a ``staticmethod``
      is a valid handler; anything else on the class (a constant, a ``property``,
      or a callable *instance* / functor) is skipped, not misregistered — only a
      real function / staticmethod is a handler (gemini#1).
    - **module-level functions**: locally defined (``__module__ == module.__name__``,
      the `_find_device_classes` criterion) non-``_`` functions — `inspect.isfunction`
      excludes imported callables, classes and callable instances.

    A name appearing in BOTH channels is a load-time error (no implicit
    precedence — fail at startup). The caller assigns the result as a fresh dict
    (rollback-safe under hot reload).
    """
    from simnos.plugins.nos.base_device import BaseDevice

    class_ns: dict[str, CommandHandler] = {}
    for device_cls in device_classes:
        for cls in device_cls.__mro__:
            if cls in (BaseDevice, object):
                continue
            for name, raw in vars(cls).items():
                # A more-derived class earlier in the MRO already claimed this
                # name (override) — skip the base definition.
                if name.startswith("_") or name in class_ns:
                    continue
                if isinstance(raw, classmethod):
                    raise ValueError(
                        f"handler {name!r} on {cls.__name__} is a classmethod; a command handler must take the "
                        "device as its first argument (a plain method or staticmethod), not `cls`"
                    )
                if isinstance(raw, staticmethod) or inspect.isfunction(raw):
                    # `getattr` on the leaf class resolves the descriptor (a
                    # staticmethod unwraps to its plain function, a method to the
                    # underlying function that takes the device as the first arg).
                    class_ns[name] = getattr(device_cls, name)
                # else: a non-callable class attribute is not a handler — skip it.
    module_ns: dict[str, CommandHandler] = {
        name: obj
        for name, obj in vars(module).items()
        if not name.startswith("_") and inspect.isfunction(obj) and obj.__module__ == module.__name__
    }
    collision = class_ns.keys() & module_ns.keys()
    if collision:
        raise ValueError(
            f"handler name(s) {sorted(collision)} are defined both as a device-class method and a module-level "
            "function; a handler name must be unambiguous (rename one)"
        )
    return {**class_ns, **module_ns}


class Nos:
    """
    Base class to build NOS plugins instances to use with SIMNOS.

    Since #317 P-4 the only command authoring form is the A3 platform dir
    (``platforms/<name>/`` -> `resolved_platform`); a py module supplies the
    device class + the ``handler:`` namespace only. The legacy py dict form
    (``commands`` / scalar prompts / ``from_dict``) was removed.
    """

    def __init__(
        self,
        name: str = "SimNOS",
        filename: str | list[str] | None = None,
        configuration_file: str | None = None,
    ) -> None:
        """
        Method to instantiate Nos Instance

        :param name: NOS plugin name (an A3 platform dir load overwrites it
            with the directory basename)
        :param filename: path(s) to load — an A3 platform dir and/or a ``.py``
            module (see `from_file`)
        :param configuration_file: device configuration file, overrides the
            module's ``DEFAULT_CONFIGURATION``
        """
        self.name = name
        self.auth: str | None = None
        self.device = None
        # Hot-reload serialization lock (#349): guards THIS instance's mutable
        # reload state (the `_NOS_RELOAD_ATTRS` set — `device` / `handlers` /
        # `sources` / `resolved_platform` / ...). The lock lives on the Nos
        # because that is the resource it protects: a pre-registered instance
        # shared by several hosts (`SimNOS(plugins=[Nos(...)])`) hands every
        # host/shell the SAME lock, closing the cross-host mutate race the #281
        # per-host locks could not (each host used to mint its own). Note that
        # `auth` is also rewritten by a reload but servers read it once at
        # construction — hot-reloading `auth:` never affects a live server (an
        # intentional no-op, #349 / Decision 5).
        self.reload_lock: threading.Lock = threading.Lock()
        # Every path handed to `from_file`, in load order — diagnostics only.
        # A py-only Nos keeps the constructor-default name (the module's legacy
        # ``NAME`` constant is no longer read, #317 P-4), so the A3-required
        # error in `build_resolved_platform` names these sources to stay
        # traceable to the offending plugin path.
        self.sources: list[str] = []
        # A3 ``handler:`` namespace (#317 / P-1): name -> callable, populated by
        # `_from_module` from the py plugin's device class + module-level
        # functions. `build_resolved_platform` binds A3 handler refs against it.
        # Rebuilt (fresh dict) on hot reload, so it is a `_NOS_RELOAD_ATTRS` member.
        self.handlers: dict[str, CommandHandler] = {}
        self.configuration_file = configuration_file
        # A3 form (#264 / PR-2): an A3 platform dir loads straight into a
        # `ResolvedPlatform` (modes + resolved commands). None until an A3 dir is
        # loaded; the merge (`build_resolved_platform`) rejects a Nos that never
        # loaded one — the A3 dir is the required authoring form (#317 P-4).
        self.resolved_platform: ResolvedPlatform | None = None
        if isinstance(filename, str):
            self.from_file(filename)
        elif isinstance(filename, list):
            for file in filename:
                self.from_file(file)

    def _from_module(self, filename: str) -> None:
        """
        Method to import NOS behavior from a python file or python module.

        Loads from the .py file using the recipe:
        https://docs.python.org/3/library/importlib.html#importing-a-source-file-directly

        The module supplies dynamic behavior only (#317 P-4): the device class
        is auto-detected as the module's single locally-defined `BaseDevice`
        subclass, if any (see `_find_device_classes`), and the A3 ``handler:``
        namespace (`self.handlers`) is built from the device class methods +
        module-level functions (see `_build_handler_namespace`) so an A3
        platform's `handler:` refs bind at merge time (#317 / P-1). An optional
        ``DEFAULT_CONFIGURATION`` constant points at the device configuration
        file. A legacy ``commands`` dict is rejected loudly — that authoring
        channel was removed (#317 P-2/P-4); other legacy constants (``NAME``,
        the prompt templates) are simply no longer read. See
        :mod:`simnos.plugins.nos.platforms_py.cisco_ios` for a live example.

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
        # so a broken plugin raises without leaving partial state behind (#232).
        # A leftover py `commands` dict is a removed authoring channel; ignoring
        # it silently would hide the author's intent, so it fails at load — the
        # P-3 merge-time guard moved to this earlier boundary in P-4. The check
        # is truthiness, not type: any non-empty `commands` value is an
        # authoring attempt, while a falsy one (an empty dict is the shipped
        # vestige shape) is contentless and stays ignored (same contract as P-3).
        module_commands = getattr(module, "commands", None)
        if module_commands:
            raise ValueError(
                f"Module '{filename}' defines a non-empty `commands` attribute — py dict authoring was removed "
                "(#317); author the commands in the platform's A3 `commands/` dir and keep the py module for "
                "the device class / handlers only"
            )
        device_classes = _find_device_classes(module)
        if len(device_classes) > 1:
            raise ValueError(
                f"Module '{filename}' defines multiple BaseDevice subclasses "
                f"({', '.join(sorted(c.__name__ for c in device_classes))}); expected exactly one"
            )
        # Build the A3 handler namespace before mutating self (#317 / P-1): a
        # classmethod handler / a class-vs-module name collision raises here, so
        # a broken plugin never leaves partial state (same no-partial contract as
        # the device-class validation above).
        new_handlers = _build_handler_namespace(module, device_classes)
        device = None
        if device_classes:
            configuration_file = self.configuration_file or getattr(module, "DEFAULT_CONFIGURATION", None)
            device = device_classes[0](configuration_file=configuration_file)
        else:
            log.warning("Module '%s' defines no BaseDevice subclass; no device will be set from this module", filename)
        # Commit phase — nothing below is expected to raise.
        # Fresh dict (never in-place `.update`): `_NOS_RELOAD_ATTRS` snapshots
        # `handlers` by reference for hot-reload rollback, so a mutable in-place
        # update could not be rolled back. Cumulative later-wins across a
        # multi-file load (#317 / P-1, 案D).
        self.handlers = {**self.handlers, **new_handlers}
        if device_classes:
            # Only a detected class updates the device — a no-device module
            # keeps whatever a previously loaded file set (same "existing
            # device survives" semantics as the pre-#241
            # `if classname is not None` commit).
            self.device = device

    def _from_platform_dir(self, path: str) -> None:
        """Load an A3 platform directory into `self.resolved_platform` (#264 / D6).

        The A3 form normalizes straight to a `ResolvedPlatform`. The platform
        name is the directory name (D1); a py module loaded after this dir
        supplies the device class + `handlers` on top.

        :param path: directory holding ``platform.yaml`` + ``commands/``
        :raises ValueError: on any A3 schema / reference / render violation
        """
        self.resolved_platform = load_platform_dir(path)
        self.name = os.path.basename(os.path.normpath(path))
        # `auth` has live behavior (ssh_server allows auth-none when nos.auth ==
        # "none"); wire it from the A3 meta so it is not a silent dead field
        # (1st round claude #2). Other meta (netmiko_device_type / ntc_platform)
        # is consumed by the platform registry (#266), not here.
        self.auth = self.resolved_platform.auth

    def from_file(self, filename: str) -> None:
        """
        Method to load NOS from an A3 platform directory or a Python file

        :param filename: OS path string to an A3 platform dir (``platform.yaml``
            + ``commands/``), or a `.py` file with a NOS device class / dynamic
            handlers. The legacy monolithic ``.yaml/.yml`` platform form was
            removed in v3 (#264); static command data lives in the A3 dir.
        """
        # An A3 platform is a directory (holds platform.yaml + commands/), not a
        # file — dispatch on that before the extension check (#264 / D6).
        if os.path.isdir(filename):
            self._from_platform_dir(filename)
            self._record_source(filename)
            return
        if not self._is_file_ending_correct(filename):
            raise ValueError(f'Unsupported "{filename}" file extension. Supported: an A3 platform dir or a .py file')
        if not os.path.isfile(filename):
            raise FileNotFoundError(filename)
        self._from_module(filename)
        self._record_source(filename)

    def _record_source(self, filename: str) -> None:
        """Note a successfully loaded source path (diagnostics, see `sources`).

        Deduplicated: hot reload re-runs `from_file` on the same target every
        time it changes, and the diagnostic wants the source *set*, not a
        reload history. Fresh list (never in-place `.append`): the hot-reload
        rollback (`_NOS_RELOAD_ATTRS`) snapshots `sources` by reference — same
        rollback-safety pattern as `handlers` (2nd round 🦊#1 / 🐳#1).
        """
        if filename not in self.sources:
            self.sources = [*self.sources, filename]

    def _is_file_ending_correct(self, filename: str) -> bool:
        """
        Method to check if file extension is supported.

        Only ``.py`` plugin files are loaded as files now; A3 platforms are
        directories (handled before this check). The legacy ``.yaml/.yml``
        monolithic platform form was removed in v3 (#264).
        """
        return filename.endswith(".py")


# Re-export `available_platforms` from simnos.plugins.nos so existing callers
# (e.g. `from simnos.core.nos import available_platforms`) keep working after
# the source of truth was moved to the dynamically-derived registry. Placed
# at file end to avoid circular import with simnos.plugins.nos.
# `import X as X` + explicit `__all__` keeps mypy strict mode happy about
# implicit re-export.
from simnos.plugins.nos import available_platforms as available_platforms  # noqa: E402

__all__ = ["Nos", "available_platforms"]
