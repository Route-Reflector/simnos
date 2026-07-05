"""Tests for the interactive challenge mechanism (#338 Phase 1: `kind: password`).

Covers the four layers the challenge rides on:

- **schema** (`ModelChallenge` / `ModelCommandAuthoring`): per-kind required
  fields, single-line prompt, exclusivity with handler / variants, alias +
  `_default_` rejection.
- **loader** (`_resolve_challenge`): mode normalization, the loud boundaries
  (mode subset, `success.new_mode`, unknown render var).
- **dispatch** (`CMDShell`): fire / non-fire (mode scoping, #338 案D), success /
  failure / empty answer, the `secret`->`password` fallback (案F), abbreviation,
  the creds-unwired warning, and the `is_running` close.
- **wire** (netmiko): the real `conn.enable()` success + a wrong secret raising.

The driver sub-phase (`_run_challenge` / `_read_challenge_line`) and the SSH /
Telnet byte-parity are pinned in `test_async_session.py` and the
`test_*_byte_parity.py` goldens respectively.
"""

import threading

from netmiko import ConnectHandler
from pydantic import ValidationError
import pytest

from simnos import SimNOS
from simnos.core.nos import Nos
from simnos.core.platform_loader import load_platform_dir
from simnos.core.pydantic_models import ModelChallenge, ModelCommandAuthoring
from simnos.plugins.shell.cmd_shell import CMDShell, PendingChallenge
from tests.utils import TEST_PASSWORD, TEST_USERNAME, build_inventory, netmiko_device_type_of

# A well-formed password challenge, reused across the schema tests.
_OK_CHALLENGE = {
    "kind": "password",
    "prompt": "[sudo] password for {{ username }}: ",
    "auth": "password",
    "success": {"new_mode": "enable"},
    "failure_output": "Sorry, try again.",
}


def _write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _platform(tmp_path, chal_yaml: str) -> str:
    """A minimal 2-mode A3 platform with one challenge command + `_default_`."""
    root = tmp_path / "chalp"
    _write(
        root / "platform.yaml",
        'modes:\n  user:\n    prompt: "{{ base_prompt }}$"\n'
        '  enable:\n    prompt: "{{ base_prompt }}#"\ninitial_mode: user\n',
    )
    _write(root / "commands" / "chal.yaml", chal_yaml)
    _write(root / "commands" / "default.yaml", "command: _default_\ntype: simnos\noutput: default.txt\n")
    _write(root / "commands" / "default.txt", "% Unknown command\n")
    return str(root)


def _shell(platform_dir: str, **creds) -> CMDShell:
    nos = Nos(filename=platform_dir)
    shell = CMDShell(nos=nos, nos_inventory_config={}, base_prompt="dev", is_running=threading.Event(), **creds)
    shell.is_running.set()
    return shell


# `model_validate` takes the raw mapping (Any), so nested dicts (challenge /
# success / variants) validate without a per-field type-checker suppression —
# the same runtime coercion + ValidationError the constructor gives.
def _cmd(**kw) -> ModelCommandAuthoring:
    return ModelCommandAuthoring.model_validate(kw)


def _chal(**kw) -> ModelChallenge:
    return ModelChallenge.model_validate(kw)


def _fire(shell: CMDShell, line: str) -> PendingChallenge:
    """Dispatch `line` and return the fired `PendingChallenge` (asserting it fired)."""
    pending = shell.dispatch(line).challenge
    assert pending is not None
    return pending


