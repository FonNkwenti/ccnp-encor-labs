# Automation and Programmability — Lab Specification

## Exam Reference
- **Exam:** Implementing Cisco Enterprise Network Core Technologies v1.2 (350-401)
- **Blueprint Bullets:**
  - 4.6: Configure and verify NETCONF and RESTCONF
  - 6.1: Interpret basic Python components and scripts
  - 6.2: Construct valid JSON-encoded files
  - 6.5: Interpret REST API response codes and results in payload using Cisco Catalyst Center and RESTCONF
  - 6.6: Construct an EEM applet to automate configuration, troubleshooting, or data collection

## Topology Summary

Two CSR1000v routers (R1/R2 for NETCONF and RESTCONF — IOS-XE required), one IOSv router
(R3 for EEM applets), and two VPC end-hosts (PC1, PC2 for traffic generation). R1 and R2
provide the model-driven programmability endpoints (YANG/NETCONF/RESTCONF). R3 provides the
EEM environment. OSPF runs as the IGP. Python and JSON exercises are workstation-based
(interpreted in the workbook, run from the student's local machine against R1/R2 APIs).
**Dual-stack (IPv4 + IPv6)** from lab-01 onward. Total: 5 nodes (3 routers + 2 VPCs).

## Lab Progression

| # | Folder | Title | Difficulty | Time | Type | Blueprint Refs | Devices |
|---|--------|-------|-----------|------|------|----------------|---------|
| 00 | lab-00-eem-applets | EEM Applets for On-Box Automation | Foundation | 60m | progressive | 6.6 | R1, R2, R3, PC1, PC2 |
| 01 | lab-01-python-and-json | Python Scripting and JSON Construction | Foundation | 75m | progressive | 6.1, 6.2 | R1, R2, R3, PC1, PC2 |
| 02 | lab-02-netconf | NETCONF Configuration and Verification | Intermediate | 90m | progressive | 4.6 | R1, R2, R3, PC1, PC2 |
| 03 | lab-03-restconf | RESTCONF and REST API Interpretation | Intermediate | 90m | progressive | 4.6, 6.5 | R1, R2, R3, PC1, PC2 |
| 04 | lab-04-capstone-config | Automation Full Mastery — Capstone I | Advanced | 120m | capstone_i | all | R1, R2, R3, PC1, PC2 |
| 05 | lab-05-capstone-troubleshoot | Automation Comprehensive Troubleshooting — Capstone II | Advanced | 120m | capstone_ii | all | R1, R2, R3, PC1, PC2 |

## Blueprint Coverage Matrix

| Blueprint Bullet | Description | Covered In |
|-----------------|-------------|------------|
| 4.6 | Configure and verify NETCONF and RESTCONF | lab-02, lab-03, lab-04, lab-05 |
| 6.1 | Interpret basic Python components and scripts | lab-01, lab-04, lab-05 |
| 6.2 | Construct valid JSON-encoded files | lab-01, lab-03, lab-04, lab-05 |
| 6.5 | Interpret REST API response codes and results using RESTCONF | lab-03, lab-04, lab-05 |
| 6.6 | Construct an EEM applet | lab-00, lab-04, lab-05 |

## Design Decisions

- **6 labs matching the estimate:** EEM (lab-00), Python/JSON (lab-01), NETCONF (lab-02), RESTCONF (lab-03), plus two capstones. Each progressive lab covers a distinct automation approach.
- **EEM first (lab-00):** EEM applets are on-box, CLI-based, and require no external tools — the simplest entry point to automation. Students learn event detectors, actions, and applet syntax before moving to off-box programmability.
- **Python/JSON before NETCONF/RESTCONF:** Understanding Python dictionaries and JSON structure is prerequisite for interpreting NETCONF XML/JSON payloads and RESTCONF responses. Lab-01 covers Python basics and JSON construction as workbook exercises with interpretation questions.
- **NETCONF before RESTCONF:** NETCONF (SSH-based, XML payload) is lower-level and helps students understand YANG data models before RESTCONF abstracts them behind HTTP/REST semantics. Lab-02 uses ncclient Python library or raw SSH subsystem.
- **Mixed platform (CSR1000v + IOSv):** NETCONF/RESTCONF require IOS-XE (CSR1000v). EEM works on any IOS/IOS-XE platform. R1/R2 are CSR1000v for API access; R3 is IOSv for EEM (lighter resource footprint).
- **Python exercises are workstation-based:** Students run Python scripts from their local machine (or EVE-NG host) targeting R1/R2 RESTCONF/NETCONF endpoints. No Python environment on the routers themselves.
- **Catalyst Center is conceptual:** Blueprint 6.5 mentions Catalyst Center, but no Catalyst Center instance is available. RESTCONF on CSR1000v covers the hands-on API portion; Catalyst Center API interpretation is theory in the workbook.
- **Dual-stack from lab-01:** Lab-00 (EEM) is IPv4 only. Lab-01+ exercises dual-stack where applicable (IPv6 interface config via NETCONF, IPv6 routes via RESTCONF).
