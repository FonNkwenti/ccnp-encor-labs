# OSPF Lab 04 — Inter-Area Summarization and Filtering

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

**Exam Objective:** 3.2.b — Configure simple OSPFv2/v3 environments, including multiple normal areas, summarization, and filtering

This lab focuses on controlling the size and content of OSPF routing tables through inter-area route summarization and prefix filtering. You will reduce the number of Type 3 LSAs crossing area boundaries by aggregating multiple specific prefixes into a single summary, suppress individual subnets using `area range not-advertise`, and filter route installation locally using distribute-lists. ASBR-level summarization further reduces the external LSA footprint. These techniques are foundational for scaling real enterprise OSPF deployments.

### Inter-Area Summarization (`area range`)

OSPF does not summarize routes automatically. An ABR (Area Border Router) must be explicitly configured to aggregate specific routes from one area before advertising them into another. The `area range` command on an ABR tells OSPF: "for any Type 1/2 LSA from area X that falls within this prefix, generate a single summary Type 3 LSA instead of individual Type 3 LSAs."

```
router ospf 1
 area 1 range 10.1.4.0 255.255.252.0
```

This single command on R2 replaces up to four individual Type 3 LSAs (10.1.4.0/24, 10.1.5.0/24, 10.1.6.0/24, 10.1.7.0/24) with one Type 3 LSA for 10.1.4.0/22. The `/22` covers all four `/24` networks:

| Summary | Covers |
|---------|--------|
| 10.1.4.0/22 | 10.1.4.0/24, 10.1.5.0/24, 10.1.6.0/24, 10.1.7.0/24 |

The cost of the summary is the **maximum cost** among all contributing specific routes. Individual `/24` LSAs are withdrawn from Area 0 — they only exist in the LSDB of Area 1 routers.

For OSPFv3 (IPv6 address-family), the equivalent is:
```
router ospfv3 1
 address-family ipv6 unicast
  area 1 range 2001:DB8:1:4::/62
```
The `/62` covers 2001:db8:1:4::/64 through 2001:db8:1:7::/64 (four /64 prefixes).

> **Key exam point:** `area range` is configured on the **ABR** for routes **sourced** from the specified area. R2 summarizes Area 1 routes going into Area 0 — NOT Area 0 routes going into Area 1.

### `area range not-advertise`

Adding `not-advertise` to an `area range` statement suppresses the prefix entirely — no summary Type 3 LSA is generated for it, and it is excluded from any enclosing summary range. Traffic to that subnet is unreachable from outside the area.

```
router ospf 1
 area 1 range 10.1.6.0 255.255.255.0 not-advertise
```

Use cases:
- Prevent a specific subnet from being visible outside its area (security, policy)
- Exclude a subnet from a summary when the summary would otherwise include it
- Test route reachability by selectively suppressing prefixes

> **Exam distinction:** `not-advertise` on a specific `/24` within a `/22` range: the `/22` summary is still advertised (since other contributing routes exist), but the specific `/24` is excluded from cost calculation and not individually advertised.

### ASBR Summarization (`summary-address`)

When an ASBR redistributes external routes into OSPF, it generates one Type 5 LSA (or Type 7 in NSSA) per external prefix by default. The `summary-address` command on the ASBR aggregates these external LSAs before they are flooded.

```
router ospf 1
 summary-address 172.16.0.0 255.255.0.0
```

This tells R5: "instead of generating separate Type 7 LSAs for 172.16.5.0/24 and 172.16.6.0/24, generate one Type 7 LSA for 172.16.0.0/16." The ABR (R3) translates this to a single Type 5 LSA for Area 0 and beyond.

For OSPFv3:
```
router ospfv3 1
 address-family ipv6 unicast
  summary-prefix 2001:DB8:172::/48
```

> **Exam distinction:** ABR summarization (`area range`) aggregates **intra-area** routes crossing a boundary. ASBR summarization (`summary-address`) aggregates **external** redistributed routes at the source.

### Distribute-List Filtering (`distribute-list prefix ... in`)

The `distribute-list prefix ... in` command under `router ospf` prevents specific OSPF-learned routes from being installed into the local routing table (RIB). It does **not** filter LSAs from the LSDB — other routers are unaffected.

```
ip prefix-list BLOCK_10_1_5 seq 5 deny 10.1.5.0/24
ip prefix-list BLOCK_10_1_5 seq 10 permit 0.0.0.0/0 le 32

router ospf 1
 distribute-list prefix BLOCK_10_1_5 in
```

The prefix-list denies the specific prefix and permits everything else. The distribute-list references the prefix-list to filter routes entering the RIB from OSPF. On R1, `10.1.5.0/24` will be absent from `show ip route` even though the LSDB still contains the LSA (or summary).

> **Exam point:** OSPF `distribute-list in` is a **local RIB filter only**. It does not affect what is advertised to neighbors. This differs from EIGRP `distribute-list out`, which affects what is sent to neighbors.

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| Inter-area summarization | Configure `area range` on ABR to reduce Type 3 LSA count |
| IPv6 summarization | Apply OSPFv3 AF `area range` for IPv6 address-family |
| ASBR summarization | Use `summary-address` to aggregate external Type 7/5 LSAs |
| IPv6 ASBR summarization | Apply OSPFv3 AF `summary-prefix` for IPv6 external routes |
| Prefix suppression | Use `area range not-advertise` to hide specific subnets |
| RIB filtering | Deploy `distribute-list prefix ... in` to control local table |
| Verification workflow | Confirm summarization effect via LSDB and routing table inspection |

