"""
Tests for netmiko init compatibility, send_command response, and shutdown/EOF regression.

Verifies that:
- netmiko session_preparation() does not produce "Unknown command" (#69, #71)
- Unknown commands are handled gracefully without crashing
- send_command returns the defined output for each platform (#76)
- callable (py plugin override) outputs round-trip through netmiko,
  with the sweep classification contract pinned directly (#230)
- Shell exits cleanly on shutdown without thread leaks (#71 regression)
"""

import contextlib
import dataclasses
import sys
import threading

from netmiko import ConnectHandler
import pytest

from simnos import SimNOS
from simnos.core.nos import Nos
from simnos.core.resolved_command import ResolvedCommand, ResolvedOutput
from simnos.plugins.nos import nos_plugins
from simnos.plugins.shell.cmd_shell import build_resolved_platform
from tests._platform_quirks import INIT_UNKNOWN_CMD_ALLOWED
from tests.utils import (
    TEST_PASSWORD,
    TEST_USERNAME,
    build_inventory,
    build_synthetic_platform,
    get_platforms_from_md,
    get_py_platforms,
    netmiko_device,
)

HOSTNAME = "router"  # Inventory host key; also used as base_prompt in output formatting


def _make_simnos(device_type):
    """Create a SimNOS instance for a single device on an ephemeral port (#271).

    `HOSTNAME` is kept as the host key because it doubles as the base_prompt
    used in the output-formatting assertions below. The real bound port is read
    back from `net.hosts[HOSTNAME].port` after `start()`.
    """
    return SimNOS(inventory=build_inventory(device_type, host_key=HOSTNAME))


def _device(device_type, port, **extra):
    """Build netmiko ConnectHandler kwargs for a single-device SimNOS on `port`."""
    creds = {"username": TEST_USERNAME, "password": TEST_PASSWORD, "port": port}
    return netmiko_device(device_type, creds, **extra)


class TestNetmikoInitCompat:
    """Test netmiko session_preparation() compatibility."""

    @pytest.mark.timeout(30)
    @pytest.mark.parametrize("device_type", get_platforms_from_md())
    def test_no_unknown_command_on_init(self, device_type, tmp_path):
        """ConnectHandler init should not produce 'Unknown command'."""
        if device_type in INIT_UNKNOWN_CMD_ALLOWED:
            pytest.skip(f"{device_type}: {INIT_UNKNOWN_CMD_ALLOWED[device_type].reason}")

        log_file = tmp_path / f"session_{device_type}.log"
        net = _make_simnos(device_type)
        try:
            net.start()
            device = _device(device_type, net.hosts[HOSTNAME].port, session_log=str(log_file))
            with ConnectHandler(**device):
                pass
            session_output = log_file.read_text()
            assert "Unknown command" not in session_output, (
                f"{device_type}: 'Unknown command' found in session log during init"
            )
        finally:
            net.stop()

    @pytest.mark.timeout(30)
    @pytest.mark.parametrize("device_type", get_platforms_from_md())
    def test_unknown_command_graceful(self, device_type):
        """Unknown commands should not crash the shell."""
        net = _make_simnos(device_type)
        try:
            net.start()
            device = _device(device_type, net.hosts[HOSTNAME].port)
            with ConnectHandler(**device) as conn:
                output = conn.send_command(
                    "this_command_does_not_exist_12345",
                    read_timeout=10,
                )
                assert isinstance(output, str)
                # Verify session is still alive after unknown command
                follow_up = conn.send_command_timing("?")
                assert isinstance(follow_up, str)
        finally:
            net.stop()


