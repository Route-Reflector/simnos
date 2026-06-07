# Adding new platforms
SIMNOS is designed to be easily extensible. It is designed in such
a way that adding new platforms is simple and can be done using different
methods. At the moment, it is possible only using Python modules or YAML files.

!!! tip
    There is implemented a hot-reloader that automatically reloads Python modules
    and YAML files when they are modified inside `simnos/plugins/nos`. To run it
    simply do `simnos --reload-commands`.

## YAML files
This is preferred way in case that the platform you want to implement is not
existing yet. The great advantage of this method is that it is fairly simple
to add new platforms. However, it is not as flexible as the Python module method
as it is not possible to implement dynamic behavior.

The YAML files are located in the `simnos/plugins/nos/platforms_yaml` directory.

### Templating rules

String fields in the YAML (`initial_prompt` and per-command `output` /
`prompt` / `new_prompt`) are rendered with Python's `str.format()` at
runtime. Top-level `enable_prompt` / `config_prompt` are not consumed by the
runtime shell today (Python plugins use their own module constants), but they
are written in the same template style and validated preventively by the CI
sweep. Only two constructs are supported:

- `{base_prompt}` — replaced with the device's base prompt (hostname):

    ```yaml
    initial_prompt: "{base_prompt}>"
    ```

- `{{` / `}}` — escapes for a literal `{` / `}` in the output:

    ```yaml
    output: "{{master:0}}"   # renders as: {master:0}
    ```

Anything else from the format mini-language is **not supported** and is
treated as an authoring error: attribute access (`{base_prompt.foo}`), index
access (`{base_prompt[0]}`), format specs (`{base_prompt:d}`), positional
placeholders (`{}` / `{0}`), and unknown names (`{hostname}`). This includes
constructs that `str.format()` would render without raising — e.g.
`{base_prompt!r}` or `{base_prompt:>20}` — the build-time check rejects them
explicitly.

On a malformed template:

- **Runtime** is lenient — the error is logged and the session degrades
  safely instead of crashing: a broken `output` is sent unformatted, a broken
  `prompt` candidate never matches (the command becomes unreachable), a
  broken `new_prompt` keeps the current prompt.
- **Build time** is loud — `invoke gen_docs_platform_commands` and the CI
  template sweep (`tests/test_gen_docs_platform_commands.py`) raise a
  `RuntimeError` naming the platform / command / field.

### Prompt keys

The three top-level prompt keys describe the CLI's mode prompts:

- `initial_prompt` — the prompt right after login. This is the only one the
  runtime shell consumes directly (it becomes the session's first prompt).
- `enable_prompt` — the privileged-mode prompt (Cisco `enable` style).
- `config_prompt` — the configuration-mode prompt.

`enable_prompt` / `config_prompt` are authoring metadata: mode transitions
are driven entirely by per-command `prompt` / `new_prompt` values, so use
these keys to document the platform's modes, not to drive behavior. The
naming is Cisco-flavored; for platforms whose real CLI does not fit it,
keep the **real device prompt** and accept the naming mismatch — e.g.
`hp_comware` stores the Comware *system view* prompt (`[{base_prompt}]`)
under `config_prompt`, which is accurate for the device even though Comware
has no "config mode" of that name. Platforms with a flat CLI (no modes,
e.g. D-Link xStack) should simply leave these keys out.

### Authoring conventions

These are enforced by `invoke lint-platform-yaml` (CI + pre-commit) and the
yamllint `quoted-strings` rule:

- **Quote style**: if you quote a scalar, use double quotes. Single quotes
  are only kept where the real device output itself contains double quotes
  (marked with an inline `# yamllint disable-line rule:quoted-strings`).
- **`prompt` form**: both a bare string and a list are valid authoring
  sugar — the loader normalizes either to a list before commit, so runtime
  consumers always see lists.
- **`_default_` command**: every *new* platform must define one, with the
  platform's real unknown-command error (e.g. Cisco IOS answers
  `% Invalid input detected at '^' marker.`, NX-OS says `% Invalid command
  at '^' marker.` — vendor wording differs, do not copy-paste). Cite your
  source as a `# source: <URL> (retrieved YYYY-MM-DD)` comment right above
  the entry. Existing platforms without one are frozen in
  `platform_yaml_lint_baseline.yaml`; that baseline only ever shrinks.
- **`help` text**: write real help. Auto-generated stubs
  (`execute the command "X"`) are frozen in the baseline and new ones fail
  the lint.
- **`output_variants`**: an optional data-only field holding alternate
  captures of the same command's output. The runtime does not consume it;
  it is preserved because re-capturing device output is not always
  possible.

Unknown fields are rejected at load time: a typo'd top-level key raises a
`ValueError` and a typo'd command field fails the pydantic validation
(`extra="forbid"`), so mistakes surface immediately instead of being
dropped silently.


## Python modules
This method is more flexible than the YAML files method. It is possible to implement
dynamic behavior and to use the full power of Python. However, it is a little more difficult to
implement. The Python modules are located in the `simnos/plugins/nos/platforms_py` package.
