"""Integration tests for the asyncssh SSH transport + shared loop (#297 Stage 2).

Covers the Stage 2 acceptance gates the byte-parity goldens don't:

- **100-host concurrent, 0 failures** (§5) — the headline finding from the spike
  (the W2-without-W3 hybrid dropped sessions under 100-host load; W3 push dispatch
  on the shared loop must not).
- **lifecycle** (§5) — partial stop keeps other hosts serving, restart, double
  stop, and mixed SSH(async) + Telnet(async, Stage 3) teardown — plus the
  no-thread-leak / loop-converges-to-STOPPED guarantee (executor convergence).

These drive raw paramiko channels (byte-exact, lighter than netmiko) against real
``AsyncSshServer`` listeners on the SimNOS-owned shared loop.
"""

import asyncio
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager, suppress
import os
import socket
import threading
import time

import asyncssh
import paramiko
import pytest

from simnos import SimNOS
from simnos.core.pydantic_models import EPHEMERAL_PORT
from simnos.core.shared_loop import LoopState, SharedLoop
from simnos.plugins.servers.async_server_base import AsyncServerBase
from simnos.plugins.shell.cmd_shell import CMDShell
from tests.plugins.telnet_test_helpers import telnet_login_run
from tests.utils import TEST_PASSWORD, TEST_USERNAME

_HOST = "127.0.0.1"

# Stage 2 AC is "100 hosts, 0 failures". Tunable down for a constrained CI box via
# the env var; the default exercises the real acceptance number.
_STRESS_HOSTS = int(os.environ.get("SIMNOS_ASYNC_STRESS_HOSTS", "100"))

# Budget for the dispatch worker pool to drain after stop. The bounded executor is
# shut down with wait=False (does not join the daemon `simnos-dispatch` workers, by
# design — a non-cooperative handler must not block stop), so the workers exit on
# their own shortly after; a generous deadline keeps the convergence assertion from
# flaking on a loaded CI box (claude 1st#2).
_THREAD_CONVERGE_DEADLINE = 10


def _multi_host_inventory(n: int, device_type: str = "cisco_ios") -> dict:
    """Build an *n*-host single-platform inventory (hosts ``h0``..``h{n-1}``).

    Every host binds an ephemeral port (#271): the OS assigns a free port at bind
    time, so there is no TOCTOU window for a parallel worker to steal. Read the real
    ports back with ``_host_ports`` after ``start()``.
    """
    hosts = {
        f"h{i}": {
            "username": TEST_USERNAME,
            "password": TEST_PASSWORD,
            "port": EPHEMERAL_PORT,
            "device_type": device_type,
        }
        for i in range(n)
    }
    return {"hosts": hosts}


def _host_ports(net: SimNOS, n: int) -> list[int]:
    """The real OS-assigned ports of hosts ``h0``..``h{n-1}`` after start (#271)."""
    return [net.hosts[f"h{i}"].port for i in range(n)]


def _run_one_command(port: int, command: bytes, expect: bytes) -> bool:
    """Connect, auth, run *command* over a raw paramiko channel; True if *expect* seen."""
    sock = socket.create_connection((_HOST, port), timeout=10)
    transport = paramiko.Transport(sock)
    try:
        transport.start_client(timeout=10)
        transport.auth_password(TEST_USERNAME, TEST_PASSWORD)
        channel = transport.open_session(timeout=10)
        channel.get_pty()
        channel.invoke_shell()
        channel.sendall(command)
        channel.settimeout(10)
        buf = b""
        deadline = time.monotonic() + 10
        while expect not in buf and time.monotonic() < deadline:
            try:
                chunk = channel.recv(4096)
            except TimeoutError:
                break
            if not chunk:
                break
            buf += chunk
        channel.close()
        return expect in buf
    finally:
        transport.close()


@contextmanager
def _running(inventory: dict):
    net = SimNOS(inventory=inventory)
    net.start()
    try:
        yield net
    finally:
        net.stop()


