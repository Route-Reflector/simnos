"""Legacy-form -> `ResolvedCommand` normalization core (#264 / P1-1 D6).

This is the bridge that lets PR-1 ship the new runtime representation
(:mod:`simnos.core.resolved_command`) and mode engine while the data is still
in the v2 ``platforms_yaml`` / py-plugin / inventory form. Every legacy inflow
is normalized here into `ResolvedPlatform` / `ResolvedCommand`, so the shell,
tests and new consumers see one semantics regardless of authoring form. (The
docs generator still reads the legacy yaml via ``tasks.render_template`` until
it moves to this representation in PR-3 — D9.)

The normalization faithfully replicates v2 render semantics — that fidelity
is exactly what the migration oracle (b') verifies (v2 frozen-replica
projection vs adapter projection, #264 / Decision 3). The file-loader half of
this adapter is removed in PR-3; the normalization core stays until the
inventory commands path is reworked in #266 (Decision 9).

Mode synthesis (#264 / M2): v2 declares three prompt templates
(``initial_prompt`` / ``enable_prompt`` / ``config_prompt``); the adapter maps
them to the canonical modes ``user`` / ``enable`` / ``config`` and reverse-maps
each command's ``prompt`` string back to the mode name(s) it is valid in. The
reverse lookup is exact because every shipped prompt renders to one of the
three canonical strings (measured 100%, #264 Background).
"""

import logging

from simnos.core.resolved_command import (
    NO_OUTPUT,
    ModeDef,
    ResolvedCommand,
    ResolvedOutput,
    ResolvedPlatform,
    compile_template,
    format_template_to_jinja,
)

log = logging.getLogger(__name__)

# Initial mode every synthesized platform starts in (#264 / M2).
INITIAL_MODE = "user"

# Base prompt used only to build the prompt -> mode reverse map. Any value
# works as long as distinct mode templates render distinctly; an unusual
# sentinel avoids accidental collision with literal prompt text.
_REVERSE_SENTINEL = "\x00simnos-base-prompt\x00"


def reverse_map_from_modes(modes: dict[str, ModeDef]) -> dict[str, str]:
    """Build a rendered-prompt -> mode-name reverse lookup from mode defs.

    Keys are each mode prompt rendered at the internal sentinel base prompt;
    values are mode names. Two modes rendering to the same prompt string is an
    ambiguity the reverse lookup cannot resolve -> raises (measured 0 in
    shipped data, guarded for future/external data). Shared by `synthesize_modes`
    (legacy 3-prompt inflow) and the shell's A3 path, where the modes come from
    a `ResolvedPlatform` but inventory/BASIC commands still arrive in legacy form
    and need the same prompt->mode reverse lookup (#264 / D6).
    """
    reverse_map: dict[str, str] = {}
    for mode_name, mode in modes.items():
        rendered = mode.render_prompt(_REVERSE_SENTINEL)
        if rendered in reverse_map:
            raise ValueError(
                f"ambiguous prompt->mode mapping: modes {reverse_map[rendered]!r} and "
                f"{mode_name!r} both render to {rendered!r}; cannot reverse-map command prompts"
            )
        reverse_map[rendered] = mode_name
    return reverse_map


def synthesize_modes(
    initial_prompt: str,
    enable_prompt: str | None,
    config_prompt: str | None,
) -> tuple[dict[str, ModeDef], str, dict[str, str]]:
    """Build the mode map + initial mode + prompt->mode reverse lookup.

    Returns ``(modes, initial_mode, reverse_map)``. v2 declares three prompt
    templates; they map to the canonical modes ``user`` / ``enable`` / ``config``
    in shell order. Undefined enable/config prompts produce no such mode.
    """
    sources: tuple[tuple[str, str | None], ...] = (
        ("user", initial_prompt),
        ("enable", enable_prompt),
        ("config", config_prompt),
    )
    modes: dict[str, ModeDef] = {}
    for mode_name, source in sources:
        if source is None:
            continue
        jinja_source, _ = format_template_to_jinja(source)
        template, _ = compile_template(jinja_source)
        modes[mode_name] = ModeDef(name=mode_name, prompt_template=template)
    return modes, INITIAL_MODE, reverse_map_from_modes(modes)


