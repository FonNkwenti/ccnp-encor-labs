# Lab 01 -- Multi-Area OSPFv2 + Dual-Stack Fundamentals

**Topic:** OSPF | **Exam:** 350-401 | **Difficulty:** Foundation
**Estimated time:** 75 minutes | **Blueprint:** 3.2.a / 3.2.b

Transitions from a single-area OSPFv2 domain to a three-area hierarchy and
adds IPv6 dual-stack via OSPFv3 address-families. R2 becomes the Area 0/1
ABR, R3 becomes the Area 0/2 ABR. R4 collapses entirely into Area 1, R5
entirely into Area 2. OSPFv3 runs alongside OSPFv2 on every transit and
LAN interface so that both IPv4 and IPv6 converge end-to-end.

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

**Exam Objective:** 3.2.a (compare OSPF routing concepts, area types) and 3.2.b
(configure simple OSPFv2/v3 environments including multiple normal areas,
neighbor adjacency, point-to-point and broadcast network types, and
passive-interface) -- OSPF Routing.

Multi-area OSPF is the first scaling technique every link-state operator
learns: rather than forcing every router to recompute shortest paths across
one gigantic LSDB, the domain is partitioned into areas anchored on a
backbone (Area 0). Area Border Routers (ABRs) sit at the boundary and
translate intra-area detail (Type 1/2 LSAs) into inter-area summaries
(Type 3 LSAs). This lab walks that partition step by step and then adds
OSPFv3 so IPv6 rides the same topology -- exactly what 350-401 expects
from a "dual-stack OSPFv2/v3" deployment.

### Why Split OSPF Into Areas?

A single-area OSPF domain works fine with 10-20 routers. Beyond that, three
costs grow faster than the network does:

| Cost | Single-area impact | Multi-area fix |
|------|--------------------|----------------|
| LSDB size | Every router stores every LSA | Non-backbone routers only store their own area's Type 1/2 |
| SPF recompute time | Any link flap re-runs SPF on every router | Intra-area flaps stay inside the area; only the abstract Type 3 re-announces |
| Flooding scope | Every LSA reaches every router | Type 1/2 LSAs are area-scoped; Type 3 summaries carry only essential inter-area data |

Splitting into areas bounds all three. The tradeoff is hierarchy: Area 0
**must** be contiguous and every other area **must** touch it directly (or
through a virtual-link, which is out of scope here).

### Area Border Routers (ABRs)

An ABR is any router with interfaces in two or more OSPF areas, at least
one of which is Area 0. ABRs perform three jobs:

1. **Maintain one LSDB per attached area.** R2 in this lab holds an Area 0
   LSDB and an Area 1 LSDB; they don't mix.
2. **Generate Type 3 Summary LSAs.** For every intra-area prefix they hear
   in one area, they flood a summary description into every other area
   they're connected to. This is how Area 1 learns about Area 0 networks
   and vice-versa.
