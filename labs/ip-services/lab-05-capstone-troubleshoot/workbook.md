# IP Services Lab 05 — Comprehensive Troubleshooting Capstone II

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

**Exam Objectives:** 1.4, 3.3.a, 3.3.b, 3.3.c | Topic: IP Services

This is the troubleshooting capstone for the IP Services topic. The network is pre-configured with a complete IP services stack — OSPF, NTP, NAT/PAT, and VRRPv3 — but contains 6 concurrent deliberate faults. You must diagnose all faults using only `show` commands and fix each one without introducing new issues. The network must reach the fully operational end-state before the lab is considered complete.

### Troubleshooting Methodology

For IP services, a layered approach prevents chasing symptoms of upstream faults:

```
Layer 1 — Routing (OSPF)
  ↓ Is reachability working between all routers?
Layer 2 — NTP
  ↓ Are clients synchronized? Authentication working?
Layer 3 — NAT/PAT
  ↓ Are translations being created? Correct interfaces?
Layer 4 — FHRP (VRRPv3)
  ↓ Is the correct router Master? Both AFs covered?
  ↓ Does failover work on uplink loss?
Layer 5 — End-to-end
  ↓ PC1 and PC2 reach 203.0.113.1 via IPv4/NAT and IPv6 via VRRP VIP
```

Work top-down. A broken OSPF adjacency explains why NAT translations fail (no route to outside). A correct OSPF fix unlocks NAT testing. Never skip layers.

### Key Diagnostic Commands

| Layer | First Command | What You Need to See |
|-------|--------------|---------------------|
| OSPF | `show ip ospf neighbor` | FULL on all active interfaces |
| NTP | `show ntp associations` | `*` on configured server |
| NAT | `show ip nat translations` | Static + dynamic entries after ping |
| VRRP | `show vrrp brief` | R1 Master, R2 Backup, both AFs |
| Tracking | `show track 1` | Up, linked to VRRP |
| E2E | PC ping 203.0.113.1 | Success via VRRP VIP |

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| Multi-fault triage | Identify root vs. downstream faults across four IP services technologies |
| OSPF passive-interface debugging | Diagnose silent adjacency failures with `show ip ospf interface` |
| NTP auth troubleshooting | Identify MD5 key mismatch without knowing the correct key-string |
| NAT interface and ACL debugging | Distinguish reversed interfaces from wrong ACL match criteria |
| VRRPv3 dual-stack coverage | Verify both address-families and their failover independently |
| VRRP tracking math | Verify decrement is sufficient to force failover given priority gap |

---

## 2. Topology & Scenario

**Scenario:** You have inherited a network that was "fully configured" by a departing engineer. An audit report says all IP services are operational, but the NOC is seeing multiple failures: NTP clients out of sync, internet connectivity broken for LAN hosts, and doubts about VRRP failover reliability. You have been handed console access and must restore full IP services operation.

```
                    ┌─────────────────────────┐
                    │           R3            │
                    │   Upstream / ISP Router │
                    │   Lo0: 3.3.3.3/32       │
                    │   Lo1: 203.0.113.1/24   │
                    └──────┬───────────┬──────┘
           Gi0/0           │           │           Gi0/1
     10.0.13.2/30          │           │     10.0.23.2/30
   [F6: OSPF passive]      │           │
                           │           │
     10.0.13.1/30          │           │     10.0.23.1/30
           Gi0/1           │           │           Gi0/1
  [F1: ip nat inside]      │           │
     ┌─────────────────────┘           └─────────────────────┐
     │                                                       │
┌────┴──────────────────────┐     ┌──────────────────────────┴────┐
│            R1             │     │              R2               │
│  [F1] NAT reversed        │     │  [F4] NTP key mismatch        │
│  [F2] PAT ACL wrong       │─────│  [F5] VRRPv3 IPv6 AF missing  │
│  [F3] VRRP decrement=5    │Gi0/2│                               │
└──────────────┬────────────┘     └────────────────┬─────────────┘
         Gi0/0 │                                   │ Gi0/0
   [F1: nat outside]                               │
               └──────────────┬────────────────────┘
                               │
                        ┌──────┴──────┐
                        │   SW-LAN    │
                        └──┬───────┬──┘
                           │       │
                    ┌──────┴──┐ ┌──┴──────┐
                    │  PC1    │ │  PC2    │
                    │.10/24   │ │.20/24   │
                    └─────────┘ └─────────┘

6 pre-embedded faults — diagnose all before declaring victory
```

