"""
Well-formed NOS plugin that imports other plugins' BaseDevice subclasses.

Pins the `__module__` guard of `Nos._find_device_classes` (#241 / D5):
the imported `CiscoIOS` / `AristaEOS` keep their origin `__module__` and
must NOT be detected as this module's device — only the locally-defined
subclass counts, so even MULTIPLE import-mixins neither trip the
multiple-subclass ValueError nor steal the device slot (a regression to
a bare `issubclass` filter would be caught here, 3rd code review 🐙 #3).
"""

from simnos.plugins.nos.platforms_py._templates.base_template import BaseDevice
from simnos.plugins.nos.platforms_py.arista_eos import AristaEOS  # noqa: F401 — import mixin on purpose
from simnos.plugins.nos.platforms_py.cisco_ios import CiscoIOS  # noqa: F401 — import mixin on purpose


class LocalDevice(BaseDevice):
    """The single locally-defined device class — the one to detect."""
