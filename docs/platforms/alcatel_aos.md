# alcatel_aos


!!! warning
    This is automatically generated. In case of any issues,
    please refer to the source code or, even better,
    open an issue on the GitHub repository. Thanks! 🤗📖
## Commands

### enable

**Output:** None

**Help:** enter enable mode

**Prompt:**
- alcatel_aos>

### ex

**Output:** None

**Help:** exit the terminal

**Prompt:**
- alcatel_aos>
- alcatel_aos#

### show chassis

**Output:**
```
Chassis 1
  Model Name:                    OS6350-P24,
  Description:                   Chassis,
  Part Number:                   000000-00,
  Hardware Revision:             01,
  Serial Number:                 AAA000000000,
  Manufacture Date:              JAN  1 2000,
  Admin Status:                  POWER ON,
  Operational Status:            UP,
  Number Of Resets:              1
  MAC Address:                   00:00:00:00:00:00,

Chassis 2
  Model Name:                    OS6350-P24,
  Description:                   6350 24 PORT COPPER GE POE ,
  Part Number:                   000000-00,
  Hardware Revision:             01,
  Serial Number:                 AAA000000000,
  Manufacture Date:              JAN  1 2000,
  Admin Status:                  POWER ON,
  Operational Status:            UP,
  MAC Address:                   00:00:00:00:00:00,
```

**Help:** execute the command "show chassis"

**Prompt:**
- alcatel_aos>
- alcatel_aos#

### show interfaces alias

**Output:**
```
 Chas/
 Slot/     Admin     Link        WTR      WTS       Alias
 Port      Status   Status      (sec)    (msec)
--------+----------+---------+----------+----------+-----------------------
 1/1/1     enable     up      0          0          "This is an example"
 2/1/10    enable     down    0          0          "This_is_an_example"
 2/1/11    enable     down    0          0          "This"
```

**Help:** execute the command "show interfaces alias"

**Prompt:**
- alcatel_aos>
- alcatel_aos#

### show interfaces ethernet

**Output:**
```
Slot/Port  1/1  :
  Operational Status     : up, ""
  Last Time Link Changed : MON JAN 08 20:38:47 ,
  Number of Status Change: 2,
  Type                   : Ethernet,
  SFP/SFP+/XFP           : Not Present,
  MAC address            : aa:aa:aa:aa:aa:aa,
  BandWidth (Megabits)   :     1000,            Duplex           : Full,
  Autonegotiation        :   1  [ 1000-F 100-F 100-H 10-F 10-H ],
  Long Frame Size(Bytes) : 9216,
  Rx              :
  Bytes Received  :          28902644070, Unicast Frames :             62119123,
  Broadcast Frames:               123797, M-cast Frames  :               358499,
  UnderSize Frames:                    0, OverSize Frames:                    0,
  Lost Frames     :                    0, Error Frames   :                    0,
  CRC Error Frames:                    0, Alignments Err :                    0,
  Tx              :
  Bytes Xmitted   :         274375376582, Unicast Frames :             97599952,
  Broadcast Frames:           1746630116, M-cast Frames  :             87217616,
  UnderSize Frames:                    0, OverSize Frames:                    0,
  Lost Frames     :                    0, Collided Frames:                    0,
  Error Frames    :                    0
Slot/Port  1/2 :
  Operational Status     : down, "Admin-Down"
  Last Time Link Changed : WED JAN 10 10:00:26 ,
  Number of Status Change: 2,
  Type                   : Ethernet,
  SFP/SFP+/XFP           : GBIC_LX,
  MAC address            : bb:bb:bb:bb:bb:bb,
  BandWidth (Megabits)   :     -  ,            Duplex           : -,
  Autonegotiation        :   1  [ 1000-F                       ],
  Long Frame Size(Bytes) : 9216,
  Rx              :
  Bytes Received  :        1602614019301, Unicast Frames :           1423093884,
  Broadcast Frames:            131096783, M-cast Frames  :              9298965,
  UnderSize Frames:                    0, OverSize Frames:                    0,
  Lost Frames     :                    0, Error Frames   :                    0,
  CRC Error Frames:                    0, Alignments Err :                    0,
  Tx              :
  Bytes Xmitted   :         313945899784, Unicast Frames :            702405038,
  Broadcast Frames:                94040, M-cast Frames  :              3193107,
  UnderSize Frames:                    0, OverSize Frames:                    0,
  Lost Frames     :                    0, Collided Frames:                    0,
  Error Frames    :                    0
```

**Help:** execute the command "show interfaces ethernet"

**Prompt:**
- alcatel_aos>
- alcatel_aos#

