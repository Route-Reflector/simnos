"""Unit tests for the A3 docs generator helpers (`tasks`).

`gen_docs_platform_commands` now renders each platform from the A3
`ResolvedCommand` (loud at `load_platform_dir` time) instead of the legacy
`platforms_yaml` + `str.format` path, so the old `render_template` build-time
formatter and its yaml-sweep loud check are gone (#264 / D9). What remains
worth pinning here is the surrounding plumbing the generator depends on:

- the sweep semantics, so a removed platform's markdown is deleted on the next
  regeneration while hand-authored `index.md` / `index.ja.md` are preserved
- A3 platform-name discovery (`_a3_platform_names`)
- the nav display-name derivation and the mkdocs Platforms-nav rewrite
"""

import pytest

from tasks import (
    _a3_platform_names,
    platform_display_name,
    rewrite_mkdocs_platforms_nav,
    sweep_orphaned_platform_docs,
)


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

    def test_a3_platform_doc_is_preserved(self, tmp_path):
        """A platform listed as valid keeps its page; only orphans are swept (#264).

        gen_docs feeds `sweep` the A3 platform names it just (re)generated, so a
        listed platform's page survives and a page with no backing platform is
        removed.
        """
        self._write(tmp_path / "cisco_ios.md")  # a generated A3 platform page
        self._write(tmp_path / "orphan.md")
        removed = sweep_orphaned_platform_docs(
            str(tmp_path),
            valid_platforms={"cisco_ios"},
        )
        assert removed == ["orphan.md"]
        assert (tmp_path / "cisco_ios.md").exists()

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


class TestA3PlatformNames:
    """`_a3_platform_names` discovers A3 platform dirs (those with platform.yaml)."""

    def test_finds_dirs_with_platform_yaml(self, tmp_path):
        (tmp_path / "cisco_ios").mkdir()
        (tmp_path / "cisco_ios" / "platform.yaml").write_text("modes: {}\n", encoding="utf-8")
        (tmp_path / "not_a_platform").mkdir()  # no platform.yaml
        (tmp_path / "stray.txt").write_text("x", encoding="utf-8")
        assert _a3_platform_names(str(tmp_path)) == ["cisco_ios"]

    def test_absent_dir_is_empty(self, tmp_path):
        assert _a3_platform_names(str(tmp_path / "nonexistent")) == []


class TestPlatformDisplayName:
    """Pin the nav display-name derivation (#239)."""

    def test_override_wins(self):
        """A curated override beats the default derivation."""
        assert platform_display_name("aruba_aoscx") == "Aruba AOS-CX"

    def test_default_title_cases_tokens(self):
        """An unknown slug falls back to title-casing each token."""
        assert platform_display_name("acme_router") == "Acme Router"


class TestRewriteMkdocsPlatformsNav:
    """Pin the Platforms nav regeneration semantics (#239).

    Operates on a minimal mkdocs-like file so the pins are independent of
    the real mkdocs.yml content (which the manifest test in
    `tests/core/test_simnos.py` checks against the registry).
    """

    MKDOCS_STUB = (
        "site_name: stub\n"
        "nav:\n"
        '  - Home: "index.md"\n'
        "  - Platforms:\n"
        '      - Index: "platforms/index.md"\n'
        '      - Stale Entry: "platforms/removed_platform.md"\n'
        "  - Development:\n"
        '      - Index: "development/index.md"\n'
    )

    def test_rewrites_only_platforms_section(self, tmp_path):
        """Entries are regenerated sorted; surrounding sections untouched."""
        mkdocs = tmp_path / "mkdocs.yml"
        mkdocs.write_text(self.MKDOCS_STUB, encoding="utf-8")

        rewrite_mkdocs_platforms_nav(["cisco_ios", "arista_eos"], mkdocs_path=str(mkdocs))

        text = mkdocs.read_text(encoding="utf-8")
        assert (
            "  - Platforms:\n"
            '      - Index: "platforms/index.md"\n'
            '      - Arista EOS: "platforms/arista_eos.md"\n'
            '      - Cisco IOS: "platforms/cisco_ios.md"\n'
            "  - Development:\n"
        ) in text
        assert "removed_platform" not in text  # stale entry swept
        assert '  - Home: "index.md"\n' in text  # other sections preserved

    def test_idempotent(self, tmp_path):
        """A second run produces byte-identical output."""
        mkdocs = tmp_path / "mkdocs.yml"
        mkdocs.write_text(self.MKDOCS_STUB, encoding="utf-8")

        rewrite_mkdocs_platforms_nav(["cisco_ios"], mkdocs_path=str(mkdocs))
        first = mkdocs.read_text(encoding="utf-8")
        rewrite_mkdocs_platforms_nav(["cisco_ios"], mkdocs_path=str(mkdocs))

        assert mkdocs.read_text(encoding="utf-8") == first

    def test_missing_platforms_section_raises(self, tmp_path):
        """A file without the Platforms section fails loud, not silent."""
        mkdocs = tmp_path / "mkdocs.yml"
        mkdocs.write_text("site_name: stub\nnav:\n  - Home: 'index.md'\n", encoding="utf-8")

        with pytest.raises(RuntimeError, match=r"Could not locate the '  - Platforms:' nav section"):
            rewrite_mkdocs_platforms_nav(["cisco_ios"], mkdocs_path=str(mkdocs))
