# NTP Configuration and QoS Interpretation

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

**Exam Objective:** 350-401 blueprint bullets 3.3.a -- *Interpret NTP and PTP
configurations* -- and 1.4 -- *Interpret QoS configurations*. Both are
"interpret" bullets: the exam rewards reading existing config accurately,
identifying component roles, and explaining expected behavior.

This lab combines hands-on NTP (configure + verify a small hierarchy with
authentication) with a pre-loaded QoS MQC policy that you will analyze rather
than build. You will finish the lab able to (a) build a minimum-viable NTP
design and audit it with show commands, and (b) read any MQC policy and answer
exam-style questions about what traffic hits which class and what action it
receives.

### NTP in Cisco IOS

Network Time Protocol keeps clocks synchronized across devices so that logs,
certificates, and TACACS/RADIUS events can be correlated in order. On Cisco
IOS, a router can act as:

- **Master:** `ntp master <stratum>` makes the router an authoritative source.
  Stratum 1 is reserved for directly-attached reference clocks; a typical lab
  master uses 3-7.
- **Client:** `ntp server <ip>` points the router at a time source. Multiple
  `ntp server` statements provide redundancy (the router picks one based on
  stratum and dispersion).
- **Peer:** `ntp peer <ip>` -- symmetric sync with another router at the same
  stratum. Rare in exam scenarios.

**NTP authentication** uses a pre-shared key on both sides:

```
! On the master:
ntp authentication-key <id> md5 <string>
ntp authenticate
ntp trusted-key <id>

! On the client:
ntp authentication-key <id> md5 <string>   ! must match master
ntp authenticate
ntp trusted-key <id>
ntp server <master-ip> key <id>            ! attach the key on the peer line
```

**Reachability octal:** `show ntp associations` includes a `reach` field in
octal. `377` (octal) = 11111111 binary = all 8 recent polls succeeded -- the
peer is fully reachable. `0` = never responded. Any value climbing from `1`
toward `377` indicates sync is progressing.

### PTP vs NTP (theory)

**Precision Time Protocol (IEEE 1588)** trades NTP's simplicity for much better
accuracy. PTP uses hardware timestamping at the MAC layer, sub-microsecond
precision, and a master-clock election via Best Master Clock Algorithm (BMCA).
It's used for synchrophasor protection in utilities, financial trading
time-stamping, and 5G fronthaul. NTP with software timestamps typically
achieves low-millisecond accuracy on a LAN; PTP achieves sub-microsecond.

| Property | NTP | PTP |
|----------|-----|-----|
| Typical accuracy (LAN) | 1-10 ms | <1 us |
| Timestamping | Software | Hardware (boundary/transparent clocks) |
| Transport | UDP/123 | Ethernet multicast or UDP |
| Master election | Manual / configured | BMCA (automatic) |
| Typical use | General IT | Finance, utilities, industrial |

### QoS -- MQC Building Blocks

Cisco's Modular QoS CLI (MQC) composes policy in three layers, always in the
same order:

1. **Class-map** -- defines *what traffic*. `match dscp ef`, `match
   access-group`, `match protocol`, etc. `match-any` = OR; `match-all` =
   AND.
2. **Policy-map** -- defines *what action per class*. Actions include
   `priority` (LLQ), `bandwidth` (CBWFQ reservation), `police` (rate-limit),
   `shape` (smooth + buffer), `set dscp` (mark), `random-detect` (WRED drop).
3. **Service-policy** -- attaches the policy-map to an interface with a
   direction: `service-policy input X` or `service-policy output X`.

#### DSCP quick reference

| Class | DSCP | Binary | Role |
|-------|------|--------|------|
| EF | 46 | 101110 | Expedited Forwarding -- voice RTP |
| AF41 | 34 | 100010 | Real-time video |
| AF31 | 26 | 011010 | Business / transactional data |
| AF21 | 18 | 010010 | Best-effort business |
| AF11 | 10 | 001010 | Bulk transfer |
| CS1 | 8 | 001000 | Scavenger |
| BE | 0 | 000000 | Best effort / default |

#### Action taxonomy

- **priority percent X** -- strict LLQ; max X% of interface bandwidth during
  congestion. Only one priority class per policy.
- **bandwidth percent X** -- minimum guarantee (not a cap); class gets at
  least X% when congested.
- **police cir Y** -- rate-limit; traffic exceeding Y triggers the
  `exceed-action` (transmit / drop / set dscp).
- **random-detect** -- WRED drops packets proactively as queue fills, before
  tail-drop kicks in. `random-detect dscp-based` uses per-DSCP profiles.
