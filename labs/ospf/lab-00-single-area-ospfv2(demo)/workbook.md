# Lab 00 — Single-Area OSPFv2 Fundamentals

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

**Exam Objective:** 3.2.a — Compare routing concepts of EIGRP and OSPF (link state, metrics, path selection, area types) | 3.2.b — Configure simple OSPFv2/v3 environments (neighbor adjacency, network types, passive-interface)

OSPF is the most widely deployed interior gateway protocol in enterprise networks. Unlike
distance-vector protocols (EIGRP, RIP), OSPF is a true link-state protocol — every router
builds a complete topological map of the network, then independently computes shortest paths
using Dijkstra's SPF algorithm. This lab introduces the core OSPF mechanics: process
configuration, neighbor adjacency formation, the link-state database, and route computation
— all within a single area to isolate fundamentals before multi-area complexity is added.

### Link-State Protocol Fundamentals

In a link-state protocol, each router originates Link-State Advertisements (LSAs) describing
its directly connected links (neighbors, costs, network types). These LSAs are flooded
reliably to all routers in the area, building an identical Link-State Database (LSDB) on
every router. Each router then runs Dijkstra's Shortest Path First algorithm independently
on its local copy of the LSDB to compute a loop-free shortest-path tree rooted at itself.

Key differences from distance-vector:
- **Full topology visibility** — every router sees the complete area graph, not just
  next-hop distances
- **Fast convergence** — incremental LSA updates trigger targeted SPF recalculations
- **Loop-free by design** — SPF computation guarantees loop-free paths
- **Bandwidth-based metric** — OSPF cost = reference bandwidth / interface bandwidth
  (default reference: 100 Mbps)

### OSPF Neighbor Adjacency

Two OSPF routers on the same link must agree on several parameters before forming a neighbor
relationship:

| Parameter | Must Match? | Default |
|-----------|-------------|---------|
| Hello interval | Yes | 10s (broadcast/p2p), 30s (NBMA) |
| Dead interval | Yes | 4x hello (40s on broadcast/p2p) |
| Area ID | Yes | — |
| Authentication | Yes | None |
| Subnet mask | Yes (broadcast/NBMA) | — |
| Stub area flag | Yes | Not stub |
| MTU | Must match for DBD exchange | 1500 |

The neighbor state machine progresses through: **Down → Init → 2-Way → ExStart → Exchange →
Loading → Full**. On broadcast segments, only the DR and BDR form Full adjacencies with all
neighbors; DROTHERs remain in 2-Way with each other.

### OSPF Router-ID

The OSPF router-ID is a 32-bit identifier that uniquely identifies each router in the OSPF
domain. Selection priority:
1. Explicitly configured via `router-id` command (recommended)
2. Highest IP address on any loopback interface
3. Highest IP address on any active physical interface

Best practice is to always configure the router-ID explicitly to prevent unexpected changes
when interfaces go down.

### LSA Types in Single-Area OSPF

In a single-area deployment, you will encounter two LSA types:

| LSA Type | Name | Originated By | Purpose |
|----------|------|---------------|---------|
| Type 1 | Router LSA | Every router | Describes router's links and their costs within the area |
| Type 2 | Network LSA | DR only | Describes the set of routers attached to a broadcast/NBMA segment |

Type 2 LSAs only exist on broadcast or NBMA segments where a DR is elected. On point-to-point
links, there is no DR and therefore no Type 2 LSA.

### Passive Interfaces

The `passive-interface` command stops OSPF from sending hello packets on an interface while
still advertising that interface's network in LSAs. Use passive-interface on:
- LAN segments where no OSPF neighbor exists (end-host subnets)
- Loopback interfaces (passive by default for OSPF, but explicit is clearer)

Without passive-interface, OSPF wastes CPU cycles sending hellos into subnets where no
neighbor will ever respond, and exposes the OSPF process to potential rogue neighbor attacks.

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| OSPF process configuration | Enable OSPF with explicit router-ID and network statements |
| Neighbor adjacency verification | Confirm adjacency states using show commands |
| LSDB analysis | Read and interpret Type 1 and Type 2 LSAs |
| Passive-interface design | Protect end-host subnets from unnecessary OSPF participation |
| Route verification | Trace OSPF-learned routes in the routing table |
| Timer manipulation | Understand and modify hello/dead intervals |

---

## 2. Topology & Scenario

### Network Diagram

