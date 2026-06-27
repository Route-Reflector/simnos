"""Command abbreviation + Tab token-grain completion (#303 / P3-2).

The shell resolves an abbreviated command line (``sh ver`` -> ``show version``)
only after the exact-match lookup misses, so a full command's wire stays
byte-identical (the byte-parity goldens pin that separately). These tests cover:

1. full commands are never diverted to abbreviation (positive invariant);
2. genuinely unknown input still answers with ``_default_`` (negative fixture);
3. abbreviation / ambiguous / incomplete resolution on real cisco_ios data;
4. alias safety on real arista_eos data (canonical-only candidate set);
5. multi-space full commands resolve via ``split()`` collapse;
6. Tab completion returns whole-line names, token-grain;
7. the ``_ambiguous_`` / ``_incomplete_`` specials are overridable and flow
   through the normal dispatch pipeline (handler override is None-safe, and the
   specials never transition or close);
8. abbreviation works on the shared ``_dispatch_general`` core both transports use.
"""

import dataclasses
import threading

import pytest

from simnos.core.nos import Nos
from simnos.core.resolved_command import ResolvedCommand, ResolvedOutput
from simnos.plugins.nos import nos_plugins
from simnos.plugins.servers.async_session import _complete, _LineEditor
from simnos.plugins.shell.cmd_shell import CMDShell
from tests.plugins.test_async_session import _FakeTransport
from tests.plugins.test_ssh_line_editor import _feed

# The packaged Cisco-style defaults (BASIC_COMMANDS), after the adapter collapses
# the escaped ``{{input}}`` to a literal ``{input}`` and dispatch substitutes it.
AMBIGUOUS_PREFIX = '% Ambiguous command:  "'
INCOMPLETE_DIAG = "% Incomplete command."

# A small, representative cross-platform sweep: A3-only (cisco_ios), A3 + legacy
# py overrides (arista_eos), and two more NOS families, so the special-command
# invariants are not pinned on cisco_ios alone.
SWEEP_PLATFORMS = ["cisco_ios", "arista_eos", "huawei_smartax", "juniper_junos"]


def _shell(name: str) -> CMDShell:
    """A real merged-platform shell for `name`, ready to dispatch."""
    is_running = threading.Event()
    is_running.set()  # otherwise _dispatch_general reports server shutdown
    return CMDShell(
        nos=Nos(filename=nos_plugins[name]),
        nos_inventory_config={},
        base_prompt="device",
        is_running=is_running,
    )


def _legacy_shell(commands: dict) -> CMDShell:
    """A legacy (3-prompt) shell built from an in-memory command dict."""
    nos = Nos()
    nos.from_dict(
        {
            "name": "synthetic",
            "initial_prompt": "{base_prompt}>",
            "enable_prompt": "{base_prompt}#",
            "config_prompt": "{base_prompt}(config)#",
            "commands": commands,
        }
    )
    is_running = threading.Event()
    is_running.set()
    return CMDShell(
        nos=nos,
        nos_inventory_config={},
        base_prompt="device",
        is_running=is_running,
    )


def _enable(shell: CMDShell) -> CMDShell:
    """Put a cisco-like shell in enable mode (where the show tree is valid)."""
    shell.current_mode = "enable"
    return shell


# --------------------------------------------------------------- 1. positive invariant
def test_full_commands_never_diverted_to_abbreviation():
    """Every real command resolves by exact match, never via abbreviation.

    Abbreviation only fires on an exact-match miss, so a full command's dispatch
    output is whatever the exact ResolvedCommand produces — never an ambiguous /
    incomplete diagnostic. Pinned across the sweep so the byte-parity-protected
    full-command path cannot silently regress when abbreviation is in play.
    """
    for platform in SWEEP_PLATFORMS:
        shell = _shell(platform)
        for name, cmd in list(shell.commands.items()):
            if name.startswith("_") and name.endswith("_"):
                continue  # specials are not dispatched by name
            shell.current_mode = next(iter(cmd.modes)) if cmd.modes else shell.platform.initial_mode
            body, close = shell._dispatch_general(name)
            assert body != INCOMPLETE_DIAG, f"{platform}:{name!r} fell through to incomplete"
            assert not (body or "").startswith(AMBIGUOUS_PREFIX), f"{platform}:{name!r} fell through to ambiguous"
            if cmd.exit:
                assert close is True
            elif cmd.output.kind in ("literal", "template") and not cmd.variants:
                # exact-match output, unperturbed by the abbreviation machinery
                assert body == cmd.output.render(shell.base_prompt)


