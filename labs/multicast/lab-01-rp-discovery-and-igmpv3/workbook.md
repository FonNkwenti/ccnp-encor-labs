# Lab 01 — RP Discovery Mechanisms and IGMPv3

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

**Exam Objective:** 3.3.d — Describe multicast protocols, such as RPF check, PIM SM, IGMP v2/v3, SSM, bidir, and MSDP (Multicast)

Lab-00 pinned the Rendezvous Point on every router with a single static statement. That works for three routers in a lab, but it fails at scale: adding a new router means touching every existing device, losing the RP means a manual edit rollout to swap addresses, and there is no failover. In real enterprises multicast planes use **dynamic RP discovery** so routers learn the RP automatically — either through Cisco's Auto-RP (since IOS 12.0) or the standards-based Bootstrap Router (BSR) protocol (RFC 5059). This lab configures both mechanisms back-to-back and ends in BSR state, which carries forward into the capstone. It closes with an IGMPv3 upgrade on the receiver LAN — a prerequisite for SSM in lab-02.

### Why Static RP Breaks at Scale

A static RP statement (`ip pim rp-address 2.2.2.2`) makes the RP address part of every router's configuration. Three failure modes appear as soon as the network grows:

| Problem | Consequence |
|---------|-------------|
| New router deployed | Manual statement must be pushed or it has no RP |
| RP hardware fails | Every router needs an edit to point at the replacement |
| Multi-RP partitioning | No mechanism to split group ranges across RPs |

Dynamic RP discovery solves all three: candidate RPs advertise themselves, routers learn the current mapping automatically, and group-to-RP assignments are negotiated.

### Auto-RP (Cisco Proprietary)

Auto-RP uses two well-known multicast groups:

| Group | Purpose | Sent by |
|-------|---------|---------|
| 224.0.1.39 | RP announcements | Candidate RPs (`ip pim send-rp-announce`) |
| 224.0.1.40 | RP discovery (winning RP-to-group map) | Mapping Agents (`ip pim send-rp-discovery`) |

The Mapping Agent collects announcements from all candidate RPs, runs an election (highest IP wins for overlapping group ranges), and floods the result on 224.0.1.40 so every router learns which RP serves which groups.

**The bootstrap paradox:** Auto-RP traffic is itself multicast, but PIM-SM requires an RP to forward groups. If no router knows the RP, 224.0.1.39/40 cannot flow. Cisco solves this with `ip pim autorp listener` — a command that causes 224.0.1.39/40 (and only those two groups) to flood in dense-mode style, reaching every router without needing an RP. Every non-candidate router in a PIM-SM domain should have this command.

**Why two Mapping Agents?** The baseline has R1 and R3 as MAs. One MA is sufficient; two gives redundancy. When two MAs run, both listen to announcements, both run the election independently, and both flood 224.0.1.40. Routers that receive multiple discoveries keep the most recent. The tradeoff is slightly more Auto-RP traffic; the benefit is continued RP distribution if one MA fails. Single-MA deployments are more common in compact networks.

IOS syntax:

```
! Candidate RP (announces self)
ip pim send-rp-announce Loopback0 scope 10

! Mapping Agent (publishes winning RP-to-group map)
ip pim send-rp-discovery Loopback0 scope 10

! Listener (flood Auto-RP groups in dense mode)
ip pim autorp listener
```

The `scope` value is TTL in hops — 10 means the announcement can cross up to ten routers before being dropped.

### BSR (RFC 5059, Standards-Based)

BSR replaces Auto-RP's flood-with-a-listener trick with **PIM hop-by-hop flooding**. BSR messages ride inside PIM packets (protocol number 103) and are forwarded hop-by-hop along the PIM adjacency mesh — no multicast group, no listener workaround.

The protocol has three roles:

| Role | Function | Command |
|------|----------|---------|
| BSR candidate | Participates in BSR election | `ip pim bsr-candidate Loopback0 <hash-mask>` |
| RP candidate | Advertises itself as a candidate RP to the elected BSR | `ip pim rp-candidate Loopback0` |
| Non-candidate router | Receives BSR messages, learns RP-to-group map | (no extra config — PIM-SM adjacency is enough) |

