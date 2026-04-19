# Lab 00 — Network Diagnostics: Debug, Ping, Traceroute, SNMP, Syslog

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

**Exam Objective:** 4.1 — Use debugs, conditional debugs, ping, traceroute, and SNMP to identify, fix, and troubleshoot network issues (Network Assurance)

This lab establishes the foundational diagnostic toolkit every network engineer uses daily. You will configure persistent log buffering with accurate timestamps, deploy SNMP v2c for device monitoring and trap delivery, use extended ping and traceroute to probe network behaviour beyond simple reachability, and apply conditional debug filtering to scope real-time packet-level output without overwhelming the console. These tools are examined both as configuration tasks and as active troubleshooting techniques in the ENCOR exam.

---

### Syslog Architecture and Buffered Logging

Cisco IOS syslog events are generated for every significant system event — interface state changes, OSPF adjacency changes, authentication failures, and more. By default, messages go only to the console; they are not saved anywhere. Configuring a local buffer (`logging buffered`) keeps the most recent events in memory so you can review them after the fact with `show logging`.

**Severity Levels** — the IOS syslog severity scale follows RFC 5424:

| Level | Keyword | Example Events |
|-------|---------|----------------|
| 0 | emergencies | System unusable |
| 1 | alerts | Immediate action needed |
| 2 | critical | Critical conditions |
| 3 | errors | Error conditions |
| 4 | warnings | Warning conditions |
| 5 | notifications | Normal but significant |
| 6 | informational | Informational (interface up/down, OSPF neighbor change) |
| 7 | debugging | Debug-level output |

Setting `logging buffered 16384 informational` buffers all messages at severity 6 and below (0–6). It is a threshold, not an exact match — a common exam trap.

**Timestamps** are critical for correlating events. Without `service timestamps log datetime msec`, every syslog line shows a relative uptime counter (`00:03:12`) that is useless when tracing a sequence of events across devices. The `msec` keyword adds millisecond resolution.

```
! IOS syntax — buffered logging with timestamps
service timestamps log datetime msec
logging buffered <bytes> <severity-keyword>
```

> **Key behaviour:** The `show logging` command shows the buffer most-recent-last. If you see `logging buffered 16384 errors` instead of `informational`, interface up/down events (severity 5 — notifications) and OSPF changes (severity 5) will be silently discarded.

---

### SNMP v2c Communities and Traps

SNMP (Simple Network Management Protocol) provides a structured mechanism for reading device state (GET), writing configuration (SET), and receiving asynchronous event notifications (TRAP). Version 2c uses community strings as a shared secret — no per-user authentication.

**Two community roles:**

| Community | Access | IOS Keyword |
|-----------|--------|-------------|
| Read-only | GETs only — walk the MIB tree, read counters | `RO` |
| Read-write | GETs and SETs — change configuration via SNMP | `RW` |

**Traps vs. Informs:** A trap is fire-and-forget (UDP). The agent sends it once; no acknowledgement is expected. An inform (v2c/v3 only) requires the manager to acknowledge. For this lab, traps suffice.

**Interface traps** (`linkdown`, `linkup`) are the most common production use: a monitoring system learns of an interface failure without polling. The `coldstart` trap fires when the device reloads — useful for detecting unexpected reboots.

```
! SNMP v2c communities
snmp-server community <string> RO
snmp-server community <string> RW

! Trap receiver — send traps to this IP using the RO community
snmp-server host <ip> version 2c <community>

! Which trap types to generate
snmp-server enable traps snmp linkdown linkup coldstart
```

> **Security note for the exam:** SNMP v2c community strings travel in clear text. `ENCOR-RW` with write access to 192.168.x.x on a production device is a high-severity finding. In real deployments, restrict access with a standard ACL appended to the community: `snmp-server community ENCOR-RO RO ACL-SNMP-PERMIT`.

---

### Conditional Debug with ACL Filters

`debug ip packet` generates a line of output for every IP packet processed by the router's software path. On an active router this can produce thousands of lines per second, consuming CPU and flooding the console. **Conditional debug** solves this by attaching a named ACL as a filter — only packets matching an ACL permit entry generate debug output.

**How it works:**
1. Define a named extended ACL that matches the traffic of interest.
2. Reference that ACL when enabling the debug command.
3. IOS evaluates the ACL against each candidate packet before generating output.