3. **Compute inter-area paths** through themselves. An internal Area 1
   router's best path to an Area 2 prefix is always `ABR-to-Area-0 ->
   other-ABR-into-Area-2`. The ABR is the pinch point.

Verification of ABR status:

```
show ip ospf                        ! "It is an area border router" line
show ip ospf border-routers         ! routing table of ABRs/ASBRs
```

### LSA Types Encountered Here

| Type | Name | Originator | Scope |
|------|------|-----------|-------|
| 1 | Router LSA | Every router | Its own area only |
| 2 | Network LSA | DR on broadcast segments | DR's area only |
| 3 | Summary LSA | ABR | Every area except the one it describes |

Lab-00 only produced Type 1 and Type 2 LSAs (everything was Area 0). The
moment R4's interfaces move to Area 1 in this lab, R2 starts generating
Type 3 LSAs describing `10.1.24.0/30`, `192.168.1.0/24`, and `4.4.4.4/32`
into Area 0 and the mirror direction into Area 1. You'll see the new LSA
type in `show ip ospf database`.

Routes learned via Type 3 LSAs appear in the routing table with code
`O IA` (OSPF inter-area) rather than the plain `O` code for intra-area
routes.

### OSPFv3 vs OSPFv2 (What Changes for IPv6)

OSPFv3 is a separate protocol -- not an extension of OSPFv2. It runs in
its own process, maintains its own LSDB, and forms its own neighborships.
But the *design* is intentionally familiar:

| Aspect | OSPFv2 (IPv4) | OSPFv3 (IPv6) |
|--------|---------------|---------------|
| Transport | IPv4 protocol 89 | IPv6 next-header 89 |
| Neighbor peering | IPv4 interface addresses | Link-local addresses (`fe80::/10`) |
| Router-ID | 32-bit, from Loopback or explicit | Still 32-bit dotted-quad -- **not** derived from IPv6 |
| Enable on interface | `network x.x.x.x m.m.m.m area N` under `router ospf` | `ospfv3 N ipv6 area N` **directly on the interface** |
| Address family | Implicit IPv4 | Explicit `address-family ipv6 unicast` |

Two practical consequences for this lab:

1. **Router-IDs must be set explicitly under `router ospfv3`.** With no IPv4
   address on a pure-IPv6 interface, OSPFv3 has nothing to auto-derive.
2. **OSPFv3 uses link-local addresses for peering**, so every router needs
   a deterministic link-local (`fe80::<n>`) to make neighbor troubleshooting
   easier. Auto-generated EUI-64 link-locals work but are unreadable.

### Dual-Stack Coexistence

OSPFv2 and OSPFv3 run side-by-side on every router in this lab, on every
interface that carries both an IPv4 address and an IPv6 address. There is
no dependency between them -- an OSPFv2 FULL adjacency does not imply the
OSPFv3 side is FULL. You must verify both independently. That's the
discipline 350-401 is testing.

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| Multi-area OSPF design | Assigning interfaces to areas, identifying ABR placement, planning Area 0 backbone |
| Type 3 LSA analysis | Reading `show ip ospf database summary` and correlating with `O IA` routes |
| OSPFv3 address-family configuration | `router ospfv3 1` with `address-family ipv6 unicast` and per-interface `ospfv3 1 ipv6 area N` |
| Dual-stack verification | Independent OSPFv2 and OSPFv3 neighbor checks; end-to-end IPv4 and IPv6 reachability |
| ABR status verification | `show ip ospf`, `show ip ospf border-routers`, `show ipv6 ospf` equivalents |
| Link-local address planning | Deterministic `fe80::<n>` assignment for readable OSPFv3 peer output |

---

## 2. Topology & Scenario

**Scenario:** You're the network engineer for North Ridge Networks. The
research lab that came online last quarter (Lab 00's single-area OSPF
domain) has grown to include a branch office in Building A (R4 + PC1) and
a field-research subnet in Building C (R5 + PC2). Leadership has also
mandated a dual-stack rollout to prepare for the campus IPv6 migration.

Your job: partition the existing single-area OSPF into three areas so the
branches don't re-run SPF every time the backbone flaps, promote R2 and R3
to ABRs, and bring OSPFv3 up alongside OSPFv2 on every router so both
address families converge independently.

```
                         ┌─────────────────────────────────┐
                         │            AREA 0               │
                         │                                 │
                         │         ┌──────────────┐        │
                         │         │      R1      │        │
                         │         │ (Backbone)   │        │
                         │         │ Lo0: 1.1.1.1 │        │
                         │         └──────┬───────┘        │
                         │                │ Gi0/0          │
                         │         10.0.123.1/24           │
                         │                │                │
                         │         ┌──────┴─────────┐      │
                         │         │   SW-AREA0     │      │
                         │         │ (broadcast)    │      │
                         │         └──┬─────────┬───┘      │
                         │   10.0.123.2        10.0.123.3  │
                         │            │         │          │
                         │       ┌────┴────┐  ┌─┴───────┐  │
                         │       │   R2    │  │   R3    │  │
                         │       │(ABR 0/1)│  │(ABR 0/2)│  │
                         │       │Lo0:2.2.2.2│ │Lo0:3.3.3.3││
                         │       └────┬────┘  └──┬──────┘  │
                         └────────────┼──────────┼─────────┘
                                Gi0/1 │          │ Gi0/1
                              10.1.24.1/30     10.2.35.1/30
                           ┌──────────┼────────┐ ┌────────┼─────────┐
                           │          │        │ │        │         │
                           │   AREA 1 │        │ │ AREA 2 │         │
                           │          │        │ │        │         │
                           │   10.1.24.2/30    │ │   10.2.35.2/30   │
                           │         Gi0/0     │ │         Gi0/0    │
                           │     ┌────┴──────┐ │ │    ┌────┴──────┐ │
                           │     │    R4     │ │ │    │    R5     │ │
                           │     │ (Internal)│ │ │    │ (Internal)│ │
                           │     │Lo0:4.4.4.4│ │ │    │Lo0:5.5.5.5│ │
                           │     └────┬──────┘ │ │    └────┬──────┘ │
                           │    Gi0/2 │        │ │   Gi0/1 │        │
                           │  192.168.1.1/24   │ │  192.168.2.1/24  │
                           │          │        │ │         │        │
                           │     ┌────┴───┐    │ │    ┌────┴───┐    │
                           │     │  PC1   │    │ │    │  PC2   │    │
                           │     │.10/24  │    │ │    │.10/24  │    │
                           │     └────────┘    │ │    └────────┘    │
                           └───────────────────┘ └──────────────────┘
