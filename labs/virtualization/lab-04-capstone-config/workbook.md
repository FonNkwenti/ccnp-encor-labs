# Lab 04 — VRF and Tunneling Full Mastery (Capstone I)

## Table of Contents

1. [Concepts & Skills Covered](#1-concepts--skills-covered)
2. [Topology & Scenario](#2-topology--scenario)
3. [Hardware & Environment Specifications](#3-hardware--environment-specifications)
4. [Base Configuration](#4-base-configuration)
5. [Lab Challenge: Full Protocol Mastery](#5-lab-challenge-full-protocol-mastery)
6. [Verification & Analysis](#6-verification--analysis)
7. [Verification Cheatsheet](#7-verification-cheatsheet)
8. [Solutions (Spoiler Alert!)](#8-solutions-spoiler-alert)
9. [Troubleshooting Scenarios](#9-troubleshooting-scenarios)
10. [Lab Completion Checklist](#10-lab-completion-checklist)

---

## 1. Concepts & Skills Covered

**Exam Objective:** 2.2, 2.2.a, 2.2.b — Configure and verify VRF-Lite (Virtualization), GRE, and IPsec Tunneling

This capstone integrates all virtualization techniques from labs 00–03 into a single end-to-end deployment. You will build VRF routing table isolation and inter-site transit from scratch, then overlay an encrypted GRE tunnel between branch and remote sites — combining every blueprint bullet for this chapter without guided steps.

### VRF and VRF-Lite Recap

A **VRF (Virtual Routing and Forwarding)** instance creates a private IP routing table on a single router. Interfaces, routes, and protocols that belong to a VRF are completely invisible to the global table and to other VRFs. This is the software equivalent of dedicated physical routers.

**VRF-Lite** extends a VRF across multiple routers using sub-interfaces (802.1Q encapsulation) or dedicated physical links. There is no MPLS involvement — each transit router carries the VRF routing table segment using static routes or per-VRF dynamic routing.

Key IOS mechanics:
- `vrf definition <NAME>` with `address-family ipv4`/`ipv6` enables dual-stack.
- `vrf forwarding <NAME>` applied to an interface removes its IP address — you must reapply after the VRF assignment.
- Sub-interface: `encapsulation dot1Q <VLAN>` identifies the VRF traffic stream on a shared physical link.

```
R1 Gi0/0.100 (VLAN 100, VRF A)  ──dot1Q──  R3 Gi0/0.100  ──dot1Q──  R2 Gi0/0.100
R1 Gi0/0     (global table)      ────────── R3 Gi0/0      ───────── R2 Gi0/0
```

### GRE Tunneling

GRE (Generic Routing Encapsulation, IP protocol 47) wraps any Layer-3 packet inside an IP header. This creates a virtual point-to-point link between two loopback addresses, regardless of the number of underlay hops.

Key properties:
- **Multicast capable** — OSPF hellos traverse GRE natively.
- **Dual-stack** — IPv6 can be carried as inner payload over an IPv4 GRE tunnel.
- **No encryption** — traffic is in cleartext unless combined with IPsec.
- **MTU awareness** — GRE adds a 24-byte header; set `ip mtu 1400` and `ip tcp adjust-mss 1360` to prevent fragmentation.

IOS interface skeleton:
```
interface Tunnel0
 tunnel source Loopback0
 tunnel destination <remote-loopback>
 tunnel mode gre ip
```

### IKEv2 and IPsec

**IKEv2** is the modern key-exchange protocol that negotiates IPsec Security Associations. It replaces IKEv1's two-phase model with a single 4-message exchange.

IKEv2 four-tier hierarchy on IOS:

| Object | Purpose |
|--------|---------|
| Proposal | Specifies encryption (`aes-cbc-256`), integrity (`sha256`), and DH group (`14`) |
| Policy | Selects which proposal(s) to offer |
| Keyring | Maps peer IP addresses to pre-shared keys |
| Profile | Binds policy + keyring; defines peer identity matching |

The IPsec profile (`crypto ipsec profile`) links the transform-set (ESP algorithms) to the IKEv2 profile and is applied to the tunnel interface with `tunnel protection ipsec profile <NAME>`.

### GRE-over-IPsec

GRE-over-IPsec combines both technologies: the GRE tunnel carries multicast and IPv6, while IPsec encrypts all GRE-encapsulated traffic. The result is an overlay that supports OSPF adjacency AND encryption.

```
[IP Payload]  →  [GRE Header + IP]  →  [ESP/IPsec]  →  [Outer IP (transport)]
   (inner)          (overlay)            (encryption)       (underlay)
```

Configuration sequence: configure GRE tunnel first, verify OSPF adjacency, then apply `tunnel protection ipsec profile <NAME>` — the profile addition triggers IKEv2 negotiation and encrypts the existing GRE path.

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| VRF dual-stack | Create VRF instances with IPv4 and IPv6 address families |
| VRF-Lite transit | Extend a VRF across multiple routers via sub-interfaces |
| Inter-VRF route leaking | Share selected prefixes between isolated routing tables |
| GRE tunnel construction | Build a point-to-point overlay using loopback anchors |
| IKEv2 hierarchy | Configure proposal, policy, keyring, and profile from scratch |
| GRE-over-IPsec | Apply IPsec protection to an existing GRE tunnel |
| OSPF over overlay | Run OSPF process 2 over the GRE tunnel for overlay routing |
| IPsec SA verification | Interpret `show crypto ipsec sa` packet counters |

---

## 2. Topology & Scenario

**Scenario:** GlobalCorp operates two branch sites (R1 and R2) connected through a shared WAN transit router (R3). A remote site (R4) exists beyond R3 that is reachable only via overlay tunneling. The network team must implement full tenant separation using VRF-Lite for two customers (CUSTOMER-A and CUSTOMER-B), then connect the R1 branch to the R4 remote site via an encrypted GRE-over-IPsec tunnel. All configuration must be built from scratch — only interface IP addressing is pre-loaded.

```
              ┌─────────────────────────────┐
              │            R1               │
              │     Branch/Site Router      │
              │     Lo0: 1.1.1.1/32         │
              └─────┬──────────────┬────────┘
           Gi0/0    │              │ Gi0/1
      10.0.13.1/30  │              │ 10.0.12.1/30
                    │              │
      10.0.13.2/30  │              │ 10.0.12.2/30
           Gi0/0    │              │ Gi0/1
       ┌────────────┘              └────────────────┐
       │                                            │
┌──────┴─────────────┐              ┌───────────────┴───────┐
│        R3           │              │          R2            │
│  Transit Router     │              │  Branch/Site Router    │
│  Lo0: 3.3.3.3/32    │              │  Lo0: 2.2.2.2/32       │
└────────┬────────────┘              └────────────────────────┘
     Gi0/2│ 10.0.34.1/30                    │ Gi0/2
          │                                  │ 192.168.2.1/24
          │ 10.0.34.2/30                     │
     Gi0/0│                           ┌──────┴──────┐
┌─────────┴──────────┐                │    PC2      │
│        R4           │                │192.168.2.10 │
│ Remote Site Router  │                └─────────────┘
│  Lo0: 4.4.4.4/32    │
│  Lo1: 10.4.4.4/32   │
└─────────────────────┘

R1 Gi0/2 ──── PC1 (192.168.1.10/24)   [VRF CUSTOMER-A LAN, site 1]
R2 Gi0/2 ──── PC2 (192.168.2.10/24)   [VRF CUSTOMER-A LAN, site 2]

VRF-Lite CUSTOMER-A transit (dot1Q VLAN 100):
  R1 Gi0/0.100 (172.16.13.1/30) ──── R3 Gi0/0.100 (172.16.13.2/30)
  R3 Gi0/1.100 (172.16.23.2/30) ──── R2 Gi0/0.100 (172.16.23.1/30)

GRE-over-IPsec overlay tunnel (Tunnel0):
  R1 Lo0 (1.1.1.1) ══════════ R4 Lo0 (4.4.4.4)  [traverses R3 underlay]
  Tunnel0 IPs: 172.16.14.1/30 <-> 172.16.14.2/30
```

---

## 3. Hardware & Environment Specifications

**Platform:** EVE-NG — all routers use IOSv (iosv-158-3) images.

**Cabling:**

| Link | Source | Destination | Subnet |
|------|--------|-------------|--------|
| L1 | R1 Gi0/0 | R3 Gi0/0 | 10.0.13.0/30 |
| L2 | R2 Gi0/0 | R3 Gi0/1 | 10.0.23.0/30 |
| L3 | R1 Gi0/1 | R2 Gi0/1 | 10.0.12.0/30 |
| L4 | R1 Gi0/2 | PC1 | 192.168.1.0/24 |
| L5 | R2 Gi0/2 | PC2 | 192.168.2.0/24 |
| L6 | R3 Gi0/2 | R4 Gi0/0 | 10.0.34.0/30 |

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

Run `python3 setup_lab.py --host <eve-ng-ip>` to load the starting configuration.

**Pre-loaded on all routers:**
- Hostnames
- Interface IPv4 addresses (global routing table only)
- `ipv6 unicast-routing`

**NOT pre-loaded — you must configure everything below from scratch:**
- VRF definitions (CUSTOMER-A and CUSTOMER-B)
- IPv6 address families on VRFs
- Sub-interface encapsulation and VRF assignments
- VRF interface IP addresses
- OSPF underlay (process 1)
- GRE tunnel interface (Tunnel0)
- IKEv2 proposal, policy, keyring, and profile
- IPsec transform-set and profile
- Tunnel protection (GRE-over-IPsec)
- OSPF overlay (process 2)
- Per-VRF static routes
- Inter-VRF route leaking
- Loopback interfaces for CUSTOMER-B and R4 test prefix

**PC1 and PC2** — configure manually in the EVE-NG console:
```
PC1> ip 192.168.1.10/24 192.168.1.1
PC2> ip 192.168.2.10/24 192.168.2.1
```

---

## 5. Lab Challenge: Full Protocol Mastery

> This is a capstone lab. No step-by-step guidance is provided.
> Configure the complete VRF and Tunneling solution from scratch — IP addressing is pre-configured; everything else is yours to build.
> All blueprint bullets for this chapter must be addressed.

---

### Task 1: VRF Definitions and Dual-Stack Address Families

- Create two VRF instances on R1 and R2: CUSTOMER-A (route distinguisher 65001:100) and CUSTOMER-B (route distinguisher 65001:200).
- On R3, create CUSTOMER-A only (R3 carries VRF-A transit; it does not host CUSTOMER-B).
- Enable both IPv4 and IPv6 address families in each VRF instance.
- On R1 and R2, assign the LAN interface (Gi0/2) to CUSTOMER-A and re-apply the appropriate IPv4 and IPv6 addresses.
- On R1 and R2, create a Loopback1 in CUSTOMER-B representing the customer-B subnet (R1: 172.20.1.1/24, R2: 172.20.2.1/24) with IPv6 addresses (R1: 2001:db8:b1::1/64, R2: 2001:db8:b2::1/64).
- On R1 and R2, create a Loopback2 in CUSTOMER-B to demonstrate overlapping address space (R1: 192.168.1.100/24, R2: 192.168.2.100/24) — these intentionally overlap with the CUSTOMER-A LAN subnets, confirming VRF isolation.

**Verification:** `show vrf` must list CUSTOMER-A and CUSTOMER-B on R1/R2, CUSTOMER-A only on R3. `show ip route vrf CUSTOMER-A` must show the connected LAN prefix. `show vrf detail` must show both IPv4 and IPv6 address families.

---

### Task 2: VRF-Lite Transit and Per-VRF Routing

- On R1, R3, and R2, create 802.1Q sub-interfaces on Gi0/0 (VLAN 100) for CUSTOMER-A transit. Assign each sub-interface to VRF CUSTOMER-A with the correct IPv4 and IPv6 addresses from the addressing table.
- On R3, configure a second sub-interface on Gi0/1 (VLAN 100) for the R3-R2 CUSTOMER-A segment.
- Configure per-VRF static routes so CUSTOMER-A traffic can traverse R3: R1 must know the R2 LAN, R2 must know the R1 LAN, and R3 must know both LANs (with next-hops pointing toward the appropriate transit sub-interface neighbors).
- Add IPv6 static routes in VRF CUSTOMER-A matching the IPv4 static routes above.

**Verification:** `show ip route vrf CUSTOMER-A` on R1, R2, and R3 must each show the remote LAN prefix as a static route. `ping vrf CUSTOMER-A 192.168.2.1 source GigabitEthernet0/2` from R1 must succeed. `PC1> ping 192.168.2.10` must succeed end-to-end.

---

### Task 3: OSPF Underlay and GRE Overlay Tunnel

- Configure OSPF process 1 on all four routers (R1, R2, R3, R4) as the underlay IGP. Advertise loopback0 addresses and all global-table WAN links. Do NOT advertise VRF interfaces into OSPF process 1.
- Verify that all four loopbacks (1.1.1.1, 2.2.2.2, 3.3.3.3, 4.4.4.4) are reachable before creating the tunnel.
- On R1 and R4, create Tunnel0 with loopback0 as tunnel source and the remote loopback0 as tunnel destination. Use the tunnel addressing (R1: 172.16.14.1/30, R4: 172.16.14.2/30) with IPv6 (R1: 2001:db8:14::1/64, R4: 2001:db8:14::2/64). Set the interface as point-to-point for OSPF.
- Set appropriate MTU and MSS values on Tunnel0 to prevent fragmentation.
- Configure OSPF process 2 on R1 and R4 to advertise the tunnel subnet and R4's Loopback1 (10.4.4.4/32) over the GRE overlay.

**Verification:** `show interface Tunnel0` must show line protocol UP/UP and `Tunnel protocol/transport GRE/IP`. `show ip ospf 2 neighbor` must show R4 (from R1) in FULL state. `show ip route 10.4.4.4` on R1 must show an OSPF entry learned via Tunnel0.

---

### Task 4: IPsec Protection — GRE-over-IPsec

- On R1 and R4, configure the IKEv2 four-tier hierarchy: proposal (AES-256-CBC, SHA-256, DH group 14), policy, keyring (peer R4 at 4.4.4.4 / peer R1 at 1.1.1.1, PSK: LAB-PSK-2026), and profile (match remote identity by /32 host address, PSK authentication on both sides).
- Configure an IPsec transform-set using ESP-AES-256 and ESP-SHA256-HMAC in tunnel mode.
- Create an IPsec profile that binds the transform-set and IKEv2 profile.
- Apply the IPsec profile to Tunnel0 on both R1 and R4 using tunnel protection. The GRE tunnel already exists — adding protection will trigger IKEv2 negotiation automatically.

**Verification:** `show crypto ikev2 sa` must show one established SA with remote peer 4.4.4.4 (from R1). `show crypto ipsec sa` must show non-zero `#pkts encrypt`/`#pkts decrypt` counters after `ping 172.16.14.2 source Tunnel0` from R1. `show interface Tunnel0` must still show UP/UP with `Tunnel protocol/transport GRE/IP`.

---

### Task 5: VRF Isolation and Inter-VRF Route Leaking

- On R1 and R2, add Loopback2 to CUSTOMER-B (overlapping IPs 192.168.1.100/24 and 192.168.2.100/24 respectively) and confirm that `show ip route vrf CUSTOMER-B` shows the overlapping prefix without conflict.
- Configure inter-VRF route leaking on R1 using /32 host static routes: allow CUSTOMER-B to reach the specific host 192.168.1.1 (R1's CUSTOMER-A LAN gateway) and allow CUSTOMER-A to reach the specific host 172.20.1.1 (R1's CUSTOMER-B Loopback1). The /32 host routes must be more specific than the overlapping /24 connected routes.
- Verify that CUSTOMER-A and CUSTOMER-B remain isolated for all other prefixes (no default leaking).

**Verification:** `show ip route vrf CUSTOMER-B` on R1 must show Loopback2 (192.168.1.100/24) connected AND a /32 host route for 172.20.1.1 pointing toward Loopback1. `show ip route vrf CUSTOMER-A` must show a /32 host route for 172.20.1.1. `ping vrf CUSTOMER-B 192.168.1.1` from R1 must succeed (leaking). `ping vrf CUSTOMER-B 192.168.2.1` must fail (no leaking to R2 CUSTOMER-A).

---

### Task 6: End-to-End Verification and Overlay vs. Underlay Comparison

- From R1, verify that ping to 10.4.4.4 (R4 Loopback1) succeeds and is routed via Tunnel0 (overlay), not via the underlay path.
- Confirm overlay vs. underlay separation: run `traceroute 4.4.4.4` (underlay — shows R3 as a hop) and `traceroute 10.4.4.4` (overlay — shows Tunnel0, no intermediate hops visible at IP level).
- Verify IPsec encryption is active: after `ping 172.16.14.2 source Tunnel0`, check `show crypto ipsec sa` for non-zero `#pkts encrypt` and `#pkts decrypt`.
- Verify dual-stack over the tunnel: `ping ipv6 2001:db8:14::2 source 2001:db8:14::1` from R1 must succeed.
- Confirm R3 sees only encrypted outer packets, not the GRE inner payload: run `debug ip packet` briefly on R3 and confirm all traffic on 10.0.13.0/30 has source/destination matching loopback addresses (tunnel endpoints), not tunnel IPs.

**Verification:** `ping 172.16.14.2 source Tunnel0` from R1 succeeds (populates IPsec SA counters). `show ip route 10.4.4.4` shows next-hop via Tunnel0. `show crypto ipsec sa` shows non-zero encrypt/decrypt counters. `show crypto ikev2 sa` shows established SA.

---

## 6. Verification & Analysis

### Task 1: VRF Definitions

```
R1# show vrf
  Name                             Default RD            Protocols   Interfaces
  CUSTOMER-A                       65001:100             ipv4,ipv6   Gi0/0.100  ! ← rd must match
  CUSTOMER-B                       65001:200             ipv4,ipv6   Lo1 Lo2    ! ← both AFs present

R1# show ip route vrf CUSTOMER-A
Routing Table: CUSTOMER-A
C    192.168.1.0/24 is directly connected, GigabitEthernet0/2   ! ← LAN connected in VRF

R1# show ipv6 route vrf CUSTOMER-A
IPv6 Routing Table - VRF "CUSTOMER-A"
C    2001:DB8:A1::/64 [0/0]
     via GigabitEthernet0/2, directly connected                 ! ← IPv6 LAN in VRF
```

### Task 2: VRF-Lite Transit and Routing

```
R3# show ip route vrf CUSTOMER-A
Routing Table: CUSTOMER-A
C    172.16.13.0/30 is directly connected, GigabitEthernet0/0.100   ! ← R1 transit
C    172.16.23.0/30 is directly connected, GigabitEthernet0/1.100   ! ← R2 transit
S    192.168.1.0/24 [1/0] via 172.16.13.1                           ! ← route to R1 LAN
S    192.168.2.0/24 [1/0] via 172.16.23.1                           ! ← route to R2 LAN

R1# ping vrf CUSTOMER-A 192.168.2.1 source GigabitEthernet0/2
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 192.168.2.1, timeout is 2 seconds:
!!!!!                                                            ! ← 5/5 success
Success rate is 100 percent (5/5), round-trip min/avg/max = 1/2/4 ms

PC1> ping 192.168.2.10
84 bytes from 192.168.2.10 icmp_seq=1 ttl=62 time=3.842 ms
84 bytes from 192.168.2.10 icmp_seq=2 ttl=62 time=4.107 ms         ! ← end-to-end PC ping works
```

### Task 3: OSPF Underlay and GRE Tunnel

```
R1# show ip ospf neighbor
Neighbor ID     Pri   State           Dead Time   Address         Interface
2.2.2.2           1   FULL/BDR        00:00:33    10.0.12.2       Gi0/1
3.3.3.3           1   FULL/DR         00:00:37    10.0.13.2       Gi0/0     ! ← underlay neighbors

R1# show ip ospf 2 neighbor
Neighbor ID     Pri   State           Dead Time   Address         Interface
4.4.4.4           0   FULL/  -        00:00:35    172.16.14.2     Tunnel0   ! ← overlay neighbor (P2P)

R1# show interface Tunnel0
Tunnel0 is up, line protocol is up
  ...
  Tunnel source 1.1.1.1 (Loopback0), destination 4.4.4.4
  Tunnel protocol/transport GRE/IP                               ! ← must show GRE/IP (not IPSEC/IP)
  ...

R1# show ip route 10.4.4.4
Routing entry for 10.4.4.4/32
  Known via "ospf 2", distance 110, metric 1001
  * 172.16.14.2, from 4.4.4.4, via Tunnel0                      ! ← learned via overlay
```

### Task 4: IPsec Protection

```
R1# show crypto ikev2 sa
IPv4 Crypto IKEv2  SA

Tunnel-id Local                 Remote                fvrf/ivrf            Status
1         1.1.1.1/500           4.4.4.4/500           none/none            READY    ! ← SA established

R1# show crypto ipsec sa
interface: Tunnel0
    Crypto map tag: Tunnel0-head-0, local addr 1.1.1.1

   protected vrf: (none)
   local  ident (addr/mask/prot/port): (0.0.0.0/0.0.0.0/47/0)   ! ← GRE (protocol 47)
   remote ident (addr/mask/prot/port): (0.0.0.0/0.0.0.0/47/0)

    #pkts encaps: 48, #pkts encrypt: 48, #pkts digest: 48        ! ← non-zero after ping source Tunnel0
    #pkts decaps: 48, #pkts decrypt: 48, #pkts verify: 48        ! ← reply returns through Tunnel0
    #pkts compressed: 0, #pkts decompressed: 0
    #pkts not compressed: 0, #pkts compr. failed: 0
    #pkts not decompressed: 0, #pkts decompress failed: 0
    #send errors 0, #recv errors 0
```

### Task 5: VRF Isolation

```
R1# show ip route vrf CUSTOMER-B
Routing Table: CUSTOMER-B
C    172.20.1.0/24 is directly connected, Loopback1              ! ← CUSTOMER-B LAN
C    192.168.1.0/24 is directly connected, Loopback2             ! ← overlapping prefix (no conflict)
S    192.168.1.1/32 [1/0] via GigabitEthernet0/2, 192.168.1.1   ! ← inter-VRF leak (/32 host)

R1# show ip route vrf CUSTOMER-A | include 172.20
S    172.20.1.1/32 [1/0] via Loopback1, 172.20.1.1              ! ← /32 leak into CUSTOMER-A

R1# ping vrf CUSTOMER-B 192.168.1.1
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 192.168.1.1, timeout is 2 seconds:
!!!!!                                                            ! ← inter-VRF leak working
Success rate is 100 percent (5/5)
```

### Task 6: End-to-End and Overlay vs. Underlay

```
R1# traceroute 4.4.4.4
Type escape sequence to abort.
Tracing the route to 4.4.4.4
  1 10.0.13.2 4 msec                                             ! ← R3 underlay hop visible
  2 10.0.34.2 4 msec                                             ! ← R4 via R3

R1# traceroute 10.4.4.4
Type escape sequence to abort.
Tracing the route to 10.4.4.4
  1 172.16.14.2 8 msec                                           ! ← R4 tunnel IP, R3 invisible
```

---

## 7. Verification Cheatsheet

### VRF Configuration

```
vrf definition <NAME>
 rd <ASN:NN>
 address-family ipv4
 exit-address-family
 address-family ipv6
 exit-address-family
!
interface <INTF>
 vrf forwarding <NAME>
 ip address ...        ! re-apply after vrf forwarding
 ipv6 address ...
```

| Command | Purpose |
|---------|---------|
| `show vrf` | List all VRFs with RD and assigned interfaces |
| `show ip route vrf <NAME>` | Show VRF-specific IPv4 routing table |
| `show ipv6 route vrf <NAME>` | Show VRF-specific IPv6 routing table |
| `ping vrf <NAME> <DST>` | Send ping within a specific VRF |
| `show vrf detail` | Show VRF address families and all member interfaces |

> **Exam tip:** `vrf forwarding` on an interface clears all IP addresses. Always re-apply IPv4 and IPv6 addresses immediately after the VRF assignment.

### VRF-Lite Sub-Interface Transit

```
interface GigabitEthernet0/0.100
 encapsulation dot1Q 100
 vrf forwarding CUSTOMER-A
 ip address <TRANSIT-IP> <MASK>
 ipv6 address <TRANSIT-IPv6>/64
!
ip route vrf CUSTOMER-A <REMOTE-LAN> <MASK> <NEXT-HOP>
ipv6 route vrf CUSTOMER-A <REMOTE-LAN-v6>/64 <NEXT-HOP-v6>
```

| Command | Purpose |
|---------|---------|
| `show interfaces GigabitEthernet0/0.100` | Verify sub-interface line protocol |
| `show ip route vrf CUSTOMER-A` | Verify per-VRF routing including static routes |
| `traceroute vrf CUSTOMER-A <DST>` | Trace path within a VRF |

### GRE Tunnel Configuration

```
interface Tunnel0
 ip address <TUN-IP> <MASK>
 ipv6 address <TUN-IPv6>/64
 ip mtu 1400
 ip tcp adjust-mss 1360
 tunnel source Loopback0
 tunnel destination <REMOTE-LOOPBACK>
 tunnel mode gre ip
 ip ospf network point-to-point
 no shutdown
```

| Command | Purpose |
|---------|---------|
| `show interface Tunnel0` | Verify tunnel UP/UP and protocol/transport type |
| `show ip ospf 2 neighbor` | Verify OSPF overlay adjacency over tunnel |
| `traceroute <overlay-dst>` | Confirm R3 is invisible (tunnel compresses hops) |

> **Exam tip:** A GRE tunnel can be up while `tunnel mode ipsec ipv4` is up only with an active SA. `tunnel mode gre ip` + `tunnel protection` keeps the GRE type visible even with IPsec applied.

### IKEv2 and IPsec Configuration

```
crypto ikev2 proposal IKEv2-PROP
 encryption aes-cbc-256
 integrity sha256
 group 14
!
crypto ikev2 policy IKEv2-POL
 proposal IKEv2-PROP
!
crypto ikev2 keyring IKEv2-KEYRING
 peer <NAME>
  address <PEER-IP>
  pre-shared-key <PSK>
!
crypto ikev2 profile IKEv2-PROFILE
 match identity remote address <PEER-IP> 255.255.255.255
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
interface Tunnel0
 tunnel protection ipsec profile IPSEC-PROFILE
```

| Command | Purpose |
|---------|---------|
| `show crypto ikev2 sa` | Verify IKEv2 SA is READY (not DELETED) |
| `show crypto ikev2 sa detail` | Show negotiated parameters and lifetime |
| `show crypto ipsec sa` | Show SA pair and packet counters |
| `show crypto session` | Quick summary of all VPN sessions |
| `debug crypto ikev2` | Live IKEv2 negotiation (use carefully) |

> **Exam tip:** `#pkts encrypt` increments on the sender; `#pkts decrypt` increments on the receiver. Source pings from the tunnel interface (not Loopback0) to ensure the reply travels back through the tunnel and populates decrypt counters.

### Verification Commands

| Command | What to Look For |
|---------|-----------------|
| `show vrf` | RD assigned, interfaces listed |
| `show ip route vrf CUSTOMER-A` | Remote LAN as static route (S) |
| `show interface Tunnel0` | UP/UP, `Tunnel protocol/transport GRE/IP` |
| `show ip ospf 2 neighbor` | R4 in FULL state on Tunnel0 |
| `show crypto ikev2 sa` | Status = READY |
| `show crypto ipsec sa` | Non-zero encrypt/decrypt counters |
| `ping vrf CUSTOMER-A 192.168.2.10 source Gi0/2` | PC2 reachable via VRF |
| `ping 10.4.4.4 source Loopback0` | R4 overlay prefix reachable |

### Common VRF and Tunnel Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| `show vrf` shows interface but no IP | Forgot to re-apply IP after `vrf forwarding` |
| CUSTOMER-A static route missing on R3 | Static route not added to VRF, or wrong next-hop |
| Tunnel0 protocol DOWN | Underlay path to tunnel destination unreachable (OSPF 1 not configured) |
| `show crypto ikev2 sa` shows DELETED | PSK mismatch or proposal mismatch between peers |
| `#pkts decrypt = 0` after ping | Ping sourced from Loopback0 — reply routes via underlay; use `source Tunnel0` instead |
| GRE tunnel UP but no OSPF neighbor | Missing `ip ospf network point-to-point` or OSPF process not on tunnel subnet |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Task 1–2: VRF Definitions and VRF-Lite Transit

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1 — VRF + dual-stack + sub-interface transit + LAN in VRF
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
interface Loopback1
 vrf forwarding CUSTOMER-B
 ip address 172.20.1.1 255.255.255.0
 ipv6 address 2001:db8:b1::1/64
!
interface Loopback2
 vrf forwarding CUSTOMER-B
 ip address 192.168.1.100 255.255.255.0
!
interface GigabitEthernet0/0.100
 encapsulation dot1Q 100
 vrf forwarding CUSTOMER-A
 ip address 172.16.13.1 255.255.255.252
 ipv6 address 2001:db8:ca13::1/64
!
interface GigabitEthernet0/2
 vrf forwarding CUSTOMER-A
 ip address 192.168.1.1 255.255.255.0
 ipv6 address 2001:db8:a1::1/64
 no shutdown
!
ip route vrf CUSTOMER-A 192.168.2.0 255.255.255.0 172.16.13.2
ipv6 route vrf CUSTOMER-A 2001:db8:a2::/64 2001:db8:ca13::2
ip route vrf CUSTOMER-B 192.168.1.1 255.255.255.255 GigabitEthernet0/2 192.168.1.1
ip route vrf CUSTOMER-A 172.20.1.1 255.255.255.255 Loopback1 172.20.1.1
```
</details>

<details>
<summary>Click to view R2 Configuration</summary>

```bash
! R2 — mirrors R1 for CUSTOMER-A; CUSTOMER-B isolation demo
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
interface Loopback1
 vrf forwarding CUSTOMER-B
 ip address 172.20.2.1 255.255.255.0
 ipv6 address 2001:db8:b2::1/64
!
interface Loopback2
 vrf forwarding CUSTOMER-B
 ip address 192.168.2.100 255.255.255.0
!
interface GigabitEthernet0/0.100
 encapsulation dot1Q 100
 vrf forwarding CUSTOMER-A
 ip address 172.16.23.1 255.255.255.252
 ipv6 address 2001:db8:ca23::1/64
!
interface GigabitEthernet0/2
 vrf forwarding CUSTOMER-A
 ip address 192.168.2.1 255.255.255.0
 ipv6 address 2001:db8:a2::1/64
 no shutdown
!
ip route vrf CUSTOMER-A 192.168.1.0 255.255.255.0 172.16.23.2
ipv6 route vrf CUSTOMER-A 2001:db8:a1::/64 2001:db8:ca23::2
```
</details>

<details>
<summary>Click to view R3 Configuration</summary>

```bash
! R3 — VRF-Lite transit only; no CUSTOMER-B
vrf definition CUSTOMER-A
 rd 65001:100
 address-family ipv4
 exit-address-family
 address-family ipv6
 exit-address-family
!
interface GigabitEthernet0/0.100
 encapsulation dot1Q 100
 vrf forwarding CUSTOMER-A
 ip address 172.16.13.2 255.255.255.252
 ipv6 address 2001:db8:ca13::2/64
!
interface GigabitEthernet0/1.100
 encapsulation dot1Q 100
 vrf forwarding CUSTOMER-A
 ip address 172.16.23.2 255.255.255.252
 ipv6 address 2001:db8:ca23::2/64
!
ip route vrf CUSTOMER-A 192.168.1.0 255.255.255.0 172.16.13.1
ip route vrf CUSTOMER-A 192.168.2.0 255.255.255.0 172.16.23.1
ipv6 route vrf CUSTOMER-A 2001:db8:a1::/64 2001:db8:ca13::1
ipv6 route vrf CUSTOMER-A 2001:db8:a2::/64 2001:db8:ca23::1
```
</details>

### Task 3–4: OSPF, GRE Tunnel, and IPsec

<details>
<summary>Click to view R1 Full Solution Config</summary>

```bash
! R1 — OSPF underlay + GRE-over-IPsec Tunnel0
router ospf 1
 router-id 1.1.1.1
 network 1.1.1.1 0.0.0.0 area 0
 network 10.0.13.0 0.0.0.3 area 0
 network 10.0.12.0 0.0.0.3 area 0
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
interface Tunnel0
 description R1-R4 GRE-over-IPsec
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
router ospf 2
 router-id 1.1.1.1
 network 172.16.14.0 0.0.0.3 area 0
```
</details>

<details>
<summary>Click to view R4 Full Solution Config</summary>

```bash
! R4 — mirror of R1 IKEv2/IPsec + OSPF overlay
router ospf 1
 router-id 4.4.4.4
 network 4.4.4.4 0.0.0.0 area 0
 network 10.0.34.0 0.0.0.3 area 0
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
interface Loopback1
 ip address 10.4.4.4 255.255.255.255
!
interface Tunnel0
 description R4-R1 GRE-over-IPsec
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
router ospf 2
 router-id 4.4.4.4
 network 172.16.14.0 0.0.0.3 area 0
 network 10.4.4.4 0.0.0.0 area 0
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show vrf
show ip route vrf CUSTOMER-A
show ip ospf neighbor
show ip ospf 2 neighbor
show interface Tunnel0
show crypto ikev2 sa
show crypto ipsec sa
ping 10.4.4.4 source Loopback0
ping 172.16.14.2 source Tunnel0
traceroute 4.4.4.4
traceroute 10.4.4.4
```
</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. Inject the fault first, then
diagnose and fix using only show commands.

### Workflow

```bash
python3 setup_lab.py --host <eve-ng-ip>                           # load initial config
python3 scripts/fault-injection/apply_solution.py --host <ip>     # restore to known-good
python3 scripts/fault-injection/inject_scenario_01.py --host <ip> # Ticket 1
python3 scripts/fault-injection/apply_solution.py --host <ip>     # restore between tickets
python3 scripts/fault-injection/inject_scenario_02.py --host <ip> # Ticket 2
python3 scripts/fault-injection/apply_solution.py --host <ip>     # restore
python3 scripts/fault-injection/inject_scenario_03.py --host <ip> # Ticket 3
```

---

### Ticket 1 — Encrypted Tunnel Drops — R4 Remote Prefix Unreachable

R1's operations team reports that the encrypted overlay to the remote site is non-functional. `ping 10.4.4.4` from R1 was working yesterday; today it fails completely. OSPF process 1 (underlay) neighbors are intact.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>`

**Success criteria:** `ping 10.4.4.4 source Loopback0` from R1 succeeds. `show crypto ikev2 sa` shows Status = READY.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Confirm OSPF 1 underlay is intact — `show ip ospf neighbor` should show R2 and R3 as neighbors.
2. Ping the tunnel destination via underlay: `ping 4.4.4.4 source Loopback0`. If this fails, the underlay is broken (not this ticket). If it succeeds, the underlay is healthy.
3. Check IKEv2 SA: `show crypto ikev2 sa`. If the status shows DELETED or no SA exists, IKEv2 negotiation failed.
4. Check IKEv2 error counters: `show crypto ikev2 stats`. Look for authentication failures.
5. Narrow to PSK: `show running-config | section ikev2 keyring`. Compare the PSK value on R1 and R4. A mismatch causes AUTH_FAILED at IKEv2 Phase 1.
6. On R4: `show running-config | section ikev2 keyring`. Confirm the PSK matches.
</details>

<details>
<summary>Click to view Fix</summary>

The pre-shared key in R1's IKEv2 keyring was changed to an incorrect value.

```bash
R1(config)# crypto ikev2 keyring IKEv2-KEYRING
R1(config-ikev2-keyring)# peer R4
R1(config-ikev2-keyring-peer)# pre-shared-key LAB-PSK-2026
```

After correction, IKEv2 renegotiates automatically when traffic is generated. Verify:
```bash
R1# ping 172.16.14.2 source Tunnel0
R1# show crypto ikev2 sa
```
</details>

---

### Ticket 2 — PC1 and PC2 Cannot Communicate — VRF Path Broken

A network change was applied overnight. PC1 (192.168.1.10) can no longer reach PC2 (192.168.2.10). The OSPF underlay and the encrypted tunnel are both operational. The VRF-Lite transit through R3 appears to be affected.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py --host <eve-ng-ip>`

**Success criteria:** `PC1> ping 192.168.2.10` succeeds. `show ip route vrf CUSTOMER-A` on R3 shows static routes to both LANs.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Confirm the global table is unaffected: `ping 2.2.2.2 source Loopback0` from R1 should succeed (OSPF underlay).
2. Test the VRF path: `ping vrf CUSTOMER-A 192.168.2.1 source GigabitEthernet0/2` from R1. If this fails, the VRF routing is broken.
3. Check R1's VRF routing table: `show ip route vrf CUSTOMER-A`. Verify a static route exists for 192.168.2.0/24. If it exists, the problem is on R3.
4. Check R3's VRF routing table: `show ip route vrf CUSTOMER-A`. If static routes to 192.168.1.0/24 and 192.168.2.0/24 are missing, R3 cannot forward VRF-A traffic.
5. Check R3's running config: `show running-config | section ip route vrf`. If the static routes are absent, they were removed.
</details>

<details>
<summary>Click to view Fix</summary>

The static routes for VRF CUSTOMER-A were removed from R3, breaking bidirectional VRF-Lite transit.

```bash
R3(config)# ip route vrf CUSTOMER-A 192.168.1.0 255.255.255.0 172.16.13.1
R3(config)# ip route vrf CUSTOMER-A 192.168.2.0 255.255.255.0 172.16.23.1
R3(config)# ipv6 route vrf CUSTOMER-A 2001:db8:a1::/64 2001:db8:ca13::1
R3(config)# ipv6 route vrf CUSTOMER-A 2001:db8:a2::/64 2001:db8:ca23::1
```

Verify:
```bash
R3# show ip route vrf CUSTOMER-A
R1# ping vrf CUSTOMER-A 192.168.2.1 source GigabitEthernet0/2
PC1> ping 192.168.2.10
```
</details>

---

### Ticket 3 — Tunnel Appears Up but Traffic Is Not Encrypted

A compliance audit flag was raised: the overlay tunnel to R4 shows UP in the routing table and OSPF adjacency is FULL, but the security team says no IPsec SAs are active. Traffic is flowing in cleartext.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py --host <eve-ng-ip>`

**Success criteria:** `show crypto ipsec sa` shows non-zero `#pkts encrypt`/`#pkts decrypt`. `show interface Tunnel0` still shows `Tunnel protocol/transport GRE/IP`.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Confirm OSPF 2 adjacency exists: `show ip ospf 2 neighbor` — R4 should be FULL. If OSPF is FULL, the GRE layer is working.
2. Check if IPsec SA exists: `show crypto ipsec sa`. If there are no SAs (no protected/encrypt counters), IPsec is not engaged.
3. Check IKEv2 SA: `show crypto ikev2 sa`. No SA entry confirms IKEv2 was not triggered.
4. Check Tunnel0 protection: `show running-config interface Tunnel0`. Look for `tunnel protection ipsec profile IPSEC-PROFILE`. If this line is missing, the tunnel has no IPsec binding.
5. Confirm the IPsec profile and IKEv2 hierarchy exist: `show crypto ikev2 profile` and `show crypto ipsec profile`. If the objects exist but are not applied, the tunnel is simply unprotected.
</details>

<details>
<summary>Click to view Fix</summary>

The `tunnel protection ipsec profile IPSEC-PROFILE` statement was removed from Tunnel0 on R1. The GRE tunnel continued to function without encryption.

```bash
R1(config)# interface Tunnel0
R1(config-if)# tunnel protection ipsec profile IPSEC-PROFILE
```

Adding the protection line immediately triggers IKEv2 negotiation. Verify:
```bash
R1# show crypto ikev2 sa
R1# ping 172.16.14.2 source Tunnel0
R1# show crypto ipsec sa
```
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] VRF CUSTOMER-A and CUSTOMER-B defined with IPv4 + IPv6 address families on R1 and R2
- [ ] VRF CUSTOMER-A defined on R3 (no CUSTOMER-B)
- [ ] LAN interfaces (Gi0/2) assigned to CUSTOMER-A with correct IPs on R1 and R2
- [ ] Loopback1 in CUSTOMER-B on R1 and R2 (172.20.x.1/24 + IPv6)
- [ ] Loopback2 in CUSTOMER-B with overlapping addresses (192.168.x.100/24)
- [ ] Sub-interfaces Gi0/0.100 (VLAN 100) on R1, R3, R2 — VRF CUSTOMER-A with correct IPs
- [ ] Gi0/1.100 on R3 for R3-R2 CUSTOMER-A transit segment
- [ ] Per-VRF static routes on R1, R2, R3 for CUSTOMER-A LAN reachability (IPv4 + IPv6)
- [ ] Inter-VRF leaking on R1: /32 host routes for 192.168.1.1 into CUSTOMER-B and 172.20.1.1 into CUSTOMER-A
- [ ] OSPF process 1 on all four routers — loopbacks + WAN links (global table only)
- [ ] All four loopbacks mutually reachable before tunnel creation
- [ ] Tunnel0 created on R1 and R4 (GRE, Loopback0 source, remote Loopback0 dest)
- [ ] MTU 1400 and MSS 1360 set on Tunnel0
- [ ] OSPF process 2 on R1 and R4 — tunnel subnet + R4 Loopback1
- [ ] IKEv2 hierarchy on R1 and R4 (proposal, policy, keyring PSK LAB-PSK-2026, profile)
- [ ] IPsec transform-set and profile on R1 and R4
- [ ] Tunnel protection applied to Tunnel0 on both R1 and R4
- [ ] `show crypto ikev2 sa` shows READY on both R1 and R4
- [ ] `show crypto ipsec sa` shows non-zero encrypt/decrypt counters
- [ ] PC1 and PC2 configured in VPCS
- [ ] `PC1> ping 192.168.2.10` succeeds end-to-end via VRF
- [ ] `ping 10.4.4.4 source Loopback0` from R1 succeeds via overlay

### Troubleshooting

- [ ] Ticket 1 diagnosed and fixed (IKEv2 authentication failure)
- [ ] Ticket 2 diagnosed and fixed (VRF CUSTOMER-A transit broken on R3)
- [ ] Ticket 3 diagnosed and fixed (IPsec protection missing on Tunnel0)
