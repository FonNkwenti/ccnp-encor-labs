# Multicast Comprehensive Troubleshooting -- Capstone II

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

**Exam Objective:** 350-401 blueprint bullet 3.3.d -- *Describe and implement
multicast protocols (PIM-SM, PIM Bidirectional, SSM, RP discovery, MSDP)* --
applied in a full fault-diagnosis context spanning every sub-topic from labs
00-03.

This is the final multicast capstone. The network ships pre-broken: six
independent faults have been injected across R2, R3, and R4 and span every
sub-topic covered in the chapter (PIM-SM adjacency, BSR-based RP discovery,
SSM with IGMPv3, Bidirectional PIM, MSDP peering, and PIM-domain fencing
with `ip pim bsr-border`). Your job is to diagnose each symptom from `show`
commands alone and restore full multicast operation for all three modes
without introducing any new faults.

### Systematic Multicast Troubleshooting Methodology

Multicast failures look chaotic at first -- "nothing works" is a common
complaint. The reality is almost always one of a handful of root causes.
Work down the layers below; skipping one is how engineers waste hours.

| Layer | Question | Key Command |
|-------|----------|-------------|
| 1. Multicast enabled | Is `ip multicast-routing` globally on? | `show run | include multicast-routing` |
| 2. PIM on interface | Is `ip pim sparse-mode` on every transit interface? | `show ip pim interface` |
| 3. PIM neighbor | Do the expected PIM neighbors exist? | `show ip pim neighbor` |
| 4. RP mapping | Does every router know the RP for the group? | `show ip pim rp mapping` |
| 5. IGMP | Is the receiver LAN seeing joins? | `show ip igmp groups`, `show ip igmp interface` |
| 6. RPF | Does RPF toward the source/RP succeed? | `show ip rpf <source>`, `show ip mroute <G>` |
| 7. Forwarding | Is there an OIL entry with a non-zero packet counter? | `show ip mroute <G> count` |
| 8. MSDP | Is the SA cache populated between inter-domain RPs? | `show ip msdp peer`, `show ip msdp sa-cache` |

### Fault Categories You Will See

Every fault in this lab maps to exactly one of these categories. Learning to
name the category from the symptom is half the battle.

| Category | Typical Symptom |
|----------|-----------------|
| PIM adjacency missing | `show ip pim neighbor` missing an expected peer on one segment |
| RP mapping missing | `show ip pim rp mapping` has no entry for a group range |
| RPF fail (`ip mroute` override) | `show ip rpf <src>` shows `RPF type: mroute` pointing at wrong interface; unicast looks healthy |
| IGMP static-group missing (SSM) | No `(S,G)` mroute ever forms; SSM traffic arrives but no state |
| MSDP session stuck | `show ip msdp peer` shows Inactive/Listen; SA cache empty |
| BSR domain leak | `show ip pim bsr-router` on a border router shows the foreign-domain BSR |

### RPF -- The Multicast Trap Most Engineers Fall For

Unicast routing determines where packets go; multicast RPF determines where
packets are **allowed to arrive from**. The RPF lookup can be redirected
independently of unicast using `ip mroute`, which populates the multicast
RPF table only and leaves the unicast RIB untouched:

```
  R3 OSPF route:  10.1.1.0/24 via 10.1.13.1 (Gi0/1, toward R1)   ! unicast path -- packets arrive here
  R3 ip mroute:   10.1.1.0/24 RPF via 4.4.4.4 (Gi0/3, toward R4) ! multicast RPF table only
  → RPF lookup returns Gi0/3, packets arrive on Gi0/1 → RPF fail → drop
```

`ip mroute` is the textbook example of an RPF trap that leaves unicast
completely healthy (pings succeed, OSPF converged, `show ip route`
unchanged) while silently black-holing multicast. `show ip rpf <source>`
with `RPF type: mroute` is the give-away. The fix is to remove the bad
`ip mroute` so RPF falls back to the unicast RIB.

### BSR-Border Directionality

`ip pim bsr-border` on an interface blocks BSR messages in **both
directions**. To fence a domain, it suffices to configure it on **either end**
of the inter-domain link -- but if both ends lose it, BSR traffic flows
freely. The symptom is subtle: unicast and PIM still work, but a border
router starts learning the foreign domain's RPs via BSR. Dynamic RP learned
via BSR **overrides** a statically configured RP (unless `override` is
specified on the static), so the fault can silently redirect entire group
ranges.

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| Symptom-to-fault mapping | Translate a `show` observation into a hypothesis about the misconfiguration |
| Layer-by-layer isolation | Work from `ip multicast-routing` up to forwarding, never skipping a layer |
| Concurrent-fault diagnosis | Resolve multiple independent faults without regressing one while fixing another |
| RPF vs. unicast discipline | Recognize when a healthy unicast path still breaks multicast |
| RP-discovery tracing | Follow a group's RP from `rp mapping` back to its BSR origin |
| MSDP session diagnosis | Distinguish TCP-up/no-SAs from TCP-never-opened states |

---

## 2. Topology & Scenario

```
                    ┌─────────────────┐
                    │       R1        │
                    │  Source Edge    │
                    │ Lo0: 1.1.1.1    │
                    └──┬───────┬──────┘
                 Gi0/0 │       │ Gi0/1
         10.1.12.1/30  │       │  10.1.13.1/30
                       │       │
                       │       │
         10.1.12.2/30  │       │  10.1.13.2/30
                 Gi0/0 │       │ Gi0/1
              ┌────────┴───┐ ┌─┴────────────┐
              │    R2      │ │      R3      │
              │ BSR + RP   │─│ Receiver DR  │
              │Lo0:2.2.2.2 │ │Lo0:3.3.3.3   │
              └──┬─────────┘ └─┬───────┬────┘
           Gi0/2 │    10.1.23  │ Gi0/0 │ Gi0/2
      10.1.24.1/30│ (L2 link)  │       │ 10.1.3.1/24
                  │            │       │  (Rcvr LAN)
                  │  ==PIM DOMAIN BORDER==│
       10.1.24.2/30│            │10.1.34.2/30
              Gi0/0│            │Gi0/3
              ┌────┴────────────┴────┐
              │         R4           │
              │  Separate Domain     │
              │  Static RP: self     │
              │  Lo0: 4.4.4.4        │
              └──────────────────────┘
```

**Multicast design (reference end-state):**

