# Network Assurance Lab 01: Flexible NetFlow

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

**Exam Objective:** 4.2 Explain Flexible NetFlow — Network Assurance

Flexible NetFlow (FNF) is Cisco's second-generation traffic telemetry framework. Unlike traditional NetFlow (which used a fixed 7-tuple per flow), FNF lets you define exactly which IP header fields constitute a "flow" and exactly which statistics to collect. The result is a modular, reusable system that supports both IPv4 and IPv6, integrates with standard collectors over UDP, and exports data in NetFlow v9 or IPFIX format. This lab builds the complete FNF pipeline on R1 — the network edge router — and exports all flow data to R2, which acts as the NMS/collector.

### The Three-Component FNF Pipeline

FNF is assembled from three independent building blocks:

**Flow Record** — defines the flow key (what fields identify a unique flow) and the counters (what to collect per flow):
- **Match fields** (key fields): values that must be equal for packets to belong to the same flow. Examples: IPv4 source address, IPv4 destination address, transport protocol, source port, destination port.
- **Collect fields** (non-key fields): statistics accumulated over the life of a flow. Examples: byte counts, packet counts, timestamps.

```
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
```

**Flow Exporter** — defines where and how flow data is shipped after cache expiry:
- Destination IP and UDP port (standard collectors listen on UDP 2055 or 9996)
- Source interface (used as the source IP in UDP packets; Loopback preferred for stability)
- Export protocol: NetFlow v9 (template-based, extensible) or IPFIX (RFC 5101)

```
flow exporter ENCOR-EXPORTER
 destination 2.2.2.2
 source Loopback0
 transport udp 9996
 export-protocol netflow-v9
```

**Flow Monitor** — binds a record and exporter together, configures cache behavior, and is applied to an interface:
- Each monitor references exactly one record and one or more exporters.
- Cache timeouts control when active and idle flows are exported.
- Applied per-interface per-direction: `ip flow monitor <name> input`.

```
flow monitor ENCOR-MONITOR
 record ENCOR-FLOW-RECORD
 exporter ENCOR-EXPORTER
 cache timeout active 60
 cache timeout inactive 15
```

### Key Fields vs Non-Key Fields

| Category | Role | Example Commands |
|----------|------|-----------------|
| Key (match) | Identifies the flow | `match ipv4 source address`, `match transport source-port` |
| Non-key (collect) | Accumulated per flow | `collect counter bytes long`, `collect timestamp sys-uptime first` |

Two packets belong to the same flow only when ALL key fields match. Adding more key fields creates more granular (and more numerous) flows; fewer key fields creates fewer but broader flows.

### NetFlow v9 vs Legacy NetFlow v5

| Feature | NetFlow v5 | NetFlow v9 |
|---------|-----------|-----------|
| Fields | Fixed 7-tuple only | Template-based, any fields |
| IPv6 support | No | Yes |
| MPLS fields | No | Yes |
| Flexible | No | Yes |
| Collector support | Universal | Most modern collectors |

FNF always uses v9 or IPFIX. You cannot mix FNF with the old `ip flow ingress` command on the same interface in IOS 15.x.

### Cache Timeouts

| Timer | Default | Controls |
|-------|---------|---------|
| `cache timeout active` | 1800 s | Maximum age of an active (ongoing) flow before forced export |
| `cache timeout inactive` | 15 s | Idle time after last packet before flow expires |
| `cache timeout update` | 30 s (v9 only) | Template re-send interval |

Short active timeouts (60 s in this lab) are common in production to reduce collector memory pressure. Inactive timeout of 15 s matches the default — short-lived connections expire quickly.

### Dual-Stack FNF (IPv4 + IPv6)

IPv4 and IPv6 require separate flow records and monitors because the match fields are protocol-specific (`match ipv4 source address` vs `match ipv6 source address`). A single exporter can serve both monitors. Application at the interface level uses separate commands:

```
! IPv4 monitor
ip flow monitor ENCOR-MONITOR input
! IPv6 monitor (separate command, same interface)
ipv6 flow monitor ENCOR-MONITOR-V6 input
```

