# IP Services Lab 03 — VRRPv3 and Dual-Stack Gateway Redundancy

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

**Exam Objective:** 3.3.c — Describe the concepts of FHRP (First Hop Redundancy Protocols) — HSRP, VRRP, GLBP | Topic: IP Services

This lab transitions the shared LAN gateway from HSRPv2 (lab-02) to VRRPv3, the open-standard FHRP defined in RFC 5798. Unlike HSRP, VRRPv3 natively supports both IPv4 and IPv6 in a single group using separate address-families — no separate group numbering required. You will remove the existing HSRP configuration, enable VRRPv3 with dual-stack address-families, and verify identical failover behavior using VRRP's different defaults (preempt on, faster timers, different virtual MAC).

### VRRPv3 Overview

VRRP (Virtual Router Redundancy Protocol) is an IETF open standard that provides default gateway redundancy for LAN hosts. VRRPv3 (RFC 5798) extends the original VRRPv2 to support both IPv4 and IPv6. Cisco IOS uses the `fhrp version vrrp v3` global command to activate the VRRPv3 implementation, which replaces the older per-AF VRRP commands with an address-family model.

Key VRRPv3 roles:
- **Master**: The router currently forwarding traffic for the virtual IP. Sends VRRP Advertisements every 1 second (default).
- **Backup**: Standby router listening for Advertisements. If none arrive within the Master Down Interval (~3 seconds), the Backup assumes Master.
- **Virtual IP (VIP)**: The IP address configured on each address-family. LAN hosts use this as their default gateway.

### VRRPv3 vs. HSRPv2 — Key Differences

| Feature | HSRPv2 | VRRPv3 |
|---------|--------|--------|
| Standard | Cisco proprietary | IETF RFC 5798 |
| Preemption default | OFF — must configure | ON — enabled automatically |
| Hello interval | 3 seconds | 1 second |
| Hold time | 10 seconds | 3 seconds (Master Down Interval) |
| IPv4 virtual MAC | `0000.0C9F.F0xx` (group hex) | `0000.5E00.01xx` (group hex) |
| IPv6 support | Separate group (HSRP for IPv6) | Same group, separate address-family |
| Config model | `standby <group>` per AF | `vrrp <group> address-family ipv4/ipv6` |

Because preemption is on by default in VRRPv3, a higher-priority router reclaims Master automatically after recovering — no explicit `preempt` keyword is required, though it is still valid to include it.

### VRRPv3 IOS Configuration Model

VRRPv3 on Cisco IOS uses a nested configuration model:

```
fhrp version vrrp v3                        ! global — activates VRRPv3 mode

interface GigabitEthernet0/0
 vrrp 1 address-family ipv4                 ! enter IPv4 AF for group 1
  address 192.168.1.1 primary               ! virtual IPv4 address
  priority 110                              ! override default (100)
  preempt                                   ! explicit (default in v3)
  track 1 decrement 20                      ! tie to a tracked object
 vrrp 1 address-family ipv6                 ! enter IPv6 AF for group 1
  address 2001:DB8:1:1::1 primary           ! virtual IPv6 GUA
  priority 110
  preempt
```

The address-family model means one `vrrp <group>` can carry both IPv4 and IPv6 VIPs. Each AF runs its own election independently.

### Interface Tracking with VRRPv3

Tracking in VRRPv3 works identically to HSRP: a tracked object (interface line-protocol, IP route, etc.) is linked to the VRRP group with a `decrement` value. When the tracked object goes down, the priority drops by the decrement amount.

**Critical rule:** `decrement > (master_priority - backup_priority)`

With R1 at 110 and R2 at 100, the gap is 10. A decrement of 20 drops R1 to 90, which is below R2's 100, triggering failover. A decrement of 5 would leave R1 at 105 — still above R2, so no failover occurs.

### VRRPv3 Virtual MAC and ARP

The VRRPv3 IPv4 virtual MAC is `0000.5E00.01xx` where `xx` is the group number in hex. For group 1: `0000.5E00.0101`. LAN hosts ARP for the VIP and receive this MAC. When the Master changes, the new Master immediately sends Gratuitous ARP to update the switch CAM table — transparent to hosts.