```
                         ┌──────────────────────┐
                         │          R1           │
                         │  (Backbone Router)    │
                         │  Lo0: 1.1.1.1/32      │
                         └──────────┬────────────┘
                                    │ Gi0/0
                                    │ 10.0.123.1/24
                                    │
                         ┌──────────┴────────────┐
                         │     SW-AREA0          │
                         │  (Unmanaged Switch)   │
                         │  10.0.123.0/24        │
                         │  Broadcast Segment    │
                         └───┬──────────────┬────┘
                             │              │
                   Gi0/0     │              │     Gi0/0
                 10.0.123.2  │              │  10.0.123.3
              ┌──────────────┴──┐      ┌────┴──────────────┐
              │       R2        │      │       R3           │
              │  (Future ABR)   │      │  (Future ABR)      │
              │ Lo0: 2.2.2.2   │      │  Lo0: 3.3.3.3      │
              └──┬──────────────┘      └───┬────────────────┘
           Gi0/1 │                         │ Gi0/1
       10.1.24.1 │                         │ 10.2.35.1
                 │                         │
       10.1.24.2 │                         │ 10.2.35.2
           Gi0/0 │                         │ Gi0/0
              ┌──┴──────────────┐      ┌───┴────────────────┐
              │       R4        │      │       R5            │
              │  (Internal)     │      │  (Future ASBR)      │
              │ Lo0: 4.4.4.4   │      │  Lo0: 5.5.5.5       │
              └──┬──────────────┘      └───┬────────────────┘
           Gi0/2 │                         │ Gi0/1
      192.168.1.1│                         │192.168.2.1
                 │                         │
      192.168.1.10                         192.168.2.10
              ┌──┴───────┐            ┌────┴────────┐
              │   PC1    │            │    PC2      │
              │ .1.10/24 │            │  .2.10/24   │
              └──────────┘            └─────────────┘
```

### Scenario

You are a network engineer at Meridian Systems. The company has deployed five routers across
a single campus. Before segmenting the network into multiple OSPF areas (a future project),
your task is to establish baseline OSPF connectivity with all routers in a single Area 0.
This gives you a working foundation and lets you verify neighbor adjacencies, examine the
link-state database, and confirm end-to-end reachability between the PC1 and PC2 user
segments before introducing multi-area complexity.

The network team requires:
- Every router uses an explicit router-ID matching its Loopback0 address
- LAN-facing interfaces (PC segments) must be passive to OSPF
- All connected networks must be reachable via OSPF

---

## 3. Hardware & Environment Specifications

### Device Inventory

| Device | Platform | Role | Image |
|--------|----------|------|-------|
| R1 | IOSv | Backbone router | vios-adventerprisek9 |
| R2 | IOSv | Future ABR (Area 0/1) | vios-adventerprisek9 |
| R3 | IOSv | Future ABR (Area 0/2) | vios-adventerprisek9 |
| R4 | IOSv | Internal router | vios-adventerprisek9 |
| R5 | IOSv | Future ASBR | vios-adventerprisek9 |
| SW-AREA0 | Unmanaged switch | Shared broadcast segment | EVE-NG built-in |
| PC1 | VPC | End host (192.168.1.0/24) | — |
| PC2 | VPC | End host (192.168.2.0/24) | — |

### Cabling Table

| Link ID | Source | Destination | Type | Purpose |
|---------|--------|-------------|------|---------|
| L1 | R1 Gi0/0 | SW-AREA0 port1 | Ethernet | R1 to Area 0 broadcast segment |
| L2 | R2 Gi0/0 | SW-AREA0 port2 | Ethernet | R2 to Area 0 broadcast segment |
| L3 | R3 Gi0/0 | SW-AREA0 port3 | Ethernet | R3 to Area 0 broadcast segment |
| L4 | R2 Gi0/1 | R4 Gi0/0 | Point-to-point | R2 to R4 link |
| L5 | R3 Gi0/1 | R5 Gi0/0 | Point-to-point | R3 to R5 link |
| L6 | PC1 e0 | R4 Gi0/2 | Ethernet | PC1 LAN segment |
| L7 | PC2 e0 | R5 Gi0/1 | Ethernet | PC2 LAN segment |

### Console Access Table

| Device | Console Port | Connection |
|--------|-------------|------------|
| R1 | _dynamic_ | `telnet <eve-ng-ip> <port>` |
| R2 | _dynamic_ | `telnet <eve-ng-ip> <port>` |
| R3 | _dynamic_ | `telnet <eve-ng-ip> <port>` |
| R4 | _dynamic_ | `telnet <eve-ng-ip> <port>` |
| R5 | _dynamic_ | `telnet <eve-ng-ip> <port>` |

