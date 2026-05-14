# paloalto_panos


!!! warning
    This is automatically generated. In case of any issues,
    please refer to the source code or, even better,
    open an issue on the GitHub repository. Thanks! 🤗📖
## Commands

### set cli scripting-mode on

**Output:**
```
paloalto_panos> set cli scripting-mode on
```

**Help:** enable scripting mode

**Prompt:**
- paloalto_panos>

### set cli terminal width 500

**Output:** None

**Help:** set terminal width to 500 columns

**Prompt:**
- paloalto_panos>

### set cli pager off

**Output:** None

**Help:** disable paging

**Prompt:**
- paloalto_panos>

### ex

**Output:** None

**Help:** exit the terminal

**Prompt:**
- paloalto_panos>

### show interface logical

**Output:**
```
total configured logical interfaces: 38
​
name                id    vsys zone             forwarding               tag    address                                         
------------------- ----- ---- ---------------- ------------------------ ------ ------------------
ethernet1/1         16    1                     N/A                      0      N/A               
ethernet1/2         17    1                     N/A                      0      N/A               
ethernet1/2.100     275   1    ISP1         vr:default               100    65.5.44.46/30  
ethernet1/3         18    1                     N/A                      0      N/A               
ethernet1/3.101     278   1    ISP2         vr:default               101    65.5.26.46/30  
ethernet1/4         19    1                     N/A                      0      N/A               
ethernet1/4.102     256   1    WAN     vr:default               102    10.10.134.1/24  
ethernet1/5         20    1                     N/A                      0      N/A               
ethernet1/5.103     261   1    Voice            vr:default               101    10.10.248.49/24
ethernet1/6         21    1                     N/A                      0      N/A               
ethernet1/6.104     265   1    Video            vr:default               901    10.10.10.1/24    
ethernet1/7         22    1    Guest1   N/A                      0      N/A               
ethernet1/7.700     267   1    Guest1   vr:default               700    10.10.100.1/23     
dedicated-ha1       5     1                     ha                       0      10.1.1.1/30       
dedicated-ha2       6     1                     ha                       0      10.2.2.1/30       
vlan                1     1                     N/A                      0      N/A               
loopback            3     1                     N/A                      0      N/A               
tunnel              4     1                     N/A                      0      N/A   

```

**Help:** execute the command "show interface logical"

**Prompt:**
- paloalto_panos>

### show running nat-policy

**Output:**
```
"DMZ-PROXY-NAT; index: 1" {
        nat-type ipv4;
        from DMZ-APPS;
        source [ 10.1.1.1 10.1.1.2 ];
        to UNTRUSTED;
        to-interface ethernet1/5 ;
        destination any;
        service 0:any/any/any;
        translate-to "src: 2.2.2.2 (dynamic-ip-and-port) (pool idx: 1)";
        terminal no;
}

```

**Help:** execute the command "show running nat-policy"

**Prompt:**
- paloalto_panos>

### debug swm status

**Output:**
```

Partition         State             Version
--------------------------------------------------------------------------------
sysroot0          RUNNING-ACTIVE    9.0.5.xfr
sysroot1          PENDING-CHANGE    9.1.2
maint             READY             9.1.2

```

**Help:** execute the command "debug swm status"

**Prompt:**
- paloalto_panos>

### show mac all

**Output:**
```

maximum of entries supported :      1500
default timeout :                   1800 seconds
total MAC entries in table :        3
total MAC entries shown :           3
status: s - static, c - complete, i - incomplete

vlan                hw address        interface         status   ttl
--------------------------------------------------------------------------------
Test                00:50:00:00:07:00 ethernet1/2.110     c      1778
Test                00:50:00:00:08:00 ethernet1/2.111     c      1796
Test                50:00:00:02:00:01 ethernet1/2.110     c      704

```

**Help:** execute the command "show mac all"

**Prompt:**
- paloalto_panos>

### show system info

