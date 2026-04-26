# BGP Comprehensive Troubleshooting -- Capstone II

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

**Exam Objective:** 350-401 blueprint bullet 3.2.c -- *Configure and verify eBGP between
directly connected neighbors (best path selection and neighbor relationships)* -- applied
in a full fault-diagnosis context.

This is the final BGP capstone. The network ships pre-broken: six independent faults
have been injected across all four routers and span every sub-topic covered in
labs 00-03 (peering, iBGP/eBGP, MP-BGP address families, next-hop behavior, network
statements, and inbound/outbound route-maps). Your task is to diagnose each symptom
from `show` command output alone, then restore full dual-stack reachability between
PC1 and PC2 without introducing any new faults.

### Systematic BGP Troubleshooting Methodology

When a BGP session or prefix is missing, work down the layers in order. Skipping a
layer is how production troubleshooters waste hours -- always start from the bottom.

| Layer | Question | Key Command |
|-------|----------|-------------|
| 1. Transport | Is the TCP/179 path reachable? | `ping <peer>`, `show ip route <peer>` |
| 2. Neighbor | Is the session Established? | `show ip bgp summary`, `show bgp ipv6 uni sum` |
| 3. AS match | Does my `remote-as` match the peer's local AS? | `show run | sec router bgp`, peer log |
| 4. Activation | Is the neighbor activated in the correct address family? | `show bgp ipv4 uni summary`, `show bgp ipv6 uni summary` |
| 5. Advertisement | Am I advertising the prefix? | `show ip bgp neighbor <peer> advertised-routes` |
| 6. Reception | Is the peer receiving the prefix? | `show ip bgp neighbor <peer> received-routes` (soft-reconfig inbound) |
| 7. Path selection | Is the right path becoming best? | `show ip bgp <prefix>` -- examine attributes |
| 8. Recursive next-hop | Is the next-hop reachable in the RIB? | `show ip route <next-hop>` |

### Fault Categories You Will See

Every fault in this lab maps to exactly one of these categories. Learning to name
the category from the symptom is half the battle.

| Category | Typical Symptom |
|----------|-----------------|
| AS number mismatch | Session stuck in `Idle` or `Active`; log shows "bad BGP identifier" / "remote AS mismatch" |
| Missing `next-hop-self` on iBGP | iBGP routes present but marked `> i` is absent; `show ip route <next-hop>` fails |
| Bad `network` statement | Prefix absent from `show ip bgp` on the originator; no advertisement downstream |
| Inbound route-map blocking | `show ip bgp neighbor X received-routes` shows prefixes but `show ip bgp` hides them |
| IPv6 AF not activated | IPv4 session Established but `show bgp ipv6 uni summary` shows nothing |
| Missing address-family network | Prefix exists in RIB but never appears in BGP -- neighbor never learns it |

### MP-BGP Activation Discipline

Remember: when you add a `neighbor X.X.X.X remote-as N` at the router process level,
IOS activates that neighbor in the IPv4 address family **by default**. You must
explicitly `no neighbor X.X.X.X activate` in wrong-AF stanzas and explicitly
`neighbor Y:Y:: activate` in the correct one. A "silent" IPv6 session that never
comes up often turns out to be an unactivated IPv6 neighbor.

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| Symptom-to-fault mapping | Translate a show-command observation into a hypothesis about the misconfiguration |
| Layer-by-layer isolation | Work from TCP/transport up to path selection, never skipping a step |
| Concurrent-fault diagnosis | Resolve multiple independent faults without regressing one while fixing another |
| Verification discipline | Confirm each fix with a show command before moving to the next ticket |
| Root-cause analysis | Produce a one-line cause for each ticket, not just a fix |

---

## 2. Topology & Scenario

