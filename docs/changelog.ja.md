# 変更履歴 (Changelog)

SIMNOS の主要な変更点をここに記録します。
詳細は [GitHub Releases](https://github.com/Route-Reflector/simnos/releases) を参照してください。

## Unreleased

<!-- リリース時にこの見出しを `## v3.0.0 - YYYY-MM-DD` に差し替える。 -->

SIMNOS v3 は SSH/Telnet コアとプラグインのデータレイアウトを clean rewrite した
ものです。破壊的変更は以下の移行ガイドに集約しています。各行は後述の詳細エントリへ
リンクしています。

**v2 からの移行 (Migration from v2)**

_v2 に留まる場合 (移行期間)_ — v2 は critical / security 修正のみの移行期間として
保守されます。移行の準備が整うまでは、以下のいずれかで固定してください:

- PyPI: `pip install "simnos<3"`
- Docker: メジャータグ `simnos:2` を pin する (`:latest` は v3 を追うので使わない)
- git: `v2.4.0` タグ、または `2.x` メンテナンスブランチを pin する

_v3 へ上げる場合_ — 該当する変更をそれぞれ適用してください:

| こういう場合… | こうする |
|---|---|
| インベントリで `platform:` を使っている | キーを `device_type:` に改名する — エイリアスは無く `platform:` はロード時に拒否されます (`sed -i 's/^\([[:space:]]*\)platform:/\1device_type:/' inventory.yaml`)。#266 参照 |
| `ParamikoSshServer` プラグインを設定している | 削除する — `AsyncSshServer` が既定の SSH プラグインです。`ssh_key_file` / `ssh_banner` / `authorized_keys` はそのまま引き継がれます。#297 参照 |
| `simnos -i inventory.yaml` (または素の `simnos`) で起動している | サブコマンド形式を使う: `simnos up -i inventory.yaml` (default inventory なら `simnos up`)。#267 参照 |
| リッスンポート `6000` / `6001` / `6002` をハードコードしている | `start()` 後に `net.hosts[<name>].port` から実ポートを読む (CLI もログ出力します)。既定ポートは OS 割り当てになりました。#271 参照 |
| シェルの `configuration` ブロックで `ruler` / `completekey` を設定している | 削除する — ロード時に拒否されます (`extra="forbid"`)。#303 参照 |
| カスタムコマンド handler から dict (`{"output", "new_mode", "exit"}`) を返している | `str` (または `None`) のみを返し、遷移はコマンド側に静的に書く (A3 の `new_mode` / `exit` / `transitions`) — dict 返しは `% Internal error` 応答になります。#317 参照 |
| インベントリの `nos: configuration: commands:` ブロックでコマンドを定義している | 各エントリを A3 方言に書き換える: `prompt:` → `mode:` (mode 名、例 `[user, enable]`)、`new_prompt:` → `new_mode:`。そのまま返す本文は `output:` に残す (raw literal 化 — `{{`/`}}` エスケープの collapse は行われません)。`{base_prompt}` を含む本文は jinja2 記法 `{{ base_prompt }}` の `output_template:` へ。`alias` / `output_variants` エントリは拒否されます。#317 参照 |
| NOS plugin を py の `commands` dict で書いている (`platforms_py/<name>.py` の dict、`Nos(commands=…)` / `from_dict`、`SimNOS(plugins=[dict])`) | コマンドデータを A3 platform dir (`platforms/<name>/platform.yaml` + `commands/*.yaml` + 隣接 `.txt`/`.j2`) へ移し、py module は device class + `handler:` callable 専用にする — dict 形式は拒否され、対応する A3 dir の無い py module は登録されなくなりました。#317 参照 |
| `paramiko` を推移的依存として当てにしている | ランタイム依存ではなくなりました — 自前コードで import していたなら明示的に依存を追加してください。#297 参照 |

scraper (netmiko / scrapli / ansible) から見た wire 上の挙動は不変で、byte-parity
golden で固定されています — コマンドを送って出力を読むだけの自動化ツールにクライアント
側の変更は不要です。

**破壊的変更**

- インベントリのキー `platform` を `device_type` に改名 (v3, #266)。互換エイリアスはありません。`platform:` を使う v2 インベントリはロード時に拒否されます。移行はキーを書き換える (`sed -i 's/^\([[:space:]]*\)platform:/\1device_type:/' inventory.yaml`) か、v2 に固定する (`pip install "simnos<3"`、移行期間として保守) かのいずれかです。`device_type` にはプラットフォームの内部名 / `netmiko_device_type` / `ntc_platform` エイリアスのいずれも指定でき、データ駆動の逆引きインデックスを介してすべて同一プラットフォームに解決されます (#266)
- SSH / Telnet サーバのトランスポートを、共有 asyncio イベントループ上の非同期バックエンドに置換: SSH は `asyncssh` (旧 paramiko)、Telnet は `telnetlib3` で動作し、いずれも単一の push-dispatch セッションループで駆動されます (#297)。`ParamikoSshServer` プラグインとその inventory 設定は削除されました — `AsyncSshServer` (既定の SSH プラグイン) を使ってください。既存の `ssh_key_file` / `ssh_banner` / `authorized_keys` オプションはそのまま引き継がれます。同梱の DH-GEX moduli ファイルと paramiko GEX ワークアラウンドは削除され (asyncssh が moduli を自前でネゴシエート)、`paramiko` はランタイム依存ではなくなりました (byte-parity / 相互運用テストのクライアント用に dev 依存として残置)
- CLI をサブコマンド方式に再構成: `simnos up` でサーバを起動し、`simnos list-platforms` で対応プラットフォームを一覧します (#267)。v2 のフラット形式 (`simnos -i inventory.yaml`、または default inventory 用の素の `simnos`) はもうパースされません — サブコマンドが必須になりました (`simnos up -i inventory.yaml`、または default inventory 用の `simnos up`)。`up` にはアドホックな単一ホストモード (`-d/--device-type` に加えて任意で `-p/--port`、`-n/--host-name`、`-u/--username`、`-w/--password`) も追加され、インベントリファイルなしで単発のプラットフォームを起動できます。`-l/--log-level` と `-r/--reload-commands` は各サブコマンド共通のフラグとして引き継がれます
- 既定のリッスンポートを、固定値 `6000` / `6001` / `6002` から OS 割り当て (ephemeral) に変更 (#271)。引数なしの `SimNOS()` (組み込み default inventory) と `port: 0` を指定したインベントリホストは、`bind()` 時に OS がアトミックに選んだポートにバインドします。実ポートは `start()` 後に `host.port` から読み戻してください (CLI は `host <name> listening on <addr>:<port>` をログ出力します)。これにより macOS CI で見られたワーカー間のポート衝突フレーク (`OSError: Errno 48`) が解消します。`6000` をハードコードしていた呼び出し側やテストは、代わりに `net.hosts[<name>].port` を読む必要があります。replicas リスト経路は依然として明示的な `ge=1` ポートを要求します — ephemeral は単一ホスト専用です
- `ruler` / `completekey` シェル設定ノブを、それが属していた `cmd.Cmd` 基底クラスとともに削除 (#303)。これらを設定するインベントリ `configuration` ブロックはロード時に拒否されます (`extra="forbid"`) — キーを削除してください。scraper (netmiko / scrapli / ansible) から見た wire 上の挙動は不変で、byte-parity golden で固定されています
- コマンド handler の戻り値契約を `str | None` に縮小 (#317)。dict 返し形式 (`CommandResult` の `output` / `new_mode` / `exit`) は削除されました: dict を返し続けるカスタム py plugin handler には wire 上で固定の `% Internal error` 行 + サーバ ERROR ログが返り、遷移も発火しません。mode 遷移とセッション終了は静的に書いてください — A3 コマンドの `new_mode` / `exit` / `transitions`。同変更で同梱の cisco_ios / arista_eos / huawei_smartax はコマンド authoring を py `commands` dict から A3 platform dir へ移送済みです (py module は device class + 動的 output handler のみ)。副作用として、per-host `overlay` entry はコマンドの実配信 mode 集合を継承するようになりました (例: cisco_ios `show version` の overlay は enable mode が必要 — 実 wire と一致)
- インベントリコマンドの schema (`nos: configuration: commands:`) を A3 方言に刷新 (#317)。エントリは mode *名* と静的遷移で書きます — `mode:` (リスト、省略 = 全 mode)、`new_mode:` / `exit:` / mode 条件付き `transitions:`、`help:`、そして inline の `output:` (verbatim literal) または `output_template:` (`{{ base_prompt }}` で render される jinja2 ソース)。legacy の prompt 文字列 field はロード時に拒否されます: `prompt:` / `new_prompt:` (mode 名を使う)、`alias:` (削除 — inflow をまたぐ alias は解決意味論が未定義)、`output_variants:`。移行本文の render 変更が 2 点あります: `output:` は raw literal になり (v2 の `str.format` による `{{`/`}}` brace エスケープ collapse は廃止)、`{base_prompt}` を参照していた本文は jinja2 記法の `output_template:` へ移す必要があります。mode 名は起動時にプラットフォームの modes に対して検証されるため、typo はセッション中でなく `start()` で失敗します。py module が `commands` dict を定義している場合もロード時に拒否されます (その authoring channel は #317 P-2 で A3 dir へ移送済みで、「ロードは通るが merge に乗らない」dict は誤りを隠すため)
- legacy py-dict authoring の基層を全面撤去 (#317)。コマンド authoring の形式は A3 platform dir のみになりました: `Nos(commands=…, initial_prompt=…)`、`Nos.from_dict` / `dict_args`、`SimNOS(plugins=[…])` の dict 形式は削除され (str plugin は A3 platform dir のパス限定)、対応する `platforms/<name>/` dir の無い `platforms_py/<name>.py` module は警告のうえ登録されません (py-only platform はコマンドを配信できません)。py module の legacy 定数 (`NAME`、`INITIAL_PROMPT`、`ENABLE_PROMPT`、`CONFIG_PROMPT`、`AUTH`) はもう読まれません — プラットフォーム名は A3 dir の basename、prompt / auth は `platform.yaml` が持ちます。py module は動的挙動の channel として残ります: device class と、A3 `handler:` field がバインドする関数群です
- `BaseDevice` 基底クラスを `simnos/plugins/nos/base_device.py` に移設 (#350)。従来は `simnos/plugins/nos/platforms_py/_templates/base_template.py` に「authoring テンプレート」を名乗って置かれていましたが、実際は全 device モジュール (と core) が import する必須のランタイム基底クラスでした。旧 import path と空になった `_templates/` サブパッケージは削除。外部の py handler モジュールは import 行 1 箇所の更新のみが必要で、クラス自体は不変です

**機能強化**

- トポロジ inventory とは別の、最小限の環境設定ファイル `sys_config.yaml` (`data_dir`、`variants_policy`) を導入。`sys_config=` 引数、`SIMNOS_SYS_CONFIG` 環境変数、`./sys_config.yaml`、`~/.simnos/sys_config.yaml` の順で探索し、`SIMNOS_DATA_DIR` が `data_dir` を上書きします。設定の優先順位 `CLI > env > inventory(host > default) > sys_config > builtin` を確立します。両フィールドは予約 (no-op、ロード時に警告) で、#265 / #267 で実配線されます (#266)
- インベントリフィールド `facts` / `overlay` / `variants_policy` を #265 のスキーマの器として予約。検証はされますがまだ誰も消費しません。設定されているが不活性な値は暗黙に無視せず `log.warning` で顕在化します (#266)
- プラグインのプラットフォームレイアウトを A3 ディレクトリ形式に移行: 従来のモノリシックなプラットフォーム単位 YAML を、プラットフォーム単位の `platform.yaml` (modes + prompts) と、`commands/*.yaml` 配下のコマンド 1 個 1 ファイル (隣接する `.txt` / `.j2` 出力) に置換 (#264)。`command` フィールドが単一の真実の源 (SSoT) で、ビルド時 lint (`invoke lint-platform-data`) が encoding / 参照 / 拡張子の規約を強制します。任意の動的挙動は引き続き `platforms_py/<nos>.py` に置けます
- データ駆動の facts レンダリングとコマンド単位の出力バリアントを追加 (#287)。コマンド出力は `.j2` テンプレート + 隣接するサイドカー `.json` (ビルド時に厳格検証) の facts として記述でき、コマンドは `variants_policy` (`int` / `random`、任意で seed) で選択される複数の `variants` を宣言できます。canonical 出力を共有し、二相のアトミック swap で書き出します
- SSH セッションに対話的ラインエディタを追加: `?` の文脈ヘルプ (現在モードのコマンド一覧)、コマンドツリーに対する Tab 補完、`↑` / `↓` 履歴、`←` / `→` カーソル移動と backspace を、push-dispatch ループ上の軽量 readline レイヤとして実装 (#303)。編集シーケンスは対話的なキー入力時のみ出力されるため、scraper からのフルライン入力には影響せず byte-parity で同一を維持します
- 実機式のコマンド省略マッチを追加: トークン単位で一意な prefix が完全なコマンドに解決され、曖昧なときは `% Ambiguous command`、部分一致のときは incomplete-command メッセージを返します (#305)。省略マッチは dispatch コア (既定 ON) と Tab 補完で共有されます
- 長い出力向けにターミナルページング (`--More--`) を追加 (#307)。ページ高は PTY / Telnet NAWS の行数に従い (取得できなければ `sys_config.paging.default_rows`、既定 24 にフォールバック)、`terminal length 0` 系のコマンドはそのセッションのページングを無効化します (`disables_paging` データフラグ)。非対話クライアント (netmiko の `height=1000`、scraper) は byte-parity を保つ行数ゲートを通じてページャをバイパスします。`--More--` 文字列はプラットフォームデータです (`platform.yaml` の `paging.more_prompt`、Cisco 既定は `" --More-- "`)
- コマンドの hot-reload ウォッチャ (`SIMNOS_RELOAD_COMMANDS`) を、per-shell スナップショット + プラットフォーム単位 watch にスコープし、共有 reload を host ロック下で直列化することで、並行セッションと競合しないようにしました (#281)

**バグ修正**

- `SimNOS` インスタンス間 (およびインスタンス → 呼び出し元) の状態汚染を解消 (#346)。`SimNOS(plugins=[...])` の登録先が共有 module-global からプラットフォームレジストリの per-instance copy に変わり、インスタンス A で登録した custom plugin はインスタンス B から見えなくなりました — この漏れに依存していた場合は、利用する各 `SimNOS` の `plugins=[...]` に渡してください。また explicit な `inventory` dict を in-place で書き換えなくなりました (`plugins` list も契約として同様に copy されます): SimNOS は自身の copy 上で動作する (inventory は deep copy、plugins list は container copy) ため、同じ inventory dict を異なる `sys_config` 設定のインスタンス間で使い回しても、最初のインスタンスが seed した `variants_policy` を silent に継承しません
- コマンド解決を deterministic + 実機準拠に是正 (#348)。省略マッチは、短いコマンドが exact トークンを持つときに**別の**コマンドを実行しなくなりました (`show ip` と `show ipv6 route` が両方あるとき `show ip ro` は、`show ipv6 route` を実行する代わりに実機 IOS 同様 unknown-command エラーを返します)。また別モードのコマンドへの exact match が現在モードの省略マッチ空間を shadow しなくなりました (実機は per-mode 解決なので、返すべき場面では `% Incomplete command.` 等を返します)。loader 側では、別の alias を指す alias が load error になり (chain の解決結果がファイル名 sort 順に silent 依存していたため — alias は real コマンドを直接指してください)、継承した challenge 発火モードを落とす alias `mode:` override も既存の transitions check と同様に拒否されます。full な in-mode コマンドは省略マッチに入らないため scraper の wire は byte 同一 — 変わるのは従来誤動作していた入力だけです
- async session driver に 4 箇所コピーされていた CR/LF/NUL 終端 state machine を単一の step 関数に統一し、byte 分類の divergence 2 件を修正 (#350)。`--More--` pager は、CR-LF 分割の pending 中に SSH の NUL が来ても phantom でページを進めなくなりました (NUL が pending を clear せず保持するようになり、後続の LF が CR の片割れとして消費されます)。また in-band login (auth-none / Telnet) は、迷子の NUL を echo して username/password に混入させなくなりました (CR 隣接の 1 個だけでなく、全 NUL を drop)。どちらもほぼ到達不能な byte 列にのみ影響し、scraper の wire は byte 同一 — byte-parity golden は無変更です

## v2.3.1

**バグ修正**

- DH Group Exchange (DH-GEX) moduli ファイル (`simnos/plugins/servers/moduli`、2048 + 3072 ビット素数を連結) を同梱し、システム moduli が無いときのフォールバックとしてロード。Windows / macOS で `gex-sha256` の advertise を復活させ、`netmiko.fortinet.FortinetSSH` のような SHA-1 寄りのレガシー SSH クライアントが再び KEX を完了できるようにします — v2.3.0 の Known Issues に挙げた `pytest-full-matrix` の Win/macOS 決定的失敗を解消します。Linux の挙動は不変 (システムの `/etc/ssh/moduli` が引き続き優先)。既存の `_default_key_lock` パターンに倣った thread-safe な one-shot ロードキャッシュ用に `_moduli_lock` を追加し、同梱欠落 / 同梱破損の退行経路に `log.error` アラームを追加。4096 ビット素数は VM ホストでの ssh-keygen `-M screen` 実行時間の都合で将来の chore PR に先送り (#189)

**ツール**

- ローテーションポリシー (3 年ごと、logjam 級イベント時はアドホック) と `ssh-keygen` による再生成手順を記した `docs/development/regenerate_moduli.md` (+ `.ja.md` i18n) を追加 (#189)
- リリース時の `unzip -l dist/*.whl | grep moduli` / `tar tzf dist/*.tar.gz | grep moduli` アサーションを `pypi-publish.yml` に追加し、同梱 moduli を落とすパッケージング退行を publish 前に検出 (#189)

## v2.3.0

**破壊的変更**

- `hp_comware` プラットフォームを、従来の Cisco 風プロンプト (`>`/`#`/`(config)#`) ではなく実機の HP Comware CLI 規約 (`<HOST>` user view / `[HOST]` system view) に沿って書き直し。`enable` / `ex` コマンドを削除 (HP には存在しない) し、`system-view` / `return` / `quit` を追加。hp_comware の netmiko / scrapli / ansible 相互運用が追加設定なしで動作するようになりました。従来の `enable` コマンドをスクリプトで叩いていた直接 CLI ユーザは、`system-view` を使うようスクリプトを更新する必要があります (#173, closes #136)

**新機能**

- `cisco_ios` 向けに netmiko / scrapli / ansible 互換 CI ワークフロー (`workflow_dispatch`) を追加。`compatibility` pytest マーカーと `compatibility` オプション依存グループ (`scrapli`、`ansible-core`) でゲートした新しい `tests/compatibility/` テストスイート。各ライブラリは独立した CI ジョブとして実行されます。netmiko + scrapli 完全互換のため `terminal width 512` / `configure terminal` / `end` / `exit` を `cisco_ios.yaml` に追加 (#177, closes #125 Phase 1+2+3)
- NTC Templates v9.1 コマンドを 10 プラットフォームに追加 — `mikrotik_routeros` (25)、`linux` (15)、`alcatel_aos` (12)、`alcatel_sros` (7)、`ciena_saos` (5)、`aruba_os` (4)、`extreme_exos` (2)、`hp_procurve` (2)、`paloalto_panos` (2)、`aruba_aoscx` (1): 合計 75 コマンド (#174)
- NTC Templates v9.1 コマンドを `hp_comware` に追加 — `display bgp peer ipv4` / `display link-aggregation member-port`: 2 コマンド。`#128` NTC v9.1 エピックをクローズ (#175)

**バグ修正**

- `cmd_shell.default` が、yaml `output` に未認識の `str.format` プレースホルダを含む場合でもシェルセッションをクラッシュさせないように修正。`KeyError` / `ValueError` / `IndexError` を捕捉し、エラーをログ出力して raw output を返します。ランタイムは意図的に寛容ですが、ビルド時のドキュメント生成 (`tasks.render_template`) は同じ状況で引き続き `RuntimeError` を送出します (#170, closes #162)

**ツール**

- `invoke gen-docs-platform-commands` が、裏付けとなる yaml が削除された `docs/platforms/*.md` を孤児として掃除するようになりました。`index.md` / `index.ja.md` 用に `_PRESERVED_PLATFORM_DOCS` を含みます (#169, closes #159)

**テスト**

- `pytest-rerunfailures` を追加し、`test_send_command_returns_defined_output` を `@pytest.mark.flaky(reruns=2, reruns_delay=1)` でマークして、遅い CI ランナー (例: `broadcom_icos`) で断続的に観測された netmiko auto-enable レースを安定化 (#176)

**依存関係**

- `paramiko` 制約を `>=4.0,<5.0` から `>=4.0,<6.0` に引き上げ (paramiko 5.0 リリース)。既存の `_DISABLED_GEX_ALGORITHMS` ワークアラウンドは引き続き必要 (upstream の stale-snapshot バグが 5.0 でも未修正) (#168)
- `urllib3` を 2.6.3 から 2.7.0 に更新 (#167)

## v2.2.1

**新機能**

- Cisco ファミリに NTC Templates v9.1 コマンドを追加 — cisco_nxos / cisco_xr / cisco_asa: 合計 19 コマンド。`cisco_asa` の手動 netmiko init 互換 (`show curpriv` / `terminal pager 0` など) を含みます (#151)
- 非 Cisco バッチに NTC Templates v9.1 コマンドを追加 — fortinet / juniper_junos / paloalto_panos / arista_eos: 合計 30 コマンド (#154)
- Huawei ファミリに NTC Templates v9.1 コマンドを追加 — huawei_smartax / huawei_vrp: 合計 39 コマンド (#160)
- Ansible 互換のため cisco_ios に `show privilege` を追加し、互換表で cisco_ios を Ansible 検証済みとしてマーク (#124)

**バグ修正**

- `gen_docs_platform_commands` invoke タスクを書き直し: `output` フィールドの無いコマンドを扱い、ランタイム意味論に合わせて `{base_prompt}` 置換に `str.format()` を使用、正しいレンダリングで全 50 プラットフォームのドキュメントを再生成 (#146)
- ドキュメント生成器を `str.format()` に切り替えることで、エスケープされた波括弧リテラル (`{{ ... }}`) をプラットフォームドキュメントで正しくレンダリング (`cmd_shell.default` ランタイムと一致)。フィクスチャにリテラル波括弧を含む 10 プラットフォーム (huawei_smartax、juniper_junos、cisco_asa、cisco_ios、cisco_nxos、hp_comware、arista_eos、paloalto_panos、oneaccess_oneos、huawei_vrp) に影響 (#160)

**ツール**

- `sync_ntc_commands.py` を改善: canonical な raw フィクスチャを優先し、代替フィクスチャを `output_variants` として保持、兄弟フィクスチャのノイズをフィルタ (#147)
- `sync_ntc_commands.py` 出力でリテラル `{xxx}` パターンを自動エスケープ (予防的エスケープ) し、任意の NTC フィクスチャ内容に対してランタイム `str.format()` が安全になるように (#156)

**テスト**

- `render_template` フォーマッタの意味論 (置換、escape/unescape、エラーコンテキスト) を固定する `tests/test_gen_docs_platform_commands.py` を追加し、波括弧レンダリングの将来の退行を防止 (#160)

**CI/CD**

- `pytest-xdist` の並列実行を既定で有効化 (`addopts = "-vv -n auto"`)。ローカル計測: 18:06 → 3:01 (6.0 倍高速化) (#164)
- Docker 前提のタスク (`build` / `clean` / `rebuild` / `pytest` / `cli` / `tests`) と dead code を `tasks.py` から削除し、CI ワークフローから `INVOKE_LOCAL` を除去 (#145)

## v2.2.0

**新機能**

- NTC Templates v9.0 から 9 個の新プラットフォームを追加: aruba_aoscx、cisco_apic、cisco_viptela、cisco_wlc_ssh、edgecore、extreme_slxos、oneaccess_oneos、watchguard_firebox、zte_zxros (#129)
- NTC Templates v9.1 から cisco_ios に 28 個の新コマンドを追加 (SD-WAN、CTS、endpoint-tracker、license コマンドを含む) (#128)

**テスト**

- 全 YAML-only プラットフォームに netmiko 接続テストを追加 (#129)
- フルプラットフォーム xfail の代わりに、粒度の細かい `skip_enable_platforms` でテスト skip ロジックを精緻化 (#129)

**ドキュメント**

- バイリンガル対応 (英語 / 日本語)、AI Transparency ポリシー、コントリビューションワークフローを含む `CONTRIBUTING.md` を追加 (#121)
- GitHub Private Vulnerability Reporting を指すバイリンガル対応の `SECURITY.md` を追加 (#120)
- プラットフォーム互換リストを、注記付きの詳細な互換表に変換 (#129)

**CI/CD**

- 50 以上の YAML プラットフォーム検証のため yamllint を CI に追加 (#137)

**依存関係**

- ntc-templates 9.0.0 → 9.1.0 (netmiko 経由の推移的依存)
- cryptography 46.0.5 → 46.0.7
- pytest 9.0.2 → 9.0.3
- trivy-action 0.35.0 → 0.36.0
- GitHub Actions Pages ワークフローを Node.js 24 互換バージョンに更新

## v2.1.3

**セキュリティ**

- trivy-action のサプライチェーン侵害を修正: 0.34.1 → v0.35.0 に更新 (#117)

**CI/CD**

- GitHub Actions を Node.js 24 互換バージョンに更新 (#112, #118)
- 週次自動更新のため Dependabot 設定を追加 (#116)

## v2.1.2

**パフォーマンス**

- SSH/Telnet tap 関数のバイト単位 `time.sleep(0.01)` を除去 — テストスイートが約 20% 高速化 (#107)
- 即時サーバシャットダウンのため `accept()` ポーリングを `selectors` + `socketpair` に置換 (#106)

**セキュリティ**

- 7 件の Dependabot アラートを修正するため依存関係をアップグレード: urllib3、filelock、virtualenv、pynacl (#111)

## v2.1.1

**バグ修正**

- Docker Trivy スキャン失敗 (zlib CVE) を `apk upgrade --no-cache` で解消 (#102)
- cisco_ios の macOS テストタイムアウトを 600 秒に延長 (#102)
- Telnet 認証失敗時の BrokenPipeError を修正 (#102)

**CI/CD**

- 早すぎる publish を防ぐため、publish ワークフローのトリガをタグ push から release イベントに変更 (#103)

## v2.1.0

**新機能**

- SSH / Telnet サーバの echo coalescing — netmiko `send_command()` で断続的に空出力になる問題を防止 (#87, #94)
- RFC 854/857/858 準拠の Telnet サーバプラグイン
- SSH / Telnet サーバで共有する thread-safe な TapIO I/O ブリッジ

**バグ修正**

- thread-unsafe な ChannelFile を直接 Channel API に置換 (#85)
- SSH channel_to_shell_tap に CRLF 処理を追加 (#88)
