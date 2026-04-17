# IP Services Lab 04 — Full Mastery Capstone I

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

**Exam Objectives:** 1.4 (QoS interpretation), 3.3.a (NTP), 3.3.b (NAT/PAT), 3.3.c (FHRP — VRRP) | Topic: IP Services

This is the configuration capstone for the IP Services topic. All four blueprint bullet areas — NTP, NAT/PAT, FHRP, and QoS — must be implemented from scratch on a clean topology. IP addressing and a pre-loaded QoS policy are the only pre-configured elements. You must build the complete IP services stack in one session, verifying each layer before proceeding to the next.

### Blueprint Coverage Summary

| Blueprint | Technology | Your Deliverable |
|-----------|-----------|-----------------|
| 3.3.a | NTP | R1 master (stratum 3), R2/R3 clients, MD5 auth key 1 |
| 3.3.b | NAT/PAT | Static NAT PC1→10.0.13.10, dynamic pool, PAT overload |
| 3.3.c | FHRP | VRRPv3 group 1 dual-stack, R1 Master, R2 Backup, tracking |
| 1.4 | QoS | Interpret pre-loaded LAN-OUT policy — class-maps, actions, policing |

### Recommended Build Order

A systematic build order prevents downstream failures (e.g., NAT testing needs OSPF reachability first):

1. **OSPFv2 + OSPFv3** — establish routing and reachability foundation
2. **NTP** — R1 master, R2/R3 clients with MD5 auth
3. **NAT/PAT** — NAT inside/outside, static, pool, PAT
4. **VRRPv3** — remove any residual FHRP, configure dual-stack VRRP
5. **Interface tracking** — link Gi0/1 line-protocol to VRRP group 1 IPv4
6. **QoS interpretation** — answer analysis questions on the pre-loaded policy
7. **End-to-end verification** — dual-stack, failover, NAT translations

### QoS Policy Analysis

A `policy-map LAN-OUT` is pre-loaded on R1 Gi0/1 (outbound). Before beginning configuration, study the policy with `show policy-map LAN-OUT` and answer the following:

- Which class receives a strict priority queue? What percentage of bandwidth?
- Which class uses CBWFQ with WRED? What is the minimum guaranteed bandwidth?
- What is the policing CIR for the SCAVENGER class? What happens to excess traffic?
- Which class handles traffic not matched by any other class?
- What DSCP value matches the VOICE class? The VIDEO class?

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| Full-stack IP services build | Configure NTP, NAT, FHRP, and OSPF in sequence from scratch |
| OSPFv2 + OSPFv3 dual-stack | Single OSPF process for both IPv4 and IPv6 |
| NTP authentication | MD5 key exchange between master and clients |
| NAT/PAT triage | Static → dynamic pool → PAT overload, correct interface mapping |
| VRRPv3 dual-stack | Address-family IPv4 and IPv6, tracking, failover |
| QoS interpretation | Read MQC policy-maps and identify class behaviors |

---

## 2. Topology & Scenario

**Scenario:** You have been handed a fresh topology with only IP addressing pre-configured. The network team requires the full IP services stack to be operational within a two-hour window. R1 is the primary LAN gateway (VRRP Master) and the NTP master. R3 is the simulated ISP router that hosts a public server at 203.0.113.1. Both PC1 and PC2 must reach R3's server through NAT on R1, and the virtual gateway must survive R1's uplink failure.

