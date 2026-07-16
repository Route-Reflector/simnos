"""
Intentionally broken NOS plugin: defines TWO locally-defined BaseDevice
subclasses, so `Nos._from_module` raises ValueError during the build
phase (#241 / D5 — exactly one local subclass expected). Replaces the
pre-#241 `broken_device_name_module.py` (DEVICE_NAME pointing at a
missing class), whose failure mode disappeared together with the
DEVICE_NAME mechanism. Used to pin that a broken plugin leaves Nos
state untouched (#232 build-before-commit) and never leaks into a
running shell via hot reload.
"""

from simnos.plugins.nos.base_device import BaseDevice


class DeviceA(BaseDevice):
    """First local device class — one too many together with DeviceB."""


class DeviceB(BaseDevice):
    """Second local device class — triggers the multiple-subclass ValueError."""
