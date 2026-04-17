# Lab 00 -- eBGP Peering Fundamentals

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
relationships).

This lab introduces the Border Gateway Protocol (BGP) -- the routing protocol that
holds the Internet together. You will configure a single external BGP (eBGP) session
between two routers in different autonomous systems, watch the neighbor state
machine progress to Established, advertise prefixes with the `network` statement,
and interpret the BGP table. Everything that follows in the BGP chapter builds on
the primitives in this lab.

### IGP vs EGP -- Where BGP Fits

Protocols like OSPF and EIGRP are **Interior Gateway Protocols (IGPs)**: they run
*within* one administrative domain (one company, one autonomous system) and optimize
for fast convergence and shortest-path routing. BGP is the **Exterior Gateway Protocol
(EGP)**: it runs *between* autonomous systems, and its job is not "shortest path" --
it is **policy**. Which neighbor should I prefer? Which prefixes should I advertise
to whom? How do I influence the traffic other ASes send to me?

| Aspect | IGP (OSPF / EIGRP) | EGP (BGP) |
|---|---|---|
| Scope | Single AS | Between ASes (and large inside one AS) |
| Goal | Fastest convergence, shortest path | Policy, stability, scalability |
| Algorithm | Dijkstra (OSPF) / DUAL (EIGRP) | Path vector |
| Transport | OSPF: IP proto 89 / EIGRP: IP proto 88 | TCP port 179 |
| Neighbor formation | Automatic via hellos on the segment | Manually configured, unicast |
| Metric | Cost / composite | 10+ path attributes evaluated in order |
| Route scale | Thousands | 950,000+ Internet prefixes |

BGP uses **TCP/179** and **unicast neighbor statements**, which is why a neighbor
never forms by accident -- both sides must explicitly configure each other.

### Autonomous Systems and AS Numbers

An **autonomous system (AS)** is a collection of routers under a single
administrative policy. Each AS is identified by an AS number (ASN):

- **Public ASNs** (1 -- 64495, and 131072 -- 4199999999): registered with IANA/RIRs,
  used on the public Internet.
- **Private ASNs** (64512 -- 65534, and 4200000000 -- 4294967294): for private or
  experimental use, never leaked to the Internet.
- **Reserved** (0, 23456, 64496 -- 64511, etc.): documentation and special use.

This lab uses **65001** (enterprise) and **65002** (ISP) -- both in the 2-byte
private range, the standard choice for labs.

### eBGP vs iBGP

| Attribute | eBGP (external BGP) | iBGP (internal BGP) |
|---|---|---|
| Purpose | Peering between **different** ASes | Peering **within** one AS |
| AS numbers | Different on each side | Same on both sides |
| Default TTL | 1 (directly connected) | 255 |
| Peering target | Directly connected interface IP | Often Loopback (via IGP) |
| AS_Path modification | Prepends local AS on outbound | Does not modify |
| Route propagation | Learned routes advertised freely | **Split horizon**: iBGP routes not re-advertised to other iBGP peers |
| Next-hop behavior | Rewrites to self on outbound | Preserves next-hop from eBGP (hence `next-hop-self`) |

This lab configures **eBGP only**. iBGP arrives in lab-01 when R2 joins the topology.

### BGP Neighbor State Machine

A BGP session progresses through a well-defined set of states. Understanding these
is essential for diagnosis:

```
    ┌────────┐ TCP/179        ┌────────┐ OPEN sent    ┌──────────┐
    │  Idle  │ ───connect───► │ Active │ ───────────► │ OpenSent │
    └────┬───┘                └────┬───┘              └─────┬────┘
         │ admin shutdown          │ TCP retry              │ OPEN rcvd
         ▼                         ▼                        ▼
     (restart)                  (retry)               ┌───────────┐
                                                      │ OpenConfirm│
                                                      └─────┬─────┘
                                                            │ KEEPALIVE
                                                            ▼
                                                     ┌─────────────┐
                                                     │ Established │◄── data flows
                                                     └─────────────┘
```

