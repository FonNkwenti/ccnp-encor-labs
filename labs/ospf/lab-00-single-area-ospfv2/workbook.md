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

**Exam Objective:** 3.2.a / 3.2.b — Configure and verify simple OSPFv2 environments (single-area, neighbor adjacency, LSA types)

OSPF is a link-state IGP that floods topology information (LSAs) inside each area so every
router can independently run the SPF (Dijkstra) algorithm and build a loop-free tree to every
destination. This lab introduces the protocol in its simplest form — one area, one process,
five routers — so you can observe the three state machines that every OSPF deployment
depends on: the neighbor adjacency FSM, the LSDB (link-state database), and the SPF
calculation that populates the routing table.

### The OSPF Process and Router-ID

Every OSPF router runs one or more OSPF processes. A process is identified locally by a
process ID (1-65535) which has no meaning on the wire — two routers can run OSPF with
different process IDs and still become neighbors. What matters is the router-ID, a 32-bit
value that uniquely identifies the router inside the OSPF domain. It is selected in this
order:

1. An explicit `router-id A.B.C.D` under the OSPF process (preferred — deterministic)
2. Highest IP on any up/up Loopback interface
3. Highest IP on any up/up physical interface

Once chosen, the router-ID is locked until the OSPF process is cleared (`clear ip ospf process`)
or the router reboots. A duplicate router-ID between two neighbors prevents adjacency.

```
! OSPF process and explicit router-ID
router ospf <process-id>
 router-id <A.B.C.D>
```

> **Exam tip:** Always configure `router-id` explicitly. Leaving it dynamic means a
> loopback added later can silently change it and drop every adjacency the router has.

### Advertising Networks with `network` Statements

The `network` statement under `router ospf` does two things at once:

1. It enables OSPF on every interface whose primary IP matches the `network / wildcard` pair.
2. It places that interface into the specified area.

A wildcard mask of `0.0.0.0` matches exactly one IP and is the most surgical form — useful
for loopbacks. `0.0.0.3` matches a /30 point-to-point. `0.0.0.255` matches a /24 LAN.
The area ID can be decimal (`area 0`) or dotted-decimal (`area 0.0.0.0`) — both are accepted.

```
! network <address> <wildcard> area <area-id>
router ospf 1
 network 10.0.123.0 0.0.0.255 area 0    ! enables OSPF on all Gi0/0 /24 interfaces
 network 1.1.1.1 0.0.0.0 area 0         ! enables OSPF on Loopback0 (exact match)
```

An interface enabled by a `network` statement sends and receives OSPF Hellos, forms
adjacencies, and floods LSAs. `passive-interface` shuts off Hellos on a selected interface
while still advertising its subnet into the LSDB — perfect for LAN segments facing end hosts
or servers.

### Neighbor Adjacency States

Two OSPF routers transition through a series of states before exchanging LSAs:

| State | Meaning |
|-------|---------|
| `DOWN` | No Hellos received from this neighbor |
| `INIT` | Hello received, but local router-ID not listed in the neighbor's Hello |
| `2-WAY` | Bidirectional Hello — both routers see each other. On a broadcast segment, DROTHERs stay here permanently. |
| `EXSTART` | Master/slave election for DBD (Database Description) exchange |
| `EXCHANGE` | DBD packets summarize the LSDB |
| `LOADING` | Missing LSAs requested via LSRs, answered with LSUs |
| `FULL` | LSDBs are synchronized — adjacency is complete |

For adjacency to form, both ends must agree on: area ID, subnet mask, hello/dead intervals,
authentication, and MTU. A mismatch on any of these parks the adjacency at or below
`EXSTART` and leaves the routers unable to exchange LSAs.

### Hello and Dead Timers

OSPF Hellos are unicast to multicast `224.0.0.5` (AllSPFRouters). On broadcast and
point-to-point networks the default `hello-interval` is 10 seconds and the `dead-interval`
is 4× hello = 40 seconds. Both ends MUST agree; a mismatch prevents adjacency.

Tuning these down (e.g. hello=5, dead=20) speeds up dead-neighbor detection and convergence
at the cost of more control-plane traffic. Values can be set per-interface — only the two
routers on that link need to agree; other adjacencies on the same router keep their own timers.

```
! Per-interface timer tuning
interface GigabitEthernet0/1
 ip ospf hello-interval 5
 ip ospf dead-interval 20
```

### DR/BDR Election on Broadcast Segments

On a shared Ethernet segment with more than two OSPF speakers, flooding every LSA to every
neighbor would scale quadratically. OSPF solves this by electing a Designated Router (DR)
and Backup Designated Router (BDR). DROTHERs form a FULL adjacency only with the DR and BDR;
among themselves they stay at `2-WAY`.

