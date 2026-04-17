# IP Services Lab 02: HSRP — First Hop Redundancy

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

**Exam Objective:** 3.3.c — Configure first hop redundancy protocols, such as HSRP, VRRP (CCNP ENCOR 350-401, IP Services)

End-hosts need a default gateway to reach destinations outside their subnet. A single physical gateway is a single point of failure — if it goes down, every host on the LAN loses connectivity instantly. First Hop Redundancy Protocols (FHRPs) solve this by presenting a single virtual IP and virtual MAC address that two or more routers share. When the active router fails, the standby takes over the virtual address with minimal interruption.

HSRP (Hot Standby Router Protocol) is Cisco-proprietary and the most widely deployed FHRP in enterprise networks. This lab configures HSRPv2 for both IPv4 and IPv6 gateway redundancy, and introduces interface tracking to drive automatic failover based on uplink health.

### HSRP Roles and Virtual MAC

HSRP defines two primary roles on a LAN segment:

| Role | Description |
|------|-------------|
| **Active** | Owns the virtual IP and virtual MAC; forwards all traffic from hosts pointing to the VIP |
| **Standby** | Monitors the Active router; takes over if the Active stops sending hellos |
| **Listen** | Any other HSRP-enabled router aware of the group but neither Active nor Standby |

The virtual MAC address is derived from the HSRP group number:
- HSRPv1: `0000.0C07.AC<group>` (e.g., group 1 = `0000.0C07.AC01`)
- HSRPv2: `0000.0C9F.F<group>` (e.g., group 1 = `0000.0C9F.F001`)

Hosts ARP for the virtual IP and cache the virtual MAC. During failover, the new Active router sends a Gratuitous ARP with the same virtual MAC, overwriting the switch's CAM table so traffic reroutes without host reconfiguration.

### Priority and Election

The Active router is elected based on **priority** (default 100). Higher value wins. If two routers have equal priority, the one with the higher interface IP wins.

```
standby 1 priority 110   ! R1 wins election (110 > 100)
```

Priority can be changed at any time. However, changing priority does **not** immediately trigger a role change unless **preemption** is enabled.

### Preemption

Without preemption, the first router to reach the Active state holds it indefinitely — even if a higher-priority router comes online later. Preemption allows the higher-priority router to forcibly reclaim the Active role:

```
standby 1 preempt
```

> **Exam tip:** Preemption is **not enabled by default** in HSRP. Always configure it explicitly on the higher-priority router so failback is automatic after recovery.

### Interface Tracking and Object Tracking

Interface tracking links HSRP priority to the health of an upstream interface. If the tracked interface goes down, the router decrements its HSRP priority. If the decrement causes the priority to fall below the standby router's priority (and preempt is configured), the standby takes over.

```
track 1 interface GigabitEthernet0/1 line-protocol
standby 1 track 1 decrement 20
```

The decrement must exceed the difference between the two routers' priorities. With R1 at 110 and R2 at 100, a decrement of at least 11 is needed to trigger failover. A value of 20 provides a safe margin.

### HSRPv2 vs HSRPv1

| Feature | HSRPv1 | HSRPv2 |
|---------|--------|--------|
| Group range | 0–255 | 0–4095 |
| Virtual MAC | `0000.0C07.AC<group>` | `0000.0C9F.F<group>` |
| IPv6 support | No | Yes |
| Multicast address | 224.0.0.2 | 224.0.0.102 |
| Millisecond timers | No | Yes |

HSRPv2 is required for IPv6 gateway redundancy. Both versions cannot coexist in the same group on the same interface.

### HSRP for IPv6

HSRPv2 supports IPv6 virtual addresses. The IPv6 group is configured separately from the IPv4 group and uses its own priority and preempt settings:

```
standby version 2
standby 2 ipv6 2001:DB8:1:1::1/64
standby 2 priority 110
standby 2 preempt
```