One router in the domain wins the BSR election (highest priority, then highest IP). That router collects candidate-RP messages, builds the RP set, and distributes it in periodic BSR messages. Every PIM router receives those messages through normal PIM adjacencies.

**Hash-mask length:** The last argument of `ip pim bsr-candidate` (e.g., `0` or `30`) determines how multicast groups are distributed across candidate RPs. With two or more RPs, a hash-mask length of 30 spreads groups evenly; with a single RP it does not matter and 0 is acceptable. Cargo-culting `0` into a multi-RP design causes uneven load — always match hash-mask-length to the RP count.

BSR is fully interoperable across vendors; Auto-RP is Cisco-only. In greenfield multi-vendor designs BSR is the default choice.

### IGMPv2 vs IGMPv3

IGMP is the host-to-router protocol that reports group membership. The receiver LAN speaks IGMP; the router-to-router cloud speaks PIM. Upgrading from v2 to v3 changes only the receiver-LAN interface.

| Feature | IGMPv2 (RFC 2236) | IGMPv3 (RFC 3376) |
|---------|-------------------|-------------------|
| Group join | Join (*,G) only | Join (*,G) or (S,G) |
| Source filtering | No | Yes — INCLUDE/EXCLUDE source lists |
| Report destination | 224.0.0.2 (leave), group address (report) | 224.0.0.22 (all IGMPv3 routers) |
| SSM support | No | Required |
| Membership Query | Group-specific | Group-and-source-specific |

Version negotiation on Cisco IOS is governed by the lowest common version on the segment. If any host reports v2, the router falls back. For SSM (lab-02) the receiver interface must be pinned at v3.

IOS syntax:

```
interface GigabitEthernet0/2
 ip igmp version 3
 ip igmp join-group 239.1.1.1
```

`ip igmp join-group` makes the router itself act as a host (it joins the group and processes traffic in the control plane). This is how labs simulate a receiver when no real host is present — a VPCS node cannot issue IGMP reports, so R3 joining its own interface creates the (*,G) state.

### Skills this lab develops

| Skill | Description |
|-------|-------------|
| Dynamic RP discovery | Configure Auto-RP and BSR and understand when each is appropriate |
| Migration sequencing | Decommission one RP mechanism cleanly before introducing another |
| IGMP version negotiation | Upgrade receiver interfaces to IGMPv3 and verify version state |
| Control-plane verification | Use `show ip pim rp mapping` / `bsr-router` / `autorp` to confirm RP-learning before sending traffic |
| Multi-protocol compare | Contrast Cisco proprietary Auto-RP against standards-based BSR |

---

## 2. Topology & Scenario

**Scenario.** Acme Corp's IP video platform uses the three-router triangle (R1/R2/R3) from lab-00. Operations reviewed the static RP design and flagged two problems: the RP address is hard-coded on every router (painful to change), and there is no failover if R2 dies. Your task is to migrate the network from static RP to dynamic RP discovery. First prototype Auto-RP to prove the concept, then cut over to BSR for the standards-based production deployment. While you're on the receiver LAN, upgrade it to IGMPv3 — a prerequisite for the SSM work planned in the next sprint.

```
                    ┌─────────────────┐
                    │       R1        │
                    │  Source-side    │
                    │ Lo0: 1.1.1.1    │
                    │ Auto-RP MA      │
                    └──┬───────────┬──┘
               Gi0/0   │           │   Gi0/1
           10.1.12.1/30│           │10.1.13.1/30
                       │           │
           10.1.12.2/30│           │10.1.13.2/30
               Gi0/0   │           │   Gi0/1
            ┌──────────┴──┐     ┌──┴─────────────┐
            │     R2      │     │       R3       │
            │  RP (BSR)   │     │  Receiver-side │
            │Lo0: 2.2.2.2 │     │ Lo0: 3.3.3.3   │
            │BSR+RP cand. │     │ Auto-RP MA     │
            └──────┬──────┘     └──────┬─────────┘
                   │Gi0/1              │Gi0/0
             10.1.23.1/30         10.1.23.2/30
                   └────────────────────┘
                        10.1.23.0/30
                            (L2)

      ┌───────────────┐                       ┌───────────────┐
      │  PC1 (VPCS)   │                       │  PC2 (VPCS)   │
      │ 10.1.1.10/24  │── R1 Gi0/2 ──  R3 Gi0/2 ──│ 10.1.3.10/24 │
      │ Source LAN    │   10.1.1.1/24    10.1.3.1/24 │ Receiver LAN │
      └───────────────┘                       └───────────────┘
```

