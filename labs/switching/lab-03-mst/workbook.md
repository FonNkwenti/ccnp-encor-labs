# Lab 03 — Multiple Spanning Tree (MST)

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

**Exam Objective:** Blueprint 3.1.c — Layer 2 Spanning Tree (MST)

This lab is a **standalone** study of Multiple Spanning Tree (IEEE 802.1s). You
start from a working Rapid PVST+ baseline (trunks up, VLANs 10/20/30/99 defined,
end-to-end reachability via R1 router-on-a-stick) and convert the campus to MST.
The pedagogical goal is to make one thing obvious by the end of the lab: MST runs
a small, engineered set of instances — not one per VLAN — and *region identity*
is the load-bearing concept that everything else depends on.

### Why MST exists (vs Rapid PVST+)

Rapid PVST+ runs one full 802.1w state machine per VLAN. On a switch with 200
VLANs that is 200 parallel STP instances, each with its own BPDU flow, timers,
and CPU cost. MST groups VLANs into a **small number of instances** — typically
two or three — and runs one 802.1w state machine per instance.

| Aspect | Rapid PVST+ (802.1w) | MST (802.1s) |
|--------|----------------------|--------------|
| STP instances | One per VLAN | One per MST instance (2-3 typical) |
| BPDU overhead | High on VLAN-dense switches | Low and bounded |
| Load balancing | Per-VLAN priority tuning | Per-instance priority, with VLAN groups mapped to instances |
| Interop | Cisco-proprietary PVST+ | IEEE 802.1s standard |
| Configuration cost | Almost none | Must define region identity on every switch |

MST is what production enterprise networks run for two reasons: bounded control-plane
cost, and the ability to engineer traffic by grouping VLANs into instances that
root at different bridges.

### MST region — the three-field identity

All switches that must participate in the same MST domain share an identical
**region configuration**. The region is defined by *exactly three things*:

| Field | Example | Rule |
|-------|---------|------|
| Region **name** | `ENCOR-REGION` | Case-sensitive string |
| **Revision** number | `1` | 16-bit integer, not auto-incremented |
| VLAN-to-instance **mapping** | VLAN 10,99 -> MST 1 | Every VLAN maps to exactly one instance (0 by default) |

Two switches are in the same region **only if all three fields match exactly**.
A single-character typo in the name, a revision bump that wasn't propagated, or
a missing VLAN mapping on one switch puts that switch at the region boundary —
which changes its STP behaviour fundamentally (see "MST boundary" below).

The configuration is entered in a sub-mode, not at global level:

```
SW1(config)# spanning-tree mst configuration
SW1(config-mst)# name ENCOR-REGION
SW1(config-mst)# revision 1
SW1(config-mst)# instance 1 vlan 10, 99
SW1(config-mst)# instance 2 vlan 20, 30
SW1(config-mst)# exit
```

Nothing commits until you `exit` the sub-mode — IOS validates the mapping as a
single atomic change.

### Instance 0 — IST and CIST

MST always has **Instance 0**, called the **IST** (Internal Spanning Tree). Every
VLAN that isn't explicitly mapped elsewhere sits in Instance 0. The IST is also
the only instance that carries BPDUs across the region boundary — it appears to
the outside world as the region's single **CIST** (Common and Internal Spanning
Tree). Remember two rules:

1. You cannot delete Instance 0. It's the default bucket.
2. Only Instance 0's BPDUs cross into a neighbouring region. Instances 1 through
   N are region-internal.

### Per-instance root election

Each MST instance has its own independent root bridge election — same rules as
Rapid PVST+ (lowest Bridge ID wins, priority in 4096 steps, MAC tiebreaker), but
per **instance** rather than per **VLAN**. Typical deterministic placement:

```
SW1(config)# spanning-tree mst 1 priority 4096   ! SW1 is root for Instance 1 (VLAN 10, 99)
SW2(config)# spanning-tree mst 2 priority 4096   ! SW2 is root for Instance 2 (VLAN 20, 30)
```

Because VLAN 10 and VLAN 99 are both mapped to Instance 1, they share a single
forwarding topology rooted at SW1. Students must internalise that the mapping is
the load-balancing knob — priorities alone don't split traffic between VLANs in
the same instance.

### Port roles and states — per instance, not per VLAN

Every port has one role per instance. On a triangle with dual trunks per pair,
a given physical port might be:

