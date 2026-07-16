"""A3 platform directory loader (#264 / P1-1 D6).

Reads the on-disk form — ``platforms/<nos>/platform.yaml`` +
``commands/*.yaml`` + adjacent output files — validates it through the
authoring pydantic models (:mod:`simnos.core.pydantic_models`), and produces a
:class:`~simnos.core.resolved_command.ResolvedPlatform` directly. The shell,
docs gen and tests then consume the one runtime representation regardless of
which form the data was authored in (D4).

All load-time validation that needs the filesystem or jinja2 lives here:
output-file existence, ``.j2`` syntax, mode-name existence, and prompt-template
render (#264 / Decision 7). Structural validation (types, output-channel
exclusivity, alias purity, path shape) is done by the pydantic models at the
boundary just above.
"""

from dataclasses import replace
import functools
import glob
import os

from jinja2 import TemplateSyntaxError
import yaml

from simnos.core.pydantic_models import (
    ModelChallenge,
    ModelCommandAuthoring,
    ModelConfirmAction,
    ModelPlatformMeta,
    ModelTransition,
)
from simnos.core.resolved_command import (
    CHALLENGE_RENDER_VARS,
    NO_OUTPUT,
    ConfirmAction,
    ModeDef,
    ResolvedChallenge,
    ResolvedCommand,
    ResolvedOutput,
    ResolvedPlatform,
    Transition,
    compile_challenge_prompt,
    compile_template,
)
from simnos.core.values_loader import resolve_output_file

PLATFORM_META_FILENAME = "platform.yaml"
COMMANDS_SUBDIR = "commands"


@functools.cache
def load_platform_dir(path: str) -> ResolvedPlatform:
    """Load an A3 platform directory into a `ResolvedPlatform`.

    Cached by `path` (#264 / D6): the result is immutable and
    ``configuration_file``-independent (per-host state lives on the `BaseDevice`,
    built separately), so every host / replica of a platform shares one parse
    instead of re-reading platform.yaml + the command files on each
    ``Host.start()``. Consumers MUST treat the result read-only (the shell
    layers it into a fresh dict, never mutating it). The hot-reload path calls
    `load_platform_dir.cache_clear()` so a changed file is re-read; an unbounded
    `functools.cache` is fine at ~50 platforms (an LRU bound is a future option
    if platform count grows — D6).

    :param path: directory holding ``platform.yaml`` and ``commands/``
    :raises ValueError: on any schema, reference, or render violation — the
        loud load-time boundary that replaces v2's silent fallbacks (#264 / D5)
    """
    meta = _load_platform_meta(os.path.join(path, PLATFORM_META_FILENAME))
    modes = _build_modes(meta)
    commands_dir = os.path.join(path, COMMANDS_SUBDIR)
    authored = _load_command_files(commands_dir)
    commands = _resolve_commands(authored, modes, commands_dir)
    # Pass `more_prompt` only when the platform authored one, so the single source
    # of the Cisco-style default ``" --More-- "`` stays on `ResolvedPlatform` (#307).
    paging_kwargs = {"more_prompt": meta.paging.more_prompt} if meta.paging else {}
    return ResolvedPlatform(
        modes=modes, initial_mode=meta.initial_mode, commands=commands, auth=meta.auth, **paging_kwargs
    )


def _read_yaml_mapping(filepath: str) -> dict:
    """Read a YAML file that must contain a top-level mapping."""
    if not os.path.isfile(filepath):
        raise ValueError(f"required file not found: {filepath}")
    with open(filepath, encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"{filepath} does not contain a mapping (got {type(data).__name__})")
    return data


def _load_platform_meta(filepath: str) -> ModelPlatformMeta:
    return ModelPlatformMeta(**_read_yaml_mapping(filepath))


def _build_modes(meta: ModelPlatformMeta) -> dict[str, ModeDef]:
    """Compile each mode's prompt template; only `base_prompt` may appear."""
    modes: dict[str, ModeDef] = {}
    for name, mdef in meta.modes.items():
        try:
            template, required = compile_template(mdef.prompt)
        except TemplateSyntaxError as e:
            raise ValueError(f"mode {name!r} prompt template has a jinja2 syntax error: {e}") from e
        if required:
            # `compile_template` already strips `base_prompt`; anything left is
            # an unknown variable a prompt may not use (host facts are for
            # output templates, not prompts).
            raise ValueError(
                f"mode {name!r} prompt uses unknown variable(s) {sorted(required)}; only base_prompt is allowed"
            )
        modes[name] = ModeDef(name=name, prompt_template=template)
    return modes