- **fair-queue** -- flow-based WFQ inside a class (usually `class-default`).

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| NTP hierarchy | Configure master/client roles, read stratum levels, interpret reach |
| NTP authentication | Add MD5 keys correctly on both sides so peers actually authenticate |
| QoS policy reading | Given an MQC policy block, identify which traffic hits which class |
| Action interpretation | Predict what happens to voice, video, data, and bulk under congestion |
| PTP concepts | Explain when PTP is used instead of NTP and why |

---

## 2. Topology & Scenario

```
                         ┌──────────────────────┐
                         │         R3           │
                         │ (Upstream / NTP+NAT) │
                         │     Lo0: 3.3.3.3     │
                         │  Lo1: 203.0.113.1/24 │
                         └──┬──────────────┬────┘
                    Gi0/0   │              │   Gi0/1
              10.0.13.2/30  │              │  10.0.23.2/30
                            │              │
              10.0.13.1/30  │              │  10.0.23.1/30
                    Gi0/1   │              │   Gi0/1
              ┌─────────────┴───┐      ┌───┴─────────────┐
              │       R1        │      │       R2        │
              │ (Primary Gwy)   │      │ (Secondary Gwy) │
              │  Lo0: 1.1.1.1   │      │  Lo0: 2.2.2.2   │
              │  NTP Master     │      │  NTP Client     │
              └────┬───────┬────┘      └────┬───────┬────┘
             Gi0/0 │       │ Gi0/2     Gi0/0│       │ Gi0/2
     192.168.1.2/24│       │10.0.12.1 192.168.1.3/24│ 10.0.12.2
                   │       └───────────────┐│       │
                   │               R1-R2   ││       │
                   │               sync    ││       │
                   │                       └┼───────┘
                   │                        │
              ┌────┴────────────────────────┴────┐
              │         SW-LAN (unmanaged)       │
              │          192.168.1.0/24          │
              └───┬──────────────────────┬───────┘
                  │                      │
               ┌──┴──┐                 ┌─┴──┐
               │ PC1 │                 │PC2 │
               │ .10 │                 │ .20│
               └─────┘                 └────┘
```

### Scenario

Your enterprise has a small three-router core. Logs from last week are
timestamped with drifted clocks -- the SOC team cannot correlate events across
devices. You have been asked to set up a simple NTP hierarchy (R1 as master,
R2 and R3 as clients, authenticated with MD5) so that all devices share a
single time source.

While you are in the devices, the WAN lead has asked you to review the
pre-loaded QoS policy on R1 (outbound to the ISP uplink) and confirm it
matches the approved service-level plan:

- Voice must have strict-priority up to 10% of the link
- Video gets at least 20% with DSCP-based WRED
- Critical data gets at least 30%
- Scavenger is rate-limited to 128 kbps
- Everything else hits best-effort queueing

---

## 3. Hardware & Environment Specifications

### Console Access Table

| Device | Port | Connection Command |
|--------|------|--------------------|
| R1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R3 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| PC1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| PC2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |

### Cabling

| Link | From | To | Subnet |
|------|------|----|--------|
| L1 | R1 Gi0/0 | SW-LAN port1 | 192.168.1.0/24 (shared LAN) |
| L2 | R2 Gi0/0 | SW-LAN port2 | 192.168.1.0/24 (shared LAN) |
| L3 | PC1 e0 | SW-LAN port3 | 192.168.1.0/24 |
| L4 | PC2 e0 | SW-LAN port4 | 192.168.1.0/24 |
| L5 | R1 Gi0/1 | R3 Gi0/0 | 10.0.13.0/30 |
| L6 | R2 Gi0/1 | R3 Gi0/1 | 10.0.23.0/30 |
| L7 | R1 Gi0/2 | R2 Gi0/2 | 10.0.12.0/30 |

---

## 4. Base Configuration

`setup_lab.py` pushes the `initial-configs/` to each router. The configs
already contain:

- Full interface addressing
- OSPF process 1 across every routed link (R1, R2, R3 all in area 0)
- Loopback 0 on each router (router-ID and OSPF source)
- On R1 only: a pre-loaded QoS MQC policy (`LAN-OUT`) already attached
  outbound on Gi0/1

**NOT pre-loaded (student must add):**

- NTP master configuration on R1
- NTP client configuration on R2 and R3
- NTP MD5 authentication on all three routers

---

## 5. Lab Challenge: Core Implementation

### Task 1: Configure R1 as an NTP master at stratum 3

- On R1, become an authoritative NTP source at stratum 3.
- No authentication yet -- you will add it in Task 3.