Both monitors can share the same exporter. The router tags each exported template with a different template ID so the collector knows which record schema to use.

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| FNF flow record design | Selecting appropriate key and non-key fields for traffic visibility |
| Flow exporter configuration | Directing telemetry to an NMS over UDP/NetFlow v9 |
| Flow monitor assembly | Binding records and exporters; tuning cache timeouts |
| Dual-stack FNF | Separate IPv4 and IPv6 monitors on the same interfaces |
| FNF verification | Interpreting `show flow monitor`, `show flow record`, `show flow exporter statistics` |

---

## 2. Topology & Scenario

**Scenario:** You are a network engineer at Acme Corp. The security and operations teams have requested real-time traffic telemetry for the edge network. R1 (the edge router) must be configured as the NetFlow exporter, sending all IPv4 and IPv6 flow data to R2 (the NMS server at 2.2.2.2) on UDP port 9996. The data must include 5-tuple identification (source/destination IP, source/destination port, IP protocol) and byte/packet counts with timestamps.

```
     ┌────────────────────────┐  Gi0/1   10.1.12.1/30       Gi0/1  ┌────────────────────────┐  Gi0/2  10.1.23.1/30  Gi0/0  ┌────────────────────┐
     │           R1           ├───────────────────────────────────────┤           R2           ├────────────────────────────────┤         R3         │
     │   (Edge / FNF Exporter)│  2001:db8:12::1/64 10.1.12.2/30     │   (Distrib. / NMS)     │  10.1.23.2/30                  │   (Remote Target)  │
     │   Lo0: 1.1.1.1/32      │             2001:db8:12::2/64        │   Lo0: 2.2.2.2/32      │                                │   Lo0: 3.3.3.3/32  │
     └──────────┬─────────────┘                                      └──────────┬─────────────┘                               └────────────────────┘
            Gi0/0│ 192.168.10.1/24                                          Gi0/0│ 192.168.20.1/24
                 │ 2001:db8:10::1/64                                              │ 2001:db8:20::1/64
            Gi0/2│                                                          Gi0/2│
     ┌───────────┴───────┐  Gi0/1              Gi0/1  ┌──────────────────────────┴──┐
     │       SW1         ├────────── trunk ─────────────┤             SW2             │
     │  (Access / SPAN)  │    VLANs 10,20,99,500        │   (Distrib. / RSPAN dst)    │
     │  SVI:192.168.99.11│                              │   SVI:192.168.99.12          │
     └──────────┬────────┘                              └──────────────┬──────────────┘
           Gi0/3│ (VLAN 10)                                       Gi0/3│ (VLAN 20)
          ┌─────┴──────┐                                         ┌─────┴──────┐
          │    PC1     │                                         │    PC2     │
          │ 192.168.10 │                                         │ 192.168.20 │
          │  .10/24    │                                         │  .10/24    │
          └────────────┘                                         └────────────┘
```

**Flow Export Path:** R1 (exporter) → R1 Gi0/1 → R2 Gi0/1 → R2 Lo0 (2.2.2.2:9996/UDP)

---

## 3. Hardware & Environment Specifications

| Device | Role | Platform | Image |
|--------|------|----------|-------|
| R1 | Edge Router / FNF Exporter | IOSv | vios-adventerprisek9 |
| R2 | Distribution / NMS Collector | IOSv | vios-adventerprisek9 |
| R3 | Remote Branch | IOSv | vios-adventerprisek9 |
| SW1 | Access Switch / SPAN Source | IOSvL2 | viosl2-adventerprisek9 |
| SW2 | Distribution Switch / RSPAN Dest | IOSvL2 | viosl2-adventerprisek9 |
| PC1 | LAN Host A | VPCS | — |
| PC2 | LAN Host B | VPCS | — |

**Cabling:**

| Link | Device A | Interface | Device B | Interface | Subnet |
|------|----------|-----------|----------|-----------|--------|
| L1 | R1 | Gi0/1 | R2 | Gi0/1 | 10.1.12.0/30 |
| L2 | R2 | Gi0/2 | R3 | Gi0/0 | 10.1.23.0/30 |
| L3 | R1 | Gi0/0 | SW1 | Gi0/2 | 192.168.10.0/24 |
| L4 | R2 | Gi0/0 | SW2 | Gi0/2 | 192.168.20.0/24 |
| L5 | SW1 | Gi0/1 | SW2 | Gi0/1 | Trunk (VLANs 10,20,99,500) |
| L6 | SW1 | Gi0/3 | PC1 | eth0 | 192.168.10.0/24 (VLAN 10) |
| L7 | SW2 | Gi0/3 | PC2 | eth0 | 192.168.20.0/24 (VLAN 20) |