```
                    ┌─────────────────────────┐
                    │           R3            │
                    │   Upstream / ISP Router │
                    │   Lo0: 3.3.3.3/32       │
                    │   Lo1: 203.0.113.1/24   │
                    └──────┬───────────┬──────┘
           Gi0/0           │           │           Gi0/1
     10.0.13.2/30          │           │     10.0.23.2/30
                           │           │
     10.0.13.1/30          │           │     10.0.23.1/30
           Gi0/1           │           │           Gi0/1
     ┌─────────────────────┘           └─────────────────────┐
     │                                                       │
┌────┴──────────────────────┐     ┌──────────────────────────┴────┐
│            R1             │     │              R2               │
│  Primary Gateway          │     │  Secondary Gateway            │
│  NTP Master (Str 3)       │     │  NTP Client                   │
│  NAT/PAT Inside           │─────│  Lo0: 2.2.2.2/32             │
│  Lo0: 1.1.1.1/32          │Gi0/2│  Gi0/0: 192.168.1.3/24       │
│  Gi0/0: 192.168.1.2/24    │.1↔.2│                               │
└──────────────┬────────────┘     └────────────────┬─────────────┘
         Gi0/0 │                                   │ Gi0/0
               └──────────────┬────────────────────┘
                               │
                        ┌──────┴──────┐
                        │   SW-LAN    │
                        └──┬───────┬──┘
                           │       │
                    ┌──────┴──┐ ┌──┴──────┐
                    │  PC1    │ │  PC2    │
                    │.10/24   │ │.20/24   │
                    └─────────┘ └─────────┘

Build targets: OSPFv2+v3 | NTP MD5 | NAT/PAT | VRRPv3 group 1 dual-stack
VIP (to build): 192.168.1.1 (IPv4) | 2001:DB8:1:1::1 (IPv6)
```

---

## 3. Hardware & Environment Specifications

**Cabling Table:**

| Link | Source Device | Source Interface | Target Device | Target Interface | Subnet |
|------|---------------|-----------------|---------------|-----------------|--------|
| L1 | R1 | GigabitEthernet0/0 | SW-LAN | port1 | 192.168.1.0/24 |
| L2 | R2 | GigabitEthernet0/0 | SW-LAN | port2 | 192.168.1.0/24 |
| L3 | PC1 | e0 | SW-LAN | port3 | 192.168.1.0/24 |
| L4 | PC2 | e0 | SW-LAN | port4 | 192.168.1.0/24 |
| L5 | R1 | GigabitEthernet0/1 | R3 | GigabitEthernet0/0 | 10.0.13.0/30 |
| L6 | R2 | GigabitEthernet0/1 | R3 | GigabitEthernet0/1 | 10.0.23.0/30 |
| L7 | R1 | GigabitEthernet0/2 | R2 | GigabitEthernet0/2 | 10.0.12.0/30 |

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

The following is pre-loaded in `initial-configs/`:

**Pre-configured:**
- Hostnames, `no ip domain-lookup`
- `ipv6 unicast-routing` on all routers
- IPv4 and IPv6 addressing on all interfaces (dual-stack)
- QoS MQC policy `LAN-OUT` on R1 Gi0/1 outbound (for interpretation only)

**NOT pre-configured (student builds everything):**
- OSPF routing process (OSPFv2 or OSPFv3)
- NTP master, client, and MD5 authentication
- NAT inside/outside interface designations
- NAT/PAT rules (static, dynamic pool, PAT overload)
- FHRP (no HSRP or VRRP)
- Interface tracking objects
- `fhrp version vrrp v3`

---

## 5. Lab Challenge: Full Protocol Mastery

> This is a capstone lab. No step-by-step guidance is provided.
> Configure the complete IP Services solution from scratch — IP addressing is pre-configured; everything else is yours to build.
> All blueprint bullets for this chapter must be addressed.

**Required end-state:**

| Component | Requirement |
|-----------|------------|
| OSPFv2 | All routers in area 0. Router IDs match loopback IPs. Loopbacks + uplinks + LAN interfaces participating. Passive-interface default with exceptions for active links. |
| OSPFv3 | Same router IDs. All interfaces with IPv6 addresses in area 0. |
| NTP | R1 master at stratum 3. R2 and R3 sync to R1. MD5 authentication key 1 (key-string `NTP_KEY_1`). All routers authenticate. |
| NAT — Static | PC1 (192.168.1.10) mapped one-to-one to 10.0.13.10. |
| NAT — Dynamic | PC2 (192.168.1.20) translated via pool NAT-POOL (10.0.13.100–110). |
| PAT | All 192.168.1.0/24 hosts overloaded on R1 Gi0/1 IP. |
| VRRPv3 | Group 1 IPv4 VIP 192.168.1.1. Group 1 IPv6 VIP 2001:DB8:1:1::1. R1 priority 110, R2 priority 100. Preemption enabled. |
| Interface Tracking | Track 1 monitors R1 Gi0/1 line-protocol. Decrement 20 applied to VRRP group 1 IPv4. |
| QoS | Pre-loaded — interpret only. Answer analysis questions in Section 1. |
| Reachability | PC1 and PC2 reach 203.0.113.1 via IPv4/NAT. IPv6 reachability via virtual gateway. VRRP failover works on R1 uplink loss. |

