"""
Well-formed NOS plugin that imports another plugin's BaseDevice subclass.

Pins the `__module__` guard of `Nos._find_device_classes` (#241 / D5):
the imported `CiscoIOS` keeps its origin `__module__` and must NOT be
detected as this module's device — only the locally-defined subclass
counts, so the import-mixin neither trips the multiple-subclass
ValueError nor steals the device slot.
"""

from simnos.plugins.nos.platforms_py._templates.base_template import BaseDevice
from simnos.plugins.nos.platforms_py.cisco_ios import CiscoIOS  # noqa: F401 — import mixin on purpose

NAME = "importing_module"
INITIAL_PROMPT = "{base_prompt}>"


class LocalDevice(BaseDevice):
    """The single locally-defined device class — the one to detect."""


commands = {"noop": {"output": "ok", "help": "noop"}}