# --------------------------------------------------------------------- schema
class TestChallengeSchema:
    def test_valid_password_challenge_parses(self):
        m = _cmd(command="sudo -s", type="simnos", mode=["user"], challenge=_OK_CHALLENGE)
        assert m.challenge is not None
        assert m.challenge.kind == "password"
        assert m.challenge.auth == "password"
        assert m.challenge.success is not None and m.challenge.success.new_mode == "enable"

    def test_prompt_must_be_single_line(self):
        with pytest.raises(ValidationError, match="single line"):
            _chal(kind="password", prompt="line1\nline2", auth="password", success={"new_mode": "enable"})

    def test_prompt_rejects_nul(self):
        with pytest.raises(ValidationError, match="NUL"):
            _chal(kind="password", prompt="pw\x00: ", auth="password", success={"new_mode": "enable"})

    def test_auth_and_success_required(self):
        with pytest.raises(ValidationError):
            _chal(kind="password", prompt="Password: ")  # no auth / success

    def test_valid_confirm_challenge_parses(self):
        m = _chal(
            kind="confirm",
            prompt="Proceed? [confirm]",
            on={"": {"exit": True}, "n": {}},
            default={},
        )
        assert m.kind == "confirm"
        assert m.on is not None
        assert m.on[""].exit is True
        assert m.on["n"].new_mode is None and m.on["n"].exit is None  # cancel

    def test_confirm_requires_on(self):
        with pytest.raises(ValidationError, match="non-empty `on:`"):
            _chal(kind="confirm", prompt="Proceed? [confirm]")

    def test_confirm_empty_on_rejected(self):
        with pytest.raises(ValidationError, match="non-empty `on:`"):
            _chal(kind="confirm", prompt="Proceed? [confirm]", on={})

    def test_confirm_forbids_password_fields(self):
        with pytest.raises(ValidationError, match="password-only"):
            _chal(kind="confirm", prompt="Proceed? [confirm]", on={"": {"exit": True}}, auth="secret")

    def test_password_forbids_confirm_fields(self):
        with pytest.raises(ValidationError, match="confirm-only"):
            _chal(
                kind="password",
                prompt="Password: ",
                auth="password",
                success={"new_mode": "enable"},
                on={"": {"exit": True}},
            )

    def test_confirm_action_exit_with_output_rejected(self):
        # A closing session sends no body (the existing close contract, gemini#1).
        with pytest.raises(ValidationError, match="cannot set `output`"):
            _chal(kind="confirm", prompt="Proceed? [confirm]", on={"": {"exit": True, "output": "bye"}})

    def test_confirm_action_exit_false_rejected(self):
        with pytest.raises(ValidationError, match="`exit` must be true"):
            _chal(kind="confirm", prompt="Proceed? [confirm]", on={"": {"exit": False}})

    def test_confirm_action_new_mode_and_exit_rejected(self):
        with pytest.raises(ValidationError, match="at most one"):
            _chal(kind="confirm", prompt="Proceed? [confirm]", on={"": {"new_mode": "enable", "exit": True}})

    @pytest.mark.parametrize("bad_key", ["y\n", "y\r", "y\x00", "\x1b[A", "a\x7f", "a\x08"])
    def test_confirm_on_key_with_control_char_rejected(self, bad_key):
        # An `on:` key holding a byte the line reader never leaves in the answer
        # (CR/LF/NUL terminators/drops, ESC/BS/DEL editing) is a dead entry.
        with pytest.raises(ValidationError, match="control bytes"):
            _chal(kind="confirm", prompt="Proceed? [confirm]", on={bad_key: {"exit": True}})

    def test_challenge_exclusive_with_handler(self):
        with pytest.raises(ValidationError, match="exclusive"):
            _cmd(command="enable-admin", type="simnos", handler="do_enable", challenge=_OK_CHALLENGE)

    def test_challenge_exclusive_with_variants(self):
        with pytest.raises(ValidationError, match="exclusive"):
            _cmd(
                command="enable-admin",
                type="simnos",
                variants=[{"name": "variant_1", "output": "a.txt"}],
                challenge=_OK_CHALLENGE,
            )

    def test_challenge_exclusive_with_disables_paging(self):
        # A firing challenge returns before the sticky-paging flag would be set,
        # so authoring both would silently drop the disable (1st round claude#3).
        with pytest.raises(ValidationError, match="exclusive"):
            _cmd(command="enable-admin", type="simnos", mode=["user"], disables_paging=True, challenge=_OK_CHALLENGE)

    def test_challenge_composes_with_output(self):
        # A non-firing mode uses `output` — the alcatel_sros per-mode response (案D).
        m = _cmd(
            command="enable-admin",
            type="simnos",
            mode=["user", "enable"],
            output="already.txt",
            challenge={**_OK_CHALLENGE, "mode": ["user"]},
        )
        assert m.challenge is not None and m.output == "already.txt"

    def test_alias_cannot_author_challenge(self):
        with pytest.raises(ValidationError, match="alias cannot also set"):
            _cmd(command="ena", alias="enable-admin", challenge=_OK_CHALLENGE)

    def test_default_cannot_author_challenge(self):
        with pytest.raises(ValidationError, match="_default_"):
            _cmd(command="_default_", type="simnos", challenge=_OK_CHALLENGE)

    def test_challenge_mode_empty_list_rejected(self):
        with pytest.raises(ValidationError, match="omit `mode`"):
            _chal(kind="password", prompt="Password: ", mode=[], auth="password", success={"new_mode": "enable"})


