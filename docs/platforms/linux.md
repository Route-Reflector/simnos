# linux


!!! warning
    This is automatically generated. In case of any issues,
    please refer to the source code or, even better,
    open an issue on the GitHub repository. Thanks! 🤗📖
## Commands

### enable

**Output:** None

**Help:** enter enable mode

**Prompt:**
- linux$

### ip vrf show

**Output:**
```
Name              Table
-----------------------
vrf-blue            10
vrf-red             20

```

**Help:** execute the command "ip vrf show"

**Prompt:**
- linux$
- linux#

### ip address show

**Output:**
```
1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN group default qlen 1000
    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
    inet 127.0.0.1/8 scope host lo
       valid_lft forever preferred_lft forever
2: ens32: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc fq_codel state UP group default qlen 1000
    link/ether 00:0c:29:56:07:1b brd ff:ff:ff:ff:ff:ff
    inet 192.168.131.128/24 brd 192.168.131.255 scope global dynamic ens32
       valid_lft 1307sec preferred_lft 1307sec
3: gpd0: <POINTOPOINT,MULTICAST,NOARP,UP,LOWER_UP> mtu 1400 qdisc fq_codel state UNKNOWN group default qlen 500
    link/none
    inet 10.20.20.12/32 scope global gpd0
       valid_lft forever preferred_lft forever
4: br-218f5e637867: <NO-CARRIER,BROADCAST,MULTICAST,UP> mtu 1500 qdisc noqueue state DOWN group default
    link/ether 02:42:5d:d7:c2:c1 brd ff:ff:ff:ff:ff:ff
    inet 172.21.0.1/16 brd 172.21.255.255 scope global br-218f5e637867
       valid_lft forever preferred_lft forever
5: vrf-blue: <NOARP,MASTER,UP,LOWER_UP> mtu 65575 qdisc noqueue state UP group default qlen 1000
    link/ether ee:be:e9:28:70:69 brd ff:ff:ff:ff:ff:ff
6: brblue: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue master vrf-blue state UNKNOWN group default qlen 1000
    link/ether 66:37:23:9b:9e:e4 brd ff:ff:ff:ff:ff:ff
    inet 10.0.0.1/24 scope global brblue
       valid_lft forever preferred_lft forever
    inet 192.168.0.1/25 scope global brred
       valid_lft forever preferred_lft forever

```

**Help:** execute the command "ip address show"

**Prompt:**
- linux$
- linux#

### ip link show

**Output:**
```
1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN mode DEFAULT group default qlen 1000
    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
 2: ens32: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc fq_codel state UP mode DEFAULT group default qlen 1000
    link/ether 00:0c:29:56:07:1b brd ff:ff:ff:ff:ff:ff
 3: gpd0: <POINTOPOINT,MULTICAST,NOARP,UP,LOWER_UP> mtu 1400 qdisc fq_codel state UNKNOWN mode DEFAULT group default qlen 500
    link/none
4: br-218f5e637867: <NO-CARRIER,BROADCAST,MULTICAST,UP> mtu 1500 qdisc noqueue state DOWN mode DEFAULT group default
    link/ether 02:42:5d:d7:c2:c1 brd ff:ff:ff:ff:ff:ff
5: vrf-blue: <NOARP,MASTER,UP,LOWER_UP> mtu 65575 qdisc noqueue state UP mode DEFAULT group default qlen 1000
    link/ether ee:be:e9:28:70:69 brd ff:ff:ff:ff:ff:ff
 6: vrf-red: <NOARP,MASTER,UP,LOWER_UP> mtu 65575 qdisc noqueue state UP mode DEFAULT group default qlen 1000
    link/ether d6:a6:dd:0d:d5:f9 brd ff:ff:ff:ff:ff:ff
 7: brblue: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue master vrf-blue state UNKNOWN mode DEFAULT group default qlen 1000
    link/ether 66:37:23:9b:9e:e4 brd ff:ff:ff:ff:ff:ff
8: brred: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue master vrf-red state UNKNOWN mode DEFAULT group default qlen 1000
    link/ether da:ca:17:97:f5:34 brd ff:ff:ff:ff:ff:ff

```

**Help:** execute the command "ip link show"

