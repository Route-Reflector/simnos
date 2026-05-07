"""Invoke tasks for simnos.

Provides lint / static-analysis wrappers (`ruff`, `yamllint`, `bandit`),
local docs serving (`docs`), platform docs generation
(`gen_docs_platform_commands`), and a Netmiko login debug helper
(`netmiko_check`).
"""

import os
import time

from invoke import task
from netmiko import ConnectHandler
import yaml

from simnos import SimNOS


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
def docs(context):
    """Build and serve docs locally for development."""
    run_cmd(context, "mkdocs serve --dev-addr 0.0.0.0:8001")


WARNING_MESSAGE = """
!!! warning
    This is automatically generated. In case of any issues,
    please refer to the source code or, even better,
    open an issue on the GitHub repository. Thanks! 🤗📖
"""


@task
def gen_docs_platform_commands(ctx):
    """
    Generate platform specific commands in the docs.
    """
    platforms_folder: str = "simnos/plugins/nos/platforms_yaml"
    files: list[str] = os.listdir(platforms_folder)
    platforms: list[str] = [platform.split(".yaml")[0] for platform in files]

    for platform in platforms:
        print(f"Generating Platform: {platform}")
        with open(f"{platforms_folder}/{platform}.yaml", encoding="utf-8") as file:
            data = yaml.safe_load(file)
        with open(f"docs/platforms/{platform}.md", "w", encoding="utf-8") as platforms_file:
            platforms_file.write(f"# {platform}\n\n")
            platforms_file.write(WARNING_MESSAGE)
            platforms_file.write("## Commands\n\n")
            for command, details in data["commands"].items():
                platforms_file.write(f"### {command}\n\n")
                output = details.get("output")
                if not output:
                    platforms_file.write("**Output:** None\n\n")
                else:
                    platforms_file.write(f"**Output:**\n```\n{output.replace('{base_prompt}', platform)}\n```\n\n")
                platforms_file.write(f"**Help:** {details.get('help', '')}\n\n")
                platforms_file.write("**Prompt:**\n")
                prompts = details.get("prompt", [])
                if not isinstance(prompts, list):
                    prompts = [prompts]
                for prompt in prompts:
                    platforms_file.write(f"- {prompt.replace('{base_prompt}', platform)}\n")
                platforms_file.write("\n")


@task(help={"device_type": "The device type to connect to."})
def netmiko_check(ctx, device_type: str):
    """
    This is a task for debugging possible problems with Netmiko logins.
    """
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
