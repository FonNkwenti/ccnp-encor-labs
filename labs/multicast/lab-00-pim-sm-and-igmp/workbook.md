# Multicast Lab 00: PIM Sparse Mode, IGMP, and RPF Fundamentals

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

**Exam Objective:** 3.3.d — Describe multicast protocols, such as RPF check, PIM SM, IGMP v2/v3, SSM, bidir, and MSDP (Multicast topic)

IP multicast is the network-layer mechanism that delivers a single packet stream to multiple interested receivers simultaneously — without the sender needing to know who or how many they are. This lab introduces the foundational concepts: how routers use PIM Sparse Mode to build distribution trees, how IGMP allows hosts to join groups, and how the RPF check ensures loop-free multicast forwarding.

### Multicast Addressing and the Group Model

Multicast uses the Class D address space — 224.0.0.0/4 (224.0.0.0 through 239.255.255.255). A multicast group address identifies a logical "channel"; any host can send to it, and any host can join it. Routers do not need per-host state — they track group membership per interface.

Key address ranges:
| Range | Use |
|-------|-----|
| 224.0.0.0/24 | Link-local (not forwarded by routers) — PIM hellos use 224.0.0.13 |
| 232.0.0.0/8 | SSM (Source-Specific Multicast) — lab-02 |
| 239.0.0.0/8 | Administratively scoped (private, equivalent to RFC 1918) |

This lab uses **239.1.1.1** as the group address — administratively scoped, suitable for internal exercises.

### PIM Sparse Mode (PIM-SM) Operation

PIM (Protocol Independent Multicast) builds the distribution tree routers use to forward multicast traffic. "Protocol Independent" means PIM uses the existing unicast routing table (OSPF in this lab) for its RPF check — it does not run its own routing protocol.

**Sparse Mode** assumes most routers do *not* have interested receivers. Traffic only flows where explicitly requested via explicit Joins — the opposite of Dense Mode, which floods everywhere and prunes back.

PIM-SM uses two types of trees:

**Shared Tree (RPT — RP Tree):** All traffic for group G flows via the Rendezvous Point (RP). The first-hop receiver router sends a `(*,G) Join` toward the RP. The RP is a common meeting point for sources and receivers. Entry format: `(*,G)` — "any source, group G."

**Shortest-Path Tree (SPT):** After traffic arrives via the RP, the last-hop router (closest to receivers) can trigger an SPT switchover by sending an `(S,G) Join` directly toward the source. This cuts out the RP for that source-group pair and produces a more efficient path. Entry format: `(S,G)` — "source S, group G."

The PIM-SM join/register process:
```
Source → R1 (first-hop)
  └── R1 sends PIM Register (unicast) to RP (R2)
  └── RP builds (S,G) state, starts forwarding to receivers via shared tree
  └── Last-hop router (R3) joins (*,G) shared tree toward RP
  └── When traffic rate exceeds SPT threshold (default 0 kbps), R3 sends (S,G) Join directly toward R1
  └── (S,G) SPT is active; RP sends PIM Prune to R1 to stop duplicate traffic
```

On IOS, PIM-SM requires:
- `ip multicast-routing` globally — activates the multicast forwarding engine
- `ip pim sparse-mode` per interface — enables PIM on that interface
- `ip pim rp-address <ip>` globally — configures a static RP address (this lab)

### IGMP v2 and Group Membership

IGMP (Internet Group Management Protocol) is the protocol between a router and directly connected hosts. It is how hosts tell routers "I want to receive traffic for group G."

**IGMPv2** (default on IOS) uses three message types:
| Message | Sender | Purpose |
|---------|--------|---------|
| Membership Query | Router | Asks "who is still interested in any group?" (224.0.0.1) |
| Membership Report | Host | "I want to join group G" (sent to the group address) |
| Leave Group | Host | "I'm leaving group G" (sent to 224.0.0.2) |

The router on the LAN segment with receivers is the **IGMP Querier** — it sends periodic General Queries (every 125 seconds by default). Hosts respond with Membership Reports. If no host responds for a group, the router removes the (*, G) entry and stops forwarding traffic toward that segment.

On IOS, IGMPv2 is the default — no explicit configuration is needed. The command `ip igmp join-group <group>` causes the router interface itself to act as a host and join the group, which is useful in labs when there are no real hosts.

