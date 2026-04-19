# Lab 04 — Network Assurance Full Mastery — Capstone I

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

**Exam Objective:** 4.1, 4.2, 4.3, 4.4 — Full Network Assurance (network-assurance)

Network assurance is the practice of continuously measuring, recording, and acting on network state. This capstone integrates all four toolsets from the progressive lab series: diagnostics (debug, SNMP, syslog), Flexible NetFlow, SPAN/RSPAN traffic mirroring, and IP SLA active probing with automated tracking. Unlike the individual labs where each tool was introduced in isolation, here you must wire them all together from scratch — OSPF provides the routed foundation, and the monitoring tools must function end-to-end as a coherent observability stack.

---

### The Four-Layer Monitoring Stack

Each tool in the network assurance blueprint occupies a different layer of the observability pyramid:

| Layer | Tool | What It Answers |
|-------|------|----------------|
| Active probing | IP SLA | "Is the path alive? What is the latency and jitter?" |
| Traffic visibility | Flexible NetFlow | "Who is talking to whom, how much, when?" |
| Frame-level capture | SPAN / RSPAN | "What exactly is in these packets?" |
| Event correlation | Syslog / SNMP | "What events happened, and when were they reported?" |

Each layer answers a question the others cannot. A flapping link may not show up in NetFlow until flows expire; IP SLA detects it within the probe interval. A misconfigured ACL is invisible to IP SLA but obvious in a SPAN capture.

---

### OSPF as the Observability Foundation

Before any monitoring tool can function, the network must route. In this capstone, OSPF is your responsibility — not pre-configured. Every monitoring tool depends on reachability:

- NetFlow exports to R2 (2.2.2.2) over the OSPF-routed path
- IP SLA probes reach R3 (3.3.3.3) via OSPF
- SNMP traps are sent from R1/R2/R3 to R2's loopback

Configure OSPF area 0 across all three routers (R1, R2, R3) before configuring any monitoring tool, or none of the verifications will pass.

**OSPFv3 (IPv6) parallel:**
IOSv uses classic OSPFv3 syntax (`ipv6 router ospf 1` global process + `ipv6 ospf 1 area 0` per interface). Both IPv4 and IPv6 routing must be established before verifying dual-stack monitoring.

---

### NetFlow Component Dependencies

The three Flexible NetFlow components form a strict dependency chain. Configuring them out of order or missing one causes silent failure:

```
Flow Record  →  Flow Monitor  →  Interface (applied)
     ↓               ↓
Flow Exporter  →  Flow Monitor
```

| If you omit... | Symptom |
|---------------|---------|
| Flow record match fields | Monitor created but cache never populated |
| Flow exporter destination | Flows cached locally, never exported |
| Interface application | No flows in cache — monitor exists but sees no traffic |
| Correct direction (`input`) | May miss traffic; `output` captures different flows |

A flow monitor must be applied to an interface with a direction (`input` or `output`) before any flows will appear in `show flow monitor cache`.

---

### SPAN/RSPAN Session Dependencies

SPAN and RSPAN have hard prerequisites that must all be satisfied before mirrored traffic appears at the destination port:

| Requirement | Local SPAN | RSPAN |
|-------------|-----------|-------|
| Source port configured | Required | Required |
| Destination port configured | Required | Required |
| RSPAN VLAN (`remote-span`) | Not needed | Required — both switches |
| RSPAN VLAN on trunk | Not needed | Required — trunk must allow VLAN 500 |
| Destination session on remote switch | Not needed | Required — SW2 must reference VLAN 500 |

The RSPAN VLAN must be defined with `remote-span` and permitted on the trunk **before** configuring RSPAN monitor sessions — IOS rejects monitor commands that reference an undefined RSPAN VLAN.

---

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| Full-stack deployment | Configure all four network assurance toolsets from scratch in the correct dependency order |
| OSPF dual-stack foundation | Build IPv4 OSPF and IPv6 OSPFv3 routing before layering monitoring tools |
| NetFlow pipeline construction | Create flow record, exporter, and monitor; apply to interfaces in correct direction |
| SPAN and RSPAN | Configure local SPAN session and multi-switch RSPAN with RSPAN VLAN and trunk setup |
| IP SLA with tracking | Deploy ICMP echo, UDP jitter, and IPv6 probes; wire track object to static route |
| Diagnostic tools | Configure syslog, SNMP v2c, trap receiver, and conditional debug ACL |
| End-to-end verification | Use show commands across all four toolsets to confirm operational state |

