# プラットフォーム

SIMNOS がサポートするプラットフォームの一覧です。各プラットフォームは SSH ログインと Netmiko の互換性をテスト済みです。

## 互換性の凡例

| 記号 | 意味 |
|:---:|---|
| ✅ | 動作確認済み |
| ⚠️ | 制限あり — Notes を参照 |
| `-` | 未テスト |

!!! note
    プラットフォームに問題が見つかった場合は、[GitHub リポジトリ](https://github.com/Route-Reflector/simnos/issues)で Issue を作成してください。

## 利用可能なプラットフォーム

| Platform | SSH | Netmiko | Scrapli | Ansible | Notes |
|---|:---:|:---:|:---:|:---:|---|
| [alcatel_aos](alcatel_aos.md) | ✅ | ✅ | - | - | |
| [alcatel_sros](alcatel_sros.md) | ✅ | ⚠️ | - | - | Netmiko が `enable-admin` を送信し `secret`（enable パスワード）を要求する。SIMNOS は enable secret 未対応。show コマンドは enable なしで動作。 |
| [allied_telesis_awplus](allied_telesis_awplus.md) | ✅ | ✅ | - | - | |
| [arista_eos](arista_eos.md) | ✅ | ✅ | - | - | |
| [aruba_aoscx](aruba_aoscx.md) | ✅ | ✅ | - | - | v2.2.0 で追加 |
| [aruba_os](aruba_os.md) | ✅ | ✅ | - | - | |
| [avaya_ers](avaya_ers.md) | ✅ | ✅ | - | - | |
| [avaya_vsp](avaya_vsp.md) | ✅ | ✅ | - | - | |
| [broadcom_icos](broadcom_icos.md) | ✅ | ✅ | - | - | |
| [brocade_fastiron](brocade_fastiron.md) | ✅ | ✅ | - | - | |
| [brocade_netiron](brocade_netiron.md) | ✅ | ✅ | - | - | |
| [checkpoint_gaia](checkpoint_gaia.md) | ✅ | ✅ | - | - | |
| [ciena_saos](ciena_saos.md) | ✅ | ✅ | - | - | |
| [cisco_apic](cisco_apic.md) | ✅ | ⚠️ | - | - | Linux ベース NOS。Netmiko が enable モード昇格で `sudo -s` を送信する。SIMNOS は sudo 未対応。手動 `enable` 後に show コマンドは動作。v2.2.0 で追加 |
| [cisco_asa](cisco_asa.md) | ✅ | ✅ | - | - | |
| [cisco_ftd](cisco_ftd.md) | ✅ | ✅ | - | - | |
| [cisco_ios](cisco_ios.md) | ✅ | ✅ | - | ✅ | |
| [cisco_nxos](cisco_nxos.md) | ✅ | ✅ | - | - | |
| [cisco_s300](cisco_s300.md) | ✅ | ✅ | - | - | |
| [cisco_viptela](cisco_viptela.md) | ✅ | ✅ | - | - | v2.2.0 で追加 |
| [cisco_wlc_ssh](cisco_wlc_ssh.md) | ✅ | ✅ | - | - | v2.2.0 で追加 |
| [cisco_xr](cisco_xr.md) | ✅ | ✅ | - | - | |
| [dell_force10](dell_force10.md) | ✅ | ✅ | - | - | |
| [dell_powerconnect](dell_powerconnect.md) | ✅ | ✅ | - | - | |
| [dlink_ds](dlink_ds.md) | ✅ | ✅ | - | - | |
| [edgecore](edgecore.md) | ✅ | ⚠️ | - | - | Linux ベース NOS（SONiC）。Netmiko が enable モード昇格で `sudo -s` を送信する。SIMNOS は sudo 未対応。手動 `enable` 後に show コマンドは動作。v2.2.0 で追加 |
| [eltex](eltex.md) | ✅ | ✅ | - | - | |
| [ericsson_ipos](ericsson_ipos.md) | ✅ | ⚠️ | - | - | Netmiko が `administrator` を送信し `secret`（enable パスワード）を要求する。SIMNOS は enable secret 未対応。show コマンドは enable なしで動作。 |
| [extreme_exos](extreme_exos.md) | ✅ | ✅ | - | - | |
| [extreme_slxos](extreme_slxos.md) | ✅ | ✅ | - | - | enable モードなし（常に特権モード）。v2.2.0 で追加 |
| [fortinet](fortinet.md) | ✅ | ✅ | - | - | |
| [hp_comware](hp_comware.md) | ✅ | ⚠️ | - | - | Netmiko が config モード遷移で `system-view` を送信するが、SIMNOS にこのコマンドがない。show コマンドは正常に動作。 |
| [hp_procurve](hp_procurve.md) | ✅ | ✅ | - | - | |
| [huawei_smartax](huawei_smartax.md) | ✅ | ⚠️ | - | - | callable コマンド（`return`/`disable`）がプロンプトを動的に変更するため、Netmiko が ReadTimeout になる。 |
| [huawei_vrp](huawei_vrp.md) | ✅ | ✅ | - | - | |
| [ipinfusion_ocnos](ipinfusion_ocnos.md) | ✅ | ✅ | - | - | |
| [juniper_junos](juniper_junos.md) | ✅ | ✅ | - | - | |
| [juniper_screenos](juniper_screenos.md) | ✅ | ✅ | - | - | |
| [linux](linux.md) | ✅ | ⚠️ | - | - | Linux ベース NOS。Netmiko が enable モード昇格で `sudo -s` を送信する。SIMNOS は sudo 未対応。手動 `enable` 後に show コマンドは動作。 |
| [mikrotik_routeros](mikrotik_routeros.md) | ✅ | ✅ | - | - | |
| [oneaccess_oneos](oneaccess_oneos.md) | ✅ | ✅ | - | - | ONEOS5/6 自動検出対応。v2.2.0 で追加 |
| [paloalto_panos](paloalto_panos.md) | ✅ | ✅ | - | - | enable モードなし（PAN-OS は全コマンド `>` で実行）。 |
| [ruckus_fastiron](ruckus_fastiron.md) | ✅ | ✅ | - | - | |
| [ubiquiti_edgerouter](ubiquiti_edgerouter.md) | ✅ | ✅ | - | - | |
| [ubiquiti_edgeswitch](ubiquiti_edgeswitch.md) | ✅ | ✅ | - | - | |
| [vyatta_vyos](vyatta_vyos.md) | ✅ | ✅ | - | - | |
| [watchguard_firebox](watchguard_firebox.md) | ✅ | ✅ | - | - | enable モードなし。v2.2.0 で追加 |
| [yamaha](yamaha.md) | ✅ | ⚠️ | - | - | Netmiko が `enable` を送信し `secret`（enable パスワード）を要求する。SIMNOS は enable secret 未対応。show コマンドは enable なしで動作。 |
| [zte_zxros](zte_zxros.md) | ✅ | ✅ | - | - | v2.2.0 で追加 |
| [zyxel_os](zyxel_os.md) | ✅ | ✅ | - | - | |