Hosts use the virtual IPv6 address as their default gateway, providing the same redundancy behavior as the IPv4 group.

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| HSRPv2 configuration | Configuring Active/Standby roles with explicit priority and preemption |
| Dual-stack IPv6 | Adding IPv6 addresses to all interfaces and enabling ipv6 unicast-routing |
| OSPFv3 | Extending OSPF to carry IPv6 prefixes alongside IPv4 |
| Interface tracking | Linking HSRP priority to uplink health via object tracking |
| Failover simulation | Testing HSRP failover by taking down the tracked interface |
| HSRP IPv6 group | Configuring a second HSRP group for IPv6 gateway redundancy |
| HSRP verification | Reading show standby outputs to confirm roles, VIP, and virtual MAC |

---

## 2. Topology & Scenario

```
                    ┌─────────────────────────┐
                    │           R3            │
                    │   (Upstream / ISP)      │
                    │   Lo0: 3.3.3.3          │
                    │   Lo1: 203.0.113.1/24   │
                    └──────┬───────────┬──────┘
           Gi0/0           │           │           Gi0/1
     10.0.13.2/30          │           │     10.0.23.2/30
                           │           │
     10.0.13.1/30          │           │     10.0.23.1/30
           Gi0/1           │           │           Gi0/1
     ┌─────────────────────┘           └──────────────────────┐
     │                                                        │
┌────┴──────────────────┐           ┌───────────────────────┴────┐
│          R1           │           │           R2               │
│  (HSRP Active)        │           │   (HSRP Standby)           │
│  Priority: 110        │           │   Priority: 100            │
│  Tracks: Gi0/1        │           │   Lo0: 2.2.2.2             │
│  Lo0: 1.1.1.1         │           └───────────────────────┬────┘
└──────────┬────────────┘                                   │
     Gi0/0 │ 192.168.1.2/24                   192.168.1.3/24│ Gi0/0
           │                                               │
           └───────────────┐              ┌────────────────┘
                    ┌──────┴──────────────┴──────┐
                    │          SW-LAN             │
                    │    (Unmanaged Switch)        │
                    │   VIP: 192.168.1.1 (HSRP)   │
                    └──────┬──────────────┬───────┘
                           │              │
              192.168.1.10 │              │ 192.168.1.20
            GW: 192.168.1.1│              │GW: 192.168.1.1
                     ┌─────┴────┐   ┌────┴─────┐
                     │   PC1    │   │   PC2    │
                     │ (VPC)    │   │  (VPC)   │
                     └──────────┘   └──────────┘
```

**Scenario:** Meridian Financial's network team has deployed R1 as the LAN gateway and R2 as a backup path to R3. Currently, if R1's uplink fails, all LAN traffic stops because PC1 and PC2 have a static default gateway pointing to R1's physical IP. Your task is to configure HSRPv2 on R1 and R2 so they share a virtual gateway IP, configure interface tracking on R1 so automatic failover occurs when R1's uplink goes down, and extend the redundancy to IPv6 as dual-stack is introduced.

---

## 3. Hardware & Environment Specifications

**Cabling Table:**

| Link | Device A | Interface | Device B | Interface | Subnet |
|------|----------|-----------|----------|-----------|--------|
| L1 | R1 | Gi0/0 | SW-LAN | port1 | 192.168.1.0/24 |
| L2 | R2 | Gi0/0 | SW-LAN | port2 | 192.168.1.0/24 |
| L3 | PC1 | e0 | SW-LAN | port3 | 192.168.1.0/24 |
| L4 | PC2 | e0 | SW-LAN | port4 | 192.168.1.0/24 |
| L5 | R1 | Gi0/1 | R3 | Gi0/0 | 10.0.13.0/30 |
| L6 | R2 | Gi0/1 | R3 | Gi0/1 | 10.0.23.0/30 |
| L7 | R1 | Gi0/2 | R2 | Gi0/2 | 10.0.12.0/30 |

**IPv6 Addressing (introduced this lab):**

