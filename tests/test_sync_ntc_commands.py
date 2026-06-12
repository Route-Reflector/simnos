"""Unit tests for sync_ntc_commands.py.

Covers `select_primary_raw` (the NTC fixture-naming heuristics) and the A3
take-in candidate output (`write_diff_files`) the tool generates (#264 / D9).

`select_primary_raw` cases are derived from concrete real NTC Templates data:

- `cisco_ios/show_ip_bgp_neighbors_advertised-routes/`: folder uses `-`,
  the matching raw uses `_` and has no platform prefix.
- `alcatel_sros/ping/`: only prefix-less names (`ping.raw`,
  `ping_bounce.raw`, ...).
- `alcatel_aos/show_interfaces_ethernet/`: contains a sibling fixture
  `alcatel_aos_show_interfaces_R8.raw` that sorts alphabetically before
  the right fixture and would be picked by a naive selector.
"""

import importlib.util
import os
from pathlib import Path
import sys

import yaml

# sync_ntc_commands.py is a top-level script (not under simnos/) so we load
# it explicitly rather than via a package import.
_SYNC_PATH = Path(__file__).resolve().parents[1] / "sync_ntc_commands.py"
_spec = importlib.util.spec_from_file_location("sync_ntc_commands", _SYNC_PATH)
assert _spec is not None and _spec.loader is not None
sync_ntc_commands = importlib.util.module_from_spec(_spec)
sys.modules["sync_ntc_commands"] = sync_ntc_commands
_spec.loader.exec_module(sync_ntc_commands)

select_primary_raw = sync_ntc_commands.select_primary_raw
write_diff_files = sync_ntc_commands.write_diff_files


class TestWriteDiffFiles:
    """`write_diff_files` emits A3 take-in candidate files (#264 / D9).

    One ``commands/<stem>.yaml`` + adjacent ``.txt`` per command, with
    ``type: ntc`` and a ``source`` provenance block — raw NTC text stored
    verbatim (no brace escaping, the A3 runtime renders literals unchanged).
    """

    def _new_commands(self):
        return {
            "show version": {
                "output": "Cisco IOS\nflags={origin_is_acl,}\n",
                "output_variants": [],
                "raw_path": "ntc-templates/tests/cisco_ios/show_version/cisco_ios_show_version.raw",
                "raw_path_variants": [],
            }
        }

    def test_emits_a3_command_yaml_and_txt(self, tmp_path):
        write_diff_files(str(tmp_path), "cisco_ios", self._new_commands(), "abc123", ["user", "enable"])
        commands_dir = tmp_path / "cisco_ios" / "commands"
        mapping = yaml.safe_load((commands_dir / "show_version.yaml").read_text(encoding="utf-8"))
        assert mapping["command"] == "show version"
        assert mapping["type"] == "ntc"
        assert mapping["source"] == {
            "ntc_template": "tests/cisco_ios/show_version/cisco_ios_show_version.raw",
            "ntc_commit": "abc123",
        }
        assert mapping["mode"] == ["user", "enable"]
        assert mapping["output"] == "show_version.txt"

    def test_output_text_is_verbatim_with_trailing_newline(self, tmp_path):
        """Braces survive unescaped; a single trailing newline is ensured."""
        write_diff_files(str(tmp_path), "cisco_ios", self._new_commands(), "abc123", [])
        body = (tmp_path / "cisco_ios" / "commands" / "show_version.txt").read_text(encoding="utf-8")
        assert body == "Cisco IOS\nflags={origin_is_acl,}\n"

    def test_variants_become_variant_entries(self, tmp_path):
        new_commands = {
            "show foo": {
                "output": "primary\n",
                "output_variants": ["alt one\n", "alt two\n"],
                "raw_path": "ntc-templates/tests/cisco_ios/show_foo/show_foo.raw",
                "raw_path_variants": [],
            }
        }
        write_diff_files(str(tmp_path), "cisco_ios", new_commands, "abc123", [])
        commands_dir = tmp_path / "cisco_ios" / "commands"
        mapping = yaml.safe_load((commands_dir / "show_foo.yaml").read_text(encoding="utf-8"))
        assert [v["name"] for v in mapping["variants"]] == ["variant_1", "variant_2", "variant_3"]
        assert "output" not in mapping
        assert (commands_dir / "show_foo__variant_1.txt").read_text(encoding="utf-8") == "primary\n"
        assert (commands_dir / "show_foo__variant_3.txt").read_text(encoding="utf-8") == "alt two\n"

    def test_fs_hostile_command_name_is_sanitized(self, tmp_path):
        new_commands = {
            "get system status | grep Version": {
                "output": "v1\n",
                "output_variants": [],
                "raw_path": "ntc-templates/tests/fortinet/x/x.raw",
                "raw_path_variants": [],
            }
        }
        write_diff_files(str(tmp_path), "fortinet", new_commands, "abc123", [])
        files = os.listdir(tmp_path / "fortinet" / "commands")
        # no path separators / pipes leaked into the filename
        assert all("/" not in f and "|" not in f for f in files)
        assert "get_system_status_grep_version.yaml" in files


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
