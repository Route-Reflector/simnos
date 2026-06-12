# mikrotik_routeros


!!! warning
    This is automatically generated. In case of any issues,
    please refer to the source code or, even better,
    open an issue on the GitHub repository. Thanks! 🤗📖
## Commands

### _default_

**Output:**
```
bad command name (line 1 column 1)
```

**Help:** default output for unknown commands

**Prompt:**

### interface bonding print detail

**Output:**
```
Flags: X - disabled, R - running
 0  R ;;; To Cisco Te1/3 - Te1/4
      name="bond1" mtu=9000 mac-address=4C:5E:0C:14:3F:9D arp=enabled arp-timeout=auto slaves=sfp-sfpplus7,sfp-sfpplus8 mode=802.3ad primary=none link-monitoring=mii arp-interval=100ms arp-ip-targets="" mii-interval=100ms down-delay=0ms up-delay=0ms lacp-rate=1sec transmit-hash-policy=layer-3-and-4 min-links=0
```

**Help:** execute the command "interface bonding print detail"

**Prompt:**
- [admin@mikrotik_routeros] >

### interface bridge host print terse without-paging

**Output:**
```
0 D E  mac-address=11:22:33:44:55:01 interface=ether4 bridge=lan-bridge on-interface=ether4
1 D E  mac-address=11:22:33:44:55:02 interface=ether3 bridge=lan-bridge on-interface=ether3
2 DLE  mac-address=11:22:33:44:55:03 interface=lan-bridge bridge=lan-bridge on-interface=lan-bridge
3 DL   mac-address=11:22:33:44:55:04 interface=ether4 bridge=lan-bridge on-interface=ether4
4  I   mac-address=11:22:33:44:55:05 interface=lan-bridge bridge=lan-bridge
5  I   comment=test comment mac-address=11:22:33:44:55:06 interface=lan-bridge bridge=lan-bridge
6 XI   mac-address=11:22:33:44:55:07 interface=lan-bridge bridge=lan-bridge
7 XI   mac-address=11:22:33:44:55:08 vid=123 interface=lan-bridge bridge=lan-bridge
```

**Help:** execute the command "interface bridge host print terse without-paging"

**Prompt:**
- [admin@mikrotik_routeros] >

### interface ethernet monitor name once

**Output:**
```
                     name: ether30
                    status: no-link
          auto-negotiation: done
               advertising: 10M-half,10M-full,100M-half,100M-full,1000M-half,1000M-full
  link-partner-advertising:
```

**Help:** execute the command "interface ethernet monitor name once"

**Prompt:**
- [admin@mikrotik_routeros] >

### interface ethernet poe print without-paging

**Output:**
```
bad command name po (line 1 column 7)
```

**Help:** execute the command "interface ethernet poe print without-paging"

**Prompt:**
- [admin@mikrotik_routeros] >

### interface ethernet print

**Output:**
```
Flags: X - disabled, R - running, S - slave
 #    NAME     MTU MAC-ADDRESS       ARP             SWITCH
 0    ether1  1500 12:34:56:78:90:AA enabled         switch1
 1 R  ether2  1500 12:34:56:78:90:AB enabled         switch1
 2 XS ether3  1500 12:34:56:78:90:AC enabled         switch1
 3  S ether4  1500 12:34:56:78:90:AD enabled         switch1
 4 R  ether5  1500 12:34:56:78:90:AE enabled         switch1
```

**Help:** execute the command "interface ethernet print"

**Prompt:**
- [admin@mikrotik_routeros] >

### interface print brief

**Output:**
```
Flags: D - dynamic, X - disabled, R - running, S - slave
 #     NAME                                TYPE       ACTUAL-MTU L2MTU  MAX-L2MTU MAC-ADDRESS
 0     ether1                              ether            1500  1598       2028 12:34:56:78:90:AA
 1 D   ether2                              ether            1500  1598            12:34:56:78:90:AB
 2  R  ether3                              ether            1500                  12:34:56:78:90:AC
 3   S ether4                              ether            1500  1598
 4 DR  ether5                              ether            1500
 5  RS ether6                              ether            1500  1598       2028 12:34:56:78:90:AD
 6 D S lte1                                lte              1500  1598       2028 12:34:56:78:90:AE
 7 DRS pptp-out1                           pptp-out         1450  1598       2028
```

**Help:** execute the command "interface print brief"

**Prompt:**
- [admin@mikrotik_routeros] >

### interface print detail

