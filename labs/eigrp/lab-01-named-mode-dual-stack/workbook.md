# Lab 01 — EIGRP Named Mode and Dual-Stack

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

**Exam Objective:** 3.2.a Layer 3 — EIGRP — configure and verify EIGRP operation,
including named mode and IPv6 (ENCOR 350-401).

Lab 00 built classic EIGRP on an IPv4-only triangle. Lab 01 keeps the same physical
topology but converts EIGRP to the modern **named-mode** model and activates a second
**IPv6** address-family alongside the existing IPv4 one. After this lab the student can
recognise a dual-stack EIGRP configuration, understand per-address-family controls, and
explain why Cisco publishes new EIGRP features only for named mode.

### From Classic to Named Mode

Classic EIGRP (`router eigrp 100`) is a single-protocol, single-AS process. Named mode
(`router eigrp <name>`) is a container — the process name is a local label, and the real
EIGRP instances live inside **address-families** keyed by `autonomous-system` number:

```
router eigrp EIGRP-LAB            ! name is local-only (never seen by neighbors)
 address-family ipv4 unicast autonomous-system 100
  ...
 address-family ipv6 unicast autonomous-system 100
  ...
```

Two neighbors form an adjacency if their **AS numbers match within the same AF** — the
named-mode label on each side can differ freely. The AS number inside each AF is the
number peers compare against the `hello` packet; neighbors see AS 100, not "EIGRP-LAB".

Why convert:

- All EIGRP features after IOS 15.0 (wide metrics, FHRP, service families, OTP) are
  named-mode only.
- Consolidates IPv4 and IPv6 under one process — easier to audit and maintain.
- Per-AF knobs (router-id, passive-interface, distribute-lists) are cleanly isolated.

### Address-Family Model

Inside each `address-family`, configuration is scoped:

| Knob | Classic mode | Named mode |
|------|--------------|------------|
| Router-ID | `eigrp router-id` under the process | `eigrp router-id` under each AF (independent) |
| Interface controls | `passive-interface Gi0/0` under the process | `af-interface Gi0/0` / `passive-interface` under each AF |
| Default interface behavior | N/A (per-interface only) | `af-interface default` applies to all interfaces in that AF |
| Authentication | `ip authentication mode eigrp 100 md5` on interface | `authentication mode md5` under `af-interface` |
| Summarization | `ip summary-address eigrp 100 ...` on interface | `summary-address` under `af-interface` |
| Network statements | `network X.X.X.X WILDCARD` | `network X.X.X.X WILDCARD` (IPv4 AF only; IPv6 AF auto-enables) |

IPv6 AF has **no** `network` statements. Any interface with an IPv6 address and
`no shutdown` is automatically enrolled; students opt out by placing `shutdown` or
`passive-interface` under the corresponding `af-interface`.

### EIGRP for IPv6

Running EIGRP for IPv6 requires:

1. `ipv6 unicast-routing` at global config (otherwise the router does not forward IPv6).
2. Each participating interface must have a **link-local** address — EIGRP uses link-local
   as the next-hop in all advertised routes. Configure explicitly
   (`ipv6 address FE80::1 link-local`) so it's predictable; without an explicit one the
   router picks an EUI-64-based address that changes with MAC assignments.
3. Each participating interface must have a **global unicast** IPv6 address.
4. The IPv6 AF must have an `eigrp router-id` (a 32-bit IPv4-style value) — without one,
   if no IPv4 interface carries an address the AF won't start.

Route advertisements list the IPv6 prefix with the **link-local** address as next-hop,
which is why peers must be on the same layer-2 segment.

### Classic vs Wide Metrics

The classic metric is 32-bit, computed from a Kbps-scale bandwidth and tens-of-microsecond
delay. Above ~10 Gbps the bandwidth term saturates (it becomes 1), so 10 G, 40 G, and
100 G links produce identical metrics — a modelling bug for modern topologies.

Named mode introduces the **wide metric**: 64-bit, delay-based, and scaled so that
1 Gbps = delay 10, 10 Gbps = 1, 100 Gbps = 0.1 (and so on). The result is divided by
`metric rib-scale` (default 128) to produce the RIB metric, which stays within 32 bits
and keeps legacy tooling working.

```
Wide metric (named)   = 65535 × (K1 × scaled_BW + K3 × scaled_Delay) × 256
Classic metric (old)  =          (10^7/BW_min  +     Delay_sum)      × 256
```

