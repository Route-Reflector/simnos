"""Typed contract between the cmd_shell dispatch and NOS plugin callables.

An A3 command may author ``handler: <name>`` instead of a static output; the
name resolves to a callable on the platform's py module (see
:mod:`simnos.plugins.nos.platforms_py.cisco_ios` for a live example). This
module is the single place where that callable's signature and return shape
are written down — `CMDShell._dispatch_general()` (via `_invoke_handler`)
dispatches against it and plugin authors can import it for type annotations
(optional; plain functions matching the shape work as-is).
"""

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from simnos.plugins.nos.base_device import BaseDevice


class CommandHandler(Protocol):
    """Callable signature cmd_shell invokes for dynamic command output.

    Plugin authors typically satisfy this with a method on their `BaseDevice`
    subclass (see ``platforms_py/cisco_ios.py``); ``device`` then binds as
    ``self``. ``device`` is None for platforms without a device class.

    A handler produces **output only**: return the body ``str`` (sent
    verbatim — handlers receive ``base_prompt`` and render themselves, so
    literal braces need no escaping) or ``None`` to write nothing. Mode
    transitions and session close are static authoring data (``new_mode`` /
    ``exit`` / ``transitions`` in the command yaml), not handler returns —
    the dict-return form (``CommandResult``) was removed with the legacy
    py-dict authoring (#317 / P-2). Branch on ``current_mode`` (the mode
    name), not on ``current_prompt`` — the latter is the rendered prompt
    string, kept for display/embedding only.

    Raising is allowed for "should never happen" states: cmd_shell logs the
    full traceback and answers the client with the fixed one-liner
    ``simnos.plugins.shell.cmd_shell.HANDLER_ERROR_OUTPUT`` — no traceback
    reaches the wire. A non-``str | None`` return gets the same one-liner
    (loud in the log, never garbage on the wire).
    """

    def __call__(
        self,
        device: "BaseDevice | None",
        *,
        base_prompt: str,
        current_mode: str,
        current_prompt: str,
        command: str,
    ) -> str | None: ...
