# Lab 02 — EIGRP Stub, Summarization, and Unequal-Cost Load Balancing

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

**Exam Objective:** 3.2.a — Compare EIGRP and OSPF (advanced distance-vector, DUAL, metrics, load balancing, path selection, stub)

This lab adds three advanced EIGRP features to the named-mode dual-stack foundation
from Lab 01: **stub routing**, **manual route summarization**, and **unequal-cost load
balancing via variance**. Each feature is independently tunable per address-family,
letting you shape query scope, advertisement scope, and path selection on an operational
EIGRP domain.

### Stub Routing

A stub router advertises a **restricted** set of prefixes to its neighbors AND tells
those neighbors not to send **EIGRP queries** through it. Queries are how EIGRP
searches for alternate paths when a successor is lost; scoping them away from
branch/leaf routers keeps convergence fast and prevents "stuck-in-active" (SIA) events.

In named mode, the stub setting is **per address-family**:

```
router eigrp EIGRP-LAB
 address-family ipv4 unicast autonomous-system 100
  eigrp stub <option>
 exit-address-family
```

**Stub options:**

| Option | Advertises | Use case |
|--------|------------|----------|
| `connected` | Directly connected subnets | Spoke with only local LAN networks |
| `static` | Redistributed static routes | Hub-and-spoke with static-only spoke |
| `summary` | Manually summarized routes | Spoke advertising a summary only |
| `receive-only` | Nothing (listens only) | One-way propagation |
| `redistributed` | Redistributed routes | Spoke importing from another protocol |
| (combinations) | e.g. `connected static` | Mix-and-match |

A hub router identifies a stub neighbor via its hello packet (the stub TLV). Once
identified, the hub **stops sending queries** to that neighbor — queries are the main
source of SIA issues in large hub-and-spoke networks.

### Route Summarization

EIGRP lets you **summarize** multiple more-specific prefixes into one aggregate route
at the egress interface. Summarization happens per interface in named mode:

```
router eigrp EIGRP-LAB
 address-family ipv4 unicast autonomous-system 100
  af-interface GigabitEthernet0/0
   summary-address 10.3.0.0 255.255.252.0
  exit-af-interface
 exit-address-family
```

**Effects of `summary-address`:**

1. The summary is advertised out the interface.
2. The more-specifics are **suppressed** from advertisements out that interface.
3. A **discard route** (Null0, AD 5) is installed on the summarizing router. This
   prevents routing loops if the summary covers more address space than the actual
   prefixes (anything unmatched gets dropped).
4. Administrative distance for the discard route can be tuned with
   `summary-address ... <AD>`.

For IPv6, the syntax uses prefix-length notation:

```
af-interface GigabitEthernet0/0
 summary-address 2001:DB8:3::/62
```

**Why summarize?** Smaller routing tables, hidden topology changes (a flap on one
specific subnet does not reach routers outside the summary boundary), and reduced
EIGRP query scope (queries stop at summary boundaries — the summarizing router
replies immediately on behalf of the suppressed prefixes).

### Unequal-Cost Load Balancing (Variance)

EIGRP can install **multiple paths** of unequal cost for the same prefix, distributing
traffic proportionally to each path's inverse metric. This is unique among IGPs
(OSPF supports only equal-cost load balancing).

**Variance rules:**

- Default variance is `1` (only equal-cost paths install).
- `variance N` installs any feasible successor whose metric is `< N × successor_metric`.
- Only **feasible successors** qualify — not all alternate paths. A feasible successor
  is a neighbor whose **advertised distance** (AD) is less than the current
  **feasible distance** (FD) via the successor. This loop-prevention rule is the
  core of DUAL (Diffusing Update Algorithm).

**Example:**

| Path | Composite Metric | Role |
|------|------------------|------|
| Via neighbor A | 3,328 | Successor (lowest) |
| Via neighbor B | 26,112 | Feasible successor (FC holds) |

Ratio 26,112 / 3,328 ≈ 7.85. `variance 8` installs both; `variance 1` (default)
installs only A.

**Traffic share** is proportional: the slower path receives ~(metric_A/metric_B) of
the traffic. Cisco IOS distributes flows via CEF per-destination by default.

### Bandwidth Manipulation

