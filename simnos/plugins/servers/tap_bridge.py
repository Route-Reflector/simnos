"""Transport-agnostic tap functions bridging a network client and a TapIO shell.

Shared by SSH (paramiko channel) and Telnet (raw socket) servers. The
transport differences are absorbed by TransportAdapter implementations
that live in the respective server modules (G3 / #225). The loop logic is
ported verbatim from the former SSH tap pair in ssh_server_paramiko.py so
that the #87 echo-coalescing behaviour is preserved byte for byte.
"""

import io
import logging
import threading
import time
from typing import Protocol

from simnos.core.timeouts import SHUTDOWN_IO_TIMEOUT
from simnos.plugins.servers.tap_io import TapIO, process_tap_line

log = logging.getLogger(__name__)

# Echo coalescing delay for the GIL-scheduling race workaround (#87 SSH /
# #94 Telnet). A 1 ms pause lets the shell enqueue the prompt after a
# newline echo so both are sent in a single sendall().
_COALESCE_DELAY = 0.001


class TransportAdapter(Protocol):
    """Minimal transport surface required by the tap functions.

    Implementations: ParamikoChannelAdapter (ssh_server_paramiko),
    TelnetSocketAdapter (telnet_server).

    Timeout responsibility: adapters do NOT manage I/O timeouts. The caller
    (connection_function) configures them on the underlying channel/socket
    before the taps start; recv_byte()/sendall() simply let the resulting
    TimeoutError propagate. New transports must follow the same split.
    """

    #: Exceptions that mean "I/O failed / peer gone" for this transport.
    #: NOTE: TimeoutError is a subclass of OSError (Py3.10+), so it is
    #: unavoidably *matched* by this tuple. The tap functions therefore
    #: catch TimeoutError in a dedicated ``except TimeoutError:`` clause
    #: placed BEFORE ``except transport.io_errors:`` — exception-clause
    #: order is the contract, not tuple membership.
    io_errors: tuple[type[Exception], ...]

    #: RFC 854 quirk switch: True (Telnet) = CR NUL is a complete sequence,
    #: NUL resets the pending-LF state. False (SSH) = no CR NUL convention,
    #: pending-LF state is preserved across NUL bytes.
    nul_resets_skip_lf: bool

    #: Short name for log messages ("ssh" / "telnet").
    name: str

    def recv_byte(self) -> bytes | None:
        """Read one data byte. Returns None on EOF (b"" must be normalized).

        MUST let TimeoutError propagate to the caller (do NOT swallow it
        inside the adapter) — the tap functions turn recv timeout into a
        ``continue`` so that run_srv shutdown checks keep cycling.
        """
        ...

    def sendall(self, data: bytes) -> None:
        """Send *data* to the client. TimeoutError must propagate."""
        ...

    def is_closed(self) -> bool:
        """Best-effort early check for known-dead transport state.

        Minimum guarantee: returns True once the transport is closed on our
        side (e.g. socket fd already closed). A transport MAY additionally
        report peer-side closure it already knows about (e.g. paramiko's
        channel.closed / not channel.active reflect peer EOF) — callers must
        NOT rely on that: authoritative peer-disconnect detection is
        recv_byte() -> None or an io_errors exception on send.
        """
        ...


