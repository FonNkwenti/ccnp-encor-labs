# Lab 03 — IP SLA Probes and Tracking

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

**Exam Objective:** 4.4 — Configure and verify IP SLA (network-assurance)

Passive monitoring tools like NetFlow and SPAN only see traffic that already exists. IP SLA fills the gap by actively injecting synthetic test traffic — pings, UDP probes, HTTP GETs — and continuously measuring round-trip time, jitter, and packet loss. This lab configures ICMP echo and UDP jitter probes from R1 to R3, adds an IPv6 ICMP echo probe for dual-stack coverage, then wires the ICMP probe to a track object that automatically removes a static route when R3 becomes unreachable.

---

### IP SLA Probe Types

An IP SLA operation defines the **type** of synthetic test, the **source**, the **destination**, and **timing parameters**. The router runs the probe on a schedule and records each result in the SLA statistics database.

| Operation Type | Responder Required | Measures | Common Use |
|---------------|-------------------|---------|-----------|
| `icmp-echo` | No | Round-trip time, packet loss | Basic reachability |
| `udp-jitter` | Yes | RTT, one-way delay, jitter, MOS | VoIP quality assessment |
| `tcp-connect` | No | TCP session setup time | Application availability |
| `http` | No | HTTP response time, DNS lookup | Web application monitoring |
| `path-jitter` | No | Jitter along each hop | Path characterization |

**IOS syntax — ICMP echo:**
```
ip sla <operation-number>
 icmp-echo <destination-ip> source-ip <source-ip>
 frequency <seconds>
ip sla schedule <operation-number> life forever start-time now
```

**IOS syntax — UDP jitter:**
```
ip sla <operation-number>
 udp-jitter <destination-ip> <port> source-ip <source-ip> num-packets <count>
 frequency <seconds>
ip sla schedule <operation-number> life forever start-time now
```

The `frequency` keyword sets how often the probe runs (in seconds). Without an explicit `ip sla schedule`, a configured probe never starts — this is the single most common misconfiguration on the exam.

---

### IP SLA Responder

The IP SLA responder is a lightweight process that runs on the target device and listens for incoming SLA probe packets. It is required for UDP jitter probes because the responder adds hardware timestamps to each response packet, enabling one-way delay measurements that are impossible with ICMP alone.

```
ip sla responder
```

This single global command enables the responder. It listens on all ports simultaneously — no per-port configuration is needed. ICMP echo probes do not require the responder; any device that responds to ping works as a target.

> **Key distinction:** `icmp-echo` targets any IP — the destination does not need to be a Cisco device. `udp-jitter` requires `ip sla responder` on the target.

---

### IP SLA Scheduling

A probe is inert until scheduled. The schedule command defines when the probe starts, how long it runs, and whether it repeats:

```
ip sla schedule <number> life {forever | <seconds>} start-time {now | hh:mm[:ss] [month day | day month] | pending | after hh:mm:ss}
```

| Parameter | Meaning |
|-----------|---------|
| `life forever` | Probe runs indefinitely (exam default) |
| `start-time now` | Starts immediately when command is entered |
| `start-time pending` | Configured but not yet running |
| `start-time after` | Delayed start (useful for maintenance windows) |

After scheduling, `show ip sla statistics` confirms the probe is active and shows the latest RTT, success/failure count, and last measurement timestamp.

---

### Track Objects and IP SLA Integration

A track object watches an IP SLA probe's reachability state (up/down) and exposes it as a boolean signal. Other IOS features — static routes, HSRP, PBR — can subscribe to a track object to take automatic action when connectivity changes.

```
track <track-id> ip sla <operation-number> reachability
 delay down <seconds> up <seconds>
```

The `delay` values add dampening: the track does not change state until the probe has been continuously up (or down) for the specified number of seconds. This prevents route flapping when a link is marginal.

**Tracked static route:**
```
ip route <prefix> <mask> <next-hop> track <track-id>
```

When track state is **Up**, the route is installed with its normal Administrative Distance (1 for static). When track state is **Down**, the route is withdrawn — OSPF's lower-preference route (AD 110) takes over automatically, achieving policy-based failover without any manual intervention.

| Track State | Route State | Routing Decision |
|------------|-------------|-----------------|
| Up | Installed (AD 1) | Traffic uses static route |
| Down | Withdrawn | OSPF route (AD 110) takes over |

