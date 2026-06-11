# huawei_smartax


!!! warning
    This is automatically generated. In case of any issues,
    please refer to the source code or, even better,
    open an issue on the GitHub repository. Thanks! 🤗📖
## Commands

### display board

**Output:**
```
  -------------------------------------------------------------------------
  SlotID  BoardName  Status          SubType0 SubType1    Online/Offline
  -------------------------------------------------------------------------
  0       A123ABCD   Normal                           
  1     
  2       A123ABCDE  Normal                           
  3       A123ABCDE  Active_normal   CPCF             
  4       A123ABCDE  Standby_failed  CPCF                 Offline  
  5     
  -------------------------------------------------------------------------
```

**Help:** execute the command "display board"

**Prompt:**
- huawei_smartax>
- huawei_smartax#

### display board serial-number

**Output:**
```
  -------------------------------------------------------------------------
  Solt ID        Board Name         Serial Number 
  -------------------------------------------------------------------------
  0              A123ABCD           123ABC45D6789012                
  1                                                                 
  2              A123ABCDE          123ABC45D6789012                
  3              A123ABCDE          123456789123                    
  4              A123ABCDE          --                              
  5                                                                 
  -------------------------------------------------------------------------
```

**Help:** execute the command "display board serial-number"

**Prompt:**
- huawei_smartax>
- huawei_smartax#

### display cpu

**Output:**
```
  CPU occupancy: 17%
```

**Help:** execute the command "display cpu"

**Prompt:**
- huawei_smartax>
- huawei_smartax#

### display location

**Output:**
```
  -----------------------------------------------------------------------
   SRV-P BUNDLE TYPE MAC            MAC TYPE F /S /P   VPI  VCI   VLAN ID
   INDEX INDEX
  -----------------------------------------------------------------------
      99     -  gpon aaaa-aaaa-aaaa dynamic  0 /1 /0   0    1           1
  -----------------------------------------------------------------------
  Note: F--Frame, S--Slot, P--Port, F/S/P indicates PW Index for PW,
        A--The MAC address is learned or configured on the aggregation port,
        VPI indicates ONT ID for PON, VCI indicates GEM index for GPON,
        v/e--vlan/encap, pritag--priority-tagged,
        ppp--pppoe, ip--ipoe, ip4--ipv4oe, ip6--ipv6oe
```

**Help:** execute the command "display location"

**Prompt:**
- huawei_smartax>
- huawei_smartax#

### display location aaaa-aaaa-aaaa ont

**Output:**
```
{ <cr>||<K> }:

  Command:
          display location aaaa-aaaa-aaaa ont
  It will take several minutes, please wait or press CTRL_C to break
  Are you sure to query MAC address location ? (y/n)[n]:y
  ----------------------------------------------------------------------
  MAC             MAC TYPE  F/S/P    ONT ID  Port ID  Port Type  VLAN
  ----------------------------------------------------------------------
  aaaa-aaaa-aaaa  DYNAMIC   0/ 1/0        0        1  ETH           1
  ----------------------------------------------------------------------
```

**Help:** execute the command "display location aaaa-aaaa-aaaa ont"

**Prompt:**
- huawei_smartax>
- huawei_smartax#

### display mac-address

**Output:**
```
  It will take some time, please wait...
  -----------------------------------------------------------------------
   SRV-P BUNDLE TYPE MAC            MAC TYPE F /S /P   VPI  VCI   VLAN ID
   INDEX INDEX
  -----------------------------------------------------------------------
       1     -  gpon aaaa-aaaa-aaaa static   0 /1 /0   1    1           1
       -     -  eth  aaaa-aaaa-aaaa dynamic  0 /1 /1   -    -           1
       -     -  eth  aaaa-aaaa-aaaa dynamic  0 /1 /1   -    -           1
       -     -  eth  aaaa-aaaa-aaaa dynamic  0 /1 /1   -    -           1
       -     -  eth  aaaa-aaaa-aaaa dynamic  0 /1 /1   -    -           1
       -     -  eth  aaaa-aaaa-aaaa dynamic  0 /1 /1   -    -           1
       -     -  eth  aaaa-aaaa-aaaa dynamic  0 /1 /1   -    -           1
       -     -  eth  aaaa-aaaa-aaaa dynamic  0 /1 /1   -    -           1
       -     -  eth  aaaa-aaaa-aaaa dynamic  0 /1 /1   -    -           1
       -     -  eth  aaaa-aaaa-aaaa dynamic  0 /1 /1   -    -           1
  -----------------------------------------------------------------------
  Total: 10
  Note: F--Frame, S--Slot, P--Port, F/S/P indicates PW Index for PW,
        A--The MAC address is learned or configured on the aggregation 
port,
        VPI indicates ONT ID for PON, VCI indicates GEM index for GPON,
        v/e--vlan/encap, pritag--priority-tagged,
        ppp--pppoe, ip--ipoe, ip4--ipv4oe, ip6--ipv6oe
```

**Help:** execute the command "display mac-address"

**Prompt:**
- huawei_smartax>
- huawei_smartax#

### display mac-address ont 0 1 2 0

**Output:**
```
 ---------------------------------------------------------------
 F/S/P   ONTID    ONT        ONT       MAC-ADDRESS        VLAN
                   port-type  port-ID
 ---------------------------------------------------------------
 0/ 2/6      2    ETH              1   805e-0c5c-4277       80
 0/ 2/6      2    ETH              1   84a9-3845-d603     1003
 0/ 2/6      2    ETH              2   0026-73f9-5a63     1003 
 ---------------------------------------------------------------
 Total: 3
```

**Help:** execute the command "display mac-address ont 0 1 2 0"

**Prompt:**
- huawei_smartax>
- huawei_smartax#

### display mem

**Output:**
```
  Memory occupancy: 79%
```

**Help:** execute the command "display mem"

**Prompt:**
- huawei_smartax>
- huawei_smartax#

### display ont-lineprofile gpon all

**Output:**
```
  ------------------------------------------------------------------------------
  Profile-ID  Profile-name                                Binding times
  ------------------------------------------------------------------------------
  0           line-profile_default_0                      0           
  429         example                                     12            
  ------------------------------------------------------------------------------
  Total: 2
```

**Help:** execute the command "display ont-lineprofile gpon all"

**Prompt:**
- huawei_smartax>
- huawei_smartax#

### display ont-srvprofile gpon all

**Output:**
```
  -----------------------------------------------------------------------------
  Profile-ID  Profile-name                                Binding times
  -----------------------------------------------------------------------------
  0           srv-profile_default_0                       0            
  1           20221019172007514                           0            
  -----------------------------------------------------------------------------
  Total: 2
```

**Help:** execute the command "display ont-srvprofile gpon all"

**Prompt:**
- huawei_smartax>
- huawei_smartax#

### display ont autofind

**Output:**
```
   ----------------------------------------------------------------------------
   Number              : 1
   F/S/P               : 0/0/0
   Ont SN              : 12345678A12BC3AB (ABCD-A12BC3DE)
   Password            : 0x00000000000000000000
   Loid                :
   Checkcode           :
   VendorID            : HWTC
   Ont Version         : 1234A.D
   Ont SoftwareVersion : A1B123D12E123
   Ont EquipmentID     : EG8145X6-10
   Ont Customized Info : EUCOMMONEBG4
   Ont MAC             : 1234-ABCD-1234
   Ont Equipment SN    : 123456789ABCDEFGHIJK
   Ont autofind time   : 2000-01-01 00:00:00+00:00
   Multi channel       : -
   ----------------------------------------------------------------------------
```

**Help:** execute the command "display ont autofind"

**Prompt:**
- huawei_smartax>
- huawei_smartax#

### display ont capability all

**Output:**
```
  During the course of print ,press CTRL_C to break
  -------------------------------------------------------------------------- 
  ONT Hardware Capability / Status Information                               
  -------------------------------------------------------------------------- 
  F/S/P:                              0/1/0
  ONT description:                    ONU_1
  ONT ID:                             0
  Equipment ID:                       A123B
  Number of uplink PON ports:         1
  Number of POTS ports:               1
  Number of ETH ports:                1
  Number of VDSL ports:               -
  Number of TDM ports:                -
  Number of MOCA ports:               -
  Number of CATV ANI ports:           -
  Number of CATV UNI ports:           -
  Number of GEM ports:                32
  IP configuration:                   support
  Number of Traffic Schedulers:       8
  Number of T-CONTs:                  8
  The type of flow control:           GEMPORT CAR
  ONT optical module power              
  control capability:                 support
  ONT type:                           HGU
  Extended OMCI message format:       support
  VoIP configuration method:          OMCI/Configuration file/TR069
  VoIP signalling protocol:           SIP/H.248
  ETHOAM:                             not support
  Single ring check:                  support
  Multi channel:                      -
  Fit AP:                             not support
  -------------------------------------------------------------------------- 
  Number of PQs in T-CONT   0:          8
  Number of PQs in T-CONT   1:          8
  Number of PQs in T-CONT   2:          8
  Number of PQs in T-CONT   3:          8
  Number of PQs in T-CONT   4:          8
  Number of PQs in T-CONT   5:          8
  Number of PQs in T-CONT   6:          8
  Number of PQs in T-CONT   7:          8
  -------------------------------------------------------------------------- 
  F/S/P:                              0/1/0
  ONT description:                    ONT_NO_DESCRIPTION
  ONT ID:                             1
  Equipment ID:                       A123B-A10
  Number of uplink PON ports:         1
  Number of POTS ports:               -
  Number of ETH ports:                4
  Number of VDSL ports:               -
  Number of TDM ports:                -
  Number of MOCA ports:               -
  Number of CATV ANI ports:           -
  Number of CATV UNI ports:           -
  Number of GEM ports:                32
  IP configuration:                   support
  Number of Traffic Schedulers:       8
  Number of T-CONTs:                  8
  The type of flow control:           GEMPORT CAR
  ONT optical module power              
  control capability:                 support
  ONT type:                           HGU
  Extended OMCI message format:       support
  VoIP configuration method:          -
  VoIP signalling protocol:           -
  ETHOAM:                             not support
  Single ring check:                  support
  Multicast encrypt:                  support
  Multi channel:                      -
  Fit AP:                             not support
  -------------------------------------------------------------------------- 
  Number of PQs in T-CONT   0:          8
  Number of PQs in T-CONT   1:          8
  Number of PQs in T-CONT   2:          8
  Number of PQs in T-CONT   3:          8
  Number of PQs in T-CONT   4:          8
  Number of PQs in T-CONT   5:          8
  Number of PQs in T-CONT   6:          8
  Number of PQs in T-CONT   7:          8
  -------------------------------------------------------------------------- 
  The total of online ONTs are: 2
  -------------------------------------------------------------------------- 
```