**Output:**
```
Flags: D - dynamic, X - disabled, R - running, S - slave
 0     name="ether1" default-name="ether1" type="ether" mtu=1500 actual-mtu=1500 l2mtu=1598 max-l2mtu=2028 mac-address=12:34:56:78:90:AA last-link-down-time=jul/09/2023 07:18:33 last-link-up-time=jul/09/2023 07:18:42 link-downs=20

 1 D   name="ether2" default-name="ether2" type="ether" mtu=1500 actual-mtu=1500 l2mtu=1598 max-l2mtu=2028 mac-address=12:34:56:78:90:AB last-link-down-time=jul/09/2023 07:18:34 last-link-up-time=jul/09/2023 07:18:43 link-downs=20

 2  R  name="ether3" default-name="ether3" type="ether" mtu=1500 actual-mtu=1500 l2mtu=1598 max-l2mtu=2028 mac-address=12:34:56:78:90:AC link-downs=0

 3   S name="ether4" default-name="ether4" type="ether" mtu=1500 actual-mtu=1500 l2mtu=1598 max-l2mtu=2028 mac-address=12:34:56:78:90:AD link-downs=0

 4 DR  name="ether5" default-name="ether5" type="ether" mtu=1500 actual-mtu=1500 l2mtu=1598 max-l2mtu=2028 mac-address=12:34:56:78:90:AE link-downs=0

 5  RS name="ether6" default-name="ether6" type="ether" mtu=1500 actual-mtu=1500 l2mtu=1598 max-l2mtu=2028 mac-address=12:34:56:78:90:AF link-downs=0

 6 D S name="lte1" type="lte" mtu=1500 actual-mtu=1500 mac-address=12:34:56:78:90:BA last-link-down-time=jul/21/2023 07:47:40 last-link-up-time=jul/21/2023 07:47:46 link-downs=114

 7 DRS ;;; very very long
multiline description 
       name="pptp-out1" type="pptp-out" mtu=1450 actual-mtu=1450 last-link-down-time=jul/21/2023 07:47:03 last-link-up-time=jul/21/2023 07:47:56 link-downs=304
 
 8  RS ;;; Free Wi-Fi HTTPS
       name="pptp-to-AH1100-HS" type="pptp-out" mtu=1596 actual-mtu=1596 last-link-down-time=nov/03/1970 12:24:10 last-link-up-time=nov/03/1970 12:24:10 link-downs=38 
```

**Help:** execute the command "interface print detail"

**Prompt:**
- [admin@mikrotik_routeros] >

### interface print terse without-paging

**Output:**
```
 0 D   name=ether1 default-name=ether1 type=ether mtu=1500 actual-mtu=1500 l2mtu=1598 max-l2mtu=2028 mac-address=12:34:56:78:90:AA last-link-up-time=aug/16/1970 13:05:43 link-downs=0
 1 DR  name=ether2_UniFi2 default-name=ether2 type=ether mtu=1500 actual-mtu=1500 l2mtu=1598 max-l2mtu=2028 mac-address=12:34:56:78:90:AB last-link-down-time=aug/17/1970 13:33:01 last-link-up-time=aug/17/1970 13:23:11 link-downs=3
 2     name=ether3_UniFi1 default-name=ether3 type=ether mtu=1500 actual-mtu=1500 l2mtu=1598 max-l2mtu=2028 mac-address=12:34:56:78:90:AC link-downs=0
 3  R  name=bridge-VLAN1 type=bridge mtu=auto actual-mtu=1500 l2mtu=1594 mac-address=12:34:56:78:90:AD last-link-up-time=aug/16/1970 13:05:35 link-downs=0
 4  X  name=bridge-VLAN2 type=bridge mac-address=12:34:56:78:90:AE link-downs=0
 5   S name=eth3_vlan1 type=vlan mtu=1500 actual-mtu=1500 l2mtu=1594 mac-address=12:34:56:78:90:AF last-link-down-time=aug/17/1970 13:33:01 last-link-up-time=aug/17/1970 13:23:11 link-downs=3
 6   S name=eth4_vlan2 type=vlan mtu=1500 actual-mtu=1500 l2mtu=1594 mac-address=12:34:56:78:90:BA link-downs=0
 7  RS name=eth4_vlan3 type=vlan mtu=1500 actual-mtu=1500 l2mtu=1594 mac-address=12:34:56:78:90:BB link-downs=0
 8 D S name=eth4_vlan4 type=vlan mtu=1500 actual-mtu=1500 l2mtu=1594 mac-address=12:34:56:78:90:BC link-downs=0
 9 DXS name=eth5_vlan5 type=vlan mtu=1500 actual-mtu=1500 l2mtu=1594 mac-address=12:34:56:78:90:BD last-link-up-time=aug/16/1970 13:05:43 link-downs=0
10  R  name=eth6_vlan6 type=vlan mtu=1500 actual-mtu=1500 l2mtu=1598 mac-address=12:34:56:78:90:BE fast-path=yes last-link-down-time=sep/08/2023 01:07:00 last-link-up-time=sep/08/2023 01:07:09 link-downs=7
```

**Help:** execute the command "interface print terse without-paging"

**Prompt:**
- [admin@mikrotik_routeros] >

### interface vlan print detail

