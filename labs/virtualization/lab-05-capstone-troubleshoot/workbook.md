# Lab 05 — VRF and Tunneling Comprehensive Troubleshooting (Capstone II)

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

**Exam Objective:** 2.2 — Configure and verify data path virtualization technologies (VRF, GRE, IPsec tunneling). Topic: Virtualization.

This capstone troubleshooting lab develops the diagnostic reasoning skills needed to identify and fix concurrent faults across VRF routing, GRE tunneling, and IKEv2/IPsec encryption. The network is pre-broken with five independent faults; students must isolate each problem using show commands and restore full end-to-end functionality. This mirrors real-world escalation scenarios where multiple layers fail simultaneously and the engineer must determine which problem to address first.

### VRF Routing and Address Families

A Virtual Routing and Forwarding (VRF) instance maintains a separate routing table, CEF table, and forwarding instance from the global table. When an interface is assigned to a VRF using `vrf forwarding <NAME>`, its IP address is immediately cleared — the student must re-apply the address after the assignment.

VRF dual-stack requires explicit address families. An IOS `vrf definition` without `address-family ipv6` will not carry IPv6 routes, even if the router itself has `ipv6 unicast-routing` enabled. IPv6 addresses assigned to interfaces in such a VRF are silently rejected. The fix is to add the IPv6 address family to the VRF definition and then re-apply IPv6 addresses to all VRF interfaces.

Key diagnostic commands:
- `show vrf detail <NAME>` — shows defined address families
- `show ip route vrf <NAME>` — IPv4 routing table for the VRF
- `show ipv6 route vrf <NAME>` — IPv6 routing table for the VRF
- `show ip interface <intf>` — shows VRF assignment under "VPN Routing/Forwarding"

### GRE Tunnels and Underlay Dependency

A GRE tunnel's line protocol state depends on whether the router has a valid route to the tunnel destination IP. If the underlay (OSPF, static routes, or connected paths) loses the route to the remote loopback, the tunnel immediately drops to "line protocol is down" — even though the physical interface is still up. This is a common source of confusion: the physical links look healthy but the tunnel is dead.

Tunnel state depends on:
1. Route to tunnel destination in the **global routing table** (not VRF — tunnel source/dest are in global by default)
2. Interface referenced by `tunnel source` must be UP/UP

GRE uses IP protocol 47. It adds a 24-byte overhead (4-byte GRE header + 20-byte outer IP header). Setting `ip mtu 1400` and `ip tcp adjust-mss 1360` prevents fragmentation for TCP traffic.

Key diagnostic commands:
- `show interface Tunnel0` — line protocol state and tunnel parameters
- `ping <tunnel-dest-loopback>` from source router — tests underlay reachability
- `show ip route <destination-loopback>` — confirms underlay has the route
- `show ip ospf neighbor` — confirms OSPF adjacencies that provide the route

### IKEv2 Four-Tier Configuration and Failure Modes

IKEv2 has a strict four-level hierarchy on IOS: proposal → policy → keyring → profile. If any layer is misconfigured, the IKE_SA_INIT or IKE_AUTH exchange fails and no SA is established.

Common failure modes:
| Failure Point | Layer | Symptom |
|--------------|-------|---------|
| Mismatched encryption/DH group | Proposal | IKE_SA_INIT fails — no SA attempt succeeds |
| Wrong PSK | Keyring | IKE_AUTH fails — AUTH_FAILED in debug output |
| Wrong peer IP in keyring | Keyring | No PSK found for peer — AUTH_FAILED |
| Profile not matched | Profile | `match identity remote` filter drops the peer |
| Missing `tunnel protection` | Tunnel interface | GRE UP but no IKEv2 negotiation ever starts |

When `tunnel protection ipsec profile <NAME>` is missing from a GRE tunnel interface, IKEv2 is never triggered — the router simply forwards GRE packets without encryption. The tunnel stays UP (GRE works without IPsec) but `show crypto ipsec sa` shows no protected interfaces.

Key diagnostic commands:
- `show crypto ikev2 sa` — shows IKE SA state (READY = working; empty = never negotiated)
- `show crypto ikev2 statistics` — aggregate counters including auth failures
- `show crypto ipsec sa` — shows IPsec SAs and packet counters; "protected interface" field confirms binding
- `show running-config interface Tunnel0` — check for `tunnel protection ipsec profile` line

### GRE-over-IPsec: Protection Profile Binding

GRE-over-IPsec uses a GRE tunnel interface with an IPsec profile applied via `tunnel protection ipsec profile <NAME>`. This binding must exist on **both** endpoints. If only one side has the binding:
- Side WITH protection: encrypts outbound, tries to decrypt inbound
- Side WITHOUT protection: sends plain GRE, receives plain GRE (no SA)
- Net result: GRE tunnel stays UP, OSPF overlay adjacency may stay UP, but IPsec SA is absent

This is different from a PSK mismatch (where both sides try to negotiate but fail during AUTH). The "missing protection" fault is harder to spot because everything appears to work — connectivity is present, just unencrypted.

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| Layer-by-layer triage | Diagnose underlay routing before blaming overlay tunnels |
| VRF interface verification | Confirm VRF assignment and address family completeness |
| IKEv2 failure diagnosis | Distinguish proposal mismatch from PSK mismatch from missing profile |
| GRE tunnel state analysis | Understand why tunnel line protocol follows underlay route reachability |
| Security verification | Confirm encryption is active using crypto SA packet counters |

---

## 2. Topology & Scenario

**Enterprise Scenario:** AcmeCorp's NOC has escalated a P1 incident. The VRF-segmented WAN and the encrypted overlay tunnel between the HQ site router (R1) and the Remote Site (R4) are both degraded. Multiple users at Site 2 (R2/PC2) are reporting connectivity failures to Site 1 (R1/PC1) through the CUSTOMER-A VRF. The R4 encrypted tunnel is also reported as down. You have been brought in to diagnose and resolve all faults. The environment uses VRF-Lite across R1-R3-R2 for customer isolation, and a GRE-over-IPsec tunnel between R1 and R4 for the encrypted overlay.

**Physical Topology:**

