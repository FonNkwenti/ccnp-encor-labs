# Lab 02 — SSM, Bidirectional PIM, and MSDP

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

**Exam Objective:** 3.3.d — Describe IPv4 multicast protocols (IGMPv2/v3, PIM-SM, RP)

This lab extends the PIM-SM + BSR topology from Lab 01 with three advanced delivery modes that every CCNP-level engineer should be able to pick apart:

- **SSM** (Source-Specific Multicast) — skips the RP entirely, receivers subscribe to exact `(S,G)` pairs
- **Bidirectional PIM** — one shared tree in both directions, ideal for many-to-many flows
- **MSDP** (Multicast Source Discovery Protocol) — stitches separate PIM domains together without merging them

A fourth router, **R4**, is introduced as a second RP in its own PIM domain. You will fence the two domains with `ip pim bsr-border`, then re-join them at the control plane via MSDP so source activity on one RP propagates to the other.

### Source-Specific Multicast (SSM)

SSM, defined in RFC 4607, eliminates the shared tree and the RP. Receivers send IGMPv3 `INCLUDE` reports that name **both** the source and the group — the router plants an `(S,G)` state directly and RPF-builds the tree back to that source. There is no `(*,G)` entry, no register messages, no shared tree.

Two consequences you must internalise:

1. **IGMPv3 is non-negotiable.** IGMPv2 cannot express "join group 232.1.1.1 from source 10.1.1.10 only" — it only carries group addresses. A receiver-side LAN running IGMPv2 cannot use SSM.
2. **No RP means no single point of failure for that range.** But receivers must learn source addresses out-of-band (SDP, HTTP, DNS) since SSM has no source discovery of its own.

The IANA-reserved range is **232.0.0.0/8**. Cisco defaults enforce IGMPv3 in this range and reject `(*,G)` joins — the source's IP **must** be specified.

**Why it exists:** one-to-many content delivery (video streaming, stock tickers, software updates) where every receiver knows up-front which source to pull from. ASM's shared-tree overhead and register-message gymnastics are pure waste in that scenario.

### Bidirectional PIM (Bidir)

Bidir is PIM-SM's answer to many-to-many applications — multi-party video conferences, collaborative editing, market data distribution. In ASM, each source must register with the RP and then builds an SPT; 1,000 sources = 1,000 `(S,G)` states in the core. Bidir says: **use the shared tree for everything, in both directions, always.**

Key properties:

- **No `(S,G)` state** — only `(*,G)` entries ever exist for a bidir group
- **No source registration** — sources just send, no PIM Register messages
- **No SPT switchover** — traffic never leaves the shared tree
- **Designated Forwarder (DF) election** — each multi-access link elects one router per RP to forward both upstream (toward the RP) and downstream (away from the RP). The DF is the only router allowed to touch bidir traffic on that segment.

Bidir requires explicit enablement on every router with `ip pim bidir-enable` **before** any group is designated bidir. The RP is then advertised with the `bidir` keyword so every router plants bidir state for the matching range.

**Scaling win:** 1,000 sources on the same bidir group produce exactly one `(*,G)` entry per router. Same scaling cost as a single source.

### MSDP (Multicast Source Discovery Protocol)

PIM-SM is designed around a single RP per group. Two administrative domains (two enterprises, or an enterprise and an SP) each want their own RP but still need to exchange multicast traffic. Merging the PIM domains is not on the table — each owns its BSR election, its scope, its policy.

MSDP is the glue. It is a TCP-based protocol (port 639) between RPs in different PIM domains. When a local source registers with one RP, that RP sends a **Source-Active (SA)** message to its MSDP peers announcing "source X is active for group G here." Remote RPs cache this and can pull the source if a local receiver is interested.

What MSDP moves: **source knowledge only.** It does not move data packets. It does not move `(*,G)` joins. It does not build a tree across the boundary on its own. A remote RP that hears an SA and has a matching `(*,G)` will send a PIM `(S,G)` join toward the source's RP, which triggers the normal SPT setup across the domain boundary.

The PIM domains must remain separate. `ip pim bsr-border` on the interfaces that face the other domain stops BSR RP-set distribution from crossing — MSDP replaces that plumbing at the RP-to-RP level only.

**Canonical config elements:**

- `ip msdp peer <remote-rp> connect-source Loopback0` — TCP peering on the RP loopbacks
- `ip msdp originator-id Loopback0` — stamps SAs with a stable, routable identity
- `ip pim bsr-border` on every interface that crosses the domain boundary

### PIM Domain Borders & `ip pim bsr-border`

A **PIM domain** is a set of routers that share the same RP-set, either statically, via Auto-RP, or via BSR. A single misplaced BSR-Candidate announcement can leak into a neighbour domain and hijack its RP election.

`ip pim bsr-border` is an **interface** command that says: "do not send or accept BSR messages on this link." Auto-RP announcements are stopped by TTL-scoping, but BSR uses multicast 224.0.0.13 and will flood across any PIM-enabled link unless you fence it explicitly.

In this lab, R2 Gi0/2 (facing R4) and R3 Gi0/3 (facing R4) both carry `ip pim bsr-border`. Corresponding `bsr-border` on R4's interfaces completes the fence.

### Skills this lab develops

