"""
Shared helpers for the device-class unit tests in this package (T-14 / #230).

Each test_<nos>.py invokes plugin callables with the same contract as
`CMDShell._invoke_handler` (device, base_prompt=, current_mode=, current_prompt=,
command=); this module holds that invocation and the common base_prompt so the
per-platform files stay focused on their pins.
"""

from simnos.core.nos import Nos

__all__ = ["BASE_PROMPT", "call_command"]

BASE_PROMPT = "router"


def call_command(nos: Nos, command: str, current_mode: str, current_prompt: str = "", base_prompt: str = BASE_PROMPT):
    """Invoke a callable command with the cmd_shell handler contract (#264).

    Handlers branch on `current_mode` (the mode name); `current_prompt` (the
    rendered prompt) is display-only and rarely used, so it defaults to blank.
    """
    return nos.commands[command]["output"](
        nos.device,
        base_prompt=base_prompt,
        current_mode=current_mode,
        current_prompt=current_prompt,
        command=command,
    )
