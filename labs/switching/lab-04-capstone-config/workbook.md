# Lab 04 — Layer 2 Full Configuration (Capstone I)

## Table of Contents

1. [Concepts & Skills Covered](#1-concepts--skills-covered)
2. [Topology & Scenario](#2-topology--scenario)
3. [Hardware & Environment Specifications](#3-hardware--environment-specifications)
4. [Base Configuration](#4-base-configuration)
5. [Lab Challenge: Full Protocol Mastery](#5-lab-challenge-full-protocol-mastery)
6. [Verification & Analysis](#6-verification--analysis)
7. [Verification Cheatsheet](#7-verification-cheatsheet)
8. [Solutions (Spoiler Alert!)](#8-solutions-spoiler-alert)
9. [Troubleshooting Scenarios](#9-troubleshooting-scenarios)
10. [Lab Completion Checklist](#10-lab-completion-checklist)

---

## 1. Concepts & Skills Covered

**Exam Objective:** Blueprint 3.1, 3.1.a, 3.1.b, 3.1.c — Layer 2 (VLANs & trunking, EtherChannels, Spanning Tree).

This is the Layer 2 capstone. It consolidates the three progressive labs (VLANs + trunking, EtherChannel, Rapid PVST+ / enhancements) into a **single clean-slate build** on the same topology. There is no guided walk-through — you design the port plan, decide root placement, pick bundle modes, and drive the network to end-to-end reachability on your own.

### VLANs, trunks, and the native VLAN (3.1.a)

Every switch needs the same VLAN database (10, 20, 30, 99) before a trunk will carry those VLANs cleanly. Trunks on IOSvL2 require an explicit encapsulation (`switchport trunk encapsulation dot1q`) and — for deterministic behaviour — a disabled DTP (`switchport nonegotiate`). The native VLAN must match on both ends of every trunk; a mismatch does not break the link but produces CDP logs and black-holes untagged traffic.

| Setting | Command | Why |
|---------|---------|-----|
| Encapsulation | `switchport trunk encapsulation dot1q` | Required on IOSvL2 before `mode trunk` is accepted |
| Mode | `switchport mode trunk` | Hard-coded trunk (no DTP) |
| Native VLAN | `switchport trunk native vlan 99` | All management traffic rides VLAN 99 untagged |
| Allowed list | `switchport trunk allowed vlan 10,20,30,99` | Minimises broadcast domain scope |
| DTP | `switchport nonegotiate` | Prevents mode flapping / DTP injection |

### EtherChannel bundle types (3.1.b)

Three bundles, three protocols — the capstone deliberately exercises all of them:

| Bundle | Pair | Protocol | Modes |
|--------|------|----------|-------|
| Po1 | SW1 ↔ SW2 | LACP (802.3ad) | active / passive |
| Po2 | SW1 ↔ SW3 | PAgP (Cisco) | desirable / auto |
| Po3 | SW2 ↔ SW3 | Static | on / on |

Each member port must have **identical trunk parameters** (encapsulation, mode, native VLAN, allowed VLAN list) before the bundle will come up as `Po… (SU)`. Configure all L2 parameters on both the physical members and the `Port-channel` interface — IOSvL2 does not auto-sync every knob.

### Rapid PVST+ and root engineering (3.1.c)

Rapid PVST+ runs one 802.1w instance per VLAN. Each VLAN elects its own root. Priority moves in 4096 increments (Extended System ID occupies the low 12 bits). The capstone uses the same deterministic root plan as Lab 02, now layered onto all three bundles at once:

- **SW1 = root for VLANs 10, 30, 99** — priority 4096. Keeps northbound traffic toward the R1 uplink on the shortest path.
- **SW2 = root for VLAN 20** — priority 4096. Engineering traffic roots near PC1's segment.
- **Secondary roots** are placed at priority 28672 so failover is deterministic (never 32768 default).

### STP enhancements — PortFast, BPDU guard, Root guard

| Enhancement | Where | Effect |
|-------------|-------|--------|
| PortFast | PC-facing access ports | Skip listening/learning; forward immediately |
| BPDU guard | Same PC-facing ports | Err-disable on any BPDU (rogue-switch protection) |
| Root guard | Designated ports facing neighbour switches (bundles) | Blocks into `root-inconsistent` if a superior BPDU arrives |

Root guard goes on ports where the local switch is root for **every** VLAN on that port and no neighbour should ever challenge it. In this topology SW1 is not root for VLAN 20, so Po1 and Po2 carry legitimate superior BPDUs from SW2. Enabling root guard on those bundles would put them into `root-inconsistent` for VLAN 20. Only SW1's **Gi0/0** (R1-facing trunk) qualifies — R1 never participates in STP elections and will never send a superior BPDU. BPDU guard goes on the **host-facing** access ports only — never on an inter-switch link.

### Router-on-a-stick inter-VLAN routing

R1's Gi0/0 is a trunk; one sub-interface per VLAN provides the default gateway. Sub-interface `.99` carries the native VLAN and must use the `native` keyword on its `encapsulation dot1Q` line so R1 accepts untagged frames.

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| Design a clean-slate L2 build | Translate a VLAN plan + cabling table into a working port-assignment blueprint without step-by-step prompts |
| Bundle with three protocols | Configure LACP, PAgP, and static EtherChannels side-by-side and verify each comes up |
| Engineer deterministic STP | Place primary and secondary roots per VLAN; verify role tables across bundles |
| Apply layered protection | Combine PortFast + BPDU guard at the edge with Root guard on distribution uplinks |
| Prove end-to-end reachability | Use `ping`, `traceroute`, `show ip route`, and `show cdp neighbors` to validate every VLAN reaches R1 and the other VLANs |

---

## 2. Topology & Scenario

### Network Diagram

```
                             ┌──────────────────┐
                             │       R1         │
                             │ (Router-on-stick)│
                             │  Lo0: 1.1.1.1    │
                             └────────┬─────────┘
                                Gi0/0 │ trunk (dot1q)
                                      │ native VLAN 99, allowed 10,20,30,99
                                      │
                             ┌────────┴─────────┐
                             │      SW1         │
                             │ Root 10/30/99    │
                             │   pri 4096       │
                             └──┬────────────┬──┘
                     Po1 (LACP) │            │ Po2 (PAgP)
                     Gi0/1,Gi0/2│            │ Gi0/3,Gi1/0
                                │            │
                  ┌─────────────┴───┐    ┌───┴───────────┐
                  │      SW2        │    │     SW3       │
                  │ Root VLAN 20    │    │ 2ndary VLAN 20│
                  │  pri 4096       │    │  pri 28672    │
                  └──┬──────────┬───┘    └───┬───────┬───┘
              Gi1/1  │          │Gi0/3       │Gi0/1  │Gi1/1
              access │          │Gi1/0       │Gi0/2  │access
              VLAN10 │          │ Po3 (static, mode on) │ VLAN 20
                     │          └───────┬────┘       │
                     │                  │            │
                 ┌───┴────┐         ┌───┴────┐
                 │  PC1   │         │  PC2   │
                 │.10.10  │         │.20.10  │
                 └────────┘         └────────┘
             192.168.10.0/24     192.168.20.0/24
```

### Scenario

Acme Corp is standing up a new campus floor. The cabling crew has racked three switches (SW1 distribution, SW2/SW3 access), run dual fibres between every pair, and plugged in one PC per access switch and a router (R1) to SW1 for inter-VLAN routing. You log in to find **clean switches** — only hostnames and management IPs are present. IT management has handed you this requirements list:

- Four VLANs: 10 Sales, 20 Engineering, 30 Management-Hosts, 99 Native/Mgmt.
- Every inter-switch pair must be a **single logical trunk** — no redundant physical links allowed to stay as individual interfaces. Mix of LACP, PAgP, and static to match existing vendor contracts.
- **SW1 is the designated L2 core** — it must root VLAN 10, 30, 99. **SW2 roots VLAN 20** for the Engineering team. Deterministic failover (no default priorities).
- PC ports must come up instantly and reject any rogue switch.
- No downstream neighbour may ever claim root — lock the distribution bundles.
- R1 provides gateways for all four VLANs (including the native VLAN).
- End state: PC1 ↔ PC2 ping succeeds, and every switch can ping 1.1.1.1 through its management VLAN.

Everything else — port assignments, bundle numbering, interface descriptions — is yours to design.

---

## 3. Hardware & Environment Specifications

### Device Inventory

| Device | Platform | Role | Loopback0 |
|--------|----------|------|-----------|
| SW1 | IOSvL2 | Distribution / root for VLAN 10,30,99 | n/a |
| SW2 | IOSvL2 | Access (PC1) / root for VLAN 20 | n/a |
| SW3 | IOSvL2 | Access (PC2) / secondary root VLAN 20 | n/a |
| R1  | IOSv   | Inter-VLAN router (router-on-a-stick) | 1.1.1.1/32 |
| PC1 | VPC    | End host — 192.168.10.10/24 | — |
| PC2 | VPC    | End host — 192.168.20.10/24 | — |

### Cabling Table

| Link | A end | B end | Type | Purpose |
|------|-------|-------|------|---------|
| L1 | R1 Gi0/0 | SW1 Gi0/0 | Trunk | Router-on-a-stick uplink |
| L2 | SW1 Gi0/1 | SW2 Gi0/1 | Po1 member (LACP) | Distribution ↔ access |
| L3 | SW1 Gi0/2 | SW2 Gi0/2 | Po1 member (LACP) | Distribution ↔ access |
| L4 | SW1 Gi0/3 | SW3 Gi0/3 | Po2 member (PAgP) | Distribution ↔ access |
| L5 | SW1 Gi1/0 | SW3 Gi1/0 | Po2 member (PAgP) | Distribution ↔ access |
| L6 | SW2 Gi0/3 | SW3 Gi0/1 | Po3 member (static) | Access ↔ access |
| L7 | SW2 Gi1/0 | SW3 Gi0/2 | Po3 member (static) | Access ↔ access |
| L8 | PC1 eth0 | SW2 Gi1/1 | Access VLAN 10 | Host |
| L9 | PC2 eth0 | SW3 Gi1/1 | Access VLAN 20 | Host |

### Console Access Table

| Device | Port | Connection Command |
|--------|------|--------------------|
| SW1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| SW2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| SW3 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R1  | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| PC1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| PC2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |

---

## 4. Base Configuration

**Clean slate.** `initial-configs/` contains only:

- Hostname (`SW1`, `SW2`, `SW3`, `R1`)
- `no ip domain-lookup`
- Console / VTY `exec-timeout 0 0` + `logging synchronous`
- R1 Loopback0 1.1.1.1/32
- No VLANs, no trunks, no EtherChannels, no STP tuning — build everything yourself.

**NOT pre-loaded (you must configure):**

- VLAN database (10, 20, 30, 99 with names)
- Trunk links between all switch pairs (with native VLAN 99, allowed list 10,20,30,99)
- EtherChannel bundles (Po1 LACP, Po2 PAgP, Po3 static)
- EtherChannel load-balancing method
- Rapid PVST+ mode and per-VLAN priorities
- PortFast + BPDU guard on PC-facing access ports
- Root guard on distribution-facing trunks / bundles
- Router-on-a-stick sub-interfaces on R1
- Access port assignments for PC1 and PC2
- Management SVI (VLAN 99) on each switch with its IP

---

## 5. Lab Challenge: Full Protocol Mastery

> This is a capstone lab. No step-by-step guidance is provided.
> Configure the complete Layer 2 solution from scratch — hostnames and management addressing are pre-configured; everything else is yours to build.
> All blueprint bullets for this chapter (3.1, 3.1.a, 3.1.b, 3.1.c) must be addressed.

**Target end state:**

- Four VLANs present on SW1/SW2/SW3 with matching names.
- Every inter-switch link is a member of an EtherChannel: **Po1 LACP (SW1↔SW2), Po2 PAgP (SW1↔SW3), Po3 static (SW2↔SW3)**.
- Global `port-channel load-balance src-dst-mac` on every switch.
- All trunks (physical members and `Port-channel` interfaces) use dot1q, native VLAN 99, allowed list `10,20,30,99`, and `switchport nonegotiate`.
- `spanning-tree mode rapid-pvst` on every switch.
- SW1 priority 4096 for VLANs 10/30/99; priority 8192 for VLAN 20 (so SW1 never wins VLAN 20 even if SW2's bundle goes down).
- SW2 priority 4096 for VLAN 20; priority 28672 for VLANs 10/30/99.
- SW3 priority 28672 for VLAN 20 (other VLANs: default).
- PC-facing access ports: `switchport mode access`, `access vlan 10/20`, `spanning-tree portfast`, `spanning-tree bpduguard enable`.
- `spanning-tree guard root` on SW1's R1-facing trunk (Gi0/0) **only**. Do NOT apply root guard to Po1 or Po2 — SW2 is root for VLAN 20 and sends legitimate superior BPDUs on those bundles; enabling root guard there would put them into `root-inconsistent` for VLAN 20, violating the empty `show spanning-tree inconsistentports` acceptance test.
- R1 Gi0/0 with no IP; sub-interfaces `.10/.20/.30/.99` each with `encapsulation dot1Q <id> [native for 99]` and the VLAN gateway IP.
- Spare switch interfaces (any Gi not in use) must be `shutdown`.
- Management SVI on VLAN 99: SW1 .1, SW2 .2, SW3 .3; R1 .99 gateway .254.

**Acceptance tests (all must pass):**

1. `show etherchannel summary` on SW1/SW2/SW3 shows `Po1(SU)`, `Po2(SU)`, `Po3(SU)` where applicable.
2. `show spanning-tree vlan 10` on SW1 → "This bridge is the root." `show spanning-tree vlan 20` on SW2 → same.
3. `show spanning-tree inconsistentports` is empty on every switch.
4. PC1 (`ping 192.168.20.10`) reaches PC2 across VLANs through R1.
5. Every switch can ping 1.1.1.1 and 192.168.99.254 from its VLAN 99 SVI.
6. `show ip int brief | include Gi` on R1 shows `.10/.20/.30/.99` sub-interfaces up/up.

---

## 6. Verification & Analysis

Run these after your build; every highlighted line must match.

### VLAN database

```
SW1# show vlan brief
VLAN Name                             Status    Ports
---- -------------------------------- --------- -----------------------
1    default                          active    Gi1/1, Gi1/2, Gi1/3
10   SALES                            active                               ! ← must exist, name SALES
20   ENGINEERING                      active                               ! ← must exist
30   MANAGEMENT_HOSTS                 active                               ! ← must exist
99   NATIVE_MGMT                      active                               ! ← must exist
```

### Trunks carry the right VLANs

```
SW1# show interfaces trunk
Port         Mode         Encapsulation  Status        Native vlan
Gi0/0        on           802.1q         trunking      99             ! ← native 99, not 1
Po1          on           802.1q         trunking      99
Po2          on           802.1q         trunking      99

Port         Vlans allowed on trunk
Gi0/0        10,20,30,99                                              ! ← exactly these four
Po1          10,20,30,99
Po2          10,20,30,99
```

### EtherChannel summary

```
SW1# show etherchannel summary
Flags:  D - down        P - bundled in port-channel
        s - suspended   H - Hot-standby (LACP only)
Number of channel-groups in use: 2
Group  Port-channel  Protocol    Ports
------+-------------+-----------+-----------------------------
1      Po1(SU)         LACP      Gi0/1(P)   Gi0/2(P)            ! ← both members bundled
2      Po2(SU)         PAgP      Gi0/3(P)   Gi1/0(P)            ! ← both members bundled
```

```
SW2# show etherchannel summary
1      Po1(SU)         LACP      Gi0/1(P)   Gi0/2(P)            ! ← passive side bundled
3      Po3(SU)         -         Gi0/3(P)   Gi1/0(P)            ! ← static: Protocol = '-'
```

### Spanning tree — root placement

```
SW1# show spanning-tree vlan 10
VLAN0010
  Spanning tree enabled protocol rstp                            ! ← rstp, not ieee
  Root ID    Priority    4106
             Address     <SW1 MAC>
             This bridge is the root                             ! ← confirm root
  Bridge ID  Priority    4106  (priority 4096 sys-id-ext 10)     ! ← 4096 + VLAN 10
```

```
SW2# show spanning-tree vlan 20
VLAN0020
  Root ID    Priority    4116
             Address     <SW2 MAC>
             This bridge is the root                             ! ← SW2 is root for VLAN 20
```

### No root-inconsistent ports

```
SW1# show spanning-tree inconsistentports
Name        Interface               Inconsistency
-------- -------------------------- ------------------
                                                                 ! ← empty table — Root guard is quiet
```

### End-to-end reachability

```
PC1> ping 192.168.20.10
84 bytes from 192.168.20.10 icmp_seq=1 ttl=63 time=4.2 ms         ! ← ttl=63 → crossed R1 once
84 bytes from 192.168.20.10 icmp_seq=2 ttl=63 time=2.8 ms
```

```
SW1# ping 1.1.1.1 source vlan 99
!!!!!                                                             ! ← 5/5 from mgmt SVI
Success rate is 100 percent (5/5), round-trip min/avg/max = 1/2/4 ms
```

---

## 7. Verification Cheatsheet

### VLAN & Trunk Configuration

```
vlan <id>
 name <NAME>
interface <id>
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk native vlan 99
 switchport trunk allowed vlan 10,20,30,99
 switchport nonegotiate
```

| Command | Purpose |
|---------|---------|
| `vlan 10 / name SALES` | Create and name VLAN in the DB |
| `switchport trunk encapsulation dot1q` | Required on IOSvL2 before `mode trunk` |
| `switchport nonegotiate` | Disable DTP — deterministic trunk |
| `switchport trunk native vlan 99` | Move native off VLAN 1 |
| `switchport trunk allowed vlan 10,20,30,99` | Restrict broadcast domain |

> **Exam tip:** Native VLAN mismatches don't bring a link down; they log a CDP warning and silently drop untagged frames onto the wrong VLAN. Always match both ends.

### EtherChannel Configuration

```
interface <member>
 channel-group <N> mode {active|passive|desirable|auto|on}
interface Port-channel<N>
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk native vlan 99
 switchport trunk allowed vlan 10,20,30,99
```

| Command | Purpose |
|---------|---------|
| `channel-group N mode active` | LACP initiator |
| `channel-group N mode passive` | LACP responder |
| `channel-group N mode desirable` | PAgP initiator |
| `channel-group N mode auto` | PAgP responder |
| `channel-group N mode on` | Static bundle (no protocol) |
| `port-channel load-balance src-dst-mac` | Global distribution algorithm |

> **Exam tip:** `active` + `passive` forms an LACP bundle; `passive` + `passive` does NOT — one side must actively initiate. Same for `desirable` / `auto` on PAgP.

### Spanning Tree

```
spanning-tree mode rapid-pvst
spanning-tree vlan <list> priority <0-61440 in steps of 4096>
interface <edge>
 spanning-tree portfast
 spanning-tree bpduguard enable
interface <uplink>
 spanning-tree guard root
```

| Command | Purpose |
|---------|---------|
| `spanning-tree mode rapid-pvst` | 802.1w per-VLAN |
| `spanning-tree vlan N priority 4096` | Set root |
| `spanning-tree vlan N priority 28672` | Secondary (beats default 32768, loses to 4096) |
| `spanning-tree portfast` | Skip listening/learning on edge |
| `spanning-tree bpduguard enable` | Err-disable if a BPDU arrives |
| `spanning-tree guard root` | Block if superior BPDU arrives (goes `root-inconsistent`) |

> **Exam tip:** BPDU guard and root guard are opposites. BPDU guard assumes the port should NEVER see a BPDU (edge). Root guard assumes the port SHOULD see BPDUs but only from inferior bridges (uplinks into the core). Root guard is **per-port, not per-VLAN** — if any VLAN's legitimate root bridge is reachable through that port, enabling root guard will block that VLAN. In a split-root topology (different VLANs rooted on different switches), root guard can only be applied on ports where the local switch is root for every VLAN on that trunk.

### Router-on-a-Stick

```
interface GigabitEthernet0/0
 no ip address
 no shutdown
interface GigabitEthernet0/0.<vlan>
 encapsulation dot1Q <vlan> [native]
 ip address <gateway> <mask>
```

| Command | Purpose |
|---------|---------|
| `encapsulation dot1Q 10` | Tag with VLAN 10 |
| `encapsulation dot1Q 99 native` | Accept/send untagged on VLAN 99 sub-interface |

### Verification Commands

| Command | What to Look For |
|---------|-----------------|
| `show vlan brief` | All 4 VLANs present, correctly named |
| `show interfaces trunk` | Mode `on`, native 99, allowed 10,20,30,99 |
| `show interfaces Port-channel1 switchport` | Trunking, encap 802.1q, native 99 |
| `show etherchannel summary` | `(SU)` flag on Po1/Po2/Po3; members `(P)` |
| `show etherchannel port-channel` | Protocol column: LACP / PAgP / `-` (static) |
| `show spanning-tree vlan N` | "This bridge is the root" on the intended root |
| `show spanning-tree root` | Per-VLAN root bridge + cost + port |
| `show spanning-tree inconsistentports` | Must be EMPTY (no root-inconsistent / BPDU-inconsistent) |
| `show spanning-tree interface Gi1/1 portfast` | `Portfast: enabled` on access ports |
| `show errdisable recovery` | Causes enabled (BPDU guard should appear if a port is err-disabled) |
| `show cdp neighbors` | All bundled pairs and the R1 trunk appear |
| `show ip interface brief` (R1) | Gi0/0 and sub-interfaces up/up |
| `ping` / `traceroute` (PCs and R1) | End-to-end reachability through R1 |

### Per-VLAN STP Priority Reference

| Priority | Meaning |
|----------|---------|
| 0 | Always wins (use sparingly — no fallback if this device fails) |
| 4096 | Primary root |
| 8192 | Tertiary / explicit loss guard |
| 28672 | Secondary root (beats default 32768) |
| 32768 | Default — do NOT leave in production |
| 61440 | Lowest practical priority (never root) |

### Common L2 Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| Trunk stays in `access` mode | Missing `switchport trunk encapsulation dot1q` before `mode trunk` (IOSvL2) |
| EtherChannel flaps / won't bundle | Member-port config mismatch (VLAN allowed list, native VLAN, speed/duplex, mode/encap) |
| Port-channel up but student-entered `channel-group N mode on` didn't bundle | Mode `on` on one end + `active/passive` on the other — static never negotiates |
| `%SPANTREE-2-ROOTGUARD_BLOCK` syslog | Superior BPDU on a Root-guard port — a neighbour claimed root |
| Access port err-disabled immediately after linkup | BPDU guard triggered — remove BPDU source, then `shutdown` / `no shutdown` |
| PC cannot reach its gateway | Access-VLAN mismatch, or R1 sub-interface not `native` on VLAN 99 if default gateway is VLAN 99 |
| Inter-VLAN ping fails, intra-VLAN works | R1 sub-interface missing or wrong VLAN tag |
| Native VLAN mismatch syslog every 60 s | `switchport trunk native vlan 99` only set on one end |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the capstone without looking at these first! This is the only lab in the switching chapter that asks you to derive the entire config from scratch.

### Objective 1: VLAN database + trunks + native VLAN (blueprint 3.1, 3.1.a)

<details>
<summary>Click to view SW1 VLAN + trunk config</summary>

```bash
! SW1
hostname SW1
no ip domain-lookup
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
interface GigabitEthernet0/0
 description TRUNK_TO_R1_Gi0/0
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk native vlan 99
 switchport trunk allowed vlan 10,20,30,99
 switchport nonegotiate
 no shutdown
```

</details>

<details>
<summary>Click to view SW2 / SW3 VLAN DB (same as SW1)</summary>

```bash
vlan 10
 name SALES
vlan 20
 name ENGINEERING
vlan 30
 name MANAGEMENT_HOSTS
vlan 99
 name NATIVE_MGMT
```

</details>

### Objective 2: EtherChannel bundles — LACP, PAgP, static (blueprint 3.1.b)

<details>
<summary>Click to view SW1 — Po1 (LACP active) + Po2 (PAgP desirable)</summary>

```bash
port-channel load-balance src-dst-mac
!
interface range GigabitEthernet0/1 - 2
 description PO1_MEMBER_TO_SW2
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk native vlan 99
 switchport trunk allowed vlan 10,20,30,99
 switchport nonegotiate
 channel-group 1 mode active
 no shutdown
!
interface GigabitEthernet0/3
 description PO2_MEMBER_TO_SW3_Gi0/3
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk native vlan 99
 switchport trunk allowed vlan 10,20,30,99
 switchport nonegotiate
 channel-group 2 mode desirable
 no shutdown
!
interface GigabitEthernet1/0
 description PO2_MEMBER_TO_SW3_Gi1/0
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk native vlan 99
 switchport trunk allowed vlan 10,20,30,99
 switchport nonegotiate
 channel-group 2 mode desirable
 no shutdown
!
interface Port-channel1
 description LACP_PO1_TO_SW2
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk native vlan 99
 switchport trunk allowed vlan 10,20,30,99
 switchport nonegotiate
!
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
<summary>Click to view SW2 — Po1 (LACP passive) + Po3 (static)</summary>

```bash
port-channel load-balance src-dst-mac
!
interface range GigabitEthernet0/1 - 2
 channel-group 1 mode passive
!
interface GigabitEthernet0/3
 channel-group 3 mode on
interface GigabitEthernet1/0
 channel-group 3 mode on
```

</details>

<details>
<summary>Click to view SW3 — Po2 (PAgP auto) + Po3 (static)</summary>

```bash
port-channel load-balance src-dst-mac
!
interface GigabitEthernet0/3
 channel-group 2 mode auto
interface GigabitEthernet1/0
 channel-group 2 mode auto
!
interface range GigabitEthernet0/1 - 2
 channel-group 3 mode on
```

</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show etherchannel summary
show etherchannel port-channel
show interfaces Port-channel1 switchport
```

</details>

### Objective 3: Rapid PVST+ & root engineering (blueprint 3.1.c)

<details>
<summary>Click to view STP mode + priorities (all 3 switches)</summary>

```bash
! SW1
spanning-tree mode rapid-pvst
spanning-tree vlan 10,30,99 priority 4096
spanning-tree vlan 20 priority 8192

! SW2
spanning-tree mode rapid-pvst
spanning-tree vlan 20 priority 4096
spanning-tree vlan 10,30,99 priority 28672

! SW3
spanning-tree mode rapid-pvst
spanning-tree vlan 20 priority 28672
```

</details>

<details>
<summary>Click to view STP enhancements — PortFast, BPDU guard, Root guard</summary>

```bash
! SW2 — PC1 access
interface GigabitEthernet1/1
 description ACCESS_PC1_VLAN10
 switchport mode access
 switchport access vlan 10
 spanning-tree portfast
 spanning-tree bpduguard enable
 no shutdown
!
! SW3 — PC2 access
interface GigabitEthernet1/1
 description ACCESS_PC2_VLAN20
 switchport mode access
 switchport access vlan 20
 spanning-tree portfast
 spanning-tree bpduguard enable
 no shutdown
!
! SW1 — Root guard on R1-facing trunk ONLY
! Po1/Po2 cannot use root guard: SW2 is root for VLAN 20 and sends superior
! BPDUs on those bundles — enabling root guard would block VLAN 20 traffic.
interface GigabitEthernet0/0
 spanning-tree guard root
```

</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show spanning-tree vlan 10
show spanning-tree vlan 20
show spanning-tree root
show spanning-tree inconsistentports
show spanning-tree interface Gi1/1 portfast
```

</details>

### Objective 4: Router-on-a-stick (blueprint 3.1.a)

<details>
<summary>Click to view R1 sub-interfaces</summary>

```bash
interface GigabitEthernet0/0
 description TRUNK_TO_SW1_Gi0/0
 no ip address
 no shutdown
!
interface GigabitEthernet0/0.10
 encapsulation dot1Q 10
 ip address 192.168.10.1 255.255.255.0
interface GigabitEthernet0/0.20
 encapsulation dot1Q 20
 ip address 192.168.20.1 255.255.255.0
interface GigabitEthernet0/0.30
 encapsulation dot1Q 30
 ip address 192.168.30.1 255.255.255.0
interface GigabitEthernet0/0.99
 encapsulation dot1Q 99 native
 ip address 192.168.99.254 255.255.255.0
```

</details>

### Objective 5: Access ports + management SVI

<details>
<summary>Click to view SVIs + spare shutdowns</summary>

```bash
! SW1
interface Vlan99
 ip address 192.168.99.1 255.255.255.0
 no shutdown
interface range GigabitEthernet1/1 - 3
 shutdown

! SW2
interface Vlan99
 ip address 192.168.99.2 255.255.255.0
 no shutdown
interface range GigabitEthernet1/2 - 3
 shutdown

! SW3
interface Vlan99
 ip address 192.168.99.3 255.255.255.0
 no shutdown
interface range GigabitEthernet1/2 - 3
 shutdown
```

</details>

> Full per-device solutions also live in `solutions/SW1.cfg`, `SW2.cfg`, `SW3.cfg`, `R1.cfg`.

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. Inject the fault first, then
diagnose and fix using only show commands.

### Workflow

```bash
python3 setup_lab.py                                   # reset to known-good
python3 scripts/fault-injection/inject_scenario_01.py  # Ticket 1
python3 scripts/fault-injection/inject_scenario_02.py  # Ticket 2
python3 scripts/fault-injection/inject_scenario_03.py  # Ticket 3
python3 scripts/fault-injection/apply_solution.py      # restore
```

---

### Ticket 1 — PC1 and PC2 Lose Reachability After Router Uplink Change

The NOC ran a hardening pass on SW1 and restricted the allowed VLAN list on the router-facing trunk. Inter-VLAN connectivity is now completely broken — neither PC can reach the other VLAN and both fail to ping their gateways. All EtherChannel bundles still show `(SU)` and all trunks are up. No L2 faults are visible.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py`

**Success criteria:** PC1 pings PC2 (`ttl=63`), both PCs can reach their gateways (192.168.10.1 and 192.168.20.1), and `show interfaces trunk` on SW1 shows Gi0/0 carrying VLANs `10,20,30,99`.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `show interfaces trunk` on SW1 — examine the **Vlans allowed on trunk** column for Gi0/0 and compare it to Po1 and Po2.
2. Notice that Gi0/0 is missing VLANs 10 and 20 from the allowed list. R1's sub-interfaces Gi0/0.10 and Gi0/0.20 are still up/up but receive no tagged frames from the network.
3. Confirm with `show interfaces GigabitEthernet0/0 switchport` on SW1 → look at *Trunking VLANs Enabled*.

</details>

<details>
<summary>Click to view Fix</summary>

```bash
SW1(config)# interface GigabitEthernet0/0
SW1(config-if)# switchport trunk allowed vlan 10,20,30,99
```

Verify with `show interfaces trunk` on SW1 that Gi0/0 now shows `10,20,30,99` in the allowed column. PC1 should immediately be able to ping PC2 once R1's sub-interfaces receive tagged frames again.
</details>

---

### Ticket 2 — A Distribution Bundle Stays Down

Monitoring flagged that `show etherchannel summary` reports Po2 in `(SD)` — members exist but the bundle never came up. No user complaints yet: VLAN 20 traffic still reaches R1 via Po3→SW2→Po1 (redundancy is masking the outage), and VLAN 10/30/99 re-converged through SW2 as well. Your job is to restore Po2 before a second failure takes the network down — in production this kind of silent bundle failure is exactly what monitoring, not user tickets, must catch.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py`

**Success criteria:** `show etherchannel summary` on both SW1 and SW3 shows Po2 `(SU)` with both member ports `(P)`, and `show etherchannel port-channel` reports PAgP (not LACP) on both ends.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `show etherchannel summary` on SW1 and SW3 — note the protocol column.
2. `show etherchannel port-channel` on each side — compare protocol. SW1 is PAgP (`desirable`); if SW3 reports LACP, the two ends are speaking different aggregation protocols.
3. `show running-config interface Gi0/3` on SW3 — confirm the wrong mode (`passive` = LACP).
4. Remember the PAgP matrix: `desirable + desirable` ✓, `desirable + auto` ✓, `auto + auto` ✗. LACP and PAgP are incompatible regardless of mode.

</details>

<details>
<summary>Click to view Fix</summary>

SW3's Po2 members were changed to LACP `passive`; return them to PAgP `auto`:

```bash
SW3(config)# interface range Gi0/3 , Gi1/0
SW3(config-if-range)# no channel-group 2
SW3(config-if-range)# channel-group 2 mode auto
```

Wait ~15 s for PAgP to re-negotiate and verify `Po2(SU)`.
</details>

---

### Ticket 3 — An Access Port Went Err-Disabled

SW3's PC2 port is down. The user reports their switch-hub went in yesterday to "add more ports" at the desk. In production a BPDU arriving on a PortFast port with `bpduguard enable` would err-disable it (`show interfaces status err-disabled` → cause `bpduguard`). In this EVE-NG simulation the port is administratively shut, so `show interfaces status` shows `disabled` — the recovery procedure is identical.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py`

**Success criteria:** SW3 Gi1/1 is `connected / 20` (VLAN 20), PC2 pings its gateway, and no more `BPDUGUARD` err-disable events fire.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `show interfaces status` on SW3 — confirm Gi1/1 is `disabled` (this simulation) or `err-disabled` (real BPDU-guard event). Either way, the port is not forwarding.
2. `show errdisable recovery` — note whether auto-recovery is enabled (it isn't by default). In a real event this is where you'd confirm the cause is `bpduguard`.
3. In production: `show logging | include BPDUGUARD` confirms the BPDU-source event and identifies the rogue device.
4. A PC-only access port should never receive a BPDU — the presence of one means a switch or hub is plugged into the port. Remove the rogue device before recovering.

</details>

<details>
<summary>Click to view Fix</summary>

After the rogue device is removed, bounce the port:

```bash
SW3(config)# interface GigabitEthernet1/1
SW3(config-if)# shutdown
SW3(config-if)# no shutdown
```

Confirm `show interfaces status` shows `connected / 20` and PC2 pings `192.168.20.1`. BPDU guard stays enabled — it is the correct long-term defence.
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [x] VLANs 10, 20, 30, 99 present on SW1, SW2, SW3 with matching names
- [x] Every inter-switch physical link is a member of Po1, Po2, or Po3
- [x] `show etherchannel summary` → `Po1(SU)`, `Po2(SU)`, `Po3(SU)` on all relevant switches
- [x] All trunks: native VLAN 99, allowed list `10,20,30,99`, `nonegotiate`
- [x] `spanning-tree mode rapid-pvst` on every switch
- [x] SW1 is root for VLAN 10, 30, 99 (`show spanning-tree vlan 10` → "This bridge is the root")
- [x] SW2 is root for VLAN 20
- [x] Secondary priorities explicitly set (28672) — no device at default 32768 for a VLAN it backs up
- [x] PC-facing access ports have `portfast` and `bpduguard enable`
- [x] Root guard applied on SW1 Gi0/0 only (NOT Po1/Po2 — split-root topology prevents it)
- [x] R1 sub-interfaces `.10/.20/.30/.99` all up/up; `.99` has the `native` keyword
- [x] PC1 `ping 192.168.20.10` succeeds (ttl=63 → crossed R1 once)
- [x] Every switch can ping 1.1.1.1 from its VLAN 99 SVI
- [x] `show spanning-tree inconsistentports` is empty on every switch
- [x] Spare interfaces on each switch are `shutdown`

### Troubleshooting

- [x] Ticket 1 — allowed VLAN pruning on SW1 Gi0/0 diagnosed and fixed; PC1 ↔ PC2 ping passes
- [x] Ticket 2 — EtherChannel mode mismatch diagnosed; Po2 `(SU)`
- [x] Ticket 3 — BPDU-guard err-disable resolved; rogue switch removed; port recovered

---
