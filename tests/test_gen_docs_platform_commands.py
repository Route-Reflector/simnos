"""Unit tests for `tasks.render_template`.

Pin the formatter semantics that `gen_docs_platform_commands` relies on:
- substitutes `{base_prompt}` with the platform name
- unescapes `{{` / `}}` literals (preventive escape from
  `sync_ntc_commands.escape_format_braces`)
- raises `RuntimeError` with platform / command / field context on any
  formatting failure (escape漏れ など)

Without these tests, a future refactor switching `.format()` back to
`.replace()` (or any other formatter) would silently break docs rendering
for platforms that contain literal braces (e.g. `{master:0}` in
`juniper_junos`, `{ <cr>||<K> }` in `huawei_smartax`).
"""

import pytest

from tasks import render_template


class TestRenderTemplate:
    """Pin formatting semantics shared with `cmd_shell.default`."""

    def test_substitutes_base_prompt(self):
        """`{base_prompt}` must be replaced by the platform name."""
        result = render_template("{base_prompt}>", "huawei_smartax", "enable", "prompt")
        assert result == "huawei_smartax>"

    def test_unescapes_doubled_braces(self):
        """`{{ ... }}` must collapse to `{ ... }` to match runtime output."""
        result = render_template("{{master:0}}", "juniper_junos", "show version", "output")
        assert result == "{master:0}"

    def test_handles_combined_substitution_and_escape(self):
        """Both transformations applied in the same string."""
        template = "{base_prompt}> {{literal}}"
        result = render_template(template, "huawei_smartax", "display", "output")
        assert result == "huawei_smartax> {literal}"

    def test_passthrough_when_no_placeholders(self):
        """Plain strings must pass through unchanged."""
        result = render_template("Hello world", "linux", "ls", "output")
        assert result == "Hello world"

    def test_raises_runtime_error_on_unknown_placeholder(self):
        """Unescaped `{xxx}` (xxx != base_prompt) must surface a contextual error."""
        with pytest.raises(RuntimeError, match=r"Failed to format output for platformA/'cmd1'"):
            render_template("{unknown}", "platformA", "cmd1", "output")

    def test_raises_runtime_error_on_broken_brace(self):
        """Malformed brace (e.g. unmatched `{`) must surface a contextual error."""
        with pytest.raises(RuntimeError, match=r"Failed to format prompt for platformB/'cmd2'"):
            render_template("{broken", "platformB", "cmd2", "prompt")

    def test_error_message_hints_at_escape_fix(self):
        """Error message should point users at the escape rule."""
        with pytest.raises(RuntimeError, match=r"escape"):
            render_template("{oops}", "p", "c", "output")
