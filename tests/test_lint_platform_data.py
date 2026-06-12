"""Unit tests for the A3 platform data lint (#264 / D8, D9, tasks.check_platform_data)."""

from tasks import check_platform_data, check_platform_data_warnings


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
