# Multicast Lab 03 — Full Protocol Mastery (Capstone I)

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

**Exam Objective:** Blueprint 3.3.d — Describe multicast protocols, such as RPF check, PIM SM, IGMP v2/v3, SSM, bidir, and MSDP (Multicast)

This capstone fuses everything from labs 00–02 into one end-to-end multicast fabric. You will stand up four routers with PIM-SM, introduce dynamic RP discovery with BSR, carve out SSM and Bidirectional PIM group ranges, fence R4 into its own PIM domain, and stitch the two domains together with MSDP. No step-by-step instructions — only an end state to meet and verification gates to pass.

### PIM-SM, Shared Tree, and the SPT Switchover

PIM Sparse Mode builds a shared tree `(*,G)` rooted at the Rendezvous Point (RP). Receivers join the RP; sources register with the RP via unicast PIM Register messages. Once the first packet reaches the Last-Hop Router (LHR), the LHR may prune off the shared tree and build a source-specific tree `(S,G)` by joining directly toward the source (SPT switchover, default threshold 0 kbps). The RPF check — "did this packet arrive on the interface the unicast RIB says is the best path back to the source?" — gates every multicast forward decision.

### BSR vs Auto-RP vs Static

Three ways to advertise an RP:

| Mechanism | Transport | Scope | Standards |
|-----------|-----------|-------|-----------|
| Static RP | Config only | Per-router | Always available |
| Auto-RP | Dense-mode 224.0.1.39/40 | Cisco-proprietary | Widely deployed |
| BSR | PIMv2 225.0.0.13 | RFC 5059 | Interoperable |

BSR wins in multi-vendor environments — it flows inside PIM itself, and priority/hash election happens across all candidates automatically. This lab uses BSR for the main domain and static RP inside R4's single-router domain.

### SSM — No RP, No Shared Tree

Source-Specific Multicast builds `(S,G)` state directly from IGMPv3 INCLUDE reports. There is no `(*,G)`, no RP, and no Register traffic — the receiver explicitly names both source and group. IANA reserves 232.0.0.0/8 for SSM; most deployments carve a smaller slice with `ip pim ssm range <ACL>`.

### Bidirectional PIM

Bidir PIM is a shared tree that forwards in both directions. There is no `(S,G)`, no Register, and no SPT switchover. A Designated Forwarder (DF) is elected per segment so only one router forwards upstream toward the RP for a given group. Bidir drastically reduces `(S,G)` state in many-to-many environments (financial data feeds, collaboration).

### MSDP — Connecting Two PIM Domains

MSDP (RFC 3618) lets RPs in different PIM domains learn about each other's sources. RPs peer over TCP 639; when a source registers in one domain, that domain's RP floods a Source-Active (SA) message to its MSDP peers. Remote RPs cache the SA and, if they have a receiver for the group, pull `(S,G)` traffic directly from the source via the unicast topology (RPF still applies).

### PIM Domain Borders

`ip pim bsr-border` on an interface blocks BSR/Auto-RP messages from leaking. It does NOT block multicast data. It does NOT shut PIM. It defines where one administrative PIM domain ends and the next begins — critical for MSDP to have two distinct domains to federate.

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| PIM-SM full configuration | Bring up PIM on all transit interfaces and verify adjacencies |
| BSR-based RP election | Configure C-BSR and C-RP, confirm election and group-to-RP mapping |
| SSM deployment | Carve an SSM range, configure IGMPv3, install source-specific joins |
| Bidir PIM deployment | Enable bidir, designate a bidir RP candidate, verify DF election per segment |
| MSDP inter-domain peering | Peer two RPs, exchange SA messages, prove sa-cache population |
| Domain border enforcement | Fence BSR with `bsr-border`, keep unicast (OSPF) intact for RPF and MSDP |
| Multi-mode validation | Prove ASM, SSM, and Bidir coexist on the same fabric |

---

## 2. Topology & Scenario

You are the senior network architect at **Polaris Research Labs**, a high-energy physics institute. The facility produces three classes of multicast traffic that share the same L3 fabric:

- **Sensor telemetry (ASM, 239.1.1.0/24)** — classic PIM-SM: many sensors, a few dashboards, receivers discover sources via the RP.
- **Compute-cluster broadcasts (SSM, 232.1.1.0/24)** — source-specific streams where every receiver already knows which node is producing which feed.
- **Collaboration mesh (Bidir PIM, 239.2.2.0/24)** — many-to-many group chat between control rooms; every participant is both a sender and a receiver.

R2 is the primary RP in your main PIM domain. A partner institute's router, **R4**, has been rack-mounted in your facility but sits in its own PIM domain — that boundary must be enforced. You will federate the two domains with **MSDP** so your RP and theirs can exchange source information without merging the domains.

**IP Addressing:** IPv4 only. IPv6 multicast (MLD) is out of scope for blueprint 3.3.d.