```
              ┌──────────────────────────┐       ┌──────────────────────────┐
              │           R1             │       │           R2             │
              │   (VRF Host, HQ Site)    │       │  (VRF Host, Branch Site) │
              │   Lo0: 1.1.1.1/32        │       │   Lo0: 2.2.2.2/32        │
              └───┬───────────────┬──────┘       └──────┬──────────────┬────┘
           Gi0/0  │          Gi0/1│                     │Gi0/0    Gi0/1│
     10.0.13.1/30 │    10.0.12.1/30                     │10.0.23.1/30  │10.0.12.2/30
                  │               └─────────────────────┘
     10.0.13.2/30 │
           Gi0/0  │
              ┌───┴──────────────────────┐
              │           R3             │
              │   (Shared WAN Transport) │
              │   Lo0: 3.3.3.3/32        │
              └────────────┬─────────────┘
                      Gi0/2│
               10.0.34.1/30│
                            │
               10.0.34.2/30 │
                      Gi0/0 │
              ┌─────────────┴────────────┐
              │           R4             │
              │   (Remote Site / VPN EP) │
              │   Lo0: 4.4.4.4/32        │
              └──────────────────────────┘
```

**VRF-Lite Overlay (CUSTOMER-A transit via 802.1Q sub-interfaces):**

```
  R1:Gi0/0.100             R3:Gi0/0.100 ─ R3:Gi0/1.100             R2:Gi0/0.100
  172.16.13.1/30  ◄──────►  172.16.13.2/30   172.16.23.2/30  ◄──────►  172.16.23.1/30
  (VRF CUSTOMER-A)          (VRF CUSTOMER-A)  (VRF CUSTOMER-A)          (VRF CUSTOMER-A)
```

**Encrypted Overlay (Tunnel0 — GRE-over-IPsec):**

```
  R1:Tunnel0                                                       R4:Tunnel0
  172.16.14.1/30  ◄── GRE encapsulated inside IPsec ESP ──────►  172.16.14.2/30
  (source: 1.1.1.1)       underlay path: R1→R3→R4           (source: 4.4.4.4)
```

**End Hosts:**

| Device | IP | Gateway | VRF |
|--------|-----|---------|-----|
| PC1 | 192.168.1.10/24 | 192.168.1.1 (R1 Gi0/2) | CUSTOMER-A |
| PC2 | 192.168.2.10/24 | 192.168.2.1 (R2 Gi0/2) | CUSTOMER-A |

---

## 3. Hardware & Environment Specifications

**Platform:** IOSv (Cisco IOS Virtual Router) on EVE-NG

| Device | Role | Platform | Interfaces Used |
|--------|------|----------|----------------|
| R1 | HQ/VRF host, GRE-over-IPsec endpoint | IOSv | Lo0, Lo1, Lo2, Tunnel0, Gi0/0, Gi0/0.100, Gi0/1, Gi0/2 |
| R2 | Branch/VRF host | IOSv | Lo0, Lo1, Lo2, Gi0/0, Gi0/0.100, Gi0/1, Gi0/2 |
| R3 | Shared WAN transport | IOSv | Lo0, Gi0/0, Gi0/0.100, Gi0/1, Gi0/1.100, Gi0/2 |
| R4 | Remote site, GRE-over-IPsec endpoint | IOSv | Lo0, Lo1, Tunnel0, Gi0/0 |
| PC1 | End host, CUSTOMER-A Site 1 | VPCS | eth0 |
| PC2 | End host, CUSTOMER-A Site 2 | VPCS | eth0 |

**Cabling:**

| Link ID | Source | Destination | Subnet | Purpose |
|---------|--------|-------------|--------|---------|
| L1 | R1 Gi0/0 | R3 Gi0/0 | 10.0.13.0/30 | R1-R3 WAN underlay |
| L2 | R2 Gi0/0 | R3 Gi0/1 | 10.0.23.0/30 | R2-R3 WAN underlay |
| L3 | R1 Gi0/1 | R2 Gi0/1 | 10.0.12.0/30 | R1-R2 direct link |
| L4 | R1 Gi0/2 | PC1 eth0 | 192.168.1.0/24 | R1 LAN (CUSTOMER-A) |
| L5 | R2 Gi0/2 | PC2 eth0 | 192.168.2.0/24 | R2 LAN (CUSTOMER-A) |
| L6 | R3 Gi0/2 | R4 Gi0/0 | 10.0.34.0/30 | R3-R4 WAN underlay |

**Console Access Table:**

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

The `initial-configs/` directory contains the **pre-broken** starting state for this lab. When you run `setup_lab.py`, the following is pre-configured on each device — but with five embedded faults:

**What IS pre-configured:**

- Hostname and `ipv6 unicast-routing` on all routers
- All physical interface IP addresses (Loopback0, physical Gi interfaces)
- 802.1Q sub-interfaces for VRF CUSTOMER-A transit (Gi0/0.100 and Gi0/1.100 on R3; Gi0/0.100 on R1 and R2)
- VRF definitions for CUSTOMER-A and CUSTOMER-B (partially correct)
- OSPF process 1 underlay (partially correct — missing one network statement)
- OSPF process 2 overlay on R1 and R4
- IKEv2 proposal, policy, keyring, and profile on R1 and R4 (one side has wrong PSK)
- IPsec transform-set and profile on R1 and R4
- GRE Tunnel0 on R1 and R4 (binding incomplete on one side)
- VRF static routes for CUSTOMER-A on R1, R2, and R3

**What is NOT correct (embedded faults — diagnose these):**

- VRF interface assignment completeness
- IPv6 address family in all VRF definitions
- OSPF underlay coverage of all WAN links
- IPsec profile binding on tunnel interfaces
- IKEv2 pre-shared key consistency across peers

**PC1 and PC2:** Must be configured manually in the VPCS console:
```
PC1> ip 192.168.1.10/24 192.168.1.1
PC2> ip 192.168.2.10/24 192.168.2.1
```

---

## 5. Lab Challenge: Comprehensive Troubleshooting

> This is a capstone lab. The network is pre-broken.
> Diagnose and resolve 5+ concurrent faults spanning all blueprint bullets.
> No step-by-step guidance is provided — work from symptoms only.

The following degraded services have been reported. Each represents a distinct fault to diagnose and fix:

### Fault Area 1 — VRF CUSTOMER-A Cannot Deliver Traffic to the PC2 Subnet

PC2 (192.168.2.10/24) is unreachable from within VRF CUSTOMER-A on R1 and R3. The transit path through R3 exists, but packets do not reach their destination. The global routing table is unaffected.

**Success criteria:** `ping 192.168.2.10 vrf CUSTOMER-A source 192.168.1.1` from R1 succeeds. PC1 can ping PC2.

---

### Fault Area 2 — IPv6 VRF Routing Is Broken Through the Transit Router

IPv6 connectivity within VRF CUSTOMER-A is completely absent through the R3 transit path. `show ipv6 route vrf CUSTOMER-A` on R3 returns an empty table despite IPv6 being enabled globally.

**Success criteria:** `ping ipv6 2001:db8:a2::10 vrf CUSTOMER-A source 2001:db8:a1::1` from R1 succeeds.