EIGRP's composite metric depends on the **minimum bandwidth** along the path. The
`bandwidth` command under an interface changes what EIGRP uses for its calculation
(the physical link speed is NOT changed). This is how you create metric asymmetry to
**demonstrate variance** without rewiring:

```
interface GigabitEthernet0/1
 bandwidth 100000     ! 100 Mbps in Kbps
```

Default for GigE is 1,000,000 Kbps. Lowering to 100,000 Kbps raises the path cost
through that link and allows alternate paths to become feasible successors.

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| Stub router configuration | Configure EIGRP stub per address-family with the appropriate option |
| Verify stub behaviour | Confirm on the hub that queries are suppressed toward the stub neighbor |
| Manual route summarization | Configure per-interface summary-address for IPv4 and IPv6 AFs |
| Summary verification | Confirm summary advertised, specifics suppressed, discard route installed |
| Bandwidth manipulation | Change EIGRP's bandwidth perception to create metric asymmetry |
| Variance configuration | Configure variance multiplier per AF to enable unequal-cost load balancing |
| Feasibility condition analysis | Read `show ip eigrp topology` to verify FS eligibility before installing |
| Traffic-share interpretation | Read `show ip route` traffic-share output and predict flow distribution |

---

## 2. Topology & Scenario

You are the network engineer at **Meridian Logistics**, a regional carrier that has
just expanded. The Branch B office on R3 now hosts four business applications, each
on its own /24 subnet (10.3.0.0/24 through 10.3.3.0/24). A new logistics depot,
**Branch C**, has been stood up: it sits behind router R4, which has only one uplink
(to R2) and one LAN (PC2 / 192.168.2.0/24).

Three operational demands drive this lab:

1. **Branch C must not be a transit path.** If the core loses a prefix, the hub
   routers must not send EIGRP queries down the single uplink to R4 hunting for
   alternates. You will configure R4 as an EIGRP stub (connected).
2. **Routing tables at the core are bloated.** The four Branch B subnets must appear
   as a single summary (10.3.0.0/22) from R1/R2's perspective. You will configure
   route summarization on R3, for both IPv4 and IPv6 AFs.
3. **The R2↔R3 link is a slower 100 Mbps metro pair.** During peak hours, the
   alternate R2→R1→R3 path (1 Gbps) sits idle. You will use `variance` on R2 to
   install both paths and share traffic across them.

### Topology Diagram

```
                    ┌───────────────────────┐
                    │          R1           │
                    │     (Hub Router)      │
                    │    Lo0: 1.1.1.1/32    │
                    └────┬─────────────┬────┘
                  Gi0/0  │             │   Gi0/1
            10.12.0.1/30 │             │  10.13.0.1/30
                         │             │
            10.12.0.2/30 │             │  10.13.0.2/30
                  Gi0/0  │             │   Gi0/0
              ┌──────────┘             └──────────┐
              │                                    │
    ┌─────────┴─────────┐                ┌─────────┴─────────┐
    │        R2         │ Gi0/1  Gi0/1   │        R3         │
    │  (Branch A /      ├────────────────┤  (Branch B /      │
    │   variance)       │  10.23.0.0/30  │   summarization)  │
    │  Lo0: 2.2.2.2/32  │  BW: 100 Mbps  │  Lo0: 3.3.3.3/32  │
    └─────────┬─────────┘                │  Lo1: 10.3.0.1/24 │
              │ Gi0/2                    │  Lo2: 10.3.1.1/24 │
              │ 10.24.0.1/30             │  Lo3: 10.3.2.1/24 │
              │                          │  Lo4: 10.3.3.1/24 │
              │ 10.24.0.2/30             └─────────┬─────────┘
              │ Gi0/0                              │ Gi0/3
    ┌─────────┴─────────┐                          │ 192.168.1.1/24
    │        R4         │                          │
    │  (Stub Router)    │                      ┌───┴───┐
    │  Lo0: 4.4.4.4/32  │                      │  PC1  │
    └─────────┬─────────┘                      │  .10  │
              │ Gi0/1                          └───────┘
              │ 192.168.2.1/24
              │
          ┌───┴───┐
          │  PC2  │
          │  .10  │
          └───────┘
```

All transit links are dual-stack. IPv6 transit prefixes follow the pattern
`2001:DB8:<low><high>::/64` (e.g., R2↔R4 is `2001:DB8:24::/64`).

---

## 3. Hardware & Environment Specifications

### Devices

