"""Unit tests for the runtime command representation (#264 / P1-1 D4).

Covers the `str.format` -> jinja2 converter (exactness vs v2 and its loud
boundary) and `ResolvedOutput.render` per kind.
"""

import pytest

from simnos.core.resolved_command import (
    ResolvedOutput,
    compile_template,
    format_template_to_jinja,
)


class TestFormatTemplateToJinja:
    """`format_template_to_jinja` must match `str.format` for legacy forms."""

    @pytest.mark.parametrize(
        "template",
        [
            "plain text",
            "hostname {base_prompt}",
            "{base_prompt} uptime is 1 day",
            "a {{ b }} literal",
            "={{RA, Tunnel, }}",
            "line1\nline2\n",
            "{base_prompt}>",
            "{base_prompt}(config)#",
            "Hostname: {base_prompt}\nFQDN:     {base_prompt}",
            "{{base_prompt}}",
            'JSON {{"k": 1}} end',
            "",
        ],
    )
    def test_render_matches_str_format(self, template):
        """The compiled jinja template renders identically to `str.format`."""
        base_prompt = "R1-device"
        jinja_source, _ = format_template_to_jinja(template)
        compiled, _ = compile_template(jinja_source)
        assert compiled.render(base_prompt=base_prompt) == template.format(base_prompt=base_prompt)

    def test_has_field_flag(self):
        """`has_base_prompt` reflects whether a `{base_prompt}` field is present."""
        _, has = format_template_to_jinja("hostname {base_prompt}")
        assert has is True
        _, has = format_template_to_jinja("a {{ b }} literal")
        assert has is False

    @pytest.mark.parametrize(
        "bad",
        [
            "value is {unknown}",  # unsupported field
            "pos {}",  # positional field
            "idx {0}",  # numbered field
            "spec {base_prompt:>5}",  # format spec
            "conv {base_prompt!r}",  # conversion
            "unbalanced {broken",  # malformed brace
        ],
    )
    def test_loud_on_unsupported_or_malformed(self, bad):
        """Unsupported fields / malformed braces raise (the #162 loud boundary)."""
        with pytest.raises(ValueError):
            format_template_to_jinja(bad)

    def test_endraw_injection_guarded(self):
        """A literal carrying a jinja raw-block delimiter raises, not silently breaks.

        The escaped form ``{{% endraw %}}`` collapses (under `str.format`) to a
        literal ``{% endraw %}``, the one sequence that could break out of the
        ``{% raw %}`` wrapping — guarded loudly.
        """
        with pytest.raises(ValueError, match="raw-block"):
            format_template_to_jinja("text {{% endraw %}} more")


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
