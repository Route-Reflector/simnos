[English](README.md) | [日本語](README.ja.md)

[![Downloads][pepy-downloads-badge]][pepy-downloads-link]
[![PyPI][pypi-latest-release-badge]][pypi-latest-release-link]
[![PyPI versions][pypi-pyversion-badge]][pypi-pyversion-link]
[![GitHub Discussion][github-discussions-badge]][github-discussions-link]
[![Ruff][ruff-badge]][ruff-link]
[![Tests][github-tests-badge]][github-tests-link]

# Simulated Network Operating Systems - SIMNOS

> "Reality is merely an illusion, albeit a very persistent one."
>
> ~ Albert Einstein

SIMNOS simulates Network Operating Systems interactions. You can simulate
network devices like Cisco IOS or Huawei SmartAX interactions over
SSH with little effort. This project is mainly intended for testing
and development purposes.

[Documentation](https://route-reflector.github.io/simnos/) | [Examples](https://route-reflector.github.io/simnos/examples/) | [Platforms](https://route-reflector.github.io/simnos/platforms/)

## Origin

SIMNOS is an independent project derived from [FakeNOS](https://github.com/fakenos/fakenos), created by Denis Mulyalin and maintained by Enric Perpinyà Pitarch. After significant divergence in tooling, platforms, and architecture, it was rebranded as SIMNOS to avoid confusion with the upstream project.

**AI Transparency:** AI-assisted development (Claude Code, Codex, Gemini, etc.) is actively used in this project. All AI-generated changes are reviewed by a human maintainer before merging.

**Key differences from FakeNOS:**

- Package name: `simnos` (on PyPI)
- Package manager: uv (migrated from Poetry)
- Linter/Formatter: Ruff (migrated from Black/Pylint)
- Python support: 3.13 / 3.14
- CI: Modernized GitHub Actions workflow
- NOS platforms: 5 additional platforms enabled (brocade_fastiron, ciena_saos, fortinet, juniper_screenos, ruckus_fastiron)
- Paramiko: upgraded to 4.0 with DH Group Exchange server-mode workaround

## Why?

Crucial aspect of writing applications or scripts for Network Automation is
testing, often testing done using physical or virtual instances of network
appliances running certain version of Network Operating System (NOS). That
approach, while gives best integration results, in many cases carries a lot
of overhead to setup, run and tear down as well as putting significant burden
on compute and storage resource utilization.

Other approach is to mock underlying libraries methods to fool applications
under testing into believing that it is getting output from real devices. That
approach works very well for unit testing, but fails to simulate such aspects
as connection establishment and handling.

SIMNOS positions itself somewhere in the middle between full integration testing
and testing that mocks device interactions. SIMNOS allows to create NOS plugins
to produce pre-defined output to test applications behavior while running servers
to establish connections with.

## What?

SIMNOS can:

- Run thousands of servers to stress test applications
- Simulate Network Operating Systems Command Line Interface (CLI) interactions
- Provide high-level API to create custom NOS plugins
- Run in docker container to simplify integration with your infrastructure
- Make use of SIMNOS CLI tool for quick run and prototype simulations
- Works on Windows, Mac and Linux under Python 3.13 and 3.14

## How?

Send input and get the output - this is how we interact with many
Network Operating Systems, SIMNOS allows to pre-define the output
to sent in response to certain input commands, making it ideal for
isolated feature testing.

SIMNOS is a micro-kernel framework that can be extended using plugins.
The core is kept small and optimized while most of the functionality
offloaded to plugins.

SIMNOS has these pluggable systems:

- Server Plugins - plugins responsible for running various servers to connect with
- Shell Plugins - plugins to simulate command line interface shell
- NOS plugins - plugins to simulate Network Operating System commands

## What not?

SIMNOS is a simulator, it does not emulate any of Network Control, Data
or Management planes, it merely takes the commands as input and responds
with predefined output.

## Acknowledgments

SIMNOS is built upon the work of [FakeNOS](https://github.com/fakenos/fakenos). We are grateful to the original creators and contributors:

- [Denis Mulyalin](https://github.com/dmulyalin) - Original Creator of FakeNOS
- [Enric Perpinyà Pitarch](https://github.com/evilmonkey19) - Main Collaborator and Maintainer of FakeNOS

### Inspired by and borrowed from

- [sshim](https://pythonhosted.org/sshim/) - library for testing and debugging SSH automation clients
- [PythonSSHServerTutorial](https://github.com/ramonmeza/PythonSSHServerTutorial) - tutorial on creating paramiko based SSH server
- [fake-switches](https://github.com/internap/fake-switches) - pluggable switch/router command-line simulator
- [ncs-netsim](https://developer.cisco.com/docs/nso/guides/#!the-network-simulator) - tool to simulate a network of devices
- [cisshgo](https://github.com/tbotnz/cisshgo) - concurrent SSH server to emulate network equipment for testing purposes
- [scrapli-replay](https://pypi.org/project/scrapli-replay/) - tools to enable easy testing of SSH programs and to create semi-interactive SSH servers

[github-discussions-link]:     https://github.com/Route-Reflector/simnos/discussions
[github-discussions-badge]:    https://img.shields.io/static/v1?label=Discussions&message=Ask&color=blue&logo=github
[ruff-badge]:                  https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json
[ruff-link]:                   https://github.com/astral-sh/ruff
[pypi-pyversion-link]:         https://pypi.python.org/pypi/simnos/
[pypi-pyversion-badge]:        https://img.shields.io/pypi/pyversions/simnos.svg?logo=python
[pepy-downloads-link]:         https://pepy.tech/project/simnos
[pepy-downloads-badge]:        https://pepy.tech/badge/simnos
[github-tests-badge]:          https://github.com/Route-Reflector/simnos/actions/workflows/main.yml/badge.svg
[github-tests-link]:           https://github.com/Route-Reflector/simnos/actions
[pypi-latest-release-link]:    https://pypi.python.org/pypi/simnos
[pypi-latest-release-badge]:   https://img.shields.io/pypi/v/simnos.svg?logo=data:image/svg+xml;base64,PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0iVVRGLTgiPz4KPHN2ZyBpZD0iTGF5ZXJfMiIgZGF0YS1uYW1lPSJMYXllciAyIiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA2NC41OSA2NC41OCI+CiAgPGRlZnM+CiAgICA8c3R5bGU+CiAgICAgIC5jbHMtMSB7CiAgICAgICAgZmlsbDogIzQwMmE1OTsKICAgICAgfQoKICAgICAgLmNscy0xLCAuY2xzLTIgewogICAgICAgIHN0cm9rZS13aWR0aDogMHB4OwogICAgICB9CgogICAgICAuY2xzLTIgewogICAgICAgIGZpbGw6ICNmZmY7CiAgICAgIH0KICAgIDwvc3R5bGU+CiAgPC9kZWZzPgogIDxnIGlkPSJMYXllcl8xLTIiIGRhdGEtbmFtZT0iTGF5ZXIgMSI+CiAgICA8Zz4KICAgICAgPHBhdGggY2xhc3M9ImNscy0xIiBkPSJNOS42NywwaDQ1LjVjNS4xNS44LDguNTUsMy44NCw5LjQyLDkuMDR2NDYuNjJjLS42OCw0Ljc0LTQuNTQsOC4xNy05LjIzLDguNjctNy40Ni43OS0zNS0uNjYtNDUuMzIsMC00LjQxLjAxLTkuMTUtMy4xMy05Ljc5LTcuNzRDLS4wOCw1NC4xOS0uMDksMTAuMzQuMjUsNy45My44NSwzLjY3LDUuNTMuMjUsOS42NywwWiIvPgogICAgICA8Zz4KICAgICAgICA8cGF0aCBjbGFzcz0iY2xzLTIiIGQ9Ik0xMC4yMyw1Ljc4YzIuMTgtLjMxLDQxLjgzLS4zLDQ0LjAxLDAsMi4xNi4zLDMuOTUsMS43Myw0LjU3LDMuODItLjQyLDcuNjIuNTUsNDIuMDEsMCw0NS4zMi0uMzEsMS44Ni0yLjEsMy4xOC0zLjgyLDMuNjQtOC40OC0uNTctNDAuNDIuODctNDQuOTQuMTktMS45My0uMjktMy44OC0yLjA2LTQuMi00LjAxLS4zNi0yLjIxLS4zNi00Mi41NSwwLTQ0Ljc2LjM0LTIuMDksMi4yOC0zLjksNC4zOC00LjJaIi8+CiAgICAgICAgPHBhdGggY2xhc3M9ImNscy0xIiBkPSJNNDkuNTgsMTkuMDJjMTIuOTksMTYuNzEtMy4yMywzOS44My0yMy41LDM0LjMxLTEuMjMtLjMzLTcuMS0zLjAzLTYuOTktNC4wMWwzLjgyLTQuMmMxMi40MSw4LjgzLDI4LjQ3LTMuMzksMjQuNzEtMTcuMjUtMS40My01LjI3LTQuNS0yLjYyLDEuOTYtOC44NloiLz4KICAgICAgICA8cGF0aCBjbGFzcz0iY2xzLTEiIGQ9Ik00MS40NywxOS41OGMtMTQuMzgtOS42Ni0zMS40OCw2LjczLTIyLjU2LDIxLjI2LS4wNSwxLjMtMi45NSwzLjM5LTMuODIsNC42NkMtLjM4LDI1LjIyLDI0Ljg3LjQyLDQ1LjM4LDE1LjAxYy4wNy4zMy0zLjM2LDQuMTgtMy45Miw0LjU3WiIvPgogICAgICAgIDxwYXRoIGNsYXNzPSJjbHMtMiIgZD0iTTQxLjQ3LDE5LjU4Yy0xLjUzLDEuMDctMy0uNjMtNC45NC0xLjEyLTYuNDItMS42MS0xMy4zNi44OS0xNi44OCw2LjYyLTEsMS42Mi0xLjUyLDMuNDgtMi4yNCw1LjIyLS4wOC4yLS40Mi0uMzEtLjU2LDAtLjcsMS41NS4xOSw1LjkzLjc1LDcuNjUuMzcsMS4xNCwxLjM1LDEuNjgsMS4zMSwyLjg5LTguOTItMTQuNTMsOC4xOS0zMC45MSwyMi41Ni0yMS4yNloiLz4KICAgICAgICA8Zz4KICAgICAgICAgIDxwYXRoIGNsYXNzPSJjbHMtMSIgZD0iTTM0LjQ3LDI0LjYyYzMuNTEtLjI0LDUuNzUsMyw0LjU3LDYuMjUtLjM3LDEuMDMtNi4wMSw3LjA4LTYuOTksNy43NC00LjM5LDIuOTMtOC4wMi0uNjQtNi44MS00Ljk0LjI3LS45Niw2LjU3LTguODYsOS4yMy05LjA0WiIvPgogICAgICAgICAgPHBhdGggY2xhc3M9ImNscy0xIiBkPSJNMzUuMjIsMjUuOTJjMS43Ni4wNywyLjkzLDIuMDEsMi43LDMuNjQtLjExLjgxLTguOTUsMTMuNTktMTEuNTYsNi41My0uNzUtMi40OSw2LjkzLTEwLjI0LDguODYtMTAuMTZaIi8+CiAgICAgICAgPC9nPgogICAgICA8L2c+CiAgICA8L2c+CiAgPC9nPgo8L3N2Zz4=
