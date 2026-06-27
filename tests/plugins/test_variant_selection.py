"""Per-session variant selection — machine C (#287 / D6, D7).

Pins `variants_policy` resolution through the shell: int select (deterministic
default), out-of-range loud, seeded random (reproducible / per-host sticky),
seedless random (per-session fixed), the canonical_name shared-state contract,
the dispatch `cmd.variants` guard, and the two-phase atomic hot-reload rebuild
(lazy-decide new canonicals, prune dropped ones, no KeyError, no partial commit).

The shell is built directly against tmp A3 platforms (the real tree is never
mutated), mirroring `test_cmd_shell_a3.py`.
"""

import io
import threading

import pytest

from simnos.core.host import HostRenderConfig
from simnos.core.nos import Nos
from simnos.core.pydantic_models import ModelVariantsPolicy
from simnos.core.resolved_command import ResolvedCommand, ResolvedOutput
from simnos.plugins.shell.cmd_shell import CMDShell


def _write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _platform_with_variants(tmp_path, *, n=3, extra_yaml: dict[str, str] | None = None):
    """A minimal platform whose `show test` has `n` distinct literal variants."""
    root = tmp_path / "cisco_ios"
    _write(
        root / "platform.yaml",
        'modes:\n  user:\n    prompt: "{{ base_prompt }}>"\ninitial_mode: user\n',
    )
    commands = root / "commands"
    variants_yaml = "".join(f"- name: variant_{i + 1}\n  output: show_test__variant_{i + 1}.txt\n" for i in range(n))
    _write(commands / "show_test.yaml", f"command: show test\ntype: simnos\nvariants:\n{variants_yaml}")
    for i in range(n):
        _write(commands / f"show_test__variant_{i + 1}.txt", f"VARIANT-{i + 1}\n")
    _write(commands / "default.yaml", "command: _default_\ntype: simnos\noutput: default.txt\n")
    _write(commands / "default.txt", "% Invalid input\n")
    if extra_yaml:
        for fname, content in extra_yaml.items():
            _write(commands / fname, content)
    return root


def _shell(nos, *, policy=None, host_name="R1", base_prompt="R1"):
    render_config = HostRenderConfig(variants_policy=policy, host_name=host_name)
    return CMDShell(
        stdin=None,
        stdout=io.StringIO(),
        nos=nos,
        nos_inventory_config={},
        base_prompt=base_prompt,
        is_running=_running_event(),
        render_config=render_config,
    )


def _running_event():
    ev = threading.Event()
    ev.set()
    return ev


def _served(shell, line="show test"):
    """Dispatch a line through the shared core and return its rendered body.

    `default` was removed in #303 P3-3; `_dispatch_general` returns the body the
    shell would have written (variant outputs here are single-line).
    """
    body, _close = shell._dispatch_general(line)
    return body or ""


class TestIntSelect:
    def test_default_select_is_first_variant(self, tmp_path):
        # No policy -> select 0 -> variants[0], the legacy-compatible default.
        shell = _shell(Nos(filename=str(_platform_with_variants(tmp_path))))
        assert shell._variant_indices["show test"] == 0
        assert _served(shell).strip() == "VARIANT-1"

    def test_explicit_int_selects_that_index(self, tmp_path):
        shell = _shell(
            Nos(filename=str(_platform_with_variants(tmp_path))),
            policy=ModelVariantsPolicy(select=2),
        )
        assert shell._variant_indices["show test"] == 2
        assert _served(shell).strip() == "VARIANT-3"

    def test_out_of_range_int_is_loud_at_build(self, tmp_path):
        # 5 >= 3 variants -> loud at shell construction (build phase), not a
        # silent modulo wrap (#287 / D6, codex#2 3rd).
        with pytest.raises(ValueError, match=r"select=5 out of range.*show test"):
            _shell(
                Nos(filename=str(_platform_with_variants(tmp_path, n=3))),
                policy=ModelVariantsPolicy(select=5),
            )