---

## 2. Topology & Scenario

**Scenario:** Meridian Financial has deployed a new branch network segment. You have been handed a clean slate — only IP addresses are configured. Your task is to build the complete network assurance stack from OSPF routing through all four monitoring toolsets. The NOC team needs continuous visibility into path quality, flow data, packet captures, and event logs before the segment goes into production.

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

**Monitoring Architecture:**

| System | Source | Destination | Protocol |
|--------|--------|-------------|---------|
| NetFlow v9 | R1 (Gi0/0, Gi0/1) | R2 Lo0 (2.2.2.2) | UDP/9996 |
| SNMP traps | R1, R2, R3 | R2 Lo0 (2.2.2.2) | SNMPv2c |
| Local SPAN | SW1:Gi0/3 | SW1:Gi0/0 | In-switch copy |
| RSPAN | SW1:Gi0/3 → VLAN 500 | SW2:Gi0/0 | Tagged across trunk |
| IP SLA probes | R1 Lo0 (1.1.1.1) | R3 (3.3.3.3) | ICMP / UDP |

---

## 3. Hardware & Environment Specifications

### Device List

| Device | Platform | Role | IOS Version |
|--------|----------|------|-------------|
| R1 | IOSv (vios-adventerprisek9) | Edge router — NetFlow exporter, IP SLA source, syslog/SNMP | 15.x |
| R2 | IOSv (vios-adventerprisek9) | Distribution router — NetFlow collector, SNMP trap receiver | 15.x |
| R3 | IOSv (vios-adventerprisek9) | Remote router — IP SLA responder | 15.x |
| SW1 | IOSvL2 (vios_l2-adventerprisek9) | Access switch — SPAN source, RSPAN source | 15.x |
| SW2 | IOSvL2 (vios_l2-adventerprisek9) | Distribution switch — RSPAN destination | 15.x |
| PC1 | VPCS | Traffic source (VLAN 10) | — |
| PC2 | VPCS | Traffic destination (VLAN 20) | — |

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
- `ipv6 unicast-routing` enabled on all routers
- VLANs 10, 20, and 99 on SW1 and SW2
- Trunk between SW1 and SW2 (VLANs 10, 20, 99 — VLAN 500 NOT included)
- Access port assignments (SW1:Gi0/3 → VLAN 10, SW2:Gi0/3 → VLAN 20)
- Management SVIs (SW1: 192.168.99.11, SW2: 192.168.99.12)
- PC1: `192.168.10.10/24` gateway `192.168.10.1`
- PC2: `192.168.20.10/24` gateway `192.168.20.1`

### NOT pre-configured (your task — build everything from scratch)

- OSPF routing (IPv4 and IPv6) on all routers
- Syslog buffering and timestamps
- SNMP v2c communities, trap receiver, and interface traps
- Conditional debug ACL
- Flexible NetFlow (flow record, exporter, monitor — IPv4 and IPv6)
- Flow monitor application on R1 interfaces
- RSPAN VLAN 500 with `remote-span` designation
- RSPAN VLAN 500 on SW1-SW2 trunk
- Local SPAN session on SW1
- RSPAN source session on SW1 and destination session on SW2
- IP SLA responder on R3
- IP SLA probes (ICMP echo, UDP jitter, IPv6 ICMP echo) on R1
- SLA probe schedules
- Track object linked to SLA 1 reachability
- Tracked static route on R1

---

## 5. Lab Challenge: Full Protocol Mastery

> This is a capstone lab. No step-by-step guidance is provided.
> Configure the complete Network Assurance solution from scratch — IP addressing is pre-configured; everything else is yours to build.
> All blueprint bullets for this chapter must be addressed.

### Objectives

