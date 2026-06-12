"""
Diff-based NTC Templates sync tool for simnos.

Compares simnos A3 platforms (``platforms/<name>/``) against NTC Templates
test data and outputs only NEW commands (commands in NTC but not in simnos)
as **A3 take-in candidate files** — one ``commands/<stem>.yaml`` + adjacent
``<stem>.txt`` per command, with ``type: ntc`` and a ``source`` block — so a
maintainer can review and drop them straight into the platform dir (#264 / D9).
simnos's own data is never modified.

Output is verbatim: the A3 form stores raw NTC capture text (no ``str.format``
brace escaping — the runtime renders literal output unchanged, #264 / D6, D8).

Usage:
    python sync_ntc_commands.py                          # all platforms
    python sync_ntc_commands.py --platform cisco_ios     # specific platform
    python sync_ntc_commands.py --output /tmp/ntc-diff   # custom output dir
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys

import yaml

from a3_paths import list_a3_platform_names, unique_command_stem
from simnos.core.platform_loader import load_platform_dir

NTC_REPO_URL = "https://github.com/networktocode/ntc-templates"
NTC_LOCAL_DIR = "/tmp/ntc-templates"
SIMNOS_A3_DIR = "simnos/plugins/nos/platforms"
DEFAULT_OUTPUT_DIR = "/tmp/ntc-diff"


def clone_or_update_ntc(target_dir: str) -> None:
    """Clone or pull the NTC Templates repository.

    If a local clone exists but pull fails (e.g. offline), the existing
    clone is used as-is with a warning.
    """
    if os.path.exists(os.path.join(target_dir, ".git")):
        try:
            subprocess.check_call(
                ["git", "-C", target_dir, "pull", "--quiet"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            print(f"NTC Templates updated: {target_dir}")
        except subprocess.CalledProcessError:
            print(f"WARNING: git pull failed, using existing clone: {target_dir}")
    else:
        subprocess.check_call(
            ["git", "clone", "--quiet", NTC_REPO_URL, target_dir],
            stdout=subprocess.DEVNULL,
        )
        print(f"NTC Templates cloned: {target_dir}")


def get_ntc_commit_sha(target_dir: str) -> str:
    """Get the current commit SHA of the NTC Templates repo."""
    result = subprocess.run(
        ["git", "-C", target_dir, "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def get_ntc_platforms(target_dir: str) -> list[str]:
    """Get all platform names from NTC Templates tests directory."""
    tests_dir = os.path.join(target_dir, "tests")
    if not os.path.isdir(tests_dir):
        return []
    return sorted(name for name in os.listdir(tests_dir) if os.path.isdir(os.path.join(tests_dir, name)))


def select_primary_raw(platform: str, folder: str, raw_files: list[str]) -> str:
    """Pick the primary ``.raw`` file for a NTC command folder.

    NTC's fixture naming is inconsistent: some folders have a clean
    ``<platform>_<folder>.raw``, others use the folder name directly
    (``ping.raw``), and some swap separators (folder
    ``...advertised-routes`` vs file ``...advertised_routes.raw``). A
    naive alphabetical pick can also land on a fixture that belongs to a
    sibling command (e.g. ``alcatel_aos_show_interfaces_R8.raw`` sitting
    inside ``show_interfaces_ethernet/``).

    Selection order:

    1. ``<platform>_<folder>.raw`` (canonical exact)
    2. ``<platform>_<folder normalized>.raw`` (``-`` → ``_``)
    3. ``<folder>.raw`` (no platform prefix)
    4. ``<folder normalized>.raw``
    5. The alphabetical-first raw whose stem contains the (normalized)
       folder name — filters out unrelated siblings.
    6. The alphabetical-first raw (last resort).

    ``raw_files`` must be alphabetically sorted; the function does not
    re-sort.
    """
    folder_normalized = folder.replace("-", "_")
    candidates = [
        f"{platform}_{folder}.raw",
        f"{platform}_{folder_normalized}.raw",
        f"{folder}.raw",
        f"{folder_normalized}.raw",
    ]
    for candidate in candidates:
        if candidate in raw_files:
            return candidate

    matching = [f for f in raw_files if folder_normalized in f.replace("-", "_").removesuffix(".raw")]
    if matching:
        return matching[0]

    return raw_files[0]


def get_ntc_commands(target_dir: str, platform: str) -> dict[str, dict]:
    """Extract commands and outputs from NTC Templates test data.

    Each command folder may contain multiple ``.raw`` fixtures
    representing different device states. We collect them all: a
    primary fixture is picked via :func:`select_primary_raw` and stored
    as ``output``; the rest are stored as ``output_variants``.

    Returns a dict of {command_name: {
        "output": str,
        "output_variants": list[str],
        "raw_path": str,
        "raw_path_variants": list[str],
    }}.
    """
    tests_dir = os.path.join(target_dir, "tests", platform)
    if not os.path.isdir(tests_dir):
        return {}

    commands: dict[str, dict] = {}
    for folder in sorted(os.listdir(tests_dir)):
        folder_path = os.path.join(tests_dir, folder)
        if not os.path.isdir(folder_path):
            continue

        raw_files = sorted(f for f in os.listdir(folder_path) if f.endswith(".raw"))
        if not raw_files:
            continue

        primary = select_primary_raw(platform, folder, raw_files)
        primary_path = os.path.join(folder_path, primary)
        with open(primary_path, encoding="utf-8") as f:
            # Verbatim: the A3 form stores raw NTC text (no brace escaping).
            output = f.read()

        variant_outputs: list[str] = []
        variant_paths: list[str] = []
        for variant in raw_files:
            if variant == primary:
                continue
            variant_path = os.path.join(folder_path, variant)
            with open(variant_path, encoding="utf-8") as f:
                variant_outputs.append(f.read())
            variant_paths.append(variant_path)

        command_name = folder.replace("_", " ")
        commands[command_name] = {
            "output": output,
            "output_variants": variant_outputs,
            "raw_path": primary_path,
            "raw_path_variants": variant_paths,
        }

    return commands


def get_simnos_commands(platform: str) -> set[str]:
    """Return the command names a simnos A3 platform already defines.

    Loads ``platforms/<platform>/`` through the runtime loader, so the keys are
    the resolved ``command`` fields (the SSoT) — the same names NTC folders map
    to. An unmigrated / absent platform yields an empty set (every NTC command
    is then "new").
    """
    a3_dir = os.path.join(SIMNOS_A3_DIR, platform)
    if not os.path.isfile(os.path.join(a3_dir, "platform.yaml")):
        return set()
    return set(load_platform_dir(a3_dir).commands.keys())


def get_platform_modes(platform: str) -> list[str]:
    """Return the canonical mode names of an A3 platform (for the diff `mode`).

    NTC commands are show/exec output, valid wherever the platform exposes a
    prompt; the candidate file lists the platform's modes so a reviewer can
    trim them. An absent platform falls back to the canonical user/enable pair.
    """
    a3_dir = os.path.join(SIMNOS_A3_DIR, platform)
    if not os.path.isfile(os.path.join(a3_dir, "platform.yaml")):
        return ["user", "enable"]
    return list(load_platform_dir(a3_dir).modes.keys())


def get_simnos_platforms() -> set[str]:
    """Get all platform names from the simnos A3 directory."""
    return set(list_a3_platform_names(SIMNOS_A3_DIR))


def compute_diff(
    ntc_commands: dict[str, dict],
    simnos_commands: set[str],
) -> dict[str, dict]:
    """Return commands that exist in NTC but not in simnos."""
    return {
        cmd_name: cmd_data for cmd_name, cmd_data in sorted(ntc_commands.items()) if cmd_name not in simnos_commands
    }


def _ensure_trailing_newline(text: str) -> str:
    """LF + a single trailing newline; empty stays a 0-byte file (D7/D8).

    Mirrors ``migrate_platform_yaml._ensure_trailing_newline`` so re-synced
    output is byte-identical to a migrated literal.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if text and not text.endswith("\n"):
        text += "\n"
    return text