**Output:**
```
Flags: X - disabled, R - running
 0 R ;;; MGMT
     name="vlan1@bond1" mtu=1574 l2mtu=9212 mac-address=AA:BB:CC:11:22:33 arp=enabled arp-timeout=auto loop-protect=default loop-protect-status=off loop-protect-send-interval=5s loop-protect-disable-time=5m vlan-id=1 interface=bond1 use-service-tag=no

 1 R ;;; INET
     name="vlan2@bond1" mtu=1574 l2mtu=9212 mac-address=AA:BB:CC:11:22:33 arp=enabled arp-timeout=auto loop-protect=default loop-protect-status=off loop-protect-send-interval=5s loop-protect-disable-time=5m vlan-id=2 interface=bond1 use-service-tag=no

 2 R ;;; MGMT
     name="vlan10@vlan975@sfp-sfpplus1" mtu=1574 l2mtu=9208 mac-address=AA:BB:CC:11:22:33 arp=enabled arp-timeout=auto loop-protect=default loop-protect-status=off loop-protect-send-interval=5s loop-protect-disable-time=5m vlan-id=10 interface=vlan975@sfp-sfpplus1 use-service-tag=no

 3 R ;;; INET
     name="vlan11@vlan975@sfp-sfpplus1" mtu=1500 l2mtu=9208 mac-address=AA:BB:CC:11:22:33 arp=enabled arp-timeout=auto loop-protect=default loop-protect-status=off loop-protect-send-interval=5s loop-protect-disable-time=5m vlan-id=11 interface=vlan975@sfp-sfpplus1 use-service-tag=no

 4 R ;;; INET
     name="vlan12@vlan975@sfp-sfpplus1" mtu=1500 l2mtu=9208 mac-address=AA:BB:CC:11:22:33 arp=enabled arp-timeout=auto loop-protect=default loop-protect-status=off loop-protect-send-interval=5s loop-protect-disable-time=5m vlan-id=12 interface=vlan975@sfp-sfpplus1 use-service-tag=no

 5 R ;;; INET
     name="vlan111@sfp-sfpplus1" mtu=1500 l2mtu=9212 mac-address=AA:BB:CC:11:22:33 arp=enabled arp-timeout=auto loop-protect=default loop-protect-status=off loop-protect-send-interval=5s loop-protect-disable-time=5m vlan-id=111 interface=sfp-sfpplus1 use-service-tag=no

 6 R ;;; Intercap
     name="vlan975@sfp-sfpplus1" mtu=1500 l2mtu=9212 mac-address=AA:BB:CC:11:22:33 arp=enabled arp-timeout=auto loop-protect=default loop-protect-status=off loop-protect-send-interval=5s loop-protect-disable-time=5m vlan-id=975 interface=sfp-sfpplus1 use-service-tag=no

 7 R name="vlan4050@sfp-sfpplus11" mtu=9212 l2mtu=9212 mac-address=AA:BB:CC:11:22:33 arp=enabled arp-timeout=auto loop-protect=default loop-protect-status=off loop-protect-send-interval=5s loop-protect-disable-time=5m vlan-id=4050 interface=sfp-sfpplus11 use-service-tag=no
```

**Help:** execute the command "interface vlan print detail"

**Prompt:**
- [admin@mikrotik_routeros] >

### interface wireguard peers print terse without-paging

**Output:**
```
0 interface=wg1 name=peer2 public-key=dcKiJ0TpLjtSWZh3G0ILJ9cL56fTIfHBAsZsXdDIlFM= private-key= endpoint-address= endpoint-port=0 current-endpoint-address=192.168.93.254 current-endpoint-port=50610 allowed-address=192.168.100.0/24 preshared-key= client-address=192.168.100.2/32 client-endpoint= rx=180 tx=92 last-handshake=20s
1 interface=wg1 name=peer2 public-key=dcKiJ0TpLjtSWZh3G0ILJ9cL56fTIfHBAsZsXdDIlFM= private-key= endpoint-address= endpoint-port=0 current-endpoint-address=192.168.93.254 current-endpoint-port=50610 allowed-address=192.168.100.0/24 preshared-key= client-address=192.168.100.2/32 client-endpoint= rx=5.3KiB tx=1472 last-handshake=1m45s
```

**Help:** execute the command "interface wireguard peers print terse without-paging"

**Prompt:**
- [admin@mikrotik_routeros] >

### interface wireguard print terse without-paging

**Output:**
```
0 R name=wg1 mtu=1420 listen-port=13231 private-key=+NLZfYaDm6qMfroVg6wf0pZ+0PyriGCd8oO/HkyQqFg= public-key=oeyOeBGeRb8UfvpqFT8XkaG1euGU0viW7Ep4fZEQKyM=
1 R name=wg2 mtu=1420 listen-port=13232 private-key=YEvXxfzV5w8hiS4qZ4keoCe2gsYBJWuOxS3V38rpWH8= public-key=LZoLYLOGTqe2p+S3jcdNAKABYEEFRChELB1p34H2STY=
```

**Help:** execute the command "interface wireguard print terse without-paging"

**Prompt:**
- [admin@mikrotik_routeros] >

### ip address export verbose

**Output:**
```
# jul/21/2023 09:42:42 by RouterOS 6.48.6
# software id = 1234-ABCD
 #
# model = RB750UPr2
# serial number = AB12345CD789
/ip address
add address=10.159.1.159/30 disabled=no interface=ether2 network=10.159.1.158
add address=10.80.90.5/27 comment="test comment" disabled=yes interface=eth3_vlan1 network=10.80.90.0
```

**Help:** execute the command "ip address export verbose"

**Prompt:**
- [admin@mikrotik_routeros] >

### ip address print

**Output:**
```
Flags: X - disabled, I - invalid, D - dynamic
 #   ADDRESS            NETWORK         INTERFACE
 0   10.156.1.229/30    10.156.1.228    ether4_CiscoPhone3
 1   10.152.1.229/30    10.152.1.228    ether5_KFCcisco
 2   10.160.1.229/30    10.160.1.228    ether2_BOX
 3 XI 10.100.3.200/27    10.100.3.192    bridge70
```

**Help:** execute the command "ip address print"

**Prompt:**
- [admin@mikrotik_routeros] >

### ip arp print

**Output:**
```
Flags: X - disabled, I - invalid, H - DHCP, D - dynamic, P - published, C - complete
 #    ADDRESS         MAC-ADDRESS       INTERFACE
 0 DC 10.160.1.230    12:34:56:78:90:AA ether2
 1    10.152.1.230    12:34:56:78:90:AB ether5
 2    10.152.1.231    12:34:56:78:90:AC
 3    10.152.1.232                      ether4
 4 DC 10.152.1.233
```

**Help:** execute the command "ip arp print"

**Prompt:**
- [admin@mikrotik_routeros] >

### ip arp print terse without-paging