def client_to_shell_tap(
    transport: TransportAdapter,
    shell_stdin: TapIO,
    shell_replied_event: threading.Event,
    run_srv: threading.Event,
    *,
    initial_skip_lf: bool = False,
    shell_stdout: TapIO | None = None,
) -> None:
    """Read bytes from the client transport and forward complete lines to shell stdin.

    When *shell_stdout* is provided, the newline echo (``\\r\\n``) for
    line-ending bytes is written to *shell_stdout* instead of being sent
    directly to the transport.  ``shell_to_client_tap`` then batches the
    echo together with the shell's response into a single ``sendall()``,
    preventing a race where the client reads the echo and the prompt as
    separate packets (#87 SSH / #94 Telnet).
    """
    buffer: io.BytesIO = io.BytesIO()
    skip_lf = initial_skip_lf
    while run_srv.is_set():
        try:
            byte = transport.recv_byte()
        except TimeoutError:
            continue
        except transport.io_errors:
            log.debug("tap_bridge.client_to_shell_tap [%s] read closed", transport.name)
            break
        log.debug(
            "tap_bridge.client_to_shell_tap [%s] received from client: %s",
            transport.name,
            [byte],
        )

        # EOF / connection closed (adapters normalize b"" to None)
        if byte is None:
            break

        # Drop NUL bytes completely (don't echo, don't buffer).
        # Telnet (RFC 854): CR NUL is a complete sequence, so reset skip_lf.
        # SSH: no CR NUL convention, skip_lf is intentionally preserved.
        if byte == b"\x00":
            if transport.nul_resets_skip_lf:
                skip_lf = False
            continue

        # Consume the LF half of a CR LF pair.
        if skip_lf:
            skip_lf = False
            if byte == b"\n":
                continue

        # Wait for the shell to reply, but check run_srv periodically
        # so that shutdown is not blocked for the full wait duration.
        while not shell_replied_event.wait(timeout=SHUTDOWN_IO_TIMEOUT):
            if not run_srv.is_set():
                break
        if not run_srv.is_set():
            break
        if transport.is_closed():
            log.error("tap_bridge.client_to_shell_tap [%s] transport closed. Exiting.", transport.name)
            break
        try:
            if byte in (b"\r", b"\n"):
                skip_lf = byte == b"\r"
                if shell_stdout is not None:
                    shell_stdout.write("\r\n")
                else:
                    transport.sendall(b"\r\n")
                log.debug(
                    "tap_bridge.client_to_shell_tap [%s] echoing new line to client: %s",
                    transport.name,
                    [b"\r\n"],
                )
                buffer.write(byte)
                buffer.seek(0)
                line = buffer.read().decode(encoding="utf-8")
                buffer.seek(0)
                buffer.truncate()
                log.debug(
                    "tap_bridge.client_to_shell_tap [%s] sending line to shell: %s",
                    transport.name,
                    [line],
                )
                shell_stdin.write(line)
                shell_replied_event.clear()
            else:
                transport.sendall(byte)
                log.debug(
                    "tap_bridge.client_to_shell_tap [%s] echoing byte to client: %s",
                    transport.name,
                    [byte],
                )
                buffer.write(byte)
        except TimeoutError as e:
            # Echo-send timeout is treated as a disconnect, matching the
            # pre-G3 behaviour of both transports (policy table in the G3
            # design doc; deliberately NOT unified with the batch-send
            # retry in shell_to_client_tap).
            log.error("tap_bridge.client_to_shell_tap [%s] echo write timeout: %s", transport.name, e)
            break
        except transport.io_errors as e:
            log.error("tap_bridge.client_to_shell_tap [%s] client write error: %s", transport.name, e)
            break

    run_srv.clear()


def shell_to_client_tap(
    transport: TransportAdapter,
    shell_stdout: TapIO,
    shell_replied_event: threading.Event,
    run_srv: threading.Event,
) -> None:
    """Read lines from shell stdout and send them to the client transport.

    After reading the first available line, a brief coalescing pause
    (``_COALESCE_DELAY``) allows the shell to enqueue additional output
    (e.g. a prompt following a newline echo).  All available lines are then
    sent in a single ``sendall()`` call so the client receives them in one
    packet, avoiding a GIL-scheduling race (#87 SSH / #94 Telnet).

    When the first line is whitespace-only (a newline echo from
    ``client_to_shell_tap``), the function blocks on a second
    ``readline()`` instead of sending the echo alone.  This guarantees
    the echo and the prompt that follows it are always delivered in the
    same ``sendall()`` call, even when the shell is slow (e.g. hot
    reload YAML re-parse in ``precmd()``).

    A send timeout is retried (U1 — unified for both transports); each
    send attempt is gated on a preceding ``run_srv.is_set()`` check (the
    check and the send are not atomic, so a clear racing in between is
    tolerated — D11).
    """
    while run_srv.is_set():
        if transport.is_closed():
            break
        line = shell_stdout.readline()
        if not line:
            break

        # Coalesce: brief pause lets the shell enqueue the prompt
        # after the newline echo, so both are sent in one packet.
        time.sleep(_COALESCE_DELAY)

        batch = process_tap_line(line)
        drained = shell_stdout.drain()

        if not drained and batch.strip() == "":
            # Echo-only batch (e.g. "\r\n") with nothing else queued.
            # The shell hasn't produced the prompt yet — block until it
            # does so we never send a bare echo as a separate packet.
            next_line = shell_stdout.readline()
            if next_line:
                batch += process_tap_line(next_line)
                # Drain any extra items that arrived alongside the prompt.
                time.sleep(_COALESCE_DELAY)
                drained = shell_stdout.drain()

        for extra in drained:
            # Separate consecutive lines that don't end with a newline
            # (e.g. prompts: "SimNOS>") so they aren't concatenated into
            # "SimNOS>SimNOS>..." which breaks netmiko's find_prompt().
            if batch and not batch.endswith("\n"):
                batch += "\r\n"
            batch += process_tap_line(extra)

        log.debug("tap_bridge.shell_to_client_tap [%s] sending batch to client %s", transport.name, [batch])
        written = False
        while run_srv.is_set() and not written:
            try:
                transport.sendall(batch.encode(encoding="utf-8"))
                written = True
            except TimeoutError:
                # Batch size aids debugging the partial-send duplicate risk
                # accepted in the G3 design (resend may duplicate echoed chars).
                log.debug(
                    "tap_bridge.shell_to_client_tap [%s] write timeout (batch %d chars), retrying",
                    transport.name,
                    len(batch),
                )
                continue
            except transport.io_errors as e:
                log.error("tap_bridge.shell_to_client_tap [%s] client write error: %s", transport.name, e)
                break
        if not written:
            break
        shell_replied_event.set()

    run_srv.clear()


