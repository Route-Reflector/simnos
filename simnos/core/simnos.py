"""
Main module to interact with SimNOS servers.
It is the entry point to start, stop and list SimNOS servers.
"""

import concurrent.futures
import copy
import logging
import platform
import socket
import threading

import detect
import yaml

from simnos.core.host import Host
from simnos.core.nos import Nos
from simnos.core.pydantic_models import ModelSimnosInventory
from simnos.plugins.nos import nos_plugins
from simnos.plugins.servers import servers_plugins
from simnos.plugins.shell import shell_plugins

log = logging.getLogger(__name__)

default_inventory = {
    "default": {
        "username": "user",
        "password": "user",
        "port": 6000,
        "server": {
            "plugin": "ParamikoSshServer",
            "configuration": {
                "address": "127.0.0.1",
                "timeout": 1,
            },
        },
        "shell": {"plugin": "CMDShell", "configuration": {}},
        "nos": {"plugin": "cisco_ios", "configuration": {}},
    },
    "hosts": {
        "router_cisco_ios": {"port": 6000, "platform": "cisco_ios"},
        "router_huawei_smartax": {"port": 6001, "platform": "huawei_smartax"},
        "router_arista_eos": {"port": 6002, "platform": "arista_eos"},
    },
}

# If Windows or WSL, the configuration address is 0.0.0.0
# WSL Bug: https://github.com/microsoft/WSL/issues/4983
if detect.docker and "WSL2" in platform.release():
    server_config = default_inventory["default"]["server"]["configuration"]
    server_config["address"] = "0.0.0.0"  # noqa: S104


