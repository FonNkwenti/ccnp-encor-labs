# Infrastructure Security — Lab Specification

## Exam Reference
- **Exam:** Implementing Cisco Enterprise Network Core Technologies v1.2 (350-401)
- **Blueprint Bullets:**
  - 5.1: Configure and verify device access control
  - 5.1.a: Lines and local user authentication
  - 5.1.b: Authentication and authorization using AAA
  - 5.2: Configure and verify infrastructure security features
  - 5.2.a: ACLs
  - 5.2.b: CoPP

## Topology Summary

Three IOSv routers (R1 as the primary hardening target, R2 as a management station/AAA
peer, R3 as an external threat simulation endpoint), one IOSvL2 switch (SW1 for 802.1X
port-based access control), and two VPC end-hosts (PC1 as a legitimate user, PC2 as an
untrusted host). OSPF runs as the IGP. **Dual-stack (IPv4 + IPv6)** from lab-01 onward —
IPv6 ACLs and IPv6-aware CoPP entries. Total: 6 nodes (3 routers + 1 switch + 2 VPCs).

## Lab Progression

| # | Folder | Title | Difficulty | Time | Type | Blueprint Refs | Devices |
|---|--------|-------|-----------|------|------|----------------|---------|
| 00 | lab-00-device-access | Lines, Local Users, and SSH Hardening | Foundation | 60m | progressive | 5.1, 5.1.a | R1, R2, R3, SW1, PC1, PC2 |
| 01 | lab-01-aaa | AAA Authentication and Authorization | Intermediate | 75m | progressive | 5.1, 5.1.b | R1, R2, R3, SW1, PC1, PC2 |
| 02 | lab-02-acls | Standard, Extended, and IPv6 ACLs | Intermediate | 75m | progressive | 5.2, 5.2.a | R1, R2, R3, SW1, PC1, PC2 |
| 03 | lab-03-copp | Control Plane Policing | Advanced | 75m | progressive | 5.2, 5.2.b | R1, R2, R3, SW1, PC1, PC2 |
| 04 | lab-04-capstone-config | Infrastructure Security Full Mastery — Capstone I | Advanced | 120m | capstone_i | all | R1, R2, R3, SW1, PC1, PC2 |
| 05 | lab-05-capstone-troubleshoot | Infrastructure Security Comprehensive Troubleshooting — Capstone II | Advanced | 120m | capstone_ii | all | R1, R2, R3, SW1, PC1, PC2 |

## Blueprint Coverage Matrix

| Blueprint Bullet | Description | Covered In |
|-----------------|-------------|------------|
| 5.1 | Configure and verify device access control | lab-00, lab-01, lab-04, lab-05 |
| 5.1.a | Lines and local user authentication | lab-00, lab-04, lab-05 |
| 5.1.b | Authentication and authorization using AAA | lab-01, lab-04, lab-05 |
| 5.2 | Configure and verify infrastructure security features | lab-02, lab-03, lab-04, lab-05 |
| 5.2.a | ACLs | lab-02, lab-04, lab-05 |
| 5.2.b | CoPP | lab-03, lab-04, lab-05 |

## Design Decisions

- **6 labs matching the estimate:** Two access control labs (5.1.a lines/SSH, 5.1.b AAA), two infrastructure security labs (5.2.a ACLs, 5.2.b CoPP), plus two capstones. Each sub-bullet gets a dedicated lab.
- **Device access before infrastructure security:** Students must be able to log into devices securely (5.1) before protecting the infrastructure (5.2). The progressive chain naturally flows: secure the login -> secure the management plane -> filter traffic -> protect the control plane.
- **Local AAA (no external server):** AAA labs use the local user database and local method lists. This avoids requiring a RADIUS/TACACS+ server in EVE-NG. The concepts (method lists, authorization levels, accounting) are identical — only the server backend differs. TACACS+ and RADIUS theory is covered in the workbook.
- **SW1 for port-based access:** SW1 provides a switching context for 802.1X concepts and port security. While full 802.1X requires an ISE server, the switch-side configuration (dot1x, MAB) is teachable with local auth fallback.
- **R3 as external/threat simulation:** R3 represents an untrusted network. ACLs and CoPP policies protect R1/R2 from traffic originating at R3. This makes security policies tangible — without a threat source, ACLs are abstract.
- **CoPP as the final progressive lab:** CoPP uses MQC (class-map, policy-map) applied to the control-plane interface. It's the most complex topic and builds on ACL knowledge from lab-02 (ACLs classify traffic for CoPP class-maps).
- **Dual-stack from lab-01:** Lab-00 is IPv4 only. Lab-01 adds IPv6 awareness. Lab-02 configures both IPv4 and IPv6 ACLs. Lab-03 includes IPv6 CoPP entries.
