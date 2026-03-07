# 作業ログ: 20260307_205610_claude_issue-69-71-cmdshell-readline-crash

## メタ情報
- 🗓 作業開始: 2026-03-07 20:56:10(JST)
- 🏁 作業終了: 2026-03-07 21:58:43(JST)
- ✍️ 作成者: 🐙claude
- 🧑‍💻 作業者: 🐙claude
- 👀 レビュー/コメント: 🦊codex(1st), 🐳gemini(1st)
- 🎯 対象: Issue #69 / Issue #71 / Issue #72
- 📦 対象プロジェクト: simnos

## 目的(Goal)
- #71: TapIO.readline() が None を返し cmd.Cmd がクラッシュする問題を修正
- #69: yamaha の output: true がシェル終了シグナルと衝突する問題を修正
- #72: netmiko init 互換テストを追加

## 計画(Plan)
- [x] Phase 1: #71 修正（TapIO.readline() バッファ drain + CMDShell.do_EOF 追加 + tap スレッド調整）
- [x] Phase 2: #69 修正（yamaha.yaml の output: true → output: ""）
- [x] Phase 3: #72 テスト追加（netmiko init 互換テスト + shutdown/EOF 回帰テスト）
- [x] Phase 4: リファクタリング・lint 修正・全テスト実行
- [x] Phase 5: 最終リファクタリング（コードクリーンアップ）
- [x] Phase 6: コードレビュー対応（codex [SHOULD FIX] 1件）

## 参照元
- 設計ドキュメント: design/20260307_131833_claude_issue-69-70-71-72-investigation.md
- ブランチ: fix/issue-69-71-cmdshell-readline-crash

## 変更内容(Changes)

### Phase 1: #71 TapIO.readline() クラッシュ + EOF ハンドリング
- `simnos/plugins/servers/tap_io.py` — readline() が run_srv クリア後にバッファを drain して `""` を返すように修正（`None` → `TypeError` を解消）
- `simnos/plugins/shell/cmd_shell.py` — `do_EOF()` メソッド追加（`""` → `line='EOF'` → `do_EOF` → `return True` で cmdloop 正常終了）
- `simnos/plugins/servers/ssh_server_paramiko.py` — `shell_to_channel_tap` の EOF 判定を `if line is None:` → `if not line:` に変更
- `simnos/plugins/servers/telnet_server.py` — `shell_to_socket_tap` の EOF 判定を `if line is None:` → `if not line:` に変更 + `run_srv` 再チェック追加

### Phase 2: #69 yamaha output: true 誤解釈
- `simnos/plugins/nos/platforms_yaml/yamaha.yaml` — `console lines infinity` の `output: true` → `output: ""` に変更（YAML boolean が Python `True` に変換され、シェル終了シグナルと衝突する問題を修正）

### Phase 3: #72 テスト追加
- `tests/core/test_netmiko_init_compat.py` — 新規作成（171 行）
  - `TestNetmikoInitCompat`: 全プラットフォームの netmiko init 互換テスト（"Unknown command" 検出）
  - `TestShutdownEOF`: サーバー停止時の EOF ハンドリング回帰テスト（スレッドリーク検証）
  - `INIT_UNKNOWN_CMD_ALLOWED`: 既知の非互換プラットフォーム除外リスト（8 プラットフォーム）
- `tests/plugins/test_ssh_server_paramiko.py` — EOF 期待値を `None` → `""` に更新
- `tests/plugins/test_cmd_shell.py` — `test_do_eof` テスト追加

### Phase 4: lint 修正
- `simnos/plugins/servers/telnet_server.py` — `try/except TimeoutError: pass` → `contextlib.suppress(TimeoutError)` (SIM105)
- `tests/plugins/test_ssh_server_paramiko.py` — `# noqa: S507` 追加（既存の AutoAddPolicy 警告抑制）

### Phase 5: 最終リファクタリング
- `tests/core/test_netmiko_init_compat.py` — docstring からテストに存在しない記述を削除、`_platforms()` ラッパー関数を削除し `get_platforms_from_md()` 直接呼び出しに統一（`test_netmiko.py` と同じパターン）