---

### Fault Area 3 — Tunnel0 Line Protocol Is Down on Both R1 and R4

`show interface Tunnel0` on R1 reports "line protocol is down." OSPF process 2 shows no neighbors. The physical interfaces that form the underlay path appear to be connected.

**Success criteria:** `show interface Tunnel0` reports UP/UP on both R1 and R4. R3's `show ip ospf neighbor` shows R4 (4.4.4.4) in FULL state.

---

### Fault Area 4 — Tunnel0 Is Up but R1 Has Not Initiated Any IKEv2 Negotiation

Tunnel0 line protocol is UP, but `show crypto ipsec sa` on R1 shows no protected interfaces and `show crypto ikev2 sa` is empty. R1 has not initiated IKEv2 toward R4 — because of asymmetric tunnel protection, R4 drops R1's plain GRE packets, so OSPF process 2 has no neighbors.

**Success criteria:** `show running-config interface Tunnel0` on R1 includes `tunnel protection ipsec profile IPSEC-PROFILE`. After applying it, `show crypto ikev2 sa` shows an active negotiation attempt from R1 (SA will not reach READY until Ticket 5 is resolved).

---

### Fault Area 5 — IKEv2 Security Association Will Not Establish

After restoring the IPsec profile binding, IKEv2 negotiation begins but the SA never reaches READY state. `show crypto ikev2 sa` remains empty or shows a failed negotiation attempt.

**Success criteria:** `show crypto ikev2 sa` shows Status = READY on both R1 and R4. `ping 172.16.14.2 source Tunnel0` from R1 produces non-zero `#pkts encrypt` and `#pkts decrypt` in `show crypto ipsec sa`.

---

## 6. Verification & Analysis

The following outputs represent the expected healthy state once all five faults are resolved. Confirm each marked line or value to verify your fix is correct.

### VRF CUSTOMER-A — IPv4 Reachability

```bash
R1# show ip route vrf CUSTOMER-A
Routing Table: CUSTOMER-A
...
C    172.16.13.0/30 is directly connected, GigabitEthernet0/0.100     ! ← transit link R1-R3
S    192.168.2.0/24 [1/0] via 172.16.13.2                            ! ← static route to PC2 subnet

R3# show ip route vrf CUSTOMER-A
C    172.16.13.0/30 is directly connected, GigabitEthernet0/0.100     ! ← link to R1 CUSTOMER-A
C    172.16.23.0/30 is directly connected, GigabitEthernet0/1.100     ! ← link to R2 CUSTOMER-A
S    192.168.1.0/24 [1/0] via 172.16.13.1                            ! ← route to PC1 via R1
S    192.168.2.0/24 [1/0] via 172.16.23.1                            ! ← route to PC2 via R2

R2# show ip route vrf CUSTOMER-A
C    172.16.23.0/30 is directly connected, GigabitEthernet0/0.100     ! ← transit link R2-R3
C    192.168.2.0/24 is directly connected, GigabitEthernet0/2         ! ← PC2 subnet MUST be in VRF
S    192.168.1.0/24 [1/0] via 172.16.23.2                            ! ← route to PC1

R1# ping 192.168.2.10 vrf CUSTOMER-A source 192.168.1.1
!!!!!                                                                  ! ← 5 successes, no timeouts
```

### VRF CUSTOMER-A — IPv6 Reachability

```bash
R3# show vrf detail CUSTOMER-A
VRF CUSTOMER-A (VRF Id = 1); default RD 65001:100
  Interfaces:
    Gi0/0.100      Gi0/1.100
  Address family ipv4 (Table ID = 0x1):
    ...
  Address family ipv6 (Table ID = 0x1E000001):    ! ← ipv6 AF must be present
    ...

R3# show ipv6 route vrf CUSTOMER-A
IPv6 Routing Table - CUSTOMER-A - 5 entries
...
S    2001:DB8:A1::/64 [1/0] via 2001:DB8:CA13::1    ! ← IPv6 route to R1 LAN
S    2001:DB8:A2::/64 [1/0] via 2001:DB8:CA23::1    ! ← IPv6 route to R2 LAN

R1# ping ipv6 2001:db8:a2::10 vrf CUSTOMER-A source 2001:db8:a1::1
!!!!!                                                                  ! ← IPv6 end-to-end works
```

### Underlay OSPF — R4 Reachability

```bash
R3# show ip ospf interface brief
Interface    PID   Area            IP Address/Mask    Cost  State Nbrs F/C
Lo0           1    0               3.3.3.3/32           1   LOOP  0/0
Gi0/0         1    0               10.0.13.2/30         1   P2P   1/1
Gi0/1         1    0               10.0.23.2/30         1   P2P   1/1
Gi0/2         1    0               10.0.34.1/30         1   P2P   1/1   ! ← Gi0/2 must be in OSPF

R1# show ip route 4.4.4.4
Routing entry for 4.4.4.4/32
  Known via "ospf 1", distance 110, ...
  * 10.0.13.2, via GigabitEthernet0/0                                ! ← route via R3 must exist
```

### Tunnel0 — GRE and IPsec State

```bash
R1# show interface Tunnel0
Tunnel0 is up, line protocol is up                                    ! ← BOTH up
  Hardware is Tunnel
  Description: R1-R4 GRE-over-IPsec (encrypted overlay)
  ...
  Tunnel protocol/transport GRE/IP
    Key disabled, sequencing disabled
    Checksumming of packets disabled
  Tunnel source 1.1.1.1 (Loopback0), destination 4.4.4.4
  Tunnel Subblocks:
    src-track:
      Tunnel0 source tracking subblock associated with Loopback0

R1# show running-config interface Tunnel0
interface Tunnel0
 ...
 tunnel protection ipsec profile IPSEC-PROFILE                        ! ← protection binding must be present

R1# show crypto ipsec sa
interface: Tunnel0                                                     ! ← Tunnel0 listed as protected
    Crypto map tag: Tunnel0-head-0, local addr 1.1.1.1
...
   #pkts encrypt: 5, #pkts digest: 5                                  ! ← non-zero after ping
   #pkts decrypt: 5, #pkts verify: 5                                  ! ← non-zero after ping

R1# show crypto ikev2 sa
 IPv4 Crypto IKEv2 SA
Tunnel-id Local                 Remote                fvrf/ivrf            Status
1         1.1.1.1/500           4.4.4.4/500           none/none            READY  ! ← READY = IKEv2 up
```

### OSPF Overlay and End-to-End