---

## 2. Topology & Scenario

**Enterprise scenario:** You are a network engineer at Acme Corp. The OSPF backbone team has deployed multi-area OSPFv2/v3 with Totally Stubby Area 1 and NSSA Area 2 (completed in lab-03). The NOC has raised two concerns:

1. **Routing table growth:** R4 in Area 1 hosts four new server loopback subnets (10.1.4-7.0/24). Without summarization, four separate inter-area (O IA) entries appear in every Area 0 and Area 2 router's table. The network team wants a single aggregate entry.

2. **External route pollution:** R5 redistributes two simulated ISP loopbacks (172.16.5.0/24, 172.16.6.0/24) into OSPF. Policy requires these to appear as a single aggregate in Area 0, not as two individual Type 5 entries.

Additionally, the security team has requested that `10.1.5.0/24` must not appear in R1's routing table (local policy — the specific server pool is not accessible from R1's zone). And a new policy requires that `10.1.6.0/24` must not be advertised outside Area 1 at all.

Your task: implement inter-area and ASBR summarization, apply route filtering, and verify that end-to-end reachability for permitted routes is maintained.

```
                    ┌──────────────────────────────────────────────────────────────┐
                    │                     Area 0 (Backbone)                        │
                    │                                                               │
                    │                   ┌──────────────────┐                       │
                    │                   │        R1        │                       │
                    │                   │  Backbone Router  │                       │
                    │                   │  Lo0: 1.1.1.1/32  │                       │
                    │                   │  distribute-list  │                       │
                    │                   └────────┬─────────┘                       │
                    │                   Gi0/0   │                                  │
                    │                    .1     │                                  │
                    │              ┌────────────┴─────────────┐                   │
                    │              │      SW-AREA0             │                   │
                    │              │  10.0.123.0/24 broadcast  │                   │
                    │              └──────┬──────────────┬─────┘                   │
                    │           .2 Gi0/0 │              │ Gi0/0 .3                 │
                    │         ┌──────────┴──┐      ┌────┴─────────┐               │
                    │         │     R2      │      │      R3      │               │
                    │         │  ABR 0/1    │      │  ABR 0/2     │               │
                    │         │  2.2.2.2/32 │      │  3.3.3.3/32  │               │
                    │         │  area 1     │      │  area 2 nssa │               │
                    │         │  range/22   │      │              │               │
                    └─────────┼─────────────┘      └────┬─────────┼───────────────┘
                              │  Gi0/1  Gi0/2           │ Gi0/1   │
              Area 1          │  .1      .1             .1        │  Area 2
      ┌───────────────────────┼──────────────────┐      │         │──────────────────┐
      │ (Totally Stubby)      │                  │      │         │   (NSSA)         │
      │           10.1.24.0/30│  10.1.26.0/30    │      │10.2.35.0/30               │
      │               .2 Gi0/0│ Gi0/2 .2 Gi0/0  │      │         │                  │
      │         ┌─────────────┘      ┌───────────┘    .2 Gi0/0   │                  │
      │         │                    │           ┌─────────────────┘                 │
      │  ┌──────┴──────┐    ┌────────┴────┐      │  ┌──────────────┐                │
      │  │     R4      │    │     R6      │      │  │      R5      │                │
      │  │ Internal    │    │  Internal   │      │  │  ASBR Area 2 │                │
      │  │ 4.4.4.4/32  │    │  6.6.6.6/32 │      │  │  5.5.5.5/32  │                │
      │  │ Lo1-4:      │    │             │      │  │  Lo1: 172.16.5│                │
      │  │ 10.1.4-7/24 │    │             │      │  │  Lo2: 172.16.6│                │
      │  └──┬──────┬───┘    └──────┬──────┘      │  │  summ:/16    │                │
      │ Gi0/1│  Gi0/2             Gi0/1 .1        │  └─────┬────────┘                │
      │.1  10.1.46 .1               .2            │  Gi0/1 │                        │
      │    └──────────────────────┘               │        │                        │
      │           10.1.46.0/30                    │  192.168.2.0/24                 │
      │                                           │                                  │
      │   Gi0/2 .1                              .1│                                  │
      │   192.168.1.0/24                       .10│                                  │
      │         │                          ┌──────┴───┐                             │
      │   ┌─────┴──────┐                   │   PC2    │                             │
      │   │    PC1     │                   │ Area 2   │                             │
      │   │  Area 1    │                   │ 192.168  │                             │
      │   │ 192.168    │                   │  .2.10   │                             │
      │   │  .1.10     │                   └──────────┘                             │
      │   └────────────┘                                                            │
      └─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Hardware & Environment Specifications

### Cabling Table

| Link ID | Source | Interface | Destination | Interface | Subnet | Area |
|---------|--------|-----------|-------------|-----------|--------|------|
| L1 | R1 | Gi0/0 | SW-AREA0 | port1 | 10.0.123.0/24 | 0 |
| L2 | R2 | Gi0/0 | SW-AREA0 | port2 | 10.0.123.0/24 | 0 |
| L3 | R3 | Gi0/0 | SW-AREA0 | port3 | 10.0.123.0/24 | 0 |
| L4 | R2 | Gi0/1 | R4 | Gi0/0 | 10.1.24.0/30 | 1 |
| L5 | R3 | Gi0/1 | R5 | Gi0/0 | 10.2.35.0/30 | 2 |
| L6 | R4 | Gi0/2 | PC1 | e0 | 192.168.1.0/24 | 1 |
| L7 | R5 | Gi0/1 | PC2 | e0 | 192.168.2.0/24 | 2 |
| L8 | R2 | Gi0/2 | R6 | Gi0/0 | 10.1.26.0/30 | 1 |
| L9 | R4 | Gi0/1 | R6 | Gi0/1 | 10.1.46.0/30 | 1 |

### Console Access Table

| Device | Port | Connection Command |
|--------|------|--------------------|
| R1 | (see EVE-NG UI) | `telnet 192.168.242.128 <port>` |
| R2 | (see EVE-NG UI) | `telnet 192.168.242.128 <port>` |
| R3 | (see EVE-NG UI) | `telnet 192.168.242.128 <port>` |
| R4 | (see EVE-NG UI) | `telnet 192.168.242.128 <port>` |
| R5 | (see EVE-NG UI) | `telnet 192.168.242.128 <port>` |
| R6 | (see EVE-NG UI) | `telnet 192.168.242.128 <port>` |
| PC1 | (see EVE-NG UI) | `telnet 192.168.242.128 <port>` |
| PC2 | (see EVE-NG UI) | `telnet 192.168.242.128 <port>` |

> **Note:** Console ports are assigned dynamically by EVE-NG. Open the lab in the EVE-NG web UI, start all nodes, and note the assigned telnet port for each device from the topology canvas.

---

## 4. Base Configuration

The following is pre-loaded via `setup_lab.py` (sourced from `initial-configs/`). This is the complete lab-03 solution state.

**Pre-configured (do not re-configure):**
- IP addressing (IPv4 and IPv6) on all interfaces
- OSPFv2 process 1 with explicit router-IDs on all routers
- Multi-area OSPF: Area 0 (backbone), Area 1 (totally stubby), Area 2 (NSSA)
- OSPFv3 address-family (IPv6) on all routers
- DR/BDR tuning: R1 priority 255, R2 priority 200, R3 priority 0
- Point-to-point network type on all inter-router links (Gi0/1, Gi0/2 on ABRs)
- Area 1 totally stubby (`area 1 stub no-summary` on R2 ABR; `area 1 stub` on R4, R6)
- Area 2 NSSA (`area 2 nssa` on R3 and R5)
- R5 ASBR redistribution of Loopback1 and Loopback2 via route-map REDIST_EXT
- Passive-interface on LAN segments (R4 Gi0/2, R5 Gi0/1)
- VTY access (telnet) on all routers

**NOT pre-configured (your task):**
- Summarization loopbacks on R4 (Loopback1-4)
- OSPF advertisement of R4 loopbacks
- Inter-area summarization on R2
- OSPFv3 inter-area summarization on R2
- ASBR summarization on R5
- OSPFv3 ASBR summarization on R5
- Distribute-list filtering on R1
- Area range not-advertise on R2

---

## 5. Lab Challenge: Core Implementation

### Task 1: Add Summarization Loopbacks to R4

On R4, create four new loopback interfaces to serve as summarization targets. Assign IPv4 addresses from the 10.1.4.0/24, 10.1.5.0/24, 10.1.6.0/24, and 10.1.7.0/24 subnets (host address .1 on each). Assign corresponding IPv6 addresses from 2001:db8:1:4::/64, 2001:db8:1:5::/64, 2001:db8:1:6::/64, and 2001:db8:1:7::/64 (host address ::1 on each). Add descriptive labels so the interfaces are identifiable as summarization targets.

**Verification:** `show ip interface brief | include Loopback` must show four new loopback interfaces in up/up state with correct IP addresses.

---

### Task 2: Advertise R4 Loopback Networks into OSPF Area 1

Advertise each of the four new loopback subnets (10.1.4-7.0/24) into OSPF Area 1 using the appropriate addressing mechanism. Enable OSPFv3 IPv6 on each new loopback interface for Area 1. After this task, the four /24 routes should appear as O (intra-area) routes in R4's routing table and as O IA routes on R1, R2, R3 (before summarization is applied).

**Verification:** `show ip route ospf` on R1 must show four separate `O IA 10.1.x.0/24` entries. `show ospfv3 route` on R1 must show four separate IPv6 inter-area entries for 2001:db8:1:4-7::/64.

---

### Task 3: Configure Inter-Area Summarization on R2 (IPv4)

On R2, configure ABR summarization for the four Area 1 loopback subnets. Use a single aggregate that covers 10.1.4.0/24 through 10.1.7.0/24. After this task, R1 must show a single summarized inter-area route instead of four individual /24 entries.

**Verification:** `show ip route ospf` on R1 must show exactly one `O IA 10.1.4.0/22` entry. The four individual /24 routes must be absent. `show ip ospf database summary` on R1 must show one Type 3 LSA for 10.1.4.0/22.

---

### Task 4: Configure OSPFv3 Inter-Area Summarization on R2 (IPv6)

On R2, configure OSPFv3 address-family summarization for the equivalent IPv6 loopback prefixes. Use a single aggregate that covers 2001:db8:1:4::/64 through 2001:db8:1:7::/64. A /62 prefix covers exactly these four /64 subnets.

**Verification:** `show ospfv3 database inter-area prefix` on R1 must show one entry for 2001:db8:1:4::/62. The four individual /64 entries must be absent.

---

### Task 5: Configure ASBR Summarization on R5 (IPv4)

On R5, configure OSPF ASBR summarization so that the two external loopback routes (172.16.5.0/24 and 172.16.6.0/24) are aggregated into a single external route before being flooded as a Type 7 LSA. Use a 172.16.0.0/16 aggregate. After this task, R1 must show a single external route instead of two individual /24 entries.

**Verification:** `show ip route ospf` on R1 must show exactly one `O E2 172.16.0.0/16` entry. The two individual /24 external routes must be absent. `show ip ospf database external` on R3 must show one Type 5 LSA for 172.16.0.0/16.

---

### Task 6: Configure OSPFv3 ASBR Summarization on R5 (IPv6)

On R5, configure OSPFv3 ASBR summarization for the IPv6 external loopback prefixes (2001:db8:172:5::/64 and 2001:db8:172:6::/64). Use a 2001:db8:172::/48 aggregate.

**Verification:** `show ospfv3 database inter-area prefix` on R1 should show the IPv6 aggregate. `show ospfv3 route` on R1 must show one IPv6 external aggregate, not two individual /64 entries.

---

### Task 7: Apply Distribute-List Filtering on R1

On R1, create a named prefix-list that denies 10.1.5.0/24 and permits all other prefixes. Apply this prefix-list as an inbound distribute-list on R1's OSPF process. After this task, 10.1.5.0/24 must not appear in R1's IPv4 routing table.

Note: at this point in the lab, the 10.1.4.0/22 summary covers 10.1.5.0/24 (so the specific /24 is already absent from the routing table). The distribute-list demonstrates the filtering mechanism and would suppress the specific route if it were individually advertised (for example, if summarization were removed).

**Verification:** `show ip route 10.1.5.0` on R1 must return no match. `show ip ospf database` on R1 must still contain the summary LSA (the LSDB is unaffected; only RIB installation is filtered).

---

### Task 8: Suppress a Specific Subnet with `area range not-advertise`

On R2, add an `area range not-advertise` statement for the 10.1.6.0/24 prefix. This suppresses the /24 from being advertised into Area 0 (it is neither individually advertised nor counted as contributing to the /22 summary's cost).

**Verification:** `show ip ospf database summary` on R1 must show that the 10.1.4.0/22 summary is still present (the other three /24s still contribute). `show ip route 10.1.6.0` on R1 must return no match (the /24 is suppressed — it is reachable only from within Area 1 via the /22 aggregate, but R1's distribute-list already blocks /24 specifics irrelevant here).

---

### Task 9: Verify Filtering Effectiveness

Confirm that the filtering mechanisms are working as intended across all routers.

- On R1: `10.1.5.0/24` must be absent from `show ip route` (distribute-list effect)
- On R1 and R3: `10.1.6.0/24` must be absent (not-advertise suppression)
- On R1: `10.1.4.0/22` must appear as a single O IA summary (summarization effect)
- On R1: `172.16.0.0/16` must appear as a single O E2 (ASBR summarization effect)
- The LSDB on R1 (`show ip ospf database`) must still contain the underlying LSAs

**Verification:** Run `show ip route ospf` on R1, R2, R3. Confirm only the aggregate entries are present for the summarized ranges. Confirm the LSDB contains fewer Type 3 and Type 5/7 LSAs than before summarization.

---

### Task 10: Confirm End-to-End Reachability

Verify that the summarization and filtering have not broken connectivity between permitted endpoints. PC1 (192.168.1.10) must reach PC2 (192.168.2.10) via IPv4. Repeat the test for IPv6 (2001:db8:1:1::10 to 2001:db8:2:2::10).

**Verification:** `ping 192.168.2.10` from PC1 must succeed. `ping 2001:db8:2:2::10` from PC1 must succeed.

---

## 6. Verification & Analysis

### Task 1-2: Loopback Interfaces on R4

```
R4# show ip interface brief | include Loopback
Loopback0              4.4.4.4          YES manual up                    up
Loopback1              10.1.4.1         YES manual up                    up    ! ← Lo1 must be up/up
Loopback2              10.1.5.1         YES manual up                    up    ! ← Lo2 must be up/up
Loopback3              10.1.6.1         YES manual up                    up    ! ← Lo3 must be up/up
Loopback4              10.1.7.1         YES manual up                    up    ! ← Lo4 must be up/up