- Configure OSPF area 0 on R1, R2, and R3 (IPv4 and IPv6) so all loopbacks and subnets are reachable
- Configure syslog buffering (16384 bytes, informational severity, `datetime msec` timestamps) on all routers
- Configure SNMP v2c with read-only community `ENCOR-RO`, read-write community `ENCOR-RW`, trap receiver at R2 (2.2.2.2) using `ENCOR-RO`, and enable link-state and coldstart traps on all routers
- Create a conditional debug ACL on R1 named `DEBUG-FILTER` permitting traffic from PC1 (192.168.10.10)
- Build a complete Flexible NetFlow pipeline on R1: IPv4 flow record (`ENCOR-FLOW-RECORD`) with 5-tuple match and byte/packet/timestamp collect fields; IPv6 flow record (`ENCOR-FLOW-RECORD-V6`); exporter (`ENCOR-EXPORTER`) sending to R2 loopback (2.2.2.2) via UDP/9996 using NetFlow v9; IPv4 and IPv6 monitors applied to both R1 LAN and WAN interfaces in the input direction
- Create RSPAN VLAN 500 (named RSPAN, `remote-span`) on both SW1 and SW2, and add it to the trunk between them
- Configure local SPAN session 1 on SW1 mirroring PC1 port (Gi0/3) to the local monitoring port (Gi0/0)
- Configure RSPAN session 2 on SW1 sourcing from PC1 port (Gi0/3) to RSPAN VLAN 500; configure RSPAN destination session 1 on SW2 receiving from VLAN 500 and forwarding to Gi0/0
- Enable `ip sla responder` on R3
- Configure IP SLA 1 (ICMP echo, source 1.1.1.1, destination 3.3.3.3, frequency 30s), SLA 2 (UDP jitter, destination 3.3.3.3 port 5000, source 1.1.1.1, 10 packets, frequency 60s), and SLA 3 (IPv6 ICMP echo, destination 2001:db8:23::2, source-interface Gi0/1, frequency 30s); schedule all three probes `life forever start-time now`
- Create track object 1 monitoring SLA 1 reachability with 10-second up/down delay
- Add a static route on R1 for the R2-R3 link subnet (10.1.23.0/30) via 10.1.12.2, conditioned on track 1

---

## 6. Verification & Analysis

### OSPF — Routing Foundation

```
R1# show ip ospf neighbor
Neighbor ID     Pri   State           Dead Time   Address         Interface
2.2.2.2           1   FULL/DR         00:00:33    10.1.12.2       GigabitEthernet0/1   ! ← R2 neighbor up

R1# show ip route ospf
O    2.2.2.2/32 [110/2] via 10.1.12.2, 00:02:00, GigabitEthernet0/1    ! ← R2 loopback learned
O    3.3.3.3/32 [110/3] via 10.1.12.2, 00:02:00, GigabitEthernet0/1    ! ← R3 loopback learned
O    10.1.23.0/30 [110/2] via 10.1.12.2, 00:02:00, GigabitEthernet0/1  ! ← R2-R3 link learned
O    192.168.20.0/24 [110/2] via 10.1.12.2, 00:02:00, GigabitEthernet0/1
```

### Diagnostics — Syslog and SNMP

```
R1# show logging
Syslog logging: enabled (0 messages dropped, 0 flushes, 0 overruns)
    Console logging: level debugging
    Monitor logging: level debugging
    Buffer logging:  level informational, 16384 bytes               ! ← 16384 buffer, informational level
    Log Buffer (16384 bytes):
    *Apr 19 00:01:00.123: %LINK-3-UPDOWN: Interface Gi0/1, changed state to up   ! ← timestamps present
```

```
R1# show snmp community
Community name: ENCOR-RO                          ! ← RO community present
Community Index: cisco0
Community SecurityName: ENCOR-RO
storage-type: nonvolatile   active

Community name: ENCOR-RW                          ! ← RW community present
...

R1# show snmp host
Notification host: 2.2.2.2 udp-port: 162  type: trap   ! ← trap receiver = R2 Lo0
                   user: ENCOR-RO  security model: v2c  ! ← correct community
```

### Flexible NetFlow — Flow Cache

```
R1# show flow monitor ENCOR-MONITOR cache
Cache type:                              Normal (Platform cache)
Cache size:                                4096
Current entries:                              3     ! ← entries > 0 = flows are being captured

  IPV4 SRC ADDR  IPV4 DST ADDR  TRNS SRC PORT  TRNS DST PORT  IP PROT  bytes  pkts
  192.168.10.10  192.168.20.10          0              0           1     120     2   ! ← PC1→PC2 ICMP
  ...
```

