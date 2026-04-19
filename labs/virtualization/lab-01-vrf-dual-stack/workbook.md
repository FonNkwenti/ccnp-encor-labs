# Lab 01 — VRF with Dual-Stack and Inter-VRF Routing

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

**Exam Objective:** 2.2 / 2.2.a — Configure and verify VRF (VRF-Lite), Virtualization & VRF

This lab extends the IPv4-only VRF-Lite topology from Lab 00 to a dual-stack environment. You will add IPv6 address families to existing VRF definitions, configure IPv6 addresses on VRF-bound interfaces, build per-VRF IPv6 static routing, and implement inter-VRF route leaking. Together, these tasks demonstrate that IOS VRF segmentation works identically for both protocol families — and that deliberate leaking is the only way to cross the VRF boundary.

---

### IPv6 Address Family in VRF Definitions

Modern IOS uses the `vrf definition` stanza (not the legacy `ip vrf`) precisely because it supports both IPv4 and IPv6 address families. Each family must be explicitly enabled:

```
vrf definition CUSTOMER-A
 rd 65001:100
 !
 address-family ipv4
 exit-address-family
 !
 address-family ipv6
 exit-address-family
```

Without `address-family ipv6`, any `ipv6 address` configured on a VRF-bound interface is silently ignored — the interface accepts IPv6 config at the CLI but never installs routes into the VRF FIB. This is the most common dual-stack VRF misconfiguration.

Separately, `ipv6 unicast-routing` must be enabled globally. Even if VRF IPv6 AF is configured, IOS will not forward IPv6 frames between interfaces if this global command is absent.

---

### Per-VRF IPv6 Static Routing

Just as IPv4 VRF statics use `ip route vrf <name>`, IPv6 VRF statics use `ipv6 route vrf <name>`:

```
ipv6 route vrf CUSTOMER-A 2001:db8:a2::/64 2001:db8:ca13::2
```

The route is installed only in CUSTOMER-A's IPv6 RIB. A plain `show ipv6 route` (global table) will not show it. You must use `show ipv6 route vrf CUSTOMER-A` to verify. This mirrors the IPv4 behavior and is a common exam trap — candidates forget the `vrf` keyword when verifying.

---

### Inter-VRF Route Leaking via Cross-VRF Statics

IOS allows a static route in VRF-A to name an exit interface that belongs to VRF-B. The FIB lookup for the next hop is then performed in VRF-B's table, causing the packet to cross VRF boundaries:

```
ip route vrf CUSTOMER-B 192.168.1.1 255.255.255.255 GigabitEthernet0/2 192.168.1.1
```

Here the route is installed in CUSTOMER-B's FIB, but `GigabitEthernet0/2` belongs to CUSTOMER-A. When CUSTOMER-B forwards to 192.168.1.1, the packet exits the Gi0/2 interface in the CUSTOMER-A domain.

**Critical: prefix length matters.** Lab 00 added `Loopback2` in CUSTOMER-B with address `192.168.1.100/24`. That creates a connected route `192.168.1.0/24 [AD 0]` in CUSTOMER-B's IPv4 FIB. A leaked `/24` static (AD 1) would be suppressed by Longest Prefix Match — the connected route wins. The fix is to leak a **`/32` host route** for the specific gateway (192.168.1.1). A `/32` beats the `/24` connected route by LPM, regardless of AD.

---

### VRF-Aware vs VRF-Unaware Show Commands

| Command | Shows |
|---------|-------|
| `show ip route` | Global table only — no VRF routes |
| `show ip route vrf CUSTOMER-A` | CUSTOMER-A IPv4 RIB |
| `show ipv6 route vrf CUSTOMER-A` | CUSTOMER-A IPv6 RIB |
| `show ip vrf` | All VRF definitions and their interfaces |
| `show ipv6 interface brief` | All interfaces — note missing VRF context |
| `ping vrf CUSTOMER-A 192.168.2.1` | Sourced from CUSTOMER-A FIB |
| `ping vrf CUSTOMER-A 2001:db8:a2::1` | IPv6 sourced from CUSTOMER-A |

The exam frequently tests whether you add the `vrf <name>` keyword to verification commands. Without it, the command always looks at the global table and produces a misleading "no route" or "success" result.

---

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| Dual-stack VRF configuration | Add `address-family ipv6` to VRF definitions and assign IPv6 addresses on VRF-bound interfaces |
| Per-VRF IPv6 static routing | Build and verify IPv6 routes scoped to a specific VRF |
| Inter-VRF route leaking | Use cross-VRF exit interfaces to deliberately bridge two VRFs via static routes |
| LPM conflict analysis | Identify when a leaked route is masked by a more-specific connected route and fix with `/32` host routes |
| VRF-aware verification | Use `vrf <name>` variants of show commands to see routes and reachability inside a VRF |

