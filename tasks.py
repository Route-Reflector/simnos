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

# Stdlib-only shared helpers (no `simnos` import), so `invoke --list` and the
# lint tasks stay free of the pydantic / asyncssh load cost (#264 / D1).
from a3_paths import PLATFORMS_DIR as PLATFORMS_A3_DIR
from a3_paths import list_a3_platform_names, sanitize_command_stem


def run_cmd(context, exec_cmd):
    """Run an invoke task command locally with a pty."""
    print(f"Running command: {exec_cmd}")
    return context.run(exec_cmd, pty=True)


@task
def ruff(context):
    """Run ruff to check that Python files adherence to ruff standards."""
    # `ruff check --diff` only reports violations that HAVE an autofix (exit 0 on
    # e.g. F821/S/B/PERF hits), which silently blinded the CI gate to most of the
    # selected rule set (#344); the plain `check` reports everything. `format
    # --diff` is a real format check and stays.
    run_cmd(context, "ruff check")
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


def _iter_platform_command_dirs(platforms_dir: str):
    """Yield ``(platform, commands_dir)`` for every platform with a commands dir.

    The single walk shared by every ``check_platform_data_*`` lint pass — an
    absent platforms dir or a platform without a ``commands/`` subdir is
    skipped, so callers loop over real targets only.
    """
    if not os.path.isdir(platforms_dir):
        return
    for platform in sorted(os.listdir(platforms_dir)):
        commands_dir = os.path.join(platforms_dir, platform, "commands")
        if os.path.isdir(commands_dir):
            yield platform, commands_dir


def _iter_command_yamls(commands_dir: str):
    """Yield ``(yaml_path, parsed_data)`` for every command yaml in the dir.

    The glob + parse loop every lint pass repeats; an empty / null yaml parses
    to ``{}`` so callers can ``.get`` without guarding.
    """
    for command_yaml in sorted(glob.glob(os.path.join(commands_dir, "*.yaml"))):
        with open(command_yaml, encoding="utf-8") as f:
            yield command_yaml, yaml.safe_load(f) or {}


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
    for platform, commands_dir in _iter_platform_command_dirs(platforms_dir):
        violations.extend(
            f"{platform}/commands/{os.path.basename(stray)}: uses .yml; the loader only globs .yaml"
            for stray in sorted(glob.glob(os.path.join(commands_dir, "*.yml")))
        )
        referenced: dict[str, list[str]] = {}
        for command_yaml, data in _iter_command_yamls(commands_dir):
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
    for platform, commands_dir in _iter_platform_command_dirs(platforms_dir):
        for command_yaml, data in _iter_command_yamls(commands_dir):
            stem = os.path.basename(command_yaml).removesuffix(".yaml")
            command = data.get("command")
            if isinstance(command, str):
                base = sanitize_command_stem(command)
                # Accept the exact stem or the deterministic ``__<n>`` collision
                # suffix the migrate / sync tools append (not an arbitrary ``__x``).
                if stem != base and not re.fullmatch(rf"{re.escape(base)}__\d+", stem):
                    warnings.append(
                        f"{platform}/commands/{stem}.yaml: filename does not match command {command!r} "
                        f"(expected stem {base!r})"
                    )
            if data.get("type") == "ntc" and not data.get("source"):
                warnings.append(
                    f"{platform}/commands/{stem}.yaml: type: ntc but no `source` block (provenance missing)"
                )
    return warnings


