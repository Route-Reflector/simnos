"""
Custom shell class to interact with NOS.
"""

import copy
from dataclasses import dataclass
import hashlib
import logging
import os
import random
import string
import traceback
from typing import TYPE_CHECKING, cast

from simnos.core.command_adapter import adapt_commands, adapt_legacy_commands, reverse_map_from_modes
from simnos.core.command_contract import CommandHandler, CommandResult
from simnos.core.nos import Nos
from simnos.core.overlay_loader import resolve_overlay
from simnos.core.platform_loader import load_platform_dir
from simnos.core.resolved_command import ResolvedCommand, ResolvedOutput, ResolvedPlatform
from simnos.plugins import nos
from simnos.plugins.shell.utils import get_files_changed

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


# Special, always-present commands fed through the same legacy adapter as the
# NOS data (#264 / D5). They carry no `prompt`, so the adapter resolves them to
# an empty mode set = valid in every mode.
BASIC_COMMANDS: dict = {
    "exit": {"exit": True, "help": "Exit commands shell"},
    "_default_": {
        "output": "Unknown command",
        "help": "Output to print for unknown commands",
    },
    # Abbreviation diagnostics (#303 / P3-2). Overridable specials like
    # `_default_` — the default wording is Cisco IOS style (no captured oracle
    # exists, so it follows public IOS documentation; re-pin if a capture is
    # obtained), and huawei/junos can override it from platform data. The
    # dispatcher fills a literal `{input}` placeholder with the typed line via
    # `str.replace`. These entries flow through the legacy adapter
    # (`format_template_to_jinja`), which treats `{...}` as a `str.format` field
    # and rejects any field but `base_prompt`, so the placeholder is written
    # **escaped** as `{{input}}` here: the adapter collapses it to a literal
    # `{input}` (no template render), which `_dispatch_general` then substitutes.
    # An override may carry `{input}` only as literal / A3 `.j2` text or via a
    # handler (which formats itself from its `command` argument); a legacy
    # py-module str.format template with a bare `{input}` fails loudly at load.
    "_ambiguous_": {
        "output": '% Ambiguous command:  "{{input}}"',
        "help": "Output for an ambiguous command abbreviation",
    },
    "_incomplete_": {
        "output": "% Incomplete command.",
        "help": "Output for an incomplete command abbreviation",
    },
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
    merge under one precedence — BASIC < NOS < overlay < inventory, later inflows
    winning:

    - **legacy NOS** (`nos.resolved_platform is None`): the merged dict (BASIC +
      NOS commands + inventory, all legacy form) goes through the legacy adapter,
      which synthesizes the modes from the 3 scalar prompts. The user overlay is
      A3-only (#286 / Decision 12), so it is not applied here.
    - **A3 NOS** (`nos.resolved_platform` set): modes come from the A3 platform;
      its resolved static commands sit between the still-legacy BASIC (below) and
      the legacy py-module / inventory inflows (above, keeping the py-override
      precedence). The legacy inflows are normalized with the A3 platform's
      prompt->mode reverse map. The user overlay (#286), when the host opted in,
      slots between the py inflow and inventory so a captured `.txt` overrides the
      packaged output but a session-local inventory command still wins. Inventory /
      py aliases resolve within their own inflow only; a cross-inflow alias (e.g.
      inventory aliasing an A3 command) is out of scope until the inventory rework
      (#266) — shipped data has none.

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
    # User overlay (#286): a host opts in via inventory `overlay.override_commands`;
    # the overlay dir was resolved + existence-checked by Host. Applied after py and
    # before inventory (last-wins precedence, Decision 14).
    if render_config is not None and render_config.overlay_root and render_config.override_commands:
        overlay_commands = resolve_overlay(
            render_config.overlay_root, a3, override_commands=render_config.override_commands
        )
        log.debug("overlay overrides %d command(s): %s", len(overlay_commands), sorted(overlay_commands))
        commands.update(overlay_commands)
    commands.update(adapt_commands(copy.deepcopy(inventory_commands), reverse_map))
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


@dataclass(frozen=True)
class DispatchResult:
    """Structured result of one dispatched line (#297 / §3a).

    The push session driver turns this into wire bytes. The legacy
    ``cmd.Cmd.cmdloop`` / ``onecmd`` (removed in #303 P3-3) could not represent
    multi-line output, no output, session close, or a post-transition prompt in
    a single ``str``, so the I/O-independent dispatch core returns the pieces
    explicitly:

    - ``body``: text the driver renders line-by-line with ``newline``, or
      ``None`` for no output (empty line, EOF, a handler returning no
      ``output``). The driver suppresses it when ``close`` is set — the legacy
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
    ):
        self.nos: Nos = nos
        # Platform name captured at build time for the hot-reload ownership filter
        # (#274 / D6). A later foreign py reload can overwrite live `nos.name`
        # (`_from_module` commit phase), so the filter must compare against this
        # frozen value, not `self.nos.name`, or a hijacked name would permanently
        # skip this session's own A3 platform reload.
        self._platform_name: str = nos.name
        self.intro = intro
        self.base_prompt = base_prompt
        self.newline = newline
        self.is_running = is_running
        # Paging (#307 / P3-4). `page_default_rows` is the fallback page height
        # (sys_config.paging.default_rows, wired through the server); `more_prompt`
        # is installed from the resolved platform in `_apply_platform`. The push
        # driver reads both, plus `paging_disabled` — a sticky per-session flag a
        # `disables_paging` command flips (the realism of `terminal length 0`).
        self.page_default_rows: int = page_default_rows
        self._paging_disabled: bool = False
        # Inventory-defined commands are a third inflow alongside BASIC and the
        # NOS data; kept in authoring form and normalized through the adapter on
        # a hot-reload rebuild (#264 / D6).
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
        #    against the latest commands (dispatch identity; a legacy alias may
        #    override its own output_variants, codex#1 6th).
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
        # The merged platform is per-host invariant (base_prompt is the host name,
        # nos/inventory are shared), so the server normalizes it once at
        # Host.start and passes it to every connection's shell (#264 / Impact —
        # normalize once, fail at startup). When not supplied (tests / direct
        # construction) the shell builds its own. A malformed prompt template
        # fails loudly here (the #172 lenient fallback is gone, #264 / D5).
        if resolved_platform is None:
            resolved_platform = build_resolved_platform(self.nos, self._inventory_commands, self._render_config)
        self._apply_platform(resolved_platform)

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
          the latest `commands`, so a legacy alias overriding its own
          `output_variants` keeps its own output while still sharing the
          canonical's chosen index (codex#1 6th).
        - every command sharing a `canonical_name` must expose the same variant
          pool length, else the shared index is ambiguous — loud (codex#1 6th).
          A3 aliases (`replace`) always match; only legacy `output_variants`
          overrides can diverge.
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
                # Broad except, like the dispatch core's handler guard: any
                # plugin error must not crash the session. Roll back the partial
                # nos mutation so the broken file does not poison subsequent
                # reloads, then log the traceback so a genuine plugin bug stays
                # diagnosable.
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

    def _dispatch_general(self, line) -> tuple[str | None, bool]:
        """Resolve + invoke one general command; return ``(body, close)``.

        The I/O-independent heart of dispatch, called by the push `dispatch`
        core (#297, SSH; both transports since #303 P3-3). Applies a mode
        transition as a live-session side effect (§1a) but writes nothing — the
        caller renders `body`.

        ``close`` is True for an exit command, a handler returning ``exit``, or
        a server shutdown observed mid-dispatch. The legacy `default` adapter
        suppressed the body on every one of those close paths, so callers MUST
        NOT render `body` when `close` is set.

        The exception boundary is the `_invoke_handler` block only: resolution,
        the mode check and the transition never raise (an unknown command is a
        plain dict miss, an unknown handler mode degrades inside
        `_apply_new_mode`), so `HANDLER_ERROR_OUTPUT` structurally means "a
        command handler crashed" and nothing else (#241 / #264).
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
            if cmd.exit:
                return None, True
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
            # keys the lookup so a legacy alias returns its own output.
            output = self._variant_outputs.get(cmd.name, cmd.output) if cmd.variants else cmd.output
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
                log.debug("shell.dispatch '%s' command %r not found", self.base_prompt, line)
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
                return None, True
            # A handler transition applies only when the command has no static
            # one (a static `new_mode` was the last write in the v2 order).
            if transition is None:
                transition = result.get("new_mode")
            body = result.get("output")
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
            self._apply_new_mode(transition, line)
        # Server shutdown observed mid-dispatch: close without rendering the body
        # (the legacy `default` adapter returned True here before writing output).
        if not self.is_running.is_set():
            return body, True
        return body, False

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
        if not parsed:
            body, close = None, False  # blank line: no output
        elif cmd_name == "EOF":
            body, close = None, True  # EOF line: close session
        elif cmd_name == "help":
            body, close = self._help_body(), False  # leading `?` / `help`: current-mode listing
        else:
            body, close = self._dispatch_general(parsed)  # general command path
        # postcmd gets the post-precmd line (pre-parseline) — not the
        # parseline-transformed `parsed` (e.g. "?" -> "help ") — so a postcmd
        # override sees the line as typed on both transports (#297, claude#1).
        close = bool(self.postcmd(close, line))
        return DispatchResult(body=body, prompt=self.prompt, close=close, mode=self.current_mode)