---

## 2. Topology & Scenario

**Scenario:** GlobalCorp's network team has just completed a VRF-Lite rollout (Lab 00). The next work order is to extend each VRF to dual-stack (IPv4 + IPv6) in preparation for an IPv6-only branch office expansion. Additionally, the NOC has raised a new requirement: a single VRF-B management host (172.20.1.1) must be able to reach the CUSTOMER-A gateway at R1 for monitoring purposes — without collapsing VRF isolation. You will implement inter-VRF route leaking to satisfy this requirement in a controlled, auditable way.

```
              ┌─────────────────────────────┐
              │            R1               │
              │   (Branch A / VRF Host)     │
              │  Lo0: 1.1.1.1/32            │
              │  Lo1(B): 172.20.1.1/24      │
              │          2001:db8:b1::1/64  │
              │  Lo2(B): 192.168.1.100/24   │
              └──────┬──────────────────────┘
         Gi0/0       │                     │ Gi0/2 (CUST-A LAN)
   10.0.13.1/30      │                     │ 192.168.1.1/24
                     │                     │ 2001:db8:a1::1/64
         Gi0/0       │                     │        │
   10.0.13.2/30      │                     │        │ PC1
              ┌──────┴─────────────┐        │ 192.168.1.10/24
              │        R3          │        │ 2001:db8:a1::10/64
              │  (WAN Transport)   │
              │  Lo0: 3.3.3.3/32   │
              └──────┬─────────────┘
         Gi0/1       │                     │ Gi0/2 (CUST-A LAN)
   10.0.23.2/30      │                     │ 192.168.2.1/24
                     │                     │ 2001:db8:a2::1/64
         Gi0/0       │                     │        │
   10.0.23.1/30      │                     │        │ PC2
              ┌──────┴──────────────────────┘ 192.168.2.10/24
              │            R2               │ 2001:db8:a2::10/64
              │   (Branch B / VRF Host)     │
              │  Lo0: 2.2.2.2/32            │
              │  Lo1(B): 172.20.2.1/24      │
              │          2001:db8:b2::1/64  │
              │  Lo2(B): 192.168.2.100/24   │
              └─────────────────────────────┘
```

**VRF CUSTOMER-A transit (subinterfaces on Gi0/0.100 / Gi0/1.100):**

| Link | IPv4 | IPv6 |
|------|------|------|
| R1 Gi0/0.100 ↔ R3 Gi0/0.100 | 172.16.13.1/30 ↔ .2/30 | 2001:db8:ca13::1/64 ↔ ::2/64 |
| R2 Gi0/0.100 ↔ R3 Gi0/1.100 | 172.16.23.1/30 ↔ .2/30 | 2001:db8:ca23::1/64 ↔ ::2/64 |

> **L3 (not shown above):** R1 Gi0/1 ↔ R2 Gi0/1, `10.0.12.0/30` — global-table OSPF underlay; not a VRF transit link. See the cabling table in Section 3.

---

## 3. Hardware & Environment Specifications

**Platform:** EVE-NG (Intel/Windows). All routers use IOSv (IOSv 15.9.3M).

**Cabling:**

| Link | Source | Destination | Subnet |
|------|--------|-------------|--------|
| L1 | R1 Gi0/0 | R3 Gi0/0 | 10.0.13.0/30 |
| L2 | R2 Gi0/0 | R3 Gi0/1 | 10.0.23.0/30 |
| L3 | R1 Gi0/1 | R2 Gi0/1 | 10.0.12.0/30 |
| L4 | R1 Gi0/2 | PC1 | 192.168.1.0/24 |
| L5 | R2 Gi0/2 | PC2 | 192.168.2.0/24 |

**Console Access Table:**

| Device | Port | Connection Command |
|--------|------|--------------------|
| R1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R3 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| PC1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| PC2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |

---

## 4. Base Configuration

The `initial-configs/` directory contains Lab 00's completed solution — VRF-Lite is fully operational. The following is pre-loaded on all devices:

**Pre-loaded:**
- VRF definitions for CUSTOMER-A and CUSTOMER-B (IPv4 address family only)
- All interface IP addresses (IPv4 only — no IPv6 addresses configured yet)
- OSPF process 1 on global-table underlay interfaces
- IPv4 static routes for CUSTOMER-A inter-site reachability (R1, R2, R3)
- PC1 and PC2 IPv4 addresses and gateways

**NOT pre-loaded (you configure this):**
- IPv6 address family in VRF definitions
- Global IPv6 unicast routing
- IPv6 addresses on VRF-bound interfaces
- Per-VRF IPv6 static routes
- Inter-VRF route leaking (cross-VRF static routes)
- IPv6 addresses on PC1 and PC2

---

## 5. Lab Challenge: Core Implementation

