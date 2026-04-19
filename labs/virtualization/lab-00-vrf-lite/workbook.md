# Lab 00 — VRF-Lite Routing Table Isolation

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

**Exam Objective:** 2.2 / 2.2.a — Configure and verify data path virtualization technologies: VRF

VRF (Virtual Routing and Forwarding) creates multiple independent routing tables on a single
router, allowing overlapping IP address spaces and traffic isolation. VRF-Lite extends this to
a multi-hop path where several routers each maintain VRF instances and forward traffic accordingly —
without the MPLS control plane required in full MPLS-VPN. Understanding VRF is foundational to
multi-tenant networking, SD-WAN segmentation, and the broader tunneling topics that follow in
this chapter.

### VRF Fundamentals

A VRF instance is a separate routing and forwarding table scoped to a named domain. Every router
has one implicit default VRF (the global routing table). When you create a named VRF, you get an
additional, isolated FIB. Packets arriving on an interface assigned to that VRF are looked up only
in that VRF's routing table — they cannot reach global-table destinations and global-table packets
cannot reach VRF destinations, unless explicit leaking is configured.

Key IOS command flow for modern VRF definition (IOS 15+):
```
vrf definition CUSTOMER-A
 rd 65001:100          ! Route Distinguisher — makes VPNv4 routes unique
 !
 address-family ipv4   ! Enable IPv4 in this VRF
 exit-address-family
```

The **route distinguisher (RD)** is an 8-byte value prepended to IPv4 prefixes to create a globally
unique VPNv4 address when the prefix is distributed via MP-BGP. In VRF-Lite (no MPLS), the RD is
still required syntax but has no operational effect on local forwarding — it is bookkeeping for
future BGP-based VPN integration.

### Interface Assignment and the IP-Removal Trap

Assigning an interface to a VRF with `vrf forwarding <name>` **removes any existing IP address**
from that interface. This is the most common mistake in VRF deployment:

```
interface GigabitEthernet0/2
 vrf forwarding CUSTOMER-A   ! ← IP address is removed here
 ip address 192.168.1.1 255.255.255.0   ! ← must re-apply
```

The sequence matters: configure `vrf forwarding` first, then `ip address`. Reversing the order
causes IOS to reject the `ip address` command because the interface is already in a different
VRF context.

### Sub-Interfaces and 802.1Q for VRF Transit

VRF-Lite across a shared transport router (R3) requires that each VRF have its own Layer 3
path through R3. Since each physical link already carries the global underlay, sub-interfaces
with 802.1Q encapsulation provide a clean, scalable way to multiplex VRF traffic:

```
interface GigabitEthernet0/0.100
 encapsulation dot1Q 100        ! VLAN tag 100 = CUSTOMER-A
 vrf forwarding CUSTOMER-A
 ip address 172.16.13.1 255.255.255.252
```

The physical interface (Gi0/0) remains in the global table with the underlay IP. The sub-interface
(Gi0/0.100) lives in VRF CUSTOMER-A. IOS creates a logical Layer 3 interface for each sub-interface,
tagged with the dot1Q VLAN ID. R3 does the same on its side — both ends agree on the tag.

### VRF-Aware Routing

Routing protocols and static routes must be VRF-aware to install prefixes into the correct table:

| Mechanism | VRF-aware syntax |
|---|---|
| Static route | `ip route vrf <name> <prefix> <mask> <next-hop>` |
| OSPF | `router ospf <pid> vrf <name>` |
| EIGRP (named) | `address-family ipv4 unicast vrf <name>` |

In this lab, static routes build the VRF CUSTOMER-A forwarding path across R3. The global OSPF
process (process 1) runs in the global table only and provides underlay reachability for loopbacks
and management — it has no visibility into VRF routes.

**Skills this lab develops:**

| Skill | Description |
|---|---|
| VRF definition | Create named VRF instances with RD and IPv4 address-family |
| Interface-to-VRF assignment | Assign physical and sub-interfaces to a VRF |
| Sub-interface creation | Use dot1Q encapsulation to carry multiple VRFs over one physical link |
| VRF-aware static routes | Install routes into a specific VRF table |
| VRF isolation verification | Confirm that VRF routing tables are independent |
| VRF show commands | Navigate per-VRF routing tables and interface assignments |

---

## 2. Topology & Scenario