R4# show ip route ospf
O    4.4.4.4/32 [110/1] via ...                                                ! ← own loopback (local)
O*IA 0.0.0.0/0 [110/2] via 10.1.24.1, GigabitEthernet0/0                      ! ← default from ABR (totally stubby)
...

R1# show ip route ospf | include 10.1
O IA     10.1.24.0/30 [110/2] via 10.0.123.2 ...
O IA     10.1.4.0/24  [110/12] via 10.0.123.2 ...   ! ← should see 4x /24 before summarization
O IA     10.1.5.0/24  [110/12] via 10.0.123.2 ...
O IA     10.1.6.0/24  [110/12] via 10.0.123.2 ...
O IA     10.1.7.0/24  [110/12] via 10.0.123.2 ...
```

### Task 3: Inter-Area Summarization on R2 (IPv4)

```
R2# show ip ospf database summary | include 10.1.4
                Type-3 Summary Link States (Area 0)
LS age: 42
  LS Type: Summary Links(Network)
  Link State ID: 10.1.4.0 (summary Network Number)        ! ← single /22 Type 3 LSA
  Advertising Router: 2.2.2.2
  Network Mask: /22

R1# show ip route ospf | include 10.1.4
O IA     10.1.4.0/22 [110/12] via 10.0.123.2, GigabitEthernet0/0   ! ← single summary, not 4x /24