def _ntc_source(raw_path: str, ntc_commit: str) -> dict:
    """The A3 ``source`` block for an NTC-derived command (provenance)."""
    rel = raw_path
    marker = f"{os.sep}tests{os.sep}"
    if marker in raw_path:
        rel = "tests/" + raw_path.split(marker, 1)[1].replace(os.sep, "/")
    return {"ntc_template": rel, "ntc_commit": ntc_commit}


def write_diff_files(
    output_dir: str,
    platform: str,
    new_commands: dict[str, dict],
    ntc_commit: str,
    modes: list[str],
) -> str:
    """Write A3 take-in candidate files for a platform; return its commands dir.

    Per command: ``commands/<stem>.yaml`` (``command`` / ``type: ntc`` /
    ``source`` / ``help`` / ``mode`` / ``output`` or ``variants``) + adjacent
    ``<stem>.txt`` capture file(s). The layout mirrors a real A3 platform dir so
    the files can be reviewed and copied straight under
    ``simnos/plugins/nos/platforms/<platform>/`` (#264 / D9).

    Note: ``platform.yaml`` is NOT generated — for an existing platform it lives
    in the real tree; for a brand-new platform the maintainer authors it by hand
    (the modes/auth are not derivable from NTC fixtures). ``main`` prints this
    for ``[NEW PLATFORM]`` rows (1st round codex #3).

    The platform's commands dir is cleared first so a re-run after an NTC update
    leaves no stale candidate from a command that NTC dropped / renamed
    (1st round claude #6a).
    """
    commands_dir = os.path.join(output_dir, platform, "commands")
    if os.path.isdir(commands_dir):
        shutil.rmtree(commands_dir)
    os.makedirs(commands_dir, exist_ok=True)

    used_stems: set[str] = set()
    for cmd_name, cmd_data in new_commands.items():
        stem = unique_command_stem(cmd_name, used_stems)
        mapping: dict = {
            "command": cmd_name,
            "type": "ntc",
            "source": _ntc_source(cmd_data["raw_path"], ntc_commit),
            "help": f'execute the command "{cmd_name}"',
        }
        if modes:
            mapping["mode"] = modes
        variants = cmd_data.get("output_variants") or []
        if variants:
            variant_entries = [{"name": "variant_1", "output": f"{stem}__variant_1.txt"}]
            _write(os.path.join(commands_dir, f"{stem}__variant_1.txt"), _ensure_trailing_newline(cmd_data["output"]))
            for i, variant_output in enumerate(variants):
                vstem = f"{stem}__variant_{i + 2}"
                _write(os.path.join(commands_dir, f"{vstem}.txt"), _ensure_trailing_newline(variant_output))
                variant_entries.append({"name": f"variant_{i + 2}", "output": f"{vstem}.txt"})
            mapping["variants"] = variant_entries
        else:
            mapping["output"] = f"{stem}.txt"
            _write(os.path.join(commands_dir, f"{stem}.txt"), _ensure_trailing_newline(cmd_data["output"]))
        _write(
            os.path.join(commands_dir, f"{stem}.yaml"),
            yaml.safe_dump(mapping, sort_keys=False, allow_unicode=True, default_flow_style=False),
        )

    return commands_dir


