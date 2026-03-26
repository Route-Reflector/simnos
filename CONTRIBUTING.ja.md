[English](CONTRIBUTING.md) | [日本語](CONTRIBUTING.ja.md)

# SIMNOS へのコントリビューション

SIMNOS に興味を持っていただきありがとうございます！

始める前に、このプロジェクトが何であり、何でないかを理解してください。

## SIMNOS とは（そして何でないか）

SIMNOS はネットワーク自動化ツールのための**軽量テストスタブ**です。テストと開発に必要な範囲で NOS のコマンドラインインターフェースをシミュレートします。それ以上のことはしません。

**SIMNOS はフルネットワークエミュレータではありません。** CML2、ContainerLab、GNS3 などのプロジェクトはコントロールプレーン、データプレーン、プロトコルのリッチなエミュレーションを提供します。SIMNOS はそれらと競合することを目指していません。ルーティングプロトコルの動作やパケット転送が必要であれば、それらのツールを使ってください。

**設計原則:** YAML で静的にできることは YAML で行う。Python は動的な処理（例: `show clock` で現在時刻を返す、config モードのコマンドで内部状態を変更する）にのみ使用する。

## AI の利用について（AI Transparency）

このプロジェクトでは AI アシスタント（Claude Code、Codex、Gemini 等）を積極的に開発に活用しています。AI が生成した変更はすべて、人間のメンテナーがレビューしてからマージしています。

**AI を利用したコントリビューションも歓迎します。** AI ツールを使用した場合は以下をお願いします:

- PR の説明に使用した AI ツールを明記してください
- 利用可能な最上位のモデルを、推論（Reasoning）機能を有効にした状態で使用してください
- 提出前に AI の出力を自分でレビューしてください — コードの責任は AI ではなくあなたにあります
- 可能であれば、別の AI でクロスレビューしてください（例: Claude で書いたコードを Gemini でレビュー）。異なる AI は異なる観点で問題を発見します

**AI を利用した PR の大量送信や、Issue・コメントへの大量投稿は禁止です。** 内容が正しくてもスパムとみなし、レビューせずクローズします。

## コントリビューションの方法

### バグ報告

[Issue](https://github.com/Route-Reflector/simnos/issues) を開いて、以下を記載してください:

- 期待した動作
- 実際の動作
- 再現手順
- 環境（OS、Python バージョン、simnos バージョン）

### 機能提案

まず Issue を開いて相談してください。このプロジェクトはスコープが限定されており、すべての機能が適合するわけではありません。事前に議論することでお互いの時間を節約できます。

### 変更の提出

- **小さな修正**（タイポ、軽微なバグ）: Issue と PR を同時に出してOKです。
- **大きな変更**（新機能、リファクタリング）: まず Issue を開いてください。コードを書く前にアプローチを合意しましょう。
- **Issue なしの PR** はレビューが困難です。コンテキストがないと、その変更が適切かどうか判断できません。*何を*だけでなく*なぜ*を説明してください。

> 注意: このプロジェクトは一人の開発者が空き時間にメンテナンスしています。レビューには時間がかかることがあります。メンテナーの判断で PR をリジェクトすることもあります — 個人的に受け取らないでください。

## 新プラットフォームの追加

新しいプラットフォームのコントリビューションは歓迎です！以下に留意してください:

- **実機での動作検証はコントリビューターの責任です。** メンテナーは多くの場合、実機にアクセスできません。提出前に実デバイスの出力（または信頼できるリファレンスデータ）でテストしてください。
- **[NTC Templates](https://github.com/networktocode/ntc-templates) にまだない場合**、パーサーの追加も検討してください。ネットワーク自動化エコシステム全体の利益になりますし、SIMNOS は NTC のテストデータをコマンド出力のソースとして利用しています。
- **プラットフォーム YAML の構造**: `simnos/plugins/nos/platforms_yaml/` の既存プラットフォームを参考にしてください。最低限必要なもの:
  - `initial_prompt` — デフォルトの CLI プロンプト
  - `commands` — コマンド名と出力、ヘルプテキスト、プロンプトのマッピング
- 詳細は [新プラットフォームの作成](https://route-reflector.github.io/simnos/ja/development/creating_new_platforms/) ガイドを参照してください。

## 開発環境のセットアップ

### 前提条件

- Python 3.13 または 3.14
- [uv](https://docs.astral.sh/uv/)（パッケージマネージャー）
- Docker（任意、コンテナベースのテスト用）

### 始め方

```bash
# リポジトリをフォークしてクローン
git clone https://github.com/<your-username>/simnos.git
cd simnos

# 依存関係のインストールと仮想環境の作成
uv sync

# pre-commit フックのインストール
uv run pre-commit install
```

### テストの実行

```bash
# すべてのチェック（lint + security + tests）を Docker で実行
uv run invoke tests

# Docker なしでローカル実行
uv run invoke tests --local

# 個別のチェック
uv run invoke ruff --local      # リンティングとフォーマット
uv run invoke bandit --local    # セキュリティチェック
uv run invoke pytest --local    # ユニットテスト
```

### コードスタイル

- **リンター/フォーマッター**: [Ruff](https://docs.astral.sh/ruff/) — `pyproject.toml` で設定
- **セキュリティ**: [Bandit](https://bandit.readthedocs.io/) — 同じく `pyproject.toml` で設定
- **pre-commit フック** がコミット時に自動実行されます（ruff + bandit）
- 行の長さ: 120 文字
- 対象 Python: 3.13+

詳細は [Conventions](https://route-reflector.github.io/simnos/ja/development/conventions/) を参照してください。

### コミットメッセージ

以下のフォーマットに従ってください:

```
type: description (#issue-number)
```

type: `feat`, `fix`, `refactor`, `docs`, `chore`, `test`

例:
- `feat: add show privilege command for cisco_ios (#124)`
- `fix: handle offline NTC Templates clone (#123)`
- `docs: add CONTRIBUTING.md (#121)`

## ライセンス

コントリビューションにより、あなたの貢献が [MIT ライセンス](LICENSE) の下でライセンスされることに同意したものとみなされます。