**Output:**
```
hostname: pa1
ip-address: 10.0.0.90
netmask: 255.255.255.0
default-gateway: 10.0.0.2
ipv6-address: unknown
ipv6-link-local-address: fe80::20c:29ff:fe6d:c67e/64
 ipv6-default-gateway: 
mac-address: 00:0c:29:6d:c6:7e
time: Thu Apr 28 06:33:12 2016
uptime: 2 days, 2:38:49
family: vm
model: PA-VM
serial: unknown
vm-mac-base: BA:DB:EE:FB:AD:00
vm-mac-count: 255
vm-uuid: 564D8B6D-7BDB-75AF-400F-B062016DC67E
 vm-cpuid: FB060000FDFB8B07
vm-license: none
vm-mode: VMWare ESXi
sw-version: 7.0.1
global-protect-client-package-version: 0.0.0
app-version: 497-2688
 app-release-date: unknown
av-version: 0
av-release-date: unknown
threat-version: 0
threat-release-date: unknown
wf-private-version: 0
wf-private-release-date: unknown
url-db: paloaltonetworks
wildfire-version: 0
wildfire-release-date: unknown
url-filtering-version: 0000.00.00.000
global-protect-datafile-version: 0
global-protect-datafile-release-date: unknown
logdb-version: 7.0.9
platform-family: vm
vpn-disable-mode: off
multi-vsys: off
operational-mode: normal


```

**Help:** execute the command "show system info"

**Prompt:**
- paloalto_panos>

### show high-availability all

**Output:**
```
Group 1: 
  Mode: Active-Passive
  Local Information:
    Version: 1
    Mode: Active-Passive
    State: active (last 45 days)
    Device Information:
      Model: PA-5020
      Management IPv4 Address: 10.10.186.197/24
      Management IPv6 Address: 
      Jumbo-Frames disabled; MTU 1500
    HA1 Control Links Joint Configuration:
      Link Monitor Interval: 3000 ms
      Encryption Enabled: no
    HA1 Control Link Information:
      IP Address: 10.1.1.1/30
      MAC Address: 00:90:0b:33:3d:53
      Interface: dedicated-ha1
      Link State: Up; Setting: 1Gb/s-full
      Key Imported : no
    HA2 Data Link Information:
      IP Address: 10.2.2.1/30
      MAC Address: 58:49:3b:1e:69:16
      Interface: dedicated-ha2
      Link State: Up; Setting: 1Gb/s-full
    Election Option Information:
      Priority: 50
      Preemptive: yes
      Promotion Hold Interval: 2000 ms
      Hello Message Interval: 8000 ms
      Heartbeat Ping Interval: 1000 ms
      Max # of Flaps: 3
      Preemption Hold Interval: 1 min
      Monitor Fail Hold Up Interval: 0 ms
      Addon Master Hold Up Interval: 500 ms
    Active-Passive Mode:
      Passive Link State: auto
      Monitor Fail Hold Down Interval: 1 min
    Version Information:
      Build Release: 6.1.10
      URL Database: 4773
      Application Content: 580-3287
      Anti-Virus: 1858-2337
      Threat Content: 580-3287
      VPN Client Software: Not Installed
      Global Protect Client Software: Not Installed
    Version Compatibility:
      Software Version: Match
      Application Content Compatibility: Match
      Anti-Virus Compatibility: Match
      Threat Content Compatibility: Match
      VPN Client Software Compatibility: Match
      Global Protect Client Software Compatibility: Match
    State Synchronization: Complete; type: ethernet
  Peer Information:
    Connection status: up
    Version: 1
    Mode: Active-Passive
    State: passive (last 45 days)
    Device Information:
      Model: PA-5020
      Management IPv4 Address: 10.10.186.198/24
      Management IPv6 Address: 
      Jumbo-Frames disabled; MTU 1500
    HA1 Control Link Information:
      IP Address: 10.1.1.2
      MAC Address: 00:90:0b:33:44:53
      Connection up; Primary HA1 link
    HA2 Data Link Information:
      IP Address: 10.2.2.2
      MAC Address: 58:49:3b:1e:55:16
    Election Option Information:
      Priority: 100
      Preemptive: yes
    Version Information:
      Build Release: 6.1.10
      URL Database: 4773
      Application Content: 580-3287
      Anti-Virus: 1858-2337
      Threat Content: 580-3287
      VPN Client Software: Not Installed
      Global Protect Client Software: Not Installed
  Initial Monitor Hold inactive; Allow Network/Links to Settle:
    Link and path monitoring failures honored
  Link Monitoring Information:
    Enabled: yes
    Failure condition: any
    Group Link:
      Enabled: yes
      Failure condition: any
      Interface ethernet1/1: up
      Interface ethernet1/2: up
      Interface ethernet1/3: up
      Interface ethernet1/4: up
      Interface ethernet1/5: up
      Interface ethernet1/6: up
      Interface ethernet1/7: up
      Interface ethernet1/8: up
  Path Monitoring Information:
    Enabled: yes
    Failure condition: any
    Virtual-Wire Groups:
      No Virtual-Wire path monitoring groups
    VLAN Groups:
      No VLAN path monitoring groups
    Virtual-Router Groups:
      No Virtual-Router path monitoring groups
  Configuration Synchronization:
    Enabled: yes
    Running Configuration: synchronized


```

