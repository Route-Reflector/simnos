"""
Intentionally broken NOS plugin: DEVICE_NAME points to a class that does
not exist, so `Nos._from_module` raises AttributeError after the module
itself imports fine. Used to pin that a broken plugin leaves Nos state
untouched (#232 build-before-commit) and never leaks into a running shell
via hot reload.
"""

NAME = "broken_module"
INITIAL_PROMPT = "{base_prompt}$"
DEVICE_NAME = "MissingClass"

commands = {"polluting command": {"output": "x", "help": "x"}}