@pytest.mark.timeout(180)
def test_async_ssh_100_host_concurrent_no_failures():
    """100 hosts, one concurrent client each, every session must succeed (§5).

    This is the spike's failure scenario (W2-without-W3 dropped sessions under
    100-host load). With W3 push dispatch on the shared loop + bounded executor,
    failures must be 0. After stop the loop converges to STOPPED with no leaked
    thread (executor convergence — the dispatch worker pool is released).
    """
    n = _STRESS_HOSTS
    inventory = _multi_host_inventory(n)
    baseline = threading.active_count()
    with _running(inventory) as net:
        ports = _host_ports(net, n)
        with ThreadPoolExecutor(max_workers=n) as pool:
            results = list(pool.map(lambda p: _run_one_command(p, b"show vlan\r", b"VLAN Name"), ports))
        assert all(results), f"{results.count(False)}/{n} concurrent sessions failed"
        assert net._shared_loop.refcount == n

    assert net._shared_loop.state is LoopState.STOPPED
    # Executor convergence: the loop thread + bounded dispatch pool are released.
    deadline = time.monotonic() + _THREAD_CONVERGE_DEADLINE
    while threading.active_count() > baseline and time.monotonic() < deadline:
        time.sleep(0.05)
    assert threading.active_count() <= baseline, f"threads did not converge: {[t.name for t in threading.enumerate()]}"


def test_partial_stop_keeps_other_host_serving():
    """Stopping one async host leaves the loop up and the other host reachable (§1)."""
    with _running(_multi_host_inventory(2)) as net:
        # Capture the resolved ephemeral ports while both are up (stop() does not
        # reset host.port, so h0's port stays readable after it is stopped).
        h0_port, h1_port = _host_ports(net, 2)
        # Stop only h0; the shared loop must keep running for h1.
        net.stop(hosts=["h0"])
        assert net._shared_loop.state is LoopState.RUNNING
        assert net._shared_loop.refcount == 1
        # h1 still serves.
        assert _run_one_command(h1_port, b"show vlan\r", b"VLAN Name")
        # h0's port is free again (listener released) — a fresh connect is refused.
        with pytest.raises((ConnectionRefusedError, OSError)):
            socket.create_connection((_HOST, h0_port), timeout=2).close()


def test_restart_after_full_stop():
    """A host can be stopped and started again on the same SimNOS (restart, §1)."""
    net = SimNOS(inventory=_multi_host_inventory(1))
    try:
        net.start()
        # The ephemeral port resolves on first start and stays fixed across
        # stop→start (Host.stop does not reset host.port, #271 / D4).
        (port,) = _host_ports(net, 1)
        assert _run_one_command(port, b"show vlan\r", b"VLAN Name")
        net.stop()
        assert net._shared_loop.state is LoopState.STOPPED
        net.start()  # restart: loop lazily recreated
        assert net._shared_loop.state is LoopState.RUNNING
        assert _run_one_command(port, b"show vlan\r", b"VLAN Name")
    finally:
        net.stop()


def test_double_stop_is_idempotent():
    """Calling stop twice must not raise and leaves the loop STOPPED (§1a)."""
    with _running(_multi_host_inventory(1)) as net:
        net.stop()
        net.stop()  # second stop is a no-op
        assert net._shared_loop.state is LoopState.STOPPED


def test_start_failure_converges_with_no_leak(monkeypatch):
    """A failed create_server leaves the loop cleanable + no thread leak (codex 2nd#6).

    create_server raises (e.g. bind failure): start() must re-raise, Host.start
    rolls back, and the caller's stop() tears the now-idle loop down to STOPPED
    with no orphaned thread.
    """

    async def _failing_create(*args, **kwargs):
        raise OSError("simulated bind failure")

    monkeypatch.setattr(asyncssh, "create_server", _failing_create)

    baseline = threading.active_count()
    net = SimNOS(inventory=_multi_host_inventory(1))
    try:
        with pytest.raises(OSError, match="simulated bind failure"):
            net.start()
    finally:
        net.stop()
    assert net._shared_loop.state is LoopState.STOPPED
    deadline = time.monotonic() + _THREAD_CONVERGE_DEADLINE
    while threading.active_count() > baseline and time.monotonic() < deadline:
        time.sleep(0.05)
    assert threading.active_count() <= baseline


def test_start_timeout_closes_late_acceptor(monkeypatch):
    """A create that completes *after* start() timed out has its listener closed
    via the done-callback — the real timeout→late-acceptor path (codex 3rd#2).

    create_server is slowed past a shortened start timeout and made to complete
    despite the cancel (swallowing CancelledError), modelling an asyncssh create
    that wins the cancel race. The ``_discard_late_acceptor`` done-callback must
    then close the orphaned acceptor.
    """
    closed = threading.Event()

    class _FakeAcceptor:
        def close(self):
            closed.set()

    async def _slow_create(*args, **kwargs):
        # Swallow the cancel and complete anyway -> a "late" acceptor produced
        # after start() gave up (models a create that wins the cancel race).
        with suppress(asyncio.CancelledError):
            await asyncio.sleep(1.0)
        return _FakeAcceptor()

    # The create budget now lives in the shared AsyncServerBase (Stage 3 dedup).
    monkeypatch.setattr("simnos.plugins.servers.async_server_base._CREATE_LISTENER_TIMEOUT", 0.3)
    monkeypatch.setattr(asyncssh, "create_server", _slow_create)

    net = SimNOS(inventory=_multi_host_inventory(1))
    try:
        with pytest.raises(TimeoutError):
            net.start()
        assert closed.wait(timeout=5), "late acceptor was not closed by the done-callback"
    finally:
        net.stop()