---

### IPv6 IP SLA

IP SLA supports IPv6 destinations natively. The router auto-detects that the destination is an IPv6 address and applies the correct probe logic:

```
ip sla <number>
 icmp-echo <ipv6-destination> source-interface <interface>
 frequency <seconds>
ip sla schedule <number> life forever start-time now
```

Note: IPv6 probes use `source-interface` rather than `source-ip` — the router derives the IPv6 source address from the interface's configured address.

---

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| IP SLA probe configuration | Define ICMP echo and UDP jitter operations with correct source/destination parameters |
| IP SLA scheduling | Schedule probes with `life forever start-time now` |
| Responder configuration | Enable `ip sla responder` on the target for UDP jitter measurement |
| Track object creation | Link a track object to an SLA probe's reachability state with dampening delays |
| Tracked static routes | Tie a static route to a track object for automatic path failover |
| IPv6 SLA probes | Configure dual-stack monitoring with IPv6 ICMP echo |
| SLA statistics interpretation | Read RTT, jitter, packet loss, and success/failure ratio from `show ip sla statistics` |

---

## 2. Topology & Scenario

**Scenario:** Meridian Financial has tasked you with adding active monitoring to their edge network. R1 serves as the edge router; R3 hosts a critical application database. You must configure synthetic probes to continuously test reachability and application-layer quality to R3, and automate failover if R3 becomes unreachable. The existing SPAN, RSPAN, and NetFlow infrastructure remains in place from the previous labs.

```
                         ┌───────────────────────────────────┐
                         │               R1                  │
                         │          (Edge Router)            │
                         │       Lo0: 1.1.1.1/32             │
                         │  IP SLA source — probes 1, 2, 3   │
                         └──────┬──────────────┬─────────────┘
              Gi0/0             │              │             Gi0/1
        192.168.10.1/24         │              │        10.1.12.1/30
        2001:db8:10::1/64       │              │       2001:db8:12::1/64
                                │              │
        192.168.10.0/24         │              │        10.1.12.0/30
               ┌────────────────┘              └────────────────────────┐
               │                                                        │
     ┌─────────┴──────────┐                             Gi0/1           │
     │        SW1         │                       10.1.12.2/30          │
     │  (Access Switch)   │                      2001:db8:12::2/64      │
     │  MGMT: 192.168.    │                                    ┌────────┴────────────┐
     │       99.11/24     │                                    │        R2           │
     └──┬─────────────┬───┘                                    │ (Distribution Rtr)  │
  Gi0/3 │         Gi0/1│ trunk                                 │   Lo0: 2.2.2.2/32   │
(PC1    │              │ VLANs                                 │ NetFlow collector   │
 port)  │              │ 10,20,99,500                          └────┬───────────┬────┘
        │              │                                     Gi0/0  │           │ Gi0/2
  PC1───┘        ┌─────┴──────────┐                  192.168.20.1/24│           │ 10.1.23.1/30
192.168.10.10    │      SW2       │              2001:db8:20::1/64  │           │ 2001:db8:23::1/64
                 │ (Dist Switch)  │                                 │           │
                 │  MGMT: 192.168.│                    192.168.20.0 │           │ 10.1.23.0/30
                 │       99.12/24 │                   ┌─────────────┘           │
                 └──┬──────────┬──┘                   │                         │
              Gi0/3 │      Gi0/2│                   SW2:Gi0/2                   │
           (PC2     │           │                                   ┌────────────┴────────┐
            port)   │           └──────────── PC2 ──────┘          │         R3          │
                    │            192.168.20.10                      │   (Remote Router)   │
             PC2────┘                                               │   Lo0: 3.3.3.3/32   │
                                                                    │ IP SLA responder    │
                                                                    │ SLA target          │
                                                                    └─────────────────────┘
```

**IP SLA Probe Summary:**

| SLA ID | Type | Source | Destination | Purpose |
|--------|------|--------|-------------|---------|
| 1 | ICMP echo | R1 Lo0 (1.1.1.1) | R3 Lo0 (3.3.3.3) | Basic reachability — feeds Track 1 |
| 2 | UDP jitter | R1 Lo0 (1.1.1.1) | R3:5000 | Delay/jitter/loss measurement |
| 3 | IPv6 ICMP echo | R1 Gi0/1 | R3 Gi0/0 (2001:db8:23::2) | Dual-stack reachability |

