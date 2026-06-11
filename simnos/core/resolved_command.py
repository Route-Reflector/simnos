"""Runtime command representation (#264 / P1-1 D4).

The shell, docs gen and tests consume one normalized representation —
`ResolvedCommand` / `ResolvedOutput` — regardless of the authoring inflow
(legacy ``platforms_yaml`` dicts, py-plugin dicts, inventory commands, or
the future A3 ``commands/*.yaml``). The legacy adapter
(:mod:`simnos.core.command_adapter`) normalizes the old forms into these
dataclasses; the new A3 loader (PR-2) produces them directly.

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

from dataclasses import dataclass
import string
from typing import TYPE_CHECKING, Literal

from jinja2 import Environment, StrictUndefined, Template
from jinja2 import meta as jinja_meta

if TYPE_CHECKING:
    from simnos.core.command_contract import CommandHandler

# The single known render variable. Extracted template variables minus this
# set become `ResolvedOutput.required_vars` — the host-facts to check at
# start time (#265). `base_prompt` is always supplied by the shell, so it is
# never a "missing var" (#264 / D4, 2nd round gemini #4).
KNOWN_RENDER_VARS: frozenset[str] = frozenset({"base_prompt"})

# Jinja2 environment for output/prompt templates. `keep_trailing_newline`
# keeps the final newline jinja2 would otherwise strip (wire output is
# compared byte-for-byte by the migration oracle); `StrictUndefined` makes an
# undefined fact loud at render time instead of rendering an empty string
# (#264 / D5, Decision 7). No trim/lstrip: output whitespace is significant.
_TEMPLATE_ENV = Environment(
    undefined=StrictUndefined,
    autoescape=False,  # noqa: S701 — output is CLI text, not HTML
    keep_trailing_newline=True,
)

_FORMATTER = string.Formatter()


def _jinja_raw(literal: str) -> str:
    """Wrap a literal segment so jinja2 emits it verbatim.

    A literal segment may contain ``{``/``}`` (router output, JSON, brace
    art) that jinja2 would otherwise read as ``{{`` / ``{%`` delimiters.
    ``{% raw %}`` disables jinja2 parsing inside; the only sequence that
    could break out is a literal ``{% endraw %}``, which never appears in
    NOS CLI output — guarded loudly just in case (#264 / D6, D8).
    """
    if "endraw" in literal:
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
    """
    parts: list[str] = []
    has_field = False
    try:
        segments = list(_FORMATTER.parse(template))
    except ValueError as e:
        # Unbalanced brace (e.g. "value is {broken"): str.format would raise
        # the same way. Loud per D6 item 3.
        raise ValueError(f"malformed format template {template!r}: {e}") from e
    for literal_text, field_name, format_spec, conversion in segments:
        if literal_text:
            parts.append(_jinja_raw(literal_text))
        if field_name is None:
            continue
        if field_name != "base_prompt" or format_spec or conversion:
            raise ValueError(
                f"unsupported format field in template {template!r}: "
                f"field={field_name!r} spec={format_spec!r} conversion={conversion!r} "
                "(only a bare {base_prompt} is supported)"
            )
        has_field = True
        parts.append("{{ base_prompt }}")
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
    required_vars: frozenset[str] = frozenset()

    def render(self, base_prompt: str) -> str | None:
        """Render literal/template output; None for none/handler kinds.

        Handler output is produced by the shell (it owns the device handle
        and the dispatch-time error boundary), so `render` returns None for
        it — the caller dispatches handlers separately.
        """
        if self.kind == "literal":
            return self.text
        if self.kind == "template" and self.template is not None:
            return self.template.render(base_prompt=base_prompt)
        return None


# Sentinel kinds reused as module-level singletons (immutable, shareable).
NO_OUTPUT = ResolvedOutput(kind="none")


@dataclass(frozen=True)
class ResolvedCommand:
    """Normalized command, independent of the authoring form (#264 / D4).

    `modes` is the set of mode names the command is valid in; an empty set
    means "valid in every mode" (the successor of legacy ``prompt`` omission,
    used by ``_default_`` and unconditional commands). `new_mode` is the mode
    to transition to after running, or None for no transition.
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
    """A platform's modes + resolved commands, ready for the shell (#264 / D4)."""

    modes: dict[str, ModeDef]
    initial_mode: str
    commands: dict[str, ResolvedCommand]