### show interfaces port

**Output:**
```
Legends: WTR - Wait To Restore
         #   - WTR Timer is Running & Port is in wait-to-restore state
         *   - Permanent Shutdown

Slot/    Admin     Link    Violations  Recovery   Recovery      WTR            Alias
Port     Status   Status                 Time       Max        (sec)
------+----------+---------+----------+----------+----------+----------+-----------------------------------------
 *1/1    enable      up        none           300         10          0 "Hello"
  1/2    enable      down      none           300         10          0 ""
  1/11   enable      down      none           300         10       # 10 ""
  1/17   disable     down      none           300         10          0 ""
  1/23   disable     down      none           300         10          0 ""
  1/25   enable      up        none           300         10          0 ""
  1/26   enable      down      none           300         10          0 ""
  1/28   enable      down      none             0          0          0 ""
```

**Help:** execute the command "show interfaces port"

**Prompt:**
- alcatel_aos>
- alcatel_aos#

### show interfaces status

**Output:**
```
                       DETECTED           CONFIGURED
Slot/ AutoNego  Speed Duplex Hybrid  Speed   Duplex Hybrid  Trap
Port           (Mbps)         Type   (Mbps)         Mode   LinkUpDown
-----+--------+------+------+------+--------+------+------+------
 1/1   Enable   1000   Full    NA      Auto   Auto    NA      -  
 1/2   Enable    -      -      -       Auto   Auto    NA      -  
 1/3   Enable    -      -      -       Auto   Auto    NA      -  
 1/4   Enable    -      -      -       Auto   Auto    NA      -  
 1/5   Enable    -      -      -       Auto   Auto    NA      -  
 1/6   Enable    -      -      -       Auto   Auto    NA      -  
 1/7   Enable    -      -      -       Auto   Auto    NA      -  
 1/8   Enable    -      -      -       Auto   Auto    NA      -  
 1/9   Enable    -      -      -       Auto   Auto    NA      -  
 1/10  Enable    -      -      -       Auto   Auto    NA      -  
 1/11  Enable    -      -      -       Auto   Auto    NA      -  
 1/12  Enable    -      -      -       Auto   Auto    NA      -  
 1/13  Enable    -      -      -       Auto   Auto    NA      -  
 1/14  Enable    -      -      -       Auto   Auto    NA      -  
 1/15  Enable    -      -      -       Auto   Auto    NA      -  
 1/16  Enable    -      -      -       Auto   Auto    NA      -  
 1/17  Enable    -      -      -       Auto   Auto    NA      -  
 1/18  Enable    -      -      -       Auto   Auto    NA      -  
 1/19  Enable    -      -      -       Auto   Auto    NA      -  
 1/20  Enable    -      -      -       Auto   Auto    NA      -  
 1/21  Enable    -      -      -       Auto   Auto    NA      -  
 1/22  Enable    -      -      -       Auto   Auto    NA      -  
 1/23  Enable    -      -      -       Auto   Auto    NA      -  
 1/24  Enable    -      -      -       Auto   Auto    NA      -  
 1/25  Enable   1000   Full    NA       1000  Full    NA      -  
 1/26  Enable    -      -      -        1000  Full    NA      -  

FF - ForcedFiber PF - PreferredFiber  F - Fiber
FC - ForcedCopper PC - PreferredCopper C - Copper
```

**Help:** execute the command "show interfaces status"

**Prompt:**
- alcatel_aos>
- alcatel_aos#

### show linkagg alias

**Output:**
```

                         Admin        Oper     Att/Sel  
Number  Aggregate  Size  state        state      Ports      Name 
-------+----------+----+------------+-------+---------+--------------
   2     Dynamic      2    ENABLED    UP      2  2     LINK_LACP_CORE
  31     Dynamic      8    ENABLED    DOWN    0  0     Created by Auto-Fabric on Mon Oct 6 00:00:00 2000
  32     Dynamic      8    ENABLED    DOWN    0  0     Created by Auto-Fabric on Mon Oct 01 00:00:00 2000
```

**Help:** execute the command "show linkagg alias"

**Prompt:**
- alcatel_aos>
- alcatel_aos#

### show linkagg port

**Output:**
```

Slot/Port Aggregate SNMP Id   Status   Agg  Oper Link Prim
---------+---------+-------+----------+----+----+----+----
   1/1    Dynamic     1000  ATTACHED     1  UP   UP   YES
   1/2    Dynamic     1001  ATTACHED     1  UP   UP   NO 
   1/3    Dynamic     1002  ATTACHED     2  UP   UP   YES
   1/4    Dynamic     1003  ATTACHED     2  UP   UP   NO 
```

