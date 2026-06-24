"""Byte-parity transcript tests for the SSH wire (issue #297 / W3 push dispatch).

The W3 push-dispatch refactor (#297 Stage 1) replaces the two tap threads +
``TapIO`` + ``cmd.Cmd.cmdloop`` with a single push-driven session loop on the
current paramiko transport. The *external* wire byte stream must not change.

These tests pin that contract by driving a **raw paramiko channel** (not
netmiko — we need byte-exact control over what is sent and a faithful capture
of every byte received) through a scripted interactive scenario and comparing
the captured transcript against a golden file.

The golden is **generated once from the unmodified v3 wire** (run with
``SIMNOS_RECORD_GOLDEN=1``) and then frozen as the immovable baseline the
refactor must reproduce byte for byte (design §5, gemini#2). Regenerate it
deliberately (and review the diff) only when the *intended* wire changes.

Determinism: the scenario host has no ``variants_policy`` so every
variant-bearing command resolves to ``select: 0`` (``variants[0]``), and the
chosen commands render static output (no timestamps / RNG), so the byte stream
is identical run to run. The transcript only depends on the cisco_ios command
data, so a data edit (not this refactor) is the only legitimate reason for a
golden update.
"""

from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import socket
import time

import paramiko
import pytest

from simnos import SimNOS
from tests.utils import TEST_PASSWORD, TEST_USERNAME, build_inventory

# Where the frozen golden transcripts live (one file per scenario).
_GOLDEN_DIR = Path(__file__).parent.parent / "assets" / "golden_transcripts" / "cisco_ios"

# Set to regenerate the golden from the *current* wire behaviour. Use only to
# capture the unmodified-v3 baseline, or after a deliberate, reviewed wire change.
_RECORD = bool(os.environ.get("SIMNOS_RECORD_GOLDEN"))

_HOST = "127.0.0.1"
_DRAIN_IDLE = 0.4  # seconds of silence that marks the end of one response
_DRAIN_OVERALL = 10.0  # max seconds to wait for the first byte of a response


def _drain(channel: paramiko.Channel) -> bytes:
    """Read from *channel* until the wire goes idle.

    Waits up to ``_DRAIN_OVERALL`` for the first byte, then treats a
    ``_DRAIN_IDLE`` gap (no new bytes) as the end of the response. The total
    byte *content* is deterministic, so concatenating across reads yields the
    same transcript every run regardless of TCP segmentation.
    """
    channel.settimeout(_DRAIN_IDLE)
    buf = bytearray()
    start = time.monotonic()
    while True:
        try:
            chunk = channel.recv(4096)
        except TimeoutError:
            if buf:
                break  # had data, now idle -> response complete
            if time.monotonic() - start > _DRAIN_OVERALL:
                break  # nothing ever arrived
            continue
        if not chunk:
            break  # EOF
        buf.extend(chunk)
    return bytes(buf)


def _open_shell_channel(port: int) -> tuple[paramiko.Transport, paramiko.Channel]:
    """Authenticate over a raw paramiko transport and open an interactive shell."""
    sock = socket.create_connection((_HOST, port), timeout=5)
    transport = paramiko.Transport(sock)
    transport.start_client(timeout=5)
    transport.auth_password(TEST_USERNAME, TEST_PASSWORD)
    channel = transport.open_session(timeout=5)
    channel.get_pty()
    channel.invoke_shell()
    return transport, channel


def _format_transcript(steps: list[tuple[bytes, bytes]]) -> str:
    """Render (sent, received) steps as a readable, diff-friendly golden text.

    ``repr`` makes ``\\r\\n`` / ``\\x00`` visible so a byte drift is obvious in
    the diff rather than hidden in invisible control characters.
    """
    lines = []
    for i, (sent, received) in enumerate(steps):
        lines.append(f"--- step {i}: send={sent!r}")
        lines.append(repr(received))
    return "\n".join(lines) + "\n"


def _assert_or_record(name: str, steps: list[tuple[bytes, bytes]]) -> None:
    """Compare the transcript against the golden, or record it when explicitly asked."""
    transcript = _format_transcript(steps)
    golden_path = _GOLDEN_DIR / f"{name}.txt"
    if _RECORD:
        _GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
        golden_path.write_text(transcript, encoding="utf-8")
        pytest.skip(f"recorded golden {golden_path} ({len(transcript)} chars)")
    # A missing golden fails loudly rather than silently re-recording (which would
    # let a deleted/absent baseline pass as a no-op). Regenerate deliberately.
    assert golden_path.exists(), f"golden {golden_path} missing; regenerate with SIMNOS_RECORD_GOLDEN=1"
    expected = golden_path.read_text(encoding="utf-8")
    assert transcript == expected, (
        f"SSH wire transcript drifted from golden {golden_path}.\n"
        f"If the wire change is intentional, regenerate with SIMNOS_RECORD_GOLDEN=1 and review the diff."
    )