```
R1# show flow exporter ENCOR-EXPORTER statistics
Flow Exporter ENCOR-EXPORTER:
  Packet send statistics (last cleared 00:03:00 ago):
    Successfully sent:          5 (720 bytes)              ! ← sent > 0 = exports reaching R2
    Send errors:                0                          ! ← zero send errors (routing OK)
```

### SPAN and RSPAN

```
SW1# show monitor session 1
Session 1
---------
Type                : Local Session
Source Ports        :
    Both            : Gi0/3                               ! ← PC1 port as source
Destination Ports   : Gi0/0                               ! ← local monitoring port
    Encapsulation   : Native
          Ingress   : Disabled

Session 2
---------
Type                   : Remote Source Session
Source Ports           :
    Both               : Gi0/3                            ! ← PC1 port
Destination RSPAN VLAN : 500                              ! ← traffic going into VLAN 500

SW2# show monitor session 1
Session 1
---------
Type                   : Remote Destination Session
Source RSPAN VLAN      : 500                              ! ← receiving from VLAN 500
Destination Ports      : Gi0/0                            ! ← remote monitoring port
    Encapsulation   : Native
          Ingress   : Disabled
```

```
SW1# show vlan id 500
VLAN  Name      Status   Ports
500   RSPAN      active                                    ! ← VLAN 500 exists
VLAN Type  SAID       MTU  ...
500  enet  100500     1500
Remote SPAN VLAN                                          ! ← must show "Remote SPAN VLAN"
```

### IP SLA and Tracking

```
R1# show ip sla summary
IPSLAs Latest Operation Summary
Codes: * active, ^ inactive, ~ pending

ID           Type        Destination       Stats        Return      Last
                                          (ms)         Code        Run
-----------------------------------------------------------------------
*1           icmp-echo   3.3.3.3           RTT=2        OK          00:01:00   ! ← OK, RTT present
*2           udp-jitter  3.3.3.3           RTT=3        OK          00:01:00   ! ← OK
*3           icmp-echo   2001:DB8:23::2    RTT=3        OK          00:01:00   ! ← IPv6 probe OK
```

```
R1# show track 1
Track 1
  IP SLA 1 Reachability                                   ! ← references SLA 1
  Reachability is Up                                      ! ← Up
    1 change, last change 00:02:00
  Delay up 10 secs, down 10 secs                          ! ← delay configured

Tracked by:
  Static IP Routing 0                                     ! ← route is watching track

R1# show ip route 10.1.23.0
Routing entry for 10.1.23.0/30
  Known via "static", distance 1, metric 0               ! ← AD 1 = static active
  * 10.1.12.2, via GigabitEthernet0/1
```

---

## 7. Verification Cheatsheet

### OSPF Verification

```
show ip ospf neighbor
show ip route ospf
show ipv6 route ospf
show ip ospf interface brief
```

| Command | What to Look For |
|---------|-----------------|
| `show ip ospf neighbor` | All expected neighbors in FULL state |
| `show ip route ospf` | All remote loopbacks and subnets present (AD 110) |
| `show ipv6 route ospf` | IPv6 equivalents (O prefix) |

### Diagnostics Configuration

```
service timestamps log datetime msec
logging buffered <size> <severity>
snmp-server community <name> RO
snmp-server host <ip> version 2c <community>
snmp-server enable traps snmp linkdown linkup coldstart
ip access-list extended <name>
 permit ip host <src> any
```

| Command | Purpose |
|---------|---------|
| `service timestamps log datetime msec` | Add date/time to all syslog messages |
| `logging buffered 16384 informational` | Buffer syslog locally at severity 6 |
| `snmp-server community ENCOR-RO RO` | Define read-only community |
| `snmp-server host 2.2.2.2 version 2c ENCOR-RO` | Send traps to R2 loopback |
| `snmp-server enable traps snmp linkdown linkup coldstart` | Enable interface and boot traps |

> **Exam tip:** SNMP traps use UDP/162 by default. The trap receiver must be reachable via routing — configure OSPF before testing SNMP trap delivery.

### Flexible NetFlow Configuration