def test_discard_late_acceptor_closes_completed_future():
    """The late-acceptor done-callback closes a listener produced after start gave
    up, routing close() onto the loop thread (codex 2nd#2 / gemini 1st#1).

    The callback can fire synchronously on the caller thread (future already done at
    ``add_done_callback`` time), so ``acceptor.close()`` must run via
    ``call_soon_threadsafe`` — not inline — to stay loop-safe. The test asserts both
    that close ran AND that it ran on the loop thread, not the caller thread: a
    regression that closed inline would still set ``closed`` but on the wrong thread,
    so the thread-identity assertion is what actually pins the fix (codex 2nd#2).
    """
    closed = threading.Event()
    close_thread: dict[str, int] = {}

    class _FakeAcceptor:
        def close(self):
            close_thread["ident"] = threading.get_ident()
            closed.set()

    shared_loop = SharedLoop()
    shared_loop.ensure_running()
    # A bare AsyncServerBase carrying only _shared_loop (the one attribute the
    # callback touches); __new__ skips the heavy __init__ while keeping the type.
    server = AsyncServerBase.__new__(AsyncServerBase)
    server._shared_loop = shared_loop

    try:
        future: concurrent.futures.Future = concurrent.futures.Future()
        future.set_result(_FakeAcceptor())
        # The future is already done, so the callback runs inline on THIS thread.
        server._discard_late_acceptor(future)
        assert closed.wait(timeout=5), "acceptor.close() was not scheduled on the loop thread"
        assert close_thread["ident"] != threading.get_ident(), "close() ran on the caller thread, not the loop"
    finally:
        shared_loop.teardown_if_idle()


def test_discard_late_acceptor_ignores_cancelled_future():
    """A cancelled create future has no acceptor to reclaim — callback is a no-op."""
    server = AsyncServerBase.__new__(AsyncServerBase)
    server._shared_loop = None

    future: concurrent.futures.Future = concurrent.futures.Future()
    future.cancel()
    server._discard_late_acceptor(future)  # must not raise


def test_stop_converges_with_inflight_slow_dispatch(monkeypatch):
    """stop must converge even with a non-cooperative (slow) in-flight dispatch (codex 1st#3).

    A dispatch that blocks the executor thread (can't be cancelled) must not hang
    stop: aclose closes the session and cancels the awaiting task within the bounded
    budget, and the late executor result lands on a closed transport (generation
    isolation — the result never reaches the wire). The orphaned worker exits on its
    own afterwards. Here we pin the convergence + STOPPED state under that load.
    """
    original_dispatch = CMDShell.dispatch

    def slow_dispatch(self, line):
        if line == "slowcmd":
            time.sleep(3)  # non-cooperative: blocks the dispatch worker thread
        return original_dispatch(self, line)

    monkeypatch.setattr(CMDShell, "dispatch", slow_dispatch)

    with _running(_multi_host_inventory(1)) as net:
        (port,) = _host_ports(net, 1)
        sock = socket.create_connection((_HOST, port), timeout=10)
        transport = paramiko.Transport(sock)
        try:
            transport.start_client(timeout=10)
            transport.auth_password(TEST_USERNAME, TEST_PASSWORD)
            channel = transport.open_session(timeout=10)
            channel.get_pty()
            channel.invoke_shell()
            time.sleep(0.3)  # let the intro flush
            channel.sendall(b"slowcmd\r")  # dispatch now sleeping in the executor
            time.sleep(0.5)
            started = time.monotonic()
            net.stop()  # stop while the dispatch is in-flight
            elapsed = time.monotonic() - started
        finally:
            transport.close()

    assert net._shared_loop.state is LoopState.STOPPED
    # Must converge well under the drain budget (10s): a regression that blocks on
    # the non-cooperative dispatch instead of detaching it stalls to ~10s.
    assert elapsed < 8, f"stop did not converge with an in-flight dispatch ({elapsed:.1f}s)"


