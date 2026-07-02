"""Sidecar-json loader + normalizer + build-time validation (#287 / Layer 1).

Covers `simnos.core.values_loader`: the three sidecar shapes folded to a render
namespace (`_normalize_values`), the strict envelope test (`_is_envelope`), the
reserved-key + command-match loud-fails, the on-disk `load_values`, and the
build-time `validate_render_values` (top-level + dry-render). A final
ntc-templates round-trip proves the headline use case: edit a value in the
sidecar, re-render, re-parse, get the edited value back.
"""

import pathlib

from jinja2 import Environment, StrictUndefined, Template
import pytest

from simnos.core.platform_loader import load_platform_dir
from simnos.core.resolved_command import ResolvedOutput, compile_template
from simnos.core.values_loader import (
    _is_envelope,
    _normalize_values,
    load_values,
    validate_render_values,
)

_ENV = Environment(undefined=StrictUndefined, autoescape=False, keep_trailing_newline=True)  # noqa: S701 — CLI text, not HTML

# Repo root, so the real-platform / fixture loads work regardless of the CWD a
# single-test run uses (not just `pytest tests/` from the root, 2nd round claude#1).
_REPO = pathlib.Path(__file__).resolve().parents[2]
_CISCO_IOS = str(_REPO / "simnos/plugins/nos/platforms/cisco_ios")


def _template(src: str) -> tuple[Template, frozenset[str]]:
    return compile_template(src)


class TestIsEnvelope:
    def test_well_formed_envelope(self):
        raw = [{"command": "show version", "parsed": [{"version": "1"}]}]
        assert _is_envelope(raw) is True

    def test_multi_entry_envelope(self):
        raw = [
            {"command": "show version", "parsed": [{"version": "1"}]},
            {"command": "show clock", "parsed": [{"time": "x"}]},
        ]
        assert _is_envelope(raw) is True

    def test_empty_list_is_not_envelope(self):
        # An empty list must fall through to the bare-list rule (-> {"parsed": []}),
        # never be read as an envelope (#287 / D4 R1).
        assert _is_envelope([]) is False

    def test_bare_row_list_is_not_envelope(self):
        # textfsm rows lacking command/parsed columns.
        assert _is_envelope([{"intf": "Et0/0", "ipaddr": "1.1.1.1"}]) is False

    def test_row_with_only_command_column_is_not_envelope(self):
        # A row that happens to carry `command` but not a list `parsed` is not an
        # envelope — the all-keys-strict test guards the false positive.
        assert _is_envelope([{"command": "x", "parsed": "not-a-list"}]) is False

    def test_dict_is_not_envelope(self):
        assert _is_envelope({"parsed": []}) is False


