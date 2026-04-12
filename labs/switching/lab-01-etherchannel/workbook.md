# Lab 01 — Static and Dynamic EtherChannels

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

**Exam Objective:** 3.1.b — Troubleshoot static and dynamic EtherChannels

EtherChannel bundles two or more parallel physical links between switches into a single logical
interface, eliminating Spanning Tree's instinct to block redundant paths while delivering
aggregated bandwidth and link-level redundancy. This lab takes the dual-link triangle topology
already trunking from Lab 00 and transforms it into three EtherChannel bundles — one LACP,
one PAgP, one static — so you can observe how each protocol negotiates, fails, and is
diagnosed under real exam conditions.

### EtherChannel Fundamentals

An EtherChannel (also called a Link Aggregation Group, or LAG) presents multiple physical
links to the network as a single logical port-channel interface. From the perspective of
Spanning Tree Protocol, only the logical port-channel exists — STP cannot block a member
link. Traffic is distributed across members using a hash of frame attributes.

Key requirements — all member links must share the same:
- Speed and duplex
- Switchport mode (trunk or access)
- Trunk encapsulation type (dot1q)
- Native VLAN and allowed VLAN list
- Layer 3 subnet (if routed EtherChannel)

A mismatch in any of these prevents bundle formation. The switch logs an error and may place
member ports in individual suspended state.

```
! EtherChannel syntax structure
interface range GigabitEthernetX/Y - Z
 channel-group <number> mode <mode>

interface Port-channel<number>
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk native vlan <id>
 switchport trunk allowed vlan <list>
```

### LACP — Link Aggregation Control Protocol (802.3ad)

LACP is the IEEE open-standard protocol (802.3ad) for negotiating EtherChannel formation.
Both ends exchange LACP Data Units (LACPDUs) to agree on bundle membership. LACP modes:

| Mode | Behavior |
|------|----------|
| `active` | Actively sends LACPDUs to initiate negotiation |
| `passive` | Listens for LACPDUs; forms bundle only if the other end is active |

**Rule:** At least one side must be `active`. Two `passive` sides will never form a bundle
(neither sends LACPDUs). An `active`/`active` pair also forms a bundle.

LACP allows up to 16 member links — 8 active, 8 in hot-standby. Active links carry traffic;
standby links are promoted automatically if an active link fails.

```
! LACP configuration
interface GigabitEthernetX/Y
 channel-group 1 mode active     ! or passive on the remote end

! Verify LACP state
show lacp neighbor
show lacp internal
```

> **Exam tip:** LACP `passive`/`passive` = no bundle. One side must be `active`.
> This is the most frequently tested LACP failure mode.

### PAgP — Port Aggregation Protocol

PAgP is Cisco's proprietary predecessor to LACP. It uses PAgP frames to negotiate bundle
membership. PAgP modes:

| Mode | Behavior |
|------|----------|
| `desirable` | Actively sends PAgP frames to initiate negotiation |
| `auto` | Listens for PAgP frames; forms bundle only if the other end is desirable |

**Rule:** At least one side must be `desirable`. Two `auto` sides will never form a bundle
(neither sends PAgP frames). Because PAgP is Cisco-proprietary, a PAgP port cannot negotiate
with a port running LACP — protocol mismatch prevents bundle formation.

```
! PAgP configuration
interface GigabitEthernetX/Y
 channel-group 2 mode desirable  ! or auto on the remote end

! Verify PAgP state
show pagp neighbor
show pagp internal
```

> **Exam tip:** PAgP `auto`/`auto` = no bundle. Mixing PAgP and LACP on the same bundle = no bundle.

### Static EtherChannel (Mode On)

Static mode (`channel-group N mode on`) forces the interface into a bundle without any
negotiation protocol. No LACPDUs or PAgP frames are exchanged — the ports simply join
the channel-group unconditionally.

**Risk:** If one end is `mode on` and the other end is running LACP or PAgP, no bundle forms.
Worse, if member link configuration mismatches go undetected, frames may loop because
STP sees a single port-channel with multiple physical links in forwarding state.

```
! Static EtherChannel — both ends must be 'on'
interface GigabitEthernetX/Y
 channel-group 3 mode on

! No protocol-specific verification commands
! Use show etherchannel summary / show interfaces port-channel
```