**Scenario:** Horizon Telecom operates a shared WAN router (R3) that carries traffic for
multiple enterprise customers. Customer-A has branch sites at R1 and R2, each with a local
LAN. Customer-B also uses the same infrastructure. Your job is to configure VRF-Lite so that
Customer-A's traffic is isolated from Customer-B's traffic, even though both traverse the
same physical links through R3. End-to-end, PC1 at the R1 site must be able to ping PC2
at the R2 site through R3's shared WAN, entirely within VRF CUSTOMER-A.

```
          ┌─────────────────────────────┐
          │             R1              │
          │       (Site 1 Router)       │
          │     Lo0: 1.1.1.1/32         │
          │     Lo1 (CUST-B): 172.20.1.1│
          └──────┬──────────────────────┘
    Gi0/0 global │ 10.0.13.1/30
 Gi0/0.100 CUST-A│ 172.16.13.1/30
                 │
    Gi0/0 global │ 10.0.13.2/30
 Gi0/0.100 CUST-A│ 172.16.13.2/30
          ┌──────┴──────────────────────┐
          │             R3              │
          │   (Shared WAN Transport)    │
          │     Lo0: 3.3.3.3/32         │
          └──────┬──────────────────────┘
    Gi0/1 global │ 10.0.23.2/30
 Gi0/1.100 CUST-A│ 172.16.23.2/30
                 │
    Gi0/0 global │ 10.0.23.1/30
 Gi0/0.100 CUST-A│ 172.16.23.1/30
          ┌──────┴──────────────────────┐
          │             R2              │
          │       (Site 2 Router)       │
          │     Lo0: 2.2.2.2/32         │
          │     Lo1 (CUST-B): 172.20.2.1│
          └─────────────────────────────┘

  R1 Gi0/1 (10.0.12.1/30) ─────────────── R2 Gi0/1 (10.0.12.2/30)  [global direct link]

  R1 Gi0/2 (CUST-A: 192.168.1.1/24)
       │ PC1: 192.168.1.10/24

  R2 Gi0/2 (CUST-A: 192.168.2.1/24)
       │ PC2: 192.168.2.10/24
```

**Key topology relationships:**
- R3 is the shared transport — it carries both global underlay and VRF CUSTOMER-A traffic over the same physical links using sub-interfaces
- The global table runs OSPF (process 1) for loopback reachability — this is pre-configured
- VRF CUSTOMER-A has its own transit IPs (172.16.13.0/30, 172.16.23.0/30) on sub-interfaces, completely separate from the global underlay
- PC1 and PC2 are end-hosts in VRF CUSTOMER-A — their gateways are R1/R2's LAN interfaces assigned to that VRF

---

## 3. Hardware & Environment Specifications

| Device | Platform | Role | Key IPs |
|--------|----------|------|---------|
| R1 | IOSv (IOS 15.9) | Site 1 Router | Lo0: 1.1.1.1, LAN: 192.168.1.1 |
| R2 | IOSv (IOS 15.9) | Site 2 Router | Lo0: 2.2.2.2, LAN: 192.168.2.1 |
| R3 | IOSv (IOS 15.9) | Shared WAN Transport | Lo0: 3.3.3.3 |
| PC1 | VPCS | End host — CUSTOMER-A site 1 | 192.168.1.10/24 |
| PC2 | VPCS | End host — CUSTOMER-A site 2 | 192.168.2.10/24 |

**Cabling Table:**

| Link | Source | Destination | Subnet | Purpose |
|------|--------|-------------|--------|---------|
| L1 | R1 Gi0/0 | R3 Gi0/0 | 10.0.13.0/30 | WAN underlay (global) |
| L2 | R2 Gi0/0 | R3 Gi0/1 | 10.0.23.0/30 | WAN underlay (global) |
| L3 | R1 Gi0/1 | R2 Gi0/1 | 10.0.12.0/30 | Direct link (global) |
| L4 | R1 Gi0/2 | PC1 | 192.168.1.0/24 | CUSTOMER-A LAN site 1 |
| L5 | R2 Gi0/2 | PC2 | 192.168.2.0/24 | CUSTOMER-A LAN site 2 |

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

Run `python3 setup_lab.py --host <eve-ng-ip>` to push the initial configuration to all nodes.

**Pre-configured on all routers:**
- Hostnames
- Interface IP addressing (global table, underlay links and loopbacks only)
- OSPF process 1 in area 0 (global table — underlay IGP)

**NOT pre-configured (student task):**
- VRF definitions
- Route distinguisher values
- IPv4 address family under VRF definitions
- Sub-interface creation and dot1Q encapsulation
- Interface-to-VRF assignments
- VRF-specific IP addressing on sub-interfaces and LAN interfaces
- VRF-aware static routes
- CUSTOMER-B isolation demonstration