A neighbour in classic mode advertises classic metrics; a neighbour in named mode
advertises wide metrics. If both sides speak named mode, they negotiate wide. When one
side is classic and the other named, the named side falls back to classic for that
adjacency to stay compatible.

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| IPv6 interface addressing | Configure global unicast + explicit link-local on all transit links and loopbacks. |
| Classic→named migration | Remove `router eigrp 100`, rebuild under `router eigrp EIGRP-LAB` with AF blocks. |
| Address-family configuration | Set per-AF router-id, network statements, and interface controls. |
| Dual-stack verification | Distinguish IPv4 vs IPv6 neighbor tables, topology tables, and RIBs. |
| Wide metric recognition | Read the metric output of `show ip eigrp topology` and identify the named-mode signature. |

---

## 2. Topology & Scenario

```
                    ┌─────────────────────────────┐
                    │             R1              │
                    │        (Hub / Core)         │
                    │  Lo0: 1.1.1.1/32            │
                    │  Lo0: 2001:DB8:FF::1/128    │
                    └──────┬─────────────┬────────┘
                 Gi0/0     │             │     Gi0/1
        10.12.0.1/30 (.1)  │             │  (.1) 10.13.0.1/30
        2001:DB8:12::1/64  │             │  2001:DB8:13::1/64
                           │             │
        2001:DB8:12::2/64  │             │  2001:DB8:13::2/64
        10.12.0.2/30 (.2)  │             │  (.2) 10.13.0.2/30
                 Gi0/0     │             │     Gi0/0
                 ┌─────────┴─────┐   ┌───┴──────────────────┐
                 │       R2      │   │         R3           │
                 │  (Branch A)   │   │    (Branch B)        │
                 │ Lo0: 2.2.2.2  │   │  Lo0: 3.3.3.3        │
                 │ 2001:DB8:FF::2│   │  2001:DB8:FF::3      │
                 └────────┬──────┘   └──────┬──────┬────────┘
                     Gi0/1│                 │Gi0/1 │Gi0/3
                  10.23.0.1/30 ─────────── 10.23.0.2/30
                  2001:DB8:23::1/64        2001:DB8:23::2/64
                                                  │
                                      192.168.1.1/24
                                      2001:DB8:1:1::1/64
                                                  │
                                              ┌───┴───┐
                                              │  PC1  │
                                              │  VPC  │
                                              │.10 /24│
                                              │::10/64│
                                              └───────┘
```

### Scenario — "Bringing IPv6 to the Core"

You inherit the IPv4-only triangle from Lab 00. Architecture is rolling out IPv6 across
the enterprise and has asked you to pilot it on the three core routers. Management wants:

1. Every core router configured with IPv6 on all active interfaces, including loopbacks
   and the PC1 LAN.
2. A **single** EIGRP process that handles both IPv4 and IPv6 — no parallel protocol
   instances.
3. PC1 reachable over both protocols.

You decide to migrate EIGRP to named mode as part of the roll-out, because named mode is
required for IPv6 inside a unified process and is the long-term direction of Cisco
EIGRP. Your starting point is the Lab 00 solution.

---

## 3. Hardware & Environment Specifications

### EVE-NG Nodes

| Device | Role | Image | RAM | NVRAM | Interfaces used |
|--------|------|-------|-----|-------|-----------------|
| R1 | IOSv router (Hub) | i86bi-linux-l3-adventerprisek9 15.x | 512 MB | 256 KB | Gi0/0, Gi0/1, Lo0 |
| R2 | IOSv router (Branch A) | i86bi-linux-l3-adventerprisek9 15.x | 512 MB | 256 KB | Gi0/0, Gi0/1, Lo0 |
| R3 | IOSv router (Branch B) | i86bi-linux-l3-adventerprisek9 15.x | 512 MB | 256 KB | Gi0/0, Gi0/1, Gi0/3, Lo0 |
| PC1 | VPC host | vpcs 0.8+ | n/a | n/a | e0 |

### Cabling Table

| Link ID | A-side | B-side | IPv4 subnet | IPv6 subnet |
|---------|--------|--------|-------------|-------------|
| L1 | R1 Gi0/0 | R2 Gi0/0 | 10.12.0.0/30 | 2001:DB8:12::/64 |
| L2 | R1 Gi0/1 | R3 Gi0/0 | 10.13.0.0/30 | 2001:DB8:13::/64 |
| L3 | R2 Gi0/1 | R3 Gi0/1 | 10.23.0.0/30 | 2001:DB8:23::/64 |
| L4 | R3 Gi0/3 | PC1 e0   | 192.168.1.0/24 | 2001:DB8:1:1::/64 |