| Device | Interface | IPv6 Address | Link-Local |
|--------|-----------|-------------|------------|
| R1 | Gi0/0 | 2001:DB8:1:1::2/64 | FE80::1 |
| R1 | Gi0/1 | 2001:DB8:13::1/64 | FE80::1 |
| R1 | Gi0/2 | 2001:DB8:12::1/64 | FE80::1 |
| R2 | Gi0/0 | 2001:DB8:1:1::3/64 | FE80::2 |
| R2 | Gi0/1 | 2001:DB8:23::1/64 | FE80::2 |
| R2 | Gi0/2 | 2001:DB8:12::2/64 | FE80::2 |
| R3 | Gi0/0 | 2001:DB8:13::2/64 | FE80::3 |
| R3 | Gi0/1 | 2001:DB8:23::2/64 | FE80::3 |
| PC1 | e0 | 2001:DB8:1:1::10/64 | — |
| PC2 | e0 | 2001:DB8:1:1::20/64 | — |
| HSRP group 2 | VIP | 2001:DB8:1:1::1 | — |

**Console Access Table:**

| Device | Port | Connection Command |
|--------|------|--------------------|
| R1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R3 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |

---

## 4. Base Configuration

The following is pre-configured in `initial-configs/` (chained from Lab 01 solutions):

**Pre-loaded on all routers:**
- Hostname, `no ip domain-lookup`
- Full IPv4 addressing (all interfaces)
- OSPF process 1 (area 0, all interfaces)
- NTP (R1 as master, R2/R3 as clients with MD5 auth)
- Console/VTY lines

**Pre-loaded on R1 only:**
- QoS MQC (LAN-OUT policy on Gi0/1)
- NAT inside/outside, static NAT for PC1, dynamic pool, PAT overload

**NOT pre-configured (student builds these):**
- `ipv6 unicast-routing` on any router
- IPv6 addresses on any interface
- OSPFv3 process and interface participation
- HSRP groups 1 and 2 on R1 and R2
- Object tracking (`track 1`)
- PC default gateways updated to the HSRP VIP

---

## 5. Lab Challenge: Core Implementation

### Task 1: Enable IPv6 and Add IPv6 Addresses to All Router Interfaces

- Enable IPv6 unicast routing globally on R1, R2, and R3.
- Add IPv6 global unicast addresses and link-local addresses to all active interfaces on each router (per the addressing table in Section 3).
- Add loopback0 IPv6 addresses: R1=2001:DB8:FF::1/128, R2=2001:DB8:FF::2/128, R3=2001:DB8:FF::3/128.

**Verification:** `show ipv6 interface brief` on each router must show all interfaces with their configured global unicast addresses and a link-local address.

---

### Task 2: Enable OSPFv3 for IPv6 Routing

- Start an OSPFv3 process (process ID 1, same router-ID as OSPFv2) on R1, R2, and R3.
- Participate all active interfaces in area 0.
- Apply the same passive-interface policy as OSPFv2.

**Verification:** `show ipv6 ospf neighbor` on each router must show active adjacencies. `show ipv6 route ospf` must show IPv6 routes learned from neighbors.

---

### Task 3: Configure HSRPv2 Group 1 (IPv4) on R1 and R2

- Enable HSRPv2 on the LAN-facing interface of R1 and R2.
- Configure HSRP group 1 with virtual IP 192.168.1.1 on both routers.
- Set R1's priority to 110 and R2's priority to 100.
- Enable preemption on both R1 and R2.

**Verification:** `show standby brief` must show R1 as Active (P flag) and R2 as Standby. Both must show VIP 192.168.1.1 and the HSRPv2 virtual MAC (0000.0C9F.F001).

---

### Task 4: Configure Interface Tracking on R1

- Create a tracking object (object 1) that monitors R1's uplink interface (Gi0/1) line-protocol state.
- Bind the tracking object to HSRP group 1 on R1 with a priority decrement of 20.
- Verify the tracked object state is Up.

**Verification:** `show track 1` must show the tracked interface as Up. `show standby GigabitEthernet0/0` must show the track binding with decrement 20.

---

### Task 5: Simulate R1 Uplink Failure and Verify Failover

