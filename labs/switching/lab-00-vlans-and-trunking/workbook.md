# Lab 00 — VLANs and Trunk Negotiation

## Table of Contents

1. [Concepts & Skills Covered](#1-concepts--skills-covered)
2. [Topology & Scenario](#2-topology--scenario)
3. [Hardware & Environment Specifications](#3-hardware--environment-specifications)
4. [Base Configuration](#4-base-configuration)
5. [Lab Challenge: Core Implementation](#5-lab-challenge-core-implementation)
6. [Verification & Analysis](#6-verification--analysis)
7. [Verification Cheatsheet](#7-verification-cheatsheet)
8. [Solutions (Spoiler Alert!)](#8-solutions-spoiler-alert)
9. [Troubleshooting Scenarios](#9-troubleshooting-scenarios)
10. [Lab Completion Checklist](#10-lab-completion-checklist)

---

## 1. Concepts & Skills Covered

**Exam Objective:** 3.1 — Layer 2 | 3.1.a — Troubleshoot static and dynamic 802.1q trunking protocols

VLANs are the foundation of every enterprise switched network. They segment broadcast domains
at Layer 2, improving security, performance, and manageability. This lab builds the VLAN and
trunking baseline that all subsequent switching labs depend on — you will create VLANs, form
802.1Q trunks, experiment with DTP negotiation, configure router-on-a-stick inter-VLAN routing,
and verify end-to-end reachability across VLANs.

### VLANs and Broadcast Domain Segmentation

A VLAN is a logical broadcast domain. Frames within a VLAN are forwarded only to ports
assigned to that VLAN — a host in VLAN 10 cannot directly communicate with a host in VLAN 20
at Layer 2. This provides:

- **Security isolation** — sensitive traffic stays within its VLAN boundary
- **Broadcast containment** — ARP, DHCP discover, and other broadcasts are confined
- **Flexible grouping** — users can be grouped by function regardless of physical location

VLANs 1-1005 are the normal range (stored in `vlan.dat`). VLANs 1006-4094 are the extended
range (requires VTP transparent mode or VTPv3). VLAN 1 is the default VLAN and cannot be
deleted — best practice is to move all user traffic off VLAN 1.

```
! VLAN creation syntax
vlan <id>
 name <VLAN_NAME>
```

### 802.1Q Trunking

A trunk carries frames from multiple VLANs over a single physical link by inserting a 4-byte
802.1Q tag into the Ethernet frame header. The tag contains the 12-bit VLAN ID (VID) field,
allowing up to 4094 VLANs.

Key trunk parameters:
- **Native VLAN** — frames on the native VLAN are sent **untagged** across the trunk. Both
  ends must agree on the native VLAN or a mismatch occurs (CDP will warn about this).
- **Allowed VLANs** — by default, a trunk carries all VLANs (1-4094). Best practice is to
  restrict trunks to only the VLANs that need to cross that link.
- **Trunk encapsulation** — Cisco switches that support both ISL and 802.1Q default to
  `negotiate`. On IOSvL2, you must explicitly set `switchport trunk encapsulation dot1q`
  before configuring `switchport mode trunk`.

```
! Trunk configuration syntax
interface <type>
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk native vlan <id>
 switchport trunk allowed vlan <list>
 switchport nonegotiate
```

### Dynamic Trunking Protocol (DTP)

DTP is a Cisco-proprietary protocol that negotiates whether a link becomes a trunk or stays
as an access port. DTP modes and their negotiation outcomes:

| Local Mode | Remote Mode | Result |
|------------|-------------|--------|
| `trunk` | `trunk` | Trunk |
| `trunk` | `dynamic auto` | Trunk |
| `trunk` | `dynamic desirable` | Trunk |
| `trunk` | `access` | **Mismatch** (limited connectivity) |
| `dynamic desirable` | `dynamic desirable` | Trunk |
| `dynamic desirable` | `dynamic auto` | Trunk |
| `dynamic auto` | `dynamic auto` | **Access** (neither initiates) |
| `access` | `access` | Access |

**Exam relevance:** The 350-401 exam tests your ability to predict trunk formation outcomes
from DTP mode combinations and to troubleshoot failed trunk negotiation. In production,
`switchport nonegotiate` should be used on all statically configured trunks to disable DTP
and prevent rogue switch attacks.

### Router-on-a-Stick Inter-VLAN Routing

A router with a single physical trunk interface can route between VLANs using sub-interfaces.
Each sub-interface is assigned to one VLAN via `encapsulation dot1Q <vlan-id>` and given an
IP address that serves as the default gateway for hosts in that VLAN.

```
! Sub-interface syntax
interface GigabitEthernet0/0.10
 encapsulation dot1Q 10
 ip address 192.168.10.1 255.255.255.0
```

The native VLAN sub-interface uses `encapsulation dot1Q <vlan-id> native` — untagged frames
arriving on the physical interface are directed to this sub-interface.

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| VLAN creation and naming | Build the logical broadcast domain structure |
| Static trunk configuration | Form 802.1Q trunks with explicit encapsulation and mode |
| DTP negotiation analysis | Predict and verify trunk/access outcomes from mode combinations |
| Trunk hardening | Restrict allowed VLANs, set native VLAN, disable DTP |
| Router-on-a-stick | Configure sub-interfaces for inter-VLAN routing |
| End-to-end verification | Trace reachability across L2 and L3 boundaries |

---

## 2. Topology & Scenario

### Network Diagram

```
                         ┌──────────────────────┐
                         │          R1           │
                         │ (Inter-VLAN Router)   │
                         │ Lo0: 1.1.1.1/32       │
                         └──────────┬────────────┘
                                    │ Gi0/0 (trunk)
                                    │ sub-if .10/.20/.30/.99
                                    │
                                    │ Gi0/0 (trunk)
                         ┌──────────┴────────────┐
                         │          SW1           │
                         │ (Distribution Switch)  │
                         │ VLAN99: 192.168.99.1   │
                         └───┬──────────────┬─────┘
                  Gi0/1,0/2  │              │  Gi0/3,Gi1/0
                  (trunk)    │              │  (trunk)
                             │              │
                  Gi0/1,0/2  │              │  Gi0/3,Gi1/0
                  (trunk)    │              │  (trunk)
              ┌──────────────┴──┐      ┌────┴──────────────┐
              │       SW2       │      │       SW3          │
              │ (Access Switch) │      │  (Access Switch)   │
              │ VLAN99: .99.2   │      │  VLAN99: .99.3     │
              └──┬──────────┬───┘      └───┬────────────┬───┘
        Gi0/3,   │          │ Gi1/1        │ Gi1/1      │  Gi0/1,
        Gi1/0    │          │ (access)     │ (access)   │  Gi0/2
        (trunk)  │          │              │            │  (trunk)
                 └──────────┼──────────────┼────────────┘
                            │              │
                       ┌────┴───┐     ┌────┴───┐
                       │  PC1   │     │  PC2   │
                       │VLAN 10 │     │VLAN 20 │
                       │.10.10  │     │.20.10  │
                       └────────┘     └────────┘
```

### Scenario

You are a network engineer at Globex Corporation. The company is deploying a new campus
switching infrastructure with three switches in a triangular mesh topology. Your task is to
segment the network into VLANs for the Sales, Engineering, and Management teams, establish
802.1Q trunks between all switches, connect R1 as the inter-VLAN router, and verify that
hosts in different VLANs can communicate through R1.

The security team requires that:
- All trunks use a dedicated native VLAN (not VLAN 1)
- Trunks carry only the VLANs that are needed
- DTP is disabled on production trunks after initial testing

---

## 3. Hardware & Environment Specifications

### Device Inventory

| Device | Platform | Role | Image |
|--------|----------|------|-------|
| SW1 | IOSvL2 | Distribution switch / root bridge candidate | vios_l2-adventerprisek9 |
| SW2 | IOSvL2 | Access switch (PC1 segment) | vios_l2-adventerprisek9 |
| SW3 | IOSvL2 | Access switch (PC2 segment) | vios_l2-adventerprisek9 |
| R1 | IOSv | Inter-VLAN router (router-on-a-stick) | vios-adventerprisek9 |
| PC1 | VPC | End host (VLAN 10) | — |
| PC2 | VPC | End host (VLAN 20) | — |

### Cabling Table

| Link ID | Source | Destination | Type | Purpose |
|---------|--------|-------------|------|---------|
| L1 | R1 Gi0/0 | SW1 Gi0/0 | Trunk | Router-on-a-stick uplink |
| L2 | SW1 Gi0/1 | SW2 Gi0/1 | Trunk | SW1-SW2 link 1 |
| L3 | SW1 Gi0/2 | SW2 Gi0/2 | Trunk | SW1-SW2 link 2 |
| L4 | SW1 Gi0/3 | SW3 Gi0/3 | Trunk | SW1-SW3 link 1 |
| L5 | SW1 Gi1/0 | SW3 Gi1/0 | Trunk | SW1-SW3 link 2 |
| L6 | SW2 Gi0/3 | SW3 Gi0/1 | Trunk | SW2-SW3 link 1 |
| L7 | SW2 Gi1/0 | SW3 Gi0/2 | Trunk | SW2-SW3 link 2 |
| L8 | PC1 e0 | SW2 Gi1/1 | Access | PC1 (VLAN 10) |
| L9 | PC2 e0 | SW3 Gi1/1 | Access | PC2 (VLAN 20) |

### Console Access Table

| Device | Console Port | Connection |
|--------|-------------|------------|
| SW1 | _dynamic_ | `telnet <eve-ng-ip> <port>` |
| SW2 | _dynamic_ | `telnet <eve-ng-ip> <port>` |
| SW3 | _dynamic_ | `telnet <eve-ng-ip> <port>` |
| R1 | _dynamic_ | `telnet <eve-ng-ip> <port>` |

> Console ports are assigned dynamically by EVE-NG. Check the EVE-NG web UI or use
> `GET /api/labs/<lab>/nodes` to discover assigned port numbers.

### IP Addressing

| VLAN | Name | Subnet | Gateway (R1) |
|------|------|--------|-------------|
| 10 | SALES | 192.168.10.0/24 | 192.168.10.1 |
| 20 | ENGINEERING | 192.168.20.0/24 | 192.168.20.1 |
| 30 | MANAGEMENT_HOSTS | 192.168.30.0/24 | 192.168.30.1 |
| 99 | NATIVE_MGMT | 192.168.99.0/24 | SW1 SVI: 192.168.99.1 |

| Host | IP Address | Default Gateway | VLAN |
|------|-----------|----------------|------|
| PC1 | 192.168.10.10/24 | 192.168.10.1 | 10 |
| PC2 | 192.168.20.10/24 | 192.168.20.1 | 20 |

---

## 4. Base Configuration

### What IS pre-loaded (initial-configs/)

Each device starts with only:
- Hostname set
- DNS lookup disabled
- Console and VTY line settings (logging synchronous, no exec timeout)

### What is NOT pre-loaded (you will configure)

- VLANs (10, 20, 30, 99)
- Trunk configuration on inter-switch links
- Native VLAN and allowed VLAN filtering
- DTP settings
- Router-on-a-stick sub-interfaces on R1
- Access port assignments for PC1 and PC2
- Management SVIs

### Loading Initial Configs

```bash
python3 setup_lab.py --host <eve-ng-ip>
```

### PC Configuration (manual)

After loading initial configs, configure the VPCs interactively:

**PC1:**
```
ip 192.168.10.10 255.255.255.0 192.168.10.1
```

**PC2:**
```
ip 192.168.20.10 255.255.255.0 192.168.20.1
```

---

## 5. Lab Challenge: Core Implementation

### Task 1: Create the VLAN Structure

- Create four VLANs on **all three switches** (SW1, SW2, SW3):
  - VLAN 10 named SALES
  - VLAN 20 named ENGINEERING
  - VLAN 30 named MANAGEMENT_HOSTS
  - VLAN 99 named NATIVE_MGMT
- Verify that all VLANs exist and are active on every switch.

**Verification:** `show vlan brief` — all four VLANs must appear as active on each switch.

---

### Task 2: Configure Static Trunks Between Switches

- On all inter-switch links (SW1-SW2: Gi0/1, Gi0/2; SW1-SW3: Gi0/3, Gi1/0; SW2-SW3: Gi0/3, Gi1/0 on SW2 side; Gi0/1, Gi0/2 on SW3 side), configure 802.1Q trunks:
  - Set the trunk encapsulation to 802.1Q
  - Set the port mode to trunk
  - Set the native VLAN to 99
  - Restrict allowed VLANs to 10, 20, 30, and 99 only
- Also configure the SW1 Gi0/0 uplink to R1 as a trunk with the same native VLAN and allowed VLAN list.

**Verification:** `show interfaces trunk` — each trunk port must show mode "on", native VLAN 99, and allowed VLANs 10,20,30,99.

---

### Task 3: Explore DTP Negotiation

- Before disabling DTP, experiment with dynamic modes on one pair of links to observe negotiation behavior:
  - Temporarily set SW1 Gi0/1 to dynamic desirable and SW2 Gi0/1 to dynamic auto — verify that a trunk forms.
  - Change both sides to dynamic auto — verify that the link falls back to access mode.
  - Change one side to access mode and the other to trunk — observe the mismatch behavior.
- After experimenting, return both interfaces to static trunk mode.

**Verification:** `show interfaces <int> switchport` — check "Administrative Mode" and "Operational Mode" after each change. The final state must show "trunk" on both sides.

---

### Task 4: Disable DTP on All Trunks

- On every trunk port across all three switches (and the SW1-R1 uplink), disable DTP negotiation so that no DTP frames are sent.

**Verification:** `show interfaces <int> switchport` — "Negotiation of Trunking" must show "Off" on every trunk port.

---

### Task 5: Configure Access Ports for End Hosts

- On SW2, assign the port connected to PC1 (Gi1/1) as an access port in VLAN 10.
- On SW3, assign the port connected to PC2 (Gi1/1) as an access port in VLAN 20.

**Verification:** `show interfaces <int> switchport` — "Access Mode VLAN" must show the correct VLAN assignment on each port.

---

### Task 6: Configure Router-on-a-Stick on R1

- On R1, configure the physical trunk interface (Gi0/0) with no IP address and bring it up.
- Create sub-interfaces for each VLAN:
  - Sub-interface for VLAN 10 with 802.1Q encapsulation and the SALES gateway address
  - Sub-interface for VLAN 20 with 802.1Q encapsulation and the ENGINEERING gateway address
  - Sub-interface for VLAN 30 with 802.1Q encapsulation and the MANAGEMENT_HOSTS gateway address
  - Sub-interface for VLAN 99 with native 802.1Q encapsulation and address 192.168.99.254/24

**Verification:** `show ip interface brief` — all four sub-interfaces must be up/up with the correct IP addresses.

---

### Task 7: Configure Management SVIs

- On each switch, create an SVI for VLAN 99 and assign the management IP address:
  - SW1: 192.168.99.1/24
  - SW2: 192.168.99.2/24
  - SW3: 192.168.99.3/24

**Verification:** `show ip interface brief` — VLAN 99 SVI must be up/up with the correct address on each switch.

---

### Task 8: Verify End-to-End Reachability

- From PC1 (192.168.10.10), ping PC2 (192.168.20.10) — this traverses VLAN 10 on SW2, trunks to SW1, R1 routes between VLANs, trunks back down, and reaches VLAN 20 on SW3.
- From PC1, ping R1's VLAN 10 gateway (192.168.10.1).
- From PC2, ping R1's VLAN 20 gateway (192.168.20.1).
- Verify switch management reachability: from SW1, ping SW2 (192.168.99.2) and SW3 (192.168.99.3) over VLAN 99.

**Verification:** All pings must succeed with 0% packet loss.

---

## 6. Verification & Analysis

### Task 1 — VLAN Structure

```
SW1# show vlan brief

VLAN Name                             Status    Ports
---- -------------------------------- --------- -------------------------------
1    default                          active    Gi1/1, Gi1/2, Gi1/3
10   SALES                            active                                    ! ← VLAN 10 exists
20   ENGINEERING                      active                                    ! ← VLAN 20 exists
30   MANAGEMENT_HOSTS                 active                                    ! ← VLAN 30 exists
99   NATIVE_MGMT                      active                                    ! ← VLAN 99 exists
```

> Repeat on SW2 and SW3. All four VLANs must appear on every switch.

### Task 2 — Static Trunks

```
SW1# show interfaces trunk

Port        Mode         Encapsulation  Status        Native vlan
Gi0/0       on           802.1q         trunking      99          ! ← R1 uplink, native 99
Gi0/1       on           802.1q         trunking      99          ! ← SW2 link 1
Gi0/2       on           802.1q         trunking      99          ! ← SW2 link 2
Gi0/3       on           802.1q         trunking      99          ! ← SW3 link 1
Gi1/0       on           802.1q         trunking      99          ! ← SW3 link 2

Port        Vlans allowed on trunk
Gi0/0       10,20,30,99                                           ! ← restricted, not 1-4094
Gi0/1       10,20,30,99
Gi0/2       10,20,30,99
Gi0/3       10,20,30,99
Gi1/0       10,20,30,99
```

### Task 3 — DTP Negotiation Outcomes

```
! Step 1: SW1 Gi0/1 = dynamic desirable, SW2 Gi0/1 = dynamic auto
SW1# show interfaces Gi0/1 switchport
Administrative Mode: dynamic desirable
Operational Mode: trunk                                            ! ← trunk formed via DTP

! Step 2: Both sides = dynamic auto
SW1# show interfaces Gi0/1 switchport
Administrative Mode: dynamic auto
Operational Mode: static access                                    ! ← no trunk! Both passive.

! Step 3: Return to static trunk
SW1# show interfaces Gi0/1 switchport
Administrative Mode: trunk
Operational Mode: trunk                                            ! ← final state: static trunk
```

### Task 4 — DTP Disabled

```
SW1# show interfaces Gi0/1 switchport
Administrative Mode: trunk
Operational Mode: trunk
Negotiation of Trunking: Off                                       ! ← DTP disabled
```

### Task 5 — Access Ports

```
SW2# show interfaces Gi1/1 switchport
Administrative Mode: static access
Access Mode VLAN: 10 (SALES)                                       ! ← correct VLAN assignment

SW3# show interfaces Gi1/1 switchport
Administrative Mode: static access
Access Mode VLAN: 20 (ENGINEERING)                                 ! ← correct VLAN assignment
```

### Task 6 — Router-on-a-Stick

```
R1# show ip interface brief
Interface                  IP-Address      OK? Method Status                Protocol
GigabitEthernet0/0         unassigned      YES unset  up                    up
GigabitEthernet0/0.10      192.168.10.1    YES manual up                    up       ! ← VLAN 10 gw
GigabitEthernet0/0.20      192.168.20.1    YES manual up                    up       ! ← VLAN 20 gw
GigabitEthernet0/0.30      192.168.30.1    YES manual up                    up       ! ← VLAN 30 gw
GigabitEthernet0/0.99      192.168.99.254  YES manual up                    up       ! ← native VLAN
Loopback0                  1.1.1.1         YES manual up                    up
```

### Task 7 — Management SVIs

```
SW1# show ip interface brief | include Vlan99
Vlan99                     192.168.99.1    YES manual up                    up       ! ← SW1 mgmt

SW2# show ip interface brief | include Vlan99
Vlan99                     192.168.99.2    YES manual up                    up       ! ← SW2 mgmt

SW3# show ip interface brief | include Vlan99
Vlan99                     192.168.99.3    YES manual up                    up       ! ← SW3 mgmt
```

### Task 8 — End-to-End Reachability

```
PC1> ping 192.168.20.10
84 bytes from 192.168.20.10 icmp_seq=1 ttl=63 time=12.345 ms     ! ← cross-VLAN via R1
84 bytes from 192.168.20.10 icmp_seq=2 ttl=63 time=8.123 ms
84 bytes from 192.168.20.10 icmp_seq=3 ttl=63 time=7.890 ms

! TTL=63 confirms the packet traversed one L3 hop (R1)

PC1> ping 192.168.10.1
84 bytes from 192.168.10.1 icmp_seq=1 ttl=255 time=4.567 ms      ! ← gateway reachable

SW1# ping 192.168.99.2
!!!!!
Success rate is 100 percent (5/5)                                  ! ← management VLAN works

SW1# ping 192.168.99.3
!!!!!
Success rate is 100 percent (5/5)                                  ! ← management VLAN works
```

---

## 7. Verification Cheatsheet

### VLAN Configuration

```
! VLAN creation
vlan <id>
 name <NAME>
```

| Command | Purpose |
|---------|---------|
| `vlan <id>` | Enter VLAN configuration mode |
| `name <NAME>` | Assign a descriptive name to the VLAN |

> **Exam tip:** VLAN 1 is the default and cannot be deleted. The 350-401 expects you to move all user and management traffic off VLAN 1.

### Trunk Configuration

```
interface <type>
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk native vlan <id>
 switchport trunk allowed vlan <list>
 switchport nonegotiate
```

| Command | Purpose |
|---------|---------|
| `switchport trunk encapsulation dot1q` | Set 802.1Q encapsulation (required on IOSvL2) |
| `switchport mode trunk` | Force the port into trunk mode |
| `switchport trunk native vlan <id>` | Set the native (untagged) VLAN |
| `switchport trunk allowed vlan <list>` | Restrict which VLANs traverse the trunk |
| `switchport nonegotiate` | Disable DTP — no negotiation frames sent |

> **Exam tip:** `switchport trunk allowed vlan add <id>` adds a VLAN without replacing the existing list. Using `allowed vlan <list>` without `add` overwrites the entire allowed list.

### DTP Modes

```
interface <type>
 switchport mode dynamic desirable
 switchport mode dynamic auto
 switchport mode trunk
 switchport mode access
```

| Command | Purpose |
|---------|---------|
| `switchport mode dynamic desirable` | Actively initiates DTP trunk negotiation |
| `switchport mode dynamic auto` | Passively waits for DTP — will trunk if asked |
| `switchport mode trunk` | Forces trunk regardless of remote DTP state |
| `switchport mode access` | Forces access — ignores DTP |

### Access Port Configuration

```
interface <type>
 switchport mode access
 switchport access vlan <id>
```

| Command | Purpose |
|---------|---------|
| `switchport mode access` | Force the port into access mode |
| `switchport access vlan <id>` | Assign the port to a specific VLAN |

### Router-on-a-Stick Sub-interfaces

```
interface GigabitEthernet0/0
 no ip address
 no shutdown
!
interface GigabitEthernet0/0.<vlan-id>
 encapsulation dot1Q <vlan-id>
 ip address <gateway-ip> <mask>
```

| Command | Purpose |
|---------|---------|
| `encapsulation dot1Q <vlan-id>` | Map sub-interface to a VLAN |
| `encapsulation dot1Q <vlan-id> native` | Map sub-interface to the native VLAN |
| `ip address <ip> <mask>` | Set the default gateway address for the VLAN |

> **Exam tip:** The physical interface must be `no shutdown` with no IP address. Sub-interfaces inherit the physical interface's line protocol state.

### Verification Commands

| Command | What to Look For |
|---------|-----------------|
| `show vlan brief` | VLAN IDs, names, status (active), and port membership |
| `show interfaces trunk` | Mode (on), encapsulation (802.1q), native VLAN, allowed VLANs |
| `show interfaces <int> switchport` | Admin/operational mode, negotiation status, VLAN assignments |
| `show ip interface brief` | Sub-interface status (up/up) and IP addresses |
| `show cdp neighbors` | Verify physical connectivity and neighbor discovery |
| `show spanning-tree vlan <id>` | Confirm STP state per VLAN (all ports forwarding expected) |
| `ping <ip>` | End-to-end reachability (check TTL for L3 hop count) |

### Common VLAN/Trunk Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| Trunk shows "not-trunking" | Missing `switchport trunk encapsulation dot1q` on IOSvL2 |
| Native VLAN mismatch syslog | Different native VLAN configured on each end of the trunk |
| Traffic for one VLAN not crossing trunk | VLAN missing from `allowed vlan` list |
| Both sides dynamic auto — no trunk | Neither side initiates DTP; both remain access |
| PC cannot reach gateway | Wrong access VLAN, or gateway sub-interface down |
| Sub-interface down/down | Physical interface is shutdown or no cable connected |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Tasks 1-4: VLAN and Trunk Configuration (Switches)

<details>
<summary>Click to view SW1 Configuration</summary>

```bash
! SW1 — VLANs, trunks, management SVI
!
vlan 10
 name SALES
vlan 20
 name ENGINEERING
vlan 30
 name MANAGEMENT_HOSTS
vlan 99
 name NATIVE_MGMT
!
! Trunk to R1
interface GigabitEthernet0/0
 description TRUNK_TO_R1_Gi0/0
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk native vlan 99
 switchport trunk allowed vlan 10,20,30,99
 switchport nonegotiate
 no shutdown
!
! Trunks to SW2
interface GigabitEthernet0/1
 description TRUNK_TO_SW2_Gi0/1
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk native vlan 99
 switchport trunk allowed vlan 10,20,30,99
 switchport nonegotiate
 no shutdown
!
interface GigabitEthernet0/2
 description TRUNK_TO_SW2_Gi0/2
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk native vlan 99
 switchport trunk allowed vlan 10,20,30,99
 switchport nonegotiate
 no shutdown
!
! Trunks to SW3
interface GigabitEthernet0/3
 description TRUNK_TO_SW3_Gi0/3
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk native vlan 99
 switchport trunk allowed vlan 10,20,30,99
 switchport nonegotiate
 no shutdown
!
interface GigabitEthernet1/0
 description TRUNK_TO_SW3_Gi1/0
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk native vlan 99
 switchport trunk allowed vlan 10,20,30,99
 switchport nonegotiate
 no shutdown
!
! Management SVI
interface Vlan99
 description MANAGEMENT
 ip address 192.168.99.1 255.255.255.0
 no shutdown
```
</details>

<details>
<summary>Click to view SW2 Configuration</summary>

```bash
! SW2 — VLANs, trunks, access port, management SVI
!
vlan 10
 name SALES
vlan 20
 name ENGINEERING
vlan 30
 name MANAGEMENT_HOSTS
vlan 99
 name NATIVE_MGMT
!
! Trunks to SW1
interface GigabitEthernet0/1
 description TRUNK_TO_SW1_Gi0/1
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk native vlan 99
 switchport trunk allowed vlan 10,20,30,99
 switchport nonegotiate
 no shutdown
!
interface GigabitEthernet0/2
 description TRUNK_TO_SW1_Gi0/2
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk native vlan 99
 switchport trunk allowed vlan 10,20,30,99
 switchport nonegotiate
 no shutdown
!
! Trunks to SW3
interface GigabitEthernet0/3
 description TRUNK_TO_SW3_Gi0/1
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk native vlan 99
 switchport trunk allowed vlan 10,20,30,99
 switchport nonegotiate
 no shutdown
!
interface GigabitEthernet1/0
 description TRUNK_TO_SW3_Gi0/2
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk native vlan 99
 switchport trunk allowed vlan 10,20,30,99
 switchport nonegotiate
 no shutdown
!
! Access port for PC1
interface GigabitEthernet1/1
 description ACCESS_PC1_VLAN10
 switchport mode access
 switchport access vlan 10
 no shutdown
!
! Management SVI
interface Vlan99
 description MANAGEMENT
 ip address 192.168.99.2 255.255.255.0
 no shutdown
```
</details>

<details>
<summary>Click to view SW3 Configuration</summary>

```bash
! SW3 — VLANs, trunks, access port, management SVI
!
vlan 10
 name SALES
vlan 20
 name ENGINEERING
vlan 30
 name MANAGEMENT_HOSTS
vlan 99
 name NATIVE_MGMT
!
! Trunks to SW2
interface GigabitEthernet0/1
 description TRUNK_TO_SW2_Gi0/3
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk native vlan 99
 switchport trunk allowed vlan 10,20,30,99
 switchport nonegotiate
 no shutdown
!
interface GigabitEthernet0/2
 description TRUNK_TO_SW2_Gi1/0
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk native vlan 99
 switchport trunk allowed vlan 10,20,30,99
 switchport nonegotiate
 no shutdown
!
! Trunks to SW1
interface GigabitEthernet0/3
 description TRUNK_TO_SW1_Gi0/3
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk native vlan 99
 switchport trunk allowed vlan 10,20,30,99
 switchport nonegotiate
 no shutdown
!
interface GigabitEthernet1/0
 description TRUNK_TO_SW1_Gi1/0
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk native vlan 99
 switchport trunk allowed vlan 10,20,30,99
 switchport nonegotiate
 no shutdown
!
! Access port for PC2
interface GigabitEthernet1/1
 description ACCESS_PC2_VLAN20
 switchport mode access
 switchport access vlan 20
 no shutdown
!
! Management SVI
interface Vlan99
 description MANAGEMENT
 ip address 192.168.99.3 255.255.255.0
 no shutdown
```
</details>

### Tasks 5-6: Router-on-a-Stick

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1 — Router-on-a-stick inter-VLAN routing
!
interface GigabitEthernet0/0
 description TRUNK_TO_SW1_Gi0/0
 no ip address
 no shutdown
!
interface GigabitEthernet0/0.10
 description GATEWAY_VLAN10_SALES
 encapsulation dot1Q 10
 ip address 192.168.10.1 255.255.255.0
!
interface GigabitEthernet0/0.20
 description GATEWAY_VLAN20_ENGINEERING
 encapsulation dot1Q 20
 ip address 192.168.20.1 255.255.255.0
!
interface GigabitEthernet0/0.30
 description GATEWAY_VLAN30_MGMT_HOSTS
 encapsulation dot1Q 30
 ip address 192.168.30.1 255.255.255.0
!
interface GigabitEthernet0/0.99
 description GATEWAY_VLAN99_NATIVE_MGMT
 encapsulation dot1Q 99 native
 ip address 192.168.99.254 255.255.255.0
!
interface Loopback0
 ip address 1.1.1.1 255.255.255.255
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
! From PC1 — cross-VLAN ping to PC2
PC1> ping 192.168.20.10

! From SW1 — management VLAN verification
SW1# ping 192.168.99.2
SW1# ping 192.168.99.3
SW1# ping 192.168.99.254

! Trunk status
SW1# show interfaces trunk
SW2# show interfaces trunk
SW3# show interfaces trunk

! R1 sub-interface status
R1# show ip interface brief
```
</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. Inject the fault first, then
diagnose and fix using only show commands.

### Workflow

```bash
python3 setup_lab.py --host <eve-ng-ip>                          # reset to known-good
python3 scripts/fault-injection/inject_scenario_01.py            # Ticket 1
python3 scripts/fault-injection/apply_solution.py                # restore
```

---

### Ticket 1 — PC1 Can Ping Its Gateway But Cannot Reach PC2

A junior engineer reports that PC1 (VLAN 10, 192.168.10.10) can ping its default gateway
(192.168.10.1) but cannot reach PC2 (VLAN 20, 192.168.20.10). All switches show trunks as up.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>`

**Success criteria:** PC1 can ping PC2 (192.168.20.10) successfully.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Start from PC1: `ping 192.168.20.10` — fails.
2. From PC1: `ping 192.168.10.1` — succeeds (gateway reachable, VLAN 10 is fine).
3. From R1: `ping 192.168.20.10` — fails (R1 cannot reach PC2 either).
4. From R1: `show ip interface brief` — check if Gi0/0.20 is up/up with correct IP.
5. On SW1: `show interfaces trunk` — check "Vlans allowed on trunk" for Gi0/3 and Gi1/0 (links to SW3). If VLAN 20 is missing from allowed list on the SW1-SW3 trunk, VLAN 20 traffic cannot reach SW3.
6. On SW3: `show interfaces trunk` — confirm the same VLAN is missing from the SW3 side.
</details>

<details>
<summary>Click to view Fix</summary>

The fault is a missing VLAN in the trunk allowed list on the SW1-SW3 links. VLAN 20 was
removed from the allowed VLAN list on SW1's Gi0/3 and Gi1/0 (and/or SW3's Gi0/3 and Gi1/0).

```bash
! SW1
interface GigabitEthernet0/3
 switchport trunk allowed vlan 10,20,30,99
interface GigabitEthernet1/0
 switchport trunk allowed vlan 10,20,30,99

! SW3 (if also affected)
interface GigabitEthernet0/3
 switchport trunk allowed vlan 10,20,30,99
interface GigabitEthernet1/0
 switchport trunk allowed vlan 10,20,30,99
```

Verify: `PC1> ping 192.168.20.10` — should now succeed.
</details>

---

### Ticket 2 — CDP Reports Native VLAN Mismatch on SW2

The monitoring system flags a syslog message: `%CDP-4-NATIVE_VLAN_MISMATCH` on SW2.
Inter-switch connectivity is degraded — some traffic between SW1 and SW2 is intermittently
lost.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py --host <eve-ng-ip>`

**Success criteria:** No native VLAN mismatch warnings, all trunks show native VLAN 99, full connectivity restored.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. On SW2: `show interfaces trunk` — check the native VLAN column. If one trunk port shows native VLAN 1 instead of 99, that is the mismatch.
2. On SW1: `show interfaces trunk` — compare. SW1 side will show native VLAN 99 while the SW2 side shows VLAN 1 (or vice versa).
3. Identify which interface(s) have the wrong native VLAN.
4. Check for missing `switchport trunk native vlan 99` on the affected port.
</details>

<details>
<summary>Click to view Fix</summary>

The fault is a native VLAN mismatch — one side of the SW1-SW2 trunk has native VLAN 1 instead
of 99.

```bash
! SW2 (assuming SW2 Gi0/1 was changed)
interface GigabitEthernet0/1
 switchport trunk native vlan 99
```

Verify:
```bash
SW2# show interfaces trunk
! Native VLAN column must show 99 on all trunk ports
! Wait 60 seconds — no more CDP mismatch syslog messages
```
</details>

---

### Ticket 3 — PC2 Cannot Reach Any Network Resource

The help desk reports that PC2 (connected to SW3 Gi1/1) has no network connectivity at all.
PC2 cannot ping its own gateway. The physical link light is green.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py --host <eve-ng-ip>`

**Success criteria:** PC2 can ping its gateway (192.168.20.1) and PC1 (192.168.10.10).

<details>
<summary>Click to view Diagnosis Steps</summary>

1. On SW3: `show interfaces Gi1/1 switchport` — check the "Access Mode VLAN" field. If PC2's port is assigned to the wrong VLAN (e.g., VLAN 30 instead of VLAN 20), PC2's IP (192.168.20.x) won't match the VLAN's subnet.
2. On SW3: `show vlan brief` — verify which ports are in which VLAN.
3. On R1: `show ip interface brief` — confirm Gi0/0.20 has 192.168.20.1 and is up/up.
4. If the VLAN assignment is wrong, the fix is straightforward.
</details>

<details>
<summary>Click to view Fix</summary>

The fault is an incorrect VLAN assignment on SW3's access port for PC2. The port was moved to
VLAN 30 (MANAGEMENT_HOSTS) instead of VLAN 20 (ENGINEERING).

```bash
! SW3
interface GigabitEthernet1/1
 switchport access vlan 20
```

Verify:
```bash
SW3# show interfaces Gi1/1 switchport
! Access Mode VLAN: 20 (ENGINEERING)

PC2> ping 192.168.20.1
! Should succeed

PC2> ping 192.168.10.10
! Should succeed (cross-VLAN via R1)
```
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] VLANs 10, 20, 30, 99 created and named on all three switches
- [ ] All inter-switch links configured as 802.1Q trunks
- [ ] Native VLAN 99 set on every trunk
- [ ] Allowed VLANs restricted to 10, 20, 30, 99 on every trunk
- [ ] DTP disabled (`switchport nonegotiate`) on all trunk ports
- [ ] PC1 access port (SW2 Gi1/1) in VLAN 10
- [ ] PC2 access port (SW3 Gi1/1) in VLAN 20
- [ ] R1 sub-interfaces configured for VLANs 10, 20, 30, 99
- [ ] Management SVIs configured on SW1 (.99.1), SW2 (.99.2), SW3 (.99.3)
- [ ] PC1 can ping PC2 across VLANs (via R1)
- [ ] Switches can ping each other over VLAN 99

### Troubleshooting

- [ ] Ticket 1 — Diagnosed and fixed missing allowed VLAN on trunk
- [ ] Ticket 2 — Diagnosed and fixed native VLAN mismatch
- [ ] Ticket 3 — Diagnosed and fixed incorrect access VLAN assignment
