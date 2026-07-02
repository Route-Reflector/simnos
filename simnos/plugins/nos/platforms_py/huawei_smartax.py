"""
NOS module for Huawei SmartAX
"""

import os

from simnos.plugins.nos.platforms_py._templates.base_template import BaseDevice

NAME: str = "huawei_smartax"
INITIAL_PROMPT: str = "{base_prompt}>"
ENABLE_PROMPT: str = "{base_prompt}#"
CONFIG_PROMPT: str = "{base_prompt}(config)#"

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
            for board in boards:
                board[title] = board_column[boards.index(board)]
        rows = [list(board.values()) for board in boards]
        return self.render("huawei_smartax/display_board.j2", titles=titles, rows=rows)

    def _return(self, base_prompt, current_mode, current_prompt, command):
        "Return to user prompt"
        # v2 keyed on the prompt suffix: ">" (user) stayed user, "#"
        # (enable/config) went to enable. Mode names express that directly.
        if current_mode == "user":
            return {"output": "", "new_mode": "user"}
        return {"output": "", "new_mode": "enable"}

    def quit(self, base_prompt, current_mode, current_prompt, command):
        "Exit from device"
        return {"exit": True}

    def disable(self, base_prompt, current_mode, current_prompt, command):
        "Exit exec prompt"
        # From enable/config drop to user; already in user = no transition.
        if current_mode in ("enable", "config"):
            return {"output": "", "new_mode": "user"}
        return {"output": ""}


commands = {
    "enable": {
        "output": None,
        "new_prompt": ENABLE_PROMPT,
        "help": "enter exec prompt",
        "prompt": INITIAL_PROMPT,
    },
    "undo smart": {
        "output": None,
        "help": "undo smart command",
        "prompt": [INITIAL_PROMPT, ENABLE_PROMPT],
    },
    "infoswitch cli OFF": {
        "output": None,
        "help": "turn off infoswitch cli",
        "prompt": [INITIAL_PROMPT, ENABLE_PROMPT],
    },
    "return": {
        "output": HuaweiSmartAX._return,
        "help": "return to user prompt",
        "prompt": ENABLE_PROMPT,
        # The handler decides `new_mode` at dispatch time (conditional on
        # current_mode), so the static command dict carries no `new_prompt`.
        # Flag the transition statically so the netmiko sweep skips it (#115);
        # #317 supersedes this once A3 authors handlers with a static new_mode.
        "changes_prompt": True,
    },
    # `scroll` is served by the A3 command (commands/scroll.yaml), byte-identical
    # to this empty-output stub. It was dropped from this py module so the A3
    # `scroll` (carrying `disables_paging: true`, #307 / P3-4) is no longer
    # shadowed by the py inflow (which overrides A3 in build_resolved_platform and
    # cannot carry the flag — py-plugin paging is out of scope). See #320 / #308.
    "disable": {
        "output": HuaweiSmartAX.disable,
        "help": "exit exec prompt",
        "prompt": [INITIAL_PROMPT, ENABLE_PROMPT],
        # Handler-decided transition (see `return` above) — flag it so the
        # netmiko sweep skips it (#115).
        "changes_prompt": True,
    },
    "display board": {
        "output": HuaweiSmartAX.make_display_board,
        "help": "display board information",
        "prompt": [INITIAL_PROMPT, ENABLE_PROMPT],
    },
    "quit": {
        "output": HuaweiSmartAX.quit,
        "help": "exit from device",
        "prompt": [INITIAL_PROMPT, ENABLE_PROMPT],
    },
}