- Shut down R1's Gi0/1 (uplink to R3).
- Observe R1's HSRP priority drop from 110 to 90 (110 − 20).
- Confirm R2 becomes the HSRP Active router.
- Re-enable R1's Gi0/1 and verify R1 reclaims Active status via preemption.

**Verification:** During the outage: `show standby brief` on R1 shows Standby; on R2 shows Active. After recovery: R1 returns to Active within a few seconds.

---

### Task 6: Configure HSRP Group 2 for IPv6

- Configure HSRP group 2 on the LAN-facing interface of R1 and R2 with IPv6 virtual address 2001:DB8:1:1::1/64.
- Set R1's group 2 priority to 110, R2's to 100, with preemption on both.

**Verification:** `show standby ipv6 brief` must show R1 as Active and R2 as Standby for group 2 with the IPv6 VIP.

---

### Task 7: Update PC Gateways and Verify End-to-End Reachability

- Update PC1 and PC2 default gateways from R1's physical IP (192.168.1.2) to the HSRP virtual IP (192.168.1.1).
- Add IPv6 addresses and IPv6 default gateway (2001:DB8:1:1::1) to PC1 and PC2.
- Verify IPv4 and IPv6 reachability from both PCs to 203.0.113.1 through the virtual gateway.

**Verification:** Pings from PC1 and PC2 to 203.0.113.1 succeed. Shut down R1's Gi0/1 and verify pings continue through R2 (may have a brief 1–3 second interruption during failover).

---

## 6. Verification & Analysis

### Task 3 — HSRP Group 1 State

```
R1# show standby brief
                     P indicates configured to preempt.
                     |
Interface   Grp  Pri P State   Active          Standby         Virtual IP
Gi0/0       1    110 P Active  local           192.168.1.3     192.168.1.1  ! ← R1 is Active (P=preempt)
                                                                              ! ← Standby is R2 (192.168.1.3)

R2# show standby brief
Interface   Grp  Pri P State   Active          Standby         Virtual IP
Gi0/0       1    100 P Standby 192.168.1.2     local           192.168.1.1  ! ← R2 is Standby
```

```
R1# show standby GigabitEthernet0/0
GigabitEthernet0/0 - Group 1 (version 2)
  State is Active                                ! ← correct role
  Virtual IP address is 192.168.1.1
  Active virtual MAC address is 0000.0c9f.f001   ! ← HSRPv2 virtual MAC (group 1)
  Local virtual MAC address is 0000.0c9f.f001 (v2 default)
  Hello time 3 sec, hold time 10 sec             ! ← default timers
  Preemption enabled                             ! ← required for failback
  Active router is local
  Standby router is 192.168.1.3, priority 100 expires in X sec
  Priority 110 (configured 110)
    Track object 1 state Up decrement 20         ! ← tracking binding
```

### Task 5 — During Failover (R1 Gi0/1 shutdown)

```
R1# show standby brief
Interface   Grp  Pri P State   Active          Standby         Virtual IP
Gi0/0       1    90  P Standby 192.168.1.3     local           192.168.1.1  ! ← priority dropped to 90 (110-20)

R2# show standby brief
Interface   Grp  Pri P State   Active          Standby         Virtual IP
Gi0/0       1    100 P Active  local           192.168.1.2     192.168.1.1  ! ← R2 took over as Active

R1# show track 1
Track 1
  Interface GigabitEthernet0/1 line-protocol
  Line protocol is Down                         ! ← tracked interface is down
  1 change, last change 00:00:XX
```

### Task 6 — HSRP Group 2 (IPv6)

```
R1# show standby ipv6 brief
                     P indicates configured to preempt.
                     |
Interface   Grp  Pri P State   Active addr             Standby addr
Gi0/0       2    110 P Active  local                   FE80::2        ! ← R1 Active for IPv6
                                                                        ! ← R2 standby shown as link-local
```

---

## 7. Verification Cheatsheet

### IPv6 Interface Configuration

