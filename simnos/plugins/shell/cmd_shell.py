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
    ):
        self.nos: Nos = nos
        self.ruler = ruler
        self.intro = intro
        self.base_prompt = base_prompt
        self.newline = newline
        self.is_running = is_running
        # Inventory-defined commands are a third inflow alongside BASIC and the
        # NOS data; kept in authoring form and normalized through the adapter on
        # every (re)build (#264 / D6).
        self._inventory_commands: dict = nos_inventory_config.get("commands", {})
        # Builds self.platform / self.commands / self.current_mode / self.prompt.
        # A malformed prompt template now fails loudly here (the #172 lenient
        # fallback is gone — prompt rendering is load-time validated, #264 / D5).
        self._rebuild()

        # call the base constructor of cmd.Cmd, with our own stdin and stdout
        super().__init__(
            completekey=completekey,
            stdin=stdin,
            stdout=stdout,
        )

    def _rebuild(self) -> None:
        """Merge the command inflows and normalize them to `ResolvedCommand`.

        The shell consumes one representation regardless of authoring form. Two
        inflow shapes are merged under the same precedence (BASIC < NOS < inventory,
        later inflows winning, as before):

        - **legacy NOS** (`self.nos.resolved_platform is None`): the merged dict
          (BASIC + NOS commands + inventory, all legacy form) is run through the
          legacy adapter, which synthesizes the modes from the 3 scalar prompts.
        - **A3 NOS** (`self.nos.resolved_platform` set): modes come from the A3
          platform; its resolved static commands sit between the still-legacy
          BASIC (below) and the legacy py-module/inventory inflows (above, which
          keep the py-override precedence). The legacy inflows are normalized
          with the A3 platform's prompt->mode reverse map.

        Atomic: if normalization raises (malformed data), self.* keep their prior
        values, so a broken hot reload leaves the running session intact
        (#264 / D5, D6).
        """
        if self.nos.resolved_platform is not None:
            platform = self._rebuild_a3(self.nos.resolved_platform)
        else:
            merged = {
                **copy.deepcopy(BASIC_COMMANDS),
                **copy.deepcopy(self.nos.commands or {}),
                **copy.deepcopy(self._inventory_commands),
            }
            platform = adapt_legacy_commands(
                self.nos.initial_prompt,
                self.nos.enable_prompt,
                self.nos.config_prompt,
                merged,
            )
        self.platform = platform
        self.commands = platform.commands
        # Keep the user's current mode across a hot reload when it still exists;
        # otherwise (first build, or a reload that dropped the mode) start at the
        # platform's initial mode.
        if getattr(self, "current_mode", None) not in platform.modes:
            self.current_mode = platform.initial_mode
        self.prompt = platform.modes[self.current_mode].render_prompt(self.base_prompt)

    def _rebuild_a3(self, a3: ResolvedPlatform) -> ResolvedPlatform:
        """Merge BASIC + py-module + inventory inflows over an A3 platform (#264 / D6).

        Modes come from the A3 platform. The still-legacy inflows are normalized
        with the A3 platform's prompt->mode reverse map and layered under/over the
        A3 static commands to keep the legacy precedence (BASIC < A3 static <
        py module < inventory). A py module loaded after the A3 dir populated
        ``self.nos.commands`` with its dynamic handlers — those override the A3
        statics, as the legacy py-override did.

        Inventory/py aliases are resolved within their own inflow only; an alias
        crossing inflows (e.g. inventory aliasing an A3 command) is out of scope
        until the inventory rework (#266) — shipped data has no such aliases.
        """
        reverse_map = reverse_map_from_modes(a3.modes)
        commands: dict = {}
        commands.update(adapt_commands(copy.deepcopy(BASIC_COMMANDS), reverse_map))
        commands.update(a3.commands)
        commands.update(adapt_commands(copy.deepcopy(self.nos.commands or {}), reverse_map))
        commands.update(adapt_commands(copy.deepcopy(self._inventory_commands), reverse_map))
        # Carry `auth` so the merged platform mirrors the A3 source — auth is
        # consumed via `nos.auth`, but dropping it here would re-introduce the
        # silent-dead-end asymmetry the auth wiring fixed (2nd round codex/claude #3).
        return ResolvedPlatform(modes=a3.modes, initial_mode=a3.initial_mode, commands=commands, auth=a3.auth)

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

    # `Nos` state `from_file` mutates; snapshotted per reloaded file so a file
    # that loads but fails to normalize can be rolled back (2nd round codex #1).
    _NOS_RELOAD_ATTRS = ("name", "initial_prompt", "enable_prompt", "config_prompt", "auth", "device")

    def reload_commands(self, changed_files: list):
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
        """
        load_platform_dir.cache_clear()
        for file in changed_files:
            snapshot_commands = dict(self.nos.commands)
            snapshot_attrs = {attr: getattr(self.nos, attr) for attr in self._NOS_RELOAD_ATTRS}
            try:
                self.nos.from_file(file)
                self._rebuild()
            except Exception:
                # Broad except, like `default()`: any plugin error must not
                # crash the session. Roll back the partial nos mutation so the
                # broken file does not poison subsequent reloads, then log the
                # traceback so a genuine plugin bug stays diagnosable.
                self.nos.commands = snapshot_commands
                for attr, value in snapshot_attrs.items():
                    setattr(self.nos, attr, value)
                log.error("shell '%s' failed to hot-reload %r\n%s", self.base_prompt, file, traceback.format_exc())
                continue

    def precmd(self, line):
        """Method to return line before processing the command"""
        if os.environ.get("SIMNOS_RELOAD_COMMANDS"):
            changed_files = get_files_changed(nos.__path__[0])
            if changed_files:
                log.debug("Reloading... Files changed: %s", changed_files)
                self.reload_commands(changed_files)
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
