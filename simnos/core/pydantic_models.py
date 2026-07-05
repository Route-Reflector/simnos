"""
File to contain pydantic models for plugins input/output data validation
"""

import keyword
import os
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    IPvAnyAddress,
    StrictBool,
    StrictInt,
    StrictStr,
    field_validator,
    model_validator,
)

# Valid TCP port. Restores the range constraint lost in the pydantic v1 -> v2
# migration (v1 used `conint(strict=True, gt=0, le=65535)`); #237 / #199 C-15.
Port = Annotated[StrictInt, Field(ge=1, le=65535)]

# 0 = OS-assigned ephemeral port (#271). The OS atomically reserves a free port
# inside the `bind(("", 0))` syscall, so the TOCTOU window of "find a free port,
# then bind it later" is structurally gone. The real port is read back after
# start and stored on `host.port` (Host.start / D4). Applied to the single-port
# host path only; the `replicas` port-range path keeps `Port` (ge=1) since a
# range of ephemeral ports is meaningless.
EPHEMERAL_PORT = 0
EphemeralPort = Annotated[StrictInt, Field(ge=0, le=65535)]

# ---------------------------------------------------------------------------------------
# A3 authoring schema (#264 / P1-1 D2, D3) — the new per-platform on-disk form
# (`platforms/<nos>/platform.yaml` + `commands/*.yaml`). Validated at load; the
# loader then normalizes to `ResolvedCommand` / `ResolvedPlatform`, so the shell
# never sees this authoring form (D4). Kept structural here (types, exclusivity,
# alias purity, path shape); semantic checks that need the filesystem or jinja2
# (file existence, `.j2` syntax, mode-name existence, prompt render) live in the
# loader (`simnos.core.platform_loader`).
# ---------------------------------------------------------------------------------------


def _reject_unsafe_output_ref(value: str | None) -> str | None:
    """Reject an output file reference that escapes the command's own dir.

    Output files are adjacent to their command yaml (D1): a bare filename, no
    path separators, no ``..``, not absolute. This blocks references into
    packaged-data-外 paths at the authoring boundary (#264 / D1).
    """
    if value is None:
        return value
    if value != os.path.basename(value) or value in ("", ".", "..") or os.path.isabs(value):
        raise ValueError(f"output reference {value!r} must be a bare filename in the command's own directory")
    return value


class ModelCommandVariant(BaseModel):
    """One alternate capture of a multi-output command (#264 / D3).

    Each variant points at an output file read verbatim as literal wire text:
    the authoring *field* decides the channel, not the extension (the loader's
    `_resolve_output_file` reads variants with ``as_template=False``). ``.j2``
    templates in variants are out of scope for P1-1 (Decision 6) — a variant
    must reference a literal ``.txt`` (the file-name convention is enforced by
    the data lint, not the loader).
    """

    model_config = ConfigDict(extra="forbid")

    name: StrictStr
    output: StrictStr

    @field_validator("output")
    @classmethod
    def _safe_output(cls, value: str) -> str:
        # A variant output is always present (non-optional str); validate for
        # the side-effect and return the value unchanged.
        _reject_unsafe_output_ref(value)
        return value


def _reject_empty_mode_list(value: list[str] | None) -> list[str] | None:
    """Shared `mode:` field rule for the A3 and inventory command schemas.

    An explicit empty list reads as "runnable in no mode"; "all modes" is
    expressed by omitting `mode`. Reject `[]` so the two never blur
    (#264 / Decision 7). One definition so the dialects (and the message)
    cannot drift (#317 P-3/P-4).
    """
    if value is not None and not value:
        raise ValueError("mode: [] is rejected — omit `mode` to mean all modes (#264 / Decision 7)")
    return value


def _check_transitions_combination(
    transitions: dict | None, new_mode: str | None, exit_flag: bool | None, *, prefix: str = ""
) -> None:
    """Shared `transitions:` combination rule for the A3 and inventory schemas.

    `transitions` is the mode-conditional alternative to the simple static
    `new_mode` / `exit` — setting both is ambiguous, and an empty map is an
    authoring error, not a silent no-op (#317 / P-1). One definition so the
    dialects (and the messages) cannot drift (#317 P-3/P-4); `prefix` carries
    the command label where the schema knows it.
    """
    if transitions is None:
        return
    conflict = sorted(name for name, v in (("new_mode", new_mode), ("exit", exit_flag)) if v is not None)
    if conflict:
        raise ValueError(f"{prefix}`transitions` is exclusive with {conflict} (#317 / P-1)")
    if not transitions:
        raise ValueError(f"{prefix}`transitions: {{}}` is empty — omit it (#317 / P-1)")