Configure dual-stack VRF routing and inter-VRF route leaking as described below.

### Task 1: Enable IPv6 in VRF Definitions and Global Routing Table

- On R1, R2, and R3, extend each VRF definition that carries CUSTOMER-A traffic to support IPv6 by adding the IPv6 address family inside the VRF definition.
- On R1 and R2, also add the IPv6 address family to the CUSTOMER-B VRF definition.
- Enable global IPv6 unicast routing on R1, R2, and R3.

**Verification:** `show vrf` (or `show ip vrf detail`) on R1 must list both address families for CUSTOMER-A and CUSTOMER-B. `show running-config | include ipv6 unicast-routing` must return a match on all three routers.

---

### Task 2: Configure IPv6 Addresses on VRF-Bound Interfaces

Assign IPv6 addresses to VRF-bound interfaces on all three routers using the addressing table below.

| Router | Interface | VRF | IPv6 Address |
|--------|-----------|-----|--------------|
| R1 | Gi0/0.100 | CUSTOMER-A | 2001:db8:ca13::1/64 |
| R1 | Gi0/2 | CUSTOMER-A | 2001:db8:a1::1/64 |
| R1 | Lo1 | CUSTOMER-B | 2001:db8:b1::1/64 |
| R2 | Gi0/0.100 | CUSTOMER-A | 2001:db8:ca23::1/64 |
| R2 | Gi0/2 | CUSTOMER-A | 2001:db8:a2::1/64 |
| R2 | Lo1 | CUSTOMER-B | 2001:db8:b2::1/64 |
| R3 | Gi0/0.100 | CUSTOMER-A | 2001:db8:ca13::2/64 |
| R3 | Gi0/1.100 | CUSTOMER-A | 2001:db8:ca23::2/64 |

Also configure IPv6 addresses on PC1 (`2001:db8:a1::10/64`, gateway `2001:db8:a1::1`) and PC2 (`2001:db8:a2::10/64`, gateway `2001:db8:a2::1`).

**Verification:** `show ipv6 interface brief vrf CUSTOMER-A` on R1 must show Gi0/0.100 and Gi0/2 with their IPv6 addresses and status UP/UP. `ping vrf CUSTOMER-A 2001:db8:ca13::2` from R1 must succeed (transit reachability).

---

### Task 3: Configure Per-VRF IPv6 Static Routes for CUSTOMER-A

Add IPv6 static routes so PC1 and PC2 can reach each other's subnets over IPv6 via the VRF CUSTOMER-A path through R3.

- R1 needs a route to PC2's IPv6 LAN via R3's CUSTOMER-A transit interface.
- R2 needs a route to PC1's IPv6 LAN via R3's CUSTOMER-A transit interface.
- R3 needs routes to both PC LANs pointing back toward R1 and R2 respectively.

**Verification:** `show ipv6 route vrf CUSTOMER-A` on R1 must show a static route (`S`) to `2001:db8:a2::/64`. `ping vrf CUSTOMER-A 2001:db8:a2::1` from R1 must succeed. `ping 2001:db8:a2::10` from PC1 must succeed.

---

### Task 4: Configure Inter-VRF Route Leaking on R1

The NOC requires that R1's CUSTOMER-B management host (`172.20.1.1`) can reach the CUSTOMER-A gateway (`192.168.1.1`) on R1's LAN interface — and vice versa. Implement controlled inter-VRF route leaking using static routes only on R1.

- Install a host route in CUSTOMER-B's FIB pointing to the CUSTOMER-A gateway, using the CUSTOMER-A LAN interface as the exit path. Use a `/32` prefix.
- Install a host route in CUSTOMER-A's FIB pointing to the CUSTOMER-B loopback, using the CUSTOMER-B loopback interface as the exit path. Use a `/32` prefix.

The `/32` prefix length is required — explain in your notes why a `/24` would not work here.

**Verification:** `show ip route vrf CUSTOMER-B` on R1 must show a static host route (`S`) to `192.168.1.1/32`. `ping vrf CUSTOMER-B 192.168.1.1 source Loopback1` from R1 must succeed (source Lo1 172.20.1.1 proves genuine CUSTOMER-B traffic exits via CUSTOMER-A). `ping vrf CUSTOMER-A 172.20.1.1` from R1 must succeed.

---

### Task 5: Demonstrate VRF Isolation via Show Command Comparison

Run the following verification sequence to confirm that VRF-unaware commands cannot see VRF routes:

- Confirm that `show ip route` (global table) on R1 does **not** show `192.168.1.0/24` or `192.168.2.0/24`.
- Confirm that `show ipv6 route` (global table) on R1 does **not** show any `2001:db8:a1::` or `2001:db8:a2::` prefixes.
- Confirm that `show ip route vrf CUSTOMER-A` does show both `/24` LAN prefixes.
- Confirm that the inter-VRF leak routes appear in their respective VRF tables only.

