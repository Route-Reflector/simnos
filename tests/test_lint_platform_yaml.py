"""Self-tests for the platform yaml conventions lint (#244 / D2 + D4).

Two layers:
- the real repo passes the lint (the baseline matches reality), and
- negative assets prove each ratchet rule actually fails — without these
  a bug in the lint logic would read as "everything is clean" forever
  (2nd round 🐳#3).

The lint logic is imported from tasks.py (the established pattern, see
tests/test_gen_docs_platform_commands.py); the baseline data itself lives
in `platform_yaml_lint_baseline.yaml` so wording PRs only touch data.
"""

import pathlib
import tempfile
import unittest

from tasks import PLATFORM_YAML_LINT_BASELINE, PLATFORMS_YAML_DIR, check_platform_yaml, is_stub_help

CLEAN_PLATFORM = """\
name: synth
initial_prompt: "{base_prompt}>"
commands:
  show clock:
    output: "12:00:00"
    help: Display the system clock
  _default_:
    output: "% Unknown"
    help: default output for unknown commands
"""


class IsStubHelpTest(unittest.TestCase):
    """Pin the stub-help classification (#244 / P-13)."""

    def test_lowercase_execute_prefix_is_stub(self):
        assert is_stub_help('execute the command "show version"')

    def test_capitalized_execute_prefix_is_stub(self):
        assert is_stub_help("Execute the command terminal width 511. This automatically generated.")

    def test_automatically_generated_marker_is_stub(self):
        assert is_stub_help("Anything mentioning This automatically generated. counts")

    def test_real_help_is_not_stub(self):
        assert not is_stub_help("enter enable mode")


class CheckPlatformYamlTest(unittest.TestCase):
    """Ratchet rules of `check_platform_yaml` (#244 / D2 + D4)."""

    def _make_repo(self, files: dict[str, str], baseline: str) -> tuple[str, str]:
        """Build a throwaway platforms dir + baseline file."""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = pathlib.Path(tmp.name)
        platforms = root / "platforms"
        platforms.mkdir()
        for name, content in files.items():
            (platforms / name).write_text(content, encoding="utf-8")
        baseline_path = root / "baseline.yaml"
        baseline_path.write_text(baseline, encoding="utf-8")
        return str(platforms), str(baseline_path)

    def test_real_repo_is_clean(self):
        """The shipped baseline matches the shipped platform yamls."""
        assert check_platform_yaml(PLATFORMS_YAML_DIR, PLATFORM_YAML_LINT_BASELINE) == []

    def test_empty_glob_is_a_violation(self):
        """A wrong platforms path must fail loudly, never silently pass.

        Guards the worst failure mode of a path typo: an empty glob would
        otherwise lint nothing and report success (2nd round 🐙#3).
        """
        platforms, baseline = self._make_repo({}, "missing_default: []\nstub_help: {}\n")
        violations = check_platform_yaml(platforms, baseline)
        assert len(violations) == 1
        assert "no platform yamls found" in violations[0]

    def test_clean_platform_passes(self):
        platforms, baseline = self._make_repo({"synth.yaml": CLEAN_PLATFORM}, "missing_default: []\nstub_help: {}\n")
        assert check_platform_yaml(platforms, baseline) == []

    def test_missing_default_outside_baseline_fails(self):
        """Rule 1: a new platform without `_default_` is rejected."""
        content = CLEAN_PLATFORM.replace(
            '  _default_:\n    output: "% Unknown"\n    help: default output for unknown commands\n', ""
        )
        platforms, baseline = self._make_repo({"synth.yaml": content}, "missing_default: []\nstub_help: {}\n")
        violations = check_platform_yaml(platforms, baseline)
        assert any("missing '_default_'" in v for v in violations)

    def test_new_stub_help_fails_even_when_another_stub_is_fixed(self):
        """Rule 2: identity set, not a count — swaps cannot slip through.

        Pins the 2nd round 🦊#1 scenario: baseline froze `old cmd` as a
        stub; the PR fixes it but adds `new cmd` with a stub. A per-file
        count would balance out; the identity set fails both directions.
        """
        content = CLEAN_PLATFORM + '  new cmd:\n    output: "x"\n    help: execute the command "new cmd"\n'
        platforms, baseline = self._make_repo(
            {"synth.yaml": content},
            "missing_default: []\nstub_help:\n  PLATDIR/synth.yaml:\n    - old cmd\n",
        )
        baseline_text = (
            pathlib.Path(baseline).read_text(encoding="utf-8").replace("PLATDIR", platforms.replace("\\", "/"))
        )
        pathlib.Path(baseline).write_text(baseline_text, encoding="utf-8")
        violations = check_platform_yaml(platforms, baseline)
        assert any("'new cmd' adds an auto-generated stub help" in v for v in violations)
        assert any("'old cmd' no longer has a stub help" in v for v in violations)

    def test_heritage_sentence_fails_on_parsed_help(self):
        """Rule 3: detection works on parsed values, so folding cannot hide it.

        The sentence is authored folded across two lines — a raw-text grep
        misses it (this fooled four independent measurements during the
        design round), the parsed check does not.
        """
        content = CLEAN_PLATFORM + (
            '  legacy cmd:\n    output: "x"\n'
            "    help: Execute the command legacy. This automatically generated. Feel\n"
            "      free to change it!\n"
        )
        platforms, baseline = self._make_repo({"synth.yaml": content}, "missing_default: []\nstub_help: {}\n")
        violations = check_platform_yaml(platforms, baseline)
        assert any("still contains 'Feel free to change it!'" in v for v in violations)

    def test_stale_baseline_entry_fails(self):
        """Rule 4: a baseline entry for a removed file must be cleaned up."""
        platforms, baseline = self._make_repo(
            {"synth.yaml": CLEAN_PLATFORM},
            "missing_default:\n  - somewhere/gone.yaml\nstub_help: {}\n",
        )
        violations = check_platform_yaml(platforms, baseline)
        assert any("the file does not exist" in v for v in violations)

    def test_fixed_default_still_in_baseline_fails(self):
        """Rule 5: improving a file forces shrinking the baseline in the same PR.

        Without this, a forgotten baseline entry would let the violation
        grow back unnoticed later (2nd round 🦊#2).
        """
        platforms, baseline = self._make_repo({"synth.yaml": CLEAN_PLATFORM}, "missing_default: []\nstub_help: {}\n")
        rel = f"{platforms.replace(chr(92), '/')}/synth.yaml"
        pathlib.Path(baseline).write_text(f"missing_default:\n  - {rel}\nstub_help: {{}}\n", encoding="utf-8")
        violations = check_platform_yaml(platforms, baseline)
        assert any("still listed under missing_default" in v for v in violations)