| Device | Platform | Role |
|--------|----------|------|
| R1 | IOSv 15.7 | Hub router (EIGRP core) |
| R2 | IOSv 15.7 | Branch A router — variance point |
| R3 | IOSv 15.7 | Branch B router — summarization point |
| R4 | IOSv 15.7 | **New in lab-02** — stub spoke |
| PC1 | VPCS | End host on R3 LAN |
| PC2 | VPCS | **New in lab-02** — end host on R4 LAN |

### Cabling

| Link | Endpoint A | Endpoint B | IPv4 | IPv6 |
|------|-----------|-----------|------|------|
| L1 | R1 Gi0/0 | R2 Gi0/0 | 10.12.0.0/30 | 2001:DB8:12::/64 |
| L2 | R1 Gi0/1 | R3 Gi0/0 | 10.13.0.0/30 | 2001:DB8:13::/64 |
| L3 | R2 Gi0/1 | R3 Gi0/1 | 10.23.0.0/30 | 2001:DB8:23::/64 |
| L4 | R3 Gi0/3 | PC1 e0 | 192.168.1.0/24 | 2001:DB8:1:1::/64 |
| **L5** | **R2 Gi0/2** | **R4 Gi0/0** | **10.24.0.0/30** | **2001:DB8:24::/64** |
| **L6** | **R4 Gi0/1** | **PC2 e0** | **192.168.2.0/24** | **2001:DB8:2:2::/64** |

L3 is the bandwidth-manipulated link (100 Mbps) for the variance demo.

### Console Access Table

| Device | Port | Connection Command |
|--------|------|-------------------|
| R1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R3 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R4 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| PC1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| PC2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |

---

## 4. Base Configuration

The `initial-configs/` folder contains the starting state for this lab.

### Pre-loaded on R1, R2, R3

- Everything from Lab 01: named-mode EIGRP `EIGRP-LAB`, AS 100, dual-stack (IPv4 + IPv6 AFs)
- Router IDs: 1.1.1.1 / 2.2.2.2 / 3.3.3.3
- `passive-interface Gi0/3` on R3 in both AFs (toward PC1 LAN)

### Pre-loaded on R3 (new for this lab)

- Loopback1–Loopback4 with IPv4 `10.3.0-3.1/24` and IPv6 `2001:DB8:3:0-3::1/64`
- Loopback1–4 enrolled in EIGRP IPv4 AF via `network 10.3.0.0 0.0.3.255`
- IPv6 AF auto-enrolls the loopbacks (no network statement needed)

### Pre-loaded on R2 (new for this lab)

- Gi0/2 IP addressing: `10.24.0.1/30` + `2001:DB8:24::1/64` (toward R4)
- **NOT** yet enrolled in EIGRP — the student must add network statements

### Pre-loaded on R4 (new device)

- Hostname, interfaces Lo0, Gi0/0 (toward R2), Gi0/1 (toward PC2 LAN)
- IPv4 and IPv6 addressing on all interfaces
- **NO** EIGRP configuration — the student builds it from scratch

### NOT pre-loaded (student tasks)

- R4 EIGRP named-mode process (both AFs)
- R4 stub configuration
- R2 Gi0/2 EIGRP enrollment (IPv4 network statement)
- R3 summary-address on Gi0/0 and Gi0/1 (both AFs)
- Bandwidth manipulation on R2 Gi0/1 and R3 Gi0/1
- Variance multiplier on R2 (both AFs)

---

## 5. Lab Challenge: Core Implementation

### Task 1: Join R4 to the EIGRP Domain

- Enable IPv6 unicast routing on R4.
- Configure EIGRP named mode on R4 with process name `EIGRP-LAB`.
- Create IPv4 and IPv6 address-families under Autonomous System 100.
- Set the EIGRP router-id to `4.4.4.4` in both AFs.
- Enroll R4's connected prefixes in the IPv4 AF: Loopback0, the R2 link, and the PC2 LAN.
- Make R4's Gi0/1 (PC2 LAN) passive in both AFs — there is no EIGRP neighbor on that segment.

**Verification:** `show ip eigrp neighbors` on R2 must list R4 (10.24.0.2) as an
IPv4 neighbor; `show ipv6 eigrp neighbors` must list R4's link-local address as an
IPv6 neighbor.

### Task 2: Enroll R2's Gi0/2 in EIGRP

