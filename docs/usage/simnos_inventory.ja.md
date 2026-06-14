# インベントリ
SIMNOS はインベントリを使用してネットワークデバイスホストのセットとその設定を定義します。これはプロジェクトの重要な部分です。インベントリは `default` と `hosts` の2つのセクションを含む辞書です。`default` セクションには、SIMNOS が各ホストにデフォルトで使用するパラメータと設定が含まれます。`hosts` セクションは、ホスト名をキーとしたホスト定義の辞書です。ホストごとに定義されたパラメータは、`default` セクションで定義されたパラメータを上書きします。

SIMNOS にインベントリデータを提供する方法は2つあります:

1. YAML ファイルを使用する
2. Python 辞書を使用する

!!! warning "v2 からの移行: `platform` → `device_type`"
    SIMNOS v3 では、インベントリのキー `platform` を `device_type` にリネームしました
    (netmiko / ansible との用語統一)。これは**互換エイリアスを持たない破壊的変更**で、
    旧 `platform:` を使った v2 インベントリはロード時に拒否されます。移行方法は2つあります:

    - 旧形式をそのまま使いたい場合は **v2 に pin** してください。v2 系 (現 `main` ブランチ)
      は移行期間として保守を継続します: `pip install "simnos<3"`。
    - v3 へ移行する場合は**キーを書き換え**ます。YAML インベントリでは:

        ```bash
        sed -i 's/^\([[:space:]]*\)platform:/\1device_type:/' inventory.yaml
        ```

        Python 辞書インベントリでは、`"platform"` キーを `"device_type"` にリネームします。

    `device_type` には、プラットフォームの内部名 (`cisco_ios`)、その
    `netmiko_device_type`、または `ntc_platform` エイリアスのいずれも指定でき、
    すべて同じプラットフォームに解決されます。

## 基本構造
すべてのケースで、提供方法に関係なく、インベントリデータは以下の構造を持つ必要があります:

- **default**: SIMNOS が各ホストにデフォルトで使用するデフォルトパラメータと設定を含む辞書。
- **hosts**: ホスト名をキーとしたホスト定義の辞書。ホストごとに定義されたパラメータは、`default` セクションで定義されたパラメータを上書きします。

`hosts` セクションの提供は常に必須です。`default` セクションは任意です。提供されない場合、SIMNOS はデフォルト設定を使用します。この構造は階層的に動作するため、`hosts` セクションが `default` セクションを上書きします。

!!! warning
    デフォルトパラメータは自由に変更できますが、そのまま維持し、`hosts` セクションで上書きすることを推奨します。`default` セクションを変更する場合は、デフォルト設定にあるすべてのパラメータを提供する必要があります。

### デフォルトインベントリ
SIMNOS オブジェクトのインスタンス化時にインベントリデータが提供されない場合、SIMNOS はデフォルトのインベントリ設定にフォールバックします。現在のデフォルトは以下の通りです[^1]:
``` py linenums="1" hl_lines="16 17 18 19"
default_inventory = {
    "default": {
        "username": "user",
        "password": "user",
        "port": 6000,
        "server": {
            "plugin": "ParamikoSshServer",
            "configuration": {
                "address": "127.0.0.1",
                "timeout": 1,
            },
        },
        "shell": {"plugin": "CMDShell", "configuration": {}},
        "nos": {"plugin": "cisco_ios", "configuration": {}},
    },
    "hosts": {
        "router_cisco_ios": {"port": 6000, "device_type": "cisco_ios"},
        "router_huawei_smartax": {"port": 6001, "device_type": "huawei_smartax"},
        "router_arista_eos": {"port": 6002, "device_type": "arista_eos"},
    }
}
```

## YAML
インベントリデータを提供する最も簡単な方法です。シンプルな YAML ファイルでインベントリデータを定義できます。YAML ファイルは以下の構造を持つ必要があります:

``` yaml
default:
  username: user
  password: user
  port: 6000
  device_type: cisco_ios
```

この場合、ユーザー名 `user`、パスワード `user`、ポート `6000` の `router0` という名前のホストが作成されます。プラットフォームは `cisco_ios` になります。より多くのホストを作成したい場合は、`hosts` セクションに追加できます:

``` yaml
hosts:
    router1:
        port: 6001
        device_type: huawei_smartax
    router2:
        port: 6002
        device_type: cisco_ios
```