def _get_test_command(device_type: str) -> tuple[str, str] | None:
    """Pick a testable command from the platform's resolved A3 commands.

    Selection priority:
    1. First non-empty literal output without curly braces
    2. First non-empty literal output with curly braces (fallback)

    Outputs with curly braces are deprioritized because they may contain
    platform-specific markers ({master:0} on Juniper) that interfere with
    netmiko prompt detection; the no-brace path also makes the caller's
    `.format(base_prompt=...)` a no-op on the literal text.

    Excludes: special commands (_default_ etc.), handler/template output,
    exit / transition commands, and commands outside the initial mode.
    """
    if device_type not in nos_plugins:
        return None

    nos = Nos(filename=nos_plugins[device_type])
    platform = nos.resolved_platform
    assert platform is not None, f"{device_type}: no A3 platform data (#317 P-4)"
    initial = platform.initial_mode
    fallback = None

    for cmd_name, rc in platform.commands.items():
        if cmd_name.startswith("_") and cmd_name.endswith("_"):
            continue
        if cmd_name in ("enable", "exit", "quit", "logout", "ex"):
            continue
        if rc.new_mode or rc.exit:
            continue
        # A `challenge:` command (#338) waits for an interactive answer in its
        # firing mode (e.g. alcatel_sros `enable-admin` in user mode), so a plain
        # send_command would hang on its sub-prompt. Its literal `output` is only
        # the non-firing-mode response — never a valid initial-mode probe here.
        if rc.challenge:
            continue
        if rc.output.kind != "literal" or not rc.output.text or not rc.output.text.strip():
            continue
        # Valid in the initial mode? (empty mode set = valid in every mode.)
        if rc.modes and initial not in rc.modes:
            continue
        text = rc.output.text
        if "{" not in text:
            return (cmd_name, text)
        if fallback is None:
            fallback = (cmd_name, text)

    return fallback


# (platform, command) pairs whose callable output depends on wall-clock
# time. The expected value computed in the test process would race the
# server-side call, so they are excluded from the e2e content sweep;
# their format is pinned by the device-class unit tests
# (tests/plugins/nos/) instead. Platform-qualified on purpose: a future
# platform whose same-named command IS deterministic stays in the sweep.
# If a new py plugin adds a time-dependent callable without listing it
# here, the sweep fails on content mismatch — add the pair here and pin
# the format in the unit tests for that platform.
TIME_DEPENDENT_COMMANDS = {("cisco_ios", "show clock"), ("arista_eos", "show clock")}


def _get_callable_test_commands(
    device_type: str, base_prompt: str = HOSTNAME
) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Collect (cmd, expected) pairs for the callable-output e2e sweep.

    Thin lookup wrapper: loads the same merged Nos the server uses
    (`Host.start` equivalent) and delegates to
    `_classify_callable_commands`, which is kept separate so its
    classification contract can be pinned with a synthetic Nos.
    """
    return _classify_callable_commands(Nos(filename=nos_plugins[device_type]), device_type, base_prompt)


def _classify_callable_commands(
    nos: Nos, device_type: str, base_prompt: str
) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Classify the merged view's handler commands into the (initial, enable) sweep phases.

    Returns two lists of (cmd, expected): commands runnable at the initial
    prompt and commands requiring enable mode. Since #317 P-2 the dynamic
    commands are the merged `ResolvedPlatform`'s ``kind == "handler"`` entries
    (A3 ``handler:`` refs and custom legacy-dict callables both normalize
    there), and handlers are output-only (`str | None`) — a command that also
    carries a transition (`new_mode` / `exit` / `transitions`) is skipped like
    the static sweep does (the flat sweep cannot run it safely).

    A handler command valid in neither user nor enable mode (e.g.
    config-mode-only) raises AssertionError instead of being silently
    dropped: extend the sweep (config phase) or add a dedicated exclusion
    set — do not reuse TIME_DEPENDENT_COMMANDS for non-time reasons.

    The expected value is computed by invoking the handler with the same
    contract as `CMDShell._invoke_handler` and taken **verbatim** — the shell
    does not apply `.format(base_prompt=...)` to handler output (#241 / D-b:
    handlers receive base_prompt and format themselves), so the oracle must
    not either. A None return has no content to verify and is skipped.

    Note: classification itself invokes the handlers (expected), so a
    state-mutating handler would advance device state here before the e2e
    session runs — fine today (all make_* are read-only), but a
    sweep-eligibility redesign is needed if that ever changes.
    """
    merged = build_resolved_platform(nos, {})
    prompt_of = {name: mode.render_prompt(base_prompt) for name, mode in merged.modes.items()}

    initial_cmds: list[tuple[str, str]] = []
    enable_cmds: list[tuple[str, str]] = []
    unclassified: list[str] = []
    for cmd_name, rc in merged.commands.items():
        out = rc.output
        if out.kind != "handler" or out.handler is None or (device_type, cmd_name) in TIME_DEPENDENT_COMMANDS:
            continue
        if rc.new_mode or rc.exit or rc.transitions:
            continue  # transition commands are unit/parity-test scope (a flat sweep cannot run them)
        # Empty `modes` = valid in every mode; sweep it from the initial prompt.
        if not rc.modes or "user" in rc.modes:
            current_mode, bucket = "user", initial_cmds
        elif "enable" in rc.modes:
            current_mode, bucket = "enable", enable_cmds
        else:
            unclassified.append(cmd_name)
            continue
        expected = out.handler(
            nos.device,
            base_prompt=base_prompt,
            current_mode=current_mode,
            current_prompt=prompt_of.get(current_mode, ""),
            command=cmd_name,
        )
        if expected is None:
            continue  # a None return writes nothing -> no content to verify
        # Anything else non-str is a broken str|None contract (#317 P-2) — fail
        # here rather than silently dropping it as "nothing to verify", which
        # would let a contract-violating handler shrink the sweep unnoticed
        # (1st round codex#1).
        assert isinstance(expected, str), (
            f"{device_type}: handler command {cmd_name!r} returned {type(expected).__name__} "
            "(contract is str | None) — fix the handler, do not exclude it here"
        )
        bucket.append((cmd_name, expected))

    assert not unclassified, (
        f"{device_type}: handler commands outside the initial/enable "
        f"sweep phases: {unclassified}. Extend the sweep (e.g. config phase) or add a "
        f"dedicated exclusion set with a reason — do not reuse TIME_DEPENDENT_COMMANDS."
    )
    return initial_cmds, enable_cmds