### Phase 6: コードレビュー対応
- `tests/core/test_netmiko_init_compat.py` — `test_unknown_command_graceful()` に `send_command_timing("?")` を追加し、未知コマンド後のセッション継続性を検証（codex [SHOULD FIX] 対応）

## 実施内容

### テスト結果（Phase 4）
```
uv run pytest tests/ -v
517 passed, 8 skipped
```
- 8 skipped: `INIT_UNKNOWN_CMD_ALLOWED` に含まれるプラットフォーム（aruba_os, brocade_fastiron, cisco_asa, dlink_ds, huawei_smartax, ipinfusion_ocnos, ruckus_fastiron, vyatta_vyos）

### リファクタリング後テスト結果（Phase 5）
```
uv run pytest tests/core/test_netmiko_init_compat.py tests/plugins/test_cmd_shell.py tests/plugins/test_ssh_server_paramiko.py -v
239 passed, 8 skipped
```

### レビュー対応後テスト結果（Phase 6）
```
uv run pytest tests/core/test_netmiko_init_compat.py::TestNetmikoInitCompat::test_unknown_command_graceful -v
41 passed
```

### lint 結果
```
uv run ruff check
All checks passed!
```

## コミット
- `684a71d` fix: TapIO.readline() crash and EOF handling (#71)
- `c0c8c84` fix: yamaha output: true misinterpreted as shell exit signal (#69)
- `0f7913d` test: add netmiko init compat and shutdown/EOF regression tests (#72)
- `cb45b7b` style: fix pre-existing ruff lint errors
- `05f9a65` test: final refactoring and session continuity verification (#72)
- `2ce96b7` chore: add worklog for issue-69-71-cmdshell-readline-crash

## 備考・判断事項
- #70 は Won't Fix でクローズ済み（#54 prompt-toolkit 移行の scope で対応予定）
- codex 1st review で案B（readline → ""のみ）の無限ループ問題を発見 → 案D（バッファ drain + do_EOF）に変更
- codex 2nd review で #72 テスト要件矛盾・Telnet 副作用・既存テスト影響を指摘 → 全て設計に反映
- 3rd review で codex・gemini ともに LGTM

## メモ(Notes)
- #70 は Won't Fix でクローズ済み — multi-step dialog flow は cmd.Cmd の制約上不可能。#54 prompt-toolkit 移行で対応予定
- 設計レビュー 3 回実施（codex + gemini）、3rd round で全員 LGTM

## 次やること(Next)
- [ ] PR 作成・push
- [ ] #69, #71 のクローズ確認

## コメント(レビュー/指摘/提案)

### 2026-03-07 21:46:48(JST) 🦊codex (1st review)

**判定:** SUGGESTION

**ファイルごとのレビュー:**
- `simnos/plugins/nos/platforms_yaml/yamaha.yaml`
  - [GOOD] `console lines infinity` を `output: ""` に変えたことで、`CMDShell.default()` で `True` が stop シグナルとして解釈されてセッションが閉じる経路を避けられています。
- `simnos/plugins/servers/ssh_server_paramiko.py`
  - [GOOD] `TapIO.readline()` の EOF を空文字に寄せた変更と `if not line:` が揃っていて、SSH 側も EOF を自然に抜けられる形になっています。
- `simnos/plugins/servers/tap_io.py`
  - [GOOD] EOF で `""` を返すようにしたのは `io.StringIO.readline()` と `cmd.Cmd.cmdloop()` の期待値に合っており、`None` 起因の shutdown 回帰に対する修正として妥当です。
- `simnos/plugins/servers/telnet_server.py`
  - [GOOD] `shell_to_socket_tap()` で `readline()` 後に `run_srv` を再確認したのは、停止レース時にソケットへ余計な送信を試みないためのガードとして効いています。
- `simnos/plugins/shell/cmd_shell.py`
  - [GOOD] `do_EOF()` の追加で、`cmdloop()` が EOF を正常終了として扱えるようになり、停止時の `Unknown command` や hang を避けられます。
- `tests/core/test_netmiko_init_compat.py`
  - [SHOULD FIX] `test_unknown_command_graceful()` は `send_command()` の戻り値が `None` でないことしか見ていないため、未知コマンドに応答した直後にシェルが落ちる回帰を検出できません。未知コマンド送信後に既知コマンドをもう 1 回実行して応答を確認するなど、セッション継続性まで見る形にした方がこのテストの目的に合います。
- `tests/plugins/test_cmd_shell.py`
  - [GOOD] `do_EOF()` の単体テストを追加していて、EOF ハンドラの退行を最小コストで押さえられています。
- `tests/plugins/test_ssh_server_paramiko.py`
  - [GOOD] `TapIO.readline()` の EOF 仕様変更に合わせて期待値を空文字へ更新しており、既存の SSH ユニットテストとの整合は取れています。

**総評:** EOF/停止処理の根本原因に対して、`TapIO` の EOF 互換化と `CMDShell.do_EOF()` の追加は筋が良い修正です。気になったのは 1 点だけで、未知コマンド回帰テストが「エラーを返せた」ことしか見ておらず、「その後もセッションが生きている」ことまで保証できていません。ローカルでの `pytest` 実行は、この環境に `detect` パッケージが入っていないため収集段階で確認できませんでした。

### 2026-03-07 13:45:00(JST) 🐳gemini (1st review)

**判定:** LGTM

**ファイルごとのレビュー:**
- `simnos/plugins/nos/platforms_yaml/yamaha.yaml`:
  - [GOOD] `output: ""` への変更により、YAMLパース時のブール値（`true`）の混入を防ぎ、一貫した文字列処理が保証される。
- `simnos/plugins/servers/ssh_server_paramiko.py`:
  - [GOOD] `if not line:` への変更により、`None` と空文字列の両方を適切にキャッチできるようになり、堅牢性が向上した。
- `simnos/plugins/servers/tap_io.py`:
  - [GOOD] タイムアウト時に `None` ではなく `""` を返すように変更。これは Python の `readline()` の標準的な挙動（EOF時に空文字列を返す）に準拠しており、望ましい。
  - [GOOD] ループ後の `if self.lines:` チェックにより、極めて稀なタイミングの競合（ループ終了直後にデータが入るケース）への耐性が向上している。
- `simnos/plugins/servers/telnet_server.py`:
  - [GOOD] `contextlib.suppress(TimeoutError)` の使用により、コードが簡潔で読みやすくなっている。
  - [GOOD] `readline()` の戻り値チェック (`if not line`) とサーバー停止フラグ (`run_srv.is_set()`) のチェック追加により、終了処理の応答性が向上した。
- `simnos/plugins/shell/cmd_shell.py`:
  - [GOOD] `do_EOF` メソッドの追加。これにより、入力ストリームが閉じた際に `cmdloop` が適切に終了し、プロセスのハングを防ぐことができる。
- `tests/core/test_netmiko_init_compat.py`:
  - [GOOD] 新規テストファイルの追加。Netmiko との互換性、および EOF 処理の回帰テストが網羅されており、非常に価値が高い。`INIT_UNKNOWN_CMD_ALLOWED` による既知の問題の除外も適切。
- `tests/plugins/test_cmd_shell.py`:
  - [GOOD] `do_EOF` の単体テストが追加されており、変更が検証されている。
- `tests/plugins/test_ssh_server_paramiko.py`:
  - [GOOD] `TapIO` の仕様変更（`None` -> `""`）に合わせたテストの更新。
  - [GOOD] `noqa: S507` の追加によるセキュリティ警告の抑制。テストコード内での自動ホストキー受け入れは一般的であり、適切。

**総評:**
本変更は、EOF処理の標準化（`None` から `""` への移行）と、シェルおよびサーバーのクリーンな終了処理の改善に重点を置いています。
特に `do_EOF` の実装と `TapIO` の挙動修正は、長時間のセッションや異常終了時の安定性に大きく寄与します。
テストも十分に拡充されており、品質の高いパッチです。