**Verification:** Document the output differences between the global and per-VRF versions of `show ip route` and `show ipv6 route`. This distinction is a direct exam objective.

---

## 6. Verification & Analysis

### Task 1 — IPv6 AF in VRF Definitions

```bash
R1# show running-config | section vrf definition CUSTOMER-A
vrf definition CUSTOMER-A
 rd 65001:100
 !
 address-family ipv4        ! ← IPv4 AF present from lab-00
 exit-address-family
 !
 address-family ipv6        ! ← NEW: IPv6 AF must appear here
 exit-address-family

R1# show running-config | include ipv6 unicast-routing
ipv6 unicast-routing        ! ← must be present on all three routers
```

### Task 2 — IPv6 Addresses on VRF Interfaces

```bash
R1# show ipv6 interface GigabitEthernet0/0.100
GigabitEthernet0/0.100 is up, line protocol is up
  VRF is CUSTOMER-A
  IPv6 is enabled, link-local address is FE80::...
  Global unicast address(es):
    2001:db8:ca13::1, subnet is 2001:db8:ca13::/64   ! ← transit address confirmed

R1# show ipv6 interface GigabitEthernet0/2
GigabitEthernet0/2 is up, line protocol is up
  VRF is CUSTOMER-A
  IPv6 is enabled, link-local address is FE80::...
  Global unicast address(es):
    2001:db8:a1::1, subnet is 2001:db8:a1::/64       ! ← LAN address confirmed

R1# ping vrf CUSTOMER-A 2001:db8:ca13::2
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 2001:db8:ca13::2, timeout is 2 seconds:
!!!!!                                                 ! ← R3 transit reachable
```

### Task 3 — Per-VRF IPv6 Static Routes

```bash
R1# show ipv6 route vrf CUSTOMER-A
IPv6 Routing Table - CUSTOMER-A - 3 entries
...
C   2001:db8:a1::/64 [0/0]
     via GigabitEthernet0/2, directly connected                ! ← LAN connected
L   2001:db8:a1::1/128 [0/0]
     via GigabitEthernet0/2, receive
C   2001:db8:ca13::/64 [0/0]
     via GigabitEthernet0/0.100, directly connected
L   2001:db8:ca13::1/128 [0/0]
     via GigabitEthernet0/0.100, receive
S   2001:db8:a2::/64 [1/0]                                     ! ← static to PC2 LAN
     via 2001:db8:ca13::2

R1# ping vrf CUSTOMER-A 2001:db8:a2::1 source 2001:db8:a1::1
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 2001:db8:a2::1, timeout is 2 seconds:
!!!!!                                                           ! ← R2 LAN gateway reachable

PC1> ping 2001:db8:a2::10
84 bytes from 2001:db8:a2::10 icmp_seq=1 ttl=61 time=...      ! ← PC1 to PC2 end-to-end
```

### Task 4 — Inter-VRF Route Leaking

```bash
R1# show ip route vrf CUSTOMER-B
...
      192.168.0.0/8 is variably subnetted
S        192.168.1.1/32 [1/0]
           via GigabitEthernet0/2, 192.168.1.1    ! ← /32 host leak; exits CUST-A Gi0/2

R1# show ip route vrf CUSTOMER-A
...
      172.20.0.0/8 is variably subnetted
S        172.20.1.1/32 [1/0]
           via Loopback1, 172.20.1.1              ! ← /32 host leak; exits CUST-B Lo1

R1# ping vrf CUSTOMER-B 192.168.1.1 source Loopback1
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 192.168.1.1, timeout is 2 seconds:
!!!!!                                             ! ← CUSTOMER-B (Lo1 172.20.1.1) → CUSTOMER-A gateway

R1# ping vrf CUSTOMER-A 172.20.1.1
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 172.20.1.1, timeout is 2 seconds:
!!!!!                                             ! ← CUSTOMER-A can reach CUSTOMER-B loopback
```

### Task 5 — VRF Isolation Demonstration

```bash
R1# show ip route
...
      10.0.0.0/8 is variably subnetted
C        10.0.13.0/30 is directly connected, GigabitEthernet0/0
C        10.0.12.0/30 is directly connected, GigabitEthernet0/1
L        1.1.1.1/32 is directly connected, Loopback0
! No 192.168.x.x or 172.16.x.x prefixes here — VRF routes are invisible to global table

R1# show ipv6 route
IPv6 Routing Table - default - 3 entries
...
! No 2001:db8:a1:: or 2001:db8:ca13:: here — VRF IPv6 routes are invisible

R1# show ip route vrf CUSTOMER-A
...
C   192.168.1.0/24 via GigabitEthernet0/2     ! ← visible only with vrf keyword
S   192.168.2.0/24 via 172.16.13.2            ! ← static route via R3 transit
S   172.20.1.1/32  via Loopback1              ! ← inter-VRF leak appears here
```

