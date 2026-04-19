# Lab 02 — SPAN, RSPAN, and ERSPAN

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

**Exam Objective:** 4.3 — Configure and verify SPAN/RSPAN on IOS switches (network-assurance)

Traffic analysis is a foundational NOC skill — you cannot debug what you cannot see. SPAN and RSPAN give you a non-intrusive way to mirror live traffic from a production port to an analyzer without inserting a tap or breaking a circuit. This lab builds SPAN locally on SW1 and then extends the mirror across a trunk link to SW2 using RSPAN, mirroring the enterprise pattern where the network analyzer lives on a different switch than the monitored port.

---

### Local SPAN (Switched Port Analyzer)

SPAN copies frames arriving on (or leaving) a **source** port to a **destination** port on the **same switch**. The destination port receives an exact copy of source traffic; it cannot carry normal data while it is a SPAN destination.

Key rules:
- Source and destination must be on the same switch.
- Up to 4 SPAN sessions per switch (platform-dependent).
- Source can be one or more interfaces, or an entire VLAN.
- Destination port is taken out of normal forwarding; it only delivers mirrored frames.

**IOS syntax:**
```
monitor session <N> source interface <interface> [rx | tx | both]
monitor session <N> destination interface <interface>
```

`both` is the default direction — bidirectional (ingress + egress) monitoring.

---

### RSPAN (Remote SPAN)

RSPAN extends port mirroring across multiple switches using a dedicated **RSPAN VLAN** as the transport vehicle. The VLAN carries only mirrored frames — STP, VTP, and other control plane protocols are suppressed on it.

**Three-switch components:**

| Component | Where | What it does |
|-----------|-------|-------------|
| RSPAN VLAN | Both switches | Declared with `remote-span` keyword; marks VLAN as mirrored-traffic-only |
| Source session | Source switch (SW1) | Captures port traffic; sends copies into RSPAN VLAN |
| Destination session | Destination switch (SW2) | Receives frames from RSPAN VLAN; forwards to local analyzer port |

**IOS syntax (source switch):**
```
monitor session <N> source interface <interface>
monitor session <N> destination remote vlan <vlan-id>
```

**IOS syntax (destination switch):**
```
monitor session <N> source remote vlan <vlan-id>
monitor session <N> destination interface <interface>
```

**Critical requirement:** RSPAN VLAN must be defined with `remote-span` on *both* switches and must be allowed on the trunk link connecting them.

---

### ERSPAN (Encapsulated Remote SPAN)

ERSPAN encapsulates mirrored frames in GRE and transports them across a routed Layer 3 network — no trunk or dedicated VLAN required. The GRE tunnel can traverse any IP path.

ERSPAN is supported on IOS-XE (CSR1000v) only — **not** on IOSvL2. It is covered here as theory for the 350-401 exam; no configuration is performed in this lab.

| Type | Transport | Destination | Platform |
|------|-----------|-------------|----------|
| SPAN | Same switch | Local port | All |
| RSPAN | Trunk VLAN | Remote switch port | All |
| ERSPAN | GRE / IP | Any L3 endpoint | IOS-XE only |

> **Exam tip:** Expect questions comparing the three types. The key distinguishing factor is whether the transport is intra-switch, inter-switch (L2), or routed (L3/GRE).

---

### Session Limits and Restrictions

- A port **cannot** be both a source and a destination in different sessions simultaneously.
- A destination port **cannot** be a trunk or participate in EtherChannel while in use as a SPAN destination.
- SPAN source VLAN monitors all ports in that VLAN (not a specific port).
- `show monitor session` reports **Active** or **Inactive** but cannot confirm actual traffic flow — use a sniffer on the destination port to verify mirroring is working.

---

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| Local SPAN | Configure and verify a single-switch mirror session |
| RSPAN source session | Extend a mirror across a trunk into a remote VLAN |
| RSPAN destination session | Terminate the remote VLAN onto a local analyzer port |
| RSPAN VLAN design | Declare and propagate the remote-span VLAN correctly |
| Session verification | Use `show monitor session` to confirm Active status |
| Session teardown | Remove sessions cleanly without disrupting remaining sessions |

---

## 2. Topology & Scenario

**Scenario:** The NOC at Acme Corp has reported intermittent latency complaints from users in Site A (VLAN 10). The network team needs to capture PC1's traffic simultaneously at two points: on SW1 locally (where a laptop analyzer is connected to Gi0/0), and on SW2 remotely (where the permanent Wireshark appliance lives on Gi0/0). Your task is to configure local SPAN on SW1 for immediate capture, and RSPAN across the existing trunk to deliver the same mirror to the remote analyzer on SW2.