- Main PIM domain: R1, R2, R3
  - BSR: R2 (Lo0 = 2.2.2.2)
  - ASM RP: R2 Lo0 for 239.1.1.0/24
  - Bidir RP: R2 Lo0 for 239.2.2.0/24
  - SSM range: 232.1.1.0/24 (IGMPv3 on R3 Gi0/2)
- Separate PIM domain: R4
  - Static RP: 4.4.4.4 (self)
- Inter-domain link: L6 (R2 Gi0/2 ↔ R4 Gi0/0) and L7 (R3 Gi0/3 ↔ R4 Gi0/1)
  - Both links fenced with `ip pim bsr-border`
  - MSDP peering: R2 Lo0 ↔ R4 Lo0 for ASM SA exchange
- Receivers:
  - R3 Gi0/2 (PC2 LAN): IGMPv3, joins 239.1.1.1, 239.2.2.1, and
    `(10.1.1.10, 232.1.1.1)` SSM
  - R4 Lo0: joins 239.1.1.1 (MSDP SA-cache demonstrator)

### Scenario

The network was fully operational at the end of Lab 03. During a change
window last night, an on-call engineer pushed "a handful of tweaks" across
R2, R3, and R4 before being pulled onto another incident. The shift handover
log contains only:

> *"Multicast broken. Users on the receiver LAN report no streams. R4 looks
> weird in the BSR tables. Escalating."*

No fault list was recorded. No config backup was taken. Your job is to
diagnose every fault from the routers themselves, restore full ASM / SSM /
Bidir forwarding, and document each root cause before the morning handover.

---

## 3. Hardware & Environment Specifications

### Cabling

| Link | From | To | Subnet | Role |
|------|------|----|--------|------|
| L1 | R1 Gi0/0 | R2 Gi0/0 | 10.1.12.0/30 | IGP + PIM transit |
| L2 | R2 Gi0/1 | R3 Gi0/0 | 10.1.23.0/30 | IGP + PIM transit |
| L3 | R1 Gi0/1 | R3 Gi0/1 | 10.1.13.0/30 | IGP + PIM transit |
| L4 | R1 Gi0/2 | PC1 | 10.1.1.0/24 | Source LAN |
| L5 | R3 Gi0/2 | PC2 | 10.1.3.0/24 | Receiver LAN (IGMPv3) |
| L6 | R2 Gi0/2 | R4 Gi0/0 | 10.1.24.0/30 | PIM domain border |
| L7 | R3 Gi0/3 | R4 Gi0/1 | 10.1.34.0/30 | PIM domain border |

### Console Access Table

| Device | Port | Connection Command |
|--------|------|--------------------|
| R1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R3 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R4 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| PC1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| PC2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |

---

## 4. Base Configuration

`setup_lab.py` pushes the pre-broken configs from `initial-configs/` to
every router. The configs contain:

- Full interface addressing (all links up)
- OSPFv2 converged across all routers
- `ip multicast-routing` globally enabled
- PIM sparse-mode on most (but not all) transit interfaces
- Bidir + SSM globally enabled
- BSR and RP-candidate statements on R2 (partial)
- IGMP configuration on R3 Gi0/2 (partial)
- MSDP peering between R2 and R4 (with a defect)
- bsr-border on most inter-domain interfaces (with a gap)
- **Six injected faults** -- your job to find and fix every one

**NOT pre-loaded** (these are the **faults** you must restore; every fault
is a misconfiguration or an extra/missing line that a careless engineer
could reasonably have introduced during the change window):

- Nothing is architecturally absent -- the reference design is fully
  represented in the configs. The six faults are edits to that reference.
  You are expected to diagnose and fix in place, not rebuild from scratch.

---

## 5. Lab Challenge: Comprehensive Troubleshooting

> This is a capstone lab. The network is pre-broken.
> Diagnose and resolve 6 concurrent faults spanning all blueprint bullets.
> No step-by-step guidance is provided -- work from symptoms only.

### What You Are Given

- All routers are reachable on the console; every physical link is up.
- OSPF is fully converged; loopback-to-loopback unicast reachability works
  across all four routers.
- `ip multicast-routing` is globally enabled on every router.
- Every multicast construct required for the reference design is represented
  *somewhere* in the configs -- BSR, two RP-candidate lines, SSM ACL, Bidir
  enablement, MSDP peering, IGMPv3 on the receiver LAN, and static RP on R4.
  The defects are edits, not deletions of entire features.

### What You Must Achieve

By the end of this lab, the following must all be true **simultaneously**:

- `show ip pim neighbor` on R1, R2, R3 shows every expected neighbor on
  every PIM segment inside the main domain.
- `show ip pim rp mapping` on R1, R2, R3 shows:
  - `2.2.2.2` for `239.1.1.0/24` (ASM)
  - `2.2.2.2` for `239.2.2.0/24` **Bidir**
- `show ip pim rp mapping` on R4 shows **only** `4.4.4.4` (static) -- no
  entries leaked in from the main domain's BSR.
- `show ip mroute 239.1.1.1` on R3: `(*, 239.1.1.1)` with Gi0/2 in the OIL
  **and** `(10.1.1.10, 239.1.1.1)` with a non-zero packet counter on Gi0/2.
- `show ip mroute 232.1.1.1` on R3: `(10.1.1.10, 232.1.1.1)` with flags
  `sTI`, Gi0/1 as incoming, Gi0/2 in the OIL.
- `show ip mroute 239.2.2.1` on R3: `(*, 239.2.2.1)` with flag `B` (Bidir),
  Gi0/2 in the OIL.
- `show ip msdp peer` on both R2 and R4: peer is **Up** and **Established**.
- `show ip msdp sa-cache` on R4: contains at least one `(10.1.1.10,
  239.1.1.1)` entry originated from R2.
- End-to-end forwarding works for ASM, SSM, and Bidir (see Section 6).

### Rules of Engagement

- **Work from `show` commands only** until you have a hypothesis. Do not
  blind-edit configs -- every fault has a unique show-command fingerprint.
- **Record each fault's root cause in one line** before applying the fix
  (what was wrong + why that symptom appeared).
- **After each fix, re-verify** the affected `show` output before moving on.
- **Do not run `apply_solution.py`** until you have genuinely tried every
  ticket yourself. The only reason to run it is to reset after you are done,
  or to rescue a session that has drifted beyond repair.
- **No new faults introduced**: the end-state must match Section 6 exactly.
  Don't paper over a fault by adding workarounds elsewhere.