```bash
R1# show ip ospf 2 neighbor
Neighbor ID     Pri   State       Dead Time   Address         Interface
4.4.4.4           0   FULL/  -    00:00:37    172.16.14.2     Tunnel0   ! ← R4 FULL over tunnel

R1# show ip route ospf 2
      10.0.0.0/8 is variably subnetted
O     10.4.4.4/32 [110/1001] via 172.16.14.2, Tunnel0                 ! ← R4 overlay prefix reachable

R1# ping 172.16.14.2 source Tunnel0
!!!!!                                                                  ! ← tunnel-sourced ping (populates IPsec counters)
```

---

## 7. Verification Cheatsheet

### VRF State Verification

```
show vrf
show vrf detail <NAME>
show ip route vrf <NAME>
show ipv6 route vrf <NAME>
show ip interface <intf>
```

| Command | What to Look For |
|---------|-----------------|
| `show vrf` | All VRFs and their assigned interfaces |
| `show vrf detail <NAME>` | Address families (ipv4, ipv6) — both must appear for dual-stack |
| `show ip route vrf <NAME>` | Connected and static routes — LAN prefix must be present |
| `show ipv6 route vrf <NAME>` | IPv6 connected and static routes — empty = missing IPv6 AF or routes |
| `show ip interface <intf>` | "VPN Routing/Forwarding" field — confirms VRF assignment |
| `show running-config interface <intf>` | `vrf forwarding` line — confirm correct VRF name |

> **Exam tip:** Moving an interface to a VRF removes its IP address silently. Always re-apply the address after `vrf forwarding <NAME>`. A missing address is the most common post-VRF-assignment mistake.

### OSPF Underlay Verification

```
show ip ospf neighbor
show ip ospf interface brief
show ip route ospf
show ip route <loopback-ip>
```

| Command | What to Look For |
|---------|-----------------|
| `show ip ospf neighbor` | All expected peers in FULL/DROTHER state |
| `show ip ospf interface brief` | Every WAN interface listed — missing = no OSPF on that segment |
| `show ip route <4.4.4.4>` | Route must exist for GRE tunnel destination |
| `show ip route ospf` | All loopbacks reachable via OSPF |

> **Exam tip:** If a GRE tunnel is DOWN, check the underlay route to the tunnel destination **before** investigating tunnel-specific config. The tunnel follows the route.

### GRE Tunnel Verification

```
show interface Tunnel0
show ip ospf 2 neighbor
ping <tunnel-dest-loopback>
traceroute <tunnel-dest> source <loopback>
```

| Command | What to Look For |
|---------|-----------------|
| `show interface Tunnel0` | "line protocol is up" — down means no route to destination |
| `show running-config interface Tunnel0` | Correct source, destination, mode, and protection line |
| `ping 4.4.4.4` (from R1 global) | Tests underlay path — must succeed for tunnel to come up |
| `show ip ospf 2 neighbor` | R4/R1 in FULL state over Tunnel0 |

### IPsec and IKEv2 Verification

```
show crypto ikev2 sa
show crypto ikev2 statistics
show crypto ipsec sa
show crypto ipsec profile
show running-config | section ikev2
```

| Command | What to Look For |
|---------|-----------------|
| `show crypto ikev2 sa` | Status = READY — any other state means negotiation failed |
| `show crypto ikev2 statistics` | `Auth failure` count increments — PSK mismatch |
| `show crypto ipsec sa` | Protected interface listed, `#pkts encrypt/decrypt` non-zero after ping |
| `show running-config interface Tunnel0` | `tunnel protection ipsec profile IPSEC-PROFILE` must be present |
| `show crypto ipsec profile` | Profile name and transform-set binding |

> **Exam tip:** If `show crypto ikev2 sa` is completely empty (no entries), the most likely cause is a missing `tunnel protection ipsec profile` on one side — IKEv2 never initiates. If entries appear but show "failed" or non-READY state, the issue is in the negotiation (PSK, proposal mismatch).

### Common Virtualization Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| VRF route table empty for a prefix | Interface not assigned to VRF, or static route missing |
| IPv6 VRF routes missing on one router | `address-family ipv6` not in `vrf definition` |
| Tunnel0 line protocol DOWN | No underlay route to tunnel destination |
| Tunnel UP but no crypto SA | Missing `tunnel protection ipsec profile` on one side |
| `show crypto ikev2 sa` empty | `tunnel protection` not configured (IKEv2 never triggered) |
| IKEv2 SA failed / AUTH error | Pre-shared key mismatch between peers |
| `#pkts decrypt` always zero | Ping not sourced from Tunnel interface (return path bypasses tunnel) |

---

## 8. Solutions (Spoiler Alert!)

> Try to diagnose all five faults independently before looking at these fixes!

### Fault 1 — R2 LAN Interface Not in VRF CUSTOMER-A

<details>
<summary>Click to view Diagnosis Steps</summary>

1. From R1, confirm the VRF CUSTOMER-A route to 192.168.2.0/24 is present:
   `show ip route vrf CUSTOMER-A` — route via 172.16.13.2 (R3) exists.
2. From R3, confirm the onward route to 192.168.2.0/24:
   `show ip route vrf CUSTOMER-A` — route via 172.16.23.1 (R2) exists.
3. Arrive at R2. Run `show ip route vrf CUSTOMER-A` — 192.168.2.0/24 should appear as "C" (connected) but does NOT.
4. Run `show running-config interface GigabitEthernet0/2` on R2 — no `vrf forwarding CUSTOMER-A` line. The interface is in the global table.
5. Root cause: R2's LAN interface (Gi0/2) is assigned to the global routing table instead of VRF CUSTOMER-A.
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! R2 — re-assign Gi0/2 to VRF CUSTOMER-A and re-apply all addresses
interface GigabitEthernet0/2
 vrf forwarding CUSTOMER-A
 ip address 192.168.2.1 255.255.255.0
 ipv6 address 2001:db8:a2::1/64
```

Note: `vrf forwarding CUSTOMER-A` clears the existing IP address. Both `ip address` and `ipv6 address` must be re-applied after the assignment.

Verify: `show ip route vrf CUSTOMER-A` on R2 now shows `C 192.168.2.0/24` connected on Gi0/2.
</details>

---

### Fault 2 — VRF CUSTOMER-A Missing IPv6 Address Family on R3

<details>
<summary>Click to view Diagnosis Steps</summary>

1. From R1, try: `ping ipv6 2001:db8:ca13::2 vrf CUSTOMER-A` — the R3-side of the transit link. This may succeed (R1→R3 sub-interface link is IPv6 enabled on both ends) or fail depending on R3 interface state.
2. Check R3: `show ipv6 route vrf CUSTOMER-A` — returns **empty table** or "No entries found."
3. Check R3 VRF definition: `show vrf detail CUSTOMER-A` — shows only `address-family ipv4`, NOT `address-family ipv6`. This is the root cause.
4. Confirm sub-interfaces lack IPv6: `show running-config interface GigabitEthernet0/0.100` on R3 — no `ipv6 address` line.
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! R3 — add IPv6 address family, then re-apply IPv6 addresses and routes
vrf definition CUSTOMER-A
 address-family ipv6
 exit-address-family
!
interface GigabitEthernet0/0.100
 ipv6 address 2001:db8:ca13::2/64
!
interface GigabitEthernet0/1.100
 ipv6 address 2001:db8:ca23::2/64
!
ipv6 route vrf CUSTOMER-A 2001:db8:a1::/64 2001:db8:ca13::1
ipv6 route vrf CUSTOMER-A 2001:db8:a2::/64 2001:db8:ca23::1
```