**Help:** execute the command "display ont capability all"

**Prompt:**
- huawei_smartax>
- huawei_smartax#

### display ont gemport 0 ontid 0

**Output:**
```
  F/S/P: 0/0/0     ONT ID: 5                                                    
  ------------------------------------------------------------------------------ 
  GEM port  T-CONT  Service  Encrypt  Up  Down  Traffic                         
   ID       ID      type              PQ  PQ    table index                     
  ------------------------------------------------------------------------------
  126       4       ETHERNET off      -   adapt -
  ------------------------------------------------------------------------------
  Notes: Run the display traffic table ip command to query                      
         traffic table configuration                                            
  ------------------------------------------------------------------------------  
  The number of GEM ports is: 1
```

**Help:** execute the command "display ont gemport 0 ontid 0"

**Prompt:**
- huawei_smartax>
- huawei_smartax#

### display ont info 0

**Output:**
```
  -----------------------------------------------------------------------------
  F/S/P   ONT         SN         Control     Run      Config   Match    Protect
          ID                     flag        state    state    state    side 
  -----------------------------------------------------------------------------
  0/ 1/0    0  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0    1  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0    2  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0    3  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0    4  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0    5  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0    6  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0    7  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0    8  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0    9  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0   10  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0   11  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0   12  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0   13  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0   14  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0   15  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0   16  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0   17  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0   18  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0   19  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0   20  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0   21  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0   22  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0   23  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0   24  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0   25  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0   26  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0   27  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0   28  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0   29  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0   30  1234567890ABCDEF  active      online   normal   match    no 
  -----------------------------------------------------------------------------
  F/S/P       ONT  Description  
              ID  
  -----------------------------------------------------------------------------
  0/ 1/0       0   Generic_description
  0/ 1/0       1   Generic_description
  0/ 1/0       2   Generic_description
  0/ 1/0       3   Generic_description
  0/ 1/0       4   Generic_description
  0/ 1/0       5   Generic_description
  0/ 1/0       6   Generic_description
  0/ 1/0       7   Generic_description
  0/ 1/0       8   Generic_description
  0/ 1/0       9   Generic_description
  0/ 1/0      10   Generic_description
  0/ 1/0      11   Generic_description
  0/ 1/0      12   Generic_description
  0/ 1/0      13   Generic_description
  0/ 1/0      14   Generic_description
  0/ 1/0      15   Generic_description
  0/ 1/0      16   Generic_description
  0/ 1/0      17   Generic_description
  0/ 1/0      18   Generic_description
  0/ 1/0      19   Generic_description
  0/ 1/0      20   Generic_description
  0/ 1/0      21   Generic_description
  0/ 1/0      22   Generic_description
  0/ 1/0      23   Generic_description
  0/ 1/0      24   Generic_description
  0/ 1/0      25   Generic_description
  0/ 1/0      26   Generic_description
  0/ 1/0      27   Generic_description
  0/ 1/0      28   Generic_description
  0/ 1/0      29   Generic_description
  0/ 1/0      30   Generic_description
  -----------------------------------------------------------------------------
  In port 0/ 1/0 , the total of ONTs are: 31, online: 31
  -----------------------------------------------------------------------------
```

**Help:** execute the command "display ont info 0"

**Prompt:**
- huawei_smartax>
- huawei_smartax#

### display ont info 0 1

**Output:**
```
  -----------------------------------------------------------------------------
  F/S/P                   : 0/ 0/6
  ONT-ID                  : 2
  Control flag            : active
  Run state               : online
  Config state            : normal
  Match state             : match
  ONT LLID                : -
  ONT distance(m)         : 47
  ONT last distance(m)    : 39
  ONT RTT(TQ)             : -
  Memory occupation       : 44
  CPU occupation          : 84
  Temperature             : 57
  Authentic type          : SN-auth
  SN                      : 8XN7J0FFL8NL6I3W
  Management mode         : OMCI
  Software work mode      : normal
  Multicast mode          : IGMP-Snooping
  Description             : New_link
  Last down cause         : dying-gasp
  Last up time            : 2023-01-05 08:56:12+08:00
  Last down time          : 2023-01-05 08:55:28+08:00
  Last dying gasp time    : 2023-01-05 08:55:28+08:00
  ONT online duration     : 0 day(s), 0 hour(s), 3 minute(s), 0 second(s)
  Type D support          : Not support
  Isolation state         : normal
  ONT NNI type            : auto
  ONT actual NNI type     : auto
  Last ONT actual NNI type: auto
  Interoperability-mode   : unknown
  FEC upstream state      :
  VS-ID                   : 0
  VS name                 : admin-vs
  Global ONT-ID           : 93
  Fiber route             : none
  -----------------------------------------------------------------------------
  Line profile ID      : 500
  Line profile name    : new_link
  -----------------------------------------------------------------------------
  FEC upstream switch :Disable
  OMCC Encrypt switch :On
  Qos mode            :Pq
  Mapping mode        :Vlan
  Tr069 management    :Disable
  -----------------------------------------------------------------------------
  Notes: * indicates Discrete TCONT(TCONT Unbound)
  -----------------------------------------------------------------------------
  <T-CONT   0>          DBA Profile-ID:1
  <T-CONT   1>          DBA Profile-ID:2
  <T-CONT   4>          DBA Profile-ID:5
    <Gem Index 126>
    ------------------------------------------------------------------------
    |Serv-Type:ETH |Encrypt:off |Cascade:off |GEM-CAR:-            |
    |Upstream-priority-queue:-  |Downstream-priority-queue:-       |
    ------------------------------------------------------------------------
     Mapping VLAN  Priority Port   Port  Bundle  Flow  Transparent
     index                  type   ID    ID      CAR
    ------------------------------------------------------------------------
     0       500   -        -      -     -       -     -
    ------------------------------------------------------------------------
  <T-CONT   5>          DBA Profile-ID:5
    <Gem Index 126>
    ------------------------------------------------------------------------
    |Serv-Type:ETH |Encrypt:off |Cascade:off |GEM-CAR:-            |
    |Upstream-priority-queue:-  |Downstream-priority-queue:-       |
    ------------------------------------------------------------------------
     Mapping VLAN  Priority Port   Port  Bundle  Flow  Transparent
     index                  type   ID    ID      CAR
    ------------------------------------------------------------------------
     0       500   -        -      -     -       -     -
    ------------------------------------------------------------------------
  -----------------------------------------------------------------------------
  Service profile ID   : 500
  Service profile name : new_link
  -----------------------------------------------------------------------------
  Port-type     Port-number
  -----------------------------------------------------------------------------
  POTS          4
  ETH           4
  TDM           0
  MOCA          0
  CATV          0
  -----------------------------------------------------------------------------
  TDM port type                     : E1
  TDM service type                  : TDMoGem
  MAC learning function switch      : enable
  ONT transparent function switch   : disable
  Multicast forward mode            : Unconcern
  Multicast forward VLAN            : -
  Multicast mode                    : Unconcern
  Upstream IGMP packet forward mode : Unconcern
  Upstream IGMP packet forward VLAN : -
  Upstream IGMP packet priority     : -
  Native VLAN option                : Concern
  Upstream PQ color policy          : None
  Downstream PQ color policy        : None
  -----------------------------------------------------------------------------
  Port-type Port-ID QinQmode  PriorityPolicy Inbound     Outbound
  -----------------------------------------------------------------------------
  ETH       1       unconcern unconcern      unconcern   unconcern
  ETH       2       unconcern unconcern      unconcern   unconcern
  ETH       3       unconcern unconcern      unconcern   unconcern
  ETH       4       unconcern unconcern      unconcern   unconcern
  -----------------------------------------------------------------------------
  Notes: * indicates the discretely configured traffic profile
  -----------------------------------------------------------------------------
  Port-type Port-ID Dscp-mapping-table-index
  -----------------------------------------------------------------------------
  ETH       1       0
  ETH       2       0
  ETH       3       0
  ETH       4       0
  IPHOST    1       0
  -----------------------------------------------------------------------------
  Port   Port   Service-type Index S-VLAN S-PRI C-VLAN C-PRI ENCAP      S-PRI
  type   ID                                                             POLICY
  -----------------------------------------------------------------------------
  ETH    1      Translation  1     500    -     500    -     -          -
  -----------------------------------------------------------------------------
  Notes: * indicates transparent attribute of the vlan
  -----------------------------------------------------------------------------
  Port-type  Port-ID    IGMP-mode         IGMP-VLAN  IGMP-PRI  Max-MAC-Count
  -----------------------------------------------------------------------------
  ETH              1    -                         -         -      Unlimited
  ETH              2    -                         -         -      Unlimited
  ETH              3    -                         -         -      Unlimited
  ETH              4    -                         -         -      Unlimited
  -----------------------------------------------------------------------------
  Alarm policy profile ID      : 0
  Alarm policy profile name    : alarm-policy_0
  -----------------------------------------------------------------------------
```

