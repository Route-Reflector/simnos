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


# Platforms where netmiko's session_preparation() hits the platform's
# unknown-command answer during init. Missing command definitions are fixed in
# platform data; an entry stays only when the error is what the real device
# answers too.
INIT_UNKNOWN_CMD_ALLOWED: dict[str, Quirk] = {
    # netmiko's HuaweiSmartAXSSH.enable() uses pattern="" and so always sends
    # the secret after `enable`. Real SmartAX enters `#` without a password, so
    # the device rejects that stray line as well — faithful, not a data gap.
    "huawei_smartax": Quirk("secret sent after a password-less enable", "#70", "2026-09-25"),
    # netmiko's RuckusFastironBase.enable() resends `enable` (up to 3 times)
    # until it sees a password prompt or "No password has been assigned". The
    # shipped `enable` models no enable password and enters `#` silently, so
    # the resends hit the unknown-command answer. Adding a password challenge
    # would fail every connect made without `secret`; fixing it needs the real
    # no-password wording from a device capture.
    "brocade_fastiron": Quirk("enable resent until a password prompt appears", None, "2026-09-25"),
    "ruckus_fastiron": Quirk("enable resent until a password prompt appears", None, "2026-09-25"),
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
