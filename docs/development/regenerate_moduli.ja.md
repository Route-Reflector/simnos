# Bundled moduli の再生成

SIMNOS は Diffie-Hellman Group Exchange (DH-GEX) 用の moduli ファイルを
`simnos/plugins/servers/moduli` に同梱しています。これにより、system
moduli ファイル (`/etc/ssh/moduli`) を持たないホスト (主に Windows /
macOS) でも paramiko ベースの SSH サーバが GEX 鍵交換をサポートできます。
このページでは、このファイルが存在する理由、再生成のタイミング、および
正確な手順を文書化します。

## なぜ SIMNOS が moduli を同梱するのか

paramiko 自身は moduli ファイルを同梱していません。`/etc/ssh/moduli` または
`/usr/local/etc/moduli` をシステムが提供することを期待していますが、
Windows / macOS ホストは通常これを持ちません。moduli ファイルが無い場合、
paramiko の GEX server-mode は stale-snapshot bug (paramiko issue
[2126](https://github.com/paramiko/paramiko/issues/2126)) に遭遇するため、
SIMNOS は workaround として GEX アルゴリズムを全て server-side で disable
します。これに paramiko 5.0 の SHA-1 KEX 削除が組み合わさると、
`netmiko.fortinet.FortinetSSH` のような SHA-1-leaning legacy client と
**空の KEX overlap** が発生し、Windows / macOS で deterministic な接続失敗を
引き起こします。

自前で moduli ファイルを同梱することで、これらの platform でも server が
`gex-sha256` を advertise できるようになり、SHA-1 KEX を復活させずに接続性を
回復します。詳細な root-cause 解析は [paramiko issue 2126 への
follow-up コメント](https://github.com/paramiko/paramiko/issues/2126#issuecomment-4458397596)
を参照してください。

### なぜ paramiko 同梱の moduli を使わないのか?

paramiko は moduli を同梱していません (検証済: 当該 paramiko package 内に
`moduli` ファイルは存在しない)。自前で同梱することで、OpenSSH サーバが
installed されていない platform でも SIMNOS が自己完結します。

### なぜ OpenSSH の openssh-portable から直接 copy しないのか?

可能ではあります (license は BSD 系で SIMNOS の MIT と互換) が、自前で
`ssh-keygen` で生成することで以下の利点があります:

- 生成日時が記録される (ssh-keygen の `# Time` ヘッダで自動記録)
- rotation 責任が明確 (再生成タイミングを SIMNOS 側で制御可能)
- OpenSSH の release cadence から独立

コストは maintainer マシンでの 1 回限りの数時間の生成だけです。

## moduli は公開情報

DH prime は SSH protocol で KEX 時に毎回 client へ送信されるため、秘密
情報ではありません。OpenSSH 自身も
[`openssh-portable`](https://github.com/openssh/openssh-portable)
public リポジトリで moduli を公開しています。SIMNOS が moduli を GitHub
public repo に同梱することは同じ慣習であり、security implication はあり
ません。

## Rotation policy

- **3 年ごと** (次回推奨日: YYYY-MM、ファイルの ssh-keygen `# Time`
  ヘッダ + 3 年で計算)
- **Ad-hoc**: 2048-bit 以上の DH-GEX に対する新規 logjam-class
  precomputation 攻撃が報告された場合

Rotation 頻度は意図的に緩めに設定しています — 2048-bit 以上の DH prime は
precomputation 攻撃の実用範囲外ですし、SIMNOS は production SSH server
というより test simulator としての用途が中心だからです。3 年という
baseline は主要 Linux distribution の典型的な refresh 周期に揃えてあります。

## 手順

Linux maintainer machine で実行してください。`-M screen` step は CPU-bound
かつ single-threaded で、物理 host では合計数時間、VM 環境ではさらに長
時間かかる場合があります。そのため 3072-bit の screen 処理は
`split -n l/N` で candidates ファイルを N 分割し、複数 ssh-keygen process
を並列に走らせるアプローチを取ります。ファイルは 1 度生成して commit
するだけで、CI で再生成することはありません。

現在の bundle には 2048-bit と 3072-bit の primes のみが含まれます。
4096-bit primes は本リリースでは見送り済みです (詳細は設計 doc の
Notes § と、4096 を追加する follow-up chore PR を参照)。

```bash
# 1. 各 bit size の候補生成 (高速、数秒〜数分)
ssh-keygen -M generate -O bits=2048 moduli-2048.candidates
ssh-keygen -M generate -O bits=3072 moduli-3072.candidates

# 2a. 2048-bit candidates を 1 process で screening (約 30 分〜3 時間)
ssh-keygen -M screen -f moduli-2048.candidates moduli-2048

# 2b. 3072-bit candidates を分割し、複数 ssh-keygen を並列実行
#     (利用可能 CPU 数に合わせて N を調整)
split -n l/8 moduli-3072.candidates moduli-3072.chunk.
for chunk in moduli-3072.chunk.*; do
  (ssh-keygen -M screen -f "$chunk" "${chunk}.screened") &
done
wait
cat moduli-3072.chunk.*.screened > moduli-3072

# 3. 同梱ファイルとして concatenate
#    (ファイル名は拡張子なし、OpenSSH 慣習に揃える)
cat moduli-2048 moduli-3072 > simnos/plugins/servers/moduli

# 4. 中間ファイル cleanup
rm moduli-*.candidates moduli-2048 moduli-3072 moduli-3072.chunk.*

# 5. 検証 (合計で数百〜数千行になるはず)
wc -l simnos/plugins/servers/moduli
head -1 simnos/plugins/servers/moduli   # 「# Time」ヘッダの存在を確認
```

これらのコマンドは cwd にのみ書き込み、system の `/etc/ssh/moduli` には
触れません。root 権限も不要です。

## wheel に moduli が含まれていることの verify

新しいファイルを commit したら、local で wheel をビルドし、moduli ファイル
が含まれていることを確認してください:

```bash
uv build
unzip -l dist/simnos-*.whl | grep moduli
tar tzf dist/simnos-*.tar.gz | grep moduli
```

ファイルが含まれていない場合は、`pyproject.toml` に明示的に include を
追加してください:

```toml
[tool.uv.build-backend]
source-include = ["simnos/plugins/servers/moduli"]
```

Release CI workflow でも publish 前に wheel 内の moduli ファイル存在を
assert します。

## Commit と PR

- Commit message: `chore: regenerate bundled moduli (#NNN)`
- PR description に新しい「next recommended rotation」日 (生成日 + 3 年) を
  記録
- logjam-class trigger による再生成の場合は、その背景も簡潔に記載