**Output:**
```
 0 DC address=10.160.1.230 mac-address=12:34:56:78:90:AA interface=ether2_BOX published=no
 1    address=10.152.1.230 mac-address=12:34:56:78:90:AB interface=ether5_KFCcisco published=no
```

**Help:** execute the command "ip arp print terse without-paging"

**Prompt:**
- [admin@mikrotik_routeros] >

### ip arp print without-paging

**Output:**
```
Flags: X - disabled, I - invalid, H - DHCP, D - dynamic, P - published, C - complete 
 #    ADDRESS         MAC-ADDRESS       INTERFACE                                                                                                                                                      
 0 D  185.163.212.158                   dmz-1-vlan                                                                                                                                                     
17:20:06 echo: system,error,critical login failure for user admin from 65.160.140.13 via ssh
 1    185.163.212.159 AF:D6:C8:F2:36:16 vlan-2                                                                                                                                                     
```

**Help:** execute the command "ip arp print without-paging"

**Prompt:**
- [admin@mikrotik_routeros] >

### ip dhcp-server lease print

**Output:**
```
Flags: X - disabled, R - radius, D - dynamic, B - blocked
 #   ADDRESS          MAC-ADDRESS        HOST-NAME  SERVER         RATE-LIMIT  STATUS  LAST-SEEN
 0   192.168.60.254                                 *1                         bound   35w13h13m15s
 1 X 192.168.61.254                      MikroTik   DHCPv4_Server              waiting never
 1   192.168.62.254   12:34:56:78:90:AA             DHCPv4_Server              waiting never
 2 D 192.168.88.254   12:34:56:78:90:AB  MikroTik   DHCPv4_Server              waiting never
```

**Help:** execute the command "ip dhcp-server lease print"

**Prompt:**
- [admin@mikrotik_routeros] >

### ip dhcp-server lease print terse without-paging

**Output:**
```
 0 D address=192.168.69.254 address-lists="" server=*1 dhcp-option="" status=conflict expires-after=6m59s last-seen=35w12h24m42s active-address=192.168.69.254 active-server=*1 src-mac-address=12:34:56:78:90:AB
 1   address=172.16.16.120 mac-address=30:07:4D:F5:07:49 client-id="1:30:7:4d:f5:7:49" address-lists="" server=defconf dhcp-option="" status=bound expires-after=8m55s last-seen=1m5s active-address=172.16.16.120 active-mac-address=30:07:4D:F5:07:49 active-client-id="1:30:7:4d:f5:7:49" active-server=defconf host-name="Galaxy-S8"
```

**Help:** execute the command "ip dhcp-server lease print terse without-paging"

**Prompt:**
- [admin@mikrotik_routeros] >

### ip dhcp-server lease print without-paging

**Output:**
```
Flags: X - disabled, R - radius, D - dynamic, B - blocked 
 #   ADDRESS                                 MAC-ADDRESS       HOST-NAME                     SERVER                     RATE-LIMIT                     STATUS  LAST-SEEN                               
17:20:06 echo: system,error,critical login failure for user admin from 65.160.140.13 via ssh
 0                                           AF:D6:C8:F2:36:16                                                                                         waiting never                                   
 1 X 192.168.1.56                                                                                                       15                             waiting never                                   
```

**Help:** execute the command "ip dhcp-server lease print without-paging"

**Prompt:**
- [admin@mikrotik_routeros] >

### ip dns cache print terse without-paging

**Output:**
```
0 type=A data=216.58.215.142 name=google.com ttl=1m44s
1 type=AAAA data=2a00:1450:4003:804::200e name=google.com ttl=1m24s
```

**Help:** execute the command "ip dns cache print terse without-paging"

**Prompt:**
- [admin@mikrotik_routeros] >

### ip firewall address-list print terse

**Output:**
```
 0   list=Eqinoxe address=185.48.253.0/27 creation-time=jan/01/2002 01:00:25 
 1   list=Eqinoxe address=185.48.254.0/28 creation-time=jan/01/2002 01:00:25 
 2   list=Eqinoxe address=185.163.212.64/28 creation-time=jan/01/2002 01:00:25 
 3   list=Eqinoxe address=185.163.212.48/28 creation-time=jan/01/2002 01:00:25 
 4   list=Eqinoxe address=185.197.109.16/28 creation-time=jan/01/2002 01:00:25 
 5   list=Supervision address=185.132.66.240 creation-time=jan/01/2002 01:00:25 
 6   list=Supervision address=85.14.167.232/29 creation-time=jan/01/2002 01:00:25 
 7   list=Supervision address=185.48.254.16/29 creation-time=jan/01/2002 01:00:25 
 8   list=Supervision address=5.10.130.152/30 creation-time=jan/01/2002 01:00:25 
 9   list=Supervision address=85.14.167.193 creation-time=jan/01/2002 01:00:25 
10   list=azeazeaze address=192.168.1.1 creation-time=jun/14/2022 06:34:30 
11   list=azeazeaze address=192.168.1.2 creation-time=jun/14/2022 06:44:09 
12   list=azeazeaze address=192.168.1.3 creation-time=jun/14/2022 06:44:51 
13 X list=azeazeaze address=192.168.3.0/24 creation-time=jun/14/2022 07:53:30 
14 D list=azeazeaze address=192.168.3.0/24 creation-time=jun/14/2022 07:53:49 timeout=4m52s 
15 list=snmp-monitoring-address-list address=85.14.167.234 creation-time=mar/01/2023 13:59:33
```

