"""
Test module for simnos.core.simnos.
The file can be found in simnos/core/simnos.py
"""

# pylint: disable=protected-access
import copy
import logging
import os
import platform
import re
import threading
from typing import NamedTuple, cast
from unittest.mock import MagicMock, Mock, patch

import pytest
import yaml

from a3_paths import PLATFORMS_DIR
from simnos.core.host import Host
from simnos.core.nos import Nos, available_platforms
from simnos.core.pydantic_models import ModelOverlay, ModelSysConfig
from simnos.core.simnos import SimNOS, default_inventory, simnos
from simnos.core.utils import _is_in_docker
from simnos.plugins.nos import nos_plugins, resolve_device_type
from tests.utils import (
    SYNTHETIC_CUSTOM_A3_DIR,
    SYNTHETIC_CUSTOM_HANDLERS,
    get_platforms_from_md,
    get_running_hosts,
    set_attr,
)


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
    pytest.param(
        {"default": {"port": 5000}, "hosts": {"R1": {"port": None}}},
        r"port must be an integer \(0 = ephemeral\)",
        id="port_explicit_null",
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
        expected_hosts = cast(dict, default_inventory["hosts"])
        default_config = cast(dict, default_inventory["default"])

        net = SimNOS()
        assert set(net.hosts) == set(expected_hosts)
        for router_name, host in net.hosts.items():
            # Mirror production's merge: host config overrides the shared default.
            expected = {**default_config, **expected_hosts[router_name]}
            assert host.username == expected["username"]
            assert host.password == expected["password"]
            # The default inventory now uses EPHEMERAL_PORT (0, #271); this host is
            # not started, so the ephemeral port is unresolved and both sides are 0.
            # The real port only lands on host.port after start() (Host.start / D4).
            assert host.port == expected["port"]
            assert host.server_inventory["plugin"] == "AsyncSshServer"
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
                    "device_type": available_platforms[0],
                },
                "R2": {
                    "port": 6000,
                    "username": "simnos_R2",
                    "password": "simnos_R2",
                    "device_type": available_platforms[0],
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
        inventory = {"hosts": {"R1": {"port": 5001, "device_type": "cisco_ios"}}}
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
        net.allocated_ports = {5000}
        with pytest.raises(ValueError, match=r"already in use"):
            net._allocate_port(5000)

    def test_allocate_port(self):
        """
        Test that the function _allocate_port allocates the port.
        """
        inventory = {"hosts": {"R1": {"port": 5000, "device_type": "cisco_ios"}}}
        net = SimNOS(inventory=inventory)
        assert 5000 in net.allocated_ports
        assert len(net.allocated_ports) == 1

    def test_allocate_port_range(self):
        """
        Test that the function _allocate_port allocates the port.
        """
        inventory = {"hosts": {"R1": {"port": [5000, 5001], "replicas": 2, "device_type": "cisco_ios"}}}
        net = SimNOS(inventory=inventory)
        assert net.allocated_ports == {5000, 5001}

    @pytest.mark.parametrize(
        "port",
        [-1, 65536, 100000],
        ids=["negative", "above_max", "far_above_max"],
    )
    def test_allocate_port_out_of_range(self, port):
        """Test that _allocate_port_single rejects ports outside 1-65535 (0 is ephemeral, #271)."""
        net = SimNOS()
        with pytest.raises(ValueError, match="out of valid range"):
            net._allocate_port_single(port)

    def test_allocate_port_ephemeral_is_noop(self):
        """port=0 (ephemeral, #271) is a no-op: no range error, no dedup error, and it is
        never registered in ``allocated_ports`` — so several hosts can all request 0
        (e.g. the default inventory's 3 hosts) without a spurious 'already in use'."""
        net = SimNOS()
        net._allocate_port_single(0)
        net._allocate_port_single(0)  # second port=0 must not raise "already in use"
        assert 0 not in net.allocated_ports

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

    def test_inventory_empty_dict_is_loud(self):
        """An explicit `inventory={}` fails on the missing `hosts`, loudly (#345).

        The old `inventory or deepcopy(default)` falsy check silently swapped an
        empty dict for the 3-host default environment.
        """
        with pytest.raises(ValueError, match="hosts"):
            SimNOS(inventory={})

    def test_get_hosts_as_list_empty_means_none(self):
        """An explicit empty host list selects NO hosts; only None selects all (#345).

        The old falsy check expanded `hosts=[]` (e.g. a programmatic filter that
        matched nothing) to every host, so `stop([])` stopped the whole environment.
        """
        net = SimNOS()
        assert net._get_hosts_as_list([]) == []
        assert len(net._get_hosts_as_list(None)) == len(net.hosts)

    def test_duplicate_host_name_from_replicas_is_loud(self):
        """A replicas-generated name colliding with an explicit host raises (#345).

        `r` with `replicas: 2` generates `r0`/`r1`; without the guard the later
        instantiation silently replaced the explicit `r0` in `self.hosts` and one
        configured host never started.
        """
        inventory = {
            "hosts": {
                "r0": {"port": 5100},
                "r": {"replicas": 2, "port": [5000, 5001]},
            }
        }
        with pytest.raises(ValueError, match=r"Duplicate host name 'r0'"):
            SimNOS(inventory=inventory)

    def test_env_data_dir_empty_is_loud(self, monkeypatch):
        """A set-but-empty SIMNOS_DATA_DIR raises, matching SIMNOS_SYS_CONFIG (#345).

        The old `if env_data_dir:` truthiness silently ignored an empty override.
        """
        monkeypatch.setenv("SIMNOS_DATA_DIR", "  ")
        with pytest.raises(ValueError, match="SIMNOS_DATA_DIR is set but empty"):
            SimNOS(inventory={"hosts": {}})

    @staticmethod
    def _sweep_mock_host(name: str, running: bool) -> Mock:
        """A minimal Host stand-in for the start/stop sweep tests (#347)."""
        h = Mock()
        h.name = name
        h.running = running
        h.server = None  # keeps _collect_server_threads empty
        return h

    @pytest.mark.parametrize("parallel", [False, True], ids=["serial", "parallel"])
    def test_stop_sweep_survives_one_host_failure(self, parallel):
        """One host's stop() raising no longer aborts the stop sweep (#347).

        The remaining hosts are still stopped, the shared-loop teardown still
        runs (it used to be skipped, leaking the loop thread), and the first
        error is re-raised at the end so the caller still learns stop() failed.
        """
        net = SimNOS(inventory={"hosts": {}})
        bad = self._sweep_mock_host("bad", running=True)
        bad.stop.side_effect = RuntimeError("stop boom")
        good = self._sweep_mock_host("good", running=True)
        net.hosts = {"bad": bad, "good": good}
        teardown = Mock(return_value=True)
        net._shared_loop.teardown_if_idle = teardown
        with pytest.raises(RuntimeError, match="stop boom"):
            net.stop(parallel=parallel)
        good.stop.assert_called_once()
        teardown.assert_called_once()

    def test_start_sweep_stays_fail_fast(self):
        """start() keeps fail-fast semantics: a failing host aborts immediately (#347).

        The collect-and-continue boundary is a stop-path contract only; starting
        the remaining environment after one host failed would hand the caller a
        partially-started cluster that looks successful.
        """
        net = SimNOS(inventory={"hosts": {}})
        bad = self._sweep_mock_host("bad", running=False)
        bad.start.side_effect = RuntimeError("bind failed")
        second = self._sweep_mock_host("second", running=False)
        net.hosts = {"bad": bad, "second": second}
        with pytest.raises(RuntimeError, match="bind failed"):
            net.start()
        second.start.assert_not_called()

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
        inventory = {"hosts": {"R1": {"device_type": "wrong_platform"}}}
        with pytest.raises(ValueError, match=r"Platform wrong_platform is not supported by SIMNOS"):
            SimNOS(inventory=inventory)

    def test_legacy_platform_key_rejected(self):
        """The v2 `platform:` key is rejected in v3 (#266, 案3-A complete breaking).

        v3 renamed the inventory field to `device_type` with no compat alias;
        `extra="forbid"` on the inventory models makes a stale `platform:` a hard
        load error (the migration path is a version pin / key rename, not an
        in-place alias). This pins that the breaking change stays breaking.
        """
        inventory = {"hosts": {"R1": {"platform": "cisco_ios"}}}
        with pytest.raises(ValueError, match=r"Extra inputs are not permitted"):
            SimNOS(inventory=inventory)

    def test_plugins_str_a3_dir_registers_under_basename(self):
        """A str plugin (A3 platform dir path) registers under the dir basename (#317 P-4).

        The route `creating_nos_plugin.md` documents for an external
        static-only platform: `SimNOS(plugins=["path/to/dir"])` builds a Nos
        from the dir and keys it by the platform name (= dir basename), so an
        inventory `nos: {plugin: <basename>}` resolves to it. The registration
        lands on the per-instance registry only — the module-global stays
        clean (#346), so no teardown is needed.
        """
        net = SimNOS(inventory={"hosts": {}}, plugins=[SYNTHETIC_CUSTOM_A3_DIR])
        assert "synthetic_custom" in net.nos_plugins
        registered = net.nos_plugins["synthetic_custom"]
        assert isinstance(registered, Nos)
        assert registered.resolved_platform is not None
        assert "show clock" in registered.resolved_platform.commands
        assert "synthetic_custom" not in nos_plugins

    def test_plugins_str_py_path_rejected(self):
        """A str plugin pointing at a `.py` file (or any non-dir) is loud (#317 P-4).

        A py module alone cannot author commands, so the py-path escape hatch
        the dict/py plugin forms provided is gone — the caller is pointed at
        the `Nos(filename=[a3_dir, handler_py])` route instead.
        """
        with pytest.raises(ValueError, match=r"is not an A3 platform dir"):
            SimNOS(inventory={"hosts": {}}, plugins=[SYNTHETIC_CUSTOM_HANDLERS])

    def test_plugins_dict_rejected(self):
        """The dict plugin form (legacy `from_dict` inflow) is gone (#317 P-4)."""
        with pytest.raises(TypeError, match=r"supported str \(A3 platform dir\) or Nos"):
            # cast: this deliberately violates the `list[str | Nos]` annotation —
            # the loud runtime TypeError is exactly what the test pins.
            SimNOS(inventory={"hosts": {}}, plugins=cast("list[str | Nos]", [{"name": "legacy", "commands": {}}]))

    def test_device_type_netmiko_alias_resolves(self):
        """A netmiko-canonical `device_type` resolves to its internal platform (#266 / D2).

        `edgecore_sonic` is edgecore's `netmiko_device_type` alias (not its
        internal name); inventory may name a platform by that alias and the host
        validates/builds without error, while `available_platforms` keeps the
        internal name. This is the 2-key capability the alias index unlocks.
        """
        inventory = {"hosts": {"R1": {"device_type": "edgecore_sonic"}}}
        net = SimNOS(inventory=inventory)
        assert net.hosts["R1"].device_type == "edgecore_sonic"
        assert "edgecore" in available_platforms
        assert "edgecore_sonic" not in available_platforms
        # The alias resolves to the internal platform key (the reverse-index core).
        assert resolve_device_type("edgecore_sonic") == "edgecore"

    def test_resolve_device_type_test_injected_and_unknown(self, monkeypatch):
        """resolve_device_type serves a test-injected platform and None-passes the unknown (#266 / D2).

        The unknown → None half is what the `nos: {plugin: X}` path relies on:
        the `start()` chokepoint falls back to the raw key and resolves it
        against the per-instance registry — `SimNOS(plugins=[...])` registrations
        never reach the frozen module-global (#346). The dynamic-fallback half
        is the deliberate monkeypatch seam the frozen registry keeps: an entry
        injected into the global still resolves by identity even though the
        import-time index predates it.
        """
        import simnos.plugins.nos as nos_registry

        assert resolve_device_type("runtime_only_nos") is None  # unknown → None (chokepoint passes raw through)
        monkeypatch.setitem(nos_registry.nos_plugins, "runtime_only_nos", ["<runtime-registered>"])
        assert resolve_device_type("runtime_only_nos") == "runtime_only_nos"  # identity via dynamic fallback

    def test_inventory_validation_cmdshell_plugin(self):
        """
        Test that the inventory is validated when
        it contains a shell plugin.
        """
        inventory = {
            "hosts": {
                "R1": {
                    "port": 6000,
                    "device_type": available_platforms[0],
                    "shell": {
                        "plugin": "CMDShell",
                        "configuration": {},
                    },
                }
            }
        }
        net = SimNOS(inventory=inventory)
        assert isinstance(net.inventory, dict)
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
                    "device_type": "huawei_smartax",
                    "configuration_file": "tests/assets/test_module.yaml.j2",
                }
            }
        }
        with SimNOS(inventory=inventory) as net:
            host: Host = next(iter(net.hosts.values()))
            assert host.nos is not None and host.nos.device is not None  # ty narrowing (host.nos: None | Nos)
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
            assert host.nos is not None and host.nos.device is not None  # ty narrowing (host.nos: None | Nos)
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

    def test_nos_load_inventory_from_py_and_data_source(self):
        """
        Test cisco_ios NOS loaded correctly as it has two sources: the A3
        platform dir (#264 — replaced the legacy cisco_ios.yaml) and cisco_ios.py.
        """
        inventory = {"hosts": {"R1": {"port": 5001, "device_type": "cisco_ios"}}}
        net = SimNOS(inventory)
        cisco_sources = net.nos_plugins["cisco_ios"]
        assert isinstance(cisco_sources, list)
        assert len(cisco_sources) == 2, "Not all files detected"