| Skill | Description |
|-------|-------------|
| Configure SSM range | Define an ACL for 232.0.0.0/8 and apply it with `ip pim ssm range` |
| IGMPv3 `INCLUDE` semantics | Place a static `(S,G)` source-specific join on a receiver LAN interface |
| Enable Bidirectional PIM | Activate bidir with `ip pim bidir-enable` and advertise a bidir RP-candidate |
| Identify the Designated Forwarder | Use `show ip pim interface df` to see DF winners on each segment |
| Configure MSDP | Establish a TCP peering between two RPs with `connect-source` and `originator-id` |
| Inspect the SA cache | Read `show ip msdp sa-cache` and relate entries to source activity |
| Fence a PIM domain | Apply `ip pim bsr-border` to stop BSR RP-set leakage between domains |
| Reason about multicast state | Tell at a glance whether an entry is `(*,G)`, `(S,G)`, SSM, or bidir from `show ip mroute` output |

---

## 2. Topology & Scenario

**Scenario** — You run the enterprise multicast backbone built across Labs 00–01. The network streams financial market data from the trading floor (PC1 → 10.1.1.10) to analyst desks (PC2 → 10.1.3.10) using ASM today.

Two new requirements have landed from engineering and operations:

1. **The trading platform vendor ships only over SSM.** Their market-data feed uses `232.1.1.1 from 10.1.1.10`. The receiver-side LAN must be able to subscribe with a source-specific join. No RP should sit in the data path for this range.
2. **Voice and collaboration teams want a bidirectional group** for conference bridge signalling on `239.2.2.0/24` — every participant is both a source and a receiver, and shared-tree-only forwarding is preferred to keep per-source state off the core routers.

Separately, a **partner company's network** (modelled here by R4, a second RP in a separate PIM domain) needs to receive source information for joint research flows. Management has said: do not merge the two domains. Use MSDP.

Your task: bring up R4, fence the two PIM domains, configure SSM and bidir across the enterprise, and establish the MSDP peering with R4.

```
                        ┌─────────────────────────┐
                        │           R1            │
                        │    (Source-side PE)     │
                        │    Lo0: 1.1.1.1/32      │
                        └───┬────────────────┬────┘
                     Gi0/0  │                │  Gi0/1
               10.1.12.1/30 │                │ 10.1.13.1/30
                            │                │
                            │                │
                            │                │
                     Gi0/0  │                │  Gi0/1
              10.1.12.2/30  │                │  10.1.13.2/30
               ┌────────────┴──────┐   ┌─────┴────────────┐
               │        R2         │   │        R3        │
               │ (Primary RP + BSR)│   │ (Receiver-side PE)│
               │  Lo0: 2.2.2.2/32  │   │ Lo0: 3.3.3.3/32  │
               │  RP for ASM+Bidir │   │                  │
               └──┬───────────┬────┘   └──┬──────────┬────┘
             Gi0/1│           │Gi0/2  Gi0/0        Gi0/3│
         10.1.23.1│           │10.1.24.1  10.1.23.2     │10.1.34.2
             /30  │           │/30          /30         │/30
                  │           │                         │
                  │           │  ┌──── L6 ────┐         │
                  └───────────┤  │  bsr-border│         │
                              │  └────────────┘         │
                     10.1.24.2│                         │10.1.34.1
                        Gi0/0 │                         │ Gi0/1
                              └──────┐       ┌──────────┘
                                     │       │
                                ┌────┴───────┴────┐
                                │       R4        │
                                │ (Second RP —    │
                                │  separate PIM   │
                                │     domain)     │
                                │ Lo0: 4.4.4.4/32 │
                                │ MSDP peer of R2 │
                                └─────────────────┘

              L4 (Source LAN)                     L5 (Receiver LAN)
              R1 Gi0/2 — PC1                      R3 Gi0/2 — PC2
              10.1.1.0/24                         10.1.3.0/24
```

**Key notes:**
- L6 (R2↔R4) and L7 (R3↔R4) both carry `ip pim bsr-border` — BSR RP-set is NOT advertised across the fence.
- R4 is a single-router PIM domain. It uses `ip pim rp-address 4.4.4.4` (static, self-reference) because it is the RP of its own domain.
- MSDP peering runs over the routed path Lo0 ↔ Lo0 (2.2.2.2 ↔ 4.4.4.4), carried by OSPF.
- To make SA traffic visible on R4 without attaching an extra LAN: R4's Loopback0 joins `239.1.1.1` so the MSDP SA cache has a real receiver pulling the `(S,G)` across the fence.

---

## 3. Hardware & Environment Specifications

### EVE-NG Cabling

| Link | Source | Interface | Target | Interface | Subnet | Role |
|------|--------|-----------|--------|-----------|--------|------|
| L1 | R1 | Gi0/0 | R2 | Gi0/0 | 10.1.12.0/30 | Core link |
| L2 | R2 | Gi0/1 | R3 | Gi0/0 | 10.1.23.0/30 | Core link |
| L3 | R1 | Gi0/1 | R3 | Gi0/1 | 10.1.13.0/30 | Core link (triangle) |
| L4 | R1 | Gi0/2 | PC1 | eth0 | 10.1.1.0/24 | Source LAN |
| L5 | R3 | Gi0/2 | PC2 | eth0 | 10.1.3.0/24 | Receiver LAN |
| L6 | R2 | Gi0/2 | R4 | Gi0/0 | 10.1.24.0/30 | **PIM domain border** |
| L7 | R3 | Gi0/3 | R4 | Gi0/1 | 10.1.34.0/30 | **PIM domain border** |

### Console Access Table

| Device | Port | Connection Command |
|--------|------|--------------------|
| R1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R3 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R4 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| PC1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| PC2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |

### Platform