def check_platform_data_device_type_collisions(platforms_dir: str = PLATFORMS_A3_DIR) -> list[str]:
    """Flag device_type alias collisions across A3 platforms (#266 / D2 defense-in-depth).

    Mirrors the runtime reverse-index guard in :mod:`simnos.plugins.nos`: each
    platform contributes its own name (*identity*) plus its ``netmiko_device_type``
    / ``ntc_platform`` aliases as device_type keys. A key that resolves to more
    than one platform is a collision — including an alias that lands on another
    platform's identity name (2nd round gemini #3). The runtime guard already
    raises on import; this surfaces the same conflict at authoring time with a
    clear message instead of an import crash. Re-registering the same
    ``(key -> platform)`` pair (the common ``name == netmiko == ntc`` case) is a
    no-op, matching the runtime value-comparison rule.

    Returns a list of human-readable violation strings (empty = clean).
    """
    index: dict[str, str] = {}
    violations: list[str] = []

    def register(key, platform: str, kind: str) -> None:
        if not key or not isinstance(key, str):
            return
        prev = index.get(key)
        if prev is not None and prev != platform:
            violations.append(f"device_type collision: {key!r} ({kind} of {platform}) already maps to {prev}")
            return
        index[key] = platform

    names = list_a3_platform_names(platforms_dir)
    # Identity first (same order discipline as the runtime guard) so an alias
    # colliding with another platform's name is reported against the alias.
    for platform in names:
        register(platform, platform, "identity")
    for platform in names:
        meta_path = os.path.join(platforms_dir, platform, "platform.yaml")
        # A malformed platform.yaml becomes a violation string rather than a
        # crashing traceback, so the lint stays symmetric with the runtime
        # index guard's warn+skip degradation (#266 1st round gemini #6 / claude #4).
        try:
            with open(meta_path, encoding="utf-8") as f:
                meta = yaml.safe_load(f)
        except (yaml.YAMLError, OSError) as exc:
            violations.append(f"{platform}/platform.yaml: unreadable for device_type collision check ({exc})")
            continue
        if not isinstance(meta, dict):
            violations.append(f"{platform}/platform.yaml: not a mapping; cannot check device_type aliases")
            continue
        register(meta.get("netmiko_device_type"), platform, "netmiko_device_type")
        register(meta.get("ntc_platform"), platform, "ntc_platform")
    return violations


# Render variables the loader substitutes in the `.j2` / challenge channels,
# mirrored from `simnos.core.resolved_command` (KNOWN_RENDER_VARS |
# CHALLENGE_RENDER_VARS). Hardcoded because tasks.py stays simnos-import-free
# (#264 / D1); `tests/test_lint_platform_data.py` pins this tuple against the
# real constants so a new render variable cannot silently escape the guard.
_RENDER_VAR_NAMES = ("base_prompt", "username")
# Single-brace (`{base_prompt}`, the str.format heritage that leaked in #328),
# double-brace (`{{ base_prompt }}`, the jinja spelling) and any mismatched
# hybrid are all flagged, including trailing jinja filters / format specs
# (`{{ base_prompt | upper }}` / `{base_prompt:<20}` — `[^}]*` up to the closing
# brace, 1st round codex #1) and jinja whitespace-control (`{{- base_prompt }}`
# — `-?\s*` after the braces, 2nd/3rd round codex; the closing-side `-}}` is
# already inside `[^}]*`): a brace expression *starting* with a render-var
# name (`\b` keeps `{base_prompt_style}` a different identifier) has no
# legitimate reading in a literal file. Real-device literals (`{ACDEF}` /
# `{master}` / `flags={origin_is_acl,}`) never start with these exact names,
# which is what keeps the false-positive rate at zero (#329). `re.escape` is a
# no-op for the current names but keeps a future metachar-bearing name from
# becoming a wildcard (1st round gemini #1).
_RENDER_VAR_LEAK_RE = re.compile(
    r"\{\{?-?\s*(?:" + "|".join(re.escape(name) for name in _RENDER_VAR_NAMES) + r")\b[^}]*\}?\}"
)


def check_platform_data_render_leaks(platforms_dir: str = PLATFORMS_A3_DIR) -> list[str]:
    """Flag jinja render variables leaked into literal ``.txt`` outputs (#329).

    The ``.txt`` channel is served verbatim (never rendered), so a
    ``{base_prompt}`` / ``{{ base_prompt }}`` inside one reaches the wire
    unsubstituted — the #328 arista_eos ``show hostname`` regression class. A
    body that needs a render variable must be authored as ``.j2``
    (``output_template:``) instead. Scans every ``.txt`` under ``commands/``
    (variants included); ``.j2`` is the render channel and exempt. Undecodable
    bytes are replaced rather than raised — a broken encoding is already a
    gating violation in `check_platform_data` and must not crash this pass.

    Returns a list of human-readable violation strings (empty = clean).
    """
    violations: list[str] = []
    for platform, commands_dir in _iter_platform_command_dirs(platforms_dir):
        for txt_path in sorted(glob.glob(os.path.join(commands_dir, "*.txt"))):
            with open(txt_path, encoding="utf-8", errors="replace") as f:
                content = f.read()
            for match in _RENDER_VAR_LEAK_RE.finditer(content):
                line_no = content.count("\n", 0, match.start()) + 1
                violations.append(
                    f"{platform}/commands/{os.path.basename(txt_path)}:{line_no}: render variable "
                    f"{match.group(0)!r} in a literal .txt — author it as a .j2 output_template instead (#328)"
                )
    return violations