**Verification:** `R1# show ntp status` must return `Clock is synchronized,
stratum 3, reference is 127.127.1.1` (internal reference) within 60 seconds.

---

### Task 2: Configure R2 and R3 as NTP clients of R1

- On R2 and R3, point NTP at `1.1.1.1` (R1's Loopback 0).
- Allow up to 2 minutes for the association to reach state `synchronized`.

**Verification:** `show ntp associations` on R2 and R3 must list `1.1.1.1` with
an asterisk `*` in the first column (selected sys peer), `reach` climbing to
`377`, and stratum `3`. `show ntp status` on the clients must report stratum
`4` (master +1).

---

### Task 3: Add MD5 authentication to the NTP hierarchy

- Create authentication key ID **1** with MD5 string `NTP_KEY_1` on all three
  routers (master and both clients).
- Enable NTP authentication globally and declare key 1 as trusted.
- On R2 and R3, bind key 1 to the `ntp server` statement that points at R1.
- Confirm that associations stay synchronized after the change.

**Verification:** `show ntp associations detail` on R2 must show
`authenticated`. `show ntp authentication-status` must report `authentication
enabled`. `show ntp status` must still show `Clock is synchronized`.

---

### Task 4: Interpret the pre-loaded QoS policy on R1

Read `show policy-map LAN-OUT` and `show run | section class-map|policy-map`
on R1, then answer the five questions below in Section 6. Do not modify any
QoS configuration.

**Verification:** You can produce the answer to each Section 6 question with
only the outputs of `show policy-map interface Gi0/1`, `show class-map`, and
`show policy-map LAN-OUT`.

---

### Task 5: Verify end-to-end baseline reachability

- `PC1 ping 203.0.113.1` (R3 simulated internet server) -- must succeed.
- `PC1 ping 2.2.2.2` (R2 loopback over OSPF) -- must succeed.

**Verification:** Both pings return replies (TTL typically 253 after three
hops through the LAN and R1→R3).

---

## 6. Verification & Analysis

### NTP hierarchy -- end state

```bash
R1# show ntp status
Clock is synchronized, stratum 3, reference is 127.127.1.1         ! ← stratum 3, master itself
nominal freq is 1000.0003 Hz, actual freq is 1000.0003 Hz, precision is 2**10
...

R2# show ntp status
Clock is synchronized, stratum 4, reference is 1.1.1.1             ! ← stratum 4, synced to R1
...

R2# show ntp associations
  address         ref clock       st   when   poll reach  delay  offset   disp
*~1.1.1.1        .LOCL.            3     32     64   377  2.016   0.050  1.031   ! ← *, stratum 3, reach 377 = fully synced

R2# show ntp associations detail
1.1.1.1 configured, authenticated, our_master, sane, valid, stratum 3   ! ← authenticated must be present
ref ID 127.127.1.1, time E1234567.89ABCDEF (00:00:00.000 UTC Mon Jan 1 2035)
```

### QoS policy interpretation -- answer these five questions

```bash
R1# show policy-map LAN-OUT
 Policy Map LAN-OUT
   Class VOICE
    priority percent 10                          ! ← Q1: what action here?
   Class VIDEO
    bandwidth percent 20
    random-detect dscp-based                     ! ← Q2: what does WRED do here?
   Class CRITICAL-DATA
    bandwidth percent 30
   Class SCAVENGER
    police cir 128000
     conform-action transmit
     exceed-action drop                          ! ← Q3: what happens to exceeding traffic?
   Class class-default
    fair-queue
    random-detect                                ! ← Q4: why WRED on default?
```

**Answer each in one sentence:**

- **Q1 -- VOICE action:** Packets marked DSCP EF receive strict-priority
  service (LLQ) capped at 10% of the interface bandwidth during congestion.
- **Q2 -- VIDEO WRED:** `random-detect dscp-based` uses per-DSCP drop
  profiles (AF41 has lower drop probability than AF42/AF43) so that video is
  preferentially dropped from lower drop-precedence.
- **Q3 -- SCAVENGER police exceed:** Traffic that exceeds 128 kbps is
  dropped.
- **Q4 -- class-default WRED:** Prevents TCP global synchronization by
  randomly dropping packets as the default queue fills, instead of waiting
  for tail-drop.
- **Q5 -- What DSCP value triggers the VOICE class?** DSCP EF (46 /
  `101110`) because `class-map match-any VOICE` matches `dscp ef`.

### End-to-end reachability

```bash
PC1> ping 203.0.113.1
84 bytes from 203.0.113.1 icmp_seq=1 ttl=253 time=3.987 ms       ! ← baseline works
```

---

## 7. Verification Cheatsheet

### NTP Configuration

```
ntp master <stratum>
ntp server <ip> [key <id>] [prefer]
ntp peer <ip>
ntp authentication-key <id> md5 <string>
ntp authenticate
ntp trusted-key <id>
```

| Command | Purpose |
|---------|---------|
| `ntp master 3` | Become authoritative at stratum 3 |
| `ntp server 1.1.1.1 key 1` | Sync to 1.1.1.1 using key 1 |
| `ntp authentication-key 1 md5 KEY` | Define key 1 with MD5 hash |
| `ntp authenticate` | Require authentication on all sync |
| `ntp trusted-key 1` | Mark key 1 as acceptable for sync |

> **Exam tip:** Both sides must have identical `authentication-key` (same ID,
> same string) and both must run `ntp authenticate` + `ntp trusted-key`. The
> client also needs `key <id>` on the `ntp server` line. Miss any of those
> four components and sync silently fails.

### NTP Verification

| Command | What to Look For |
|---------|-----------------|
| `show ntp status` | `Clock is synchronized` + stratum number |
| `show ntp associations` | `*` in first column = selected peer; `reach 377` = 8/8 polls OK |
| `show ntp associations detail` | `authenticated`, `sane`, `valid`, `our_master` |
| `show ntp authentication-status` | `authentication enabled` |
| `debug ntp packet` | Only use on a lab device -- verbose |

### QoS / MQC Verification

| Command | What to Look For |
|---------|-----------------|
| `show policy-map` | All policy-maps on the box |
| `show policy-map LAN-OUT` | Config of a specific policy |
| `show policy-map interface Gi0/1` | Run-time counters (matched / dropped) per class |
| `show class-map` | All class-maps and their match criteria |
| `show run | section policy-map` | Full MQC stanza for review |

> **Exam tip:** On the exam, `show policy-map interface` is the single most
> useful command -- it shows every class with its matched-packets counter
> and action-level stats (policer conforms/exceeds, WRED drops). If a class
> shows zero matches, your match criteria is wrong.

### Common NTP Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| Association never reaches `reach 377` | Client can't ping master (routing) |
| `show ntp assoc` shows peer but no `*` | Stratum higher than expected, insane, or invalid |
| `show ntp assoc detail` shows `unauthenticated` | Key mismatch or `ntp trusted-key` missing |
| Client stratum = 16 | Never synced -- peer unreachable or `ntp authenticate` not set |

### Common QoS Interpretation Traps

| Trap | Watch For |
|------|-----------|
| `match-any` vs `match-all` | `match-any` = OR; easy to over-match |
| `priority` vs `bandwidth` | priority = cap (LLQ); bandwidth = floor (CBWFQ) |
| `police` vs `shape` | police = drop above rate; shape = buffer + smooth |
| Class order in policy-map | Matched in order; first match wins |
| WRED without `bandwidth` | WRED in `class-default` is valid; WRED without queueing is not |

### Wildcard / DSCP Quick Reference

| Subnet Mask | Wildcard | Common Use |
|-------------|----------|------------|
| /24 | 0.0.0.255 | LAN segment |
| /30 | 0.0.0.3 | Point-to-point link |

| Class | DSCP | Decimal | Typical Traffic |
|-------|------|---------|-----------------|
| EF | 46 | 46 | Voice RTP |
| AF41 | 34 | 34 | Video |
| AF31 | 26 | 26 | Business data |
| CS1 | 8 | 8 | Scavenger |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Task 1-3: NTP Master + Clients + Authentication

<details>
<summary>Click to view R1 Configuration (NTP master)</summary>

```bash
R1(config)# ntp authentication-key 1 md5 NTP_KEY_1
R1(config)# ntp authenticate
R1(config)# ntp trusted-key 1
R1(config)# ntp master 3
```
</details>

<details>
<summary>Click to view R2 Configuration (NTP client)</summary>

```bash
R2(config)# ntp authentication-key 1 md5 NTP_KEY_1
R2(config)# ntp authenticate
R2(config)# ntp trusted-key 1
R2(config)# ntp server 1.1.1.1 key 1
```
</details>

<details>
<summary>Click to view R3 Configuration (NTP client)</summary>

```bash
R3(config)# ntp authentication-key 1 md5 NTP_KEY_1
R3(config)# ntp authenticate
R3(config)# ntp trusted-key 1
R3(config)# ntp server 1.1.1.1 key 1
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ntp status
show ntp associations
show ntp associations detail
show ntp authentication-status
```
</details>

### Task 4: QoS Answers

<details>
<summary>Click to view Answers</summary>

- Q1 -- Voice is strict-priority (LLQ), capped at 10% during congestion.
- Q2 -- WRED dscp-based drops AF42/AF43 before AF41 as the queue fills.
- Q3 -- Scavenger exceeding 128 kbps is dropped.
- Q4 -- class-default uses WRED to avoid TCP global synchronization.
- Q5 -- DSCP EF (46) hits the VOICE class.
</details>

### Task 5: End-to-end Verification

<details>
<summary>Click to view Verification</summary>

```bash
PC1> ping 203.0.113.1
PC1> ping 2.2.2.2
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

### Ticket 1 -- R2 Reports Clock Stratum 16 And Never Syncs

After configuring NTP, `show ntp status` on R2 reports stratum 16 ("clock not
set") even though R1 is serving as master. The association to 1.1.1.1 exists
but never gets a `*` marker.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py`

**Success criteria:** R2 reaches stratum 4 (master +1), `*` next to 1.1.1.1
in associations, `authenticated` in association detail.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `R2# show ntp associations detail` -- look for `unauthenticated` and
   `configured, unsynced`.
2. `R2# show run | include ntp` -- check authentication-key, trusted-key,
   server line, authenticate.
3. Compare the `md5` string on R1 and R2 -- one of them is wrong.
</details>

<details>
<summary>Click to view Fix</summary>

The key on R2 was set to `WRONG_KEY` instead of `NTP_KEY_1`. Remove and
re-add with the correct value:

```bash
R2(config)# no ntp authentication-key 1 md5 WRONG_KEY
R2(config)# ntp authentication-key 1 md5 NTP_KEY_1
```

Wait 1-2 poll cycles (64 seconds each by default) for `reach` to climb.
</details>

---

### Ticket 2 -- R3 Cannot Reach R1's Loopback For NTP

R3's NTP association to 1.1.1.1 shows `reach 0`. `show ntp associations`
never advances. `ping 1.1.1.1 source Lo0` from R3 also fails.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py`

**Success criteria:** R3 pings 1.1.1.1, NTP association reaches `reach 377`
and stratum 4.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `R3# ping 1.1.1.1` -- fails. Rules out NTP; this is routing.
2. `R3# show ip route 1.1.1.1` -- no route.
3. `R3# show ip ospf neighbor` -- no neighbor on Gi0/0 (toward R1).
4. `R3# show run interface Gi0/0` -- `ip ospf 1 area 1` (wrong area).
</details>

<details>
<summary>Click to view Fix</summary>

```bash
R3(config)# interface Gi0/0
R3(config-if)# no ip ospf 1 area 1
R3(config-if)# ip ospf 1 area 0
```
</details>

---

### Ticket 3 -- QoS Policy Dropping All Traffic On R1 Uplink

Operators report PC1 can no longer reach 203.0.113.1. `show policy-map
interface Gi0/1` on R1 shows enormous drop counters in `class-default`.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py`

**Success criteria:** PC1 reaches 203.0.113.1; `show policy-map interface`
shows traffic conforming (not exceeding) in class-default.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `R1# show policy-map interface Gi0/1` -- note enormous drop counter on
   `class-default`.
2. `R1# show run policy-map LAN-OUT` -- a `police cir 8000` has been added to
   `class-default`, rate-limiting everything to 8 kbps.
</details>

<details>
<summary>Click to view Fix</summary>

```bash
R1(config)# policy-map LAN-OUT
R1(config-pmap)# class class-default
R1(config-pmap-c)# no police cir 8000
```
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] R1 configured as NTP master at stratum 3
- [ ] R2 and R3 configured as NTP clients pointing at 1.1.1.1
- [ ] MD5 authentication key 1 = `NTP_KEY_1` on all three routers
- [ ] `ntp authenticate` and `ntp trusted-key 1` on all three routers
- [ ] `key 1` appended to the `ntp server` line on clients
- [ ] R2 and R3 show stratum 4 synced to 1.1.1.1
- [ ] `show ntp associations detail` reports `authenticated` on R2 and R3
- [ ] QoS Q1-Q5 answered from pre-loaded `LAN-OUT` policy
- [ ] PC1 pings 203.0.113.1 (baseline reachability)

### Troubleshooting

- [ ] Ticket 1 -- authentication key mismatch diagnosed and fixed
- [ ] Ticket 2 -- OSPF area mismatch diagnosed and fixed
- [ ] Ticket 3 -- QoS class-default policer removed; reachability restored