**Help:** execute the command "show high-availability all"

**Prompt:**
- paloalto_panos>

### show counter global

**Output:**
```
Global counters:
Elapsed time since last sampling: 349.576 seconds

name                                   value     rate severity  category  aspect    description
--------------------------------------------------------------------------------
pkt_recv                                  29        0 info      packet    pktproc   Packets received
pkt_sent                                  21        0 info      packet    pktproc   Packets transmitted
pkt_sock_recv                              1        0 info      packet    pktproc   Packets received at socket level - delayed counter
pkt_lldp_sent                              1        0 info      packet    pktproc   LLDP Packets transmitted
flow_rcv_dot1q_tag_err                     1        0 drop      flow      parse     Packets dropped: 802.1q tag not configured
flow_no_interface                          1        0 drop      flow      parse     Packets dropped: invalid interface
ssl_hsm_up_down_event_rcv                  1        0 info      ssl       pktproc   The number of HSM up/down events received
--------------------------------------------------------------------------------
 Total counters shown: 7
--------------------------------------------------------------------------------


```

**Help:** execute the command "show counter global"

**Prompt:**
- paloalto_panos>

### show jobs all

**Output:**
```

Enqueued              Dequeued           ID  PositionInQ                              Type                         Status Result Completed
 ------------------------------------------------------------------------------------------------------------------------------------------
 2017/02/28 10:19:48   10:19:48            7                                    FqdnRefresh                            FIN     OK 10:20:11
2017/02/28 10:13:49   10:13:49            6                                    FqdnRefresh                            FIN     OK 10:14:21
2017/02/28 10:13:22   10:13:22            5                                         Commit                            FIN     OK 10:13:49
2017/02/27 12:06:50   12:06:50            4                                         Commit                            FIN     OK 12:07:18
2017/02/27 12:02:54   12:02:54            3                                         Commit                            FIN     OK 12:03:20
2017/02/27 11:55:15   11:55:15            2                                         Commit                            FIN     OK 11:55:42
 2017/02/23 08:31:14   08:31:14            1                                        AutoCom                            FIN     OK 08:32:06



```

**Help:** execute the command "show jobs all"

**Prompt:**
- paloalto_panos>

### show arp all

**Output:**
```

maximum of entries supported :      1500
default timeout:                    1800 seconds
total ARP entries in table :        5
total ARP entries shown :           5
status: s - static, c - complete, e - expiring, i - incomplete

interface         ip address      hw address        port              status   ttl
--------------------------------------------------------------------------------
ethernet1/1       172.25.1.254    08:30:6b:26:43:30 ethernet1/1         c      627
vlan.1            172.25.2.195    00:50:00:00:07:00 ethernet1/2.110     c      1012
vlan.1            172.25.2.196    00:50:00:00:08:00 ethernet1/2.111     c      1016
vlan.1            172.25.2.197    (incomplete)      ethernet1/2.111     c      1016

```

**Help:** execute the command "show arp all"

**Prompt:**
- paloalto_panos>

### show interface hardware