**Help:** execute the command "ip firewall address-list print terse"

**Prompt:**
- [admin@mikrotik_routeros] >

### ip firewall connection print terse without-paging

**Output:**
```
0 SAC protocol=tcp src-address=172.31.255.29 src-port=56454 dst-address=172.31.255.30 dst-port=22 reply-src-address=172.31.255.30 reply-src-port=22 reply-dst-address=172.31.255.29 reply-dst-port=56454 tcp-state=established timeout=23h59m52s orig-packets=520 orig-bytes=47 603 orig-fasttrack-packets=0 orig-fasttrack-bytes=0 repl-packets=363 repl-bytes=53 460 repl-fasttrack-packets=0 repl-fasttrack-bytes=0 orig-rate=1760bps repl-rate=6.4kbps
1 S Cs protocol=icmp src-address=192.168.80.254 dst-address=216.58.215.142 reply-src-address=216.58.215.142 reply-dst-address=172.31.255.30 icmp-type=8 icmp-code=0 icmp-id=69 timeout=9s orig-packets=7 269 orig-bytes=610 596 orig-fasttrack-packets=0 orig-fasttrack-bytes=0 repl-packets=7 269 repl-bytes=610 596 repl-fasttrack-packets=0 repl-fasttrack-bytes=0 orig-rate=1344bps repl-rate=1344bps
```

**Help:** execute the command "ip firewall connection print terse without-paging"

**Prompt:**
- [admin@mikrotik_routeros] >

### ip firewall filter print all without-paging

**Output:**
```
Flags: X - disabled, I - invalid, D - dynamic 
 0    ;;; defconf: accept established,related,untracked
      chain=input action=accept connection-state=established,related,untracked 

 1    ;;; defconf: drop invalid
      chain=input action=drop connection-state=invalid 

 2    ;;; FIREWALL-DMZ-1
      chain=forward action=accept connection-state=established,related,new in-interface=dmz-1-vlan out-interface=pppoe-out1 

 3    chain=forward action=accept dst-address=185.163.212.156/30 

 4    ;;; defconf: accept ICMP
      chain=input action=accept protocol=icmp 

 5    ;;; Acces VPN
      chain=input action=accept protocol=udp dst-port=500,1701,4500 log-prefix="Acces VPN" 

 6    chain=input action=accept protocol=ipsec-esp 

 7    ;;; Acces WAN
      chain=input action=accept protocol=tcp src-address-list=Supervision dst-port=4430,22,8291 

 8    ;;; Acces WAN SNMP
      chain=input action=accept protocol=udp src-address-list=Supervision dst-port=161 
17:20:06 echo: system,error,critical login failure for user admin from 65.160.140.13 via ssh

 9    ;;; defconf: accept to local loopback (for CAPsMAN)
      chain=input action=accept dst-address=127.0.0.1 

10    ;;; defconf: drop all not coming from LAN
      chain=input action=drop in-interface-list=!LAN 

11    ;;; defconf: accept in ipsec policy
      chain=forward action=accept ipsec-policy=in,ipsec 

12    ;;; defconf: accept out ipsec policy
      chain=forward action=accept ipsec-policy=out,ipsec 

13 X  ;;; defconf: fasttrack
      chain=forward action=fasttrack-connection hw-offload=yes connection-state=established,related

14    ;;; defconf: accept established,related, untracked
      chain=forward action=accept connection-state=established,related,untracked 

15    ;;; defconf: drop invalid
      chain=forward action=drop connection-state=invalid 

16    ;;; defconf: drop all from WAN not DSTNATed
      chain=forward action=drop connection-state=new connection-nat-state=!dstnat in-interface-list=WAN 

17    ;;; Input
      chain=input action=accept src-address-list=Eqinoxe 

18    ;;; related established
      chain=input connection-state=established,related 

19    chain=forward connection-state=established,related src-mac-address=67:33:EB:0E:EB:A8

20    ;;; drop invalid connections
17:20:06 echo: system,error,critical login failure for user admin from 65.160.140.13 via ssh
      chain=forward action=drop connection-state=invalid protocol=tcp 

21    ;;; Block all entrant
      chain=input action=drop in-interface=all-ppp 

22    chain=input action=drop in-interface=all-ethernet log-prefix=""
```

**Help:** execute the command "ip firewall filter print all without-paging"

**Prompt:**
- [admin@mikrotik_routeros] >

### ip firewall nat print all without-paging

**Output:**
```
Flags: X - disabled, I - invalid, D - dynamic 
17:20:06 echo: system,error,critical login failure for user admin from 65.160.140.13 via ssh
 0    ;;; dmz-1: masquerade
      chain=srcnat action=masquerade src-address=!185.163.212.156/30 out-interface-list=WAN ipsec-policy=out,none 

 1    chain=dstnat action=redirect protocol=icmp src-address=192.168.1.16 dst-address=31.31.31.31 in-interface-list=dmz-1 log=no log-prefix="" 

 2 X  ;;; qsdqsdqsd
17:20:06 echo: system,error,critical login failure for user admin from 65.160.140.13 via ssh
      chain=srcnat action=accept protocol=vmtp in-interface=all-ethernet out-interface=ether4 log=no log-prefix="" 

 3 X  chain=srcnat action=accept protocol=tcp src-address-list=Supervision dst-address-list=Eqinoxe src-port=80 dst-port=8080 log=no log-prefix="" 

 4    chain=srcnat action=masquerade protocol=icmp src-address=0.0.0.0 out-interface-list=DMZ log=no log-prefix="" ipsec-policy=out,ipsec 
```