### Console Access Table

| Device | Port | Connection Command |
|--------|------|--------------------|
| R1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R3 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| PC1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |

Run `python3 setup_lab.py --host <eve-ng-ip>` to push the initial configs.

---

## 4. Base Configuration

`initial-configs/` is the exact Lab 00 solution: three routers in classic EIGRP mode
(`router eigrp 100`) with a working IPv4-only triangle. Everything you had working at
the end of Lab 00 — neighbor adjacencies, topology table, PC1 reachability — is present.

**Already pre-loaded:**

- IPv4 addressing on all transit links and PC1 LAN
- Loopback0 on R1/R2/R3 (IPv4 only)
- Classic EIGRP process (`router eigrp 100`) on R1/R2/R3
- `passive-interface GigabitEthernet0/3` under the classic process on R3
- PC1 has `192.168.1.10/24` and default gateway

**NOT pre-loaded (your job to add):**

- IPv6 unicast routing globally
- IPv6 addresses on any interface or loopback
- IPv6 link-local addresses
- Named-mode EIGRP process (`router eigrp EIGRP-LAB`)
- IPv4 address-family (inside named-mode process)
- IPv6 address-family (inside named-mode process)
- Per-AF passive-interface on R3's LAN
- IPv6 address on PC1

---

## 5. Lab Challenge: Core Implementation

### Task 1: Enable IPv6 routing globally

- Turn on IPv6 packet forwarding on R1, R2, and R3.

**Verification:** `show ipv6 protocols` must respond without "IPv6 routing is not enabled"
and `show running-config | include unicast-routing` must show the IPv6 line.

---

### Task 2: Add IPv6 addresses to all interfaces

- On every transit interface (Gi0/0, Gi0/1 on each router, and R3's Gi0/1 toward R2),
  configure:
  - An explicit **link-local** address of `FE80::<router-number>`.
  - A **global unicast** address from the `2001:DB8:<link>::<host>/64` subnet per the
    topology diagram.
- On Loopback0 on R1/R2/R3, add `2001:DB8:FF::<router-number>/128`.
- On R3 Gi0/3 (PC1 LAN), add `2001:DB8:1:1::1/64` and link-local `FE80::3`.
- On PC1, add IPv6 `2001:DB8:1:1::10/64` with gateway `2001:DB8:1:1::1`.

**Verification:** `show ipv6 interface brief` on each router must list the expected global
and link-local addresses on every participating interface.

---

### Task 3: Remove the classic EIGRP process

- Deconfigure the existing `router eigrp 100` process on all three routers.

**Verification:** `show running-config | section router eigrp` must return nothing on any
router. `show ip eigrp neighbors` must return "no neighbors" or fail cleanly.

---

### Task 4: Build the named-mode process with an IPv4 address-family

- Create a new named-mode EIGRP process with the name `EIGRP-LAB` on all three routers.
- Inside the process, open the **IPv4 unicast address-family** with autonomous-system 100.
- Inside the IPv4 AF on each router, set `eigrp router-id` to the router's Loopback0 IPv4
  address.
- Advertise all Lab 00 IPv4 networks using the same `network` statements you used
  previously:
  - R1 — Loopback0, 10.12.0.0/30, 10.13.0.0/30
  - R2 — Loopback0, 10.12.0.0/30, 10.23.0.0/30
  - R3 — Loopback0, 10.13.0.0/30, 10.23.0.0/30, 192.168.1.0/24

**Verification:** `show ip eigrp neighbors` on R1 must list two peers (R2 and R3).
`show ip route eigrp` on R1 must show `D` entries for 2.2.2.2/32, 3.3.3.3/32,
10.23.0.0/30, and 192.168.1.0/24.

---

### Task 5: Open the IPv6 address-family

- Inside the same named-mode process on each router, open the **IPv6 unicast
  address-family** with autonomous-system 100.
- Set `eigrp router-id` in the IPv6 AF to the router's Loopback0 IPv4 address (same value
  as the IPv4 AF).
- No network statements are needed — every IPv6-enabled interface is enrolled automatically.

**Verification:** `show ipv6 eigrp neighbors` on R1 must list two peers identified by their
link-local addresses. `show ipv6 route eigrp` on R1 must show entries for the R2 and R3
loopbacks and the PC1 LAN.

---

### Task 6: Keep the PC1 LAN passive in both AFs

