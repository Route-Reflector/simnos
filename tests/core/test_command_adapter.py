"""Unit tests for the legacy-form normalization core (#264 / P1-1 D6).

Covers mode synthesis + prompt->mode reverse lookup, command normalization
(prompt/new_prompt/output/variants/alias), and the loud boundaries. The
whole-dataset equivalence (all 50 platforms vs v2) is the migration oracle
(b') added in PR-1's later increment; these unit tests pin the pieces.
"""

import pytest

from simnos.core.command_adapter import (
    adapt_commands,
    adapt_legacy_commands,
    synthesize_modes,
)

CISCO_PROMPTS = ("{base_prompt}>", "{base_prompt}#", "{base_prompt}(config)#")


def _cisco_modes():
    """The canonical 3-mode reverse map shared by several tests."""
    return synthesize_modes(*CISCO_PROMPTS)


class TestSynthesizeModes:
    """Mode synthesis from v2's three prompt templates (#264 / M2)."""

    def test_three_modes(self):
        modes, initial, reverse = _cisco_modes()
        assert set(modes) == {"user", "enable", "config"}
        assert initial == "user"
        assert set(reverse.values()) == {"user", "enable", "config"}

    def test_two_modes_when_no_config(self):
        modes, _, _ = synthesize_modes("{base_prompt}>", "{base_prompt}#", None)
        assert set(modes) == {"user", "enable"}

    def test_one_mode_when_only_initial(self):
        modes, initial, _ = synthesize_modes("{base_prompt}>", None, None)
        assert set(modes) == {"user"}
        assert initial == "user"

    def test_ambiguous_modes_raise(self):
        """Two modes rendering to the same prompt cannot be reverse-mapped."""
        with pytest.raises(ValueError, match="ambiguous"):
            synthesize_modes("{base_prompt}#", "{base_prompt}#", None)

    def test_mode_prompt_renders_with_base_prompt(self):
        modes, _, _ = _cisco_modes()
        assert modes["config"].render_prompt("R1") == "R1(config)#"


class TestAdaptCommandModes:
    """prompt -> mode membership reverse lookup."""

    def test_single_prompt_to_single_mode(self):
        _, _, reverse = _cisco_modes()
        resolved = adapt_commands({"show run": {"output": "x", "prompt": "{base_prompt}#"}}, reverse)
        assert resolved["show run"].modes == frozenset({"enable"})

    def test_prompt_list_to_mode_set(self):
        _, _, reverse = _cisco_modes()
        resolved = adapt_commands(
            {"show clock": {"output": "x", "prompt": ["{base_prompt}>", "{base_prompt}#"]}}, reverse
        )
        assert resolved["show clock"].modes == frozenset({"user", "enable"})

    def test_prompt_omitted_is_empty_modes(self):
        """A command with no prompt is valid in every mode (empty set)."""
        _, _, reverse = _cisco_modes()
        resolved = adapt_commands({"cmd": {"output": "x"}}, reverse)
        assert resolved["cmd"].modes == frozenset()

    def test_unmappable_prompt_is_loud(self):
        _, _, reverse = _cisco_modes()
        with pytest.raises(ValueError, match="cannot map"):
            adapt_commands({"weird": {"output": "x", "prompt": "alien$"}}, reverse)

    def test_explicit_empty_prompt_list_is_loud(self):
        """`prompt: []` is rejected, not silently treated as all-modes (#264 / claude #3).

        v2 `_check_prompt([])` was always False (unreachable); an empty mode set
        means the opposite ("all modes"), so the inversion must be loud.
        """
        _, _, reverse = _cisco_modes()
        with pytest.raises(ValueError, match=r"empty prompt list"):
            adapt_commands({"cmd": {"output": "x", "prompt": []}}, reverse)

    def test_format_failing_prompt_is_context_tagged_loud(self):
        """An unknown-field prompt fails with a context-tagged ValueError, not a bare KeyError."""
        _, _, reverse = _cisco_modes()
        with pytest.raises(ValueError, match=r"command 'weird'"):
            adapt_commands({"weird": {"output": "x", "prompt": "{hostname}>"}}, reverse)

    def test_unmappable_new_prompt_is_loud(self):
        _, _, reverse = _cisco_modes()
        with pytest.raises(ValueError, match="new_prompt"):
            adapt_commands({"go": {"output": None, "prompt": "{base_prompt}>", "new_prompt": "alien$"}}, reverse)

    def test_new_prompt_maps_to_new_mode(self):
        _, _, reverse = _cisco_modes()
        resolved = adapt_commands(
            {"enable": {"output": None, "prompt": "{base_prompt}>", "new_prompt": "{base_prompt}#"}}, reverse
        )
        assert resolved["enable"].new_mode == "enable"

    def test_no_new_prompt_is_none(self):
        _, _, reverse = _cisco_modes()
        resolved = adapt_commands({"show run": {"output": "x", "prompt": "{base_prompt}#"}}, reverse)
        assert resolved["show run"].new_mode is None


