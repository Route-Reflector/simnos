# Simulated Network Operating Systems - SIMNOS

[![PyPI versions][pypi-pyversion-badge]][pypi-pyversion-link]
[![PyPI][pypi-latest-release-badge]][pypi-latest-release-link]
[![GitHub Discussion][github-discussions-badge]][github-discussions-link]
[![Ruff][ruff-badge]][ruff-link]
[![Tests][github-tests-badge]][github-tests-link]
[![Downloads][pepy-downloads-badge]][pepy-downloads-link]


> "Reality is merely an illusion, albeit a very persistent one."
>
> ~ Albert Einstein

SIMNOS simulates Network Operating Systems interactions. You can simulate
network devices like Cisco IOS or Huawei SmartAX interactions over
SSH with little effort. This project is mainly intended for testing
and development purposes.

[Installation](usage/installation.md) | [Examples](examples/index.md) | [Platforms](platforms/index.md)


## Installation
[![PyPI versions][pypi-pyversion-badge]][pypi-pyversion-link]

The package is available on PyPI:
```bash
pip install simnos
```

For development, we recommend using [uv](https://docs.astral.sh/uv/):
```bash
uv sync
```


## Usage
This is sample example in which we simulate two devices, one running Cisco IOS
and another running Huawei SmartAX. To run it, create `inventory.yaml` file with
the following content:
```yaml
hosts:
  R1:
    username: admin
    password: admin
    platform: cisco_ios
    port: 6000
  R2:
    username: admin
    password: admin
    platform: huawei_smartax
    port: 6001
```

Then create `main.py` file with the following content:
```python
from simnos import SimNOS
network_os = SimNOS(inventory='inventory.yaml')
network_os.start()
```

Run the script:
```bash
python main.py
```

And Voila! :dizzy: You have two devices running, one with Cisco IOS and another with Huawei SmartAX.
In case you want to connect to them, you can use any SSH client, like `ssh`:
```bash
# To connect to Cisco IOS
ssh -p 6000 admin@localhost

# To connect to Huawei Smartax
ssh -p 6001 admin@localhost
```

And here are some commands :computer: you can try:

1. Cisco IOS commands:
    - `show version`
    - `show interfaces`
    - `show ip interface brief`
2. Huawei SmartAX commands:
    - `display version`
    - `display board`
    - `display sysman service state`

!!! tip
    Many times, we don't have time to read the documentation. There is a simple `help` command which shows all the available commands. It can be called using `help` or `?`.

## CLI Usage
SIMNOS comes with a CLI tool that allows you to start the simulation from the
command line. You can try a predefined example by running:
```bash
simnos
```

In this case 3 devices will be created:
- Cisco IOS device with username `user` and password `user` on port `6000`
- Huawei SmartAX device with username `user` and password `user` on port `6001`
- Arista EOS device with username `user` and password `user` on port `6002`

You can also specify the inventory file to use:
```bash
simnos --inventory inventory.yaml
```

## Acknowledgements

SIMNOS is a fork of [FakeNOS](https://github.com/fakenos/fakenos), originally created by [Denis Mulyalin](https://github.com/dmulyalin) and maintained by [Enric Perpinyà](https://github.com/evilmonkey19). We are grateful for their foundational work that made this project possible. See the [Collaborators](collaborators.md) page for more details.

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
[pypi-latest-release-badge]:   https://img.shields.io/pypi/v/simnos.svg?logo=data:image/svg+xml;base64,PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0iVVRGLTgiPz4KPHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA2NCA2NCI+CiAgPGRlZnM+CiAgICA8c3R5bGU+CiAgICAgIC5iZyB7IGZpbGw6ICMwMDk0ODU7IHN0cm9rZS13aWR0aDogMDsgfQogICAgICAuYm9keS1zaWRlIHsgZmlsbDogIzdjYjM0MjsgfQogICAgICAuYm9keS10b3AgeyBmaWxsOiAjOWNjYzY1OyB9CiAgICAgIC5hcnJvdyB7IGZpbGw6ICNmZmY7IH0KICAgICAgLmFycm93LWxpbmUgeyBzdHJva2U6ICNmZmY7IHN0cm9rZS13aWR0aDogMi41OyBzdHJva2UtbGluZWNhcDogcm91bmQ7IGZpbGw6IG5vbmU7IH0KICAgIDwvc3R5bGU+CiAgPC9kZWZzPgogIDwhLS0gUm91bmRlZCBzcXVhcmUgYmFja2dyb3VuZCAtLT4KICA8cmVjdCBjbGFzcz0iYmciIHg9IjIiIHk9IjIiIHdpZHRoPSI2MCIgaGVpZ2h0PSI2MCIgcng9IjEyIiByeT0iMTIiLz4KICA8IS0tIFJvdXRlciBib2R5IChsYXJnZXIgY3lsaW5kZXIpIC0tPgogIDwhLS0gU2lkZSBmYWNlIC0tPgogIDxwYXRoIGNsYXNzPSJib2R5LXNpZGUiIGQ9Ik0gOCwyNiBRIDgsMzQgMzIsMzggUSA1NiwzNCA1NiwyNiBMIDU2LDQyIFEgNTYsNTAgMzIsNTQgUSA4LDUwIDgsNDIgWiIvPgogIDwhLS0gVG9wIGVsbGlwc2UgLS0+CiAgPGVsbGlwc2UgY2xhc3M9ImJvZHktdG9wIiBjeD0iMzIiIGN5PSIyNiIgcng9IjI0IiByeT0iOSIvPgogIDwhLS0gVmVydGljYWwgYXJyb3cgKHVwLWRvd24gY29ubmVjdGVkKSBpbnNpZGUgdG9wIGVsbGlwc2UgLS0+CiAgPGxpbmUgY2xhc3M9ImFycm93LWxpbmUiIHgxPSIzMiIgeTE9IjIwIiB4Mj0iMzIiIHkyPSIzMiIvPgogIDxwb2x5Z29uIGNsYXNzPSJhcnJvdyIgcG9pbnRzPSIzMiwxOSAzNS41LDIzIDI4LjUsMjMiLz4KICA8cG9seWdvbiBjbGFzcz0iYXJyb3ciIHBvaW50cz0iMzIsMzMgMjguNSwyOSAzNS41LDI5Ii8+CiAgPCEtLSBIb3Jpem9udGFsIGFycm93IChsZWZ0LXJpZ2h0IGNvbm5lY3RlZCkgaW5zaWRlIHRvcCBlbGxpcHNlIC0tPgogIDxsaW5lIGNsYXNzPSJhcnJvdy1saW5lIiB4MT0iMTYiIHkxPSIyNiIgeDI9IjQ4IiB5Mj0iMjYiLz4KICA8cG9seWdvbiBjbGFzcz0iYXJyb3ciIHBvaW50cz0iMTUsMjYgMTksMjIuNSAxOSwyOS41Ii8+CiAgPHBvbHlnb24gY2xhc3M9ImFycm93IiBwb2ludHM9IjQ5LDI2IDQ1LDIyLjUgNDUsMjkuNSIvPgo8L3N2Zz4K
