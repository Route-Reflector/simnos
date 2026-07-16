# Creating a NOS plugin

A NOS plugin is what an inventory host's `device_type` / `nos.plugin` resolves
to: the command data plus (optionally) dynamic behavior. Since v3 (#317) there
is exactly **one authoring form**:

- an **A3 platform directory** — `platform.yaml` (modes + metadata) and one
  `commands/<stem>.yaml` per command with adjacent `.txt` / `.j2` output.
  This is the required part; a platform with no A3 dir cannot serve commands.
- an optional **Python handler module** — a `BaseDevice` subclass (plus
  module-level functions) whose methods the A3 `handler:` field binds to at
  server start. This is the only job the py module has: it authors **no
  commands** (the legacy `commands` dict, `NAME` / `INITIAL_PROMPT` /
  `ENABLE_PROMPT` / `CONFIG_PROMPT` constants and `Nos.from_dict` were removed
  in #317).

The full A3 authoring reference (file layout, `platform.yaml`, per-command
fields, lint conventions) lives in
[Adding new platforms](creating_new_platforms.md). This page covers the two
plugin-specific topics: shipping a platform **outside** the SIMNOS package,
and the **handler contract**.

## An external custom platform

A platform does not have to live inside the SIMNOS package tree. Author the
same A3 dir anywhere on disk:

```
my_platform/
  platform.yaml
  commands/
    show_version.yaml
    show_version.txt
    show_marker.yaml      # handler: make_show_marker
    default.yaml          # _default_
    default.txt
my_platform_handlers.py   # optional: device class + handler callables
```

### Static-only platform (no handlers)

Point the inventory host directly at the directory:

```yaml
hosts:
    R1:
        username: user
        password: user
        port: 0
        nos:
            plugin: path/to/my_platform
```

```bash
simnos up -i path/to/inventory.yaml
```

Equivalently in Python, register the directory path (a str plugin must be an
A3 platform dir — `.py` paths and dict plugins are rejected):

```python
from simnos import SimNOS

net = SimNOS(inventory=inventory, plugins=["path/to/my_platform"])
```

### Platform with dynamic handlers

A `handler:` command needs the handler module loaded alongside the A3 dir, so
build the `Nos` yourself and register the instance. The platform name is the
A3 directory's basename; the inventory references it by that name:

```python
from simnos import Nos, SimNOS

nos = Nos(filename=["path/to/my_platform", "path/to/my_platform_handlers.py"])

inventory = {
    "hosts": {
        "R1": {
            "username": "user",
            "password": "user",
            "port": 0,
            "nos": {"plugin": "my_platform"},
        },
    }
}

net = SimNOS(inventory=inventory, plugins=[nos])
net.start()
```

An unresolved `handler:` reference (no such callable in the module) fails
loudly at `start()` — never a silently output-less command.

## The Python handler module

The module defines at most one locally-defined `BaseDevice` subclass — it is
**auto-detected** (importing other device classes is fine; only locally
defined subclasses count, and two or more is a loud `ValueError`). Its
non-underscore methods, plus locally-defined module-level functions, form the
platform's **handler namespace**; an A3 command references one by name:

```yaml
# commands/show_marker.yaml
command: show marker
type: custom
help: dynamic marker command
mode: [user, enable]
handler: make_show_marker
```

```python
"""my_platform_handlers.py"""

from simnos.plugins.nos.base_device import BaseDevice

DEFAULT_CONFIGURATION = "path/to/configurations/my_platform.yaml.j2"  # optional


class MyPlatform(BaseDevice):
    """Holds per-device state shared between handlers."""

    def make_show_marker(self, base_prompt, current_mode, current_prompt, command):
        return f"marker from {current_mode}"
```

A name defined both as a device-class method and a module-level function is a
load-time error (no implicit precedence). A `classmethod` cannot be a handler
(its first argument binds to `cls`, not the device).

The class instance is shared across a host's sessions, so handlers can keep
state (e.g. a command that changes the device's IP; later commands see the
change). `BaseDevice` provides `self.configurations` (loaded from the optional
`DEFAULT_CONFIGURATION` YAML / Jinja2 [configuration](../usage/configurations.md)
file; `Nos(configuration_file=...)` overrides it) and a
`render(template, **kwargs)` helper for Jinja2 templates under
`simnos/plugins/nos/platforms_py/templates/`.

## The callable contract

The typed contract lives in `simnos.core.command_contract` (the
`CommandHandler` Protocol) — import it for type annotations if you like;
plain functions matching the shape work as-is.

The shell invokes a handler as:

```python
handler(device, base_prompt=..., current_mode=..., current_prompt=..., command=...)
```

where `device` is the instance of your `BaseDevice` subclass (or `None` for a
platform without a device class). A device-class method satisfies this
naturally: `device` binds as `self`. `command` is the literal line the user
typed (an abbreviation like `sh ver` arrives unexpanded).

A handler returns its **output only** (#317):

- `str` - output string to display
- `None` - no response

Mode transitions and session close are static authoring data (`new_mode` /
`exit` / `transitions` on the command), not handler returns — the former
dict-return `CommandResult` form was removed. A handler that still returns a
dict (or anything but `str | None`) is answered with the fixed
`% Internal error` line and an error log. Branch on the `current_mode`
argument, not on the prompt string.

Two rules that differ from static output files:

- **Format yourself.** The shell does *not* render handler output — handlers
  receive `base_prompt` as an argument and build their own strings. Literal
  braces in device output need no escaping.
- **Raising is allowed** for "should never happen" states: the shell logs the
  full traceback server-side and answers the client with the fixed
  `% Internal error` line — no traceback ever reaches the wire.

## Migrating a v2 plugin

A v2-era py plugin (module `commands` dict + prompt constants) no longer
loads: the `commands` dict is rejected at load, and the constants are simply
not read. Move each dict entry into an A3 `commands/<stem>.yaml`
(`prompt:` → `mode:` names, `new_prompt:` → `new_mode:`, output text →
adjacent `.txt` / `.j2`), declare the modes in `platform.yaml`, and keep only
the device class + handler callables in the module — see the
[changelog migration table](../changelog.md) and
[Adding new platforms](creating_new_platforms.md).