> **Exam tip:** Static (`mode on`) is the only mode that does NOT use a negotiation protocol.
> Mixing `on` with `active`, `passive`, `desirable`, or `auto` always results in failure.

### EtherChannel Load Balancing

Traffic across bundle members is distributed by hashing frame attributes. The hash is
deterministic — the same flow always uses the same link. Available hash inputs:

| Algorithm | Basis |
|-----------|-------|
| `src-mac` | Source MAC address |
| `dst-mac` | Destination MAC address |
| `src-dst-mac` | XOR of source and destination MAC |
| `src-ip` | Source IP address |
| `dst-ip` | Destination IP address |
| `src-dst-ip` | XOR of source and destination IP |

The choice of algorithm affects traffic distribution. If all traffic flows from a single MAC,
`src-mac` maps everything to one link — poor distribution. `src-dst-mac` or `src-dst-ip`
usually provide the best spread across links.

```
! Configure load-balance method (global command)
port-channel load-balance src-dst-mac

! Verify the configured method
show etherchannel load-balance
```

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| LACP bundle configuration | Configure active/passive roles and verify LACPDU exchange |
| PAgP bundle configuration | Configure desirable/auto roles and verify PAgP frame exchange |
| Static EtherChannel | Configure mode-on bundles and understand the negotiation tradeoff |
| Bundle verification | Read `show etherchannel summary` flags and interpret member port states |
| Mismatch troubleshooting | Identify and resolve speed, protocol, and VLAN mismatch conditions |
| Load balancing | Configure and verify EtherChannel traffic distribution |
| Trunk over EtherChannel | Confirm trunk parameters are inherited and consistent on port-channel interfaces |

---

## 2. Topology & Scenario

**Scenario:** Acme Corporation's campus core has three distribution switches (SW1, SW2, SW3)
interconnected in a full-mesh triangle. Each switch pair has two physical links. The network
team completed the VLAN and trunking baseline in the previous maintenance window. Today's
change window requires bundling those parallel links into EtherChannels to double inter-switch
bandwidth and provide link-level redundancy without sacrificing Spanning Tree convergence time.

The design requires three bundles:
- **Po1** — SW1 to SW2: LACP (IEEE 802.3ad), open-standard negotiated
- **Po2** — SW1 to SW3: PAgP (Cisco-proprietary), legacy negotiated
- **Po3** — SW2 to SW3: Static (no negotiation, maximum simplicity)

R1 continues to provide inter-VLAN routing via its trunk to SW1 Gi0/0 — R1 is unaffected
by EtherChannel changes on the switch-to-switch links.

```
                         ┌─────────────────────────┐
                         │           R1            │
                         │   (router-on-a-stick)   │
                         │   Lo0: 1.1.1.1/32       │
                         └───────────┬─────────────┘
                               Gi0/0 │ (trunk, not bundled)
                               Gi0/0 │
                         ┌───────────┴─────────────┐
                         │           SW1           │
                         │  (distribution/core)    │
                         │  VLAN99 SVI: .99.1      │
                         └──────┬──────────┬───────┘
                Gi0/1,Gi0/2     │   Po1    │ Gi0/3,Gi1/0
                (LACP active)   │          │ (PAgP desirable)
                                │          │      Po2
                                │          │
              Gi0/1,Gi0/2       │          │  Gi0/3,Gi1/0
              (LACP passive)    │          │  (PAgP auto)
                    ┌───────────┘          └──────────┐
                    │                                 │
               ┌────┴──────────────┐    ┌────────────┴──────┐
               │       SW2         │    │       SW3          │
               │  (access/PC1)     │    │  (access/PC2)      │
               │  VLAN99 SVI: .99.2│    │  VLAN99 SVI: .99.3 │
               └──────┬────────────┘    └────────────┬───────┘
          Gi0/3,Gi1/0 │  Po3 (static)   Gi0/1,Gi0/2 │
              (mode on)└────────────────┘   (mode on)
                       │                │
               PC1─SW2:Gi1/1      PC2─SW3:Gi1/1
               VLAN10 .10.10/24   VLAN20 .20.10/24
```

---

## 3. Hardware & Environment Specifications

### Device Summary

