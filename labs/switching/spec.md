# Layer 2 Switching — Lab Specification

## Exam Reference
- **Exam:** Implementing Cisco Enterprise Network Core Technologies v1.2 (350-401)
- **Blueprint Bullets:**
  - 3.1: Layer 2
  - 3.1.a: Troubleshoot static and dynamic 802.1q trunking protocols
  - 3.1.b: Troubleshoot static and dynamic EtherChannels
  - 3.1.c: Configure and verify common Spanning Tree Protocols (RSTP, MST) and Spanning Tree enhancements such as root guard and BPDU guard

## Topology Summary

Three IOSvL2 switches (SW1, SW2, SW3) in a full-mesh triangle with dual links per pair
(6 inter-switch links total, supporting 3 two-member EtherChannel bundles). One IOSv
router (R1) connects via trunk to SW1 for inter-VLAN routing (router-on-a-stick). Two
VPC end-hosts (PC1, PC2) connect to SW2 and SW3 for reachability verification. Total: 6 nodes.

## Lab Progression

| # | Folder | Title | Difficulty | Time | Type | Blueprint Refs | Devices |
|---|--------|-------|-----------|------|------|----------------|---------|
| 00 | lab-00-vlans-and-trunking | VLANs and Trunk Negotiation | Foundation | 60m | progressive | 3.1, 3.1.a | SW1, SW2, SW3, R1, PC1, PC2 |
| 01 | lab-01-etherchannel | Static and Dynamic EtherChannels | Foundation | 60m | progressive | 3.1.b | SW1, SW2, SW3, R1, PC1, PC2 |
| 02 | lab-02-rstp-and-enhancements | RSTP and STP Enhancements | Intermediate | 75m | progressive | 3.1.c | SW1, SW2, SW3, R1, PC1, PC2 |
| 03 | lab-03-mst | Multiple Spanning Tree (MST) | Intermediate | 75m | standalone | 3.1.c | SW1, SW2, SW3, R1, PC1, PC2 |
| 04 | lab-04-capstone-config | Layer 2 Full Configuration — Capstone I | Advanced | 120m | capstone_i | all | SW1, SW2, SW3, R1, PC1, PC2 |
| 05 | lab-05-capstone-troubleshoot | Layer 2 Comprehensive Troubleshooting — Capstone II | Advanced | 120m | capstone_ii | all | SW1, SW2, SW3, R1, PC1, PC2 |

## Blueprint Coverage Matrix

| Blueprint Bullet | Description | Covered In |
|-----------------|-------------|------------|
| 3.1 | Layer 2 | lab-00, lab-01, lab-02, lab-04, lab-05 |
| 3.1.a | Troubleshoot static and dynamic 802.1q trunking protocols | lab-00, lab-04, lab-05 |
| 3.1.b | Troubleshoot static and dynamic EtherChannels | lab-01, lab-04, lab-05 |
| 3.1.c | Configure and verify common STP (RSTP, MST) and enhancements (root guard, BPDU guard) | lab-02, lab-03, lab-04, lab-05 |

## Design Decisions

- **MST is standalone (lab-03):** MST requires `spanning-tree mode mst` which replaces Rapid PVST+ — this is a mode switch, not an additive config. Placing it after the progressive chain preserves the "never remove config" rule for labs 00-02.
- **Dual inter-switch links from the start:** Even though EtherChannel isn't configured until lab-01, the physical links are present from lab-00 (as individual trunk links). This avoids topology changes mid-sequence.
- **Troubleshooting built into progressive labs:** Blueprint bullets 3.1.a and 3.1.b use the verb "troubleshoot" — each progressive lab includes verification tasks that exercise diagnostic skills (DTP mode combinations, EtherChannel formation checks), not just configuration.
- **Router-on-a-stick for inter-VLAN routing:** R1 provides L3 reachability across VLANs, enabling end-to-end ping verification between PC1 and PC2 in different VLANs.
