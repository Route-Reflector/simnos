"""
Main module to interact with SimNOS servers.
It is the entry point to start, stop and list SimNOS servers.
"""

import concurrent.futures
import copy
import functools
import logging
import os
from pathlib import Path
import platform
import threading
import time

import yaml

from simnos.core.host import Host
from simnos.core.nos import Nos
from simnos.core.pydantic_models import EPHEMERAL_PORT, ModelSimnosInventory, ModelSysConfig
from simnos.core.servers import join_threads_with_deadline
from simnos.core.shared_loop import SharedLoop
from simnos.core.timeouts import (
    SHUTDOWN_GLOBAL_DEADLINE,
    SHUTDOWN_SAFETY_NET_DEADLINE,
    SHUTDOWN_SAFETY_NET_PER_THREAD,
)
from simnos.core.utils import _is_in_docker
from simnos.plugins.nos import assert_platform_supported, nos_plugins
from simnos.plugins.servers import servers_plugins
from simnos.plugins.shell import shell_plugins

log = logging.getLogger(__name__)

DEFAULT_PORT_START = 6000

# Ports are EPHEMERAL_PORT (0): a no-arg `SimNOS()` binds OS-assigned ports so
# parallel test workers never collide on a fixed port (#271, system B). The real
# port lands on `host.port` after start. `DEFAULT_PORT_START` stays the CLI default
# for `simnos up -d <dev>` (cli.py).
default_inventory = {
    "default": {
        "username": "user",
        "password": "user",
        "port": EPHEMERAL_PORT,
        "server": {
            "plugin": "AsyncSshServer",
            "configuration": {
                "address": "127.0.0.1",
                "timeout": 1,
            },
        },
        "shell": {"plugin": "CMDShell", "configuration": {}},
        "nos": {"plugin": "cisco_ios", "configuration": {}},
    },
    "hosts": {
        "router_cisco_ios": {"port": EPHEMERAL_PORT, "device_type": "cisco_ios"},
        "router_huawei_smartax": {"port": EPHEMERAL_PORT, "device_type": "huawei_smartax"},
        "router_arista_eos": {"port": EPHEMERAL_PORT, "device_type": "arista_eos"},
    },
}

# If Windows or WSL, the configuration address is 0.0.0.0
# WSL Bug: https://github.com/microsoft/WSL/issues/4983
if _is_in_docker() and "WSL2" in platform.release():
    server_config = default_inventory["default"]["server"]["configuration"]
    server_config["address"] = "0.0.0.0"  # noqa: S104