### RPF Check and Multicast Forwarding

The RPF (Reverse Path Forwarding) check is how routers prevent multicast forwarding loops. Before forwarding a multicast packet, the router verifies that the packet arrived on the interface it would use to reach the *source* via unicast routing. If not, the packet is dropped silently.

```
                   10.1.1.10 (source)
                        │
              ┌─────────┘
              │
         [R2 receives multicast from R1 on Gi0/0]
              │
         R2 checks: "What is my unicast path to 10.1.1.10?"
              │
         show ip route 10.1.1.10 → via R1, next-hop 10.1.12.1, interface Gi0/0
              │
         Packet arrived on Gi0/0 ← matches RPF interface → FORWARD
         Packet arrived on Gi0/1 ← does NOT match → DROP (loop guard)
```

`show ip rpf <source-address>` shows what the router considers the RPF interface and RPF neighbor for a given source. If the RPF check fails (e.g., due to a routing change), multicast traffic stops — even if OSPF is fully converged. This is a common source of multicast failures.

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| PIM-SM global/interface configuration | Enable multicast routing and PIM on all router interfaces |
| Static RP configuration | Point all routers at a common Rendezvous Point |
| IGMP join simulation | Use `ip igmp join-group` to simulate a host receiver |
| RPF verification | Interpret `show ip rpf` to confirm the forwarding path |
| Mroute table reading | Distinguish (*,G) shared-tree and (S,G) shortest-path entries |
| SPT switchover observation | Understand when and why routers switch to the source tree |

---

## 2. Topology & Scenario

**Scenario:** You are a network engineer at a media company deploying IP multicast for internal video distribution. The company backbone consists of three routers (R1, R2, R3) in a triangle to provide redundant paths. R2 is the designated Rendezvous Point. PC1 is the video source; PC2 is a receiver in a remote segment. OSPF is already running as the unicast IGP. Your task is to bring up PIM-SM from scratch.

```
┌───────────┐              ┌──────────────────────┐
│   PC1     │──Gi0/2───────│         R1           │
│ (Source)  │  10.1.1.0/24 │    (Source Router)   │
│10.1.1.10  │              │    Lo0: 1.1.1.1/32   │
└───────────┘              └────┬──────────────┬───┘
                         Gi0/0 │              │ Gi0/1
                   10.1.12.1/30 │              │ 10.1.13.1/30
                                │              │
                   10.1.12.2/30 │              │ 10.1.13.2/30
                         Gi0/0 │              │ Gi0/1
              ┌─────────────────┘              └──────────────┐
              │                                               │
┌─────────────┴──────────┐               ┌────────────────────┴────┐
│          R2             │               │           R3            │
│      (Primary RP)       │               │    (Receiver Router)    │
│    Lo0: 2.2.2.2/32     │               │    Lo0: 3.3.3.3/32     │
└──────────┬──────────────┘               └──────────────┬──────────┘
       Gi0/1│                                         Gi0/0│
  10.1.23.1/30│                               10.1.23.2/30│
              │                                            │
              └────────────────────────────────────────────┘
                                 10.1.23.0/30
                                                       Gi0/2│
                                                  10.1.3.0/24│
                                                       ┌─────┴──────┐
                                                       │    PC2     │
                                                       │ (Receiver) │
                                                       │ 10.1.3.10  │
                                                       └────────────┘
```

**Multicast group:** 239.1.1.1
**RP address:** 2.2.2.2 (R2 Loopback0)

---

## 3. Hardware & Environment Specifications

| Device | Platform | Role | Management |
|--------|----------|------|------------|
| R1 | IOSv | Source-side router | EVE-NG console |
| R2 | IOSv | Primary RP | EVE-NG console |
| R3 | IOSv | Receiver-side router | EVE-NG console |
| PC1 | VPCS | Multicast source (simulated) | EVE-NG console |
| PC2 | VPCS | Multicast receiver | EVE-NG console |

**Cabling:**

| Link | Source | Destination | Subnet |
|------|--------|-------------|--------|
| L1 | R1 Gi0/0 | R2 Gi0/0 | 10.1.12.0/30 |
| L2 | R2 Gi0/1 | R3 Gi0/0 | 10.1.23.0/30 |
| L3 | R1 Gi0/1 | R3 Gi0/1 | 10.1.13.0/30 |
| L4 | R1 Gi0/2 | PC1 | 10.1.1.0/24 |
| L5 | R3 Gi0/2 | PC2 | 10.1.3.0/24 |

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