- **Root port** for Instance 1 (forwarding toward SW1)
- **Designated port** for Instance 2 (forwarding toward a non-root neighbour)
- ...all on the same physical interface, simultaneously.

The output of `show spanning-tree mst <N>` gives the per-instance view that matters.
`show spanning-tree` alone shows only the summary and can hide per-instance detail.

### MST boundary — why region mismatch is so disruptive

When an MST switch sends BPDUs toward a neighbour that is **not in the same
region**, the neighbour treats the entire region as a single "virtual" bridge
speaking only CIST (Instance 0). The boundary port inherits IST behaviour and
loses any per-instance distinction. The most common cause is a typo in the
region name or a mismatched revision number. The visible symptom is that a
switch with correct mapping suddenly isn't blocking the ports it should be,
because its neighbour treats it as an external bridge.

**Troubleshooting approach:** when MST behaviour surprises you, always start with
`show spanning-tree mst configuration` on every switch and diff the region
fields. Ninety percent of MST problems are three-field identity drift.

### MST vs Rapid PVST+ — side-by-side output

After conversion, `show spanning-tree summary` on this lab's switches shows
**three** STP instances (MST 0, 1, 2). In the Rapid PVST+ baseline you had
**four** (one per VLAN). That reduction is the whole pitch for MST, visible in
a single command.

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| Configure MST mode | Switch STP mode from Rapid PVST+ to MST and verify the mode change |
| Define an MST region | Enter the sub-mode, set region name / revision / VLAN-to-instance mapping atomically |
| Verify region consistency | Confirm all switches share identical region identity using `show spanning-tree mst configuration` |
| Engineer per-instance roots | Assign different root bridges per MST instance for traffic engineering |
| Read per-instance port roles | Interpret `show spanning-tree mst <N>` to map roles per instance across the same physical ports |
| Diagnose region mismatch | Use three-field diff to locate region boundary faults |
| Contrast MST with Rapid PVST+ | Verify instance count reduction and explain the load-balancing shift |

---

## 2. Topology & Scenario

### Network Diagram

```
                              ┌────────────────────┐
                              │         R1         │
                              │ (Router-on-stick)  │
                              │   Lo0: 1.1.1.1     │
                              └─────────┬──────────┘
                                 Gi0/0  │ trunk (dot1q)
                                        │ native VLAN 99; allowed 10,20,30,99
                                        │
                              ┌─────────┴──────────┐
                              │        SW1         │
                              │  Root MST 1        │
                              │  (VLAN 10, 99)     │
                              │  priority 4096     │
                              └───┬────────────┬───┘
                      Gi0/1,Gi0/2 │            │ Gi0/3,Gi1/0
                        trunk x2  │            │   trunk x2
                                  │            │
                   ┌──────────────┴─┐      ┌───┴────────────────┐
                   │      SW2       │      │        SW3         │
                   │  Root MST 2    │      │  Region member     │
                   │ (VLAN 20, 30)  │      │  (no root role)    │
                   │ priority 4096  │      │  priority default  │
                   └──┬─────────┬───┘      └───┬──────────┬─────┘
               Gi1/1  │         │Gi0/3,Gi1/0   │Gi0/1,Gi0/2  │Gi1/1
               access │         │ trunk x2     │ trunk x2    │ access
               VLAN10 │         └──────┬───────┘             │ VLAN 20
                      │                │                     │
                  ┌───┴────┐       (SW2<->SW3           ┌────┴───┐
                  │  PC1   │        two trunks)         │  PC2   │
                  │ .10.10 │                            │ .20.10 │
                  └────────┘                            └────────┘
               192.168.10.0/24                       192.168.20.0/24

    Region: ENCOR-REGION / revision 1
    Instance 1 = VLAN 10, 99        (root: SW1)
    Instance 2 = VLAN 20, 30        (root: SW2)
    Instance 0 (IST) = everything unmapped (CIST toward external regions)
```

### Scenario

Acme Corp's campus Layer 2 core currently runs Rapid PVST+. Engineering has
requested that the core be migrated to MST ahead of a VLAN expansion project
that will bring total VLAN count past 150. The network architect has drafted
the region design:

- **Region:** `ENCOR-REGION`, revision `1`.
- **Instance 1:** VLAN 10 (Sales) and VLAN 99 (Native/Mgmt) — these map
  together so that management traffic follows the same forwarding topology
  as user Sales traffic, simplifying troubleshooting.
