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

String fields in the YAML (`initial_prompt`, `enable_prompt`, `config_prompt`,
and per-command `output` / `prompt` / `new_prompt`) are rendered with Python's
`str.format()`. Only two constructs are supported:

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
placeholders (`{}` / `{0}`), and unknown names (`{hostname}`).

On a malformed template:

- **Runtime** is lenient — the error is logged and the session degrades
  safely instead of crashing: a broken `output` is sent unformatted, a broken
  `prompt` candidate never matches (the command becomes unreachable), a
  broken `new_prompt` keeps the current prompt.
- **Build time** is loud — `invoke gen_docs_platform_commands` and the CI
  template sweep (`tests/test_gen_docs_platform_commands.py`) raise a
  `RuntimeError` naming the platform / command / field.


## Python modules
This method is more flexible than the YAML files method. It is possible to implement
dynamic behavior and to use the full power of Python. However, it is a little more difficult to
implement. The Python modules are located in the `simnos/plugins/nos/platforms_py` package.