**Prompt:**
- linux$
- linux#

### arp -a

**Output:**
```
? (192.168.13.197) at 00:04:4b:cc:9c:ba [ether] on eth1.100
? (192.168.10.100) at <incomplete> on eth1.10
? (192.168.13.252) at 5c:e2:8c:fc:a4:74 [ether] on eth1.100
esxi (192.168.13.5) at 00:e0:67:05:9d:5a [ether] on eth1.100
 ? (192.168.13.253) at dc:f7:19:cd:d6:c4 [ether] on eth1.100
? (192.168.123.199) at 00:0f:c9:0e:c8:ec [ether] on eth0.21
? (192.168.10.52) at <incomplete> on eth1.10
? (192.168.10.7) at 00:0c:29:02:3b:93 [ether] on eth1.10
? (192.168.10.249) at 00:0c:29:bb:5f:a2 [ether] on eth1.10

```

**Help:** execute the command "arp -a"

**Prompt:**
- linux$
- linux#

### ip route show

**Output:**
```
default via 10.0.0.4 dev brblue
unreachable default metric 4278198272
 broadcast 10.0.0.0 dev brblue proto kernel scope link src 10.0.0.1
10.0.0.0/24 dev brblue proto kernel scope link src 10.0.0.1
local 10.0.0.1 dev brblue proto kernel scope host src 10.0.0.1
broadcast 10.0.0.255 dev brblue proto kernel scope link src 10.0.0.1
192.168.0.0/24 via 10.0.0.2 dev brblue
192.168.131.2 dev ens32 proto dhcp scope link src 192.168.131.128 metric 100

```

**Help:** execute the command "ip route show"

**Prompt:**
- linux$
- linux#

### bluetoothctl show

**Output:**
```
Controller AA:AA:AA:AA:AA:AA (public)
        Manufacturer: 0x005d (93)
        Version: 0x0a (10)
        Name: ntc-AA-AAAA
        Alias: ntc-AA-AAAA
        Class: 0x00000000 (0)
        Powered: no
        Discoverable: no
        DiscoverableTimeout: 0x000000b4 (180)
        Pairable: yes
        UUID: Message Notification Se.. (00001133-0000-1000-8000-00805f9b34fb)
        UUID: A/V Remote Control        (0000110e-0000-1000-8000-00805f9b34fb)
        UUID: OBEX Object Push          (00001105-0000-1000-8000-00805f9b34fb)
        UUID: Message Access Server     (00001132-0000-1000-8000-00805f9b34fb)
        UUID: PnP Information           (00001200-0000-1000-8000-00805f9b34fb)
        UUID: IrMC Sync                 (00001104-0000-1000-8000-00805f9b34fb)
        UUID: Vendor specific           (00005005-0000-1000-8000-0002ee000001)
        UUID: A/V Remote Control Target (0000110c-0000-1000-8000-00805f9b34fb)
        UUID: Generic Attribute Profile (00001801-0000-1000-8000-00805f9b34fb)
        UUID: Phonebook Access Server   (0000112f-0000-1000-8000-00805f9b34fb)
        UUID: Audio Sink                (0000110b-0000-1000-8000-00805f9b34fb)
        UUID: Device Information        (0000180a-0000-1000-8000-00805f9b34fb)
        UUID: Generic Access Profile    (00001800-0000-1000-8000-00805f9b34fb)
        UUID: Handsfree Audio Gateway   (0000111f-0000-1000-8000-00805f9b34fb)
        UUID: Audio Source              (0000110a-0000-1000-8000-00805f9b34fb)
        UUID: OBEX File Transfer        (00001106-0000-1000-8000-00805f9b34fb)
        UUID: Handsfree                 (0000111e-0000-1000-8000-00805f9b34fb)
        Modalias: usb:v1D6Bp0246d0548
        Discovering: no
        Roles: central
        Roles: peripheral
Advertising Features:
        ActiveInstances: 0x00 (0)
        SupportedInstances: 0x04 (4)
        SupportedIncludes: tx-power
        SupportedIncludes: appearance
        SupportedIncludes: local-name
        SupportedSecondaryChannels: 1M
        SupportedSecondaryChannels: 2M
        SupportedSecondaryChannels: Coded

```