この場合、`router1` と `router2` の2つのホストが作成されます。`router1` はポート `6001` でプラットフォーム `huawei_smartax`、`router2` はポート `6002` でプラットフォーム `cisco_ios` になります。認証情報が `hosts` セクションで提供されていないため、SIMNOS はデフォルトの認証情報を使用します。

YAML ファイルを使用するには、SIMNOS CLI ツールを使用できます:

``` bash
simnos -i path/to/inventory.yaml
```

## Python 辞書
YAML はインベントリデータを SIMNOS に提供する最も簡単な方法ですが、Python 辞書はより柔軟で、より複雑なインベントリデータ構造を扱えます。実際のところ、Python 辞書は SIMNOS 内部でインベントリデータを処理するために使用されています。

独自の Python 辞書を使用したい場合は、SIMNOS に直接提供できます。以下のコードでは、YAML の最初のコードとまったく同じことを行っています:

``` python
from simnos import SimNOS

inventory_data = {
    "hosts": {
        "router1": {
            "username": "user",
            "password": "user",
            "port": 6000,
            "device_type": "cisco_ios",
        }
    }
}

network = SimNOS(inventory=inventory_data)
```

前と同様に、より多くのホストを作成したい場合は、`hosts` セクションに追加できます:

``` python
inventory_data = {
    "hosts": {
        "router1": {"port": 6001, "device_type": "huawei_smartax"},
        "router2": {"port": 6002, "device_type": "cisco_ios"}
    }
}
```


## その他の例
サーバーを起動するためのサンプルインベントリデータとコード:

```{ .python .annotate }
from simnos import SimNOS

fake_network = {
    "default": { # (4)
        "username": "user",
        "password": "user",
        "port": [5000, 6000],
        "server": {
            "plugin": "ParamikoSshServer",
            "configuration": {
                "ssh_key_file": "./ssh-keys/ssh_host_rsa_key",
                "timeout": 1,
                "address": "127.0.0.1",
            },
        },
        "shell": {"plugin": "CMDShell", "configuration": {}},
        "nos": {"plugin": "cisco_ios", "configuration": {}},
    },
    "hosts": {
        "R1": {
            "port": 5001,
            "username": "simnos", # (2)
            "password": "simnos",
            "server": {
                "plugin": "ParamikoSshServer",
                "configuration": {"address": "0.0.0.0"},  # (1)
            },
            "shell": {
                "plugin": "CMDShell",
                "configuration": {"intro": "Custom SSH Shell"},
            },
        },
        "R2": {},
        "core-router": {"replicas": 2, "port": [5000, 6000]}, # (3)
    },
}

network = SimNOS(inventory=fake_network)
network.start()

print(network.list_hosts())
```

1. `0.0.0.0` - すべてのインターフェースで接続を待ち受ける
2. `default` セクションで定義された `username` と `password` を上書き
3. 提供された範囲から次に利用可能なポートを使用して、`core-router1` と `core-router2` の2つのホストを起動
4. すべてのホストがデフォルトで使用する設定

上記のコードを実行する代わりに、SIMNOS CLI ツールにカスタムインベントリを提供することもできます:

```bash
simnos -i path/to/my_inventory.yaml
```

`my_inventory.yaml` には、上記の Python コードと同等の YAML 構造のインベントリを含めることができます:

```yaml
default:
  password: user
  username: user
  port: [5000, 6000]
  server:
    plugin: ParamikoSshServer
    configuration:
      address: 127.0.0.1
      ssh_key_file: ./ssh-keys/ssh_host_rsa_key
      timeout: 1
  shell:
    configuration: {}
    plugin: CMDShell
  nos:
    configuration: {}
    plugin: cisco_ios
hosts:
  R1:
    password: simnos
    port: 5001
    username: simnos
    server:
      plugin: ParamikoSshServer
      configuration:
        address: 0.0.0.0
    shell:
      plugin: CMDShell
      configuration:
        intro: Custom SSH Shell
  R2: {}
  core-router:
    replicas: 2
    port: [5000, 6000]
```

または、この簡略化されたインベントリを含めることもできます:

```yaml
default:
  password: user
  username: user
  port: [5000, 6000]
  server:
    plugin: ParamikoSshServer
    configuration:
      address: 0.0.0.0
hosts:
  router:
    replicas: 10
    device_type: cisco_ios
```

