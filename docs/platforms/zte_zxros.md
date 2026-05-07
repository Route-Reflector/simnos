# zte_zxros


!!! warning
    This is automatically generated. In case of any issues,
    please refer to the source code or, even better,
    open an issue on the GitHub repository. Thanks! 🤗📖
## Commands

### enable

**Output:** None

**Help:** enter enable mode

**Prompt:**
- zte_zxros>

### show arp

**Output:**
```
Arp protect whole is disabled 
The count is 17
IP                       Hardware                    Exter  Inter  Sub
Address         Age      Address        Interface    VlanID VlanID Interface
--------------------------------------------------------------------------------
10.10.255.1    H        744a.a42b.2010 xgei-1/1/0/1 201    N/A    N/A
                                        .201                       
10.10.255.2    00:14:17 0427.5873.0b65 xgei-1/1/0/1 201    N/A    xgei-1/1/0/1.
                                        .201                       201
10.10.10.249    H        744a.a42b.2010 xgei-1/1/0/1 301    N/A    N/A
                                        .301                       
10.10.10.250    00:14:17 0427.5873.0b65 xgei-1/1/0/1 301    N/A    xgei-1/1/0/1.
                                        .301                       301
10.10.10.25     H        744a.a42b.2010 xgei-1/1/0/1 401    N/A    N/A
                                        .401                       
10.10.10.26     00:14:17 0427.5873.0b65 xgei-1/1/0/1 401    N/A    xgei-1/1/0/1.
                                        .401                       401
10.10.10.253    H        744a.a42b.2010 xgei-1/1/0/1 1001   N/A    N/A
                                        .1001                      
10.10.10.254    00:14:17 0427.5873.0b65 xgei-1/1/0/1 1001   N/A    xgei-1/1/0/1.
                                        .1001                      1001
10.102.195.181  H        744a.a42b.2010 xgei-1/1/0/2 3100   N/A    N/A
                                        .3100                      
10.102.195.182  00:00:39 8cdf.9d27.35c0 xgei-1/1/0/2 3100   N/A    xgei-1/1/0/2.
                                        .3100                      3100
10.89.255.201   H        744a.a42b.2010 xgei-1/1/0/2 3901   N/A    N/A
                                        .3901                      
10.89.255.202   00:15:00 0020.85f8.5d58 xgei-1/1/0/2 3901   N/A    xgei-1/1/0/2.
                                        .3901                      3901
10.10.184.255  H        744a.a42b.2010 xxvgei-1/1/0 N/A    N/A    N/A
                                        /20                        
10.10.184.254  01:20:43 744a.a42b.1fe8 xxvgei-1/1/0 N/A    N/A    xxvgei-1/1/0/
                                        /20                        20
10.10.185.2    H        744a.a42b.2010 xxvgei-1/1/0 N/A    N/A    N/A
                                        /24                        
10.10.185.3    03:09:39 744a.a42b.d358 xxvgei-1/1/0 N/A    N/A    xxvgei-1/1/0/
                                        /24                        24
192.168.1.11  H        744a.a42b.2011 mgmt_eth     N/A    N/A    N/A

```

**Help:** execute the command "show arp"

**Prompt:**
- zte_zxros>
- zte_zxros#

### show interface

