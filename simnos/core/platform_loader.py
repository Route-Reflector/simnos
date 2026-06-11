"""A3 platform directory loader (#264 / P1-1 D6).

Reads the new on-disk form — ``platforms/<nos>/platform.yaml`` +
``commands/*.yaml`` + adjacent output files — validates it through the
authoring pydantic models (:mod:`simnos.core.pydantic_models`), and produces a
:class:`~simnos.core.resolved_command.ResolvedPlatform` directly (no legacy
intermediate, unlike :mod:`simnos.core.command_adapter`). The shell, docs gen
and tests then consume the one runtime representation regardless of which form
the data was authored in (D4).

All load-time validation that needs the filesystem or jinja2 lives here:
output-file existence, ``.j2`` syntax, mode-name existence, and prompt-template
render (#264 / Decision 7). Structural validation (types, output-channel
exclusivity, alias purity, path shape) is done by the pydantic models at the
boundary just above.
"""

from dataclasses import replace
import glob
import os

from jinja2 import TemplateSyntaxError
import yaml

from simnos.core.pydantic_models import ModelCommandAuthoring, ModelPlatformMeta
from simnos.core.resolved_command import (
    NO_OUTPUT,
    ModeDef,
    ResolvedCommand,
    ResolvedOutput,
    ResolvedPlatform,
    compile_template,
)

PLATFORM_META_FILENAME = "platform.yaml"
COMMANDS_SUBDIR = "commands"


def load_platform_dir(path: str) -> ResolvedPlatform:
    """Load an A3 platform directory into a `ResolvedPlatform`.

    :param path: directory holding ``platform.yaml`` and ``commands/``
    :raises ValueError: on any schema, reference, or render violation — the
        loud load-time boundary that replaces v2's silent fallbacks (#264 / D5)
    """
    meta = _load_platform_meta(os.path.join(path, PLATFORM_META_FILENAME))
    modes = _build_modes(meta)
    commands_dir = os.path.join(path, COMMANDS_SUBDIR)
    authored = _load_command_files(commands_dir)
    commands = _resolve_commands(authored, modes, commands_dir)
    return ResolvedPlatform(modes=modes, initial_mode=meta.initial_mode, commands=commands)


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
            # help (usually blank) — same as the legacy adapter and v2 do_help
            # (#264 / D6, Decision 6).
            resolved[name] = replace(target, name=model.command, help=model.help or "")
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


def _resolve_command(
    model: ModelCommandAuthoring,
    mode_names: frozenset[str],
    commands_dir: str,
    filepath: str,
) -> ResolvedCommand:
    """Resolve one validated authoring model to a `ResolvedCommand`."""
    # `_default_` is the mode-agnostic fallback; the schema already forbids a
    # `mode` on it, so its mode set is empty (= every mode). An omitted `mode`
    # is likewise the empty set ("all modes", #264 / D5).
    if model.command == "_default_" or model.mode is None:
        cmd_modes: frozenset[str] = frozenset()
    else:
        unknown = [m for m in model.mode if m not in mode_names]
        if unknown:
            raise ValueError(f"command {model.command!r}: mode(s) {unknown} not in platform modes {sorted(mode_names)}")
        cmd_modes = frozenset(model.mode)

    if model.new_mode is not None and model.new_mode not in mode_names:
        raise ValueError(
            f"command {model.command!r}: new_mode {model.new_mode!r} not in platform modes {sorted(mode_names)}"
        )

    if model.variants is not None:
        variants = tuple(
            (
                v.name,
                _resolve_output_file(
                    v.output, commands_dir, as_template=False, where=f"command {model.command!r} variant {v.name!r}"
                ),
            )
            for v in model.variants
        )
        # variants[0] is the served primary (deterministic default — D3).
        output = variants[0][1]
    elif model.output is not None:
        output = _resolve_output_file(model.output, commands_dir, as_template=False, where=f"command {model.command!r}")
        variants = ()
    elif model.output_template is not None:
        output = _resolve_output_file(
            model.output_template, commands_dir, as_template=True, where=f"command {model.command!r}"
        )
        variants = ()
    else:
        output = NO_OUTPUT
        variants = ()

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
    )


def _resolve_output_file(ref: str, commands_dir: str, *, as_template: bool, where: str) -> ResolvedOutput:
    """Read an adjacent output file into a `ResolvedOutput`.

    The authoring *field* decides the channel, not the extension: ``output`` /
    variants are read verbatim (literal wire text), ``output_template`` is
    compiled as jinja2. ``.txt`` / ``.j2`` are a lint-level naming convention,
    not load semantics.
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
        return ResolvedOutput(kind="template", template=template, required_vars=required)
    return ResolvedOutput(kind="literal", text=content)
