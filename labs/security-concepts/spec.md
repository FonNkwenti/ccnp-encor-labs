# Security Design and API Security — Lab Specification

## Exam Reference
- **Exam:** Implementing Cisco Enterprise Network Core Technologies v1.2 (350-401)
- **Blueprint Bullets:**
  - 5.3: Describe REST API security
  - 5.4: Describe the components of network security design
  - 5.4.a: Threat defense
  - 5.4.b: Endpoint security
  - 5.4.c: Next-generation firewall
  - 5.4.d: TrustSec and MACsec
  - 4.5: Describe how Cisco Catalyst Center is used to apply network configuration, monitoring, and management using traditional and AI-powered workflows
  - 6.3: Describe the high-level principles and benefits of a data modeling language, such as YANG
  - 6.4: Describe APIs for Cisco Catalyst Center and SD-WAN Manager
  - 6.7: Compare agent vs. agentless orchestration tools

## Topology Summary

No EVE-NG topology required. All bullets use "describe," "explain," or "compare" verbs.
Content is entirely conceptual — requires Catalyst Center, ISE, NGFW, and SD-WAN Manager,
none of which are available in this EVE-NG environment. MACsec requires hardware ASICs.
Reference workbooks use architecture diagrams, API payload interpretation, and quiz-style
verification exercises. Total: 0 nodes.

## Workbook Format

All labs use **reference workbook format**. No `setup_lab.py`, no `fault-injection/` scripts,
no `initial-configs/` or `solutions/` directories. Each lab contains only `workbook.md` and
optionally `topology.drawio` for architecture diagrams.

## Lab Progression

| # | Folder | Title | Difficulty | Time | Type | Blueprint Refs | Devices | Format |
|---|--------|-------|-----------|------|------|----------------|---------|--------|
| 00 | lab-00-security-design | Network Security Design and Components | Foundation | 60m | progressive | 5.3, 5.4, 5.4.a, 5.4.b, 5.4.c, 5.4.d | — | reference |
| 01 | lab-01-catalyst-center-and-apis | Catalyst Center, YANG, and Network APIs | Intermediate | 60m | progressive | 4.5, 6.3, 6.4, 6.7 | — | reference |
| 02 | lab-02-capstone-review | Security Design and APIs Comprehensive Review | Advanced | 60m | capstone_i | all | — | reference |

## Blueprint Coverage Matrix

| Blueprint Bullet | Description | Covered In |
|-----------------|-------------|------------|
| 5.3 | Describe REST API security | lab-00, lab-02 |
| 5.4 | Describe components of network security design | lab-00, lab-02 |
| 5.4.a | Threat defense | lab-00, lab-02 |
| 5.4.b | Endpoint security | lab-00, lab-02 |
| 5.4.c | Next-generation firewall | lab-00, lab-02 |
| 5.4.d | TrustSec and MACsec | lab-00, lab-02 |
| 4.5 | Describe Catalyst Center for network management | lab-01, lab-02 |
| 6.3 | Describe YANG data modeling language | lab-01, lab-02 |
| 6.4 | Describe APIs for Catalyst Center and SD-WAN Manager | lab-01, lab-02 |
| 6.7 | Compare agent vs agentless orchestration tools | lab-01, lab-02 |

## Design Decisions

- **3 labs matching the estimate:** Despite 10 blueprint bullets, all are conceptual "describe" verbs. Two thematic groupings (security design + management/APIs) plus one capstone review is sufficient.
- **Security design in lab-00:** Groups 5.3 (REST API security) with 5.4 (network security design). Both are security-themed conceptual topics. REST API security (authentication methods, token handling) complements the security design components.
- **Catalyst Center and APIs in lab-01:** Groups 4.5 (Catalyst Center), 6.3 (YANG), 6.4 (network APIs), and 6.7 (orchestration tools). These are all management/programmability concepts that relate to each other — Catalyst Center uses YANG models exposed via APIs, managed by orchestration tools.
- **Single capstone (review):** Same rationale as overlay-technologies — no hands-on configuration means no troubleshooting capstone. The review capstone uses scenario-based questions covering all 10 bullets.
- **No EVE-NG topology:** All topics require infrastructure not available in EVE-NG (Catalyst Center, ISE, NGFW appliances, MACsec-capable hardware). Reference workbooks with architecture diagrams and API payload interpretation are more exam-aligned than attempting to simulate unavailable platforms.
- **Cross-references:** REST API security connects to automation topic (RESTCONF authentication). TrustSec/SGT connects to sd-networking (SD-Access uses SGTs). YANG connects to automation (NETCONF/RESTCONF use YANG models). Catalyst Center connects to sd-networking (SD-Access management plane).
