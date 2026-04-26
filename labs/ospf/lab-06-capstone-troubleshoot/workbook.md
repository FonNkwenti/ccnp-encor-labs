# OSPF Lab 06 — Comprehensive Troubleshooting: Capstone II

## Table of Contents

1. [Concepts & Skills Covered](#1-concepts--skills-covered)
2. [Topology & Scenario](#2-topology--scenario)
3. [Hardware & Environment Specifications](#3-hardware--environment-specifications)
4. [Base Configuration](#4-base-configuration)
5. [Lab Challenge: Comprehensive Troubleshooting](#5-lab-challenge-comprehensive-troubleshooting)
6. [Verification & Analysis](#6-verification--analysis)
7. [Verification Cheatsheet](#7-verification-cheatsheet)
8. [Solutions (Spoiler Alert!)](#8-solutions-spoiler-alert)
9. [Troubleshooting Scenarios](#9-troubleshooting-scenarios)
10. [Lab Completion Checklist](#10-lab-completion-checklist)

---

## 1. Concepts & Skills Covered

**Exam Objective:** 3.2.a (OSPF area types, LSA types, adjacency behavior) and 3.2.b (OSPF neighbor relationships, DR/BDR election, network types, passive-interface, summarization, filtering)

This capstone integrates all OSPF concepts into a single troubleshooting challenge. The network is pre-broken with five concurrent faults spanning every blueprint category. You must diagnose and resolve all faults using only show commands, restoring full multi-area OSPF convergence with IPv4 and IPv6 end-to-end reachability. No step-by-step guidance is provided.

---

### Topic 1: OSPF Troubleshooting Methodology

Systematic troubleshooting prevents chasing symptoms. OSPF failures fall into a predictable hierarchy — work from the bottom up:

```
Layer 1:  Physical / interface up-up?
Layer 2:  Is OSPF enabled on the interface (show ip ospf interface)?
Layer 3:  Are hellos being sent and received?
           → Hello/dead timer match?
           → Area ID match?
           → Network type match?
           → Authentication match (if configured)?
Layer 4:  Neighbor state progression (INIT → 2-WAY → EXSTART → LOADING → FULL)?
           → MTU mismatch → stuck in EXSTART/EXCHANGE
           → Duplicate router-ID → stuck in EXSTART
Layer 5:  Routes in LSDB but not in routing table?
           → Distribute-list filtering?
           → Area type blocking LSAs?
Layer 6:  Correct routes in routing table but reachability fails?
           → Passive interface on transit link?
           → Missing network statement?
```

Always start with `show ip ospf neighbor` to map adjacency state across the topology, then drill into each suspicious link with `show ip ospf interface <int>`.

---

### Topic 2: Hello/Dead Timer Mismatch Diagnosis

OSPF requires matching hello and dead intervals between neighbors. IOS defaults are hello=10s, dead=40s on broadcast/point-to-point. Mismatched timers cause neighbors to never reach 2-WAY — they are discarded during INIT processing.

**Identifying the mismatch:**

```
R4# show ip ospf interface GigabitEthernet0/0
GigabitEthernet0/0 is up, line protocol is up
  Internet Address 10.1.24.2/30, Area 1, Attached via Network Statement
  Process ID 1, Router ID 4.4.4.4, Network Type POINT_TO_POINT, Cost: 1
  Timer intervals configured, Hello 5, Dead 20, Wait 20, Retransmit 5
              ! ← hello=5, dead=20 on R4
  Neighbor Count is 0, ...
              ! ← zero neighbors despite interface being up

R2# show ip ospf interface GigabitEthernet0/1
  Timer intervals configured, Hello 10, Dead 40, Wait 40, Retransmit 5
              ! ← hello=10, dead=40 on R2 — MISMATCH
```

Fix: match the hello and dead intervals on both ends of the link, or remove the custom timers from both sides to revert to defaults.

---

### Topic 3: Area ID Mismatch Diagnosis

OSPF uses area IDs in hello packets. If two routers on the same link advertise different area IDs, no adjacency forms. The interface shows OSPF is active, but the neighbor never appears.

```
R3# show ip ospf interface GigabitEthernet0/1
  Internet Address 10.2.35.1/30, Area 0, ...
              ! ← Area 0 on R3 side

R5# show ip ospf interface GigabitEthernet0/0
  Internet Address 10.2.35.2/30, Area 2, ...
              ! ← Area 2 on R5 side — MISMATCH: no adjacency
```

Fix: correct the network statement or area assignment so both sides use the same area ID.

---

### Topic 4: Passive Interface and Network Type Mismatch Diagnosis

**Passive interface on transit link:** A passive interface receives OSPF's hello packets from neighbors but never sends its own. The interface is in the OSPF LSDB but no adjacency forms. The symptom is a missing neighbor entry on both sides.

```
R4# show ip ospf interface GigabitEthernet0/1
  GigabitEthernet0/1 is up, line protocol is up
  ...
  No Hellos (Passive interface)   ! ← transit link is passive — adjacency impossible
```

**Network type mismatch:** OSPF encodes the network type in hello packets. A point-to-point interface and a broadcast interface on the same link use different adjacency rules. On broadcast, DR/BDR election runs; on point-to-point, it does not. Mismatched types cause hello processing failures.

```
R2# show ip ospf interface GigabitEthernet0/2
  Network Type POINT_TO_POINT   ! ← R2 side is p2p

R6# show ip ospf interface GigabitEthernet0/0
  Network Type BROADCAST         ! ← R6 side is broadcast — MISMATCH
```

---

### Topic 5: Redistribution and External Route Diagnosis

When external routes are absent from all routing tables despite the ASBR being reachable:
1. Confirm the ASBR has `redistribute` configured: `show run | section router ospf`
2. Check the NSSA LSDB for Type 7 LSAs: `show ip ospf database nssa-external`
3. Check the backbone for Type 5 LSAs (translated by ABR): `show ip ospf database external`
4. If route-maps are referenced, confirm they exist: `show route-map`

An empty Type 7 LSDB on the ASBR confirms redistribution is not running, even if the ASBR is OSPF-adjacent.

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| Systematic OSPF troubleshooting | Apply a top-down diagnostic methodology to isolate OSPF faults |
| Hello/dead timer diagnosis | Identify and resolve timer mismatches between OSPF neighbors |
| Area ID mismatch resolution | Find and fix incorrect area assignments on ABR or internal router links |
| Passive interface identification | Distinguish passive-on-transit from passive-on-LAN in show output |
| Network type mismatch correction | Identify broadcast vs point-to-point inconsistency from show output |
| Redistribution diagnosis | Trace missing external routes from ASBR through LSDB to routing table |
| Concurrent fault management | Prioritize and sequence fixes across multiple simultaneous failures |
| OSPFv3 parallel diagnosis | Apply IPv4 troubleshooting patterns to OSPFv3 adjacency problems |

---

## 2. Topology & Scenario

**Enterprise Scenario:** Meridian Technologies has called you in to rescue their network after a change-management window went wrong. Five separate configuration changes were applied overnight, and the OSPF control plane is now severely degraded. PC1 cannot reach PC2, external ISP routes have vanished, and several adjacencies are down. Your task is to find all five faults and restore full OSPF convergence — no rollback available, diagnosis only.

```
                        ┌──────────────────────────┐
                        │           R1             │
                        │   (Area 0 — DR)          │
                        │   Lo0: 1.1.1.1/32        │
                        │   Lo0v6: 2001:DB8:FF::1  │
                        └────────────┬─────────────┘
                                     │ Gi0/0
                                     │ 10.0.123.1/24
                                     │
                           ┌─────────┴──────────┐
                           │     SW-AREA0        │
                           │  10.0.123.0/24      │
                           │  (broadcast/Area 0) │
                           └────┬───────────┬────┘
                   Gi0/0        │           │       Gi0/0
             10.0.123.2/24      │           │  10.0.123.3/24
              ┌─────────────────┘           └──────────────────┐
              │                                                 │
┌─────────────┴──────────────┐             ┌───────────────────┴──────────┐
│            R2              │             │            R3                │
│   (ABR Area 0/1 — BDR)     │             │   (ABR Area 0/2 — DROTHER)  │
│   Lo0: 2.2.2.2/32          │             │   Lo0: 3.3.3.3/32           │
└──────────┬────────┬────────┘             └───────────────┬─────────────┘
       Gi0/1│    Gi0/2│                                     │Gi0/1
  10.1.24.1/30│  10.1.26.1/30                           10.2.35.1/30│
              │        │                                             │
  10.1.24.2/30│  10.1.26.2/30                           10.2.35.2/30│
          Gi0/0│    Gi0/0│                                           │Gi0/0
┌─────────────┘    ┌─────┘                       ┌───────────────────┘
│  ┌───────────────┘                             │
│  │                                             │
│  │  10.1.46.1/30                               │
│  │  Gi0/1           Gi0/1 10.1.46.2/30         │
│  └──────────────────────────────┐              │
│                                 │              │
┌────────────────────┐   ┌────────┴───────────┐  ┌────────────────────────┐
│         R4         │   │        R6          │  │          R5            │
│ (Area 1 internal)  │   │ (Area 1 internal)  │  │  (Area 2 ASBR)         │
│ Lo0: 4.4.4.4/32    │   │ Lo0: 6.6.6.6/32   │  │  Lo0: 5.5.5.5/32      │
│ Lo1-4: 10.1.4-7/24 │   │                   │  │  Lo1: 172.16.5.0/24   │
└────────┬───────────┘   └───────────────────┘  │  Lo2: 172.16.6.0/24   │
     Gi0/2│ 192.168.1.1/24                       └────────┬───────────────┘
          │                                           Gi0/1│ 192.168.2.1/24
┌─────────┴──────────┐                           ┌────────┴───────────────┐
│        PC1         │                           │         PC2            │
│ 192.168.1.10/24    │                           │  192.168.2.10/24       │
└────────────────────┘                           └────────────────────────┘

Area 0: 10.0.123.0/24 (broadcast — DR/BDR election)
Area 1: Totally Stubby (R2 is ABR, no-summary)
Area 2: NSSA (R3 is ABR; R5 is ASBR)
```

---

## 3. Hardware & Environment Specifications

**Cabling Table**

| Link ID | Source | Source Interface | Target | Target Interface | Subnet | Area |
|---------|--------|-----------------|--------|-----------------|--------|------|
| L1 | R1 | Gi0/0 | SW-AREA0 | port1 | 10.0.123.0/24 | 0 |
| L2 | R2 | Gi0/0 | SW-AREA0 | port2 | 10.0.123.0/24 | 0 |
| L3 | R3 | Gi0/0 | SW-AREA0 | port3 | 10.0.123.0/24 | 0 |
| L4 | R2 | Gi0/1 | R4 | Gi0/0 | 10.1.24.0/30 | 1 |
| L5 | R3 | Gi0/1 | R5 | Gi0/0 | 10.2.35.0/30 | 2 |
| L6 | R4 | Gi0/2 | PC1 | e0 | 192.168.1.0/24 | 1 |
| L7 | R5 | Gi0/1 | PC2 | e0 | 192.168.2.0/24 | 2 |
| L8 | R2 | Gi0/2 | R6 | Gi0/0 | 10.1.26.0/30 | 1 |
| L9 | R4 | Gi0/1 | R6 | Gi0/1 | 10.1.46.0/30 | 1 |

**Console Access Table**

| Device | Port | Connection Command |
|--------|------|--------------------|
| R1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R3 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R4 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R5 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R6 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| PC1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| PC2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |

**Platform:** IOSv 15.9 (ios-classic) on EVE-NG

Run `python3 setup_lab.py --host <eve-ng-ip>` to push the pre-broken configuration to all routers. The lab starts in a degraded state — do not run `apply_solution.py` before beginning your diagnosis.

---

## 4. Base Configuration

The `setup_lab.py` script pushes a pre-broken OSPF configuration. The following is pre-configured:

**Pre-configured on all routers:**
- Hostnames, `no ip domain-lookup`, `ipv6 unicast-routing`
- Interface IP addresses (IPv4 and IPv6) with `no shutdown`
- OSPF process 1 with router-IDs on all routers
- Most OSPF network statements and area type declarations
- DR/BDR priority settings on Area 0 interfaces
- OSPFv3 address-family configuration (partial)
- R2: ABR summarization (`area 1 range`, `area 1 range not-advertise`)
- R5: prefix-lists, route-maps, ASBR `summary-address` command
- R1: distribute-list filtering (BLOCK_10_1_5 prefix-list)

**Five faults are pre-loaded — you must find and fix them all:**

- Something is wrong with the OSPF hello/dead timer configuration on at least one link
- At least one router has a link placed in the wrong OSPF area
- A transit interface may have been accidentally set to passive
- An interface may have the wrong OSPF network type configured
- External route redistribution may be absent from the ASBR

**Pre-configured on PC1/PC2 (VPC auto-load on boot):**
- PC1: `192.168.1.10/24`, gateway `192.168.1.1`, IPv6 `2001:db8:1:1::10/64`
- PC2: `192.168.2.10/24`, gateway `192.168.2.1`, IPv6 `2001:db8:2:2::10/64`

---

## 5. Lab Challenge: Comprehensive Troubleshooting

> This is a capstone lab. The network is pre-broken.
> Diagnose and resolve 5+ concurrent faults spanning all blueprint bullets.
> No step-by-step guidance is provided — work from symptoms only.

**Starting state after `setup_lab.py`:**
- Multiple OSPF adjacencies are down
- Area 1 may be partially or fully isolated
- Area 2 has no adjacency with the backbone
- External ISP routes are absent from all routing tables
- PC1 cannot reach PC2

**Your goal:** Restore the network to the following known-good state:

1. All OSPF adjacencies are FULL — R1-R2, R1-R3, R2-R3 (Area 0), R2-R4, R2-R6, R4-R6 (Area 1), R3-R5 (Area 2)
2. R1 is DR, R2 is BDR, R3 is DROTHER on the Area 0 broadcast segment
3. Area 1 is totally stubby — R4 and R6 receive only the default route
4. Area 2 is NSSA — R5 is ASBR with external routes redistributed
5. R2 summarizes Area 1 loopback prefixes into 10.1.4.0/22; suppresses 10.1.6.0/24
6. R5 summarizes external routes into 172.16.0.0/16 Type 7 (translated to Type 5 by R3)
7. R1 filters 10.1.5.0/24 from its local RIB using distribute-list
8. OSPFv3 adjacencies are FULL on all links
9. PC1 ↔ PC2 reachable over both IPv4 and IPv6

---

## 6. Verification & Analysis

Use these as your post-fix verification targets. The broken lab will not match these outputs — work toward them.

### All Adjacencies FULL

```
R1# show ip ospf neighbor

Neighbor ID     Pri   State           Dead Time   Address         Interface
2.2.2.2         200   FULL/BDR        00:00:38    10.0.123.2      GigabitEthernet0/0   ! ← R2 = BDR
3.3.3.3           0   FULL/DROTHER    00:00:39    10.0.123.3      GigabitEthernet0/0   ! ← R3 = DROTHER

R2# show ip ospf neighbor

Neighbor ID     Pri   State           Dead Time   Address         Interface
1.1.1.1         255   FULL/DR         00:00:36    10.0.123.1      GigabitEthernet0/0   ! ← R1 = DR
3.3.3.3           1   FULL/DROTHER    00:00:38    10.0.123.3      GigabitEthernet0/0
4.4.4.4           1   FULL/  -        00:00:38    10.1.24.2       GigabitEthernet0/1   ! ← R4: p2p adj restored
6.6.6.6           1   FULL/  -        00:00:39    10.1.26.2       GigabitEthernet0/2   ! ← R6: p2p adj restored

R3# show ip ospf neighbor

Neighbor ID     Pri   State           Dead Time   Address         Interface
1.1.1.1         255   FULL/DR         00:00:38    10.0.123.1      GigabitEthernet0/0
2.2.2.2         200   FULL/BDR        00:00:36    10.0.123.2      GigabitEthernet0/0
5.5.5.5           1   FULL/  -        00:00:38    10.2.35.2       GigabitEthernet0/1   ! ← R5 adj restored

R4# show ip ospf neighbor

Neighbor ID     Pri   State           Dead Time   Address         Interface
2.2.2.2           1   FULL/  -        00:00:38    10.1.24.1       GigabitEthernet0/0   ! ← R2 adj restored
6.6.6.6           1   FULL/  -        00:00:39    10.1.46.2       GigabitEthernet0/1   ! ← R6 adj restored
```

### Totally Stubby Area 1 (R4/R6 receive only default)

```
R4# show ip route ospf
Gateway of last resort is 10.1.24.1 to network 0.0.0.0

O*IA  0.0.0.0/0 [110/2] via 10.1.24.1, GigabitEthernet0/0   ! ← ONLY the default route
                                                               ! ← no other O IA entries

R4# show ip ospf database summary
! Only one Type 3 LSA: 0.0.0.0 from 2.2.2.2   ! ← confirms totally stubby
```

### External Routes Present (R5 redistribution restored)

```
R1# show ip route ospf | include 172.16
O E2  172.16.0.0/16 [110/20] via 10.0.123.3, GigabitEthernet0/0   ! ← single /16 summary

R5# show ip ospf database nssa-external
! Type 7 LSA for 172.16.0.0 present   ! ← redistribution working

R3# show ip ospf database external
! Type 5 LSA for 172.16.0.0 present   ! ← ABR translation working
```

### R3-R5 Adjacency (Area 2 restored)

```
R3# show ip ospf interface GigabitEthernet0/1
  Internet Address 10.2.35.1/30, Area 2, ...   ! ← must be Area 2, not Area 0
  Network Type POINT_TO_POINT, Cost: 1
  Neighbor Count is 1, Adjacent neighbor count is 1   ! ← R5 fully adjacent
```

### R2-R4 Adjacency (hello timers matched)

```
R2# show ip ospf interface GigabitEthernet0/1
  Timer intervals configured, Hello 5, Dead 20   ! ← must match R4 (5/20)
  Neighbor Count is 1, Adjacent neighbor count is 1

R4# show ip ospf interface GigabitEthernet0/0
  Timer intervals configured, Hello 5, Dead 20   ! ← same timers
```

### R4 Gi0/1 Not Passive (R4-R6 adjacency restored)

```
R4# show ip ospf interface GigabitEthernet0/1
  GigabitEthernet0/1 is up, line protocol is up
  ...
  No Hellos (Passive interface)   ! ← this must NOT appear
  Neighbor Count is 1, ...        ! ← R6 must be adjacent
```

### R6 Gi0/0 Network Type Corrected (R2-R6 adjacency restored)

```
R6# show ip ospf interface GigabitEthernet0/0
  Network Type POINT_TO_POINT   ! ← must be POINT_TO_POINT, not BROADCAST

R2# show ip ospf neighbor | include 6.6.6.6
6.6.6.6    1   FULL/  -   ...   GigabitEthernet0/2   ! ← R6 FULL on R2
```

### End-to-End Reachability

```
PC1> ping 192.168.2.10
84 bytes from 192.168.2.10 icmp_seq=1 ttl=60 time=X.X ms   ! ← IPv4 restored

PC1> ping 2001:db8:2:2::10
2001:db8:2:2::10 icmp6_seq=1 ttl=60 time=X.X ms   ! ← IPv6 restored
```

---

## 7. Verification Cheatsheet

### OSPF Neighbor and Interface State

```
show ip ospf neighbor
show ip ospf neighbor detail
show ip ospf interface <int>
show ip ospf interface brief
```

| Command | What to Look For |
|---------|-----------------|
| `show ip ospf neighbor` | State column — all should be FULL; anything else is a problem |
| `show ip ospf interface Gi0/X` | Area, Network Type, hello/dead timers, neighbor count, passive status |
| `show ip ospf interface brief` | Quick scan of all OSPF interfaces and their areas |

> **Exam tip:** `show ip ospf neighbor detail` shows the hello options field. If the area option flag differs (e.g., `E` bit for external routing), it indicates an area type mismatch between neighbors.

---

### OSPF LSDB Diagnosis

```
show ip ospf database
show ip ospf database summary
show ip ospf database external
show ip ospf database nssa-external
show ip ospf database router
```

| Command | What to Look For |
|---------|-----------------|
| `show ip ospf database` | LSA count per area/type — stub areas should have no Type 5 |
| `show ip ospf database nssa-external` | Type 7 LSAs on ASBR/ABR — empty means no redistribution |
| `show ip ospf database external` | Type 5 LSAs — should show translated 172.16.0.0/16 in Area 0 |
| `show ip ospf database summary` | Type 3 LSAs — only 0.0.0.0 should exist in totally stubby area |

---

### Route Table Verification

```
show ip route ospf
show ip route ospf | include O IA
show ip route ospf | include E2
show ipv6 route ospf
show ip route 0.0.0.0
```

| Command | What to Look For |
|---------|-----------------|
| `show ip route ospf` | Presence of all expected OSPF routes |
| `show ip route 172.16.0.0` | Must show O E2 with /16 mask (ASBR summary) |
| `show ip route 0.0.0.0` | Must be present on Area 1 routers (totally stubby default) |

---

### Area Type Verification

```
show ip ospf | include Area
show ip ospf interface | include Area
show run | section router ospf
```

| Command | What to Look For |
|---------|-----------------|
| `show ip ospf` | Area type listed for each area — "Stub, no summary" for totally stubby |
| `show run \| section router ospf` | Exact area type commands (`area N nssa`, `area N stub no-summary`) |

---

### Redistribution Diagnosis

```
show route-map
show ip ospf database nssa-external
show run | section router ospf | include redistribute
```

| Command | What to Look For |
|---------|-----------------|
| `show route-map` | Route-map exists and has matches — if missing, redistribution won't work |
| `show ip ospf database nssa-external` | Empty = ASBR not redistributing |
| `show run \| section router ospf` | `redistribute connected subnets route-map REDIST_EXT` must be present |

---

### OSPFv3 Diagnosis

```
show ospfv3 neighbor
show ospfv3 interface brief
show ospfv3 database
show ipv6 route ospf
```

| Command | What to Look For |
|---------|-----------------|
| `show ospfv3 neighbor` | Mirrors IPv4 adjacency state — all should be FULL |
| `show ospfv3 interface brief` | Which interfaces are in which OSPFv3 areas |

---

### Wildcard Mask Quick Reference

| Subnet Mask | Wildcard Mask | Common Use |
|-------------|---------------|------------|
| /32 | 0.0.0.0 | Loopback (host route) |
| /30 | 0.0.0.3 | Point-to-point link |
| /24 | 0.0.0.255 | Standard LAN |
| /22 | 0.0.3.255 | Summarization range (4 × /24) |
| /16 | 0.255.255.255 | ASBR summary range |

---

### Common OSPF Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| Neighbor stuck in INIT or absent | One-way hello; mismatched hello/dead timers; area ID mismatch |
| Neighbor stuck in EXSTART | MTU mismatch; duplicate router-ID |
| No adjacency despite interface up | Passive interface on transit link; network type mismatch |
| Type 5 LSAs missing from backbone | ASBR not redistributing; NSSA ABR missing Type 7→Type 5 translation |
| Area 1 shows full routing table instead of default | `area 1 stub no-summary` missing on ABR |
| No default route in Area 1 | Area 1 is normal (not stub), or ABR has no Area 0 adjacency |
| OSPFv3 down but OSPFv2 up | `ospfv3 pid ipv6 area N` missing on interface; wrong area in AF |

---

## 8. Solutions (Spoiler Alert!)

> Work through all five faults before reading the solutions!

### Fix 1: Hello/Dead Timer Mismatch on R2-R4 Link

<details>
<summary>Click to view the Fix</summary>

**Fault:** R2 GigabitEthernet0/1 was missing the custom hello/dead timers. R4 Gi0/0 has hello=5, dead=20. R2 was using defaults (hello=10, dead=40) — mismatch prevents adjacency.

```bash
! On R2:
configure terminal
interface GigabitEthernet0/1
 ip ospf hello-interval 5
 ip ospf dead-interval 20
end

! Verify:
R2# show ip ospf interface GigabitEthernet0/1
! Timer intervals configured, Hello 5, Dead 20
R2# show ip ospf neighbor | include 4.4.4.4
! 4.4.4.4  1  FULL/-  ...  GigabitEthernet0/1
```
</details>

---

### Fix 2: Area ID Mismatch on R3-R5 Link

<details>
<summary>Click to view the Fix</summary>

**Fault:** R3 GigabitEthernet0/1 was placed in Area 0 (both in the network statement and the ospfv3 interface command). R5 is in Area 2. Area mismatch → no adjacency.

```bash
! On R3:
configure terminal
router ospf 1
 no network 10.2.35.0 0.0.0.3 area 0
 network 10.2.35.0 0.0.0.3 area 2
exit
interface GigabitEthernet0/1
 no ospfv3 1 ipv6 area 0
 ospfv3 1 ipv6 area 2
end

! Verify:
R3# show ip ospf interface GigabitEthernet0/1
! Area 2 — confirmed
R3# show ip ospf neighbor | include 5.5.5.5
! 5.5.5.5  1  FULL/-  ...  GigabitEthernet0/1
```
</details>

---

### Fix 3: Passive Interface on R4 Transit Link (Gi0/1)

<details>
<summary>Click to view the Fix</summary>

**Fault:** R4 GigabitEthernet0/1 (link to R6) was set to passive, blocking hellos. R4-R6 adjacency was down.

```bash
! On R4:
configure terminal
router ospf 1
 no passive-interface GigabitEthernet0/1
exit
router ospfv3 1
 address-family ipv6 unicast
  no passive-interface GigabitEthernet0/1
 exit-address-family
end

! Verify:
R4# show ip ospf interface GigabitEthernet0/1
! "No Hellos (Passive interface)" must NOT appear
R4# show ip ospf neighbor | include 6.6.6.6
! 6.6.6.6  1  FULL/-  ...  GigabitEthernet0/1
```
</details>

---

### Fix 4: Network Type Mismatch on R6-R2 Link

<details>
<summary>Click to view the Fix</summary>

**Fault:** R6 GigabitEthernet0/0 (link to R2) was missing `ip ospf network point-to-point`, reverting to broadcast. R2 Gi0/2 was point-to-point. Type mismatch → no adjacency.

```bash
! On R6:
configure terminal
interface GigabitEthernet0/0
 ip ospf network point-to-point
end

! Verify:
R6# show ip ospf interface GigabitEthernet0/0
! Network Type POINT_TO_POINT
R2# show ip ospf neighbor | include 6.6.6.6
! 6.6.6.6  1  FULL/-  ...  GigabitEthernet0/2
```
</details>

---

### Fix 5: Missing Redistribution on R5

<details>
<summary>Click to view the Fix</summary>

**Fault:** R5's `redistribute connected subnets route-map REDIST_EXT` was removed from `router ospf 1`, and `redistribute connected route-map REDIST_EXT_V6` was removed from OSPFv3 address-family. External routes were not injected.

```bash
! On R5:
configure terminal
router ospf 1
 redistribute connected subnets route-map REDIST_EXT
exit
router ospfv3 1
 address-family ipv6 unicast
  redistribute connected route-map REDIST_EXT_V6
 exit-address-family
end

! Verify:
R5# show ip ospf database nssa-external
! Type 7 LSA for 172.16.0.0 present
R1# show ip route ospf | include 172.16
! O E2  172.16.0.0/16 ...
```
</details>

<details>
<summary>Click to view Complete Verification Commands</summary>

```bash
! Full adjacency check
show ip ospf neighbor
show ospfv3 neighbor

! Area type check
show ip ospf database summary        ! Area 1: only 0.0.0.0 LSA
show ip ospf database external       ! Area 0: 172.16.0.0/16 present
show ip ospf database nssa-external  ! Area 2: 172.16.0.0 Type 7 present

! Interface health
show ip ospf interface GigabitEthernet0/1   ! On R2: hello=5, dead=20
show ip ospf interface GigabitEthernet0/1   ! On R3: Area 2, not passive
show ip ospf interface GigabitEthernet0/0   ! On R6: POINT_TO_POINT

! Route tables
show ip route ospf                          ! On R4: only 0.0.0.0/0 default
show ip route ospf | include 172.16         ! On R1: O E2 172.16.0.0/16

! End-to-end
ping 192.168.2.10 source 192.168.1.1
ping 2001:db8:2:2::10 source 2001:db8:1:1::1
```
</details>

---

## 9. Troubleshooting Scenarios

The lab starts in the broken state after `setup_lab.py`. All five faults are active simultaneously. Work through them in any order — each fix below can also be practiced in isolation using the individual inject scripts.

### Workflow

```bash
python3 setup_lab.py --host <eve-ng-ip>                        # push broken state
python3 scripts/fault-injection/apply_solution.py --host ...   # restore after practice
python3 scripts/fault-injection/inject_scenario_01.py --host ...  # re-inject fault 1 only
```

---

### Ticket 1 — R4 and R2 Are Not OSPF Neighbors

The network team reports that R4 lost its OSPF neighbor relationship with R2 overnight. R4's neighbor table is empty on Gi0/0, and R2 shows no neighbor on Gi0/1. IP connectivity between the interfaces is confirmed (`ping 10.1.24.1` from R4 succeeds).

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py`

**Success criteria:** `show ip ospf neighbor` on R4 shows R2 (2.2.2.2) in FULL state on GigabitEthernet0/0.

<details>
<summary>Click to view Diagnosis Steps</summary>

```
R4# show ip ospf neighbor
! Empty — no neighbors

R4# show ip ospf interface GigabitEthernet0/0
! Check: Timer intervals configured, Hello 5, Dead 20
! Note the hello/dead timers on R4

R2# show ip ospf interface GigabitEthernet0/1
! Check: what timers does R2 report?
! If Hello 10, Dead 40 (defaults) → MISMATCH with R4's 5/20

! OSPF requires matching hello intervals between neighbors.
! R4 was custom-configured with 5s/20s. The R2 side lost those settings.
! IOS discards hellos with mismatched hello intervals during INIT processing.
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! On R2:
configure terminal
interface GigabitEthernet0/1
 ip ospf hello-interval 5
 ip ospf dead-interval 20
end

! Verify:
R2# show ip ospf neighbor
! 4.4.4.4  1  FULL/-  ...  GigabitEthernet0/1
```
</details>

---

### Ticket 2 — No Area 2 Routes in Any Area 0 Routing Table

R1, R2, and the Area 0 routers have lost all knowledge of 10.2.35.0/30, 5.5.5.5/32, and 192.168.2.0/24. R3's `show ip ospf neighbor` shows no entry for R5.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py`

**Success criteria:** `show ip ospf neighbor` on R3 shows R5 (5.5.5.5) in FULL state on GigabitEthernet0/1.

<details>
<summary>Click to view Diagnosis Steps</summary>

```
R3# show ip ospf neighbor
! R5 missing

R3# show ip ospf interface GigabitEthernet0/1
! Check: what Area does R3 report for Gi0/1?
! If Area 0 → that is wrong; R5 is in Area 2

R5# show ip ospf interface GigabitEthernet0/0
! Shows Area 2

! Area mismatch: R3 advertises Area 0 on Gi0/1, R5 expects Area 2.
! OSPF discards hellos from neighbors in a different area.

! Check R3's OSPF config:
R3# show run | section router ospf
! Look for: network 10.2.35.0 0.0.0.3 area X
! If X = 0 instead of 2 → that is the fault
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! On R3:
configure terminal
router ospf 1
 no network 10.2.35.0 0.0.0.3 area 0
 network 10.2.35.0 0.0.0.3 area 2
exit
interface GigabitEthernet0/1
 no ospfv3 1 ipv6 area 0
 ospfv3 1 ipv6 area 2
end

! Verify:
R3# show ip ospf neighbor | include 5.5.5.5
! 5.5.5.5  1  FULL/-  ...  GigabitEthernet0/1
```
</details>

---

### Ticket 3 — R4 and R6 Are Not OSPF Neighbors

R6 is reachable via R2 but shows no neighbor on GigabitEthernet0/1. R4 also shows no neighbor on Gi0/1. Pinging across the R4-R6 link works at Layer 3.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py`

**Success criteria:** `show ip ospf neighbor` on R4 shows R6 (6.6.6.6) in FULL state on GigabitEthernet0/1.

<details>
<summary>Click to view Diagnosis Steps</summary>

```
R4# show ip ospf neighbor
! R6 missing from neighbor table

R4# show ip ospf interface GigabitEthernet0/1
! Look for: "No Hellos (Passive interface)"
! If present → R4 Gi0/1 is passive; no hellos are sent

! A passive interface suppresses OSPF hellos outbound. The interface is still
! in the LSDB (advertised as a stub network) but no adjacency can form.
! Transit links should never be passive.

R4# show run | section router ospf
! Look for: passive-interface GigabitEthernet0/1
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! On R4:
configure terminal
router ospf 1
 no passive-interface GigabitEthernet0/1
exit
router ospfv3 1
 address-family ipv6 unicast
  no passive-interface GigabitEthernet0/1
 exit-address-family
end

! Verify:
R4# show ip ospf interface GigabitEthernet0/1
! "No Hellos (Passive interface)" must be absent
R4# show ip ospf neighbor | include 6.6.6.6
! 6.6.6.6  1  FULL/-  ...  GigabitEthernet0/1
```
</details>

---

### Ticket 4 — R6 and R2 Cannot Form an Adjacency

R6 shows no OSPF neighbor on GigabitEthernet0/0. R2 Gi0/2 shows no neighbor on R6. IP ping across 10.1.26.0/30 succeeds.

**Inject:** `python3 scripts/fault-injection/inject_scenario_04.py`

**Success criteria:** `show ip ospf neighbor` on R2 shows R6 (6.6.6.6) in FULL state on GigabitEthernet0/2.

<details>
<summary>Click to view Diagnosis Steps</summary>

```
R2# show ip ospf neighbor
! R6 missing from GigabitEthernet0/2

R2# show ip ospf interface GigabitEthernet0/2
! Network Type POINT_TO_POINT

R6# show ip ospf interface GigabitEthernet0/0
! Network Type BROADCAST  ← MISMATCH
! "Designated Router (ID) ..." — DR election is running on R6's side

! Network type is encoded in hello packets. POINT_TO_POINT and BROADCAST
! use different adjacency rules. IOS drops hellos from a neighbor with a
! different network type.

! On a broadcast segment, hellos are sent to 224.0.0.5 (all OSPF) and DR/BDR
! is elected. On point-to-point, hellos go directly to the neighbor's link-local
! without DR election. These two modes are incompatible.
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! On R6:
configure terminal
interface GigabitEthernet0/0
 ip ospf network point-to-point
end

! Verify:
R6# show ip ospf interface GigabitEthernet0/0
! Network Type POINT_TO_POINT
R2# show ip ospf neighbor | include 6.6.6.6
! 6.6.6.6  1  FULL/-  ...  GigabitEthernet0/2
```
</details>

---

### Ticket 5 — External ISP Routes Are Absent from All Routing Tables

R1, R2, and R3 all show no 172.16.x.x routes. R5 appears to have an adjacency with R3 (once Ticket 2 is fixed), but no external routes are being generated. PC1 cannot reach the simulated ISP networks.

**Inject:** `python3 scripts/fault-injection/inject_scenario_05.py`

**Success criteria:** `show ip route ospf` on R1 shows `O E2 172.16.0.0/16` via R3.

<details>
<summary>Click to view Diagnosis Steps</summary>

```
R1# show ip route ospf | include 172
! Empty — no external routes

R5# show ip ospf database nssa-external
! Empty — no Type 7 LSAs
! This means R5 is not generating external LSAs (redistribution is not running)

R5# show run | section router ospf
! Look for: redistribute connected subnets route-map REDIST_EXT
! If absent → redistribution was removed

R5# show route-map REDIST_EXT
! Route-map exists but is not referenced by redistribution command
! The route-map itself is not the problem — the redistribute statement is missing

! Without redistribute, R5 OSPF process generates no Type 7 LSAs for
! 172.16.5.0/24 or 172.16.6.0/24, even though the summary-address command
! is present. The summary has nothing to summarize.
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! On R5:
configure terminal
router ospf 1
 redistribute connected subnets route-map REDIST_EXT
exit
router ospfv3 1
 address-family ipv6 unicast
  redistribute connected route-map REDIST_EXT_V6
 exit-address-family
end

! Verify:
R5# show ip ospf database nssa-external
! Type 7 LSA for 172.16.0.0 now present

R1# show ip route ospf | include 172.16
! O E2  172.16.0.0/16 [110/20] via 10.0.123.3, GigabitEthernet0/0
```
</details>

---

## 10. Lab Completion Checklist

### Core Troubleshooting (All Faults Resolved)

- [ ] Fault 1 found and fixed: R2-R4 adjacency FULL (hello timers corrected on R2 Gi0/1)
- [ ] Fault 2 found and fixed: R3-R5 adjacency FULL (Area 2 restored on R3 Gi0/1)
- [ ] Fault 3 found and fixed: R4-R6 adjacency FULL (passive removed from R4 Gi0/1)
- [ ] Fault 4 found and fixed: R2-R6 adjacency FULL (point-to-point restored on R6 Gi0/0)
- [ ] Fault 5 found and fixed: External routes 172.16.0.0/16 visible in all areas
- [ ] All Area 0 adjacencies FULL (R1-R2, R1-R3, R2-R3)
- [ ] R4 and R6 show only O*IA 0.0.0.0/0 in routing table (totally stubby intact)
- [ ] 10.1.4.0/22 inter-area summary visible in Area 0 (R2 summarization intact)
- [ ] 10.1.5.0/24 absent from R1 routing table (distribute-list intact)
- [ ] OSPFv3 adjacencies FULL on all links
- [ ] PC1 to PC2 reachable over IPv4 and IPv6

### Individual Fault Practice (Optional)

- [ ] Ticket 1: Practiced hello timer mismatch in isolation
- [ ] Ticket 2: Practiced area ID mismatch in isolation
- [ ] Ticket 3: Practiced passive-on-transit in isolation
- [ ] Ticket 4: Practiced network type mismatch in isolation
- [ ] Ticket 5: Practiced missing redistribution in isolation