**Help:** execute the command "ip firewall nat print all without-paging"

**Prompt:**
- [admin@mikrotik_routeros] >

### ip hotspot ip-binding print terse without-paging

**Output:**
```
0 P comment=Sonda_Mantenimiento mac-address=D8:3A:DD:48:B6:1C server=server1 type=bypassed
1   mac-address=B0:4A:B4:76:A9:5D address=10.0.1.98 to-address=10.0.1.98 server=server1
```

**Help:** execute the command "ip hotspot ip-binding print terse without-paging"

**Prompt:**
- [admin@mikrotik_routeros] >

### ip neighbor print detail

**Output:**
```
 0 interface=ether1 address=10.159.1.159 address4=10.159.1.159 mac-address=12:34:56:78:90:AB identity="MikroTik-Dev" platform="MikroTik" version="6.48.6 (long-term)" unpack=none age=17s uptime=1w5d2h31m30s software-id="1234-ABCD" board="RB750UPr2" interface-name="ether2" system-description="MikroTik RouterOS 6.48.6 (long-term) RB750UPr2" system-caps=bridge,router system-caps-enabled=bridge,wlan-ap,router
```

**Help:** execute the command "ip neighbor print detail"

**Prompt:**
- [admin@mikrotik_routeros] >

### ip route print detail

**Output:**
```
Flags: X - disabled, A - active, D - dynamic, C - connect, S - static, r - rip, b - bgp, o - ospf, m - mme, B - blackhole, U - unreachable, P - prohibit
 0 ADS  dst-address=0.0.0.0/0 gateway=192.168.8.1 gateway-status=192.168.8.1 reachable via  lte1 distance=2 scope=30 target-scope=10 vrf-interface=lte1

 1 ADC  dst-address=10.160.1.228/30 pref-src=10.160.1.230 gateway=ether1 gateway-status=ether1 reachable distance=0 scope=10

 2 A S  dst-address=10.213.20.64/32 gateway=10.160.1.229 gateway-status=10.160.1.229 reachable via  ether1 distance=1 scope=30 target-scope=10

 3 A S  ;;; to Internet
        dst-address=0.0.0.0/0 gateway=10.160.1.230 gateway-status=10.160.1.230 reachable via ether2 distance=1 scope=30 target-scope=10 routing-mark=to-reserve

 4 A S  dst-address=0.0.0.0/0 gateway=1.2.3.4 gateway-status=1.2.3.4 recursive via 10.152.1.230 ether5 distance=1 scope=30 target-scope=10 routing-mark=Free_Wi-Fi

 5 A SB dst-address=10.0.0.0/8 type=blackhole distance=100 routing-mark=Free_Wi-Fi

 6 A S  dst-address=0.0.0.0/0 gateway=1.2.3.4 gateway-status=1.2.3.4 recursive via 10.152.1.230 ether5 check-gateway=ping distance=1 scope=30 target-scope=10
```

**Help:** execute the command "ip route print detail"

**Prompt:**
- [admin@mikrotik_routeros] >

### ip route print terse

**Output:**
```
 0 ADS  dst-address=::/0 gateway=pppoe-out1 gateway-status=pppoe-out1 reachable distance=100 scope=30 target-scope=10 
 1 ADC  dst-address=2a05:c100:7::/64 gateway=bridge-lan gateway-status=bridge-lan reachable distance=0 scope=10 
 2   S  dst-address=9bb8:baac:d400::/38 gateway=ether4 gateway-status=ether4 unreachable distance=44 scope=30 target-scope=10 
17:20:06 echo: system,error,critical login failure for user admin from 65.160.140.13 via ssh
 3 X S  dst-address=ec64:a7fd:bc1c:14c:7960:5000::/84 gateway=ether2 gateway-status=ether2 inactive distance=7 scope=30 target-scope=10 
 4   S  dst-address=fd79:f1d4:a400::/39 gateway=ether5 gateway-status=ether5 unreachable distance=24 scope=30 target-scope=10 
```

**Help:** execute the command "ip route print terse"

**Prompt:**
- [admin@mikrotik_routeros] >

### ip route print terse without-paging

**Output:**
```
 0 A S  dst-address=0.0.0.0/0 gateway=192.168.8.1 gateway-status=192.168.8.1 reachable via  lte1 distance=2 scope=30 target-scope=10 vrf-interface=lte1
 1 ADC  dst-address=10.160.1.228/30 pref-src=10.160.1.230 gateway=ether1 gateway-status=ether1 reachable distance=0 scope=10
 2 A S  comment=to Internet dst-address=134.0.0.0/8 gateway=10.160.1.230 gateway-status=10.160.1.230 reachable via  ether2 distance=1 scope=30 target-scope=10 routing-mark=reserve
 3 A S  dst-address=172.0.0.0/8 gateway=1.2.3.4 gateway-status=1.2.3.4 recursive via 10.152.1.230 ether5 distance=1 scope=30 target-scope=10 routing-mark=Free_Wi-Fi
 4 A SB dst-address=10.0.0.0/8 type=blackhole distance=100 routing-mark=Free_Wi-Fi
```

**Help:** execute the command "ip route print terse without-paging"

**Prompt:**
- [admin@mikrotik_routeros] >

### ipv6 neighbor print without-paging