```
! Define the filter ACL
ip access-list extended DEBUG-FILTER
 permit ip host 192.168.10.10 any

! Enable debug with the filter (exec mode — not a config command)
debug ip packet detail DEBUG-FILTER

! Always disable when done
undebug all
```

> **Critical exam behaviour:** The ACL attached to a conditional debug is evaluated source-first. `permit ip host 192.168.10.10 any` generates output for packets FROM 192.168.10.10. To also see return traffic, add `permit ip any host 192.168.10.10`. If the ACL has no explicit permit (or has an implicit deny for the traffic of interest), debug produces no output — the most common misconfiguration in this area.

---

### Extended Ping and Extended Traceroute

The basic `ping <ip>` and `traceroute <ip>` commands use the router's closest outgoing interface as the source address. Extended mode adds control over source, size, repeat count, DF bit, timeout, and TTL.

**Extended ping options used in this lab:**

| Option | Purpose |
|--------|---------|
| Source address/interface | Forces a specific source IP — tests return-path reachability |
| Repeat count | More probes = statistical confidence; useful for detecting intermittent drops |
| Datagram size | Test MTU path — large size + DF bit reveals fragmentation points |
| DF bit | Set "Don't Fragment" — required for MTU discovery |

**Extended traceroute extras:**

| Option | Purpose |
|--------|---------|
| Source address | Confirms symmetric routing |
| Minimum TTL | Skip known hops at the start of the path |
| Numeric | Skip DNS reverse lookups for faster output |

```
! Invoke extended ping interactively
ping
Protocol [ip]:
Target IP address: 3.3.3.3
Repeat count [5]: 100
Datagram size [100]: 1400
Timeout in seconds [2]:
Extended commands [n]: y
Source address or interface: 1.1.1.1
Type of service [0]:
Set DF bit in IP header? [no]: yes
...

! Extended traceroute
traceroute
Protocol [ip]:
Target IP address: 3.3.3.3
Source address: 1.1.1.1
Numeric display [n]: yes
...
```

> **Exam tip:** Source-interface extended ping from a Loopback is the standard method to test whether a specific prefix is reachable end-to-end and that routing is symmetric. If a plain `ping 3.3.3.3` succeeds but `ping 3.3.3.3 source Loopback0` fails, the remote router has no return route to 1.1.1.1.

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| Syslog buffering | Configure persistent event logging with correct severity threshold |
| Timestamp configuration | Add datetime + millisecond precision to syslog entries |
| SNMP v2c community design | Separate RO and RW communities; understand access implications |
| SNMP trap delivery | Target a trap receiver and select relevant trap types |
| Conditional debug | Scope debug output with a named ACL to prevent console storms |
| Extended ping | Control source, size, DF bit for MTU and symmetric-path testing |
| Extended traceroute | Trace multi-hop paths with source control and numeric output |

---

## 2. Topology & Scenario

**Scenario:** You are a network engineer at Meridian Industries. The NOC team has deployed a new three-router, two-switch topology but has no visibility into device events, no SNMP monitoring, and no structured diagnostic process. Your task is to instrument the network — configure syslog so that events are preserved in the local buffer with accurate timestamps, deploy SNMP v2c so that R2 can serve as the monitoring aggregation point, and establish the conditional debug workflow that the team can use for future troubleshooting. Once instrumentation is in place, you will exercise extended ping and extended traceroute to confirm end-to-end reachability and path behaviour.

```
     ┌────────────────────┐  Gi0/1   10.1.12.1/30   Gi0/1  ┌────────────────────┐  Gi0/2  10.1.23.1/30  Gi0/0  ┌────────────────────┐
     │         R1         ├─────────────────────────────────┤         R2         ├──────────────────────────────┤         R3         │
     │  (Edge / Exporter) │         10.1.12.2/30            │  (Distrib. / NMS)  │        10.1.23.2/30           │  (Remote / Target) │
     │  Lo0: 1.1.1.1/32   │                                 │  Lo0: 2.2.2.2/32   │                               │  Lo0: 3.3.3.3/32   │
     └──────────┬─────────┘                                 └──────────┬─────────┘                               └────────────────────┘
            Gi0/0│                                                  Gi0/0│
      192.168.10.1/24                                        192.168.20.1/24
            Gi0/2│                                                  Gi0/2│
     ┌────────────┴──────┐  Gi0/1         Gi0/1  ┌──────────────────────┴──┐
     │        SW1        ├──────── trunk ──────────┤         SW2             │
     │  (Access/SPAN src)│  (VLANs 10,20,99,500)  │  (Distrib. / RSPAN dst) │
     │ SVI:192.168.99.11 │                          │ SVI:192.168.99.12       │
     └──────────┬────────┘                          └──────────┬──────────────┘
           Gi0/3│ (VLAN 10)                               Gi0/3│ (VLAN 20)
          ┌─────┴──────┐                                  ┌────┴──────┐
          │    PC1     │                                  │    PC2    │
          │ 192.168.10 │                                  │ 192.168.20│
          │  .10/24    │                                  │  .10/24   │
          └────────────┘                                  └───────────┘
```

