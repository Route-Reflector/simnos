# Adding new platforms
SIMNOS is designed to be easily extensible. A platform's static command data
lives in an **A3 platform directory**; dynamic behavior is added with an
optional Python module. The two compose: the A3 dir provides the static
commands and modes, and a co-named Python module can add handlers / a device
class on top (#264).

!!! tip
    A hot-reloader (`simnos up --reload-commands`) watches each platform's own
    sources — the A3 platform directory **and** its Python module — and reloads
    the platform when a file changes (#274 / #281). Editing a `commands/*.yaml`,
    an output `.txt` / `.j2`, or the module `.py` propagates to the next command
    of a live session.

## A3 platform directory
This is the way to add a platform's static command data. Each platform is a
directory under `simnos/plugins/nos/platforms/<name>/` containing:

```
platforms/<name>/
  platform.yaml        # modes + metadata
  commands/
    <stem>.yaml        # one command per file (command field is the SSoT)
    <stem>.txt         # literal output for that command
    <stem>.j2          # jinja2 template output (when {{ base_prompt }} is needed)
```

The command-file *stem* is non-semantic — the `command:` field inside the yaml
is the single source of truth. The lint warns if the stem does not match the
sanitized command name (a discoverability convention, not a correctness rule).

### `platform.yaml`

Declares the platform's modes (name → prompt template) and metadata:

```yaml
modes:
  user:
    prompt: "{{ base_prompt }}>"
  enable:
    prompt: "{{ base_prompt }}#"
  config:
    prompt: "{{ base_prompt }}(config)#"
initial_mode: user
auth: none                      # optional — e.g. dell_powerconnect disables SSH auth
netmiko_device_type: cisco_ios  # optional metadata placeholders (consumed by #266)
ntc_platform: cisco_ios
```

Prompt templates are **jinja2** (`{{ base_prompt }}` is the device hostname);
`StrictUndefined` makes an undefined variable a loud render error. `initial_mode`
must be one of the declared modes. A flat-CLI platform (no privileged/config
modes) simply declares a single mode. The mode names are conventionally
`user` / `enable` / `config`, but any name works as long as commands reference
the names that exist.

### `commands/<stem>.yaml`

One command per file. Fields (unknown fields are rejected — `extra="forbid"`):

```yaml
command: show version          # SSoT; what the user types
type: ntc                      # ntc | simnos | custom (provenance class)
source:                        # optional; required-by-convention for type: ntc
  ntc_template: tests/cisco_ios/show_version/cisco_ios_show_version.raw
  ntc_commit: <sha>
help: show system version
mode: [user, enable]           # modes the command is valid in; omit = all modes
output: show_version.txt       # a bare .txt filename, read verbatim (literal)
```

- **`output`** references an adjacent `.txt` file read **verbatim** — no
  `str.format`, no brace escaping. A literal `{master:0}` in the capture
  reaches the wire unchanged.
- **`output_template`** references an adjacent `.j2` file rendered with jinja2
  (use it only when the output must interpolate `{{ base_prompt }}`). A command
  may set `output` *or* `output_template`, never both.
- **`handler`** names a callable on the platform's Python module (a device-class
  method or module-level function) that computes the output at dispatch time —
  the fourth, mutually exclusive output channel (#317). The handler returns
  `str | None` (output only; transitions stay static data — see below).
- **`new_mode`** names the mode to transition to after the command runs
  (the successor of the legacy `new_prompt`).
- **`transitions`** is the mode-conditional transition map, exclusive with
  `new_mode` / `exit`: each key is one of the command's modes, each value
  `{new_mode: <mode>}` or `{exit: true}` (#317). E.g. arista_eos `exit` closes
  the session from user/enable but drops config to enable.
- **`variants`** is the multi-capture contract: a list of `{name, output}`
  entries (`variant_1` mirrors the primary, `variant_2`.. are alternates), each
  pointing at its own `.txt`.
- **`alias`** makes the command a pure reference to another command. The one
  dispatch field an alias may re-author is `mode:` (e.g. arista_eos
  `do show ip int brief` is config-only while its target is user/enable, #317);
  everything else is inherited.
- **`exit`** marks a session-closing command.
- **`disables_paging`** marks a command that turns the `--More--` pager off for
  the rest of the session (e.g. `terminal length 0`, #307).
- **`challenge`** makes the command ask for a password after it runs (enable
  secret / `sudo -s`, #338) — see [Interactive challenges](#interactive-challenges).
- **`_default_`** is the mode-agnostic unknown-command fallback: author the
  platform's real error wording (e.g. Cisco IOS `% Invalid input detected at
  '^' marker.`; vendor wording differs, do not copy-paste). It takes no `mode`.

### Interactive challenges

A `challenge:` block turns a command into a two-step interaction: it prints a
sub-prompt, reads one answer line, and only then transitions — the shape of an
enable secret (`enable-admin`, `enable 15`, `administrator`) or `sudo -s`
(#338). Phase 1 supports `kind: password` (the answer is verified against the
host credentials and never echoed); `confirm` (y/n) lands in a later phase.

```yaml
command: sudo -s
type: simnos
mode: [user]
challenge:
  kind: password
  prompt: "[sudo] password for {{ username }}: "  # single line; base_prompt / username only
  auth: password          # `password` = host password; `secret` = host secret (falls back to password)
  success:
    new_mode: enable      # applied only on a correct answer (or `exit: true`)
  failure_output: "Sorry, try again."  # body on a wrong / empty answer; the prompt stays put
```

- The answer is checked **once** — a wrong or empty answer prints
  `failure_output` and stays in the current mode (no retry loop). This matches
  what netmiko's `enable()` expects (a re-prompt would hang its read).
- Set the host's `secret` in inventory (same name as netmiko's `secret` arg) for
  `auth: secret`; unset, it falls back to the host `password` so the simulator
  works out of the box.
- **`mode`** inside `challenge:` scopes which modes fire it (default: every mode
  the command is valid in). A mode that does **not** fire the challenge answers
  the command's ordinary `output` instead — this is how a command responds
  differently per mode (e.g. `enable-admin` challenges in user mode but prints
  "already in admin mode" once enabled) without a separate command.
- `challenge` composes with `output` / `output_template` (the non-firing-mode
  response) but not with `handler` / `variants`, and an alias inherits its
  target's challenge rather than re-authoring it.

### Authoring conventions

The A3 data lint (`invoke lint-platform-data`, CI + pre-commit) gates:

- **encoding**: every `.txt` / `.j2` output file must be UTF-8, LF-only, and end
  with a trailing newline (an empty output file stays 0 bytes).
- **references**: each output file is referenced by exactly one command yaml
  (1 yaml : 1 output); an unreferenced output file (orphan), a missing
  referenced file, or a shared reference is flagged.
- **extension convention**: literal channels (`output` / a variant's `output`)
  use `.txt`; `output_template` uses `.j2`. A stray `.yml` command file (the
  loader only globs `.yaml`) is flagged.
- **`_default_` presence**: every new platform must define a `_default_`
  command. Platforms that predate the rule are frozen in
  `platform_data_lint_baseline.yaml` (repo root); that baseline only ever
  shrinks.
- **`help` text**: write real help. Auto-generated stubs
  (`execute the command "X"`) are frozen in the baseline and new ones fail
  the lint; replacing a stub with real help requires removing its baseline
  entry in the same PR. The heritage sentence `"Feel free to change it!"`
  is rejected outright.

It also prints **warnings** (non-blocking): a filename not matching the
sanitized command name, and a `type: ntc` command missing its `source` block.

The `quoted-strings` yamllint rule does not apply to the platform data
directory (raw captures live in `.txt` files, not yaml scalars).

### Generating candidates from NTC Templates

`sync_ntc_commands.py` compares NTC Templates against the A3 platforms and emits
A3 take-in candidate files (`commands/<stem>.yaml` + `.txt`, `type: ntc` with a
`source` block) for commands not yet present — review them and copy them under
`platforms/<name>/`. A brand-new platform's `platform.yaml` is authored by hand
(modes/auth are not derivable from NTC fixtures).

## Python modules
This method adds dynamic behavior on top of the static A3 data with the full
power of Python. The Python modules are located in the
`simnos/plugins/nos/platforms_py` package; a module co-named with an A3
platform composes with it. The pattern (#317): the module defines a
`BaseDevice` subclass whose methods (plus module-level functions) form the
platform's **handler namespace**, and A3 commands reference them by name via
`handler:` — an unresolved reference fails loudly at server start. See the
[handler contract](creating_nos_plugin.md) for the callable signature and the
`str | None` return rule.

The module authors **no commands**: a legacy `commands` dict is rejected at
load (#317), and the old `NAME` / prompt constants are no longer read. The A3
dir is also required — a `platforms_py/<name>.py` with no co-named
`platforms/<name>/` dir is not registered (the registry warns at import, and
the data lint flags both the orphan module and a `handler:` command on a
platform that ships no module).