**Output:**
```
Flags: R - router 
 0   address=ff02::5 interface=main mac-address=33:33:00:00:00:05 status="noarp" 

 1   address=ff02::1 interface=main mac-address=33:33:00:00:00:01 status="noarp" 

 2 R address=fe80::d7:4cff:fec1:2e32 interface=main mac-address=00:0C:42:28:79:45 status="stale" 

 3   address=2a05:c100:1d::351c interface=bridge-lan status="failed"
```

**Help:** execute the command "ipv6 neighbor print without-paging"

**Prompt:**
- [admin@mikrotik_routeros] >

### log print detail without-paging

**Output:**
```
 time=jul/19 14:27:01 topics=script,info message="Ping testA: Packets Sent = 18, Packets Loss = 10 % "

 time=jul/19 16:27:01 topics=script,info message="Ping testA: Packets Sent = 18, Packets Loss = 10 % "

 time=jul/19 16:37:01 topics=script,info message="Ping testA: Packets Sent = 12, Packets Loss = 40 % "

 time=jul/19 19:17:01 topics=script,info message="Ping testA: Packets Sent = 17, Packets Loss = 15 % "

 time=jul/19 03:05:02 topics=script,warning message="Connection via Box bad. Reset USB Modem"

 time=jul/20 03:07:40 topics=interface,info message="lte1 link down"

 time=jul/20 03:07:46 topics=interface,info message="lte1 link up"

 time=jul/20 03:07:46 topics=dhcp,info message="dhcp-client on lte1 got IP address 192.168.1.2"
```

**Help:** execute the command "log print detail without-paging"

**Prompt:**
- [admin@mikrotik_routeros] >

### ping

**Output:**
```
  SEQ HOST                                     SIZE TTL TIME  STATUS
    0 8.8.8.8                                    56  64 157ms
    1 8.8.8.8                                    56  64 64ms
    2 8.8.8.8                                    56  64 60ms
    3 8.8.8.8                                    56  64 65ms
    sent=13 received=13 packet-loss=0% min-rtt=55ms avg-rtt=67ms max-rtt=157ms
```

**Help:** execute the command "ping"

**Prompt:**
- [admin@mikrotik_routeros] >

### routing bgp peer print status

**Output:**
```
Flags: X - disabled, E - established
 0   name="peer1" instance=default remote-address=192.168.1.134 remote-as=65001 tcp-md5-key="" nexthop-choice=default multihop=no route-reflect=no hold-time=3m
     ttl=255 in-filter="" out-filter="" address-families=ip,ipv6 default-originate=never remove-private-as=no as-override=no passive=no use-bfd=no state=opensent
```

**Help:** execute the command "routing bgp peer print status"

**Prompt:**
- [admin@mikrotik_routeros] >

### routing bgp peer print status without-paging

**Output:**
```
Flags: X - disabled, E - established
 0 E name="SRV-R1" instance=default remote-address=1.2.3.4 remote-as=8491 tcp-md5-key="" nexthop-choice=default multihop=no route-reflect=no hold-time=3m ttl=255 in-filter=INTERNAL-RR-IN out-filter=INTERNAL-RR-OUT address-families=ip update-source=Loopback0 default-originate=never remove-private-as=no as-override=no passive=no use-bfd=no remote-id=1.2.3.4 local-address=1.2.3.44 uptime=7w6d1h49m36s prefix-count=1836 updates-sent=331 updates-received=237257 withdrawn-sent=301 withdrawn-received=84853 remote-hold-time=1m30s used-hold-time=1m30s used-keepalive-time=30s refresh-capability=yes as4-capability=yes state=established
 
 1 E name="SRV-R2" instance=default remote-address=1.2.3.5 remote-as=8491 tcp-md5-key="" nexthop-choice=default multihop=no route-reflect=no hold-time=3m ttl=255 in-filter=INTERNAL-RR-IN out-filter=INTERNAL-RR-OUT address-families=ip update-source=Loopback0 default-originate=never remove-private-as=no as-override=no passive=no use-bfd=no remote-id=1.2.3.5 local-address=1.2.3.44 uptime=7w6d1h49m43s prefix-count=1835 updates-sent=331 updates-received=243335 withdrawn-sent=301 withdrawn-received=84680 remote-hold-time=1m30s used-hold-time=1m30s used-keepalive-time=30s refresh-capability=yes as4-capability=yes state=established
```

**Help:** execute the command "routing bgp peer print status without-paging"

**Prompt:**
- [admin@mikrotik_routeros] >

### routing ospf interface print terse

**Output:**
```
 0  P interface=all cost=10 priority=1 authentication=none authentication-key=foo authentication-key-id=1 network-type=broadcast instance-id=0 retransmit-interval=5s transmit-delay=1s hello-interval=10s dead-interval=40s use-bfd=no
 1    comment=ospf comment interface=vlan906@bond1 cost=10 priority=1 authentication=none authentication-key="bar" authentication-key-id=1 network-type=broadcast instance-id=0 retransmit-interval=5s transmit-delay=1s hello-interval=10s dead-interval=40s use-bfd=no
 2 DP interface=lo0 cost=10 priority=1 authentication=none authentication-key="" authentication-key-id=1 network-type=broadcast instance-id=0 retransmit-interval=5s transmit-delay=1s hello-interval=10s dead-interval=40s use-bfd=no
```

**Help:** execute the command "routing ospf interface print terse"

**Prompt:**
- [admin@mikrotik_routeros] >

### routing ospf neighbor print

