# Enterprise Network Design — Lab Specification

## Exam Reference
- **Exam:** Implementing Cisco Enterprise Network Core Technologies v1.2 (350-401)
- **Blueprint Bullets:**
  - 1.1: Explain the different design principles used in an enterprise network
  - 1.1.a: High-level enterprise network design such as 2-tier, 3-tier, fabric, and cloud
  - 1.1.b: High availability techniques such as redundancy, FHRP, and SSO
  - 3.2.d: Describe policy-based routing

## Topology Summary

Three IOSv routers (R1/R2/R3) and two VPC end-hosts (PC1, PC2). R1 is a dual-homed edge
router with two ISP links (R2 and R3) for PBR exercises. R2 and R3 simulate upstream
providers with different path characteristics. OSPF runs as the IGP. The same topology
supports both hands-on PBR configuration and design-theory walkthroughs. **IPv4 only** —
design theory and PBR exercises do not require IPv6. Total: 5 nodes (3 routers + 2 VPCs).

## Workbook Format

This topic uses **reference workbook format** for theory-heavy labs (lab-00, lab-01) and
**standard lab format** for the hands-on PBR lab (lab-02). Reference workbooks include
architecture diagrams, show-command interpretation, and quiz-style verification but do NOT
include `setup_lab.py`, `fault-injection/` scripts, or `initial-configs/`/`solutions/`
directories. The capstones blend both formats.

## Lab Progression

| # | Folder | Title | Difficulty | Time | Type | Blueprint Refs | Devices | Format |
|---|--------|-------|-----------|------|------|----------------|---------|--------|
| 00 | lab-00-design-principles | Enterprise Design — 2-Tier, 3-Tier, Fabric, and Cloud | Foundation | 60m | progressive | 1.1, 1.1.a | R1, R2, R3, PC1, PC2 | reference |
| 01 | lab-01-high-availability | High Availability — Redundancy, FHRP, and SSO | Intermediate | 60m | progressive | 1.1, 1.1.b | R1, R2, R3, PC1, PC2 | reference |
| 02 | lab-02-policy-based-routing | Policy-Based Routing Configuration | Intermediate | 75m | progressive | 3.2.d | R1, R2, R3, PC1, PC2 | standard |
| 03 | lab-03-capstone-config | Network Design Full Mastery — Capstone I | Advanced | 120m | capstone_i | all | R1, R2, R3, PC1, PC2 | hybrid |
| 04 | lab-04-capstone-troubleshoot | Network Design Comprehensive Troubleshooting — Capstone II | Advanced | 120m | capstone_ii | all | R1, R2, R3, PC1, PC2 | hybrid |

## Blueprint Coverage Matrix

| Blueprint Bullet | Description | Covered In |
|-----------------|-------------|------------|
| 1.1 | Explain enterprise network design principles | lab-00, lab-01, lab-03, lab-04 |
| 1.1.a | High-level design — 2-tier, 3-tier, fabric, cloud | lab-00, lab-03, lab-04 |
| 1.1.b | HA techniques — redundancy, FHRP, SSO | lab-01, lab-03, lab-04 |
| 3.2.d | Describe policy-based routing | lab-02, lab-03, lab-04 |

## Design Decisions

- **5 labs instead of estimated 4:** Separating design principles (lab-00) from HA (lab-01) gives each topic proper depth. PBR needs its own hands-on lab (lab-02). With 2 capstones = 5. The +1 deviation is justified by the breadth of 1.1 (covers four design models).
- **Reference format for theory labs:** 1.1.a and 1.1.b are "explain" bullets — no configuration to build. Reference workbooks use architecture diagrams, topology walkthroughs, show-command interpretation, and quiz questions instead of hands-on tasks.
- **Standard format for PBR:** 3.2.d is a "describe" bullet but PBR is fully configurable on IOSv. Students create route-maps, match ACLs, set next-hop, and apply to interfaces — genuine hands-on.
- **Dual-homed R1 for PBR:** R1 connects to both R2 and R3, simulating dual ISP. PBR on R1 steers traffic from PC1 via R2 and traffic from PC2 via R3 based on source address. This is the canonical PBR use case.
- **1.1.b HA overlaps with ip-services FHRP:** The ip-services topic covers HSRP/VRRP configuration. This topic covers the design rationale — why you choose FHRP, where to place it, how it fits with SSO/NSF. No duplication of hands-on config.
- **IPv4 only:** Design theory is IP-version agnostic. PBR exercises use IPv4 ACLs and route-maps. No IPv6 complexity needed for these learning objectives.
- **Hybrid capstones:** Capstone I combines PBR configuration with design interpretation questions. Capstone II includes PBR troubleshooting plus design scenario analysis.