def _write_authorized_keys(tmp_path, key: paramiko.PKey) -> str:
    """Write *key*'s public half to an OpenSSH authorized_keys file; return its path."""
    path = tmp_path / "authorized_keys"
    path.write_text(f"{key.get_name()} {key.get_base64()}\n")
    return str(path)


def _host_with_authorized_keys(authorized_keys: str) -> dict:
    """Single host ``device`` on an ephemeral port (#271) with publickey auth configured."""
    return {
        "hosts": {
            "device": {
                "username": TEST_USERNAME,
                "password": TEST_PASSWORD,
                "port": EPHEMERAL_PORT,
                "device_type": "cisco_ios",
                "server": {
                    "plugin": "AsyncSshServer",
                    "configuration": {"address": "127.0.0.1", "authorized_keys": authorized_keys},
                },
            }
        }
    }


def test_publickey_auth_accepts_authorized_key(tmp_path):
    """An authorized public key authenticates (asyncssh validate_public_key)."""
    key = paramiko.RSAKey.generate(2048)
    inventory = _host_with_authorized_keys(_write_authorized_keys(tmp_path, key))
    with _running(inventory) as net:
        port = net.hosts["device"].port
        sock = socket.create_connection((_HOST, port), timeout=10)
        transport = paramiko.Transport(sock)
        try:
            transport.start_client(timeout=10)
            transport.auth_publickey(TEST_USERNAME, key)  # raises on failure
            assert transport.is_authenticated()
        finally:
            transport.close()


def _advertised_auth_methods(port: int) -> list[str]:
    """Return the auth methods the server advertises (via paramiko's auth_none probe)."""
    sock = socket.create_connection((_HOST, port), timeout=10)
    transport = paramiko.Transport(sock)
    try:
        transport.start_client(timeout=10)
        try:
            transport.auth_none(TEST_USERNAME)
            return []  # none accepted (no auth required) — not our cisco_ios case
        except paramiko.BadAuthenticationType as e:
            return list(e.allowed_types)
    finally:
        transport.close()


def test_publickey_advertised_only_with_authorized_keys(tmp_path):
    """publickey is advertised iff authorized_keys is set (paramiko parity, E2).

    Advertising it on a no-keys host would invite a key-offering paramiko client
    into the auth-retry SERVICE_REQUEST-resend disconnect; password-first clients
    are unaffected either way.
    """
    key = paramiko.RSAKey.generate(2048)
    authed = _host_with_authorized_keys(_write_authorized_keys(tmp_path, key))

    with _running(_multi_host_inventory(1)) as net:
        (no_keys_port,) = _host_ports(net, 1)
        methods = _advertised_auth_methods(no_keys_port)
        assert "password" in methods
        assert "publickey" not in methods  # no keys -> not advertised

    with _running(authed) as net:
        keys_port = net.hosts["device"].port
        methods = _advertised_auth_methods(keys_port)
        assert "publickey" in methods  # keys configured -> advertised


def test_mixed_ssh_async_and_telnet():
    """Async SSH and async Telnet coexist on the shared loop and tear down cleanly.

    Both AsyncSshServer and the telnetlib3 TelnetServer (Stage 3) register on the
    shared loop (refcount == 2, managed_threads == []), both serve, and a full stop
    returns the loop to STOPPED and the process to its thread baseline (§1).
    """
    inventory = {
        "hosts": {
            "ssh": {
                "username": TEST_USERNAME,
                "password": TEST_PASSWORD,
                "port": EPHEMERAL_PORT,
                "device_type": "cisco_ios",
            },
            "telnet": {
                "username": TEST_USERNAME,
                "password": TEST_PASSWORD,
                "port": EPHEMERAL_PORT,
                "device_type": "cisco_ios",
                "server": {"plugin": "TelnetServer", "configuration": {"address": "127.0.0.1"}},
            },
        }
    }
    baseline = threading.active_count()
    with _running(inventory) as net:
        ssh_port = net.hosts["ssh"].port
        telnet_port = net.hosts["telnet"].port
        assert _run_one_command(ssh_port, b"show vlan\r", b"VLAN Name")
        # Telnet is async too now: both hosts are registered on the shared loop.
        telnet_out = asyncio.run(telnet_login_run(telnet_port, b"show vlan\r", marker=b"device>"))
        assert b"VLAN Name" in telnet_out
        assert net._shared_loop.refcount == 2

    assert net._shared_loop.state is LoopState.STOPPED
    deadline = time.monotonic() + _THREAD_CONVERGE_DEADLINE
    while threading.active_count() > baseline and time.monotonic() < deadline:
        time.sleep(0.05)
    assert threading.active_count() <= baseline
