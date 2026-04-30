# Changelog

All notable changes to SIMNOS are documented here.
For full details, see the [GitHub Releases](https://github.com/Route-Reflector/simnos/releases).

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