**Console Access Table:**

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

The following is **pre-loaded** on all devices in `initial-configs/`:

**Pre-loaded on all routers (R1, R2, R3):**
- Hostnames and `service timestamps log datetime msec`
- Logging (buffered informational)
- SNMP communities and traps (ENCOR-RO, ENCOR-RW, host 2.2.2.2)
- IPv4 addressing on all interfaces
- IPv6 addressing on all interfaces
- OSPFv2 area 0 (IPv4 routing — all loopbacks and P2P links)
- OSPFv3 area 0 IPv6 (IPv6 routing — all P2P links and LAN segments)
- `ipv6 unicast-routing`

**Pre-loaded on switches (SW1, SW2):**
- VLANs 10 (DATA-A), 20 (DATA-B), 99 (MGMT), 500 (RSPAN)
- Trunk configuration (Gi0/1) and access ports (Gi0/2, Gi0/3)
- Management SVIs (Vlan99)

**Pre-loaded on PCs:**
- IP addressing and default gateway

**NOT pre-loaded — student must configure:**
- Flexible NetFlow flow records (IPv4 and IPv6)
- Flow exporter
- Flow monitors (IPv4 and IPv6)
- FNF application on R1 interfaces

---

## 5. Lab Challenge: Core Implementation

> Work on R1 only. R2, R3, SW1, SW2, PC1, PC2 are fully configured and operational.
> All routing is functional: ping between any two loopbacks before starting.

### Task 1: Create the IPv4 Flow Record

- Define a named flow record that identifies traffic by its complete 5-tuple: source and destination IPv4 addresses, source and destination transport-layer ports, and IP protocol number.
- Configure the record to collect per-flow byte counts (long format), packet counts (long format), and first/last seen timestamps based on router uptime.

**Verification:** `show flow record ENCOR-FLOW-RECORD` must display all five match fields and four collect fields with no error messages.

---

### Task 2: Create the Flow Exporter

- Define a named flow exporter that sends telemetry to R2's loopback address (2.2.2.2).
- Use R1's Loopback0 as the source interface so the export IP remains stable regardless of which physical interface is up.
- Export on UDP port 9996 using NetFlow version 9 format.

**Verification:** `show flow exporter ENCOR-EXPORTER` must show the destination, source interface, transport protocol, and export protocol correctly.

---

### Task 3: Create the IPv4 Flow Monitor

- Define a named flow monitor that references the IPv4 flow record from Task 1 and the exporter from Task 2.
- Set the active flow cache timeout to 60 seconds and the inactive timeout to 15 seconds.

**Verification:** `show flow monitor ENCOR-MONITOR` must show the record and exporter bindings and the configured cache timeouts.

---

### Task 4: Apply the IPv4 Monitor to R1's Interfaces

- Apply the IPv4 flow monitor in the ingress direction on both of R1's active traffic interfaces: the LAN-facing interface (Gi0/0) and the uplink toward R2 (Gi0/1).

**Verification:** `show flow interface GigabitEthernet0/0` and `show flow interface GigabitEthernet0/1` must each show the IPv4 monitor applied for input.

---

### Task 5: Create the IPv6 Flow Record

- Define a second named flow record for IPv6 traffic. It must match source and destination IPv6 addresses, and must also include source/destination transport ports and IP protocol in its key fields.
- Collect the same counters and timestamps as the IPv4 record (bytes long, packets long, first/last uptime).

**Verification:** `show flow record ENCOR-FLOW-RECORD-V6` must display all five match fields and four collect fields.

---

### Task 6: Create the IPv6 Flow Monitor and Apply It

