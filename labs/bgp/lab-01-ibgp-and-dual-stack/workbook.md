# Lab 01 -- iBGP, Dual-Homing, and Dual-Stack

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

**Exam Objective:** 350-401 blueprint bullet **3.2.c** -- Configure and verify eBGP
between directly connected neighbors (best path selection algorithm and neighbor
relationships). This lab extends the primitive eBGP from lab-00 with iBGP,
dual-homing, and IPv6 dual-stack.

R2 joins the enterprise in this lab. R1 and R2 form AS 65001 together; both peer
eBGP with R3 (AS 65002). R1 and R2 also peer **iBGP** with each other so BGP
prefixes learned from R3 flow between the two enterprise edges. Once IPv4 is
working, the entire topology is extended to **IPv6 dual-stack** -- every router
runs BGP IPv4 and IPv6 address families side-by-side.

### iBGP -- Why It Exists, Why It's Different

Inside one AS, routers still need to share BGP prefixes. If R2 learns a route from
AS 65002 and R1 doesn't hear about it, R1's routing decisions toward AS 65002 are
incomplete. **iBGP** solves this by defining BGP sessions between routers within
the same AS.

But iBGP plays by different rules than eBGP:

| Behavior | eBGP | iBGP |
|---|---|---|
| AS of the peer | Different | Same |
| Default TTL | 1 | 255 |
| Peering target | Directly connected IP | **Loopback (via IGP)** |
| AS_Path modification | Prepends local AS | Does not modify |
| `next-hop` rewrite on outbound | **Yes** (rewrites to self) | **No** (preserves) |
| Re-advertisement to other iBGP peers | Yes, once per prefix | **No** -- split horizon |

Two behaviors stand out:

1. **Next-hop preservation.** When R2 receives a prefix from eBGP peer R3 and
   passes it to iBGP peer R1, the next-hop R1 sees is *R3's peering IP* --
   **unchanged**. If R1 has no IGP route to that IP, the iBGP route is
   **inaccessible** and will not be installed in the RIB.
2. **iBGP split horizon.** A route learned from an iBGP peer is **never**
   re-advertised to another iBGP peer. This prevents loops but means that in
   ASes with N routers, every router needs a **full mesh** of iBGP sessions
   (N*(N-1)/2 sessions), or a **route reflector** to break the rule. In lab-01
   we have just two routers, so a single iBGP session is a full mesh.

### `next-hop-self` -- The Fix You Always Need

Because iBGP preserves next-hop, the classic lab/exam gotcha is:

```
R3 (AS 65002) --eBGP--> R2 --iBGP--> R1
                next-hop
                 = R3's
                interface IP
                (reachable
                 by R2 only)
```

R1 receives the prefix with next-hop pointing to R3's address on the R2-R3 link.
R1 does not know how to reach that address (the link is not in OSPF -- it's in
another AS). Result: the prefix lands in R1's BGP table as **inaccessible** and
does not install into the RIB.

The fix is to tell R2 to rewrite the next-hop to itself when sending to R1:

```
R2(config-router-af)# neighbor 1.1.1.1 next-hop-self
```

Now R2 tells R1: "for this prefix, the next-hop is **me**." R1 reaches R2 via
the OSPF-learned Loopback0 route, so the BGP prefix is valid and installs.

> **Exam tip:** `next-hop-self` is required on **every iBGP-outbound direction**
> where the original next-hop would be unreachable by the iBGP peer. In this lab
> both R1 and R2 learn eBGP prefixes from R3, so BOTH must set `next-hop-self`
> toward each other.

### Why Peer iBGP on Loopback

iBGP sessions classically peer on Loopback0 addresses, not physical-interface
addresses. Two benefits:

1. **Resilience.** A physical-interface-based session goes down the moment that
   interface fails. A Loopback-based session stays up as long as the IGP has
   **any** path between the two routers.
2. **Redundant paths.** If R1 and R2 were connected by two physical links, a
   Loopback peering uses whichever link the IGP currently prefers, and fails
   over automatically if one link dies.

Loopback peering requires the IGP to advertise each router's Loopback0 -- which
is why **OSPF is pre-configured** on the R1-R2 internal link in this lab.
`neighbor X update-source Loopback0` tells BGP to source its own TCP/179 packets
from the Loopback0 IP (otherwise they leave with the outgoing interface's IP
and the far side rejects them).

### BGP Address Families -- One Process, Multiple Protocols

Modern BGP uses **multi-protocol BGP (MP-BGP)** to carry prefixes for many
address families -- IPv4 unicast, IPv6 unicast, VPNv4, EVPN, and more -- over
the **same TCP session**. A single `router bgp 65001` process can run IPv4 and
IPv6 in parallel:

```
router bgp 65001
 neighbor 2.2.2.2 remote-as 65001              ! session definition (shared)
 neighbor 2.2.2.2 update-source Loopback0
 neighbor 2001:DB8:FF::2 remote-as 65001       ! separate IPv6 session
 neighbor 2001:DB8:FF::2 update-source Loopback0
 !
 address-family ipv4
  neighbor 2.2.2.2 activate                    ! explicit per-AF activation
  neighbor 2.2.2.2 next-hop-self
 !
 address-family ipv6
  neighbor 2001:DB8:FF::2 activate
  neighbor 2001:DB8:FF::2 next-hop-self
```