class ModelTransition(BaseModel):
    """One mode's entry in a command's `transitions` map (#317 / P-1).

    Exactly one of `new_mode` / `exit` must be set: ``exit: true`` terminates the
    session, ``new_mode: <mode>`` switches mode after the command runs. Both-set,
    neither-set and ``exit: false`` are all rejected — an empty or ambiguous entry
    is an authoring error, not a silent no-op. The mode name(s) (the map keys) and
    each `new_mode` value are validated against the platform modes by the loader.
    """

    model_config = ConfigDict(extra="forbid")

    new_mode: StrictStr | None = None
    exit: StrictBool | None = None

    @model_validator(mode="after")
    def _exactly_one(self) -> "ModelTransition":
        if self.exit is not None and not self.exit:
            raise ValueError("transition `exit` must be true — omit it entirely for a `new_mode` transition")
        if (self.new_mode is not None) == bool(self.exit):
            raise ValueError("a transition entry must set exactly one of `new_mode` or `exit: true`")
        return self


class ModelConfirmAction(BaseModel):
    """One entry in a confirm challenge's `on:` map (or its `default:`) (#338 / §1, Phase 3).

    A relaxation of `ModelTransition`: unlike a transition, an action may set
    *neither* `new_mode` nor `exit` — that is a cancel (a no-op, the prompt
    returns unchanged, e.g. the ``n`` of a ``reload`` confirm). It may also carry
    an `output` literal body — the ``[OK]`` a ``copy running-config
    startup-config`` prints on save. `exit: true` forbids `output` (a closing
    session sends no body — the existing close contract, 1st round gemini#1);
    `exit: false` is rejected like a transition's, and `new_mode` + `exit` are
    mutually exclusive. `output` is an inline literal (unlike the command-level
    `output`, which references an adjacent file).
    """

    model_config = ConfigDict(extra="forbid")

    new_mode: StrictStr | None = None
    exit: StrictBool | None = None
    output: StrictStr | None = None

    @model_validator(mode="after")
    def _check(self) -> "ModelConfirmAction":
        if self.exit is not None and not self.exit:
            raise ValueError("confirm action `exit` must be true — omit it entirely for a cancel or `new_mode` action")
        if self.new_mode is not None and self.exit:
            raise ValueError("a confirm action sets at most one of `new_mode` or `exit: true`")
        if self.exit and self.output is not None:
            raise ValueError("a confirm action with `exit: true` cannot set `output` (a closing session sends no body)")
        return self


class ModelChallenge(BaseModel):
    """A3 `challenge:` block — a post-command interactive sub-prompt (#338 / §1).

    Two kinds:

    - ``kind: password`` — the command holds its transition until the client
      answers a (non-echoed) password prompt. ``auth`` picks the expected value
      (``secret`` falls back to the host password when unset, #338 / 案F),
      ``success`` is the transition on a correct answer, ``failure_output`` the
      body on a wrong / empty one (a single attempt, #338 / C1).
    - ``kind: confirm`` — the command asks a (echoed) yes/no or free-line prompt
      (``reload`` ``[confirm]``, ``copy run start`` ``Destination filename?``);
      the answer line is looked up in ``on:`` (falling back to ``default:``) to
      pick a `ModelConfirmAction` — a transition, a cancel, and/or an ``[OK]``
      body. ``on`` is required (non-empty); ``auth`` / ``success`` /
      ``failure_output`` are password-only and rejected here.

    - ``prompt`` is the (single-line) sub-prompt text, jinja2-capable with
      ``base_prompt`` / ``username`` (loader dry-renders it at build time).
    - ``mode`` scopes which modes fire the challenge (omitted = the command's
      every mode); a non-firing mode uses the command's ordinary output (#338 /
      案D). The loader checks the names against the command's modes.
    """

    model_config = ConfigDict(extra="forbid")

    kind: Literal["password", "confirm"]
    prompt: StrictStr
    mode: list[StrictStr] | None = None
    # --- password kind (required there, forbidden on confirm) ---
    auth: Literal["secret", "password"] | None = None
    success: ModelTransition | None = None
    failure_output: StrictStr | None = None
    # --- confirm kind (`on` required there, all three forbidden on password) ---
    on: dict[StrictStr, ModelConfirmAction] | None = None
    default: ModelConfirmAction | None = None

    _reject_empty_mode = field_validator("mode")(_reject_empty_mode_list)

    @field_validator("prompt")
    @classmethod
    def _single_line(cls, value: str) -> str:
        # A sub-prompt is a single in-line token (like `more_prompt`): a newline
        # would split the wire the netmiko `pattern="ssword"` wait reads, and a
        # NUL is stripped by the tap normalizer, so reject both at the authoring
        # boundary rather than corrupting the challenge wire at runtime (#338 /
        # §1, 1st round codex#6). A template's rendered result is re-checked by
        # the loader dry-render.
        if "\n" in value or "\r" in value:
            raise ValueError("challenge `prompt` must be a single line (no CR/LF)")
        if "\x00" in value:
            raise ValueError("challenge `prompt` must not contain a NUL byte")
        return value

    @model_validator(mode="after")
    def _check_kind(self) -> "ModelChallenge":
        if self.kind == "password":
            missing = sorted(n for n, v in (("auth", self.auth), ("success", self.success)) if v is None)
            if missing:
                raise ValueError(f"challenge `kind: password` requires {missing}")
            present = sorted(n for n, v in (("on", self.on), ("default", self.default)) if v is not None)
            if present:
                raise ValueError(f"challenge `kind: password` cannot set {present} (confirm-only)")
        else:  # confirm
            if not self.on:
                raise ValueError("challenge `kind: confirm` requires a non-empty `on:` map")
            # An `on:` key with CR/LF/NUL can never equal a read answer line (the
            # driver terminates on CR/LF and drops NUL), so it is a dead entry —
            # reject it loudly, mirroring `transitions`' dead-key check rather than
            # silently never firing (1st round claude#3).
            dead = sorted(k for k in self.on if "\r" in k or "\n" in k or "\x00" in k)
            if dead:
                raise ValueError(f"challenge `on:` keys must be single-line (no CR/LF/NUL); {dead} would never match")
            present = sorted(
                n
                for n, v in (("auth", self.auth), ("success", self.success), ("failure_output", self.failure_output))
                if v is not None
            )
            if present:
                raise ValueError(f"challenge `kind: confirm` cannot set {present} (password-only)")
        return self