**Track Object:**

| Track ID | Monitors | Action on Down |
|----------|---------|---------------|
| 1 | SLA 1 reachability | Removes static route to 10.1.23.0/30; OSPF takes over |

---

## 3. Hardware & Environment Specifications

### Device List

| Device | Platform | Role | IOS Version |
|--------|----------|------|-------------|
| R1 | IOSv (vios-adventerprisek9) | Edge router — IP SLA source | 15.x |
| R2 | IOSv (vios-adventerprisek9) | Distribution router | 15.x |
| R3 | IOSv (vios-adventerprisek9) | Remote router — IP SLA responder | 15.x |
| SW1 | IOSvL2 (vios_l2-adventerprisek9) | Access switch | 15.x |
| SW2 | IOSvL2 (vios_l2-adventerprisek9) | Distribution switch | 15.x |
| PC1 | VPCS | Traffic source | — |
| PC2 | VPCS | Traffic destination | — |

### Cabling Table

| Link | Device A | Interface | Device B | Interface | Subnet |
|------|----------|-----------|----------|-----------|--------|
| L1 | SW1 | Gi0/1 | SW2 | Gi0/1 | trunk (VLANs 10,20,99,500) |
| L2 | R1 | Gi0/0 | SW1 | Gi0/2 | 192.168.10.0/24 |
| L3 | R2 | Gi0/0 | SW2 | Gi0/2 | 192.168.20.0/24 |
| L4 | R1 | Gi0/1 | R2 | Gi0/1 | 10.1.12.0/30 |
| L5 | R2 | Gi0/2 | R3 | Gi0/0 | 10.1.23.0/30 |
| L6 | PC1 | eth0 | SW1 | Gi0/3 | VLAN 10 |
| L7 | PC2 | eth0 | SW2 | Gi0/3 | VLAN 20 |

SW1:Gi0/0 — local SPAN destination (monitoring port)
SW2:Gi0/0 — RSPAN destination (remote monitoring port)

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

The following is pre-loaded on all devices when the lab starts. Run `setup_lab.py` to push the initial configs.

### Pre-configured on all devices

- IP addressing on all interfaces (IPv4 and IPv6)
- OSPF process 1 in area 0 on all router-to-router links and loopbacks
- OSPFv3 (classic `ipv6 router ospf 1`) for IPv6 routing
- Passive interfaces on R1:Gi0/0 and R2:Gi0/0 (LAN-facing)
- VLANs 10, 20, 99, and 500 (RSPAN) on SW1 and SW2
- Trunk between SW1 and SW2 (VLANs 10, 20, 99, 500)
- SPAN and RSPAN monitoring sessions from Lab 02
- Flexible NetFlow pipeline (record, exporter, monitor) from Lab 01
- SNMP v2c communities and syslog buffering from Lab 00
- PC1: `192.168.10.10/24` gateway `192.168.10.1`
- PC2: `192.168.20.10/24` gateway `192.168.20.1`

### NOT pre-configured (your task)

- IP SLA probes (ICMP echo, UDP jitter, IPv6 ICMP echo)
- SLA scheduling on any probe
- IP SLA responder on R3
- Track object linked to SLA 1 reachability
- Tracked static route on R1

---

## 5. Lab Challenge: Core Implementation

### Task 1: ICMP Echo Probe to R3

- On R1, create IP SLA operation 1 as an ICMP echo probe targeting R3's loopback address (3.3.3.3). Use R1's loopback address (1.1.1.1) as the source.
- Set the probe frequency to 30 seconds.
- Schedule the probe to run immediately and continue indefinitely.

**Verification:** `show ip sla statistics 1` must show at least one successful round, RTT values populated, and zero failures. `show ip sla configuration 1` must confirm the destination and source IP.

---

### Task 2: UDP Jitter Probe with Responder

- On R3, enable the IP SLA responder globally so R3 can respond to jitter probes.
- On R1, create IP SLA operation 2 as a UDP jitter probe targeting R3 (3.3.3.3) on port 5000. Use R1's loopback (1.1.1.1) as the source. Send 10 packets per probe cycle.
- Set the probe frequency to 60 seconds.
- Schedule the probe to run immediately and continue indefinitely.

