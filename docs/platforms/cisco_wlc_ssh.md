# cisco_wlc_ssh


!!! warning
    This is automatically generated. In case of any issues,
    please refer to the source code or, even better,
    open an issue on the GitHub repository. Thanks! 🤗📖
## Platforms:

## Commands

### enable

**Output:** None

**Help:** enter enable mode

**Prompt:**
- {base_prompt}>

### show 802.11a

**Output:**
```
'\n802.11a Network.................................. Disabled\n11acSupport...................................... Enabled\n11nSupport....................................... Enabled\n      802.11a Low Band........................... Enabled\n      802.11a Mid Band........................... Enabled\n      802.11a High Band.......................... Enabled\n802.11a Operational Rates\n    802.11a 6M Rate.............................. Mandatory\n    802.11a 9M Rate.............................. Supported\n    802.11a 12M Rate............................. Mandatory\n    802.11a 18M Rate............................. Supported\n    802.11a 24M Rate............................. Mandatory\n    802.11a 36M Rate............................. Supported\n    802.11a 48M Rate............................. Supported\n    802.11a 54M Rate............................. Supported\n802.11n MCS Settings:\n    MCS 0........................................ Supported\n    MCS 1........................................ Supported\n    MCS 2........................................ Supported\n    MCS 3........................................ Supported\n    MCS 4........................................ Supported\n    MCS 5........................................ Supported\n    MCS 6........................................ Supported\n    MCS 7........................................ Supported\n    MCS 8........................................ Supported\n    MCS 9........................................ Supported\n    MCS 10....................................... Supported\n    MCS 11....................................... Supported\n    MCS 12....................................... Supported\n    MCS 13....................................... Supported\n    MCS 14....................................... Supported\n    MCS 15....................................... Supported\n    MCS 16....................................... Supported\n    MCS 17....................................... Supported\n    MCS 18....................................... Supported\n    MCS 19....................................... Supported\n    MCS 20....................................... Supported\n    MCS 21....................................... Supported\n    MCS 22....................................... Supported\n    MCS 23....................................... Supported\n    MCS 24....................................... Supported\n    MCS 25....................................... Supported\n    MCS 26....................................... Supported\n    MCS 27....................................... Supported\n    MCS 28....................................... Supported\n    MCS 29....................................... Supported\n    MCS 30....................................... Supported\n    MCS 31....................................... Supported\n802.11ac MCS Settings:\n    Nss=1: MCS 0-9 .............................. Supported\n    Nss=2: MCS 0-9 .............................. Supported\n    Nss=3: MCS 0-9 .............................. Supported\n    Nss=4: MCS 0-7 .............................. Supported\n802.11n Status:\n    A-MPDU Tx:\n        Priority 0............................... Enabled\n        Priority 1............................... Enabled\n        Priority 2............................... Enabled\n        Priority 3............................... Enabled\n        Priority 4............................... Enabled\n        Priority 5............................... Enabled\n        Priority 6............................... Disabled\n        Priority 7............................... Disabled\n        Aggregation scheduler.................... Enabled\n        Frame Burst.............................. Automatic\n            Realtime Timeout..................... 10\n            Non Realtime Timeout................. 200\n    A-MSDU Tx:\n        Priority 0............................... Enabled\n        Priority 1............................... Enabled\n        Priority 2............................... Enabled\n        Priority 3............................... Enabled\n        Priority 4............................... Enabled\n        Priority 5............................... Enabled\n        Priority 6............................... Disabled\n        Priority 7............................... Disabled\n    A-MSDU Max Subframes ........................ 3\n    A-MSDU MAX Length ........................... 8k\n    Rifs Rx ..................................... Enabled\n    Guard Interval .............................. Any\nBeacon Interval.................................. 100\nCF Pollable mandatory............................ Disabled\nCF Poll Request mandatory........................ Disabled\nCFP Period....................................... 4\nCFP Maximum Duration............................. 60\nDefault Channel.................................. 36\nDefault Tx Power Level........................... 1\nDTPC  Status..................................... Enabled\nFragmentation Threshold.......................... 2346\nRSSI Low Check................................... Disabled\nRSSI Threshold................................... -80\nTI Threshold..................................... -50\nLegacy Tx Beamforming setting.................... Disabled\nTraffic Stream Metrics Status.................... Disabled\nExpedited BW Request Status...................... Disabled\nWorld Mode....................................... Enabled\ndfs-peakdetect................................... Enabled\nEDCA profile type................................ default-wmm\nVoice MAC optimization status.................... Disabled\nCall Admission Control (CAC) configuration\nVoice AC:\n   Voice AC - Admission control (ACM)............ Disabled\n   Voice Stream-Size............................. 84000\n   Voice Max-Streams............................. 2\n   Voice max RF bandwidth........................ 75\n   Voice reserved roaming bandwidth.............. 6\n   Voice CAC Method ............................. Load-Based\n   Voice tspec inactivity timeout................ Disabled\n CAC SIP-Voice configuration\n   SIP based CAC ................................ Disabled\n   SIP Codec Type ............................... CODEC_TYPE_G711\n   SIP call bandwidth ........................... 64\n   SIP call bandwith sample-size ................ 20\nVideo AC:\n   Video AC - Admission control (ACM)............ Disabled\n   Video max RF bandwidth........................ 0\n   Video reserved roaming bandwidth.............. 0\n   Video load-based CAC mode..................... Disabled\n   Video CAC Method ............................. Static\n CAC SIP-Video Configuration\n   SIP based CAC ................................ Disabled\n   Best-effort AC - Admission control (ACM)...... Disabled\n   Background AC - Admission control (ACM)....... Disabled\nMaximum Number of Clients per AP Radio........... 200\n'
```

**Help:** execute the command "show 802.11a"

**Prompt:**
- {base_prompt}>
- {base_prompt}#

### show 802.11a cleanair config

