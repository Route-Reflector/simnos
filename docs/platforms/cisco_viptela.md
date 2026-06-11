# cisco_viptela


!!! warning
    This is automatically generated. In case of any issues,
    please refer to the source code or, even better,
    open an issue on the GitHub repository. Thanks! 🤗📖
## Commands

### _default_

**Output:**
```
% Invalid input detected
```

**Help:** default output for unknown commands

**Prompt:**

### enable

**Output:** None

**Help:** enter enable mode

**Prompt:**
- cisco_viptela>

### show arp

**Output:**
```
VPN  IF NAME  IP            MAC                STATE    IDLE TIMER  UPTIME
-----------------------------------------------------------------------------
0    eth0  10.10.20.70   00:50:56:bf:a0:d3  dynamic  0:00:11:33  0:00:08:28
```

**Help:** execute the command "show arp"

**Prompt:**
- cisco_viptela>
- cisco_viptela#

### show control connections

**Output:**
```
                                                                                             PEER                                          PEER                                          
      PEER    PEER PEER            SITE       DOMAIN PEER                                    PRIV  PEER                                    PUB                                           
INDEX TYPE    PROT SYSTEM IP       ID         ID     PRIVATE IP                              PORT  PUBLIC IP                               PORT  ORGANIZATION            REMOTE COLOR     STATE UPTIME     
---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
0     vedge   dtls 172.37.205.6    65123      1      192.168.2.14                            12386 80.169.94.206                           12386 network-SDWAN             gold            up     42:01:48:26
0     vedge   dtls 172.37.205.6    65123      1      212.145.174.58                          12386 212.215.174.58                          12386 network-SDWAN             silver          up     25:18:09:32
0     vedge   dtls 10.7.205.1      65221      1      10.1.242.4                              12346 21.0.118.48                             12346 network-SDWAN             gold            up     110:18:19:05
0     vedge   dtls 10.8.205.6      65222      1      10.2.242.5                              12346 30.107.33.32                            12346 network-SDWAN             silver          up     110:18:18:49
0     vsmart  dtls 10.94.3.250     222        1      10.94.3.70                              12346 50.238.90.220                           12346 network-SDWAN             default         up     59:12:30:33
0     vbond   dtls 10.94.3.249     0          0      20.203.233.139                          12346 43.203.233.139                          12346 network-SDWAN             default         up     110:18:19:19
0     vbond   dtls 10.94.2.249     0          0      20.214.51.185                           12346 45.214.51.185                           12346 network-SDWAN             default         up     110:18:19:19
0     vmanage dtls 10.94.2.248     120        0      10.94.2.70                              12346 56.117.133.18                           12346 network-SDWAN             default         up     139:23:37:04
1     vedge   dtls 10.94.2.247     125        1      10.94.2.73                              12386 51.145.96.212                           12386 network-SDWAN             gold            up     110:18:04:58
1     vedge   dtls 10.8.205.1      65222      1      10.2.242.4                              12346 78.117.13.0                             12346 network-SDWAN             gold            up     110:18:19:19
1     vbond   dtls 10.94.3.249     0          0      20.223.213.139                          12346 90.223.213.139                          12346 network-SDWAN             default         up     110:18:19:24
1     vbond   dtls 10.94.2.249     0          0      20.254.81.185                           12346 33.254.54.185                           12346 network-SDWAN             default         up     110:18:19:24
2     vedge   dtls 172.37.205.1    65123      1      192.158.1.9                             12386 222.115.191.254                         12386 network-SDWAN             silver          up     25:18:09:48
2     vedge   dtls 172.37.205.1    65123      1      217.101.187.218                         12346 247.121.187.218                         12346 network-SDWAN             gold            up     42:01:48:24
2     vedge   dtls 172.31.127.1    65124      1      192.168.11.9                            12406 183.81.133.71                           12406 network-SDWAN             silver          up     51:02:00:29
2     vedge   dtls 172.31.127.6    65124      1      185.81.153.72                           12386 182.89.193.72                           12386 network-SDWAN             silver          up     51:02:00:34
2     vedge   dtls 172.31.127.6    65124      1      192.138.17.14                           12426 222.121.2.79                            12426 network-SDWAN             gold            up     103:02:15:50
2     vedge   dtls 172.31.127.1    65124      1      213.86.117.170                          12346 203.86.147.170                          12346 network-SDWAN             gold            up     110:18:19:14
```

**Help:** execute the command "show control connections"

**Prompt:**
- cisco_viptela>
- cisco_viptela#

### show interface

**Output:**
```

                                        IF      IF      IF                                                                TCP
                  AF                    ADMIN   OPER    TRACKER  ENCAP                                     SPEED          MSS                 RX       TX
VPN  INTERFACE    TYPE  IP ADDRESS      STATUS  STATUS  STATUS   TYPE   PORT TYPE  MTU  HWADDR             MBPS   DUPLEX  ADJUST  UPTIME      PACKETS  PACKETS
----------------------------------------------------------------------------------------------------------------------------------------------------------------
0    eth0         ipv4  10.10.20.90/24  Up      Up      -        null   transport  -    00:50:56:bf:8a:02  1000   full    -       0:00:18:51  24175    21348
0    eth1         ipv4  -               Down    Down    -        -      -          -    00:50:56:bf:f2:1a  1000   full    -       -           -        -
0    eth2         ipv4  -               Down    Down    -        -      -          -    00:50:56:bf:47:34  1000   full    -       -           -        -
0    system       ipv4  10.10.1.1/32    Up      Up      -        null   loopback   -    -                  1000   full    -       0:00:21:54  0        0
0    docker0      ipv4  -               Down    Down    -        -      -          -    02:42:39:23:37:dd  1000   full    -       -           -        -
0    cbr-vmanage  ipv4  -               Down    Up      -        -      -          -    02:42:d6:c0:0b:66  1000   full    -       -           -        -
```

**Help:** execute the command "show interface"

**Prompt:**
- cisco_viptela>
- cisco_viptela#

### show omp peers

**Output:**
```
R -> routes received
I -> routes installed
S -> routes sent

                         DOMAIN    OVERLAY   SITE
PEER             TYPE    ID        ID        ID        STATE    UPTIME           R/I/S
------------------------------------------------------------------------------------------
10.7.55.1       vedge   1         1         65251     up       17:00:21:34      30/0/542
10.7.55.6       vedge   1         1         65251     up       17:00:21:21      30/0/542
10.8.55.1       vedge   1         1         65252     up       20:00:39:42      30/0/542
10.8.55.6       vedge   1         1         65252     up       20:00:39:37      30/0/542
10.51.55.1      vedge   1         1         65241     up       24:00:43:10      32/0/334
10.94.2.247      vedge   1         1         125       up       108:21:17:49     6/0/301
10.94.3.247      vedge   1         1         225       up       39:05:26:24      6/0/301
10.94.3.250      vsmart  1         1         222       up       108:21:31:58     1031/0/1031
192.168.255.1    vedge   1         1         65153     up       108:21:32:16     201/0/732
192.168.255.6    vedge   1         1         65153     up       108:21:31:55     219/0/714
192.168.127.1    vedge   1         1         65154     up       108:21:32:09     180/0/726
192.168.127.6    vedge   1         1         65154     up       108:21:32:15     183/0/723
```

**Help:** execute the command "show omp peers"

**Prompt:**
- cisco_viptela>
- cisco_viptela#

