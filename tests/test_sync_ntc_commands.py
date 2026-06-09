"""Unit tests for sync_ntc_commands.py.

Focuses on `select_primary_raw`, which encodes the NTC fixture-naming
heuristics (canonical exact, separator normalization, prefix-less name,
sibling-fixture filtering, alphabetical fallback). These were derived
from concrete cases observed in real NTC Templates data:

- `cisco_ios/show_ip_bgp_neighbors_advertised-routes/`: folder uses `-`,
  the matching raw uses `_` and has no platform prefix.
- `alcatel_sros/ping/`: only prefix-less names (`ping.raw`,
  `ping_bounce.raw`, ...).
- `alcatel_aos/show_interfaces_ethernet/`: contains a sibling fixture
  `alcatel_aos_show_interfaces_R8.raw` that sorts alphabetically before
  the right fixture and would be picked by a naive selector.
"""

import importlib.util
from pathlib import Path
import sys

# sync_ntc_commands.py is a top-level script (not under simnos/) so we load
# it explicitly rather than via a package import.
_SYNC_PATH = Path(__file__).resolve().parents[1] / "sync_ntc_commands.py"
_spec = importlib.util.spec_from_file_location("sync_ntc_commands", _SYNC_PATH)
assert _spec is not None and _spec.loader is not None
sync_ntc_commands = importlib.util.module_from_spec(_spec)
sys.modules["sync_ntc_commands"] = sync_ntc_commands
_spec.loader.exec_module(sync_ntc_commands)

select_primary_raw = sync_ntc_commands.select_primary_raw
escape_format_braces = sync_ntc_commands.escape_format_braces


class TestEscapeFormatBraces:
    """`escape_format_braces` doubles ``{`` and ``}`` so NTC outputs survive
    simnos's runtime ``output.format(base_prompt=...)`` call without
    ``KeyError``. The motivating real-world cases are Juniper's ``{master}``
    routing-engine indicator and ``rpd{junos-bgpshard0}`` process-thread
    names from ``show system processes summary``.
    """

    def test_juniper_master_indicator(self):
        """`{master}` becomes `{{master}}` — the most common Juniper case."""
        assert escape_format_braces("...\n{master}\n") == "...\n{{master}}\n"

    def test_juniper_process_thread_names(self):
        """Nested-looking patterns like `rpd{junos-bgpshard0}` are escaped."""
        assert (
            escape_format_braces("rpd{junos-bgpshard0}\nchassisd{chassisd}")
            == "rpd{{junos-bgpshard0}}\nchassisd{{chassisd}}"
        )

    def test_already_escaped_double_braces_get_quadrupled(self):
        """Pre-escaped `{{x}}` becomes `{{{{x}}}}` — by design.

        Inputs to this function are raw NTC fixtures, which never carry
        pre-escaped braces. We pin the literal behaviour here to make
        the contract explicit: callers must pass untouched fixture text.
        """
        assert escape_format_braces("{{x}}") == "{{{{x}}}}"

    def test_passthrough_when_no_braces(self):
        """Strings without braces are returned unchanged."""
        assert escape_format_braces("plain output text\n") == "plain output text\n"

    def test_preserves_other_characters(self):
        """Newlines, percent signs, backslashes are not affected."""
        text = "line1\nline2\n100%\\path\n"
        assert escape_format_braces(text) == text


class TestSelectPrimaryRaw:
    def test_canonical_exact_match(self):
        """`<platform>_<folder>.raw` wins over suffixed siblings."""
        files = sorted(["cisco_ios_show_cts_pacs.raw", "cisco_ios_show-cts-pacs_6.raw"])
        assert select_primary_raw("cisco_ios", "show_cts_pacs", files) == "cisco_ios_show_cts_pacs.raw"

    def test_canonical_separator_normalization(self):
        """`<platform>_<folder normalized -→_>.raw` wins when folder uses `-`."""
        files = sorted(["cisco_ios_show_foo.raw", "something_unrelated.raw"])
        assert select_primary_raw("cisco_ios", "show-foo", files) == "cisco_ios_show_foo.raw"

    def test_prefix_less_canonical(self):
        """`<folder>.raw` (no platform prefix) wins over suffixed siblings."""
        files = sorted(["ping.raw", "ping_bounce.raw", "ping_fail.raw", "ping_rapid.raw"])
        assert select_primary_raw("alcatel_sros", "ping", files) == "ping.raw"

    def test_separator_normalization(self):
        """Folder name with `-` matches a raw file using `_`, no platform prefix."""
        files = sorted(["show_ip_bgp_neighbors_advertised_routes.raw", "show_ip_bgp_neighbors_advertised_routes2.raw"])
        assert (
            select_primary_raw("cisco_ios", "show_ip_bgp_neighbors_advertised-routes", files)
            == "show_ip_bgp_neighbors_advertised_routes.raw"
        )

    def test_folder_name_filter_skips_sibling_fixture(self):
        """`<folder>` contained in the raw stem wins over an unrelated alpha-first sibling."""
        files = sorted(["alcatel_aos_show_interfaces_R8.raw", "alcatel_aos_show_interfaces_ethernet_R6.raw"])
        assert (
            select_primary_raw("alcatel_aos", "show_interfaces_ethernet", files)
            == "alcatel_aos_show_interfaces_ethernet_R6.raw"
        )

    def test_alphabetical_last_resort(self):
        """When nothing matches the folder name, fall back to alphabetical-first.

        Multiple files are required to exercise the actual ordering — a
        single-file fixture would pass any selector trivially.
        """
        files = sorted(["zzz_unrelated.raw", "aaa_unrelated.raw", "mmm_unrelated.raw"])
        assert select_primary_raw("cisco_ios", "some_command", files) == "aaa_unrelated.raw"

    def test_single_raw_file(self):
        """Single-raw folder picks that file regardless of canonical match."""
        files = ["provided_output.raw"]
        assert select_primary_raw("cisco_ios", "show_ip_dhcp_snooping_binding", files) == "provided_output.raw"