class TestNormalizeValues:
    def test_envelope_extracts_parsed_only(self):
        raw = [
            {"prompt": "R1#", "command": "show version", "parsed": [{"version": "15.8"}]},
            {"prompt": "R1#", "command": "show clock", "parsed": [{"time": "noon"}]},
        ]
        values = _normalize_values(raw, "show version")
        # 案B (2nd round claude#4): only the matched entry's `parsed` rows are
        # exposed; envelope metadata (command/prompt) is dropped so the namespace
        # is identical to the bare-list shape.
        assert values == {"parsed": [{"version": "15.8"}]}

    def test_envelope_command_match_is_whitespace_and_case_insensitive(self):
        raw = [{"command": "Show   IP  Interface Brief", "parsed": [{"intf": "Et0/0"}]}]
        values = _normalize_values(raw, "show ip interface brief")
        assert values["parsed"] == [{"intf": "Et0/0"}]

    def test_envelope_single_entry_still_requires_match(self):
        # A single envelope entry whose command does not match is a loud error,
        # not a silent "there's only one, use it" (#287 / D4, codex#1 1st).
        raw = [{"command": "show clock", "parsed": [{"time": "x"}]}]
        with pytest.raises(ValueError, match=r"no entry for command 'show version'"):
            _normalize_values(raw, "show version")

    def test_bare_list_wrapped_as_parsed(self):
        raw = [{"intf": "Et0/0"}, {"intf": "Et0/1"}]
        assert _normalize_values(raw, "show ip interface brief") == {"parsed": raw}

    def test_empty_list_wrapped_as_empty_parsed(self):
        assert _normalize_values([], "show version") == {"parsed": []}

    def test_dict_returned_as_is(self):
        assert _normalize_values({"hostname": "R1"}, "show version") == {"hostname": "R1"}

    def test_reserved_key_collision_is_loud(self):
        # A sidecar key shadowing `base_prompt` would crash render() with
        # "multiple values"; caught at normalize time instead (#287 / D4 F).
        with pytest.raises(ValueError, match=r"reserved render var.*base_prompt"):
            _normalize_values({"base_prompt": "evil", "x": 1}, "show version")

    def test_envelope_drops_sibling_metadata_keys(self):
        # 案B (2nd round claude#4): a stray sibling key in an envelope entry (even
        # a reserved one) is not exposed — only `parsed` is kept, so it cannot
        # collide with base_prompt or leak as a render var.
        raw = [{"command": "show version", "parsed": [{"v": "1"}], "base_prompt": "ignored", "extra": 1}]
        assert _normalize_values(raw, "show version") == {"parsed": [{"v": "1"}]}

    def test_scalar_payload_is_loud(self):
        with pytest.raises(ValueError, match=r"must be a list or mapping"):
            _normalize_values("nope", "show version")


class TestLoadValues:
    def test_absent_sidecar_returns_empty(self, tmp_path):
        j2 = tmp_path / "show_version.j2"
        j2.write_text("{{ base_prompt }}\n", encoding="utf-8")
        assert load_values(str(j2), "show version") == {}

    def test_present_sidecar_normalized(self, tmp_path):
        (tmp_path / "show_version.json").write_text('{"hostname": "R1"}', encoding="utf-8")
        j2 = tmp_path / "show_version.j2"
        j2.write_text("{{ hostname }}\n", encoding="utf-8")
        assert load_values(str(j2), "show version") == {"hostname": "R1"}

    def test_malformed_json_is_loud(self, tmp_path):
        (tmp_path / "x.json").write_text("{not valid", encoding="utf-8")
        j2 = tmp_path / "x.j2"
        j2.write_text("{{ base_prompt }}\n", encoding="utf-8")
        with pytest.raises(ValueError, match=r"not valid JSON"):
            load_values(str(j2), "x")


class TestValidateRenderValues:
    def test_literal_is_noop(self):
        out = ResolvedOutput(kind="literal", text="hi\n")
        validate_render_values(out, "show version", source="x")  # no raise

    def test_base_prompt_only_template_ok(self):
        template, required = _template("welcome to {{ base_prompt }}\n")
        out = ResolvedOutput(kind="template", template=template, required_vars=required)
        validate_render_values(out, "banner", source="x")  # no raise, no values needed

    def test_missing_top_level_var_is_loud(self):
        template, required = _template("{{ base_prompt }} {{ hostname }}\n")
        out = ResolvedOutput(kind="template", template=template, required_vars=required)  # no values
        with pytest.raises(ValueError, match=r"needs render var.*hostname.*sidecar"):
            validate_render_values(out, "show version", source="x")

    def test_nested_key_gap_caught_by_dry_render(self):
        # required_vars extracts `parsed` only; the missing nested `version` is
        # caught by the StrictUndefined dry-render (#287 / D5 B).
        template, required = _template("{{ base_prompt }} {{ parsed[0].version }}\n")
        out = ResolvedOutput(kind="template", template=template, required_vars=required, values={"parsed": [{}]})
        with pytest.raises(ValueError, match=r"undefined value during dry-render"):
            validate_render_values(out, "show version", source="x")

    def test_satisfied_nested_keys_pass(self):
        template, required = _template("{{ base_prompt }} {{ parsed[0].version }}\n")
        out = ResolvedOutput(
            kind="template", template=template, required_vars=required, values={"parsed": [{"version": "1"}]}
        )
        validate_render_values(out, "show version", source="x")  # no raise