The critical rule: **every neighbor must be explicitly activated in each address
family it participates in**. By default Cisco IOS auto-activates new neighbors in
the IPv4 AF, which is why IPv6-only peers need `no neighbor X activate` under
IPv4 to avoid confusion. The opposite is also true: IPv6 neighbors are NOT
auto-activated in the IPv6 AF and must be explicitly enabled.

### OSPFv3 for IPv6 iBGP Next-Hop

For the iBGP-IPv6 session to work over Loopback0, R1 and R2 need IPv6 reachability
to each other's Loopback0 /128. Just as OSPFv2 provides that for IPv4, **OSPFv3**
provides it for IPv6. OSPFv3 runs a separate process (`ipv6 router ospf 1`) and
enables per-interface (`ipv6 ospf 1 area 0`) rather than using `network`
statements.

### Skills this lab develops

| Skill | Description |
|---|---|
| iBGP peering over Loopback | Configure `neighbor` + `update-source Loopback0` with an IGP-reachable loopback |
| `next-hop-self` on iBGP | Rewrite next-hop on outbound iBGP to make eBGP-learned prefixes resolvable |
| Dual-homed eBGP | Establish two independent eBGP sessions from the same AS to the same peer AS |
| IPv6 interface addressing | Assign link-local + global IPv6 addresses; enable `ipv6 unicast-routing` |
| OSPFv3 | Run IPv6 IGP for loopback reachability in parallel with OSPFv2 |
| BGP IPv6 address family | Activate neighbors in the IPv6 AF; advertise IPv6 prefixes with `network` |
| Dual-stack verification | Read IPv4 and IPv6 BGP tables side-by-side |
| IPv6 end-to-end reachability | Validate traffic flow across an AS boundary using IPv6 prefixes |

---

## 2. Topology & Scenario

**Scenario:** Following the successful lab-00 single-homed deployment, the
enterprise has provisioned a second edge router (R2) and a second transit link
to the ISP. You must bring R2 into AS 65001, establish iBGP between R1 and R2
so they share the same view of external prefixes, and then add IPv6 dual-stack
so the enterprise can support both protocols end-to-end.

```
                    ┌──── AS 65001 (Enterprise) ────┐
                    │                                │
         ┌──────────────────┐    iBGP    ┌──────────────────┐
         │        R1        │◄──────────►│        R2        │
         │  Lo0: 1.1.1.1    │   (Lo0)    │  Lo0: 2.2.2.2    │
         │ Lo1: 172.16.1.1  │   OSPF     │                  │
         └──┬───────────┬───┘ (preconfig)└────────┬─────────┘
     Gi0/2 │       Gi0/1│  10.0.12.0/30     Gi0/1 │
 192.168.1.1      10.0.13.1/30                    │ 10.0.23.1/30
            │           │                         │
         ┌──┴───┐       │     eBGP (IPv4+IPv6)    │
         │ PC1  │       │  AS 65001 ↔ AS 65002    │
         │ .10  │       │                         │
         └──────┘    10.0.13.2/30           10.0.23.2/30
                        │ Gi0/0                   │ Gi0/1
                        └────────────┬────────────┘
                                     │
                          ┌──────────┴──────────┐
                          │         R3          │
                          │  ISP -- AS 65002    │
                          │   Lo0: 3.3.3.3      │
                          │  Lo1: 172.16.3.1    │
                          └─────────────────────┘
```

### Why dual-homed?

With one path (lab-00), a single link failure blackholes the enterprise. With
two eBGP sessions to the same ISP, BGP advertises both paths into the
enterprise; if one link fails, the other takes over on the next best-path
evaluation. R3 also has two paths *back* to the enterprise, which is what lab-02
exploits for best-path manipulation.

### IPv6 on top

Every segment in the topology gets parallel IPv6 addressing. BGP runs both
IPv4 and IPv6 address families, **sharing the same neighbor state machine per
peer** but with separate prefix tables and separate activation flags. A student
who understands dual-stack BGP here can run any address family (VPNv4, L2VPN,
EVPN) tomorrow -- the activation pattern is identical.

---

## 3. Hardware & Environment Specifications

### Devices

| Device | Platform | Role |
|---|---|---|
| R1 | IOSv (15.x+) | Enterprise Edge 1 (AS 65001) |
| R2 | IOSv (15.x+) | Enterprise Edge 2 (AS 65001) -- **new in lab-01** |
| R3 | IOSv (15.x+) | ISP (AS 65002) |
| PC1 | VPCS | End host on R1's LAN (192.168.1.10/24 + 2001:DB8:1:1::10/64) |

### Cabling

| Link | Endpoint A | Endpoint B | IPv4 Subnet | IPv6 Subnet |
|---|---|---|---|---|
| L1 | R1 Gi0/0 | R2 Gi0/0 | 10.0.12.0/30 | 2001:DB8:12::/64 |
| L2 | R1 Gi0/1 | R3 Gi0/0 | 10.0.13.0/30 | 2001:DB8:13::/64 |
| L3 | R2 Gi0/1 | R3 Gi0/1 | 10.0.23.0/30 | 2001:DB8:23::/64 |
| L4 | R1 Gi0/2 | PC1 e0 | 192.168.1.0/24 | 2001:DB8:1:1::/64 |

### Console Access Table

| Device | Port | Connection Command |
|---|---|---|
| R1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R3 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| PC1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |

---

## 4. Base Configuration

Push with:

```bash
python3 setup_lab.py --host <eve-ng-ip>
```

### What IS pre-loaded (inherited from lab-00 + new for lab-01)

