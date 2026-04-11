# VRF and Tunneling — Lab Specification

## Exam Reference
- **Exam:** Implementing Cisco Enterprise Network Core Technologies v1.2 (350-401)
- **Blueprint Bullets:**
  - 2.2: Configure and verify data path virtualization technologies
  - 2.2.a: VRF
  - 2.2.b: GRE and IPsec tunneling

## Topology Summary

Four IOSv routers simulating a multi-site enterprise with VRF isolation and tunnel overlays.
R1 and R2 are branch/site routers requiring VRF segmentation. R3 is a shared WAN/transport
router (SP core simulation). R4 is a remote site router introduced in lab-02 for IPsec
tunneling. OSPF runs as the underlay IGP on global routing table links. **Dual-stack
(IPv4 + IPv6)** from lab-01 onward — VRF with IPv6 address family, IPv6 over GRE/IPsec.
Two VPC end-hosts (PC1 on R1, PC2 on R2). Total: 6 nodes (4 routers + 2 VPCs).

## Lab Progression

| # | Folder | Title | Difficulty | Time | Type | Blueprint Refs | Devices |
|---|--------|-------|-----------|------|------|----------------|---------|
| 00 | lab-00-vrf-lite | VRF-Lite Routing Table Isolation | Foundation | 60m | progressive | 2.2, 2.2.a | R1, R2, R3, PC1, PC2 |
| 01 | lab-01-vrf-dual-stack | VRF with Dual-Stack and Inter-VRF Routing | Intermediate | 75m | progressive | 2.2, 2.2.a | R1, R2, R3, PC1, PC2 |
| 02 | lab-02-gre-tunnels | GRE Tunneling Over a Shared Transport | Intermediate | 75m | progressive | 2.2, 2.2.b | R1, R2, R3, R4, PC1, PC2 |
| 03 | lab-03-ipsec-and-gre-over-ipsec | IPsec Tunnels and GRE over IPsec | Advanced | 90m | progressive | 2.2, 2.2.b | R1, R2, R3, R4, PC1, PC2 |
| 04 | lab-04-capstone-config | VRF and Tunneling Full Mastery — Capstone I | Advanced | 120m | capstone_i | all | R1, R2, R3, R4, PC1, PC2 |
| 05 | lab-05-capstone-troubleshoot | VRF and Tunneling Comprehensive Troubleshooting — Capstone II | Advanced | 120m | capstone_ii | all | R1, R2, R3, R4, PC1, PC2 |

## Blueprint Coverage Matrix

| Blueprint Bullet | Description | Covered In |
|-----------------|-------------|------------|
| 2.2 | Configure and verify data path virtualization technologies | lab-00, lab-01, lab-02, lab-03, lab-04, lab-05 |
| 2.2.a | VRF | lab-00, lab-01, lab-04, lab-05 |
| 2.2.b | GRE and IPsec tunneling | lab-02, lab-03, lab-04, lab-05 |

## Design Decisions

- **6 labs instead of estimated 5:** VRF and tunneling are distinct skill sets that each need proper progressive buildup. VRF-Lite (lab-00) and VRF dual-stack (lab-01) form one progression; GRE (lab-02) and IPsec/GRE-over-IPsec (lab-03) form another. Both converge in the capstones. This +1 deviation keeps each lab focused.
- **VRF before tunneling:** VRF-Lite is conceptually simpler (routing table isolation on a single platform) and provides a foundation — GRE tunnels can later carry VRF traffic, combining both skills.
- **R3 as shared transport:** R3 simulates a service provider or shared WAN where multiple customers (VRFs) transit the same physical infrastructure. This makes VRF isolation tangible — without a shared router, VRF is just extra configuration with no visible benefit.
- **R4 introduced in lab-02:** GRE and IPsec tunnels need two endpoints. R1-to-R4 tunnels traverse R3 (transport), making the overlay/underlay distinction clear. R4 is not needed for VRF-only labs.
- **GRE before IPsec:** GRE is simpler (no crypto), supports multicast/broadcast, and establishes the tunnel interface concept. IPsec adds encryption complexity. GRE-over-IPsec combines both — GRE provides the multiprotocol tunnel, IPsec provides confidentiality.
- **Dual-stack from lab-01:** Lab-00 is IPv4-only VRF-Lite. Lab-01 adds IPv6 address families to VRFs and demonstrates VRF-aware IPv6 routing. Lab-02+ carries IPv6 through GRE tunnels.
- **OSPF as underlay IGP:** Global routing table runs OSPF for reachability between tunnel endpoints. VRF routing uses static routes or a separate OSPF/EIGRP instance per VRF.