| State | What's happening | If stuck here, investigate |
|---|---|---|
| Idle | Session disabled or reset-and-wait | `no shutdown` on neighbor, reachability |
| Connect | TCP handshake initiated (rare to see) | TCP/179 blocked? |
| Active | TCP retry loop | **Reachability** to neighbor IP, ACLs, source-interface |
| OpenSent | OPEN message sent, awaiting peer's OPEN | AS number mismatch, router-ID collision, auth |
| OpenConfirm | OPENs exchanged, awaiting KEEPALIVE | Timer mismatch, MD5 mismatch |
| **Established** | Session up, prefixes flowing | This is the healthy steady state |

> **Idle** = nothing happening. **Active** is a misleading name: it actually means
> "trying but failing." A session oscillating Idle -> Active is almost always a
> reachability or TCP problem; a session stuck in OpenSent is almost always an AS
> or router-ID problem.

### The `network` Statement -- BGP's Unique Semantic

In OSPF and EIGRP, the `network` statement says "enable the protocol on this
interface." In BGP, `network` means something very different:

> **BGP `network` advertises a prefix, but only if a matching route is already
> present in the IP routing table.**

This is the **#1 source of confusion** for engineers moving from IGPs to BGP. The
prefix must match **exactly** -- same network, same mask -- or the advertisement
is silently dropped. Example:

```
router bgp 65001
 network 172.16.1.0 mask 255.255.255.0    ! advertises 172.16.1.0/24
                                           ! only if 172.16.1.0/24 exists in the RIB
```

If R1 has a /30 and a /24 in its table, `network 172.16.0.0 mask 255.255.0.0` matches
NEITHER, and nothing is advertised. The `mask` keyword is required for anything that
is not a classful prefix.

### Skills this lab develops

| Skill | Description |
|---|---|
| BGP process configuration | Start `router bgp <asn>` with explicit router-ID and log-neighbor-changes |
| eBGP neighbor definition | Configure `neighbor <ip> remote-as <asn>` for a directly connected peer |
| Neighbor state progression | Read `show ip bgp summary` and interpret the State/PfxRcd column |
| Network advertisement | Use `network <prefix> mask <mask>` tied to a RIB-present route |
| BGP table interpretation | Read `show ip bgp` -- best path marker, next-hop, AS_Path, Origin |
| RIB installation | Verify BGP routes appear in the routing table with AD 20 (eBGP) |
| End-to-end reachability | Validate traffic flow across an AS boundary |
| BGP timers | Observe default keepalive (60s) and hold (180s) timers |

---

## 2. Topology & Scenario

**Scenario:** You are a network engineer at an enterprise (AS 65001) connecting to
its Internet service provider (AS 65002) for the first time. The edge router R1 is
cabled to the ISP's router R3, and an end host PC1 sits on R1's LAN. IP addressing
is pre-configured on both ends of the link. Your task: bring up the eBGP peering
session, advertise the enterprise's public-facing prefix (172.16.1.0/24) and the
PC1 LAN (192.168.1.0/24) into BGP, and confirm that R3 (the ISP) learns both
prefixes and PC1 can reach the ISP's advertised network (172.16.3.0/24).

```
                  ┌─────────────────────────┐
                  │           R1            │
                  │  (Enterprise Edge -- AS │
                  │         65001)          │
                  │    Lo0: 1.1.1.1/32      │
                  │   Lo1: 172.16.1.1/24    │
                  └──┬─────────────────┬────┘
               Gi0/2 │                 │ Gi0/1
           192.168.1.1/24          10.0.13.1/30
                     │                 │
                  ┌──┴──┐               │ eBGP (TCP/179)
                  │ PC1 │               │ AS 65001 ↔ AS 65002
                  │ .10 │               │
                  └─────┘          10.0.13.2/30
                                         │ Gi0/0
                                   ┌─────┴──────────────────┐
                                   │          R3            │
                                   │   (ISP -- AS 65002)    │
                                   │    Lo0: 3.3.3.3/32     │
                                   │   Lo1: 172.16.3.1/24   │
                                   └────────────────────────┘
```

### Why only two routers in lab-00?

Lab-00 is deliberately minimal. The goal is to strip away every distraction
(iBGP, dual-homing, route-maps, path attributes) and focus on exactly one thing:
how an eBGP session comes up and how prefixes cross an AS boundary. R2 joins the
topology in lab-01 (iBGP + dual-homing); R4 arrives in lab-02 (best path
selection). Everything you learn here is the foundation for those later additions.

---

## 3. Hardware & Environment Specifications

