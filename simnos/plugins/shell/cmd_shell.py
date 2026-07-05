"""
Custom shell class to interact with NOS.
"""

from dataclasses import dataclass, replace
import hashlib
import logging
import os
import random
import string
import threading
import traceback
from typing import TYPE_CHECKING, cast

from jinja2 import TemplateSyntaxError

from simnos.core.command_contract import CommandHandler
from simnos.core.nos import Nos
from simnos.core.overlay_loader import resolve_overlay
from simnos.core.platform_loader import load_platform_dir, resolve_modes, resolve_transitions
from simnos.core.pydantic_models import ModelInventoryCommand, NosPluginConfig
from simnos.core.resolved_command import (
    NO_OUTPUT,
    ModeDef,
    ResolvedChallenge,
    ResolvedCommand,
    ResolvedOutput,
    ResolvedPlatform,
    compile_template,
)
from simnos.core.values_loader import validate_render_values

# `nos_pkg` is the package module (for `__path__`); the `__init__` arg `nos` is a
# `Nos` instance that would shadow a plain `from simnos.plugins import nos`, so the
# module is bound under a distinct name (#281 / D5, 2nd round gemini#1/claude#1).
import simnos.plugins.nos as nos_pkg
from simnos.plugins.nos import nos_plugins
from simnos.plugins.shell.utils import (
    get_files_changed,
    get_files_lasttime_changed,
    get_files_under_roots,
    platform_watch_roots,
)

if TYPE_CHECKING:
    from simnos.core.host import HostRenderConfig
    from simnos.core.pydantic_models import ModelVariantsPolicy

log = logging.getLogger(__name__)


def _stable_hash(seed: int, host: str, command: str) -> int:
    """Deterministic hash for seeded variant selection (#287 / D6, gemini#3).

    ``hash()`` is salted per-process by ``PYTHONHASHSEED`` so it cannot be used
    for a selection that must be reproducible across runs/tools. sha256 over the
    three terms pins the algorithm; the caller takes ``% N``. The host term is
    the stable inventory id (``Host.name``), not ``base_prompt`` (overridable /
    shared), and the command term is the canonical name so all aliases of one
    command hash alike (#287 / D6 E, codex#1). The terms are joined on a NUL byte
    (which cannot occur in a command name or a sane host id) rather than ``:`` so
    no host/command pair can collide by shifting the separator (1st round
    claude#4).
    """
    digest = hashlib.sha256(f"{seed}\x00{host}\x00{command}".encode()).hexdigest()
    return int(digest, 16)


def _basic_command(name: str, *, output: str | None = None, help: str = "", exit: bool = False) -> ResolvedCommand:
    """Build one native BASIC entry (#317 / P-3, 案F): literal output, all modes."""
    return ResolvedCommand(
        name=name,
        modes=frozenset(),  # empty = valid in every mode
        new_mode=None,
        output=ResolvedOutput(kind="literal", text=output) if output is not None else NO_OUTPUT,
        variants=(),
        help=help,
        exit=exit,
        type="simnos",
    )


# Special, always-present commands, in native `ResolvedCommand` form (#317 / P-3,
# 案F — the legacy-adapter round trip is gone). They sit under every other inflow
# in the merge, so platform data / overlay / inventory can override them. Frozen
# dataclasses: `build_resolved_platform` shares them without copying.
BASIC_COMMANDS: dict[str, ResolvedCommand] = {
    "exit": _basic_command("exit", help="Exit commands shell", exit=True),
    "_default_": _basic_command(
        "_default_",
        output="Unknown command",
        help="Output to print for unknown commands",
    ),
    # Abbreviation diagnostics (#303 / P3-2). Overridable specials like
    # `_default_` — the default wording is Cisco IOS style (no captured oracle
    # exists, so it follows public IOS documentation; re-pin if a capture is
    # obtained), and huawei/junos can override it from platform data. The
    # dispatcher fills the literal `{input}` placeholder with the typed line via
    # `str.replace` — a plain single-brace literal now that the entry is born a
    # `ResolvedOutput` (the `{{input}}` escape the legacy adapter's
    # `str.format`-field detection forced is gone, #317 / P-3). An override may
    # carry `{input}` as literal / A3 `.j2` text or via a handler (which formats
    # itself from its `command` argument).
    "_ambiguous_": _basic_command(
        "_ambiguous_",
        output='% Ambiguous command:  "{input}"',
        help="Output for an ambiguous command abbreviation",
    ),
    "_incomplete_": _basic_command(
        "_incomplete_",
        output="% Incomplete command.",
        help="Output for an incomplete command abbreviation",
    ),
}

# Wire response when a command handler (callable output) crashes. Real NOSes
# never print Python tracebacks, and clients (Netmiko/KeroRoute integration
# tests) must not be handed one to parse — the full traceback goes to the
# server log instead (#241 / D4).
HANDLER_ERROR_OUTPUT = "% Internal error"


def build_resolved_platform(
    nos: "Nos", inventory_commands: dict, render_config: "HostRenderConfig | None" = None
) -> ResolvedPlatform:
    """Merge the command inflows into one `ResolvedPlatform` (#264 / D6).

    The shell consumes one representation regardless of authoring form. Inflows
    merge under one precedence — BASIC < platform data < overlay < inventory,
    later inflows winning. The platform's modes and static commands come from
    its A3 dir (`nos.resolved_platform`); they sit over the native BASIC
    entries. The user overlay (#286), when the host opted in, slots between the
    platform data and inventory so a captured `.txt` overrides the packaged
    output but a session-local inventory command still wins.

    An A3 platform dir is required (#317 P-4 — the legacy py-dict adapter is
    gone): a `Nos` that never loaded one is rejected loudly here, which
    surfaces at `Host.start` via `build_shared_platform` (fail at startup).

    The inventory commands arrive in their A3-dialect authoring form
    (`ModelInventoryCommand`, #317 / P-3) and are normalized here against the
    platform's modes.

    Pure (no session state): the result is per-host invariant, so the server
    builds it once and shares it across connections.
    """
    a3 = nos.resolved_platform
    if a3 is None:
        # A py-only Nos keeps the constructor-default name (`NAME` is no longer
        # read), so name the loaded source paths too — the actionable pointer.
        raise ValueError(
            f"platform {nos.name!r} has no A3 platform dir (resolved_platform is unset; "
            f"loaded sources: {nos.sources or 'none'}) — py-only platforms were removed (#317 P-4); "
            "ship a `platforms/<name>/` dir (platform.yaml + commands/) and keep the py module for "
            "the device class / handlers only"
        )
    commands: dict[str, ResolvedCommand] = dict(BASIC_COMMANDS)
    commands.update(a3.commands)
    # User overlay (#286): a host opts in via inventory `overlay.override_commands`;
    # the overlay dir was resolved + existence-checked by Host. Applied before
    # inventory (last-wins precedence, Decision 14).
    if render_config is not None and render_config.overlay_root and render_config.override_commands:
        overlay_commands = resolve_overlay(
            render_config.overlay_root, a3, override_commands=render_config.override_commands
        )
        log.debug("overlay overrides %d command(s): %s", len(overlay_commands), sorted(overlay_commands))
        commands.update(overlay_commands)
    commands.update(_resolve_inventory_commands(inventory_commands, a3.modes))
    # Bind any A3 `handler:` refs to the platform's py handler namespace now that
    # every inflow is merged (an overlay/inventory override may have replaced a
    # handler command with a literal, so bind the final state) (#317 / P-1).
    _bind_handler_refs(commands, nos.handlers)
    # Carry `auth` so the merged platform mirrors the A3 source — auth is consumed
    # via `nos.auth`, but dropping it would re-introduce the silent-dead-end
    # asymmetry the auth wiring fixed (2nd round codex/claude #3).
    return ResolvedPlatform(
        modes=a3.modes,
        initial_mode=a3.initial_mode,
        commands=commands,
        auth=a3.auth,
        # Carry the A3 paging prompt through the merge — otherwise a per-host
        # merged platform would silently fall back to the default `--More--` even
        # when the platform authored its own (#307 / P3-4).
        more_prompt=a3.more_prompt,
    )


