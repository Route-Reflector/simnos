"""User overlay loader (#286 / P1-2a — custom data layering).

Resolves user-local output overrides (``.txt`` / ``.j2`` files placed under
``<sys_config.data_dir>/<registry-key>/``) against a base A3 platform, producing
a ``{command: ResolvedCommand}`` dict the shell merges between the py-handler
inflow and the inventory commands (precedence, design Decision 14). Its main use
is "drop a production capture ``.txt`` and the command's wire output is replaced";
it also adds commands the package does not ship.

Unlike :func:`simnos.core.platform_loader.load_platform_dir`, the overlay has no
``platform.yaml`` / modes of its own — it is *base-aware*:

- a command found in the base is an **output-only override** — only its output
  (and ``variants``) is swapped; every other field (modes / new_mode / help /
  exit / type) is inherited from the base command (design Decision 7);
- a command absent from the base is a **new command** — all-modes
  (``modes=frozenset()``), ``type="custom"``, no transition.

Only ``.txt`` (literal wire text) and ``.j2`` (jinja2 template) are read; yaml
full-replacement is deferred to a future issue. A facts-bearing ``.j2`` pulls
its render values from an adjacent sidecar ``<stem>.json`` (#287 / Layer 1):
``_resolve_output_file`` validates at build time, so a template that needs a
value the sidecar does not supply fails loud here instead of at connect time
(#286 rejected every facts-bearing ``.j2`` because it had no injection path;
#287 opens that path).

The output-file *channel* is decided by extension (``.txt``->literal /
``.j2``->template), unlike the A3 loader where the authoring yaml field decides
it (the overlay has no yaml). The extension is translated to ``as_template`` and
the rest of the read is the part loader's :func:`_resolve_output_file`.
"""

from dataclasses import replace
import logging
import os

from simnos.core.platform_loader import _resolve_output_file
from simnos.core.resolved_command import ResolvedCommand, ResolvedOutput, ResolvedPlatform
from simnos.core.utils import _is_unsafe_bare_ref

log = logging.getLogger(__name__)

# Output file extensions the overlay accepts; the channel is keyed off these
# (`.txt` -> literal, `.j2` -> template). yaml is out of scope for #286.
_ALLOWED_EXTS: tuple[str, ...] = (".txt", ".j2")


def resolve_overlay(
    overlay_root: str,
    base: ResolvedPlatform,
    *,
    override_commands: str | list[str] | dict[str, str],
) -> dict[str, ResolvedCommand]:
    """Resolve overlay output files against `base` into merge-ready commands.

    :param overlay_root: the platform's overlay dir (``<data_dir>/<registry-key>/``);
        the caller (Host) has already verified it exists.
    :param base: the A3 platform whose commands an override inherits from. A
        command absent here becomes a new ``type="custom"`` command.
    :param override_commands: which commands to pull (``all`` / list / map — see
        :class:`~simnos.core.pydantic_models.ModelOverlay`).
    :raises ValueError: a listed/mapped command with no file, a command that
        resolves to more than one file (`.txt` + `.j2`), an unsafe file ref, or
        a ``.j2`` that needs host facts #286 cannot inject.
    """
    resolved: dict[str, ResolvedCommand] = {}
    for command, filename in _select_overlay_files(overlay_root, override_commands):
        output = _read_overlay_output(overlay_root, filename, command)
        resolved[command] = _build_overlay_command(command, filename, output, base.commands.get(command))
    return resolved


def _select_overlay_files(
    overlay_root: str, override_commands: str | list[str] | dict[str, str]
) -> list[tuple[str, str]]:
    """Resolve `override_commands` to an ordered list of ``(command, filename)``."""
    if override_commands == "all":
        return _select_all(overlay_root)
    if isinstance(override_commands, dict):
        return _select_map(overlay_root, override_commands)
    if isinstance(override_commands, list):
        return _select_list(overlay_root, override_commands)
    # The schema validates the type; this guards a direct (non-inventory) caller.
    raise ValueError(f"override_commands must be 'all', a list, or a map, got {type(override_commands).__name__}")


def _select_all(overlay_root: str) -> list[tuple[str, str]]:
    """Apply every ``.txt`` / ``.j2`` in the dir; a command->2-file clash is loud."""
    by_command: dict[str, list[str]] = {}
    for filename in sorted(os.listdir(overlay_root)):
        if not filename.endswith(_ALLOWED_EXTS) or not os.path.isfile(os.path.join(overlay_root, filename)):
            continue
        by_command.setdefault(_decode_command_name(filename), []).append(filename)
    pairs: list[tuple[str, str]] = []
    for command, files in sorted(by_command.items()):
        if len(files) > 1:
            raise ValueError(
                f"overlay command {command!r} resolves to multiple files {sorted(files)} in {overlay_root!r}; "
                "a command must map to exactly one .txt or .j2 (remove the duplicate)"
            )
        pairs.append((command, files[0]))
    return pairs