### Devices

| Device | Platform | Role |
|---|---|---|
| R1 | IOSv (15.x+) | Enterprise edge router (AS 65001) |
| R3 | IOSv (15.x+) | ISP router (AS 65002) |
| PC1 | VPCS | End host on R1's LAN (192.168.1.10/24) |

### Cabling

| Link | Endpoint A | Endpoint B | Subnet |
|---|---|---|---|
| L2 | R1 Gi0/1 | R3 Gi0/0 | 10.0.13.0/30 (eBGP peering link) |
| L4 | R1 Gi0/2 | PC1 e0 | 192.168.1.0/24 |

> The baseline defines additional links (R1-R2, R2-R3) but those interfaces are
> administratively shut in this lab; R2 joins in lab-01.

### Console Access Table

| Device | Port | Connection Command |
|---|---|---|
| R1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R3 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| PC1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |

Console ports are assigned dynamically by EVE-NG. Use the EVE-NG web UI or run
`python3 setup_lab.py --host <eve-ng-ip>` which discovers ports via the REST API.

---

## 4. Base Configuration

The `initial-configs/` directory contains starting configs for each router with IP
addressing pre-loaded. Push it with:

```bash
python3 setup_lab.py --host <eve-ng-ip>
```

### What IS pre-loaded

- Hostnames (R1, R3)
- `no ip domain-lookup`
- Loopback0 addresses (1.1.1.1/32, 3.3.3.3/32)
- Loopback1 addresses (172.16.1.1/24 on R1, 172.16.3.1/24 on R3) -- these are the
  prefixes you will advertise into BGP
- Physical interface IPs on the R1-R3 link and the PC1 LAN
- R1 Gi0/0 (toward R2), R3 Gi0/1 (toward R2), R3 Gi0/2 (toward R4) administratively
  shut down -- those endpoints do not exist in lab-00
- Console/VTY line settings

### What is NOT pre-loaded (you will configure in Section 5)

- BGP routing process
- BGP router-ID
- eBGP neighbor definition
- BGP network statements (route advertisement)

Verify pre-staged connectivity before starting Section 5:

```bash
R1# ping 10.0.13.2      ! R3 should reply -- directly connected
R1# ping 172.16.3.1     ! FAILS -- R3's Loopback1 is not yet reachable
PC1> ping 192.168.1.1   ! R1 should reply -- default gateway
```

The R1 -> R3 loopback ping failing is expected: until BGP is up, neither side
learns routes to the other's 172.16.x.0/24 prefix.

---

## 5. Lab Challenge: Core Implementation

Work through the tasks in order. After each task, run its verification command and
confirm the expected state before moving on.

### Task 1: Start the BGP process on R1 and R3

- Enable BGP on R1 with Autonomous System number **65001**.
- Enable BGP on R3 with Autonomous System number **65002**.
- Set an explicit BGP router-ID on each device that matches its Loopback0 address
  (R1 = 1.1.1.1, R3 = 3.3.3.3).
- Enable logging of neighbor state changes so adjacency events appear in the log.

**Verification:** `show ip bgp summary` on both routers must show the local AS
number and the configured router-ID. No neighbors are expected yet.

---

### Task 2: Configure the eBGP neighbor relationship

- On R1, declare R3 as a BGP neighbor using R3's directly connected interface
  address (10.0.13.2) and remote AS number 65002.
- On R3, declare R1 as a BGP neighbor using R1's directly connected interface
  address (10.0.13.1) and remote AS number 65001.
- Add a human-readable description to each neighbor (e.g., `eBGP_TO_R3_AS65002`).
- Under the IPv4 unicast address family, explicitly activate each neighbor.

**Verification:** `show ip bgp summary` must show the peer's IP, AS number, and
the **State/PfxRcd** column progressing to a numeric value (e.g., `0`). A numeric
value means the session is **Established**; a literal word (`Active`, `Idle`,
`OpenSent`) means the session is still coming up or has failed.

---

### Task 3: Advertise prefixes into BGP with network statements

- On R1, under the IPv4 address family, advertise `172.16.1.0/24` using the
  `network ... mask ...` form.
- On R1, also advertise the PC1 LAN `192.168.1.0/24` (classful boundary, so the
  `mask` keyword is optional).
