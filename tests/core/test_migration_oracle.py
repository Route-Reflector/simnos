"""Migration oracle (b'): adapter projection == v2 frozen-replica projection.

#264 / P1-1 Decision 3 (b'). PR-1 (the shell rewire increment) removes v2's
``str.format`` render semantics and prompt-string matching from the runtime, so
this test carries a **frozen reimplementation** of them and asserts, across all
shipped platforms, that the legacy adapter
(:func:`simnos.core.command_adapter.adapt_legacy_commands`) projects every
command to the same client-observable behavior v2 produced.

This pins "adapter == v2" *independently of the adapter's own code*: the
comparison input is the raw legacy command dict run through the frozen replica,
not anything the adapter computed — which is what stops the gate from
degenerating into the adapter self-checking (Decision 3, 1st round claude #3).

Projection (Decision 3): for a fixed ``base_prompt``, the rendered output as
``splitlines()`` (wire-equivalent: ``writeline`` absorbs trailing newlines),
the set of modes the command is visible in, the transition target mode, and
``exit`` / ``help`` / variant count. ``_default_`` is the unconditional
fallback v2 never prompt-matches, so its mode visibility / transition are
excluded from the comparison (Decision 3 / D5).

Scope: this gate covers the **static / mechanically-converted** surface
(string output, prompt->mode, static new_prompt->new_mode). Callable handler
output is collapsed to a sentinel — handler dynamic transitions
(``make_exit`` / ``_return`` / ``disable``) are NOT projected here, because the
v2 handler code was rewritten in place (no frozen v2 handler exists to compare
against); those conversions are pinned per-mode by the device-class tests in
tests/plugins/nos/ (2nd round codex #2 / claude #6).

Two further fidelity limits, harmless on shipped data (claude #6):
- `_v2_new_mode` projects a canonical-外 new_prompt to None (no transition);
  the adapter loud-raises on the same input, so the comparison is never
  reached (shipped data is 100% canonical).
- do_help's alias-visibility refinement (claude #2) is shared by the replica
  (both read merged modes), so it is not a comparison axis here.

One-shot gate — removable once the A3 migration completes (PR-3).
"""

import copy

import pytest

from simnos.core.command_adapter import adapt_legacy_commands
from simnos.core.nos import Nos
from simnos.plugins.nos import available_platforms, nos_plugins
from simnos.plugins.shell.cmd_shell import BASIC_COMMANDS

# Fixed device prompt for the projection; any value with distinct canonical
# renders works (Decision 3 "固定 base_prompt").
_FIXED = "oracle"
# Sentinels kept out of the str/list value space so they compare by identity.
_HANDLER = "<<handler>>"
_ALL_MODES = "<<all-modes>>"
# Frozen copy of v2's `str.format` failure modes (cmd_shell.FORMAT_ERRORS as of
# PR-1) — the shell increment deletes the original, this replica must not.
_V2_FORMAT_ERRORS = (KeyError, IndexError, ValueError, AttributeError, TypeError)


def _v2_format(template: str):
    """v2 `_safe_format`: `str.format` with a silent raw fallback on failure."""
    try:
        return template.format(base_prompt=_FIXED)
    except _V2_FORMAT_ERRORS:
        return template


def _rendered_modes(nos: Nos) -> dict[str, str]:
    """Render each canonical mode prompt the way v2 would (str.format)."""
    sources = {"user": nos.initial_prompt, "enable": nos.enable_prompt, "config": nos.config_prompt}
    return {name: tmpl.format(base_prompt=_FIXED) for name, tmpl in sources.items() if tmpl}


def _v2_visible_modes(prompt_value, rendered_modes: dict[str, str]):
    """v2 `_check_prompt` replica: which canonical modes match the prompt(s)."""
    if prompt_value is None:
        return _ALL_MODES
    candidates = [prompt_value] if isinstance(prompt_value, str) else prompt_value
    visible = set()
    for candidate in candidates:
        try:
            rendered = candidate.format(base_prompt=_FIXED)
        except _V2_FORMAT_ERRORS:
            continue  # _safe_format returns None -> never a match
        visible |= {name for name, mode_prompt in rendered_modes.items() if rendered == mode_prompt}
    return visible


def _v2_new_mode(new_prompt, rendered_modes: dict[str, str]) -> str | None:
    """v2 transition replica: the mode whose prompt the new_prompt renders to."""
    if new_prompt is None:
        return None
    rendered = _v2_format(new_prompt)
    for name, mode_prompt in rendered_modes.items():
        if rendered == mode_prompt:
            return name
    return None


def _v2_output(value):
    """Project a legacy output value the way the wire would observe it."""
    if value is None:
        return None
    if callable(value):
        return _HANDLER
    return _v2_format(value).splitlines()


def _replica_projection(merged: dict, rendered_modes: dict[str, str]) -> dict[str, dict]:
    """Project every (alias-merged) legacy command via the frozen v2 replica."""
    projection: dict[str, dict] = {}
    for name, entry in merged.items():
        # v2 `do_help` reads the raw (unmerged) entry, so an alias's observable
        # help is its own, not the target's (#264 / D6).
        own_help = entry.get("help", "")
        if "alias" in entry:
            target = merged.get(entry["alias"])
            if target is None:
                continue  # missing target -> dropped (v2 unknown-command path)
            entry = {**target, **entry}
        is_default = name == "_default_"
        variants = entry.get("output_variants")
        projection[name] = {
            "output": _v2_output(entry.get("output")),
            # `_default_` is never prompt-matched by v2 -> exclude from compare.
            "modes": None if is_default else _v2_visible_modes(entry.get("prompt"), rendered_modes),
            "new_mode": None if is_default else _v2_new_mode(entry.get("new_prompt"), rendered_modes),
            "exit": bool(entry.get("exit")),
            "help": own_help,
            "variant_count": (len(variants) + 1) if variants else 0,
        }
    return projection


def _adapter_projection(commands: dict) -> dict[str, dict]:
    """Project every adapter-resolved command into the same comparison shape."""
    projection: dict[str, dict] = {}
    for name, rc in commands.items():
        out = rc.output
        if out.kind == "handler":
            rendered = _HANDLER
        elif out.kind == "none":
            rendered = None
        else:
            body = out.render(_FIXED)
            rendered = body.splitlines() if body is not None else None
        is_default = name == "_default_"
        projection[name] = {
            "output": rendered,
            "modes": None if is_default else (_ALL_MODES if not rc.modes else set(rc.modes)),
            "new_mode": rc.new_mode,
            "exit": rc.exit,
            "help": rc.help,
            "variant_count": len(rc.variants),
        }
    return projection


@pytest.mark.parametrize("platform", available_platforms)
def test_adapter_matches_v2_replica(platform):
    """Every shipped command projects identically under v2-replica and adapter."""
    nos = Nos(filename=nos_plugins[platform])
    # The shell merges BASIC commands under the platform's own (which win).
    merged = {**copy.deepcopy(BASIC_COMMANDS), **copy.deepcopy(nos.commands)}

    rendered_modes = _rendered_modes(nos)
    replica = _replica_projection(merged, rendered_modes)
    resolved = adapt_legacy_commands(nos.initial_prompt, nos.enable_prompt, nos.config_prompt, merged)
    adapter = _adapter_projection(resolved.commands)

    assert set(adapter) == set(replica), f"{platform}: command set differs"
    mismatches = {name: (replica[name], adapter[name]) for name in replica if replica[name] != adapter[name]}
    assert not mismatches, f"{platform}: {len(mismatches)} command(s) diverge from v2: {sorted(mismatches)}"
