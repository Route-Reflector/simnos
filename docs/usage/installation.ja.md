# インストール

## PyPi（推奨）
SIMNOS は PyPi に公開されています。`pip` を使ってインストールするには、以下のコマンドを実行してください:
```bash
python3 -m pip install simnos
```

## Git
以下の方法は、開発を行う場合を除き推奨しません。開発目的の場合は、すべての機能が揃っており開発プロセスがより簡単になる `uv` 方式を推奨します。

### pip を使う方法
この方法でインストールする前に、[Git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git) をダウンロードしてインストールする必要があります。`git` が既にインストールされている場合は、以下のコマンドを実行してください:
```bash
python3 -m pip install git+https://github.com/Route-Reflector/simnos
```

## uv を使う方法（開発向け推奨）
SIMNOS は依存関係と仮想環境の管理に [uv](https://docs.astral.sh/uv/) を使用しています。以下の手順に従って uv で SIMNOS をインストールしてください:

```{ .bash .annotate }
curl -LsSf https://astral.sh/uv/install.sh | sh      # (1)
git clone https://github.com/Route-Reflector/simnos   # (2)
cd simnos                                              # (3)
uv sync                                                # (4)
uv run pre-commit install                              # (5)
```

1.  uv をインストール
2.  GitHub の main ブランチから SIMNOS リポジトリをクローン
3.  simnos フォルダに移動
4.  uv を実行して仮想環境を作成し、依存関係をインストール
5.  git commit 時の自動コードチェック用に pre-commit フックを有効化