class TestSendCommandResponse:
    """Test that send_command returns the defined output for each platform (#76)."""

    @pytest.mark.flaky(reruns=2, reruns_delay=1)
    @pytest.mark.timeout(30)
    @pytest.mark.parametrize("device_type", get_platforms_from_md())
    def test_send_command_returns_defined_output(self, device_type: str):
        """Defined command should return matching output via send_command.

        Marked `flaky` (reruns=2): netmiko's auto-enable on certain device_types
        (observed: broadcom_icos) can intermittently fail on slow CI runners with
        "Failed to enter enable mode" due to SSH handshake / banner timing race.
        The race is in the netmiko side and not deterministically reproducible;
        a 2-rerun retry stabilizes CI without masking deterministic regressions.
        """
        result = _get_test_command(device_type)
        assert result is not None, (
            f"No testable command found for {device_type}. "
            "Every docs-listed platform must have at least one testable command."
        )

        cmd, expected_raw = result
        expected = expected_raw.format(base_prompt=HOSTNAME)
        net = _make_simnos(device_type)
        try:
            net.start()
            device = _device(device_type, net.hosts[HOSTNAME].port)
            with ConnectHandler(**device) as conn:
                output = conn.send_command(cmd, read_timeout=15)
                assert isinstance(output, str)
                assert output.strip() == expected.strip(), (
                    f"{device_type}: '{cmd}' returned unexpected output.\n"
                    f"  expected: {expected.strip()!r}\n"
                    f"  actual:   {output.strip()!r}"
                )
        finally:
            net.stop()

    @pytest.mark.flaky(reruns=2, reruns_delay=1)
    # Sweep test (multiple commands + enable), not a single-command test:
    # 60s instead of the 30s used by the single-shot tests above.
    @pytest.mark.timeout(60)
    @pytest.mark.parametrize("device_type", get_py_platforms())
    def test_send_command_returns_callable_output(self, device_type: str):
        """Callable (py override) outputs must round-trip through netmiko.

        Q16 (T-14 / #230): the static-command test above systematically
        excludes callable outputs, so the dynamic outputs that py plugins
        exist for had no e2e content verification. One session per
        platform sweeps every eligible callable: initial-prompt commands
        first, then enable-only commands after conn.enable() (skipped
        when empty).

        Marked `flaky` (reruns=2): same rationale as
        test_send_command_returns_defined_output (netmiko auto-enable
        handshake race on slow CI runners).
        """
        initial_cmds, enable_cmds = _get_callable_test_commands(device_type)
        if not (initial_cmds or enable_cmds):
            # Legitimate since #317 P-2 for platforms whose only dynamic
            # commands are time-dependent (cisco/arista `show clock`): the
            # formerly-callable statics are A3 data now, swept by the static
            # tests. Guard the skip on an explicit denylist entry so an
            # accidental full coverage shrink (helper regression dropping every
            # handler) still fails instead of skipping.
            assert any(platform == device_type for platform, _cmd in TIME_DEPENDENT_COMMANDS), (
                f"No eligible handler command found for {device_type} and none are "
                "time-dependent-excluded — the sweep lost its dynamic coverage."
            )
            pytest.skip(f"{device_type}: all dynamic outputs are time-dependent (format pinned by unit tests)")

        net = _make_simnos(device_type)
        try:
            net.start()
            device = _device(device_type, net.hosts[HOSTNAME].port)
            with ConnectHandler(**device) as conn:

                def check(cmds: list[tuple[str, str]], phase: str) -> None:
                    for cmd, expected in cmds:
                        output = conn.send_command(cmd, read_timeout=15)
                        assert isinstance(output, str)
                        assert output.strip() == expected.strip(), (
                            f"{device_type}: '{cmd}' ({phase}) returned unexpected output.\n"
                            f"  expected: {expected.strip()!r}\n"
                            f"  actual:   {output.strip()!r}"
                        )

                check(initial_cmds, "initial prompt")
                if enable_cmds:
                    conn.enable()
                    check(enable_cmds, "enable mode")
        finally:
            net.stop()