def _write(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare simnos A3 platforms against NTC Templates and output new commands as A3 candidate files.",
    )
    parser.add_argument(
        "--platform",
        help="Process only this platform (e.g. cisco_ios)",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory for diff files (default: {DEFAULT_OUTPUT_DIR})",
    )
    args = parser.parse_args()

    # Step 1: Clone/pull NTC Templates
    print("Syncing NTC Templates...")
    clone_or_update_ntc(NTC_LOCAL_DIR)
    ntc_commit = get_ntc_commit_sha(NTC_LOCAL_DIR)
    print(f"NTC commit: {ntc_commit[:12]}")

    # Step 2: Determine platforms to process
    ntc_platforms = set(get_ntc_platforms(NTC_LOCAL_DIR))
    simnos_platforms = get_simnos_platforms()

    if args.platform:
        if args.platform not in ntc_platforms:
            print(f"Error: platform '{args.platform}' not found in NTC Templates")
            sys.exit(1)
        platforms_to_process = {args.platform}
    else:
        platforms_to_process = ntc_platforms

    # Guard against accidental writes into the real simnos platform tree
    if os.path.realpath(args.output) == os.path.realpath(SIMNOS_A3_DIR):
        print(f"Error: --output must not point to the simnos platform directory ({SIMNOS_A3_DIR})")
        sys.exit(1)

    # Step 3: Process each platform
    total_new = 0
    platforms_with_diff = 0
    new_platforms = []

    for platform in sorted(platforms_to_process):
        ntc_commands = get_ntc_commands(NTC_LOCAL_DIR, platform)
        if not ntc_commands:
            continue

        is_new_platform = platform not in simnos_platforms
        simnos_cmds = get_simnos_commands(platform)
        modes = get_platform_modes(platform)

        new_commands = compute_diff(ntc_commands, simnos_cmds)

        if not new_commands:
            continue

        if is_new_platform:
            new_platforms.append(platform)

        output_path = write_diff_files(
            args.output,
            platform,
            new_commands,
            ntc_commit,
            modes,
        )

        marker = " [NEW PLATFORM — author platform.yaml by hand]" if is_new_platform else ""
        print(f"  {platform}: {len(new_commands)} new commands → {output_path}{marker}")
        total_new += len(new_commands)
        platforms_with_diff += 1

    # Step 4: Summary
    print()
    print("=" * 50)
    print(f"Platforms processed: {len(platforms_to_process)}")
    print(f"Platforms with new commands: {platforms_with_diff}")
    print(f"Total new commands: {total_new}")
    if new_platforms:
        print(f"New platforms (not in simnos): {', '.join(sorted(new_platforms))}")
    print(f"Diff files written to: {args.output}")


if __name__ == "__main__":
    main()