The following is pre-loaded via `setup_lab.py`:

**Pre-configured on all routers:**
- Hostname and `no ip domain lookup`
- Interface IP addressing (all links from baseline.yaml)
- OSPFv2 process 1 — all interfaces in area 0; passive on source/receiver LANs

**NOT pre-configured (student configures):**
- IP multicast routing process
- PIM Sparse Mode on any interface
- Rendezvous Point address
- IGMP group membership

**PC1 and PC2** have static IPs pre-loaded via `.vpc` files. No additional configuration is required.

---

## 5. Lab Challenge: Core Implementation

### Task 1: Enable IP Multicast Routing

- Enable the global multicast routing process on R1, R2, and R3.
- This is required before any PIM or IGMP commands will take effect on interfaces.

**Verification:** `show ip mroute` must return output (even if empty initially) rather than an error message indicating multicast routing is not enabled.

---

### Task 2: Enable PIM Sparse Mode on All Interfaces

- Enable PIM Sparse Mode on every active interface of each router, including Loopback0 interfaces.
- All five interfaces on R1 (Lo0, Gi0/0, Gi0/1, Gi0/2) and R3 (Lo0, Gi0/0, Gi0/1, Gi0/2), and all three on R2 (Lo0, Gi0/0, Gi0/1) must participate.

**Verification:** `show ip pim interface` on each router must show all interfaces listed with mode `Sparse`.

---

### Task 3: Configure a Static Rendezvous Point

- Configure R2's Loopback0 address (2.2.2.2) as the static RP for all multicast groups on all three routers.

**Verification:** `show ip pim rp mapping` on each router must show 2.2.2.2 as the RP for group range 224.0.0.0/4.

---

### Task 4: Verify PIM Neighbor Adjacencies

- Confirm that PIM neighborships have formed between R1–R2 (on the 10.1.12.0/30 link), R2–R3 (on the 10.1.23.0/30 link), and R1–R3 (on the 10.1.13.0/30 link).

**Verification:** `show ip pim neighbor` on each router must show the correct neighbors and uptime values.

---

### Task 5: Simulate a Receiver with IGMP

- On R3's receiver LAN interface (Gi0/2), configure R3 itself to join multicast group 239.1.1.1 using the IGMP join-group mechanism. This simulates PC2 sending an IGMP Membership Report.

**Verification:** `show ip igmp groups` on R3 must show group 239.1.1.1 on GigabitEthernet0/2 with version IGMPv2.

---

### Task 6: Examine the RPF Check

- Without generating traffic yet, examine the RPF path that R2 and R3 would use for source address 10.1.1.10 (PC1).
- Identify the RPF interface and RPF neighbor on each router.

**Verification:** `show ip rpf 10.1.1.10` on R2 must show RPF neighbor 10.1.12.1 (R1) via GigabitEthernet0/0. On R3, the result will reflect the triangle topology — note which path OSPF prefers.

---

### Task 7: Generate Traffic and Observe the Multicast Routing Table

- From R1 (acting as a multicast source for this task), send a ping to group 239.1.1.1 with a repeat count of at least 10.
- Observe how the multicast routing table evolves: first a shared-tree (*,G) entry appears, then a source-tree (S,G) entry after SPT switchover.
- Note the incoming interface (RPF interface) and outgoing interface list (OIL) for each entry.

**Verification:** `show ip mroute 239.1.1.1` on R2 must show both `(*,239.1.1.1)` and `(10.1.1.1,239.1.1.1)` entries. R3 must show an OIL entry for GigabitEthernet0/2 (receiver LAN).

---

## 6. Verification & Analysis

### Task 1 — Multicast Routing Enabled

```
R1# show ip mroute
IP Multicast Routing Table
Flags: D - Dense, S - Sparse, B - Bidir Group, s - SSM Group ...
Outgoing interface flags: H - Hardware switched, A - Assert winner, p - PIM Join
...
                                                   ! ← table header confirms multicast routing is active
```

### Task 2 — PIM Interface Mode

