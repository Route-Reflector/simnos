# Inventory
SIMNOS uses an inventory to define a set of network device hosts and their configuration. It is a key part to the project. The inventory is a dictionary that contains two sections: `default` and `hosts`. The `default` section contains parameters and configuration that SIMNOS uses by default for each host. The `hosts` section is a dictionary keyed by hosts' names containing host definition. Any parameter defined per-host overrides parameters defined in the `default` section.

There are two ways to provide inventory data to SIMNOS:

1. Using YAML file
2. Using Python dictionary

!!! warning "Migrating from v2: `platform` → `device_type`"
    SIMNOS v3 renamed the inventory key `platform` to `device_type` (aligning with
    netmiko / ansible). This is a **breaking change with no compatibility alias**:
    a v2 inventory that still uses `platform:` is rejected at load. There are two
    migration paths:

    - **Pin to v2** if you need the old format unchanged. The v2 line (the current
      `main` branch) is kept maintained as a migration window:
      `pip install "simnos<3"`.
    - **Rewrite the key** to move to v3. In a YAML inventory:

        ```bash
        sed -i 's/^\([[:space:]]*\)platform:/\1device_type:/' inventory.yaml
        ```

        In a Python-dict inventory, rename the `"platform"` key to `"device_type"`.

    A `device_type` may be named by a platform's internal name (`cisco_ios`), its
    `netmiko_device_type`, or its `ntc_platform` alias — all resolve to the same
    platform.

## Basic structure
In all cases the inventory data must have the following structure independently of the method used to provide it:

- **default**: A dictionary containing default parameters and configuration that SIMNOS uses by default for each host.
- **hosts**: A dictionary keyed by hosts' names containing host definition. Any parameter defined per-host overrides parameters defined in the `default` section.

It is mandatory always to provide the `hosts` section. The `default` section is optional. If not provided, SIMNOS uses a default configuration. This structure works in hierarchical way, so the `hosts` section will override the `default` section.

!!! warning
    Even though you can freely change the default parameters, it is recommended to keep them as they are and override them through the `hosts` section. In case you change the `default` section, you must provide all the parameters that are in the default configuration.

### Default inventory
If no inventory data provided on SIMNOS object instantiation, SIMNOS falls back on using default inventory configuration. These are the current defaults[^1]:
``` py linenums="1" hl_lines="16 17 18 19"
default_inventory = {
    "default": {
        "username": "user",
        "password": "user",
        "port": 6000,
        "server": {
            "plugin": "AsyncSshServer",
            "configuration": {
                "address": "127.0.0.1",
                "timeout": 1,
            },
        },
        "shell": {"plugin": "CMDShell", "configuration": {}},
        "nos": {"plugin": "cisco_ios", "configuration": {}},
    },
    "hosts": {
        "router_cisco_ios": {"port": 6000, "device_type": "cisco_ios"},
        "router_huawei_smartax": {"port": 6001, "device_type": "huawei_smartax"},
        "router_arista_eos": {"port": 6002, "device_type": "arista_eos"},
    }
}
```

## YAML
This is the easier way to provide inventory data. In a simple YAML file, you can define the inventory data. The YAML file must have the following structure:

``` yaml
default:
  username: user
  password: user
  port: 6000
  device_type: cisco_ios
```

In this case, it will create a host named `router0` with the username `user`, password `user`, and port `6000`. The platform will be `cisco_ios`. If you want to create more hosts, you can add them to the `hosts` section:

``` yaml
hosts:
    router1:
        port: 6001
        device_type: huawei_smartax
    router2:
        port: 6002
        device_type: cisco_ios
```

In this case, you are creating 2 hosts: `router1` and `router2`. `router1` will have the port `6001` and the platform `huawei_smartax`. `router2` will have the port `6002` and the platform `cisco_ios`. As the credentials are not provided in the `hosts` section, SIMNOS will use the default credentials.

