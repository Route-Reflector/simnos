"""Unit tests for the A3 platform data lint (#264 / D8, D9, tasks.check_platform_data)."""

from tasks import check_platform_data


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


def test_absent_dir_is_clean(tmp_path):
    # No platforms dir at all (the state before any A3 migration) is not an error.
    assert check_platform_data(str(tmp_path / "nonexistent")) == []