class TestInstanceIsolation:
    """SimNOS instances do not contaminate each other or their callers (#346).

    Ownership contract: the module-global `nos_plugins` registry is frozen after
    import — `SimNOS(plugins=[...])` registrations go to the per-instance copy —
    and caller-passed containers (inventory dict / sys_config dict / plugins
    list) are borrowed read-only; SimNOS mutates only its own copies.
    """

    def test_plugin_registration_stays_per_instance(self):
        """A `plugins=[...]` registration is invisible to the global and to other instances."""
        net_a = SimNOS(inventory={"hosts": {}}, plugins=[SYNTHETIC_CUSTOM_A3_DIR])
        net_b = SimNOS(inventory={"hosts": {}})
        assert "synthetic_custom" in net_a.nos_plugins
        assert "synthetic_custom" not in nos_plugins
        assert "synthetic_custom" not in net_b.nos_plugins

    def test_builtin_shadowing_is_instance_local_and_lists_are_copied(self):
        """Shadowing a built-in name, and mutating an entry list, stay instance-local.

        The identity / append pins run against a NON-shadowed entry on purpose:
        the shadowed one holds a `Nos` instance, so an identity check against the
        global's path list would be vacuous (different types) and `append` an
        AttributeError. What must not leak is an element added to a copied path
        list — the one-level-deep copy's whole point (#346).
        """
        shadow_nos = Nos(filename=os.path.join(PLATFORMS_DIR, "cisco_ios"))
        net_a = SimNOS(inventory={"hosts": {}}, plugins=[shadow_nos])
        net_b = SimNOS(inventory={"hosts": {}})
        # The shadow is visible only inside net_a; global / net_b keep the path list.
        assert net_a.nos_plugins["cisco_ios"] is shadow_nos
        assert isinstance(nos_plugins["cisco_ios"], list)
        assert isinstance(net_b.nos_plugins["cisco_ios"], list)
        # Value lists are copied, and an element appended to one instance's list
        # reaches neither the global nor another instance. `cast` for ty: the
        # runtime isinstance pin narrows to `list | (Nos & list)` (Nos is not
        # final), which still rejects `.append(str)`.
        entry_a = cast("list[str]", net_a.nos_plugins["arista_eos"])
        entry_b = cast("list[str]", net_b.nos_plugins["arista_eos"])
        assert isinstance(entry_a, list)
        assert entry_a is not nos_plugins["arista_eos"]
        assert entry_b is not nos_plugins["arista_eos"]
        assert entry_a is not entry_b
        entry_a.append("<instance-local>")
        assert "<instance-local>" not in nos_plugins["arista_eos"]
        assert "<instance-local>" not in entry_b

    def test_registered_nos_resolves_for_host_and_is_shared_as_is(self):
        """The documented custom-plugin flow works off the per-instance registry (#346).

        `resolve_device_type` no longer sees instance registrations (the global
        is frozen), so the raw-key fallback → per-instance lookup chain in
        `Host.start` is load-bearing — this pins the `creating_nos_plugin.md`
        flow end to end (the handler-platform variant: the synthetic platform
        has `handler:` commands, so the Nos needs the A3 dir plus the handler
        module), plus the contract's deliberate exception: a caller-built `Nos`
        is registered and reused as-is, never copied.
        """
        caller_nos = Nos(filename=[SYNTHETIC_CUSTOM_A3_DIR, SYNTHETIC_CUSTOM_HANDLERS])
        inventory = {"hosts": {"R1": {"nos": {"plugin": "synthetic_custom"}}}}
        net = SimNOS(inventory=inventory, plugins=[caller_nos])
        assert net.plugins[0] is caller_nos
        assert net.nos_plugins["synthetic_custom"] is caller_nos
        # start() inside the try: a mid-start failure must still reach stop()
        # (partial-start resources would otherwise leak into later tests).
        try:
            net.start()
            assert net.hosts["R1"].nos is caller_nos
        finally:
            net.stop()

    def test_explicit_inventory_dict_is_not_mutated(self):
        """An explicit inventory dict is borrowed read-only — no defaults baked in."""
        caller_inventory = {"hosts": {"R1": {"device_type": "cisco_ios"}}}
        snapshot = copy.deepcopy(caller_inventory)
        SimNOS(inventory=caller_inventory)
        assert caller_inventory == snapshot

    def test_reused_inventory_does_not_inherit_prior_sys_config_seed(self):
        """The #346 failure scenario: instance A's sys_config seed must not leak into B.

        Before the fix, `_load_inventory` baked A's seeded `variants_policy` into
        the caller's dict; B's seed check then mistook it for an explicit
        inventory value and silently inherited A's setting.
        """
        inventory = {"hosts": {}}
        SimNOS(inventory=inventory, sys_config={"variants_policy": {"select": 1}})
        net_b = SimNOS(inventory=inventory, sys_config={"variants_policy": {"select": 2}})
        assert isinstance(net_b.inventory, dict)
        assert net_b.inventory["default"]["variants_policy"]["select"] == 2

    def test_caller_plugins_list_is_not_mutated(self):
        """The plugins list container is copied; a later caller append is invisible.

        (The `Nos` *elements* are deliberately shared, pinned by
        `test_registered_nos_resolves_for_host_and_is_shared_as_is`.)
        """
        caller_plugins: list[str | Nos] = [SYNTHETIC_CUSTOM_A3_DIR]
        net = SimNOS(inventory={"hosts": {}}, plugins=caller_plugins)
        caller_plugins.append("<appended-after-init>")
        assert net.plugins == [SYNTHETIC_CUSTOM_A3_DIR]
        # And the read-only-borrow half: SimNOS wrote nothing into the caller's
        # list — only the caller's own append is there.
        assert caller_plugins == [SYNTHETIC_CUSTOM_A3_DIR, "<appended-after-init>"]

    def test_caller_sys_config_dict_is_not_mutated(self):
        """An explicit sys_config dict is borrowed read-only (contract symmetry).

        Already true before #346 (`ModelSysConfig(**raw).model_dump()` builds a
        fresh dict); pinned so all three caller-passed containers stay covered.
        """
        caller_sys_config = {"variants_policy": {"select": 1}}
        snapshot = copy.deepcopy(caller_sys_config)
        SimNOS(inventory={"hosts": {}}, sys_config=caller_sys_config)
        assert caller_sys_config == snapshot