To use the YAML file, you can use the SIMNOS CLI tool:

``` bash
simnos up -i path/to/inventory.yaml
```

### CLI subcommands

The CLI is organized into subcommands:

``` bash
# Start the predefined 3-host example (no inventory needed):
simnos up

# Start a single host ad-hoc, without writing an inventory file:
simnos up --device-type cisco_ios --port 6000

# Start from an inventory file:
simnos up -i path/to/inventory.yaml

# List the platforms you can use as a device_type:
simnos list-platforms
```

`simnos up` accepts `--device-type` (`-d`) for an ad-hoc single host, or
`-i`/`--inventory` for a file — the two are mutually exclusive. With neither, the
built-in 3-host example starts. Ad-hoc credentials default to the built-in
`user`/`user`; override them with `--username`/`--password`. The log level is set
with `-l`/`--log-level` after the subcommand (e.g. `simnos up -l DEBUG`).

## Python dictionary
Although YAML is the easier way to provide inventory data to SIMNOS, using Python dictionary is more flexible and allows for more complex inventory data structures. As a matter of fact, python dictionaries are used internally by SIMNOS to handle the inventory data.

In case you want to use your own Python dictionary, you can provide it directly to SIMNOS. In the following code we are doing exactly the same as the first code in YAML:

``` python
from simnos import SimNOS

inventory_data = {
    "hosts": {
        "router1": {
            "username": "user",
            "password": "user",
            "port": 6000,
            "device_type": "cisco_ios",
        }
    }
}

network = SimNOS(inventory=inventory_data)
```

As before, in case that you want to create more hosts, you can add them to the `hosts` section:

``` python
inventory_data = {
    "hosts": {
        "router1": {"port": 6001, "device_type": "huawei_smartax"},
        "router2": {"port": 6002, "device_type": "cisco_ios"}
    }
}
```


## Other examples
Sample inventory data and code to start the servers:

```{ .python .annotate }
from simnos import SimNOS

fake_network = {
    "default": { # (4)
        "username": "user",
        "password": "user",
        "port": [5000, 6000],
        "server": {
            "plugin": "AsyncSshServer",
            "configuration": {
                "ssh_key_file": "./ssh-keys/ssh_host_rsa_key",
                "timeout": 1,
                "address": "127.0.0.1",
            },
        },
        "shell": {"plugin": "CMDShell", "configuration": {}},
        "nos": {"plugin": "cisco_ios", "configuration": {}},
    },
    "hosts": {
        "R1": {
            "port": 5001,
            "username": "simnos", # (2)
            "password": "simnos",
            "server": {
                "plugin": "AsyncSshServer",
                "configuration": {"address": "0.0.0.0"},  # (1)
            },
            "shell": {
                "plugin": "CMDShell",
                "configuration": {"intro": "Custom SSH Shell"},
            },
        },
        "R2": {},
        "core-router": {"replicas": 2, "port": [5000, 6000]}, # (3)
    },
}

network = SimNOS(inventory=fake_network)
network.start()

print(network.list_hosts())
```

1. `0.0.0.0` - Listen for connections on all interfaces
2. Override `username` and `password` defined in `default` section
3. Start two hosts `core-router1` and `core-router2` using next available
   ports from provided range
4. Settings used by all hosts by default

Alternative to running above code is to supply custom inventory to
SIMNOS CLI tool:

```bash
simnos up -i path/to/my_inventory.yaml
```

Where `my_inventory.yaml` could contain equivalent to above Python code
YAML structured inventory:

```yaml
default:
  password: user
  username: user
  port: [5000, 6000]
  server:
    plugin: AsyncSshServer
    configuration:
      address: 127.0.0.1
      ssh_key_file: ./ssh-keys/ssh_host_rsa_key
      timeout: 1
  shell:
    configuration: {}
    plugin: CMDShell
  nos:
    configuration: {}
    plugin: cisco_ios
hosts:
  R1:
    password: simnos
    port: 5001
    username: simnos
    server:
      plugin: AsyncSshServer
      configuration:
        address: 0.0.0.0
    shell:
      plugin: CMDShell
      configuration:
        intro: Custom SSH Shell
  R2: {}
  core-router:
    replicas: 2
    port: [5000, 6000]
```