Election rules (evaluated in order):

1. Highest OSPF interface priority (default = 1, range 0-255). Priority `0` disqualifies.
2. Highest router-ID as tiebreaker.

The election is **non-preemptive** — once elected, a DR holds the role until it fails or
the OSPF process is cleared, even if a higher-priority router joins later. In this lab,
defaults are used everywhere, so the tiebreaker (router-ID) decides: R3 (3.3.3.3) wins DR,
R2 (2.2.2.2) BDR, R1 (1.1.1.1) DROTHER.

### LSA Types 1 and 2

In a single-area design only two LSA types matter:

| Type | Name | Purpose |
|------|------|---------|
| 1 | Router LSA | Every router advertises its own interfaces, states, and costs |
| 2 | Network LSA | Generated by the DR only, lists all routers attached to the broadcast segment |

Inter-area (Type 3), ASBR-summary (Type 4), and external (Type 5/7) LSAs appear in later
labs. In Section 6 you will view a Type-1 entry per router and a single Type-2 for the
SW-AREA0 segment originated by R3 (the DR).

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| OSPF process configuration | Start `router ospf N`, set an explicit router-ID, enable OSPF on interfaces via `network` statements in area 0 |
| Neighbor verification | Read `show ip ospf neighbor` — interpret state, priority, DR/BDR roles |
| LSDB inspection | Use `show ip ospf database` to see Type 1 (Router) and Type 2 (Network) LSAs |
| Routing table analysis | Identify intra-area routes (`O`) and their metric/next-hop via `show ip route ospf` |
| Passive-interface | Suppress Hellos on LAN-facing interfaces while still advertising the prefix |
| Timer tuning | Adjust `ip ospf hello-interval` / `dead-interval` and confirm both ends match |
| DR/BDR observation | Use `show ip ospf interface` to confirm elected roles on the shared segment |
| End-to-end reachability | Verify PC1 ↔ PC2 across five routers via `ping` and `traceroute` |

---

## 2. Topology & Scenario

**Scenario:** Acme Engineering is standing up a lab network for a new OSPF rollout. Three
core routers (R1, R2, R3) sit on a shared Layer 2 segment (the "core fabric"), while two
edge routers (R4, R5) terminate user subnets at remote sites. All five routers must run a
single OSPFv2 process in a single area so routes to PC1 (site A) and PC2 (site B) are
reachable from every device. The design team wants aggressive convergence on the R2↔R4
link to validate fast reconvergence on the eventual production path, so that link will
run hello=5 / dead=20.

```
                      ┌─────────────────────┐
                      │         R1          │
                      │  (Area 0 backbone)  │
                      │   Lo0: 1.1.1.1/32   │
                      └─────────┬───────────┘
                           Gi0/0│
                       10.0.123.1/24
                                │
                    ┌───────────┴───────────┐
                    │       SW-AREA0        │
                    │  (unmanaged switch)   │
                    │   10.0.123.0/24       │
                    └──┬─────────────────┬──┘
                       │                 │
                 10.0.123.2/24     10.0.123.3/24
                       │Gi0/0            │Gi0/0
              ┌────────┴────────┐  ┌─────┴────────────┐
              │       R2        │  │        R3        │
              │  (Area 0 core)  │  │  (Area 0 core)   │
              │ Lo0: 2.2.2.2/32 │  │ Lo0: 3.3.3.3/32  │
              └────────┬────────┘  └─────┬────────────┘
                 Gi0/1 │                 │ Gi0/1
             10.1.24.1/30           10.2.35.1/30
                       │                 │
             10.1.24.2/30           10.2.35.2/30
                 Gi0/0 │                 │ Gi0/0
              ┌────────┴────────┐  ┌─────┴────────────┐
              │       R4        │  │        R5        │
              │  (Area 0 edge)  │  │  (Area 0 edge)   │
              │ Lo0: 4.4.4.4/32 │  │ Lo0: 5.5.5.5/32  │
              └────────┬────────┘  └─────┬────────────┘
                 Gi0/2 │                 │ Gi0/1
             192.168.1.1/24         192.168.2.1/24
                       │                 │
                 ┌─────┴─────┐      ┌────┴─────┐
                 │    PC1    │      │   PC2    │
                 │ .1.10/24  │      │ .2.10/24 │
                 └───────────┘      └──────────┘
```

---

## 3. Hardware & Environment Specifications

### Device Summary

