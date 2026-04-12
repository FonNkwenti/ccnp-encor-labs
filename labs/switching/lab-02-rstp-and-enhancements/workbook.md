# Lab 02 — Rapid STP and STP Enhancements

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

**Exam Objective:** Blueprint 3.1.c — Layer 2 Spanning Tree (RSTP, STP enhancements)

This lab builds on the EtherChannel backbone from Lab 01 and layers in per-VLAN
root-bridge engineering, edge-port protection, and fast convergence. Rapid
PVST+ is the default mode students will see on nearly every Cisco production
network, so getting fluent with its port roles, states, and safeguards is
essential for both the 350-401 exam and real operations.

### Rapid PVST+ vs legacy PVST+

Rapid PVST+ runs an independent instance of 802.1w RSTP per VLAN. The key
improvements over legacy 802.1D / PVST+:

| Aspect | PVST+ (802.1D) | Rapid PVST+ (802.1w) |
|--------|----------------|----------------------|
| Convergence | 30–50 s after link failure | 1–2 s with edge/P2P link types |
| Port states | Listening, Learning, Forwarding, Blocking, Disabled | Discarding, Learning, Forwarding |
| Port roles | Root, Designated, Non-designated | Root, Designated, Alternate, Backup |
| Proposal/Agreement | No — timers only | Yes — handshake-driven transition |
| BPDU version | 0 | 2 |

Rapid PVST+ is the default recommended mode on modern Catalyst platforms.
Enable it explicitly so the running-config reflects intent:

```
spanning-tree mode rapid-pvst
```

### Root bridge election and per-VLAN priority

Each VLAN elects its own root independently. The switch with the **lowest
Bridge ID** (priority + MAC) wins. Priority is the first tiebreaker and
always moves in 4096-step increments (the low 12 bits carry the VLAN's
Extended System ID). Typical deterministic placement:

```
SW1(config)# spanning-tree vlan 10,30,99 priority 4096   ! SW1 is root for these
SW2(config)# spanning-tree vlan 20       priority 4096   ! SW2 is root for VLAN 20
```

Verify per VLAN — never trust a single `show`:

```
show spanning-tree vlan 10
show spanning-tree root
```

### Port roles, states, and timers

After convergence each port in each VLAN instance has exactly one role:

| Role | Meaning |
|------|---------|
| Root | Best path toward the root bridge (one per non-root switch, per VLAN) |
| Designated | Best port for a segment — forwards BPDUs toward leaves |
| Alternate | Backup path to the root — blocked, promotes to Root on failure |
| Backup | Redundant designated port on the same segment (rare, hub topology) |

EtherChannel collapses multiple physical links into one logical STP port, so
bundled links elect one root/designated role for the whole bundle — which is
exactly why Lab 01 bundled the backbone first.

### STP enhancements for edge ports and root protection

| Enhancement | Where | Purpose |
|-------------|-------|---------|
| **PortFast** | Access ports (to PCs/servers) | Skip listening/learning; forward immediately |
| **BPDU guard** | Same edge ports | Err-disable the port if a BPDU is received (rogue switch protection) |
| **Root guard** | Designated ports facing downstream switches | Block port into `root-inconsistent` if a superior BPDU arrives — protects the intended root |
| **Loop guard** | Non-designated ports on P2P links | Protect against unidirectional-link-induced loops |

Root guard and BPDU guard are **opposites in direction**:
- BPDU guard assumes the port should **never see a BPDU**.
- Root guard assumes the port **must see BPDUs**, but only from an inferior (non-root) bridge.

### Convergence in Rapid PVST+

Rapid PVST+ converges in ~1–2 seconds on direct link failures, provided:
- The link type is **point-to-point** (full-duplex trunks qualify automatically)
- Edge ports are marked (PortFast) so they don't trigger topology changes

Observable signals:
- `show spanning-tree vlan X detail` shows the **topology change count** and the
  **time since last change**
