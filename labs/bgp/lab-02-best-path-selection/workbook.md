# BGP Lab 02 -- Best Path Selection and Attributes

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

**Exam Objective:** CCNP ENCOR 350-401, 3.2.c -- Configure and verify eBGP (best path selection, neighbor relationships).

Lab 02 takes the dual-stack topology you built in Lab 01 and adds a third autonomous system (AS 65003 on R4) so that AS 65001 now has multiple BGP paths to the same destination. This is where the best-path algorithm stops being theoretical: every prefix you see in `show bgp` has more than one possible path, and BGP must pick exactly one. You will manipulate each tie-breaker attribute in turn -- Weight, LOCAL_PREF, AS_PATH, MED, Origin -- and watch the selected path move in real time.

### The BGP Best-Path Algorithm

When BGP has more than one path to a prefix, it walks down this ordered list until one path wins. The first step that produces a unique winner ends the evaluation -- steps below it are never considered.

| Step | Attribute | Rule | Scope | Configured With |
|------|-----------|------|-------|-----------------|
| 1 | **Weight** | Higher wins | Local to this router only | `neighbor X weight N` or route-map `set weight` |
| 2 | **LOCAL_PREF** | Higher wins | Propagated within the AS via iBGP | route-map `set local-preference` inbound |
| 3 | Locally originated | Locally injected (`network` / `redistribute`) wins over learned | Local | Implicit |
| 4 | **AS_PATH length** | Shorter wins | Global -- carried in every advertisement | route-map `set as-path prepend` outbound |
| 5 | **Origin** | IGP < EGP < Incomplete | Global | route-map `set origin` |
| 6 | **MED** | Lower wins, compared only across paths from same neighbor AS | Leaks 1 AS, not propagated further | route-map `set metric` outbound |
| 7 | eBGP over iBGP | eBGP path preferred | Local | Implicit |
| 8 | IGP metric to NEXT_HOP | Lower wins | Local | IGP cost to BGP next-hop |
| 9+ | Router-ID, cluster-list, neighbor IP | Tie-breakers | -- | Implicit |

**Key insight:** the algorithm is strictly ordered. If Weight produces a unique winner on this router, LOCAL_PREF is never consulted -- even if LOCAL_PREF would have picked a different path. This is why Weight is "sledgehammer" local policy: it overrides everything downstream.

### Weight -- Cisco-Proprietary, Router-Local

Weight is a Cisco extension. It lives only on the router where it is configured and is never carried in BGP updates. This makes it useful for overriding everything else on a single router without coordinating with any neighbor, but useless for influencing downstream routers.

```
! Set weight at neighbor level (applies to all prefixes from this peer):
router bgp <AS>
 neighbor <peer-ip> weight <0-65535>

! Or set weight per-prefix via route-map inbound:
route-map SET_WEIGHT permit 10
 match ip address prefix-list SOME_PREFIXES
 set weight 500
!
router bgp <AS>
 address-family ipv4
  neighbor <peer-ip> route-map SET_WEIGHT in
```

Default weight is 0 for learned routes and 32768 for locally originated routes -- which is why your own `network`-ed prefixes always win on your own router.

### LOCAL_PREF -- The AS-Wide Exit Selector

LOCAL_PREF is the "stay within the AS" equivalent of Weight. Unlike Weight, it rides in iBGP updates, so every router inside the AS learns which exit the AS as a whole prefers. Higher LOCAL_PREF wins.

```
route-map PREFER_PRIMARY permit 10
 set local-preference 200
!
router bgp <AS>
 address-family ipv4
  neighbor <primary-eBGP-peer> route-map PREFER_PRIMARY in
```

Default LOCAL_PREF is 100 when not explicitly set. The classic enterprise pattern: both edge routers receive the same external prefix from the same ISP, but you tag the preferred edge's inbound updates with 200. iBGP carries that 200 to the other edge, so every router in your AS agrees on the same exit.

### AS_PATH -- Inbound Influence Across ASes

LOCAL_PREF and Weight only control *outbound* traffic (how your AS leaves). To control *inbound* traffic (how other ASes reach you), you have to make your advertisements less attractive through their algorithm. AS_PATH prepending inflates the length of your AS_PATH so that neighbor ASes see your path as longer.

```
route-map PREPEND_TO_R1 permit 10
 set as-path prepend <AS> <AS> <AS>
!
router bgp <AS>
 address-family ipv4
  neighbor <peer-ip> route-map PREPEND_TO_R1 out
```

Each prepend of your own AS adds one hop to the path length. Other ASes compare path lengths and pick the shortest -- so prepending on one exit shifts inbound traffic toward the other exit.

### MED -- Multi-Exit Discriminator

MED (also called METRIC in show output) is a hint to a *neighboring AS* when you have multiple peering points with that neighbor: "please come in this way; avoid that way." Lower MED wins. It only propagates one AS away and is compared only among paths from the same neighbor AS.

```
route-map SET_MED_PRIMARY permit 10
 set metric 50
!
router bgp <AS>
 address-family ipv4
  neighbor <peer-ip> route-map SET_MED_PRIMARY out
```