**Verification gates — work through these in order:**

1. `show ip ospf neighbor` — R1 must have 2 neighbors (R2, R3). Same for R2 (R1, R3) and R3 (R1, R2).
2. `show ntp associations detail` on R2 and R3 — must show `sys.peer` for 1.1.1.1.
3. `show ip nat translations` — after pinging 203.0.113.1 from PC1 and PC2.
4. `show vrrp brief` — R1 Master, R2 Backup, both AFs.
5. `show track 1` — Up, linked to VRRP group 1 IPv4.
6. Failover test — shut R1 Gi0/1, verify R2 becomes Master, restore.

---

## 6. Verification & Analysis

### OSPF Adjacencies

```
R1# show ip ospf neighbor
Neighbor ID     Pri   State       Dead Time   Address         Interface
2.2.2.2           1   FULL/DR     00:00:31    192.168.1.3     GigabitEthernet0/0  ! ← R2 via LAN
3.3.3.3           1   FULL/BDR    00:00:38    10.0.13.2       GigabitEthernet0/1  ! ← R3 via uplink
2.2.2.2           1   FULL/  -    00:00:33    10.0.12.2       GigabitEthernet0/2  ! ← R2 direct

R3# show ipv6 ospf neighbor
OSPFv3 Router with ID (3.3.3.3) (Process ID 1)
Neighbor ID     Pri   State       Dead Time   Interface ID    Interface
1.1.1.1           1   FULL/  -    00:00:36    4               GigabitEthernet0/0  ! ← R1 via uplink
2.2.2.2           1   FULL/  -    00:00:35    4               GigabitEthernet0/1  ! ← R2 via uplink
```

### NTP Synchronization

```
R2# show ntp associations
      address         ref clock       st   when   poll reach  delay  offset   disp
*~1.1.1.1            127.127.1.1      3     56     64   377   0.500   0.123  0.189  ! ← * = synced, ~ = configured
 * sys.peer, # selected, + candidate, - outlyer, x falseticker, ~ configured

R2# show ntp status
Clock is synchronized, stratum 4, reference is 1.1.1.1                           ! ← stratum 4 (R1 is 3)
```

### NAT Translations

```
R1# show ip nat translations
Pro Inside global      Inside local       Outside local      Outside global
--- 10.0.13.10         192.168.1.10       ---                ---             ! ← static for PC1
tcp 10.0.13.10:1024    192.168.1.10:1024  203.0.113.1:80     203.0.113.1:80 ! ← static entry for active session
tcp 10.0.13.100:2048   192.168.1.20:2048  203.0.113.1:80     203.0.113.1:80 ! ← dynamic pool for PC2
```

### VRRPv3 State

```
R1# show vrrp brief
Interface   Grp  A-F   Pri Time  Own Pre State   Master addr/Group addr
Gi0/0         1  IPv4  110  3609   N   P Master  192.168.1.2    192.168.1.1     ! ← R1 is Master IPv4
Gi0/0         1  IPv6  110  3609   N   P Master  FE80::1        2001:DB8:1:1::1  ! ← R1 is Master IPv6

R2# show vrrp brief
Gi0/0         1  IPv4  100  3609   N   P Backup  192.168.1.2    192.168.1.1     ! ← R2 Backup; Master=R1
Gi0/0         1  IPv6  100  3609   N   P Backup  FE80::1        2001:DB8:1:1::1
```

---

## 7. Verification Cheatsheet

### OSPFv2 Configuration

```
router ospf 1
 router-id <loopback-ip>
 passive-interface default
 no passive-interface <active-link>

interface <X>
 ip ospf 1 area 0
```

| Command | Purpose |
|---------|---------|
| `show ip ospf neighbor` | Verify adjacency states — must be FULL |
| `show ip ospf interface brief` | Check passive status and Hello/Dead intervals |
| `show ip route ospf` | Verify O-learned routes |

### OSPFv3 Configuration

```
ipv6 router ospf 1
 router-id <same-as-ospfv2>
 passive-interface default
 no passive-interface <active-link>

interface <X>
 ipv6 ospf 1 area 0
```

