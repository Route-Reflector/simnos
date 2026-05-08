# oneaccess_oneos


!!! warning
    This is automatically generated. In case of any issues,
    please refer to the source code or, even better,
    open an issue on the GitHub repository. Thanks! 🤗📖
## Commands

### enable

**Output:** None

**Help:** enter enable mode

**Prompt:**
- oneaccess_oneos>

### term len 0

**Output:** None

**Help:** disable paging

**Prompt:**
- oneaccess_oneos>
- oneaccess_oneos#

### screen-width 512

**Output:**
```
error: unknown command
```

**Help:** set terminal width (ONEOS6, returns error to trigger ONEOS5 fallback)

**Prompt:**
- oneaccess_oneos>
- oneaccess_oneos#

### stty columns 255

**Output:** None

**Help:** set terminal width (ONEOS5 fallback)

**Prompt:**
- oneaccess_oneos>
- oneaccess_oneos#

### cat bsa bsaboot.inf

**Output:**
```
flash:/BSA/binaries/OneOs
flash:/BSA/config/bsaStart.cfg

```

**Help:** execute the command "cat bsa bsaboot.inf"

**Prompt:**
- oneaccess_oneos>
- oneaccess_oneos#

### hostname

**Output:**
```
dops-lab-02

```

**Help:** execute the command "hostname"

**Prompt:**
- oneaccess_oneos>
- oneaccess_oneos#

### ls

**Output:**
```
Listing the directory /BSA/binaries
.                                       0
..                                      0
OneOs                            15896363
ONEOS16-MONO_FT-V5.2R2E7_HA1.ZZZ 15848593

```

**Help:** execute the command "ls"

**Prompt:**
- oneaccess_oneos>
- oneaccess_oneos#

### show cellular-radio context

**Output:**
```
 Context 1
 =========

  Cellular controller: 0
  Internal context Id: 1
  Interface          : Virtual-Ethernet 1, USB-Path: /sys/class/net/wwan0
  Cellular profile   : 1

  rxSpeed/max                    : 0/0
  txSpeed/max                    : 0/0

  Call manager state             : _connected
  Mtu                            : 1500
  Data bearer technology         : LTE

  Ipv4 connection
   Address                       : 101.194.59.47
   Subnet                        : 255.255.255.224
   Gateway                       : 101.194.59.48
   Primary Dns                   : 2.2.2.90
   Secondary Dns                 : 2.2.2.94
   Packet data connection        : Connected
   Last call end reason          : <not available>
   Data statistics               : 
    Tx packets                   : 603031
    Rx packets                   : 572105
    Tx packet errors             : 0
    Rx packet errors             : 0
    Tx packet overflows          : 0
    Rx packet overflows          : 0
    Tx bytes                     : 83925324
    Rx bytes                     : 87179616

  Ipv6 connection
   Address                       : <not available>
   Gateway                       : <not available>
   Primary Dns                   : <not available>
   Secondary Dns                 : <not available>
   Packet data connection        : <not available>
   Last call end reason          : <not available>
   Data statistics               : <not available>

```

**Help:** execute the command "show cellular-radio context"

**Prompt:**
- oneaccess_oneos>
- oneaccess_oneos#

### show cellular-radio equipment

**Output:**
```
 Cellular Radio Modem Information
  Manufacturer identification                          : Sierra Wireless, Incorporated
  Equipment information                                : MC7455
  Boot revision identification                         : SWI9X30C_02.20.03.00 r6691 CARMD-EV-FRMWR2 2016/06/30 10:54:05
  Revision identification                              : SWI9X30C_02.20.03.00 r6691 CARMD-EV-FRMWR2 2016/06/30 10:54:05
  Equipment information (IMEI)                         : 359022065533630

 SIM Card Information
  SIM card status                                      : SIM card is present
  SIM International Mobile Subscriber Identity IMSI    : 211104500225982
  Integrated Circuit Card ID                           : 89320269140114098260

 PIN Information
  PIN code status                                      : entered OK 

```

**Help:** execute the command "show cellular-radio equipment"

**Prompt:**
- oneaccess_oneos>
- oneaccess_oneos#

### show cellular-radio network

**Output:**
```
 Current selected operator                            :  Dummy Provider
 Signal strength                                      :  Good
 Total Ec/Io                                          :  <not available>
 RSSI                                                 :  -58 dBm
 RSRQ                                                 :  -9 dB
 RSRP                                                 :  -91 dBm
 SNR                                                  :  23 dB
 Current radio access technology                      :  4G
 Circuit-switched register state                      :  Registered
 Packet-switched attach state                         :  Attached

Statistics: 
 Reset on loss of GPRS registration                   :  1
 Reset on failed initial registration                 :  0
 Hardware reset of modem                              :  0
 Unknown reset of modem                               :  505
 Toggle w_disable of modem                            :  0

Details: 
 Location Area Code (LAC)                             :  <not available>
 Cell ID                                              :  18224898
 Tracking Area Code (TAC)                             :  18300
 Current Public Land Mobile Network (PLMN = MCC+MNC)  :  20610

```

**Help:** execute the command "show cellular-radio network"

**Prompt:**
- oneaccess_oneos>
- oneaccess_oneos#

### show helpers

**Output:**
```
ip forward-protocol udp 137
ip forward-protocol udp 138
ip forward-protocol udp 67
ip forward-protocol udp 68
ip forward-protocol udp 69
ip forward-protocol udp 37
ip forward-protocol udp 42
ip forward-protocol udp 49
ip forward-protocol udp 53
Bvi 1: 0 broadcasts forwarded
  10.1.0.151  10.2.0.20  10.88.1.11
Bvi 2: 0 broadcasts forwarded
  10.2.0.20  10.1.0.151  10.88.1.11
Bvi 3: 0 broadcasts forwarded
  10.1.0.151  10.2.0.20  10.88.1.11

```

**Help:** execute the command "show helpers"

**Prompt:**
- oneaccess_oneos>
- oneaccess_oneos#

### show interfaces

**Output:**
```
GigabitEthernet 0/0 is up, line protocol is up
  Flags: (0x8063) BROADCAST MULTICAST ARP, interface index is 111
  Promiscuous mode active
  Encapsulation: Ethernet v2, MTU 1500 bytes
  Up-time 396d21h16m, status change count 3
  Hardware address is 70:fc:8c:02:bb:4f, ARP timeout 7200 sec
  Auto-negotiation, full-duplex, flowcontrol disabled
  Line speed 1000000 kbps
  Mean input/output rate 504776/397392 bits/s, 226/198 packets/s (over the last 4 seconds)
  Mean input/output load percentage 0.050/0.039 percent (over the last 4 seconds)
  Congestion Management Dropped packets: RX:0, CPU:0, Total:0
  Bridged to group 1
  Output queuing strategy: fifo, output queue length/depth 0/126
  Reliability: 255/255
  IN:  4578563266 packets, 2133875155484 bytes, 0 queue drops
       735617600 broadcasts, 136187244 multicasts, 0 errors, 164 discards, 0 mac acl discards
       0 unknown protocols
  OUT: 3838465524 packets, 2752454327149 bytes, 3357 queue drops
       20941718 broadcasts, 0 multicasts, 0 errors, 1 discards, 0 collisions
GigabitEthernet 0/1 is up, line protocol is up
  Flags: (0x8063) BROADCAST MULTICAST ARP, interface index is 112
  Promiscuous mode active
  Encapsulation: Ethernet v2, MTU 1500 bytes
  Up-time 11d21h45m, status change count 31
  Hardware address is 70:fc:8c:06:bb:4f, ARP timeout 7200 sec
  Auto-negotiation, full-duplex, flowcontrol disabled
  Line speed 1000000 kbps
  Mean input/output rate 243736/256456 bits/s, 152/114 packets/s (over the last 4 seconds)
  Mean input/output load percentage 0.024/0.025 percent (over the last 4 seconds)
  Congestion Management Dropped packets: RX:0, CPU:0, Total:0
  Bridged to group 2
  Output queuing strategy: fifo, output queue length/depth 0/126
  Reliability: 255/255
  IN:  1125009328 packets, 189632230943 bytes, 0 queue drops
       745390714 broadcasts, 123018268 multicasts, 0 errors, 887632010 discards, 0 mac acl discards
       887631923 unknown protocols
  OUT: 351229701 packets, 302436379177 bytes, 23658 queue drops
       2298782 broadcasts, 0 multicasts, 0 errors, 0 discards, 0 collisions
GigabitEthernet 0/2 is up, line protocol is down
  Flags: (0x8023) BROADCAST MULTICAST ARP, interface index is 113
  Promiscuous mode active
  Encapsulation: Ethernet v2, MTU 1500 bytes
  Down-time 448d10h36m, status change count 0
  Hardware address is 70:fc:8c:0a:bb:4f, ARP timeout 7200 sec
  Line speed unknown
  Mean input/output rate 0/0 bits/s, 0/0 packets/s (over the last 4 seconds)
  Mean input/output load percentage 0.000/0.000 percent (over the last 4 seconds)
  Congestion Management Dropped packets: RX:0, CPU:0, Total:0
  Bridged to group 1
  Output queuing strategy: fifo, output queue length/depth 0/126
  Reliability: 255/255
  IN:  0 packets, 0 bytes, 0 queue drops
       0 broadcasts, 0 multicasts, 0 errors, 0 discards, 0 mac acl discards
       0 unknown protocols            
  OUT: 0 packets, 0 bytes, 0 queue drops
       0 broadcasts, 0 multicasts, 0 errors, 0 discards, 0 collisions
GigabitEthernet 0/3 is up, line protocol is down
  Flags: (0x8023) BROADCAST MULTICAST ARP, interface index is 114
  Promiscuous mode active
  Encapsulation: Ethernet v2, MTU 1500 bytes
  Down-time 448d10h36m, status change count 0
  Hardware address is 70:fc:8c:0e:bb:4f, ARP timeout 7200 sec
  Line speed unknown
  Mean input/output rate 0/0 bits/s, 0/0 packets/s (over the last 4 seconds)
  Mean input/output load percentage 0.000/0.000 percent (over the last 4 seconds)
  Congestion Management Dropped packets: RX:0, CPU:0, Total:0
  Bridged to group 1
  Output queuing strategy: fifo, output queue length/depth 0/126
  Reliability: 255/255
  IN:  0 packets, 0 bytes, 0 queue drops
       0 broadcasts, 0 multicasts, 0 errors, 0 discards, 0 mac acl discards
       0 unknown protocols
  OUT: 0 packets, 0 bytes, 0 queue drops
       0 broadcasts, 0 multicasts, 0 errors, 0 discards, 0 collisions
FastEthernet 1/0 is up, line protocol is up
  Flags: (0x8063) BROADCAST MULTICAST ARP, interface index is 106
  Description: *** WAN INTERFACE ***
  Encapsulation: Ethernet v2, MTU 1546 bytes
  Up-time 448d10h36m, status change count 1
  Hardware address is 70:fc:8c:12:bb:4f, ARP timeout 7200 sec
  Auto-negotiation, full-duplex, flowcontrol enabled
  Line speed 100000 kbps
  Media-type rj45
  Mean input/output rate 229312/237176 bits/s, 104/102 packets/s (over the last 4 seconds)
  Mean input/output load percentage 0.229/0.237 percent (over the last 4 seconds)
  Congestion Management Dropped packets: RX:0, CPU:0, Total:0
  Output queuing strategy: cbq
  Reliability: 255/255
  IN:  3777818556 packets, 2813130486707 bytes, 0 queue drops
       608769 broadcasts, 0 multicasts, 0 errors, 608769 discards, 0 mac acl discards
       608769 unknown protocols
  OUT: 3537518750 packets, 1904299986411 bytes, 1944226 queue drops
       0 broadcasts, 0 multicasts, 0 errors, 114820 discards, 0 collisions
FastEthernet 1/0.10 is up, line protocol is up
  Flags: (0x8063) BROADCAST MULTICAST ARP, interface index is 22017
  Description: *** VDSL2 SHARED VLAN ***
  Encapsulation: 802.1Q Virtual LAN, VLAN ID 10, MTU 1500 bytes
  Up-time 448d10h36m, status change count 1
  Hardware address is 70:fc:8c:12:bb:4f, ARP timeout 7200 sec
  Line speed 100000 kbps
  Mean input/output rate 229312/237176 bits/s, 104/102 packets/s (over the last 4 seconds)
  Mean input/output load percentage 0.229/0.237 percent (over the last 4 seconds)
  Congestion Management Dropped packets: RX:0, CPU:0, Total:0
  Output queuing strategy: fifo, output queue length/depth 0/126
  Reliability: 255/255
  IN:  3777209791 packets, 2812914388764 bytes, 0 queue drops
       0 broadcasts, 0 multicasts, 0 errors, 0 discards, 0 mac acl discards
       0 unknown protocols
  OUT: 3539577808 packets, 1907203054251 bytes, 0 queue drops
       0 broadcasts, 0 multicasts, 3 errors, 0 discards, 0 collisions
Dialer 1 is up, line protocol is up
  Flags: (0x90f1) POINT-TO-POINT MULTICAST, interface index is 11101
  Description: *** VT096413 - GS99999941512 - IP-VPN - ['VDSL2 SHARED VLAN'] - NOS-EMLP-01/ANT-EMLP-01 - LOOPBACK
  Encapsulation: Point-to-Point Protocol, MTU 1492 bytes
  Up-time 196d20h26m, status change count 7
  Internet address is 94.105.238.194/32, destination address is 94.105.238.193
  Line speed 100000 kbps, bandwidth limit 70000 kbps
  Mean input/output rate 240208/217472 bits/s, 104/102 packets/s (over the last 4 seconds)
  Mean input/output load percentage 0.240/0.310 percent (over the last 4 seconds)
  Congestion Management Dropped packets: RX:0, CPU:0, Total:0
  Output queuing strategy: fifo+shaper, output queue length/depth 0/126
  Shaper: packets dequeued -763131925, burst(current/max) 874602/875000
  Reliability: 255/255
  IN:  3769467815 packets, 2899812744256 bytes, 0 queue drops
       0 broadcasts, 0 multicasts, 0 errors, 0 discards, 0 mac acl discards
       0 unknown protocols
  OUT: 3531835372 packets, 1821912521847 bytes, 0 queue drops
       0 broadcasts, 0 multicasts, 0 errors, 0 discards
Loopback 0 is up, line protocol is up
  Flags: (0x80e9) LOOPBACK MULTICAST, interface index is 9902
  MTU 32768 bytes
  Up-time 448d10h36m, status change count 0
  Internet address is 127.0.0.1/32
  IPv6 address is ::1/128
  IPv6 address is fe80::1/64
  Line speed unknown
  Mean input/output rate 0/0 bits/s, 0/0 packets/s (over the last 4 seconds)
  Mean input/output load percentage 0.000/0.000 percent (over the last 4 seconds)
  Congestion Management Dropped packets: RX:0, CPU:0, Total:0
  Output queuing strategy: fifo, output queue length/depth 0/126
  IN:  1749 packets, 164332 bytes, 0 queue drops
       0 broadcasts, 0 multicasts, 0 errors, 0 discards, 0 mac acl discards
       0 unknown protocols
  OUT: 1749 packets, 164332 bytes, 0 queue drops
       0 broadcasts, 0 multicasts, 0 errors, 0 discards
Loopback 1 is up, line protocol is up
  Flags: (0x80e9) LOOPBACK MULTICAST, interface index is 9903
  Firewall zone: management
  Description: *** VT096413 - GS99999941512 ***
  MTU 32768 bytes
  Up-time 448d10h36m, status change count 0
  Internet address is 94.105.25.111/32
  Line speed unknown
  Mean input/output rate 6280/6280 bits/s, 9/9 packets/s (over the last 4 seconds)
  Mean input/output load percentage 0.000/0.000 percent (over the last 4 seconds)
  Congestion Management Dropped packets: RX:0, CPU:0, Total:0
  Output queuing strategy: fifo, output queue length/depth 0/126
  IN:  6346421 packets, 472102678 bytes, 0 queue drops
       0 broadcasts, 0 multicasts, 0 errors, 0 discards, 0 mac acl discards
       0 unknown protocols            
  OUT: 6346427 packets, 472103054 bytes, 0 queue drops
       0 broadcasts, 0 multicasts, 0 errors, 0 discards
Bvi 1 is up, line protocol is up
  Flags: (0x8063) BROADCAST MULTICAST ARP, interface index is 9501
  Description: Connection to Customer LAN
  Encapsulation: Ethernet v2, MTU 1500 bytes
  Up-time 396d21h16m, status change count 3
  Hardware address is 70:fc:8c:02:bb:4f, ARP timeout 7200 sec
  Internet address is 192.168.5.1/24, broadcast address is 192.168.5.255
  Line speed 1000000 kbps
  Mean input/output rate 504776/397352 bits/s, 226/198 packets/s (over the last 4 seconds)
  Mean input/output load percentage 0.000/0.000 percent (over the last 4 seconds)
  Congestion Management Dropped packets: RX:0, CPU:0, Total:0
  Bridged to group 1
  Output queuing strategy: fifo, output queue length/depth 0/126
  IN:  4578208775 packets, 2133846516522 bytes, 0 queue drops
       735617627 broadcasts, 136187246 multicasts, 0 errors, 0 discards, 0 mac acl discards
       683928098 unknown protocols
  OUT: 3814474945 packets, 2750982891198 bytes, 0 queue drops
       20941724 broadcasts, 0 multicasts, 1 errors, 22341208 discards
Bvi 55 is up, line protocol is up
  Flags: (0x8063) BROADCAST MULTICAST ARP, interface index is 9555
  Encapsulation: Ethernet v2, MTU 1500 bytes
  Up-time 11d21h45m, status change count 31
  Hardware address is 70:fc:8c:06:bb:4f, ARP timeout 7200 sec
  Internet address is 192.168.55.1/24, broadcast address is 192.168.55.255
  Line speed 1000000 kbps
  Mean input/output rate 186144/256456 bits/s, 113/114 packets/s (over the last 4 seconds)
  Mean input/output load percentage 0.000/0.000 percent (over the last 4 seconds)
  Congestion Management Dropped packets: RX:0, CPU:0, Total:0
  Bridged to group 2
  Output queuing strategy: fifo, output queue length/depth 0/126
  IN:  237375069 packets, 58811387749 bytes, 0 queue drops
       182857 broadcasts, 19575274 multicasts, 0 errors, 0 discards, 0 mac acl discards
       18243239 unknown protocols
  OUT: 351253527 packets, 302442538460 bytes, 0 queue drops
       2298786 broadcasts, 0 multicasts, 1 errors, 2496554 discards
Null 0 is up, line protocol is up
  Flags: (0x80e1) MULTICAST, interface index is 9901
  MTU 32768 bytes
  Up-time 448d10h36m, status change count 0
  Line speed unknown
  Mean input/output rate 0/0 bits/s, 0/0 packets/s (over the last 4 seconds)
  Mean input/output load percentage 0.000/0.000 percent (over the last 4 seconds)
  Congestion Management Dropped packets: RX:0, CPU:0, Total:0
  Output queuing strategy: fifo, output queue length/depth 0/126
  IN:  0 packets, 0 bytes, 0 queue drops
       0 broadcasts, 0 multicasts, 0 errors, 0 discards, 0 mac acl discards
       0 unknown protocols
  OUT: 0 packets, 0 bytes, 0 queue drops
       0 broadcasts, 0 multicasts, 0 errors, 0 discards

```

