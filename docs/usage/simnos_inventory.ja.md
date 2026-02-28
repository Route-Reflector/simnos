# インベントリ
SIMNOS はインベントリを使用して SSH ホストのセットとその設定を定義します。これはプロジェクトの重要な部分です。インベントリは `default` と `hosts` の2つのセクションを含む辞書です。`default` セクションには、SIMNOS が各ホストにデフォルトで使用するパラメータと設定が含まれます。`hosts` セクションは、ホスト名をキーとしたホスト定義の辞書です。ホストごとに定義されたパラメータは、`default` セクションで定義されたパラメータを上書きします。

SIMNOS にインベントリデータを提供する方法は2つあります:

1. YAML ファイルを使用する
2. Python 辞書を使用する

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
        "router_cisco_ios": {"port": 6000, "platform": "cisco_ios"},
        "router_huawei_smartax": {"port": 6001, "platform": "huawei_smartax"},
        "router_arista_eos": {"port": 6002, "platform": "arista_eos"},
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
  platform: cisco_ios
```

この場合、ユーザー名 `user`、パスワード `user`、ポート `6000` の `router0` という名前のホストが作成されます。プラットフォームは `cisco_ios` になります。より多くのホストを作成したい場合は、`hosts` セクションに追加できます:

``` yaml
hosts:
    router1:
        port: 6001
        platform: huawei_smartax
    router2:
        port: 6002
        platform: cisco_ios
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
            "platform": "cisco_ios",
        }
    }
}

