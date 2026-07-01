"""Centralized registry of platform-specific test quirks.

Each entry pairs a platform with a :class:`Quirk` recording *why* the quirk
exists (`reason`), the tracking issue if any (`issue`), and when it was last
reviewed (`last_reviewed`). Keeping these together -- instead of scattering
bare sets/dicts across test modules -- makes it visible at a glance which
quirks could be retired next.

Consumers test membership (``platform in QUIRK_DICT``); the reason is surfaced
in the skip/xfail message so failures explain themselves.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Quirk:
    """A known platform-specific deviation exercised by the test suite."""

    reason: str
    issue: str | None  # "#NNN" or a URL; None means not yet tracked
    last_reviewed: str  # "YYYY-MM-DD"


# Platforms where netmiko's session_preparation() emits "Unknown command"
# during init because of a missing command definition. Fix individually.
INIT_UNKNOWN_CMD_ALLOWED: dict[str, Quirk] = {
    "aruba_os": Quirk("no paging command", None, "2026-06-08"),
    "brocade_fastiron": Quirk("enable (repeated)", None, "2026-06-08"),
    "dlink_ds": Quirk("disable clipaging", None, "2026-06-08"),
    "huawei_smartax": Quirk("enable password", "#70", "2026-06-08"),
    "ruckus_fastiron": Quirk("enable (repeated), skip-page-display", None, "2026-06-08"),
    "vyatta_vyos": Quirk("set terminal width 512", None, "2026-06-08"),
}

# Platforms where enable()/config_mode() cannot be exercised because they need
# a secret or sudo. Their initial (show) commands are still tested.
SKIP_ENABLE: dict[str, Quirk] = {
    "alcatel_sros": Quirk("requires enable-admin with secret", None, "2026-06-08"),
    "cisco_apic": Quirk("Linux-based, requires sudo -s for enable", None, "2026-06-08"),
    "edgecore": Quirk("Linux-based (SONiC), requires sudo -s for enable", None, "2026-06-08"),
    "ericsson_ipos": Quirk("requires administrator with secret", None, "2026-06-08"),
    "linux": Quirk("Linux-based, requires sudo -s for enable", None, "2026-06-08"),
    "yamaha": Quirk("requires enable with secret", None, "2026-06-08"),
}

# Python-plugin platforms whose "all commands" sweep is xfailed.
# huawei_smartax was xfailed here until #115: its callable `return`/`disable`
# now carry a static `changes_prompt` flag so the netmiko sweep skips them
# instead of running them into a ReadTimeout. No platform is currently quirked.
XFAIL_PY_ALL_COMMANDS: dict[str, Quirk] = {}
