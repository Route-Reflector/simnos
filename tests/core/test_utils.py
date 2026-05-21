"""Tests for simnos.core.utils."""

from unittest.mock import MagicMock, patch

from simnos.core.utils import _is_in_docker


class TestIsInDocker:
    """Pin the two heuristics used by ``_is_in_docker``.

    The function exists because the previously-used ``detect`` package was
    unmaintained (last release 2020-12-03). These tests pin the contract so
    that future refactors keep both detection paths intact.
    """

    def test_returns_true_when_dockerenv_file_exists(self):
        """``/.dockerenv`` existence is the primary positive signal."""
        with patch("simnos.core.utils.Path") as mock_path:
            mock_path.return_value.exists.return_value = True
            assert _is_in_docker() is True

    def test_returns_true_when_cgroup_mentions_docker(self):
        """If ``/.dockerenv`` is missing, ``/proc/1/cgroup`` containing
        ``docker`` is the fallback positive signal."""
        mock_dockerenv = MagicMock()
        mock_dockerenv.exists.return_value = False
        mock_cgroup = MagicMock()
        mock_cgroup.read_text.return_value = "12:cpuset:/docker/abc123\n"
        with patch("simnos.core.utils.Path") as mock_path:
            mock_path.side_effect = [mock_dockerenv, mock_cgroup]
            assert _is_in_docker() is True

    def test_returns_true_when_cgroup_mentions_containerd(self):
        """``containerd`` in cgroup also counts as a container runtime."""
        mock_dockerenv = MagicMock()
        mock_dockerenv.exists.return_value = False
        mock_cgroup = MagicMock()
        mock_cgroup.read_text.return_value = "0::/system.slice/containerd.service\n"
        with patch("simnos.core.utils.Path") as mock_path:
            mock_path.side_effect = [mock_dockerenv, mock_cgroup]
            assert _is_in_docker() is True

    def test_returns_false_when_neither_signal_present(self):
        """Plain host (``/.dockerenv`` absent, cgroup mentions neither
        ``docker`` nor ``containerd``) returns ``False``."""
        mock_dockerenv = MagicMock()
        mock_dockerenv.exists.return_value = False
        mock_cgroup = MagicMock()
        mock_cgroup.read_text.return_value = "0::/user.slice/user-1000.slice\n"
        with patch("simnos.core.utils.Path") as mock_path:
            mock_path.side_effect = [mock_dockerenv, mock_cgroup]
            assert _is_in_docker() is False

    def test_returns_false_when_cgroup_read_fails(self):
        """On platforms without ``/proc/1/cgroup`` (Windows, macOS), the
        ``OSError`` from ``read_text`` is swallowed and ``False`` returned."""
        mock_dockerenv = MagicMock()
        mock_dockerenv.exists.return_value = False
        mock_cgroup = MagicMock()
        mock_cgroup.read_text.side_effect = OSError("no such file")
        with patch("simnos.core.utils.Path") as mock_path:
            mock_path.side_effect = [mock_dockerenv, mock_cgroup]
            assert _is_in_docker() is False
