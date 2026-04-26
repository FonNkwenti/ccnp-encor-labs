# Lab 03 — EIGRP Full Protocol Mastery (Capstone I)

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

**Exam Objective:** 3.2.a — Compare EIGRP and OSPF (advanced distance-vector, DUAL, metrics, load balancing, path selection, stub)

This is the **EIGRP capstone configuration lab**. Every protocol feature exercised in
labs 00–02 must be rebuilt from scratch on top of a fresh IP/IPv6 plan. The routers
boot with only addressing configured — no EIGRP process, no summaries, no stubs, no
variance. You, the engineer, build the full dual-stack EIGRP domain to the production
specification.

### Named-Mode Dual-Stack EIGRP

All configuration lives under a single named process (`EIGRP-LAB`), with IPv4 and IPv6
address families each owning their own AS (100), router-id, network statements, and
per-interface controls. Classic-mode syntax (`router eigrp 100` followed by `network`
statements at the top level) is **not** acceptable for this build.

```
router eigrp NAME
 address-family ipv4 unicast autonomous-system N
  eigrp router-id A.B.C.D
  network ...
 address-family ipv6 unicast autonomous-system N
  eigrp router-id A.B.C.D
```

Named mode unlocks per-AF tuning: stub, summary-address, variance, and passive-interface
are all configurable separately for IPv4 and IPv6.

### Stub Routing (Query Scope Control)

A stub router advertises a limited set of prefixes and signals to its hub that it is
**not a transit path** — the hub stops sending EIGRP queries to it. This is how
hub-and-spoke networks prevent stuck-in-active (SIA) events at scale. In named mode,
`eigrp stub <option>` lives inside each address-family.

### Manual Summarization (Topology Hiding)

Per-interface `summary-address` under `af-interface` advertises an aggregate prefix
and suppresses the more-specifics out that interface. A Null0 discard route with AD 5
is auto-installed on the summarizing router. IPv4 uses dotted-quad mask syntax; IPv6
uses prefix-length notation.

### Unequal-Cost Load Balancing (Variance)

`variance N` under an address family tells DUAL to install any feasible successor
whose metric is less than N × successor_metric. Only **feasible successors** qualify —
alternates whose advertised distance is greater than or equal to the local feasible
distance cannot install (the Feasibility Condition).

### Bandwidth Manipulation

EIGRP's composite metric is driven by the **minimum bandwidth** along the path. The
`bandwidth` interface command changes what EIGRP believes about link speed (the
physical rate is unchanged). This is how you engineer metric asymmetry to
deliberately create feasible-successor opportunities for variance.

### Passive Interfaces

LAN-facing interfaces must not form EIGRP adjacencies with hosts. `passive-interface`
under `af-interface` stops hello packets out the interface while still letting its
subnet be advertised. Apply in **both** AFs on dual-stack LAN links.

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| End-to-end EIGRP deployment | Stand up a complete dual-stack EIGRP domain with no starter config |
| Named-mode configuration | Build IPv4 and IPv6 address families under one named process |
| Stub-router design | Identify the stub role and configure `eigrp stub connected` in both AFs |
| Route summarization | Place `summary-address` on the correct egress interfaces to hide specifics |
| Metric engineering | Use `bandwidth` to create an asymmetric path for the variance demo |
| Variance tuning | Select a variance multiplier that satisfies the metric ratio |
| Passive-interface hygiene | Suppress hellos on every LAN-facing segment in both AFs |
| Verification methodology | Prove convergence with `show ip eigrp neighbors`, `topology`, `route eigrp` |

---

## 2. Topology & Scenario

Meridian Logistics is migrating its regional backbone to a fresh set of IOSv
appliances. Network Engineering has handed you a **clean pull of the IP plan** —
addressing is pre-staged, but every protocol feature (EIGRP process, dual-stack,
stub, summarization, bandwidth asymmetry, variance, passive interfaces) must be
rebuilt. The design specification below is the target state; you choose the
implementation order.

**Design requirements:**

