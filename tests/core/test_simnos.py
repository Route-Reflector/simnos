"""
Test module for simnos.core.simnos.
The file can be found in simnos/core/simnos.py
"""

# pylint: disable=protected-access
import logging
import platform
import threading
from unittest.mock import MagicMock, Mock, patch

import detect
import pytest
import yaml

from simnos.core.host import Host
from simnos.core.nos import available_platforms
from simnos.core.simnos import SimNOS, simnos
from tests.utils import get_platforms_from_md, get_running_hosts


# pylint: disable=too-many-public-methods
class TestSimNOS:
    """
    Test class for the SimNOS class.
    """

    def test_create_simnos_without_arguments(self):
        """
        Test that SimNOS creates two hosts when no
        arguments are passed.
        Those routers should have the following:
        - names are router0 and router1
        - port are 6000 and 6001
        - address is localhost
        - timeout is 1
        - username is user
        - password is user
        - server plugin is ParamikoSshServer
        - shell plugin is CMDShell
        """
        net = SimNOS()
        assert len(net.hosts) == 3
        for router_name, host in net.hosts.items():
            assert router_name in [
                "router_cisco_ios",
                "router_huawei_smartax",
                "router_arista_eos",
            ]
            assert host.username in ["user"]
            assert host.password in ["user"]
            assert host.port in {6000, 6001, 6002}
            assert host.server_inventory["plugin"] == "ParamikoSshServer"
            if detect.docker and "WSL2" in platform.release():
                assert host.server_inventory["configuration"]["address"] == "0.0.0.0"
            else:
                assert host.server_inventory["configuration"]["address"] == "127.0.0.1"
            assert host.server_inventory["configuration"]["timeout"] == 1
            assert host.shell_inventory["plugin"] == "CMDShell"
            assert host.shell_inventory["configuration"] == {"base_prompt": router_name}

    def test_create_simnos_with_inventory_as_dict(self):
        """
        Test that SimNOS creates two hosts when an inventory is passed.
        Those routers should have the following:
        - names are R1 and R2
        - port are 5001 and 6000
        - username is simnos
        - password is simnos
        """
        inventory = {
            "hosts": {
                "R1": {
                    "port": 5001,
                    "username": "simnos_R1",
                    "password": "simnos_R1",
                    "platform": available_platforms[0],
                },
                "R2": {
                    "port": 6000,
                    "username": "simnos_R2",
                    "password": "simnos_R2",
                    "platform": available_platforms[0],
                },
            }
        }
        net = SimNOS(inventory=inventory)
        assert len(net.hosts) == 2
        for router_name, host in net.hosts.items():
            assert router_name in ["R1", "R2"]
            assert host.username in ["simnos_R1", "simnos_R2"]
            assert host.password in ["simnos_R1", "simnos_R2"]
            assert host.port in [5001, 6000]

    def test_create_simnos_with_inventory_as_file(self):
        """
        Test that SimNOS creates two hosts when an inventory is passed as a file.
        Those routers should have the following:
        - names are R1 and R2
        - port are 5001 and 6000
        - username is simnos
        - password is simnos
        """
        net = SimNOS(inventory="tests/assets/inventory.yaml")
        assert len(net.hosts) == 2
        for router_name, host in net.hosts.items():
            assert router_name in ["R1", "R2"]
            assert host.username == "simnos"
            assert host.password == "simnos"
            assert host.port in [5001, 6000]

    def test_is_inventory_in_yaml(self):
        """
        Test that the inventory is in yaml format.
        """
        net = SimNOS(inventory="tests/assets/inventory.yaml")
        assert isinstance(net.inventory, dict)

    def test_is_inventory_in_yaml_false(self):
        """
        Test that the inventory is in yaml format.
        """
        with pytest.raises(ValueError, match=r"Inventory file must end with \.yaml or \.yml"):
            SimNOS(inventory="tests/assets/inventory.txt")

    def test_is_inventory_in_yaml_unit(self):
        """
        Test that the function _is_inventory_in_yaml returns True
        when the inventory is in yaml format.
        """
        net = SimNOS()
        net.inventory = "tests/assets/inventory.yaml"
        assert net._is_inventory_in_yaml() is True

    def test_is_inventory_in_yaml_unit_false(self):
        """
        Test that the function _is_inventory_in_yaml returns False
        when the inventory is not in yaml format.
        """
        net = SimNOS()
        net.inventory = "tests/assets/inventory.txt"
        assert net._is_inventory_in_yaml() is False

    def test_load_inventory_yaml_unit_true(self):
        """
        Test that the function _load_inventory_yaml returns a dictionary
        when the inventory is in yaml format.
        """
        net = SimNOS()
        net.inventory = "tests/assets/inventory.yaml"
        net._load_inventory_yaml()
        assert isinstance(net.inventory, dict)

    def test_load_inventory_yaml_unit_false(self):
        """
        Test that the function _load_inventory_yaml returns None
        when the inventory is not in yaml format.
        """
        net = SimNOS()
        net.inventory = "tests/assets/inventory.txt"
        assert net._load_inventory_yaml() is None

    def test_load_inventory_unit_yaml(self):
        """
        Test that the function _load_inventory loads the inventory
        when the inventory is in yaml format.
        """
        net = SimNOS()
        net.inventory = "tests/assets/inventory.yaml"
        net._load_inventory()
        assert isinstance(net.inventory, dict)

    def test_load_inventory_unit_dict(self):
        """
        Test that the function _load_inventory loads the inventory
        when the inventory is a dictionary.
        """
        net = SimNOS()
        net.inventory = {"hosts": {"R1": {"port": 5001}}}
        net._load_inventory()
        assert isinstance(net.inventory, dict)

    def test_load_inventory_unit_default(self):
        """
        Test that the function _load_inventory loads the inventory
        when the inventory is a dictionary with a default key.
        """
        net = SimNOS()
        net.inventory = {"default": {"port": 5001}, "hosts": {"R1": {}}}
        net._load_inventory()
        assert isinstance(net.inventory, dict)

    def test_load_inventory_unit_wrong_dict(self):
        """
        Test that the function _load_inventory raises an exception
        when the inventory is not a dictionary.
        """
        net = SimNOS()
        net.inventory = "tests/assets/inventory.txt"
        with pytest.raises(ValueError, match=r"Inventory file must end with \.yaml or \.yml"):
            net._load_inventory()

    @patch("simnos.core.simnos.SimNOS._allocate_port")
    def test_init_unit(self, mock_allocate_port):
        """
        Test that the function _init creates the hosts.
        """
        inventory = {"hosts": {"R1": {"port": 5001, "platform": "cisco_ios"}}}
        net = SimNOS(inventory)
        assert len(net.hosts) == 1
        assert "R1" in net.hosts
        assert mock_allocate_port.call_count == 1

    def test_port_already_allocated(self):
        """
        Test that the function _allocate_port raises an exception
        when the port is already allocated.
        """
        net = SimNOS()
        net.allocated_ports = [5000]
        with pytest.raises(ValueError):
            net._allocate_port(5000)

    def test_allocate_port(self):
        """
        Test that the function _allocate_port allocates the port.
        """
        inventory = {"hosts": {"R1": {"port": 5000, "platform": "cisco_ios"}}}
        net = SimNOS(inventory=inventory)
        assert 5000 in net.allocated_ports
        assert len(net.allocated_ports) == 1

    def test_allocate_port_range(self):
        """
        Test that the function _allocate_port allocates the port.
        """
        inventory = {"hosts": {"R1": {"port": [5000, 5001], "replicas": 2, "platform": "cisco_ios"}}}
        net = SimNOS(inventory=inventory)
        assert net.allocated_ports == {5000, 5001}

    @pytest.mark.parametrize(
        "port",
        [0, -1, 65536, 100000],
        ids=["zero", "negative", "above_max", "far_above_max"],
    )
    def test_allocate_port_out_of_range(self, port):
        """Test that _allocate_port_single rejects ports outside 1-65535."""
        net = SimNOS()
        with pytest.raises(ValueError, match="out of valid range"):
            net._allocate_port_single(port)

    def test_allocate_port_boundary_valid(self):
        """Test that port 1 and 65535 are accepted as valid boundary values."""
        net = SimNOS()
        net._allocate_port_single(1)
        net._allocate_port_single(65535)
        assert {1, 65535}.issubset(net.allocated_ports)

    def test_replicas_not_set_and_port_list(self):
        """
        Test that the function _check_ports_and_replicas raises an exception
        when replicas is not set.
        """
        inventory = {"default": {"port": [5000, 5001]}, "hosts": {"R1": {}}}
        with pytest.raises(ValueError):
            SimNOS(inventory=inventory)

    def test_replicas_set_and_port_int(self):
        """
        Test that the function _check_ports_and_replicas raises an exception
        when replicas is set and port is an int.
        """
        inventory = {"default": {"port": 5000, "replicas": 2}, "hosts": {"R1": {}}}
        with pytest.raises(ValueError):
            SimNOS(inventory=inventory)

    def test_replicas_set_and_port_list_not_enough_ports(self):
        """
        Test that the function _check_ports_and_replicas raises an exception
        when replicas is set and there are not enough ports.
        """
        inventory = {"default": {"port": [5000], "replicas": 2}, "hosts": {"R1": {}}}
        with pytest.raises(ValueError):
            SimNOS(inventory=inventory)

    def test_replicas_set_and_port_list_too_many_ports(self):
        """
        Test that the function _check_ports_and_replicas raises an exception
        when replicas is set and there are too many ports.
        """
        inventory = {
            "default": {"port": [5000, 5001, 5002], "replicas": 2},
            "hosts": {"R1": {}},
        }
        with pytest.raises(ValueError):
            SimNOS(inventory=inventory)

    def test_replicas_set_and_port_1_larger_than_port_2(self):
        """
        Test that the function _check_ports_and_replicas raises an exception
        when replicas is set and the first port is larger than the second port.
        """
        inventory = {
            "default": {"port": [5001, 5000], "replicas": 2},
            "hosts": {"R1": {}},
        }
        with pytest.raises(ValueError):
            SimNOS(inventory=inventory)

    def test_replicas_set_and_replicas_less_than_1(self):
        """
        Test that the function _check_ports_and_replicas raises an exception
        when replicas is set and the replicas are less than 1.
        """
        inventory = {
            "default": {"port": [5000, 5001], "replicas": 0},
            "hosts": {"R1": {}},
        }
        with pytest.raises(ValueError):
            SimNOS(inventory=inventory)

    def test_replicas_set_and_ports_set_not_same_length(self):
        """
        Test that the function _check_ports_and_replicas raises an exception
        when replicas is set and the ports are not the same length.
        """
        inventory = {
            "default": {"port": [5000, 5001], "replicas": 3},
            "hosts": {"R1": {}},
        }
        with pytest.raises(ValueError):
            SimNOS(inventory=inventory)

    def test_wrong_plugin_name(self):
        """
        Test that the function _check_plugin_name raises an exception
        when the plugin name is wrong.
        """
        inventory = {"hosts": {"R1": {"server": {"plugin": "wrong_plugin"}}}}
        with pytest.raises(ValueError):
            SimNOS(inventory=inventory)

    def test_wrong_platform(self):
        """
        Test that the function _check_platform raises an exception
        when the platform is wrong.
        """
        inventory = {"hosts": {"R1": {"platform": "wrong_platform"}}}
        with pytest.raises(ValueError):
            SimNOS(inventory=inventory)

    def test_inventory_validation_cmdshell_plugin(self):
        """
        Test that the inventory is validated when
        it contains a shell plugin.
        """
        inventory = {
            "hosts": {
                "R1": {
                    "port": 6000,
                    "platform": available_platforms[0],
                    "shell": {
                        "plugin": "CMDShell",
                        "configuration": {},
                    },
                }
            }
        }
        net = SimNOS(inventory=inventory)
        assert net.inventory["hosts"]["R1"]["shell"]["plugin"] == "CMDShell"

    def test_inventory_configuration_dict(self):
        """
        Test that the inventory is validated when
        it contains a configuration.
        """
        configurations: dict = {}
        with open("tests/assets/test_module.yaml.j2", encoding="utf-8") as file:
            data = file.read()
            configurations = yaml.safe_load(data)
        inventory = {
            "hosts": {
                "R1": {
                    "port": 6000,
                    "platform": "huawei_smartax",
                    "configuration_file": "tests/assets/test_module.yaml.j2",
                }
            }
        }
        with SimNOS(inventory=inventory) as net:
            host: Host = next(iter(net.hosts.values()))
            assert host.nos.device.configurations == configurations

    def test_inventory_configuration_yaml(self):
        """
        Test that the inventory is validated when
        it contains a configuration_file.
        """
        configurations: dict = {}
        with open("tests/assets/test_module.yaml.j2", encoding="utf-8") as file:
            data = file.read()
            configurations = yaml.safe_load(data)
        with SimNOS(inventory="tests/assets/inventory_configuration.yaml") as net:
            host: Host = next(iter(net.hosts.values()))
            assert host.nos.device.configurations == configurations

    def test_simnos_start_stop_hosts(self):
        """
        Test that the function start and stop hosts by the name.
        """
        net = SimNOS()

        net.start(hosts="router_cisco_ios")
        assert net.hosts["router_cisco_ios"].running is True
        assert net.hosts["router_huawei_smartax"].running is False
        assert net.hosts["router_arista_eos"].running is False

        net.start(hosts="router_huawei_smartax")
        assert net.hosts["router_cisco_ios"].running is True
        assert net.hosts["router_huawei_smartax"].running is True
        assert net.hosts["router_arista_eos"].running is False

        net.start(hosts="router_arista_eos")
        assert net.hosts["router_cisco_ios"].running is True
        assert net.hosts["router_huawei_smartax"].running is True
        assert net.hosts["router_arista_eos"].running is True

        net.stop(hosts="router_cisco_ios")
        assert net.hosts["router_cisco_ios"].running is False
        assert net.hosts["router_huawei_smartax"].running is True
        assert net.hosts["router_arista_eos"].running is True

        net.stop(hosts="router_huawei_smartax")
        assert net.hosts["router_cisco_ios"].running is False
        assert net.hosts["router_huawei_smartax"].running is False
        assert net.hosts["router_arista_eos"].running is True

        net.stop(hosts="router_arista_eos")
        assert net.hosts["router_cisco_ios"].running is False
        assert net.hosts["router_huawei_smartax"].running is False
        assert net.hosts["router_arista_eos"].running is False

        net.stop()

    def test_simnos_base_inventory(self):
        """
        Base test for checking the start and stop operations
        using default inventory.
        """
        net = SimNOS()
        before_start = get_running_hosts(net.hosts)
        for running_state in before_start.values():
            assert running_state is False

        net.start()
        after_start = get_running_hosts(net.hosts)
        for running_state in after_start.values():
            assert running_state is True

        net.stop()
        after_stop = get_running_hosts(net.hosts)
        for running_state in after_stop.values():
            assert running_state is False

        assert len(before_start) == len(after_start) == len(after_stop) == 3

    def test_number_of_threads_after_stop_is_only_main(self):
        """
        Test that the number of threads after stopping the network
        returns to the baseline (before start).
        """
        baseline = threading.active_count()
        net = SimNOS()
        net.start()
        net.stop()
        assert threading.active_count() <= baseline

    def test_execute_function_over_hosts_invalid_workers(self):
        """
        Test that _execute_function_over_hosts raises ValueError
        when workers < 1.
        """
        net = SimNOS()
        hosts = list(net.hosts.values())
        with pytest.raises(ValueError, match="workers must be >= 1"):
            net._execute_function_over_hosts(
                hosts,
                "start",
                host_running=False,
                parallel=True,
                workers=0,
            )

    def test_nos_load_inventory_from_py_and_yaml(self):
        """
        Test cisco_ios NOS loaded correctly as it has both
        cisco_ios.py and cisco_ios.yaml definitions
        """
        inventory = {"hosts": {"R1": {"port": 5001, "platform": "cisco_ios"}}}
        net = SimNOS(inventory)
        assert len(net.nos_plugins["cisco_ios"]) == 2, "Not all files detected"


