"""
This module is the point of entry for all NOS plugins.

It gets the names and filenames to load the NOS plugins
later whenever needed (lazy loading).
The NOS plugins are loaded first from YAML files, then Python modules
override or extend any existing entries.

With .py modules we can have functionality, while using YAML is only
intended for quick development of new NOS plugins.

``available_platforms`` is the public derived view of this registry —
``simnos.core.nos.available_platforms`` re-exports it for backward
compatibility with callers that still import from the core module.
"""

import glob
import os

nos_plugins: dict = {}

current_file_path = os.path.abspath(__file__)
current_directory = os.path.dirname(current_file_path)

# load NOS from YAML files
platforms_directory_yaml = os.path.join(current_directory, "platforms_yaml")
yaml_files = glob.glob(os.path.join(platforms_directory_yaml, "*.yaml"))
for file in yaml_files:
    platform_name: str = os.path.basename(file).replace(".yaml", "")
    nos_plugins[platform_name] = [file]

# load NOS from python modules updating the NOS.
# The glob is non-recursive on purpose: authoring templates (BaseDevice in
# `platforms_py/_templates/`) live in a subpackage and never surface as
# platforms (#239 — previously a filename filter excluded base_template.py).
platforms_directory_py: str = os.path.join(current_directory, "platforms_py")
py_files = glob.glob(os.path.join(platforms_directory_py, "*.py"))
py_files = [file for file in py_files if not file.endswith("__init__.py")]
for file in py_files:
    platform_name: str = os.path.basename(file).replace(".py", "")
    if platform_name in nos_plugins:
        nos_plugins[platform_name].append(file)
    else:
        nos_plugins[platform_name] = [file]

# Single source of truth for "supported platform" — derived from `nos_plugins`
# so that adding a yaml/py file under platforms_yaml/ or platforms_py/ is the
# only step needed to extend the registry. Sorted for deterministic order;
# a tuple so consumers cannot mutate the registry view in place (#237).
available_platforms: tuple[str, ...] = tuple(sorted(nos_plugins.keys()))


def assert_platform_supported(platform: str) -> None:
    """Raise ValueError if `platform` is not a registered NOS plugin.

    Shared by `Host._validate` and the `@simnos` test decorator so the
    check and its error message live next to the registry they guard
    (#237, G1 follow-up).
    """
    if platform not in available_platforms:
        # Join the names so the user-facing message does not leak the
        # registry container type (tuple vs list repr).
        raise ValueError(
            f"Platform {platform} is not supported by SIMNOS. Supported platforms are: {', '.join(available_platforms)}"
        )