> Console ports are assigned dynamically by EVE-NG. Check the EVE-NG web UI or use
> `GET /api/labs/<lab>/nodes` to discover assigned port numbers.

### IP Addressing

| Network | Subnet | Description |
|---------|--------|-------------|
| 10.0.123.0/24 | R1=.1, R2=.2, R3=.3 | Area 0 shared broadcast segment |
| 10.1.24.0/30 | R2=.1, R4=.2 | R2-R4 point-to-point link |
| 10.2.35.0/30 | R3=.1, R5=.2 | R3-R5 point-to-point link |
| 192.168.1.0/24 | R4=.1, PC1=.10 | PC1 LAN segment |
| 192.168.2.0/24 | R5=.1, PC2=.10 | PC2 LAN segment |

| Router | Loopback0 |
|--------|-----------|
| R1 | 1.1.1.1/32 |
| R2 | 2.2.2.2/32 |
| R3 | 3.3.3.3/32 |
| R4 | 4.4.4.4/32 |
| R5 | 5.5.5.5/32 |

---

## 4. Base Configuration

### What IS pre-loaded (initial-configs/)

Each router starts with:
- Hostname set
- DNS lookup disabled
- IP addresses on all active interfaces (Loopbacks, GigabitEthernet links)
- Interfaces brought up (no shutdown)
- Console and VTY line settings

### What is NOT pre-loaded (you will configure)

- OSPF routing process
- Router-ID assignment
- Network statements advertising subnets into OSPF
- Passive-interface on LAN segments
- Hello/dead timer adjustments

### Loading Initial Configs

```bash
python3 setup_lab.py --host <eve-ng-ip>
```

### PC Configuration (manual)

After loading initial configs, configure the VPCs interactively:

**PC1:**
```
ip 192.168.1.10 255.255.255.0 192.168.1.1
```

**PC2:**
```
ip 192.168.2.10 255.255.255.0 192.168.2.1
```

---

## 5. Lab Challenge: Core Implementation

### Task 1: Enable OSPF with Explicit Router-IDs

- On all five routers (R1 through R5), enable OSPF process 1.
- Set the router-ID explicitly on each router to match its Loopback0 address (e.g., R1 uses 1.1.1.1, R2 uses 2.2.2.2, etc.).

**Verification:** `show ip ospf` — Router-ID must match the explicitly configured value on each router.

---

### Task 2: Advertise All Connected Networks into Area 0

- On each router, advertise all connected subnets into OSPF Area 0 using network statements with appropriate wildcard masks:
  - R1: Loopback0 and the 10.0.123.0/24 segment
  - R2: Loopback0, the 10.0.123.0/24 segment, and the 10.1.24.0/30 link to R4
  - R3: Loopback0, the 10.0.123.0/24 segment, and the 10.2.35.0/30 link to R5
  - R4: Loopback0, the 10.1.24.0/30 link to R2, and the 192.168.1.0/24 PC1 LAN
  - R5: Loopback0, the 10.2.35.0/30 link to R3, and the 192.168.2.0/24 PC2 LAN
- All network statements must use Area 0 since this is a single-area deployment.

**Verification:** `show ip ospf interface brief` — every active interface must appear under Area 0.

---

### Task 3: Verify OSPF Neighbor Adjacencies

- After configuring network statements, verify that OSPF neighbors form on each link:
  - R1 should have neighbors R2 and R3 on the broadcast segment
  - R2 should have neighbors R1, R3 (broadcast segment) and R4 (point-to-point)
  - R3 should have neighbors R1, R2 (broadcast segment) and R5 (point-to-point)
  - R4 should have neighbor R2
  - R5 should have neighbor R3
- Identify the DR and BDR on the 10.0.123.0/24 broadcast segment. Note which router was elected and why (based on router-ID, since all priorities default to 1).

**Verification:** `show ip ospf neighbor` — all neighbors must be in FULL state (or FULL/DR, FULL/BDR, 2WAY/DROTHER on the broadcast segment).

---

### Task 4: Examine the Link-State Database

- On R1, examine the full LSDB and identify:
  - How many Type 1 (Router) LSAs exist — there should be one per router in the area
  - Whether a Type 2 (Network) LSA exists for the 10.0.123.0/24 broadcast segment, and which router originated it (must be the DR)
  - Why no Type 2 LSA exists for the R2-R4 or R3-R5 point-to-point links
