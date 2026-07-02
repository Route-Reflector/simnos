"""
Test the Netmiko compatibility as this library can be used
as a testing tool for Netmiko.
"""

import random
import sys
import threading
from typing import cast

from netmiko import (
    ConnectHandler,
    NetMikoAuthenticationException,
    NetMikoTimeoutException,
)
import pytest

from simnos import SimNOS
from simnos.core.nos import available_platforms
from simnos.core.pydantic_models import EPHEMERAL_PORT
from tests.utils import generate_random_string, get_platforms_from_md, netmiko_device_type_of


class TestNetmiko:
    """
    Test the Netmiko compatibility as this library can be used
    as a testing tool for Netmiko.
    """

    @pytest.mark.timeout(30)
    @pytest.mark.parametrize("device_type", get_platforms_from_md())
    def test_custom_inventory_network(self, device_type: str):
        """
        This test tries to connect to device as Netmiko would
        do. It ensures that the current implemented devices are
        ready to used with Netmiko. We only look if any error
        has raised.
        """
        net = None
        try:
            inventory = {
                "hosts": {
                    "router": {
                        "username": "usertest",
                        "password": "passwordtest",
                        "port": EPHEMERAL_PORT,
                        "device_type": device_type,
                    }
                }
            }
            net = SimNOS(inventory=inventory)

            net.start()

            device_credentials = {
                "host": "localhost",
                "username": "usertest",
                "password": "passwordtest",
                "port": net.hosts["router"].port,  # real OS-assigned port (#271)
                "device_type": netmiko_device_type_of(device_type),
            }
            print(f"Testing device_type: {device_type}")
            with ConnectHandler(**device_credentials):
                pass
            print(f"Success device_type: {device_type}")
        finally:
            if net is not None:
                net.stop()
            all_threads = threading.enumerate()
            for thread in all_threads:
                if thread is not threading.main_thread() and "pytest_timeout" not in thread.name:
                    thread.join()

        n_threads: int = 2 if sys.platform == "win32" else 1
        assert threading.active_count() == n_threads

    @pytest.mark.timeout(20 * 10)
    def test_simnos_start_stop_hosts(self):
        """
        Test that the function start and stop hosts by the name.
        """
        inventory = {
            "hosts": {
                "router0": {
                    "port": EPHEMERAL_PORT,
                    "username": generate_random_string(5),
                    "password": generate_random_string(8),
                    "device_type": random.choice(available_platforms),
                },
                "router1": {
                    "port": EPHEMERAL_PORT,
                    "username": generate_random_string(5),
                    "password": generate_random_string(8),
                    "device_type": random.choice(available_platforms),
                },
            }
        }

        net = SimNOS(inventory=inventory)

        for _ in range(10):  # Run the loop 10 times
            router_to_toggle = random.choice(list(inventory["hosts"].keys()))  # Choose a router randomly

            if net.hosts[router_to_toggle].running:
                net.stop(hosts=router_to_toggle)
            else:
                net.start(hosts=router_to_toggle)

            # Always check the state of both routers. With ephemeral ports (#271)
            # there is no pre-loop full start, so build credentials at connect time
            # from `net.hosts[router].port`: a started host carries its real
            # OS-assigned port (connect succeeds), while a never-started host stays
            # at 0 → connect fails → the except asserts `not running`. A host that
            # was started then stopped keeps its resolved port (Host.stop does not
            # reset it), so connecting to that now-dead port also fails as expected.
            for router in inventory["hosts"]:
                credentials = {
                    "host": "localhost",
                    "username": inventory["hosts"][router]["username"],
                    "password": inventory["hosts"][router]["password"],
                    "port": net.hosts[router].port,
                    "device_type": netmiko_device_type_of(cast(str, inventory["hosts"][router]["device_type"])),
                }
                try:
                    with ConnectHandler(**credentials):
                        assert net.hosts[router].running
                except (NetMikoTimeoutException, NetMikoAuthenticationException):
                    assert not net.hosts[router].running

        net.stop()

    @pytest.mark.timeout(30)
    def test_external_a3_dir_via_inventory_plugin_path(self, tmp_path):
        """An out-of-tree A3 platform dir served via `nos: {plugin: <path>}`.

        The inventory path route (no registry entry) used to point at a py
        module; since #317 P-4 a bare path can only be an A3 platform dir (a
        static-only external platform — one needing `handler:` callables is
        registered as a `Nos(filename=[dir, py])` instance instead, see
        tests/plugins/test_custom_platform_e2e.py).
        """
        plat = tmp_path / "external_static"
        cmds = plat / "commands"
        cmds.mkdir(parents=True)
        (plat / "platform.yaml").write_text(
            'modes:\n  user:\n    prompt: "{{ base_prompt }}>"\ninitial_mode: user\n', encoding="utf-8"
        )
        cmds.joinpath("show_clock.yaml").write_text(
            "command: show clock\ntype: custom\nmode: [user]\noutput: show_clock.txt\n", encoding="utf-8"
        )
        cmds.joinpath("show_clock.txt").write_text("*21:01:33.000 AET 01 01 01 2022\n", encoding="utf-8")
        cmds.joinpath("default.yaml").write_text(
            "command: _default_\ntype: custom\noutput: default.txt\n", encoding="utf-8"
        )
        cmds.joinpath("default.txt").write_text("% Unknown command\n", encoding="utf-8")
        inventory: dict = {
            "hosts": {
                "R1": {
                    "username": "user",
                    "password": "user",
                    "port": EPHEMERAL_PORT,
                    "nos": {
                        "plugin": str(plat),
                    },
                }
            }
        }
        with SimNOS(inventory=inventory) as net:
            credentials: dict = {
                "host": "localhost",
                "username": "user",
                "password": "user",
                "port": net.hosts["R1"].port,  # real OS-assigned port (#271)
                "device_type": "generic",
            }
            with ConnectHandler(**credentials) as conn:
                output = conn.send_command("show clock")
                assert isinstance(output, str)
                assert output.strip() == "*21:01:33.000 AET 01 01 01 2022"