**Help:** execute the command "show interfaces"

**Prompt:**
- oneaccess_oneos>
- oneaccess_oneos#

### show ip access-lists

**Output:**
```
interface Bvi 20, inbound IP access list GUEST_WIFI_IN

IP access list extended GRE-Tunnel21
permit gre host 10.94.55.207 host 94.105.25.2 log (0 matches)

IP access list extended GRE-Tunnel11
permit gre host 10.94.55.207 host 94.105.25.9 log (0 matches)

IP access list extended GUEST_WIFI_IN
deny any 10.0.0.0 0.255.255.255 (0 matches)
deny any 172.16.0.0 0.15.255.255 (0 matches)
deny any 192.168.0.0 0.0.255.255 (0 matches)
permit any any (5164438 matches)

IP access list standard 52
permit 91.208.220.0 0.0.0.255 any (4519825 matches)

IP access list extended MANAGEMENT_IN
permit tcp 91.208.220.0 0.0.0.255 any eq ssh (2896 matches)
permit tcp 91.208.220.0 0.0.0.255 any eq telnet (0 matches)
permit tcp 94.104.18.0 0.0.1.255 any eq ssh (0 matches)
permit tcp 94.104.18.0 0.0.1.255 any eq telnet (0 matches)
permit tcp 192.4.21.0 0.0.0.255 any eq ssh (0 matches)
permit tcp 192.4.21.0 0.0.0.255 any eq telnet (0 matches)
permit tcp 192.4.91.0 0.0.0.255 any eq ssh (0 matches)
permit tcp 192.4.91.0 0.0.0.255 any eq telnet (0 matches)
permit tcp host 10.0.96.16 10.110.0.0 0.0.255.255 eq telnet (0 matches)
permit tcp 192.0.2.0 0.0.0.255 any eq ssh (0 matches)
permit tcp 192.0.2.0 0.0.0.255 any eq telnet (0 matches)
deny any any (0 matches)

For info on ACLs used by IPSEC, please refer to show crypto acl [detail <name>] command. 

```

**Help:** execute the command "show ip access-lists"

**Prompt:**
- oneaccess_oneos>
- oneaccess_oneos#

### show ip as-path-access-list

**Output:**
```
AS path access list 102
    permit ^$

```

**Help:** execute the command "show ip as-path-access-list"

**Prompt:**
- oneaccess_oneos>
- oneaccess_oneos#

### show ip bgp summary

**Output:**
```
BGP router identifier 194.5.12.148, local AS number 65000, vrf (null)
6 BGP AS-PATH entries
0 BGP community entries

Neighbor        V     AS     MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
194.5.163.29   4      14737   13360   12237       34    0    0 4d05h57m       28

Total number of neighbors 1

```

**Help:** execute the command "show ip bgp summary"

**Prompt:**
- oneaccess_oneos>
- oneaccess_oneos#

### show ip interface brief

**Output:**
```
Interface              IP-Address      OK? Status                Protocol Description         
GigabitEthernet 0/0       <unassigned>    YES up                    up      *** PBXPLUG 212 - BACKUP TEST - 94.105.1.119 ***
GigabitEthernet 0/1       <unassigned>    YES up                    up      *** PBXPLUG 401 - BACKUP TEST - 94.105.34.2 ***
GigabitEthernet 0/2       <unassigned>    YES up                    down    *IPERF*
GigabitEthernet 0/3       <unassigned>    YES up                    down    
FastEthernet 1/0          <unassigned>    YES up                    up      *** WAN INTERFACE ***
FastEthernet 1/0.1        192.168.1.2     YES up                    up      *** management A-modem (modem ip = 192.168.1.1) ***
FastEthernet 1/0.10       <unassigned>    YES up                    up      *** VT096910 - GS20170330107 - IP-VPN - VDSL2 SHARED VLAN - NOS-EMLP-01/ANT-EMLP-01 - Loopback503941 ***
Dialer 1                  94.105.163.30   YES up                    up      *** VT096910 - GS20170330107 - IP-VPN - VDSL2 SHARED VLAN - NOS-EMLP-01/ANT-EMLP-01 - Loopback503941
Dialer 2                  <unassigned>    NO  administratively down down    *** VT108085 - GS20190640686 - CI - VDSL2 SHARED VLAN - NOS-EMLP-01/ANT-EMLP-01 - LOOPBACK 503899 ***
Dialer 3                  94.104.254.138  YES up                    up      *** DATA VDSL shared VLAN - GSID0004_MAIN - CI TEST - NOS-EMLP-01/ANT-EMLP-01 - LOOPBACK 500000***
Loopback 0                127.0.0.1       YES up                    up      
Loopback 1                94.105.12.148   YES up                    up      *** VT096910 - GS20170330107 ***
Loopback 777              94.107.245.249  YES up                    up      
Bvi 10                    192.168.10.1    YES up                    up      *** VT108085 - GS20190640686 - CI ACCESS ***
Bvi 100                   192.168.100.1   YES up                    up      *** TEST MAARTEN - BACKUP SCRIPT PBXPLUG ***
Bvi 200                   94.105.16.129   YES up                    down    *IPERF*
dot11radio 0/0.1          <unassigned>    YES up                    up      
dot11radio 0/0.2          <unassigned>    YES up                    up      
Null 0                    <unassigned>    YES up                    up      
dot11radio 0/0            <unassigned>    YES up                    up      

```

**Help:** execute the command "show ip interface brief"

**Prompt:**
- oneaccess_oneos>
- oneaccess_oneos#

### show ip prefix-list

**Output:**
```
RIP: ip prefix-list DENY-BGP: 3 entries
   Description: ** do not advertise to BGP neighbors **
   seq 5 permit 192.4.21.0/24 le 32
   seq 10 permit 192.4.91.0/24 le 32
   seq 15 deny any
OSPF: ip prefix-list DENY-BGP: 3 entries
   Description: ** do not advertise to BGP neighbors **
   seq 5 permit 192.4.21.0/24 le 32
   seq 10 permit 192.4.91.0/24 le 32
   seq 15 deny any
BGP: ip prefix-list DENY-BGP: 3 entries
   Description: ** do not advertise to BGP neighbors **
   seq 5 permit 192.4.21.0/24 le 32
   seq 10 permit 192.4.91.0/24 le 32
   seq 15 deny any

```

**Help:** execute the command "show ip prefix-list"

**Prompt:**
- oneaccess_oneos>
- oneaccess_oneos#

### show ip ssh

**Output:**
```
SSH Enabled
Authentication timeout 30 secs, retries 3
Session timeout 900 secs
Authentication method: all
Maximum number of sessions 5
Maximum number of channels per session 10
Authorized public keys:
none
Key fingerprint:
ssh-rsa 4096 bc:f8:c3:67:8f:de:f3:ec:5c:29:b5:a4:e4:25:de:7a
SCP server enabled

```

**Help:** execute the command "show ip ssh"

**Prompt:**
- oneaccess_oneos>
- oneaccess_oneos#

### show ip vrf brief

**Output:**
```
 VRF Name                          VRF Id                    Interfaces
 MODEM                             1                         FastEthernet 1/0.1
 INTERNET                          2                         Dialer 2
                                                             Dialer 3
                                                             Loopback 777
                                                             Bvi 10
 TEST                              3

```

**Help:** execute the command "show ip vrf brief"

**Prompt:**
- oneaccess_oneos>
- oneaccess_oneos#

### show isdn active

**Output:**
```
                               ISDN ACTIVE CALLS                                
--------------------------------------------------------------------------------
App.  Call         Calling           Called   Call   Port BChan Call-ref call-id
      Type          Number           Number Duration                            
--------------------------------------------------------------------------------
no isdn active calls...
--------------------------------------------------------------------------------

```

**Help:** execute the command "show isdn active"

**Prompt:**
- oneaccess_oneos>
- oneaccess_oneos#

### show isdn led-status

**Output:**
```
 Status of VOIP service

 1 Dial-peer pots up.
 1 Dial-peer voip up.

 Sip-gateway status is no shutdown,
 -> is registered
    1/1 ep is registered with registrar sip.blabla.be:5060
 -> IF loopback 1 [1.2.3.4] is up.

 No Sip-server,

 no voice com...

voice led track-conditions
 voice-gw   any
 voice-port no

Sys LEDs
SYS LED VoIP color= GREEN , state=ON
SYS LED COM  color=     - , state=OFF
SYS LED Maintenance color=     - , state=OFF

```

**Help:** execute the command "show isdn led-status"

**Prompt:**
- oneaccess_oneos>
- oneaccess_oneos#

### show isdn status all

**Output:**
```
	isdn line                       5/0
		physical type                  E1
		protocol descriptor            E1_PRI
		 linecode                      hdb3
		 framing                       DF
		config state                   up
		loop state                     down 
		-layer 1 status                deactivated
		Alarm Indication Signal (AIS)  OFF
		Loss Off Signal (LOS)          ON
		Remote Indication Signal (RAI) OFF
		pri AIS occurrence(s)          0
		pri LOS occurrence(s)          1
		pri RDI occurrence(s)          0
		-layer 2 status                deactivated
		Tx frames on D channel         0
		Rx frames on D channel         0
		-layer 3 status
		    no active call

	isdn line                       5/1
		protocol descriptor     BRI_NT
		config state            down
		-layer 1 status         deactivated
		-layer 2 status         deactivated
		Tx frames on D channel  0
		Rx frames on D channel  0
		-layer 3 status
		    no active call

	isdn line                       5/2
		protocol descriptor     BRI_NT
		config state            down
		-layer 1 status         deactivated
		-layer 2 status         deactivated
		Tx frames on D channel  0
		Rx frames on D channel  0
		-layer 3 status
		    no active call

```

**Help:** execute the command "show isdn status all"

**Prompt:**
- oneaccess_oneos>
- oneaccess_oneos#

### show memory

**Output:**
```
===============================================
| Memory status report  |   Kbytes  |         |
===============================================
| Ram size              |  262 144  |         |
| :..Program            |   41 171  |         |
| :  :..code            |   30 715  |         |
| :  :..data            |   10 455  |         |
| :..Static buffers     |      192  |         |
| :..Dynamic total      |  213 604  |         |
| :  :       used       |   46 847  |  21.9%  |
| :  :       free       |  166 757  |  78.0%  |
| :  :..System total    |  213 604  |         |
| :            used     |   46 847  |  21.9%  |
| :            free     |  166 757  |  78.0%  |
| :..Ram disk total     |    1 011  |         |
|             used      |       74  |   7.4%  |
|             free      |      937  |  92.7%  |
|                       |           |         |
| Flash size            |    2 048  |         |
| :..Boot               |    1 024  |         |
| :..Static areas       |      200  |         |
|                       |           |         |
| Extended Flash size   |   65 536  |         |
| :..Flash disk total   |   64 688  |         |
|               used    |   31 176  |  48.1%  |
|               free    |   33 512  |  51.8%  |
===============================================

```

**Help:** execute the command "show memory"

**Prompt:**
- oneaccess_oneos>
- oneaccess_oneos#

### show policy-interface output