- Define a named IPv6 flow monitor that references the IPv6 flow record from Task 5 and reuses the same exporter from Task 2.
- Use the same cache timeouts as the IPv4 monitor (active 60 s, inactive 15 s).
- Apply this IPv6 monitor in the ingress direction on both Gi0/0 and Gi0/1.

**Verification:** `show flow interface GigabitEthernet0/0` must show both the IPv4 monitor and the IPv6 monitor applied for input. After generating traffic with `ping 2001:db8:12::2` from R1, `show flow monitor ENCOR-MONITOR-V6 cache` must show at least one active IPv6 flow.

---

## 6. Verification & Analysis

After completing all tasks, verify the complete FNF implementation:

### Flow Record Verification

```
R1# show flow record ENCOR-FLOW-RECORD
flow record ENCOR-FLOW-RECORD:
  Description:        User defined
  No. of users:       1                      ! ← bound to 1 monitor
  Total field space:  36 bytes
  Fields:
    match ipv4 source address                ! ← key field 1
    match ipv4 destination address           ! ← key field 2
    match transport source-port              ! ← key field 3
    match transport destination-port         ! ← key field 4
    match ip protocol                        ! ← key field 5
    collect counter bytes long               ! ← non-key: byte count
    collect counter packets long             ! ← non-key: packet count
    collect timestamp sys-uptime first       ! ← non-key: flow start
    collect timestamp sys-uptime last        ! ← non-key: flow last seen

R1# show flow record ENCOR-FLOW-RECORD-V6
flow record ENCOR-FLOW-RECORD-V6:
  Description:        User defined
  No. of users:       1                      ! ← bound to 1 IPv6 monitor
  Total field space:  68 bytes
  Fields:
    match ipv6 source address                ! ← IPv6 key field 1 (128-bit)
    match ipv6 destination address           ! ← IPv6 key field 2 (128-bit)
    match transport source-port              ! ← key field 3
    match transport destination-port         ! ← key field 4
    match ip protocol                        ! ← key field 5
    collect counter bytes long
    collect counter packets long
    collect timestamp sys-uptime first
    collect timestamp sys-uptime last
```

### Flow Exporter Verification

```
R1# show flow exporter ENCOR-EXPORTER
Flow Exporter ENCOR-EXPORTER:
  Description:              User defined
  Export protocol:          NetFlow Version 9   ! ← must be v9, not v5
  Transport Configuration:
    Destination IP address: 2.2.2.2             ! ← R2 loopback
    Source IP address:      1.1.1.1             ! ← R1 Loopback0 resolved
    Transport Protocol:     UDP
    Destination Port:       9996                ! ← collector port
    Source Port:            <dynamic>
    DSCP:                   0x0
    TTL:                    255

R1# show flow exporter ENCOR-EXPORTER statistics
Flow Exporter ENCOR-EXPORTER:
  Packet send statistics (last cleared 00:01:23 ago):
    Successfully sent:         2                ! ← > 0 means exports are happening
    Reason not sent:           0                ! ← must be 0; non-zero = connectivity issue
```

### Flow Monitor Verification

```
R1# show flow monitor ENCOR-MONITOR
Flow Monitor ENCOR-MONITOR:
      Description:       User defined
      Flow Record:       ENCOR-FLOW-RECORD   ! ← correct record bound
      Flow Exporter:     ENCOR-EXPORTER      ! ← correct exporter bound
      Cache:
        Type:          normal (Platform cache)
        Status:        allocated
        Size:          4096 entries / 311316 bytes
        Inactive Timeout: 15 secs            ! ← must be 15
        Active Timeout:   60 secs            ! ← must be 60

R1# show flow monitor ENCOR-MONITOR-V6
Flow Monitor ENCOR-MONITOR-V6:
      Description:       User defined
      Flow Record:       ENCOR-FLOW-RECORD-V6
      Flow Exporter:     ENCOR-EXPORTER
      Cache:
        Inactive Timeout: 15 secs
        Active Timeout:   60 secs
```

### Interface Application Verification

