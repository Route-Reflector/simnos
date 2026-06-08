"""
Test module for simnos.core.simnos.
The file can be found in simnos/core/simnos.py
"""

# pylint: disable=protected-access
import logging
import os
import platform
import re
import threading
from typing import NamedTuple
from unittest.mock import MagicMock, Mock, patch

import pytest
import yaml

from simnos.core.host import Host
from simnos.core.nos import available_platforms
from simnos.core.simnos import SimNOS, default_inventory, simnos
from simnos.core.utils import _is_in_docker
from simnos.plugins.nos import nos_plugins
from tests.utils import get_platforms_from_md, get_running_hosts


class _Step(NamedTuple):
    """One start/stop step + the cumulative running state expected afterwards."""

    action: str  # "start" or "stop"
    target: str  # host name to toggle
    running: dict[str, bool]  # expected running state of every host after the step


# Invalid port/replicas combinations rejected by ``_check_ports_and_replicas``.
# Every case puts ``replicas`` on the host (not ``default``): ``InventoryDefaultSection``
# uses ``extra="forbid"``, so keeping ``port`` in ``default`` while moving ``replicas`` to
# the host lets the merged params reach ``_check_ports_and_replicas`` without pydantic
# rejecting them first. The ``replicas_zero`` case is the #220 regression pin: the old
# ``if not replicas`` falsy guard short-circuited ``replicas=0`` past the intended
# "replicas must be greater than 0" branch; #220 switched to ``if replicas is None`` and
# moved the ``replicas < 1`` check ahead of the port-type checks.
_REPLICAS_REJECT_CASES = [
    pytest.param(
        {"default": {"port": [5000, 5001]}, "hosts": {"R1": {}}},
        r"replicas is not set, port must be an integer",
        id="not_set_port_list",
    ),
    pytest.param(
        {"default": {"port": 5000}, "hosts": {"R1": {"replicas": 2}}},
        r"port must be a list of two integers",
        id="set_port_int",
    ),
    pytest.param(
        {"default": {"port": [5000]}, "hosts": {"R1": {"replicas": 2}}},
        r"port must be a list of two integers",
        id="port_list_too_few",
    ),
    pytest.param(
        {"default": {"port": [5000, 5001, 5002]}, "hosts": {"R1": {"replicas": 2}}},
        r"port must be a list of two integers",
        id="port_list_too_many",
    ),
    pytest.param(
        {"default": {"port": [5001, 5000]}, "hosts": {"R1": {"replicas": 2}}},
        r"port\[0\] must be less than port\[1\]",
        id="port0_ge_port1",
    ),
    pytest.param(
        {"default": {"port": [5000, 5001]}, "hosts": {"R1": {"replicas": 0}}},
        r"replicas must be greater than 0",
        id="replicas_zero",
    ),
    pytest.param(
        {"default": {"port": [5000, 5001]}, "hosts": {"R1": {"replicas": 3}}},
        r"port range must be equal to the number of replicas",
        id="len_mismatch",
    ),
]