**Verification:** `show ip sla statistics 2` must show RTT summary data, jitter values, and zero timeouts. `show ip sla responder` on R3 must confirm the responder is active.

---

### Task 3: Track Object and Automatic Failover

- Create track object 1 on R1 that monitors IP SLA operation 1's reachability state. Add a 10-second up/down state change delay to prevent flapping.
- Add a static route on R1 for the R2-to-R3 point-to-point subnet (10.1.23.0/30) via R2's address (10.1.12.2), conditioned on track object 1 being Up.

**Verification:** `show track 1` must show the track is Up and reference SLA operation 1. `show ip route 10.1.23.0` must show the static route installed (AD 1). Shut an interface to simulate R3 loss and verify the static route is withdrawn after the delay.

---

### Task 4: IPv6 ICMP Echo Probe

- On R1, create IP SLA operation 3 as an IPv6 ICMP echo probe targeting R3's IPv6 address on the R2-R3 link (2001:db8:23::2). Use R1's Gi0/1 interface as the source.
- Set the probe frequency to 30 seconds.
- Schedule the probe to run immediately and continue indefinitely.

**Verification:** `show ip sla statistics 3` must show successful RTT measurements. The output header must confirm the target address is the IPv6 address, not an IPv4 address.

---

## 6. Verification & Analysis

### Task 1 — ICMP Echo Probe

```
R1# show ip sla configuration 1
IP SLAs Infrastructure Engine-III
Entry number: 1
Owner:
Tag:
Operation timeout (milliseconds): 5000
Type of operation to perform: icmp-echo       ! ← must be icmp-echo
Target address/Source address: 3.3.3.3/1.1.1.1  ! ← correct dest and source
Type Of Service parameter: 0x0
Request size (ARR data portion): 28
Operation frequency (seconds): 30             ! ← 30-second interval confirmed
Next scheduled start time: Start Time already passed
Group Scheduled : FALSE
Randomly Scheduled : FALSE
Life (seconds): Forever                       ! ← life forever confirmed
Entry Ageout (seconds): never
Recurring (Starting Everyday): FALSE
Status of entry (SNMP RowStatus): Active
Threshold (milliseconds): 5000
Distribution Statistics:
  Number of statistic hours kept: 2
  Number of statistic distribution buckets kept: 1
  Statistic distribution interval (milliseconds): 20
Enhanced History:
```

```
R1# show ip sla statistics 1
IPSLAs Latest Operation Statistics

IPSLA operation id: 1
        Latest RTT: 2 milliseconds                ! ← RTT populated (not N/A)
Latest operation start time: *00:05:12.345 UTC
Latest operation return code: OK                  ! ← OK = success
Number of successes: 10                           ! ← at least 1 success
Number of failures: 0                             ! ← zero failures
Operation time to live: Forever
```

### Task 2 — UDP Jitter Probe and Responder

```
R3# show ip sla responder
General IP SLA Responder Info
  Status: Active                                  ! ← must be Active
  Responder is enabled.
  Number of control packets received: 2
  Number of responses sent: 2
```

```
R1# show ip sla statistics 2
IPSLAs Latest Operation Statistics

IPSLA operation id: 2
        Latest RTT: 3 milliseconds
Latest operation start time: *00:06:00.123 UTC
Latest operation return code: OK                  ! ← OK (not "No Connection")
Number of successes: 3                            ! ← successes > 0
Number of failures: 0
RTT Values:
        Number Of RTT: 10
        RTT Min/Avg/Max: 2/3/5 milliseconds       ! ← jitter data populated
Packet Loss Values:
        Loss Source to Destination: 0             ! ← zero packet loss
        Loss Destination to Source: 0
Jitter Values:
        Jitter Min/Avg/Max: 0/1/2 milliseconds    ! ← jitter values present
        Positive SD Jitter Min/Avg/Max: 0/1/2
        Negative SD Jitter Min/Avg/Max: 0/1/2
Operation time to live: Forever
```

### Task 3 — Track Object and Tracked Static Route

```
R1# show track 1
Track 1
  IP SLA 1 Reachability                          ! ← references SLA 1
  Reachability is Up                             ! ← must be Up
    1 change, last change 00:01:05
  Delay up 10 secs, down 10 secs                 ! ← delay confirmed
  Latest operation return code: OK
  Latest RTT (milliseconds) 2

Tracked by:
  Static IP Routing 0                            ! ← route is watching this track
```

