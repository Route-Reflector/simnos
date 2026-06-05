"""
Custom shell class to interact with NOS.
"""

from cmd import Cmd
import copy
import logging
import os
import traceback

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
            except Exception as e:
                log.error("shell '%s' failed to hot-reload %r: %r", self.base_prompt, file, e)
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

    def default(self, line):
        """Method called if no do_xyz methods found"""
        log.debug("shell.default '%s' running command '%s'", self.base_prompt, [line])
        ret = self.commands["_default_"]["output"]
        try:
            cmd_data = self.commands[line]
            if "alias" in cmd_data:
                cmd_data = {**self.commands[cmd_data["alias"]], **cmd_data}
            if self._check_prompt(cmd_data.get("prompt"), command=line):
                if cmd_data.get("exit"):
                    return True
                ret = cmd_data.get("output")
                if callable(ret):
                    ret = ret(
                        self.nos.device,
                        base_prompt=self.base_prompt,
                        current_prompt=self.prompt,
                        command=line,
                    )
                    if isinstance(ret, dict):
                        if "new_prompt" in ret:
                            self._apply_new_prompt(ret["new_prompt"], line)
                        if ret.get("exit"):
                            return True
                        ret = ret.get("output")
                if "new_prompt" in cmd_data:
                    self._apply_new_prompt(cmd_data["new_prompt"], line)
            else:
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
        except KeyError:
            log.error("shell.default '%s' command '%s' not found", self.base_prompt, [line])
            if callable(ret):
                ret = "An error occurred related to the command function"
        except ValueError:
            log.error("Output is still a callable")
            ret = "An error occurred"
        except Exception as e:
            log.error("An error occurred: %s", str(e))
            ret = traceback.format_exc()
            ret = ret.replace("\n", self.newline)
        if not self.is_running.is_set():
            return True
        if ret is not None:
            # Failure falls back to the raw template (information beats
            # dropping the whole output); lenient policy in _safe_format.
            formatted = self._safe_format(ret, where=f"output for command {line!r}")
            self.writeline(formatted if formatted is not None else ret)
        return False
