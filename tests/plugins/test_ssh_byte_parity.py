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
from contextlib import contextmanager
import os
from pathlib import Path
import socket
import time

import paramiko
import pytest

from simnos import SimNOS
from tests.utils import TEST_PASSWORD, TEST_USERNAME, build_inventory

# Where the frozen golden transcripts live (one subdir per platform, one file per scenario).
_GOLDEN_BASE = Path(__file__).parent.parent / "assets" / "golden_transcripts"

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


def _assert_or_record(name: str, steps: list[tuple[bytes, bytes]], *, platform: str = "cisco_ios") -> None:
    """Compare the transcript against the golden, or record it when explicitly asked."""
    transcript = _format_transcript(steps)
    golden_dir = _GOLDEN_BASE / platform
    golden_path = golden_dir / f"{name}.txt"
    if _RECORD:
        golden_dir.mkdir(parents=True, exist_ok=True)
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


@contextmanager
def _running_host(device_type: str):
    """Start a single-host SimNOS for *device_type* and yield its port; auto-stop."""
    net = SimNOS(inventory=build_inventory(device_type))
    net.start()
    try:
        # Read the real OS-assigned port back after start (#271): the inventory dict
        # keeps the ephemeral sentinel 0.
        yield net.hosts["device"].port
    finally:
        net.stop()


@pytest.fixture
def cisco_ios_port():
    """Start a single cisco_ios SSH host and yield its port; auto-stop."""
    with _running_host("cisco_ios") as port:
        yield port


def test_byte_parity_interactive_session(cisco_ios_port):
    """Pin the full interactive wire: intro/prompt, char echo, CR/LF/CRLF,
    NUL drop, empty line, help, mode transitions, unknown command, exit."""
    transport, channel = _open_shell_channel(cisco_ios_port)
    steps: list[tuple[bytes, bytes]] = []
    try:
        # step 0: the shell intro + first prompt (no input sent yet)
        steps.append((b"", _drain(channel)))
        # A scripted sequence exercising the wire machinery deterministically.
        # A real scraper disables paging first (netmiko sends `terminal length 0`);
        # the paramiko client here requests an 80x24 pty, so without this `show vlan`
        # (30 lines) would page at `--More--`. Disabling paging up front reproduces
        # the pre-paging wire byte-for-byte for every following step (#307 / P3-4).
        script = [
            b"terminal length 0\r",  # disable paging (sticky) — faithful scraper behaviour
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
            # Disable paging up front: this test uses an 80x24 pty and asserts the
            # response ends with the prompt, which `--More--` paging would break.
            # It is assertion-based (outside the golden), so it needs the explicit
            # disable a real scraper sends (#307 / P3-4, claude#2).
            channel.sendall(b"terminal length 0\r")
            _drain(channel)
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


def test_byte_parity_challenge_session():
    """Pin the interactive challenge wire (#338): `sudo -s` on linux fires a password
    sub-prompt, the answer is NOT echoed, a wrong answer replays the failure body with
    the user prompt, and a correct one reaches root (`device#`).

    This is a NEW golden (linux has no prior transcript), recorded from the current
    wire — not a re-record of a frozen baseline. The password answer is `TEST_PASSWORD`
    (the challenge is `auth: password`, so sudo asks for the login password).
    """
    with _running_host("linux") as port:
        transport, channel = _open_shell_channel(port)
        steps: list[tuple[bytes, bytes]] = []
        try:
            steps.append((b"", _drain(channel)))  # intro + user prompt (device$)
            script = [
                b"sudo -s\r",  # challenge fires: "[sudo] password for test_user: "
                b"wrongpw\r",  # wrong answer -> failure body + user prompt (answer not echoed)
                b"sudo -s\r",  # re-fire (single-attempt: each fire is one prompt)
                TEST_PASSWORD.encode() + b"\r",  # correct -> root prompt device#
            ]
            for chunk in script:
                channel.sendall(chunk)
                steps.append((chunk, _drain(channel)))
        finally:
            channel.close()
            transport.close()
    _assert_or_record("challenge_session", steps, platform="linux")


def test_byte_parity_confirm_session(cisco_ios_port):
    """Pin the interactive confirm wire (#338 Phase 3): cisco_ios confirm commands.

    A NEW golden (a dedicated confirm transcript, not a re-record of the frozen
    `interactive_session` baseline). Exercises the `kind: confirm` driver path,
    which differs from the password path by echoing the answer and emitting an
    `[OK]`-style body:

    - `copy running-config startup-config` asks a free-line prompt; Enter accepts
      the default and builds (`Building configuration...` / `[OK]`), staying in enable
    - `write memory` is a plain literal (NOT a challenge) — the non-interactive save
    - `reload` answered `n` cancels (the `n` echoes, the prompt returns unchanged)
    - `reload` answered with a bare Enter confirms → the session closes (EOF)
    """
    transport, channel = _open_shell_channel(cisco_ios_port)
    steps: list[tuple[bytes, bytes]] = []
    try:
        steps.append((b"", _drain(channel)))  # intro + user prompt (device>)
        script = [
            b"enable\r",  # -> enable mode (device#), no secret on cisco_ios
            b"copy running-config startup-config\r",  # confirm fires: "Destination filename ...? "
            b"\r",  # accept default -> "Building configuration...\r\n[OK]" + device#
            b"write memory\r",  # plain literal -> same [OK] body, no sub-prompt
            b"reload\r",  # confirm fires: "Proceed with reload? [confirm]"
            b"n\r",  # cancel: the `n` echoes, prompt returns (no body)
            b"reload\r",  # re-fire
            b"\r",  # bare Enter confirms -> session closes
        ]
        for chunk in script:
            channel.sendall(chunk)
            steps.append((chunk, _drain(channel)))
    finally:
        channel.close()
        transport.close()
    _assert_or_record("confirm_session", steps)


def test_byte_parity_session_close_command():
    """Pin the wire for a real session-closing command, #297 codex#2.

    A minimal, dedicated close-over-wire pin: typing `ex` on alcatel_aos closes
    the session. alcatel_aos declares no `exit`/`ex` command of its own, so `ex`
    abbreviation-resolves to the all-modes BASIC `exit` (exit:true) — the char
    echoes + the newline echo, then the server closes (no body, no prompt). Since
    #327 Tier 3 removed the redundant standalone `ex` stub, this now exercises the
    abbreviation path; the wire is byte-identical (`ex\\r` -> `ex\\r\\n` -> close).
    (The exact-match close path itself is pinned at unit level by
    `test_abbreviation.test_session_close_authoring`, so this wire pin is free to
    ride the abbreviation route without losing close-over-wire coverage.)
    """
    with _running_host("alcatel_aos") as port:
        transport, channel = _open_shell_channel(port)
        steps: list[tuple[bytes, bytes]] = []
        try:
            steps.append((b"", _drain(channel)))  # intro + first prompt
            channel.sendall(b"ex\r")  # exit: true -> close after the newline echo
            steps.append((b"ex\r", _drain(channel)))  # "ex\r\n" then EOF (server closed)
        finally:
            channel.close()
            transport.close()
    _assert_or_record("session_close", steps, platform="alcatel_aos")