# --------------------------------------------------------------------- loader
class TestChallengeLoader:
    def test_resolves_challenge_fields(self, tmp_path):
        p = _platform(
            tmp_path,
            "command: sudo -s\ntype: simnos\nmode: [user]\n"
            'challenge:\n  kind: password\n  prompt: "[sudo] password for {{ username }}: "\n'
            "  auth: password\n  success:\n    new_mode: enable\n  failure_output: nope\n",
        )
        cmd = load_platform_dir(p).commands["sudo -s"]
        assert cmd.challenge is not None
        ch = cmd.challenge
        assert ch.kind == "password"
        assert ch.auth == "password"
        assert ch.modes == frozenset({"user"})
        assert ch.success is not None and ch.success.new_mode == "enable"
        assert ch.failure_output == "nope"
        assert ch.prompt.kind == "template"  # references `username`

    def test_literal_prompt_stored_verbatim(self, tmp_path):
        p = _platform(
            tmp_path,
            "command: enable-admin\ntype: simnos\nmode: [user]\n"
            'challenge:\n  kind: password\n  prompt: "Password: "\n  auth: secret\n  success:\n    new_mode: enable\n',
        )
        ch = load_platform_dir(p).commands["enable-admin"].challenge
        assert ch is not None
        assert ch.prompt.kind == "literal" and ch.prompt.text == "Password: "

    def test_mode_omitted_fires_in_all_command_modes(self, tmp_path):
        p = _platform(
            tmp_path,
            "command: enable-admin\ntype: simnos\nmode: [user, enable]\n"
            'challenge:\n  kind: password\n  prompt: "Password: "\n  auth: secret\n  success:\n    exit: true\n',
        )
        ch = load_platform_dir(p).commands["enable-admin"].challenge
        assert ch is not None
        assert ch.modes == frozenset({"user", "enable"})

    def test_all_modes_command_challenge_expands_to_platform_modes(self, tmp_path):
        # Command-level `mode:` omitted (all-modes, empty cmd_modes) + challenge.mode
        # omitted → the challenge fires in every platform mode, not the empty set (the
        # `cmd_modes or mode_names` expansion, mirroring resolve_transitions). Without
        # it `current_mode in modes` would always be False = a silent non-fire (design
        # anti-silent-bug, codex 1st#4).
        p = _platform(
            tmp_path,
            "command: sudo -s\ntype: simnos\n"  # no `mode:` → all-modes command
            'challenge:\n  kind: password\n  prompt: "Password: "\n  auth: secret\n  success:\n    exit: true\n',
        )
        ch = load_platform_dir(p).commands["sudo -s"].challenge
        assert ch is not None
        assert ch.modes == frozenset({"user", "enable"})  # full platform mode set

    def test_challenge_mode_not_subset_is_loud(self, tmp_path):
        p = _platform(
            tmp_path,
            "command: enable-admin\ntype: simnos\nmode: [user]\n"
            'challenge:\n  kind: password\n  mode: [enable]\n  prompt: "Password: "\n'
            "  auth: secret\n  success:\n    exit: true\n",
        )
        with pytest.raises(ValueError, match=r"challenge\.mode"):
            load_platform_dir(p)

    def test_success_new_mode_absent_is_loud(self, tmp_path):
        p = _platform(
            tmp_path,
            "command: enable-admin\ntype: simnos\nmode: [user]\n"
            'challenge:\n  kind: password\n  prompt: "Password: "\n  auth: secret\n'
            "  success:\n    new_mode: nope\n",
        )
        with pytest.raises(ValueError, match="new_mode"):
            load_platform_dir(p)

    def test_resolves_confirm_actions(self, tmp_path):
        p = _platform(
            tmp_path,
            "command: reload\ntype: simnos\nmode: [enable]\n"
            'challenge:\n  kind: confirm\n  prompt: "Proceed? [confirm]"\n'
            '  "on":\n    "": {exit: true}\n    "n": {}\n'
            '  default: {output: "[OK]"}\n',
        )
        ch = load_platform_dir(p).commands["reload"].challenge
        assert ch is not None
        assert ch.kind == "confirm"
        assert ch.auth is None and ch.success is None  # password-only fields absent
        assert ch.on is not None
        assert ch.on[""].exit is True and ch.on[""].output is None
        assert ch.on["n"].exit is False and ch.on["n"].new_mode is None  # cancel
        assert ch.default is not None and ch.default.output == "[OK]"

    def test_confirm_on_action_new_mode_absent_is_loud(self, tmp_path):
        # The error names the offending slot (`on['y']`) so a multi-entry confirm
        # points the author at the right action (1st claude#5 / 2nd codex#3).
        p = _platform(
            tmp_path,
            "command: reload\ntype: simnos\nmode: [enable]\n"
            'challenge:\n  kind: confirm\n  prompt: "Proceed? [confirm]"\n'
            '  "on":\n    "y": {new_mode: nope}\n',
        )
        with pytest.raises(ValueError, match=r"on\['y'\].*new_mode 'nope'"):
            load_platform_dir(p)

    def test_confirm_default_action_new_mode_absent_is_loud(self, tmp_path):
        # The `default:` slot is validated + named the same way as an `on:` entry.
        p = _platform(
            tmp_path,
            "command: reload\ntype: simnos\nmode: [enable]\n"
            'challenge:\n  kind: confirm\n  prompt: "Proceed? [confirm]"\n'
            '  "on":\n    "": {}\n  default: {new_mode: nope}\n',
        )
        with pytest.raises(ValueError, match=r"default new_mode 'nope'"):
            load_platform_dir(p)

    def test_unknown_render_var_is_loud(self, tmp_path):
        p = _platform(
            tmp_path,
            "command: enable-admin\ntype: simnos\nmode: [user]\n"
            'challenge:\n  kind: password\n  prompt: "{{ bogus }}: "\n  auth: secret\n'
            "  success:\n    exit: true\n",
        )
        with pytest.raises(ValueError, match="unknown variable"):
            load_platform_dir(p)