| Device | Platform | Role | Management IP |
|--------|----------|------|---------------|
| SW1 | IOSvL2 | Distribution switch / core | 192.168.99.1/24 (SVI Vlan99) |
| SW2 | IOSvL2 | Access switch (PC1 segment) | 192.168.99.2/24 (SVI Vlan99) |
| SW3 | IOSvL2 | Access switch (PC2 segment) | 192.168.99.3/24 (SVI Vlan99) |
| R1 | IOSv | Inter-VLAN router (ROAS) | 192.168.99.254/24 (sub-int Gi0/0.99) |
| PC1 | VPC | End host — VLAN 10 SALES | 192.168.10.10/24 GW .10.1 |
| PC2 | VPC | End host — VLAN 20 ENGINEERING | 192.168.20.10/24 GW .20.1 |

### Cabling Table

| Link ID | Source | Destination | Bundle | Purpose |
|---------|--------|-------------|--------|---------|
| L1 | R1 Gi0/0 | SW1 Gi0/0 | — | Router-on-a-stick trunk |
| L2 | SW1 Gi0/1 | SW2 Gi0/1 | Po1 member | LACP EtherChannel |
| L3 | SW1 Gi0/2 | SW2 Gi0/2 | Po1 member | LACP EtherChannel |
| L4 | SW1 Gi0/3 | SW3 Gi0/3 | Po2 member | PAgP EtherChannel |
| L5 | SW1 Gi1/0 | SW3 Gi1/0 | Po2 member | PAgP EtherChannel |
| L6 | SW2 Gi0/3 | SW3 Gi0/1 | Po3 member | Static EtherChannel |
| L7 | SW2 Gi1/0 | SW3 Gi0/2 | Po3 member | Static EtherChannel |
| L8 | PC1 e0 | SW2 Gi1/1 | — | Access port VLAN 10 |
| L9 | PC2 e0 | SW3 Gi1/1 | — | Access port VLAN 20 |

### Console Access Table

| Device | Port | Connection Command |
|--------|------|--------------------|
| SW1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| SW2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| SW3 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |

> Ports are dynamically assigned by EVE-NG. Check the EVE-NG web UI node properties or
> run `python3 setup_lab.py --host <eve-ng-ip>` to push initial configs automatically.

---

## 4. Base Configuration

The following configuration is already loaded by `setup_lab.py` (from `initial-configs/`):

**Pre-loaded on all switches (SW1, SW2, SW3):**
- VLAN database: VLAN 10 (SALES), 20 (ENGINEERING), 30 (MANAGEMENT_HOSTS), 99 (NATIVE_MGMT)
- Management SVI on VLAN 99 (SW1=.99.1, SW2=.99.2, SW3=.99.3)
- All inter-switch interfaces configured as individual 802.1Q trunks (native VLAN 99, allowed 10,20,30,99)

**Pre-loaded on R1:**
- Sub-interface configuration for inter-VLAN routing (VLAN 10, 20, 30, 99)
- Loopback0: 1.1.1.1/32

**NOT pre-configured — the student configures these in this lab:**
- EtherChannel bundles (port-channel interfaces)
- LACP protocol configuration on any switch
- PAgP protocol configuration on any switch
- Static EtherChannel membership on any switch
- EtherChannel load-balancing method

---

## 5. Lab Challenge: Core Implementation

> Work through each task in order. Verify each task before moving to the next.
> Consult Section 8 only if you are stuck after 10 minutes on a task.

---

### Task 1: LACP EtherChannel — Po1 (SW1 ↔ SW2)

- Configure a two-member EtherChannel (channel-group 1) between SW1 and SW2 using LACP.
- Assign SW1 as the active LACP role and SW2 as the passive LACP role on both member links.
- Configure the resulting Port-channel1 interface as an 802.1Q trunk on both switches:
  native VLAN 99, allowed VLANs 10, 20, 30, and 99, with DTP disabled.

**Verification:** `show etherchannel summary` must show Po1 as `SU` (Layer 2, in use) with both Gi0/1 and Gi0/2 listed as `P` (bundled in port-channel). `show lacp neighbor` must show the neighbor's MAC and port for both member links.

---

### Task 2: PAgP EtherChannel — Po2 (SW1 ↔ SW3)

- Configure a two-member EtherChannel (channel-group 2) between SW1 and SW3 using PAgP.
- Assign SW1 as the desirable PAgP role and SW3 as the auto PAgP role on both member links.
- Configure Port-channel2 as an 802.1Q trunk on both switches: same VLAN parameters as Po1.