- **Instance 2:** VLAN 20 (Engineering) and VLAN 30 (Management Hosts) —
  heavier utilisation, rooted on SW2 for load distribution.
- **Instance 0 (IST/CIST):** everything else. Any future VLAN lands here by
  default until the architect explicitly maps it.
- **SW1** is the root for Instance 1; **SW2** is the root for Instance 2.
  SW3 is a region member with no root role.

You will convert all three switches from Rapid PVST+ to MST, define the
region identically on each, and verify per-instance root election and port
roles. Section 9 then injects three MST-specific faults for diagnosis.

---

## 3. Hardware & Environment Specifications

### Device Inventory

| Device | Platform | Role | Loopback0 |
|--------|----------|------|-----------|
| SW1 | IOSvL2 | Root for MST Instance 1 (VLAN 10, 99) | n/a |
| SW2 | IOSvL2 | Root for MST Instance 2 (VLAN 20, 30); PC1 access | n/a |
| SW3 | IOSvL2 | Region member (no root role); PC2 access | n/a |
| R1  | IOSv   | Inter-VLAN router (router-on-a-stick) | 1.1.1.1/32 |
| PC1 | VPC    | End host in VLAN 10 (192.168.10.0/24) | — |
| PC2 | VPC    | End host in VLAN 20 (192.168.20.0/24) | — |

### Cabling Table

| Link | A end | B end | Type | Purpose |
|------|-------|-------|------|---------|
| L1 | R1 Gi0/0 | SW1 Gi0/0 | Trunk | R1 router-on-a-stick |
| L2 | SW1 Gi0/1 | SW2 Gi0/1 | Trunk | SW1<->SW2 link 1 |
| L3 | SW1 Gi0/2 | SW2 Gi0/2 | Trunk | SW1<->SW2 link 2 |
| L4 | SW1 Gi0/3 | SW3 Gi0/3 | Trunk | SW1<->SW3 link 1 |
| L5 | SW1 Gi1/0 | SW3 Gi1/0 | Trunk | SW1<->SW3 link 2 |
| L6 | SW2 Gi0/3 | SW3 Gi0/1 | Trunk | SW2<->SW3 link 1 |
| L7 | SW2 Gi1/0 | SW3 Gi0/2 | Trunk | SW2<->SW3 link 2 |
| L8 | PC1 e0 | SW2 Gi1/1 | Access | PC1 in VLAN 10 |
| L9 | PC2 e0 | SW3 Gi1/1 | Access | PC2 in VLAN 20 |

> No EtherChannel bundles in this lab. The two parallel trunks per pair are
> intentional — they give you **two physical paths per instance** so that MST
> port-role assignment (one forwarding, one blocking) is visible in every
> `show` output.

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
| 99 (NATIVE_MGMT) | 192.168.99.0/24 | 192.168.99.254 (R1) |

---

## 4. Base Configuration

### What IS pre-loaded (initial-configs/)

- Hostnames, `no ip domain-lookup`
- VLAN database (10, 20, 30, 99) on all three switches
- All inter-switch trunks (static `switchport mode trunk`, native VLAN 99,
  allowed 10,20,30,99, `nonegotiate`) — two parallel trunks per pair
- R1 router-on-a-stick sub-interfaces for all four VLANs
- PC1 access port (SW2 Gi1/1, VLAN 10) and PC2 access port (SW3 Gi1/1, VLAN 20)
- Management SVI on each switch (192.168.99.1/2/3)
- STP mode: **`rapid-pvst`** (the "before" state you will migrate *from*)
- PC1 / PC2 `.vpc` files auto-load on EVE-NG boot

### What is NOT pre-loaded (you will configure)

- MST mode (`spanning-tree mode mst`)
- MST region configuration (name, revision, VLAN-to-instance mapping)
- Per-instance root priorities (SW1 for MST 1, SW2 for MST 2)

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

### Task 1: Capture the Rapid PVST+ baseline

- Before touching any config, record the current state.
- Run `show spanning-tree summary` on every switch and note the STP mode
  (`rapid-pvst`) and the number of per-VLAN STP instances listed.
- Run `show spanning-tree root` and note which switch is root for each
  VLAN (likely a MAC-based "winner" since no priorities are tuned).

**Verification:** Every switch shows `rapid-pvst mode` and four per-VLAN
instances (VLANs 1, 10, 20, 30, 99 depending on which are active). Save
this output so you can diff it after the MST conversion.