| Command | Purpose |
|---------|---------|
| `show ipv6 ospf neighbor` | IPv6 adjacency state |
| `show ipv6 route ospf` | OSPFv3 IPv6 routes |

> **Exam tip:** OSPFv3 on IOS still uses a router-id — it must be explicitly set if no IPv4 address exists. Use the loopback IPv4 address as the router-id even in IPv6-only scenarios.

### NTP Configuration

```
! Master
ntp authentication-key 1 md5 <key-string>
ntp authenticate
ntp trusted-key 1
ntp master <stratum>

! Client
ntp authentication-key 1 md5 <key-string>
ntp authenticate
ntp trusted-key 1
ntp server <master-ip> key 1
```

| Command | Purpose |
|---------|---------|
| `show ntp status` | Clock sync status and stratum |
| `show ntp associations` | Peer table — `*` = synced peer |

### NAT/PAT Configuration

```
interface <inside>
 ip nat inside
interface <outside>
 ip nat outside

ip nat inside source static <local> <global>
ip access-list standard <ACL> / permit <range>
ip nat pool <name> <start> <end> netmask <mask>
ip nat inside source list <ACL> pool <name>
ip nat inside source list <ACL> interface <outside-int> overload
```

| Command | Purpose |
|---------|---------|
| `show ip nat translations` | Active translation table |
| `show ip nat statistics` | Hit/miss counters |
| `clear ip nat translation *` | Flush dynamic translations |

> **Exam tip:** Static NAT takes priority over dynamic/PAT. The processing order is: static → dynamic pool → PAT overload. A static entry for PC1 always wins.

### VRRPv3 Configuration

```
fhrp version vrrp v3

interface <LAN>
 vrrp 1 address-family ipv4
  address <vip> primary
  priority <value>
  preempt
  track <obj> decrement <n>
 vrrp 1 address-family ipv6
  address <ipv6-vip> primary
  priority <value>
  preempt
```

| Command | Purpose |
|---------|---------|
| `show vrrp brief` | State, priority, VIP per group/AF |
| `show vrrp` | Timers, virtual MAC, track, Master Down Interval |
| `show track <n>` | Tracked object state |

### Verification Commands

| Command | What to Look For |
|---------|-----------------|
| `show ip ospf neighbor` | All neighbors in FULL state |
| `show ntp associations` | `*` on configured server entry |
| `show ip nat translations` | Static entry + dynamic entries after test ping |
| `show vrrp brief` | R1 Master, R2 Backup for both AFs |
| `show track 1` | Up, linked to VRRP group 1 IPv4 |
| `show policy-map interface Gi0/1` | QoS statistics per class |

### Common Capstone Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| No OSPF adjacencies | Passive-interface on wrong interfaces; mismatched areas |
| NTP not syncing | MD5 key mismatch; wrong server IP; no `ntp trusted-key` |
| No NAT translations | Inside/outside on wrong interfaces; ACL not matching source range |
| VRRP commands rejected | `fhrp version vrrp v3` missing globally |
| VRRP failover not working | Track decrement ≤ priority gap (must be > 10) |
| IPv6 hosts lose gateway on failover | IPv6 AF missing on R2's VRRP config |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### OSPFv2 + OSPFv3

<details>
<summary>Click to view R1 OSPF Configuration</summary>

```bash
! R1
interface Loopback0
 ip ospf 1 area 0
 ipv6 ospf 1 area 0
interface GigabitEthernet0/0
 ip ospf 1 area 0
 ipv6 ospf 1 area 0
interface GigabitEthernet0/1
 ip ospf 1 area 0
 ipv6 ospf 1 area 0
interface GigabitEthernet0/2
 ip ospf 1 area 0
 ipv6 ospf 1 area 0
!
router ospf 1
 router-id 1.1.1.1
 passive-interface default
 no passive-interface GigabitEthernet0/0
 no passive-interface GigabitEthernet0/1
 no passive-interface GigabitEthernet0/2
!
ipv6 router ospf 1
 router-id 1.1.1.1
 passive-interface default
 no passive-interface GigabitEthernet0/0
 no passive-interface GigabitEthernet0/1
 no passive-interface GigabitEthernet0/2
```
</details>