- On R3, apply `passive-interface` on `GigabitEthernet0/3` under **both** the IPv4 and
  IPv6 address-families (the classic-mode passive setting does not carry over — you must
  set it per AF in named mode).

**Verification:** `show ip eigrp interfaces` on R3 must not list Gi0/3 in the active
interface list (passive interfaces appear only in `show ip eigrp interfaces detail`).
Same check for `show ipv6 eigrp interfaces`. PC1 must not receive any EIGRP hello
packets (no captures needed — absence is verified by the above).

---

### Task 7: Verify end-to-end dual-stack reachability

- From PC1, ping all three router loopbacks on IPv4 **and** on IPv6.

**Verification:**

- `ping 1.1.1.1`, `ping 2.2.2.2`, `ping 3.3.3.3` all succeed.
- `ping 2001:db8:ff::1`, `ping 2001:db8:ff::2`, `ping 2001:db8:ff::3` all succeed.

---

## 6. Verification & Analysis

### Task 1 — IPv6 forwarding enabled

```bash
R1# show running-config | include unicast-routing
ipv6 unicast-routing             ! ← must be present on R1, R2, R3
```

### Task 2 — IPv6 interface addressing

```bash
R1# show ipv6 interface brief
GigabitEthernet0/0     [up/up]
    FE80::1                                               ! ← explicit link-local
    2001:DB8:12::1                                        ! ← global unicast
GigabitEthernet0/1     [up/up]
    FE80::1                                               ! ← same LLA reused (standard)
    2001:DB8:13::1
Loopback0              [up/up]
    FE80::F816:3EFF:FE00:0                                ! ← auto LLA on loopback (OK)
    2001:DB8:FF::1                                        ! ← loopback /128
```

### Task 4 — IPv4 named-mode neighbors and routes

```bash
R1# show ip eigrp neighbors
EIGRP-IPv4 VR(EIGRP-LAB) Address-Family Neighbors for AS(100)      ! ← named VR header
H   Address     Interface  Hold Uptime  SRTT  RTO  Q  Seq
0   10.12.0.2   Gi0/0        13 00:02:15  10  200  0  7                  ! ← R2 peer
1   10.13.0.2   Gi0/1        11 00:02:10  12  200  0  6                  ! ← R3 peer

R1# show ip route eigrp
D    2.2.2.2/32 [90/2816] via 10.12.0.2, 00:02:15, Gi0/0        ! ← R2 loopback
D    3.3.3.3/32 [90/2816] via 10.13.0.2, 00:02:10, Gi0/1        ! ← R3 loopback
D    10.23.0.0/30 [90/3072] via 10.12.0.2, ..., Gi0/0
                  [90/3072] via 10.13.0.2, ..., Gi0/1
D    192.168.1.0/24 [90/3072] via 10.13.0.2, 00:02:10, Gi0/1    ! ← PC1 LAN
```

### Task 4 — Wide metric recognition

```bash
R1# show ip eigrp topology 2.2.2.2/32
EIGRP-IPv4 VR(EIGRP-LAB) Topology Entry for AS(100)/ID(1.1.1.1) for 2.2.2.2/32
  State is Passive, Query origin flag is 1, 1 Successor(s), FD is 163840, RIB is 1280
                                                            ! ^^^ 64-bit wide metric
                                                            ! ^^^^^^^^ scaled RIB value
  Descriptor Blocks:
  10.12.0.2 (GigabitEthernet0/0), from 10.12.0.2, Send flag is 0x0
      Composite metric is (163840/131072), route is Internal
```

The `FD is 163840` is the wide metric; `RIB is 1280` is after `rib-scale 128` division.
Compare to lab 00's `FD is 156160` (classic 32-bit). Same topology, different scale.

### Task 5 — IPv6 neighbors and routes

```bash
R1# show ipv6 eigrp neighbors
EIGRP-IPv6 VR(EIGRP-LAB) Address-Family Neighbors for AS(100)
H   Address                 Interface        Hold Uptime   SRTT   RTO  Q  Seq
0   Link-local address:     Gi0/0              14 00:02:30   5    100  0  5     ! ← next-hop is LLA
    FE80::2
1   Link-local address:     Gi0/1              12 00:02:25   6    100  0  4     ! ← always LLA
    FE80::3

R1# show ipv6 route eigrp
D   2001:DB8:FF::2/128 [90/2816]
     via FE80::2, GigabitEthernet0/0                      ! ← LLA next-hop
D   2001:DB8:FF::3/128 [90/2816]
     via FE80::3, GigabitEthernet0/1
D   2001:DB8:23::/64 [90/3072]
     via FE80::2, GigabitEthernet0/0
     via FE80::3, GigabitEthernet0/1                      ! ← equal-cost paths
D   2001:DB8:1:1::/64 [90/3072]
     via FE80::3, GigabitEthernet0/1                      ! ← PC1 LAN v6
```