class TestReservedInventoryFields:
    """Inventory render fields (`facts` / `overlay` / `variants_policy`).

    `overlay` is consumed by #286 (Host.start resolves the overlay dir);
    `variants_policy` by #287 (threaded to the shell). `facts` stays a reservation
    for the Layer-2 follow-up issue — accepted + validated but no-op. These pin
    that they (a) load without error, (b) reach the Host as attributes, and (c)
    the still-reserved `facts` warns loudly when set so the no-op is never silent
    (Decision 5, anti-silent-bug).
    """

    def test_reserved_fields_accepted_and_reach_host(self):
        """facts / overlay / variants_policy load and are stored on the Host."""
        inventory = {
            "hosts": {
                "R1": {
                    "port": 6100,
                    "device_type": "cisco_ios",
                    "facts": {"hostname": "R1", "serial": "ABC"},
                    "overlay": {"override_commands": ["show version"]},
                    "variants_policy": {"select": 0},
                }
            }
        }
        net = SimNOS(inventory=inventory)
        host = net.hosts["R1"]
        assert host.facts == {"hostname": "R1", "serial": "ABC"}
        assert host.overlay == {"override_commands": ["show version"]}
        assert host.variants_policy == {"select": 0}

    def test_reserved_field_warns_when_set(self, caplog):
        """A set reserved field emits a no-op warning (not a silent inert config)."""
        inventory = {"hosts": {"R1": {"port": 6101, "device_type": "cisco_ios", "facts": {"k": "v"}}}}
        with caplog.at_level(logging.WARNING, logger="simnos.core.host"):
            SimNOS(inventory=inventory)
        warnings = [r.getMessage() for r in caplog.records if "reserved field" in r.getMessage()]
        assert any("'facts'" in m and "no effect yet" in m for m in warnings)

    def test_reserved_fields_absent_no_warning(self, caplog):
        """A plain inventory (no reserved fields) emits no reserved-field warning."""
        inventory = {"hosts": {"R1": {"port": 6102, "device_type": "cisco_ios"}}}
        with caplog.at_level(logging.WARNING, logger="simnos.core.host"):
            SimNOS(inventory=inventory)
        assert not [r for r in caplog.records if "reserved field" in r.getMessage()]

    def test_overlay_random_commands_warns_noop(self, caplog):
        """`overlay.random_commands` is the #287 vessel — inert in #286, so a set
        value warns (anti-silent-bug) even though `overlay.override_commands` is consumed."""
        inventory = {
            "hosts": {
                "R1": {"port": 6107, "device_type": "cisco_ios", "overlay": {"random_commands": ["show version"]}}
            }
        }
        with caplog.at_level(logging.WARNING, logger="simnos.core.host"):
            SimNOS(inventory=inventory)
        assert any(
            "overlay.random_commands" in r.getMessage() and "no effect yet" in r.getMessage() for r in caplog.records
        )

    def test_variants_policy_set_does_not_warn_noop(self, caplog):
        """`variants_policy` is consumed by #287 (not a reservation), so setting it
        emits no reserved-field no-op warning — the #287 regression pin for the
        removed #266 warning (3rd round claude#3)."""
        inventory = {"hosts": {"R1": {"port": 6108, "device_type": "cisco_ios", "variants_policy": {"select": 1}}}}
        with caplog.at_level(logging.WARNING, logger="simnos.core.host"):
            SimNOS(inventory=inventory)
        assert not [
            r for r in caplog.records if "reserved field" in r.getMessage() and "variants_policy" in r.getMessage()
        ]

    def test_seed_without_random_select_warns(self, caplog):
        """`variants_policy.seed` set while `select` is not 'random' is inert (seed
        only affects random selection), so it warns — anti-silent-bug (3rd round
        claude#2, the test for the 1st-round claude#3 warning)."""
        inventory = {
            "hosts": {"R1": {"port": 6109, "device_type": "cisco_ios", "variants_policy": {"select": 0, "seed": 1234}}}
        }
        with caplog.at_level(logging.WARNING, logger="simnos.core.host"):
            SimNOS(inventory=inventory)
        assert any(
            "variants_policy.seed" in r.getMessage() and "the seed is ignored" in r.getMessage() for r in caplog.records
        )

    def test_overlay_schema_rejects_unknown_key(self):
        """ModelOverlay keeps `extra="forbid"` — a typo'd overlay key is rejected."""
        with pytest.raises(ValueError, match=r"Extra inputs are not permitted"):
            ModelOverlay(override_commands="all", bogus=1)  # ty: ignore[unknown-argument]  # intentional: extra="forbid" probe

    def test_reserved_field_extra_still_forbidden(self):
        """Reserving fields does not loosen `extra="forbid"` on the inventory."""
        inventory = {"hosts": {"R1": {"port": 6103, "device_type": "cisco_ios", "bogus_field": 1}}}
        with pytest.raises(ValueError, match=r"Extra inputs are not permitted"):
            SimNOS(inventory=inventory)


