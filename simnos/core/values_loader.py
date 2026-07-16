"""Sidecar-json loader + normalizer for template render values (#287 / Layer 1).

A ``.j2`` command output may be rendered with values pulled from a sidecar
``<stem>.json`` sitting next to it — the verbatim ``--parse`` output of a
KeroRoute (ntc-templates / textfsm) run. Editing a value in that json (e.g.
``version``) lets a client test version-conditional branching without owning
hardware at that version; re-parsing the rendered wire output returns the
edited value (the Layer-1 round-trip, #287 / D3, D4).

KeroRoute can save that json in more than one shape depending on its envelope
setting, and textfsm itself returns a bare list, so :func:`_normalize_values`
folds all shapes into one render-variable namespace where the parsed rows are
always reachable as the canonical var ``parsed``. The ``.j2`` author writes
``{% for row in parsed %}`` / ``{{ parsed[0].version }}`` and the same template
works regardless of how the json was saved (#287 / D4, 案A2).

This module is shared by both inflows that can carry a ``.j2``: the packaged
demo loader (:mod:`simnos.core.platform_loader`) and the user overlay loader
(:mod:`simnos.core.overlay_loader`); both also call
:func:`validate_render_values` for the build-time loud check (#287 / D5).
"""

import json
import os
from typing import Any

from jinja2 import TemplateSyntaxError, UndefinedError

from simnos.core.resolved_command import KNOWN_RENDER_VARS, ResolvedOutput, compile_template

# Non-empty sentinel base_prompt for the dry-render (#287 / D5, claude#4): an
# empty string would skip an undefined inside ``{% for %}`` bodies that also
# reference ``{{ base_prompt }}``, defeating the nested-key check. The trailing
# ``#`` mimics a real device prompt so a template doing ``base_prompt.split('#')``
# does not spuriously IndexError and get rejected at build time (3rd round gemini#1).
_DRY_SENTINEL = "<dry>#"


def _sidecar_path(j2_path: str) -> str:
    """Map ``<stem>.j2`` to its sidecar ``<stem>.json`` in the same directory."""
    root, _ext = os.path.splitext(j2_path)
    return root + ".json"


def _canonical_command(name: str) -> str:
    """Normalize a command name for sidecar matching (#287 / D4).

    Lowercase + collapse runs of internal whitespace to one space (and trim the
    ends): ``"show   ip  int brief"`` and ``"Show ip int brief"`` compare equal,
    so a cosmetic whitespace/case difference between the simnos command name and
    the KeroRoute-captured ``command`` key cannot raise a false ``ValueError``
    (#287 / D4, gemini#2 4th).
    """
    return " ".join(name.lower().split())


def _is_envelope(raw: Any) -> bool:
    """Strict KeroRoute-envelope test (#287 / D4 rule 1, R1).

    True only for a *non-empty* list whose *every* item is a dict with a ``str``
    ``command`` and a ``list`` ``parsed``. This assumes a parsed-row list never
    has rows that *all* carry both a ``str`` ``command`` and a ``list`` ``parsed``
    column (none of the ntc-templates schemas do): such a list would be read as
    an envelope. The all-items + non-empty guard does reject the realistic
    near-misses — a row list where only *some* rows carry those keys, and the
    empty list (which falls through to the bare-list rule).
    """
    return (
        isinstance(raw, list)
        and len(raw) > 0
        and all(
            isinstance(x, dict) and isinstance(x.get("command"), str) and isinstance(x.get("parsed"), list) for x in raw
        )
    )


def _normalize_values(raw: Any, command_name: str) -> dict[str, Any]:
    """Fold a sidecar payload into a render-variable namespace (#287 / D4).

    Three shapes:

    1. **envelope list** ``[{prompt, command, parsed: [...]}]`` — pick the entry
       whose ``command`` matches ``command_name`` (compared after
       :func:`_canonical_command` on both sides, length-independent: a single
       entry must still match). No match is a loud ``ValueError``. Only the
       entry's ``parsed`` rows are kept (``{"parsed": [...]}``); the envelope
       metadata keys (``command``/``prompt``) are *not* exposed as render vars
       (2nd round claude#4 / 案B). This makes the envelope and bare-list shapes
       produce an identical namespace, so the same ``.j2`` works regardless of
       how KeroRoute saved the json — the shape-independence the normalizer
       exists for — and avoids a template that silently couples to the envelope
       form by referencing ``{{ command }}`` / ``{{ prompt }}``.
    2. **bare list** ``[{...row...}]`` (textfsm) — wrapped as ``{"parsed": raw}``.
    3. **dict** — returned as-is (the user's own namespace).

    The reserved-key collision check runs once on the merged result (after all
    three rules) so a sidecar key shadowing ``base_prompt`` fails loud at build
    time instead of crashing ``render(base_prompt=.., **values)`` with "got
    multiple values" (#287 / D4 F, claude#2 4th). It is effectively only the
    dict shape that can now trip it (envelope yields just ``parsed``).
    """
    if _is_envelope(raw):
        target = _canonical_command(command_name)
        for entry in raw:
            if _canonical_command(entry["command"]) == target:
                values: dict[str, Any] = {"parsed": entry["parsed"]}
                break
        else:
            present = [entry["command"] for entry in raw]
            shown = ", ".join(present[:10])
            suffix = "" if len(present) <= 10 else f" (+{len(present) - 10} more)"
            raise ValueError(
                f"sidecar json envelope has no entry for command {command_name!r} (commands present: {shown}{suffix})"
            )
    elif isinstance(raw, list):
        values = {"parsed": raw}
    elif isinstance(raw, dict):
        values = dict(raw)
    else:
        raise ValueError(f"sidecar json for {command_name!r} must be a list or mapping, got {type(raw).__name__}")

    collisions = set(values) & KNOWN_RENDER_VARS
    if collisions:
        raise ValueError(
            f"sidecar json for {command_name!r} uses reserved render var(s) {sorted(collisions)}; "
            "rename the key(s) — these are supplied by the shell, not the sidecar"
        )
    return values