Verify: `show vrf detail CUSTOMER-A` on R3 shows both `address-family ipv4` and `address-family ipv6`. `show ipv6 route vrf CUSTOMER-A` shows static routes to 2001:db8:a1::/64 and 2001:db8:a2::/64.
</details>

---

### Fault 3 — R3 Not Advertising 10.0.34.0/30 in OSPF (Tunnel Underlay Break)

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `show interface Tunnel0` on R1 — line protocol is DOWN.
2. `ping 4.4.4.4` from R1 — fails. No route to host.
3. `show ip route 4.4.4.4` on R1 — no routing entry.
4. Check R3 OSPF: `show ip ospf neighbor` on R3 — R1 is present but R4 is **absent**.
5. Check R3 OSPF interfaces: `show ip ospf interface brief` — Gi0/2 (R3-R4 link) is not listed.
6. Confirm: `show running-config | section router ospf 1` on R3 — no `network 10.0.34.0 0.0.0.3 area 0` statement.
7. Root cause: OSPF is not enabled on R3's Gi0/2, so no adjacency forms with R4 and 4.4.4.4 is never learned.
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! R3
router ospf 1
 network 10.0.34.0 0.0.0.3 area 0
```

Verify: `show ip ospf neighbor` on R3 shows R4 (4.4.4.4) in FULL state. `show ip route 4.4.4.4` on R1 shows an OSPF route. `show interface Tunnel0` on R1 comes up to UP/UP within ~30 seconds.
</details>

---

### Fault 4 — Tunnel0 Missing IPsec Protection Profile on R1

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `show interface Tunnel0` on R1 — UP/UP (after Fault 3 fix). GRE is working.
2. `show crypto ipsec sa` on R1 — output shows "There are no ipsec sas" or no "protected interface" entry.
3. `show running-config interface Tunnel0` on R1 — no `tunnel protection ipsec profile` line.
4. Compare R4: `show running-config interface Tunnel0` on R4 — `tunnel protection ipsec profile IPSEC-PROFILE` is present.
5. Root cause: R1's Tunnel0 is missing the IPsec profile binding. GRE works but IKEv2 is never triggered from R1's side.
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! R1
interface Tunnel0
 tunnel protection ipsec profile IPSEC-PROFILE
```

After applying, IKEv2 negotiation will initiate. If the SA still does not reach READY state, proceed to Fault 5.
</details>

---

### Fault 5 — IKEv2 Pre-Shared Key Mismatch on R4

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `show crypto ikev2 sa` on R1 — empty or shows IKE_SA_INIT/IKE_AUTH in progress but not READY.
2. `show crypto ikev2 statistics` on R1 — `Auth failure` counter is non-zero.
3. `show running-config | section ikev2 keyring` on R1 — PSK for peer R4 is `LAB-PSK-2026`.
4. `show running-config | section ikev2 keyring` on R4 — PSK for peer R1 is `WRONG-PSK-LAB`. Mismatch confirmed.
5. Root cause: R4's IKEv2 keyring has an incorrect pre-shared key. IKEv2 completes IKE_SA_INIT (DH exchange) but fails IKE_AUTH (authentication).
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! R4
crypto ikev2 keyring IKEv2-KEYRING
 peer R1
  pre-shared-key LAB-PSK-2026
```

Verify: `show crypto ikev2 sa` on both R1 and R4 shows Status = READY within 10–20 seconds. Then run `ping 172.16.14.2 source Tunnel0` from R1 and confirm `show crypto ipsec sa` shows non-zero encrypt/decrypt counters.
</details>

---

### Complete Solution Configs

<details>
<summary>Click to view R1 Solution Config</summary>

```bash
hostname R1
!
vrf definition CUSTOMER-A
 rd 65001:100
 address-family ipv4
 exit-address-family
 address-family ipv6
 exit-address-family
!
vrf definition CUSTOMER-B
 rd 65001:200
 address-family ipv4
 exit-address-family
 address-family ipv6
 exit-address-family
!
ipv6 unicast-routing
!
crypto ikev2 proposal IKEv2-PROP
 encryption aes-cbc-256
 integrity sha256
 group 14
!
crypto ikev2 policy IKEv2-POL
 proposal IKEv2-PROP
!
crypto ikev2 keyring IKEv2-KEYRING
 peer R4
  address 4.4.4.4
  pre-shared-key LAB-PSK-2026
!
crypto ikev2 profile IKEv2-PROFILE
 match identity remote address 4.4.4.4 255.255.255.255
 authentication remote pre-share
 authentication local pre-share
 keyring local IKEv2-KEYRING
!
crypto ipsec transform-set TS-AES256 esp-aes 256 esp-sha256-hmac
 mode tunnel
!
crypto ipsec profile IPSEC-PROFILE
 set transform-set TS-AES256
 set ikev2-profile IKEv2-PROFILE
!
interface Loopback0
 ip address 1.1.1.1 255.255.255.255
!
interface Loopback1
 vrf forwarding CUSTOMER-B
 ip address 172.20.1.1 255.255.255.0
 ipv6 address 2001:db8:b1::1/64
!
interface Tunnel0
 description R1-R4 GRE-over-IPsec (encrypted overlay)
 ip address 172.16.14.1 255.255.255.252
 ipv6 address 2001:db8:14::1/64
 ip mtu 1400
 ip tcp adjust-mss 1360
 tunnel source Loopback0
 tunnel destination 4.4.4.4
 tunnel mode gre ip
 tunnel protection ipsec profile IPSEC-PROFILE
 ip ospf network point-to-point
 no shutdown
!
interface GigabitEthernet0/0
 ip address 10.0.13.1 255.255.255.252
 no shutdown
!
interface GigabitEthernet0/0.100
 encapsulation dot1Q 100
 vrf forwarding CUSTOMER-A
 ip address 172.16.13.1 255.255.255.252
 ipv6 address 2001:db8:ca13::1/64