```
R1# show ip pim interface
Address          Interface                Ver/   Nbr    Query  DR         DR
                                         Mode   Count  Intvl  Prior
1.1.1.1          Loopback0               v2/S   0      30     1          1.1.1.1  ! ← Lo0 in Sparse mode
10.1.12.1        GigabitEthernet0/0      v2/S   1      30     1          10.1.12.1 ! ← Gi0/0 in Sparse, 1 neighbor
10.1.13.1        GigabitEthernet0/1      v2/S   1      30     1          10.1.13.1 ! ← Gi0/1 in Sparse, 1 neighbor
10.1.1.1         GigabitEthernet0/2      v2/S   0      30     1          10.1.1.1  ! ← Gi0/2 in Sparse, source LAN

R2# show ip pim interface
Address          Interface                Ver/   Nbr    Query  DR         DR
                                         Mode   Count  Intvl  Prior
2.2.2.2          Loopback0               v2/S   0      30     1          2.2.2.2  ! ← RP's loopback must be in Sparse
10.1.12.2        GigabitEthernet0/0      v2/S   1      30     1          10.1.12.2
10.1.23.1        GigabitEthernet0/1      v2/S   1      30     1          10.1.23.1
```

### Task 3 — Static RP Mapping

```
R1# show ip pim rp mapping
PIM Group-to-RP Mappings
Group(s) 224.0.0.0/4
  RP 2.2.2.2 (?), v2v1
    Info source: Static   ! ← confirms static RP (not Auto-RP or BSR)
    Uptime: 00:05:12, expires: never

R3# show ip pim rp mapping
PIM Group-to-RP Mappings
Group(s) 224.0.0.0/4
  RP 2.2.2.2 (?), v2v1
    Info source: Static   ! ← all routers must show the same RP
    Uptime: 00:05:08, expires: never
```

### Task 4 — PIM Neighbors

```
R2# show ip pim neighbor
PIM Neighbor Table
Mode: B - Bidir Capable, DR - Designated Router, N - Default DR Priority,
      P - Proxy Capable, S - State Refresh Capable, G - GenID Capable, L - DR Load-balancing Capable
Neighbor          Interface                Uptime/Expires    Ver   DR
Address                                                            Prio/Mode
10.1.12.1         GigabitEthernet0/0       00:08:32/00:01:27 v2    1 / DR S P G   ! ← R1 neighbor via Gi0/0
10.1.23.2         GigabitEthernet0/1       00:08:30/00:01:25 v2    1 / S P G      ! ← R3 neighbor via Gi0/1
```

### Task 5 — IGMP Group Membership

```
R3# show ip igmp groups
IGMP Connected Group Membership
Group Address    Interface                Uptime    Expires   Last Reporter   Group Accounted
239.1.1.1        GigabitEthernet0/2       00:01:14  00:02:46  3.3.3.3         ! ← group joined on receiver LAN
                                                                               ! ← Last Reporter = 3.3.3.3 (R3 itself)
```

### Task 6 — RPF Check

```
R2# show ip rpf 10.1.1.10
RPF information for ? (10.1.1.10)
  RPF interface: GigabitEthernet0/0          ! ← packet must arrive on Gi0/0 (toward R1)
  RPF neighbor: 10.1.12.1 (R1)              ! ← R1 is the RPF neighbor
  RPF route/mask: 10.1.1.0/24
  RPF type: unicast (ospf 1)                ! ← OSPF is the source of RPF info
  RPF recursion count: 0
  Doing distance-preferred lookups across tables

R3# show ip rpf 10.1.1.10
RPF information for ? (10.1.1.10)
  RPF interface: GigabitEthernet0/1          ! ← R3 reaches 10.1.1.0 via R1 directly (L3 link)
  RPF neighbor: 10.1.13.1 (R1)              ! ← direct R1-R3 link wins in OSPF (equal cost)
  RPF route/mask: 10.1.1.0/24
  RPF type: unicast (ospf 1)
```

> **Note:** R3 reaches PC1's subnet via R1 directly (L3 link 10.1.13.0/30) rather than via R2. This means when the SPT switchover happens, R3 will send an (S,G) Join toward R1 — not via R2. This is the RPF check in action: traffic must arrive on the interface that leads back to the source.

### Task 7 — Multicast Routing Table (after traffic)

> **Source-address note:** The ping below sources from R1's Gi0/2 IP
> (10.1.1.1), so the (S,G) entry is keyed on `10.1.1.1` — not PC1's
> 10.1.1.10 used in the Task 6 RPF example. Both addresses live in
> 10.1.1.0/24, so the RPF interface result is identical. R1 is standing
> in as the multicast source here because VPCS cannot generate real
> multicast streams.