```
R1# show flow interface GigabitEthernet0/0
Interface GigabitEthernet0/0
  FNF:  monitor:         ENCOR-MONITOR       ! ← IPv4 monitor applied
        direction:       Input               ! ← ingress direction
        traffic(ip):     on
  FNF:  monitor:         ENCOR-MONITOR-V6    ! ← IPv6 monitor applied
        direction:       Input
        traffic(ipv6):   on                  ! ← IPv6 traffic captured

R1# show flow interface GigabitEthernet0/1
Interface GigabitEthernet0/1
  FNF:  monitor:         ENCOR-MONITOR
        direction:       Input
        traffic(ip):     on
  FNF:  monitor:         ENCOR-MONITOR-V6
        direction:       Input
        traffic(ipv6):   on
```

### Live Flow Cache Verification

After PC1 pings R3's loopback (3.3.3.3) — this generates ingress traffic on R1 Gi0/0:

```
R1# show flow monitor ENCOR-MONITOR cache
Cache type:                               Normal (Platform cache)
Cache size:                                             4096
Current entries:                                           1  ! ← at least 1 flow

  IPV4 SRC ADDR    IPV4 DST ADDR    TRNS SRC PORT  TRNS DST PORT  IP PROT  bytes  pkts
  ---------------  ---------------  ---------------  ---------------  -------  -----  ----
  192.168.10.10    3.3.3.3                       0               0        1   500     5  ! ← ICMP from PC1 (proto=1), captured ingress on Gi0/0
```

---

## 7. Verification Cheatsheet

### Flow Record Configuration

```
flow record <NAME>
 match ipv4 source address
 match ipv4 destination address
 match transport source-port
 match transport destination-port
 match ip protocol
 collect counter bytes long
 collect counter packets long
 collect timestamp sys-uptime first
 collect timestamp sys-uptime last
```

| Command | Purpose |
|---------|---------|
| `match ipv4 source address` | Key field: source IPv4 (identifies unique flow) |
| `match transport source-port` | Key field: L4 source port |
| `collect counter bytes long` | Non-key: byte count (64-bit, avoids wrap on fast links) |
| `collect timestamp sys-uptime first` | Non-key: when first packet of flow was seen |

> **Exam tip:** `match` = key field (identifies the flow), `collect` = non-key field (statistics). Both are required in a useful flow record.

### Flow Exporter Configuration

```
flow exporter <NAME>
 destination <collector-ip>
 source <interface>
 transport udp <port>
 export-protocol netflow-v9
```

| Command | Purpose |
|---------|---------|
| `destination <ip>` | Collector IP address |
| `source <interface>` | Source interface for UDP packets (use Loopback for stability) |
| `transport udp <port>` | Collector UDP port (standard: 9996 or 2055) |
| `export-protocol netflow-v9` | Template-based format; required for IPv6 and custom fields |

> **Exam tip:** NetFlow v5 is fixed-format IPv4 only. FNF always requires v9 or IPFIX to support custom records and IPv6.

### Flow Monitor Configuration

```
flow monitor <NAME>
 record <RECORD-NAME>
 exporter <EXPORTER-NAME>
 cache timeout active <seconds>
 cache timeout inactive <seconds>
```

| Command | Purpose |
|---------|---------|
| `record <name>` | Binds the flow record (defines what to track) |
| `exporter <name>` | Binds the exporter (defines where to send data) |
| `cache timeout active <s>` | Force-export ongoing flows older than N seconds |
| `cache timeout inactive <s>` | Export idle flows after N seconds of silence |

### Interface Application

```
interface <NAME>
 ip flow monitor <MONITOR-NAME> input
 ipv6 flow monitor <MONITOR-V6-NAME> input
```

| Command | Purpose |
|---------|---------|
| `ip flow monitor <name> input` | Apply IPv4 monitor to ingress traffic |
| `ipv6 flow monitor <name> input` | Apply IPv6 monitor to ingress traffic |
| `ip flow monitor <name> output` | Apply IPv4 monitor to egress traffic |

> **Exam tip:** Ingress monitoring is the standard approach. To capture bidirectional traffic, apply monitors in both directions — or apply the monitor to both endpoints of the link.

### Verification Commands

