# LISP and VXLAN — Lab Specification

## Exam Reference
- **Exam:** Implementing Cisco Enterprise Network Core Technologies v1.2 (350-401)
- **Blueprint Bullets:**
  - 2.1: Describe device virtualization technologies
  - 2.1.a: Hypervisor type 1 and 2
  - 2.1.b: Virtual machine
  - 2.1.c: Virtual switching
  - 2.3: Describe network virtualization concepts
  - 2.3.a: LISP
  - 2.3.b: VXLAN

## Topology Summary

No EVE-NG topology required. All bullets in this topic use the "describe" verb — content is
conceptual. Reference workbooks use architecture diagrams, packet format analysis, show-command
interpretation from reference outputs, and quiz-style verification exercises. Total: 0 nodes.

## Workbook Format

All labs in this topic use **reference workbook format**. No `setup_lab.py`, no
`fault-injection/` scripts, no `initial-configs/` or `solutions/` directories. Each lab
contains only `workbook.md` and optionally `topology.drawio` for architecture diagrams.

## Lab Progression

| # | Folder | Title | Difficulty | Time | Type | Blueprint Refs | Devices | Format |
|---|--------|-------|-----------|------|------|----------------|---------|--------|
| 00 | lab-00-device-virtualization | Device Virtualization — Hypervisors, VMs, and Virtual Switching | Foundation | 45m | progressive | 2.1, 2.1.a, 2.1.b, 2.1.c | — | reference |
| 01 | lab-01-lisp-and-vxlan | LISP and VXLAN Network Virtualization Concepts | Intermediate | 60m | progressive | 2.3, 2.3.a, 2.3.b | — | reference |
| 02 | lab-02-capstone-review | Virtualization Concepts Comprehensive Review | Advanced | 60m | capstone_i | all | — | reference |

## Blueprint Coverage Matrix

| Blueprint Bullet | Description | Covered In |
|-----------------|-------------|------------|
| 2.1 | Describe device virtualization technologies | lab-00, lab-02 |
| 2.1.a | Hypervisor type 1 and 2 | lab-00, lab-02 |
| 2.1.b | Virtual machine | lab-00, lab-02 |
| 2.1.c | Virtual switching | lab-00, lab-02 |
| 2.3 | Describe network virtualization concepts | lab-01, lab-02 |
| 2.3.a | LISP | lab-01, lab-02 |
| 2.3.b | VXLAN | lab-01, lab-02 |

## Design Decisions

- **3 labs matching the estimate:** Two progressive reference workbooks covering the two topic areas (device virtualization, network virtualization), plus one capstone review. No Capstone II (troubleshooting) — there is nothing to break in a reference-only topic.
- **Single capstone (review) instead of two:** With no hands-on configuration, a troubleshooting capstone has no meaning. The single capstone is a comprehensive review covering all bullets with scenario-based questions and interpretation exercises.
- **Device virtualization in lab-00:** 2.1 covers hypervisors, VMs, and virtual switching — all conceptual. Students learn to compare Type 1 vs Type 2 hypervisors, understand VM vs container isolation, and describe vSwitch, DPDK, SR-IOV, and PCI passthrough concepts.
- **LISP and VXLAN combined in lab-01:** Both are network virtualization overlay technologies often deployed together (SD-Access uses LISP for control plane + VXLAN for data plane). Covering them in one lab shows the architectural relationship.
- **No EVE-NG topology:** LISP requires specific IOS-XE map-server features. VXLAN BGP EVPN requires NX-OSv 9000. Neither is practical for a "describe" bullet. Reference workbooks with packet diagrams and show-command interpretation are more exam-aligned.
- **Cross-references to other topics:** VXLAN is the data plane for SD-Access (covered in sd-networking lab-03). LISP is the control plane for SD-Access. VRF (covered in virtualization topic) is the data path virtualization that complements these overlay concepts.