**Help:** execute the command "show linkagg port"

**Prompt:**
- alcatel_aos>
- alcatel_aos#

### show lldp remote-system

**Output:**
```
Remote LLDP Agents on Local Slot/Port 1/1:

    Chassis aa:aa:aa:aa:aa:aa, Port bb:bb:bb:bb:bb:bb:
      Remote ID                   = 1,
      Chassis Subtype             = 1 (MAC Address),
      Port Subtype                = 1 (MAC address),
      Port Description            = Alcatel-Lucent Enterprise OAW-AP1201H eth0-4094,
      System Name                 = AP,
      System Description          = Alcatel-Lucent Enterprise OAW-AP1201H 1.0.0.10,
      Capabilities Supported      = Bridge WLAN AP Router Station Only,
      Capabilities Enabled        = Bridge WLAN AP Router,
      Management IP Address       = 1.1.1.1,
      MED Device Type             = Network Connectivity,
      MED Capabilities            = Capabilities | Power via MDI-PD(33),
      MED Extension TLVs Present  = Network Policy| Inventory,
      MED Power Type              = PD Device,
      MED Power Source            = PSE and Local,
      MED Power Priority          = Low,
      MED Power Value             = 25.4 W

Remote LLDP Agents on Local Slot/Port 1/2:

    Chassis aa:aa:aa:aa:aa:aa, Port bb:bb:bb:bb:bb:bb:
      Remote ID                   = 1,
      Chassis Subtype             = 1 (MAC Address),
      Port Subtype                = 1 (MAC address),
      Port Description            = Alcatel-Lucent Enterprise OAW-AP1321 eth1,
      System Name                 = AP,
      System Description          = Alcatel-Lucent Enterprise OAW-AP1321 1.0.0.10,
      Capabilities Supported      = Bridge WLAN AP Router Station Only,
      Capabilities Enabled        = Bridge WLAN AP Router,
      Management IP Address       = 1.1.1.1,
      MED Device Type             = Network Connectivity,
      MED Capabilities            = Capabilities | Power via MDI-PD(33),
      MED Extension TLVs Present  = Network Policy| Inventory,
      MED Power Type              = PD Device,
      MED Power Source            = PSE and Local,
      MED Power Priority          = Low,
      MED Power Value             = 25.4 W,
      Remote port MAC/PHY AutoNeg = Supported Enabled Capability 0x8336,
      Mau Type                    = 1000BaseTFD - Four-pair Category 5 UTP full duplex mode

Remote LLDP Agents on Local Slot/Port 1/3:

    Chassis aa:aa:aa:aa:aa:aa, Port bb:bb:bb:bb:bb:bb:
      Remote ID                   = 1,
      Chassis Subtype             = 1 (MAC Address),
      Port Subtype                = 1 (MAC address),
      Port Description            = Alcatel-Lucent Enterprise OAW-AP1361 eth0,
      System Name                 = AP,
      System Description          = Alcatel-Lucent Enterprise OAW-AP1361 1.0.0.10,
      Capabilities Supported      = Bridge WLAN AP Router Station Only,
      Capabilities Enabled        = Bridge WLAN AP Router,
      Management IP Address       = 1.1.1.1,
      MED Device Type             = Network Connectivity,
      MED Capabilities            = Capabilities | Power via MDI-PD(33),
      MED Extension TLVs Present  = Network Policy| Inventory,
      Remote port MAC/PHY AutoNeg = Supported Enabled Capability 0x8337,
      Mau Type                    = 1000BaseTFD - Four-pair Category 5 UTP full duplex mode

Remote LLDP Agents on Local Slot/Port 1/4:

    Chassis aa:aa:aa:aa:aa:aa, Port 1001:
      Remote ID                   = 123,
      Chassis Subtype             = 1 (MAC Address),
      Port Subtype                = 1 (Locally assigned),
      Port Description            = Alcatel-Lucent OS6860 GNI 1/1/1,
      System Name                 = SW,
      System Description          = (null),
      Capabilities Supported      = Bridge Router,
      Capabilities Enabled        = Bridge Router,
      Management IP Address       = 1.1.1.1

Remote LLDP Agents on Local Slot/Port 1/24:

    Chassis aa:aa:aa:aa:aa:aa, Port GigabitEthernet0/0/47:
      Remote ID                   = 223,
      Chassis Subtype             = 4 (MAC Address),
      Port Subtype                = 5 (Interface name),
      Port Description            = UPLINK,
      System Name                 = super_mega_switch,
      System Description          = S5700-52P-PWR-LI-AC
Huawei Versatile Routing Platform Software
VRP (R) software, Version 1.110 (S5700 A000A000A00AAA000)
Copyright (C) 2000-2001 HUAWEI TECH Co., Ltd.,
      Capabilities Supported      = Bridge Router,
      Capabilities Enabled        = Bridge Router,
      Management IP Address       = 1.1.1.1
      Remote port default vlan    = 2000,
      Vlan ID                     = 1,
      Vlan Name                   = VLAN 0001,
      Protocol vlan Id            = 0 (Flags = 0),
      Remote port MAC/PHY AutoNeg = Supported Enabled Capability 0xa03e,
      Mau Type                    = 1000BaseTFD - Four-pair Category 5 UTP full duplex mode
```