R1# show ip route 10.1.4.0
Routing entry for 10.1.4.0/22
  Known via "ospf 1", ...
  O IA, metric 12, candidate default path

R1# show ip route 10.1.5.0
% Network not in table    ! ← specific /24 absent (covered by /22 summary)
```

### Task 4: OSPFv3 Inter-Area Summarization on R2

```
R2# show ospfv3 database inter-area prefix
            OSPFv3 Router with ID (2.2.2.2) (Process ID 1)

                Inter Area Prefix Link States (Area 0)
  LS Age: 55
  LS Type: Inter Area Prefix Links
  Link State ID: 0x0000000X
  Advertising Router: 2.2.2.2
  Prefix: 2001:DB8:1:4::/62       ! ← single /62 IPv6 summary in Area 0

R1# show ospfv3 route | include 2001:DB8:1
OI  2001:DB8:1:4::/62  [110/...]  via ... GigabitEthernet0/0   ! ← /62 covers :4::/64 through :7::/64
```

### Task 5: ASBR Summarization on R5 (IPv4)

```
R5# show ip ospf database external | include 172.16
                Type-5 AS External Link States
  Link State ID: 172.16.0.0 (External Network Number)     ! ← single /16 aggregate
  Advertising Router: 5.5.5.5
  Network Mask: /16

