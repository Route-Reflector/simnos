"""Invoke tasks for simnos.

Provides lint / static-analysis wrappers (`ruff`, `yamllint`, `bandit`),
local docs serving (`docs`), platform docs generation
(`gen_docs_platform_commands`), and a Netmiko login debug helper
(`netmiko_check`).
"""

from collections.abc import Iterable
import os
import time

from invoke import task
import yaml


def run_cmd(context, exec_cmd):
    """Run an invoke task command locally with a pty."""
    print(f"Running command: {exec_cmd}")
    return context.run(exec_cmd, pty=True)


@task
def ruff(context):
    """Run ruff to check that Python files adherence to ruff standards."""
    run_cmd(context, "ruff check --diff")
    run_cmd(context, "ruff format --diff")


@task
def yamllint(context):
    """Run yamllint to check YAML files."""
    run_cmd(context, "yamllint .")


@task
def bandit(context):
    """Run bandit to validate basic static code security analysis."""
    run_cmd(context, "bandit -c pyproject.toml --recursive ./")


@task
def ty(context, exit_zero=False):
    """Run ty type-checker (blocking since Phase 2, see #218).

    Phase 2 brought production code to 0 diagnostics; tests/ is excluded
    via pyproject.toml ``[tool.ty.src]``. CI now treats ty as blocking
    (exit_zero=False default + no continue-on-error). New type errors in
    production code break the build.

    Args:
        exit_zero: When True, pass ``--exit-zero`` so ty never exits
            non-zero. Default is False (blocking) for CI. Set True only
            for developer workflow chains where a transient typing error
            should not abort the rest of the invoke pipeline.
    """
    flag = "--exit-zero " if exit_zero else ""
    run_cmd(context, f"uv run ty check . {flag}".rstrip())


@task
def docs(context):
    """Build and serve docs locally for development."""
    run_cmd(context, "mkdocs serve --dev-addr 0.0.0.0:8001")


WARNING_MESSAGE = """
!!! warning
    This is automatically generated. In case of any issues,
    please refer to the source code or, even better,
    open an issue on the GitHub repository. Thanks! 🤗📖
"""


def render_template(template: str, platform: str, command: str, field: str) -> str:
    """Render a YAML string template the same way the runtime shell does.

    Uses `str.format(base_prompt=platform)` to match `cmd_shell.default`:
    substitutes `{base_prompt}` and unescapes `{{` / `}}` literals from
    `sync_ntc_commands.escape_format_braces` preventive escape.

    Re-raises any formatting failure (the `FORMAT_ERRORS` catch set shared
    with the lenient runtime `cmd_shell._safe_format`; the asymmetry is
    "raise vs silent" only) as `RuntimeError` carrying the platform /
    command / field context, so CI failures pinpoint the offending YAML
    entry instead of dumping a contextless stack trace.
    """
    # Lazy import: keep `invoke --list` / lint-only tasks fast (the existing
    # tasks.py convention, see netmiko_check); cached after the first call.
    from simnos.plugins.shell.cmd_shell import FORMAT_ERRORS

    try:
        return template.format(base_prompt=platform)
    except FORMAT_ERRORS as exc:
        raise RuntimeError(
            f"Failed to format {field} for {platform}/{command!r}: {exc!r}. "
            f"Check that any literal '{{' / '}}' in YAML is escaped as '{{{{' / '}}}}'."
        ) from exc


_PRESERVED_PLATFORM_DOCS: frozenset[str] = frozenset({"index.md", "index.ja.md"})


def sweep_orphaned_platform_docs(
    docs_folder: str,
    valid_platforms: Iterable[str],
    preserve: frozenset[str] = _PRESERVED_PLATFORM_DOCS,
) -> list[str]:
    """Remove ``docs/platforms/*.md`` entries whose backing yaml is gone.

    Keeps the docs idempotent with the yaml directory as the source of
    truth: if a platform's yaml is deleted, the corresponding markdown
    is also removed on the next regeneration. ``preserve`` lists hand-
    authored markdown that has no yaml counterpart (index pages etc.)
    and must never be swept.

    Returns the sorted list of removed filenames for caller-side logging.
    """
    expected: set[str] = {f"{platform}.md" for platform in valid_platforms}
    removed: list[str] = []
    for entry in sorted(os.listdir(docs_folder)):
        if not entry.endswith(".md"):
            continue
        if entry in expected or entry in preserve:
            continue
        os.remove(f"{docs_folder}/{entry}")
        removed.append(entry)
    return removed


@task
def gen_docs_platform_commands(ctx):
    """
    Generate platform specific commands in the docs.
    """
    platforms_folder: str = "simnos/plugins/nos/platforms_yaml"
    docs_folder: str = "docs/platforms"
    files: list[str] = os.listdir(platforms_folder)
    platforms: list[str] = [platform.split(".yaml")[0] for platform in files]

    for platform in platforms:
        print(f"Generating Platform: {platform}")
        with open(f"{platforms_folder}/{platform}.yaml", encoding="utf-8") as file:
            data = yaml.safe_load(file)
        with open(f"{docs_folder}/{platform}.md", "w", encoding="utf-8") as platforms_file:
            platforms_file.write(f"# {platform}\n\n")
            platforms_file.write(WARNING_MESSAGE)
            platforms_file.write("## Commands\n\n")
            for command, details in data["commands"].items():
                platforms_file.write(f"### {command}\n\n")
                output = details.get("output")
                if not output:
                    platforms_file.write("**Output:** None\n\n")
                else:
                    rendered = render_template(output, platform, command, "output")
                    platforms_file.write(f"**Output:**\n```\n{rendered}\n```\n\n")
                platforms_file.write(f"**Help:** {details.get('help', '')}\n\n")
                platforms_file.write("**Prompt:**\n")
                prompts = details.get("prompt", [])
                if not isinstance(prompts, list):
                    prompts = [prompts]
                for prompt in prompts:
                    rendered = render_template(prompt, platform, command, "prompt")
                    platforms_file.write(f"- {rendered}\n")
                platforms_file.write("\n")

    for orphan in sweep_orphaned_platform_docs(docs_folder, platforms):
        print(f"Removed orphaned doc: {orphan}")


@task(help={"device_type": "The device type to connect to."})
def netmiko_check(ctx, device_type: str):
    """
    This is a task for debugging possible problems with Netmiko logins.
    """
    # Lazy import: keep `invoke --list` and lint-only tasks fast by avoiding
    # the heavy netmiko / simnos import cost unless this task is actually run.
    from netmiko import ConnectHandler

    from simnos import SimNOS

    init_time = time.time()
    inventory = {
        "hosts": {
            "host1": {
                "username": "user",
                "password": "user",
                "platform": device_type,
                "port": 6000,
            }
        }
    }

    credentials = {
        "host": "localhost",
        "username": "user",
        "password": "user",
        "port": 6000,
        "device_type": device_type,
    }

    net = SimNOS(inventory=inventory)
    net.start()

    with ConnectHandler(**credentials):
        time.sleep(1)

    net.stop()

    print("Everything is OK! ✅")
    print(f"Time spent: {time.time() - init_time:.2f}s")
