"""
Custom shell class to interact with NOS.
"""

from cmd import Cmd
import copy
import logging
import os
import traceback
from typing import cast

from simnos.core.command_adapter import adapt_commands, adapt_legacy_commands, reverse_map_from_modes
from simnos.core.command_contract import CommandHandler, CommandResult
from simnos.core.nos import Nos
from simnos.core.platform_loader import load_platform_dir
from simnos.core.resolved_command import ResolvedCommand, ResolvedPlatform
from simnos.plugins import nos
from simnos.plugins.shell.utils import get_files_changed

log = logging.getLogger(__name__)

# Special, always-present commands fed through the same legacy adapter as the
# NOS data (#264 / D5). They carry no `prompt`, so the adapter resolves them to
# an empty mode set = valid in every mode.
BASIC_COMMANDS: dict = {
    "exit": {"exit": True, "help": "Exit commands shell"},
    "_default_": {
        "output": "Unknown command",
        "help": "Output to print for unknown commands",
    },
}

# Wire response when a command handler (callable output) crashes. Real NOSes
# never print Python tracebacks, and clients (Netmiko/KeroRoute integration
# tests) must not be handed one to parse — the full traceback goes to the
# server log instead (#241 / D4).
HANDLER_ERROR_OUTPUT = "% Internal error"


def build_resolved_platform(nos: "Nos", inventory_commands: dict) -> ResolvedPlatform:
    """Merge the command inflows into one `ResolvedPlatform` (#264 / D6).

    The shell consumes one representation regardless of authoring form. Inflows
    merge under one precedence — BASIC < NOS < inventory, later inflows winning:

    - **legacy NOS** (`nos.resolved_platform is None`): the merged dict (BASIC +
      NOS commands + inventory, all legacy form) goes through the legacy adapter,
      which synthesizes the modes from the 3 scalar prompts.
    - **A3 NOS** (`nos.resolved_platform` set): modes come from the A3 platform;
      its resolved static commands sit between the still-legacy BASIC (below) and
      the legacy py-module / inventory inflows (above, keeping the py-override
      precedence). The legacy inflows are normalized with the A3 platform's
      prompt->mode reverse map. Inventory / py aliases resolve within their own
      inflow only; a cross-inflow alias (e.g. inventory aliasing an A3 command)
      is out of scope until the inventory rework (#266) — shipped data has none.

    Pure (no session state): the result is per-host invariant, so the server
    builds it once and shares it across connections.
    """
    a3 = nos.resolved_platform
    if a3 is None:
        merged = {
            **copy.deepcopy(BASIC_COMMANDS),
            **copy.deepcopy(nos.commands or {}),
            **copy.deepcopy(inventory_commands),
        }
        return adapt_legacy_commands(nos.initial_prompt, nos.enable_prompt, nos.config_prompt, merged)
    reverse_map = reverse_map_from_modes(a3.modes)
    commands: dict = {}
    commands.update(adapt_commands(copy.deepcopy(BASIC_COMMANDS), reverse_map))
    commands.update(a3.commands)
    commands.update(adapt_commands(copy.deepcopy(nos.commands or {}), reverse_map))
    commands.update(adapt_commands(copy.deepcopy(inventory_commands), reverse_map))
    # Carry `auth` so the merged platform mirrors the A3 source — auth is consumed
    # via `nos.auth`, but dropping it would re-introduce the silent-dead-end
    # asymmetry the auth wiring fixed (2nd round codex/claude #3).
    return ResolvedPlatform(modes=a3.modes, initial_mode=a3.initial_mode, commands=commands, auth=a3.auth)


