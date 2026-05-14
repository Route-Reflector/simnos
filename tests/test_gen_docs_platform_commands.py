"""Unit tests for `tasks.render_template` and `tasks.sweep_orphaned_platform_docs`.

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

Also pin the sweep semantics so that deleting a yaml causes the matching
markdown to be removed on the next regeneration, while hand-authored
`index.md` / `index.ja.md` are preserved.
"""

import pytest

from tasks import render_template, sweep_orphaned_platform_docs


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


class TestSweepOrphanedPlatformDocs:
    """Pin sweep semantics so docs regeneration stays idempotent with yaml."""

    def _write(self, path, content=""):
        path.write_text(content, encoding="utf-8")

    def test_removes_md_without_matching_yaml(self, tmp_path):
        """A `.md` whose platform is not in `valid_platforms` must be removed."""
        self._write(tmp_path / "cisco_ios.md")
        self._write(tmp_path / "deleted_platform.md")

        removed = sweep_orphaned_platform_docs(
            str(tmp_path),
            valid_platforms={"cisco_ios"},
        )

        assert removed == ["deleted_platform.md"]
        assert (tmp_path / "cisco_ios.md").exists()
        assert not (tmp_path / "deleted_platform.md").exists()

    def test_keeps_md_with_matching_yaml(self, tmp_path):
        """Markdown whose platform is in `valid_platforms` must be kept."""
        self._write(tmp_path / "juniper_junos.md")

        removed = sweep_orphaned_platform_docs(
            str(tmp_path),
            valid_platforms={"juniper_junos"},
        )

        assert removed == []
        assert (tmp_path / "juniper_junos.md").exists()

    def test_preserves_default_index_pages(self, tmp_path):
        """`index.md` and `index.ja.md` must never be swept (default preserve)."""
        self._write(tmp_path / "index.md")
        self._write(tmp_path / "index.ja.md")
        self._write(tmp_path / "orphan.md")

        removed = sweep_orphaned_platform_docs(
            str(tmp_path),
            valid_platforms=set(),
        )

        assert removed == ["orphan.md"]
        assert (tmp_path / "index.md").exists()
        assert (tmp_path / "index.ja.md").exists()

    def test_preserve_list_is_overridable(self, tmp_path):
        """Custom `preserve` argument must be honored (drops index defaults)."""
        self._write(tmp_path / "index.md")
        self._write(tmp_path / "keep_me.md")

        removed = sweep_orphaned_platform_docs(
            str(tmp_path),
            valid_platforms=set(),
            preserve=frozenset({"keep_me.md"}),
        )

        # index.md is no longer preserved by the custom list, so it is swept.
        assert removed == ["index.md"]
        assert (tmp_path / "keep_me.md").exists()
        assert not (tmp_path / "index.md").exists()

    def test_ignores_non_markdown_files(self, tmp_path):
        """Non-`.md` siblings (images, indexes etc.) must not be touched."""
        self._write(tmp_path / "diagram.png", "binary")
        self._write(tmp_path / "notes.txt", "text")
        self._write(tmp_path / "orphan.md")

        removed = sweep_orphaned_platform_docs(
            str(tmp_path),
            valid_platforms=set(),
        )

        assert removed == ["orphan.md"]
        assert (tmp_path / "diagram.png").exists()
        assert (tmp_path / "notes.txt").exists()

    def test_empty_directory(self, tmp_path):
        """Empty docs folder must not raise."""
        removed = sweep_orphaned_platform_docs(
            str(tmp_path),
            valid_platforms={"cisco_ios"},
        )

        assert removed == []

    def test_returns_sorted_list(self, tmp_path):
        """Return order must be deterministic for stable logging output."""
        for name in ("zzz.md", "aaa.md", "mmm.md"):
            self._write(tmp_path / name)

        removed = sweep_orphaned_platform_docs(
            str(tmp_path),
            valid_platforms=set(),
        )

        assert removed == ["aaa.md", "mmm.md", "zzz.md"]
