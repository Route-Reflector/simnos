"""Unit tests for the A3 platform directory loader (#264 / P1-1 D6).

These build small A3 platform directories on tmp_path and assert the loader
normalizes them into `ResolvedPlatform` / `ResolvedCommand`, and that every
load-time validation (Decision 7) fails loudly. The shipped-data equivalence is
covered separately by the migration oracle; here we pin the loader contract in
isolation.
"""

import pytest

from simnos.core.platform_loader import load_platform_dir


@pytest.fixture(autouse=True)
def _clear_loader_cache():
    """Isolate the module-level load_platform_dir cache between tests."""
    load_platform_dir.cache_clear()
    yield
    load_platform_dir.cache_clear()


def _write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _platform(tmp_path, *, modes=None, initial_mode="user"):
    """Create a minimal platform dir; return its path + the commands dir."""
    modes = modes or {"user": "{{ base_prompt }}>", "enable": "{{ base_prompt }}#"}
    root = tmp_path / "myplat"
    lines = ["modes:"]
    for name, prompt in modes.items():
        lines.append(f"  {name}:")
        lines.append(f'    prompt: "{prompt}"')
    lines.append(f"initial_mode: {initial_mode}")
    _write(root / "platform.yaml", "\n".join(lines) + "\n")
    (root / "commands").mkdir(parents=True, exist_ok=True)
    return root, root / "commands"


def _cmd(commands_dir, filename, yaml_text, *, output_files=None):
    _write(commands_dir / filename, yaml_text)
    for name, content in (output_files or {}).items():
        _write(commands_dir / name, content)


class TestLoadHappyPath:
    def test_literal_output_and_modes(self, tmp_path):
        root, commands = _platform(tmp_path)
        _cmd(
            commands,
            "show_version.yaml",
            "command: show version\ntype: ntc\nmode: [user, enable]\noutput: show_version.txt\n",
            output_files={"show_version.txt": "Cisco IOS\n"},
        )
        platform = load_platform_dir(str(root))
        cmd = platform.commands["show version"]
        assert cmd.modes == frozenset({"user", "enable"})
        assert cmd.output.kind == "literal"
        assert cmd.output.render("R1") == "Cisco IOS\n"
        assert cmd.type == "ntc"
        assert platform.initial_mode == "user"
        assert platform.modes["user"].render_prompt("R1") == "R1>"

    def test_template_output_carries_required_vars(self, tmp_path):
        root, commands = _platform(tmp_path)
        _cmd(
            commands,
            "scripting.yaml",
            "command: set scripting\ntype: simnos\noutput_template: scripting.j2\n",
            output_files={"scripting.j2": "{{ base_prompt }} ready for {{ hostname }}\n"},
        )
        cmd = load_platform_dir(str(root)).commands["set scripting"]
        assert cmd.output.kind == "template"
        # base_prompt is excluded; the host fact `hostname` is carried for #265.
        assert cmd.output.required_vars == frozenset({"hostname"})

    def test_template_renders_base_prompt_only(self, tmp_path):
        root, commands = _platform(tmp_path)
        _cmd(
            commands,
            "banner.yaml",
            "command: banner\ntype: simnos\noutput_template: banner.j2\n",
            output_files={"banner.j2": "welcome to {{ base_prompt }}\n"},
        )
        cmd = load_platform_dir(str(root)).commands["banner"]
        assert cmd.output.required_vars == frozenset()
        assert cmd.output.render("R1") == "welcome to R1\n"

    def test_omitted_mode_means_all_modes(self, tmp_path):
        root, commands = _platform(tmp_path)
        _cmd(
            commands,
            "ping.yaml",
            "command: ping\ntype: simnos\noutput: ping.txt\n",
            output_files={"ping.txt": "ok\n"},
        )
        cmd = load_platform_dir(str(root)).commands["ping"]
        assert cmd.modes == frozenset()

    def test_no_output_command(self, tmp_path):
        root, commands = _platform(tmp_path)
        _cmd(commands, "enable.yaml", "command: enable\ntype: simnos\nmode: [user]\nnew_mode: enable\n")
        cmd = load_platform_dir(str(root)).commands["enable"]
        assert cmd.output.kind == "none"
        assert cmd.new_mode == "enable"

    def test_variants_primary_is_first(self, tmp_path):
        root, commands = _platform(tmp_path)
        _cmd(
            commands,
            "show_ver.yaml",
            (
                "command: show ver\ntype: ntc\nvariants:\n"
                "  - name: default\n    output: a.txt\n  - name: asr\n    output: b.txt\n"
            ),
            output_files={"a.txt": "AAA\n", "b.txt": "BBB\n"},
        )
        cmd = load_platform_dir(str(root)).commands["show ver"]
        assert cmd.output.render("R1") == "AAA\n"  # variants[0] is primary
        assert [name for name, _ in cmd.variants] == ["default", "asr"]
        assert cmd.variants[1][1].render("R1") == "BBB\n"

    def test_default_is_mode_agnostic(self, tmp_path):
        root, commands = _platform(tmp_path)
        _cmd(
            commands,
            "default.yaml",
            "command: _default_\ntype: simnos\noutput: d.txt\n",
            output_files={"d.txt": "% Invalid\n"},
        )
        cmd = load_platform_dir(str(root)).commands["_default_"]
        assert cmd.modes == frozenset()

    def test_alias_carries_target_dispatch_keeps_own_help(self, tmp_path):
        root, commands = _platform(tmp_path)
        _cmd(
            commands,
            "sh_ver.yaml",
            "command: show version\ntype: ntc\nmode: [user]\noutput: v.txt\n",
            output_files={"v.txt": "V\n"},
        )
        _cmd(commands, "alias.yaml", "command: sh ver\nalias: show version\nhelp: abbrev for show version\n")
        platform = load_platform_dir(str(root))
        alias = platform.commands["sh ver"]
        assert alias.output.render("R1") == "V\n"  # target's dispatch
        assert alias.modes == frozenset({"user"})
        assert alias.help == "abbrev for show version"  # own help
        assert alias.name == "sh ver"