---

## 7. Verification Cheatsheet

### VRF IPv6 Address Family

```
vrf definition <NAME>
 address-family ipv6
 exit-address-family
```

| Command | Purpose |
|---------|---------|
| `show running-config \| section vrf definition` | Confirm IPv6 AF is present in VRF stanza |
| `show vrf detail <NAME>` | Show AF configuration and assigned interfaces |

> **Exam tip:** `vrf definition` (not legacy `ip vrf`) is required for dual-stack VRF support. Mixing the two syntaxes on the same router causes unpredictable behavior.

### Global and Per-VRF IPv6 Routing

```
ipv6 unicast-routing
ipv6 address <addr>/<prefix>
ipv6 route vrf <NAME> <prefix>/<len> <next-hop>
```

| Command | Purpose |
|---------|---------|
| `show ipv6 unicast-routing` | Confirm global IPv6 forwarding is enabled |
| `show ipv6 interface brief` | All interfaces with IPv6 addresses and state |
| `show ipv6 route vrf <NAME>` | Per-VRF IPv6 RIB — always use `vrf <NAME>` |
| `ping vrf <NAME> <ipv6-addr>` | Test reachability inside a specific VRF |

> **Exam tip:** `show ipv6 route` without `vrf` shows only the global table. A "no route" result does not mean the VRF route is missing — check the VRF table explicitly.

### Inter-VRF Route Leaking

```
! Leak from VRF-B into VRF-A gateway (exit via VRF-A interface):
ip route vrf CUSTOMER-B <host>/32 <vrf-a-interface> <vrf-a-next-hop>

! Leak from VRF-A into VRF-B loopback (exit via VRF-B interface):
ip route vrf CUSTOMER-A <host>/32 <vrf-b-interface> <vrf-b-next-hop>
```

| Command | Purpose |
|---------|---------|
| `show ip route vrf <NAME>` | Confirm leaked /32 routes appear in target VRF |
| `ping vrf <NAME> <leaked-host>` | Verify cross-VRF forwarding works |
| `show ip cef vrf <NAME> <prefix>` | CEF adjacency for the leaked prefix |

> **Exam tip:** Always use `/32` host routes when leaking into a VRF that has overlapping connected prefixes. A `/24` static loses to a connected `/24` at AD 0, regardless of metric.

### Verification Commands

| Command | What to Look For |
|---------|-----------------|
| `show ip vrf` | All VRFs and their member interfaces |
| `show ipv6 route vrf CUSTOMER-A` | Static (`S`) routes to remote LAN prefixes |
| `show ip route vrf CUSTOMER-A` | Both `/24` LAN prefixes + any leaked `/32` |
| `show ip route vrf CUSTOMER-B` | Leaked `/32` to CUSTOMER-A gateway |
| `show ipv6 interface Gi0/0.100` | VRF assignment and IPv6 address present |
| `ping vrf CUSTOMER-A 2001:db8:a2::1` | R1 to R2 LAN gateway over VRF IPv6 |
| `ping vrf CUSTOMER-B 192.168.1.1 source Loopback1` | Cross-VRF leak (CUST-B Lo1 172.20.1.1 → CUST-A gateway) |

### IPv6 Prefix Quick Reference

| Purpose | Prefix |
|---------|--------|
| CUSTOMER-A R1-R3 transit | 2001:db8:ca13::/64 |
| CUSTOMER-A R2-R3 transit | 2001:db8:ca23::/64 |
| CUSTOMER-A PC1 LAN | 2001:db8:a1::/64 |
| CUSTOMER-A PC2 LAN | 2001:db8:a2::/64 |
| CUSTOMER-B R1 loopback | 2001:db8:b1::/64 |
| CUSTOMER-B R2 loopback | 2001:db8:b2::/64 |

### Common VRF Dual-Stack Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| `ipv6 address` accepted but not in `show ipv6 interface` | `address-family ipv6` missing from VRF definition |
| IPv6 routing works on one router but not the transit | `ipv6 unicast-routing` missing on transit router |
| Leaked `/24` route not in VRF FIB | Overlapping connected `/24` in the VRF beats static at AD 0 — use `/32` |
| `ping vrf CUSTOMER-A ipv6-addr` fails but IPv4 works | IPv6 static route missing from VRF table |
| `show ipv6 route` shows nothing | Missing `vrf <NAME>` — global table has no VRF routes |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Task 1: Enable IPv6 AF in VRF Definitions

<details>
<summary>Click to view R1, R2, R3 Configuration</summary>