def load_values(j2_path: str, command_name: str) -> dict[str, Any]:
    """Read+normalize the sidecar ``<stem>.json`` next to ``j2_path``; ``{}`` if absent.

    An absent sidecar is not an error here — a ``.j2`` may legitimately render
    from ``base_prompt`` alone; the build-time loud check
    (:func:`validate_render_values`) is what fails a template that *needs* a
    missing value (#287 / D5).
    """
    sidecar = _sidecar_path(j2_path)
    if not os.path.isfile(sidecar):
        return {}
    with open(sidecar, encoding="utf-8") as f:
        try:
            raw = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"sidecar json {sidecar!r} for {command_name!r} is not valid JSON: {e}") from e
    return _normalize_values(raw, command_name)


def validate_render_values(output: ResolvedOutput, command_name: str, source: str) -> None:
    """Build-time loud check that a template's required vars are satisfiable (#287 / D5).

    Two layers, run at loader read time so both the normal start build and the
    hot-reload build go through the same gate (#287 / D5 I):

    1. **top-level** ``required_vars ⊆ values`` — a wholly missing variable
       (``{parsed}`` with no sidecar) is loud here.
    2. **dry-render** with ``StrictUndefined`` + a non-empty sentinel
       ``base_prompt`` + the real values — catches nested-key gaps the variable
       extraction can't see (``{{ parsed[0].version }}`` extracts ``parsed`` but
       not ``version``). Any jinja evaluation error (undefined, filter/type
       mismatch) is wrapped as a ``ValueError`` naming the command and source.

    Non-template kinds (literal ``.txt`` / handler) and ``base_prompt``-only
    templates have ``required_vars == frozenset()`` and empty values, so this is
    a no-op for them (#287 / D5, claude#3) — the legacy ``.txt`` fast path stays
    untouched.
    """
    if output.kind != "template" or output.template is None:
        return
    missing = output.required_vars - set(output.values)
    if missing:
        raise ValueError(
            f"template for {command_name!r} ({source}) needs render var(s) {sorted(missing)} "
            f"absent from its sidecar json (present: {sorted(output.values)})"
        )
    try:
        output.template.render(base_prompt=_DRY_SENTINEL, **output.values)
    except UndefinedError as e:
        raise ValueError(
            f"template for {command_name!r} ({source}) references an undefined value during dry-render: {e}"
        ) from e
    except Exception as e:
        # Any other jinja evaluation error (filter/type mismatch, bad subscript)
        # is turned into a loud build-time ValueError naming the command/source.
        raise ValueError(f"template for {command_name!r} ({source}) failed dry-render: {e}") from e


def resolve_output_file(
    ref: str, commands_dir: str, *, as_template: bool, where: str, command_name: str
) -> ResolvedOutput:
    """Read an adjacent output file into a `ResolvedOutput`.

    The authoring *field* decides the channel, not the extension: ``output`` /
    variants are read verbatim (literal wire text), ``output_template`` is
    compiled as jinja2. ``.txt`` / ``.j2`` are a lint-level naming convention,
    not load semantics.

    For the template channel the adjacent sidecar ``<stem>.json`` (if any) is
    read into ``values`` and the result is validated at build time: a template
    that needs a value the sidecar does not supply fails loud here rather than
    at connect time (#287 / Layer 1, D4/D5). ``command_name`` matches the
    sidecar envelope entry.

    Lives here (not in the platform loader) because it is shared by both
    inflows that read adjacent output files — the packaged A3 loader
    (:mod:`simnos.core.platform_loader`) and the user overlay loader
    (:mod:`simnos.core.overlay_loader`) — matching this module\'s charter;
    it was a private cross-module import before (#350).
    """
    filepath = os.path.join(commands_dir, ref)
    if not os.path.isfile(filepath):
        raise ValueError(f"{where}: output file {ref!r} not found at {filepath}")
    with open(filepath, encoding="utf-8") as fh:
        content = fh.read()
    if as_template:
        try:
            template, required = compile_template(content)
        except TemplateSyntaxError as e:
            raise ValueError(f"{where}: output template {ref!r} has a jinja2 syntax error: {e}") from e
        values = load_values(filepath, command_name)
        output = ResolvedOutput(kind="template", template=template, required_vars=required, values=values)
        validate_render_values(output, command_name, source=filepath)
        return output
    return ResolvedOutput(kind="literal", text=content)