!
interface GigabitEthernet0/1
 ip address 10.0.12.1 255.255.255.252
 no shutdown
!
interface GigabitEthernet0/2
 vrf forwarding CUSTOMER-A
 ip address 192.168.1.1 255.255.255.0
 ipv6 address 2001:db8:a1::1/64
 no shutdown
!
router ospf 1
 router-id 1.1.1.1
 network 1.1.1.1 0.0.0.0 area 0
 network 10.0.13.0 0.0.0.3 area 0
 network 10.0.12.0 0.0.0.3 area 0
!
router ospf 2
 router-id 1.1.1.1
 network 172.16.14.0 0.0.0.3 area 0
!
ip route vrf CUSTOMER-A 192.168.2.0 255.255.255.0 172.16.13.2
ipv6 route vrf CUSTOMER-A 2001:db8:a2::/64 2001:db8:ca13::2
ip route vrf CUSTOMER-B 192.168.1.1 255.255.255.255 GigabitEthernet0/2 192.168.1.1
ip route vrf CUSTOMER-A 172.20.1.1 255.255.255.255 Loopback1 172.20.1.1
!
end
```
</details>

<details>
<summary>Click to view R2 Solution Config</summary>

```bash
hostname R2
!
vrf definition CUSTOMER-A
 rd 65001:100
 address-family ipv4
 exit-address-family
 address-family ipv6
 exit-address-family
!
vrf definition CUSTOMER-B
 rd 65001:200
 address-family ipv4
 exit-address-family
 address-family ipv6
 exit-address-family
!
ipv6 unicast-routing
!
interface Loopback0
 ip address 2.2.2.2 255.255.255.255
!
interface Loopback1
 vrf forwarding CUSTOMER-B
 ip address 172.20.2.1 255.255.255.0
 ipv6 address 2001:db8:b2::1/64
!
interface Loopback2
 vrf forwarding CUSTOMER-B
 ip address 192.168.2.100 255.255.255.0
!
interface GigabitEthernet0/0
 ip address 10.0.23.1 255.255.255.252
 no shutdown
!
interface GigabitEthernet0/0.100
 encapsulation dot1Q 100
 vrf forwarding CUSTOMER-A
 ip address 172.16.23.1 255.255.255.252
 ipv6 address 2001:db8:ca23::1/64
!
interface GigabitEthernet0/1
 ip address 10.0.12.2 255.255.255.252
 no shutdown
!
interface GigabitEthernet0/2
 vrf forwarding CUSTOMER-A
 ip address 192.168.2.1 255.255.255.0
 ipv6 address 2001:db8:a2::1/64
 no shutdown
!
router ospf 1
 router-id 2.2.2.2
 network 2.2.2.2 0.0.0.0 area 0
 network 10.0.23.0 0.0.0.3 area 0
 network 10.0.12.0 0.0.0.3 area 0
!
ip route vrf CUSTOMER-A 192.168.1.0 255.255.255.0 172.16.23.2
ipv6 route vrf CUSTOMER-A 2001:db8:a1::/64 2001:db8:ca23::2
!
end
```
</details>

<details>
<summary>Click to view R3 Solution Config</summary>

```bash
hostname R3
!
vrf definition CUSTOMER-A
 rd 65001:100
 address-family ipv4
 exit-address-family
 address-family ipv6
 exit-address-family
!
ipv6 unicast-routing
!
interface Loopback0
 ip address 3.3.3.3 255.255.255.255
!
interface GigabitEthernet0/0
 ip address 10.0.13.2 255.255.255.252
 no shutdown
!
interface GigabitEthernet0/0.100
 encapsulation dot1Q 100
 vrf forwarding CUSTOMER-A
 ip address 172.16.13.2 255.255.255.252
 ipv6 address 2001:db8:ca13::2/64
!
interface GigabitEthernet0/1
 ip address 10.0.23.2 255.255.255.252
 no shutdown
!
interface GigabitEthernet0/1.100
 encapsulation dot1Q 100
 vrf forwarding CUSTOMER-A
 ip address 172.16.23.2 255.255.255.252
 ipv6 address 2001:db8:ca23::2/64
!
interface GigabitEthernet0/2
 ip address 10.0.34.1 255.255.255.252
 no shutdown
!
router ospf 1
 router-id 3.3.3.3
 network 3.3.3.3 0.0.0.0 area 0
 network 10.0.13.0 0.0.0.3 area 0
 network 10.0.23.0 0.0.0.3 area 0
 network 10.0.34.0 0.0.0.3 area 0
!
ip route vrf CUSTOMER-A 192.168.1.0 255.255.255.0 172.16.13.1
ip route vrf CUSTOMER-A 192.168.2.0 255.255.255.0 172.16.23.1
ipv6 route vrf CUSTOMER-A 2001:db8:a1::/64 2001:db8:ca13::1
ipv6 route vrf CUSTOMER-A 2001:db8:a2::/64 2001:db8:ca23::1
!
end
```
</details>

<details>
<summary>Click to view R4 Solution Config</summary>

```bash
hostname R4
!
ipv6 unicast-routing
!
crypto ikev2 proposal IKEv2-PROP
 encryption aes-cbc-256
 integrity sha256
 group 14
!
crypto ikev2 policy IKEv2-POL
 proposal IKEv2-PROP
!
crypto ikev2 keyring IKEv2-KEYRING
 peer R1
  address 1.1.1.1
  pre-shared-key LAB-PSK-2026
!
crypto ikev2 profile IKEv2-PROFILE
 match identity remote address 1.1.1.1 255.255.255.255
 authentication remote pre-share
 authentication local pre-share
 keyring local IKEv2-KEYRING
!
crypto ipsec transform-set TS-AES256 esp-aes 256 esp-sha256-hmac
 mode tunnel
!
crypto ipsec profile IPSEC-PROFILE
 set transform-set TS-AES256
 set ikev2-profile IKEv2-PROFILE
!
interface Loopback0
 ip address 4.4.4.4 255.255.255.255
!
interface Loopback1
 ip address 10.4.4.4 255.255.255.255
!
interface Tunnel0
 description R4-R1 GRE-over-IPsec (encrypted overlay)
 ip address 172.16.14.2 255.255.255.252
 ipv6 address 2001:db8:14::2/64
 ip mtu 1400
 ip tcp adjust-mss 1360
 tunnel source Loopback0
 tunnel destination 1.1.1.1
 tunnel mode gre ip
 tunnel protection ipsec profile IPSEC-PROFILE
 ip ospf network point-to-point
 no shutdown
!
interface GigabitEthernet0/0
 ip address 10.0.34.2 255.255.255.252
 no shutdown