```
R1# show ip route 10.1.23.0
Routing entry for 10.1.23.0/30
  Known via "static", distance 1, metric 0       ! ← AD 1 = static is active
  Tag 0, type unicast
  Redistributing via ospf 1
  Last update from 10.1.12.2 on GigabitEthernet0/1, 00:02:00 ago
  Routing Descriptor Blocks:
  * 10.1.12.2, via GigabitEthernet0/1
      Route metric is 0, traffic share count is 1
```

After simulating R3 loss (30+ seconds after track goes Down):

```
R1# show ip route 10.1.23.0
Routing entry for 10.1.23.0/30
  Known via "ospf 1", distance 110, metric 3     ! ← OSPF (AD 110) took over
  ...
```

```
R1# show track 1
Track 1
  IP SLA 1 Reachability
  Reachability is Down                           ! ← track went Down
    2 changes, last change 00:00:15
```

### Task 4 — IPv6 ICMP Echo Probe

```
R1# show ip sla statistics 3
IPSLAs Latest Operation Statistics

IPSLA operation id: 3
        Latest RTT: 3 milliseconds               ! ← RTT populated
Latest operation start time: *00:08:30.456 UTC
Latest operation return code: OK                 ! ← OK = IPv6 probe succeeded
Number of successes: 5                           ! ← successes > 0
Number of failures: 0
Operation time to live: Forever
```

```
R1# show ip sla configuration 3
IP SLAs Infrastructure Engine-III
Entry number: 3
...
Type of operation to perform: icmp-echo
Target address/Source address: 2001:DB8:23::2/GigabitEthernet0/1  ! ← IPv6 dest confirmed
Operation frequency (seconds): 30
Life (seconds): Forever
```

---

## 7. Verification Cheatsheet

### IP SLA Configuration Commands

```
ip sla <number>
 icmp-echo <destination> source-ip <source>
 frequency <seconds>

ip sla <number>
 udp-jitter <destination> <port> source-ip <source> num-packets <count>
 frequency <seconds>

ip sla schedule <number> life forever start-time now
```

| Command | Purpose |
|---------|---------|
| `ip sla <N>` | Enter IP SLA operation config mode |
| `icmp-echo <dst> source-ip <src>` | Define ICMP echo probe destination and source IP |
| `udp-jitter <dst> <port> source-ip <src> num-packets <N>` | Define UDP jitter probe |
| `frequency <sec>` | Set probe interval in seconds |
| `ip sla schedule <N> life forever start-time now` | Schedule probe to start immediately and run forever |
| `ip sla responder` | Enable SLA responder on target device (required for UDP jitter) |

> **Exam tip:** An IP SLA probe does nothing without `ip sla schedule`. A configured but unscheduled SLA is a common exam trap — always verify with `show ip sla configuration`.

### Track Object Commands

```
track <id> ip sla <operation-number> reachability
 delay down <seconds> up <seconds>

ip route <prefix> <mask> <next-hop> track <id>
```

| Command | Purpose |
|---------|---------|
| `track <id> ip sla <N> reachability` | Create track object watching SLA probe state |
| `delay down <sec> up <sec>` | Add dampening to prevent state flapping |
| `ip route ... track <id>` | Conditional static route — only active when track is Up |

> **Exam tip:** The `delay` values under a track object are in seconds, not milliseconds. A `delay down 10` means the track waits 10 seconds of continuous Down state before signaling Down to subscribers.

### IPv6 IP SLA

```
ip sla <number>
 icmp-echo <ipv6-destination> source-interface <interface>
 frequency <seconds>
ip sla schedule <number> life forever start-time now
```

| Command | Purpose |
|---------|---------|
| `icmp-echo <ipv6-addr> source-interface <intf>` | IPv6 ICMP echo using interface as source (not `source-ip`) |

> **Exam tip:** IPv6 SLA probes use `source-interface`, not `source-ip`. The router auto-detects the IPv6 address family from the destination format.

### Verification Commands

