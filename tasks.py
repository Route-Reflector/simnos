"""Invoke tasks for simnos.

Provides lint / static-analysis wrappers (`ruff`, `yamllint`, `bandit`),
local docs serving (`docs`), platform docs generation
(`gen_docs_platform_commands`), and a Netmiko login debug helper
(`netmiko_check`).
"""

from collections.abc import Iterable
import glob
import os
import re
import time

from invoke import Exit, task
import yaml


def run_cmd(context, exec_cmd):
    """Run an invoke task command locally with a pty."""
    print(f"Running command: {exec_cmd}")
    return context.run(exec_cmd, pty=True)


@task
def ruff(context):
    """Run ruff to check that Python files adherence to ruff standards."""
    run_cmd(context, "ruff check --diff")
    run_cmd(context, "ruff format --diff")


@task
def yamllint(context):
    """Run yamllint to check YAML files."""
    run_cmd(context, "yamllint .")


@task
def bandit(context):
    """Run bandit to validate basic static code security analysis."""
    run_cmd(context, "bandit -c pyproject.toml --recursive ./")


# --- A3 platform data lint (#264 / D8, D9) -----------------------------------

PLATFORMS_A3_DIR = "simnos/plugins/nos/platforms"


def _a3_platform_names(platforms_dir: str = PLATFORMS_A3_DIR) -> list[str]:
    """Names of A3 platforms (dirs holding a ``platform.yaml``), sorted."""
    if not os.path.isdir(platforms_dir):
        return []
    return sorted(
        entry
        for entry in os.listdir(platforms_dir)
        if os.path.isfile(os.path.join(platforms_dir, entry, "platform.yaml"))
    )