> **Key dependency patterns:**
> - All three routers form a full PIM-SM adjacency mesh over the core triangle — required for BSR flooding.
> - OSPF provides the unicast RIB that RPF checks depend on; it is already converged from lab-00.
> - PC2 is a VPCS node (no IGMP reports); R3 Gi0/2 joins the group itself via `ip igmp join-group` to simulate a receiver.

---

## 3. Hardware & Environment Specifications

### EVE-NG Cabling

| Link | From | Interface | To | Interface | Subnet |
|------|------|-----------|----|-----------|--------|
| L1 | R1 | Gi0/0 | R2 | Gi0/0 | 10.1.12.0/30 |
| L2 | R2 | Gi0/1 | R3 | Gi0/0 | 10.1.23.0/30 |
| L3 | R1 | Gi0/1 | R3 | Gi0/1 | 10.1.13.0/30 |
| L4 | R1 | Gi0/2 | PC1 | eth0 | 10.1.1.0/24 |
| L5 | R3 | Gi0/2 | PC2 | eth0 | 10.1.3.0/24 |

### Console Access Table

| Device | Port | Connection Command |
|--------|------|--------------------|
| R1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R3 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| PC1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| PC2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |

### Platform

IOSv 15.9(3)M6 for R1/R2/R3. VPCS for PC1/PC2 (lab-02 swaps VPCS for Alpine 3.18 per `spec-linux-hosts-delta.md`).

---

## 4. Base Configuration

The `initial-configs/` directory contains the **lab-00 end-state**:

- OSPF area 0 on all three routers — converged, all loopbacks and transit subnets reachable
- IPv4 addressing per the topology above
- `ip multicast-routing` enabled on R1/R2/R3
- `ip pim sparse-mode` on every router interface (Loopback0 plus Gi0/0, Gi0/1, and where present Gi0/2)
- **Static RP: `ip pim rp-address 2.2.2.2`** on all three routers — this is what you will replace

PC1 and PC2 have static IPv4 addresses and default gateways configured.

### What is NOT pre-loaded (student builds)

- Auto-RP candidate RP role
- Auto-RP Mapping Agent role
- Auto-RP listener
- BSR candidate role
- BSR RP candidate role
- IGMPv3 on the receiver LAN
- Persistent IGMP join on R3 Gi0/2

---

## 5. Lab Challenge: Core Implementation

Work through the tasks in order. Each task builds on the previous one, and the network transitions from static RP → Auto-RP → BSR → IGMPv3. All verification in Tasks 2–5 is control-plane; data-plane traffic generation is Task 7 after the receiver is fully configured.

### Task 1: Decommission the Static RP

- Remove the static RP statement from all three routers so that no static mapping remains.
- No new command replaces it yet — the PIM domain will have no RP for the duration of this task.

**Verification:** `show ip pim rp mapping` on R1, R2, and R3 must show no RP mapping (empty output or "This system is a candidate RP" only after later tasks).

---

### Task 2: Configure Auto-RP

- On R2: advertise Loopback0 as a candidate RP for all groups with TTL scope 10.
- On R1: run the Mapping Agent role on Loopback0 with TTL scope 10.
- On R3: run the Mapping Agent role on Loopback0 with TTL scope 10 (two MAs for redundancy — see theory notes).
- On all three routers: enable the Auto-RP listener so the 224.0.1.39 and 224.0.1.40 groups flow in the absence of a PIM-SM RP.