---

## 6. Verification & Analysis

The following end-state outputs are what the restored network must produce.
Use them as the target picture while you work through the tickets.

### R2 -- PIM Neighbors (main domain complete)

```bash
R2# show ip pim neighbor
Neighbor          Interface                Uptime/Expires    Ver   DR Prio/Mode
10.1.12.1         GigabitEthernet0/0       01:02:11/00:01:35 v2    1 / S P G
10.1.23.2         GigabitEthernet0/1       00:01:47/00:01:29 v2    1 / DR S P G   ! ← R3 neighbor (Ticket 1 fix)
10.1.24.2         GigabitEthernet0/2       01:02:00/00:01:32 v2    1 / S P G
```

### R3 -- PIM Neighbors

```bash
R3# show ip pim neighbor
Neighbor          Interface                Uptime/Expires    Ver   DR Prio/Mode
10.1.23.1         GigabitEthernet0/0       00:01:47/00:01:33 v2    1 / S P G      ! ← R2 neighbor visible after fix
10.1.13.1         GigabitEthernet0/1       01:02:15/00:01:28 v2    1 / S P G
10.1.34.1         GigabitEthernet0/3       01:02:07/00:01:30 v2    1 / S P G
```

### R3 -- RP Mapping (both ASM and Bidir present)

```bash
R3# show ip pim rp mapping
PIM Group-to-RP Mappings

Group(s) 239.1.1.0/24                                          ! ← ASM group range
  RP 2.2.2.2 (?), v2                                           ! ← Ticket 2 fix restores this
    Info source: 2.2.2.2 (?), via bootstrap, priority 0, holdtime 150
         Uptime: 00:01:12, expires: 00:02:15

Group(s) 239.2.2.0/24, Bidir                                   ! ← Bidir group range
  RP 2.2.2.2 (?), v2
    Info source: 2.2.2.2 (?), via bootstrap, priority 0, holdtime 150
         Uptime: 01:03:22, expires: 00:02:10
```

### R4 -- RP Mapping (STATIC ONLY; no BSR leak)

```bash
R4# show ip pim rp mapping
PIM Group-to-RP Mappings

Group(s): 224.0.0.0/4, Static                                  ! ← static catch-all
    RP: 4.4.4.4 (?)                                            ! ← only self-RP visible (Ticket 6 fix)

! NOTE: No "via bootstrap" entries. If you see ANY 2.2.2.2 line here, the
! bsr-border fence on L6 is leaking -- Fault 6 has not been fully fixed.

R4# show ip pim bsr-router
PIMv2 Bootstrap information
This system is not a BSR or BSR candidate                      ! ← correct: R4 is isolated
No BSR information available                                   ! ← correct: no leak
```

### R3 -- Mroute Entries (all three modes)

```bash
R3# show ip mroute 239.1.1.1
(*, 239.1.1.1), 00:02:15/stopped, RP 2.2.2.2, flags: SJC      ! ← ASM shared tree toward R2
  Incoming interface: GigabitEthernet0/0, RPF nbr 10.1.23.1   ! ← RPF toward R2 (Ticket 2 restores RP)
  Outgoing interface list:
    GigabitEthernet0/2, Forward/Sparse, 00:02:15/00:02:45     ! ← receiver LAN in OIL

(10.1.1.10, 239.1.1.1), 00:00:47/00:02:43, flags: T           ! ← SPT after first packet (Ticket 3 fix)
  Incoming interface: GigabitEthernet0/1, RPF nbr 10.1.13.1   ! ← RPF toward R1 (source); NOT Gi0/0
  Outgoing interface list:
    GigabitEthernet0/2, Forward/Sparse, 00:00:47/00:03:13

R3# show ip mroute 232.1.1.1
(10.1.1.10, 232.1.1.1), 00:01:00/00:03:20, flags: sTI         ! ← SSM (s) + SPT (T) + IGMPv3 include (I)
  Incoming interface: GigabitEthernet0/1, RPF nbr 10.1.13.1   ! ← Ticket 4 fix: static-group restored
  Outgoing interface list:
    GigabitEthernet0/2, Forward/Sparse, 00:01:00/00:02:01

R3# show ip mroute 239.2.2.1
(*, 239.2.2.1), 01:03:10/00:03:20, RP 2.2.2.2, flags: BC      ! ← Bidir (B) shared tree
  Bidir-Upstream: GigabitEthernet0/0, RPF nbr 10.1.23.1
  Outgoing interface list:
    GigabitEthernet0/2, Bidir-Upstream, 01:03:10/00:00:00
    GigabitEthernet0/0, Forward/Sparse, 01:03:10/00:03:20     ! ← DF on this segment
```

### R2 -- MSDP Peer Up + SA Cache (with R2-originated SAs)

```bash
R2# show ip msdp peer 4.4.4.4
MSDP Peer 4.4.4.4 (?), AS ?
  Connection status:
    State: Up, Resets: 0, Connection source: Loopback0 (2.2.2.2)   ! ← Up after Ticket 5 fix
    Uptime(Downtime): 00:02:31, Messages sent/received: 5/3, SAs learned from this peer: 0
    Input messages discarded: 0

R2# show ip msdp sa-cache
MSDP Source-Active Cache - 1 entries
(10.1.1.10, 239.1.1.1), RP 2.2.2.2, BGP/AS 0, 00:00:43/00:05:57, Peer Local   ! ← locally originated
```

### R4 -- MSDP SA Cache Populated From R2

```bash
R4# show ip msdp sa-cache
MSDP Source-Active Cache - 1 entries
(10.1.1.10, 239.1.1.1), RP 2.2.2.2, BGP/AS 0, 00:00:43/00:05:57, Peer 2.2.2.2  ! ← SA from R2 (Ticket 5 fix)
```

### End-to-End Forwarding Proof (all three modes)

