#!/usr/bin/env python3
"""One-shot converter: legacy ``platforms_yaml/<name>.yaml`` -> A3 ``platforms/<name>/`` (#264 / D7).

Reads one legacy monolithic platform yaml and writes the A3 form:
``platforms/<name>/platform.yaml`` (modes + meta) + ``commands/<cmd>.yaml`` +
adjacent ``<cmd>.txt`` output files. Also emits the migration-oracle snapshot
(``tests/assets/oracle/<name>.json``) — the adapter projection of the legacy
data, frozen so the committed oracle (b) test can compare the A3 loader's
projection against it after the legacy yaml is deleted (Decision 3 (b), D7-3).

Mechanical conversions (D3 / D7):
- ``initial_prompt`` / ``enable_prompt`` / ``config_prompt`` -> ``modes`` +
  ``initial_mode: user`` (canonical user/enable/config).
- per command ``prompt`` (str|list) -> ``mode`` (list of mode names; omitted =
  all modes). ``_default_``'s prompt is dropped (mode-agnostic fallback).
- ``new_prompt`` -> ``new_mode``.
- str ``output`` -> a literal ``.txt`` file (``{{``/``}}`` unescaped); a
  ``{base_prompt}``-bearing output becomes ``output_template`` (``.j2``).
- ``output: null`` -> no output file; ``output_variants`` -> ``variants``.
- ``type`` is set to ``simnos`` for every converted command (NTC provenance is
  not recorded in the legacy data; ``source`` is backfilled by NTC re-sync).

Run from the repo root:  ``python migrate_platform_yaml.py cisco_ios``
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

import yaml

from simnos.core.command_adapter import adapt_legacy_commands
from simnos.core.platform_loader import load_platform_dir
from simnos.core.resolved_command import format_template_to_jinja

LEGACY_DIR = "simnos/plugins/nos/platforms_yaml"
A3_ROOT = "simnos/plugins/nos/platforms"
SNAPSHOT_DIR = "tests/assets/oracle"

# Legacy scalar prompt -> canonical mode name (#264 / M2).
PROMPT_FIELD_TO_MODE = (("initial_prompt", "user"), ("enable_prompt", "enable"), ("config_prompt", "config"))


def _sanitize_filename(command: str, used: set[str]) -> str:
    """Map a command name to a lint-clean, collision-free file stem (D1).

    ``[a-z0-9_.-]`` only; spaces and other chars collapse to ``_``. The stem is
    non-semantic (the ``command`` field is the SSoT, Decision 1), so a collision
    just needs a deterministic suffix.
    """
    stem = re.sub(r"[^a-z0-9_.-]", "_", command.lower())
    stem = re.sub(r"_+", "_", stem).strip("_") or "cmd"
    candidate = stem
    counter = 2
    while candidate in used:
        candidate = f"{stem}__{counter}"
        counter += 1
    used.add(candidate)
    return candidate


def _ensure_trailing_newline(text: str) -> str:
    """LF + a single trailing newline (D7). Wire-equivalent under splitlines().

    Empty output (legacy ``output: ''`` / an empty ``output_variant``) stays a
    0-byte file: a forced ``\\n`` would round-trip to ``['']`` under splitlines
    where the legacy empty literal projects to ``[]`` — a phantom blank line the
    variant-body oracle catches (fortinet / oneaccess_oneos). The lint's
    trailing-newline rule already exempts empty files (`raw and ...`).
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if text and not text.endswith("\n"):
        text += "\n"
    return text


def _build_prompt_to_mode(legacy: dict) -> dict[str, str]:
    """Map each defined legacy prompt template string to its canonical mode."""
    mapping: dict[str, str] = {}
    for field, mode in PROMPT_FIELD_TO_MODE:
        template = legacy.get(field)
        if template is not None:
            mapping[template] = mode
    return mapping


def _prompt_to_modes(prompt, prompt_to_mode: dict[str, str], command: str) -> list[str] | None:
    """Reverse-map a legacy ``prompt`` (str|list|None) to mode names."""
    if prompt is None:
        return None
    candidates = [prompt] if isinstance(prompt, str) else list(prompt)
    modes: list[str] = []
    for candidate in candidates:
        mode = prompt_to_mode.get(candidate)
        if mode is None:
            raise SystemExit(
                f"command {command!r}: prompt {candidate!r} is not one of the canonical prompts "
                f"{sorted(prompt_to_mode)!r}; manual review required (#264 / D7)"
            )
        if mode not in modes:
            modes.append(mode)
    return modes