**Output:**
```
total configured hardware interfaces: 26

name                    id    speed/duplex/state        mac address
--------------------------------------------------------------------------------
ethernet1/1             64    1000/full/up              c4:24:56:d7:30:40
ethernet1/2             65    ukn/ukn/down(autoneg)     c4:24:56:d7:30:41
ethernet1/3             66    ukn/ukn/down(autoneg)     c4:24:56:d7:30:42
ethernet1/4             67    ukn/ukn/down(autoneg)     c4:24:56:d7:30:43
ethernet1/5             68    ukn/ukn/down(autoneg)     c4:24:56:d7:30:44
ethernet1/6             69    ukn/ukn/down(autoneg)     c4:24:56:d7:30:45
ethernet1/7             70    ukn/ukn/down(autoneg)     c4:24:56:d7:30:46
ethernet1/8             71    ukn/ukn/down(autoneg)     c4:24:56:d7:30:47
ethernet1/9             72    ukn/ukn/down(autoneg)     c4:24:56:d7:30:48
ethernet1/10            73    ukn/ukn/down(autoneg)     c4:24:56:d7:30:49
ethernet1/11            74    ukn/ukn/down(autoneg)     c4:24:56:d7:30:4a
ethernet1/12            75    ukn/ukn/down(autoneg)     c4:24:56:d7:30:4b
ethernet1/13            76    ukn/ukn/down(autoneg)     c4:24:56:d7:30:4c
ethernet1/14            77    ukn/ukn/down(autoneg)     c4:24:56:d7:30:4d
ethernet1/15            78    ukn/ukn/down(autoneg)     c4:24:56:d7:30:4e
ethernet1/16            79    ukn/ukn/down(autoneg)     c4:24:56:d7:30:4f
ethernet1/17            80    10000/full/up             c4:24:56:d7:30:50
ethernet1/18            81    10000/full/up             c4:24:56:d7:30:51
ethernet1/19            82    ukn/ukn/down(autoneg)     c4:24:56:d7:30:52
ethernet1/20            83    ukn/ukn/down(autoneg)     c4:24:56:d7:30:53
ha1-a                   5     ukn/ukn/down(autoneg)     08:66:1f:02:04:a2
ha1-b                   7     ukn/ukn/down(autoneg)     c4:24:56:d7:30:07
vlan                    1     [n/a]/[n/a]/up            c4:24:56:d7:30:01
loopback                3     [n/a]/[n/a]/up            c4:24:56:d7:30:03
tunnel                  4     [n/a]/[n/a]/up            c4:24:56:d7:30:04
hsci                    8     ukn/ukn/down(autoneg)     c4:24:56:d7:30:08

 aggregation groups: 0
```

**Help:** execute the command "show interface hardware"

**Prompt:**
- paloalto_panos>

### show running security-policy

**Output:**
```
"Outside Web Server" {
        from Trust;
        source 10.1.1.0/24;
        source-region none;
        to Untrust;
        destination 200.10.10.10;
        destination-region none;
        user any;
        category any;
        application/service [ any/tcp/any/8000 any/tcp/any/80 any/tcp/any/8080 ];
        action allow;
        icmp-unreachable: no
        terminal yes;
}

"ICMP Any" {
        from Trust;
        source any;
        source-region none;
        to Untrust;
        destination any;
        destination-region none;
        user any;
        category any;
        application/service [ icmp/icmp/any/any ping/icmp/any/any ];
        action allow;
        icmp-unreachable: no
        terminal yes;
}

"DNS Outbound" {
        from Trust;
        source 10.1.1.0/24;
        source-region none;
        to Untrust;
        destination [ 8.8.8.8 8.8.4.4 ];
        destination-region none;
        user any;
        category any;
        application/service  dns/udp/any/53;
        action allow;
        icmp-unreachable: no
        terminal yes;
}

"Inbound to DMZ Web" {
        from Untrust;
        source any;
        source-region none;
        to DMZ;
        destination 200.10.10.100;
        destination-region none;
        user any;
        category any;
        application/service [ any/tcp/any/8000 any/tcp/any/80 any/tcp/any/8080 ];
        action allow;
        icmp-unreachable: no
        terminal yes;
}

"Inbound to DMZ Deny" {
        from Untrust;
        source any;
        source-region none;
        to DMZ;
        destination any;
        destination-region none;
        user any;
        category any;
        application/service  any/any/any/any;
        action deny;
        icmp-unreachable: no
        terminal no;
}

intrazone-default {
        from any;
        source any;
        source-region none;
        to any;
        destination any;
        destination-region none;
        category any;
        application/service  any/any/any/any;
        action allow;
        icmp-unreachable: no
        terminal yes;
        type intrazone;
}

interzone-default {
        from any;
        source any;
        source-region none;
        to any;
        destination any;
        destination-region none;
        category any;
        application/service  any/any/any/any;
        action deny;
        icmp-unreachable: no
        terminal yes;
        type interzone;
}

dynamic url: no
pol objs matched


```

