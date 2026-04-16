# Lab 02 -- OSPF Network Types + DR/BDR Manipulation

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

**Exam Objective:** 3.2.b -- OSPFv2/OSPFv3 network types, DR/BDR election, priority
manipulation (CCNP ENCOR 350-401).

This lab evolves the multi-area topology from lab-01 by tuning the behavior of
each OSPF segment. You will inspect the default DR/BDR election on the Area 0
broadcast segment, override it with priority, and convert the two transit /30
links into OSPF point-to-point so they skip DR/BDR and shed their Type 2 LSAs.
The topology, addressing, and area design are unchanged -- the lesson here is
purely about *how OSPF runs on the wire*.

### OSPF network types

The OSPF network type determines three things on every interface:

| Property                | Broadcast          | Point-to-Point       |
|-------------------------|--------------------|----------------------|
| DR/BDR election         | Yes                | No                   |
| Hello / dead default    | 10 / 40 seconds    | 10 / 40 seconds (Ethernet); 10 / 40 on serial with HDLC/PPP |
| Uses multicast 224.0.0.5 | Yes               | Yes                  |
| Type 2 LSA generated    | Yes (by DR)        | No                   |
| Neighbors per segment   | 0..N               | Exactly 1            |

On IOS, Ethernet interfaces default to **broadcast**, regardless of whether the
subnet holds one peer or twenty. For a /30 transit with exactly two routers,
broadcast is functionally wasteful: the DR/BDR state, the Type 2 LSA, and the
`all-DROTHER` (224.0.0.6) multicast all exist to support segments that simply
aren't there. Converting the interface to `ip ospf network point-to-point`
removes every bit of that overhead while keeping the adjacency.

```
interface GigabitEthernet0/1
 ip ospf network point-to-point
```

Both ends must match -- a broadcast/p2p mismatch prevents the adjacency from
reaching FULL, usually visible as a stuck EXSTART/EXCHANGE state or routes
that flap as each side re-elects a DR the other side doesn't see.

### DR/BDR election and priority

On a broadcast segment, OSPF picks a **Designated Router (DR)** and **Backup
Designated Router (BDR)** during the first 40 seconds of the `Waiting` state.
Every other router on that segment becomes a **DROTHER**. DROTHERs form FULL
adjacency with the DR and BDR (multicasting to 224.0.0.6) but stay at the
2-WAY state with each other -- this is why `show ip ospf neighbor` on a
DROTHER lists its peers as `2WAY/DROTHER`.

Election order:

1. Highest **`ip ospf priority`** wins. Default is 1. Range 0..255.
2. Tie-break on highest **router-ID**.
3. Priority **0** means ineligible -- the router will never become DR or BDR
   no matter what happens to the current election winners.

OSPF does **not** pre-empt. Once a router is elected DR, it stays DR until
it disappears from the segment (dead timer expires, interface goes down,
or the OSPF process is cleared). Setting priority 255 on a router that
joins after the election still produces a DROTHER -- you have to force a
re-election (`clear ip ospf process` or bounce the interface) for the new
priority to take effect.

```
interface GigabitEthernet0/0
 ip ospf priority 255    ! eligible; wins on priority alone
!
interface GigabitEthernet0/0
 ip ospf priority 0      ! permanently ineligible (DROTHER only)
```

### Type 2 LSAs and why p2p sheds them

Every broadcast segment generates one **Type 2 (Network) LSA**, originated by
the DR, that enumerates the routers attached to that segment. Point-to-point
interfaces don't produce Type 2s -- the adjacency is described purely by the
two Router (Type 1) LSAs on each side. For a /30 transit carrying only two
routers, the Type 2 LSA duplicates information already in the Type 1s.
Converting the transit to p2p makes the LSDB smaller and SPF faster.

| LSA Type | Role                              | Generated on broadcast | Generated on p2p |
|----------|-----------------------------------|------------------------|------------------|
| 1        | Router LSA (intra-area prefixes)  | Yes                    | Yes              |
| 2        | Network LSA (broadcast DR only)   | Yes                    | **No**           |
| 3        | Summary LSA (ABR, inter-area)     | N/A                    | N/A              |

`show ip ospf database network` lists only Type 2 LSAs -- before the
conversion the Area 1 and Area 2 transits each produce one; after, only the
Area 0 shared segment appears.