```bash
! R1 and R2 (both CUSTOMER-A and CUSTOMER-B VRFs):
vrf definition CUSTOMER-A
 address-family ipv6
 exit-address-family
vrf definition CUSTOMER-B
 address-family ipv6
 exit-address-family
ipv6 unicast-routing

! R3 (CUSTOMER-A only):
vrf definition CUSTOMER-A
 address-family ipv6
 exit-address-family
ipv6 unicast-routing
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show running-config | section vrf definition CUSTOMER-A
show running-config | include ipv6 unicast-routing
```
</details>

---

### Task 2: IPv6 Addresses on VRF-Bound Interfaces

<details>
<summary>Click to view R1 Configuration</summary>

```bash
interface GigabitEthernet0/0.100
 ipv6 address 2001:db8:ca13::1/64
interface GigabitEthernet0/2
 ipv6 address 2001:db8:a1::1/64
interface Loopback1
 ipv6 address 2001:db8:b1::1/64
```
</details>

<details>
<summary>Click to view R2 Configuration</summary>

```bash
interface GigabitEthernet0/0.100
 ipv6 address 2001:db8:ca23::1/64
interface GigabitEthernet0/2
 ipv6 address 2001:db8:a2::1/64
interface Loopback1
 ipv6 address 2001:db8:b2::1/64
```
</details>

<details>
<summary>Click to view R3 Configuration</summary>

```bash
interface GigabitEthernet0/0.100
 ipv6 address 2001:db8:ca13::2/64
interface GigabitEthernet0/1.100
 ipv6 address 2001:db8:ca23::2/64
```
</details>

<details>
<summary>Click to view PC1 and PC2 Configuration</summary>

```bash
! PC1 (VPCS):
ip 2001:db8:a1::10/64 2001:db8:a1::1

! PC2 (VPCS):
ip 2001:db8:a2::10/64 2001:db8:a2::1
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ipv6 interface brief
show ipv6 interface GigabitEthernet0/0.100
ping vrf CUSTOMER-A 2001:db8:ca13::2
```
</details>

---

### Task 3: Per-VRF IPv6 Static Routes

<details>
<summary>Click to view R1 Configuration</summary>

```bash
ipv6 route vrf CUSTOMER-A 2001:db8:a2::/64 2001:db8:ca13::2
```
</details>

<details>
<summary>Click to view R2 Configuration</summary>

```bash
ipv6 route vrf CUSTOMER-A 2001:db8:a1::/64 2001:db8:ca23::2
```
</details>

<details>
<summary>Click to view R3 Configuration</summary>

```bash
ipv6 route vrf CUSTOMER-A 2001:db8:a1::/64 2001:db8:ca13::1
ipv6 route vrf CUSTOMER-A 2001:db8:a2::/64 2001:db8:ca23::1
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ipv6 route vrf CUSTOMER-A
ping vrf CUSTOMER-A 2001:db8:a2::1 source 2001:db8:a1::1
```
</details>

---

### Task 4: Inter-VRF Route Leaking on R1

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! Leak CUSTOMER-A gateway into CUSTOMER-B using /32 to beat the connected /24
ip route vrf CUSTOMER-B 192.168.1.1 255.255.255.255 GigabitEthernet0/2 192.168.1.1
! Leak CUSTOMER-B loopback into CUSTOMER-A
ip route vrf CUSTOMER-A 172.20.1.1 255.255.255.255 Loopback1 172.20.1.1
```

Why `/32` and not `/24`? R1's CUSTOMER-B VRF has `Loopback2` configured with
`192.168.1.100/24`. That creates a connected route `192.168.1.0/24` in CUSTOMER-B's
FIB with AD 0. A static `/24` (AD 1) loses to it — the leaked route never activates.
A `/32` for the specific host `192.168.1.1` wins by Longest Prefix Match regardless
of AD, because `/32 > /24`.
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ip route vrf CUSTOMER-B
show ip route vrf CUSTOMER-A
ping vrf CUSTOMER-B 192.168.1.1 source Loopback1
ping vrf CUSTOMER-A 172.20.1.1
```
</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. Inject the fault first, then
diagnose and fix using only show commands.

### Workflow

```bash
python3 setup_lab.py                                             # reset to known-good
python3 scripts/fault-injection/inject_scenario_01.py           # Ticket 1
python3 scripts/fault-injection/apply_solution.py               # restore
```

---

### Ticket 1 — PC1 Can Ping PC2 Over IPv4 but Not IPv6

Operations reports that after a recent maintenance window, PC1 can reach PC2's IPv4 address (`192.168.2.10`) but `ping 2001:db8:a2::10` from PC1 times out. All IPv4 VRF routing is intact.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py`

**Success criteria:** `ping 2001:db8:a2::10` from PC1 succeeds. `show ipv6 route vrf CUSTOMER-A` on R1 shows a static route (`S`) to `2001:db8:a2::/64`.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! 1. Confirm IPv4 works but IPv6 fails from PC1
PC1> ping 192.168.2.10       ! succeeds
PC1> ping 2001:db8:a2::10    ! fails