---

## 5. Lab Challenge: Core Implementation

> Work through all five tasks in sequence. Do not read ahead to Section 8.

### Task 1: Define VRFs on All Routers

- Create VRF CUSTOMER-A on R1, R3, and R2. Assign it route distinguisher 65001:100.
  Enable the IPv4 address family within the VRF definition.
- Create VRF CUSTOMER-B on R1 and R2 only (R3 does not carry CUSTOMER-B traffic in this lab).
  Assign it route distinguisher 65001:200 and enable the IPv4 address family.

**Verification:** `show vrf` on each router must list CUSTOMER-A (on R1, R3, R2) and CUSTOMER-B (on R1, R2) with state "up".

---

### Task 2: Build the VRF CUSTOMER-A Transit Path Through R3

- On R1 and R3, create a sub-interface on the R1-R3 physical link. Use VLAN ID 100 as the dot1Q tag.
  Assign the sub-interface to VRF CUSTOMER-A and apply transit addresses:
  R1 side: 172.16.13.1/30, R3 side: 172.16.13.2/30.
- On R2 and R3, create a sub-interface on the R2-R3 physical link using the same VLAN ID 100.
  Assign to VRF CUSTOMER-A with transit addresses: R2 side 172.16.23.1/30, R3 side 172.16.23.2/30.

**Verification:** `show ip interface brief` must show the sub-interfaces up/up. `ping vrf CUSTOMER-A 172.16.13.2` from R1 must succeed.

---

### Task 3: Assign LAN Interfaces to VRF CUSTOMER-A

- On R1, move the LAN-facing interface (connected to PC1) into VRF CUSTOMER-A.
  Note: IOS removes the IP address when the VRF assignment is applied — re-apply 192.168.1.1/24 afterward.
- On R2, repeat the process for the LAN interface connected to PC2, applying 192.168.2.1/24.

**Verification:** `show ip vrf interfaces` must show Gi0/2 on R1 and R2 as members of CUSTOMER-A. PC1 should be able to ping its gateway 192.168.1.1.

---

### Task 4: Configure VRF-Aware Static Routes

- On R1: install a VRF CUSTOMER-A static route to reach R2's LAN (192.168.2.0/24) via R3's sub-interface address 172.16.13.2.
- On R3: install VRF CUSTOMER-A static routes in both directions — towards R1's LAN (192.168.1.0/24) via 172.16.13.1, and towards R2's LAN (192.168.2.0/24) via 172.16.23.1.
- On R2: install a VRF CUSTOMER-A static route to reach R1's LAN (192.168.1.0/24) via R3's sub-interface address 172.16.23.2.

**Verification:** `show ip route vrf CUSTOMER-A` on each router must show the remote LAN prefix. `ping vrf CUSTOMER-A 192.168.2.1` from R1 must succeed.

---

### Task 5: Demonstrate VRF Isolation with CUSTOMER-B

- On R1 and R2, assign the Loopback1 interface to VRF CUSTOMER-B and apply addresses:
  R1: 172.20.1.1/24, R2: 172.20.2.1/24.
- On R1, create a second loopback (Loopback2) in VRF CUSTOMER-B and assign address 192.168.1.100/24.
  On R2, create Loopback2 in VRF CUSTOMER-B and assign address 192.168.2.100/24.
  This places the same 192.168.1.0/24 and 192.168.2.0/24 prefixes in *both* CUSTOMER-A and
  CUSTOMER-B simultaneously — the key proof of overlapping address space.
- Verify that `show ip route vrf CUSTOMER-A` and `show ip route vrf CUSTOMER-B` on R1 both
  contain 192.168.1.0/24, yet neither table sees the other VRF's entry. The global table must
  show neither prefix.
- Attempt to ping the CUSTOMER-B loopback on R2 (172.20.2.1) from R1's global context — confirm
  it fails. Then ping with the CUSTOMER-B VRF context from R1 — confirm it also fails
  (no inter-site routing in CUSTOMER-B yet), demonstrating complete isolation.

**Verification:** `show ip route vrf CUSTOMER-A` on R1 must show 192.168.1.0/24 via Gi0/2 and NOT via Lo2. `show ip route vrf CUSTOMER-B` on R1 must show 192.168.1.0/24 via Lo2 and NOT via Gi0/2. `show ip route` (global) must show neither 192.168.1.0 nor 172.20.0.0.

---

## 6. Verification & Analysis