- On R3, under the IPv4 address family, advertise `172.16.3.0/24` using the
  `network ... mask ...` form.

> The `network` statement requires the prefix to match an entry in the IP routing
> table **exactly** (same network, same mask). Both 172.16.1.0/24 and 192.168.1.0/24
> exist as connected routes on R1, so both will be advertised.

**Verification:** `show ip bgp` on R1 must list three prefixes -- `172.16.1.0/24`
and `192.168.1.0/24` as locally originated (next-hop `0.0.0.0`, marked `>i` or
`*>`), plus `172.16.3.0/24` learned from R3. On R3, `show ip bgp` must show
`172.16.3.0/24` local and `172.16.1.0/24` + `192.168.1.0/24` learned from R1.

---

### Task 4: Verify BGP routes install into the routing table

- On R1, examine the IP routing table for entries learned from BGP.
- Confirm the administrative distance of eBGP routes is **20**.
- Confirm the next-hop for the BGP-learned prefix is R3's peering IP (10.0.13.2).

**Verification:** `show ip route bgp` on R1 must show
`B 172.16.3.0/24 [20/0] via 10.0.13.2`. On R3, the same command must show
`B 172.16.1.0/24 [20/0] via 10.0.13.1` and `B 192.168.1.0/24 [20/0] via 10.0.13.1`.

---

### Task 5: Examine BGP keepalive and hold timers

- On R1, display the BGP neighbor details to find the negotiated keepalive and
  hold-down timers.
- Confirm they match the Cisco defaults (keepalive 60 seconds, hold 180 seconds).
- Note the **Local router ID**, **Remote router ID**, and **BGP state** fields.

**Verification:** `show ip bgp neighbors 10.0.13.2` on R1 must show
`BGP state = Established` and `BGP table version is N, ... 1 paths` and hold-time
of 180s, keepalive of 60s.

---

### Task 6: Verify end-to-end reachability

- From PC1, ping R3's advertised loopback (172.16.3.1).
- From R1, traceroute 172.16.3.1 and confirm the path is a single hop through
  R3 (10.0.13.2).
- From R3, ping 192.168.1.10 (PC1) sourcing from Loopback1 (172.16.3.1) -- this
  proves bidirectional reachability across the AS boundary.

**Verification:** All three probes succeed. Traceroute from R1 shows exactly one
routed hop (10.0.13.2). The R3 -> PC1 ping succeeds only because R1 advertised
192.168.1.0/24 into BGP in Task 3.

---

## 6. Verification & Analysis

Run these commands after completing Section 5. Inline `!` comments mark exactly
what to look for.

### 6a -- BGP summary and neighbor state (Tasks 1-2)

```
R1# show ip bgp summary
BGP router identifier 1.1.1.1, local AS number 65001                  ! <-- Task 1: router-ID + local AS
BGP table version is 4, main routing table version 4
3 network entries using 744 bytes of memory

Neighbor        V   AS MsgRcvd MsgSent  TblVer InQ OutQ Up/Down State/PfxRcd
10.0.13.2       4 65002      8      10       4   0    0 00:02:14            1    ! <-- numeric State = Established
```

Key reads:
- `local AS number 65001` confirms Task 1
- `BGP router identifier 1.1.1.1` confirms router-ID is explicit (not auto-selected)
- Under `V` (version): `4` means BGP-4, the only version in production use
- The State/PfxRcd column: a **number** means Established and N prefixes received.
  A **word** (`Idle`, `Active`, `OpenSent`) means the session is not up yet.

### 6b -- BGP table on R1 (Task 3)

```
R1# show ip bgp
BGP table version is 4, local router ID is 1.1.1.1
Status codes: s suppressed, d damped, h history, * valid, > best, i - internal,
              r RIB-failure, S Stale, m multipath, b backup-path, f RT-Filter,
              x best-external, a additional-path, c RIB-compressed,
Origin codes: i - IGP, e - EGP, ? - incomplete
RPKI validation codes: V valid, I invalid, N Not found

     Network          Next Hop            Metric LocPrf Weight Path
 *>  172.16.1.0/24    0.0.0.0                  0         32768 i         ! <-- R1 originated; weight 32768
 *>  172.16.3.0/24    10.0.13.2                0             0 65002 i   ! <-- learned from R3; AS_Path = 65002
 *>  192.168.1.0      0.0.0.0                  0         32768 i         ! <-- R1 originated (LAN)
```