```bash
! ASM: source from PC1
PC1> ping 239.1.1.1
84 bytes from 10.1.3.10 icmp_seq=1 ttl=62 time=3.112 ms       ! ← PC2 responds (IGMP join)
84 bytes from 4.4.4.4    icmp_seq=1 ttl=254 time=2.041 ms      ! ← R4 Lo0 responds (MSDP SA demo)

! Bidir: source from PC1
PC1> ping 239.2.2.1
84 bytes from 10.1.3.10 icmp_seq=1 ttl=62 time=3.089 ms       ! ← PC2 responds (Bidir shared tree)

! SSM: source MUST be PC1 (R3's INCLUDE filter bound to 10.1.1.10)
PC1> ping 232.1.1.1
232.1.1.1 icmp_seq=1 timeout                                   ! ← VPCS shows no echo reply -- EXPECTED
                                                                !   (multicast replies are host-dependent on VPCS)
! Proof of SSM forwarding is in R3's mroute state, not a ping reply:
R3# show ip mroute 232.1.1.1 count
Group: 232.1.1.1, Source count: 1, Packets forwarded: 42, Packets received: 42   ! ← non-zero = success
```

---

## 7. Verification Cheatsheet

### PIM Adjacency Diagnosis

```
show ip pim interface
show ip pim neighbor
show ip pim interface <int> detail
```

| Command | Purpose |
|---------|---------|
| `show ip pim interface` | Lists every PIM-enabled interface + DR + hello timers |
| `show ip pim neighbor` | Which PIM neighbors exist and on which segment |
| `show ip pim interface <int> detail` | Deep view: DR election, hello count, query count |

> **Exam tip:** An interface that is OSPF-healthy but missing from `show ip
> pim interface` almost always lacks `ip pim sparse-mode`. Compare the two
> outputs side-by-side to find adjacency gaps.

### RP Discovery (BSR) Diagnosis

```
show ip pim bsr-router
show ip pim rp mapping
show ip pim rp <group>
```

| Command | Purpose |
|---------|---------|
| `show ip pim bsr-router` | Identifies the BSR for the domain and its uptime |
| `show ip pim rp mapping` | Per-group-range RP mappings + source (bootstrap / static / Auto-RP) |
| `show ip pim rp <group>` | Which RP is being used for a specific group right now |

> **Exam tip:** "Via bootstrap" in `rp mapping` means BSR delivered it; "Static"
> means it was configured on this router. A BSR-learned RP **overrides** a
> static RP unless `override` is used. Check the mapping source carefully in
> any multi-domain topology.

### RPF Diagnosis

```
show ip rpf <source>
show ip mroute <group>
show ip route <source>
```

| Command | Purpose |
|---------|---------|
| `show ip rpf <source>` | Which interface multicast will accept packets from this source on |
| `show ip mroute <G>` | Mroute state + RPF interface + OIL |
| `show ip route <source>` | Unicast path to the source (what RPF uses by default) |

> **Exam tip:** If `show ip rpf` points at the wrong interface, look for
> `ip mroute` (populates a multicast-only RPF table -- `RPF type: mroute`),
> a static `ip route` (changes unicast AND RPF -- `RPF type: unicast
> (static)`), or a route-map policy. `ip mroute` is the sneakier one
> because unicast stays healthy.

### IGMP / SSM Diagnosis

```
show ip igmp interface <int>
show ip igmp groups
show ip igmp groups <group> detail
show ip mroute <group>
```

| Command | Purpose |
|---------|---------|
| `show ip igmp interface` | IGMP version + querier + join count per interface |
| `show ip igmp groups` | Joined group list on each interface |
| `show ip igmp groups <G> detail` | IGMPv3 INCLUDE/EXCLUDE filters and source lists |
| `show ip mroute <G>` | Must show `(S,G)` with flag `I` for SSM to work |

> **Exam tip:** SSM requires `(S,G)` state formed from an IGMPv3 INCLUDE
> report. If the mroute shows only `(*,G)` or nothing, the IGMPv3 join
> never landed -- check `show ip igmp groups <G> detail` for the source list.

### MSDP Diagnosis

```
show ip msdp peer
show ip msdp summary
show ip msdp sa-cache
show ip msdp count
```

| Command | Purpose |
|---------|---------|
| `show ip msdp peer` | TCP state + connection source + SA counts per peer |
| `show ip msdp summary` | One-line view of every MSDP peer |
| `show ip msdp sa-cache` | SAs learned from peers or originated locally |
| `show ip msdp count` | Incoming/outgoing SA counts (rate-check) |

> **Exam tip:** MSDP runs on TCP/639 and uses the local `connect-source` IP
> against the remote router's `ip msdp peer X` line. Any mismatch (wrong
> peer IP, missing route to peer, firewall block) results in `Inactive` or
> `Listen` state and an empty SA cache.

### BSR-Border / PIM-Domain Diagnosis

```
show ip pim bsr-router
show run | include bsr-border
show ip pim interface <int>
```

| Command | What to Look For |
|---------|-----------------|
| `show ip pim bsr-router` on border router | Must show "not a BSR" + "No BSR information available" on the fenced side |
| `show run | include bsr-border` | Confirms the command is on every inter-domain interface on at least one end |
| `show ip pim interface <int>` | `PIM DR border` flag when bsr-border is set |

> **Exam tip:** `bsr-border` blocks BSR in **both directions**. Dropping it
> on just one end still blocks if the other end retains it -- but dropping it
> on **both ends** of one link opens the border.

### Common Multicast Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| `show ip pim neighbor` missing a peer | `ip pim sparse-mode` missing on one end of the segment |
| `show ip pim rp mapping` empty for a range | No `rp-candidate` for that range, or BSR itself isn't elected |
| `(*,G)` present but no `(S,G)` | RPF fails toward source; check `show ip rpf` |
| Nothing at all for SSM group | IGMPv3 static-group missing or `ip pim ssm range` missing |
| MSDP `Inactive` / `Listen` | Wrong peer IP, wrong connect-source, unicast route missing |
| Border router sees foreign BSR | `bsr-border` missing on both ends of the inter-domain link |
| `B` flag missing from `(*,G)` | `ip pim bidir-enable` missing, or `rp-candidate ... bidir` keyword absent |

### Wildcard Mask Quick Reference

| Subnet Mask | Wildcard Mask | Common Use |
|-------------|---------------|------------|
| /30 (255.255.255.252) | 0.0.0.3 | Point-to-point link |
| /24 (255.255.255.0) | 0.0.0.255 | LAN segment |
| /32 (255.255.255.255) | 0.0.0.0 | Loopback match |

---

## 8. Solutions (Spoiler Alert!)

> Try to diagnose every ticket before peeking. Each `<details>` block reveals
> the fault and the restore command for one of the six injected faults.

### Fault 1: R3 has an `ip mroute` entry that breaks RPF toward the source

<details>
<summary>Click to view Root Cause and Fix</summary>

