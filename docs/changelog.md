# Changelog

All notable changes to SIMNOS are documented here.
For full details, see the [GitHub Releases](https://github.com/Route-Reflector/simnos/releases).

## Unreleased

<!-- At release, rename this heading to `## v3.0.0 - YYYY-MM-DD`. -->

SIMNOS v3 is a clean rewrite of the SSH/Telnet core and the plugin data
layout. The breaking changes are consolidated in the migration guide below;
each links to its detailed entry further down.

**Migration from v2**

_Staying on v2 (migration window)_ — v2 is maintained as a migration window for
critical / security fixes only. Pin to it until you are ready to move:

- PyPI: `pip install "simnos<3"`
- Docker: pin the major tag `simnos:2` (do not use `:latest`, which now tracks v3)
- git: pin the `v2.4.0` tag or the `2.x` maintenance branch

_Upgrading to v3_ — apply each change that affects you:

| If you… | Do this |
|---|---|
| use `platform:` in an inventory | Rename the key to `device_type:` — there is no alias, `platform:` is rejected at load (`sed -i 's/^\([[:space:]]*\)platform:/\1device_type:/' inventory.yaml`). See #266 |
| configure the `ParamikoSshServer` plugin | Drop it — `AsyncSshServer` is the default SSH plugin; `ssh_key_file` / `ssh_banner` / `authorized_keys` carry over unchanged. See #297 |
| run `simnos -i inventory.yaml` (or bare `simnos`) | Use the subcommand form: `simnos up -i inventory.yaml` (or `simnos up` for the default inventory). See #267 |
| hardcode listen port `6000` / `6001` / `6002` | Read the real port from `net.hosts[<name>].port` after `start()` (the CLI logs it); default ports are now OS-assigned. See #271 |
| set `ruler` / `completekey` in a shell `configuration` block | Remove them — they are rejected at load (`extra="forbid"`). See #303 |
| return a dict (`{"output", "new_mode", "exit"}`) from a custom command handler | Return `str` (or `None`) only, and author the transition statically on the command (A3 `new_mode` / `exit` / `transitions`) — a dict return now answers `% Internal error`. See #317 |
| define commands in an inventory `nos: configuration: commands:` block | Rewrite each entry to the A3 dialect: `prompt:` → `mode:` (mode names, e.g. `[user, enable]`), `new_prompt:` → `new_mode:`; a verbatim body stays in `output:` (now a raw literal — `{{`/`}}` escapes are no longer collapsed), a body containing `{base_prompt}` becomes `output_template:` with jinja2 `{{ base_prompt }}`. `alias` / `output_variants` entries are rejected. See #317 |
| author a NOS plugin as a py `commands` dict (a `platforms_py/<name>.py` dict, `Nos(commands=…)` / `from_dict`, or `SimNOS(plugins=[dict])`) | Move the command data into an A3 platform dir (`platforms/<name>/platform.yaml` + `commands/*.yaml` + adjacent `.txt`/`.j2`) and keep the py module for the device class + `handler:` callables only — the dict forms are rejected, and a py module with no co-named A3 dir is no longer registered. See #317 |
| rely on `paramiko` pulled in transitively | It is no longer a runtime dependency — depend on it explicitly if your own code imported it. See #297 |
| import `BaseDevice` from `simnos.plugins.nos.platforms_py._templates.base_template` | Update the import to `from simnos.plugins.nos.base_device import BaseDevice` — the class moved and the `_templates/` subpackage is gone. See #350 |

On-the-wire behaviour for scrapers (netmiko / scrapli / ansible) is unchanged
and pinned by the byte-parity golden — no client-side changes are needed for
automated tooling that only sends commands and reads output.

**Breaking Changes**

- Move the `BaseDevice` base class to `simnos/plugins/nos/base_device.py` (#350). It previously lived in `simnos/plugins/nos/platforms_py/_templates/base_template.py`, labelled an authoring template while actually being the mandatory runtime base every device module (and core) imports; the old import path and the now-empty `_templates/` subpackage are removed. External py handler modules must update the single import line — the class itself is unchanged
- Rename the inventory key `platform` to `device_type` (v3, #266). There is no compatibility alias: a v2 inventory using `platform:` is rejected at load. Migrate by rewriting the key (`sed -i 's/^\([[:space:]]*\)platform:/\1device_type:/' inventory.yaml`) or pin to v2 (`pip install "simnos<3"`, maintained as a migration window). A `device_type` accepts a platform's internal name, its `netmiko_device_type`, or its `ntc_platform` alias — all resolve to the same platform via the data-driven reverse index (#266)
- Replace the SSH and Telnet server transports with asynchronous backends on a shared asyncio event loop: SSH now runs on `asyncssh` (was paramiko) and Telnet on `telnetlib3`, both driven by a single push-dispatch session loop (#297). The `ParamikoSshServer` plugin and its inventory configuration are removed — use `AsyncSshServer` (the default SSH plugin); existing `ssh_key_file` / `ssh_banner` / `authorized_keys` options carry over. The bundled DH-GEX moduli file and the paramiko GEX workaround are gone (asyncssh negotiates moduli itself), and `paramiko` is no longer a runtime dependency (retained as a dev dependency for the byte-parity / interop test clients)
- Restructure the CLI around subcommands: `simnos up` starts server(s) and `simnos list-platforms` lists supported platforms (#267). The v2 flat form (`simnos -i inventory.yaml`, or a bare `simnos` for the default inventory) no longer parses — a subcommand is now required (`simnos up -i inventory.yaml`, or `simnos up` for the default inventory). `up` also gains an ad-hoc single-host mode (`-d/--device-type` with optional `-p/--port`, `-n/--host-name`, `-u/--username`, `-w/--password`) so a one-off platform launches without an inventory file. The `-l/--log-level` and `-r/--reload-commands` flags carry over as shared flags on every subcommand
- Default listen ports are now OS-assigned (ephemeral) instead of the fixed `6000` / `6001` / `6002` (#271). A no-argument `SimNOS()` (the builtin default inventory) and any inventory host with `port: 0` bind a port chosen atomically by the OS at `bind()` time; read the real port back from `host.port` after `start()` (the CLI logs `host <name> listening on <addr>:<port>`). This removes the cross-worker port-collision flake seen on macOS CI (`OSError: Errno 48`). Callers and tests that hardcoded `6000` must read `net.hosts[<name>].port` instead. The replicas list path still requires explicit `ge=1` ports — ephemeral is single-host only
- Remove the `ruler` and `completekey` shell-configuration knobs together with the `cmd.Cmd` base class they belonged to (#303). An inventory `configuration` block that still sets them is now rejected at load (`extra="forbid"`) — drop the keys. On-the-wire behaviour for scrapers (netmiko / scrapli / ansible) is unchanged and pinned by the byte-parity golden
- Shrink the command-handler return contract to `str | None` (#317). The dict-return form (`CommandResult` with `output` / `new_mode` / `exit`) is removed: a custom py-plugin handler that still returns a dict is answered on the wire with the fixed `% Internal error` line plus a server ERROR log, and its transition does not fire. Author mode transitions and session close statically instead — `new_mode` / `exit` / `transitions` on the A3 command. The bundled cisco_ios / arista_eos / huawei_smartax platforms moved their command authoring from the py `commands` dict into their A3 platform dirs in the same change (py modules now carry only the device class and dynamic output handlers); as a side effect, a per-host `overlay` entry now inherits the command's actually-served mode set (e.g. overlaying cisco_ios `show version` requires enable mode, matching the real wire)
- Rework the inventory command schema (`nos: configuration: commands:`) to the A3 dialect (#317). Entries now speak mode *names* and static transitions — `mode:` (list, omit for all modes), `new_mode:` / `exit:` / mode-conditional `transitions:`, `help:`, and an inline `output:` (verbatim literal) or `output_template:` (jinja2 source rendered with `{{ base_prompt }}`). The legacy prompt-string fields are rejected at load: `prompt:` / `new_prompt:` (use mode names), `alias:` (removed — a cross-inflow alias has no defined resolution semantics), and `output_variants:`. Note two render changes for migrated bodies: `output:` is now raw literal text (the v2 `str.format` brace-escape collapse of `{{`/`}}` is gone), and a body that referenced `{base_prompt}` must move to `output_template:` with the jinja2 spelling. Mode names are validated against the platform's modes at startup, so a typo fails at `start()`, not mid-session. A py module that still defines a `commands` dict is also rejected at load (that authoring channel moved to the A3 dir in #317 P-2, and a dict that loads but silently never merges would hide the mistake)
- Remove the legacy py-dict authoring base outright (#317). An A3 platform dir is now the only command authoring form: `Nos(commands=…, initial_prompt=…)`, `Nos.from_dict` / `dict_args`, and the dict form of `SimNOS(plugins=[…])` are gone (a str plugin must be an A3 platform dir path), and a `platforms_py/<name>.py` module with no co-named `platforms/<name>/` dir is warned about and not registered (py-only platforms cannot serve commands). A py module's legacy constants (`NAME`, `INITIAL_PROMPT`, `ENABLE_PROMPT`, `CONFIG_PROMPT`, `AUTH`) are no longer read — the platform name is the A3 dir basename and the prompts/auth live in `platform.yaml`. The py module remains the dynamic-behavior channel: the device class plus the functions the A3 `handler:` field binds to

**Enhancements**

- Introduce `sys_config.yaml`, a minimal environment-config file (`data_dir`, `variants_policy`) distinct from the topology inventory. Discovered via the `sys_config=` argument, the `SIMNOS_SYS_CONFIG` env var, `./sys_config.yaml`, or `~/.simnos/sys_config.yaml`; `SIMNOS_DATA_DIR` overrides `data_dir`. Establishes the setting precedence `CLI > env > inventory(host > default) > sys_config > builtin`. Both fields are reserved (no-op, warned at load) and wired up in #265 / #267 (#266)
- Reserve the inventory fields `facts`, `overlay`, and `variants_policy` as the schema vessel for #265. They are validated but consumed by nobody yet; a set-but-inert value is surfaced with a `log.warning` rather than silently ignored (#266)
- Migrate the plugin platform layout to the A3 directory format: a per-platform `platform.yaml` (modes + prompts) plus one file per command under `commands/*.yaml` with adjacent `.txt` / `.j2` output, replacing the monolithic per-platform YAML (#264). The `command` field is the single source of truth, and a build-time lint (`invoke lint-platform-data`) enforces the encoding / reference / extension conventions. Optional dynamic behaviour still lives in `platforms_py/<nos>.py`
- Add data-driven facts rendering and per-command output variants (#287). A command's output can be authored as a `.j2` template with an adjacent sidecar `.json` of facts (validated loudly at build time), and a command may declare multiple `variants` selected by `variants_policy` (`int` / `random` with an optional seed), sharing a canonical output and written via a two-phase atomic swap
- Add an interactive line editor to the SSH session: `?` context help (current-mode command list), Tab completion over the command tree, `↑` / `↓` history, `←` / `→` cursor movement and backspace, layered as a lightweight readline over the push-dispatch loop (#303). Editing sequences are emitted only on interactive keypress, so full-line input from scrapers is untouched and stays byte-parity-identical
- Add real-device-style command abbreviation: a unique per-token prefix resolves to the full command, with `% Ambiguous command` on a tie and an incomplete-command message on a partial match (#305). Abbreviation is shared by the dispatch core (default-on) and by Tab completion
- Add terminal paging (`--More--`) for long command output (#307). The page height follows the PTY / Telnet NAWS rows (falling back to `sys_config.paging.default_rows`, default 24); a `terminal length 0`-class command disables paging for the session (the `disables_paging` data flag), and non-interactive clients (netmiko at `height=1000`, scrapers) bypass the pager through a line-count gate that preserves byte parity. The `--More--` string is platform data (`platform.yaml` `paging.more_prompt`, Cisco default `" --More-- "`)
- Scope the command hot-reload watcher (`SIMNOS_RELOAD_COMMANDS`) to per-shell snapshots and per-platform watches, serialising a shared reload under the host lock so it no longer races concurrent sessions (#281)

## v2.3.1

**Bug Fixes**

- Bundle a DH Group Exchange (DH-GEX) moduli file (`simnos/plugins/servers/moduli`, 2048 + 3072-bit primes concatenated) and load it as fallback when no system moduli is available. Restores `gex-sha256` advertisement on Windows / macOS so that SHA-1-leaning legacy SSH clients such as `netmiko.fortinet.FortinetSSH` can complete KEX again — resolves the `pytest-full-matrix` Win/macOS deterministic failures listed as Known Issues in v2.3.0. Linux behaviour is unchanged (system `/etc/ssh/moduli` continues to take precedence). Adds `_moduli_lock` for thread-safe one-shot load caching mirroring the existing `_default_key_lock` pattern, plus `log.error` alarms for the bundled-missing and bundled-corrupted regression paths. 4096-bit primes are deferred for a future chore PR due to ssh-keygen `-M screen` runtime in VM hosts (#189)

**Tooling**

- Add `docs/development/regenerate_moduli.md` (+ `.ja.md` i18n) documenting the rotation policy (every 3 years, ad-hoc on logjam-class events) and the `ssh-keygen` regeneration procedure (#189)
- Add a release-time `unzip -l dist/*.whl | grep moduli` and `tar tzf dist/*.tar.gz | grep moduli` assertion to `pypi-publish.yml` so a packaging regression that drops the bundled moduli is caught before publish (#189)

## v2.3.0

**Breaking Changes**

- `hp_comware` platform was rewritten to follow real HP Comware CLI convention (`<HOST>` user view / `[HOST]` system view) instead of the previous Cisco-style prompts (`>`/`#`/`(config)#`). The `enable` and `ex` commands were removed (HP does not have them), and `system-view` / `return` / `quit` were added. netmiko / scrapli / ansible interop with hp_comware now works out of the box. Direct-CLI users that scripted against the previous `enable` command must update their scripts to use `system-view` (#173, closes #136)

**Features**

- Add netmiko / scrapli / ansible compatibility CI workflow (`workflow_dispatch`) for `cisco_ios`. New `tests/compatibility/` test suite gated by the `compatibility` pytest marker and `compatibility` optional dependency group (`scrapli`, `ansible-core`). Each library runs as an independent CI job. Adds `terminal width 512` / `configure terminal` / `end` / `exit` to `cisco_ios.yaml` for full netmiko + scrapli compatibility (#177, closes #125 Phase 1+2+3)
- Add NTC Templates v9.1 commands to 10 platforms — `mikrotik_routeros` (25), `linux` (15), `alcatel_aos` (12), `alcatel_sros` (7), `ciena_saos` (5), `aruba_os` (4), `extreme_exos` (2), `hp_procurve` (2), `paloalto_panos` (2), `aruba_aoscx` (1): 75 commands total (#174)
- Add NTC Templates v9.1 commands to `hp_comware` — `display bgp peer ipv4` / `display link-aggregation member-port`: 2 commands. Closes the `#128` NTC v9.1 epic (#175)

**Bug Fixes**

- `cmd_shell.default` no longer crashes the shell session when a yaml `output` contains an unrecognized `str.format` placeholder. Catches `KeyError`, `ValueError`, and `IndexError`, logs the error, and returns the raw output. Runtime is intentionally lenient; the build-time docs generator (`tasks.render_template`) still raises `RuntimeError` for the same situation (#170, closes #162)

**Tooling**

- `invoke gen-docs-platform-commands` now sweeps orphaned `docs/platforms/*.md` files when their backing yaml is deleted. Includes `_PRESERVED_PLATFORM_DOCS` for `index.md` / `index.ja.md` (#169, closes #159)

**Tests**

- Add `pytest-rerunfailures` and mark `test_send_command_returns_defined_output` as `@pytest.mark.flaky(reruns=2, reruns_delay=1)` to stabilize netmiko auto-enable race intermittently observed on slow CI runners (e.g. `broadcom_icos`) (#176)

**Dependencies**

- Bump `paramiko` constraint from `>=4.0,<5.0` to `>=4.0,<6.0` (paramiko 5.0 released). The existing `_DISABLED_GEX_ALGORITHMS` workaround remains required (upstream stale-snapshot bug still unfixed in 5.0) (#168)
- Bump `urllib3` from 2.6.3 to 2.7.0 (#167)

## v2.2.1

**Features**

- Add NTC Templates v9.1 commands to Cisco family — cisco_nxos / cisco_xr / cisco_asa: 19 commands total. Includes manual `cisco_asa` netmiko init compat (`show curpriv` / `terminal pager 0` etc.) (#151)
- Add NTC Templates v9.1 commands to non-Cisco batch — fortinet / juniper_junos / paloalto_panos / arista_eos: 30 commands total (#154)
- Add NTC Templates v9.1 commands to Huawei family — huawei_smartax / huawei_vrp: 39 commands total (#160)
- Add `show privilege` to cisco_ios for Ansible compatibility, mark cisco_ios as Ansible-verified in compatibility table (#124)

**Bug Fixes**

- Rewrite `gen_docs_platform_commands` invoke task: handle commands without `output` field, use `str.format()` for `{base_prompt}` substitution to match runtime semantics, regenerate all 50 platform docs with correct rendering (#146)
- Render escaped brace literals (`{{ ... }}`) correctly in platform docs by switching docs generator to `str.format()`, matching `cmd_shell.default` runtime. Affects 10 platforms with literal braces in fixtures (huawei_smartax, juniper_junos, cisco_asa, cisco_ios, cisco_nxos, hp_comware, arista_eos, paloalto_panos, oneaccess_oneos, huawei_vrp) (#160)

**Tooling**

- Improve `sync_ntc_commands.py`: prefer canonical raw fixture, retain alternate fixtures as `output_variants`, filter sibling-fixture noise (#147)
- Auto-escape literal `{xxx}` patterns in `sync_ntc_commands.py` output (preventive escape) so that runtime `str.format()` is safe for any NTC fixture content (#156)

**Tests**

- Add `tests/test_gen_docs_platform_commands.py` pinning `render_template` formatter semantics (substitution, escape unescape, error context) to prevent future regression of brace rendering (#160)

**CI/CD**

- Enable `pytest-xdist` parallel execution by default (`addopts = "-vv -n auto"`). Local measurement: 18:06 → 3:01 (6.0x speedup) (#164)
- Remove Docker-first tasks (`build` / `clean` / `rebuild` / `pytest` / `cli` / `tests`) and dead code from `tasks.py`, drop `INVOKE_LOCAL` from CI workflows (#145)

## v2.2.0

**Features**

- Add 9 new platforms from NTC Templates v9.0: aruba_aoscx, cisco_apic, cisco_viptela, cisco_wlc_ssh, edgecore, extreme_slxos, oneaccess_oneos, watchguard_firebox, zte_zxros (#129)
- Add 28 new commands to cisco_ios from NTC Templates v9.1, including SD-WAN, CTS, endpoint-tracker, and license commands (#128)

**Tests**

- Add netmiko connection tests for all YAML-only platforms (#129)
- Refine test skip logic with granular `skip_enable_platforms` instead of full-platform xfail (#129)

**Documentation**

- Add `CONTRIBUTING.md` with bilingual support (English / Japanese), AI Transparency policy, and contribution workflow (#121)
- Add `SECURITY.md` with bilingual support pointing to GitHub Private Vulnerability Reporting (#120)
- Convert platform compatibility list to detailed compatibility table with notes (#129)

**CI/CD**

- Add yamllint to CI for YAML platform validation across 50+ YAML files (#137)

**Dependencies**

- Bump ntc-templates 9.0.0 → 9.1.0 (transitive via netmiko)
- Bump cryptography 46.0.5 → 46.0.7
- Bump pytest 9.0.2 → 9.0.3
- Bump trivy-action 0.35.0 → 0.36.0
- Bump GitHub Actions Pages workflows to Node.js 24 compatible versions

## v2.1.3

**Security**

- Fix trivy-action supply chain compromise: update 0.34.1 → v0.35.0 (#117)

**CI/CD**

- Update GitHub Actions to Node.js 24 compatible versions (#112, #118)
- Add Dependabot configuration for automated weekly updates (#116)

## v2.1.2

**Performance**

- Remove per-byte `time.sleep(0.01)` in SSH/Telnet tap functions — test suite ~20% faster (#107)
- Replace `accept()` polling with `selectors` + `socketpair` for instant server shutdown (#106)

**Security**

- Upgrade dependencies to fix 7 Dependabot alerts: urllib3, filelock, virtualenv, pynacl (#111)

## v2.1.1

**Bug Fixes**

- Resolve Docker Trivy scan failure (zlib CVE) with `apk upgrade --no-cache` (#102)
- Increase macOS test timeout to 600s for cisco_ios (#102)
- Fix BrokenPipeError on Telnet authentication failure (#102)

**CI/CD**

- Change publish workflow triggers from tag push to release event to prevent premature publishing (#103)

## v2.1.0

**Features**

- Echo coalescing for SSH and Telnet servers — prevents intermittent empty output with netmiko `send_command()` (#87, #94)
- Telnet server plugin with RFC 854/857/858 compliance
- Thread-safe TapIO I/O bridge shared by SSH and Telnet servers

**Bug Fixes**

- Replace thread-unsafe ChannelFile with direct Channel API (#85)
- Add CRLF handling to SSH channel_to_shell_tap (#88)