```

**IPv6 overlay (same topology, dual-stack):**

- Area 0 shared segment: `2001:DB8:0:123::/64`
- Area 1 transit (R2↔R4): `2001:DB8:1:24::/64`
- Area 1 PC1 LAN: `2001:DB8:1:1::/64`
- Area 2 transit (R3↔R5): `2001:DB8:2:35::/64`
- Area 2 PC2 LAN: `2001:DB8:2:2::/64`
- Loopbacks: `2001:DB8:FF::<router-number>/128`
- Link-local: `fe80::<router-number>` on every router interface

Full device list, platforms, and links: see
[`../baseline.yaml`](../baseline.yaml) and
[`topology/README.md`](topology/README.md).

---

## 3. Hardware & Environment Specifications

### Device Inventory

| Device | Platform | Role | Loopback0 (IPv4) | Loopback0 (IPv6) |
|--------|----------|------|------------------|------------------|
| R1 | IOSv | Backbone (Area 0) | 1.1.1.1/32 | 2001:DB8:FF::1/128 |
| R2 | IOSv | ABR (Area 0 / Area 1) | 2.2.2.2/32 | 2001:DB8:FF::2/128 |
| R3 | IOSv | ABR (Area 0 / Area 2) | 3.3.3.3/32 | 2001:DB8:FF::3/128 |
| R4 | IOSv | Internal (Area 1) | 4.4.4.4/32 | 2001:DB8:FF::4/128 |
| R5 | IOSv | Internal (Area 2) | 5.5.5.5/32 | 2001:DB8:FF::5/128 |
| SW-AREA0 | Unmanaged switch | Area 0 broadcast segment | -- | -- |
| PC1 | VPCS | End host (Area 1 LAN) | 192.168.1.10 / 2001:DB8:1:1::10 | -- |
| PC2 | VPCS | End host (Area 2 LAN) | 192.168.2.10 / 2001:DB8:2:2::10 | -- |

### Cabling

| Link | Source | Destination | IPv4 Subnet | IPv6 Subnet | OSPF Area |
|------|--------|-------------|-------------|-------------|-----------|
| L1 | R1 Gi0/0 | SW-AREA0 port1 | 10.0.123.0/24 | 2001:DB8:0:123::/64 | 0 |
| L2 | R2 Gi0/0 | SW-AREA0 port2 | 10.0.123.0/24 | 2001:DB8:0:123::/64 | 0 |
| L3 | R3 Gi0/0 | SW-AREA0 port3 | 10.0.123.0/24 | 2001:DB8:0:123::/64 | 0 |
| L4 | R2 Gi0/1 | R4 Gi0/0 | 10.1.24.0/30 | 2001:DB8:1:24::/64 | 1 |
| L5 | R3 Gi0/1 | R5 Gi0/0 | 10.2.35.0/30 | 2001:DB8:2:35::/64 | 2 |
| L6 | R4 Gi0/2 | PC1 e0 | 192.168.1.0/24 | 2001:DB8:1:1::/64 | 1 |
| L7 | R5 Gi0/1 | PC2 e0 | 192.168.2.0/24 | 2001:DB8:2:2::/64 | 2 |

### Console Access Table

Console ports are assigned dynamically by EVE-NG. Record them from the
EVE-NG web UI after starting the lab.

| Device | Port | Connection Command |
|--------|------|--------------------|
| R1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R3 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R4 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R5 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| PC1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| PC2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |

---

## 4. Base Configuration

The `initial-configs/` directory contains the **final OSPFv2 solution from
Lab 00** -- a fully converged single-area domain with every router in
Area 0. `setup_lab.py` pushes these to each node after the EVE-NG topology
starts.

**Pre-loaded by `setup_lab.py`:**

- Hostnames (R1-R5)
- IPv4 addressing on every transit, LAN, and loopback interface
- OSPFv2 process 1 in single-area (Area 0) on all five routers
- Explicit router-IDs (1.1.1.1 .. 5.5.5.5)
- Custom hello=5 / dead=20 timers on R2 Gi0/1 and R4 Gi0/0 (from lab-00)
- `passive-interface` on R4 Gi0/2 and R5 Gi0/1 (LAN edges, from lab-00)
- VTY telnet access
- PC1/PC2 IPv4 addresses (via `.vpc` startup files)

**NOT pre-loaded -- you add these:**

- Multi-area partitioning (Area 0 / Area 1 / Area 2)
- IPv6 global routing
- IPv6 addressing on router interfaces and loopbacks
- IPv6 link-local addresses (deterministic per-router)
- OSPFv3 routing process and IPv6 address-family
- OSPFv3 interface bindings
- IPv6 addresses on PC1 and PC2

---

## 5. Lab Challenge: Core Implementation

Complete the eight tasks below in order. Each task ends with a
**Verification** line showing the exact command you must run and what
state it must confirm.

### Task 1: Promote R2 and R3 to Area Border Routers

- On R2, reassign the point-to-point link to R4 (Gi0/1 -- the `10.1.24.0/30`
  network) from Area 0 to Area 1 inside the OSPFv2 process. Leave R2's
  Loopback0 and Gi0/0 shared-segment interface in Area 0.
- On R3, reassign the point-to-point link to R5 (Gi0/1 -- the `10.2.35.0/30`
  network) from Area 0 to Area 2. Leave R3's Loopback0 and Gi0/0 shared-
  segment interface in Area 0.

**Verification:** `show ip ospf | include area border` on R2 and R3 must
report "It is an area border router"; `show ip ospf border-routers` on R1
must list both R2 (`2.2.2.2`) and R3 (`3.3.3.3`) as ABRs.

---

### Task 2: Collapse R4 Into Area 1

- Move every OSPFv2-participating network on R4 -- Loopback0
  (`4.4.4.4/32`), Gi0/0 (`10.1.24.0/30`), and Gi0/2 (`192.168.1.0/24`) --
  from Area 0 to Area 1.
- Preserve the existing passive-interface on Gi0/2 so R4 still doesn't
  send hellos toward PC1.

**Verification:** `show ip ospf interface brief` on R4 must show every
interface in Area 1; `show ip ospf neighbor` on R2 must list R4 (4.4.4.4)
as FULL on Gi0/1.

---

### Task 3: Collapse R5 Into Area 2

- Move every OSPFv2-participating network on R5 -- Loopback0
  (`5.5.5.5/32`), Gi0/0 (`10.2.35.0/30`), and Gi0/1 (`192.168.2.0/24`) --
  from Area 0 to Area 2.
- Preserve the existing passive-interface on Gi0/1.

**Verification:** `show ip ospf interface brief` on R5 must show every
interface in Area 2; `show ip ospf neighbor` on R3 must list R5 (5.5.5.5)
as FULL on Gi0/1.

---

### Task 4: Inspect Inter-Area LSAs and Routes

- On R1, examine the LSDB and identify the new Type 3 (Summary) LSAs that
  R2 and R3 have injected into Area 0 for Area 1 and Area 2 prefixes.
- On R1, confirm that Area 1 and Area 2 prefixes now appear in the routing
  table with the `O IA` code.
- On R4 and R5, confirm Area 0 prefixes (the shared segment and peer
  loopbacks) appear with the `O IA` code -- these came from the opposite
  ABR.

**Verification:** `show ip ospf database summary` on R1 must list
entries for `10.1.24.0`, `192.168.1.0`, `4.4.4.4`, `10.2.35.0`,
`192.168.2.0`, `5.5.5.5`; `show ip route ospf` on R1 must show
`O IA` entries for each of those prefixes.

---

### Task 5: Enable IPv6 Routing and Address Every Router Interface

- On R1 through R5, enable IPv6 unicast routing globally.
- On each router, add a deterministic link-local address `fe80::<router-
  number>` (e.g., R1 uses `fe80::1`, R2 uses `fe80::2`) to every interface
  that will participate in OSPFv3.
- Add the global IPv6 address from the topology table (Section 3) to each
  router interface -- transit links, LAN interfaces, and Loopback0.
- IPv6 address on Loopback0 uses the `2001:DB8:FF::<router-number>/128`
  scheme.

**Verification:** `show ipv6 interface brief` on every router must list
both a link-local `FE80::<n>` and the global `2001:DB8:...` address on
each configured interface; `ping 2001:DB8:0:123::1` from R2 must succeed
(link-local neighbor discovery is working on the shared segment).

---

### Task 6: Configure IPv6 on PC1 and PC2

- Add the IPv6 address `2001:DB8:1:1::10/64` and default gateway
  `2001:DB8:1:1::1` to PC1.
- Add the IPv6 address `2001:DB8:2:2::10/64` and default gateway
  `2001:DB8:2:2::1` to PC2.
- Save the PC config.

**Verification:** `show ipv6` on each VPCS node must display the global
address and gateway; `ping 2001:DB8:1:1::1` from PC1 and
`ping 2001:DB8:2:2::1` from PC2 must succeed (tests IPv6 NDP to local
gateway).

---

### Task 7: Bring Up OSPFv3 With the IPv6 Address-Family

- On every router (R1-R5), create an OSPFv3 process using process ID 1
  with the IPv6 address-family enabled.
- Assign each router an explicit router-ID that matches its OSPFv2
  router-ID (e.g., R2 uses `2.2.2.2`).
- On every interface that runs OSPFv2, enable OSPFv3 for IPv6 in the
  matching area -- the Area 0 segment stays Area 0, R2-R4 transit stays
  Area 1, R3-R5 transit stays Area 2, and so on. The area map must be
  identical between the two address families.
- Mirror the passive-interface discipline inside the IPv6 address-family:
  R4 Gi0/2 and R5 Gi0/1 must stay passive for OSPFv3 as well.

**Verification:** `show ospfv3 neighbor` on every router must show all
expected adjacencies in FULL state; `show ospfv3 interface brief` on R4
must show Gi0/2 as PASSIVE; `show ipv6 route ospf` on R1 must include
`OI` (OSPFv3 inter-area) routes for Area 1 and Area 2 prefixes.

---

### Task 8: Verify End-to-End Dual-Stack Reachability

- From PC1, ping PC2's IPv4 address (`192.168.2.10`).
- From PC1, ping PC2's IPv6 address (`2001:DB8:2:2::10`).
- From PC2, ping PC1 in reverse for both address families.
- Traceroute both directions for both stacks and confirm the path is:
  `PC -> local R4/R5 -> local ABR (R2 or R3) -> shared segment -> other
  ABR -> remote R4/R5 -> remote PC`.

**Verification:** All four ping directions must succeed with 100% reply
rate (or tolerate one initial miss for ARP/ND). Both IPv4 and IPv6
traceroutes must show exactly five router hops (R4/R5 -> R2/R3 -> R1 or
peer ABR -> R3/R2 -> R5/R4).

---

## 6. Verification & Analysis

### ABR Status Verification

```
R2# show ip ospf | include area border
 It is an area border router                              ! ← confirms R2 is ABR