```
ipv6 unicast-routing
interface GigabitEthernet0/0
 ipv6 address FE80::1 link-local
 ipv6 address 2001:DB8:1:1::2/64
```

| Command | Purpose |
|---------|---------|
| `ipv6 unicast-routing` | Enables IPv6 forwarding (global config, required) |
| `ipv6 address <addr> link-local` | Sets a manual link-local address |
| `ipv6 address <prefix>/<len>` | Assigns a global unicast address |

### OSPFv3 Configuration

```
ipv6 router ospf 1
 router-id 1.1.1.1
 passive-interface default
 no passive-interface GigabitEthernet0/0
!
interface GigabitEthernet0/0
 ipv6 ospf 1 area 0
```

| Command | Purpose |
|---------|---------|
| `ipv6 router ospf <pid>` | Starts OSPFv3 process |
| `ipv6 ospf <pid> area <area>` | Participates interface in OSPFv3 area |

> **Exam tip:** OSPFv3 requires `router-id` to be set manually if no IPv4 address exists on any interface.

### HSRPv2 Configuration

```
interface GigabitEthernet0/0
 standby version 2
 standby 1 ip 192.168.1.1
 standby 1 priority 110
 standby 1 preempt
 standby 1 track 1 decrement 20
 standby 2 ipv6 2001:DB8:1:1::1/64
 standby 2 priority 110
 standby 2 preempt
```

| Command | Purpose |
|---------|---------|
| `standby version 2` | Enables HSRPv2 (required for IPv6 and extended group range) |
| `standby <grp> ip <vip>` | Configures the virtual IPv4 gateway IP |
| `standby <grp> priority <val>` | Sets election priority (default 100; higher wins) |
| `standby <grp> preempt` | Allows higher-priority router to reclaim Active role |
| `standby <grp> track <obj> decrement <val>` | Decrements priority when tracked object goes down |
| `standby <grp> ipv6 <addr/prefix>` | Configures IPv6 virtual gateway address (HSRPv2 only) |

> **Exam tip:** Preemption is NOT enabled by default. Forgetting `standby preempt` on the primary router is one of the most common HSRP misconfigurations.

### Object Tracking

```
track 1 interface GigabitEthernet0/1 line-protocol
```

| Command | Purpose |
|---------|---------|
| `track <id> interface <if> line-protocol` | Tracks interface up/down state |
| `track <id> interface <if> ip routing` | Tracks whether the interface has a valid route |

> **Exam tip:** Decrement must exceed (R1 priority − R2 priority) to trigger failover. With 110 vs 100, minimum decrement = 11. Use 20 for a safe margin.

### Verification Commands

| Command | What to Look For |
|---------|-----------------|
| `show standby brief` | Roles (Active/Standby), VIP, priority, preempt flag (P) |
| `show standby <if>` | Full detail: virtual MAC, timers, tracking, active/standby IPs |
| `show standby ipv6 brief` | Same as above for IPv6 groups |
| `show track <id>` | Tracked object state (Up/Down), change count |
| `show ipv6 interface brief` | IPv6 addresses and state per interface |
| `show ipv6 ospf neighbor` | OSPFv3 adjacencies |
| `show ipv6 route ospf` | IPv6 routes learned via OSPFv3 |

### HSRP Priority and Decrement Reference

| R1 Priority | R2 Priority | Minimum Decrement | Recommended |
|-------------|-------------|-------------------|-------------|
| 110 | 100 | 11 | 20 |
| 120 | 100 | 21 | 30 |
| 150 | 100 | 51 | 60 |

### Common HSRP Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| Both routers show Active | HSRP version mismatch (v1 vs v2), or not in same group |
| Wrong router is Active | Priority misconfigured, or preemption not enabled |
| Failover doesn't occur on uplink loss | Track decrement too small, or tracking not configured |
| Failback doesn't occur after recovery | Preemption not enabled on the higher-priority router |
| IPv6 group not forming | `standby version 2` missing, or `ipv6 unicast-routing` not enabled |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Tasks 1–2: IPv6 Addressing and OSPFv3