For IPv6, the virtual MAC is the same format. The IPv6 VIP is a full global unicast address (not link-local), and the virtual link-local address is auto-derived from the virtual MAC.

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| VRRPv3 configuration | Enable VRRPv3 globally and configure IPv4/IPv6 address-families |
| HSRP-to-VRRP migration | Remove HSRP config and replace with equivalent VRRPv3 |
| Dual-stack FHRP | Configure redundant gateway for both IPv4 and IPv6 simultaneously |
| Interface tracking | Link uplink state to VRRP priority for automatic failover |
| FHRP comparison | Articulate HSRPv2 vs. VRRPv3 differences for the exam |
| Failover verification | Simulate and confirm VRRP failover under uplink failure |

---

## 2. Topology & Scenario

**Scenario:** Your enterprise's LAN gateway redundancy was configured with HSRPv2 in the previous lab cycle. The network team has decided to migrate to VRRPv3 to standardize on an open protocol that supports dual-stack natively in a single group. R1 and R2 are the redundant LAN gateways; R3 is the upstream ISP router. PC1 and PC2 must maintain uninterrupted connectivity through the virtual gateway during the migration and subsequent failover tests.

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
│  VRRP Master (Pri 110)    │     │  VRRP Backup  (Pri 100)       │
│  Lo0: 1.1.1.1/32          │─────│  Lo0: 2.2.2.2/32             │
│  Gi0/0: 192.168.1.2/24    │Gi0/2│  Gi0/0: 192.168.1.3/24       │
│  Gi0/0: 2001:DB8:1:1::2/64│.1↔.2│  Gi0/0: 2001:DB8:1:1::3/64  │
└──────────────┬────────────┘     └────────────────┬─────────────┘
         Gi0/0 │                                   │ Gi0/0
               │                                   │
               └──────────────┬────────────────────┘
                               │
                        ┌──────┴──────┐
                        │   SW-LAN    │
                        │ 192.168.1.0 │
                        │    /24      │
                        └──┬───────┬──┘
                           │       │
                    ┌──────┴──┐ ┌──┴──────┐
                    │  PC1    │ │  PC2    │
                    │.10/24   │ │.20/24   │
                    │::10/64  │ │::20/64  │
                    └─────────┘ └─────────┘

VRRPv3 Group 1:
  IPv4 VIP: 192.168.1.1     Virtual MAC: 0000.5E00.0101
  IPv6 VIP: 2001:DB8:1:1::1
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

The following is pre-loaded in `initial-configs/` (chained from lab-02 solutions):

**Pre-configured on all routers:**
- Hostnames, `no ip domain-lookup`
- IPv4 and IPv6 addressing on all interfaces (dual-stack)
- OSPFv2 (router ospf 1) and OSPFv3 (ipv6 router ospf 1) fully operational
- NTP hierarchy (R1 master, R2 and R3 clients with MD5 authentication)
- QoS MQC policy (LAN-OUT) on R1 Gi0/1
- NAT/PAT on R1 (static for PC1, dynamic pool, PAT overload)
- **HSRPv2 group 1 (IPv4) and group 2 (IPv6)** on R1 and R2 — active and functional

**NOT pre-configured (student builds):**
- VRRPv3 global mode (`fhrp version vrrp v3`)
- VRRPv3 group 1 IPv4 and IPv6 address-families
- HSRP removal

---

## 5. Lab Challenge: Core Implementation

### Task 1: Remove HSRP from R1 and R2

On both R1 and R2, remove all HSRP configuration from the LAN interface. This includes the IPv4 standby group 1 and the IPv6 standby group 2. Verify that no `standby` commands remain in the running configuration for GigabitEthernet0/0 on either router.

**Verification:** `show running-config interface GigabitEthernet0/0` on R1 and R2 must show no `standby` lines. `show standby brief` should return no output.

---

### Task 2: Enable VRRPv3 Globally

On both R1 and R2, activate VRRPv3 mode at the global configuration level. This is a prerequisite for the address-family interface commands used in later tasks. Without this global command, IOS will reject the nested `vrrp` interface syntax.

**Verification:** `show running-config | include fhrp` must return the VRRPv3 mode line on both routers.

---

### Task 3: Configure VRRPv3 Group 1 — IPv4 Address-Family

