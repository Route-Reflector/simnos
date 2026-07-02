"""Runtime command representation (#264 / P1-1 D4).

The shell, docs gen and tests consume one normalized representation —
`ResolvedCommand` / `ResolvedOutput` — regardless of the authoring inflow
(A3 ``commands/*.yaml``, py-plugin dicts, or inventory commands). The A3 loader
(:mod:`simnos.core.platform_loader`) produces these dataclasses directly; the
adapter (:mod:`simnos.core.command_adapter`) normalizes the remaining legacy
dict inflows (py-plugin / inventory) into the same form.

The representation is a frozen dataclass, not a pydantic model: every load
path validates at its boundary, so runtime re-validation is unnecessary and
a dataclass can hold a compiled ``jinja2.Template`` / a handler callable
directly (#264 / D4).

This module also owns the ``str.format`` -> jinja2 conversion the legacy
adapter relies on: v2 rendered yaml/py output and prompt templates with
``str.format(base_prompt=...)``, while the new runtime renders templates with
jinja2 (``StrictUndefined``). The converter (`format_template_to_jinja`)
makes the two equivalent for the brace-escape and ``{base_prompt}`` cases the
legacy data actually uses (#264 / D6, D8).
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
import re
import string
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

# Jinja2 environment for output/prompt templates. `StrictUndefined` makes an
# undefined fact loud at render time instead of rendering an empty string
# (#264 / D5, Decision 7). No trim/lstrip: output whitespace is significant.
# `keep_trailing_newline` keeps the final newline jinja2 would otherwise strip
# — inert for legacy-adapter inflow (its converted source always ends in
# ``{% endraw %}`` / ``{{ base_prompt }}``, never a bare newline), but needed
# for the hand-written ``.j2`` templates A3 authoring introduces in PR-2.
_TEMPLATE_ENV = Environment(
    undefined=StrictUndefined,
    autoescape=False,  # noqa: S701 — output is CLI text, not HTML
    keep_trailing_newline=True,
)

_FORMATTER = string.Formatter()


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


# A `{% endraw %}` tag (jinja2 tolerates whitespace and the +/- trim markers)
# is the only sequence that can break out of a `{% raw %}` wrapping. Match just
# that, not the bare word "endraw" — real CLI output can legitimately contain
# the word without the surrounding delimiters (1st round codex #2 / claude #4a).
_ENDRAW_DELIMITER = re.compile(r"\{%[-+]?\s*endraw\b")


def _jinja_raw(literal: str) -> str:
    """Wrap a literal run so jinja2 emits it verbatim.

    A literal run may contain ``{``/``}`` (router output, JSON, brace art)
    that jinja2 would otherwise read as ``{{`` / ``{%`` delimiters.
    ``{% raw %}`` disables jinja2 parsing inside; the only sequence that
    could break out is a literal ``{% endraw %}``, which never appears in
    NOS CLI output — guarded loudly just in case (#264 / D6, D8). The caller
    passes the full concatenated run so this guard sees a ``{% endraw %}``
    even when ``{{`` split it across formatter segments.
    """
    if _ENDRAW_DELIMITER.search(literal):
        raise ValueError(f"output literal contains a jinja2 raw-block delimiter, cannot convert: {literal!r}")
    return "{% raw %}" + literal + "{% endraw %}"


def format_template_to_jinja(template: str) -> tuple[str, bool]:
    """Convert a ``str.format`` template to equivalent jinja2 source.

    Returns ``(jinja_source, has_base_prompt)``. The conversion is exact for
    the constructs legacy SIMNOS data uses: ``{{`` / ``}}`` brace escapes and
    the lone ``{base_prompt}`` field. Any other field (``{0}`` / ``{}`` /
    ``{other}``), a format spec (``{base_prompt:>10}``), a conversion
    (``{base_prompt!r}``) or an unbalanced brace raises ``ValueError`` — the
    loud-fail boundary that replaces v2's silent ``str.format`` fallback for
    such templates (#264 / D6 item 3, #162). Packaged data is verified clean
    (0 format failures) by the migration oracle.

    `string.Formatter.parse` already unescapes ``{{`` -> ``{`` in the literal
    segments it yields, so a template with no field round-trips to its
    unescaped literal text.

    Consecutive literal segments are concatenated before being wrapped in one
    ``{% raw %}`` block: ``{{`` splits a literal run in two (the ``{`` lands at
    the end of one segment, the rest in the next), so wrapping per-segment
    could leave a ``{% endraw %}`` straddling the boundary that the per-segment
    guard cannot see. Joining first means the guard inspects the full literal.
    """
    parts: list[str] = []
    has_field = False
    literal_run: list[str] = []

    def flush_literal() -> None:
        if literal_run:
            parts.append(_jinja_raw("".join(literal_run)))
            literal_run.clear()

    try:
        segments = list(_FORMATTER.parse(template))
    except ValueError as e:
        # Unbalanced brace (e.g. "value is {broken"): str.format would raise
        # the same way. Loud per D6 item 3.
        raise ValueError(f"malformed format template {template!r}: {e}") from e
    for literal_text, field_name, format_spec, conversion in segments:
        if literal_text:
            literal_run.append(literal_text)
        if field_name is None:
            continue
        flush_literal()  # a field ends the current literal run
        if field_name != "base_prompt" or format_spec or conversion:
            raise ValueError(
                f"unsupported format field in template {template!r}: "
                f"field={field_name!r} spec={format_spec!r} conversion={conversion!r} "
                "(only a bare {base_prompt} is supported)"
            )
        has_field = True
        parts.append("{{ base_prompt }}")
    flush_literal()
    return "".join(parts), has_field


def compile_template(jinja_source: str) -> tuple[Template, frozenset[str]]:
    """Compile jinja2 source and extract its non-`base_prompt` variables.

    The extracted variables (minus `KNOWN_RENDER_VARS`) are the host-facts a
    later render needs; PR-1 only carries them on `ResolvedOutput` for #265
    to consume — it does not check them against a host context yet
    (#264 / Decision 7).
    """
    required = jinja_meta.find_undeclared_variables(_TEMPLATE_ENV.parse(jinja_source))
    return _TEMPLATE_ENV.from_string(jinja_source), frozenset(required) - KNOWN_RENDER_VARS


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
    # than being a silent no-output command (#317 / P-1, 案D). The legacy adapter
    # sets ``handler`` directly and leaves this None.
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
        ``base_prompt`` for ``template`` kind; they are empty for the legacy
        ``base_prompt``-only templates and ignored by literal/handler kinds, so
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
class ResolvedCommand:
    """Normalized command, independent of the authoring form (#264 / D4).

    `modes` is the set of mode names the command is valid in; an empty set
    means "valid in every mode" (the successor of legacy ``prompt`` omission,
    used by ``_default_`` and unconditional commands). `new_mode` is the mode
    to transition to after running, or None for no transition.

    `output` is always the served/primary capture (the only one the runtime
    sends). `variants` is the canonical contract for multi-capture commands:
    empty for a single-output command, otherwise the full ordered capture list
    with ``variants[0]`` mirroring `output` as the primary (``variant_1``) and
    the alternates following (``variant_2`` ..). This is the one semantics all
    inflows normalize to — the legacy adapter rebuilds it from v2's separate
    ``output`` / ``output_variants`` (#264 / D3, D7).

    `canonical_name` is the name of the command this one resolves to: its own
    `name` for a real command, or the alias *target*'s name for an alias. The
    shell keys per-session variant state on it so every alias of one command
    shares one chosen state (#287 / D6 — without this, an alias would pick its
    own variant and the box would appear to "transform" between aliases). It
    defaults to `name`; `__post_init__` backfills it so real commands and the
    A3 ``dataclasses.replace`` alias path inherit it for free, while the legacy
    adapter passes the target name explicitly (#287, codex#1 4th/5th).
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
    without it the field would be a silent dead end (1st round claude #2). The
    legacy adapter leaves it None (legacy NOS keeps `auth` on the Nos directly).
    """

    modes: dict[str, ModeDef]
    initial_mode: str
    commands: dict[str, ResolvedCommand]
    auth: str | None = None
    # The platform's ``--More--`` pager prompt (#307 / P3-4), authored in
    # ``platform.yaml`` under ``paging.more_prompt`` (Cisco ``" --More-- "`` /
    # Juniper ``"---(more)---"`` / Huawei ``"---- More ----"``). The shell exposes
    # it to the push driver; the default mirrors Cisco IOS. The legacy adapter
    # leaves the default (legacy NOS have no A3 ``platform.yaml``).
    more_prompt: str = " --More-- "