**Help:** execute the command "display ont info 0 1"

**Prompt:**
- huawei_smartax>
- huawei_smartax#

### display ont info 0 1 2

**Output:**
```
  -----------------------------------------------------------------------------
  F/S/P   ONT         SN         Control     Run      Config   Match    Protect
          ID                     flag        state    state    state    side 
  -----------------------------------------------------------------------------
  0/ 1/0    0  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0    1  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0    2  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0    3  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0    4  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0    5  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0    6  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0    7  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0    8  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0    9  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0   10  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0   11  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0   12  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0   13  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0   14  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0   15  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0   16  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0   17  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0   18  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0   19  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0   20  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0   21  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0   22  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0   23  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0   24  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0   25  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0   26  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0   27  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0   28  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0   29  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0   30  1234567890ABCDEF  active      online   normal   match    no 
  -----------------------------------------------------------------------------
  F/S/P       ONT  Description  
              ID  
  -----------------------------------------------------------------------------
  0/ 1/0       0   Generic_description
  0/ 1/0       1   Generic_description
  0/ 1/0       2   Generic_description
  0/ 1/0       3   Generic_description
  0/ 1/0       4   Generic_description
  0/ 1/0       5   Generic_description
  0/ 1/0       6   Generic_description
  0/ 1/0       7   Generic_description
  0/ 1/0       8   Generic_description
  0/ 1/0       9   Generic_description
  0/ 1/0      10   Generic_description
  0/ 1/0      11   Generic_description
  0/ 1/0      12   Generic_description
  0/ 1/0      13   Generic_description
  0/ 1/0      14   Generic_description
  0/ 1/0      15   Generic_description
  0/ 1/0      16   Generic_description
  0/ 1/0      17   Generic_description
  0/ 1/0      18   Generic_description
  0/ 1/0      19   Generic_description
  0/ 1/0      20   Generic_description
  0/ 1/0      21   Generic_description
  0/ 1/0      22   Generic_description
  0/ 1/0      23   Generic_description
  0/ 1/0      24   Generic_description
  0/ 1/0      25   Generic_description
  0/ 1/0      26   Generic_description
  0/ 1/0      27   Generic_description
  0/ 1/0      28   Generic_description
  0/ 1/0      29   Generic_description
  0/ 1/0      30   Generic_description
  -----------------------------------------------------------------------------
  In port 0/ 1/0 , the total of ONTs are: 31, online: 31
  -----------------------------------------------------------------------------
```

**Help:** execute the command "display ont info 0 1 2"

**Prompt:**
- huawei_smartax>
- huawei_smartax#

### display ont info 0 1 2 3

**Output:**
```
  -----------------------------------------------------------------------------
  F/S/P                   : 0/ 0/6
  ONT-ID                  : 2
  Control flag            : active
  Run state               : online
  Config state            : normal
  Match state             : match
  ONT LLID                : -
  ONT distance(m)         : 47
  ONT last distance(m)    : 39
  ONT RTT(TQ)             : -
  Memory occupation       : 44
  CPU occupation          : 84
  Temperature             : 57
  Authentic type          : SN-auth
  SN                      : 8XN7J0FFL8NL6I3W
  Management mode         : OMCI
  Software work mode      : normal
  Multicast mode          : IGMP-Snooping
  Description             : New_link
  Last down cause         : dying-gasp
  Last up time            : 2023-01-05 08:56:12+08:00
  Last down time          : 2023-01-05 08:55:28+08:00
  Last dying gasp time    : 2023-01-05 08:55:28+08:00
  ONT online duration     : 0 day(s), 0 hour(s), 3 minute(s), 0 second(s)
  Type D support          : Not support
  Isolation state         : normal
  ONT NNI type            : auto
  ONT actual NNI type     : auto
  Last ONT actual NNI type: auto
  Interoperability-mode   : unknown
  FEC upstream state      :
  VS-ID                   : 0
  VS name                 : admin-vs
  Global ONT-ID           : 93
  Fiber route             : none
  -----------------------------------------------------------------------------
  Line profile ID      : 500
  Line profile name    : new_link
  -----------------------------------------------------------------------------
  FEC upstream switch :Disable
  OMCC Encrypt switch :On
  Qos mode            :Pq
  Mapping mode        :Vlan
  Tr069 management    :Disable
  -----------------------------------------------------------------------------
  Notes: * indicates Discrete TCONT(TCONT Unbound)
  -----------------------------------------------------------------------------
  <T-CONT   0>          DBA Profile-ID:1
  <T-CONT   1>          DBA Profile-ID:2
  <T-CONT   4>          DBA Profile-ID:5
    <Gem Index 126>
    ------------------------------------------------------------------------
    |Serv-Type:ETH |Encrypt:off |Cascade:off |GEM-CAR:-            |
    |Upstream-priority-queue:-  |Downstream-priority-queue:-       |
    ------------------------------------------------------------------------
     Mapping VLAN  Priority Port   Port  Bundle  Flow  Transparent
     index                  type   ID    ID      CAR
    ------------------------------------------------------------------------
     0       500   -        -      -     -       -     -
    ------------------------------------------------------------------------
  <T-CONT   5>          DBA Profile-ID:5
    <Gem Index 126>
    ------------------------------------------------------------------------
    |Serv-Type:ETH |Encrypt:off |Cascade:off |GEM-CAR:-            |
    |Upstream-priority-queue:-  |Downstream-priority-queue:-       |
    ------------------------------------------------------------------------
     Mapping VLAN  Priority Port   Port  Bundle  Flow  Transparent
     index                  type   ID    ID      CAR
    ------------------------------------------------------------------------
     0       500   -        -      -     -       -     -
    ------------------------------------------------------------------------
  -----------------------------------------------------------------------------
  Service profile ID   : 500
  Service profile name : new_link
  -----------------------------------------------------------------------------
  Port-type     Port-number
  -----------------------------------------------------------------------------
  POTS          4
  ETH           4
  TDM           0
  MOCA          0
  CATV          0
  -----------------------------------------------------------------------------
  TDM port type                     : E1
  TDM service type                  : TDMoGem
  MAC learning function switch      : enable
  ONT transparent function switch   : disable
  Multicast forward mode            : Unconcern
  Multicast forward VLAN            : -
  Multicast mode                    : Unconcern
  Upstream IGMP packet forward mode : Unconcern
  Upstream IGMP packet forward VLAN : -
  Upstream IGMP packet priority     : -
  Native VLAN option                : Concern
  Upstream PQ color policy          : None
  Downstream PQ color policy        : None
  -----------------------------------------------------------------------------
  Port-type Port-ID QinQmode  PriorityPolicy Inbound     Outbound
  -----------------------------------------------------------------------------
  ETH       1       unconcern unconcern      unconcern   unconcern
  ETH       2       unconcern unconcern      unconcern   unconcern
  ETH       3       unconcern unconcern      unconcern   unconcern
  ETH       4       unconcern unconcern      unconcern   unconcern
  -----------------------------------------------------------------------------
  Notes: * indicates the discretely configured traffic profile
  -----------------------------------------------------------------------------
  Port-type Port-ID Dscp-mapping-table-index
  -----------------------------------------------------------------------------
  ETH       1       0
  ETH       2       0
  ETH       3       0
  ETH       4       0
  IPHOST    1       0
  -----------------------------------------------------------------------------
  Port   Port   Service-type Index S-VLAN S-PRI C-VLAN C-PRI ENCAP      S-PRI
  type   ID                                                             POLICY
  -----------------------------------------------------------------------------
  ETH    1      Translation  1     500    -     500    -     -          -
  -----------------------------------------------------------------------------
  Notes: * indicates transparent attribute of the vlan
  -----------------------------------------------------------------------------
  Port-type  Port-ID    IGMP-mode         IGMP-VLAN  IGMP-PRI  Max-MAC-Count
  -----------------------------------------------------------------------------
  ETH              1    -                         -         -      Unlimited
  ETH              2    -                         -         -      Unlimited
  ETH              3    -                         -         -      Unlimited
  ETH              4    -                         -         -      Unlimited
  -----------------------------------------------------------------------------
  Alarm policy profile ID      : 0
  Alarm policy profile name    : alarm-policy_0
  -----------------------------------------------------------------------------
```

**Help:** execute the command "display ont info 0 1 2 3"

**Prompt:**
- huawei_smartax>
- huawei_smartax#