**Output:**
```
'\nClean Air Solution............................... Disabled\nAir Quality Settings:\n    Air Quality Reporting........................ Enabled\n    Air Quality Reporting Period (min)........... 15\n    Air Quality Alarms........................... Enabled\n      Air Quality Alarm Threshold................ 35\n      Unclassified Interference.................. Disabled\n      Unclassified Severity Threshold............ 20\nInterference Device Settings:\n    Interference Device Reporting................ Enabled\n    Interference Device Types:\n        TDD Transmitter.......................... Enabled\n        Jammer................................... Enabled\n        Continuous Transmitter................... Enabled\n        DECT-like Phone.......................... Enabled\n        Video Camera............................. Enabled\n        WiFi Inverted............................ Enabled\n        WiFi Invalid Channel..................... Enabled\n        SuperAG.................................. Enabled\n        Canopy................................... Enabled\n        WiMax Mobile............................. Enabled\n        WiMax Fixed.............................. Enabled\n    Interference Device Alarms................... Enabled\n    Interference Device Types Triggering Alarms:\n        TDD Transmitter.......................... Disabled\n        Jammer................................... Enabled\n        Continuous Transmitter................... Disabled\n        DECT-like Phone.......................... Disabled\n        Video Camera............................. Disabled\n        WiFi Inverted............................ Enabled\n        WiFi Invalid Channel..................... Enabled\n        SuperAG.................................. Disabled\n        Canopy................................... Disabled\n        WiMax Mobile............................. Disabled\n        WiMax Fixed.............................. Disabled\nAdditional Clean Air Settings:\n    CleanAir ED-RRM State........................ Disabled\n    CleanAir ED-RRM Sensitivity.................. Medium\n    CleanAir ED-RRM Custom Threshold............. 50\n    CleanAir Rogue Contribution.................. Disabled\n    CleanAir Rogue Duty-Cycle Threshold.......... 80\n    CleanAir Persistent Devices state............ Disabled\n    CleanAir Persistent Device Propagation....... Disabled\n'
```

**Help:** execute the command "show 802.11a cleanair config"

**Prompt:**
- {base_prompt}>
- {base_prompt}#

### show advanced 802.11a channel

**Output:**
```
'\n Leader Automatic Channel Assignment\n  Channel Assignment Mode........................ OFF\n  Channel Update Interval........................ 600 seconds\n  Anchor time (Hour of the day).................. 0 \n  Update Contribution\n    Noise........................................ Enable\n    Interference................................. Enable\n    Load......................................... Disable\n    Device Aware................................. Disable\n  CleanAir Event-driven RRM option............... Disabled\n  Channel Assignment Leader...................... Cisco_lab (192.168.1.11) (::)\n  Last Run....................................... 448 seconds ago\n  Last Run Time.................................. 0 seconds\n  DCA Sensitivity Level.......................... MEDIUM (15 dB)\n  DCA 802.11n/ac Channel Width................... 20 MHz\n  DCA Minimum Energy Limit....................... -95 dBm\n  Channel Energy Levels \n    Minimum...................................... unknown\n    Average...................................... unknown\n    Maximum...................................... unknown\n  Channel Dwell Times \n    Minimum...................................... unknown\n    Average...................................... unknown\n    Maximum...................................... unknown\n  802.11a 5 GHz Auto-RF Channel List\n    Allowed Channel List......................... 36,40,44,48,52,56,60,64,100,\n                                                  104,108,112,116,120,124,128,\n                                                  132,136,140,144,149,153,157,\n                                                  161\n    Unused Channel List.......................... 165\n  802.11a 4.9 GHz Auto-RF Channel List\n    Allowed Channel List......................... \n    Unused Channel List.......................... 1,2,3,4,5,6,7,8,9,10,11,12,\n                                                  13,14,15,16,17,18,19,20,21,\n                                                  22,23,24,25,26\n  DCA Outdoor AP option.......................... Disabled\n'
```

**Help:** execute the command "show advanced 802.11a channel"

**Prompt:**
- {base_prompt}>
- {base_prompt}#

### show ap config general