**Verification:** `show etherchannel summary` must show Po2 as `SU` with both Gi0/3 and Gi1/0 as `P`. `show pagp neighbor` must show the neighbor's device ID for both member links.

---

### Task 3: Static EtherChannel — Po3 (SW2 ↔ SW3)

- Configure a two-member EtherChannel (channel-group 3) between SW2 and SW3 using static mode
  (no negotiation protocol) on both ends.
- Configure Port-channel3 as an 802.1Q trunk on both switches: same VLAN parameters as Po1 and Po2.

**Verification:** `show etherchannel summary` must show Po3 as `SU` with both member links as `P`. Note that no `show lacp` or `show pagp` output exists for this bundle — static mode has no protocol state.

---

### Task 4: EtherChannel Load Balancing

- Configure all three switches to use source-destination MAC address hashing for EtherChannel
  load distribution.
- Verify the active load-balance method on each switch.

**Verification:** `show etherchannel load-balance` must report `EtherChannel Load-Balancing Method: src-dst-mac` on all three switches.

---

### Task 5: Trunk Verification Across Bundles

- Confirm that all three port-channel interfaces (Po1, Po2, Po3) are operating as 802.1Q trunks.
- Verify that VLANs 10, 20, 30, and 99 are active and forwarding on each port-channel trunk.
- Confirm end-to-end reachability: PC1 (VLAN 10) must be able to ping PC2 (VLAN 20) via R1.

**Verification:** `show interfaces trunk` must list Po1, Po2, and Po3 as trunk interfaces with the correct native VLAN and allowed VLAN list. `ping 192.168.20.10` from PC1 must succeed.

---

### Task 6: EtherChannel Mismatch Troubleshooting

The network team has reported that a newly added EtherChannel bundle is not forming. Based on
the following symptom description, identify and resolve the misconfiguration without looking
at device configs directly — use only `show` commands to diagnose.

**Symptom:** SW1's `show etherchannel summary` shows Po1 member Gi0/2 in `I` (individual)
state rather than `P` (bundled). SW2 Gi0/2 also shows `I` state.

- Determine whether the failure is caused by a protocol mismatch, speed mismatch, or VLAN
  mismatch using the appropriate verification commands.
- Restore the member to bundled state without disrupting the rest of Po1 or any other traffic.

**Verification:** After the fix, `show etherchannel summary` must show all Po1 members as `P` and the bundle as `SU`. `show etherchannel detail` must show no suspended or individual ports.

---

## 6. Verification & Analysis

### LACP Bundle State (Po1 — SW1 perspective)

```
SW1# show etherchannel summary
Flags:  D - down        P - bundled in port-channel
        I - stand-alone s - suspended
        H - Hot-standby (LACP only)
        R - Layer3      S - Layer2
        U - in use      f - failed to allocate aggregator

        M - not in use, minimum links not met
        u - unsuitable for bundling
        w - waiting to be aggregated
        d - default port

Number of channel-groups in use: 2     ! ← SW1 terminates Po1 and Po2
Number of aggregators:           2

Group  Port-channel  Protocol    Ports
------+-------------+-----------+-----------------------------------------------
1      Po1(SU)          LACP      Gi0/1(P)    Gi0/2(P)    ! ← SU = L2 in-use; P = bundled
2      Po2(SU)          PAgP      Gi0/3(P)    Gi1/0(P)    ! ← PAgP bundle also up
```

### LACP Neighbor Detail

```
SW1# show lacp 1 neighbor
Channel group 1 neighbors

                 LACP port     Admin  Oper   Port    Port
Port      Flags  State         Key    Key    Number  State
Gi0/1     SA     bndl          0x1    0x1    0x2     0x3D  ! ← SA = active, bndl = bundled
Gi0/2     SA     bndl          0x1    0x1    0x3     0x3D

Partner's information:
                 LACP port     Admin  Oper   Port    Port
Port      Flags  State         Key    Key    Number  State
Gi0/1     FA     bndl          0x0    0x1    0x2     0x3C  ! ← FA = passive on SW2
Gi0/2     FA     bndl          0x0    0x1    0x3     0x3C
```

### PAgP Bundle State (Po2 — SW1 perspective)