**Output:**
```
xxvgei-1/1/0/24 is up, ifindex: 8225
  Description: R-xxxxx-01Z_xxvgei-1/1/0/24_to_R-xxxxx02-01Z_xxvgei-1/1/0/20;by:XXX;CID:XXXXXXX 
  Line protocol is up, IPv4 protocol is up, IPv6 protocol is down,
 detected status is RX-OK/TX-OK
  Last line protocol up time :  2023-04-02 15:42:13 
  Hardware is XXVGigabit Ethernet, address is 744a.a42b.2010
  Internet address is 10.206.185.2/31 
  BW 10 Gbit/s
  IP MTU 9178 bytes
  MTU 9192 bytes
  MPLS MTU 9178 bytes

  Fec-eth : N/A
  Fec-bypass : disable
  ARP type ARP
  ARP Timeout 04:00:00 
  Last Clear Time : 2023-03-15 00:23:16  Last Refresh Time: 2023-04-07 11:17:50
  Rate period     : 30 s                                     
   Input          : 54070488 bit/s       17263 packet/s      
   Output         : 181452736 bit/s      19848 packet/s      
  Peak rate:                                                 
   Input          : 193604816 bit/s      peak time          2023-03-18 19:13:50
   Output         : 1832230896 bit/s     peak time          2023-03-18 20:36:40
  Intf utilization: input 0.54%          output 1.81%        
  HardwareCounters:                                          
  In_Bytes          9284060783182        In_Packets         37909098091
  In_Broadcasts     3                    In_Multicasts      1009767
  In_Unicasts       37908088321          In_CRC_ERROR       0
  In_Fragments      0                    In_64B             39549
  In_65_127B        23801374871          In_128_255B        7867332105
  In_256_511B       1669025875           In_512_1023B       1998802757
  In_1024_1518B     2559890154           In_1519_MaxB       12632780
  In_Undersize      0                    In_Oversize        0
  E_Bytes           91949543490869       E_Packets          79122043711
  E_Broadcasts      5                    E_Multicasts       1086970
  E_Unicasts        79120956747          E_CRC_ERROR        0
  E_64B             20521174             E_65_127B          7788975586
  E_128_255B        5664052345           E_256_511B         1768390101
  E_512_1023B       1247046702           E_1024_1518B       62105204361
  E_1519_MaxB       527853452            E_Oversize         0
  StreamCounters  :                                          
  In_Bytes          9284060783182        In_Packets         37909098091
  E_Bytes           91949543490869       E_Packets          79122043711
xxvgei-1/1/0/32 is administratively down, ifindex: 8233
  The interface is configured shutdown
  Line protocol is down, IPv4 protocol is down, IPv6 protocol is down,
 detected status is RX-OK/TX-OK
  Last line protocol up time :  - 
  Hardware is XXVGigabit Ethernet, address is 744a.a42b.2010
  Internet address is unassigned
  BW 25 Gbit/s
  IP MTU 1500 bytes
  MTU 1600 bytes
  MPLS MTU 1550 bytes

  Fec-eth : enable
  Fec-bypass : disable
  ARP type ARP
  ARP Timeout 04:00:00 
  Last Clear Time : 2023-03-15 00:23:16  Last Refresh Time: 2023-03-15 00:23:16
  Rate period     : 30 s                                     
   Input          : 0 bit/s              0 packet/s          
   Output         : 0 bit/s              0 packet/s          
  Peak rate:                                                 
   Input          : 0 bit/s              peak time          N/A
   Output         : 0 bit/s              peak time          N/A
  Intf utilization: input 0%             output 0%           
  HardwareCounters:                                          
  In_Bytes          0                    In_Packets         0
  In_Broadcasts     0                    In_Multicasts      0
  In_Unicasts       0                    In_CRC_ERROR       0
  In_Fragments      0                    In_64B             0
  In_65_127B        0                    In_128_255B        0
  In_256_511B       0                    In_512_1023B       0
  In_1024_1518B     0                    In_1519_MaxB       0
  In_Undersize      0                    In_Oversize        0
  E_Bytes           0                    E_Packets          0
  E_Broadcasts      0                    E_Multicasts       0
  E_Unicasts        0                    E_CRC_ERROR        0
  E_64B             0                    E_65_127B          0
  E_128_255B        0                    E_256_511B         0
  E_512_1023B       0                    E_1024_1518B       0
  E_1519_MaxB       0                    E_Oversize         0
  StreamCounters  :                                          
  In_Bytes          0                    In_Packets         0
  E_Bytes           0                    E_Packets          0
mgmt_eth is down, ifindex: 262145
  Line protocol is down, IPv4 protocol is down, IPv6 protocol is down,
 detected status is RX-OK/TX-OK
  Last line protocol up time :  2023-03-15 00:21:14 
  Hardware is Management Ethernet, address is 744a.a42b.2011
  Internet address is 192.168.1.11/24 
  BW 100 Mbit/s
  IP MTU 1500 bytes
  MTU 1514 bytes
  ARP type ARP
  ARP Timeout 04:00:00 
  Last Clear Time : 2023-03-15 00:21:14  Last Refresh Time: 2023-03-15 00:21:20
  Rate period     : 30 s                                     
   Input          : 0 bit/s              0 packet/s          
   Output         : 0 bit/s              0 packet/s          
  Peak rate:                                                 
   Input          : 0 bit/s              peak time          N/A
   Output         : 0 bit/s              peak time          N/A
  Intf utilization: input 0%             output 0%           
  HardwareCounters:                                          
  In_Bytes          0                    In_Packets         0
  In_Broadcasts     N/A                  In_Multicasts      0
  In_Unicasts       N/A                  In_CRC_ERROR       N/A
  In_Fragments      N/A                  In_64B             N/A
  In_65_127B        N/A                  In_128_255B        N/A
  In_256_511B       N/A                  In_512_1023B       N/A
  In_1024_1518B     N/A                  In_1519_MaxB       N/A
  In_Undersize      N/A                  In_Oversize        0
  E_Bytes           836                  E_Packets          11
  E_Broadcasts      N/A                  E_Multicasts       N/A
  E_Unicasts        N/A                  E_CRC_ERROR        N/A
  E_64B             N/A                  E_65_127B          N/A
  E_128_255B        N/A                  E_256_511B         N/A
  E_512_1023B       N/A                  E_1024_1518B       N/A
  E_1519_MaxB       N/A                  E_Oversize         0
loopback0 is up, ifindex: 8234
  Description: Management&Traffic address 
  Line protocol is up, IPv4 protocol is up, IPv6 protocol is up,
 detected status is RX-OK/TX-OK
  Last line protocol up time :  2023-03-15 00:21:12 
  Hardware is Loopback, address is 744a.a42b.2010
  Internet address is 10.10.10.108/32 
  BW 8 Gbit/s
  IP MTU 1500 bytes
  IPv6 MTU 1500 bytes
  MPLS MTU 1550 bytes

```