- Compare the LSDB on R4 — it should be identical to R1's (same area, same database).

**Verification:** `show ip ospf database` — count Router LSAs (should equal number of routers in area), verify Network LSA originated by DR.

---

### Task 5: Configure Passive Interfaces on LAN Segments

- On R4, set the interface facing PC1 (Gi0/2) as passive for OSPF.
- On R5, set the interface facing PC2 (Gi0/1) as passive for OSPF.
- Verify that the passive interfaces still appear in OSPF (their networks are still advertised) but no hellos are sent.

**Verification:** `show ip ospf interface <int>` — passive interfaces must show "No Hellos (Passive interface)". `show ip route ospf` on R1 must still show routes to 192.168.1.0/24 and 192.168.2.0/24.

---

### Task 6: Verify End-to-End Reachability

- From PC1 (192.168.1.10), ping PC2 (192.168.2.10).
- From PC1, ping R1's Loopback0 (1.1.1.1).
- From R1, ping R4's LAN interface (192.168.1.1) and R5's LAN interface (192.168.2.1).
- Trace the path from PC1 to PC2 — the expected hops are: PC1 → R4 → R2 → R3 → R5 → PC2.

**Verification:** All pings succeed. `traceroute 192.168.2.10` from PC1 should show 4 router hops.

---

### Task 7: Verify OSPF Routes in the Routing Table

- On R1, examine the OSPF routing table. All remote networks must appear as "O" (intra-area) routes.
- Confirm that the cost (metric) for each route reflects the cumulative interface costs along the shortest path.
- On R4, check which next-hop is used to reach the 192.168.2.0/24 network (should be R2 at 10.1.24.1).

**Verification:** `show ip route ospf` — all routes must show "O" prefix (not "O IA" — that would indicate multi-area). `show ip route 192.168.2.0` on R4 must show via 10.1.24.1.

---

### Task 8: Examine and Adjust Hello/Dead Timers

- On the R2-R4 point-to-point link, examine the current hello and dead interval values.
- Change the hello interval to 5 seconds on both R2 Gi0/1 and R4 Gi0/0. The dead interval must adjust accordingly (dead = 4x hello = 20 seconds).
- Verify the adjacency reforms with the new timer values.
- Observe what happens if you change only one side — temporarily set R2's hello to 5 seconds while R4 remains at 10 seconds. The adjacency must drop due to timer mismatch.
- After observing the mismatch, restore matching timers (5/20 on both sides).

**Verification:** `show ip ospf interface <int>` — Hello interval and Dead interval must show the modified values. After mismatch, `show ip ospf neighbor` on R2 should show R4's state dropping.

---

## 6. Verification & Analysis

### Task 1 — OSPF Process with Router-ID

```
R1# show ip ospf
 Routing Process "ospf 1" with ID 1.1.1.1                         ! ← explicit router-ID
 Start time: 00:00:02.456, Time elapsed: 00:05:23.789
 Supports only single TOS(TOS0) routes
 Supports opaque LSA
 ...
 Number of areas in this router is 1. 1 normal 0 stub 0 nssa      ! ← single area
```

### Task 2 — Network Statements

```
R2# show ip ospf interface brief
Interface    PID   Area            IP Address/Mask    Cost  State Nbrs F/C
Lo0          1     0               2.2.2.2/32         1     LOOP  0/0
Gi0/0        1     0               10.0.123.2/24      1     BDR   2/3  ! ← broadcast segment
Gi0/1        1     0               10.1.24.1/30       1     P2P   1/1  ! ← point-to-point to R4
```

### Task 3 — Neighbor Adjacencies

```
R1# show ip ospf neighbor

Neighbor ID     Pri   State           Dead Time   Address         Interface
3.3.3.3           1   FULL/DR         00:00:36    10.0.123.3      GigabitEthernet0/0  ! ← R3 is DR
2.2.2.2           1   FULL/BDR        00:00:37    10.0.123.2      GigabitEthernet0/0  ! ← R2 is BDR

! R1 (router-ID 1.1.1.1) is DROTHER — lowest router-ID among the three
! DR election winner: R3 (3.3.3.3) — highest router-ID
! BDR: R2 (2.2.2.2) — second highest router-ID
```