---

## 3. Hardware & Environment Specifications

**Cabling Table:**

| Link | Source Device | Source Interface | Target Device | Target Interface | Subnet |
|------|---------------|-----------------|---------------|-----------------|--------|
| L1 | R1 | GigabitEthernet0/0 | SW-LAN | port1 | 192.168.1.0/24 |
| L2 | R2 | GigabitEthernet0/0 | SW-LAN | port2 | 192.168.1.0/24 |
| L3 | PC1 | e0 | SW-LAN | port3 | 192.168.1.0/24 |
| L4 | PC2 | e0 | SW-LAN | port4 | 192.168.1.0/24 |
| L5 | R1 | GigabitEthernet0/1 | R3 | GigabitEthernet0/0 | 10.0.13.0/30 |
| L6 | R2 | GigabitEthernet0/1 | R3 | GigabitEthernet0/1 | 10.0.23.0/30 |
| L7 | R1 | GigabitEthernet0/2 | R2 | GigabitEthernet0/2 | 10.0.12.0/30 |

**Console Access Table:**

| Device | Port | Connection Command |
|--------|------|--------------------|
| R1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R3 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| PC1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| PC2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |

---

## 4. Base Configuration

The following is pre-loaded in `initial-configs/` — the complete IP services stack with 6 deliberate faults injected:

**Pre-configured (present but possibly broken):**
- Hostnames, `no ip domain-lookup`, `ipv6 unicast-routing`
- IPv4 and IPv6 addressing on all interfaces
- OSPFv2 and OSPFv3 (but with one passive-interface fault)
- NTP hierarchy (but with key mismatch on R2)
- NAT/PAT on R1 (but with reversed interfaces and wrong ACL)
- VRRPv3 on R1 and R2 (but with wrong decrement and missing IPv6 AF on R2)
- QoS MQC policy `LAN-OUT` pre-loaded on R1 Gi0/1

**Your job:** Find and fix all 6 faults. Do not introduce new issues.

---

## 5. Lab Challenge: Comprehensive Troubleshooting

> This is a capstone lab. The network is pre-broken.
> Diagnose and resolve 6 concurrent faults spanning all blueprint bullets.
> No step-by-step guidance is provided — work from symptoms only.

**Reported symptoms from the NOC:**

1. R2 and R3 NTP associations show no synchronized peer — clocks drifting
2. PC1 and PC2 cannot reach the internet server (203.0.113.1) — no translations
3. `show ip nat translations` is empty after test pings
4. VRRP failover did not occur during a recent R1 uplink test — R1 stayed Master despite uplink failure
5. IPv6 hosts report no gateway when R1 is taken offline for maintenance
6. R1's OSPF neighbor count is lower than expected

**Success criteria — all must be true simultaneously:**

| Test | Expected Result |
|------|----------------|
| `show ip ospf neighbor` on R1 | 3 neighbors (R2 via Gi0/0, R3 via Gi0/1, R2 via Gi0/2) all FULL |
| `show ntp associations` on R2 | `*~1.1.1.1` — synchronized |
| `show ntp associations` on R3 | `*~1.1.1.1` — synchronized |
| PC1 ping 203.0.113.1 | Success |
| PC2 ping 203.0.113.1 | Success |
| `show ip nat translations` | Static entry + dynamic entries present |
| `show vrrp brief` on R1 | Master for both IPv4 and IPv6 AFs |
| `show vrrp brief` on R2 | Backup for both IPv4 and IPv6 AFs |
| Shut R1 Gi0/1, check R2 | R2 becomes VRRP Master for IPv4 |
| Restore R1 Gi0/1, check R1 | R1 reclaims VRRP Master |

---