| Device | Platform | Role | Loopback0 |
|--------|----------|------|-----------|
| R1 | IOSv | Area 0 backbone (shared segment only) | 1.1.1.1/32 |
| R2 | IOSv | Area 0 core (shared segment + R4 uplink, tuned timers) | 2.2.2.2/32 |
| R3 | IOSv | Area 0 core (shared segment + R5 uplink) — wins DR | 3.3.3.3/32 |
| R4 | IOSv | Area 0 edge (uplink to R2 + PC1 LAN) | 4.4.4.4/32 |
| R5 | IOSv | Area 0 edge (uplink to R3 + PC2 LAN) | 5.5.5.5/32 |
| SW-AREA0 | Unmanaged switch | Shared L2 broadcast segment for R1/R2/R3 | — |
| PC1 | VPC | End host on Area 0 LAN (site A) | 192.168.1.10/24 gw .1.1 |
| PC2 | VPC | End host on Area 0 LAN (site B) | 192.168.2.10/24 gw .2.1 |

### Cabling Table

| Link ID | Source | Destination | Subnet | Purpose |
|---------|--------|-------------|--------|---------|
| L1 | R1 Gi0/0 | SW-AREA0 port1 | 10.0.123.0/24 | Shared Area 0 segment |
| L2 | R2 Gi0/0 | SW-AREA0 port2 | 10.0.123.0/24 | Shared Area 0 segment |
| L3 | R3 Gi0/0 | SW-AREA0 port3 | 10.0.123.0/24 | Shared Area 0 segment |
| L4 | R2 Gi0/1 | R4 Gi0/0 | 10.1.24.0/30 | Point-to-point (tuned timers) |
| L5 | R3 Gi0/1 | R5 Gi0/0 | 10.2.35.0/30 | Point-to-point |
| L6 | R4 Gi0/2 | PC1 e0 | 192.168.1.0/24 | PC1 LAN (passive) |
| L7 | R5 Gi0/1 | PC2 e0 | 192.168.2.0/24 | PC2 LAN (passive) |

### Console Access Table

| Device | Port | Connection Command |
|--------|------|--------------------|
| R1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R3 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R4 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R5 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| PC1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| PC2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |

> Ports are dynamically assigned by EVE-NG. Check the EVE-NG web UI node properties, or
> run `python3 setup_lab.py --host <eve-ng-ip>` to push initial configs automatically.

---

## 4. Base Configuration

The following configuration is already loaded by `setup_lab.py` (from `initial-configs/`):

**Pre-loaded on every router:**
- Hostname and `no ip domain-lookup`
- Loopback0 addressed to the router-ID IP (1.1.1.1, 2.2.2.2, ...)
- All lab-scope physical interfaces IP-addressed, described, and `no shutdown`
- `line vty 0 4` with `login` / `transport input telnet` for Netmiko reachability

**Pre-loaded on PC1 / PC2:**
- VPC IP and default gateway

**NOT pre-configured — the student configures these in this lab:**
- OSPF routing process
- Explicit OSPF router-ID
- Network statements placing each interface into area 0
- Passive-interface on PC-facing LAN interfaces
- Hello/dead timer tuning on the R2 ↔ R4 link

---

## 5. Lab Challenge: Core Implementation

> Work through each task in order. Verify each task before moving to the next.
> Consult Section 8 only if you are stuck after 10 minutes on a task.

---

### Task 1: Enable OSPFv2 with Explicit Router-IDs

- On every router (R1-R5), start OSPF process 1 and set an explicit router-ID that matches
  the router's Loopback0 address (R1 = 1.1.1.1, R2 = 2.2.2.2, and so on).

**Verification:** `show ip protocols` must list `Routing Protocol is "ospf 1"` and
`Router ID <expected>` on each router. A dynamic router-ID selection warning must NOT be present.

---

### Task 2: Advertise All Connected Networks into Area 0

- On each router, advertise every directly connected lab subnet — the Loopback0 /32,
  all connected transit links, and the PC LAN on R4/R5 — into area 0 using `network`
  statements with the correct wildcard masks.
- Use a `0.0.0.0` wildcard for loopbacks, `0.0.0.3` for /30 transit links, and `0.0.0.255`
  for /24 LANs.

**Verification:** `show ip ospf interface brief` on each router must list every active
interface with `Area 0` and a valid cost. No lab interface should be missing.

---

### Task 3: Suppress Hellos on PC-Facing LAN Interfaces

- Prevent OSPF Hellos from being sent toward PC1 and PC2 while still advertising the
  192.168.1.0/24 and 192.168.2.0/24 prefixes into OSPF.
- On R4, make Gi0/2 passive. On R5, make Gi0/1 passive.

**Verification:** `show ip ospf interface GigabitEthernet0/2` on R4 must report
`Passive interface`. The interface must still appear in `show ip ospf interface brief`
with a valid cost, confirming the prefix is still advertised.

---

### Task 4: Tune Hello and Dead Timers on the R2 ↔ R4 Link