def _prompt_list(prompt) -> list[str]:
    """Normalize a legacy ``prompt`` value (str | list | None) to a list."""
    if prompt is None:
        return []
    if isinstance(prompt, str):
        return [prompt]
    return list(prompt)


def _lookup_mode(prompt_template: str, reverse_map: dict[str, str], *, where: str) -> str:
    """Reverse-map one v2 prompt template string to a mode name (loud on miss).

    Command prompts render via `str.format` (the v2 mechanism) while the
    `reverse_map` keys were built by rendering the mode templates with jinja2;
    the two are equivalent for these templates (verified by the converter,
    `format_template_to_jinja`), so the lookup matches.

    A malformed / unknown-field prompt (e.g. inventory data with
    ``{hostname}``) is validated through that same converter, so it fails with
    a context-tagged ``ValueError`` instead of a bare ``KeyError`` escaping
    from ``str.format`` — symmetric with the output loud boundary (1st round
    claude #2 / gemini #4).
    """
    try:
        format_template_to_jinja(prompt_template)
    except ValueError as e:
        raise ValueError(f"cannot map {where} {prompt_template!r} to a mode: {e}") from e
    rendered = prompt_template.format(base_prompt=_REVERSE_SENTINEL)
    mode = reverse_map.get(rendered)
    if mode is None:
        raise ValueError(
            f"cannot map {where} {prompt_template!r} to a mode (known modes render to {sorted(reverse_map)!r})"
        )
    return mode


def _adapt_output(value, *, where: str) -> ResolvedOutput:
    """Normalize a legacy ``output`` value to a `ResolvedOutput`.

    - None -> none kind
    - callable -> handler kind
    - str -> literal (no `{base_prompt}`) or template (with `{base_prompt}`),
      with v2 ``{{``/``}}`` brace escapes unescaped (#264 / D6 item 2).
    """
    if value is None:
        return NO_OUTPUT
    if callable(value):
        return ResolvedOutput(kind="handler", handler=value)
    if not isinstance(value, str):
        # v2 never produced non-str/non-callable static output; loud so a
        # malformed inflow surfaces at load instead of via str(value) on wire.
        raise ValueError(f"{where}: unsupported output type {type(value).__name__}")
    jinja_source, has_field = format_template_to_jinja(value)
    if not has_field:
        # No render needed; `str.format` on a field-free template collapses
        # ``{{`` -> ``{`` and ``}}`` -> ``}`` — exactly the unescape the literal
        # wire text needs.
        return ResolvedOutput(kind="literal", text=value.format())
    template, required = compile_template(jinja_source)
    return ResolvedOutput(kind="template", template=template, required_vars=required)


def _resolve_alias(name: str, entry: dict, commands: dict) -> dict | None:
    """Replicate v2's single-level alias field-merge (#264 / D6).

    v2 `_resolve_command` merged ``{**commands[target], **entry}`` (the alias
    entry's own keys win) one level deep. A missing target degrades to None —
    the same lenient unknown-command path as v2 (the dispatch then answers
    with ``_default_``); shipped data has no missing targets.
    """
    target_name = entry["alias"]
    target = commands.get(target_name)
    if target is None:
        log.warning("command %r aliases missing target %r; dropping (treated as unknown)", name, target_name)
        return None
    return {**target, **entry}