- **Routers:** Cisco IOSv 15.9(3)M6 (QEMU image in EVE-NG)
- **Hosts:** VPCS 0.6.1
- **Control plane:** OSPFv2 area 0 — carries all multicast RPF lookups
- **Lab reset:** `python3 setup_lab.py --host <eve-ng-ip>` pushes `initial-configs/` to every device

---

## 4. Base Configuration

The `initial-configs/` directory contains the fully converged **Lab 01 end state** on R1/R2/R3 plus a **minimal R4** (IP addressing + OSPF only):

**Pre-loaded:**
- IP addressing on every interface, including R4's Gi0/0, Gi0/1, and Loopback0
- OSPF area 0 reachability across all four routers (R4 is already in the OSPF domain)
- `ip multicast-routing` globally on R1/R2/R3 (NOT on R4 — you will enable it)
- PIM sparse-mode on every R1/R2/R3 interface (NOT on R4)
- BSR-based RP discovery from Lab 01 — R2 is BSR-Candidate and RP-Candidate for the full 224/4 range
- IGMPv3 on R3 Gi0/2 from Lab 01
- `ip igmp join-group 239.1.1.1` on R3 Gi0/2 (ASM receiver carried over from Lab 01)

**NOT pre-loaded (student builds):**
- Multicast routing and PIM sparse-mode on R4
- Static RP self-reference on R4 (R4 is the RP of its own domain)
- `ip pim bsr-border` on the four inter-domain interfaces (R2 Gi0/2, R3 Gi0/3, R4 Gi0/0, R4 Gi0/1)
- SSM range definition and application cluster-wide
- Bidirectional PIM enablement and bidir RP-candidate advertisement
- Static SSM `(S,G)` join on R3 Gi0/2
- Bidir group join on R3 Gi0/2
- MSDP peering between R2 (2.2.2.2) and R4 (4.4.4.4)
- `ip igmp join-group 239.1.1.1` on R4 Loopback0 (so MSDP SA cache is demonstrable)

### Command-compatibility note

Several multicast features used in this lab (SSM range, bidirectional PIM, MSDP peering, BSR-border, IGMP static-group with source) are documented standard IOS 15.x syntax but have not been bench-verified on this specific EVE-NG IOSv image. If any command silently no-ops or the parser rejects it, flag it so `.agent/skills/reference-data/ios-compatibility.yaml` can be updated. Lab 00 and 01 ran this workflow without verify and succeeded on the same image.

---

## 5. Lab Challenge: Core Implementation

Configure the network to deliver three distinct multicast services (ASM, SSM, bidir) and exchange source information with a separate PIM domain via MSDP.

### Task 1: Bring R4 Into the Multicast Fabric

- Enable multicast routing globally on R4.
- Enable PIM sparse-mode on R4's Loopback0, Gi0/0, and Gi0/1.
- Configure R4 as the static RP for itself — R4 is the sole router in its own PIM domain, so it must know where to send register messages: its own loopback.
- Enable bidirectional PIM globally on R4 (so R4 matches the rest of the cluster once bidir is turned up in Task 4).

**Verification:** `show ip pim interface` on R4 must list all three multicast-enabled interfaces. `show ip pim rp mapping` on R4 must show itself (4.4.4.4) as the static RP for 224.0.0.0/4.

---

### Task 2: Fence the PIM Domains

- Apply the BSR-border command to every interface that crosses between R2/R3's domain and R4's domain. That means:
  - R2 Gi0/2 (facing R4)
  - R3 Gi0/3 (facing R4)
  - R4 Gi0/0 (facing R2)
  - R4 Gi0/1 (facing R3)
- Confirm that R4 still does NOT hear R2's BSR advertisements — R4 must run its own RP-set, independent of R2's BSR.

**Verification:** `show ip pim bsr-router` on R4 must show no BSR learned (R4 is in its own domain with no BSR). `show ip pim rp mapping` on R4 must list only itself (not R2). `show ip pim interface` on R2 Gi0/2 and R3 Gi0/3 must show BSR-Border as enabled.

---

### Task 3: Enable Source-Specific Multicast

- Define a standard ACL named SSM_RANGE that permits the 232.1.1.0/24 range.
- Apply this ACL cluster-wide — on R1, R2, R3, and R4 — so every router treats 232.1.1.0/24 as SSM.
- R3's receiver LAN (Gi0/2) is already running IGMPv3 from Lab 01 — confirm this is still the case.
- Install a static source-specific join on R3 Gi0/2 for group 232.1.1.1 with source 10.1.1.10 (PC1). This simulates an IGMPv3 receiver without needing to script VPCS.

**Verification:** `show ip pim ssm-mapping` on any router (or `show running-config | include ssm`) must confirm the SSM range. `show ip igmp groups detail` on R3 must show 232.1.1.1 with source 10.1.1.10 in INCLUDE mode. Ping `232.1.1.1` **from PC1** (source 10.1.1.10 — PC1 owns that IP, R1 does not) and confirm R3 installs an `(S,G)` mroute via RPF toward R1 — **not** via the RP. A ping from R1 cannot work here because R1 does not own 10.1.1.10 and IOS won't let you spoof a non-local source.

---

### Task 4: Enable Bidirectional PIM and Advertise a Bidir RP

- Enable bidirectional PIM globally on every router in the main domain (R1, R2, R3). R4 already has it from Task 1.
- On R2, split the existing BSR RP-candidate advertisement into two:
  - ASM_GROUPS ACL → permits 239.1.1.0/24 → advertised as **non-bidir** RP
  - BIDIR_GROUPS ACL → permits 239.2.2.0/24 → advertised as **bidir** RP (use the `bidir` keyword)
