# Adding new platforms
SIMNOS is designed to be easily extensible. A platform's static command data
lives in an **A3 platform directory**; dynamic behavior is added with an
optional Python module. The two compose: the A3 dir provides the static
commands and modes, and a co-named Python module can add handlers / a device
class on top (#264).

!!! tip
    A hot-reloader reloads **Python modules** when they change inside
    `simnos/plugins/nos` (`simnos --reload-commands`). Hot-reload of an A3
    platform directory is a separate, deferred capability (#274); for now an A3
    edit is picked up on the next server start.

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
- **`new_mode`** names the mode to transition to after the command runs
  (the successor of the legacy `new_prompt`).
- **`variants`** is the multi-capture contract: a list of `{name, output}`
  entries (`variant_1` mirrors the primary, `variant_2`.. are alternates), each
  pointing at its own `.txt`.
- **`alias`** makes the command a pure reference to another command — it carries
  no other dispatch fields.
- **`exit`** marks a session-closing command.
- **`_default_`** is the mode-agnostic unknown-command fallback: author the
  platform's real error wording (e.g. Cisco IOS `% Invalid input detected at
  '^' marker.`; vendor wording differs, do not copy-paste). It takes no `mode`.

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
This method adds dynamic behavior on top of (or instead of) the static A3 data:
handlers and a device class with the full power of Python. The Python modules
are located in the `simnos/plugins/nos/platforms_py` package; a module co-named
with an A3 platform is merged over it (its commands win per-command).