**Root cause:** R3 has `ip mroute 10.1.1.0 255.255.255.0 4.4.4.4`. This
populates the multicast RPF table with a route that says "accept 10.1.1.0/24
multicast traffic from the direction of 4.4.4.4" -- which resolves via OSPF
to Gi0/3 (toward R4). Unicast routing is untouched (OSPF still says Gi0/1
for this prefix), so pings succeed, `show ip route` looks normal, and the
fault is invisible to any unicast check. But multicast packets arrive on
Gi0/1 while RPF expects Gi0/3 → RPF fail → drop on every packet. R3's
`(*, 239.1.1.1)` Join also heads out Gi0/3 (toward R4) and dies there
because R4 is in a separate domain.

**Detection:**
```bash
R3# show ip rpf 10.1.1.10
RPF information for ? (10.1.1.10)
  RPF interface: GigabitEthernet0/3             ! ← WRONG -- OSPF unicast says Gi0/1
  RPF neighbor: ? (10.1.34.1)
  RPF route/mask: 10.1.1.0/24
  RPF type: mroute                              ! ← DEAD GIVEAWAY -- mroute override
  Doing distance-preferred lookups across tables

R3# show ip route 10.1.1.0 255.255.255.0
Routing entry for 10.1.1.0/24
  Known via "ospf 1", distance 110               ! ← unicast healthy -- OSPF via Gi0/1
  Routing Descriptor Blocks:
  * 10.1.13.1, via GigabitEthernet0/1

R3# show run | include ip mroute
ip mroute 10.1.1.0 255.255.255.0 4.4.4.4         ! ← the culprit

R3# show ip mroute 239.1.1.1
(*, 239.1.1.1), 00:02:15/stopped, RP 2.2.2.2, flags: SJC
  Incoming interface: GigabitEthernet0/3, RPF nbr 10.1.34.1   ! ← Join goes toward R4, not R2
  Outgoing interface list:
    GigabitEthernet0/2, Forward/Sparse, 00:02:15/00:02:45

R3# show ip mroute 239.1.1.1 count
Group: 239.1.1.1, Packets forwarded: 0           ! ← zero forwarded despite OIL
```

**Fix on R3:**
```bash
R3(config)# no ip mroute 10.1.1.0 255.255.255.0 4.4.4.4
```

After removal, RPF falls back to the unicast RIB and returns `Gi0/1` with
neighbor `10.1.13.1`, matching the interface where multicast packets
actually arrive. The existing `(*,G)` may need a reconverge to flip its
incoming interface; a quick `R3# clear ip mroute 239.1.1.1` speeds it up.
</details>

### Fault 2: R2 Gi0/1 is missing `ip pim sparse-mode`

<details>
<summary>Click to view Root Cause and Fix</summary>

**Root cause:** R2's Gi0/1 (the R2-R3 L2 link) has no `ip pim sparse-mode`.
OSPF still forms on the segment, but PIM does not. R3 never sees R2 as a
PIM neighbor on that link, so Joins sent toward R2 via the OSPF-preferred
Gi0/0 path are dropped.

**Detection:**
```bash
R3# show ip pim neighbor
Neighbor          Interface               Uptime/Expires    Ver   DR Prio/Mode
10.1.13.1         GigabitEthernet0/1      01:01:40/00:01:35 v2    1 / S P G
10.1.34.1         GigabitEthernet0/3      01:01:32/00:01:27 v2    1 / S P G
! ← no neighbor on Gi0/0 (10.1.23.1 / R2) -- should be there

R2# show ip pim interface
Address          Interface               Ver/  Nbr    Query  DR       DR
                                         Mode  Count  Intvl  Prior
10.1.12.2        GigabitEthernet0/0      v2/S  1      30     1        10.1.12.2
10.1.24.1        GigabitEthernet0/2      v2/SB 1      30     1        10.1.24.1
! ← Gi0/1 absent entirely -- PIM not configured on that interface
```

**Fix on R2:**
```bash
R2(config)# interface GigabitEthernet0/1
R2(config-if)# ip pim sparse-mode
```
</details>

### Fault 3: R2 is missing the ASM rp-candidate line

<details>
<summary>Click to view Root Cause and Fix</summary>

**Root cause:** R2's `rp-candidate` line for `ASM_GROUPS` (239.1.1.0/24) was
removed; only the Bidir line (`group-list BIDIR_GROUPS bidir`) remains. BSR
is still elected and still floods -- but with no RP mapping for the ASM
range, R1/R2/R3 have no RP to send Joins toward. ASM traffic silently drops.
Bidir keeps working because its rp-candidate entry is intact.

**Detection:**
```bash
R3# show ip pim rp mapping
PIM Group-to-RP Mappings

Group(s) 239.2.2.0/24, Bidir                 ! ← Bidir range present
  RP 2.2.2.2 (?), v2
    Info source: 2.2.2.2 (?), via bootstrap, priority 0, holdtime 150
! ← note the ABSENCE of any 239.1.1.0/24 entry -- that's the fault

R1# show ip pim rp 239.1.1.1
Group: 239.1.1.1, RP: ?
! ← "?" means no RP known for this group

R2# show run | include rp-candidate
ip pim rp-candidate Loopback0 group-list BIDIR_GROUPS bidir    ! ← only Bidir line present
```

**Fix on R2:**
```bash
R2(config)# ip pim rp-candidate Loopback0 group-list ASM_GROUPS
```

Wait ~60 seconds for BSR to flood the new mapping, then re-check `show ip
pim rp mapping` on R1 and R3.
</details>

### Fault 4: R3 Gi0/2 is missing the IGMP static-group for SSM

<details>
<summary>Click to view Root Cause and Fix</summary>

**Root cause:** R3's Gi0/2 has `ip igmp version 3` and the two ASM/Bidir
join-groups, but the `ip igmp static-group 232.1.1.1 source 10.1.1.10`
line (the only SSM join on the receiver LAN) is missing. Without the
IGMPv3 INCLUDE filter, no `(S,G)` ever forms for the SSM range -- R3
silently ignores any SSM traffic that arrives.

**Detection:**
```bash
R3# show ip igmp groups 232.1.1.1 detail
! (no output -- 232.1.1.1 not joined on any interface)

R3# show ip igmp interface GigabitEthernet0/2 | include Multicast groups
  Multicast groups joined by this system (number of users):
      239.1.1.1(1)    239.2.2.1(1)                     ! ← 232.1.1.1 missing

R3# show ip mroute 232.1.1.1
! (no entry)
```