Key reads:
- **`*>`** = valid (`*`) AND best (`>`). Every healthy prefix should have this marker.
- **Weight 32768** is the auto-assigned weight for locally originated routes --
  that's how R1 knows its own `network`-statement prefixes are "mine."
- **Weight 0** on the learned prefix is the default weight BGP assigns to routes
  received from a peer.
- **AS_Path `65002`** on 172.16.3.0/24 tells R1 the prefix originated in AS 65002
  and arrived with exactly one AS hop (direct eBGP).
- **Origin `i`** means the prefix was injected via a `network` statement (IGP
  origin). You'll see `?` (incomplete) for redistributed routes and rarely `e`
  (EGP, long obsolete).

### 6c -- BGP routes in the IP routing table (Task 4)

```
R1# show ip route bgp
      172.16.0.0/16 is variably subnetted, 2 subnets, 2 masks
B        172.16.3.0/24 [20/0] via 10.0.13.2, 00:02:30        ! <-- AD 20 = eBGP; next-hop = R3
```

Key reads:
- **`B`** = BGP-learned
- **`[20/0]`** -- 20 is the administrative distance for **eBGP** (iBGP is 200).
  Anything lower than 20 means a more-preferred protocol overrode BGP; AD 0
  (connected) always wins.
- **Metric 0** -- BGP does not compute a metric the way IGPs do. The slot is
  populated with MED (Multi-Exit Discriminator), which defaults to 0.

### 6d -- BGP neighbor detail (Task 5)

```
R1# show ip bgp neighbors 10.0.13.2
BGP neighbor is 10.0.13.2,  remote AS 65002, external link              ! <-- external = eBGP
  Description: eBGP_TO_R3_AS65002
  BGP version 4, remote router ID 3.3.3.3                               ! <-- R3's router-ID
  BGP state = Established, up for 00:02:47                              ! <-- MUST be Established
  Last read 00:00:47, last write 00:00:47, hold time is 180, keepalive interval is 60 seconds  ! <-- defaults
  Neighbor sessions:
    1 active, is not multisession capable (disabled)
  Neighbor capabilities:
    Route refresh: advertised and received(new)
    Four-octets ASN Capability: advertised and received
    Address family IPv4 Unicast: advertised and received
    ...
  Message statistics:
    InQ depth is 0
    OutQ depth is 0
                         Sent       Rcvd
    Opens:                  1          1
    Notifications:          0          0
    Updates:                2          2
    Keepalives:             4          4
    Route Refresh:          0          0
    Total:                  7          7
  ...
  For address family: IPv4 Unicast
    Session: 10.0.13.2
    BGP table version 4, neighbor version 4/0
    Output queue size : 0
    Index 1, Advertisements 1, Suppressed 0, Sent 1, Received 1          ! <-- we sent 2 prefixes, got 1
```

Key reads:
- `BGP state = Established` -- non-negotiable for prefix exchange
- `external link` -- eBGP (vs `internal link` for iBGP)
- `hold time is 180, keepalive interval is 60` -- Cisco defaults; these are
  **negotiated to the lower of the two sides** at session establishment
- Advertisements / Received counters under the AF section -- useful sanity check

### 6e -- End-to-end reachability (Task 6)

```
PC1> ping 172.16.3.1
84 bytes from 172.16.3.1 icmp_seq=1 ttl=254 time=3.241 ms              ! <-- works only if BGP is up

R1# traceroute 172.16.3.1
Tracing the route to 172.16.3.1
  1 10.0.13.2 4 msec 4 msec 4 msec                                      ! <-- one hop (R3)

R3# ping 192.168.1.10 source Loopback1
Sending 5, 100-byte ICMP Echos to 192.168.1.10, timeout is 2 seconds:
Packet sent with a source address of 172.16.3.1
!!!!!                                                                   ! <-- 100% success
```

---

## 7. Verification Cheatsheet

### BGP Process Configuration

```
router bgp <asn>
 bgp router-id <ip>
 bgp log-neighbor-changes
 neighbor <peer-ip> remote-as <peer-asn>
 neighbor <peer-ip> description <text>
 !
 address-family ipv4
  neighbor <peer-ip> activate
  network <prefix> mask <mask>
 exit-address-family
```