class SimNOS:
    """
    SimNOS class is a main entry point to interact
    with fake NOS servers - start, stop, list.

    :param inventory: SimNOS inventory dictionary or
                      OS path to .yaml file with inventory data
    :param plugins: Plugins to add extra devices/commands
                    currently not supported easily.

    Sample usage:

    ```python
    from simnos import SimNOS

    net = SimNOS()
    net.start()
    ```
    """

    def __init__(
        self,
        inventory: dict | None = None,
        plugins: list | None = None,
    ) -> None:
        self.inventory: dict = inventory or default_inventory
        self.plugins: list = plugins or []

        self.hosts: dict[str, Host] = {}
        self.allocated_ports: set[int] = set()

        self.shell_plugins = shell_plugins
        self.nos_plugins = nos_plugins
        self.servers_plugins = servers_plugins

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

    def __exit__(self, *args):
        """
        Method to stop the SimNOS servers when exiting the context manager.
        It is meant to be used with the `with` statement.
        """
        self.stop()

    def _is_inventory_in_yaml(self) -> bool:
        """method that checks if the inventory is a yaml file."""
        return isinstance(self.inventory, str) and self.inventory.endswith((".yaml", ".yml"))

    def _load_inventory_yaml(self) -> None:
        """Helper method to load SimNOS inventory if it is yaml."""
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

        self.inventory["default"] = {
            **default_inventory["default"],
            **self.inventory.get("default", {}),
        }
        ModelSimnosInventory(**self.inventory)
        log.debug("SimNOS inventory validation succeeded")

    def _init(self) -> None:
        """
        Helper method to initiate host objects
        and store them in self.hosts, this
        method called automatically on SimNOS object instantiation.
        """
        for host_name, host_config in self.inventory["hosts"].items():
            params = {
                **copy.deepcopy(self.inventory["default"]),
                **copy.deepcopy(host_config),
            }
            port: int | list = params.pop("port")
            replicas: int = params.pop("replicas", None)
            self._check_ports_and_replicas_are_okey(port, replicas)
            self._instantiate_host_object(host_name, port, replicas, params)

    def _check_ports_and_replicas_are_okey(self, port, replicas):
        """
        Method to check if the port and replicas are okey

        :param port: integer or list of two integers - port to allocate
        :param replicas: integer - number of hosts to create
        """
        if not replicas and isinstance(port, list):
            raise ValueError("If replicas is not set, port must be an integer.")
        if replicas and not isinstance(port, list):
            raise ValueError("If replicas is set, port must be a list of two integers.")
        if replicas and len(port) != 2:
            raise ValueError("If replicas is set, port must be a list of two integers.")
        if replicas and port[0] >= port[1]:
            raise ValueError("If replicas is set, port[0] must be less than port[1].")
        if replicas and replicas < 1:
            raise ValueError("If replicas is set, replicas must be greater than 0.")
        if replicas and port[1] - port[0] + 1 != replicas:
            raise ValueError(
                "If replicas is set, port range \
                    must be equal to the number of replicas."
            )

    def _instantiate_host_object(self, host_name: str, port: int | list[int], replicas: int, params: dict):
        """
        Method that instantiate the host objects. It initializes the hosts
        with the corresponding name, port and network operating system

        :param host: string - name of the host
        :param port: integer or list of two integers - port to allocate
        :param count: integer - number of hosts to create
        :param params: dictionary - parameters to pass to
                                    the host like configurations
        """
        hosts_name, ports = self._get_hosts_and_ports(host_name, port, replicas)
        for h_name, p in zip(hosts_name, ports, strict=True):
            self._instantiate_single_host_object(h_name, p, params)

    def _get_hosts_and_ports(self, host_name: str, port: int | list[int], replicas: int | None = None):
        """
        Method to get hosts and ports correctly
        depending on the number of replicas (if exists).

        :param host_name: string - name of the host
        :param port: integer or list of two integers - port to allocate
        :param replicas: integer - number of hosts to create
        """
        if replicas:
            hosts_name = [f"{host_name}{i}" for i in range(replicas)]
            ports = list(range(port[0], port[1] + 1))
        else:
            hosts_name = [host_name]
            ports = [port]
        return hosts_name, ports

    def _instantiate_single_host_object(self, host, port, params):
        """
        Method that instantiate the host objects. It initializes the hosts

        :param host: string - name of the host
        :param port: integer or list of two integers - port to allocate
        :param params: dictionary - parameters to pass to
                                    the host like configurations
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
            allocated_port = self._allocate_port_single(p)
            self.allocated_ports.add(allocated_port)

    def _allocate_port_single(self, port: int) -> int:
        """
        Method to allocate single port for host.

        :param port: integer - port to allocate
        """
        if port in self.allocated_ports:
            raise ValueError(f"Port {port} already in use")
        self.allocated_ports.add(port)
        return port

    def _get_hosts_as_list(self, hosts: str | list[str] | None = None) -> list[Host]:
        """
        Helper method to get hosts as list

        :param hosts: string or list of strings
        :return: list of strings
        """
        if not hosts:
            hosts = list(self.hosts.keys())
        if isinstance(hosts, str):
            hosts = [hosts]
        return [self.hosts[host] for host in hosts]

    def start(
        self,
        hosts: str | list | None = None,
        parallel: bool = False,
        workers: int | None = None,
    ) -> None:  # type: ignore
        """
        Function to start NOS servers instances

        :param hosts: single or list of hosts to start by their name.
        :param parallel: if True, start hosts in parallel using threads.
        :param workers: max number of worker threads (default: min(32, host_count)).
        """
        hosts: list[str] = self._get_hosts_as_list(hosts)
        self._execute_function_over_hosts(
            hosts,
            "start",
            host_running=False,
            parallel=parallel,
            workers=workers,
        )
        log.info(
            "The following devices has been initiated: %s",
            [host.name for host in hosts],
        )
        for host in hosts:
            log.info("Device %s is running on port %s", host.name, host.port)

    def stop(
        self,
        hosts: str | list[str] | None = None,
        parallel: bool = False,
        workers: int | None = None,
    ) -> None:
        """
        Function to stop NOS servers instances and join managed threads.

        :param hosts: single or list of hosts to stop by their name.
        :param parallel: if True, stop hosts in parallel using threads.
        :param workers: max number of worker threads (default: min(32, host_count)).
        """
        hosts: list[str] = self._get_hosts_as_list(hosts)
        # Collect managed threads before stopping (Host.stop sets server to None)
        managed_threads = self._collect_server_threads(hosts)
        self._execute_function_over_hosts(
            hosts,
            "stop",
            host_running=True,
            parallel=parallel,
            workers=workers,
        )
        if managed_threads:
            self._join_threads(managed_threads)

    def _collect_server_threads(self, hosts: list[Host]) -> list[threading.Thread]:
        """Collect all managed threads from host servers before stopping."""
        threads: list[threading.Thread] = []
        for host in hosts:
            if host.server is not None:
                threads.extend(host.server.managed_threads)
        return threads

    def _join_threads(self, threads: list[threading.Thread]) -> None:
        """
        Join SimNOS-managed threads after all hosts are stopped.
        Server threads are already joined by TCPServerBase.stop();
        this is a safety net for any stragglers.
        """
        for thread in threads:
            thread.join(timeout=5)
        alive = [t for t in threads if t.is_alive()]
        if alive:
            log.warning("%d SimNOS thread(s) did not exit within timeout", len(alive))

    def _execute_function_over_hosts(
        self,
        hosts: list[Host],
        func: str,
        host_running: bool = True,
        parallel: bool = False,
        workers: int | None = None,
    ):
        """
        Function that executes a function like start or stop over
        the selected hosts.

        :param hosts: list of Hosts objects in which the function will
        be executed.
        :param parallel: if True, execute in parallel using threads.
        :param workers: max number of worker threads.
        """
        for host in hosts:
            if host not in self.hosts.values():
                raise ValueError(f"Host {host} not found")
        targets = [h for h in hosts if h.running == host_running]
        if not parallel or len(targets) <= 1:
            for h in targets:
                getattr(h, func)()
            return
        if workers is not None and workers < 1:
            raise ValueError(f"workers must be >= 1, got {workers}")
        max_workers = workers or min(32, len(targets))
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = [ex.submit(getattr(h, func)) for h in targets]
            for f in futures:
                f.result()

    def _register_nos_plugins(self) -> None:
        """
        Method to register NOS plugin with SimNOS object, all plugins
        must be registered before calling start method.

        :param plugin: OS path string to NOS plugin `.yaml/.yml` or `.py` file,
          dictionary or instance if Nos class
        """
        for plugin in self.plugins:
            if isinstance(plugin, Nos):
                nos_instance = plugin
            else:
                nos_instance = Nos()
                if isinstance(plugin, dict):
                    nos_instance.from_dict(plugin)
                elif isinstance(plugin, str):
                    nos_instance.from_file(plugin)
                else:
                    raise TypeError(f"Unsupported NOS type {type(plugin)}, supported str, dict or Nos")
            self.nos_plugins[nos_instance.name] = nos_instance


def _get_free_port() -> int:
    """
    Method to get a free port for the SimNOS server.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def simnos(platform: str | None = None, inventory: dict | None = None, return_instance: bool = False):
    """
    Decorator to run a test with SimNOS server.
    """
    if platform and inventory:
        raise ValueError("platform and inventory cannot be used together")
    if not platform and not inventory:
        raise ValueError("platform or inventory must be set")
    if platform:
        inventory = {
            "hosts": {
                "SimNOS": {
                    "username": "test",
                    "password": "test",
                    "port": _get_free_port(),
                    "platform": platform,
                }
            }
        }

    def decorator(func):
        def wrapper(*args, **kwargs):
            with SimNOS(inventory=inventory) as net:
                if return_instance:
                    return func(*args, net=net, **kwargs)
                return func(*args, **kwargs)

        return wrapper

    return decorator