**Output:**
```
 0 instance=default router-id=89.188.172.2 address=89.188.172.81 interface=vlan68 priority=128 dr-address=0.0.0.0 backup-dr-address=0.0.0.0 state="Full" state-changes=5 ls-retransmits=0 ls-requests=0 db-summaries=0 adjacency=7w5d8h40m21s

 1 instance=default router-id=89.188.172.3 address=89.188.172.93 interface=vlan71 priority=128 dr-address=0.0.0.0 backup-dr-address=0.0.0.0 state="Full" state-changes=5 ls-retransmits=0 ls-requests=0 db-summaries=0 adjacency=7w5d8h40m21s
```

**Help:** execute the command "routing ospf neighbor print"

**Prompt:**
- [admin@mikrotik_routeros] >

### routing ospf neighbor print terse without-paging

**Output:**
```
 0 instance=default router-id=1.2.3.4 address=1.2.3.58 interface=vlan1 priority=128 dr-address=0.0.0.0 backup-dr-address=0.0.0.0 state=Full state-changes=5 ls-retransmits=0 ls-requests=0 db-summaries=0 adjacency=7w5d8h47m54s
 1 instance=default router-id=1.2.3.5 address=1.2.3.59 interface=vlan2 priority=128 dr-address=0.0.0.0 backup-dr-address=0.0.0.0 state=Full state-changes=5 ls-retransmits=0 ls-requests=0 db-summaries=0
```

**Help:** execute the command "routing ospf neighbor print terse without-paging"

**Prompt:**
- [admin@mikrotik_routeros] >

### snmp community print without-paging

**Output:**
```
17:20:06 echo: system,error,critical login failure for user admin from 65.160.140.13 via ssh
Flags: * - default, X - disabled 
 #    NAME                                                        ADDRESSES                                                                                         SECURITY   READ-ACCESS WRITE-ACCESS
17:20:06 echo: system,error,critical login failure for user admin from 65.160.140.13 via ssh
 0 *  Monitoring                                                  ::/0                                                                                              none       yes         no          
```

**Help:** execute the command "snmp community print without-paging"

**Prompt:**
- [admin@mikrotik_routeros] >

### system clock print

**Output:**
```
                  time: 10:00:47
                  date: jul/21/2023
  time-zone-autodetect: yes
        time-zone-name: Europe/Moscow
            gmt-offset: +03:00
            dst-active: no
```

**Help:** execute the command "system clock print"

**Prompt:**
- [admin@mikrotik_routeros] >

### system identity print

**Output:**
```
  name: Mikrotik-Device_Name
```

**Help:** execute the command "system identity print"

**Prompt:**
- [admin@mikrotik_routeros] >

### system resource print

**Output:**
```
                   uptime: 6w5d11h55m45s
                  version: 6.48.6 (long-term)
               build-time: Dec/03/2021 12:15:05
              free-memory: 40.2MiB
             total-memory: 64.0MiB
                      cpu: MIPS 24Kc V7.4
                cpu-count: 1
            cpu-frequency: 650MHz
                 cpu-load: 1%
           free-hdd-space: 1196.0KiB
          total-hdd-space: 16.0MiB
  write-sect-since-reboot: 44663
         write-sect-total: 572180
               bad-blocks: 0%
        architecture-name: mipsbe
               board-name: hEX PoE lite
                 platform: MikroTik
```

**Help:** execute the command "system resource print"

**Prompt:**
- [admin@mikrotik_routeros] >

### system routerboard print

**Output:**
```
       routerboard: yes
        board-name: hEX PoE lite
             model: RouterBOARD 750UP r2
     serial-number: 8B0208F4D5F9
     firmware-type: qca9531L
  factory-firmware: 3.41
  current-firmware: 3.41
  upgrade-firmware: 6.48.6
```

**Help:** execute the command "system routerboard print"

**Prompt:**
- [admin@mikrotik_routeros] >

### tool profile

**Output:**
```
NAME                    CPU        USAGE
spi                                   1%
console                               0%
firewall                            0.5%
networking                            0%
management                          0.5%
profiling                             0%
unclassified                        0.5%
total                               2.5%
```

**Help:** execute the command "tool profile"

**Prompt:**
- [admin@mikrotik_routeros] >

### tool speed-test address

**Output:**
```
address: 192.168.88.1
              status: tcp upload
      time-remaining: 23s
    ping-min-avg-max: 52.4ms / 86.1ms / 246ms
  jitter-min-avg-max: 12us / 21.3ms / 158ms
                loss: 0% (0/200)
        tcp-download: 921Mbps local-cpu-load:30%
          tcp-upload: 920Mbps local-cpu-load:30% remote-cpu-load:25%
        udp-download: 917Mbps local-cpu-load:6% remote-cpu-load:21%
          udp-upload: 916Mbps local-cpu-load:20% remote-cpu-load:6%
```

**Help:** execute the command "tool speed-test address"

**Prompt:**
- [admin@mikrotik_routeros] >

### user active print

**Output:**
```
Flags: R - radius, M - by-romon
 #    WHEN                 NAME       ADDRESS         VIA
 0    jul/21/2023 09:38:39 user1      1.2.3.4         ssh
 1    jul/21/2023 11:00:32 user2      1.2.3.5         telnet
```

**Help:** execute the command "user active print"

**Prompt:**
- [admin@mikrotik_routeros] >

### user print

**Output:**
```
Flags: X - disabled
 #   NAME                     GROUP  ADDRESS            LAST-LOGGED-IN
 0   ;;; system default user
     admin                    full                      jun/30/2023 01:08:59
 1   user1                    full                      jul/18/2023 05:12:46
```

**Help:** execute the command "user print"

**Prompt:**
- [admin@mikrotik_routeros] >