def check_platform_data_py_modules(platforms_dir: str = PLATFORMS_A3_DIR) -> list[str]:
    """Cross-check the A3 platforms against their py handler modules (#317 P-4).

    Two gating rules, both about the ``handler:`` channel's binding contract
    (a `handler:` ref binds against the co-named ``platforms_py/<name>.py``
    module's namespace at merge time — `build_resolved_platform`):

    1. **orphan py module**: a ``platforms_py/<name>.py`` with no
       ``platforms/<name>/`` A3 dir can never be registered (the registry
       warns and skips it since #317 P-4) — flag it at authoring time.
    2. **unbindable handler ref**: a command yaml carrying ``handler:`` on a
       platform that ships no py module would fail at every ``Host.start``;
       flag it here so the author sees it before running a server. (Whether the
       named callable exists inside the module is the runtime bind's job — this
       lint is stdlib-only and does not import plugin code.)

    Returns a list of human-readable violation strings (empty = clean).
    """
    py_dir = os.path.join(os.path.dirname(os.path.normpath(platforms_dir)), "platforms_py")
    py_modules = {
        os.path.basename(p)[: -len(".py")]
        for p in glob.glob(os.path.join(py_dir, "*.py"))
        if os.path.basename(p) != "__init__.py"
    }
    a3_platforms = set(list_a3_platform_names(platforms_dir))
    violations = [
        f"platforms_py/{name}.py: no matching A3 platform dir (platforms/{name}/) — "
        "py-only platforms were removed (#317 P-4); the registry will not register it"
        for name in sorted(py_modules - a3_platforms)
    ]
    for platform, commands_dir in _iter_platform_command_dirs(platforms_dir):
        if platform in py_modules:
            continue
        violations.extend(
            f"{platform}/commands/{os.path.basename(command_yaml)}: `handler: {data['handler']}` but the platform "
            f"ships no platforms_py/{platform}.py module — the ref can never bind at Host.start"
            for command_yaml, data in _iter_command_yamls(commands_dir)
            if isinstance(data.get("handler"), str)
        )
    return violations


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


# --- A3 authoring ratchet (#276, ported from the #244 platform-yaml lint) ----

PLATFORM_DATA_LINT_BASELINE = "platform_data_lint_baseline.yaml"
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