```
R2# show ip ospf neighbor

Neighbor ID     Pri   State           Dead Time   Address         Interface
3.3.3.3           1   FULL/DR         00:00:33    10.0.123.3      GigabitEthernet0/0  ! ← R3 DR
1.1.1.1           1   2WAY/DROTHER    00:00:38    10.0.123.1      GigabitEthernet0/0  ! ← R1 DROTHER
4.4.4.4           0   FULL/  -        00:00:35    10.1.24.2       GigabitEthernet0/1  ! ← R4 (p2p, pri 0)
```

### Task 4 — Link-State Database

```
R1# show ip ospf database

            OSPF Router with ID (1.1.1.1) (Process ID 1)

                Router Link States (Area 0)

Link ID         ADV Router      Age         Seq#       Checksum Link count
1.1.1.1         1.1.1.1         245         0x80000003 0x00ABCD 2          ! ← R1 Router LSA
2.2.2.2         2.2.2.2         243         0x80000005 0x001234 4          ! ← R2 Router LSA
3.3.3.3         3.3.3.3         241         0x80000004 0x005678 4          ! ← R3 Router LSA
4.4.4.4         4.4.4.4         240         0x80000003 0x009ABC 3          ! ← R4 Router LSA
5.5.5.5         5.5.5.5         239         0x80000003 0x00DEF0 3          ! ← R5 Router LSA
! 5 Router LSAs = 5 routers in the area

                Net Link States (Area 0)

Link ID         ADV Router      Age         Seq#       Checksum
10.0.123.3      3.3.3.3         241         0x80000001 0x004567            ! ← Type 2 from DR (R3)
! Only ONE Network LSA — for the broadcast segment
! No Type 2 for R2-R4 or R3-R5 links (point-to-point = no DR)
```

### Task 5 — Passive Interfaces

```
R4# show ip ospf interface GigabitEthernet0/2
GigabitEthernet0/2 is up, line protocol is up
  Internet Address 192.168.1.1/24, Area 0
  Process ID 1, Router ID 4.4.4.4, Network Type BROADCAST, Cost: 1
  ...
  No Hellos (Passive interface)                                    ! ← passive confirmed
  Neighbor Count is 0, Adjacent neighbor count is 0
```

```
R1# show ip route ospf
...
O     192.168.1.0/24 [110/3] via 10.0.123.2, 00:02:15, Gi0/0     ! ← still advertised
O     192.168.2.0/24 [110/3] via 10.0.123.3, 00:02:15, Gi0/0     ! ← still advertised
```

### Task 6 — End-to-End Reachability

```
PC1> ping 192.168.2.10
84 bytes from 192.168.2.10 icmp_seq=1 ttl=61 time=15.678 ms       ! ← TTL=61 = 4 hops
84 bytes from 192.168.2.10 icmp_seq=2 ttl=61 time=10.234 ms
84 bytes from 192.168.2.10 icmp_seq=3 ttl=61 time=9.876 ms

! Path: PC1 → R4 → R2 → R3 → R5 → PC2 (4 router hops, TTL 64-4=60... 
! VPC starts at TTL=64, passes through 4 routers → arrives at 60, 
! but replies traverse 4 hops too → depends on VPC implementation)

PC1> trace 192.168.2.10
trace to 192.168.2.10, 8 hops max
 1  192.168.1.1   3.456 ms                                         ! ← R4
 2  10.1.24.1     5.678 ms                                         ! ← R2
 3  10.0.123.3    7.890 ms                                         ! ← R3
 4  192.168.2.1   9.012 ms                                         ! ← R5 (PC2 gateway)
```

### Task 7 — OSPF Routing Table

```
R1# show ip route ospf
...
      1.0.0.0/32 is subnetted, 1 subnets
O        1.1.1.1 is directly connected, Loopback0
      2.0.0.0/32 is subnetted, 1 subnets
O        2.2.2.2 [110/2] via 10.0.123.2, 00:05:00, GigabitEthernet0/0
      3.0.0.0/32 is subnetted, 1 subnets
O        3.3.3.3 [110/2] via 10.0.123.3, 00:05:00, GigabitEthernet0/0
      4.0.0.0/32 is subnetted, 1 subnets
O        4.4.4.4 [110/3] via 10.0.123.2, 00:04:50, GigabitEthernet0/0  ! ← via R2
      5.0.0.0/32 is subnetted, 1 subnets
O        5.5.5.5 [110/3] via 10.0.123.3, 00:04:50, GigabitEthernet0/0  ! ← via R3
      10.0.0.0/8 is variably subnetted
O        10.1.24.0/30 [110/2] via 10.0.123.2, 00:05:00, GigabitEthernet0/0
O        10.2.35.0/30 [110/2] via 10.0.123.3, 00:05:00, GigabitEthernet0/0
O     192.168.1.0/24 [110/3] via 10.0.123.2, 00:04:50, Gi0/0     ! ← all "O" (intra-area)
O     192.168.2.0/24 [110/3] via 10.0.123.3, 00:04:50, Gi0/0     ! ← not "O IA"
```