## 6. Verification & Analysis

### Expected End-State — OSPF

```
R1# show ip ospf neighbor
Neighbor ID     Pri   State       Dead Time   Address         Interface
2.2.2.2           1   FULL/DR     00:00:35    192.168.1.3     GigabitEthernet0/0  ! ← R2 via LAN
3.3.3.3           1   FULL/BDR    00:00:31    10.0.13.2       GigabitEthernet0/1  ! ← R3 via uplink (Fault 6 fixed)
2.2.2.2           1   FULL/  -    00:00:38    10.0.12.2       GigabitEthernet0/2  ! ← R2 direct
```

### Expected End-State — NTP

```
R2# show ntp associations
      address         ref clock       st   when   poll reach  delay  offset   disp
*~1.1.1.1            127.127.1.1      3     12     64   377   0.500   0.123  0.189  ! ← * = synced (Fault 4 fixed)

R2# show ntp status
Clock is synchronized, stratum 4, reference is 1.1.1.1                              ! ← synchronized
```

### Expected End-State — NAT

```
R1# show ip nat translations
Pro Inside global      Inside local       Outside local      Outside global
--- 10.0.13.10         192.168.1.10       ---                ---             ! ← static (always present)
tcp 10.0.13.10:1024    192.168.1.10:1024  203.0.113.1:80     203.0.113.1:80 ! ← active session PC1
tcp 10.0.13.1:2049     192.168.1.20:2049  203.0.113.1:80     203.0.113.1:80 ! ← PAT for PC2 (Faults 1+2 fixed)
```

### Expected End-State — VRRPv3

```
R1# show vrrp brief
Interface   Grp  A-F   Pri Time  Own Pre State   Master addr/Group addr
Gi0/0         1  IPv4  110  3609   N   P Master  192.168.1.2    192.168.1.1     ! ← Fault 3 fixed: priority 110
Gi0/0         1  IPv6  110  3609   N   P Master  FE80::1        2001:DB8:1:1::1  ! ← Master IPv6

R2# show vrrp brief
Gi0/0         1  IPv4  100  3609   N   P Backup  192.168.1.2    192.168.1.1     ! ← Backup
Gi0/0         1  IPv6  100  3609   N   P Backup  FE80::1        2001:DB8:1:1::1  ! ← Fault 5 fixed: IPv6 AF present
```

---

## 7. Verification Cheatsheet

### Diagnostic Command Reference

| Layer | Command | What to Look For |
|-------|---------|-----------------|
| OSPF | `show ip ospf neighbor` | FULL on all active interfaces; count = expected |
| OSPF | `show ip ospf interface brief` | No unexpected PASSIVE state on active links |
| OSPF | `show ip route ospf` | Routes to all remote networks present |
| NTP | `show ntp associations` | `*` marks the synced peer |
| NTP | `show ntp status` | "Clock is synchronized" + stratum < 16 |
| NAT | `show ip nat translations` | Static entry always present; dynamic after test ping |
| NAT | `show ip interface Gi0/0` | "NAT: inside" |
| NAT | `show ip interface Gi0/1` | "NAT: outside" |
| NAT | `show ip access-lists NAT-PAT` | Permits 192.168.1.0/24 (not 10.0.13.0) |
| VRRP | `show vrrp brief` | State + priority per AF |
| VRRP | `show vrrp` | Virtual MAC, track state, Master Down Interval |
| Track | `show track 1` | Up; "Tracked by: VRRP ... decrement 20" |

### Quick Fault Fingerprinting

| Symptom | Where to Look | Likely Fault |
|---------|--------------|-------------|
| R1 has only 2 OSPF neighbors | `show ip ospf interface Gi0/1` on R3 — check PASSIVE | R3 Gi0/0 passive |
| NTP unsynchronized on R2 | `show ntp associations` — no `*` | Key mismatch |
| No NAT translations at all | `show ip interface Gi0/0` — check NAT role | NAT reversed |
| PC2 no internet, PC1 works | `show ip access-lists NAT-PAT` — check permit | Wrong ACL subnet |
| Failover doesn't trigger | `show vrrp` — check "Priority is" after track Down | Decrement too small |
| IPv6 hosts lose gateway | `show vrrp` on R2 — only IPv4 AF shown | IPv6 AF missing on R2 |