@pytest.fixture
def cisco_ios_port():
    """Start a single cisco_ios SSH host and yield its port; auto-stop."""
    inventory = build_inventory("cisco_ios")
    net = SimNOS(inventory=inventory)
    net.start()
    try:
        yield inventory["hosts"]["device"]["port"]
    finally:
        net.stop()


def test_byte_parity_interactive_session(cisco_ios_port):
    """Pin the full interactive wire: intro/prompt, char echo, CR/LF/CRLF,
    NUL drop, empty line, help, mode transitions, unknown command, exit."""
    transport, channel = _open_shell_channel(cisco_ios_port)
    steps: list[tuple[bytes, bytes]] = []
    try:
        # step 0: the shell intro + first prompt (no input sent yet)
        steps.append((b"", _drain(channel)))
        # A scripted sequence exercising the wire machinery deterministically.
        script = [
            b"show vlan\r",  # valid command, static table + prompt
            b"enable\r",  # mode user -> enable (prompt changes)
            b"\r",  # empty line: bare newline echo + prompt
            b"show vlan\r",  # valid in enable too
            b"configure terminal\r",  # mode enable -> config
            b"end\r",  # mode config -> enable
            b"?\r",  # help listing for the current mode
            b"no such command\r",  # unknown -> _default_ output
            b"sh\x00ow vlan\r",  # NUL dropped mid-line, command still dispatched
            b"show vlan\r\n",  # CR LF pair: LF consumed, one dispatch
            b"show vlan\n",  # bare LF terminator
            b"exit\r",  # exit command (mode-dependent behaviour)
        ]
        for chunk in script:
            channel.sendall(chunk)
            steps.append((chunk, _drain(channel)))
    finally:
        channel.close()
        transport.close()
    _assert_or_record("interactive_session", steps)


def test_ssh_push_concurrent_connections(cisco_ios_port):
    """Stage 1 light stress (#297 / §4, claude#7): the push driver must not
    regress the thread-per-connection model under concurrency.

    N clients connect in parallel; each authenticates, changes mode, runs a
    command, and must get its own correct prompt + output back (no crossed
    wires, no dropped sessions). This is the lightweight sync-transport + push
    check the spike never measured; the heavy 100-host failure-0 stress lands
    in Stage 2 with asyncssh. Tunable via SIMNOS_PUSH_STRESS_N for local runs.
    """
    n = int(os.environ.get("SIMNOS_PUSH_STRESS_N", "30"))

    def _one_session(_i: int) -> bool:
        transport, channel = _open_shell_channel(cisco_ios_port)
        try:
            assert b"device>" in _drain(channel)  # intro + user prompt
            channel.sendall(b"enable\r")
            assert b"device#" in _drain(channel)  # mode transition
            channel.sendall(b"show vlan\r")
            response = _drain(channel)
            assert b"VLAN Name" in response and response.endswith(b"device#")
            return True
        finally:
            channel.close()
            transport.close()

    with ThreadPoolExecutor(max_workers=n) as pool:
        results = list(pool.map(_one_session, range(n)))
    assert all(results), f"{results.count(False)}/{n} concurrent push sessions failed"


def test_byte_parity_eof_on_disconnect(cisco_ios_port):
    """Pin the wire when the client sends a partial line then disconnects:
    chars are echoed, the unterminated line is dropped, no spurious output."""
    transport, channel = _open_shell_channel(cisco_ios_port)
    steps: list[tuple[bytes, bytes]] = []
    try:
        steps.append((b"", _drain(channel)))
        # Type a partial line (no terminator), capture the char echoes.
        partial = b"show ver"
        channel.sendall(partial)
        steps.append((partial, _drain(channel)))
        # Half-close the write side (client EOF) and capture any trailing wire.
        channel.shutdown_write()
        steps.append((b"<EOF>", _drain(channel)))
    finally:
        channel.close()
        transport.close()
    _assert_or_record("eof_on_disconnect", steps)