**Fix on R3:**
```bash
R3(config)# interface GigabitEthernet0/2
R3(config-if)# ip igmp static-group 232.1.1.1 source 10.1.1.10
```

Verify with `show ip mroute 232.1.1.1` -- `(10.1.1.10, 232.1.1.1)` should
appear within a few seconds with flag `I` (IGMPv3 include-received).
</details>

### Fault 5: R4 has the wrong MSDP peer IP

<details>
<summary>Click to view Root Cause and Fix</summary>

**Root cause:** R4's MSDP peer statement reads `ip msdp peer 2.2.2.200
connect-source Loopback0` -- an IP that exists nowhere in the network. R4
sends SYN to 2.2.2.200, it never arrives, the session never comes up, and
the SA cache stays empty. R2's side (`ip msdp peer 4.4.4.4`) is correct, so
R2 keeps trying to connect from its side too -- but R4 never answers on the
right IP. On R2, the peer stays in `Listen` state.

**Detection:**
```bash
R4# show ip msdp peer
MSDP Peer 2.2.2.200 (?), AS ?
  Connection status:
    State: Inactive, Resets: 0, Connection source: Loopback0 (4.4.4.4)
    Uptime(Downtime): 00:02:14, Messages sent/received: 0/0    ! ← 0/0 = never connected
    SAs learned from this peer: 0

R4# show ip route 2.2.2.200
% Network not in table                           ! ← no route = no unicast path

R4# show run | include msdp peer
ip msdp peer 2.2.2.200 connect-source Loopback0  ! ← typo

R2# show ip msdp peer
MSDP Peer 4.4.4.4
  State: Listen                                   ! ← waiting for the other side
```

**Fix on R4:**
```bash
R4(config)# no ip msdp peer 2.2.2.200 connect-source Loopback0
R4(config)# ip msdp peer 2.2.2.2 connect-source Loopback0
R4(config)# ip msdp description R2-MSDP-PEER
```

Removing the peer statement also drops `description` -- re-apply it. Verify
with `show ip msdp peer` on both sides; state must be `Up`.
</details>

### Fault 6: BSR-border missing on both ends of L6 (R2 Gi0/2 + R4 Gi0/0)

<details>
<summary>Click to view Root Cause and Fix</summary>

**Root cause:** `ip pim bsr-border` was removed from **both** R2 Gi0/2 and
R4 Gi0/0 (L6 link). With no bsr-border on either end, R2's BSR messages
flood onto L6, R4 accepts them, and R4's `show ip pim rp mapping` now shows
the main-domain RPs (2.2.2.2 for both ASM and Bidir ranges). Dynamic RP
learned via BSR overrides R4's static `ip pim rp-address 4.4.4.4` for those
ranges (no `override` keyword), breaking the intended domain isolation.

**Detection:**
```bash
R4# show ip pim bsr-router
PIMv2 Bootstrap information
  BSR address: 2.2.2.2 (?)                        ! ← should be "not a BSR, no BSR info"
  Uptime:      00:00:47, BSR Priority: 0, Hash mask length: 0
  Expires:     00:01:43

R4# show ip pim rp mapping
PIM Group-to-RP Mappings

Group(s) 239.1.1.0/24
  RP 2.2.2.2 (?), v2                              ! ← foreign RP learned via BSR
    Info source: 2.2.2.2 (?), via bootstrap       ! ← confirms leak

Group(s) 239.2.2.0/24, Bidir
  RP 2.2.2.2 (?), v2
    Info source: 2.2.2.2 (?), via bootstrap

Group(s): 224.0.0.0/4, Static
    RP: 4.4.4.4 (?)                               ! ← overridden for 239.x ranges

R4# show run | section interface GigabitEthernet0/0
interface GigabitEthernet0/0
 ip address 10.1.24.2 255.255.255.252
 ip pim sparse-mode
!  (bsr-border missing)

R2# show run | section interface GigabitEthernet0/2
interface GigabitEthernet0/2
 ip address 10.1.24.1 255.255.255.252
 ip pim sparse-mode
!  (bsr-border also missing -- both ends clean of it)
```

**Fix (both ends of L6):**
```bash
R2(config)# interface GigabitEthernet0/2
R2(config-if)# ip pim bsr-border

R4(config)# interface GigabitEthernet0/0
R4(config-if)# ip pim bsr-border
```

Wait for the existing BSR holdtime to expire (~150s) or clear explicitly:
```bash
R4# clear ip pim rp-mapping *
```

Verify R4's `show ip pim rp mapping` now shows ONLY the static 4.4.4.4
entry and `show ip pim bsr-router` reports no BSR.
</details>

### Final Verification (all fixes applied)

<details>
<summary>Click to view End-State Commands</summary>

```bash
! PIM adjacency complete in main domain:
R2# show ip pim neighbor              ! must show 3 neighbors
R3# show ip pim neighbor              ! must show 3 neighbors

! RP mapping correct on both domains:
R3# show ip pim rp mapping            ! ASM (2.2.2.2) + Bidir (2.2.2.2)
R4# show ip pim rp mapping            ! ONLY static 4.4.4.4

! All three multicast modes forward:
R3# show ip mroute 239.1.1.1          ! ASM: (*,G) + (S,G) with non-zero counters
R3# show ip mroute 232.1.1.1          ! SSM: (10.1.1.10, 232.1.1.1) with flag I
R3# show ip mroute 239.2.2.1          ! Bidir: (*,G) with flag B

! MSDP peering Up, SA cache populated:
R2# show ip msdp peer                 ! State: Up
R4# show ip msdp sa-cache             ! must show (10.1.1.10, 239.1.1.1) from peer 2.2.2.2