class ModelCommandAuthoring(BaseModel):
    """A3 per-command authoring schema (#264 / D3).

    One file = one command; `command` is the SSoT key (Decision 1), the
    filename is non-semantic. Exactly one output channel may be set
    (`output` / `output_template` / `variants` / `handler`, and `variants` may
    not be the empty list); all absent = no output. `handler` names a py-defined
    callable resolved at merge time (#317 / P-1). Transitions are either the
    simple static `new_mode` / `exit`, or the mode-conditional `transitions` map
    (exclusive with them). An `alias` is a reference: it may carry only
    `command` + `help` + a `mode:` override (#317 / P-1); all other dispatch
    fields are inherited from the target, not re-authored. `_default_` is the
    unconditional fallback, so authoring a `mode` / `new_mode` / `transitions` /
    `alias` on it is rejected — it must stay mode-agnostic and must not inherit a
    target's modes (Decision 7).
    """

    model_config = ConfigDict(extra="forbid")

    command: StrictStr
    # Required for a real command, forbidden on an alias (validated below).
    type: Literal["ntc", "simnos", "custom"] | None = None
    source: dict | None = None
    help: StrictStr | None = None
    mode: list[StrictStr] | None = None
    new_mode: StrictStr | None = None
    output: StrictStr | None = None
    output_template: StrictStr | None = None
    variants: list[ModelCommandVariant] | None = None
    # Fourth (dynamic) output channel: the name of a py-defined handler callable
    # (#317 / P-1). The loader records it as a `handler_ref`; the merge binds the
    # actual callable from the platform's py handler namespace.
    handler: StrictStr | None = None
    # Mode-conditional transition map (#317 / P-1), exclusive with `new_mode` /
    # `exit`. Keys are mode names the command is valid in; each entry decides the
    # transition for that mode (see `ModelTransition`).
    transitions: dict[StrictStr, ModelTransition] | None = None
    exit: StrictBool | None = None
    alias: StrictStr | None = None
    # Session-level "disable paging" flag (#307 / P3-4). Set on the real command
    # whose output stubs paging off (e.g. `terminal length 0`); the shell flips a
    # sticky session flag when it runs in-mode and the push driver then skips the
    # `--More--` pager. Forbidden on an alias (it inherits the target's value via
    # the loader's `replace`, see `_check_combination`).
    disables_paging: StrictBool | None = None
    # Post-command interactive sub-prompt (#338 / §1). Exclusive with the dynamic
    # `handler` / `variants` channels and with `disables_paging` (no cross use
    # case, and a firing challenge would silently drop the paging disable), but
    # composes with `output` / `output_template` (the ordinary output for a mode
    # the challenge does not fire in). Forbidden on an alias (it inherits the
    # target's value via the loader's `replace`), see `_check_combination`.
    challenge: ModelChallenge | None = None

    @field_validator("output", "output_template")
    @classmethod
    def _safe_output(cls, value: str | None) -> str | None:
        return _reject_unsafe_output_ref(value)

    @field_validator("handler")
    @classmethod
    def _valid_handler(cls, value: str | None) -> str | None:
        # A handler is a py identifier resolved against the platform's handler
        # namespace at merge time; reject a non-identifier here so a path /
        # dotted / spaced value fails at the authoring boundary, not at bind.
        # A keyword (`class` / `def`) passes `isidentifier()` but can never name a
        # real py function, so reject it here for a clear boundary error rather
        # than a confusing "not found in namespace" at bind (1st round codex#5).
        if value is not None and (not value.isidentifier() or keyword.iskeyword(value)):
            raise ValueError(f"handler {value!r} must be a valid Python identifier")
        return value

    _reject_empty_mode = field_validator("mode")(_reject_empty_mode_list)

    @field_validator("variants")
    @classmethod
    def _check_variants(cls, value: list[ModelCommandVariant] | None) -> list[ModelCommandVariant] | None:
        # `variants: []` would pass the channel-exclusivity check as "present"
        # yet leave the loader's `variants[0]` with a bare IndexError — reject it
        # loudly here (1st round codex/claude #1). Duplicate variant names break
        # the (name, output) selection contract, so reject those too.
        if value is None:
            return value
        if not value:
            raise ValueError("variants: [] is rejected — omit `variants` for a no-output command (#264 / Decision 6)")
        names = [v.name for v in value]
        duplicates = sorted({name for name in names if names.count(name) > 1})
        if duplicates:
            raise ValueError(f"variants have duplicate name(s) {duplicates} — each variant name must be unique")
        return value

    @model_validator(mode="after")
    def _check_combination(self) -> "ModelCommandAuthoring":
        if self.alias is not None:
            # An alias inherits every dispatch field from its target; it may
            # re-author only `mode` (a mode-set override, #317 / P-1) alongside
            # `command` + `help`. Everything else is forbidden.
            forbidden = {
                "type": self.type,
                "source": self.source,
                "new_mode": self.new_mode,
                "output": self.output,
                "output_template": self.output_template,
                "variants": self.variants,
                "handler": self.handler,
                "transitions": self.transitions,
                "exit": self.exit,
                "disables_paging": self.disables_paging,
                "challenge": self.challenge,
            }
            present = sorted(k for k, v in forbidden.items() if v is not None)
            if present:
                raise ValueError(
                    f"command {self.command!r}: alias cannot also set {present} "
                    "(only `command`, `help` and a `mode:` override are allowed alongside `alias`) (#317 / P-1)"
                )
        else:
            if self.type is None:
                raise ValueError(f"command {self.command!r}: `type` is required (ntc | simnos | custom)")
            channels = sorted(
                name
                for name, v in (
                    ("output", self.output),
                    ("output_template", self.output_template),
                    ("variants", self.variants),
                    ("handler", self.handler),
                )
                if v is not None
            )
            if len(channels) > 1:
                raise ValueError(
                    f"command {self.command!r}: at most one output channel allowed, got {channels} (#264 / Decision 6)"
                )
            # A challenge holds the transition and produces its own body/prompt, so
            # it cannot ride the dynamic `handler` / `variants` channels — those
            # decide output at dispatch time (#338 / Decision 8). It DOES compose
            # with `output` / `output_template` (the response for a non-firing mode).
            # `disables_paging` is also exclusive: a firing challenge returns before
            # `_dispatch_general` sets the sticky-paging flag, so authoring both would
            # silently drop the disable (anti-silent-bug) — and enable/sudo never turn
            # paging off, so the pair is meaningless (1st round claude#3).
            if self.challenge is not None:
                conflict = sorted(
                    name
                    for name, v in (
                        ("handler", self.handler),
                        ("variants", self.variants),
                        ("disables_paging", self.disables_paging or None),
                    )
                    if v is not None
                )
                if conflict:
                    raise ValueError(
                        f"command {self.command!r}: `challenge` is exclusive with {conflict} (#338 / Decision 8)"
                    )
            _check_transitions_combination(
                self.transitions, self.new_mode, self.exit, prefix=f"command {self.command!r}: "
            )
        if self.command == "_default_":
            if (
                self.mode is not None
                or self.new_mode is not None
                or self.transitions is not None
                or self.challenge is not None
            ):
                raise ValueError(
                    "command '_default_': `mode` / `new_mode` / `transitions` / `challenge` are rejected — the "
                    "fallback is mode-agnostic (runtime never matches its mode, would be dead data) (#264 / Decision 7)"
                )
            # An aliased `_default_` would inherit the target's modes/new_mode via
            # the loader's `replace(target, ...)`, making the fallback
            # mode-bearing. Reject so `_default_` can never lose its
            # empty-modes semantics through the alias backdoor
            # (1st round claude #6).
            if self.alias is not None:
                raise ValueError(
                    "command '_default_': `alias` is rejected — the fallback must not inherit a target's "
                    "modes / transition (#264 / Decision 7)"
                )
        return self