```
flow record <name>
 match ipv4 source address
 match ipv4 destination address
 match transport source-port
 match transport destination-port
 match ip protocol
 collect counter bytes long
 collect counter packets long
 collect timestamp sys-uptime first
 collect timestamp sys-uptime last

flow exporter <name>
 destination <ip>
 source <interface>
 transport udp 9996
 export-protocol netflow-v9

flow monitor <name>
 record <record-name>
 exporter <exporter-name>
 cache timeout active 60
 cache timeout inactive 15

interface <intf>
 ip flow monitor <monitor-name> input
 ipv6 flow monitor <v6-monitor-name> input
```

| Command | Purpose |
|---------|---------|
| `match ipv4 source address` | Identify flows by source IP |
| `collect counter bytes long` | Count bytes per flow |
| `export-protocol netflow-v9` | Use NetFlow v9 format (supports IPv6) |
| `cache timeout active 60` | Export flows after 60s even if still active |
| `ip flow monitor <name> input` | Apply monitor to interface (ingress traffic) |

> **Exam tip:** `flow monitor` must be applied to an interface with a direction keyword (`input` or `output`). A monitor configured but never applied produces an empty cache.

### SPAN and RSPAN Configuration

```
! RSPAN VLAN — both switches
vlan 500
 name RSPAN
 remote-span

! SW1 — local SPAN
monitor session 1 source interface <port>
monitor session 1 destination interface <port>

! SW1 — RSPAN source
monitor session 2 source interface <port>
monitor session 2 destination remote vlan 500

! SW2 — RSPAN destination
monitor session 1 source remote vlan 500
monitor session 1 destination interface <port>

! Trunk — must include VLAN 500
switchport trunk allowed vlan add 500
```

| Command | Purpose |
|---------|---------|
| `vlan 500 / remote-span` | Mark VLAN as RSPAN transport; suppresses STP/CDP |
| `monitor session N source interface X` | Set SPAN capture source |
| `monitor session N destination remote vlan 500` | Send copies into RSPAN VLAN |
| `monitor session N source remote vlan 500` | Receive copies from RSPAN VLAN |
| `switchport trunk allowed vlan add 500` | Allow RSPAN VLAN on trunk (easy to miss!) |

> **Exam tip:** RSPAN fails silently if VLAN 500 is not in the trunk allowed list. Always verify with `show interfaces trunk` after configuring RSPAN.

### IP SLA Configuration

```
ip sla <N>
 icmp-echo <dst> source-ip <src>
 frequency <sec>
ip sla schedule <N> life forever start-time now

ip sla <N>
 udp-jitter <dst> <port> source-ip <src> num-packets <count>
 frequency <sec>
ip sla schedule <N> life forever start-time now

ip sla responder                        ! on target device

track <id> ip sla <N> reachability
 delay down <sec> up <sec>

ip route <prefix> <mask> <next-hop> track <id>
```

| Command | Purpose |
|---------|---------|
| `ip sla schedule N life forever start-time now` | Start probe immediately, run forever |
| `ip sla responder` | Enable on target for UDP jitter probes |
| `track N ip sla N reachability` | Watch probe state (Up/Down) |
| `delay down 10 up 10` | Prevent flapping from brief interruptions |
| `ip route ... track N` | Conditional static — installed only when track is Up |

> **Exam tip:** `ip sla schedule` is mandatory — without it, the probe never runs. A configured-but-not-scheduled SLA operation shows `*pending*` in `show ip sla statistics`.

### Verification Commands

| Command | What to Look For |
|---------|-----------------|
| `show ip ospf neighbor` | All neighbors in FULL state |
| `show logging` | Timestamps present; buffer size and severity correct |
| `show snmp community` | Both ENCOR-RO and ENCOR-RW present |
| `show snmp host` | Trap receiver = 2.2.2.2, community = ENCOR-RO |
| `show flow monitor ENCOR-MONITOR cache` | Current entries > 0 after generating traffic |
| `show flow exporter ENCOR-EXPORTER statistics` | Successfully sent > 0, send errors = 0 |
| `show monitor session 1` (SW1) | Type = Local Session, source = Gi0/3, dest = Gi0/0 |
| `show monitor session 2` (SW1) | Type = Remote Source Session, dest RSPAN VLAN 500 |
| `show monitor session 1` (SW2) | Type = Remote Destination Session, source VLAN 500 |
| `show vlan id 500` | VLAN 500 shows "Remote SPAN VLAN" |
| `show interfaces trunk` (SW1) | VLAN 500 in allowed and forwarding columns |
| `show ip sla summary` | All 3 operations marked `*` (active), return code OK |
| `show track 1` | Reachability is Up, references SLA 1 |
| `show ip route 10.1.23.0` | Static route present (AD 1) |