def _load_command_files(commands_dir: str) -> dict[str, tuple[ModelCommandAuthoring, str]]:
    """Glob + validate every ``commands/*.yaml``; detect duplicate `command`.

    The `command` field is the SSoT key (Decision 1) — two files declaring the
    same command is a load error, regardless of filename.
    """
    if not os.path.isdir(commands_dir):
        raise ValueError(f"commands directory not found: {commands_dir}")
    authored: dict[str, tuple[ModelCommandAuthoring, str]] = {}
    for filepath in sorted(glob.glob(os.path.join(commands_dir, "*.yaml"))):
        model = ModelCommandAuthoring(**_read_yaml_mapping(filepath))
        if model.command in authored:
            raise ValueError(
                f"duplicate command {model.command!r}: declared in both {authored[model.command][1]} and {filepath}"
            )
        authored[model.command] = (model, filepath)
    return authored


def _resolve_commands(
    authored: dict[str, tuple[ModelCommandAuthoring, str]],
    modes: dict[str, ModeDef],
    commands_dir: str,
) -> dict[str, ResolvedCommand]:
    """Two-pass resolve: real commands first, then aliases against them."""
    mode_names = frozenset(modes)
    resolved: dict[str, ResolvedCommand] = {}
    for name, (model, filepath) in authored.items():
        if model.alias is None:
            resolved[name] = _resolve_command(model, mode_names, commands_dir, filepath)
    for name, (model, _filepath) in authored.items():
        if model.alias is not None:
            target = _follow_alias(name, authored, resolved)
            # An alias carries the target's dispatch fields but keeps its own
            # help (usually blank) (#264 / D6, Decision 6).
            aliased = replace(target, name=model.command, help=model.help or "")
            # A `mode:` override lets an alias run in a different mode set than
            # its target (e.g. arista `do show ip int brief`: target is
            # user/enable, the alias is config-only) — the one dispatch field an
            # alias may re-author (#317 / P-1). Validate the names and re-check
            # any inherited `transitions` against the narrowed modes.
            if model.mode is not None:
                new_modes = resolve_modes(model.command, model.mode, mode_names)
                if aliased.transitions is not None:
                    stray = sorted(k for k in aliased.transitions if k not in new_modes)
                    if stray:
                        raise ValueError(
                            f"command {model.command!r}: alias `mode:` override to {sorted(new_modes)} drops "
                            f"transition mode(s) {stray} inherited from target {model.alias!r} (dead entry)"
                        )
                aliased = replace(aliased, modes=new_modes)
            resolved[name] = aliased
    return resolved


def _follow_alias(
    start: str,
    authored: dict[str, tuple[ModelCommandAuthoring, str]],
    resolved: dict[str, ResolvedCommand],
) -> ResolvedCommand:
    """Follow an alias chain to its real target (loud on cycle / unknown)."""
    seen = {start}
    current = authored[start][0].alias
    while True:
        if current in resolved:
            return resolved[current]
        if current not in authored:
            raise ValueError(f"command {start!r} aliases unknown target {current!r}")
        if current in seen:
            raise ValueError(f"alias cycle detected starting at {start!r} (revisits {current!r})")
        seen.add(current)
        current = authored[current][0].alias


def _require_platform_mode(new_mode: str | None, mode_names: frozenset[str], label: str) -> None:
    """Raise the shared loud check if `new_mode` is set but not a platform mode.

    `label` is the fully-formed message head (e.g. ``command 'x': challenge.success.new_mode 'y'``);
    only the common ``not in platform modes {..}`` tail is factored, so each transition
    source (static `new_mode`, `transitions` map, challenge `success` / confirm action)
    keeps its own wording.
    """
    if new_mode is not None and new_mode not in mode_names:
        raise ValueError(f"{label} not in platform modes {sorted(mode_names)}")