**Verification:** `show ip pim rp mapping` on all three routers must list RP 2.2.2.2 with "Info source: <MA-IP>, via Auto-RP". `show ip pim autorp` must show "RP Announce / RP Discovery: enabled" on the expected routers.

---

### Task 3: Validate Auto-RP Control-Plane Convergence

- On R1 and R3, confirm the RP learned matches what R2 announced.
- Observe the Auto-RP cache age to confirm announcements are refreshing (default every 60 seconds).
- No multicast data traffic is sent in this task — you are validating RP-learning only.

**Verification:** `show ip pim rp mapping` "Uptime" increments, "Expires" does not drop to zero. Running `show ip pim autorp` twice a minute apart should show the counters increasing.

---

### Task 4: Migrate from Auto-RP to BSR

- On R1, R2, and R3: remove the Auto-RP configuration added in Task 2 (`send-rp-announce`, `send-rp-discovery`, `autorp listener`).
- On R2: configure Loopback0 as a BSR candidate with hash-mask length 0 (single RP in the domain).
- On R2: configure Loopback0 as a PIM RP candidate (this is what the BSR will distribute).
- R1 and R3 need no new commands — they learn the RP from BSR messages received over the existing PIM adjacencies.

**Verification:** `show ip pim bsr-router` on R1 and R3 must show R2 (2.2.2.2) as the elected BSR. `show ip pim rp mapping` on R1/R3 must show RP 2.2.2.2 with "Info source: 2.2.2.2, via bootstrap".

---

### Task 5: Validate BSR Control-Plane Convergence

- Confirm BSR messages are flooding hop-by-hop by observing the "Uptime" and "Expires" counters on R1 and R3.
- Confirm no Auto-RP state remains — `show ip pim autorp` should report the feature disabled.

**Verification:** `show ip pim bsr-router` shows the current BSR is 2.2.2.2 with a stable uptime. `show ip pim rp mapping` lists only the bootstrap-learned RP (no `via Auto-RP` entries).

---

### Task 6: Upgrade the Receiver LAN to IGMPv3

- On R3 Gi0/2: enable IGMP version 3.
- On R3 Gi0/2: configure a static host join for group 239.1.1.1 so R3 itself simulates a receiver (the VPCS PC2 cannot generate IGMP reports).

**Verification:** `show ip igmp interface GigabitEthernet0/2` must report "Current IGMP host version" and "Current IGMP router version" as 3. `show ip igmp groups GigabitEthernet0/2` must list 239.1.1.1 as a v3 member.

---

### Task 7: End-to-End Data-Plane Test

- From R1, send a multicast ping to 239.1.1.1 sourced from Gi0/2 (the source LAN interface) with a repeat count of 50.
- Verify the (*,G) and (S,G) state on R2 (the RP) and R3 (the receiver).
- Confirm the SPT switchover: R3's (S,G) entry should replace shared-tree forwarding with source-tree forwarding after the first packets arrive.

**Verification:** `show ip mroute 239.1.1.1` on R2 shows (*, 239.1.1.1) with incoming interface Null / OIL pointing toward R3. `show ip mroute 239.1.1.1` on R3 shows both (*, 239.1.1.1) rooted at RP 2.2.2.2 and (10.1.1.1, 239.1.1.1) with RPF neighbor 10.1.13.1 (direct R1-R3 link — shortest path).

---

## 6. Verification & Analysis

### Task 1 — Static RP removed

```bash
R1# show ip pim rp mapping
PIM Group-to-RP Mappings

R1#                                               ! ← empty output confirms no RP mapping
```

### Task 2 — Auto-RP active