Critical limitation: by default Cisco does **not** compare MED across paths from different ASes. If you send MED=50 and another AS sends MED=10, IOS does not pick the lower one unless you configure `bgp always-compare-med`.

### Origin -- IGP, EGP, or Incomplete

The Origin attribute records how the prefix originally entered BGP:

| Origin | Code | Source |
|--------|------|--------|
| IGP | `i` | Advertised with `network` statement |
| EGP | `e` | Legacy -- not used today |
| Incomplete | `?` | Redistributed into BGP from an IGP |

When Origin is the deciding step, IGP (`i`) beats Incomplete (`?`). This is why `network` statements are almost always preferred over redistribution for the same prefix.

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| Introduce a third AS | Add R4 in AS 65003 and establish eBGP to R3 across an IPv4+IPv6 peering. |
| Interpret best-path output | Read `show bgp ipv4 unicast <prefix>` and identify why BGP chose the selected path. |
| Apply Weight | Use a route-map with `set weight` to override everything downstream on one router. |
| Apply LOCAL_PREF | Use a route-map with `set local-preference` inbound to make the AS as a whole prefer one exit. |
| Apply AS_PATH prepending | Use `set as-path prepend` outbound to influence how other ASes reach you. |
| Apply MED | Use `set metric` outbound to hint path preference to a neighboring AS. |
| Compare path selection across IPv4 and IPv6 | Validate that BGP runs the same algorithm independently per address-family. |
| Troubleshoot best-path decisions | Diagnose why a "wrong" path was chosen by walking the algorithm in order. |

---

## 2. Topology & Scenario

Your enterprise (AS 65001) now has TWO external peering relationships -- directly to ISP AS 65002 via R3, and through AS 65002 to the remote branch AS 65003 on R4. This creates multiple paths for every external prefix, and the business wants deterministic, documented path preferences: R1 is the primary exit, R2 is backup; incoming traffic to the enterprise should prefer coming in through R1 but survive an R1 outage.

```
                    ┌────────── AS 65001 ──────────┐
                    │                                │
                    │  ┌────────────────┐           │
                    │  │       R1       │◄──PC1     │
                    │  │ Enterprise Ed1 │           │
                    │  │ Lo0: 1.1.1.1   │           │
                    │  └───────┬────────┘           │
                    │          │ Gi0/0              │
                    │          │ 10.0.12.1/30       │
                    │          │ 2001:DB8:12::1/64  │
                    │          │ (OSPFv2 + OSPFv3)  │
                    │          │                    │
                    │          │ 10.0.12.2/30       │
                    │          │ 2001:DB8:12::2/64  │
                    │          │ Gi0/0              │
                    │  ┌───────┴────────┐           │
                    │  │       R2       │           │
                    │  │ Enterprise Ed2 │           │
                    │  │ Lo0: 2.2.2.2   │           │
                    │  └─┬──────────────┘           │
                    └────┼──────────────────────────┘
                         │ Gi0/1
                         │ 10.0.23.1/30
                         │ 2001:DB8:23::1/64
                         │
              Gi0/1      │ 10.0.13.1/30
   10.0.13.2/30   ┌──────┴──────────────────┐
   2001:DB8:13::2/64 │                      │
              Gi0/0 │                       │ Gi0/1  10.0.23.2/30
                    ▼                       ▼        2001:DB8:23::2/64
              ┌────────────────────────────────┐
              │              R3                │
              │  ISP Router (AS 65002)         │
              │  Lo0: 3.3.3.3                  │
              └────────────┬───────────────────┘
                           │ Gi0/2
                           │ 10.0.34.1/30
                           │ 2001:DB8:34::1/64
                           │
                           │ 10.0.34.2/30
                           │ 2001:DB8:34::2/64
                           │ Gi0/0
                    ┌──────┴─────────┐
                    │      R4        │◄──PC2
                    │ Remote Branch  │
                    │   AS 65003     │
                    │ Lo0: 4.4.4.4   │
                    └────────────────┘
```

**AS design:**
- **AS 65001** (Enterprise): R1 and R2. Internal link R1<->R2 runs OSPFv2 + OSPFv3 + iBGP.
- **AS 65002** (ISP / Transit): R3 alone. Dual-homed eBGP to AS 65001 via R1 and R2. Single eBGP to AS 65003 via R4.
- **AS 65003** (Remote Branch): R4 alone. Single eBGP to R3.

**Advertised prefixes:**
- R1: `172.16.1.0/24` and `192.168.1.0/24` (+ v6 equivalents).
- R2: none (transit only within AS 65001).
- R3: `172.16.3.0/24` (+ v6 equivalent).
- R4: `172.16.4.0/24` and `192.168.2.0/24` (+ v6 equivalents).

**Your mission:** make AS 65001 prefer R1 as the primary exit for all external prefixes, with R2 as the backup. Apply MED at R3 so AS 65002 hints which entry point it prefers. Verify that PC1 (on R1) can reach PC2 (on R4) across three autonomous systems.

---