R1# show ip route ospf | include 172.16
O E2     172.16.0.0/16 [110/20] via 10.0.123.3, GigabitEthernet0/0   ! ← single E2, not 2x /24
```

### Task 6: OSPFv3 ASBR Summarization on R5

```
R1# show ospfv3 route | include 2001:DB8:172
OE2 2001:DB8:172::/48  [110/20]  via ...   ! ← single /48 covers :5::/64 and :6::/64
```

### Task 7: Distribute-List on R1

```
R1# show ip route 10.1.5.0
% Network not in table   ! ← blocked by distribute-list

R1# show ip ospf database | include 10.1.4
  10.1.4.0/22  (Type-3 Summary) ...   ! ← LSA still present in LSDB (distribute-list is RIB only)
```

### Task 8: area range not-advertise

```
R1# show ip route 10.1.6.0
% Network not in table   ! ← suppressed by not-advertise on R2

R3# show ip route 10.1.6.0
% Network not in table   ! ← suppressed topology-wide (not just on R1)

R2# show ip ospf database summary | include 10.1.6
                 (absent — no Type 3 LSA for 10.1.6.0/24)   ! ← suppressed by not-advertise
```

### Task 9-10: End-to-End Reachability

```
PC1> ping 192.168.2.10
84 bytes from 192.168.2.10 icmp_seq=1 ttl=61 time=10 ms    ! ← IPv4 reachability confirmed
84 bytes from 192.168.2.10 icmp_seq=2 ttl=61 time=8 ms

PC1> ping 2001:db8:2:2::10
2001:db8:2:2::10 icmp6_seq=1 ttl=61 time=12 ms              ! ← IPv6 reachability confirmed
2001:db8:2:2::10 icmp6_seq=2 ttl=61 time=10 ms
```

---

## 7. Verification Cheatsheet

### Inter-Area Summarization (`area range`)

```
router ospf 1
 area <area-id> range <network> <mask>
 area <area-id> range <network> <mask> not-advertise

router ospfv3 1
 address-family ipv6 unicast
  area <area-id> range <prefix>/<len>
```

| Command | Purpose |
|---------|---------|
| `area 1 range 10.1.4.0 255.255.252.0` | Summarize Area 1 routes into 10.1.4.0/22 |
| `area 1 range 10.1.6.0 255.255.255.0 not-advertise` | Suppress 10.1.6.0/24 from Area 0 |
| `area 1 range 2001:DB8:1:4::/62` | IPv6 summary for four /64 prefixes |

> **Exam tip:** `area range` is configured on the **ABR** only. It applies to routes being advertised **out of** the specified area. Internal routers do not run this command.

### ASBR Summarization (`summary-address`)

```
router ospf 1
 summary-address <network> <mask>

router ospfv3 1
 address-family ipv6 unicast
  summary-prefix <prefix>/<len>
```

| Command | Purpose |
|---------|---------|
| `summary-address 172.16.0.0 255.255.0.0` | Aggregate external routes before generating Type 7 |
| `summary-prefix 2001:DB8:172::/48` | IPv6 aggregate for external prefixes |

> **Exam tip:** `summary-address` is configured on the **ASBR** only (the router doing redistribution). The ABR translates the aggregated Type 7 to a single Type 5.

### Distribute-List Filtering

```
ip prefix-list <NAME> seq 5 deny <prefix>/<len>
ip prefix-list <NAME> seq 10 permit 0.0.0.0/0 le 32

router ospf 1
 distribute-list prefix <NAME> in