---

### Task 2: Switch all three switches to MST mode

- On SW1, SW2, and SW3, change the spanning-tree mode to MST.
- This is the only per-switch step that doesn't require identical syntax
  across the region — the mode change itself is local.

**Verification:** `show spanning-tree summary` on each switch — the first
line must read `Switch is in mst mode`. At this point, with no region config
yet, every switch is in its own implicit region and will treat every
neighbour as external.

---

### Task 3: Configure the MST region identically on all three switches

- Enter the MST configuration sub-mode.
- Set region **name** to `ENCOR-REGION` (case-sensitive).
- Set **revision** to `1`.
- Map **VLANs 10 and 99** to MST **Instance 1**.
- Map **VLANs 20 and 30** to MST **Instance 2**.
- Exit the sub-mode so IOS commits the mapping atomically.

**Verification:** `show spanning-tree mst configuration` on each switch —
the output must be **byte-for-byte identical** across SW1, SW2, and SW3.
Any difference in name, revision, or mapping means the switch is in a
different region.

---

### Task 4: Elect SW1 as root for MST Instance 1 and SW2 as root for MST Instance 2

- On SW1, set the MST Instance 1 priority to 4096.
- On SW2, set the MST Instance 2 priority to 4096.
- Leave SW3 at default priority for both instances.

**Verification:** `show spanning-tree mst 1` on SW1 shows `This bridge is
the root`. `show spanning-tree mst 2` on SW2 shows the same. On SW3,
`show spanning-tree mst 1` shows SW1's MAC as the root; `show spanning-tree
mst 2` shows SW2's MAC as the root.

---

### Task 5: Verify per-instance port roles across the triangle

- On each switch, run `show spanning-tree mst 1` and then `show spanning-tree
  mst 2`. Note how the **same physical port** can have different roles in
  different instances.
- Specifically confirm: of the two parallel SW1<->SW2 trunks (Gi0/1 and Gi0/2),
  one is Root and one is Alternate for Instance 1 on SW2. The Alternate
  port is **blocking** for Instance 1 but still forwarding for Instance 0
  BPDUs.

**Verification:** On SW2 — `show spanning-tree mst 1` shows one of Gi0/1 /
Gi0/2 as `Root FWD` and the other as `Altn BLK`. `show spanning-tree mst 2`
shows the MST-2 view (SW2 is root, so all ports are Designated for that
instance).

---

### Task 6: Verify MST region consistency from every switch

- On each switch, run `show spanning-tree mst configuration digest`. The
  three fields plus the computed digest hash must match across SW1, SW2,
  and SW3.
- This hash is what MST uses to detect region boundaries at runtime — a
  neighbour with a different digest is treated as external.

**Verification:** The `Digest:` hex value at the bottom of
`show spanning-tree mst configuration digest` is identical on all three
switches.

---

### Task 7: Contrast MST with the Rapid PVST+ baseline

- Run `show spanning-tree summary` on SW1 again.
- Compare the instance count with the output you saved in Task 1.

**Verification:** Before MST, SW1 had one STP instance per active VLAN
(typically 4-5). After MST, SW1 has exactly **three** instances: MST 0
(IST/CIST), MST 1, and MST 2. This instance-count reduction is the
production motivation for MST.

---

### Task 8: End-to-end reachability sanity check

- From PC1, ping PC2.
- From PC1, ping R1's VLAN 10 gateway (192.168.10.1).
- From PC2, ping R1's VLAN 20 gateway (192.168.20.1).

**Verification:** All three pings succeed with 0% loss. If any fail, the
most likely cause is a region mismatch (Task 3) — different regions look
like external bridges to each other, which can block otherwise-valid paths.

---

## 6. Verification & Analysis

### Task 1 — Rapid PVST+ baseline

```
SW1# show spanning-tree summary
Switch is in rapid-pvst mode                         ! ← starting mode
Root bridge for: (none — MAC tiebreaker)             ! ← no priority tuning yet
Extended system ID           is enabled
...
Name                   Blocking Listening Learning Forwarding STP Active
---------------------- -------- --------- -------- ---------- ----------
VLAN0001                    0         0        0          5          5
VLAN0010                    1         0        0          4          5   ! ← one instance per VLAN
VLAN0020                    1         0        0          4          5
VLAN0030                    1         0        0          4          5
VLAN0099                    1         0        0          4          5
---------------------- -------- --------- -------- ---------- ----------
5 vlans                     4         0        0         21         25   ! ← 5 STP instances total
```

### Task 2 — MST mode enabled

```
SW1# show spanning-tree summary
Switch is in mst mode (IEEE Standard)                ! ← mode change confirmed
```

### Task 3 — Region configuration identical across switches

```
SW1# show spanning-tree mst configuration
Name      [ENCOR-REGION]                             ! ← must match on all 3 switches
Revision  1      Instances configured 3
Instance  Vlans mapped
--------  ---------------------------------------------------------------------
0         1-9,11-19,21-29,31-98,100-4094                                     ! ← IST: everything unmapped
1         10,99                                                              ! ← VLAN 10, 99 -> MST 1
2         20,30                                                              ! ← VLAN 20, 30 -> MST 2
-------------------------------------------------------------------------------
```

Run the same command on SW2 and SW3 — output must be **identical**.

### Task 4 — Per-instance root election

```
SW1# show spanning-tree mst 1

