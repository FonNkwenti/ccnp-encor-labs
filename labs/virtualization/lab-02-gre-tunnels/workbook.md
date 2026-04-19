# Lab 02 — GRE Tunneling Over a Shared Transport

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

**Exam Objective:** 2.2 / 2.2.b — Configure and verify data path virtualization technologies: GRE and IPsec tunneling

This lab introduces GRE (Generic Routing Encapsulation) tunnels over a shared transport network. A new remote site (R4) is introduced; your job is to build a direct overlay connection from R1 to R4 that traverses the shared carrier (R3) without requiring R3 to know anything about the overlay routes. You will also run a second OSPF process over the tunnel to demonstrate dynamic routing through the overlay, extend the tunnel to carry IPv6, and use traceroute to prove that the overlay and underlay are separate routing planes.

---

### GRE Fundamentals

GRE (RFC 2784) wraps an original IP packet inside a new IP packet with a GRE header inserted between them:

```
┌──────────────────────────────────────────────────────────────┐
│  Outer IP Header  │  GRE Header (4 bytes)  │  Inner Payload  │
│  src=1.1.1.1      │  Protocol=0x0800 (IPv4)│  (original pkt) │
│  dst=4.4.4.4      │  or 0x86DD (IPv6)      │                 │
│  proto=47 (GRE)   │                        │                 │
└──────────────────────────────────────────────────────────────┘
```

Key properties:
- **Protocol number:** 47. Transport routers (R3) see IP proto=47 and forward without inspecting the inner packet.
- **No encryption.** GRE provides only encapsulation, not confidentiality. Add IPsec for encryption (lab-03).
- **Multicast support.** OSPF hellos (224.0.0.5/224.0.0.6) are carried through the tunnel, enabling dynamic routing protocols over GRE.
- **IPv4 and IPv6 inner payload.** Assign both an IPv4 and an IPv6 address to the tunnel interface and GRE carries both transparently.
- **Overhead.** GRE adds 24 bytes (20-byte outer IP + 4-byte GRE header). This reduces effective MTU. Use `ip mtu 1400` on the tunnel interface and `ip tcp adjust-mss 1360` to prevent fragmentation.

---

### Tunnel Source, Destination, and Loopback Stability

GRE tunnel configuration specifies a source IP and a destination IP for the outer header:

```
interface Tunnel0
 tunnel source Loopback0
 tunnel destination 4.4.4.4
```

The tunnel source determines which IP address appears in the outer header. Using a **loopback interface** as the source is best practice:

- A loopback never goes down due to cable pulls or transceiver failures.
- If a physical WAN interface flaps, the loopback remains up and the tunnel stays established.
- Using a physical interface as tunnel source would tear down the tunnel whenever that interface bounces — breaking all overlay traffic even if an alternate path exists.

The tunnel destination (`4.4.4.4`) must be reachable via the routing table at all times. IOS checks reachability to the tunnel destination continuously. If the route disappears, the tunnel line protocol goes DOWN. This is the most common GRE failure mode in practice.

---

### Overlay vs Underlay Routing

Introducing a GRE tunnel creates two parallel routing planes:

| Plane | Components | Purpose |
|-------|-----------|---------|
| **Underlay** | OSPF process 1, physical links, loopbacks | Provides reachability between tunnel endpoints (1.1.1.1 ↔ 4.4.4.4) |
| **Overlay** | GRE Tunnel0, OSPF process 2 | Carries application traffic; appears as a direct link between R1 and R4 |

The overlay routes (learned via OSPF process 2 over the tunnel) are only visible on R1 and R4. R3 — the shared transport — has no knowledge of overlay subnets. R3 routes GRE-encapsulated packets by the outer IP address alone.

This is the critical exam concept: the tunnel **appears as a direct link** between R1 and R4 even though the physical path is R1 → R3 → R4. A traceroute to the overlay destination shows only one hop (the far tunnel endpoint) while a traceroute to R4's underlay loopback shows R3 as an intermediate hop.

