# Lab 00 -- Classic EIGRP Fundamentals

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

**Exam Objective:** 350-401 blueprint bullet **3.2.a** -- Compare routing concepts of
EIGRP and OSPF (advanced distance vector vs. link state, load balancing, path selection,
path operations, metrics, and area types) -- EIGRP side.

This lab introduces EIGRP (Enhanced Interior Gateway Routing Protocol) in its original
"classic" configuration mode. You'll build a three-router triangle running EIGRP AS 100,
watch DUAL select successors and feasible successors, and learn to read the EIGRP
topology table -- the foundation that every later EIGRP feature builds on.

### EIGRP vs OSPF -- The Fundamental Difference

EIGRP is an **advanced distance-vector** protocol; OSPF is a **link-state** protocol.
That single difference drives almost everything else:

| Aspect | EIGRP | OSPF |
|---|---|---|
| Algorithm | DUAL (Diffusing Update Algorithm) | Dijkstra (SPF) |
| Router's view | Routes received from neighbors | Full link-state database |
| Update trigger | Topology change only (partial) | Flooding of LSAs |
| Metric | Composite (bandwidth + delay + ...) | Cost (based on bandwidth) |
| Convergence | Very fast (pre-computed backup) | Fast (SPF recomputation) |
| Areas | Flat by default (no areas) | Hierarchical (backbone + areas) |
| Vendor | Cisco-originated (RFC 7868) | Open standard (RFC 2328) |

EIGRP routers do not build a map of the network. Each router trusts neighbor-reported
metrics, applies the feasibility condition to guarantee loop-free paths, and stores
the results in a topology table. The best route (successor) is installed in the
routing table; a backup loop-free route (feasible successor, if one exists) is kept
ready in the topology table for instant failover.

### DUAL, Successors, and the Feasibility Condition

DUAL is the brain of EIGRP. For each destination, every router tracks two metric values
reported by each neighbor:

- **Feasible Distance (FD)** -- this router's own metric to reach the destination via
  its best neighbor (the successor).
- **Reported Distance (RD)** -- the metric the *neighbor* advertises for reaching that
  destination. This is the neighbor's own FD.

The **feasibility condition** guarantees loop-free backup paths:

> A neighbor's path qualifies as a **feasible successor** only if that neighbor's
> **RD is strictly less than** this router's current **FD** to the destination.

The intuition: if a neighbor is already *closer* to the destination than we are,
routing through them cannot create a loop back to us. The feasible successor is
pre-computed, so failover is instant -- no query, no SPF run.

```
                    ┌────────────┐
                    │     R1     │  FD to PC1 LAN = 130
                    └──┬──────┬──┘
                       │      │
                10.12  │      │ 10.13  (1 Gbps -- low delay)
                       │      │
                    ┌──┴──┐ ┌─┴───┐
                    │ R2  │ │ R3  │ ◄── directly connected
                    └──┬──┘ └──┬──┘    RD(R3) reported to R1 = 30
                       │      │
                       └──┬───┘
                       10.23 (triangle base)
```

From R1 to `192.168.1.0/24` (PC1 LAN on R3):
- **Via R3 directly:** cost is R1's FD (lowest) -- R3 is the **successor**.
- **Via R2 then R3:** cost is higher. If `RD(R2 toward PC1 LAN) < FD(R1 toward PC1 LAN)`,
  R2 qualifies as a feasible successor. (In lab-00 all links are 1 Gbps so the
  feasibility condition happens to hold here -- lab-02 tunes bandwidth to make this
  explicit.)

### Classic EIGRP vs Named Mode -- Why Lab-00 Uses Classic

EIGRP has two configuration flavors:

```
! Classic mode (lab-00)
router eigrp 100
 eigrp router-id 1.1.1.1
 network 10.12.0.0 0.0.0.3
 no auto-summary

! Named mode (lab-01 onward)
router eigrp EIGRP-LAB
 address-family ipv4 unicast autonomous-system 100
  eigrp router-id 1.1.1.1
  network 10.12.0.0 0.0.0.3
  exit-af-topology
 exit-address-family
```

Classic mode is IPv4-only, uses a 32-bit metric, and is the historical syntax that
still appears in the exam. Named mode supports IPv4 + IPv6 dual-stack, uses 64-bit
"wide metrics," and is the modern recommended approach. Lab-00 builds fluency with
the classic syntax first; lab-01 converts to named mode and adds IPv6.