| Command | Purpose |
|---|---|
| `router bgp 65001` | Enter BGP configuration for Autonomous System 65001 |
| `bgp router-id 1.1.1.1` | Set explicit 32-bit router-ID (overrides highest-IP auto-pick) |
| `bgp log-neighbor-changes` | Log neighbor state transitions to syslog (very useful) |
| `neighbor 10.0.13.2 remote-as 65002` | Define an eBGP peer (different remote-as = eBGP) |
| `neighbor 10.0.13.2 description ...` | Human-readable tag for the neighbor |
| `neighbor 10.0.13.2 activate` | Enable the neighbor for this address family (required) |
| `network 172.16.1.0 mask 255.255.255.0` | Advertise the prefix IF it is in the RIB exactly |
| `network 192.168.1.0` | Same for a classful prefix (mask keyword is optional) |
| `no synchronization` | (Legacy) off by default on 12.4T+ -- no action needed on IOSv 15+ |

> **Exam tip:** The `network` statement in BGP is NOT like an IGP's `network`
> statement. It does not enable BGP on an interface. It advertises a prefix
> *only* when that exact prefix (network + mask) is already in the RIB.

### Verification Commands

| Command | What to Look For |
|---|---|
| `show ip bgp summary` | Local AS + router-ID; neighbor list; State/PfxRcd numeric = up |
| `show ip bgp` | Prefix table; `*>` on every best path; AS_Path, next-hop, Origin |
| `show ip bgp <prefix>` | Detailed view of one prefix: all paths, attributes, best path marker |
| `show ip bgp neighbors <ip>` | Session state, router-IDs, negotiated timers, message counters |
| `show ip bgp neighbors <ip> advertised-routes` | What we are sending to this peer |
| `show ip bgp neighbors <ip> routes` | What this peer sent us (pre-inbound-policy: raw) |
| `show ip route bgp` | BGP prefixes installed into the RIB (AD 20 for eBGP, 200 for iBGP) |
| `show tcp brief` | TCP session to peer on port 179 -- useful when stuck in Active/Idle |
| `clear ip bgp <peer-ip>` | Hard reset the session (disruptive; flaps all prefixes) |
| `clear ip bgp <peer-ip> soft` | Soft reset using Route Refresh (no session flap) |

> **Exam tip:** State/PfxRcd is the single most important field in
> `show ip bgp summary`. A number = session is up and that many prefixes arrived
> from that neighbor. A word = the session is still in the state machine (Idle,
> Active, OpenSent) and is NOT exchanging prefixes.

### BGP Administrative Distance Reference

| Route Source | AD |
|---|---|
| Connected interface | 0 |
| Static | 1 |
| eBGP | **20** |
| EIGRP (internal) | 90 |
| OSPF | 110 |
| EIGRP (external) | 170 |
| iBGP | **200** |

eBGP is deliberately **lower** than every IGP so that a route learned from an
external AS is preferred over any internal path (the external view is more
authoritative for external destinations). iBGP is deliberately **higher** so
that IGP-learned routes win inside an AS.

### Common eBGP Failure Causes

| Symptom | Likely Cause |
|---|---|
| Neighbor stuck in **Idle** | `shutdown` on neighbor, or no reachability configured yet |
| Neighbor stuck in **Active** | Cannot reach neighbor IP -- routing/ACL/interface problem |
| Neighbor flaps Idle <-> Active | Unstable underlying path, or TCP/179 blocked intermittently |
| Neighbor stuck in **OpenSent** | AS number mismatch, or router-ID collision (same RID on both sides) |
| Neighbor Established but 0 prefixes | `network` mask doesn't match RIB, or neighbor not `activate`d in the AF |
| Prefix in BGP table but not RIB | Another protocol has a lower AD; look for the `r` (RIB-failure) flag |
| One side sees prefix, other doesn't | Inbound filter on one side, or `next-hop` unreachable |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these configs first!

### Objective 1: eBGP session and prefix advertisement

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1 (AS 65001)
router bgp 65001
 bgp router-id 1.1.1.1
 bgp log-neighbor-changes
 neighbor 10.0.13.2 remote-as 65002
 neighbor 10.0.13.2 description eBGP_TO_R3_AS65002
 !
 address-family ipv4
  network 172.16.1.0 mask 255.255.255.0
  network 192.168.1.0
  neighbor 10.0.13.2 activate
 exit-address-family