**Help:** execute the command "show lldp remote-system"

**Prompt:**
- alcatel_aos>
- alcatel_aos#

### show mac-address-table

**Output:**
```
Legend: Mac Address: * = address not valid

   Vlan      Mac Address          Type       Protocol    Operation    Interface 
  ------+-------------------+--------------+-----------+------------+-----------
   * 1    aa:aa:aa:aa:aa:aa      permanent         ---      bridging      1/1  
     2    bb:bb:bb:bb:bb:bb        learned         ---      bridging      1/1  
     3    cc:cc:cc:cc:cc:cc        learned         ---      bridging      1/1  
     4    dd:dd:dd:dd:dd:dd        learned         ---      bridging      1/1
 * 999    ee:ee:ee:ee:ee:ee      permanent           0      bridging      1/11

Total number of Valid MAC addresses above = 4
```

**Help:** execute the command "show mac-address-table"

**Prompt:**
- alcatel_aos>
- alcatel_aos#

### show port-security

**Output:**
```

Legend: Mac Address: * = Duplicate Static
        Mac Address: # = Pseudo Static


Port:  1/11
 Operation Mode   :                ENABLED,
 Max MAC bridged  :                      1,
 Trap Threshold   :               DISABLED,
 Max MAC filtered :                      5,
 Violation        :               RESTRICT,
 Violating MAC    :                   NULL

 MAC Address        VLAN   TYPE
-------------------+------+------------
 aa:aa:aa:aa:aa:aa    10   STATIC

 
Legend: Mac Address: * = Duplicate Static
        Mac Address: # = Pseudo Static


Port:  1/12
 Operation Mode   :                ENABLED,
 Max MAC bridged  :                      1,
 Trap Threshold   :               DISABLED,
 Max MAC filtered :                      5,
 Violation        :               RESTRICT,
 Violating MAC    :                   NULL

 MAC Address        VLAN   TYPE
-------------------+------+------------
 aa:aa:aa:aa:aa:bb    10   STATIC
```

**Help:** execute the command "show port-security"

**Prompt:**
- alcatel_aos>
- alcatel_aos#

### show system

**Output:**
```
System:
  Description:  Alcatel-Lucent Enterprise OS6350-P24 6.7.1.001.R01 GA, January 01, 2000.,
  Object ID:    0.0.0.0.0.0.0000.000.0.0.0.0.00.0.0,
  Up Time:      22 days 2 hours 20 minutes and 20 seconds,
  Contact:      Alcatel-Lucent Enterprise, https://www.al-enterprise.com,
  Name:         SWA_0001,
  Location:     Espoo - Finland,
  Services:     2,
  Date & Time:  MON JAN 01 2001  00:00:00 (CET)

Flash Space:
    Primary CMM:
      Available (bytes):  39243776,
      Comments         :  None
```

**Help:** execute the command "show system"

**Prompt:**
- alcatel_aos>
- alcatel_aos#

### show vlan

**Output:**
```
                              stree                 mble   src        
 vlan  type  admin   oper   1x1   flat   auth   ip   tag   lrn   name
-----+-----+------+------+------+------+----+-----+-----+------+----------
   1    std   on     on     on    on     off   off   off     on   VLAN 1                          
  10    std   on    off     on    on     off   off   off     on   name with spaces                
 100    std   on     on     on    on     off    on   off     on   name-with-dashes                  
1000   gvrp   on     on     on    on     off    on   off     on   namewithoutnothing                  
```

**Help:** execute the command "show vlan"

**Prompt:**
- alcatel_aos>
- alcatel_aos#

### show vlan port

**Output:**
```
  vlan       port         type         status
--------+------------+------------+--------------
  1         1/1/23       default    inactive
  1         1/1/25       qtagged    forwarding
```

**Help:** execute the command "show vlan port"

**Prompt:**
- alcatel_aos>
- alcatel_aos#