### display ont info by-sn ABC

**Output:**
```
  -----------------------------------------------------------------------------
  F/S/P                   : 0/ 0/6
  ONT-ID                  : 2
  Control flag            : active
  Run state               : online
  Config state            : normal
  Match state             : match
  ONT LLID                : -
  ONT distance(m)         : 47
  ONT last distance(m)    : 39
  ONT RTT(TQ)             : -
  Memory occupation       : 44
  CPU occupation          : 84
  Temperature             : 57
  Authentic type          : SN-auth
  SN                      : 8XN7J0FFL8NL6I3W
  Management mode         : OMCI
  Software work mode      : normal
  Multicast mode          : IGMP-Snooping
  Description             : New_link
  Last down cause         : dying-gasp
  Last up time            : 2023-01-05 08:56:12+08:00
  Last down time          : 2023-01-05 08:55:28+08:00
  Last dying gasp time    : 2023-01-05 08:55:28+08:00
  ONT online duration     : 0 day(s), 0 hour(s), 3 minute(s), 0 second(s)
  Type D support          : Not support
  Isolation state         : normal
  ONT NNI type            : auto
  ONT actual NNI type     : auto
  Last ONT actual NNI type: auto
  Interoperability-mode   : unknown
  FEC upstream state      :
  VS-ID                   : 0
  VS name                 : admin-vs
  Global ONT-ID           : 93
  Fiber route             : none
  -----------------------------------------------------------------------------
  Line profile ID      : 500
  Line profile name    : new_link
  -----------------------------------------------------------------------------
  FEC upstream switch :Disable
  OMCC Encrypt switch :On
  Qos mode            :Pq
  Mapping mode        :Vlan
  Tr069 management    :Disable
  -----------------------------------------------------------------------------
  Notes: * indicates Discrete TCONT(TCONT Unbound)
  -----------------------------------------------------------------------------
  <T-CONT   0>          DBA Profile-ID:1
  <T-CONT   1>          DBA Profile-ID:2
  <T-CONT   4>          DBA Profile-ID:5
    <Gem Index 126>
    ------------------------------------------------------------------------
    |Serv-Type:ETH |Encrypt:off |Cascade:off |GEM-CAR:-            |
    |Upstream-priority-queue:-  |Downstream-priority-queue:-       |
    ------------------------------------------------------------------------
     Mapping VLAN  Priority Port   Port  Bundle  Flow  Transparent
     index                  type   ID    ID      CAR
    ------------------------------------------------------------------------
     0       500   -        -      -     -       -     -
    ------------------------------------------------------------------------
  <T-CONT   5>          DBA Profile-ID:5
    <Gem Index 126>
    ------------------------------------------------------------------------
    |Serv-Type:ETH |Encrypt:off |Cascade:off |GEM-CAR:-            |
    |Upstream-priority-queue:-  |Downstream-priority-queue:-       |
    ------------------------------------------------------------------------
     Mapping VLAN  Priority Port   Port  Bundle  Flow  Transparent
     index                  type   ID    ID      CAR
    ------------------------------------------------------------------------
     0       500   -        -      -     -       -     -
    ------------------------------------------------------------------------
  -----------------------------------------------------------------------------
  Service profile ID   : 500
  Service profile name : new_link
  -----------------------------------------------------------------------------
  Port-type     Port-number
  -----------------------------------------------------------------------------
  POTS          4
  ETH           4
  TDM           0
  MOCA          0
  CATV          0
  -----------------------------------------------------------------------------
  TDM port type                     : E1
  TDM service type                  : TDMoGem
  MAC learning function switch      : enable
  ONT transparent function switch   : disable
  Multicast forward mode            : Unconcern
  Multicast forward VLAN            : -
  Multicast mode                    : Unconcern
  Upstream IGMP packet forward mode : Unconcern
  Upstream IGMP packet forward VLAN : -
  Upstream IGMP packet priority     : -
  Native VLAN option                : Concern
  Upstream PQ color policy          : None
  Downstream PQ color policy        : None
  -----------------------------------------------------------------------------
  Port-type Port-ID QinQmode  PriorityPolicy Inbound     Outbound
  -----------------------------------------------------------------------------
  ETH       1       unconcern unconcern      unconcern   unconcern
  ETH       2       unconcern unconcern      unconcern   unconcern
  ETH       3       unconcern unconcern      unconcern   unconcern
  ETH       4       unconcern unconcern      unconcern   unconcern
  -----------------------------------------------------------------------------
  Notes: * indicates the discretely configured traffic profile
  -----------------------------------------------------------------------------
  Port-type Port-ID Dscp-mapping-table-index
  -----------------------------------------------------------------------------
  ETH       1       0
  ETH       2       0
  ETH       3       0
  ETH       4       0
  IPHOST    1       0
  -----------------------------------------------------------------------------
  Port   Port   Service-type Index S-VLAN S-PRI C-VLAN C-PRI ENCAP      S-PRI
  type   ID                                                             POLICY
  -----------------------------------------------------------------------------
  ETH    1      Translation  1     500    -     500    -     -          -
  -----------------------------------------------------------------------------
  Notes: * indicates transparent attribute of the vlan
  -----------------------------------------------------------------------------
  Port-type  Port-ID    IGMP-mode         IGMP-VLAN  IGMP-PRI  Max-MAC-Count
  -----------------------------------------------------------------------------
  ETH              1    -                         -         -      Unlimited
  ETH              2    -                         -         -      Unlimited
  ETH              3    -                         -         -      Unlimited
  ETH              4    -                         -         -      Unlimited
  -----------------------------------------------------------------------------
  Alarm policy profile ID      : 0
  Alarm policy profile name    : alarm-policy_0
  -----------------------------------------------------------------------------
```

**Help:** execute the command "display ont info by-sn ABC"

**Prompt:**
- huawei_smartax>
- huawei_smartax#

### display ont info by-sn sn

