# スクリプト開発

通常、ネットワーク自動化タスクを開発する際は、SSH 経由でデバイスに対してスクリプトを実行します。開発目的では、フェイクデバイスを使うのが良いアプローチです。こうすることで、実機を壊すリスクなしにスクリプトをテストできます。ここで SIMNOS の出番です。実ネットワーク上に実機をセットアップする代わりに、ローカルで簡単にフェイクプラットフォームを作成できます。

## YAML を使う方法

例として、Huawei SmartAX を実行するフェイクデバイスを作成してみましょう。まず、以下の内容の YAML ファイルを作成します:
```yaml
hosts:
    myRouter:
        username: admin
        password: admin
        platform: huawei_smartax
        port: 6000
```
このファイルを `inventory.yaml` 📕 と名付けることができますが、他の名前でも構いません。すべての YAML ファイルで、
デバイスは `hosts:` の下に記述する必要があります。*hosts* の中には、各デバイスが固有のポートを持つ限り、
好きなだけデバイスを追加できます。デバイスを追加するには、任意の名前を付けるだけです。

各デバイスには `username`、`password`、`port`、`platform` を設定できます。利用可能なすべてのプラットフォームは[こちら](../platforms/index.md)で確認できます。この例ではプラットフォームに `huawei_smartax` を選択し、認証情報はユーザー名 `admin`、パスワード `admin` としています。

次に、以下の内容で Python スクリプトを作成します:
```python
from simnos import SimNOS
network_os = SimNOS(inventory='inventory.yaml')
network_os.start()

try:
    while True:
        pass
except KeyboardInterrupt:
    network_os.stop()
```
このスクリプトは `inventory.yaml` で定義したフェイクデバイスを起動します。`Ctrl+C` を押すまで実行し続けます。押すとすべてのプロセスが停止します。使用しているすべてのスレッドを閉じる必要があるため、通常は数秒かかります。

Python :snake: スクリプトを実行するには、以下のコマンドを使用します:
```bash
python main.py
```

このスクリプトは Huawei SmartAX を実行するフェイクデバイスを作成します。`ssh` などの SSH クライアントで接続できます:
```bash
# Huawei SmartAX に接続
ssh -p 6000 admin@localhost
```

以下は試せるコマンドです:

-  `display version`
-  `display board`
-  `display sysman service state`

**以上です！** 💅 これで、Huawei SmartAX をエミュレートするフェイクネットワークデバイスを作成し、SSH で接続できるようになりました。

さらに試してみたい場合は、他のプラットフォームを試したり、認証情報やポートを変更して慣れることをお勧めします。

## dict を使う方法
`.yaml` ファイルの代わりに辞書を使用することも可能です。プログラム的に変数を定義したい場合に便利です。前述の方法とほぼ同様ですが、この場合は2つのファイルではなく1つのファイルにまとめます。

CLI でプラットフォームを指定できるようにしたい場合を想像してください。以下のスクリプトは同じことを行いますが、`platform` を指定できます:

```python
import argparse
from simnos import SimNOS

parser = argparse.ArgumentParser(
    description="Create a fake device specifying the platform."
    )

parser.add_argument(
    "platform",
    type=str,
    help="fake device network operating system"
    )

args = parser.parse_args()

inventory = {
    "hosts": {
        "mySwitch": {
            "username": "admin",
            "password": "admin",
            "platform": args.platform,
            "port": 6000
        }
    }
}

net = SimNOS(inventory=inventory)
```

例えば、以下のコマンドで実行できます:
```bash
python main.py huawei_smartax
```

**以上です！** 前回と同じ方法でアクセスできますが、プラットフォームを毎回指定できます。例えば Cisco IOS の場合も同様です:

```bash
python main.py cisco_ios
```

これで Cisco IOS デバイスを作成できます。

## Netmiko と NTC-Templates を使ったサンプル
以下のスクリプトは、[Netmiko](https://github.com/ktbyers/netmiko) と [NTC-Templates](https://github.com/networktocode/ntc-templates) ライブラリを使用して ONT のシリアル番号を取得します。フェイクデバイスがこのケースでは実機と同様に動作することを示すのが目的です。

前述の方法でプラットフォーム `huawei_smartax` のフェイクデバイスを起動し、以下のコードを使用します:
```python
from netmiko import ConnectHandler
from ntc_templates.parse import parse_output

credentials = {
    "host": "localhost",
    "username": "admin",
    "password": "admin",
    "port": 6000,
    "device_type": "huawei_smartax"
}

serial_number: str = ''
with ConnectHandler(**credentials) as conn:
    output = conn.send_command("display ont info summary ont")
    parsed_output = parse_output(
        platform="huawei_smartax",
        command="display ont info summary 0/1/0",
        data=output
    )
    serial_number = parsed_output[0]['serial_number']

print(f"Serial number of the first ONT: {serial_number}")
```