**Help:** execute the command "show running security-policy"

**Prompt:**
- paloalto_panos>

### test security-policy-match

**Output:**
```
"Allow 10.125.100.58-To-Google DNS; index: 1" {
        from Internal;
        source 10.125.100.58;
        source-region none;
        to External;
        destination 8.8.8.8;
        destination-region none;
        user any;
        source-device any;
        destinataion-device any;
        category any;
        application/service 0:any/tcp/any/59;
        action allow;
        icmp-unreachable: no
        terminal yes;
}

"Allow 10.125.100.58-To-1.1.1.1; index: 2" {
        from Internal;
        source 10.125.100.58;
        source-region none;
        to External;
        destination 1.1.1.1;
        destination-region none;
        user any;
        source-device any;
        destinataion-device any;
        category any;
        application/service 0:any/tcp/any/53;
        action allow;
        icmp-unreachable: no
        terminal yes;
}

"Allow DNS_Objects-To-192.0.2.10; index: 4" {
        from Internal;
        source [ 1.1.1.1 8.8.8.8 ];
        source-region none;
        to External;
        destination 192.0.2.10;
        destination-region none;
        user any;
        source-device any;
        destinataion-device any;
        category any;
        application/service [0:any/tcp/any/53 1:any/tcp/any/54 ];
        action allow;
        icmp-unreachable: no
        terminal yes;
}
```

**Help:** execute the command "test security-policy-match"

**Prompt:**
- paloalto_panos>

### show interface management

**Output:**
```


-------------------------------------------------------------------------------
 Name: Management Interface
Link status:
  Runtime link speed/duplex/state: 1000/full/up
  Configured link speed/duplex/state: auto/auto/auto
MAC address:
  Port MAC address 08:66:1f:02:04:a3

Ip address: 10.0.1.5
Netmask: 255.255.255.0
 Default gateway: 10.0.1.1
Ipv6 address: unknown
Ipv6 link local address: fe80::a66:1fff:fe02:4a3/64
 Ipv6 default gateway:
-------------------------------------------------------------------------------
 

-------------------------------------------------------------------------------
 Logical interface counters:
-------------------------------------------------------------------------------
 bytes received                    264279971
bytes transmitted                 238725455
packets received                  279836
packets transmitted               291248
receive errors                    0
transmit errors                   0
receive packets dropped           0
transmit packets dropped          0
multicast packets received        0
-------------------------------------------------------------------------------

```

**Help:** execute the command "show interface management"

**Prompt:**
- paloalto_panos>

### request license info

**Output:**
```
Current PDT Date: May 19, 2021

License entry:
Feature: WildFire License
Description: WildFire signature feed, integrated WildFire logs, WildFire API
Serial: 0000000xxxxxxxx
Issued: January 13, 2020
Expires: March 08, 2023
Expired?: no
Base license: PA-VM

License entry:
Feature: Premium
Description: 24 x 7 phone support; advanced replacement hardware service
Serial: 0000000xxxxxxxx
Issued: January 13, 2020
Expires: January 09, 2023
Expired?: no
Base license: PA-VM

License entry:
Feature: PAN-DB URL Filtering
Description: Palo Alto Networks URL Filtering License
Serial: 0000000xxxxxxxx
Issued: January 13, 2020
Expires: March 08, 2023
Expired?: no
Base license: PA-VM

License entry:
Feature: GlobalProtect Portal
Description: GlobalProtect Portal License
Serial: 0000000xxxxxxxx
Issued: March 08, 2017
Expires: Never
Expired?: no
Base license: PA-VM

License entry:
Feature: PA-VM
Description: Standard VM-100
Serial: 0000000xxxxxxxx
Issued: March 08, 2017
Expires: Never
Expired?: no

License entry:
Feature: Threat Prevention
Description: Threat Prevention
Serial: 0000000xxxxxxxx
Issued: January 13, 2020
Expires: January 13, 2023
Expired?: no
Base license: PA-VM

License entry:
Feature: GlobalProtect Gateway
Description: GlobalProtect Gateway License
Serial: 0000000xxxxxxxx
Issued: January 13, 2020
Expires: March 08, 2023
Expired?: no
Base license: PA-VM
Authcode: abc def

```

