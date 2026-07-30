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
    _RENDER_VAR_NAMES,
    check_platform_data,
    check_platform_data_device_type_collisions,
    check_platform_data_py_modules,
    check_platform_data_ratchet,
    check_platform_data_render_leaks,
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


class TestRenderLeaks:
    """Render-variable leak guard for literal ``.txt`` outputs (#329).

    Pins both halves of the issue's contract: the #328 regression class
    (``{base_prompt}`` served verbatim from a literal file) is caught, and the
    real-device literal braces the issue catalogued (hp_comware ``{ACDEF}``,
    juniper ``{master}``, cisco crypto ``flags={...}``) stay false-positive-free.
    """

    def test_single_brace_leak_flagged(self, tmp_path):
        # The exact #328 shape: str.format heritage moved verbatim into .txt.
        commands = _platform(tmp_path)
        _write(commands / "show_hostname.yaml", "command: show hostname\ntype: simnos\noutput: show_hostname.txt\n")
        _write(commands / "show_hostname.txt", "Hostname: {base_prompt}\n")
        violations = check_platform_data_render_leaks(str(tmp_path))
        assert len(violations) == 1
        assert "show_hostname.txt:1" in violations[0]
        assert "{base_prompt}" in violations[0]

    def test_double_brace_leak_flagged(self, tmp_path):
        # The jinja spelling in a literal file is the same authoring mistake.
        commands = _platform(tmp_path)
        _write(commands / "show.yaml", "command: show\ntype: simnos\noutput: show.txt\n")
        _write(commands / "show.txt", "line one\n{{ base_prompt }} uptime is 1 day\n")
        violations = check_platform_data_render_leaks(str(tmp_path))
        assert len(violations) == 1
        assert "show.txt:2" in violations[0]

    def test_jinja_filter_and_format_spec_flagged(self, tmp_path):
        # A trailing jinja filter / format spec is the same unsubstituted leak
        # (1st round codex #1): the expression *starts* with the render var.
        commands = _platform(tmp_path)
        _write(commands / "show.yaml", "command: show\ntype: simnos\noutput: show.txt\n")
        _write(
            commands / "show.txt",
            "{{ base_prompt | upper }} ready\npadded: {base_prompt:<20}|\n{{- base_prompt -}} trimmed\n",
        )
        violations = check_platform_data_render_leaks(str(tmp_path))
        assert len(violations) == 3
        assert "show.txt:1" in violations[0]
        assert "show.txt:2" in violations[1]
        # jinja whitespace-control is a valid spelling of the same leak
        # (2nd round codex #1).
        assert "show.txt:3" in violations[2]

    def test_similar_identifier_not_flagged(self, tmp_path):
        # `\b` pins the name as a whole identifier: `base_prompt_style` is a
        # different token and must not trip the guard.
        commands = _platform(tmp_path)
        _write(commands / "show.yaml", "command: show\ntype: simnos\noutput: show.txt\n")
        _write(commands / "show.txt", "style is {base_prompt_style} today\n")
        assert check_platform_data_render_leaks(str(tmp_path)) == []

    def test_broken_encoding_does_not_crash_and_still_reports(self, tmp_path):
        # errors="replace" contract (docstring): a broken encoding is the
        # encoding gate's violation, but this pass must survive the file and
        # still report the leak with the right line number (1st round codex #2).
        commands = _platform(tmp_path)
        _write(commands / "show.yaml", "command: show\ntype: simnos\noutput: show.txt\n")
        _write(commands / "show.txt", b"\xff\xfe garbage\n{base_prompt}\n", binary=True)
        violations = check_platform_data_render_leaks(str(tmp_path))
        assert len(violations) == 1
        assert "show.txt:2" in violations[0]

    def test_username_challenge_var_flagged(self, tmp_path):
        # `username` is a CHALLENGE_RENDER_VARS member and equally has no
        # legitimate braced reading in a literal file.
        commands = _platform(tmp_path)
        _write(commands / "sudo.yaml", "command: sudo -s\ntype: simnos\noutput: sudo.txt\n")
        _write(commands / "sudo.txt", "[sudo] password for {username}:\n")
        violations = check_platform_data_render_leaks(str(tmp_path))
        assert len(violations) == 1
        assert "{username}" in violations[0]

    def test_real_device_literal_braces_pass(self, tmp_path):
        # The false-positive catalogue from #329: real devices print these
        # braces literally and a naive "any `{` in .txt" rule would flag them.
        commands = _platform(tmp_path)
        _write(commands / "display.yaml", "command: display link-aggregation\ntype: simnos\noutput: display.txt\n")
        _write(
            commands / "display.txt",
            "Flag: {ACDEF} {ACG} {EF}\n"
            "flags={origin_is_acl,}\n"
            "current outbound spi: 0x0(0), flags={Transport UDP-Encaps, }\n"
            "{master}\n"
            "idle{idle: cpu7}\n",
        )
        assert check_platform_data_render_leaks(str(tmp_path)) == []

    def test_j2_channel_is_exempt(self, tmp_path):
        # `.j2` is the render channel — `{{ base_prompt }}` there is the point.
        commands = _platform(tmp_path)
        _write(commands / "show.yaml", "command: show\ntype: simnos\noutput_template: show.j2\n")
        _write(commands / "show.j2", "{{ base_prompt }} uptime is 1 day\n")
        assert check_platform_data_render_leaks(str(tmp_path)) == []

    def test_real_repo_is_clean(self):
        # Zero leaks in the shipped data is what makes this check safe to gate.
        assert check_platform_data_render_leaks() == []

    def test_var_names_stay_in_sync_with_loader(self):
        # tasks.py hardcodes the names (it must stay simnos-import-free, #264 /
        # D1); this pin is the sync contract — adding a render variable to the
        # loader without extending the lint fails here, not in production.
        from simnos.core.resolved_command import CHALLENGE_RENDER_VARS, KNOWN_RENDER_VARS

        assert set(_RENDER_VAR_NAMES) == set(KNOWN_RENDER_VARS | CHALLENGE_RENDER_VARS)


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