**Output:**
```
FastEthernet 1/0: service-policy output L3VPN_SHARED_VLAN_SHAPE_CE_OUT
traffic statistics:
  Class 'CLASS_ANY':
    705455781 packets, 202655648081 bytes, 0 dscp remarked, mean input rate 76250 bits/s
     Packets dropped by Congestion Management: CPU:0 Rx:0 Total:0 
    Service-policy L3VPN_SHARED_QOS_CE_OUT :
      Class 'REAL-TIME': color-blind mode
        82440 packets, 22296428 bytes, mean input rate 0 bits/s
        cir 512 kbits/s, cbs 6400 bytes
        conformed 79705 packets, 20216566 bytes; action: set-dscp-transmit 46
        exceeded 2735 packets, 2079862 bytes; action: drop
      Class 'MANAGEMENT':
        3881496 packets, 352515276 bytes, 0 dscp remarked, mean input rate 76250 bits/s
     Packets dropped by Congestion Management: CPU:0 Rx:0 Total:0 
      Class 'ROUTING':
        94685677 packets, 20577282182 bytes, 0 dscp remarked, mean input rate 0 bits/s
     Packets dropped by Congestion Management: CPU:0 Rx:0 Total:0 
      Class 'PREMIUM':
        866614 packets, 336167380 bytes, 17 dscp remarked, mean input rate 0 bits/s
     Packets dropped by Congestion Management: CPU:0 Rx:0 Total:0 
      Class 'GOLD':
        45391 packets, 15054274 bytes, 111 dscp remarked, mean input rate 0 bits/s
     Packets dropped by Congestion Management: CPU:0 Rx:0 Total:0 
      Class 'SILVER':
        5160082 packets, 2081326098 bytes, 968 dscp remarked, mean input rate 0 bits/s
     Packets dropped by Congestion Management: CPU:0 Rx:0 Total:0 
      Class 'BRONZE':
        76569 packets, 28162916 bytes, 70513 dscp remarked, mean input rate 0 bits/s
     Packets dropped by Congestion Management: CPU:0 Rx:0 Total:0 
      Class 'class-default':
        600657514 packets, 179242844271 bytes, 0 dscp remarked, mean input rate 0 bits/s
     Packets dropped by Congestion Management: CPU:0 Rx:0 Total:0 
  Class 'class-default':
    0 packets, 0 bytes, 0 dscp remarked, mean input rate 0 bits/s
     Packets dropped by Congestion Management: CPU:0 Rx:0 Total:0 

output queuing statistics:
  Class 'CLASS_ANY': medium priority (no excess allowed)
    bandwidth 33250 kb/s, burst 81872 bytes
    mean input rate 73400 bits/s, mean output rate 73400 bits/s
    packets output 700594742, packets dropped 707805 (0%)
    bytes output 222578689918, bytes dropped 939630669 (0%)
    Service-policy L3VPN_SHARED_QOS_CE_OUT :
      Class 'REAL-TIME': high priority
        bandwidth 512 kb/s, burst 32249 bytes, queue length/limit 0/50
        mean input rate 0 bits/s, mean output rate 0 bits/s
        packets output 79705, packets dropped 0 (0%)
        bytes output 22607716, bytes dropped 0 (0%)
      Class 'MANAGEMENT': medium priority
        bandwidth 9 kb/s, burst 1870 bytes, queue length/limit 0/50
        mean input rate 73200 bits/s, mean output rate 73200 bits/s
        packets output 3881341, packets dropped 0 (0%)
        bytes output 468946094, bytes dropped 0 (0%)
        remaining-bandwidth share 1, excess-rate-priority 0, excess packets sent 222911
      Class 'ROUTING': medium priority
        bandwidth 9 kb/s, burst 1870 bytes, queue length/limit 0/50
        mean input rate 0 bits/s, mean output rate 0 bits/s
        packets output 94685677, packets dropped 0 (0%)
        bytes output 23417852492, bytes dropped 0 (0%)
        remaining-bandwidth share 1, excess-rate-priority 0, excess packets sent 83405404
      Class 'PREMIUM': medium priority
        bandwidth 11452 kb/s, burst 28624 bytes, queue length/limit 0/60
        mean input rate 0 bits/s, mean output rate 0 bits/s
        packets output 866614, packets dropped 0 (0%)
        bytes output 362165800, bytes dropped 0 (0%)
        remaining-bandwidth share 34, excess-rate-priority 0, excess packets sent 279
        weight random early detection:
          exponential weight: 9

         Dscp   Random drop         Tail drop             Min/Max      Mark
                   pkts               pkts               threshold  probability
           0        0                  0                   30/60       1/10
           1        0                  0                   33/60       1/10
           2        0                  0                   36/60       1/10
           3        0                  0                   39/60       1/10
           4        0                  0                   42/60       1/10
           5        0                  0                   45/60       1/10
           6        0                  0                   48/60       1/10
           7        0                  0                   51/60       1/10
           8        0                  0                   33/60       1/10
           9        0                  0                   33/60       1/10
           10       0                  0                   36/60       1/10
           11       0                  0                   39/60       1/10
           12       0                  0                   42/60       1/10
           13       0                  0                   45/60       1/10
           14       0                  0                   48/60       1/10
           15       0                  0                   51/60       1/10
           16       0                  0                   36/60       1/10
           17       0                  0                   33/60       1/10
           18       0                  0                   36/60       1/10
           19       0                  0                   39/60       1/10
           20       0                  0                   42/60       1/10
           21       0                  0                   45/60       1/10
           22       0                  0                   48/60       1/10
           23       0                  0                   51/60       1/10
           24       0                  0                   39/60       1/10
           25       0                  0                   33/60       1/10
           26       0                  0                   36/60       1/10
           27       0                  0                   39/60       1/10
           28       0                  0                   42/60       1/10
           29       0                  0                   45/60       1/10
           30       0                  0                   48/60       1/10
           31       0                  0                   51/60       1/10
           32       0                  0                   42/60       1/10
           33       0                  0                   33/60       1/10
           34       0                  0                   36/60       1/10
           35       0                  0                   39/60       1/10
           36       0                  0                   42/60       1/10
           37       0                  0                   45/60       1/10
           38       0                  0                   48/60       1/10
           39       0                  0                   51/60       1/10
           40       0                  0                   45/60       1/10
           41       0                  0                   33/60       1/10
           42       0                  0                   36/60       1/10
           43       0                  0                   39/60       1/10
           44       0                  0                   42/60       1/10
           45       0                  0                   45/60       1/10
           46       0                  0                   48/60       1/10
           47       0                  0                   51/60       1/10
           48       0                  0                   48/60       1/10
           49       0                  0                   33/60       1/10
           50       0                  0                   36/60       1/10
           51       0                  0                   39/60       1/10
           52       0                  0                   42/60       1/10
           53       0                  0                   45/60       1/10
           54       0                  0                   48/60       1/10
           55       0                  0                   51/60       1/10
           56       0                  0                   51/60       1/10
           57       0                  0                   33/60       1/10
           58       0                  0                   36/60       1/10
           59       0                  0                   39/60       1/10
           60       0                  0                   42/60       1/10
           61       0                  0                   45/60       1/10
           62       0                  0                   48/60       1/10
           63       0                  0                   51/60       1/10
      Class 'GOLD': medium priority
        bandwidth 8180 kb/s, burst 29750 bytes, queue length/limit 0/60
        mean input rate 0 bits/s, mean output rate 0 bits/s
        packets output 45391, packets dropped 0 (0%)
        bytes output 16416004, bytes dropped 0 (0%)
        remaining-bandwidth share 24, excess-rate-priority 0, excess packets sent 0
        weight random early detection:
          exponential weight: 9

         Dscp   Random drop         Tail drop             Min/Max      Mark
                   pkts               pkts               threshold  probability
           0        0                  0                   30/60       1/10
           1        0                  0                   33/60       1/10
           2        0                  0                   36/60       1/10
           3        0                  0                   39/60       1/10
           4        0                  0                   42/60       1/10
           5        0                  0                   45/60       1/10
           6        0                  0                   48/60       1/10
           7        0                  0                   51/60       1/10
           8        0                  0                   33/60       1/10
           9        0                  0                   33/60       1/10
           10       0                  0                   36/60       1/10
           11       0                  0                   39/60       1/10
           12       0                  0                   42/60       1/10
           13       0                  0                   45/60       1/10
           14       0                  0                   48/60       1/10
           15       0                  0                   51/60       1/10
           16       0                  0                   36/60       1/10
           17       0                  0                   33/60       1/10
           18       0                  0                   36/60       1/10
           19       0                  0                   39/60       1/10
           20       0                  0                   42/60       1/10
           21       0                  0                   45/60       1/10
           22       0                  0                   48/60       1/10
           23       0                  0                   51/60       1/10
           24       0                  0                   39/60       1/10
           25       0                  0                   33/60       1/10
           26       0                  0                   36/60       1/10
           27       0                  0                   39/60       1/10
           28       0                  0                   42/60       1/10
           29       0                  0                   45/60       1/10
           30       0                  0                   48/60       1/10
           31       0                  0                   51/60       1/10
           32       0                  0                   42/60       1/10
           33       0                  0                   33/60       1/10
           34       0                  0                   36/60       1/10
           35       0                  0                   39/60       1/10
           36       0                  0                   42/60       1/10
           37       0                  0                   45/60       1/10
           38       0                  0                   48/60       1/10
           39       0                  0                   51/60       1/10
           40       0                  0                   45/60       1/10
           41       0                  0                   33/60       1/10
           42       0                  0                   36/60       1/10
           43       0                  0                   39/60       1/10
           44       0                  0                   42/60       1/10
           45       0                  0                   45/60       1/10
           46       0                  0                   48/60       1/10
           47       0                  0                   51/60       1/10
           48       0                  0                   48/60       1/10
           49       0                  0                   33/60       1/10
           50       0                  0                   36/60       1/10
           51       0                  0                   39/60       1/10
           52       0                  0                   42/60       1/10
           53       0                  0                   45/60       1/10
           54       0                  0                   48/60       1/10
           55       0                  0                   51/60       1/10
           56       0                  0                   51/60       1/10
           57       0                  0                   33/60       1/10
           58       0                  0                   36/60       1/10
           59       0                  0                   39/60       1/10
           60       0                  0                   42/60       1/10
           61       0                  0                   45/60       1/10
           62       0                  0                   48/60       1/10
           63       0                  0                   51/60       1/10
      Class 'SILVER': medium priority
        bandwidth 4908 kb/s, burst 30749 bytes, queue length/limit 0/60
        mean input rate 0 bits/s, mean output rate 0 bits/s
        packets output 5160082, packets dropped 0 (0%)
        bytes output 2236128558, bytes dropped 0 (0%)
        remaining-bandwidth share 14, excess-rate-priority 0, excess packets sent 42
        weight random early detection:
          exponential weight: 9

         Dscp   Random drop         Tail drop             Min/Max      Mark
                   pkts               pkts               threshold  probability
           0        0                  0                   30/60       1/10
           1        0                  0                   33/60       1/10
           2        0                  0                   36/60       1/10
           3        0                  0                   39/60       1/10
           4        0                  0                   42/60       1/10
           5        0                  0                   45/60       1/10
           6        0                  0                   48/60       1/10
           7        0                  0                   51/60       1/10
           8        0                  0                   33/60       1/10
           9        0                  0                   33/60       1/10
           10       0                  0                   36/60       1/10
           11       0                  0                   39/60       1/10
           12       0                  0                   42/60       1/10
           13       0                  0                   45/60       1/10
           14       0                  0                   48/60       1/10
           15       0                  0                   51/60       1/10
           16       0                  0                   36/60       1/10
           17       0                  0                   33/60       1/10
           18       0                  0                   36/60       1/10
           19       0                  0                   39/60       1/10
           20       0                  0                   42/60       1/10
           21       0                  0                   45/60       1/10
           22       0                  0                   48/60       1/10
           23       0                  0                   51/60       1/10
           24       0                  0                   39/60       1/10
           25       0                  0                   33/60       1/10
           26       0                  0                   36/60       1/10
           27       0                  0                   39/60       1/10
           28       0                  0                   42/60       1/10
           29       0                  0                   45/60       1/10
           30       0                  0                   48/60       1/10
           31       0                  0                   51/60       1/10
           32       0                  0                   42/60       1/10
           33       0                  0                   33/60       1/10
           34       0                  0                   36/60       1/10
           35       0                  0                   39/60       1/10
           36       0                  0                   42/60       1/10
           37       0                  0                   45/60       1/10
           38       0                  0                   48/60       1/10
           39       0                  0                   51/60       1/10
           40       0                  0                   45/60       1/10
           41       0                  0                   33/60       1/10
           42       0                  0                   36/60       1/10
           43       0                  0                   39/60       1/10
           44       0                  0                   42/60       1/10
           45       0                  0                   45/60       1/10
           46       0                  0                   48/60       1/10
           47       0                  0                   51/60       1/10
           48       0                  0                   48/60       1/10
           49       0                  0                   33/60       1/10
           50       0                  0                   36/60       1/10
           51       0                  0                   39/60       1/10
           52       0                  0                   42/60       1/10
           53       0                  0                   45/60       1/10
           54       0                  0                   48/60       1/10
           55       0                  0                   51/60       1/10
           56       0                  0                   51/60       1/10
           57       0                  0                   33/60       1/10
           58       0                  0                   36/60       1/10
           59       0                  0                   39/60       1/10
           60       0                  0                   42/60       1/10
           61       0                  0                   45/60       1/10
           62       0                  0                   48/60       1/10
           63       0                  0                   51/60       1/10
      Class 'BRONZE': medium priority
        bandwidth 3272 kb/s, burst 31249 bytes, queue length/limit 0/60
        mean input rate 0 bits/s, mean output rate 0 bits/s
        packets output 76493, packets dropped 76 (0%)
        bytes output 30364562, bytes dropped 95424 (0%)
        remaining-bandwidth share 9, excess-rate-priority 0, excess packets sent 10772
        weight random early detection:
          exponential weight: 7

         Dscp   Random drop         Tail drop             Min/Max      Mark
                   pkts               pkts               threshold  probability
           0        0                  0                   30/60       1/10
           1        0                  0                   33/60       1/10
           2        0                  0                   36/60       1/10
           3        0                  0                   39/60       1/10
           4        0                  0                   42/60       1/10
           5        0                  0                   45/60       1/10
           6        0                  0                   48/60       1/10
           7        0                  0                   51/60       1/10
           8        0                  0                   33/60       1/10
           9        0                  0                   33/60       1/10
           10       0                  0                   36/60       1/10
           11       0                  0                   39/60       1/10
           12       0                  0                   42/60       1/10
           13       0                  0                   45/60       1/10
           14       0                  0                   48/60       1/10
           15       0                  0                   51/60       1/10
           16       0                  0                   36/60       1/10
           17       0                  0                   33/60       1/10
           18       0                  0                   36/60       1/10
           19       0                  0                   39/60       1/10
           20       0                  0                   42/60       1/10
           21       0                  0                   45/60       1/10
           22       0                  0                   48/60       1/10
           23       0                  0                   51/60       1/10
           24       0                  0                   39/60       1/10
           25       0                  0                   33/60       1/10
           26       0                  0                   36/60       1/10
           27       0                  0                   39/60       1/10
           28       0                  0                   42/60       1/10
           29       0                  0                   45/60       1/10
           30       0                  0                   48/60       1/10
           31       0                  0                   51/60       1/10
           32       0                  0                   42/60       1/10
           33       0                  0                   33/60       1/10
           34       0                  0                   36/60       1/10
           35       0                  0                   39/60       1/10
           36       0                  0                   42/60       1/10
           37       0                  0                   45/60       1/10
           38       0                  0                   48/60       1/10
           39       0                  0                   51/60       1/10
           40       0                  0                   45/60       1/10
           41       0                  0                   33/60       1/10
           42       0                  0                   36/60       1/10
           43       0                  0                   39/60       1/10
           44       0                  0                   42/60       1/10
           45       0                  0                   45/60       1/10
           46       0                  0                   48/60       1/10
           47       0                  0                   51/60       1/10
           48       0                  0                   48/60       1/10
           49       0                  0                   33/60       1/10
           50       0                  0                   36/60       1/10
           51       0                  0                   39/60       1/10
           52       0                  0                   42/60       1/10
           53       0                  0                   45/60       1/10
           54       0                  0                   48/60       1/10
           55       0                  0                   51/60       1/10
           56       0                  0                   51/60       1/10
           57       0                  0                   33/60       1/10
           58       0                  0                   36/60       1/10
           59       0                  0                   39/60       1/10
           60       0                  0                   42/60       1/10
           61       0                  0                   45/60       1/10
           62       0                  0                   48/60       1/10
           63       0                  0                   51/60       1/10
      Class 'class-default': medium priority
        bandwidth 4908 kb/s, burst 30749 bytes, queue length/limit 0/60
        mean input rate 96 bits/s, mean output rate 96 bits/s
        packets output 595799441, packets dropped 707729 (0%)
        bytes output 196024209496, bytes dropped 939535245 (0%)
        remaining-bandwidth share 14, excess-rate-priority 0, excess packets sent 52266475
        weight random early detection:
          exponential weight: 9

         Dscp   Random drop         Tail drop             Min/Max      Mark
                   pkts               pkts               threshold  probability
           0        119931             0                   30/60       1/10
           1        0                  0                   33/60       1/10
           2        41                 0                   36/60       1/10
           3        0                  0                   39/60       1/10
           4        3                  0                   42/60       1/10
           5        0                  0                   45/60       1/10
           6        0                  0                   48/60       1/10
           7        0                  0                   51/60       1/10
           8        0                  0                   33/60       1/10
           9        0                  0                   33/60       1/10
           10       0                  0                   36/60       1/10
           11       0                  0                   39/60       1/10
           12       0                  0                   42/60       1/10
           13       0                  0                   45/60       1/10
           14       0                  0                   48/60       1/10
           15       0                  0                   51/60       1/10
           16       0                  0                   36/60       1/10
           17       0                  0                   33/60       1/10
           18       0                  0                   36/60       1/10
           19       0                  0                   39/60       1/10
           20       0                  0                   42/60       1/10
           21       0                  0                   45/60       1/10
           22       0                  0                   48/60       1/10
           23       0                  0                   51/60       1/10
           24       0                  0                   39/60       1/10
           25       0                  0                   33/60       1/10
           26       0                  0                   36/60       1/10
           27       0                  0                   39/60       1/10
           28       0                  0                   42/60       1/10
           29       0                  0                   45/60       1/10
           30       0                  0                   48/60       1/10
           31       0                  0                   51/60       1/10
           32       0                  0                   42/60       1/10
           33       0                  0                   33/60       1/10
           34       0                  0                   36/60       1/10
           35       0                  0                   39/60       1/10
           36       0                  0                   42/60       1/10
           37       0                  0                   45/60       1/10
           38       0                  0                   48/60       1/10
           39       0                  0                   51/60       1/10
           40       0                  0                   45/60       1/10
           41       0                  0                   33/60       1/10
           42       0                  0                   36/60       1/10
           43       0                  0                   39/60       1/10
           44       0                  0                   42/60       1/10
           45       0                  0                   45/60       1/10
           46       0                  0                   48/60       1/10
           47       0                  0                   51/60       1/10
           48       0                  0                   48/60       1/10
           49       0                  0                   33/60       1/10
           50       0                  0                   36/60       1/10
           51       0                  0                   39/60       1/10
           52       0                  0                   42/60       1/10
           53       0                  0                   45/60       1/10
           54       0                  0                   48/60       1/10
           55       0                  0                   51/60       1/10
           56       2                  0                   51/60       1/10
           57       0                  0                   33/60       1/10
           58       0                  0                   36/60       1/10
           59       0                  0                   39/60       1/10
           60       0                  0                   42/60       1/10
           61       0                  0                   45/60       1/10
           62       0                  0                   48/60       1/10
           63       0                  0                   51/60       1/10
  Class 'class-default': medium priority
    bandwidth 66750 kb/s, burst 163868 bytes, queue length/limit 0/50
    mean input rate 0 bits/s, mean output rate 0 bits/s
    packets output 0, packets dropped 0 (0%)
    bytes output 0, bytes dropped 0 (0%)
    remaining-bandwidth share 66, excess-rate-priority 0, excess packets sent 0
  Interface total:
    bandwidth 100000 kb/s
    mean input rate 104400 bits/s, mean output rate 104400 bits/s
    packets output 704745364, packets dropped 707805 (0%)
    bytes output 222877578682, bytes dropped 939630669 (0%)

```

**Help:** execute the command "show policy-interface output"

**Prompt:**
- oneaccess_oneos>
- oneaccess_oneos#

### show product-info-area

**Output:**
```
+----------------------------------------------------------------+
|                       Product Info Area                        |
+------------------------------+---------------------------------+
| Key                          | Value                           |
+------------------------------+---------------------------------+
| mac0                         | 70:FC:8C:07:22:CC               |
+------------------------------+---------------------------------+
| mac1                         | 70:FC:8C:0B:22:CC               |
+------------------------------+---------------------------------+
| mac2                         | 70:FC:8C:0F:22:CC               |
+------------------------------+---------------------------------+
| mac3                         | 70:FC:8C:13:22:CC               |
+------------------------------+---------------------------------+
| mac4                         | 70:FC:8C:17:22:CC               |
+------------------------------+---------------------------------+
| mac5                         | 70:FC:8C:1B:22:CC               |
+------------------------------+---------------------------------+
| mac6                         | 70:FC:8C:1F:22:CC               |
+------------------------------+---------------------------------+
| mac7                         | 70:FC:8C:23:22:CC               |
+------------------------------+---------------------------------+
| Manufacturing File Reference | 1000 00 N 0046230A00 AH         |
+------------------------------+---------------------------------+
| Motherboard Type             | MB420SAVad0UFPE0BNW             |
+------------------------------+---------------------------------+
| Manufacturing Location       | TOAB                            |
+------------------------------+---------------------------------+
| Manufacturing Date           | 18/01/2017                      |
+------------------------------+---------------------------------+
| Serial Number                | T1703006230033175               |
+------------------------------+---------------------------------+
| Product name                 | LBB_140                         |
+------------------------------+---------------------------------+
| Commercial name              | LBB 140                         |
+------------------------------+---------------------------------+
| Mreturn1                     |                                 |
+------------------------------+---------------------------------+
| Mreturn2                     |                                 |
+------------------------------+---------------------------------+
| Mreturn3                     |                                 |
+------------------------------+---------------------------------+
| Mreturn4                     |                                 |
+------------------------------+---------------------------------+

```

**Help:** execute the command "show product-info-area"

**Prompt:**
- oneaccess_oneos>
- oneaccess_oneos#

### show reboot counters

**Output:**
```


Reboot status for device LBB_154 S/N T2047008177055804

Last Reboot Cause : Software requested / System defense - reboot after crash

Reboot Counters :
Reboot on hardware reset                         : 0
Power Fail detection                             : 9
Total Software Requested Reboots                 : 7
  System defense - reboot after crash            : 6
  Administrator requested delayed reboot         : 1

```

**Help:** execute the command "show reboot counters"

**Prompt:**
- oneaccess_oneos>
- oneaccess_oneos#

### show route-map

**Output:**
```
route-map BGP-MAP-OUT permit 10
 match as-path 102
 set origin igp
 set metric 50
exit
route-map BGP_SECONDARY_OUT permit 10
 set as-path prepend 65000 65000 65000
 set origin       igp
 set local-preference 50
 set metric       100
exit
route-map CONNECTED-BGP deny 5
 match ip address prefix-list DENY-BGP
exit
route-map CONNECTED-BGP permit 10
 set origin       igp
 set local-preference 100
 set metric       50
exit

```

**Help:** execute the command "show route-map"

**Prompt:**
- oneaccess_oneos>
- oneaccess_oneos#

### show running-config aaa

