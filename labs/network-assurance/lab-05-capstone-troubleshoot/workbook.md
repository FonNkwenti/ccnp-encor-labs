# Network Assurance Comprehensive Troubleshooting — Capstone II
## Lab 05: Capstone Troubleshoot | CCNP ENCOR 350-401 | Blueprint 4.1–4.4

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

**Exam Objective:** 4.1 — Diagnose network problems using debugs, conditional debugs, traceroute, ping, SNMP, and syslog | 4.2 — Configure and verify Flexible NetFlow | 4.3 — Configure SPAN/RSPAN/ERSPAN | 4.4 — Configure and verify IP SLA

This capstone tests your ability to diagnose and restore five concurrent faults across all four Network Assurance blueprint bullets. Unlike the progressive labs, you receive no guided steps — only symptoms. You must identify root causes using `show` commands, correlate evidence across tools, and apply precise fixes. This simulates the real-world scenario of inheriting a misconfigured network and restoring full observability.

### The Troubleshooter's Method

Effective network troubleshooting follows a consistent pattern: gather symptoms, isolate the layer and tool responsible, identify the exact misconfiguration, apply the minimum change, and verify the fix did not break anything else. When five faults are concurrent, prioritize by impact (connectivity before monitoring) and work from the data plane toward the management plane.

For this lab, the faults are independent — fixing one does not fix another. You can work in any order, but the verification outputs in Section 6 provide a complete reference for the known-good state.

| Troubleshooting Approach | Application |
|--------------------------|-------------|
| Divide and conquer | Isolate each tool's config independently |
| Layer-by-layer | Confirm OSPF/routing before blaming monitoring tools |
| State comparison | Compare `show` output to expected values in Section 6 |
| Minimum viable fix | Change only what is broken; do not reconfigure working components |

### SNMP Trap Delivery Troubleshooting

SNMP traps are UDP datagrams — they are fire-and-forget. If a trap never reaches its receiver, the router has no error to report; the misconfiguration is silent. The key diagnostic is `show snmp` which lists the configured trap destinations. A wrong IP address means traps are silently discarded at the destination.

```
show snmp
show snmp host
show snmp community
```

The trap host address in `snmp-server host <ip>` must match the reachable IP of the receiver. In this topology, R2's Loopback0 (`2.2.2.2`) is the collector — any other IP causes silent trap loss.

### Flexible NetFlow Interface Application Troubleshooting

A flow monitor is defined globally but must be explicitly applied to each interface where flows should be captured. Missing an interface is one of the most common NetFlow misconfigurations: the monitor exists and exports correctly for applied interfaces, but traffic on unapplied interfaces is silently uncounted.

```
show flow interface
show flow monitor <name> cache
show flow exporter <name> statistics
```

`show flow interface` reveals which interfaces have a monitor applied and in which direction. If an interface is absent from the output, no flows are captured on it — regardless of how much traffic transits it.

### SPAN and RSPAN Session Troubleshooting

SPAN session problems fall into two categories: wrong source/destination (configuration error) and RSPAN VLAN not propagated (infrastructure error). Both produce the same symptom — the monitor port captures nothing or the wrong traffic.

```
show monitor session all
show monitor session <N>
show vlan brief
show interfaces trunk
```

For RSPAN: VLAN 500 must be configured as `remote-span` on both switches AND must appear in the trunk's `allowed vlan` list. A VLAN defined as remote-span but pruned from the trunk means RSPAN frames are silently dropped at the trunk boundary.

### IP SLA Responder Troubleshooting

UDP jitter probes require the IP SLA responder to be enabled on the target device. Without the responder, the probe destination has no listening socket and returns an ICMP port-unreachable, causing the SLA operation to report "No connection." ICMP echo probes do not need a responder — only UDP jitter does.

```
show ip sla statistics
show ip sla configuration
```

The `Return Code` field in `show ip sla statistics` is diagnostic: `OK` = success, `No connection` = responder not running, `Timeout` = routing/reachability failure. The two codes have different root causes and must not be confused.

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| Multi-fault correlation | Isolating concurrent independent faults without cross-contamination |
| Silent failure recognition | Identifying misconfigurations that produce no error messages |
| Show-command-only diagnosis | Building the full picture from `show` output alone |
| SNMP trap path verification | Validating trap destination configuration end-to-end |
| NetFlow interface coverage audit | Confirming all required interfaces have monitor applied |
| SPAN/RSPAN session validation | Reading session state and trunk VLAN lists together |
| IP SLA return code interpretation | Distinguishing No Connection from Timeout |

---

## 2. Topology & Scenario