**Output:**
```
'Cisco AP Identifier.............................. 111\nCisco AP Name.................................... AP_test_01\nCountry code..................................... IT  - Italy\nRegulatory Domain allowed by Country............. 802.11bg:-E     802.11a:-E\nAP Country code.................................. IT  - Italy\nAP Regulatory Domain............................. -E\nSwitch Port Number .............................. 8\nMAC Address...................................... 00:62:ec:01:02:03\nIP Address Configuration......................... Static IP assigned\nIP Address....................................... 10.1.1.1\nIP NetMask....................................... 255.255.255.0\nGateway IP Addr.................................. 10.1.1.254\nDomain........................................... \nName Server...................................... 192.168.1.1\nNAT External IP Address.......................... None\nCAPWAP Path MTU.................................. 1485\nDHCP Release Override............................ Disabled \nTelnet State..................................... Globally Enabled\nSsh State........................................ Globally Enabled\nCisco AP Location................................ default location\nCisco AP Floor Label............................. 0\nCisco AP Group Name.............................. GROUP_PE\nPrimary Cisco Switch Name........................ WLC\nPrimary Cisco Switch IP Address.................. 10.2.2.2\nSecondary Cisco Switch Name...................... \nSecondary Cisco Switch IP Address................ Not Configured\nTertiary Cisco Switch Name....................... \nTertiary Cisco Switch IP Address................. Not Configured\nAdministrative State ............................ ADMIN_ENABLED\nOperation State ................................. REGISTERED\nMirroring Mode .................................. Disabled\nAP Mode ......................................... FlexConnect\nPublic Safety ................................... Disabled \nAP SubMode ...................................... Not Configured\nRogue Detection ................................. Enabled\nAP Vlan Trunking ................................ Enabled  (Inherited) \nAP Native Vlan ID: .............................. 1 (Inherited) \nRemote AP Debug ................................. Disabled\nLogging trap severity level ..................... emergencies\nLogging syslog facility ......................... kern\nS/W  Version .................................... 8.2.164.0\nBoot  Version ................................... 15.2.4.5\nMini IOS Version ................................ 8.2.100.0\nStats Reporting Period .......................... 180\nStats Collection Mode ........................... normal\nRadio Core Mode ................................. Disabled\nSlub Debug Mode ................................. Disabled\nLED State........................................ Enabled\nPoE Pre-Standard Switch.......................... Disabled\nPoE Power Injector MAC Addr...................... Disabled\nPower Type/Mode.................................. PoE/Medium Power (15.4 W)\nNumber Of Slots.................................. 2 \nAP Model......................................... AIR-CAP2702E-E-K9\nAP Image......................................... C2700-K9W8-M\nIOS Version...................................... 15.3(3)JC9$\nReset Button..................................... Enabled\nAP Serial Number................................. FCEDDCCBBAA\nAP Certificate Type.............................. Manufacture Installed\nAP LAG Configuration Status ..................... Disabled\nLAG Support for AP .............................. No\nNative Vlan Inheritance: ........................ AP\nFlexConnect Vlan mode :.......................... Enabled\n        Native ID :..................................... 1\n        WLAN 13 :....................................... 3 (Wlan-Specific)\n        WLAN 46 :....................................... 13 (Wlan-Specific)\n        WLAN 70 :....................................... 254 (Wlan-Specific)\nFlexConnect VLAN ACL Mappings\nFlexConnect Group................................ Not a member of any group\nGroup VLAN ACL Mappings\n\n\nGroup VLAN Name to Id Mappings\n Template in Modified State - apply it to see mappings\n\nAP-Specific FlexConnect Policy ACLs :\nL2Acl Configuration ............................. Not Available\nFlexConnect Local-Split ACLs :\n\nWLAN ID   PROFILE NAME                       ACL                                 TYPE\n-------  --------------------------------   ---------------------------------   -------\n\n Flexconnect Central-Dhcp Values :\n\nWLAN ID   PROFILE NAME                         Central-Dhcp      DNS Override      Nat-Pat     Type\n-------  ---------------------------------    --------------    --------------    ---------   ------   \n  13       WLAN_13                                  False             False          False      Wlan  \n  46       WLAN_46                                  False             False          False      Wlan  \n  70       WLAN_70                                  False             False          False      Wlan\n\nFlex AVC visibility Configurations.............. \n\nWlanId  PROFILE NAME                     Inherit-level Visibility       Flex Avc-profile\n------- -------------------------------- ------------- ---------- --------------------------------\n13         WLAN_13                          wlan-spec     disable    none                            \n46         WLAN_46                          wlan-spec     disable    none                            \n70         WLAN_70                          wlan-spec     enable     none                            \n\nFlexConnect Backup Auth Radius Servers :\n Primary Radius Server........................... Disabled\n Secondary Radius Server......................... Disabled\nAP User Mode..................................... AUTOMATIC\nAP User Name..................................... admin\nAP Dot1x User Mode............................... Not Configured\nAP Dot1x User Name............................... Not Configured\nCisco AP system logging host..................... 255.255.255.255\nAP Up Time....................................... 248 days, 07 h 09 m 00 s\nAP LWAPP Up Time................................. 165 days, 11 h 03 m 33 s\nJoin Date and Time............................... Wed Jan 17 10:07:12 2018\nJoin Taken Time.................................. 0 days, 00 h 05 m 36 s\nMemory Type...................................... DDR3\nMemory Size...................................... 11839 KBytes\nCPU Type......................................... PowerPC CPU at 800Mhz, revision number 0x2151\nFlash Type....................................... Onboard Flash\nFlash Size....................................... 1564 KBytes\nGPS Present...................................... NO\nEthernet Vlan Tag................................ Disabled\nEthernet Port Duplex............................. Auto\nEthernet Port Speed.............................. Auto\nAP Link Latency.................................. Disabled\nRogue Detection.................................. Enabled\nAP TCP MSS Adjust................................ Disabled\nHotspot Venue Group.............................. Unspecified\nHotspot Venue Type............................... Unspecified\n      DNS server IP ............................. 192.168.1.1\n'
```

**Help:** execute the command "show ap config general"

**Prompt:**
- {base_prompt}>
- {base_prompt}#

### show ap image all

**Output:**
```
'\nTotal number of APs.............................. 2\nNumber of APs\n\tInitiated....................................... 0\n\tDownloading..................................... 0\n\tPredownloading.................................. 0\n\tCompleted predownloading........................ 0\n\tNot Supported................................... 0\n\tFailed to Predownload........................... 0\n\n                                                 Predownload     Predownload                                  Flexconnect\nAP Name            Primary Image  Backup Image   Status          Version        Next Retry Time  Retry Count  Predownload\n------------------ -------------- -------------- --------------- -------------- ---------------- ------------ --------------\nESP1-05-NAP01      8.5.161.0      0.0.0.0        None            None           NA               NA                       \nESP1-05-NAP02      8.5.161.0      0.0.0.0        None            None           NA               NA                       \n\n'
```

**Help:** execute the command "show ap image all"

**Prompt:**
- {base_prompt}>
- {base_prompt}#

### show ap summary

**Output:**
```
'\nNumber of APs.................................... 2\n \nGlobal AP User Name.............................. admin\nGlobal AP Dot1x User Name........................ Not Configured\nGlobal AP Dot1x EAP Method....................... EAP-FAST\n \nAP Name                         Slots  AP Model              Ethernet MAC       Location              Country     IP Address       Clients  DSE Location \n------------------------------  -----  --------------------  -----------------  --------------------  ----------  ---------------  -------  --------------\n2800-Default                    3      AIR-AP2802I-E-K9       c0:ff:ee:c0:ff:ee  default location      IT          172.25.81.216    0        [0 ,0 ,0 ]\n2700-Server                     2      AIR-CAP2702E-E-K9      ca:fe:ca:fe:ca:fe  Server room           IT          172.25.81.221    0        [0 ,0 ,0 ]\n'
```