```
R1# ping 239.1.1.1 repeat 20 source GigabitEthernet0/2

R2# show ip mroute 239.1.1.1
IP Multicast Routing Table
...
(*,239.1.1.1), 00:00:45/00:02:59, RP 2.2.2.2, flags: S
  Incoming interface: Loopback0, RPF nbr 0.0.0.0   ! ← RP itself; shared tree entry
  Outgoing interface list:
    GigabitEthernet0/1, Forward/Sparse, 00:00:45/00:02:14  ! ← toward R3 (receiver)

(10.1.1.1,239.1.1.1), 00:00:12/00:02:47, flags: T
  Incoming interface: GigabitEthernet0/0, RPF nbr 10.1.12.1 ! ← source traffic arrives from R1
  Outgoing interface list:
    GigabitEthernet0/1, Forward/Sparse, 00:00:12/00:02:47  ! ← forwarded toward R3

R3# show ip mroute 239.1.1.1
(*,239.1.1.1), 00:00:45/00:02:59, RP 2.2.2.2, flags: S
  Incoming interface: GigabitEthernet0/0, RPF nbr 10.1.23.1 ! ← shared tree arrives from R2
  Outgoing interface list:
    GigabitEthernet0/2, Forward/Sparse, 00:00:45/00:02:14  ! ← forwarded to receiver LAN

(10.1.1.1,239.1.1.1), 00:00:12/00:02:47, flags: T        ! ← SPT entry after switchover
  Incoming interface: GigabitEthernet0/1, RPF nbr 10.1.13.1 ! ← direct path from R1 (SPT)
  Outgoing interface list:
    GigabitEthernet0/2, Forward/Sparse, 00:00:12/00:02:47
```

---

## 7. Verification Cheatsheet

### Global Multicast Configuration

```
ip multicast-routing
ip pim rp-address <rp-ip>
```

| Command | Purpose |
|---------|---------|
| `ip multicast-routing` | Enable multicast forwarding globally (required first) |
| `ip pim rp-address <ip>` | Configure a static RP for all groups (224.0.0.0/4) |
| `ip pim rp-address <ip> <acl>` | Restrict static RP to specific group range |

### Interface Configuration

```
interface <name>
 ip pim sparse-mode
 ip igmp join-group <group>
```

| Command | Purpose |
|---------|---------|
| `ip pim sparse-mode` | Enable PIM-SM on this interface (required on all interfaces) |
| `ip igmp join-group <group>` | Router interface joins as a simulated host receiver |
| `ip igmp version 3` | Upgrade interface to IGMPv3 (needed for SSM) |
| `ip pim dr-priority <0-4294967294>` | Influence Designated Router election on a LAN |

> **Exam tip:** `ip multicast-routing` is required before any PIM configuration takes effect. Forgetting this global command is the most common reason PIM appears configured but nothing works.

### Verification Commands

| Command | What to Look For |
|---------|-----------------|
| `show ip pim interface` | All interfaces listed in `Sparse` mode |
| `show ip pim neighbor` | PIM neighbors on each point-to-point link |
| `show ip pim rp mapping` | Correct RP address (2.2.2.2) for 224.0.0.0/4 |
| `show ip igmp groups` | Group 239.1.1.1 present on receiver-LAN interface |
| `show ip rpf <source-ip>` | RPF interface and neighbor for a given source address |
| `show ip mroute` | All (*,G) and (S,G) entries in the multicast routing table |
| `show ip mroute <group>` | Detailed entry for one group — incoming interface, OIL |
| `show ip mroute count` | Packet counters per (S,G) entry to confirm traffic is flowing |
| `debug ip pim` | PIM join/prune/register events (use sparingly in production) |

### Multicast Tree Types Quick Reference

| Entry | Tree Type | Description |
|-------|-----------|-------------|
| `(*,G)` | Shared tree (RPT) | Any source, group G — traffic via RP |
| `(S,G)` | Shortest-path tree (SPT) | Specific source S, group G — direct path |
| `(S,G,rpt)` | SPT prune on shared tree | Source pruned from shared tree after SPT switchover |

