#!/usr/bin/env python3
"""Re-baseline the merged-view oracle snapshots (#317 P-2, lives until P-4).

The committed gate (``tests/core/test_merged_oracle.py``) compares the *merged
runtime view* — ``build_resolved_platform`` over the platform's full registry
inflow (A3 dir + py handler module), exactly what ``Host.start`` serves — of
each formerly-py-authored platform against a frozen
``tests/assets/oracle_merged/<platform>.json``.

The original snapshots were frozen at the P-2 migration and byte-verified
against the pre-migration merged view (py dict inflow still present): every
projection axis except the expected handler->static conversions was equal, and
the converted outputs were byte-compared against pre-migration renders frozen
under ``tests/assets/p2_migration_wire/`` (see the #317 P-2 PR). Until the
legacy adapter and py inflow are removed (P-4), this gate is the last line
of defense that P-3's merge rework does not drift the served view — the byte
goldens only cover cisco_ios scenarios.

Re-running this script is a golden-file update: the snapshot diff MUST be
reviewed in the PR.

Run from the repo root:
    python regen_merged_oracle_snapshots.py arista_eos    # one platform
    python regen_merged_oracle_snapshots.py               # every snapshot platform
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from a3_paths import write_text_file
from simnos.core.nos import Nos
from simnos.plugins.nos import nos_plugins
from simnos.plugins.shell.cmd_shell import build_resolved_platform
from tests.core.oracle_projection import project_resolved

SNAPSHOT_DIR = os.path.join("tests", "assets", "oracle_merged")

# The platforms under the merged-view gate: the three whose py `commands` dict
# P-2 migrated to A3. Other platforms have no py inflow, so their merged view
# is BASIC + the A3 loader view already pinned by the per-platform A3 oracle.
# TODO(#317 P-4): remove this gate (script + test_merged_oracle.py + snapshots)
# once the legacy adapter / py inflow are gone and the comparison target no
# longer exists — grep marker so the removal PR cannot miss it.
MERGED_ORACLE_PLATFORMS = ("arista_eos", "cisco_ios", "huawei_smartax")


def project_merged_platform(platform: str) -> dict[str, dict]:
    """Project the platform's merged runtime view (the Host.start wiring)."""
    nos = Nos(filename=nos_plugins[platform])
    merged = build_resolved_platform(nos, {})
    return project_resolved(merged.commands)


def regen(platform: str) -> None:
    if platform not in MERGED_ORACLE_PLATFORMS:
        raise SystemExit(f"{platform}: not a merged-oracle platform ({', '.join(MERGED_ORACLE_PLATFORMS)})")
    projection = project_merged_platform(platform)
    snapshot_path = os.path.join(SNAPSHOT_DIR, f"{platform}.json")
    write_text_file(snapshot_path, json.dumps(projection, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    print(f"re-baselined {platform}: {len(projection)} commands -> {snapshot_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Re-baseline merged-view oracle snapshots (#317 P-2).")
    parser.add_argument("platform", nargs="?", help="platform name (default: all merged-oracle platforms)")
    args = parser.parse_args()
    for platform in [args.platform] if args.platform else MERGED_ORACLE_PLATFORMS:
        regen(platform)


if __name__ == "__main__":
    sys.exit(main())
