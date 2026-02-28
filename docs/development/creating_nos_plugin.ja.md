NOS プラグインを作成し、サーバーを起動する前に SIMNOS インスタンスに登録できます。

NOS プラグインを作成する方法はいくつかあります:

1. [YAML ファイルから NOS プラグインを作成する](creating_nos_plugin.md#create-nos-plugin-from-a-yaml-file)
2. [Python ファイルから NOS プラグインを作成する](creating_nos_plugin.md#create-nos-plugin-from-a-python-file)
3. [Nos クラスから NOS プラグインを作成する](creating_nos_plugin.md#create-nos-plugin-from-the-nos-class)

上記の方法のいずれかが他より優れているというわけではなく、それぞれに適したユースケースがあります。ただし、作成がシンプルで柔軟性が低いものから、より複雑で柔軟性が高いものの順にリストされています。

NOS プラグインでは以下の属性を定義できます:

- `name` - インベントリで使用するプラグインの参照名
- `initial_prompt` - 表示されるシェルプロンプトの定義または変更に使用
- `enable_prompt` - `enable` モードへの移行に使用（任意）
- `config_prompt` - `config` モードへの移行に使用（任意）
- `commands` - この NOS プラグインが出力を返すことができるコマンドの辞書

## 初期 NOS シェルプロンプト
初期 NOS シェルプロンプトは、シェル起動時にユーザーに表示されるインジケーターです。
中括弧 `{}` 内で定義されている場合、`base_prompt` フォーマッターを使用してインベントリからホスト名を参照できます。

例えば、初期プロンプトが `{base_prompt}>` に設定されている場合、フォーマットメソッドを適用した後の最終プロンプトは、インベントリのホスト `R1` に対して `R1>` となります。

## NOS コマンド
コマンドは、コマンド文字列をキーとし、出力やヘルプ、正しく呼び出すために必要なプロンプトなどのコマンドの詳細を含む別の辞書を値とする辞書です。

Python コマンド辞書のサンプル内容:

```{ .python .annotate }
commands = {
    "enable": {
        "output": None, # (6)
        "new_prompt": "{base_prompt}#", # (2)
        "help": "enter exec prompt", # (5)
        "prompt": "{base_prompt}>", # (10)
    },
    "show clock": {
        "output": MyDevice.make_show_clock, # (9)
        "help": "Display the system clock",
        "prompt": ["{base_prompt}>", "{base_prompt}#"], # (3)
    },
    "show running-config": {
        "output": """ # (4)
service timestamps debug datetime msec
service timestamps log datetime msec
no service password-encryption
!
hostname {base_prompt} # (12)
!
boot-start-marker
boot-end-marker
        """,
        "help": "Current operating configuration",
        "prompt": "{base_prompt}#",
    },
    "show version": {
        "output": """
Version: 0.1.0
{base_prompt} uptime is 1 day, 17 hours, 32 minutes
Uptime for this control processor is 1 day, 17 hours, 33 minutes

Configuration register is 0x2102
        """,
        "help": "System hardware and software status",
        "prompt": "{base_prompt}#",
    },
    "_default_": { # (11)
        "output": "% Invalid input detected at '^' marker.",
        "help": "Output to print for unknown commands",
    },
    "terminal width 511": {
        "output": "", # (8)
        "help": "Set terminal width to 511"
    },
    "terminal length 0": {
        "output": "",
        "help": "Set terminal length to 0"
    },
    "exit": {"output": True, "help": "Exit commands shell"} # (7)
}
```

1. コマンド出力を生成するカスタム関数
2. コマンド出力が返された後に表示する新しいプロンプト
3. このコマンドが有効な現在のプロンプトのリスト（コマンドのスコープ）
4. 複数行のコマンド出力
5. シェルで `?` または `help` が入力された場合に表示されるヘルプメッセージ
6. コマンド出力として `None` を返すとレスポンスは生成されない
7. コマンド出力として True を返すとシェルが閉じる
8. 空の出力を返すと改行文字のみを含むレスポンスが生成される
9. 出力は関数などの呼び出し可能なオブジェクトを参照でき、シェルプラグインによって実行されてレスポンス内容が生成される
10. このコマンドが有効な唯一のプロンプト
11. 未定義コマンドに使用されるデフォルトのレスポンス内容
12. 返される出力には `base_prompt` フォーマッターを含めることができる

コマンド辞書がサポートする属性:

| Attribute       | Emoji                            | Description                                               |
| -------------- | ---------------------------------| --------------------------------------------------------- |
| `output`       | :octicons-command-palette-16:    | レスポンスで返すコマンド出力                  |
| `help`         | :material-help-box:              | コマンドのヘルプメッセージ内容                              |
| `prompt`       | :simple-powershell:              | このコマンドが有効なインジケーターまたはインジケーターのリスト |
| `new_prompt`   | :simple-nushell:                | コマンド出力が返された後に表示する新しいプロンプト   |
| `alias`        | :material-drama-masks:              | 呼び出し可能な関数としてのコマンド出力                      |


コマンド辞書の `output` 属性の値は以下の型が使用できます:

- `string` - レスポンスで返す1行以上の文字列。`base_prompt` フォーマッターを含めることができます。
- `None` - レスポンスは返されません
- `True` - シェルを閉じます
- `callable` - 返される出力は関数などの呼び出し可能なオブジェクトを参照でき、シェルプラグインによって実行されてレスポンス内容が生成されます

`prompt` と `new_prompt` 属性に関する補足事項。

`prompt` はこのコマンドが現在のプロンプトのコンテキストで有効かどうかを示すフィルターとして機能します。現在のプロンプトの値がコマンドのプロンプトと等しくない場合、レスポンス出力は `_default_` コマンドの出力値（通常はエラーメッセージ）から取得されます。

`new_prompt` は単純に、コマンド出力がユーザーに返された後、現在のプロンプト値を `new_prompt` の値に設定すべきであることを示します。

## Create a NOS plugin from a YAML file

以下のサンプル内容で `path/to/my_nos.yaml` に YAML ファイルを作成します:

```yaml
name: MySimNOSPlugin

initial_prompt: "{base_prompt}>"

commands:
  enable:
    output: null
    new_prompt: "{base_prompt}#"
    help: enter exec prompt
    prompt: "{base_prompt}>"
  show clock:
    output: "*21:01:33.000 AET 01 01 01 2022"
    help: "Display the system clock"
    prompt: ["{base_prompt}#"]
  show running-config:
    output: |
      service timestamps debug datetime msec
      service timestamps log datetime msec
      no service password-encryption
      !
      hostname {base_prompt}
      !
      boot-start-marker
      boot-end-marker
    help: "Current operating configuration"
    prompt: "{base_prompt}#"
  show version:
    output: |
      Version: 0.1.0
      {base_prompt} uptime is 1 day, 17 hours, 32 minutes
      Uptime for this control processor is 1 day, 17 hours, 33 minutes

      Configuration register is 0x2102
    help: System hardware and software status
    prompt: "{base_prompt}#"
  _default_:
    output: "% Invalid input detected at '^' marker."
    help: "Output to print for unknown commands"
  terminal width 511: {"output": "", "help": "Set terminal width to 511"}
  terminal length 0: {"output": "", "help": "Set terminal length to 0"}
```

この YAML ファイルを使用して、以下のように NOS プラグインを登録できます:

```yaml
hosts:
    R1:
        username: user
        password: user
        port: 6000
        nos:
            plugin: path/to/my_nos.yaml
```

素早くテストするには、ターミナルで以下のコマンドを実行してください:

```bash
simnos -i path/to/inventory.yaml
```

## Create a NOS plugin from a Python file

Python モジュールから作成された NOS プラグインは、インタラクティブ性を可能にする SIMNOS の主要な強みの一つです。コマンドの考え方は、出力が事前定義された出力ではなく、コマンドの出力を返す関数を定義できることです。これにより、コマンドの出力を動的にでき、時間、日付、ホストなどに応じて変化させることができます。Python NOS モジュールを開発する場合は、このセクションを注意深く読む価値があります。

以下のコードはテスト中に使用する Python モジュールですが、完全に機能します（Netmiko ではオブジェクトはジェネリックです）:

```python
"""
This is a testing module
"""

import time

from simnos.plugins.nos.platforms_py.base_template import BaseDevice

NAME: str = "test_module"
INITIAL_PROMPT = "{base_prompt}>"
ENABLE_PROMPT = "{base_prompt}#"
CONFIG_PROMPT = "{base_prompt}(config)#"
DEVICE_NAME: str = "TestModule"

DEFAULT_CONFIGURATION: str = "tests/assets/test_module.yaml.j2"


# noqa: ARG002
class TestModule(BaseDevice):
    """
    Class that keeps track of the state of the TestModule device.
    """

    def make_show_clock(self, base_prompt, current_prompt, command):
        """Return the current time."""
        return str(time.ctime())

    def make_show_version(self, base_prompt, current_prompt, command):
        """Return the system version."""
        return "TestModule version 1.0"


commands = {
    "enable": {
        "output": None,
        "new_prompt": "{base_prompt}#",
        "help": "enter exec prompt",
        "prompt": INITIAL_PROMPT,
    },
    "show clock": {
        "output": TestModule.make_show_clock,
        "help": "show current time",
        "prompt": ["{base_prompt}#", "{base_prompt}>"],
    },
    "show version": {
        "output": TestModule.make_show_version,
        "help": "show system version",
        "prompt": "{base_prompt}#",
    },
}
```

分解して説明しましょう。SIMNOS はモジュールを動的にロードできますが、モジュールには特定の構造が必要です。一方では、いくつかの定数（NAME、INITIAL_PROMPT、ENABLE_PROMPT、CONFIG_PROMPT、DEVICE_NAME）が必要で、他方ではコマンドの辞書、最後に BaseDevice を継承するクラスが必要です。これは SIMNOS がモジュールをロードするために必須です。

まず、NAME、INITIAL_PROMPT、ENABLE_PROMPT（任意）、CONFIG_PROMPT（任意）、DEVICE_NAME の属性があります。これらの属性は SIMNOS が NOS プラグインを登録するために必要です。NAME はプラグインの名前、INITIAL_PROMPT は初期シェルインジケーター、ENABLE_PROMPT は enable モードのシェルインジケーター、CONFIG_PROMPT は config モードのシェルインジケーター、DEVICE_NAME はデバイスの名前です。

次に、コマンドの辞書があります。この辞書は NOS プラグインが出力を返すことができるコマンドを含む Python 辞書です。各コマンドは "output"、"help"、"prompt" の属性を持つ辞書です。出力は文字列または文字列を返す関数にできます。ヘルプは `?` または `help` コマンドが入力された場合にユーザーに表示されるヘルプです。プロンプトはコマンドが有効なシェルインジケーターです。

最後に、BaseDevice を継承するクラスがあります。このクラスは SIMNOS がモジュールを正しくロードするために必要です。内部的には、`DEFAULT_CONFIGURATION` 属性で定義された[設定](../usage/configurations.md)ファイルのデータが辞書としてロードされる `self.configurations` 属性でモジュールを初期化します。また、`simnos/plugins/nos/platforms_py/templates/` ディレクトリ内の Jinja2 テンプレートをレンダリングできる `render(self, template: str, **kwargs) -> str` メソッドも含まれています。これらの属性を持つクラスにすることで、モジュールの標準化に役立ちます。同時に、個別の関数ではなくクラスにすることで、コマンド間で変数を共有したり、デバイスの状態を変更することもできます。例えば、デバイスの IP を変更するコマンドを作成した場合、クラス内のデバイスの状態を変更し、残りのコマンドがこの変更を考慮して新しい IP で文字列を返すようにできます。

もちろん、独自のコマンドとロジックで独自の Python モジュールを作成することもできます。正しい構造を持ち、正しくロードできることを確認してください。SIMNOS インベントリで指定すれば、SIMNOS がロードとコマンドの登録を行います。

上記のコードを確認するために、以前と同様にインベントリの YAML を作成できます:
```yaml
hosts:
    R1:
        username: user
        password: user
        port: 6000
        nos:
            plugin: path/to/my_nos.py
```

素早くテストするには、ターミナルで以下のコマンドを実行してください:
```bash
simnos -i path/to/inventory.yaml
```

## Create a NOS plugin from the Nos class
!!! warning
    Nos クラスを直接使用して NOS プラグインを開発することはメンテナンスが複雑になるため推奨されません。代わりに Python モジュールの使用を推奨します。

SIMNOS パッケージには、NOS プラグインを作成して SIMNOS インスタンスに登録するために使用できる基底クラス Nos が付属しています。結局のところ、以前と同じことを行いましたが、自分で作成する代わりに SIMNOS に任せていたのです。

インスタンス化時に必要な属性を指定して Nos クラスを使用したカスタム NOS プラグインを定義するサンプルコード:

```python
from simnos import SimNOS, Nos

nos = Nos(
    name="MySimNOSPlugin",
    initial_prompt="{base_prompt}>",
    commands={
        "terminal length 0": {"output": "", "help": "Set terminal length to 0", "prompt": "{base_prompt}>"},
        "show clock": {"output": "MySimNOSPlugin system time is 00:00:00", "help": "Display the system clock", "prompt": "{base_prompt}>"},
    },
)

inventory = {
    "hosts": {
        "router42": {
            "port": 6005,
            "nos": {"plugin": "MySimNOSPlugin"},
        },
    }
}

net = SimNOS(inventory)

net.register_nos_plugin(plugin=nos)

net.start()

try:
    while True:
        pass
except KeyboardInterrupt:
    net.stop()
```

この例では、必要な属性を持つ Nos オブジェクトが作成され、SimNOS のインスタンスに登録されます。

さらに、Nos クラスの `from_dict` メソッドと `from_file` メソッドを使用して Nos の属性を指定できます。例えば、[Python ファイルから NOS プラグインを作成する](creating_nos_plugin.md#create-nos-plugin-from-a-python-file)セクションと同等の結果を得るには、以下のコードを使用できます:

```python
nos = Nos(filename="path/to/my_nos.py")

inventory = {
    "hosts": {
        "router42": {
            "port": 6005,
            "nos": {"plugin": "MySimNOSPlugin"},
        },
    }
}
```

!!! note
    2つのコマンドが同じ名前に一致する場合、最後にロードされたコマンドが使用されます。
