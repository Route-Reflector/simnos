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
from simnos.core.pydantic_models import ModelHost, ModelVariantsPolicy
from simnos.plugins.nos import assert_platform_supported, resolve_device_type

if TYPE_CHECKING:
    from simnos.core.simnos import SimNOS

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class HostRenderConfig:
    """Per-host render config the server carries from Host to the shell (#286 / C1).

    A single carrier so the wiring (Host -> server -> ``build_shared_platform`` ->
    ``build_resolved_platform`` -> shell) is threaded once. #286 fills ``overlay_*``;
    #287 adds ``variants_policy`` / ``host_name`` here without touching the
    signature again (a future Layer-2 ``facts`` field will slot in the same way).
    The ``overlay_*`` fields are ``None`` when the host has not opted into the
    overlay, in which case the merge skips the overlay layer entirely.

    ``variants_policy`` is the typed per-host variant-selection policy (#287 / D6);
    ``host_name`` is the stable inventory host id (``Host.name``) used as the
    seeded-hash host term — not ``base_prompt``, which the shell config can
    override and several hosts can share (#287 / D6 E).
    """

    overlay_root: str | None = None
    override_commands: str | list[str] | dict[str, str] | None = None
    variants_policy: "ModelVariantsPolicy | None" = None
    host_name: str | None = None


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
        # Inventory render config. `overlay` is consumed by #286 and
        # `variants_policy` by #287 (Host.start resolves them and threads them to
        # the shell via HostRenderConfig); `facts` stays a reservation (stored but
        # inert, warned below) for the Layer-2 follow-up issue, so it can be wired
        # later without touching the Host signature again.
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
        # Parse the per-host variant policy to its typed model at the carrier
        # boundary so the shell only ever sees `ModelVariantsPolicy`, never a raw
        # dict (#287 / D6 K — typed-model-first). The inventory schema already
        # validated this value (precedence-merged whole, D8), so re-parsing only
        # materializes the typed object + defaults (select=0).
        variants_policy = ModelVariantsPolicy(**self.variants_policy) if self.variants_policy else None
        render_config = HostRenderConfig(
            overlay_root=self._resolve_overlay_root(plugin_key),
            override_commands=(self.overlay or {}).get("override_commands"),
            variants_policy=variants_policy,
            host_name=self.name,
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
            # AsyncSshServer (#297 Stage 2) reaches the SimNOS-owned shared loop
            # through this back reference; the sync paramiko/telnet plugins accept
            # and ignore it for a uniform construction call.
            simnos=self.simnos,
            **self.server_inventory["configuration"],
        )
        # Defense-in-depth for a partial start (#291). A host whose `start()`
        # raised keeps `running == False`, so `SimNOS.stop()` (filters on
        # `running == True`) never stops it, yet `SimNOS._collect_server_threads()`
        # still collects its threads (it gates on `server is not None`) — a
        # dangling server here makes the shutdown join block. Stop the just-built
        # server and drop the reference + reset `running` before re-raising.
        #
        # The catch is `BaseException`, not `Exception`: the most likely
        # partial-start trigger is a `KeyboardInterrupt` (the operator aborts
        # startup), which `except Exception` would miss. `self.running = True`
        # lives INSIDE the try so an interrupt in the gap after a successful
        # `server.start()` is still rolled back rather than leaving the dangling
        # state. Cleanup is best-effort: a failure is logged (not raised) so it
        # cannot mask the original error, and the reference/flag reset regardless.
        try:
            self.server.start()
            self.running = True
        except BaseException:
            try:
                self.server.stop()
            except Exception:
                log.exception("Host %s: cleanup after a failed start() raised", self.name)
            finally:
                self.server = None
                self.running = False
            raise

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

        The state reset runs in a ``finally`` so the host does not dangle if
        ``server.stop()`` is cut short by an interrupt — the server self-cleans
        in its own ``finally``, so dropping the reference + clearing ``running``
        keeps the host out of ``SimNOS._collect_server_threads()`` (#291,
        symmetric with the rollback in ``start()``).
        """
        if self.server is None:
            log.debug("Host %s has no running server; stop() is a no-op", self.name)
            return
        try:
            self.server.stop()
        finally:
            self.server = None
            self.running = False

    def _warn_reserved_fields(self) -> None:
        """Warn loudly for reserved fields that are set but inert.

        `facts` is accepted + validated by the inventory schema (the "器") but is
        deferred to the Layer-2 follow-up issue (global facts / cross-command
        coherence); #287 wires only per-host `variants_policy`, so `facts` stays a
        set-but-inert no-op and is warned here to keep it visible instead of
        silent (#266 / Decision 5, anti-silent-bug). `overlay` is consumed by #286
        (Host.start); its `random_commands` sub-field is a *future* per-command
        variant-policy vessel that #287 does not wire, so a set-but-inert
        `random_commands` is warned on its own (#287 / D8 C, anti-silent-bug).

        `variants_policy` is consumed by #287 (Host.start threads it through
        `HostRenderConfig` to the shell), so it is not a reservation — but a
        ``seed`` set while ``select`` is not ``"random"`` is inert (seed only
        matters for random selection), so that misconfiguration is warned on its
        own to keep it from being a silent no-op (1st round claude#3).
        """
        if self.facts is not None:
            log.warning(
                "Host %s has reserved field 'facts' set, which has no effect yet "
                "(activated in the Layer-2 follow-up issue, currently no-op).",
                self.name,
            )
        if (self.overlay or {}).get("random_commands"):
            log.warning(
                "Host %s has overlay.random_commands set, which has no effect yet "
                "(reserved for a future per-command variant policy, currently no-op).",
                self.name,
            )
        variants_policy = self.variants_policy or {}
        if variants_policy.get("seed") is not None and variants_policy.get("select") != "random":
            log.warning(
                "Host %s sets variants_policy.seed but select is %r (not 'random'); the seed is ignored "
                "(it only affects random selection).",
                self.name,
                variants_policy.get("select"),
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