### Common PIM-SM Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| `show ip pim interface` shows no interfaces | `ip multicast-routing` not configured globally |
| No PIM neighbors | `ip pim sparse-mode` missing on one or both sides of a link |
| `show ip pim rp mapping` empty | `ip pim rp-address` not configured |
| `show ip mroute` empty after traffic | RPF check failing — unicast path to source changed |
| `(*,G)` present but no traffic | No IGMP join on receiver side — OIL is empty |
| `(S,G)` missing after traffic | SPT threshold set to `infinity` — only shared tree in use |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Task 1–3: Enable Multicast Routing, PIM-SM, and Static RP

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1
ip multicast-routing
!
interface Loopback0
 ip pim sparse-mode
!
interface GigabitEthernet0/0
 ip pim sparse-mode
!
interface GigabitEthernet0/1
 ip pim sparse-mode
!
interface GigabitEthernet0/2
 ip pim sparse-mode
!
ip pim rp-address 2.2.2.2
```
</details>

<details>
<summary>Click to view R2 Configuration</summary>

```bash
! R2
ip multicast-routing
!
interface Loopback0
 ip pim sparse-mode
!
interface GigabitEthernet0/0
 ip pim sparse-mode
!
interface GigabitEthernet0/1
 ip pim sparse-mode
!
ip pim rp-address 2.2.2.2
```
</details>

<details>
<summary>Click to view R3 Configuration</summary>

```bash
! R3
ip multicast-routing
!
interface Loopback0
 ip pim sparse-mode
!
interface GigabitEthernet0/0
 ip pim sparse-mode
!
interface GigabitEthernet0/1
 ip pim sparse-mode
!
interface GigabitEthernet0/2
 ip pim sparse-mode
!
ip pim rp-address 2.2.2.2
```
</details>

### Task 5: IGMP Join on R3

<details>
<summary>Click to view R3 Configuration</summary>

```bash
! R3
interface GigabitEthernet0/2
 ip igmp join-group 239.1.1.1
```
</details>

### Task 7: Generate Traffic from R1

<details>
<summary>Click to view Traffic Generation</summary>

```bash
! R1 — send multicast ping from source LAN interface
R1# ping 239.1.1.1 repeat 50 source GigabitEthernet0/2

! Then immediately check:
R2# show ip mroute 239.1.1.1
R3# show ip mroute 239.1.1.1
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ip pim interface
show ip pim neighbor
show ip pim rp mapping
show ip igmp groups
show ip rpf 10.1.1.10
show ip mroute
show ip mroute 239.1.1.1
show ip mroute count
```
</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. Inject the fault first, then
diagnose and fix using only show commands.

### Workflow

```bash
python3 setup_lab.py                                   # reset to known-good
python3 scripts/fault-injection/inject_scenario_01.py  # Ticket 1
python3 scripts/fault-injection/apply_solution.py      # restore after each ticket
```

---

### Ticket 1 — Multicast Traffic Does Not Reach the RP

You have verified that R3 has joined group 239.1.1.1. R1 sends pings to 239.1.1.1 sourced from Gi0/2, but `show ip mroute` on R2 shows no (S,G) entry for the source at 10.1.1.10. The (*,G) entry is also absent. OSPF is fully converged.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py`

**Success criteria:** After your fix, `show ip mroute 239.1.1.1` on R2 shows a (S,G) entry with incoming interface GigabitEthernet0/0 and traffic flowing.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `show ip mroute` on R1 — check if R1 even has a local (S,G) entry for the source
2. `show ip pim interface` on R1 — verify PIM mode on all interfaces, especially Gi0/2
3. `show ip pim neighbor` on R1 — confirm R2 and R3 are still PIM neighbors
4. `show ip rpf 10.1.1.10` on R2 — confirm RPF path is intact
5. Key clue: R1 Gi0/2 (source LAN) is missing from `show ip pim interface` output, or shows as non-Sparse
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! R1
interface GigabitEthernet0/2
 ip pim sparse-mode
```

Root cause: PIM Sparse Mode was removed from R1's source-facing interface. Without PIM on Gi0/2, R1 cannot detect the source joining the LAN and will not trigger a PIM Register toward the RP. The multicast packet from PC1 is received on a non-PIM interface and dropped.
</details>

---

### Ticket 2 — PC2 Receives No Multicast Traffic Despite R3 Joining the Group

The NOC reports that R3 has joined group 239.1.1.1 (confirmed via `show ip igmp groups`), and OSPF is fully converged. R2 shows a valid (*,G) entry with traffic, but R3's mroute table shows no (*,G) entry for 239.1.1.1. Traffic never reaches the receiver LAN.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py`