**Help:** execute the command "bluetoothctl show"

**Prompt:**
- linux$
- linux#

### dmidecode -t bios

**Output:**
```
# dmidecode 1.12
SMBIOS 1.1 present.

Handle 0x0000, DMI type 0, 24 bytes
BIOS Information
	Vendor: Dell
	Version: O11   
	Release Date: 01/11/1011
	Address: 0xA1110
	Runtime Size: 111111 bytes
	ROM Size: 2048 kB
	Characteristics:
		PCI is supported
		PNP is supported
		APM is supported
		BIOS is upgradeable
		BIOS shadowing is allowed
		ESCD support is available
		Boot from CD is supported
		Selectable boot is supported
		BIOS ROM is socketed
		EDD is supported
		Print screen service is supported (int 5h)
		8042 keyboard services are supported (int 9h)
		Serial services are supported (int 14h)
		Printer services are supported (int 17h)
		CGA/mono video services are supported (int 10h)
		ACPI is supported
		USB legacy is supported
		Smart battery is supported
		 BIOS boot specification is supported
		Function key-initiated network boot is supported
		Targeted content distribution is supported

```

**Help:** execute the command "dmidecode -t bios"

**Prompt:**
- linux$
- linux#

### dmidecode -t memory

**Output:**
```
# dmidecode 1.11
SMBIOS 1.1 present.

Handle 0x001A, DMI type 11, 11 bytes
Physical Memory Array
	Location: System Board Or Motherboard
	 Use: System Memory
	Error Correction Type: Multi-bit ECC
	Maximum Capacity: 16 GB
	Error Information Handle: Not Provided
	Number Of Devices: 4

Handle 0x001A, DMI type 11, 11 bytes
Memory Device
	Array Handle: 0x001A
	Error Information Handle: No Error
	Total Width: 10 bits
	Data Width: 10 bits
	Size: 1111 MB
	Form Factor: DIMM
	Set: 1
	Locator: DIMM1A
	Bank Locator: Not Specified
	Type: DDR2
	Type Detail: Synchronous
	Speed: 1111 MHz
	Manufacturer: Not Specified
	Serial Number: Not Specified
	Asset Tag: Not Specified
	Part Number: Not Specified
	Rank: Unknown

Handle 0x001A, DMI type 11, 11 bytes
Memory Device
	Array Handle: 0x001A
	Error Information Handle: No Error
	Total Width: Unknown
	Data Width: Unknown
	Size: No Module Installed
	Form Factor: DIMM
	Set: 1
	Locator: DIMM1C
	Bank Locator: Not Specified
	Type: Reserved
	Type Detail: Synchronous
	Speed: Unknown
	Manufacturer: Not Specified
	Serial Number: Not Specified
	Asset Tag: Not Specified
	Part Number: Not Specified
	Rank: Unknown

Handle 0x001A, DMI type 11, 11 bytes
Memory Device
	Array Handle: 0x001A
	Error Information Handle: No Error
	Total Width: Unknown
	Data Width: Unknown
	Size: No Module Installed
	Form Factor: DIMM
	Set: 1
	Locator: DIMM1B
	Bank Locator: Not Specified
	Type: Reserved
	Type Detail: Synchronous
	Speed: Unknown
	Manufacturer: Not Specified
	Serial Number: Not Specified
	Asset Tag: Not Specified
	Part Number: Not Specified
	Rank: Unknown

Handle 0x001A, DMI type 11, 11 bytes
Memory Device
	Array Handle: 0x001A
	Error Information Handle: No Error
	Total Width: Unknown
	Data Width: Unknown
	Size: No Module Installed
	Form Factor: DIMM
	Set: 1
	Locator: DIMM1D
	Bank Locator: Not Specified
	Type: Reserved
	Type Detail: Synchronous
	Speed: Unknown
	Manufacturer: Not Specified
	Serial Number: Not Specified
	Asset Tag: Not Specified
	Part Number: Not Specified
	Rank: Unknown

```

**Help:** execute the command "dmidecode -t memory"

**Prompt:**
- linux$
- linux#

### dmidecode -t processor