**Help:** execute the command "show ap summary"

**Prompt:**
- {base_prompt}>
- {base_prompt}#

### show band-select

**Output:**
```
'Band Select Probe Response....................... per WLAN enabling\n   Cycle Count................................... 2 cycles\n   Cycle Threshold............................... 200 milliseconds\n   Age Out Suppression........................... 20 seconds\n   Age Out Dual Band............................. 60 seconds\n   Client RSSI................................... -80 dBm\n   Client Mid RSSI............................... -80 dBm\n'
```

**Help:** execute the command "show band-select"

**Prompt:**
- {base_prompt}>
- {base_prompt}#

### show boot

**Output:**
```
'Primary Boot Image............................... 8.10.183.0 (default) (active)\nBackup Boot Image................................ 8.8.125.0\n'
```

**Help:** execute the command "show boot"

**Prompt:**
- {base_prompt}>
- {base_prompt}#

### show cdp neighbors detail

**Output:**
```
'\n-------------------------\nDevice ID: AAA.pizza.com(FXS1828Q2JH)\nEntry address(es):\n  IP address: 1.2.3.4\nPlatform: N77-C7706,  Capabilities: Router Switch IGMP\nInterface: GigabitEthernet0/0/2,  Port ID (outgoing port): Ethernet1/15\nHoldtime : 127 sec\n\nVersion :\nCisco Nexus Operating System (NX-OS) Software, Version 6.2(10)\n\nAdvertisement version: 2\nDuplex: Full\n\n-------------------------\nDevice ID: BBB.beer.com\nEntry address(es):\n  IP address: 172.5.6.7\nPlatform: cisco WS-C3750G-12S,  Capabilities: Router Switch IGMP\nInterface: GigabitEthernet0/0/7,  Port ID (outgoing port): GigabitEthernet1/0/11\nHoldtime : 162 sec\n\n\nVersion :\nCisco IOS Software, C3750 Software (C3750-IPSERVICESK9-M), Version 12.2(55)SE11, RELEASE SOFTWARE (fc3) Technical Support: http://www.cisco.com/techsupport Copyright (c) 1986-2016 by Cisco Systems, Inc. Compiled Wed 17-Aug-16 13:28 by prod_rel_team\n\nAdvertisement version: 2\nDuplex: Full\n\n-------------------------\nDevice ID: CCC.cake.com\nEntry address(es):\n  IP address: 172.9.10.11\nPlatform: cisco WS-C3750G-12S,  Capabilities: Router Switch IGMP\nInterface: GigabitEthernet0/0/8,  Port ID (outgoing port): GigabitEthernet1/0/1\nHoldtime : 162 sec\n\nVersion :\nCisco IOS Software, C3750 Software (C3750-IPSERVICESK9-M), Version 12.2(55)SE11, RELEASE SOFTWARE (fc3) Technical Support: http://www.cisco.com/techsupport Copyright (c) 1986-2016 by Cisco Systems, Inc. Compiled Wed 17-Aug-16 13:28 by prod_rel_team\n\nAdvertisement version: 2\nDuplex: Full\n\n'
```

**Help:** execute the command "show cdp neighbors detail"

**Prompt:**
- {base_prompt}>
- {base_prompt}#

### show client detail

