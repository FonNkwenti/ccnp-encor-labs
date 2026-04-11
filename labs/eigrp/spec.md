# EIGRP Routing — Lab Specification

## Exam Reference
- **Exam:** Implementing Cisco Enterprise Network Core Technologies v1.2 (350-401)
- **Blueprint Bullets:**
  - 3.2.a: Compare routing concepts of EIGRP and OSPF (advanced distance vector vs. link state, load balancing, path selection, path operations, metrics, and area types) — EIGRP side

## Topology Summary

Four IOSv routers (R1-R3 core, R4 optional stub) in a triangle-plus-spoke topology. R1 is
the hub router, R2 and R3 are branch routers forming a triangle with R1, and R4 is a stub
router connected to R2 (introduced in lab-02). Two VPC end-hosts (PC1 on R3, PC2 on R4)
for end-to-end verification. **Dual-stack (IPv4 + IPv6)** from lab-01 onward — all router
interfaces carry both IPv4 and IPv6 addresses; EIGRP named mode with IPv6 address family
runs alongside classic/named IPv4. Total: 6 nodes (3 core + 1 optional + 2 VPCs).

## Lab Progression

| # | Folder | Title | Difficulty | Time | Type | Blueprint Refs | Devices |
|---|--------|-------|-----------|------|------|----------------|---------|
| 00 | lab-00-classic-eigrp | Classic EIGRP Fundamentals | Foundation | 60m | progressive | 3.2.a | R1, R2, R3, PC1, PC2 |
| 01 | lab-01-named-mode-dual-stack | Named Mode and Dual-Stack | Foundation | 75m | progressive | 3.2.a | R1, R2, R3, PC1, PC2 |
| 02 | lab-02-stub-summarization-variance | Stub, Summarization, and Unequal-Cost Load Balancing | Intermediate | 90m | progressive | 3.2.a | R1, R2, R3, R4, PC1, PC2 |
| 03 | lab-03-capstone-config | EIGRP Full Protocol Mastery — Capstone I | Advanced | 120m | capstone_i | 3.2.a | R1, R2, R3, R4, PC1, PC2 |
| 04 | lab-04-capstone-troubleshoot | EIGRP Comprehensive Troubleshooting — Capstone II | Advanced | 120m | capstone_ii | 3.2.a | R1, R2, R3, R4, PC1, PC2 |

## Blueprint Coverage Matrix

| Blueprint Bullet | Description | Covered In |
|-----------------|-------------|------------|
| 3.2.a | Compare EIGRP/OSPF — advanced distance vector, DUAL, metrics, load balancing, path selection, stub | lab-00, lab-01, lab-02, lab-03, lab-04 |

## Design Decisions

- **Single blueprint bullet expanded to 5 labs:** 3.2.a is a "compare" bullet covering EIGRP's full depth — DUAL algorithm, classic vs wide metrics, feasibility condition, unequal-cost load balancing, stub routing, and named mode. Each concept requires dedicated hands-on to build real understanding. The OSPF comparison theory is included in the workbook Section 1 concepts.
- **Triangle topology for DUAL demonstration:** R1-R2-R3 triangle provides redundant paths to every destination. The R1-R3 direct path vs R1-R2-R3 indirect path creates the successor/feasible successor pair needed for DUAL and variance demonstrations.
- **R4 is optional (introduced lab-02):** Keeps early labs simpler (3 routers). R4 adds a stub spoke for EIGRP stub routing and provides PC2's LAN segment.
- **Classic mode first, then named mode:** Lab-00 uses classic EIGRP (`router eigrp 100`) to establish fundamentals. Lab-01 converts to named mode (`router eigrp EIGRP-LAB`) which natively supports dual-stack via address families. This mirrors real-world migration paths and exam expectations.
- **Dual-stack from lab-01 onward:** Lab-00 is IPv4 only. Lab-01 introduces named mode with IPv6 address family, carried through all subsequent labs. Matches the OSPF topic's dual-stack strategy.
- **PC1 on R3, PC2 on R4:** PC1 is reachable from lab-00 (R3 is core). PC2 requires R4 (introduced lab-02). In lab-00/01, PC2's LAN doesn't exist yet — end-to-end verification uses PC1 plus loopback pings.
- **Bandwidth manipulation for unequal-cost:** The R2-R3 link has lower bandwidth configured to create metric asymmetry. This allows R1 to have both a successor (via R3 directly) and a feasible successor (via R2 then R3) for R3's LAN, enabling variance-based load balancing.