**Output:**
```
  -----------------------------------------------------------------------------
  F/S/P                   : 0/1/1
  ONT-ID                  : 131
  Control flag            : active
  Run state               : online
  Config state            : normal
  Match state             : match
  DBA type                : SR
  ONT distance(m)         : 100
  ONT last distance(m)    : 100
  ONT battery state       : not support
  ONT power type          : -
  Memory occupation       : 23%
  CPU occupation          : 30%
  Temperature             : 70(C)
  Authentic type          : SN-auth
  SN                      : 123456789123AB12AB (HWTC-12AB12AB)
  Management mode         : OMCI
  Software work mode      : normal
  Isolation state         : normal
  ONT IP 0 address/mask   : 192.168.0.1/24
  ONT IP 1 address/mask   : 192.168.0.1/24
  Description             : ABCD
  Last down cause         : dying-gasp
  Last up time            : 09/02/2019 01:58:52+00:00
  Last down time          : 22/01/2019 01:57:55+00:00
  Last dying gasp time    : 22/01/2019 01:57:55+00:00
  Last restart reason     : -
  ONT online duration     : 22 day(s), 1 hour(s), 23 minute(s), 23 second(s) 
  ONT system up duration  : 22 day(s), 1 hour(s), 23 minute(s), 23 second(s) 
  Type C support          : Not support
  Interoperability-mode   : ITU-T
  Power reduction status  : -
  FEC upstream state      : use-profile-config
  VS-ID                   : 0
  VS name                 : admin-vs
  Global ONT-ID           : 131
  -----------------------------------------------------------------------------
  VoIP configure method   : Default
  -----------------------------------------------------------------------------
  Line profile ID      : 100
  Line profile name    : ftth
  -----------------------------------------------------------------------------
  FEC upstream switch :Disable 
  OMCC encrypt switch :On
  Qos mode            :PQ
  Mapping mode        :VLAN
  TR069 management    :Enable        
  TR069 IP index      :0
  ------------------------------------------------------------------------------
  Notes: * indicates Discrete TCONT(TCONT Unbound)
  ------------------------------------------------------------------------------
  <T-CONT   0>          DBA Profile-ID:1
  <T-CONT   1>          DBA Profile-ID:100
   <Gem Index 1>
   --------------------------------------------------------------------
   |Serv-Type:ETH |Encrypt:on  |Cascade:off |GEM-CAR:-            |
   |Upstream-priority-queue:0  |Downstream-priority-queue:-       |
   --------------------------------------------------------------------
    Mapping VLAN  Priority Port    Port  Bundle  Flow  Transparent
    index                  type    ID    ID      CAR   
   --------------------------------------------------------------------
    0       40    -        -       -     -       -     -          
    1       41    -        -       -     -       -     -          
   --------------------------------------------------------------------
  <T-CONT   2>          DBA Profile-ID:101
   <Gem Index 2>
   --------------------------------------------------------------------
   |Serv-Type:ETH |Encrypt:on  |Cascade:off |GEM-CAR:-            |
   |Upstream-priority-queue:0  |Downstream-priority-queue:-       |
   --------------------------------------------------------------------
    Mapping VLAN  Priority Port    Port  Bundle  Flow  Transparent
    index                  type    ID    ID      CAR   
   --------------------------------------------------------------------
    0       42    -        -       -     -       -     -          
   --------------------------------------------------------------------
  <T-CONT   3>          DBA Profile-ID:102
   <Gem Index 3>
   --------------------------------------------------------------------
   |Serv-Type:ETH |Encrypt:on  |Cascade:off |GEM-CAR:-            |
   |Upstream-priority-queue:0  |Downstream-priority-queue:-       |
   --------------------------------------------------------------------
    Mapping VLAN  Priority Port    Port  Bundle  Flow  Transparent
    index                  type    ID    ID      CAR   
   --------------------------------------------------------------------
    0       1     -        -       -     -       -     -          
    1       2     -        -       -     -       -     -          
    2       3     -        -       -     -       -     -          
    3       4     -        -       -     -       -     -          
   --------------------------------------------------------------------
  <T-CONT   4>          DBA Profile-ID:103
   <Gem Index 4>
   --------------------------------------------------------------------
   |Serv-Type:ETH |Encrypt:on  |Cascade:off |GEM-CAR:-            |
   |Upstream-priority-queue:0  |Downstream-priority-queue:-       |
   --------------------------------------------------------------------
    Mapping VLAN  Priority Port    Port  Bundle  Flow  Transparent
    index                  type    ID    ID      CAR   
   --------------------------------------------------------------------
    0       8     -        -       -     -       -     -          
   --------------------------------------------------------------------
  <T-CONT   5>          DBA Profile-ID:104
   <Gem Index 5>
   --------------------------------------------------------------------
   |Serv-Type:ETH |Encrypt:on  |Cascade:off |GEM-CAR:-            |
   |Upstream-priority-queue:0  |Downstream-priority-queue:-       |
   --------------------------------------------------------------------
  ------------------------------------------------------------------------------
  Notes: Run the display traffic table ip command to query 
         traffic table configuration
  -----------------------------------------------------------------------------
  Service profile ID   : 100
  Service profile name : ftth
  -----------------------------------------------------------------------------
  Port-type     Port-number     Max-adaptive-number
  -----------------------------------------------------------------------------
  POTS          adaptive        32
  ETH           adaptive        8
  VDSL          0               -
  TDM           0               -    
  MOCA          0               -
  CATV          adaptive        8
  -----------------------------------------------------------------------------
  TDM port type                     : E1
  TDM service type                  : TDMoGem
  MAC learning function switch      : Enable
  ONT transparent function switch   : Disable
  Ring check switch                 : Enable
  Ring port auto-shutdown           : Enable
  Ring detect frequency             : 8 (pps)
  Ring resume interval              : 240 (s)
  Ring detect period                : 0 (s)
  Multicast forward mode            : Unconcern
  Multicast forward VLAN            : -
  Multicast mode                    : Unconcern
  Upstream IGMP packet forward mode : Unconcern
  Upstream IGMP packet forward VLAN : -
  Upstream IGMP packet priority     : -
  Native VLAN option                : Concern
  Upstream PQ color policy          : -
  Downstream PQ color policy        : -
  Monitor link                      : Unconcern
  MTU(byte)                         : Unconcern
  -----------------------------------------------------------------------------
  Port-type Port-ID QinQmode  PriorityPolicy Inbound     Outbound
  -----------------------------------------------------------------------------
  ETH       1       unconcern unconcern      unconcern   unconcern
  ETH       2       unconcern unconcern      unconcern   unconcern
  ETH       3       unconcern unconcern      unconcern   unconcern
  ETH       4       unconcern unconcern      unconcern   unconcern
  ETH       5       unconcern unconcern      unconcern   unconcern
  ETH       6       unconcern unconcern      unconcern   unconcern
  ETH       7       unconcern unconcern      unconcern   unconcern
  ETH       8       unconcern unconcern      unconcern   unconcern
  IPHOST    1       unconcern unconcern      unconcern   unconcern
  -----------------------------------------------------------------------------
  Notes: * indicates the discretely configured traffic profile,
         run the display traffic table ip command to query
         traffic table configuration.
  -----------------------------------------------------------------------------
  Port-type Port-ID  DownstreamMode  MismatchPolicy
  -----------------------------------------------------------------------------
  ETH             1  operation       discard       
  ETH             2  operation       discard       
  ETH             3  operation       discard       
  ETH             4  operation       discard       
  ETH             5  operation       discard       
  ETH             6  operation       discard       
  ETH             7  operation       discard       
  ETH             8  operation       discard       
  -----------------------------------------------------------------------------
  Port-type Port-ID Dscp-mapping-table-index Classification-profile-id
  -----------------------------------------------------------------------------
  ETH       1       0                        -        
  ETH       2       0                        -        
  ETH       3       0                        -        
  ETH       4       0                        -        
  ETH       5       0                        -        
  ETH       6       0                        -        
  ETH       7       0                        -        
  ETH       8       0                        -        
  IPHOST    1       0                        -
  -----------------------------------------------------------------------------
  Port-type  Port-ID    IGMP-mode         IGMP-VLAN  IGMP-PRI  Max-MAC-Count
  -----------------------------------------------------------------------------
  ETH              1    -                         -         -      Unlimited
  ETH              2    -                         -         -      Unlimited
  ETH              3    -                         -         -      Unlimited
  ETH              4    -                         -         -      Unlimited
  ETH              5    -                         -         -      Unlimited
  ETH              6    -                         -         -      Unlimited
  ETH              7    -                         -         -      Unlimited
  ETH              8    -                         -         -      Unlimited
  IPHOST           1    -                         -         -      Unlimited
  -----------------------------------------------------------------------------
  Port-type Port-ID   Traffic-suppress   Traffic-suppress   Traffic-suppress
                      unicast(kbps)      multicast(kpbs)    broadcast(kbps)
  -----------------------------------------------------------------------------
  ETH             1   -                  -                  -               
  ETH             2   -                  -                  -               
  ETH             3   -                  -                  -               
  ETH             4   -                  -                  -               
  ETH             5   -                  -                  -               
  ETH             6   -                  -                  -               
  ETH             7   -                  -                  -               
  ETH             8   -                  -                  -               
  -----------------------------------------------------------------------------
  Port-type  Port-ID  L2-isolate
  -----------------------------------------------------------------------------
  ETH              1  unconcern           
  ETH              2  unconcern           
  ETH              3  unconcern           
  ETH              4  unconcern           
  ETH              5  unconcern           
  ETH              6  unconcern           
  ETH              7  unconcern           
  ETH              8  unconcern           
  -----------------------------------------------------------------------------
  Alarm policy profile ID      : 0
  Alarm policy profile name    : alarm-policy_0
  -----------------------------------------------------------------------------
  TR069 server profile ID      : 1
  TR069 server profile name    : tr069-server-profile_1
  -----------------------------------------------------------------------------
  -----------------------------------------------------------------------------
  The number of required ONTs     : 1
  -----------------------------------------------------------------------------
```

**Help:** execute the command "display ont info by-sn sn"

**Prompt:**
- huawei_smartax>
- huawei_smartax#

### display ont info fsp

**Output:**
```
  -----------------------------------------------------------------------------
  F/S/P   ONT         SN         Control     Run      Config   Match    Protect
          ID                     flag        state    state    state    side 
  -----------------------------------------------------------------------------
  0/ 1/0    0  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0    1  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0    2  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0    3  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0    4  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0    5  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0    6  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0    7  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0    8  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0    9  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0   10  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0   11  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0   12  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0   13  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0   14  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0   15  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0   16  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0   17  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0   18  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0   19  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0   20  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0   21  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0   22  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0   23  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0   24  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0   25  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0   26  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0   27  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0   28  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0   29  1234567890ABCDEF  active      online   normal   match    no 
  0/ 1/0   30  1234567890ABCDEF  active      online   normal   match    no 
  -----------------------------------------------------------------------------
  F/S/P       ONT  Description  
              ID  
  -----------------------------------------------------------------------------
  0/ 1/0       0   Generic_description
  0/ 1/0       1   Generic_description
  0/ 1/0       2   Generic_description
  0/ 1/0       3   Generic_description
  0/ 1/0       4   Generic_description
  0/ 1/0       5   Generic_description
  0/ 1/0       6   Generic_description
  0/ 1/0       7   Generic_description
  0/ 1/0       8   Generic_description
  0/ 1/0       9   Generic_description
  0/ 1/0      10   Generic_description
  0/ 1/0      11   Generic_description
  0/ 1/0      12   Generic_description
  0/ 1/0      13   Generic_description
  0/ 1/0      14   Generic_description
  0/ 1/0      15   Generic_description
  0/ 1/0      16   Generic_description
  0/ 1/0      17   Generic_description
  0/ 1/0      18   Generic_description
  0/ 1/0      19   Generic_description
  0/ 1/0      20   Generic_description
  0/ 1/0      21   Generic_description
  0/ 1/0      22   Generic_description
  0/ 1/0      23   Generic_description
  0/ 1/0      24   Generic_description
  0/ 1/0      25   Generic_description
  0/ 1/0      26   Generic_description
  0/ 1/0      27   Generic_description
  0/ 1/0      28   Generic_description
  0/ 1/0      29   Generic_description
  0/ 1/0      30   Generic_description
  -----------------------------------------------------------------------------
  In port 0/ 1/0 , the total of ONTs are: 31, online: 31
  -----------------------------------------------------------------------------
```

**Help:** execute the command "display ont info fsp"

**Prompt:**
- huawei_smartax>
- huawei_smartax#

### display ont info summary ont