class SimNOS:
    """
    SimNOS class is a main entry point to interact
    with SimNOS servers - start, stop, list.

    :param inventory: SimNOS inventory dictionary or
                      OS path to .yaml file with inventory data
    :param plugins: Plugins to add extra devices/commands
                    currently not supported easily.
    :param sys_config: SimNOS environment config (`sys_config.yaml`): a dict, an
                       OS path to a .yaml file, or None to auto-discover
                       (see ``_discover_sys_config``). Holds environment-wide
                       settings (data_dir, variants_policy); the inventory holds
                       topology (#266 / D4).

    Sample usage:

    ```python
    from simnos import SimNOS

    net = SimNOS()
    net.start()
    ```
    """

    def __init__(
        self,
        inventory: dict | str | None = None,
        plugins: list | None = None,
        sys_config: dict | str | None = None,
    ) -> None:
        # deepcopy the module-global fallback: `_load_inventory` reassigns
        # `self.inventory["default"]` (and `_seed_inventory_default_from_sys_config`
        # seeds sys_config into it), so aliasing the global would bake per-instance
        # state into it and leak to later `SimNOS()` calls (1st round codex#1). An
        # explicit `inventory` is the caller's own object and left untouched.
        self.inventory: dict | str = inventory or copy.deepcopy(default_inventory)
        self.plugins: list = plugins or []

        self.hosts: dict[str, Host] = {}
        self.allocated_ports: set[int] = set()

        self.shell_plugins = shell_plugins
        self.nos_plugins = nos_plugins
        self.servers_plugins = servers_plugins

        # The shared asyncio loop the async server plugins (AsyncSshServer +
        # telnetlib3 TelnetServer) run on (#297, §1). Owned here as a SimNOS-scoped
        # resource; the loop thread + bounded executor start lazily on the first
        # async host start (``ensure_shared_loop``) and are torn down once in
        # ``stop()`` when no async host remains.
        self._shared_loop = SharedLoop()

        self._load_sys_config(sys_config)
        self._load_inventory()
        self._init()
        self._register_nos_plugins()

    def __enter__(self):
        """
        Method to start the SimNOS servers when entering the context manager.
        It is meant to be used with the `with` statement.
        """
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Method to stop the SimNOS servers when exiting the context manager.
        It is meant to be used with the `with` statement.

        If ``stop()`` itself raises, the traceback is logged via
        ``log.exception`` (so it is not lost) and the exception is re-raised
        to preserve normal context-manager semantics. This prevents
        silent failures during shutdown.
        """
        try:
            self.stop()
        except Exception:
            log.exception("stop() failed during SimNOS context manager __exit__")
            raise

    # ----------------------------------------------------------------------
    # sys_config (environment config) loading + precedence (#266 / D4)
    # ----------------------------------------------------------------------

    # Search order for sys_config.yaml when no dict/path is passed explicitly
    # (Decision 6). cwd before home: a project-local file beats the user default.
    _SYS_CONFIG_FILENAME = "sys_config.yaml"

    def _load_sys_config(self, sys_config: dict | str | None) -> None:
        """Resolve, validate and store the environment config (#266 / D4).

        Stores the resolved settings on ``self.sys_config`` (global). The
        precedence chain ``CLI > env > inventory(host > default) > sys_config >
        builtin`` (Decision 7) is realized as: sys_config seeds the inventory
        default (``_seed_inventory_default_from_sys_config``, so inventory wins),
        the ``SIMNOS_DATA_DIR`` env var overrides the file's ``data_dir`` here
        (env wins over file), and the CLI layer (#267) hooks in above env.
        """
        raw = self._discover_sys_config(sys_config)
        resolved = ModelSysConfig(**raw).model_dump()
        # env > sys_config file (Decision 7): SIMNOS_DATA_DIR overrides the file.
        env_data_dir = os.environ.get("SIMNOS_DATA_DIR")
        if env_data_dir:
            resolved["data_dir"] = env_data_dir
        self.sys_config: dict = resolved

    def _discover_sys_config(self, sys_config: dict | str | None) -> dict:
        """Find the sys_config source by the Decision 6 search order.

        ① explicit ``sys_config`` arg (dict used as-is, str read as a path) →
        ② env ``SIMNOS_SYS_CONFIG`` (path) → ③ ``./sys_config.yaml`` (cwd) →
        ④ ``~/.simnos/sys_config.yaml`` → ⑤ builtin default (empty). An explicit
        arg / env path that does not exist is a loud error (the caller asked for
        it); the implicit cwd/home probes are skipped when absent.
        """
        if isinstance(sys_config, dict):
            return sys_config
        if isinstance(sys_config, str):
            # Strip to stay symmetric with the env branch (#267, claude#3 3rd).
            return self._read_sys_config_file(Path(sys_config.strip()), required=True)
        if "SIMNOS_SYS_CONFIG" in os.environ:
            env_path = os.environ["SIMNOS_SYS_CONFIG"].strip()
            if not env_path:
                raise ValueError("SIMNOS_SYS_CONFIG is set but empty; unset it or provide a path")
            return self._read_sys_config_file(Path(env_path), required=True)
        for candidate in (Path.cwd() / self._SYS_CONFIG_FILENAME, Path.home() / ".simnos" / self._SYS_CONFIG_FILENAME):
            if candidate.is_file():
                return self._read_sys_config_file(candidate, required=False)
        return {}

    @staticmethod
    def _read_sys_config_file(path: Path, required: bool) -> dict:
        """Read and parse a sys_config YAML file into a dict.

        :param required: if True, a missing file raises (explicit arg/env asked
                         for this path); if False, the caller already confirmed
                         existence (implicit probe).
        """
        if not path.is_file():
            if required:
                raise FileNotFoundError(f"sys_config file not found: {path}")
            return {}
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f.read())
        if data is None:
            return {}
        if not isinstance(data, dict):
            raise TypeError(f"sys_config must be a mapping, got {type(data).__name__} in {path}")
        return data

    def _seed_inventory_default_from_sys_config(self, inventory_default: dict) -> dict:
        """Seed inventory-default with sys_config's per-host settings (#266 / D4).

        Realizes the ``inventory(default) > sys_config`` rung of the precedence
        chain (Decision 7) for the per-host ``variants_policy``: sys_config's
        global default sits *under* the inventory default (and per-host) so a more
        specific inventory value wins. ``data_dir`` is environment-global, not a
        per-host setting, so it stays on ``self.sys_config`` and is not seeded here.
        """
        seeded = dict(inventory_default)
        policy = self.sys_config.get("variants_policy")
        if policy is not None and "variants_policy" not in seeded:
            seeded["variants_policy"] = policy
        return seeded

    def _is_inventory_in_yaml(self) -> bool:
        """method that checks if the inventory is a yaml file."""
        return isinstance(self.inventory, str) and self.inventory.endswith((".yaml", ".yml"))

    def _load_inventory_yaml(self) -> None:
        """Helper method to load SimNOS inventory if it is yaml."""
        # narrow for ty; _is_inventory_in_yaml() guarantees self.inventory is a str.
        assert isinstance(self.inventory, str)  # noqa: S101 — caller-side invariant
        with open(self.inventory, encoding="utf-8") as f:
            self.inventory = yaml.safe_load(f.read())

    def _load_inventory(self) -> None:
        """Helper method to load SimNOS inventory"""
        if self._is_inventory_in_yaml():
            self._load_inventory_yaml()

        if isinstance(self.inventory, str):
            raise ValueError(f"Inventory file must end with .yaml or .yml, got '{self.inventory}'")
        if not isinstance(self.inventory, dict):
            raise TypeError(f"Inventory must be a dict or a path to a YAML file, got {type(self.inventory).__name__}")

        # Precedence (Decision 7, last-wins): builtin < sys_config < inventory
        # default < host. sys_config seeds the default below the inventory's own
        # default; the per-host `{**default, **host}` merge in `_init` then lets a
        # host override. The CLI layer (#267) hooks in above env, outside this merge.
        self.inventory["default"] = {
            **default_inventory["default"],
            # `default: null` validates as None (schema allows it); `or {}` keeps
            # the merge from a `dict(None)` crash with an opaque traceback (1st round claude#3).
            **self._seed_inventory_default_from_sys_config(self.inventory.get("default") or {}),
        }
        ModelSimnosInventory(**self.inventory)
        log.debug("SimNOS inventory validation succeeded")

    def _init(self) -> None:
        """
        Helper method to initiate host objects
        and store them in self.hosts, this
        method called automatically on SimNOS object instantiation.
        """
        # narrow for ty; _load_inventory() ran first and resolved/validated the
        # inventory to a dict (str paths loaded, non-dict raised), so it is a dict here.
        assert isinstance(self.inventory, dict)  # noqa: S101 — caller-side invariant
        for host_name, host_config in self.inventory["hosts"].items():
            params = {
                **copy.deepcopy(self.inventory["default"]),
                **copy.deepcopy(host_config),
            }
            # `params` is built from the raw inventory dict (Any-typed), but the
            # inventory was validated by `ModelSimnosInventory`, so port is int |
            # list[int] at runtime — ty cannot see that through the dict (ty 0.0.55).
            port: int | list[int] = params.pop("port")  # ty: ignore[invalid-assignment]
            replicas: int | None = params.pop("replicas", None)
            self._check_ports_and_replicas(port, replicas)
            self._instantiate_host_object(host_name, port, replicas, params)

    def _check_ports_and_replicas(self, port: int | list[int], replicas: int | None) -> None:
        """
        Method to check if the port and replicas are valid

        :param port: integer or list of two integers - port to allocate
        :param replicas: integer - number of hosts to create
        """
        # `is None` (not `not replicas`) so that replicas=0 is treated as "set
        # with invalid value" and reaches the `replicas < 1` check below. T-12
        # PR #211 recorded this as a known quirk; #220 promotes the check.
        # Guard cascade also lets ty narrow `port` to list[int] after the
        # initial isinstance check.
        if replicas is None:
            if isinstance(port, list):
                raise ValueError("If replicas is not set, port must be an integer.")
            return  # port is int, no further check needed
        if replicas < 1:
            raise ValueError("If replicas is set, replicas must be greater than 0.")
        if not isinstance(port, list):
            raise ValueError("If replicas is set, port must be a list of two integers.")
        if len(port) != 2:
            raise ValueError("If replicas is set, port must be a list of two integers.")
        if port[0] >= port[1]:
            raise ValueError("If replicas is set, port[0] must be less than port[1].")
        if port[1] - port[0] + 1 != replicas:
            raise ValueError("If replicas is set, port range must be equal to the number of replicas.")

    def _instantiate_host_object(
        self, host_name: str, port: int | list[int], replicas: int | None, params: dict
    ) -> None:
        """
        Method that instantiate the host objects. It initializes the hosts
        with the corresponding name, port and network operating system

        :param host_name: string - name of the host
        :param port: integer or list of two integers - port to allocate
        :param replicas: integer - number of hosts to create
        :param params: dictionary - parameters to pass to
                                    the host like configurations
        """
        hosts_name, ports = self._get_hosts_and_ports(host_name, port, replicas)
        for h_name, p in zip(hosts_name, ports, strict=True):
            self._instantiate_single_host_object(h_name, p, params)

    def _get_hosts_and_ports(
        self, host_name: str, port: int | list[int], replicas: int | None = None
    ) -> tuple[list[str], list[int]]:
        """
        Method to get hosts and ports correctly
        depending on the number of replicas (if exists).

        Pre-condition: ``_check_ports_and_replicas`` already validated that
        when ``replicas`` is truthy, ``port`` is a list[int] of length 2,
        and otherwise ``port`` is an int. The ``isinstance`` assertions
        below narrow ``port`` for ty without changing runtime behavior.

        :param host_name: string - name of the host
        :param port: integer or list of two integers - port to allocate
        :param replicas: integer - number of hosts to create
        """
        if replicas:
            assert isinstance(port, list)  # noqa: S101 — caller-side invariant from _check_ports_and_replicas
            hosts_name = [f"{host_name}{i}" for i in range(replicas)]
            ports = list(range(port[0], port[1] + 1))
        else:
            assert isinstance(port, int)  # noqa: S101 — caller-side invariant
            hosts_name = [host_name]
            ports = [port]
        return hosts_name, ports

    def _instantiate_single_host_object(self, host: str, port: int, params: dict) -> None:
        """
        Method that instantiates a single host object.

        :param host: name of the host
        :param port: port to allocate
        :param params: parameters to pass to the host like configurations
        """
        self._allocate_port(port)
        self.hosts[host] = Host(name=host, port=port, simnos=self, **params)

    def _allocate_port(self, port: int | list[int]) -> None:
        """
        Method to allocate port for host

        :param port: integer or list of two integers -
                     range to allocate port from
        """
        if isinstance(port, int):
            port: list[int] = [port]

        for p in port:
            self._allocate_port_single(p)

    def _allocate_port_single(self, port: int) -> None:
        """
        Method to allocate single port for host.

        :param port: integer - port to allocate
        """
        if port == EPHEMERAL_PORT:
            # OS assigns a unique real port at bind time (#271); skip the range
            # check, the dedup check, and `allocated_ports` registration. Several
            # hosts can all request port 0 (e.g. the default inventory) without
            # colliding here, and the real ports are read back after start.
            return
        if not (0 < port <= 65535):
            raise ValueError(f"Port {port} out of valid range (1-65535)")
        if port in self.allocated_ports:
            raise ValueError(f"Port {port} already in use")
        self.allocated_ports.add(port)

    def ensure_shared_loop(self) -> SharedLoop:
        """Start (lazily) and return the SimNOS-owned shared asyncio loop (§1).

        Called by async server plugins (``AsyncSshServer.start``) so the loop
        thread + bounded executor exist before a listener is registered. Idempotent
        while running; recreates the loop after a full stop (restart).
        """
        self._shared_loop.ensure_running()
        return self._shared_loop

    def _get_hosts_as_list(self, hosts: str | list[str] | None = None) -> list[Host]:
        """
        Helper method to get hosts as list

        :param hosts: string or list of strings
        :return: list of Host objects
        """
        if not hosts:
            hosts = list(self.hosts.keys())
        if isinstance(hosts, str):
            hosts = [hosts]
        return [self.hosts[host] for host in hosts]

    def start(
        self,
        hosts: str | list[str] | None = None,
        parallel: bool = False,
        workers: int | None = None,
    ) -> None:
        """
        Function to start NOS servers instances

        :param hosts: single or list of hosts to start by their name.
        :param parallel: if True, start hosts in parallel using threads.
        :param workers: max number of worker threads (default: min(32, host_count)).
        """
        hosts: list[Host] = self._get_hosts_as_list(hosts)
        self._execute_function_over_hosts(
            hosts,
            "start",
            host_running=False,
            parallel=parallel,
            workers=workers,
        )
        log.info(
            "The following devices have been initiated: %s",
            [host.name for host in hosts],
        )
        for host in hosts:
            log.info("Device %s is running on port %s", host.name, host.port)
            self._warn_security(host)

    def stop(
        self,
        hosts: str | list[str] | None = None,
        parallel: bool = False,
        workers: int | None = None,
    ) -> None:
        """
        Function to stop NOS servers instances and join managed threads.

        Uses a global deadline (SHUTDOWN_GLOBAL_DEADLINE seconds) to bound the
        total wall-clock time.  If the deadline is exceeded, remaining hosts
        may be left running and a warning is logged.

        :param hosts: single or list of hosts to stop by their name.
        :param parallel: if True, stop hosts in parallel using threads.
        :param workers: max number of worker threads (default: min(32, host_count)).
        """
        deadline = time.monotonic() + SHUTDOWN_GLOBAL_DEADLINE
        hosts: list[Host] = self._get_hosts_as_list(hosts)
        # Collect managed threads before stopping (Host.stop sets server to None)
        managed_threads = self._collect_server_threads(hosts)
        self._execute_function_over_hosts(
            hosts,
            "stop",
            host_running=True,
            parallel=parallel,
            workers=workers,
            deadline=deadline,
        )
        if managed_threads:
            remaining = max(0, deadline - time.monotonic())
            self._join_threads(managed_threads, timeout=min(SHUTDOWN_SAFETY_NET_DEADLINE, remaining))
        # Tear the shared loop down once no async host remains registered (§1a 5b):
        # global teardown is SimNOS's job (the loop thread is joined here once, not
        # per host). A partial stop that leaves async hosts running is a no-op here
        # (refcount > 0), so the loop keeps serving them.
        self._shared_loop.teardown_if_idle(deadline)

    def _collect_server_threads(self, hosts: list[Host]) -> list[threading.Thread]:
        """Collect all managed threads from host servers before stopping."""
        threads: list[threading.Thread] = []
        for host in hosts:
            if host.server is not None:
                threads.extend(host.server.managed_threads)
        return threads

    def _join_threads(
        self,
        threads: list[threading.Thread],
        timeout: float | None = None,
    ) -> None:
        """
        Join SimNOS-managed threads after all hosts are stopped.

        The async server plugins own no per-connection threads (``managed_threads``
        is empty — sessions live on the SimNOS shared loop, torn down by
        ``teardown_if_idle``), so this is a safety net for any stragglers.
        """
        total = timeout if timeout is not None else SHUTDOWN_SAFETY_NET_DEADLINE
        alive = join_threads_with_deadline(threads, total, SHUTDOWN_SAFETY_NET_PER_THREAD)
        if alive:
            log.warning("%d SimNOS thread(s) did not exit within timeout", len(alive))

    def _execute_function_over_hosts(
        self,
        hosts: list[Host],
        func: str,
        host_running: bool = True,
        parallel: bool = False,
        workers: int | None = None,
        deadline: float | None = None,
    ) -> None:
        """
        Function that executes a function like start or stop over
        the selected hosts.

        :param hosts: list of Hosts objects in which the function will
        be executed.
        :param parallel: if True, execute in parallel using threads.
        :param workers: max number of worker threads.
        :param deadline: optional monotonic deadline; skip remaining hosts if exceeded.
        """
        for host in hosts:
            if host not in self.hosts.values():
                raise ValueError(f"Host {host} not found")
        targets = [h for h in hosts if h.running == host_running]
        if not parallel or len(targets) <= 1:
            for i, h in enumerate(targets):
                if deadline is not None and time.monotonic() >= deadline:
                    log.warning("Global stop deadline exceeded, %d host(s) not stopped", len(targets) - i)
                    break
                getattr(h, func)()
            return
        if workers is not None and workers < 1:
            raise ValueError(f"workers must be >= 1, got {workers}")
        max_workers = workers or min(32, len(targets))
        remaining = max(0, deadline - time.monotonic()) if deadline is not None else None
        ex = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        futures = [ex.submit(getattr(h, func)) for h in targets]
        timed_out = False
        try:
            for f in concurrent.futures.as_completed(futures, timeout=remaining):
                f.result()
        except TimeoutError:
            timed_out = True
            log.warning("Global stop deadline exceeded during parallel %s", func)
        finally:
            if timed_out:
                ex.shutdown(wait=False, cancel_futures=True)
            else:
                ex.shutdown(wait=True)

    @staticmethod
    def _warn_security(host: Host) -> None:
        """Emit warnings for common security misconfigurations."""
        if host.username == "user" and host.password == "user":  # noqa: S105
            log.warning(
                "Device %s uses default credentials (user/user). "
                "Change username/password in the inventory for non-local use.",
                host.name,
            )
        address = host.server_inventory.get("configuration", {}).get("address", "")
        if address == "0.0.0.0":  # noqa: S104
            log.warning(
                "Device %s binds to 0.0.0.0 (all interfaces). Use 127.0.0.1 to restrict access to localhost only.",
                host.name,
            )

    def _register_nos_plugins(self) -> None:
        """
        Method to register NOS plugins with SimNOS object, all plugins
        must be registered before calling start method.

        A plugin is a ready `Nos` instance or a str path to an A3 platform dir
        (``platform.yaml`` + ``commands/``). The dict form and a bare ``.py``
        path were removed with the legacy py-dict authoring (#317 P-4) — a py
        module alone cannot author commands; hand a handler module to `Nos`
        yourself (``Nos(filename=[a3_dir, handler_py])``) and register the
        instance.
        """
        for plugin in self.plugins:
            if isinstance(plugin, Nos):
                nos_instance = plugin
            elif isinstance(plugin, str):
                if not os.path.isdir(plugin):
                    raise ValueError(
                        f"NOS plugin path {plugin!r} is not an A3 platform dir — a str plugin must point at a "
                        "directory holding platform.yaml + commands/ (py-only / dict plugins were removed, #317 P-4)"
                    )
                nos_instance = Nos(filename=plugin)
            else:
                raise TypeError(f"Unsupported NOS type {type(plugin)}, supported str (A3 platform dir) or Nos")
            self.nos_plugins[nos_instance.name] = nos_instance


def simnos(device_type: str | None = None, inventory: dict | str | None = None, return_instance: bool = False):
    """
    Decorator to run a test with SimNOS server.
    """
    if device_type and inventory:
        raise ValueError("device_type and inventory cannot be used together")
    if not device_type and not inventory:
        raise ValueError("device_type or inventory must be set")
    if device_type:
        assert_platform_supported(device_type)
        inventory = {
            "hosts": {
                "SimNOS": {
                    "username": "test",
                    "password": "test",
                    "port": EPHEMERAL_PORT,  # OS-assigned (#271); read back via net.hosts["SimNOS"].port
                    "device_type": device_type,
                }
            }
        }

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with SimNOS(inventory=inventory) as net:
                if return_instance:
                    return func(*args, net=net, **kwargs)
                return func(*args, **kwargs)

        # Remove __wrapped__ so that pytest does not introspect the
        # original signature and try to inject 'net' as a fixture.
        del wrapper.__wrapped__
        return wrapper

    return decorator