```
                      ┌─────────────────────────┐
                      │           R3            │
                      │   (ISP / Transit)       │
                      │      AS 65002          │
                      │   Lo0: 3.3.3.3         │
                      │ Lo0v6: 2001:DB8:FF::3  │
                      └──┬───────────┬───────┬──┘
                   Gi0/0 │           │ Gi0/1 │ Gi0/2
                         │           │       │
            10.0.13.0/30 │           │       │ 10.0.34.0/30
           2001:DB8:13/64│           │       │ 2001:DB8:34/64
                         │           │       │
   ┌─────────────────────┘           │       └─────────────────────┐
   │                                 │                              │
   │ Gi0/1                     Gi0/1 │                        Gi0/0 │
┌──┴────────────┐         ┌──────────┴────┐                ┌────────┴───────┐
│      R1       │         │       R2      │                │       R4       │
│  Ent. Edge 1  │─────────│  Ent. Edge 2  │                │   Remote Site  │
│  AS 65001    │  Gi0/0  │   AS 65001   │                │   AS 65003    │
│Lo0: 1.1.1.1  │ 10.0.12 │ Lo0: 2.2.2.2 │                │ Lo0: 4.4.4.4  │
│     │ Gi0/2  │ /30     │               │                │      │ Gi0/1  │
└─────┼────────┘         └───────────────┘                └──────┼────────┘
      │                                                            │
      │ 192.168.1.0/24                           192.168.2.0/24    │
      │ 2001:DB8:1:1::/64                        2001:DB8:2:2::/64 │
   ┌──┴──┐                                                       ┌┴──┐
   │ PC1 │                                                       │PC2│
   └─────┘                                                       └───┘
```

### Scenario

The network was fully operational at the end of Lab 03. During a change window last
night, an on-call engineer pushed six unapproved configuration changes across R1-R4
before being pulled onto another incident. The shift handover log contains only:
*"BGP broken on multiple routers, PC1 can't reach PC2, escalating."*

No fault list was recorded. No config backup was taken. Your job is to diagnose
every fault from the routers themselves, restore full dual-stack reachability, and
document each root cause before the morning handover.

---

## 3. Hardware & Environment Specifications

### Console Access Table

| Device | Port | Connection Command |
|--------|------|--------------------|
| R1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R3 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R4 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| PC1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| PC2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |

### Cabling

| Link | From | To | Subnet (v4 / v6) |
|------|------|----|--------------------|
| L1 | R1 Gi0/0 | R2 Gi0/0 | 10.0.12.0/30 / 2001:DB8:12::/64 |
| L2 | R1 Gi0/1 | R3 Gi0/0 | 10.0.13.0/30 / 2001:DB8:13::/64 |
| L3 | R2 Gi0/1 | R3 Gi0/1 | 10.0.23.0/30 / 2001:DB8:23::/64 |
| L4 | R1 Gi0/2 | PC1 e0 | 192.168.1.0/24 / 2001:DB8:1:1::/64 |
| L5 | R3 Gi0/2 | R4 Gi0/0 | 10.0.34.0/30 / 2001:DB8:34::/64 |
| L6 | R4 Gi0/1 | PC2 e0 | 192.168.2.0/24 / 2001:DB8:2:2::/64 |

---

## 4. Base Configuration

`setup_lab.py` pushes the pre-broken configs from `initial-configs/` to each
router. The configs contain:

- Full interface addressing (v4 + v6, all interfaces up)
- OSPFv2 and OSPFv3 on R1-R2 internal link
- BGP process on each router with peer statements, address families, and policies
- **Six injected faults** -- your job to find and fix every one

**NOT pre-loaded:**

- Nothing is missing from the reference topology; the faults are misconfigurations,
  not omissions. Every fault is a change you could reasonably make by typo or
  copy-paste. You must not rebuild the configs from scratch -- diagnose and fix in
  place.

---

## 5. Lab Challenge: Comprehensive Troubleshooting

> This is a capstone lab. The network is pre-broken.
> Diagnose and resolve 5+ concurrent faults spanning all blueprint bullets.
> No step-by-step guidance is provided -- work from symptoms only.

### What You Are Given

- All routers are reachable on the console; all physical links are up
- Loopbacks are addressed correctly; IGP (OSPFv2 + OSPFv3 between R1 and R2) is
  working
- Every router has a BGP process running and every peer statement is present