**Help:** execute the command "show interface"

**Prompt:**
- zte_zxros>
- zte_zxros#

### show interface brief

**Output:**
```
Interface               Attribute  Mode         BW    Admin Phy   Prot  Description                                               
xgei-1/1/0/1            optical    Duplex/full  1G    up    up    up    Link_to_XXXXXX                  
xgei-1/1/0/2            optical    Duplex/full  1G    up    up    up    Link_to_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX... 
xgei-1/1/0/3            optical    Duplex/full  1G    down  down  down                                                            
xgei-1/1/0/4            optical    Duplex/full  1G    down  down  down                                                            
xgei-1/1/0/5            optical    Duplex/full  10G   down  down  down                                                            
xgei-1/1/0/6            optical    Duplex/full  10G   down  down  down                                                            
xgei-1/1/0/7            optical    Duplex/full  10G   down  down  down                                                            
xgei-1/1/0/8            optical    Duplex/full  10G   down  down  down                                                            
xgei-1/1/0/9            optical    Duplex/full  10G   down  down  down                                                            
xgei-1/1/0/10           optical    Duplex/full  10G   down  down  down                                                            
cgei-1/1/0/33           optical    Duplex/full  100G  down  down  down                                                            
cgei-1/1/0/34           optical    Duplex/full  100G  down  down  down                                                            
cgei-1/1/0/35           optical    Duplex/full  100G  down  down  down                                                            
cgei-1/1/0/36           optical    Duplex/full  100G  down  down  down                                                            
xxvgei-1/1/0/11         optical    Duplex/full  25G   down  down  down                                                            
xxvgei-1/1/0/12         optical    Duplex/full  25G   down  down  down                                                            
xxvgei-1/1/0/13         optical    Duplex/full  25G   down  down  down                                                            
xxvgei-1/1/0/14         optical    Duplex/full  25G   down  down  down                                                            
xxvgei-1/1/0/15         optical    Duplex/full  25G   down  down  down                                                            
xxvgei-1/1/0/16         optical    Duplex/full  25G   down  down  down                                                            
xxvgei-1/1/0/17         optical    Duplex/full  25G   down  down  down                                                            
xxvgei-1/1/0/18         optical    Duplex/full  25G   down  down  down                                                            
xxvgei-1/1/0/19         optical    Duplex/full  25G   down  down  down                                                            
xxvgei-1/1/0/20         optical    Duplex/full  10G   up    up    up    R-xxxx-01Z_xxvgei-1/1/0/20_to_C-XXXXXX-02Z_... 
xxvgei-1/1/0/21         optical    Duplex/full  25G   down  down  down                                                            
xxvgei-1/1/0/22         optical    Duplex/full  25G   down  down  down                                                            
xxvgei-1/1/0/23         optical    Duplex/full  25G   down  down  down                                                            
xxvgei-1/1/0/24         optical    Duplex/full  10G   up    up    up    R-xxxx01-01Z_xxvgei-1/1/0/24_to_R-XXXXX02-01Z_x... 
xxvgei-1/1/0/25         optical    Duplex/full  25G   down  down  down                                                            
xxvgei-1/1/0/26         optical    Duplex/full  25G   down  down  down                                                            
xxvgei-1/1/0/27         optical    Duplex/full  25G   down  down  down                                                            
xxvgei-1/1/0/28         optical    Duplex/full  25G   down  down  down                                                            
xxvgei-1/1/0/29         optical    Duplex/full  25G   down  down  down                                                            
xxvgei-1/1/0/30         optical    Duplex/full  25G   down  down  down                                                            
xxvgei-1/1/0/31         optical    Duplex/full  25G   down  down  down                                                            
xxvgei-1/1/0/32         optical    Duplex/full  25G   down  down  down  

```

**Help:** execute the command "show interface brief"

**Prompt:**
- zte_zxros>
- zte_zxros#

### show isis adjacency

**Output:**
```
Process ID: 0
Interface         System id        State     Lev     Holds       SNPA(802.2)    Pri     MT   NSF       AF       
xxvgei-1/1/0/20   RAW-KSBJB0072... UP        L2      28          PPP            -            Disable   IPv4      
xxvgei-1/1/0/24   RR-KSMTP1445-01Z UP        L2      22          PPP            -            Disable   IPv4      

Process ID: 1
Interface         System id        State     Lev     Holds       SNPA(802.2)    Pri     MT   NSF       AF       
xxvgei-1/1/0/2... RAW-KSBJB0072... UP        L2      30          PPP            -       M    Disable   IPv6      
xxvgei-1/1/0/2... RR-KSMTP1445-01Z UP        L2      22          PPP            -       M    Disable   IPv6     

```