<details>
<summary>Click to view R1 Configuration</summary>

```bash
ipv6 unicast-routing
!
interface Loopback0
 ipv6 address 2001:DB8:FF::1/128
 ipv6 ospf 1 area 0
interface GigabitEthernet0/0
 ipv6 address FE80::1 link-local
 ipv6 address 2001:DB8:1:1::2/64
 ipv6 ospf 1 area 0
interface GigabitEthernet0/1
 ipv6 address FE80::1 link-local
 ipv6 address 2001:DB8:13::1/64
 ipv6 ospf 1 area 0
interface GigabitEthernet0/2
 ipv6 address FE80::1 link-local
 ipv6 address 2001:DB8:12::1/64
 ipv6 ospf 1 area 0
!
ipv6 router ospf 1
 router-id 1.1.1.1
 passive-interface default
 no passive-interface GigabitEthernet0/0
 no passive-interface GigabitEthernet0/1
 no passive-interface GigabitEthernet0/2
```
</details>

### Tasks 3–4: HSRP Group 1 (IPv4) + Interface Tracking on R1

<details>
<summary>Click to view R1 Configuration</summary>

```bash
track 1 interface GigabitEthernet0/1 line-protocol
!
interface GigabitEthernet0/0
 standby version 2
 standby 1 ip 192.168.1.1
 standby 1 priority 110
 standby 1 preempt
 standby 1 track 1 decrement 20
```
</details>

<details>
<summary>Click to view R2 Configuration</summary>

```bash
interface GigabitEthernet0/0
 standby version 2
 standby 1 ip 192.168.1.1
 standby 1 priority 100
 standby 1 preempt
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show standby brief
show standby GigabitEthernet0/0
show track 1
```
</details>

### Task 6: HSRP Group 2 (IPv6)

<details>
<summary>Click to view R1 Configuration</summary>

```bash
interface GigabitEthernet0/0
 standby 2 ipv6 2001:DB8:1:1::1/64
 standby 2 priority 110
 standby 2 preempt
```
</details>

<details>
<summary>Click to view R2 Configuration</summary>

```bash
interface GigabitEthernet0/0
 standby 2 ipv6 2001:DB8:1:1::1/64
 standby 2 priority 100
 standby 2 preempt
```
</details>

### Task 7: PC Gateway Update

<details>
<summary>Click to view PC1 and PC2 Configuration</summary>

```bash
! PC1 (VPC)
ip 192.168.1.10 255.255.255.0 192.168.1.1
ip6 2001:db8:1:1::10/64 2001:db8:1:1::1

! PC2 (VPC)
ip 192.168.1.20 255.255.255.0 192.168.1.1
ip6 2001:db8:1:1::20/64 2001:db8:1:1::1
```
</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world HSRP fault. Inject the fault first, then
diagnose and fix using only show commands.

### Workflow

```bash
python3 setup_lab.py                                   # reset to known-good
python3 scripts/fault-injection/inject_scenario_01.py  # Ticket 1
python3 scripts/fault-injection/apply_solution.py      # restore
```

---

### Ticket 1 — R2 Is the Active HSRP Router; R1 Is in Standby

The NOC reports that traffic from PC1 is egressing through R2 instead of R1. No topology changes were announced. R2 appears to be the HSRP Active router.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py`

**Success criteria:** `show standby brief` on R1 shows Active state with priority 110. R2 shows Standby.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
R1# show standby brief
! Look at the Pri column for group 1 on Gi0/0
! If R1 shows a priority below 100 (e.g., 90), it lost the election

R1# show run interface GigabitEthernet0/0
! Check standby 1 priority value -- should be 110, not 90

R2# show standby brief
! Confirms R2 is Active (R1 priority dropped below R2's 100)
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
R1# configure terminal
R1(config)# interface GigabitEthernet0/0
R1(config-if)#  standby 1 priority 110
R1(config-if)# end
! R1 preempts R2 and reclaims Active state (preempt is still configured)
R1# show standby brief
! R1 must show Active with priority 110
```
</details>

---

