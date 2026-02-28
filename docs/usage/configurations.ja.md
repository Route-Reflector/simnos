# 設定

SIMNOS の最も便利な機能の一つは、起動前にデバイスを設定できることです。これは、例えばインターフェースの IP アドレスを指定したり、ポートで許可される VLAN を指定する場合に便利です。デフォルトでいくつかの値が事前定義されていますが、ニーズに合わせて変更することもできます。

設定ファイルはブランドやデバイスごとに高度にカスタマイズされているため、自由に設定できますが、変数の最終値のみを変更することを推奨します。独自の設定ファイルを使用するには、SIMNOS 設定ファイルでファイルのパスを指定するだけです。以下は例です:

```yaml
hosts:
  R1:
    username: user
    password: user
    port: 6000
    platform: cisco_ios
    configuration_file: my_configurations/cisco_ios.yaml.j2
```

この場合、設定ファイルは `my_configurations` フォルダにあり、`cisco_ios.yaml.j2` という名前です。

現在、SIMNOS は以下のプラットフォームで設定を受け付けます:

- [cisco_ios](https://github.com/Route-Reflector/simnos/tree/main/simnos/plugins/nos/platforms_py/configurations/cisco_ios.yaml.j2)
- [huawei_smartax](https://github.com/Route-Reflector/simnos/tree/main/simnos/plugins/nos/platforms_py/configurations/huawei_smartax.yaml.j2)
- [arista_eos](https://github.com/Route-Reflector/simnos/tree/main/simnos/plugins/nos/platforms_py/configurations/arista_eos.yaml.j2)
