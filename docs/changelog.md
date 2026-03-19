# Changelog

All notable changes to SIMNOS are documented here.
For full details, see the [GitHub Releases](https://github.com/Route-Reflector/simnos/releases).

## Unreleased

**CI/CD**

- Update GitHub Actions to Node.js 24 compatible versions (#112)

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