- Add a network statement on R2's IPv4 AF covering the 10.24.0.0/30 link to R4.
- The IPv6 AF auto-enrolls the interface because IPv6 addressing exists.

**Verification:** `show ip eigrp neighbors` on R2 must include R4 (10.24.0.2) after
this step — confirming Gi0/2 is participating.

### Task 3: Configure R4 as an EIGRP Stub (Connected)

- Apply `eigrp stub connected` in R4's IPv4 AF.
- Apply the same in R4's IPv6 AF.

**Verification:** On R2, `show ip eigrp neighbors detail` must show R4 as "Stub Peer"
advertising "Connected Routes." `show ipv6 eigrp neighbors detail` must show the same
for IPv6.

### Task 4: Summarize R3's Branch B Loopbacks

- On R3, under the IPv4 AF, configure a summary-address `10.3.0.0/22` on **both**
  Gi0/0 (toward R1) and Gi0/1 (toward R2).
- On R3, under the IPv6 AF, configure a summary-address `2001:DB8:3::/62` on Gi0/0
  and Gi0/1.

**Verification:** `show ip route eigrp` on R1 must show **one** route for
`10.3.0.0/22` — the four /24s must be absent. `show ip route` on R3 must show a
discard route `10.3.0.0/22 is directly connected, Null0` with AD 5.

### Task 5: Manipulate Bandwidth on the R2↔R3 Link

- Set `bandwidth 100000` (100 Mbps) under R2's Gi0/1 interface.
- Set `bandwidth 100000` under R3's Gi0/1 interface.
- This only affects EIGRP metric calculation — the physical link speed does not change.

**Verification:** `show interface Gi0/1 | include BW` on both R2 and R3 must show
`BW 100000 Kbit/sec`. The EIGRP composite metric for routes crossing this link
should now be noticeably higher.

### Task 6: Enable Unequal-Cost Load Balancing on R2

- Configure `variance 8` under R2's IPv4 AF.
- Configure `variance 8` under R2's IPv6 AF (so 2001:DB8:1:1::/64 also benefits).
- Rationale: the direct R2→R3 path and the indirect R2→R1→R3 path have a metric
  ratio of roughly 8:1 once the R2↔R3 bandwidth is lowered. Variance 8 installs both.

**Verification:** `show ip route 192.168.1.0` on R2 must list two EIGRP entries
(next-hops 10.12.0.1 via Gi0/0 and 10.23.0.2 via Gi0/1). `show ip eigrp topology
192.168.1.0/24` must mark both as "FD is ..." with `via` entries — the second must
be tagged as a feasible successor.

---

## 6. Verification & Analysis

### Task 1 & 2 — R4 Joined, Full Neighbor Table

```bash
R2# show ip eigrp neighbors
EIGRP-IPv4 VR(EIGRP-LAB) Address-Family Neighbors for AS(100)
H   Address         Interface       Hold  Uptime   SRTT   RTO  Q  Seq
                                   (sec)           (ms)       Cnt Num
0   10.24.0.2       Gi0/2             13  00:00:45    5   100  0  7    ! <- R4, new neighbor
1   10.12.0.1       Gi0/0             12  00:35:20    8   100  0  14
2   10.23.0.2       Gi0/1             11  00:35:18    6   100  0  18

R2# show ipv6 eigrp neighbors
EIGRP-IPv6 VR(EIGRP-LAB) Address-Family Neighbors for AS(100)
H   Address                  Interface    Hold Uptime   SRTT   RTO  Q  Seq
0   Link-local address:
     FE80::4                 Gi0/2          14 00:00:44    7   100  0  5   ! <- R4 IPv6
1   Link-local address:
     FE80::1                 Gi0/0          13 00:35:18    9   100  0  11
2   Link-local address:
     FE80::3                 Gi0/1          12 00:35:16    8   100  0  14
```

### Task 3 — R4 Is a Stub Peer

```bash
R2# show ip eigrp neighbors detail
EIGRP-IPv4 VR(EIGRP-LAB) Address-Family Neighbors for AS(100)
H   Address         Interface       Hold  Uptime   SRTT   RTO  Q  Seq
                                   (sec)           (ms)       Cnt Num
0   10.24.0.2       Gi0/2             14  00:02:33    5   100  0  12
   Version 23.0/2.0, Retrans: 0, Retries: 0, Prefixes: 2
   Topology-ids from peer - 0
   Stub Peer Advertising ( CONNECTED ) Routes                    ! <- R4 is stub
   Suppressing queries
```