R3# show ip ospf | include area border
 It is an area border router                              ! ← confirms R3 is ABR

R1# show ip ospf border-routers
OSPF Router with ID (1.1.1.1) (Process ID 1)

Base Topology (MTID 0)

Internal Router Routing Table

i 2.2.2.2 [1] via 10.0.123.2, GigabitEthernet0/0, ABR, Area 0   ! ← R2 = ABR
i 3.3.3.3 [1] via 10.0.123.3, GigabitEthernet0/0, ABR, Area 0   ! ← R3 = ABR
```

### Type 3 Summary LSAs in the LSDB

```
R1# show ip ospf database summary

            OSPF Router with ID (1.1.1.1) (Process ID 1)

                Summary Net Link States (Area 0)

  LS age: 234
  Options: (No TOS-capability, DC, Upward)
  LS Type: Summary Links(Network)
  Link State ID: 4.4.4.4 (summary Network Number)              ! ← R4 loopback as Type 3
  Advertising Router: 2.2.2.2                                   ! ← R2 is the ABR injecting
  LS Seq Number: 80000001
  Checksum: 0xA1B2
  Length: 28
  Network Mask: /32
        MTID: 0         Metric: 2

  LS age: 231
  Link State ID: 10.1.24.0 (summary Network Number)             ! ← Area 1 transit
  Advertising Router: 2.2.2.2
  Network Mask: /30
        MTID: 0         Metric: 1

  LS age: 228
  Link State ID: 192.168.1.0 (summary Network Number)           ! ← PC1 LAN
  Advertising Router: 2.2.2.2
  Network Mask: /24

  LS age: 234
  Link State ID: 5.5.5.5 (summary Network Number)              ! ← R5 loopback via R3
  Advertising Router: 3.3.3.3                                   ! ← injected by R3
```

### Inter-Area Routes (O IA)

```
R1# show ip route ospf
     10.0.0.0/8 is variably subnetted, 7 subnets, 2 masks
O IA    10.1.24.0/30 [110/2] via 10.0.123.2, 00:04:10, GigabitEthernet0/0    ! ← via R2
O IA    10.2.35.0/30 [110/2] via 10.0.123.3, 00:04:10, GigabitEthernet0/0    ! ← via R3
     2.0.0.0/32 is subnetted, 1 subnets
O       2.2.2.2 [110/1] via 10.0.123.2, 00:04:10, GigabitEthernet0/0         ! ← intra-area (O)
     3.0.0.0/32 is subnetted, 1 subnets
O       3.3.3.3 [110/1] via 10.0.123.3, 00:04:10, GigabitEthernet0/0         ! ← intra-area (O)
     4.0.0.0/32 is subnetted, 1 subnets