**Subnet summary:**

| Segment | Subnet | Devices |
|---------|--------|---------|
| R1–R2 | 10.1.12.0/30 | R1 Gi0/1 (.1), R2 Gi0/1 (.2) |
| R2–R3 | 10.1.23.0/30 | R2 Gi0/2 (.1), R3 Gi0/0 (.2) |
| VLAN 10 (DATA-A) | 192.168.10.0/24 | R1 Gi0/0 (.1), PC1 (.10) |
| VLAN 20 (DATA-B) | 192.168.20.0/24 | R2 Gi0/0 (.1), PC2 (.10) |
| VLAN 99 (MGMT) | 192.168.99.0/24 | SW1 SVI (.11), SW2 SVI (.12) |
| VLAN 500 (RSPAN) | — | Reserved for lab-02 |

---

## 3. Hardware & Environment Specifications

### Devices

| Device | Platform | Role |
|--------|----------|------|
| R1 | IOSv (iosv) | Edge router — syslog host, SNMP agent, debug source |
| R2 | IOSv (iosv) | Distribution — SNMP trap receiver aggregation point |
| R3 | IOSv (iosv) | Remote router — multi-hop traceroute target |
| SW1 | IOSvL2 (iosvl2) | Access switch — SPAN source (lab-02) |
| SW2 | IOSvL2 (iosvl2) | Distribution switch — RSPAN destination (lab-02) |
| PC1 | VPCS | Traffic source for conditional debug testing |
| PC2 | VPCS | Traffic destination |

### Cabling

| Link | Source | Destination | Notes |
|------|--------|-------------|-------|
| L1 | SW1 Gi0/1 | SW2 Gi0/1 | Trunk — VLANs 10, 20, 99, 500 |
| L2 | R1 Gi0/0 | SW1 Gi0/2 | VLAN 10 — R1 is default gateway |
| L3 | R2 Gi0/0 | SW2 Gi0/2 | VLAN 20 — R2 is default gateway |
| L4 | R1 Gi0/1 | R2 Gi0/1 | P2P 10.1.12.0/30 |
| L5 | R2 Gi0/2 | R3 Gi0/0 | P2P 10.1.23.0/30 |
| L6 | PC1 | SW1 Gi0/3 | VLAN 10 access |
| L7 | PC2 | SW2 Gi0/3 | VLAN 20 access |

> **Reserved ports:** SW1 Gi0/0 and SW2 Gi0/0 are monitoring ports — reserved for SPAN/RSPAN sessions in lab-02. Do not assign them to VLANs or connect them to devices in this lab.

### Console Access Table

| Device | Port | Connection Command |
|--------|------|--------------------|
| R1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R3 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| SW1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| SW2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| PC1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| PC2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |

---

## 4. Base Configuration

Run `python3 setup_lab.py --host <eve-ng-ip>` to push initial configs to all router and switch nodes. PC1 and PC2 must be configured manually via their EVE-NG consoles.

### Pre-loaded on all routers (R1, R2, R3)

- IP addressing on all interfaces (Loopback0, point-to-point links, LAN interfaces)
- OSPF process 1 in area 0 — all routers have full reachability
- Passive interface on R1 Gi0/0 and R2 Gi0/0 (LAN segments)

### Pre-loaded on switches (SW1, SW2)

- VLANs 10 (DATA-A), 20 (DATA-B), 99 (MGMT), 500 (RSPAN — `remote-span` marked)
- Trunk between SW1 Gi0/1 and SW2 Gi0/1 (VLANs 10, 20, 99, 500)
- Access port configuration for R1/R2 uplinks and PC ports
- VLAN 99 SVIs with management IP addresses

### Pre-loaded on PCs (manual)

- PC1: IP address, subnet mask, default gateway
- PC2: IP address, subnet mask, default gateway