- After a flap, the affected VLAN reconverges without triggering MAC-table
  flushes across the whole topology (edge flaps don't generate TC BPDUs when
  PortFast is set)

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| Configure Rapid PVST+ | Explicitly set STP mode and verify per-VLAN behaviour |
| Engineer root placement | Assign primary/secondary root bridges per VLAN with deterministic priority values |
| Identify port roles | Read `show spanning-tree` output to map Root / Designated / Alternate roles to the physical topology |
| Protect edge ports | Apply PortFast + BPDU guard on access ports facing PCs |
| Protect root placement | Apply root guard on designated ports to prevent unauthorised root changes |
| Troubleshoot STP faults | Diagnose root-inconsistent ports, mode mismatches, and suboptimal path costs |

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
                             │ Root for 10/30/99│
                             │   priority 4096  │
                             └──┬────────────┬──┘
                     Po1 (LACP) │            │ Po2 (PAgP)
                     Gi0/1,Gi0/2│            │ Gi0/3,Gi1/0
                                │            │
                  ┌─────────────┴───┐    ┌───┴───────────┐
                  │      SW2        │    │     SW3       │
                  │ Root for VLAN 20│    │  (default)    │
                  │  priority 4096  │    │  priority     │
                  │                 │    │    32768      │
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

Acme Corp's campus Layer 2 core is now fully bundled (Lab 01) and stable.
The network architect has mandated **deterministic Spanning Tree behaviour**
before the environment goes into production:

- VLANs 10 (Sales), 30 (Management Hosts), and 99 (Native/Mgmt) must have
  their root bridge on **SW1** — this keeps north-south traffic toward the R1
  router-on-a-stick uplink on the optimal path.
- VLAN 20 (Engineering) must root at **SW2** — Engineering's user base is
  heaviest on that side of the topology.
- PC-facing access ports must converge instantly on boot (PortFast) and
  reject any rogue switch that tries to plug in (BPDU guard).
- SW1's role as the VLAN 10/30/99 root must be **protected** against a
  misconfigured neighbour claiming a lower priority.

You will configure Rapid PVST+, tune per-VLAN root priorities, apply the
STP enhancements, and verify port roles per VLAN. Section 9 drops three
troubleshooting tickets on the finished network.

---

## 3. Hardware & Environment Specifications

### Device Inventory

| Device | Platform | Role | Loopback0 |
|--------|----------|------|-----------|
| SW1 | IOSvL2 | Primary root for VLAN 10/30/99 | n/a |
| SW2 | IOSvL2 | Primary root for VLAN 20; PC1 access | n/a |
| SW3 | IOSvL2 | Default priority; PC2 access | n/a |
| R1  | IOSv   | Inter-VLAN router (router-on-a-stick) | 1.1.1.1/32 |
| PC1 | VPC    | End host (192.168.10.0/24) | — |
| PC2 | VPC    | End host (192.168.20.0/24) | — |

### Cabling Table

| Link | A end | B end | Type | Purpose |
|------|-------|-------|------|---------|
| L1 | R1 Gi0/0 | SW1 Gi0/0 | Trunk | R1 router-on-a-stick |
| Po1 (L2+L3) | SW1 Gi0/1, Gi0/2 | SW2 Gi0/1, Gi0/2 | LACP bundle | Distribution uplink |
| Po2 (L4+L5) | SW1 Gi0/3, Gi1/0 | SW3 Gi0/3, Gi1/0 | PAgP bundle | Distribution uplink |
| Po3 (L6+L7) | SW2 Gi0/3, Gi1/0 | SW3 Gi0/1, Gi0/2 | Static bundle | SW2<->SW3 backbone |
| L8 | PC1 e0 | SW2 Gi1/1 | Access | PC1 in VLAN 10 |
| L9 | PC2 e0 | SW3 Gi1/1 | Access | PC2 in VLAN 20 |

### Console Access Table

| Device | Port | Connection Command |
|--------|------|--------------------|
| SW1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| SW2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| SW3 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R1  | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |

`setup_lab.py` discovers these ports automatically via the EVE-NG REST API.

### IP Addressing

| VLAN | Subnet | Gateway (R1 sub-int) |
|------|--------|----------------------|
| 10 (SALES) | 192.168.10.0/24 | 192.168.10.1 |
| 20 (ENGINEERING) | 192.168.20.0/24 | 192.168.20.1 |
| 30 (MANAGEMENT_HOSTS) | 192.168.30.0/24 | 192.168.30.1 |
| 99 (NATIVE_MGMT) | 192.168.99.0/24 | 192.168.99.1 (SW1 SVI) |

---

## 4. Base Configuration

### What IS pre-loaded (initial-configs/)

Copied from Lab 01 solutions:

- Hostnames, VLAN database (10/20/30/99), `port-channel load-balance src-dst-mac`
- Po1 LACP (SW1 active <-> SW2 passive), Po2 PAgP (SW1 desirable <-> SW3 auto),
  Po3 static (mode on, both sides)
- All trunk config on port-channel and member interfaces (native VLAN 99,
  allowed 10,20,30,99, nonegotiate)
- R1 router-on-a-stick sub-interfaces + ACLs (unchanged)
- PC1 / PC2 `.vpc` files auto-load on EVE-NG boot

### What is NOT pre-loaded (you will configure)

- Rapid PVST+ STP mode
- Per-VLAN root-bridge priority
- Root guard on SW1's designated port-channels
- PortFast + BPDU guard on PC-facing access ports

### Loading Initial Configs

```bash
python3 setup_lab.py --host <eve-ng-ip>
```

### PC Configuration

PC1 and PC2 read their `.vpc` files from EVE-NG on boot — no manual typing
required. Verify on each VPC console:

```
PC1> show ip
NAME        : PC1
IP/MASK     : 192.168.10.10/24
GATEWAY     : 192.168.10.1
```

---

## 5. Lab Challenge: Core Implementation

### Task 1: Enable Rapid PVST+ on all three switches

- On SW1, SW2, and SW3, explicitly set the STP mode to Rapid PVST+.
- Confirm no switch is running legacy PVST+ or MST by accident.

**Verification:** `show spanning-tree summary` — the first line must read
`Switch is in rapid-pvst mode` on every switch.

---

### Task 2: Engineer root placement per VLAN

- Configure **SW1** as the primary root for VLANs 10, 30, and 99 using
  priority value 4096.
- Configure **SW2** as the primary root for VLAN 20 using priority value 4096.
- Leave SW3 at its default priority (32768).

**Verification:** `show spanning-tree root` on each switch — the "Root ID"
column must show SW1's MAC for VLANs 10/30/99 and SW2's MAC for VLAN 20.
`show spanning-tree vlan 10` on SW1 must read
`This bridge is the root` at the top.

---

### Task 3: Identify port roles across the triangle

- For each VLAN, walk the topology and predict which port on each switch
  is Root, Designated, or Alternate **before** running the show command.
- Verify by inspecting the port-channel roles on SW2 and SW3 for VLANs
  10, 20, 30, and 99.

**Verification:** `show spanning-tree vlan 10` on SW2 — Po1 (toward the
root SW1) must be in role **Root**; Po3 (toward SW3) must be in role
**Designated**. `show spanning-tree vlan 20` on SW1 — Po1 (toward the
VLAN 20 root SW2) must be in role **Root**.

---

### Task 4: Protect SW1's root role with root guard

- On the port-channels on SW1 that face SW2 (Po1) and SW3 (Po2), enable
  root guard for all VLANs.
- Confirm that the feature is applied on the logical port-channel
  interface — not on individual member links.

**Verification:** `show spanning-tree inconsistentports` on SW1 — must be
empty under normal operation. `show running-config interface Port-channel1`
must show `spanning-tree guard root`.

---

### Task 5: Apply PortFast and BPDU guard on PC-facing access ports

- On SW2 Gi1/1 (PC1) and SW3 Gi1/1 (PC2), enable PortFast so the port
  skips the listening/learning states on link-up.
- On the same ports, enable BPDU guard so any BPDU received err-disables
  the port.

**Verification:** `show spanning-tree interface Gi1/1 detail` on SW2 must
include `The port is in the portfast edge mode` and
`Bpdu guard is enabled`. `show spanning-tree summary` must show `Portfast
Default` or per-interface PortFast counts consistent with the number of
access ports configured.

---

### Task 6: Verify fast convergence on an edge port flap

- Simulate PC1 unplugging and re-plugging by shutting and unshutting SW2
  Gi1/1. Because PortFast is set, no topology change BPDU should be
  generated.
- Compare the topology change counter before and after the flap.

**Verification:** `show spanning-tree vlan 10 detail` on SW1 — the
`Number of topology changes` counter MUST NOT increment when PortFast is
configured correctly.

---

### Task 7: Verify STP behaviour across EtherChannel bundles

- Confirm that each port-channel (Po1, Po2, Po3) appears as a single
  logical STP port on every switch.
- For each VLAN, confirm that individual member interfaces (Gi0/1, Gi0/2,
  etc.) are not listed in `show spanning-tree` — only the Port-channel.