| Command | What to Look For |
|---------|-----------------|
| `show ip sla statistics [N]` | Latest RTT, return code (must be OK), success/failure counts |
| `show ip sla statistics [N] details` | Full RTT distribution, jitter breakdown, MOS score (UDP jitter) |
| `show ip sla configuration [N]` | Confirm destination, source, frequency, type, and schedule |
| `show ip sla summary` | One-line status for all configured SLA operations |
| `show ip sla responder` | Confirm responder is Active on R3 |
| `show track [id]` | Track state (Up/Down), delay config, SLA reference, and subscribers |
| `show track brief` | One-line summary for all track objects |
| `show ip route` | Verify tracked static route is installed (AD 1 when track Up) |

### Common IP SLA Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| Return code: Timeout | Destination unreachable, or firewall blocking ICMP |
| Return code: No Connection | UDP jitter probe, but responder not enabled on target |
| Return code: Over threshold | RTT exceeded configured threshold value |
| Successes: 0, Failures: N | Probe running but all packets lost — check routing to destination |
| Statistics never update | Probe configured but `ip sla schedule` not entered |
| Track stays Down despite reachability | Wrong SLA operation number referenced in track object |
| Static route missing despite track Up | Typo in `ip route` prefix/mask, or wrong track ID |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Task 1: ICMP Echo Probe

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1 — IP SLA 1: ICMP echo to R3 Lo0
ip sla 1
 icmp-echo 3.3.3.3 source-ip 1.1.1.1
 frequency 30
ip sla schedule 1 life forever start-time now
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ip sla configuration 1
show ip sla statistics 1
```
</details>

---

### Task 2: UDP Jitter Probe and Responder

<details>
<summary>Click to view R3 Configuration</summary>

```bash
! R3 — Enable IP SLA responder
ip sla responder
```
</details>

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1 — IP SLA 2: UDP jitter to R3
ip sla 2
 udp-jitter 3.3.3.3 5000 source-ip 1.1.1.1 num-packets 10
 frequency 60
ip sla schedule 2 life forever start-time now
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
! On R3:
show ip sla responder

! On R1:
show ip sla statistics 2
show ip sla statistics 2 details
```
</details>

---

### Task 3: Track Object and Automatic Failover

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1 — Track object and tracked static route
track 1 ip sla 1 reachability
 delay down 10 up 10
!
ip route 10.1.23.0 255.255.255.252 10.1.12.2 track 1
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show track 1
show ip route 10.1.23.0
show ip route
```
</details>

---

### Task 4: IPv6 ICMP Echo Probe

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1 — IP SLA 3: IPv6 ICMP echo to R3 Gi0/0 IPv6 address
ip sla 3
 icmp-echo 2001:db8:23::2 source-interface GigabitEthernet0/1
 frequency 30
ip sla schedule 3 life forever start-time now
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ip sla statistics 3
show ip sla configuration 3
```
</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. Inject the fault first, then diagnose and fix using only show commands.

### Workflow

```bash
python3 setup_lab.py                                   # reset to known-good
python3 scripts/fault-injection/inject_scenario_01.py  # Ticket 1
python3 scripts/fault-injection/apply_solution.py      # restore
```

---

### Ticket 1 — ICMP Echo Probe to R3 Reports 100% Packet Loss

You are on shift and receive an alert that the reachability monitor for R3 has recorded 100% packet loss for the last five probe cycles. All other routing is functioning normally — OSPF adjacencies are up and PC1 can reach PC2. Investigate why SLA probe 1 is failing.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py`

**Success criteria:** `show ip sla statistics 1` returns code OK with zero failures and RTT values populated.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Run `show ip sla statistics 1` — confirm the return code shows `Timeout` or `No route to host`, and failures are non-zero.
2. Run `show ip sla configuration 1` — inspect the target address. Compare it against R3's loopback (`show ip interface brief` on R3 = 3.3.3.3).
3. Run `ping 3.3.3.4` from R1 — this should fail (destination does not exist), confirming the probe is aimed at the wrong IP.
4. Run `ping 3.3.3.3 source loopback 0` from R1 — this succeeds, confirming R3 is reachable but the SLA destination is wrong.
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! On R1 — remove the misconfigured SLA and reconfigure with the correct destination
no ip sla schedule 1
no ip sla 1
ip sla 1
 icmp-echo 3.3.3.3 source-ip 1.1.1.1
 frequency 30
ip sla schedule 1 life forever start-time now
```