### NOT pre-configured (student task)

- Syslog buffering and severity level
- Syslog timestamps
- SNMP communities (read-only and read-write)
- SNMP trap receiver
- SNMP trap types
- Conditional debug ACL
- Any exec-mode debug commands

---

## 5. Lab Challenge: Core Implementation

### Task 1: Enable Syslog Buffering with Timestamps

- Enable syslog timestamps on all three routers (R1, R2, R3) using datetime format with millisecond resolution.
- Configure local log buffering on each router with a 16384-byte buffer at the informational severity level.

**Verification:** `show logging` on each router must show the buffer size, severity level, and at least one timestamped log entry. The line `Log Buffer (16384 bytes)` and `Logging to buffer (informational)` must be present.

---

### Task 2: Configure SNMP v2c Communities

- Configure a read-only community named `ENCOR-RO` on all three routers.
- Configure a read-write community named `ENCOR-RW` on all three routers.

**Verification:** `show snmp community` on each router must list both communities with their respective access levels.

---

### Task 3: Configure SNMP Trap Receiver and Enable Traps

- On all three routers, designate R2's loopback address (2.2.2.2) as the SNMP trap receiver, using version 2c and the read-only community.
- Enable SNMP traps for link-down, link-up, and cold-start events on all three routers.

**Verification:** `show snmp host` on each router must show 2.2.2.2 as the trap destination. Shut then no-shut an interface on R1 and confirm a trap entry appears in `show snmp` counters.

---

### Task 4: Configure a Conditional Debug ACL

- On R1, create a named extended ACL called `DEBUG-FILTER` that permits all IP traffic sourced from PC1 (192.168.10.10) to any destination.
- This ACL will be used in the next task to scope debug output.

**Verification:** `show ip access-lists DEBUG-FILTER` must show the ACL with the permit entry. No matches yet (the debug is not yet active).

---

### Task 5: Apply Extended Ping with Source and MTU Options

- From R1, send an extended ping to R3's loopback (3.3.3.3) using:
  - Source: R1's loopback address (1.1.1.1)
  - Repeat count: 100 packets
  - Datagram size: 1400 bytes
  - DF bit: set

**Verification:** All 100 packets must succeed (100% success rate). If the ping fails with large sizes, investigate MTU settings on the path.

---

### Task 6: Apply Extended Traceroute with Source Control

- From R1, run an extended traceroute to R3's loopback (3.3.3.3):
  - Source address: R1's loopback (1.1.1.1)
  - Numeric output (no DNS lookups)

**Verification:** The traceroute must show exactly two hops — R2 (10.1.12.2) and R3 (3.3.3.3). Confirm the source in the output header shows 1.1.1.1.

---

### Task 7: Exercise Conditional Debug

- On R1, enable `debug ip packet detail` scoped to the `DEBUG-FILTER` ACL.
- From PC1, ping PC2 (192.168.20.10) to generate matching traffic.
- Observe the debug output and confirm only packets from 192.168.10.10 are logged.
- Disable all debugging when finished.

**Verification:** Debug output must show IP packet lines containing `192.168.10.10` as the source. No packets from other hosts must appear. `show debug` after disabling must show no active debugs.

---

## 6. Verification & Analysis

### Task 1 — Syslog

```
R1# show logging
Syslog logging: enabled (0 messages dropped, 3 messages rate-limited,
                0 flushes, 0 overruns, xml disabled, filtering disabled)

No Active Message Discriminator.
No Inactive Message Discriminator.

    Console logging: level debugging, 43 messages logged, xml disabled,
                     filtering disabled
    Monitor logging: level debugging, 0 messages logged, xml disabled,
                     filtering disabled
    Buffer logging:  level informational, 5 messages logged, xml disabled,  ! ← must say "informational"
                    filtering disabled
    Exception Logging: size (4096 bytes)
    Count and timestamp logging messages: disabled
    Persistent logging: disabled

No active filter modules.

    Trap logging: level informational, 0 message lines logged

Log Buffer (16384 bytes):                                                   ! ← buffer size must be 16384

*Apr 19 12:01:23.412: %OSPF-5-ADJCHG: Process 1, Nbr 2.2.2.2 on           ! ← timestamped entry (datetime msec format)
GigabitEthernet0/1 from LOADING to FULL, Loading Done
```

### Task 2 — SNMP Communities