| Command | What to Look For |
|---------|-----------------|
| `show flow record <name>` | All match and collect fields listed; "No. of users: N" shows monitor binding |
| `show flow exporter <name>` | Correct destination, source, UDP port, export protocol |
| `show flow exporter <name> statistics` | "Successfully sent" > 0; "Reason not sent: 0" |
| `show flow monitor <name>` | Correct record and exporter bound; cache timeouts |
| `show flow monitor <name> cache` | Live flow entries with src/dst IPs, ports, counts |
| `show flow interface <intf>` | Monitor name, direction, and traffic type (ip/ipv6) per interface |

### Common FNF Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| No flow entries in cache | Monitor not applied to interface, or no traffic on that interface |
| "Successfully sent: 0" in exporter stats | No route to collector IP; source interface issue |
| "Reason not sent" > 0 in exporter stats | Destination unreachable; wrong destination IP |
| Monitor shows wrong record | Record name typo in `flow monitor` configuration |
| IPv6 flows not captured | `ipv6 flow monitor` not applied, or `ipv6 unicast-routing` not enabled |
| Cache never expires | Active timeout too high; traffic volume too low to trigger inactive timeout |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Task 1 & 2: IPv4 Flow Record and Exporter

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1
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
flow exporter ENCOR-EXPORTER
 destination 2.2.2.2
 source Loopback0
 transport udp 9996
 export-protocol netflow-v9
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show flow record ENCOR-FLOW-RECORD
show flow exporter ENCOR-EXPORTER
```
</details>

---

### Task 3 & 4: IPv4 Flow Monitor and Interface Application

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1
flow monitor ENCOR-MONITOR
 record ENCOR-FLOW-RECORD
 exporter ENCOR-EXPORTER
 cache timeout active 60
 cache timeout inactive 15
!
interface GigabitEthernet0/0
 ip flow monitor ENCOR-MONITOR input
!
interface GigabitEthernet0/1
 ip flow monitor ENCOR-MONITOR input
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show flow monitor ENCOR-MONITOR
show flow interface GigabitEthernet0/0
show flow interface GigabitEthernet0/1
show flow monitor ENCOR-MONITOR cache
```
</details>

---

### Tasks 5 & 6: IPv6 Flow Record, Monitor, and Interface Application

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1
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
flow monitor ENCOR-MONITOR-V6
 record ENCOR-FLOW-RECORD-V6
 exporter ENCOR-EXPORTER
 cache timeout active 60
 cache timeout inactive 15
!
interface GigabitEthernet0/0
 ipv6 flow monitor ENCOR-MONITOR-V6 input
!
interface GigabitEthernet0/1
 ipv6 flow monitor ENCOR-MONITOR-V6 input
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show flow record ENCOR-FLOW-RECORD-V6
show flow monitor ENCOR-MONITOR-V6
show flow interface GigabitEthernet0/0
show flow monitor ENCOR-MONITOR-V6 cache
```
</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world FNF fault. Inject the fault first, then diagnose and fix using only `show` commands.

### Workflow

```bash
python3 setup_lab.py --host <eve-ng-ip>          # reset to known-good
python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>  # Ticket 1
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>      # restore
```

---

### Ticket 1 — No Flow Data Reaching the NMS

The NOC reports that R2's NetFlow collector has received zero packets from R1 in the past 10 minutes, even though the lab was working earlier. R1 is generating traffic normally.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>`

**Success criteria:** `show flow exporter ENCOR-EXPORTER statistics` shows "Successfully sent" incrementing, and R2's collector receives UDP packets on port 9996.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Check whether the exporter is sending: `show flow exporter ENCOR-EXPORTER statistics` — look for "Reason not sent" > 0.
2. Check the configured destination: `show flow exporter ENCOR-EXPORTER` — verify the destination IP.
3. Verify reachability to the destination: `ping <destination-ip> source Loopback0` — if unreachable, the configured IP may be wrong.
4. Compare the destination IP to R2's actual loopback: `show ip route 2.2.2.2` — R2's loopback is reachable; if the exporter shows a different IP, that's the fault.
</details>

<details>
<summary>Click to view Fix</summary>

The exporter destination was changed from 2.2.2.2 (R2 loopback) to 3.3.3.3 (R3 loopback). R3 has no NetFlow collector, so exports fail.

```bash
! R1
flow exporter ENCOR-EXPORTER
 no destination 3.3.3.3
 destination 2.2.2.2
```