Verify: `show ip sla statistics 1` — return code must be OK within 30 seconds.
</details>

---

### Ticket 2 — UDP Jitter Probe Returns "No Connection" Error

You have just deployed IP SLA probe 2 (UDP jitter) on R1 targeting R3 port 5000. The probe configuration looks correct on R1, but `show ip sla statistics 2` consistently shows return code `No connection`. All ICMP pings from R1 to R3 succeed.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py`

**Success criteria:** `show ip sla statistics 2` shows return code OK with RTT and jitter values populated.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Run `show ip sla statistics 2` on R1 — confirm return code is `No connection`.
2. Run `ping 3.3.3.3 source loopback 0` from R1 — succeeds, so routing is not the problem.
3. Note that `No connection` on a UDP jitter probe specifically indicates the target is not listening. ICMP echo would return `Timeout` for a routing problem; `No connection` means the target host is up but the responder is not running.
4. Log into R3 and run `show ip sla responder` — confirm the responder status is inactive or not configured.
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! On R3 — enable the IP SLA responder
ip sla responder
```

Verify: `show ip sla responder` on R3 shows `Status: Active`. Within 60 seconds, `show ip sla statistics 2` on R1 shows return code OK.
</details>

---

### Ticket 3 — Tracked Static Route to R2-R3 Subnet Missing from Routing Table

Track object 1 is configured and appears to be running. However, `show ip route` on R1 shows the R2-R3 link subnet (10.1.23.0/30) is being learned via OSPF (AD 110) rather than the tracked static route (AD 1). OSPF adjacencies are intact and R3 is fully reachable via ICMP.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py`

**Success criteria:** `show ip route 10.1.23.0` shows the route via `static` at AD 1. `show track 1` shows Reachability is Up and references SLA 1.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Run `show ip route 10.1.23.0` — confirm the route source is `ospf 1` (AD 110), not `static` (AD 1).
2. Run `show track 1` — inspect which SLA operation the track references. The output will show `IP SLA 10 Reachability` instead of `IP SLA 1 Reachability`. SLA 10 does not exist, so the track is permanently Down.
3. Run `show ip sla summary` — confirm only SLA operations 1, 2, and 3 are defined. SLA 10 is not present.
4. The root cause: the track object was misconfigured to reference SLA 10 (which does not exist) instead of SLA 1.
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! On R1 — remove the misconfigured track and reconfigure it to reference SLA 1
no track 1
track 1 ip sla 1 reachability
 delay down 10 up 10
```

Verify: `show track 1` shows `IP SLA 1 Reachability` and `Reachability is Up`. Within 10 seconds (up delay), `show ip route 10.1.23.0` shows the static route at AD 1.
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] **Task 1:** SLA 1 (ICMP echo) configured targeting 3.3.3.3 with source 1.1.1.1, frequency 30, scheduled `life forever start-time now`
- [ ] **Task 1:** `show ip sla statistics 1` shows return code OK and zero failures
- [ ] **Task 2:** `ip sla responder` enabled on R3
- [ ] **Task 2:** SLA 2 (UDP jitter) configured targeting 3.3.3.3 port 5000, 10 packets, frequency 60, scheduled
- [ ] **Task 2:** `show ip sla statistics 2` shows return code OK with jitter values populated
- [ ] **Task 3:** Track 1 references SLA 1 reachability with `delay down 10 up 10`
- [ ] **Task 3:** Tracked static route for 10.1.23.0/30 via 10.1.12.2 conditioned on track 1
- [ ] **Task 3:** `show ip route 10.1.23.0` shows static route at AD 1 when track is Up
- [ ] **Task 4:** SLA 3 (IPv6 ICMP echo) configured targeting 2001:db8:23::2 via Gi0/1, frequency 30, scheduled
- [ ] **Task 4:** `show ip sla statistics 3` shows return code OK for IPv6 probe

### Troubleshooting

- [ ] **Ticket 1:** Identified wrong SLA destination IP; corrected to 3.3.3.3 and verified probe succeeds
- [ ] **Ticket 2:** Identified missing `ip sla responder` on R3; enabled and verified UDP jitter probe succeeds
- [ ] **Ticket 3:** Identified track object referencing non-existent SLA 10; corrected to SLA 1 and verified static route reinstalled