### Task 8 — Hello/Dead Timer Adjustment

```
! After setting hello 5 on both R2 Gi0/1 and R4 Gi0/0:
R2# show ip ospf interface GigabitEthernet0/1
GigabitEthernet0/1 is up, line protocol is up
  Internet Address 10.1.24.1/30, Area 0
  Process ID 1, Router ID 2.2.2.2, Network Type POINT_TO_POINT, Cost: 1
  ...
  Timer intervals configured, Hello 5, Dead 20, Wait 20, Retransmit 5  ! ← modified timers
  Hello due in 00:00:03
  Neighbor Count is 1, Adjacent neighbor count is 1

! During mismatch (R2=5s, R4=10s):
R2# show ip ospf neighbor
! R4 will disappear — dead timer mismatch prevents adjacency
```

---

## 7. Verification Cheatsheet

### OSPF Process Configuration

```
router ospf <process-id>
 router-id <A.B.C.D>
 network <network> <wildcard> area <id>
 passive-interface <interface>
```

| Command | Purpose |
|---------|---------|
| `router ospf <pid>` | Enable OSPF routing process |
| `router-id <A.B.C.D>` | Set explicit 32-bit router identifier |
| `network <net> <wc> area <id>` | Advertise matching interfaces into an OSPF area |
| `passive-interface <int>` | Suppress hellos on interface (still advertises subnet) |

> **Exam tip:** The `network` command doesn't advertise a network — it enables OSPF on interfaces whose IP matches the network/wildcard. The actual network advertised in LSAs is the interface's connected subnet.

### Hello/Dead Timer Configuration

```
interface <type>
 ip ospf hello-interval <seconds>
 ip ospf dead-interval <seconds>
```

| Command | Purpose |
|---------|---------|
| `ip ospf hello-interval <sec>` | Set OSPF hello packet interval (both sides must match) |
| `ip ospf dead-interval <sec>` | Set time before declaring neighbor dead (typically 4x hello) |

> **Exam tip:** Changing the hello interval does NOT automatically change the dead interval on IOS. You must set both, or use `ip ospf dead-interval minimal hello-multiplier <n>` for sub-second convergence.

### Verification Commands

| Command | What to Look For |
|---------|-----------------|
| `show ip ospf` | Router-ID, process ID, number of areas, SPF statistics |
| `show ip ospf neighbor` | Neighbor state (FULL/2WAY), DR/BDR role, dead timer countdown |
| `show ip ospf interface brief` | Area assignment, cost, state (DR/BDR/DROTHER/P2P), neighbor count |
| `show ip ospf interface <int>` | Hello/dead timers, network type, passive status, DR/BDR IP |
| `show ip ospf database` | LSDB summary — count Router LSAs, check Network LSAs |
| `show ip ospf database router <rid>` | Detailed Type 1 LSA for a specific router |
| `show ip ospf database network` | Detailed Type 2 LSA (broadcast segments only) |
| `show ip route ospf` | OSPF-learned routes — check "O" vs "O IA" prefix |
| `show ip route <prefix>` | Detailed route entry — next-hop, metric, source router-ID |

### Wildcard Mask Quick Reference

| Subnet Mask | Wildcard Mask | Common Use |
|-------------|---------------|------------|
| 255.255.255.255 (/32) | 0.0.0.0 | Exact host (loopback) |
| 255.255.255.252 (/30) | 0.0.0.3 | Point-to-point link |
| 255.255.255.0 (/24) | 0.0.0.255 | Standard LAN subnet |
| 255.255.0.0 (/16) | 0.0.255.255 | Class B summary |