##### MST1    vlans mapped:   10,99
Bridge        address aabb.cc00.1000  priority      4097 (4096 sysid 1)
Root          this switch for MST1                                        ! ← SW1 is root for MST 1

Interface        Role Sts Cost      Prio.Nbr Type
---------------- ---- --- --------- -------- --------------------------------
Gi0/1            Desg FWD 20000     128.2    P2p                          ! ← all ports Designated
Gi0/2            Desg FWD 20000     128.3    P2p
Gi0/3            Desg FWD 20000     128.4    P2p
Gi1/0            Desg FWD 20000     128.9    P2p
```

```
SW2# show spanning-tree mst 2

##### MST2    vlans mapped:   20,30
Bridge        address aabb.cc00.0200  priority      4098 (4096 sysid 2)
Root          this switch for MST2                                        ! ← SW2 is root for MST 2
```

### Task 5 — Per-instance port roles on the same physical ports

```
SW2# show spanning-tree mst 1

##### MST1    vlans mapped:   10,99
Bridge        address aabb.cc00.0200  priority      32769 (32768 sysid 1)
Root          address aabb.cc00.1000  priority      4097 (4096 sysid 1)     ! ← SW1 is root
              port    Gi0/1                                                 ! ← Root port for MST 1

Interface        Role Sts Cost      Prio.Nbr Type
---------------- ---- --- --------- -------- --------------------------------
Gi0/1            Root FWD 20000     128.2    P2p                           ! ← Root port
Gi0/2            Altn BLK 20000     128.3    P2p                           ! ← Alternate (blocking)
Gi0/3            Desg FWD 20000     128.4    P2p                           ! ← Designated toward SW3
Gi1/0            Desg FWD 20000     128.9    P2p
Gi1/1            Desg FWD 20000     128.10   P2p Edge
```

```
SW2# show spanning-tree mst 2

##### MST2    vlans mapped:   20,30
Bridge        address aabb.cc00.0200  priority      4098 (4096 sysid 2)
Root          this switch for MST2                                        ! ← SW2 is root for MST 2

Interface        Role Sts Cost      Prio.Nbr Type
---------------- ---- --- --------- -------- --------------------------------
Gi0/1            Desg FWD 20000     128.2    P2p                           ! ← SAME physical port, different role
Gi0/2            Desg FWD 20000     128.3    P2p
```

Compare the role of `Gi0/1` in the two outputs: **Root for MST 1** (forwarding
toward SW1), but **Designated for MST 2** (SW2 is the root for MST 2). This
is the per-instance-role payoff of MST.

### Task 6 — Region digest hash

```
SW1# show spanning-tree mst configuration digest
Name      [ENCOR-REGION]
Revision  1
Instances configured 3

Digest:                   0x9ABC1234567890DEF0123456789ABCDE   ! ← must match on SW2 and SW3
Pre-std Digest:           0x...
```

If any switch shows a different `Digest:` value, that switch is in a
different region — re-check Task 3 character by character.

### Task 7 — Instance count reduction

```
SW1# show spanning-tree summary
Switch is in mst mode (IEEE Standard)

Name                   Blocking Listening Learning Forwarding STP Active
---------------------- -------- --------- -------- ---------- ----------
MST0                        0         0        0          4          4
MST1                        0         0        0          4          4
MST2                        0         0        0          4          4   ! ← only 3 instances
---------------------- -------- --------- -------- ---------- ----------
3 msts                      0         0        0         12         12   ! ← down from 5 in Task 1
```

### Task 8 — End-to-end reachability

```
PC1> ping 192.168.20.10