**Output:**
```
  ------------------------------------------------------------------------------
  In port 0/1/0, the total of ONTs are: 23, online: 23
  ------------------------------------------------------------------------------
  ONT  Run     Last                Last                Last
  ID   State   UpTime              DownTime            DownCause
  ------------------------------------------------------------------------------
  0    online  2000-01-01 00:00:00 2000-01-01 00:00:00 LOSi/LOBi
  1    online  2000-01-01 00:00:00 2000-01-01 00:00:00 LOSi/LOBi
  2    online  2000-01-01 00:00:00 2000-01-01 00:00:00 LOSi/LOBi
  3    online  2000-01-01 00:00:00 2000-01-01 00:00:00 LOSi/LOBi
  4    online  2000-01-01 00:00:00 2000-01-01 00:00:00 LOSi/LOBi
  5    online  2000-01-01 00:00:00 2000-01-01 00:00:00 LOSi/LOBi
  6    online  2000-01-01 00:00:00 2000-01-01 00:00:00 LOSi/LOBi
  7    online  2000-01-01 00:00:00 2000-01-01 00:00:00 LOSi/LOBi
  8    online  2000-01-01 00:00:00 2000-01-01 00:00:00 LOSi/LOBi
  9    online  2000-01-01 00:00:00 2000-01-01 00:00:00 LOSi/LOBi
  10   online  2000-01-01 00:00:00 2000-01-01 00:00:00 LOSi/LOBi
  11   online  2000-01-01 00:00:00 2000-01-01 00:00:00 LOSi/LOBi
  12   online  2000-01-01 00:00:00 2000-01-01 00:00:00 LOSi/LOBi
  13   online  2000-01-01 00:00:00 2000-01-01 00:00:00 LOSi/LOBi
  14   online  2000-01-01 00:00:00 2000-01-01 00:00:00 LOSi/LOBi
  15   online  2000-01-01 00:00:00 2000-01-01 00:00:00 LOSi/LOBi
  16   online  2000-01-01 00:00:00 2000-01-01 00:00:00 LOSi/LOBi
  17   online  2000-01-01 00:00:00 2000-01-01 00:00:00 LOSi/LOBi
  18   online  2000-01-01 00:00:00 2000-01-01 00:00:00 LOSi/LOBi
  19   online  2000-01-01 00:00:00 2000-01-01 00:00:00 LOSi/LOBi
  20   online  2000-01-01 00:00:00 2000-01-01 00:00:00 LOSi/LOBi
  21   online  2000-01-01 00:00:00 2000-01-01 00:00:00 LOSi/LOBi
  22   online  2000-01-01 00:00:00 2000-01-01 00:00:00 LOSi/LOBi
  ------------------------------------------------------------------------------
  ONT        SN        Type          Distance Rx/Tx power  Description
  ID                                    (m)      (dBm)
  ------------------------------------------------------------------------------
  0   1234567890ABCDEF AB1234C5         100   -10.12/2.03  AB12
  1   1234567890ABCDEF AB1234C5         100   -10.12/2.03  AB12
  2   1234567890ABCDEF AB1234C5         100   -10.12/2.03  AB12
  3   1234567890ABCDEF AB1234C5         100   -10.12/2.03  AB12
  4   1234567890ABCDEF AB1234C5         100   -10.12/2.03  AB12
  5   1234567890ABCDEF AB1234C5         100   -10.12/2.03  AB12
  6   1234567890ABCDEF AB1234C5         100   -10.12/2.03  AB12
  7   1234567890ABCDEF AB1234C5         100   -10.12/2.03  AB12
  8   1234567890ABCDEF AB1234C5         100   -10.12/2.03  AB12
  9   1234567890ABCDEF AB1234C5         100   -10.12/2.03  AB12
  10  1234567890ABCDEF AB1234C5         100   -10.12/2.03  AB12
  11  1234567890ABCDEF AB1234C5         100   -10.12/2.03  AB12
  12  1234567890ABCDEF AB1234C5         100   -10.12/2.03  AB12
  13  1234567890ABCDEF AB1234C5         100   -10.12/2.03  AB12
  14  1234567890ABCDEF AB1234C5         100   -10.12/2.03  AB12
  15  1234567890ABCDEF AB1234C5         100   -10.12/2.03  AB12
  16  1234567890ABCDEF AB1234C5         100   -10.12/2.03  AB12
  17  1234567890ABCDEF AB1234C5         100   -10.12/2.03  AB12
  18  1234567890ABCDEF AB1234C5         100   -10.12/2.03  AB12
  19  1234567890ABCDEF AB1234C5         100   -10.12/2.03  AB12
  20  1234567890ABCDEF AB1234C5         100   -10.12/2.03  AB12
  21  1234567890ABCDEF AB1234C5         100   -10.12/2.03  AB12
  22  1234567890ABCDEF AB1234C5         100   -10.12/2.03  AB12
  ------------------------------------------------------------------------------
```

**Help:** execute the command "display ont info summary ont"

**Prompt:**
- huawei_smartax>
- huawei_smartax#

### display ont optical-info 0 all

**Output:**
```
  ----------------------------------------------------------------------------- 
  ONT  Rx power  Tx power  OLT Rx ONT  Temperature  Voltage  Current  Distance  
  ID   (dBm)     (dBm)     power(dBm)  (C)          (V)      (mA)     (m)       
  ----------------------------------------------------------------------------- 
    0  -24.68    3.68      -22.68      38           3.200    6        171       
    1  -24.68    3.86      -23.02      31           3.220    8        170       
    2  -25.68    3.62      -23.77      32           3.200    8        170       
    3  -25.37    3.91      -22.45      31           3.180    7        170       
    4  -25.37    3.76      -22.22      30           3.200    7        170       
    5  -26.57    3.96      -23.88      38           3.220    8        170       
    6  -24.68    3.53      -23.47      36           3.260    8        170       
    7  -25.37    3.71      -23.88      38           3.220    9        170       
    8  -25.37    3.66      -22.93      30           3.180    5        170       
    9  -24.43    3.72      -23.77      38           3.200    8        170    
  -----------------------------------------------------------------------------
```

**Help:** execute the command "display ont optical-info 0 all"

**Prompt:**
- huawei_smartax>
- huawei_smartax#

### display ont port state 0 1 eth-port

**Output:**
```
  --------------------------------------------------------------------------
  ONT-ID   ONT      ONT       Speed(Mbps)   Duplex   LinkState  RingStatus
           port-ID  Port-type    
  --------------------------------------------------------------------------
       1         1         GE 1000          full     up         noloop    
       1         2         GE -             -        down       noloop    
       1         3        ETH -             -        -          -         
  --------------------------------------------------------------------------
```

**Help:** execute the command "display ont port state 0 1 eth-port"

**Prompt:**
- huawei_smartax>
- huawei_smartax#

### display ont port vlan 0 1 byport eth 0

**Output:**
```
  --------------------------------------------------------------------
  Port   Port C-VLAN C-PRI ETH-type   VLAN-type   S-VLAN S-PRI  S-PRI
  type   ID                                                     POLICY
  --------------------------------------------------------------------
  eth    1    -      2     -          Translation 1      7      -
  eth    2    -      2     -          Translation 1      7      -
  --------------------------------------------------------------------
  Native VLAN     : 1
  Default priority: 0
  Downstream mode : operation
  Mismatch policy : discard
  --------------------------------------------------------------------
  Notes: IPoE indicates IPv4-IPoE,  * indicates transparent attribute of
  the vlan, In the Ethernet encapsulation list, the hexadecimal digits
  indicate the user-defined Ethernet encapsulation type
```

**Help:** execute the command "display ont port vlan 0 1 byport eth 0"

**Prompt:**
- huawei_smartax>
- huawei_smartax#

### display ont port vlan 0 1 byvlan 0

**Output:**
```
  --------------------------------------------------------------------
  C-VLAN C-PRI ETH-type   VLAN-type   Port   Port S-VLAN S-PRI  S-PRI
                                      type   ID                 POLICY
  --------------------------------------------------------------------
  100    -     IPoE       QINQ        ETH    2    20     3        DSCP
  100    -     0x6321     QINQ        ETH    4    70     -        -
  --------------------------------------------------------------------
  Notes: IPoE indicates IPv4-IPoE, * indicates transparent attribute of
  the vlan, In the Ethernet encapsulation list, the hexadecimal digits
  indicate the user-defined Ethernet encapsulation type
```

**Help:** execute the command "display ont port vlan 0 1 byvlan 0"

**Prompt:**
- huawei_smartax>
- huawei_smartax#

### display ont snmp-profile 0 all

**Output:**
```
  --------------------------------------------------------------------
  ONT ID     SNMP profile ID     SNMP profile name
  --------------------------------------------------------------------
       1              1          snmp-profile_1
       2              1          snmp-profile_1
  --------------------------------------------------------------------
```

**Help:** execute the command "display ont snmp-profile 0 all"

**Prompt:**
- huawei_smartax>
- huawei_smartax#

### display ont version summary 0

**Output:**
```
  During the course of print ,press CTRL_C to break
  -----------------------------------------------------------------------------
  The number of configured ONT   :6
  The number of online ONT       :6
  The number of offline ONT      :0
  The number of no registered ONT:0
  -----------------------------------------------------------------------------
  Access Vendor  ONT Model                Software          Online   Offline
  Type   ID                               Version           Number   Number
  -----------------------------------------------------------------------------
  GPON   HWTC    A123-G                  A1A012A01A012     2        0    
  GPON   HWTC    A123B                   A1A012A01A013     3        0    
  GPON   HWTC    A123A                   A1A012A01A014     1        0    
  -----------------------------------------------------------------------------
```