```
            ┌───────────────────────────┐
            │            R1             │
            │      (Source Router)      │
            │      Lo0: 1.1.1.1/32      │
            └──┬─────────────────────┬──┘
        Gi0/0 │                     │ Gi0/1
   10.1.12.1/30                     10.1.13.1/30
               │                     │
               │ L1                  │ L3
               │                     │
   10.1.12.2/30                     10.1.13.2/30
        Gi0/0 │                     │ Gi0/1
            ┌──┴─────────────────┐ ┌──┴────────────────┐
            │         R2         │ │        R3         │
            │   (Primary RP —    │ │   (Receiver /     │
            │     BSR / ASM      │ │     LHR)          │
            │    Bidir / MSDP)   │ │ Lo0: 3.3.3.3/32   │
            │  Lo0: 2.2.2.2/32   │ │                   │
            └──┬─────────────┬───┘ └──┬─────────────┬──┘
         Gi0/1│             │Gi0/2 Gi0/0           │Gi0/3
   10.1.23.1/30     10.1.24.1/30   10.1.23.2/30    10.1.34.2/30
               │             │        │             │
               │     L2      │        │             │     L7
               │             │  L6    │             │  (PIM domain
               │             │        │             │   border)
               │             │        │             │
   10.1.23.2/30              │   10.1.23.1/30       │
               │             │                     │
               └─────────────┘                     │
                   (L2)                            │
                                  10.1.24.2/30    10.1.34.1/30
                                       Gi0/0       Gi0/1
                                      ┌──┴────────────┴──┐
                                      │        R4        │
                                      │  (Second RP —    │
                                      │  Static self-RP, │
                                      │  MSDP peer)      │
                                      │ Lo0: 4.4.4.4/32  │
                                      └──────────────────┘

          [PC1: 10.1.1.10  — Source]         [PC2: 10.1.3.10  — Receiver]
                    │                                 │
                    │ Gi0/2 10.1.1.1/24   Gi0/2 10.1.3.1/24
                    └───────── R1                R3 ─────────┘

  PIM Domain A: R1, R2, R3     PIM Domain B: R4 (fenced by bsr-border on L6 and L7)
  MSDP peering: R2 Lo0 ↔ R4 Lo0 (TCP 639, connect-source Loopback0)
  SSM range:   232.1.1.0/24     Bidir range: 239.2.2.0/24     ASM range: 239.1.1.0/24
```

---

## 3. Hardware & Environment Specifications

| Component | Details |
|-----------|---------|
| Platform | EVE-NG community edition |
| Router image | Cisco IOSv 15.9(3)M6 (QEMU) |
| End-host image | VPCS |
| Devices | R1, R2, R3, R4 (IOSv) + PC1, PC2 (VPCS) |
| Connectivity | All router-router links = GigabitEthernet (emulated) |

**Cabling:**

| Link | Endpoint A | Endpoint B | Subnet | Notes |
|------|-----------|-----------|--------|-------|
| L1 | R1 Gi0/0 (10.1.12.1/30) | R2 Gi0/0 (10.1.12.2/30) | 10.1.12.0/30 | Main PIM domain |
| L2 | R2 Gi0/1 (10.1.23.1/30) | R3 Gi0/0 (10.1.23.2/30) | 10.1.23.0/30 | Main PIM domain |
| L3 | R1 Gi0/1 (10.1.13.1/30) | R3 Gi0/1 (10.1.13.2/30) | 10.1.13.0/30 | Main PIM domain |
| L4 | R1 Gi0/2 (10.1.1.1/24) | PC1 (10.1.1.10/24) | 10.1.1.0/24 | Source LAN |
| L5 | R3 Gi0/2 (10.1.3.1/24) | PC2 (10.1.3.10/24) | 10.1.3.0/24 | Receiver LAN |
| L6 | R2 Gi0/2 (10.1.24.1/30) | R4 Gi0/0 (10.1.24.2/30) | 10.1.24.0/30 | **PIM domain border** |
| L7 | R3 Gi0/3 (10.1.34.2/30) | R4 Gi0/1 (10.1.34.1/30) | 10.1.34.0/30 | **PIM domain border** |

**Console Access Table:**

| Device | Port | Connection Command |
|--------|------|--------------------|
| R1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R3 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R4 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| PC1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| PC2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |

---

## 4. Base Configuration

Run `python3 setup_lab.py --host <eve-ng-ip>` to push the initial state:

**Pre-loaded:**

- Hostnames, no ip domain lookup, console/VTY line config
- Loopback0 on every router (1.1.1.1, 2.2.2.2, 3.3.3.3, 4.4.4.4)
- All router-router and router-LAN interface IPs, `no shutdown`
- OSPF process 1, area 0, router-id = Loopback0, networks for every interface in area 0 (unicast fabric required for RPF)
- Passive-interface on the host-facing LANs (R1 Gi0/2 and R3 Gi0/2)

**NOT pre-loaded — all yours to build:**

