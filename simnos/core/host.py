"""
This module sets up the host object which is the main object in SIMNOS.
It provides the methods to start and stop the server instance for the host.
It also validates the host object using pydantic.
"""

import logging
from typing import TYPE_CHECKING

from simnos.core.nos import Nos
from simnos.core.pydantic_models import ModelHost
from simnos.plugins.nos import assert_platform_supported

if TYPE_CHECKING:
    from simnos.core.simnos import SimNOS

log = logging.getLogger(__name__)


class Host:
    """
    Host class to build host instances to use with SIMNOS.
    """

    def __init__(
        self,
        name: str,
        username: str,
        password: str,
        port: int,
        server: dict,
        shell: dict,
        nos: dict,
        simnos: "SimNOS",
        platform: str | None = None,
        configuration_file: str | None = None,
    ) -> None:
        self.name: str = name
        self.server_inventory: dict = server
        self.shell_inventory: dict = shell
        self.nos_inventory: dict = nos
        self.username: str = username
        self.password: str = password
        self.port: int = port
        self.simnos = simnos  # SimNOS object
        self.shell_inventory["configuration"].setdefault("base_prompt", self.name)
        self.running = False
        self.server = None
        self.server_plugin = None
        self.shell_plugin = None
        self.nos_plugin = None
        self.nos = None
        self.platform: str | None = platform
        self.configuration_file: str | None = configuration_file

        if self.platform:
            self.nos_inventory["plugin"] = self.platform

        self._validate()

    def start(self):
        """Method to start server instance for this host.

        No-op if the server is already running (``self.running``),
        symmetric with the double-stop guard in ``stop()``. This protects
        direct ``host.start()`` callers from spawning a duplicate server
        instance (and orphaning the first one); the SimNOS-level
        orchestration already filters on ``host_running=False`` and never
        double-starts.
        """
        if self.running:
            log.debug("Host %s is already running; start() is a no-op", self.name)
            return
        self.server_plugin = self.simnos.servers_plugins[self.server_inventory["plugin"]]
        self.shell_plugin = self.simnos.shell_plugins[self.shell_inventory["plugin"]]
        self.nos_plugin = self.simnos.nos_plugins.get(self.nos_inventory["plugin"], self.nos_inventory["plugin"])
        self.nos = (
            Nos(filename=self.nos_plugin, configuration_file=self.configuration_file)
            if not isinstance(self.nos_plugin, Nos)
            else self.nos_plugin
        )
        self.server = self.server_plugin(
            shell=self.shell_plugin,
            shell_configuration=self.shell_inventory["configuration"],
            nos=self.nos,
            nos_inventory_config=self.nos_inventory.get("configuration", {}),
            port=self.port,
            username=self.username,
            password=self.password,
            **self.server_inventory["configuration"],
        )
        self.server.start()
        self.running = True

    def stop(self):
        """Method to stop server instance for this host.

        No-op if the server was never started or has already been stopped
        (``self.server is None``); this guards against double-stop calls.
        """
        if self.server is None:
            return
        self.server.stop()
        self.server = None
        self.running = False

    def _validate(self):
        """Validate that the host has the required attributes using pydantic"""
        if self.platform:
            self._check_if_platform_is_supported(self.platform)
        ModelHost(**self.__dict__)

    def _check_if_platform_is_supported(self, platform: str):
        """Check if the platform is supported.

        Thin wrapper around the registry-level helper; kept as a method
        because tests patch / call it as the Host-level seam (#237).
        """
        assert_platform_supported(platform)