On the LAN interface of both R1 and R2, configure VRRPv3 group 1 for the IPv4 address-family. Use virtual IP 192.168.1.1. Set R1's priority to 110 and R2's priority to 100. Enable preemption on both routers.

**Verification:** `show vrrp brief` must show R1 as Master and R2 as Backup for group 1. Both should show virtual IP 192.168.1.1.

---

### Task 4: Configure VRRPv3 Group 1 — IPv6 Address-Family

On the LAN interface of both R1 and R2, add the IPv6 address-family to VRRP group 1. Use virtual IP 2001:DB8:1:1::1 as the primary address. Set R1's priority to 110 and R2's priority to 100. Enable preemption on both.

**Verification:** `show vrrp` must show group 1 with both address-families on both routers. R1 must be Master for IPv6, R2 must be Backup.

---

### Task 5: Configure Interface Tracking for Automatic Failover

On R1, configure the VRRP IPv4 group to track the state of the uplink to R3 (GigabitEthernet0/1 line-protocol). Set the priority decrement to 20. This ensures that when R1's uplink fails, its VRRP priority drops below R2's 100, triggering automatic failover.

- A tracked object (track 1) is already present from lab-02 — verify it monitors GigabitEthernet0/1 line-protocol.
- Link this tracked object to the VRRP IPv4 group with a decrement of 20.

**Verification:** `show track 1` must show the tracked interface is Up. `show vrrp` on R1 must show the track object linked to group 1 IPv4 with decrement 20.

---

### Task 6: Verify Dual-Stack End-to-End Reachability

Confirm that both PC1 and PC2 can reach the simulated internet server on R3 (203.0.113.1) via IPv4 through the virtual gateway. Verify that the VRRP virtual MAC (0000.5E00.0101) appears in the switch ARP table and in the PC ARP cache.

From each PC:
- Ping 203.0.113.1 over IPv4 via the VRRP virtual gateway
- Ping 2001:DB8:FF::3 over IPv6 via the VRRP virtual gateway

**Verification:** Pings succeed from both PCs. `show ip arp` on R1 must show the LAN interface's ARP entries. PC ARP cache shows 192.168.1.1 resolved to 0000.5E00.0101.

---

### Task 7: Simulate Uplink Failure and Verify VRRP Failover

Shut down R1's uplink to R3 (GigabitEthernet0/1) and observe VRRP behavior:
- The tracked object should transition to Down.
- R1's priority should drop from 110 to 90 (decrement 20).
- R2 should become VRRP Master for both address-families.
- PC1 and PC2 should maintain connectivity through R2.

After verifying failover, restore R1's uplink and confirm R1 reclaims Master (preemption).

**Verification:** During failure: `show vrrp brief` on R2 shows Master. After restore: `show vrrp brief` on R1 shows Master. End-to-end pings succeed throughout.

---

## 6. Verification & Analysis

### VRRPv3 State — Normal Operation

```
R1# show vrrp brief
                                                  P indicates configured to preempt.
                                                  |
Interface   Grp  A-F   Pri Time  Own Pre State   Master addr/Group addr
Gi0/0         1  IPv4  110  3609   N   P Master  192.168.1.2    192.168.1.1   ! ← R1 is Master IPv4
Gi0/0         1  IPv6  110  3609   N   P Master  FE80::1        2001:DB8:1:1::1  ! ← R1 is Master IPv6

R2# show vrrp brief
Interface   Grp  A-F   Pri Time  Own Pre State   Master addr/Group addr
Gi0/0         1  IPv4  100  3609   N   P Backup  192.168.1.2    192.168.1.1   ! ← R2 is Backup; Master addr = R1
Gi0/0         1  IPv6  100  3609   N   P Backup  FE80::1        2001:DB8:1:1::1  ! ← R2 is Backup IPv6
```

### VRRPv3 Detail — R1