class TestPlatforms:
    """
    Tests directly related to the platforms like the ordering
    or if the platforms match the docs and the real in the code.
    """

    def test_available_platforms_match_docs(self):
        """
        Test if the available platforms are correct set
        in the platforms.md and platforms.py file.
        """
        assert sorted(available_platforms) == sorted(get_platforms_from_md())

    def test_available_platforms_in_py_file_are_ordered(self):
        """
        Test if the available platforms in the platforms.py file
        are ordered alphabetically.
        """
        assert available_platforms == sorted(available_platforms)

    def test_available_platforms_in_docs_are_ordered(self):
        """
        Test if the available platforms in the platforms.md file
        are ordered alphabetically.
        """
        platforms = get_platforms_from_md()
        assert platforms == sorted(platforms)

    def test_with_works(self):
        """
        Test that the with statement works.
        """
        baseline = threading.active_count()
        with SimNOS() as net:
            assert len(net.hosts) == 3
        assert threading.active_count() <= baseline

    @simnos(platform="cisco_ios", return_instance=True)
    def test_decorator_with_platform(self, net: SimNOS):
        """Test that the decorator works with a platform."""
        platforms_used = [host.nos.name for host in net.hosts.values()]
        assert len(net.hosts) == 1
        assert "cisco_ios" in platforms_used
        assert "huawei_smartax" not in platforms_used
        assert "arista_eos" not in platforms_used

    @simnos(inventory="tests/assets/inventory.yaml")
    def test_decorator_with_inventory(self):
        """
        Test that the decorator works with an inventory.
        This test is empty on purpose. If it loads
        correctly the inventory, it will work.
        """

    def test_decorator_raise_error_if_platform_and_inventory_provided(self):
        """Test that the decorator raises an exception if both platform and inventory are set."""
        with pytest.raises(ValueError):

            @simnos(platform="cisco_ios", inventory="tests/assets/inventory.yaml")
            def dummy_function():
                pass

            dummy_function()

    def test_decorator_raise_error_if_not_platform_or_inventory_provided(self):
        """Test that the decorator raises an exception if neither platform nor inventory are set."""
        with pytest.raises(ValueError):

            @simnos()
            def dummy_function():
                pass

            dummy_function()


