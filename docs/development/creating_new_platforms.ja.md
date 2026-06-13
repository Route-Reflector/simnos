# 新しいプラットフォームの追加
SIMNOS は容易に拡張できるように設計されています。プラットフォームの静的なコマンドデータは **A3 プラットフォームディレクトリ**に置き、動的な挙動は任意の Python モジュールで追加します。両者は合成され、A3 dir が静的コマンドとモードを提供し、同名の Python モジュールがその上にハンドラ / デバイスクラスを重ねます (#264)。

!!! tip
    ホットリローダーは `simnos/plugins/nos` 内の **Python モジュール**が変更されたときにリロードします (`simnos --reload-commands`)。A3 プラットフォームディレクトリのホットリロードは別の、保留中の機能です (#274)。現状 A3 の編集は次回サーバー起動時に反映されます。

## A3 プラットフォームディレクトリ
プラットフォームの静的コマンドデータを追加する方法です。各プラットフォームは `simnos/plugins/nos/platforms/<name>/` 配下のディレクトリで、以下を含みます:

```
platforms/<name>/
  platform.yaml        # モード + メタデータ
  commands/
    <stem>.yaml        # 1 コマンド 1 ファイル (command フィールドが SSoT)
    <stem>.txt         # そのコマンドの literal 出力
    <stem>.j2          # jinja2 テンプレート出力 ({{ base_prompt }} が必要な場合)
```

コマンドファイルの *stem* は非意味的です — yaml 内の `command:` フィールドが唯一の真実 (SSoT)。lint は stem が sanitize 済コマンド名と一致しない場合に warning を出します (correctness ではなく discoverability の規約)。

### `platform.yaml`

プラットフォームのモード (名前 → prompt テンプレート) とメタデータを宣言します:

```yaml
modes:
  user:
    prompt: "{{ base_prompt }}>"
  enable:
    prompt: "{{ base_prompt }}#"
  config:
    prompt: "{{ base_prompt }}(config)#"
initial_mode: user
auth: none                      # 任意 — 例: dell_powerconnect は SSH auth を無効化
netmiko_device_type: cisco_ios  # 任意のメタデータ placeholder (#266 で消費)
ntc_platform: cisco_ios
```

prompt テンプレートは **jinja2** (`{{ base_prompt }}` はデバイスのホスト名)。`StrictUndefined` により未定義変数は loud な render エラーになります。`initial_mode` は宣言済みモードのいずれかである必要があります。flat CLI (特権/設定モードなし) のプラットフォームは単一モードだけを宣言します。モード名は慣習的に `user` / `enable` / `config` ですが、コマンドが参照する名前が存在しさえすれば任意の名前が使えます。

### `commands/<stem>.yaml`

1 コマンド 1 ファイル。フィールド (未知 field は reject — `extra="forbid"`):

```yaml
command: show version          # SSoT; ユーザーが入力するもの
type: ntc                      # ntc | simnos | custom (provenance クラス)
source:                        # 任意; type: ntc では規約上必須
  ntc_template: tests/cisco_ios/show_version/cisco_ios_show_version.raw
  ntc_commit: <sha>
help: show system version
mode: [user, enable]           # コマンドが有効なモード; 省略 = 全モード
output: show_version.txt       # 裸の .txt ファイル名、verbatim 読込 (literal)
```

- **`output`** は隣接する `.txt` ファイルを **verbatim** で参照 — `str.format` なし、brace エスケープなし。capture 中の literal な `{master:0}` はそのまま wire に届きます。
- **`output_template`** は隣接する `.j2` ファイルを jinja2 で render (出力が `{{ base_prompt }}` を補間する必要がある場合のみ使用)。1 コマンドは `output` か `output_template` のどちらか一方のみ。
- **`new_mode`** はコマンド実行後に遷移するモード名 (旧 `new_prompt` の後継)。
- **`variants`** は multi-capture 契約: `{name, output}` エントリのリスト (`variant_1` が primary を mirror、`variant_2`.. が alternate)、各々が自身の `.txt` を指す。
- **`alias`** はコマンドを別コマンドへの純粋な参照にします — 他の dispatch field は持ちません。
- **`exit`** はセッションを閉じるコマンドを表します。
- **`_default_`** はモード非依存の unknown-command フォールバック: プラットフォームの実機エラー文言を記述 (例: Cisco IOS は `% Invalid input detected at '^' marker.`; vendor ごとに違うので copy-paste 禁止)。`mode` は取りません。

### authoring 規約

A3 データ lint (`invoke lint-platform-data`、CI + pre-commit) が gate するもの:

- **encoding**: すべての `.txt` / `.j2` 出力ファイルは UTF-8・LF のみ・末尾改行必須 (空の出力ファイルは 0 バイトのまま)。
- **参照**: 各出力ファイルはちょうど 1 つの command yaml から参照される (1 yaml : 1 output)。未参照の出力ファイル (orphan)、欠落した参照先、共有参照を検出。
- **拡張子規約**: literal channel (`output` / variant の `output`) は `.txt`、`output_template` は `.j2`。`.yml` の command ファイル (loader は `.yaml` のみ glob) を検出。
- **`_default_` の存在**: 新規プラットフォームは必ず `_default_` command を定義する。rule 以前からのプラットフォームは `platform_data_lint_baseline.yaml` (repo root) に凍結済みで、この baseline は縮小しかしない。
- **`help` テキスト**: 本物の help を書く。自動生成 stub (`execute the command "X"`) は baseline に凍結済みで、新規追加は lint が fail する。stub を本物の help に置き換える際は同じ PR で baseline エントリも削除する。heritage 文言 `"Feel free to change it!"` は無条件で reject される。

加えて **warning** (非ブロッキング) も出力: ファイル名が sanitize 済コマンド名と不一致、`type: ntc` なのに `source` ブロック欠落。

yamllint の `quoted-strings` rule はプラットフォームデータディレクトリには適用されません (raw capture は yaml scalar ではなく `.txt` ファイルに置かれます)。

### NTC Templates からの candidate 生成

`sync_ntc_commands.py` は NTC Templates を A3 プラットフォームと比較し、まだ存在しないコマンドについて A3 take-in candidate ファイル (`commands/<stem>.yaml` + `.txt`、`source` ブロック付き `type: ntc`) を生成します — レビューして `platforms/<name>/` 配下にコピーしてください。新規プラットフォームの `platform.yaml` は手書きします (モード/auth は NTC fixture から導出できません)。

## Python モジュール
この方法は静的な A3 データの上に (または代わりに) 動的な挙動を追加します: Python のフルパワーによるハンドラとデバイスクラス。Python モジュールは `simnos/plugins/nos/platforms_py` パッケージに配置されます。A3 プラットフォームと同名のモジュールはその上に merge されます (コマンド単位でモジュール側が勝ちます)。