- Keep the SSM range (232.1.1.0/24) out of both ACLs — SSM skips the RP entirely.
- Add a receiver for the bidir group: on R3 Gi0/2, join 239.2.2.1.

**Verification:** `show ip pim rp mapping` on R1/R3 must show 2.2.2.2 listed twice — once as RP for 239.1.1.0/24 (SM mode) and once as RP for 239.2.2.0/24 (Bidir mode). `show ip pim interface df` must show a DF winner for every PIM-enabled interface facing a bidir group.

---

### Task 5: Stand Up MSDP

- On R2, configure an MSDP peer toward R4's loopback (4.4.4.4) with R2's own loopback as the connect-source.
- On R4, configure the reciprocal peer toward 2.2.2.2 with its own loopback as connect-source.
- On both sides, set `originator-id Loopback0` so SA messages carry a stable, routable identity.
- Give each peer a description for operational clarity.
- On R4, install `ip igmp join-group 239.1.1.1` on Loopback0. This makes R4 itself a receiver for 239.1.1.1 — when a source registers at R2 (the primary RP), R4 learns about it via MSDP SA and installs an `(S,G)` that points back across the fence toward R2.

**Verification:** `show ip msdp summary` on both R2 and R4 must show the peer in **Up** state. `show ip msdp peer 4.4.4.4` on R2 must show a TCP session established on port 639. `show ip msdp sa-cache` on R4 must show an SA entry after R1 pings 239.1.1.1 (the source registers at R2, R2 advertises via MSDP, R4 caches it).

---

### Task 6: End-to-End Data-Plane Validation

- From R1, generate a 5-packet multicast ping to **each** of the following, observe the receiver, then record which forwarding model was used:
  - `239.1.1.1` with source 10.1.1.1 — ASM (shared tree, BSR RP = R2)
  - `232.1.1.1` with source 10.1.1.10 — SSM (no RP, direct SPT to receiver)
  - `239.2.2.1` with source 10.1.1.1 — Bidir (shared tree only, DF-forwarded)
- Confirm on R2 and R3 that the mroute table shows the expected state type for each group:
  - 239.1.1.1 → `(*,G)` + `(S,G)` (SPT switchover behavior from lab-00/01)
  - 232.1.1.1 → `(S,G)` only, **no** `(*,G)`
  - 239.2.2.1 → `(*,G)` only, **Bidir** flag, no `(S,G)`

**Verification:** `show ip mroute 232.1.1.1` must list `(10.1.1.10, 232.1.1.1)` with no `(*, 232.1.1.1)`. `show ip mroute 239.2.2.1` must show the `B` (bidir) flag on the `(*,G)` line. `show ip msdp sa-cache` on R4 must show an active SA for 239.1.1.1 sourced at 10.1.1.1.

---

## 6. Verification & Analysis

### Task 1 — R4 multicast-enabled and aware of its own RP

```bash
R4# show ip pim interface

Address          Interface                Ver/   Nbr    Query  DR         DR
                                          Mode   Count  Intvl  Prior
4.4.4.4          Loopback0                v2/S   0      30     1          4.4.4.4     ! ← sparse mode
10.1.24.2        GigabitEthernet0/0       v2/S   1      30     1          10.1.24.2   ! ← PIM neighbor with R2
10.1.34.1        GigabitEthernet0/1       v2/S   1      30     1          10.1.34.1   ! ← PIM neighbor with R3

R4# show ip pim rp mapping
PIM Group-to-RP Mappings

Group(s): 224.0.0.0/4, Static
    RP: 4.4.4.4 (?)                                                       ! ← R4 is its own RP
```

### Task 2 — PIM domain fence verified

```bash
R4# show ip pim bsr-router
PIMv2 Bootstrap information
This system is not a BSR.                                                 ! ← no BSR learned (good)
```

```bash
R2# show ip pim interface GigabitEthernet0/2 detail
GigabitEthernet0/2 is up, line protocol is up
  BSR Border: Yes                                                         ! ← fence active on R2 Gi0/2
```

```bash
R3# show ip pim interface GigabitEthernet0/3 detail
GigabitEthernet0/3 is up, line protocol is up
  BSR Border: Yes                                                         ! ← fence active on R3 Gi0/3
```

### Task 3 — SSM active and receiver joined

```bash
R3# show ip pim ssm-mapping
Origin Type | ACL
Static      | SSM_RANGE                                                   ! ← SSM range bound to ACL

R3# show ip igmp groups 232.1.1.1 detail
Interface:  GigabitEthernet0/2
Group:      232.1.1.1
Group mode: INCLUDE                                                       ! ← IGMPv3 INCLUDE (SSM semantics)
  Source Address   Uptime    Expires   Fwd  Flags
  10.1.1.10        00:01:42  stopped   Yes  4S                            ! ← source 10.1.1.10 bound
```

After `ping 232.1.1.1` from PC1 (source 10.1.1.10):

```bash
R3# show ip mroute 232.1.1.1
(10.1.1.10, 232.1.1.1), 00:00:05/00:03:24, flags: sTI                     ! ← (S,G) only, no (*,G)
  Incoming interface: GigabitEthernet0/1, RPF nbr 10.1.13.1               ! ← RPF direct to R1, not via R2/RP
  Outgoing interface list:
    GigabitEthernet0/2, Forward/Sparse, 00:00:05/00:03:24
```