class TestWarnSecurity:
    """Test cases for SimNOS._warn_security()."""

    def test_default_credentials_warning(self, caplog):
        """Default credentials (user/user) should emit a warning."""
        host = Mock(
            username="user",
            password="user",
            name="R1",
            server_inventory={"configuration": {"address": "127.0.0.1"}},
        )
        with caplog.at_level(logging.WARNING, logger="simnos.core.simnos"):
            SimNOS._warn_security(host)
        assert "default credentials" in caplog.text

    def test_bind_all_interfaces_warning(self, caplog):
        """Binding to 0.0.0.0 should emit a warning."""
        host = Mock(
            username="admin",
            password="secret",
            name="R1",
            server_inventory={"configuration": {"address": "0.0.0.0"}},
        )
        with caplog.at_level(logging.WARNING, logger="simnos.core.simnos"):
            SimNOS._warn_security(host)
        assert "0.0.0.0" in caplog.text

    def test_no_warning_for_safe_config(self, caplog):
        """Safe configuration should not emit any warning."""
        host = Mock(
            username="admin",
            password="secret",
            name="R1",
            server_inventory={"configuration": {"address": "127.0.0.1"}},
        )
        with caplog.at_level(logging.WARNING, logger="simnos.core.simnos"):
            SimNOS._warn_security(host)
        assert caplog.text == ""

    def test_both_warnings(self, caplog):
        """Default credentials + 0.0.0.0 should emit both warnings."""
        host = Mock(
            username="user",
            password="user",
            name="R1",
            server_inventory={"configuration": {"address": "0.0.0.0"}},
        )
        with caplog.at_level(logging.WARNING, logger="simnos.core.simnos"):
            SimNOS._warn_security(host)
        assert "default credentials" in caplog.text
        assert "0.0.0.0" in caplog.text


