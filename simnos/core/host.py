"""
This module sets up the host object which is the main object in SIMNOS.
It provides the methods to start and stop the server instance for the host.
It also validates the host object using pydantic.
"""

from dataclasses import dataclass
import logging
import os
from typing import TYPE_CHECKING

from simnos.core.nos import Nos
from simnos.core.pydantic_models import ModelHost
from simnos.plugins.nos import assert_platform_supported, resolve_device_type

if TYPE_CHECKING:
    from simnos.core.simnos import SimNOS

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class HostRenderConfig:
    """Per-host render config the server carries from Host to the shell (#286 / C1).

    A single carrier so the wiring (Host -> server -> ``build_shared_platform`` ->
    ``build_resolved_platform`` -> shell) is threaded once. #286 fills ``overlay_*``;
    #287 adds ``facts`` / random fields here without touching the signature again.
    Both are ``None`` when the host has not opted into the overlay, in which case
    the merge skips the overlay layer entirely (no behaviour change).
    """

    overlay_root: str | None = None
    override_commands: str | list[str] | dict[str, str] | None = None


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
        # Inventory render config. `overlay` is consumed by #286 (Host.start
        # resolves the overlay dir and threads it to the shell via
        # HostRenderConfig); `facts` / `variants_policy` are still #287 reservations
        # (stored but inert, warned below) so #287 can wire them without touching
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
        render_config = HostRenderConfig(
            overlay_root=self._resolve_overlay_root(plugin_key),
            override_commands=(self.overlay or {}).get("override_commands"),
        )
        self.server = self.server_plugin(
            shell=self.shell_plugin,
            shell_configuration=self.shell_inventory["configuration"],
            nos=self.nos,
            nos_inventory_config=self.nos_inventory.get("configuration", {}),
            port=self.port,
            username=self.username,
            password=self.password,
            render_config=render_config,
            **self.server_inventory["configuration"],
        )
        self.server.start()
        self.running = True

    def _resolve_overlay_root(self, plugin_key: str) -> str | None:
        """Resolve this host's overlay dir, or None when overlay is not opted in (#286).

        The opt-in is the inventory ``overlay.override_commands`` (empty/unset =
        no overlay -> None, the merge skips the overlay layer). When set, the data
        must be reachable: ``sys_config.data_dir`` must be configured and
        ``<data_dir>/<plugin_key>/`` must exist. An explicit opt-in that cannot be
        satisfied is a loud error, never a silent fall-back to packaged output
        (design Decision 10a) — including opting in on a legacy / py-only platform,
        whose merge path drops the overlay layer (`build_resolved_platform`), so a
        non-A3 platform with overlay set must fail here rather than silently serve
        the packaged output (Decision 12, J4). ``plugin_key`` is the registry key
        (already passed through ``resolve_device_type`` in ``start()``), not the raw
        inventory ``device_type`` — aliasing platforms and the ``nos.plugin`` path
        would otherwise point the dir at the wrong (or no) name (Decision 3).
        """
        override_commands = (self.overlay or {}).get("override_commands")
        if not override_commands:
            return None
        # `self.nos` is built just above in `start()` before this is called; the
        # None guard lets direct unit calls (no start) keep testing the dir logic.
        # The A3-only rationale lives in the docstring above.
        if self.nos is not None and self.nos.resolved_platform is None:
            raise ValueError(
                f"Host {self.name}: overlay.override_commands is set but platform {plugin_key!r} is "
                "legacy / py-only (no A3 command data); overlays apply to A3 platforms only."
            )
        data_dir = self.simnos.sys_config.get("data_dir")
        if not data_dir:
            raise ValueError(
                f"Host {self.name}: overlay.override_commands is set but sys_config.data_dir is not "
                "configured; cannot locate the overlay directory."
            )
        root = os.path.join(data_dir, plugin_key)
        if not os.path.isdir(root):
            raise ValueError(
                f"Host {self.name}: overlay directory {root!r} does not exist "
                f"(data_dir={data_dir!r}, platform={plugin_key!r})."
            )
        return root

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
        """Warn loudly for #287 reserved fields that are set but inert.

        `facts` / `variants_policy` are accepted and validated by the inventory
        schema (the "器") but consumed by neither the loader nor the shell until
        #287 wires them up. A `log.warning` here keeps a set-but-inert config
        visible instead of a silent no-op (#266 / Decision 5, anti-silent-bug).
        The value may come from the host, the inventory default, or a sys_config
        seed (`variants_policy`), so the message stays provenance-neutral. `overlay`
        is consumed by #286 (Host.start) so it is not a whole-field reservation —
        but its `random_commands` sub-field is the #287 vessel and stays inert, so
        a set-but-inert `random_commands` is warned on its own (#287, anti-silent-bug).
        """
        for field in ("facts", "variants_policy"):
            if getattr(self, field) is not None:
                log.warning(
                    "Host %s has reserved field %r set, which has no effect yet (activated in #287, currently no-op).",
                    self.name,
                    field,
                )
        if (self.overlay or {}).get("random_commands"):
            log.warning(
                "Host %s has overlay.random_commands set, which has no effect yet "
                "(activated in #287, currently no-op).",
                self.name,
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