Without the stub, the detail block would show only `Version`, `Retrans`, `Prefixes`
lines — no "Stub Peer" line.

### Task 4 — Summary On, Specifics Suppressed, Discard Route On R3

```bash
R1# show ip route eigrp | include 10.3
D        10.3.0.0/22 [90/3328] via 10.13.0.2, 00:00:15, GigabitEthernet0/1   ! <- summary, not /24s

R1# show ipv6 route eigrp | include 2001:DB8:3
D   2001:DB8:3::/62 [90/3328]
     via FE80::3, GigabitEthernet0/1                                         ! <- IPv6 summary

R3# show ip route | include Null0
S        10.3.0.0/22 is a summary, 00:00:42, Null0                           ! <- discard (AD 5)

R3# show ipv6 route | include Null0
S   2001:DB8:3::/62 [5/0]
     via Null0, directly connected                                           ! <- IPv6 discard
```

### Task 5 — Bandwidth Adjusted

```bash
R2# show interface Gi0/1 | include BW
  MTU 1500 bytes, BW 100000 Kbit/sec, DLY 10 usec,                           ! <- 100 Mbps
R2#
```

### Task 6 — Two Paths Installed On R2

```bash
R2# show ip route 192.168.1.0
Routing entry for 192.168.1.0/24
  Known via "eigrp 100", distance 90, metric 3328, type internal
  Redistributing via eigrp 100
  Last update from 10.23.0.2 on GigabitEthernet0/1, 00:01:25 ago
  Routing Descriptor Blocks:
  * 10.12.0.1, from 10.12.0.1, 00:01:25 ago, via GigabitEthernet0/0           ! <- successor
      Route metric is 3328, traffic share count is 20
      Total delay is 30 microseconds, minimum bandwidth is 1000000 Kbit
      ...
    10.23.0.2, from 10.23.0.2, 00:01:25 ago, via GigabitEthernet0/1           ! <- feasible succ
      Route metric is 26112, traffic share count is 3
      Total delay is 20 microseconds, minimum bandwidth is 100000 Kbit
      ...

R2# show ip eigrp topology 192.168.1.0/24
EIGRP-IPv4 VR(EIGRP-LAB) Topology Entry for AS(100)/ID(2.2.2.2) for 192.168.1.0/24
  State is Passive, Query origin flag is 1, 2 Successor(s), FD is 3328        ! <- 2 successors
  Descriptor Blocks:
  10.12.0.1 (GigabitEthernet0/0), from 10.12.0.1, Send flag is 0x0
      Composite metric is (3328/2816), route is Internal                       ! <- FD/AD
  10.23.0.2 (GigabitEthernet0/1), from 10.23.0.2, Send flag is 0x0
      Composite metric is (26112/2816), route is Internal                      ! <- FS, FC ok
```

Traffic-share count is proportional to inverse metric. Both paths install because
FD 26112 < 8 × 3328 = 26624, and the feasible successor's AD (2816) is less than the
successor's FD (3328).

### End-to-End Reachability

```bash
PC1> ping 192.168.2.10
84 bytes from 192.168.2.10 icmp_seq=1 ttl=61 time=2.050 ms               ! <- PC1 <-> PC2 works

PC1> ping 2001:db8:2:2::10
84 bytes from 2001:db8:2:2::10 icmp_seq=1 ttl=61 time=2.100 ms           ! <- IPv6 end-to-end
```

---

## 7. Verification Cheatsheet

### Stub Configuration

```
router eigrp NAME
 address-family ipv4 unicast autonomous-system N
  eigrp stub <connected | static | summary | receive-only | redistributed>
```

| Command | Purpose |
|---------|---------|
| `eigrp stub connected` | Advertise only connected prefixes; do not accept queries |
| `eigrp stub receive-only` | Listen only — advertise nothing |
| `eigrp stub connected static` | Combine connected + static (mix-and-match) |

> **Exam tip:** `eigrp stub` must be applied in **both** AFs for dual-stack. IPv4 stub
> does not affect the IPv6 AF.

### Summarization (Manual)