**Verification:** `show spanning-tree vlan 10` on SW2 — member interfaces
`Gi0/1` and `Gi0/2` must NOT appear; only `Po1` must appear as the logical
STP port for the bundle.

---

### Task 8: End-to-end reachability sanity check

- From PC1, ping PC2.
- From PC1, ping R1's VLAN 10 gateway (192.168.10.1).
- From PC2, ping R1's VLAN 20 gateway (192.168.20.1).

**Verification:** All three pings succeed with 0% loss. If any fail, the
root placement or the access-port configuration is likely wrong — revisit
Tasks 2 and 5.

---

## 6. Verification & Analysis

### Task 1 — Rapid PVST+ mode

```
SW1# show spanning-tree summary
Switch is in rapid-pvst mode                         ! ← must say "rapid-pvst"
Root bridge for: VLAN0010, VLAN0030, VLAN0099        ! ← SW1 is root for these
Extended system ID           is enabled
Portfast Default             is disabled
PortFast BPDU Guard Default  is disabled
```

### Task 2 — Root placement

```
SW1# show spanning-tree root

Vlan                   Root ID          Cost    Time   Dst Hel Max Fwd Root Port
---------------- -------------------- --------- ----- --- --- --- --- --------------
VLAN0001         32769 aabb.cc00.0100         0    15   2  20  15
VLAN0010          4106 aabb.cc00.1000         0    15   2  20  15              ! ← SW1 (priority 4096 + vlan 10 sys-id)
VLAN0020          4116 aabb.cc00.0200       1    15   2  20  15  Po1           ! ← SW2 is root via Po1
VLAN0030          4126 aabb.cc00.1000         0    15   2  20  15              ! ← SW1
VLAN0099          4195 aabb.cc00.1000         0    15   2  20  15              ! ← SW1
```

Note the `4096 + <vlan-id>` = Bridge ID priority values (4106, 4116, 4126, 4195).

### Task 3 — Port roles

```
SW2# show spanning-tree vlan 10

VLAN0010
  Spanning tree enabled protocol rstp
  Root ID    Priority    4106
             Address     aabb.cc00.1000                              ! ← SW1's MAC
             Cost        3
             Port        56 (Port-channel1)
             Hello Time   2 sec  Max Age 20 sec  Forward Delay 15 sec

Interface           Role Sts Cost      Prio.Nbr Type
------------------- ---- --- --------- -------- --------------------------------
Po1                 Root FWD 3         128.56   P2p                              ! ← Root port toward SW1
Po3                 Desg FWD 3         128.58   P2p                              ! ← Designated on SW2<->SW3 link
```

### Task 4 — Root guard

```
SW1# show spanning-tree inconsistentports

Name                 Interface                Inconsistency
-------------------- ------------------------ ------------------
                                                                ! ← empty = no violation

Number of inconsistent ports (segments) in the system : 0      ! ← must be 0
```

```
SW1# show running-config interface Port-channel1
interface Port-channel1
 ...
 spanning-tree guard root                             ! ← must be present
```

### Task 5 — PortFast and BPDU guard

```
SW2# show spanning-tree interface Gi1/1 detail
 Port 69 (GigabitEthernet1/1) of VLAN0010 is designated forwarding
   Port path cost 4, Port priority 128, Port Identifier 128.69
   Designated root has priority 4106, address aabb.cc00.1000
   ...
   The port is in the portfast edge mode                         ! ← required
   ...
   Bpdu guard is enabled                                         ! ← required
   Link type is point-to-point by default, Internal
   BPDU: sent 23, received 0
```

### Task 6 — Topology-change suppression on edge flaps

```
SW1# show spanning-tree vlan 10 detail | include topology changes
  Number of topology changes 0 last change occurred 00:12:44 ago  ! ← before flap
```

Flap PC1 port:
```
SW2(config)# interface Gi1/1
SW2(config-if)# shutdown
SW2(config-if)# no shutdown
```

```
SW1# show spanning-tree vlan 10 detail | include topology changes
  Number of topology changes 0 last change occurred 00:13:02 ago  ! ← unchanged = PortFast working
```

If the counter increments, PortFast is not applied — revisit Task 5.

### Task 7 — STP over EtherChannel