### Fix Reference

| Fault | Fix |
|-------|-----|
| R3 OSPF passive on Gi0/0 | `router ospf 1` + `no passive-interface Gi0/0` (both OSPFv2 and OSPFv3) |
| R2 NTP key mismatch | `no ntp authentication-key 1 md5 <wrong>` + `ntp authentication-key 1 md5 NTP_KEY_1` |
| R1 NAT reversed | `int Gi0/0` → `ip nat inside`; `int Gi0/1` → `ip nat outside` |
| R1 PAT ACL wrong subnet | Replace ACL permit: `permit 192.168.1.0 0.0.0.255` |
| R2 VRRPv3 IPv6 AF missing | `int Gi0/0` → `vrrp 1 address-family ipv6` + address + priority + preempt |
| R1 VRRP decrement too small | `vrrp 1 address-family ipv4` → `no track 1 decrement 5` + `track 1 decrement 20` |

---

## 8. Solutions (Spoiler Alert!)

> Attempt to find and fix all 6 faults yourself before reading this section.

### Fault 1 — R1 NAT Inside/Outside Reversed

<details>
<summary>Click to view Fix</summary>

```bash
R1# configure terminal
R1(config)# interface GigabitEthernet0/0
R1(config-if)# no ip nat outside
R1(config-if)# ip nat inside
R1(config-if)# interface GigabitEthernet0/1
R1(config-if)# no ip nat inside
R1(config-if)# ip nat outside
R1(config-if)# end
R1# clear ip nat translation *
```
</details>

### Fault 2 — R1 NAT-PAT ACL Wrong Subnet

<details>
<summary>Click to view Fix</summary>

```bash
R1# configure terminal
R1(config)# ip access-list standard NAT-PAT
R1(config-std-nacl)# no permit 10.0.13.0 0.0.0.255
R1(config-std-nacl)# permit 192.168.1.0 0.0.0.255
R1(config-std-nacl)# end
R1# clear ip nat translation *
```
</details>

### Fault 3 — R1 VRRP Track Decrement Too Small

<details>
<summary>Click to view Fix</summary>

```bash
R1# configure terminal
R1(config)# interface GigabitEthernet0/0
R1(config-if)# vrrp 1 address-family ipv4
R1(config-if-vrrp)# no track 1 decrement 5
R1(config-if-vrrp)# track 1 decrement 20
R1(config-if-vrrp)# end
! Verify: shut Gi0/1, confirm R2 becomes Master
```
</details>

### Fault 4 — R2 NTP Authentication Key Mismatch

<details>
<summary>Click to view Fix</summary>

```bash
R2# configure terminal
R2(config)# no ntp authentication-key 1 md5 NTP_KEY_WRONG
R2(config)# ntp authentication-key 1 md5 NTP_KEY_1
R2(config)# end
! Wait ~60s for NTP to re-associate
R2# show ntp associations   ! * should appear on 1.1.1.1
```
</details>

### Fault 5 — R2 VRRPv3 IPv6 Address-Family Missing

<details>
<summary>Click to view Fix</summary>

```bash
R2# configure terminal
R2(config)# interface GigabitEthernet0/0
R2(config-if)# vrrp 1 address-family ipv6
R2(config-if-vrrp)# address 2001:DB8:1:1::1 primary
R2(config-if-vrrp)# priority 100
R2(config-if-vrrp)# preempt
R2(config-if-vrrp)# end
R2# show vrrp   ! confirm both IPv4 and IPv6 AFs present
```
</details>

### Fault 6 — R3 OSPF Passive-Interface on Gi0/0

<details>
<summary>Click to view Fix</summary>

```bash
R3# configure terminal
R3(config)# router ospf 1
R3(config-router)# no passive-interface GigabitEthernet0/0
R3(config-router)# ipv6 router ospf 1
R3(config-rtr)# no passive-interface GigabitEthernet0/0
R3(config-rtr)# end
! Wait for adjacency to form
R3# show ip ospf neighbor   ! 1.1.1.1 (R1) should appear FULL
```
</details>