def _select_list(overlay_root: str, commands: list[str]) -> list[tuple[str, str]]:
    """Apply each listed command by its default-name file (`show version` -> `show_version.txt`)."""
    pairs: list[tuple[str, str]] = []
    for command in commands:
        stem = _encode_stem(command)
        # Validate the generated filename before touching the filesystem: a list
        # entry like `../../etc/hostname` or `/tmp/leak` encodes to a non-bare ref
        # that `os.path.join` would resolve outside the overlay root. Same
        # root-confinement invariant the map form enforces (Decision 10c) — only
        # `_select_map` validated it before (3rd round codex#1 / claude#1).
        candidates: list[str] = []
        for ext in _ALLOWED_EXTS:
            ref = f"{stem}{ext}"
            _validate_overlay_ref(ref, where=f"overlay command {command!r}")
            if os.path.isfile(os.path.join(overlay_root, ref)):
                candidates.append(ref)
        if not candidates:
            raise ValueError(
                f"overlay command {command!r} is listed in override_commands but no "
                f"{stem}.txt / {stem}.j2 was found in {overlay_root!r}"
            )
        if len(candidates) > 1:
            raise ValueError(
                f"overlay command {command!r} resolves to multiple files {sorted(candidates)} in {overlay_root!r}; "
                "keep only one of .txt / .j2"
            )
        pairs.append((command, candidates[0]))
    return pairs


def _select_map(overlay_root: str, mapping: dict[str, str]) -> list[tuple[str, str]]:
    """Apply each command via its explicitly named file (per-host capture choice, R11)."""
    pairs: list[tuple[str, str]] = []
    for command, ref in mapping.items():
        _validate_overlay_ref(ref, where=f"overlay command {command!r}")
        if not os.path.isfile(os.path.join(overlay_root, ref)):
            raise ValueError(f"overlay command {command!r} maps to {ref!r}, which does not exist in {overlay_root!r}")
        pairs.append((command, ref))
    return pairs


def _decode_command_name(filename: str) -> str:
    """``show_version.txt`` -> ``show version`` (ntc raw-data naming, case-sensitive)."""
    return filename.rsplit(".", 1)[0].replace("_", " ")


def _encode_stem(command: str) -> str:
    """``show version`` -> ``show_version`` (default-name stem for a listed command)."""
    return command.replace(" ", "_")


def _validate_overlay_ref(ref: str, *, where: str) -> None:
    """Reject an overlay file ref that escapes the overlay dir or is not `.txt` / `.j2`.

    Called for both the map form (explicit ref) and the list form (the
    command-derived ``stem.ext``). The overlay map/list bypass the A3 authoring
    schema (which rejects path traversal at its boundary), so the loader enforces
    the same invariant here: a bare filename, no separators / ``..``, not absolute,
    ``.txt`` / ``.j2`` only (design Decision 10c).
    """
    if _is_unsafe_bare_ref(ref):
        raise ValueError(f"{where}: overlay file reference {ref!r} must be a bare filename in the overlay directory")
    if not ref.endswith(_ALLOWED_EXTS):
        raise ValueError(f"{where}: overlay file {ref!r} must end with .txt or .j2")


def _read_overlay_output(overlay_root: str, filename: str, command: str) -> ResolvedOutput:
    """Read one overlay file into a `ResolvedOutput` (#287 / Layer 1).

    Reuses the part loader (`_resolve_output_file`), translating the extension to
    its ``as_template`` channel. For a ``.j2`` the adjacent sidecar
    ``<stem>.json`` supplies render values and `_resolve_output_file` validates
    them at build time: a template needing a value the sidecar does not provide
    fails loud here, not at connect time (#287 / D4, D5). #286 rejected every
    facts-bearing ``.j2`` outright (no injection path); #287 opens that path via
    the sidecar, so the explicit ``required_vars`` rejection is gone — the build
    gate inside `_resolve_output_file` is now the single source of that loud-fail.
    """
    return _resolve_output_file(
        filename,
        overlay_root,
        as_template=filename.endswith(".j2"),
        where=f"overlay command {command!r}",
        command_name=command,
    )


def _build_overlay_command(
    command: str, filename: str, output: ResolvedOutput, base_cmd: ResolvedCommand | None
) -> ResolvedCommand:
    """Build the overridden / new `ResolvedCommand` for one resolved overlay file.

    Base present -> output-only override: swap ``output`` / ``variants`` only,
    inherit every other field, and record the overlay file under ``source`` so the
    override is traceable. Base absent -> a new all-modes ``type="custom"`` command.
    """
    if base_cmd is not None:
        if base_cmd.variants:
            # A multi-capture base loses its variant pool to the single override
            # output, so the command drops out of #287 random selection. Make the
            # narrowing observable rather than a silent surprise (Decision 11).
            log.info(
                "overlay command %r drops %d base variant(s) via output-only override "
                "(no longer eligible for #287 random selection)",
                command,
                len(base_cmd.variants),
            )
        source = dict(base_cmd.source or {})
        source["overlay_file"] = filename
        return replace(base_cmd, output=output, variants=(), source=source)
    return ResolvedCommand(
        name=command,
        modes=frozenset(),  # empty = valid in every mode (no mode info in a bare file)
        new_mode=None,
        output=output,
        variants=(),
        help="",
        exit=False,
        type="custom",
        source={"overlay_file": filename},
    )