> Why from PC1 and not R1? R3's IGMPv3 INCLUDE filter is bound to source **10.1.1.10**, which is PC1's address. R1 cannot originate traffic with that source — it's not one of R1's interface IPs, and IOS refuses non-local `source` arguments. Send the SSM test from the VPCS host that actually owns 10.1.1.10.

### Task 4 — Bidir RP active and DF elected

```bash
R1# show ip pim rp mapping
PIM Group-to-RP Mappings

Group(s) 239.1.1.0/24                                                     ! ← ASM range
  RP 2.2.2.2 (?), v2
    Info source: 2.2.2.2 (?), via bootstrap, priority 0
    Uptime: 00:05:12, expires: 00:02:10

Group(s) 239.2.2.0/24, Bidir                                              ! ← Bidir range
  RP 2.2.2.2 (?), v2
    Info source: 2.2.2.2 (?), via bootstrap, priority 0
    Uptime: 00:05:12, expires: 00:02:10                                   ! ← same RP, bidir flag
```

```bash
R3# show ip pim interface df
Interface                RP               DF Winner        Metric    Uptime
GigabitEthernet0/0       2.2.2.2          10.1.23.1        20        00:04:33   ! ← R2 is DF toward RP
GigabitEthernet0/1       2.2.2.2          10.1.13.2        20        00:04:33   ! ← R3 is DF locally
GigabitEthernet0/2       2.2.2.2          10.1.3.1         20        00:04:33   ! ← R3 DF on receiver LAN
```

After R1 pings 239.2.2.1:

```bash
R3# show ip mroute 239.2.2.1
(*, 239.2.2.1), 00:00:08/00:03:21, RP 2.2.2.2, flags: BC                  ! ← B = Bidir, C = connected receiver
  Bidir-Upstream: GigabitEthernet0/0, RPF nbr 10.1.23.1
  Outgoing interface list:
    GigabitEthernet0/2, Forward/Sparse, 00:00:08/stopped                  ! ← no (S,G) ever appears for bidir
```

### Task 5 — MSDP peering Up and SA cache populated

```bash
R2# show ip msdp summary
MSDP Peer Status Summary
Peer Address     AS   State       Uptime/  Reset  SA  Peer Name
                                  Downtime Count  Count
4.4.4.4          ?    Up          00:03:12 0      1   R4-MSDP-PEER         ! ← Up, SA count > 0

R2# show ip msdp peer 4.4.4.4
MSDP Peer 4.4.4.4 (R4-MSDP-PEER), AS ?
  Connection status:
    State: Up, Resets: 0, Connection source: Loopback0 (2.2.2.2)           ! ← TCP session on port 639
    Uptime(Downtime): 00:03:12, SA messages received: 0, SA messages sent: 1
```

After R1 pings 239.1.1.1:

```bash
R4# show ip msdp sa-cache
MSDP Source-Active Cache - 1 entries
(10.1.1.1, 239.1.1.1), RP 2.2.2.2, MBGP/AS 0, 00:00:15/00:05:44, Peer 2.2.2.2   ! ← SA received from R2
```

```bash
R4# show ip mroute 239.1.1.1
(10.1.1.1, 239.1.1.1), 00:00:10/00:02:49, flags: s                        ! ← (S,G) installed via SA+MSDP
  Incoming interface: GigabitEthernet0/0, RPF nbr 10.1.24.1               ! ← RPF back to R2 across border
  Outgoing interface list:
    Loopback0, Forward/Sparse, 00:00:10/00:02:49                          ! ← Lo0 is the receiver
```

### Task 6 — Three models, three states

| Group | Expected mroute state | Path |
|-------|----------------------|------|
| 239.1.1.1 (ASM) | `(*, G)` + `(S, G)` after SPT switch | R1 → R2 (RP) → R3 → PC2 |
| 232.1.1.1 (SSM) | `(S, G)` only, no `(*, G)` | R1 → R3 direct (via L3) |
| 239.2.2.1 (Bidir) | `(*, G)` with `B` flag, no `(S, G)` ever | Shared tree both ways |

---

## 7. Verification Cheatsheet

### SSM Configuration

```
ip pim ssm range ACL_NAME
ip access-list standard ACL_NAME
 permit 232.0.0.0 0.255.255.255
!
interface X
 ip igmp version 3
 ip igmp static-group GROUP source SOURCE_IP
```

| Command | Purpose |
|---------|---------|
| `ip pim ssm range ACL` | Bind SSM behaviour to groups matched by ACL |
| `ip pim ssm default` | Enable SSM on the IANA-reserved 232/8 range |
| `ip igmp version 3` | Required on receiver interface — IGMPv2 cannot carry source lists |
| `ip igmp static-group G source S` | Pseudo-receiver join (useful when no real IGMPv3 host is attached) |

> **Exam tip:** SSM range is validated globally but enforced per-group — any group in the ACL is treated SSM, any outside is treated ASM/bidir/whatever rules apply.

### Bidirectional PIM

```
ip pim bidir-enable
ip pim rp-candidate Loopback0 group-list BIDIR_ACL bidir
ip access-list standard BIDIR_ACL
 permit 239.2.2.0 0.0.0.255
```

| Command | Purpose |
|---------|---------|
| `ip pim bidir-enable` | Required globally on **every** router in the bidir domain before any bidir group will work |
| `ip pim rp-candidate ... bidir` | Advertise this RP as a bidir RP via BSR (the `bidir` keyword is the switch) |
| `ip pim rp-address R bidir` | Static equivalent of the above |
| `show ip pim interface df` | List DF winner per interface per RP (bidir only) |

