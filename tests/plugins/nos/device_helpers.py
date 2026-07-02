"""
Shared helpers for the device-class unit tests in this package (T-14 / #230).

Each test_<nos>.py invokes plugin handlers with the same contract as
`CMDShell._invoke_handler` (device, base_prompt=, current_mode=, current_prompt=,
command=); this module holds that invocation and the common base_prompt so the
per-platform files stay focused on their pins. Handlers are resolved from the
A3 handler namespace (`nos.handlers`, #317) — the same lookup
`build_resolved_platform` binds `handler:` refs against.
"""

from simnos.core.nos import Nos

__all__ = ["BASE_PROMPT", "call_handler"]

BASE_PROMPT = "router"


def call_handler(nos: Nos, handler: str, command: str, current_mode: str, current_prompt: str = ""):
    """Invoke a py handler with the cmd_shell handler contract (#264 / #317).

    Handlers branch on `current_mode` (the mode name); `current_prompt` (the
    rendered prompt) is display-only and rarely used, so it defaults to blank.
    """
    return nos.handlers[handler](
        nos.device,
        base_prompt=BASE_PROMPT,
        current_mode=current_mode,
        current_prompt=current_prompt,
        command=command,
    )
