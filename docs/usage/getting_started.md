# Basic Usage
SIMNOS has some built in default hosts which are used in case that no `inventory` is given. In such case it will open the following:

- **router_cisco_ios**: a device with username `user` and password `user` in the port 6000. The platform is `cisco_ios`.
- **router_huawei_smartax**: a device with username `user` and password `user` in the port 6001. The platform is `huawei_smartax`.
- **router_arista_eos**: a device with username `user` and password `user` in the port 6002. The platform is `arista_eos`.

In all cases, the fake devices are running on the localhost or 127.0.0.1 address. To run those just use the following code:

```python
from simnos import SimNOS

network = SimNOS()
network.start()
```

Initiate SSH connection using default username `user` and password `user`:

```bash
ssh -p 6000 user@localhost # cisco_ios
ssh -p 6001 user@localhost # huawei_smartax
```

## Interactive line editing (SSH)

When you connect over **SSH** interactively, SIMNOS gives you real-device-style
line editing:

- **←/→** move the cursor within the line; **↑/↓** browse command history.
- **Backspace** / **Delete** edit the current line.
- **Tab** completes a command from those valid in the current mode.
- **`?`** (typed alone, followed by **Enter**) lists the commands available in the current mode.

Editing only reacts to those interactive keystrokes. Automation tools that send
whole lines (Netmiko, Scrapli, Ansible) never trigger it, so they see exactly the
same plain byte stream as before — the editing layer never alters the wire for a
scraper. This means **one running instance serves both a human SSH session and an
automation client identically**: connect by hand to verify behaviour, then point
Netmiko at the same port.

Line editing is **SSH-only**; the Telnet server keeps the plain (non-editing)
stream.

## Command abbreviation

Like a real NOS, SIMNOS accepts **abbreviated commands**: each token may be
shortened to an unambiguous prefix, so `sh ver` runs `show version` and `conf t`
runs `configure terminal`. This works on both SSH and Telnet, and on both the
exact-typed and Tab-completed forms.

- Every token must be present — trailing tokens cannot be dropped. A strict
  prefix of a longer command (e.g. `sh ip`) answers `% Incomplete command.`,
  matching real IOS.
- An abbreviation that matches more than one command answers
  `% Ambiguous command:  "<input>"`.
- Abbreviation only fires when the typed line is **not** an exact command, so a
  full command's bytes on the wire are unchanged — scrapers that send full
  commands are never affected.

Resolution and Tab completion target each command's **canonical** spelling, so
aliases resolve toward their canonical form (a full alias still works when typed
in full). The default `% Ambiguous` / `% Incomplete` wording is Cisco IOS style;
a platform can override it from its data (the `_ambiguous_` / `_incomplete_`
commands, alongside `_default_`).

The equivalent to running above code would be to run SIMNOS CLI without
any arguments:

```bash
simnos up
```

!!! warning "Security notice"
    SIMNOS is intended for **testing and development only**. Be aware of the following defaults:

    - **Default credentials**: The built-in inventory uses `user`/`user`. Change these in your inventory for any non-local deployment.
    - **Default SSH host key**: When no custom key is provided, SIMNOS auto-generates an RSA host key at startup. The same key is shared across all hosts within a single process. This key is not persisted across restarts, so SSH clients may see host key warnings after a restart. Provide a custom key via `ssh_key_file` in the server configuration for non-local use.
    - **Bind address**: By default SIMNOS binds to `127.0.0.1` (localhost only). In Docker/WSL environments it may bind to `0.0.0.0` (all interfaces), exposing the service to the network.