## 3. Hardware & Environment Specifications

**EVE-NG Topology:** `bgp/lab-02-best-path-selection.unl`

**Router Image:** vIOS (IOSv Layer 3) on R1, R2, R3, R4.

### Cabling

| Link | A-side | Z-side | Subnet (IPv4) | Subnet (IPv6) |
|------|--------|--------|---------------|----------------|
| L1 | R1 Gi0/0 | R2 Gi0/0 | 10.0.12.0/30 | 2001:DB8:12::/64 |
| L2 | R1 Gi0/1 | R3 Gi0/0 | 10.0.13.0/30 | 2001:DB8:13::/64 |
| L3 | R2 Gi0/1 | R3 Gi0/1 | 10.0.23.0/30 | 2001:DB8:23::/64 |
| L4 | R1 Gi0/2 | PC1 e0 | 192.168.1.0/24 | 2001:DB8:1:1::/64 |
| L5 | R3 Gi0/2 | R4 Gi0/0 | 10.0.34.0/30 | 2001:DB8:34::/64 |
| L6 | R4 Gi0/1 | PC2 e0 | 192.168.2.0/24 | 2001:DB8:2:2::/64 |

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

Run `python3 setup_lab.py --host <eve-ng-ip>` from this lab directory. This pushes `initial-configs/` to every active router (R1, R2, R3, R4). PC1 and PC2 load their `.vpc` files directly on boot.

### Pre-loaded on R1 and R2

- All interfaces from Lab 01: IP addressing (IPv4 + IPv6), loopbacks, OSPFv2 + OSPFv3 on the internal link.
- Full BGP 65001 configuration from Lab 01: iBGP to each other (Loopback-sourced, `next-hop-self`), eBGP to R3 (dual-stack, per-AF activation).
- R1 advertises `172.16.1.0/24`, `192.168.1.0/24`, and v6 equivalents.

### Pre-loaded on R3

- All interfaces from Lab 01 (IPv4 + IPv6, link-local FE80::3).
- **New:** Gi0/2 up with 10.0.34.1/30 and 2001:DB8:34::1/64 toward R4.
- BGP 65002 with eBGP to R1 and R2 only (v4+v6). The R4 peers are a student task.

### Pre-loaded on R4 (new device)

- All interfaces with IPv4 + IPv6 addresses.
- Loopback0 4.4.4.4/32 + 2001:DB8:FF::4/128.
- Loopback1 172.16.4.1/24 + 2001:DB8:172:4::1/64 (BGP-advertised prefix).
- **NOT pre-loaded:** any BGP configuration at all. Student configures BGP 65003 from scratch.

### NOT pre-loaded (your responsibility)

- BGP process on R4.
- eBGP peering R3 <-> R4 (v4 + v6).
- Advertisement of R4's `172.16.4.0/24`, `192.168.2.0/24`, and v6 equivalents.
- LOCAL_PREF policy on R1 and R2 to make R1 the primary exit.
- MED policy on R3 (different metric values toward R1 vs R2).

---

## 5. Lab Challenge: Core Implementation

### Task 1: Establish eBGP between R3 and R4 (dual-stack)

- On R4: bring up the BGP process in Autonomous System 65003.
- Use router-id 4.4.4.4.
- Configure eBGP to R3's IPv4 peering address (10.0.34.1) and R3's IPv6 peering address (2001:DB8:34::1).
- On R3: add matching eBGP neighbors for R4 (both address families). Remote AS is 65003.
- Activate each neighbor only under its matching address-family; deactivate the IPv4 neighbor under the IPv6 AF (and vice versa).

**Verification:** `show bgp ipv4 unicast summary` on R3 must show 10.0.34.2 with State/PfxRcd = 0 (no prefixes advertised yet) transitioning to a number once R4 advertises. `show bgp ipv6 unicast summary` must show 2001:DB8:34::2 Established.

---

### Task 2: Advertise R4's Networks

- On R4 under the IPv4 address-family: advertise 172.16.4.0/24 and 192.168.2.0/24 with network statements.
- On R4 under the IPv6 address-family: advertise 2001:DB8:172:4::/64 and 2001:DB8:2:2::/64 with network statements.

**Verification:**
- `show bgp ipv4 unicast` on R1 must list 172.16.4.0/24 and 192.168.2.0/24, with AS_PATH `65002 65003`.
- `show bgp ipv6 unicast` on R1 must list 2001:DB8:172:4::/64 and 2001:DB8:2:2::/64 with the same AS_PATH.

---

### Task 3: Observe Default Best Path Selection

- Without adding any attribute manipulation, examine which path R1 selects for 172.16.4.0/24.
- Note that R1 sees two paths: direct eBGP via 10.0.13.2 (R3), and via iBGP from R2 (which received it from R3 too).
- Identify which attribute in the best-path algorithm breaks the tie at this point (hint: steps 1-6 are all equal; the tie breaks on "eBGP over iBGP" or on AS_PATH length).

**Verification:** `show bgp ipv4 unicast 172.16.4.0` on R1 must show the selected path marked with `>`, and the other path without the `>` marker. The output explains the tie-breaker that was used.