# --------------------------------------------------------------- 2. negative fixture
# `(platform, mode, input, reason)` — inputs that must stay `_default_`, NOT be
# coerced into a command / ambiguous / incomplete by abbreviation. Seeded from
# the cisco_ios byte-parity golden's unknown-command steps (`no such command`,
# `exit` out-of-mode) plus a few clearly-foreign tokens.
NEGATIVE_FIXTURE = [
    ("cisco_ios", "enable", "no such command", "golden step 8 unknown -> _default_"),
    ("cisco_ios", "enable", "exit", "golden step 12: exit is config-only -> _default_"),
    ("cisco_ios", "enable", "zzz", "foreign single token"),
    ("cisco_ios", "enable", "frobnicate the widget", "foreign multi token"),
    ("arista_eos", "enable", "configure t", "alias long-form abbreviation is not canonical -> _default_"),
    ("arista_eos", "enable", "wibble", "foreign single token"),
]


@pytest.mark.parametrize(("platform", "mode", "line", "reason"), NEGATIVE_FIXTURE)
def test_unknown_input_stays_default(platform, mode, line, reason):
    shell = _shell(platform)
    shell.current_mode = mode
    expected = shell.commands["_default_"].output.render(shell.base_prompt)
    body, _close = shell._dispatch_general(line)
    assert body == expected, reason


# --------------------------------------------------------------- 3. abbreviation positive (cisco_ios)
@pytest.mark.parametrize(
    ("line", "expect"),
    [
        ("sh ver", "command"),  # show version
        ("conf t", "command"),  # configure terminal (canonical = full form)
        ("sh ip int br", "command"),  # show ip interface brief
        ("s i i b", "ambiguous"),  # 's' (and 'i') match multiple commands
        ("sh ip", "incomplete"),  # strict prefix of longer commands, no full match
    ],
)
def test_abbreviation_resolution_cisco(line, expect):
    shell = _enable(_shell("cisco_ios"))
    kind, _payload = shell._resolve_abbreviation(line)
    assert kind == expect


def test_abbreviation_dispatches_expected_output_cisco():
    shell = _enable(_shell("cisco_ios"))
    # `sh ip int br` resolves to the same body as the full command.
    abbrev, _ = shell._dispatch_general("sh ip int br")
    full, _ = shell._dispatch_general("show ip interface brief")
    assert abbrev == full
    # ambiguous / incomplete render the (input-interpolated) diagnostics.
    amb, amb_close = shell._dispatch_general("s i i b")
    assert amb == '% Ambiguous command:  "s i i b"'
    assert amb_close is False
    inc, inc_close = shell._dispatch_general("sh ip")
    assert inc == INCOMPLETE_DIAG
    assert inc_close is False


# --------------------------------------------------------------- 4. alias safety (arista_eos real data)
def test_alias_safety_arista():
    """Canonical-only candidates: word-variant aliases neither falsely-ambiguate
    nor falsely-prune, and a long-form alias of a short canonical does not
    abbreviation-resolve (a documented data-dependent limitation, Decision 5)."""
    shell = _enable(_shell("arista_eos"))
    # canonical `terminal length 0`, alias `term length 0`: no false ambiguity.
    kind, payload = shell._resolve_abbreviation("te l 0")
    assert kind == "command"
    assert isinstance(payload, ResolvedCommand)
    assert payload.canonical_name == "terminal length 0"
    # `term l 0` (abbreviating the alias's own surface, which shares the canonical
    # prefix) also resolves to the canonical.
    kind, _ = shell._resolve_abbreviation("term l 0")
    assert kind == "command"
    # canonical is the SHORT form `conf t`; the long-form alias `configure
    # terminal` resolves only by exact match, its abbreviation does not.
    assert shell.commands.get("configure terminal") is not None  # exact alias entry exists
    kind, _ = shell._resolve_abbreviation("configure t")
    assert kind == "none"  # -> _default_, not the config-mode transition