O IA    4.4.4.4 [110/3] via 10.0.123.2, 00:04:10, GigabitEthernet0/0         ! ← inter-area (O IA)
     5.0.0.0/32 is subnetted, 1 subnets
O IA    5.5.5.5 [110/3] via 10.0.123.3, 00:04:10, GigabitEthernet0/0         ! ← inter-area (O IA)
O IA 192.168.1.0/24 [110/3] via 10.0.123.2, 00:04:10, GigabitEthernet0/0     ! ← PC1 LAN via R2
O IA 192.168.2.0/24 [110/3] via 10.0.123.3, 00:04:10, GigabitEthernet0/0     ! ← PC2 LAN via R3
```

### OSPFv2 Neighbor Table

```
R2# show ip ospf neighbor

Neighbor ID     Pri   State           Dead Time   Address         Interface
1.1.1.1           1   FULL/BDR        00:00:39    10.0.123.1      GigabitEthernet0/0   ! ← R1 on seg
3.3.3.3           1   FULL/DR         00:00:38    10.0.123.3      GigabitEthernet0/0   ! ← R3 = DR
4.4.4.4           1   FULL/  -        00:00:17    10.1.24.2       GigabitEthernet0/1   ! ← R4 in Area 1
```

### OSPFv3 (IPv6) Neighbor Table

```
R2# show ospfv3 neighbor

          OSPFv3 1 address-family ipv6 unicast (router-id 2.2.2.2)

Neighbor ID     Pri   State           Dead Time   Interface ID    Interface
1.1.1.1           1   FULL/BDR        00:00:38    3               GigabitEthernet0/0   ! ← R1 IPv6
3.3.3.3           1   FULL/DR         00:00:37    3               GigabitEthernet0/0   ! ← R3 IPv6
4.4.4.4           1   FULL/  -        00:00:32    4               GigabitEthernet0/1   ! ← R4 IPv6 Area 1
```

### OSPFv3 Interface Brief (passive check)

```
R4# show ospfv3 interface brief

Interface    PID   Area            AF      Cost  State Nbrs F/C
Lo0          1     1               ipv6    1     LOOP  0/0
Gi0/0        1     1               ipv6    1     P2P   1/1
Gi0/2        1     1               ipv6    1     DR    0/0     ! ← passive — 0 neighbors on LAN
```

### IPv6 Inter-Area Routes (OI)

```
R1# show ipv6 route ospf
IPv6 Routing Table - default - 11 entries
Codes: C - Connected, L - Local, S - Static, U - Per-user Static route
       B - BGP, R - RIP, I1 - ISIS L1, I2 - ISIS L2, IA - ISIS interarea
       IS - ISIS summary, D - EIGRP, EX - EIGRP external, ND - ND Default
       O - OSPF Intra, OI - OSPF Inter, OE1 - OSPF ext 1, OE2 - OSPF ext 2

OI  2001:DB8:1:1::/64 [110/3]
     via FE80::2, GigabitEthernet0/0                              ! ← PC1 LAN via R2 link-local
OI  2001:DB8:1:24::/64 [110/2]
     via FE80::2, GigabitEthernet0/0                              ! ← Area 1 transit
OI  2001:DB8:2:2::/64 [110/3]
     via FE80::3, GigabitEthernet0/0                              ! ← PC2 LAN via R3
OI  2001:DB8:2:35::/64 [110/2]
     via FE80::3, GigabitEthernet0/0                              ! ← Area 2 transit
OI  2001:DB8:FF::4/128 [110/3]
     via FE80::2, GigabitEthernet0/0                              ! ← R4 Lo0 via R2
OI  2001:DB8:FF::5/128 [110/3]
     via FE80::3, GigabitEthernet0/0                              ! ← R5 Lo0 via R3
```

### End-to-End Dual-Stack Ping

```
PC1> ping 192.168.2.10
84 bytes from 192.168.2.10 icmp_seq=1 ttl=60 time=4.2 ms              ! ← IPv4 path works

PC1> ping 2001:db8:2:2::10
2001:db8:2:2::10 icmp_seq=1 ttl=60 time=4.8 ms                         ! ← IPv6 path works
```

---

## 7. Verification Cheatsheet

### OSPFv2 Multi-Area Configuration

```
router ospf <process-id>
 router-id <id>
 network <prefix> <wildcard> area <area-id>
 passive-interface <interface>
```

| Command | Purpose |
|---------|---------|
| `router ospf 1` | Enter the OSPFv2 process |
| `router-id 2.2.2.2` | Pin router-ID explicitly (don't auto-derive) |
| `network 10.1.24.0 0.0.0.3 area 1` | Enable OSPFv2 on interfaces matching this prefix, in Area 1 |
| `passive-interface GigabitEthernet0/2` | Advertise the subnet but send no hellos out this interface |

> **Exam tip:** A single wildcard mistake (e.g., `area 0` instead of `area 1`)
> prevents neighbor formation. Two routers in different areas never reach
> FULL.

### IPv6 Global Enable and Addressing

```
ipv6 unicast-routing

interface <name>
 ipv6 address <prefix>/64
 ipv6 address <fe80::n> link-local
```

| Command | Purpose |
|---------|---------|
| `ipv6 unicast-routing` | Turn on IPv6 forwarding globally (required!) |
| `ipv6 address 2001:DB8::1/64` | Global unicast address on interface |
| `ipv6 address FE80::1 link-local` | Deterministic link-local (makes neighbor output readable) |

> **Exam tip:** Forgetting `ipv6 unicast-routing` leaves the router with
> IPv6 addresses but no routing -- OSPFv3 neighbors still come up, but
> transit traffic is dropped.

### OSPFv3 (IPv6 Address-Family) Configuration

```
router ospfv3 <process-id>
 router-id <id>
 !
 address-family ipv6 unicast
  passive-interface <interface>
 exit-address-family

