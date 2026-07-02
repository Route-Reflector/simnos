"""
Test module for the module simnos.core.host
under simnos/core/host.py
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from simnos import SimNOS
from simnos.core.host import Host
from simnos.core.nos import available_platforms


class TestHost:
    """
    Test module for the Host class
    """

    @pytest.fixture
    def host(self):
        """Initial fixture for the setup"""
        server = {"plugin": "server_plugin", "configuration": {}}
        shell = {"plugin": "shell_plugin", "configuration": {}}
        nos = {"plugin": "nos_plugin", "configuration": {}}
        net = Mock()
        server_plugin = Mock()
        # Host.start reads back the server's real bound port into host.port (#271 / D4).
        # Give the mock server a real int so host.port stays a plain int after start
        # instead of a MagicMock.
        server_plugin.return_value.port = 22
        net.servers_plugins = {"server_plugin": server_plugin}
        net.shell_plugins = {"shell_plugin": Mock()}
        net.nos_plugins = {"nos_plugin": Mock()}
        with patch.object(Host, "_check_if_platform_is_supported") as mock_check_platform:
            mock_check_platform.return_value = None
            host = Host("name", "username", "password", 22, server, shell, nos, net)
        return host

    def test_init(self, host):
        """
        The test passes if the host is correctly initialized.
        """
        assert host.name == "name"
        assert host.username == "username"
        assert host.password == "password"
        assert host.port == 22
        assert host.server_inventory == {"plugin": "server_plugin", "configuration": {}}
        assert host.shell_inventory == {
            "plugin": "shell_plugin",
            "configuration": {"base_prompt": "name"},
        }
        assert host.nos_inventory == {"plugin": "nos_plugin", "configuration": {}}
        assert not host.running

    def test_start(self, host):
        """
        The test passes if the start method is called and the server is started.
        """
        host.start()
        assert host.running
        host.server.start.assert_called_once()

    def test_start_twice_is_noop(self, host):
        """A second start() while running does not spawn a new server.

        Pins the double-start guard (#237, #199 C-23 follow-up): without
        it, a direct start() call built and started a second server
        instance, orphaning the first. Symmetric with the double-stop
        guard in stop().
        """
        host.start()
        first_server = host.server
        host.start()
        assert host.server is first_server
        first_server.start.assert_called_once()
        assert host.running

    def test_restart_after_stop_creates_new_server(self, host):
        """start() after stop() builds and starts a fresh server.

        Separates the restartable semantics from the idempotent no-op
        (#237 cross-review 🦊#5): the guard gates on `self.running`, so
        a regression in stop()'s state update would silently turn
        restarts into no-ops — this pin catches that.
        """
        host.start()
        host.stop()
        host.start()
        assert host.running
        assert host.server is not None
        # The plugin factory ran twice = a fresh server was built for the
        # restart (the mock factory returns the same object both times,
        # so instance identity cannot be asserted here).
        assert host.server_plugin.call_count == 2
        assert host.server.start.call_count == 2

    def test_start_failure_stops_server_and_resets(self, host):
        """A mid-start server.start() failure cleans up and does not dangle.

        Pins the partial-start defense-in-depth (#291): SimNOS.stop() filters
        on running=True, so a host whose server.start() raised (running stays
        False) is excluded from cluster shutdown. Host.start() therefore stops
        the just-built server and drops the reference before re-raising, so no
        server is left started-but-unreachable on the failed host.
        """
        server_factory = host.simnos.servers_plugins["server_plugin"]
        failed_server = server_factory.return_value
        failed_server.start.side_effect = RuntimeError("bind failed")
        with pytest.raises(RuntimeError, match="bind failed"):
            host.start()
        failed_server.stop.assert_called_once()
        assert host.server is None
        assert not host.running

    def test_start_failure_cleanup_error_does_not_mask_original(self, host):
        """A cleanup stop() failure does not hide the original start() error.

        The re-raised exception must be the *same* object as the real start()
        failure (the cause a caller needs), not a secondary error from the
        best-effort cleanup stop() (#291). Pinning that cleanup stop() was
        actually called proves the suppression path ran (without it, dropping
        the cleanup line would leave this test green). State is reset regardless.
        """
        server_factory = host.simnos.servers_plugins["server_plugin"]
        failed_server = server_factory.return_value
        start_error = RuntimeError("bind failed")
        failed_server.start.side_effect = start_error
        failed_server.stop.side_effect = OSError("stop boom")
        with pytest.raises(RuntimeError, match="bind failed") as exc_info:
            host.start()
        assert exc_info.value is start_error
        failed_server.stop.assert_called_once()
        assert host.server is None
        assert not host.running

    def test_start_baseexception_still_cleans_up(self, host):
        """A BaseException (e.g. Ctrl+C) mid-start still triggers cleanup (#291).

        KeyboardInterrupt is the most likely partial-start trigger (the operator
        aborts startup). `except Exception` would miss it, leaving the server
        set and running=False — which SimNOS.stop() skips but
        _collect_server_threads() still picks up, hanging the shutdown join. The
        catch is `except BaseException`, so the server is stopped and dropped
        before the interrupt re-raises.
        """
        server_factory = host.simnos.servers_plugins["server_plugin"]
        failed_server = server_factory.return_value
        failed_server.start.side_effect = KeyboardInterrupt
        with pytest.raises(KeyboardInterrupt):
            host.start()
        failed_server.stop.assert_called_once()
        assert host.server is None
        assert not host.running

    def test_restart_after_failed_start_builds_fresh_server(self, host):
        """A retry after a failed start() builds a new server (#291).

        Dropping `self.server` on the failure path keeps the double-start guard
        (gates on `running`, still False) open, so a retry is a real restart
        that constructs a fresh server rather than re-using the failed one.
        """
        server_factory = host.simnos.servers_plugins["server_plugin"]
        failed_server = Mock()
        failed_server.start.side_effect = RuntimeError("bind failed")
        good_server = Mock()
        server_factory.side_effect = [failed_server, good_server]
        with pytest.raises(RuntimeError, match="bind failed"):
            host.start()
        assert host.server is None
        host.start()
        assert host.server is good_server
        assert host.running
        good_server.start.assert_called_once()

    def test_stop(self, host):
        """
        It test that when the host is called the stop,
        the server is correctly stoped and called
        its stop function.
        """
        host.start()
        mock_server = MagicMock()
        host.server = mock_server
        host.stop()
        assert not host.running
        mock_server.stop.assert_called_once()
        assert host.server is None

    def test_stop_resets_state_even_if_server_stop_raises(self, host):
        """Host.stop() resets state even if server.stop() is interrupted (#291).

        The server self-cleans in its own finally, so the host must drop the
        reference + clear running regardless, keeping the host out of
        SimNOS._collect_server_threads(). Symmetric with start()'s rollback.
        """
        host.start()
        host.server.stop.side_effect = KeyboardInterrupt
        with pytest.raises(KeyboardInterrupt):
            host.stop()
        assert host.server is None
        assert not host.running

    def test_platform_is_wrong(self, host):
        """
        The test passes if the ValueError is raised when the platform is not supported.
        """
        platform = "wrong_platform"
        host.simnos = SimNOS()
        with pytest.raises(ValueError, match=r"Platform wrong_platform is not supported by SIMNOS"):
            # pylint: disable=protected-access
            host._check_if_platform_is_supported(platform)

    def test_platform_is_supported(self, host):
        """
        The test passes if the platform is supported.
        """
        host.simnos = SimNOS()
        platform = available_platforms[0]
        # pylint: disable=protected-access
        host._check_if_platform_is_supported(platform)


class TestResolveOverlayRoot:
    """`Host._resolve_overlay_root` (#286): opt-in detection + loud-fail boundary.

    The opt-in is `overlay.override_commands`; when set, sys_config.data_dir must
    be configured and `<data_dir>/<plugin_key>/` must exist — an explicit opt-in
    that cannot be satisfied is a loud error, never a silent fall-back (Decision 10a).
    """

    def _host(self, *, overlay, data_dir):
        server = {"plugin": "server_plugin", "configuration": {}}
        shell = {"plugin": "shell_plugin", "configuration": {}}
        nos = {"plugin": "nos_plugin", "configuration": {}}
        net = Mock()
        net.sys_config = {"data_dir": data_dir}
        with patch.object(Host, "_check_if_platform_is_supported"):
            return Host("R1", "u", "p", 22, server, shell, nos, net, overlay=overlay)

    def test_not_opted_in_returns_none(self):
        host = self._host(overlay=None, data_dir="/srv")
        assert host._resolve_overlay_root("cisco_ios") is None

    def test_empty_override_commands_returns_none(self):
        host = self._host(overlay={"override_commands": []}, data_dir="/srv")
        assert host._resolve_overlay_root("cisco_ios") is None

    def test_opted_in_without_data_dir_is_loud(self):
        host = self._host(overlay={"override_commands": "all"}, data_dir=None)
        with pytest.raises(ValueError, match=r"sys_config.data_dir is not configured"):
            host._resolve_overlay_root("cisco_ios")

    def test_opted_in_with_missing_dir_is_loud(self, tmp_path):
        host = self._host(overlay={"override_commands": "all"}, data_dir=str(tmp_path))
        with pytest.raises(ValueError, match=r"overlay directory .* does not exist"):
            host._resolve_overlay_root("cisco_ios")

    def test_opted_in_with_existing_dir_returns_path(self, tmp_path):
        (tmp_path / "cisco_ios").mkdir()
        host = self._host(overlay={"override_commands": "all"}, data_dir=str(tmp_path))
        assert host._resolve_overlay_root("cisco_ios") == str(tmp_path / "cisco_ios")

    def test_opted_in_on_py_only_platform_is_loud(self, tmp_path):
        # Overlay is A3-only: opting in on a py-only platform (no
        # resolved_platform — a runtime-registered custom) must fail here with
        # the overlay-focused message, before the merge's own A3-required error
        # (Decision 12 / #317 P-4).
        (tmp_path / "py_plat").mkdir()
        host = self._host(overlay={"override_commands": "all"}, data_dir=str(tmp_path))
        host.nos = Mock(resolved_platform=None)  # py-only: no A3 platform data
        with pytest.raises(ValueError, match=r"no A3 command data.*A3 platforms only"):
            host._resolve_overlay_root("py_plat")
