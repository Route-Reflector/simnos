# Simulated Network Operating Systems - SIMNOS

[![PyPI versions][pypi-pyversion-badge]][pypi-pyversion-link]
[![PyPI][pypi-latest-release-badge]][pypi-latest-release-link]
[![GitHub Discussion][github-discussions-badge]][github-discussions-link]
[![Ruff][ruff-badge]][ruff-link]
[![Tests][github-tests-badge]][github-tests-link]
[![Downloads][pepy-downloads-badge]][pepy-downloads-link]


> 「現実とは、非常にしつこい幻想にすぎない。」
>
> ~ アルベルト・アインシュタイン

SIMNOS はネットワークオペレーティングシステムの対話をシミュレートします。
Cisco IOS や Huawei SmartAX などのネットワーク機器を SSH 経由で
簡単にシミュレートできます。本プロジェクトは主にネットワーク自動化ツールや
スクリプトのテスト・開発を目的としています。

[インストール](usage/installation.md) | [サンプル](examples/index.md) | [プラットフォーム](platforms/index.md)


## インストール
[![PyPI versions][pypi-pyversion-badge]][pypi-pyversion-link]

PyPI からインストールできます:
```bash
pip install simnos
```

開発環境には [uv](https://docs.astral.sh/uv/) の使用を推奨します:
```bash
uv sync
```


## 使い方
Cisco IOS と Huawei SmartAX の2台をシミュレートする例です。
まず `inventory.yaml` を作成します:
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

次に `main.py` を作成します:
```python
from simnos import SimNOS
network_os = SimNOS(inventory='inventory.yaml')
network_os.start()
```

スクリプトを実行します:
```bash
python main.py
```

これで完了です！ :dizzy: Cisco IOS と Huawei SmartAX の2台が起動しました。
SSH クライアントで接続できます:
```bash
# Cisco IOS に接続
ssh -p 6000 admin@localhost

# Huawei SmartAX に接続
ssh -p 6001 admin@localhost
```

実行できるコマンド例 :computer: :

1. Cisco IOS コマンド:
    - `show version`
    - `show interfaces`
    - `show ip interface brief`
2. Huawei SmartAX コマンド:
    - `display version`
    - `display board`
    - `display sysman service state`

!!! tip
    ドキュメントを読む時間がない場合は、`help` または `?` コマンドで利用可能なすべてのコマンドを表示できます。

## CLI の使い方
SIMNOS にはコマンドラインツールが付属しています。
事前定義されたサンプルを以下のコマンドで実行できます:
```bash
simnos
```

この場合、3台のデバイスが作成されます:
- Cisco IOS (ユーザ名 `user`、パスワード `user`、ポート `6000`)
- Huawei SmartAX (ユーザ名 `user`、パスワード `user`、ポート `6001`)
- Arista EOS (ユーザ名 `user`、パスワード `user`、ポート `6002`)

インベントリファイルを指定することもできます:
```bash
simnos --inventory inventory.yaml
```

## 謝辞

SIMNOS は [FakeNOS](https://github.com/fakenos/fakenos) のフォークです。オリジナルの作者 [Denis Mulyalin](https://github.com/dmulyalin) 氏とメンテナの [Enric Perpinyà](https://github.com/evilmonkey19) 氏の基盤的な貢献に感謝いたします。詳細は[コラボレーター](collaborators.md)ページをご覧ください。

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