### Skills this lab develops

| Skill                                           | Description                                                                |
|-------------------------------------------------|----------------------------------------------------------------------------|
| Inspect default OSPF network types              | Read `show ip ospf interface` and correctly identify broadcast vs p2p.    |
| Control DR/BDR election with `ip ospf priority` | Force a specific router to DR/BDR/DROTHER independent of router-ID.       |
| Apply priority 0 to exclude a router from election | Permanently remove a router from DR/BDR eligibility on a shared segment.   |
| Convert Ethernet transits to OSPF point-to-point | Align OSPF semantics with the physical /30 and drop DR/BDR overhead.      |
| Read the LSDB for network-type evidence         | Use `show ip ospf database network` / `router` to confirm Type 2 behavior. |
| Diagnose network-type mismatches                | Recognise the FULL/EXSTART/INIT symptoms of a one-sided p2p conversion.   |

---

## 2. Topology & Scenario

**Scenario.** The enterprise has stabilised the lab-01 multi-area design.
During an LSDB audit the operations team flagged three concerns:

1. R3 is currently the DR on the Area 0 backbone purely because it has the
   highest router-ID. Architecture wants the strongest router (R1) to carry
   DR responsibility, with R2 as BDR, and R3 explicitly excluded from the
   election -- R3 is scheduled for a planned maintenance next quarter and
   must not be eligible when it comes back online.
2. The Area 1 and Area 2 transit links are /30s with exactly two OSPF peers.
   Running DR/BDR election on them is pointless and bloats the LSDB with
   Type 2 LSAs that describe nothing new.
3. Convergence metrics should stay equal or improve after the changes.

Your job: tune the Area 0 election, convert the two transit links to
point-to-point, verify the LSDB shrinks as expected, and confirm PC1 can
still reach PC2 on both IPv4 and IPv6.

```
                            ┌──────────────────────┐
                            │        R1            │
                            │   (Area 0, DR)       │
                            │  Lo0: 1.1.1.1/32     │
                            │  prio 255            │
                            └──────────┬───────────┘
                                       │ Gi0/0
                                       │ 10.0.123.1/24
                                       │
                              ┌────────┴─────────┐
                              │   SW-AREA0       │  10.0.123.0/24
                              │   (unmanaged)    │  Broadcast
                              └───┬──────────┬───┘
                          Gi0/0   │          │   Gi0/0
                   10.0.123.2/24  │          │  10.0.123.3/24
                    ┌─────────────┴─┐      ┌─┴─────────────┐
                    │     R2        │      │     R3        │
                    │ (ABR 0/1, BDR)│      │(ABR 0/2, DROTHER)
                    │ Lo0: 2.2.2.2  │      │ Lo0: 3.3.3.3  │
                    │ prio 200      │      │ prio 0        │
                    └───────┬───────┘      └───┬───────────┘
                      Gi0/1 │                  │ Gi0/1
                  10.1.24.1/30                 │ 10.2.35.1/30
                            │ p2p           p2p│
                  10.1.24.2/30                 │ 10.2.35.2/30
                      Gi0/0 │                  │ Gi0/0
                    ┌───────┴───────┐      ┌───┴───────────┐
                    │     R4        │      │     R5        │
                    │   (Area 1)    │      │   (Area 2)    │
                    │ Lo0: 4.4.4.4  │      │ Lo0: 5.5.5.5  │
                    └───────┬───────┘      └───┬───────────┘
                      Gi0/2 │                  │ Gi0/1
                  192.168.1.1/24              192.168.2.1/24
                    ┌───────┴───────┐      ┌───┴───────────┐
                    │     PC1       │      │     PC2       │
                    │ .10 / ...::10 │      │ .10 / ...::10 │
                    └───────────────┘      └───────────────┘
                   192.168.1.0/24          192.168.2.0/24
```

---

## 3. Hardware & Environment Specifications

