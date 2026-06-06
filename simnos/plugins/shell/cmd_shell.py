"""
Custom shell class to interact with NOS.
"""

from cmd import Cmd
import copy
import logging
import os
import traceback
from typing import cast

from simnos.core.command_contract import CommandHandler, CommandResult
from simnos.core.nos import Nos
from simnos.plugins import nos
from simnos.plugins.shell.utils import get_files_changed

log = logging.getLogger(__name__)

BASIC_COMMANDS: dict = {
    "exit": {"exit": True, "help": "Exit commands shell"},
    "_default_": {
        "output": "Unknown command",
        "help": "Output to print for unknown commands",
    },
}

# `str.format()` failure modes caused by a malformed template. Shared as the
# single source of truth between the lenient runtime shell (`_safe_format`)
# and the loud build-time docs gen (`tasks.render_template`); the runtime
# logs and degrades while build time raises (and additionally strict-rejects
# unsupported constructs that would render fine).
FORMAT_ERRORS = (KeyError, IndexError, ValueError, AttributeError, TypeError)

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
        # Lenient: a malformed initial_prompt template must not kill every
        # connection to this host; fall back to the raw template and log.
        formatted = self._safe_format(nos.initial_prompt, where="initial_prompt")
        self.prompt = formatted if formatted is not None else nos.initial_prompt
        self.is_running = is_running

        # form commands
        self.commands = {
            **copy.deepcopy(BASIC_COMMANDS),
            **copy.deepcopy(nos.commands or {}),
            **copy.deepcopy(nos_inventory_config.get("commands", {})),
        }
        # call the base constructor of cmd.Cmd, with our own stdin and stdout
        super().__init__(
            completekey=completekey,
            stdin=stdin,
            stdout=stdout,
        )

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

    def reload_commands(self, changed_files: list):
        """Method to reload commands

        Lenient per file: hot reload is a dev feature and may observe a
        half-written or malformed plugin file (e.g. an editor's partial
        save, or a file that vanished after detection). One broken file
        must not kill the SSH session nor block reloading the remaining
        files — log and retry on the next change.
        """
        for file in changed_files:
            try:
                self.nos.from_file(file)
            except Exception:
                # Broad except, like `default()`: any plugin error must not
                # crash the session. The traceback goes to the log so a
                # genuine plugin bug surfacing here stays diagnosable.
                log.error("shell '%s' failed to hot-reload %r\n%s", self.base_prompt, file, traceback.format_exc())
                continue
            self.commands.update(self.nos.commands)

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

    def do_help(self, arg):
        """Method to return help for commands"""
        lines = {}  # dict of {cmd: cmd_help}
        width = 0  # record longest command width for padding
        # form help for all commands
        for cmd, cmd_data in self.commands.items():
            # skip special commands
            if cmd.startswith("_") and cmd.endswith("_"):
                continue
            # skip commands that does not match current prompt
            if not self._check_prompt(cmd_data.get("prompt"), command=cmd):
                continue
            lines[cmd] = cmd_data.get("help", "")
            width = max(width, len(cmd))
        # form help lines
        help_msg = []
        for k, v in lines.items():
            padding = " " * (width - len(k)) + "  "
            help_msg.append(f"{k}{padding}{v}")
        self.writeline(self.newline.join(help_msg))

    def _safe_format(self, template: str, *, where: str) -> str | None:
        """Format `template` with `base_prompt`; return None on failure.

        The runtime shell is intentionally lenient: yaml templating errors
        are logged but never crash the session nor leak tracebacks to the
        wire. The build-time counterpart `tasks.render_template` shares the
        `FORMAT_ERRORS` catch set but raises `RuntimeError` — and is
        additionally strict about unsupported constructs that would render
        fine (e.g. `{base_prompt!r}`). Yaml authors may use only
        `{base_prompt}` substitution and `{{` / `}}` escapes; see
        docs/development/creating_new_platforms.md.

        :param template: format template string from yaml / plugin data
        :param where: caller context for the error log; include the command
            name when available (e.g. ``f"output for command {line!r}"``)
        """
        try:
            return template.format(base_prompt=self.base_prompt)
        except FORMAT_ERRORS as e:
            log.error(
                "shell '%s' error formatting %s %r: %r",
                self.base_prompt,
                where,
                template,
                e,
            )
            return None

    def _check_prompt(self, prompt_: str | list[str] | None, command: str = ""):
        """
        Helper method to check if prompt_ matches current prompt

        :param prompt_: (string, list of strings, or None) prompt to check
        :param command: command name for the error log; callers without it
            keep working (the log just omits the command context)
        """
        # prompt_ is None if no 'prompt' key defined for command
        if prompt_ is None:
            return True
        candidates = [prompt_] if isinstance(prompt_, str) else prompt_
        where = f"prompt for command {command!r}" if command else "prompt"
        # A broken candidate is just a non-match; the remaining candidates
        # are still evaluated independently.
        for candidate in candidates:
            formatted = self._safe_format(candidate, where=where)
            if formatted is not None and self.prompt == formatted:
                return True
        return False

    def _apply_new_prompt(self, template: str, command: str) -> None:
        """Transition the prompt; a broken template keeps the current one.

        Shared by the callable-dict and cmd_data `new_prompt` paths of
        `default()`: a format failure means no prompt transition (the
        session stays on the current prompt); see `_safe_format`.
        """
        new_prompt = self._safe_format(template, where=f"new_prompt for command {command!r}")
        if new_prompt is not None:
            self.prompt = new_prompt

    def _resolve_command(self, command: str) -> dict | None:
        """Return the merged cmd_data for `command`, or None if unknown.

        Alias resolution happens here too: a missing alias target is the
        same lenient unknown-command path as a missing command (both used
        to be one broad `except KeyError`) — the caller answers with the
        `_default_` output, never with the handler-crash response.
        """
        try:
            cmd_data = self.commands[command]
            if "alias" in cmd_data:
                cmd_data = {**self.commands[cmd_data["alias"]], **cmd_data}
        except KeyError:
            log.error("shell.default '%s' command '%s' not found", self.base_prompt, [command])
            return None
        return cmd_data

    def _invoke_callable(self, func: CommandHandler, command: str) -> CommandResult:
        """Invoke a command handler and normalize its return to CommandResult.

        A plain str (or None) return is sugar for `{"output": <value>}`;
        see `simnos.core.command_contract`. This is normalization, not
        validation: a contract-breaking return (list / int / ...) is
        wrapped and flows through the lenient output path like today —
        contract violations are caught statically (Protocol) and by the
        e2e callable sweep, not at runtime on the hot path.
        """
        ret = func(
            self.nos.device,
            base_prompt=self.base_prompt,
            current_prompt=self.prompt,
            command=command,
        )
        if isinstance(ret, dict):
            return ret
        # After the dict check `ret` is str | None at runtime (a TypedDict
        # IS a dict); the cast spells that out for the type checker, which
        # cannot narrow the TypedDict member out of the union by isinstance.
        return {"output": cast("str | None", ret)}

    def _render_output(self, ret, command: str, *, format_output: bool) -> None:
        """Write `ret` to the client; only yaml-static output is formatted.

        `ret` is untyped on purpose: the lenient path also carries
        contract-breaking handler returns (see `_invoke_callable`), which
        `writeline`'s `str(value)` absorbs.

        Callable output is passed through verbatim (`format_output=False`):
        handlers receive `base_prompt` as an argument and format
        themselves (see `CommandHandler`), so a second `.format()` here
        would only mis-render device output containing literal braces or
        an accidental `{base_prompt}` (#241 / D-b). For yaml-static
        output, a format failure falls back to the raw template
        (information beats dropping the whole output); lenient policy in
        `_safe_format`.
        """
        if not format_output:
            self.writeline(ret)
            return
        formatted = self._safe_format(ret, where=f"output for command {command!r}")
        self.writeline(formatted if formatted is not None else ret)

    def default(self, line):
        """Dispatch `line`: resolve -> prompt check -> invoke -> render.

        The exception boundary is the `_invoke_callable` block only:
        resolve / alias / prompt check / new_prompt never raise (KeyError
        degrades inside `_resolve_command`, format errors are caught
        inside `_safe_format`), so `HANDLER_ERROR_OUTPUT` is structurally
        guaranteed to mean "a command handler crashed" and nothing else.
        """
        log.debug("shell.default '%s' running command '%s'", self.base_prompt, [line])
        from_callable = False
        cmd_data = self._resolve_command(line)
        if cmd_data is not None and self._check_prompt(cmd_data.get("prompt"), command=line):
            if cmd_data.get("exit"):
                return True
            ret = cmd_data.get("output")
        else:
            if cmd_data is not None:
                log.warning(
                    "'%s' command prompt '%s' not matching current prompt '%s'",
                    line,
                    (
                        ", ".join(cmd_data.get("prompt", []))
                        if isinstance(cmd_data.get("prompt"), list)
                        else cmd_data.get("prompt", "")
                    ),
                    self.prompt,
                )
            # Unknown command and prompt mismatch both answer with the
            # `_default_` output — a silent shell would make clients
            # (e.g. Netmiko) wait for a timeout instead.
            ret = self.commands["_default_"]["output"]
            cmd_data = None  # the `_default_` answer never applies cmd_data's new_prompt
        if callable(ret):
            from_callable = True
            try:
                result = self._invoke_callable(ret, line)
            except Exception:
                # Same shape as the hot-reload guard (#232): full traceback
                # to the log, the session survives, and the client gets a
                # real-NOS-style one-liner instead of a Python traceback.
                log.error(
                    "shell '%s' command %r handler crashed\n%s",
                    self.base_prompt,
                    line,
                    traceback.format_exc(),
                )
                result = {"output": HANDLER_ERROR_OUTPUT}
            if "new_prompt" in result:
                self._apply_new_prompt(result["new_prompt"], line)
            if result.get("exit"):
                return True
            ret = result.get("output")
        if cmd_data is not None and "new_prompt" in cmd_data:
            self._apply_new_prompt(cmd_data["new_prompt"], line)
        if not self.is_running.is_set():
            return True
        if ret is not None:
            self._render_output(ret, line, format_output=not from_callable)
        return False