**Help:** execute the command "request license info"

**Prompt:**
- paloalto_panos>

### show high-availability path-monitoring

**Output:**
```
--------------------------------------------------------------------------------
total paths monitored :                         2
hold time to send probe packets :               1000 ms
  (after device becomes active)
--------------------------------------------------------------------------------
grp/name/type             destination     suc/total rtt min/max/avg (ms) probe cnt/interval(ms)
--------------------------------------------------------------------------------
HA_PATH_NORTH/VR_HANDOFF/virtual-router 8.8.8.8         10/10     3.66/4.19/3.90      10/1000    
HA_PATH_NORTH/VR_HANDOFF/virtual-router 217.111.187.217 10/10     2.36/2.75/2.58      10/1000    
--------------------------------------------------------------------------------
```

**Help:** execute the command "show high-availability path-monitoring"

**Prompt:**
- paloalto_panos>

### show routing protocol bgp summary

**Output:**
```
  ==========
  router id:                     1.1.1.1
  virtual router:                VR_HANDOFF
  reject default route:          no
  redist default route:          allow
  Install BGP routes:            yes
  Graceful Restart:              supported
  AS size:                       2
  Local AS:                      65253
  Local member AS:               0
  Cluster id:                    0.0.0.0
  Default local preference:      100
  Always compare MED:            no
  Aggregate regardless MED:      yes
  Deterministic MED processing:  yes
  Accept ORF:                    no
  Accept CISCO style prefix:     yes
  mp-bgp-enable:                 yes
  afi-safi-ipv4-unicast:         yes
  rib-out entries:               current 46, peak 47 
    peer DC-N9K-BGW01 - BLU 301: AS 65253, Established, IP 192.168.1.1
      bgpAfiIpv4/unicast pfx:    Accepted pfx: 4, Advertised pfx: 4
    peer DC-N9K-BGW02 - BLU 301: AS 65301, Established, IP 192.168.1.2
      bgpAfiIpv4/unicast pfx:    Accepted pfx: 4, Advertised pfx: 4
    peer DC-N9K-BGW01 - GRN 302: AS 65253, Established, IP 192.168.2.9
      bgpAfiIpv4/unicast pfx:    Accepted pfx: 3, Advertised pfx: 4
    peer DC-N9K-BGW02 - GRN 302: AS 65302, Established, IP 192.168.2.10
      bgpAfiIpv4/unicast pfx:    Accepted pfx: 3, Advertised pfx: 4
    peer DC-N9K-BGW01 - AMB 303: AS 65253, Established, IP 192.168.3.17
      bgpAfiIpv4/unicast pfx:    Accepted pfx: 2, Advertised pfx: 3
    peer DC-N9K-BGW02 - AMB 303: AS 65303, Established, IP 192.168.3.18
      bgpAfiIpv4/unicast pfx:    Accepted pfx: 2, Advertised pfx: 3

```

**Help:** execute the command "show routing protocol bgp summary"

**Prompt:**
- paloalto_panos>

### show routing resource

**Output:**
```
GLOBAL ROUTING RESOURCE USAGE:
  ==========
  All      Routes (total):             18 	(limit    10000)
  All IPv4 Routes (total):             18 	(limit    10000)
  All IPv6 Routes (total):              0 	(limit    10000)
  All     Routes (active):             18
  ==========
  Static   Routes (total):              5
  Connect  Routes (total):              4
  BGP      Routes (total):              9
  OSPF     Routes (total):              0
  RIP      Routes (total):              0
```

**Help:** execute the command "show routing resource"

**Prompt:**
- paloalto_panos>

### show routing route