**Success criteria:** After your fix, `show ip mroute 239.1.1.1` on R3 shows a (*,G) entry with incoming interface GigabitEthernet0/0 and GigabitEthernet0/2 in the OIL.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `show ip pim rp mapping` on R3 — compare the RP address against R1 and R2
2. `show ip route 3.3.3.3` on R3 — verify the RP is reachable
3. Key clue: R3's RP mapping shows a different address than R1/R2. R3 is trying to join a shared tree at a non-existent RP.
4. `show ip pim neighbor` on R3 — PIM neighbors are present, so the issue is not PIM adjacency
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! R3
no ip pim rp-address 3.3.3.3
ip pim rp-address 2.2.2.2
```

Root cause: R3 had a wrong RP address configured (3.3.3.3 — R3's own loopback). When R3 tried to join the shared tree for 239.1.1.1, it sent a (*,G) Join toward 3.3.3.3, which has no PIM state. The correct RP is 2.2.2.2 (R2's Loopback0).
</details>

---

### Ticket 3 — R2 Cannot Forward Traffic from the R1-Side of the Network

R3 has joined group 239.1.1.1 and the RP address is consistent across all routers. However, after R1 sends multicast traffic, `show ip mroute 239.1.1.1` on R2 stays empty — no (*,G) traffic flowing, no (S,G) entry building — and R3's mroute shows no (S,G) entry either. OSPF is fully converged and all unicast reachability is intact. Something on R2's R1-facing side is no longer participating in PIM.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py`

**Success criteria:** After your fix, `show ip mroute 239.1.1.1` on R2 shows an (S,G) entry with incoming interface GigabitEthernet0/0 and traffic forwarding to R3.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `show ip rpf 10.1.1.10` on R2 — verify the RPF interface matches where traffic is arriving
2. `show ip pim interface` on R2 — check that the RPF interface (Gi0/0) has PIM enabled
3. `show ip pim neighbor` on R2 — check neighbors on Gi0/0
4. Key clue: Gi0/0 on R2 is in the PIM interface table but shows 0 neighbors, or Gi0/0 does not appear at all
5. The RPF check succeeds at the unicast level (OSPF still sees the route) but PIM cannot receive traffic on a non-PIM interface
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! R2
interface GigabitEthernet0/0
 ip pim sparse-mode
```

Root cause: PIM Sparse Mode was removed from R2's Gi0/0 interface (the link toward R1). Although OSPF still selects Gi0/0 as the path to reach R1/PC1's subnet, PIM will not accept multicast traffic on an interface that does not have `ip pim sparse-mode`. The RPF check fails because the ingress interface is not a PIM interface.
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] `ip multicast-routing` configured on R1, R2, and R3
- [ ] `ip pim sparse-mode` on all active interfaces (Lo0, Gi0/0, Gi0/1, Gi0/2 as applicable)
- [ ] `ip pim rp-address 2.2.2.2` configured on R1, R2, and R3
- [ ] `show ip pim interface` shows all interfaces in Sparse mode on all routers
- [ ] `show ip pim neighbor` shows R1-R2, R2-R3, and R1-R3 neighbors
- [ ] `show ip pim rp mapping` shows 2.2.2.2 for 224.0.0.0/4 on all routers
- [ ] `ip igmp join-group 239.1.1.1` configured on R3 Gi0/2
- [ ] `show ip igmp groups` on R3 shows 239.1.1.1 on Gi0/2
- [ ] `show ip rpf 10.1.1.10` on R2 shows RPF interface Gi0/0, RPF neighbor 10.1.12.1
- [ ] `show ip mroute 239.1.1.1` on R2 shows (*,G) and (S,G) entries after traffic
- [ ] R3 mroute shows Gi0/2 in the OIL for 239.1.1.1

### Troubleshooting

- [ ] Ticket 1 diagnosed and resolved (source-facing PIM interface)
- [ ] Ticket 2 diagnosed and resolved (wrong RP address on receiver router)
- [ ] Ticket 3 diagnosed and resolved (PIM missing on RP-to-source link)