# --------------------------------------------------------------------- dispatch
_PW_CMD = (
    "command: sudo -s\ntype: simnos\nmode: [user]\n"
    'challenge:\n  kind: password\n  prompt: "[sudo] password for {{ username }}: "\n'
    "  auth: password\n  success:\n    new_mode: enable\n  failure_output: Sorry, try again.\n"
)

# A confirm challenge that closes on Enter / `y`, cancels on `n` / anything else
# (the `reload [confirm]` shape); fires in user mode to keep the unit test simple.
_CONFIRM_CLOSE_CMD = (
    "command: reload\ntype: simnos\nmode: [user]\n"
    'challenge:\n  kind: confirm\n  prompt: "Proceed with reload? [confirm]"\n'
    '  "on":\n    "": {exit: true}\n    "y": {exit: true}\n    "n": {}\n  default: {}\n'
)

# A free-line confirm that emits an `[OK]` body and stays put (the `copy running-config
# startup-config` shape: Enter or any typed filename both build).
_CONFIRM_OUTPUT_CMD = (
    "command: save\ntype: simnos\nmode: [user]\n"
    'challenge:\n  kind: confirm\n  prompt: "Destination filename [startup-config]? "\n'
    '  "on":\n    "": {output: "[OK]"}\n  default: {output: "[OK]"}\n'
)

# A confirm whose actions transition mode (`new_mode`) — one bare, one also with a
# body — and which authors NO `default:`, so an unknown answer falls through to a
# plain cancel (the `on` miss + `default is None` path, not a cancel action).
_CONFIRM_MODE_CMD = (
    "command: switchmode\ntype: simnos\nmode: [user]\n"
    'challenge:\n  kind: confirm\n  prompt: "Enter mode? "\n'
    '  "on":\n    "e": {new_mode: enable}\n    "b": {new_mode: enable, output: "[OK]"}\n'
)