```
R1# show vrrp
GigabitEthernet0/0 - Group 1 - Address-Family IPv4
  State is Master                                    ! ← correct state
  State duration 0 mins 42.380 secs
  Virtual IP address is 192.168.1.1                 ! ← matches VIP
  Virtual MAC address is 0000.5E00.0101             ! ← VRRP MAC format group 1
  Advertisement interval is 1000 msec               ! ← 1 second (faster than HSRP's 3s)
  Preemption enabled                                 ! ← on by default in VRRPv3
  Priority is 110
  Track object 1 state Up decrement 20              ! ← track linked
  Master Router is 192.168.1.2 (local), priority is 110
  Master Advertisement interval is 1000 msec
  Master Down interval is 3.609 secs (3 secs + (110 * 30 msec)) ! ← ~3.6s hold
GigabitEthernet0/0 - Group 1 - Address-Family IPv6
  State is Master                                    ! ← IPv6 AF also Master
  Virtual IP address is 2001:DB8:1:1::1 primary     ! ← IPv6 VIP
  Virtual MAC address is 0000.5E00.0101             ! ← same virtual MAC
```

### Track Object State

```
R1# show track 1
Track 1
  Interface GigabitEthernet0/1 Line Protocol     ! ← tracks uplink
  Line protocol is Up                             ! ← must be Up in normal state
  1 change, last change 00:01:02
  Tracked by:
    VRRP GigabitEthernet0/0 1 IPv4               ! ← linked to VRRP group 1 IPv4
```

### Failover — R1 Uplink Down

```
R1# show vrrp brief
Interface   Grp  A-F   Pri Time  Own Pre State   Master addr/Group addr
Gi0/0         1  IPv4   90  3609   N   P Backup  192.168.1.3    192.168.1.1   ! ← priority dropped 110→90, R2 now Master
Gi0/0         1  IPv6  110  3609   N   P Master  FE80::1        2001:DB8:1:1::1  ! ← IPv6 unchanged (only IPv4 tracked)

R1# show track 1
  Line protocol is Down                           ! ← uplink down triggered decrement
  2 changes, last change 00:00:05
```

### PC ARP and Reachability

```
PC1> show arp
00:00:5e:00:01:01  192.168.1.1  expires in 119 seconds   ! ← VRRP virtual MAC for group 1
```

---

## 7. Verification Cheatsheet

### VRRPv3 Global Configuration

```
fhrp version vrrp v3

interface GigabitEthernet0/0
 vrrp <group> address-family ipv4
  address <vip> primary
  priority <value>
  preempt
  track <object> decrement <value>
 vrrp <group> address-family ipv6
  address <ipv6-vip> primary
  priority <value>
  preempt
```

| Command | Purpose |
|---------|---------|
| `fhrp version vrrp v3` | Activates VRRPv3 mode globally (required) |
| `vrrp <g> address-family ipv4` | Enters IPv4 AF config for VRRP group |
| `vrrp <g> address-family ipv6` | Enters IPv6 AF config for VRRP group |
| `address <ip> primary` | Sets the virtual IP for the address-family |
| `priority <value>` | Sets election priority (default 100; higher wins) |
| `preempt` | Allows higher-priority router to reclaim Master (default in v3) |
| `track <obj> decrement <n>` | Reduces priority by n when tracked object goes down |

> **Exam tip:** On Cisco IOS, `fhrp version vrrp v3` must appear before any `vrrp` interface commands. Omitting it causes IOS to reject the address-family syntax.

### HSRP Removal

```
interface GigabitEthernet0/0
 no standby <group>                  ! remove entire HSRP group
 no standby <group> ipv6 <address>   ! or remove IPv6 group
```

| Command | Purpose |
|---------|---------|
| `no standby <group>` | Removes the entire HSRP group and all parameters |
| `no standby version 2` | Returns interface to HSRPv1 mode (use when removing v2 marker) |

### Verification Commands

| Command | What to Look For |
|---------|-----------------|
| `show vrrp brief` | State (Master/Backup), priority, virtual IP per group/AF |
| `show vrrp` | Detailed timers, virtual MAC, track state, Master Down Interval |
| `show vrrp interface Gi0/0` | All VRRP groups on a specific interface |
| `show track 1` | Tracked object state (Up/Down), change count, linked protocols |
| `show ip arp` | Confirm VIP (192.168.1.1) resolves to VRRP virtual MAC |
| `show standby brief` | Confirm no HSRP output after removal |
| `show running-config interface Gi0/0` | Confirm no `standby` lines remain |

### VRRP vs. HSRP Quick Reference

