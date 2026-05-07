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
NTC_LOCAL_DIR = "/tmp/ntc-templates"
SIMNOS_YAML_DIR = "simnos/plugins/nos/platforms_yaml"
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


def escape_format_braces(text: str) -> str:
    """Double every ``{`` / ``}`` so the text survives ``str.format()`` unchanged.

    NTC fixtures may contain literal ``{xxx}`` patterns (e.g. Juniper's
    ``{master}`` routing-engine indicator, ``{rpd}`` / ``{junos-bgpshard*}``
    process-thread names). simnos's runtime calls
    ``output.format(base_prompt=...)`` on every command output, which would
    otherwise interpret these as named placeholders and raise ``KeyError``.
    Doubling the braces makes them literal under ``str.format()``.

    NTC fixtures never contain simnos-specific placeholders like
    ``{base_prompt}``, so a blanket replace is safe — anything that comes
    from NTC is content meant to be displayed verbatim.
    """
    return text.replace("{", "{{").replace("}", "}}")


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
            output = escape_format_braces(f.read())

        variant_outputs: list[str] = []
        variant_paths: list[str] = []
        for variant in raw_files:
            if variant == primary:
                continue
            variant_path = os.path.join(folder_path, variant)
            with open(variant_path, encoding="utf-8") as f:
                variant_outputs.append(escape_format_braces(f.read()))
            variant_paths.append(variant_path)

        command_name = folder.replace("_", " ")
        commands[command_name] = {
            "output": output,
            "output_variants": variant_outputs,
            "raw_path": primary_path,
            "raw_path_variants": variant_paths,
        }

    return commands


def get_simnos_yaml_data(platform: str) -> dict | None:
    """Load and return the full YAML data for a simnos platform."""
    yaml_path = os.path.join(SIMNOS_YAML_DIR, f"{platform}.yaml")
    if not os.path.isfile(yaml_path):
        return None

    yaml = YAML()
    with open(yaml_path, encoding="utf-8") as f:
        data = yaml.load(f)

    if not data or "commands" not in data:
        return None

    return data


def get_simnos_commands(platform_data: dict | None) -> set[str]:
    """Get command names from simnos YAML data."""
    if platform_data is None:
        return set()
    return set(platform_data["commands"].keys())


def get_platform_prompts(platform_data: dict | None) -> list[str]:
    """Get prompt patterns from simnos YAML data.

    Returns a list of prompt strings suitable for the 'prompt' field
    in diff YAML output, derived from the platform's initial_prompt
    and enable_prompt.
    """
    if platform_data is None:
        return ["{base_prompt}>", "{base_prompt}#"]

    initial = platform_data.get("initial_prompt", "{base_prompt}>")
    enable = platform_data.get("enable_prompt")

    if enable and enable != initial:
        return [initial, enable]
    return [initial]


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
    prompts: list[str],
) -> str:
    """Write diff YAML file and return the file path."""
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{platform}.yaml")

    yaml = YAML()
    yaml.default_flow_style = False

    # Build commands dict for YAML output
    prompt_value = prompts[0] if len(prompts) == 1 else prompts
    commands_data = {}
    has_any_variants = False
    for cmd_name, cmd_data in new_commands.items():
        entry: dict = {
            "output": cmd_data["output"],
            "help": f'execute the command "{cmd_name}"',
            "prompt": prompt_value,
        }
        if cmd_data.get("output_variants"):
            entry["output_variants"] = cmd_data["output_variants"]
            has_any_variants = True
        commands_data[cmd_name] = entry

    now = datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M:%S UTC")

    # Write as YAML with header comments
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"# NTC Templates diff for {platform}\n")
        f.write(f"# Generated: {now}\n")
        f.write(f"# NTC commit: {ntc_commit}\n")
        if is_new_platform:
            f.write("# NOTE: New platform — not yet in simnos\n")
        f.write(f"# New commands: {len(new_commands)}\n")
        if has_any_variants:
            f.write("#\n")
            f.write("# NOTE: `output_variants` lists alternate fixtures from NTC and is\n")
            f.write("# currently ignored by the simnos runtime (no schema support yet).\n")
            f.write("# It is preserved for future scenario / random response features.\n")
        f.write("#\n")
        f.write("# Source .raw files (primary marked with *):\n")
        for cmd_name, cmd_data in new_commands.items():
            f.write(f"#   {cmd_name}:\n")
            f.write(f"#     * {cmd_data['raw_path']}\n")
            for variant_path in cmd_data.get("raw_path_variants", []):
                f.write(f"#       {variant_path}\n")
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

    # Guard against accidental cleanup of simnos platform YAML
    if os.path.realpath(args.output) == os.path.realpath(SIMNOS_YAML_DIR):
        print(f"Error: --output must not point to simnos YAML directory ({SIMNOS_YAML_DIR})")
        sys.exit(1)

    # Clean stale diff YAML files from previous runs
    if os.path.isdir(args.output):
        for f in os.listdir(args.output):
            if f.endswith(".yaml"):
                os.remove(os.path.join(args.output, f))

    # Step 3: Process each platform
    total_new = 0
    platforms_with_diff = 0
    new_platforms = []

    for platform in sorted(platforms_to_process):
        ntc_commands = get_ntc_commands(NTC_LOCAL_DIR, platform)
        if not ntc_commands:
            continue

        is_new_platform = platform not in simnos_platforms
        platform_data = get_simnos_yaml_data(platform) if not is_new_platform else None
        simnos_cmds = get_simnos_commands(platform_data)
        prompts = get_platform_prompts(platform_data)

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
            prompts,
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