class TestClassifyCallableCommands:
    """Pin the classification contract of `_classify_callable_commands`.

    The e2e sweep above only exercises the current 3 py platforms'
    happy path; these tests pin the maintenance contract directly with
    a synthetic Nos (same pattern as tests/plugins/test_tap_test_helpers.py)
    so a future helper change fails here first, not via silent coverage
    shrinkage in the sweep.
    """

    @staticmethod
    def _synthetic_nos(commands: dict[str, "ResolvedCommand"]) -> Nos:
        """Build a minimal Nos over an in-memory 3-mode `ResolvedPlatform`.

        Successor of the removed `dict_args` vehicle (#317 P-4): the handler
        commands are constructed natively, the same shape the A3 loader + merge
        bind produces.
        """
        platform = build_synthetic_platform(
            {
                "user": "{{ base_prompt }}>",
                "enable": "{{ base_prompt }}#",
                "config": "{{ base_prompt }}(config)#",
            }
        )
        nos = Nos(name="synth")
        nos.resolved_platform = dataclasses.replace(platform, commands=commands)
        return nos

    @staticmethod
    def _handler_cmd(name: str, handler, *, modes: tuple[str, ...], new_mode: str | None = None) -> "ResolvedCommand":
        """One bound-handler `ResolvedCommand` (the post-merge dispatch shape)."""
        return ResolvedCommand(
            name=name,
            modes=frozenset(modes),
            new_mode=new_mode,
            output=ResolvedOutput(kind="handler", handler=handler),
            variants=(),
            help="",
            exit=False,
            type="custom",
        )

    def test_config_only_handler_fails_loudly(self):
        """A handler command outside the sweep phases is coverage loss."""
        weird = self._handler_cmd("weird", lambda device, **kwargs: "static", modes=("config",))
        nos = self._synthetic_nos({"weird": weird})
        with pytest.raises(AssertionError, match=r"outside the initial/enable\s+sweep phases: \['weird'\]"):
            _classify_callable_commands(nos, "synth", HOSTNAME)

    def test_transition_handler_command_is_unit_scope(self):
        """A handler command carrying a static transition is excluded, no fail.

        Transitions are static authoring data since #317 P-2 (handlers are
        output-only); a flat sweep cannot run a mode-changing command, so it is
        skipped like the static sweep skips `new_mode` commands.
        """
        modey = self._handler_cmd("modey", lambda device, **kwargs: "", modes=("user",), new_mode="enable")
        initial_cmds, enable_cmds = _classify_callable_commands(
            self._synthetic_nos({"modey": modey}), "synth", HOSTNAME
        )
        assert initial_cmds == []
        assert enable_cmds == []

    def test_none_returning_handler_is_skipped(self):
        """A None-returning handler writes nothing — no content to verify, no fail."""
        silent = self._handler_cmd("silent", lambda device, **kwargs: None, modes=("user",))
        initial_cmds, enable_cmds = _classify_callable_commands(
            self._synthetic_nos({"silent": silent}), "synth", HOSTNAME
        )
        assert initial_cmds == []
        assert enable_cmds == []

    def test_contract_breaking_handler_fails_loudly(self):
        """A non-str|None return fails classification instead of shrinking the sweep.

        Only None means "no content to verify"; a dict/list return is a broken
        #317 P-2 handler contract, and silently dropping it would let a
        contract-violating handler disappear from the e2e sweep (and, combined
        with the denylist skip, potentially the whole platform) unnoticed
        (1st round codex#1).
        """
        broken = self._handler_cmd("broken", lambda device, **kwargs: {"output": "x"}, modes=("user",))
        nos = self._synthetic_nos({"broken": broken})
        with pytest.raises(AssertionError, match=r"returned dict \(contract is str \| None\)"):
            _classify_callable_commands(nos, "synth", HOSTNAME)

    def test_denylist_is_platform_qualified(self):
        """Another platform's deterministic 'show clock' stays in the sweep."""
        clock = self._handler_cmd("show clock", lambda device, **kwargs: "deterministic", modes=("user",))
        initial_cmds, enable_cmds = _classify_callable_commands(
            self._synthetic_nos({"show clock": clock}), "synth", HOSTNAME
        )
        assert initial_cmds == [("show clock", "deterministic")]
        assert enable_cmds == []

    def test_bucketing_and_expected_verbatim(self):
        """initial / enable / dual-mode (-> initial) bucketing + verbatim oracle.

        The `{base_prompt}` placeholder in 'enable only' stays **unsubstituted**
        in the expected value: the shell does not format handler output
        (#241 / D-b), so the sweep oracle must take the return verbatim —
        this pin replaces the pre-#241 one that expected the `.format` step.
        """
        nos = self._synthetic_nos(
            {
                "init only": self._handler_cmd("init only", lambda device, **kwargs: "from init", modes=("user",)),
                "enable only": self._handler_cmd(
                    "enable only", lambda device, **kwargs: "hostname {base_prompt}", modes=("enable",)
                ),
                "dual mode": self._handler_cmd(
                    "dual mode", lambda device, **kwargs: "from dual", modes=("user", "enable")
                ),
            }
        )
        initial_cmds, enable_cmds = _classify_callable_commands(nos, "synth", HOSTNAME)
        assert initial_cmds == [("init only", "from init"), ("dual mode", "from dual")]
        assert enable_cmds == [("enable only", "hostname {base_prompt}")]