| Role                    | Device    | Platform           | Key Interfaces                               |
|-------------------------|-----------|--------------------|----------------------------------------------|
| Backbone router         | R1        | IOSv               | Gi0/0 to SW-AREA0                            |
| ABR (Area 0 / Area 1)   | R2        | IOSv               | Gi0/0 to SW-AREA0, Gi0/1 to R4               |
| ABR (Area 0 / Area 2)   | R3        | IOSv               | Gi0/0 to SW-AREA0, Gi0/1 to R5               |
| Internal Area 1 router  | R4        | IOSv               | Gi0/0 to R2, Gi0/2 to PC1                    |
| Internal Area 2 router  | R5        | IOSv               | Gi0/0 to R3, Gi0/1 to PC2                    |
| Shared broadcast segment| SW-AREA0  | Unmanaged switch   | 3 ports (R1, R2, R3)                         |
| Test host (Area 1)      | PC1       | VPCS               | PC1 eth0 to R4 Gi0/2                         |
| Test host (Area 2)      | PC2       | VPCS               | PC2 eth0 to R5 Gi0/1                         |

### Cabling

| Link | From (device / port) | To (device / port) | Subnet (v4)      | Subnet (v6)           |
|------|----------------------|--------------------|------------------|-----------------------|
| L1   | R1 Gi0/0             | SW-AREA0           | 10.0.123.0/24    | 2001:DB8:0:123::/64   |
| L2   | R2 Gi0/0             | SW-AREA0           | 10.0.123.0/24    | 2001:DB8:0:123::/64   |
| L3   | R3 Gi0/0             | SW-AREA0           | 10.0.123.0/24    | 2001:DB8:0:123::/64   |
| L4   | R2 Gi0/1             | R4 Gi0/0           | 10.1.24.0/30     | 2001:DB8:1:24::/64    |
| L5   | R3 Gi0/1             | R5 Gi0/0           | 10.2.35.0/30     | 2001:DB8:2:35::/64    |
| L6   | R4 Gi0/2             | PC1 eth0           | 192.168.1.0/24   | 2001:DB8:1:1::/64     |
| L7   | R5 Gi0/1             | PC2 eth0           | 192.168.2.0/24   | 2001:DB8:2:2::/64     |

### Console Access Table

| Device     | Port           | Connection Command            |
|------------|----------------|-------------------------------|
| R1         | (see EVE-NG UI)| `telnet <eve-ng-ip> <port>`   |
| R2         | (see EVE-NG UI)| `telnet <eve-ng-ip> <port>`   |
| R3         | (see EVE-NG UI)| `telnet <eve-ng-ip> <port>`   |
| R4         | (see EVE-NG UI)| `telnet <eve-ng-ip> <port>`   |
| R5         | (see EVE-NG UI)| `telnet <eve-ng-ip> <port>`   |
| PC1        | (see EVE-NG UI)| `telnet <eve-ng-ip> <port>`   |
| PC2        | (see EVE-NG UI)| `telnet <eve-ng-ip> <port>`   |

---

## 4. Base Configuration

`setup_lab.py` pushes `initial-configs/` -- a verbatim copy of the lab-01
solution. Each router therefore already has:

- Hostnames, `no ip domain-lookup`, `ipv6 unicast-routing`
- All IPv4 and IPv6 addresses from lab-01
- Multi-area OSPFv2 (Areas 0, 1, 2) with all required `network` statements
- OSPFv3 for IPv6 on every active interface, areas mirroring OSPFv2
- Matching 5/20 hello/dead timers on R2 Gi0/1 and R4 Gi0/0
- PC1 and PC2 dual-stack via `.vpc` files

**NOT pre-loaded** (this is your job):

- OSPF priority on Area 0 interfaces (all three routers default to priority 1)
- Point-to-point network type on the Area 1 and Area 2 transit links
  (both default to broadcast on Ethernet)

After `setup_lab.py` completes you should see PC1 ping PC2 successfully --
the network is fully converged. The work in this lab is about *how* it
converges, not whether.

---

## 5. Lab Challenge: Core Implementation

Work the tasks in order. Each one builds on the state from the previous.

### Task 1: Observe the default network types and DR/BDR election

- On R1, R2, and R3, survey the OSPF interface state on Gi0/0. Record the
  network type, the priority, and the current DR/BDR identities.
- On R2 Gi0/1 and R3 Gi0/1 (the transit links), confirm the default network
  type that Ethernet inherits.
- Check the LSDB for Type 2 (Network) LSAs on every router. Note which
  segments produce one and which routers are listed as attached.