class CMDShell(Cmd):
    """
    Custom shell class to interact with NOS.
    """

    use_rawinput = False

    def __init__(
        self,
        stdin,
        stdout,
        nos,
        nos_inventory_config,
        base_prompt,
        is_running,
        intro="Custom SSH Shell",
        ruler="",
        completekey="tab",
        newline="\r\n",
        resolved_platform=None,
    ):
        self.nos: Nos = nos
        # Platform name captured at build time for the hot-reload ownership filter
        # (#274 / D6). A later foreign py reload can overwrite live `nos.name`
        # (`_from_module` commit phase), so the filter must compare against this
        # frozen value, not `self.nos.name`, or a hijacked name would permanently
        # skip this session's own A3 platform reload.
        self._platform_name: str = nos.name
        self.ruler = ruler
        self.intro = intro
        self.base_prompt = base_prompt
        self.newline = newline
        self.is_running = is_running
        # Inventory-defined commands are a third inflow alongside BASIC and the
        # NOS data; kept in authoring form and normalized through the adapter on
        # a hot-reload rebuild (#264 / D6).
        self._inventory_commands: dict = nos_inventory_config.get("commands", {})
        # The merged platform is per-host invariant (base_prompt is the host name,
        # nos/inventory are shared), so the server normalizes it once at
        # Host.start and passes it to every connection's shell (#264 / Impact —
        # normalize once, fail at startup). When not supplied (tests / direct
        # construction) the shell builds its own. A malformed prompt template
        # fails loudly here (the #172 lenient fallback is gone, #264 / D5).
        if resolved_platform is None:
            resolved_platform = build_resolved_platform(self.nos, self._inventory_commands)
        self._apply_platform(resolved_platform)

        # call the base constructor of cmd.Cmd, with our own stdin and stdout
        super().__init__(
            completekey=completekey,
            stdin=stdin,
            stdout=stdout,
        )

    @staticmethod
    def build_shared_platform(nos: Nos, nos_inventory_config: dict) -> ResolvedPlatform | None:
        """Build the per-host merged platform the server shares across connections.

        Called once at Host.start (by the server) so inventory/data errors fail
        there rather than on each connection, and so the normalization is not
        repeated per connection (#264 / Impact).

        Returns None when hot-reload is enabled (`SIMNOS_RELOAD_COMMANDS`): in
        that dev mode each connection must rebuild from the live `nos` so file
        edits propagate to new connections, so there is no shared snapshot.
        """
        if os.environ.get("SIMNOS_RELOAD_COMMANDS"):
            return None
        return build_resolved_platform(nos, nos_inventory_config.get("commands", {}))

    def _apply_platform(self, platform: ResolvedPlatform) -> None:
        """Install a (built or shared) platform + refresh session mode / prompt."""
        self.platform = platform
        self.commands = platform.commands
        # Keep the user's current mode across a hot reload when it still exists;
        # otherwise (first build, or a reload that dropped the mode) start at the
        # platform's initial mode.
        if getattr(self, "current_mode", None) not in platform.modes:
            self.current_mode = platform.initial_mode
        self.prompt = platform.modes[self.current_mode].render_prompt(self.base_prompt)

    def _rebuild(self) -> None:
        """Re-merge the inflows and install the result (hot-reload path).

        Atomic: `build_resolved_platform` raises before `_apply_platform` mutates
        anything, so a broken hot reload leaves the running session intact
        (#264 / D5, D6).
        """
        self._apply_platform(build_resolved_platform(self.nos, self._inventory_commands))

    def start(self):
        """Method to start the shell"""
        self.cmdloop()

    def stop(self):
        """Method to stop the shell"""
        self.stdin.write("exit" + self.newline)

    def writeline(self, value):
        """Method to write a line to stdout with newline at the end"""
        for line in str(value).splitlines():
            self.stdout.write(line + self.newline)

    def do_EOF(self, line):
        """Handle EOF from readline — exit the shell gracefully."""
        return True

    def emptyline(self):
        """This method to do nothing if empty line entered"""

    # `Nos` state `from_file` mutates; snapshotted per reload target so a target
    # that loads but fails to normalize can be rolled back (2nd round codex #1).
    _NOS_RELOAD_ATTRS = (
        "name",
        "initial_prompt",
        "enable_prompt",
        "config_prompt",
        "auth",
        "device",
        "resolved_platform",
    )

    def reload_commands(self, reload_targets: list):
        """Method to reload commands

        Lenient per file: hot reload is a dev feature and may observe a
        half-written or malformed plugin file (e.g. an editor's partial
        save, or a file that vanished after detection). One broken file
        must not kill the SSH session nor block reloading the remaining
        files — log and retry on the next change.

        `from_file` commits to `self.nos` *before* the adapter validates it in
        `_rebuild`, so a file that loads under the legacy schema but fails
        normalization (e.g. a canonical-外 prompt) would leave broken commands
        in `self.nos` and re-fail every later file in the batch. Snapshot the
        mutated nos state and roll it back on failure to keep the per-file
        contract; `_rebuild` itself is atomic, so live `self.commands` is never
        touched by a failed reload (2nd round codex #1).

        The A3 platform parse is cached by `load_platform_dir`; drop that cache
        first so a reload re-reads the changed files instead of the stale parse
        (#264 / D6 cache bypass). No-op for legacy yaml/py reloads.

        `reload_targets` are reload units (A3 platform dirs / `.py` modules), not
        raw changed files (#274 / D1). A dir target for a *different* platform is
        skipped (#274 / D6 ownership filter): the watcher sees the whole
        `plugins/nos` tree, so without this a sibling platform's edit — or a
        `git checkout` touching many platforms — would `_from_platform_dir`-replace
        this session's `resolved_platform` and hijack it onto another NOS.
        """
        load_platform_dir.cache_clear()
        for target in reload_targets:
            if os.path.isdir(target) and os.path.basename(target) != self._platform_name:
                # Foreign A3 platform dir — not this session's platform. Skipping
                # keeps a sibling edit / git checkout from hijacking the session.
                continue
            snapshot_commands = dict(self.nos.commands)
            snapshot_attrs = {attr: getattr(self.nos, attr) for attr in self._NOS_RELOAD_ATTRS}
            try:
                self.nos.from_file(target)
                self._rebuild()
            except Exception:
                # Broad except, like `default()`: any plugin error must not
                # crash the session. Roll back the partial nos mutation so the
                # broken file does not poison subsequent reloads, then log the
                # traceback so a genuine plugin bug stays diagnosable.
                self.nos.commands = snapshot_commands
                for attr, value in snapshot_attrs.items():
                    setattr(self.nos, attr, value)
                log.error("shell '%s' failed to hot-reload %r\n%s", self.base_prompt, target, traceback.format_exc())
                continue

    def precmd(self, line):
        """Method to return line before processing the command"""
        if os.environ.get("SIMNOS_RELOAD_COMMANDS"):
            reload_targets = get_files_changed(nos.__path__[0])
            if reload_targets:
                log.debug("Reloading... Reload targets: %s", reload_targets)
                self.reload_commands(reload_targets)
        return line

    def postcmd(self, stop, line):
        """Method to return stop value to stop the shell"""
        return stop

    def _in_current_mode(self, cmd: ResolvedCommand) -> bool:
        """Whether `cmd` is valid in the current mode (empty modes = all)."""
        return not cmd.modes or self.current_mode in cmd.modes

    def do_help(self, arg):
        """List help for commands valid in the current mode.

        Intentional refinement over v2 (2nd round claude #2): v2 `do_help`
        read the raw unmerged entries, so an alias without its own prompt was
        listed in *every* mode even where typing it fell through to
        `_default_`. Listing by the resolved mode set instead matches
        dispatchability — e.g. arista_eos's prompt-less aliases (``config
        term``) now appear only in their target mode. Dispatch behavior is
        unchanged (v2 already matched on the merged prompt); only the help
        listing is affected.
        """
        lines = {}  # dict of {cmd: cmd_help}
        width = 0  # record longest command width for padding
        for name, cmd in self.commands.items():
            # skip special commands
            if name.startswith("_") and name.endswith("_"):
                continue
            # skip commands not valid in the current mode
            if not self._in_current_mode(cmd):
                continue
            lines[name] = cmd.help
            width = max(width, len(name))
        # form help lines
        help_msg = []
        for k, v in lines.items():
            padding = " " * (width - len(k)) + "  "
            help_msg.append(f"{k}{padding}{v}")
        self.writeline(self.newline.join(help_msg))

    def _apply_new_mode(self, mode_name: str, command: str) -> None:
        """Transition to `mode_name`; an unknown name keeps the current mode.

        Static transitions (`ResolvedCommand.new_mode`) are validated at load,
        so they always resolve. A handler-returned `new_mode` is runtime data,
        so an unknown one is lenient: log and stay put (#264 / D5).
        """
        mode = self.platform.modes.get(mode_name)
        if mode is None:
            log.error(
                "shell '%s' command %r returned unknown mode %r; staying in %r",
                self.base_prompt,
                command,
                mode_name,
                self.current_mode,
            )
            return
        self.current_mode = mode_name
        self.prompt = mode.render_prompt(self.base_prompt)

    def _invoke_handler(self, handler: CommandHandler, command: str) -> CommandResult:
        """Invoke a command handler and normalize its return to CommandResult.

        A plain str (or None) return is sugar for `{"output": <value>}`;
        see `simnos.core.command_contract`. This is normalization, not
        validation: a contract-breaking return (list / int / ...) is
        wrapped and flows through the lenient output path like today —
        contract violations are caught statically (Protocol) and by the
        e2e callable sweep, not at runtime on the hot path.
        """
        ret = handler(
            self.nos.device,
            base_prompt=self.base_prompt,
            current_mode=self.current_mode,
            current_prompt=self.prompt,
            command=command,
        )
        if isinstance(ret, dict):
            return ret
        # Declare the wrapped value as str | None for the type checker (it
        # cannot narrow the TypedDict member out of the union by isinstance).
        return {"output": cast("str | None", ret)}

    def default(self, line):
        """Dispatch `line`: resolve -> mode check -> render/invoke -> transition.

        The exception boundary is the `_invoke_handler` block only: resolution,
        the mode check and the transition never raise (an unknown command is a
        plain dict miss, an unknown handler mode degrades inside
        `_apply_new_mode`), so `HANDLER_ERROR_OUTPUT` structurally means "a
        command handler crashed" and nothing else (#241 / #264).
        """
        log.debug("shell.default '%s' running command '%s'", self.base_prompt, [line])
        cmd = self.commands.get(line)
        if cmd is not None and self._in_current_mode(cmd):
            if cmd.exit:
                return True
            output = cmd.output
            transition = cmd.new_mode
        else:
            if cmd is not None:
                log.warning(
                    "'%s' command not valid in current mode '%s' (valid modes: %s)",
                    line,
                    self.current_mode,
                    ", ".join(sorted(cmd.modes)) if cmd.modes else "all",
                )
            else:
                # Keep the unknown-command trail v2 logged (observability for
                # typo / undefined-command diagnosis); the wire answer is the
                # same `_default_` output (2nd round claude #5).
                log.debug("shell.default '%s' command %r not found", self.base_prompt, line)
            # Unknown command and mode mismatch both answer with the `_default_`
            # output — a silent shell would make clients (e.g. Netmiko) wait for
            # a timeout. The `_default_` answer never applies a transition.
            output = self.commands["_default_"].output
            transition = None
        if output.kind == "handler" and output.handler is not None:
            try:
                result = self._invoke_handler(output.handler, line)
            except Exception:
                # Same shape as the hot-reload guard (#232): full traceback
                # to the log, the session survives, and the client gets a
                # real-NOS-style one-liner instead of a Python traceback.
                log.error("shell '%s' command %r handler crashed\n%s", self.base_prompt, line, traceback.format_exc())
                result = {"output": HANDLER_ERROR_OUTPUT}
            if result.get("exit"):
                return True
            # A handler transition applies only when the command has no static
            # one (a static `new_mode` was the last write in the v2 order).
            if transition is None:
                transition = result.get("new_mode")
            body = result.get("output")
        else:
            body = output.render(self.base_prompt)
        if transition is not None:
            self._apply_new_mode(transition, line)
        if not self.is_running.is_set():
            return True
        if body is not None:
            self.writeline(body)
        return False
