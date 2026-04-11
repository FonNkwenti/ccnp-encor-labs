# OSPF Routing — Lab Specification

## Exam Reference
- **Exam:** Implementing Cisco Enterprise Network Core Technologies v1.2 (350-401)
- **Blueprint Bullets:**
  - 3.2.a: Compare routing concepts of EIGRP and OSPF (advanced distance vector vs. link state, load balancing, path selection, path operations, metrics, and area types) — OSPF side
  - 3.2.b: Configure simple OSPFv2/v3 environments, including multiple normal areas, summarization, and filtering (neighbor adjacency, point-to-point, and broadcast network types, and passive-interface)

## Topology Summary

Five core IOSv routers (R1-R5) spanning three OSPF areas, plus one optional router (R6)
introduced in lab-03 for stub/NSSA area demonstrations. **Dual-stack (IPv4 + IPv6)** from
lab-01 onward — all router interfaces carry both IPv4 and IPv6 addresses; OSPFv3 address
families run alongside OSPFv2. Area 0 uses a shared Ethernet segment (via EVE-NG unmanaged
switch) connecting R1, R2, R3 for DR/BDR election labs. Areas 1 and 2 use back-to-back
links for point-to-point network type. Two VPC end-hosts (PC1, PC2) in different areas for
end-to-end verification (both IPv4 and IPv6). Total: 8 nodes (5 core + 1 optional + 2 VPCs).

## Area Design

| Area | Type | Routers | Purpose |
|------|------|---------|---------|
| 0 (Backbone) | Normal | R1, R2, R3 | Shared multi-access segment for DR/BDR election |
| 1 | Normal → Stub/Totally Stubby (lab-03) | R2 (ABR), R4, R6 (optional) | Standard area, later converted to stub |
| 2 | Normal → NSSA (lab-03) | R3 (ABR), R5 | ASBR redistribution into NSSA |

## Lab Progression

| # | Folder | Title | Difficulty | Time | Type | Blueprint Refs | Devices |
|---|--------|-------|-----------|------|------|----------------|---------|
| 00 | lab-00-single-area-ospfv2 | Single-Area OSPFv2 Fundamentals | Foundation | 60m | progressive | 3.2.a, 3.2.b | R1, R2, R3, R4, R5, PC1, PC2 |
| 01 | lab-01-multi-area-ospfv2 | Multi-Area OSPFv2 | Foundation | 75m | progressive | 3.2.a, 3.2.b | R1, R2, R3, R4, R5, PC1, PC2 |
| 02 | lab-02-network-types | Broadcast vs Point-to-Point Network Types | Intermediate | 75m | progressive | 3.2.b | R1, R2, R3, R4, R5, PC1, PC2 |
| 03 | lab-03-area-types | Stub, Totally Stubby, and NSSA Areas | Intermediate | 75m | progressive | 3.2.a | R1, R2, R3, R4, R5, R6, PC1, PC2 |
| 04 | lab-04-summarization-filtering | Inter-Area Summarization and Filtering | Advanced | 90m | progressive | 3.2.b | R1, R2, R3, R4, R5, R6, PC1, PC2 |
| 05 | lab-05-capstone-config | OSPF Full Protocol Mastery — Capstone I | Advanced | 120m | capstone_i | all | all |
| 06 | lab-06-capstone-troubleshoot | OSPF Comprehensive Troubleshooting — Capstone II | Advanced | 120m | capstone_ii | all | all |

## Blueprint Coverage Matrix

| Blueprint Bullet | Description | Covered In |
|-----------------|-------------|------------|
| 3.2.a | Compare EIGRP/OSPF — link-state concepts, metrics, load balancing, area types | lab-00, lab-01, lab-03, lab-05, lab-06 |
| 3.2.b | Configure OSPFv2/v3, multi-area, summarization, filtering, network types, passive-interface | lab-00, lab-01, lab-02, lab-04, lab-05, lab-06 |

## Design Decisions

- **Shared multi-access segment in Area 0:** R1, R2, R3 connect via an EVE-NG unmanaged switch on a common subnet. This creates a genuine broadcast segment for DR/BDR election observation — not simulated with `ip ospf network broadcast` on point-to-point links.
- **Area types are progressive (not standalone):** Unlike MST in switching, adding `area X stub` or `area X nssa` is additive config to the existing OSPF process. No commands are removed, so the progressive chain holds.
- **R6 is optional (introduced lab-03):** Keeps early labs simpler (5 routers). R6 adds a second internal router to Area 1 for richer stub area demonstration.
- **Dual-stack is a first-class requirement, not an add-on:** The 350-401 exam description mandates "dual stack (IPv4 and IPv6) architecture" and bullet 3.2.b explicitly says "OSPFv2/v3." Every router interface has both IPv4 and IPv6 addresses (2001:db8::/32 documentation space). OSPFv3 address families are introduced in lab-01 and carried through all subsequent labs. IPv6 end-to-end reachability is verified alongside IPv4.
- **OSPFv3 woven into labs, not a separate lab:** OSPFv2 is the foundation in lab-00 (IPv4 only); OSPFv3 address families are added in lab-01 when multi-area is introduced, then carried progressively through all remaining labs.
- **Point-to-point vs broadcast is a dedicated lab (lab-02):** The blueprint explicitly requires both network types. Lab-02 focuses on converting interfaces, observing adjacency behavior differences, and understanding when each type is appropriate.