```
SW1# show pagp 2 neighbor
Flags:  S - Device is sending Slow hello.  C - Device is in Consistent state.
        A - Device is in Auto mode.        P - Device learns on physical port.

Channel group 2 neighbors:
         Partner              Partner          Partner         Partner Group
Port      Name                Device-ID        Port       Age  Flags   Cap.
Gi0/3     SW3                 aabb.cc00.0300   Gi0/3      20s  SC      10001 ! ← SW3 is consistent
Gi1/0     SW3                 aabb.cc00.0300   Gi1/0      18s  SC      10001
```

### Static Bundle State (Po3 — SW2 perspective)

```
SW2# show etherchannel summary
Group  Port-channel  Protocol    Ports
------+-------------+-----------+-----------------------------------------------
1      Po1(SU)          LACP      Gi0/1(P)    Gi0/2(P)
3      Po3(SU)           -        Gi0/3(P)    Gi1/0(P)    ! ← Protocol is "-" for static
```

### Trunk State Over Port-Channels

```
SW1# show interfaces trunk

Port        Mode         Encapsulation  Status        Native vlan
Gi0/0       on           802.1q         trunking      99          ! ← R1 uplink
Po1         on           802.1q         trunking      99          ! ← LACP bundle
Po2         on           802.1q         trunking      99          ! ← PAgP bundle

Port        Vlans allowed on trunk
Gi0/0       10,20,30,99
Po1         10,20,30,99  ! ← inherited from port-channel config
Po2         10,20,30,99

Port        Vlans allowed and active in management domain
Po1         10,20,30,99  ! ← all VLANs must appear here

Port        Vlans in spanning tree forwarding state and not pruned
Po1         10,20,30,99  ! ← STP sees the bundle, not individual links
Po2         10,20,30,99
```

### Load Balance Verification

```
SW1# show etherchannel load-balance
EtherChannel Load-Balancing Configuration:
        src-dst-mac   ! ← must match what you configured

EtherChannel Load-Balancing Addresses Used Per-Protocol:
Non-IP: Source XOR Destination MAC address
  IP: Source XOR Destination MAC address
```

### Individual Port Mismatch Detection

```
SW1# show etherchannel detail
...
Port: Gi0/2
------------
Link state: bundled    ! ← if "stand-alone" here, member is NOT in bundle
Port state = Up Mstr Assoc In-Bndl
Channel group: 1    Mode: Active          Gcchange: -
...
Age of the port in the current state: 00d:00h:05m:03s

! If you see "stand-alone" check:
SW1# show interfaces Gi0/2 trunk
! Look for native vlan or allowed vlan mismatch vs the port-channel
```

---

## 7. Verification Cheatsheet

### EtherChannel Bundle Status

```
show etherchannel summary
show etherchannel detail
show etherchannel <group> port-channel
```

| Command | What to Look For |
|---------|-----------------|
| `show etherchannel summary` | Bundle flags: `SU` = L2 in use; member flags: `P` = bundled, `I` = individual (broken), `s` = suspended |
| `show etherchannel detail` | Per-port state, age, mismatches |
| `show etherchannel load-balance` | Active hash algorithm |

> **Exam tip:** `I` (individual) on a member means the port is NOT bundled — it is forwarding independently and STP may block it.

### LACP Verification

```
show lacp neighbor
show lacp internal
show lacp <group> neighbor
show lacp counters
```

| Command | What to Look For |
|---------|-----------------|
| `show lacp neighbor` | Partner system MAC, port key, and state flags (`A`=active, `P`=passive) |
| `show lacp internal` | Local port state, admin key, oper key — keys must match across members |
| `show lacp counters` | LACPDUs sent/received — a port sending but not receiving indicates a unidirectional link |

> **Exam tip:** LACP `passive`/`passive` = no LACPDUs sent from either side = no bundle.

### PAgP Verification

```
show pagp neighbor
show pagp internal
show pagp <group> neighbor
show pagp counters
```

| Command | What to Look For |
|---------|-----------------|
| `show pagp neighbor` | Partner device ID, port name, and state (`S`=slow, `C`=consistent, `A`=auto) |
| `show pagp internal` | Local state, channel flags, learn method |
| `show pagp counters` | PAgP frames sent/received — zero received from a port indicates the remote is not running PAgP |