1. One dual-stack named process (`EIGRP-LAB`, AS 100) across R1, R2, R3, R4.
2. Router-IDs match Loopback0 (R1=1.1.1.1, R2=2.2.2.2, R3=3.3.3.3, R4=4.4.4.4).
3. R4 is the stub (connected) — only advertises its own prefixes; the hub stops
   querying it.
4. R3 summarizes its four Branch B loopbacks as `10.3.0.0/22` (and
   `2001:DB8:3::/62`) on **both** uplinks (toward R1 and toward R2).
5. The R2↔R3 base of the triangle is a 100 Mbps circuit — bandwidth on both ends
   must reflect that (100,000 Kbps). All other links are 1 Gbps.
6. R2 uses `variance 8` to install both the direct R2→R3 path and the feasible
   R2→R1→R3 path for the 192.168.1.0/24 / 2001:DB8:1:1::/64 destinations.
7. All LAN-facing interfaces (R3 Gi0/3, R4 Gi0/1) are passive in both AFs.
8. End-to-end IPv4 **and** IPv6 reachability between PC1 and PC2.

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
| R4 | IOSv 15.7 | Stub spoke — PC2 LAN |
| PC1 | VPCS | End host on R3 LAN |
| PC2 | VPCS | End host on R4 LAN |

### Cabling

| Link | Endpoint A | Endpoint B | IPv4 | IPv6 |
|------|-----------|-----------|------|------|
| L1 | R1 Gi0/0 | R2 Gi0/0 | 10.12.0.0/30 | 2001:DB8:12::/64 |
| L2 | R1 Gi0/1 | R3 Gi0/0 | 10.13.0.0/30 | 2001:DB8:13::/64 |
| L3 | R2 Gi0/1 | R3 Gi0/1 | 10.23.0.0/30 | 2001:DB8:23::/64 |
| L4 | R3 Gi0/3 | PC1 e0 | 192.168.1.0/24 | 2001:DB8:1:1::/64 |
| L5 | R2 Gi0/2 | R4 Gi0/0 | 10.24.0.0/30 | 2001:DB8:24::/64 |
| L6 | R4 Gi0/1 | PC2 e0 | 192.168.2.0/24 | 2001:DB8:2:2::/64 |

L3 is the bandwidth-manipulated link — 100 Mbps — driving the variance demo.

### Console Access Table

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

The `initial-configs/` folder contains the **clean-slate** starting state. Only IP
addressing is pre-configured; all EIGRP protocol work is yours.

### Pre-loaded on every router

- Hostname, `no ip domain-lookup`, `ipv6 unicast-routing`
- All interface IPv4 + IPv6 addressing (including link-local `FE80::N`)
- All transit interfaces in `no shutdown` state
- Loopback0 (router-id source): 1.1.1.1 / 2.2.2.2 / 3.3.3.3 / 4.4.4.4

### Pre-loaded on R3

- Loopback1–4 with `10.3.0-3.1/24` plus `2001:DB8:3:0-3::1/64` (available to summarize)
- PC1 LAN on Gi0/3: `192.168.1.1/24` + `2001:DB8:1:1::1/64`

### Pre-loaded on R2

- Gi0/2 toward R4 already addressed (`10.24.0.1/30` + `2001:DB8:24::1/64`) and up

### Pre-loaded on R4

- Gi0/0 toward R2 (`10.24.0.2/30` + `2001:DB8:24::2/64`) and Gi0/1 toward PC2
  (`192.168.2.1/24` + `2001:DB8:2:2::1/64`)

### NOT pre-loaded (student tasks)

- EIGRP named-mode process on any router
- IPv4 address-family (AS, router-id, networks)
- IPv6 address-family (AS, router-id)
- Stub configuration on R4
- Summary-address on R3 (both AFs, both uplinks)
- Bandwidth manipulation on the R2↔R3 link (both ends)
- Variance multiplier on R2 (both AFs)
- Passive-interface on LAN segments (R3 Gi0/3, R4 Gi0/1)

---

## 5. Lab Challenge: Full Protocol Mastery