```
</details>

<details>
<summary>Click to view R3 Configuration</summary>

```bash
! R3 (AS 65002)
router bgp 65002
 bgp router-id 3.3.3.3
 bgp log-neighbor-changes
 neighbor 10.0.13.1 remote-as 65001
 neighbor 10.0.13.1 description eBGP_TO_R1_AS65001
 !
 address-family ipv4
  network 172.16.3.0 mask 255.255.255.0
  neighbor 10.0.13.1 activate
 exit-address-family
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ip bgp summary
show ip bgp
show ip bgp 172.16.3.0
show ip bgp neighbors 10.0.13.2
show ip route bgp
ping 172.16.3.1 source Loopback1       ! from R1
ping 172.16.3.1                         ! from PC1
traceroute 172.16.3.1                   ! from R1
```
</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. Inject the fault first, then diagnose
and fix using only `show` commands.

### Workflow

```bash
python3 setup_lab.py --host <eve-ng-ip>                                # reset to known-good
python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>
# ...troubleshoot...
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>   # restore
```

---

### Ticket 1 -- eBGP Session on R1 Never Leaves "Active"

After a recent config change, R1's BGP session to the ISP refuses to come up.
`show ip bgp summary` on R1 shows the session cycling between Idle and Active
for the last ten minutes. R3 reports the same symptom from its side. Users on
PC1 cannot reach the ISP's 172.16.3.0/24 network.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py`

**Success criteria:** R1 and R3 must both show `State/PfxRcd` as a numeric
value (Established). R1 must learn `172.16.3.0/24` via BGP.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. On R1: `show ip bgp summary` -- neighbor 10.0.13.2 cycles Idle -> Active.
2. "Active" = BGP is **trying** to open the TCP session but failing. That is a
   reachability or TCP-port problem, NOT an AS/auth problem.
3. From R1, `ping 10.0.13.2` -- FAILS. The peering IP is unreachable.
4. `show ip interface brief | include 10.0.13` -- Gi0/1 shows up/up with IP
   10.0.13.1/30, so the interface is fine.
5. On R3: `show ip interface brief | include 10.0.13` -- Gi0/0 is
   **administratively down**. Somebody shut the peering interface on the ISP side.
6. A down peering interface = no Layer 2 = no TCP/179 = Active forever.
</details>

<details>
<summary>Click to view Fix</summary>

```bash
R3(config)# interface GigabitEthernet0/0
R3(config-if)# no shutdown
R3(config-if)# end

R1# show ip bgp summary                           ! <-- neighbor State/PfxRcd becomes numeric
R1# show ip route bgp                             ! <-- B 172.16.3.0/24 returns
```
</details>

---

### Ticket 2 -- BGP Session Stuck in "OpenSent" on R1

R1's BGP session to R3 advances past Idle/Active (so TCP reachability is fine)
but never reaches Established. `show ip bgp summary` shows State column stuck
at `OpenSent` for minutes, and the session counter keeps resetting. No prefixes
flow.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py`

**Success criteria:** R1's neighbor state must reach Established and R1 must
receive `172.16.3.0/24` in the BGP table.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. On R1: `show ip bgp summary` -- state shows OpenSent (or flapping OpenSent
   -> Idle -> Active -> OpenSent).
2. "OpenSent" means TCP is up, R1 sent its OPEN message, and it is waiting for
   R3's OPEN to match. A mismatch in the OPEN message (AS number, or router-ID
   collision) sends the session back to Idle.
3. On R1: `show ip bgp neighbors 10.0.13.2 | include remote AS` -- R1 expects
   remote AS 65002.
4. On R3: `show ip protocols | include Routing Protocol is` OR
   `show running-config | section router bgp` -- R3 is running `router bgp 65099`
   (wrong AS number).
5. AS mismatch means R3's OPEN says `My AS = 65099` but R1 was told to expect
   65002. R1 rejects the OPEN and resets the session. IOS logs
   `%BGP-3-NOTIFICATION: ... 2/2 (peer in wrong AS)` when `bgp log-neighbor-changes`
   is enabled.
</details>

<details>
<summary>Click to view Fix</summary>

```bash
R3(config)# no router bgp 65099                   ! remove the wrong-AS process
R3(config)# router bgp 65002
R3(config-router)# bgp router-id 3.3.3.3
R3(config-router)# neighbor 10.0.13.1 remote-as 65001
R3(config-router)# neighbor 10.0.13.1 description eBGP_TO_R1_AS65001
R3(config-router)# address-family ipv4
R3(config-router-af)# network 172.16.3.0 mask 255.255.255.0
R3(config-router-af)# neighbor 10.0.13.1 activate
R3(config-router-af)# end