def adapt_commands(commands: dict, reverse_map: dict[str, str]) -> dict[str, ResolvedCommand]:
    """Normalize a merged legacy command dict to `ResolvedCommand` objects.

    `commands` is the already-merged view (BASIC + nos + inventory), so alias
    targets resolve within it. The prompt->mode reverse lookup uses
    `reverse_map` from `synthesize_modes`.
    """
    resolved: dict[str, ResolvedCommand] = {}
    for name, entry in commands.items():
        if not isinstance(entry, dict):
            raise ValueError(f"command {name!r}: expected a mapping, got {type(entry).__name__}")
        if "alias" in entry:
            merged = _resolve_alias(name, entry, commands)
            if merged is None:
                continue
            # The merge carries the target's dispatch fields (output / modes /
            # transition), but `help` stays the alias entry's own: v2 `do_help`
            # lists the raw (unmerged) entry, so an alias shows its own help —
            # usually absent, i.e. blank — not the target's (#264 / D6).
            merged["help"] = entry.get("help", "")
            entry = merged
        resolved[name] = _adapt_command(name, entry, reverse_map)
    return resolved


def _adapt_command(name: str, entry: dict, reverse_map: dict[str, str]) -> ResolvedCommand:
    """Normalize a single (alias-merged) legacy command entry."""
    # `_default_` is the unconditional fallback: v2 never matches its prompt
    # (#264 / D5), so its mode set is empty (= valid in every mode) and any
    # authored prompt is dropped.
    is_default = name == "_default_"
    if is_default:
        modes: frozenset[str] = frozenset()
    else:
        raw_prompt = entry.get("prompt")
        # An explicit empty list is rejected loudly: v2 `_check_prompt([])` was
        # always False (command unreachable), but an empty mode set here means
        # "all modes" — the opposite. "All modes" is expressed by omitting
        # prompt, so `[]` is an authoring error, symmetric with Decision 7's
        # `mode: []` reject (2nd round claude #3).
        if isinstance(raw_prompt, list) and not raw_prompt:
            raise ValueError(
                f"command {name!r}: explicit empty prompt list [] is rejected — "
                "omit prompt to mean all modes (#264 / Decision 7)"
            )
        modes = frozenset(
            _lookup_mode(p, reverse_map, where=f"command {name!r} prompt") for p in _prompt_list(raw_prompt)
        )

    new_prompt = entry.get("new_prompt")
    if new_prompt is None or is_default:
        new_mode = None
    else:
        new_mode = _lookup_mode(new_prompt, reverse_map, where=f"command {name!r} new_prompt")

    # v2 keeps the served capture in `output` and any alternates in the
    # data-only `output_variants`. Project that onto the canonical contract
    # (ResolvedCommand docstring): single-output commands carry no variants;
    # multi-capture commands list every capture with `output` mirrored at
    # `variants[0]` (variant_1) and the alternates as variant_2.. (D3, D7).
    output = _adapt_output(entry.get("output"), where=f"command {name!r}")
    alternates = entry.get("output_variants") or []
    if alternates:
        variants: tuple[tuple[str, ResolvedOutput], ...] = (
            ("variant_1", output),
            *(
                (f"variant_{i + 2}", _adapt_output(v, where=f"command {name!r} variant {i + 2}"))
                for i, v in enumerate(alternates)
            ),
        )
    else:
        variants = ()

    return ResolvedCommand(
        name=name,
        modes=modes,
        new_mode=new_mode,
        output=output,
        variants=variants,
        help=entry.get("help", ""),
        exit=bool(entry.get("exit")),
        type="simnos",
        source=None,
    )


def adapt_legacy_commands(
    initial_prompt: str,
    enable_prompt: str | None,
    config_prompt: str | None,
    commands: dict,
) -> ResolvedPlatform:
    """Top-level: synthesize modes + normalize a merged legacy command dict."""
    modes, initial_mode, reverse_map = synthesize_modes(initial_prompt, enable_prompt, config_prompt)
    resolved_commands = adapt_commands(commands, reverse_map)
    return ResolvedPlatform(modes=modes, initial_mode=initial_mode, commands=resolved_commands)