| Attribute | HSRPv2 | VRRPv3 |
|-----------|--------|--------|
| Virtual MAC (IPv4) | 0000.0C9F.F0**xx** | 0000.5E00.01**xx** |
| Hello interval | 3 s | 1 s |
| Hold time | 10 s | ~3.6 s (Master Down Interval) |
| Preempt default | Off | On |
| IPv6 support | Separate group | Same group, separate AF |
| Standard | Cisco proprietary | IETF RFC 5798 |

> **Exam tip:** VRRP Master Down Interval = 3 × Advertisement + skew = ~3 seconds. This makes VRRP converge roughly 3× faster than HSRP in default configuration.

### Common VRRP Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| `vrrp` interface commands rejected | `fhrp version vrrp v3` not configured globally |
| Both routers show Backup state | No Master — VIP may conflict with a real interface IP on a different router |
| R2 never becomes Master on failover | Track decrement too small (must exceed priority gap) |
| IPv6 gateway unreachable on failover | IPv6 address-family not configured on backup router |
| Preemption not working | Using VRRPv2 syntax without v3 — check `show vrrp` for version |
| Wrong virtual MAC in ARP | HSRP still active on interface — confirm `no standby` |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Task 1 & 2: Remove HSRP and Enable VRRPv3

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1
interface GigabitEthernet0/0
 no standby version 2
 no standby 1
 no standby 2

fhrp version vrrp v3
```
</details>

<details>
<summary>Click to view R2 Configuration</summary>

```bash
! R2
interface GigabitEthernet0/0
 no standby version 2
 no standby 1
 no standby 2

fhrp version vrrp v3
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show running-config interface GigabitEthernet0/0
show standby brief
show running-config | include fhrp
```
</details>

---

### Tasks 3–5: VRRPv3 Group 1 IPv4, IPv6, and Tracking

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1
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
<summary>Click to view R2 Configuration</summary>

```bash
! R2
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

<details>
<summary>Click to view Verification Commands</summary>

```bash
show vrrp brief
show vrrp
show track 1
```
</details>

---

### Tasks 6–7: Reachability and Failover Test

<details>
<summary>Click to view Failover Test Procedure</summary>

```bash
! On R1 — simulate uplink failure
interface GigabitEthernet0/1
 shutdown

! Verify on R1
show vrrp brief                ! R1 IPv4 should show Backup (priority 90)
show track 1                   ! Line protocol is Down

! Verify on R2
show vrrp brief                ! R2 should show Master

! Restore
interface GigabitEthernet0/1
 no shutdown

! Verify R1 reclaims Master (preemption)
show vrrp brief                ! R1 back to Master
```
</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. Inject the fault first, then diagnose and fix using only show commands.

### Workflow

```bash
python3 setup_lab.py                                    # reset to initial-configs
python3 scripts/fault-injection/apply_solution.py       # apply known-good solution
python3 scripts/fault-injection/inject_scenario_01.py   # Ticket 1
python3 scripts/fault-injection/apply_solution.py       # restore before next ticket
```

---

### Ticket 1 — LAN Hosts Are Using the Wrong Default Gateway Router

A network change was applied overnight. This morning users report intermittent slowness. On investigation you notice that all LAN traffic is flowing through R2 instead of R1, even though R1 is up and has a higher configured priority.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py`

**Success criteria:** `show vrrp brief` on R1 shows Master for group 1 IPv4 at priority 110. All PC traffic flows through R1.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! Step 1 — check VRRP state on R1
R1# show vrrp brief
! Look for State column — if Backup, priority problem

! Step 2 — check priority
R1# show vrrp
! Look for "Priority is" line — should be 110

! Step 3 — check running config
R1# show running-config interface GigabitEthernet0/0
! Look for "priority" under vrrp 1 address-family ipv4
! If it shows 90, the decrement was applied manually
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
R1# show vrrp brief   ! confirm Master
```
</details>

---

### Ticket 2 — IPv6 Hosts Lose Connectivity When R1 Goes Down