```
SW2# show spanning-tree vlan 10

... (header)

Interface           Role Sts Cost      Prio.Nbr Type
------------------- ---- --- --------- -------- --------------------------------
Po1                 Root FWD 3         128.56   P2p                ! ← logical Po1 only
Po3                 Desg FWD 3         128.58   P2p                ! ← logical Po3 only
Gi1/1               Desg FWD 4         128.69   P2p Edge           ! ← access port to PC1
                                                                    ! ← Gi0/1 and Gi0/2 MUST NOT appear
```

### Task 8 — End-to-end reachability

```
PC1> ping 192.168.20.10

84 bytes from 192.168.20.10 icmp_seq=1 ttl=63 time=2.534 ms
84 bytes from 192.168.20.10 icmp_seq=2 ttl=63 time=1.892 ms
...                                                               ! ← all replies succeed
```

---

## 7. Verification Cheatsheet

### Rapid PVST+ Mode Configuration

```
spanning-tree mode rapid-pvst
```

| Command | Purpose |
|---------|---------|
| `spanning-tree mode rapid-pvst` | Switch from default PVST+ to Rapid PVST+ (802.1w per-VLAN) |
| `spanning-tree mode mst` | Switch to Multiple Spanning Tree (covered in Lab 03) |

> **Exam tip:** The default mode on most IOS platforms is `pvst` (legacy).
> Rapid PVST+ is not automatic — explicitly configure it.

### Root Bridge Priority

```
spanning-tree vlan <id[,id,...]> priority <0-61440 in 4096 steps>
```

| Command | Purpose |
|---------|---------|
| `spanning-tree vlan 10,30,99 priority 4096` | Make this switch the primary root for those VLANs |
| `spanning-tree vlan 20 priority 8192` | Make this switch the secondary root (backup) for VLAN 20 |
| `spanning-tree vlan 10 root primary` | Macro — sets priority to 24576 (older, less deterministic) |

> **Exam tip:** Always use explicit `priority` values — not the `root primary` macro.
> The exam rewards knowing what the actual priority number is.

### STP Enhancements — Edge Protection

```
interface GigabitEthernetX/Y
 spanning-tree portfast
 spanning-tree bpduguard enable
```

| Command | Purpose |
|---------|---------|
| `spanning-tree portfast` | Skip listen/learn on this port — immediate forwarding (edge only) |
| `spanning-tree bpduguard enable` | Err-disable port if a BPDU arrives |
| `spanning-tree portfast default` | (global) Apply PortFast to all access ports |
| `spanning-tree portfast bpduguard default` | (global) Apply BPDU guard to all PortFast ports |

> **Exam tip:** PortFast only applies to access ports. Enabling it on a trunk
> generates a warning and has no effect unless combined with
> `spanning-tree portfast trunk` (rarely correct).

### STP Enhancements — Root Protection

```
interface Port-channelN
 spanning-tree guard root
```

| Command | Purpose |
|---------|---------|
| `spanning-tree guard root` | If a superior BPDU arrives, put the port in `root-inconsistent` (blocks until superior BPDU stops) |
| `spanning-tree guard loop` | Port blocks if BPDUs stop arriving (unidirectional link protection) |

> **Exam tip:** Root guard goes on the **designated** port (facing downstream).
> Loop guard goes on **non-designated** ports (Root or Alternate).
> Getting this backward is the most common exam trap.

### Verification Commands

| Command | What to Look For |
|---------|------------------|
| `show spanning-tree summary` | STP mode (`rapid-pvst`), which VLANs this switch is root for, Portfast defaults |
| `show spanning-tree root` | Root bridge ID and root port for every VLAN |
| `show spanning-tree vlan <id>` | Per-VLAN port roles (Root/Desg/Altn), states (FWD/BLK), types (P2p Edge) |
| `show spanning-tree vlan <id> detail` | Topology change counter + time since last change |
| `show spanning-tree inconsistentports` | Ports currently blocked by root guard or loop guard |
| `show spanning-tree interface <int> detail` | Per-port PortFast / BPDU guard / Guard-Root state |

### Wildcard Mask Quick Reference

Not used in Layer 2 STP (no OSPF/EIGRP network statements this lab).

### Common Rapid PVST+ Failure Causes

