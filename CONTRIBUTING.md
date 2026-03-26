[English](CONTRIBUTING.md) | [日本語](CONTRIBUTING.ja.md)

# Contributing to SIMNOS

Thank you for your interest in contributing to SIMNOS!

Before diving in, please take a moment to understand what this project is — and what it isn't.

## What SIMNOS Is (and Isn't)

SIMNOS is a **lightweight test stub** for network automation tools. It simulates NOS command-line interfaces just enough for testing and development — nothing more.

**SIMNOS is not** a full network emulator. Projects like CML2, ContainerLab, or GNS3 provide rich emulation of control planes, data planes, and protocols. SIMNOS does not aim to compete with them. If you need routing protocol behavior or packet forwarding, those tools are the right choice.

**Design principle:** What can be done statically in YAML stays in YAML. Python is only used for things that require dynamic behavior (e.g., `show clock` returning the current time, or config mode commands that change internal state).

## AI Transparency

AI-assisted development (Claude Code, Codex, Gemini, etc.) is actively used in this project. All AI-generated changes are reviewed by a human maintainer before merging.

**AI-assisted contributions are welcome.** If you use AI tools in your contribution, please:

- Disclose it — mention which AI tool(s) you used in your PR description
- Use the best available model with reasoning (extended thinking) enabled
- Review the AI output yourself before submitting — you are responsible for the code, not the AI

## How to Contribute

### Reporting Bugs

Open an [Issue](https://github.com/Route-Reflector/simnos/issues) with:

- What you expected to happen
- What actually happened
- Steps to reproduce
- Your environment (OS, Python version, simnos version)

### Suggesting Features

Open an Issue first to discuss. This project has a narrow scope, and not every feature fits. Discussing upfront saves everyone time.

### Submitting Changes

- **Small fixes** (typos, minor bugs): You can open an Issue and PR at the same time.
- **Larger changes** (new features, refactoring): Open an Issue first. Let's agree on the approach before you invest time writing code.
- **PRs without an Issue** may be difficult to review — without context, it's hard to judge whether a change is appropriate. Please explain *why*, not just *what*.

> Note: This project is maintained by a single developer in their spare time. Reviews may take a while. PRs may be rejected at the maintainer's discretion — don't take it personally.

## Adding New Platforms

New platform contributions are welcome! A few things to keep in mind:

- **Real device verification is your responsibility.** The maintainer often does not have access to the actual hardware. Please test your platform against real device output (or well-known reference data) before submitting.
- **If the platform isn't in [NTC Templates](https://github.com/networktocode/ntc-templates) yet**, consider contributing a parser there as well. It benefits the entire network automation ecosystem, and SIMNOS uses NTC test data as a source for command outputs.
- **Platform YAML structure**: Look at existing platforms in `simnos/plugins/nos/platforms_yaml/` for reference. Each platform needs at minimum:
  - `initial_prompt` — the default CLI prompt
  - `commands` — a mapping of command names to their output, help text, and prompt
- See the [Creating New Platforms](https://route-reflector.github.io/simnos/development/creating_new_platforms/) guide for details.

## Development Setup

### Prerequisites

- Python 3.13 or 3.14
- [uv](https://docs.astral.sh/uv/) (package manager)
- Docker (optional, for container-based testing)

### Getting Started

```bash
# Fork and clone the repository
git clone https://github.com/<your-username>/simnos.git
cd simnos

# Install dependencies and create virtual environment
uv sync

# Install pre-commit hooks
uv run pre-commit install
```

### Running Tests

```bash
# Run all checks (lint + security + tests) in Docker
uv run invoke tests

# Run locally without Docker
uv run invoke tests --local

# Or run individual checks
uv run invoke ruff --local      # Linting and formatting
uv run invoke bandit --local    # Security checks
uv run invoke pytest --local    # Unit tests
```

### Code Style

- **Linter/Formatter**: [Ruff](https://docs.astral.sh/ruff/) — configured in `pyproject.toml`
- **Security**: [Bandit](https://bandit.readthedocs.io/) — also configured in `pyproject.toml`
- **Pre-commit hooks** run automatically on commit (ruff + bandit)
- Line length: 120 characters
- Target Python: 3.13+

For details, see [Conventions](https://route-reflector.github.io/simnos/development/conventions/).

### Commit Messages

Follow this format:

```
type: description (#issue-number)
```

Types: `feat`, `fix`, `refactor`, `docs`, `chore`, `test`

Examples:
- `feat: add show privilege command for cisco_ios (#124)`
- `fix: handle offline NTC Templates clone (#123)`
- `docs: add CONTRIBUTING.md (#121)`

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
