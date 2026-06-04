"""
Device-class unit tests for the huawei_smartax Python plugin (T-14 / #230).

This platform's e2e all-commands test is xfail'd (mode-changing
callables cause netmiko ReadTimeout), so these unit tests are its only
content-level verification. Producer-side pins: `make_display_board`
table structure, the per-prompt branches of the dict-returning mode
callables (`_return` / `disable` / `quit`), the `_add_whitespaces`
alignment helper, and the DEFAULT_CONFIGURATION (yaml.j2) wiring.
"""

import pytest

from simnos.core.nos import Nos
from simnos.plugins.nos import nos_plugins
from simnos.plugins.nos.platforms_py.huawei_smartax import ENABLE_PROMPT, INITIAL_PROMPT
from tests.plugins.nos.device_helpers import BASE_PROMPT, call_command

INITIAL = INITIAL_PROMPT.format(base_prompt=BASE_PROMPT)
ENABLE = ENABLE_PROMPT.format(base_prompt=BASE_PROMPT)


@pytest.fixture(scope="module")
def nos() -> Nos:
    """Merged Nos via the same wiring the server uses (Host.start equivalent).

    `Nos._from_module` instantiates the device with DEFAULT_CONFIGURATION
    (configurations/huawei_smartax.yaml.j2), so the j2 -> yaml -> dict
    loading path of BaseDevice.load_configurations is covered too.
    """
    return Nos(filename=nos_plugins["huawei_smartax"])


def test_default_configuration_provides_boards(nos):
    """DEFAULT_CONFIGURATION (yaml.j2) wiring: boards data is loaded."""
    assert "boards" in nos.device.configurations
    assert nos.device.configurations["boards"]["num"] > 0


def test_display_board_table_structure(nos):
    out = call_command(nos, "display board", INITIAL)
    lines = out.splitlines()
    header_lines = [line for line in lines if "SlotID" in line]
    assert len(header_lines) == 1
    header = header_lines[0]
    assert "BoardName" in header
    # One data row per configured slot (empty slots render as a bare SlotID).
    data_rows = [line for line in lines if line.strip() and line.strip()[0].isdigit()]
    assert len(data_rows) == nos.device.configurations["boards"]["num"]
    # _add_whitespaces pads every column to its max width, so the header
    # and all data rows share one length and SlotID sits at a fixed column.
    slot_col = header.index("SlotID")
    assert all(len(row) == len(header) for row in data_rows)
    assert all(row[slot_col].isdigit() for row in data_rows)


class TestModeCallables:
    """Pin the per-prompt branches of the dict-returning mode callables.

    The branches dispatch on the current_prompt *suffix* ('>' / '#' /
    other), so 'bogus$' exercises the fallback branch.
    """

    def test_return_from_initial_prompt(self, nos):
        assert call_command(nos, "return", INITIAL) == {"output": "", "new_prompt": INITIAL_PROMPT}

    def test_return_from_enable_prompt(self, nos):
        assert call_command(nos, "return", ENABLE) == {"output": "", "new_prompt": ENABLE_PROMPT}

    def test_return_from_other_prompt(self, nos):
        assert call_command(nos, "return", "bogus$") == {"output": "", "new_prompt": INITIAL_PROMPT}

    def test_disable_from_enable_prompt(self, nos):
        assert call_command(nos, "disable", ENABLE) == {"output": "", "new_prompt": INITIAL_PROMPT}

    def test_disable_from_other_prompt_keeps_prompt(self, nos):
        assert call_command(nos, "disable", "bogus$") == {"output": "", "new_prompt": "bogus$"}

    def test_quit_exits(self, nos):
        assert call_command(nos, "quit", INITIAL) == {"exit": True}


class TestAddWhitespaces:
    """Pin the column alignment helper, including boundary cases."""

    def test_pads_to_longest_element(self, nos):
        result = nos.device._add_whitespaces(["a", "bbb", "cc"])
        assert result == ["a  ", "bbb", "cc "]

    def test_single_element_is_unpadded(self, nos):
        assert nos.device._add_whitespaces(["abc"]) == ["abc"]

    def test_equal_length_elements_are_unpadded(self, nos):
        assert nos.device._add_whitespaces(["aa", "bb"]) == ["aa", "bb"]

    def test_empty_column_raises(self, nos):
        """Current behavior: max() on an empty column raises ValueError.

        Unreachable via make_display_board (the column always includes
        its title), pinned as a guard so a future formatting change that
        alters this contract is visible here first.
        """
        with pytest.raises(ValueError, match=r"empty"):
            nos.device._add_whitespaces([])