!
router ospf 1
 router-id 4.4.4.4
 network 4.4.4.4 0.0.0.0 area 0
 network 10.0.34.0 0.0.0.3 area 0
!
router ospf 2
 router-id 4.4.4.4
 network 172.16.14.0 0.0.0.3 area 0
 network 10.4.4.4 0.0.0.0 area 0
!
end
```
</details>

---

## 9. Troubleshooting Scenarios

All five faults are **pre-injected** via `setup_lab.py`. There are no separate
inject scripts in this lab — the initial configs ARE the broken state.
Tickets are ordered to follow natural peel-back diagnosis: VRF faults first
(Tickets 1–2), then underlay routing (Ticket 3), then IPsec faults in dependency
order (Tickets 4–5). Work sequentially unless you have reason to branch.

### Workflow

```bash
python3 setup_lab.py --host <eve-ng-ip>                        # push pre-broken configs (5 faults)
# (diagnose + fix each ticket below)
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>  # restore to known-good
```

---

### Ticket 1 — VRF CUSTOMER-A Cannot Reach the PC2 Subnet

Your team reports that PC1 (192.168.1.10) cannot reach PC2 (192.168.2.10) through the CUSTOMER-A VRF. The OSPF underlay between R1, R2, and R3 appears healthy. The issue is isolated to the VRF CUSTOMER-A routing plane.

**Success criteria:** `ping 192.168.2.10 vrf CUSTOMER-A source 192.168.1.1` from R1 succeeds. PC1 can ping PC2.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. On R1: `show ip route vrf CUSTOMER-A` — confirm a route to 192.168.2.0/24 exists (static via 172.16.13.2). The route is correct; the problem is downstream.
2. On R3: `show ip route vrf CUSTOMER-A` — confirm routes to both 192.168.1.0/24 and 192.168.2.0/24 exist. The route to 192.168.2.0/24 points via 172.16.23.1 (R2's transit interface).
3. On R2: `show ip route vrf CUSTOMER-A` — 192.168.2.0/24 is **absent** from the VRF table (it is connected, but it's in the global table, not VRF CUSTOMER-A).
4. On R2: `show running-config interface GigabitEthernet0/2` — no `vrf forwarding CUSTOMER-A` line. The interface is in the global routing table.
5. Root cause: R2's LAN-facing interface (Gi0/2) is not assigned to VRF CUSTOMER-A. PC2's subnet is only reachable from the global table.
</details>

<details>
<summary>Click to view Fix</summary>

On R2, enter interface configuration for Gi0/2, assign it to VRF CUSTOMER-A, and reapply both the IPv4 and IPv6 addresses (both are cleared when `vrf forwarding` is applied):

```bash
interface GigabitEthernet0/2
 vrf forwarding CUSTOMER-A
 ip address 192.168.2.1 255.255.255.0
 ipv6 address 2001:db8:a2::1/64
```

Verify: `show ip route vrf CUSTOMER-A` on R2 now shows `C 192.168.2.0/24` connected on Gi0/2. Then `ping 192.168.2.10 vrf CUSTOMER-A source 192.168.1.1` from R1 succeeds.
</details>

---

### Ticket 2 — IPv6 Connectivity Is Completely Absent Through the VRF CUSTOMER-A Transit

With IPv4 VRF connectivity restored (Ticket 1), IPv6 traffic within VRF CUSTOMER-A still fails. `ping ipv6 2001:db8:a2::10 vrf CUSTOMER-A` from R1 does not reach PC2. R3 is the transit router for all CUSTOMER-A traffic.

**Success criteria:** `ping ipv6 2001:db8:a2::10 vrf CUSTOMER-A source 2001:db8:a1::1` from R1 succeeds. `show ipv6 route vrf CUSTOMER-A` on R3 shows static routes to both customer LANs.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. On R1: `show ipv6 route vrf CUSTOMER-A` — shows a static route to 2001:db8:a2::/64 via 2001:db8:ca13::2. Route exists at R1.
2. On R3: `show ipv6 route vrf CUSTOMER-A` — returns **empty** or "No entries found." R3 has no IPv6 VRF routes.
3. On R3: `show vrf detail CUSTOMER-A` — inspect the address families listed. Only `address-family ipv4` appears; `address-family ipv6` is **missing**.
4. On R3: `show running-config interface GigabitEthernet0/0.100` — no `ipv6 address` line (the AF was never configured, so the address was never applied).
5. Root cause: VRF CUSTOMER-A on R3 lacks the `address-family ipv6` declaration. Without it, IPv6 routes cannot exist in the VRF and IPv6 addresses on VRF interfaces are not retained.
</details>

<details>
<summary>Click to view Fix</summary>

Add the IPv6 address family to VRF CUSTOMER-A on R3, then reapply IPv6 addresses to both sub-interfaces and add the two IPv6 static routes:

```bash
vrf definition CUSTOMER-A
 address-family ipv6
 exit-address-family
!
interface GigabitEthernet0/0.100
 ipv6 address 2001:db8:ca13::2/64
!
interface GigabitEthernet0/1.100
 ipv6 address 2001:db8:ca23::2/64
!
ipv6 route vrf CUSTOMER-A 2001:db8:a1::/64 2001:db8:ca13::1
ipv6 route vrf CUSTOMER-A 2001:db8:a2::/64 2001:db8:ca23::1
```

Verify: `show vrf detail CUSTOMER-A` on R3 shows both `address-family ipv4` and `address-family ipv6`. `show ipv6 route vrf CUSTOMER-A` shows static routes to 2001:db8:a1::/64 and 2001:db8:a2::/64.
</details>

---

### Ticket 3 — Tunnel0 Line Protocol Down on Both R1 and R4

`show interface Tunnel0` on R1 reports "line protocol is down." OSPF process 2 has no neighbors. The encrypted overlay to R4 is completely non-operational.

**Success criteria:** `show interface Tunnel0` shows UP/UP on both R1 and R4. R3's `show ip ospf neighbor` shows R4 (4.4.4.4) in FULL state. Note: OSPF process 2 (overlay) adjacency will not form yet — Ticket 4's fault prevents it.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. On R1: `show interface Tunnel0` — line protocol is DOWN. Tunnel source (Loopback0, 1.1.1.1) is UP. Destination is 4.4.4.4.
2. On R1: `ping 4.4.4.4` — fails. `show ip route 4.4.4.4` — no route.
3. On R1: `show ip ospf neighbor` (process 1) — R2 (via 10.0.12.x) and R3 (via 10.0.13.x) are FULL, but R4 is absent.
4. On R3: `show ip ospf neighbor` — R1 is FULL (via Gi0/0), R2 is FULL (via Gi0/1), but **no R4 neighbor on Gi0/2**.
5. On R3: `show ip ospf interface brief` — Gi0/2 is **not listed** (OSPF is not running on it).
6. On R3: `show running-config | section router ospf 1` — the `network 10.0.34.0 0.0.0.3 area 0` statement is missing.
7. Root cause: OSPF process 1 on R3 is not enabled on the Gi0/2 (R3-R4) segment. R4 never forms an adjacency with R3, so 4.4.4.4 is unreachable from R1.
</details>

<details>
<summary>Click to view Fix</summary>

Add the missing OSPF network statement for the R3-R4 link:

```bash
! R3
router ospf 1
 network 10.0.34.0 0.0.0.3 area 0