class ModelModeDef(BaseModel):
    """One mode declaration: a prompt template rendered with `base_prompt` (#264 / D2)."""

    model_config = ConfigDict(extra="forbid")

    prompt: StrictStr


class ModelPlatformPaging(BaseModel):
    """A3 per-platform paging settings (`platform.yaml` `paging:`, #307 / P3-4).

    Only the `--More--` prompt string is per-platform (Cisco ``" --More-- "`` /
    Juniper ``"---(more)---"`` / Huawei ``"---- More ----"``). The page height
    source (pty/NAWS rows, falling back to `sys_config.paging.default_rows`) is an
    environment concern, not a platform one, so it lives in `ModelPaging` instead.
    """

    model_config = ConfigDict(extra="forbid")

    more_prompt: StrictStr = " --More-- "

    @field_validator("more_prompt")
    @classmethod
    def _single_line_ascii(cls, value: str) -> str:
        # The pager erases `more_prompt` with `\b`*N + ' '*N + `\b`*N where
        # N = len(more_prompt), which only erases correctly when char count == byte
        # count == display columns: a single-line ASCII string (#307 / P3-4, codex#3).
        # A newline / control char / non-ASCII / empty prompt would mis-erase, so
        # reject it at load time rather than corrupting the wire at runtime.
        if not value:
            raise ValueError("paging.more_prompt must not be empty")
        if not value.isascii():
            raise ValueError(f"paging.more_prompt must be ASCII (got {value!r}); wide glyphs break the erase width")
        # Control chars C0 (`c < " "`, incl. CR/LF/NUL/TAB) and DEL (0x7f) render in
        # ~0 columns, breaking the char==column erase assumption (claude 2nd#3).
        if any(c < " " or c == "\x7f" for c in value):
            raise ValueError(f"paging.more_prompt must be a single line with no control characters (got {value!r})")
        return value


