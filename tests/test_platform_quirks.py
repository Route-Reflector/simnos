"""Validation pins for the platform quirk registry metadata.

These guard against metadata rot in ``tests/_platform_quirks.py``: every
``Quirk`` must carry a non-empty reason, a well-formed (or absent) issue
reference, and a real ISO ``YYYY-MM-DD`` review date, and every registry key
must be a known platform (typo / stale-entry guard).
"""

import datetime
import re

import pytest

from simnos.core.nos import available_platforms
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
def test_quirk_last_reviewed_is_real_iso_date(registry_name: str, platform: str, quirk: Quirk):
    """`last_reviewed` is a real ISO YYYY-MM-DD date (rejects e.g. 2026-99-99)."""
    try:
        datetime.date.fromisoformat(quirk.last_reviewed)
    except ValueError:
        pytest.fail(f"{registry_name}[{platform!r}] has an invalid last_reviewed: {quirk.last_reviewed!r}")


@pytest.mark.parametrize("registry_name, platform, quirk", _all_entries())
def test_quirk_platform_is_a_known_platform(registry_name: str, platform: str, quirk: Quirk):
    """Quirk keys must be real platforms (guards against typos / stale entries)."""
    assert platform in available_platforms, f"{registry_name}[{platform!r}] is not a known platform (typo or removed?)"