### What You Must Achieve

By the end of this lab, the following must all be true simultaneously:

- All four expected BGP sessions are Established in **both** address families
  (IPv4 and IPv6):
  - R1 ↔ R2 iBGP (v4 over Lo0, v6 over Lo0 v6)
  - R1 ↔ R3 eBGP (v4, v6)
  - R2 ↔ R3 eBGP (v4, v6)
  - R3 ↔ R4 eBGP (v4, v6)
- R1's BGP table contains `172.16.3.0/24`, `172.16.4.0/24`, `192.168.2.0/24`, plus
  the IPv6 equivalents
- R2's BGP table contains the same prefixes (learned via iBGP from R1 and via eBGP
  from R3)
- R4's BGP table contains `172.16.1.0/24`, `172.16.3.0/24`, and `192.168.1.0/24`,
  plus the IPv6 equivalents
- **End-to-end reachability:** `PC1 ping 192.168.2.10` succeeds, and
  `PC1 ping 2001:db8:2:2::10` succeeds
- No new faults introduced: path selection still honors LOCAL_PREF (R1 is preferred
  exit within AS 65001) and MED (R1 is preferred entry into AS 65001 from R3)

### Rules of Engagement

- Work from **show commands only** until you have a hypothesis -- do not blind-edit
  configs
- Record each fault's root cause in one line before applying the fix
- After each fix, re-verify the affected session/prefix before moving on
- Do **not** run `apply_solution.py` until you have tried every ticket yourself

---

## 6. Verification & Analysis

The following end-state outputs are what the restored network must produce. Use
them as the target picture while you work through the tickets.

### R1 -- BGP Summary (both AFs, all sessions Established)

```bash
R1# show ip bgp summary
Neighbor        V           AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
2.2.2.2         4        65001      45      45        9    0    0 00:10:12        3   ! iBGP session Up, receiving prefixes
10.0.13.2       4        65002      52      51        9    0    0 00:11:03        3   ! eBGP to R3 Up

R1# show bgp ipv6 unicast summary
Neighbor        V           AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
2001:DB8:13::2  4        65002      46      47        8    0    0 00:10:45        3   ! IPv6 eBGP session must be Up (Fault 5)
2001:DB8:FF::2  4        65001      42      43        8    0    0 00:10:30        2   ! IPv6 iBGP session Up
```

### R2 -- BGP Summary

```bash
R2# show ip bgp summary
Neighbor        V           AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
1.1.1.1         4        65001      45      44        9    0    0 00:10:12        3   ! iBGP Up after Fault 1 fix
10.0.23.2       4        65002      51      52        9    0    0 00:10:58        3   ! Must show >0 prefixes (Fault 6 fix)

R2# show ip bgp
   Network          Next Hop            Metric LocPrf Weight Path
*>i 172.16.1.0/24    1.1.1.1                  0    100      0 i     ! learned via iBGP from R1
*>i 172.16.4.0/24    1.1.1.1                200    200      0 65002 65003 i  ! via iBGP, local_pref 200 wins
*  172.16.3.0/24    10.0.23.2              100      0      0 65002 i   ! MED 100 from R3 direct
*>i 172.16.3.0/24    1.1.1.1                 50    200      0 65002 i  ! iBGP path wins on LOCAL_PREF
```

### R4 -- BGP Summary

```bash
R4# show ip bgp
   Network          Next Hop            Metric LocPrf Weight Path
*>  172.16.1.0/24    10.0.34.1                          0 65002 65001 i
*>  172.16.3.0/24    10.0.34.1                          0 65002 i
*>  172.16.4.0/24    0.0.0.0                  0      32768 i    ! locally originated
*>  192.168.1.0      10.0.34.1                          0 65002 65001 i
*>  192.168.2.0      0.0.0.0                  0      32768 i    ! Fault 4 fix restores this
```

### End-to-End Reachability