```
router eigrp NAME
 address-family ipv4 unicast autonomous-system N
  af-interface INTERFACE
   summary-address A.B.C.D M.M.M.M [admin-distance]
 address-family ipv6 unicast autonomous-system N
  af-interface INTERFACE
   summary-address PREFIX/LEN [admin-distance]
```

| Command | Purpose |
|---------|---------|
| `summary-address 10.3.0.0 255.255.252.0` | Advertise /22 summary, suppress specifics out this interface (IPv4) |
| `summary-address 2001:DB8:3::/62` | IPv6 summary, prefix-length notation |
| `summary-address ... 250` | Tune AD of the local discard route to 250 |

> **Exam tip:** The `summary-address` in named mode lives under `af-interface`, not
> classic-mode's `ip summary-address eigrp AS ...` under the interface. Do not mix.

### Variance and Bandwidth

```
router eigrp NAME
 address-family ipv4 unicast autonomous-system N
  variance <1-128>

interface INTERFACE
 bandwidth <Kbps>
 delay <tens of microseconds>
```

| Command | Purpose |
|---------|---------|
| `variance 8` | Install FS paths whose metric < 8× successor metric |
| `variance 1` | Default — equal-cost only |
| `bandwidth 100000` | Tell EIGRP the link is 100 Mbps (does not change the physical speed) |
| `delay 1000` | Add 10,000 microseconds of delay to EIGRP's metric |

> **Exam tip:** Variance installs **only feasible successors**. If FC fails, the
> alternate path will NOT install no matter how high variance is set.

### Verification Commands

| Command | What to Look For |
|---------|-----------------|
| `show ip eigrp neighbors` | All expected neighbors present, Hold/Uptime reasonable |
| `show ip eigrp neighbors detail` | "Stub Peer" line for stub neighbors + "Suppressing queries" |
| `show ip route eigrp` | Summary prefix present; more-specifics absent at receiver |
| `show ip route A.B.C.D` | Multiple "Routing Descriptor Blocks" = ECMP/UCMP installed |
| `show ip eigrp topology PREFIX` | Successor + FS with (FD/AD) tuples; FC holds when AD < FD |
| `show ip eigrp topology all-links` | See successors AND non-feasible alternatives in one view |
| `show ip route \| include Null0` | Summary discard route; confirms local summarization |
| `show interface INT \| include BW` | Current EIGRP-visible bandwidth |
| `show ip protocols` | AS, router-id, variance multiplier, metric weights |
| `show ipv6 eigrp neighbors detail` | IPv6 stub/AF info (separate tree from IPv4) |

### Wildcard Mask Quick Reference

| Subnet Mask | Wildcard Mask | Common Use |
|-------------|---------------|------------|
| 255.255.255.252 (/30) | 0.0.0.3 | Point-to-point links |
| 255.255.255.0 (/24) | 0.0.0.255 | LAN segment |
| 255.255.252.0 (/22) | 0.0.3.255 | Aggregate of 4 /24s |
| 255.255.255.255 (/32) | 0.0.0.0 | Single loopback or host |

### Common EIGRP Advanced-Feature Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| Summary not advertised | `summary-address` placed under wrong interface or wrong AF |
| More-specifics still seen by neighbor | `summary-address` missing on that egress interface |
| No feasible successor (variance ignored) | FC fails — alternate's AD ≥ successor's FD |
| Stub flag missing on neighbor | `eigrp stub` not configured in the matching AF |
| Hub still sends queries to stub | Stub command placed outside the address-family in named mode |
| Variance installs no extras | Default `variance 1` left in place, or no FS exists |
| Bandwidth change ignored | Applied only to one side of the link — must set on both ends for symmetric cost |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Task 1: Join R4 to the EIGRP Domain

<details>
<summary>Click to view R4 EIGRP Core Configuration</summary>

```bash
! R4
ipv6 unicast-routing
router eigrp EIGRP-LAB
 address-family ipv4 unicast autonomous-system 100
  af-interface GigabitEthernet0/1
   passive-interface
  exit-af-interface
  eigrp router-id 4.4.4.4
  network 4.4.4.4 0.0.0.0
  network 10.24.0.0 0.0.0.3
  network 192.168.2.0 0.0.0.255
 exit-address-family
 address-family ipv6 unicast autonomous-system 100
  af-interface GigabitEthernet0/1
   passive-interface
  exit-af-interface
  eigrp router-id 4.4.4.4
 exit-address-family
```
</details>