interface <name>
 ospfv3 <process-id> ipv6 area <area-id>
```

| Command | Purpose |
|---------|---------|
| `router ospfv3 1` | Create the OSPFv3 process |
| `router-id 2.2.2.2` | **Required** on IPv6-only interfaces (can't auto-derive from v6) |
| `address-family ipv6 unicast` | Enter the IPv6 AF; enables OSPFv3 for IPv6 |
| `passive-interface Gi0/2` | Passive for OSPFv3 (independent of OSPFv2 passive) |
| `ospfv3 1 ipv6 area 1` | On the interface: bind it to OSPFv3 AF-IPv6, Area 1 |

> **Exam tip:** OSPFv3 enables on interfaces **directly**, not via `network`
> statements. Confusing this with OSPFv2 syntax is a common 350-401 trap.

### Verification Commands

| Command | What to Look For |
|---------|------------------|
| `show ip ospf` | "It is an area border router" line on ABRs |
| `show ip ospf border-routers` | List of known ABRs/ASBRs with paths |
| `show ip ospf interface brief` | Interface area assignments; passive state |
| `show ip ospf neighbor` | All OSPFv2 neighbors FULL; DR/BDR on broadcast |
| `show ip ospf database summary` | Type 3 LSAs per area |
| `show ip route ospf` | `O` intra-area vs `O IA` inter-area codes |
| `show ipv6 interface brief` | Link-local + global IPv6 addresses present |
| `show ospfv3 neighbor` | All OSPFv3 neighbors FULL |
| `show ospfv3 interface brief` | IPv6 AF area, passive state |
| `show ipv6 route ospf` | `O` intra-area, `OI` inter-area |
| `show ipv6 ospf database` | OSPFv3 LSDB with IPv6 LSA types |

### Wildcard Mask Quick Reference

| Subnet Mask | Wildcard Mask | Common Use |
|-------------|---------------|------------|
| /30 (255.255.255.252) | 0.0.0.3 | Point-to-point transits |
| /24 (255.255.255.0) | 0.0.0.255 | LAN segments |
| /32 (host) | 0.0.0.0 | Pin a single loopback into one area |

### Common Multi-Area / Dual-Stack Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| Two routers stuck in INIT or EXSTART | Area ID mismatch on the shared link |
| ABR doesn't show up as ABR in `show ip ospf` | Router has interfaces in only one area |
| `O IA` routes absent on one side | ABR missing a `network` statement for the remote area |
| OSPFv2 FULL but OSPFv3 INIT | `ipv6 unicast-routing` missing, or `ospfv3 N ipv6 area X` absent on interface |
| `Transport input` errors | VTY doesn't allow telnet (check `transport input telnet`) |
| IPv6 pings to gateway fail from PC | No IPv6 address on PC, or missing gateway |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Objective 1: Promote R2 and R3 to ABRs

<details>
<summary>Click to view R2 Configuration</summary>

```bash
! R2
router ospf 1
 no network 10.1.24.0 0.0.0.3 area 0
 network 10.1.24.0 0.0.0.3 area 1
```
</details>

<details>
<summary>Click to view R3 Configuration</summary>

```bash
! R3
router ospf 1
 no network 10.2.35.0 0.0.0.3 area 0
 network 10.2.35.0 0.0.0.3 area 2
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ip ospf | include area border
show ip ospf border-routers
show ip ospf database summary
```
</details>

---

### Objective 2: Collapse R4 Into Area 1

<details>
<summary>Click to view R4 Configuration</summary>

```bash
! R4
router ospf 1
 no network 4.4.4.4 0.0.0.0 area 0
 no network 10.1.24.0 0.0.0.3 area 0
 no network 192.168.1.0 0.0.0.255 area 0
 network 4.4.4.4 0.0.0.0 area 1
 network 10.1.24.0 0.0.0.3 area 1
 network 192.168.1.0 0.0.0.255 area 1
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ip ospf interface brief
show ip ospf neighbor
```
</details>

---

### Objective 3: Collapse R5 Into Area 2

<details>
<summary>Click to view R5 Configuration</summary>

```bash
! R5
router ospf 1
 no network 5.5.5.5 0.0.0.0 area 0
 no network 10.2.35.0 0.0.0.3 area 0
 no network 192.168.2.0 0.0.0.255 area 0
 network 5.5.5.5 0.0.0.0 area 2
 network 10.2.35.0 0.0.0.3 area 2
 network 192.168.2.0 0.0.0.255 area 2
```
</details>

---

### Objective 4: Inspect Inter-Area LSAs and Routes

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ip ospf database summary
show ip route ospf
show ip route 192.168.2.0
```
</details>

---

### Objective 5: Enable IPv6 and Address Every Router Interface

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1
ipv6 unicast-routing
!
interface Loopback0
 ipv6 address 2001:DB8:FF::1/128
!
interface GigabitEthernet0/0
 ipv6 address FE80::1 link-local
 ipv6 address 2001:DB8:0:123::1/64
```
</details>

<details>
<summary>Click to view R2 Configuration</summary>

```bash
! R2
ipv6 unicast-routing
!
interface Loopback0
 ipv6 address 2001:DB8:FF::2/128
!
interface GigabitEthernet0/0
 ipv6 address FE80::2 link-local
 ipv6 address 2001:DB8:0:123::2/64
!
interface GigabitEthernet0/1
 ipv6 address FE80::2 link-local
 ipv6 address 2001:DB8:1:24::1/64
```
</details>

<details>
<summary>Click to view R3 Configuration</summary>

```bash
! R3
ipv6 unicast-routing
!
interface Loopback0
 ipv6 address 2001:DB8:FF::3/128
!
interface GigabitEthernet0/0
 ipv6 address FE80::3 link-local
 ipv6 address 2001:DB8:0:123::3/64