class TestChallengeDispatch:
    def test_fires_in_firing_mode(self, tmp_path):
        shell = _shell(_platform(tmp_path, _PW_CMD), username="admin", password="pw")
        r = shell.dispatch("sudo -s")
        assert r.challenge is not None
        assert r.body is None and r.close is False
        assert r.challenge.prompt_text == "[sudo] password for admin: "
        assert r.challenge.echo is False  # password: never echo
        assert r.challenge.command == "sudo -s"

    def test_success_transitions(self, tmp_path):
        shell = _shell(_platform(tmp_path, _PW_CMD), username="admin", password="pw")
        pending = _fire(shell, "sudo -s")
        r = shell.complete_challenge(pending, "pw")
        assert r.mode == "enable" and r.body is None and r.prompt == "dev#"

    def test_failure_keeps_prompt(self, tmp_path):
        shell = _shell(_platform(tmp_path, _PW_CMD), username="admin", password="pw")
        pending = _fire(shell, "sudo -s")
        r = shell.complete_challenge(pending, "wrong")
        assert r.body == "Sorry, try again." and r.mode == "user" and r.prompt == "dev$"

    def test_empty_answer_fails(self, tmp_path):
        shell = _shell(_platform(tmp_path, _PW_CMD), username="admin", password="pw")
        pending = _fire(shell, "sudo -s")
        r = shell.complete_challenge(pending, "")  # bare Enter (nokia_sros escape path)
        assert r.body == "Sorry, try again." and r.mode == "user"

    def test_non_firing_mode_uses_output(self, tmp_path):
        # challenge.mode=[user] + output for enable: dispatch in enable answers the
        # output with NO challenge (alcatel_sros per-mode response, 案D).
        p = _platform(
            tmp_path,
            "command: enable-admin\ntype: simnos\nmode: [user, enable]\noutput: already.txt\n"
            'challenge:\n  kind: password\n  mode: [user]\n  prompt: "Password: "\n'
            "  auth: secret\n  success:\n    new_mode: enable\n",
        )
        (tmp_path / "chalp" / "commands" / "already.txt").write_text("Already in admin mode.\n", encoding="utf-8")
        shell = _shell(p, username="admin", password="pw", secret="sec")
        shell.current_mode = "enable"
        shell.prompt = "dev#"
        r = shell.dispatch("enable-admin")
        assert r.challenge is None
        assert r.body is not None and r.body.strip() == "Already in admin mode." and r.mode == "enable"

    def test_secret_fallback_to_password(self, tmp_path):
        # auth: secret with `secret` unset -> falls back to `password` (案F).
        p = _platform(
            tmp_path,
            "command: enable-admin\ntype: simnos\nmode: [user]\n"
            'challenge:\n  kind: password\n  prompt: "Password: "\n  auth: secret\n'
            "  success:\n    new_mode: enable\n",
        )
        shell = _shell(p, username="admin", password="pw", secret=None)
        pending = _fire(shell, "enable-admin")
        assert shell.complete_challenge(pending, "pw").mode == "enable"

    def test_secret_used_when_set(self, tmp_path):
        p = _platform(
            tmp_path,
            "command: enable-admin\ntype: simnos\nmode: [user]\n"
            'challenge:\n  kind: password\n  prompt: "Password: "\n  auth: secret\n'
            "  success:\n    new_mode: enable\n",
        )
        shell = _shell(p, username="admin", password="pw", secret="sec")
        pending = _fire(shell, "enable-admin")
        assert shell.complete_challenge(pending, "sec").mode == "enable"  # secret matches
        shell.current_mode = "user"
        assert shell.complete_challenge(pending, "pw").mode == "user"  # password does NOT match a set secret

    def test_abbreviation_fires_challenge(self, tmp_path):
        # `en` resolves to the sole `enable-admin` and fires its challenge, IOS-style.
        p = _platform(
            tmp_path,
            "command: enable-admin\ntype: simnos\nmode: [user]\n"
            'challenge:\n  kind: password\n  prompt: "Password: "\n  auth: secret\n'
            "  success:\n    new_mode: enable\n",
        )
        shell = _shell(p, username="admin", password="pw", secret="sec")
        assert shell.dispatch("en").challenge is not None

    def test_creds_unwired_warns_and_fails(self, tmp_path, caplog):
        # A direct construction with no creds hits a challenge: loud warning + failure,
        # never a silent always-fail (anti-silent-bug, 1st round claude#5).
        shell = _shell(_platform(tmp_path, _PW_CMD))  # no username/password/secret
        pending = _fire(shell, "sudo -s")
        with caplog.at_level("WARNING"):
            r = shell.complete_challenge(pending, "anything")
        assert r.body == "Sorry, try again."
        assert "no credentials wired" in caplog.text

    def test_is_running_clear_closes(self, tmp_path):
        shell = _shell(_platform(tmp_path, _PW_CMD), username="admin", password="pw")
        pending = _fire(shell, "sudo -s")
        shell.is_running.clear()  # mid-shutdown
        assert shell.complete_challenge(pending, "pw").close is True

    def test_answer_not_logged(self, tmp_path, caplog):
        # R5: the entered value never appears in the log.
        shell = _shell(_platform(tmp_path, _PW_CMD), username="admin", password="pw")
        pending = _fire(shell, "sudo -s")
        with caplog.at_level("DEBUG"):
            shell.complete_challenge(pending, "s3cr3t-marker")
        assert "s3cr3t-marker" not in caplog.text