**Output:**
```
'Client MAC Address...............................04:67:f8:63:2a:cfb\nClient Username ................................. N/A\nAP MAC Address................................... 10:e0:1d:f0:86:91\nAP Name.......................................... APf-16\nAP radio slot Id................................. 1  \nClient State..................................... Associated\nClient User Group................................ \nClient NAC OOB State............................. Access\nWireless LAN Id.................................. 4  \nWireless LAN Network Name (SSID)................. SINGLE\nWireless LAN Profile Name........................ device\nHotspot (802.11u)................................ Not Supported\nBSSID............................................ 80:e0:1d:f0:88:9a  \nConnected For ................................... 15688 secs\nChannel.......................................... 157\nIP Address....................................... 10.10.10.110\nGateway Address.................................. Unknown\nNetmask.......................................... Unknown\nAssociation Id................................... 14 \nAuthentication Algorithm......................... Open System\nReason Code...................................... 1  \nStatus Code...................................... 0  \nSession Timeout.................................. 28800\nClient CCX version............................... No CCX support\nQoS Level........................................ Silver\nAvg data Rate.................................... 0\nBurst data Rate.................................. 0\nAvg Real time data Rate.......................... 0\nBurst Real Time data Rate........................ 0\n802.1P Priority Tag.............................. disabled\nCTS Security Group Tag........................... Not Applicable\nKTS CAC Capability............................... No\nQos Map Capability............................... No\nWMM Support...................................... Enabled\n  APSD ACs.......................................  BK  BE  VI  VO \nCurrent Rate..................................... m8 ss2\nSupported Rates.................................. 18.0,24.0,36.0,48.0,54.0\nMobility State................................... Local\nMobility Move Count.............................. 0\nSecurity Policy Completed........................ Yes\nPolicy Manager State............................. RUN\nAudit Session ID................................. 05964b0a0014fc2acc4c7e5c\nAAA Role Type.................................... none\nLocal Policy Applied............................. none\nIPv4 ACL Name.................................... none\nFlexConnect ACL Applied Status................... Unavailable\nIPv4 ACL Applied Status.......................... Unavailable\nIPv6 ACL Name.................................... none\nIPv6 ACL Applied Status.......................... Unavailable\nLayer2 ACL Name.................................. none\nLayer2 ACL Applied Status........................ Unavailable\nClient Type...................................... SimpleIP\nmDNS Status...................................... Enabled\nmDNS Profile Name................................ default-mdns-profile\nNo. of mDNS Services Advertised.................. 0\nPolicy Type...................................... WPA2\nAuthentication Key Management.................... PSK\nEncryption Cipher................................ CCMP (AES)\nProtected Management Frame ...................... No\nManagement Frame Protection...................... No\nEAP Type......................................... Unknown\nInterface........................................ qa_mobile\nVLAN............................................. 218\nQuarantine VLAN.................................. 0\nAccess VLAN...................................... 218\nLocal Bridging VLAN.............................. 218\nClient Capabilities:\n      CF Pollable................................ Not implemented\n      CF Poll Request............................ Not implemented\n      Short Preamble............................. Not implemented\n      PBCC....................................... Not implemented\n      Channel Agility............................ Not implemented\n      Listen Interval............................ 20\n      Fast BSS Transition........................ Not implemented\n      11v BSS Transition......................... Not implemented\nClient Wifi Direct Capabilities:\n      WFD capable................................ No\n      Manged WFD capable......................... No\n      Cross Connection Capable................... No\n      Support Concurrent Operation............... No\nFast BSS Transition Details:\nClient Statistics:\n      Number of Bytes Received................... 78808\n      Number of Bytes Sent....................... 585125\n      Total Number of Bytes Sent................. 585125\n      Total Number of Bytes Recv................. 78808\n      Number of Bytes Sent (last 90s)............ 64\n      Number of Bytes Recv (last 90s)............ 292\n      Number of Packets Received................. 761\n      Number of Packets Sent..................... 763\n      Number of Interim-Update Sent.............. 0\n      Number of EAP Id Request Msg Timeouts...... 0\n      Number of EAP Id Request Msg Failures...... 0\n      Number of EAP Request Msg Timeouts......... 0\n      Number of EAP Request Msg Failures......... 0\n      Number of EAP Key Msg Timeouts............. 0\n      Number of EAP Key Msg Failures............. 0\n      Number of Data Retries..................... 317\n      Number of RTS Retries...................... 0\n      Number of Duplicate Received Packets....... 4\n      Number of Decrypt Failed Packets........... 0\n      Number of Mic Failured Packets............. 0\n      Number of Mic Missing Packets.............. 0\n      Number of RA Packets Dropped............... 0\n      Number of Policy Errors.................... 0\n      Radio Signal Strength Indicator............ -51 dBm\n      Signal to Noise Ratio...................... 43 dB\nClient Rate Limiting Statistics:\n      Number of Data Packets Received............ 0\n      Number of Data Rx Packets Dropped.......... 0\n      Number of Data Bytes Received.............. 0\n      Number of Data Rx Bytes Dropped............ 0\n      Number of Realtime Packets Received........ 0\n      Number of Realtime Rx Packets Dropped...... 0\n      Number of Realtime Bytes Received.......... 0\n      Number of Realtime Rx Bytes Dropped........ 0\n      Number of Data Packets Sent................ 0\n      Number of Data Tx Packets Dropped.......... 0\n      Number of Data Bytes Sent.................. 0\n      Number of Data Tx Bytes Dropped............ 0\n      Number of Realtime Packets Sent............ 0\n      Number of Realtime Tx Packets Dropped...... 0\n      Number of Realtime Bytes Sent.............. 0\n      Number of Realtime Tx Bytes Dropped........ 0\nNearby AP Statistics:\n      AP2F-29(slot 0)\n        antenna0: 6 secs ago..................... -72 dBm\n        antenna1: 6 secs ago..................... -75 dBm\n      AP2F-29(slot 1)\n        antenna0: 5 secs ago..................... -77 dBm\n        antenna1: 5 secs ago..................... -80 dBm\n      AP2F-23(slot 0)\n        antenna0: 5 secs ago..................... -86 dBm\n        antenna1: 5 secs ago..................... -87 dBm\n      AP2F-23(slot 1)\n        antenna0: 6 secs ago..................... -90 dBm\n        antenna1: 6 secs ago..................... -91 dBm\n      AP3f-10(slot 1)\n        antenna0: 3 secs ago..................... -78 dBm\n        antenna1: 3 secs ago..................... -79 dBm\n      AP3f-11(slot 1)\n        antenna0: 5 secs ago..................... -78 dBm\n        antenna1: 5 secs ago..................... -82 dBm\n      AP3f-17(slot 0)\n        antenna0: 6 secs ago..................... -57 dBm\n        antenna1: 6 secs ago..................... -60 dBm\n      AP3f-17(slot 1)\n        antenna0: 6 secs ago..................... -60 dBm\n        antenna1: 6 secs ago..................... -57 dBm\n      AP2F-27(slot 1)\n        antenna0: 6 secs ago..................... -83 dBm\n        antenna1: 6 secs ago..................... -80 dBm\n      AP3f-13(slot 0)\n        antenna0: 6 secs ago..................... -72 dBm\n        antenna1: 6 secs ago..................... -76 dBm\n      AP3f-13(slot 1)\n        antenna0: 6 secs ago..................... -74 dBm\n        antenna1: 6 secs ago..................... -70 dBm\n      AP3f-12(slot 0)\n        antenna0: 5 secs ago..................... -79 dBm\n        antenna1: 5 secs ago..................... -79 dBm\n      AP3f-12(slot 1)\n        antenna0: 6 secs ago..................... -74 dBm\n        antenna1: 6 secs ago..................... -75 dBm\n      AP2F-28(slot 0)\n        antenna0: 5 secs ago..................... -86 dBm\n        antenna1: 5 secs ago..................... -87 dBm\n      AP2F-28(slot 1)\n        antenna0: 5 secs ago..................... -88 dBm\n        antenna1: 5 secs ago..................... -82 dBm\n      AP2F-25(slot 1)\n        antenna0: 6 secs ago..................... -87 dBm\n        antenna1: 6 secs ago..................... -88 dBm\n      AP3f-15(slot 0)\n        antenna0: 6 secs ago..................... -74 dBm\n        antenna1: 6 secs ago..................... -71 dBm\n      AP3f-15(slot 1)\n        antenna0: 6 secs ago..................... -77 dBm\n        antenna1: 6 secs ago..................... -69 dBm\n      AP3f-14(slot 1)\n        antenna0: 6 secs ago..................... -73 dBm\n        antenna1: 6 secs ago..................... -71 dBm\n      AP3f-16(slot 0)\n        antenna0: 6 secs ago..................... -67 dBm\n        antenna1: 6 secs ago..................... -65 dBm\n      AP3f-16(slot 1)\n        antenna0: 6 secs ago..................... -51 dBm\n        antenna1: 6 secs ago..................... -57 dBm\nDNS Server details:\n      DNS server IP ............................. 0.0.0.0\n      DNS server IP ............................. 0.0.0.0\nAssisted Roaming Prediction List details:\n\n\n Client Dhcp Required:     False\nAllowed (URL)IP Addresses\n-------------------------\n\nAVC Profile Name: ............................... Internal Wireless AVC\n'
```