> **Exam tip:** PAgP `auto`/`auto` = no PAgP frames sent = no bundle.

### Port-Channel Interface

```
show interfaces port-channel <number>
show interfaces port-channel <number> trunk
show interfaces port-channel <number> etherchannel
```

| Command | What to Look For |
|---------|-----------------|
| `show interfaces port-channel N` | Line protocol must be `up`; shows member count |
| `show interfaces trunk` | Lists port-channel interfaces alongside physical trunks |
| `show etherchannel N port-channel` | Ports bundled, load-share algorithm, hash buckets |

### Common EtherChannel Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| Member shows `I` (individual) | Trunk VLAN mismatch, native VLAN mismatch, or speed/duplex mismatch |
| Member shows `s` (suspended) | Protocol mismatch (LACP vs. PAgP vs. static) or configuration inconsistency |
| Po shows `SD` (standalone down) | No members are up |
| `show lacp neighbor` empty | Remote end running PAgP or static mode; or cable down |
| `show pagp neighbor` empty | Remote end running LACP or static mode; or cable down |
| Bundle forms but traffic is uneven | Load-balance algorithm does not spread the flow space |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Task 1: LACP EtherChannel — Po1

<details>
<summary>Click to view SW1 Configuration</summary>

```bash
! SW1 — LACP active on both members
interface GigabitEthernet0/1
 channel-group 1 mode active

interface GigabitEthernet0/2
 channel-group 1 mode active

interface Port-channel1
 description LACP_PO1_TO_SW2
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk native vlan 99
 switchport trunk allowed vlan 10,20,30,99
 switchport nonegotiate
```
</details>

<details>
<summary>Click to view SW2 Configuration</summary>

```bash
! SW2 — LACP passive on both members
interface GigabitEthernet0/1
 channel-group 1 mode passive

interface GigabitEthernet0/2
 channel-group 1 mode passive

interface Port-channel1
 description LACP_PO1_TO_SW1
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk native vlan 99
 switchport trunk allowed vlan 10,20,30,99
 switchport nonegotiate
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show etherchannel summary
show lacp 1 neighbor
show interfaces port-channel1
show interfaces port-channel1 trunk
```
</details>

---

### Task 2: PAgP EtherChannel — Po2

<details>
<summary>Click to view SW1 Configuration</summary>

```bash
! SW1 — PAgP desirable on both members
interface GigabitEthernet0/3
 channel-group 2 mode desirable

interface GigabitEthernet1/0
 channel-group 2 mode desirable

interface Port-channel2
 description PAGP_PO2_TO_SW3
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk native vlan 99
 switchport trunk allowed vlan 10,20,30,99
 switchport nonegotiate
```
</details>

<details>
<summary>Click to view SW3 Configuration</summary>

```bash
! SW3 — PAgP auto on both members
interface GigabitEthernet0/3
 channel-group 2 mode auto

interface GigabitEthernet1/0
 channel-group 2 mode auto

interface Port-channel2
 description PAGP_PO2_TO_SW1
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk native vlan 99
 switchport trunk allowed vlan 10,20,30,99
 switchport nonegotiate
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show etherchannel summary
show pagp 2 neighbor
show interfaces port-channel2 trunk
```
</details>

---

### Task 3: Static EtherChannel — Po3

<details>
<summary>Click to view SW2 Configuration</summary>

```bash
! SW2 — static mode on both members
interface GigabitEthernet0/3
 channel-group 3 mode on

interface GigabitEthernet1/0
 channel-group 3 mode on

interface Port-channel3
 description STATIC_PO3_TO_SW3
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk native vlan 99
 switchport trunk allowed vlan 10,20,30,99
 switchport nonegotiate
```
</details>

<details>
<summary>Click to view SW3 Configuration</summary>

```bash
! SW3 — static mode on both members
interface GigabitEthernet0/1
 channel-group 3 mode on

interface GigabitEthernet0/2
 channel-group 3 mode on

interface Port-channel3
 description STATIC_PO3_TO_SW2
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk native vlan 99
 switchport trunk allowed vlan 10,20,30,99
 switchport nonegotiate
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show etherchannel summary
show interfaces port-channel3 trunk
! Note: show lacp and show pagp produce no output for static bundles
```
</details>

---

### Task 4: EtherChannel Load Balancing

