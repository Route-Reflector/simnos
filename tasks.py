"""Invoke tasks for simnos.

Provides lint / static-analysis wrappers (`ruff`, `yamllint`, `bandit`),
local docs serving (`docs`), platform docs generation
(`gen_docs_platform_commands`), and a Netmiko login debug helper
(`netmiko_check`).
"""

from collections.abc import Iterable
import glob
import os
import string
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


# --- platform yaml conventions lint (#244) -----------------------------------

# Real path — a shorthand here would make the glob empty and the lint a
# silent pass, which defeats the ratchet entirely. The `*.yaml` glob below
# mirrors the plugin discovery glob (simnos/plugins/nos/__init__.py), which
# also only picks up `.yaml` — a stray `.yml` is invisible to both.
PLATFORMS_YAML_DIR = "simnos/plugins/nos/platforms_yaml"
PLATFORM_YAML_LINT_BASELINE = "platform_yaml_lint_baseline.yaml"
HERITAGE_HELP_SENTENCE = "Feel free to change it!"


def is_stub_help(help_text: str) -> bool:
    """Return True for an auto-generated stub help (FakeNOS heritage).

    Covers the lower/upper-case `execute the command ...` prefix and the
    `This automatically generated` marker (#244 / P-13).

    Deliberately prefix/marker-based, so a hand-edited help that keeps
    the stub prefix still counts as a stub — improving a help means
    dropping the prefix, not appending to it (conservative direction:
    the false-positive side only freezes an entry in the baseline, it
    never lets new drift through).
    """
    lowered = help_text.lower()
    return lowered.startswith("execute the command") or "this automatically generated" in lowered


def check_platform_yaml(
    platforms_dir: str = PLATFORMS_YAML_DIR,
    baseline_path: str = PLATFORM_YAML_LINT_BASELINE,
) -> list[str]:
    """Check platform yamls against the authoring conventions (#244).

    Baseline-ratchet rules (the baseline freezes today's drift; new drift
    fails CI, improvements must shrink the baseline in the same PR):

    1. every platform defines a `_default_` command (baseline-exempt)
    2. no command gains an auto-generated stub help (identity set per
       file — a count would let "improve one, add one" slip through)
    3. no help contains the heritage sentence "Feel free to change it!"
       (checked on parsed help values: a raw-text grep is fooled by
       folded scalars splitting the sentence across lines)
    4. no baseline entry points at a file that no longer exists
    5. no baseline entry remains for a violation that was fixed
       (forgetting to shrink the baseline would let later regressions
       grow back unnoticed)

    Returns a list of human-readable violations (empty = clean).
    """
    with open(baseline_path, encoding="utf-8") as f:
        baseline = yaml.safe_load(f) or {}
    baseline_missing = set(baseline.get("missing_default") or [])
    baseline_stub = {file: set(commands or []) for file, commands in (baseline.get("stub_help") or {}).items()}

    violations: list[str] = []
    paths = sorted(glob.glob(os.path.join(platforms_dir, "*.yaml")))
    if not paths:
        return [f"{platforms_dir}: no platform yamls found (wrong path?)"]
    seen: set[str] = set()
    for path in paths:
        rel = path.replace(os.sep, "/")
        seen.add(rel)
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        commands = (data or {}).get("commands") or {}
        helps = {
            name: details["help"]
            for name, details in commands.items()
            if isinstance(details, dict) and isinstance(details.get("help"), str)
        }
        # rule 1 / 5: _default_ presence vs baseline
        if "_default_" not in commands and rel not in baseline_missing:
            violations.append(f"{rel}: missing '_default_' command (new platforms must define one)")
        if "_default_" in commands and rel in baseline_missing:
            violations.append(
                f"{rel}: defines '_default_' but is still listed under missing_default — shrink {baseline_path}"
            )
        # rule 2 / 5: stub-help identity set vs baseline
        current_stubs = {name for name, help_text in helps.items() if is_stub_help(help_text)}
        allowed_stubs = baseline_stub.get(rel, set())
        violations.extend(
            f"{rel}: command '{name}' adds an auto-generated stub help — write a real one"
            for name in sorted(current_stubs - allowed_stubs)
        )
        violations.extend(
            f"{rel}: command '{name}' no longer has a stub help but is still listed under stub_help "
            f"— shrink {baseline_path}"
            for name in sorted(allowed_stubs - current_stubs)
        )
        # rule 3: heritage sentence
        violations.extend(
            f"{rel}: command '{name}' help still contains {HERITAGE_HELP_SENTENCE!r}"
            for name in sorted(name for name, help_text in helps.items() if HERITAGE_HELP_SENTENCE in help_text)
        )
    # rule 4: stale baseline entries
    violations.extend(
        f"{rel}: listed in {baseline_path} but the file does not exist — remove the stale entry"
        for rel in sorted((baseline_missing | set(baseline_stub)) - seen)
    )
    return violations