```
              ┌─────────────────────────────────┐
              │              R1                 │
              │        (Gateway / OSPF)         │
              │  Lo0: 1.1.1.1   Gi0/0: 192.168.10.1/24  │
              └───────────────┬─────────────────┘
                              │ Gi0/0 — access VLAN 10
                              │ (connected to SW1 Gi0/2)
              ┌───────────────┴─────────────────┐
              │              SW1                │
              │       (IOSvL2 — Site A)         │
              │  Vlan99: 192.168.99.11/24        │
              └─────┬──────┬──────┬─────────────┘
        Gi0/0 (dest)│  Gi0/2│  Gi0/3│  Gi0/1 (trunk)
    Local analyzer  │   R1  │  PC1  │  ──────────────────┐
                    │       │       │                    │
                    │       │       │                    │ VLAN 500 (RSPAN)
                    │       │       │              ┌─────┴──────────────────┐
                    │       │       │              │           SW2          │
                    │       │       │              │    (IOSvL2 — Site B)   │
                    │       │       │              │  Vlan99: 192.168.99.12 │
                    │       │       │              └──┬───────┬─────────────┘
                    │       │       │          Gi0/0  │  Gi0/2│  Gi0/3
                    │       │       │    Remote anlzr │   R2  │  PC2
                    │       │
              ┌─────┴───────┴──────────────┐
              │             PC1            │
              │  192.168.10.10/24          │
              └────────────────────────────┘

SPAN Session Flow:
  Local SPAN  : SW1 Gi0/3 (src) ──────────────────► SW1 Gi0/0 (dst)
  RSPAN       : SW1 Gi0/3 (src) → VLAN 500 trunk → SW2 Gi0/0 (dst)
```

**IP Addressing Summary:**

| Device | Interface | IPv4 Address | IPv6 Address |
|--------|-----------|-------------|-------------|
| R1 | Lo0 | 1.1.1.1/32 | — |
| R1 | Gi0/0 | 192.168.10.1/24 | 2001:db8:10::1/64 |
| R1 | Gi0/1 | 10.1.12.1/30 | 2001:db8:12::1/64 |
| R2 | Lo0 | 2.2.2.2/32 | — |
| R2 | Gi0/0 | 192.168.20.1/24 | 2001:db8:20::1/64 |
| R2 | Gi0/1 | 10.1.12.2/30 | 2001:db8:12::2/64 |
| R2 | Gi0/2 | 10.1.23.1/30 | 2001:db8:23::1/64 |
| R3 | Lo0 | 3.3.3.3/32 | — |
| R3 | Gi0/0 | 10.1.23.2/30 | 2001:db8:23::2/64 |
| SW1 | Vlan99 | 192.168.99.11/24 | — |
| SW2 | Vlan99 | 192.168.99.12/24 | — |
| PC1 | eth0 | 192.168.10.10/24 | — |
| PC2 | eth0 | 192.168.20.10/24 | — |

---

## 3. Hardware & Environment Specifications

**Platform:** EVE-NG on Dell Latitude 5540 (Intel/Windows)

**Device Images:**

| Device | EVE-NG Image | IOS Version |
|--------|-------------|------------|
| R1, R2, R3 | IOSv (iosv-157-3) | 15.7(3)M |
| SW1, SW2 | IOSvL2 (iosvl2-15.x) | 15.x |
| PC1, PC2 | VPCS | — |

**Cabling Table:**

| Link | Device A | Interface | Device B | Interface | Type |
|------|----------|-----------|----------|-----------|------|
| L1 | R1 | Gi0/0 | SW1 | Gi0/2 | Access VLAN 10 |
| L2 | R2 | Gi0/0 | SW2 | Gi0/2 | Access VLAN 20 |
| L3 | R1 | Gi0/1 | R2 | Gi0/1 | Routed /30 |
| L4 | R2 | Gi0/2 | R3 | Gi0/0 | Routed /30 |
| L5 | SW1 | Gi0/1 | SW2 | Gi0/1 | 802.1Q Trunk |
| L6 | SW1 | Gi0/3 | PC1 | eth0 | Access VLAN 10 |
| L7 | SW2 | Gi0/3 | PC2 | eth0 | Access VLAN 20 |

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