```

| Command | Purpose |
|---------|---------|
| `ip prefix-list BLOCK seq 5 deny 10.1.5.0/24` | Deny specific prefix |
| `ip prefix-list BLOCK seq 10 permit 0.0.0.0/0 le 32` | Permit everything else |
| `distribute-list prefix BLOCK in` | Apply filter to OSPF RIB installation |

> **Exam tip:** OSPF `distribute-list in` is a **local RIB filter** — it does NOT affect the LSDB or what other routers see. To filter LSAs from a neighbor, use Type 3 LSA filtering (`area X filter-list prefix NAME in/out`) instead.

### Verification Commands

| Command | What to Look For |
|---------|-----------------|
| `show ip route ospf` | Confirm summary entries present, specifics absent |
| `show ip ospf database summary` | Type 3 LSA count and content — fewer after summarization |
| `show ip ospf database external` | Type 5 LSA count — one aggregate, not multiple specifics |
| `show ospfv3 database inter-area prefix` | IPv6 summary Type 3 LSAs |
| `show ospfv3 route` | IPv6 OSPF RIB entries |
| `show ip route 10.1.5.0` | Must return "% Network not in table" after distribute-list |
| `show ip route 10.1.6.0` | Must return "% Network not in table" after not-advertise |
| `show ip ospf border-routers` | ABR and ASBR entries — confirm R2/R3 as ABR, R5 as ASBR |

### Wildcard Mask Quick Reference

| Prefix Length | Subnet Mask | Wildcard Mask | Example |
|--------------|-------------|---------------|---------|
| /32 | 255.255.255.255 | 0.0.0.0 | Loopback host |
| /30 | 255.255.255.252 | 0.0.0.3 | P2P link |
| /24 | 255.255.255.0 | 0.0.0.255 | Standard subnet |
| /22 | 255.255.252.0 | 0.0.3.255 | Summary of 4x /24 |
| /16 | 255.255.0.0 | 0.0.255.255 | Large summary |

### Common OSPF Summarization Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| Individual /24s still appear in Area 0 | `area range` not configured on ABR, or wrong area specified |
| Summary missing but contributing routes present | `area range` mask is too narrow (doesn't cover all specifics) |
| ASBR summary not working | `summary-address` configured on ABR instead of ASBR |
| distribute-list has no effect | Prefix-list has wrong prefix or missing `permit 0.0.0.0/0 le 32` |
| not-advertise still shows route in table | Prefix-list or `area range` mis-typed; wrong mask |
| IPv6 summary absent | OSPFv3 AF `area range` missing from ABR config |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Task 1-2: Summarization Loopbacks on R4

<details>
<summary>Click to view R4 Configuration</summary>

```bash
! R4 — add Loopback1-4 and advertise into Area 1
interface Loopback1
 description SUMMARIZATION_TARGET_1
 ip address 10.1.4.1 255.255.255.0
 ipv6 address 2001:DB8:1:4::1/64
 ospfv3 1 ipv6 area 1
!
interface Loopback2
 description SUMMARIZATION_TARGET_2
 ip address 10.1.5.1 255.255.255.0
 ipv6 address 2001:DB8:1:5::1/64
 ospfv3 1 ipv6 area 1
!
interface Loopback3
 description SUMMARIZATION_TARGET_3
 ip address 10.1.6.1 255.255.255.0
 ipv6 address 2001:DB8:1:6::1/64
 ospfv3 1 ipv6 area 1
!
interface Loopback4
 description SUMMARIZATION_TARGET_4
 ip address 10.1.7.1 255.255.255.0
 ipv6 address 2001:DB8:1:7::1/64
 ospfv3 1 ipv6 area 1
!
router ospf 1
 network 10.1.4.0 0.0.0.255 area 1
 network 10.1.5.0 0.0.0.255 area 1
 network 10.1.6.0 0.0.0.255 area 1
 network 10.1.7.0 0.0.0.255 area 1
```

</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ip interface brief | include Loopback
show ip route ospf
show ip ospf database
```

</details>

---

### Task 3: Inter-Area Summarization on R2 (IPv4)

<details>
<summary>Click to view R2 Configuration</summary>

```bash
! R2 — ABR inter-area summarization for Area 1
router ospf 1
 area 1 range 10.1.4.0 255.255.252.0
```

</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ip ospf database summary
show ip route ospf
show ip route 10.1.4.0
show ip route 10.1.5.0
```

</details>

---

### Task 4: OSPFv3 Inter-Area Summarization on R2 (IPv6)

<details>
<summary>Click to view R2 Configuration</summary>

```bash
! R2 — OSPFv3 AF inter-area summarization
router ospfv3 1
 address-family ipv6 unicast
  area 1 range 2001:DB8:1:4::/62
```

</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ospfv3 database inter-area prefix
show ospfv3 route
```

</details>

---

### Task 5: ASBR Summarization on R5 (IPv4)

<details>
<summary>Click to view R5 Configuration</summary>

```bash
! R5 — ASBR summarization for external routes
router ospf 1
 summary-address 172.16.0.0 255.255.0.0
```

</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ip ospf database external
show ip route ospf | include 172.16
show ip route 172.16.5.0
```

</details>

---

### Task 6: OSPFv3 ASBR Summarization on R5 (IPv6)

<details>
<summary>Click to view R5 Configuration</summary>

```bash
! R5 — OSPFv3 ASBR summarization
router ospfv3 1
 address-family ipv6 unicast
  summary-prefix 2001:DB8:172::/48
```

</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ospfv3 route
show ospfv3 database inter-area prefix
```

</details>

---

### Task 7: Distribute-List on R1

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1 — prefix-list and distribute-list
ip prefix-list BLOCK_10_1_5 seq 5 deny 10.1.5.0/24
ip prefix-list BLOCK_10_1_5 seq 10 permit 0.0.0.0/0 le 32
!
router ospf 1
 distribute-list prefix BLOCK_10_1_5 in
```

</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ip route 10.1.5.0
show ip prefix-list BLOCK_10_1_5
show ip ospf database
```

</details>

---

### Task 8: area range not-advertise on R2

