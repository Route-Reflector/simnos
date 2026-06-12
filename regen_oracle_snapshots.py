#!/usr/bin/env python3
"""Re-baseline A3 migration-oracle snapshots from the A3 loader (#264 / Decision 3 (b)).

The committed oracle (b) gate (``tests/core/test_migration_oracle_a3.py``)
compares the A3 loader projection of each platform against a frozen
``tests/assets/oracle/<platform>.json``. The original snapshots were frozen by
``migrate_platform_yaml.py`` from the *legacy adapter* and proved the migration
was v2-equivalent (sealed in PR-3's green CI).

After migration the regen path is from the A3 loader itself: an **intentional**
edit to an A3 platform's commands changes the projection and fails the gate, so
this script rewrites the affected snapshot to the new projection. This is a
golden-file update — the snapshot diff MUST be reviewed in the PR. It no longer
proves v2-equivalence (it reads the same loader the test reads); it just records
"this is the new intended projection" for regression-detection going forward.

Run from the repo root:
    python regen_oracle_snapshots.py cisco_ios        # one platform
    python regen_oracle_snapshots.py                  # every A3 platform
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from a3_paths import list_a3_platform_names
from simnos.core.platform_loader import load_platform_dir
from tests.core.oracle_projection import project_resolved

A3_ROOT = "simnos/plugins/nos/platforms"
SNAPSHOT_DIR = "tests/assets/oracle"


def regen(platform: str) -> None:
    platform_dir = os.path.join(A3_ROOT, platform)
    if not os.path.isfile(os.path.join(platform_dir, "platform.yaml")):
        raise SystemExit(f"{platform}: not an A3 platform dir ({platform_dir})")
    projection = project_resolved(load_platform_dir(platform_dir).commands)
    snapshot_path = os.path.join(SNAPSHOT_DIR, f"{platform}.json")
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)
    with open(snapshot_path, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(projection, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    print(f"re-baselined {platform}: {len(projection)} commands -> {snapshot_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Re-baseline A3 migration-oracle snapshots from the A3 loader (#264).")
    parser.add_argument("platform", nargs="?", help="platform name (default: all A3 platforms)")
    args = parser.parse_args()
    platforms = [args.platform] if args.platform else list_a3_platform_names(A3_ROOT)
    for platform in platforms:
        regen(platform)


if __name__ == "__main__":
    sys.exit(main())
