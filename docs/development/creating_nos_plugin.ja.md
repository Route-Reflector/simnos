# NOS プラグインの作成

NOS プラグインは、インベントリホストの `device_type` / `nos.plugin` が解決する
先です: コマンドデータと (任意で) 動的な挙動を持ちます。v3 (#317) 以降、authoring
形式は **1 つだけ** です:

- **A3 プラットフォームディレクトリ** — `platform.yaml` (modes + メタデータ) と、
  コマンド 1 個につき 1 つの `commands/<stem>.yaml` (隣接する `.txt` / `.j2` 出力)。
  これが必須部分で、A3 dir を持たないプラットフォームはコマンドを配信できません。
- 任意の **Python handler モジュール** — `BaseDevice` subclass (+ モジュールレベル
  関数) で、その method を A3 の `handler:` フィールドがサーバ起動時にバインドします。
  py モジュールの役割はこれだけで、**コマンドは一切 author しません** (legacy の
  `commands` dict、`NAME` / `INITIAL_PROMPT` / `ENABLE_PROMPT` / `CONFIG_PROMPT`
  定数、`Nos.from_dict` は #317 で削除されました)。

A3 authoring の完全なリファレンス (ファイルレイアウト、`platform.yaml`、コマンド
フィールド、lint 規約) は
[新しいプラットフォームの追加](creating_new_platforms.ja.md) にあります。この
ページはプラグイン固有の 2 トピック — SIMNOS パッケージの**外**でプラットフォーム
を用意する方法と、**handler 契約** — を扱います。

## 外部カスタムプラットフォーム

プラットフォームは SIMNOS パッケージツリーの中に置く必要はありません。同じ A3
dir をディスク上の任意の場所に author します:

```
my_platform/
  platform.yaml
  commands/
    show_version.yaml
    show_version.txt
    show_marker.yaml      # handler: make_show_marker
    default.yaml          # _default_
    default.txt
my_platform_handlers.py   # 任意: device class + handler callable
```

### 静的データのみ (handler 無し)

インベントリホストからディレクトリを直接指します:

```yaml
hosts:
    R1:
        username: user
        password: user
        port: 0
        nos:
            plugin: path/to/my_platform
```

```bash
simnos up -i path/to/inventory.yaml
```

Python では、ディレクトリパスを登録します (str の plugin は A3 platform dir
限定 — `.py` パスと dict 形式は拒否されます):

```python
from simnos import SimNOS

net = SimNOS(inventory=inventory, plugins=["path/to/my_platform"])
```

### 動的 handler 付きプラットフォーム

`handler:` コマンドは A3 dir と一緒に handler モジュールをロードする必要が
あるため、`Nos` を自分で組み立ててインスタンスを登録します。プラットフォーム名は
A3 ディレクトリの basename で、インベントリはその名前で参照します:

```python
from simnos import Nos, SimNOS

nos = Nos(filename=["path/to/my_platform", "path/to/my_platform_handlers.py"])

inventory = {
    "hosts": {
        "R1": {
            "username": "user",
            "password": "user",
            "port": 0,
            "nos": {"plugin": "my_platform"},
        },
    }
}

net = SimNOS(inventory=inventory, plugins=[nos])
net.start()
```

未解決の `handler:` 参照 (モジュールに該当 callable が無い) は `start()` で loud
に fail します — 出力の無いコマンドとして黙って動くことはありません。

## Python handler モジュール

モジュールはローカル定義の `BaseDevice` subclass を最大 1 つ定義し、それは
**自動検出** されます (他の device class の import は問題ありません。ローカル
定義の subclass のみが対象で、2 つ以上は loud な `ValueError` です)。その
非アンダースコア method と、ローカル定義のモジュールレベル関数が、プラット
フォームの **handler namespace** になり、A3 コマンドが名前で参照します:

```yaml
# commands/show_marker.yaml
command: show marker
type: custom
help: dynamic marker command
mode: [user, enable]
handler: make_show_marker
```

```python
"""my_platform_handlers.py"""

from simnos.plugins.nos.base_device import BaseDevice

DEFAULT_CONFIGURATION = "path/to/configurations/my_platform.yaml.j2"  # 任意


class MyPlatform(BaseDevice):
    """handler 間で共有する device 状態を保持する。"""

    def make_show_marker(self, base_prompt, current_mode, current_prompt, command):
        return f"marker from {current_mode}"
```

device-class method とモジュールレベル関数の両方に同名が定義されている場合は
ロード時エラーです (暗黙の優先順位はありません)。`classmethod` は handler に
できません (第 1 引数が device でなく `cls` にバインドされるため)。

class インスタンスはホストのセッション間で共有されるため、handler は状態を保持
できます (例: device の IP を変更するコマンドを作れば、以降のコマンドはその変更を
反映できます)。`BaseDevice` は `self.configurations` (任意の
`DEFAULT_CONFIGURATION` が指す YAML / Jinja2
[configuration](../usage/configurations.ja.md) ファイルからロード。
`Nos(configuration_file=...)` が上書き) と、
`simnos/plugins/nos/platforms_py/templates/` 配下の Jinja2 テンプレートを render
する `render(template, **kwargs)` ヘルパを提供します。

## callable 契約

型付きの契約は `simnos.core.command_contract` (`CommandHandler` Protocol) に
あります — 型注釈に使いたければ import してください。形が合っていれば素の関数で
そのまま動きます。

シェルは handler を次のように呼び出します:

```python
handler(device, base_prompt=..., current_mode=..., current_prompt=..., command=...)
```

`device` はあなたの `BaseDevice` subclass のインスタンス (device class の無い
プラットフォームでは `None`) です。device-class method は自然にこの形を満たします:
`device` が `self` にバインドされます。`command` はユーザーが打った文字通りの行です
(`sh ver` のような省略形は展開されずに渡ります)。

handler は **出力のみ** を返します (#317):

- `str` - 表示する出力文字列
- `None` - 応答なし

mode 遷移とセッション終了は静的な authoring データ (コマンドの `new_mode` /
`exit` / `transitions`) であり、handler の戻り値ではありません — 旧 dict 返し
(`CommandResult`) 形式は削除されました。dict (や `str | None` 以外) を返し続ける
handler には固定の `% Internal error` 行が応答され、エラーログが残ります。prompt
文字列ではなく `current_mode` 引数で分岐してください。

静的な出力ファイルと異なるルールが 2 つあります:

- **自分でフォーマットする。** シェルは handler 出力を render しません — handler は
  `base_prompt` を引数として受け取り、自分で文字列を組み立てます。device 出力中の
  リテラルの中括弧はエスケープ不要です。
- **raise してよい** のは「起きてはならない」状態のとき: シェルはサーバ側で full
  traceback をログし、クライアントには固定の `% Internal error` 行を返します —
  traceback が wire に届くことはありません。

## v2 プラグインの移行

v2 時代の py プラグイン (モジュールの `commands` dict + prompt 定数) はもう
ロードできません: `commands` dict はロード時に拒否され、定数は読まれません。
dict の各エントリを A3 の `commands/<stem>.yaml` に移し (`prompt:` → `mode:`
名、`new_prompt:` → `new_mode:`、出力テキスト → 隣接 `.txt` / `.j2`)、modes を
`platform.yaml` に宣言し、モジュールには device class + handler callable だけを
残してください — [changelog の移行表](../changelog.ja.md) と
[新しいプラットフォームの追加](creating_new_platforms.ja.md) を参照。