- Global multicast routing
- PIM mode on any interface
- Rendezvous Point discovery (BSR, Auto-RP, or static)
- SSM range definition
- Bidirectional PIM enablement
- IGMP version selection and static joins
- MSDP peering and originator ID
- PIM domain border markers

---

## 5. Lab Challenge: Full Protocol Mastery

> This is a capstone lab. No step-by-step guidance is provided.
> Configure the complete Multicast solution from scratch — IP addressing and OSPF are pre-configured; everything else is yours to build.
> All blueprint bullets for this chapter must be addressed.

**Required end-state:**

| Component | Requirement |
|-----------|-------------|
| Global multicast | `ip multicast-routing` active on R1, R2, R3, R4 |
| PIM-SM | Sparse mode on every transit interface (L1, L2, L3, L6, L7) and on Loopback0 of every router; sparse mode on R1 Gi0/2 (source LAN) and R3 Gi0/2 (receiver LAN) |
| BSR RP discovery (main domain) | R2 is the C-BSR (priority 0) AND the C-RP. Two separate `rp-candidate` statements: one bound to ASM group-list (239.1.1.0/24), one bound to Bidir group-list (239.2.2.0/24) with the `bidir` keyword |
| Static RP (R4 domain) | R4 uses `ip pim rp-address 4.4.4.4` as its own RP (single-router PIM domain) |
| SSM | `ip pim ssm range SSM_RANGE` cluster-wide. ACL `SSM_RANGE` permits 232.1.1.0/24 |
| Bidirectional PIM | `ip pim bidir-enable` globally on every router that forwards bidir traffic |
| IGMP | R3 Gi0/2 runs IGMPv3. Static joins on R3 Gi0/2: `join-group 239.1.1.1` (ASM), `join-group 239.2.2.1` (Bidir), `static-group 232.1.1.1 source 10.1.1.10` (SSM). R4 Lo0 joins 239.1.1.1 to demonstrate MSDP SA-cache population |
| PIM domain border | `ip pim bsr-border` on R2 Gi0/2, R3 Gi0/3, R4 Gi0/0, R4 Gi0/1 |
| MSDP | R2 ↔ R4 peering over Loopback0 (TCP 639). Both peers set `connect-source Loopback0` and `ip msdp originator-id Loopback0` |
| Reachability | End-to-end multicast forwarding proven for all three modes: ASM 239.1.1.1, SSM 232.1.1.1, Bidir 239.2.2.1. MSDP SA cache populated on R4 |

**Verification gates — work through these in order:**