# --------------------------------------------------------------- 5. multi-space full command
def test_multi_space_full_command_resolves_cisco():
    """`split()` collapses runs of spaces, so a double-spaced full command (a
    miss for the exact dict lookup) resolves through abbreviation — more faithful
    than v2's `_default_`, and outside the byte-parity contract (the input was
    not an exact match)."""
    shell = _enable(_shell("cisco_ios"))
    spaced, _ = shell._dispatch_general("show  version")
    full, _ = shell._dispatch_general("show version")
    assert spaced == full


# --------------------------------------------------------------- 6. Tab token-grain completion
def test_completion_token_grain_cisco():
    shell = _enable(_shell("cisco_ios"))
    # leading-token abbreviation expands to whole-line full command names
    assert shell.completion_candidates("sh ip i") == ["show ip interface", "show ip interface brief"]
    # trailing space lists the next token's candidates (head fully consumed)
    trailing = shell.completion_candidates("sh ip ")
    assert "show ip route" in trailing
    assert all(c.startswith("show ip ") for c in trailing)
    # exact-prefix (P3-1 behaviour) still works
    assert "show version" in shell.completion_candidates("show v")
    # empty prefix lists every current-mode canonical command (and only canonical)
    everything = shell.completion_candidates("")
    assert "show version" in everything
    assert everything == sorted(everything)
    # an ambiguous *head* (a committed, non-last token matching multiple
    # commands) returns nothing — Tab stays silent where dispatch would diagnose.
    # ("s i " trailing-space: head ["s","i"]; position 1 "i" matches
    # interface/inventory/ip/ipv6/isdn/isis -> ambiguous.)
    assert shell.completion_candidates("s i ") == []


def test_completion_is_canonical_only_cisco():
    """Tab lists canonical names, not aliases (asymmetric with the help listing)."""
    shell = _enable(_shell("arista_eos"))
    everything = shell.completion_candidates("")
    assert "conf t" in everything  # canonical
    assert "configure terminal" not in everything  # alias is hidden from Tab


# --------------------------------------------------------------- 7. overridable specials + handler
def test_specials_overridable_literal():
    shell = _legacy_shell(
        {
            "clear counters": {"output": "cleared", "prompt": "{base_prompt}#"},
            "clock set": {"output": "set", "prompt": "{base_prompt}#"},
            "show version": {"output": "v1", "prompt": "{base_prompt}#"},
            # literal override carrying the placeholder (escaped for the adapter)
            "_ambiguous_": {"output": "AMB <{{input}}>", "help": ""},
            "_incomplete_": {"output": "INC!", "help": ""},
        }
    )
    shell.current_mode = "enable"
    amb, _ = shell._dispatch_general("cl")  # clear vs clock -> ambiguous
    assert amb == "AMB <cl>"  # custom wording + {input} interpolation
    inc, _ = shell._dispatch_general("show")  # strict prefix of "show version"
    assert inc == "INC!"


def test_special_handler_override_is_none_safe_and_no_double_substitution():
    """A handler-kind `_ambiguous_` override flows through the normal dispatch
    pipeline (the cmd-swap, not a render-only helper), so `render()` returning
    None for a handler does not crash, and a literal `{input}` the handler emits
    itself is NOT re-substituted (handler formats from its own `command` arg)."""
    shell = _legacy_shell(
        {
            "clear counters": {"output": "cleared", "prompt": "{base_prompt}#"},
            "clock set": {"output": "set", "prompt": "{base_prompt}#"},
        }
    )
    shell.current_mode = "enable"

    def handler(device, *, base_prompt, current_mode, current_prompt, command):
        # body deliberately contains a literal "{input}" to prove it is NOT replaced
        return f"H:{command} {{input}}"

    shell.commands = {
        **shell.commands,
        "_ambiguous_": dataclasses.replace(
            shell.commands["_ambiguous_"], output=ResolvedOutput(kind="handler", handler=handler)
        ),
    }
    body, close = shell._dispatch_general("cl")  # ambiguous -> handler special
    assert body == "H:cl {input}"  # handler ran, {input} left intact (no double sub)
    assert close is False


