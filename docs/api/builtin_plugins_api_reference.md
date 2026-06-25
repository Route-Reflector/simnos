## NOS Plugins

NOS plugins are at the heart of SIMNOS, they are what enables to realize its
full potential.

### Cisco IOS

::: simnos.plugins.nos.platforms_py.cisco_ios
    rendering:
      show_if_no_docstring: true
      heading_level: 4
      show_object_full_path: false

## Server Plugins

Server plugins act as an access layer, simulating device connections.

### AsyncSshServer

::: simnos.plugins.servers.ssh_server_asyncssh.AsyncSshServer
    rendering:
      heading_level: 4
      show_object_full_path: false

### TelnetServer

::: simnos.plugins.servers.telnet_server.TelnetServer
    rendering:
      heading_level: 4
      show_object_full_path: false

### Internal

#### AsyncServerBase

Shared async-server lifecycle (start/stop/aclose, session registry, dispatch
wiring) on the SimNOS-owned shared event loop. This is an internal base class,
not a public API.

::: simnos.plugins.servers.async_server_base.AsyncServerBase
    rendering:
      heading_level: 5
      show_object_full_path: false

## Shell Plugins

Shell plugins act as plumbing between server plugins and NOS plugins,
connecting them together.

### CMDShell

::: simnos.plugins.shell.cmd_shell.CMDShell
    rendering:
      heading_level: 4
      show_object_full_path: false

## Tape Plugins

Idea - Tape Plugins will allow to record interactions with real devices and build
NOS plugins automatically using gathered data.