---

### Task 4: Apply Weight to Override Path Selection on R1

- Create a prefix-list `R4_NETWORKS` that matches 172.16.4.0/24 and 192.168.2.0/24.
- Create a route-map `SET_WEIGHT` that matches that prefix-list and sets weight 500.
- Apply the route-map inbound on R1's eBGP peer (10.0.13.2).
- Soft-clear the session: `clear ip bgp 10.0.13.2 soft in`.

**Verification:** `show bgp ipv4 unicast 172.16.4.0` on R1 must show Weight 500 on the selected path. R2's view should be unaffected (Weight is router-local). **Remove this route-map before moving on** -- Weight is being demonstrated transiently, not kept in the final config.

---

### Task 5: Apply LOCAL_PREF for AS-Wide Exit Preference

- On R1: create a route-map `LOCAL_PREF_FROM_R3` that sets local-preference 200, and apply it inbound on the eBGP peer toward R3 (both address-families, with matching v6 prefix-list for the IPv6 AF).
- On R2: create a route-map with local-preference 150 and apply it inbound on its eBGP peer toward R3.
- Soft-clear both eBGP sessions inbound.

**Verification:**
- `show bgp ipv4 unicast 172.16.4.0` on R1 shows LocPrf 200 on the path via 10.0.13.2 (selected).
- `show bgp ipv4 unicast 172.16.4.0` on R2 shows TWO paths: the path via iBGP from R1 has LocPrf 200 (selected), and the path via its own eBGP neighbor 10.0.23.2 has LocPrf 150 (not selected). R2 has chosen to send traffic through R1.
- Repeat the same check in IPv6 AF.

---

### Task 6: Apply AS_PATH Prepending on R3 Toward R1

- On R3: create a route-map `PREPEND_TO_R1` that sets as-path prepend `65002 65002` (two extra hops), and apply it outbound on the eBGP peer 10.0.13.1.
- Soft-clear the session: `clear ip bgp 10.0.13.1 soft out`.
- Observe how this changes AS_PATH length on R1 for R3-originated and R4-originated prefixes.

**Verification:**
- `show bgp ipv4 unicast 172.16.3.0` on R1 shows AS_PATH `65002 65002 65002` (originally `65002`).
- Prepending alone does NOT override LOCAL_PREF (which is evaluated first). So this prepend is observable but does not move traffic. **Remove this route-map before the final solution check** -- it is being demonstrated transiently.

---

### Task 7: Apply MED on R3 Toward AS 65001

- On R3 (kept in the final solution): create two outbound route-maps -- `MED_TO_R1` setting metric 50, and `MED_TO_R2` setting metric 100.
- Apply `MED_TO_R1` outbound on neighbor 10.0.13.1; apply `MED_TO_R2` outbound on neighbor 10.0.23.1.
- Repeat for IPv6 address-family with matching v6 prefix-lists.
- Soft-clear both outbound sessions.

**Verification:** `show bgp ipv4 unicast 172.16.3.0` on R1 shows Metric 50. The same view on R2 (via iBGP) shows the R1-learned path with Metric 50 vs R2's own eBGP-learned path with Metric 100. Even so, LOCAL_PREF (step 2) wins before MED (step 6) is evaluated. MED only takes effect in cases where LOCAL_PREF is equal.

---

### Task 8: Verify End-to-End Reachability Across Three ASes

- From PC1 (192.168.1.10): `ping 192.168.2.10` and `ping6 2001:db8:2:2::10`.
- From PC2 (192.168.2.10): `ping 192.168.1.10`.
- Trace the path: `trace 192.168.2.10` on PC1 should show R1 -> R3 -> R4 (primary exit via R1 due to LOCAL_PREF 200).

**Verification:** both v4 and v6 ping must succeed with 5/5 reply rate. Traceroute from PC1 must transit R1 (192.168.1.1) then R3 (10.0.13.2) then R4 (10.0.34.2) then the PC2 interface.

---

## 6. Verification & Analysis

### After Task 1-2: Check eBGP R3<->R4

```bash
R3# show bgp ipv4 unicast summary | begin Neighbor
Neighbor        V           AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
10.0.13.1       4        65001      34      36       12    0    0 00:25:44        2
10.0.23.1       4        65001      33      35       12    0    0 00:25:44        2
10.0.34.2       4        65003      12      10       12    0    0 00:05:21        2   ! <- R4 Established, 2 prefixes received

R3# show bgp ipv6 unicast summary | begin Neighbor
Neighbor        V           AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
2001:DB8:13::1  4        65001      30      32       10    0    0 00:25:44        2
2001:DB8:23::1  4        65001      31      33       10    0    0 00:25:44        2
2001:DB8:34::2  4        65003      10       9       10    0    0 00:05:21        2   ! <- R4 IPv6 Established
```

### After Task 3 (default): Inspect Best Path on R1