```bash
R2# show ip pim autorp
AutoRP Information:
  AutoRP is enabled.
  RP Discovery packet MTU is 0.
  224.0.1.40 is used as the discovery group.
  AutoRP groups over sparse mode interface is enabled

  PIM AutoRP Statistics: Sent/Received
  RP Announce: 12/0, RP Discovery: 0/0                ! ← R2 is announcing as RP candidate

R1# show ip pim autorp
AutoRP Information:
  AutoRP is enabled.
  RP Discovery packet MTU is 0.
  224.0.1.40 is used as the discovery group.
  AutoRP groups over sparse mode interface is enabled

  PIM AutoRP Statistics: Sent/Received
  RP Announce: 0/12, RP Discovery: 8/0                ! ← R1 is receiving announces, sending discovery (MA role)

R1# show ip pim rp mapping
PIM Group-to-RP Mappings
This system is an RP-mapping agent (Loopback0)

Group(s) 224.0.0.0/4
  RP 2.2.2.2 (?), v2v1
    Info source: 2.2.2.2 (?), elected via Auto-RP     ! ← RP 2.2.2.2 discovered via Auto-RP
         Uptime: 00:01:23, expires: 00:02:37
```

### Task 4 — BSR active

```bash
R1# show ip pim bsr-router
PIMv2 Bootstrap information
  BSR address: 2.2.2.2 (?)                            ! ← R2 elected as BSR
  Uptime:      00:00:41, BSR Priority: 0, Hash mask length: 0
  Expires:     00:01:49
  This system is a candidate RP-agent (Loopback0)     ! ← (seen on R2 only)

R3# show ip pim rp mapping
PIM Group-to-RP Mappings

Group(s) 224.0.0.0/4
  RP 2.2.2.2 (?), v2
    Info source: 2.2.2.2 (?), via bootstrap, priority 0, holdtime 150
                                                      ! ← "via bootstrap" confirms BSR-learned
         Uptime: 00:01:12, expires: 00:02:07
```

### Task 6 — IGMPv3 on receiver LAN

```bash
R3# show ip igmp interface GigabitEthernet0/2
GigabitEthernet0/2 is up, line protocol is up
  Internet address is 10.1.3.1/24
  IGMP is enabled on interface
  Current IGMP host version is 3                      ! ← must be 3
  Current IGMP router version is 3                    ! ← must be 3
  IGMP query interval is 60 seconds
  ...

R3# show ip igmp groups GigabitEthernet0/2
IGMP Connected Group Membership
Group Address    Interface                Uptime    Expires   Last Reporter   Group Accounted
239.1.1.1        GigabitEthernet0/2       00:00:47  stopped   10.1.3.1        ! ← v3, locally joined
```

### Task 7 — Data-plane forwarding via BSR-discovered RP

```bash
R1# ping 239.1.1.1 repeat 50 source GigabitEthernet0/2
Type escape sequence to abort.
Sending 50, 100-byte ICMP Echos to 239.1.1.1, timeout is 2 seconds:
Packet sent with a source address of 10.1.1.1
Reply to request 0 from 10.1.3.1, 12 ms                ! ← R3 (joined receiver) replies

R3# show ip mroute 239.1.1.1
(*, 239.1.1.1), 00:01:47/stopped, RP 2.2.2.2, flags: SJCL
  Incoming interface: GigabitEthernet0/0, RPF nbr 10.1.23.1    ! ← via RP (R2)
  Outgoing interface list:
    GigabitEthernet0/2, Forward/Sparse, 00:01:47/00:02:47

(10.1.1.1, 239.1.1.1), 00:00:14/00:02:45, flags: LJT
  Incoming interface: GigabitEthernet0/1, RPF nbr 10.1.13.1    ! ← SPT switchover to direct R1-R3 link
  Outgoing interface list:
    GigabitEthernet0/2, Forward/Sparse, 00:00:14/00:02:47
```

---

## 7. Verification Cheatsheet

### Auto-RP Configuration

```
! Candidate RP (R2)
ip pim send-rp-announce <interface> scope <ttl>

! Mapping Agent (R1, R3)
ip pim send-rp-discovery <interface> scope <ttl>

! All non-candidate routers
ip pim autorp listener
```

| Command | Purpose |
|---------|---------|
| `ip pim send-rp-announce Lo0 scope 10` | Advertise self as candidate RP on 224.0.1.39 |
| `ip pim send-rp-discovery Lo0 scope 10` | Run as Mapping Agent, publish RP set on 224.0.1.40 |
| `ip pim autorp listener` | Forward 224.0.1.39/40 in dense mode (solves bootstrap paradox) |