**Output:**
```
# dmidecode 1.1
SMBIOS 1.1 present.

Handle 0x0004, DMI type 4, 42 bytes
Processor Information
	Socket Designation: CPU 1   
	Type: Central Processor
	Family: Core 2 Quad
	Manufacturer: AMD
	ID: AA AA AA AA AA AA AA AA
	Signature: Type 0, Family 1, Model 2, Stepping 3
	Flags:
		 FPU (Floating-point unit on-chip)
		VME (Virtual mode extension)
		DE (Debugging extension)
		PSE (Page size extension)
		TSC (Time stamp counter)
		MSR (Model specific registers)
		PAE (Physical address extension)
	 	MCE (Machine check exception)
		CX8 (CMPXCHG8 instruction supported)
	 	APIC (On-chip APIC hardware supported)
		SEP (Fast system call)
		MTRR (Memory type range registers)
		PGE (Page global enable)
		MCA (Machine check architecture)
		CMOV (Conditional move instruction supported)
		 PAT (Page attribute table)
		PSE-36 (36-bit page size extension)
		CLFSH (CLFLUSH instruction supported)
		DS (Debug store)
		ACPI (ACPI supported)
		MMX (MMX technology supported)
		FXSR (FXSAVE and FXSTOR instructions supported)
		SSE (Streaming SIMD extensions)
		SSE2 (Streaming SIMD extensions 2)
		SS (Self-snoop)
		HTT (Multi-threading)
		TM (Thermal monitor supported)
		PBE (Pending break enabled)
	Version: Intel(R) AAAA(R) CPU           A1111  @ 1.10GHz
	Voltage: 1.2 V
	External Clock: 133 MHz
	 Max Speed: 1100 MHz
	Current Speed: 1100 MHz
	Status: Populated, Enabled
	Upgrade: Slot 1
	L1 Cache Handle: 0x0001
	L2 Cache Handle: 0x0002
	L3 Cache Handle: 0x0003
	Serial Number: Not Specified
	Asset Tag: Not Specified
	Part Number: Not Specified
	Core Count: 1
	Core Enabled: 1
	Thread Count: 1
	Characteristics:
		128-bit capable

```

**Help:** execute the command "dmidecode -t processor"

**Prompt:**
- linux$
- linux#

### dmidecode -t system

**Output:**
```
# dmidecode 1.11
SMBIOS 1.1 present.

Handle 0x0001, DMI type 1, 11 bytes
System Information
	Manufacturer: HP
	Product Name: ProG4 Deepseek G6
	Version:        
	Serial Number: AA111100AA
	UUID: 1111AA1A-AA1A-11A1-1AAA-A1111AAAA1AA
	Wake-up Type: Power Switch
	SKU Number: 000000-000
	Family: Not Specified

Handle 0x0011, DMI type 12, 1 bytes
System Configuration Options
	Option 1: Jumper settings can be described here.

Handle 0x0011, DMI type 11, 11 bytes
System Event Log
	Area Length: 32 bytes
	Header Start Offset: 0x0000
	Header Length: 32 bytes
	Data Start Offset: 0x0010
	Access Method: General-purpose non-volatile data functions
	Access Address: 0x0000
	Status: Valid, Not Full
	Change Token: 0x0000001D
	Header Format: Type 1
	Supported Log Type Descriptors: 3
	Descriptor 1: POST error
	Data Format 1: POST results bitmap
	Descriptor 2: Single-bit ECC memory error
	Data Format 2: Multiple-event
	Descriptor 3: Multi-bit ECC memory error
	Data Format 3: Multiple-event

Handle 0x001A, DMI type 23, 13 bytes
System Reset
	Status: Enabled
	Watchdog Timer: Present
	Boot Option: Do Not Reboot
	Boot Option On Limit: Do Not Reboot
	Reset Count: Unknown
	Reset Limit: Unknown
	Timer Interval: Unknown
	Timeout: Unknown

Handle 0x001A, DMI type 32, 20 bytes
System Boot Information
	Status: No errors detected

```

**Help:** execute the command "dmidecode -t system"

**Prompt:**
- linux$
- linux#

### iwconfig