! 2. Check IPv6 VRF routing table on R1
R1# show ipv6 route vrf CUSTOMER-A
! S 2001:db8:a2::/64 is MISSING — that is the fault

! 3. Confirm the transit is working (IPv6 to R3)
R1# ping vrf CUSTOMER-A 2001:db8:ca13::2
! succeeds — the issue is the static route, not the interface

! 4. Confirm R3 and R2 have their IPv6 routes (to rule out transit fault)
R3# show ipv6 route vrf CUSTOMER-A
R2# show ipv6 route vrf CUSTOMER-A
! R3 has both /64 routes; R2 has its static to 2001:db8:a1::/64 — all OK
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
R1# configure terminal
R1(config)# ipv6 route vrf CUSTOMER-A 2001:db8:a2::/64 2001:db8:ca13::2
R1(config)# end
R1# write memory

! Verify:
R1# show ipv6 route vrf CUSTOMER-A
S   2001:db8:a2::/64 [1/0] via 2001:db8:ca13::2   ! ← route restored
R1# ping vrf CUSTOMER-A 2001:db8:a2::1 source 2001:db8:a1::1
!!!!!
```
</details>

---

### Ticket 2 — R1 CUSTOMER-B Host Reports No Path to 192.168.1.1

The NOC management tool (sourced from the CUSTOMER-B VRF context at R1) is reporting that `192.168.1.1` is unreachable. CUSTOMER-A to CUSTOMER-A traffic is unaffected. The NOC team suspects the inter-VRF routing policy was accidentally removed.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py`

**Success criteria:** `ping vrf CUSTOMER-B 192.168.1.1 source Loopback1` from R1 succeeds. `ping vrf CUSTOMER-A 172.20.1.1` from R1 succeeds. Both inter-VRF /32 routes appear in their respective VRF tables.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! 1. Confirm CUSTOMER-B to CUSTOMER-A is failing
R1# ping vrf CUSTOMER-B 192.168.1.1
.....    ! fails

! 2. Check CUSTOMER-B's routing table for the leaked /32
R1# show ip route vrf CUSTOMER-B
! 192.168.1.1/32 is MISSING — the inter-VRF leak static has been removed

! 3. Check the reverse direction too
R1# ping vrf CUSTOMER-A 172.20.1.1
.....    ! also fails

R1# show ip route vrf CUSTOMER-A
! 172.20.1.1/32 is MISSING — both leak routes are gone

! 4. Confirm CUSTOMER-A routes are otherwise intact (intra-VRF)
R1# ping vrf CUSTOMER-A 192.168.2.1
!!!!!    ! CUSTOMER-A intra-VRF is fine — only inter-VRF leaks are missing
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
R1# configure terminal
R1(config)# ip route vrf CUSTOMER-B 192.168.1.1 255.255.255.255 GigabitEthernet0/2 192.168.1.1
R1(config)# ip route vrf CUSTOMER-A 172.20.1.1 255.255.255.255 Loopback1 172.20.1.1
R1(config)# end
R1# write memory

! Verify:
R1# show ip route vrf CUSTOMER-B
S   192.168.1.1/32 [1/0] via GigabitEthernet0/2, 192.168.1.1   ! ← restored
R1# ping vrf CUSTOMER-B 192.168.1.1 source Loopback1
!!!!!                                                            ! ← cross-VRF path restored
R1# ping vrf CUSTOMER-A 172.20.1.1
!!!!!
```
</details>

---

### Ticket 3 — IPv6 Pings Across R3 Fail; IPv4 Works Perfectly

A change-window report says IPv6 connectivity for CUSTOMER-A stopped working between sites after a configuration push to R3 during last night's maintenance. IPv4 traffic (including `ping vrf CUSTOMER-A 192.168.2.1` from R1) still works. IPv6 pings beyond R3 fail.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py`

**Success criteria:** `show ipv6 route vrf CUSTOMER-A` on R3 shows connected and static routes. `ping vrf CUSTOMER-A 2001:db8:a2::1` from R1 succeeds.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! 1. Confirm IPv4 works but IPv6 fails
R1# ping vrf CUSTOMER-A 192.168.2.1
!!!!!   ! IPv4 to R2 LAN: OK

R1# ping vrf CUSTOMER-A 2001:db8:a2::1
.....   ! IPv6 to R2 LAN: fails

! 2. Check IPv6 transit reachability — does R1 reach R3's transit IPv6?
R1# ping vrf CUSTOMER-A 2001:db8:ca13::2
.....   ! Even the adjacent transit hop fails over IPv6