> **Exam tip:** Auto-RP listener is mandatory on every non-candidate router when the PIM domain is sparse-only. Forgetting it is the #1 Auto-RP failure.

### BSR Configuration

```
! BSR candidate + RP candidate (same router in simple designs)
ip pim bsr-candidate <interface> <hash-mask-length> [priority]
ip pim rp-candidate <interface> [group-list <acl>]
```

| Command | Purpose |
|---------|---------|
| `ip pim bsr-candidate Lo0 0` | Compete for BSR role with hash-mask length 0 |
| `ip pim bsr-candidate Lo0 30` | Cisco-typical hash-mask length for multi-RP designs |
| `ip pim rp-candidate Lo0` | Offer self as a candidate RP to the elected BSR |

> **Exam tip:** Hash-mask length matters only when two or more RP candidates serve overlapping groups. Single-RP domains can use 0; multi-RP designs should use 30. Do not cargo-cult 0 into production.

### IGMP Version and Join

```
interface <interface>
 ip igmp version {2 | 3}
 ip igmp join-group <group>
```

| Command | Purpose |
|---------|---------|
| `ip igmp version 3` | Pin IGMP to v3 (required for SSM) |
| `ip igmp join-group 239.1.1.1` | Router acts as a host receiver for the group |
| `ip igmp static-group 239.1.1.1` | Router forwards the group without processing traffic locally |

> **Exam tip:** `join-group` and `static-group` look similar but behave differently. `join-group` puts the router in the control path — it processes packets. `static-group` just adds an OIL entry. SSM labs use `static-group source-list` for source-specific joins.

### Verification Commands

| Command | What to Look For |
|---------|------------------|
| `show ip pim rp mapping` | RP address + "via Auto-RP" or "via bootstrap" — confirms dynamic discovery |
| `show ip pim autorp` | Announce/Discovery counters incrementing |
| `show ip pim bsr-router` | Elected BSR, uptime, priority, hash-mask length |
| `show ip igmp interface <int>` | Current IGMP router version (must be 3 after upgrade) |
| `show ip igmp groups <int>` | Group 239.1.1.1 present on the receiver interface |
| `show ip mroute 239.1.1.1` | (*,G) via RP and (S,G) via shortest path after SPT switchover |

### Common RP-Discovery Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| Auto-RP: no RP learned on any router | `ip pim autorp listener` missing — 224.0.1.40 drops at first non-candidate hop |
| Auto-RP: RP learned on some routers, not others | TTL scope too low for the topology diameter |
| Auto-RP: wrong RP elected | Candidate RP with higher IP is reachable (election rule = highest RP-address) |
| BSR: `show ip pim bsr-router` shows no BSR | `ip pim bsr-candidate` missing, or PIM adjacency broken on the path |
| BSR: BSR elected but no RP mapping | `ip pim rp-candidate` missing — BSR distributes "no RPs" |
| IGMP: reports ignored | IGMP version mismatch between router and host, or snooping dropping traffic on intermediate L2 |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Task 1: Decommission Static RP

<details>
<summary>Click to view Configuration (all routers)</summary>

```bash
! R1, R2, R3 — identical
no ip pim rp-address 2.2.2.2
```
</details>

### Task 2: Configure Auto-RP

<details>
<summary>Click to view R2 Configuration (Candidate RP)</summary>

```bash
! R2
ip pim send-rp-announce Loopback0 scope 10
ip pim autorp listener
```
</details>

<details>
<summary>Click to view R1 Configuration (Mapping Agent)</summary>

```bash
! R1
ip pim send-rp-discovery Loopback0 scope 10
ip pim autorp listener
```
</details>

<details>
<summary>Click to view R3 Configuration (Mapping Agent)</summary>

```bash
! R3
ip pim send-rp-discovery Loopback0 scope 10
ip pim autorp listener
```
</details>

<details>
<summary>Click to view Verification</summary>