### Task 7 — End-to-end PC1 reachability

```
PC1> ping 1.1.1.1
84 bytes from 1.1.1.1 icmp_seq=1 ttl=254 time=12.4 ms       ! ← IPv4 OK

PC1> ping 2001:db8:ff::1
84 bytes from 2001:db8:ff::1 icmp_seq=1 ttl=254 time=14.1 ms   ! ← IPv6 OK
```

---

## 7. Verification Cheatsheet

### Enabling IPv6

```
ipv6 unicast-routing
interface <name>
 ipv6 address FE80::<n> link-local
 ipv6 address <prefix>/<len>
```

| Command | Purpose |
|---------|---------|
| `ipv6 unicast-routing` | Enables IPv6 packet forwarding (global). |
| `ipv6 address FE80::1 link-local` | Pins an explicit link-local; overrides EUI-64. |
| `ipv6 address 2001:DB8:12::1/64` | Assigns a global unicast address. |

> **Exam tip:** Without an explicit link-local, the router picks an EUI-64 LLA based on
> the MAC — this changes if the interface is re-created and breaks neighbor reliability.

### EIGRP Named-Mode Skeleton

```
router eigrp <NAME>
 address-family ipv4 unicast autonomous-system <AS>
  eigrp router-id <ID>
  network <addr> <wildcard>
  af-interface <int>
   passive-interface
  exit-af-interface
 exit-address-family
 address-family ipv6 unicast autonomous-system <AS>
  eigrp router-id <ID>
  af-interface <int>
   passive-interface
  exit-af-interface
 exit-address-family
```

| Command | Purpose |
|---------|---------|
| `router eigrp EIGRP-LAB` | Starts named-mode process with local label `EIGRP-LAB`. |
| `address-family ipv4 unicast autonomous-system 100` | Opens the IPv4 AF on AS 100. |
| `address-family ipv6 unicast autonomous-system 100` | Opens the IPv6 AF on AS 100. |
| `eigrp router-id 1.1.1.1` | Sets the router-id for that AF (32-bit IPv4 format). |
| `network 10.12.0.0 0.0.0.3` | Enables EIGRP on matching IPv4 interfaces (IPv4 AF only). |
| `af-interface Gi0/3` | Enters AF-interface config for per-AF controls. |
| `passive-interface` | Stops hellos on that interface for this AF only. |
| `af-interface default` | Applies the following controls to every interface in this AF. |

> **Exam tip:** The `network` statement exists only under the IPv4 AF. For IPv6, every
> interface with an IPv6 address is enrolled automatically — opt out with `shutdown` or
> `passive-interface` under `af-interface`.

### Removing the Old Process

```
no router eigrp 100
```

| Command | Purpose |
|---------|---------|
| `no router eigrp 100` | Removes the classic EIGRP process entirely. |

### Verification Commands

| Command | What to Look For |
|---------|-----------------|
| `show ip eigrp neighbors` | Two peers per router, `EIGRP-IPv4 VR(EIGRP-LAB)` header = named mode. |
| `show ipv6 eigrp neighbors` | Two peers listed by link-local next-hop. |
| `show ip eigrp topology <prefix>` | `FD is <value>` — wide metric is 6-digit or larger; classic is 5-6 digit. |
| `show ip eigrp interfaces` | Active (non-passive) interfaces in the IPv4 AF. |
| `show ipv6 eigrp interfaces` | Active interfaces in the IPv6 AF. |
| `show ip protocols` | Lists the named process, AS number per AF, router-id. |
| `show ipv6 protocols` | Same, for IPv6 AF. |
| `show running-config | section router eigrp` | Full named-mode block — useful for diff. |
| `show ipv6 interface brief` | All IPv6 addresses (link-local + global) per interface. |

### Common Named-Mode / Dual-Stack Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| Named process created but no IPv4 neighbors | `network` statements missing under IPv4 AF. |
| IPv4 works, IPv6 does not | `ipv6 unicast-routing` missing; or `eigrp router-id` missing in IPv6 AF. |
| IPv6 neighbors stuck in Init | No explicit link-local on one end, or LLAs on different subnets. |
| Partial dual-stack (one AF only fails) | Per-AF `passive-interface`, per-AF `shutdown`, or AS number mismatch in one AF. |
| Neighbors form but no routes | `af-interface default / passive-interface` applied without re-enabling specific interfaces. |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Task 1 + Task 2: IPv6 global + interface addressing

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
 ipv6 address 2001:DB8:12::1/64
