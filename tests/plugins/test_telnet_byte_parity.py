"""Byte-parity transcript tests for the Telnet wire (issue #297 / Stage 3).

Stage 3 replaces the raw-socket Telnet server (TCPServerBase + manual IAC + two
tap threads + ``TapIO`` + ``cmd.Cmd.cmdloop``) with a telnetlib3 server driven by
the **shared** ``run_async_push_session`` on the SimNOS shared loop. The
application-layer wire (banner / in-band login / per-char echo / body / prompt /
Telnet CR NUL) must not change.

The golden is byte-identical to the legacy raw-socket Telnet server's
application-layer wire — verified directly during development by running both
servers through the same telnetlib3-client scenario (3903 bytes, byte-for-byte),
honouring design §5 "record from the unmodified v3 wire". The transport-level IAC
negotiation differs (telnetlib3 negotiates WILL ECHO / WILL SGA / BINARY itself)
but is absorbed by the telnetlib3 client, so it never enters the captured
application transcript.

Determinism mirrors the SSH byte-parity test: the host has no ``variants_policy``
so variant-bearing commands resolve to ``variants[0]`` and render static output,
making the byte stream identical run to run.
"""

import asyncio
from contextlib import contextmanager
import os
from pathlib import Path

import pytest

from simnos import SimNOS
from tests.plugins.telnet_test_helpers import capture_telnet_transcript
from tests.utils import build_inventory

# Where the frozen golden transcripts live (one subdir per platform, one file per scenario).
_GOLDEN_BASE = Path(__file__).parent.parent / "assets" / "golden_transcripts"

# Set to regenerate the golden from the *current* wire behaviour. Use only to
# capture the baseline, or after a deliberate, reviewed wire change.
_RECORD = bool(os.environ.get("SIMNOS_RECORD_GOLDEN"))

# A telnet host whose transcript is captured at the application layer.
_TELNET_SERVER = {"plugin": "TelnetServer", "configuration": {}}


def _format_transcript(steps: list[tuple[bytes, bytes]]) -> str:
    """Render (sent, received) steps as a readable, diff-friendly golden text."""
    lines = []
    for i, (sent, received) in enumerate(steps):
        lines.append(f"--- step {i}: send={sent!r}")
        lines.append(repr(received))
    return "\n".join(lines) + "\n"


def _assert_or_record(name: str, steps: list[tuple[bytes, bytes]], *, platform: str = "cisco_ios") -> None:
    """Compare the transcript against the golden, or record it when explicitly asked."""
    transcript = _format_transcript(steps)
    golden_dir = _GOLDEN_BASE / platform / "telnet"
    golden_path = golden_dir / f"{name}.txt"
    if _RECORD:
        golden_dir.mkdir(parents=True, exist_ok=True)
        golden_path.write_text(transcript, encoding="utf-8")
        pytest.skip(f"recorded golden {golden_path} ({len(transcript)} chars)")
    assert golden_path.exists(), f"golden {golden_path} missing; regenerate with SIMNOS_RECORD_GOLDEN=1"
    expected = golden_path.read_text(encoding="utf-8")
    assert transcript == expected, (
        f"Telnet wire transcript drifted from golden {golden_path}.\n"
        f"If the wire change is intentional, regenerate with SIMNOS_RECORD_GOLDEN=1 and review the diff."
    )


@contextmanager
def _running_telnet_host(device_type: str):
    """Start a single Telnet SimNOS host for *device_type* and yield its port."""
    net = SimNOS(inventory=build_inventory(device_type, server=_TELNET_SERVER))
    net.start()
    try:
        # Real OS-assigned port read back after start (#271).
        yield net.hosts["device"].port
    finally:
        net.stop()


def test_telnet_byte_parity_interactive_session():
    """Pin the full Telnet wire: banner + login, intro/prompt, char echo,
    CR/LF/CRLF, NUL drop (CR NUL terminator), empty line, help, mode
    transitions, unknown command, exit."""
    with _running_telnet_host("cisco_ios") as port:
        script = [
            # The telnetlib3 test client negotiates NAWS (window size), so page_rows()
            # is set and `show vlan` (30 lines) would page at `--More--`. A real
            # scraper disables paging first; doing so here reproduces the pre-paging
            # wire byte-for-byte for every following step (#307 / P3-4, claude#4 —
            # telnet was NOT assumed safe, it was measured to negotiate NAWS).
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
            b"show vlan\r\x00",  # CR NUL pair (Telnet): NUL consumed, one dispatch
            b"show vlan\n",  # bare LF terminator
            b"exit\r",  # exit command (mode-dependent behaviour)
        ]
        steps = asyncio.run(capture_telnet_transcript(port, script))
    _assert_or_record("interactive_session", steps)


def test_telnet_byte_parity_session_close_command():
    """Pin the Telnet wire for a real session-closing command.

    Typing ``ex`` on alcatel_aos abbreviation-resolves to the all-modes BASIC
    ``exit`` (#327 Tier 3 removed the standalone ``ex`` stub): char echoes + the
    newline echo, then the server closes (no body, no prompt) — same as the SSH
    session_close golden but over Telnet.
    """
    with _running_telnet_host("alcatel_aos") as port:
        steps = asyncio.run(capture_telnet_transcript(port, [b"ex\r"]))
    _assert_or_record("session_close", steps, platform="alcatel_aos")