**Help:** execute the command "show client detail"

**Prompt:**
- {base_prompt}>
- {base_prompt}#

### show exclusionlist

**Output:**
```
'Manually Disabled Clients\n-------------------------\nMAC Address               Description\n-----------------------   --------------------------------\naa:bb:cc:dd:ee:ff         bad-guy\n00:22:43:cc:ac:2d         request #6aa493\n34:f6:aa:7e:70:3e         ticket #612333\n40:b0:34:99:95:d9         Unkown Device\n\n\nNo dynamically excluded clients.'
```

**Help:** execute the command "show exclusionlist"

**Prompt:**
- {base_prompt}>
- {base_prompt}#

### show flexconnect group summary

**Output:**
```
'FlexConnect Group Summary: Count: 4\nGroup Name            # Aps\n--------------------  --------\n\nFlexCon Group - Grp1              44\nFlexCon Group - Grp2              14\ndefault-flex-group                0\ndefault-flex-group-1826280552     0'
```

**Help:** execute the command "show flexconnect group summary"

**Prompt:**
- {base_prompt}>
- {base_prompt}#

### show interface detailed id

**Output:**
```
'\n\nInterface Name................................... my-interface\nMAC Address...................................... c0:12:43:56:78:90\nIP Address....................................... 8.8.8.8\nIP Netmask....................................... 255.255.254.0\nIP Gateway....................................... 8.8.8.1\nExternal NAT IP State............................ Disabled\nExternal NAT IP Address.......................... 0.0.0.0\nLink Local IPv6 Address.......................... fe80::c012:4356:7890:5643/64\nSTATE ........................................... NONE\nIPv6 Address..................................... ::/128\nSTATE ........................................... NONE\nIPv6 Gateway..................................... ::\nIPv6 Gateway Mac Address......................... 00:00:00:00:00:00\nSTATE ........................................... NONE\nVLAN............................................. 300\nQuarantine-vlan.................................. 0\nNAS-Identifier................................... none\nActive Physical Port............................. LAG (13)\nPrimary Physical Port............................ LAG (13)\nBackup Physical Port............................. Unconfigured\nDHCP Proxy Mode.................................. Global\nPrimary DHCP Server.............................. 1.1.1.1\nSecondary DHCP Server............................ 1.1.1.2\nDHCP Option 82................................... Disabled\nDHCP Option 82 bridge mode insertion............. Disabled\nDHCP Option 6 Opendns Override................... Disabled\nIPv4 ACL......................................... Unconfigured\nmDNS Profile Name................................ Unconfigured\nAP Manager....................................... No\nGuest Interface.................................. No\n3G VLAN.......................................... Disabled\nL2 Multicast..................................... Enabled\n\n'
```

**Help:** execute the command "show interface detailed id"

**Prompt:**
- {base_prompt}>
- {base_prompt}#

### show interface group summary

**Output:**
```
'Interface Group Name             Total Interfaces  Total Wlans  Total AP Groups  Quarantine\n-------------------------------- ----------------  -----------  ---------------  ----------\nintgrp_guest                             1              1              2              No\nintgrp_prod                              1              1              6              No\nintgrp_byod                              1              2              11             No\n'
```

**Help:** execute the command "show interface group summary"

**Prompt:**
- {base_prompt}>
- {base_prompt}#

### show interface summary

**Output:**
```
'\n\n Number of Interfaces.......................... 3\n\nInterface Name                   Port Vlan Id  IP Address      Type    Ap Mgr Guest\n-------------------------------- ---- -------- --------------- ------- ------ -----\nmanagement                       1    untagged 192.168.1.11    Static  Yes    N/A  \nservice-port                     N/A  N/A      11.1.1.1        Static  No     N/A  \nvirtual                          N/A  N/A      1.1.1.1         Static  No     N/A  \n'
```

**Help:** execute the command "show interface summary"

**Prompt:**
- {base_prompt}>
- {base_prompt}#

### show inventory

**Output:**
```
'\nBurned-in MAC Address............................ 70:1F:53:12:34:56\nMaximum number of APs supported.................. 150\nNAME: "Chassis"    , DESCR: "Cisco 3500 Series Wireless LAN Controller"\nPID: AIR-CT3504-K9,  VID: V01,  SN: ABC1234D567\n'
```

**Help:** execute the command "show inventory"

**Prompt:**
- {base_prompt}>
- {base_prompt}#

### show mobility anchor

**Output:**
```
'\nMobility Anchor Export List\n\n\n Priority number, 1=Highest priority and 3=Lowest priority(default). \n\n WLAN ID     IP Address            Status                            Priority\n -------     ---------------       ------                            --------\n 12          10.0.0.211            Up                                  3                                    \n 12          10.0.0.212            Up                                  2                                    \n 13          10.0.0.212            Up                                  2                                    \n 13          10.0.0.213            Up                                  1                                    \n\n GLAN ID     IP Address            Status\n -------     ---------------       ------\n 99          192.168.180.1         Down\n'
```

**Help:** execute the command "show mobility anchor"

**Prompt:**
- {base_prompt}>
- {base_prompt}#