class TestSeededRandom:
    def test_seeded_random_is_reproducible_per_host(self, tmp_path):
        # Same seed + same host id -> same variant across two independent sessions
        # (sticky), and the index is in range.
        root = _platform_with_variants(tmp_path, n=3)
        policy = ModelVariantsPolicy(select="random", seed=1234)
        a = _shell(Nos(filename=str(root)), policy=policy, host_name="R1")
        b = _shell(Nos(filename=str(root)), policy=policy, host_name="R1")
        assert a._variant_indices["show test"] == b._variant_indices["show test"]
        assert 0 <= a._variant_indices["show test"] < 3

    def test_seeded_random_differs_by_host(self, tmp_path):
        # The host term is part of the hash, so different hosts spread across
        # states (pin that at least one host pair differs over a small sweep).
        root = _platform_with_variants(tmp_path, n=3)
        policy = ModelVariantsPolicy(select="random", seed=1234)
        idxs = {
            h: _shell(Nos(filename=str(root)), policy=policy, host_name=h)._variant_indices["show test"]
            for h in ("R1", "R2", "R3", "R4", "R5")
        }
        assert len(set(idxs.values())) > 1


class TestSeedlessRandom:
    def test_seedless_random_is_fixed_within_session(self, tmp_path):
        # One connection picks one variant and keeps it for every poll (the box
        # does not transform mid-session, D7).
        shell = _shell(
            Nos(filename=str(_platform_with_variants(tmp_path))),
            policy=ModelVariantsPolicy(select="random"),
        )
        first = _served(shell)
        for _ in range(5):
            assert _served(shell) == first


class TestCanonicalSharing:
    def test_alias_shares_canonical_state(self, tmp_path):
        # An A3 alias of the variant command shares one state index (keyed on
        # canonical_name), so both names serve the same variant (#287 / D6).
        root = _platform_with_variants(
            tmp_path,
            extra_yaml={"sh_test.yaml": "command: sh test\nalias: show test\n"},
        )
        shell = _shell(Nos(filename=str(root)), policy=ModelVariantsPolicy(select=1))
        # Both the real command and its alias resolve to canonical "show test".
        assert shell.commands["sh test"].canonical_name == "show test"
        assert _served(shell, "show test").strip() == "VARIANT-2"
        assert _served(shell, "sh test").strip() == "VARIANT-2"


class TestPoolLengthGuard:
    def test_same_canonical_different_pool_length_is_loud(self, tmp_path):
        # Two commands sharing a canonical_name but exposing different variant
        # pool lengths make the shared index ambiguous — loud (#287 / D6,
        # codex#1 6th). This is the legacy `output_variants`-override shape; build
        # it directly and feed `_build_variant_maps`.
        shell = _shell(Nos(filename=str(_platform_with_variants(tmp_path))))
        o = ResolvedOutput(kind="literal", text="x\n")
        real = ResolvedCommand(
            name="show bgp",
            modes=frozenset(),
            new_mode=None,
            output=o,
            variants=(("variant_1", o), ("variant_2", o)),
            help="",
            exit=False,
            type="simnos",
        )
        alias = ResolvedCommand(
            name="sh bgp",
            modes=frozenset(),
            new_mode=None,
            output=o,
            variants=(("variant_1", o), ("variant_2", o), ("variant_3", o)),
            help="",
            exit=False,
            type="simnos",
            canonical_name="show bgp",
        )
        with pytest.raises(ValueError, match=r"variant pool length mismatch for canonical 'show bgp'"):
            shell._build_variant_maps({"show bgp": real, "sh bgp": alias})


class TestDispatchGuard:
    def test_non_variant_command_ignores_map(self, tmp_path):
        # A single-output command (variants=()) never consults the variant map.
        root = _platform_with_variants(tmp_path)
        _write(root / "commands" / "show_one.yaml", "command: show one\ntype: simnos\noutput: show_one.txt\n")
        _write(root / "commands" / "show_one.txt", "ONLY\n")
        shell = _shell(Nos(filename=str(root)))
        assert _served(shell, "show one").strip() == "ONLY"