!
interface GigabitEthernet0/1
 ipv6 address FE80::1 link-local
 ipv6 address 2001:DB8:13::1/64
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
 ipv6 address 2001:DB8:12::2/64
!
interface GigabitEthernet0/1
 ipv6 address FE80::2 link-local
 ipv6 address 2001:DB8:23::1/64
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
 ipv6 address 2001:DB8:13::2/64
!
interface GigabitEthernet0/1
 ipv6 address FE80::3 link-local
 ipv6 address 2001:DB8:23::2/64
!
interface GigabitEthernet0/3
 ipv6 address FE80::3 link-local
 ipv6 address 2001:DB8:1:1::1/64
```
</details>

<details>
<summary>Click to view PC1 Configuration</summary>

```
ip 192.168.1.10 255.255.255.0 192.168.1.1
ip6 2001:db8:1:1::10/64 2001:db8:1:1::1
save
```
</details>

### Task 3 + Task 4 + Task 5 + Task 6: Named-mode dual-stack EIGRP

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1
no router eigrp 100
!
router eigrp EIGRP-LAB
 address-family ipv4 unicast autonomous-system 100
  eigrp router-id 1.1.1.1
  network 1.1.1.1 0.0.0.0
  network 10.12.0.0 0.0.0.3
  network 10.13.0.0 0.0.0.3
 exit-address-family
 !
 address-family ipv6 unicast autonomous-system 100
  eigrp router-id 1.1.1.1
 exit-address-family
```
</details>

<details>
<summary>Click to view R2 Configuration</summary>

```bash
! R2
no router eigrp 100
!
router eigrp EIGRP-LAB
 address-family ipv4 unicast autonomous-system 100
  eigrp router-id 2.2.2.2
  network 2.2.2.2 0.0.0.0
  network 10.12.0.0 0.0.0.3
  network 10.23.0.0 0.0.0.3
 exit-address-family
 !
 address-family ipv6 unicast autonomous-system 100
  eigrp router-id 2.2.2.2
 exit-address-family
```
</details>

<details>
<summary>Click to view R3 Configuration</summary>

```bash
! R3
no router eigrp 100
!
router eigrp EIGRP-LAB
 address-family ipv4 unicast autonomous-system 100
  af-interface GigabitEthernet0/3
   passive-interface
  exit-af-interface
  eigrp router-id 3.3.3.3
  network 3.3.3.3 0.0.0.0
  network 10.13.0.0 0.0.0.3
  network 10.23.0.0 0.0.0.3
  network 192.168.1.0 0.0.0.255
 exit-address-family
 !
 address-family ipv6 unicast autonomous-system 100
  af-interface GigabitEthernet0/3
   passive-interface
  exit-af-interface
  eigrp router-id 3.3.3.3
 exit-address-family
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show running-config | include unicast-routing
show ipv6 interface brief
show ip eigrp neighbors
show ipv6 eigrp neighbors
show ip route eigrp
show ipv6 route eigrp
show ip eigrp topology 2.2.2.2/32
show ip protocols
show ipv6 protocols
```
</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. Inject the fault first, then
diagnose and fix using only show commands.

### Workflow

```bash
python3 setup_lab.py                                   # first-time or reset
python3 scripts/fault-injection/apply_solution.py      # restore to known-good
python3 scripts/fault-injection/inject_scenario_01.py  # Ticket 1
python3 scripts/fault-injection/inject_scenario_02.py  # Ticket 2
python3 scripts/fault-injection/inject_scenario_03.py  # Ticket 3
```

---

### Ticket 1 — PC1 loses IPv4 connectivity to R2's loopback while IPv6 still works

