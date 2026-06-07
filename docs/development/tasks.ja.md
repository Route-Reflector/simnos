開発を容易にするために、いくつかの小さなタスクが開発されています。自由に追加してください。これらのタスクはすべて `tasks.py` に記載されています。タスクを実行するには、以下のコマンドを使用してください:
```bash
invoke <task_name>
```

利用可能なタスクは以下の通りです:

-  `gen-docs-platform-commands`: プラットフォームのドキュメントを自動生成します。元々はプロジェクトの最初のバージョンですべてのコマンドをドキュメント化するために作られましたが、任意のプラットフォームのドキュメント化に使用できます。また `mkdocs.yml` の Platforms nav セクションもプラットフォーム一覧から再生成するため、新しいプラットフォームのドキュメントページが nav から辿れないまま公開されることはありません。

-  `netmiko-check`: Netmiko はネットワーク自動化のコアライブラリです。SIMNOS はそのテストライブラリとしての役割を意図しており、利用可能なプラットフォームが Netmiko と互換性があることを確認することが重要です。このタスクは、プラットフォームと Netmiko の互換性をテストするために使用できるスクリプトを生成します。成功すると `Everything is OK! ✅` と表示されます。

-  `lint-platform-yaml`: platform YAML を authoring 規約 (#244) に照らして検査します: 新規 platform の `_default_` 必須、auto-generated stub help の新規追加禁止、heritage 文言の残存禁止。既存の drift は `platform_yaml_lint_baseline.yaml` (repo root) に凍結されており、baseline は縮小のみ — 違反を直したら同じ PR で baseline の entry も削除する必要があります。CI と pre-commit hook で実行されます。