During a planned maintenance window, R1 was briefly taken offline. IPv4 hosts failed over successfully to R2 but IPv6 hosts lost their gateway and could not reconnect. After R1 came back, IPv6 was restored. The IPv6 gateway has no redundancy.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py`

**Success criteria:** `show vrrp` on R2 shows group 1 with both IPv4 and IPv6 address-families active in Backup state. Shutting R1 Gi0/0 causes R2 to become Master for both AFs.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! Step 1 — check VRRP detail on R2
R2# show vrrp
! Look for both address-family IPv4 and IPv6 entries
! If only IPv4 appears, IPv6 AF is missing

! Step 2 — check running config on R2
R2# show running-config interface GigabitEthernet0/0
! Look for 'vrrp 1 address-family ipv6' block
! If absent, that is the fault

! Step 3 — confirm IPv6 VRRP works when R1 is up
R1# show vrrp
! R1 should show IPv6 Master — only R2 backup is missing
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
R2# configure terminal
R2(config)# interface GigabitEthernet0/0
R2(config-if)# vrrp 1 address-family ipv6
R2(config-if-vrrp)# address 2001:DB8:1:1::1 primary
R2(config-if-vrrp)# priority 100
R2(config-if-vrrp)# preempt
R2(config-if-vrrp)# end
R2# show vrrp   ! confirm both AFs present
```
</details>

---

### Ticket 3 — R1 Uplink Fails But VRRP Does Not Failover

A user reports that pinging the internet fails whenever R1's upstream link to R3 is down, yet VRRP shows R1 is still Master. The track object is showing Down. The failover that worked perfectly in the previous lab is no longer triggering.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py`

**Success criteria:** After shutting R1 Gi0/1, R1 VRRP priority drops to 90 and R2 becomes Master. `show track 1` shows Down and VRRP transitions to Backup on R1.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! Step 1 — check track state
R1# show track 1
! Line protocol is Down (injected by shutting Gi0/1 manually for test)
! Check "Tracked by" — VRRP should appear

! Step 2 — check VRRP state
R1# show vrrp
! Priority should reflect the decrement
! If "Priority is 105" with track Down, decrement is only 5 (not 20)

! Step 3 — check running config for decrement
R1# show running-config interface GigabitEthernet0/0
! Look for 'track 1 decrement' value under vrrp 1 address-family ipv4
! Gap between R1 (110) and R2 (100) is 10 — decrement must be > 10
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
R1# configure terminal
R1(config)# interface GigabitEthernet0/0
R1(config-if)# vrrp 1 address-family ipv4
R1(config-if-vrrp)# no track 1 decrement 5
R1(config-if-vrrp)# track 1 decrement 20
R1(config-if-vrrp)# end
R1# show vrrp   ! confirm track decrement is 20
! Simulate failure: shutdown Gi0/1, verify R2 becomes Master
```
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] HSRP removed from R1 and R2 (`show standby brief` returns no output)
- [ ] `fhrp version vrrp v3` configured globally on R1 and R2
- [ ] VRRPv3 group 1 IPv4 configured: VIP 192.168.1.1, R1 priority 110, R2 priority 100
- [ ] VRRPv3 group 1 IPv6 configured: VIP 2001:DB8:1:1::1, R1 priority 110, R2 priority 100
- [ ] Preemption enabled on both routers for both address-families
- [ ] R1 shows Master for both IPv4 and IPv6 AFs (`show vrrp brief`)
- [ ] R2 shows Backup for both IPv4 and IPv6 AFs (`show vrrp brief`)
- [ ] Track object 1 monitors Gi0/1 line-protocol with decrement 20 on R1
- [ ] Virtual MAC 0000.5E00.0101 visible in PC ARP cache for 192.168.1.1
- [ ] PC1 and PC2 reach 203.0.113.1 (IPv4) via virtual gateway
- [ ] PC1 and PC2 reach IPv6 destinations via 2001:DB8:1:1::1 virtual gateway
- [ ] R1 uplink failure triggers VRRP failover to R2 (R2 becomes Master)
- [ ] R1 uplink restore triggers VRRP preemption (R1 reclaims Master)

### Troubleshooting

- [ ] Ticket 1 resolved: R1 restored as VRRP Master for IPv4
- [ ] Ticket 2 resolved: R2 has IPv6 address-family configured for full dual-stack redundancy
- [ ] Ticket 3 resolved: Track decrement corrected to 20, failover triggers on uplink failure
