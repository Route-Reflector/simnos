# 新しいプラットフォームの追加
SIMNOS は容易に拡張できるように設計されています。プラットフォームの静的なコマンドデータは **A3 プラットフォームディレクトリ**に置き、動的な挙動は任意の Python モジュールで追加します。両者は合成され、A3 dir が静的コマンドとモードを提供し、同名の Python モジュールがその上にハンドラ / デバイスクラスを重ねます (#264)。

!!! tip
    ホットリローダー (`simnos up --reload-commands`) は各プラットフォーム自身のソース — A3 プラットフォームディレクトリ **と** Python モジュール — を watch し、ファイル変更時にそのプラットフォームをリロードします (#274 / #281)。`commands/*.yaml`、出力 `.txt` / `.j2`、モジュール `.py` の編集は、live セッションの次のコマンドから反映されます。

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
- **`handler`** はプラットフォームの Python モジュール上の callable (device class の method またはモジュールレベル関数) を名前で参照し、dispatch 時に出力を計算します — 第 4 の排他 output channel (#317)。handler の戻り値は `str | None` (output のみ; 遷移は静的データ — 下記参照)。
- **`new_mode`** はコマンド実行後に遷移するモード名 (旧 `new_prompt` の後継)。
- **`transitions`** はモード条件付き遷移 map で、`new_mode` / `exit` と排他: key はコマンドの mode のいずれか、値は `{new_mode: <mode>}` または `{exit: true}` (#317)。例: arista_eos の `exit` は user/enable ではセッションを閉じ、config では enable に落ちます。
- **`variants`** は multi-capture 契約: `{name, output}` エントリのリスト (`variant_1` が primary を mirror、`variant_2`.. が alternate)、各々が自身の `.txt` を指す。
- **`alias`** はコマンドを別コマンドへの純粋な参照にします。alias が再指定できる唯一の dispatch field は `mode:` です (例: arista_eos の `do show ip int brief` は target が user/enable なのに対し config 専用、#317) — それ以外はすべて継承。
- **`exit`** はセッションを閉じるコマンドを表します。
- **`disables_paging`** は `--More--` ページャーをそのセッション以降無効化するコマンドを表します (例: `terminal length 0`、#307)。
- **`challenge`** はコマンド実行後にパスワードを求める (enable secret / `sudo -s`、#338) — [対話 challenge](#対話-challenge) を参照。
- **`_default_`** はモード非依存の unknown-command フォールバック: プラットフォームの実機エラー文言を記述 (例: Cisco IOS は `% Invalid input detected at '^' marker.`; vendor ごとに違うので copy-paste 禁止)。`mode` は取りません。

### 対話 challenge

`challenge:` block はコマンドを 2 段の対話にします: sub-prompt を表示し、応答行を 1 行読み、そのあとで遷移します — enable secret (`enable-admin` / `enable 15` / `administrator`) や `sudo -s` の形 (#338)。Phase 1 は `kind: password` に対応 (応答は host の資格情報で検証され、wire には一切 echo されません); `confirm` (y/n) は後の Phase です。

```yaml
command: sudo -s
type: simnos
mode: [user]
challenge:
  kind: password
  prompt: "[sudo] password for {{ username }}: "  # 1 行; 使える変数は base_prompt / username のみ
  auth: password          # `password` = host password; `secret` = host secret (未設定なら password に fallback)
  success:
    new_mode: enable      # 正解時のみ適用 (または `exit: true`)
  failure_output: "Sorry, try again."  # 不正解 / 空応答時の body; prompt はそのまま
```

- 応答は **1 回だけ** 検証されます — 不正解 / 空応答は `failure_output` を表示して現在のモードに留まります (retry ループ無し)。これは netmiko の `enable()` の期待 (再 prompt するとその read が hang する) と整合します。
- `auth: secret` を使う場合は inventory の host に `secret` (netmiko の `secret` 引数と同名) を設定します; 未設定なら host `password` に fallback するので、シミュレータは out-of-box で動きます。
- `challenge:` 内の **`mode`** はどのモードで発火するかを絞ります (既定: コマンドが有効な全モード)。発火しないモードでは、代わりにコマンド通常の `output` を返します — これがモードごとに応答を変える方法です (例: `enable-admin` は user モードで challenge、enable 済なら "already in admin mode" を表示) — 別コマンドを作らずに実現できます。
- `challenge` は `output` / `output_template` (非発火モードの応答) とは共存しますが `handler` / `variants` とは排他で、alias は target の challenge を継承します (再 authoring 不可)。

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
この方法は静的な A3 データの上に Python のフルパワーで動的な挙動を追加します。Python モジュールは `simnos/plugins/nos/platforms_py` パッケージに配置され、A3 プラットフォームと同名のモジュールが合成されます。パターン (#317): モジュールは `BaseDevice` subclass を定義し、その method (+ モジュールレベル関数) がプラットフォームの **handler namespace** になり、A3 コマンドが `handler:` で名前参照します — 未解決の参照はサーバ起動時に loud に fail します。callable のシグネチャと `str | None` 戻り値規則は [handler 契約](creating_nos_plugin.ja.md) を参照。

モジュールは**コマンドを一切 author しません**: legacy の `commands` dict はロード時に拒否され (#317)、旧 `NAME` / prompt 定数はもう読まれません。A3 dir も必須です — 同名の `platforms/<name>/` dir を持たない `platforms_py/<name>.py` は登録されず (registry が import 時に警告)、data lint も orphan モジュールと「py モジュール無しプラットフォームの `handler:` コマンド」の両方を検出します。