> **Exam tip:** If **any** router in the shared-tree path has not run `ip pim bidir-enable`, bidir traffic is silently dropped at that hop — no error message. It is the silent-failure trap the exam likes.

### MSDP Peering

```
ip msdp peer REMOTE_IP connect-source Loopback0
ip msdp description REMOTE_IP TEXT
ip msdp originator-id Loopback0
```

| Command | Purpose |
|---------|---------|
| `ip msdp peer X connect-source Lo0` | Define TCP peer to remote RP, source from loopback |
| `ip msdp originator-id Lo0` | Stamp outbound SAs with a loopback identity (survives physical link failure) |
| `ip msdp description` | Free-text peer description for `show` output |
| `ip msdp default-peer X` | Fallback peer for all SAs (stub MSDP topology) |
| `ip msdp sa-filter in/out` | Policy controls on what SAs to accept/announce |

> **Exam tip:** `connect-source Loopback0` and `originator-id Loopback0` are **not** the same. `connect-source` is the source IP of the TCP session. `originator-id` is the RP identity stamped inside the SA payload. They usually match but do not have to.

### Domain Border

```
interface X
 ip pim bsr-border
```

| Command | Purpose |
|---------|---------|
| `ip pim bsr-border` | Interface-level — do not send/receive BSR messages on this link |

### Verification Commands

| Command | What to Look For |
|---------|-----------------|
| `show ip pim rp mapping` | One entry per group range per RP; `Bidir` keyword on bidir ranges |
| `show ip pim ssm-mapping` | SSM range ACL bound |
| `show ip igmp groups detail` | INCLUDE/EXCLUDE mode, source list for IGMPv3 |
| `show ip mroute 232.1.1.1` | `(S,G)` only, no `(*,G)` — confirms SSM |
| `show ip mroute 239.2.2.1` | `B` flag on `(*,G)`, no `(S,G)` ever — confirms Bidir |
| `show ip pim interface df` | DF winner per segment per RP |
| `show ip msdp summary` | Peer state should be `Up`, SA count > 0 once sources active |
| `show ip msdp sa-cache` | Cached `(S,G)` entries with RP + peer identity |
| `show ip msdp peer X` | TCP session details, source/originator IP, reset count |
| `show ip pim bsr-router` | On R4 must show "not a BSR" AND no BSR learned — confirms fence |

### SSM/Bidir/ASM Quick-Reference

| Mode | Group range | `(*,G)` state | `(S,G)` state | RP needed | IGMP version |
|------|------------|--------------|--------------|-----------|--------------|
| ASM | 224/4 minus others | Yes | Yes (after SPT switch) | Yes | v2 or v3 |
| SSM | 232.0.0.0/8 | **No** | Yes only | **No** | v3 only |
| Bidir | designated by RP config | Yes (with `B` flag) | **Never** | Yes | v2 or v3 |

### Common Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| SSM group join rejected with `Group not in SSM range` | `ip pim ssm range ACL` missing or ACL scope wrong |
| IGMPv3 source-specific join silently ignored | Receiver interface still running IGMPv2 |
| Bidir traffic drops at one hop | Router in path missing `ip pim bidir-enable` |
| DF election "stuck" / no winner | Bidir enabled only on some routers; offer messages are ignored |
| MSDP peer stuck in Inactive | TCP reachability broken OR `connect-source` address not reachable from peer |
| MSDP Up but SA count stays at 0 | No source has registered yet at the local RP, OR register-filter is blocking |
| R4 hears R2's BSR announcements | `ip pim bsr-border` missing on one of the four fence interfaces |
| R4 SA cache populated but no `(S,G)` | No local receiver on R4 — MSDP learns, but nothing pulls |

---

## 8. Solutions (Spoiler Alert!)

> Try the lab end to end before looking at these. The exam-level skill is in the thinking, not the typing.

### Task 1: Bring R4 Into the Multicast Fabric

<details>
<summary>Click to view R4 Configuration</summary>

```bash
! R4
ip multicast-routing
ip pim bidir-enable
ip pim rp-address 4.4.4.4
!
interface Loopback0
 ip pim sparse-mode
!
interface GigabitEthernet0/0
 ip pim sparse-mode
!
interface GigabitEthernet0/1
 ip pim sparse-mode
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ip pim interface
show ip pim rp mapping
show ip pim neighbor
```
</details>

---

### Task 2: Fence the PIM Domains

<details>
<summary>Click to view R2 Configuration</summary>

```bash
! R2
interface GigabitEthernet0/2
 ip pim bsr-border
```
</details>

<details>
<summary>Click to view R3 Configuration</summary>

```bash
! R3
interface GigabitEthernet0/3
 ip pim bsr-border
```
</details>

<details>
<summary>Click to view R4 Configuration</summary>

```bash
! R4
interface GigabitEthernet0/0
 ip pim bsr-border
!
interface GigabitEthernet0/1
 ip pim bsr-border
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ip pim bsr-router
show ip pim rp mapping
show ip pim interface GigabitEthernet0/2 detail
```
</details>

---

### Task 3: Enable Source-Specific Multicast

<details>
<summary>Click to view R1/R2/R3/R4 Configuration</summary>

```bash
! R1, R2, R3, R4 (same on every router)
ip pim ssm range SSM_RANGE
!
ip access-list standard SSM_RANGE
 permit 232.1.1.0 0.0.0.255
```
</details>