def _resolve_command(
    model: ModelCommandAuthoring,
    mode_names: frozenset[str],
    commands_dir: str,
    filepath: str,
) -> ResolvedCommand:
    """Resolve one validated authoring model to a `ResolvedCommand`."""
    cmd_modes = resolve_modes(model.command, model.mode, mode_names)

    _require_platform_mode(model.new_mode, mode_names, f"command {model.command!r}: new_mode {model.new_mode!r}")

    if model.variants is not None:
        variants = tuple(
            (
                v.name,
                resolve_output_file(
                    v.output,
                    commands_dir,
                    as_template=False,
                    where=f"command {model.command!r} variant {v.name!r}",
                    command_name=model.command,
                ),
            )
            for v in model.variants
        )
        # variants[0] is the served primary (deterministic default — D3).
        output = variants[0][1]
    elif model.output is not None:
        output = resolve_output_file(
            model.output,
            commands_dir,
            as_template=False,
            where=f"command {model.command!r}",
            command_name=model.command,
        )
        variants = ()
    elif model.output_template is not None:
        output = resolve_output_file(
            model.output_template,
            commands_dir,
            as_template=True,
            where=f"command {model.command!r}",
            command_name=model.command,
        )
        variants = ()
    elif model.handler is not None:
        # The handler callable is bound at merge time from the platform's py
        # handler namespace (#317 / P-1, 案D); the loader stays pure and only
        # records the reference name (schema-validated as an identifier).
        output = ResolvedOutput(kind="handler", handler_ref=model.handler)
        variants = ()
    else:
        output = NO_OUTPUT
        variants = ()

    challenge = (
        _resolve_challenge(model.challenge, cmd_modes, mode_names, model.command)
        if model.challenge is not None
        else None
    )

    return ResolvedCommand(
        name=model.command,
        modes=cmd_modes,
        new_mode=model.new_mode,
        output=output,
        variants=variants,
        help=model.help or "",
        exit=bool(model.exit),
        # `type` is required for a real (non-alias) command (schema-enforced).
        type=model.type or "simnos",
        source=model.source,
        disables_paging=bool(model.disables_paging),
        transitions=resolve_transitions(model.command, model.transitions, cmd_modes, mode_names),
        challenge=challenge,
    )


# Non-empty sentinel for the challenge-prompt dry-render (mirrors
# `values_loader._DRY_SENTINEL`): a value both `base_prompt` and `username` take
# so a template referencing either renders without an undefined at build time.
_CHALLENGE_DRY_SENTINEL = "x"


def _resolve_challenge_prompt(source: str, command_name: str) -> ResolvedOutput:
    """Compile + build-time validate a challenge prompt into a `ResolvedOutput` (#338 / §2).

    A challenge prompt may reference `base_prompt` / `username` (only). Unknown
    variables, a jinja syntax error, a render failure, or a rendered result that
    spans multiple lines all fail loudly here (fail at startup, #287-style) rather
    than at connect time. A prompt with no jinja markers is stored verbatim as a
    literal (no runtime render); anything else is a template the shell renders
    with `base_prompt` + `username`.
    """
    try:
        template, unknown = compile_challenge_prompt(source)
    except TemplateSyntaxError as e:
        raise ValueError(f"command {command_name!r}: challenge prompt has a jinja2 syntax error: {e}") from e
    if unknown:
        raise ValueError(
            f"command {command_name!r}: challenge prompt uses unknown variable(s) {sorted(unknown)}; "
            f"only {sorted(CHALLENGE_RENDER_VARS)} are allowed"
        )
    try:
        rendered = template.render(base_prompt=_CHALLENGE_DRY_SENTINEL, username=_CHALLENGE_DRY_SENTINEL)
    except Exception as e:
        raise ValueError(f"command {command_name!r}: challenge prompt failed dry-render: {e}") from e
    if "\n" in rendered or "\r" in rendered:
        raise ValueError(f"command {command_name!r}: challenge prompt renders to multiple lines; keep it single-line")
    if "{{" not in source and "{%" not in source and "{#" not in source:
        return ResolvedOutput(kind="literal", text=source)
    return ResolvedOutput(kind="template", template=template, required_vars=frozenset())


def _resolve_challenge(
    model: ModelChallenge, cmd_modes: frozenset[str], mode_names: frozenset[str], command_name: str
) -> ResolvedChallenge:
    """Resolve a validated `challenge:` block to a `ResolvedChallenge` (#338 / §2).

    `challenge.mode` is normalized to the effective firing set: the authored
    modes (checked ⊆ the command's own modes), or the command's effective modes
    when omitted — an all-modes command (empty `cmd_modes`) expands to the full
    platform mode set, the same `cmd_modes or mode_names` rule `resolve_transitions`
    uses, so a runtime `current_mode in modes` check never silently misses. Every
    `new_mode` (password `success` or confirm action) is validated against the
    platform modes, the same loud boundary the static `new_mode` uses.
    """
    effective_cmd_modes = cmd_modes or mode_names
    if model.mode is not None:
        unknown = sorted(m for m in model.mode if m not in effective_cmd_modes)
        if unknown:
            raise ValueError(
                f"command {command_name!r}: challenge.mode {unknown} not in the command's modes "
                f"{sorted(effective_cmd_modes)}"
            )
        challenge_modes = frozenset(model.mode)
    else:
        challenge_modes = effective_cmd_modes
    prompt = _resolve_challenge_prompt(model.prompt, command_name)
    if model.kind == "password":
        # The kind-specific validator guarantees `success` here (and `on` below);
        # assert to narrow the `... | None` unions for the type checker.
        st = model.success
        assert st is not None  # noqa: S101 — password kind: the validator guarantees `success`
        _require_platform_mode(
            st.new_mode, mode_names, f"command {command_name!r}: challenge.success.new_mode {st.new_mode!r}"
        )
        return ResolvedChallenge(
            kind=model.kind,
            prompt=prompt,
            modes=challenge_modes,
            auth=model.auth,
            success=Transition(new_mode=st.new_mode, exit=bool(st.exit)),
            failure_output=model.failure_output,
        )
    # confirm: resolve every `on` entry (and `default`) to a ConfirmAction.
    assert model.on is not None  # noqa: S101 — confirm kind: the validator guarantees a non-empty `on`
    return ResolvedChallenge(
        kind=model.kind,
        prompt=prompt,
        modes=challenge_modes,
        on={
            key: _resolve_confirm_action(action, mode_names, command_name, f"on[{key!r}]")
            for key, action in model.on.items()
        },
        default=(
            _resolve_confirm_action(model.default, mode_names, command_name, "default")
            if model.default is not None
            else None
        ),
    )