**Output:**
```
lo        no wireless extensions.

eth0      no wireless extensions.

wlan0     IEEE 802.11  ESSID:"My_home"  
          Mode:Managed  Frequency:5.18 GHz  Access Point: AA:AA:AA:AA:AA:AA   
          Bit Rate=24 Mb/s   Tx-Power=31 dBm   
          Retry short limit:7   RTS thr:off   Fragment thr:off
          Encryption key:off
          Power Management:on
          Link Quality=56/70  Signal level=-54 dBm  
          Rx invalid nwid:0  Rx invalid crypt:0  Rx invalid frag:0
          Tx excessive retries:155  Invalid misc:0   Missed beacon:0

wlan1     IEEE 802.11  ESSID:off/any  
          Mode:Managed  Access Point: Not-Associated   Tx-Power=20 dBm   
          Retry short limit:7   RTS thr:off   Fragment thr:off
          Power Management:off

wlan2     IEEE 802.11  ESSID:"My_other_home"  
          Mode:Managed  Frequency:5.22 GHz  Access Point: AA:AA:AA:AA:AA:AA   
          Bit Rate=200 Mb/s   Tx-Power=31 dBm   
          Retry short limit:7   RTS thr:off   Fragment thr:off
          Encryption key:off
          Power Management:on
          Link Quality=62/70  Signal level=-48 dBm  
          Rx invalid nwid:0  Rx invalid crypt:0  Rx invalid frag:0
          Tx excessive retries:7  Invalid misc:0   Missed beacon:0

wlan3     unassociated  Nickname:"<WIFI@REALTEK>"
          Mode:Managed  Frequency=5.18 GHz  Access Point: Not-Associated   
          Sensitivity:0/0  
          Retry:off   RTS thr:off   Fragment thr:off
          Power Management:off
          Link Quality:0  Signal level:0  Noise level:0
          Rx invalid nwid:0  Rx invalid crypt:0  Rx invalid frag:0
          Tx excessive retries:0  Invalid misc:0   Missed beacon:0
        
wlan4     IEEE 802.11AX  ESSID:"My_home"  Nickname:"<WIFI@REALTEK>"
          Mode:Managed  Frequency:5.18 GHz  Access Point: AA:AA:AA:AA:AA:AA   
          Bit Rate:574 Mb/s   Sensitivity:0/0  
          Retry:off   RTS thr:off   Fragment thr:off
          Power Management:off
          Link Quality=58/100  Signal level=58/100  Noise level=0/100
          Rx invalid nwid:0  Rx invalid crypt:0  Rx invalid frag:0
          Tx excessive retries:0  Invalid misc:0   Missed beacon:0

wlan5     IEEE 802.11bgn  ESSID:"HS"  Nickname:"<WIFI@REALTEK>"
          Mode:Managed  Frequency:2.452 GHz  Access Point: AA:AA:AA:AA:AA:AA   
          Bit Rate:300 Mb/s   Sensitivity:0/0  
          Retry:off   RTS thr:off   Fragment thr:off
          Power Management:off
          Link Quality=60/100  Signal level=60/100  Noise level=0/100
          Rx invalid nwid:0  Rx invalid crypt:0  Rx invalid frag:0
          Tx excessive retries:0  Invalid misc:0   Missed beacon:0

wlan6    IEEE 802.11  ESSID:"HS"  
          Mode:Managed  Frequency:2.452 GHz  Access Point: AA:AA:AA:AA:AA:AA   
          Bit Rate=72.2 Mb/s   Tx-Power=31 dBm   
          Retry short limit:7   RTS thr:off   Fragment thr:off
          Power Management:on
          Link Quality=62/70  Signal level=-48 dBm  
          Rx invalid nwid:0  Rx invalid crypt:0  Rx invalid frag:0
          Tx excessive retries:4  Invalid misc:0   Missed beacon:0

```

**Help:** execute the command "iwconfig"

**Prompt:**
- linux$
- linux#

### iwlist wlan0 scanning

