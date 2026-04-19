# Lab 05 — Layer 2 Comprehensive Troubleshooting (Capstone II)

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

**Exam Objective:** Blueprint 3.1, 3.1.a, 3.1.b, 3.1.c — Layer 2 Troubleshooting (VLANs & trunking, EtherChannels, Spanning Tree).

This is the Layer 2 **troubleshooting** capstone. The full build from Lab 04 is present on the topology, but with six concurrent faults injected across the three switches. Your job is to drive the network back to full end-to-end reachability using only `show` commands, syslog, and a disciplined top-down methodology. No step-by-step guidance is provided — the scenario section lists six symptom reports, not solutions.

### A repeatable L2 troubleshooting methodology

Every L2 fault the exam asks about sits somewhere in this stack. Walk it top-down:

1. **Physical / Data Link up?** — `show interfaces status`, `show interfaces description`. A port that says `err-disabled`, `notconnect`, or `disabled` has to be resolved before anything above it matters.
2. **Trunk formed?** — `show interfaces trunk`. Is each bundle / trunk port in `trunking` status with matching native VLAN and a sensible allowed list?
3. **Bundle bundled?** — `show etherchannel summary`, `show etherchannel port-channel`. `(SU)` means up-and-bundled; `(SD)`/`(sD)` means members exist but the channel did not form.
4. **VLAN database + access assignment correct?** — `show vlan brief`. If a host port lists the wrong VLAN, end-to-end ping will fail even when every bundle is green.
5. **STP converged?** — `show spanning-tree vlan <id>`, `show spanning-tree inconsistentports`. Any port in `root-inconsistent` or `bpdu-inconsistent` is being blocked by a protection feature.
6. **End-to-end ping** — only worth running once the five layers above are healthy.

| Layer | Question | Go-to command |
|-------|----------|---------------|
| L1 | Is the port alive? | `show interfaces status` |
| L2 (access) | What VLAN is this port in? | `show vlan brief`, `show interfaces <id> switchport` |
| L2 (trunk) | Is the trunk carrying the right VLANs with matching native? | `show interfaces trunk` |
| L2 (bundle) | Did the channel bundle? | `show etherchannel summary` |
| STP | Which bridge is root for this VLAN? Any inconsistent ports? | `show spanning-tree vlan <id>`, `show spanning-tree inconsistentports` |
| L3 | Does the gateway respond? | `ping`, `show ip int brief` on R1 |

### Native VLAN mismatches are silent-but-deadly

