# 自動テスト

最も興味深いユースケースの一つが自動テストです。このサンプルでは、SIMNOS がライブラリのテストを簡単に行えることを示します。ユニットテストなど他のテストを置き換えるものではなく、軽量なフェイクプラットフォームを提供することでそれらを補完するものです。まずスクリプトを作成し、その後テストを書きますが、逆の順序（TDD）で行うことを推奨します。

## スクリプト
以下のスクリプトは、前のサンプル[スクリプト開発](developing_scripts.md)で説明したものと似ています。先にそのサンプルを実施することを推奨します。簡単に言うと、Huawei SmartAX デバイスに接続し、ポート上のすべての ONT の値を取得し、最初の ONT のシリアル番号を探します。

```python
from netmiko import ConnectHandler
from ntc_templates.parse import parse_output

credentials = {
    "host": "192.168.0.1",
    "username": "admin",
    "password": "admin",
    "port": 22,
    "device_type": "huawei_smartax"
}


def get_serial_number(sn_index: int = 0) -> str:
    """
    This functions connects to the device and get
    the ONT in the indicated index.
    """
    ont_serial_number: str = ''
    with ConnectHandler(**credentials) as conn:
        output = conn.send_command("display ont info summary ont")
        parsed_output = parse_output(
            platform="huawei_smartax",
            command="display ont info summary 0/1/0",
            data=output
        )
        ont_serial_number = parsed_output[0]['serial_number']
    return ont_serial_number

if __name__ == "__main__":
    serial_number_first_ont = get_serial_number(0)
    print(f"Serial number of the first ONT: {serial_number_first_ont}")
```

!!! note
    これらの認証情報は実際のものではないことに注意してください。

上記のファイルは `main.py` と名付けます。

## テスト
ここまでで、まだテストされていないスクリプトがあります。すでにそのまま使えますが、事前に何らかのテストを行うことを推奨します。さらに今は SIMNOS があるので、この素晴らしいライブラリを活用できます 😝。

テストを書いて、説明をしましょう:
```python
from unittest.mock import patch
from simnos import SimNOS
import main

inventory = {
    "hosts": {
        "R1": {
            "username": "user",
            "password": "user",
            "port": 6000,
            "platform": "huawei_smartax",
        }
    }
}

fake_credentials = {
    "host": "localhost",
    "username": "user",
    "password": "user",
    "port": 6000,
    "device_type": "huawei_smartax",
}

@patch('main.credentials', fake_credentials)
def test_get_serial_number():
    """
    It tests that the function get_serial_number() gets
    the first ONT serial number correctly.
    """
    net = SimNOS(inventory=inventory)
    net.start()
    result = main.get_serial_number(0)
    assert result == "1234567890ABCDEF"

    net.stop()

if __name__ == "__main__":
    test_get_serial_number()
    print("All test passed ✅")
```
このテストは以下の手順を実行します:
1. フェイクデバイスを作成して起動する
2. テスト対象のアクションを実行する
3. フェイクデバイスを停止する

自動テストの場合、常に同じ構造に従う必要があります。この start → test → stop の流れは必須です。`net.stop()` を呼び出さないと、基盤のスレッドが新しい接続を待ち続けるため、テストスイートがハングアップします。

!!! tip
    よりクリーンなアプローチとして、`@simnos` デコレータや `with` 文を使用することもできます。
    以下のセクションを参照してください。

## `with` を使った実装
前の例は `with` 文を使って実装できます。これはより Python らしい方法であり、使用を推奨します。前の例は次のように書き換えられます:

```python
from simnos import SimNOS

with SimNOS(inventory=inventory) as net:
    result = main.get_serial_number(0)
    assert result == "1234567890ABCDEF"
```

## デコレータを使った実装
!!! new
    バージョン v1.0.2 で実装

前の例はデコレータを使って実装することもできます。これはさらに Python らしい方法です。個人的にはお気に入りの方法です。前の例は次のように書き換えられます:

```python
from simnos import simnos

@simnos(platform="huawei_smartax")
def test_get_serial_number():
    """
    It tests that the function get_serial_number() gets
    the first ONT serial number correctly.
    """
    result = main.get_serial_number(0)
    assert result == "1234567890ABCDEF"
```

デコレータはフェイクデバイスの起動と停止を処理し、開始前にインベントリを作成し、テスト後に停止します。このデコレータは単一プラットフォームでのテストに最適です。しかし、カスタムインベントリを使って複数のプラットフォームでも使用できます。

```python
from simnos import simnos

@simnos(inventory=inventory)
def test_get_serial_number():
    """
    It tests that the function get_serial_number() gets
    the first ONT serial number correctly.
    """
    result = main.get_serial_number(0)
    assert result == "1234567890ABCDEF"
```

最後に、フェイクデバイスにアクセスしたい場合は、デコレータに `return_instance` パラメータを追加できます。これにより、テストにフェイクデバイスのインスタンスが返されます。フェイクデバイスに対して追加のテストを行ったり、直接接続したい場合に便利です。

```python
from simnos import simnos

@simnos(platform="huawei_smartax", return_instance=True)
def get_ports_used_in_decorator():
    """ We want to see the ports of the fake device """
    host_ports = [host.port for host in net.hosts.values()]
    print(host_ports)
```

この場合、以下の結果が得られます:
```bash
>> [60231]
```

!!! note
    デフォルトでは `return_instance` は `False` です。使用したい場合は `True` に設定する必要があります。

!!! note
    platform パラメータを使用すると、ランダムなポートが割り当てられます。これはテストが他のシステムに影響しないための意図的な仕様です。特定のポートを使用したい場合は、インベントリで指定できます。