### NTP

<details>
<summary>Click to view R1 NTP Configuration (Master)</summary>

```bash
ntp authentication-key 1 md5 NTP_KEY_1
ntp authenticate
ntp trusted-key 1
ntp master 3
```
</details>

<details>
<summary>Click to view R2 / R3 NTP Configuration (Client)</summary>

```bash
ntp authentication-key 1 md5 NTP_KEY_1
ntp authenticate
ntp trusted-key 1
ntp server 1.1.1.1 key 1
```
</details>

### NAT/PAT

<details>
<summary>Click to view R1 NAT Configuration</summary>

```bash
interface GigabitEthernet0/0
 ip nat inside
interface GigabitEthernet0/1
 ip nat outside
!
ip nat inside source static 192.168.1.10 10.0.13.10
!
ip access-list standard NAT-DYNAMIC
 permit host 192.168.1.20
ip nat pool NAT-POOL 10.0.13.100 10.0.13.110 netmask 255.255.255.0
ip nat inside source list NAT-DYNAMIC pool NAT-POOL
!
ip access-list standard NAT-PAT
 permit 192.168.1.0 0.0.0.255
ip nat inside source list NAT-PAT interface GigabitEthernet0/1 overload
```
</details>

### VRRPv3 + Tracking

<details>
<summary>Click to view R1 VRRPv3 Configuration</summary>

```bash
fhrp version vrrp v3
!
track 1 interface GigabitEthernet0/1 line-protocol
!
interface GigabitEthernet0/0
 vrrp 1 address-family ipv4
  address 192.168.1.1 primary
  priority 110
  preempt
  track 1 decrement 20
 vrrp 1 address-family ipv6
  address 2001:DB8:1:1::1 primary
  priority 110
  preempt
```
</details>

<details>
<summary>Click to view R2 VRRPv3 Configuration</summary>

```bash
fhrp version vrrp v3
!
interface GigabitEthernet0/0
 vrrp 1 address-family ipv4
  address 192.168.1.1 primary
  priority 100
  preempt
 vrrp 1 address-family ipv6
  address 2001:DB8:1:1::1 primary
  priority 100
  preempt
```
</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. Inject the fault first, then diagnose and fix using only show commands.

### Workflow

```bash
python3 setup_lab.py                                    # reset to initial-configs
python3 scripts/fault-injection/apply_solution.py       # apply known-good solution first
python3 scripts/fault-injection/inject_scenario_01.py   # Ticket 1
python3 scripts/fault-injection/apply_solution.py       # restore before next ticket
```

---

### Ticket 1 — R2 and R3 Have No Routes to R1's Networks

The NOC has reported that R2 and R3 cannot reach R1's Loopback or LAN networks. NTP clients (R2, R3) have also fallen out of sync. Routing is the likely root cause.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py`

**Success criteria:** `show ip ospf neighbor` on R1 shows FULL adjacencies with R2 and R3. `show ip route` on R2 and R3 shows O-learned routes for R1's networks.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! Step 1 — check OSPF adjacencies on R1
R1# show ip ospf neighbor
! If empty, R1 has no adjacencies

! Step 2 — check OSPF interface state
R1# show ip ospf interface brief
! Look for "PASSIVE" in State column on Gi0/0, Gi0/1, Gi0/2
! If all active interfaces are passive, Hello exchange is blocked

! Step 3 — confirm running config
R1# show running-config | section ospf
! Look for explicit 'passive-interface GigabitEthernetX' on active interfaces
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
R1# configure terminal
R1(config)# router ospf 1
R1(config-router)# no passive-interface GigabitEthernet0/0
R1(config-router)# no passive-interface GigabitEthernet0/1
R1(config-router)# no passive-interface GigabitEthernet0/2
R1(config-router)# end
R1# show ip ospf neighbor   ! confirm FULL adjacencies return
```
</details>

---

### Ticket 2 — PC1 and PC2 Cannot Reach 203.0.113.1

Internet connectivity has been lost for all LAN hosts. OSPF is up and routers can ping each other, but PC1 and PC2 get no response from the external server. `show ip nat translations` is empty.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py`