# pylint: disable=too-many-public-methods
class TestSimNOS:
    """
    Test class for the SimNOS class.
    """

    def test_create_simnos_without_arguments(self):
        """SimNOS() with no args builds exactly the hosts declared in default_inventory.

        Host names / ports / credentials are derived from default_inventory
        (the SSoT) instead of hardcoded, so this stays correct if the default
        set changes. server/shell plugins, address (WSL/docker aware) and the
        host_key-derived base_prompt are pinned per host.
        """
        expected_hosts = default_inventory["hosts"]
        default_config = default_inventory["default"]

        net = SimNOS()
        assert set(net.hosts) == set(expected_hosts)
        for router_name, host in net.hosts.items():
            # Mirror production's merge: host config overrides the shared default.
            expected = {**default_config, **expected_hosts[router_name]}
            assert host.username == expected["username"]
            assert host.password == expected["password"]
            assert host.port == expected["port"]
            assert host.server_inventory["plugin"] == "ParamikoSshServer"
            if _is_in_docker() and "WSL2" in platform.release():
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
        assert net._is_inventory_in_yaml()

    def test_is_inventory_in_yaml_unit_false(self):
        """
        Test that the function _is_inventory_in_yaml returns False
        when the inventory is not in yaml format.
        """
        net = SimNOS()
        net.inventory = "tests/assets/inventory.txt"
        assert not net._is_inventory_in_yaml()

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
        with pytest.raises(ValueError, match=r"already in use"):
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

    @pytest.mark.parametrize("inventory, match", _REPLICAS_REJECT_CASES)
    def test_check_ports_and_replicas_rejects(self, inventory, match):
        """``_check_ports_and_replicas`` rejects invalid port/replicas combinations.

        See ``_REPLICAS_REJECT_CASES`` for the per-case rationale (including the
        ``extra="forbid"`` placement constraint and the #220 ``replicas_zero``
        regression pin).
        """
        with pytest.raises(ValueError, match=match):
            SimNOS(inventory=inventory)

    def test_wrong_plugin_name(self):
        """
        Test that the function _check_plugin_name raises an exception
        when the plugin name is wrong.
        """
        inventory = {"hosts": {"R1": {"server": {"plugin": "wrong_plugin"}}}}
        with pytest.raises(ValueError, match=r"wrong_plugin"):
            SimNOS(inventory=inventory)

    def test_wrong_platform(self):
        """
        Test that the function _check_platform raises an exception
        when the platform is wrong.
        """
        inventory = {"hosts": {"R1": {"platform": "wrong_platform"}}}
        with pytest.raises(ValueError, match=r"Platform wrong_platform is not supported by SIMNOS"):
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
        """start/stop by host name; each step pins the cumulative running state.

        Driven as one sequence over a single SimNOS() instance (not parametrized
        per row) because each step's expectation depends on the prior steps'
        accumulated state.
        """
        # Host names come from default_inventory (SSoT); the sequence + expected
        # per-step states are hand-authored because they encode the cumulative order.
        c, h, a = default_inventory["hosts"]
        steps = [
            _Step("start", c, {c: True, h: False, a: False}),
            _Step("start", h, {c: True, h: True, a: False}),
            _Step("start", a, {c: True, h: True, a: True}),
            _Step("stop", c, {c: False, h: True, a: True}),
            _Step("stop", h, {c: False, h: False, a: True}),
            _Step("stop", a, {c: False, h: False, a: False}),
        ]
        net = SimNOS()
        try:
            for step in steps:
                getattr(net, step.action)(hosts=step.target)
                assert get_running_hosts(net.hosts) == step.running
        finally:
            net.stop()

    def test_simnos_base_inventory(self):
        """
        Base test for checking the start and stop operations
        using default inventory.
        """
        net = SimNOS()
        before_start = get_running_hosts(net.hosts)
        for running_state in before_start.values():
            assert not running_state

        net.start()
        after_start = get_running_hosts(net.hosts)
        for running_state in after_start.values():
            assert running_state

        net.stop()
        after_stop = get_running_hosts(net.hosts)
        for running_state in after_stop.values():
            assert not running_state

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


