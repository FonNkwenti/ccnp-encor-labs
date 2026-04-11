# SD-WAN and SD-Access — Lab Specification

## Exam Reference
- **Exam:** Implementing Cisco Enterprise Network Core Technologies v1.2 (350-401)
- **Blueprint Bullets:**
  - 1.2: Explain the working principles of the Cisco Catalyst SD-WAN solution
  - 1.2.a: SD-WAN control and data planes elements
  - 1.2.b: Benefits and limitations of Catalyst SD-WAN solution
  - 1.3: Explain the working principles of the Cisco SD-Access solution
  - 1.3.a: SD-Access control and data planes elements
  - 1.3.b: Traditional campus interoperating with SD-Access

## Topology Summary

**SD-WAN labs (lab-00 through lab-02):** One vManage (NMS), one vSmart (controller), one
vBond (orchestrator), and two vEdge routers (branch sites) — all Viptela 20.6.2 images on
EVE-NG. An IOSv router simulates an ISP/transport network between vEdge sites.

**SD-Access labs (lab-03):** Reference workbook only — no topology. Requires Catalyst Center
and ISE which are not available in EVE-NG.

Total for SD-WAN: 6 nodes (vManage + vSmart + vBond + 2 vEdge + 1 IOSv transport).
Total for SD-Access: 0 nodes (conceptual). Overall: 6 nodes max.

## Workbook Format

SD-WAN labs (lab-00 through lab-02) use **standard lab format** — hands-on with the Viptela
platform. SD-Access lab (lab-03) uses **reference workbook format** — architecture diagrams,
concept walkthroughs, and quiz-style questions. Capstones are hybrid.

## Lab Progression

| # | Folder | Title | Difficulty | Time | Type | Blueprint Refs | Devices | Format |
|---|--------|-------|-----------|------|------|----------------|---------|--------|
| 00 | lab-00-sdwan-fabric-bringup | SD-WAN Fabric Bring-Up and Control Plane | Foundation | 90m | progressive | 1.2, 1.2.a | vManage, vSmart, vBond, vEdge1, vEdge2, R-TRANSPORT | standard |
| 01 | lab-01-sdwan-omp-and-policies | OMP Routing and Control Policies | Intermediate | 90m | progressive | 1.2, 1.2.a, 1.2.b | vManage, vSmart, vBond, vEdge1, vEdge2, R-TRANSPORT | standard |
| 02 | lab-02-sdwan-data-plane | SD-WAN Data Plane and Application Policies | Intermediate | 90m | progressive | 1.2, 1.2.a, 1.2.b | vManage, vSmart, vBond, vEdge1, vEdge2, R-TRANSPORT | standard |
| 03 | lab-03-sd-access-concepts | SD-Access Architecture and Campus Integration | Intermediate | 60m | standalone | 1.3, 1.3.a, 1.3.b | — | reference |
| 04 | lab-04-capstone-config | SD-Networking Full Mastery — Capstone I | Advanced | 120m | capstone_i | all | vManage, vSmart, vBond, vEdge1, vEdge2, R-TRANSPORT | hybrid |
| 05 | lab-05-capstone-troubleshoot | SD-Networking Comprehensive Troubleshooting — Capstone II | Advanced | 120m | capstone_ii | all | vManage, vSmart, vBond, vEdge1, vEdge2, R-TRANSPORT | hybrid |

## Blueprint Coverage Matrix

| Blueprint Bullet | Description | Covered In |
|-----------------|-------------|------------|
| 1.2 | Explain Cisco Catalyst SD-WAN working principles | lab-00, lab-01, lab-02, lab-04, lab-05 |
| 1.2.a | SD-WAN control and data planes elements | lab-00, lab-01, lab-02, lab-04, lab-05 |
| 1.2.b | Benefits and limitations of Catalyst SD-WAN | lab-01, lab-02, lab-04, lab-05 |
| 1.3 | Explain Cisco SD-Access working principles | lab-03, lab-04, lab-05 |
| 1.3.a | SD-Access control and data planes elements | lab-03, lab-04, lab-05 |
| 1.3.b | Traditional campus interoperating with SD-Access | lab-03, lab-04, lab-05 |

## Design Decisions

- **6 labs (+1 from estimate of 5):** SD-WAN needs 3 progressive labs for fabric bring-up, OMP/policies, and data plane. SD-Access needs 1 reference lab. Plus 2 capstones = 6. The extra lab allows proper pacing of SD-WAN complexity.
- **SD-WAN is hands-on:** EVE-NG has vManage, vSmart, vBond, vEdge 20.6.2 images. Fabric bring-up, OMP routing, and control/data policies are all configurable via vManage GUI and CLI.
- **SD-Access is reference only:** Requires Catalyst Center and ISE — neither available in EVE-NG. Reference workbook covers architecture, fabric roles, VXLAN-SGT overlay, and traditional campus interop.
- **SD-Access as standalone lab:** Lab-03 does not depend on SD-WAN config state (different platform entirely). Marked `standalone: true` and placed before capstones.
- **R-TRANSPORT as ISP simulation:** One IOSv router provides the transport network (internet/MPLS simulation) between vEdge sites. This makes the underlay/overlay separation visible — vEdges build IPsec tunnels over R-TRANSPORT.
- **Fabric bring-up first:** SD-WAN requires strict bootstrapping order: vBond -> vSmart -> vManage -> vEdge. Lab-00 walks through this sequence. Without a functional fabric, OMP and policies cannot be demonstrated.
- **vManage GUI + CLI dual approach:** SD-WAN is primarily managed via vManage GUI, but CLI verification commands are essential for the exam. Labs use both approaches.
- **RAM considerations:** vManage requires significant RAM (~16 GB). The topology is intentionally minimal (2 vEdges) to fit within EVE-NG host constraints on the Dell Latitude 5540.