class TestHotReloadVariants:
    def test_new_variant_command_on_reload_is_decided_lazily(self, tmp_path):
        # A variant-bearing command that appears on reload must be decided
        # lazily, not KeyError (#287 / #1, codex#1/gemini#1 3rd).
        root = _platform_with_variants(tmp_path)
        shell = _shell(Nos(filename=str(root)), policy=ModelVariantsPolicy(select=1))
        _write(
            root / "commands" / "show_new.yaml",
            "command: show new\ntype: simnos\nvariants:\n"
            "- name: variant_1\n  output: show_new__variant_1.txt\n"
            "- name: variant_2\n  output: show_new__variant_2.txt\n",
        )
        _write(root / "commands" / "show_new__variant_1.txt", "NEW-1\n")
        _write(root / "commands" / "show_new__variant_2.txt", "NEW-2\n")
        shell.reload_commands([str(root)])
        assert shell._variant_indices["show new"] == 1
        assert _served(shell, "show new").strip() == "NEW-2"
        # The pre-existing command's index is preserved across the reload.
        assert shell._variant_indices["show test"] == 1

    def test_dropped_variant_command_is_pruned(self, tmp_path):
        root = _platform_with_variants(tmp_path)
        shell = _shell(Nos(filename=str(root)))
        assert "show test" in shell._variant_indices
        (root / "commands" / "show_test.yaml").unlink()
        for i in range(3):
            (root / "commands" / f"show_test__variant_{i + 1}.txt").unlink()
        shell.reload_commands([str(root)])
        assert "show test" not in shell._variant_indices

    def test_bad_select_on_reload_leaves_session_intact(self, tmp_path):
        # A reload whose policy would be out of range must not partially mutate
        # the live session (#287 / R8 two-phase atomic). Here the new command has
        # fewer variants than `select`, so the rebuild raises; the old maps stay.
        root = _platform_with_variants(tmp_path, n=3)
        shell = _shell(Nos(filename=str(root)), policy=ModelVariantsPolicy(select=2))
        assert shell._variant_indices["show test"] == 2
        # Capture the live dict object (not a copy) so identity pins that the
        # failed reload never reached the commit phase that reassigns it.
        before_ref = shell.commands
        before_snapshot = dict(shell.commands)
        rng_before = shell._connection_rng.getstate()
        # Shrink the pool to 2 variants while a NEW canonical needs index 2.
        _write(
            root / "commands" / "show_two.yaml",
            "command: show two\ntype: simnos\nvariants:\n"
            "- name: variant_1\n  output: show_two__variant_1.txt\n"
            "- name: variant_2\n  output: show_two__variant_2.txt\n",
        )
        _write(root / "commands" / "show_two__variant_1.txt", "TWO-1\n")
        _write(root / "commands" / "show_two__variant_2.txt", "TWO-2\n")
        # reload_commands swallows the build error (atomic rollback); the live
        # session keeps its prior command set AND its RNG state (#287 / R8, codex#2).
        shell.reload_commands([str(root)])
        assert shell.commands is before_ref  # commit never ran -> same object
        assert dict(shell.commands) == before_snapshot  # content unchanged
        assert "show two" not in shell.commands
        assert shell._connection_rng.getstate() == rng_before  # no RNG consumed by the failed build

    def test_explicit_int_pool_shrink_on_existing_canonical_is_loud(self, tmp_path):
        # An inherited explicit-int index pushed out of range by a hot reload
        # shrinking the pool is loud, not silently wrapped — the same contract a
        # fresh connect enforces (2nd round gemini#1 / codex#1). This is the
        # existing-canonical case (test_bad_select... covers a new canonical).
        root = _platform_with_variants(tmp_path, n=3)
        shell = _shell(Nos(filename=str(root)), policy=ModelVariantsPolicy(select=2))
        assert shell._variant_indices["show test"] == 2
        o = ResolvedOutput(kind="literal", text="x\n")
        shrunk = {
            "show test": ResolvedCommand(
                name="show test",
                modes=frozenset(),
                new_mode=None,
                output=o,
                variants=(("variant_1", o), ("variant_2", o)),  # was 3, now 2
                help="",
                exit=False,
                type="simnos",
            )
        }
        with pytest.raises(ValueError, match=r"select=2 out of range.*after a hot reload"):
            shell._build_variant_maps(shrunk)

    def test_random_pool_shrink_refits_and_persists_index(self, tmp_path):
        # Random has no fixed-index contract, so a pool shrink refits silently
        # with `% n` instead of raising (the asymmetry vs explicit int). The refit
        # must be *written back* to the index map so a later re-expansion can't
        # revive the pre-shrink index and flip-flop the choice (3rd round codex#1).
        root = _platform_with_variants(tmp_path, n=3)
        shell = _shell(Nos(filename=str(root)), policy=ModelVariantsPolicy(select="random", seed=1))
        shell._variant_indices["show test"] = 2  # force the out-of-range-after-shrink case
        o0 = ResolvedOutput(kind="literal", text="V0\n")
        o1 = ResolvedOutput(kind="literal", text="V1\n")
        o2 = ResolvedOutput(kind="literal", text="V2\n")

        def _cmd(*variants):
            return ResolvedCommand(
                name="show test",
                modes=frozenset(),
                new_mode=None,
                output=variants[0],
                variants=tuple((f"variant_{i + 1}", v) for i, v in enumerate(variants)),
                help="",
                exit=False,
                type="simnos",
            )

        indices, outputs = shell._build_variant_maps({"show test": _cmd(o0, o1)})  # n=2, no raise
        assert outputs["show test"].render("R1") == "V0\n"  # 2 % 2 = 0 -> variants[0]
        assert indices["show test"] == 0  # refit persisted, not stale 2
        # Commit the shrink result, then re-expand: the index stays 0 (no revival).
        shell._variant_indices = indices
        indices2, outputs2 = shell._build_variant_maps({"show test": _cmd(o0, o1, o2)})  # back to n=3
        assert indices2["show test"] == 0
        assert outputs2["show test"].render("R1") == "V0\n"  # not the revived V2

    def test_prompt_render_failure_on_reload_rolls_back_rng(self, tmp_path):
        # The RNG snapshot/rollback spans the whole build/validate phase, so a
        # prompt-render failure *after* a seedless-random draw rolls back both the
        # commands and the consumed randomness (2nd round codex#2).
        root = _platform_with_variants(tmp_path)
        shell = _shell(Nos(filename=str(root)), policy=ModelVariantsPolicy(select="random"))  # seedless
        before_ref = shell.commands
        rng_before = shell._connection_rng.getstate()
        # A NEW variant command forces a seedless draw during the failing reload...
        _write(
            root / "commands" / "show_new.yaml",
            "command: show new\ntype: simnos\nvariants:\n"
            "- name: variant_1\n  output: show_new__variant_1.txt\n"
            "- name: variant_2\n  output: show_new__variant_2.txt\n",
        )
        _write(root / "commands" / "show_new__variant_1.txt", "NEW-1\n")
        _write(root / "commands" / "show_new__variant_2.txt", "NEW-2\n")
        # ...and an undefined mode prompt makes _apply_platform's render fail after it.
        _write(
            root / "platform.yaml",
            'modes:\n  user:\n    prompt: "{{ undefined_var }}"\ninitial_mode: user\n',
        )
        shell.reload_commands([str(root)])  # swallowed (atomic rollback)
        assert shell.commands is before_ref  # rolled back, commit never ran
        assert "show new" not in shell.commands
        assert shell._connection_rng.getstate() == rng_before  # RNG draw rolled back too