**Help:** execute the command "show isis adjacency"

**Prompt:**
- zte_zxros>
- zte_zxros#

### show mpls traffic-eng tunnels

**Output:**
```

Name: tunnel_1
      (Tunnel1) Destination: 10.10.10.87
  Status:
    Admin: up  Oper: up  Path:  valid  Signalling: connected
    Path option: 1, type explicit name: Tunnel_RAW-XXXXX0056-01Z_to_R-PTABR-01 (Basis for Setup)
    Path option: 2, type explicit name: Tunnel_RAW-XXXXX0056-01Z_to_R-PTABR-01-hsb
    Pre-setup Path: none
    Actual Bandwidth:                N/A      Tunnel Utilize:              N/A
    Actual Bandwidth In:             N/A      Tunnel Utilize In:           N/A
    Hot-standby protection:
      protect option: 1, type dynamic (Basis for Setup)
    PCE-authorized: NO
    PCE-auto-init tunnel: NO
    Active-MPLS-binding-SID: none
  Config Parameters:
    Resv-Style: SE
    Metric Type: IGP (default)   Upper Limit: 4294967295
    Hop Prior: disabled         Upper Limit: -
    Hot Hop Limit: -
    Record-Route: enabled
    Facility Fast-reroute: disabled
    Detour Fast-reroute: disabled
    Protect Coexist: disabled
    Protect Nest: disabled
    Main LSP Fast-reroute Block: disabled
    Bandwidth Protection: disabled
    Hot-standby-lsp Fast-reroute: disabled
    E2E: disabled
    BFD: disabled
    Policy Class: N/A
    Track Name: 
    Auto-reoptimize: enabled        Time remaining:(3600/1198)
    Hot-standby-lsp Auto-reoptimize: enabled        Time remaining:(3600/1193)
    Reference Hot-standby: enabled
    Tunnel-Status: enabled
    Bandwidth: 0 kbps (Global) Priority: 7  7
    CBS: 0 byte  EIR: 0 kbps  EBS: 0 byte
    Main affinity:
      Exclude-any: None
      Include-any: None
      Include-all: None
    HSB affinity:
      Exclude-any: None
      Include-any: None
      Include-all: None
    FRR affinity:
      Exclude-any: None
      Include-any: None
      Include-all: None
    AutoRoute: disabled
    AUTO-BW: disabled
    Forwarding-adjacency: disabled
    Co-routed Bidirect: disabled
    Associated Bidirect: disabled
    Rate-limit: disabled
    Crankback: disabled
    Soft Preemption: disabled
    Soft Preemption Status: not pending
    Addresses of preempting links: 0.0.0.0
    Graceful shutdown address: NULL
    Without-CSPF: disabled
    Ultralimit discard: disabled
    PCEP slave name: 
    PCE-initiate: disabled
    Advertise None-null: disabled
  InLabel: -
  OutLabel: smartgroup2, 282291
  LSP recoverd from GR: NO
  RSVP Signalling Info :
    Src 10.10.10.1, Dst 10.10.10.87, Tun-ID 1, Tun-Instance 335
    RSVP Path Info:
      Explicit Route: 10.10.10.22 10.10.10.23 10.10.10.194
                      10.10.10.195 10.10.10.87
      Exclude Route: NULL
      Record Route: NULL
      Tspec: ave rate= 0 kb, burst= 1000 byte, peak rate= 0 kb
    RSVP Resv Info:
      Record Route: 10.10.10.23(282291) 10.10.10.195(3)
      Fspec: ave rate= 0 kb, burst= 1000 byte, peak rate= 0 kb

  History:
    Tunnel:
    Time Since Created: 3 days, 17 hours, 21 minutes, 25 seconds
    Time Since Up     : 3 days, 17 hours, 18 minutes, 17 seconds
    Prior LSP(main): path option 1
    Current LSP: Uptime:2 days, 1 hours, 49 minutes, 41 seconds
    Last LSP Error Information:
      Cspf failed(lspid:762,errcode:1,errvalue:44).
      Cspf failed(lspid:761,errcode:1,errvalue:44).
      Cspf failed(lspid:760,errcode:1,errvalue:44).

Name: tunnel_1
      (hot)(Tunnel1) Destination: 10.10.10.87
  Status:
    Signalling: up
    Actual Bandwidth:                N/A      Tunnel Utilize:              N/A
    Actual Bandwidth In:             N/A      Tunnel Utilize In:           N/A
    Hot-standby protection:
    PCE-authorized: NO
    PCE-auto-init tunnel: NO
    Active-MPLS-binding-SID: none
  Config Parameters:
    BFD: disabled
    Hot-standby-lsp Fast-reroute: disabled
    Hot-standby-lsp Auto-reoptimize: enabled        Time remaining:(3600/1192)
    Bandwidth: 0 kbps (Global) Priority: 7  7
    CBS: 0 byte  EIR: 0 kbps  EBS: 0 byte
    Main affinity:
      Exclude-any: None
      Include-any: None
      Include-all: None
    HSB affinity:
      Exclude-any: None
      Include-any: None
      Include-all: None
    FRR affinity:
      Exclude-any: None
      Include-any: None
      Include-all: None
    AutoRoute: disabled
    AUTO-BW: disabled
    Forwarding-adjacency: disabled
    Co-routed Bidirect: disabled
    Associated Bidirect: disabled
    Rate-limit: disabled
    Crankback: disabled
    Soft Preemption: disabled
    Soft Preemption Status: not pending
    Addresses of preempting links: 0.0.0.0
    Graceful shutdown address: NULL
    Without-CSPF: disabled
    Ultralimit discard: disabled
    PCEP slave name: 
    PCE-initiate: disabled
    Advertise None-null: disabled
  InLabel: -
  OutLabel: smartgroup1, 475765
  LSP recoverd from GR: NO
  RSVP Signalling Info :
    Src 10.10.10.1, Dst 10.10.10.87, Tun-ID 1, Tun-Instance 336
    RSVP Path Info:
      Explicit Route: 10.10.10.21 10.10.10.20 10.10.10.24
                      10.10.10.25 10.10.10.87
      Exclude Route: NULL
      Record Route: NULL
      Tspec: ave rate= 0 kb, burst= 1000 byte, peak rate= 0 kb
    RSVP Resv Info:
      Record Route: 10.10.10.10(475765) 10.10.10.20(475765)
                    10.10.10.25(3)
      Fspec: ave rate= 0 kb, burst= 1000 byte, peak rate= 0 kb

  History:
    Tunnel:
    Time Since Created: 3 days, 17 hours, 21 minutes, 26 seconds
    Time Since Up     : 3 days, 17 hours, 18 minutes, 18 seconds
    Prior LSP(HSB): path option 1
    Current LSP: Uptime:2 days, 1 hours, 49 minutes, 42 seconds
    Last LSP Error Information:
      Cspf failed(lspid:762,errcode:1,errvalue:44).
      Cspf failed(lspid:761,errcode:1,errvalue:44).
      Cspf failed(lspid:760,errcode:1,errvalue:44).

Name: tunnel_2
      (Tunnel2) Destination: 10.10.10.117
  Status:
    Admin: up  Oper: up  Path:  valid  Signalling: connected
    Path option: 1, type explicit name: Tunnel_RAW-XXXXX0056-01Z_to_AG-PTPMK-01 (Basis for Setup)
    Path option: 2, type explicit name: Tunnel_RAW-XXXXX0056-01Z_to_AG-PTPMK-01-hsb
    Pre-setup Path: none
    Actual Bandwidth:                N/A      Tunnel Utilize:              N/A
    Actual Bandwidth In:             N/A      Tunnel Utilize In:           N/A
    Hot-standby protection:
      protect option: 1, type dynamic (Basis for Setup)
    PCE-authorized: NO
    PCE-auto-init tunnel: NO
    Active-MPLS-binding-SID: none
  Config Parameters:
    Resv-Style: SE
    Metric Type: IGP (default)   Upper Limit: 4294967295
    Hop Prior: disabled         Upper Limit: -
    Hot Hop Limit: -
    Record-Route: enabled
    Facility Fast-reroute: disabled
    Detour Fast-reroute: disabled
    Protect Coexist: disabled
    Protect Nest: disabled
    Main LSP Fast-reroute Block: disabled
    Bandwidth Protection: disabled
    Hot-standby-lsp Fast-reroute: disabled
    E2E: disabled
    BFD: disabled
    Policy Class: N/A
    Track Name: 
    Auto-reoptimize: enabled        Time remaining:(3600/1197)
    Hot-standby-lsp Auto-reoptimize: enabled        Time remaining:(3600/1192)
    Reference Hot-standby: enabled
    Tunnel-Status: enabled
    Bandwidth: 0 kbps (Global) Priority: 7  7
    CBS: 0 byte  EIR: 0 kbps  EBS: 0 byte
    Main affinity:
      Exclude-any: None
      Include-any: None
      Include-all: None
    HSB affinity:
      Exclude-any: None
      Include-any: None
      Include-all: None
    FRR affinity:
      Exclude-any: None
      Include-any: None
      Include-all: None
    AutoRoute: disabled
    AUTO-BW: disabled
    Forwarding-adjacency: disabled
    Co-routed Bidirect: disabled
    Associated Bidirect: disabled
    Rate-limit: disabled
    Crankback: disabled
    Soft Preemption: disabled
    Soft Preemption Status: not pending
    Addresses of preempting links: 0.0.0.0
    Graceful shutdown address: NULL
    Without-CSPF: disabled
    Ultralimit discard: disabled
    PCEP slave name: 
    PCE-initiate: disabled
    Advertise None-null: disabled
  InLabel: -
  OutLabel: smartgroup2, 3
  LSP recoverd from GR: NO
  RSVP Signalling Info :
    Src 10.10.10.1, Dst 10.10.10.117, Tun-ID 2, Tun-Instance 336
    RSVP Path Info:
      Explicit Route: 10.10.10.22 10.10.10.23 10.10.10.117
      Exclude Route: NULL
      Record Route: NULL
      Tspec: ave rate= 0 kb, burst= 1000 byte, peak rate= 0 kb
    RSVP Resv Info:
      Record Route: 10.10.10.23(3)
      Fspec: ave rate= 0 kb, burst= 1000 byte, peak rate= 0 kb

  History:
    Tunnel:
    Time Since Created: 3 days, 17 hours, 21 minutes, 26 seconds
    Time Since Up     : 2 days, 1 hours, 52 minutes, 11 seconds
    Prior LSP(main): path option 1
    Current LSP: Uptime:2 days, 1 hours, 50 minutes, 34 seconds
    Last LSP Error Information:
      Cspf failed(lspid:765,errcode:1,errvalue:44).
      Cspf failed(lspid:764,errcode:1,errvalue:44).
      Cspf failed(lspid:763,errcode:1,errvalue:44).

Name: tunnel_2
      (hot)(Tunnel2) Destination: 10.10.10.117
  Status:
    Signalling: up
    Actual Bandwidth:                N/A      Tunnel Utilize:              N/A
    Actual Bandwidth In:             N/A      Tunnel Utilize In:           N/A
    Hot-standby protection:
    PCE-authorized: NO
    PCE-auto-init tunnel: NO
    Active-MPLS-binding-SID: none
  Config Parameters:
    BFD: disabled
    Hot-standby-lsp Fast-reroute: disabled
    Hot-standby-lsp Auto-reoptimize: enabled        Time remaining:(3600/1192)
    Bandwidth: 0 kbps (Global) Priority: 7  7
    CBS: 0 byte  EIR: 0 kbps  EBS: 0 byte
    Main affinity:
      Exclude-any: None
      Include-any: None
      Include-all: None
    HSB affinity:
      Exclude-any: None
      Include-any: None
      Include-all: None
    FRR affinity:
      Exclude-any: None
      Include-any: None
      Include-all: None
    AutoRoute: disabled
    AUTO-BW: disabled
    Forwarding-adjacency: disabled
    Co-routed Bidirect: disabled
    Associated Bidirect: disabled
    Rate-limit: disabled
    Crankback: disabled
    Soft Preemption: disabled
    Soft Preemption Status: not pending
    Addresses of preempting links: 0.0.0.0
    Graceful shutdown address: NULL
    Without-CSPF: disabled
    Ultralimit discard: disabled
    PCEP slave name: 
    PCE-initiate: disabled
    Advertise None-null: disabled
  InLabel: -
  OutLabel: smartgroup1, 475764
  LSP recoverd from GR: NO
  RSVP Signalling Info :
    Src 10.10.10.1, Dst 10.10.10.117, Tun-ID 2, Tun-Instance 337
    RSVP Path Info:
      Explicit Route: 10.10.10.21 10.10.10.20 10.10.10.24
                      10.10.10.25 10.10.10.195 10.10.10.194
                      10.10.10.117
      Exclude Route: NULL
      Record Route: NULL
      Tspec: ave rate= 0 kb, burst= 1000 byte, peak rate= 0 kb
    RSVP Resv Info:
      Record Route: 10.10.10.10(475764) 10.10.10.20(475764)
                    10.10.10.25(269025) 10.10.10.194(3)
      Fspec: ave rate= 0 kb, burst= 1000 byte, peak rate= 0 kb

  History:
    Tunnel:
    Time Since Created: 3 days, 17 hours, 21 minutes, 26 seconds
    Time Since Up     : 2 days, 1 hours, 52 minutes, 11 seconds
    Prior LSP(HSB): path option 1
    Current LSP: Uptime:2 days, 1 hours, 50 minutes, 33 seconds
    Last LSP Error Information:
      Cspf failed(lspid:765,errcode:1,errvalue:44).
      Cspf failed(lspid:764,errcode:1,errvalue:44).
      Cspf failed(lspid:763,errcode:1,errvalue:44).

Name: tunnel_1
      (remote)(Tunnel1) Destination: 10.10.10.87
  Status:
    Signalling: up
  RSVP Signalling Info :
    InLabel: smartgroup1, 205844
    OutLabel: smartgroup2, 282288
  LSP recoverd from GR: NO
    Src 10.10.10.10, Dst 10.10.10.87, Tun-ID 1, Tun-Instance 35831
    RSVP Path Info:
      Explicit Route: 10.10.10.21 10.10.10.22 10.10.10.23
                      10.10.10.194 10.10.10.195 10.10.10.87
      Exclude Route: NULL
      Record Route: 10.10.10.10 10.10.10.20
      Tspec: ave rate= 0 kb, burst= 1000 byte, peak rate= 0 kb
      Affinity(Bit position):
        Exclude-any: None
        Include-any: None
        Include-all: None
    RSVP Resv Info:
      Record Route: 10.10.10.23(282288) 10.10.10.195(3)
      Fspec: ave rate= 0 kb, burst= 1000 byte, peak rate= 0 kb

  History:
    Tunnel:
    Time Since Created: 2 days, 1 hours, 50 minutes, 45 seconds
    Current LSP: Uptime:2 days, 1 hours, 50 minutes, 41 seconds

Name: tunnel_2
      (remote)(Tunnel2) Destination: 10.10.10.117
  Status:
    Signalling: up
  RSVP Signalling Info :
    InLabel: smartgroup1, 205845
    OutLabel: smartgroup2, 3
  LSP recoverd from GR: NO
    Src 10.10.10.10, Dst 10.10.10.117, Tun-ID 2, Tun-Instance 35956
    RSVP Path Info:
      Explicit Route: 10.10.10.21 10.10.10.22 10.10.10.23
                      10.10.10.117
      Exclude Route: NULL
      Record Route: 10.10.10.10 10.10.10.20
      Tspec: ave rate= 0 kb, burst= 1000 byte, peak rate= 0 kb
      Affinity(Bit position):
        Exclude-any: None
        Include-any: None
        Include-all: None
    RSVP Resv Info:
      Record Route: 10.10.10.23(3)
      Fspec: ave rate= 0 kb, burst= 1000 byte, peak rate= 0 kb

  History:
    Tunnel:
    Time Since Created: 2 days, 1 hours, 49 minutes, 14 seconds
    Current LSP: Uptime:2 days, 1 hours, 49 minutes, 13 seconds

Name: tunnel_101
      (remote)(Tunnel101) Destination: 10.169.120.220
  Status:
    Signalling: up
  RSVP Signalling Info :
    InLabel: xxvgei-1/1/0/20, 205926
    OutLabel: smartgroup2, 283792
  LSP recoverd from GR: NO
    Src 10.10.10.4, Dst 10.169.120.220, Tun-ID 101, Tun-Instance 24849
    RSVP Path Info:
      Explicit Route: 10.10.10.2 10.10.10.22 10.10.10.23
                      10.10.10.194 10.10.10.195 10.10.10.57
                      10.10.10.56 10.169.120.220
      Exclude Route: NULL
      Record Route: 10.10.10.2 10.10.10.3 10.10.10.3
                    10.10.10.5 10.10.10.4 10.10.10.7
      Tspec: ave rate= 0 kb, burst= 1000 byte, peak rate= 0 kb
      Affinity(Bit position):
        Exclude-any: None
        Include-any: None
        Include-all: None
    RSVP Resv Info:
      Record Route: 10.10.10.23(283792) 10.10.10.195(270881)
                    10.10.10.56(3)
      Fspec: ave rate= 0 kb, burst= 1000 byte, peak rate= 0 kb

  History:
    Tunnel:
    Time Since Created: 0 days, 18 hours, 6 minutes, 44 seconds
    Current LSP: Uptime:0 days, 18 hours, 6 minutes, 43 seconds

Name: AG-PTPMK-01-to-RAW-XXXXX0056-01Z
      (remote)(Tunnel8011) Destination: 10.10.10.1
  Status:
    Signalling: up
  RSVP Signalling Info :
    InLabel: smartgroup2, 3
    OutLabel: -
  LSP recoverd from GR: NO
    Src 10.10.10.117, Dst 10.10.10.1, Tun-ID 8011, Tun-Instance 103
    RSVP Path Info:
      Explicit Route: NULL
      Exclude Route: NULL
      Record Route: 10.10.10.23
      Tspec: ave rate= 0 kb, burst= 0 byte, peak rate= inf kb
      Affinity(Bit position):
        Exclude-any: None
        Include-any: None
        Include-all: None
    RSVP Resv Info:
      Record Route: NULL
      Fspec: ave rate= 0 kb, burst= 0 byte, peak rate= inf kb

  History:
    Tunnel:
    Time Since Created: 2 days, 1 hours, 40 minutes, 56 seconds
    Current LSP: Uptime:2 days, 1 hours, 40 minutes, 56 seconds

Name: Bypass->10.10.10.78->10.10.10.242
      (remote)(Tunnel14243) Destination: 10.10.10.73
  Status:
    Signalling: up
  RSVP Signalling Info :
    InLabel: smartgroup1, 205843
    OutLabel: smartgroup2, 282252
  LSP recoverd from GR: NO
    Src 10.10.10.87, Dst 10.10.10.73, Tun-ID 14243, Tun-Instance 1
    RSVP Path Info:
      Explicit Route: 10.10.10.21 10.10.10.22 10.10.10.23
                      10.10.10.246 10.10.10.249
      Exclude Route: NULL
      Record Route: 10.10.10.10 10.10.10.20 10.10.10.25
      Tspec: ave rate= 0 kb, burst= 0 byte, peak rate= inf kb
      Affinity(Bit position):
        Exclude-any: None
        Include-any: None
        Include-all: None
    RSVP Resv Info:
      Record Route: 10.10.10.23(282252) 10.10.10.74(397)
                    10.10.10.250(397) 10.10.10.73(3)
                    10.10.10.249(3)
      Fspec: ave rate= 0 kb, burst= 0 byte, peak rate= inf kb

  History:
    Tunnel:
    Time Since Created: 2 days, 1 hours, 51 minutes, 26 seconds
    Current LSP: Uptime:2 days, 1 hours, 51 minutes, 23 seconds

Name: R-PTABR-01-to-RAW-XXXXX0056-01Z
      (remote)(Tunnel53991) Destination: 10.10.10.1
  Status:
    Signalling: up
  RSVP Signalling Info :
    InLabel: smartgroup2, 3
    OutLabel: -
  LSP recoverd from GR: NO
    Src 10.10.10.87, Dst 10.10.10.1, Tun-ID 53991, Tun-Instance 80
    RSVP Path Info:
      Explicit Route: NULL
      Exclude Route: NULL
      Record Route: 10.10.10.23 10.10.10.195
      Tspec: ave rate= 0 kb, burst= 0 byte, peak rate= inf kb
      Affinity(Bit position):
        Exclude-any: None
        Include-any: None
        Include-all: None
    RSVP Resv Info:
      Record Route: NULL
      Fspec: ave rate= 0 kb, burst= 0 byte, peak rate= inf kb

  History:
    Tunnel:
    Time Since Created: 2 days, 1 hours, 51 minutes, 13 seconds
    Current LSP: Uptime:2 days, 1 hours, 51 minutes, 13 seconds

```