### Common OSPF Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| Neighbor stuck in INIT | One-way communication — ACL blocking OSPF, or asymmetric path |
| Neighbor stuck in EXSTART/EXCHANGE | MTU mismatch between neighbors |
| Neighbor not appearing at all | Hello/dead timer mismatch, area ID mismatch, or interface not in OSPF |
| Adjacency flapping (up/down) | Unstable link, duplex mismatch, or hello timer too aggressive |
| Route missing from table | Network not advertised (missing `network` statement), or passive on transit link |
| Unexpected DR election | Router-ID or priority changed; DR election is non-preemptive |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Tasks 1-2: OSPF Process and Network Statements

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1
router ospf 1
 router-id 1.1.1.1
 network 1.1.1.1 0.0.0.0 area 0
 network 10.0.123.0 0.0.0.255 area 0
```
</details>

<details>
<summary>Click to view R2 Configuration</summary>

```bash
! R2
router ospf 1
 router-id 2.2.2.2
 network 2.2.2.2 0.0.0.0 area 0
 network 10.0.123.0 0.0.0.255 area 0
 network 10.1.24.0 0.0.0.3 area 0
```
</details>

<details>
<summary>Click to view R3 Configuration</summary>

```bash
! R3
router ospf 1
 router-id 3.3.3.3
 network 3.3.3.3 0.0.0.0 area 0
 network 10.0.123.0 0.0.0.255 area 0
 network 10.2.35.0 0.0.0.3 area 0
```
</details>

<details>
<summary>Click to view R4 Configuration</summary>

```bash
! R4
router ospf 1
 router-id 4.4.4.4
 network 4.4.4.4 0.0.0.0 area 0
 network 10.1.24.0 0.0.0.3 area 0
 network 192.168.1.0 0.0.0.255 area 0
```
</details>

<details>
<summary>Click to view R5 Configuration</summary>

```bash
! R5
router ospf 1
 router-id 5.5.5.5
 network 5.5.5.5 0.0.0.0 area 0
 network 10.2.35.0 0.0.0.3 area 0
 network 192.168.2.0 0.0.0.255 area 0
```
</details>

### Task 5: Passive Interfaces

<details>
<summary>Click to view Passive Interface Configuration</summary>

```bash
! R4
router ospf 1
 passive-interface GigabitEthernet0/2

! R5
router ospf 1
 passive-interface GigabitEthernet0/1
```
</details>

### Task 8: Hello/Dead Timer Adjustment

<details>
<summary>Click to view Timer Configuration</summary>

```bash
! R2
interface GigabitEthernet0/1
 ip ospf hello-interval 5
 ip ospf dead-interval 20

! R4
interface GigabitEthernet0/0
 ip ospf hello-interval 5
 ip ospf dead-interval 20
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
! Verify OSPF neighbors
show ip ospf neighbor

! Verify LSDB
show ip ospf database

! Verify routes
show ip route ospf

! Verify interface OSPF state
show ip ospf interface brief

! End-to-end ping
! From PC1: ping 192.168.2.10
! From PC1: trace 192.168.2.10
```
</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. Inject the fault first, then
diagnose and fix using only show commands.

### Workflow

```bash
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>     # reset to known-good
python3 scripts/fault-injection/inject_scenario_NN.py --host <eve-ng-ip> # break
# diagnose + fix using show commands only
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>     # restore
```

Inject scripts run a **pre-flight check** -- they refuse to inject if the
target device isn't in the expected solution state. Always restore with
`apply_solution.py` between tickets.

---

### Ticket 1 — R4 Has No OSPF Neighbors

After a maintenance window, R4 reports zero OSPF neighbors. All interfaces show up/up and
IP connectivity between R2 and R4 works (ping succeeds), but `show ip ospf neighbor` on R4
is empty.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>`

**Success criteria:** R4 shows R2 (4.4.4.4) as a FULL neighbor, and PC1 can ping PC2.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. On R4: `show ip ospf neighbor` — empty.
2. On R4: `ping 10.1.24.1` — succeeds (L3 connectivity to R2 is fine).
3. On R4: `show ip ospf interface Gi0/0` — check hello/dead intervals.
4. On R2: `show ip ospf interface Gi0/1` — compare hello/dead intervals.
5. If timers differ between R2 and R4, that is the cause — OSPF requires matching hello/dead timers.
</details>

<details>
<summary>Click to view Fix</summary>

The fault is a hello/dead timer mismatch. R4's Gi0/0 was set to `ip ospf hello-interval 15`
(dead 60) while R2's Gi0/1 remains at the default 10/40.

```bash
! R4
interface GigabitEthernet0/0
 ip ospf hello-interval 5
 ip ospf dead-interval 20

! R2 (match R4)
interface GigabitEthernet0/1
 ip ospf hello-interval 5
 ip ospf dead-interval 20
```