```bash
PC1> ping 192.168.2.10

84 bytes from 192.168.2.10 icmp_seq=1 ttl=61 time=4.213 ms   ! ← TTL 61 (3 hops traversed)
84 bytes from 192.168.2.10 icmp_seq=2 ttl=61 time=3.987 ms

PC1> ping 2001:db8:2:2::10

2001:db8:2:2::10 icmp_seq=1 ttl=61 time=4.102 ms             ! ← Dual-stack reachability restored
```

---

## 7. Verification Cheatsheet

### BGP Neighbor-State Diagnosis

```
show ip bgp summary
show bgp ipv6 unicast summary
show ip bgp neighbors <peer>
show tcp brief
```

| Command | Purpose |
|---------|---------|
| `show ip bgp summary` | Session state + prefix count per IPv4 neighbor |
| `show bgp ipv6 unicast summary` | Same, for IPv6 AF |
| `show ip bgp neighbors <peer>` | Full neighbor detail -- AS, update source, last error |
| `show tcp brief` | TCP/179 session actually open? (rules out transport) |

> **Exam tip:** `Idle` with no retry attempts usually means TCP unreachable (route
> missing or peer unreachable). `Active` means we're trying -- look for AS mismatch.

### Advertisement Verification

```
show ip bgp neighbors <peer> advertised-routes
show ip bgp neighbors <peer> received-routes
clear ip bgp <peer> soft in
```

| Command | Purpose |
|---------|---------|
| `show ip bgp neighbors X advertised-routes` | What WE are sending to X |
| `show ip bgp neighbors X received-routes` | What X sends us **before** inbound policy (needs soft-reconfig) |
| `show ip bgp neighbors X routes` | Post-policy routes from X (what actually hits RIB) |
| `clear ip bgp X soft in` | Re-run inbound policy without tearing down session |
| `clear ip bgp X soft out` | Re-advertise to X without session reset |

> **Exam tip:** A prefix present in `received-routes` but absent from `show ip bgp`
> is the classic inbound route-map block. Compare those two outputs side by side.

### Prefix Origin Verification

```
show ip bgp <prefix>
show ip route <prefix>
show run | sec router bgp
```

| Command | Purpose |
|---------|---------|
| `show ip bgp <prefix>` | All paths to a specific prefix + attribute values |
| `show ip route <next-hop>` | Is the BGP next-hop reachable in the RIB? (iBGP gotcha) |
| `show run | sec router bgp` | Fast visual on `network` statements and neighbor policies |

### Address-Family Activation Check

```
show bgp ipv4 unicast summary
show bgp ipv6 unicast summary
show run | sec router bgp.*address-family
```

| Command | What to Look For |
|---------|-----------------|
| Per-AF summary | Missing neighbor row = not activated in this AF |
| `show run | sec address-family` | Explicit `neighbor X activate` / `no neighbor Y activate` |

> **Exam tip:** A v6 neighbor defined under the process but never activated in
> `address-family ipv6` will never come up, yet won't error at config time. Always
> check the per-AF summary, not just `show ip bgp summary`.

### Common BGP Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| Session Idle, no log messages | Peer unreachable on TCP/179; check IGP / update-source |
| Session Active, log shows "bad remote AS" | `remote-as` mismatch on one side |
| Session Up, no prefixes received | IPv6 AF not activated, or inbound route-map deny |
| Prefix present on originator, missing on peer | `network` statement typo or missing-AF network |
| iBGP prefix in BGP table marked `i` but not best | Next-hop unreachable in RIB -- `next-hop-self` missing |
| Path selection wrong (not honoring LOCAL_PREF) | Route-map not attached inbound, or wrong direction |

### Wildcard Mask Quick Reference

| Subnet Mask | Wildcard Mask | Common Use |
|-------------|---------------|------------|
| /30 (255.255.255.252) | 0.0.0.3 | Point-to-point link |
| /24 (255.255.255.0) | 0.0.0.255 | LAN segment |
| /32 (255.255.255.255) | 0.0.0.0 | Single loopback |

---

## 8. Solutions (Spoiler Alert!)

> Try to diagnose every ticket before peeking. Each `<details>` block reveals the
> fault and the restore command for one of the six injected faults.