class TestConfirmChallenge:
    """`kind: confirm` dispatch — echoed answer looked up in `on` / `default` (#338 Phase 3)."""

    def test_confirm_fires_with_echo(self, tmp_path):
        shell = _shell(_platform(tmp_path, _CONFIRM_CLOSE_CMD))
        r = shell.dispatch("reload")
        assert r.challenge is not None
        assert r.body is None and r.close is False
        assert r.challenge.prompt_text == "Proceed with reload? [confirm]"
        assert r.challenge.echo is True  # confirm: echoed (unlike password)
        assert r.challenge.command == "reload"

    def test_confirm_close_on_enter(self, tmp_path):
        shell = _shell(_platform(tmp_path, _CONFIRM_CLOSE_CMD))
        pending = _fire(shell, "reload")
        r = shell.complete_challenge(pending, "")  # bare Enter confirms
        assert r.close is True and r.body is None

    def test_confirm_close_on_y(self, tmp_path):
        shell = _shell(_platform(tmp_path, _CONFIRM_CLOSE_CMD))
        pending = _fire(shell, "reload")
        assert shell.complete_challenge(pending, "y").close is True

    def test_confirm_cancel_on_n(self, tmp_path):
        shell = _shell(_platform(tmp_path, _CONFIRM_CLOSE_CMD))
        pending = _fire(shell, "reload")
        r = shell.complete_challenge(pending, "n")  # explicit cancel: no close, no body, prompt intact
        assert r.close is False and r.body is None and r.mode == "user" and r.prompt == "dev$"

    def test_confirm_default_cancels_unknown_answer(self, tmp_path):
        shell = _shell(_platform(tmp_path, _CONFIRM_CLOSE_CMD))
        pending = _fire(shell, "reload")
        r = shell.complete_challenge(pending, "maybe")  # not in `on` → default {} → cancel
        assert r.close is False and r.body is None

    def test_confirm_output_body_on_enter(self, tmp_path):
        shell = _shell(_platform(tmp_path, _CONFIRM_OUTPUT_CMD))
        pending = _fire(shell, "save")
        r = shell.complete_challenge(pending, "")  # accept default filename
        assert r.body == "[OK]" and r.close is False and r.mode == "user"

    def test_confirm_default_output_on_typed_filename(self, tmp_path):
        shell = _shell(_platform(tmp_path, _CONFIRM_OUTPUT_CMD))
        pending = _fire(shell, "save")
        r = shell.complete_challenge(pending, "myfile")  # any filename → default → build
        assert r.body == "[OK]"

    def test_confirm_is_running_clear_closes(self, tmp_path):
        # Same shutdown observation as password (both stages share one close contract).
        shell = _shell(_platform(tmp_path, _CONFIRM_OUTPUT_CMD))
        pending = _fire(shell, "save")
        shell.is_running.clear()
        assert shell.complete_challenge(pending, "").close is True

    def test_confirm_new_mode_transitions(self, tmp_path):
        # A confirm action can transition mode (the `elif action.new_mode` branch).
        shell = _shell(_platform(tmp_path, _CONFIRM_MODE_CMD))
        pending = _fire(shell, "switchmode")
        r = shell.complete_challenge(pending, "e")
        assert r.mode == "enable" and r.prompt == "dev#" and r.body is None and r.close is False

    def test_confirm_new_mode_with_output(self, tmp_path):
        # `new_mode` + `output` compose (the relaxation over a plain transition).
        shell = _shell(_platform(tmp_path, _CONFIRM_MODE_CMD))
        pending = _fire(shell, "switchmode")
        r = shell.complete_challenge(pending, "b")
        assert r.mode == "enable" and r.body == "[OK]" and r.close is False

    def test_confirm_no_default_cancels_unknown(self, tmp_path):
        # `on` miss + no `default:` authored → `action is None` → a plain cancel
        # (distinct from a `default: {}` cancel action; both stay put).
        shell = _shell(_platform(tmp_path, _CONFIRM_MODE_CMD))
        pending = _fire(shell, "switchmode")
        r = shell.complete_challenge(pending, "zzz")
        assert r.close is False and r.body is None and r.mode == "user" and r.prompt == "dev$"