def check_platform_data_ratchet(
    platforms_dir: str = PLATFORMS_A3_DIR,
    baseline_path: str = PLATFORM_DATA_LINT_BASELINE,
) -> list[str]:
    """Check the A3 platform dirs against the authoring ratchet (#276).

    Baseline-ratchet rules (the baseline freezes today's drift; new drift
    fails CI, improvements must shrink the baseline in the same PR):

    1. every platform defines a `_default_` command (baseline-exempt)
    2. no command gains an auto-generated stub help (identity set per
       platform — a count would let "improve one, add one" slip through)
    3. no help contains the heritage sentence "Feel free to change it!"
       (checked on parsed help values: a raw-text grep is fooled by
       folded scalars splitting the sentence across lines)
    4. no baseline entry points at a platform that no longer exists
    5. no baseline entry remains for a violation that was fixed
       (forgetting to shrink the baseline would let later regressions
       grow back unnoticed)

    Ported from the #244 `check_platform_yaml` ratchet, re-keyed for A3:
    the lint unit is the platform dir (not a monolithic yaml file), so the
    baseline keys are platform names and the stub identity sets hold
    `command` field values (the SSoT, not filenames).

    Two intentional non-guards (vs the old monolithic lint):

    - wrong path: unlike the old `check_platform_yaml`, this has no
      "empty glob → loud" self-guard. The `lint_platform_data` task owns
      that check (`list_a3_platform_names()` raises on an empty platforms
      dir), so a typo'd path is caught before the ratchet runs. A direct
      `check_platform_data_ratchet(wrong_dir, baseline)` call still fails
      loudly today because the shipped baseline lists all 50 platforms, so
      rule 4 fires once per stale entry (pinned by
      `TestRatchet.test_wrong_path_fires_stale_entries`).
    - duplicate `command`: two yamls in one platform declaring the same
      `command` is a load error in `platform_loader` (and every platform is
      load-tested in `tests/plugins/test_platforms.py`), so the last-wins
      `helps[command]` here cannot mask a stub in practice — the loader is
      the SSoT for command uniqueness, not this lint.

    Returns a list of human-readable violations (empty = clean).
    """
    with open(baseline_path, encoding="utf-8") as f:
        baseline = yaml.safe_load(f) or {}
    baseline_missing = set(baseline.get("missing_default") or [])
    baseline_stub = {platform: set(commands or []) for platform, commands in (baseline.get("stub_help") or {}).items()}

    violations: list[str] = []
    seen: set[str] = set()
    for platform, commands_dir in _iter_platform_command_dirs(platforms_dir):
        seen.add(platform)
        commands: set[str] = set()
        helps: dict[str, str] = {}
        for _, data in _iter_command_yamls(commands_dir):
            command = data.get("command")
            if not isinstance(command, str):
                continue
            commands.add(command)
            if isinstance(data.get("help"), str):
                helps[command] = data["help"]
        # rule 1 / 5: _default_ presence vs baseline
        if "_default_" not in commands and platform not in baseline_missing:
            violations.append(f"{platform}: missing '_default_' command (new platforms must define one)")
        if "_default_" in commands and platform in baseline_missing:
            violations.append(
                f"{platform}: defines '_default_' but is still listed under missing_default — shrink {baseline_path}"
            )
        # rule 2 / 5: stub-help identity set vs baseline
        current_stubs = {name for name, help_text in helps.items() if is_stub_help(help_text)}
        allowed_stubs = baseline_stub.get(platform, set())
        violations.extend(
            f"{platform}: command '{name}' adds an auto-generated stub help — write a real one"
            for name in sorted(current_stubs - allowed_stubs)
        )
        violations.extend(
            f"{platform}: command '{name}' no longer has a stub help but is still listed under stub_help "
            f"— shrink {baseline_path}"
            for name in sorted(allowed_stubs - current_stubs)
        )
        # rule 3: heritage sentence
        violations.extend(
            f"{platform}: command '{name}' help still contains {HERITAGE_HELP_SENTENCE!r}"
            for name in sorted(name for name, help_text in helps.items() if HERITAGE_HELP_SENTENCE in help_text)
        )
    # rule 4: stale baseline entries (`seen` only holds platforms with a
    # `commands/` dir, so a bare dir with no command data reads as stale too —
    # the wording covers both "removed" and "no longer an A3 platform").
    violations.extend(
        f"{platform}: listed in {baseline_path} but is not an A3 platform with command data — remove the stale entry"
        for platform in sorted((baseline_missing | set(baseline_stub)) - seen)
    )
    return violations