### The Classic EIGRP Composite Metric

```
Metric = 256 * (BW_slowest + Delay_cumulative)

BW_slowest   = 10^7 / min(link bandwidth along path, Kbps)
Delay_cumul  = sum of (interface delay, tens-of-microseconds)
```

By default only bandwidth and delay contribute (K1=K3=1, K2=K4=K5=0). For a
GigabitEthernet interface: bandwidth = 1,000,000 Kbps, delay = 10 microseconds
(1 tens-of-microseconds). The formula produces a 32-bit integer.

> **Exam tip:** Two EIGRP neighbors must agree on AS number AND K-values or the
> adjacency never forms. A K-value mismatch is silent -- `show ip eigrp neighbors`
> simply shows no neighbor.

### Skills this lab develops

| Skill | Description |
|---|---|
| EIGRP process configuration | Enable EIGRP in classic mode with explicit router-ID |
| Network statements with wildcard masks | Advertise specific subnets rather than whole classful networks |
| Neighbor relationship verification | Read `show ip eigrp neighbors` and interpret each column |
| Topology table analysis | Identify successor and feasible successor in `show ip eigrp topology` |
| DUAL feasibility reasoning | Apply the RD < FD rule to classify a candidate route |
| Metric calculation | Compute composite metric from interface bandwidth and delay |
| Passive-interface scoping | Suppress hellos on LAN segments without losing advertisement |
| Connectivity verification | Validate end-to-end reachability with ping and traceroute |

---

## 2. Topology & Scenario

