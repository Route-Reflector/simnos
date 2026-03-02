# 基本的な使い方
SIMNOS には組み込みのデフォルトホストがあり、`inventory` が指定されない場合に使用されます。その場合、以下のデバイスが起動します:

- **router_cisco_ios**: ユーザー名 `user`、パスワード `user`、ポート 6000 のデバイス。プラットフォームは `cisco_ios`。
- **router_huawei_smartax**: ユーザー名 `user`、パスワード `user`、ポート 6001 のデバイス。プラットフォームは `huawei_smartax`。
- **router_arista_eos**: ユーザー名 `user`、パスワード `user`、ポート 6002 のデバイス。プラットフォームは `arista_eos`。

すべてのケースで、フェイクデバイスは localhost（127.0.0.1）上で実行されます。起動するには以下のコードを使用してください:

```python
from simnos import SimNOS

network = SimNOS()
network.start()
```

デフォルトのユーザー名 `user` とパスワード `user` で SSH 接続を開始します:

```bash
ssh -p 6000 user@localhost # cisco_ios
ssh -p 6001 user@localhost # huawei_smartax
```

上記のコードを実行する代わりに、引数なしで SIMNOS CLI を実行することもできます:

```bash
simnos
```

!!! warning "セキュリティに関する注意"
    SIMNOS は**テストおよび開発専用**です。以下のデフォルト設定に注意してください:

    - **デフォルト認証情報**: 組み込みインベントリは `user`/`user` を使用します。ローカル以外のデプロイでは、インベントリでこれらを変更してください。
    - **デフォルト SSH ホスト鍵**: カスタム鍵が指定されていない場合、SIMNOS は起動時に RSA ホスト鍵を自動生成します。同一プロセス内の全ホストで同じ鍵が共有されます。この鍵は再起動後に保持されないため、SSH クライアントがホスト鍵の警告を表示することがあります。ローカル以外の使用では、サーバー設定で `ssh_key_file` を指定してカスタム鍵を提供してください。
    - **バインドアドレス**: デフォルトで SIMNOS は `127.0.0.1`（localhost のみ）にバインドします。Docker/WSL 環境では `0.0.0.0`（全インターフェース）にバインドされ、サービスがネットワークに公開される場合があります。