class TestLoadRejections:
    def test_duplicate_command(self, tmp_path):
        root, commands = _platform(tmp_path)
        _cmd(commands, "a.yaml", "command: show version\ntype: ntc\noutput: a.txt\n", output_files={"a.txt": "A\n"})
        _cmd(commands, "b.yaml", "command: show version\ntype: ntc\noutput: b.txt\n", output_files={"b.txt": "B\n"})
        with pytest.raises(ValueError, match="duplicate command"):
            load_platform_dir(str(root))

    def test_unknown_mode(self, tmp_path):
        root, commands = _platform(tmp_path)
        _cmd(commands, "a.yaml", "command: x\ntype: ntc\nmode: [bogus]\n")
        with pytest.raises(ValueError, match="not in platform modes"):
            load_platform_dir(str(root))

    def test_unknown_new_mode(self, tmp_path):
        root, commands = _platform(tmp_path)
        _cmd(commands, "a.yaml", "command: x\ntype: ntc\nnew_mode: bogus\n")
        with pytest.raises(ValueError, match="new_mode"):
            load_platform_dir(str(root))

    def test_missing_output_file(self, tmp_path):
        root, commands = _platform(tmp_path)
        _cmd(commands, "a.yaml", "command: x\ntype: ntc\noutput: ghost.txt\n")
        with pytest.raises(ValueError, match="not found"):
            load_platform_dir(str(root))

    def test_bad_template_syntax(self, tmp_path):
        root, commands = _platform(tmp_path)
        _cmd(
            commands,
            "a.yaml",
            "command: x\ntype: ntc\noutput_template: bad.j2\n",
            output_files={"bad.j2": "{{ unclosed\n"},
        )
        with pytest.raises(ValueError, match="syntax error"):
            load_platform_dir(str(root))

    def test_prompt_unknown_variable(self, tmp_path):
        root, commands = _platform(tmp_path, modes={"user": "{{ base_prompt }}{{ junk }}>"})
        _cmd(commands, "a.yaml", "command: x\ntype: ntc\n")
        with pytest.raises(ValueError, match="only base_prompt is allowed"):
            load_platform_dir(str(root))

    def test_alias_cycle(self, tmp_path):
        root, commands = _platform(tmp_path)
        _cmd(commands, "a.yaml", "command: a\nalias: b\n")
        _cmd(commands, "b.yaml", "command: b\nalias: a\n")
        with pytest.raises(ValueError, match="cycle"):
            load_platform_dir(str(root))

    def test_alias_unknown_target(self, tmp_path):
        root, commands = _platform(tmp_path)
        _cmd(commands, "a.yaml", "command: a\nalias: ghost\n")
        with pytest.raises(ValueError, match="unknown target"):
            load_platform_dir(str(root))

    def test_missing_platform_yaml(self, tmp_path):
        root = tmp_path / "noplat"
        (root / "commands").mkdir(parents=True)
        with pytest.raises(ValueError, match="required file not found"):
            load_platform_dir(str(root))

    def test_missing_commands_dir(self, tmp_path):
        root = tmp_path / "p"
        _write(root / "platform.yaml", 'modes:\n  user:\n    prompt: "{{ base_prompt }}>"\ninitial_mode: user\n')
        with pytest.raises(ValueError, match="commands directory not found"):
            load_platform_dir(str(root))


class TestLoadCache:
    def test_repeated_load_returns_cached_object(self, tmp_path):
        root, commands = _platform(tmp_path)
        _cmd(commands, "x.yaml", "command: x\ntype: ntc\noutput: x.txt\n", output_files={"x.txt": "v\n"})
        first = load_platform_dir(str(root))
        second = load_platform_dir(str(root))
        assert first is second  # shared parse, not re-read

    def test_cache_clear_forces_reparse(self, tmp_path):
        root, commands = _platform(tmp_path)
        _cmd(commands, "x.yaml", "command: x\ntype: ntc\noutput: x.txt\n", output_files={"x.txt": "v\n"})
        first = load_platform_dir(str(root))
        load_platform_dir.cache_clear()
        assert load_platform_dir(str(root)) is not first