The following is pre-configured in `initial-configs/` and loaded by `setup_lab.py`:

**Pre-loaded on all devices:**
- Hostnames and `service timestamps log datetime msec`
- IPv4 and IPv6 addressing on all interfaces
- OSPF and OSPFv3 (classic syntax) with correct router IDs and passive interfaces
- SNMP v2c communities and syslog buffering (from lab-01 inheritance)
- Flexible NetFlow records/exporters/monitors on R1 (from lab-01 inheritance)
- VLANs 10 (DATA-A), 20 (DATA-B), 99 (MGMT), and 500 (RSPAN) on SW1 and SW2
- VLAN 500 declared with `remote-span` on both switches
- Trunk link between SW1 Gi0/1 and SW2 Gi0/1 with VLAN 500 allowed
- PC1 and PC2 IP addresses

**NOT pre-loaded (student configures):**
- Local SPAN monitoring session on SW1
- RSPAN source session on SW1
- RSPAN destination session on SW2
- Gi0/0 destination port activation on SW1 and SW2

> **Note:** VLAN 500 is already defined with `remote-span` on both switches and is already allowed on the trunk. The RSPAN VLAN plumbing is done — your job is to configure the monitoring sessions that use it.

---

## 5. Lab Challenge: Core Implementation

### Task 1: Configure Local SPAN on SW1

On SW1, configure a local monitoring session (session number 1) that mirrors all traffic from the PC1 access port to the local analyzer port (Gi0/0). Both ingress and egress traffic should be captured.

- Source: the access port carrying PC1's traffic
- Destination: the Gi0/0 port where a local analyzer is connected

**Verification:** `show monitor session 1` must show Status: Active and identify the correct source and destination interfaces.

---

### Task 2: Configure RSPAN Source Session on SW1

On SW1, configure a second monitoring session (session number 2) that also sources from the PC1 access port. This session must forward the mirrored traffic into the RSPAN VLAN so it is carried across the trunk to SW2.

- Source: the same PC1 access port used in Task 1 (SPAN source sessions can share a source)
- Destination: the remote RSPAN VLAN (VLAN 500)

**Verification:** `show monitor session 2` on SW1 must show Status: Active and identify VLAN 500 as the remote destination.

---

### Task 3: Configure RSPAN Destination Session on SW2

On SW2, configure a monitoring session (session number 1) that receives mirrored frames from RSPAN VLAN 500 and delivers them to the permanent analyzer port on Gi0/0.

- Source: remote VLAN 500 (receives frames pushed by SW1 session 2)
- Destination: Gi0/0 on SW2 where the Wireshark appliance is connected

**Verification:** `show monitor session 1` on SW2 must show Status: Active and identify remote VLAN 500 as the source and Gi0/0 as the destination.

---

### Task 4: Verify RSPAN VLAN Transport

Confirm that VLAN 500 is correctly declared as a remote-span VLAN on both switches and is actively forwarded across the trunk link.

- Verify the RSPAN VLAN definition on both switches
- Verify VLAN 500 appears in the trunk's allowed and active VLAN lists on both SW1 and SW2

**Verification:** `show vlan id 500` must show Type: Remote Span. `show interfaces trunk` on both switches must show VLAN 500 in the VLANs allowed and active column.

---

### Task 5: Remove and Recreate Sessions

Practice session lifecycle management: remove all monitoring sessions from both switches, then recreate only the RSPAN sessions (Tasks 2 and 3). Do not restore the local SPAN session.

- Remove all sessions from SW1 and SW2 cleanly
- Recreate the RSPAN source session on SW1 (Task 2 configuration)
- Recreate the RSPAN destination session on SW2 (Task 3 configuration)

**Verification:** `show monitor session all` on each switch must show only the RSPAN sessions (no local SPAN session 1 on SW1). All active sessions must show Status: Active.

---

## 6. Verification & Analysis

> **Important:** `show monitor session` confirms that the session is **configured correctly** and the ports are operationally up. It does NOT prove that traffic is flowing through the mirror. To verify actual packet capture, you would connect a sniffer (e.g., Wireshark) to the destination port, or use EVE-NG's built-in link capture on the destination interface. The verification below confirms correct configuration and session state.

### Task 1 — Local SPAN on SW1

```
SW1# show monitor session 1
Session 1
---------
Type              : Local Session
Source Ports      :
    Both          : Gi0/3          ! ← PC1 port must be source (both directions)
Destination Ports : Gi0/0          ! ← local analyzer port
    Encapsulation : Native
          Ingress : Disabled
    Status        : Active         ! ← must be Active; Inactive means port issue
```