**Output:**
```
wlan1     Scan completed :
          Cell 01 - Address: AA:AA:AA:AA:AA:AA
                    ESSID:""
                    Protocol:IEEE 802.11bgn
                    Mode:Master
                    Frequency:2.422 GHz (Channel 3)
                    Encryption key:on
                    Bit Rates:780 Mb/s
                    Extra:rsn_ie=30140100000fac040100000fac040100000fac020000
                    IE: IEEE 802.11i/WPA2 Version 1
                        Group Cipher : CCMP
                        Pairwise Ciphers (1) : CCMP
                        Authentication Suites (1) : PSK
                    Quality=0/100  Signal level=57/100  
                    Extra:fm=0002
          Cell 03 - Address: AA:AA:AA:AA:AA:AA
                    ESSID:"Awdin"
                    Protocol:IEEE 802.11bgn
                    Mode:Master
                    Frequency:2.422 GHz (Channel 3)
                    Encryption key:on
                    Bit Rates:780 Mb/s
                    Extra:rsn_ie=30140100000fac040100000fac040100000fac020000
                    IE: IEEE 802.11i/WPA2 Version 1
                        Group Cipher : CCMP
                        Pairwise Ciphers (1) : CCMP
                        Authentication Suites (1) : PSK
                    IE: Unknown: DD9F0050F204104A0001101044000102103B00010310470010BC329E001DD811B286010000000000011021001852616C696E6B20546563686E6F6C6F67792C20436F72702E1023001C52616C696E6B20576972656C6573732041636365737320506F696E74102400065254323836301042000831323334353637381054000800060050F20400011011000B52616C696E6B4150535F3010080002008C103C000101
                    Quality=36/100  Signal level=56/100  
                    Extra:fm=0003
          Cell 05 - Address: AA:AA:AA:AA:AA:AA
                    ESSID:"HS"
                    Protocol:IEEE 802.11bgn
                    Mode:Master
                    Frequency:2.452 GHz (Channel 9)
                    Encryption key:off
                    Bit Rates:300 Mb/s
                    Quality=59/100  Signal level=59/100  
                    Extra:fm=0003
          Cell 07 - Address: AA:AA:AA:AA:AA:AA
                    ESSID:"Some-SSID2"
                    Protocol:IEEE 802.11gn
                    Mode:Master
                    Frequency:2.462 GHz (Channel 11)
                    Encryption key:on
                    Bit Rates:1.17 Gb/s
                    Extra:rsn_ie=30140100000fac040100000fac040100000fac020000
                    IE: IEEE 802.11i/WPA2 Version 1
                        Group Cipher : CCMP
                        Pairwise Ciphers (1) : CCMP
                        Authentication Suites (1) : PSK
                    Quality=20/100  Signal level=72/100  
                    Extra:fm=0003
          Cell 49 - Address: AA:AA:AA:AA:AA:AA
                    ESSID:"Some-SSID"
                    Protocol:IEEE 802.11AC
                    Mode:Master
                    Frequency:5.805 GHz
                    Encryption key:on
                    Bit Rates:867 Mb/s
                    Extra:rsn_ie=30160100000fac040100000fac040100000fac023c000000
                    IE: IEEE 802.11i/WPA2 Version 1
                        Group Cipher : CCMP
                        Pairwise Ciphers (1) : CCMP
                        Authentication Suites (1) : PSK
                    IE: Unknown: DD5C0050F204104A00011010440001021049000600372A0001201054000800070050F20000001011000A53595332312D303033341049002600013720010001072002000A53595332312D303033342005000C3137322E32302E322E323032
                    Quality=0/100  Signal level=38/100  
                    Extra:fm=0002


```

**Help:** execute the command "iwlist wlan0 scanning"

**Prompt:**
- linux$
- linux#

### nmcli connection show

**Output:**
```
NAME                        UUID                                  TYPE      DEVICE 
Wired connection 1          4c73e12a-1934-3ea9-96bc-b13580626d18  ethernet  eth0   
lo                          8fa1d0f5-729e-47d6-b791-ba82a1ecff0c  loopback  lo     
My_other_home               a48f5437-163b-4fb0-983f-c98d0fa117c6  wifi      wlan0  
My_home                     2c794a07-a61d-4276-bc16-c90459cb17ab  wifi      --  

```

**Help:** execute the command "nmcli connection show"

**Prompt:**
- linux$
- linux#

### pct config 1

