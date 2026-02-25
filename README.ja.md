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

SIMNOS はネットワーク OS の対話操作をシミュレートするライブラリです。Cisco IOS や Huawei SmartAX などのネットワークデバイスとの SSH 対話を簡単にシミュレートできます。主にテストと開発を目的としています。

[ドキュメント](https://route-reflector.github.io/simnos/) | [サンプル](https://route-reflector.github.io/simnos/examples/) | [プラットフォーム](https://route-reflector.github.io/simnos/platforms/)

## 由来

SIMNOS は [FakeNOS](https://github.com/fakenos/fakenos)（Denis Mulyalin 氏が作成、Enric Perpinyà Pitarch 氏がメンテナンス）から派生した独立プロジェクトです。ツール、プラットフォーム、アーキテクチャにおいて大きく分岐したため、upstream プロジェクトとの混同を避ける目的で SIMNOS としてリブランディングしました。

**AI 透明性：** 本プロジェクトでは AI 支援開発（Claude Code、Codex、Gemini 等）を積極的に活用しています。AI が生成したすべての変更は、マージ前に人間のメンテナーがレビューしています。

**FakeNOS との主な相違点：**

- パッケージ名: `simnos`（PyPI 上）
- パッケージマネージャ: uv（Poetry から移行）
- リンター/フォーマッター: Ruff（Black/Pylint から移行）
- Python サポート: 3.13 / 3.14
- CI: GitHub Actions ワークフローの近代化
- NOS プラットフォーム: 5 種を追加有効化（brocade_fastiron, ciena_saos, fortinet, juniper_screenos, ruckus_fastiron）
- Paramiko: 4.0 にアップグレード（DH Group Exchange サーバーモードのワークアラウンド含む）

## なぜ？

ネットワーク自動化のためのアプリケーションやスクリプトを書く上で、テストは極めて重要です。多くの場合、特定バージョンのネットワーク OS（NOS）を実行する物理または仮想のネットワーク機器を使ってテストを行いますが、このアプローチは最良の統合テスト結果を得られる反面、セットアップ・実行・後片付けに大きなオーバーヘッドが伴い、コンピュートやストレージリソースへの負荷も大きくなります。

もう一つのアプローチは、テスト対象のアプリケーションが実際のデバイスから出力を受け取っていると錯覚させるため、下位ライブラリのメソッドをモックすることです。このアプローチはユニットテストには非常に有効ですが、接続の確立やハンドリングといった側面のシミュレーションには対応できません。

SIMNOS は、完全な統合テストとデバイスインタラクションのモックによるテストの中間に位置します。SIMNOS では NOS プラグインを作成して、接続先のサーバーを実行しながら、事前定義した出力でアプリケーションの動作をテストできます。

## 何ができる？

SIMNOS でできること：

- 数千台のサーバーを起動してアプリケーションの負荷テスト
- ネットワーク OS のコマンドラインインターフェース（CLI）対話のシミュレーション
- カスタム NOS プラグイン作成のための高レベル API の提供
- Docker コンテナでの実行によるインフラとの統合の簡素化
- SIMNOS CLI ツールによるシミュレーションの素早い起動とプロトタイプ作成
- Windows、Mac、Linux 上の Python 3.13 / 3.14 で動作

## どうやって？

入力を送信して出力を得る ── これが多くのネットワーク OS との対話方法です。SIMNOS は特定の入力コマンドに対するレスポンスを事前定義できるため、分離された機能テストに最適です。

SIMNOS はプラグインで拡張可能なマイクロカーネルフレームワークです。コアは小さく最適化されており、ほとんどの機能はプラグインに委ねられています。

SIMNOS のプラグインシステム：

- Server Plugins - 接続先の各種サーバーを実行するプラグイン
- Shell Plugins - コマンドラインインターフェースシェルをシミュレートするプラグイン
- NOS Plugins - ネットワーク OS コマンドをシミュレートするプラグイン

## 何ができない？

SIMNOS はシミュレータであり、ネットワークの制御プレーン、データプレーン、管理プレーンのいずれもエミュレートしません。コマンドを入力として受け取り、事前定義された出力を返すだけです。

## 謝辞

SIMNOS は [FakeNOS](https://github.com/fakenos/fakenos) の成果の上に構築されています。オリジナルの作者とコントリビューターに感謝します：

- [Denis Mulyalin](https://github.com/dmulyalin) - FakeNOS オリジナル作者
- [Enric Perpinyà Pitarch](https://github.com/evilmonkey19) - FakeNOS メインコラボレーター・メンテナー

### インスピレーション元と参考

- [sshim](https://pythonhosted.org/sshim/) - SSH 自動化クライアントのテスト・デバッグ用ライブラリ
- [PythonSSHServerTutorial](https://github.com/ramonmeza/PythonSSHServerTutorial) - paramiko ベースの SSH サーバー作成チュートリアル
- [fake-switches](https://github.com/internap/fake-switches) - プラグイン式スイッチ/ルーターコマンドラインシミュレータ
- [ncs-netsim](https://developer.cisco.com/docs/nso/guides/#!the-network-simulator) - デバイスネットワークシミュレーションツール
- [cisshgo](https://github.com/tbotnz/cisshgo) - テスト用ネットワーク機器エミュレーション並行 SSH サーバー
- [scrapli-replay](https://pypi.org/project/scrapli-replay/) - SSH プログラムのテストを容易にし、セミインタラクティブ SSH サーバーを作成するツール

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