**Output:**
```
aaa group server tacacs TACGROUP
aaa authentication login default TACGROUP
aaa authentication login console TACGROUP
aaa authentication enable default TACGROUP
aaa authentication enable console TACGROUP
aaa authorization command 15 TACGROUP none
aaa authorization command 7 TACGROUP none
aaa authorization command 1 TACGROUP none
aaa authorization command 0 TACGROUP none
aaa authorization network group TACGROUP
aaa accounting exec default start-stop group TACGROUP
aaa accounting commands 15 default stop-only group TACGROUP
aaa accounting system default start-stop group TACGROUP
aaa accounting commands 7 default stop-only group TACGROUP
aaa accounting commands 1 default stop-only group TACGROUP
aaa accounting commands 0 default stop-only group TACGROUP
aaa authentication banner sequence 1 *-TACACS SERVER UNAVAILABLE-*

```

**Help:** execute the command "show running-config aaa"

**Prompt:**
- oneaccess_oneos>
- oneaccess_oneos#

### show running-config bind

**Output:**
```
bind ssh acl MANAGEMENT_IN_SSH
bind ssh loopback 1
bind ssh loopback 21
bind ssh loopback 91
bind ssh tunnel 21
bind ssh tunnel 91
bind ssh virtual-ethernet 1
bind ssh vrf UNTRUST-SSH
bind ssh vrf default-router
bind telnet acl MANAGEMENT_IN_TELNET
bind telnet loopback 1
bind telnet loopback 21
bind telnet loopback 91
bind telnet tunnel 21
bind telnet tunnel 91
bind telnet virtual-ethernet 1
bind telnet vrf UNTRUST-TELNET
bind telnet vrf default-router

```

**Help:** execute the command "show running-config bind"

**Prompt:**
- oneaccess_oneos>
- oneaccess_oneos#

### show running-config ip dhcp

**Output:**
```
ip dhcp vrf INTERNET excluded-address 192.168.10.1
ip dhcp pool DHCP_LBB                
 vrf INTERNET
 lease 0 8 0
default-router 192.168.10.1
dns-server 212.224.255.252 212.224.255.254
network 192.168.10.0 255.255.255.0
exit
ip dhcp pool OrangeShopWifi-VLAN20
lease 0 8 0
domain-name  OrangeShopWifi
default-router 10.32.60.1
dns-server 212.224.129.90 212.224.129.94
network 10.32.60.0 255.255.255.0
exit
ip dhcp pool OrangeShopDigitalSignage-VLAN30
lease 0 8 0
default-router 10.42.60.1
domain-name  OrangeShopDigitalSignage
dns-server 212.224.129.90 212.224.129.94
network 10.42.60.0 255.255.255.0
exit
ip dhcp pool OrangeShopSecurity-VLAN40
lease 0 8 0
default-router 10.52.60.1
domain-name  OrangeShopSecurity
dns-server 212.224.129.90 212.224.129.94
network 10.52.60.0 255.255.255.0
exit
ip dhcp pool TEST-MAARTEN
dns-server 10.200.19.4 10.200.19.5
exit
ip dhcp pool TEST-FEDERALE-WOUTER
dns-server 10.20.25.6 10.0.1.228 172.20.64.13
domain-name  federale.be
exit
ip dhcp pool TEST1
dns-server 1.1.1.1 192.168.50.20 192.168.50.30 2.2.2.2 3.3.3.3
exit
!

```

**Help:** execute the command "show running-config ip dhcp"

**Prompt:**
- oneaccess_oneos>
- oneaccess_oneos#

### show running-config ip route

**Output:**
```
ip route 94.105.1.119 255.255.255.255 192.168.100.2
ip route 94.105.16.130 255.255.255.255 Bvi 200
ip route 94.105.34.2 255.255.255.255 192.168.100.3

```

**Help:** execute the command "show running-config ip route"

**Prompt:**
- oneaccess_oneos>
- oneaccess_oneos#

### show snmp community

**Output:**
```
SNMP write community: Kl3t5k0p
SNMP access control lists :52
SNMP read community: 5pr1t5
SNMP access control lists :52

```

**Help:** execute the command "show snmp community"

**Prompt:**
- oneaccess_oneos>
- oneaccess_oneos#

### show sntp

**Output:**
```
server                                  source                                  stratum  version   last     receive
101.208.220.147                          Loopback 1                              
10.208.220.19                           Loopback 1                                 5       1      00:00:39   synced

broadcast client mode is not enabled
SNTP Authentication is not enabled

```

**Help:** execute the command "show sntp"

**Prompt:**
- oneaccess_oneos>
- oneaccess_oneos#

### show soft-file info

**Output:**
```
Binary file informations : 
  file name              = /BSA/binaries/OneOs
  software version       = ONEOS92-DUAL_FT-V5.2R2E7_HA8
  software creation date = 04/08/20 17:31:55
  file size              = 13852345 (0xD35EB9)
  header checksum        = 0xD920F600
  computed checksum      = 0xD920F600
  target device          = One92
file is OK

```

**Help:** execute the command "show soft-file info"

**Prompt:**
- oneaccess_oneos>
- oneaccess_oneos#

### show software-image

**Output:**
```
--------------- Active bank ---------------
Software version : OneOS-pCPE-ARM_pi1-6.8.4
Creation date    : 2022-08-02 16:59:01
Header checksum  : 0x16368E60

-------------- Alternate bank -------------
Software version : OneOS-pCPE-ARM_pi1-6.6.1m3
Creation date    : 2021-03-26 11:13:54
Header checksum  : 0x73ED8876

```

**Help:** execute the command "show software-image"

**Prompt:**
- oneaccess_oneos>
- oneaccess_oneos#

### show system hardware

**Output:**
```
 HARDWARE DESCRIPTION

  Device   : LBB_150
  CPU      : BCM63136 - ARMv7 Processor rev 1 (v7l)

 Core Freq : 1000MHz   DDR Freq : 800MHz (1600 MT/s data rate) 
 Physical Ram size :   1GiB  
 Nand Flash size : 512MiB  


 Secure Boot protection : yes


 Local   : x Uplink : x Radio :      Usb :     

 Local   : GIGABIT ETHERNET + SFP ETHERNET + SWITCH ETHERNET / 4 ports
 Uplink  : AVDSL/1 Pair POTS 
 Wlan 0 : BCM43602 - 2,4GHz - 3x3
 Wlan 1 : BCM4366 - 5GHz - 4x4

```

**Help:** execute the command "show system hardware"

**Prompt:**
- oneaccess_oneos>
- oneaccess_oneos#

### show system secure-crashlog

**Output:**
```
coredump_00011_2022-02-25T2003_tExcTask-6-1668-0-0.txt
------------------------------------------------------
Crash caused by     : Program terminated with signal SIGABRT, Aborted.
Crash time          : 2022-02-25 2003
Crash filename      : /BSA/dump/coredump_00011_2022-02-25T2003_tExcTask-6-1668-0-0.xz
Device identifier   : PBXPLUG_103 S/N T2137008344020891

Software version    : OneOS-pCPE-ARM_pi2-6.7.1m2 (integci_r1_1pa290b4_dev_photo116)
Software created on : 2021-10-08 15:30:45
Boot version        : BOOT-ARM_hw2-3.1.3 (integ_r1_1pa4b1_dev_b313std (CFE r1_3pa4))
Boot created on     : 2019-05-27 11:12:53
Recovery version    : OneOs-RCY-ARM_pi2-1.3.6 (integ_r1_1pa19b1_dev_b136std)
Recovery created on : 2019-10-11 09:21:48

System started      : 2022-01-28 03:00:51
Start caused by     : Generic software reboot request
Sys Up time         : 28d 17h 4m 3s
Core was generated by '/usr/bin/cp_voice'
* Backtrace
*
#0  0xb55a9ab4 in raise () from /lib/libc.so.6
No symbol table info available.
#1  0xb55ad774 in abort () from /lib/libc.so.6
No symbol table info available.
#2  0xb55a259c in __assert_fail_base () from /lib/libc.so.6
No symbol table info available.
#3  0xb55a2678 in __assert_fail () from /lib/libc.so.6
No symbol table info available.
#4  0xb56c2e4c in pthread_mutex_lock () from /lib/libpthread.so.0
No symbol table info available.
#5  0xb54a034c in wdog_valid () from /usr/lib/libv2lin.so
No symbol table info available.
#6  0xb54a0434 in process_tick_for () from /usr/lib/libv2lin.so
No symbol table info available.
#7  0xb54a068c in process_timer_list () from /usr/lib/libv2lin.so
No symbol table info available.
#8  0xb5494774 in exception_task () from /usr/lib/libv2lin.so
No symbol table info available.
#9  0xb549524c in task_wrapper () from /usr/lib/libv2lin.so
No symbol table info available.
#10 0xb56bff20 in start_thread () from /lib/libpthread.so.0
No symbol table info available.
#11 0xb5651e30 in ?? () from /lib/libc.so.6
*
* Registers
*
r0             0x0      0
r1             0x708    1800
r2             0x6      6
r3             0xb48678b0       3028711600
r4             0x2      2
r5             0xb56b70a4       3043717284
r6             0xb48673f0       3028710384
r7             0x10c    268
r8             0x0      0
r9             0xb4866864       3028707428
r10            0x1      1
r11            0x134170 1261936
r12            0x0      0
sp             0xb486685c       0xb486685c
lr             0xb55ad774       3042629492
pc             0xb55a9ab4       0xb55a9ab4 <raise+52>
cpsr           0x20030010       537067536
*
* Current instructions
*
=> 0xb55a9ab4 <raise+52>:       cmn     r0, #4096       ; 0x1000
   0xb55a9ab8 <raise+56>:       pop     {r7}            ; (ldr r7, [sp], #4)
   0xb55a9abc <raise+60>:       ldrhi   r2, [pc, #44]   ; 0xb55a9af0 <raise+112>
   0xb55a9ac0 <raise+64>:       rsbhi   r1, r0, #0
   0xb55a9ac4 <raise+68>:       mvnhi   r0, #0
   0xb55a9ac8 <raise+72>:       ldrhi   r2, [pc, r2]
   0xb55a9acc <raise+76>:       strhi   r1, [r3, r2]
   0xb55a9ad0 <raise+80>:       bx      lr
   0xb55a9ad4 <raise+84>:       cmp     r0, #0
   0xb55a9ad8 <raise+88>:       bgt     0xb55a9aac <raise+44>
   0xb55a9adc <raise+92>:       bic     r12, r0, #-2147483648   ; 0x80000000
   0xb55a9ae0 <raise+96>:       cmp     r12, #0
   0xb55a9ae4 <raise+100>:      rsbne   r0, r0, #0
   0xb55a9ae8 <raise+104>:      moveq   r0, r1
   0xb55a9aec <raise+108>:      b       0xb55a9aac <raise+44>
   0xb55a9af0 <raise+112>:      andseq  r12, r0, r12, ror #11

*
* End of file
*

```

**Help:** execute the command "show system secure-crashlog"

**Prompt:**
- oneaccess_oneos>
- oneaccess_oneos#

### show system status

**Output:**
```
System Information for device MB420SAVad0UFPE0BNW S/N T1703006230033175

Software version    : ONEOS16-MONO_FT-V5.2R2E7_HA8
Software created on : 04/08/20 18:14:48
License token       : None
Boot version        : BOOT16-SEC-V3.4R3E40C
Boot created on     : 14/06/16 09:34:31

Boot Flags          : 0x00000008

Current system time : 29/09/22 13:41:52
System started      : 02/07/22 16:20:10
Start caused by     : Power Fail detection
Sys Up time         : 88d 21h 21m 42s
System clock ticks  : 384072819

Current CPU load    : 16.1%
Current Critical Tasks CPU load           : 14.4%
Current Non Critical Tasks CPU load       : 1.7%
Average CPU load (5 / 60 Minutes)         : 15.8% / 15.6%

Free / Max RAM      :  163,04 /  208,59 MB

```

**Help:** execute the command "show system status"

**Prompt:**
- oneaccess_oneos>
- oneaccess_oneos#

### show tacacs

**Output:**
```
 TACACS+ SERVER Statistics
 --------------------------
  Tacacs+ Server  Address     : 91.208.220.142
  Server port                 : 49
  Number of sockets open      : 14196
  Number of sockets closed    : 13677
  Number of sockets aborted   : 0
  Number of sockets error     : 0
  Number of sockets timeout   : 0
  Number of connect fails     : 4
  Number of packets sent      : 14590
  Number of packets received  : 14590

  Tacacs+ Server  Address     : 1.2.3.4
  Server port                 : 49
  Number of sockets open      : 5124
  Number of sockets closed    : 4933
  Number of sockets aborted   : 0
  Number of sockets error     : 0
  Number of sockets timeout   : 0
  Number of connect fails     : 0
  Number of packets sent      : 5264
  Number of packets received  : 5264

  Tacacs+ Server  Address     : 11.22.33.44
  Server port                 : 49
  Number of sockets open      : 126
  Number of sockets closed    : 119
  Number of sockets aborted   : 0
  Number of sockets error     : 0
  Number of sockets timeout   : 0
  Number of connect fails     : 21
  Number of packets sent      : 105
  Number of packets received  : 105

```

**Help:** execute the command "show tacacs"

**Prompt:**
- oneaccess_oneos>
- oneaccess_oneos#

### show tacacs-server

**Output:**
```
----- List of TACACS+ server -----

  IP address      Port      Secret Key                     Source address     VRF
 1.1.1.1   49      6b57e38f62d089b98be63ff357fccc9e9d959eba64bc   Loopback 1
  2.2.2.2   49      6b57e38f62d089b98be63ff357fccc9e9d959eba64bc   Loopback 1
  3.3.3.3   49      6b57e38f62d089b98be63ff357fccc9e9d959eba64bc   Loopback 1

```

**Help:** execute the command "show tacacs-server"

**Prompt:**
- oneaccess_oneos>
- oneaccess_oneos#

### show track all

**Output:**
```

 Track 1 

   interface GigabitEthernet 0/0 ip-routing 

   Ip-routing is UP 

   1 Change, Last Change 12:48:41 

   Up Delay 2, Down Delay 2

   Poll Interval (in msec) 1000 


 Track 2 

   interface GigabitEthernet 0/1 ip-routing 

   Ip-routing is UP 

   1 Change, Last Change 12:48:41 

   Up Delay 2, Down Delay 2

   Poll Interval (in msec) 1000 


 Track 3 

   interface GigabitEthernet 0/2 ip-routing 

   Ip-routing is UP 

   1 Change, Last Change 12:48:41 

   Up Delay 2, Down Delay 2

   Poll Interval (in msec) 1000 


 Track 4 

   VRRP Id 4 vrf ORANGE_APN_WGKAIOT_0001 

   Vrrp is UP 

   3 Change, Last Change 09:14:18 

   Up Delay 2, Down Delay 2

   Poll Interval (in msec) 3000 

```

**Help:** execute the command "show track all"

**Prompt:**
- oneaccess_oneos>
- oneaccess_oneos#

### show transceiver equipment

**Output:**
```

No SFP module present

```

**Help:** execute the command "show transceiver equipment"

**Prompt:**
- oneaccess_oneos>
- oneaccess_oneos#

### show voice dial-peer voice voip all

**Output:**
```
	Dial Peer						0
	Config state						up
	Operstatus						up
	Registration status					unused
	Current protocol					sip  (UDP)
	lastOK 							0
	User Agent						(null)
	 Bandwidth really used/CAC value/unused			0 / 0/ 2147483647 bps
	Current sip-protocol-mode				ipv4  (config : ipv4)
	Current Calls						0
				Outgoing Calls
		Outgoing Calls					0
		Bandwidth really used/CAC value/unused		0 / 0/ 2147483647 bps
		Outgoing calls failures				0
		Q931 Call failures				0
			Cause Class 0 (normal event)		0
			Cause Class 1 (normal event)		0
				Normal Cause (16)		0
				User busy (17)			0
				No answer (18)			0
			Cause Class 2 (unavailable resources)	0
			Cause Class 3 (unavailable service)	0
			Cause Class 4 (service not provided)	0
			Cause Class 5 (invalid message)		0
			Cause Class 6 (protocol error)		0
			Cause Class 7 (interworking)		0
		SIP Call failures				0
			Incompatible capabilities		0
			Protocol errors				0
		Internal call failures				0
	 		DSP unavailable				0
			Max-bandwidth exceeded			0
			Max-connection exceeded			0
			RTP dynamic-payload error		0
			Not specified				0
				Incoming Calls
		Incoming calls					0
		Bandwidth really used/CAC value/unused		0 / 0/ 2147483647 bps
		Incoming calls failures				0
		Local Port Call failures			0
		SIP Call failures				0
			Incompatible capabilities		0
			Protocol errors				0
		 Internal call failures				0
			DSP unavailable				0
			Unknown number				0
			Channel / port unavailable		0
			Max-bandwidth exceeded			0
			Max-connection exceeded			0
			RTP dynamic-payload error		0
			Not specified				0
				Voice & Fax statistics
	 	Number of real dsp switching			0
	RTP statistics
		Number of transmitted packets			0
		Number of received packets			0
		Number of transmitted bytes			0
		Number of received bytes			0
		Number of excessive jitter events		0
		Number of lost packets				0
		Number of invalid packets			0
	Number of calls with frame error rate
		 total <0.01%  <0.1%  <0.5%    <1%    <5%   >=5%
		     0      0      0      0      0      0      0
	Modem passthrough
		Number of switching to modem mode		0
	T38 FAX Calls
		Number of outgoing fax				0
		Number of incoming fax				0
	 	Number of failures				0
			Request Mode failure			0
			Pre-message procedure failure		0
			Page failure				0
		Number of transmitted packets			0
		Number of received packets			0
		Number of transmitted bytes			0
		Number of received bytes			0
		Number of lost packets				0
 
```

**Help:** execute the command "show voice dial-peer voice voip all"

**Prompt:**
- oneaccess_oneos>
- oneaccess_oneos#

### show voice mos