class TestJoinThreadsDeadline:
    """Tests for deadline-capped _join_threads (Issue #65)."""

    def test_join_threads_deadline_caps_total_time(self):
        """Deadline should cap total join time: threads past deadline are skipped."""
        net = SimNOS()

        mock_threads = [Mock() for _ in range(5)]
        call_count = [0]
        base_time = 1000.0

        def mock_monotonic():
            call_count[0] += 1
            if call_count[0] == 1:
                return base_time  # deadline = base_time + 15
            if call_count[0] <= 3:
                return base_time + 5  # remaining = 10 (within deadline)
            return base_time + 16  # past deadline

        with patch("simnos.core.servers.time.monotonic", side_effect=mock_monotonic):
            net._join_threads(mock_threads)

        # First 2 threads should have been joined, rest skipped
        mock_threads[0].join.assert_called_once()
        mock_threads[1].join.assert_called_once()
        mock_threads[2].join.assert_not_called()
        mock_threads[3].join.assert_not_called()
        mock_threads[4].join.assert_not_called()


class TestGlobalDeadline:
    """Tests for global deadline in _execute_function_over_hosts (Issue #65 R2)."""

    def test_sequential_deadline_skips_remaining_hosts(self):
        """Sequential path: hosts past deadline are skipped with a warning."""
        inventory = {
            "hosts": {
                "R1": {"port": 5001, "platform": "cisco_ios"},
                "R2": {"port": 5002, "platform": "cisco_ios"},
                "R3": {"port": 5003, "platform": "cisco_ios"},
            }
        }
        net = SimNOS(inventory)
        hosts = list(net.hosts.values())
        for h in hosts:
            h.running = True

        call_count = [0]

        def slow_stop():
            call_count[0] += 1

        for h in hosts:
            h.stop = slow_stop

        # Deadline already in the past → all hosts skipped
        with patch("simnos.core.simnos.time.monotonic", return_value=1000.0):
            net._execute_function_over_hosts(
                hosts, "stop", host_running=True, deadline=999.0
            )
        assert call_count[0] == 0, "No hosts should have been stopped past deadline"

    def test_parallel_deadline_uses_shutdown_wait_false(self):
        """Parallel path: executor uses shutdown(wait=False, cancel_futures=True)."""
        inventory = {
            "hosts": {
                "R1": {"port": 5001, "platform": "cisco_ios"},
                "R2": {"port": 5002, "platform": "cisco_ios"},
            }
        }
        net = SimNOS(inventory)
        hosts = list(net.hosts.values())
        for h in hosts:
            h.running = True
            h.stop = Mock()

        mock_ex = MagicMock()
        mock_future = MagicMock()
        mock_ex.submit.return_value = mock_future

        with (
            patch("simnos.core.simnos.concurrent.futures.ThreadPoolExecutor", return_value=mock_ex),
            patch("simnos.core.simnos.concurrent.futures.as_completed", side_effect=TimeoutError),
            patch("simnos.core.simnos.time.monotonic", return_value=1000.0),
        ):
            net._execute_function_over_hosts(
                hosts, "stop", host_running=True,
                parallel=True, deadline=1001.0,
            )

        mock_ex.shutdown.assert_called_once_with(wait=False, cancel_futures=True)
