"""Shared A3 platform-data path + filename helpers (#264 / D1).

A repo-root module (stdlib only — ``os`` / ``re``) so the invoke tasks
(``tasks.py``) and the dev scripts (``migrate_platform_yaml.py`` /
``sync_ntc_commands.py`` / ``regen_oracle_snapshots.py``) share one definition
without any of them paying the cost of importing the ``simnos`` package. The
``command`` field inside each command yaml is the SSoT; filenames are
non-semantic, so the stem helpers drive conventions (lint warning / generated
filenames), not load behavior.
"""

import os
import re

# Root holding the A3 platform dirs (each is one platform with a platform.yaml).
PLATFORMS_DIR = "simnos/plugins/nos/platforms"

# Where the migration-oracle (b) snapshots live (frozen by migrate, re-baselined
# by regen, compared by the committed oracle test).
SNAPSHOT_DIR = "tests/assets/oracle"


def list_a3_platform_names(root: str = PLATFORMS_DIR) -> list[str]:
    """Names of A3 platforms (dirs holding a ``platform.yaml``), sorted."""
    if not os.path.isdir(root):
        return []
    return sorted(entry for entry in os.listdir(root) if os.path.isfile(os.path.join(root, entry, "platform.yaml")))


def sanitize_command_stem(command: str) -> str:
    """Map a command name to a lint-clean A3 file stem (``[a-z0-9_.-]`` only).

    Spaces and other characters collapse to ``_``; leading/trailing ``_`` are
    stripped. The result is non-semantic — a collision just needs a suffix
    (see :func:`unique_command_stem`).
    """
    stem = re.sub(r"[^a-z0-9_.-]", "_", command.lower())
    return re.sub(r"_+", "_", stem).strip("_") or "cmd"


def unique_command_stem(command: str, used: set[str]) -> str:
    """Sanitized stem with a deterministic ``__<n>`` collision suffix.

    Records the chosen stem in ``used`` so repeated calls within one platform
    never collide. The suffix shape is what the filename-convention lint accepts.
    """
    base = sanitize_command_stem(command)
    candidate = base
    counter = 2
    while candidate in used:
        candidate = f"{base}__{counter}"
        counter += 1
    used.add(candidate)
    return candidate


def write_text_file(path: str, content: str) -> None:
    """Write UTF-8 ``content`` to ``path``, creating parent dirs as needed.

    The one file-write primitive the dev scripts (migrate / sync / regen) share,
    so an A3 output / candidate / snapshot file is written the same way
    everywhere (parents created, UTF-8, no implicit newline — callers pass
    :func:`ensure_trailing_newline` output when the trailing-newline convention
    applies).
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


def ensure_trailing_newline(text: str) -> str:
    """LF + a single trailing newline for an A3 output file (D7 / D8).

    Wire-equivalent under ``splitlines()``. Empty output (legacy ``output: ''`` /
    an empty ``output_variant``) stays a 0-byte file: a forced ``\\n`` would
    round-trip to ``['']`` under splitlines where the empty literal projects to
    ``[]`` — a phantom blank line the variant-body oracle catches (fortinet /
    oneaccess_oneos). The encoding lint's trailing-newline rule already exempts
    empty files (``raw and ...``). Shared by the migrate converter and the NTC
    sync tool so a re-synced literal is byte-identical to a migrated one.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if text and not text.endswith("\n"):
        text += "\n"
    return text
