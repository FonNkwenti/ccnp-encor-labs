# BGP Routing — Lab Specification

## Exam Reference
- **Exam:** Implementing Cisco Enterprise Network Core Technologies v1.2 (350-401)
- **Blueprint Bullets:**
  - 3.2.c: Configure and verify eBGP between directly connected neighbors (best path selection algorithm and neighbor relationships)

## Topology Summary

Four IOSv routers across three autonomous systems (AS 65001 with R1/R2, AS 65002 with R3,
AS 65003 with R4 optional). R1 and R2 form the enterprise edge with iBGP between them and
OSPF as the IGP. R3 represents an ISP with eBGP peering to both R1 and R2 (dual-homed).
R4 is a remote site in a third AS, introduced in lab-02 for extended path selection. **Dual-stack
(IPv4 + IPv6)** from lab-01 onward — BGP IPv4 and IPv6 address families with separate neighbor
activation. Two VPC end-hosts (PC1 on R1, PC2 on R4). Total: 6 nodes (3 core + 1 optional + 2 VPCs).

## Lab Progression

| # | Folder | Title | Difficulty | Time | Type | Blueprint Refs | Devices |
|---|--------|-------|-----------|------|------|----------------|---------|
| 00 | lab-00-ebgp-peering | eBGP Peering Fundamentals | Foundation | 60m | progressive | 3.2.c | R1, R3, PC1 |
| 01 | lab-01-ibgp-and-dual-stack | iBGP, Dual-Homing, and Dual-Stack | Foundation | 75m | progressive | 3.2.c | R1, R2, R3, PC1 |
| 02 | lab-02-best-path-selection | Best Path Selection and Attributes | Intermediate | 90m | progressive | 3.2.c | R1, R2, R3, R4, PC1, PC2 |
| 03 | lab-03-capstone-config | BGP Full Protocol Mastery — Capstone I | Advanced | 120m | capstone_i | 3.2.c | R1, R2, R3, R4, PC1, PC2 |
| 04 | lab-04-capstone-troubleshoot | BGP Comprehensive Troubleshooting — Capstone II | Advanced | 120m | capstone_ii | 3.2.c | R1, R2, R3, R4, PC1, PC2 |

## Blueprint Coverage Matrix

| Blueprint Bullet | Description | Covered In |
|-----------------|-------------|------------|
| 3.2.c | Configure and verify eBGP — best path selection, neighbor relationships | lab-00, lab-01, lab-02, lab-03, lab-04 |

## Design Decisions

- **Three autonomous systems:** AS 65001 (enterprise with R1/R2), AS 65002 (ISP with R3), AS 65003 (remote site with R4). This provides eBGP peering across AS boundaries while also requiring iBGP within AS 65001 — both are tested on the exam.
- **Dual-homed enterprise edge:** Both R1 and R2 peer eBGP with R3, giving the ISP two entry points into AS 65001. This creates the multi-path scenario needed for best path selection demonstrations.
- **iBGP within AS 65001:** R1 and R2 share BGP routes via iBGP, requiring `next-hop-self` configuration. This teaches a critical eBGP+iBGP interaction even though the blueprint focuses on eBGP.
- **OSPF as IGP within AS 65001:** R1-R2 run OSPF on their internal link so iBGP next-hops are reachable. This leverages the OSPF skills already built. OSPF is pre-configured in initial-configs.
- **R4 optional (introduced lab-02):** Keeps early labs focused on basic eBGP peering. R4 adds a third AS for AS_Path manipulation and MED demonstration.
- **Best path selection in dedicated lab:** Lab-02 focuses entirely on path manipulation — Weight, Local Preference, AS_Path prepending, MED, Origin. Each attribute is exercised in sequence so the student sees how the algorithm evaluates them in order.
- **Dual-stack from lab-01:** Lab-00 is IPv4 only. Lab-01 adds IPv6 addresses and BGP IPv6 unicast address family with separate neighbor activation per AF.