class ModelPlatformMeta(BaseModel):
    """A3 per-platform metadata schema (`platform.yaml`, #264 / D2).

    Modes are declared centrally (name -> prompt template); commands reference
    mode names only (M2). No `name` field — the platform name is the directory
    name (D1). `netmiko_device_type` / `ntc_platform` are data placeholders the
    consumer side wires up in #266. `paging` is the optional P3-4 pager settings
    (#307); omitted = the Cisco-style default `--More--` prompt.
    """

    model_config = ConfigDict(extra="forbid")

    modes: dict[StrictStr, ModelModeDef]
    initial_mode: StrictStr
    auth: StrictStr | None = None
    netmiko_device_type: StrictStr | None = None
    ntc_platform: StrictStr | None = None
    paging: ModelPlatformPaging | None = None

    @model_validator(mode="after")
    def _check_modes(self) -> "ModelPlatformMeta":
        if not self.modes:
            raise ValueError("platform.yaml: `modes` must declare at least one mode")
        if self.initial_mode not in self.modes:
            raise ValueError(
                f"platform.yaml: initial_mode {self.initial_mode!r} is not in modes {sorted(self.modes)!r}"
            )
        return self


class ModelHost(BaseModel):
    """
    Pydantic model for Host Attributes
    """

    name: StrictStr
    username: StrictStr
    password: StrictStr
    port: EphemeralPort  # 0 = OS-assigned ephemeral (#271); resolved to a real port at start
    device_type: StrictStr | None = None
    # enable-secret / sudo password for a `challenge: {auth: secret}` command
    # (#338). Same name as netmiko's `secret` ConnectHandler arg. Unset → the
    # challenge falls back to `password` (案F, out-of-box simulator behaviour).
    secret: StrictStr | None = None


# ---------------------------------------------------------------------------------------
# SimNOS inventory data model components
# ---------------------------------------------------------------------------------------