### Fault 1: R1 iBGP peer has wrong remote-as

<details>
<summary>Click to view Root Cause and Fix</summary>

**Root cause:** On R1, `neighbor 2.2.2.2 remote-as 65099` -- should be `65001`
(both R1 and R2 are in AS 65001). Session stuck in `Active`.

**Detection:**
```bash
R1# show ip bgp summary | include 2.2.2.2
2.2.2.2         4        65099       0       0        1    0    0 never    Active
R1# show ip bgp neighbors 2.2.2.2 | include remote AS
  BGP neighbor is 2.2.2.2,  remote AS 65099, local AS 65001, internal link
```

**Fix:**
```bash
R1(config)# router bgp 65001
R1(config-router)# no neighbor 2.2.2.2 remote-as 65099
R1(config-router)# neighbor 2.2.2.2 remote-as 65001
R1(config-router)# neighbor 2.2.2.2 update-source Loopback0
```

Note: removing and re-adding the neighbor drops other neighbor sub-commands --
re-apply `update-source Loopback0` and (later) `activate` + `next-hop-self` +
route-map in the IPv4 AF.
</details>

### Fault 2: R2 missing `next-hop-self` on iBGP to R1 (IPv4 AF)

<details>
<summary>Click to view Root Cause and Fix</summary>

**Root cause:** R2's `address-family ipv4` lacks `neighbor 1.1.1.1 next-hop-self`.
Once R2 starts sending R3's prefixes to R1 via iBGP, R1 sees next-hop `10.0.23.2`
(R2-R3 link) which R1 cannot resolve -- the eBGP link is not in OSPF.

**Detection:**
```bash
R1# show ip bgp 172.16.3.0
BGP routing table entry for 172.16.3.0/24
 Refresh Epoch 1
  65002, (received-only)
    10.0.23.2 (inaccessible) from 2.2.2.2 (2.2.2.2)    ! ← inaccessible = NH unreachable
```

**Fix on R2:**
```bash
R2(config)# router bgp 65001
R2(config-router)# address-family ipv4
R2(config-router-af)# neighbor 1.1.1.1 next-hop-self
R2(config-router-af)# end
R2# clear ip bgp 1.1.1.1 soft out
```
</details>

### Fault 3: R3 wrong `network` statement (172.16.13.0 instead of 172.16.3.0)

<details>
<summary>Click to view Root Cause and Fix</summary>

**Root cause:** Under R3 `address-family ipv4`, the statement reads
`network 172.16.13.0 mask 255.255.255.0`. R3's Lo1 is `172.16.3.1/24`, so there
is no RIB entry matching `172.16.13.0/24` -- BGP has nothing to advertise.

**Detection:**
```bash
R3# show ip bgp | include 172.16
# (no 172.16.3.0/24 entry — because network statement references a prefix not in RIB)
R3# show run | section router bgp
 network 172.16.13.0 mask 255.255.255.0    ! ← typo
```

**Fix:**
```bash
R3(config)# router bgp 65002
R3(config-router)# address-family ipv4
R3(config-router-af)# no network 172.16.13.0 mask 255.255.255.0
R3(config-router-af)# network 172.16.3.0 mask 255.255.255.0
```
</details>

### Fault 4: R4 missing IPv4 `network 192.168.2.0` statement

<details>
<summary>Click to view Root Cause and Fix</summary>

**Root cause:** R4's `address-family ipv4` only advertises `172.16.4.0/24`. The
PC2 LAN prefix `192.168.2.0/24` is in R4's RIB (connected) but never enters BGP.
PC1 cannot reach PC2 on IPv4.

**Detection:**
```bash
R4# show ip bgp | include 192.168
# (no 192.168.2.0 entry)
R3# show ip bgp neighbors 10.0.34.2 received-routes | include 192.168
# (no 192.168.2.0 received)
```

**Fix:**
```bash
R4(config)# router bgp 65003
R4(config-router)# address-family ipv4
R4(config-router-af)# network 192.168.2.0
```
</details>

