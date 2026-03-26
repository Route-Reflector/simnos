"""
Diff-based NTC Templates sync tool for simnos.

Compares simnos platform YAML files against NTC Templates test data
and outputs only NEW commands (commands in NTC but not in simnos) to
separate diff files. simnos YAML files are never modified.

Usage:
    python sync_ntc_commands.py                          # all platforms
    python sync_ntc_commands.py --platform cisco_ios     # specific platform
    python sync_ntc_commands.py --output /tmp/ntc-diff   # custom output dir
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import os
import subprocess
import sys

from ruamel.yaml import YAML

NTC_REPO_URL = "https://github.com/networktocode/ntc-templates"
NTC_LOCAL_DIR = "/tmp/ntc-templates"  # noqa: S108
SIMNOS_YAML_DIR = "simnos/plugins/nos/platforms_yaml"
DEFAULT_OUTPUT_DIR = "/tmp/ntc-diff"  # noqa: S108


def clone_or_update_ntc(target_dir: str) -> None:
    """Clone or pull the NTC Templates repository."""
    if os.path.exists(os.path.join(target_dir, ".git")):
        subprocess.check_call(  # noqa: S603
            ["git", "-C", target_dir, "pull", "--quiet"],  # noqa: S607
            stdout=subprocess.DEVNULL,
        )
        print(f"NTC Templates updated: {target_dir}")
    else:
        subprocess.check_call(  # noqa: S603
            ["git", "clone", "--quiet", NTC_REPO_URL, target_dir],  # noqa: S607
            stdout=subprocess.DEVNULL,
        )
        print(f"NTC Templates cloned: {target_dir}")


def get_ntc_commit_sha(target_dir: str) -> str:
    """Get the current commit SHA of the NTC Templates repo."""
    result = subprocess.run(  # noqa: S603
        ["git", "-C", target_dir, "rev-parse", "HEAD"],  # noqa: S607
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


def get_ntc_commands(target_dir: str, platform: str) -> dict[str, dict]:
    """Extract commands and outputs from NTC Templates test data.

    Returns a dict of {command_name: {"output": str, "raw_path": str}}.
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

        # Use first .raw file (sorted for reproducibility)
        raw_path = os.path.join(folder_path, raw_files[0])
        with open(raw_path, encoding="utf-8") as f:
            output = f.read()

        command_name = folder.replace("_", " ")
        commands[command_name] = {
            "output": output,
            "raw_path": raw_path,
        }

    return commands


def get_simnos_commands(platform: str) -> set[str]:
    """Get command names from simnos YAML file."""
    yaml_path = os.path.join(SIMNOS_YAML_DIR, f"{platform}.yaml")
    if not os.path.isfile(yaml_path):
        return set()

    yaml = YAML()
    with open(yaml_path, encoding="utf-8") as f:
        data = yaml.load(f)

    if not data or "commands" not in data:
        return set()

    return set(data["commands"].keys())


def get_simnos_platforms() -> set[str]:
    """Get all platform names from simnos YAML directory."""
    if not os.path.isdir(SIMNOS_YAML_DIR):
        return set()
    return {f.replace(".yaml", "") for f in os.listdir(SIMNOS_YAML_DIR) if f.endswith(".yaml")}


def compute_diff(
    ntc_commands: dict[str, dict],
    simnos_commands: set[str],
) -> dict[str, dict]:
    """Return commands that exist in NTC but not in simnos."""
    return {
        cmd_name: cmd_data for cmd_name, cmd_data in sorted(ntc_commands.items()) if cmd_name not in simnos_commands
    }


def write_diff_file(
    output_dir: str,
    platform: str,
    new_commands: dict[str, dict],
    ntc_commit: str,
    is_new_platform: bool,
) -> str:
    """Write diff YAML file and return the file path."""
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{platform}.yaml")

    yaml = YAML()
    yaml.default_flow_style = False

    # Build commands dict for YAML output
    commands_data = {}
    raw_paths = []
    for cmd_name, cmd_data in new_commands.items():
        commands_data[cmd_name] = {
            "output": cmd_data["output"],
            "help": f'execute the command "{cmd_name}"',
            "prompt": ["{base_prompt}>", "{base_prompt}#"],
        }
        raw_paths.append(cmd_data["raw_path"])

    now = datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M:%S UTC")

    # Write as YAML with header comments
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"# NTC Templates diff for {platform}\n")
        f.write(f"# Generated: {now}\n")
        f.write(f"# NTC commit: {ntc_commit}\n")
        if is_new_platform:
            f.write("# NOTE: New platform — not yet in simnos\n")
        f.write(f"# New commands: {len(new_commands)}\n")
        f.write("#\n")
        f.write("# Source .raw files:\n")
        for path in raw_paths:
            f.write(f"#   {path}\n")
        f.write("\n")
        yaml.dump({"commands": commands_data}, f)

    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare simnos YAML platforms against NTC Templates and output new commands.",
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

    # Step 3: Process each platform
    total_new = 0
    platforms_with_diff = 0
    new_platforms = []

    for platform in sorted(platforms_to_process):
        ntc_commands = get_ntc_commands(NTC_LOCAL_DIR, platform)
        if not ntc_commands:
            continue

        is_new_platform = platform not in simnos_platforms
        simnos_cmds = get_simnos_commands(platform) if not is_new_platform else set()

        new_commands = compute_diff(ntc_commands, simnos_cmds)

        if not new_commands:
            continue

        if is_new_platform:
            new_platforms.append(platform)

        output_path = write_diff_file(
            args.output,
            platform,
            new_commands,
            ntc_commit,
            is_new_platform,
        )

        marker = " [NEW PLATFORM]" if is_new_platform else ""
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