```
SW1# show monitor session 1 detail
Session 1
---------
Type              : Local Session
Source Ports      :
    Both          : GigabitEthernet0/3   ! ← correct source
Destination Ports : GigabitEthernet0/0  ! ← correct destination
    Encapsulation : Native
          Ingress : Disabled
    Status        : Active
```

### Task 2 — RSPAN Source Session on SW1

```
SW1# show monitor session 2
Session 2
---------
Type              : Remote Source Session
Source Ports      :
    Both          : Gi0/3               ! ← same source as session 1; allowed
Destination RSPAN VLAN : 500            ! ← RSPAN VLAN must be 500
    Status        : Active              ! ← must be Active
```

### Task 3 — RSPAN Destination Session on SW2

```
SW2# show monitor session 1
Session 1
---------
Type              : Remote Destination Session
Source RSPAN VLAN : 500                 ! ← must match SW1's session 2
Destination Ports : Gi0/0              ! ← remote analyzer port
    Encapsulation : Native
          Ingress : Disabled
    Status        : Active             ! ← must be Active
```

### Task 4 — RSPAN VLAN Transport

```
SW1# show vlan id 500

VLAN Name                             Status    Ports
---- -------------------------------- --------- -------------------------------
500  RSPAN                            active              ! ← VLAN must exist
                                                           ! ← no ports listed (by design)

VLAN Type  SAID       MTU   Parent RingNo BridgeNo Stp  BrdgMode Trans1 Trans2
---- ----- ---------- ----- ------ ------ -------- ---- -------- ------ ------
500  enet  100500     1500  -      -      -        -    -        0      0

Remote SPAN VLAN
----------------
Enabled                                 ! ← Remote SPAN must show Enabled
```

```
SW1# show interfaces trunk

Port        Mode         Encapsulation  Status        Native vlan
Gi0/1       on           802.1q         trunking      1

Port        Vlans allowed on trunk
Gi0/1       10,20,99,500                ! ← VLAN 500 must be in allowed list

Port        Vlans allowed and active in management domain
Gi0/1       10,20,99,500               ! ← VLAN 500 must be active on trunk

Port        Vlans in spanning tree forwarding state and not pruned
Gi0/1       10,20,99                   ! ← VLAN 500 absent here is correct
                                        ! ← RSPAN VLAN has STP suppressed
```

### Task 5 — After Teardown and Recreate

```
SW1# show monitor session all
Session 2
---------
Type              : Remote Source Session
Source Ports      :
    Both          : Gi0/3
Destination RSPAN VLAN : 500
    Status        : Active             ! ← only session 2; session 1 removed
```

```
SW2# show monitor session all
Session 1
---------
Type              : Remote Destination Session
Source RSPAN VLAN : 500
Destination Ports : Gi0/0
    Status        : Active
```

---

## 7. Verification Cheatsheet

### SPAN Session Configuration

```
monitor session <N> source interface <intf> [rx | tx | both]
monitor session <N> destination interface <intf>
no monitor session <N>
no monitor session all
```

| Command | Purpose |
|---------|---------|
| `monitor session 1 source interface Gi0/3` | Mirror all traffic from Gi0/3 |
| `monitor session 1 source interface Gi0/3 rx` | Mirror only ingress on Gi0/3 |
| `monitor session 1 destination interface Gi0/0` | Forward copies to Gi0/0 |
| `no monitor session 1` | Remove session 1 entirely |
| `no monitor session all` | Remove all sessions |

> **Exam tip:** A destination port cannot be a trunk port or carry data traffic while active as a SPAN destination. Plan analyzer ports as dedicated monitoring-only interfaces.

### RSPAN Source Session Configuration

```
vlan <id>
 remote-span
!
monitor session <N> source interface <intf>
monitor session <N> destination remote vlan <vlan-id>
```

| Command | Purpose |
|---------|---------|
| `vlan 500` + `remote-span` | Declare VLAN 500 as the RSPAN transport VLAN |
| `monitor session 2 source interface Gi0/3` | Source port on the local switch |
| `monitor session 2 destination remote vlan 500` | Push mirrored frames into RSPAN VLAN |

### RSPAN Destination Session Configuration

```
monitor session <N> source remote vlan <vlan-id>
monitor session <N> destination interface <intf>
```