def _write(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


def _convert_output(value, stem: str, commands_dir: str) -> dict:
    """Turn a legacy ``output`` into A3 fields + write the adjacent file.

    Returns the command-yaml fragment ({} for null, {output: ...} for literal,
    {output_template: ...} for a ``{base_prompt}`` template).
    """
    if value is None:
        return {}
    if callable(value):
        # Handlers live in the py module, never in the converted yaml data.
        raise SystemExit(f"unexpected callable output for {stem!r} in legacy yaml")
    jinja_source, has_field = format_template_to_jinja(value)
    if not has_field:
        # No render: `str.format` collapses `{{`->`{` — the literal wire text.
        _write(os.path.join(commands_dir, f"{stem}.txt"), _ensure_trailing_newline(value.format()))
        return {"output": f"{stem}.txt"}
    # `{base_prompt}` present -> a jinja template file.
    _write(os.path.join(commands_dir, f"{stem}.j2"), _ensure_trailing_newline(jinja_source))
    return {"output_template": f"{stem}.j2"}


def _convert_command(name: str, entry: dict, stem: str, commands_dir: str, prompt_to_mode: dict[str, str]) -> dict:
    """Build one A3 command-yaml mapping (field order is intentional)."""
    out: dict = {"command": name, "type": "simnos"}
    if entry.get("help"):
        out["help"] = entry["help"]
    if name != "_default_":
        modes = _prompt_to_modes(entry.get("prompt"), prompt_to_mode, name)
        if modes is not None:
            out["mode"] = modes
        new_prompt = entry.get("new_prompt")
        if new_prompt is not None:
            new_modes = _prompt_to_modes(new_prompt, prompt_to_mode, name)
            if new_modes:
                out["new_mode"] = new_modes[0]
    variants = entry.get("output_variants")
    if variants:
        variant_files = []
        for i, variant in enumerate(variants):
            vstem = f"{stem}__variant_{i + 2}"
            _write(os.path.join(commands_dir, f"{vstem}.txt"), _ensure_trailing_newline(variant.format()))
            variant_files.append({"name": f"variant_{i + 2}", "output": f"{vstem}.txt"})
        primary = _convert_output(entry.get("output"), f"{stem}__variant_1", commands_dir)
        out["variants"] = [{"name": "variant_1", **primary}, *variant_files]
    else:
        out.update(_convert_output(entry.get("output"), stem, commands_dir))
    if entry.get("exit"):
        out["exit"] = True
    return out


def _platform_meta_yaml(legacy: dict) -> str:
    """Render platform.yaml text (clean jinja prompts, intentional key order)."""
    lines = ["modes:"]
    for field, mode in PROMPT_FIELD_TO_MODE:
        template = legacy.get(field)
        if template is None:
            continue
        jinja_prompt = template.replace("{base_prompt}", "{{ base_prompt }}")
        lines.append(f"  {mode}:")
        lines.append(f'    prompt: "{jinja_prompt}"')
    lines.append("initial_mode: user")
    # `auth` has live SSH behavior (e.g. dell_powerconnect's `auth: none`); carry
    # it through so the A3 form does not silently drop it (1st round claude #2).
    if legacy.get("auth") is not None:
        lines.append(f"auth: {legacy['auth']}")
    lines.append(f"netmiko_device_type: {legacy['name']}")
    lines.append(f"ntc_platform: {legacy['name']}")
    return "\n".join(lines) + "\n"


def _projection(commands: dict) -> dict[str, dict]:
    """JSON-friendly projection for the oracle snapshot (shared shape with the test)."""
    # Imported lazily so the script does not hard-depend on the test package
    # unless a snapshot is actually built.
    from tests.core.oracle_projection import project_resolved

    return project_resolved(commands)


def convert(platform: str) -> None:
    legacy_path = os.path.join(LEGACY_DIR, f"{platform}.yaml")
    with open(legacy_path, encoding="utf-8") as fh:
        legacy = yaml.safe_load(fh)

    prompt_to_mode = _build_prompt_to_mode(legacy)
    platform_dir = os.path.join(A3_ROOT, platform)
    commands_dir = os.path.join(platform_dir, "commands")
    os.makedirs(commands_dir, exist_ok=True)

    _write(os.path.join(platform_dir, "platform.yaml"), _platform_meta_yaml(legacy))

    used_stems: set[str] = set()
    for name, entry in legacy.get("commands", {}).items():
        stem = _sanitize_filename(name, used_stems)
        mapping = _convert_command(name, entry, stem, commands_dir, prompt_to_mode)
        text = yaml.safe_dump(mapping, sort_keys=False, allow_unicode=True, default_flow_style=False)
        _write(os.path.join(commands_dir, f"{stem}.yaml"), text)

    # Oracle (b): adapter projection of the legacy data == A3 loader projection.
    legacy_resolved = adapt_legacy_commands(
        legacy.get("initial_prompt"),
        legacy.get("enable_prompt"),
        legacy.get("config_prompt"),
        legacy.get("commands", {}),
    )
    a3_resolved = load_platform_dir(platform_dir)
    legacy_proj = _projection(legacy_resolved.commands)
    a3_proj = _projection(a3_resolved.commands)
    if legacy_proj != a3_proj:
        diff = sorted(k for k in legacy_proj if legacy_proj.get(k) != a3_proj.get(k))
        raise SystemExit(f"{platform}: A3 projection diverges from legacy adapter for {diff}")

    snapshot_path = os.path.join(SNAPSHOT_DIR, f"{platform}.json")
    _write(snapshot_path, json.dumps(legacy_proj, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    print(f"converted {platform}: {len(legacy.get('commands', {}))} commands -> {platform_dir}")
    print(f"oracle snapshot: {snapshot_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert a legacy platform yaml to the A3 form (#264).")
    parser.add_argument("platform", help="platform name (e.g. cisco_ios)")
    args = parser.parse_args()
    convert(args.platform)


if __name__ == "__main__":
    sys.exit(main())