### Task 1 — VRF Definitions

```bash
R1# show vrf
  Name                             Default RD          Protocols   Interfaces
  CUSTOMER-A                       65001:100           ipv4              ! ← RD correct, ipv4 AF active
  CUSTOMER-B                       65001:200           ipv4              ! ← B present on R1

R3# show vrf
  Name                             Default RD          Protocols   Interfaces
  CUSTOMER-A                       65001:100           ipv4              ! ← R3 has CUSTOMER-A only

R2# show vrf
  Name                             Default RD          Protocols   Interfaces
  CUSTOMER-A                       65001:100           ipv4              ! ← same RD across all routers
  CUSTOMER-B                       65001:200           ipv4
```

### Task 2 — Sub-Interface Transit Links

```bash
R1# show ip interface brief
Interface                  IP-Address      OK? Method Status                Protocol
GigabitEthernet0/0         10.0.13.1       YES NVRAM  up                    up
GigabitEthernet0/0.100     172.16.13.1     YES NVRAM  up                    up      ! ← sub-intf up/up
GigabitEthernet0/1         10.0.12.1       YES NVRAM  up                    up
GigabitEthernet0/2         192.168.1.1     YES NVRAM  up                    up

R1# ping vrf CUSTOMER-A 172.16.13.2
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 172.16.13.2, timeout is 2 seconds:
!!!!!                                                                       ! ← 5/5 success = transit up
Success rate is 100 percent (5/5), round-trip min/avg/max = 1/1/2 ms

R3# show ip interface brief
Interface                  IP-Address      OK? Method Status                Protocol
GigabitEthernet0/0         10.0.13.2       YES NVRAM  up                    up
GigabitEthernet0/0.100     172.16.13.2     YES NVRAM  up                    up      ! ← both sub-intfs
GigabitEthernet0/1         10.0.23.2       YES NVRAM  up                    up
GigabitEthernet0/1.100     172.16.23.2     YES NVRAM  up                    up      ! ← both sides of R3
```

### Task 3 — LAN Interface in VRF

```bash
R1# show ip vrf interfaces
Interface              IP-Address      VRF                              Protocol
Gi0/0.100              172.16.13.1     CUSTOMER-A                       up          ! ← transit sub-intf
Gi0/2                  192.168.1.1     CUSTOMER-A                       up          ! ← LAN in VRF
Lo1                    172.20.1.1      CUSTOMER-B                       up

PC1> ping 192.168.1.1
84 bytes from 192.168.1.1 icmp_seq=1 ttl=255 time=0.5 ms                ! ← gateway reachable
```

### Task 4 — VRF Routing Tables

```bash
R1# show ip route vrf CUSTOMER-A
Routing Table: CUSTOMER-A
...
C    172.16.13.0/30 is directly connected, GigabitEthernet0/0.100      ! ← transit link
C    192.168.1.0/24 is directly connected, GigabitEthernet0/2          ! ← local LAN
S    192.168.2.0/24 [1/0] via 172.16.13.2                              ! ← static to R2 LAN

R3# show ip route vrf CUSTOMER-A
Routing Table: CUSTOMER-A
...
C    172.16.13.0/30 is directly connected, GigabitEthernet0/0.100
C    172.16.23.0/30 is directly connected, GigabitEthernet0/1.100
S    192.168.1.0/24 [1/0] via 172.16.13.1                              ! ← to R1 LAN
S    192.168.2.0/24 [1/0] via 172.16.23.1                              ! ← to R2 LAN

R2# show ip route vrf CUSTOMER-A
Routing Table: CUSTOMER-A
...
C    172.16.23.0/30 is directly connected, GigabitEthernet0/0.100
C    192.168.2.0/24 is directly connected, GigabitEthernet0/2
S    192.168.1.0/24 [1/0] via 172.16.23.2                              ! ← static to R1 LAN

PC1> ping 192.168.2.10
84 bytes from 192.168.2.10 icmp_seq=1 ttl=61 time=2.4 ms               ! ← end-to-end via VRF
```

### Task 5 — VRF Isolation and Overlapping Address Space