**Output:**
```
     ------------------------- Call Quality -------------------------

     ------------------------- Current hour -------------------------
         Number of Call       : 0 
         Average of MOS       : 0.00 
         Minimum MOS          : 0.00 
         Maximum MOS          : 0.00 
         Average of ERL       : 0 
         Average of ACOM      : 0 
         Average of loss-rate : 0 
         Average of jitter    : 0 
         Average of Max delay : 0 
         Average Pdd          : 0 

     ------------------------- Previous hour ------------------------
         Number of Call       : 1 
         Average of MOS       : 4.34 
         Minimum MOS          : 4.34 
         Maximum MOS          : 4.34 
         Average of ERL       : 14 
         Average of ACOM      : 43 
         Average of loss-rate : 0 
         Average of jitter    : 0 
         Average of Max delay : 3 
         Average Pdd          : 0 

     ----------------------------------------------------------------

```

**Help:** execute the command "show voice mos"

**Prompt:**
- oneaccess_oneos>
- oneaccess_oneos#

### show voice sip-gateway

**Output:**
```
	Sip-Gateway statistics : 
	Gateway state				up
	Operstatus				up
	SIP-GW entity opened sockets:
	  UDP sockets:
		Sockidx: 0, 1.2.3.4:5060
	Registration state			registered
	RTP monitoring				disable
	Nb Registered endpoints/Max to register/Registrar server:
		[1/1]				blabla:5060
	Bandwidth really used/CAC value/unused	0 / 0/ 2147483647 bps 
	Threshold of bandwidth to switch	unused
	Max Bandwidth exceeded			0
	Number of lower switching		0
	Registration errors			0

	Current sip-protocol-mode		ipv4  (config : ipv4)
	Current call				0
	Calls released by rtp monitoring	0

	Authentication Rejects			0

	Dropped packets				0
		due to rate limitation		0
		due to memory limitation	0
		due to CPU limitation		0
		due to denied by acl		0
		due to unknown proxy		0

```

**Help:** execute the command "show voice sip-gateway"

**Prompt:**
- oneaccess_oneos>
- oneaccess_oneos#

### show voice voice-port all

**Output:**
```
	port :  0   lp :  0   sense : PRI         if-state : noShutdown  (vp-state : noShutdown)               
	port :  1   lp :  0   sense : BRI         if-state : Shutdown    (vp-state : noShutdown)               
	port :  2   lp :  1   sense : BRI         if-state : Shutdown    (vp-state : noShutdown)               
	port :  3   lp :  0   sense : POTS [FXS]  vp-state : noShutdown               
	port :  4   lp :  1   sense : POTS [FXS]  vp-state : noShutdown               
	port :  5   lp :  2   sense : POTS [FXS]  vp-state : noShutdown               
	port :  6   lp :  3   sense : POTS [FXS]  vp-state : noShutdown               

```

**Help:** execute the command "show voice voice-port all"

**Prompt:**
- oneaccess_oneos>
- oneaccess_oneos#

### show voice voice-port pri all

**Output:**
```
	voice port				5/0
		physical type			E1
		protocol descriptor		E1_PRI
		config state			up
		loop state			down 
		framing				DF
		layer 1 status			deactivated
		 Alarm Indication Signal (AIS)	OFF
		 Loss Off Signal (LOS)		ON
		 Remote Alarm Indication (RAI)	OFF
		 pri AIS occurrence(s)		0
		 pri LOS occurrence(s)		1
		 pri RAI occurrence(s)		0
		layer 2 status			deactivated
		attached voip dial peer		0
		number of voice communication	0
		Channel(s) used			
 
		Outgoing calls				0
		Outgoing calls failures			0
	 		Physical Interface down			0
			Cause Class 0 (normal event)		0
			Cause Class 1 (normal event)		0
				Normal Cause (16)		0
		 		User busy (17)			0
				No answer (18)			0
			Cause Class 2 (unavailable resources)	0
			Cause Class 3 (unavailable service)	0
			Cause Class 4 (service not provided)	0
			Cause Class 5 (invalid message)		0
			Cause Class 6 (protocol error)		0
			Cause Class 7 (interworking)		0
 
		Incoming calls				0
		Incoming calls backup invoked		0
		Incoming calls failures			0
			Remote failure				0
			Unknown number				0
			DSP unavailable				0
			No VoIP resource available		0
			Not specified				0

```

**Help:** execute the command "show voice voice-port pri all"

**Prompt:**
- oneaccess_oneos>
- oneaccess_oneos#

### show voice voice-port pri all histo

**Output:**
```
	voice port				5/0
		physical type			E1
		protocol descriptor		E1_PRI
		attached voip dial peer		0
		date of last reset		28/12/2022 03:05
		max channel(s) used		0/30
		daily occupancy of B channels
		  %
		100 |                                                                                               
		 90 |                                                                                               
		 80 |                                                                                               
		 70 |                                                                                               
		 60 |                                                                                               
		 50 |                                                                                               
		 40 |                                                                                               
		 30 |                                                                                               
		 20 |                                                                                               
		 10 |                                                                                               
		  0 +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
		      00  01  02  03  04  05  06  07  08  09  10  11  12  13  14  15  16  17  18  19  20  21  22  23   H.

```

**Help:** execute the command "show voice voice-port pri all histo"

**Prompt:**
- oneaccess_oneos>
- oneaccess_oneos#

### show voice voip-call active all

**Output:** None

**Help:** execute the command "show voice voip-call active all"

**Prompt:**
- oneaccess_oneos>
- oneaccess_oneos#

### show voice voip-call any all