def test_special_none_kind_override_does_not_crash():
    """A none-kind (empty) `_ambiguous_` override yields no body and never the
    `None.replace` crash the render-only helper would have hit."""
    shell = _legacy_shell(
        {
            "clear counters": {"output": "cleared", "prompt": "{base_prompt}#"},
            "clock set": {"output": "set", "prompt": "{base_prompt}#"},
        }
    )
    shell.current_mode = "enable"
    shell.commands = {
        **shell.commands,
        "_ambiguous_": dataclasses.replace(shell.commands["_ambiguous_"], output=ResolvedOutput(kind="none")),
    }
    body, close = shell._dispatch_general("cl")
    assert body is None
    assert close is False


@pytest.mark.parametrize("platform", SWEEP_PLATFORMS)
def test_packaged_specials_never_transition_or_close(platform):
    """The packaged `_ambiguous_` / `_incomplete_` defaults must not transition
    the mode or close the session — they ride the normal dispatch pipeline, so
    an authoring slip that set `new_mode` / `exit` would otherwise leak through."""
    shell = _shell(platform)
    for cmd_name in ("_ambiguous_", "_incomplete_"):
        cmd = shell.commands[cmd_name]
        assert cmd.new_mode is None
        assert cmd.exit is False
        assert not cmd.modes  # valid in every mode (no prompt)


# --------------------------------------------------------------- 8. shared dispatch core path
def test_abbreviation_through_dispatch_general_core():
    """Both transports share `_dispatch_general`, so abbreviation works on the
    shared core regardless of transport — line editing stays SSH-only (pinned in
    test_ssh_line_editor), but the resolution itself is path-independent
    (cmd.Cmd `default` adapter removed in #303 P3-3)."""
    shell = _enable(_shell("cisco_ios"))
    body, close = shell._dispatch_general("sh ver")
    assert close is False
    assert body is not None
    assert "Cisco IOS" in body


def test_abbreviation_on_ssh_dispatch_path():
    """The push dispatch core (SSH) resolves abbreviations and reports them via
    DispatchResult without writing to stdout."""
    shell = _enable(_shell("cisco_ios"))
    result = shell.dispatch("s i i b")  # ambiguous
    assert result.body == '% Ambiguous command:  "s i i b"'
    assert result.close is False


def test_complete_abbreviated_leading_token_through_real_complete():
    """End-to-end: a real shell's token-grain `completion_candidates` drives the
    SSH `_complete` line-replacement so a leading-token abbreviation expands the
    whole line (#303 P3-2, claude 1st#3). The async_session `_complete` unit
    tests use a flat-`startswith` stub, so this is the only place the real
    token-grain completion meets the real line editor."""
    shell = _enable(_shell("cisco_ios"))
    tr = _FakeTransport([])
    editor = _LineEditor(tr.send)
    _feed(editor, b"sh ver")  # leading-token abbreviation, unique -> show version
    _complete(editor, shell, tr)
    assert editor.take_line() == b"show version "


def test_abbreviation_handler_receives_typed_line():
    """A handler reached via abbreviation gets the *typed* (abbreviated) line as
    its `command`, consistent with exact dispatch (the handler always sees the
    literal typed line; the wire echo shows what the user typed). Pinned so the
    contract is intentional rather than incidental (codex 1st#4)."""
    shell = _legacy_shell({"show version": {"output": "v", "prompt": "{base_prompt}#"}})
    shell.current_mode = "enable"
    seen = []

    def handler(device, *, base_prompt, current_mode, current_prompt, command):
        seen.append(command)
        return "ok"

    shell.commands = {
        **shell.commands,
        "show version": dataclasses.replace(
            shell.commands["show version"], output=ResolvedOutput(kind="handler", handler=handler)
        ),
    }
    body, _ = shell._dispatch_general("sh ver")  # abbreviation -> handler command
    assert body == "ok"
    assert seen == ["sh ver"]  # the typed abbreviation, not the canonical "show version"
