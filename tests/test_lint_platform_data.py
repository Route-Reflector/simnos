"""Unit tests for the A3 platform data lint (#264 / D8, D9 + #276 ratchet).

Covers `tasks.check_platform_data` (data conventions),
`tasks.check_platform_data_warnings` (warning tier) and
`tasks.check_platform_data_ratchet` (authoring baseline ratchet). The ratchet
tests follow the deleted `tests/test_lint_platform_yaml.py` (#244): the real
repo passes against the shipped baseline, and negative assets prove each rule
actually fails — without these a bug in the lint logic would read as
"everything is clean" forever.
"""

from tasks import (
    check_platform_data,
    check_platform_data_ratchet,
    check_platform_data_warnings,
    is_stub_help,
)


def _write(path, content, *, binary=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    if binary:
        path.write_bytes(content)
    else:
        path.write_text(content, encoding="utf-8")


def _platform(tmp_path, name="p"):
    commands = tmp_path / name / "commands"
    commands.mkdir(parents=True)
    return commands


class TestEncoding:
    def test_clean_data_passes(self, tmp_path):
        commands = _platform(tmp_path)
        _write(commands / "show.yaml", "command: show\ntype: ntc\noutput: show.txt\n")
        _write(commands / "show.txt", "ok\n")
        assert check_platform_data(str(tmp_path)) == []

    def test_crlf_flagged(self, tmp_path):
        commands = _platform(tmp_path)
        _write(commands / "show.yaml", "command: show\ntype: ntc\noutput: show.txt\n")
        _write(commands / "show.txt", b"ok\r\n", binary=True)
        violations = check_platform_data(str(tmp_path))
        assert any("CR" in v for v in violations)

    def test_missing_trailing_newline_flagged(self, tmp_path):
        commands = _platform(tmp_path)
        _write(commands / "show.yaml", "command: show\ntype: ntc\noutput: show.txt\n")
        _write(commands / "show.txt", "no newline")
        violations = check_platform_data(str(tmp_path))
        assert any("trailing newline" in v for v in violations)

    def test_invalid_utf8_flagged(self, tmp_path):
        commands = _platform(tmp_path)
        _write(commands / "show.yaml", "command: show\ntype: ntc\noutput: show.txt\n")
        _write(commands / "show.txt", b"\xff\xfe bad\n", binary=True)
        violations = check_platform_data(str(tmp_path))
        assert any("UTF-8" in v for v in violations)


class TestReferences:
    def test_orphan_output_flagged(self, tmp_path):
        commands = _platform(tmp_path)
        _write(commands / "show.yaml", "command: show\ntype: ntc\n")  # no output ref
        _write(commands / "stray.txt", "orphan\n")
        violations = check_platform_data(str(tmp_path))
        assert any("orphan" in v for v in violations)

    def test_shared_reference_flagged(self, tmp_path):
        commands = _platform(tmp_path)
        _write(commands / "a.yaml", "command: a\ntype: ntc\noutput: shared.txt\n")
        _write(commands / "b.yaml", "command: b\ntype: ntc\noutput: shared.txt\n")
        _write(commands / "shared.txt", "x\n")
        violations = check_platform_data(str(tmp_path))
        assert any("1 yaml : 1 output" in v for v in violations)

    def test_missing_referenced_file_flagged(self, tmp_path):
        commands = _platform(tmp_path)
        _write(commands / "a.yaml", "command: a\ntype: ntc\noutput: ghost.txt\n")
        violations = check_platform_data(str(tmp_path))
        assert any("missing" in v for v in violations)


class TestConventions:
    def test_stray_yml_flagged(self, tmp_path):
        commands = _platform(tmp_path)
        _write(commands / "a.yml", "command: a\ntype: ntc\n")  # .yml, not .yaml
        violations = check_platform_data(str(tmp_path))
        assert any(".yml" in v for v in violations)

    def test_literal_output_with_j2_extension_flagged(self, tmp_path):
        commands = _platform(tmp_path)
        _write(commands / "a.yaml", "command: a\ntype: ntc\noutput: a.j2\n")
        _write(commands / "a.j2", "x\n")
        violations = check_platform_data(str(tmp_path))
        assert any("literal output" in v and ".j2" in v for v in violations)

    def test_variant_with_j2_extension_flagged(self, tmp_path):
        commands = _platform(tmp_path)
        _write(
            commands / "a.yaml",
            "command: a\ntype: ntc\nvariants:\n  - name: default\n    output: a.j2\n",
        )
        _write(commands / "a.j2", "x\n")
        violations = check_platform_data(str(tmp_path))
        assert any("literal output" in v for v in violations)

    def test_output_template_non_j2_flagged(self, tmp_path):
        commands = _platform(tmp_path)
        _write(commands / "a.yaml", "command: a\ntype: ntc\noutput_template: a.txt\n")
        _write(commands / "a.txt", "x\n")
        violations = check_platform_data(str(tmp_path))
        assert any("output_template" in v and "must use .j2" in v for v in violations)


def test_absent_dir_is_clean(tmp_path):
    # No platforms dir at all (the state before any A3 migration) is not an error.
    assert check_platform_data(str(tmp_path / "nonexistent")) == []


class TestWarnings:
    """Warning-tier conventions (#264 / D9): filename + type:ntc provenance.

    These never gate (`check_platform_data` stays empty); they are surfaced by
    `check_platform_data_warnings` for the maintainer.
    """

    def test_clean_data_has_no_warnings(self, tmp_path):
        commands = _platform(tmp_path)
        _write(commands / "show_version.yaml", "command: show version\ntype: simnos\noutput: show_version.txt\n")
        _write(commands / "show_version.txt", "ok\n")
        assert check_platform_data_warnings(str(tmp_path)) == []

    def test_filename_mismatch_warned(self, tmp_path):
        commands = _platform(tmp_path)
        # stem `wrong` does not match the sanitized command `show version`.
        _write(commands / "wrong.yaml", "command: show version\ntype: simnos\noutput: wrong.txt\n")
        _write(commands / "wrong.txt", "ok\n")
        warnings = check_platform_data_warnings(str(tmp_path))
        assert any("filename does not match command" in w and "show_version" in w for w in warnings)

    def test_collision_suffix_filename_is_not_warned(self, tmp_path):
        commands = _platform(tmp_path)
        # the deterministic `__2` collision suffix is an accepted stem shape.
        _write(commands / "show_version__2.yaml", "command: show version\ntype: simnos\noutput: show_version__2.txt\n")
        _write(commands / "show_version__2.txt", "ok\n")
        assert check_platform_data_warnings(str(tmp_path)) == []

    def test_ntc_without_source_warned(self, tmp_path):
        commands = _platform(tmp_path)
        _write(commands / "show_version.yaml", "command: show version\ntype: ntc\noutput: show_version.txt\n")
        _write(commands / "show_version.txt", "ok\n")
        warnings = check_platform_data_warnings(str(tmp_path))
        assert any("type: ntc but no `source`" in w for w in warnings)

    def test_ntc_with_source_not_warned(self, tmp_path):
        commands = _platform(tmp_path)
        _write(
            commands / "show_version.yaml",
            "command: show version\ntype: ntc\nsource:\n  ntc_template: t\n  ntc_commit: c\noutput: show_version.txt\n",
        )
        _write(commands / "show_version.txt", "ok\n")
        assert check_platform_data_warnings(str(tmp_path)) == []


class TestIsStubHelp:
    """Pin the stub-help classification (#244 / P-13, ported in #276)."""

    def test_lowercase_execute_prefix_is_stub(self):
        assert is_stub_help('execute the command "show version"')

    def test_capitalized_execute_prefix_is_stub(self):
        assert is_stub_help("Execute the command terminal width 511. This automatically generated.")

    def test_automatically_generated_marker_is_stub(self):
        assert is_stub_help("Anything mentioning This automatically generated. counts")

    def test_real_help_is_not_stub(self):
        assert not is_stub_help("enter enable mode")


class TestRatchet:
    """Baseline-ratchet rules of `check_platform_data_ratchet` (#276).

    Ported from the deleted `tests/test_lint_platform_yaml.py` (#244),
    re-keyed for A3: baseline keys are platform names, stub identity sets
    hold `command` field values.
    """

    EMPTY_BASELINE = "missing_default: []\nstub_help: {}\n"

    def _baseline(self, tmp_path, content=EMPTY_BASELINE):
        path = tmp_path / "baseline.yaml"
        path.write_text(content, encoding="utf-8")
        return str(path)

    def _clean_platform(self, tmp_path, name="p"):
        commands = _platform(tmp_path, name)
        _write(commands / "_default_.yaml", "command: _default_\nhelp: default output for unknown commands\n")
        _write(commands / "show_clock.yaml", "command: show clock\nhelp: Display the system clock\n")
        return commands

    def test_real_repo_is_clean(self):
        """The shipped baseline matches the shipped A3 platform data."""
        assert check_platform_data_ratchet() == []

    def test_clean_platform_passes(self, tmp_path):
        self._clean_platform(tmp_path)
        assert check_platform_data_ratchet(str(tmp_path), self._baseline(tmp_path)) == []

    def test_missing_default_outside_baseline_fails(self, tmp_path):
        """Rule 1: a new platform without `_default_` is rejected."""
        commands = _platform(tmp_path)
        _write(commands / "show_clock.yaml", "command: show clock\nhelp: Display the system clock\n")
        violations = check_platform_data_ratchet(str(tmp_path), self._baseline(tmp_path))
        assert any("missing '_default_'" in v for v in violations)

    def test_new_stub_help_fails_even_when_another_stub_is_fixed(self, tmp_path):
        """Rule 2: identity set, not a count — swaps cannot slip through.

        Pins the #244 2nd round 🦊#1 scenario: baseline froze `old cmd` as a
        stub; the PR fixes it but adds `new cmd` with a stub. A per-platform
        count would balance out; the identity set fails both directions.
        """
        commands = self._clean_platform(tmp_path)
        _write(commands / "new_cmd.yaml", 'command: new cmd\nhelp: execute the command "new cmd"\n')
        baseline = self._baseline(tmp_path, "missing_default: []\nstub_help:\n  p:\n  - old cmd\n")
        violations = check_platform_data_ratchet(str(tmp_path), baseline)
        assert any("'new cmd' adds an auto-generated stub help" in v for v in violations)
        assert any("'old cmd' no longer has a stub help" in v for v in violations)

    def test_heritage_sentence_fails_on_parsed_help(self, tmp_path):
        """Rule 3: detection works on parsed values, so folding cannot hide it.

        The sentence is authored folded across two lines — a raw-text grep
        misses it (this fooled four independent measurements during the #244
        design round), the parsed check does not.
        """
        commands = self._clean_platform(tmp_path)
        _write(
            commands / "legacy_cmd.yaml",
            "command: legacy cmd\n"
            "help: Execute the command legacy. This automatically generated. Feel\n"
            "  free to change it!\n",
        )
        baseline = self._baseline(tmp_path, "missing_default: []\nstub_help:\n  p:\n  - legacy cmd\n")
        violations = check_platform_data_ratchet(str(tmp_path), baseline)
        assert any("still contains 'Feel free to change it!'" in v for v in violations)

    def test_stale_baseline_entry_fails(self, tmp_path):
        """Rule 4: a baseline entry for a removed platform must be cleaned up."""
        self._clean_platform(tmp_path)
        baseline = self._baseline(tmp_path, "missing_default:\n- gone_platform\nstub_help: {}\n")
        violations = check_platform_data_ratchet(str(tmp_path), baseline)
        assert any("not an A3 platform with command data" in v for v in violations)

    def test_fixed_default_still_in_baseline_fails(self, tmp_path):
        """Rule 5: improving a platform forces shrinking the baseline in the same PR.

        Without this, a forgotten baseline entry would let the violation
        grow back unnoticed later (#244 2nd round 🦊#2).
        """
        self._clean_platform(tmp_path)
        baseline = self._baseline(tmp_path, "missing_default:\n- p\nstub_help: {}\n")
        violations = check_platform_data_ratchet(str(tmp_path), baseline)
        assert any("still listed under missing_default" in v for v in violations)

    def test_fixed_stub_still_in_baseline_fails(self, tmp_path):
        """Rule 5 (stub side): a fixed stub left in the baseline must shrink.

        The mirror of `test_fixed_default_still_in_baseline_fails` for the
        stub_help channel — the platform has no stub help anymore but the
        baseline still freezes one, so the entry has to be removed (#276 1st
        round 🦊#3). The swap test exercises this direction too, but a
        standalone case keeps the rule-5 stub regression readable in isolation.
        """
        self._clean_platform(tmp_path)
        baseline = self._baseline(tmp_path, "missing_default: []\nstub_help:\n  p:\n  - show clock\n")
        violations = check_platform_data_ratchet(str(tmp_path), baseline)
        assert any("'show clock' no longer has a stub help" in v for v in violations)

    def test_wrong_path_fires_stale_entries(self, tmp_path):
        """A typo'd platforms dir is not a silent pass.

        The ratchet has no empty-glob self-guard (the `lint_platform_data`
        task owns that via `list_a3_platform_names()`), but a wrong dir
        against the shipped-style baseline still fails loudly: every baseline
        platform is unseen, so rule 4 fires per entry (#276 1st round 🦊#2 / 🐙#3).
        """
        baseline = self._baseline(tmp_path, "missing_default:\n- alcatel_aos\nstub_help:\n  cisco_ios:\n  - show foo\n")
        violations = check_platform_data_ratchet(str(tmp_path / "nonexistent"), baseline)
        assert any("alcatel_aos" in v and "not an A3 platform" in v for v in violations)
        assert any("cisco_ios" in v and "not an A3 platform" in v for v in violations)