```bash
R1# show bgp ipv4 unicast 172.16.4.0
BGP routing table entry for 172.16.4.0/24, version 6
Paths: (2 available, best #1, table default)
  Advertised to update-groups:
     2
  Refresh Epoch 2
  65002 65003
    10.0.13.2 from 10.0.13.2 (3.3.3.3)
      Origin IGP, metric 0, localpref 100, valid, external, best   ! ← default: eBGP > iBGP wins (step 7)
      rx pathid: 0, tx pathid: 0x0
  Refresh Epoch 2
  65002 65003
    2.2.2.2 (metric 2) from 2.2.2.2 (2.2.2.2)
      Origin IGP, metric 0, localpref 100, valid, internal         ! ← not selected: iBGP
      rx pathid: 0, tx pathid: 0
```

### After Task 4 (Weight): Inspect on R1 Only

```bash
R1# show bgp ipv4 unicast 172.16.4.0
BGP routing table entry for 172.16.4.0/24, version 8
Paths: (2 available, best #1, table default)
  65002 65003
    10.0.13.2 from 10.0.13.2 (3.3.3.3)
      Origin IGP, metric 0, localpref 100, weight 500, valid, external, best   ! ← Weight 500 wins step 1
```

Weight does NOT appear on R2's view of the same prefix -- confirm:

```bash
R2# show bgp ipv4 unicast 172.16.4.0
  ! ← weight 0 on both paths here; Weight never leaves R1
```

### After Task 5 (LOCAL_PREF): Both R1 and R2

```bash
R1# show bgp ipv4 unicast 172.16.4.0
  65002 65003
    10.0.13.2 from 10.0.13.2 (3.3.3.3)
      Origin IGP, metric 0, localpref 200, valid, external, best   ! ← LocPref 200 wins step 2

R2# show bgp ipv4 unicast 172.16.4.0
Paths: (2 available, best #1, table default)
  65002 65003
    1.1.1.1 (metric 2) from 1.1.1.1 (1.1.1.1)
      Origin IGP, metric 0, localpref 200, valid, internal, best   ! ← R2 now prefers R1 (via iBGP)
  65002 65003
    10.0.23.2 from 10.0.23.2 (3.3.3.3)
      Origin IGP, metric 0, localpref 150, valid, external         ! ← R2's own eBGP path loses
```

### After Task 7 (MED): Observable on R1 for R3's Loopback

```bash
R1# show bgp ipv4 unicast 172.16.3.0
  65002
    10.0.13.2 from 10.0.13.2 (3.3.3.3)
      Origin IGP, metric 50, localpref 200, valid, external, best   ! ← Metric 50 received from R3

R2# show bgp ipv4 unicast 172.16.3.0
  65002
    10.0.23.2 from 10.0.23.2 (3.3.3.3)
      Origin IGP, metric 100, localpref 150, valid, external        ! ← Metric 100 toward R2
  65002
    1.1.1.1 (metric 2) from 1.1.1.1 (1.1.1.1)
      Origin IGP, metric 50, localpref 200, valid, internal, best   ! ← wins on LocPref, not MED
```

### After Task 8: End-to-End

```bash
PC1> ping 192.168.2.10
84 bytes from 192.168.2.10 icmp_seq=1 ttl=61 time=12.3 ms    ! ← success; TTL=61 means 3 hops
84 bytes from 192.168.2.10 icmp_seq=2 ttl=61 time=11.8 ms

PC1> trace 192.168.2.10
trace to 192.168.2.10, 8 hops max, press Ctrl+C to stop
 1   192.168.1.1   ... ms                                      ! ← R1
 2   10.0.13.2     ... ms                                      ! ← R3 (primary exit via LocPref 200)
 3   10.0.34.2     ... ms                                      ! ← R4
 4   192.168.2.10  ... ms                                      ! ← PC2
```

---

## 7. Verification Cheatsheet

### BGP Best-Path Attribute Commands

```
route-map <NAME> permit <seq>
 match ip address prefix-list <LIST>
 set weight <0-65535>               ! Step 1 -- local to this router
 set local-preference <0-4294967295> ! Step 2 -- propagated via iBGP
 set as-path prepend <AS> [<AS> ...] ! Step 4 -- influences inbound (outbound route-map)
 set origin igp | incomplete         ! Step 5
 set metric <0-4294967295>           ! Step 6 (MED) -- influences neighboring AS
!
router bgp <AS>
 address-family ipv4
  neighbor <peer> route-map <NAME> in | out
```

| Command | Purpose |
|---------|---------|
| `set weight <N>` | Router-local override; highest wins |
| `set local-preference <N>` | AS-wide exit selector; highest wins; propagates via iBGP |
| `set as-path prepend <AS>...` | Inflates AS_PATH length (apply outbound toward peer AS you want to discourage) |
| `set metric <N>` | MED; lowest wins; compared only across same-AS paths |
| `set origin igp` | Marks origin as IGP (`i`); beats Incomplete (`?`) |

> **Exam tip:** Memorise the order: Weight -> LocPref -> AS_PATH -> MED -> eBGP-over-iBGP. Four out of five multi-attribute best-path questions on the exam test whether you know step 2 beats step 6.