**Scenario:** You are a junior engineer at a 3-site enterprise. The network has three
routers (R1 hub, R2 branch A, R3 branch B) cabled in a triangle for redundancy. IP
addressing is already in place; you have been asked to bring up EIGRP AS 100 across
the triangle so the three sites can exchange routes and PC1 (on R3's LAN) can reach
every router loopback. Your supervisor wants this done in classic EIGRP mode today;
a dual-stack named-mode migration is on the roadmap for next sprint.

```
                           ┌─────────────────────────┐
                           │           R1            │
                           │      (Hub / Core)       │
                           │    Lo0: 1.1.1.1/32      │
                           └──────┬───────────┬──────┘
                        Gi0/0     │           │     Gi0/1
                   10.12.0.1/30   │           │   10.13.0.1/30
                                  │           │
                   10.12.0.2/30   │           │   10.13.0.2/30
                        Gi0/0     │           │     Gi0/0
                 ┌────────────────┘           └────────────────┐
                 │                                             │
            ┌────┴──────────────┐           ┌──────────────────┴────┐
            │       R2          │           │         R3            │
            │   (Branch A)      │           │     (Branch B)        │
            │  Lo0: 2.2.2.2/32  │           │   Lo0: 3.3.3.3/32     │
            └─────────┬─────────┘           └────────┬──────────┬───┘
                  Gi0/1│                         Gi0/1│     Gi0/3│
              10.23.0.1/30                    10.23.0.2/30   192.168.1.1/24
                      │                             │          │
                      └─────────────────────────────┘      ┌───┴───┐
                              10.23.0.0/30                 │  PC1  │
                           (triangle base)                 │  .10  │
                                                           └───────┘
```

### Why a triangle?

The triangle gives every destination two independent paths (R1 reaches PC1's LAN via
R3 directly, or via R2 then R3). That redundancy is exactly what DUAL needs to
demonstrate successor + feasible successor selection in later labs. Right now, with
every link at 1 Gbps and identical delay, the direct path always wins -- but the
topology table still lists the alternate path so you can see DUAL working.

---

## 3. Hardware & Environment Specifications

### Devices

| Device | Platform | Role |
|---|---|---|
| R1 | IOSv (15.x+) | Hub router -- core of the triangle |
| R2 | IOSv (15.x+) | Branch A -- triangle base endpoint |
| R3 | IOSv (15.x+) | Branch B -- hosts PC1 LAN (192.168.1.0/24) |
| PC1 | VPCS | End host on R3's LAN (192.168.1.10/24) |

### Cabling

| Link | Endpoint A | Endpoint B | Subnet |
|---|---|---|---|
| L1 | R1 Gi0/0 | R2 Gi0/0 | 10.12.0.0/30 |
| L2 | R1 Gi0/1 | R3 Gi0/0 | 10.13.0.0/30 |
| L3 | R2 Gi0/1 | R3 Gi0/1 | 10.23.0.0/30 (triangle base) |
| L4 | R3 Gi0/3 | PC1 e0 | 192.168.1.0/24 |

### Console Access Table

| Device | Port | Connection Command |
|---|---|---|
| R1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R3 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| PC1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |

Console ports are assigned dynamically by EVE-NG. Use the EVE-NG web UI or run
`python3 setup_lab.py --host <eve-ng-ip>` which discovers ports via the REST API.

---

## 4. Base Configuration

The `initial-configs/` directory contains a starting point for each router with IP
addressing pre-loaded. Push it with:

```bash
python3 setup_lab.py --host <eve-ng-ip>
```

### What IS pre-loaded

- Hostnames (R1, R2, R3)
- `no ip domain-lookup`
- Loopback0 addresses (1.1.1.1/32, 2.2.2.2/32, 3.3.3.3/32)
- Physical interface IPs on all connected segments
- Interface descriptions
- Console/VTY line settings (logging synchronous, no exec-timeout)

### What is NOT pre-loaded (you will configure in Section 5)

- EIGRP routing process
- EIGRP router-ID
- Network advertisements (network statements)
- Passive-interface on the LAN segment

Verify pre-staged connectivity before starting Section 5:

```bash
R1# ping 10.12.0.2      ! R2 should reply -- directly connected
R1# ping 10.13.0.2      ! R3 should reply -- directly connected
R3# ping 192.168.1.10   ! PC1 should reply -- directly connected
```

---

## 5. Lab Challenge: Core Implementation

Work through these tasks in order. After each task, run its verification command and
confirm the expected state before moving on.

### Task 1: Enable EIGRP AS 100 on R1, R2, and R3

- Start the EIGRP classic-mode process on all three routers using Autonomous System
  number **100**.
- Configure the EIGRP router-ID explicitly on each router to match the loopback:
  R1 = 1.1.1.1, R2 = 2.2.2.2, R3 = 3.3.3.3.
- Disable auto-summary (belt-and-braces; IOSv defaults already disable it).

**Verification:** `show ip protocols` must show "Routing Protocol is eigrp 100" and
the configured router-ID on each device.

---

### Task 2: Advertise every connected subnet into EIGRP

- On each router, advertise its **loopback0** (host mask `0.0.0.0`) into EIGRP.
- On each router, advertise every **transit /30** that touches a neighbor using the
  correct wildcard mask (`0.0.0.3`).
- On R3, additionally advertise the **PC1 LAN** (`192.168.1.0/24`) using wildcard
  mask `0.0.0.255`.

> A wildcard mask is the inverse of a subnet mask. `/30` (255.255.255.252) becomes
> `0.0.0.3`; `/24` (255.255.255.0) becomes `0.0.0.255`.

**Verification:** `show ip eigrp neighbors` on R1 must list both R2 (10.12.0.2) and
R3 (10.13.0.2). R2 and R3 must each show two neighbors. `show ip route eigrp` on R1
must show O... sorry, **D** entries for 2.2.2.2/32, 3.3.3.3/32, 10.23.0.0/30, and
192.168.1.0/24.

---

### Task 3: Examine the EIGRP topology table

- On R1, display the topology table and locate the entry for `192.168.1.0/24`.
- Identify the **successor** (which neighbor R1 uses as the best path).
- Identify the **feasible distance (FD)** -- R1's own metric to the destination.
- Identify the **reported distance (RD)** of each candidate neighbor.
- Apply the feasibility condition (`RD < FD`) to determine whether the alternate
  triangle-base path qualifies as a feasible successor.

**Verification:** `show ip eigrp topology 192.168.1.0/24` must show two entries --
one via 10.13.0.2 (R3 direct) marked as successor, one via 10.12.0.2 (R2, if it
meets feasibility). Note the FD and RD values for use in Task 4.

---

### Task 4: Calculate the composite metric by hand

- Read the FD for `192.168.1.0/24` on R1 from the topology table.
- For the successor path (R1 -> R3 directly over a 1 Gbps GigabitEthernet link):
  compute `256 * (10^7 / 1_000_000 + 1)` = `256 * 11` = **2,816**.
- Confirm this matches the FD (it will be slightly larger because the calculation
  adds R3's delay component plus R1's egress delay).

**Verification:** The metric you compute matches `show ip eigrp topology` output
to within rounding from the delay stack.

---

### Task 5: Suppress hellos on R3's PC1 LAN

- On R3, mark the LAN-facing interface (Gi0/3) as a passive interface so EIGRP stops
  sending hellos out toward PC1 (PC1 is not an EIGRP speaker). The subnet must still
  be advertised -- only the hellos are suppressed.

**Verification:** `show ip eigrp interfaces` on R3 must NOT list Gi0/3.
`show ip route eigrp` on R1 and R2 must still show `D 192.168.1.0/24`.

---

### Task 6: Verify end-to-end reachability from PC1

- From PC1, ping each router loopback (1.1.1.1, 2.2.2.2, 3.3.3.3).
- From R1, traceroute 192.168.1.10 and confirm the path traverses R3 directly
  (one hop of EIGRP routing, then the LAN hop).

**Verification:** All four pings succeed. Traceroute from R1 shows 10.13.0.2
(R3 Gi0/0) then 192.168.1.10.

---

## 6. Verification & Analysis

Run these commands after completing Section 5 to validate each objective. The inline
`! <--` comments point out exactly what to look at.

### 6a -- Neighbor adjacencies (Tasks 1-2)

```
R1# show ip eigrp neighbors
EIGRP-IPv4 Neighbors for AS(100)
H   Address         Interface       Hold Uptime   SRTT   RTO  Q  Seq
                                    (sec)         (ms)        Cnt Num
0   10.12.0.2       Gi0/0            12  00:02:13   10   200  0   5   ! <-- R2 must appear
1   10.13.0.2       Gi0/1            13  00:02:10   12   200  0   4   ! <-- R3 must appear

R2# show ip eigrp neighbors
H   Address         Interface       Hold Uptime   SRTT   RTO  Q  Seq
0   10.12.0.1       Gi0/0            14  00:02:13   10   200  0   6   ! <-- R1
1   10.23.0.2       Gi0/1            11  00:02:05   15   200  0   5   ! <-- R3 (triangle base)
```

### 6b -- Protocol summary and router-ID (Task 1)

```
R1# show ip protocols
Routing Protocol is "eigrp 100"
  Outgoing update filter list for all interfaces is not set
  Incoming update filter list for all interfaces is not set
  Default networks flagged in outgoing updates
  Default networks accepted from incoming updates
  EIGRP-IPv4 Protocol for AS(100)
    Metric weight K1=1, K2=0, K3=1, K4=0, K5=0   ! <-- default K-values (must match neighbors)
    NSF-aware route hold timer is 240
    Router-ID: 1.1.1.1                            ! <-- explicit router-ID set in Task 1
    Topology : 0 (base)
      Active Timer: 3 min
      Distance: internal 90 external 170
  Routing for Networks:
    1.1.1.1/32                                    ! <-- loopback advertisement
    10.12.0.0/30
    10.13.0.0/30
```

### 6c -- Topology table (Tasks 3-4)

```
R1# show ip eigrp topology 192.168.1.0/24
EIGRP-IPv4 Topology Entry for AS(100)/ID(1.1.1.1) for 192.168.1.0/24
  State is Passive, Query origin flag is 1, 1 Successor(s), FD is 3072     ! <-- FD value
  Descriptor Blocks:
  10.13.0.2 (GigabitEthernet0/1), from 10.13.0.2, Send flag is 0x0
      Composite metric is (3072/2816), route is Internal                   ! <-- successor: FD/RD
      Vector metric:
        Minimum bandwidth is 1000000 Kbit
        Total delay is 20 microseconds                                     ! <-- 10us R3 + 10us R1
        Reliability is 255/255
        Load is 1/255
        Minimum MTU is 1500
        Hop count is 1
```

If the triangle-base neighbor also satisfies `RD < FD`, you'll see a second Descriptor
Block flagged as a feasible successor. In the flat 1 Gbps topology this sometimes
doesn't appear -- lab-02 manipulates bandwidth to force it.

### 6d -- Routing table (Task 2)

```
R1# show ip route eigrp
      2.0.0.0/32 is subnetted, 1 subnets
D        2.2.2.2 [90/130816] via 10.12.0.2, 00:03:15, Gi0/0              ! <-- R2 loopback
      3.0.0.0/32 is subnetted, 1 subnets
D        3.3.3.3 [90/130816] via 10.13.0.2, 00:03:12, Gi0/1              ! <-- R3 loopback
      10.0.0.0/30 is subnetted, 3 subnets
D        10.23.0.0 [90/3072] via 10.12.0.2, 00:03:15, Gi0/0              ! <-- triangle base
                   [90/3072] via 10.13.0.2, 00:03:12, Gi0/1              ! <-- ECMP -- both equal
D     192.168.1.0/24 [90/3072] via 10.13.0.2, 00:03:12, Gi0/1            ! <-- PC1 LAN
```

Notice the **[90/3072]** notation -- `90` is the administrative distance (internal
EIGRP), `3072` is the composite metric.

### 6e -- Passive interface (Task 5)

```
R3# show ip eigrp interfaces
EIGRP-IPv4 Interfaces for AS(100)
                        Xmit Queue   Mean   Pacing Time   Multicast    Pending
Interface    Peers       Un/Reliable  SRTT   Un/Reliable   Flow Timer   Routes
Gi0/0          1          0/0          10      0/0            50           0    ! <-- R1 neighbor
Gi0/1          1          0/0          12      0/0            50           0    ! <-- R2 neighbor
Lo0            0          0/0           0      0/0             0           0
                                                                                ! Gi0/3 NOT listed (passive)
```

### 6f -- End-to-end reachability (Task 6)

```
PC1> ping 1.1.1.1
84 bytes from 1.1.1.1 icmp_seq=1 ttl=254 time=2.123 ms    ! <-- R1 loopback via R3

PC1> ping 2.2.2.2
84 bytes from 2.2.2.2 icmp_seq=1 ttl=254 time=3.104 ms    ! <-- R2 loopback via R3->R1->R2 or R3->R2

R1# traceroute 192.168.1.10
Tracing the route to 192.168.1.10
  1 10.13.0.2 4 msec 4 msec 4 msec                        ! <-- R3 Gi0/0
  2 192.168.1.10 8 msec 8 msec *                          ! <-- PC1
```

---

## 7. Verification Cheatsheet

### EIGRP Process Configuration (Classic Mode)

```
router eigrp <asn>
 eigrp router-id <ip>
 network <addr> <wildcard>
 passive-interface <iface>
 no auto-summary
```

| Command | Purpose |
|---|---|
| `router eigrp 100` | Enter EIGRP classic configuration for Autonomous System 100 |
| `eigrp router-id 1.1.1.1` | Set explicit 32-bit router-ID (overrides auto-selection) |
| `network 10.12.0.0 0.0.0.3` | Advertise this subnet AND enable EIGRP on matching interfaces |
| `network 1.1.1.1 0.0.0.0` | Advertise a specific host (loopback) into EIGRP |
| `passive-interface Gi0/3` | Suppress hellos on the interface; still advertise the subnet |
| `no auto-summary` | Disable classful auto-summarization (already default on IOSv 15+) |

> **Exam tip:** The AS number must match between neighbors. `router eigrp 100` on one
> side and `router eigrp 200` on the other will never form an adjacency. No log line
> is generated -- you just see no neighbor.

### Verification Commands

| Command | What to Look For |
|---|---|
| `show ip eigrp neighbors` | Every expected neighbor listed; Hold timer counting down |
| `show ip eigrp interfaces` | Each EIGRP-enabled interface listed with peer count > 0 on transit links |
| `show ip eigrp topology` | Successor entry for each destination; FD and RD values |
| `show ip eigrp topology <prefix>` | Detailed FD/RD for a specific destination; feasible successors |
| `show ip route eigrp` | `D` entries for every remote subnet; AD = 90 for internal |
| `show ip protocols` | Router-ID, K-values, advertised networks, AD settings |
| `show ip eigrp traffic` | Hello/update/query counters -- useful for troubleshooting |
| `debug eigrp packets` | Real-time hello / update packet trace (use sparingly) |

### Wildcard Mask Quick Reference

| Subnet Mask | Prefix | Wildcard Mask | Common Use |
|---|---|---|---|
| 255.255.255.255 | /32 | 0.0.0.0 | Single host / loopback |
| 255.255.255.252 | /30 | 0.0.0.3 | Point-to-point transit link |
| 255.255.255.0 | /24 | 0.0.0.255 | Class-C / LAN segment |
| 255.255.0.0 | /16 | 0.0.255.255 | Aggregate /16 |
| 255.0.0.0 | /8 | 0.255.255.255 | Classful Class-A |

### Common Classic-EIGRP Failure Causes

| Symptom | Likely Cause |
|---|---|
| No neighbor appears on a transit link | AS number mismatch OR network statement missing the interface |
| Neighbor flaps constantly | K-value mismatch OR hello/hold timer mismatch |
| Route missing from one router's RIB but present on another | Network statement missing on the advertising side |
| Adjacency up but no route learned | Interface configured passive on one side |
| Metric looks wrong | Bandwidth / delay misconfigured on an interface in the path |
| Routing loop or blackhole | `no auto-summary` missing on a discontiguous classful boundary (rare on IOS 15+) |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these configs first!

### Objective 1: EIGRP process on all routers

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1
router eigrp 100
 eigrp router-id 1.1.1.1
 network 1.1.1.1 0.0.0.0
 network 10.12.0.0 0.0.0.3
 network 10.13.0.0 0.0.0.3
 no auto-summary
```
</details>

<details>
<summary>Click to view R2 Configuration</summary>

```bash
! R2
router eigrp 100
 eigrp router-id 2.2.2.2
 network 2.2.2.2 0.0.0.0
 network 10.12.0.0 0.0.0.3
 network 10.23.0.0 0.0.0.3
 no auto-summary
```
</details>

<details>
<summary>Click to view R3 Configuration</summary>

```bash
! R3
router eigrp 100
 eigrp router-id 3.3.3.3
 network 3.3.3.3 0.0.0.0
 network 10.13.0.0 0.0.0.3
 network 10.23.0.0 0.0.0.3
 network 192.168.1.0 0.0.0.255
 passive-interface GigabitEthernet0/3
 no auto-summary
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ip eigrp neighbors
show ip protocols
show ip eigrp topology
show ip eigrp topology 192.168.1.0/24
show ip route eigrp
show ip eigrp interfaces
ping 1.1.1.1 source 192.168.1.10    ! from PC1
traceroute 192.168.1.10             ! from R1
```
</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. Inject the fault first, then diagnose and
fix using only `show` commands.

### Workflow

```bash
python3 setup_lab.py --host <eve-ng-ip>                   # reset to known-good
python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>
# ...troubleshoot...
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>   # restore
```

---

### Ticket 1 -- R1 Reports Only One EIGRP Neighbor

You come in Monday morning and notice R1 has only one EIGRP neighbor instead of two.
Routes to 2.2.2.2 and 10.23.0.0/30 are missing from R1's RIB. R2 itself looks
healthy when you console in -- its neighbor table just has no entry for R1.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py`

**Success criteria:** R1 must show **two** EIGRP neighbors (R2 via 10.12.0.2 and
R3 via 10.13.0.2), and `D 2.2.2.2/32` must appear in R1's routing table.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. On R1, `show ip eigrp neighbors` -- only R3 appears.
2. On R2, `show ip eigrp neighbors` -- neither R1 nor R3 appears.
3. On R1, `show ip eigrp interfaces` -- Gi0/0 still listed (configuration side is fine).
4. Interface is up: `show ip interface brief` -- Gi0/0 up/up on both ends, ping
   10.12.0.2 from R1 succeeds. So L1/L2 / IP connectivity is fine.
5. Check EIGRP process: `show ip protocols | include eigrp` on R2.
   -- R2 shows "Routing Protocol is eigrp **200**". The AS number was changed.
6. An AS mismatch prevents adjacency entirely -- no hellos are accepted between
   peers running different AS numbers, and IOS logs nothing by default.
</details>

<details>
<summary>Click to view Fix</summary>

```bash
R2(config)# no router eigrp 200
R2(config)# router eigrp 100
R2(config-router)# eigrp router-id 2.2.2.2
R2(config-router)# network 2.2.2.2 0.0.0.0
R2(config-router)# network 10.12.0.0 0.0.0.3
R2(config-router)# network 10.23.0.0 0.0.0.3
R2(config-router)# no auto-summary
R2# show ip eigrp neighbors                    ! <-- R1 and R3 both appear now
R1# show ip route eigrp | include 2.2.2.2      ! <-- D 2.2.2.2 returns
```
</details>

---

### Ticket 2 -- R2-R3 Adjacency on the Triangle Base Is Down

R1's adjacencies to R2 and R3 are both up. But on R2, `show ip eigrp neighbors` lists
R1 only -- the neighbor across the 10.23.0.0/30 base link is gone. R3 similarly shows
only R1 on its neighbor table. Ping 10.23.0.2 from R2 still succeeds, so L3
connectivity is fine.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py`

**Success criteria:** R2 must see R3 as a neighbor on Gi0/1 (address 10.23.0.2).
R3 must see R2 (10.23.0.1) on its neighbor table.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `show ip eigrp neighbors` on R2 -- only R1 listed (missing R3 on Gi0/1).
2. `show ip eigrp interfaces` on R2 -- Gi0/1 IS listed with Peers = 0.
3. `show ip eigrp interfaces` on R3 -- Gi0/1 is **NOT listed**. EIGRP is not
   enabled on that interface on R3.
4. `show running-config | section router eigrp` on R3 -- the
   `network 10.23.0.0 0.0.0.3` statement is missing.
5. Without the network statement on R3, EIGRP does not bind to Gi0/1 at all,
   so no hellos are sent out of that interface, and R2 has no peer to adjacency with.
</details>

<details>
<summary>Click to view Fix</summary>

```bash
R3(config)# router eigrp 100
R3(config-router)# network 10.23.0.0 0.0.0.3
R3(config-router)# end
R3# show ip eigrp neighbors                  ! <-- R2 (10.23.0.1) appears
R2# show ip eigrp topology 3.3.3.3/32        ! <-- now has a second path via R3 directly
```
</details>

---

### Ticket 3 -- R1 Sees R2 as a Neighbor but Not R3 (Despite Interface Up)

R1's `show ip interface brief` shows Gi0/1 up/up (toward R3). You can ping 10.13.0.2
from R1 and get replies. EIGRP is configured on both ends. But R1 only has one
neighbor (R2), and it's been that way since an overnight change window.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py`

**Success criteria:** R1 must have **two** EIGRP neighbors again (R2 via Gi0/0 and
R3 via Gi0/1). Route `D 3.3.3.3/32` on R1 must have **two** equal-cost next-hops in
the RIB (it currently only has the indirect path via R2).

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `show ip eigrp neighbors` on R1 -- only R2 on Gi0/0.
2. Ping 10.13.0.2 from R1 succeeds -- L2/L3 is fine.
3. `show ip eigrp interfaces` on R1 -- Gi0/1 is **still listed**, but Peers = 0.
4. `show ip protocols | section eigrp` on R1 -- observe "Passive Interface(s):
   GigabitEthernet0/1". That's the giveaway.
5. `show running-config | section router eigrp` on R1 confirms
   `passive-interface GigabitEthernet0/1`.
6. Passive-interface on a **transit** link (not a LAN) suppresses hellos, so no
   adjacency forms, but EIGRP still *advertises* the subnet -- which is why
   `show ip eigrp interfaces` still lists Gi0/1. Routes to R3's destinations still
   arrive via R2 -- traffic is degraded, not blackholed.
</details>

<details>
<summary>Click to view Fix</summary>

```bash
R1(config)# router eigrp 100
R1(config-router)# no passive-interface GigabitEthernet0/1
R1(config-router)# end
R1# show ip eigrp neighbors                  ! <-- R3 (10.13.0.2) now appears
R1# show ip route 3.3.3.3                    ! <-- now two equal-cost paths
```
</details>

---

## 10. Lab Completion Checklist

### Core Implementation (Section 5)

- [ ] Task 1: EIGRP AS 100 running on R1, R2, R3 with explicit router-IDs
- [ ] Task 2: All transit /30s and loopbacks advertised; R3's LAN (192.168.1.0/24) advertised
- [ ] Task 3: Identified successor + (if present) feasible successor for 192.168.1.0/24 on R1
- [ ] Task 4: Manually computed composite metric matches `show ip eigrp topology` output
- [ ] Task 5: R3 Gi0/3 is passive; LAN still appears as `D 192.168.1.0/24` on R1 and R2
- [ ] Task 6: PC1 can ping 1.1.1.1, 2.2.2.2, 3.3.3.3; traceroute from R1 to PC1 transits R3 directly

### Troubleshooting (Section 9)

- [ ] Ticket 1: AS number mismatch on R2 diagnosed and fixed
- [ ] Ticket 2: Missing network statement on R3 diagnosed and fixed
- [ ] Ticket 3: Passive-interface on R1's transit link diagnosed and fixed

### Understanding

- [ ] Can explain, in your own words, why EIGRP is "advanced distance vector" not link-state
- [ ] Can state the feasibility condition (RD < FD) and why it guarantees loop-free backups
- [ ] Can read `show ip eigrp topology <prefix>` and identify successor vs feasible successor
- [ ] Can compute the classic composite metric from bandwidth and delay alone