> This is a capstone lab. No step-by-step guidance is provided.
> Configure the complete EIGRP solution from scratch — IP addressing is pre-configured; everything else is yours to build.
> All blueprint bullets for this chapter must be addressed.

**Design specification to hit:**

- Named-mode process `EIGRP-LAB`, AS 100, on R1/R2/R3/R4
- Dual-stack address families (IPv4 and IPv6) with explicit router-ids
- R4 configured as `eigrp stub connected` in both AFs
- R3 advertises `10.3.0.0/22` and `2001:DB8:3::/62` summaries on Gi0/0 **and** Gi0/1
- R2 Gi0/1 and R3 Gi0/1 both configured for `bandwidth 100000` (100 Mbps)
- R2 `variance 8` in both AFs (installs the feasible successor for PC1's LAN)
- Passive-interface on every LAN-facing interface in both AFs
- Verified IPv4 + IPv6 reachability PC1 ↔ PC2

Plan your configuration order (hint: build adjacency first, then stub, then summary,
then metric/variance — layer features on top of a working base). Do not peek at
Section 8 until you have tried to build it.

---

## 6. Verification & Analysis

Use these expected outputs as your "known-good" reference. Each code block marks the
exact line or value you must confirm with an inline `!` comment.

### Named-Mode Neighbor Tables

```bash
R1# show ip eigrp neighbors
EIGRP-IPv4 VR(EIGRP-LAB) Address-Family Neighbors for AS(100)
H   Address         Interface       Hold  Uptime   SRTT   RTO  Q  Seq
0   10.12.0.2       Gi0/0             13  00:05:01    5   100  0  22   ! <- R2 reachable
1   10.13.0.2       Gi0/1             14  00:05:00    6   100  0  18   ! <- R3 reachable

R2# show ip eigrp neighbors
EIGRP-IPv4 VR(EIGRP-LAB) Address-Family Neighbors for AS(100)
0   10.24.0.2       Gi0/2             12  00:04:55    5   100  0  7    ! <- R4 (stub)
1   10.12.0.1       Gi0/0             11  00:05:02    8   100  0  14   ! <- R1
2   10.23.0.2       Gi0/1             13  00:05:00    6   100  0  12   ! <- R3

R2# show ipv6 eigrp neighbors
EIGRP-IPv6 VR(EIGRP-LAB) Address-Family Neighbors for AS(100)
0   Link-local address:
     FE80::4                 Gi0/2    14  00:04:53    7   100  0  5    ! <- R4 IPv6
1   Link-local address:
     FE80::1                 Gi0/0    13  00:05:00    9   100  0  11   ! <- R1 IPv6
2   Link-local address:
     FE80::3                 Gi0/1    12  00:04:59    8   100  0  14   ! <- R3 IPv6
```

### R4 Is a Stub Peer

```bash
R2# show ip eigrp neighbors detail
H   Address         Interface       Hold  Uptime   SRTT   RTO  Q  Seq
0   10.24.0.2       Gi0/2             14  00:02:33    5   100  0  12
   Version 23.0/2.0, Retrans: 0, Retries: 0, Prefixes: 2
   Stub Peer Advertising ( CONNECTED ) Routes                    ! <- stub confirmed
   Suppressing queries                                           ! <- query scoping on
```

### Summarization On Both Uplinks, Discards On R3

```bash
R1# show ip route eigrp | include 10.3
D        10.3.0.0/22 [90/3328] via 10.13.0.2, 00:01:15, Gi0/1    ! <- single summary

R2# show ip route eigrp | include 10.3
D        10.3.0.0/22 [90/...] via 10.12.0.1, 00:01:15, Gi0/0     ! <- summary via R1
                                                                   !    (stub path; no FS here)

R3# show ip route | include Null0
S        10.3.0.0/22 is a summary, 00:01:22, Null0                ! <- IPv4 discard (AD 5)

R3# show ipv6 route | include Null0
S   2001:DB8:3::/62 [5/0]
     via Null0, directly connected                                ! <- IPv6 discard
```

### Bandwidth Asymmetry

```bash
R2# show interface Gi0/1 | include BW
  MTU 1500 bytes, BW 100000 Kbit/sec, DLY 10 usec,                ! <- R2 side 100 Mbps

R3# show interface Gi0/1 | include BW
  MTU 1500 bytes, BW 100000 Kbit/sec, DLY 10 usec,                ! <- R3 side 100 Mbps
```

### Variance: Two Paths For PC1's LAN On R2

```bash
R2# show ip route 192.168.1.0
Routing entry for 192.168.1.0/24
  Known via "eigrp 100", distance 90, metric 3328, type internal
  Routing Descriptor Blocks:
  * 10.12.0.1, from 10.12.0.1, 00:01:25 ago, via Gi0/0
      Route metric is 3328, traffic share count is 20             ! <- successor (R1 path)
      minimum bandwidth is 1000000 Kbit
    10.23.0.2, from 10.23.0.2, 00:01:25 ago, via Gi0/1
      Route metric is 26112, traffic share count is 3             ! <- FS (direct R3 path)
      minimum bandwidth is 100000 Kbit

R2# show ip eigrp topology 192.168.1.0/24
  State is Passive, Query origin flag is 1, 2 Successor(s), FD is 3328   ! <- 2 successors
  10.12.0.1 (Gi0/0)
      Composite metric is (3328/2816), route is Internal          ! <- FD 3328, AD 2816
  10.23.0.2 (Gi0/1)
      Composite metric is (26112/2816), route is Internal         ! <- FC holds (2816<3328)
```

### End-to-End Reachability

```bash
PC1> ping 192.168.2.10
84 bytes from 192.168.2.10 icmp_seq=1 ttl=61 time=2.050 ms        ! <- IPv4 PC1 <-> PC2

PC1> ping 2001:db8:2:2::10
84 bytes from 2001:db8:2:2::10 icmp_seq=1 ttl=61 time=2.100 ms    ! <- IPv6 PC1 <-> PC2
```

---

## 7. Verification Cheatsheet

### Named-Mode Process

```
router eigrp NAME
 address-family ipv4 unicast autonomous-system N
  eigrp router-id A.B.C.D
  network A.B.C.D WILDCARD
 address-family ipv6 unicast autonomous-system N
  eigrp router-id A.B.C.D
```

| Command | Purpose |
|---------|---------|
| `router eigrp NAME` | Create or enter named process NAME |
| `address-family ipv4 unicast autonomous-system N` | Enter IPv4 AF for AS N |
| `address-family ipv6 unicast autonomous-system N` | Enter IPv6 AF for AS N |
| `eigrp router-id A.B.C.D` | Explicit router-id (per AF) |
| `network A.B.C.D WILDCARD` | Enroll matching interfaces in the IPv4 AF |

> **Exam tip:** IPv6 AF enrolls interfaces automatically — no `network` statement is
> needed in the IPv6 address-family.

### Stub / Summary / Passive

```
 address-family ipv4 unicast autonomous-system N
  af-interface INTERFACE
   passive-interface
   summary-address A.B.C.D M.M.M.M [AD]
  eigrp stub connected
```

| Command | Purpose |
|---------|---------|
| `eigrp stub connected` | Advertise connected only; hub suppresses queries |
| `summary-address 10.3.0.0 255.255.252.0` | Advertise /22 summary, suppress specifics (IPv4) |
| `summary-address 2001:DB8:3::/62` | IPv6 summary, prefix-length notation |
| `passive-interface` | Suppress hellos on this AF-interface; prefix still advertised |

> **Exam tip:** `summary-address` in named mode lives under `af-interface` (not under
> the physical interface as in classic mode with `ip summary-address eigrp ...`).

### Variance and Bandwidth

```
 address-family ipv4 unicast autonomous-system N
  variance <1-128>

interface INTERFACE
 bandwidth <Kbps>
```

| Command | Purpose |
|---------|---------|
| `variance 8` | Install feasible successors up to 8× the successor metric |
| `bandwidth 100000` | Tell EIGRP the link is 100 Mbps (does not change PHY speed) |

> **Exam tip:** Variance installs only feasible successors. If the alternate's
> advertised distance ≥ the successor's feasible distance, the FC fails and the
> path cannot install, regardless of variance value.

### Verification Commands

| Command | What to Look For |
|---------|-----------------|
| `show ip eigrp neighbors` | Every expected IPv4 neighbor present, Uptime growing |
| `show ipv6 eigrp neighbors` | Every expected IPv6 neighbor present |
| `show ip eigrp neighbors detail` | "Stub Peer" + "Suppressing queries" on stub neighbors |
| `show ip route eigrp` | Summary prefix visible; more-specifics absent at receiver |
| `show ip eigrp topology PREFIX` | Successor + FS with (FD/AD); FC holds when AD < FD |
| `show ip route \| include Null0` | Local discard route for each summary |
| `show interface INT \| include BW` | EIGRP-visible bandwidth on the interface |
| `show ip protocols` | AS, router-id, variance multiplier |
| `ping / ping ipv6` | End-to-end reachability PC1 ↔ PC2 |

### Wildcard Mask Quick Reference

| Subnet Mask | Wildcard Mask | Common Use |
|-------------|---------------|------------|
| 255.255.255.252 (/30) | 0.0.0.3 | Point-to-point links |
| 255.255.255.0 (/24) | 0.0.0.255 | LAN segment |
| 255.255.252.0 (/22) | 0.0.3.255 | Aggregate of 4 /24s |
| 255.255.255.255 (/32) | 0.0.0.0 | Single loopback or host |

### Common EIGRP Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| Neighbor missing | AS mismatch, passive-interface on transit link, ACL blocking multicast, no `network` match (IPv4) |
| Summary not seen at neighbor | `summary-address` missing on that egress interface or wrong AF |
| No feasible successor (variance idle) | FC fails — alternate's AD ≥ successor's FD |
| Stub flag absent | `eigrp stub` placed outside the address-family (named mode) |
| Bandwidth change ignored | Applied on only one side of the link; always configure symmetrically |
| Variance stays at 1 | Applied in wrong AF or at top-level router scope |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the capstone without looking at these first!

### R1 — Hub (core process, no special features)

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1
router eigrp EIGRP-LAB
 address-family ipv4 unicast autonomous-system 100
  eigrp router-id 1.1.1.1
  network 1.1.1.1 0.0.0.0
  network 10.12.0.0 0.0.0.3
  network 10.13.0.0 0.0.0.3
 exit-address-family
 address-family ipv6 unicast autonomous-system 100
  eigrp router-id 1.1.1.1
 exit-address-family
```
</details>

### R2 — Variance Point and Bandwidth Asymmetry

<details>
<summary>Click to view R2 Configuration</summary>

```bash
! R2
interface GigabitEthernet0/1
 bandwidth 100000

router eigrp EIGRP-LAB
 address-family ipv4 unicast autonomous-system 100
  eigrp router-id 2.2.2.2
  variance 8
  network 2.2.2.2 0.0.0.0
  network 10.12.0.0 0.0.0.3
  network 10.23.0.0 0.0.0.3
  network 10.24.0.0 0.0.0.3
 exit-address-family
 address-family ipv6 unicast autonomous-system 100
  eigrp router-id 2.2.2.2
  variance 8
 exit-address-family
```
</details>

### R3 — Summarization + Bandwidth + Passive LAN

<details>
<summary>Click to view R3 Configuration</summary>

```bash
! R3
interface GigabitEthernet0/1
 bandwidth 100000

router eigrp EIGRP-LAB
 address-family ipv4 unicast autonomous-system 100
  af-interface GigabitEthernet0/0
   summary-address 10.3.0.0 255.255.252.0
  exit-af-interface
  af-interface GigabitEthernet0/1
   summary-address 10.3.0.0 255.255.252.0
  exit-af-interface
  af-interface GigabitEthernet0/3
   passive-interface
  exit-af-interface
  eigrp router-id 3.3.3.3
  network 3.3.3.3 0.0.0.0
  network 10.3.0.0 0.0.3.255
  network 10.13.0.0 0.0.0.3
  network 10.23.0.0 0.0.0.3
  network 192.168.1.0 0.0.0.255
 exit-address-family
 address-family ipv6 unicast autonomous-system 100
  af-interface GigabitEthernet0/0
   summary-address 2001:DB8:3::/62
  exit-af-interface
  af-interface GigabitEthernet0/1
   summary-address 2001:DB8:3::/62
  exit-af-interface
  af-interface GigabitEthernet0/3
   passive-interface
  exit-af-interface
  eigrp router-id 3.3.3.3
 exit-address-family
```
</details>

### R4 — Stub Spoke + Passive LAN

<details>
<summary>Click to view R4 Configuration</summary>

```bash
! R4
router eigrp EIGRP-LAB
 address-family ipv4 unicast autonomous-system 100
  af-interface GigabitEthernet0/1
   passive-interface
  exit-af-interface
  eigrp router-id 4.4.4.4
  eigrp stub connected
  network 4.4.4.4 0.0.0.0
  network 10.24.0.0 0.0.0.3
  network 192.168.2.0 0.0.0.255
 exit-address-family
 address-family ipv6 unicast autonomous-system 100
  af-interface GigabitEthernet0/1
   passive-interface
  exit-af-interface
  eigrp router-id 4.4.4.4
  eigrp stub connected
 exit-address-family
```
</details>

<details>
<summary>Click to view Full Verification Command List</summary>

```bash
show ip eigrp neighbors
show ipv6 eigrp neighbors
show ip eigrp neighbors detail
show ipv6 eigrp neighbors detail
show ip route eigrp
show ipv6 route eigrp
show ip route | include Null0
show ipv6 route | include Null0
show ip route 192.168.1.0
show ip eigrp topology 192.168.1.0/24
show interface Gi0/1 | include BW
show ip protocols
```
</details>

---

## 9. Troubleshooting Scenarios

Fault scripts are provided for additional practice after the build is complete. Each
ticket simulates a real-world fault — inject, diagnose with show commands, and fix.

### Workflow

```bash
python3 setup_lab.py                                   # reset to known-good (applies solutions)
python3 scripts/fault-injection/inject_scenario_01.py  # Ticket 1
python3 scripts/fault-injection/apply_solution.py      # restore
```

---

### Ticket 1 — Summary Disappears from the Core's Routing Table

After a change-window the operations team reports that R1 and R2 are again seeing
the four /24 Branch B routes instead of the single `10.3.0.0/22` summary. The
discard route on R3 has also gone missing.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py`

**Success criteria:** `show ip route eigrp | include 10.3` on R1 and R2 shows **one**
`10.3.0.0/22` entry; `show ip route | include Null0` on R3 shows the IPv4 summary
discard.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. On R3: `show running-config | section router eigrp` — confirm `summary-address
   10.3.0.0 255.255.252.0` is present under `af-interface GigabitEthernet0/0` AND
   `af-interface GigabitEthernet0/1`. Missing on either side means the neighbor on
   that side still sees the /24s.
2. On R1: `show ip route eigrp | include 10.3` — four /24s = R3 Gi0/0 summary
   missing.
3. On R2: `show ip route eigrp | include 10.3` — four /24s = R3 Gi0/1 summary
   missing.
4. On R3: `show ip route | include Null0` — absence of the summary discard route
   means neither `summary-address` command is active.
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

### Ticket 2 — Hub Keeps Querying the Logistics Depot During Flap Tests

An SRE flap-test on R3's LAN is producing SIA alarms around R4. `show ip eigrp
neighbors detail` on R2 shows R4 as a regular peer — the stub designation has
vanished.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py`

**Success criteria:** `show ip eigrp neighbors detail` on R2 shows R4 as
`Stub Peer Advertising ( CONNECTED ) Routes` with `Suppressing queries`. Same for
IPv6 (`show ipv6 eigrp neighbors detail`).

<details>
<summary>Click to view Diagnosis Steps</summary>

1. On R4: `show ip protocols` — look for the stub line under EIGRP. Absent means
   stub is missing.
2. On R4: `show running-config | section router eigrp` — confirm `eigrp stub
   connected` is present inside **each** address-family (named-mode requirement).
3. On R2: `show ip eigrp neighbors detail` — "Stub Peer" is printed only when the
   neighbor advertises the stub TLV in its hellos.
4. Cross-check IPv6: a missing IPv6 stub line means stub is configured only in
   IPv4 (easy miss on dual-stack).
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

### Ticket 3 — Branch A Variance Is Configured but Only One Path Installs

Capacity planning reports the R2↔R3 100 Mbps metro link is idle at peak. R2 still
has `variance 8` in its running-config, yet `show ip route 192.168.1.0` lists only
the R1 next-hop. The alternate path is not being installed.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py`

**Success criteria:** `show ip route 192.168.1.0` on R2 lists **two** Routing
Descriptor Blocks (via 10.12.0.1 **and** 10.23.0.2); `show ip eigrp topology
192.168.1.0/24` shows "2 Successor(s)".

<details>
<summary>Click to view Diagnosis Steps</summary>

1. On R2 and R3: `show interface Gi0/1 | include BW` — both ends must report
   `BW 100000 Kbit/sec`. A one-sided bandwidth change creates asymmetric metric
   calculations that may keep the Feasibility Condition from holding.
2. On R2: `show ip eigrp topology 192.168.1.0/24` — confirm the direct R2→R3 path
   appears. Compare `(FD/AD)` tuples; if the FS AD ≥ the successor FD, FC fails
   (variance cannot override that).
3. On R2: `show ip protocols` — confirm variance reads `8`, not `1`.
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! R2
interface GigabitEthernet0/1
 bandwidth 100000

! R3
interface GigabitEthernet0/1
 bandwidth 100000

! R2 (if variance also missing)
router eigrp EIGRP-LAB
 address-family ipv4 unicast autonomous-system 100
  variance 8
 exit-address-family
 address-family ipv6 unicast autonomous-system 100
  variance 8
 exit-address-family
```
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] Named-mode EIGRP process `EIGRP-LAB` configured on R1, R2, R3, R4
- [ ] IPv4 and IPv6 address-families under AS 100 on every router
- [ ] Router-IDs pinned: 1.1.1.1 / 2.2.2.2 / 3.3.3.3 / 4.4.4.4
- [ ] All expected IPv4 adjacencies up (`show ip eigrp neighbors`)
- [ ] All expected IPv6 adjacencies up (`show ipv6 eigrp neighbors`)
- [ ] R4 configured as `eigrp stub connected` in both AFs
- [ ] R2 detail shows R4 as "Stub Peer Advertising ( CONNECTED )" + "Suppressing queries"
- [ ] R3 `summary-address 10.3.0.0 255.255.252.0` on Gi0/0 and Gi0/1 (IPv4 AF)
- [ ] R3 `summary-address 2001:DB8:3::/62` on Gi0/0 and Gi0/1 (IPv6 AF)
- [ ] R1 and R2 see `10.3.0.0/22` (and `2001:DB8:3::/62`) — no /24s present
- [ ] Null0 discard route on R3 for IPv4 and IPv6 summaries
- [ ] R2 Gi0/1 and R3 Gi0/1 both report `BW 100000 Kbit/sec`
- [ ] R2 `variance 8` applied in both AFs
- [ ] R2 routing table lists two paths for 192.168.1.0/24 (`show ip route 192.168.1.0`)
- [ ] Passive-interface on R3 Gi0/3 and R4 Gi0/1 in both AFs
- [ ] PC1 ↔ PC2 end-to-end reachable over IPv4 and IPv6

### Troubleshooting

- [ ] Ticket 1 (summary missing) diagnosed and fixed
- [ ] Ticket 2 (stub missing) diagnosed and fixed
- [ ] Ticket 3 (bandwidth / variance / FC) diagnosed and fixed