A native VLAN mismatch does **not** bring the trunk down. The bundle stays `(SU)`, every member stays `(P)`, and both sides happily forward tagged frames. Only **untagged** traffic (e.g. the native VLAN's control traffic, management SVI reachability, a legacy trunked hypervisor) gets dropped into the wrong VLAN on one side. Two symptoms give it away:

- Periodic syslog: `%CDP-4-NATIVE_VLAN_MISMATCH` — logs the local and remote port numbers.
- `show interfaces trunk` — the **Native vlan** column disagrees between the two ends.

### EtherChannel protocol matrices (the exam's favourite trap)

A bundle forms only when both sides negotiate compatibly. Memorise these:

| LACP (802.3ad) | active | passive |
|----------------|--------|---------|
| active | ✓ (bundle) | ✓ (bundle) |
| passive | ✓ (bundle) | ✗ (no init) |

| PAgP (Cisco) | desirable | auto |
|--------------|-----------|------|
| desirable | ✓ | ✓ |
| auto | ✓ | ✗ |

| Mixed / Static | on | active/passive | desirable/auto |
|----------------|----|----------------|----------------|
| on (static) | ✓ | ✗ | ✗ |

Rule: **mode `on` only bundles with `on`**. Never mix static with LACP or PAgP. And `passive+passive` / `auto+auto` never forms because neither side will initiate.

### STP protection features and how they fail loud

| Feature | Where | Symptom when it fires |
|---------|-------|-----------------------|
| **Root guard** | Distribution-side bundles (SW1 Po1/Po2 and the R1 trunk) | Port placed in `root-inconsistent`. Syslog: `%SPANTREE-2-ROOTGUARD_BLOCK`. Fires when a neighbour sends a superior BPDU (i.e. tries to become root). |
| **BPDU guard** | Edge/access ports (PC-facing) | Port err-disabled. Syslog: `%SPANTREE-2-BLOCK_BPDUGUARD` then `%PM-4-ERR_DISABLE`. Fires the instant *any* BPDU is received. |
| **PortFast** | Same edge/access ports | No fault — but its absence causes 30 s listen/learn delay on host bring-up. |

Root guard blocks — it doesn't err-disable. BPDU guard err-disables — it doesn't block. Read the syslog; the keyword tells you which protection fired.

### Allowed-VLAN pruning cuts reachability without breaking the trunk

`switchport trunk allowed vlan 10,20,30,99` restricts which VLANs traverse the trunk. Remove one and that VLAN's traffic is silently dropped on that link — but the trunk stays `trunking`, CDP is happy, and STP still converges. Always diff the **Vlans allowed on trunk** column of `show interfaces trunk` between both ends.

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| Top-down L2 diagnosis | Walk the L1 → access → trunk → bundle → STP → L3 ladder in a fixed, repeatable order |
| Correlate syslog with `show` output | Turn a `%SPANTREE-2-ROOTGUARD_BLOCK` or `%CDP-4-NATIVE_VLAN_MISMATCH` line into a target interface in under a minute |
| Distinguish silent vs loud faults | Recognise failures that keep bundles up and ports forwarding (native / allowed / access VLAN) from ones that flip state (BPDU guard err-disable, root guard block) |
| Apply the right fix at the right layer | Never fix a symptom above the broken layer — a missing VLAN won't heal by reconfiguring STP |
| Concurrent-fault prioritisation | Decide which of six tickets to clear first so later tickets become observable |

---

## 2. Topology & Scenario

### Network Diagram

```
                             ┌──────────────────┐
                             │       R1         │
                             │ (Router-on-stick)│
                             │  Lo0: 1.1.1.1    │
                             └────────┬─────────┘
                                Gi0/0 │ trunk (dot1q)
                                      │ native VLAN 99, allowed 10,20,30,99
                                      │
                             ┌────────┴─────────┐
                             │      SW1         │
                             │ Root 10/30/99    │
                             │   pri 4096       │
                             └──┬────────────┬──┘
                     Po1 (LACP) │            │ Po2 (PAgP)
                     Gi0/1,Gi0/2│            │ Gi0/3,Gi1/0
                                │            │
                  ┌─────────────┴───┐    ┌───┴───────────┐
                  │      SW2        │    │     SW3       │
                  │ Root VLAN 20    │    │ 2ndary VLAN 20│
                  │  pri 4096       │    │  pri 28672    │
                  └──┬──────────┬───┘    └───┬───────┬───┘
              Gi1/1  │          │Gi0/3       │Gi0/1  │Gi1/1
              access │          │Gi1/0       │Gi0/2  │access
              VLAN10 │          │ Po3 (static, mode on) │ VLAN 20
                     │          └───────┬────┘       │
                     │                  │            │
                 ┌───┴────┐         ┌───┴────┐
                 │  PC1   │         │  PC2   │
                 │.10.10  │         │.20.10  │
                 └────────┘         └────────┘
             192.168.10.0/24     192.168.20.0/24
```

### Scenario

You have taken over the Acme Corp campus L2 fabric from the previous engineer on their last day. Their hand-over notes say "everything worked when I left" — but the morning's ticket queue says otherwise. Six separate incidents have been opened by different stakeholders across the last 24 hours:

- The Sales team's PC1 can no longer reach its gateway.
- Engineering's PC2 has been unreachable since last night's change window.
- NOC dashboards show a root-inconsistent port on SW1 Po1.
- CDP is flooding the syslog with native VLAN mismatch warnings for Po2.
- A core-facing EtherChannel is stuck in `(SD)` — members exist but the bundle is not forming.
- An access port on one of the access switches is showing `disabled` / `err-disabled` in the status output.

The faults are **concurrent**, not sequential — running `setup_lab.py` loads the current broken state onto all four devices so you can triage them all at once. The hand-over notes contain no root-cause information, only the open tickets. Restore the network to full L2 health (all bundles `(SU)`, STP converged without inconsistent ports, PC1 ↔ PC2 end-to-end ping through R1 succeeds, every switch pings 1.1.1.1 via its VLAN 99 SVI) without introducing new issues. The `solutions/` directory holds the known-good reference config; use it only to verify after you've diagnosed each fault yourself.

---

## 3. Hardware & Environment Specifications

### Device Inventory

| Device | Platform | Role | Loopback0 |
|--------|----------|------|-----------|
| SW1 | IOSvL2 | Distribution / root for VLAN 10,30,99 | n/a |
| SW2 | IOSvL2 | Access (PC1) / root for VLAN 20 | n/a |
| SW3 | IOSvL2 | Access (PC2) / secondary root VLAN 20 | n/a |
| R1  | IOSv   | Inter-VLAN router (router-on-a-stick) | 1.1.1.1/32 |
| PC1 | VPC    | End host — 192.168.10.10/24 | — |
| PC2 | VPC    | End host — 192.168.20.10/24 | — |

### Cabling Table

| Link | A end | B end | Type | Purpose |
|------|-------|-------|------|---------|
| L1 | R1 Gi0/0 | SW1 Gi0/0 | Trunk | Router-on-a-stick uplink |
| L2 | SW1 Gi0/1 | SW2 Gi0/1 | Po1 member (LACP) | Distribution ↔ access |
| L3 | SW1 Gi0/2 | SW2 Gi0/2 | Po1 member (LACP) | Distribution ↔ access |
| L4 | SW1 Gi0/3 | SW3 Gi0/3 | Po2 member (PAgP) | Distribution ↔ access |
| L5 | SW1 Gi1/0 | SW3 Gi1/0 | Po2 member (PAgP) | Distribution ↔ access |
| L6 | SW2 Gi0/3 | SW3 Gi0/1 | Po3 member (static) | Access ↔ access |
| L7 | SW2 Gi1/0 | SW3 Gi0/2 | Po3 member (static) | Access ↔ access |
| L8 | PC1 eth0 | SW2 Gi1/1 | Access VLAN 10 | Host |
| L9 | PC2 eth0 | SW3 Gi1/1 | Access VLAN 20 | Host |

### Console Access Table

| Device | Port | Connection Command |
|--------|------|--------------------|
| SW1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| SW2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| SW3 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R1  | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| PC1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| PC2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |

---

## 4. Base Configuration

**Pre-broken build.** `initial-configs/` loads the Lab 04 capstone topology with **six faults pre-injected**. The faults are concurrent and distributed across SW2 and SW3 (SW1 and R1 are clean — their config matches the solutions). Running `setup_lab.py` puts you directly into the broken state so you can begin troubleshooting immediately.

**Pre-loaded (correct) baseline on all devices:**

- Hostnames, `no ip domain-lookup`, comfort lines
- VLAN database (10 SALES, 20 ENGINEERING, 30 MANAGEMENT_HOSTS, 99 NATIVE_MGMT)
- Rapid PVST+ mode and intended root placement
- EtherChannel bundles Po1 (LACP), Po2 (PAgP), Po3 (static)
- Router-on-a-stick sub-interfaces on R1
- Management SVIs on VLAN 99

**Broken (what you must fix):** Six things. The symptom descriptions live in Section 9 — the fault identities (which device, which knob) are in the Diagnosis/Fix spoiler blocks, not in this section.

---

## 5. Lab Challenge: Comprehensive Troubleshooting

> This is a capstone lab. The network is pre-broken.
> Diagnose and resolve 5+ concurrent faults spanning all blueprint bullets.
> No step-by-step guidance is provided — work from symptoms only.

**Target end state (acceptance tests):**

1. `show etherchannel summary` on SW1/SW2/SW3 shows `Po1(SU)`, `Po2(SU)`, `Po3(SU)` where applicable — every member `(P)`.
2. `show spanning-tree inconsistentports` is **empty** on every switch.
3. `show spanning-tree vlan 10` → "This bridge is the root" on SW1 (priority 4096).
4. `show interfaces trunk` — native VLAN = 99 on every trunk and every end; allowed list `10,20,30,99` on every trunk and every end.
5. `show interfaces status` — PC-facing ports (SW2 Gi1/1, SW3 Gi1/1) are `connected` with the correct access VLAN (10 and 20 respectively).
6. `show vlan brief` — SW2 Gi1/1 shows `VLAN 10`; SW3 Gi1/1 shows `VLAN 20`.
7. `PC1 > ping 192.168.20.10` — succeeds (ttl=63 after routing through R1).
8. Every switch can `ping 1.1.1.1 source Vlan99` successfully.
9. Syslog: no more `%CDP-4-NATIVE_VLAN_MISMATCH`, `%SPANTREE-2-ROOTGUARD_BLOCK`, `%PM-4-ERR_DISABLE bpduguard`, or `%LINK-3-UPDOWN` churn.

You are scored on the end state, not the path — but a disciplined top-down walk (L1 → access → trunk → bundle → STP → L3) will reach it faster than random guessing.

---

## 6. Verification & Analysis

After each fix, re-run the relevant verification block. Every highlighted line must match before the ticket is closed.

### L1 / interface status

```
SW3# show interfaces status
Port     Name               Status       Vlan       Duplex  Speed Type
Gi1/1    ACCESS_PC2_VLAN20  connected    20         a-full  auto  RJ45 Server     ! ← must be "connected / 20", not "disabled" or "err-disabled"
```

```
SW2# show vlan brief | include Gi1/1
10   SALES                            active    Gi1/1                            ! ← Gi1/1 must be in VLAN 10, not 30
```

### Trunk parameters — native and allowed list agree end-to-end

```
SW1# show interfaces trunk
Port         Mode    Encapsulation  Status      Native vlan
Gi0/0        on      802.1q         trunking    99                               ! ← native 99 (R1 trunk)
Po1          on      802.1q         trunking    99                               ! ← SW1↔SW2
Po2          on      802.1q         trunking    99                               ! ← SW1↔SW3 — must match SW3 side

Port         Vlans allowed on trunk
Po1          10,20,30,99                                                         ! ← full list, not 20,30,99
```

```
SW3# show interfaces trunk
Port         Mode    Encapsulation  Status      Native vlan
Po2          on      802.1q         trunking    99                               ! ← must be 99 to match SW1
```

### EtherChannel — all three bundles up

```
SW1# show etherchannel summary
Group  Port-channel  Protocol    Ports
------+-------------+-----------+-----------------------------
1      Po1(SU)         LACP      Gi0/1(P)   Gi0/2(P)            ! ← SW1↔SW2 LACP
2      Po2(SU)         PAgP      Gi0/3(P)   Gi1/0(P)            ! ← SW1↔SW3 PAgP — NOT (SD)
```

```
SW3# show etherchannel port-channel | include Protocol
                Protocol:   PAgP                                                 ! ← SW3 side must also be PAgP, not LACP
```

### Spanning tree — no inconsistent ports anywhere

```
SW1# show spanning-tree inconsistentports
Name        Interface               Inconsistency
-------- -------------------------- ------------------
                                                                                 ! ← table must be EMPTY on every switch
```

```
SW1# show spanning-tree vlan 10
VLAN0010
  Spanning tree enabled protocol rstp
  Root ID    Priority    4106
             Address     <SW1 MAC>
             This bridge is the root                                             ! ← SW1, not SW2 (SW2 must not win VLAN 10)
  Bridge ID  Priority    4106  (priority 4096 sys-id-ext 10)                     ! ← 4096, not 0
```

### End-to-end reachability — the only test that integrates every fix

```
PC1> ping 192.168.20.10
84 bytes from 192.168.20.10 icmp_seq=1 ttl=63 time=4.2 ms                        ! ← ttl=63 — crossed R1 once
```

```
SW2# ping 1.1.1.1 source vlan 99
!!!!!                                                                            ! ← 5/5 from management SVI
```

### Syslog — noise must stop

```
SW1# show logging | include NATIVE_VLAN|ROOTGUARD|BPDUGUARD|ERR_DISABLE
                                                                                 ! ← empty (or only historical messages) after fixes
```

---

## 7. Verification Cheatsheet

### Top-Down Diagnostic Walk

```
show interfaces status                 ! L1 — any port not "connected"?
show interfaces trunk                  ! L2-trunk — native VLAN, allowed list
show etherchannel summary              ! L2-bundle — (SU) on every Po
show etherchannel port-channel         ! L2-bundle — protocol agreement
show vlan brief                        ! L2-access — host port VLAN assignment
show spanning-tree vlan <id>           ! STP — root bridge, port roles
show spanning-tree inconsistentports   ! STP — root/bpdu-inconsistent ports
show logging | include <pattern>       ! Correlate syslog with the symptom
ping <peer>                            ! L3 — the final integration test
```

| Command | What to Look For |
|---------|-----------------|
| `show interfaces status` | Status column: `connected`, `notconnect`, `disabled`, `err-disabled` |
| `show interfaces <id> status err-disabled` | Err-disabled cause (e.g. `bpduguard`) |
| `show interfaces trunk` | Mode `on`, status `trunking`, native VLAN matches peer, allowed list matches peer |
| `show etherchannel summary` | `(SU)` = bundled + layer-2; `(SD)` = down; member `(P)` = bundled, `(s)` = suspended |
| `show etherchannel port-channel` | Protocol column — LACP / PAgP / `-` (static). Must match other side. |
| `show vlan brief` | Confirms access port assignment (which VLAN holds which Gi) |
| `show spanning-tree vlan N` | "This bridge is the root" on intended root; priority lines |
| `show spanning-tree inconsistentports` | **Must be empty**. Any entry = a protection feature fired |
| `show logging` (filtered) | Historical trail of which fault fired when |
| `show errdisable recovery` | Which causes auto-recover (default is mostly "disabled") |

> **Exam tip:** The three "silent" L2 faults (native VLAN mismatch, allowed-list filtering, wrong access VLAN) never bring a port down. You only catch them by diffing `show interfaces trunk` / `show vlan brief` output between the two ends. Always check both sides of a link.

### Syslog Patterns to Pattern-Match

```
%CDP-4-NATIVE_VLAN_MISMATCH     ! Trunk native VLAN disagreement (silent data-plane break)
%SPANTREE-2-ROOTGUARD_BLOCK     ! Root guard fired — a neighbour claimed root
%SPANTREE-2-BLOCK_BPDUGUARD     ! BPDU arrived on an edge port
%PM-4-ERR_DISABLE               ! Port moved to err-disabled (reason follows)
%EC-5-CANNOT_BUNDLE2            ! EtherChannel member rejected (config mismatch)
%LINEPROTO-5-UPDOWN             ! Port protocol state change
```

| Syslog keyword | Likely layer | First command to run |
|----------------|-------------|----------------------|
| `NATIVE_VLAN_MISMATCH` | Trunk | `show interfaces trunk` (compare Native vlan both ends) |
| `ROOTGUARD_BLOCK` | STP | `show spanning-tree inconsistentports` + `show spanning-tree vlan <N>` |
| `BPDUGUARD` + `ERR_DISABLE` | Edge port | `show interfaces status err-disabled` |
| `CANNOT_BUNDLE` | EtherChannel | `show etherchannel port-channel`, compare protocol/mode |
| Link flap | L1 | `show interfaces <id>` — counters, duplex, speed |

> **Exam tip:** Syslog is an answer key. If CLI memory is thin, `show logging | include <pattern>` almost always tells you the affected interface and reason code. Always check syslog *before* exhaustively walking every interface.

### EtherChannel Mode Compatibility

```
LACP:   active + active    bundles
        active + passive   bundles
        passive + passive  ✗ does not bundle

PAgP:   desirable + desirable  bundles
        desirable + auto       bundles
        auto + auto            ✗ does not bundle

Static: on + on            bundles
        on + anything else  ✗ does not bundle
```

| Mode Mix | Outcome |
|----------|---------|
| `active` + `passive` | LACP bundle |
| `desirable` + `auto` | PAgP bundle |
| `on` + `on` | Static bundle |
| `active` + `desirable` | ✗ protocol conflict |
| `on` + `active` | ✗ static vs dynamic |
| `passive` + `passive` or `auto` + `auto` | ✗ neither side initiates |

> **Exam tip:** When a bundle is `(SD)`, run `show etherchannel port-channel` on both ends and compare the **Protocol** column first. Mismatched protocol is a far more common exam fault than mismatched L2 parameters.

### STP Protection Matrix

| Feature | Trigger | Result | Recovery |
|---------|---------|--------|----------|
| Root guard | Superior BPDU on a designated port | Port = `root-inconsistent` | Auto-recovers when superior BPDU stops |
| BPDU guard | *Any* BPDU on a PortFast port | Port = `err-disabled` | Manual `shutdown`/`no shutdown` (or `errdisable recovery cause bpduguard`) |
| BPDU filter | BPDU on a PortFast port | Port stops sending/receiving BPDUs (silently becomes normal) | N/A |

### Per-VLAN STP Priority Reference

| Priority | Meaning |
|----------|---------|
| 0 | Always wins (dangerous — no fallback) |
| 4096 | Primary root |
| 28672 | Secondary root (beats default 32768) |
| 32768 | Default — do not leave in production |

### Common L2 Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| Trunk up, but one VLAN's traffic disappears over a specific link | Allowed VLAN list pruned on one end |
| Bundle `(SD)` with members `(s)` | Protocol or mode mismatch (LACP vs PAgP, or passive/passive) |
| `ROOTGUARD_BLOCK` syslog on a distribution port | A downstream switch's priority was lowered below the intended root's |
| Access port stuck `err-disabled / bpduguard` | Rogue switch/hub plugged in, *or* port manually re-shut after recovery timer expired |
| `CDP-4-NATIVE_VLAN_MISMATCH` every 60 s | Native VLAN differs between the two trunk ends |
| PC cannot reach gateway but trunk is healthy | Access port assigned to the wrong VLAN |
| Intra-VLAN ping works, inter-VLAN ping fails | R1 sub-interface missing or wrong `encapsulation dot1Q` tag |

---

## 8. Solutions (Spoiler Alert!)

> Try to diagnose each ticket using only `show` commands first. The solution for each fault lives in the corresponding ticket in Section 9; the per-device known-good configs live in `solutions/SW1.cfg`, `solutions/SW2.cfg`, `solutions/SW3.cfg`, `solutions/R1.cfg`.

### Recovery strategy — fix in this order

Some faults mask others. Work them in the order that maximises observability:

1. **First — the trunk-level faults** (native VLAN mismatch, allowed-list pruning). Their absence lets the bundle carry every VLAN so later layer symptoms become visible.
2. **Next — the bundle-level fault** (EtherChannel mode mismatch). Without a formed bundle, downstream STP events on that path are invisible.
3. **Then — the STP protection fires** (root guard on SW1's Po1 caused by SW2's priority = 0). Fixing the priority clears the inconsistent port automatically.
4. **Next — the access-VLAN misassignment** on the PC1 port.
5. **Last — the shutdown on PC2's access port**. Bouncing that port must come after the adjacent bundle is healthy, otherwise the recovery flap muddies the syslog trail.

### Consolidated fix summary

<details>
<summary>Click to view SW2 corrections (3 faults)</summary>

```bash
! SW2
! Fix F2 — restore VLAN 10 to allowed list on Po1 and member ports
interface range GigabitEthernet0/1 - 2
 switchport trunk allowed vlan 10,20,30,99
interface Port-channel1
 switchport trunk allowed vlan 10,20,30,99
!
! Fix F4 — restore SW2's VLAN 10 priority (secondary, not primary)
no spanning-tree vlan 10 priority 0
spanning-tree vlan 10,30,99 priority 28672
!
! Fix F6 — PC1 access port back to VLAN 10
interface GigabitEthernet1/1
 switchport access vlan 10
```
</details>

<details>
<summary>Click to view SW3 corrections (3 faults)</summary>

```bash
! SW3
! Fix F1 — restore native VLAN 99 on Po2 members and the bundle
interface range GigabitEthernet0/3 , GigabitEthernet1/0
 switchport trunk native vlan 99
interface Port-channel2
 switchport trunk native vlan 99
!
! Fix F3 — restore PAgP auto mode on Gi0/3 (to match SW1 Po2 = desirable)
interface GigabitEthernet0/3
 no channel-group 2 mode passive
 channel-group 2 mode auto
!
! Fix F5 — recover PC2 access port (simulated bpduguard err-disable recovery)
interface GigabitEthernet1/1
 no shutdown
```
</details>

> Full per-device solutions also live in `solutions/SW1.cfg`, `SW2.cfg`, `SW3.cfg`, `R1.cfg`.

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. `setup_lab.py` loads all six faults at once so you can work the scenario realistically. The individual inject scripts rebuild one fault at a time for focused repetition after the first end-to-end pass.

### Workflow

```bash
python3 setup_lab.py                                   # load the full pre-broken state (all 6 faults)
python3 scripts/fault-injection/apply_solution.py      # restore known-good (when finished or stuck)

# Focused single-fault practice (after solving the full scenario once):
python3 scripts/fault-injection/inject_scenario_01.py  # Ticket 1 only
python3 scripts/fault-injection/inject_scenario_02.py  # Ticket 2 only
python3 scripts/fault-injection/inject_scenario_03.py  # Ticket 3 only
python3 scripts/fault-injection/inject_scenario_04.py  # Ticket 4 only
python3 scripts/fault-injection/inject_scenario_05.py  # Ticket 5 only
python3 scripts/fault-injection/inject_scenario_06.py  # Ticket 6 only
```

---

### Ticket 1 — CDP Floods the Syslog with Native VLAN Warnings on Po2

The NOC dashboard is lit up with a periodic `%CDP-4-NATIVE_VLAN_MISMATCH` message naming members of Po2. The bundle still shows `(SU)`, every member is `(P)`, and data-plane reachability across Po2 looks partially fine — but management traffic over VLAN 99 is intermittently unreachable on that path. Neither SW1 nor SW3 has been reconfigured today according to change control, but someone was investigating Po2 last night.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py`

**Success criteria:** `show interfaces trunk` shows native VLAN 99 on **both** ends of Po2 (SW1 and SW3) for the bundle and every member. `%CDP-4-NATIVE_VLAN_MISMATCH` messages stop firing.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `show logging | include NATIVE_VLAN` — note the interface names logged (local and remote).
2. `show interfaces trunk` on SW1 — Po2 **Native vlan** column.
3. `show interfaces trunk` on SW3 — Po2 **Native vlan** column.
4. Diff the two. The value that is not 99 is the one to fix.
5. `show running-config interface Port-channel2` and its members on the broken side — confirm the offending `switchport trunk native vlan 1` line.
</details>

<details>
<summary>Click to view Fix</summary>

The fault is on **SW3**: Po2 and its members (Gi0/3, Gi1/0) have `switchport trunk native vlan 1` instead of 99.

```bash
! SW3
interface range GigabitEthernet0/3 , GigabitEthernet1/0
 switchport trunk native vlan 99
interface Port-channel2
 switchport trunk native vlan 99
```

Verify with `show interfaces trunk` on both ends — native VLAN 99 everywhere on Po2. CDP warnings stop within 60 s (one CDP cycle).
</details>

---

### Ticket 2 — Sales Team (VLAN 10) Cannot Reach R1 Across Po1

Sales users report they can see each other on PC1's segment but cannot reach their VLAN 10 gateway on R1. Traffic for VLANs 20, 30, and the native VLAN 99 flows correctly across Po1. `show etherchannel summary` reports Po1 as healthy `(SU)` on both SW1 and SW2, and the trunk is `trunking` on both ends.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py`

**Success criteria:** `show interfaces trunk` on both ends of Po1 shows **Vlans allowed on trunk** = `10,20,30,99`. PC1 pings `192.168.10.1` (VLAN 10 gateway on R1) and `192.168.20.10` (PC2) successfully.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. On PC1: `ping 192.168.10.1` — fails. Establish whether the problem is VLAN-10-specific.
2. On SW2: `show vlan brief` — confirm Gi1/1 membership and VLAN 10's presence in the database (both should look correct).
3. `show interfaces trunk` on SW1 — Po1 **Vlans allowed on trunk** column.
4. `show interfaces trunk` on SW2 — Po1 **Vlans allowed on trunk** column.
5. Diff the two. Whichever side is missing VLAN 10 is the broken end.
</details>

<details>
<summary>Click to view Fix</summary>

The fault is on **SW2**: Po1 and its members (Gi0/1, Gi0/2) have `switchport trunk allowed vlan 20,30,99` — VLAN 10 has been pruned.

```bash
! SW2
interface range GigabitEthernet0/1 - 2
 switchport trunk allowed vlan 10,20,30,99
interface Port-channel1
 switchport trunk allowed vlan 10,20,30,99
```

Verify with `show interfaces trunk` on both ends and re-ping from PC1 to 192.168.10.1.
</details>

---

### Ticket 3 — Po2 Will Not Form (Stuck in SD)

Last night's change window included an "EtherChannel refresh" on SW3. This morning Po2 between SW1 and SW3 is stuck — `show etherchannel summary` on SW1 reports `Po2(SD)` with both members `(s)`, and reachability toward PC2 is relying entirely on Po1→Po3 which is slower. Every other bundle (Po1 and Po3) is healthy.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py`

**Success criteria:** `show etherchannel summary` on SW1 and SW3 shows `Po2(SU)` with both members `(P)`. `show etherchannel port-channel` reports Protocol `PAgP` on both ends.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `show etherchannel summary` on SW1 and SW3 — confirm `Po2(SD)` on both sides.
2. `show etherchannel port-channel | section Port-channel2` on SW1 — note Protocol (should be PAgP) and each member's mode.
3. `show etherchannel port-channel | section Port-channel2` on SW3 — note Protocol and each member's mode.
4. Recall the mode matrix: Po2 is PAgP (SW1 desirable + SW3 auto). If one end is reporting LACP, a member was re-configured with an LACP mode (`active` or `passive`). LACP and PAgP cannot bundle together.
5. Check `show running-config interface GigabitEthernet0/3` on SW3 — look for the offending `channel-group 2 mode passive` line.
</details>

<details>
<summary>Click to view Fix</summary>

The fault is on **SW3 Gi0/3**: `channel-group 2 mode passive` (LACP) was applied instead of `auto` (PAgP). The other SW3 member (Gi1/0) is still `auto`, so one member tries LACP and one tries PAgP — the bundle cannot form and both members go suspended.

```bash
! SW3
interface GigabitEthernet0/3
 no channel-group 2 mode passive
 channel-group 2 mode auto
```

Wait ~15 seconds for PAgP to converge and re-verify `Po2(SU)` with both members `(P)`.
</details>

---

### Ticket 4 — SW1 Reports a Root-Inconsistent Port on Po2

`show spanning-tree inconsistentports` on SW1 shows `Po2` in `Root Inconsistent` state, and `show logging` has a recent `%SPANTREE-2-ROOTGUARD_BLOCK` message referencing Po2 / VLAN 10. VLAN 10 traffic between SW1 and SW3 is completely blocked on Po2.

**Inject:** `python3 scripts/fault-injection/inject_scenario_04.py`

**Success criteria:** `show spanning-tree inconsistentports` is empty on SW1. `show spanning-tree vlan 10` on SW1 shows "This bridge is the root" with priority 4096. `show spanning-tree vlan 10` on SW3 shows SW1 as root (not SW3 itself).

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `show spanning-tree inconsistentports` on SW1 — confirm Po2 / VLAN 10 in Root Inconsistent.
2. `show logging | include ROOTGUARD` — confirms the protection fired and names the VLAN.
3. `show spanning-tree vlan 10` on SW3 — look at the Bridge ID priority line. If it reads `priority 10 (priority 0 sys-id-ext 10)`, SW3 has been configured to claim root for VLAN 10 (priority 0 always wins).
4. Compare: `show running-config | include spanning-tree vlan` on SW3 — confirm the offending `spanning-tree vlan 10 priority 0` line.
5. Recall the design: SW1 = root for VLANs 10/30/99 (priority 4096). SW3 has no legitimate root claim — root guard on SW1 Po2 protects this boundary.
</details>

<details>
<summary>Click to view Fix</summary>

The fault is on **SW3**: `spanning-tree vlan 10 priority 0` was applied, making SW3 the bridge with priority 0 (sys-id-ext 10) = bridge ID 10. SW1 (priority 4096) sees the superior BPDU on Po2 and Root guard fires.

```bash
! SW3
no spanning-tree vlan 10 priority 0
```

This removes SW3's spurious root claim. Root guard automatically clears the inconsistent state within seconds once SW3 stops sending superior BPDUs for VLAN 10.

Verify with `show spanning-tree inconsistentports` (must be empty) and `show spanning-tree vlan 10` on both switches — SW1 is "this bridge is the root".
</details>

---

### Ticket 5 — PC2's Access Port is Disabled on SW3

A weekend tech was "tidying cables" on SW3 and the Engineering user who sits behind PC2 reports they lost connectivity afterward. `show interfaces status` on SW3 shows `Gi1/1` (PC2's port) as `disabled`. No `err-disabled` cause is listed; the interface is administratively down.

**Inject:** `python3 scripts/fault-injection/inject_scenario_05.py`

**Success criteria:** SW3 `Gi1/1` is `connected` on VLAN 20. PC2 pings `192.168.20.1` (its gateway). `show interfaces status` shows the port in `connected` state.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `show interfaces status | include Gi1/1` on SW3 — confirm `disabled`.
2. `show interfaces GigabitEthernet1/1` on SW3 — look for `administratively down, line protocol is down`.
3. `show errdisable recovery` — confirm no err-disable cause is active (this is a pure shutdown, not a bpduguard event; the workbook scenario describes it as a "simulated BPDU-guard err-disable" but the current state is just `shutdown`).
4. `show running-config interface GigabitEthernet1/1` on SW3 — confirm the `shutdown` line and that PortFast + BPDU guard are still in place.
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! SW3
interface GigabitEthernet1/1
 no shutdown
```

Verify `show interfaces status` → `connected / 20`. BPDU guard stays enabled — it is the correct long-term defence.
</details>

---

### Ticket 6 — PC1 Cannot Reach Its Default Gateway

PC1 reports it cannot reach `192.168.10.1`. Its IP is `192.168.10.10/24` and the NIC is up. VLAN 10 trunking across Po1 is now healthy (after Ticket 2's fix) and the VLAN 10 STP topology is stable (after Ticket 4's fix). The problem is local to SW2's host-facing port.

**Inject:** `python3 scripts/fault-injection/inject_scenario_06.py`

**Success criteria:** `show vlan brief` on SW2 shows `Gi1/1` in VLAN 10. PC1 pings `192.168.10.1` and `192.168.20.10` (PC2) successfully.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. On PC1: `show ip` — confirm 192.168.10.10/24, gateway 192.168.10.1.
2. `show interfaces GigabitEthernet1/1` on SW2 — must be `connected`.
3. `show interfaces GigabitEthernet1/1 switchport` on SW2 — look at **Access Mode VLAN**. Is it `10 (SALES)` or something else?
4. `show vlan brief` on SW2 — what VLAN does Gi1/1 currently belong to?
5. Cross-check the design: the cabling table shows PC1 in VLAN 10.
</details>

<details>
<summary>Click to view Fix</summary>

The fault is on **SW2**: Gi1/1 is `switchport access vlan 30` instead of `vlan 10`, so PC1's frames end up on VLAN 30 (Management-Hosts).

```bash
! SW2
interface GigabitEthernet1/1
 switchport access vlan 10
```

Verify with `show vlan brief` on SW2 (Gi1/1 should now appear under VLAN 10) and re-ping from PC1 to 192.168.10.1 and 192.168.20.10.
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] `show interfaces trunk` on every switch: native VLAN 99 on every trunk and member
- [ ] `show interfaces trunk` on every switch: allowed list `10,20,30,99` on every trunk
- [ ] `show etherchannel summary` on SW1/SW2/SW3: `Po1(SU)`, `Po2(SU)`, `Po3(SU)` — every member `(P)`
- [ ] `show etherchannel port-channel`: Po1 = LACP both ends, Po2 = PAgP both ends, Po3 = static both ends
- [ ] `show spanning-tree inconsistentports`: empty on every switch
- [ ] `show spanning-tree vlan 10` on SW1: "This bridge is the root" — priority 4106 (4096 + sys-id-ext 10)
- [ ] `show spanning-tree vlan 20` on SW2: "This bridge is the root"
- [ ] `show interfaces status` on SW2: Gi1/1 `connected`, VLAN 10
- [ ] `show interfaces status` on SW3: Gi1/1 `connected`, VLAN 20
- [ ] PC1 `ping 192.168.10.1` succeeds
- [ ] PC1 `ping 192.168.20.10` succeeds (ttl=63)
- [ ] PC2 `ping 192.168.20.1` succeeds
- [ ] Every switch pings `1.1.1.1` from its VLAN 99 SVI
- [ ] `show logging | include NATIVE_VLAN|ROOTGUARD|BPDUGUARD|ERR_DISABLE` shows no new events in the last minute

### Troubleshooting

- [ ] Ticket 1 — Native VLAN mismatch on Po2 resolved; CDP warnings stop
- [ ] Ticket 2 — Allowed VLAN list on Po1 restored; VLAN 10 traffic flows
- [ ] Ticket 3 — Po2 member channel-group mode corrected; bundle forms
- [ ] Ticket 4 — SW3 VLAN 10 priority 0 removed; SW1 Po2 root guard clears
- [ ] Ticket 5 — SW3 Gi1/1 no-shut; PC2 reconnects
- [ ] Ticket 6 — SW2 Gi1/1 access VLAN corrected; PC1 reaches its gateway

---