class TestDeviceTypeCollisions:
    """#266 / D2: device_type alias collisions across platforms are gated.

    Mirrors the runtime reverse-index guard in `simnos.plugins.nos`; these
    pin that the authoring-time lint catches the same conflicts (and does NOT
    false-positive on the `name == netmiko == ntc` shape every platform ships
    today, which a naive "key already seen" check would).
    """

    @staticmethod
    def _meta(tmp_path, name, *, netmiko=None, ntc=None):
        d = tmp_path / name
        d.mkdir(parents=True, exist_ok=True)
        lines = []
        if netmiko is not None:
            lines.append(f"netmiko_device_type: {netmiko}")
        if ntc is not None:
            lines.append(f"ntc_platform: {ntc}")
        (d / "platform.yaml").write_text(("\n".join(lines) + "\n") if lines else "{}\n", encoding="utf-8")

    def test_distinct_platforms_pass(self, tmp_path):
        self._meta(tmp_path, "edgecore", netmiko="edgecore_sonic", ntc="edgecore")
        self._meta(tmp_path, "cisco_ios", netmiko="cisco_ios", ntc="cisco_ios")
        assert check_platform_data_device_type_collisions(str(tmp_path)) == []

    def test_identity_equals_aliases_is_noop(self, tmp_path):
        # name == netmiko == ntc (today's common case) must NOT false-positive.
        self._meta(tmp_path, "cisco_ios", netmiko="cisco_ios", ntc="cisco_ios")
        assert check_platform_data_device_type_collisions(str(tmp_path)) == []

    def test_two_platforms_share_netmiko_alias_flagged(self, tmp_path):
        self._meta(tmp_path, "p_a", netmiko="shared_dt")
        self._meta(tmp_path, "p_b", netmiko="shared_dt")
        violations = check_platform_data_device_type_collisions(str(tmp_path))
        assert any("shared_dt" in v for v in violations)

    def test_alias_colliding_with_other_identity_flagged(self, tmp_path):
        # p_b's netmiko alias lands on p_a's identity name (2nd round gemini #3).
        self._meta(tmp_path, "p_a")
        self._meta(tmp_path, "p_b", netmiko="p_a")
        violations = check_platform_data_device_type_collisions(str(tmp_path))
        assert any("p_a" in v for v in violations)

    def test_malformed_platform_yaml_is_violation_not_crash(self, tmp_path):
        # A malformed platform.yaml yields a violation string, not a traceback —
        # symmetric with the runtime index guard's warn+skip (1st round PR1
        # cross-review gemini #6 / claude #4).
        d = tmp_path / "broken"
        d.mkdir(parents=True)
        (d / "platform.yaml").write_text("netmiko_device_type: [unclosed\n", encoding="utf-8")
        violations = check_platform_data_device_type_collisions(str(tmp_path))
        assert any("broken/platform.yaml" in v for v in violations)

    def test_non_mapping_platform_yaml_is_violation(self, tmp_path):
        # A platform.yaml that parses to a non-mapping (e.g. a bare list) is a
        # violation, not an AttributeError on `.get`.
        d = tmp_path / "listy"
        d.mkdir(parents=True)
        (d / "platform.yaml").write_text("- just\n- a\n- list\n", encoding="utf-8")
        violations = check_platform_data_device_type_collisions(str(tmp_path))
        assert any("listy/platform.yaml" in v and "not a mapping" in v for v in violations)