### Fault 5: R1 IPv6 eBGP neighbor 2001:DB8:13::2 not activated

<details>
<summary>Click to view Root Cause and Fix</summary>

**Root cause:** Under R1 `address-family ipv6`, the line `no neighbor 2001:DB8:13::2
activate` is present. The TCP session to R3 comes up but R3 sees no activity on
IPv6 prefix exchange.

**Detection:**
```bash
R1# show bgp ipv6 unicast summary | include 2001:DB8:13
# (no 2001:DB8:13::2 row — not activated in this AF)
R1# show run | section address-family ipv6
  no neighbor 2001:DB8:13::2 activate    ! ← the culprit
```

**Fix:**
```bash
R1(config)# router bgp 65001
R1(config-router)# address-family ipv6
R1(config-router-af)# neighbor 2001:DB8:13::2 activate
R1(config-router-af)# neighbor 2001:DB8:13::2 route-map LOCAL_PREF_V6_FROM_R3 in
```
</details>

### Fault 6: R2 inbound route-map denies all IPv4 prefixes from R3

<details>
<summary>Click to view Root Cause and Fix</summary>

**Root cause:** R2 has `neighbor 10.0.23.2 route-map BLOCK_FROM_R3 in` applied,
and `BLOCK_FROM_R3` is a `deny 10` route-map matching all prefixes. R2 receives
the updates but discards them -- 0 prefixes in the BGP table from R3 direct.

**Detection:**
```bash
R2# show ip bgp summary | include 10.0.23.2
10.0.23.2       4        65002      52      51        9    0    0 00:10:03        0   ! ← 0 prefixes!
R2# show ip bgp neighbors 10.0.23.2 received-routes
   Network          Next Hop       Metric LocPrf Weight Path
*  172.16.3.0/24    10.0.23.2         100             0 65002 i     ! ← prefixes ARE received
# but `show ip bgp` shows nothing from 10.0.23.2 → blocked inbound
R2# show run | section route-map
route-map BLOCK_FROM_R3 deny 10
 match ip address prefix-list ALL_V4
```

**Fix:**
```bash
R2(config)# router bgp 65001
R2(config-router)# address-family ipv4
R2(config-router-af)# no neighbor 10.0.23.2 route-map BLOCK_FROM_R3 in
R2(config-router-af)# neighbor 10.0.23.2 route-map LOCAL_PREF_FROM_R3 in
R2(config-router-af)# end
R2# clear ip bgp 10.0.23.2 soft in
R2(config)# no route-map BLOCK_FROM_R3
R2(config)# no ip prefix-list BLOCK_ALL
```

Also soft-clear R2→R3 `clear ip bgp 10.0.23.2 soft in` so the prefixes re-enter.
</details>

### Final Verification (all fixes applied)

<details>
<summary>Click to view End-State Commands</summary>

```bash
# All sessions must be Established in both AFs:
R1# show ip bgp summary
R1# show bgp ipv6 unicast summary
R2# show ip bgp summary
R2# show bgp ipv6 unicast summary
R3# show ip bgp summary
R4# show ip bgp summary

# End-to-end dual-stack reachability:
PC1> ping 192.168.2.10
PC1> ping 2001:db8:2:2::10

# Path selection still correct:
R2# show ip bgp 172.16.4.0   ! best path must be via 1.1.1.1 (iBGP, LOCAL_PREF 200)
R1# show ip bgp 172.16.4.0   ! best path via 10.0.13.2 with LOCAL_PREF 200
```
</details>

---

## 9. Troubleshooting Scenarios

All six faults are **pre-injected** via `setup_lab.py`. There are no separate
inject scripts in this lab -- the initial configs ARE the broken state. Work each
ticket sequentially or in parallel, as you prefer.

### Workflow

```bash
python3 setup_lab.py                               # pushes pre-broken configs (all 6 faults)
# (diagnose + fix each ticket below)
python3 scripts/fault-injection/apply_solution.py  # restore to known-good (lab-03 end-state)
```

---

### Ticket 1 -- R1 Reports iBGP Session to R2 Stuck in Active