- Configure hello-interval = 5 and dead-interval = 20 on R2 Gi0/1 AND R4 Gi0/0.
- Both ends must match. No other adjacencies should be affected.

**Verification:** `show ip ospf interface GigabitEthernet0/1` on R2 must show
`Hello 5, Dead 20`. The R2 ↔ R4 adjacency must remain FULL after the change.

---

### Task 5: Confirm Neighbor Adjacencies Across the Topology

- Verify that every router has reached the `FULL` state with each of its direct OSPF
  neighbors.
- On the shared segment (SW-AREA0), confirm that R3 is DR, R2 is BDR, and R1 is DROTHER
  (R1 will show `FULL/DR` and `FULL/BDR` neighbors but `2-WAY/DROTHER` is not expected
  here because there are only three routers — R1 becomes FULL with both R2 and R3).

**Verification:** `show ip ospf neighbor` on R1 must list two neighbors both in `FULL`
state — R2 as BDR, R3 as DR. Every router must show at least one `FULL` neighbor.

---

### Task 6: Inspect the LSDB for Type 1 and Type 2 LSAs

- View the link-state database on any Area 0 router.
- Identify exactly five Type-1 (Router) LSAs — one per router — and one Type-2 (Network) LSA
  advertised by the DR for the shared 10.0.123.0/24 segment.