| Command | Purpose |
|---------|---------|
| `monitor session 1 source remote vlan 500` | Receive mirrored frames from RSPAN VLAN |
| `monitor session 1 destination interface Gi0/0` | Deliver copies to local analyzer port |

> **Exam tip:** The RSPAN VLAN must be defined with `remote-span` on **both** the source and destination switches. Forgetting this on the destination switch is a common misconfiguration.

### Verification Commands

| Command | What to Look For |
|---------|-----------------|
| `show monitor session <N>` | Type, source, destination, Status: Active |
| `show monitor session all` | All active sessions and their types |
| `show monitor session <N> detail` | Full interface names and encapsulation |
| `show vlan id 500` | `Remote SPAN VLAN: Enabled` line |
| `show interfaces trunk` | VLAN 500 in allowed and active columns |
| `show interfaces Gi0/0 status` | Port status (destination ports show monitoring mode) |

### Common SPAN/RSPAN Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| Session shows Inactive | Destination port is shutdown or in EtherChannel |
| RSPAN session on SW2 shows Inactive | VLAN 500 not in trunk's allowed list, or not declared `remote-span` on SW2 |
| Session Active but no traffic seen | Analyzer tool issue, or wrong direction (rx vs tx) configured |
| `remote-span` command rejected | VLAN 500 not created first with `vlan 500` |
| Cannot configure destination on trunk port | Destination port must be an access port or unconfigured routed port |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Task 1: Local SPAN on SW1

<details>
<summary>Click to view SW1 Configuration</summary>

```bash
! SW1
monitor session 1 source interface GigabitEthernet0/3
monitor session 1 destination interface GigabitEthernet0/0
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show monitor session 1
show monitor session 1 detail
```
</details>

---

### Task 2: RSPAN Source Session on SW1

<details>
<summary>Click to view SW1 Configuration</summary>

```bash
! SW1
monitor session 2 source interface GigabitEthernet0/3
monitor session 2 destination remote vlan 500
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show monitor session 2
```
</details>

---

### Task 3: RSPAN Destination Session on SW2

<details>
<summary>Click to view SW2 Configuration</summary>

```bash
! SW2
monitor session 1 source remote vlan 500
monitor session 1 destination interface GigabitEthernet0/0
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show monitor session 1
```
</details>

---

### Task 4: Verify RSPAN VLAN Transport

<details>
<summary>Click to view Verification Commands</summary>

```bash
! On SW1 and SW2
show vlan id 500
show interfaces trunk
```
</details>

---

### Task 5: Remove and Recreate Sessions

<details>
<summary>Click to view SW1 Configuration</summary>

```bash
! SW1 — remove all sessions first
no monitor session all

! Recreate RSPAN source only
monitor session 2 source interface GigabitEthernet0/3
monitor session 2 destination remote vlan 500
```
</details>

<details>
<summary>Click to view SW2 Configuration</summary>

```bash
! SW2 — remove all sessions first
no monitor session all

! Recreate RSPAN destination only
monitor session 1 source remote vlan 500
monitor session 1 destination interface GigabitEthernet0/0
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show monitor session all
```
</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. Inject the fault first, then
diagnose and fix using only show commands.

### Workflow

```bash
python3 setup_lab.py                                   # reset to known-good
python3 scripts/fault-injection/inject_scenario_01.py  # Ticket 1
python3 scripts/fault-injection/apply_solution.py      # restore
```

---

### Ticket 1 — SW1 Local SPAN Shows Active but PC1 Traffic Is Missing

The NOC analyst reports that the analyzer on SW1 Gi0/0 is capturing traffic, but none of it appears to be from PC1. The local SPAN session shows Active.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py`

**Success criteria:** `show monitor session 1` on SW1 shows Gi0/3 as the source port and the analyst confirms PC1 traffic is captured.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Run `show monitor session 1` on SW1 — check the source port listed.
2. Compare with the expected source (Gi0/3 = PC1's access port). If the wrong port is listed, the session is configured with an incorrect source.
3. Verify the physical cabling: PC1 connects to SW1 Gi0/3. R1 connects to SW1 Gi0/2.
4. A source set to Gi0/2 would mirror R1's router traffic, not PC1's end-host traffic.

```
SW1# show monitor session 1
Session 1
---------
Type              : Local Session
Source Ports      :
    Both          : Gi0/2     ! ← wrong port — this is R1's port, not PC1's