network = SimNOS(inventory=inventory_data)
```

前と同様に、より多くのホストを作成したい場合は、`hosts` セクションに追加できます:

``` python
inventory_data = {
    "hosts": {
        "router1": {"port": 6001, "platform": "huawei_smartax"},
        "router2": {"port": 6002, "platform": "cisco_ios"}
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
    platform: cisco_ios
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
準拠しない場合は `ValidationError` を発生させます。

インベントリは Pydantic モデルでモデリングされていますが、同等の JSON スキーマは
以下のようになります:

```json
{
    "title": "ModelSimnosInventory",
    "description": "SIMNOS inventory data schema",
    "type": "object",
    "properties": {
        "default": {
            "$ref": "#/definitions/InventoryDefaultSection"
        },
        "hosts": {
            "title": "Hosts",
            "type": "object",
            "additionalProperties": {
                "$ref": "#/definitions/HostConfig"
            }
        }
    },
    "required": [
        "hosts"
    ],
    "additionalProperties": false,
    "definitions": {
        "ParamikoSshServerConfig": {
            "title": "ParamikoSshServerConfig",
            "type": "object",
            "properties": {
                "ssh_key_file": {
                    "title": "Ssh Key File",
                    "type": "string"
                },
                "ssh_key_file_password": {
                    "title": "Ssh Key File Password",
                    "type": "string"
                },
                "ssh_banner": {
                    "title": "Ssh Banner",
                    "default": "SIMNOS Paramiko SSH Server",
                    "type": "string"
                },
                "timeout": {
                    "title": "Timeout",
                    "default": 1,
                    "type": "integer"
                },
                "address": {
                    "title": "Address",
                    "anyOf": [
                        {
                            "enum": [
                                "localhost"
                            ],
                            "type": "string"
                        },
                        {
                            "type": "string",
                            "format": "ipvanyaddress"
                        }
                    ]
                },
                "watchdog_interval": {
                    "title": "Watchdog Interval",
                    "default": 1,
                    "type": "integer"
                }
            }
        },
        "ParamikoSshServerPlugin": {
            "title": "ParamikoSshServerPlugin",
            "type": "object",
            "properties": {
                "plugin": {
                    "title": "Plugin",
                    "enum": [
                        "ParamikoSshServer"
                    ],
                    "type": "string"
                },
                "configuration": {
                    "$ref": "#/definitions/ParamikoSshServerConfig"
                }
            },
            "required": [
                "plugin"
            ]
        },
        "CMDShellConfig": {
            "title": "CMDShellConfig",
            "type": "object",
            "properties": {
                "intro": {
                    "title": "Intro",
                    "default": "Custom SSH Shell",
                    "type": "string"
                },
                "ruler": {
                    "title": "Ruler",
                    "default": "",
                    "type": "string"
                },
                "completekey": {
                    "title": "Completekey",
                    "default": "tab",
                    "type": "string"
                },
                "newline": {
                    "title": "Newline",
                    "default": "\r\n",
                    "type": "string"
                }
            }
        },
        "CMDShellPlugin": {
            "title": "CMDShellPlugin",
            "type": "object",
            "properties": {
                "plugin": {
                    "title": "Plugin",
                    "enum": [
                        "CMDShell"
                    ],
                    "type": "string"
                },
                "configuration": {
                    "$ref": "#/definitions/CMDShellConfig"
                }
            },
            "required": [
                "plugin"
            ]
        },
        "NosPlugin": {
            "title": "NosPlugin",
            "type": "object",
            "properties": {
                "plugin": {
                    "title": "Plugin",
                    "type": "string"
                },
                "configuration": {
                    "title": "Configuration",
                    "type": "object"
                }
            },
            "required": [
                "plugin"
            ]
        },
        "InventoryDefaultSection": {
            "title": "InventoryDefaultSection",
            "type": "object",
            "properties": {
                "username": {
                    "title": "Username",
                    "type": "string"
                },
                "password": {
                    "title": "Password",
                    "type": "string"
                },
                "port": {
                    "title": "Port",
                    "anyOf": [
                        {
                            "type": "integer",
                            "exclusiveMinimum": 0,
                            "maximum": 65535
                        },
                        {
                            "type": "array",
                            "items": {
                                "type": "integer",
                                "exclusiveMinimum": 0,
                                "maximum": 65535
                            },
                            "minItems": 2,
                            "maxItems": 2,
                            "uniqueItems": true
                        }
                    ]
                },
                "server": {
                    "$ref": "#/definitions/ParamikoSshServerPlugin"
                },
                "shell": {
                    "$ref": "#/definitions/CMDShellPlugin"
                },
                "nos": {
                    "$ref": "#/definitions/NosPlugin"
                }
            }
        },
        "HostConfig": {
            "title": "HostConfig",
            "type": "object",
            "properties": {
                "username": {
                    "title": "Username",
                    "type": "string"
                },
                "password": {
                    "title": "Password",
                    "type": "string"
                },
                "port": {
                    "title": "Port",
                    "anyOf": [
                        {
                            "type": "integer",
                            "exclusiveMinimum": 0,
                            "maximum": 65535
                        },
                        {
                            "type": "array",
                            "items": {
                                "type": "integer",
                                "exclusiveMinimum": 0,
                                "maximum": 65535
                            },
                            "minItems": 2,
                            "maxItems": 2,
                            "uniqueItems": true
                        }
                    ]
                },
                "server": {
                    "$ref": "#/definitions/ParamikoSshServerPlugin"
                },
                "shell": {
                    "$ref": "#/definitions/CMDShellPlugin"
                },
                "nos": {
                    "$ref": "#/definitions/NosPlugin"
                },
                "replicas": {
                    "title": "Replicas",
                    "exclusiveMinimum": 0,
                    "type": "integer"
                }
            }
        }
    }
}
```

## インベントリオプション
以下のオプションは、`default` セクションまたは `hosts` セクションのいずれかで使用して、デフォルト値を上書きできます。

### トップレベルオプション

| オプション     | 絵文字         | 説明                                | 例                                               |
| --------------| ------------- | ---------------------------------- | ----------------------------------------------- |
| `username`    | :person:      | デバイスのユーザー名                  | `username: admin`                               |
| `password`    | :key:         | デバイスのパスワード                  | `password: admin`                               |
| `platform`    | :station:     | 使用するネットワークオペレーティングシステム | `platform: cisco_ios`                           |
| `port`        | :ship:        | 接続するポート                       | `port: 6000`                                    |
| `replicas`    | :repeat:      | 作成するホスト数                     | `replicas: 10`                                  |
| `server`      | :satellite:   | サーバー設定                         | [Server options](#server-options) セクションを参照     |
| `shell`       | :shell:       | シェル設定                           | [Shell options](#shell-options) セクションを参照       |
| `nos`         | :computer:    | NOS 設定                            | [NOS options](#nos-options) セクションを参照           |

### Server options

| オプション                 | 絵文字                     | 説明                                  | 例                                                                         |
| ------------------------- | ------------------------- | ------------------------------------- | ------------------------------------------------------------------------- |
| `plugin`                  | :electric_plug:           | 使用するサーバープラグイン               | `plugin: ParamikoSshServer`                                               |
| `configuration`           | :gear:                    | サーバー設定                           | [Server configuration options](#server-configuration-options) セクションを参照 |

### Server configuration options

| オプション                 | 絵文字                     | 説明                                  | 例                                              |
| ------------------------- | ------------------------- | ------------------------------------- | ---------------------------------------------- |
| `ssh_key_file`            | :key:                     | SSH 秘密鍵ファイルのパス                | `ssh_key_file: /path/to/ssh_key`               |
| `ssh_key_file_password`   | :key:                     | SSH 秘密鍵のパスワード                  | `ssh_key_file_password: password`              |
| `ssh_banner`              | :scroll:                  | 表示する SSH バナー                    | `ssh_banner: "Welcome to SIMNOS SSH Server"`   |
| `timeout`                 | :hourglass:               | サーバーのタイムアウト                  | `timeout: 1`                                   |
| `address`                 | :globe_with_meridians:    | サーバーのバインドアドレス               | `address: 127.0.0.1`                           |
| `watchdog_interval`       | :dog:                     | ウォッチドッグの間隔                    | `watchdog_interval: 1`                         |


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


[^1]: 現在のデフォルトを確認するには、SIMNOS の[ソースコード](https://github.com/Route-Reflector/simnos/blob/main/simnos/core/simnos.py)を参照してください。