<details>
<summary>Click to view R2 Configuration</summary>

```bash
! R2 — suppress 10.1.6.0/24 from Area 0
router ospf 1
 area 1 range 10.1.6.0 255.255.255.0 not-advertise
```

</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ip route 10.1.6.0
show ip ospf database summary
show ip route ospf
```

</details>

---

### Task 9-10: Verification and Reachability

<details>
<summary>Click to view Expected Output</summary>

```bash
! On R1
show ip route ospf
! Must show:
!   O IA 10.1.4.0/22  (summary present)
!   O E2 172.16.0.0/16 (ASBR summary present)
!   No 10.1.5.0/24, 10.1.6.0/24 entries

show ip route 10.1.5.0
! % Network not in table

show ip route 10.1.6.0
! % Network not in table

! On PC1
ping 192.168.2.10       ! Must succeed (5/5)
ping 2001:db8:2:2::10   ! Must succeed (5/5)
```

</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. Inject the fault first, then diagnose and fix using only show commands.

### Workflow

```bash
python3 setup_lab.py --host 192.168.242.128                      # reset to known-good
python3 scripts/fault-injection/inject_scenario_01.py --host 192.168.242.128  # Ticket 1
python3 scripts/fault-injection/apply_solution.py --host 192.168.242.128     # restore
```

---

### Ticket 1 — Summary Route Missing from Area 0 Routing Tables

R1 reports that instead of a single aggregate entry for the Area 1 server subnets, it now sees four separate inter-area routes. The change was made during a maintenance window on R2.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py --host 192.168.242.128`

**Success criteria:** After fixing, `show ip route ospf` on R1 must show a single `O IA 10.1.4.0/22` entry and no individual /24 entries.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! Step 1: Confirm symptom on R1
R1# show ip route ospf | include 10.1
! Expect: 4x O IA /24 entries — summarization broken

! Step 2: Verify ABR config on R2
R2# show running-config | section router ospf
! Look for: area 1 range 10.1.4.0 255.255.252.0
! If missing: summarization command was removed

! Step 3: Verify LSDB for Area 0 — individual Type 3 LSAs present?
R1# show ip ospf database summary
! If 4x /24 Type 3 LSAs from 2.2.2.2 present: confirms missing area range on R2
```

</details>

<details>
<summary>Click to view Fix</summary>

```bash
! On R2 — restore inter-area summarization
router ospf 1
 area 1 range 10.1.4.0 255.255.252.0

! Verify
R1# show ip route ospf | include 10.1.4
! O IA 10.1.4.0/22 must appear; individual /24s must be gone
```

</details>

---

### Ticket 2 — External Routes Not Fully Summarized on R5

R1 shows two separate external entries (172.16.5.0/24 and 172.16.6.0/24) instead of the expected single 172.16.0.0/16 aggregate. R5 was recently reconfigured by a junior engineer.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py --host 192.168.242.128`

**Success criteria:** After fixing, `show ip route ospf` on R1 must show exactly one `O E2 172.16.0.0/16` entry.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! Step 1: Confirm symptom on R1
R1# show ip route ospf | include 172.16
! Expect: 2x O E2 /24 entries — ASBR summary broken

! Step 2: Check R5 OSPF config
R5# show running-config | section router ospf
! Look for: summary-address 172.16.0.0 255.255.0.0
! If present but wrong mask (e.g., 255.255.255.0 /24): summary too narrow, doesn't cover both

! Step 3: Check LSDB on R5
R5# show ip ospf database external
! If two Type 7 LSAs (/24 each): summary-address not working correctly
```

</details>

<details>
<summary>Click to view Fix</summary>

```bash
! On R5 — restore correct ASBR summarization mask
router ospf 1
 no summary-address 172.16.5.0 255.255.255.0
 summary-address 172.16.0.0 255.255.0.0

! Verify
R1# show ip route ospf | include 172.16
! O E2 172.16.0.0/16 must be the only external entry
```

</details>

---

### Ticket 3 — Distribute-List Has No Effect on R1's Routing Table

The security team confirms that 10.1.5.0/24 must not appear in R1's routing table, but the entry is still present. A colleague says they configured a distribute-list on R1 yesterday.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py --host 192.168.242.128`

**Success criteria:** After fixing, `show ip route 10.1.5.0` on R1 must return "% Network not in table."

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! Step 1: Confirm symptom on R1
R1# show ip route 10.1.5.0
! Expect: entry exists — distribute-list not filtering

! Step 2: Check distribute-list config
R1# show running-config | section router ospf
! Look for: distribute-list prefix BLOCK_10_1_5 in
! If present: check the prefix-list name

! Step 3: Check prefix-list
R1# show ip prefix-list
! Look for: prefix-list named BLOCK_10_1_5
! If a different name exists (e.g., BLOCK_10_1_5_V2): name mismatch — distribute-list references wrong list
! If prefix-list exists but has wrong entries: check the deny statement
```

</details>

<details>
<summary>Click to view Fix</summary>

```bash
! On R1 — the distribute-list references a non-existent prefix-list name
! Remove the broken distribute-list and add the correct one:
router ospf 1
 no distribute-list prefix BLOCK_10_1_5_TYPO in
 distribute-list prefix BLOCK_10_1_5 in

! Ensure the correctly named prefix-list exists:
ip prefix-list BLOCK_10_1_5 seq 5 deny 10.1.5.0/24
ip prefix-list BLOCK_10_1_5 seq 10 permit 0.0.0.0/0 le 32