@task
def lint_platform_yaml(context):
    """Lint platform yamls against the authoring conventions (#244).

    Baseline-ratchet lint: see `check_platform_yaml` for the rules. The
    baseline lives in `platform_yaml_lint_baseline.yaml` (repo root) and
    only ever shrinks — additions fail CI.
    """
    violations = check_platform_yaml()
    for violation in violations:
        print(violation)
    if violations:
        raise Exit(f"platform yaml lint failed with {len(violations)} violation(s)", code=1)
    print("platform yaml lint OK")


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


def render_template(template: str, platform: str, command: str, field: str) -> str:
    """Render a YAML string template the same way the runtime shell does.

    Uses `str.format(base_prompt=platform)` to match `cmd_shell.default`:
    substitutes `{base_prompt}` and unescapes `{{` / `}}` literals from
    `sync_ntc_commands.escape_format_braces` preventive escape.

    Build time is strict: besides re-raising the `FORMAT_ERRORS` catch set
    shared with the lenient runtime `cmd_shell._safe_format`, this rejects
    unsupported constructs that `str.format()` would happily render (e.g.
    `{base_prompt!r}` or `{base_prompt:>20}`) — only a plain
    `{base_prompt}` field and `{{` / `}}` escapes are supported. Every
    failure surfaces as `RuntimeError` carrying the platform / command /
    field context, so CI failures pinpoint the offending YAML entry
    instead of dumping a contextless stack trace.
    """
    # Lazy import: keep `invoke --list` / lint-only tasks fast (the existing
    # tasks.py convention, see netmiko_check); cached after the first call.
    from simnos.plugins.shell.cmd_shell import FORMAT_ERRORS

    try:
        # Strict authoring check first: a malformed template raises ValueError
        # out of parse() (caught below); a well-formed but unsupported
        # construct (conversion / format spec / non-base_prompt field) would
        # render silently, so it must be rejected explicitly.
        for _, field_name, format_spec, conversion in string.Formatter().parse(template):
            if field_name is None:
                continue
            if field_name != "base_prompt" or conversion is not None or format_spec:
                raise RuntimeError(
                    f"Failed to format {field} for {platform}/{command!r}: unsupported template "
                    f"construct (field_name={field_name!r}, conversion={conversion!r}, "
                    f"format_spec={format_spec!r}). Only '{{base_prompt}}' substitution and "
                    f"'{{{{' / '}}}}' escapes are supported."
                )
        return template.format(base_prompt=platform)
    except FORMAT_ERRORS as exc:
        raise RuntimeError(
            f"Failed to format {field} for {platform}/{command!r}: {exc!r}. "
            f"Check that any literal '{{' / '}}' in YAML is escaped as '{{{{' / '}}}}'."
        ) from exc


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

    The caller passes the same yaml-derived platform list the docs pages
    are generated from, so every nav entry has a backing page. This is
    intentional: a hypothetical yaml-less py-only platform has no docs page
    to link, so it must not get a nav entry here — the registry-truth pin
    (`test_available_platforms_match_mkdocs_nav`) failing is the designed
    loud signal to decide how to document such a platform.
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
    """
    Generate platform specific commands in the docs.
    """
    platforms_folder: str = PLATFORMS_YAML_DIR
    docs_folder: str = "docs/platforms"
    files: list[str] = os.listdir(platforms_folder)
    platforms: list[str] = [platform.split(".yaml")[0] for platform in files]

    for platform in platforms:
        print(f"Generating Platform: {platform}")
        with open(f"{platforms_folder}/{platform}.yaml", encoding="utf-8") as file:
            data = yaml.safe_load(file)
        with open(f"{docs_folder}/{platform}.md", "w", encoding="utf-8") as platforms_file:
            platforms_file.write(f"# {platform}\n\n")
            platforms_file.write(WARNING_MESSAGE)
            platforms_file.write("## Commands\n\n")
            for command, details in data["commands"].items():
                platforms_file.write(f"### {command}\n\n")
                output = details.get("output")
                if not output:
                    platforms_file.write("**Output:** None\n\n")
                else:
                    rendered = render_template(output, platform, command, "output")
                    platforms_file.write(f"**Output:**\n```\n{rendered}\n```\n\n")
                platforms_file.write(f"**Help:** {details.get('help', '')}\n\n")
                platforms_file.write("**Prompt:**\n")
                prompts = details.get("prompt", [])
                if not isinstance(prompts, list):
                    prompts = [prompts]
                for prompt in prompts:
                    rendered = render_template(prompt, platform, command, "prompt")
                    platforms_file.write(f"- {rendered}\n")
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