<details>
<summary>Click to view R3 Receiver Configuration</summary>

```bash
! R3
interface GigabitEthernet0/2
 ip igmp version 3
 ip igmp static-group 232.1.1.1 source 10.1.1.10
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ip pim ssm-mapping
show ip igmp groups detail
! ping must be sent from PC1 (which owns 10.1.1.10), not from R1:
! PC1> ping 232.1.1.1
show ip mroute 232.1.1.1                   ! expect (10.1.1.10, 232.1.1.1) with non-zero OIL counter
```
</details>

---

### Task 4: Bidirectional PIM + Split RP-Candidate

<details>
<summary>Click to view R1, R2, R3 Global Configuration</summary>

```bash
! R1, R2, R3 — bidir must be enabled cluster-wide
ip pim bidir-enable
```
</details>

<details>
<summary>Click to view R2 RP-Candidate Split</summary>

```bash
! R2
no ip pim rp-candidate Loopback0
!
ip pim rp-candidate Loopback0 group-list ASM_GROUPS
ip pim rp-candidate Loopback0 group-list BIDIR_GROUPS bidir
!
ip access-list standard ASM_GROUPS
 permit 239.1.1.0 0.0.0.255
ip access-list standard BIDIR_GROUPS
 permit 239.2.2.0 0.0.0.255
```
</details>

<details>
<summary>Click to view R3 Receiver Configuration</summary>

```bash
! R3
interface GigabitEthernet0/2
 ip igmp join-group 239.2.2.1
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ip pim rp mapping
show ip pim interface df
ping 239.2.2.1 source 10.1.1.1 repeat 5    ! from R1
show ip mroute 239.2.2.1
```
</details>

---

### Task 5: MSDP Peering Between R2 and R4

<details>
<summary>Click to view R2 Configuration</summary>

```bash
! R2
ip msdp peer 4.4.4.4 connect-source Loopback0
ip msdp description 4.4.4.4 R4-MSDP-PEER
ip msdp originator-id Loopback0
```
</details>

<details>
<summary>Click to view R4 Configuration</summary>

```bash
! R4
ip msdp peer 2.2.2.2 connect-source Loopback0
ip msdp description 2.2.2.2 R2-MSDP-PEER
ip msdp originator-id Loopback0
!
interface Loopback0
 ip igmp join-group 239.1.1.1
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ip msdp summary
show ip msdp peer 4.4.4.4
ping 239.1.1.1 source 10.1.1.1 repeat 5    ! from R1
show ip msdp sa-cache                      ! on R4
show ip mroute 239.1.1.1                   ! on R4
```
</details>

---

### Task 6: End-to-End Validation

<details>
<summary>Click to view Verification Commands</summary>

```bash
! From R1 (ASM and Bidir — R1 can source these from its own LAN IP):
ping 239.1.1.1 source 10.1.1.1 repeat 5      ! ASM
ping 239.2.2.1 source 10.1.1.1 repeat 5      ! Bidir

! SSM must be sent from PC1 (source 10.1.1.10 — PC1 owns it, R1 does not):
! PC1> ping 232.1.1.1

! On R3 and R4:
show ip mroute 239.1.1.1
show ip mroute 232.1.1.1                     ! expect (10.1.1.10, 232.1.1.1), non-zero OIL counter
show ip mroute 239.2.2.1
show ip msdp sa-cache
```
</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a fault a real operator would see. Inject the fault first, then diagnose and fix using only `show` commands.

### Workflow

```bash
python3 setup_lab.py                                   # reset to known-good
python3 scripts/fault-injection/inject_scenario_01.py  # Ticket 1
python3 scripts/fault-injection/apply_solution.py      # restore
```

---

### Ticket 1 — Receiver-Side Router Rejects Source-Specific Joins

Operations reports that R3's IGMPv3 source-specific join for `232.1.1.1 from 10.1.1.10` is being rejected with "Group not in SSM range." The receiver LAN was working with SSM yesterday. Nothing in the IGMP configuration was touched.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py`

**Success criteria:** `show ip igmp groups 232.1.1.1 detail` on R3 shows INCLUDE mode with source 10.1.1.10 bound, and `ping 232.1.1.1` from PC1 (source 10.1.1.10) causes R3 to install an `(S,G)` mroute entry with a non-zero OIL packet counter.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Check IGMP state on R3 Gi0/2:
   `show ip igmp groups 232.1.1.1 detail`
   — IGMPv3 is still running; source join is present in config but flagged as inactive.
2. Check SSM range binding on R3:
   `show ip pim ssm-mapping`
   `show running-config | section ip pim`
   — Either the `ip pim ssm range SSM_RANGE` command is missing or the ACL SSM_RANGE has a scope that no longer covers 232.1.1.0/24.
3. Compare to R1/R2/R4:
   `show ip pim ssm-mapping`
   — Other routers still have it; only R3 is inconsistent.
</details>

<details>
<summary>Click to view Fix</summary>

Restore the SSM range binding on R3 (or whichever element of the ACL/binding was altered):

```bash
! R3
ip pim ssm range SSM_RANGE
!
ip access-list standard SSM_RANGE
 permit 232.1.1.0 0.0.0.255
```