84 bytes from 192.168.20.10 icmp_seq=1 ttl=63 time=2.412 ms
84 bytes from 192.168.20.10 icmp_seq=2 ttl=63 time=1.875 ms
...                                                                        ! ← all replies succeed
```

---

## 7. Verification Cheatsheet

### MST Mode Configuration

```
spanning-tree mode mst
```

| Command | Purpose |
|---------|---------|
| `spanning-tree mode mst` | Switch from Rapid PVST+ (or PVST+) to MST |
| `spanning-tree mode rapid-pvst` | Revert to Rapid PVST+ |

> **Exam tip:** Mode change is local, not regional. Each switch's mode is
> independent; the region config is what ties them together.

### MST Region Configuration

```
spanning-tree mst configuration
 name <region-name>
 revision <0-65535>
 instance <1-4094> vlan <vlan-list>
 exit
```

| Command | Purpose |
|---------|---------|
| `name ENCOR-REGION` | Set the region name (case-sensitive) |
| `revision 1` | Set the region revision number |
| `instance 1 vlan 10, 99` | Map VLAN 10 and VLAN 99 to MST Instance 1 |
| `no instance 1` | Remove Instance 1 (unmapped VLANs fall back to Instance 0) |
| `show pending` (inside sub-mode) | Preview uncommitted region changes before `exit` |
| `abort` (inside sub-mode) | Discard uncommitted region changes |

> **Exam tip:** Nothing commits until you `exit` the sub-mode. Until then
> the running config still reflects the old region. Always follow with
> `show spanning-tree mst configuration` on every switch to confirm consistency.

### Per-Instance Root Priority

```
spanning-tree mst <instance-id> priority <0-61440 in 4096 steps>
```

| Command | Purpose |
|---------|---------|
| `spanning-tree mst 1 priority 4096` | Make this switch the primary root for MST Instance 1 |
| `spanning-tree mst 2 priority 8192` | Make this switch the secondary root for MST Instance 2 |
| `spanning-tree mst 0 priority 4096` | Make this switch the IST/CIST root (rarely manually set) |

> **Exam tip:** Priority is per **instance**, never per VLAN. The VLAN grouping
> inside the instance is what determines which traffic follows this root.

### Verification Commands

| Command | What to Look For |
|---------|------------------|
| `show spanning-tree summary` | STP mode (`mst`), instance count (should match number of mapped instances + MST 0) |
| `show spanning-tree mst configuration` | Region name, revision, VLAN-to-instance mapping |
| `show spanning-tree mst configuration digest` | 128-bit digest hash — must match across region members |
| `show spanning-tree mst <N>` | Per-instance root bridge, bridge ID, and port roles |
| `show spanning-tree mst interface <int>` | Per-instance role for one physical port |
| `show spanning-tree mst detail` | All instances + topology change counters |

### VLAN-to-Instance Mapping Worksheet

| Instance | VLANs | Purpose | Root Bridge |
|----------|-------|---------|-------------|
| 0 (IST/CIST) | Everything unmapped | Boundary BPDUs + future VLANs | SW1 or lowest-MAC (default) |
| 1 | 10, 99 | Sales + Native/Management | SW1 (priority 4096) |
| 2 | 20, 30 | Engineering + Management Hosts | SW2 (priority 4096) |

### Common MST Failure Causes

| Symptom | Likely Cause |
|---------|--------------|
| One switch has a different number of MST instances in `show spanning-tree summary` | That switch has a different region mapping — boundary behaviour |
| Region digest hash differs between two switches | Name, revision, or VLAN-to-instance mapping mismatch |
| All ports Designated on a non-root switch for a given instance | Neighbour is treating this switch as external (region mismatch) |
| A VLAN you mapped to MST 2 appears to follow MST 0 | Mapping didn't commit — did you `exit` the sub-mode? |
| Mode change succeeded but no instances appear | `spanning-tree mst configuration` never entered — only Instance 0 exists by default |
| Unexpected blocking port for an instance whose root you didn't configure | Default-priority root election picked a switch by MAC tiebreaker |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Objective 2: Enable MST mode

<details>
<summary>Click to view All Switches Configuration</summary>

```bash
! SW1, SW2, SW3 (identical)
spanning-tree mode mst
```

</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show spanning-tree summary
```