def _resolve_confirm_action(
    model: ModelConfirmAction, mode_names: frozenset[str], command_name: str, entry: str
) -> ConfirmAction:
    """Resolve one confirm `on:` entry / `default:` to a `ConfirmAction` (#338 / §3).

    `new_mode` is validated against the platform modes, the same loud boundary the
    password `success.new_mode` and static `new_mode` use. `entry` names the map
    slot (`on[<key>]` / `default`) so a multi-entry confirm points the author at
    the offending action (1st round claude#5).
    """
    _require_platform_mode(
        model.new_mode,
        mode_names,
        f"command {command_name!r}: challenge confirm action {entry} new_mode {model.new_mode!r}",
    )
    return ConfirmAction(new_mode=model.new_mode, exit=bool(model.exit), output=model.output)


def resolve_modes(
    command: str,
    mode: list[str] | None,
    mode_names: frozenset[str],
    *,
    where: str = "command",
) -> frozenset[str]:
    """Validate a command's ``mode:`` list against the platform modes.

    ``None`` resolves to the empty set — "valid in every mode" (an omitted
    ``mode``, and ``_default_``, whose ``mode`` the schema forbids so it always
    arrives as None; #264 / D5). Shared by the loader (real commands + the
    alias ``mode:`` override) and the merge's inventory-command normalization
    (#317 / P-3) — the inflows speak one dialect, so the mode check is one
    loud boundary; ``where`` tags the error with the calling inflow (mirrors
    `resolve_transitions`).
    """
    if mode is None:
        return frozenset()
    unknown = [m for m in mode if m not in mode_names]
    if unknown:
        raise ValueError(f"{where} {command!r}: mode(s) {unknown} not in platform modes {sorted(mode_names)}")
    return frozenset(mode)


def resolve_transitions(
    command: str,
    transitions: dict[str, ModelTransition] | None,
    cmd_modes: frozenset[str],
    mode_names: frozenset[str],
    *,
    where: str = "command",
) -> dict[str, Transition] | None:
    """Validate + build a command's mode-conditional transition map (#317 / P-1).

    Each key must be one of the command's own modes (`cmd_modes`, or every
    platform mode when `mode` was omitted) — a key outside them would never fire
    (dead entry, an authoring error). Each `new_mode` value must be a real
    platform mode, the same loud boundary the static `new_mode` uses. Returns
    None when the command authored no `transitions` (the common case).

    Shared with the merge's inventory-command normalization (#317 / P-3), which
    speaks the same `transitions` dialect against the merged platform's modes;
    `where` tags the error with the calling inflow.
    """
    if transitions is None:
        return None
    # Empty `cmd_modes` means "all modes" (mode omitted / `_default_`); the schema
    # already forbids `transitions` on `_default_`, so a command reaching here with
    # empty modes is a genuine all-modes command whose keys may be any platform mode.
    effective_modes = cmd_modes or mode_names
    resolved: dict[str, Transition] = {}
    for key, mt in transitions.items():
        if key not in effective_modes:
            raise ValueError(
                f"{where} {command!r}: transitions key {key!r} is not one of the command's modes "
                f"{sorted(effective_modes)} — it would never fire (dead entry)"
            )
        _require_platform_mode(
            mt.new_mode, mode_names, f"{where} {command!r}: transitions[{key!r}].new_mode {mt.new_mode!r}"
        )
        resolved[key] = Transition(new_mode=mt.new_mode, exit=bool(mt.exit))
    return resolved
