"""
This module is the point of entry for all NOS plugins.

It gets the names and filenames to load the NOS plugins
later whenever needed (lazy loading).
Registration order (#264 / D6): A3 platform dirs (``platforms/<name>/``) are
registered first; Python modules then append to their platform's existing
entry. An A3 dir is required (#317 P-4) — a py module with no co-named A3 dir
is warned about and not registered. The legacy monolithic
``platforms_yaml/<name>.yaml`` form was removed in v3 (#264 PR-3).

With .py modules we can have functionality (the device class + the A3
``handler:`` namespace), while the A3 dir carries the static command data.

``available_platforms`` is the public derived view of this registry —
``simnos.core.nos.available_platforms`` re-exports it for backward
compatibility with callers that still import from the core module.

Inventory refers to a platform by its ``device_type`` (#266): besides the
internal platform name (= directory basename, the registry key), a platform's
``netmiko_device_type`` / ``ntc_platform`` aliases also resolve to it via the
``device_type_to_platform`` reverse index built below.

Ownership (#346): once this module's import completes, ``nos_plugins`` is
frozen — production code never writes to it again. Runtime registrations
(``SimNOS(plugins=[...])``) go to the per-instance copy ``SimNOS.nos_plugins``
and never land here, so instances cannot contaminate each other. This is a
*logical* freeze (an ownership contract, not ``MappingProxyType``-enforced
immutability); tests may still deliberately monkeypatch entries in — the
dynamic fallback in ``resolve_device_type`` remains as that injection seam.
"""

import glob
import logging
import os

from pydantic import ValidationError
import yaml

from simnos.core.platform_loader import PLATFORM_META_FILENAME, _load_platform_meta

log = logging.getLogger(__name__)

nos_plugins: dict[str, list[str]] = {}

current_file_path = os.path.abspath(__file__)
current_directory = os.path.dirname(current_file_path)

# Load A3 platform dirs (the command-data form, #264 / D6): each
# `platforms/<name>/` holding a `platform.yaml` is one platform, discovered by
# directory name (no parse needed for the registry).
_a3_platform_dirs: dict[str, str] = {}
platforms_directory_a3 = os.path.join(current_directory, "platforms")
if os.path.isdir(platforms_directory_a3):
    for entry in sorted(os.listdir(platforms_directory_a3)):
        dirpath = os.path.join(platforms_directory_a3, entry)
        if os.path.isfile(os.path.join(dirpath, PLATFORM_META_FILENAME)):
            nos_plugins[entry] = [dirpath]
            _a3_platform_dirs[entry] = dirpath

# Load the python handler modules, appending each to its platform's existing
# A3 entry (registration order: A3 dir first, py module last).
# The glob is non-recursive on purpose: only platform handler modules may live
# directly in `platforms_py/` — shared infra (the `BaseDevice` base class) lives
# outside it in `plugins/nos/base_device.py` so it never surfaces as a platform
# (#239 / #350 — previously a filename filter, then a `_templates/` subpackage,
# did this job).
# A py module with no co-named A3 dir is NOT registered (#317 P-4): py-only
# platforms are gone (the merge requires A3 command data), and registering one
# would only defer the failure to `Host.start` — warn at import instead, so the
# orphan is visible the moment the registry is built.
platforms_directory_py: str = os.path.join(current_directory, "platforms_py")
py_files = glob.glob(os.path.join(platforms_directory_py, "*.py"))
py_files = [file for file in py_files if os.path.basename(file) != "__init__.py"]
for file in py_files:
    platform_name: str = os.path.basename(file).removesuffix(".py")
    if platform_name in nos_plugins:
        nos_plugins[platform_name].append(file)
    else:
        log.warning(
            "platforms_py/%s.py has no matching A3 platform dir (platforms/%s/); not registered — "
            "an A3 dir is required since #317 P-4 (the py module supplies handlers only)",
            platform_name,
            platform_name,
        )

# Single source of truth for "supported platform" — derived from `nos_plugins`
# so that adding an A3 dir under platforms/ or a .py file under platforms_py/ is
# the only step needed to extend the registry. Sorted for deterministic order;
# a tuple so consumers cannot mutate the registry view in place (#237).
available_platforms: tuple[str, ...] = tuple(sorted(nos_plugins.keys()))