Expect `Switch is in mst mode (IEEE Standard)` as the first line.

</details>

### Objective 3: MST region configuration

<details>
<summary>Click to view All Switches Configuration</summary>

```bash
! SW1, SW2, SW3 — identical region config
spanning-tree mst configuration
 name ENCOR-REGION
 revision 1
 instance 1 vlan 10, 99
 instance 2 vlan 20, 30
 exit
```

</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show spanning-tree mst configuration
show spanning-tree mst configuration digest
```

Expect identical name, revision, mapping, and digest on all three switches.

</details>

### Objective 4: Per-instance root priorities

<details>
<summary>Click to view SW1 Configuration</summary>

```bash
! SW1 — root for MST 1
spanning-tree mst 1 priority 4096
```

</details>

<details>
<summary>Click to view SW2 Configuration</summary>

```bash
! SW2 — root for MST 2
spanning-tree mst 2 priority 4096
```

</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show spanning-tree mst 1
show spanning-tree mst 2
```

On SW1, `show spanning-tree mst 1` must say `This bridge is the root`.
On SW2, `show spanning-tree mst 2` must say the same.

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

### Ticket 1 — SW3 suddenly shows all Designated ports and extra STP instances

Users report intermittent connectivity to the VLAN 20 gateway. On SW3,
`show spanning-tree summary` lists more MST instances than SW1 and SW2 do,
and every port on SW3 shows role Designated for MST 0 — even the ones that
should be Alternate. SW1 and SW2 look correct to each other; only SW3 is
acting strangely.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>`

**Success criteria:** `show spanning-tree mst configuration digest` on all
three switches returns an identical digest value. PC2 can ping 192.168.20.1
and PC1 again with 0% loss.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Run `show spanning-tree mst configuration` on SW1, SW2, and SW3 and
   compare byte-for-byte. Most MST troubles diff on one of three fields:
   name, revision, or mapping.
2. Name matches (`ENCOR-REGION` on all three). Mapping matches (Instance 1
   = 10,99; Instance 2 = 20,30).
3. **Revision:** SW1 and SW2 show `Revision 1`. SW3 shows `Revision 99`
   (or some other unexpected value). This is the fault.
4. Run `show spanning-tree mst configuration digest` — SW3's digest differs
   from SW1/SW2's, confirming region boundary.
5. Recall: SW3 now acts as an external bridge to SW1 and SW2 — all
   inter-switch ports become IST/CIST boundary ports, which is why every
   port on SW3 is Designated for MST 0.

</details>

<details>
<summary>Click to view Fix</summary>

Restore the revision number on SW3 to match the region:

```bash
! SW3
spanning-tree mst configuration
 revision 1
 exit
```

Verify the digest re-aligns:

```bash
SW3# show spanning-tree mst configuration digest
Name      [ENCOR-REGION]
Revision  1
...
Digest:                   0x9ABC1234...            ! ← now matches SW1 and SW2
```

</details>

---

### Ticket 2 — VLAN 20 traffic follows an unexpected path

PC2 reaches its VLAN 20 gateway, but the path it takes looks wrong. On SW3,
`show spanning-tree mst 2` shows the root port pointing toward SW1 rather
than toward SW2 (which is the designed root for MST 2). Ping works but is
slower than expected under load. No region mismatch — all three switches
show identical `show spanning-tree mst configuration`.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py --host <eve-ng-ip>`

**Success criteria:** `show spanning-tree mst 2` on SW3 shows a root port
that leads directly toward SW2 (Gi0/1 or Gi0/2 — the SW2-facing trunks),
**not** toward SW1 (Gi0/3 or Gi1/0). SW2 must show `This bridge is the
root` for MST 2.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. On SW3: `show spanning-tree mst 2` — note the current root port and
   root bridge address.
2. On SW2: `show spanning-tree mst 2` — if SW2 is still claiming to be
   the root, the problem is elsewhere. If SW2 is NOT claiming root, its
   priority has been tampered with.
3. On SW2: `show running-config | include spanning-tree mst` — look for
   an unexpected `spanning-tree mst 2 priority` value. The baseline
   solution is `4096`; any higher value hands the root to a different
   switch.
4. Alternatively check SW1: a rogue `spanning-tree mst 2 priority 4096`
   on SW1 would let SW1 win MST 2 root via MAC tiebreaker (both SW1 and
   SW2 with priority 4096 + sysid 2 = 4098, then MAC breaks the tie).