### ホストレプリカ
前述の通り、一部のホストにはレプリカフラグが設定されています。ホスト定義には `replicas` パラメータを含めて、ホストを一括定義できます。例えば、このインベントリ:

```python
inventory_data = {
    "hosts": {
        "router": {"replicas": 10, "port": [5001, 6000]}
    }
}
```

この設定により、SIMNOS はポート 5001 から 5010 をそれぞれ使用して、`router0` から `router9` までの10個のホストサーバーインスタンスを実行します。これにより、同じ設定を使用するホストのセットを簡単に定義してセットアップをスケールアウトできます。

!!! warning
    ホストのインベントリデータに `replicas` パラメータが含まれる場合、`port` パラメータはポートを割り当てる範囲を表す2つの整数のリストでなければなりません。ホストに `replicas` パラメータが含まれない場合、`port` は 1〜65535 の範囲の正の整数でなければなりません。

## SSH 秘密鍵の生成

デフォルトでは SIMNOS はパッケージに同梱された SSH 秘密鍵を使用するため、その鍵は公開されており安全ではありません。代わりに、SIMNOS はローカルで生成した SSH 鍵を使用できます。

### Linux と MacOS

ターミナルで `ssh-keygen -A` コマンドを使用して、すべての SSH 鍵を生成します。コマンドを実行すると、
RSA 鍵は `~/.ssh/id_rsa`（つまり `/home/<ユーザー名>/.ssh/id_rsa`）にあります。
上記のパスを SIMNOS サーバー設定の `ssh_key_file` 引数に指定してください。

または、`ssh-keygen -t rsa -f ssh-keys/ssh_host_rsa_key` コマンドで秘密鍵を生成することもできます。

### Windows 10

Windows キーを押して、`Manage Optional Features` と入力します。OpenSSH Client と Server がリストにあれば準備完了です。
どちらかがない場合は、「Add a feature」をクリックして `OpenSSH` を検索し、クリックしてインストールします。
次に、管理者として cmd を開きます。`ssh-keygen` コマンドを入力し、画面の指示に従います。
鍵の場所が表示されます。表示されたパスを SIMNOS サーバー設定の `ssh_key_file` 引数に指定してください。パスワードを設定した場合は、`ssh_key_file_password` パラメータにも含めてください。


## インベントリ JSON スキーマ

