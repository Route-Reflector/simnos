"""
Tests for netmiko init compatibility and shutdown/EOF regression.

Verifies that:
- netmiko session_preparation() does not produce "Unknown command" (#69, #71)
- Defined show commands return correct responses
- Unknown commands are handled gracefully without crashing
- Shell exits cleanly on shutdown without thread leaks (#71 regression)
"""

import contextlib
import threading

import detect
from netmiko import ConnectHandler
import pytest

from simnos import SimNOS
from tests.utils import get_free_port, get_platforms_from_md

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


def _platforms():
    """Return test platforms excluding known-incompatible ones."""
    return get_platforms_from_md()


def _make_simnos(device_type, port):
    """Create a SimNOS instance for a single device."""
    inventory = {
        "hosts": {
            "router": {
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
    @pytest.mark.parametrize("device_type", _platforms())
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
    @pytest.mark.parametrize("device_type", _platforms())
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