Or restore defaults on R4:
```bash
! R4
interface GigabitEthernet0/0
 no ip ospf hello-interval
 no ip ospf dead-interval
```

Verify: `show ip ospf neighbor` on R4 should show R2 in FULL state.
</details>

---

### Ticket 2 — PC1 Can Reach R4 But Cannot Ping Any Remote Network

PC1 reports it can ping its gateway (192.168.1.1) but cannot reach PC2, R1, or any other
router beyond R4. R4 itself can ping R2 (10.1.24.1) successfully.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py --host <eve-ng-ip>`

**Success criteria:** PC1 can ping PC2 (192.168.2.10) and R1's loopback (1.1.1.1).

<details>
<summary>Click to view Diagnosis Steps</summary>

1. From PC1: `ping 192.168.1.1` — succeeds (gateway reachable).
2. From PC1: `ping 10.1.24.1` — fails (R2 not reachable from PC1).
3. On R4: `show ip route ospf` — check if OSPF routes are present.
4. On R4: `show ip ospf interface brief` — is Gi0/2 (PC1 LAN) listed?
5. If 192.168.1.0/24 is not in OSPF: R4 has the route as connected but is not advertising it. Other routers don't know how to reach 192.168.1.0/24, so return traffic fails.
6. On R2: `show ip route 192.168.1.0` — if missing, confirms the network isn't being advertised by R4.
</details>

<details>
<summary>Click to view Fix</summary>

The fault is a missing network statement on R4. The `network 192.168.1.0 0.0.0.255 area 0`
statement was removed, so R4 is not advertising the PC1 LAN subnet into OSPF. R4 can reach
R2 (its OSPF neighbor) but other routers have no route back to 192.168.1.0/24.

```bash
! R4
router ospf 1
 network 192.168.1.0 0.0.0.255 area 0
```

Verify: `show ip route ospf` on R1 should show `O 192.168.1.0/24`. PC1 can now ping PC2.
</details>

---

### Ticket 3 — R3 and R5 Cannot Form an OSPF Adjacency

The monitoring system alerts that R3 and R5 are no longer OSPF neighbors. R3's `show ip ospf
neighbor` does not list R5. Both interfaces show up/up. The rest of the OSPF domain (R1, R2,
R4) functions normally.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py --host <eve-ng-ip>`

**Success criteria:** R3 shows R5 as a FULL neighbor and PC2 is reachable from PC1.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. On R3: `show ip ospf neighbor` — R5 is missing.
2. On R3: `ping 10.2.35.2` — succeeds (L3 is fine).
3. On R3: `show ip ospf interface Gi0/1` — check if the interface is in OSPF and not passive.
4. If it shows "No Hellos (Passive interface)" — R3's transit link to R5 was made passive, blocking adjacency.
5. On R5: `show ip ospf interface Gi0/0` — R5 side is fine, but R3 never sends hellos.
</details>

<details>
<summary>Click to view Fix</summary>

The fault is `passive-interface GigabitEthernet0/1` on R3. This prevents R3 from sending
OSPF hellos to R5, which kills the adjacency. Passive-interface should only be used on
end-host LAN segments, never on transit links.

```bash
! R3
router ospf 1
 no passive-interface GigabitEthernet0/1
```

Verify: `show ip ospf neighbor` on R3 should show R5 (5.5.5.5) in FULL state within ~40 seconds.
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] OSPF process 1 enabled with explicit router-ID on all 5 routers
- [ ] All connected networks advertised into Area 0
- [ ] R1, R2, R3 form adjacencies on the broadcast segment (DR/BDR elected)
- [ ] R2-R4 and R3-R5 form point-to-point adjacencies
- [ ] LSDB contains 5 Type 1 Router LSAs and 1 Type 2 Network LSA
- [ ] Passive-interface configured on R4 Gi0/2 and R5 Gi0/1
- [ ] PC1 can ping PC2 across the OSPF domain
- [ ] All routes show as "O" (intra-area) — no "O IA"
- [ ] Hello/dead timers adjusted to 5/20 on R2-R4 link

### Troubleshooting

- [ ] Ticket 1 — Diagnosed and fixed hello/dead timer mismatch
- [ ] Ticket 2 — Diagnosed and fixed missing network statement
- [ ] Ticket 3 — Diagnosed and fixed passive-interface on transit link