**Verification:** `show ip ospf interface brief` on all five routers should
show every active OSPF interface; `show ip ospf neighbor` on R1, R2, R3 must
list the DR and BDR chosen by router-ID tie-break (highest RID = 3.3.3.3 = R3
is DR, 2.2.2.2 = R2 is BDR, 1.1.1.1 = R1 is DROTHER); `show ip ospf database
network` must list three Type 2 LSAs (one per broadcast segment: 10.0.123.0,
10.1.24.0, 10.2.35.0).

---

### Task 2: Force R1 to DR and R2 to BDR on the Area 0 segment

- On R1 Gi0/0, set the OSPF priority to 255 (maximum).
- On R2 Gi0/0, set the OSPF priority to 200.
- R3 keeps its default priority for the moment (do not touch R3 in this step).
- After configuration, force a re-election. On the DR-elect (R1), clearing the
  OSPF process or bouncing Gi0/0 is sufficient -- OSPF does not pre-empt, so
  the priority change alone will not promote R1 without a re-election.

**Verification:** `show ip ospf interface gi0/0` on R1 must report
`State DR, Priority 255`. `show ip ospf interface gi0/0` on R2 must report
`State BDR, Priority 200`. `show ip ospf neighbor` on R1 must show both R2
and R3 in state `FULL/BDR` and `FULL/DROTHER` respectively.

---

### Task 3: Exclude R3 from DR/BDR eligibility (priority 0)

- On R3 Gi0/0, set the OSPF priority to 0.
- Force a re-election on R3 so the change takes effect (the DR/BDR on the
  segment do not change -- R1 stays DR, R2 stays BDR -- but R3's own state
  must move to DROTHER with priority 0).

**Verification:** `show ip ospf interface gi0/0` on R3 must report
`State DROTHER, Priority 0`. On R1 and R2, `show ip ospf neighbor` must list
R3 with `Pri` column = 0. If you subsequently bounce R1's Gi0/0 (do not do
this as part of the lab -- just confirm mentally), R2 would become DR and a
new BDR would be elected from the remaining candidates; R3 could not be
elected at any step.

---

### Task 4: Convert the Area 1 and Area 2 transit links to point-to-point

- On R2 Gi0/1 and R4 Gi0/0 (the Area 1 transit), set the OSPF network type
  to point-to-point. Both sides must match.
- On R3 Gi0/1 and R5 Gi0/0 (the Area 2 transit), do the same.
- Do not change any timers -- the custom 5/20 on R2 Gi0/1 and R4 Gi0/0 from
  lab-00 must still match between the two peers.

**Verification:** `show ip ospf interface gi0/1` on R2 and R3 must report
`Network Type POINT_TO_POINT`; the `Designated Router` line must be absent
or `0.0.0.0`. `show ip ospf neighbor` on R2 must show R4 as `FULL/-` (no
DR/BDR role on a p2p interface). On R4 and R5, `show ip ospf interface
gi0/0` must mirror the p2p state. End-to-end, PC1 must still be able to
ping PC2 on both IPv4 and IPv6.

---

### Task 5: Confirm the LSDB reflects the new topology

- Re-run `show ip ospf database network` on R1 (or any router in Area 0).
  The Area 1 and Area 2 transit Type 2 LSAs must no longer exist.
- Run `show ip ospf database summary` on R1 and confirm Type 3 LSAs for the
  Area 1 and Area 2 prefixes (including 10.1.24.0/30, 192.168.1.0/24,
  10.2.35.0/30, 192.168.2.0/24) are still being generated by the ABRs.
- Re-run `show ip ospf database router` on R4 and R5 and confirm the transit
  link is now described as a point-to-point link (Link ID = neighbor RID)
  instead of a transit-to-DR link.

**Verification:** `show ip ospf database network` on any router must list
**only one** Type 2 LSA -- the 10.0.123.0 segment. Routing tables on R1, R4,
R5 must contain the expected `O` and `O IA` routes with no loss of
reachability.

---

## 6. Verification & Analysis

Every code block below uses inline `!` comments to mark the exact line or
value the student must confirm.

### Task 1 verification