**Scenario:** You have inherited the ENCOR monitoring lab from a colleague who left mid-configuration. Users report that the monitoring dashboard is largely dark — no NetFlow data from the core link, no SNMP traps arriving at the collector, the remote mirror port is blank, the local mirror is showing the wrong traffic, and one IP SLA probe keeps failing. Your task is to identify and fix all five faults without restarting any devices.

```
                         ┌───────────────────────────────────────┐
                         │                 R1                    │
                         │          (Edge Router)                │
                         │         Lo0: 1.1.1.1/32               │
                         │  SLA source · NetFlow exporter        │
                         │  Syslog · SNMP · Debug                │
                         └──────┬───────────────┬────────────────┘
              Gi0/0             │               │              Gi0/1
        192.168.10.1/24         │               │         10.1.12.1/30
        2001:db8:10::1/64       │               │        2001:db8:12::1/64
                                │               │
        192.168.10.0/24         │               │         10.1.12.0/30
               ┌────────────────┘               └────────────────────────┐
               │                                                         │
     ┌─────────┴──────────┐                              Gi0/1           │
     │        SW1         │                        10.1.12.2/30          │
     │  (Access Switch)   │                       2001:db8:12::2/64      │
     │  MGMT: 192.168.    │                                    ┌─────────┴───────────┐
     │       99.11/24     │                                    │         R2          │
     └──┬──────────────┬──┘                                    │ (Distribution Rtr)  │
  Gi0/3 │          Gi0/1│ trunk                                │   Lo0: 2.2.2.2/32   │
(PC1    │               │ VLANs                                │ NetFlow collector   │
 port)  │               │ 10,20,99,500                         └──┬──────────────────┘
        │               │                                   Gi0/0 │           │ Gi0/2
  PC1───┘        ┌──────┴─────────┐                 192.168.20.1/24│           │ 10.1.23.1/30
192.168.10.10    │      SW2       │             2001:db8:20::1/64  │           │ 2001:db8:23::1/64
                 │ (Dist Switch)  │                                │           │
                 │  MGMT: 192.168.│                   192.168.20.0 │           │ 10.1.23.0/30
                 │       99.12/24 │                  ┌─────────────┘           │
                 └──┬──────────┬──┘                  │                         │
              Gi0/3 │      Gi0/2│                  SW2:Gi0/2        ┌──────────┴──────────┐
           (PC2     │           │                                   │          R3         │
            port)   │           │                                   │  (Remote Router)    │
             PC2────┘                                               │   Lo0: 3.3.3.3/32   │
                                                                    │ IP SLA responder    │
                                                                    └─────────────────────┘
```

**RSPAN VLAN 500** flows: SW1 Gi0/3 (PC1) → RSPAN session 2 → VLAN 500 → trunk Gi0/1 → SW2 → RSPAN session 1 → SW2 Gi0/0 (remote monitor)

---

## 3. Hardware & Environment Specifications

### Physical Cabling

| Link | Source | Destination | Type | Subnet / VLAN |
|------|--------|-------------|------|---------------|
| L1 | SW1 Gi0/1 | SW2 Gi0/1 | Trunk | VLANs 10, 20, 99, 500 |
| L2 | R1 Gi0/0 | SW1 Gi0/2 | Access | VLAN 10 / 192.168.10.0/24 |
| L3 | R2 Gi0/0 | SW2 Gi0/2 | Access | VLAN 20 / 192.168.20.0/24 |
| L4 | R1 Gi0/1 | R2 Gi0/1 | P2P | 10.1.12.0/30 |
| L5 | R2 Gi0/2 | R3 Gi0/0 | P2P | 10.1.23.0/30 |
| L6 | PC1 | SW1 Gi0/3 | Access | VLAN 10 |
| L7 | PC2 | SW2 Gi0/3 | Access | VLAN 20 |

### Console Access Table

| Device | Role | Port | Connection Command |
|--------|------|------|--------------------|
| R1 | Edge router / NetFlow exporter | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R2 | Distribution / NetFlow collector | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R3 | Remote router / IP SLA responder | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| SW1 | Access switch / SPAN source | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| SW2 | Distribution switch / RSPAN dest | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| PC1 | Traffic source | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| PC2 | Traffic destination | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |

---

## 4. Base Configuration

The initial-configs loaded by `setup_lab.py` include the following (pre-broken state):

**Pre-configured on all routers:**
- Hostnames and interface IP addressing (IPv4 and IPv6)
- OSPFv2 and OSPFv3 (both running, all routes present)
- Syslog buffering with timestamps
- SNMP v2c communities and trap configuration (with one fault)