### Route-Map Scaffolding (Inbound vs Outbound)

```
! INBOUND -- affects how MY router sees others' advertisements (Weight, LocPref):
neighbor <peer> route-map <NAME> in

! OUTBOUND -- affects how OTHERS see my advertisements (AS_PATH prepend, MED):
neighbor <peer> route-map <NAME> out
```

| Command | Purpose |
|---------|---------|
| `neighbor X route-map Y in` | Apply policy to routes RECEIVED from neighbor X |
| `neighbor X route-map Y out` | Apply policy to routes SENT to neighbor X |
| `clear ip bgp <peer> soft in` | Reapply inbound policy without resetting the session |
| `clear ip bgp <peer> soft out` | Reapply outbound policy (required after changing route-map out) |

> **Exam tip:** After ANY route-map change you must soft-clear the affected direction. A configuration-only change with no clear will not take effect.

### Verification Commands

| Command | What to Look For |
|---------|-----------------|
| `show bgp ipv4 unicast summary` | Established state; PfxRcd count per neighbor |
| `show bgp ipv4 unicast` | Table overview with `>` marking the selected best path |
| `show bgp ipv4 unicast <prefix>` | Detailed per-path view showing Weight, LocPref, MED, AS_PATH, Origin; marks `best` |
| `show bgp ipv6 unicast <prefix>` | Same detail for IPv6 AF |
| `show ip route bgp` | BGP-originated routes installed in the RIB |
| `show route-map <NAME>` | Policy hit counters to verify it's being applied |
| `show ip bgp neighbors <peer> policy` | Which route-maps are applied in/out on a peer |

### Common BGP Best-Path Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| Route-map configured but behavior unchanged | Forgot `clear ip bgp <peer> soft in|out` -- policy applies only to new updates |
| Weight 500 visible on R1 but R2 sees Weight 0 | Weight is never carried in BGP updates -- by design |
| LOCAL_PREF 200 set on R1 but R2 shows 100 | `next-hop-self` or iBGP session problem -- iBGP isn't delivering the attribute |
| MED set to 50 but neighbor AS still uses higher-MED path | `bgp always-compare-med` not configured (MED only compared across same-AS paths by default) |
| AS_PATH prepend visible but traffic path unchanged | LOCAL_PREF (step 2) already produced a winner; AS_PATH (step 4) never evaluated |
| `set origin igp` change has no effect | Paths differ at earlier steps -- Origin is step 5, rarely reached |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Task 1 + 2: R4 and R3 eBGP

<details>
<summary>Click to view R4 Configuration</summary>

```bash
! R4
router bgp 65003
 bgp router-id 4.4.4.4
 bgp log-neighbor-changes
 neighbor 10.0.34.1 remote-as 65002
 neighbor 10.0.34.1 description eBGP_TO_R3_AS65002
 neighbor 2001:DB8:34::1 remote-as 65002
 neighbor 2001:DB8:34::1 description eBGP_V6_TO_R3_AS65002
 !
 address-family ipv4
  network 172.16.4.0 mask 255.255.255.0
  network 192.168.2.0
  neighbor 10.0.34.1 activate
  no neighbor 2001:DB8:34::1 activate
 exit-address-family
 !
 address-family ipv6
  network 2001:DB8:172:4::/64
  network 2001:DB8:2:2::/64
  no neighbor 10.0.34.1 activate
  neighbor 2001:DB8:34::1 activate
 exit-address-family
```
</details>

<details>
<summary>Click to view R3 Additions (new R4 peer)</summary>

```bash
! R3
router bgp 65002
 neighbor 10.0.34.2 remote-as 65003
 neighbor 10.0.34.2 description eBGP_TO_R4_AS65003
 neighbor 2001:DB8:34::2 remote-as 65003
 neighbor 2001:DB8:34::2 description eBGP_V6_TO_R4_AS65003
 !
 address-family ipv4
  neighbor 10.0.34.2 activate
  no neighbor 2001:DB8:34::2 activate
 exit-address-family
 !
 address-family ipv6
  no neighbor 10.0.34.2 activate
  neighbor 2001:DB8:34::2 activate
 exit-address-family
```
</details>

### Task 5: LOCAL_PREF on R1 and R2

<details>
<summary>Click to view R1 LOCAL_PREF Configuration</summary>

```bash
! R1
ip prefix-list ALL_V4 seq 5 permit 0.0.0.0/0 le 32
!
ipv6 prefix-list ALL_V6 seq 5 permit ::/0 le 128
!
route-map LOCAL_PREF_FROM_R3 permit 10
 match ip address prefix-list ALL_V4
 set local-preference 200
!
route-map LOCAL_PREF_V6_FROM_R3 permit 10
 match ipv6 address prefix-list ALL_V6
 set local-preference 200
!
router bgp 65001
 address-family ipv4
  neighbor 10.0.13.2 route-map LOCAL_PREF_FROM_R3 in
 exit-address-family
 address-family ipv6
  neighbor 2001:DB8:13::2 route-map LOCAL_PREF_V6_FROM_R3 in
 exit-address-family
!
clear ip bgp 10.0.13.2 soft in
clear bgp ipv6 unicast 2001:DB8:13::2 soft in
```
</details>

