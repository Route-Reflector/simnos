"""Integration golden for the `--More--` pager over the real SSH wire (#307 / P3-4).

Unlike ``test_ssh_byte_parity.py`` (whose goldens disable paging up front so they
reproduce the *pre-paging* wire), this file deliberately requests a **small pty**
and a **long output** (``show vlan`` = 30 lines) so the server pages, then drives
the pager keys (Space / Enter / q) over a raw paramiko channel and pins the
captured wire against a golden.

This golden is **regression-detection only** (design Notes, claude#6): it records
SIMNOS's own paged output, not an external IOS capture, so it pins "the pager
keeps emitting the same bytes" — the exact ``--More--`` erase sequence
(``\\b``*N + spaces + ``\\b``*N) is SIMNOS's own contract, also pinned byte-for-byte
by ``test_async_session.py``. The byte-level pager state machine (skip_lf,
cross-chunk CRLF, EOF) is unit-pinned there; here we confirm the real asyncssh
transport + real cisco_ios data + a real pty actually page end to end.
"""

from contextlib import contextmanager
import os
from pathlib import Path
import socket
import time

import paramiko
import pytest

from simnos import SimNOS
from tests.utils import TEST_PASSWORD, TEST_USERNAME, build_inventory

_GOLDEN_BASE = Path(__file__).parent.parent / "assets" / "golden_transcripts"
_RECORD = bool(os.environ.get("SIMNOS_RECORD_GOLDEN"))

_HOST = "127.0.0.1"
_DRAIN_IDLE = 0.4  # seconds of silence that marks the end of one response / page
_DRAIN_OVERALL = 10.0
_PTY_HEIGHT = 10  # small pty so `show vlan` (30 lines) pages every `_PTY_HEIGHT` rows


def _drain(channel: paramiko.Channel) -> bytes:
    """Read from *channel* until the wire goes idle (one page / response)."""
    channel.settimeout(_DRAIN_IDLE)
    buf = bytearray()
    start = time.monotonic()
    while True:
        try:
            chunk = channel.recv(4096)
        except TimeoutError:
            if buf:
                break
            if time.monotonic() - start > _DRAIN_OVERALL:
                break
            continue
        if not chunk:
            break
        buf.extend(chunk)
    return bytes(buf)


def _open_shell_channel(port: int, *, height: int) -> tuple[paramiko.Transport, paramiko.Channel]:
    """Authenticate and open an interactive shell with an explicit pty *height*."""
    sock = socket.create_connection((_HOST, port), timeout=5)
    transport = paramiko.Transport(sock)
    transport.start_client(timeout=5)
    transport.auth_password(TEST_USERNAME, TEST_PASSWORD)
    channel = transport.open_session(timeout=5)
    channel.get_pty(width=80, height=height)  # small height -> the pager fires
    channel.invoke_shell()
    return transport, channel


def _format_transcript(steps: list[tuple[bytes, bytes]]) -> str:
    lines = []
    for i, (sent, received) in enumerate(steps):
        lines.append(f"--- step {i}: send={sent!r}")
        lines.append(repr(received))
    return "\n".join(lines) + "\n"


def _assert_or_record(name: str, steps: list[tuple[bytes, bytes]], *, platform: str = "cisco_ios") -> None:
    transcript = _format_transcript(steps)
    golden_dir = _GOLDEN_BASE / platform / "paging"
    golden_path = golden_dir / f"{name}.txt"
    if _RECORD:
        golden_dir.mkdir(parents=True, exist_ok=True)
        golden_path.write_text(transcript, encoding="utf-8")
        pytest.skip(f"recorded golden {golden_path} ({len(transcript)} chars)")
    assert golden_path.exists(), f"golden {golden_path} missing; regenerate with SIMNOS_RECORD_GOLDEN=1"
    expected = golden_path.read_text(encoding="utf-8")
    assert transcript == expected, (
        f"SSH paging wire transcript drifted from golden {golden_path}.\n"
        f"If the wire change is intentional, regenerate with SIMNOS_RECORD_GOLDEN=1 and review the diff."
    )


@contextmanager
def _running_host(device_type: str):
    net = SimNOS(inventory=build_inventory(device_type))
    net.start()
    try:
        # Real OS-assigned port read back after start (#271).
        yield net.hosts["device"].port
    finally:
        net.stop()


@pytest.fixture
def cisco_ios_port():
    with _running_host("cisco_ios") as port:
        yield port


def test_ssh_paging_session(cisco_ios_port):
    """Pin the full paged wire: first page + --More--, Space (full page), Enter
    (one line), then q (erase + prompt, rest discarded)."""
    transport, channel = _open_shell_channel(cisco_ios_port, height=_PTY_HEIGHT)
    steps: list[tuple[bytes, bytes]] = []
    try:
        steps.append((b"", _drain(channel)))  # intro + first prompt
        channel.sendall(b"show vlan\r")
        steps.append((b"show vlan\r", _drain(channel)))  # first page + --More--
        channel.sendall(b" ")  # Space -> next full page + --More--
        steps.append((b"<SPACE>", _drain(channel)))
        channel.sendall(b"\r")  # Enter -> one more line (+ --More-- if rows remain)
        steps.append((b"<ENTER>", _drain(channel)))
        channel.sendall(b"q")  # q -> erase --More-- + prompt, discard the rest
        steps.append((b"q", _drain(channel)))
    finally:
        channel.close()
        transport.close()
    _assert_or_record("paging_session", steps)


def test_ssh_paging_first_page_structure(cisco_ios_port):
    """Structural pin independent of the golden: the first page emits exactly
    `_PTY_HEIGHT` body lines then `--More--`, and Space advances without a prompt
    yet (more output remains)."""
    transport, channel = _open_shell_channel(cisco_ios_port, height=_PTY_HEIGHT)
    try:
        _drain(channel)  # intro + prompt
        channel.sendall(b"show vlan\r")
        first = _drain(channel)
        assert first.endswith(b" --More-- "), "first page must end at the pager prompt"
        # echo "show vlan\r\n" + exactly `_PTY_HEIGHT` body lines (each CRLF) + --More--.
        body = first.split(b"show vlan\r\n", 1)[1].rsplit(b" --More-- ", 1)[0]
        assert body.count(b"\r\n") == _PTY_HEIGHT, "first page body must be exactly pty-height lines"
        assert not first.rstrip().endswith(b"device>"), "the prompt must NOT appear while paging"
        channel.sendall(b"q")  # quit cleanly
        assert _drain(channel).endswith(b"device>")  # q restores the prompt
    finally:
        channel.close()
        transport.close()


def test_ssh_paging_eof_mid_pager_no_hang(cisco_ios_port):
    """Disconnecting at --More-- ends the session cleanly (no prompt, no hang)."""
    transport, channel = _open_shell_channel(cisco_ios_port, height=_PTY_HEIGHT)
    try:
        _drain(channel)
        channel.sendall(b"show vlan\r")
        first = _drain(channel)
        assert first.endswith(b" --More-- ")
        # Close at the pager prompt: the server discards the rest and sends no prompt.
        channel.shutdown_write()
        tail = _drain(channel)
        assert b"device>" not in tail  # no prompt after a mid-pager disconnect
    finally:
        channel.close()
        transport.close()
