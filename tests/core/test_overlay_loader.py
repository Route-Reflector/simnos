"""Unit tests for the user overlay loader (#286 / P1-2a — custom data layering).

These build a small base `ResolvedPlatform` plus an overlay dir of `.txt` / `.j2`
files on tmp_path and assert `resolve_overlay` produces the right merge-ready
commands for each `override_commands` form, and that every build-time guard
(Decision 8-11) fails loudly.
"""

import logging

import pytest

from simnos.core.overlay_loader import resolve_overlay
from simnos.core.resolved_command import ResolvedCommand, ResolvedOutput, ResolvedPlatform


def _literal(text: str) -> ResolvedOutput:
    return ResolvedOutput(kind="literal", text=text)


def _command(
    name: str, *, output: ResolvedOutput | None = None, variants=(), modes=frozenset({"enable"})
) -> ResolvedCommand:
    return ResolvedCommand(
        name=name,
        modes=modes,
        new_mode=None,
        output=output or _literal(f"base {name}\n"),
        variants=variants,
        help=f"help for {name}",
        exit=False,
        type="ntc",
        source={"raw": f"{name}.raw"},
    )


def _base(*commands: ResolvedCommand) -> ResolvedPlatform:
    """Minimal base platform — resolve_overlay only reads `commands`."""
    return ResolvedPlatform(modes={}, initial_mode="", commands={c.name: c for c in commands})


def _write(overlay_root, filename, content):
    (overlay_root / filename).write_text(content, encoding="utf-8")


class TestOverrideForms:
    def test_all_applies_every_file(self, tmp_path):
        base = _base(_command("show version"), _command("show clock"))
        _write(tmp_path, "show_version.txt", "OVERRIDDEN version\n")
        _write(tmp_path, "show_clock.txt", "OVERRIDDEN clock\n")
        resolved = resolve_overlay(str(tmp_path), base, override_commands="all")
        assert set(resolved) == {"show version", "show clock"}
        assert resolved["show version"].output.text == "OVERRIDDEN version\n"

    def test_list_applies_named_commands_only(self, tmp_path):
        base = _base(_command("show version"), _command("show clock"))
        _write(tmp_path, "show_version.txt", "OVERRIDDEN version\n")
        _write(tmp_path, "show_clock.txt", "ignored\n")
        resolved = resolve_overlay(str(tmp_path), base, override_commands=["show version"])
        assert set(resolved) == {"show version"}

    def test_map_selects_explicit_file_per_command(self, tmp_path):
        """The R11 case: a host pulls a specific capture file for a command."""
        base = _base(_command("show version"))
        _write(tmp_path, "show_version_B.txt", "B-variant version\n")
        resolved = resolve_overlay(str(tmp_path), base, override_commands={"show version": "show_version_B.txt"})
        assert resolved["show version"].output.text == "B-variant version\n"


class TestOutputOnlyOverride:
    def test_inherits_base_fields_swaps_output(self, tmp_path):
        base = _base(_command("show version", modes=frozenset({"user", "enable"})))
        _write(tmp_path, "show_version.txt", "NEW\n")
        cmd = resolve_overlay(str(tmp_path), base, override_commands="all")["show version"]
        # output swapped, everything else inherited from base.
        assert cmd.output.text == "NEW\n"
        assert cmd.modes == frozenset({"user", "enable"})
        assert cmd.help == "help for show version"
        assert cmd.type == "ntc"
        assert cmd.variants == ()

    def test_source_records_overlay_file(self, tmp_path):
        base = _base(_command("show version"))
        _write(tmp_path, "show_version.txt", "NEW\n")
        cmd = resolve_overlay(str(tmp_path), base, override_commands="all")["show version"]
        assert cmd.source is not None
        assert cmd.source["overlay_file"] == "show_version.txt"
        assert cmd.source["raw"] == "show version.raw"  # base provenance preserved

    def test_variants_dropped_logs_info(self, tmp_path, caplog):
        base = _base(
            _command(
                "show version",
                output=_literal("v1\n"),
                variants=(("variant_1", _literal("v1\n")), ("variant_2", _literal("v2\n"))),
            )
        )
        _write(tmp_path, "show_version.txt", "NEW\n")
        with caplog.at_level(logging.INFO, logger="simnos.core.overlay_loader"):
            cmd = resolve_overlay(str(tmp_path), base, override_commands="all")["show version"]
        assert cmd.variants == ()
        assert any("drops" in r.getMessage() and "variant" in r.getMessage() for r in caplog.records)


class TestNewCommand:
    def test_new_command_is_all_modes_custom(self, tmp_path):
        base = _base(_command("show version"))
        _write(tmp_path, "show_run.txt", "running-config\n")
        cmd = resolve_overlay(str(tmp_path), base, override_commands=["show run"])["show run"]
        assert cmd.name == "show run"
        assert cmd.modes == frozenset()  # empty = valid in every mode
        assert cmd.new_mode is None
        assert cmd.exit is False
        assert cmd.variants == ()
        assert cmd.type == "custom"
        assert cmd.output.text == "running-config\n"
        assert cmd.source == {"overlay_file": "show_run.txt"}


class TestTemplateOverlay:
    def test_base_prompt_only_template_is_allowed(self, tmp_path):
        base = _base(_command("show version"))
        _write(tmp_path, "show_version.j2", "prompt is {{ base_prompt }}\n")
        cmd = resolve_overlay(str(tmp_path), base, override_commands="all")["show version"]
        assert cmd.output.kind == "template"
        assert cmd.output.render("R1") == "prompt is R1\n"

    def test_facts_bearing_template_is_loud_fail(self, tmp_path):
        base = _base(_command("show version"))
        _write(tmp_path, "show_version.j2", "hostname {{ hostname }}\n")
        with pytest.raises(ValueError, match=r"needs host facts.*hostname.*#287"):
            resolve_overlay(str(tmp_path), base, override_commands="all")


class TestLoudFailGuards:
    def test_listed_command_with_no_file_is_loud(self, tmp_path):
        base = _base(_command("show version"))
        with pytest.raises(ValueError, match=r"no show_version.txt / show_version.j2 was found"):
            resolve_overlay(str(tmp_path), base, override_commands=["show version"])

    def test_same_stem_txt_and_j2_collision_is_loud(self, tmp_path):
        base = _base(_command("show version"))
        _write(tmp_path, "show_version.txt", "txt\n")
        _write(tmp_path, "show_version.j2", "{{ base_prompt }}\n")
        with pytest.raises(ValueError, match=r"resolves to multiple files"):
            resolve_overlay(str(tmp_path), base, override_commands="all")

    def test_map_missing_file_is_loud(self, tmp_path):
        base = _base(_command("show version"))
        with pytest.raises(ValueError, match=r"maps to .*does not exist"):
            resolve_overlay(str(tmp_path), base, override_commands={"show version": "absent.txt"})

    def test_map_path_traversal_is_rejected(self, tmp_path):
        base = _base(_command("show version"))
        with pytest.raises(ValueError, match=r"must be a bare filename"):
            resolve_overlay(str(tmp_path), base, override_commands={"show version": "../escape.txt"})

    def test_map_bad_extension_is_rejected(self, tmp_path):
        base = _base(_command("show version"))
        _write(tmp_path, "show_version.csv", "nope\n")
        with pytest.raises(ValueError, match=r"must end with .txt or .j2"):
            resolve_overlay(str(tmp_path), base, override_commands={"show version": "show_version.csv"})
