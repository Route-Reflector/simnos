"""Unit tests for `tasks.render_template` and `tasks.sweep_orphaned_platform_docs`.

Pin the formatter semantics that `gen_docs_platform_commands` relies on:
- substitutes `{base_prompt}` with the platform name
- unescapes `{{` / `}}` literals (preventive escape from
  `sync_ntc_commands.escape_format_braces`)
- raises `RuntimeError` with platform / command / field context on any
  formatting failure (escape漏れ など) and on unsupported-but-renderable
  constructs (strict authoring check, e.g. `{base_prompt!r}`)

Without these tests, a future refactor switching `.format()` back to
`.replace()` (or any other formatter) would silently break docs rendering
for platforms that contain literal braces (e.g. `{master:0}` in
`juniper_junos`, `{ <cr>||<K> }` in `huawei_smartax`).

Also pin the sweep semantics so that deleting a yaml causes the matching
markdown to be removed on the next regeneration, while hand-authored
`index.md` / `index.ja.md` are preserved.

Since #171/#172 the catch set is the 5-tuple `FORMAT_ERRORS` shared with
the lenient runtime (`cmd_shell._safe_format`), and the platform-yaml
template sweep below keeps the "build-time loud" side CI-resident.
"""

import os

import pytest
import yaml

from tasks import render_template, sweep_orphaned_platform_docs

PLATFORMS_YAML_DIR = "simnos/plugins/nos/platforms_yaml"


def _yaml_platforms() -> list[str]:
    """Platform names from the yaml dir (the same source gen_docs lists)."""
    return sorted(f.removesuffix(".yaml") for f in os.listdir(PLATFORMS_YAML_DIR) if f.endswith(".yaml"))


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

    def test_raises_runtime_error_on_positional_placeholder(self):
        """`{}` must surface a contextual error.

        Pins #171: would raise IndexError via `str.format()`; rejected by
        the strict authoring check (empty field name). Added so each
        unsupported-input family is pinned symmetrically with the runtime
        fallback tests in tests/plugins/test_cmd_shell.py.
        """
        with pytest.raises(RuntimeError, match=r"Failed to format output for platformE/'cmd5'"):
            render_template("value is {}", "platformE", "cmd5", "output")

    def test_raises_runtime_error_on_attribute_access(self):
        """`{base_prompt.foo}` must surface a contextual error.

        Pins #171: would raise AttributeError via `str.format()` (a member
        of the shared 5-tuple `FORMAT_ERRORS`); rejected by the strict
        authoring check (compound field name). Previously this dumped a
        contextless stack trace at docs-gen time.
        """
        with pytest.raises(RuntimeError, match=r"Failed to format output for platformC/'cmd3'"):
            render_template("{base_prompt.foo}", "platformC", "cmd3", "output")

    def test_raises_runtime_error_on_item_access(self):
        """`{base_prompt[bad]}` must surface a contextual error.

        Pins #171: would raise TypeError via `str.format()`, the fifth
        member of `FORMAT_ERRORS`; rejected by the strict authoring check.
        With the KeyError / ValueError / IndexError pins above, every
        unsupported-input family has a contextual-RuntimeError pin.
        """
        with pytest.raises(RuntimeError, match=r"Failed to format prompt for platformD/'cmd4'"):
            render_template("{base_prompt[bad]}", "platformD", "cmd4", "prompt")

    def test_raises_runtime_error_on_conversion(self):
        """`{base_prompt!r}` must be rejected even though it renders fine.

        Pins the strict authoring check (1st code review 反映): conversion
        specifiers raise no exception via `str.format()` (they would render
        a quoted hostname), so without the explicit parse-time check the
        "only two constructs supported" spec would silently erode.
        """
        with pytest.raises(RuntimeError, match=r"Failed to format output for platformF/'cmd6'.*unsupported"):
            render_template("{base_prompt!r}", "platformF", "cmd6", "output")

    def test_raises_runtime_error_on_format_spec(self):
        """`{base_prompt:>20}` must be rejected even though it renders fine.

        Pins the strict authoring check: str-valid format specs render
        without raising, so the parse-time check is the only guard.
        """
        with pytest.raises(RuntimeError, match=r"Failed to format prompt for platformG/'cmd7'.*unsupported"):
            render_template("{base_prompt:>20}", "platformG", "cmd7", "prompt")


class TestPlatformYamlTemplateSweep:
    """CI-resident loud counterpart of the lenient runtime (#171/#172).

    The runtime shell silently logs malformed `{base_prompt}` templates
    (`cmd_shell._safe_format`), so a yaml authoring mistake in this repo
    would otherwise surface only as a runtime log line. This sweep renders
    every str template field of every platform yaml through
    `render_template`, turning such a mistake into a contextual
    RuntimeError in CI.

    Covered fields: top-level initial_prompt / enable_prompt /
    config_prompt (the latter two are not formatted by cmd_shell today,
    but are written as `{base_prompt}` templates in yaml — covered
    preventively) + per-command output (str only; callable outputs are
    covered by the T-14 / #230 device-class tests) / prompt (each list
    candidate gets an indexed field name like `prompt[0]`) / new_prompt.
    """

    TOP_LEVEL_FIELDS = ("initial_prompt", "enable_prompt", "config_prompt")

    @pytest.mark.parametrize("platform", _yaml_platforms())
    def test_all_templates_render(self, platform):
        """Every `{base_prompt}` template field in the yaml must render."""
        with open(f"{PLATFORMS_YAML_DIR}/{platform}.yaml", encoding="utf-8") as file:
            data = yaml.safe_load(file)

        for field in self.TOP_LEVEL_FIELDS:
            template = data.get(field)
            if isinstance(template, str):
                render_template(template, platform, "-", field)

        for command, details in data.get("commands", {}).items():
            output = details.get("output")
            if isinstance(output, str):
                render_template(output, platform, command, "output")
            prompts = details.get("prompt", [])
            if isinstance(prompts, str):
                render_template(prompts, platform, command, "prompt")
            else:
                for i, prompt in enumerate(prompts):
                    render_template(prompt, platform, command, f"prompt[{i}]")
            new_prompt = details.get("new_prompt")
            if isinstance(new_prompt, str):
                render_template(new_prompt, platform, command, "new_prompt")


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