### show mobility sum

**Output:**
```
'\nMobility Protocol Port........................... 16666\nDefault Mobility Domain.......................... data\nMulticast Mode .................................. Disabled\nMobility Domain ID for 802.11r................... 0xb187\nMobility Keepalive Interval...................... 10\nMobility Keepalive Count......................... 3\nMobility Group Members Configured................ 2\nMobility Control Message DSCP Value.............. 0\n\nControllers configured in the Mobility Group\n MAC Address        IP Address                                       Group Name                        Multicast IP                                     Status\n 08:00:27:0a:04:25  192.168.1.12                                     data                              0.0.0.0                                          Control and Data Path Down\n 08:00:27:1d:a4:d4  192.168.1.11                                     data                              0.0.0.0                                          Up\n'
```

**Help:** execute the command "show mobility sum"

**Prompt:**
- {base_prompt}>
- {base_prompt}#

### show port summary

**Output:**
```
'\n           STP   Admin   Physical   Physical   Link   Link\nPr  Type   Stat   Mode     Mode      Status   Status  Trap     POE    \n-- ------- ---- ------- ---------- ---------- ------ ------- ---------\n1  Normal  Forw Enable  Auto       1000 Full  Up     Enable  N/A     \n2  Normal  Disa Disable Auto       Auto       Down   Enable  N/A     \n3  Normal  Disa Disable Auto       Auto       Down   Enable  Disable \n4  Normal  Forw Enable  Auto       1000 Full  Up     Enable  Enable  (Power Off) \n5  Normal  Disa Enable  Auto       Auto       Down   Enable  N/A     \nRP Normal  Forw Enable  Auto       Auto       Up     Enable  N/A     \nSP Normal  Disa Enable  Auto       Auto       Down   Enable  N/A     \n'
```

**Help:** execute the command "show port summary"

**Prompt:**
- {base_prompt}>
- {base_prompt}#

### show radius summary

**Output:**
```
"\nVendor Id Backward Compatibility................. Disabled\nCall Station Id Case............................. lower\nAccounting Call Station Id Type.................. Mac Address\nAuth Call Station Id Type........................ AP's Radio MAC Address:SSID\nExtended Source Ports Support.................... Enabled\nAggressive Failover.............................. Disabled\nKeywrap.......................................... Disabled\nFallback Test:\n    Test Mode.................................... Passive\n    Probe User Name.............................. cisco-probe\n    Interval (in seconds)........................ 300\nMAC Delimiter for Authentication Messages........ hyphen\nMAC Delimiter for Accounting Messages............ hyphen\nRADIUS Authentication Framed-MTU................. 1300 Bytes\n\nAuthentication Servers\n\nIdx  Type  Server Address    Port    State     Tout  MgmtTout  RFC3576  IPSec - state/Profile Name/RadiusRegionString\n---  ----  ----------------  ------  --------  ----  --------  -------  -------------------------------------------------------\n3  * NM    10.255.255.24       1812    Enabled   5     5         Disabled  Disabled - /none\n4  * NM    10.255.255.25       1812    Enabled   5     5         Disabled  Disabled - /none\n\nAccounting Servers\n\nIdx  Type  Server Address    Port    State     Tout  MgmtTout  RFC3576  IPSec - state/Profile Name/RadiusRegionString\n---  ----  ----------------  ------  --------  ----  --------  -------  -------------------------------------------------------\n3  * N     10.255.255.26       1813    Enabled   5     5         N/A       Disabled - /none\n4  * N     10.255.255.27       1813    Enabled   5     5         N/A       Disabled - /none\n"
```

**Help:** execute the command "show radius summary"

**Prompt:**
- {base_prompt}>
- {base_prompt}#

### show redundancy detail

**Output:**
```
'Redundancy Management IP Address................. 10.128.1.2\nPeer Redundancy Management IP Address............ 10.128.1.3\nRedundancy Port IP Address....................... 169.254.1.2\nPeer Redundancy Port IP Address.................. 169.254.1.3\nPeer Service Port IP Address..................... 0.0.0.0\n\nSwitchover History[1]:\nPrevious Active = 10.128.1.3, Current Active = 10.128.1.2\nSwitchover Reason = Active controller failed, Switchover Time = Tue Nov 24 19:24:43 2020\n\n\nRedundancy Timeout Values.....:\n----------------------------------------------------\nKeep Alive Timeout    : 100 msecs\nPeer Search Timeout   : 120 secs\n\n\nNumber of Routes................................. 0\n\nDestination Network          Netmask               Gateway\n-------------------    -------------------   -------------------\n'
```

**Help:** execute the command "show redundancy detail"

**Prompt:**
- {base_prompt}>
- {base_prompt}#

### show redundancy summary

**Output:**
```
'            Redundancy Mode = SSO ENABLED \n                Local State = ACTIVE \n                 Peer State = STANDBY HOT \n                       Unit = Primary\n                    Unit ID = 00:00:00:00:12:34\n           Redundancy State = SSO\n               Mobility MAC = 00:00:00:00:12:34\n               Redundancy Port  = UP\n            BulkSync Status = Complete\nAverage Redundancy Peer Reachability Latency = 199 Micro Seconds\nAverage Management Gateway Reachability Latency = 570 Micro Seconds\n'
```

**Help:** execute the command "show redundancy summary"

**Prompt:**
- {base_prompt}>
- {base_prompt}#

### show rf-profile summary

