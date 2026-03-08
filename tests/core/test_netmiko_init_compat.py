"""
Tests for netmiko init compatibility, send_command response, and shutdown/EOF regression.

Verifies that:
- netmiko session_preparation() does not produce "Unknown command" (#69, #71)
- Unknown commands are handled gracefully without crashing
- send_command returns the defined output for each platform (#76)
- Shell exits cleanly on shutdown without thread leaks (#71 regression)
"""

import contextlib
import threading

import detect
from netmiko import ConnectHandler
import pytest

from simnos import SimNOS
from tests.utils import get_free_port, get_platforms_from_md

HOSTNAME = "router"  # Inventory host key; also used as base_prompt in output formatting

# Platforms where "Unknown command" is expected during init due to
# missing command definitions for netmiko's session_preparation().
# These should be fixed individually as separate issues.
INIT_UNKNOWN_CMD_ALLOWED = {
    "aruba_os",  # no paging
    "brocade_fastiron",  # enable (repeated)
    "cisco_asa",  # show curpriv, terminal pager 0, configure terminal
    "dlink_ds",  # disable clipaging
    "huawei_smartax",  # enable password (#70)
    "ipinfusion_ocnos",  # terminal length 0
    "ruckus_fastiron",  # enable (repeated), skip-page-display
    "vyatta_vyos",  # set terminal width 512
}


def _make_simnos(device_type, port):
    """Create a SimNOS instance for a single device."""
    inventory = {
        "hosts": {
            HOSTNAME: {
                "username": "test",
                "password": "test",
                "port": port,
                "platform": device_type,
            }
        }
    }
    return SimNOS(inventory=inventory)


class TestNetmikoInitCompat:
    """Test netmiko session_preparation() compatibility."""

    @pytest.mark.timeout(30)
    @pytest.mark.parametrize("device_type", get_platforms_from_md())
    def test_no_unknown_command_on_init(self, device_type, tmp_path):
        """ConnectHandler init should not produce 'Unknown command'."""
        if device_type in INIT_UNKNOWN_CMD_ALLOWED:
            pytest.skip(f"{device_type} is in the init exclusion list (#70)")

        port = get_free_port()
        log_file = tmp_path / f"session_{device_type}.log"
        net = _make_simnos(device_type, port)
        try:
            net.start()
            device = {
                "host": "localhost",
                "username": "test",
                "password": "test",
                "port": port,
                "device_type": device_type,
                "session_log": str(log_file),
            }
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
            device = {
                "host": "localhost",
                "username": "test",
                "password": "test",
                "port": port,
                "device_type": device_type,
            }
            with ConnectHandler(**device) as conn:
                output = conn.send_command(
                    "this_command_does_not_exist_12345",
                    read_timeout=10,
                )
                assert output is not None
                # Verify session is still alive after unknown command
                follow_up = conn.send_command_timing("?")
                assert follow_up is not None
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
    from simnos.core.nos import Nos
    from simnos.plugins.nos import nos_plugins

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


# Platforms where send_command is flaky:
# - aruba_os, hp_comware: intermittently return empty output (race condition
#   beyond the ChannelFile fix in #85; possibly TapIO timing)
# - mikrotik_routeros: trailing prompt included in output (netmiko prompt
#   detection issue, unrelated to SSH I/O)
SEND_CMD_XFAIL = {"aruba_os", "hp_comware", "mikrotik_routeros"}


class TestSendCommandResponse:
    """Test that send_command returns the defined output for each platform (#76)."""

    @pytest.mark.timeout(30)
    @pytest.mark.parametrize("device_type", get_platforms_from_md())
    def test_send_command_returns_defined_output(self, device_type: str):
        """Defined command should return matching output via send_command."""
        if device_type in SEND_CMD_XFAIL:
            pytest.xfail(f"{device_type}: flaky or prompt detection issue")

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
            device = {
                "host": "localhost",
                "username": "test",
                "password": "test",
                "port": port,
                "device_type": device_type,
            }
            with ConnectHandler(**device) as conn:
                output = conn.send_command(cmd, read_timeout=15)
                assert output.strip() == expected.strip(), (
                    f"{device_type}: '{cmd}' returned unexpected output.\n"
                    f"  expected: {expected.strip()!r}\n"
                    f"  actual:   {output.strip()!r}"
                )
        finally:
            net.stop()


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
            device = {
                "host": "localhost",
                "username": "test",
                "password": "test",
                "port": port,
                "device_type": "cisco_ios",
            }
            with ConnectHandler(**device):
                pass
        finally:
            net.stop()
            self._join_all_threads()

        n_threads = 2 if detect.windows else 1
        assert threading.active_count() == n_threads

    @pytest.mark.timeout(30)
    def test_server_stop_while_connected(self):
        """Server stop during active connection should not hang."""
        port = get_free_port()
        net = _make_simnos("cisco_ios", port)
        net.start()
        try:
            device = {
                "host": "localhost",
                "username": "test",
                "password": "test",
                "port": port,
                "device_type": "cisco_ios",
            }
            conn = ConnectHandler(**device)
            # Stop server while connection is still open
            net.stop()
            # Connection should be closed by server shutdown
            with contextlib.suppress(Exception):
                conn.disconnect()
        finally:
            self._join_all_threads()

        n_threads = 2 if detect.windows else 1
        assert threading.active_count() == n_threads