### Common Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| OSPF neighbors not forming | Missing `network` statement or mismatched area |
| No syslog timestamps | `service timestamps log datetime msec` not configured |
| SNMP traps not delivered | OSPF not configured (trap receiver unreachable) or wrong community |
| Flow cache always empty | Monitor not applied to any interface |
| Flow exporter send errors | Wrong destination IP (2.2.2.2) or OSPF route missing |
| RSPAN no traffic at SW2 | VLAN 500 not in trunk allowed list, or missing `remote-span` keyword |
| SLA statistics pending | `ip sla schedule` not entered for that operation |
| SLA UDP jitter `No connection` | `ip sla responder` not configured on R3 |
| Track stays Down | Referenced SLA operation not scheduled or not reaching target |
| Static route not installed | Track is Down, or `track` keyword missing from `ip route` command |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the capstone without looking at these solutions first!

### OSPF — R1, R2, R3

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1 — OSPF area 0 (IPv4 + IPv6)
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
interface GigabitEthernet0/0
 ipv6 ospf 1 area 0
!
interface GigabitEthernet0/1
 ipv6 ospf 1 area 0
```
</details>

<details>
<summary>Click to view R2 Configuration</summary>

```bash
! R2 — OSPF area 0
router ospf 1
 router-id 2.2.2.2
 passive-interface GigabitEthernet0/0
 network 2.2.2.2 0.0.0.0 area 0
 network 10.1.12.0 0.0.0.3 area 0
 network 10.1.23.0 0.0.0.3 area 0
 network 192.168.20.0 0.0.0.255 area 0
!
ipv6 router ospf 1
 router-id 2.2.2.2
 passive-interface GigabitEthernet0/0
!
interface GigabitEthernet0/0
 ipv6 ospf 1 area 0
!
interface GigabitEthernet0/1
 ipv6 ospf 1 area 0
!
interface GigabitEthernet0/2
 ipv6 ospf 1 area 0
```
</details>

<details>
<summary>Click to view R3 Configuration</summary>

```bash
! R3 — OSPF area 0
router ospf 1
 router-id 3.3.3.3
 network 3.3.3.3 0.0.0.0 area 0
 network 10.1.23.0 0.0.0.3 area 0
!
ipv6 router ospf 1
 router-id 3.3.3.3
!
interface GigabitEthernet0/0
 ipv6 ospf 1 area 0
```
</details>

---

### Diagnostics — Syslog, SNMP, Debug ACL

<details>
<summary>Click to view R1 Configuration (all routers follow the same pattern)</summary>

```bash
! R1 — Syslog, SNMP, debug ACL
service timestamps log datetime msec
!
logging buffered 16384 informational
!
snmp-server community ENCOR-RO RO
snmp-server community ENCOR-RW RW
snmp-server host 2.2.2.2 version 2c ENCOR-RO
snmp-server enable traps snmp linkdown linkup coldstart
!
ip access-list extended DEBUG-FILTER
 permit ip host 192.168.10.10 any
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show logging
show snmp community
show snmp host
show ip access-lists DEBUG-FILTER
```
</details>

---

### Flexible NetFlow — R1

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1 — Flexible NetFlow pipeline
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
interface GigabitEthernet0/0
 ip flow monitor ENCOR-MONITOR input
 ipv6 flow monitor ENCOR-MONITOR-V6 input
!
interface GigabitEthernet0/1
 ip flow monitor ENCOR-MONITOR input
 ipv6 flow monitor ENCOR-MONITOR-V6 input
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show flow monitor ENCOR-MONITOR cache
show flow exporter ENCOR-EXPORTER statistics
show flow monitor ENCOR-MONITOR-V6 cache
```
</details>

---

### SPAN and RSPAN — SW1, SW2

<details>
<summary>Click to view SW1 Configuration</summary>

```bash
! SW1 — RSPAN VLAN + SPAN sessions
vlan 500
 name RSPAN
 remote-span
!
interface GigabitEthernet0/1
 switchport trunk allowed vlan 10,20,99,500
!
monitor session 1 source interface GigabitEthernet0/3
monitor session 1 destination interface GigabitEthernet0/0
!
monitor session 2 source interface GigabitEthernet0/3
monitor session 2 destination remote vlan 500
```
</details>