- All IPv4 addressing including the new R1-R2 and R2-R3 segments
- OSPFv2 process 1 between R1 and R2 (for iBGP Loopback next-hop reachability)
  -- `passive-interface default` with the internal link explicitly un-passive
- R1-R3 eBGP session from lab-00 (IPv4 only, still up)
- R3 already advertises 172.16.3.0/24 into IPv4 BGP
- R1 already advertises 172.16.1.0/24 and 192.168.1.0/24 into IPv4 BGP
- R2 has all physical + loopback IPv4 addressing but NO BGP process yet

### What is NOT pre-loaded (you will configure in Section 5)

- iBGP session between R1 and R2 (IPv4)
- Second eBGP session between R2 and R3 (IPv4)
- `next-hop-self` on iBGP peers
- `ipv6 unicast-routing` and all IPv6 interface addressing
- OSPFv3 between R1 and R2 on the internal link
- BGP IPv6 address family -- activations, neighbors, network advertisements

Verify starting state before Section 5:

```bash
R1# show ip ospf neighbor           ! R2 (2.2.2.2) must appear, state FULL
R1# show ip bgp summary              ! neighbor 10.0.13.2, State = numeric (Established)
R1# show ip bgp                      ! 172.16.1.0/24, 172.16.3.0/24, 192.168.1.0
R2# show ip bgp summary              ! local AS 65001, NO neighbors yet
```

---

## 5. Lab Challenge: Core Implementation

### Task 1: Verify the pre-configured OSPF foundation