```bash
show ip pim autorp
show ip pim rp mapping
```
</details>

### Task 4: Migrate to BSR

<details>
<summary>Click to view R1 Configuration (remove Auto-RP)</summary>

```bash
! R1
no ip pim send-rp-discovery Loopback0 scope 10
no ip pim autorp listener
```
</details>

<details>
<summary>Click to view R2 Configuration (remove Auto-RP, add BSR)</summary>

```bash
! R2
no ip pim send-rp-announce Loopback0 scope 10
no ip pim autorp listener
ip pim bsr-candidate Loopback0 0
ip pim rp-candidate Loopback0
```
</details>

<details>
<summary>Click to view R3 Configuration (remove Auto-RP)</summary>

```bash
! R3
no ip pim send-rp-discovery Loopback0 scope 10
no ip pim autorp listener
```
</details>

<details>
<summary>Click to view Verification</summary>

```bash
show ip pim bsr-router
show ip pim rp mapping
```
</details>

### Task 6: IGMPv3 on Receiver LAN

<details>
<summary>Click to view R3 Configuration</summary>

```bash
! R3
interface GigabitEthernet0/2
 ip igmp version 3
 ip igmp join-group 239.1.1.1
```
</details>

<details>
<summary>Click to view Verification</summary>

```bash
show ip igmp interface GigabitEthernet0/2
show ip igmp groups GigabitEthernet0/2
```
</details>

### Task 7: End-to-End Data-Plane Test

<details>
<summary>Click to view Traffic Generation and Verification</summary>

```bash
! From R1 — source multicast ping
R1# ping 239.1.1.1 repeat 50 source GigabitEthernet0/2

! Immediately check mroute state on R2 (RP) and R3 (receiver)
R2# show ip mroute 239.1.1.1
R3# show ip mroute 239.1.1.1
R3# show ip rpf 10.1.1.1
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

### Ticket 1 — Branch Routers Report No RP Mapping

After you completed the BSR migration, operations verified `show ip pim rp mapping` on all three routers and wrote acceptance notes. Overnight a maintenance window ran and this morning R1 and R3 both show `PIM Group-to-RP Mappings` with no entries. R2 itself still reports normally. Multicast to 239.1.1.1 has stopped reaching PC2.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py`

**Success criteria:** `show ip pim rp mapping` on R1 and R3 shows RP 2.2.2.2 learned via bootstrap, and `ping 239.1.1.1 repeat 5 source Gi0/2` from R1 reaches R3's join-group.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `show ip pim rp mapping` on R1 and R3 → empty.
2. `show ip pim bsr-router` on R1 → no BSR address, or expired BSR.
3. `show ip pim bsr-router` on R2 → may show "This system is a candidate BSR" but there is no receiver for its messages.
4. `show ip pim neighbor` on R2 → confirms PIM adjacency is UP.
5. `show running-config | include pim` on R2 → inspect BSR and RP candidate lines.
6. Identify which BSR-related command has been removed on R2.
</details>

<details>
<summary>Click to view Fix</summary>

The BSR candidate or RP candidate command is missing on R2. The network still has PIM neighbors, so BSR flooding works the moment R2 generates messages again. Reapply on R2:

```bash
R2(config)# ip pim bsr-candidate Loopback0 0
R2(config)# ip pim rp-candidate Loopback0
```

Verify:

```bash
R1# show ip pim bsr-router      ! ← must show 2.2.2.2 within 60s
R1# show ip pim rp mapping      ! ← RP 2.2.2.2 via bootstrap
```
</details>

---

### Ticket 2 — Receiver LAN Sees IGMP Queries but Reports Are Ignored