---

### GRE Tunnel Line Protocol State

IOS determines the GRE tunnel line protocol state based on two checks:

1. **Source interface up** — the interface named in `tunnel source` must be up and have an IP address.
2. **Destination reachable** — a route to the `tunnel destination` address must exist in the routing table.

Without keepalives (the default), the tunnel line protocol goes UP as soon as both conditions are met — even if the far end does not respond. With keepalives (`keepalive 10 3`), the router sends GRE keepalive probes and brings the line protocol DOWN if the far end doesn't echo them. Keepalives are optional but useful for fail-fast detection.

---

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| GRE tunnel configuration | Create and configure Tunnel0 with source/destination loopbacks, IP/IPv6 addresses, MTU/MSS |
| Overlay routing with OSPF | Run a second OSPF process over the GRE tunnel for dynamic overlay route exchange |
| IPv6 over GRE | Assign IPv6 to the tunnel interface and verify dual-stack inner payload delivery |
| Overlay vs underlay analysis | Use traceroute and show commands to distinguish the two routing planes |
| GRE failure diagnosis | Identify and fix broken tunnels by analyzing route reachability and interface state |

---

## 2. Topology & Scenario

**Scenario:** GlobalCorp has acquired a remote development site connected via a third-party carrier. The carrier's transport router (R3) is shared and does not belong to GlobalCorp — no VRF routing or direct configuration is possible on R3. The network team must extend connectivity from R1 (main site) to R4 (remote site) by building a GRE overlay tunnel that traverses R3 without R3 needing any awareness of the overlay routes. A second OSPF process will run inside the tunnel for dynamic route exchange. IPv6 support is also required.

```
              ┌──────────────────────────────────────┐
              │                R1                    │
              │      (Branch A / VRF Host)           │
              │  Lo0: 1.1.1.1/32                     │
              │  Tunnel0: 172.16.14.1/30             │
              │           2001:db8:14::1/64          │
              └──────┬────────────────────┬──────────┘
         Gi0/0       │ (L1)        (L3)   │ Gi0/1
   10.0.13.1/30      │          10.0.12.1/30
                     │                    │
   10.0.13.2/30      │          10.0.12.2/30
         Gi0/0       │          (L3)      │ Gi0/1
              ┌──────┴─────────┐    ┌─────┴────────────────────┐
              │      R3        │    │           R2             │
              │  (Transport)   │    │  (Branch B / VRF Host)   │
              │  Lo0: 3.3.3.3  │    │  Lo0: 2.2.2.2/32         │
              └──────┬─────────┘    └────────────────┬─────────┘
         Gi0/2       │ (L6)                  Gi0/2   │ (L5)
   10.0.34.1/30      │                192.168.2.1/24 │
                     │                               │
   10.0.34.2/30      │                              PC2
         Gi0/0       │                192.168.2.10/24
              ┌──────┴────────────────────────────────────────────┐
              │                     R4                            │
              │             (Remote Site)                         │
              │  Lo0: 4.4.4.4/32    Lo1: 10.4.4.4/32 (overlay)   │
              │  Tunnel0: 172.16.14.2/30  2001:db8:14::2/64       │
              └───────────────────────────────────────────────────┘
```

> PC1 attaches to R1 Gi0/2 (192.168.1.1/24, 2001:db8:a1::1/64). VRF CUSTOMER-A is pre-configured on R1/R2/R3 from previous labs — unchanged in this lab.

**GRE overlay link (not a physical cable):**

| Tunnel | R1 endpoint | R4 endpoint | IPv4 subnet | IPv6 subnet |
|--------|-------------|-------------|-------------|-------------|
| Tunnel0 | 172.16.14.1/30 | 172.16.14.2/30 | 172.16.14.0/30 | 2001:db8:14::/64 |

> Underlay path (physical): R1 → R3 → R4 (2 hops). Overlay path (GRE): R1 → R4 (1 hop via Tunnel0).

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
| L6 | R3 Gi0/2 | R4 Gi0/0 | 10.0.34.0/30 |