def check_platform_data(platforms_dir: str = PLATFORMS_A3_DIR) -> list[str]:
    """Lint the A3 platform data directories (#264 / D8, D9).

    Rules:
    1. encoding (D8): every output file (``.txt`` / ``.j2``) must decode as
       UTF-8, contain no CR (LF-only), and end with a trailing newline. Trailing
       whitespace is intentionally NOT checked (raw-capture fidelity).
    2. orphan: an output file referenced by no command yaml is flagged
       (1st round claude #6c).
    3. shared reference: an output file referenced by more than one command yaml
       is flagged — the 1-yaml:1-output principle (2nd round gemini #3).
    4. extension convention: a literal channel (``output`` / a variant's output)
       must reference ``.txt`` and ``output_template`` must reference ``.j2`` —
       the loader reads by field, so a variant pointing at ``.j2`` would emit raw
       jinja verbatim (1st round claude #5). Enforced here, not in the loader.
    5. stray ``.yml``: a command file uses the ``.yml`` extension, which the
       loader's ``*.yaml`` glob silently ignores (1st round claude #8).

    Returns a list of human-readable violation strings (empty = clean). Filename
    convention + ``type: ntc`` source-presence checks are warning-tier and live
    in `check_platform_data_warnings` (printed by the task, never gating).
    """
    violations: list[str] = []
    if not os.path.isdir(platforms_dir):
        return violations
    for platform in sorted(os.listdir(platforms_dir)):
        commands_dir = os.path.join(platforms_dir, platform, "commands")
        if not os.path.isdir(commands_dir):
            continue
        violations.extend(
            f"{platform}/commands/{os.path.basename(stray)}: uses .yml; the loader only globs .yaml"
            for stray in sorted(glob.glob(os.path.join(commands_dir, "*.yml")))
        )
        referenced: dict[str, list[str]] = {}
        for command_yaml in sorted(glob.glob(os.path.join(commands_dir, "*.yaml"))):
            with open(command_yaml, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            for ref in _output_refs(data):
                referenced.setdefault(ref, []).append(os.path.basename(command_yaml))
            violations.extend(_check_ref_extensions(data, platform, os.path.basename(command_yaml)))

        output_files = {
            os.path.basename(p) for ext in ("*.txt", "*.j2") for p in glob.glob(os.path.join(commands_dir, ext))
        }
        for output_file in sorted(output_files):
            rel = f"{platform}/commands/{output_file}"
            violations.extend(_check_output_encoding(os.path.join(commands_dir, output_file), rel))
            if output_file not in referenced:
                violations.append(f"{rel}: orphan output file (referenced by no command yaml)")
        for ref, sources in sorted(referenced.items()):
            if len(sources) > 1:
                violations.append(
                    f"{platform}/commands/{ref}: referenced by {len(sources)} yamls {sources} (1 yaml : 1 output)"
                )
            if ref not in output_files:
                violations.append(f"{platform}/commands/{ref}: referenced by {sources} but the file is missing")
    return violations


def _command_stem(command: str) -> str:
    """The conventional A3 file stem for a command name (#264 / D1).

    Same ``[a-z0-9_.-]`` sanitization the migrate / NTC-sync tools use; the
    ``command`` field is the SSoT (filenames are non-semantic), so this drives a
    warning-tier convention check, not a gate.
    """
    stem = re.sub(r"[^a-z0-9_.-]", "_", command.lower())
    return re.sub(r"_+", "_", stem).strip("_") or "cmd"


def check_platform_data_warnings(platforms_dir: str = PLATFORMS_A3_DIR) -> list[str]:
    """Warning-tier A3 conventions (#264 / D9) — informational, never a gate.

    1. filename convention: a command yaml's stem should be the sanitized
       ``command`` name (optionally with a ``__<n>`` collision suffix). A
       mismatch is harmless (the loader keys on the ``command`` field) but hurts
       discoverability.
    2. ``type: ntc`` provenance: a command authored as ``type: ntc`` should
       carry a ``source`` block (``ntc_template`` / ``ntc_commit``) so the
       capture's origin is traceable; a missing one is flagged.

    Returns a list of human-readable warnings (empty = clean).
    """
    warnings: list[str] = []
    if not os.path.isdir(platforms_dir):
        return warnings
    for platform in sorted(os.listdir(platforms_dir)):
        commands_dir = os.path.join(platforms_dir, platform, "commands")
        if not os.path.isdir(commands_dir):
            continue
        for command_yaml in sorted(glob.glob(os.path.join(commands_dir, "*.yaml"))):
            stem = os.path.basename(command_yaml).removesuffix(".yaml")
            with open(command_yaml, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            command = data.get("command")
            if isinstance(command, str):
                base = _command_stem(command)
                if stem != base and not stem.startswith(f"{base}__"):
                    warnings.append(
                        f"{platform}/commands/{stem}.yaml: filename does not match command {command!r} "
                        f"(expected stem {base!r})"
                    )
            if data.get("type") == "ntc" and not data.get("source"):
                warnings.append(
                    f"{platform}/commands/{stem}.yaml: type: ntc but no `source` block (provenance missing)"
                )
    return warnings


def _variant_output_refs(command_data: dict) -> list[str]:
    """The output file each variant references (str-typed entries only)."""
    return [
        variant["output"]
        for variant in command_data.get("variants") or []
        if isinstance(variant, dict) and isinstance(variant.get("output"), str)
    ]


def _output_refs(command_data: dict) -> list[str]:
    """Every output file a command yaml references (output / output_template / variants)."""
    refs: list[str] = []
    for key in ("output", "output_template"):
        value = command_data.get(key)
        if isinstance(value, str):
            refs.append(value)
    refs.extend(_variant_output_refs(command_data))
    return refs


def _check_ref_extensions(command_data: dict, platform: str, yaml_name: str) -> list[str]:
    """Literal channels must use ``.txt``; ``output_template`` must use ``.j2`` (D8 convention)."""
    literal_refs = [command_data["output"]] if isinstance(command_data.get("output"), str) else []
    literal_refs += _variant_output_refs(command_data)
    violations = [
        f"{platform}/commands/{yaml_name}: literal output {ref!r} uses .j2 (literal channels are .txt)"
        for ref in literal_refs
        if ref.endswith(".j2")
    ]
    template_ref = command_data.get("output_template")
    if isinstance(template_ref, str) and not template_ref.endswith(".j2"):
        violations.append(f"{platform}/commands/{yaml_name}: output_template {template_ref!r} must use .j2")
    return violations


def _check_output_encoding(path: str, rel: str) -> list[str]:
    """UTF-8 / LF-only / trailing-newline checks for one output file (D8)."""
    violations: list[str] = []
    raw = open(path, "rb").read()  # noqa: SIM115 — short-lived, byte-level read
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as e:
        return [f"{rel}: not valid UTF-8 ({e})"]
    if "\r" in text:
        violations.append(f"{rel}: contains CR (output files must be LF-only)")
    if raw and not text.endswith("\n"):
        violations.append(f"{rel}: missing trailing newline")
    return violations


@task
def lint_platform_data(context):
    """Lint the A3 platform data directories (#264 / D8, D9).

    Gating: encoding (UTF-8 / LF / trailing newline), orphan output files,
    shared output references, extension convention, stray ``.yml`` (see
    `check_platform_data`). Warning-tier (printed, non-blocking): filename
    convention + ``type: ntc`` provenance (see `check_platform_data_warnings`).
    """
    warnings = check_platform_data_warnings()
    for warning in warnings:
        print(f"WARNING: {warning}")
    if warnings:
        print(f"({len(warnings)} warning(s) — informational, not blocking)")

    violations = check_platform_data()
    for violation in violations:
        print(violation)
    if violations:
        raise Exit(f"platform data lint failed with {len(violations)} violation(s)", code=1)
    print("platform data lint OK")


@task
def ty(context, exit_zero=False):
    """Run ty type-checker (blocking since Phase 2, see #218).

    Phase 2 brought production code to 0 diagnostics; Phase 3 (#251) then
    removed the tests/ and ssh_server_paramiko exclusions from pyproject.toml
    ``[tool.ty.src]``, so the whole tree is now scanned with 0 diagnostics.
    CI treats ty as blocking (exit_zero=False default + no continue-on-error),
    so new type errors anywhere (production or tests) break the build.

    Args:
        exit_zero: When True, pass ``--exit-zero`` so ty never exits
            non-zero. Default is False (blocking) for CI. Set True only
            for developer workflow chains where a transient typing error
            should not abort the rest of the invoke pipeline.
    """
    flag = "--exit-zero " if exit_zero else ""
    run_cmd(context, f"uv run ty check . {flag}".rstrip())


@task
def docs(context):
    """Build and serve docs locally for development."""
    run_cmd(context, "mkdocs serve --dev-addr 0.0.0.0:8001")


WARNING_MESSAGE = """
!!! warning
    This is automatically generated. In case of any issues,
    please refer to the source code or, even better,
    open an issue on the GitHub repository. Thanks! 🤗📖
"""


_PRESERVED_PLATFORM_DOCS: frozenset[str] = frozenset({"index.md", "index.ja.md"})

# Curated nav display names that the default derivation (title-casing each
# underscore-separated token) cannot produce. New platforms fall back to the
# default and can be added here when the vendor spelling differs (#239).
NAV_DISPLAY_NAME_OVERRIDES: dict[str, str] = {
    "alcatel_aos": "Alcatel AOS",
    "alcatel_sros": "Alcatel SROS",
    "arista_eos": "Arista EOS",
    "aruba_aoscx": "Aruba AOS-CX",
    "aruba_os": "Aruba OS",
    "avaya_ers": "Avaya ERS",
    "avaya_vsp": "Avaya VSP",
    "broadcom_icos": "Broadcom ICOS",
    "ciena_saos": "Ciena SAOS",
    "cisco_apic": "Cisco APIC",
    "cisco_asa": "Cisco ASA",
    "cisco_ftd": "Cisco FTD",
    "cisco_ios": "Cisco IOS",
    "cisco_nxos": "Cisco NXOS",
    "cisco_wlc_ssh": "Cisco WLC SSH",
    "cisco_xr": "Cisco XR",
    "dell_force10": "Dell Force 10",
    "dell_powerconnect": "Dell PowerConnect",
    "dlink_ds": "DLink DS",
    "ericsson_ipos": "Ericsson IPOS",
    "extreme_exos": "Extreme EXOS",
    "extreme_slxos": "Extreme SLX-OS",
    "hp_comware": "HP Comware",
    "hp_procurve": "HP Procurve",
    "huawei_smartax": "Huawei SmartAX",
    "huawei_vrp": "Huawei VRP",
    "ipinfusion_ocnos": "IP Infusion OcNOS",
    "juniper_junos": "Juniper JunOS",
    "juniper_screenos": "Juniper ScreenOS",
    "mikrotik_routeros": "Mikrotik RouterOS",
    "oneaccess_oneos": "OneAccess OneOS",
    "paloalto_panos": "PaloAlto PanOS",
    "ubiquiti_edgerouter": "Ubiquiti EdgeRouter",
    "ubiquiti_edgeswitch": "Ubiquiti EdgeSwitch",
    "vyatta_vyos": "Vyatta VyOS",
    "watchguard_firebox": "WatchGuard Firebox",
    "zte_zxros": "ZTE ZXROS",
    "zyxel_os": "Zyxel OS",
}


def platform_display_name(platform: str) -> str:
    """Return the nav display name for a platform slug."""
    return NAV_DISPLAY_NAME_OVERRIDES.get(platform, platform.replace("_", " ").title())


def rewrite_mkdocs_platforms_nav(platforms: Iterable[str], mkdocs_path: str = "mkdocs.yml") -> None:
    """Regenerate the Platforms nav section of mkdocs.yml from `platforms`.

    The caller passes the platform list the docs pages are generated from. For
    the legacy yaml platforms every nav entry has a backing page. A3-migrated
    platforms (#264) are also included to keep their existing page in the nav
    until docs generation moves to the ResolvedCommand path (PR-3); an
    "A3-born" platform with no pre-existing page would get a nav entry without a
    backing page until then — a known PR-3 follow-up (2nd round claude #5b).
    A yaml-less, A3-less py-only platform still gets no nav entry — the
    registry-truth pin (`test_available_platforms_match_mkdocs_nav`) failing is
    the designed loud signal to decide how to document such a platform.
    Closes the M-1 failure mode (#239): a new platform used to need a manual
    nav entry, and a forgotten one silently produced a docs page unreachable
    from the site nav. The section is replaced as a text block (instead of a
    yaml round-trip) so comments, ordering and the material python tags in
    the rest of mkdocs.yml are preserved byte-for-byte.

    Raises RuntimeError if the Platforms section cannot be located.
    """
    with open(mkdocs_path, encoding="utf-8") as file:
        lines = file.readlines()
    try:
        start = lines.index("  - Platforms:\n")
    except ValueError:
        raise RuntimeError(f"Could not locate the '  - Platforms:' nav section in {mkdocs_path}") from None
    end = start + 1
    while end < len(lines) and lines[end].startswith("      - "):
        end += 1
    generated = ['      - Index: "platforms/index.md"\n']
    generated += [f'      - {platform_display_name(p)}: "platforms/{p}.md"\n' for p in sorted(platforms)]
    lines[start + 1 : end] = generated
    with open(mkdocs_path, "w", encoding="utf-8") as file:
        file.writelines(lines)


def sweep_orphaned_platform_docs(
    docs_folder: str,
    valid_platforms: Iterable[str],
    preserve: frozenset[str] = _PRESERVED_PLATFORM_DOCS,
) -> list[str]:
    """Remove ``docs/platforms/*.md`` entries whose backing yaml is gone.

    Keeps the docs idempotent with the yaml directory as the source of
    truth: if a platform's yaml is deleted, the corresponding markdown
    is also removed on the next regeneration. ``preserve`` lists hand-
    authored markdown that has no yaml counterpart (index pages etc.)
    and must never be swept.

    Returns the sorted list of removed filenames for caller-side logging.
    """
    expected: set[str] = {f"{platform}.md" for platform in valid_platforms}
    removed: list[str] = []
    for entry in sorted(os.listdir(docs_folder)):
        if not entry.endswith(".md"):
            continue
        if entry in expected or entry in preserve:
            continue
        os.remove(f"{docs_folder}/{entry}")
        removed.append(entry)
    return removed


@task
def gen_docs_platform_commands(ctx):
    """Generate platform-specific command docs from the A3 ``ResolvedCommand``.

    Reads each A3 platform through the runtime loader (#264 / D9) instead of the
    legacy ``platforms_yaml`` + ``str.format`` path: literal output is emitted
    verbatim, template output is rendered with the platform name as the device
    ``base_prompt`` (matching the old build-time substitution). Only the A3
    static surface is documented — py-module dynamic handlers were never in the
    docs (the old generator read yaml only), so the coverage is unchanged.
    """
    # Lazy import: keep `invoke --list` / lint-only tasks free of the pydantic /
    # jinja2 load cost unless this task actually runs (same paradigm as
    # `netmiko_check`).
    from simnos.core.platform_loader import load_platform_dir

    docs_folder: str = "docs/platforms"
    platforms: list[str] = _a3_platform_names()

    for platform in platforms:
        print(f"Generating Platform: {platform}")
        resolved = load_platform_dir(os.path.join(PLATFORMS_A3_DIR, platform))
        with open(f"{docs_folder}/{platform}.md", "w", encoding="utf-8") as platforms_file:
            platforms_file.write(f"# {platform}\n\n")
            platforms_file.write(WARNING_MESSAGE)
            platforms_file.write("## Commands\n\n")
            for command, rc in resolved.commands.items():
                platforms_file.write(f"### {command}\n\n")
                if rc.output.kind == "none":
                    platforms_file.write("**Output:** None\n\n")
                else:
                    # `base_prompt` = platform name (the old build-time choice);
                    # strip the file-convention trailing newline for display.
                    rendered = (rc.output.render(platform) or "").rstrip("\n")
                    platforms_file.write(f"**Output:**\n```\n{rendered}\n```\n\n")
                platforms_file.write(f"**Help:** {rc.help}\n\n")
                platforms_file.write("**Prompt:**\n")
                # The modes the command is visible in, rendered in canonical
                # order (user/enable/config). An all-modes command (empty `modes`,
                # the legacy prompt-omission successor) lists none — same as the
                # old generator emitting no prompt lines for an omitted prompt.
                for mode_name, mode in resolved.modes.items():
                    if mode_name in rc.modes:
                        platforms_file.write(f"- {mode.render_prompt(platform)}\n")
                platforms_file.write("\n")

    for orphan in sweep_orphaned_platform_docs(docs_folder, platforms):
        print(f"Removed orphaned doc: {orphan}")

    rewrite_mkdocs_platforms_nav(platforms)
    print("Regenerated mkdocs.yml Platforms nav")


@task(help={"device_type": "The device type to connect to."})
def netmiko_check(ctx, device_type: str):
    """
    This is a task for debugging possible problems with Netmiko logins.
    """
    # Lazy import: keep `invoke --list` and lint-only tasks fast by avoiding
    # the heavy netmiko / simnos import cost unless this task is actually run.
    from netmiko import ConnectHandler

    from simnos import SimNOS

    init_time = time.time()
    inventory = {
        "hosts": {
            "host1": {
                "username": "user",
                "password": "user",
                "platform": device_type,
                "port": 6000,
            }
        }
    }

    credentials = {
        "host": "localhost",
        "username": "user",
        "password": "user",
        "port": 6000,
        "device_type": device_type,
    }

    net = SimNOS(inventory=inventory)
    net.start()

    with ConnectHandler(**credentials):
        time.sleep(1)

    net.stop()

    print("Everything is OK! ✅")
    print(f"Time spent: {time.time() - init_time:.2f}s")
