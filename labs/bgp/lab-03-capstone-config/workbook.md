# BGP Lab 03 -- Full Protocol Mastery (Capstone I)

## Table of Contents

1. [Concepts & Skills Covered](#1-concepts--skills-covered)
2. [Topology & Scenario](#2-topology--scenario)
3. [Hardware & Environment Specifications](#3-hardware--environment-specifications)
4. [Base Configuration](#4-base-configuration)
5. [Lab Challenge: Full Protocol Mastery](#5-lab-challenge-full-protocol-mastery)
6. [Verification & Analysis](#6-verification--analysis)
7. [Verification Cheatsheet](#7-verification-cheatsheet)
8. [Solutions (Spoiler Alert!)](#8-solutions-spoiler-alert)
9. [Troubleshooting Scenarios](#9-troubleshooting-scenarios)
10. [Lab Completion Checklist](#10-lab-completion-checklist)

---

## 1. Concepts & Skills Covered

**Exam Objective:** CCNP ENCOR 350-401, 3.2.c -- Configure and verify eBGP (best path selection, neighbor relationships).

This is a capstone. No task-by-task guidance is provided. Labs 00 through 02 walked you through eBGP peering, iBGP with loopback peering and `next-hop-self`, dual-stack BGP with MP-BGP per-address-family activation, OSPF as the IGP inside AS 65001, and the full best-path algorithm (Weight, LOCAL_PREF, AS_PATH prepending, MED, Origin). In this lab you apply the entire stack from scratch, with only IP addressing pre-configured.

### Architecture Summary You Must Implement

| Layer | Requirement |
|-------|-------------|
| IGP (AS 65001) | OSPFv2 area 0 and OSPFv3 area 0 on the R1<->R2 internal link, carrying Loopback0 reachability for iBGP peering |
| iBGP (AS 65001) | Loopback-sourced peering between R1 and R2 in BOTH IPv4 and IPv6 address-families, with `next-hop-self` applied by both routers |
| eBGP (AS 65001 <-> 65002) | Dual-homed: R1<->R3 and R2<->R3, in BOTH IPv4 and IPv6 address-families, interface-address peering |
| eBGP (AS 65002 <-> 65003) | R3<->R4 in BOTH IPv4 and IPv6 address-families |
| MP-BGP | Separate neighbor activation per address-family; deactivate the wrong-AF neighbors explicitly |
| Advertisements | R1: 172.16.1.0/24, 192.168.1.0/24, v6 equivalents. R3: 172.16.3.0/24, v6 equivalent. R4: 172.16.4.0/24, 192.168.2.0/24, v6 equivalents. R2 is transit only. |
| Path policy | LOCAL_PREF 200 on R1 inbound from R3, 150 on R2 inbound from R3 (R1 primary exit). MED 50 on R3 outbound toward R1, 100 outbound toward R2 |

### Blueprint Coverage

Every bullet below must be demonstrable on your completed lab. Use `show` commands to prove it.

- iBGP peering between R1 and R2 is Established in both IPv4 and IPv6 AFs and uses Loopback0 as the session source.
- eBGP peering R1<->R3, R2<->R3, R3<->R4 is Established in both AFs.
- `next-hop-self` is configured on R1 and R2 toward their iBGP peer -- R2 can resolve the next-hop of R3-learned prefixes via the IGP route to 1.1.1.1.
- R1 sees all three external prefix groups (R3's, R4's) in both IPv4 and IPv6 BGP tables.
- R1's best path to 172.16.4.0/24 shows LocPref 200 on the direct eBGP path.
- R2's best path to 172.16.4.0/24 shows the iBGP path from 1.1.1.1 with LocPref 200 (propagated by iBGP), not its own eBGP path.
- R1 and R2 both see Metric 50 vs Metric 100 on R3's 172.16.3.0/24 prefix (MED outbound on R3).
- PC1 can ping and traceroute to PC2 in both IPv4 and IPv6; traceroute from PC1 transits R1 -> R3 -> R4.

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| Build a dual-stack multi-AS BGP network from scratch | Plan the order of operations so every prerequisite is in place before the next configuration step. |
| Integrate IGP and BGP | Use OSPFv2/v3 on the internal link to make iBGP loopback peering work. |
| Apply MP-BGP per-AF activation discipline | Keep IPv4 and IPv6 address-families independent and correctly activated on each peer. |
| Implement enterprise path preference | Use LOCAL_PREF inbound on eBGP peers so iBGP distributes the preference AS-wide. |
| Set MED outbound to hint the neighbor AS | Use route-map outbound with `set metric` to influence the neighbor's inbound path. |
| Verify by proof, not by feeling | Every requirement in Section 1 must be backed by a `show` output. |

---

## 2. Topology & Scenario

You are the network architect rolling out the final production design for a three-AS enterprise-to-ISP-to-branch topology. Lab exercises over the past two weeks have broken the design into pieces; today you implement it end-to-end.

The topology is the same one you have been building since Lab 01 -- AS 65001 with R1 and R2 at the enterprise edge, AS 65002 with R3 as the ISP transit, AS 65003 with R4 at the remote branch. Dual-stack (IPv4 and IPv6) is mandatory. Only IP addressing is pre-configured; every routing protocol, peering session, advertisement, and policy is yours to build.

```
                    ┌────────── AS 65001 ──────────┐
                    │                                │
   PC1 ──┐          │  ┌────────────────┐           │
         │          │  │       R1       │           │
         │          │  │ Enterprise Ed1 │           │
         │          │  │ Lo0: 1.1.1.1   │           │
         └─Gi0/2────┤  └───────┬────────┘           │
  192.168.1.0/24    │          │ OSPFv2+v3+iBGP     │
  2001:DB8:1:1::/64 │          │ 10.0.12.0/30       │
                    │          │ 2001:DB8:12::/64   │
                    │  ┌───────┴────────┐           │
                    │  │       R2       │           │
                    │  │ Enterprise Ed2 │           │
                    │  │ Lo0: 2.2.2.2   │           │
                    │  └─┬──────────────┘           │
                    └────┼──────────────────────────┘
                         │ eBGP (dual-homed)
              eBGP       │
              ┌──────────┴───────┐
              │        R3        │
              │  ISP (AS 65002)  │
              │   Lo0: 3.3.3.3   │
              └────────┬─────────┘
                       │ eBGP
                       │ 10.0.34.0/30
                       │ 2001:DB8:34::/64
                       │
                ┌──────┴──────┐
                │     R4      │──── PC2
                │  Branch     │     192.168.2.0/24
                │  AS 65003   │     2001:DB8:2:2::/64
                │ Lo0: 4.4.4.4│
                └─────────────┘
```

---

## 3. Hardware & Environment Specifications

**EVE-NG Topology:** `bgp/lab-03-capstone-config.unl`

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

Run `python3 setup_lab.py --host <eve-ng-ip>` from this lab directory.

### Pre-loaded (initial-configs)

- Hostnames on all four routers.
- `ipv6 unicast-routing` enabled.
- All interfaces with correct IPv4 + IPv6 addresses (link-local FE80::<router-number>).
- Loopback0 and Loopback1 with IPv4 + IPv6 addressing.
- PC1 and PC2 with dual-stack addresses via `.vpc`.

### NOT pre-loaded (your responsibility)

- OSPFv2 process on R1 and R2 (area 0, Loopback0 + internal link).
- OSPFv3 process on R1 and R2 (area 0, applied via `ipv6 ospf 1 area 0` on Loopback0 and internal link).
- BGP process on all four routers with appropriate router-IDs.
- iBGP peering R1 <-> R2 (IPv4 and IPv6, Loopback-sourced, `next-hop-self`).
- eBGP peering R1 <-> R3, R2 <-> R3, R3 <-> R4 (IPv4 and IPv6).
- MP-BGP: separate neighbor activation per address-family.
- BGP network advertisements (R1, R3, R4; R2 is transit only).
- Path preference policies: LOCAL_PREF 200 on R1 and 150 on R2 inbound from R3; MED 50/100 on R3 outbound toward R1/R2.

---

## 5. Lab Challenge: Full Protocol Mastery

> This is a capstone lab. No step-by-step guidance is provided.
> Configure the complete BGP solution from scratch -- IP addressing is pre-configured; everything else is yours to build.
> All blueprint bullets for this chapter must be addressed.

### Requirements

Your final lab must satisfy every item below. Use your own planning, your own command order, and your own verification commands.

**R1 -- Enterprise Edge 1 (AS 65001):**

- OSPFv2 and OSPFv3 on the internal link toward R2 and on Loopback0, router-id 1.1.1.1, area 0 only, passive-interface-default with the internal link as the only non-passive interface.
- BGP AS 65001 with router-id 1.1.1.1.
- iBGP peer to R2, Loopback-sourced, dual-stack, with `next-hop-self` applied.
- eBGP peer to R3 on the direct link, dual-stack.
- Advertise 172.16.1.0/24, 192.168.1.0/24 in IPv4 AF; 2001:DB8:172:1::/64, 2001:DB8:1:1::/64 in IPv6 AF.
- Inbound route-map on eBGP peer 10.0.13.2 (and IPv6 peer) that sets LOCAL_PREF 200.

**R2 -- Enterprise Edge 2 (AS 65001):**

- OSPFv2 and OSPFv3 on the internal link toward R1 and on Loopback0, router-id 2.2.2.2.
- BGP AS 65001 with router-id 2.2.2.2.
- iBGP peer to R1, Loopback-sourced, dual-stack, with `next-hop-self` applied.
- eBGP peer to R3 on the direct link, dual-stack.
- No local network advertisements (R2 is transit only).
- Inbound route-map on eBGP peer 10.0.23.2 (and IPv6 peer) that sets LOCAL_PREF 150.

**R3 -- ISP Router (AS 65002):**

- BGP AS 65002 with router-id 3.3.3.3.
- eBGP peers to R1 (direct link), R2 (direct link), and R4 (direct link), all dual-stack.
- Advertise 172.16.3.0/24 in IPv4 AF; 2001:DB8:172:3::/64 in IPv6 AF.
- Outbound route-maps toward R1 setting metric 50 and toward R2 setting metric 100, on BOTH address-families.

**R4 -- Remote Branch (AS 65003):**

- BGP AS 65003 with router-id 4.4.4.4.
- eBGP peer to R3, dual-stack.
- Advertise 172.16.4.0/24, 192.168.2.0/24 in IPv4 AF; 2001:DB8:172:4::/64, 2001:DB8:2:2::/64 in IPv6 AF.

**Success criteria (verified end-to-end):**

- `show bgp ipv4 unicast summary` on every router shows all expected neighbors Established with the expected PfxRcd counts.
- `show bgp ipv6 unicast summary` on every router shows the same in IPv6.
- `show bgp ipv4 unicast 172.16.4.0` on R1 shows LocPref 200 on the selected path.
- `show bgp ipv4 unicast 172.16.4.0` on R2 shows the iBGP path from 1.1.1.1 (LocPref 200) as best.
- `show bgp ipv4 unicast 172.16.3.0` on R1 shows Metric 50; on R2 the direct eBGP path shows Metric 100.
- PC1 `ping 192.168.2.10` succeeds. PC1 `ping6 2001:db8:2:2::10` succeeds.
- PC1 `trace 192.168.2.10` transits R1 -> R3 -> R4.

---

## 6. Verification & Analysis

### BGP Session Health (all routers)

```bash
R1# show bgp ipv4 unicast summary
Neighbor        V           AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
2.2.2.2         4        65001      34      36       14    0    0 00:15:32        0   ! ← iBGP Established (R2 transit, 0 pfx)
10.0.13.2       4        65002      38      35       14    0    0 00:15:20        3   ! ← eBGP to R3, 3 prefixes (R3+R4)

R1# show bgp ipv6 unicast summary
Neighbor        V           AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
2001:DB8:FF::2  4        65001      32      34       12    0    0 00:15:30        0
2001:DB8:13::2  4        65002      34      32       12    0    0 00:15:18        3

R2# show bgp ipv4 unicast summary
Neighbor        V           AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
1.1.1.1         4        65001      36      34       14    0    0 00:15:32        5   ! ← R1 sends 5 prefixes via iBGP
10.0.23.2       4        65002      38      35       14    0    0 00:15:20        3

R3# show bgp ipv4 unicast summary
Neighbor        V           AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
10.0.13.1       4        65001      35      38       14    0    0 00:15:20        2
10.0.23.1       4        65001      35      38       14    0    0 00:15:20        0   ! ← R2 is transit, advertises nothing
10.0.34.2       4        65003      12      10       14    0    0 00:10:12        2
```

### Best-Path Verification (R1's view of R4's prefix)

```bash
R1# show bgp ipv4 unicast 172.16.4.0
BGP routing table entry for 172.16.4.0/24
Paths: (2 available, best #1, table default)
  65002 65003
    10.0.13.2 from 10.0.13.2 (3.3.3.3)
      Origin IGP, metric 50, localpref 200, valid, external, best   ! ← LocPref 200 wins step 2; Metric 50 inherited from R3's MED
  65002 65003
    2.2.2.2 (metric 2) from 2.2.2.2 (2.2.2.2)
      Origin IGP, metric 100, localpref 150, valid, internal        ! ← iBGP path via R2: inferior on LocPref
```

### Best-Path Verification (R2's view -- iBGP wins)

```bash
R2# show bgp ipv4 unicast 172.16.4.0
BGP routing table entry for 172.16.4.0/24
Paths: (2 available, best #1, table default)
  65002 65003
    1.1.1.1 (metric 2) from 1.1.1.1 (1.1.1.1)
      Origin IGP, metric 50, localpref 200, valid, internal, best    ! ← iBGP from R1 (LocPref 200) wins
  65002 65003
    10.0.23.2 from 10.0.23.2 (3.3.3.3)
      Origin IGP, metric 100, localpref 150, valid, external         ! ← R2's own eBGP path loses
```

### End-to-End Reachability

```bash
PC1> ping 192.168.2.10
84 bytes from 192.168.2.10 icmp_seq=1 ttl=61 time=11.8 ms    ! ← success via R1->R3->R4

PC1> trace 192.168.2.10
 1   192.168.1.1     ... ms    ! ← R1 (gateway)
 2   10.0.13.2       ... ms    ! ← R3 (primary exit via LocPref 200)
 3   10.0.34.2       ... ms    ! ← R4
 4   192.168.2.10    ... ms    ! ← PC2

PC1> ping6 2001:db8:2:2::10
84 bytes from 2001:db8:2:2::10 icmp_seq=1 ttl=61 time=12.1 ms    ! ← IPv6 dual-stack reachable
```

---

## 7. Verification Cheatsheet

### BGP Configuration Skeletons

```
router ospf 1
 router-id X.X.X.X
 passive-interface default
 no passive-interface <internal-link-interface>
 network <loopback-ip> 0.0.0.0 area 0
 network <internal-subnet> <wildcard> area 0
!
ipv6 router ospf 1
 router-id X.X.X.X
 passive-interface default
 no passive-interface <internal-link-interface>
!
interface <loopback-or-internal-link>
 ipv6 ospf 1 area 0
!
router bgp <AS>
 bgp router-id X.X.X.X
 bgp log-neighbor-changes
 neighbor <peer-ip> remote-as <remote-AS>
 neighbor <peer-ip> update-source Loopback0      ! iBGP only
 !
 address-family ipv4
  network <prefix> mask <mask>
  neighbor <peer-ip> activate
  neighbor <peer-ip> next-hop-self               ! iBGP only
  neighbor <peer-ip> route-map <NAME> in | out
  no neighbor <v6-peer> activate
 exit-address-family
 !
 address-family ipv6
  network <v6-prefix>
  neighbor <v6-peer> activate
  neighbor <v6-peer> next-hop-self               ! iBGP only
  no neighbor <v4-peer> activate
 exit-address-family
```

### Verification Commands

| Command | What to Look For |
|---------|-----------------|
| `show bgp ipv4 unicast summary` | All expected neighbors Established with correct PfxRcd |
| `show bgp ipv6 unicast summary` | Same check for IPv6 AF |
| `show bgp ipv4 unicast` | Table overview -- `>` on selected best path |
| `show bgp ipv4 unicast <prefix>` | Per-path Weight, LocPref, MED, AS_PATH, Origin, `best` marker |
| `show ip route bgp` | BGP-originated entries in RIB |
| `show ip route ospf` | IGP reachability to 1.1.1.1 / 2.2.2.2 (required for iBGP loopback peering) |
| `show ip bgp neighbors <peer> policy` | Confirms which route-maps are attached in/out |
| `show route-map <NAME>` | Hit counter on the policy |

### Common Capstone Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| iBGP neighbor stuck in Idle | IGP (OSPF) not running -- no route to the peer's Loopback0 |
| iBGP Established but R2 can't reach R3's prefixes | `next-hop-self` missing on R1 -- R2 can't resolve 10.0.13.2 |
| IPv4 prefixes in table but IPv6 absent | Forgot to `activate` the v6 peer under IPv6 address-family |
| LOCAL_PREF 200 configured but not visible on R2 | Route-map `in` applied but never soft-cleared (`clear ip bgp <peer> soft in`) |
| MED applied on R3 but Metric 0 on R1's view | Route-map `out` applied but never soft-cleared (`clear ip bgp <peer> soft out`) |
| PC1 can ping but not traceroute | Usually a return-path issue -- R4 doesn't have a route back to 192.168.1.0 because its eBGP path is broken one way |

---

## 8. Solutions (Spoiler Alert!)

> This is a capstone -- do not peek until you have fully attempted the build yourself.

### Full Configuration Files

<details>
<summary>Click to view R1 Configuration</summary>

```bash
hostname R1
!
no ip domain-lookup
ipv6 unicast-routing
!
interface Loopback0
 ip address 1.1.1.1 255.255.255.255
 ipv6 address 2001:DB8:FF::1/128
 ipv6 ospf 1 area 0
!
interface Loopback1
 ip address 172.16.1.1 255.255.255.0
 ipv6 address 2001:DB8:172:1::1/64
!
interface GigabitEthernet0/0
 ip address 10.0.12.1 255.255.255.252
 ipv6 address FE80::1 link-local
 ipv6 address 2001:DB8:12::1/64
 ipv6 ospf 1 area 0
 no shutdown
!
interface GigabitEthernet0/1
 ip address 10.0.13.1 255.255.255.252
 ipv6 address FE80::1 link-local
 ipv6 address 2001:DB8:13::1/64
 no shutdown
!
interface GigabitEthernet0/2
 ip address 192.168.1.1 255.255.255.0
 ipv6 address FE80::1 link-local
 ipv6 address 2001:DB8:1:1::1/64
 no shutdown
!
router ospf 1
 router-id 1.1.1.1
 passive-interface default
 no passive-interface GigabitEthernet0/0
 network 1.1.1.1 0.0.0.0 area 0
 network 10.0.12.0 0.0.0.3 area 0
!
ipv6 router ospf 1
 router-id 1.1.1.1
 passive-interface default
 no passive-interface GigabitEthernet0/0
!
ip prefix-list ALL_V4 seq 5 permit 0.0.0.0/0 le 32
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
 bgp router-id 1.1.1.1
 bgp log-neighbor-changes
 neighbor 2.2.2.2 remote-as 65001
 neighbor 2.2.2.2 update-source Loopback0
 neighbor 10.0.13.2 remote-as 65002
 neighbor 2001:DB8:13::2 remote-as 65002
 neighbor 2001:DB8:FF::2 remote-as 65001
 neighbor 2001:DB8:FF::2 update-source Loopback0
 !
 address-family ipv4
  network 172.16.1.0 mask 255.255.255.0
  network 192.168.1.0
  neighbor 2.2.2.2 activate
  neighbor 2.2.2.2 next-hop-self
  neighbor 10.0.13.2 activate
  neighbor 10.0.13.2 route-map LOCAL_PREF_FROM_R3 in
  no neighbor 2001:DB8:13::2 activate
  no neighbor 2001:DB8:FF::2 activate
 exit-address-family
 !
 address-family ipv6
  network 2001:DB8:172:1::/64
  network 2001:DB8:1:1::/64
  no neighbor 10.0.13.2 activate
  neighbor 2001:DB8:13::2 activate
  neighbor 2001:DB8:13::2 route-map LOCAL_PREF_V6_FROM_R3 in
  neighbor 2001:DB8:FF::2 activate
  neighbor 2001:DB8:FF::2 next-hop-self
 exit-address-family
```
</details>

<details>
<summary>Click to view R2 Configuration</summary>

See `solutions/R2.cfg` in this lab directory. It follows the same pattern as R1 but with router-id 2.2.2.2, LOCAL_PREF 150, and no local `network` advertisements.
</details>

<details>
<summary>Click to view R3 Configuration</summary>

See `solutions/R3.cfg`. BGP AS 65002 with four eBGP peers (R1, R2, R4) dual-stack; MED 50 outbound toward R1 and MED 100 outbound toward R2 in both address-families.
</details>

<details>
<summary>Click to view R4 Configuration</summary>

See `solutions/R4.cfg`. BGP AS 65003 with one eBGP peer to R3 dual-stack; advertises 172.16.4.0/24, 192.168.2.0/24, and v6 equivalents.
</details>

<details>
<summary>Click to view Full Verification Sequence</summary>

```bash
! Verify IGP reachability (prerequisite for iBGP)
R1# show ip route ospf
R1# show ipv6 route ospf

! Verify BGP adjacency in both address-families
R1# show bgp ipv4 unicast summary
R1# show bgp ipv6 unicast summary
R2# show bgp ipv4 unicast summary
R3# show bgp ipv4 unicast summary
R4# show bgp ipv4 unicast summary

! Verify path selection
R1# show bgp ipv4 unicast 172.16.4.0
R2# show bgp ipv4 unicast 172.16.4.0
R1# show bgp ipv6 unicast 2001:DB8:172:4::/64

! Verify end-to-end
PC1> ping 192.168.2.10
PC1> ping6 2001:db8:2:2::10
PC1> trace 192.168.2.10
```
</details>

---

## 9. Troubleshooting Scenarios

Capstone I is focused on clean-slate build, not troubleshooting. Comprehensive troubleshooting is covered in Lab 04 (Capstone II). If your build fails end-to-end verification, diagnose using the failure causes in Section 7.

### Workflow

```bash
python3 setup_lab.py                              # reset to IP-only initial state
python3 scripts/fault-injection/apply_solution.py # push full solution for comparison
```

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] OSPFv2 adjacency UP between R1 and R2
- [ ] OSPFv3 adjacency UP between R1 and R2
- [ ] R1 and R2 have OSPF routes to each other's Loopback0
- [ ] iBGP R1<->R2 Established in IPv4 AF
- [ ] iBGP R1<->R2 Established in IPv6 AF (Loopback-sourced, 2001:DB8:FF::1 / ::2)
- [ ] eBGP R1<->R3 Established in both AFs
- [ ] eBGP R2<->R3 Established in both AFs
- [ ] eBGP R3<->R4 Established in both AFs
- [ ] R1 advertises 172.16.1.0/24 and 192.168.1.0/24 (IPv4 AF); R3 and R4 receive them
- [ ] R1 advertises 2001:DB8:172:1::/64 and 2001:DB8:1:1::/64 (IPv6 AF)
- [ ] R3 advertises 172.16.3.0/24 and 2001:DB8:172:3::/64
- [ ] R4 advertises 172.16.4.0/24, 192.168.2.0/24, and v6 equivalents
- [ ] `next-hop-self` applied on R1 and R2 toward their iBGP peer
- [ ] R1's view of 172.16.4.0/24 shows LocPref 200 on selected path
- [ ] R2's view of 172.16.4.0/24 shows iBGP path from 1.1.1.1 as best (LocPref 200)
- [ ] R1 sees Metric 50 on 172.16.3.0/24; R2's direct eBGP path shows Metric 100
- [ ] PC1 pings 192.168.2.10 (5/5 reply)
- [ ] PC1 ping6 2001:db8:2:2::10 (5/5 reply)
- [ ] PC1 traceroute to 192.168.2.10 transits R1 -> R3 -> R4