# --------------------------------------------------------------------- creds wiring
class TestChallengeCredsWiring:
    def test_secret_threads_from_inventory_to_shell(self):
        """Inventory `secret` reaches the per-session shell (`_secret`) via
        Host -> server -> `_build_shell`, alongside username / password (§5 table)."""
        net = SimNOS(inventory=build_inventory("linux", secret="my-enable-secret"))
        net.start()
        try:
            server = net.hosts["device"].server
            assert server is not None
            shell = server._build_shell()
            assert shell._secret == "my-enable-secret"
            assert shell._password == TEST_PASSWORD
            assert shell._username == TEST_USERNAME
        finally:
            net.stop()

    def test_secret_defaults_to_none(self):
        """No inventory `secret` -> the shell's `_secret` is None (password fallback)."""
        net = SimNOS(inventory=build_inventory("linux"))
        net.start()
        try:
            server = net.hosts["device"].server
            assert server is not None
            assert server._build_shell()._secret is None
        finally:
            net.stop()


# --------------------------------------------------------------------- wire (netmiko)
class TestChallengeWire:
    def test_linux_enable_succeeds(self):
        """`conn.enable()` on linux runs `sudo -s`, answers the password prompt and
        reaches root — the full challenge wire end to end (design §6 本命)."""
        net = SimNOS(inventory=build_inventory("linux"))
        net.start()
        try:
            port = net.hosts["device"].port
            conn = ConnectHandler(
                host="localhost",
                username=TEST_USERNAME,
                password=TEST_PASSWORD,
                port=port,
                device_type=netmiko_device_type_of("linux"),
                secret=TEST_PASSWORD,  # sudo asks for the login password (auth: password)
            )
            try:
                assert conn.check_enable_mode() is False  # user mode ($)
                conn.enable()
                assert conn.check_enable_mode() is True  # root (#)
            finally:
                conn.disconnect()
        finally:
            net.stop()

    def test_linux_enable_wrong_secret_raises(self):
        """A wrong sudo password never reaches root, so netmiko's enable() raises."""
        net = SimNOS(inventory=build_inventory("linux"))
        net.start()
        try:
            port = net.hosts["device"].port
            conn = ConnectHandler(
                host="localhost",
                username=TEST_USERNAME,
                password=TEST_PASSWORD,
                port=port,
                device_type=netmiko_device_type_of("linux"),
                secret="wrong-secret",
            )
            try:
                conn.read_timeout_override = 3.0  # fail fast instead of the 10s default
                with pytest.raises(ValueError):
                    conn.enable()
            finally:
                conn.disconnect()
        finally:
            net.stop()

    def test_alcatel_sros_enable_admin_per_mode(self):
        """Pin the C2 per-mode contract for alcatel_sros `enable-admin` (design §6, 案D).

        NokiaSros.check_enable_mode re-sends `enable-admin` and, on seeing the
        password prompt, escapes it with a bare Enter (RETURN) before reading the
        prompt back. That empty answer is a single failed attempt (C1) that leaves
        the user prompt intact, so the escape does not hang:

        - user mode: `enable-admin` fires the challenge → check_enable_mode's bare
          Enter fails it → back at `>` → "in admin mode" absent → check returns False
        - after enable() supplies the secret → admin (enable) mode `#`
        - enable mode: `enable-admin` does NOT fire (challenge.mode=[user]); its
          `output` carries "in admin mode" so check_enable_mode returns True
        """
        net = SimNOS(inventory=build_inventory("alcatel_sros"))
        net.start()
        try:
            port = net.hosts["device"].port
            conn = ConnectHandler(
                host="localhost",
                username=TEST_USERNAME,
                password=TEST_PASSWORD,
                port=port,
                device_type=netmiko_device_type_of("alcatel_sros"),
                secret=TEST_PASSWORD,  # no inventory secret → server falls back to password (案F)
            )
            try:
                assert conn.check_enable_mode() is False  # bare-Enter escape, still user mode
                conn.enable()
                assert conn.check_enable_mode() is True  # enable-mode output carries "in admin mode"
            finally:
                conn.disconnect()
        finally:
            net.stop()