**Console Access Table:**

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

The `initial-configs/` directory contains the following pre-loaded state:

**Pre-loaded:**
- R1, R2, R3: complete lab-01 dual-stack VRF configuration (VRF CUSTOMER-A and CUSTOMER-B, inter-VRF leaking, OSPF process 1 underlay)
- R3: L6 underlay link (Gi0/2 toward R4, 10.0.34.1/30) and OSPF process 1 advertisement for it
- R4: Loopback0 (4.4.4.4/32), Loopback1 (10.4.4.4/32), Gi0/0 (10.0.34.2/30), OSPF process 1 (underlay only — Lo0 and Gi0/0 advertised in area 0)
- PC1 and PC2: IPv4 and IPv6 addressing from lab-01

**NOT pre-loaded (you configure this):**
- GRE Tunnel0 on R1 and R4
- OSPF process 2 (overlay routing over the tunnel)
- IPv6 addresses on Tunnel0 interfaces
- MTU and TCP MSS adjustments on tunnel interfaces

> **Pre-connectivity check:** Before starting, verify that R1 can ping R4's loopback: `ping 4.4.4.4 source 1.1.1.1`. If this fails, OSPF process 1 underlay is not working — resolve that first before configuring the tunnel.

---

## 5. Lab Challenge: Core Implementation

Configure a GRE tunnel with dual-stack overlay routing between R1 and R4.

### Task 1: Configure the GRE Tunnel Infrastructure

On R1, create a GRE tunnel interface (Tunnel0) using the loopback as the tunnel source and R4's loopback as the destination. Assign the IPv4 address `172.16.14.1/30` to the tunnel. Reduce the tunnel's IP MTU to 1400 bytes and adjust the TCP MSS to 1360 bytes. Configure the tunnel's OSPF network type as point-to-point.

On R4, configure the symmetric end of the same tunnel (source R4's loopback, destination R1's loopback), assign IPv4 address `172.16.14.2/30`, apply the same MTU/MSS settings, and set the OSPF network type to point-to-point.

**Verification:** `show interface Tunnel0` on R1 must show `Tunnel0 is up, line protocol is up`. `ping 172.16.14.2` from R1 must succeed (1 RTT, no fragmentation). `show interface Tunnel0` on R4 must also show up/up.

---

### Task 2: Enable OSPF Process 2 for Dynamic Overlay Routing

Start a second OSPF routing process (process 2) on R1 and R4. This process runs exclusively over the GRE tunnel — it must NOT be applied to any physical or VRF interface.

- On R1: advertise the tunnel subnet (`172.16.14.0/30`) into OSPF process 2, area 0. Use the same router-id as process 1 (1.1.1.1).
- On R4: advertise the tunnel subnet AND R4's overlay loopback network (`10.4.4.4/32`) into OSPF process 2, area 0.

**Verification:** `show ip ospf 2 neighbor` on R1 must show R4 (`4.4.4.4`) in FULL state. `show ip route ospf 2` on R1 must show a route to `10.4.4.4/32` via the tunnel. `ping 10.4.4.4 source 1.1.1.1` from R1 must succeed.

---

### Task 3: Extend the Tunnel to Carry IPv6

Assign IPv6 addresses to the Tunnel0 interface on both routers:
- R1 Tunnel0: `2001:db8:14::1/64`
- R4 Tunnel0: `2001:db8:14::2/64`

No additional routing is needed — the /64 subnet creates a connected link between R1 and R4 over the GRE tunnel.

**Verification:** `show ipv6 interface Tunnel0` on R1 must show the IPv6 address as UP. `ping 2001:db8:14::2` from R1 must succeed, proving that IPv6 traffic is being carried inside the IPv4 GRE tunnel.

---

### Task 4: Analyze Overlay vs Underlay Separation

Perform the following verification steps to confirm the overlay and underlay are separate:

- From R1, run traceroute to R4's **underlay** loopback (`4.4.4.4`) with source `1.1.1.1`. Confirm R3 (`10.0.13.2`) appears as the first hop.
- From R1, run traceroute to R4's **overlay** loopback (`10.4.4.4`) with source `1.1.1.1`. Confirm only R4's tunnel IP (`172.16.14.2`) appears — one hop.
- On R3, check the routing table for `10.4.4.4` and `172.16.14.0`. Confirm R3 has no knowledge of these overlay prefixes.
- On R1, check which routing process installed the route to `10.4.4.4`. It must be OSPF process 2 (not process 1).

**Verification:** `show ip route 10.4.4.4` on R1 must show `O` (OSPF) learned via process 2 through Tunnel0. `show ip route 10.4.4.4` on R3 must return no match. Traceroute to 4.4.4.4 shows 2 hops; traceroute to 10.4.4.4 shows 1 hop.

---

## 6. Verification & Analysis

### Task 1 — GRE Tunnel Infrastructure

```bash
R1# show interface Tunnel0
Tunnel0 is up, line protocol is up          ! ← both status bits must be UP
  Hardware is Tunnel
  Description: R1-R4 GRE Tunnel (overlay)
  Internet address is 172.16.14.1/30        ! ← correct tunnel IP
  MTU 1400 bytes, BW 100 Kbit/sec          ! ← MTU reduced to 1400
  ...
  Tunnel source 1.1.1.1 (Loopback0), destination 4.4.4.4   ! ← loopback source
  Tunnel protocol/transport GRE/IP
  ...

R4# show interface Tunnel0
Tunnel0 is up, line protocol is up          ! ← R4 side must also be up
  Internet address is 172.16.14.2/30        ! ← symmetric far-end address
  Tunnel source 4.4.4.4 (Loopback0), destination 1.1.1.1   ! ← correct

R1# ping 172.16.14.2
!!!!!                                       ! ← tunnel is forwarding IPv4
```

### Task 2 — OSPF Process 2 Overlay Routing

```bash
R1# show ip ospf 2 neighbor
Neighbor ID   Pri  State     Dead Time  Address        Interface
4.4.4.4         0  FULL/  -  00:00:37   172.16.14.2    Tunnel0   ! ← FULL, "-" = p2p (no DR)

R1# show ip route ospf 2
O        172.16.14.0/30 [110/1000] via 172.16.14.2, 00:02:11, Tunnel0
O        10.4.4.4/32 [110/1001] via 172.16.14.2, 00:02:11, Tunnel0    ! ← overlay loopback learned

R1# show ip route 10.4.4.4
Routing entry for 10.4.4.4/32
  Known via "ospf 2", distance 110                    ! ← process 2, not process 1
  ...
  via 172.16.14.2, Tunnel0                            ! ← exit via tunnel

R1# ping 10.4.4.4 source 1.1.1.1
!!!!!                                                 ! ← overlay reachability confirmed
```

### Task 3 — IPv6 over GRE

```bash
R1# show ipv6 interface Tunnel0
Tunnel0 is up, line protocol is up
  VRF is default (if not configured otherwise)
  IPv6 is enabled, link-local address is FE80::...
  Global unicast address(es):
    2001:db8:14::1, subnet is 2001:db8:14::/64    ! ← IPv6 address on tunnel

R1# ping 2001:db8:14::2
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 2001:db8:14::2, timeout is 2 seconds:
!!!!!                                              ! ← IPv6 carried inside IPv4 GRE
```

### Task 4 — Overlay vs Underlay Separation

