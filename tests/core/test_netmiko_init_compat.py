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
import sys
import threading

from netmiko import ConnectHandler
import pytest

from simnos import SimNOS
from simnos.core.nos import Nos
from simnos.plugins.nos import nos_plugins
from tests._platform_quirks import INIT_UNKNOWN_CMD_ALLOWED
from tests.utils import (
    TEST_PASSWORD,
    TEST_USERNAME,
    build_inventory,
    get_free_port,
    get_platforms_from_md,
    get_py_platforms,
    netmiko_device,
)

HOSTNAME = "router"  # Inventory host key; also used as base_prompt in output formatting


def _make_simnos(device_type, port):
    """Create a SimNOS instance for a single device.

    `HOSTNAME` is kept as the host key because it doubles as the base_prompt
    used in the output-formatting assertions below.
    """
    return SimNOS(inventory=build_inventory(device_type, host_key=HOSTNAME, port=port))


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

        port = get_free_port()
        log_file = tmp_path / f"session_{device_type}.log"
        net = _make_simnos(device_type, port)
        try:
            net.start()
            device = _device(device_type, port, session_log=str(log_file))
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
        port = get_free_port()
        net = _make_simnos(device_type, port)
        try:
            net.start()
            device = _device(device_type, port)
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
    """Pick one command from the Nos-loaded definition for testing.

    Selection priority:
    1. First non-empty string output without curly braces
    2. First non-empty string output with curly braces (fallback)

    Outputs with curly braces are deprioritized because they may contain
    format placeholders ({base_prompt}) or platform-specific markers
    ({master:0} on Juniper) that interfere with netmiko prompt detection.

    Excludes: special commands (_default_ etc.), alias, new_prompt,
    exit flag, callable output, and prompt-mode-changing commands.
    """
    if device_type not in nos_plugins:
        return None

    nos = Nos(filename=nos_plugins[device_type])
    fallback = None

    for cmd_name, cmd_data in nos.commands.items():
        if cmd_name.startswith("_") and cmd_name.endswith("_"):
            continue
        if cmd_name in ("enable", "exit", "quit", "logout", "ex"):
            continue
        if "alias" in cmd_data or "new_prompt" in cmd_data:
            continue
        if cmd_data.get("exit"):
            continue

        output = cmd_data.get("output")
        if not isinstance(output, str) or not output.strip():
            continue

        prompt = cmd_data.get("prompt")
        if prompt is None:
            continue
        prompts = [prompt] if isinstance(prompt, str) else prompt
        if nos.initial_prompt not in prompts:
            continue

        # Prefer output without curly braces
        if "{" not in output:
            return (cmd_name, output)
        if fallback is None:
            fallback = (cmd_name, output)

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
    """Classify callable commands into the (initial, enable) sweep phases.

    Returns two lists of (cmd, expected): commands runnable at the
    initial prompt and commands requiring enable mode. Eligible =
    callable output that returns a str — dict-returning mode/exit
    callables are unit-test scope at ANY prompt (config included) —
    and is not in TIME_DEPENDENT_COMMANDS.

    A *str-returning* callable matching neither the initial nor the
    enable prompt (e.g. config-mode-only) raises AssertionError instead
    of being silently dropped: extend the sweep (config phase) or add a
    dedicated exclusion set — do not reuse TIME_DEPENDENT_COMMANDS for
    non-time reasons.

    The expected value is computed by invoking the callable with the
    same 4-arg contract as `cmd_shell.default` (device, base_prompt=,
    current_prompt=, command=) and taken **verbatim** — the shell does
    not apply `.format(base_prompt=...)` to callable output (#241 /
    D-b: handlers receive base_prompt and format themselves), so the
    oracle must not either. Alias entries have no `output` key of their
    own, so they are skipped here; the alias target entry is swept
    independently.

    Note: classification itself invokes the callables (probe + expected),
    so a state-mutating callable would advance device state here before
    the e2e session runs — fine today (all make_* are read-only), but a
    sweep-eligibility redesign is needed if that ever changes.
    """
    initial_prompt = nos.initial_prompt.format(base_prompt=base_prompt)
    enable_prompt = (nos.enable_prompt or "").format(base_prompt=base_prompt)

    initial_cmds: list[tuple[str, str]] = []
    enable_cmds: list[tuple[str, str]] = []
    unclassified: list[str] = []
    for cmd_name, cmd_data in nos.commands.items():
        output = cmd_data.get("output")
        if not callable(output) or (device_type, cmd_name) in TIME_DEPENDENT_COMMANDS:
            continue
        prompts = cmd_data.get("prompt")
        prompts = [prompts] if isinstance(prompts, str) else (prompts or [])
        formatted = [p.format(base_prompt=base_prompt) for p in prompts]
        if initial_prompt in formatted:
            current_prompt, bucket = initial_prompt, initial_cmds
        elif enable_prompt and enable_prompt in formatted:
            current_prompt, bucket = enable_prompt, enable_cmds
        else:
            # Outside the sweep phases. Probe with the command's own
            # declared prompt to apply the eligibility contract: a dict
            # return means mode/exit logic (unit-test scope at any
            # prompt); only a str return here is real e2e coverage loss.
            probe_prompt = formatted[0] if formatted else initial_prompt
            probe = output(nos.device, base_prompt=base_prompt, current_prompt=probe_prompt, command=cmd_name)
            if isinstance(probe, str):
                unclassified.append(cmd_name)
            continue
        expected = output(nos.device, base_prompt=base_prompt, current_prompt=current_prompt, command=cmd_name)
        if not isinstance(expected, str):
            continue  # dict-returning mode/exit callables -> unit tests cover these
        bucket.append((cmd_name, expected))

    assert not unclassified, (
        f"{device_type}: str-returning callable commands outside the initial/enable "
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
        port = get_free_port()

        net = _make_simnos(device_type, port)
        try:
            net.start()
            device = _device(device_type, port)
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
        assert initial_cmds or enable_cmds, (
            f"No eligible callable command found for {device_type}. "
            "Every py platform must expose at least one str-returning callable."
        )

        port = get_free_port()
        net = _make_simnos(device_type, port)
        try:
            net.start()
            device = _device(device_type, port)
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
    def _synthetic_nos(commands: dict) -> Nos:
        """Build a minimal Nos with the standard 3-mode prompt set."""
        return Nos(
            dict_args={
                "name": "synth",
                "initial_prompt": "{base_prompt}>",
                "enable_prompt": "{base_prompt}#",
                "config_prompt": "{base_prompt}(config)#",
                "commands": commands,
            }
        )

    def test_config_only_str_callable_fails_loudly(self):
        """A str-returning callable outside the sweep phases is coverage loss."""
        nos = self._synthetic_nos(
            {
                "weird": {
                    "output": lambda device, **kwargs: "static",
                    "help": "config-only str callable",
                    "prompt": "{base_prompt}(config)#",
                }
            }
        )
        with pytest.raises(AssertionError, match=r"outside the initial/enable\s+sweep phases: \['weird'\]"):
            _classify_callable_commands(nos, "synth", HOSTNAME)

    def test_config_only_dict_callable_is_unit_scope(self):
        """Dict-returning mode callables are excluded at ANY prompt, no fail."""
        nos = self._synthetic_nos(
            {
                "modey": {
                    "output": lambda device, **kwargs: {"exit": True},
                    "help": "config-only dict callable",
                    "prompt": "{base_prompt}(config)#",
                }
            }
        )
        initial_cmds, enable_cmds = _classify_callable_commands(nos, "synth", HOSTNAME)
        assert initial_cmds == []
        assert enable_cmds == []

    def test_denylist_is_platform_qualified(self):
        """Another platform's deterministic 'show clock' stays in the sweep."""
        nos = self._synthetic_nos(
            {
                "show clock": {
                    "output": lambda device, **kwargs: "deterministic",
                    "help": "deterministic clock on a synthetic platform",
                    "prompt": "{base_prompt}>",
                }
            }
        )
        initial_cmds, enable_cmds = _classify_callable_commands(nos, "synth", HOSTNAME)
        assert initial_cmds == [("show clock", "deterministic")]
        assert enable_cmds == []

    def test_bucketing_and_expected_verbatim(self):
        """initial / enable / dual-prompt (-> initial) bucketing + verbatim oracle.

        The `{base_prompt}` placeholder in 'enable only' stays **unsubstituted**
        in the expected value: the shell does not format callable output
        (#241 / D-b), so the sweep oracle must take the return verbatim —
        this pin replaces the pre-#241 one that expected the `.format` step.
        """
        nos = self._synthetic_nos(
            {
                "init only": {
                    "output": lambda device, **kwargs: "from init",
                    "help": "initial-prompt only",
                    "prompt": "{base_prompt}>",
                },
                "enable only": {
                    "output": lambda device, **kwargs: "hostname {base_prompt}",
                    "help": "enable-prompt only, with literal placeholder",
                    "prompt": "{base_prompt}#",
                },
                "dual prompt": {
                    "output": lambda device, **kwargs: "from dual",
                    "help": "both prompts -> initial bucket wins",
                    "prompt": ["{base_prompt}#", "{base_prompt}>"],
                },
            }
        )
        initial_cmds, enable_cmds = _classify_callable_commands(nos, "synth", HOSTNAME)
        assert initial_cmds == [("init only", "from init"), ("dual prompt", "from dual")]
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
        """Shell should exit via do_EOF when server stops, no thread leaks."""
        port = get_free_port()
        net = _make_simnos("cisco_ios", port)
        try:
            net.start()
            device = _device("cisco_ios", port)
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
        port = get_free_port()
        net = _make_simnos("cisco_ios", port)
        net.start()
        try:
            device = _device("cisco_ios", port)
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