5. The fault is one of: SW2's MST 2 priority removed or raised, OR SW1
   given a competing MST 2 priority.

</details>

<details>
<summary>Click to view Fix</summary>

Case A — SW2 lost its priority:

```bash
! SW2
spanning-tree mst 2 priority 4096
```

Case B — SW1 has a competing priority for MST 2:

```bash
! SW1
no spanning-tree mst 2 priority <competing-value>
```

Verify:

```bash
SW2# show spanning-tree mst 2 | include This bridge
                                  Root this switch for MST2            ! ← SW2 is root again

SW3# show spanning-tree mst 2 | include Root
Root    address aabb.cc00.0200    ! ← SW2's MAC
        port    Gi0/1 (or Gi0/2)  ! ← direct toward SW2, not through SW1
```

</details>

---

### Ticket 3 — VLAN 30 traffic behaves like VLAN 10

A user reports that Management Hosts (VLAN 30) traffic takes the same
physical path as Sales (VLAN 10) traffic, rather than the path MST 2
should be using. On SW2, `show spanning-tree mst 2` no longer lists VLAN
30 as a mapped VLAN. Region identity diff between switches exists but is
subtle — the name and revision match everywhere.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py --host <eve-ng-ip>`

**Success criteria:** `show spanning-tree mst configuration` on SW2 shows
`Instance 2 -> 20, 30` (not just `20` or VLAN 30 appearing under MST 1).
Digest hash re-aligns across all three switches. PC2 and PC1 both ping
their respective gateways.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Run `show spanning-tree mst configuration` on all three switches.
   Name and revision match. Now compare the instance mappings line by line.
2. SW1 and SW3 both show `Instance 2 vlans mapped 20, 30`.
3. SW2 shows `Instance 2 vlans mapped 20` only. VLAN 30 is no longer in
   Instance 2 on SW2 — it fell back to Instance 0 (IST).
4. Confirm with `show spanning-tree mst configuration digest` — SW2's
   digest differs from SW1/SW3.
5. Because VLAN 30 is mapped to MST 2 on SW1/SW3 but to MST 0 (IST) on
   SW2, forwarding for VLAN 30 across SW2's boundary-like ports takes an
   unexpected path — the classic "VLAN jumps instances on one switch"
   symptom.

</details>

<details>
<summary>Click to view Fix</summary>

Restore VLAN 30 into MST Instance 2 on SW2:

```bash
! SW2
spanning-tree mst configuration
 instance 2 vlan 20, 30
 exit
```

Verify:

```bash
SW2# show spanning-tree mst configuration
Instance  Vlans mapped
--------  ---------------------------------------------------------------------
0         1-9,11-19,21-29,31-98,100-4094
1         10,99
2         20,30                                              ! ← VLAN 30 back in MST 2
```

Digest should now match SW1 and SW3.

</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [x] Rapid PVST+ baseline captured before any changes (Task 1)
- [x] `show spanning-tree summary` on all three switches reads `mst mode (IEEE Standard)` (Task 2)
- [x] `show spanning-tree mst configuration` on SW1, SW2, SW3 is byte-for-byte identical — name ENCOR-REGION, revision 1, instance 1 = 10,99, instance 2 = 20,30 (Task 3)
- [x] `show spanning-tree mst 1` on SW1 reads `This bridge is the root` (Task 4)
- [x] `show spanning-tree mst 2` on SW2 reads `This bridge is the root` (Task 4)
- [x] On SW2 the same physical port has different roles per instance — e.g. Gi0/1 is Root for MST 1 and Designated for MST 2 (Task 5)
- [x] `show spanning-tree mst configuration digest` returns an identical Digest value on all three switches (Task 6)
- [x] Post-MST instance count in `show spanning-tree summary` is 3 (MST 0, 1, 2) — reduced from the per-VLAN count recorded in Task 1 (Task 7)
- [x] PC1 pings PC2, 192.168.10.1, and 192.168.20.1 with 0% loss (Task 8)

### Troubleshooting

- [ ] Ticket 1 solved: SW3's region revision restored; digest aligns across all three switches
- [ ] Ticket 2 solved: SW2's MST 2 priority restored; SW3's root port for MST 2 points toward SW2
- [ ] Ticket 3 solved: VLAN 30 re-mapped to MST Instance 2 on SW2; digest realigned