```bash
R1# show ip ospf interface gi0/0
GigabitEthernet0/0 is up, line protocol is up
  Internet Address 10.0.123.1/24, Area 0
  Process ID 1, Router ID 1.1.1.1, Network Type BROADCAST, Cost: 1        ! ← default BROADCAST
  Transmit Delay is 1 sec, State DROTHER, Priority 1                      ! ← default prio 1
  Designated Router (ID) 3.3.3.3, Interface address 10.0.123.3            ! ← R3 wins by RID tiebreak
  Backup Designated router (ID) 2.2.2.2, Interface address 10.0.123.2     ! ← R2 is BDR

R1# show ip ospf neighbor
Neighbor ID     Pri   State           Dead Time   Address         Interface
2.2.2.2           1   FULL/BDR        00:00:38    10.0.123.2      Gi0/0    ! ← Pri=1 default
3.3.3.3           1   FULL/DR         00:00:35    10.0.123.3      Gi0/0    ! ← Pri=1 default

R1# show ip ospf database network
        OSPF Router with ID (1.1.1.1) (Process ID 1)
                Net Link States (Area 0)
Link ID         ADV Router      Age      Seq#       Checksum
10.0.123.3      3.3.3.3         42       0x80000001 0x...      ! ← Area 0 Type 2 (DR=R3)

        OSPF Router with ID (1.1.1.1) (Process ID 1)
                Summary Net Link States (Area 0)
...
```

### Task 2 verification (after priority + re-election)

```bash
R1# show ip ospf interface gi0/0
  ...
  State DR, Priority 255                                                   ! ← R1 now DR
  Designated Router (ID) 1.1.1.1, Interface address 10.0.123.1            ! ← R1 is DR

R2# show ip ospf interface gi0/0
  State BDR, Priority 200                                                  ! ← R2 now BDR

R1# show ip ospf neighbor
Neighbor ID     Pri   State           Dead Time   Address         Interface
2.2.2.2         200   FULL/BDR        00:00:35    10.0.123.2      Gi0/0    ! ← BDR
3.3.3.3           1   FULL/DROTHER    00:00:37    10.0.123.3      Gi0/0    ! ← demoted to DROTHER
```

### Task 3 verification (after R3 priority 0)

```bash
R3# show ip ospf interface gi0/0
  State DROTHER, Priority 0                                                 ! ← ineligible

R1# show ip ospf neighbor
Neighbor ID     Pri   State           Dead Time   Address         Interface
2.2.2.2         200   FULL/BDR        00:00:35    10.0.123.2      Gi0/0
3.3.3.3           0   FULL/DROTHER    00:00:33    10.0.123.3      Gi0/0    ! ← Pri=0

R1# show ip ospf interface gi0/0 | include Hello
  Hello due in 00:00:05
```

### Task 4 verification (after p2p conversion)

```bash
R2# show ip ospf interface gi0/1
  Internet Address 10.1.24.1/30, Area 1
  Process ID 1, Router ID 2.2.2.2, Network Type POINT_TO_POINT, Cost: 1   ! ← POINT_TO_POINT
  Transmit Delay is 1 sec, State POINT_TO_POINT                           ! ← no DR/BDR state
  Timer intervals configured, Hello 5, Dead 20, Wait 20, Retransmit 5     ! ← 5/20 preserved

R2# show ip ospf neighbor
Neighbor ID     Pri   State           Dead Time   Address         Interface
4.4.4.4           0   FULL/  -        00:00:17    10.1.24.2       Gi0/1    ! ← no DR/BDR role
1.1.1.1         255   FULL/DR         00:00:38    10.0.123.1      Gi0/0
3.3.3.3           0   FULL/DROTHER    00:00:35    10.0.123.3      Gi0/0

R3# show ip ospf interface gi0/1
  Network Type POINT_TO_POINT                                              ! ← p2p on Area 2 transit

PC1> ping 192.168.2.10
84 bytes from 192.168.2.10 icmp_seq=1 ttl=60 time=8.2 ms                  ! ← end-to-end OK

PC1> ping 2001:db8:2:2::10
80 bytes from 2001:db8:2:2::10 icmp_seq=1 ttl=60 time=8.5 ms              ! ← IPv6 also OK
```

### Task 5 verification (LSDB after conversion)

```bash
R1# show ip ospf database network
        OSPF Router with ID (1.1.1.1) (Process ID 1)
                Net Link States (Area 0)
Link ID         ADV Router      Age      Seq#       Checksum
10.0.123.1      1.1.1.1         35       0x80000002 0x...      ! ← only Area 0 Type 2 remains
                                                                ! ← ADV Router = R1 (the new DR)

R1# show ip ospf database | include Link Count|Summary
  Number of Links: 3                                                       ! ← down from 4 pre-conversion

R4# show ip ospf database router self-originate | include Link connected
  Link connected to: another Router (point-to-point)                       ! ← was "a Transit Network"
   (Link ID) Neighboring Router ID: 2.2.2.2
```