```bash
R1# show ip route vrf CUSTOMER-A
Routing Table: CUSTOMER-A
...
C    192.168.1.0/24 is directly connected, GigabitEthernet0/2          ! ← LAN via Gi0/2 (not Lo2)
! 172.20.0.0 does NOT appear — CUSTOMER-B routes invisible to CUSTOMER-A

R1# show ip route vrf CUSTOMER-B
Routing Table: CUSTOMER-B
C    172.20.1.0/24 is directly connected, Loopback1
C    192.168.1.0/24 is directly connected, Loopback2                   ! ← SAME prefix, different VRF
! Both VRFs contain 192.168.1.0/24 — this is the overlapping address space proof

R1# show ip route
! 192.168.1.0 does NOT appear — VRF routes invisible to global table   ! ← global isolation confirmed
! 172.20.0.0 does NOT appear

R1# ping 172.20.2.1 source Loopback0
% Success rate is 0 percent (0/5)                                       ! ← global cannot reach CUST-B

R1# ping vrf CUSTOMER-B 172.20.2.1
% Success rate is 0 percent (0/5)                                       ! ← no inter-site B routing yet
```

---

## 7. Verification Cheatsheet

### VRF Definition and Assignment

```
vrf definition <NAME>
 rd <ASN>:<NN>
 !
 address-family ipv4
 exit-address-family
```

| Command | Purpose |
|---------|---------|
| `vrf definition <NAME>` | Create a named VRF (IOS 15+ syntax) |
| `rd <ASN>:<NN>` | Assign Route Distinguisher |
| `address-family ipv4` | Enable IPv4 forwarding in VRF |

> **Exam tip:** `vrf definition` is IOS 15+ (modern). The older `ip vrf <NAME>` is classic IOS and lacks the `address-family` sub-mode. Know both forms — the exam may show either.

### Interface Assignment

```
interface GigabitEthernet0/2
 vrf forwarding <NAME>     ! removes existing IP — must re-apply below
 ip address <IP> <MASK>
```

| Command | Purpose |
|---------|---------|
| `vrf forwarding <NAME>` | Move interface into a VRF (IOS 15+) |
| `ip vrf forwarding <NAME>` | Classic syntax equivalent |

> **Exam tip:** `vrf forwarding` on a physical interface with an existing IP **always removes the IP**. Sub-interfaces have no IP until you apply one, so the trap doesn't apply there.

### Sub-Interface with 802.1Q for VRF Transit

```
interface GigabitEthernet0/0.<VLAN>
 encapsulation dot1Q <VLAN>
 vrf forwarding <NAME>
 ip address <IP> <MASK>
```

| Command | Purpose |
|---------|---------|
| `encapsulation dot1Q <VLAN>` | Tag sub-interface frames with VLAN ID |
| `vrf forwarding <NAME>` | Assign sub-interface to VRF |

### VRF-Aware Static Routes

```
ip route vrf <NAME> <prefix> <mask> <next-hop>
```

| Command | Purpose |
|---------|---------|
| `ip route vrf CUSTOMER-A 192.168.2.0 255.255.255.0 172.16.13.2` | Static route in VRF |

> **Exam tip:** The next-hop must be reachable within the same VRF. A global-table next-hop will not resolve for a VRF static route.

### Verification Commands

| Command | What to Look For |
|---------|-----------------|
| `show vrf` | All VRF names, RDs, protocols, assigned interfaces |
| `show vrf brief` | Compact view — name and interface count |
| `show ip vrf interfaces` | All interfaces with VRF assignments |
| `show ip route vrf <NAME>` | Full routing table for that VRF |
| `show ip interface brief` | All interfaces including sub-interfaces and their IPs |
| `ping vrf <NAME> <IP>` | VRF-aware ping from the router |
| `show running-config | section vrf` | All VRF definitions in one output |

### Common VRF-Lite Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| Sub-interface is up but VRF ping fails | Missing or wrong VRF assignment on one side |
| LAN interface in VRF has no IP | `vrf forwarding` removed the IP — re-apply it |
| `show ip route vrf` shows no routes | Missing static routes or VRF not defined on transit router |
| VRF route leaks into global table | Interface accidentally in global (no `vrf forwarding`) |
| `ping vrf` fails, direct connected shows in table | Sub-interface on far end in wrong VRF or missing |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Task 1: VRF Definitions

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1
vrf definition CUSTOMER-A
 rd 65001:100
 !
 address-family ipv4
 exit-address-family
!
vrf definition CUSTOMER-B
 rd 65001:200
 !
 address-family ipv4
 exit-address-family
```
</details>

<details>
<summary>Click to view R3 Configuration</summary>

```bash
! R3 — CUSTOMER-A only
vrf definition CUSTOMER-A
 rd 65001:100
 !
 address-family ipv4
 exit-address-family