- On R1, confirm the OSPF adjacency to R2 is in the FULL state.
- Confirm R1 has learned `2.2.2.2/32` (R2's Loopback0) via OSPF.
- Confirm R2 similarly learned `1.1.1.1/32`.

This IGP foundation is what makes Loopback-to-Loopback iBGP peering possible.

**Verification:** `show ip ospf neighbor` on both R1 and R2 must show the
other's router-ID with Neighbor State = FULL. `show ip route ospf` must include
the remote Loopback0 /32.

---

### Task 2: Configure iBGP between R1 and R2 over Loopback0

- On R1, define R2 (router-ID 2.2.2.2) as an iBGP peer (remote-as 65001) and
  source TCP packets from Loopback0.
- On R2, define R1 (router-ID 1.1.1.1) symmetrically.
- Under the IPv4 address family on both routers, **activate** the iBGP peer and
  configure `next-hop-self` so eBGP-learned prefixes become resolvable across
  the iBGP session.
- Explicitly set the BGP router-ID on R2 to 2.2.2.2.

> Without `next-hop-self`, the prefix 172.16.3.0/24 that R2 learns from R3 will
> arrive at R1 with next-hop 10.0.23.2, which R1 cannot reach (it is not in
> OSPF). The prefix will appear in R1's BGP table marked
> `(inaccessible, no route)` and will NOT install into the RIB.

**Verification:** `show ip bgp summary` on R1 must show neighbor `2.2.2.2` with
State/PfxRcd numeric (Established). `show ip bgp` on R1 must list the prefixes
R2 originates, and after Task 3 the prefixes R2 learned from R3.

---

### Task 3: Establish the second eBGP session between R2 and R3

- On R2, define R3 (10.0.23.2) as an eBGP peer (remote-as 65002) and describe
  the neighbor.
- On R3, define R2 (10.0.23.1) as an eBGP peer (remote-as 65001) and describe
  the neighbor.
- Activate the peer on both sides under the IPv4 address family.

**Verification:** `show ip bgp summary` on R3 must show **two** Established
neighbors -- 10.0.13.1 (R1) and 10.0.23.1 (R2). `show ip bgp 172.16.3.0` on R1
must now show **two paths** -- one via R2 (iBGP) and one via 10.0.13.2 (eBGP to
R3 directly). The eBGP path wins (lower AD).

---

### Task 4: Add IPv6 addressing everywhere

- Enable `ipv6 unicast-routing` globally on R1, R2, and R3.
- On every router interface that already has an IPv4 address in the topology,
  add the matching IPv6 address per the baseline plan:
  - R1 Gi0/0 <-> R2 Gi0/0: `2001:DB8:12::1/64` + `2001:DB8:12::2/64`
  - R1 Gi0/1 <-> R3 Gi0/0: `2001:DB8:13::1/64` + `2001:DB8:13::2/64`
  - R2 Gi0/1 <-> R3 Gi0/1: `2001:DB8:23::1/64` + `2001:DB8:23::2/64`
  - R1 Gi0/2 <-> PC1:      `2001:DB8:1:1::1/64`
  - Loopback0 /128: `2001:DB8:FF::1`, `2001:DB8:FF::2`, `2001:DB8:FF::3`
  - Loopback1 /64: `2001:DB8:172:1::1/64` on R1, `2001:DB8:172:3::1/64` on R3
- On each link, also configure a deterministic link-local address using the
  lab's convention: `FE80::<router-number>` (e.g., `FE80::1 link-local` on R1).
- On PC1, add the IPv6 address `2001:DB8:1:1::10/64` with gateway
  `2001:DB8:1:1::1`.

**Verification:** `show ipv6 interface brief` on each router must show every
active interface with its link-local and global IPv6 address. Pings between
directly connected IPv6 addresses on each segment must succeed. PC1 must be
able to ping `2001:DB8:1:1::1`.

---

### Task 5: Enable OSPFv3 on the R1-R2 internal link

- On R1 and R2, start `ipv6 router ospf 1` and set the router-ID to match the
  OSPFv2 router-ID (1.1.1.1 on R1, 2.2.2.2 on R2).
- On Gi0/0 (R1-R2 internal) and on Loopback0 on **both** routers, enable
  `ipv6 ospf 1 area 0`.
- Do NOT enable OSPFv3 on the R1-R3 link or the R2-R3 link -- those are in
  AS 65002 and must not share IGP routes with the ISP.

**Verification:** `show ipv6 ospf neighbor` on both R1 and R2 must show the peer
with state FULL. `show ipv6 route ospf` on R1 must show `2001:DB8:FF::2/128`;
on R2 it must show `2001:DB8:FF::1/128`.

---

### Task 6: Configure the BGP IPv6 address family

- On R1, R2, and R3, define a separate IPv6 neighbor for each BGP session
  already configured in IPv4 (iBGP uses Loopback0 IPv6; eBGP uses the peer's
  link IPv6 address).
- Inside `address-family ipv6` on each router:
  - `activate` every IPv6 neighbor
  - Apply `next-hop-self` on iBGP-IPv6 peers (same reasoning as IPv4)
  - Advertise the local IPv6 prefix(es) with a `network <prefix>/prefixlen`
    statement: R1 -> `2001:DB8:172:1::/64` and `2001:DB8:1:1::/64`,
    R3 -> `2001:DB8:172:3::/64`
- Inside `address-family ipv4`, explicitly `no neighbor <ipv6-addr> activate`
  and inside `address-family ipv6`, explicitly `no neighbor <ipv4-addr>
  activate` so each peer stays confined to the AF it belongs in. (IOS
  auto-activates new neighbors in the IPv4 AF -- undo that for IPv6-only peers.)

**Verification:** `show bgp ipv6 unicast summary` on R1 must show the iBGP
neighbor `2001:DB8:FF::2` and the eBGP neighbor `2001:DB8:13::2` both with
State/PfxRcd numeric. `show bgp ipv6 unicast` must list all IPv6 prefixes
(R1's, R2's, R3's).

---

### Task 7: Verify dual-stack end-to-end reachability

- From PC1, ping R3's advertised IPv4 loopback (`172.16.3.1`) -- must succeed.
- From PC1, ping R3's advertised IPv6 loopback (`2001:DB8:172:3::1`) -- must
  succeed.
- From R3, ping R1's Loopback1 source Loopback1:
  - IPv4: `ping 172.16.1.1 source Loopback1`
  - IPv6: `ping 2001:DB8:172:1::1 source Loopback1`
- From R3, traceroute `172.16.1.1` and confirm the path uses an AD-20 eBGP
  next-hop (either 10.0.13.1 or 10.0.23.1, whichever wins best-path).

**Verification:** All four probes succeed. Traceroute shows a single routed
hop to the enterprise.

---

## 6. Verification & Analysis

### 6a -- OSPF adjacency (Task 1)

```
R1# show ip ospf neighbor
Neighbor ID     Pri   State           Dead Time   Address         Interface
2.2.2.2           1   FULL/BDR        00:00:36    10.0.12.2       GigabitEthernet0/0    ! <-- must be FULL

R1# show ip route ospf | include 2.2.2.2
O        2.2.2.2 [110/2] via 10.0.12.2, 00:05:12, GigabitEthernet0/0          ! <-- Lo0 of R2 via OSPF
```

### 6b -- iBGP session and next-hop-self (Tasks 2-3)

```
R1# show ip bgp summary
BGP router identifier 1.1.1.1, local AS number 65001
...
Neighbor        V   AS MsgRcvd MsgSent  TblVer InQ OutQ Up/Down State/PfxRcd
2.2.2.2         4 65001     25      22      12   0    0 00:03:14            2    ! <-- iBGP peer, Established
10.0.13.2       4 65002     28      26      12   0    0 00:08:22            1    ! <-- eBGP peer from lab-00

R1# show ip bgp 172.16.3.0/24
BGP routing table entry for 172.16.3.0/24, version 10
Paths: (2 available, best #2, table default)
  Advertised to update-groups:
     3
  65002
    10.0.23.2 (metric 3) from 2.2.2.2 (2.2.2.2)                                ! <-- iBGP path via R2
      Origin IGP, metric 0, localpref 100, valid, internal
      rx pathid: 0, tx pathid: 0
  65002
    10.0.13.2 from 10.0.13.2 (3.3.3.3)                                         ! <-- eBGP direct path
      Origin IGP, metric 0, localpref 100, valid, external, best              ! <-- eBGP wins (AD 20 < 200)
```

> If the iBGP path had shown `(inaccessible)` after next-hop, `next-hop-self`
> is missing on R2. The iBGP path's next-hop appears as **10.0.23.2 with metric
> 3** -- which is R2's rewrite (its Loopback0 + OSPF cost to R2). Without
> `next-hop-self`, it would show **10.0.23.2 (inaccessible)**.

### 6c -- R3's view of dual-homed enterprise (Task 3)

```
R3# show ip bgp
     Network          Next Hop            Metric LocPrf Weight Path
 *>  172.16.1.0/24    10.0.13.1                0             0 65001 i      ! <-- via R1 direct
 *   172.16.1.0/24    10.0.23.1                0             0 65001 i      ! <-- via R2
 *>  172.16.3.0/24    0.0.0.0                  0         32768 i
 *>  192.168.1.0      10.0.13.1                0             0 65001 i      ! <-- via R1
 *   192.168.1.0      10.0.23.1                0             0 65001 i      ! <-- via R2
```

Two asterisks (two valid paths) with `>` on one -- R3 chose the shorter
router-ID next-hop per the default BGP tie-breaker.

### 6d -- IPv6 interfaces and OSPFv3 (Tasks 4-5)

```
R1# show ipv6 interface brief
Lo0                    [up/up]
    FE80::1
    2001:DB8:FF::1
Lo1                    [up/up]
    FE80::1
    2001:DB8:172:1::1
Gi0/0                  [up/up]
    FE80::1
    2001:DB8:12::1
Gi0/1                  [up/up]
    FE80::1
    2001:DB8:13::1
Gi0/2                  [up/up]
    FE80::1
    2001:DB8:1:1::1

R1# show ipv6 ospf neighbor
Neighbor ID     Pri   State           Dead Time   Interface ID    Interface
2.2.2.2           1   FULL/DR         00:00:36    4               GigabitEthernet0/0  ! <-- FULL for IPv6

R1# show ipv6 route ospf | include 2001:DB8:FF::2
OI   2001:DB8:FF::2/128 [110/1]                                                        ! <-- R2 Lo0 via OSPFv3
     via FE80::2, GigabitEthernet0/0
```

### 6e -- BGP IPv6 summary and table (Task 6)

```
R1# show bgp ipv6 unicast summary
BGP router identifier 1.1.1.1, local AS number 65001
...
Neighbor                V   AS MsgRcvd MsgSent  TblVer InQ OutQ Up/Down State/PfxRcd
2001:DB8:13::2          4 65002     12      14       6   0    0 00:02:12            1   ! <-- eBGP v6
2001:DB8:FF::2          4 65001     10      12       6   0    0 00:01:55            2   ! <-- iBGP v6

R1# show bgp ipv6 unicast
BGP table version is 6, local router ID is 1.1.1.1
...
     Network          Next Hop            Metric LocPrf Weight Path
 *>  2001:DB8:1:1::/64
                       ::                       0         32768 i               ! <-- local
 *>i 2001:DB8:172:3::/64
                       2001:DB8:23::2           0    100      0 65002 i         ! <-- iBGP from R2
 *                     2001:DB8:13::2           0             0 65002 i         ! <-- eBGP from R3
 *>  2001:DB8:172:1::/64
                       ::                       0         32768 i               ! <-- local
```

### 6f -- End-to-end dual-stack reachability (Task 7)

```
PC1> ping 172.16.3.1
84 bytes from 172.16.3.1 icmp_seq=1 ttl=253 time=3.451 ms                      ! <-- IPv4 works

PC1> ping 2001:db8:172:3::1
84 bytes from 2001:db8:172:3::1 icmp_seq=1 ttl=253 time=3.721 ms               ! <-- IPv6 works

R1# traceroute 172.16.3.1
  1 10.0.13.2 4 msec 4 msec 4 msec                                             ! <-- direct eBGP to R3
```

---

## 7. Verification Cheatsheet

### iBGP over Loopback with next-hop-self

```
router bgp <local-asn>
 neighbor <peer-loopback> remote-as <same-asn>
 neighbor <peer-loopback> update-source Loopback0
 address-family ipv4
  neighbor <peer-loopback> activate
  neighbor <peer-loopback> next-hop-self
```

| Command | Purpose |
|---|---|
| `neighbor 2.2.2.2 remote-as 65001` | Define iBGP peer (same AS = iBGP) |
| `neighbor 2.2.2.2 update-source Loopback0` | Source TCP/179 from Loopback0 IP |
| `neighbor 2.2.2.2 next-hop-self` | Rewrite eBGP-learned next-hop to this router's IP before sending to iBGP peer |
| `bgp router-id <ip>` | Set explicit router-ID (crucial when multiple loopbacks exist) |

> **Exam tip:** Loopback-based iBGP requires three things: **(1)** the remote
> Loopback reachable via IGP, **(2)** `update-source Loopback0` so outgoing TCP
> uses the loopback IP (matches the far side's `neighbor` statement), and
> **(3)** `next-hop-self` so eBGP-learned prefixes resolve.

### BGP IPv6 address family

```
router bgp <asn>
 neighbor <peer-v6> remote-as <asn>
 neighbor <peer-v6> update-source Loopback0
 !
 address-family ipv4
  no neighbor <peer-v6> activate
 !
 address-family ipv6
  neighbor <peer-v6> activate
  neighbor <peer-v6> next-hop-self
  network <prefix>/<len>
```

| Command | Purpose |
|---|---|
| `address-family ipv6` | Enter IPv6 AF configuration mode |
| `neighbor 2001:DB8:FF::2 activate` | Enable this neighbor to exchange IPv6 prefixes |
| `no neighbor 10.0.13.2 activate` (under ipv6) | Prevent IPv4-only peer from accidentally exchanging IPv6 |
| `network 2001:DB8:172:1::/64` | Advertise the IPv6 prefix if the matching route is in the RIB |

> **Exam tip:** IOS by default **auto-activates every neighbor in IPv4 unicast**.
> A v6-only neighbor needs `no neighbor X activate` in IPv4 to prevent
> misconfiguration, and needs explicit `activate` in IPv6.

### OSPFv3 (IPv6) enablement

```
ipv6 router ospf <pid>
 router-id <ip>
!
interface <iface>
 ipv6 ospf <pid> area <area-id>
```

| Command | Purpose |
|---|---|
| `ipv6 router ospf 1` | Create OSPFv3 process |
| `router-id 1.1.1.1` | IPv4-formatted router-ID (REQUIRED if no IPv4 on the box) |
| `ipv6 ospf 1 area 0` | Enable OSPFv3 on this specific interface in area 0 |

### Verification Commands

| Command | What to Look For |
|---|---|
| `show ip bgp summary` | IPv4 peers; Established (numeric) state; prefix counts |
| `show bgp ipv6 unicast summary` | IPv6 peers; Established state; separate prefix counts |
| `show ip bgp <prefix>` | Full path attributes for IPv4 prefix; next-hop accessibility |
| `show bgp ipv6 unicast <prefix>` | Same for IPv6 |
| `show ip ospf neighbor` / `show ipv6 ospf neighbor` | IGP adjacency state for loopback reachability |
| `show ip route <peer-loopback>` | IGP must know how to reach the iBGP peer's loopback |
| `show bgp ipv6 unicast neighbors <peer-v6>` | Detailed IPv6 session state |
| `show ip bgp neighbors <peer-ip> advertised-routes` | What we send out (per peer) |
| `debug bgp update` | Update message trace -- only when absolutely necessary |

### BGP Default Values Worth Memorizing

| Attribute | Default |
|---|---|
| eBGP AD | 20 |
| iBGP AD | 200 |
| BGP TCP port | 179 |
| Keepalive | 60 seconds |
| Hold-down | 180 seconds |
| Connect retry | 120 seconds |
| Weight (local-originated) | 32768 |
| Weight (learned from peer) | 0 |
| Local preference | 100 |
| MED | 0 |

### Common Dual-Stack / iBGP Failure Causes

| Symptom | Likely Cause |
|---|---|
| iBGP peer cycles Idle/Active | Peer's Loopback not reachable via IGP |
| iBGP peer Established but 0 prefixes received | IPv4-only neighbor but expected IPv6, or peer hasn't `activate`d |
| iBGP prefix in table marked `(inaccessible, no route)` | `next-hop-self` missing on the sending iBGP side |
| IPv6 BGP session never comes up | Peer IPv6 address unreachable; OSPFv3 not running; no `update-source` |
| IPv6 neighbor Established but no prefixes | Neighbor not `activate`d under `address-family ipv6`, OR `network` statement missing |
| OSPFv3 adjacency never reaches FULL | Missing IPv4-formatted router-ID, or `ipv6 ospf ... area` missing on the interface |
| eBGP session up, iBGP up, but path not preferred as expected | `next-hop-self` may be masking metric comparison -- lab-02 territory |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these configs first!

### Objective 1: iBGP + dual-homed eBGP + dual-stack full config

<details>
<summary>Click to view R1 Configuration (iBGP + eBGP + IPv6)</summary>

```bash
! R1
ipv6 unicast-routing
!
interface Loopback0
 ipv6 address 2001:DB8:FF::1/128
 ipv6 ospf 1 area 0
!
interface Loopback1
 ipv6 address 2001:DB8:172:1::1/64
!
interface GigabitEthernet0/0
 ipv6 address FE80::1 link-local
 ipv6 address 2001:DB8:12::1/64
 ipv6 ospf 1 area 0
!
interface GigabitEthernet0/1
 ipv6 address FE80::1 link-local
 ipv6 address 2001:DB8:13::1/64
!
interface GigabitEthernet0/2
 ipv6 address FE80::1 link-local
 ipv6 address 2001:DB8:1:1::1/64
!
ipv6 router ospf 1
 router-id 1.1.1.1
 passive-interface default
 no passive-interface GigabitEthernet0/0
!
router bgp 65001
 neighbor 2.2.2.2 remote-as 65001
 neighbor 2.2.2.2 description iBGP_TO_R2
 neighbor 2.2.2.2 update-source Loopback0
 neighbor 2001:DB8:13::2 remote-as 65002
 neighbor 2001:DB8:13::2 description eBGP_V6_TO_R3
 neighbor 2001:DB8:FF::2 remote-as 65001
 neighbor 2001:DB8:FF::2 description iBGP_V6_TO_R2
 neighbor 2001:DB8:FF::2 update-source Loopback0
 !
 address-family ipv4
  neighbor 2.2.2.2 activate
  neighbor 2.2.2.2 next-hop-self
  no neighbor 2001:DB8:13::2 activate
  no neighbor 2001:DB8:FF::2 activate
 exit-address-family
 !
 address-family ipv6
  network 2001:DB8:172:1::/64
  network 2001:DB8:1:1::/64
  neighbor 2001:DB8:13::2 activate
  neighbor 2001:DB8:FF::2 activate
  neighbor 2001:DB8:FF::2 next-hop-self
 exit-address-family
```
</details>

<details>
<summary>Click to view R2 Configuration (iBGP + eBGP + IPv6)</summary>

```bash
! R2
ipv6 unicast-routing
!
interface Loopback0
 ipv6 address 2001:DB8:FF::2/128
 ipv6 ospf 1 area 0
!
interface GigabitEthernet0/0
 ipv6 address FE80::2 link-local
 ipv6 address 2001:DB8:12::2/64
 ipv6 ospf 1 area 0
!
interface GigabitEthernet0/1
 ipv6 address FE80::2 link-local
 ipv6 address 2001:DB8:23::1/64
!
ipv6 router ospf 1
 router-id 2.2.2.2
 passive-interface default
 no passive-interface GigabitEthernet0/0
!
router bgp 65001
 bgp router-id 2.2.2.2
 bgp log-neighbor-changes
 neighbor 1.1.1.1 remote-as 65001
 neighbor 1.1.1.1 description iBGP_TO_R1
 neighbor 1.1.1.1 update-source Loopback0
 neighbor 10.0.23.2 remote-as 65002
 neighbor 10.0.23.2 description eBGP_TO_R3
 neighbor 2001:DB8:23::2 remote-as 65002
 neighbor 2001:DB8:23::2 description eBGP_V6_TO_R3
 neighbor 2001:DB8:FF::1 remote-as 65001
 neighbor 2001:DB8:FF::1 description iBGP_V6_TO_R1
 neighbor 2001:DB8:FF::1 update-source Loopback0
 !
 address-family ipv4
  neighbor 1.1.1.1 activate
  neighbor 1.1.1.1 next-hop-self
  neighbor 10.0.23.2 activate
  no neighbor 2001:DB8:23::2 activate
  no neighbor 2001:DB8:FF::1 activate
 exit-address-family
 !
 address-family ipv6
  neighbor 2001:DB8:23::2 activate
  neighbor 2001:DB8:FF::1 activate
  neighbor 2001:DB8:FF::1 next-hop-self
 exit-address-family
```
</details>

<details>
<summary>Click to view R3 Configuration (dual-homed eBGP + IPv6)</summary>

```bash
! R3
ipv6 unicast-routing
!
interface Loopback0
 ipv6 address 2001:DB8:FF::3/128
!
interface Loopback1
 ipv6 address 2001:DB8:172:3::1/64
!
interface GigabitEthernet0/0
 ipv6 address FE80::3 link-local
 ipv6 address 2001:DB8:13::2/64
!
interface GigabitEthernet0/1
 ipv6 address FE80::3 link-local
 ipv6 address 2001:DB8:23::2/64
!
router bgp 65002
 neighbor 10.0.23.1 remote-as 65001
 neighbor 10.0.23.1 description eBGP_TO_R2
 neighbor 2001:DB8:13::1 remote-as 65001
 neighbor 2001:DB8:13::1 description eBGP_V6_TO_R1
 neighbor 2001:DB8:23::1 remote-as 65001
 neighbor 2001:DB8:23::1 description eBGP_V6_TO_R2
 !
 address-family ipv4
  neighbor 10.0.23.1 activate
  no neighbor 2001:DB8:13::1 activate
  no neighbor 2001:DB8:23::1 activate
 exit-address-family
 !
 address-family ipv6
  network 2001:DB8:172:3::/64
  neighbor 2001:DB8:13::1 activate
  neighbor 2001:DB8:23::1 activate
 exit-address-family
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ip ospf neighbor
show ipv6 ospf neighbor
show ip bgp summary
show bgp ipv6 unicast summary
show ip bgp
show bgp ipv6 unicast
show ip bgp 172.16.3.0/24
show bgp ipv6 unicast 2001:DB8:172:3::/64
show ip bgp neighbors 2.2.2.2 routes
show bgp ipv6 unicast neighbors 2001:DB8:FF::2 routes
ping 172.16.3.1                         ! from PC1
ping 2001:db8:172:3::1                  ! from PC1
traceroute 172.16.3.1                   ! from R1
traceroute 2001:db8:172:3::1            ! from R1
```
</details>

---

## 9. Troubleshooting Scenarios

### Workflow

```bash
python3 setup_lab.py --host <eve-ng-ip>                                # apply initial-configs
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>   # push solution state
python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>
# ...troubleshoot...
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>   # restore between tickets
```

---

### Ticket 1 -- iBGP Peer Established but R1 Has No Route to 172.16.3.0/24

R1's iBGP session to R2 is up (`show ip bgp summary` shows numeric state).
`show ip bgp 172.16.3.0/24` on R1 lists a path via R2 (next-hop 10.0.23.2), but
`show ip route 172.16.3.0` returns "subnet not in table." PC1 cannot reach
172.16.3.1. R2 itself has the prefix installed correctly.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py`

**Success criteria:** R1 must install 172.16.3.0/24 into the RIB. PC1 must
ping 172.16.3.1.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. On R1: `show ip bgp 172.16.3.0/24` -- look at the path line. The iBGP path
   shows `10.0.23.2 (inaccessible, no route)` -- the next-hop is unreachable.
2. 10.0.23.0/30 is the R2-R3 eBGP link; R1 has no IGP path to that subnet.
3. The iBGP preservation of next-hop means R2 forwarded R3's advertisement with
   R3's original next-hop intact. R2 must rewrite to itself.
4. On R2: `show running-config | section router bgp` -- the line
   `neighbor 1.1.1.1 next-hop-self` is missing under `address-family ipv4`.
5. Without next-hop-self, the eBGP next-hop (10.0.23.2) leaks unchanged to R1,
   which cannot resolve it.
</details>

<details>
<summary>Click to view Fix</summary>

```bash
R2(config)# router bgp 65001
R2(config-router)# address-family ipv4
R2(config-router-af)# neighbor 1.1.1.1 next-hop-self
R2(config-router-af)# end
R2# clear ip bgp 1.1.1.1 soft out                       ! soft refresh to send new NH

R1# show ip bgp 172.16.3.0/24                           ! <-- next-hop now 2.2.2.2 (resolvable)
R1# show ip route 172.16.3.0                            ! <-- B 172.16.3.0/24 installs
```
</details>

---

### Ticket 2 -- BGP IPv6 Session to R2 Never Establishes

R1's BGP IPv4 sessions to R2 and R3 are both Established. The eBGP-IPv6 session
to R3 (2001:DB8:13::2) is also up. But the iBGP-IPv6 session to R2
(2001:DB8:FF::2) stays in Idle. `show bgp ipv6 unicast summary` shows state
`Idle` for that neighbor. IPv6 reachability between loopbacks works from the
CLI (`ping 2001:DB8:FF::2` from R1 succeeds).

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py`

**Success criteria:** R1 must show state numeric (Established) for neighbor
`2001:DB8:FF::2`. IPv6 prefixes from R2 must appear in R1's BGP IPv6 table.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. On R1: `show bgp ipv6 unicast summary` -- peer `2001:DB8:FF::2` is Idle.
2. On R1: `ping 2001:DB8:FF::2 source Loopback0` -- succeeds. So IGP (OSPFv3)
   is fine and the peer is reachable.
3. On R1: `show bgp ipv6 unicast neighbors 2001:DB8:FF::2` -- scan the message
   counters (Opens/Notifications). Opens Sent = 0 means R1 is not even trying
   to open TCP. That points to an admin or configuration problem on R1's side.
4. On R1: `show running-config | section router bgp` -- look for
   `neighbor 2001:DB8:FF::2`. The line
   `neighbor 2001:DB8:FF::2 shutdown` is present under `router bgp 65001`.
5. Someone administratively shut the peer. When shut, BGP never moves out of
   Idle.
</details>

<details>
<summary>Click to view Fix</summary>

```bash
R1(config)# router bgp 65001
R1(config-router)# no neighbor 2001:DB8:FF::2 shutdown
R1(config-router)# end
R1# show bgp ipv6 unicast summary                       ! <-- state numeric within a minute
R1# show bgp ipv6 unicast                               ! <-- R2's v6 prefixes appear
```
</details>

---

### Ticket 3 -- R3 Doesn't Receive R1's Loopback1 IPv6 Prefix

The BGP IPv6 session between R1 and R3 is Established. R3's IPv6 BGP table
contains R1's 2001:DB8:1:1::/64 (PC1 LAN) and R2's prefixes. It does NOT
contain R1's 2001:DB8:172:1::/64 Loopback1 prefix. The network team expected
R3 to see both enterprise IPv6 prefixes.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py`

**Success criteria:** R3 must show `2001:DB8:172:1::/64` in
`show bgp ipv6 unicast` with AS_Path `65001`.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. On R3: `show bgp ipv6 unicast | include 2001:DB8:172:1` -- no entry.
2. On R1: `show bgp ipv6 unicast neighbors 2001:DB8:13::2 advertised-routes` --
   only `2001:DB8:1:1::/64` is listed. R1 is not advertising `2001:DB8:172:1::/64`.
3. On R1: `show running-config | section router bgp` -- under
   `address-family ipv6`, the line `network 2001:DB8:172:1::/64` is missing.
4. Confirm R1 has the prefix in the RIB: `show ipv6 route 2001:DB8:172:1::/64`
   -- it is present as a connected prefix.
5. BGP's `network`-statement rule applies to IPv6 too: the prefix must exist in
   the RIB AND a matching `network` statement must be configured. One without
   the other = no advertisement.
</details>

<details>
<summary>Click to view Fix</summary>

```bash
R1(config)# router bgp 65001
R1(config-router)# address-family ipv6
R1(config-router-af)# network 2001:DB8:172:1::/64
R1(config-router-af)# end
R3# show bgp ipv6 unicast | include 2001:DB8:172:1      ! <-- prefix arrives
```
</details>

---

## 10. Lab Completion Checklist

### Core Implementation (Section 5)

- [ ] Task 1: OSPFv2 neighbor FULL between R1 and R2; remote Loopback0 learned
- [ ] Task 2: iBGP IPv4 session R1<->R2 Established; next-hop-self on both sides
- [ ] Task 3: Second eBGP IPv4 session R2<->R3 Established; R3 sees two paths to R1's prefixes
- [ ] Task 4: IPv6 unicast routing on; all interfaces addressed per the plan; PC1 dual-stack
- [ ] Task 5: OSPFv3 adjacency FULL on R1-R2 Gi0/0; remote Loopback0 /128 in IPv6 RIB
- [ ] Task 6: BGP IPv6 AF active; iBGP-v6 and eBGP-v6 sessions Established; `next-hop-self` on iBGP-v6; IPv6 prefixes advertised
- [ ] Task 7: IPv4 and IPv6 end-to-end reachability from PC1 to 172.16.3.1 and 2001:DB8:172:3::1

### Troubleshooting (Section 9)

- [ ] Ticket 1: Missing `next-hop-self` on R2 diagnosed and fixed
- [ ] Ticket 2: Admin `shutdown` on R1's iBGP-IPv6 peer diagnosed and fixed
- [ ] Ticket 3: Missing `network 2001:DB8:172:1::/64` advertisement on R1 diagnosed and fixed

### Understanding

- [ ] Can explain why iBGP peers use Loopback addresses (resilience + IGP multipath)
- [ ] Can explain why `next-hop-self` is required on iBGP and what the symptom of its absence looks like (`inaccessible, no route`)
- [ ] Can explain why `no neighbor <v6-addr> activate` is needed under `address-family ipv4` on IOS
- [ ] Can list three things that must be true for a Loopback-based iBGP session to come up