SIMNOS は内部で [Pydantic](https://docs.pydantic.dev/latest/concepts/models/)
モデルを使用してインベントリデータを検証し、インベントリが定義されたスキーマに
準拠しない場合は `ValidationError` を発生させます。サーバーセクションは
`ParamikoSshServer`（SSH）と `TelnetServer`（Telnet）の両方のプラグインをサポートしています。

以下のコマンドで現在の JSON スキーマを生成できます:

```python
import json
from simnos.core.pydantic_models import ModelSimnosInventory
print(json.dumps(ModelSimnosInventory.model_json_schema(), indent=4))
```

スキーマの要点:

- `server` は `ParamikoSshServerPlugin` または `TelnetServerPlugin` のいずれかを受け入れます（`anyOf`）
- `ParamikoSshServerConfig` の設定項目: `ssh_key_file`, `ssh_key_file_password`, `ssh_banner`, `timeout`, `address`, `watchdog_interval`, `authorized_keys`
- `TelnetServerConfig` の設定項目: `banner`, `timeout`, `address`, `watchdog_interval`
- すべての設定フィールドは任意で、適切なデフォルト値が設定されています

## インベントリオプション
以下のオプションは、`default` セクションまたは `hosts` セクションのいずれかで使用して、デフォルト値を上書きできます。

### トップレベルオプション

| オプション     | 絵文字         | 説明                                | 例                                               |
| --------------| ------------- | ---------------------------------- | ----------------------------------------------- |
| `username`    | :person:      | デバイスのユーザー名                  | `username: admin`                               |
| `password`    | :key:         | デバイスのパスワード                  | `password: admin`                               |
| `device_type` | :station:     | 使用するネットワークオペレーティングシステム | `device_type: cisco_ios`                           |
| `port`        | :ship:        | 接続するポート                       | `port: 6000`                                    |
| `replicas`    | :repeat:      | 作成するホスト数                     | `replicas: 10`                                  |
| `server`      | :satellite:   | サーバー設定                         | [Server options](#server-options) セクションを参照     |
| `shell`       | :shell:       | シェル設定                           | [Shell options](#shell-options) セクションを参照       |
| `nos`         | :computer:    | NOS 設定                            | [NOS options](#nos-options) セクションを参照           |
| `overlay`     | :card_index_dividers: | カスタムコマンドオーバーレイ   | [カスタムコマンドオーバーレイ](#カスタムコマンドオーバーレイデータレイヤリング) セクションを参照 |

### Server options

| オプション                 | 絵文字                     | 説明                                  | 例                                                                         |
| ------------------------- | ------------------------- | ------------------------------------- | ------------------------------------------------------------------------- |
| `plugin`                  | :electric_plug:           | 使用するサーバープラグイン               | `plugin: ParamikoSshServer`                                               |
| `configuration`           | :gear:                    | サーバー設定                           | [Server configuration options](#server-configuration-options) セクションを参照 |

### Server configuration options

SIMNOS は2つのサーバープラグインをサポートしています: **ParamikoSshServer**（SSH、デフォルト）と **TelnetServer**（Telnet）。

#### 共通オプション（SSH・Telnet 両方）

| オプション                 | 絵文字                     | 説明                                  | 例                                              |
| ------------------------- | ------------------------- | ------------------------------------- | ---------------------------------------------- |
| `timeout`                 | :hourglass:               | select のセーフティネットタイムアウト(秒) | `timeout: 1`                                   |
| `address`                 | :globe_with_meridians:    | サーバーのバインドアドレス               | `address: 127.0.0.1`                           |
| `watchdog_interval`       | :dog:                     | ウォッチドッグの間隔                    | `watchdog_interval: 1`                         |

#### ParamikoSshServer オプション

| オプション                 | 絵文字                     | 説明                                  | 例                                              |
| ------------------------- | ------------------------- | ------------------------------------- | ---------------------------------------------- |
| `ssh_key_file`            | :key:                     | SSH 秘密鍵ファイルのパス                | `ssh_key_file: /path/to/ssh_key`               |
| `ssh_key_file_password`   | :key:                     | SSH 秘密鍵のパスワード                  | `ssh_key_file_password: password`              |
| `ssh_banner`              | :scroll:                  | 表示する SSH バナー                    | `ssh_banner: "Welcome to SIMNOS SSH Server"`   |
| `authorized_keys`         | :lock:                    | authorized_keys ファイルのパス          | `authorized_keys: /path/to/authorized_keys`    |

#### TelnetServer オプション

| オプション                 | 絵文字                     | 説明                                  | 例                                              |
| ------------------------- | ------------------------- | ------------------------------------- | ---------------------------------------------- |
| `banner`                  | :scroll:                  | 表示する Telnet バナー                 | `banner: "Welcome to SIMNOS Telnet Server"`    |

Telnet サーバーを使用するには、サーバーセクションの `plugin` を `TelnetServer` に設定します:

```yaml
server:
  plugin: TelnetServer
  configuration:
    banner: "SIMNOS Telnet Server"
    address: "127.0.0.1"
```


### Shell options

| オプション                 | 絵文字                     | 説明                                  | 例                                                                       |
| ------------------------- | ------------------------- | ------------------------------------- | ----------------------------------------------------------------------- |
| `plugin`                  | :electric_plug:           | 使用するシェルプラグイン                 | `plugin: CMDShell`                                                      |
| `configuration`           | :gear:                    | シェル設定                             | 設定はプラグインに完全に依存します                                           |


### NOS options

| オプション                 | 絵文字                     | 説明                                  | 例                                                                       |
| ------------------------- | ------------------------- | ------------------------------------- | ----------------------------------------------------------------------- |
| `plugin`                  | :electric_plug:           | 使用する NOS プラグイン                 | `plugin: cisco_ios`                                                     |
| `configuration`           | :gear:                    | NOS 設定                              | 設定はプラグインに完全に依存します                                           |


## カスタムコマンドオーバーレイ（データレイヤリング）

オーバーレイを使うと、パッケージ同梱データを編集せずに、SIMNOS の隣にキャプチャ
した出力ファイルを置くだけで、**同梱コマンドの出力を差し替え**たり、**同梱に無い
コマンドを追加**したりできます。ファイルはパッケージ外に置かれるため、`pip` で
アップグレードしても消えません。

コマンドの **出力全体** が異なる場合（特定デバイス／OS バージョンのキャプチャ等）に
適しています。**値だけ**（hostname、serial など）が異なる場合は host facts という
別の仕組みになります。

### 置き場所: `sys_config.data_dir`

オーバーレイファイルは `sys_config.yaml` で指定するマシン全体共通のディレクトリ配下
に置きます:

```yaml
# sys_config.yaml
data_dir: /srv/simnos/overlays
```

`sys_config.yaml` は（優先順）`SimNOS(sys_config=...)` 引数 → 環境変数
`SIMNOS_SYS_CONFIG` → `./sys_config.yaml` → `~/.simnos/sys_config.yaml` の順で
探索されます。`SIMNOS_DATA_DIR` はファイルの `data_dir` を上書きします。

各プラットフォームは、netmiko の `device_type` 別名ではなく、**内部プラットフォーム名**
（レジストリキー = `ntc_platform` が解決する名前、例: `cisco_ios`）のサブディレクトリ
を読みます:

```
/srv/simnos/overlays/
└── cisco_ios/
    ├── show_version.txt          # `show version` の出力を差し替え
    └── show_run.txt              # `show run` を追加（同梱に無い）
```

出力ファイルは **`.txt`**（リテラルのワイヤテキスト）または **`.j2`**（jinja2
テンプレート。本リリースでは `{{ base_prompt }}` のみ参照可。host facts を必要とする
テンプレートは facts 導入までエラー）です。ファイル名の stem は `_` を空白に変換して
コマンド名に対応します: `show_version.txt` → `show version`（NTC raw キャプチャの
命名規約に追従、大文字小文字を区別）。

### 有効化: `overlay.override_commands`

ホストは、インベントリで `overlay.override_commands` を設定したときだけオーバーレイ
ディレクトリから読み込みます。3 形態あります:

```yaml
hosts:
  R1:
    device_type: cisco_ios
    overlay:
      override_commands: all                         # ディレクトリ内の .txt/.j2 を全適用
  R2:
    device_type: cisco_ios
    overlay:
      override_commands: ["show version", "show run"] # 既定名ファイルでこのコマンドだけ
  R3:
    device_type: cisco_ios
    overlay:
      override_commands:                              # ホストごとに明示ファイル選択
        show version: show_version_B.txt
```

- **`all`** — `<data_dir>/<platform>/` 内の `.txt` / `.j2` を全適用。
- **リスト** — 列挙したコマンドを既定名ファイル（`show version` →
  `show_version.txt` / `.j2`）で適用。
- **マップ** — `{コマンド: ファイル名}`。2 つのホストが同じコマンドに対して*異なる*
  キャプチャファイルを選べます（R1 → `show_version_A.txt`、R2 →
  `show_version_B.txt`）。

同梱データに存在するコマンドは **出力のみの差し替え**（出力だけ入れ替え、modes /
help / type は継承）。同梱に無いコマンドは **新規コマンド**（全モードで有効）として
追加されます。`override_commands` 未指定／空はオーバーレイ非適用（挙動不変）です。

### 注意と制限

- **有効化は loud。** `override_commands` を設定したのに `data_dir` が未設定、対象
  プラットフォームのオーバーレイディレクトリが無い、列挙／マップしたコマンドに対応
  ファイルが無い場合は起動時にエラーになります（満たせない opt-in が同梱出力に黙って
  フォールバックすることはありません）。
- **A3 プラットフォームのみ。** Python のみ（py-only）のプラットフォームは非対応。
- **マルチキャプチャコマンド。** 複数キャプチャ（variants）を持つコマンドを差し替える
  と単一のオーバーレイ出力に縮退します（INFO ログ）。
- **ホットリロード対象外。** オーバーレイディレクトリは dev ホットリロード watcher が
  見る同梱ツリー外です。変更は再接続で反映されます。
- **カタログを増やすには。** モード指定コマンドや共有したいコマンドは、同梱コマンド
  （A3 の `commands/<cmd>.yaml` + 出力ファイル）の貢献が正道です。オーバーレイは
  ローカルな出力差し替え用です。

[^1]: 現在のデフォルトを確認するには、SIMNOS の[ソースコード](https://github.com/Route-Reflector/simnos/blob/main/simnos/core/simnos.py)を参照してください。