The helpdesk reports that a monitoring probe on PC1 can still reach `2001:db8:ff::2`
but `ping 2.2.2.2` is failing. IPv4 routes through R2 have disappeared from R1 and R3,
yet `show ipv6 eigrp neighbors` on R2 shows both peers up. Restore IPv4 reachability
without disturbing the working IPv6 operation.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py`

**Success criteria:**

- `show ip eigrp neighbors` on R1 and R3 lists R2 as a peer again.
- PC1 can `ping 2.2.2.2` successfully.
- `show ipv6 eigrp neighbors` on R2 still shows both peers (unchanged).

<details>
<summary>Click to view Diagnosis Steps</summary>

1. From R1: `show ip eigrp neighbors` → R2 is missing. R3 still present.
2. From R1: `show ipv6 eigrp neighbors` → R2 **and** R3 present. So the fault is IPv4-only.
3. From R2: `show ip eigrp neighbors` → no peers. `show ipv6 eigrp neighbors` → both peers.
4. `show ip protocols` on R2:
   ```
   Routing Protocol is "eigrp 200"     ! ← wrong AS! Other routers speak AS 100.
     Address Family: IPv4 ...
   Routing Protocol is "eigrp 100"
     Address Family: IPv6 ...           ! ← IPv6 AF still on 100
   ```
5. `show running-config | section router eigrp` on R2 shows the IPv4 AF under
   `autonomous-system 200`, while IPv6 AF is still `autonomous-system 100`.

Root cause: R2's IPv4 address-family is configured under AS 200 instead of AS 100, so the
IPv4 hellos from R2 carry the wrong AS and R1/R3 drop them. IPv6 AF is unaffected.
</details>

<details>
<summary>Click to view Fix</summary>

Rebuild R2's IPv4 AF under the correct AS:

```bash
R2(config)# router eigrp EIGRP-LAB
R2(config-router)#  no address-family ipv4 unicast autonomous-system 200
R2(config-router)#  address-family ipv4 unicast autonomous-system 100
R2(config-router-af)#   eigrp router-id 2.2.2.2
R2(config-router-af)#   network 2.2.2.2 0.0.0.0
R2(config-router-af)#   network 10.12.0.0 0.0.0.3
R2(config-router-af)#   network 10.23.0.0 0.0.0.3
R2(config-router-af)#   exit-address-family
```

Verify:
- `show ip eigrp neighbors` on R1, R2, R3 all show the expected two peers.
- `PC1> ping 2.2.2.2` succeeds.
</details>

---

### Ticket 2 — R3 Loses Its Direct IPv6 EIGRP Adjacency to R1

On R3, `show ipv6 eigrp neighbors` no longer lists R1 (via Gi0/0). `show ip route eigrp`
still shows `1.1.1.1/32` and the physical R1-R3 link is healthy — the fault is IPv6-only.
The IPv6 route `2001:DB8:FF::1/128` may still appear via R2 (alternate path), but the
direct adjacency on Gi0/0 is gone.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py`

**Success criteria:**

- `show ipv6 eigrp neighbors` on R3 lists the R1 peer again (via Gi0/0).
- `show ipv6 route eigrp` on R3 lists `2001:DB8:FF::1/128`.
- `show ip eigrp neighbors` on R3 is unchanged from pre-fault (two peers, R1 and R2).

<details>
<summary>Click to view Diagnosis Steps</summary>

1. From R3: `show ip eigrp neighbors` → both R1 and R2 present (IPv4 is fine).
2. From R3: `show ipv6 eigrp neighbors` → only R2 via Gi0/1. R1 is missing on Gi0/0.
3. Note: `2001:DB8:FF::1/128` may still appear via R2 (triangle topology provides an
   alternate path), but the direct adjacency on Gi0/0 is gone — the fault IS present.
4. The R1-R3 link is carrying IPv4 EIGRP but not IPv6 EIGRP — IPv6 has been disabled
   at the EIGRP level on R3 Gi0/0 while IPv4 remains active.
4. `show running-config | section router eigrp` on R3:
   ```
   router eigrp EIGRP-LAB
    address-family ipv6 unicast autonomous-system 100
     af-interface GigabitEthernet0/0
      shutdown                       ! ← IPv6 EIGRP is shut on this interface only
   ```
5. `show ipv6 eigrp interfaces` on R3 omits Gi0/0 from the active list.

Root cause: the `shutdown` command under `af-interface Gi0/0` inside the IPv6 AF
stops EIGRP-for-IPv6 on that interface while leaving the IPv4 AF and the interface
itself untouched.
</details>

<details>
<summary>Click to view Fix</summary>

Remove the per-AF interface shutdown:

```bash
R3(config)# router eigrp EIGRP-LAB
R3(config-router)#  address-family ipv6 unicast autonomous-system 100
R3(config-router-af)#   af-interface GigabitEthernet0/0
R3(config-router-af-interface)#    no shutdown
R3(config-router-af-interface)#    exit
R3(config-router-af)#   exit-address-family
```

