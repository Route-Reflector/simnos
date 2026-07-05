"""Runtime command representation (#264 / P1-1 D4).

The shell, docs gen and tests consume one normalized representation —
`ResolvedCommand` / `ResolvedOutput` — regardless of the authoring inflow.
The A3 loader (:mod:`simnos.core.platform_loader`) produces these dataclasses
directly, and so does the merge for the inventory inflow (A3-dialect schema,
#317 P-3); the legacy py-dict adapter, the last other inflow, was removed in
#317 P-4.

The representation is a frozen dataclass, not a pydantic model: every load
path validates at its boundary, so runtime re-validation is unnecessary and
a dataclass can hold a compiled ``jinja2.Template`` / a handler callable
directly (#264 / D4).
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Literal

from jinja2 import Environment, StrictUndefined, Template
from jinja2 import meta as jinja_meta

if TYPE_CHECKING:
    from simnos.core.command_contract import CommandHandler

# The single known render variable. Extracted template variables minus this
# set become `ResolvedOutput.required_vars` — the host-facts to check at
# start time (#265). `base_prompt` is always supplied by the shell, so it is
# never a "missing var" (#264 / D4, 2nd round gemini #4).
KNOWN_RENDER_VARS: frozenset[str] = frozenset({"base_prompt"})

# The render variables a challenge prompt (#338) may reference. A superset of
# `KNOWN_RENDER_VARS` by `username` — a sub-prompt like `[sudo] password for
# {{ username }}: ` needs the connected user's name. Kept separate from the
# output render vars so the normal-output allow-set (`KNOWN_RENDER_VARS`) is not
# widened: `username` is supplied by the shell only on the challenge path, never
# as a sidecar-json fact (#338 / §2, 1st round codex#6 / claude#4).
CHALLENGE_RENDER_VARS: frozenset[str] = frozenset({"base_prompt", "username"})

# Jinja2 environment for output/prompt templates. `StrictUndefined` makes an
# undefined fact loud at render time instead of rendering an empty string
# (#264 / D5, Decision 7). No trim/lstrip: output whitespace is significant.
# `keep_trailing_newline` keeps the final newline jinja2 would otherwise strip
# — needed for the hand-written ``.j2`` templates of A3 authoring (#264 PR-2).
_TEMPLATE_ENV = Environment(
    undefined=StrictUndefined,
    autoescape=False,  # noqa: S701 — output is CLI text, not HTML
    keep_trailing_newline=True,
)


def _deep_freeze(value: Any) -> Any:
    """Recursively convert a json-ish value into a read-only structure (#287).

    A shallow ``MappingProxyType`` only protects the outer dict; a nested
    ``parsed`` list (or a row dict inside it) stays mutable, so a template like
    ``{{ parsed.pop() }}`` could mutate the shared, cached value and poison every
    other session that renders the same command (1st round codex#1 / gemini#1).
    Freeze the whole tree: ``Mapping`` -> ``MappingProxyType``, ``list``/``tuple``
    -> ``tuple``, scalars unchanged. Render only reads, so frozen types are
    transparent to jinja (``parsed[0].version`` / ``{% for row in parsed %}`` work
    on a tuple of ``MappingProxyType`` exactly as on a list of dict).
    """
    if isinstance(value, Mapping):
        return MappingProxyType({k: _deep_freeze(v) for k, v in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_deep_freeze(v) for v in value)
    return value


def compile_template(jinja_source: str) -> tuple[Template, frozenset[str]]:
    """Compile jinja2 source and extract its non-`base_prompt` variables.

    The extracted variables (minus `KNOWN_RENDER_VARS`) are the host-facts a
    later render needs; PR-1 only carries them on `ResolvedOutput` for #265
    to consume — it does not check them against a host context yet
    (#264 / Decision 7).
    """
    required = jinja_meta.find_undeclared_variables(_TEMPLATE_ENV.parse(jinja_source))
    return _TEMPLATE_ENV.from_string(jinja_source), frozenset(required) - KNOWN_RENDER_VARS


def compile_challenge_prompt(jinja_source: str) -> tuple[Template, frozenset[str]]:
    """Compile a challenge prompt template and extract its unknown variables (#338).

    Like `compile_template`, but strips `CHALLENGE_RENDER_VARS` (base_prompt +
    username) instead of `KNOWN_RENDER_VARS`: the returned set is any variable a
    challenge prompt references beyond those two, which the loader rejects loudly
    (a challenge prompt has no sidecar to supply extra facts). Kept separate so
    the normal-output compile path never treats `username` as a satisfiable var.
    """
    required = jinja_meta.find_undeclared_variables(_TEMPLATE_ENV.parse(jinja_source))
    return _TEMPLATE_ENV.from_string(jinja_source), frozenset(required) - CHALLENGE_RENDER_VARS


@dataclass(frozen=True)
class ResolvedOutput:
    """Normalized output of a single command (#264 / D4).

    Exactly one ``kind`` is meaningful per instance:

    - ``none``: the command writes nothing (`text`/`template`/`handler` all None).
    - ``literal``: `text` is the verbatim wire body (no render step).
    - ``template``: `template` is a compiled jinja2 template rendered with
      ``base_prompt`` (+ host facts in #265).
    - ``handler``: `handler` is a callable producing the body at dispatch time.
    """

    kind: Literal["none", "literal", "template", "handler"]
    text: str | None = None
    template: Template | None = None
    handler: "CommandHandler | None" = None
    # For an A3-authored ``handler:`` command, the referenced handler name (an
    # identifier). The loader records it here with ``handler=None``; the merge
    # (`build_resolved_platform`) binds the actual callable from the platform's
    # py handler namespace, so an unresolved ref fails loudly at start rather
    # than being a silent no-output command (#317 / P-1, 案D).
    handler_ref: str | None = None
    required_vars: frozenset[str] = frozenset()
    values: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Harden `values` into a deeply read-only copy (#287, codex#3 6th + codex#1 1st).

        `ResolvedOutput` is cached and shared across every session (the
        platform-level ``functools.cache``), so a render-time mutation of
        `values` — including a nested ``parsed`` list/row — would be cache
        poisoning. `_deep_freeze` recursively converts the whole tree to
        read-only types so the contract is enforced, not just documented, and
        severs any alias to the dict the normalizer returned. Run
        unconditionally (no ``MappingProxyType`` shortcut): a shallow
        ``MappingProxyType`` passed in would otherwise keep a mutable nested
        list/row, leaving the contract incomplete (2nd round codex#3); re-freezing
        an already-frozen tree is a cheap build-time copy.
        """
        object.__setattr__(self, "values", _deep_freeze(self.values))

    def render(self, base_prompt: str) -> str | None:
        """Render literal/template output; None for none/handler kinds.

        Handler output is produced by the shell (it owns the device handle
        and the dispatch-time error boundary), so `render` returns None for
        it — the caller dispatches handlers separately. Callers MUST branch on
        `kind` first (handler/none and a genuinely empty body both surface as
        None here, so a None return is not by itself "write nothing").

        `values` (sidecar-json facts, #287) are splatted alongside
        ``base_prompt`` for ``template`` kind; they are empty for a plain
        ``base_prompt``-only template and ignored by literal/handler kinds, so
        those paths render exactly as before (#287 / D2).
        """
        if self.kind == "literal":
            return self.text
        if self.kind == "template" and self.template is not None:
            return self.template.render(base_prompt=base_prompt, **self.values)
        return None


# Sentinel kinds reused as module-level singletons (immutable, shareable).
NO_OUTPUT = ResolvedOutput(kind="none")


@dataclass(frozen=True)
class Transition:
    """One mode's transition decision in a command's `transitions` map (#317 / P-1).

    Exactly one is meaningful (the A3 loader / schema enforce it): `exit` True
    terminates the session; otherwise the command switches to `new_mode` (a
    validated mode name), or stays put when `new_mode` is None. An `exit`
    transition always carries ``new_mode=None``. This is the static, per-mode
    successor to a handler deciding its own transition at dispatch time (#115):
    the shell reads it from the schema instead of running the command.
    """

    new_mode: str | None = None
    exit: bool = False


@dataclass(frozen=True)
class ConfirmAction:
    """A resolved confirm-challenge action — one `on:` entry or `default:` (#338 / §3).

    Picked by looking the answer line up in `ResolvedChallenge.on`. `exit` True
    closes the session; else `new_mode` (a validated mode name) transitions, or
    None stays put. `output` is an inline `[OK]`-style body sent after the action
    (None = no body). Neither transition set + no output = a plain cancel (the
    ``n`` of a confirm). The schema forbids `output` together with `exit`.
    """

    new_mode: str | None = None
    exit: bool = False
    output: str | None = None


@dataclass(frozen=True)
class ResolvedChallenge:
    """A command's post-dispatch interactive sub-prompt (#338 / §2).

    Two kinds:

    - `kind == "password"` — the command holds its transition until the client
      answers a password prompt; `complete_challenge` verifies it and applies
      `success` (or answers `failure_output`). `auth` picks the expected value:
      `"secret"` → `host.secret` (falling back to `host.password` when unset,
      #338 / 案F), `"password"` → `host.password`. `success` is the transition on
      a correct answer (reusing `Transition`), `failure_output` the body on a
      wrong / empty one (the prompt stays put, a single attempt — #338 / C1).
    - `kind == "confirm"` — the answer line is looked up in `on` (falling back to
      `default`, else a cancel) to pick a `ConfirmAction`. `auth` / `success` /
      `failure_output` are None here; `on` / `default` are None on password.

    - `prompt` is a `ResolvedOutput` (literal, or a template rendered with
      `base_prompt` + `username`) — the shell renders it at fire time.
    - `modes` is the loader-normalized set of modes the challenge fires in: the
      authored `challenge.mode` when given, else the command's effective modes
      (an all-modes command expands to the platform's full mode set, mirroring
      `resolve_transitions`' `cmd_modes or mode_names`). A non-firing mode uses
      the command's ordinary `output` path, which is how a per-mode response
      (alcatel_sros `enable-admin`) is expressed without generalizing per-mode
      output (#338 / 案D).
    """

    kind: str
    prompt: ResolvedOutput
    modes: frozenset[str]
    auth: str | None = None
    success: Transition | None = None
    failure_output: str | None = None
    # `Mapping` (read-only) to match the sibling `ResolvedCommand.transitions`
    # convention for a frozen dataclass map field (1st round claude#4).
    on: Mapping[str, ConfirmAction] | None = None
    default: ConfirmAction | None = None


@dataclass(frozen=True)
class ResolvedCommand:
    """Normalized command, independent of the authoring form (#264 / D4).

    `modes` is the set of mode names the command is valid in; an empty set
    means "valid in every mode" (used by ``_default_`` and unconditional
    commands). `new_mode` is the mode to transition to after running, or None
    for no transition.

    `output` is always the served/primary capture (the only one the runtime
    sends). `variants` is the canonical contract for multi-capture commands:
    empty for a single-output command, otherwise the full ordered capture list
    with ``variants[0]`` mirroring `output` as the primary (``variant_1``) and
    the alternates following (``variant_2`` ..) (#264 / D3, D7).

    `canonical_name` is the name of the command this one resolves to: its own
    `name` for a real command, or the alias *target*'s name for an alias. The
    shell keys per-session variant state on it so every alias of one command
    shares one chosen state (#287 / D6 — without this, an alias would pick its
    own variant and the box would appear to "transform" between aliases). It
    defaults to `name`; `__post_init__` backfills it so real commands and the
    A3 ``dataclasses.replace`` alias path inherit it for free (#287, codex#1
    4th/5th).
    """

    name: str
    modes: frozenset[str]
    new_mode: str | None
    output: ResolvedOutput
    variants: tuple[tuple[str, ResolvedOutput], ...]
    help: str
    exit: bool
    type: str
    source: dict | None = None
    canonical_name: str = ""
    # Mode-conditional transition map (#317 / P-1): mode name -> `Transition`.
    # None (the common case) means the command uses the simple static
    # `new_mode` / `exit` above. When set, `_dispatch_general` looks up the
    # current mode and applies that entry's transition, falling back to
    # `exit` / `new_mode` only for a mode absent from the map. The loader
    # validates every key against the command's modes and every `new_mode`
    # value against the platform modes, and the schema keeps it exclusive with
    # the top-level `new_mode` / `exit`, so it never conflicts at runtime. An
    # A3 alias built via ``dataclasses.replace`` inherits the target's map (the
    # `mode:`-override alias path re-validates the inherited keys, #317 / P-1).
    # `disables_paging` marks a session-level "turn paging off" command (e.g.
    # `terminal length 0`, #307 / P3-4). The shell sets a sticky session flag when
    # such a command runs in-mode; the push driver then renders without the
    # `--More--` pager. An A3 alias built via ``dataclasses.replace(target, ...)``
    # inherits the target's value for free (alias authoring rows cannot set it).
    disables_paging: bool = False
    transitions: Mapping[str, Transition] | None = None
    # Post-dispatch interactive sub-prompt (#338 / §2). None for the common case
    # (no challenge). When set, `_dispatch_general` holds the transition and
    # returns a `PendingChallenge` for the modes in `challenge.modes`; other modes
    # fall through to the ordinary output path. An A3 alias built via
    # ``dataclasses.replace`` inherits the target's challenge for free (alias rows
    # cannot author it).
    challenge: "ResolvedChallenge | None" = None

    def __post_init__(self) -> None:
        # Backfill canonical_name to the command's own name when unset (empty
        # sentinel — a real command's name is never empty). A real command
        # resolves to itself; an A3 alias built via
        # ``dataclasses.replace(target, name=...)`` copies the target's already
        # backfilled canonical_name (replace does not touch it) so it inherits
        # automatically (#287 / D6, codex#1 4th).
        if not self.canonical_name:
            object.__setattr__(self, "canonical_name", self.name)


@dataclass(frozen=True)
class ModeDef:
    """A shell mode: a name plus its prompt template (#264 / D2, M2)."""

    name: str
    prompt_template: Template

    def render_prompt(self, base_prompt: str) -> str:
        """Render this mode's prompt for the given device base prompt."""
        return self.prompt_template.render(base_prompt=base_prompt)


@dataclass(frozen=True)
class ResolvedPlatform:
    """A platform's modes + resolved commands, ready for the shell (#264 / D4).

    ``frozen`` prevents reassigning the fields, not mutating the `modes` /
    `commands` dicts they point at. Consumers (notably the platform-level
    ``functools.cache`` D6 introduces) MUST treat them as read-only; hardening
    to a read-only mapping is deferred to that caching increment (1st round
    codex #1).

    `auth` carries the platform's ``auth`` setting (e.g. ``"none"`` to disable
    SSH auth, as dell_powerconnect uses); the A3 loader populates it from
    ``platform.yaml`` so `Nos._from_platform_dir` can wire ``nos.auth`` —
    without it the field would be a silent dead end (1st round claude #2).
    """

    modes: dict[str, ModeDef]
    initial_mode: str
    commands: dict[str, ResolvedCommand]
    auth: str | None = None
    # The platform's ``--More--`` pager prompt (#307 / P3-4), authored in
    # ``platform.yaml`` under ``paging.more_prompt`` (Cisco ``" --More-- "`` /
    # Juniper ``"---(more)---"`` / Huawei ``"---- More ----"``). The shell exposes
    # it to the push driver; the default mirrors Cisco IOS.
    more_prompt: str = " --More-- "
