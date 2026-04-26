# IP Services Lab 01: Static NAT, Dynamic NAT, and PAT

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

**Exam Objective:** 3.3.b — Configure NAT/PAT (CCNP ENCOR 350-401, IP Services)

Network Address Translation was designed to solve IPv4 address exhaustion by allowing many private addresses (RFC 1918) to share a small pool of public addresses. On modern enterprise networks, NAT is also used for security (hiding internal topology), migration (overlapping address spaces), and load balancing. Mastering the three NAT types — static, dynamic pool, and PAT — is a core operational skill and a tested exam topic.

### NAT Address Terminology

IOS NAT uses four address categories. Mixing them up is the most common source of confusion:

| Term | Meaning | Example |
|------|---------|---------|
| **Inside Local** | The private IP of an inside host as seen on the LAN | `192.168.1.10` (PC1) |
| **Inside Global** | The public IP representing the inside host on the outside network | `10.0.13.10` (PC1's public alias) |
| **Outside Local** | The IP of an outside host as seen by inside devices (usually same as Outside Global) | `203.0.113.1` |
| **Outside Global** | The actual IP of the outside host | `203.0.113.1` |

The translation table maps Inside Local ↔ Inside Global. When a packet exits the inside interface, IOS replaces the source with the Inside Global address. When a reply arrives on the outside interface, IOS reverses the substitution.

### Static NAT

A static mapping ties one inside local address to one inside global address permanently — the entry exists in the translation table even when no traffic is flowing. This is used for servers that need a predictable public address (inbound connections must be able to find the host).

```
ip nat inside source static <inside-local> <inside-global>
```

Key behavior: the static entry pre-populates the translation table regardless of traffic. The mapping is bidirectional — traffic initiated from outside to the inside-global IP is forwarded to the inside-local IP.

### Dynamic NAT Pool

A dynamic NAT pool maps inside hosts to a range of public addresses. Translations are created on demand when traffic exits and expire after a timeout (default 24 hours for TCP, 5 minutes for ICMP). If the pool is exhausted, new connections are dropped.

```
ip nat pool <name> <start-ip> <end-ip> netmask <mask>
ip nat inside source list <acl-name> pool <name>
```

The ACL defines which inside local addresses are eligible for translation. Only traffic sourced from addresses permitted by the ACL will be translated.

### PAT (Port Address Translation / Overload)

PAT allows many inside hosts to share a single public IP by appending unique source port numbers to each translation. This is the most common form of NAT in enterprise and consumer networks — one outside IP can support tens of thousands of concurrent sessions.

```
ip nat inside source list <acl-name> interface <outside-if> overload
```

The `overload` keyword triggers PAT. IOS tracks each flow by the five-tuple (protocol, inside local IP, inside local port, inside global IP, inside global port). The translation table entry includes the port mapping.

### IOS NAT Processing Order

When IOS translates an outbound packet from inside to outside:

1. Check for a matching **static** entry (highest priority)
2. Check for a matching **dynamic pool** entry (if a mapping already exists)
3. Create a new **dynamic pool** or **PAT** entry if the ACL matches and capacity permits
4. Drop the packet if no translation can be created

Static entries always win. This allows a specific host (like PC1) to have a fixed public IP for inbound access while other hosts share a PAT address.

### NAT and OSPF

In this lab, OSPF is the IGP across all router links. OSPF routes the 10.0.x.x point-to-point subnets and the loopbacks, which ensures R1 can forward translated packets toward R3's simulated server at 203.0.113.1. NAT operates on top of the existing routing table — it rewrites packet headers but does not affect routing decisions.

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| Interface designation | Identifying inside vs outside interfaces relative to the NAT boundary |
| Static NAT | Creating and verifying a one-to-one, permanent address mapping |
| Dynamic NAT pool | Defining an address pool and binding it to an ACL |
| PAT overload | Configuring many-to-one NAT using port multiplexing |
| Translation table analysis | Reading `show ip nat translations` to confirm expected entries |
| NAT statistics | Using `show ip nat statistics` to track hit counts and pool usage |
| ACL troubleshooting | Verifying the NAT source ACL matches the correct inside-local range |
| Translation clearing | Clearing the translation table and observing re-creation behavior |

---

## 2. Topology & Scenario

```
                    ┌─────────────────────────┐
                    │           R3            │
                    │   (Upstream / ISP)      │
                    │   Lo0: 3.3.3.3          │
                    │   Lo1: 203.0.113.1/24   │
                    └──────┬───────────┬──────┘
           Gi0/0           │           │           Gi0/1
     10.0.13.2/30          │           │     10.0.23.2/30
                           │           │
     10.0.13.1/30          │           │     10.0.23.1/30
           Gi0/1           │           │           Gi0/1
     ┌─────────────────────┘           └──────────────────────┐
     │                                                        │
┌────┴──────────────────┐           ┌───────────────────────┴────┐
│          R1           │           │           R2               │
│  (Primary Gateway)    │           │   (Secondary Gateway)      │
│  NAT Inside: Gi0/0    │           │   Lo0: 2.2.2.2             │
│  NAT Outside: Gi0/1   │           └───────────────────────┬────┘
│  Lo0: 1.1.1.1         │                                   │
└──────────┬────────────┘                                   │
     Gi0/0 │ 192.168.1.2/24                   192.168.1.3/24│ Gi0/0
           │                                               │
           └───────────────┐              ┌────────────────┘
                    ┌──────┴──────────────┴──────┐
                    │          SW-LAN             │
                    │    (Unmanaged Switch)        │
                    │    192.168.1.0/24            │
                    └──────┬──────────────┬───────┘
                           │              │
              192.168.1.10 │              │ 192.168.1.20
                     ┌─────┴────┐   ┌────┴─────┐
                     │   PC1    │   │   PC2    │
                     │ (VPC)    │   │  (VPC)   │
                     └──────────┘   └──────────┘
```

**Scenario:** Meridian Financial's LAN has grown to the point where the IT team needs controlled internet access for all workstations. The security policy requires PC1 (the NOC workstation) to have a fixed public IP for inbound management connections. All other hosts should share the company's uplink IP via PAT to conserve the small public address range ISP assigned. Your task is to configure NAT on R1 to implement this policy.

---

## 3. Hardware & Environment Specifications

**Cabling Table:**

| Link | Device A | Interface | Device B | Interface | Subnet |
|------|----------|-----------|----------|-----------|--------|
| L1 | R1 | Gi0/0 | SW-LAN | port1 | 192.168.1.0/24 |
| L2 | R2 | Gi0/0 | SW-LAN | port2 | 192.168.1.0/24 |
| L3 | PC1 | e0 | SW-LAN | port3 | 192.168.1.0/24 |
| L4 | PC2 | e0 | SW-LAN | port4 | 192.168.1.0/24 |
| L5 | R1 | Gi0/1 | R3 | Gi0/0 | 10.0.13.0/30 |
| L6 | R2 | Gi0/1 | R3 | Gi0/1 | 10.0.23.0/30 |
| L7 | R1 | Gi0/2 | R2 | Gi0/2 | 10.0.12.0/30 |

**Console Access Table:**

| Device | Port | Connection Command |
|--------|------|--------------------|
| R1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R3 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |

SW-LAN is an unmanaged EVE-NG switch — no console access required.
PC1 and PC2 are VPCs — connect via the EVE-NG web console.

---

## 4. Base Configuration

The following is pre-configured in `initial-configs/` (chained from Lab 00 solutions):

**Pre-loaded on all routers:**
- Hostname and `no ip domain-lookup`
- Full IP addressing (all interfaces per the cabling table)
- OSPF process 1 (area 0 on all interfaces, router-ID from Loopback0)
- NTP: R1 as master (stratum 3), R2 and R3 as clients with MD5 auth key 1
- Console/VTY lines with logging synchronous and exec-timeout 0 0

**Pre-loaded on R1 only:**
- QoS MQC policy (class-maps VOICE/VIDEO/CRITICAL-DATA/SCAVENGER, policy-map LAN-OUT applied outbound on Gi0/1)

**NOT pre-configured (student builds these):**
- NAT inside/outside interface designations
- Static NAT mapping
- Dynamic NAT pool and its ACL
- PAT overload and its ACL

R3's Loopback1 (203.0.113.1/24) is reachable via OSPF from R1 — it acts as the simulated internet server. Ping this address from PC1/PC2 to verify NAT is translating correctly.

---

## 5. Lab Challenge: Core Implementation

### Task 1: Designate NAT Interfaces on R1

- Mark R1's LAN-facing interface (toward SW-LAN) as the NAT inside boundary.
- Mark R1's uplink interface (toward R3) as the NAT outside boundary.
- These designations are required before any NAT rule will function.

**Verification:** `show ip interface brief` shows both interfaces up. `show run | include ip nat` confirms exactly one inside and one outside designation exist.

---

### Task 2: Configure Static NAT for PC1

- Create a permanent one-to-one mapping from PC1's private IP (192.168.1.10) to the public IP 10.0.13.10.
- This mapping must be bidirectional — traffic initiated to 10.0.13.10 from outside should reach PC1.

**Verification:** `show ip nat translations` immediately shows a static entry (marked `---` in the port columns) mapping 192.168.1.10 to 10.0.13.10 — this entry must exist before any traffic is generated.

---

### Task 3: Configure Dynamic NAT Pool for PC2

- Create an access list that identifies only PC2 (192.168.1.20) as eligible for dynamic NAT.
- Create a NAT pool named `NAT-POOL` covering the public address range 10.0.13.100 through 10.0.13.110 with a /24 mask.
- Bind the access list to the pool.

**Verification:** From PC2, ping 203.0.113.1. `show ip nat translations` must show a dynamic entry for 192.168.1.20 mapped to an address in the 10.0.13.100–10.0.13.110 range.

---

### Task 4: Verify and Clear NAT Translations

- Display the full translation table and identify each entry type (static vs dynamic).
- Verify the NAT statistics counter shows active translation hits.
- Clear all dynamic translations (the static entry for PC1 must survive the clear).
- Regenerate a dynamic translation by pinging from PC2 and confirm the new entry.

**Verification:** After clearing, `show ip nat translations` shows only the static PC1 entry. After PC2 pings again, a new dynamic entry reappears for PC2.

---

### Task 5: Configure PAT Overload for All LAN Hosts

- Create an access list that matches the entire LAN subnet 192.168.1.0/24.
- Configure PAT using the outside interface IP (R1's Gi0/1 address) as the single public address for all LAN hosts.
- Both PC1 and PC2 should now be able to reach 203.0.113.1 — PC1 via its static entry (static takes priority), other hosts via PAT.

**Verification:** From both PC1 and PC2, ping 203.0.113.1. `show ip nat translations` must show PC1's static entry unchanged, plus a PAT entry (with port numbers) for PC2 and any other hosts. `show ip nat statistics` shows the overload configuration in effect.

---

### Task 6: Clear Translations and Verify Re-creation

- Clear all dynamic NAT translations.
- Immediately generate traffic from both PC1 and PC2 toward 203.0.113.1.
- Observe that translations are re-created on demand.

**Verification:** `show ip nat translations` shows active entries for both PCs after traffic is regenerated. PC1 always uses the static mapping; PC2 uses PAT (or pool, whichever applies).

---

### Task 7: Verify End-to-End Reachability

- From PC1: confirm reachability to 203.0.113.1 (simulated internet server on R3).
- From PC2: confirm reachability to 203.0.113.1.
- On R1: confirm the translation table shows the expected inside-global addresses for each host.

**Verification:** Pings from PC1 and PC2 to 203.0.113.1 succeed. `show ip nat translations` shows PC1 translating via its static entry (10.0.13.10) and PC2 translating via PAT (10.0.13.1, the Gi0/1 address, with a unique port).

---

## 6. Verification & Analysis

### Task 1 — Interface Designations

```
R1# show run | include ip nat
 ip nat inside                          ! ← must appear under Gi0/0
 ip nat outside                         ! ← must appear under Gi0/1
```

### Task 2 — Static NAT Entry

```
R1# show ip nat translations
Pro  Inside global     Inside local       Outside local      Outside global
---  10.0.13.10        192.168.1.10       ---                ---            ! ← static pre-entry, always present
```

Note the `---` in outside columns and port columns — this is the static pre-entry that exists before any traffic.

### Task 3 — Dynamic NAT Pool Entry (after PC2 pings)

```
R1# show ip nat translations
Pro  Inside global     Inside local       Outside local      Outside global
---  10.0.13.10        192.168.1.10       ---                ---            ! ← static (PC1)
icmp 10.0.13.100:1    192.168.1.20:1    203.0.113.1:1      203.0.113.1:1  ! ← dynamic pool (PC2), address from pool range
```

### Task 4 — After Clearing Dynamic Translations

```
R1# clear ip nat translation *
R1# show ip nat translations
Pro  Inside global     Inside local       Outside local      Outside global
---  10.0.13.10        192.168.1.10       ---                ---            ! ← static survives clear
                                                                             ! ← no dynamic entries until PC2 sends traffic
```

### Task 5 — PAT Translations (after both PCs ping)

```
R1# show ip nat translations
Pro  Inside global       Inside local        Outside local       Outside global
---  10.0.13.10          192.168.1.10        ---                 ---            ! ← PC1 static
icmp 10.0.13.1:1024     192.168.1.10:1      203.0.113.1:1       203.0.113.1:1  ! ← PC1 PAT ping (if no static match for ICMP flow)
icmp 10.0.13.1:1025     192.168.1.20:1      203.0.113.1:1       203.0.113.1:1  ! ← PC2 PAT, unique source port

R1# show ip nat statistics
Total active translations: 3 (1 static, 2 dynamic; 2 extended)
Peak translations: 3, occurred 00:00:12 ago
Outside interfaces:
  GigabitEthernet0/1                    ! ← correct outside interface
Inside interfaces:
  GigabitEthernet0/0                    ! ← correct inside interface
Hits: 24  Misses: 0                     ! ← hits increment with each translated packet
```

### Task 7 — End-to-End Reachability

```
PC1> ping 203.0.113.1
84 bytes from 203.0.113.1 icmp_seq=1 ttl=254 time=X ms  ! ← success via NAT

PC2> ping 203.0.113.1
84 bytes from 203.0.113.1 icmp_seq=1 ttl=254 time=X ms  ! ← success via PAT
```

---

## 7. Verification Cheatsheet

### NAT Interface Configuration

```
interface GigabitEthernet0/0
 ip nat inside
interface GigabitEthernet0/1
 ip nat outside
```

| Command | Purpose |
|---------|---------|
| `ip nat inside` | Marks the interface facing the private LAN |
| `ip nat outside` | Marks the interface facing the public network |

> **Exam tip:** Both designations are required. Configuring a NAT rule without marking interfaces causes silent failures — no error, no translation.

### Static NAT

```
ip nat inside source static <inside-local> <inside-global>
```

| Command | Purpose |
|---------|---------|
| `ip nat inside source static <IL> <IG>` | Creates a permanent bidirectional one-to-one mapping |
| `no ip nat inside source static <IL> <IG>` | Removes the static entry |

> **Exam tip:** The static entry pre-populates the translation table at boot. You can verify it without sending any traffic.

### Dynamic NAT Pool

```
ip access-list standard <acl-name>
 permit <network> <wildcard>
ip nat pool <pool-name> <start-ip> <end-ip> netmask <mask>
ip nat inside source list <acl-name> pool <pool-name>
```

| Command | Purpose |
|---------|---------|
| `ip nat pool <name> <start> <end> netmask <mask>` | Defines the public address pool |
| `ip nat inside source list <acl> pool <name>` | Binds the ACL to the pool for dynamic translation |

> **Exam tip:** If the pool is exhausted, new connections are silently dropped. Use `show ip nat statistics` to check the "Pool stats" and see how many addresses are in use.

### PAT (Overload)

```
ip access-list standard <acl-name>
 permit <network> <wildcard>
ip nat inside source list <acl-name> interface <outside-if> overload
```

| Command | Purpose |
|---------|---------|
| `ip nat inside source list <acl> interface <if> overload` | Enables PAT using the outside interface IP |
| `overload` keyword | Triggers port address translation (many-to-one) |

> **Exam tip:** PAT is the default behavior on most SOHO/enterprise edge routers. Without `overload`, IOS treats it as a dynamic pool with a single-address pool (pool exhaustion after the first session).

### Verification Commands

| Command | What to Look For |
|---------|-----------------|
| `show ip nat translations` | Translation table: static entries (no port columns), dynamic entries with port numbers |
| `show ip nat translations verbose` | Adds age, flags, and protocol detail to each entry |
| `show ip nat statistics` | Interface assignments, hit/miss counters, active translation count |
| `show access-lists <name>` | ACL match counters — must increment as traffic is translated |
| `show run \| include ip nat` | Quick check for inside/outside designations and NAT rules |
| `clear ip nat translation *` | Clears all dynamic entries; static entries survive |
| `clear ip nat translation inside <IL> <IG>` | Clears a specific dynamic entry |
| `debug ip nat` | Real-time NAT translation events (use with caution in production) |

### NAT Address Types Quick Reference

| Term | Direction | Who Sees It |
|------|-----------|-------------|
| Inside Local | Outbound (pre-NAT) | Internal devices, OSPF |
| Inside Global | Outbound (post-NAT) | External devices, R3 |
| Outside Local | Inbound (pre-NAT) | Internal devices (usually same as Outside Global) |
| Outside Global | Inbound (post-NAT) | External device's real IP |

### Common NAT Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| No translations created | Missing `ip nat inside` / `ip nat outside` on interfaces |
| Translations created but no connectivity | Routing issue — return traffic can't find the inside host |
| PAT works but pool NAT doesn't | ACL mismatch — NAT-DYNAMIC ACL doesn't match the inside host range |
| Static entry missing from table | Static NAT command not entered, or wrong inside-local IP |
| Pool exhausted, new sessions fail | Pool too small; consider switching to PAT for bulk hosts |
| `show ip nat statistics` shows Misses | ACL is not matching traffic; check ACL with `show access-lists` |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Task 1 & 2: Interface Designations + Static NAT

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! Task 1: Mark NAT boundary interfaces
interface GigabitEthernet0/0
 ip nat inside
interface GigabitEthernet0/1
 ip nat outside

! Task 2: Static NAT for PC1
ip nat inside source static 192.168.1.10 10.0.13.10
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show run | include ip nat
show ip nat translations
```
</details>

### Task 3: Dynamic NAT Pool for PC2

<details>
<summary>Click to view R1 Configuration</summary>

```bash
ip access-list standard NAT-DYNAMIC
 permit host 192.168.1.20
ip nat pool NAT-POOL 10.0.13.100 10.0.13.110 netmask 255.255.255.0
ip nat inside source list NAT-DYNAMIC pool NAT-POOL
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
! From PC2: ping 203.0.113.1
show ip nat translations
show ip nat statistics
show access-lists NAT-DYNAMIC
```
</details>

### Task 5: PAT Overload for All LAN Hosts

<details>
<summary>Click to view R1 Configuration</summary>

```bash
ip access-list standard NAT-PAT
 permit 192.168.1.0 0.0.0.255
ip nat inside source list NAT-PAT interface GigabitEthernet0/1 overload
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
! From both PC1 and PC2: ping 203.0.113.1
show ip nat translations
show ip nat statistics
```
</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world NAT fault. Inject the fault first, then
diagnose and fix using only show commands.

### Workflow

```bash
python3 setup_lab.py                                   # reset to known-good
python3 scripts/fault-injection/inject_scenario_01.py  # Ticket 1
python3 scripts/fault-injection/apply_solution.py      # restore
```

---

### Ticket 1 — LAN Hosts Cannot Reach the Internet; Translation Table Is Empty

A network change was made to R1 an hour ago. PC1 and PC2 report they cannot reach 203.0.113.1. Routing appears fine — R1 can ping 203.0.113.1 directly from its own interface. `show ip nat translations` shows no entries at all, not even the static pre-entry for PC1.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py`

**Success criteria:** PC1 and PC2 can ping 203.0.113.1. `show ip nat translations` shows the static entry for PC1 and dynamic entries for other hosts.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
R1# show run | include ip nat
! Look for ip nat inside and ip nat outside -- verify which interface has which designation

R1# show ip interface GigabitEthernet0/0
! Check "IP NAT: inside" or "IP NAT: outside" in the output

R1# show ip interface GigabitEthernet0/1
! Same check on the uplink

! If inside is on the wrong interface (uplink) and outside on the LAN:
! NAT will attempt to translate packets sourced from the UPLINK subnet,
! not the LAN hosts -- that is why the table is empty.
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
R1# configure terminal
R1(config)# interface GigabitEthernet0/0
R1(config-if)#  no ip nat outside
R1(config-if)#  ip nat inside
R1(config-if)# interface GigabitEthernet0/1
R1(config-if)#  no ip nat inside
R1(config-if)#  ip nat outside
R1(config-if)# end
R1# show ip nat translations
! Static pre-entry for PC1 now appears immediately
```
</details>

---

### Ticket 2 — PC2 Cannot Reach the Internet; PC1 Works Fine

PC1 can reach 203.0.113.1 without issues. PC2 reports no connectivity to the same address. `show ip nat translations` shows PC1's static entry and PC1's PAT entries, but no entries for PC2 (192.168.1.20).

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py`

**Success criteria:** PC2 can ping 203.0.113.1. `show ip nat translations` shows a PAT entry with source 192.168.1.20.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
R1# show ip nat statistics
! Check "Misses" counter -- it increments when traffic is not translated
! Also shows ACL name referenced in the NAT rule

R1# show access-lists NAT-PAT
! Check the permit statement -- if it matches the wrong network,
! 192.168.1.20 traffic will never hit the ACL

R1# show run | section ip nat
! Confirm ip nat inside source list NAT-PAT interface GigabitEthernet0/1 overload
! Then check NAT-PAT ACL -- should permit 192.168.1.0 0.0.0.255
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
R1# configure terminal
R1(config)# no ip access-list standard NAT-PAT
R1(config)# ip access-list standard NAT-PAT
R1(config-std-nacl)#  permit 192.168.1.0 0.0.0.255
R1(config-std-nacl)# end
R1# clear ip nat translation *
! Re-test from PC2: ping 203.0.113.1
```
</details>

---

### Ticket 3 — PC1's Fixed Public Address Is Not in the Translation Table

The NOC team reports that inbound management connections to PC1's assigned public IP (10.0.13.10) are failing. PC1 can reach 203.0.113.1 outbound without issues. `show ip nat translations` shows a static entry for PC1, but it maps to a different public IP than expected.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py`

**Success criteria:** `show ip nat translations` shows the static entry mapping 192.168.1.10 to exactly 10.0.13.10 (not any other address).

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
R1# show ip nat translations
! Locate the static entry (marked ---) for 192.168.1.10
! The Inside Global column should show 10.0.13.10
! If it shows a different address (e.g. 10.0.13.99), the static entry
! was configured with the wrong outside IP

R1# show run | include ip nat inside source static
! Confirms the exact static NAT command -- verify the inside-global IP
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
R1# configure terminal
! Remove the incorrect static entry
R1(config)# no ip nat inside source static 192.168.1.10 10.0.13.99
! Re-add with the correct public IP
R1(config)# ip nat inside source static 192.168.1.10 10.0.13.10
R1(config)# end

R1# show ip nat translations
! Static entry for 192.168.1.10 <-> 10.0.13.10 must now appear
```
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] R1 Gi0/0 designated as NAT inside; Gi0/1 designated as NAT outside
- [ ] Static NAT entry maps PC1 (192.168.1.10) to 10.0.13.10 — visible in translation table before any traffic
- [ ] Dynamic NAT pool `NAT-POOL` defined with range 10.0.13.100–10.0.13.110
- [ ] ACL `NAT-DYNAMIC` permits only 192.168.1.20 (PC2) and is bound to the pool
- [ ] Dynamic translation for PC2 appears in translation table after PC2 pings 203.0.113.1
- [ ] `clear ip nat translation *` removes dynamic entries but leaves PC1 static entry intact
- [ ] PAT ACL `NAT-PAT` permits 192.168.1.0/24 and is bound to Gi0/1 overload
- [ ] Both PC1 and PC2 can ping 203.0.113.1 with translations visible in the table
- [ ] `show ip nat statistics` shows correct inside/outside interfaces and nonzero hits

### Troubleshooting

- [ ] Ticket 1 resolved: NAT interface designations corrected; translation table populated
- [ ] Ticket 2 resolved: NAT-PAT ACL fixed to match 192.168.1.0/24; PC2 reaches 203.0.113.1
- [ ] Ticket 3 resolved: Static NAT entry corrected to map PC1 to 10.0.13.10