def _resolve_inventory_commands(inventory_commands: dict, modes: dict[str, ModeDef]) -> dict[str, ResolvedCommand]:
    """Normalize the inventory command inflow to `ResolvedCommand`s (#317 / P-3, 案E).

    The entries arrive as raw mappings — the inventory file was schema-validated
    at `SimNOS` load, but a direct ``CMDShell(nos_inventory_config=...)`` caller
    bypasses that — so they are re-parsed through `NosPluginConfig` here: the
    typed model is the one loud boundary for both paths (typed-model-first,
    #287 / D6 K), and it owns the `_default_` special rule. Mode names are then
    validated against the *actual* platform modes, which only the merge knows.
    """
    if not inventory_commands:
        return {}
    parsed = NosPluginConfig(commands=inventory_commands).commands or {}
    mode_names = frozenset(modes)
    return {name: _resolve_inventory_command(name, model, mode_names) for name, model in parsed.items()}


def _resolve_inventory_command(name: str, model: ModelInventoryCommand, mode_names: frozenset[str]) -> ResolvedCommand:
    """Resolve one validated inventory entry (mirrors the A3 loader's `_resolve_command`)."""
    where = f"inventory command {name!r}"
    cmd_modes = resolve_modes(name, model.mode, mode_names, where="inventory command")
    if model.new_mode is not None and model.new_mode not in mode_names:
        raise ValueError(f"{where}: new_mode {model.new_mode!r} not in platform modes {sorted(mode_names)}")

    if model.output is not None:
        output = ResolvedOutput(kind="literal", text=model.output)
    elif model.output_template is not None:
        try:
            template, required = compile_template(model.output_template)
        except TemplateSyntaxError as e:
            raise ValueError(f"{where}: output_template has a jinja2 syntax error: {e}") from e
        output = ResolvedOutput(kind="template", template=template, required_vars=required)
        # An inventory template has no sidecar values, so anything beyond
        # `base_prompt` can never be satisfied — the shared build-time gate
        # rejects it at start instead of a mid-session render crash (#287 / D5).
        validate_render_values(output, name, source="inventory")
    else:
        output = NO_OUTPUT

    return ResolvedCommand(
        name=name,
        modes=cmd_modes,
        new_mode=model.new_mode,
        output=output,
        variants=(),
        help=model.help or "",
        exit=bool(model.exit),
        # Session-local, user-authored — classified like an overlay-added
        # command, not packaged data (#317 / P-3).
        type="custom",
        transitions=resolve_transitions(name, model.transitions, cmd_modes, mode_names, where="inventory command"),
    )


def _bind_handler_refs(commands: dict[str, ResolvedCommand], handlers: dict[str, CommandHandler]) -> None:
    """Bind A3 ``handler:`` refs to callables from the py handler namespace (#317 / P-1).

    An A3-authored handler command carries ``output.kind == "handler"`` with
    ``handler=None`` and a ``handler_ref`` name; the py module that ships the
    platform's device class exposes the actual callables (`nos.handlers`). Resolve
    each ref here — at the merge boundary, once — and replace the command with a
    bound copy. In-place on the fresh merge dict: each `ResolvedCommand` is frozen,
    so binding means ``replace`` on the command and its output.

    An unresolved ref is loud (a `ValueError` surfacing at ``Host.start`` /
    ``build_shared_platform``): "fail at startup", never a silent no-output
    command.
    """
    for name, cmd in commands.items():
        out = cmd.output
        if out.kind == "handler" and out.handler is None and out.handler_ref is not None:
            handler = handlers.get(out.handler_ref)
            if handler is None:
                raise ValueError(
                    f"command {name!r}: handler {out.handler_ref!r} is not defined in the platform's py handler "
                    f"namespace (available: {sorted(handlers)}) — a `handler:` command needs a py module that "
                    "defines it (#317 / P-1)"
                )
            commands[name] = replace(cmd, output=replace(out, handler=handler))


@dataclass(frozen=True)
class DispatchResult:
    """Structured result of one dispatched line (#297 / §3a).

    The push session driver turns this into wire bytes. The legacy
    ``cmd.Cmd.cmdloop`` / ``onecmd`` (removed in #303 P3-3) could not represent
    multi-line output, no output, session close, or a post-transition prompt in
    a single ``str``, so the I/O-independent dispatch core returns the pieces
    explicitly:

    - ``body``: text the driver renders line-by-line with ``newline``, or
      ``None`` for no output (empty line, EOF, a handler returning None).
      The driver suppresses it when ``close`` is set — the legacy
      ``default`` adapter never wrote a body on any close path.
    - ``prompt``: the prompt to show after this line (already reflects a mode
      transition applied during dispatch).
    - ``close``: the session should close after this line.
    - ``mode``: the mode after dispatch (observability / tests).
    """

    body: str | None
    prompt: str
    close: bool
    mode: str
    # Post-dispatch interactive sub-prompt to run before this result is rendered
    # (#338 / §3). None on every ordinary line; set only when a `challenge:`
    # command fired in a firing mode, in which case `body` is None / `close` is
    # False and the push driver runs the challenge sub-phase (`_run_challenge`)
    # then renders the `complete_challenge` result instead of this one.
    challenge: "PendingChallenge | None" = None