1. `show ip ospf neighbor` — every router must have full adjacency with every directly-attached neighbor (R1: R2+R3; R2: R1+R3+R4; R3: R1+R2+R4; R4: R2+R3).
2. `show ip pim neighbor` — PIM adjacencies on L1, L2, L3, L6, L7.
3. `show ip pim rp mapping` on R1 and R3 — BSR-learned mapping for 239.1.1.0/24 points to 2.2.2.2; 239.2.2.0/24 points to 2.2.2.2 with `bidir` flag.
4. `show ip pim rp mapping` on R4 — static self-RP 4.4.4.4 (no BSR mappings — fenced by `bsr-border`).
5. `show ip mroute 239.1.1.1` on R3 — shared tree `(*, 239.1.1.1)` via RP 2.2.2.2; after traffic from PC1, `(10.1.1.10, 239.1.1.1)` state appears with SPT-bit set.
6. `show ip mroute 232.1.1.1` on R3 — only `(10.1.1.10, 232.1.1.1)`; NO `(*, 232.1.1.1)` entry (SSM has no shared tree).
7. `show ip mroute 239.2.2.1` on R3 — `(*, 239.2.2.1)` with `B` flag (Bidir); NO `(S,G)` entry (Bidir never creates one).
8. `show ip pim interface df` on all segments — exactly one DF per segment for every bidir RP.
9. `show ip msdp peer` on R2 and R4 — state `Up`, connected over Loopback0.
10. `show ip msdp sa-cache` on R4 — at least one `(10.1.1.10, 239.1.1.1)` entry after R1 generates ASM traffic.
11. End-to-end forwarding:
    - `ping 239.1.1.1` from R1 — receives responses from R3's receiver LAN and from R4 Lo0 (MSDP SA-cache demonstrator).
    - `ping 239.2.2.1` from R1 — receives response from R3's receiver LAN (Bidir path).
    - `ping 232.1.1.1` **from PC1** (source must be 10.1.1.10 to match R3's SSM INCLUDE filter). Then on R3, `show ip mroute 232.1.1.1` shows `(10.1.1.10, 232.1.1.1)` with a non-zero packet counter on Gi0/2 — proof of SSM forwarding. A ping sourced from R1 will NOT match (wrong source IP).

---

## 6. Verification & Analysis

### OSPF Underlay (prerequisite for RPF)

```
R2# show ip ospf neighbor

Neighbor ID     Pri   State           Dead Time   Address         Interface
1.1.1.1           1   FULL/DR         00:00:38    10.1.12.1       GigabitEthernet0/0   ! ← R1 on L1
3.3.3.3           1   FULL/BDR        00:00:35    10.1.23.2       GigabitEthernet0/1   ! ← R3 on L2
4.4.4.4           1   FULL/DR         00:00:32    10.1.24.2       GigabitEthernet0/2   ! ← R4 on L6 (border underlay)
```

### PIM Adjacencies

```
R2# show ip pim neighbor
PIM Neighbor Table
Neighbor          Interface                Uptime/Expires    Ver   DR
Address                                                            Prio/Mode
10.1.12.1         GigabitEthernet0/0       00:05:11/00:01:21 v2    1 / S P G      ! ← R1 on L1
10.1.23.2         GigabitEthernet0/1       00:05:09/00:01:19 v2    1 / S P G      ! ← R3 on L2
10.1.24.2         GigabitEthernet0/2       00:04:55/00:01:35 v2    1 / S P G      ! ← R4 on L6 (bsr-border interface still runs PIM)
```

### BSR-Learned RP Mapping (main domain)

```
R1# show ip pim rp mapping
PIM Group-to-RP Mappings

Group(s) 239.1.1.0/24
  RP 2.2.2.2 (?), v2                                              ! ← ASM range from BSR
    Info source: 2.2.2.2 (?), via bootstrap, priority 0, holdtime 150
         Uptime: 00:04:20, expires: 00:02:09
Group(s) 239.2.2.0/24, Bidir                                      ! ← Bidir flag present
  RP 2.2.2.2 (?), v2
    Info source: 2.2.2.2 (?), via bootstrap, priority 0, holdtime 150
         Uptime: 00:04:20, expires: 00:02:09

R4# show ip pim rp mapping                                        ! ← R4 must NOT see any BSR entries
PIM Group-to-RP Mappings

Group(s): 224.0.0.0/4, Static
    RP: 4.4.4.4 (?)                                               ! ← only the static self-RP
```

### Mroute State — ASM vs SSM vs Bidir

```
R3# show ip mroute 239.1.1.1
(*, 239.1.1.1), 00:03:14/stopped, RP 2.2.2.2, flags: SJC          ! ← shared tree, RP-rooted
  Incoming interface: GigabitEthernet0/0, RPF nbr 10.1.23.1
  Outgoing interface list:
    GigabitEthernet0/2, Forward/Sparse, 00:03:14/00:02:41         ! ← toward PC2

(10.1.1.10, 239.1.1.1), 00:00:42/00:02:17, flags: TA              ! ← SPT after first packet
  Incoming interface: GigabitEthernet0/1, RPF nbr 10.1.13.1       ! ← direct path to R1
  Outgoing interface list:
    GigabitEthernet0/2, Forward/Sparse, 00:00:42/00:02:41

R3# show ip mroute 232.1.1.1
(10.1.1.10, 232.1.1.1), 00:02:05/00:02:54, flags: sTI             ! ← SSM: (S,G) only; s = SSM, T = SPT
  Incoming interface: GigabitEthernet0/1, RPF nbr 10.1.13.1
  Outgoing interface list:
    GigabitEthernet0/2, Forward/Sparse, 00:02:05/00:02:54
                                                                  ! ← NO (*,G) for SSM groups
R3# show ip mroute 239.2.2.1
(*, 239.2.2.1), 00:03:55/00:02:44, RP 2.2.2.2, flags: BC          ! ← B = Bidir
  Bidir-Upstream: GigabitEthernet0/0, RPF nbr 10.1.23.1
  Outgoing interface list:
    GigabitEthernet0/2, Forward/Sparse, 00:03:55/00:02:44
                                                                  ! ← NO (S,G) for Bidir groups
```

### DF Election (Bidir)

```
R2# show ip pim interface df
* implies this system is the DF
Interface          RP               DF Winner        Metric          Uptime
Gi0/0              2.2.2.2          *2.2.2.2         0               00:06:12    ! ← R2 is DF toward R1 (it IS the RP)
Gi0/1              2.2.2.2          *2.2.2.2         0               00:06:10    ! ← R2 is DF toward R3
```

### MSDP Peering and SA Cache

```
R2# show ip msdp peer
MSDP Peer 4.4.4.4 (?), AS ?
  Connection status:
    State: Up, Resets: 0, Connection source: Loopback0 (2.2.2.2)   ! ← State=Up
    Uptime(Downtime): 00:05:41, Messages sent/received: 6/6
    Output messages discarded: 0
    Connection and counters cleared 00:05:41 ago

R4# show ip msdp sa-cache
MSDP Source-Active Cache - 1 entries
(10.1.1.10, 239.1.1.1), RP 2.2.2.2, BGP/AS 0, 00:01:22/00:05:38    ! ← SA learned from R2
```

### End-to-End Forwarding

```
R1# ping 239.1.1.1 repeat 5
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 239.1.1.1, timeout is 2 seconds:

Reply to request 0 from 10.1.3.1, 2 ms                            ! ← PC2-facing router responds (R3 joined group)
Reply to request 0 from 4.4.4.4, 3 ms                             ! ← R4 Lo0 joined group too (MSDP SA demo)
```

**SSM must be sourced from PC1 — R3's INCLUDE filter is bound to 10.1.1.10:**

```
PC1> ping 232.1.1.1
232.1.1.1 icmp_seq=1 timeout                          ! ← VPCS shows no echo reply (expected — multicast doesn't echo back)
                                                      !    SSM proof is in the mroute state on R3, not a ping response

R3# show ip mroute 232.1.1.1
(10.1.1.10, 232.1.1.1), 00:00:12/00:03:17, flags: sTI             ! ← (S,G) formed: s=SSM, T=SPT, I=received IGMPv3 include
  Incoming interface: GigabitEthernet0/1, RPF nbr 10.1.12.1       ! ← RPF toward R1 (PC1's upstream)
  Outgoing interface list:
    GigabitEthernet0/2, Forward/Sparse, 00:00:12/00:03:17         ! ← forwarded onto receiver LAN
```

> A ping sourced from R1 (e.g. `R1# ping 232.1.1.1`) would be dropped by R3's INCLUDE filter because the source IP wouldn't be 10.1.1.10. Always source SSM traffic from the joined sender.

---

## 7. Verification Cheatsheet

### Global Multicast Enablement

```
ip multicast-routing
```

| Command | Purpose |
|---------|---------|
| `ip multicast-routing` | Enable multicast forwarding plane globally. Required before any PIM command takes effect. |

### PIM Mode on Interfaces

```
interface X
 ip pim sparse-mode
 [ip pim bsr-border]
```

| Command | Purpose |
|---------|---------|
| `ip pim sparse-mode` | Run PIM-SM on the interface. Required on every interface that forwards multicast (including Loopback0 for BSR reachability). |
| `ip pim bsr-border` | Block BSR and Auto-RP messages. Defines the PIM administrative boundary. |

> **Exam tip:** `bsr-border` does not block PIM adjacencies or multicast data — only RP-discovery messages. You need PIM sparse-mode AND bsr-border together on the border interface.

### BSR-Based RP (main domain)

```
ip pim bsr-candidate Loopback0 0
ip pim rp-candidate Loopback0 group-list ASM_GROUPS
ip pim rp-candidate Loopback0 group-list BIDIR_GROUPS bidir

ip access-list standard ASM_GROUPS
 permit 239.1.1.0 0.0.0.255
ip access-list standard BIDIR_GROUPS
 permit 239.2.2.0 0.0.0.255
```

| Command | Purpose |
|---------|---------|
| `ip pim bsr-candidate <int> <hash-len>` | Offer this router as the Bootstrap Router for the domain. |
| `ip pim rp-candidate <int> group-list <ACL>` | Offer this router as RP for the groups permitted by the ACL. |
| `ip pim rp-candidate <int> group-list <ACL> bidir` | Same as above, but groups will run in Bidirectional PIM mode. |

### Static RP (R4 domain)

```
ip pim rp-address 4.4.4.4
```

| Command | Purpose |
|---------|---------|
| `ip pim rp-address <addr>` | Hard-code the RP for all ASM groups. Used in single-router domains or as a fallback when BSR fails. |

### SSM Range

```
ip pim ssm range SSM_RANGE

ip access-list standard SSM_RANGE
 permit 232.1.1.0 0.0.0.255
```

| Command | Purpose |
|---------|---------|
| `ip pim ssm range <ACL>` | Treat groups permitted by ACL as SSM. No RP lookup, no shared tree, no Register. |

### Bidirectional PIM

```
ip pim bidir-enable
```

| Command | Purpose |
|---------|---------|
| `ip pim bidir-enable` | Global switch. Must be enabled on every router that forwards bidir traffic; otherwise, bidir groups are silently dropped. |

> **Exam tip:** Bidir requires BOTH the global `ip pim bidir-enable` AND the `bidir` keyword on the RP candidate statement. Missing either one turns bidir groups back into vanilla ASM.

### IGMP on Receiver Interface

```
interface GigabitEthernet0/2
 ip igmp version 3
 ip igmp join-group 239.1.1.1
 ip igmp static-group 232.1.1.1 source 10.1.1.10
```

| Command | Purpose |
|---------|---------|
| `ip igmp version 3` | Upgrade IGMP to v3 (required for SSM source filtering). |
| `ip igmp join-group <G>` | Router itself joins the group (sends IGMP reports + punts to CPU). |
| `ip igmp static-group <G> source <S>` | Router pretends a host with this INCLUDE(S,G) filter is attached (for SSM without a real receiver). |

### MSDP

```
ip msdp peer 4.4.4.4 connect-source Loopback0
ip msdp description R4-MSDP-PEER
ip msdp originator-id Loopback0
```

| Command | Purpose |
|---------|---------|
| `ip msdp peer <addr> connect-source <int>` | Establish TCP 639 MSDP session sourced from the specified interface. |
| `ip msdp originator-id <int>` | Use this interface's IP as the RP identity in outbound SA messages. Without it, SA RPF checks fail. |
| `ip msdp description <text>` | Administrative label on the peer. |

> **Exam tip:** MSDP needs unicast reachability between the two Loopback0 addresses — that's why OSPF still runs across the PIM domain border even though PIM is fenced.

### Verification Commands

| Command | What to Look For |
|---------|-----------------|
| `show ip pim neighbor` | All expected neighbors, `v2` mode. Missing neighbor = no `ip pim sparse-mode` or L3 down. |
| `show ip pim rp mapping` | BSR entries for 239.1.1.0/24 and 239.2.2.0/24 (Bidir). On R4: only the static self-RP. |
| `show ip mroute <G>` | ASM → `(*,G)` + `(S,G)`. SSM → `(S,G)` only (`s` flag). Bidir → `(*,G)` with `B` flag, never `(S,G)`. |
| `show ip pim interface df` | Exactly one DF per segment for bidir. |
| `show ip msdp peer` | State `Up`. Uptime growing. `Connection source` = Loopback0. |
| `show ip msdp sa-cache` | At least one SA entry after a source registers on the peer RP. |
| `show ip rpf <source>` | Unicast table says this interface is the path back to the source — PIM uses this for RPF. |
| `show ip igmp groups` | Expected groups listed on the receiver interface. Version column matches configuration. |

### Wildcard Mask Quick Reference

| Subnet Mask | Wildcard Mask | Common Use |
|-------------|---------------|------------|
| /24 (255.255.255.0) | 0.0.0.255 | Group-list or IGMP ACL for a /24 multicast slice |
| /32 (255.255.255.255) | 0.0.0.0 | Match a single group or RP in a group-list |

### Common Multicast Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| No PIM neighbors on a link | Missing `ip pim sparse-mode` on one side, or OSPF down so Hello can't reach the other side |
| Shared tree built but no traffic | RPF failure (unicast path asymmetric), or source interface missing PIM |
| SSM `(S,G)` never appears | `ip pim ssm range` not configured, or ACL doesn't include the group |
| Bidir group behaves like ASM | Missing global `ip pim bidir-enable`, or `bidir` keyword missing from rp-candidate |
| MSDP session won't come Up | Unicast loopback unreachable, or `connect-source` mismatch between peers |
| SA cache stays empty after source registers | Missing `ip msdp originator-id Loopback0` on the source-side RP |
| R4 learns BSR mappings from R2 | `ip pim bsr-border` missing on the border interface(s) |
| R3 receiver never gets Bidir traffic | `bsr-border` mistakenly applied on an intra-domain link — fractures the domain |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these first! This capstone is the moment to prove you have internalized every multicast concept.

### R1 — Source-side router

<details>
<summary>Click to view R1 Configuration</summary>

```bash
ip multicast-routing
!
interface Loopback0
 ip pim sparse-mode
!
interface GigabitEthernet0/0
 ip pim sparse-mode
!
interface GigabitEthernet0/1
 ip pim sparse-mode
!
interface GigabitEthernet0/2
 ip pim sparse-mode
!
ip pim bidir-enable
ip pim ssm range SSM_RANGE
!
ip access-list standard SSM_RANGE
 permit 232.1.1.0 0.0.0.255
```
</details>

### R2 — Primary RP, BSR, MSDP speaker

<details>
<summary>Click to view R2 Configuration</summary>

```bash
ip multicast-routing
!
interface Loopback0
 ip pim sparse-mode
!
interface GigabitEthernet0/0
 ip pim sparse-mode
!
interface GigabitEthernet0/1
 ip pim sparse-mode
!
interface GigabitEthernet0/2
 ip pim sparse-mode
 ip pim bsr-border
!
ip pim bidir-enable
ip pim ssm range SSM_RANGE
ip pim bsr-candidate Loopback0 0
ip pim rp-candidate Loopback0 group-list ASM_GROUPS
ip pim rp-candidate Loopback0 group-list BIDIR_GROUPS bidir
!
ip access-list standard SSM_RANGE
 permit 232.1.1.0 0.0.0.255
ip access-list standard ASM_GROUPS
 permit 239.1.1.0 0.0.0.255
ip access-list standard BIDIR_GROUPS
 permit 239.2.2.0 0.0.0.255
!
ip msdp peer 4.4.4.4 connect-source Loopback0
ip msdp description R4-MSDP-PEER
ip msdp originator-id Loopback0
```
</details>

### R3 — Receiver-side router (LHR)

<details>
<summary>Click to view R3 Configuration</summary>

```bash
ip multicast-routing
!
interface Loopback0
 ip pim sparse-mode
!
interface GigabitEthernet0/0
 ip pim sparse-mode
!
interface GigabitEthernet0/1
 ip pim sparse-mode
!
interface GigabitEthernet0/2
 ip pim sparse-mode
 ip igmp version 3
 ip igmp join-group 239.1.1.1
 ip igmp join-group 239.2.2.1
 ip igmp static-group 232.1.1.1 source 10.1.1.10
!
interface GigabitEthernet0/3
 ip pim sparse-mode
 ip pim bsr-border
!
ip pim bidir-enable
ip pim ssm range SSM_RANGE
!
ip access-list standard SSM_RANGE
 permit 232.1.1.0 0.0.0.255
```
</details>

### R4 — Second RP, MSDP peer

<details>
<summary>Click to view R4 Configuration</summary>

```bash
ip multicast-routing
!
interface Loopback0
 ip pim sparse-mode
 ip igmp join-group 239.1.1.1
!
interface GigabitEthernet0/0
 ip pim sparse-mode
 ip pim bsr-border
!
interface GigabitEthernet0/1
 ip pim sparse-mode
 ip pim bsr-border
!
ip pim bidir-enable
ip pim ssm range SSM_RANGE
ip pim rp-address 4.4.4.4
!
ip access-list standard SSM_RANGE
 permit 232.1.1.0 0.0.0.255
!
ip msdp peer 2.2.2.2 connect-source Loopback0
ip msdp description R2-MSDP-PEER
ip msdp originator-id Loopback0
```
</details>

<details>
<summary>Click to view Capstone Verification Commands</summary>

```bash
show ip ospf neighbor
show ip pim neighbor
show ip pim rp mapping
show ip mroute 239.1.1.1
show ip mroute 232.1.1.1
show ip mroute 239.2.2.1
show ip pim interface df
show ip msdp peer
show ip msdp sa-cache
show ip igmp groups
ping 239.1.1.1 repeat 5                       ! from R1 (ASM)
ping 239.2.2.1 repeat 5                       ! from R1 (Bidir)
! SSM must be sourced from PC1 (10.1.1.10), not R1 — R3's INCLUDE filter requires source 10.1.1.10:
! PC1> ping 232.1.1.1
! Then verify (S,G) on R3:
show ip mroute 232.1.1.1                      ! expect (10.1.1.10, 232.1.1.1) with non-zero OIL packet count
```
</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. Inject the fault first, then diagnose and fix using only show commands. These three scenarios span the three protocol layers of this capstone: a PIM-layer adjacency fault, a BSR/RP-discovery fault, and an MSDP-layer fault.

### Workflow

```bash
python3 setup_lab.py                                   # reset to known-good
python3 scripts/fault-injection/inject_scenario_01.py  # Ticket 1
python3 scripts/fault-injection/apply_solution.py      # restore
```

---

### Ticket 1 — PC2 Loses ASM Traffic After a Transit Link "Maintenance Window"

The NOC reports that following a scheduled maintenance on the R1↔R3 link, sensor telemetry (239.1.1.1) to PC2 has become sluggish and RPF warnings are appearing in the logs. OSPF on R3 shows both neighbors Up, but multicast forwarding is intermittent and the `(S,G)` for PC1's stream is missing on R3.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py`

**Success criteria:** R3 shows both `(*, 239.1.1.1)` via RP and `(10.1.1.10, 239.1.1.1)` with SPT bit, and `ping 239.1.1.1` from R1 gets a reply from 10.1.3.1.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
R3# show ip pim neighbor
! Note which interfaces list neighbors. If L3 (Gi0/1 toward R1) has no neighbor, PIM died there.

R3# show ip pim interface
! Look for L3 interface missing PIM mode or marked "not enabled".

R3# show ip rpf 10.1.1.10
! RPF via Gi0/1 (direct path). If PIM isn't running on that interface, SPT can't form — R3 falls back to shared tree via R2 only.
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
R3(config)# interface GigabitEthernet0/1
R3(config-if)# ip pim sparse-mode
```

Root cause: `ip pim sparse-mode` was removed from R3 Gi0/1 during the "maintenance," breaking the SPT path to R1 (the RPF-preferred path for source 10.1.1.10). Traffic still flowed via the shared tree through R2, but every SPT switchover failed.
</details>

---

### Ticket 2 — R4's Receivers Start Receiving Groups They Should Not See

After a config change on R2, the partner institute (R4) reports that their router's `show ip pim rp mapping` now lists the main domain's 239.1.1.0/24 and 239.2.2.0/24 ranges with RP 2.2.2.2. This should never happen — R4 is supposed to be its own PIM domain with its own static RP.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py`

**Success criteria:** `show ip pim rp mapping` on R4 shows ONLY the static self-RP 4.4.4.4. No BSR-learned entries appear.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
R4# show ip pim rp mapping
! If you see "Info source: 2.2.2.2 ... via bootstrap", the BSR border is broken.

R2# show run interface GigabitEthernet0/2
R3# show run interface GigabitEthernet0/3
R4# show run interface GigabitEthernet0/0
R4# show run interface GigabitEthernet0/1
! Any of these four interfaces missing "ip pim bsr-border" is the hole.
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
R2(config)# interface GigabitEthernet0/2
R2(config-if)# ip pim bsr-border

R4(config)# interface GigabitEthernet0/0
R4(config-if)# ip pim bsr-border
```

Root cause: `ip pim bsr-border` was removed from both R2 Gi0/2 and R4 Gi0/0 — both ends of the R2↔R4 inter-domain link. A single `bsr-border` on either end is sufficient to block Bootstrap messages; to create the leak, both ends must be removed. The domain boundary is only as strong as its weakest border interface — all four (R2 Gi0/2, R3 Gi0/3, R4 Gi0/0, R4 Gi0/1) must have `bsr-border`.
</details>

---

### Ticket 3 — R4's SA Cache Is Empty Despite Healthy MSDP Session

R4's `show ip msdp peer` reports State: Up and the TCP session has been up for hours, but `show ip msdp sa-cache` is empty — zero entries. R2 is actively receiving Register messages from PC1 for 239.1.1.1 and has `(10.1.1.10, 239.1.1.1)` in its mroute table, but the SA is never reaching R4.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py`

**Success criteria:** `show ip msdp sa-cache` on R4 shows at least one `(10.1.1.10, 239.1.1.1)` entry with RP 2.2.2.2 after R1 generates ASM traffic.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
R2# show ip mroute 239.1.1.1
! Confirm (S,G) state exists — SA generation requires the source be registered.

R2# show ip msdp summary
R2# show ip msdp count
! Peer is Up. Check outbound SA counter. If 0, SA is not being generated on R2.

R2# show run | include msdp
! Compare to solution: "ip msdp peer ... connect-source Loopback0" + "ip msdp originator-id Loopback0".
! Missing originator-id means SA uses a different RP ID for RPF, and R4 drops it.
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
R2(config)# ip msdp originator-id Loopback0
```

Root cause: `ip msdp originator-id Loopback0` was removed on R2. MSDP SA messages carry an RP address in the message payload; R4 performs an RPF check on that RP address. Without `originator-id`, R2 populated the SA with the default outgoing interface IP (not the Loopback0 that R4 knows as the peer RP), so R4 rejected the SA at RPF time. The TCP session stays Up because TCP has no opinion on SA payload validity — only the MSDP state machine does.
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] `ip multicast-routing` enabled on R1, R2, R3, R4
- [ ] PIM sparse-mode configured on every transit and LAN interface, plus every Loopback0
- [ ] R2 is operating as BSR (`show ip pim bsr-router` reports 2.2.2.2)
- [ ] Main domain learns 239.1.1.0/24 (ASM) and 239.2.2.0/24 (Bidir) via BSR
- [ ] R4 shows ONLY static self-RP 4.4.4.4 in `show ip pim rp mapping`
- [ ] `ip pim bsr-border` present on R2 Gi0/2, R3 Gi0/3, R4 Gi0/0, R4 Gi0/1
- [ ] SSM range 232.1.1.0/24 configured cluster-wide via `ip pim ssm range SSM_RANGE`
- [ ] `ip pim bidir-enable` globally on all four routers
- [ ] R3 Gi0/2 running IGMPv3 with all three static joins (ASM, Bidir, SSM)
- [ ] R4 Lo0 joined 239.1.1.1 (MSDP SA-cache demonstrator)
- [ ] MSDP peering R2 ↔ R4 via Loopback0 with `originator-id Loopback0` on both sides
- [ ] `show ip msdp peer` reports State: Up on both R2 and R4
- [ ] `show ip msdp sa-cache` on R4 shows at least one (10.1.1.10, 239.1.1.1) entry after traffic
- [ ] `ping 239.1.1.1` from R1 returns replies from both R3's receiver LAN and R4 Lo0
- [ ] `ping 232.1.1.1` **from PC1** (source 10.1.1.10) produces `(10.1.1.10, 232.1.1.1)` mroute with non-zero packet count on R3 Gi0/2
- [ ] `ping 239.2.2.1` from R1 returns reply from R3 (Bidir path)
- [ ] `show ip mroute 232.1.1.1` on R3 shows (S,G) only, no (*,G)
- [ ] `show ip mroute 239.2.2.1` on R3 shows (*,G) with B flag, no (S,G)

### Troubleshooting

- [ ] Ticket 1 — ASM SPT restored after diagnosing missing PIM mode on R3 Gi0/1
- [ ] Ticket 2 — R4 RP mapping restored to static-only after fixing bsr-border on R2 Gi0/2 and R4 Gi0/0
- [ ] Ticket 3 — MSDP SA cache populated on R4 after restoring originator-id on R2