!
interface GigabitEthernet0/1
 ipv6 address FE80::3 link-local
 ipv6 address 2001:DB8:2:35::1/64
```
</details>

<details>
<summary>Click to view R4 Configuration</summary>

```bash
! R4
ipv6 unicast-routing
!
interface Loopback0
 ipv6 address 2001:DB8:FF::4/128
!
interface GigabitEthernet0/0
 ipv6 address FE80::4 link-local
 ipv6 address 2001:DB8:1:24::2/64
!
interface GigabitEthernet0/2
 ipv6 address FE80::4 link-local
 ipv6 address 2001:DB8:1:1::1/64
```
</details>

<details>
<summary>Click to view R5 Configuration</summary>

```bash
! R5
ipv6 unicast-routing
!
interface Loopback0
 ipv6 address 2001:DB8:FF::5/128
!
interface GigabitEthernet0/0
 ipv6 address FE80::5 link-local
 ipv6 address 2001:DB8:2:35::2/64
!
interface GigabitEthernet0/1
 ipv6 address FE80::5 link-local
 ipv6 address 2001:DB8:2:2::1/64
```
</details>

---

### Objective 6: Configure IPv6 on PC1 and PC2

<details>
<summary>Click to view PC1 Configuration</summary>

```
PC1> ip 2001:db8:1:1::10/64 2001:db8:1:1::1
PC1> save
```
</details>

<details>
<summary>Click to view PC2 Configuration</summary>

```
PC2> ip 2001:db8:2:2::10/64 2001:db8:2:2::1
PC2> save
```
</details>

---

### Objective 7: Bring Up OSPFv3 With IPv6 Address-Family

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1
router ospfv3 1
 router-id 1.1.1.1
 !
 address-family ipv6 unicast
 exit-address-family
!
interface Loopback0
 ospfv3 1 ipv6 area 0
!
interface GigabitEthernet0/0
 ospfv3 1 ipv6 area 0
```
</details>

<details>
<summary>Click to view R2 Configuration</summary>

```bash
! R2
router ospfv3 1
 router-id 2.2.2.2
 !
 address-family ipv6 unicast
 exit-address-family
!
interface Loopback0
 ospfv3 1 ipv6 area 0
!
interface GigabitEthernet0/0
 ospfv3 1 ipv6 area 0
!
interface GigabitEthernet0/1
 ospfv3 1 ipv6 area 1
```
</details>

<details>
<summary>Click to view R3 Configuration</summary>

```bash
! R3
router ospfv3 1
 router-id 3.3.3.3
 !
 address-family ipv6 unicast
 exit-address-family
!
interface Loopback0
 ospfv3 1 ipv6 area 0
!
interface GigabitEthernet0/0
 ospfv3 1 ipv6 area 0
!
interface GigabitEthernet0/1
 ospfv3 1 ipv6 area 2
```
</details>

<details>
<summary>Click to view R4 Configuration</summary>

```bash
! R4
router ospfv3 1
 router-id 4.4.4.4
 !
 address-family ipv6 unicast
  passive-interface GigabitEthernet0/2
 exit-address-family
!
interface Loopback0
 ospfv3 1 ipv6 area 1
!
interface GigabitEthernet0/0
 ospfv3 1 ipv6 area 1
!
interface GigabitEthernet0/2
 ospfv3 1 ipv6 area 1
```
</details>

<details>
<summary>Click to view R5 Configuration</summary>

```bash
! R5
router ospfv3 1
 router-id 5.5.5.5
 !
 address-family ipv6 unicast
  passive-interface GigabitEthernet0/1
 exit-address-family
!
interface Loopback0
 ospfv3 1 ipv6 area 2
!
interface GigabitEthernet0/0
 ospfv3 1 ipv6 area 2
!
interface GigabitEthernet0/1
 ospfv3 1 ipv6 area 2
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ospfv3 neighbor
show ospfv3 interface brief
show ipv6 route ospf
show ipv6 ospf database
```
</details>

---

### Objective 8: End-to-End Dual-Stack Reachability

<details>
<summary>Click to view Verification Commands</summary>

```
PC1> ping 192.168.2.10
PC1> ping 2001:db8:2:2::10
PC1> trace 192.168.2.10
PC1> trace 2001:db8:2:2::10

PC2> ping 192.168.1.10
PC2> ping 2001:db8:1:1::10
```
</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. Inject the fault first, then
diagnose and fix using only `show` commands.

### Workflow

```bash
python3 setup_lab.py                                   # reset to known-good
python3 scripts/fault-injection/apply_solution.py      # apply full multi-area solution
python3 scripts/fault-injection/inject_scenario_01.py  # Ticket 1
python3 scripts/fault-injection/apply_solution.py      # restore
```

Scripts refuse to inject if the device isn't already in the solution
state (pre-flight check). Bypass with `--skip-preflight` only if you know
why.

---

### Ticket 1 -- R2 and R4 Adjacency Never Reaches FULL

After a planned Area 1 rollout, R2 and R4 no longer form an OSPFv2
adjacency -- `show ip ospf neighbor` on either side is empty or the
session bounces between INIT and DOWN. Everything else in the domain
looks normal.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py`

**Success criteria:** R2↔R4 OSPFv2 neighbor reaches FULL on the Gi0/1↔Gi0/0
link; 192.168.1.0/24 reachable from R1; Type 3 LSA for R4's loopback
visible in R1's LSDB.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Confirm the symptom: `show ip ospf neighbor` on R2 and R4.
2. Check Layer 3 reachability: `ping 10.1.24.2` from R2.
3. Inspect interface-level OSPF state on both sides:
   `show ip ospf interface Gi0/1` on R2 and `show ip ospf interface Gi0/0`
   on R4. Compare the "Area" line.
4. Mismatch found: R2 has Gi0/1 in Area 1, R4 has Gi0/0 in Area 0.
   OSPF refuses to peer across an area mismatch.
5. Look at R4's `router ospf 1` network statements -- one of them still
   references `area 0` for the 10.1.24.0/30 network.
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! R4
router ospf 1
 no network 10.1.24.0 0.0.0.3 area 0
 network 10.1.24.0 0.0.0.3 area 1
```