R1# show ip bgp summary                           ! <-- reaches Established
R1# show ip bgp                                   ! <-- 172.16.3.0/24 via 10.0.13.2 appears
```
</details>

---

### Ticket 3 -- Session Is Established but R3 Doesn't See R1's LAN Prefix

R1 reports `State/PfxRcd = 1` toward R3, and `show ip bgp` on R1 shows all three
prefixes as expected. But the ISP engineer operating R3 says they can see
172.16.1.0/24 but **not** 192.168.1.0/24 (the PC1 LAN). PC1 can ping 10.0.13.2
but not 172.16.3.1. The ISP needs the LAN prefix advertised before they can
return-route traffic to it.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py`

**Success criteria:** R3 must see `192.168.1.0/24` in `show ip bgp` with
next-hop 10.0.13.1. PC1 must be able to ping 172.16.3.1.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. On R3: `show ip bgp | include 192.168.1` -- no entry. The prefix is NOT
   being advertised.
2. On R1: `show ip bgp neighbors 10.0.13.2 advertised-routes` -- only
   172.16.1.0/24 listed. Confirms R1 is not sending 192.168.1.0/24.
3. On R1: `show running-config | section router bgp` -- the
   `network 192.168.1.0` statement is missing from the IPv4 AF. Somebody
   removed it.
4. Remember BGP's `network` semantic: the prefix must be in the RIB AND a
   matching `network` statement must exist. RIB alone is not enough.
5. Confirm on R1: `show ip route 192.168.1.0` -- the connected /24 is present,
   so adding the statement will immediately advertise it.
</details>

<details>
<summary>Click to view Fix</summary>

```bash
R1(config)# router bgp 65001
R1(config-router)# address-family ipv4
R1(config-router-af)# network 192.168.1.0
R1(config-router-af)# end

R3# show ip bgp | include 192.168.1              ! <-- 192.168.1.0 via 10.0.13.1 appears
R3# ping 192.168.1.10                             ! <-- succeeds (PC1)
```
</details>

---

## 10. Lab Completion Checklist

### Core Implementation (Section 5)

- [ ] Task 1: BGP 65001 on R1, BGP 65002 on R3, explicit router-IDs set, log-neighbor-changes enabled
- [ ] Task 2: eBGP neighbor statements on both sides; session reaches Established
- [ ] Task 3: R1 advertises 172.16.1.0/24 and 192.168.1.0/24; R3 advertises 172.16.3.0/24
- [ ] Task 4: `B 172.16.3.0/24 [20/0] via 10.0.13.2` on R1; matching prefixes on R3
- [ ] Task 5: Confirmed BGP state Established, hold 180s, keepalive 60s
- [ ] Task 6: PC1 ping 172.16.3.1 succeeds; R1 traceroute shows single-hop via 10.0.13.2

### Troubleshooting (Section 9)

- [ ] Ticket 1: Interface shutdown on R3's peering link diagnosed and fixed
- [ ] Ticket 2: AS number mismatch on R3 (wrong ASN) diagnosed and fixed
- [ ] Ticket 3: Missing `network 192.168.1.0` statement on R1 diagnosed and fixed

### Understanding

- [ ] Can explain why BGP uses TCP/179 instead of a protocol-specific transport
- [ ] Can walk the BGP state machine (Idle -> Active -> OpenSent -> OpenConfirm -> Established) and name one likely cause of being stuck in each state
- [ ] Can explain why `network 172.16.0.0 mask 255.255.0.0` on R1 would NOT advertise 172.16.1.0/24 (exact RIB match required)
- [ ] Can state the administrative distance of eBGP (20) and iBGP (200) and why they differ