class TestAdaptDefault:
    """`_default_` is the unconditional fallback (#264 / D5)."""

    def test_default_modes_empty_and_prompt_dropped(self):
        """Even an authored prompt on `_default_` is dropped (v2 never matches it)."""
        _, _, reverse = _cisco_modes()
        resolved = adapt_commands(
            {"_default_": {"output": "% Unknown", "prompt": "{base_prompt}#", "new_prompt": "{base_prompt}>"}}, reverse
        )
        assert resolved["_default_"].modes == frozenset()
        assert resolved["_default_"].new_mode is None


class TestAdaptOutput:
    """`output` normalization to ResolvedOutput kinds."""

    def test_none_output(self):
        _, _, reverse = _cisco_modes()
        resolved = adapt_commands({"enable": {"output": None, "prompt": "{base_prompt}>"}}, reverse)
        assert resolved["enable"].output.kind == "none"

    def test_str_output_literal(self):
        _, _, reverse = _cisco_modes()
        resolved = adapt_commands({"cmd": {"output": "static {{esc}}", "prompt": "{base_prompt}>"}}, reverse)
        out = resolved["cmd"].output
        assert out.kind == "literal"
        assert out.text == "static {esc}"  # v2 brace unescape

    def test_str_output_with_base_prompt_is_template(self):
        _, _, reverse = _cisco_modes()
        resolved = adapt_commands({"cmd": {"output": "host {base_prompt}", "prompt": "{base_prompt}>"}}, reverse)
        out = resolved["cmd"].output
        assert out.kind == "template"
        assert out.render("R9") == "host R9"

    def test_non_dict_entry_is_loud(self):
        _, _, reverse = _cisco_modes()
        with pytest.raises(ValueError, match="expected a mapping"):
            adapt_commands({"bad": ["not", "a", "dict"]}, reverse)

    def test_non_str_non_callable_output_is_loud(self):
        """v2 output is only str/callable/None; anything else fails at load, not via str() on wire."""
        _, _, reverse = _cisco_modes()
        with pytest.raises(ValueError, match="unsupported output type"):
            adapt_commands({"cmd": {"output": 123, "prompt": "{base_prompt}>"}}, reverse)

    def test_callable_output_is_handler(self):
        _, _, reverse = _cisco_modes()
        handler = lambda device, **kw: "dynamic"  # noqa: E731
        resolved = adapt_commands({"cmd": {"output": handler, "prompt": "{base_prompt}>"}}, reverse)
        out = resolved["cmd"].output
        assert out.kind == "handler"
        assert out.handler is handler

    def test_output_variants_canonical_contract(self):
        """variants[0] mirrors `output` (variant_1); alternates follow as variant_2.. (D3/D7)."""
        _, _, reverse = _cisco_modes()
        resolved = adapt_commands(
            {"cmd": {"output": "primary", "output_variants": ["a", "b"], "prompt": "{base_prompt}>"}}, reverse
        )
        rc = resolved["cmd"]
        assert rc.output.text == "primary"
        assert [name for name, _ in rc.variants] == ["variant_1", "variant_2", "variant_3"]
        assert [o.text for _, o in rc.variants] == ["primary", "a", "b"]
        assert rc.variants[0][1] is rc.output  # primary mirrored at variants[0]

    def test_single_output_has_no_variants(self):
        """A command without output_variants carries an empty variants tuple."""
        _, _, reverse = _cisco_modes()
        resolved = adapt_commands({"cmd": {"output": "only", "prompt": "{base_prompt}>"}}, reverse)
        assert resolved["cmd"].variants == ()

    def test_template_output_required_vars_excludes_base_prompt(self):
        """A {base_prompt}-only output template carries no host facts (#265 placeholder)."""
        _, _, reverse = _cisco_modes()
        resolved = adapt_commands({"cmd": {"output": "host {base_prompt}", "prompt": "{base_prompt}>"}}, reverse)
        assert resolved["cmd"].output.required_vars == frozenset()