<details>
<summary>Click to view SW2 Configuration</summary>

```bash
! SW2 — RSPAN VLAN + destination session
vlan 500
 name RSPAN
 remote-span
!
interface GigabitEthernet0/1
 switchport trunk allowed vlan 10,20,99,500
!
monitor session 1 source remote vlan 500
monitor session 1 destination interface GigabitEthernet0/0
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
! SW1:
show monitor session 1
show monitor session 2
show vlan id 500
show interfaces trunk

! SW2:
show monitor session 1
show vlan id 500
```
</details>

---

### IP SLA, Track, and Failover — R1, R3

<details>
<summary>Click to view R3 Configuration</summary>

```bash
! R3 — IP SLA responder
ip sla responder
```
</details>

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1 — IP SLA probes + track + static route
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
ip route 10.1.23.0 255.255.255.252 10.1.12.2 track 1
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ip sla summary
show ip sla statistics 1
show ip sla statistics 2
show ip sla statistics 3
show track 1
show ip route 10.1.23.0
```
</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault injected into the working capstone configuration. Inject the fault first, then diagnose and fix using only show commands.

### Workflow

```bash
python3 setup_lab.py                                   # reset to known-good
python3 scripts/fault-injection/inject_scenario_01.py  # Ticket 1
python3 scripts/fault-injection/apply_solution.py      # restore
```

---

### Ticket 1 — NetFlow Collector on R2 Reports No Flow Records from R1

The NOC team reports that the NetFlow dashboard (monitoring R2 as collector) has shown no new flow data from R1 for the past 10 minutes. OSPF adjacencies are up and PC1 can ping PC2 successfully. `show flow monitor ENCOR-MONITOR cache` on R1 shows flows in the cache.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py`

**Success criteria:** `show flow exporter ENCOR-EXPORTER statistics` shows Successfully sent > 0 and Send errors = 0.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Run `show flow monitor ENCOR-MONITOR cache` — flows ARE in the cache, so the monitor is working and traffic is being seen.
2. Run `show flow exporter ENCOR-EXPORTER statistics` — look for `Send errors` > 0 or `Successfully sent` = 0.
3. Run `show flow exporter ENCOR-EXPORTER` — inspect the destination IP. The exporter destination will show `2.2.2.3` instead of `2.2.2.2`.
4. Verify: `ping 2.2.2.3 source loopback 0` from R1 — fails (no route), confirming the exporter is aimed at a non-existent host.
5. Compare to expected destination: R2's loopback is 2.2.2.2 per the design. The off-by-one (2.2.2.3) is the fault.
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! On R1 — correct the exporter destination IP
no flow exporter ENCOR-EXPORTER
flow exporter ENCOR-EXPORTER
 destination 2.2.2.2
 source Loopback0
 transport udp 9996
 export-protocol netflow-v9
```

Verify: `show flow exporter ENCOR-EXPORTER statistics` — Successfully sent increments; Send errors = 0.
</details>

---

### Ticket 2 — Remote Monitoring Port on SW2 Captures No Traffic

A security analyst has connected a laptop to SW2:Gi0/0 to capture PC1 traffic via RSPAN. The RSPAN sessions on both switches appear configured, but the capture shows nothing. The analyst can see traffic on SW1's local monitoring port (Gi0/0).

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py`

**Success criteria:** `show monitor session 1` on SW2 shows status Active, and traffic from PC1 is visible at SW2:Gi0/0.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Run `show monitor session 1` on SW2 — session appears configured (source VLAN 500, destination Gi0/0).
2. Run `show monitor session 2` on SW1 — source Gi0/3, destination remote VLAN 500 — appears correct.
3. Run `show interfaces trunk` on SW1 — inspect the "VLANs allowed on trunk" column. VLAN 500 will be **missing** from the allowed list. The trunk shows 10,20,99 but not 500.
4. Run `show vlan id 500` on SW1 — VLAN 500 exists with `remote-span` designation. The VLAN is defined but not permitted on the trunk.
5. Conclusion: RSPAN frames hit VLAN 500 but cannot cross the trunk to SW2 because VLAN 500 was removed from the trunk allowed list.
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! On SW1 — add VLAN 500 back to the trunk
interface GigabitEthernet0/1
 switchport trunk allowed vlan add 500