@task
def lint_platform_data(context):
    """Lint the A3 platform data directories (#264 / D8, D9 + #276 ratchet).

    Gating: encoding (UTF-8 / LF / trailing newline), orphan output files,
    shared output references, extension convention, stray ``.yml`` (see
    `check_platform_data`) + the authoring baseline ratchet (`_default_`
    presence / stub help / heritage wording, see
    `check_platform_data_ratchet`) + device_type alias collisions across
    platforms (#266, see `check_platform_data_device_type_collisions`)
    + py-module cross-checks (orphan ``platforms_py`` module / unbindable
    ``handler:`` ref, #317 P-4, see `check_platform_data_py_modules`)
    + render-variable leaks into literal ``.txt`` (#329, see
    `check_platform_data_render_leaks`).
    Warning-tier (printed, non-blocking):
    filename convention + ``type: ntc`` provenance (see
    `check_platform_data_warnings`).
    """
    # Loud on an empty platforms dir: after the A3 migration completed, 0
    # platforms means a wrong path / broken checkout, not a legitimate
    # pre-migration state — fail standalone instead of silently printing OK
    # (3rd round claude #7; the CI snapshot-set pin catches it too).
    if not list_a3_platform_names():
        raise Exit(f"platform data lint: no A3 platforms found under {PLATFORMS_A3_DIR} (wrong path?)", code=1)

    warnings = check_platform_data_warnings()
    for warning in warnings:
        print(f"WARNING: {warning}")
    if warnings:
        print(f"({len(warnings)} warning(s) — informational, not blocking)")

    violations = (
        check_platform_data()
        + check_platform_data_ratchet()
        + check_platform_data_device_type_collisions()
        + check_platform_data_py_modules()
        + check_platform_data_render_leaks()
    )
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
    "allied_telesis_awplus": "Allied Telesis AW+",
    "arista_eos": "Arista EOS",
    "aruba_aoscx": "Aruba AOS-CX",
    "aruba_os": "Aruba OS",
    "avaya_ers": "Avaya ERS",
    "avaya_vsp": "Avaya VSP",
    "broadcom_icos": "Broadcom ICOS",
    "brocade_fastiron": "Brocade FastIron",
    "checkpoint_gaia": "Check Point Gaia",
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
    "ruckus_fastiron": "Ruckus FastIron",
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

    The caller passes the A3 platform list `gen_docs_platform_commands` just
    generated pages for, so every nav entry has a backing page. A py-only
    platform with no A3 dir gets no page and no nav entry — the registry-truth
    pin (`test_available_platforms_match_mkdocs_nav`) failing is the designed
    loud signal to decide how to document such a platform. Closes the M-1
    failure mode (#239): a new platform used to need a manual nav entry, and a
    forgotten one silently produced a docs page unreachable from the site nav.
    The section is replaced as a text block (instead of a yaml round-trip) so
    comments, ordering and the material python tags in the rest of mkdocs.yml
    are preserved byte-for-byte.

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
    """Remove ``docs/platforms/*.md`` entries with no backing A3 platform.

    Keeps the docs idempotent with the A3 platform directory as the source of
    truth: if a platform is removed, its markdown is deleted on the next
    regeneration. ``preserve`` lists hand-authored markdown that has no platform
    counterpart (index pages etc.) and must never be swept.

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
    ``base_prompt`` (matching the old build-time substitution), and a
    ``handler:`` command (dispatch-time py output, #317 P-2) is documented as
    dynamic with its handler name.
    """
    # Lazy import: keep `invoke --list` / lint-only tasks free of the pydantic /
    # jinja2 load cost unless this task actually runs (same paradigm as
    # `netmiko_check`).
    from simnos.core.platform_loader import load_platform_dir

    docs_folder: str = "docs/platforms"
    platforms: list[str] = list_a3_platform_names()

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
                elif rc.output.kind == "handler":
                    # A `handler:` command's output is computed at dispatch time
                    # by the platform's py module (#317 P-2) — there is nothing
                    # static to render, so document the dynamic source instead.
                    platforms_file.write(f"**Output:** (dynamic — py handler `{rc.output.handler_ref}`)\n\n")
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
    # Ephemeral port (0) + read-back after start, same as the default inventory
    # (#271): a fixed 6000 collided with a running `simnos up` / parallel
    # invocations and died with a raw bind traceback (#344).
    inventory = {
        "hosts": {
            "host1": {
                "username": "user",
                "password": "user",
                "device_type": device_type,
                "port": 0,
            }
        }
    }

    net = SimNOS(inventory=inventory)
    # try/finally so a Netmiko failure still stops the server (#344); before, a
    # raise skipped `net.stop()` and left the host running.
    net.start()
    try:
        credentials = {
            "host": "localhost",
            "username": "user",
            "password": "user",
            "port": net.hosts["host1"].port,
            "device_type": device_type,
        }
        with ConnectHandler(**credentials):
            time.sleep(1)
    finally:
        net.stop()

    print("Everything is OK! ✅")
    print(f"Time spent: {time.time() - init_time:.2f}s")