**Output:**
```
flags: A:active, ?:loose, C:connect, H:host, S:static, ~:internal, R:rip, O:ospf, B:bgp, 
       Oi:ospf intra-area, Oo:ospf inter-area, O1:ospf ext-type-1, O2:ospf ext-type-2, E:ecmp, M:multicast

  
VIRTUAL ROUTER: VR_HANDOFF (id 3)
  ==========
destination                                 nexthop                                 metric flags      age   interface          next-AS    
0.0.0.0/0                                   192.168.2.49                                   A?B        121661                    0          
10.0.0.0/8                                  discard                                 10     A S                                            
10.0.0.1/32                                 192.168.2.44                                   A?B        120738                    65213      
10.0.0.2/32                                 192.168.2.44                                   A?B        120738                    65213           
10.3.0.0/16                                 discard                                 10     A S                                            
10.3.0.0/20                                 192.168.2.1                                    A?B        121661                    65213      
10.3.0.0/21                                 192.168.2.1                                    A?B        121661                    65213          
10.3.252.0/23                               192.168.2.49                                   A?B        121661                    0          
10.3.252.0/24                               192.168.2.49                                   A?B        121661                    0          
10.3.252.0/28                               discard                                 10     A S                                            
10.3.253.0/28                               discard                                 10     A S                                            
10.3.255.0/24                               192.168.2.25                                   A?B        121661                    65213      
10.3.255.0/25                               192.168.2.25                                   A?B        121661                    65213              
172.16.0.0/12                               discard                                 10     A S                                            
172.17.0.0/16                               discard                                 10     A S                                            
172.17.0.0/17                               192.168.2.1                                    A?B        121661                    65213      
172.17.128.0/18                             192.168.2.9                                    A?B        121661                    65213         
172.30.0.0/18                               192.168.2.49                                   A?B        121661                    0          
172.30.0.0/19                               192.168.2.49                                   A?B        121661                    0                  
192.168.0.0/16                              discard                                 10     A S                                            
192.168.2.0/29                              192.168.2.3                             0      A C              ethernet1/8.3111              
192.168.2.3/32                              0.0.0.0                                 0      A H                                            
192.168.2.8/29                              192.168.2.11                            0      A C              ethernet1/8.3112              
192.168.2.11/32                             0.0.0.0                                 0      A H                                            
192.168.2.16/29                             192.168.2.19                            0      A C              ethernet1/8.3113              
192.168.2.19/32                             0.0.0.0                                 0      A H                                                                              
192.168.5.10/31                             192.168.2.41                                   A?B        121661                    65213      
192.168.5.26/31                             192.168.2.41                                   A?B        121661                    65213      
total routes shown: 98
```

**Help:** execute the command "show routing route"

**Prompt:**
- paloalto_panos>

### show interface all

**Output:**
```
total configured hardware interfaces: 12
name                    id    speed/duplex/state/fec        mac address
--------------------------------------------------------------------------------
ethernet1/8             23    1000/full/up/auto             00:1b:17:aa:bb:01
ethernet1/13            28    1000/full/up/auto             00:1b:17:aa:bb:02
ethernet1/14            29    1000/full/up/auto             00:1b:17:aa:bb:03
ethernet1/19            34    10000/full/up/auto            00:1b:17:aa:bb:04
ae1                     64    [n/a]/[n/a]/up/[n/a]          00:1b:17:aa:bb:40
ae2                     65    [n/a]/[n/a]/up/[n/a]          00:1b:17:aa:bb:41
ha1-a                   5     1000/full/up/ukn              8c:36:7a:aa:bb:b5
ha1-b                   7     ukn/ukn/down((autoneg))/ukn   8c:36:7a:aa:bb:b4
vlan                    1     [n/a]/[n/a]/up/[n/a]          00:1b:17:aa:bb:01
loopback                3     [n/a]/[n/a]/up/[n/a]          00:1b:17:aa:bb:03
tunnel                  4     [n/a]/[n/a]/up/[n/a]          00:1b:17:aa:bb:04
hsci                    8     10000/full/up/ukn             64:7c:e8:aa:bb:08

aggregation groups: 2
ae1 members:
  ethernet1/19 ethernet1/20
ae2 members:
  ethernet1/11


total configured logical interfaces: 14

name                      id    vsys zone             forwarding               tag    address

------------------- ----- ---- ---------------- ------------------------ ------ ------------------
ethernet1/8               23    3    ZONE_TECH        vr:vrf01                 0      192.0.2.1/28
ethernet1/8.81            300   3    ZONE_TECH        vr:vrf01                 81     192.0.2.17/27
ethernet1/13              28    5    ZONE_INET        vr:vrf02                 0      192.0.2.33/29
                                                                                10.10.10.1/29
ethernet1/13.388          298   2    ZONE_SDWAN       vr:vrf03                 388    192.0.2.65/27
ethernet1/14              29    5    ZONE_INET        vr:vrf02                 0      192.0.2.97/28
ae1                       64    2                     N/A                      0      N/A
ae1.99                    267   2    ZONE_OTSC        vr:vrf03                 99     192.0.2.113/28
ae5                       68    5                     vr:vrf02                 0      N/A
ha1-a                     5     0                     ha                       0      198.51.100.1/30
vlan                      1     1                     N/A                      0      N/A
loopback                  3     1                     N/A                      0      N/A
loopback.99               297   2    ZONE_CORP        vr:vrf03                 0      192.0.2.129/32
tunnel                    4     1                     N/A                      0      N/A
hsci                      8     0                     N/A                      0      198.51.100.5/30

```