### Task 2: Enroll R2's Gi0/2 in EIGRP

<details>
<summary>Click to view R2 Network Statement</summary>

```bash
! R2
router eigrp EIGRP-LAB
 address-family ipv4 unicast autonomous-system 100
  network 10.24.0.0 0.0.0.3
 exit-address-family
```
</details>

### Task 3: R4 as EIGRP Stub (Connected)

<details>
<summary>Click to view R4 Stub Configuration</summary>

```bash
! R4
router eigrp EIGRP-LAB
 address-family ipv4 unicast autonomous-system 100
  eigrp stub connected
 exit-address-family
 address-family ipv6 unicast autonomous-system 100
  eigrp stub connected
 exit-address-family
```
</details>

### Task 4: R3 Summarization

<details>
<summary>Click to view R3 Summarization Configuration</summary>

```bash
! R3
router eigrp EIGRP-LAB
 address-family ipv4 unicast autonomous-system 100
  af-interface GigabitEthernet0/0
   summary-address 10.3.0.0 255.255.252.0
  exit-af-interface
  af-interface GigabitEthernet0/1
   summary-address 10.3.0.0 255.255.252.0
  exit-af-interface
 exit-address-family
 address-family ipv6 unicast autonomous-system 100
  af-interface GigabitEthernet0/0
   summary-address 2001:DB8:3::/62
  exit-af-interface
  af-interface GigabitEthernet0/1
   summary-address 2001:DB8:3::/62
  exit-af-interface
 exit-address-family
```
</details>

### Task 5: Bandwidth Manipulation on R2↔R3

<details>
<summary>Click to view R2 and R3 Interface Bandwidth</summary>

```bash
! R2
interface GigabitEthernet0/1
 bandwidth 100000

! R3
interface GigabitEthernet0/1
 bandwidth 100000
```
</details>

### Task 6: Variance on R2

<details>
<summary>Click to view R2 Variance Configuration</summary>

```bash
! R2
router eigrp EIGRP-LAB
 address-family ipv4 unicast autonomous-system 100
  variance 8
 exit-address-family
 address-family ipv6 unicast autonomous-system 100
  variance 8
 exit-address-family
```
</details>

<details>
<summary>Click to view Full Verification Command List</summary>

```bash
show ip eigrp neighbors
show ip eigrp neighbors detail
show ipv6 eigrp neighbors detail
show ip route eigrp
show ipv6 route eigrp
show ip route 192.168.1.0
show ip eigrp topology 192.168.1.0/24
show ip eigrp topology all-links
show ip route | include Null0
show interface Gi0/1 | include BW
show ip protocols
```
</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. Inject the fault first, then diagnose and
fix using only show commands.

### Workflow

```bash
python3 setup_lab.py                                   # reset to known-good
python3 scripts/fault-injection/inject_scenario_01.py  # Ticket 1
python3 scripts/fault-injection/apply_solution.py      # restore
```

---

### Ticket 1 — Hub Sees R4 but Keeps Sending Queries Down the Spoke

Operations is investigating SIA alarms around the logistics depot. `show ip eigrp
neighbors detail` on R2 shows R4 as a standard peer — the stub designation has
disappeared.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py`

**Success criteria:** R2's `show ip eigrp neighbors detail` for R4 shows
`Stub Peer Advertising (CONNECTED) Routes` and `Suppressing queries`.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. On R4: `show ip protocols` — look for the stub line. If absent, stub is missing.
2. On R4: `show running-config | section router eigrp` — confirm `eigrp stub
   connected` is present inside **each** address-family.
3. On R2: `show ip eigrp neighbors detail` — the "Stub Peer" line is only printed
   when R4 advertises the stub TLV in its hellos.
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! R4
router eigrp EIGRP-LAB
 address-family ipv4 unicast autonomous-system 100
  eigrp stub connected
 exit-address-family
 address-family ipv6 unicast autonomous-system 100
  eigrp stub connected
 exit-address-family
```
</details>

---

### Ticket 2 — Core Routers Still See Four /24 Routes Instead of the Summary