@dataclass(frozen=True)
class PendingChallenge:
    """A fired challenge the push driver must complete before rendering (#338 / §3).

    Stateless hand-off: the shell returns this on `DispatchResult.challenge`, the
    driver reads the password line (echo per `echo`) and calls back into
    `shell.complete_challenge(pending, entered)`. Holding the render-time
    `ResolvedChallenge` (frozen) fixes the wire prompt for this session, and
    `command` (the canonical name) lets `complete_challenge` name the command in a
    creds-unwired diagnostic (the entered value is never logged, R5).
    """

    spec: ResolvedChallenge
    command: str
    prompt_text: str
    echo: bool


class CMDShell:
    """
    Custom shell class to interact with NOS.
    """

    # Same value as the former ``cmd.Cmd.identchars``; ``_parseline`` reads
    # ``self.identchars`` to extract the leading command token, so it must be a
    # class attr now that the ``cmd.Cmd`` base is gone (#303 P3-3).
    identchars = string.ascii_letters + string.digits + "_"

    def __init__(
        self,
        nos,
        nos_inventory_config,
        base_prompt,
        is_running,
        intro="Custom SSH Shell",
        newline="\r\n",
        resolved_platform=None,
        render_config=None,
        page_default_rows=24,
        reload_lock=None,
        username=None,
        password=None,
        secret=None,
    ):
        self.nos: Nos = nos
        self.intro = intro
        self.base_prompt = base_prompt
        self.newline = newline
        self.is_running = is_running
        # Credentials for a `challenge:` command (#338). `username` renders a
        # sub-prompt like `[sudo] password for {{ username }}: `; `password` /
        # `secret` are the expected challenge answers (`auth: secret` falls back to
        # `password` when `secret` is None, 案F). All default to None for a direct
        # construction / legacy test that never exercises a challenge command.
        self._username: str | None = username
        self._password: str | None = password
        self._secret: str | None = secret
        # Paging (#307 / P3-4). `page_default_rows` is the fallback page height
        # (sys_config.paging.default_rows, wired through the server); `more_prompt`
        # is installed from the resolved platform in `_apply_platform`. The push
        # driver reads both, plus `paging_disabled` — a sticky per-session flag a
        # `disables_paging` command flips (the realism of `terminal length 0`).
        self.page_default_rows: int = page_default_rows
        self._paging_disabled: bool = False
        # Inventory-defined commands are a third inflow alongside BASIC and the
        # NOS data; kept in authoring form (A3 dialect, #317 / P-3) and
        # re-normalized against the freshly loaded modes on a hot-reload rebuild
        # (#264 / D6).
        self._inventory_commands: dict = nos_inventory_config.get("commands", {})
        # Per-host render config (overlay #286, variants_policy #287). Held so a
        # hot-reload `_rebuild` re-applies the overlay instead of dropping it
        # (#286 / C1); in hot-reload dev mode the shared snapshot is None so this
        # self-build path carries the overlay too.
        self._render_config: HostRenderConfig | None = render_config
        # Per-session variant state (#287 / D6, D7). Initialized BEFORE the first
        # `_apply_platform` below, because `_build_variant_maps` reads all three
        # (AttributeError guard, claude#5):
        #  - `_variant_indices`: canonical_name -> chosen index, fixed for the
        #    whole session (shared by every alias of a command).
        #  - `_variant_outputs`: cmd.name -> ResolvedOutput, rebuilt each apply
        #    against the latest commands (dispatch identity).
        #  - `_variants_policy` / `_host_name`: the policy + stable host id used
        #    to decide an index (host id, not base_prompt — D6 E).
        self._variant_indices: dict[str, int] = {}
        self._variant_outputs: dict[str, ResolvedOutput] = {}
        self._variants_policy: ModelVariantsPolicy | None = render_config.variants_policy if render_config else None
        self._host_name: str = render_config.host_name if render_config and render_config.host_name else base_prompt
        # Per-connection RNG for seed-less `select: random` — a fresh draw each
        # connection (true non-determinism, the realism opt-in; D6). Seeded
        # selection uses `_stable_hash` instead, not this RNG.
        self._connection_rng = random.Random()  # noqa: S311 — variant pick, not cryptographic
        # Per-host shared reload lock (#281 / D6): serializes the executor-thread
        # `reload_commands` against both a concurrent reload (another session of
        # this host) and this `__init__`'s self-build read below, all of which
        # touch the host-shared `self.nos`. The server injects one lock per host
        # (`Host.start` -> server kwarg); a direct construction / test gets a
        # private fallback. Established BEFORE the self-build so the read is
        # already protected.
        self._reload_lock: threading.Lock = reload_lock or threading.Lock()
        # The merged platform is per-host invariant (base_prompt is the host name,
        # nos/inventory are shared), so the server normalizes it once at
        # Host.start and passes it to every connection's shell (#264 / Impact —
        # normalize once, fail at startup). When not supplied (tests / direct
        # construction) the shell builds its own. A malformed prompt template
        # fails loudly here (the #172 lenient fallback is gone, #264 / D5). In
        # hot-reload dev mode the shared snapshot is None (`build_shared_platform`
        # returns None), so every connection self-builds from the live shared
        # `nos` — done under the reload lock so a concurrent executor reload does
        # not mutate `nos` mid-read (#281 / D6, gemini#1). `_build_shell` runs on
        # the shared event-loop thread, so a new connection contending here with an
        # in-flight reload briefly blocks the loop until the reload releases the
        # lock — dev-only (production passes a non-None shared platform, skipping
        # this branch entirely) and accepted as the cost of the no-mid-mutation
        # guarantee (#281 / Risks, 1st code review claude#1).
        if resolved_platform is None:
            with self._reload_lock:
                resolved_platform = build_resolved_platform(self.nos, self._inventory_commands, self._render_config)
        self._apply_platform(resolved_platform)
        # Hot-reload watcher state (#281 / D1, D2, D5). Built ONLY in dev hot-reload
        # mode so production (env off) does no walk and holds no snapshot — the
        # per-shell baseline replaces the #274 process-global consume-once snapshot.
        # `_watch_roots` is this platform's own subtree (per-platform watch, D2/D4),
        # derived from the registry; `.get` degrades gracefully for a platform with
        # no registry sources (e.g. a runtime-registered custom plugin). The baseline
        # snapshot is seeded here so the first command can already reflect an edit.
        self._watch_roots: list[str] = []
        self._reload_snapshot: dict[str, float] = {}
        self._package_root: str | None = None
        if os.environ.get("SIMNOS_RELOAD_COMMANDS"):
            self._package_root = nos_pkg.__path__[0]  # rollup root; module ref avoids the `nos` arg shadowing (D5)
            self._watch_roots = platform_watch_roots(nos_plugins.get(self.nos.name, []))
            self._reload_snapshot = get_files_lasttime_changed(get_files_under_roots(self._watch_roots))
            if not self._watch_roots:
                log.debug("hot-reload: no watch roots for platform %r (not in the registry?)", self.nos.name)

    @staticmethod
    def build_shared_platform(
        nos: Nos, nos_inventory_config: dict, render_config: "HostRenderConfig | None" = None
    ) -> ResolvedPlatform | None:
        """Build the per-host merged platform the server shares across connections.

        Called once at Host.start (by the server) so inventory/data errors fail
        there rather than on each connection, and so the normalization is not
        repeated per connection (#264 / Impact). `render_config` carries the host's
        overlay opt-in (#286) so the shared snapshot includes the overlay layer.

        Returns None when hot-reload is enabled (`SIMNOS_RELOAD_COMMANDS`): in
        that dev mode each connection must rebuild from the live `nos` so file
        edits propagate to new connections, so there is no shared snapshot (the
        per-shell `_render_config` carries the overlay through `_rebuild`).
        """
        if os.environ.get("SIMNOS_RELOAD_COMMANDS"):
            return None
        return build_resolved_platform(nos, nos_inventory_config.get("commands", {}), render_config)

    def _apply_platform(self, platform: ResolvedPlatform) -> None:
        """Install a (built or shared) platform + refresh session mode / prompt.

        Two-phase atomic commit (#287 / R8): everything that can raise — building
        the variant maps (validates `variants_policy.select` + variant pool
        lengths) and rendering the prompt — runs first against local candidates,
        touching no live state. Only once all of it has succeeded does the commit
        block install `commands` / variant maps / mode / prompt together. So a
        broken hot reload (bad `select`, mismatched pool, undefined mode prompt)
        leaves the running session intact, preserving `_rebuild`'s atomic
        contract. The commit block below MUST stay exception-free.

        This method owns RNG atomicity for the *whole* build/validate phase: a
        seedless-random variant decision advances `self._connection_rng`, and the
        prompt render runs *after* it, so the snapshot/rollback must span both —
        otherwise a prompt-render failure would roll back commands/maps but leak
        the consumed randomness (2nd round codex#2). On success the advances are
        kept (those variants are committed).
        """
        rng_state = self._connection_rng.getstate()
        try:
            # --- build/validate phase (may raise; live state untouched) ---
            new_indices, new_outputs = self._build_variant_maps(platform.commands)
            # Keep the user's current mode across a hot reload when it still exists;
            # otherwise (first build, or a reload that dropped the mode) start at the
            # platform's initial mode.
            candidate_mode = (
                self.current_mode if getattr(self, "current_mode", None) in platform.modes else platform.initial_mode
            )
            prompt = platform.modes[candidate_mode].render_prompt(self.base_prompt)
        except Exception:
            self._connection_rng.setstate(rng_state)  # failed build leaves no trace (commands untouched, RNG restored)
            raise
        # --- commit phase (exception-free) ---
        self.platform = platform
        self.commands = platform.commands
        self._variant_indices = new_indices
        self._variant_outputs = new_outputs
        self.current_mode = candidate_mode
        self.prompt = prompt
        # The pager prompt rides with the platform so a hot reload that swaps it
        # also refreshes the `--More--` string (#307 / P3-4).
        self.more_prompt = platform.more_prompt

    @property
    def paging_disabled(self) -> bool:
        """Whether a `disables_paging` command has turned paging off this session.

        Read by the push driver (`PushShell` protocol) before each response: once
        a `terminal length 0`-style command runs in-mode the flag stays set for
        the session (sticky; re-enabling is out of scope, #307 / P3-4).
        """
        return self._paging_disabled

    def _decide_variant_index(self, cmd: ResolvedCommand) -> int:
        """Pick the variant index for one variant-bearing command (#287 / D6).

        `select` is an int (fixed, deterministic — the default 0 reproduces the
        legacy `variants[0]`) or ``"random"``. Random with a seed is reproducible
        per host (`_stable_hash`, sticky across reconnects); random without a seed
        is a fresh draw per connection. An explicit out-of-range int is loud (no
        silent modulo, which would hide a config error — codex#2 3rd).
        """
        n = len(cmd.variants)  # caller only invokes this for variant-bearing commands (n > 0)
        policy = self._variants_policy
        sel = policy.select if policy else 0  # None policy -> select 0 (legacy-compatible default)
        if sel == "random":
            seed = policy.seed if policy else None  # policy is non-None on this branch (sel came from it)
            if seed is not None:
                return _stable_hash(seed, self._host_name, cmd.canonical_name) % n
            return self._connection_rng.randrange(n)
        if not 0 <= sel < n:
            raise ValueError(
                f"variants_policy.select={sel} out of range for {cmd.canonical_name!r} (valid: 0..{n - 1})"
            )
        return sel

    def _build_variant_maps(
        self, commands: dict[str, ResolvedCommand]
    ) -> tuple[dict[str, int], dict[str, ResolvedOutput]]:
        """Build candidate (indices, outputs) maps for a platform (#287 / D6, R8).

        Pure builder: reads `self._variant_indices` (carried session state) but
        mutates no `self.*`, so a raise here cannot corrupt the live session — the
        caller (`_apply_platform`) commits the returned maps only on success.

        - **indices** are keyed on `canonical_name` and the session keeps them
          fixed (existing canonicals are inherited, never re-decided on reload);
          a new variant-bearing canonical that appears on a hot reload is decided
          lazily, and a canonical that vanished is pruned.
        - **outputs** are keyed on `cmd.name` (dispatch identity) and rebuilt from
          the latest `commands` (codex#1 6th).
        - every command sharing a `canonical_name` must expose the same variant
          pool length, else the shared index is ambiguous — loud (codex#1 6th).
          A3 aliases inherit the target's pool via the loader's `replace`, so
          shipped data always matches; the check is a defensive guard.
        - an inherited **explicit int** index that a hot reload pushed out of
          range (the pool shrank below `select`) is loud, not silently wrapped —
          the same loud-on-out-of-range contract a fresh connect enforces, so the
          two paths stay consistent (2nd round gemini#1 / codex#1). **Random** has
          no fixed-index contract, so it refits with `% n` (D9) — and the refit is
          *written back* to the index map, so a later pool re-expansion cannot
          revive the pre-shrink index and flip-flop the session's choice (3rd
          round codex#1). For a seeded policy this means a session whose pool was
          resized no longer matches a fresh connect's ``hash % n`` — an
          acknowledged design caveat of hot-reload pool changes (D6).

        RNG atomicity for a seedless-random decision is owned by the caller
        (`_apply_platform` snapshots/rolls back across this build *and* the prompt
        render), so this builder does not roll back the RNG itself.
        """
        indices = dict(self._variant_indices)
        outputs: dict[str, ResolvedOutput] = {}
        pool_len: dict[str, int] = {}
        is_random = self._variants_policy is not None and self._variants_policy.select == "random"
        for cmd in commands.values():
            if not cmd.variants:
                continue
            canon = cmd.canonical_name
            n = len(cmd.variants)
            if pool_len.setdefault(canon, n) != n:
                raise ValueError(
                    f"variant pool length mismatch for canonical {canon!r}: "
                    f"{pool_len[canon]} vs {n} (aliases must share one pool)"
                )
            if canon not in indices:
                indices[canon] = self._decide_variant_index(cmd)
            idx = indices[canon]
            if not is_random and not 0 <= idx < n:
                raise ValueError(
                    f"variants_policy.select={idx} out of range for {canon!r} after a hot reload "
                    f"shrank its variant pool to {n} (valid: 0..{n - 1})"
                )
            idx = idx % n  # no-op for the in-range int validated above; refits only a stale random index (#287 / D9)
            if is_random:
                indices[canon] = idx  # persist the refit so a later re-expansion can't revive the stale index (codex#1)
            outputs[cmd.name] = cmd.variants[idx][1]
        # Prune indices for canonicals no longer present (hot reload dropped them).
        indices = {canon: i for canon, i in indices.items() if canon in pool_len}
        return indices, outputs

    def _rebuild(self) -> None:
        """Re-merge the inflows and install the result (hot-reload path).

        Atomic: `build_resolved_platform` raises before `_apply_platform` mutates
        anything, so a broken hot reload leaves the running session intact
        (#264 / D5, D6). Re-applies the host's overlay via `_render_config` so a
        hot reload does not silently drop it (#286 / C1).
        """
        self._apply_platform(build_resolved_platform(self.nos, self._inventory_commands, self._render_config))

    # `Nos` state `from_file` mutates; snapshotted per reload target so a target
    # that loads but fails to normalize can be rolled back (2nd round codex #1).
    _NOS_RELOAD_ATTRS = (
        "name",
        "auth",
        "device",
        "resolved_platform",
        # `_from_module` rebuilds `handlers` as a fresh dict, so snapshotting the
        # reference here rolls back a failed hot reload cleanly (#317 / P-1).
        "handlers",
        # `_record_source` builds `sources` as a fresh list for the same reason:
        # a target that loads but fails `_rebuild` must not stay in the
        # diagnostic source list (#317 / P-4, 2nd round 🦊#1 / 🐳#1).
        "sources",
    )

    def reload_commands(self, reload_targets: list):
        """Method to reload commands

        Lenient per file: hot reload is a dev feature and may observe a
        half-written or malformed plugin file (e.g. an editor's partial
        save, or a file that vanished after detection). One broken file
        must not kill the SSH session nor block reloading the remaining
        files — log and retry on the next change.

        `from_file` commits to `self.nos` *before* the merge re-validates it in
        `_rebuild`, so a platform that loads but fails normalization (e.g. an
        inventory command whose `mode` the reloaded platform no longer
        declares) would leave a broken platform in `self.nos` and re-fail every
        later file in the batch. Snapshot the mutated nos state and roll it
        back on failure to keep the per-file contract; `_rebuild` itself is
        atomic, so live `self.commands` is never touched by a failed reload
        (2nd round codex #1).

        The A3 platform parse is cached by `load_platform_dir`; drop that cache
        first so a reload re-reads the changed files instead of the stale parse
        (#264 / D6 cache bypass). No-op for py module reloads.

        `reload_targets` are reload units (A3 platform dirs / `.py` modules), not
        raw changed files (#274 / D1). Per-platform watch (#281 / D2) means a
        session only ever sees its own platform's subtree, so `reload_targets`
        cannot contain a sibling platform — the #274 ownership filter is gone as
        unreachable dead code (#281 / D7).

        Serialized by the per-host `_reload_lock` (#281 / D6): `self.nos` is shared
        by every session of this host, and dispatch runs on a bounded executor, so
        two sessions could otherwise reload concurrently and corrupt the shared
        `nos` (or race this method against a new connection's self-build read in
        `__init__`). The whole body — including `load_platform_dir.cache_clear()` —
        is under the lock: clearing the cache outside it would let session B drop
        the cache while session A is still populating from it, re-opening the stale
        parse window the cache bypass closes (#281 / D6, claude#2/codex#2).
        """
        with self._reload_lock:
            load_platform_dir.cache_clear()
            for target in reload_targets:
                snapshot_attrs = {attr: getattr(self.nos, attr) for attr in self._NOS_RELOAD_ATTRS}
                try:
                    self.nos.from_file(target)
                    self._rebuild()
                except Exception:
                    # Broad except, like the dispatch core's handler guard: any
                    # plugin error must not crash the session. Roll back the partial
                    # nos mutation so the broken file does not poison subsequent
                    # reloads, then log the traceback so a genuine plugin bug stays
                    # diagnosable.
                    for attr, value in snapshot_attrs.items():
                        setattr(self.nos, attr, value)
                    log.error(
                        "shell '%s' failed to hot-reload %r\n%s", self.base_prompt, target, traceback.format_exc()
                    )
                    continue

    def precmd(self, line):
        """Method to return line before processing the command"""
        # Two-part gate (#281, 1st code review gemini#1/claude#2): the env var
        # keeps the current "env off mid-session stops reloading" semantics, and
        # `_package_root is not None` proves `__init__` actually seeded the watcher
        # (env was on at construction). It also narrows `_package_root` to `str`
        # for `get_files_changed` without an `assert` — so a late env toggle-on
        # (no baseline seeded) or `python -O` degrades to a graceful no-op instead
        # of a `TypeError` deep in `resolve_reload_targets`. The diff runs against
        # this shell's own snapshot (per-shell, D1), then swaps in the returned one.
        if os.environ.get("SIMNOS_RELOAD_COMMANDS") and self._package_root is not None:
            reload_targets, self._reload_snapshot = get_files_changed(
                self._watch_roots, self._package_root, self._reload_snapshot
            )
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

    def _dispatchable_commands(self) -> list[tuple[str, ResolvedCommand]]:
        """(name, cmd) pairs dispatchable in the current mode (skip `_special_`).

        The single current-mode command source shared by the help listing
        (`_help_body`) and the SSH editor's Tab completion
        (`completion_candidates`, #303 P3-1), so both list exactly the commands
        that would actually dispatch right now.
        """
        return [
            (name, cmd)
            for name, cmd in self.commands.items()
            if not (name.startswith("_") and name.endswith("_")) and self._in_current_mode(cmd)
        ]

    def _abbrev_candidates(self) -> list[tuple[str, ResolvedCommand, list[str]]]:
        """Abbreviation resolution space: current-mode canonical commands (#303 P3-2).

        `_dispatchable_commands()` already applies the mode / `_special_` filter;
        this further keeps only `name == cmd.canonical_name` (the real commands,
        dropping aliases). Excluding alias surface tokens from the search space
        is what kills false ambiguity / false pruning between word-variant
        aliases of one canonical (e.g. `terminal length 0` real vs `term length
        0` alias). Each candidate carries its token list so callers narrow
        positionally. The canonical surface is the spelling the platform author
        chose as canonical (`canonical_name` = alias target name), not
        necessarily the longest form — so an alias's *partial* abbreviation
        resolves toward that canonical (cisco_ios canonical = full form; arista
        `conf t` canonical = short form).
        """
        return [(name, cmd, name.split()) for name, cmd in self._dispatchable_commands() if name == cmd.canonical_name]

    def _narrow(self, tokens: list[str]) -> tuple[str, list[tuple[str, ResolvedCommand, list[str]]]]:
        """Positionally narrow the canonical candidates by `tokens` (#303 P3-2).

        Returns ``(status, candidates)`` with status ``"ok"`` (narrowed, possibly
        still longer than the input), ``"ambiguous"`` (a position matches more
        than one distinct surface token), or ``"none"`` (nothing matches).

        Commands shorter than the input can never match, so they are pruned up
        front — this also keeps `c[2][j]` in range for the whole loop and stops a
        short command from pruning a longer one. At each position an exact token
        match wins over a strict-prefix match (so `ip` is not shadowed by `ipv6`).
        Because the candidate set is canonical-only, distinct surface tokens at a
        position mean distinct real commands = genuine ambiguity.
        """
        candidates = [c for c in self._abbrev_candidates() if len(c[2]) >= len(tokens)]
        if not candidates:
            return ("none", [])
        for j, itok in enumerate(tokens):
            matched = [c for c in candidates if c[2][j].startswith(itok)]
            if not matched:
                return ("none", [])
            exact = [c for c in matched if c[2][j] == itok]
            if exact:
                matched = exact  # all share this exact token -> never ambiguous here
            elif len({c[2][j] for c in matched}) > 1:
                return ("ambiguous", [])
            candidates = matched
        return ("ok", candidates)

    def _resolve_abbreviation(self, line: str) -> tuple[str, ResolvedCommand | str | None]:
        """Resolve an abbreviated command line, real-IOS style (#303 P3-2).

        Called only after the exact-match lookup misses, so full commands never
        reach here and their wire stays byte-identical. Returns ``(kind,
        payload)``:

        - ``("command", ResolvedCommand)``: a unique full command (token counts
          match, each input token a prefix of the canonical token).
        - ``("ambiguous", line)``: a position matches more than one command.
        - ``("incomplete", line)``: the input is a strict prefix of a longer
          command but reaches no full command (trailing tokens cannot be
          omitted, matching IOS).
        - ``("none", None)``: nothing matches → caller falls back to `_default_`.
        """
        tokens = line.split()  # collapses whitespace, like a real device
        if not tokens:
            return ("none", None)
        status, candidates = self._narrow(tokens)
        if status == "ambiguous":
            return ("ambiguous", line)
        if status == "none":
            return ("none", None)
        full = [c for c in candidates if len(c[2]) == len(tokens)]
        if full:  # dict keys are unique, so at most one full match
            return ("command", full[0][1])
        return ("incomplete", line)

    def _resolve_prefix_path(self, head: list[str]) -> list[tuple[str, ResolvedCommand, list[str]]]:
        """Canonical candidates under `head` for Tab completion (#303 P3-2).

        Empty `head` (empty prefix / trailing space) lists every current-mode
        canonical command, preserving P3-1's "empty input lists all"; an
        ambiguous / unmatched head returns ``[]`` (Tab stays silent where
        dispatch would answer with a diagnostic).
        """
        if not head:
            return self._abbrev_candidates()
        status, candidates = self._narrow(head)
        return candidates if status == "ok" else []

    def completion_candidates(self, prefix: str) -> list[str]:
        """Whole-line command names completing `prefix`, token-grain (#303 P3-2).

        Extends P3-1's flat exact-prefix `startswith` to leading-token
        abbreviation: the head tokens are resolved positionally (`_resolve_prefix_path`,
        shared with `_resolve_abbreviation`) and the last token prefix-matches the
        next canonical token. The return stays a list of whole-line full command
        names so the SSH `_complete` line-replacement contract (and its tests) is
        unchanged — `sh ip i<TAB>` expands to `show ip interface`, IOS style.
        Candidates are canonical-only (aliases resolve toward their canonical),
        so Tab is asymmetric with the help listing, which still shows aliases.
        Sorted for a stable completion menu.
        """
        tokens = prefix.split()
        trailing = prefix == "" or prefix.endswith(" ")
        head = tokens if trailing else tokens[:-1]
        last = "" if trailing else tokens[-1]
        resolved = self._resolve_prefix_path(head)
        return sorted(
            {name for name, _cmd, toks in resolved if len(toks) > len(head) and toks[len(head)].startswith(last)}
        )

    def _help_body(self) -> str:
        """Build the help listing for the current mode as body text (no I/O).

        Called by the push `dispatch` core when the parsed command is `help`
        (a leading `?` or a typed `help`), shared by both transports (#297 / #303
        P3-3). Returns the lines joined by `self.newline`; the driver renders the
        resulting body to the wire.

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
        for name, cmd in self._dispatchable_commands():
            lines[name] = cmd.help
            width = max(width, len(name))
        # form help lines
        help_msg = []
        for k, v in lines.items():
            padding = " " * (width - len(k)) + "  "
            help_msg.append(f"{k}{padding}{v}")
        return self.newline.join(help_msg)

    def _apply_new_mode(self, mode_name: str) -> None:
        """Transition to `mode_name` and render its prompt.

        Every transition source (`new_mode` / `transitions`, from any inflow)
        is validated against the platform modes at load time, so the lookup is
        plain indexing — the former lenient branch existed only for
        handler-returned modes, which the output-only handler contract removed
        (#317 / P-2).
        """
        mode = self.platform.modes[mode_name]
        self.current_mode = mode_name
        self.prompt = mode.render_prompt(self.base_prompt)

    def _invoke_handler(self, handler: CommandHandler, command: str) -> str | None:
        """Invoke a command handler; its return is the body text (or None).

        Handlers are output-only (`simnos.core.command_contract`): transitions
        and exit are static authoring data. A contract-breaking return (dict /
        list / int / ...) is answered with `HANDLER_ERROR_OUTPUT` and a loud
        log line — same shape as the crash boundary in the caller, so broken
        plugin code never puts garbage on the wire (#317 / P-2).
        """
        ret = handler(
            self.nos.device,
            base_prompt=self.base_prompt,
            current_mode=self.current_mode,
            current_prompt=self.prompt,
            command=command,
        )
        if ret is not None and not isinstance(ret, str):
            log.error(
                "shell '%s' command %r handler returned %s (contract is str | None); answering %r",
                self.base_prompt,
                command,
                type(ret).__name__,
                HANDLER_ERROR_OUTPUT,
            )
            return HANDLER_ERROR_OUTPUT
        return ret

    def _render_challenge_prompt(self, challenge: ResolvedChallenge) -> str:
        """Render a challenge sub-prompt for this session (#338 / §2).

        A literal prompt is returned verbatim; a template is rendered with
        `base_prompt` + `username`. `username` unwired (direct construction) is
        replaced by an empty string with a loud warning, so "None" is never baked
        into the wire (the render-side half of the creds-unwired defense; the
        `complete_challenge` guard is the other half, 2nd round claude#7).
        """
        out = challenge.prompt
        if out.kind == "template" and out.template is not None:
            username = self._username
            if username is None:
                log.warning(
                    "shell '%s' challenge prompt references username but none is wired; using empty string",
                    self.base_prompt,
                )
                username = ""
            return out.template.render(base_prompt=self.base_prompt, username=username)
        return out.text or ""

    def complete_challenge(self, pending: "PendingChallenge", entered: str) -> DispatchResult:
        """Verify a challenge answer and return the resulting `DispatchResult` (#338 / §3).

        The second dispatch stage: the driver read the answer line and calls this
        (on the bounded executor, like `dispatch`). Stateless — the driver carries
        `pending`, so a mid-challenge disconnect needs no shell-side cleanup.

        A password answer applies `success` (mode transition or close) when
        correct; a wrong / empty one answers `failure_output` with the prompt
        unchanged (a single attempt, #338 / C1). The expected value is `secret`
        (falling back to `password`, 案F) or `password`; if neither is wired (a
        direct construction that reached a challenge command) the answer fails
        with a loud warning rather than silently always-failing (1st round
        claude#5). The entered value is never logged (R5).

        A confirm answer is looked up in `on` (falling back to `default`, else a
        cancel = no-op with the prompt unchanged); the chosen action closes,
        transitions, and/or emits an `[OK]`-style body. The tail `is_running`
        check mirrors `_dispatch_general`, so both dispatch stages share one
        close contract (1st round claude#6).
        """
        spec = pending.spec
        body, close = None, False
        if spec.kind == "password":
            # The loader guarantees `success` on a password challenge (and a
            # non-None `on` on a confirm below); assert to narrow the unions.
            assert spec.success is not None  # noqa: S101 — loader guarantees success on a password challenge
            expected = self._secret if (spec.auth == "secret" and self._secret is not None) else self._password
            if expected is None:
                log.warning(
                    "shell '%s' challenge for %r has no credentials wired; failing", self.base_prompt, pending.command
                )
                body = spec.failure_output
            elif entered == expected:
                # `success` is a load-validated `Transition` (exactly one of
                # exit / new_mode), so exit False implies new_mode is set — the
                # `is not None` narrows it for the type checker, mirroring
                # `_dispatch_general`'s transition application.
                if spec.success.exit:
                    close = True
                elif spec.success.new_mode is not None:
                    self._apply_new_mode(spec.success.new_mode)
            else:
                body = spec.failure_output
        elif spec.kind == "confirm":
            # `on` miss → `default` (may be None) → a plain cancel: the prompt
            # returns unchanged, no body. The schema forbids `output` with
            # `exit`, so a closing action never carries a body.
            assert spec.on is not None  # noqa: S101 — loader guarantees a non-empty `on` on a confirm challenge
            action = spec.on.get(entered, spec.default)
            if action is not None:
                if action.exit:
                    close = True
                elif action.new_mode is not None:
                    self._apply_new_mode(action.new_mode)
                body = action.output
        if not self.is_running.is_set():
            close = True
        return DispatchResult(body=body, prompt=self.prompt, close=close, mode=self.current_mode)

    def _dispatch_general(self, line) -> tuple[str | None, bool, "PendingChallenge | None"]:
        """Resolve + invoke one general command; return ``(body, close, challenge)``.

        The I/O-independent heart of dispatch, called by the push `dispatch`
        core (#297, SSH; both transports since #303 P3-3). Applies a mode
        transition as a live-session side effect (§1a) but writes nothing — the
        caller renders `body`.

        ``close`` is True for an exit command (the static ``exit`` flag or the
        current mode's ``transitions`` entry) or a server shutdown observed
        mid-dispatch. The legacy `default` adapter suppressed the body on every
        one of those close paths, so callers MUST NOT render `body` when
        `close` is set.

        ``challenge`` is a `PendingChallenge` when the command declared a
        `challenge:` and the current mode is a firing mode (#338 / §3): the
        transition is held, ``body`` is None and ``close`` False, and the driver
        runs the sub-prompt then renders `complete_challenge`'s result. It is None
        on every ordinary line.

        The exception boundary is the `_invoke_handler` block only: resolution,
        the mode check and the transition never raise (an unknown command is a
        plain dict miss; every transition is load-validated), so
        `HANDLER_ERROR_OUTPUT` structurally means "a command handler crashed
        or broke the str | None contract" and nothing else (#241 / #264 / #317).
        """
        log.debug("shell.dispatch '%s' running command '%s'", self.base_prompt, [line])
        cmd = self.commands.get(line)
        # Command abbreviation (#303 / P3-2): only on an exact-match miss, so a
        # full command's wire is byte-identical (scrapers send full commands and
        # never reach here). An ambiguous / incomplete abbreviation swaps in the
        # `_ambiguous_` / `_incomplete_` overridable special so it flows through
        # the very same dispatch pipeline as `_default_` (handler / new_mode
        # supported); `abbrev_input` then drives the `{input}` interpolation
        # after the body is finalized.
        abbrev_input = None
        if cmd is None:
            kind, payload = self._resolve_abbreviation(line)
            if kind == "command":
                cmd = cast("ResolvedCommand", payload)
            elif kind in ("ambiguous", "incomplete"):
                special = self.commands.get("_ambiguous_" if kind == "ambiguous" else "_incomplete_")
                if special is not None:  # BASIC always provides these; guard the degraded case
                    cmd = special
                    abbrev_input = line  # set only when the special was actually swapped in
        if cmd is not None and self._in_current_mode(cmd):
            # Interactive challenge (#338 / §3): a `challenge:` command in a firing
            # mode holds its transition and hands the driver a `PendingChallenge`
            # (body-less, no close). Decided BEFORE the transition below, so the
            # command-level `new_mode` / `transitions` are the successor for a
            # NON-firing mode only (`challenge.success` is the sole transition
            # source in a firing mode — alcatel_sros `enable-admin` uses this to
            # answer differently per mode without per-mode output).
            if cmd.challenge is not None and self.current_mode in cmd.challenge.modes:
                prompt_text = self._render_challenge_prompt(cmd.challenge)
                pending = PendingChallenge(
                    spec=cmd.challenge,
                    command=cmd.canonical_name,
                    prompt_text=prompt_text,
                    echo=cmd.challenge.kind != "password",
                )
                return None, False, pending
            # Transition decision (#317 / P-1): the mode-conditional `transitions`
            # map wins for the current mode, else the simple static `exit` /
            # `new_mode`. An `exit` (from either channel) suppresses the body, so
            # decide it before rendering. `transitions` is None for every command
            # that uses the simple form, so this is a no-op for them.
            eff = cmd.transitions.get(self.current_mode) if cmd.transitions else None
            if eff is not None:
                if eff.exit:
                    return None, True, None
                transition = eff.new_mode
            elif cmd.exit:
                return None, True, None
            else:
                transition = cmd.new_mode
            # Sticky paging disable (#307 / P3-4): set only here — abbreviation is
            # already resolved (so `term len 0` works too) and the `_in_current_mode`
            # gate has passed (so a mode-mismatched command that falls through to
            # `_default_` does NOT disable, matching the real NOS). An A3 alias
            # inherits the target's `disables_paging` via the loader's `replace`, so
            # this also fires for alias spellings.
            if cmd.disables_paging:
                self._paging_disabled = True
                log.debug("shell '%s' paging disabled by command %r", self.base_prompt, line)
            # Consult the per-session variant map ONLY for variant-bearing
            # commands (#287 / D6, codex#2 5th). The `cmd.variants` guard is
            # required: a command stripped to a single output by an overlay has
            # `variants=()` and is absent from `_variant_outputs`, so without the
            # guard `.get(cmd.name, cmd.output)` is fine — but the guard makes the
            # intent explicit and prevents an overlay-stripped command from ever
            # reaching a sibling's variant output. `cmd.name` (dispatch identity)
            # keys the lookup; aliases share the canonical's chosen index.
            output = self._variant_outputs.get(cmd.name, cmd.output) if cmd.variants else cmd.output
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
                log.debug("shell.dispatch '%s' command %r not found", self.base_prompt, line)
            # Unknown command and mode mismatch both answer with the `_default_`
            # output — a silent shell would make clients (e.g. Netmiko) wait for
            # a timeout. The `_default_` answer never applies a transition.
            output = self.commands["_default_"].output
            transition = None
        if output.kind == "handler" and output.handler is not None:
            try:
                body = self._invoke_handler(output.handler, line)
            except Exception:
                # Same shape as the hot-reload guard (#232): full traceback
                # to the log, the session survives, and the client gets a
                # real-NOS-style one-liner instead of a Python traceback.
                log.error("shell '%s' command %r handler crashed\n%s", self.base_prompt, line, traceback.format_exc())
                body = HANDLER_ERROR_OUTPUT
        else:
            body = output.render(self.base_prompt)
        # Interpolate the typed line into an abbreviation diagnostic (#303 / P3-2),
        # after the body is finalized and before the transition / shutdown checks.
        # `abbrev_input` is set only when an `_ambiguous_` / `_incomplete_` special
        # was actually swapped in above, so this never fires on the normal path.
        # Restricted to literal / template kinds: a handler already receives `line`
        # and formats its own body, so replacing here would double-substitute; the
        # `body is not None` guard keeps a handler / none kind override from
        # crashing on `None.replace`.
        if abbrev_input is not None and body is not None and output.kind in ("literal", "template"):
            body = body.replace("{input}", abbrev_input)
        if transition is not None:
            self._apply_new_mode(transition)
        # Server shutdown observed mid-dispatch: close without rendering the body
        # (the legacy `default` adapter returned True here before writing output).
        if not self.is_running.is_set():
            return body, True, None
        return body, False, None

    def _parseline(self, line: str) -> tuple[str | None, str | None, str]:
        """Lex one line into ``(command, arg, line)``, replacing cmd.Cmd.parseline (#303 P3-3).

        Byte-for-byte compatible with the stdlib behaviour `dispatch` relied on:
        strips the line, maps a leading ``?`` to ``help ...`` (drives the help
        golden), and extracts the leading identifier as the command token. SIMNOS
        defines no ``do_shell`` (and `dispatch` only special-cases EOF / help),
        so a leading ``!`` yields no command and falls through to ``_default_`` —
        exactly as cmd.Cmd did. That ``!`` branch depends on the no-``do_shell``
        contract.
        """
        line = line.strip()
        if not line:
            return None, None, line
        if line[0] == "?":
            line = "help " + line[1:]
        elif line[0] == "!":
            return None, None, line  # no do_shell -> falls through to the _default_ path
        i, n = 0, len(line)
        while i < n and line[i] in self.identchars:
            i += 1
        return line[:i], line[i:].strip(), line

    def dispatch(self, line: str) -> DispatchResult:
        """I/O-independent dispatch core for the push session driver (#297 / §3a).

        Lexes the line with `_parseline` and routes it (precmd -> help / EOF /
        blank / general -> postcmd) so both transports (SSH asyncssh, Telnet
        telnetlib3) produce the same wire (#303 P3-3 replaced the former cmd.Cmd
        `onecmd`/`cmdloop` path). Returns a structured `DispatchResult` the
        session handler renders to wire bytes; it never writes to stdout. Mode
        transitions / variant / hot-reload run via `_dispatch_general` / `precmd`.

        The router special-cases only `EOF` (close) and `help` (current-mode
        listing); everything else goes to `_dispatch_general`. A NOS command
        named `help` / `EOF` stays shadowed by these explicit branches.
        """
        line = self.precmd(line)
        cmd_name, _arg, parsed = self._parseline(line)
        # Only the general path can fire a challenge; the blank / EOF / help
        # branches keep the 2-tuple form, so `challenge` defaults to None here and
        # only the `_dispatch_general` unpack widens to three (#338 / §3).
        challenge = None
        if not parsed:
            body, close = None, False  # blank line: no output
        elif cmd_name == "EOF":
            body, close = None, True  # EOF line: close session
        elif cmd_name == "help":
            body, close = self._help_body(), False  # leading `?` / `help`: current-mode listing
        else:
            body, close, challenge = self._dispatch_general(parsed)  # general command path
        # postcmd gets the post-precmd line (pre-parseline) — not the
        # parseline-transformed `parsed` (e.g. "?" -> "help ") — so a postcmd
        # override sees the line as typed on both transports (#297, claude#1).
        close = bool(self.postcmd(close, line))
        return DispatchResult(body=body, prompt=self.prompt, close=close, mode=self.current_mode, challenge=challenge)