**Verification:** `show ip ospf database` must list five Router LSAs (advertising
router-IDs 1.1.1.1 through 5.5.5.5) and one Net LSA with `Link ID 10.0.123.3`
(the DR's interface IP on the shared segment) advertised by 3.3.3.3.

---

### Task 7: Verify Intra-Area Routes in the Routing Table

- On R1, confirm that every /32 loopback and every transit/LAN subnet learned from OSPF is
  installed in the IPv4 RIB with administrative distance 110 and the expected next-hop.

**Verification:** `show ip route ospf` on R1 must list each remote loopback (2.2.2.2/32,
3.3.3.3/32, 4.4.4.4/32, 5.5.5.5/32) as `O`, plus the two /30 transit subnets and
both PC LAN /24s. All entries show `[110/...]`.

---

### Task 8: End-to-End Reachability from PC1 to PC2

- From PC1, ping PC2's IP (192.168.2.10). Traffic must cross R4 → R2 → R3 → R5 via OSPF.
- Confirm the return path is symmetric with a traceroute from PC1 to PC2.

**Verification:** `ping 192.168.2.10` from PC1 must succeed with 5/5 replies.
`trace 192.168.2.10` from PC1 must show four transit hops (R4 LAN, R2 P2P, R3 shared,
R5 P2P) before reaching PC2.

---

## 6. Verification & Analysis

### Task 1 — OSPF Process & Router-ID

```
R1# show ip protocols | section ospf
Routing Protocol is "ospf 1"
  Outgoing update filter list for all interfaces is not set
  Incoming update filter list for all interfaces is not set
  Router ID 1.1.1.1                        ! ← must match Loopback0, explicitly configured
  Number of areas in this router is 1. 1 normal 0 stub 0 nssa
  Maximum path: 4
  Routing for Networks:
    1.1.1.1 0.0.0.0 area 0                 ! ← loopback advertised
    10.0.123.0 0.0.0.255 area 0            ! ← shared segment advertised
```

### Task 2 — Interfaces Enabled in Area 0

```
R4# show ip ospf interface brief
Interface    PID   Area            IP Address/Mask    Cost  State Nbrs F/C
Lo0          1     0               4.4.4.4/32         1     LOOP  0/0    ! ← loopback in area 0
Gi0/0        1     0               10.1.24.2/30       1     P2P   1/1    ! ← R2 adjacency counted
Gi0/2        1     0               192.168.1.1/24     1     DR    0/0    ! ← PC LAN, passive (no neighbors)
```

### Task 3 — Passive-Interface on PC LAN

```
R4# show ip ospf interface GigabitEthernet0/2
GigabitEthernet0/2 is up, line protocol is up
  Internet Address 192.168.1.1/24, Area 0, Attached via Network Statement
  ...
  Hello due in never                                  ! ← passive — no hellos sent
  No Hellos (Passive interface)                       ! ← confirms passive state
  ...
  Suppress hello for 0 neighbor(s)
```

### Task 4 — Timer Tuning on R2 ↔ R4

```
R2# show ip ospf interface GigabitEthernet0/1
GigabitEthernet0/1 is up, line protocol is up
  Internet Address 10.1.24.1/30, Area 0, Attached via Network Statement
  Process ID 1, Router ID 2.2.2.2, Network Type POINT_TO_POINT, Cost: 1
  ...
  Timer intervals configured, Hello 5, Dead 20, Wait 20, Retransmit 5    ! ← tuned values
  ...
  Neighbor Count is 1, Adjacent neighbor count is 1
    Adjacent with neighbor 4.4.4.4                     ! ← FULL with R4 after retune
```

### Task 5 — Neighbor Adjacencies (R1 perspective)

```
R1# show ip ospf neighbor

Neighbor ID     Pri   State           Dead Time   Address         Interface
2.2.2.2           1   FULL/BDR        00:00:36    10.0.123.2      GigabitEthernet0/0   ! ← R2 = BDR
3.3.3.3           1   FULL/DR         00:00:34    10.0.123.3      GigabitEthernet0/0   ! ← R3 = DR
```

### Task 5 — DR/BDR Election (R3 perspective)

```
R3# show ip ospf interface GigabitEthernet0/0 | include Designated|Priority
  Designated Router (ID) 3.3.3.3, Interface address 10.0.123.3    ! ← R3 won DR
  Backup Designated router (ID) 2.2.2.2, Interface address 10.0.123.2  ! ← R2 is BDR
  Router Priority is 1 (default)                                   ! ← tiebreaker was router-ID
```

### Task 6 — LSDB Content

```
R1# show ip ospf database

            OSPF Router with ID (1.1.1.1) (Process ID 1)

                Router Link States (Area 0)

Link ID         ADV Router      Age  Seq#        Checksum Link count
1.1.1.1         1.1.1.1         120  0x80000005  0x00ABCD  2          ! ← R1's Type-1
2.2.2.2         2.2.2.2         115  0x80000006  0x00EF12  3          ! ← R2's Type-1 (shared + P2P + lo)
3.3.3.3         3.3.3.3         110  0x80000005  0x003456  3          ! ← R3's Type-1
4.4.4.4         4.4.4.4         100  0x80000004  0x007890  3          ! ← R4 reached via R2
5.5.5.5         5.5.5.5         100  0x80000004  0x00ABAB  3          ! ← R5 reached via R3

                Net Link States (Area 0)

Link ID         ADV Router      Age  Seq#        Checksum
10.0.123.3      3.3.3.3         110  0x80000001  0x00CDEF            ! ← Type-2 from DR (R3)
```

### Task 7 — OSPF Routes on R1

```
R1# show ip route ospf | include ^O
O        2.2.2.2/32 [110/2] via 10.0.123.2, 00:05:12, GigabitEthernet0/0    ! ← R2 loopback
O        3.3.3.3/32 [110/2] via 10.0.123.3, 00:05:12, GigabitEthernet0/0    ! ← R3 loopback
O        4.4.4.4/32 [110/3] via 10.0.123.2, 00:05:08, GigabitEthernet0/0    ! ← R4 via R2
O        5.5.5.5/32 [110/3] via 10.0.123.3, 00:05:06, GigabitEthernet0/0    ! ← R5 via R3
O        10.1.24.0/30 [110/2] via 10.0.123.2, 00:05:12, GigabitEthernet0/0  ! ← R2-R4 transit
O        10.2.35.0/30 [110/2] via 10.0.123.3, 00:05:12, GigabitEthernet0/0  ! ← R3-R5 transit
O        192.168.1.0/24 [110/3] via 10.0.123.2, 00:05:08, GigabitEthernet0/0 ! ← PC1 LAN via R2
O        192.168.2.0/24 [110/3] via 10.0.123.3, 00:05:06, GigabitEthernet0/0 ! ← PC2 LAN via R3
```

### Task 8 — End-to-End Reachability

```
PC1> ping 192.168.2.10

84 bytes from 192.168.2.10 icmp_seq=1 ttl=60 time=4.123 ms    ! ← ttl=60 → 4 IP hops consumed
84 bytes from 192.168.2.10 icmp_seq=2 ttl=60 time=3.891 ms
84 bytes from 192.168.2.10 icmp_seq=3 ttl=60 time=4.002 ms

PC1> trace 192.168.2.10
trace to 192.168.2.10, 8 hops max, press Ctrl+C to stop
 1   192.168.1.1     1.123 ms   1.001 ms   0.998 ms    ! ← R4 LAN gateway
 2   10.1.24.1       2.110 ms   2.203 ms   2.150 ms    ! ← R2 on P2P
 3   10.0.123.3      2.905 ms   2.801 ms   2.889 ms    ! ← R3 on shared segment
 4   10.2.35.2       3.550 ms   3.512 ms   3.601 ms    ! ← R5 on P2P
 5   *192.168.2.10   3.912 ms (ICMP type:3, code:3, Destination port unreachable)   ! ← PC2
```

---

## 7. Verification Cheatsheet

### OSPF Process Configuration

```
router ospf <pid>
 router-id A.B.C.D
 network <addr> <wildcard> area <area-id>
 passive-interface <if-name>
```

| Command | Purpose |
|---------|---------|
| `router ospf <pid>` | Start OSPF process; `pid` is locally significant (1-65535) |
| `router-id A.B.C.D` | Fix the router-ID — prevents silent changes when loopbacks move |
| `network <addr> <wc> area <id>` | Enable OSPF on interfaces matching addr/wildcard; place into area |
| `passive-interface <if>` | Stop Hellos on this interface; prefix still advertised |
| `passive-interface default` | Make all interfaces passive; explicit `no passive-interface X` re-enables |

> **Exam tip:** A dynamic router-ID silently flips when a new loopback outranks the current
> one. Always pin it with `router-id` to avoid 3 a.m. paging.

### Interface Controls

```
interface <if>
 ip ospf hello-interval <sec>
 ip ospf dead-interval <sec>
 ip ospf priority <0-255>
 ip ospf cost <value>
```

| Command | Purpose |
|---------|---------|
| `ip ospf hello-interval <sec>` | Override default hello (10s broadcast/P2P, 30s NBMA) |
| `ip ospf dead-interval <sec>` | Override default dead (4× hello) — BOTH ends must match |
| `ip ospf priority <0-255>` | DR/BDR election weight; `0` = never elected (DROTHER forced) |
| `ip ospf cost <value>` | Per-interface metric override (default = `10^8 / bandwidth`) |

> **Exam tip:** Matching hello AND dead on both ends is required. Setting only one half
> hangs the adjacency at `INIT` or `EXSTART`.

### Verification Commands

| Command | What to Look For |
|---------|-----------------|
| `show ip ospf` | Router-ID, area count, SPF timers, LSAs in each area |
| `show ip ospf neighbor` | Neighbor ID, state (FULL/2-WAY), role (DR/BDR/DROTHER), dead time |
| `show ip ospf interface brief` | Every OSPF interface, area, cost, network type, neighbor count |
| `show ip ospf interface <if>` | Detailed: network type, DR/BDR, hello/dead, passive flag |
| `show ip ospf database` | LSDB contents — Type-1 per router, Type-2 per broadcast segment |
| `show ip ospf database router <rid>` | Dump a specific router's Type-1 link records |
| `show ip route ospf` | Intra-area (`O`) routes with metric and next-hop |
| `show ip protocols` | Routing process summary including networks and passive list |

### Wildcard Mask Quick Reference

| Subnet Mask | Wildcard Mask | Common Use |
|-------------|---------------|------------|
| 255.255.255.255 | 0.0.0.0 | Exact /32 match (loopbacks) |
| 255.255.255.252 | 0.0.0.3 | /30 point-to-point |
| 255.255.255.0 | 0.0.0.255 | /24 LAN |
| 255.255.0.0 | 0.0.255.255 | /16 aggregate |

### Common OSPF Adjacency Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| Neighbor stuck in `INIT` | Hello received but local router-ID not in neighbor's list — one-way hello (filter? ACL?) |
| Neighbor stuck in `EXSTART` / `EXCHANGE` | MTU mismatch on the segment |
| No neighbor at all | Hello/dead mismatch, area mismatch, subnet mask mismatch, or `passive-interface` on the wrong side |
| Adjacency flaps | Dead-interval too close to hello-interval, or flaky link dropping Hellos |
| FULL but route missing | `network` statement not covering the advertising interface, or `passive` on the wrong side |
| Duplicate router-ID warning | Two routers sharing the same router-ID — election cannot complete |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Task 1-2: Enable OSPFv2 and Advertise Networks

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1 — Area 0 backbone (shared segment only)
router ospf 1
 router-id 1.1.1.1
 network 1.1.1.1 0.0.0.0 area 0
 network 10.0.123.0 0.0.0.255 area 0
```
</details>

<details>
<summary>Click to view R2 Configuration</summary>

```bash
! R2 — Area 0 core (shared segment + R4 uplink)
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
! R3 — Area 0 core (shared segment + R5 uplink) — will win DR
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
! R4 — Area 0 edge (uplink to R2 + PC1 LAN)
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
! R5 — Area 0 edge (uplink to R3 + PC2 LAN)
router ospf 1
 router-id 5.5.5.5
 network 5.5.5.5 0.0.0.0 area 0
 network 10.2.35.0 0.0.0.3 area 0
 network 192.168.2.0 0.0.0.255 area 0
```
</details>

---

### Task 3: Suppress Hellos on PC-Facing LAN Interfaces

<details>
<summary>Click to view R4 Configuration</summary>

```bash
router ospf 1
 passive-interface GigabitEthernet0/2
```
</details>

<details>
<summary>Click to view R5 Configuration</summary>

```bash
router ospf 1
 passive-interface GigabitEthernet0/1
```
</details>

---

### Task 4: Tune Hello and Dead Timers on R2 ↔ R4

<details>
<summary>Click to view R2 Configuration</summary>

```bash
interface GigabitEthernet0/1
 ip ospf hello-interval 5
 ip ospf dead-interval 20
```
</details>

<details>
<summary>Click to view R4 Configuration</summary>

```bash
interface GigabitEthernet0/0
 ip ospf hello-interval 5
 ip ospf dead-interval 20
```
</details>

---

### Tasks 5-8: Verification

<details>
<summary>Click to view Verification Commands</summary>

```bash
! Neighbor adjacencies
show ip ospf neighbor
show ip ospf neighbor detail

! DR/BDR and interface state
show ip ospf interface brief
show ip ospf interface GigabitEthernet0/0

! LSDB inspection
show ip ospf database
show ip ospf database router
show ip ospf database network

! Routes and end-to-end
show ip route ospf
show ip protocols | section ospf

! From PCs
ping 192.168.2.10       ! PC1 -> PC2
trace 192.168.2.10
```
</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. Inject the fault first, then diagnose and fix
using only `show` commands.

### Workflow

```bash
python3 setup_lab.py --host <eve-ng-ip>                                    # one-time initial-configs push
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>       # reset to known-good solution
python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>   # inject Ticket 1
# diagnose and fix using show commands
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>       # restore between tickets
```

> Note: `setup_lab.py` pushes the initial (bare-minimum) configs and is only used once,
> before you start Section 5. For troubleshooting, always reset with `apply_solution.py`,
> which pushes the full solution configs.

---

### Ticket 1 — R4 Cannot Reach R1's Loopback but R2's Works

The NOC reports that from R4, ping to R2's loopback (2.2.2.2) succeeds but ping to R1's
loopback (1.1.1.1) times out. R1's Gi0/0 is up/up and R1 shows FULL adjacency with R3
on the shared segment.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>`

**Success criteria:** From R4, `ping 1.1.1.1 source Loopback0` succeeds, and
`show ip route 1.1.1.1` on R4 returns an `O` entry.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! 1. Confirm the missing route on R4
R4# show ip route 1.1.1.1
! Expected: % Subnet not in table  (confirms the prefix isn't learned)

! 2. Is R1 even in R4's LSDB as a Router LSA?
R4# show ip ospf database | section 1.1.1.1
! If the Type-1 is missing, R1 is unreachable from R4's area perspective

! 3. Walk back toward R1 — check R2's neighbors on the shared segment
R2# show ip ospf neighbor
! If R1 is missing here, R2 is not adjacent with R1 on the shared segment

! 4. Is R2's Gi0/0 participating in OSPF?
R2# show ip ospf interface brief
! Look for GigabitEthernet0/0 entry — if missing, the network statement is wrong

! 5. Dump R2's network statements
R2# show running-config | section router ospf
! Compare against the solution — expect `network 10.0.123.0 0.0.0.255 area 0`
```
</details>

<details>
<summary>Click to view Fix</summary>

The fault is a missing `network` statement on R2: `network 10.0.123.0 0.0.0.255 area 0`
was removed, so R2 never forms an adjacency with R1 on the shared segment. R3 still sees
R1 and R2 independently, but because R2 no longer floods or relays on the shared segment,
R1's Router LSA never propagates to the R2 ↔ R4 area.

```bash
R2(config)# router ospf 1
R2(config-router)# network 10.0.123.0 0.0.0.255 area 0

! Verify
R2# show ip ospf neighbor                 ! R1 must reappear as FULL/DR or FULL/DROTHER
R4# show ip route 1.1.1.1                 ! O route via 10.1.24.1
R4# ping 1.1.1.1 source Loopback0         ! 5/5 success
```
</details>

---

### Ticket 2 — No Adjacency Forms Between R4 and R2

After a recent maintenance window, R4 and R2 are no longer exchanging OSPF LSAs. `show ip ospf
neighbor` on R4 shows no entry for R2. The physical link is up/up on both ends and pings
across the /30 succeed.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py --host <eve-ng-ip>`

**Success criteria:** `show ip ospf neighbor` on both R2 and R4 lists the peer in `FULL`
state. R4 relearns all Area 0 prefixes via R2.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! 1. Confirm the adjacency is truly missing
R4# show ip ospf neighbor
! No entry for 2.2.2.2

! 2. Physical link is fine — so suspect a protocol mismatch
R4# ping 10.1.24.1                      ! IP reachability on the transit link
! Should succeed

! 3. Check both sides' OSPF interface parameters
R4# show ip ospf interface GigabitEthernet0/0
R2# show ip ospf interface GigabitEthernet0/1
! Compare: Hello, Dead, Area, Network Type, Authentication

! 4. If one side shows Hello 10 / Dead 40 and the other shows Hello 5 / Dead 20 — timer mismatch

! 5. Check debug briefly if console-capable
R4# debug ip ospf hello
! R4 logs: "Mismatched hello parameters from 10.1.24.1"
R4# undebug all
```
</details>

<details>
<summary>Click to view Fix</summary>

The fault is a hello/dead timer mismatch: R4 Gi0/0 was reverted to defaults (hello=10, dead=40)
while R2 Gi0/1 is still configured with hello=5, dead=20. OSPF requires both to match.

```bash
R4(config)# interface GigabitEthernet0/0
R4(config-if)# ip ospf hello-interval 5
R4(config-if)# ip ospf dead-interval 20

! Verify
R4# show ip ospf interface GigabitEthernet0/0 | include Timer
!   Timer intervals configured, Hello 5, Dead 20, Wait 20, Retransmit 5
R4# show ip ospf neighbor
!   2.2.2.2  1  FULL/  -   00:00:18  10.1.24.1  GigabitEthernet0/0
```
</details>

---

### Ticket 3 — PC1 Cannot Reach PC2 Even Though Neighbors Are Healthy

All OSPF neighbors are FULL across the topology. R4 can ping R5 loopbacks and R5 can ping
R4 loopbacks. But PC1 (192.168.1.10) cannot reach PC2 (192.168.2.10) — every ping times out.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py --host <eve-ng-ip>`

**Success criteria:** PC1 can ping PC2 (192.168.2.10) with 5/5 success. `show ip route
192.168.2.0` on R4 returns an `O` entry.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! 1. Which leg of the path is missing?
PC1> ping 192.168.2.1     ! R5 LAN gateway
! Fails — so return path from R5 or the forward path is broken

! 2. Does R4 even have a route to 192.168.2.0/24?
R4# show ip route 192.168.2.0
! Expected: O 192.168.2.0/24 [110/4] via 10.1.24.1   (if missing, LSDB is incomplete)

! 3. Search LSDB for the prefix
R4# show ip ospf database | include 192.168.2
! If no match — no router is advertising 192.168.2.0 into Area 0

! 4. R5 should own that prefix. Check R5's OSPF config and interface participation
R5# show ip ospf interface brief
! GigabitEthernet0/1 should be Area 0 with cost 1
! If GigabitEthernet0/1 is missing from the list — the network statement is gone

R5# show running-config | section router ospf
! Expect `network 192.168.2.0 0.0.0.255 area 0`
```
</details>

<details>
<summary>Click to view Fix</summary>

The fault is a missing `network` statement on R5: `network 192.168.2.0 0.0.0.255 area 0`
was removed. R5 Gi0/1 still has the IP, but OSPF is not advertising the prefix, so R4 (and
the rest of Area 0) has no route back toward PC2.

```bash
R5(config)# router ospf 1
R5(config-router)# network 192.168.2.0 0.0.0.255 area 0
R5(config-router)# passive-interface GigabitEthernet0/1

! Verify
R5# show ip ospf interface brief              ! Gi0/1 now listed with cost 1
R4# show ip route 192.168.2.0                 ! O 192.168.2.0/24 [110/4]
```

Then test from PC1:

```bash
PC1> ping 192.168.2.10
! 5/5 success
```
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] `show ip ospf` on every router lists `Router ID <Loopback0 IP>` (explicitly configured)
- [ ] `show ip ospf interface brief` shows every lab interface in Area 0 with a valid cost
- [ ] R4 Gi0/2 and R5 Gi0/1 report `Passive interface` — no Hellos toward PCs
- [ ] R2 Gi0/1 and R4 Gi0/0 show `Hello 5, Dead 20` and the R2 ↔ R4 adjacency is FULL
- [ ] `show ip ospf neighbor` on R1 lists R2 as `FULL/BDR` and R3 as `FULL/DR`
- [ ] `show ip ospf database` lists five Type-1 Router LSAs and one Type-2 Net LSA from 3.3.3.3
- [ ] `show ip route ospf` on R1 contains all remote loopbacks (/32), both transit /30s, and both PC /24s
- [ ] PC1 can ping PC2 (192.168.2.10) with 5/5 success
- [ ] `trace 192.168.2.10` from PC1 shows four router hops before reaching PC2

### Troubleshooting

- [ ] Ticket 1 resolved: R2's shared-segment `network` statement restored — R4 learns 1.1.1.1/32
- [ ] Ticket 2 resolved: R4 Gi0/0 timers realigned with R2 — adjacency returns to FULL
- [ ] Ticket 3 resolved: R5's PC2 LAN `network` statement restored — PC1 ↔ PC2 connectivity works
