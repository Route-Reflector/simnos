"""telnetlib3 client helpers for the async Telnet server tests (#297 Stage 3).

The Telnet wire is captured with a **telnetlib3 client** (binary ``encoding=False``)
so the transport-level IAC negotiation is absorbed by the client and only the
application-layer bytes (banner / login / echo / body / prompt) are observed — the
Telnet analogue of the SSH byte-parity test driving a raw paramiko channel
(post-KEX/auth = application layer). The captured transcript is therefore directly
comparable to the SSH wire produced by the shared ``run_async_push_session``.
"""

import asyncio

import telnetlib3

from tests.utils import TEST_PASSWORD, TEST_USERNAME

_HOST = "127.0.0.1"
_IDLE = 0.4  # seconds of silence that marks the end of one response (matches the SSH test)
_OVERALL = 10.0  # max seconds to wait for the first byte of a response
# Client negotiation settle floor; small but enough for loopback option exchange.
_CONNECT_MINWAIT = 0.3


async def _read_idle(reader: "telnetlib3.TelnetReader") -> bytes:
    """Read until the wire goes idle (mirror of the SSH test's ``_drain``).

    Waits up to ``_OVERALL`` for the first byte, then treats an ``_IDLE`` gap as
    the end of the response. The byte *content* is deterministic, so concatenating
    across reads yields the same transcript every run regardless of segmentation.
    """
    out = bytearray()
    loop = asyncio.get_running_loop()
    start = loop.time()
    while True:
        try:
            chunk = await asyncio.wait_for(reader.read(4096), timeout=_IDLE)
        except TimeoutError:
            if out:
                break  # had data, now idle -> response complete
            if loop.time() - start > _OVERALL:
                break  # nothing ever arrived
            continue
        if not chunk:
            break  # EOF
        out += chunk
    return bytes(out)


async def capture_telnet_transcript(
    port: int,
    script: list[bytes],
    *,
    username: str = TEST_USERNAME,
    password: str = TEST_PASSWORD,
) -> list[tuple[bytes, bytes]]:
    """Log in over Telnet and run *script*, returning (sent, received) steps.

    The login preamble (banner + ``Username:``/``Password:`` echo) is captured as
    its own steps so the golden pins the in-band auth wire too; the remaining steps
    are the scripted command interaction.
    """
    reader, writer = await telnetlib3.open_connection(_HOST, port, encoding=False, connect_minwait=_CONNECT_MINWAIT)
    steps: list[tuple[bytes, bytes]] = []
    try:
        steps.append((b"<connect>", await _read_idle(reader)))  # banner + Username:
        writer.write(username.encode() + b"\r")
        await writer.drain()
        steps.append((b"<username>", await _read_idle(reader)))  # echo + Password:
        writer.write(password.encode() + b"\r")
        await writer.drain()
        steps.append((b"<password>", await _read_idle(reader)))  # intro + first prompt
        for chunk in script:
            writer.write(chunk)
            await writer.drain()
            steps.append((chunk, await _read_idle(reader)))
    finally:
        writer.close()
    return steps


async def open_and_login(
    port: int, *, username: str = TEST_USERNAME, password: str = TEST_PASSWORD
) -> "tuple[telnetlib3.TelnetReader, telnetlib3.TelnetWriter]":
    """Open a Telnet connection and complete login; return its (reader, writer).

    The push session is running on the server when this returns; the caller drives
    and closes the connection. Used by the lifecycle test that holds a live session
    open across ``stop`` (the telnet-specific active-session drain).
    """
    reader, writer = await telnetlib3.open_connection(_HOST, port, encoding=False, connect_minwait=_CONNECT_MINWAIT)
    await _read_idle(reader)  # banner + Username:
    writer.write(username.encode() + b"\r")
    await writer.drain()
    await _read_idle(reader)  # echo + Password:
    writer.write(password.encode() + b"\r")
    await writer.drain()
    await _read_idle(reader)  # intro + first prompt
    return reader, writer


async def telnet_login_run(port: int, command: bytes, *, marker: bytes) -> bytes:
    """Log in and run one *command*, returning the response; assert-friendly helper.

    Used by the mixed-transport lifecycle test to confirm a Telnet host actually
    serves (not just that it starts/stops). Reads until *marker* (the expected
    prompt) appears or the wire idles.
    """
    reader, writer = await telnetlib3.open_connection(_HOST, port, encoding=False, connect_minwait=_CONNECT_MINWAIT)
    try:
        await _read_idle(reader)  # banner + Username:
        writer.write(TEST_USERNAME.encode() + b"\r")
        await writer.drain()
        await _read_idle(reader)  # echo + Password:
        writer.write(TEST_PASSWORD.encode() + b"\r")
        await writer.drain()
        await _read_idle(reader)  # intro + prompt
        writer.write(command)
        await writer.drain()
        out = bytearray()
        loop = asyncio.get_running_loop()
        deadline = loop.time() + _OVERALL
        while marker not in out and loop.time() < deadline:
            chunk = await _read_idle(reader)
            if not chunk:
                break
            out += chunk
        return bytes(out)
    finally:
        writer.close()
