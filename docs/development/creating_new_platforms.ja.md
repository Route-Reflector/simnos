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


## Python モジュール
この方法は YAML ファイル方式よりも柔軟です。動的な動作を実装でき、Python のフルパワーを活用できます。ただし、実装はやや難しくなります。Python モジュールは `simnos/plugins/nos/platforms_py` パッケージに配置されています。