class TestRoundTrip:
    """The headline use case (#287 / D3): edit a sidecar value, re-render,
    re-parse, get the edited value back — without owning hardware at that version.
    """

    def test_edit_ipaddr_reflects_in_reparse(self):
        """The demo pair is `show ip interface brief` (#287 `.j2`+sidecar).

        `show version` carried the second demo sidecar until #317 P-2: its IOSv
        capture was shadow-dead under the py inflow, so the migration replaced
        it with the actually-served py wire (sidecar-less) and the round-trip
        pin moved here.
        """
        ntc = pytest.importorskip("ntc_templates.parse")

        plat = load_platform_dir(_CISCO_IOS)
        out = plat.commands["show ip interface brief"].output
        assert out.kind == "template"

        # Original render parses back to the shipped second-row address.
        original = out.render("R1")
        parsed = ntc.parse_output(platform="cisco_ios", command="show ip interface brief", data=original)
        assert parsed[1]["ip_address"] == "10.0.1.38"

        # Edit the sidecar value and re-render through the same template.
        edited_rows = [dict(row) for row in out.values["parsed"]]
        edited_rows[1]["ipaddr"] = "192.0.2.99"
        edited = ResolvedOutput(
            kind="template",
            template=out.template,
            required_vars=out.required_vars,
            values={**dict(out.values), "parsed": edited_rows},
        )
        reparsed = ntc.parse_output(platform="cisco_ios", command="show ip interface brief", data=edited.render("R1"))
        assert reparsed[1]["ip_address"] == "192.0.2.99"


class TestDemoByteIdentical:
    """The shipped cisco_ios `.j2`+sidecar demo must render byte-for-byte to the
    original `.txt` it replaced (#287 / D3, R5). The golden fixture under
    tests/assets/cisco_ios_demo/ is the pre-conversion capture; a whitespace
    regression in the `.j2` (e.g. a stray blank line from a `{% for %}` block,
    or a changed column width in the table) fails this pin (1st round
    codex#4 / claude#1). The former `show version` demo pin ended with #317 P-2
    (see TestRoundTrip); the served `show version` bytes are pinned by the
    per-platform A3 oracle snapshot (tests/core/test_migration_oracle_a3.py).
    """

    def test_demo_renders_byte_identical(self):
        expected = (_REPO / "tests/assets/cisco_ios_demo" / "show_ip_interface_brief.expected.txt").read_text(
            encoding="utf-8"
        )
        plat = load_platform_dir(_CISCO_IOS)
        out = plat.commands["show ip interface brief"].output
        assert out.kind == "template"
        assert out.render("R1") == expected


class TestValuesReadOnly:
    def test_values_outer_is_read_only(self):
        out = ResolvedOutput(kind="template", template=_ENV.from_string("{{ x }}"), values={"x": 1})
        with pytest.raises(TypeError):
            out.values["x"] = 2  # ty: ignore[invalid-assignment]  # MappingProxyType blocks mutation (#287, codex#3)

    def test_values_nested_is_deeply_frozen(self):
        # The shared cached value must not be mutable through a nested list/dict,
        # else a template like `{{ parsed.pop() }}` poisons every session that
        # renders the same command (1st round codex#1 / gemini#1).
        out = ResolvedOutput(
            kind="template", template=_ENV.from_string("{{ parsed }}"), values={"parsed": [{"version": "1"}]}
        )
        assert isinstance(out.values["parsed"], tuple)  # list -> tuple
        with pytest.raises((TypeError, AttributeError)):
            out.values["parsed"].append({})  # tuple has no append
        with pytest.raises(TypeError):
            out.values["parsed"][0]["version"] = "2"  # row is a frozen MappingProxyType
