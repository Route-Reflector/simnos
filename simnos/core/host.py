"""
This module sets up the host object which is the main object in SIMNOS.
It provides the methods to start and stop the server instance for the host.
It also validates the host object using pydantic.
"""

import logging
from typing import TYPE_CHECKING

from simnos.core.nos import Nos
from simnos.core.pydantic_models import ModelHost
from simnos.plugins.nos import assert_platform_supported, resolve_device_type

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
        device_type: str | None = None,
        configuration_file: str | None = None,
        facts: dict | None = None,
        overlay: dict | None = None,
        variants_policy: dict | None = None,
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
        self.device_type: str | None = device_type
        self.configuration_file: str | None = configuration_file
        # #265 reservation (#266 / D1, Decision 5): stored but consumed by nobody
        # in #266. Kept as attributes so #265 can wire them up without touching
        # the Host signature again.
        self.facts: dict | None = facts
        self.overlay: dict | None = overlay
        self.variants_policy: dict | None = variants_policy
        self._warn_reserved_fields()

        if self.device_type:
            self.nos_inventory["plugin"] = self.device_type

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
        # device_type -> platform (registry key) resolution chokepoint (#266 / D2,
        # Decision 8): all three plugin-key paths converge here — an explicit
        # `device_type` (assigned in __init__), the `nos.plugin` default, and a
        # direct `nos: {plugin: ...}`. `resolve_device_type` maps netmiko/ntc
        # aliases (and identity names) to the registry key; an unknown value
        # (e.g. a runtime-registered custom plugin) falls through unchanged.
        plugin_key = resolve_device_type(self.nos_inventory["plugin"]) or self.nos_inventory["plugin"]
        self.nos_plugin = self.simnos.nos_plugins.get(plugin_key, plugin_key)
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
            log.debug("Host %s has no running server; stop() is a no-op", self.name)
            return
        self.server.stop()
        self.server = None
        self.running = False

    def _warn_reserved_fields(self) -> None:
        """Warn loudly for #265 reserved fields that are set but inert in #266.

        `facts` / `overlay` / `variants_policy` are accepted and validated by the
        inventory schema (the "器") but consumed by neither the loader nor the
        shell until #265 wires them up. A `log.warning` here keeps a set-but-inert
        config visible instead of a silent no-op (#266 / Decision 5, anti-silent-bug).
        The value may come from the host, the inventory default, or a sys_config
        seed (`variants_policy`), so the message stays provenance-neutral.
        """
        for field in ("facts", "overlay", "variants_policy"):
            if getattr(self, field) is not None:
                log.warning(
                    "Host %s has reserved field %r set, which has no effect yet (activated in #265, currently no-op).",
                    self.name,
                    field,
                )

    def _validate(self):
        """Validate that the host has the required attributes using pydantic"""
        if self.device_type:
            self._check_if_platform_is_supported(self.device_type)
        ModelHost(**self.__dict__)

    def _check_if_platform_is_supported(self, device_type: str):
        """Check that `device_type` resolves to a supported platform.

        Thin wrapper around the registry-level helper; kept as a method
        because tests patch / call it as the Host-level seam (#237). The
        argument is the inventory `device_type` (#266); `assert_platform_supported`
        accepts both internal platform names and netmiko/ntc aliases.
        """
        assert_platform_supported(device_type)