**Output:**
```

 1 - Call from remote voip: 0  (UDP), to local port: 5/0 call-id: 151 (390) 
     calling : 490446941, called : 55335275
     setup time:  11/01/23 21h52m53s
     connexion time: 11/01/23 21h53m07s
         B channel (from B1..) : B1
     disconnected by local port: 5/0 cause :(16)[Normal call clearing]
     call duration: 00:02:31
     PDD duration: 283 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16452 /Dest ip :212.224.167.110 rtp:23394
     Play time (voice) : 00h02m31s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 7544 / 7531
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / --
     Number of Excessive Jitter events : 0
     MOS-CQ / MOS-LQ   : 4.34 / 4.39 
     ERL   : 14 dB
     ACOM  : 43 dB


 2 - Call from remote voip: 0  (UDP), to local port: 5/0 call-id: 150 (389) 
     calling : 490446941, called : 55335275
     setup time:  11/01/23 21h27m06s
     connexion time: 11/01/23 21h27m33s
         B channel (from B1..) : B1
     disconnected by remote voip: 0  (UDP) cause :(16)[Normal call clearing]
     call duration: 00:01:36
     PDD duration: 270 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16450 /Dest ip :212.224.167.110 rtp:23492
     Play time (voice) : 00h01m36s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 4814 / 4807
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / --
     Number of Excessive Jitter events : 0
     MOS-CQ / MOS-LQ   : 4.34 / 4.39 
     ERL   : 13 dB
     ACOM  : 40 dB


 3 - Call from remote voip: 0  (UDP), to local port: 5/0 call-id: 149 (388) 
     calling : 488313757, called : 55337751
     setup time:  11/01/23 20h25m09s
     connexion time: 11/01/23 20h25m09s
         B channel (from B1..) : B1
     disconnected by remote voip: 0  (UDP) cause :(16)[Normal call clearing]
     call duration: 00:00:05
     PDD duration: 102 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16448 /Dest ip :212.224.167.110 rtp:23440
     Play time (voice) : 00h00m05s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 244 / 245
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / 0
     Number of Excessive Jitter events : 0
     MOS-CQ / MOS-LQ   : -- / -- 
     ERL   : -- dB
     ACOM  : 255 dB


 4 - Call from remote voip: 0  (UDP), to local port: 5/0 call-id: 148 (387) 
     calling : 488313757, called : 55337751
     setup time:  11/01/23 20h24m56s
     connexion time: 11/01/23 20h24m56s
         B channel (from B1..) : B1
     disconnected by remote voip: 0  (UDP) cause :(16)[Normal call clearing]
     call duration: 00:00:06
     PDD duration: 155 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16446 /Dest ip :212.224.167.110 rtp:23418
     Play time (voice) : 00h00m06s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 272 / 273
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / 0
     Number of Excessive Jitter events : 0
     MOS-CQ / MOS-LQ   : -- / -- 
     ERL   : -- dB
     ACOM  : 255 dB


 5 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 147 (386) 
     calling : 3255335278, called : 3250703433
     setup time:  11/01/23 16h33m08s
     connexion time: 11/01/23 16h33m09s
         B channel (from B1..) : B1
     disconnected by local port: 5/0 cause :(16)[Normal call clearing]
     call duration: 00:02:11
     PDD duration: 847 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16444 /Dest ip :212.224.167.110 rtp:23192
     Play time (voice) : 00h02m11s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 6529 / 6529
     RTP Packet lost&discarded RX / TX (RTCP reported) : 13 / 0
     Number of Excessive Jitter events : 1
     MOS-CQ / MOS-LQ   : 4.33 / 4.39 
     ERL   : 40 dB
     ACOM  : 66 dB


 6 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 144 (383) 
     calling : 3255335278, called : 3250703433
     setup time:  11/01/23 16h15m11s
     connexion time: 11/01/23 16h15m12s
         B channel (from B1..) : B1
     disconnected by local port: 5/0 cause :(16)[Normal call clearing]
     call duration: 00:13:29
     PDD duration: 708 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16438 /Dest ip :212.224.167.110 rtp:23156
     Play time (voice) : 00h13m29s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 40459 / 40459
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / 0
     Number of Excessive Jitter events : 1
     MOS-CQ / MOS-LQ   : 4.35 / 4.39 
     ERL   : 37 dB
     ACOM  : 64 dB


 7 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 146 (385) 
     calling : 32491169975, called : 32490661143
     setup time:  11/01/23 16h22m35s
     connexion time: 11/01/23 16h22m39s
         B channel (from B1..) : B3
     disconnected by local port: 5/0 cause :(16)[Normal call clearing]
     call duration: 00:02:48
     PDD duration: 599 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16440 /Dest ip :212.224.167.110 rtp:23196
     Play time (voice) : 00h02m48s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 8567 / 8567
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / --
     Number of Excessive Jitter events : 0
     MOS-CQ / MOS-LQ   : 4.35 / 4.39 
     ERL   : 24 dB
     ACOM  : 73 dB


 8 - Call from remote voip: 0  (UDP), to local port: 5/0 call-id: 145 (384) 
     calling : 491169975, called : 55337505
     setup time:  11/01/23 16h22m35s
     connexion time: 11/01/23 16h22m39s
         B channel (from B1..) : B2
     disconnected by remote voip: 0  (UDP) cause :(16)[Normal call clearing]
     call duration: 00:02:48
     PDD duration: 852 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16442 /Dest ip :212.224.167.110 rtp:23180
     Play time (voice) : 00h02m48s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 8390 / 8382
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / --
     Number of Excessive Jitter events : 0
     MOS-CQ / MOS-LQ   : 4.34 / 4.39 
     ERL   : 32 dB
     ACOM  : 58 dB


 9 - Call from remote voip: 0  (UDP), to local port: 5/0 call-id: 143 (382) 
     calling : 492819960, called : 55335206
     setup time:  11/01/23 16h06m05s
     connexion time: 11/01/23 16h06m08s
         B channel (from B1..) : B1
     disconnected by local port: 5/0 cause :(16)[Normal call clearing]
     call duration: 00:00:19
     PDD duration: 377 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16436 /Dest ip :212.224.167.110 rtp:23128
     Play time (voice) : 00h00m19s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 943 / 929
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / 0
     Number of Excessive Jitter events : 0
     MOS-CQ / MOS-LQ   : 4.34 / 4.39 
     ERL   : 42 dB
     ACOM  : 67 dB


 10 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 142 (381) 
     calling : 3255335346, called : 32490661137
     setup time:  11/01/23 16h04m09s
     connexion time: 11/01/23 16h04m17s
         B channel (from B1..) : B1
     disconnected by remote voip: 0  (UDP) cause :(16)[Normal call clearing]
     call duration: 00:00:10
     PDD duration: 2088 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16434 /Dest ip :212.224.167.110 rtp:23122
     Play time (voice) : 00h00m10s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 801 / 801
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / --
     Number of Excessive Jitter events : 0
     MOS-CQ / MOS-LQ   : 4.34 / 4.39 
     ERL   : 28 dB
     ACOM  : 51 dB


 11 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 141 (380) 
     calling : 3255335241, called : 32498178799
     setup time:  11/01/23 15h59m31s
     connexion time: 11/01/23 15h59m55s
         B channel (from B1..) : B1
     disconnected by local port: 5/0 cause :(16)[Normal call clearing]
     call duration: 00:00:02
     PDD duration: 1422 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16432 /Dest ip :212.224.167.110 rtp:23074
     Play time (voice) : 00h00m02s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 1182 / 1199
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / 0
     Number of Excessive Jitter events : 1
     MOS-CQ / MOS-LQ   : 4.34 / 4.39 
     ERL   : 66 dB
     ACOM  : 90 dB


 12 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 140 (379) 
     calling : 3255335278, called : 32492819960
     setup time:  11/01/23 15h42m36s
     connexion time: 11/01/23 15h43m00s
         B channel (from B1..) : B1
     disconnected by local port: 5/0 cause :(16)[Normal call clearing]
     call duration: 00:00:04
     PDD duration: 967 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16430 /Dest ip :212.224.167.110 rtp:23008
     Play time (voice) : 00h00m04s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 1318 / 1334
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / 0
     Number of Excessive Jitter events : 3
     MOS-CQ / MOS-LQ   : 4.34 / 4.39 
     ERL   : 67 dB
     ACOM  : 91 dB


 13 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 139 (378) 
     calling : 3255335278, called : 32492819960
     setup time:  11/01/23 15h41m50s
     connexion time: 11/01/23 15h42m14s
         B channel (from B1..) : B1
     disconnected by local port: 5/0 cause :(16)[Normal call clearing]
     call duration: 00:00:05
     PDD duration: 1041 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16428 /Dest ip :212.224.167.110 rtp:23006
     Play time (voice) : 00h00m05s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 1379 / 1391
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / 0
     Number of Excessive Jitter events : 3
     MOS-CQ / MOS-LQ   : 4.34 / 4.39 
     ERL   : 67 dB
     ACOM  : 91 dB


 14 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 138 (377) 
     calling : 3255335206, called : 32492819960
     setup time:  11/01/23 15h10m36s
     connexion time: 11/01/23 15h10m48s
         B channel (from B1..) : B1
     disconnected by local port: 5/0 cause :(16)[Normal call clearing]
     call duration: 00:00:17
     PDD duration: 1464 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16426 /Dest ip :212.224.167.110 rtp:22878
     Play time (voice) : 00h00m17s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 1356 / 1373
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / 0
     Number of Excessive Jitter events : 1
     MOS-CQ / MOS-LQ   : 4.34 / 4.39 
     ERL   : 24 dB
     ACOM  : 54 dB


 15 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 137 (376) 
     calling : 3255337739, called : 32491169927
     setup time:  11/01/23 15h07m19s
     connexion time: 11/01/23 15h07m43s
         B channel (from B1..) : B1
     disconnected by local port: 5/0 cause :(16)[Normal call clearing]
     call duration: 00:00:07
     PDD duration: 1515 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16424 /Dest ip :212.224.167.110 rtp:22890
     Play time (voice) : 00h00m07s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 1458 / 1462
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / 0
     Number of Excessive Jitter events : 3
     MOS-CQ / MOS-LQ   : 4.34 / 4.39 
     ERL   : 41 dB
     ACOM  : 71 dB


 16 - Call from remote voip: 0  (UDP), to local port: 5/0 call-id: 136 (375) 
     calling : 490661133, called : 55335206
     setup time:  11/01/23 15h02m05s
     connexion time: 11/01/23 15h02m07s
         B channel (from B1..) : B1
     disconnected by local port: 5/0 cause :(16)[Normal call clearing]
     call duration: 00:01:04
     PDD duration: 361 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16422 /Dest ip :212.224.167.110 rtp:22866
     Play time (voice) : 00h01m04s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 3199 / 3187
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / --
     Number of Excessive Jitter events : 0
     MOS-CQ / MOS-LQ   : 4.34 / 4.39 
     ERL   : 38 dB
     ACOM  : 65 dB


 17 - Call from remote voip: 0  (UDP), to local port: 5/0 call-id: 135 (374) 
     calling : 495914834, called : 55335241
     setup time:  11/01/23 14h58m35s
     connexion time: 11/01/23 14h58m38s
         B channel (from B1..) : B1
     disconnected by remote voip: 0  (UDP) cause :(16)[Normal call clearing]
     call duration: 00:02:05
     PDD duration: 321 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16420 /Dest ip :212.224.167.110 rtp:22838
     Play time (voice) : 00h02m05s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 6214 / 6200
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / --
     Number of Excessive Jitter events : 0
     MOS-CQ / MOS-LQ   : 4.34 / 4.39 
     ERL   : 18 dB
     ACOM  : 42 dB


 18 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 134 (373) 
     calling : 3255337758, called : 32490661150
     setup time:  11/01/23 14h54m36s
     connexion time: 11/01/23 14h54m49s
         B channel (from B1..) : B1
     disconnected by local port: 5/0 cause :(16)[Normal call clearing]
     call duration: 00:01:51
     PDD duration: 3148 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16418 /Dest ip :212.224.167.110 rtp:22826
     Play time (voice) : 00h01m51s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 6031 / 6066
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / 0
     Number of Excessive Jitter events : 1
     MOS-CQ / MOS-LQ   : 4.38 / 4.39 
     ERL   : 40 dB
     ACOM  : 59 dB


 19 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 133 (372) 
     calling : 32499172658, called : 32490446941
     setup time:  11/01/23 14h53m42s
     connexion time: 11/01/23 14h54m06s
         B channel (from B1..) : B2
     disconnected by local port: 5/0 cause :(16)[Normal call clearing]
     call duration: 00:00:12
     PDD duration: 1136 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16414 /Dest ip :212.224.167.110 rtp:22808
     Play time (voice) : 00h00m12s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 1758 / 1760
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / 0
     Number of Excessive Jitter events : 3
     MOS-CQ / MOS-LQ   : 4.35 / 4.39 
     ERL   : 28 dB
     ACOM  : 66 dB


 20 - Call from remote voip: 0  (UDP), to local port: 5/0 call-id: 132 (371) 
     calling : 499172658, called : 55335361
     setup time:  11/01/23 14h53m42s
     connexion time: 11/01/23 14h54m06s
         B channel (from B1..) : B1
     disconnected by remote voip: 0  (UDP) cause :(16)[Normal call clearing]
     call duration: 00:00:12
     PDD duration: 1393 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16416 /Dest ip :212.224.167.110 rtp:22802
     Play time (voice) : 00h00m12s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 598 / 602
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / 0
     Number of Excessive Jitter events : 0
     MOS-CQ / MOS-LQ   : 4.34 / 4.39 
     ERL   : 20 dB
     ACOM  : 75 dB


 21 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 131 (370) 
     calling : 3255335346, called : 32490661134
     setup time:  11/01/23 14h41m09s
     connexion time: 11/01/23 14h41m21s
         B channel (from B1..) : B1
     disconnected by local port: 5/0 cause :(16)[Normal call clearing]
     call duration: 00:00:30
     PDD duration: 2115 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16412 /Dest ip :212.224.167.110 rtp:22776
     Play time (voice) : 00h00m30s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 2003 / 2004
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / --
     Number of Excessive Jitter events : 0
     MOS-CQ / MOS-LQ   : 4.34 / 4.39 
     ERL   : 24 dB
     ACOM  : 53 dB


 22 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 130 (369) 
     calling : 32490661150, called : 32479844827
     setup time:  11/01/23 14h12m45s
     connexion time: 11/01/23 14h12m46s
         B channel (from B1..) : B2
     disconnected by local port: 5/0 cause :(16)[Normal call clearing]
     call duration: 00:00:23
     PDD duration: 1109 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16410 /Dest ip :212.224.167.110 rtp:22630
     Play time (voice) : 00h00m23s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 1140 / 1141
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / --
     Number of Excessive Jitter events : 2
     MOS-CQ / MOS-LQ   : 4.34 / 4.39 
     ERL   : 48 dB
     ACOM  : 77 dB


 23 - Call from remote voip: 0  (UDP), to local port: 5/0 call-id: 129 (368) 
     calling : 490661150, called : 55337758
     setup time:  11/01/23 14h12m45s
     connexion time: 11/01/23 14h12m46s
         B channel (from B1..) : B1
     disconnected by remote voip: 0  (UDP) cause :(16)[Normal call clearing]
     call duration: 00:00:22
     PDD duration: 1401 msec
     advice-of-charge: free
     call priority: 100
 

 24 - Call from remote voip: 0  (UDP), to local port: 5/0 call-id: 128 (367) 
     calling : 495504138, called : 55335211
     setup time:  11/01/23 14h07m36s
     connexion time: 11/01/23 14h07m43s
         B channel (from B1..) : B1
     disconnected by local port: 5/0 cause :(16)[Normal call clearing]
     call duration: 00:02:20
     PDD duration: 263 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16408 /Dest ip :212.224.167.110 rtp:22634
     Play time (voice) : 00h02m20s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 7005 / 7003
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / 0
     Number of Excessive Jitter events : 0
     MOS-CQ / MOS-LQ   : 4.33 / 4.39 
     ERL   : 44 dB
     ACOM  : 68 dB


 25 - Call from remote voip: 0  (UDP), to local port: 5/0 call-id: 127 (366) 
     calling : 475453097, called : 55335278
     setup time:  11/01/23 13h31m44s
     connexion time: 11/01/23 13h31m51s
         B channel (from B1..) : B1
     disconnected by remote voip: 0  (UDP) cause :(16)[Normal call clearing]
     call duration: 00:05:38
     PDD duration: 254 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16406 /Dest ip :212.224.167.110 rtp:22452
     Play time (voice) : 00h05m38s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 16865 / 16867
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / 0
     Number of Excessive Jitter events : 0
     MOS-CQ / MOS-LQ   : 4.34 / 4.39 
     ERL   : 46 dB
     ACOM  : 73 dB


 26 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 126 (365) 
     calling : 3255337741, called : 32492819960
     setup time:  11/01/23 13h18m28s
     connexion time: 11/01/23 13h18m38s
         B channel (from B1..) : B1
     disconnected by local port: 5/0 cause :(16)[Normal call clearing]
     call duration: 00:00:33
     PDD duration: 899 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16404 /Dest ip :212.224.167.110 rtp:22392
     Play time (voice) : 00h00m33s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 2118 / 2136
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / 0
     Number of Excessive Jitter events : 1
     MOS-CQ / MOS-LQ   : 4.35 / 4.39 
     ERL   : 20 dB
     ACOM  : 52 dB


 27 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 125 (364) 
     calling : 3255335206, called : 32492819960
     setup time:  11/01/23 13h16m15s
     connexion time: 11/01/23 13h16m27s
         B channel (from B1..) : B1
     disconnected by local port: 5/0 cause :(16)[Normal call clearing]
     call duration: 00:00:14
     PDD duration: 1409 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16402 /Dest ip :212.224.167.110 rtp:22348
     Play time (voice) : 00h00m15s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 1217 / 1234
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / 0
     Number of Excessive Jitter events : 1
     MOS-CQ / MOS-LQ   : 4.35 / 4.39 
     ERL   : 47 dB
     ACOM  : 78 dB


 28 - Call from remote voip: 0  (UDP), to local port: 5/0 call-id: 123 (362) 
     calling : 32039693, called : 55337755
     setup time:  11/01/23 12h36m17s
     connexion time: 11/01/23 12h36m22s
         B channel (from B1..) : B1
     disconnected by local port: 5/0 cause :(16)[Normal call clearing]
     call duration: 00:00:48
     PDD duration: 1241 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16400 /Dest ip :212.224.167.110 rtp:22232
     Play time (voice) : 00h00m48s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 2365 / 2362
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / 0
     Number of Excessive Jitter events : 0
     MOS-CQ / MOS-LQ   : 4.33 / 4.39 
     ERL   : 30 dB
     ACOM  : 54 dB


 29 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 124 (363) 
     calling : 3232039693, called : 32495914860
     setup time:  11/01/23 12h36m17s
     connexion time: 11/01/23 12h36m22s
         B channel (from B1..) : B2
     disconnected by remote voip: 0  (UDP) cause :(16)[Normal call clearing]
     call duration: 00:00:48
     PDD duration: 1020 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16398 /Dest ip :212.224.167.110 rtp:22160
     Play time (voice) : 00h00m48s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 2574 / 2574
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / --
     Number of Excessive Jitter events : 0
     MOS-CQ / MOS-LQ   : 4.34 / 4.39 
     ERL   : 30 dB
     ACOM  : 57 dB


 30 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 122 (361) 
     calling : 3255335206, called : 32492136378
     setup time:  11/01/23 12h11m38s
     connexion time: 11/01/23 12h11m52s
         B channel (from B1..) : B1
     disconnected by local port: 5/0 cause :(16)[Normal call clearing]
     call duration: 00:00:12
     PDD duration: 3277 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16396 /Dest ip :212.224.167.110 rtp:22132
     Play time (voice) : 00h00m12s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 1107 / 1112
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / 0
     Number of Excessive Jitter events : 1
     MOS-CQ / MOS-LQ   : 4.34 / 4.39 
     ERL   : 39 dB
     ACOM  : 62 dB


 31 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 121 (360) 
     calling : 3255335206, called : 32495914834
     setup time:  11/01/23 12h10m24s
     connexion time: 11/01/23 12h10m27s
         B channel (from B1..) : B1
     disconnected by remote voip: 0  (UDP) cause :(16)[Normal call clearing]
     call duration: 00:00:27
     PDD duration: 1219 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16394 /Dest ip :212.224.167.110 rtp:22136
     Play time (voice) : 00h00m27s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 1444 / 1444
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / --
     Number of Excessive Jitter events : 0
     MOS-CQ / MOS-LQ   : 4.34 / 4.39 
     ERL   : 37 dB
     ACOM  : 63 dB


 32 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 120 (359) 
     calling : 3255335206, called : 32490661154
     setup time:  11/01/23 12h09m51s
     connexion time: 11/01/23 12h10m18s
         B channel (from B1..) : B1
     disconnected by local port: 5/0 cause :(16)[Normal call clearing]
     call duration: 00:00:03
     PDD duration: 3375 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16392 /Dest ip :212.224.167.110 rtp:22142
     Play time (voice) : 00h00m03s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 1287 / 1290
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / --
     Number of Excessive Jitter events : 3
     MOS-CQ / MOS-LQ   : 4.34 / 4.39 
     ERL   : 60 dB
     ACOM  : 89 dB


 33 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 119 (358) 
     calling : 3255335241, called : 32491169975
     setup time:  11/01/23 12h02m16s
     connexion time: 11/01/23 12h02m24s
         B channel (from B1..) : B1
     disconnected by remote voip: 0  (UDP) cause :(16)[Normal call clearing]
     call duration: 00:00:19
     PDD duration: 1208 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16390 /Dest ip :212.224.167.110 rtp:22090
     Play time (voice) : 00h00m19s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 1323 / 1323
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / --
     Number of Excessive Jitter events : 0
     MOS-CQ / MOS-LQ   : 4.34 / 4.39 
     ERL   : 21 dB
     ACOM  : 41 dB


 34 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 118 (357) 
     calling : 3255337741, called : 32470635841
     setup time:  11/01/23 11h48m06s
     connexion time: 11/01/23 11h48m16s
         B channel (from B1..) : B1
     disconnected by remote voip: 0  (UDP) cause :(16)[Normal call clearing]
     call duration: 00:01:55
     PDD duration: 1406 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16388 /Dest ip :212.224.167.110 rtp:21946
     Play time (voice) : 00h01m55s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 6164 / 6170
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / 0
     Number of Excessive Jitter events : 1
     MOS-CQ / MOS-LQ   : 4.35 / 4.39 
     ERL   : 25 dB
     ACOM  : 47 dB


 35 - Call from remote voip: 0  (UDP), to local port: 5/0 call-id: 117 (356) 
     calling : 470635841, called : 55335211
     setup time:  11/01/23 11h46m22s
     connexion time: ---
     disconnected by remote voip: 0  (UDP) cause :(16)[Normal call clearing]
     call duration: 00:00:00
     PDD duration: 258 msec
     advice-of-charge: free
     call priority: 100
 

 36 - Call from remote voip: 0  (UDP), to local port: 5/0 call-id: 116 (355) 
     calling : 495914834, called : 55335395
     setup time:  11/01/23 11h41m18s
     connexion time: ---
     disconnected by remote voip: 0  (UDP) cause :(16)[Normal call clearing]
     call duration: 00:00:00
     PDD duration: 343 msec
     advice-of-charge: free
     call priority: 100
 

 37 - Call from remote voip: 0  (UDP), to local port: 5/0 call-id: 115 (354) 
     calling : 495914834, called : 55335395
     setup time:  11/01/23 11h41m15s
     connexion time: ---
     disconnected by remote voip: 0  (UDP) cause :(16)[Normal call clearing]
     call duration: 00:00:00
     PDD duration: -
     advice-of-charge: free
     call priority: 100
 

 38 - Call from remote voip: 0  (UDP), to local port: 5/0 call-id: 114 (353) 
     calling : 495914834, called : 55335395
     setup time:  11/01/23 11h38m56s
     connexion time: ---
     disconnected by remote voip: 0  (UDP) cause :(16)[Normal call clearing]
     call duration: 00:00:00
     PDD duration: 302 msec
     advice-of-charge: free
     call priority: 100
 

 39 - Call from remote voip: 0  (UDP), to local port: 5/0 call-id: 113 (352) 
     calling : 495914834, called : 55335395
     setup time:  11/01/23 11h36m21s
     connexion time: ---
     disconnected by remote voip: 0  (UDP) cause :(16)[Normal call clearing]
     call duration: 00:00:00
     PDD duration: 356 msec
     advice-of-charge: free
     call priority: 100
 

 40 - Call from remote voip: 0  (UDP), to local port: 5/0 call-id: 111 (350) 
     calling : 476215202, called : 55335234
     setup time:  11/01/23 11h30m51s
     connexion time: 11/01/23 11h31m03s
         B channel (from B1..) : B1
     disconnected by local port: 5/0 cause :(16)[Normal call clearing]
     call duration: 00:00:13
     PDD duration: 3942 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16386 /Dest ip :212.224.167.110 rtp:21918
     Play time (voice) : 00h00m13s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 646 / 644
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / 0
     Number of Excessive Jitter events : 0
     MOS-CQ / MOS-LQ   : 4.34 / 4.39 
     ERL   : 24 dB
     ACOM  : 52 dB


 41 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 112 (351) 
     calling : 32476215202, called : 32490661131
     setup time:  11/01/23 11h30m51s
     connexion time: 11/01/23 11h31m03s
         B channel (from B1..) : B2
     disconnected by remote voip: 0  (UDP) cause :(16)[Normal call clearing]
     call duration: 00:00:13
     PDD duration: 3646 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16384 /Dest ip :212.224.167.110 rtp:21936
     Play time (voice) : 00h00m13s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 1060 / 1065
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / 0
     Number of Excessive Jitter events : 1
     MOS-CQ / MOS-LQ   : 4.34 / 4.39 
     ERL   : 41 dB
     ACOM  : 65 dB


 42 - Call from remote voip: 0  (UDP), to local port: 5/0 call-id: 110 (349) 
     calling : 490661150, called : 55335241
     setup time:  11/01/23 11h23m17s
     connexion time: 11/01/23 11h23m44s
         B channel (from B1..) : B1
     disconnected by remote voip: 0  (UDP) cause :(16)[Normal call clearing]
     call duration: 00:00:02
     PDD duration: 301 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16454 /Dest ip :212.224.167.110 rtp:21848
     Play time (voice) : 00h00m02s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 76 / 62
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / --
     Number of Excessive Jitter events : 0
     MOS-CQ / MOS-LQ   : -- / -- 
     ERL   : 27 dB
     ACOM  : 82 dB


 43 - Call from remote voip: 0  (UDP), to local port: 5/0 call-id: 109 (348) 
     calling : 55218750, called : 55335241
     setup time:  11/01/23 11h21m13s
     connexion time: ---
     disconnected by remote voip: 0  (UDP) cause :(16)[Normal call clearing]
     call duration: 00:00:00
     PDD duration: 355 msec
     advice-of-charge: free
     call priority: 100
 

 44 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 108 (347) 
     calling : 3255335334, called : 32475638295
     setup time:  11/01/23 11h17m51s
     connexion time: 11/01/23 11h17m57s
         B channel (from B1..) : B1
     disconnected by remote voip: 0  (UDP) cause :(16)[Normal call clearing]
     call duration: 00:01:24
     PDD duration: 814 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16452 /Dest ip :212.224.167.110 rtp:21814
     Play time (voice) : 00h01m24s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 4463 / 4464
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / --
     Number of Excessive Jitter events : 0
     MOS-CQ / MOS-LQ   : 4.34 / 4.39 
     ERL   : 20 dB
     ACOM  : 53 dB


 45 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 107 (346) 
     calling : 3255335206, called : 32492819960
     setup time:  11/01/23 11h16m33s
     connexion time: 11/01/23 11h16m46s
         B channel (from B1..) : B1
     disconnected by local port: 5/0 cause :(16)[Normal call clearing]
     call duration: 00:00:11
     PDD duration: 900 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16450 /Dest ip :212.224.167.110 rtp:21764
     Play time (voice) : 00h00m11s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 1159 / 1177
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / --
     Number of Excessive Jitter events : 1
     MOS-CQ / MOS-LQ   : 4.34 / 4.39 
     ERL   : 40 dB
     ACOM  : 64 dB


 46 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 106 (345) 
     calling : 3255335278, called : 32492819960
     setup time:  11/01/23 11h13m41s
     connexion time: 11/01/23 11h13m51s
         B channel (from B1..) : B1
     disconnected by local port: 5/0 cause :(16)[Normal call clearing]
     call duration: 00:01:58
     PDD duration: 1332 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16448 /Dest ip :212.224.167.110 rtp:21776
     Play time (voice) : 00h01m58s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 6322 / 6335
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / 0
     Number of Excessive Jitter events : 1
     MOS-CQ / MOS-LQ   : 4.35 / 4.39 
     ERL   : 24 dB
     ACOM  : 57 dB


 47 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 104 (343) 
     calling : 3255335241, called : 32491169975
     setup time:  11/01/23 11h09m16s
     connexion time: 11/01/23 11h09m21s
         B channel (from B1..) : B1
     disconnected by remote voip: 0  (UDP) cause :(16)[Normal call clearing]
     call duration: 00:03:01
     PDD duration: 1464 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16444 /Dest ip :212.224.167.110 rtp:21738
     Play time (voice) : 00h03m01s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 9207 / 9207
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / --
     Number of Excessive Jitter events : 0
     MOS-CQ / MOS-LQ   : 4.34 / 4.39 
     ERL   : 25 dB
     ACOM  : 62 dB


 48 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 105 (344) 
     calling : 3255335278, called : 32474810035
     setup time:  11/01/23 11h10m19s
     connexion time: 11/01/23 11h10m26s
         B channel (from B1..) : B2
     disconnected by local port: 5/0 cause :(16)[Normal call clearing]
     call duration: 00:01:38
     PDD duration: 1209 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16446 /Dest ip :212.224.167.110 rtp:21724
     Play time (voice) : 00h01m38s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 5201 / 5202
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / --
     Number of Excessive Jitter events : 0
     MOS-CQ / MOS-LQ   : 4.34 / 4.39 
     ERL   : 31 dB
     ACOM  : 61 dB


 49 - Call from remote voip: 0  (UDP), to local port: 5/0 call-id: 103 (342) 
     calling : 55218750, called : 55335241
     setup time:  11/01/23 11h05m39s
     connexion time: 11/01/23 11h06m06s
         B channel (from B1..) : B1
     disconnected by remote voip: 0  (UDP) cause :(16)[Normal call clearing]
     call duration: 00:00:03
     PDD duration: 350 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16442 /Dest ip :212.224.167.110 rtp:21744
     Play time (voice) : 00h00m03s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 102 / 106
     RTP Packet lost&discarded RX / TX (RTCP reported) : 1 / --
     Number of Excessive Jitter events : 0
     MOS-CQ / MOS-LQ   : -- / -- 
     ERL   : 28 dB
     ACOM  : 83 dB


 50 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 102 (341) 
     calling : 3255335278, called : 32479790455
     setup time:  11/01/23 11h04m18s
     connexion time: 11/01/23 11h04m30s
         B channel (from B1..) : B1
     disconnected by local port: 5/0 cause :(16)[Normal call clearing]
     call duration: 00:00:04
     PDD duration: 1099 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16440 /Dest ip :212.224.167.110 rtp:21706
     Play time (voice) : 00h00m04s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 732 / 761
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / 0
     Number of Excessive Jitter events : 1
     MOS-CQ / MOS-LQ   : 4.34 / 4.39 
     ERL   : 25 dB
     ACOM  : 53 dB


 51 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 101 (340) 
     calling : 3255335241, called : 3255218750
     setup time:  11/01/23 11h03m15s
     connexion time: 11/01/23 11h03m15s
         B channel (from B1..) : B1
     disconnected by remote voip: 0  (UDP) cause :(16)[Normal call clearing]
     call duration: 00:00:43
     PDD duration: 554 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16438 /Dest ip :212.224.167.110 rtp:21686
     Play time (voice) : 00h00m43s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 2131 / 2148
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / 0
     Number of Excessive Jitter events : 2
     MOS-CQ / MOS-LQ   : 4.33 / 4.39 
     ERL   : 48 dB
     ACOM  : 71 dB


 52 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 100 (339) 
     calling : 3255335241, called : 32495914834
     setup time:  11/01/23 11h01m29s
     connexion time: 11/01/23 11h01m33s
         B channel (from B1..) : B1
     disconnected by remote voip: 0  (UDP) cause :(16)[Normal call clearing]
     call duration: 00:01:24
     PDD duration: 1491 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16436 /Dest ip :212.224.167.110 rtp:21718
     Play time (voice) : 00h01m24s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 4315 / 4315
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / --
     Number of Excessive Jitter events : 0
     MOS-CQ / MOS-LQ   : 4.34 / 4.39 
     ERL   : 32 dB
     ACOM  : 64 dB


 53 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 98 (337) 
     calling : 3255335241, called : 32486141517
     setup time:  11/01/23 10h59m16s
     connexion time: 11/01/23 10h59m30s
         B channel (from B1..) : B1
     disconnected by remote voip: 0  (UDP) cause :(16)[Normal call clearing]
     call duration: 00:01:53
     PDD duration: 1433 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16432 /Dest ip :212.224.167.110 rtp:21672
     Play time (voice) : 00h01m53s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 6280 / 6281
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / --
     Number of Excessive Jitter events : 0
     MOS-CQ / MOS-LQ   : 4.34 / 4.39 
     ERL   : 43 dB
     ACOM  : 77 dB


 54 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 99 (338) 
     calling : 3255335275, called : 32495914834
     setup time:  11/01/23 11h00m11s
     connexion time: 11/01/23 11h00m15s
         B channel (from B1..) : B2
     disconnected by remote voip: 0  (UDP) cause :(16)[Normal call clearing]
     call duration: 00:00:22
     PDD duration: 998 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16434 /Dest ip :212.224.167.110 rtp:21662
     Play time (voice) : 00h00m22s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 1256 / 1256
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / --
     Number of Excessive Jitter events : 0
     MOS-CQ / MOS-LQ   : 4.34 / 4.39 
     ERL   : 14 dB
     ACOM  : 53 dB


 55 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 97 (336) 
     calling : 3255335241, called : 3255235858
     setup time:  11/01/23 10h58m23s
     connexion time: 11/01/23 10h58m25s
         B channel (from B1..) : B1
     disconnected by local port: 5/0 cause :(16)[Normal call clearing]
     call duration: 00:00:41
     PDD duration: 1643 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16430 /Dest ip :212.224.167.110 rtp:21684
     Play time (voice) : 00h00m41s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 2053 / 2080
     RTP Packet lost&discarded RX / TX (RTCP reported) : 7 / 0
     Number of Excessive Jitter events : 1
     MOS-CQ / MOS-LQ   : 4.32 / 4.38 
     ERL   : 45 dB
     ACOM  : 76 dB


 56 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 96 (335) 
     calling : 3255335241, called : 32495914834
     setup time:  11/01/23 10h57m17s
     connexion time: 11/01/23 10h57m21s
         B channel (from B1..) : B1
     disconnected by remote voip: 0  (UDP) cause :(16)[Normal call clearing]
     call duration: 00:00:40
     PDD duration: 1310 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16428 /Dest ip :212.224.167.110 rtp:21618
     Play time (voice) : 00h00m40s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 2136 / 2136
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / --
     Number of Excessive Jitter events : 0
     MOS-CQ / MOS-LQ   : 4.34 / 4.39 
     ERL   : 54 dB
     ACOM  : 88 dB


 57 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 95 (334) 
     calling : 3255335241, called : 3256303372
     setup time:  11/01/23 10h54m14s
     connexion time: 11/01/23 10h54m16s
         B channel (from B1..) : B1
     disconnected by remote voip: 0  (UDP) cause :(16)[Normal call clearing]
     call duration: 00:02:57
     PDD duration: 1601 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16426 /Dest ip :212.224.167.110 rtp:21642
     Play time (voice) : 00h02m57s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 8815 / 8872
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / 0
     Number of Excessive Jitter events : 1
     MOS-CQ / MOS-LQ   : 4.34 / 4.39 
     ERL   : 14 dB
     ACOM  : 40 dB


 58 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 93 (332) 
     calling : 3255335334, called : 32475638295
     setup time:  11/01/23 10h52m58s
     connexion time: 11/01/23 10h53m22s
         B channel (from B1..) : B2
     disconnected by remote voip: 0  (UDP) cause :(16)[Normal call clearing]
     call duration: 00:03:03
     PDD duration: 1153 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16422 /Dest ip :212.224.167.110 rtp:21632
     Play time (voice) : 00h03m03s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 10275 / 10276
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / --
     Number of Excessive Jitter events : 0
     MOS-CQ / MOS-LQ   : 4.35 / 4.39 
     ERL   : 29 dB
     ACOM  : 54 dB


 59 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 94 (333) 
     calling : 3255337755, called : 32474718109
     setup time:  11/01/23 10h53m32s
     connexion time: 11/01/23 10h53m36s
         B channel (from B1..) : B3
     disconnected by local port: 5/0 cause :(16)[Normal call clearing]
     call duration: 00:01:06
     PDD duration: 1327 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16424 /Dest ip :212.224.167.110 rtp:21612
     Play time (voice) : 00h01m06s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 3428 / 3428
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / --
     Number of Excessive Jitter events : 0
     MOS-CQ / MOS-LQ   : 4.34 / 4.39 
     ERL   : 33 dB
     ACOM  : 59 dB


 60 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 92 (331) 
     calling : 3255335241, called : 3256627111
     setup time:  11/01/23 10h52m03s
     connexion time: 11/01/23 10h52m05s
         B channel (from B1..) : B1
     disconnected by remote voip: 0  (UDP) cause :(16)[Normal call clearing]
     call duration: 00:01:57
     PDD duration: 649 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16420 /Dest ip :212.224.167.110 rtp:21634
     Play time (voice) : 00h01m57s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 5846 / 5893
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / 0
     Number of Excessive Jitter events : 1
     MOS-CQ / MOS-LQ   : 2.87 / 4.39 
     ERL   : 49 dB
     ACOM  : 76 dB


 61 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 91 (330) 
     calling : 3255335241, called : 3255218750
     setup time:  11/01/23 10h47m31s
     connexion time: 11/01/23 10h47m31s
         B channel (from B1..) : B2
     disconnected by remote voip: 0  (UDP) cause :(16)[Normal call clearing]
     call duration: 00:04:05
     PDD duration: 566 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16418 /Dest ip :212.224.167.110 rtp:21590
     Play time (voice) : 00h04m05s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 12176 / 12215
     RTP Packet lost&discarded RX / TX (RTCP reported) : 10786 / 0
     Number of Excessive Jitter events : 1
     MOS-CQ / MOS-LQ   : 1.00 / 1.00 
     ERL   : 37 dB
     ACOM  : 65 dB


 62 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 90 (329) 
     calling : 3255335346, called : 32490661135
     setup time:  11/01/23 10h47m26s
     connexion time: 11/01/23 10h47m36s
         B channel (from B1..) : B1
     disconnected by remote voip: 0  (UDP) cause :(16)[Normal call clearing]
     call duration: 00:00:37
     PDD duration: 1731 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16416 /Dest ip :212.224.167.110 rtp:21586
     Play time (voice) : 00h00m37s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 2283 / 2283
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / --
     Number of Excessive Jitter events : 0
     MOS-CQ / MOS-LQ   : 4.34 / 4.39 
     ERL   : 31 dB
     ACOM  : 55 dB


 63 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 89 (328) 
     calling : 3255335346, called : 32490661135
     setup time:  11/01/23 10h44m55s
     connexion time: 11/01/23 10h44m58s
         B channel (from B1..) : B1
     disconnected by local port: 5/0 cause :(16)[Normal call clearing]
     call duration: 00:00:03
     PDD duration: 2197 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16414 /Dest ip :212.224.167.110 rtp:21574
     Play time (voice) : 00h00m03s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 166 / 168
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / --
     Number of Excessive Jitter events : 0
     MOS-CQ / MOS-LQ   : -- / -- 
     ERL   : -- dB
     ACOM  : 255 dB


 64 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 88 (327) 
     calling : 3255337741, called : 31228355612
     setup time:  11/01/23 10h39m59s
     connexion time: 11/01/23 10h40m06s
         B channel (from B1..) : B3
     disconnected by remote voip: 0  (UDP) cause :(16)[Normal call clearing]
     call duration: 00:01:09
     PDD duration: 1017 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16412 /Dest ip :212.224.167.110 rtp:21570
     Play time (voice) : 00h01m09s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 3717 / 3723
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / 0
     Number of Excessive Jitter events : 0
     MOS-CQ / MOS-LQ   : 4.29 / 4.39 
     ERL   : 35 dB
     ACOM  : 61 dB


 65 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 87 (326) 
     calling : 32491169975, called : 32490661134
     setup time:  11/01/23 10h37m30s
     connexion time: 11/01/23 10h37m41s
         B channel (from B1..) : B2
     disconnected by local port: 5/0 cause :(16)[Normal call clearing]
     call duration: 00:03:14
     PDD duration: 2045 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16408 /Dest ip :212.224.167.110 rtp:21544
     Play time (voice) : 00h03m14s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 10140 / 10141
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / --
     Number of Excessive Jitter events : 0
     MOS-CQ / MOS-LQ   : 4.34 / 4.39 
     ERL   : 18 dB
     ACOM  : 44 dB


 66 - Call from remote voip: 0  (UDP), to local port: 5/0 call-id: 86 (325) 
     calling : 491169975, called : 55335341
     setup time:  11/01/23 10h37m30s
     connexion time: 11/01/23 10h37m41s
         B channel (from B1..) : B1
     disconnected by remote voip: 0  (UDP) cause :(16)[Normal call clearing]
     call duration: 00:03:14
     PDD duration: 2247 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16410 /Dest ip :212.224.167.110 rtp:21532
     Play time (voice) : 00h03m14s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 9688 / 9681
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / --
     Number of Excessive Jitter events : 0
     MOS-CQ / MOS-LQ   : 4.34 / 4.39 
     ERL   : 20 dB
     ACOM  : 48 dB


 67 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 84 (323) 
     calling : 3255218750, called : 32495914836
     setup time:  11/01/23 10h32m20s
     connexion time: 11/01/23 10h32m35s
         B channel (from B1..) : B2
     disconnected by local port: 5/0 cause :(16)[Normal call clearing]
     call duration: 00:00:18
     PDD duration: 1840 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16402 /Dest ip :212.224.167.110 rtp:21520
     Play time (voice) : 00h00m18s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 1560 / 1561
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / --
     Number of Excessive Jitter events : 0
     MOS-CQ / MOS-LQ   : 4.34 / 4.39 
     ERL   : 51 dB
     ACOM  : 75 dB


 68 - Call from remote voip: 0  (UDP), to local port: 5/0 call-id: 83 (322) 
     calling : 55218750, called : 55335241
     setup time:  11/01/23 10h32m20s
     connexion time: 11/01/23 10h32m35s
         B channel (from B1..) : B1
     disconnected by remote voip: 0  (UDP) cause :(16)[Normal call clearing]
     call duration: 00:00:18
     PDD duration: 2104 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16406 /Dest ip :212.224.167.110 rtp:21528
     Play time (voice) : 00h00m18s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 884 / 896
     RTP Packet lost&discarded RX / TX (RTCP reported) : 1 / 0
     Number of Excessive Jitter events : 1
     MOS-CQ / MOS-LQ   : 4.34 / 4.39 
     ERL   : 42 dB
     ACOM  : 73 dB


 69 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 85 (324) 
     calling : 3255335206, called : 32492819960
     setup time:  11/01/23 10h32m23s
     connexion time: 11/01/23 10h32m31s
         B channel (from B1..) : B3
     disconnected by remote voip: 0  (UDP) cause :(16)[Normal call clearing]
     call duration: 00:00:10
     PDD duration: 931 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16404 /Dest ip :212.224.167.110 rtp:21542
     Play time (voice) : 00h00m10s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 817 / 835
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / 0
     Number of Excessive Jitter events : 1
     MOS-CQ / MOS-LQ   : 4.35 / 4.39 
     ERL   : 36 dB
     ACOM  : 64 dB


 70 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 82 (321) 
     calling : 3255335334, called : 32490661126
     setup time:  11/01/23 10h31m03s
     connexion time: 11/01/23 10h31m16s
         B channel (from B1..) : B1
     disconnected by remote voip: 0  (UDP) cause :(16)[Normal call clearing]
     call duration: 00:00:07
     PDD duration: 3170 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16400 /Dest ip :212.224.167.110 rtp:21498
     Play time (voice) : 00h00m07s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 811 / 847
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / 0
     Number of Excessive Jitter events : 1
     MOS-CQ / MOS-LQ   : 4.34 / 4.39 
     ERL   : 34 dB
     ACOM  : 59 dB


 71 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 81 (320) 
     calling : 3255335346, called : 32495914836
     setup time:  11/01/23 10h23m33s
     connexion time: 11/01/23 10h23m46s
         B channel (from B1..) : B3
     disconnected by remote voip: 0  (UDP) cause :(16)[Normal call clearing]
     call duration: 00:02:14
     PDD duration: 678 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16398 /Dest ip :212.224.167.110 rtp:21460
     Play time (voice) : 00h02m14s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 7352 / 7352
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / --
     Number of Excessive Jitter events : 0
     MOS-CQ / MOS-LQ   : 4.34 / 4.39 
     ERL   : 29 dB
     ACOM  : 62 dB


 72 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 80 (319) 
     calling : 32460973920, called : 32495914836
     setup time:  11/01/23 10h23m24s
     connexion time: 11/01/23 10h23m31s
         B channel (from B1..) : B2
     disconnected by local port: 5/0 cause :(16)[Normal call clearing]
     call duration: 00:00:13
     PDD duration: 1492 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16394 /Dest ip :212.224.167.110 rtp:21454
     Play time (voice) : 00h00m13s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 936 / 937
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / --
     Number of Excessive Jitter events : 0
     MOS-CQ / MOS-LQ   : 4.34 / 4.39 
     ERL   : 29 dB
     ACOM  : 54 dB


 73 - Call from remote voip: 0  (UDP), to local port: 5/0 call-id: 79 (318) 
     calling : 460973920, called : 55335241
     setup time:  11/01/23 10h23m24s
     connexion time: 11/01/23 10h23m31s
         B channel (from B1..) : B1
     disconnected by remote voip: 0  (UDP) cause :(16)[Normal call clearing]
     call duration: 00:00:13
     PDD duration: 1727 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16396 /Dest ip :212.224.167.110 rtp:21452
     Play time (voice) : 00h00m13s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 652 / 657
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / 0
     Number of Excessive Jitter events : 0
     MOS-CQ / MOS-LQ   : 4.34 / 4.39 
     ERL   : 28 dB
     ACOM  : 55 dB


 74 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 78 (317) 
     calling : 3255335346, called : 32490661124
     setup time:  11/01/23 10h19m03s
     connexion time: 11/01/23 10h19m19s
         B channel (from B1..) : B1
     disconnected by local port: 5/0 cause :(16)[Normal call clearing]
     call duration: 00:01:22
     PDD duration: 3237 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16392 /Dest ip :212.224.167.110 rtp:21438
     Play time (voice) : 00h01m22s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 4726 / 4729
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / 0
     Number of Excessive Jitter events : 1
     MOS-CQ / MOS-LQ   : 4.35 / 4.39 
     ERL   : 31 dB
     ACOM  : 56 dB


 75 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 77 (316) 
     calling : 3255335346, called : 32474718109
     setup time:  11/01/23 10h18m16s
     connexion time: 11/01/23 10h18m20s
         B channel (from B1..) : B1
     disconnected by local port: 5/0 cause :(16)[Normal call clearing]
     call duration: 00:00:39
     PDD duration: 919 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16390 /Dest ip :212.224.167.110 rtp:21450
     Play time (voice) : 00h00m39s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 2137 / 2137
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / --
     Number of Excessive Jitter events : 0
     MOS-CQ / MOS-LQ   : 4.34 / 4.39 
     ERL   : 27 dB
     ACOM  : 51 dB


 76 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 76 (315) 
     calling : 3255335346, called : 32490661135
     setup time:  11/01/23 10h16m51s
     connexion time: 11/01/23 10h17m05s
         B channel (from B1..) : B1
     disconnected by remote voip: 0  (UDP) cause :(16)[Normal call clearing]
     call duration: 00:00:11
     PDD duration: 2327 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16388 /Dest ip :212.224.167.110 rtp:21430
     Play time (voice) : 00h00m11s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 1166 / 1166
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / --
     Number of Excessive Jitter events : 0
     MOS-CQ / MOS-LQ   : 4.34 / 4.39 
     ERL   : 28 dB
     ACOM  : 53 dB


 77 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 75 (314) 
     calling : 3255335206, called : 32492819960
     setup time:  11/01/23 10h07m53s
     connexion time: 11/01/23 10h08m17s
         B channel (from B1..) : B1
     disconnected by local port: 5/0 cause :(16)[Normal call clearing]
     call duration: 00:00:02
     PDD duration: 1453 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16386 /Dest ip :212.224.167.110 rtp:21352
     Play time (voice) : 00h00m02s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 1224 / 1239
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / 0
     Number of Excessive Jitter events : 3
     MOS-CQ / MOS-LQ   : 4.34 / 4.39 
     ERL   : 66 dB
     ACOM  : 90 dB


 78 - Call from remote voip: 0  (UDP), to local port: 5/0 call-id: 73 (312) 
     calling : 491169975, called : 55335354
     setup time:  11/01/23 10h05m41s
     connexion time: 11/01/23 10h05m55s
         B channel (from B1..) : B1
     disconnected by local port: 5/0 cause :(16)[Normal call clearing]
     call duration: 00:00:35
     PDD duration: 2467 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16384 /Dest ip :212.224.167.110 rtp:21354
     Play time (voice) : 00h00m35s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 1746 / 1738
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / --
     Number of Excessive Jitter events : 0
     MOS-CQ / MOS-LQ   : 4.34 / 4.39 
     ERL   : 17 dB
     ACOM  : 44 dB


 79 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 74 (313) 
     calling : 32491169975, called : 32490661135
     setup time:  11/01/23 10h05m41s
     connexion time: 11/01/23 10h05m54s
         B channel (from B1..) : B2
     disconnected by remote voip: 0  (UDP) cause :(16)[Normal call clearing]
     call duration: 00:00:35
     PDD duration: 2259 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16454 /Dest ip :212.224.167.110 rtp:21356
     Play time (voice) : 00h00m35s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 2294 / 2295
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / --
     Number of Excessive Jitter events : 0
     MOS-CQ / MOS-LQ   : 4.34 / 4.39 
     ERL   : 17 dB
     ACOM  : 60 dB


 80 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 72 (311) 
     calling : 3255335346, called : 32495914834
     setup time:  11/01/23 09h58m30s
     connexion time: 11/01/23 09h58m53s
         B channel (from B1..) : B1
     disconnected by local port: 5/0 cause :(16)[Normal call clearing]
     call duration: 00:00:04
     PDD duration: 961 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16452 /Dest ip :212.224.167.110 rtp:21314
     Play time (voice) : 00h00m04s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 1305 / 1307
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / 0
     Number of Excessive Jitter events : 3
     MOS-CQ / MOS-LQ   : 4.34 / 4.39 
     ERL   : 60 dB
     ACOM  : 90 dB


 81 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 71 (310) 
     calling : 3255335346, called : 32495914834
     setup time:  11/01/23 09h57m58s
     connexion time: 11/01/23 09h58m22s
         B channel (from B1..) : B1
     disconnected by local port: 5/0 cause :(16)[Normal call clearing]
     call duration: 00:00:03
     PDD duration: 1369 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16450 /Dest ip :212.224.167.110 rtp:21324
     Play time (voice) : 00h00m03s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 1261 / 1263
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / 0
     Number of Excessive Jitter events : 3
     MOS-CQ / MOS-LQ   : 4.34 / 4.39 
     ERL   : 60 dB
     ACOM  : 90 dB


 82 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 70 (309) 
     calling : 3255337741, called : 3256232940
     setup time:  11/01/23 09h49m37s
     connexion time: 11/01/23 09h49m38s
         B channel (from B1..) : B2
     disconnected by local port: 5/0 cause :(16)[Normal call clearing]
     call duration: 00:01:02
     PDD duration: 1118 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16448 /Dest ip :212.224.167.110 rtp:21266
     Play time (voice) : 00h01m02s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 622 / 3093
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / 3998976
     Number of Excessive Jitter events : 0
     MOS-CQ / MOS-LQ   : 4.34 / 4.39 
     ERL   : 33 dB
     ACOM  : 58 dB


 83 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 69 (308) 
     calling : 3255337741, called : 3256232940
     setup time:  11/01/23 09h49m34s
     connexion time: 11/01/23 09h49m36s
         B channel (from B1..) : B1
     disconnected by local port: 5/0 cause :(16)[Normal call clearing]
     call duration: 00:01:04
     PDD duration: 1325 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16446 /Dest ip :212.224.167.110 rtp:21262
     Play time (voice) : 00h01m04s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 628 / 3220
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / 2684106
     Number of Excessive Jitter events : 0
     MOS-CQ / MOS-LQ   : 4.35 / 4.39 
     ERL   : -- dB
     ACOM  : 255 dB


 84 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 68 (307) 
     calling : 3255337741, called : 3256232940
     setup time:  11/01/23 09h48m47s
     connexion time: 11/01/23 09h48m48s
         B channel (from B1..) : B1
     disconnected by local port: 5/0 cause :(16)[Normal call clearing]
     call duration: 00:00:34
     PDD duration: 1098 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16444 /Dest ip :212.224.167.110 rtp:21252
     Play time (voice) : 00h00m34s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 619 / 1707
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / 1121577
     Number of Excessive Jitter events : 0
     MOS-CQ / MOS-LQ   : 4.34 / 4.39 
     ERL   : 34 dB
     ACOM  : 61 dB


 85 - Call from remote voip: 0  (UDP), to local port: 5/0 call-id: 67 (306) 
     calling : 495914834, called : 55335241
     setup time:  11/01/23 09h48m07s
     connexion time: 11/01/23 09h48m23s
         B channel (from B1..) : B1
     disconnected by remote voip: 0  (UDP) cause :(16)[Normal call clearing]
     call duration: 00:00:17
     PDD duration: 308 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16442 /Dest ip :212.224.167.110 rtp:21268
     Play time (voice) : 00h00m17s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 824 / 813
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / --
     Number of Excessive Jitter events : 0
     MOS-CQ / MOS-LQ   : 4.34 / 4.39 
     ERL   : 23 dB
     ACOM  : 72 dB


 86 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 66 (305) 
     calling : 3255335241, called : 32495914834
     setup time:  11/01/23 09h41m58s
     connexion time: 11/01/23 09h42m00s
         B channel (from B1..) : B1
     disconnected by local port: 5/0 cause :(16)[Normal call clearing]
     call duration: 00:00:13
     PDD duration: 1335 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16440 /Dest ip :212.224.167.110 rtp:21216
     Play time (voice) : 00h00m13s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 678 / 680
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / --
     Number of Excessive Jitter events : 0
     MOS-CQ / MOS-LQ   : 4.34 / 4.39 
     ERL   : -- dB
     ACOM  : 255 dB


 87 - Call from remote voip: 0  (UDP), to local port: 5/0 call-id: 65 (304) 
     calling : 31113760035, called : 55335278
     setup time:  11/01/23 09h36m21s
     connexion time: ---
     disconnected by remote voip: 0  (UDP) cause :(16)[Normal call clearing]
     call duration: 00:00:00
     PDD duration: 263 msec
     advice-of-charge: free
     call priority: 100
 

 88 - Call from remote voip: 0  (UDP), to local port: 5/0 call-id: 64 (303) 
     calling : 460973920, called : 55335241
     setup time:  11/01/23 09h21m11s
     connexion time: 11/01/23 09h21m14s
         B channel (from B1..) : B1
     disconnected by remote voip: 0  (UDP) cause :(16)[Normal call clearing]
     call duration: 00:01:46
     PDD duration: 311 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16438 /Dest ip :212.224.167.110 rtp:21108
     Play time (voice) : 00h01m46s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 5330 / 5332
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / 0
     Number of Excessive Jitter events : 0
     MOS-CQ / MOS-LQ   : 4.34 / 4.39 
     ERL   : 19 dB
     ACOM  : 44 dB


 89 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 63 (302) 
     calling : 3255337741, called : 32492819960
     setup time:  11/01/23 09h02m42s
     connexion time: 11/01/23 09h02m51s
         B channel (from B1..) : B1
     disconnected by local port: 5/0 cause :(16)[Normal call clearing]
     call duration: 00:00:19
     PDD duration: 1052 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16436 /Dest ip :212.224.167.110 rtp:20998
     Play time (voice) : 00h00m19s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 1336 / 1356
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / 0
     Number of Excessive Jitter events : 0
     MOS-CQ / MOS-LQ   : 4.34 / 4.39 
     ERL   : 35 dB
     ACOM  : 57 dB


 90 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 62 (301) 
     calling : 3255337741, called : 3292349010
     setup time:  11/01/23 08h55m10s
     connexion time: 11/01/23 08h55m13s
         B channel (from B1..) : B1
     disconnected by local port: 5/0 cause :(16)[Normal call clearing]
     call duration: 00:07:20
     PDD duration: 1490 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16434 /Dest ip :212.224.167.110 rtp:20990
     Play time (voice) : 00h07m20s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 17752 / 22075
     RTP Packet lost&discarded RX / TX (RTCP reported) : 1 / 0
     Number of Excessive Jitter events : 1
     MOS-CQ / MOS-LQ   : 4.33 / 4.39 
     ERL   : 32 dB
     ACOM  : 58 dB


 91 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 61 (300) 
     calling : 3255337741, called : 32492819960
     setup time:  11/01/23 08h51m58s
     connexion time: 11/01/23 08h52m22s
         B channel (from B1..) : B1
     disconnected by local port: 5/0 cause :(16)[Normal call clearing]
     call duration: 00:00:04
     PDD duration: 1153 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16432 /Dest ip :212.224.167.110 rtp:20970
     Play time (voice) : 00h00m04s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 1298 / 1315
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / 0
     Number of Excessive Jitter events : 3
     MOS-CQ / MOS-LQ   : 4.34 / 4.39 
     ERL   : 24 dB
     ACOM  : 73 dB


 92 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 60 (299) 
     calling : 3255337741, called : 32492819960
     setup time:  11/01/23 08h44m49s
     connexion time: 11/01/23 08h45m13s
         B channel (from B1..) : B1
     disconnected by local port: 5/0 cause :(16)[Normal call clearing]
     call duration: 00:00:02
     PDD duration: 1285 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16430 /Dest ip :212.224.167.110 rtp:20888
     Play time (voice) : 00h00m02s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 1243 / 1262
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / --
     Number of Excessive Jitter events : 3
     MOS-CQ / MOS-LQ   : 4.34 / 4.39 
     ERL   : 56 dB
     ACOM  : 75 dB


 93 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 59 (298) 
     calling : 3255335206, called : 32492819960
     setup time:  11/01/23 08h42m47s
     connexion time: 11/01/23 08h42m59s
         B channel (from B1..) : B1
     disconnected by local port: 5/0 cause :(16)[Normal call clearing]
     call duration: 00:00:09
     PDD duration: 1183 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16428 /Dest ip :212.224.167.110 rtp:20902
     Play time (voice) : 00h00m09s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 994 / 1009
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / 0
     Number of Excessive Jitter events : 1
     MOS-CQ / MOS-LQ   : 4.34 / 4.39 
     ERL   : 33 dB
     ACOM  : 58 dB


 94 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 58 (297) 
     calling : 3255335286, called : 32490661144
     setup time:  11/01/23 08h27m13s
     connexion time: 11/01/23 08h27m26s
         B channel (from B1..) : B2
     disconnected by remote voip: 0  (UDP) cause :(16)[Normal call clearing]
     call duration: 00:00:21
     PDD duration: 2148 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16426 /Dest ip :212.224.167.110 rtp:20874
     Play time (voice) : 00h00m21s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 1600 / 1600
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / --
     Number of Excessive Jitter events : 0
     MOS-CQ / MOS-LQ   : 4.34 / 4.39 
     ERL   : -- dB
     ACOM  : 255 dB


 95 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 57 (296) 
     calling : 3255337758, called : 32490661150
     setup time:  11/01/23 08h26m27s
     connexion time: 11/01/23 08h26m36s
         B channel (from B1..) : B1
     disconnected by local port: 5/0 cause :(16)[Normal call clearing]
     call duration: 00:01:06
     PDD duration: 3073 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16424 /Dest ip :212.224.167.110 rtp:20882
     Play time (voice) : 00h01m06s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 3578 / 3611
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / 0
     Number of Excessive Jitter events : 0
     MOS-CQ / MOS-LQ   : 4.24 / 4.39 
     ERL   : 25 dB
     ACOM  : 50 dB


 96 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 56 (295) 
     calling : 3255335241, called : 32490446941
     setup time:  11/01/23 08h12m33s
     connexion time: 11/01/23 08h12m42s
         B channel (from B1..) : B1
     disconnected by local port: 5/0 cause :(16)[Normal call clearing]
     call duration: 00:03:31
     PDD duration: 1404 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16422 /Dest ip :212.224.167.110 rtp:20840
     Play time (voice) : 00h03m32s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 10973 / 10974
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / --
     Number of Excessive Jitter events : 0
     MOS-CQ / MOS-LQ   : 4.34 / 4.39 
     ERL   : 12 dB
     ACOM  : 45 dB


 97 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 55 (294) 
     calling : 32491169927, called : 32490446941
     setup time:  11/01/23 07h58m45s
     connexion time: 11/01/23 07h59m09s
         B channel (from B1..) : B2
     disconnected by local port: 5/0 cause :(16)[Normal call clearing]
     call duration: 00:00:05
     PDD duration: 1072 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16418 /Dest ip :212.224.167.110 rtp:20780
     Play time (voice) : 00h00m05s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 1377 / 1378
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / 0
     Number of Excessive Jitter events : 3
     MOS-CQ / MOS-LQ   : 4.34 / 4.39 
     ERL   : 49 dB
     ACOM  : 78 dB


 98 - Call from remote voip: 0  (UDP), to local port: 5/0 call-id: 54 (293) 
     calling : 491169927, called : 55335361
     setup time:  11/01/23 07h58m45s
     connexion time: 11/01/23 07h59m09s
         B channel (from B1..) : B1
     disconnected by remote voip: 0  (UDP) cause :(16)[Normal call clearing]
     call duration: 00:00:05
     PDD duration: 1343 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16420 /Dest ip :212.224.167.110 rtp:20778
     Play time (voice) : 00h00m05s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 227 / 216
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / --
     Number of Excessive Jitter events : 0
     MOS-CQ / MOS-LQ   : -- / -- 
     ERL   : 20 dB
     ACOM  : 65 dB


 99 - Call from local port: 5/0, to remote voip: 0  (UDP) call-id: 53 (292) 
     calling : 3255335286, called : 32490661144
     setup time:  11/01/23 07h04m54s
     connexion time: 11/01/23 07h05m00s
         B channel (from B1..) : B1
     disconnected by remote voip: 0  (UDP) cause :(16)[Normal call clearing]
     call duration: 00:00:44
     PDD duration: 2156 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16416 /Dest ip :212.224.167.110 rtp:20716
     Play time (voice) : 00h00m44s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 2416 / 2417
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / --
     Number of Excessive Jitter events : 0
     MOS-CQ / MOS-LQ   : 4.34 / 4.39 
     ERL   : 15 dB
     ACOM  : 42 dB


 100 - Call from remote voip: 0  (UDP), to local port: 5/0 call-id: 51 (290) 
     calling : 476215202, called : 55335234
     setup time:  11/01/23 07h04m14s
     connexion time: 11/01/23 07h04m27s
         B channel (from B1..) : B1
     disconnected by local port: 5/0 cause :(16)[Normal call clearing]
     call duration: 00:00:12
     PDD duration: 3735 msec
     advice-of-charge: free
     call priority: 100
 
     RTP Source ip :94.105.56.114 rtp:16414 /Dest ip :212.224.167.110 rtp:20682
     Play time (voice) : 00h00m12s
     Tx Coder : G711 A Law / 20 ms ; Rx Coder : G711 A Law
     RTP Packets RX / TX : 577 / 575
     RTP Packet lost&discarded RX / TX (RTCP reported) : 0 / 0
     Number of Excessive Jitter events : 0
     MOS-CQ / MOS-LQ   : 4.34 / 4.39 
     ERL   : 26 dB
     ACOM  : 50 dB

```