Verify:
- `show ipv6 eigrp neighbors` on R3 shows R1 over Gi0/0.
- `show ipv6 route eigrp` on R3 includes `2001:DB8:FF::1/128`.
</details>

---

### Ticket 3 — R3 reports no IPv4 EIGRP neighbors; IPv6 stays healthy

A change window on R3 went wrong and now `show ip eigrp neighbors` on R3 shows no peers.
PC1 cannot reach 1.1.1.1 or 2.2.2.2 over IPv4. At the same time, R3's IPv6 adjacencies
are perfect — `show ipv6 eigrp neighbors` lists both R1 and R2, and PC1 still reaches
`2001:db8:ff::1` and `2001:db8:ff::2`. Find and fix the IPv4 fault without disturbing
IPv6.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py`

**Success criteria:**

- `show ip eigrp neighbors` on R3 lists R1 (Gi0/0) and R2 (Gi0/1).
- PC1 can ping 1.1.1.1 and 2.2.2.2.
- IPv6 state unchanged: `show ipv6 eigrp neighbors` on R3 still shows both peers.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. From R3: `show ip eigrp neighbors` → empty. `show ipv6 eigrp neighbors` → both peers.
2. The IPv4 AF is silent while IPv6 AF works. So something in the IPv4 AF is globally
   suppressing hellos on R3.
3. `show ip eigrp interfaces` on R3 → no interfaces listed as active.
4. `show ip protocols` on R3 → IPv4 AF lists all interfaces under "Passive Interface(s)".
5. `show running-config | section router eigrp` on R3:
   ```
   router eigrp EIGRP-LAB
    address-family ipv4 unicast autonomous-system 100
     af-interface default
      passive-interface             ! ← makes EVERY IPv4 interface passive by default
     exit-af-interface
   ```

Root cause: `af-interface default / passive-interface` in the IPv4 AF applied passive
behavior to all IPv4 interfaces on R3, so R3 sends no IPv4 hellos. IPv6 AF was not
touched.
</details>

<details>
<summary>Click to view Fix</summary>

Remove the default passive-interface from the IPv4 AF (keep Gi0/3 passive as required
by the design):

```bash
R3(config)# router eigrp EIGRP-LAB
R3(config-router)#  address-family ipv4 unicast autonomous-system 100
R3(config-router-af)#   af-interface default
R3(config-router-af-interface)#    no passive-interface
R3(config-router-af-interface)#    exit
R3(config-router-af)#   af-interface GigabitEthernet0/3
R3(config-router-af-interface)#    passive-interface
R3(config-router-af-interface)#    exit
```

Verify:
- `show ip eigrp neighbors` on R3 lists R1 and R2.
- `show ip eigrp interfaces` on R3 shows Gi0/0 and Gi0/1 active, Gi0/3 is not listed.
- `PC1> ping 1.1.1.1` and `ping 2.2.2.2` succeed.
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] `ipv6 unicast-routing` enabled on R1, R2, R3.
- [ ] Every transit interface has an explicit `FE80::<router-number>` link-local.
- [ ] Every transit interface has a `2001:DB8:<link>::/64` global unicast address.
- [ ] Loopback0 on R1/R2/R3 has `2001:DB8:FF::<n>/128`.
- [ ] R3 Gi0/3 has `2001:DB8:1:1::1/64`.
- [ ] PC1 has IPv6 `2001:DB8:1:1::10/64` with gateway set.
- [ ] Classic `router eigrp 100` is removed on all three routers.
- [ ] Named process `router eigrp EIGRP-LAB` exists on all three routers.
- [ ] IPv4 AF under AS 100 on all three routers, with matching `network` statements.
- [ ] IPv6 AF under AS 100 on all three routers, with `eigrp router-id` set.
- [ ] `show ip eigrp neighbors` lists two peers on every router.
- [ ] `show ipv6 eigrp neighbors` lists two peers on every router (by link-local).
- [ ] R3 Gi0/3 is passive in **both** AFs.
- [ ] PC1 can ping `1.1.1.1`, `2.2.2.2`, `3.3.3.3` (IPv4).
- [ ] PC1 can ping `2001:db8:ff::1`, `2001:db8:ff::2`, `2001:db8:ff::3` (IPv6).

### Troubleshooting

- [ ] Ticket 1 resolved — IPv4 reachability restored, IPv6 untouched.
- [ ] Ticket 2 resolved — IPv6 neighbor on R1-R3 link restored.
- [ ] Ticket 3 resolved — R3 IPv4 adjacencies restored without breaking IPv6 or the
      Gi0/3 passive requirement.