class TestSysConfig:
    """sys_config.yaml loading + precedence (#266 / D4).

    sys_config holds environment-wide settings (`data_dir` / `variants_policy`);
    #266 introduces loading (arg / env / cwd / home discovery), the
    `SIMNOS_DATA_DIR` env override, and the `sys_config < inventory` precedence
    rung. `data_dir` is consumed by the overlay loader in #286; `variants_policy`
    is consumed by #287 (threaded to the shell).
    """

    def test_default_is_empty_resolved(self):
        """No sys_config anywhere → resolved defaults (data_dir/variants_policy None,
        paging materialized with default_rows=24, #307 / P3-4)."""
        net = SimNOS()
        assert net.sys_config == {"data_dir": None, "variants_policy": None, "paging": {"default_rows": 24}}

    def test_paging_default_rows_override(self):
        """`paging.default_rows` is read from sys_config and validated (gt=0, #307)."""
        net = SimNOS(sys_config={"paging": {"default_rows": 40}})
        assert net.sys_config["paging"]["default_rows"] == 40

    def test_paging_default_rows_rejects_non_positive(self):
        """A 0/negative default_rows is loud — a 0-row page would break the pager (#307)."""
        with pytest.raises(ValueError, match="greater than 0"):
            SimNOS(sys_config={"paging": {"default_rows": 0}})

    def test_dict_arg_used_as_is(self):
        """A dict arg is validated and stored verbatim."""
        net = SimNOS(sys_config={"data_dir": "/srv/simnos"})
        assert net.sys_config["data_dir"] == "/srv/simnos"

    def test_path_arg_loaded(self, tmp_path):
        """A str arg is read as a YAML path."""
        cfg = tmp_path / "sys_config.yaml"
        cfg.write_text("data_dir: /from/file\n", encoding="utf-8")
        net = SimNOS(sys_config=str(cfg))
        assert net.sys_config["data_dir"] == "/from/file"

    def test_missing_explicit_path_raises(self, tmp_path):
        """An explicit path that does not exist is a loud error."""
        with pytest.raises(FileNotFoundError, match="sys_config file not found"):
            SimNOS(sys_config=str(tmp_path / "nope.yaml"))

    def test_env_path_discovered(self, tmp_path, monkeypatch):
        """`SIMNOS_SYS_CONFIG` env points at the file when no arg is given."""
        cfg = tmp_path / "sys_config.yaml"
        cfg.write_text("data_dir: /from/env\n", encoding="utf-8")
        monkeypatch.setenv("SIMNOS_SYS_CONFIG", str(cfg))
        net = SimNOS()
        assert net.sys_config["data_dir"] == "/from/env"

    def test_empty_env_is_loud(self, monkeypatch):
        """`SIMNOS_SYS_CONFIG=""` (set but empty) is a config mistake, not a
        silent fall-through to cwd/home discovery (#267 / D4)."""
        monkeypatch.setenv("SIMNOS_SYS_CONFIG", "")
        with pytest.raises(ValueError, match="SIMNOS_SYS_CONFIG is set but empty"):
            SimNOS()

    def test_whitespace_only_env_is_loud(self, monkeypatch):
        """A whitespace-only value is treated the same as empty (#267 / D4)."""
        monkeypatch.setenv("SIMNOS_SYS_CONFIG", "   ")
        with pytest.raises(ValueError, match="SIMNOS_SYS_CONFIG is set but empty"):
            SimNOS()

    def test_padded_env_path_is_stripped(self, tmp_path, monkeypatch):
        """A padded env path is stripped before use, matching --sys-config (#267, gemini#2 2nd)."""
        cfg = tmp_path / "sys_config.yaml"
        cfg.write_text("data_dir: /from/env\n", encoding="utf-8")
        monkeypatch.setenv("SIMNOS_SYS_CONFIG", f"  {cfg}  ")
        net = SimNOS()
        assert net.sys_config["data_dir"] == "/from/env"

    def test_padded_str_arg_is_stripped(self, tmp_path):
        """A padded str sys_config arg is stripped too, symmetric with the env branch (#267, claude#3 3rd)."""
        cfg = tmp_path / "sys_config.yaml"
        cfg.write_text("data_dir: /from/arg\n", encoding="utf-8")
        net = SimNOS(sys_config=f"  {cfg}  ")
        assert net.sys_config["data_dir"] == "/from/arg"

    def test_cwd_discovered(self, tmp_path, monkeypatch):
        """`./sys_config.yaml` in cwd is discovered when no arg/env is set."""
        # env is already cleared by the autouse `_isolate_sys_config_env` fixture.
        (tmp_path / "sys_config.yaml").write_text("data_dir: /from/cwd\n", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        net = SimNOS()
        assert net.sys_config["data_dir"] == "/from/cwd"

    def test_data_dir_env_overrides_file(self, tmp_path, monkeypatch):
        """`SIMNOS_DATA_DIR` wins over the file's data_dir (env > sys_config)."""
        cfg = tmp_path / "sys_config.yaml"
        cfg.write_text("data_dir: /from/file\n", encoding="utf-8")
        monkeypatch.setenv("SIMNOS_DATA_DIR", "/from/env/override")
        net = SimNOS(sys_config=str(cfg))
        assert net.sys_config["data_dir"] == "/from/env/override"

    def test_variants_policy_seeds_inventory_default(self):
        """sys_config variants_policy seeds the inventory default → reaches hosts.

        sys_config is validated + `model_dump`ed (`_load_sys_config`), so a
        sys_config-sourced `variants_policy` materializes the typed model's
        default fields (`seed: None`); the inventory path keeps the raw dict.
        Both parse to the same `ModelVariantsPolicy` at Host.start (#287 / D8).
        """
        net = SimNOS(
            inventory={"hosts": {"R1": {"port": 6104, "device_type": "cisco_ios"}}},
            sys_config={"variants_policy": {"select": 1}},
        )
        assert net.hosts["R1"].variants_policy == {"select": 1, "seed": None}

    def test_inventory_default_wins_over_sys_config(self):
        """A more specific inventory default beats the sys_config global (precedence)."""
        net = SimNOS(
            inventory={
                "default": {"variants_policy": {"select": 2}},
                "hosts": {"R1": {"port": 6105, "device_type": "cisco_ios"}},
            },
            sys_config={"variants_policy": {"select": 1}},
        )
        assert net.hosts["R1"].variants_policy == {"select": 2}

    def test_host_wins_over_sys_config(self):
        """A per-host value beats both inventory default and sys_config (host most specific)."""
        net = SimNOS(
            inventory={"hosts": {"R1": {"port": 6106, "device_type": "cisco_ios", "variants_policy": {"select": 3}}}},
            sys_config={"variants_policy": {"select": 1}},
        )
        assert net.hosts["R1"].variants_policy == {"select": 3}

    def test_extra_key_rejected(self):
        """ModelSysConfig keeps `extra="forbid"` — an unknown key is rejected."""
        with pytest.raises(ValueError, match=r"Extra inputs are not permitted"):
            ModelSysConfig(data_dir="/x", bogus=1)  # ty: ignore[unknown-argument]  # intentional: extra="forbid" probe

    def test_non_mapping_file_raises(self, tmp_path):
        """A sys_config file that is not a mapping is a loud TypeError."""
        cfg = tmp_path / "sys_config.yaml"
        cfg.write_text("- just\n- a\n- list\n", encoding="utf-8")
        with pytest.raises(TypeError, match="sys_config must be a mapping"):
            SimNOS(sys_config=str(cfg))

    def test_data_dir_set_does_not_warn_noop(self, caplog):
        """A set data_dir no longer warns no-op — it is consumed by the overlay loader (#286).

        A host only resolves the overlay dir from data_dir when it opts in via
        `overlay.override_commands`; an unused data_dir is a valid environment
        default, not a silently-inert config, so the #266 no-op warning is gone.
        """
        with caplog.at_level(logging.WARNING, logger="simnos.core.simnos"):
            SimNOS(sys_config={"data_dir": "/srv"})
        assert not any("data_dir" in r.getMessage() and "no effect yet" in r.getMessage() for r in caplog.records)

    def test_sys_config_seed_does_not_pollute_default_inventory(self):
        """sys_config seeding must not mutate the module-global default_inventory (1st round codex#1).

        `SimNOS()` deepcopies `default_inventory` as its fallback, so seeding a
        sys_config `variants_policy` into the inventory default stays per-instance.
        Pins that the global stays clean and a subsequent plain `SimNOS()` host
        does not inherit the prior instance's seeded policy (process-global leak).
        """
        SimNOS(sys_config={"variants_policy": {"select": 5}})
        assert "variants_policy" not in default_inventory["default"]
        net = SimNOS()
        assert next(iter(net.hosts.values())).variants_policy is None


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

    @simnos(device_type="cisco_ios", return_instance=True)
    def test_decorator_with_device_type(self, net: SimNOS):
        """Test that the decorator works with a device_type."""
        platforms_used = []
        for host in net.hosts.values():
            nos = host.nos
            assert nos is not None
            platforms_used.append(nos.name)
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

    def test_decorator_raise_error_if_device_type_and_inventory_provided(self):
        """Test that the decorator raises an exception if both device_type and inventory are set."""
        with pytest.raises(ValueError, match=r"device_type and inventory cannot be used together"):

            @simnos(device_type="cisco_ios", inventory="tests/assets/inventory.yaml")
            def dummy_function():
                pass

            dummy_function()

    def test_decorator_raise_error_if_not_device_type_or_inventory_provided(self):
        """Test that the decorator raises an exception if neither device_type nor inventory are set."""
        with pytest.raises(ValueError, match=r"device_type or inventory must be set"):

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

    def test_available_platforms_excludes_base_device(self):
        """Pin that `base_device` never surfaces in registry or manifest.

        `simnos/plugins/nos/base_device.py` is the runtime `BaseDevice` base
        class, not a user-facing platform. It is kept out of the registry by
        living outside `platforms_py/` — the only dir the non-recursive py
        glob scans (#239 / #350; previously a filename filter, then a
        `_templates/` subpackage, did this job). This pin catches the module
        landing back in `platforms_py/` (where the glob would register it as
        an orphan platform).
        """
        assert "base_device" not in available_platforms
        assert "base_device" not in nos_plugins

    def test_available_platforms_have_data_source(self):
        """Pin that every supported platform has a backing data source.

        Catches "dangling key" drift: if a data source is deleted in a future
        PR but `available_platforms` is not updated (e.g. via a stale registry
        cache), this test fails. A platform's data source is its A3
        ``platforms/<p>/`` directory and/or a ``platforms_py/<p>.py`` module —
        the same and/or the registry permits (#264 / D6), so the pin matches
        `test_registry_data_source_is_a3_dir_and_or_py_module`.
        """
        py_dir = "simnos/plugins/nos/platforms_py"
        for platform_name in available_platforms:
            a3_path = f"{PLATFORMS_DIR}/{platform_name}/platform.yaml"
            py_path = f"{py_dir}/{platform_name}.py"
            assert os.path.isfile(a3_path) or os.path.isfile(py_path), (
                f"Platform '{platform_name}' is in available_platforms but has no data source "
                f"(neither {a3_path} nor {py_path})"
            )

    def test_simnos_decorator_rejects_unknown_platform(self):
        """Pin that `simnos(device_type=...)` raises at decorator-factory evaluation time.

        The validation lives in the decorator factory body (before the
        inner `decorator(func)` is returned), so a typo like
        `@simnos(device_type="cisxo_ios")` raises at module load time rather
        than waiting until the wrapped function is called. Catching this
        early avoids paying test startup cost on a doomed run.
        """
        with pytest.raises(ValueError, match="not supported"):
            simnos(device_type="nonexistent_platform")

    def test_simnos_decorator_accepts_known_platform(self):
        """Pin that a known platform does not raise at decorator evaluation.

        Negative-only tests (typo reject) would still pass if the new
        validation incorrectly rejected every platform; this happy-path
        test ensures the validation discriminates correctly.
        """
        # Should not raise — known platform from registry.
        decorator = simnos(device_type="cisco_ios")
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
            net._join_threads(cast(list[threading.Thread], mock_threads))

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
                "R1": {"port": 5001, "device_type": "cisco_ios"},
                "R2": {"port": 5002, "device_type": "cisco_ios"},
                "R3": {"port": 5003, "device_type": "cisco_ios"},
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
            set_attr(h, "stop", slow_stop)

        # Deadline already in the past → all hosts skipped
        with patch("simnos.core.simnos.time.monotonic", return_value=1000.0):
            net._execute_function_over_hosts(hosts, "stop", host_running=True, deadline=999.0)
        assert call_count[0] == 0, "No hosts should have been stopped past deadline"

    def test_parallel_deadline_uses_shutdown_wait_false(self):
        """Parallel path: executor uses shutdown(wait=False, cancel_futures=True)."""
        inventory = {
            "hosts": {
                "R1": {"port": 5001, "device_type": "cisco_ios"},
                "R2": {"port": 5002, "device_type": "cisco_ios"},
            }
        }
        net = SimNOS(inventory)
        hosts = list(net.hosts.values())
        for h in hosts:
            h.running = True
            set_attr(h, "stop", Mock())

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
                "R1": {"port": 5001, "device_type": "cisco_ios"},
                "R2": {"port": 5002, "device_type": "cisco_ios"},
            }
        }
        net = SimNOS(inventory)
        hosts = list(net.hosts.values())
        for h in hosts:
            h.running = False
            set_attr(h, "start", Mock())

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
                "R1": {"port": 5001, "device_type": "cisco_ios"},
                "R2": {"port": 5002, "device_type": "cisco_ios"},
            }
        }
        net = SimNOS(inventory)
        hosts = list(net.hosts.values())
        for h in hosts:
            h.running = False
            set_attr(h, "start", Mock())

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
