開発を容易にするために、いくつかの小さなタスクが開発されています。自由に追加してください。これらのタスクはすべて `tasks.py` に記載されています。タスクを実行するには、以下のコマンドを使用してください:
```bash
invoke <task_name>
```

利用可能なタスクは以下の通りです:

-  `gen-docs-platform-commands`: プラットフォームのドキュメントを自動生成します。元々はプロジェクトの最初のバージョンですべてのコマンドをドキュメント化するために作られましたが、任意のプラットフォームのドキュメント化に使用できます。また `mkdocs.yml` の Platforms nav セクションもプラットフォーム一覧から再生成するため、新しいプラットフォームのドキュメントページが nav から辿れないまま公開されることはありません。

-  `netmiko-check`: Netmiko はネットワーク自動化のコアライブラリです。SIMNOS はそのテストライブラリとしての役割を意図しており、利用可能なプラットフォームが Netmiko と互換性があることを確認することが重要です。このタスクは、プラットフォームと Netmiko の互換性をテストするために使用できるスクリプトを生成します。成功すると `Everything is OK! ✅` と表示されます。

-  `lint-platform-data`: A3 platform データディレクトリを authoring 規約 (#264) に照らして検査します: 出力ファイル (`.txt` / `.j2`) は UTF-8・LF のみ・末尾改行必須、各出力ファイルはちょうど 1 つの command yaml から参照される (orphan / 共有 / 欠落参照を検出)、literal channel は `.txt`・`output_template` は `.j2`、`.yml` の混入を検出。さらに authoring ratchet (#276) も gate します: 新規プラットフォームは `_default_` command を定義、自動生成 stub help の新規追加禁止、heritage 文言の残存禁止。既存の drift は `platform_data_lint_baseline.yaml` (repo root) に凍結済みで縮小しかせず、違反の修正には同じ PR での baseline エントリ削除が必要です。加えて非ブロッキングの warning も出力します (ファイル名が sanitize 済コマンド名と不一致、`type: ntc` なのに `source` ブロック欠落)。CI と pre-commit hook で実行されます。