**Pre-configured on R1:**
- Flexible NetFlow pipeline — flow record, exporter, monitor (with one fault)
- IP SLA probes 1, 2, and 3 (all scheduled, two running correctly)
- Track object 1 tied to IP SLA 1
- Tracked static route to 10.1.23.0/30

**Pre-configured on R3:**
- OSPF routing (with one fault in monitoring config)

**Pre-configured on SW1 and SW2:**
- VLAN database (10, 20, 99, 500 as remote-span)
- Trunk and access port assignments (with two faults)
- SPAN and RSPAN session configuration (with two faults)

**NOT working at lab start (student must diagnose and fix):**
- SNMP trap delivery to R2
- NetFlow flow capture on the R1-R2 link
- IP SLA UDP jitter probe (SLA 2)
- Local SPAN session (correct traffic being mirrored)
- RSPAN session (remote mirror reaching SW2)

---

## 5. Lab Challenge: Comprehensive Troubleshooting

> This is a capstone lab. The network is pre-broken.
> Diagnose and resolve 5+ concurrent faults spanning all blueprint bullets.
> No step-by-step guidance is provided — work from symptoms only.

**Your mission:** Restore all five monitoring and diagnostic systems to operational state. The faults are concurrent and independent. Use `show` commands to identify each root cause before applying any fix.

**Objectives — all five must be resolved:**

- SNMP traps from R1 must reach R2 (Loopback0 `2.2.2.2`) — verify with `show snmp host`
- Flexible NetFlow must capture flows on both R1 Gi0/0 and Gi0/1 — verify with `show flow interface`
- IP SLA probe 2 (UDP jitter to R3) must return `Return Code: OK` — verify with `show ip sla statistics 2`
- SW1 local SPAN session 1 must mirror PC1 traffic (Gi0/3) to Gi0/0 — verify with `show monitor session 1`
- RSPAN must deliver PC1 mirrored traffic to SW2 Gi0/0 — verify with `show monitor session 1` on SW2

**Constraints:**
- Use only `show` commands to diagnose — no debug during initial investigation
- Apply minimum changes — do not reconfigure working components
- Do not reload any device

---

## 6. Verification & Analysis

This section shows the expected output for all five monitoring systems in the known-good state. Use these as your target when verifying fixes.

### Fault 1 Fix Verification — SNMP Trap Host

```
R1# show snmp host
Notification host: 2.2.2.2   udp-port: 162   type: trap   ! ← must be 2.2.2.2, not 2.2.2.3
  user: ENCOR-RO   security model: v2c

R1# show snmp
...
SNMP global trap: enabled
Number of Traps sent to 2.2.2.2: <non-zero after a link event>   ! ← confirms delivery attempt
```

### Fault 2 Fix Verification — NetFlow on Both Interfaces

```
R1# show flow interface
Interface GigabitEthernet0/0
  FNF: monitor:     ENCOR-MONITOR        direction: Input     ! ← Gi0/0 correct
       monitor:     ENCOR-MONITOR-V6     direction: Input
Interface GigabitEthernet0/1
  FNF: monitor:     ENCOR-MONITOR        direction: Input     ! ← Gi0/1 must appear here
       monitor:     ENCOR-MONITOR-V6     direction: Input     ! ← both IPv4 and IPv6

R1# show flow monitor ENCOR-MONITOR cache
Cache type:                        Normal (Platform cache)
Cache size:                          4096
Current entries:                       <N>   ! ← non-zero after traffic

  IPV4 SRC ADDR   IPV4 DST ADDR   TRNS SRC PORT   TRNS DST PORT   ...
  10.1.12.1       10.1.12.2       ...             ...             ! ← R1-R2 link traffic present
  192.168.10.10   192.168.20.10   ...             ...             ! ← PC1-PC2 traffic present
```

### Fault 3 Fix Verification — IP SLA UDP Jitter Probe

```
R1# show ip sla statistics 2
IPSLA operation id: 2
        Latest RTT: <value> milliseconds   ! ← RTT must show a value, not "NoConnection"
Latest operation start time: ...
Latest operation return code: OK           ! ← must be OK, not "No connection"
Number of successes: <non-zero>            ! ← at least 1 successful probe
Number of failures: 0                      ! ← no failures after fix
```

### Fault 4 Fix Verification — Local SPAN Source Corrected

```
SW1# show monitor session 1
Session 1
---------
Type                   : Local Session
Source Ports           :
    Both               : Gi0/3           ! ← must be Gi0/3 (PC1 port), not Gi0/2
Destination Ports      : Gi0/0           ! ← monitoring port unchanged
    Encapsulation      : Native
          Ingress      : Disabled
```