class ModelInventoryCommand(BaseModel):
    """One inventory-authored command (`nos.configuration.commands`, #317 / P-3 案E).

    The inventory inflow speaks the same dialect as A3 authoring — mode *names*
    (validated against the platform modes at merge time), `new_mode` / `exit` /
    `transitions` for the session transition — instead of the removed legacy
    prompt-string form (`prompt` / `new_prompt` / `alias` / `output_variants`,
    all rejected loudly by ``extra="forbid"``). Differences from
    :class:`ModelCommandAuthoring` are inherent to the carrier:

    - the command name is the mapping *key* (no `command` field), so the
      `_default_` special rule lives on :class:`NosPluginConfig` (which sees the
      keys);
    - `output` is the inline literal wire text and `output_template` the inline
      jinja2 source (an inventory has no adjacent files to reference);
    - no `alias` — a cross-inflow alias (inventory aliasing an A3 command) has
      unresolved semantics and is out of scope (#317 P-3, 案E);
    - no `type` / `source` / `variants` / `handler` — session-local commands
      have no capture provenance, multi-capture data or py handler namespace to
      draw from — and no `disables_paging`, which belongs to the audited
      platform paging data (#307), not a per-host add-on.
    """

    model_config = ConfigDict(extra="forbid")

    help: StrictStr | None = None
    mode: list[StrictStr] | None = None
    new_mode: StrictStr | None = None
    transitions: dict[StrictStr, ModelTransition] | None = None
    exit: StrictBool | None = None
    output: StrictStr | None = None
    output_template: StrictStr | None = None

    _reject_empty_mode = field_validator("mode")(_reject_empty_mode_list)

    @model_validator(mode="after")
    def _check_combination(self) -> "ModelInventoryCommand":
        if self.output is not None and self.output_template is not None:
            raise ValueError("at most one of `output` / `output_template` allowed (#264 / Decision 6)")
        # The command name is the mapping key, not a field — no prefix to carry.
        _check_transitions_combination(self.transitions, self.new_mode, self.exit)
        return self


class NosPluginConfig(BaseModel):
    """
    Pydantic model for NOS plugin configuration.

    ``commands`` is the inventory command inflow in its A3-dialect form
    (`ModelInventoryCommand`, #317 / P-3); the merge
    (`build_resolved_platform`) validates the mode names against the platform
    and normalizes each entry to a `ResolvedCommand`.
    """

    commands: dict[StrictStr, ModelInventoryCommand] | None = None

    @model_validator(mode="after")
    def _check_default_rules(self) -> "NosPluginConfig":
        # `_default_` special rule, A3-identical (#317 / P-3, 2nd round claude#5):
        # the fallback is mode-agnostic, so a mode / transition on it would be
        # dead data. Enforced here (not on `ModelInventoryCommand`) because the
        # command name is this mapping's key, not a field of the entry.
        default = (self.commands or {}).get("_default_")
        if default is not None and (
            default.mode is not None or default.new_mode is not None or default.transitions is not None
        ):
            raise ValueError(
                "command '_default_': `mode` / `new_mode` / `transitions` are rejected — the fallback is "
                "mode-agnostic (runtime never matches its mode, would be dead data) (#264 / Decision 7)"
            )
        return self


class NosPlugin(BaseModel):
    """
    Pydantic model for NOS plugin.
    """

    plugin: StrictStr
    configuration: NosPluginConfig | None = None


class AsyncSshServerConfig(BaseModel):
    """Pydantic model for the asyncssh SSH server configuration (#297 Stage 2).

    ``timeout`` / ``watchdog_interval`` are accepted for signature parity (the
    async path drives shutdown via loop close, not a recv poll), so they are inert
    here but kept for drop-in inventory compatibility.
    """

    ssh_key_file: StrictStr | None = None
    ssh_key_file_password: StrictStr | None = None
    ssh_banner: StrictStr | None = "SIMNOS AsyncSSH Server"
    timeout: StrictInt | None = 1
    address: Literal["localhost"] | IPvAnyAddress | None = None
    watchdog_interval: StrictInt | None = 1
    authorized_keys: StrictStr | None = None


class AsyncSshServerPlugin(BaseModel):
    """Pydantic model for the asyncssh SSH server plugin (#297 Stage 2)."""

    plugin: Literal["AsyncSshServer"]
    configuration: AsyncSshServerConfig | None = None


class TelnetServerConfig(BaseModel):
    """Pydantic model for the (telnetlib3) Telnet server configuration.

    ``timeout`` / ``watchdog_interval`` are accepted for inventory compatibility
    but inert on the async path (#297 Stage 3): shutdown is driven by closing the
    listener/sessions on the shared loop, not a recv poll.
    """

    banner: StrictStr | None = "SIMNOS Telnet Server"
    timeout: StrictInt | None = 1
    address: Literal["localhost"] | IPvAnyAddress | None = None
    watchdog_interval: StrictInt | None = 1