---

## 7. Verification Cheatsheet

### Priority & network-type configuration

```
interface <name>
 ip ospf priority <0-255>
 ip ospf network {broadcast | point-to-point | point-to-multipoint | non-broadcast}
```

| Command                                           | Purpose                                                     |
|---------------------------------------------------|-------------------------------------------------------------|
| `ip ospf priority 255`                            | Maximum priority; wins election unless another peer also has 255 (then RID). |
| `ip ospf priority 0`                              | Permanently ineligible for DR/BDR (forced DROTHER).         |
| `ip ospf network point-to-point`                  | Skip DR/BDR election; no Type 2 LSA; exactly one neighbor.  |
| `ip ospf network broadcast`                       | Default on Ethernet; DR/BDR election; Type 2 LSA.           |
| `clear ip ospf process`                           | Force re-election (disruptive -- all adjacencies flap).     |

> **Exam tip:** Priority 0 on one router does **not** force re-election of
> existing DRs/BDRs on the segment. It only changes that router's
> eligibility the next time an election happens. If you need a specific
> router to become DR immediately, you must also clear the process on the
> current DR or bounce its interface.

### Forcing re-election

```
clear ip ospf process
```

| Command                           | Purpose                                                          |
|-----------------------------------|------------------------------------------------------------------|
| `clear ip ospf process`           | Restart the OSPF process on this router; triggers re-election.   |
| `shutdown` + `no shutdown`        | Interface-scoped re-election; less disruptive than process clear.|

### Verification commands

| Command                                          | What to Look For                                                                 |
|--------------------------------------------------|----------------------------------------------------------------------------------|
| `show ip ospf interface brief`                   | Network type, priority, state, DR/BDR per interface (one line each).             |
| `show ip ospf interface <name>`                  | Full detail: hello/dead timers, DR/BDR IDs, transmit delay, cost.                |
| `show ip ospf neighbor`                          | Per-neighbor Pri column + `FULL/DR`, `FULL/BDR`, `FULL/DROTHER`, or `FULL/  -` (p2p). |
| `show ip ospf database network`                  | Type 2 LSAs only -- one per broadcast segment; empty/fewer after p2p conversion. |
| `show ip ospf database router`                   | Type 1 LSAs -- each transit link described as "point-to-point" or "transit".     |
| `show ip ospf database summary`                  | Type 3 LSAs -- ABR-generated; confirm inter-area prefixes still present.         |
| `show ip route ospf`                             | `O` (intra-area) and `O IA` (inter-area) routes -- must survive all changes.     |

### Neighbor state quick reference

| State                 | Meaning                                                                        |
|-----------------------|--------------------------------------------------------------------------------|
| `DOWN`                | No hellos received.                                                            |
| `INIT`                | Hello received but local router-ID not in neighbor's Hello yet.                |
| `2WAY/DROTHER`        | Bidirectional on a broadcast segment; DROTHERs stop here with each other.      |
| `EXSTART` / `EXCHANGE`| DBD negotiation. Stuck here often means MTU mismatch or network-type mismatch. |
| `LOADING`             | Sending/receiving LSRs.                                                        |
| `FULL/DR`             | Adjacency complete; peer is DR on the segment.                                 |
| `FULL/BDR`            | Adjacency complete; peer is BDR.                                               |
| `FULL/DROTHER`        | Adjacency complete; peer is a DROTHER (we are DR or BDR).                      |
| `FULL/  -`            | Adjacency complete on p2p; no DR/BDR role applies.                             |

### Common OSPF network-type failure causes

| Symptom                                             | Likely Cause                                                                |
|-----------------------------------------------------|-----------------------------------------------------------------------------|
| Neighbors stuck EXSTART/EXCHANGE                    | MTU mismatch **or** network-type mismatch (one broadcast, one p2p).         |
| Adjacency FULL but routes flap/reinstall repeatedly | Network-type mismatch -- one side still runs DR election that never converges. |
| Two DRs on the same segment                         | Duplex mismatch / broken switch CAM -- hellos only flowing one way.         |
| DR never changes after priority edit                | OSPF doesn't pre-empt. Clear the process or bounce the DR's interface.      |
| `show ip ospf neighbor` missing a peer completely   | Hello/dead timer mismatch, area mismatch, or authentication mismatch.       |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these first!