### Fault 5 Fix Verification — RSPAN VLAN on Trunk

```
SW1# show interfaces GigabitEthernet0/1 trunk
Port        Mode             Encapsulation  Status        Native vlan
Gi0/1       on               802.1q         trunking      1

Port        Vlans allowed on trunk
Gi0/1       10,20,99,500     ! ← VLAN 500 must appear here

SW1# show monitor session 2
Session 2
---------
Type                   : Remote Source Session
Source Ports           :
    Both               : Gi0/3
Destination RSPAN VLAN : 500             ! ← RSPAN VLAN configured

SW2# show monitor session 1
Session 1
---------
Type                   : Remote Destination Session
Source RSPAN VLAN      : 500             ! ← receives from RSPAN VLAN 500
Destination Ports      : Gi0/0           ! ← remote monitoring port
```

---

## 7. Verification Cheatsheet

### SNMP Diagnostic Commands

```
show snmp
show snmp host
show snmp community
show snmp trap
```

| Command | What to Look For |
|---------|-----------------|
| `show snmp host` | Confirm trap destination IP is `2.2.2.2`, not `2.2.2.3` |
| `show snmp community` | Verify community strings ENCOR-RO and ENCOR-RW present |
| `show snmp` | Check `Number of Traps sent to <ip>` counter |
| `show logging` | Confirm syslog buffer populated; severity level correct |

> **Exam tip:** SNMP traps are UDP — there is no connection to observe. The only config-level diagnostic is `show snmp host`. If the IP is wrong, traps are silently discarded.

### Flexible NetFlow Diagnostic Commands

```
show flow interface
show flow monitor <name> cache
show flow exporter <name> statistics
show flow record <name>
```

| Command | What to Look For |
|---------|-----------------|
| `show flow interface` | All active interfaces listed; direction correct (Input) |
| `show flow monitor ENCOR-MONITOR cache` | Non-zero entries; both LAN and WAN flows present |
| `show flow exporter ENCOR-EXPORTER statistics` | Non-zero packets/bytes sent |
| `show flow record ENCOR-FLOW-RECORD` | Match and collect fields match baseline config |

> **Exam tip:** `show flow interface` is the fastest way to confirm which interfaces have a monitor applied. Missing interfaces mean blind spots in the flow data.

### SPAN and RSPAN Diagnostic Commands

```
show monitor session all
show monitor session <N>
show interfaces trunk
show vlan brief
```