Within one hello interval (5 s on this link), R2↔R4 progresses through
EXSTART → EXCHANGE → LOADING → FULL.
</details>

---

### Ticket 2 -- IPv4 Reaches PC2 but IPv6 From PC1 Times Out

After the dual-stack rollout, `ping 192.168.2.10` from PC1 succeeds, but
`ping 2001:db8:2:2::10` from PC1 returns "host unreachable" or times out.
Both PCs show their IPv6 addresses correctly with `show ipv6`.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py`

**Success criteria:** PC1 can ping PC2's IPv6 address end-to-end; all
OSPFv3 neighbors return to FULL; `show ipv6 route ospf` on R1 lists both
`2001:DB8:1:1::/64` and `2001:DB8:2:2::/64` as `OI` routes.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Confirm the asymmetry: `ping 192.168.2.10` from PC1 works but
   `ping 2001:db8:2:2::10` fails. So OSPFv2 is converged but OSPFv3 isn't.
2. Walk the path: on R1, `show ipv6 route ospf` -- is
   `2001:DB8:2:2::/64` present? If missing on R1, the problem is upstream
   on R3 or R5.
3. On R3, `show ospfv3 neighbor`. If R5 is absent, OSPFv3 adjacency is
   broken between R3 and R5.
4. On R5, `show ospfv3 interface brief`. Gi0/0 (the transit to R3) may
   be absent from the list entirely -- meaning OSPFv3 is not enabled on
   that interface.
5. Compare to the Gi0/0 config: `show running-config interface Gi0/0` on
   R5. An `ospfv3 1 ipv6 area 2` line is missing.
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! R5
interface GigabitEthernet0/0
 ospfv3 1 ipv6 area 2
```

OSPFv3 neighbor with R3 forms immediately; Type 3 LSAs propagate into
Area 0; within a few seconds, PC1's IPv6 ping to PC2 succeeds.
</details>

---

### Ticket 3 -- PC2 Unreachable From Everywhere (IPv4 and IPv6)

After a maintenance window, PC2 (192.168.2.10 / 2001:db8:2:2::10) is
unreachable from every other device in the lab. PC1 can ping R5's
loopback (5.5.5.5) for a moment but the route disappears from R1/R2/R4's
tables. R5 can ping PC2 locally without issue.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py`

**Success criteria:** PC1 can ping PC2 on both stacks; R1 shows `O IA`
routes for 10.2.35.0/30, 192.168.2.0/24, and 5.5.5.5/32; R3 is listed as
an ABR in `show ip ospf border-routers` on R1.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Confirm the symptom from multiple vantage points: `show ip route
   192.168.2.0` on R1 and R2 (missing); same on R4 (missing).
2. On R1, `show ip ospf border-routers`. If R3 is absent from the ABR
   list, R3 is no longer acting as an ABR from R1's perspective.
3. On R3, `show ip ospf`. "It is an area border router" is absent --
   R3 is no longer an ABR. That means R3 is participating in only one
   area.
4. On R3, `show ip ospf interface brief`. Gi0/1 (the transit to R5) is
   missing from the list entirely.
5. Compare to the `router ospf 1` config: a `network 10.2.35.0 0.0.0.3
   area 2` line is missing, so R3 is not participating on that link at
   all -- no adjacency with R5, no Type 3 LSAs for Area 2 prefixes.
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! R3
router ospf 1
 network 10.2.35.0 0.0.0.3 area 2
```

R3↔R5 adjacency reforms. R3 regains ABR status, injects Type 3 LSAs for
Area 2 into Area 0, and PC2 becomes reachable from the rest of the
network.
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] R2 shows "It is an area border router" in `show ip ospf`
- [ ] R3 shows "It is an area border router" in `show ip ospf`
- [ ] R4 has every interface in Area 1 per `show ip ospf interface brief`
- [ ] R5 has every interface in Area 2 per `show ip ospf interface brief`
- [ ] R1 `show ip ospf database summary` lists Type 3 LSAs for every Area 1
      and Area 2 prefix
- [ ] R1 `show ip route ospf` shows `O IA` entries for `10.1.24.0/30`,
      `192.168.1.0/24`, `4.4.4.4/32`, `10.2.35.0/30`, `192.168.2.0/24`,
      `5.5.5.5/32`
- [ ] Every router has `ipv6 unicast-routing` enabled
- [ ] Every router interface in the OSPF domain has a global IPv6 address
      and a deterministic `FE80::<n>` link-local
- [ ] PC1 and PC2 have both IPv4 and IPv6 addresses configured and saved
- [ ] Every OSPFv3 adjacency is FULL (`show ospfv3 neighbor` on all routers)
- [ ] R4 Gi0/2 and R5 Gi0/1 are passive for **both** OSPFv2 and OSPFv3
- [ ] `ping 192.168.2.10` from PC1 succeeds
- [ ] `ping 2001:db8:2:2::10` from PC1 succeeds
- [ ] `ping 192.168.1.10` from PC2 succeeds
- [ ] `ping 2001:db8:1:1::10` from PC2 succeeds

### Troubleshooting

- [ ] Ticket 1 resolved -- R2↔R4 FULL, PC1 LAN reachable
- [ ] Ticket 2 resolved -- PC1 IPv6 ping to PC2 succeeds end-to-end
- [ ] Ticket 3 resolved -- R3 shows ABR, PC2 reachable from all routers
- [ ] All fault-injection scripts ran pre-flight checks before injecting
- [ ] `apply_solution.py` restored the lab to converged state after each
      ticket