| Symptom | Likely Cause |
|---------|--------------|
| All VLANs root on the same "random" switch with MAC bridge-id | No explicit `priority` set — MAC tiebreaker wins |
| VLAN traffic takes sub-optimal path despite topology | Port cost overridden with `spanning-tree vlan X cost Y` |
| PC-facing port repeatedly err-disables after reboot | BPDU guard is catching a real switch plugged into an access port |
| SW1 Po1 in `BKN*` (broken) state with `root-inconsistent` | Root guard triggered — a downstream switch is advertising superior BPDU |
| Convergence takes 30+ s after link failure | Switch is in legacy `pvst` mode instead of `rapid-pvst` |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Objective 1: Enable Rapid PVST+

<details>
<summary>Click to view All Switches Configuration</summary>

```bash
! SW1, SW2, SW3 (identical on all three)
spanning-tree mode rapid-pvst
```

</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show spanning-tree summary
```

Expect: `Switch is in rapid-pvst mode` as the first line.

</details>

### Objective 2: Root placement per VLAN

<details>
<summary>Click to view SW1 Configuration</summary>

```bash
! SW1
spanning-tree vlan 10,30,99 priority 4096
```

</details>

<details>
<summary>Click to view SW2 Configuration</summary>

```bash
! SW2
spanning-tree vlan 20 priority 4096
```

</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show spanning-tree root
show spanning-tree vlan 10
show spanning-tree vlan 20
```

</details>

### Objective 4: Root guard on SW1 designated bundles

<details>
<summary>Click to view SW1 Configuration</summary>

```bash
! SW1
interface Port-channel1
 spanning-tree guard root
!
interface Port-channel2
 spanning-tree guard root
```

</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show spanning-tree inconsistentports
show running-config interface Port-channel1
show running-config interface Port-channel2
```

</details>

### Objective 5: PortFast + BPDU guard on edge ports

<details>
<summary>Click to view SW2 Configuration</summary>

```bash
! SW2
interface GigabitEthernet1/1
 spanning-tree portfast
 spanning-tree bpduguard enable
```

</details>

<details>
<summary>Click to view SW3 Configuration</summary>

```bash
! SW3
interface GigabitEthernet1/1
 spanning-tree portfast
 spanning-tree bpduguard enable
```

</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show spanning-tree interface Gi1/1 detail
```

Expect both `The port is in the portfast edge mode` and `Bpdu guard is enabled`.

</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. Inject the fault first, then
diagnose and fix using only show commands.

### Workflow

```bash
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>     # reset to known-good
python3 scripts/fault-injection/inject_scenario_NN.py --host <eve-ng-ip> # break
# diagnose + fix using show commands only
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>     # restore
```

Inject scripts run a **pre-flight check** — they refuse to inject if the
target device isn't in the expected solution state. Always restore with
`apply_solution.py` between tickets.

---

### Ticket 1 — VLAN 10 connectivity broken between SW1 and SW2

Users in VLAN 10 (Sales) on PC1's side cannot reach the R1 gateway
(192.168.10.1) or anything in VLAN 30. VLAN 20 traffic through the same
path works normally. SW1 logs show Po1 changing STP states for VLAN 10.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>`

**Success criteria:** PC1 can ping 192.168.10.1 and 192.168.20.10
again; `show spanning-tree inconsistentports` on SW1 is empty.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. On SW1: `show spanning-tree inconsistentports` — Po1 listed with
   inconsistency `root-inconsistent` for VLAN 10.
2. On SW1: `show spanning-tree vlan 10` — Po1 state is `BKN*` (broken /
   blocking) instead of `FWD`.
3. On SW2: `show spanning-tree vlan 10` — SW2 reports itself as root for
   VLAN 10 with priority 0. This is the smoking gun.
4. On SW2: `show running-config | include spanning-tree vlan 10` — an
   unexpected `spanning-tree vlan 10 priority 0` line is present.
5. Recall the design: SW1 is supposed to be root for VLAN 10 with
   priority 4096; any switch advertising lower priority through a
   root-guard-protected port will be blocked.

</details>

<details>
<summary>Click to view Fix</summary>

Remove the unauthorised priority override on SW2:

```bash
! SW2
no spanning-tree vlan 10 priority 0
```

Once SW2 stops advertising superior BPDUs, SW1's root guard releases
Po1 from `root-inconsistent` automatically after the BPDU timeout.
Verify:

```bash
SW1# show spanning-tree inconsistentports
Number of inconsistent ports (segments) in the system : 0

