"""Migration oracle (b): A3 loader projection == frozen adapter snapshot (#264 / Decision 3 (b)).

For each migrated platform, the conversion script froze the *legacy adapter*
projection of the old yaml into ``tests/assets/oracle/<platform>.json`` while the
legacy data still existed. This test loads the A3 platform dir through the new
loader, projects it the same way (``oracle_projection.project_resolved``), and
asserts it equals the frozen snapshot — so the migrated data + loader reproduce
the v2-equivalent behavior even after the legacy yaml is deleted (the "input not
in the gate's final tree" problem, 2nd round claude #3, solved by snapshotting).

Frozen-input nuance (1st round claude #4): the snapshot was frozen from the
*raw* legacy yaml ``commands`` dict, while the deleted b' gate validated
``adapter == v2`` over the BASIC-merged + Nos-normalized dict. The difference is
harmless on shipped data — the adapter reads prompt/output strings directly and
the only BASIC-merge-sensitive construct (an alias shadowing a BASIC command)
does not survive conversion (the migrate smoke loud-fails on a projection
divergence), so no such alias exists in the frozen platforms.

Snapshot lifecycle after migration (1st round claude #2 / codex — keep, don't
delete): this gate keeps earning its keep — variant-body freezing caught a real
empty-output bug during PR-3. The full-set equality means an *intentional* A3
edit fails it; re-baseline the affected platform with
``python regen_oracle_snapshots.py <platform>`` and review the snapshot diff as a
golden file. Regen projects the A3 loader (not the deleted legacy adapter), which
is correct for an ongoing edit baseline (a human reviews the diff) but no longer
proves v2-equivalence — that proof is sealed in this PR's green CI.
"""

import glob
import json
import os

import pytest

from a3_paths import PLATFORMS_DIR as A3_ROOT
from a3_paths import SNAPSHOT_DIR, list_a3_platform_names
from simnos.core.platform_loader import load_platform_dir
from tests.core.oracle_projection import project_resolved

_snapshots = sorted(os.path.basename(p)[: -len(".json")] for p in glob.glob(os.path.join(SNAPSHOT_DIR, "*.json")))


@pytest.mark.parametrize("platform", _snapshots)
def test_a3_loader_matches_frozen_snapshot(platform):
    """The A3 loader projection equals the frozen legacy-adapter snapshot."""
    with open(os.path.join(SNAPSHOT_DIR, f"{platform}.json"), encoding="utf-8") as fh:
        snapshot = json.load(fh)
    resolved = load_platform_dir(os.path.join(A3_ROOT, platform))
    # JSON round-trips tuples to lists; the projection uses lists already, so a
    # direct compare is apples-to-apples.
    projection = json.loads(json.dumps(project_resolved(resolved.commands)))

    assert set(projection) == set(snapshot), f"{platform}: command set differs from snapshot"
    mismatches = {name: (snapshot[name], projection[name]) for name in snapshot if snapshot[name] != projection[name]}
    assert not mismatches, f"{platform}: {len(mismatches)} command(s) diverge from snapshot: {sorted(mismatches)}"


def test_snapshot_set_matches_a3_platforms():
    """Every A3 platform has a snapshot and vice versa (no silent oracle gap).

    The parametrize above is snapshot-glob driven, so a *new* A3 platform whose
    snapshot was forgotten would silently run with no regression baseline. Pin
    the two sets equal — regenerate a missing one with
    ``python regen_oracle_snapshots.py <platform>`` (2nd round claude #2).
    """
    assert _snapshots, "no oracle snapshots found — did the conversion run?"
    assert set(_snapshots) == set(list_a3_platform_names(A3_ROOT)), (
        "oracle snapshots and A3 platforms are out of sync — "
        "run `python regen_oracle_snapshots.py` to add the missing snapshot(s)"
    )