### Task 2: Force R1 DR, R2 BDR on Area 0

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1
interface GigabitEthernet0/0
 ip ospf priority 255
!
end
clear ip ospf process
```

</details>

<details>
<summary>Click to view R2 Configuration</summary>

```bash
! R2
interface GigabitEthernet0/0
 ip ospf priority 200
!
end
clear ip ospf process
```

</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ip ospf interface gi0/0
show ip ospf neighbor
```

</details>

### Task 3: R3 ineligible (priority 0)

<details>
<summary>Click to view R3 Configuration</summary>

```bash
! R3
interface GigabitEthernet0/0
 ip ospf priority 0
!
end
clear ip ospf process
```

</details>

### Task 4: Convert transits to point-to-point

<details>
<summary>Click to view R2 + R4 Configuration (Area 1 transit)</summary>

```bash
! R2
interface GigabitEthernet0/1
 ip ospf network point-to-point
!
end

! R4
interface GigabitEthernet0/0
 ip ospf network point-to-point
!
end
```

</details>

<details>
<summary>Click to view R3 + R5 Configuration (Area 2 transit)</summary>

```bash
! R3
interface GigabitEthernet0/1
 ip ospf network point-to-point
!
end

! R5
interface GigabitEthernet0/0
 ip ospf network point-to-point
!
end
```

</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ip ospf interface gi0/1     ! on R2, R3
show ip ospf interface gi0/0     ! on R4, R5
show ip ospf neighbor
show ip ospf database network
show ip ospf database router
```

</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. Inject the fault first, then
diagnose and fix using only `show` commands.

### Workflow

```bash
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>      # reset to known-good
python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>  # Ticket 1
# diagnose and fix using show commands only
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>      # restore
```

Scripts refuse to inject unless the device is in the solution state
(pre-flight check). Bypass with `--skip-preflight` only if you know why.

---

### Ticket 1 -- R2 and R4 can exchange pings but Area 1 routes keep flapping

A junior engineer reports that after a maintenance window the R2-R4
adjacency "looks fine" (`FULL`), ICMP between 10.1.24.1 and 10.1.24.2 works,
but R1 keeps losing and regaining the Area 1 routes every minute or so.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>`

**Success criteria:** R4 Gi0/0 network type matches R2 Gi0/1. `show ip ospf
database network` must list exactly one Type 2 LSA (the 10.0.123.0 segment).
R1 must have stable `O IA` routes for 10.1.24.0/30 and 192.168.1.0/24.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. On R2 and R4, run `show ip ospf interface gi0/1` and `show ip ospf
   interface gi0/0`. One side says `Network Type POINT_TO_POINT`, the other
   says `Network Type BROADCAST`.
2. On the broadcast side, `show ip ospf database network` shows a Type 2 LSA
   that shouldn't exist (the p2p side never originates one).
3. `show ip ospf neighbor` may still report FULL -- that's what makes this
   fault subtle. The mismatch causes intermittent SPF recomputation because
   one side advertises a transit network and the other a point-to-point
   link, which is inconsistent in the LSDB.

</details>

<details>
<summary>Click to view Fix</summary>

```bash
! R4
interface GigabitEthernet0/0
 ip ospf network point-to-point
!
end
```

After applying, re-check `show ip ospf database network` -- the spurious
Type 2 is gone within a few seconds of the next LSRefresh.

</details>

---

### Ticket 2 -- R3 advertises priority 255 on Area 0 but should be ineligible for DR/BDR