SW1# show spanning-tree vlan 10
  Root ID    Priority    4106
             Address     aabb.cc00.1000            ! ← SW1 is root again
```

</details>

---

### Ticket 2 — Slow network convergence after link events

After a maintenance window one of the switches was rebooted. Users now
complain that any brief link flap causes ~30 seconds of black-hole time
before traffic recovers — compared to the near-instant recovery observed
before the maintenance. `show spanning-tree summary` on each switch
shows different STP modes.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py --host <eve-ng-ip>`

**Success criteria:** All three switches show `rapid-pvst mode` in
`show spanning-tree summary`. Shutting and no-shutting a Po3 member
recovers in <3 seconds.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. On SW1: `show spanning-tree summary | include mode` — `rapid-pvst`.
2. On SW2: `show spanning-tree summary | include mode` — `rapid-pvst`.
3. On SW3: `show spanning-tree summary | include mode` — `pvst`
   (legacy). This is the fault.
4. Recall: rapid-pvst interoperates with legacy pvst at the boundary
   (SW3 drops to legacy timers), which is what breaks the fast-convergence
   promise.

</details>

<details>
<summary>Click to view Fix</summary>

```bash
! SW3
spanning-tree mode rapid-pvst
```

Verify:
```bash
SW3# show spanning-tree summary | include mode
Switch is in rapid-pvst mode
```

</details>

---

### Ticket 3 — VLAN 20 takes a suboptimal path

The VLAN 20 (Engineering) user on PC2 reports working-but-slow
connectivity to R1's 192.168.20.1 gateway. Ping works, but the path
visibly hops through SW1 instead of the direct SW2<->SW3 bundle. SW3's
VLAN 20 root port is pointing the wrong direction.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py --host <eve-ng-ip>`

**Success criteria:** `show spanning-tree vlan 20` on SW3 shows the
root port as **Po3** (direct to SW2, the VLAN 20 root).

<details>
<summary>Click to view Diagnosis Steps</summary>

1. On SW3: `show spanning-tree vlan 20` — Root Port is Po2 (through
   SW1), not Po3 (direct to SW2). Cost-wise, Po3 should be the shorter
   path because SW2 is the root for VLAN 20.
2. On SW2: `show spanning-tree vlan 20` — Po3's port cost is an
   abnormally high value (e.g. 200000000).
3. On SW2: `show running-config interface Port-channel3 | include cost` —
   an unexpected `spanning-tree vlan 20 cost 200000000` line is present.
4. Conclude: the cost override on SW2's Po3 is forcing SW3 to prefer
   Po2 (through SW1) as its root port for VLAN 20.

</details>

<details>
<summary>Click to view Fix</summary>

Remove the cost override on SW2's Po3:

```bash
! SW2
interface Port-channel3
 no spanning-tree vlan 20 cost 200000000
```

Verify SW3 re-elects Po3 as its VLAN 20 root port:
```bash
SW3# show spanning-tree vlan 20
  Root ID    Priority    4116
             Address     aabb.cc00.0200            ! ← SW2
             Cost        3
             Port        58 (Port-channel3)        ! ← direct path restored
```

</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] All three switches are in `rapid-pvst mode` (Task 1)
- [ ] `show spanning-tree root` shows SW1's MAC for VLAN 10/30/99 and SW2's MAC for VLAN 20 (Task 2)
- [ ] Port roles on SW2 match prediction — Po1 is Root for VLAN 10, Po3 is Designated (Task 3)
- [ ] `show running-config interface Port-channel1` on SW1 shows `spanning-tree guard root` (Task 4)
- [ ] `show spanning-tree interface Gi1/1 detail` on SW2 and SW3 both show `portfast edge mode` and `Bpdu guard is enabled` (Task 5)
- [ ] Flapping PC1's access port does NOT increment the topology change counter on SW1 (Task 6)
- [ ] STP output shows only Po1/Po2/Po3 — never individual member links like Gi0/1 (Task 7)
- [ ] PC1 pings PC2, 192.168.10.1, and 192.168.20.1 with 0% loss (Task 8)

### Troubleshooting

- [ ] Ticket 1 solved: SW1's root guard reason understood; `show spanning-tree inconsistentports` clean
- [ ] Ticket 2 solved: all three switches back on `rapid-pvst`
- [ ] Ticket 3 solved: SW3's VLAN 20 root port is Po3, not Po2
