# Conventions
This sections is intended to briefly explain all the tools used inside the project. Those tools are mainly there to ensure that the code is correctly written and tested.

## General: uv
[uv](https://docs.astral.sh/uv/) is a fast Python package and project manager. It handles dependency resolution, virtual environment creation, package building, and publishing. All the configurations for the project can be found in the `pyproject.toml`.

Here are some basic commands:

- `uv sync`: use it to install all the dependencies and create the virtual environment.
- `uv lock --upgrade`: use it to update the dependencies.
- `source .venv/bin/activate`: activate the virtual environment, or use `uv run <command>` to run a command within the environment without activating it.

## Tests: Pytest
Pytest is a testing framework for Python that makes it easy to write simple and scalable tests. It allows you to write test cases as regular Python functions, using assertions to verify expected outcomes. Pytest provides powerful features such as fixtures for setting up test environments, parameterized testing, and plugins for extending functionality. It's widely used in the Python community due to its simplicity, flexibility, and extensive ecosystem of plugins.

To run the tests do the following:
```bash
pytest
```

## Security check: Bandit
Bandit is a security tool for Python code that detects common security issues and vulnerabilities. It analyzes Python code statically to identify potential security threats such as insecure use of modules, unsafe function calls, and potential security risks. Bandit provides a set of plugins that check for various security issues and can be easily integrated into development workflows, helping developers identify and fix security issues early in the development process. It's a valuable tool for improving the security posture of Python applications and libraries.

To run the bandit tool do the following:
```bash
bandit -c pyproject.toml -r .
```

## Linting and formatting: Ruff
[Ruff](https://docs.astral.sh/ruff/) is a fast Python linter and formatter that replaces Black, Flake8, and Pylint. It enforces code style, catches errors, and formats code automatically. Configuration is in `pyproject.toml` under `[tool.ruff]`.

To run ruff do the following:
```bash
ruff check .    # lint
ruff format .   # format
```

## Code coverage: coverage
Coverage is a tool used in software development to measure the extent to which the source code of a program is executed during testing. It helps developers understand how thoroughly their tests exercise the codebase by providing metrics on code coverage, typically expressed as a percentage. Coverage tools track which lines or branches of code are executed during tests and generate reports highlighting areas that are covered and those that are not. This information enables developers to identify untested code paths and improve the effectiveness of their testing efforts.

To run coverage in conjunction with pytest do the following:
```bash
coverage run -m pytest
```

It will generate a report which can look in `coverage report -m` or `coverage html`.