Destination Ports : Gi0/0
    Status        : Active
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! SW1 — correct the source port
no monitor session 1
monitor session 1 source interface GigabitEthernet0/3
monitor session 1 destination interface GigabitEthernet0/0
```

Verify:
```bash
show monitor session 1
! Source Ports Both: Gi0/3  — must show correct source
```
</details>

---

### Ticket 2 — RSPAN Traffic Not Reaching SW2

The Wireshark appliance on SW2 Gi0/0 shows no traffic, even though `show monitor session` on both switches reports Active sessions.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py`

**Success criteria:** `show interfaces trunk` on SW1 shows VLAN 500 in the allowed and active VLAN list, and the Wireshark appliance on SW2 receives mirrored frames.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Both SPAN sessions show Active — the session config is correct on both switches. The fault is in the transport layer, not the session configuration.
2. Run `show interfaces trunk` on SW1 — the RSPAN VLAN must be in both the "allowed" and "active" columns for mirrored frames to cross to SW2.
3. If VLAN 500 is missing from the allowed list on SW1's Gi0/1, mirrored frames are blocked at the trunk egress even though SW1 session 2 and SW2 session 1 both show Active.

```
SW1# show interfaces trunk

Port        Vlans allowed on trunk
Gi0/1       10,20,99             ! ← VLAN 500 missing — mirrored frames dropped here

Port        Vlans allowed and active in management domain
Gi0/1       10,20,99             ! ← VLAN 500 absent; SW2 receives nothing

SW2# show monitor session 1
Session 1
---------
Type              : Remote Destination Session
Source RSPAN VLAN : 500
    Status        : Active       ! ← config is correct; SW2 is waiting but no frames arrive
```

> The SW2 session stays Active because its local config is valid — it's configured correctly to receive from VLAN 500. The absence of frames is only visible at the analyzer (Wireshark shows nothing) or by checking the trunk on SW1.
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! SW1 — add VLAN 500 back to the trunk
interface GigabitEthernet0/1
 switchport trunk allowed vlan add 500
```

Verify:
```bash
show interfaces trunk
! VLAN 500 must appear in allowed and active columns

! SW2
show monitor session 1
! Status: Active
```
</details>

---

### Ticket 3 — SW2 RSPAN Session Configured but Shows Inactive

RSPAN was working until a junior engineer edited SW2's configuration. Now `show monitor session 1` on SW2 shows Status: Inactive even though the trunk and VLAN 500 appear correct.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py`

**Success criteria:** SW2 `show monitor session 1` shows Status: Active with source RSPAN VLAN 500 (not any other VLAN).

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Run `show monitor session 1` on SW2 — check which RSPAN VLAN is listed as the source.
2. Run `show vlan id` for the listed VLAN — if it is not declared `remote-span`, the session will be Inactive.
3. Cross-check: SW1 session 2 is sending to VLAN 500. SW2 must receive from VLAN 500. A mismatch (e.g., SW2 configured for VLAN 400) means no matching frames arrive.

```
SW2# show monitor session 1
Session 1
---------
Type              : Remote Destination Session
Source RSPAN VLAN : 400         ! ← wrong VLAN; SW1 sends on VLAN 500
    Status        : Inactive
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! SW2 — correct the RSPAN source VLAN
no monitor session 1
monitor session 1 source remote vlan 500
monitor session 1 destination interface GigabitEthernet0/0
```

Verify:
```bash
show monitor session 1
! Source RSPAN VLAN: 500  and  Status: Active
```
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] SW1 Session 1 (local SPAN) shows Status: Active with Gi0/3 as source and Gi0/0 as destination
- [ ] SW1 Session 2 (RSPAN source) shows Status: Active with Gi0/3 as source and VLAN 500 as remote destination
- [ ] SW2 Session 1 (RSPAN destination) shows Status: Active with remote VLAN 500 as source and Gi0/0 as destination
- [ ] `show vlan id 500` on both switches shows `Remote SPAN VLAN: Enabled`
- [ ] `show interfaces trunk` on both switches shows VLAN 500 in allowed and active columns
- [ ] After teardown (Task 5): only RSPAN sessions remain; `show monitor session all` confirms no local SPAN session

### Troubleshooting

- [ ] Ticket 1 diagnosed and resolved: SW1 local SPAN source corrected to Gi0/3
- [ ] Ticket 2 diagnosed and resolved: VLAN 500 restored to trunk allowed list on SW1
- [ ] Ticket 3 diagnosed and resolved: SW2 RSPAN source VLAN corrected to 500