```
</details>

<details>
<summary>Click to view R2 Configuration</summary>

```bash
! R2
vrf definition CUSTOMER-A
 rd 65001:100
 !
 address-family ipv4
 exit-address-family
!
vrf definition CUSTOMER-B
 rd 65001:200
 !
 address-family ipv4
 exit-address-family
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show vrf
show running-config | section vrf definition
```
</details>

---

### Task 2: Sub-Interface Transit Links

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1
interface GigabitEthernet0/0.100
 encapsulation dot1Q 100
 vrf forwarding CUSTOMER-A
 ip address 172.16.13.1 255.255.255.252
```
</details>

<details>
<summary>Click to view R3 Configuration</summary>

```bash
! R3
interface GigabitEthernet0/0.100
 encapsulation dot1Q 100
 vrf forwarding CUSTOMER-A
 ip address 172.16.13.2 255.255.255.252
!
interface GigabitEthernet0/1.100
 encapsulation dot1Q 100
 vrf forwarding CUSTOMER-A
 ip address 172.16.23.2 255.255.255.252
```
</details>

<details>
<summary>Click to view R2 Configuration</summary>

```bash
! R2
interface GigabitEthernet0/0.100
 encapsulation dot1Q 100
 vrf forwarding CUSTOMER-A
 ip address 172.16.23.1 255.255.255.252
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ip interface brief
ping vrf CUSTOMER-A 172.16.13.2   ! from R1
ping vrf CUSTOMER-A 172.16.23.2   ! from R2
```
</details>

---

### Task 3: LAN Interfaces in VRF

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1 — vrf forwarding removes IP; re-apply after
interface GigabitEthernet0/2
 vrf forwarding CUSTOMER-A
 ip address 192.168.1.1 255.255.255.0
 no shutdown
```
</details>

<details>
<summary>Click to view R2 Configuration</summary>

```bash
! R2
interface GigabitEthernet0/2
 vrf forwarding CUSTOMER-A
 ip address 192.168.2.1 255.255.255.0
 no shutdown
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ip vrf interfaces
! From PC1:
ping 192.168.1.1
```
</details>

---

### Task 4: VRF-Aware Static Routes

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1
ip route vrf CUSTOMER-A 192.168.2.0 255.255.255.0 172.16.13.2
```
</details>

<details>
<summary>Click to view R3 Configuration</summary>

```bash
! R3
ip route vrf CUSTOMER-A 192.168.1.0 255.255.255.0 172.16.13.1
ip route vrf CUSTOMER-A 192.168.2.0 255.255.255.0 172.16.23.1
```
</details>

<details>
<summary>Click to view R2 Configuration</summary>

```bash
! R2
ip route vrf CUSTOMER-A 192.168.1.0 255.255.255.0 172.16.23.2
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ip route vrf CUSTOMER-A
ping vrf CUSTOMER-A 192.168.2.1   ! from R1
! From PC1:
ping 192.168.2.10
```
</details>

---

### Task 5: CUSTOMER-B Isolation and Overlapping Addresses

<details>
<summary>Click to view R1 and R2 Configuration</summary>

```bash
! R1
interface Loopback1
 vrf forwarding CUSTOMER-B
 ip address 172.20.1.1 255.255.255.0
interface Loopback2
 vrf forwarding CUSTOMER-B
 ip address 192.168.1.100 255.255.255.0
!
! R2
interface Loopback1
 vrf forwarding CUSTOMER-B
 ip address 172.20.2.1 255.255.255.0
interface Loopback2
 vrf forwarding CUSTOMER-B
 ip address 192.168.2.100 255.255.255.0
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ip route vrf CUSTOMER-A      ! 192.168.1.0/24 present via Gi0/2; 172.20.0.0 absent
show ip route vrf CUSTOMER-B      ! 192.168.1.0/24 present via Lo2; 172.20.1.0/24 via Lo1
show ip route                     ! neither 192.168.x.0 nor 172.20.x.0 visible globally
ping 172.20.2.1 source Loopback0  ! global ping — must fail
ping vrf CUSTOMER-B 172.20.2.1    ! vrf ping — fails (no inter-site B routing)
```
</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. Inject the fault first, then diagnose and fix
using only show commands and logical reasoning.

### Workflow

```bash
python3 setup_lab.py --host <eve-ng-ip>                            # reset to initial config
# Apply full solution first:
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>
# Then inject a specific fault:
python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>  # Ticket 1
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>      # restore after each
```

---

### Ticket 1 — PC1 Cannot Ping PC2