### Ticket 2 — After R1 Recovered, R2 Remains the HSRP Active Router

Following a brief power cycle on R1, R2 is now the HSRP Active router. R1 is back online with all interfaces up, but it remains in Standby state despite having a higher configured priority.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py`

**Success criteria:** After simulating R1 failure and recovery (shutdown/no shutdown Gi0/0), R1 automatically reclaims Active state within a few seconds.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
R1# show standby GigabitEthernet0/0
! Check the "Preemption" line -- it should say "enabled"
! If it says "disabled", R1 can never reclaim Active even with higher priority

R1# show run interface GigabitEthernet0/0
! Confirm "standby 1 preempt" is present
! If missing, R1 will remain Standby indefinitely after recovery
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
R1# configure terminal
R1(config)# interface GigabitEthernet0/0
R1(config-if)#  standby 1 preempt
R1(config-if)# end
! Preemption is now re-enabled; R1 should reclaim Active within hold-time
R1# show standby brief
! Verify R1 is Active with P flag
```
</details>

---

### Ticket 3 — LAN Traffic Stops When R1's Uplink Fails; R2 Does Not Take Over

R1's uplink (Gi0/1) went down due to a fiber cut. PC1 and PC2 cannot reach 203.0.113.1. `show standby brief` shows R1 is still the HSRP Active router. R2, which has a working uplink via its own Gi0/1, is not taking over.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py`

**Success criteria:** When R1's Gi0/1 is shut down, HSRP failover to R2 occurs automatically. PC1/PC2 reach 203.0.113.1 through R2 within a few seconds.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
R1# show track 1
! Check tracked object state -- should be Down after Gi0/1 shutdown
! Check the "decrement" value in the HSRP binding

R1# show standby GigabitEthernet0/0
! Look at "Priority" section: "Track object 1 state Down decrement X"
! If decrement X is 5, priority drops from 110 to 105 -- still above R2's 100
! Failover only occurs if R1's priority falls BELOW R2's priority

! Calculation: R1 (110) - decrement (5) = 105 > R2 (100) --> no failover
! Required: decrement must be > (110 - 100) = 11 to trigger failover
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
R1# configure terminal
R1(config)# interface GigabitEthernet0/0
R1(config-if)#  no standby 1 track 1 decrement 5
R1(config-if)#  standby 1 track 1 decrement 20
R1(config-if)# end

! Test: shutdown Gi0/1 on R1 and observe failover
R1(config)# interface GigabitEthernet0/1
R1(config-if)#  shutdown
R1(config-if)# end
R1# show standby brief
! R1 should now show Standby (priority 90); R2 should show Active
```
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] `ipv6 unicast-routing` enabled on R1, R2, and R3
- [ ] IPv6 global unicast and link-local addresses configured on all active interfaces
- [ ] OSPFv3 process 1 active on all routers; adjacencies established; IPv6 routes exchanged
- [ ] HSRPv2 group 1: R1 Active (priority 110, preempt), R2 Standby (priority 100, preempt), VIP 192.168.1.1
- [ ] `track 1` monitors R1 Gi0/1 line-protocol; decrement 20 bound to HSRP group 1
- [ ] R1's priority drops to 90 when Gi0/1 shuts down; R2 becomes Active
- [ ] R1 reclaims Active when Gi0/1 comes back up (preemption fires)
- [ ] HSRPv2 group 2: R1 Active (priority 110), R2 Standby (100), VIP 2001:DB8:1:1::1/64
- [ ] PC1 and PC2 gateways updated to 192.168.1.1 (IPv4) and 2001:DB8:1:1::1 (IPv6)
- [ ] PCs can reach 203.0.113.1 via the HSRP virtual gateway in normal and failover states

### Troubleshooting

- [ ] Ticket 1 resolved: R1 HSRP priority restored to 110; R1 is Active
- [ ] Ticket 2 resolved: HSRP preemption re-enabled on R1; failback verified
- [ ] Ticket 3 resolved: Track decrement corrected to 20; uplink-loss failover verified