**Success criteria:** PC1 and PC2 can ping 203.0.113.1. `show ip nat translations` shows active translations. `show ip interface Gi0/0` shows `NAT: inside`.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! Step 1 — check NAT interface designations
R1# show ip interface GigabitEthernet0/0
! Look for "Inbound access list is not set" area — check for "NAT: inside" or "NAT: outside"

R1# show ip interface GigabitEthernet0/1
! Gi0/1 should say "NAT: outside" — if it says "inside", reversed

! Step 2 — check running config
R1# show running-config | include nat
! 'ip nat inside' should appear under Gi0/0
! 'ip nat outside' should appear under Gi0/1

! Step 3 — attempt test ping to confirm fault
PC1> ping 203.0.113.1
! Should fail if NAT is reversed
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
R1# configure terminal
R1(config)# interface GigabitEthernet0/0
R1(config-if)# no ip nat outside
R1(config-if)# ip nat inside
R1(config-if)# interface GigabitEthernet0/1
R1(config-if)# no ip nat inside
R1(config-if)# ip nat outside
R1(config-if)# end
R1# clear ip nat translation *
R1# show ip nat translations   ! confirm entries appear after test ping
```
</details>

---

### Ticket 3 — R2 Is Unexpectedly the VRRP Master

A network engineer configured VRRP and reports that R2 is the Master for group 1 even though R1 should be the primary router. Both routers are up and connected. The engineer confirms preemption is enabled.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py`

**Success criteria:** `show vrrp brief` on R1 shows Master for group 1 IPv4 at priority 110. R2 shows Backup at priority 100.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! Step 1 — check VRRP priority on R1
R1# show vrrp brief
! Look at Pri column for group 1 IPv4
! If R1 shows 100 (same as R2), equal-priority election is happening

! Step 2 — when priorities are equal, highest real IP wins
! R2 Gi0/0 = 192.168.1.3, R1 Gi0/0 = 192.168.1.2
! .3 > .2, so R2 wins — this is the election tiebreaker

! Step 3 — confirm intended priority in design
! R1 should have priority 110 per design spec (baseline.yaml)
R1# show running-config interface GigabitEthernet0/0
! Check 'priority' line under vrrp 1 address-family ipv4
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
R1# configure terminal
R1(config)# interface GigabitEthernet0/0
R1(config-if)# vrrp 1 address-family ipv4
R1(config-if-vrrp)# priority 110
R1(config-if-vrrp)# end
R1# show vrrp brief   ! R1 should become Master
```
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] OSPFv2 operational — all routers show FULL adjacencies (`show ip ospf neighbor`)
- [ ] OSPFv3 operational — IPv6 adjacencies full on all active interfaces
- [ ] All routers learn remote networks via OSPF (`show ip route ospf`)
- [ ] R1 configured as NTP master at stratum 3 (`ntp master 3`)
- [ ] R2 and R3 sync to R1 with MD5 authentication key 1 (`show ntp associations`)
- [ ] R1 Gi0/0 = NAT inside, Gi0/1 = NAT outside
- [ ] Static NAT: PC1 (192.168.1.10) → 10.0.13.10 in translation table
- [ ] Dynamic NAT pool: PC2 translation uses 10.0.13.100–110 range
- [ ] PAT overload: remaining hosts use Gi0/1 IP with port multiplexing
- [ ] `fhrp version vrrp v3` on R1 and R2
- [ ] VRRPv3 group 1 IPv4 VIP 192.168.1.1 — R1 Master (110), R2 Backup (100)
- [ ] VRRPv3 group 1 IPv6 VIP 2001:DB8:1:1::1 — R1 Master (110), R2 Backup (100)
- [ ] Track 1 monitors R1 Gi0/1 line-protocol with decrement 20 on VRRP IPv4
- [ ] VRRP failover verified: R1 uplink down → R2 becomes Master
- [ ] VRRP preemption verified: R1 uplink restored → R1 reclaims Master
- [ ] PC1 and PC2 reach 203.0.113.1 via NAT/VRRPv3 gateway
- [ ] QoS policy analysis answers completed (Section 1 questions)

### Troubleshooting

- [ ] Ticket 1 resolved: R1 OSPF adjacencies restored (passive-interface removed)
- [ ] Ticket 2 resolved: NAT inside/outside corrected on R1
- [ ] Ticket 3 resolved: R1 VRRP priority restored to 110