**Help:** execute the command "show voice voip-call any all"

**Prompt:**
- oneaccess_oneos>
- oneaccess_oneos#

### show vrrp interface

**Output:**
```
GigabitEthernet 0/0 - Group 1
  State is master
  Version 2
  Virtual IP address 172.16.0.240, Netmask 255.255.255.0 (1)
  Virtual MAC address is 00:00:5e:00:01:01
  Advertisement interval is 5 sec
  Preemption is enabled, min delay is 15 sec
  Priority 105
  Master router is 172.16.0.241 (local), priority is 105
GigabitEthernet 0/1 - Group 3
  State is master
  Version 2
  Virtual IP address 172.16.3.240, Netmask 255.255.255.0 (1)
  Virtual MAC address is 00:00:5e:00:01:03
  Advertisement interval is 5 sec
  Preemption is enabled, min delay is 15 sec
  Priority 105
  Master router is 172.16.3.241 (local), priority is 105
GigabitEthernet 0/2 - Group 2
  State is master
  Version 2
  Virtual IP address 172.16.5.240, Netmask 255.255.255.0 (1)
  Virtual MAC address is 00:00:5e:00:01:02
  Advertisement interval is 5 sec
  Preemption is enabled, min delay is 15 sec
  Priority 105
  Master router is 172.16.5.241 (local), priority is 105
GigabitEthernet 0/3 - Group 4
  State is master
  Version 2
  Virtual IP address 172.16.6.240, Netmask 255.255.255.0 (1)
  Virtual MAC address is 00:00:5e:00:01:04
  Advertisement interval is 5 sec
  Preemption is enabled, min delay is 15 sec
  Priority 105
  Master router is 172.16.6.241 (local), priority is 105

```

**Help:** execute the command "show vrrp interface"

**Prompt:**
- oneaccess_oneos>
- oneaccess_oneos#

### _default_

**Output:**
```
% Invalid input detected
```

**Help:** default output for unknown commands

**Prompt:**
- oneaccess_oneos>
- oneaccess_oneos#