**Help:** execute the command "show mpls traffic-eng tunnels"

**Prompt:**
- zte_zxros>
- zte_zxros#

### show version

**Output:**
```
ZXCTN 6120H-S
ZTE ZXCTN Software, Version: 6120H-S V5.10.00.50, Release software
Copyright (c) 2022 by ZTE Corporation
System image file is <sysdisk0: verset/ZXCTN6120HS_V5.10.00.50B03.set>, file size is 629,753,128 Bytes
System image is loaded from local
System uptime is 23 day(s), 10 hour(s), 59 minute(s)

[SMGD, shelf 1, slot 1]:
Board Name        : SMGD
Description       : 6120H-S System Main Board D
Board License     : LCS
System BaudRate   : 115,200 bps
MPU-1/1/0, MSC:
Bootrom Version :  V5.10.00B21
Soft Version    :  N/A
Creation Date   :  2022/10/20 14:05:00
System Nvram    :  8,192 bytes
System Memory   :  8,192 Mbytes
System Flash    :  0 Mbytes
Uptime is 23 day(s), 10 hour(s), 59 minute(s)

[FAN, shelf 1, slot 2]:
Board Name        : FAN
Description       : Fan Control Board
Board License     : N/A
FCP-1/2/0:
Bootrom Version :  N/A
Soft Version    :  N/A
Creation Date   :  N/A
System Nvram    :  0 bytes
System Memory   :  0 Mbytes
System Flash    :  0 Mbytes
Uptime is N/A

[PW1DC, shelf 1, slot 3]:
Board Name        : PW1DC
Description       : Integrated DC Power Board
Board License     : N/A
PWR-1/3/0:
Bootrom Version :  N/A
Soft Version    :  N/A
Creation Date   :  N/A
System Nvram    :  0 bytes
System Memory   :  0 Mbytes
System Flash    :  0 Mbytes
Uptime is N/A

[PW1DC, shelf 1, slot 4]:
Board Name        : PW1DC
Description       : Integrated DC Power Board
Board License     : N/A
PWR-1/4/0:
Bootrom Version :  N/A
Soft Version    :  N/A
Creation Date   :  N/A
System Nvram    :  0 bytes
System Memory   :  0 Mbytes
System Flash    :  0 Mbytes
Uptime is N/A

```

**Help:** execute the command "show version"

**Prompt:**
- zte_zxros>
- zte_zxros#

### _default_

**Output:**
```
% Invalid input detected
```

**Help:** default output for unknown commands

**Prompt:**
- zte_zxros>
- zte_zxros#