```
R1# show snmp community

Community name: ENCOR-RO                ! ← RO community present
Community Index: ENCOR-RO
Community SecurityName: ENCOR-RO
storage-type: nonvolatile, active

Community name: ENCOR-RW                ! ← RW community present
Community Index: ENCOR-RW
Community SecurityName: ENCOR-RW
storage-type: nonvolatile, active
```

### Task 3 — SNMP Trap Receiver

```
R1# show snmp host

Notification host: 2.2.2.2    udp-port: 162    type: trap      ! ← 2.2.2.2 must appear
user: ENCOR-RO    security model: v2c                           ! ← community and version correct

R1# show snmp
Chassis: ...
Contact: ...
...
0 SNMP packets input
...
3 SNMP notifications sent                                       ! ← non-zero after test flap
```

### Task 4 — Conditional Debug ACL

```
R1# show ip access-lists DEBUG-FILTER
Extended IP access list DEBUG-FILTER
    10 permit ip host 192.168.10.10 any                         ! ← entry present, match count 0 before debug
```

### Task 5 — Extended Ping

```
R1# ping 3.3.3.3 source Loopback0 repeat 100 size 1400 df-bit

Type escape sequence to abort.
Sending 100, 1400-byte ICMP Echos to 3.3.3.3, timeout is 2 seconds:
Packet sent with a source address of 1.1.1.1
Packet sent with the DF bit set
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
Success rate is 100 percent (100/100)                           ! ← must be 100%
round-trip min/avg/max = 1/2/4 ms
```

### Task 6 — Extended Traceroute

```
R1# traceroute 3.3.3.3 source 1.1.1.1 numeric

Type escape sequence to abort.
Tracing the route to 3.3.3.3
VRF info: (vrf in name/id, vrf out name/id)
  1 10.1.12.2 1 msec 1 msec 1 msec     ! ← first hop = R2 (10.1.12.2)
  2 3.3.3.3   1 msec 1 msec 1 msec     ! ← second hop = R3 loopback — exactly 2 hops total
```

### Task 7 — Conditional Debug

```
R1# debug ip packet detail DEBUG-FILTER

IP packet debugging is on (detailed) for access list DEBUG-FILTER

R1#
*Apr 19 12:15:44.123: IP: s=192.168.10.10 (GigabitEthernet0/0), d=192.168.20.10, len 100,  ! ← source is PC1
  rcvd 3
*Apr 19 12:15:44.124: IP: tableid=0, s=192.168.10.10 (GigabitEthernet0/0),                 ! ← only PC1 traffic shown
  d=192.168.20.10 (GigabitEthernet0/1), routed via FIB
...

R1# undebug all
All possible debugging has been turned off

R1# show debug
(nothing displayed — no active debugs)                          ! ← confirm all debug off
```

---

## 7. Verification Cheatsheet

### Syslog Configuration

```
service timestamps log datetime msec
logging buffered <bytes> <severity>
```

| Command | Purpose |
|---------|---------|
| `service timestamps log datetime msec` | Add datetime+ms prefix to every log line |
| `logging buffered 16384 informational` | Buffer up to 16 KB of events, severity 0–6 |
| `no logging console` | Suppress console messages (use in production) |
| `clear logging` | Flush the log buffer |

> **Exam tip:** Severity keywords are thresholds. `informational` (6) captures everything from level 0 through 6. `errors` (3) discards notifications (5), informational (6), and debugging (7).

### SNMP v2c Configuration

```
snmp-server community <string> RO [acl]
snmp-server community <string> RW [acl]
snmp-server host <ip> version 2c <community>
snmp-server enable traps snmp linkdown linkup coldstart
```

| Command | Purpose |
|---------|---------|
| `snmp-server community X RO` | Define read-only community |
| `snmp-server community X RW` | Define read-write community |
| `snmp-server host <ip> version 2c <community>` | Register a trap receiver |
| `snmp-server enable traps snmp linkdown linkup coldstart` | Select trap types |
| `show snmp community` | Verify communities and access levels |
| `show snmp host` | Verify trap destination and community |

> **Exam tip:** `snmp-server host` sets the trap destination. If the host is missing, traps are generated internally but never sent. Community in `snmp-server host` must match what the NMS expects — mismatch silently drops traps at the receiver.

### Conditional Debug ACL

```
ip access-list extended <name>
 permit ip host <src> any

debug ip packet [detail] <acl-name>
undebug all
```