<details>
<summary>Click to view R2 LOCAL_PREF Configuration</summary>

```bash
! R2
ip prefix-list ALL_V4 seq 5 permit 0.0.0.0/0 le 32
!
ipv6 prefix-list ALL_V6 seq 5 permit ::/0 le 128
!
route-map LOCAL_PREF_FROM_R3 permit 10
 match ip address prefix-list ALL_V4
 set local-preference 150
!
route-map LOCAL_PREF_V6_FROM_R3 permit 10
 match ipv6 address prefix-list ALL_V6
 set local-preference 150
!
router bgp 65001
 address-family ipv4
  neighbor 10.0.23.2 route-map LOCAL_PREF_FROM_R3 in
 exit-address-family
 address-family ipv6
  neighbor 2001:DB8:23::2 route-map LOCAL_PREF_V6_FROM_R3 in
 exit-address-family
!
clear ip bgp 10.0.23.2 soft in
clear bgp ipv6 unicast 2001:DB8:23::2 soft in
```
</details>

### Task 7: MED on R3

<details>
<summary>Click to view R3 MED Configuration</summary>

```bash
! R3
ip prefix-list ALL_V4 seq 5 permit 0.0.0.0/0 le 32
!
ipv6 prefix-list ALL_V6 seq 5 permit ::/0 le 128
!
route-map MED_TO_R1 permit 10
 match ip address prefix-list ALL_V4
 set metric 50
!
route-map MED_TO_R2 permit 10
 match ip address prefix-list ALL_V4
 set metric 100
!
route-map MED_V6_TO_R1 permit 10
 match ipv6 address prefix-list ALL_V6
 set metric 50
!
route-map MED_V6_TO_R2 permit 10
 match ipv6 address prefix-list ALL_V6
 set metric 100
!
router bgp 65002
 address-family ipv4
  neighbor 10.0.13.1 route-map MED_TO_R1 out
  neighbor 10.0.23.1 route-map MED_TO_R2 out
 exit-address-family
 address-family ipv6
  neighbor 2001:DB8:13::1 route-map MED_V6_TO_R1 out
  neighbor 2001:DB8:23::1 route-map MED_V6_TO_R2 out
 exit-address-family
!
clear ip bgp 10.0.13.1 soft out
clear ip bgp 10.0.23.1 soft out
clear bgp ipv6 unicast 2001:DB8:13::1 soft out
clear bgp ipv6 unicast 2001:DB8:23::1 soft out
```
</details>

<details>
<summary>Click to view Final Verification Commands</summary>

```bash
R1# show bgp ipv4 unicast summary
R1# show bgp ipv4 unicast 172.16.4.0
R1# show bgp ipv6 unicast 2001:DB8:172:4::/64

R2# show bgp ipv4 unicast 172.16.4.0     ! Confirm R2 picks iBGP path from R1 (LocPref 200)

R3# show bgp ipv4 unicast summary        ! All 3 peers Established with PfxRcd > 0

PC1> ping 192.168.2.10
PC1> trace 192.168.2.10
```
</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. Inject the fault first, then diagnose and fix using only show commands.

### Workflow

```bash
python3 setup_lab.py                                   # reset initial-configs
python3 scripts/fault-injection/apply_solution.py      # apply solution as known-good
python3 scripts/fault-injection/inject_scenario_01.py  # Ticket 1
python3 scripts/fault-injection/apply_solution.py      # restore
```

---

### Ticket 1 -- AS 65001 Exits Via Wrong Edge Router

Operations reports that outbound traffic from PC1 toward R4's networks is leaving AS 65001 through R2 instead of R1. Business policy requires R1 as the primary exit. The BGP sessions are all Established; pings succeed.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py`

**Success criteria:** `show bgp ipv4 unicast 172.16.4.0` on R1 shows LocPref 200 on the selected path. `show bgp ipv4 unicast 172.16.4.0` on R2 shows the iBGP-learned path from R1 as best (`>`). `traceroute 172.16.4.1 source 2.2.2.2` from R2 transits R1's loopback (1.1.1.1) as next-hop, confirming R2 exits via R1.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. On R1: `show bgp ipv4 unicast 172.16.4.0` -- observe LocPref is 100 (default) on R1's eBGP path. Expected 200.
2. `show route-map LOCAL_PREF_FROM_R3` -- the route-map exists but has zero hits in the latest counter.
3. `show ip bgp neighbors 10.0.13.2 policy` -- output shows NO inbound route-map applied.
4. `show running-config | section router bgp` -- confirm no `neighbor 10.0.13.2 route-map LOCAL_PREF_FROM_R3 in` line.

Root cause: the inbound route-map application was removed from neighbor 10.0.13.2 in R1's IPv4 address-family.
</details>

<details>
<summary>Click to view Fix</summary>