Verify: `show flow exporter ENCOR-EXPORTER` — destination should show 2.2.2.2.
</details>

---

### Ticket 2 — LAN Traffic Missing from Flow Statistics

A security analyst reports that flows from the 192.168.10.0/24 LAN segment are absent from NetFlow data, while traffic transiting Gi0/1 (the WAN uplink) is captured normally.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py --host <eve-ng-ip>`

**Success criteria:** `show flow monitor ENCOR-MONITOR cache` shows entries with source or destination addresses in the 192.168.10.0/24 range after pinging from PC1.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Check which interfaces have FNF applied: `show flow interface GigabitEthernet0/0` — if no monitor is shown, the application was removed.
2. Compare with Gi0/1: `show flow interface GigabitEthernet0/1` — if Gi0/1 shows a monitor but Gi0/0 does not, the monitor was unbound from Gi0/0.
3. Look at the running config for Gi0/0: `show run interface GigabitEthernet0/0` — no `ip flow monitor` line confirms the fault.
</details>

<details>
<summary>Click to view Fix</summary>

The `ip flow monitor ENCOR-MONITOR input` command was removed from Gi0/0, leaving the LAN interface unmonitored.

```bash
! R1
interface GigabitEthernet0/0
 ip flow monitor ENCOR-MONITOR input
```

Verify: `show flow interface GigabitEthernet0/0` — must show ENCOR-MONITOR applied for input.
</details>

---

### Ticket 3 — Collector Reports Unrecognized Flow Format

R2's NetFlow collector is receiving UDP packets from R1 on port 9996, but is rejecting them with "unknown template" or "unsupported version" errors. The collector is configured for NetFlow v9.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py --host <eve-ng-ip>`

**Success criteria:** The collector accepts flow templates and records without format errors. `show flow exporter ENCOR-EXPORTER statistics` shows "Successfully sent" increasing with no "Send failures".

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Check the export protocol: `show flow exporter ENCOR-EXPORTER` — look at "Export protocol" field.
2. If the protocol shows NetFlow Version 5, that is the fault — v5 uses a fixed format that is incompatible with FNF custom records and with collectors expecting v9 templates.
3. NetFlow v5 cannot carry IPv6 flows or custom field definitions — symptoms will worsen when IPv6 monitors are in use.
</details>

<details>
<summary>Click to view Fix</summary>

The export protocol was downgraded from `netflow-v9` to `netflow-v5`. This breaks template-based export and is incompatible with FNF custom records.

```bash
! R1
flow exporter ENCOR-EXPORTER
 no export-protocol netflow-v5
 export-protocol netflow-v9
```

Verify: `show flow exporter ENCOR-EXPORTER` — "Export protocol" must show "NetFlow Version 9".
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] **Task 1** — IPv4 flow record ENCOR-FLOW-RECORD created with 5 match fields and 4 collect fields
- [ ] **Task 2** — Flow exporter ENCOR-EXPORTER configured: destination 2.2.2.2, source Loopback0, UDP 9996, NetFlow v9
- [ ] **Task 3** — IPv4 flow monitor ENCOR-MONITOR bound to record and exporter; active 60 s, inactive 15 s
- [ ] **Task 4** — ENCOR-MONITOR applied ingress on Gi0/0 and Gi0/1
- [ ] **Task 5** — IPv6 flow record ENCOR-FLOW-RECORD-V6 created with IPv6 match fields + transport + protocol
- [ ] **Task 6** — IPv6 flow monitor ENCOR-MONITOR-V6 created and applied ingress on Gi0/0 and Gi0/1
- [ ] `show flow monitor ENCOR-MONITOR cache` shows active IPv4 flow entries
- [ ] `show flow monitor ENCOR-MONITOR-V6 cache` shows active IPv6 flow entries
- [ ] `show flow exporter ENCOR-EXPORTER statistics` shows "Successfully sent" > 0 and "Reason not sent: 0"

### Troubleshooting

- [ ] **Ticket 1** — Identified and corrected the exporter destination misconfiguration
- [ ] **Ticket 2** — Identified and corrected the missing interface monitor binding
- [ ] **Ticket 3** — Identified and corrected the export protocol version mismatch