---

## 9. Troubleshooting Scenarios

This capstone does not use individual inject scripts — the lab loads pre-broken via `setup_lab.py`. Use `inject_all.py` to reset to the broken state after applying the solution.

### Workflow

```bash
python3 setup_lab.py                                    # load pre-broken configs
# --- troubleshoot and fix all 6 faults ---
python3 scripts/fault-injection/apply_solution.py       # compare against reference
python3 scripts/fault-injection/inject_all.py           # re-break for another attempt
```

---

### Fault Discovery Order (Recommended)

Work top-down through the service stack:

---

**Step 1 — Check OSPF adjacency count**

```
R1# show ip ospf neighbor
```
Expected: 3 neighbors. If only 2, R3's Gi0/0 is likely passive. Check with `show ip ospf interface brief` on R3.

---

**Step 2 — Check NTP sync on R2 and R3**

```
R2# show ntp associations
R2# show ntp status
```
Look for `*` on 1.1.1.1. If absent and R2 shows "unsynchronized", it's a key issue — compare key hashes with `show ntp authentication-keys` (if visible) or just re-enter the correct key.

---

**Step 3 — Check NAT interface orientation**

```
R1# show ip interface GigabitEthernet0/0 | include NAT
R1# show ip interface GigabitEthernet0/1 | include NAT
```
Gi0/0 must show `NAT: inside`. Gi0/1 must show `NAT: outside`. If reversed, fix before testing translations.

---

**Step 4 — Test NAT translations**

After fixing orientation, ping 203.0.113.1 from PC1 and PC2, then:
```
R1# show ip nat translations
```
If PC1 works but PC2 doesn't, the PAT ACL subnet is wrong. Check `show ip access-lists NAT-PAT`.

---

**Step 5 — Check VRRP state and tracking**

```
R1# show vrrp brief
R1# show vrrp
R2# show vrrp brief
```
Confirm both AFs on both routers. Check decrement value — must be > 10. Shut R1 Gi0/1 and verify R2 becomes Master.

---

**Step 6 — Verify IPv6 VRRP backup on R2**

```
R2# show vrrp
```
Must show both IPv4 and IPv6 address-families. If only IPv4, add the IPv6 AF to R2.

---

## 10. Lab Completion Checklist

### All 6 Faults Resolved

- [ ] Fault 1 fixed: R1 Gi0/0 = `ip nat inside`, Gi0/1 = `ip nat outside`
- [ ] Fault 2 fixed: NAT-PAT ACL permits 192.168.1.0/24 (not 10.0.13.0)
- [ ] Fault 3 fixed: R1 VRRP group 1 IPv4 track decrement = 20
- [ ] Fault 4 fixed: R2 NTP authentication key 1 = NTP_KEY_1 (synchronized)
- [ ] Fault 5 fixed: R2 VRRPv3 group 1 IPv6 address-family configured
- [ ] Fault 6 fixed: R3 OSPF Gi0/0 not passive (R1-R3 adjacency FULL)

### Full Stack Verification

- [ ] R1 shows 3 OSPF neighbors — all FULL (`show ip ospf neighbor`)
- [ ] R2 shows NTP status synchronized to 1.1.1.1 (`show ntp associations`)
- [ ] R3 shows NTP status synchronized to 1.1.1.1 (`show ntp associations`)
- [ ] PC1 ping 203.0.113.1 succeeds (static NAT)
- [ ] PC2 ping 203.0.113.1 succeeds (PAT)
- [ ] `show ip nat translations` shows static + dynamic entries
- [ ] R1 is VRRP Master for IPv4 and IPv6, R2 is Backup
- [ ] Shutting R1 Gi0/1 causes R2 to become Master for IPv4 (decrement fix verified)
- [ ] Restoring R1 Gi0/1 causes R1 to reclaim Master (preemption)
- [ ] IPv6 failover works: shutting R1 Gi0/0 transfers IPv6 gateway to R2