Operations reports that PC1 at the R1 site has lost connectivity to PC2 at the R2 site.
The topology and cabling are unchanged. VRF configurations on R1 and R2 appear correct.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>`

**Success criteria:** PC1 can ping PC2 (192.168.2.10) and `show ip route vrf CUSTOMER-A` on R3
shows both 192.168.1.0/24 and 192.168.2.0/24 static routes.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! 1. Verify end-to-end from R1
R1# ping vrf CUSTOMER-A 192.168.2.1
! Fails — R1 cannot reach R2's LAN gateway

! 2. Check R1's VRF routing table — remote route present?
R1# show ip route vrf CUSTOMER-A
! S 192.168.2.0/24 present — R1 knows the route

! 3. Ping R3's sub-interface from R1
R1# ping vrf CUSTOMER-A 172.16.13.2
! Fails — R3's VRF sub-interface is unreachable

! 4. Check R3 VRF interfaces
R3# show ip vrf interfaces
! Gi0/0.100 and Gi0/1.100 are absent — VRF CUSTOMER-A missing from R3

! 5. Check if VRF is defined on R3
R3# show vrf
! CUSTOMER-A is not listed

! Root cause: VRF CUSTOMER-A was removed from R3 — sub-interfaces lost their VRF context
```
</details>

<details>
<summary>Click to view Fix</summary>

Re-create VRF CUSTOMER-A on R3 and reassign the sub-interfaces:

```bash
R3(config)# vrf definition CUSTOMER-A
R3(config-vrf)#  rd 65001:100
R3(config-vrf)#  !
R3(config-vrf)#  address-family ipv4
R3(config-vrf-af)#  exit-address-family
R3(config-vrf)# exit
R3(config)# interface GigabitEthernet0/0.100
R3(config-subif)#  encapsulation dot1Q 100
R3(config-subif)#  vrf forwarding CUSTOMER-A
R3(config-subif)#  ip address 172.16.13.2 255.255.255.252
R3(config)# interface GigabitEthernet0/1.100
R3(config-subif)#  encapsulation dot1Q 100
R3(config-subif)#  vrf forwarding CUSTOMER-A
R3(config-subif)#  ip address 172.16.23.2 255.255.255.252
```

Verify with `ping vrf CUSTOMER-A 172.16.13.2` from R1 and `ping vrf CUSTOMER-A 192.168.2.1`.
</details>

---

### Ticket 2 — R1 Has No Path to R2's LAN

The network team has verified that R3 is forwarding VRF CUSTOMER-A traffic normally. However,
R1 reports that PC2's subnet (192.168.2.0/24) is unreachable from R1's VRF context.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py --host <eve-ng-ip>`

**Success criteria:** `show ip route vrf CUSTOMER-A` on R1 shows `S 192.168.2.0/24` and
`ping vrf CUSTOMER-A 192.168.2.1` from R1 succeeds.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! 1. Confirm R1 VRF routing table
R1# show ip route vrf CUSTOMER-A
! 192.168.2.0/24 is absent — no route to R2 LAN

! 2. Verify transit is working
R1# ping vrf CUSTOMER-A 172.16.13.2
!!!!!  ! transit OK — R3 sub-interface reachable

! 3. Check R3's VRF routing table
R3# show ip route vrf CUSTOMER-A
! S 192.168.2.0/24 via 172.16.23.1 present — R3 has the route

! 4. Check R2
R2# show ip route vrf CUSTOMER-A
! S 192.168.1.0/24 absent — R2 also has no return route to R1 LAN

! Root cause: static route ip route vrf CUSTOMER-A 192.168.2.0 ... removed from R1;
! similarly ip route vrf CUSTOMER-A 192.168.1.0 ... removed from R2
```
</details>

<details>
<summary>Click to view Fix</summary>

Restore the missing static routes:

```bash
R1(config)# ip route vrf CUSTOMER-A 192.168.2.0 255.255.255.0 172.16.13.2

R2(config)# ip route vrf CUSTOMER-A 192.168.1.0 255.255.255.0 172.16.23.2
```

Verify with `show ip route vrf CUSTOMER-A` on both, then `ping vrf CUSTOMER-A 192.168.2.1` from R1.
</details>

---

### Ticket 3 — PC1 Can Ping Its Gateway but Cannot Reach PC2