```

Verify: `show ip ospf neighbor` on R3 shows R4 (4.4.4.4) in FULL state within ~30 seconds. `show ip route 4.4.4.4` on R1 shows an OSPF route. `show interface Tunnel0` on R1 transitions to UP/UP.
</details>

---

### Ticket 4 — Tunnel0 Is Up but No IPsec Encryption Is Engaged

After restoring underlay routing (Ticket 3), Tunnel0 line protocol comes up. However, `show crypto ipsec sa` on R1 shows no protected interfaces and `show crypto ikev2 sa` is empty — R1 has not initiated any IKEv2 negotiation. Because of asymmetric tunnel protection, R4 drops R1's unencrypted GRE packets, so OSPF process 2 remains neighborless.

**Success criteria:** `show running-config interface Tunnel0` on R1 includes `tunnel protection ipsec profile IPSEC-PROFILE`. After applying it, `show crypto ikev2 sa` shows an active negotiation attempt from R1 (the SA will not reach READY until Ticket 5 is resolved).

<details>
<summary>Click to view Diagnosis Steps</summary>

1. On R1: `show crypto ipsec sa` — output shows "There are no ipsec sas" or no "interface: Tunnel0" entry.
2. On R1: `show running-config interface Tunnel0` — the `tunnel protection ipsec profile IPSEC-PROFILE` line is **absent**.
3. On R4: `show running-config interface Tunnel0` — `tunnel protection ipsec profile IPSEC-PROFILE` IS present.
4. Result: R4 is configured to encrypt, but R1 sends and receives plain GRE. With R1 not initiating IKEv2 and not expecting encrypted inbound, no SA ever forms.
5. Root cause: The `tunnel protection` binding is missing from Tunnel0 on R1.
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! R1
interface Tunnel0
 tunnel protection ipsec profile IPSEC-PROFILE
```

After applying, R1 will initiate IKEv2 toward R4. If the SA does not reach READY state within 20–30 seconds, check `show crypto ikev2 sa` and proceed to Ticket 5.
</details>

---

### Ticket 5 — IKEv2 Negotiation Fails After Protection Profile Is Applied

After adding `tunnel protection ipsec profile IPSEC-PROFILE` to R1's Tunnel0 (Ticket 4), IKEv2 negotiation starts but `show crypto ikev2 sa` never shows a READY SA. The IKE_AUTH exchange fails.

**Success criteria:** `show crypto ikev2 sa` shows Status = READY on both R1 and R4. `ping 172.16.14.2 source Tunnel0` from R1 produces non-zero encrypt/decrypt counters in `show crypto ipsec sa`.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. On R1: `show crypto ikev2 sa` — SA entry may appear briefly then disappear, or remain absent.
2. On R1: `show crypto ikev2 statistics` — look for non-zero "Auth failure" or "IKE_AUTH" failures in the counters.
3. On R1: `show running-config | section ikev2 keyring` — shows `pre-shared-key LAB-PSK-2026` for peer R4.
4. On R4: `show running-config | section ikev2 keyring` — shows `pre-shared-key WRONG-PSK-LAB` for peer R1.
5. Root cause: The IKEv2 pre-shared keys do not match. R1 uses `LAB-PSK-2026`; R4 uses `WRONG-PSK-LAB`. IKE_SA_INIT completes (DH exchange is PSK-independent), but IKE_AUTH fails authentication.
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! R4
crypto ikev2 keyring IKEv2-KEYRING
 peer R1
  pre-shared-key LAB-PSK-2026
```

Verify: `show crypto ikev2 sa` on R1 and R4 shows Status = READY within 10–20 seconds. Then:
```bash
R1# ping 172.16.14.2 source Tunnel0
!!!!!

R1# show crypto ipsec sa
interface: Tunnel0
   #pkts encrypt: 5, #pkts digest: 5
   #pkts decrypt: 5, #pkts verify: 5
```
</details>

---

## 10. Lab Completion Checklist

### Troubleshooting — All Five Faults Resolved

- [ ] Ticket 1: `ping 192.168.2.10 vrf CUSTOMER-A source 192.168.1.1` from R1 succeeds. R2 Gi0/2 is in VRF CUSTOMER-A.
- [ ] Ticket 2: `ping ipv6 2001:db8:a2::10 vrf CUSTOMER-A source 2001:db8:a1::1` from R1 succeeds. `show vrf detail CUSTOMER-A` on R3 shows both IPv4 and IPv6 address families.
- [ ] Ticket 3: `show interface Tunnel0` is UP/UP on both R1 and R4. R3's `show ip ospf neighbor` shows R4 in FULL state. R3's OSPF 1 includes the 10.0.34.0/30 network statement.
- [ ] Ticket 4: `show running-config interface Tunnel0` on R1 includes `tunnel protection ipsec profile IPSEC-PROFILE`. `show crypto ikev2 sa` shows R1 initiating IKEv2 toward R4.
- [ ] Ticket 5: `show crypto ikev2 sa` shows Status = READY on both R1 and R4. `ping 172.16.14.2 source Tunnel0` from R1 produces non-zero encrypt/decrypt counters.

### Full Restoration Verification

- [ ] `ping 192.168.2.10 vrf CUSTOMER-A source 192.168.1.1` from R1 succeeds (PC2 reachable via VRF IPv4)
- [ ] `ping ipv6 2001:db8:a2::10 vrf CUSTOMER-A source 2001:db8:a1::1` from R1 succeeds (PC2 reachable via VRF IPv6)
- [ ] `ping 172.16.14.2 source Tunnel0` from R1 succeeds (overlay reachable)
- [ ] `show crypto ikev2 sa` shows READY on both R1 and R4 (IKEv2 established)
- [ ] `show crypto ipsec sa` on R1 shows non-zero encrypt/decrypt counters after ping (traffic is encrypted)
- [ ] `show ip ospf 2 neighbor` on R1 shows R4 in FULL state (OSPF overlay up)
