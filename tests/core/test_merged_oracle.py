"""Merged-view oracle: served runtime view == frozen P-2 snapshot (#317 P-2, lives until P-4).

For the three platforms whose py ``commands`` dict P-2 migrated to A3, this
gate pins the *merged runtime view* — ``build_resolved_platform`` over the full
registry inflow (BASIC + A3 + py handler namespace), i.e. exactly what
``Host.start`` serves — against ``tests/assets/oracle_merged/<platform>.json``.

Provenance: the snapshots were frozen at the P-2 migration and verified against
the pre-migration merged view (py inflow still present): all axes were equal
except the intended handler->static conversions, whose bytes are pinned
separately by ``tests/plugins/test_p2_migration_parity.py`` against
pre-migration renders frozen under ``tests/assets/p2_migration_wire/``.

Why keep it until P-4 (design #317, 1st round codex#3): the byte-parity goldens
cover only cisco_ios scenarios, so when P-3 reworks the merge (inventory A3
normalization, BASIC native `ResolvedCommand`s) and P-4 removes the legacy
adapter, this full-surface projection is the last defense that the served view
of the formerly-py platforms did not drift. Re-baseline an *intentional* A3
edit with ``python regen_merged_oracle_snapshots.py <platform>`` and review the
snapshot diff as a golden file.
"""

import json
import os

import pytest

from regen_merged_oracle_snapshots import MERGED_ORACLE_PLATFORMS, SNAPSHOT_DIR, project_merged_platform


@pytest.mark.parametrize("platform", MERGED_ORACLE_PLATFORMS)
def test_merged_view_matches_frozen_snapshot(platform):
    """The served merged projection equals the frozen P-2 snapshot."""
    with open(os.path.join(SNAPSHOT_DIR, f"{platform}.json"), encoding="utf-8") as fh:
        snapshot = json.load(fh)
    # JSON round-trips tuples to lists; matching the A3 oracle's compare shape.
    projection = json.loads(json.dumps(project_merged_platform(platform)))

    assert set(projection) == set(snapshot), f"{platform}: merged command set differs from snapshot"
    mismatches = {name: (snapshot[name], projection[name]) for name in snapshot if snapshot[name] != projection[name]}
    assert not mismatches, f"{platform}: {len(mismatches)} command(s) diverge from snapshot: {sorted(mismatches)}"


def test_snapshot_set_matches_gate_platforms():
    """Every gate platform has a snapshot and vice versa (no silent oracle gap)."""
    snapshots = sorted(f[: -len(".json")] for f in os.listdir(SNAPSHOT_DIR) if f.endswith(".json"))
    assert snapshots == sorted(MERGED_ORACLE_PLATFORMS), (
        "merged oracle snapshots and MERGED_ORACLE_PLATFORMS are out of sync — "
        "run `python regen_merged_oracle_snapshots.py` / update the platform tuple"
    )