def _build_device_type_index() -> dict[str, str]:
    """Build the ``device_type -> platform`` (registry key) reverse index (#266 / D2).

    Each platform contributes up to three accepted ``device_type`` spellings:
    its own name (*identity*), and the ``netmiko_device_type`` / ``ntc_platform``
    aliases declared in ``platform.yaml``. Identity is registered first so a
    platform name always wins over a colliding alias from another platform.

    Collision rule (value comparison, not key presence): re-registering the same
    ``(key -> platform)`` pair is a harmless no-op — the common case today, since
    every platform currently has ``name == netmiko_device_type == ntc_platform``.
    A key that would map to a *different* platform is a real collision and raises.
    ``None`` / empty aliases are not registered.

    Degradation (#266 / R2): a ``platform.yaml`` that fails to parse (YAML / I/O /
    schema) is skipped with a warning rather than aborting the whole import. The
    platform stays reachable by its identity name and fails loudly later at
    ``Host.start()`` / ``load_platform_dir``.
    """
    index: dict[str, str] = {}

    def register(key: str | None, platform: str) -> None:
        if not key:
            return  # None / empty string is not a usable device_type
        prev = index.get(key)
        if prev is not None and prev != platform:
            raise ValueError(f"device_type alias collision: {key!r} maps to both {prev!r} and {platform!r}")
        index[key] = platform

    # Identity first (every registered platform, A3 dir or .py module).
    for platform in nos_plugins:
        register(platform, platform)
    # Aliases come from A3 platform.yaml only (.py modules carry no metadata).
    for platform, dirpath in _a3_platform_dirs.items():
        try:
            meta = _load_platform_meta(os.path.join(dirpath, PLATFORM_META_FILENAME))
        except (yaml.YAMLError, OSError, ValidationError, ValueError) as exc:
            log.warning("device_type index: skipping %s metadata (%s) — identity name only", platform, exc)
            continue
        register(meta.netmiko_device_type, platform)
        register(meta.ntc_platform, platform)
    return index


device_type_to_platform: dict[str, str] = _build_device_type_index()


def resolve_device_type(device_type: str) -> str | None:
    """Resolve an inventory ``device_type`` to its platform registry key (#266 / D2).

    Returns the internal platform name for any accepted ``device_type``:
    - a ``netmiko_device_type`` / ``ntc_platform`` alias, via the static index;
    - the own name (*identity*) of any platform present in ``nos_plugins``,
      checked dynamically so a test-injected entry (the monkeypatch seam the
      frozen registry deliberately keeps, #346) still resolves by its own name
      even though the import-time index predates it. ``SimNOS(plugins=[...])``
      registrations do NOT land here — they live on the per-instance copy and
      resolve via the raw-key fallback below.

    Returns ``None`` when the value is not a known device_type, which lets
    callers fall back to the raw value (the chokepoint then hands it to the
    registry ``.get(key, key)`` as-is).
    """
    mapped = device_type_to_platform.get(device_type)
    if mapped is not None:
        return mapped
    if device_type in nos_plugins:
        return device_type
    return None


def assert_platform_supported(platform: str) -> None:
    """Raise ValueError if `platform` is not a registered/resolvable device_type.

    Accepts either an internal platform name or a ``netmiko_device_type`` /
    ``ntc_platform`` alias (anything `resolve_device_type` recognizes). Shared by
    `Host._validate` and the `@simnos` test decorator so the check and its error
    message live next to the registry they guard (#237, G1 follow-up; #266 D2
    broadened it from a plain `available_platforms` membership test to alias
    resolution). The message lists the canonical platform names; aliases resolve
    to one of them.
    """
    if resolve_device_type(platform) is None:
        # Join the names so the user-facing message does not leak the
        # registry container type (tuple vs list repr). Spell out that
        # netmiko/ntc aliases are accepted too, so a user who typed an alias
        # is not misled by the canonical-only list (#266 1st round gemini #4).
        # Built from the live registry (not the import-time `available_platforms`
        # tuple) so test-injected platforms appear, matching what
        # `resolve_device_type` just checked against (#344; the registry is
        # otherwise frozen after import — #346).
        raise ValueError(
            f"Platform {platform} is not supported by SIMNOS. Supported platforms are: "
            f"{', '.join(sorted(nos_plugins))} (their netmiko_device_type / ntc_platform aliases are also accepted)."
        )