class TelnetServerPlugin(BaseModel):
    """
    Pydantic model for Telnet server plugin.
    """

    plugin: Literal["TelnetServer"]
    configuration: TelnetServerConfig | None = None


class CMDShellConfig(BaseModel):
    """Pydantic model for CMD shell configuration.

    `ruler` / `completekey` were cmd.Cmd cmdloop-only knobs and were removed with
    the cmd.Cmd base in #303 P3-3; `extra="forbid"` now rejects them (and any
    other unknown key) at load time rather than letting it reach
    `CMDShell.__init__` as an unexpected keyword and crash at connect time.
    `base_prompt` is injected by `Host` (`shell.configuration` setdefault) and
    may also be set in inventory to override the host-name prompt, so it is an
    explicit field here to stay forbid-compatible.
    """

    model_config = ConfigDict(extra="forbid")

    intro: StrictStr | None = "Custom SSH Shell"
    newline: StrictStr | None = "\r\n"
    base_prompt: StrictStr | None = Field(default=None, description="Overrides the default host-name base prompt")


class CMDShellPlugin(BaseModel):
    """
    Pydantic model for CMD shell plugin.
    """

    plugin: Literal["CMDShell"]
    configuration: CMDShellConfig | None = None


class ModelVariantsPolicy(BaseModel):
    """Typed variant-selection policy (#287 / D6, D8).

    Promotes the #266 permissive ``variants_policy`` mapping to a committed
    schema now that #287 consumes it. Two dials:

    - ``select`` — a non-negative ``int`` (default ``0``) pins one variant index
      (fully deterministic, the legacy ``variants[0]`` behaviour); the literal
      ``"random"`` defers the choice to ``seed``.
    - ``seed`` — only meaningful when ``select == "random"``: set = reproducible
      per-host sticky selection (``hash(seed, host, command)``); unset = a fresh
      random draw per connection (realism, non-reproducible).

    ``select`` is a `StrictInt` so ``True``/``1.0`` are rejected (a bool index is
    a config mistake, not "index 1"), and ``ge=0`` forbids negatives — a negative
    modulo would silently pick a tail variant and hide the error (#287 / D6 J).
    ``extra="forbid"`` makes a mistyped key (``selct``) loud rather than inert.
    """

    model_config = ConfigDict(extra="forbid")

    select: Annotated[StrictInt, Field(ge=0)] | Literal["random"] = 0
    seed: StrictInt | None = None


class ModelOverlay(BaseModel):
    """User overlay control (custom data layering, #286 / P1-2a).

    Per-host control for the output-only override: drop a captured ``.txt`` /
    ``.j2`` under ``<sys_config.data_dir>/<registry-key>/`` and list it here to
    replace a packaged command's wire output (or add a command absent from the
    package). The overlay *directory* is environment-global (``sys_config.data_dir``,
    not per-host) — the #266-reserved per-host ``dir`` field is removed; what each
    host pulls from it is the per-host control below.

    ``override_commands`` (Decision 5) selects the commands this host pulls from
    the overlay dir, in three forms:

    - ``all`` — apply every ``.txt`` / ``.j2`` in the dir (stem ``_``->space is the
      command name).
    - a list — apply these commands by their default-name file (``show version``
      -> ``show_version.txt`` / ``.j2``).
    - a map — ``{command: filename}`` for an explicit per-host capture choice
      (the R11 case: host A pulls ``show_version_A.txt``, host B ``_B``).

    A command found in the base is an output-only override (only its output is
    swapped); one absent from the base is a new command (all-modes, ``type=custom``).
    Unset / empty = the overlay is not applied (this field is the opt-in). yaml
    full-replacement is deferred to a future issue — #286 reads ``.txt`` / ``.j2``
    output files only.

    ``random_commands`` is the vessel for a *future* per-command variant policy
    axis (which commands opt into random selection). #287 wires only host-wide
    ``variants_policy``; ``random_commands`` stays validated-but-inert with its
    load-time warning maintained until that future per-command issue (#287 / D8 C).
    """

    model_config = ConfigDict(extra="forbid")

    override_commands: Literal["all"] | list[StrictStr] | dict[StrictStr, StrictStr] | None = None
    random_commands: list[StrictStr] | None = None  # future per-command 器 (warning 維持)