Ops has caught an audit mismatch on the Area 0 segment. The design calls
for R3 to be permanently excluded from DR/BDR election (`ip ospf priority
0`), but `show ip ospf neighbor` on R1 and R2 now reports R3's `Pri` column
as 255. R3 is still DROTHER today -- OSPF doesn't pre-empt the current DR
(R1) -- so nothing has broken yet. The problem is latent: the next time R1
reloads or its OSPF process clears, R3 will win the new election on RID
tie-break.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py --host <eve-ng-ip>`

**Success criteria:** R3 Gi0/0 priority restored to 0. `show ip ospf
neighbor` on R1 and R2 lists R3 with `Pri` = 0. `show ip ospf interface
gi0/0` on R3 reports `State DROTHER, Priority 0`. If you subsequently bounce
R1 Gi0/0 or clear R1's OSPF process, R2 (priority 200) must become DR --
never R3.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. On R1, run `show ip ospf neighbor`. R3's Pri column reads 255 -- wrong.
2. On R3, `show running-config interface gi0/0` confirms `ip ospf priority
   255` instead of the expected `ip ospf priority 0`.
3. `show ip ospf interface gi0/0` on R3 shows `State DROTHER, Priority 255`
   -- R3 is still DROTHER because OSPF does not pre-empt, but it is now
   eligible to win the next election that happens.

</details>

<details>
<summary>Click to view Fix</summary>

```bash
! R3
interface GigabitEthernet0/0
 ip ospf priority 0
!
end
clear ip ospf process
```

OSPF does not pre-empt -- the priority change alone will not move the DR
back to R1. The process clear on R3 forces re-election; R1 wins because R3
is now ineligible and R1's priority (255) beats R2's (200).

</details>

---

### Ticket 3 -- R1 reports only one neighbor on the Area 0 segment

Ops opens a P2 ticket: R1 `show ip ospf neighbor` lists only R2 (FULL/BDR).
R3 is not in the neighbor table at all, yet R3 is up, its Gi0/0 has the
right IP, and R2 and R3 still see each other normally.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py --host <eve-ng-ip>`

**Success criteria:** R1 Gi0/0 network type returned to broadcast. R1 must
see both R2 and R3 as neighbors; `show ip ospf database network` must list
exactly one Type 2 LSA for 10.0.123.0 with three attached routers.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. On R1, `show ip ospf interface gi0/0`. The network type now reads
   `POINT_TO_POINT` on the Area 0 segment -- wrong for a shared-segment
   broadcast link.
2. On R1, `show ip ospf neighbor` shows only R2 -- the router R1 happened
   to hit first via unicast once the p2p network type was applied.
3. R2 and R3 both still have broadcast; they continue to elect a DR
   (formerly R3 by RID, now still BDR/DR between each other) but R1 drops
   out of the election entirely.

</details>

<details>
<summary>Click to view Fix</summary>

```bash
! R1
interface GigabitEthernet0/0
 ip ospf network broadcast
!
end
clear ip ospf process
```

After the process clear, R1 re-enters the election with priority 255 and
reclaims DR; R2 stays BDR; R3 remains DROTHER.

</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] `setup_lab.py` applied cleanly on all 5 routers.
- [ ] Task 1: baseline DR/BDR recorded -- R3 DR, R2 BDR, R1 DROTHER via RID.
- [ ] Task 2: R1 Gi0/0 priority 255, R2 Gi0/0 priority 200 configured.
- [ ] Task 2: `show ip ospf interface gi0/0` on R1 reports `State DR`,
      on R2 reports `State BDR`.
- [ ] Task 3: R3 Gi0/0 priority 0 configured.
- [ ] Task 3: `show ip ospf neighbor` on R1 and R2 shows R3 with Pri=0.
- [ ] Task 4: R2 Gi0/1, R4 Gi0/0, R3 Gi0/1, R5 Gi0/0 all configured
      `ip ospf network point-to-point`.
- [ ] Task 4: `show ip ospf neighbor` on R2 and R3 shows the transit peer as
      `FULL/  -` (no DR/BDR on p2p).
- [ ] Task 5: `show ip ospf database network` on R1 lists exactly one Type 2
      LSA (10.0.123.0 shared segment).
- [ ] PC1 can ping PC2 on both IPv4 (192.168.2.10) and IPv6
      (2001:db8:2:2::10).

### Troubleshooting

- [ ] Ticket 1 injected, diagnosed from `show ip ospf interface` evidence,
      fixed by matching the network type on both ends.
- [ ] Ticket 2 injected, diagnosed from `show ip ospf interface gi0/0`,
      fixed by restoring priority 0 and forcing re-election on R3.
- [ ] Ticket 3 injected, diagnosed by noting R1 lost a neighbor after a
      network-type change, fixed by restoring broadcast on R1 Gi0/0.
- [ ] After each ticket, `apply_solution.py` returns to the full multi-area
      + network-type solution state without error.