A junior engineer was asked to reduce the core routing-table footprint. R1 and R2
still show four 10.3.X.0/24 routes instead of a single 10.3.0.0/22 entry. The
business apps are reachable, but the summarization objective was not met.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py`

**Success criteria:** `show ip route eigrp | include 10.3` on R1 shows **one**
summary `10.3.0.0/22`. `show ip route | include Null0` on R3 shows a summary
discard route.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. On R3: `show running-config | section router eigrp` — confirm `summary-address`
   is present under `af-interface GigabitEthernet0/0` AND `af-interface
   GigabitEthernet0/1`. Missing on either side means the neighbor on that side still
   sees the /24s.
2. On R1: `show ip route eigrp` — if four /24s appear, R3's Gi0/0 summary is
   missing.
3. On R2: `show ip route eigrp` — if four /24s appear, R3's Gi0/1 summary is
   missing.
4. On R3: `show ip route | include Null0` — confirm the discard route; its absence
   means the summary-address command was never accepted.
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! R3
router eigrp EIGRP-LAB
 address-family ipv4 unicast autonomous-system 100
  af-interface GigabitEthernet0/0
   summary-address 10.3.0.0 255.255.252.0
  exit-af-interface
  af-interface GigabitEthernet0/1
   summary-address 10.3.0.0 255.255.252.0
  exit-af-interface
 exit-address-family
```
</details>

---

### Ticket 3 — Branch A Still Routes Everything Through R1 Despite "Variance 8"

An engineer noticed the R2↔R3 100 Mbps link is idle during peak hours. They
configured `variance 8` on R2 to split traffic across both paths, but
`show ip route 192.168.1.0` still lists only one next-hop (10.12.0.1 via R1). No
extra path installed.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py`

**Success criteria:** `show ip route 192.168.1.0` on R2 lists **two** "Routing
Descriptor Blocks" — 10.12.0.1 (successor via R1) and 10.23.0.2 (feasible successor
via R3). `show ip eigrp topology 192.168.1.0/24` shows "2 Successor(s)".

<details>
<summary>Click to view Diagnosis Steps</summary>

1. On R2: `show ip protocols` — confirm `variance` line shows `8` (not `1`). If the
   config was applied in the wrong AF or pasted in top-level router scope, variance
   stays 1.
2. On R2: `show ip eigrp topology 192.168.1.0/24` — is the direct R2→R3 path listed
   at all? If not, bandwidth or interface changes have eliminated even the topology
   entry.
3. On R2/R3: `show interface Gi0/1 | include BW` — confirm the bandwidth reduction
   was applied on BOTH ends. A one-sided change creates asymmetric metric
   calculations that may keep FC from holding.
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! R2
router eigrp EIGRP-LAB
 address-family ipv4 unicast autonomous-system 100
  variance 8
 exit-address-family
 address-family ipv6 unicast autonomous-system 100
  variance 8
 exit-address-family

interface GigabitEthernet0/1
 bandwidth 100000

! R3 (bandwidth symmetric)
interface GigabitEthernet0/1
 bandwidth 100000
```
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] R4 joined the EIGRP named-mode domain (IPv4 + IPv6 AFs, AS 100)
- [ ] R4 Gi0/1 (PC2 LAN) is passive in both AFs
- [ ] R2 Gi0/2 is enrolled in EIGRP IPv4 AF (network 10.24.0.0 0.0.0.3)
- [ ] R4 configured as `eigrp stub connected` in both AFs
- [ ] R2 detail output shows R4 as "Stub Peer" suppressing queries (IPv4 and IPv6)
- [ ] R3 summary-address 10.3.0.0/22 on Gi0/0 and Gi0/1 (IPv4 AF)
- [ ] R3 summary-address 2001:DB8:3::/62 on Gi0/0 and Gi0/1 (IPv6 AF)
- [ ] R1 and R2 see the /22 summary; the four /24s are absent
- [ ] Discard (Null0) route on R3 exists for both IPv4 and IPv6 summaries
- [ ] R2 Gi0/1 and R3 Gi0/1 both report `BW 100000 Kbit/sec`
- [ ] R2 `variance 8` applied in both AFs
- [ ] R2 routing table lists both paths for 192.168.1.0/24 with unequal traffic share
- [ ] PC1 ↔ PC2 end-to-end ping works (IPv4 and IPv6)

### Troubleshooting

- [ ] Ticket 1 (stub missing) diagnosed and fixed
- [ ] Ticket 2 (summary missing) diagnosed and fixed
- [ ] Ticket 3 (variance not installing FS) diagnosed and fixed