class TestPyModules:
    """#317 P-4: py handler modules cross-checked against the A3 platforms.

    Layout mirrors the package tree: `<root>/platforms/<name>/` (A3 dirs) next
    to `<root>/platforms_py/<name>.py` (handler modules); the check derives the
    py dir as the platforms dir's sibling.
    """

    @staticmethod
    def _tree(tmp_path):
        platforms = tmp_path / "platforms"
        platforms.mkdir()
        (tmp_path / "platforms_py").mkdir()
        return platforms

    @staticmethod
    def _a3(platforms, name, *, command_yaml=None):
        commands = platforms / name / "commands"
        commands.mkdir(parents=True)
        (platforms / name / "platform.yaml").write_text(
            'modes:\n  user:\n    prompt: "{{ base_prompt }}>"\ninitial_mode: user\n', encoding="utf-8"
        )
        if command_yaml is not None:
            (commands / "cmd.yaml").write_text(command_yaml, encoding="utf-8")

    def test_matched_module_and_handler_pass(self, tmp_path):
        platforms = self._tree(tmp_path)
        self._a3(platforms, "p_a", command_yaml="command: show x\ntype: simnos\nhandler: make_x\n")
        (tmp_path / "platforms_py" / "p_a.py").write_text("# handlers\n", encoding="utf-8")
        assert check_platform_data_py_modules(str(platforms)) == []

    def test_orphan_py_module_flagged(self, tmp_path):
        platforms = self._tree(tmp_path)
        self._a3(platforms, "p_a")
        (tmp_path / "platforms_py" / "ghost.py").write_text("# no A3 dir\n", encoding="utf-8")
        violations = check_platform_data_py_modules(str(platforms))
        assert any("platforms_py/ghost.py" in v and "no matching A3 platform dir" in v for v in violations)

    def test_init_py_is_not_an_orphan(self, tmp_path):
        platforms = self._tree(tmp_path)
        (tmp_path / "platforms_py" / "__init__.py").write_text("", encoding="utf-8")
        assert check_platform_data_py_modules(str(platforms)) == []

    def test_handler_ref_without_py_module_flagged(self, tmp_path):
        platforms = self._tree(tmp_path)
        self._a3(platforms, "p_a", command_yaml="command: show x\ntype: simnos\nhandler: make_x\n")
        violations = check_platform_data_py_modules(str(platforms))
        assert any("handler: make_x" in v and "no platforms_py/p_a.py" in v for v in violations)

    def test_static_only_platform_without_py_module_passes(self, tmp_path):
        platforms = self._tree(tmp_path)
        self._a3(platforms, "p_a", command_yaml="command: show x\ntype: simnos\n")
        assert check_platform_data_py_modules(str(platforms)) == []
