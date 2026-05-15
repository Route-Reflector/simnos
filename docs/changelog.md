# Changelog

All notable changes to SIMNOS are documented here.
For full details, see the [GitHub Releases](https://github.com/Route-Reflector/simnos/releases).

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