<details>
<summary>Click to view Configuration (all switches)</summary>

```bash
! On SW1, SW2, and SW3 (global command)
port-channel load-balance src-dst-mac
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show etherchannel load-balance
```
</details>

---

### Task 5: Trunk Verification Across Bundles

<details>
<summary>Click to view Verification Commands</summary>

```bash
! On SW1 — verify all trunks including port-channels
show interfaces trunk

! On SW2 — verify Po1 and Po3
show interfaces trunk
show interfaces port-channel1 trunk
show interfaces port-channel3 trunk

! End-to-end reachability from PC1
ping 192.168.20.10  ! PC2 VLAN 20
ping 192.168.10.1   ! R1 VLAN 10 gateway
```
</details>

---

### Task 6: EtherChannel Mismatch Troubleshooting

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! Step 1 — confirm which member is broken
SW1# show etherchannel summary
! Look for 'I' flag on Gi0/2

! Step 2 — check for VLAN/trunk mismatch on the affected member
SW1# show interfaces Gi0/2 trunk
SW2# show interfaces Gi0/2 trunk
! Compare native VLAN and allowed VLAN on both sides

! Step 3 — check for protocol state
SW1# show lacp 1 internal
! Look for mismatched admin/oper key on Gi0/2 vs Gi0/1

! Step 4 — check interface description for physical connectivity
SW1# show interfaces Gi0/2 status
! Should show 'connected' at correct speed
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! If native VLAN mismatch (e.g., Gi0/2 has native vlan 1 instead of 99):
SW1(config)# interface GigabitEthernet0/2
SW1(config-if)# switchport trunk native vlan 99

SW2(config)# interface GigabitEthernet0/2
SW2(config-if)# switchport trunk native vlan 99

! If allowed VLAN list mismatch:
SW1(config-if)# switchport trunk allowed vlan 10,20,30,99
SW2(config-if)# switchport trunk allowed vlan 10,20,30,99

! Verify recovery
SW1# show etherchannel summary
! Gi0/2 should now show 'P'
```
</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. Inject the fault first, then
diagnose and fix using only show commands.

### Workflow

```bash
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>   # reset to known-good solution
python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>  # inject Ticket 1
# diagnose and fix using show commands
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>   # restore between tickets
```

> Note: `setup_lab.py` pushes the *initial* (bare-minimum) configs and is only
> used once, before you start Section 4. For troubleshooting, always reset
> with `apply_solution.py`, which pushes the full solution configs.

---

### Ticket 1 — Po1 Reports One Member as Individual

The overnight monitoring system flagged that Po1 on SW1 shows only one active member. The
network team confirmed both physical cables between SW1 and SW2 are connected and the
LEDs are lit.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>`

**Success criteria:** Both Gi0/1 and Gi0/2 show as `P` (bundled) in `show etherchannel summary`
on both SW1 and SW2. Po1 line protocol is `up`.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! 1. Identify which member is broken
SW1# show etherchannel summary
! Look for 'I' flag on one of the Po1 members

! 2. Check the suspected member's trunk parameters
SW1# show interfaces Gi0/2 trunk
SW2# show interfaces Gi0/2 trunk
! Compare native VLAN on both sides

! 3. Check LACP neighbor for the broken member
SW1# show lacp 1 neighbor
! A port in 'I' state will not appear in LACP neighbor table for that member

! 4. Confirm speed and duplex
SW1# show interfaces Gi0/2 status
! Must show 'a-1000' or 'full' with matching values on both ends
```
</details>

<details>
<summary>Click to view Fix</summary>

The fault is a native VLAN mismatch on Gi0/2: SW2 Gi0/2 has been changed to native VLAN 1.

```bash
SW2(config)# interface GigabitEthernet0/2
SW2(config-if)# switchport trunk native vlan 99

! Verify recovery
SW1# show etherchannel summary
! Both Gi0/1 and Gi0/2 must now show 'P'
```
</details>

---

### Ticket 2 — Po2 Is Down Between SW1 and SW3

The engineering team reports they cannot reach PC2 from any device in the campus. SW1's
routing table shows no path to the VLAN 20 subnet.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py --host <eve-ng-ip>`