PC1 can ping its default gateway (192.168.1.1) but cannot reach PC2 (192.168.2.10). Other
VRF functions on R1 appear intact. The R1 Gi0/2 interface is up and has the correct IP address.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py --host <eve-ng-ip>`

**Success criteria:** PC1 can ping PC2 (192.168.2.10) and `show ip vrf interfaces` on R1 shows
Gi0/2 as a member of CUSTOMER-A.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! 1. Confirm PC1 can ping its gateway but not PC2
PC1> ping 192.168.1.1   ! succeeds — R1 Gi0/2 still has the IP; ARP delivers the reply
PC1> ping 192.168.2.10  ! fails — transit routing through CUSTOMER-A VRF is broken

! 2. Check R1 global routing table — does 192.168.1.0/24 appear there?
R1# show ip route
! C 192.168.1.0/24 is directly connected, GigabitEthernet0/2
! ← subnet is in GLOBAL table, not in CUSTOMER-A VRF

! 3. Confirm VRF interface membership
R1# show ip vrf interfaces
! Gi0/2 is absent from CUSTOMER-A — interface was moved to the global routing table

! 4. Check running config
R1# show running-config interface GigabitEthernet0/2
! No "vrf forwarding CUSTOMER-A" line — vrf forwarding was removed

! Root cause: vrf forwarding was removed from R1 Gi0/2. The IP address stays on the
! interface (IOS moves it to the global table), so ARP and gateway pings still work.
! However, traffic arriving from PC1 on Gi0/2 now enters the global routing table,
! not CUSTOMER-A — the VRF static routes to 192.168.2.0/24 are invisible here.
```
</details>

<details>
<summary>Click to view Fix</summary>

Move R1 Gi0/2 back into VRF CUSTOMER-A and re-apply the IP (the `vrf forwarding` command removes it):

```bash
R1(config)# interface GigabitEthernet0/2
R1(config-if)#  vrf forwarding CUSTOMER-A
R1(config-if)#  ip address 192.168.1.1 255.255.255.0
R1(config-if)#  no shutdown
```

Verify with `show ip vrf interfaces` (Gi0/2 must show CUSTOMER-A) and PC1 `ping 192.168.1.1`.
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] VRF CUSTOMER-A defined on R1, R3, R2 with RD 65001:100 and IPv4 address-family
- [ ] VRF CUSTOMER-B defined on R1 and R2 with RD 65001:200 and IPv4 address-family
- [ ] R1 Gi0/0.100 in CUSTOMER-A: 172.16.13.1/30 (sub-interface, dot1Q 100)
- [ ] R3 Gi0/0.100 in CUSTOMER-A: 172.16.13.2/30 and Gi0/1.100: 172.16.23.2/30
- [ ] R2 Gi0/0.100 in CUSTOMER-A: 172.16.23.1/30 (sub-interface, dot1Q 100)
- [ ] R1 Gi0/2 in CUSTOMER-A: 192.168.1.1/24
- [ ] R2 Gi0/2 in CUSTOMER-A: 192.168.2.1/24
- [ ] Static route on R1: vrf CUSTOMER-A → 192.168.2.0/24 via 172.16.13.2
- [ ] Static routes on R3: both LAN prefixes in vrf CUSTOMER-A
- [ ] Static route on R2: vrf CUSTOMER-A → 192.168.1.0/24 via 172.16.23.2
- [ ] `ping vrf CUSTOMER-A 192.168.2.1` from R1 succeeds
- [ ] PC1 can ping PC2 (192.168.1.10 → 192.168.2.10)
- [ ] R1 Lo1 in CUSTOMER-B: 172.20.1.1/24; R2 Lo1 in CUSTOMER-B: 172.20.2.1/24
- [ ] R1 Lo2 in CUSTOMER-B: 192.168.1.100/24 (same prefix as CUSTOMER-A's LAN — overlapping address space)
- [ ] R2 Lo2 in CUSTOMER-B: 192.168.2.100/24 (same prefix as CUSTOMER-A's LAN)
- [ ] `show ip route vrf CUSTOMER-A` on R1 shows 192.168.1.0/24 via Gi0/2 only (not Lo2)
- [ ] `show ip route vrf CUSTOMER-B` on R1 shows 192.168.1.0/24 via Lo2 only (not Gi0/2)
- [ ] `show ip route` (global) on R1 shows neither 192.168.1.0 nor 172.20.0.0

### Troubleshooting

- [ ] Ticket 1 resolved: CUSTOMER-A VRF restored on R3, PC1-PC2 reachability confirmed
- [ ] Ticket 2 resolved: static routes restored on R1 and R2, routing table verified
- [ ] Ticket 3 resolved: R1 Gi0/2 back in CUSTOMER-A, PC1-PC2 reachability confirmed