R3 reports `show ip igmp groups Gi0/2` missing the 239.1.1.1 entry. The interface is up, BSR is healthy, and R1 can ping R3 unicast without issue. On R3, `debug ip igmp` shows membership reports being received but immediately discarded. The operations team suspects an IGMP version mismatch introduced by a config export that overwrote interface settings.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py`

**Success criteria:** `show ip igmp interface Gi0/2` on R3 shows IGMP host version 3 and router version 3. `show ip igmp groups Gi0/2` lists 239.1.1.1.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `show ip igmp interface GigabitEthernet0/2` → note the "Current IGMP router version" value.
2. `show running-config interface GigabitEthernet0/2` → look for `ip igmp version <n>`.
3. If version is 2, the IGMPv3 membership reports from the self-join are being rejected as malformed.
</details>

<details>
<summary>Click to view Fix</summary>

Restore IGMPv3 on the receiver interface:

```bash
R3(config)# interface GigabitEthernet0/2
R3(config-if)# ip igmp version 3
```

Verify:

```bash
R3# show ip igmp interface GigabitEthernet0/2    ! ← router version 3
R3# show ip igmp groups GigabitEthernet0/2       ! ← 239.1.1.1 present
```
</details>

---

### Ticket 3 — BSR Election Succeeds but No RP Is Distributed

R1 and R3 both show a valid BSR in `show ip pim bsr-router` — R2 is elected, uptime is stable, holdtime is counting down normally. Yet `show ip pim rp mapping` on R1 and R3 is empty. Multicast pings from R1 hit R2 but never propagate to R3. Operations labeled this "BSR works, multicast doesn't" and escalated.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py`

**Success criteria:** `show ip pim rp mapping` on R1 and R3 shows RP 2.2.2.2 via bootstrap. End-to-end ping from R1 to 239.1.1.1 reaches R3.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `show ip pim bsr-router` on R1/R3 → BSR is valid (rules out PIM adjacency issues).
2. `show ip pim rp mapping` on R1/R3 → empty.
3. The BSR is distributing an empty RP-set — there is no candidate RP in the domain.
4. `show running-config | include pim` on R2 → look for `ip pim rp-candidate`.
5. BSR and RP-candidate are independent commands. BSR carries messages; RP-candidate tells BSR what to carry. Missing the latter means BSR floods "no RPs" (which is legal).
</details>

<details>
<summary>Click to view Fix</summary>

Reapply the RP candidate on R2:

```bash
R2(config)# ip pim rp-candidate Loopback0
```

Verify:

```bash
R1# show ip pim rp mapping      ! ← RP 2.2.2.2 via bootstrap
R1# ping 239.1.1.1 repeat 5 source GigabitEthernet0/2
```
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] Static RP statement removed from R1, R2, R3 (Task 1)
- [ ] Auto-RP Candidate RP configured on R2 with Loopback0 and scope 10 (Task 2)
- [ ] Auto-RP Mapping Agent configured on R1 and R3 with Loopback0 and scope 10 (Task 2)
- [ ] `ip pim autorp listener` configured on R1, R2, R3 (Task 2)
- [ ] `show ip pim rp mapping` on R1/R3 shows RP 2.2.2.2 via Auto-RP (Task 3)
- [ ] Auto-RP commands removed from R1, R2, R3 (Task 4)
- [ ] `ip pim bsr-candidate Loopback0 0` configured on R2 (Task 4)
- [ ] `ip pim rp-candidate Loopback0` configured on R2 (Task 4)
- [ ] `show ip pim bsr-router` on R1/R3 shows BSR 2.2.2.2 (Task 5)
- [ ] `show ip pim rp mapping` on R1/R3 shows RP 2.2.2.2 via bootstrap (Task 5)
- [ ] `ip igmp version 3` configured on R3 Gi0/2 (Task 6)
- [ ] `ip igmp join-group 239.1.1.1` configured on R3 Gi0/2 (Task 6)
- [ ] `show ip igmp interface Gi0/2` reports router version 3 (Task 6)
- [ ] Multicast ping from R1 to 239.1.1.1 succeeds and R3 shows (*,G) and (S,G) in `show ip mroute 239.1.1.1` (Task 7)

### Troubleshooting

- [ ] Ticket 1 — Branch routers report no RP mapping (resolved)
- [ ] Ticket 2 — Receiver LAN sees IGMP queries but reports are ignored (resolved)
- [ ] Ticket 3 — BSR election succeeds but no RP is distributed (resolved)