```bash
R1# configure terminal
R1(config)# router bgp 65001
R1(config-router)# address-family ipv4
R1(config-router-af)# neighbor 10.0.13.2 route-map LOCAL_PREF_FROM_R3 in
R1(config-router-af)# end
R1# clear ip bgp 10.0.13.2 soft in
R1# show bgp ipv4 unicast 172.16.4.0    ! Confirm localpref 200 on selected path
```
</details>

---

### Ticket 2 -- MED Appears on R1 But Not on R2's View

After applying the Task 7 MED policy, R1 correctly sees Metric 50 on R3's prefixes, but R2 sees Metric 0 (missing) on its own eBGP-learned path from R3. You expect Metric 100 on R2's direct eBGP receptions.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py`

**Success criteria:** On R2, `show bgp ipv4 unicast 172.16.3.0` path via 10.0.23.2 must show Metric 100.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. On R3: `show ip bgp neighbors 10.0.23.1 policy` -- observe that the outbound route-map is missing.
2. `show running-config | section router bgp` -- confirm only `neighbor 10.0.13.1 route-map MED_TO_R1 out` is present; the R2-facing one is absent.
3. Confirm the route-map itself exists: `show route-map MED_TO_R2` -- yes, it exists, just never applied.

Root cause: the outbound route-map application toward neighbor 10.0.23.1 was removed from R3. The route-map definition is intact, so the fix is a single command plus a soft-clear.
</details>

<details>
<summary>Click to view Fix</summary>

```bash
R3# configure terminal
R3(config)# router bgp 65002
R3(config-router)# address-family ipv4
R3(config-router-af)# neighbor 10.0.23.1 route-map MED_TO_R2 out
R3(config-router-af)# end
R3# clear ip bgp 10.0.23.1 soft out
R2# show bgp ipv4 unicast 172.16.3.0    ! Confirm metric 100 on path via 10.0.23.2
```
</details>

---

### Ticket 3 -- PC1 Cannot Reach 192.168.2.0/24 But Can Reach 172.16.4.0/24

PC1 can ping 172.16.4.1 (R4's loopback) but cannot ping 192.168.2.10 (PC2). The BGP session R3-R4 is Established; `show bgp` on R1 shows 172.16.4.0/24 but not 192.168.2.0/24.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py`

**Success criteria:** `show bgp ipv4 unicast 192.168.2.0` on R1 must return the prefix with AS_PATH `65002 65003`. PC1 ping to 192.168.2.10 must succeed.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. On R1: `show bgp ipv4 unicast 192.168.2.0` -- output: `% Network not in table`.
2. On R3: `show bgp ipv4 unicast 192.168.2.0` -- same "not in table" result, confirming R3 isn't receiving it from R4 either.
3. On R4: `show bgp ipv4 unicast 192.168.2.0` -- same "not in table" result.
4. On R4: `show ip route 192.168.2.0` -- the prefix exists in the RIB (directly connected via Gi0/1). So the interface is up, it's just not being injected into BGP.
5. `show running-config | section router bgp` on R4 -- confirm that the `network 192.168.2.0` statement is missing under address-family ipv4 (only 172.16.4.0 is advertised).

Root cause: the `network 192.168.2.0` statement was removed from R4's BGP IPv4 address-family. BGP only advertises what `network` statements inject (or what redistribution injects). A missing `network` statement is silent -- no error, just a missing prefix.
</details>

<details>
<summary>Click to view Fix</summary>

```bash
R4# configure terminal
R4(config)# router bgp 65003
R4(config-router)# address-family ipv4
R4(config-router-af)# network 192.168.2.0
R4(config-router-af)# end
R4# show bgp ipv4 unicast 192.168.2.0    ! Confirm prefix appears in local BGP table
```

Then on R1: `show bgp ipv4 unicast 192.168.2.0` -- the prefix should appear with AS_PATH `65002 65003`.
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] Task 1: eBGP R3<->R4 Established in both IPv4 and IPv6 address-families
- [ ] Task 2: R4 advertises 172.16.4.0/24, 192.168.2.0/24, 2001:DB8:172:4::/64, 2001:DB8:2:2::/64 and R1/R2 see all four
- [ ] Task 3: Identified why default best-path picked the eBGP path over iBGP (step 7 of algorithm)
- [ ] Task 4: Weight 500 applied on R1 -- confirmed visible on R1 only, not propagated to R2 (then removed)
- [ ] Task 5: LOCAL_PREF 200 on R1, 150 on R2, propagates via iBGP -- R2 picks R1's path
- [ ] Task 6: AS_PATH prepend on R3 toward R1 observable via longer AS_PATH (then removed)
- [ ] Task 7: MED 50 toward R1, MED 100 toward R2 -- visible on both IPv4 and IPv6 AFs
- [ ] Task 8: PC1 ping and trace to PC2 both succeed through R1 -> R3 -> R4

### Troubleshooting

- [ ] Ticket 1: Missing inbound route-map application on R1 diagnosed and fixed
- [ ] Ticket 2: Missing outbound route-map application on R3's R2-peer diagnosed and fixed
- [ ] Ticket 3: Missing `network 192.168.2.0` statement on R4 diagnosed and fixed