! End-to-end forwarding:
PC1> ping 239.1.1.1                   ! responses from PC2 AND R4 Lo0
PC1> ping 239.2.2.1                   ! response from PC2 (Bidir)
R3# show ip mroute 232.1.1.1 count    ! non-zero packet count = SSM forwarding
```
</details>

---

## 9. Troubleshooting Scenarios

All six faults are **pre-injected** via `setup_lab.py`. There are no separate
inject scripts in this lab -- the initial configs ARE the broken state.
Tickets are ordered to follow natural peel-back diagnosis: each ticket
exposes the next fault. Work sequentially unless you have reason to branch.

### Workflow

```bash
python3 setup_lab.py                               # pushes pre-broken configs (all 6 faults)
# (diagnose + fix each ticket below)
python3 scripts/fault-injection/apply_solution.py  # restore to known-good (lab-03 end-state)
```

---

### Ticket 1 -- R2 and R3 Do Not See Each Other as PIM Neighbors on L2

After pushing the configs, you run `show ip pim neighbor` on R3 and notice
the R2 peer (`10.1.23.1`) is missing, even though the OSPF adjacency on the
same interface is fully up and loopback-to-loopback pings work.

**Success criteria:** `show ip pim neighbor` on R2 lists R3 (`10.1.23.2`)
on Gi0/1, and R3 lists R2 (`10.1.23.1`) on Gi0/0. `show ip pim interface`
on R2 shows Gi0/1 with a non-zero neighbor count.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Confirm OSPF is healthy on the segment: `R2# show ip ospf neighbor` --
   lists R3 on Gi0/1 as `FULL`.
2. Confirm unicast works: `R2# ping 10.1.23.2` -- success.
3. Check PIM interfaces: `R2# show ip pim interface` -- Gi0/1 is **absent**
   from the list. That's the smoking gun.
4. Confirm configuration: `R2# show run interface Gi0/1` -- no `ip pim
   sparse-mode` line.
5. One-line root cause: *PIM sparse-mode not enabled on R2 Gi0/1, so the
   R2-R3 segment has no PIM adjacency.*
</details>

<details>
<summary>Click to view Fix</summary>