| Command | What to Look For |
|---------|-----------------|
| `show monitor session 1` (SW1) | Source = Gi0/3, Destination = Gi0/0 |
| `show monitor session 2` (SW1) | Source = Gi0/3, Destination RSPAN VLAN = 500 |
| `show monitor session 1` (SW2) | Source RSPAN VLAN = 500, Destination = Gi0/0 |
| `show interfaces Gi0/1 trunk` | VLAN 500 in "Vlans allowed on trunk" |
| `show vlan brief` | VLAN 500 listed as `act/unsup` (remote-span VLANs don't show active) |

> **Exam tip:** RSPAN requires three things: (1) VLAN 500 defined as `remote-span` on both switches, (2) VLAN 500 in the trunk allowed list, (3) source and destination sessions configured. Missing any one causes silent failure.

### IP SLA Diagnostic Commands

```
show ip sla statistics
show ip sla statistics <id>
show ip sla configuration <id>
show ip sla summary
```

| Command | What to Look For |
|---------|-----------------|
| `show ip sla statistics 1` | Return Code: OK; ICMP echo to 3.3.3.3 succeeds |
| `show ip sla statistics 2` | Return Code: **No connection** → responder missing on R3 |
| `show ip sla statistics 3` | Return Code: OK; IPv6 ICMP echo to 2001:db8:23::2 succeeds |
| `show ip sla summary` | All three probes show `*` (running), not `~` (pending) |
| `show track 1` | State: Up; IP SLA 1 reachability tracked |

| Return Code | Meaning | Root Cause |
|------------|---------|------------|
| OK | Probe successful | — |
| No connection | Target has no responder | `ip sla responder` missing on target |
| Timeout | Target unreachable | Routing/ACL failure |
| Pending | Probe not scheduled | Missing `ip sla schedule` |

### IP Route Tracking Commands

| Command | What to Look For |
|---------|-----------------|
| `show track 1` | State: Up; changes when SLA 1 goes down |
| `show ip route 10.1.23.0` | Route present via 10.1.12.2 (track Up) |

### Common Network Assurance Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| SNMP traps not at receiver | Wrong `snmp-server host` IP address |
| NetFlow cache empty for a link | Monitor not applied to that interface |
| NetFlow exporter shows 0 packets | Exporter destination unreachable or wrong IP |
| SPAN monitor sees wrong traffic | Wrong source port in SPAN session |
| RSPAN monitor sees nothing | VLAN 500 missing from trunk allowed list |
| IP SLA 2 returns No Connection | `ip sla responder` not enabled on target |
| IP SLA shows Pending | `ip sla schedule` missing or start-time pending |
| Tracked route missing from table | Track state is Down; SLA probe failing |

---

## 8. Solutions (Spoiler Alert!)

> Try to diagnose and fix all five faults before opening these!

### Fault 1: SNMP Trap Host Misconfiguration (R1)

<details>
<summary>Click to view Diagnosis and Fix</summary>

**Diagnosis:**
```bash
R1# show snmp host
Notification host: 2.2.2.3   udp-port: 162   type: trap
! ← 2.2.2.3 is wrong — R2 Loopback0 is 2.2.2.2
```

**Fix on R1:**
```bash
R1(config)# no snmp-server host 2.2.2.3 version 2c ENCOR-RO
R1(config)# snmp-server host 2.2.2.2 version 2c ENCOR-RO
```

**Verify:**
```bash
R1# show snmp host
Notification host: 2.2.2.2   udp-port: 162   type: trap
  user: ENCOR-RO   security model: v2c
```
</details>

### Fault 2: NetFlow Not Applied to R1 Gi0/1

<details>
<summary>Click to view Diagnosis and Fix</summary>

**Diagnosis:**
```bash
R1# show flow interface
Interface GigabitEthernet0/0
  FNF: monitor: ENCOR-MONITOR    direction: Input
       monitor: ENCOR-MONITOR-V6 direction: Input
! ← Gi0/1 is absent — inter-router traffic not captured
```

**Fix on R1:**
```bash
R1(config)# interface GigabitEthernet0/1
R1(config-if)# ip flow monitor ENCOR-MONITOR input
R1(config-if)# ipv6 flow monitor ENCOR-MONITOR-V6 input
```

**Verify:**
```bash
R1# show flow interface
Interface GigabitEthernet0/0
  FNF: monitor: ENCOR-MONITOR    direction: Input
       monitor: ENCOR-MONITOR-V6 direction: Input
Interface GigabitEthernet0/1
  FNF: monitor: ENCOR-MONITOR    direction: Input    ! ← now present
       monitor: ENCOR-MONITOR-V6 direction: Input
```
</details>

### Fault 3: IP SLA Responder Not Enabled on R3

<details>
<summary>Click to view Diagnosis and Fix</summary>

**Diagnosis:**
```bash
R1# show ip sla statistics 2
IPSLA operation id: 2
Latest operation return code: No connection   ! ← responder not running on R3
```

**Fix on R3:**
```bash
R3(config)# ip sla responder
```

**Verify:**
```bash
R1# show ip sla statistics 2
Latest operation return code: OK              ! ← probe succeeds after next interval
Number of successes: 1
Number of failures: 0
```
</details>

### Fault 4: SPAN Session Source Wrong (SW1)

<details>
<summary>Click to view Diagnosis and Fix</summary>

**Diagnosis:**
```bash
SW1# show monitor session 1
Session 1
---------
Type                   : Local Session
Source Ports           :
    Both               : Gi0/2       ! ← Gi0/2 is R1 uplink, not PC1 port
Destination Ports      : Gi0/0
```

**Fix on SW1:**
```bash
SW1(config)# no monitor session 1
SW1(config)# monitor session 1 source interface GigabitEthernet0/3
SW1(config)# monitor session 1 destination interface GigabitEthernet0/0
```

**Verify:**
```bash
SW1# show monitor session 1
Session 1
---------
Source Ports           :
    Both               : Gi0/3       ! ← now correct: PC1 port
Destination Ports      : Gi0/0
```
</details>

### Fault 5: RSPAN VLAN 500 Missing from SW1 Trunk

<details>
<summary>Click to view Diagnosis and Fix</summary>

**Diagnosis:**
```bash
SW1# show interfaces GigabitEthernet0/1 trunk
Port        Vlans allowed on trunk
Gi0/1       10,20,99            ! ← VLAN 500 missing — RSPAN frames blocked

SW2# show monitor session 1
Session 1
---------
Type                   : Remote Destination Session
Source RSPAN VLAN      : 500
Destination Ports      : Gi0/0
! ← SW2 side is correct; fault is on SW1 trunk
```

**Fix on SW1:**
```bash
SW1(config)# interface GigabitEthernet0/1
SW1(config-if)# switchport trunk allowed vlan add 500
```

**Verify:**
```bash
SW1# show interfaces GigabitEthernet0/1 trunk
Port        Vlans allowed on trunk
Gi0/1       10,20,99,500        ! ← VLAN 500 now present
```
</details>

### Known-Good Solution Configs

<details>
<summary>Click to view R1 Known-Good Config</summary>

```bash
hostname R1
!
service timestamps log datetime msec
!
logging buffered 16384 informational
!
ip access-list extended DEBUG-FILTER
 permit ip host 192.168.10.10 any
!
snmp-server community ENCOR-RO RO
snmp-server community ENCOR-RW RW
snmp-server host 2.2.2.2 version 2c ENCOR-RO
snmp-server enable traps snmp linkdown linkup coldstart
!
ipv6 unicast-routing
!
flow record ENCOR-FLOW-RECORD
 match ipv4 source address
 match ipv4 destination address
 match transport source-port
 match transport destination-port
 match ip protocol
 collect counter bytes long
 collect counter packets long
 collect timestamp sys-uptime first
 collect timestamp sys-uptime last
!
flow record ENCOR-FLOW-RECORD-V6
 match ipv6 source address
 match ipv6 destination address
 match transport source-port
 match transport destination-port
 match ip protocol
 collect counter bytes long
 collect counter packets long
 collect timestamp sys-uptime first
 collect timestamp sys-uptime last
!
flow exporter ENCOR-EXPORTER
 destination 2.2.2.2
 source Loopback0
 transport udp 9996
 export-protocol netflow-v9
!
flow monitor ENCOR-MONITOR
 record ENCOR-FLOW-RECORD
 exporter ENCOR-EXPORTER
 cache timeout active 60
 cache timeout inactive 15
!
flow monitor ENCOR-MONITOR-V6
 record ENCOR-FLOW-RECORD-V6
 exporter ENCOR-EXPORTER
 cache timeout active 60
 cache timeout inactive 15
!
ip sla 1
 icmp-echo 3.3.3.3 source-ip 1.1.1.1
 frequency 30
ip sla schedule 1 life forever start-time now
!
ip sla 2
 udp-jitter 3.3.3.3 5000 source-ip 1.1.1.1 num-packets 10
 frequency 60
ip sla schedule 2 life forever start-time now
!
ip sla 3
 icmp-echo 2001:db8:23::2 source-interface GigabitEthernet0/1
 frequency 30
ip sla schedule 3 life forever start-time now
!
track 1 ip sla 1 reachability
 delay down 10 up 10
!
interface Loopback0
 ip address 1.1.1.1 255.255.255.255
!
interface GigabitEthernet0/0
 ip address 192.168.10.1 255.255.255.0
 ipv6 address 2001:db8:10::1/64
 ip flow monitor ENCOR-MONITOR input
 ipv6 flow monitor ENCOR-MONITOR-V6 input
 ipv6 ospf 1 area 0
 no shutdown
!
interface GigabitEthernet0/1
 ip address 10.1.12.1 255.255.255.252
 ipv6 address 2001:db8:12::1/64
 ip flow monitor ENCOR-MONITOR input
 ipv6 flow monitor ENCOR-MONITOR-V6 input
 ipv6 ospf 1 area 0
 no shutdown
!
router ospf 1
 router-id 1.1.1.1
 passive-interface GigabitEthernet0/0
 network 1.1.1.1 0.0.0.0 area 0
 network 10.1.12.0 0.0.0.3 area 0
 network 192.168.10.0 0.0.0.255 area 0
!
ipv6 router ospf 1
 router-id 1.1.1.1
 passive-interface GigabitEthernet0/0
!
ip route 10.1.23.0 255.255.255.252 10.1.12.2 track 1
!
end
```
</details>

<details>
<summary>Click to view R3 Known-Good Config</summary>

```bash
hostname R3
!
service timestamps log datetime msec
!
logging buffered 16384 informational
!
snmp-server community ENCOR-RO RO
snmp-server community ENCOR-RW RW
snmp-server host 2.2.2.2 version 2c ENCOR-RO
snmp-server enable traps snmp linkdown linkup coldstart
!
ipv6 unicast-routing
!
ip sla responder
!
interface Loopback0
 ip address 3.3.3.3 255.255.255.255
!
interface GigabitEthernet0/0
 ip address 10.1.23.2 255.255.255.252
 ipv6 address 2001:db8:23::2/64
 ipv6 ospf 1 area 0
 no shutdown
!
router ospf 1
 router-id 3.3.3.3
 network 3.3.3.3 0.0.0.0 area 0
 network 10.1.23.0 0.0.0.3 area 0
!
ipv6 router ospf 1
 router-id 3.3.3.3
!
end
```
</details>

<details>
<summary>Click to view SW1 Known-Good Config</summary>

```bash
hostname SW1
!
vtp mode transparent
!
vlan 10
 name DATA-A
!
vlan 20
 name DATA-B
!
vlan 99
 name MGMT
!
vlan 500
 name RSPAN
 remote-span
!
interface GigabitEthernet0/0
 no shutdown
!
interface GigabitEthernet0/1
 switchport trunk encapsulation dot1q
 switchport trunk allowed vlan 10,20,99,500
 switchport mode trunk
 switchport nonegotiate
 no shutdown
!
interface GigabitEthernet0/2
 switchport access vlan 10
 switchport mode access
 spanning-tree portfast
 no shutdown
!
interface GigabitEthernet0/3
 switchport access vlan 10
 switchport mode access
 spanning-tree portfast
 no shutdown
!
interface Vlan99
 ip address 192.168.99.11 255.255.255.0
 no shutdown
!
monitor session 1 source interface GigabitEthernet0/3
monitor session 1 destination interface GigabitEthernet0/0
!
monitor session 2 source interface GigabitEthernet0/3
monitor session 2 destination remote vlan 500
!
end
```
</details>

---

## 9. Troubleshooting Scenarios

Each ticket targets a single fault. Use these for individual practice — inject one fault at a time from a known-good baseline, then diagnose and fix using only `show` commands.

### Workflow

```bash
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>  # reset to known-good
python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>  # Ticket 1
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>  # restore before next
```

To practice the full concurrent scenario (all 5 faults simultaneously):
```bash
python3 setup_lab.py --host <eve-ng-ip>  # loads pre-broken state
```

---

### Ticket 1 — R1 Flow Records Do Not Include Inter-Router Traffic

A colleague reports that the NetFlow dashboard shows only VLAN 10 LAN traffic. Flows between R1 and R2 are absent from the cache, and the exporter statistics show far fewer packets than expected.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>`

**Success criteria:** `show flow interface` shows ENCOR-MONITOR applied to both Gi0/0 and Gi0/1 in the Input direction. `show flow monitor ENCOR-MONITOR cache` includes entries for 10.1.12.x source addresses.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
R1# show flow interface
! If Gi0/1 is missing, the monitor is not applied there

R1# show flow monitor ENCOR-MONITOR cache
! Check source addresses — 10.1.12.x absent means Gi0/1 not monitored

R1# show flow exporter ENCOR-EXPORTER statistics
! Packet/byte counts lower than expected — confirms limited capture
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
R1(config)# interface GigabitEthernet0/1
R1(config-if)# ip flow monitor ENCOR-MONITOR input
R1(config-if)# ipv6 flow monitor ENCOR-MONITOR-V6 input
```
</details>

---

### Ticket 2 — SNMP Trap Receiver on R2 Receives No Traps from R1

The NOC reports that R2's SNMP trap log shows no entries from R1 (1.1.1.1). Interface flap events that should trigger `linkdown/linkup` traps are not appearing. ICMP ping from R2 to R1 is fully functional.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py --host <eve-ng-ip>`

**Success criteria:** `show snmp host` on R1 shows trap destination `2.2.2.2`. After triggering a trap event, the counter increments.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
R1# show snmp host
! Check the Notification host IP — if not 2.2.2.2, traps go nowhere

R1# show snmp
! Check "Number of Traps sent" — if counter is incrementing to a different IP,
! the trap delivery path is wrong

R2# show ip route 2.2.2.3
! Verify whether 2.2.2.3 is even reachable (it's not — no such host in topology)
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
R1(config)# no snmp-server host 2.2.2.3 version 2c ENCOR-RO
R1(config)# snmp-server host 2.2.2.2 version 2c ENCOR-RO
```
</details>

---

### Ticket 3 — IP SLA Probe 2 Returns "No Connection" Error

R1's IP SLA probe 2 is scheduled and running but reports a persistent failure. The return code is not Timeout — routing to R3 is confirmed working. Probe 1 (ICMP echo) to the same destination succeeds.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py --host <eve-ng-ip>`

**Success criteria:** `show ip sla statistics 2` on R1 shows `Return Code: OK` and `Number of successes` incrementing.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
R1# show ip sla statistics 2
! Return Code: No connection → R3 has no UDP responder listening

R1# show ip sla statistics 1
! If probe 1 (ICMP echo) is OK, routing is fine — isolates fault to responder

R3# show ip sla responder
! If no output or "IPSLA Responder is not enabled" — responder missing
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
R3(config)# ip sla responder
```
</details>

---

### Ticket 4 — Local Monitor Port on SW1 Captures R1 Traffic Instead of PC1

The security team reports that the local analyzer connected to SW1's Gi0/0 is capturing R1 router traffic (OSPF hellos, SNMP packets) rather than PC1 end-user traffic. The mirror port is working, just mirroring the wrong source.

**Inject:** `python3 scripts/fault-injection/inject_scenario_04.py --host <eve-ng-ip>`

**Success criteria:** `show monitor session 1` on SW1 shows `Source Ports: Gi0/3` (PC1 port). The monitoring port captures VLAN 10 host traffic.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
SW1# show monitor session 1
! Source Ports shows Gi0/2 — that is the R1 uplink, not the PC1 port

SW1# show interfaces status
! Confirm Gi0/2 = R1 uplink (VLAN 10 access to R1 Gi0/0)
! Confirm Gi0/3 = PC1 access port (correct source)
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
SW1(config)# no monitor session 1
SW1(config)# monitor session 1 source interface GigabitEthernet0/3
SW1(config)# monitor session 1 destination interface GigabitEthernet0/0
```
</details>

---

### Ticket 5 — Remote Monitor Port on SW2 Captures No Traffic

The remote packet analyzer connected to SW2 Gi0/0 captures no frames. The RSPAN configuration looks correct on SW2. VLAN 500 exists on both switches. The local SPAN session on SW1 (session 1) is working correctly.

**Inject:** `python3 scripts/fault-injection/inject_scenario_05.py --host <eve-ng-ip>`

**Success criteria:** `show interfaces GigabitEthernet0/1 trunk` on SW1 shows VLAN 500 in the allowed list. `show monitor session 1` on SW2 shows frames incrementing.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
SW1# show interfaces GigabitEthernet0/1 trunk
! Check "Vlans allowed on trunk" — if 500 is absent, RSPAN frames are blocked here

SW1# show vlan brief
! VLAN 500 should show as "act/unsup" (remote-span VLANs are not forwarded normally)

SW2# show monitor session 1
! Session 2 config is correct — fault is on the SW1 trunk, not SW2

SW1# show monitor session 2
! Source: Gi0/3, Dest RSPAN VLAN: 500 — session is OK; trunk is the bottleneck
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
SW1(config)# interface GigabitEthernet0/1
SW1(config-if)# switchport trunk allowed vlan add 500
```
</details>

---

## 10. Lab Completion Checklist

### Concurrent Troubleshooting (Full Capstone)

Use `python3 setup_lab.py --host <eve-ng-ip>` to load all 5 faults simultaneously.

- [ ] Fault 1 — SNMP trap host corrected to 2.2.2.2 on R1; `show snmp host` confirms
- [ ] Fault 2 — NetFlow monitor applied to R1 Gi0/1; `show flow interface` shows both interfaces
- [ ] Fault 3 — IP SLA responder enabled on R3; `show ip sla statistics 2` returns OK
- [ ] Fault 4 — SPAN session 1 source corrected to Gi0/3 on SW1; `show monitor session 1` confirms
- [ ] Fault 5 — VLAN 500 added to SW1 Gi0/1 trunk; `show interfaces Gi0/1 trunk` confirms

### Individual Fault Practice (Single-Scenario Injection)

- [ ] Ticket 1 — NetFlow Gi0/1 gap diagnosed and fixed
- [ ] Ticket 2 — SNMP trap host mismatch diagnosed and fixed
- [ ] Ticket 3 — IP SLA No Connection diagnosed and fixed (responder)
- [ ] Ticket 4 — SPAN wrong source port diagnosed and fixed
- [ ] Ticket 5 — RSPAN trunk VLAN pruning diagnosed and fixed

### Final Validation

- [ ] `show flow monitor ENCOR-MONITOR cache` — entries from both Gi0/0 and Gi0/1
- [ ] `show snmp host` — trap destination is 2.2.2.2
- [ ] `show ip sla statistics` — all three probes return OK
- [ ] `show monitor session 1` (SW1) — source Gi0/3, destination Gi0/0
- [ ] `show interfaces Gi0/1 trunk` (SW1) — VLAN 500 in allowed list
- [ ] `show monitor session 1` (SW2) — RSPAN destination active