class InventoryDefaultSection(BaseModel):
    """
    Pydantic model for SimNOS inventory default section.
    """

    model_config = ConfigDict(extra="forbid")

    username: StrictStr | None = None
    password: StrictStr | None = None
    # enable-secret / sudo password for `challenge: {auth: secret}` commands
    # (#338); same name as netmiko's `secret`. Inherited by hosts via `HostConfig`;
    # unset → the challenge falls back to `password` (案F).
    secret: StrictStr | None = None
    # Single port accepts 0 (ephemeral, #271); the `replicas` list path keeps
    # `Port` (ge=1) — an ephemeral port *range* is meaningless.
    port: EphemeralPort | list[Port] | None = None
    configuration_file: StrictStr | None = None
    device_type: StrictStr | None = None
    server: AsyncSshServerPlugin | TelnetServerPlugin | None = None
    shell: CMDShellPlugin | None = None
    nos: NosPlugin | None = None
    # Inventory render fields. `overlay` is consumed by #286 (Host.start resolves
    # the overlay dir and threads it to the shell). `facts` / `variants_policy`
    # remain #287 reservations — accepted + validated here so the inventory schema
    # never breaks again when #287 wires them up, but consumed by nobody until then;
    # a non-None value is surfaced at host load with `log.warning` (Host.__init__)
    # so a "set but silently inert" config is loud, not a silent no-op
    # (anti-silent-bug). `facts` is a free mapping (render variables, shape owned by
    # the Layer-2 follow-up issue); `variants_policy` is now a committed schema
    # (`ModelVariantsPolicy`, #287 / D8) since #287 consumes it; only `facts`
    # stays permissive until Layer 2 (R4).
    facts: dict | None = Field(None, description="Layer 2 (global facts) で有効化、現在 no-op (host render facts)")
    overlay: ModelOverlay | None = Field(None, description="#286 で有効化 (custom overlay / output override)")
    variants_policy: ModelVariantsPolicy | None = Field(None, description="#287 で有効化 (variant 選択方針)")


class HostConfig(InventoryDefaultSection):
    """
    Pydantic model for SimNOS inventory host configuration.
    """

    replicas: StrictInt | None = None

    @model_validator(mode="before")
    @classmethod
    def check_port_value(cls, values):
        """
        Method to validate port value based on 'replicas' value.
        """
        port = values.get("port")
        # `is not None`, not truthy: port=0 is a valid value (ephemeral, #271), so
        # `if port:` would wrongly skip both branches — letting `replicas` + port=0
        # slip past the "port must be a list" check. `is not None` treats 0 as set.
        if "replicas" not in values and port is not None:
            if not isinstance(port, int):
                raise ValueError("If no host 'replicas' given, port must be an integer")
        elif "replicas" in values and port is not None and not isinstance(port, list):
            raise ValueError("If host 'replicas' given, port must be a list")
        return values


class ModelSimnosInventory(BaseModel):
    """SimNOS inventory data schema"""

    default: InventoryDefaultSection | None = None
    hosts: dict[StrictStr, HostConfig]

    model_config = ConfigDict(extra="forbid")


class ModelPaging(BaseModel):
    """Environment-wide paging settings (`sys_config.yaml` `paging:`, #307 / P3-4).

    `default_rows` is the page height the push driver falls back to when a client
    requests a pty (SSH) / negotiates NAWS (Telnet) but reports no usable row
    count. `gt=0` makes a 0/negative value loud rather than silently breaking the
    pager (a 0-row page would loop forever / draw nothing). Always materialized
    (default_factory) so `sys_config["paging"]["default_rows"]` is present even
    when the file omits `paging:` entirely.
    """

    model_config = ConfigDict(extra="forbid")

    default_rows: int = Field(default=24, gt=0)


class ModelSysConfig(BaseModel):
    """SimNOS environment config schema (`sys_config.yaml`, #266 / D4, Decision 6).

    The minimal "environment vs topology" split: `sys_config.yaml` holds
    environment-wide settings, the inventory holds topology. #266 introduced it
    with two fields only — `data_dir` (the environment-global overlay base dir)
    and `variants_policy` (global default for the inventory per-host field of the
    same name). `data_dir` is consumed by the overlay loader in #286 (a host opts
    in via `overlay.override_commands`, which resolves `<data_dir>/<registry-key>/`);
    `variants_policy` is now consumed by #287 as the global default under the
    inventory; it shares the inventory field's committed `ModelVariantsPolicy`
    schema (#287 / D8). The whole dict flows through the
    ``inventory(default) > sys_config`` precedence as one unit before validation,
    so ``select`` and ``seed`` must co-reside in one source mapping (D8 C).
    """

    model_config = ConfigDict(extra="forbid")

    data_dir: StrictStr | None = None
    variants_policy: ModelVariantsPolicy | None = None
    paging: ModelPaging = Field(default_factory=ModelPaging)