```bash
! Underlay traceroute: R1 → R3 → R4 (2 physical hops)
R1# traceroute 4.4.4.4 source 1.1.1.1
Tracing the route to 4.4.4.4
1  10.0.13.2  8 msec  8 msec  8 msec      ! ← R3 is hop 1 (underlay visible)
2  10.0.34.2  16 msec 16 msec 16 msec     ! ← R4 WAN interface (underlay hop 2)

! Overlay traceroute: R1 → R4 via GRE (1 hop — overlay hides transport)
R1# traceroute 10.4.4.4 source 1.1.1.1
Tracing the route to 10.4.4.4
1  172.16.14.2  20 msec 20 msec 20 msec   ! ← R4 tunnel IP appears as only hop

! R3 has no overlay routes — it only sees underlay prefixes
R3# show ip route 10.4.4.4
% Network not in table                     ! ← R3 unaware of overlay
R3# show ip route 172.16.14.0
% Network not in table                     ! ← tunnel subnet hidden from R3

! Confirm overlay route installed by OSPF process 2 on R1
R1# show ip route 10.4.4.4
  Known via "ospf 2", distance 110         ! ← process 2 (not process 1)
  via 172.16.14.2, Tunnel0                 ! ← overlay exit interface
```

---

## 7. Verification Cheatsheet

### GRE Tunnel Interface Configuration

```
interface Tunnel0
 ip address <tunnel-ip> <mask>
 ipv6 address <ipv6>/<prefix>
 ip mtu 1400
 ip tcp adjust-mss 1360
 tunnel source Loopback0
 tunnel destination <far-end-loopback-ip>
 ip ospf network point-to-point
```

| Command | Purpose |
|---------|---------|
| `tunnel source Loopback0` | Use loopback for stability (never flaps) |
| `tunnel destination <ip>` | Far-end tunnel endpoint IP |
| `tunnel mode gre ip` | Default — explicit for clarity |
| `ip mtu 1400` | Reduce MTU to accommodate GRE overhead |
| `ip tcp adjust-mss 1360` | Clamp TCP MSS to prevent oversized segments |
| `ip ospf network point-to-point` | Avoid DR/BDR election on p2p tunnel link |

> **Exam tip:** The default GRE tunnel mode is `gre ip` (IPv4 outer, IPv4 inner). You do not need to configure it explicitly unless you want a different mode (e.g., `gre ipv6` for IPv6 outer transport).

### OSPF over GRE

```
router ospf 2
 router-id <same as process 1>
 network <tunnel-subnet> 0.0.0.3 area 0
 network <overlay-loopback> 0.0.0.0 area 0
```

| Command | Purpose |
|---------|---------|
| `router ospf 2` | Separate process for overlay — avoids loop with process 1 |
| `show ip ospf 2 neighbor` | Confirm FULL adjacency via tunnel |
| `show ip route ospf 2` | See only overlay routes learned via GRE |

> **Exam tip:** Use `show ip route ospf` (without process number) to see all OSPF routes. Use `show ip route ospf 2` to see only routes from process 2. The two are easily confused on exam questions.

### IPv6 over GRE

```
interface Tunnel0
 ipv6 address 2001:db8:14::1/64
```

| Command | Purpose |
|---------|---------|
| `show ipv6 interface Tunnel0` | Confirm IPv6 enabled and address assigned |
| `ping <ipv6-addr>` | Test IPv6 reachability across tunnel |

> **Exam tip:** GRE with `tunnel mode gre ip` (default) supports both IPv4 and IPv6 inner payload. You do not need a separate tunnel interface for IPv6 — just add an IPv6 address to the existing Tunnel0.

### Verification Commands

| Command | What to Look For |
|---------|-----------------|
| `show interface Tunnel0` | Both status bits UP; tunnel source/dest correct |
| `show ip ospf 2 neighbor` | Neighbor in FULL state, interface = Tunnel0 |
| `show ip route ospf 2` | Overlay prefixes (tunnel subnet + remote loopbacks) |
| `show ip route 10.4.4.4` | Route learned via "ospf 2" through Tunnel0 |
| `show ip route 4.4.4.4` | Underlay loopback via physical path (OSPF 1) |
| `traceroute 4.4.4.4 source 1.1.1.1` | 2 hops (underlay) — R3 visible |
| `traceroute 10.4.4.4 source 1.1.1.1` | 1 hop (overlay) — only R4 tunnel IP |
| `show ip route <overlay> on R3` | Must return "% Network not in table" |