**Output:**
```

arch: amd11
cores: 1111
cpulimit: 1
cpuunits: 1111
description:  Something really bad
features: nesting=1
hostname: ntc_templates
memory: 1111
net0: name=eth0,bridge=vmbr0,firewall=1,gw=1.1.1.1,hwaddr=AA:AA:AA:AA:AA:AA,ip=1.1.1.2/8,type=veth
onboot: 1
ostype: ubuntu
rootfs: local:1/vm-1-disk-0.raw,size=1000G
swap: 1111
unprivileged: 0
lxc.apparmor.profile: unconfined
lxc.cgroup.devices.allow: a
lxc.apparmor.profile: unconfined
lxc.cgroup.devices.allow: a
tags: tag1,tag2,tag3

```

**Help:** execute the command "pct config 1"

**Prompt:**
- linux$
- linux#

### pct list

**Output:**
```

VMID       Status     Lock         Name                
100        stopped                 netmiko       
101        stopped                 ntc_templates    
1001       running                 something
```

**Help:** execute the command "pct list"

**Prompt:**
- linux$
- linux#

### pveversion

**Output:**
```
pve-manager/1.1-1/101a1111 (running kernel: 1.1.11-11-pve)
```

**Help:** execute the command "pveversion"

**Prompt:**
- linux$
- linux#

### qm config 1

**Output:**
```

bootdisk: ide0
cores: 2
cpulimit: 1
ide0: local:111/vm-111-disk-0.qcow2,size=10G
ide2: local:iso/ubuntu-24.04-live-server-amd64.iso,media=cdrom
memory: 1111
name: Super-Linux-Proxmox
net0: e1000=AA:AA:AA:AA:AA:AA,bridge=vmbr0
numa: 0
onboot: 1
ostype: other
smbios1: uuid=00a0a000-0aa0-0a00-a0aa-0aa0a0000a00
sockets: 1

```

**Help:** execute the command "qm config 1"

**Prompt:**
- linux$
- linux#

### qm list

**Output:**
```

      VMID NAME                 STATUS     MEM(MB)    BOOTDISK(GB) PID       
       100 Screen-Sun-AAAAAAA   running    1111              11.00 1111111   

```

**Help:** execute the command "qm list"

**Prompt:**
- linux$
- linux#

### top

**Output:**
```
top - 12:33:53 up  2:11,  5 users,  load average: 0.12, 0.40, 0.66
Tasks: 200 total,   1 running, 189 sleeping,   5 stopped,   5 zombie
%Cpu(s): 12.5 us, 12.5 sy,  0.0 ni, 62.5 id, 12.5 wa,  0.0 hi,  0.0 si,  0.0 st 
MiB Mem :   7809.9 total,   4753.7 free,   2052.9 used,   1126.5 buff/cache     
MiB Swap:    512.0 total,    512.0 free,      0.0 used.   5757.0 avail Mem 

    PID USER      PR  NI    VIRT    RES    SHR S  %CPU  %MEM     TIME+ COMMAND
  19516 admin     20   0   28.7g 880836  52224 S  12.5  11.0   6:51.26 node
  30427 admin     20   0   11708   4864   2816 R   6.2   0.1   0:00.03 top
      1 root      20   0  168332  11152   8400 S   0.0   0.1   0:01.14 systemd
      4 root       0 -20       0      0      0 I   0.0   0.0   0:00.00 kworker/R-rcu_g
    395 systemd+  20   0   90708   6784   5888 S   0.0   0.1   0:00.18 systemd-timesyn
    397 root       0 -20       0      0      0 I   0.0   0.0   0:00.68 kworker/u13:1-brcmf_wq/mmc1:0001:1
    402 root     -51   0       0      0      0 S   0.0   0.0   0:00.00 irq/41-vc4 hdmi hpd connected
  30343 admin     20   0    5200   1408   1408 S   0.0   0.0   0:00.00 sleep
```

**Help:** execute the command "top"

**Prompt:**
- linux$
- linux#

### vzlist

**Output:**
```
      CTID      NPROC STATUS    IP_ADDR         HOSTNAME
      1110          1 running   -               something
      1111        111 running   192.168.0.1     something-bad
      1112         11 running   -               something-ugly
      1113         11 running   -               something-good
```

**Help:** execute the command "vzlist"

**Prompt:**
- linux$
- linux#