```

Verify: `show interfaces trunk` on SW1 shows 500 in the allowed and forwarding columns. Traffic appears at SW2:Gi0/0.
</details>

---

### Ticket 3 — IP SLA Statistics Show "Pending" — Probes Not Running

During a routine check, you notice that `show ip sla summary` on R1 shows all three IP SLA operations marked with `~` (pending) rather than `*` (active). The probe configurations look correct. No RTT data is available.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py`

**Success criteria:** `show ip sla summary` shows all three operations marked `*` (active) with return code OK and RTT values populated. `show track 1` shows State: Up. `show ip route 10.1.23.0` shows the track-conditioned static route installed.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Run `show ip sla summary` — all operations show `~` (pending), meaning scheduled but not yet started.
2. Run `show ip sla configuration 1` — look at the schedule line. It shows `start-time pending` rather than `start-time now`.
3. Repeat for SLA 2 and 3 — all three have `start-time pending`.
4. The schedule was reconfigured to `start-time pending`, which queues the probe but never fires it.
5. `show ip sla statistics 1` returns no data — the probe has never run.
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! On R1 — reschedule all three probes to start immediately
no ip sla schedule 1
no ip sla schedule 2
no ip sla schedule 3
ip sla schedule 1 life forever start-time now
ip sla schedule 2 life forever start-time now
ip sla schedule 3 life forever start-time now
```

Verify: Within 30 seconds, `show ip sla summary` shows all three operations as `*` (active) with return code OK.
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] OSPF area 0 established on R1, R2, R3 — all loopbacks and subnets reachable
- [ ] IPv6 OSPFv3 established — IPv6 routes present on all routers
- [ ] Syslog configured (16384 bytes, informational, `datetime msec`) on all routers
- [ ] SNMP v2c with ENCOR-RO and ENCOR-RW communities on all routers
- [ ] SNMP trap receiver at 2.2.2.2 using ENCOR-RO, interface traps enabled
- [ ] Conditional debug ACL `DEBUG-FILTER` on R1 matching 192.168.10.10
- [ ] IPv4 flow record `ENCOR-FLOW-RECORD` with 5-tuple match + byte/packet/timestamp collect
- [ ] IPv6 flow record `ENCOR-FLOW-RECORD-V6` with matching fields
- [ ] Flow exporter `ENCOR-EXPORTER` sending to 2.2.2.2 via UDP/9996, NetFlow v9
- [ ] IPv4 and IPv6 flow monitors applied to R1 Gi0/0 and Gi0/1 (input direction)
- [ ] `show flow monitor ENCOR-MONITOR cache` shows entries after generating traffic
- [ ] VLAN 500 (`remote-span`) defined on SW1 and SW2
- [ ] VLAN 500 allowed on SW1-SW2 trunk
- [ ] Local SPAN session 1 on SW1 (source Gi0/3 → dest Gi0/0)
- [ ] RSPAN session 2 on SW1 (source Gi0/3 → remote VLAN 500)
- [ ] RSPAN destination session 1 on SW2 (source VLAN 500 → Gi0/0)
- [ ] `ip sla responder` on R3
- [ ] SLA 1 (ICMP echo, 3.3.3.3, source 1.1.1.1, 30s) scheduled and running
- [ ] SLA 2 (UDP jitter, 3.3.3.3:5000, source 1.1.1.1, 10 pkts, 60s) scheduled and running
- [ ] SLA 3 (IPv6 ICMP echo, 2001:db8:23::2, source Gi0/1, 30s) scheduled and running
- [ ] Track 1 monitoring SLA 1 reachability with 10s delay
- [ ] Static route `10.1.23.0/30` via `10.1.12.2` conditioned on track 1

### Troubleshooting

- [ ] **Ticket 1:** Identified wrong exporter destination (2.2.2.3); corrected to 2.2.2.2 and verified exports succeed
- [ ] **Ticket 2:** Identified VLAN 500 missing from trunk allowed list; added and verified RSPAN traffic crosses to SW2
- [ ] **Ticket 3:** Identified probes stuck in pending state; rescheduled with `start-time now`; verified SLA active, Track 1 Up, static route 10.1.23.0/30 installed
