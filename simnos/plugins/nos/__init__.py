"""
This module is the point of entry for all NOS plugins.

It gets the names and filenames to load the NOS plugins
later whenever needed (lazy loading).
The NOS plugins are loaded first, using the .py modules and
then the .yaml files in the platforms directory for those which are left.

With .py modules we can have functionality, while using YAML is only
intended for quick development of new NOS plugins.
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
# `base_template.py` is the plugin authoring template (BaseDevice example for
# new NOS plugins to subclass), not a user-facing platform. Exclude it from
# the registry so it does not surface in `available_platforms` / parametrized
# tests.
platforms_directory_py: str = os.path.join(current_directory, "platforms_py")
py_files = glob.glob(os.path.join(platforms_directory_py, "*.py"))
py_files = [file for file in py_files if not file.endswith(("__init__.py", "base_template.py"))]
for file in py_files:
    platform_name: str = os.path.basename(file).replace(".py", "")
    if platform_name in nos_plugins:
        nos_plugins[platform_name].append(file)
    else:
        nos_plugins[platform_name] = [file]

# Single source of truth for "supported platform" — derived from `nos_plugins`
# so that adding a yaml/py file under platforms_yaml/ or platforms_py/ is the
# only step needed to extend the registry. Sorted for deterministic order.
available_platforms: list[str] = sorted(nos_plugins.keys())