class TestAdaptAlias:
    """Single-level alias field-merge, replicating v2 (#264 / D6)."""

    def test_alias_merges_target_fields(self):
        _, _, reverse = _cisco_modes()
        commands = {
            "show clock": {"output": "12:00", "help": "clock", "prompt": "{base_prompt}>"},
            "sh clock": {"alias": "show clock"},
        }
        resolved = adapt_commands(commands, reverse)
        assert resolved["sh clock"].output.text == "12:00"  # dispatch fields from target
        assert resolved["sh clock"].help == ""  # help is the alias's own (see test_alias_help_is_own_not_target)
        assert resolved["sh clock"].modes == frozenset({"user"})
        # #287 / D6: the legacy adapter dict-merges + reconstructs (no `replace`
        # auto-inherit), so canonical_name must be propagated explicitly from the
        # alias target — pin it so the legacy path is not the silent asymmetry
        # that re-introduces an alias "transforming" between variant states
        # (codex#1 5th). The real command's canonical_name is its own name.
        assert resolved["sh clock"].canonical_name == "show clock"
        assert resolved["show clock"].canonical_name == "show clock"

    def test_alias_help_is_own_not_target(self):
        """An alias shows its own help (blank if absent), not the target's (#264 / D6).

        v2 `do_help` lists the raw unmerged entry, so this is the observable
        help; the dispatch fields still come from the target.
        """
        _, _, reverse = _cisco_modes()
        commands = {
            "show clock": {"output": "12:00", "help": "clock", "prompt": "{base_prompt}>"},
            "sh clock": {"alias": "show clock"},
            "sc": {"alias": "show clock", "help": "own help"},
        }
        resolved = adapt_commands(commands, reverse)
        assert resolved["sh clock"].help == ""  # no own help -> blank
        assert resolved["sc"].help == "own help"  # own help kept
        assert resolved["sh clock"].output.text == "12:00"  # dispatch still from target

    def test_alias_entry_keys_win(self):
        """An alias entry's own fields override the target's (#264 / D6)."""
        _, _, reverse = _cisco_modes()
        commands = {
            "show ip int brief": {"output": "brief", "prompt": ["{base_prompt}>", "{base_prompt}#"]},
            "do show ip int brief": {"alias": "show ip int brief", "prompt": "{base_prompt}(config)#"},
        }
        resolved = adapt_commands(commands, reverse)
        # output inherited from target, but prompt (mode) overridden by the alias entry
        assert resolved["do show ip int brief"].output.text == "brief"
        assert resolved["do show ip int brief"].modes == frozenset({"config"})

    def test_missing_alias_target_dropped(self):
        """A missing target degrades to unknown (dropped from the resolved dict)."""
        _, _, reverse = _cisco_modes()
        resolved = adapt_commands({"broken": {"alias": "no such target"}}, reverse)
        assert "broken" not in resolved


class TestAdaptLegacyCommands:
    """Top-level `adapt_legacy_commands` wires modes + commands together."""

    def test_returns_resolved_platform(self):
        platform = adapt_legacy_commands(
            "{base_prompt}>",
            "{base_prompt}#",
            "{base_prompt}(config)#",
            {
                "enable": {"output": None, "prompt": "{base_prompt}>", "new_prompt": "{base_prompt}#"},
                "_default_": {"output": "% Unknown"},
            },
        )
        assert platform.initial_mode == "user"
        assert set(platform.modes) == {"user", "enable", "config"}
        assert platform.commands["enable"].new_mode == "enable"
        assert platform.commands["_default_"].modes == frozenset()