Or could contain this simplified inventory:

```yaml
default:
  password: user
  username: user
  port: [5000, 6000]
  server:
    plugin: AsyncSshServer
    configuration:
      address: 0.0.0.0
hosts:
  router:
    replicas: 10
    device_type: cisco_ios
```

### Hosts replicas
You could see before that some host have the replicas flag set. Host definition can contain `replicas` parameter to define hosts in bulk, e.g. this inventory:

```python
inventory_data = {
    "hosts": {
        "router": {"replicas": 10, "port": [5001, 6000]}
    }
}
```

This configuration will result in SIMNOS running 10 instances of hosts servers named `router0` to `router9` using ports 5001 to 5010 respectively. That makes it very easy to define sets of hosts that use same configuration to scale the setup out.

!!! warning
    If host inventory data contains `replicas` parameter, `port` parameter must be a list
    of two integers representing range to allocate ports from. If host does not contains
    `replicas` parameter, `port` must be a positive integer from 1 - 65535 range.

## Generating SSH private key

By default SIMNOS uses SSH private key embedded with the package, making that key publicly available, which is insecure. Instead, SIMNOS can use locally generated SSH key.

### Linux and MacOS

Use the command `ssh-keygen -A` in terminal to generate all of your SSH keys. Once the command is run,
you can find the RSA key in the following location: `~/.ssh/id_rsa` a.k.a. `/home/<username>/.ssh/id_rsa`.
Supply above path as `ssh_key_file` argument to SIMNOS server configuration.

Alternatively can use `ssh-keygen -t rsa -f ssh-keys/ssh_host_rsa_key` command to generate private key.

### Windows 10

Press Windows Key, type `Manage Optional Features`. If OpenSSH Client & Server is in the list, you're all set.
If either is not, click on "Add a feature" and search for `OpenSSH`, click on them to install.
Next, open cmd as administrator. Enter the command `ssh-keygen` and follow the on screen prompts.
The location of the key will be displayed. Supply displayed path as `ssh_key_file` argument to SIMNOS
server configuration. If you put a password, include it as the `ssh_key_file_password` parameter.


## Inventory JSON Schema