**Success criteria:** `show etherchannel summary` on SW1 shows Po2 as `SU` with both
Gi0/3 and Gi1/0 as `P`. PC1 can ping PC2.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! 1. Check bundle state on SW1
SW1# show etherchannel summary
! Po2 likely shows 'SD' (standalone down) or members show 's' (suspended)

! 2. Check PAgP neighbor
SW1# show pagp 2 neighbor
! If output is empty — no PAgP frames received from SW3

! 3. Check SW3's EtherChannel config
SW3# show etherchannel summary
! Look at the Protocol column — should show PAgP, not LACP or '-'

! 4. Verify mode on SW3 members
SW3# show run interface GigabitEthernet0/3
SW3# show run interface GigabitEthernet1/0
! If mode is 'active' (LACP) instead of 'auto' (PAgP), that is the mismatch
```
</details>

<details>
<summary>Click to view Fix</summary>

The fault is a protocol mismatch: SW3 member interfaces were set to LACP `active` while SW1
is running PAgP `desirable`.

```bash
SW3(config)# interface GigabitEthernet0/3
SW3(config-if)# channel-group 2 mode auto

SW3(config)# interface GigabitEthernet1/0
SW3(config-if)# channel-group 2 mode auto

! Verify recovery
SW1# show etherchannel summary
SW1# show pagp 2 neighbor
! Po2 must show SU; SW3 must appear as PAgP neighbor
```
</details>

---

### Ticket 3 — Po3 Entire Bundle Is Down

SW2's network team reports that SW3 is unreachable from the SW2 management SVI. PC2 is
also not pingable from the campus.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py --host <eve-ng-ip>`

**Success criteria:** `show etherchannel summary` on SW2 shows Po3 as `SU` with both
Gi0/3 and Gi1/0 as `P`. SW2 can ping SW3's management IP 192.168.99.3.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! 1. Check bundle state
SW2# show etherchannel summary
! Po3 likely shows 'SD' or members show 's'

! 2. For a static bundle there is no protocol — check member consistency
SW2# show interfaces Gi0/3 trunk
SW2# show interfaces Gi1/0 trunk
SW3# show interfaces Gi0/1 trunk
SW3# show interfaces Gi0/2 trunk
! Compare allowed VLAN lists on all four member interfaces

! 3. Check channel-group mode
SW2# show run interface Gi0/3
SW3# show run interface Gi0/1
! Both must show 'channel-group 3 mode on'
! If one side is 'mode active' or 'mode desirable', that is the mismatch

! 4. Check port-channel interface state
SW2# show interfaces port-channel3
! If 'line protocol is down' — no members are bundled
```
</details>

<details>
<summary>Click to view Fix</summary>

The fault is a static/dynamic mode mismatch: SW3 Gi0/1 and Gi0/2 were changed to
`channel-group 3 mode passive` (LACP), while SW2 is configured as `mode on` (static).

```bash
SW3(config)# interface GigabitEthernet0/1
SW3(config-if)# channel-group 3 mode on

SW3(config)# interface GigabitEthernet0/2
SW3(config-if)# channel-group 3 mode on

! Verify recovery
SW2# show etherchannel summary
SW2# ping 192.168.99.3
! Po3 SU; management ping to SW3 succeeds
```
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] Po1 (LACP) between SW1 and SW2 is `SU` with both members `P`
- [ ] `show lacp 1 neighbor` on SW1 shows SW2 as the LACP partner
- [ ] Po2 (PAgP) between SW1 and SW3 is `SU` with both members `P`
- [ ] `show pagp 2 neighbor` on SW1 shows SW3 as the PAgP partner
- [ ] Po3 (static) between SW2 and SW3 is `SU` with both members `P`
- [ ] `show etherchannel load-balance` reports `src-dst-mac` on all three switches
- [ ] `show interfaces trunk` on SW1 lists Po1 and Po2 with correct native/allowed VLANs
- [ ] PC1 can ping PC2 (192.168.20.10) via R1 inter-VLAN routing
- [ ] PC1 can ping SW1 management IP (192.168.99.1)

### Troubleshooting

- [ ] Ticket 1 resolved: both Po1 members return to `P` state after native VLAN fix
- [ ] Ticket 2 resolved: Po2 re-forms after correcting PAgP/LACP protocol mismatch on SW3
- [ ] Ticket 3 resolved: Po3 re-forms after correcting static/LACP mode mismatch on SW3