**Help:** execute the command "show interface all"

**Prompt:**
- paloalto_panos>

### show lacp aggregate-ethernet all

**Output:**
```
**********************************************************************************
AE group: ae1
Members:                Bndl Rx state       Mux state  Sel state
  ethernet1/19          yes  Current        Tx_Rx      Selected
  ethernet1/20          yes  Current        Tx_Rx      Selected
Status:           Enabled
Mode:             Active
Rate:             Slow
Max-port:         8
Fast-failover:    Disabled
Pre-negotiation:  Enabled
Local:            System Priority: 32768
                  System MAC:      64:7c:e8:aa:bb:01
                  Key:             64
Partner:          System Priority: 65534
                  System MAC:      0a:00:00:aa:bb:cc
                  Key:             103
Port State
--------------------------------------------------------------------------------
Interface                       Port
                    Number Priority  Mode    Rate  Key      State
--------------------------------------------------------------------------------
ethernet1/19         34     32768    Active  Slow  64       0x3D
Partner              3      1        Active  Slow  103      0x3D

ethernet1/20         35     32768    Active  Slow  64       0x3D
Partner              1003   1        Active  Slow  103      0x3D

Port Counters
--------------------------------------------------------------------------------
Interface               LACPDUs         Marker      Marker Response       Error
                    Sent     Recv     Sent Recv     Sent     Recv     Unknown  Illegal
--------------------------------------------------------------------------------
ethernet1/19         100      100      0    0        0        0        0        0
ethernet1/20         100      100      0    0        0        0        0        0

**********************************************************************************
AE group: ae2
Members:                Bndl Rx state       Mux state  Sel state
  ethernet1/11          yes  Current        Tx_Rx      Selected
Status:           Enabled
Mode:             Active
Rate:             Slow
Max-port:         8
Fast-failover:    Disabled
Pre-negotiation:  Enabled
Local:            System Priority: 32768
                  System MAC:      64:7c:e8:aa:bb:01
                  Key:             65
Partner:          System Priority: 32768
                  System MAC:      64:7c:e8:aa:bb:01
                  Key:             67
Port State
--------------------------------------------------------------------------------
Interface                       Port
                    Number Priority  Mode    Rate  Key      State
--------------------------------------------------------------------------------
ethernet1/11         26     32768    Active  Slow  65       0x3D
Partner              27     32768    Active  Slow  67       0x3D

Port Counters
--------------------------------------------------------------------------------
Interface               LACPDUs         Marker      Marker Response       Error
                    Sent     Recv     Sent Recv     Sent     Recv     Unknown  Illegal
--------------------------------------------------------------------------------
ethernet1/11         100      100      0    0        0        0        0        0

```

**Help:** execute the command "show lacp aggregate-ethernet all"

**Prompt:**
- paloalto_panos>

