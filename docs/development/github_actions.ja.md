
# Github Actions
常に備えておきたい非常に便利な機能は、複数のプラットフォームで同時にコードをテストする完全自動化されたプラットフォームです。ここでは Github Actions を使用しています。設定は `.github/workflows` フォルダに格納されています。

## 現在のワークフロー
現在、2つのワークフローがあります:

- `docs.yml`: 更新されたドキュメントを `gh-pages` ブランチに自動デプロイします。
- `main.yml`: コードの正確性を確認します。複数のプラットフォーム（Linux、MacOS、Windows）でフルテストスイートを実行し、コードスタイルもチェックします。

## ワークフローのローカルテスト
ワークフローを変更する場合、1000回のプルリクエストやコミットを行う代わりに、ワークフローをローカルで実行することが可能です（推奨されます）。そのためには `act` パッケージをインストールする必要があります。詳細は[公式ドキュメント](https://nektosact.com/)を参照してください。`act` コマンドでワークフローをローカルで実行できます。それだけです！

!!! tip
    完全なコマンドは: **`act -P ubuntu-latest=ghcr.io/catthehacker/ubuntu:act-latest`**

!!! failure
    現在、デフォルトのランナーは動作しません。`ghcr.io/catthehacker/ubuntu:act-latest` の使用が推奨されます。そのため完全なコマンドは `act -P ubuntu-latest=ghcr.io/catthehacker/ubuntu:act-latest` です。この場合、イメージはかなり大きくなりますが...動作します。また、こちらの [Github のお知らせ](https://github.blog/changelog/2024-03-07-github-actions-all-actions-will-run-on-node20-instead-of-node16-by-default/)も参照してください。
