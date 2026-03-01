# Docker での実行

SIMNOS をコンテナで実行することで、多くのインテグレーションユースケースが可能になります。

## Docker での実行

ビルド済みの SIMNOS Docker コンテナが
[GitHub Container Registry](https://github.com/Route-Reflector/simnos/pkgs/container/simnos) に公開されています。

```{ .bash .annotate }
docker pull ghcr.io/route-reflector/simnos:latest   # (1)
docker run -d -p 12723:6001 -p 12724:6002 \
  --name simnos ghcr.io/route-reflector/simnos       # (2)
ssh localhost -l user -p 12723                        # (3)
```

1. GHCR から最新の SIMNOS イメージを取得
2. ポートマッピングを指定してデタッチドモードでコンテナを実行
3. マッピングされたポート経由で SIMNOS ルーターに SSH 接続

カスタムインベントリを使用するには、ボリュームとしてマウントします:

```bash
docker run -d -p 12723:6001 -p 12724:6002 \
  -v /path/to/inventory.yaml:/app/docker/inventory.yaml \
  --name simnos ghcr.io/route-reflector/simnos
```

!!! warning
    デフォルトのインベントリは `0.0.0.0` にバインドし、認証情報は `user:user` です。
    これはローカルテスト専用です。共有環境や本番環境では、
    適切な認証情報を設定したカスタムインベントリを使用してください。

## Docker-Compose でのビルドと実行

SIMNOS の GitHub リポジトリには、コンテナ内で SIMNOS をビルド・起動するための
`docker-compose` ファイルと `Docker` ファイルが含まれています。
[Docker](https://docs.docker.com/engine/install/)、
[Docker-Compose](https://docs.docker.com/compose/install/)、
[GIT](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git) がシステムにインストール済みであることを前提に:

```{ .bash .annotate }
git clone https://github.com/Route-Reflector/simnos.git   # (1)
cd simnos/docker/                                          # (2)
docker-compose up -d                                       # (3)
ssh localhost -l user -p 12723                              # (4)
```

1. GitHub から SIMNOS リポジトリをクローン
2. simnos の docker ディレクトリに移動
3. デタッチド（`-d`）モードでコンテナをビルド・起動
4. マッピングされたポート経由で SIMNOS ルーターに SSH 接続

`docker-compose.yaml` はコンテナポートをホストポートにマッピングします
（例: `12723:6001`, `12724:6002`）。`localhost` のマッピングされたポートに接続してください。

`docker/` フォルダにはコンテナ内で SIMNOS を起動するために使用される
`inventory.yaml` ファイルが含まれています:

```yaml
default:
  server:
    plugin: "ParamikoSshServer"
    configuration:
      address: "0.0.0.0"
      timeout: 1

hosts:
  router:
    username: user
    password: user
    port: [6001, 6002]
    replicas: 2
    platform: cisco_ios
```

コンテナを実行する前にインベントリ設定を調整するか、インベントリの内容を更新して
`simnos` コンテナを再起動して変更を適用してください — `docker restart simnos`
