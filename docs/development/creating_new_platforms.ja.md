# 新しいプラットフォームの追加
SIMNOS は容易に拡張できるように設計されています。新しいプラットフォームの追加がシンプルで、さまざまな方法で行えるように設計されています。現時点では、Python モジュールまたは YAML ファイルを使用する方法のみが可能です。

!!! tip
    `simnos/plugins/nos` 内の Python モジュールと YAML ファイルが変更された際に自動的にリロードするホットリローダーが実装されています。実行するには `simnos --reload-commands` を実行してください。

## YAML ファイル
実装したいプラットフォームがまだ存在しない場合に推奨される方法です。この方法の大きな利点は、新しいプラットフォームの追加が非常にシンプルであることです。ただし、動的な動作を実装できないため、Python モジュール方式ほど柔軟ではありません。

YAML ファイルは `simnos/plugins/nos/platforms_yaml` ディレクトリに配置されています。

### テンプレート記法のルール

YAML 内の文字列フィールド (`initial_prompt` および各コマンドの `output` / `prompt` / `new_prompt`) は、ランタイムで Python の `str.format()` によりレンダリングされます。top-level の `enable_prompt` / `config_prompt` は現状ランタイム shell からは消費されません (Python plugin は自前の module 定数を使用) が、同じテンプレート記法で書かれるため CI sweep が予防的に検証します。サポートされる記法は次の 2 つだけです:

- `{base_prompt}` — デバイスのベースプロンプト (ホスト名) に置換されます:

    ```yaml
    initial_prompt: "{base_prompt}>"
    ```

- `{{` / `}}` — リテラルの `{` / `}` を出力するためのエスケープ:

    ```yaml
    output: "{{master:0}}"   # 出力: {master:0}
    ```

format ミニ言語のそれ以外の記法は**非サポート**であり、記述ミスとして扱われます: attribute access (`{base_prompt.foo}`)、index access (`{base_prompt[0]}`)、format spec (`{base_prompt:d}`)、positional placeholder (`{}` / `{0}`)、未知の名前 (`{hostname}`)。`str.format()` が例外を投げずにレンダリングしてしまう記法 — 例えば `{base_prompt!r}` や `{base_prompt:>20}` — も同様で、ビルド時チェックが明示的に reject します。

テンプレートが不正な場合の挙動:

- **ランタイム**は lenient — エラーはログに記録され、セッションはクラッシュせず安全に縮退します: 不正な `output` は未整形のまま送信、不正な `prompt` 候補は match しない (コマンドが到達不能になる)、不正な `new_prompt` は現在のプロンプトを維持。
- **ビルド時**は loud — `invoke gen_docs_platform_commands` と CI のテンプレート sweep (`tests/test_gen_docs_platform_commands.py`) が platform / command / field を明示した `RuntimeError` を raise します。

### prompt key の意味

top-level の 3 つの prompt key は CLI の mode prompt を記述します:

- `initial_prompt` — login 直後の prompt。runtime shell が直接消費する唯一の key (セッションの初期 prompt になります)
- `enable_prompt` — 特権 mode の prompt (Cisco `enable` 系)
- `config_prompt` — 設定 mode の prompt

`enable_prompt` / `config_prompt` は authoring メタデータです: mode 遷移は command 単位の `prompt` / `new_prompt` だけで駆動されるため、この 2 key は「platform の mode を文書化する」ために使い、挙動を駆動させるものではありません。命名は Cisco 寄りなので、実機 CLI が当てはまらない platform では**実機の prompt を優先**し、命名との乖離は許容してください — 例: `hp_comware` は Comware の *system view* prompt (`[{base_prompt}]`) を `config_prompt` に格納しています (Comware にその名の「config mode」は無いが、値は実機に忠実)。flat CLI (mode なし、例: D-Link xStack) の platform はこれらの key を単に省略してください。

### authoring 規約

以下は `invoke lint-platform-yaml` (CI + pre-commit) と yamllint の `quoted-strings` rule で機械担保されます:

- **quote style**: scalar を quote するなら double quote。実機出力自体が double quote を含む場合のみ single quote を維持 (inline `# yamllint disable-line rule:quoted-strings` でマーク)
- **`prompt` の形式**: 裸の文字列と list はどちらも有効な authoring sugar — loader が commit 前に list へ正規化するため、runtime は常に list を見ます
- **`_default_` command**: **新規** platform は必ず定義してください。文言はその platform の実機の unknown-command エラー (例: Cisco IOS は `% Invalid input detected at '^' marker.`、NX-OS は `% Invalid command at '^' marker.` — vendor ごとに違うので copy-paste 禁止)。出典は entry 直上に `# source: <URL> (retrieved YYYY-MM-DD)` コメントで記録します。既存の未定義 platform は `platform_yaml_lint_baseline.yaml` に凍結済みで、baseline は縮小のみ許可です
- **`help` text**: 本物の help を書いてください。auto-generated stub (`execute the command "X"`) は baseline に凍結済みで、新規追加は lint で fail します
- **`output_variants`**: 同一 command の別 capture を保持する data-only な optional field。runtime は消費しませんが、実機出力の再収集が常に可能とは限らないため保全されています

未知 field は load 時に reject されます: top-level key の typo は `ValueError`、command field の typo は pydantic validation (`extra="forbid"`) で fail し、silent drop は起きません。


## Python モジュール
この方法は YAML ファイル方式よりも柔軟です。動的な動作を実装でき、Python のフルパワーを活用できます。ただし、実装はやや難しくなります。Python モジュールは `simnos/plugins/nos/platforms_py` パッケージに配置されています。
