"""Unit tests for the runtime command representation (#264 / P1-1 D4).

Covers `compile_template` var extraction and `ResolvedOutput.render` per kind
(the `str.format` -> jinja2 converter retired with the legacy adapter,
#317 P-4).
"""

from simnos.core.resolved_command import ResolvedOutput, compile_template


class TestCompileTemplate:
    """`compile_template` extracts host facts, excluding `base_prompt`."""

    def test_base_prompt_excluded_from_required_vars(self):
        """`base_prompt` is shell-supplied, never a required host fact (#265)."""
        _, required = compile_template("{{ base_prompt }}>")
        assert required == frozenset()

    def test_other_vars_kept_as_required(self):
        """Non-`base_prompt` template vars are kept for #265 host-facts checking."""
        _, required = compile_template("{{ base_prompt }} {{ hostname }} {{ serial }}")
        assert required == frozenset({"hostname", "serial"})


class TestResolvedOutputRender:
    """`ResolvedOutput.render` per kind."""

    def test_literal_returns_text(self):
        out = ResolvedOutput(kind="literal", text="static body")
        assert out.render("bp") == "static body"

    def test_none_returns_none(self):
        out = ResolvedOutput(kind="none")
        assert out.render("bp") is None

    def test_template_renders_with_base_prompt(self):
        compiled, _ = compile_template("hostname {{ base_prompt }}")
        out = ResolvedOutput(kind="template", template=compiled)
        assert out.render("R7") == "hostname R7"

    def test_handler_render_returns_none(self):
        """Handler output is produced by the shell, not by `render`."""
        out = ResolvedOutput(kind="handler", handler=lambda device, **kw: "x")
        assert out.render("bp") is None