### GRE Overhead Quick Reference

| Protocol | Overhead | Result (1500-byte frame) |
|----------|----------|--------------------------|
| Outer IPv4 header | 20 bytes | 1480 available for GRE + inner |
| GRE header | 4 bytes | 1476 available for inner payload |
| Effective inner MTU | 1476 bytes | Set `ip mtu 1400` for headroom |
| TCP MSS (safe value) | 1360 bytes | Set `ip tcp adjust-mss 1360` |

### Common GRE Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| Tunnel0 line protocol DOWN | `tunnel destination` unreachable — check routing table |
| Tunnel0 UP but no OSPF neighbor | OSPF network type mismatch; area mismatch; process not enabled on tunnel subnet |
| Tunnel UP, OSPF FULL, but route missing | Remote loopback not in `network` statement of OSPF process 2 |
| IPv6 ping over tunnel fails | IPv6 address not assigned to Tunnel0 |
| Tunnel flapping | Physical interface used as tunnel source — switch to loopback |
| R3 routing table shows overlay prefixes | OSPF process 2 accidentally applied to non-tunnel interfaces |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Task 1: GRE Tunnel Infrastructure

<details>
<summary>Click to view R1 Configuration</summary>

```bash
interface Tunnel0
 description R1-R4 GRE Tunnel (overlay)
 ip address 172.16.14.1 255.255.255.252
 ip mtu 1400
 ip tcp adjust-mss 1360
 tunnel source Loopback0
 tunnel destination 4.4.4.4
 ip ospf network point-to-point
 no shutdown
```
</details>

<details>
<summary>Click to view R4 Configuration</summary>

```bash
interface Tunnel0
 description R4-R1 GRE Tunnel (overlay)
 ip address 172.16.14.2 255.255.255.252
 ip mtu 1400
 ip tcp adjust-mss 1360
 tunnel source Loopback0
 tunnel destination 1.1.1.1
 ip ospf network point-to-point
 no shutdown
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show interface Tunnel0
ping 172.16.14.2
show interface Tunnel0   ! on R4
```
</details>

---

### Task 2: OSPF Process 2 Overlay Routing

<details>
<summary>Click to view R1 Configuration</summary>

```bash
router ospf 2
 router-id 1.1.1.1
 network 172.16.14.0 0.0.0.3 area 0
```
</details>

<details>
<summary>Click to view R4 Configuration</summary>

```bash
router ospf 2
 router-id 4.4.4.4
 network 172.16.14.0 0.0.0.3 area 0
 network 10.4.4.4 0.0.0.0 area 0
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ip ospf 2 neighbor
show ip route ospf 2
ping 10.4.4.4 source 1.1.1.1
```
</details>

---

### Task 3: IPv6 over GRE

<details>
<summary>Click to view R1 Configuration</summary>

```bash
interface Tunnel0
 ipv6 address 2001:db8:14::1/64
```
</details>

<details>
<summary>Click to view R4 Configuration</summary>

```bash
interface Tunnel0
 ipv6 address 2001:db8:14::2/64
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ipv6 interface Tunnel0
ping 2001:db8:14::2
```
</details>

---

### Task 4: Overlay vs Underlay Analysis

<details>
<summary>Click to view Verification Commands</summary>

```bash
! On R1:
traceroute 4.4.4.4 source 1.1.1.1        ! underlay — 2 hops (R3 visible)
traceroute 10.4.4.4 source 1.1.1.1       ! overlay — 1 hop (Tunnel0 direct)
show ip route 10.4.4.4                    ! must show "ospf 2" via Tunnel0

! On R3:
show ip route 10.4.4.4                    ! must return "% Network not in table"
show ip route 172.16.14.0                 ! must return "% Network not in table"
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

### Ticket 1 — Tunnel Shows Up but R1 Cannot Reach R4's Overlay Network

Operations confirms the GRE tunnel interface is up on both R1 and R4. However, `ping 10.4.4.4` from R1 fails and the overlay network is unreachable. All physical connectivity is intact.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py`