! 3. Check R3's IPv6 VRF table
R3# show ipv6 route vrf CUSTOMER-A
% IPv6 routing table CUSTOMER-A does not exist   ! ← the VRF has no IPv6 AF

! 4. Check R3's VRF definition — this is the primary tell
R3# show running-config | section vrf definition CUSTOMER-A
vrf definition CUSTOMER-A
 rd 65001:100
 !
 address-family ipv4        ! ← IPv4 AF still present
 exit-address-family
! address-family ipv6 is MISSING — this is the fault

! 5. Note: removing address-family ipv6 in IOSv 15.x may also strip the IPv6
!    addresses from member interfaces. Confirm Gi0/0.100 has lost its IPv6 addr:
R3# show running-config interface GigabitEthernet0/0.100
! ipv6 address 2001:db8:ca13::2/64 may be absent — removed along with the AF
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
R3# configure terminal
R3(config)# vrf definition CUSTOMER-A
R3(config-vrf)# address-family ipv6
R3(config-vrf-af)# exit-address-family
R3(config-vrf)# end
R3# write memory

! Verify:
R3# show ipv6 route vrf CUSTOMER-A
C   2001:db8:ca13::/64 [0/0] via GigabitEthernet0/0.100   ! ← connected restored
C   2001:db8:ca23::/64 [0/0] via GigabitEthernet0/1.100
S   2001:db8:a1::/64 [1/0] via 2001:db8:ca13::1
S   2001:db8:a2::/64 [1/0] via 2001:db8:ca23::1

R1# ping vrf CUSTOMER-A 2001:db8:a2::1 source 2001:db8:a1::1
!!!!!   ! ← end-to-end IPv6 restored
```
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] `address-family ipv6` added to VRF CUSTOMER-A on R1, R2, and R3
- [ ] `address-family ipv6` added to VRF CUSTOMER-B on R1 and R2
- [ ] `ipv6 unicast-routing` enabled on R1, R2, and R3
- [ ] R1 Gi0/0.100 has `2001:db8:ca13::1/64` (CUSTOMER-A)
- [ ] R1 Gi0/2 has `2001:db8:a1::1/64` (CUSTOMER-A)
- [ ] R1 Lo1 has `2001:db8:b1::1/64` (CUSTOMER-B)
- [ ] R2 Gi0/0.100 has `2001:db8:ca23::1/64` (CUSTOMER-A)
- [ ] R2 Gi0/2 has `2001:db8:a2::1/64` (CUSTOMER-A)
- [ ] R2 Lo1 has `2001:db8:b2::1/64` (CUSTOMER-B)
- [ ] R3 Gi0/0.100 has `2001:db8:ca13::2/64` (CUSTOMER-A)
- [ ] R3 Gi0/1.100 has `2001:db8:ca23::2/64` (CUSTOMER-A)
- [ ] PC1 has `2001:db8:a1::10/64` with gateway `2001:db8:a1::1`
- [ ] PC2 has `2001:db8:a2::10/64` with gateway `2001:db8:a2::1`
- [ ] R1 `ipv6 route vrf CUSTOMER-A 2001:db8:a2::/64 2001:db8:ca13::2` installed
- [ ] R2 `ipv6 route vrf CUSTOMER-A 2001:db8:a1::/64 2001:db8:ca23::2` installed
- [ ] R3 has IPv6 statics for both LAN prefixes in VRF CUSTOMER-A
- [ ] `show ipv6 route vrf CUSTOMER-A` on R1 shows `S 2001:db8:a2::/64`
- [ ] `ping 2001:db8:a2::10` from PC1 succeeds (end-to-end IPv6 via VRF)
- [ ] R1 `ip route vrf CUSTOMER-B 192.168.1.1 255.255.255.255 GigabitEthernet0/2` installed
- [ ] R1 `ip route vrf CUSTOMER-A 172.20.1.1 255.255.255.255 Loopback1` installed
- [ ] `ping vrf CUSTOMER-B 192.168.1.1 source Loopback1` from R1 succeeds (Lo1 172.20.1.1 → CUSTOMER-A gateway)
- [ ] `ping vrf CUSTOMER-A 172.20.1.1` from R1 succeeds
- [ ] `show ip route` (global) on R1 does NOT show VRF routes
- [ ] `show ipv6 route` (global) on R1 does NOT show VRF IPv6 routes

### Troubleshooting

- [ ] Ticket 1: Identified missing IPv6 VRF static on R1; restored `ipv6 route vrf CUSTOMER-A 2001:db8:a2::/64`; PC1 to PC2 IPv6 ping restored
- [ ] Ticket 2: Identified missing inter-VRF leak routes on R1; restored both `/32` cross-VRF statics; bidirectional inter-VRF pings pass
- [ ] Ticket 3: Identified missing `address-family ipv6` in R3's VRF CUSTOMER-A; restored AF; IPv6 transit through R3 restored