def read_line(
    transport: TransportAdapter,
    *,
    echo: bool = True,
    skip_lf: bool = False,
) -> tuple[str, bool]:
    """Read one line byte-by-byte from the client transport.

    Returns (line without trailing CR/LF, next_skip_lf). A CR terminator
    sets next_skip_lf=True so the *next* call consumes the trailing LF of a
    CR LF pair — the #88 skip_lf-propagation pattern, unified for both
    transports (U3; replaces the former Telnet blocking one-byte consume).

    skip_lf handling on entry:
    - LF: consumed (second half of a CR LF pair), skip_lf cleared.
    - NUL with transport.nul_resets_skip_lf=True (Telnet): consumed
      (RFC 854 CR NUL is a complete sequence), skip_lf cleared.
    - CR: skip_lf cleared, the CR is processed as a line terminator.
    - any other byte: skip_lf cleared, the byte is processed normally.

    Exception contract:
    - recv TimeoutError -> retry (continue).
    - recv io_errors / EOF -> return the partial line read so far (U4 —
      unified on the SSH behaviour; auth then fails on the partial value
      and the connection closes through the normal path).
    - echo send errors propagate to the caller.
    """
    buf = b""
    while True:
        try:
            byte = transport.recv_byte()
        except TimeoutError:
            continue
        except transport.io_errors:
            break
        if byte is None:
            break
        if skip_lf:
            skip_lf = False
            if byte == b"\n":
                continue
            if byte == b"\x00" and transport.nul_resets_skip_lf:
                continue
        if byte == b"\r":
            if echo:
                transport.sendall(b"\r\n")
            return buf.decode("utf-8", errors="replace"), True
        if byte == b"\n":
            if echo:
                transport.sendall(b"\r\n")
            return buf.decode("utf-8", errors="replace"), False
        if echo:
            transport.sendall(byte)
        buf += byte
    return buf.decode("utf-8", errors="replace"), False


def interactive_login(
    transport: TransportAdapter,
    username: str,
    password: str,
    *,
    user_prompt: bytes,
    pass_prompt: bytes,
) -> tuple[bool, bool]:
    """Prompt for username/password over the transport and validate them.

    The prompt byte strings are transport-specific (SSH channel login uses
    Dell-style ``b"\\r\\nUser Name:"``, Telnet uses ``b"Username: "``), so
    they are parameters; the interaction shape is shared.

    Returns (authenticated, skip_lf). The skip_lf flag must be forwarded to
    client_to_shell_tap (initial_skip_lf) so it can consume the trailing
    LF/NUL left over from the final CR of the password line.

    Exception contract: prompt sends and echo sends propagate; recv
    io_errors yield partial lines via read_line (U4) and fail the
    comparison. Callers must wrap this call in try/except covering
    TimeoutError and transport.io_errors.
    """
    transport.sendall(user_prompt)
    entered_user, skip_lf = read_line(transport, echo=True, skip_lf=False)
    transport.sendall(pass_prompt)
    entered_pass, skip_lf = read_line(transport, echo=False, skip_lf=skip_lf)
    transport.sendall(b"\r\n")
    authenticated = entered_user == username and entered_pass == password
    log.debug(
        "tap_bridge.interactive_login [%s] %s for user %s",
        transport.name,
        "succeeded" if authenticated else "failed",
        entered_user,
    )
    return authenticated, skip_lf