See [Solutions: Fault 2](#fault-2-r2-gi01-is-missing-ip-pim-sparse-mode).
</details>

---

### Ticket 2 -- PC2 Receives No ASM Traffic From 239.1.1.1

With Ticket 1 fixed, PC2 still receives nothing when PC1 sources to
`239.1.1.1`. `show ip pim neighbor` now looks healthy everywhere, but the
ASM shared tree never forms. Bidir traffic (`239.2.2.1`) on the other hand
reaches PC2 just fine.

**Success criteria:** `show ip pim rp mapping` on R1, R2, R3 contains an
entry for `239.1.1.0/24` pointing at `RP 2.2.2.2` via `bootstrap`. A PC1
ping of `239.1.1.1` produces an ICMP echo-reply from PC2 and R4 Lo0.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. On R3: `show ip mroute 239.1.1.1` -- no entry at all. R3 doesn't know
   how to even start the tree.
2. `R3# show ip pim rp 239.1.1.1` -- RP is "?" (unknown).
3. `R3# show ip pim rp mapping` -- the 239.1.1.0/24 line is missing.
   Bidir (`239.2.2.0/24`) is still present, so BSR itself is working.
4. BSR is fine; the defect is in what's being advertised. Check the RP
   source: `R2# show run | include rp-candidate`.
5. R2 advertises Bidir but not ASM. One-line root cause: *R2 is missing
   the ASM rp-candidate line, so BSR has no RP mapping for 239.1.1.0/24.*
</details>

<details>
<summary>Click to view Fix</summary>

See [Solutions: Fault 3](#fault-3-r2-is-missing-the-asm-rp-candidate-line).
</details>

---

### Ticket 3 -- ASM Shared Tree Builds But No Packets Reach PC2

After Ticket 2, R3 has `(*, 239.1.1.1)` with Gi0/2 in the OIL and an RPF
pointer toward R2. PC1 starts sourcing to 239.1.1.1 again. The PIM Register
flow should trigger an SPT switch so that `(10.1.1.10, 239.1.1.1)` installs
with Gi0/1 as incoming (direct from R1). But no packets arrive at PC2, and
`show ip mroute 239.1.1.1 count` on R3 shows zero forwarded.

**Success criteria:** `show ip mroute 239.1.1.1` on R3 shows an `(S,G)`
entry with incoming interface **Gi0/1** and a non-zero packet count on the
Gi0/2 OIL entry. `show ip rpf 10.1.1.10` on R3 returns Gi0/1.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `R3# show ip mroute 239.1.1.1` -- `(*,G)` present, but incoming
   interface is Gi0/3 (toward R4) instead of Gi0/0 (toward R2) or Gi0/1
   (toward R1). Suspicious.
2. `R3# show ip mroute 239.1.1.1 count` -- packets forwarded: 0, even
   though the OIL looks right.
3. `R3# show ip rpf 10.1.1.10` -- returns Gi0/3 with `RPF type: mroute`.
   **This is the tell**: something in the multicast RPF table is
   overriding unicast. OSPF doesn't have entries with type "mroute".
4. `R3# show ip route 10.1.1.0 255.255.255.0` -- healthy OSPF via Gi0/1.
   Unicast is fine; the override is multicast-only.
5. `R3# show run | include ip mroute` -- reveals `ip mroute 10.1.1.0
   255.255.255.0 4.4.4.4`.
6. One-line root cause: *An `ip mroute` entry on R3 redirects multicast
   RPF for the source subnet toward R4, so packets arriving from R1 fail
   RPF and get dropped.*
</details>

<details>
<summary>Click to view Fix</summary>

See [Solutions: Fault 1](#fault-1-r3-has-a-static-route-that-breaks-rpf-toward-the-source).
</details>

---

### Ticket 4 -- SSM Traffic Never Forms An (S,G) On R3

PC1 has been sourcing to `232.1.1.1` for several minutes. The PC1-to-R3
unicast path is fine, RPF is correct (post-Ticket 3). But R3 has no
mroute for 232.1.1.1 at all -- it's as if the SSM traffic is being ignored.
Meanwhile, ASM and Bidir forwarding on R3 both look healthy.

**Success criteria:** `show ip mroute 232.1.1.1` on R3 shows `(10.1.1.10,
232.1.1.1)` with flags `sTI`, incoming Gi0/1, Gi0/2 in OIL with a
non-zero packet count on `show ip mroute 232.1.1.1 count`.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `R3# show ip mroute 232.1.1.1` -- no entry. Nothing has joined.
2. Check the SSM range is enabled: `R3# show ip pim interface Gi0/2` --
   SSM is globally enabled (`ip pim ssm range SSM_RANGE` present in config).
3. Check what IGMP sees: `R3# show ip igmp groups 232.1.1.1 detail` -- no
   output.
4. Look at the interface's IGMP state: `R3# show ip igmp interface Gi0/2 |
   include Multicast groups` -- only 239.1.1.1 and 239.2.2.1 listed, no
   232.x.
5. Check config: `R3# show run interface Gi0/2` -- `ip igmp version 3` is
   present but no `ip igmp static-group 232.1.1.1 source 10.1.1.10` line.
6. One-line root cause: *The IGMPv3 static-group INCLUDE join for
   `(10.1.1.10, 232.1.1.1)` is missing on R3 Gi0/2, so no SSM state forms.*
</details>

<details>
<summary>Click to view Fix</summary>

See [Solutions: Fault 4](#fault-4-r3-gi02-is-missing-the-igmp-static-group-for-ssm).
</details>

---

### Ticket 5 -- R4's MSDP SA Cache Is Empty

ASM forwarding to PC2 is now working end-to-end. The MSDP SA-cache demo
(R4 Lo0 joining 239.1.1.1) should also be responding to PC1's pings, but
R4's `show ip msdp sa-cache` is empty, and pings to 239.1.1.1 produce
replies only from PC2 -- nothing from R4 Lo0.

**Success criteria:** `show ip msdp peer` on both R2 and R4 shows the peer
in **Up** state. `show ip msdp sa-cache` on R4 contains `(10.1.1.10,
239.1.1.1)` learned from peer `2.2.2.2`. PC1 ping of 239.1.1.1 now
receives a reply from 4.4.4.4 as well as from PC2.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `R4# show ip msdp peer` -- state `Inactive`, peer address looks odd.
2. `R4# show run | include msdp` -- reveals `ip msdp peer 2.2.2.200`
   (not `2.2.2.2`).
3. `R4# show ip route 2.2.2.200` -- "Network not in table". Confirms the
   peer IP is bogus.
4. `R2# show ip msdp peer` -- state `Listen` (waiting for the other side
   that never connects with the right IP).
5. One-line root cause: *R4's MSDP peer is configured with `2.2.2.200`
   instead of `2.2.2.2`, so the TCP session never establishes.*
</details>

<details>
<summary>Click to view Fix</summary>

See [Solutions: Fault 5](#fault-5-r4-has-the-wrong-msdp-peer-ip).
</details>

---

### Ticket 6 -- R4 Shows the Main-Domain BSR and the Wrong RP

With all ASM/SSM/Bidir paths working and MSDP up, a final sanity check on
R4 reveals something wrong with the domain isolation: `show ip pim
bsr-router` on R4 shows `BSR address: 2.2.2.2`, and `show ip pim rp
mapping` on R4 lists `2.2.2.2` for the 239.1.1.0/24 and 239.2.2.0/24
ranges (with `Info source: via bootstrap`), overriding the intended static
self-RP.

**Success criteria:** `show ip pim bsr-router` on R4 shows "This system is
not a BSR or BSR candidate" and "No BSR information available". `show ip
pim rp mapping` on R4 shows **only** the static 4.4.4.4 entry -- no
bootstrap-learned entries for any group range.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `R4# show ip pim bsr-router` -- BSR 2.2.2.2 listed (should be empty).
2. `R4# show ip pim rp mapping` -- 239.1.1.0/24 and 239.2.2.0/24 mapped
   to 2.2.2.2 via bootstrap (should not appear on R4).
3. BSR is leaking into R4's domain. Figure out which link is the path.
4. Check each inter-domain interface on R4: `R4# show run interface Gi0/0`
   -- no `ip pim bsr-border`. And `R4# show run interface Gi0/1` -- has
   bsr-border.
5. L6 is suspicious -- check the other side: `R2# show run interface
   Gi0/2` -- also no bsr-border on Gi0/2.
6. One-line root cause: *Both ends of L6 are missing `ip pim bsr-border`,
   so BSR messages from R2 leak into R4's domain and override R4's static
   RP for 239.x groups via BSR-learned mappings.*
</details>

<details>
<summary>Click to view Fix</summary>

See [Solutions: Fault 6](#fault-6-bsr-border-missing-on-both-ends-of-l6-r2-gi02--r4-gi00).
</details>

---

## 10. Lab Completion Checklist

### Diagnosis and Fix

- [ ] Ticket 1 -- R2 Gi0/1 `ip pim sparse-mode` restored; R2-R3 PIM adjacency up
- [ ] Ticket 2 -- R2 ASM rp-candidate line restored; 239.1.1.0/24 maps to 2.2.2.2
- [ ] Ticket 3 -- R3 `ip mroute` for 10.1.1.0/24 removed; RPF back on Gi0/1
- [ ] Ticket 4 -- R3 Gi0/2 IGMPv3 static-group for `(10.1.1.10, 232.1.1.1)` restored
- [ ] Ticket 5 -- R4 MSDP peer corrected to 2.2.2.2; session Up
- [ ] Ticket 6 -- `ip pim bsr-border` restored on both R2 Gi0/2 and R4 Gi0/0

### End-State Verification

- [ ] `show ip pim neighbor` on R2 lists R1, R3, and R4 (3 neighbors total)
- [ ] `show ip pim rp mapping` on R3 contains BOTH 239.1.1.0/24 (ASM) and
      239.2.2.0/24 (Bidir) with RP 2.2.2.2
- [ ] `show ip pim rp mapping` on R4 shows ONLY the static 4.4.4.4 entry --
      zero bootstrap-learned mappings
- [ ] `show ip mroute 239.1.1.1` on R3: `(*,G)` **and** `(S,G)` present,
      Gi0/2 in OIL, non-zero forwarded packet count
- [ ] `show ip mroute 232.1.1.1` on R3: `(10.1.1.10, 232.1.1.1)` with flag
      `I`, incoming Gi0/1, non-zero count
- [ ] `show ip mroute 239.2.2.1` on R3: `(*,G)` with flag `B` (Bidir)
- [ ] `show ip msdp peer` on R2 and R4: state **Up**
- [ ] `show ip msdp sa-cache` on R4: contains `(10.1.1.10, 239.1.1.1)` from
      peer `2.2.2.2`
- [ ] `PC1> ping 239.1.1.1` receives replies from PC2 and R4 Lo0
- [ ] `PC1> ping 239.2.2.1` receives reply from PC2 (Bidir path)
- [ ] `R3# show ip mroute 232.1.1.1 count` shows non-zero packets forwarded

### Root-Cause Documentation

- [ ] Written one-line root cause for each of the six faults before applying
      a fix
- [ ] No new faults introduced (confirm by running every verification check
      again after the last ticket)