**Output:**
```
'\nNumber of RF Profiles............................ 9\n\nOut Of Box State................................. Disabled\n\nOut Of Box Persistence........................... Disabled\n\nRF Profile Name                    Band     Description                          11n-client-only     Applied  \n---------------------------------  -------  -----------------------------------  ------------------  ----------\nHigh-Client-Density-802.11a        5 GHz    <none>                               disable             No        \nHigh-Client-Density-802.11bg       2.4 GHz  <none>                               disable             No        \nLow-Client-Density-802.11a         5 GHz    <none>                               disable             No        \nLow-Client-Density-802.11bg        2.4 GHz  <none>                               disable             No        \nTypical-Client-Density-802.11a     5 GHz    <none>                               disable             No        \nTypical-Client-Density-802.11bg    2.4 GHz  <none>                               disable             No        \nVSW_OFFICE                         5 GHz    <none>                               disable             Yes       \nVSW_OUTDOOR                        5 GHz    <none>                               disable             Yes       \nVSW_WAREHOUSE                      5 GHz    <none>                               disable             Yes       \n'
```

**Help:** execute the command "show rf-profile summary"

**Prompt:**
- {base_prompt}>
- {base_prompt}#

### show stats port summary

**Output:**
```
'   Link                     Pkts In  Pkts In  Pkts Out           \nPr Status Pkts In  Pkts Out Bcast    Errors   Errors   Collisions\n-- ------ -------  -------  -------  -------  -------  ----------\n1  Up     2364509905 2472568024 66473417        0        0        0\n2  Down          0        0        0        0        0        0\n3  Down          0        0        0        0        0        0\n4  Up     335582045 124686415  3515026        0        0        0\n5  Down          0        0        0        0        0        0\n   Total  2700091950 2597254439 69988443        0        0        0\n'
```

**Help:** execute the command "show stats port summary"

**Prompt:**
- {base_prompt}>
- {base_prompt}#

### show sysinfo

**Output:**
```
"\nManufacturer's Name.............................. Cisco Systems Inc.\nProduct Name..................................... Cisco Controller\nProduct Version.................................. 7.4.110.0\nBootloader Version............................... 1.0.16\nField Recovery Image Version..................... 1.0.0\nFirmware Version................................. PIC 15.0\n\n\nBuild Type....................................... DATA + WPS\n\nSystem Name...................................... TEST-WLC\nSystem Location..................................\nSystem Contact...................................\nSystem ObjectID.................................. 1.3.6.1.4.1.9.1.1279\nIP Address....................................... 192.0.2.5\nLast Reset....................................... Power on reset\nSystem Up Time................................... 109 days 16 hrs 33 mins 12 secs\nSystem Timezone Location.........................\nSystem Stats Realtime Interval................... 5\nSystem Stats Normal Interval..................... 180\n\n\nConfigured Country............................... AU  - Australia\nOperating Environment............................ Commercial (0 to 40 C)\nInternal Temp Alarm Limits....................... 0 to 65 C\nInternal Temperature............................. +31 C\nExternal Temperature............................. +35 C\nFan Status....................................... 3960 rpm\n\nState of 802.11b Network......................... Enabled\nState of 802.11a Network......................... Enabled\nNumber of WLANs.................................. 6\nNumber of Active Clients......................... 20\n\nMemory Current Usage............................. Unknown\nMemory Average Usage............................. Unknown\nCPU Current Usage................................ Unknown\nCPU Average Usage................................ Unknown\n\nBurned-in MAC Address............................ D0:C2:82:11:22:33\nMaximum number of APs supported.................. 25\n\n"
```

**Help:** execute the command "show sysinfo"

**Prompt:**
- {base_prompt}>
- {base_prompt}#

### show tacacs summary

**Output:**
```
'\nFallback Test:\n    Interval (in seconds)........................ 0\nAuthentication Servers\n\nIdx      Server Address        Port    State   Tout   MgmtTout\n---  ----------------------   ------  -------  -----  --------\n1    10.255.255.24                  49      Enabled  5      5         \n2    10.255.255.25                  49      Enabled  5      5         \n3    10.255.255.124                 49      Enabled  5      5         \n\nAuthorization Servers\n\nIdx      Server Address        Port    State   Tout   MgmtTout\n---  ----------------------   ------  -------  -----  --------\n1    10.255.255.26              49      Enabled  5      5         \n2    10.255.255.27              49      Enabled  5      5         \n3    10.255.255.126             49      Enabled  5      5         \n\nAccounting Servers\n\nIdx      Server Address        Port    State   Tout   MgmtTout\n---  ----------------------   ------  -------  -----  --------\n1    10.255.255.28              49      Enabled  5      5       \n2    10.255.255.29              49      Enabled  5      5       \n3    10.255.255.128             49      Enabled  5      5       \n'
```

**Help:** execute the command "show tacacs summary"

**Prompt:**
- {base_prompt}>
- {base_prompt}#

### show time

**Output:**
```
'\nTime............................................. Tue Dec 22 11:02:42 2020\n\nTimezone delta................................... 0:0\nTimezone location................................ (GMT -5:00) Eastern Time (US and Canada)\n\nNTP Servers\n    NTP Version..................................     3\n    NTP Polling Interval.........................     72000\n\n     Index     NTP Key Index                  NTP Server                Status          NTP Msg Auth Status\n    -------  ---------------------------------------------------------------------\n       1              0                                  1.1.1.1     In Sync              AUTH DISABLED\n       2              0                                    128.138.141.172     Not Tried            AUTH DISABLED\n'
```

**Help:** execute the command "show time"

**Prompt:**
- {base_prompt}>
- {base_prompt}#

### show wlan sum

**Output:**
```
'\nNumber of WLANs.................................. 3\n\nWLAN ID  WLAN Profile Name / SSID                                                 Status    Interface Name        PMIPv6 Mobility\n-------  -----------------------------------------------------------------------  --------  --------------------  ---------------\n17       Test_lab / Test_lab                                                      Enabled   office_wireless       none        \n18       Public_lab / Public_lab                                                  Enabled   publicwifi            none        \n19       C_Fabric_test / C_Fabric_test                                            Disabled  management            none        \n'
```

**Help:** execute the command "show wlan sum"

**Prompt:**
- {base_prompt}>
- {base_prompt}#

### _default_

**Output:**
```
'% Invalid input detected'
```

**Help:** default output for unknown commands

**Prompt:**
- {base_prompt}>
- {base_prompt}#

