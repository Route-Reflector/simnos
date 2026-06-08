"""Validation pins for the platform quirk registry metadata.

These guard against metadata rot in ``tests/_platform_quirks.py``: every
``Quirk`` must carry a non-empty reason, a well-formed (or absent) issue
reference, and an ISO ``YYYY-MM-DD`` review date.
"""

import re

import pytest

from tests._platform_quirks import (
    INIT_UNKNOWN_CMD_ALLOWED,
    SKIP_ENABLE,
    XFAIL_PY_ALL_COMMANDS,
    Quirk,
)

_ALL_QUIRKS: dict[str, dict[str, Quirk]] = {
    "INIT_UNKNOWN_CMD_ALLOWED": INIT_UNKNOWN_CMD_ALLOWED,
    "SKIP_ENABLE": SKIP_ENABLE,
    "XFAIL_PY_ALL_COMMANDS": XFAIL_PY_ALL_COMMANDS,
}

_ISSUE_RE = re.compile(r"^(#\d+|https?://\S+)$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _all_entries() -> list[tuple[str, str, Quirk]]:
    """Flatten every registry into (registry_name, platform, quirk) tuples."""
    return [(name, platform, quirk) for name, registry in _ALL_QUIRKS.items() for platform, quirk in registry.items()]


@pytest.mark.parametrize("registry_name, platform, quirk", _all_entries())
def test_quirk_reason_is_non_empty(registry_name: str, platform: str, quirk: Quirk):
    """Every quirk explains itself with a non-empty reason."""
    assert quirk.reason.strip(), f"{registry_name}[{platform!r}] has an empty reason"


@pytest.mark.parametrize("registry_name, platform, quirk", _all_entries())
def test_quirk_issue_is_well_formed_or_none(registry_name: str, platform: str, quirk: Quirk):
    """`issue` is None (untracked) or a '#NNN' / URL reference -- never empty string."""
    if quirk.issue is None:
        return
    assert _ISSUE_RE.match(quirk.issue), f"{registry_name}[{platform!r}] has a malformed issue: {quirk.issue!r}"


@pytest.mark.parametrize("registry_name, platform, quirk", _all_entries())
def test_quirk_last_reviewed_is_iso_date(registry_name: str, platform: str, quirk: Quirk):
    """`last_reviewed` is an ISO YYYY-MM-DD date."""
    assert _DATE_RE.match(quirk.last_reviewed), (
        f"{registry_name}[{platform!r}] has a non-ISO last_reviewed: {quirk.last_reviewed!r}"
    )
