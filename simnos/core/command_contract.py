"""Typed contract between the cmd_shell dispatch and NOS plugin callables.

A NOS plugin may set a command's ``output`` to a callable instead of a
static string (see :mod:`simnos.plugins.nos.platforms_py.cisco_ios` for a
live example). This module is the single place where that callable's
signature and return shape are written down — `CMDShell.default()`
dispatches against it and plugin authors can import it for type
annotations (optional; plain functions matching the shape work as-is).
"""

from typing import TYPE_CHECKING, Protocol, TypedDict

if TYPE_CHECKING:
    from simnos.plugins.nos.platforms_py._templates.base_template import BaseDevice


class CommandResult(TypedDict, total=False):
    """Dict form a command handler may return.

    A plain ``str`` return is sugar for ``{"output": <str>}`` —
    `CMDShell._invoke_handler` normalizes it, so handlers only build a
    dict when they need ``new_mode`` / ``exit``.
    """

    output: str | None  # body to send to the client (None = write nothing)
    new_mode: str  # name of the mode to transition to (omit = no transition)
    exit: bool  # True = terminate the session


class CommandHandler(Protocol):
    """Callable signature cmd_shell invokes for dynamic command output.

    Plugin authors typically satisfy this with an unbound method on their
    `BaseDevice` subclass (see ``platforms_py/cisco_ios.py``); ``device``
    then binds as ``self``. ``device`` is None for platforms without a
    device class.

    The returned ``output`` is sent verbatim: cmd_shell never reformats
    handler output (handlers receive ``base_prompt`` and render themselves),
    so literal braces in device output need no escaping. To change mode,
    return ``new_mode`` (a mode name, e.g. ``"enable"``); the shell renders
    the corresponding prompt. Branch on ``current_mode`` (the mode name), not
    on ``current_prompt`` — the latter is the rendered prompt string, kept for
    display/embedding only.

    Raising is allowed for "should never happen" states (see
    ``AristaEOS.make_exit``): cmd_shell logs the full traceback and
    answers the client with the fixed one-liner
    ``simnos.plugins.shell.cmd_shell.HANDLER_ERROR_OUTPUT`` — no
    traceback reaches the wire.
    """

    def __call__(
        self,
        device: "BaseDevice | None",
        *,
        base_prompt: str,
        current_mode: str,
        current_prompt: str,
        command: str,
    ) -> "str | CommandResult | None": ...