**Success criteria:** `show ip ospf 2 neighbor` on R1 shows R4 in FULL state. `show ip route 10.4.4.4` on R1 returns an OSPF process 2 route via Tunnel0. `ping 10.4.4.4 source 1.1.1.1` succeeds.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! 1. Confirm tunnel is up but overlay is unreachable
R1# show interface Tunnel0
! Tunnel0 is up, line protocol is up  ← tunnel itself is fine

R1# ping 10.4.4.4 source 1.1.1.1
.....   ! overlay unreachable

! 2. Check OSPF process 2 neighbor state
R1# show ip ospf 2 neighbor
! No neighbors shown — or neighbor stuck in EXSTART/INIT

! 3. Check OSPF process 2 detail on both routers
R1# show ip ospf 2
! Confirms process 2 is running on R1

R4# show ip ospf 2
! Look at routing process 2 — check the Tunnel0 area assignment

! 4. Check Tunnel0 OSPF configuration on R4
R4# show running-config | section router ospf 2
! One of the network statements has area 1 instead of area 0 — that is the fault
! R1 is in area 0, R4 is in area 1 → area mismatch → adjacency blocked
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
R4# configure terminal
R4(config)# router ospf 2
R4(config-router)# no network 172.16.14.0 0.0.0.3 area 1
R4(config-router)# no network 10.4.4.4 0.0.0.0 area 1
R4(config-router)# network 172.16.14.0 0.0.0.3 area 0
R4(config-router)# network 10.4.4.4 0.0.0.0 area 0
R4(config-router)# end
R4# write memory

! Verify (allow ~40 seconds for adjacency):
R1# show ip ospf 2 neighbor
4.4.4.4    0  FULL/  -   00:00:38   172.16.14.2    Tunnel0  ! ← FULL, area mismatch resolved
R1# ping 10.4.4.4 source 1.1.1.1
!!!!!                                                        ! ← overlay restored
```
</details>

---

### Ticket 2 — Tunnel0 Line Protocol Down on R1 After Config Change

A change window was applied to R1 last night. This morning, NOC monitoring shows Tunnel0 is DOWN on R1 and the overlay network is completely unreachable. All physical interfaces are UP.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py`

**Success criteria:** `show interface Tunnel0` on R1 shows `line protocol is up`. `ping 10.4.4.4 source 1.1.1.1` succeeds.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! 1. Confirm tunnel is down
R1# show interface Tunnel0
! Tunnel0 is up, line protocol is down   ! ← destination unreachable

! 2. Check the tunnel destination
R1# show running-config interface Tunnel0
! tunnel destination 4.4.4.5             ! ← wrong IP — 4.4.4.5 instead of 4.4.4.4

! 3. Verify that the configured destination is not reachable
R1# ping 4.4.4.5
.....   ! 4.4.4.5 doesn't exist — no route in table

! 4. Verify the correct destination is reachable
R1# ping 4.4.4.4
!!!!!   ! 4.4.4.4 is reachable via underlay — typo in destination
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
R1# configure terminal
R1(config)# interface Tunnel0
R1(config-if)# tunnel destination 4.4.4.4
R1(config-if)# end
R1# write memory

! Verify:
R1# show interface Tunnel0
! Tunnel0 is up, line protocol is up     ! ← destination now reachable
R1# ping 10.4.4.4 source 1.1.1.1
!!!!!
```
</details>

---

### Ticket 3 — GRE Tunnel Down Despite All Physical Links Active

An engineer has shut R1's Loopback0 for "maintenance" but forgot to restore it. The GRE tunnel is down and all overlay traffic is offline. Physical WAN interfaces (Gi0/0, Gi0/1) are all UP.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py`

