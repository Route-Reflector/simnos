# Platforms

The following platforms are supported by SIMNOS. Each platform has been tested for SSH login and Netmiko compatibility.

## Compatibility Legend

| Symbol | Meaning |
|:---:|---|
| ✅ | Verified working |
| ⚠️ | Limited — see Notes for details |
| `-` | Not yet tested |

!!! note
    If you encounter any issues with a platform, please open an issue on the [GitHub repository](https://github.com/Route-Reflector/simnos/issues).

## Available Platforms

| Platform | SSH | Netmiko | Scrapli | Ansible | Notes |
|---|:---:|:---:|:---:|:---:|---|
| [alcatel_aos](alcatel_aos.md) | ✅ | ✅ | - | - | |
| [alcatel_sros](alcatel_sros.md) | ✅ | ⚠️ | - | - | Netmiko sends `enable-admin` which requires `secret` (enable password). SIMNOS does not support enable secret. Show commands work without enable. |
| [allied_telesis_awplus](allied_telesis_awplus.md) | ✅ | ✅ | - | - | |
| [arista_eos](arista_eos.md) | ✅ | ✅ | - | - | |
| [aruba_aoscx](aruba_aoscx.md) | ✅ | ✅ | - | - | New in v2.2.0 |
| [aruba_os](aruba_os.md) | ✅ | ✅ | - | - | |
| [avaya_ers](avaya_ers.md) | ✅ | ✅ | - | - | |
| [avaya_vsp](avaya_vsp.md) | ✅ | ✅ | - | - | |
| [broadcom_icos](broadcom_icos.md) | ✅ | ✅ | - | - | |
| [brocade_fastiron](brocade_fastiron.md) | ✅ | ✅ | - | - | |
| [brocade_netiron](brocade_netiron.md) | ✅ | ✅ | - | - | |
| [checkpoint_gaia](checkpoint_gaia.md) | ✅ | ✅ | - | - | |
| [ciena_saos](ciena_saos.md) | ✅ | ✅ | - | - | |
| [cisco_apic](cisco_apic.md) | ✅ | ⚠️ | - | - | Linux-based NOS. Netmiko sends `sudo -s` for enable mode escalation. SIMNOS does not support sudo. Show commands work after manual `enable`. New in v2.2.0 |
| [cisco_asa](cisco_asa.md) | ✅ | ✅ | - | - | |
| [cisco_ftd](cisco_ftd.md) | ✅ | ✅ | - | - | |
| [cisco_ios](cisco_ios.md) | ✅ | ✅ | - | - | |
| [cisco_nxos](cisco_nxos.md) | ✅ | ✅ | - | - | |
| [cisco_s300](cisco_s300.md) | ✅ | ✅ | - | - | |
| [cisco_viptela](cisco_viptela.md) | ✅ | ✅ | - | - | New in v2.2.0 |
| [cisco_wlc_ssh](cisco_wlc_ssh.md) | ✅ | ✅ | - | - | New in v2.2.0 |
| [cisco_xr](cisco_xr.md) | ✅ | ✅ | - | - | |
| [dell_force10](dell_force10.md) | ✅ | ✅ | - | - | |
| [dell_powerconnect](dell_powerconnect.md) | ✅ | ✅ | - | - | |
| [dlink_ds](dlink_ds.md) | ✅ | ✅ | - | - | |
| [edgecore](edgecore.md) | ✅ | ⚠️ | - | - | Linux-based NOS (SONiC). Netmiko sends `sudo -s` for enable mode escalation. SIMNOS does not support sudo. Show commands work after manual `enable`. New in v2.2.0 |
| [eltex](eltex.md) | ✅ | ✅ | - | - | |
| [ericsson_ipos](ericsson_ipos.md) | ✅ | ⚠️ | - | - | Netmiko sends `administrator` which requires `secret` (enable password). SIMNOS does not support enable secret. Show commands work without enable. |
| [extreme_exos](extreme_exos.md) | ✅ | ✅ | - | - | |
| [extreme_slxos](extreme_slxos.md) | ✅ | ✅ | - | - | No enable mode (always privileged). New in v2.2.0 |
| [fortinet](fortinet.md) | ✅ | ✅ | - | - | |
| [hp_comware](hp_comware.md) | ✅ | ⚠️ | - | - | Netmiko sends `system-view` to enter config mode, but SIMNOS does not have this command. Show commands work normally. |
| [hp_procurve](hp_procurve.md) | ✅ | ✅ | - | - | |
| [huawei_smartax](huawei_smartax.md) | ✅ | ⚠️ | - | - | Has callable commands (`return`/`disable`) that dynamically change the prompt, causing Netmiko ReadTimeout. |
| [huawei_vrp](huawei_vrp.md) | ✅ | ✅ | - | - | |
| [ipinfusion_ocnos](ipinfusion_ocnos.md) | ✅ | ✅ | - | - | |
| [juniper_junos](juniper_junos.md) | ✅ | ✅ | - | - | |
| [juniper_screenos](juniper_screenos.md) | ✅ | ✅ | - | - | |
| [linux](linux.md) | ✅ | ⚠️ | - | - | Linux-based NOS. Netmiko sends `sudo -s` for enable mode escalation. SIMNOS does not support sudo. Show commands work after manual `enable`. |
| [mikrotik_routeros](mikrotik_routeros.md) | ✅ | ✅ | - | - | |
| [oneaccess_oneos](oneaccess_oneos.md) | ✅ | ✅ | - | - | ONEOS5/6 auto-detection supported. New in v2.2.0 |
| [paloalto_panos](paloalto_panos.md) | ✅ | ✅ | - | - | No enable mode (PAN-OS uses `>` for all operational commands). |
| [ruckus_fastiron](ruckus_fastiron.md) | ✅ | ✅ | - | - | |
| [ubiquiti_edgerouter](ubiquiti_edgerouter.md) | ✅ | ✅ | - | - | |
| [ubiquiti_edgeswitch](ubiquiti_edgeswitch.md) | ✅ | ✅ | - | - | |
| [vyatta_vyos](vyatta_vyos.md) | ✅ | ✅ | - | - | |
| [watchguard_firebox](watchguard_firebox.md) | ✅ | ✅ | - | - | No enable mode. New in v2.2.0 |
| [yamaha](yamaha.md) | ✅ | ⚠️ | - | - | Netmiko sends `enable` which requires `secret` (enable password). SIMNOS does not support enable secret. Show commands work without enable. |
| [zte_zxros](zte_zxros.md) | ✅ | ✅ | - | - | New in v2.2.0 |
| [zyxel_os](zyxel_os.md) | ✅ | ✅ | - | - | |