| Command | Purpose |
|---------|---------|
| `debug ip packet detail <acl>` | Enable filtered packet debug |
| `undebug all` | Disable all active debugs |
| `show debug` | Confirm which debugs are active |
| `terminal monitor` | Mirror debug output to SSH/Telnet session |

> **Exam tip:** `debug ip packet` only captures software-switched packets. Hardware-CEF-switched flows do not appear. On a lightly loaded lab router, CEF may punt all packets to process switching — but on production hardware, you may see nothing without a `no ip cef` (never do this in production).

### Extended Ping and Traceroute

```
ping <ip> source <ip|int> repeat <n> size <bytes> [df-bit]
traceroute <ip> source <ip> numeric
```

| Command | What to Look For |
|---------|-----------------|
| `ping 3.3.3.3 source Loopback0` | `Success rate is 100 percent` — symmetric routing confirmed |
| `ping 3.3.3.3 size 1400 df-bit` | If `!` — path MTU ≥ 1400. If `M` — fragmentation needed, MTU issue |
| `traceroute 3.3.3.3 source 1.1.1.1 numeric` | Count hops; confirm expected next-hops |

### Verification Commands

| Command | What to Look For |
|---------|-----------------|
| `show logging` | Buffer level = informational; entries have datetime format |
| `show snmp community` | Both ENCOR-RO and ENCOR-RW listed |
| `show snmp host` | 2.2.2.2 appears as UDP trap destination |
| `show snmp` | `SNMP notifications sent` counter > 0 after a test event |
| `show ip access-lists DEBUG-FILTER` | Permit entry present; match count increments during debug |
| `show debug` | All blank = no active debugs |

### Common Network Assurance Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| `show logging` shows no recent events | Severity threshold too restrictive (e.g., `errors` instead of `informational`) |
| Debug produces no output | ACL has no permit entry matching the traffic, or traffic is CEF-switched |
| SNMP GET times out | Wrong community string on agent or NMS |
| Traps generated but not received | `snmp-server host` missing or wrong community |
| Traceroute shows `*` at a hop | ICMP TTL-exceeded responses blocked by an ACL or firewall |
| Extended ping fails with DF bit | Path MTU below datagram size — fragmentation blocked |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Task 1 & 2: Syslog Buffering and SNMP Communities (all routers)

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1
service timestamps log datetime msec
logging buffered 16384 informational
snmp-server community ENCOR-RO RO
snmp-server community ENCOR-RW RW
snmp-server host 2.2.2.2 version 2c ENCOR-RO
snmp-server enable traps snmp linkdown linkup coldstart
```
</details>

<details>
<summary>Click to view R2 Configuration</summary>

```bash
! R2
service timestamps log datetime msec
logging buffered 16384 informational
snmp-server community ENCOR-RO RO
snmp-server community ENCOR-RW RW
snmp-server host 2.2.2.2 version 2c ENCOR-RO
snmp-server enable traps snmp linkdown linkup coldstart
```
</details>

<details>
<summary>Click to view R3 Configuration</summary>

```bash
! R3
service timestamps log datetime msec
logging buffered 16384 informational
snmp-server community ENCOR-RO RO
snmp-server community ENCOR-RW RW
snmp-server host 2.2.2.2 version 2c ENCOR-RO
snmp-server enable traps snmp linkdown linkup coldstart
```
</details>

### Task 4: Conditional Debug ACL

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1
ip access-list extended DEBUG-FILTER
 permit ip host 192.168.10.10 any
```
</details>

### Tasks 5–7: Extended Ping, Traceroute, and Conditional Debug

<details>
<summary>Click to view Exec Commands (R1)</summary>

```bash
! Extended ping — loopback source, 1400-byte, DF bit
ping 3.3.3.3 source Loopback0 repeat 100 size 1400 df-bit

! Extended traceroute — loopback source, numeric
traceroute 3.3.3.3 source 1.1.1.1 numeric

! Conditional debug
debug ip packet detail DEBUG-FILTER
! (generate traffic from PC1)
undebug all
```
</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. Inject the fault first, then
diagnose and fix using only show commands.

### Workflow

```bash
python3 setup_lab.py --host <eve-ng-ip>                        # reset to known-good
python3 scripts/fault-injection/inject_scenario_01.py          # Ticket 1
python3 scripts/fault-injection/apply_solution.py              # restore
```

---

### Ticket 1 — SNMP Queries to R1 Return Authentication Failure

