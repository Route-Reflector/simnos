"""Push-session wire assembly shared by the async server plugins (#297).

The session driver (:func:`simnos.plugins.servers.async_session.run_async_push_session`)
turns one dispatched line into a single write unit — the held ``\\r\\n`` echo, the
command body, and the next prompt — so the wire byte stream is identical across
the SSH (asyncssh) and Telnet (telnetlib3) transports. The assembly itself lives
here, transport-agnostic, and is pinned end-to-end by the byte-parity goldens in
``tests/plugins/test_ssh_byte_parity.py`` / ``tests/plugins/test_telnet_byte_parity.py``.

History: this module also hosted the synchronous tap pair + ``run_push_session``
that drove the paramiko SSH channel and the raw-socket Telnet server. Those were
retired with the paramiko server in #297 Stage 4; only the wire-assembly helpers
the async path reuses remain (the per-line ``_process_tap_line`` normalisation,
formerly the standalone ``tap_io`` module's ``process_tap_line``, was folded in
here at the same time).
"""

import logging
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from simnos.plugins.shell.cmd_shell import DispatchResult

log = logging.getLogger(__name__)


def _process_tap_line(line: str) -> str:
    """Sanitise a single line of shell output for the network client.

    - Strips NUL bytes.
    - Converts bare ``\\n`` to ``\\r\\n`` (leaves existing ``\\r\\n`` intact).
    """
    if "\x00" in line:
        line = line.replace("\x00", "")
    if "\r\n" not in line and "\n" in line:
        line = line.replace("\n", "\r\n")
    return line


class PushShell(Protocol):
    """The shell surface the push driver drives (CMDShell implements it, #297).

    Duck-typed so the session driver stays shell-agnostic and both transports can
    reuse it: `dispatch` is the I/O-independent core, while `intro` / `prompt` /
    `newline` supply the wire framing.
    """

    intro: str | None
    prompt: str
    newline: str

    def dispatch(self, line: str) -> "DispatchResult": ...

    def completion_candidates(self, prefix: str) -> list[str]:
        """Whole-line current-mode command names completing ``prefix`` (#303 Tab).

        P3-1 matched an exact prefix; P3-2 widened this to leading-token
        abbreviation, still returning whole-line names (the line-replacement
        contract is unchanged).
        """
        ...


def _assemble_wire(writes: list[str]) -> bytes:
    """Normalize each shell write and join to wire bytes (#297 / §3a).

    `_process_tap_line` is applied per write, mirroring how the legacy
    `shell_to_client_tap` processed each shell stdout write individually (NUL
    strip / bare-LF → CRLF). This is the session-handler write-unit assembly
    shared by SSH and Telnet.
    """
    return "".join(_process_tap_line(w) for w in writes).encode("utf-8")


def _render_intro(shell: PushShell) -> bytes:
    """Initial wire bytes: the shell intro line + the first prompt (#297 / §3a).

    Reproduces the framing the legacy `cmd.Cmd.cmdloop` produced (removed in #303
    P3-3): ``str(intro)+"\\n"`` then ``self.prompt`` as two stdout writes
    (assembled per write so CR/LF/NUL normalization matches the legacy
    `shell_to_client_tap`).
    """
    writes: list[str] = []
    if shell.intro:
        writes.append(f"{shell.intro}\n")
    writes.append(shell.prompt)
    return _assemble_wire(writes)


def _render_response(shell: PushShell, result: "DispatchResult") -> bytes:
    """Wire bytes for one dispatched line: newline echo + body + next prompt (#297 / §3a).

    The line-terminator echo (``\\r\\n``) is held until dispatch completes and
    emitted as the first part of this single write unit, reproducing the legacy
    echo coalescing without the timing-dependent ``_COALESCE_DELAY``. On a close
    result neither body nor prompt is emitted (the legacy `default` adapter wrote
    nothing on its close paths), leaving just the newline echo. Each body line
    gets a trailing ``newline``, reproducing the legacy per-line shell output.
    """
    writes: list[str] = ["\r\n"]  # line-terminator echo, held until dispatch
    if not result.close:
        if result.body is not None:
            writes.extend(line + shell.newline for line in str(result.body).splitlines())
        writes.append(result.prompt)
    return _assemble_wire(writes)
