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
    `CMDShell._invoke_callable` normalizes it, so handlers only build a
    dict when they need ``new_prompt`` / ``exit``.
    """

    output: str | None  # body to send to the client (None = write nothing)
    new_prompt: str  # prompt transition template ({base_prompt} allowed)
    exit: bool  # True = terminate the session


class CommandHandler(Protocol):
    """Callable signature cmd_shell invokes for dynamic command output.

    Plugin authors typically satisfy this with an unbound method on their
    `BaseDevice` subclass (see ``platforms_py/cisco_ios.py``); ``device``
    then binds as ``self``. ``device`` is None for platforms without a
    device class.

    The returned ``output`` must be fully rendered: cmd_shell does NOT
    apply ``{base_prompt}`` formatting to callable output (handlers
    receive ``base_prompt`` as an argument and format themselves) — only
    yaml-static output strings are formatted. Literal braces in device
    output therefore need no escaping. A returned ``new_prompt`` is the
    one exception: prompt templates are the shell's concern, so the
    shell formats it like any yaml ``new_prompt``.

    Raising is allowed for "should never happen" states (see
    ``AristaEOS.make_exit``): cmd_shell logs the full traceback and
    answers the client with the fixed ``HANDLER_ERROR_OUTPUT`` line —
    no traceback reaches the wire.
    """

    def __call__(
        self,
        device: "BaseDevice | None",
        *,
        base_prompt: str,
        current_prompt: str,
        command: str,
    ) -> "str | CommandResult | None": ...