**Help:** execute the command "display ont version summary 0"

**Prompt:**
- huawei_smartax>
- huawei_smartax#

### display ont wan-info 0 1 2 0

**Output:**
```
  ---------------------------------------------------------------------
  F/S/P                      : 0/1/0
  ONT ID                     : 0     
  ---------------------------------------------------------------------
  Index                      : 1
  Name                       : OLT_1
  Service type               : Tr069
  Connection type            : IP routed
  IPv4 Connection status     : Connected
  IPv4 access type           : Static
  IPv4 address               : 1.1.1.1
  Subnet mask                : 255.255.254.0
  Default gateway            : 1.1.1.2
  Primary DNS                : 8.8.8.8
  Secondary DNS              : 8.8.4.4
  Manage VLAN                : 1000
  Manage priority            : 5
  Multicast VLAN             : -
  NAT switch                 : Disable
  Option60                   : No
  Switch                     : Enable
  MAC address                : AAAA-AAAA-AAAA
  Priority policy            : Specified
  L2 encap-type              : IPoE  
  IPv4 switch                : Enable
  IPv6 switch                : Disable
  Prefix                     : -
  Prefix access mode         : Invalid
  Prefix preferred time      : -
  Prefix valid time          : -
  IPv6 Connection status     : Invalid
  IPv6 address               : -
  IPv6 Primary DNS           : -
  IPv6 Secondary DNS         : -
  IPv6 Multicast VLAN        : -
  IPv6 address status        : Invalid
  IPv6 address access mode   : Invalid
  IPv6 address preferred time: -
  IPv6 address valid time    : -
  DS-Lite Mode               : Invalid
  DS-Lite peer address       : -
  ---------------------------------------------------------------------
  Index                      : 2
  Name                       : OLT_2
  Service type               : Voip
  Connection type            : IP routed
  IPv4 Connection status     : Connected
  IPv4 access type           : Static
  IPv4 address               : 2.2.2.2
  Subnet mask                : 3.3.3.3
  Default gateway            : 5.5.5.5
  Primary DNS                : 8.8.8.8
  Secondary DNS              : 8.8.4.4
  Manage VLAN                : 3000
  Manage priority            : 5
  Multicast VLAN             : -
  NAT switch                 : Disable
  Option60                   : No
  Switch                     : Enable
  MAC address                : AAAA-AAAA-AAAA
  Priority policy            : Specified
  L2 encap-type              : IPoE
  IPv4 switch                : Enable
  IPv6 switch                : Disable
  Prefix                     : -
  Prefix access mode         : Invalid
  Prefix preferred time      : -
  Prefix valid time          : -
  IPv6 Connection status     : Invalid
  IPv6 address               : -
  IPv6 Primary DNS           : -
  IPv6 Secondary DNS         : -
  IPv6 Multicast VLAN        : -     
  IPv6 address status        : Invalid
  IPv6 address access mode   : Invalid
  IPv6 address preferred time: -
  IPv6 address valid time    : -
  DS-Lite Mode               : Invalid
  DS-Lite peer address       : -
  ---------------------------------------------------------------------
  Index                      : 3
  Name                       : PATATA
  Service type               : Internet
  Connection type            : IP bridged
  IPv4 Connection status     : Connected
  IPv4 access type           : Invalid
  IPv4 address               : -
  Subnet mask                : -
  Default gateway            : -
  Primary DNS                : -
  Secondary DNS              : -
  Manage VLAN                : 3002
  Manage priority            : 0
  Multicast VLAN             : -
  NAT switch                 : Disable
  Option60                   : No
  Switch                     : Enable
  MAC address                : --------------
  Priority policy            : Specified
  L2 encap-type              : IPoE
  IPv4 switch                : Enable
  IPv6 switch                : Disable
  Prefix                     : -
  Prefix access mode         : Invalid
  Prefix preferred time      : -
  Prefix valid time          : -
  IPv6 Connection status     : Invalid
  IPv6 address               : -
  IPv6 Primary DNS           : -
  IPv6 Secondary DNS         : -
  IPv6 Multicast VLAN        : -
  IPv6 address status        : Invalid
  IPv6 address access mode   : Invalid
  IPv6 address preferred time: -
  IPv6 address valid time    : -
  DS-Lite Mode               : Invalid
  DS-Lite peer address       : -
  ---------------------------------------------------------------------
  Index                      : 4
  Name                       : PATATA_2
  Service type               : Internet
  Connection type            : IP bridged
  IPv4 Connection status     : Connected
  IPv4 access type           : Invalid
  IPv4 address               : -
  Subnet mask                : -
  Default gateway            : -
  Primary DNS                : -
  Secondary DNS              : -
  Manage VLAN                : 3003
  Manage priority            : 0
  Multicast VLAN             : -
  NAT switch                 : Disable
  Option60                   : No
  Switch                     : Enable
  MAC address                : --------------
  Priority policy            : Specified
  L2 encap-type              : IPoE
  IPv4 switch                : Enable
  IPv6 switch                : Disable
  Prefix                     : -
  Prefix access mode         : Invalid
  Prefix preferred time      : -
  Prefix valid time          : -
  IPv6 Connection status     : Invalid
  IPv6 address               : -
  IPv6 Primary DNS           : -
  IPv6 Secondary DNS         : -
  IPv6 Multicast VLAN        : -
  IPv6 address status        : Invalid
  IPv6 address access mode   : Invalid
  IPv6 address preferred time: -
  IPv6 address valid time    : -
  DS-Lite Mode               : Invalid
  DS-Lite peer address       : -
  ---------------------------------------------------------------------
  Index                      : 5
  Name                       : INTERNET_5
  Service type               : Internet
  Connection type            : IP bridged
  IPv4 Connection status     : Connected
  IPv4 access type           : Invalid
  IPv4 address               : -
  Subnet mask                : -
  Default gateway            : -
  Primary DNS                : -
  Secondary DNS              : -
  Manage VLAN                : 3001
  Manage priority            : 0     
  Multicast VLAN             : -
  NAT switch                 : Disable
  Option60                   : No
  Switch                     : Enable
  MAC address                : --------------
  Priority policy            : Specified
  L2 encap-type              : IPoE
  IPv4 switch                : Enable
  IPv6 switch                : Disable
  Prefix                     : -
  Prefix access mode         : Invalid
  Prefix preferred time      : -
  Prefix valid time          : -
  IPv6 Connection status     : Invalid
  IPv6 address               : -
  IPv6 Primary DNS           : -
  IPv6 Secondary DNS         : -
  IPv6 Multicast VLAN        : -
  IPv6 address status        : Invalid
  IPv6 address access mode   : Invalid
  IPv6 address preferred time: -
  IPv6 address valid time    : -
  DS-Lite Mode               : Invalid
  DS-Lite peer address       : -     
  ---------------------------------------------------------------------
  Index                      : 6
  Name                       : INTERNET_7
  Service type               : Internet
  Connection type            : IP bridged
  IPv4 Connection status     : Connected
  IPv4 access type           : Invalid
  IPv4 address               : -
  Subnet mask                : -
  Default gateway            : -
  Primary DNS                : -
  Secondary DNS              : -
  Manage VLAN                : 3005
  Manage priority            : 0
  Multicast VLAN             : -
  NAT switch                 : Disable
  Option60                   : No
  Switch                     : Enable
  MAC address                : --------------
  Priority policy            : Specified
  L2 encap-type              : IPoE
  IPv4 switch                : Enable
  IPv6 switch                : Disable
  Prefix                     : -     
  Prefix access mode         : Invalid
  Prefix preferred time      : -
  Prefix valid time          : -
  IPv6 Connection status     : Invalid
  IPv6 address               : -
  IPv6 Primary DNS           : -
  IPv6 Secondary DNS         : -
  IPv6 Multicast VLAN        : -
  IPv6 address status        : Invalid
  IPv6 address access mode   : Invalid
  IPv6 address preferred time: -
  IPv6 address valid time    : -
  DS-Lite Mode               : Invalid
  DS-Lite peer address       : -
  ---------------------------------------------------------------------
```

**Help:** execute the command "display ont wan-info 0 1 2 0"

**Prompt:**
- huawei_smartax>
- huawei_smartax#

### display ont wlan-info 0 1 2 0

**Output:**
```
  ------------------------------------------------------------------------------
  F/S/P                    : 0/1/2
  ONT ID                   : 0
  The total number of SSID : 2
  ------------------------------------------------------------------------------
  SSID Index               : 1
  SSID                     : TEST_2_4G
  Wireless Standard        : IEEE 802.11b/g/n
  Administrative state     : enable
  Operational state        : up
  Maximum associate number : 64
  Current associate number : 2
  ------------------------------------------------------------------------------
  SSID Index               : 5
  SSID                     : TEST_5_G
  Wireless Standard        : IEEE 802.11ac
  Administrative state     : enable
  Operational state        : up
  Maximum associate number : 64
  Current associate number : 0
  ------------------------------------------------------------------------------
```

**Help:** execute the command "display ont wlan-info 0 1 2 0"

**Prompt:**
- huawei_smartax>
- huawei_smartax#

### display ont wlan-status 0 1