class TestShutdownEOF:
    """Regression tests for shutdown/EOF handling (#71)."""

    @staticmethod
    def _join_all_threads():
        """Join all non-main, non-pytest threads."""
        for thread in threading.enumerate():
            if thread is not threading.main_thread() and "pytest_timeout" not in thread.name:
                thread.join(timeout=5)

    @pytest.mark.timeout(30)
    def test_shell_exits_cleanly_on_server_stop(self):
        """Shell should exit on EOF (dispatch close branch) when server stops, no thread leaks."""
        net = _make_simnos("cisco_ios")
        try:
            net.start()
            device = _device("cisco_ios", net.hosts[HOSTNAME].port)
            with ConnectHandler(**device):
                pass
        finally:
            net.stop()
            self._join_all_threads()

        n_threads = 2 if sys.platform == "win32" else 1
        assert threading.active_count() == n_threads

    @pytest.mark.timeout(30)
    def test_server_stop_while_connected(self):
        """Server stop during active connection should not hang."""
        net = _make_simnos("cisco_ios")
        net.start()
        try:
            device = _device("cisco_ios", net.hosts[HOSTNAME].port)
            conn = ConnectHandler(**device)
            # Stop server while connection is still open
            net.stop()
            # Connection should be closed by server shutdown
            with contextlib.suppress(Exception):
                conn.disconnect()
        finally:
            self._join_all_threads()

        n_threads = 2 if sys.platform == "win32" else 1
        assert threading.active_count() == n_threads