SIMNOS internally uses [Pydantic](https://docs.pydantic.dev/latest/concepts/models/)
models to validate inventory data and raise `ValidationError` if inventory does
not comply with defined schema. The server section supports both `AsyncSshServer` (SSH)
and `TelnetServer` (Telnet) plugins.

You can generate the current JSON Schema with:

```python
import json
from simnos.core.pydantic_models import ModelSimnosInventory
print(json.dumps(ModelSimnosInventory.model_json_schema(), indent=4))
```

Key points of the schema:

- `server` accepts either `AsyncSshServerPlugin` or `TelnetServerPlugin` (via `anyOf`)
- `AsyncSshServerConfig` includes: `ssh_key_file`, `ssh_key_file_password`, `ssh_banner`, `timeout`, `address`, `watchdog_interval`, `authorized_keys`
- `TelnetServerConfig` includes: `banner`, `timeout`, `address`, `watchdog_interval`
- All configuration fields are optional with sensible defaults

## Inventory options
The following options can be used either in the `default` section or in the `hosts` section to override the default values.

### Top-level options

| Option        | Emoji         | Description                        | E.g.                                            |
| --------------| ------------- | ---------------------------------- | ----------------------------------------------- |
| `username`    | :person:      | username of the device             | `username: admin`                               |
| `password`    | :key:         | password of the device             | `password: admin`                               |
| `device_type` | :station:     | network operating system used      | `device_type: cisco_ios`                        |
| `port`        | :ship:        | port to connect to                 | `port: 6000`                                    |
| `replicas`    | :repeat:      | number of hosts to create          | `replicas: 10`                                  |
| `server`      | :satellite:   | server configuration               | See section [Server options](#server-options)   |
| `shell`       | :shell:       | shell configuration                | See section [Shell options](#shell-options)     |
| `nos`         | :computer:    | NOS configuration                  | See section [NOS options](#nos-options)         |
| `overlay`     | :card_index_dividers: | custom command overlay     | See section [Custom command overlay](#custom-command-overlay-data-layering) |
| `variants_policy` | :game_die:        | which variant a multi-capture command serves | See section [Variant selection](#variant-selection-variants_policy) |

### Server options

| Option                    | Emoji                     | Description                           | E.g.                                                                      |
| ------------------------- | ------------------------- | ------------------------------------- | ------------------------------------------------------------------------- |
| `plugin`                  | :electric_plug:           | server plugin to use                  | `plugin: AsyncSshServer`                                               |
| `configuration`           | :gear:                    | server configuration                  | See section [Server configuration options](#server-configuration-options) |

### Server configuration options

SIMNOS supports two server plugins: **AsyncSshServer** (SSH, default) and **TelnetServer** (Telnet).

#### Common options (both SSH and Telnet)

| Option                    | Emoji                     | Description                           | E.g.                                           |
| ------------------------- | ------------------------- | ------------------------------------- | ---------------------------------------------- |
| `timeout`                 | :hourglass:               | safety-net timeout for select (sec)   | `timeout: 1`                                   |
| `address`                 | :globe_with_meridians:    | address to bind server to             | `address: 127.0.0.1`                           |
| `watchdog_interval`       | :dog:                     | interval for watchdog                 | `watchdog_interval: 1`                         |

#### AsyncSshServer options

| Option                    | Emoji                     | Description                           | E.g.                                           |
| ------------------------- | ------------------------- | ------------------------------------- | ---------------------------------------------- |
| `ssh_key_file`            | :key:                     | path to SSH private key file          | `ssh_key_file: /path/to/ssh_key`               |
| `ssh_key_file_password`   | :key:                     | password for SSH private key          | `ssh_key_file_password: password`              |
| `ssh_banner`              | :scroll:                  | SSH banner to display                 | `ssh_banner: "Welcome to SIMNOS SSH Server"`   |
| `authorized_keys`         | :lock:                    | path to authorized_keys file          | `authorized_keys: /path/to/authorized_keys`    |

#### TelnetServer options

| Option                    | Emoji                     | Description                           | E.g.                                           |
| ------------------------- | ------------------------- | ------------------------------------- | ---------------------------------------------- |
| `banner`                  | :scroll:                  | Telnet banner to display              | `banner: "Welcome to SIMNOS Telnet Server"`    |

To use the Telnet server, set the `plugin` to `TelnetServer` in the server section:

```yaml
server:
  plugin: TelnetServer
  configuration:
    banner: "SIMNOS Telnet Server"
    address: "127.0.0.1"
```


### Shell options

| Option                    | Emoji                     | Description                           | E.g.                                                                    |
| ------------------------- | ------------------------- | ------------------------------------- | ----------------------------------------------------------------------- |
| `plugin`                  | :electric_plug:           | shell plugin to use                   | `plugin: CMDShell`                                                      |
| `configuration`           | :gear:                    | shell configuration                   | The configuration entirely rely on the plugin                           |


### NOS options

| Option                    | Emoji                     | Description                           | E.g.                                                                    |
| ------------------------- | ------------------------- | ------------------------------------- | ----------------------------------------------------------------------- |
| `plugin`                  | :electric_plug:           | NOS plugin to use                     | `plugin: cisco_ios`                                                     |
| `configuration`           | :gear:                    | NOS configuration                     | The configuration entirely rely on the plugin                           |


## Custom command overlay (data layering)

The overlay lets you **replace the output of a packaged command** — or **add a
command the package does not ship** — by dropping a captured output file next to
SIMNOS instead of editing the packaged data. Because the files live outside the
package, they survive a `pip` upgrade.

It is the right tool when the *whole output* of a command differs (e.g. a capture
from a specific device or OS version). When only *values* differ (hostname,
serial, …) that is host facts, a separate mechanism.

### Where the files live: `sys_config.data_dir`

Overlay files live under an environment-global directory set in `sys_config.yaml`:

```yaml
# sys_config.yaml
data_dir: /srv/simnos/overlays
```

`sys_config.yaml` is discovered from (in order) the `SimNOS(sys_config=...)` arg,
the `SIMNOS_SYS_CONFIG` env var, `./sys_config.yaml`, then
`~/.simnos/sys_config.yaml`. `SIMNOS_DATA_DIR` overrides the file's `data_dir`.

Each platform reads from its own subdirectory named by the **internal platform
name** (the registry key — e.g. `cisco_ios`, the same name `ntc_platform`
resolves to), not the netmiko `device_type` alias:

```
/srv/simnos/overlays/
└── cisco_ios/
    ├── show_version.txt          # replaces `show version` output
    └── show_run.txt              # adds `show run` (absent from the package)
```

Output files are **`.txt`** (literal wire text) or **`.j2`** (a jinja2 template).
A `.j2` may reference `{{ base_prompt }}` plus values supplied by an adjacent
**sidecar `<stem>.json`** — see [Template render values](#template-render-values-sidecar-json).
A `.j2` that needs a value with no sidecar to supply it is a loud build-time
error. A filename's stem maps to a command name by turning `_` into a space:
`show_version.txt` → `show version` (matching the NTC raw-capture naming
convention, case-sensitive).

### Opting in: `overlay.override_commands`

A host pulls from the overlay dir only when its inventory sets
`overlay.override_commands`. It takes three forms:

```yaml
hosts:
  R1:
    device_type: cisco_ios
    overlay:
      override_commands: all                         # apply every .txt/.j2 in the dir
  R2:
    device_type: cisco_ios
    overlay:
      override_commands: ["show version", "show run"] # these commands, default-name files
  R3:
    device_type: cisco_ios
    overlay:
      override_commands:                              # explicit per-host capture file
        show version: show_version_B.txt
```

- **`all`** — apply every `.txt` / `.j2` in `<data_dir>/<platform>/`.
- **list** — apply each named command by its default-name file (`show version`
  → `show_version.txt` / `.j2`).
- **map** — `{command: filename}`, so two hosts can pull *different* capture files
  for the same command (R1 → `show_version_A.txt`, R2 → `show_version_B.txt`).

A command found in the packaged data is an **output-only override** — only its
output is swapped; its modes / help / type are inherited. A command absent from
the package becomes a **new command**, valid in every mode. Unset / empty
`override_commands` means the overlay is not applied (no behaviour change).

### Notes and limits

- **Opt-in is loud.** If `override_commands` is set but `data_dir` is unconfigured,
  the platform's overlay dir is missing, or a listed/mapped command has no file,
  startup fails with an error — an opt-in that cannot be satisfied never silently
  falls back to packaged output.
- **A3 platforms only.** Python-only (py-only) platforms do not support overlays.
- **Filenames are bare names, matched exactly.** A list / `all` entry is matched
  case-sensitively against the default-name file, so use the packaged command's
  exact lowercase spelling. A command name that does not map cleanly to a
  `stem_with_underscores.txt` filename (anything with `/` or other path
  characters) must be selected with the **map** form, giving an explicit bare
  filename — the list / `all` forms reject a non-bare generated name.
- **Multi-capture commands.** Overriding a command that ships multiple captures
  (variants) collapses it to the single overlay output (logged at INFO).
- **Not hot-reloaded.** The overlay dir is outside the packaged tree the dev
  hot-reload watcher sees; an overlay change takes effect on reconnect.
- **Growing the catalog.** For mode-specific commands or commands you want to
  share, contributing a packaged command (an A3 `commands/<cmd>.yaml` + output
  file) is the canonical route; the overlay is for local, output-only tweaks.

## Template render values (sidecar JSON)

A `.j2` command output (packaged or overlay) renders from `{{ base_prompt }}`
**plus** values read from an adjacent **sidecar `<stem>.json`** — the verbatim
`--parse` output of a KeroRoute / [ntc-templates](https://github.com/networktocode/ntc-templates)
run. This lets you change *values* (not the whole output) — for example bump the
reported software version — to exercise a client's version-conditional logic
without owning hardware at that version. Re-parsing the rendered output returns
your edited value (a per-command **round-trip**).

```
cisco_ios/commands/
├── show_version.j2      # ...Version {{ parsed[0].version }}, RELEASE...
└── show_version.json    # the --parse output that supplies `version`
```

The sidecar is normalized into a render namespace where the parsed rows are
always reachable as **`parsed`**, regardless of how KeroRoute saved them:

- an **envelope** `[{ "command": "show version", "parsed": [ ... ] }]` — the
  entry whose `command` matches is selected (whitespace/case-insensitive);
- a **bare row list** `[ { ...row... }, ... ]` (textfsm) — wrapped as `parsed`;
- a **plain object** `{ ... }` — used as-is.

So a template writes `{{ parsed[0].version }}` (single record) or
`{% for row in parsed %}…{% endfor %}` (table). The packaged `cisco_ios`
`show version` and `show ip interface brief` ship as `.j2` + sidecar demos.

Validation is **loud at build time**: a `.j2` whose required value the sidecar
does not supply (top-level or a missing nested key), or a sidecar using the
reserved `base_prompt` key, fails at startup — never silently at connect time.
For a **packaged** sidecar (inside an A3 platform dir), editing the `.json`
triggers the dev hot-reload like editing the `.j2`. An **overlay** sidecar lives
under the external `data_dir`, which the watcher does not see, so an overlay
sidecar edit takes effect on reconnect (same as the overlay `.txt`/`.j2`).

> Per-command sidecar values are command-local. Cross-command coherence
> (changing a hostname/interface once and having every command agree) is a
> separate **global facts** mechanism deferred to a future release; the
> `facts` inventory field is reserved for it and currently a no-op (warned).

## Variant selection (`variants_policy`)

Some packaged commands ship **multiple captures** of one command — different
router states (a feature configured vs not). By default SIMNOS serves the first
(`variants[0]`). `variants_policy` (per host, or as a `sys_config.yaml` global
default under the inventory) picks which one, and stays fixed for the whole SSH
session (the box does not change state mid-session):

```yaml
hosts:
  R1:
    device_type: cisco_ios
    variants_policy:
      select: 0          # int index (default 0) — fully deterministic
  R2:
    device_type: cisco_ios
    variants_policy:
      select: random     # pick one at connect time
      seed: 1234          # optional: reproducible, sticky per host
```

- **`select: <int>`** — pin that index (default `0`). Out-of-range is a loud
  error, not a silent wrap.
- **`select: random` + `seed`** — reproducible: the same `seed` + host always
  resolves to the same variant (sticky across reconnects); different hosts spread
  across states.
- **`select: random`** with no `seed` — a fresh random draw each connection
  (realism — "you don't know which state the box is in until you connect"); not
  reproducible.

Determinism is the default; randomness is a deliberate double opt-in. An overlay
that collapses a multi-capture command to a single output (above) takes it out of
variant selection.

[^1]: To see the current defaults, check the [source code](https://github.com/Route-Reflector/simnos/blob/main/simnos/core/simnos.py) of SIMNOS.
