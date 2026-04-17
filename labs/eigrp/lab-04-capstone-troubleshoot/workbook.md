# Lab 04 — EIGRP Comprehensive Troubleshooting (Capstone II)

## Table of Contents

1. [Concepts & Skills Covered](#1-concepts--skills-covered)
2. [Topology & Scenario](#2-topology--scenario)
3. [Hardware & Environment Specifications](#3-hardware--environment-specifications)
4. [Base Configuration](#4-base-configuration)
5. [Lab Challenge: Comprehensive Troubleshooting](#5-lab-challenge-comprehensive-troubleshooting)
6. [Verification & Analysis](#6-verification--analysis)
7. [Verification Cheatsheet](#7-verification-cheatsheet)
8. [Solutions (Spoiler Alert!)](#8-solutions-spoiler-alert)
9. [Troubleshooting Scenarios](#9-troubleshooting-scenarios)
10. [Lab Completion Checklist](#10-lab-completion-checklist)

---

## 1. Concepts & Skills Covered

**Exam Objective:** Blueprint 3.2, 3.2.a, 3.2.b — Troubleshoot EIGRP (named mode, dual-stack, stub, summarization, load balancing).

This is the EIGRP **troubleshooting** capstone. The full dual-stack build from Lab 03 is loaded on the topology, but with five concurrent faults distributed across all four routers. Your job is to restore full IPv4 + IPv6 reachability and unequal-cost load balancing using only `show`, `debug`, and a disciplined top-down methodology. No step-by-step guidance is provided — the scenario section lists five symptom reports, not solutions.

### A repeatable EIGRP troubleshooting methodology

Every EIGRP fault sits somewhere in this stack. Walk it top-down, per address family:

1. **Interface enrolled?** — `show ip eigrp interfaces` / `show ipv6 eigrp interfaces`. If the interface is missing, the network statement is wrong (IPv4) or the interface is `shutdown` (IPv6). Nothing below this matters if the interface is absent.
2. **Hellos being sent?** — `show ip protocols`, `show running-config | section eigrp`. A `passive-interface` (or `af-interface ... passive-interface`) silences hellos — the interface is still *enrolled* but the neighbor never forms.
3. **Hello received and parameters agree?** — `show ip eigrp neighbors`. If the neighbor is missing, check: matching AS number (legacy mode) or matching `virtual-instance` + AF (named mode), identical K-values, same subnet / mask, no authentication mismatch.
4. **Route learned and installed?** — `show ip route eigrp`, `show ip eigrp topology`. An adjacency can be up but the route absent: stub advertising the wrong route type, summary suppressing more-specifics, or the route lost the FC to a feasible successor.
5. **Path count correct?** — For unequal-cost paths: `show ip route <prefix>` should list every variance-qualified path. Only one path means `variance` is missing or too low.
6. **End-to-end reachability** — only meaningful once layers 1-5 are healthy on both address families.

| Layer | Question | Go-to command |
|-------|----------|---------------|
| Enrolment | Is the interface part of the EIGRP process? | `show ip eigrp interfaces`, `show ipv6 eigrp interfaces` |
| Hellos | Are hellos leaving this interface? | `show ip protocols` (passive list), `show ip eigrp interfaces detail` |
| Adjacency | Does the neighbor relationship form? | `show ip eigrp neighbors`, `show ipv6 eigrp neighbors` |
| Advertised routes | What does the neighbor send me? | `show ip eigrp topology`, `show ip route eigrp` |
| Path selection | How many paths installed? | `show ip route <prefix>`, `show ip eigrp topology <prefix>` |
| Data plane | Does the packet arrive? | `ping`, `traceroute` |

### K-value mismatch — a silent, asymmetric killer

EIGRP uses **K-values** to weight the composite metric: `K1` (bandwidth), `K2` (load), `K3` (delay), `K4` + `K5` (reliability, when non-zero). Default: `K1=1, K2=0, K3=1, K4=0, K5=0`. The `metric weights 0 K1 K2 K3 K4 K5` command changes them — and **both neighbors must match** or the adjacency refuses to form.

The symptom is brutal:

```
%DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.12.0.2 (GigabitEthernet0/0) is down: K-value mismatch
```

Key troubleshooting points:
- K-values are **per address family** in named mode. An IPv4 K-value mismatch kills IPv4 adjacencies while IPv6 stays up over the same link — a classic dual-stack asymmetry.
- A K-value mismatch never recovers silently. Fix the K-values on the broken end; the adjacency comes up within one hello (5 s).
- `show ip protocols` shows the local K-values. Compare both ends.

### Passive-interface — enrolled but silent

`passive-interface` (legacy) or `af-interface <X> passive-interface` (named) keeps the interface's directly-connected subnet in the EIGRP database and continues to advertise it, but stops sending hellos. The common mistake: setting `passive-interface` on a **transit** link instead of the LAN-facing edge.

Diagnostic sequence:
1. `show ip eigrp neighbors` — the neighbor is missing.
2. `show ip eigrp interfaces` — the interface **is** listed (it's enrolled).
3. `show ip protocols` — under `Passive Interface(s):` the transit link is named.
4. Cross-check design intent: only LAN/PC-facing ports should be passive, never router-to-router links.

### Missing network statement (IPv4) — the dual-stack asymmetry

In **named-mode IPv4**, interfaces are enrolled via `network A.B.C.D wildcard` statements under the address family. Miss one and that interface's IPv4 EIGRP never starts — no hellos, no neighbor, no route.

In **named-mode IPv6**, enrolment is automatic: every interface with an IPv6 address and `ipv6 unicast-routing` joins the IPv6 AF. There is no equivalent `network` statement.

Result: a missing IPv4 network statement produces a characteristic asymmetry — `show ipv6 eigrp neighbors` shows the neighbor, `show ip eigrp neighbors` does not. Always run both when a single link looks broken; divergence between them localises the fault to the IPv4 AF.

### Stub routing — `connected` vs `receive-only`

EIGRP stub filters which route types the stub router advertises to its hub:

| Keyword | Advertises | Use case |
|---------|-----------|----------|
| `connected` | Directly connected subnets only | Branch with local LANs (this lab's R4) |
| `summary` | Manually configured summaries | Branch that aggregates before uplink |
| `static` | Static routes redistributed into EIGRP | Branch with injected statics |
| `redistributed` | Redistributed routes from other protocols | Branch that is a redistribution point |
| `receive-only` | **Nothing** — stub accepts routes but advertises none | Read-only branch (rare, dangerous) |

`receive-only` is the most common stub fault in exam questions: the adjacency forms, the hub sends everything to the stub, but the hub sees **no** routes back from the stub — even the stub's own LAN is invisible. Symptom: connected LANs on the stub router don't appear in the hub's `show ip route eigrp` even though `show ip eigrp neighbors` shows a healthy peering.

### Variance and unequal-cost multipath

EIGRP installs multiple paths to the same destination when:
1. Every candidate path passes the **feasibility condition** (AD of path < FD of primary path).
2. Every candidate path's metric ≤ `variance × FD_primary`.

`variance 1` (default) = equal-cost only. `variance 2`..`128` = up to 128× the primary metric. A missing `variance` statement after a bandwidth asymmetry has been introduced means only the fast path installs, and the student sees only one next-hop in `show ip route <prefix>` instead of the intended two.

Diagnosis:
- `show ip eigrp topology <prefix>` — lists **every** topology entry, including those rejected as non-feasible or out-of-variance.
- `show ip route <prefix>` — shows only the installed best path(s). Diff between the two reveals unused candidates.

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| Top-down EIGRP diagnosis | Walk enrolment → hellos → adjacency → advertised routes → path count — per AF |
| Dual-stack asymmetry reading | Recognise when IPv4 and IPv6 diverge on the same link and localise the fault to the IPv4 AF |
| Correlate syslog with `show` output | Turn a `%DUAL-5-NBRCHANGE ... K-value mismatch` line into a target device in under a minute |
| Distinguish enrolled-but-silent from not-enrolled | Separate `passive-interface` (enrolled, no hellos) from a missing network statement (not enrolled at all) |
| Identify stub misconfiguration | Spot the "neighbor up, no routes learned from stub" pattern characteristic of `eigrp stub receive-only` |
| Variance path-count verification | Confirm unequal-cost multipath by comparing `show ip eigrp topology` to `show ip route` |
| Concurrent-fault prioritisation | Decide which of five tickets to clear first so later tickets become observable |

---

## 2. Topology & Scenario

### Network Diagram

```
                          ┌─────────────────────────┐
                          │           R1            │
                          │        (Hub Core)       │
                          │   Lo0: 1.1.1.1/32       │
                          │   2001:DB8:FF::1/128    │
                          └──────┬───────────┬──────┘
                   Gi0/0         │           │         Gi0/1
              10.12.0.1/30       │           │      10.13.0.1/30
           2001:DB8:12::1/64     │           │    2001:DB8:13::1/64
                                 │           │
              10.12.0.2/30       │           │    10.13.0.2/30
           2001:DB8:12::2/64     │           │    2001:DB8:13::2/64
                   Gi0/0         │           │         Gi0/0
                      ┌──────────┘           └──────────┐
                      │                                 │
                 ┌────┴──────────────┐       ┌──────────┴────────┐
                 │       R2          │       │       R3          │
                 │ (Branch A / var.) │       │  (Branch B / sum) │
                 │ Lo0: 2.2.2.2/32   │       │ Lo1-4: 10.3.0-3/24│
                 │ 2001:DB8:FF::2    │       │ Lo0: 3.3.3.3/32   │
                 └───┬───────────┬───┘       └─┬─────────────┬───┘
                Gi0/1│           │Gi0/2        │Gi0/1        │Gi0/3
           10.23.0.1/30          │10.24.0.1/30 │10.23.0.2/30 │192.168.1.1/24
         2001:DB8:23::1/64       │2001:DB8:24  │2001:DB8:23  │(passive - PC1)
          bandwidth 100000       │  ::1/64     │  ::2/64     │
                      └──────────┼─────────────┘ bandwidth   │
                                 │   10.23.0.0/30 100000     │
                                 │                           │
                       10.24.0.2/30                     ┌────┴────┐
                       2001:DB8:24::2/64                │   PC1   │
                              Gi0/0                     │ .10     │
                       ┌──────┴───────────┐             └─────────┘
                       │       R4         │         192.168.1.0/24
                       │ (Stub / PC2 LAN) │
                       │ Lo0: 4.4.4.4/32  │
                       └────────┬─────────┘
                            Gi0/1
                       192.168.2.1/24 (passive - PC2)
                       2001:DB8:2:2::1/64
                                │
                           ┌────┴────┐
                           │   PC2   │
                           │  .10    │
                           └─────────┘
                       192.168.2.0/24
```

### Scenario

You have inherited the EIGRP-LAB domain from the engineer who built it last week (Lab 03's capstone). Their Friday change window was "tidy up the routing" — but first thing Monday morning, the helpdesk opens five separate tickets against the EIGRP fabric. The previous engineer is on PTO and unreachable; their change notes are missing. You have the hand-over pack: the running state on every router, the known-good reference in `solutions/`, and this ticket queue.

Five concurrent tickets:

- **NOC:** R1's syslog is flooding with `%DUAL-5-NBRCHANGE ... K-value mismatch` messages. R1 has **no** IPv4 EIGRP neighbors. Its IPv6 neighbors look fine.
- **Branch A ops:** R2 can see R1 and R4 over IPv6 but cannot see *either* over IPv4. R2↔R3 is broken in both directions on IPv4.
- **Branch A ops (2):** R2's route table has no path to 192.168.2.0/24 (PC2 LAN) in IPv4, even after the other adjacencies come back. IPv6 has a path fine.
- **Branch B ops:** Once R1 and R2 can see each other, R1 and R2 still see nothing from R4 — no PC2 LAN prefix, no R4 loopback. IPv6 shows both.
- **Capacity planning:** After all adjacencies are healthy, R2's route to PC1 LAN (192.168.1.0/24) shows a single next-hop instead of the planned two-path unequal-cost split across the fast (R1 path) and slow (direct R3 path) links.

The faults are **concurrent**, not sequential — running `setup_lab.py` loads the current broken state onto all four routers so you can triage them all at once. Restore the network to full dual-stack EIGRP health with PC1 ↔ PC2 reachability (both v4 and v6), R3's summaries intact, R4 as a `connected`-stub, and R2 installing both paths to 192.168.1.0/24. The `solutions/` directory holds the known-good reference; use it only to verify after you have diagnosed each fault yourself.

---

## 3. Hardware & Environment Specifications

### Device Inventory

| Device | Platform | Role | Loopback0 |
|--------|----------|------|-----------|
| R1 | IOSv | Hub / core — two neighbors (R2, R3) | 1.1.1.1/32, 2001:DB8:FF::1/128 |
| R2 | IOSv | Branch A / variance point — 3 neighbors | 2.2.2.2/32, 2001:DB8:FF::2/128 |
| R3 | IOSv | Branch B / summarizer — hosts Lo1-4 + PC1 LAN | 3.3.3.3/32, 2001:DB8:FF::3/128 |
| R4 | IOSv | Stub / PC2 LAN — one neighbor (R2) | 4.4.4.4/32, 2001:DB8:FF::4/128 |
| PC1 | VPCS | End host — 192.168.1.10/24, 2001:DB8:1:1::10/64 | — |
| PC2 | VPCS | End host — 192.168.2.10/24, 2001:DB8:2:2::10/64 | — |

### Cabling Table

| Link | A end | B end | Subnet (v4) | Subnet (v6) | Purpose |
|------|-------|-------|-------------|-------------|---------|
| L1 | R1 Gi0/0 | R2 Gi0/0 | 10.12.0.0/30 | 2001:DB8:12::/64 | Core ↔ Branch A |
| L2 | R1 Gi0/1 | R3 Gi0/0 | 10.13.0.0/30 | 2001:DB8:13::/64 | Core ↔ Branch B |
| L3 | R2 Gi0/1 | R3 Gi0/1 | 10.23.0.0/30 | 2001:DB8:23::/64 | Branch A ↔ Branch B (100 Mbps) |
| L4 | R2 Gi0/2 | R4 Gi0/0 | 10.24.0.0/30 | 2001:DB8:24::/64 | Branch A ↔ stub |
| L5 | R3 Gi0/3 | PC1 eth0 | 192.168.1.0/24 | 2001:DB8:1:1::/64 | PC1 LAN |
| L6 | R4 Gi0/1 | PC2 eth0 | 192.168.2.0/24 | 2001:DB8:2:2::/64 | PC2 LAN |

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

**Pre-broken build.** `initial-configs/` loads the full Lab 03 capstone topology with **five faults pre-injected**. The faults are concurrent and distributed across all four routers. Running `setup_lab.py` puts you directly into the broken state so you can begin troubleshooting immediately.

**Pre-loaded (correct) baseline on all devices:**

- Hostnames, `no ip domain-lookup`, `ipv6 unicast-routing`, comfort lines
- IPv4 + IPv6 addressing on every transit and LAN interface
- Named-mode EIGRP process `EIGRP-LAB` with both IPv4 and IPv6 AFs, AS 100
- R3's summary-addresses on both uplinks (10.3.0.0/22 + 2001:DB8:3::/62)
- R2 and R3 bandwidth 100000 on the Gi0/1 (10.23.0.0/30) link
- R3 passive on Gi0/3 (PC1 LAN), R4 passive on Gi0/1 (PC2 LAN)

**Broken (what you must fix):** Five things. The symptom descriptions live in Section 9 — the fault identities (which device, which knob) are in the Diagnosis/Fix spoiler blocks, not in this section.

---

## 5. Lab Challenge: Comprehensive Troubleshooting

> This is a capstone lab. The network is pre-broken.
> Diagnose and resolve 5+ concurrent faults spanning all blueprint bullets.
> No step-by-step guidance is provided — work from symptoms only.

**Target end state (acceptance tests):**

1. `show ip eigrp neighbors` on R1 shows **2** neighbors (10.12.0.2 / R2, 10.13.0.2 / R3).
2. `show ip eigrp neighbors` on R2 shows **3** neighbors (R1, R3, R4).
3. `show ipv6 eigrp neighbors` on every router matches its IPv4 neighbor count.
4. `show ip protocols` on every router — no `K-value mismatch` log entries in the last minute.
5. `show ip route eigrp` on R1 shows `D 10.3.0.0/22 [90/...]` via **both** 10.12.0.2 and 10.13.0.2 (equal-cost from R1's perspective through the summary).
6. `show ip route eigrp` on R1 shows `D 192.168.2.0/24` via 10.12.0.2 (through R2 → R4).
7. `show ip route eigrp` on R2 shows `D 192.168.1.0/24` with **two** next-hops: 10.12.0.1 (via R1, fast) and 10.23.0.2 (direct, slow) — unequal-cost multipath.
8. `show ip route eigrp` on R3 shows `D 192.168.2.0/24` via R1 → R2 → R4.
9. `show ip route` on R3 shows the `D 10.3.0.0/22 is a summary, 00:... Null0` discard route (AD 5).
10. `PC1> ping 192.168.2.10` — succeeds (IPv4, crosses R3 → R1 → R2 → R4).
11. `PC1> ping 2001:db8:2:2::10` — succeeds (IPv6).
12. No `%DUAL-5-NBRCHANGE` log flapping on any router.

You are scored on the end state, not the path — but a disciplined top-down walk (enrolment → hellos → adjacency → routes → path count) will reach it faster than random guessing.

---

## 6. Verification & Analysis

After each fix, re-run the relevant verification block. Every highlighted line must match before the ticket is closed.

### Neighbor tables — both AFs, all four routers

```
R1# show ip eigrp neighbors
EIGRP-IPv4 VR(EIGRP-LAB) Address-Family Neighbors for AS(100)
H   Address         Interface         Hold Uptime   SRTT   RTO  Q  Seq
                                      (sec)          (ms)      Cnt Num
0   10.13.0.2       Gi0/1               13 00:00:42   12   200  0  9     ! ← R3 must appear
1   10.12.0.2       Gi0/0               11 00:00:40   15   200  0  8     ! ← R2 must appear

R1# show ipv6 eigrp neighbors
EIGRP-IPv6 VR(EIGRP-LAB) Address-Family Neighbors for AS(100)
H   Address                 Interface     Hold Uptime   SRTT   RTO  Q  Seq
0   Link-local address:     Gi0/1           11 00:05:12   10   200  0  7  ! ← R3 IPv6 (was up throughout)
     FE80::3
1   Link-local address:     Gi0/0           12 00:05:10   12   200  0  6  ! ← R2 IPv6
     FE80::2
```

```
R2# show ip eigrp neighbors
H   Address         Interface         Hold Uptime   SRTT   RTO  Q  Seq
0   10.24.0.2       Gi0/2               14 00:00:38   18   200  0  4     ! ← R4 must appear
1   10.23.0.2       Gi0/1               12 00:00:40    9   200  0  6     ! ← R3 must appear
2   10.12.0.1       Gi0/0               11 00:00:42   11   200  0  5     ! ← R1 must appear
```

### K-value agreement

```
R1# show ip protocols | section eigrp
Routing Protocol is "eigrp 100"
  ...
  EIGRP-IPv4 VR(EIGRP-LAB) Address-Family Protocol for AS(100)
    Metric weight K1=1, K2=0, K3=1, K4=0, K5=0                        ! ← must be default 1-0-1-0-0
    ...
```

```
R1# show logging | include K-value
                                                                      ! ← no K-value mismatch lines
```

### Adjacency / passive-interface consistency

```
R3# show ip protocols | section Passive
Passive Interface(s):
  GigabitEthernet0/3                                                  ! ← only Gi0/3 (PC1 LAN) should be passive
```

```
R3# show ip eigrp interfaces
EIGRP-IPv4 VR(EIGRP-LAB) Address-Family Interfaces for AS(100)
Interface              Peers  Xmit Queue
Gi0/0                    1        0                                   ! ← 1 peer = R1
Gi0/1                    1        0                                   ! ← 1 peer = R2 (was 0 when passive)
Gi0/3                    0        0                                   ! ← 0 peers expected (passive, PC1 LAN)
Lo0 / Lo1..4             0        0                                   ! ← loopbacks
```

### Stub advertisement — R4 advertises PC2 LAN

```
R1# show ip route eigrp | include 192.168.2.0
D     192.168.2.0/24 [90/130816] via 10.12.0.1, 00:00:30, Gi0/0       ! ← via R2 → R4
```

```
R4# show ip protocols | section eigrp
  EIGRP-IPv4 VR(EIGRP-LAB) Address-Family Protocol for AS(100)
    Stub, connected                                                    ! ← "connected", NOT "receive-only"
```

### Unequal-cost load balancing on R2 to PC1 LAN

```
R2# show ip route 192.168.1.0
Routing entry for 192.168.1.0/24
  Known via "eigrp 100", distance 90, metric 156160, type internal
  Redistributing via eigrp 100
  Last update from 10.12.0.1 on Gi0/0, 00:00:15 ago
  Routing Descriptor Blocks:
  * 10.23.0.2, from 10.23.0.2, 00:00:15 ago, via Gi0/1                ! ← direct R3 path (slow, via bandwidth 100000)
      Route metric is 1536640, traffic share count is 10
    10.12.0.1, from 10.12.0.1, 00:00:15 ago, via Gi0/0                ! ← R1 transit path (fast, 1 Gbps both hops)
      Route metric is 156160, traffic share count is 100              ! ← BOTH blocks must be present
```

```
R2# show ip eigrp topology 192.168.1.0/24
EIGRP-IPv4 VR(EIGRP-LAB) Topology Entry for AS(100) ID(2.2.2.2)
 for 192.168.1.0/24
  State is Passive, Query origin flag is 1, 2 Successor(s), FD is 156160
                                                                      ! ← "2 Successor(s)" confirms variance installed both
  Descriptor Blocks:
  10.12.0.1 (Gi0/0), from 10.12.0.1, Send flag is 0x0
      Composite metric is (156160/130816), route is Internal
  10.23.0.2 (Gi0/1), from 10.23.0.2, Send flag is 0x0
      Composite metric is (1536640/130816), route is Internal
```

### End-to-end reachability — the final integration test

```
PC1> ping 192.168.2.10
84 bytes from 192.168.2.10 icmp_seq=1 ttl=61 time=6.3 ms              ! ← ttl=61 — three hops (R3→R1→R2→R4)
```

```
PC1> ping 2001:db8:2:2::10
2001:db8:2:2::10 icmp6_seq=1 ttl=61 time=6.5 ms                       ! ← IPv6 parity
```

### Syslog — noise must stop

```
R1# show logging | include DUAL-5-NBRCHANGE|K-value
                                                                      ! ← empty (or only historical, older than last 2 min)
```

---

## 7. Verification Cheatsheet

### Top-Down EIGRP Diagnostic Walk

```
show ip eigrp interfaces              ! Enrolment — is the interface in the AF?
show ip protocols | section eigrp     ! K-values, passive list, AS, router-id
show ip eigrp neighbors               ! IPv4 adjacency presence
show ipv6 eigrp neighbors             ! IPv6 adjacency presence (diff reveals AF-specific fault)
show ip eigrp topology [prefix]       ! All candidate paths, FD/AD, successor status
show ip route eigrp                   ! Installed best path(s) only
show ip route <prefix>                ! Per-prefix detail, including "traffic share count"
show logging | include DUAL|EIGRP     ! Syslog trail for adjacency events
debug eigrp packets hello              ! (use sparingly) — confirms hellos flowing
```

| Command | What to Look For |
|---------|-----------------|
| `show ip eigrp interfaces` | Interface listed = enrolled. Peers column = neighbors on that interface |
| `show ip protocols` | `Metric weight K1...K5` line, Passive Interface(s) list, Router-ID |
| `show ip eigrp neighbors` | Neighbor IP, interface, Hold timer counting down, Uptime rising |
| `show ipv6 eigrp neighbors` | Link-local neighbor, same interface. Diff vs IPv4 reveals AF-only fault |
| `show ip eigrp topology <prefix>` | "N Successor(s)" count, Composite metric, FD in parentheses |
| `show ip route <prefix>` | Routing Descriptor Blocks — one per installed path; traffic share counts |
| `show running-config | section router eigrp` | Stub mode (connected/receive-only), variance, summary-address, af-interface passive |
| `show logging` | `K-value mismatch`, `DUAL-5-NBRCHANGE`, `no common subnet`, `authentication failure` |

> **Exam tip:** The IPv4-vs-IPv6 neighbor diff is the fastest way to isolate an IPv4-only fault. If `show ipv6 eigrp neighbors` is healthy on a link but `show ip eigrp neighbors` is empty, the fault is in the IPv4 AF only — check K-values, `network` statements, and IPv4-specific `af-interface` settings first.

### K-Value Reference

```
metric weights 0 K1 K2 K3 K4 K5

  Default:  1 0 1 0 0    (bandwidth + delay)
  Any other combo must match on BOTH neighbors or adjacency fails.
```

| K-value | Factor | Default |
|---------|--------|---------|
| K1 | Bandwidth | 1 |
| K2 | Load | 0 |
| K3 | Delay | 1 |
| K4 | Reliability | 0 |
| K5 | MTU / reliability denominator | 0 |

> **Exam tip:** Any K-value change is per-AF in named mode. A mismatch produces a very loud syslog (`K-value mismatch`) and a neighbor that never forms. Fix by aligning both ends — do not try to "work around" with a redistribution hack.

### Stub Router Types

```
router eigrp <NAME>
 address-family ipv4 unicast autonomous-system <AS>
  eigrp stub <keyword>          ! pick ONE combination
  !  connected    — advertises connected networks (typical branch)
  !  summary      — advertises configured summaries
  !  static       — advertises redistributed statics
  !  redistributed — advertises all redistributed routes
  !  receive-only — advertises nothing (rare, dangerous)
```

| Keyword | Advertises | Typical Use |
|---------|-----------|-------------|
| `connected` | Directly connected subnets | Branch with LANs — this lab's R4 |
| `summary` | Manual summaries | Pre-aggregated branch |
| `static` | Redistributed statics | Branch with injected routes |
| `redistributed` | All redistributed routes | Mutual-redistribution point |
| `receive-only` | Nothing | Transit/read-only leaf (rare) |

Multiple keywords can be combined (e.g. `eigrp stub connected summary`) — `receive-only` is the one exception; it must stand alone.

> **Exam tip:** "Neighbor up, no routes learned from stub" = `receive-only`. It is the stub's most common misconfiguration because the keyword is tempting (sounds like "listen only"), but the effect is the opposite of what branch engineers usually want.

### Variance and Unequal-Cost

```
router eigrp <NAME>
 address-family ipv4 unicast autonomous-system <AS>
  variance <1..128>             ! multiplier on FD; 1 = equal-cost only
```

| Variance | Installs |
|----------|---------|
| 1 (default) | Only paths with metric = FD (equal-cost) |
| 2 | Paths with metric ≤ 2 × FD (and FC-passing) |
| N | Paths with metric ≤ N × FD (and FC-passing) |

The feasibility condition (FC) still applies: a candidate's **advertised distance** (AD) must be strictly less than the primary path's **feasible distance** (FD). Variance cannot install a non-feasible path — it can only widen the metric window for feasible ones.

### EIGRP Passive-Interface Scoping

```
router eigrp <NAME>
 address-family ipv4 unicast autonomous-system <AS>
  af-interface <IF>             ! per-interface passive
   passive-interface
  exit-af-interface
  af-interface default          ! all-interfaces default
   passive-interface
  exit-af-interface
```

| Setting | Scope | When to Use |
|---------|-------|-------------|
| `af-interface <X> passive-interface` | Just interface X | LAN/PC edge |
| `af-interface default passive-interface` | Every interface (then enable specific ones with `no passive-interface`) | Many passive LANs, few transits |

> **Exam tip:** A passive interface is **enrolled** (its subnet is advertised) but **silent** (no hellos). Misplacing it on a transit link is the #2 cause of "enrolled but no neighbor" after missing network statements.

### Common EIGRP Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| `K-value mismatch` syslog, no neighbor on IPv4 only | `metric weights` mismatch in IPv4 AF |
| IPv6 neighbor up, IPv4 neighbor missing on same link | Missing `network` statement under IPv4 AF |
| Interface enrolled, hellos not sent | `af-interface <X> passive-interface` on the transit link |
| Neighbor up, no routes learned from one specific router | `eigrp stub receive-only` on that router |
| More-specific /24 arrives at hub, summary /22 missing | `summary-address` absent on the summarizing router's egress |
| Single path installed where two were expected | `variance` missing or too low, **or** candidate failed FC |
| Discard Null0 route missing on summarizer | No `summary-address` present on any egress (Null0 is created by the first summary) |
| Neighbor flapping every few minutes | MTU mismatch, authentication clock skew, or unstable link |

### Wildcard-Mask Reference

| Subnet Mask | Wildcard Mask | Common Use in This Lab |
|-------------|---------------|------------------------|
| 255.255.255.252 | 0.0.0.3 | /30 transit links (10.12/13/23/24.0.0) |
| 255.255.255.0 | 0.0.0.255 | /24 LANs (PC1, PC2) |
| 255.255.252.0 | 0.0.3.255 | /22 summary (10.3.0.0) |
| 255.255.255.255 | 0.0.0.0 | Loopback host route |

---

## 8. Solutions (Spoiler Alert!)

> Try to diagnose each ticket using only `show` commands first. The solution for each fault lives in the corresponding ticket in Section 9; the per-device known-good configs live in `solutions/R1.cfg`, `solutions/R2.cfg`, `solutions/R3.cfg`, `solutions/R4.cfg`.

### Recovery strategy — fix in this order

Some faults mask others. Work them in the order that maximises observability:

1. **First — the K-value mismatch on R1.** It suppresses every R1 IPv4 adjacency, so none of R1's downstream symptoms are observable. Fix it and R1↔R2 + R1↔R3 come back in IPv4.
2. **Next — R3's transit-link passive-interface.** This hits the R2↔R3 IPv4 adjacency specifically. Until it's fixed, R2 and R3 cannot reach each other's loopbacks over IPv4 even though R1 can now reach both.
3. **Then — R2's missing IPv4 network statement for the R2↔R4 link.** Once this is fixed, R2 and R4 form an IPv4 adjacency and the direction-dependent symptoms on PC2 LAN reachability become visible.
4. **Next — R4's `eigrp stub receive-only`.** With the adjacency up, R4 needs to actually *advertise* PC2 LAN and its loopback. Swapping to `eigrp stub connected` fixes the silent-stub problem.
5. **Last — R2's missing `variance 8`.** Only relevant once every other adjacency is up and R2 has a full topology table; then the unequal-cost second path to PC1 LAN appears in `show ip route`.

### Consolidated fix summary

<details>
<summary>Click to view R1 correction (1 fault — Ticket 1)</summary>

```bash
! R1 — remove the non-default K-values so IPv4 adjacencies can reform
router eigrp EIGRP-LAB
 address-family ipv4 unicast autonomous-system 100
  no metric weights 0 2 0 1 0 0
 exit-address-family
```
</details>

<details>
<summary>Click to view R3 correction (1 fault — Ticket 2)</summary>

```bash
! R3 — remove the passive-interface from the transit-facing Gi0/1
router eigrp EIGRP-LAB
 address-family ipv4 unicast autonomous-system 100
  af-interface GigabitEthernet0/1
   no passive-interface
  exit-af-interface
 exit-address-family
```
</details>

<details>
<summary>Click to view R2 corrections (2 faults — Tickets 3 and 5)</summary>

```bash
! R2 — restore Gi0/2 enrolment in IPv4 AF (Ticket 3)
!    — restore variance 8 in both AFs (Ticket 5)
router eigrp EIGRP-LAB
 address-family ipv4 unicast autonomous-system 100
  network 10.24.0.0 0.0.0.3
  variance 8
 exit-address-family
 address-family ipv6 unicast autonomous-system 100
  variance 8
 exit-address-family
```
</details>

<details>
<summary>Click to view R4 correction (1 fault — Ticket 4)</summary>

```bash
! R4 — swap receive-only for connected so the stub actually advertises PC2 LAN
router eigrp EIGRP-LAB
 address-family ipv4 unicast autonomous-system 100
  no eigrp stub receive-only
  eigrp stub connected
 exit-address-family
```
</details>

> Full per-device solutions also live in `solutions/R1.cfg`, `R2.cfg`, `R3.cfg`, `R4.cfg`.

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. `setup_lab.py` loads all five faults at once so you can work the scenario realistically. The individual inject scripts rebuild one fault at a time for focused repetition after the first end-to-end pass.

### Workflow

```bash
python3 setup_lab.py                                   # load the full pre-broken state (all 5 faults)
python3 scripts/fault-injection/apply_solution.py      # restore known-good (when finished or stuck)

# Focused single-fault practice (after solving the full scenario once):
python3 scripts/fault-injection/inject_scenario_01.py  # Ticket 1 only
python3 scripts/fault-injection/inject_scenario_02.py  # Ticket 2 only
python3 scripts/fault-injection/inject_scenario_03.py  # Ticket 3 only
python3 scripts/fault-injection/inject_scenario_04.py  # Ticket 4 only
python3 scripts/fault-injection/inject_scenario_05.py  # Ticket 5 only
```

---

### Ticket 1 — R1 Syslog Floods with K-value Mismatch, No IPv4 Neighbors

The NOC dashboard on R1 is lit up with a periodic `%DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor ... is down: K-value mismatch` message, repeating for both R2 and R3. `show ip eigrp neighbors` on R1 returns an empty table. `show ipv6 eigrp neighbors` on R1 shows both R2 and R3 as healthy. The IPv4 problem is one-sided — R1 is rejecting every IPv4 hello it receives.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py`

**Success criteria:** `show ip eigrp neighbors` on R1 shows both 10.12.0.2 (R2) and 10.13.0.2 (R3). No `K-value mismatch` lines in `show logging` over the next minute.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `show logging | include K-value` on R1 — confirm the mismatch and note that it repeats every 5 s (hello interval).
2. `show ipv6 eigrp neighbors` on R1 — both neighbors present. The fault is IPv4-only.
3. `show ip protocols | section eigrp` on R1 — look for the `Metric weight K1=..., K2=..., K3=..., K4=..., K5=...` line.
4. `show ip protocols | section eigrp` on R2 — compare the K-values. The default is `K1=1, K2=0, K3=1, K4=0, K5=0`.
5. Diff: R1 has a non-default set. R2 (and R3) still run defaults. Align R1 to the default.
6. `show running-config | section router eigrp` on R1 — find the `metric weights 0 2 0 1 0 0` line under the IPv4 AF.
</details>

<details>
<summary>Click to view Fix</summary>

The fault is on **R1 IPv4 AF**: a stray `metric weights 0 2 0 1 0 0` line (K1=2, K3=1 — K1 differs from default). R2 and R3 still use default K-values, so every hello R1 receives is rejected as a mismatch.

```bash
! R1
router eigrp EIGRP-LAB
 address-family ipv4 unicast autonomous-system 100
  no metric weights 0 2 0 1 0 0
 exit-address-family
```

Adjacencies reform in under 5 s. Verify `show ip eigrp neighbors` on R1 now shows two peers and the syslog noise stops.
</details>

---

### Ticket 2 — R2 and R3 Cannot See Each Other Over IPv4 on Gi0/1

Branch A ops reports that `show ip eigrp neighbors` on R2 omits R3 (10.23.0.2) — and R3's table likewise omits R2. IPv6 between them over the same link (`FE80::3` / `FE80::2`) is healthy. The physical link is up, IP addressing is correct, and there is no ACL or authentication configured on either end. `show ip eigrp interfaces` on R3 lists Gi0/1 — but with **zero peers** and zero hellos sent.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py`

**Success criteria:** `show ip eigrp neighbors` on R2 includes 10.23.0.2 (R3). `show ip eigrp neighbors` on R3 includes 10.23.0.1 (R2). `show ip protocols | section Passive` on R3 lists only Gi0/3 — no transit interface.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `show ip eigrp neighbors` on R2 — R3 missing.
2. `show ipv6 eigrp neighbors` on R2 — R3 present. The fault is IPv4-only.
3. `show ip eigrp interfaces` on R3 — Gi0/1 is listed (so the network statement is fine), but Peers column = 0.
4. `show ip protocols | section Passive` on R3 — look for transit links in the Passive list. Only Gi0/3 (PC1 LAN) should be there.
5. If Gi0/1 appears in the passive list: `show running-config | section router eigrp` on R3 — find the offending `passive-interface` under `af-interface GigabitEthernet0/1`.
</details>

<details>
<summary>Click to view Fix</summary>

The fault is on **R3 IPv4 AF**: a `passive-interface` has been added under `af-interface GigabitEthernet0/1`, which faces R2. R3 stops sending hellos on that interface — the subnet is still advertised (interface is enrolled), but no neighbor forms. IPv6 is untouched because IPv6 AF's `af-interface Gi0/1` is clean.

```bash
! R3
router eigrp EIGRP-LAB
 address-family ipv4 unicast autonomous-system 100
  af-interface GigabitEthernet0/1
   no passive-interface
  exit-af-interface
 exit-address-family
```

Note the summary-address line on the same af-interface must be **preserved** — only the passive-interface line is wrong. Verify with `show ip eigrp neighbors` on R2 (now shows R3) and `show ip protocols | section Passive` on R3 (now only Gi0/3).
</details>

---

### Ticket 3 — R2 Has No IPv4 Neighbor Toward R4 (IPv6 Neighbor Present)

Branch A ops reports that R2 sees R4 over IPv6 (`show ipv6 eigrp neighbors` lists `FE80::4` on Gi0/2), but R2's IPv4 table is blank for 10.24.0.0/30 — `show ip eigrp neighbors` does not list 10.24.0.2. R4's side mirrors the problem: R2 is missing from R4's IPv4 neighbor table. Gi0/2 on R2 is up, IP address is correct, no ACL.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py`

**Success criteria:** `show ip eigrp neighbors` on R2 includes 10.24.0.2 (R4). `show ip eigrp interfaces` on R2 includes Gi0/2. R4 appears in R2's IPv4 topology.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `show ip eigrp neighbors` on R2 — R4 missing on IPv4.
2. `show ipv6 eigrp neighbors` on R2 — R4 (`FE80::4`) present on IPv6. The fault is IPv4-only.
3. `show ip eigrp interfaces` on R2 — **Gi0/2 is missing** from the list. Enrolment, not hellos, is the problem. (Contrast with Ticket 2, where the interface was enrolled but silent.)
4. `show running-config | section router eigrp` on R2 — list of `network` statements under IPv4 AF. The expected 10.24.0.0/30 network is absent.
5. Cross-check against `solutions/R2.cfg` or the design: R2's IPv4 AF must enrol 10.24.0.0/30 alongside 10.12.0.0/30 and 10.23.0.0/30.
</details>

<details>
<summary>Click to view Fix</summary>

The fault is on **R2 IPv4 AF**: the `network 10.24.0.0 0.0.0.3` statement is missing. Without it, Gi0/2 is not enrolled in the IPv4 process — no hellos, no neighbor. IPv6 is fine because named-mode IPv6 AF auto-enrols every interface with an IPv6 address.

```bash
! R2
router eigrp EIGRP-LAB
 address-family ipv4 unicast autonomous-system 100
  network 10.24.0.0 0.0.0.3
 exit-address-family
```

Adjacency forms within 5 s. Verify with `show ip eigrp neighbors` on R2 (R4 now listed) and `show ip eigrp interfaces` on R2 (Gi0/2 now listed).
</details>

---

### Ticket 4 — PC2 LAN (192.168.2.0/24) Is Invisible to Core and Branch B

Once R1, R2, and R4 have healthy IPv4 adjacencies, the helpdesk escalates a new symptom: R1 and R3 still have no route to 192.168.2.0/24. `show ip route eigrp` on R1 is missing the prefix entirely. `show ip eigrp neighbors` on R2 shows R4 as a happy neighbor. `show ip eigrp topology 192.168.2.0/24` on R1 also comes up empty. The adjacency exists, but R4 appears to advertise **nothing** to R2.

**Inject:** `python3 scripts/fault-injection/inject_scenario_04.py`

**Success criteria:** `show ip route eigrp` on R1 includes `D 192.168.2.0/24 via 10.12.0.1`. `show ip protocols | section eigrp` on R4 shows `Stub, connected` — not `Stub, receive only`. R4's loopback (4.4.4.4/32) also appears in R1's and R3's tables.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `show ip eigrp neighbors` on R2 — R4 is a healthy neighbor (this is not an adjacency problem).
2. `show ip route eigrp` on R1 and R2 — 192.168.2.0/24 is missing.
3. `show ip eigrp topology all-links` on R2 — look for 192.168.2.0/24 as a received prefix. It's absent.
4. `show ip protocols | section eigrp` on R4 — look for the `Stub, ...` line. If it says `Stub, receive only`, R4 is advertising **nothing** over EIGRP.
5. `show running-config | section router eigrp` on R4 — confirm the offending `eigrp stub receive-only` line under the IPv4 AF. Note that the IPv6 AF likely still has `eigrp stub connected` (which is why the IPv6 prefix is fine).
</details>

<details>
<summary>Click to view Fix</summary>

The fault is on **R4 IPv4 AF**: `eigrp stub receive-only` instead of `eigrp stub connected`. `receive-only` means R4 accepts routes from its peer but advertises nothing — even its own PC2 LAN and loopback are invisible.

```bash
! R4
router eigrp EIGRP-LAB
 address-family ipv4 unicast autonomous-system 100
  no eigrp stub receive-only
  eigrp stub connected
 exit-address-family
```

Within seconds, R2 learns 192.168.2.0/24 and 4.4.4.4/32 from R4 and redistributes them into the rest of the domain. Verify with `show ip route eigrp` on R1 and R3 — both PC2 LAN and R4's loopback must now be present.
</details>

---

### Ticket 5 — R2's Route to PC1 LAN Installs Only One Next-Hop

After every adjacency is up and all the stub/summary routes are flowing, capacity planning reports that R2 has **one** next-hop to 192.168.1.0/24 instead of the planned two. `show ip route 192.168.1.0` on R2 lists only 10.12.0.1 (via R1 — the fast 1 Gbps / 1 Gbps path). The direct R2→R3 path (10.23.0.2, 100 Mbps) is in the topology table but not installed. The design calls for both paths to be active (unequal-cost load-balance).

**Inject:** `python3 scripts/fault-injection/inject_scenario_05.py`

**Success criteria:** `show ip route 192.168.1.0` on R2 lists **two** Routing Descriptor Blocks — 10.12.0.1 (via R1) and 10.23.0.2 (direct). `show ip eigrp topology 192.168.1.0/24` on R2 shows `2 Successor(s)`. Equivalent behaviour on the IPv6 prefix `2001:DB8:1:1::/64`.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `show ip route 192.168.1.0` on R2 — only one RDB. Note the single next-hop is the low-metric (fast) path.
2. `show ip eigrp topology 192.168.1.0/24` on R2 — confirm both paths are present as topology entries, but only 1 Successor.
3. Compute whether the second path passes the **feasibility condition** (FC): its AD must be < FD of the primary. The direct R3 path is via R3 itself, so its AD = R3's FD to 192.168.1.0/24 (which is small — R3 is directly connected). The primary FD via R1 is larger. **FC passes** — so the only reason the second path is not installed is **variance**.
4. `show running-config | section router eigrp` on R2 — look under both AFs for a `variance N` line. It's missing.
5. Cross-check design: R2 is the variance point for unequal-cost load balancing — the R2↔R3 link was deliberately set to `bandwidth 100000` to make the two paths asymmetric, and `variance 8` was added to install both.
</details>

<details>
<summary>Click to view Fix</summary>

The fault is on **R2 IPv4 and IPv6 AFs**: the `variance 8` statement has been removed from both. Without variance, EIGRP only installs equal-cost paths — and the bandwidth asymmetry on R2↔R3 means the two paths to 192.168.1.0/24 are not equal-cost.

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

Both address families need the `variance` line — they are independent. Verify with `show ip route 192.168.1.0` on R2 (now shows two RDBs with traffic-share counts 100 and 10) and `show ipv6 route 2001:DB8:1:1::/64` on R2 (same two-next-hop pattern).
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] `show ip eigrp neighbors` on R1 shows 2 neighbors (R2, R3)
- [ ] `show ip eigrp neighbors` on R2 shows 3 neighbors (R1, R3, R4)
- [ ] `show ip eigrp neighbors` on R3 shows 2 neighbors (R1, R2)
- [ ] `show ip eigrp neighbors` on R4 shows 1 neighbor (R2)
- [ ] `show ipv6 eigrp neighbors` on every router matches its IPv4 count
- [ ] `show ip protocols` on every router — default K-values (1-0-1-0-0)
- [ ] `show ip route eigrp` on R1 shows `D 192.168.1.0/24`, `D 192.168.2.0/24`, `D 10.3.0.0/22`
- [ ] `show ip route 192.168.1.0` on R2 shows two Routing Descriptor Blocks (unequal-cost)
- [ ] `show ip route eigrp` on R3 shows `D 192.168.2.0/24 via R1`
- [ ] `show ip route 10.3.0.0/22` on R3 shows `is a summary, ... Null0` (discard route)
- [ ] `show ip protocols | section eigrp` on R4 shows `Stub, connected`
- [ ] `show ip protocols | section Passive` on R3 lists only Gi0/3 (no transit)
- [ ] PC1 pings 192.168.2.10 (PC2) — IPv4 succeeds
- [ ] PC1 pings 2001:db8:2:2::10 (PC2) — IPv6 succeeds
- [ ] `show logging | include DUAL|K-value` — no new events in the last 2 minutes

### Troubleshooting

- [ ] Ticket 1 — R1 K-values restored to default; IPv4 adjacencies come back
- [ ] Ticket 2 — R3 Gi0/1 IPv4 passive removed; R2↔R3 IPv4 forms
- [ ] Ticket 3 — R2 IPv4 network for 10.24.0.0/30 restored; R2↔R4 IPv4 forms
- [ ] Ticket 4 — R4 IPv4 stub changed from `receive-only` to `connected`; PC2 LAN reachable from core
- [ ] Ticket 5 — R2 variance 8 restored in both AFs; two paths to PC1 LAN installed

---