! Verify
R1# show ip route 10.1.5.0
! % Network not in table
```

</details>

---

### Ticket 4 — IPv6 Inter-Area Summary Absent from Area 0

R1's IPv6 OSPF routing table shows four individual /64 entries for 2001:db8:1:4-7::/64 instead of the expected single /62 aggregate. The IPv4 summary (10.1.4.0/22) is working correctly.

**Inject:** `python3 scripts/fault-injection/inject_scenario_04.py --host 192.168.242.128`

**Success criteria:** After fixing, `show ospfv3 route` on R1 must show one `OI 2001:DB8:1:4::/62` entry and no individual /64 entries from that range.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! Step 1: Confirm symptom
R1# show ospfv3 route | include 2001:DB8:1
! Expect: 4x OI /64 entries — IPv6 summary missing

! Step 2: Check R2 OSPFv3 AF config
R2# show running-config | section router ospfv3
! Look for: area 1 range 2001:DB8:1:4::/62 under address-family ipv6 unicast
! If absent: IPv6 area range was not configured (or was removed)

! Step 3: Confirm IPv4 summary still works
R1# show ip route ospf | include 10.1.4
! O IA 10.1.4.0/22 should still be present (IPv4 unaffected)
```

</details>

<details>
<summary>Click to view Fix</summary>

```bash
! On R2 — restore OSPFv3 AF inter-area summarization
router ospfv3 1
 address-family ipv6 unicast
  area 1 range 2001:DB8:1:4::/62

! Verify
R1# show ospfv3 route | include 2001:DB8:1:4
! OI 2001:DB8:1:4::/62 must appear; individual /64s must be absent
```

</details>

---

### Ticket 5 — Wrong Subnet Suppressed by `area range not-advertise`

R3 cannot reach 10.1.4.0/24 (a subnet that should be reachable via the 10.1.4.0/22 summary). Meanwhile, 10.1.6.0/24 (the subnet that should be suppressed) is reachable from R3. A change was made to R2's `area range not-advertise` configuration during a policy enforcement window.

**Inject:** `python3 scripts/fault-injection/inject_scenario_05.py --host 192.168.242.128`

**Success criteria:** After fixing, `show ip route 10.1.6.0` on R3 must return no match, and `show ip route 10.1.4.0` must show the /22 aggregate or /24 entry is reachable.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! Step 1: Confirm symptom
R3# show ip route 10.1.4.0
! Expect: no match (wrong subnet suppressed)

R3# show ip route 10.1.6.0
! Expect: route exists (should be suppressed but isn't)

! Step 2: Check R2 area range config
R2# show running-config | section router ospf
! Look for: area 1 range ... not-advertise
! If: area 1 range 10.1.4.0 255.255.255.0 not-advertise  → WRONG subnet suppressed
! Should be: area 1 range 10.1.6.0 255.255.255.0 not-advertise

! Step 3: Verify correct area range for /22 summary still present
R2# show running-config | section router ospf
! area 1 range 10.1.4.0 255.255.252.0  ← this must still be present (no not-advertise)
```

</details>

<details>
<summary>Click to view Fix</summary>

```bash
! On R2 — remove wrong not-advertise and apply to correct prefix
router ospf 1
 no area 1 range 10.1.4.0 255.255.255.0 not-advertise
 area 1 range 10.1.6.0 255.255.255.0 not-advertise

! Verify
R3# show ip route 10.1.6.0
! % Network not in table (correctly suppressed)
R3# show ip route 10.1.4.0
! O IA 10.1.4.0/22 (summary restored)
```

</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] R4 Loopback1-4 configured with 10.1.4-7.0/24 and 2001:db8:1:4-7::/64 addresses
- [ ] All four R4 loopback subnets advertised into OSPF Area 1
- [ ] OSPFv3 IPv6 enabled on R4 Loopback1-4 for Area 1
- [ ] R2 configured with `area 1 range 10.1.4.0/22` inter-area summarization
- [ ] R1 shows single `O IA 10.1.4.0/22` — individual /24s absent
- [ ] R2 OSPFv3 AF configured with `area 1 range 2001:DB8:1:4::/62`
- [ ] R1 shows single `OI 2001:DB8:1:4::/62` — individual /64s absent
- [ ] R5 configured with `summary-address 172.16.0.0/16` ASBR summarization
- [ ] R1 shows single `O E2 172.16.0.0/16` — individual /24 externals absent
- [ ] R5 OSPFv3 AF configured with `summary-prefix 2001:DB8:172::/48`
- [ ] R1 prefix-list BLOCK_10_1_5 defined; distribute-list applied inbound
- [ ] `show ip route 10.1.5.0` on R1 returns no match
- [ ] R2 configured with `area 1 range 10.1.6.0/24 not-advertise`
- [ ] `show ip route 10.1.6.0` on R1 and R3 returns no match
- [ ] PC1 to PC2 IPv4 ping succeeds
- [ ] PC1 to PC2 IPv6 ping succeeds

### Troubleshooting

- [ ] Ticket 1 resolved: R2 inter-area summarization restored, single /22 in Area 0
- [ ] Ticket 2 resolved: R5 ASBR summarization correct mask, single /16 external
- [ ] Ticket 3 resolved: R1 distribute-list prefix-list name corrected
- [ ] Ticket 4 resolved: R2 OSPFv3 AF area range restored, single /62 in Area 0
- [ ] Ticket 5 resolved: R2 not-advertise applied to correct prefix (10.1.6.0/24)
