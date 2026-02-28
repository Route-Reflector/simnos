# Docker での実行

SIMNOS をコンテナで実行することで、多くのインテグレーションユースケースが可能になります。

## Docker での実行

ビルド済みの SIMNOS Docker コンテナが
[DockerHUB リポジトリ](https://hub.docker.com/r/simnos/simnos)に公開されています。


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

インベントリファイルは docker-compose ファイルで `volume` として `simnos` コンテナにバインドされているため、
`inventory.yaml` ファイルへの変更はコンテナ内で実行されている `simnos` プロセスに反映されます。