Verify with `show ip pim ssm-mapping` and re-test with `ping 232.1.1.1` from PC1 (source 10.1.1.10 — R3's INCLUDE filter requires that exact source).
</details>

---

### Ticket 2 — Bidirectional Group Drops at One Hop

A voice team member reports that conference bridge traffic on `239.2.2.1` works between R2 and R3 but fails end-to-end from R1. R1 is the source; PC2 (R3 receiver) hears nothing. BSR RP-mapping on R1 shows 2.2.2.2 with the Bidir flag — so the control plane looks correct.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py`

**Success criteria:** `ping 239.2.2.1 source 10.1.1.1` from R1 produces a reply (or at minimum, the `(*,239.2.2.1)` entry on R1 shows a `B` flag and packets show up in R3's `show ip mroute count` for this group).

<details>
<summary>Click to view Diagnosis Steps</summary>

1. From R3, confirm the receive side is functional:
   `show ip mroute 239.2.2.1` — `(*,G)` with `B` flag present.
   `show ip pim interface df` — DF winners look correct on L2 and L5.
2. From R1, check bidir state:
   `show ip pim rp mapping`
   — 239.2.2.0/24 is listed with RP 2.2.2.2 and Bidir flag. Control plane OK.
   `show ip mroute 239.2.2.1`
   — `(*,G)` entry either missing the `B` flag or no entry at all.
3. Check global bidir enablement on R1:
   `show running-config | include bidir`
   — The `ip pim bidir-enable` global command is missing from R1. Without it, R1 ignores bidir announcements and does not install bidir state. Traffic is silently black-holed on the first hop.
</details>

<details>
<summary>Click to view Fix</summary>

Re-enable bidir globally on R1:

```bash
! R1
ip pim bidir-enable
```

Confirm with `show ip pim rp mapping` — 239.2.2.0/24 now shows Bidir. `show ip mroute 239.2.2.1` shows `(*,G)` with `B` flag. Re-ping from R1 and watch R3.
</details>

---

### Ticket 3 — MSDP Peer Up but Remote Cache Is Empty

Operators on the partner network (R4) report that their `show ip msdp sa-cache` has been empty for hours, even though R2 shows active sources and the MSDP peer is listed as `Up` on both sides. The TCP session is established. Nothing else is alarming.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py`

**Success criteria:** After generating multicast traffic on R1 (e.g. `ping 239.1.1.1 source 10.1.1.1`), R4's `show ip msdp sa-cache` must display an entry for `(10.1.1.1, 239.1.1.1)` with peer 2.2.2.2.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Confirm MSDP session state on both sides:
   `show ip msdp summary` — Up on both R2 and R4. SA count on R2's side to R4 is 0 or stuck.
2. From R2, check whether sources are actually registering locally:
   `show ip pim rp mapping` — 2.2.2.2 is RP for 239.1.1.0/24.
   `show ip mroute 239.1.1.1` — `(S,G)` exists at R2 for the active source.
3. From R2, check the MSDP originator configuration:
   `show running-config | section ip msdp`
   — `ip msdp originator-id Loopback0` is missing OR `ip msdp sa-filter out` is blocking. Without a valid originator, the SA is generated but discarded or stamped with an unroutable address.
4. From R4:
   `show ip msdp peer 2.2.2.2` — Connection Up, but SA messages received = 0.
</details>

<details>
<summary>Click to view Fix</summary>

Restore the MSDP originator-id on R2 (or remove the blocking SA filter):

```bash
! R2
ip msdp originator-id Loopback0
```

Re-generate source traffic:
```bash
R1# ping 239.1.1.1 source 10.1.1.1 repeat 5
```

Check R4:
```bash
R4# show ip msdp sa-cache
MSDP Source-Active Cache - 1 entries
(10.1.1.1, 239.1.1.1), RP 2.2.2.2, ...
```
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] R4 has multicast routing, PIM sparse-mode on all three interfaces, and itself as static RP
- [ ] `ip pim bsr-border` applied on R2 Gi0/2, R3 Gi0/3, R4 Gi0/0, and R4 Gi0/1
- [ ] R4 `show ip pim bsr-router` confirms no BSR learned from R2's domain
- [ ] SSM range ACL applied on R1/R2/R3/R4
- [ ] R3 Gi0/2 has IGMPv3 and a static-group `(232.1.1.1, 10.1.1.10)` join
- [ ] `ping 232.1.1.1` from PC1 (source 10.1.1.10) creates an `(S,G)`-only entry on R3 with non-zero OIL packet counter (no `(*,G)` — SSM has no shared tree)
- [ ] `ip pim bidir-enable` on R1/R2/R3/R4
- [ ] R2 advertises two RP-candidates — one SM for 239.1.1.0/24, one Bidir for 239.2.2.0/24
- [ ] R3 Gi0/2 joins 239.2.2.1
- [ ] `show ip pim rp mapping` on R1 lists both RP entries with distinct modes
- [ ] `ping 239.2.2.1 source 10.1.1.1` produces a `(*,G)` with `B` flag, no `(S,G)`
- [ ] MSDP peer R2↔R4 Up in `show ip msdp summary`
- [ ] R4 Lo0 joins 239.1.1.1
- [ ] `ping 239.1.1.1 source 10.1.1.1` from R1 produces an SA entry in R4's `show ip msdp sa-cache`

### Troubleshooting

- [ ] Ticket 1 fault diagnosed via `show ip pim ssm-mapping` and fixed
- [ ] Ticket 2 fault diagnosed via `show ip pim rp mapping` / bidir-enable check and fixed
- [ ] Ticket 3 fault diagnosed via `show ip msdp peer` + running-config inspection and fixed
- [ ] All three tickets pass their Success Criteria after the fix
