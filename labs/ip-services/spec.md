# IP Services — Lab Specification

## Exam Reference
- **Exam:** Implementing Cisco Enterprise Network Core Technologies v1.2 (350-401)
- **Blueprint Bullets:**
  - 1.4: Interpret QoS configurations
  - 3.3.a: Interpret network time protocol configurations such as NTP and PTP
  - 3.3.b: Configure NAT/PAT
  - 3.3.c: Configure first hop redundancy protocols, such as HSRP, VRRP

## Topology Summary

Three IOSv routers (R1/R2 as redundant LAN gateways, R3 as upstream/ISP), one EVE-NG
unmanaged switch (SW-LAN) providing a shared broadcast segment for the LAN, and two VPC
end-hosts (PC1, PC2). R1 and R2 share the LAN segment for HSRP/VRRP virtual gateway
operation. Both uplink to R3, providing redundant paths. OSPF runs as the IGP across all
links. **Dual-stack (IPv4 + IPv6)** from lab-02 onward — HSRPv2 for IPv4, VRRPv3 for IPv6
in later labs. Total: 6 nodes (3 routers + 1 unmanaged switch + 2 VPCs).

## Lab Progression

| # | Folder | Title | Difficulty | Time | Type | Blueprint Refs | Devices |
|---|--------|-------|-----------|------|------|----------------|---------|
| 00 | lab-00-ntp-and-qos | NTP Configuration and QoS Interpretation | Foundation | 60m | progressive | 3.3.a, 1.4 | R1, R2, R3, SW-LAN, PC1, PC2 |
| 01 | lab-01-nat-pat | Static NAT, Dynamic NAT, and PAT | Foundation | 75m | progressive | 3.3.b | R1, R2, R3, SW-LAN, PC1, PC2 |
| 02 | lab-02-hsrp | HSRP — First Hop Redundancy | Intermediate | 75m | progressive | 3.3.c | R1, R2, R3, SW-LAN, PC1, PC2 |
| 03 | lab-03-vrrp-dual-stack | VRRP and Dual-Stack Gateway Redundancy | Intermediate | 75m | progressive | 3.3.c | R1, R2, R3, SW-LAN, PC1, PC2 |
| 04 | lab-04-capstone-config | IP Services Full Mastery — Capstone I | Advanced | 120m | capstone_i | all | R1, R2, R3, SW-LAN, PC1, PC2 |
| 05 | lab-05-capstone-troubleshoot | IP Services Comprehensive Troubleshooting — Capstone II | Advanced | 120m | capstone_ii | all | R1, R2, R3, SW-LAN, PC1, PC2 |

## Blueprint Coverage Matrix

| Blueprint Bullet | Description | Covered In |
|-----------------|-------------|------------|
| 1.4 | Interpret QoS configurations | lab-00, lab-04, lab-05 |
| 3.3.a | Interpret NTP/PTP configurations | lab-00, lab-04, lab-05 |
| 3.3.b | Configure NAT/PAT | lab-01, lab-04, lab-05 |
| 3.3.c | Configure HSRP, VRRP | lab-02, lab-03, lab-04, lab-05 |

## Design Decisions

- **NTP and QoS combined in lab-00:** Both are "interpret" bullets (read and analyze existing config, not build from scratch). Combining them avoids two thin labs. NTP is configured hands-on; QoS is pre-loaded for interpretation exercises.
- **NAT/PAT gets its own lab:** 3.3.b is a "configure" bullet with significant depth — static NAT, dynamic NAT pool, PAT overload. Each requires distinct configuration and verification.
- **HSRP and VRRP in separate labs:** Both are tested independently on the exam. Lab-02 covers HSRPv2 (IPv4), lab-03 adds VRRPv3 (dual-stack IPv4+IPv6). Progressive chain works because VRRP replaces HSRP on the same interfaces (VRRP is a standalone-like lab but the rest of the config carries forward).
- **Shared LAN segment via unmanaged switch:** R1, R2, PC1, PC2 all connect to SW-LAN. This creates a genuine broadcast segment where HSRP/VRRP hellos are visible to all participants — not simulated.
- **R3 as upstream/ISP:** Provides the "outside" interface for NAT and a routing target for FHRP failover testing. Loopback1 on R3 simulates an internet server (203.0.113.0/24 documentation space).
- **OSPF as IGP:** All routers run OSPF for internal routing. OSPF is pre-configured in initial-configs since this topic focuses on IP services, not routing protocol setup.
- **Dual-stack from lab-02:** Labs 00-01 are IPv4 only. Lab-02 introduces IPv6 on the LAN segment for HSRPv2 IPv6 groups, and lab-03 uses VRRPv3 which natively supports both address families.
