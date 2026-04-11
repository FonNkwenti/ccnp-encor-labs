# Multicast — Lab Specification

## Exam Reference
- **Exam:** Implementing Cisco Enterprise Network Core Technologies v1.2 (350-401)
- **Blueprint Bullets:**
  - 3.3.d: Describe multicast protocols, such as RPF check, PIM SM, IGMP v2/v3, SSM, bidir, and MSDP

## Topology Summary

Four IOSv routers in a triangle-plus-stub layout (R1/R2/R3 core triangle, R4 as second RP
domain for MSDP). R1 serves as the source-side router with PC1 generating multicast traffic.
R3 serves as the receiver-side router with PC2 as a multicast receiver. R2 is the primary
Rendezvous Point (RP) for PIM-SM. R4 is an optional router introduced in lab-02 as a second
RP for MSDP peering. OSPF runs as the unicast IGP across all links (required for RPF).
**IPv4 only** — IPv6 MLD is not in scope for blueprint 3.3.d. Total: 6 nodes (4 routers + 2 VPCs).

## Lab Progression

| # | Folder | Title | Difficulty | Time | Type | Blueprint Refs | Devices |
|---|--------|-------|-----------|------|------|----------------|---------|
| 00 | lab-00-pim-sm-and-igmp | PIM Sparse Mode, IGMP, and RPF Fundamentals | Foundation | 60m | progressive | 3.3.d | R1, R2, R3, PC1, PC2 |
| 01 | lab-01-rp-discovery-and-igmpv3 | RP Discovery Mechanisms and IGMPv3 | Intermediate | 75m | progressive | 3.3.d | R1, R2, R3, PC1, PC2 |
| 02 | lab-02-ssm-bidir-msdp | SSM, Bidirectional PIM, and MSDP | Intermediate | 90m | progressive | 3.3.d | R1, R2, R3, R4, PC1, PC2 |
| 03 | lab-03-capstone-config | Multicast Full Protocol Mastery — Capstone I | Advanced | 120m | capstone_i | all | R1, R2, R3, R4, PC1, PC2 |
| 04 | lab-04-capstone-troubleshoot | Multicast Comprehensive Troubleshooting — Capstone II | Advanced | 120m | capstone_ii | all | R1, R2, R3, R4, PC1, PC2 |

## Blueprint Coverage Matrix

| Blueprint Bullet | Description | Covered In |
|-----------------|-------------|------------|
| 3.3.d | Describe multicast protocols — RPF, PIM SM, IGMP v2/v3, SSM, bidir, MSDP | lab-00, lab-01, lab-02, lab-03, lab-04 |

## Design Decisions

- **5 labs instead of estimated 4:** Blueprint 3.3.d covers six distinct protocol areas (RPF, PIM-SM, IGMP v2/v3, SSM, bidir, MSDP). Three progressive labs allow proper pacing — cramming SSM + bidir + MSDP into a single foundation lab would overwhelm students.
- **Triangle core topology (R1-R2-R3):** The triangle creates two paths from source to receiver, which is essential for demonstrating RPF path selection. Without multiple paths, RPF is just a formality.
- **R2 as primary RP:** Central position makes R2 the natural RP — shared-tree (*,G) traffic flows through it, and students see the difference between the shared tree (via RP) and shortest-path tree (SPT switchover).
- **R4 as second RP domain (optional, lab-02):** MSDP requires two RPs in different PIM domains exchanging source-active (SA) messages. R4 connects to both R2 and R3, forming a second domain boundary.
- **IGMP version progression:** Lab-00 uses IGMPv2 (default on IOSv). Lab-01 upgrades receiver interfaces to IGMPv3 (required for SSM source filtering). Lab-02 uses IGMPv3 with SSM source-specific joins.
- **RP discovery in lab-01:** Lab-00 uses static RP (`ip pim rp-address`) for simplicity. Lab-01 introduces Auto-RP and BSR as dynamic RP discovery mechanisms — both are testable on IOSv.
- **IPv4 only:** The dual-stack policy explicitly excludes this topic — blueprint 3.3.d covers IPv4 multicast protocols only. IPv6 MLD is not in the 350-401 scope.
- **OSPF pre-configured:** All routers run OSPF for unicast routing. PIM depends on the unicast routing table for RPF checks, so OSPF must be operational before any multicast configuration.