The NOC team reports that their monitoring platform cannot retrieve interface counters from R1. Their NMS is configured to use community string `ENCOR-RO` targeting 1.1.1.1. Queries to R2 and R3 succeed normally.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py`

**Success criteria:** `show snmp community` on R1 lists `ENCOR-RO` as a valid read-only community. A simulated SNMP GET using `show snmp` confirms the authenticationFailure counter stops incrementing.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. On R1, run `show snmp community` — confirm what communities are configured.
2. Look for `ENCOR-RO` in the output. If absent, or if a different name appears, the community is misconfigured.
3. Run `show snmp` and look for `authenticationFailure` traps sent — a climbing counter confirms the NMS is sending queries with a community R1 does not recognise.
4. Compare R1's communities against R2's (`show snmp community` on R2) to identify the discrepancy.
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! R1 — remove the wrong community and restore the correct one
conf t
no snmp-server community ENCOR-READONLY RO
snmp-server community ENCOR-RO RO
end
```
</details>

---

### Ticket 2 — Debug ip packet Produces No Output Despite Active Traffic

A junior engineer enabled `debug ip packet detail DEBUG-FILTER` on R1 to investigate a PC1 connectivity issue. PC1 is actively pinging PC2, but the console shows no debug lines at all.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py`

**Success criteria:** `debug ip packet detail DEBUG-FILTER` on R1 produces output lines showing packets from 192.168.10.10 when PC1 pings PC2. `show ip access-lists DEBUG-FILTER` shows match counts incrementing.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Run `show ip access-lists DEBUG-FILTER` — check what entries exist.
2. A `deny ip any any` (explicit or effectively empty ACL) will silently suppress all debug output because no packets match a permit.
3. The ACL must have `permit ip host 192.168.10.10 any` as an active entry.
4. Confirm by checking `show running-config | section DEBUG-FILTER`.
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! R1 — restore the missing permit entry
conf t
ip access-list extended DEBUG-FILTER
 permit ip host 192.168.10.10 any
end
```
</details>

---

### Ticket 3 — Syslog Buffer Shows No Events After Interface Flap

The operations team shut and re-enabled R1 GigabitEthernet0/1 during a maintenance window. When reviewing `show logging` afterward to confirm the interface state changes were recorded, the log buffer is empty.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py`

**Success criteria:** `show logging` on R1 shows `Logging to buffer (informational)` and the buffer contains interface state change entries after a subsequent interface flap.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Run `show logging` on R1 and examine the buffer logging line.
2. If it reads `Logging to buffer (errors)` or higher (lower number), interface state messages at severity 5 (notifications) are being discarded.
3. Interface %LINEPROTO and %LINK messages are generated at severity 3 (errors) and 5 (notifications). Setting the threshold to `errors` (3) captures the error-level messages but drops the normal-state notifications.
4. The fix is to lower the severity threshold to `informational` (6) so that all events 0–6 are captured.
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! R1 — set correct severity threshold
conf t
logging buffered 16384 informational
end
! Verify
show logging
! Flap an interface to generate a test event
conf t
interface GigabitEthernet0/1
 shutdown
 no shutdown
end
show logging
```
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] `show logging` on R1, R2, R3 — buffer level is `informational`, buffer size 16384 bytes
- [ ] `show logging` entries show datetime with millisecond timestamp format
- [ ] `show snmp community` on all routers — ENCOR-RO (RO) and ENCOR-RW (RW) present
- [ ] `show snmp host` on all routers — 2.2.2.2 listed as UDP trap destination, version 2c
- [ ] `show ip access-lists DEBUG-FILTER` on R1 — permit entry for host 192.168.10.10 present
- [ ] Extended ping from R1 to 3.3.3.3, source Loopback0, size 1400, DF bit — 100% success
- [ ] Extended traceroute from R1 to 3.3.3.3, source 1.1.1.1, numeric — exactly 2 hops shown
- [ ] Conditional debug generates output only for 192.168.10.10 traffic; `show debug` clear after `undebug all`

### Troubleshooting

- [ ] Ticket 1: `show snmp community` on R1 shows ENCOR-RO; authenticationFailure counter stops incrementing
- [ ] Ticket 2: `debug ip packet detail DEBUG-FILTER` produces output; `show ip access-lists DEBUG-FILTER` shows match counts
- [ ] Ticket 3: `show logging` on R1 shows `informational` level; interface flap event appears in buffer
