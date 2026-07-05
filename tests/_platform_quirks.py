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

# Platforms where enable()/config_mode() need an interactive secret or sudo
# password. As of #338 (challenge mechanism, Phase 2) all such platforms model
# the sub-prompt as A3 `challenge:` data and netmiko's enable() drives it, so
# this quirk is now empty — the enable/config sweep runs for every platform.
SKIP_ENABLE: dict[str, Quirk] = {}

# Python-plugin platforms whose "all commands" sweep is xfailed.
# huawei_smartax was xfailed here until #115 (then via a `changes_prompt`
# marker); since #317 P-2 its transitions are static A3 data (`new_mode` /
# `exit`), which the sweep skips natively. No platform is currently quirked.
XFAIL_PY_ALL_COMMANDS: dict[str, Quirk] = {}