**Success criteria:** `show interface Tunnel0` on R1 shows `line protocol is up`. `show interface Loopback0` shows the interface is UP. `ping 10.4.4.4 source 1.1.1.1` succeeds.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! 1. Confirm tunnel is down
R1# show interface Tunnel0
! Tunnel0 is up, line protocol is down

! 2. Physical interfaces look fine
R1# show ip interface brief
! GigabitEthernet0/0    up    up
! GigabitEthernet0/1    up    up
! GigabitEthernet0/2    up    up
! Loopback0          administratively down   ! ← source interface is shut

! 3. Understand why Loopback0 being down kills the tunnel
R1# show running-config interface Tunnel0
! tunnel source Loopback0   ← the tunnel source is Loopback0

! When Loopback0 is shut, IOS cannot source GRE packets from 1.1.1.1
! → tunnel line protocol goes DOWN regardless of physical connectivity

! 4. Also: R1's OSPF process 1 loses the 1.1.1.1 advertisement
R1# show ip ospf 1 neighbor
! R3 adjacency may be lost or routes may have changed — Lo0 no longer advertised
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
R1# configure terminal
R1(config)# interface Loopback0
R1(config-if)# no shutdown
R1(config-if)# end
R1# write memory

! Verify (allow ~10 seconds for tunnel to come up):
R1# show interface Loopback0
! Loopback0 is up, line protocol is up   ! ← restored

R1# show interface Tunnel0
! Tunnel0 is up, line protocol is up     ! ← source interface up → tunnel recovers

R1# ping 10.4.4.4 source 1.1.1.1
!!!!!

! Key lesson: loopbacks should NEVER be shut on production routers used as tunnel anchors.
! This is why loopbacks are preferred over physical interfaces as tunnel source.
```
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] Tunnel0 configured on R1 with source Loopback0, destination 4.4.4.4
- [ ] Tunnel0 configured on R4 with source Loopback0, destination 1.1.1.1
- [ ] R1 Tunnel0 IP: `172.16.14.1/30`; R4 Tunnel0 IP: `172.16.14.2/30`
- [ ] `ip mtu 1400` and `ip tcp adjust-mss 1360` on both tunnel interfaces
- [ ] `ip ospf network point-to-point` on both tunnel interfaces
- [ ] `show interface Tunnel0` on R1 shows up/up
- [ ] `show interface Tunnel0` on R4 shows up/up
- [ ] OSPF process 2 running on R1 (network 172.16.14.0/30 in area 0)
- [ ] OSPF process 2 running on R4 (network 172.16.14.0/30 and 10.4.4.4/32 in area 0)
- [ ] `show ip ospf 2 neighbor` on R1 shows R4 in FULL state
- [ ] `show ip route ospf 2` on R1 shows 10.4.4.4/32 via Tunnel0
- [ ] `ping 10.4.4.4 source 1.1.1.1` succeeds
- [ ] R1 Tunnel0 IPv6: `2001:db8:14::1/64`; R4 Tunnel0 IPv6: `2001:db8:14::2/64`
- [ ] `ping 2001:db8:14::2` from R1 succeeds (IPv6 over GRE)
- [ ] `traceroute 4.4.4.4 source 1.1.1.1` shows R3 (10.0.13.2) as hop 1 (underlay)
- [ ] `traceroute 10.4.4.4 source 1.1.1.1` shows only 1 hop at 172.16.14.2 (overlay)
- [ ] `show ip route 10.4.4.4` on R3 returns "% Network not in table"
- [ ] `show ip route 172.16.14.0` on R3 returns "% Network not in table"

### Troubleshooting

- [ ] Ticket 1: Identified OSPF process 2 area mismatch on R4; corrected area to 0; overlay routing restored
- [ ] Ticket 2: Identified wrong tunnel destination on R1 (4.4.4.5); corrected to 4.4.4.4; Tunnel0 came back up
- [ ] Ticket 3: Identified Loopback0 shutdown on R1; restored with `no shutdown`; tunnel recovered; understood loopback-as-source stability principle