class TestPlatformsManifest:
    """
    Tests directly related to the platforms like the ordering
    or if the platforms match the docs and the real in the code.

    Renamed from ``TestPlatforms`` to disambiguate from
    ``tests/plugins/test_platforms.py::TestPlatforms`` which covers
    YAML format / runtime command execution; this class covers the
    ``available_platforms`` manifest integrity (ordering, docs match).
    """

    def test_available_platforms_match_docs(self):
        """
        Test if the available platforms are correct set
        in the platforms.md and platforms.py file.
        """
        assert sorted(available_platforms) == sorted(get_platforms_from_md())

    def test_available_platforms_match_mkdocs_nav(self):
        """Pin that the mkdocs.yml Platforms nav covers the full registry.

        Closes the M-1 failure mode (#239): a forgotten nav entry left a
        platform docs page silently unreachable from the site nav. The nav
        is now regenerated by `invoke gen-docs-platform-commands`; this pin
        catches both a missing entry (platform added without regenerating)
        and a stale one (platform removed). Parsed as text because
        mkdocs.yml holds material python tags that `yaml.safe_load` rejects.

        The parse is scoped to the Platforms section (and intentionally
        independent of `tasks.rewrite_mkdocs_platforms_nav`'s locator, so a
        locator bug cannot silently satisfy its own pin): an entry surviving
        in some other nav section must not count as "reachable".
        """
        with open("mkdocs.yml", encoding="utf-8") as file:
            lines = file.read().splitlines()
        start = lines.index("  - Platforms:")
        section_lines = []
        for line in lines[start + 1 :]:
            if not line.startswith("      - "):
                break
            section_lines.append(line)
        nav_platforms = set(re.findall(r'"platforms/([a-z0-9_]+)\.md"', "\n".join(section_lines))) - {"index"}
        assert nav_platforms == set(available_platforms)

    def test_available_platforms_in_py_file_are_ordered(self):
        """
        Test if the available platforms in the platforms.py file
        are ordered alphabetically.
        """
        assert list(available_platforms) == sorted(available_platforms)

    def test_available_platforms_is_read_only(self):
        """Pin that `available_platforms` is an immutable tuple (#237).

        A mutable list let consumers mutate the registry view in place;
        the tuple makes the derived view read-only at the type level.
        """
        assert isinstance(available_platforms, tuple)

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
        with pytest.raises(ValueError, match=r"platform and inventory cannot be used together"):

            @simnos(platform="cisco_ios", inventory="tests/assets/inventory.yaml")
            def dummy_function():
                pass

            dummy_function()

    def test_decorator_raise_error_if_not_platform_or_inventory_provided(self):
        """Test that the decorator raises an exception if neither platform nor inventory are set."""
        with pytest.raises(ValueError, match=r"platform or inventory must be set"):

            @simnos()
            def dummy_function():
                pass

            dummy_function()

    def test_available_platforms_derived_from_nos_plugins(self):
        """Pin that `available_platforms` is derived from `nos_plugins.keys()`.

        Source of truth integrity guard: any drift between the registry
        (`nos_plugins`) and the public symbol breaks this test immediately,
        catching the failure mode that issue #206 (G1) eliminated.
        """
        assert list(available_platforms) == sorted(nos_plugins.keys())

    def test_available_platforms_excludes_base_template(self):
        """Pin that `base_template` never surfaces in registry or manifest.

        `simnos/plugins/nos/platforms_py/_templates/base_template.py` is the
        plugin authoring template (BaseDevice example), not a user-facing
        platform. It is kept out of the registry by living in a subpackage
        that the non-recursive py glob never scans (#239 — previously a
        filename filter did this job); this pin catches a future glob
        recursion or a template module landing back in `platforms_py/`.
        """
        assert "base_template" not in available_platforms
        assert "base_template" not in nos_plugins

    def test_available_platforms_have_yaml_source(self):
        """Pin that every supported platform has a backing yaml file.

        Catches "dangling key" drift: if a yaml is deleted in a future PR
        but `available_platforms` is not updated (e.g. via a stale registry
        cache), this test fails. All current platforms ship at least a yaml
        definition; py-only entries (BaseDevice subclasses) live alongside
        yaml entries.
        """
        yaml_dir = "simnos/plugins/nos/platforms_yaml"
        for platform_name in available_platforms:
            yaml_path = f"{yaml_dir}/{platform_name}.yaml"
            assert os.path.isfile(yaml_path), (
                f"Platform '{platform_name}' is in available_platforms but its yaml file is missing: {yaml_path}"
            )

    def test_simnos_decorator_rejects_unknown_platform(self):
        """Pin that `simnos(platform=...)` raises at decorator-factory evaluation time.

        The validation lives in the decorator factory body (before the
        inner `decorator(func)` is returned), so a typo like
        `@simnos(platform="cisxo_ios")` raises at module load time rather
        than waiting until the wrapped function is called. Catching this
        early avoids paying test startup cost on a doomed run.
        """
        with pytest.raises(ValueError, match="not supported"):
            simnos(platform="nonexistent_platform")

    def test_simnos_decorator_accepts_known_platform(self):
        """Pin that a known platform does not raise at decorator evaluation.

        Negative-only tests (typo reject) would still pass if the new
        validation incorrectly rejected every platform; this happy-path
        test ensures the validation discriminates correctly.
        """
        # Should not raise — known platform from registry.
        decorator = simnos(platform="cisco_ios")
        assert callable(decorator)


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
            net._execute_function_over_hosts(hosts, "stop", host_running=True, deadline=999.0)
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
                hosts,
                "stop",
                host_running=True,
                parallel=True,
                deadline=1001.0,
            )

        mock_ex.shutdown.assert_called_once_with(wait=False, cancel_futures=True)

    def test_parallel_normal_completion_uses_shutdown_wait_true(self):
        """Parallel path without timeout: executor uses shutdown(wait=True)."""
        inventory = {
            "hosts": {
                "R1": {"port": 5001, "platform": "cisco_ios"},
                "R2": {"port": 5002, "platform": "cisco_ios"},
            }
        }
        net = SimNOS(inventory)
        hosts = list(net.hosts.values())
        for h in hosts:
            h.running = False
            h.start = Mock()

        mock_ex = MagicMock()
        mock_future = MagicMock()
        mock_ex.submit.return_value = mock_future

        with (
            patch("simnos.core.simnos.concurrent.futures.ThreadPoolExecutor", return_value=mock_ex),
            patch("simnos.core.simnos.concurrent.futures.as_completed", return_value=[mock_future]),
        ):
            net._execute_function_over_hosts(
                hosts,
                "start",
                host_running=False,
                parallel=True,
            )

        mock_ex.shutdown.assert_called_once_with(wait=True)

    def test_parallel_exception_uses_shutdown_wait_true(self):
        """Parallel path with exception (not timeout): executor still uses shutdown(wait=True)."""
        inventory = {
            "hosts": {
                "R1": {"port": 5001, "platform": "cisco_ios"},
                "R2": {"port": 5002, "platform": "cisco_ios"},
            }
        }
        net = SimNOS(inventory)
        hosts = list(net.hosts.values())
        for h in hosts:
            h.running = False
            h.start = Mock()

        mock_ex = MagicMock()
        mock_future = MagicMock()
        mock_future.result.side_effect = RuntimeError("start failed")
        mock_ex.submit.return_value = mock_future

        with (
            patch("simnos.core.simnos.concurrent.futures.ThreadPoolExecutor", return_value=mock_ex),
            patch("simnos.core.simnos.concurrent.futures.as_completed", return_value=[mock_future]),
            pytest.raises(RuntimeError, match="start failed"),
        ):
            net._execute_function_over_hosts(
                hosts,
                "start",
                host_running=False,
                parallel=True,
            )

        mock_ex.shutdown.assert_called_once_with(wait=True)