**Output:**
```
  Command is being executed. Please wait
  ----------------------------------------------------------------------------- 
  Channel Information:
  -----------------------------------------------------------------------------
  Channel Num                     : 1
  AP ID                           : ONU
  AP Number                       : 1
  Interference degree             : 33
  -----------------------------------------------------------------------------
  Channel Num                     : 2
  AP ID                           : ONU
  AP Number                       : 2
  Interference degree             : 36
  -----------------------------------------------------------------------------
  Channel Num                     : 3
  AP ID                           : ONU
  AP Number                       : 2
  Interference degree             : 48
  -----------------------------------------------------------------------------
  Channel Num                     : 4
  AP ID                           : ONU
  AP Number                       : 0
  Interference degree             : 47
  -----------------------------------------------------------------------------
  Channel Num                     : 5
  AP ID                           : ONU
  AP Number                       : 3
  Interference degree             : 41
  -----------------------------------------------------------------------------
  Channel Num                     : 6
  AP ID                           : ONU
  AP Number                       : 1
  Interference degree             : 37
  -----------------------------------------------------------------------------
  Channel Num                     : 7
  AP ID                           : ONU
  AP Number                       : 0
  Interference degree             : 49
  -----------------------------------------------------------------------------
  Channel Num                     : 8
  AP ID                           : ONU
  AP Number                       : 2
  Interference degree             : 48
  -----------------------------------------------------------------------------
  Channel Num                     : 9
  AP ID                           : ONU
  AP Number                       : 3
  Interference degree             : 127
  -----------------------------------------------------------------------------
  Channel Num                     : 10
  AP ID                           : ONU
  AP Number                       : 2
  Interference degree             : 144
  -----------------------------------------------------------------------------
  Channel Num                     : 11
  AP ID                           : ONU
  AP Number                       : 16
  Interference degree             : 149
  -----------------------------------------------------------------------------
  Channel Num                     : 12
  AP ID                           : ONU
  AP Number                       : 0
  Interference degree             : 109
  -----------------------------------------------------------------------------
  Channel Num                     : 13
  AP ID                           : ONU
  AP Number                       : 0
  Interference degree             : 78
  ----------------------------------------------------------------------------- 
  Statistics of SSID:
  ----------------------------------------------------------------------------- 
  AP ID                           : ONU
  SSID Index                      : 1
  SSID                            : Test
  Sent Packets                    : 0
  Sent Error Packets              : 0
  Sent Discard Packets            : 0
  Received Packets                : 0
  Received Error Packets          : 0
  Received Discard Packets        : 0
  Transmission Quality Level      : Good
  ----------------------------------------------------------------------------- 
  STA Information:
  ----------------------------------------------------------------------------- 
  AP ID                           : ONU
  SSID Index                      : 1
  SSID                            : Test
  STA Mac Address                 : 0000-1111-2222
  TxRate                          : 0
  RxRate                          : 0
  RSSI                            : 0
  SNR                             : 0
  Signal Quality Level            : Good
 ------------------------------------------------------------------------------ 
```

**Help:** execute the command "display ont wlan-status 0 1"

**Prompt:**
- huawei_smartax>
- huawei_smartax#

### display port info

**Output:**
```
  -----------------------------------------------------------
  F/S/P                                      0/0/0
  Min distance(km)                           0
  Max distance(km)                           20
  Max guaranteed bandwidth(kbps)             -
  Left guaranteed bandwidth(kbps)            1000000
  Number of T-CONTs                          0
  Autofind                                   Enable
  FEC check                                  Disable
  Admin State                                On
  ONT encryption key switching interval(m)   1440
  PON-ID switch                              Disable
  PON-ID identifier                          1
  Jumbo frame switch                         Disable
  Port MTU(bytes)                            1024
  Surplus bandwidth assignment               Disable
  Best-effort bandwidth assignment           -
  Traffic alarm-profile ID                   -
  ONT online power threshold(dBm)            -
  Low-latency                                no
  Multichannel low latency                   Disable
  Optical module work mode                   Standard
  -----------------------------------------------------------
  Channel 0 Information              
  -----------------------------------------------------------
  Channel Type                               GPON
  Online ONT number threshold                Disable
  -----------------------------------------------------------
```

**Help:** execute the command "display port info"

**Prompt:**
- huawei_smartax>
- huawei_smartax#

### display service-port all

**Output:**
```
Switch-Oriented Flow List
  -----------------------------------------------------------------------------
   INDEX VLAN VLAN     PORT F/ S/ P VPI  VCI   FLOW  FLOW       RX   TX   STATE
         ID   ATTR     TYPE                    TYPE  PARA
  -----------------------------------------------------------------------------
    5827 2    common   gpon 0/1 /0  0    1     vlan  2          -    -    up   
  -----------------------------------------------------------------------------
   Total : 1  (Up/Down :    1/0)
   Note : F--Frame, S--Slot, P--Port,
          VPI indicates ONT ID for PON, VCI indicates GEM index for GPON,
          v/e--vlan/encap, pritag--priority-tagged,
          ppp--pppoe, ip--ipoe, ip4--ipv4oe, ip6--ipv6oe, vxl--vxlan.
          When FLOW TYPE is plist, the value of FLOW PARA is a byte in
          hexadecimal format and indicates a priority list. Eight bits
          of its binary value indicate priorities 0-7 from the least
          significant bit to the most significant bit. Value 1 indicates
          that the priority is used. For example, if FLOW PARA is 0x23 and
          its binary format is 0010 0011, priorities 0, 1 and 5 are used
```

**Help:** execute the command "display service-port all"

**Prompt:**
- huawei_smartax>
- huawei_smartax#

### display sysman service state

**Output:**
```
  ---------------------------------------------------------------------------
  Network service                                   Port           State
  ---------------------------------------------------------------------------
  telnet                                            23             disable
  trace                                             1026           disable
  ssh                                               22             enable
  snmp                                              161            enable
  ftp-client                                        ----           ----
  sftp-client                                       ----           ----
  ntp                                               123            enable
  radius                                            ----           enable
  dhcp-relay                                        67             disable
  dhcpv6-relay                                      547            disable
  ntp6                                              123            disable
  ipdr                                              4737           enable
  twamp                                             4294967295     enable
  netconf                                           830            enable
  telnetv6                                          23             disable
  sshv6                                             22             disable
  snmpv6                                            161            disable
  web-proxy                                         8024           disable
  portal                                            2000           disable
  capwap                                            5246           disable
  ---------------------------------------------------------------------------
```

**Help:** execute the command "display sysman service state"

**Prompt:**
- huawei_smartax>
- huawei_smartax#

### display sysuptime

**Output:**
```
  System up time: 11 day 22 hour 5 minute 17 second
```

**Help:** execute the command "display sysuptime"

**Prompt:**
- huawei_smartax>
- huawei_smartax#

### display temperature

**Output:**
```
  SlotID:  4      BoardName: H805GPFD       Temperature:   57C( 134F)

  SlotID:  5      BoardName: H808EPSD       Temperature:   59C( 138F)

  SlotID:  7      BoardName: H802SCUN       Temperature:   69C( 156F)

  SlotID:  8      BoardName: H802SCUN       Temperature:   67C( 152F)

  SlotID: 11      BoardName: H807GPBD       Temperature:   55C( 131F)

  SlotID: 18      BoardName: H801X2CS       Temperature:   38C( 100F)
```

**Help:** execute the command "display temperature"

**Prompt:**
- huawei_smartax>
- huawei_smartax#

### display version

**Output:**
```

  VERSION : AB1234C342A123D23
  PATCH   : QEF227
  PRODUCT : MA5608T
 
  Active Mainboard Running Area Information: 
  --------------------------------------------------
  Current Program Area : Area A 
  Current Data Area : Area A
 
  Program Area A Version : AB1234C342A123D23 
  Program Area B Version : AB1234C342A123D23
 
  Data Area A Version : AB1234C342A123D23 
  Data Area B Version : AB1234C342A123D23 
  --------------------------------------------------
 
  Standby Mainboard Running Area Information: 
  --------------------------------------------------
  Current Program Area : Area A 
  Current Data Area : Area A
 
  Program Area A Version : AB1234C342A123D23 
  Program Area B Version : AB1234C342A123D23
 
  Data Area A Version : AB1234C342A123D23 
  Data Area B Version : AB1234C342A123D23 
  --------------------------------------------------
 
  Uptime is 20 day(s), 23 hour(s), 19 minute(s), 16 second(s)
```

**Help:** execute the command "display version"

**Prompt:**
- huawei_smartax>
- huawei_smartax#

### enable

**Output:** None

**Help:** enter enable mode

**Prompt:**
- huawei_smartax>

### ont add

**Output:**
```
  Number of ONTs that can be added: 1, success: 1
  PortID :6, ONTID :2
```

**Help:** execute the command "ont add"

**Prompt:**
- huawei_smartax>
- huawei_smartax#

### port vlan

**Output:**
```
Set ONT port(s) VLAN configuration, success: 1, failed: 0
```

**Help:** execute the command "port vlan"

**Prompt:**
- huawei_smartax>
- huawei_smartax#

### scroll

**Output:** None

**Help:** disables the paging so the output is complete always

**Prompt:**
- huawei_smartax>
- huawei_smartax#

### undo smart

**Output:** None

**Help:** undo the command completion mode (smart mode)

**Prompt:**
- huawei_smartax>
- huawei_smartax#