R1's iBGP session to R2 (`2.2.2.2`) will not come up despite both loopbacks being
reachable over OSPF. `show ip bgp summary` lists the session but prefix count is 0
and the state alternates between Active and Idle.

**Success criteria:** R1-R2 iBGP session Established in IPv4 AF; 3+ prefixes
received from R2.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Confirm transport: `R1# ping 2.2.2.2 source lo0` -- should succeed (OSPF).
2. Check neighbor detail: `R1# show ip bgp neighbors 2.2.2.2 | i remote AS` --
   shows local AS 65001, remote AS something-other-than-65001.
3. Compare: `R2# show run | sec router bgp` -- R2 says its own AS is 65001.
4. Mismatch confirmed -- R1's `remote-as` for 2.2.2.2 is wrong.
</details>

<details>
<summary>Click to view Fix</summary>

See [Solutions: Fault 1](#fault-1-r1-ibgp-peer-has-wrong-remote-as).
</details>

---

### Ticket 2 -- R1 Learns R3's Prefixes Via iBGP As "Inaccessible"

After fixing Ticket 1, R1's BGP table shows `172.16.3.0/24` and `172.16.4.0/24`
learned from R2 (via iBGP) with next-hop `10.0.23.2` marked **(inaccessible)**.
These paths never become best; traffic egresses via the direct R1-R3 eBGP path
only.

**Success criteria:** R1 sees valid iBGP paths for R3/R4 prefixes with a reachable
next-hop (1.1.1.1 or 2.2.2.2).

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `R1# show ip bgp 172.16.3.0` -- note `10.0.23.2 (inaccessible)`.
2. `R1# show ip route 10.0.23.2` -- no route. R1 has no path to the R2-R3 eBGP
   link (it's not in OSPF by design -- external link).
3. Classic iBGP next-hop problem -- R2 should rewrite the next-hop to its own
   loopback before advertising to R1.
4. `R2# show run | sec address-family ipv4` -- `neighbor 1.1.1.1 next-hop-self`
   is missing.
</details>

<details>
<summary>Click to view Fix</summary>

See [Solutions: Fault 2](#fault-2-r2-missing-next-hop-self-on-ibgp-to-r1-ipv4-af).
</details>

---

### Ticket 3 -- R3's Loopback1 Prefix Is Missing From Every BGP Table

R1, R2, and R4 all lack `172.16.3.0/24` entirely. The prefix is directly connected
on R3 (Lo1), so this is an advertisement failure -- not a propagation failure.

**Success criteria:** `show ip bgp 172.16.3.0` on R1 returns a valid entry with
AS_Path `65002`.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Originator-side check: `R3# show ip bgp | include 172.16` -- prefix absent
   from R3's OWN BGP table. Fault is on R3.
2. `R3# show ip route 172.16.3.0` -- connected on Lo1 (RIB has it).
3. `R3# show run | section router bgp` -- look at IPv4 AF network statements.
   `network 172.16.13.0 mask 255.255.255.0` -- typo, one digit off.
</details>

<details>
<summary>Click to view Fix</summary>

See [Solutions: Fault 3](#fault-3-r3-wrong-network-statement-1721613-0-instead-of-172163-0).
</details>

---

### Ticket 4 -- PC1 Cannot Reach PC2 on IPv4 Despite All Sessions Up

Every BGP session is Established. R3 learns `172.16.4.0/24` from R4 correctly.
But PC1 pings to PC2 (`192.168.2.10`) time out, and `show ip bgp 192.168.2.0`
on any enterprise router returns no entry.

**Success criteria:** PC1 ping 192.168.2.10 succeeds; `192.168.2.0/24` present
in BGP tables of R1, R2, and R3.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Originator check: `R4# show ip bgp | i 192.168` -- prefix absent on R4. Fault
   is on R4.
2. `R4# show ip route 192.168.2.0` -- connected on Gi0/1 (RIB has it).
3. `R4# show run | sec address-family ipv4` -- only `network 172.16.4.0` present,
   `network 192.168.2.0` missing.
</details>

<details>
<summary>Click to view Fix</summary>

See [Solutions: Fault 4](#fault-4-r4-missing-ipv4-network-1921682-0-statement).
</details>

---

### Ticket 5 -- R1 Has No IPv6 Prefixes From R3

`show bgp ipv6 unicast summary` on R1 does not list the eBGP peer
`2001:DB8:13::2` at all. The IPv4 session to R3 is Established, the v6
neighbor statement exists at the process level -- but the IPv6 AF summary is
empty for this peer.

**Success criteria:** R1-R3 IPv6 eBGP session Established; R1's IPv6 BGP table
contains `2001:DB8:172:3::/64`.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `R1# show run | sec router bgp` -- neighbor `2001:DB8:13::2 remote-as 65002`
   exists at process level.
2. `R1# show run | sec address-family ipv6` -- line reads
   `no neighbor 2001:DB8:13::2 activate`. The peer is defined but muted in the
   correct AF.
3. Classic MP-BGP trap: adding a neighbor at the process level doesn't auto-
   activate v6; it only auto-activates v4.
</details>

<details>
<summary>Click to view Fix</summary>

See [Solutions: Fault 5](#fault-5-r1-ipv6-ebgp-neighbor-20012cdb8132c-2-not-activated).
</details>

---

### Ticket 6 -- R2 Shows 0 Prefixes From eBGP Peer R3 (IPv4 Only)

R2's eBGP IPv4 session to R3 is Established but the prefix count is 0.
Meanwhile `show ip bgp neighbors 10.0.23.2 received-routes` lists several
prefixes -- they're received but never installed. IPv6 from R3 is fine.

**Success criteria:** R2 shows 3+ prefixes received and installed from
`10.0.23.2`; `172.16.3.0/24` installed via direct eBGP path.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `R2# show ip bgp summary | i 10.0.23.2` -- Established, 0 prefixes.
2. Soft-reconfig inbound is already on? Try `R2# show ip bgp neighbors 10.0.23.2
   received-routes` -- shows prefixes. So they arrive.
3. `R2# show ip bgp neighbors 10.0.23.2 routes` -- empty. Policy dropped them.
4. `R2# show run | sec address-family ipv4` -- shows `neighbor 10.0.23.2
   route-map BLOCK_FROM_R3 in`.
5. `R2# show route-map BLOCK_FROM_R3` -- `deny` with a match-all prefix-list.
</details>

<details>
<summary>Click to view Fix</summary>

See [Solutions: Fault 6](#fault-6-r2-inbound-route-map-denies-all-ipv4-prefixes-from-r3).
</details>

---

## 10. Lab Completion Checklist

### Diagnosis and Fix

- [ ] Ticket 1 -- R1 iBGP remote-as mismatch identified and fixed
- [ ] Ticket 2 -- R2 next-hop-self on IPv4 iBGP added
- [ ] Ticket 3 -- R3 network statement typo corrected
- [ ] Ticket 4 -- R4 IPv4 network statement for 192.168.2.0 added
- [ ] Ticket 5 -- R1 IPv6 eBGP neighbor to R3 activated in the correct AF
- [ ] Ticket 6 -- R2 inbound route-map unblocked (and replaced with LOCAL_PREF map)

### End-State Verification

- [ ] `show ip bgp summary` on all four routers: every session Established
- [ ] `show bgp ipv6 unicast summary` on all four routers: every session Established
- [ ] R1, R2, R4 BGP tables contain all expected prefixes (see Section 6)
- [ ] PC1 pings PC2 on IPv4 (192.168.2.10)
- [ ] PC1 pings PC2 on IPv6 (2001:db8:2:2::10)
- [ ] LOCAL_PREF 200 still makes R1 the preferred exit on R2
- [ ] MED 50 still makes R1 the preferred entry from R3

### Root-Cause Documentation

- [ ] Written one-line root cause for each of the six faults before applying a fix
- [ ] No new faults introduced (confirm by running `show ip bgp summary` again on
      every router after all fixes)
