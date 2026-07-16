"""
NOS module for Huawei SmartAX.

Command authoring lives in the A3 platform dir (``platforms/huawei_smartax/``);
this module only ships the device class whose methods back the A3
``handler:`` commands, plus the default board configuration (#317 / P-2).
"""

import os

from simnos.plugins.nos.platforms_py._templates.base_template import BaseDevice

DEFAULT_CONFIGURATION: str = os.path.join(os.path.dirname(__file__), "configurations", "huawei_smartax.yaml.j2")


class HuaweiSmartAX(BaseDevice):
    """
    Class that keeps track of the state of the Huawei SmartAX device.
    """

    def _add_whitespaces(self, column: list[str]):
        """
        Add whitespacing to a column depending on the
        largest element in the column.
        """
        max_length = max(len(str(row)) for row in column)
        return [str(row).ljust(max_length) for row in column]

    def make_display_board(self, base_prompt, current_mode, current_prompt, command):
        "Return String of board information"
        titles = [
            "SlotID",
            "BoardName",
            "Status",
            "SubType0",
            "SubType1",
            "Online/Offline",
        ]
        boards = [
            {
                titles[0]: self.configurations["boards"]["slots"][board]["slot_id"],
                titles[1]: self.configurations["boards"]["slots"][board]["boardname"],
                titles[2]: self.configurations["boards"]["slots"][board]["status"],
                titles[3]: self.configurations["boards"]["slots"][board]["subtype0"],
                titles[4]: self.configurations["boards"]["slots"][board]["subtype1"],
                titles[5]: self.configurations["boards"]["slots"][board]["online_offline"],
            }
            for board in range(self.configurations["boards"]["num"])
        ]
        for index, title in enumerate(titles):
            board_column = [board[title] for board in boards]
            results = self._add_whitespaces([title, *board_column])
            board_column = results[1:]
            titles[index] = results[0]
            for board_index, board in enumerate(boards):
                board[title] = board_column[board_index]
        rows = [list(board.values()) for board in boards]
        return self.render("huawei_smartax/display_board.j2", titles=titles, rows=rows)
