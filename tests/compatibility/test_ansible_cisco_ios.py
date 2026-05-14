"""Compatibility check: ansible × cisco_ios.

Uses ansible-playbook via subprocess against simnos. Requires
`cisco.ios` + `ansible.netcommon` collections (installed in the
compatibility CI job before running these tests).
"""

import os
from pathlib import Path
import shutil
import subprocess
import textwrap

import pytest


def _write_inventory(path: Path, creds: dict) -> None:
    path.write_text(
        textwrap.dedent(f"""\
        all:
          hosts:
            test_device:
              ansible_host: {creds["host"]}
              ansible_port: {creds["port"]}
              ansible_user: {creds["username"]}
              ansible_password: {creds["password"]}
              ansible_connection: ansible.netcommon.network_cli
              ansible_network_os: cisco.ios.ios
              ansible_become: true
              ansible_become_method: enable
    """)
    )


def _run_playbook(inventory: Path, playbook: Path) -> subprocess.CompletedProcess:
    env = {**os.environ, "ANSIBLE_HOST_KEY_CHECKING": "False"}
    return subprocess.run(
        ["ansible-playbook", "-i", str(inventory), str(playbook)],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
        env=env,
    )


@pytest.mark.compatibility
def test_ansible_ios_facts(cisco_ios_simnos, tmp_path):
    if shutil.which("ansible-playbook") is None:
        pytest.skip("ansible-playbook not on PATH")

    creds = cisco_ios_simnos
    inventory = tmp_path / "inventory.yml"
    _write_inventory(inventory, creds)
    playbook = tmp_path / "play.yml"
    playbook.write_text(
        textwrap.dedent("""\
        - hosts: test_device
          gather_facts: false
          tasks:
            - name: collect ios facts
              cisco.ios.ios_facts:
                gather_subset: min
    """)
    )

    result = _run_playbook(inventory, playbook)
    assert result.returncode == 0, f"ansible-playbook failed: stdout=\n{result.stdout}\nstderr=\n{result.stderr}"
    assert "failed=0" in result.stdout


@pytest.mark.compatibility
def test_ansible_cli_command(cisco_ios_simnos, tmp_path):
    if shutil.which("ansible-playbook") is None:
        pytest.skip("ansible-playbook not on PATH")

    creds = cisco_ios_simnos
    inventory = tmp_path / "inventory.yml"
    _write_inventory(inventory, creds)
    playbook = tmp_path / "play.yml"
    playbook.write_text(
        textwrap.dedent("""\
        - hosts: test_device
          gather_facts: false
          tasks:
            - name: show version via cli_command
              ansible.netcommon.cli_command:
                command: show version
              register: result
            - name: assert output contains Cisco IOS
              ansible.builtin.assert:
                that: "'Cisco IOS' in result.stdout"
    """)
    )

    result = _run_playbook(inventory, playbook)
    assert result.returncode == 0, f"ansible-playbook failed: stdout=\n{result.stdout}\nstderr=\n{result.stderr}"
