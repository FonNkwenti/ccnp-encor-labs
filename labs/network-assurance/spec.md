# Network Assurance — Lab Specification

## Exam Reference
- **Exam:** Implementing Cisco Enterprise Network Core Technologies v1.2 (350-401)
- **Blueprint Bullets:**
  - 4.1: Diagnose network problems using such as debugs, conditional debugs, traceroute, ping, SNMP, and syslog
  - 4.2: Configure and verify Flexible NetFlow
  - 4.3: Configure SPAN/RSPAN/ERSPAN
  - 4.4: Configure and verify IPSLA

## Topology Summary

Three IOSv routers (R1/R2/R3 in a chain), two IOSvL2 switches (SW1/SW2 for SPAN/RSPAN),
and two VPC end-hosts (PC1 on SW1, PC2 on SW2). R1 and R2 connect through SW1/SW2 for
L2 visibility. R3 is a remote router providing longer paths for traceroute and IP SLA
probes. OSPF runs as the IGP. **Dual-stack (IPv4 + IPv6)** from lab-01 onward. Total:
7 nodes (3 routers + 2 switches + 2 VPCs).

## Lab Progression

| # | Folder | Title | Difficulty | Time | Type | Blueprint Refs | Devices |
|---|--------|-------|-----------|------|------|----------------|---------|
| 00 | lab-00-diagnostics | Network Diagnostics — Debug, Ping, Traceroute, SNMP, Syslog | Foundation | 60m | progressive | 4.1 | R1, R2, R3, SW1, SW2, PC1, PC2 |
| 01 | lab-01-flexible-netflow | Flexible NetFlow Configuration and Verification | Intermediate | 75m | progressive | 4.2 | R1, R2, R3, SW1, SW2, PC1, PC2 |
| 02 | lab-02-span-rspan | SPAN and RSPAN Traffic Mirroring | Intermediate | 75m | progressive | 4.3 | R1, R2, R3, SW1, SW2, PC1, PC2 |
| 03 | lab-03-ip-sla | IP SLA Probes and Tracking | Intermediate | 75m | progressive | 4.4 | R1, R2, R3, SW1, SW2, PC1, PC2 |
| 04 | lab-04-capstone-config | Network Assurance Full Mastery — Capstone I | Advanced | 120m | capstone_i | all | R1, R2, R3, SW1, SW2, PC1, PC2 |
| 05 | lab-05-capstone-troubleshoot | Network Assurance Comprehensive Troubleshooting — Capstone II | Advanced | 120m | capstone_ii | all | R1, R2, R3, SW1, SW2, PC1, PC2 |

## Blueprint Coverage Matrix

| Blueprint Bullet | Description | Covered In |
|-----------------|-------------|------------|
| 4.1 | Diagnose network problems — debugs, conditional debugs, traceroute, ping, SNMP, syslog | lab-00, lab-04, lab-05 |
| 4.2 | Configure and verify Flexible NetFlow | lab-01, lab-04, lab-05 |
| 4.3 | Configure SPAN/RSPAN/ERSPAN | lab-02, lab-04, lab-05 |
| 4.4 | Configure and verify IPSLA | lab-03, lab-04, lab-05 |

## Design Decisions

- **6 labs instead of estimated 5:** Four distinct blueprint bullets each warrant a dedicated lab. With 2 capstones, that makes 6. The +1 deviation keeps each bullet's lab focused rather than combining two unrelated toolsets.
- **One bullet per progressive lab:** Each of 4.1-4.4 is a distinct toolset (diagnostics, NetFlow, SPAN, IP SLA). Combining them would create unfocused labs. The progressive chain works because later tools build on the diagnostic foundation from lab-00.
- **Mixed platform (IOSv + IOSvL2):** SPAN/RSPAN requires L2 switches. SW1/SW2 provide the switching infrastructure for mirror sessions. Routers handle NetFlow, IP SLA, and debug/syslog. ERSPAN (L3 mirroring) is covered conceptually — it requires IOS-XE features not fully available on IOSvL2, so the lab focuses on SPAN and RSPAN with ERSPAN theory.
- **Chain topology (R1-SW1-SW2-R2-R3):** Provides multiple hops for traceroute exercises, a switched segment for SPAN/RSPAN, and a remote endpoint (R3) for IP SLA probes across multiple hops.
- **ERSPAN as theory + show commands:** Full ERSPAN configuration requires IOS-XE (CSR1000v). Rather than adding a CSR1000v for one feature, ERSPAN is covered through configuration interpretation and comparison with SPAN/RSPAN in lab-02.
- **Dual-stack from lab-01:** Lab-00 diagnostics are IPv4 only. Lab-01 adds IPv6 NetFlow records. Subsequent labs exercise both stacks where applicable (IPv6 traceroute, IPv6 IP SLA probes).
- **SNMP and syslog in lab-00:** Both are diagnostic tools under 4.1. SNMP community strings, trap receivers, and syslog severity levels are configured on routers. No external SNMP/syslog server needed — local buffer and show commands suffice.
