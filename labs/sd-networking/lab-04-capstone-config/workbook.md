# Lab 04: SD-Networking Full Mastery — Capstone I

## Table of Contents

1. [Concepts & Skills Covered](#1-concepts--skills-covered)
2. [Topology & Scenario](#2-topology--scenario)
3. [Hardware & Environment Specifications](#3-hardware--environment-specifications)
4. [Base Configuration](#4-base-configuration)
5. [Lab Challenge: Full Protocol Mastery](#5-lab-challenge-full-protocol-mastery)
6. [Verification & Analysis](#6-verification--analysis)
7. [Verification Cheatsheet](#7-verification-cheatsheet)
8. [Solutions (Spoiler Alert!)](#8-solutions-spoiler-alert)
9. [Troubleshooting Scenarios](#9-troubleshooting-scenarios)
10. [Lab Completion Checklist](#10-lab-completion-checklist)

---

## 1. Concepts & Skills Covered

**Exam Objective:** 1.2 — Describe SD-WAN architecture and components; 1.2.a — Orchestration plane (vBond); 1.2.b — Management plane (vManage) and Control plane (vSmart); 1.3 — Describe SD-Access architecture; 1.3.a — Describe SD-Access fabric roles; 1.3.b — Traditional campus interoperability with SD-Access

This capstone integrates every topic from the SD-Networking chapter into a single challenge. You will build the complete Cisco Catalyst SD-WAN fabric from a blank slate — no pre-configured system parameters on any Viptela device — while also demonstrating mastery of SD-Access architecture concepts. Success requires understanding the precise bootstrap sequence, the relationship between control plane components, and the policy model that ties the overlay together.

### SD-WAN Component Roles and Bootstrap Sequence

The SD-WAN fabric has a strict bring-up order because each component depends on the one before it for initial discovery:

```
vBond (Orchestrator)  ← Must be first: all devices connect here for discovery
    ↓
vSmart (Controller)   ← Authenticates to vBond, becomes OMP route reflector
    ↓
vManage (NMS)         ← Authenticates to vBond, provides management plane
    ↓
vEdge1, vEdge2        ← Authenticate via vBond, establish DTLS to vSmart
```

Every device needs a `system` block with four parameters:
- `system-ip` — unique router ID used in OMP (like BGP router-id)
- `site-id` — groups devices at the same physical location
- `organization-name` — must match exactly across all devices (case-sensitive)
- `vbond` — IP address of the vBond orchestrator (entry point for discovery)

On vBond specifically, append `local` to the vbond line: `vbond 172.16.0.3 local`.

### OMP, VPN Model, and IPsec Data Plane

OMP (Overlay Management Protocol) is the SD-WAN routing protocol. vSmart acts as a route reflector: vEdges advertise their VPN 1 prefixes to vSmart via OMP, and vSmart reflects them to peer vEdges. The VPN model:

| VPN | Purpose | Interfaces |
|-----|---------|-----------|
| VPN 0 | Transport (WAN) — IPsec tunnels form here | ge0/0 on vEdges, eth1 on controllers |
| VPN 1 | Service (LAN) — user traffic | ge0/1 on vEdges |
| VPN 512 | OOB Management | eth0 on vManage |

For VPN 0 to carry IPsec tunnels, the interface needs a `tunnel-interface` block:
```
tunnel-interface
 encapsulation ipsec
 allow-service all
```

IPsec tunnels form automatically between vEdges once VPN 0 tunnel-interfaces are configured and OMP peering to vSmart is up. BFD probes ride these tunnels and measure loss/latency/jitter per path.

### Centralized Policy Architecture

All SD-WAN policies are authored centrally and pushed from vSmart to vEdges:

```
vManage (author) → push to vSmart → vSmart distributes to vEdges
```

**Control policies** manipulate OMP route advertisements (accept/reject/modify). They are applied on vSmart with `apply-policy site-list ... control-policy ... in/out`.

**App-route policies** steer application traffic based on BFD path quality against SLA classes. They are applied with `apply-policy site-list ... app-route-policy ...`.

Policy building blocks required in this lab:
- `site-list` — identifies which sites the policy targets
- `vpn-list` — identifies which VPN the policy applies to
- `sla-class` — defines acceptable loss/latency/jitter thresholds
- `control-policy` — OMP route manipulation sequences
- `app-route-policy` — data path steering sequences
- `apply-policy` — binds all the above to site-lists and activates them

### SD-Access Architecture (Conceptual Component)

SD-Access uses three logical planes:

| Plane | Technology | Purpose |
|-------|-----------|---------|
| Underlay | IS-IS routed access | Loop-free L3 transport between all fabric nodes |
| Overlay | VXLAN-GPO | Encapsulates endpoint traffic, carries SGT in GPO field |
| Control | LISP | Maps endpoint EIDs (MACs/IPs) to fabric RLOCs (node IPs) |

SGT (Scalable Group Tag) is a 16-bit value assigned to endpoints at ingress by the Fabric Edge Node. The tag travels in the VXLAN Group Policy Option header — not in the payload — and is enforced at egress based on Catalyst Center policy contracts.

LISP flow: when an endpoint sends its first packet, the Fabric Edge Node (xTR) queries the Control Plane Node (LISP MS/MR) via a LISP Map-Request. The CPN responds with the RLOC (IP of the destination Fabric Edge Node). Subsequent packets go directly xTR-to-xTR via VXLAN.

Traditional campus interop uses a **fusion router** at the Fabric Border Node: the fabric VN routes are leaked into the external VRF, and the fusion router redistributes between them. This allows pre-existing campus devices outside the fabric to reach endpoints inside the fabric.

**Skills this lab develops:**

| Skill | Description |
|-------|------------|
| SD-WAN bootstrap sequence | Configure all four Viptela component types in correct order |
| System block authoring | Write `system` block parameters from memory for each device type |
| VPN 0 tunnel configuration | Enable IPsec tunnel-interface on vEdge and controller WAN ports |
| OMP verification | Read `show omp peers` and `show omp routes` output accurately |
| Centralized policy authoring | Build complete site-list + vpn-list + sla-class + policy + apply-policy |
| BFD path quality reading | Interpret `show bfd sessions` loss/latency/jitter metrics |
| SD-Access architecture recall | Map LISP, VXLAN-GPO, IS-IS to their correct planes without prompts |
| Fusion router design | Explain brownfield SD-Access interop under exam conditions |

---

## 2. Topology & Scenario

**Scenario:** You have joined the network team at a regional enterprise that is migrating its WAN from traditional MPLS to Cisco Catalyst SD-WAN. The existing transport infrastructure (R-TRANSPORT) is already in place and connected, but every SD-WAN component has been factory-reset. Your job is to bring up the complete SD-WAN fabric from scratch: bootstrap all controllers, onboard both edge sites, configure routing and policy, and verify end-to-end application-aware connectivity. Additionally, as part of the enterprise's campus modernization planning, you must answer a series of SD-Access architecture questions that will inform the team's upcoming Catalyst Center deployment.

```
                    ┌──────────────────────────────────────────┐
                    │              R-TRANSPORT                 │
                    │          (IOSv — ISP Backbone)           │
                    │  Gi0/0: 172.16.0.254/24 (Controllers)   │
                    │  Gi0/1: 172.16.1.254/24 (vEdge1 WAN)    │
                    │  Gi0/2: 172.16.2.254/24 (vEdge2 WAN)    │
                    └───┬────────────┬────────────┬────────────┘
                        │            │            │
              172.16.0.x│            │172.16.1.x  │172.16.2.x
                        │            │            │
          ┌─────────────┴──┐         │         ┌──┴───────────────┐
          │  Controllers   │         │         │   vEdge1         │
          │                │         │         │ (Site 100)       │
          │ vManage eth1:  │         │         │ VPN0: 172.16.1.1 │
          │  172.16.0.1/24 │         │         │ VPN1: 192.168.1.x│
          │ vSmart eth1:   │         │         └──────────────────┘
          │  172.16.0.2/24 │         │
          │ vBond ge0/0:   │         │         ┌──────────────────┐
          │  172.16.0.3/24 │         │         │   vEdge2         │
          └────────────────┘         │         │ (Site 200)       │
                                     │         │ VPN0: 172.16.2.1 │
                                     └────────►│ VPN1: 192.168.2.x│
                                               └──────────────────┘

                    IPsec Overlay Tunnel (VPN 0 — formed after bootstrap)
                    vEdge1 ◄───────────────────────────────► vEdge2
                             BFD probes measure path quality
```

---

## 3. Hardware & Environment Specifications

| Device | Platform | Role | VPN 0 IP |
|--------|---------|------|----------|
| vManage | vtmgmt-20.6.2-001 | NMS / Management Plane | 172.16.0.1/24 |
| vSmart | vtsmart-20.6.2 | Controller / OMP RR | 172.16.0.2/24 |
| vBond | vtbond-20.6.2 | Orchestrator | 172.16.0.3/24 |
| vEdge1 | vtedge-20.6.2 | Edge — Site 100 | 172.16.1.1/24 |
| vEdge2 | vtedge-20.6.2 | Edge — Site 200 | 172.16.2.1/24 |
| R-TRANSPORT | IOSv | ISP Transport Backbone | Pre-configured |

**Console Access Table**

| Device | Port | Connection Command |
|--------|------|--------------------|
| vManage | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| vSmart | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| vBond | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| vEdge1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| vEdge2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R-TRANSPORT | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |

> **Note:** Viptela devices use `config` (not `configure terminal`) and `commit` (not `write memory`). Configuration is transactional — nothing takes effect until `commit` is issued.

**SD-WAN Fabric Parameters**

| Parameter | Value |
|-----------|-------|
| Organization name | `ENCOR-LAB` |
| vBond address | `172.16.0.3` |
| vEdge1 system-ip | `10.10.10.11` |
| vEdge2 system-ip | `10.10.10.12` |
| vSmart system-ip | `10.10.10.2` |
| vManage system-ip | `10.10.10.1` |
| vBond system-ip | `10.10.10.3` |
| vEdge1 site-id | `100` |
| vEdge2 site-id | `200` |

---

## 4. Base Configuration

The following is pre-loaded via `setup_lab.py` before you begin:

**Pre-configured (transport infrastructure — do not modify):**
- R-TRANSPORT: all GigabitEthernet interfaces with IP addresses and descriptions

**NOT pre-configured (your responsibility — start from blank):**
- System block (host-name, system-ip, site-id, organization-name, vbond) on all Viptela devices
- Tunnel-interface on VPN 0 interfaces (vBond, vSmart, vEdge1, vEdge2)
- VPN 1 service interfaces on vEdge1 and vEdge2
- OMP peering and route advertisement
- Control policy for path preference manipulation
- Application-aware routing policy with SLA class
- All apply-policy bindings on vSmart

> **This is a clean-slate capstone. Every Viptela device starts with only a VPN 0 interface address and a default route. The system block, tunnel-interface, VPN 1, and all policies are absent.**

---

## 5. Lab Challenge: Full Protocol Mastery

> This is a capstone lab. No step-by-step guidance is provided.
> Configure the complete SD-WAN solution from scratch — VPN 0 interface addressing is pre-configured; everything else is yours to build.
> All blueprint bullets for this chapter must be addressed.

**Part A — SD-WAN Hands-On Configuration**

Bootstrap and bring up the complete SD-WAN fabric. When complete, every device must show healthy control connections, OMP must be peering, and IPsec tunnels must be up between vEdge1 and vEdge2.

Required deliverables:
- All five Viptela devices have a complete `system` block
- vBond has `vbond ... local` and a `tunnel-interface` on ge0/0
- vSmart has a `tunnel-interface` on eth1
- vEdge1 and vEdge2 have `tunnel-interface` on ge0/0 (VPN 0) and a LAN interface on ge0/1 (VPN 1)
- `show control connections` shows all peers in `up` state on all devices
- `show omp peers` shows vEdges connected to vSmart
- `show bfd sessions` shows active sessions between vEdge1 and vEdge2
- VPN 1 LAN subnets are reachable from each site (ping 192.168.1.1 from vEdge2 VPN 1)

Then build the centralized policy stack on vSmart:
- A site-list for SITE1 (site-id 100) and SITE2 (site-id 200)
- A vpn-list for VPN1 (vpn 1)
- An SLA class named `DEFAULT` with loss ≤ 5%, latency ≤ 150ms, jitter ≤ 30ms
- A control policy named `PREFER-SITE1-PATH` that sets OMP preference to 200 for routes from SITE1
- An app-route policy named `APP-AWARE-ROUTING` that applies the SLA class to all traffic in VPN 1
- Apply the control policy outbound to SITE2 and the app-route policy to both sites

**Part B — SD-Access Architecture Questions**

Answer each question in writing (in your lab notes or a separate document). These simulate the conceptual questions you will face on the 350-401 exam.

1. A packet arrives at a Fabric Edge Node destined for an endpoint in a different fabric subnet. Describe the complete LISP control plane and data plane sequence from ingress to egress delivery — name every component involved.

2. A network engineer configures SGT 10 for the Finance VLAN and SGT 20 for the Guest VLAN. Guest users must never reach Finance servers. Trace the path of a packet from a Guest endpoint to a Finance server: where is the SGT applied, where is it enforced, and what field in the encapsulation header carries it?

3. The enterprise has a legacy IP telephony system connected to a traditional campus switch that is outside the SD-Access fabric. Users inside the fabric need to reach this phone system. Describe the architectural element required, how routing is achieved, and what Catalyst Center workflow step provisions it.

4. What is the difference between an SD-Access Internal Border Node and an External Border Node? Give a specific use case for each.

5. A junior engineer claims that SD-WAN and SD-Access are the same product with different names. Write a clear three-point comparison that distinguishes them across: target network domain, primary overlay protocol, and control plane protocol.

---

## 6. Verification & Analysis

### Control Plane Verification

```
vEdge1# show control connections
                                          PEER                                          PEER                CONTROLLER
PEER    PEER PEER            SITE       DOMAIN PEER                                     PRIVATE             PUBLIC                                      LOCAL
TYPE    PROT SYSTEM IP       ID    CS   ID     STATE                                    IP                  IP                                          COLOR            PROXY
vsmart  dtls 10.10.10.2      0     0    0      up                                       172.16.0.2          172.16.0.2                                  default          No   ! ← vSmart must show "up"
vbond   dtls 10.10.10.3      0     0    0      up                                       172.16.0.3          172.16.0.3                                  default          No   ! ← vBond must show "up"
vmanage dtls 10.10.10.1      0     0    0      up                                       172.16.0.1          172.16.0.1                                  default          No   ! ← vManage must show "up"
```

```
vSmart# show omp peers
PEER             TYPE       DOMAIN   R   I   CONNECTS FLAPS
172.16.1.1       vedge      1        0   0   1        0     ! ← vEdge1 must appear
172.16.2.1       vedge      1        0   0   1        0     ! ← vEdge2 must appear
```

### Data Plane Verification

```
vEdge1# show bfd sessions
                                      SOURCE TLOC      REMOTE TLOC
SYSTEM IP        SITE ID  STATE  COLOR   IP        COLOR   IP        PROTO    ENCAP  TX_PKTS  RX_PKTS
10.10.10.12      200      up     default 172.16.1.1 default 172.16.2.1 ipsec    ipv4   ...      ...    ! ← vEdge2 BFD must be "up"
```

```
vEdge2# show ip route vpn 1
Codes: C - connected, S - static, O - OSPF, B - BGP, R - RIP, I - IGRP, L - Local,
       ~ - next-hop attribute, D - EIGRP, EX - EIGRP external
VPN   PREFIX                    NEXTHOP          PROTOCOL    COLOR    UPTIME
1     192.168.1.0/24            172.16.1.1        omp         default  00:05:12  ! ← site 1 LAN via OMP
1     192.168.2.0/24            0.0.0.0           connected   -        00:10:00  ! ← local LAN
```

### Policy Verification

```
vEdge1# show policy from-vsmart
direction: all
details      : 1
total policy from vsmart: 2
policy #1: APP-AWARE-ROUTING         ! ← app-route policy must be present
policy #2: PREFER-SITE1-PATH         ! ← control policy reflected
```

```
vSmart# show running-config apply-policy
apply-policy
 site-list SITE2
  control-policy PREFER-SITE1-PATH out   ! ← outbound to site 2
  app-route-policy APP-AWARE-ROUTING     ! ← app-route applied
 !
 site-list SITE1
  app-route-policy APP-AWARE-ROUTING     ! ← app-route applied to site 1 too
 !
```

### End-to-End Reachability

```
vEdge2# ping vpn 1 192.168.1.1
Pinging 192.168.1.1 in VPN 1
Sending 5, 100-byte ICMP Echos to 192.168.1.1
!!!!!                                                         ! ← all 5 must succeed
Success rate is 100 percent (5/5), round-trip min/avg/max = 2/3/4 ms
```

---

## 7. Verification Cheatsheet

### System Bootstrap Verification

```
show system status
show certificate installed
show control connections
```

| Command | What to Look For |
|---------|-----------------|
| `show system status` | `system-ip`, `organization-name`, `vbond` address correct |
| `show certificate installed` | Certificate present and valid |
| `show control connections` | vSmart, vBond, vManage all show `up` state |
| `show control local-properties` | Local system-ip, site-id, org-name confirmed |

> **Exam tip:** `show control connections` is the first command to run after bootstrap. If any peer shows `connect` instead of `up`, the system block on one end is misconfigured or the organization-name doesn't match.

### OMP Routing

```
show omp peers
show omp routes
show omp tlocs
```

| Command | What to Look For |
|---------|-----------------|
| `show omp peers` | All vEdges listed under vSmart; state columns show connected=1 |
| `show omp routes` | VPN 1 prefixes from both sites visible on each vEdge |
| `show omp tlocs` | TLOC entries listing transport color and IP for each peer |
| `show ip route vpn 1` | OMP-learned routes (protocol = omp) for remote site LANs |

### BFD and Data Plane

```
show bfd sessions
show tunnel statistics
show ipsec outbound-connections
```

| Command | What to Look For |
|---------|-----------------|
| `show bfd sessions` | Remote vEdge system-ip, state=up, RX_PKTS incrementing |
| `show tunnel statistics` | Packets/bytes sent and received per IPsec tunnel |
| `show ipsec outbound-connections` | Active IPsec SAs between vEdge pairs |

> **Exam tip:** BFD only runs inside IPsec tunnels between vEdges. If `show bfd sessions` is empty, the tunnel-interface is missing or the control connection to vSmart is down — OMP must peer before BFD can form.

### Policy Verification

```
show policy from-vsmart
show running-config policy
show running-config apply-policy
```

| Command | What to Look For |
|---------|-----------------|
| `show policy from-vsmart` | Policy names present; total policy count matches what you applied |
| `show running-config policy` (vSmart) | site-list, vpn-list, sla-class, policy sequences all committed |
| `show running-config apply-policy` (vSmart) | Correct site-lists bound to correct policies with in/out direction |
| `show app-route stats` | Per-application path statistics and SLA compliance |

### Verification Commands

| Command | What to Look For |
|---------|-----------------|
| `show control connections` | All peers in `up` state |
| `show omp peers` | All vEdges connected to vSmart |
| `show bfd sessions` | Active sessions between vEdge pairs |
| `show ip route vpn 1` | OMP routes for remote site prefixes |
| `show policy from-vsmart` | Policy names installed on vEdge |
| `ping vpn 1 <remote-lan-ip>` | 100% success between site LANs |

### Common SD-WAN Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| Control connections stuck in `connect` | Organization-name mismatch or certificate missing |
| vEdge shows vBond `up` but no vSmart | vSmart tunnel-interface not configured |
| OMP peers down | Control connection to vSmart not `up` |
| BFD sessions empty | VPN 0 tunnel-interface missing on one vEdge |
| VPN 1 routes not in routing table | VPN 1 interface not configured or OMP not redistributing |
| Policy not showing on vEdge | `apply-policy` not committed on vSmart, or site-list incorrect |
| `commit` succeeds but config lost after reload | Configuration not saved — issue `commit` again |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Part A — Fabric Bootstrap

<details>
<summary>Click to view vBond Configuration</summary>

```bash
! vBond — Orchestrator: must be configured first
config
system
 host-name vBond
 system-ip 10.10.10.3
 organization-name ENCOR-LAB
 vbond 172.16.0.3 local
!
vpn 0
 interface ge0/0
  ip address 172.16.0.3/24
  tunnel-interface
   encapsulation ipsec
   allow-service all
  !
  no shutdown
 !
 ip route 0.0.0.0/0 172.16.0.254
!
commit
```
</details>

<details>
<summary>Click to view vSmart Configuration</summary>

```bash
! vSmart — Controller / OMP Route Reflector
config
system
 host-name vSmart
 system-ip 10.10.10.2
 organization-name ENCOR-LAB
 vbond 172.16.0.3
!
vpn 0
 interface eth1
  ip address 172.16.0.2/24
  tunnel-interface
   encapsulation ipsec
   allow-service all
  !
  no shutdown
 !
 ip route 0.0.0.0/0 172.16.0.254
!
commit
```
</details>

<details>
<summary>Click to view vManage Configuration</summary>

```bash
! vManage — NMS / Management Plane
config
system
 host-name vManage
 system-ip 10.10.10.1
 organization-name ENCOR-LAB
 vbond 172.16.0.3
!
vpn 0
 interface eth1
  ip address 172.16.0.1/24
  no shutdown
 !
 ip route 0.0.0.0/0 172.16.0.254
!
vpn 512
 interface eth0
  ip address 192.168.100.1/24
  no shutdown
!
commit
```
</details>

<details>
<summary>Click to view vEdge1 Configuration</summary>

```bash
! vEdge1 — Site 100 Edge Router
config
system
 host-name vEdge1
 system-ip 10.10.10.11
 site-id 100
 organization-name ENCOR-LAB
 vbond 172.16.0.3
!
vpn 0
 interface ge0/0
  ip address 172.16.1.1/24
  tunnel-interface
   encapsulation ipsec
   allow-service all
  !
  no shutdown
 !
 ip route 0.0.0.0/0 172.16.1.254
!
vpn 1
 interface ge0/1
  ip address 192.168.1.1/24
  no shutdown
 !
commit
```
</details>

<details>
<summary>Click to view vEdge2 Configuration</summary>

```bash
! vEdge2 — Site 200 Edge Router
config
system
 host-name vEdge2
 system-ip 10.10.10.12
 site-id 200
 organization-name ENCOR-LAB
 vbond 172.16.0.3
!
vpn 0
 interface ge0/0
  ip address 172.16.2.1/24
  tunnel-interface
   encapsulation ipsec
   allow-service all
  !
  no shutdown
 !
 ip route 0.0.0.0/0 172.16.2.254
!
vpn 1
 interface ge0/1
  ip address 192.168.2.1/24
  no shutdown
 !
commit
```
</details>

### Part A — Centralized Policy

<details>
<summary>Click to view vSmart Policy Configuration</summary>

```bash
! vSmart — Policy stack (configure after all vEdges are up)
config
policy
 site-list SITE1
  site-id 100
 !
 site-list SITE2
  site-id 200
 !
 vpn-list VPN1
  vpn 1
 !
 sla-class DEFAULT
  loss    5
  latency 150
  jitter  30
 !
 control-policy PREFER-SITE1-PATH
  sequence 10
   match route
    site-list SITE1
   !
   action accept
    set
     preference 200
    !
   !
  !
  default-action accept
 !
 app-route-policy APP-AWARE-ROUTING
  vpn-list VPN1
   sequence 10
    match
     source-ip 0.0.0.0/0
     destination-ip 0.0.0.0/0
    !
    action sla-class DEFAULT
     preferred-color default
    !
   !
  !
 !
!
apply-policy
 site-list SITE2
  control-policy PREFER-SITE1-PATH out
  app-route-policy APP-AWARE-ROUTING
 !
 site-list SITE1
  app-route-policy APP-AWARE-ROUTING
 !
!
commit
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show control connections
show omp peers
show omp routes
show bfd sessions
show policy from-vsmart
ping vpn 1 192.168.1.1    ! run from vEdge2
ping vpn 1 192.168.2.1    ! run from vEdge1
```
</details>

### Part B — SD-Access Answer Key

<details>
<summary>Click to view SD-Access Architecture Answers</summary>

**Question 1 — LISP flow:**
1. Endpoint sends packet; Fabric Edge Node (xTR/ITR) receives it in VPN/VN context
2. ITR has no LISP mapping for destination EID — sends LISP Map-Request to Control Plane Node (LISP MS/MR)
3. CPN looks up EID-to-RLOC mapping; responds with Map-Reply containing destination RLOC (IP of remote Fabric Edge Node)
4. ITR encapsulates original packet in VXLAN-GPO with source=local RLOC, destination=remote RLOC
5. VXLAN packet traverses IS-IS underlay to remote Fabric Edge Node (ETR/xTR)
6. ETR decapsulates VXLAN, delivers original packet to destination endpoint

**Question 2 — SGT enforcement:**
- SGT 20 (Guest) assigned at ingress by Fabric Edge Node connected to Guest endpoint
- SGT travels in VXLAN Group Policy Option (GPO) header — the `G` bit set, SGT in 16-bit field
- At egress Fabric Edge Node, Catalyst Center policy contract: SGT 20 → SGT 10 = deny
- Packet is dropped at the egress xTR before reaching the Finance server

**Question 3 — Brownfield fusion router:**
- A **fusion router** is placed at the Fabric Border Node
- The fabric VN subnet is leaked into the external VRF on the fusion router; external VRF routes are leaked back into the fabric VN
- In Catalyst Center: **Provision** → Fabric Domain → IP Transit → assign the External Border Node and configure the IP Transit network
- The fusion router participates in both the external routing domain and the SD-Access IP transit

**Question 4 — Border Node types:**
- **Internal Border Node**: connects fabric to another SD-Access fabric domain (SDA Transit). Use case: extending the fabric across a WAN link to a remote building.
- **External Border Node**: connects fabric to traditional/non-SD-Access networks (IP Transit). Use case: connecting SD-Access fabric to a legacy data center running traditional routing.

**Question 5 — SD-WAN vs SD-Access:**

| Dimension | SD-WAN | SD-Access |
|-----------|--------|-----------|
| Target domain | WAN / branch connectivity | Enterprise campus LAN/WLAN |
| Overlay protocol | IPsec (VPN 0 tunnels between vEdges) | VXLAN-GPO (between Fabric Nodes) |
| Control plane protocol | OMP (vSmart as route reflector) | LISP (CPN as Map-Server/Resolver) |
</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. Inject the fault first, then diagnose and fix using only show commands.

### Workflow

```bash
python3 setup_lab.py                                   # reset to known-good
python3 scripts/fault-injection/inject_scenario_01.py  # Ticket 1
python3 scripts/fault-injection/inject_scenario_02.py  # Ticket 2
python3 scripts/fault-injection/inject_scenario_03.py  # Ticket 3
python3 scripts/fault-injection/apply_solution.py      # restore
```

---

### Ticket 1 — vEdge2 Reports No Control Connections After Reboot

The NOC reports that vEdge2 came back online after a maintenance window reboot, but the monitoring dashboard shows it as disconnected. vEdge1 and all controllers appear healthy.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py`

**Success criteria:** `show control connections` on vEdge2 shows vSmart, vBond, and vManage all in `up` state. `show bfd sessions` on vEdge1 shows vEdge2 session as `up`.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `show control connections` — all entries show `connect` or empty; no `up` state
2. `show system status` — verify system-ip, organization-name, vbond address
3. `show certificate installed` — check certificate validity
4. Compare `show running-config system` against expected values:
   - organization-name must be exactly `ENCOR-LAB` (case-sensitive)
   - vbond must be `172.16.0.3`
5. `ping vpn 0 172.16.0.3` — verify transport reachability to vBond
6. Root cause: `organization-name` has been changed to a wrong value — the fabric rejects the device because it doesn't match the expected org name

</details>

<details>
<summary>Click to view Fix</summary>

```bash
vEdge2# config
vEdge2(config)# system
vEdge2(config-system)# organization-name ENCOR-LAB
vEdge2(config-system)# commit
vEdge2# show control connections
! Verify all peers return to "up" state within 30 seconds
```
</details>

---

### Ticket 2 — Site 1 LAN Traffic Cannot Reach Site 2 LAN

A user at site 1 reports they can no longer ping servers at site 2. The SD-WAN dashboard shows both sites are connected and the control plane appears healthy. BFD sessions between vEdge1 and vEdge2 are up.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py`

**Success criteria:** `ping vpn 1 192.168.2.1` from vEdge1 succeeds with 100% success rate.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `show omp peers` — vSmart and vEdges all connected
2. `show ip route vpn 1` on vEdge1 — check if 192.168.2.0/24 (site 2 LAN) is present
3. If route is missing: `show omp routes` on vSmart — check if site 2 routes are in OMP table
4. `show running-config policy vpn-list VPN1` on vSmart — verify VPN 1 is in the vpn-list
5. Root cause: vpn-list VPN1 has been changed to reference `vpn 2` instead of `vpn 1` — the app-route policy no longer applies to the correct VPN, and routes are not being distributed

</details>

<details>
<summary>Click to view Fix</summary>

```bash
vSmart# config
vSmart(config)# policy
vSmart(config-policy)# vpn-list VPN1
vSmart(config-vpn-list-VPN1)# no vpn 2
vSmart(config-vpn-list-VPN1)# vpn 1
vSmart(config-vpn-list-VPN1)# commit
vSmart# show running-config policy vpn-list VPN1
! Verify "vpn 1" is present
vEdge1# show ip route vpn 1
! Verify 192.168.2.0/24 appears as OMP route
```
</details>

---

### Ticket 3 — Application Performance Degraded on Both Sites Despite BFD Sessions Up

Users on both sites report high latency and jitter on business-critical applications. The monitoring team confirms BFD sessions are active, but application-aware routing doesn't appear to be steering traffic. `show policy from-vsmart` on both vEdges returns empty.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py`

**Success criteria:** `show policy from-vsmart` on vEdge1 and vEdge2 lists both `APP-AWARE-ROUTING` and `PREFER-SITE1-PATH`. Application latency returns to normal.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `show policy from-vsmart` on vEdge1 and vEdge2 — empty (no policies)
2. `show running-config apply-policy` on vSmart — verify apply-policy block exists
3. If apply-policy block is missing or site-list references are wrong, policies will not be distributed
4. `show running-config policy` on vSmart — confirm policy definitions are committed
5. Root cause: `apply-policy` block has been removed from vSmart — policy definitions exist but nothing binds them to site-lists and pushes them to vEdges

</details>

<details>
<summary>Click to view Fix</summary>

```bash
vSmart# config
vSmart(config)# apply-policy
vSmart(config-apply-policy)# site-list SITE2
vSmart(config-apply-policy-site-list-SITE2)# control-policy PREFER-SITE1-PATH out
vSmart(config-apply-policy-site-list-SITE2)# app-route-policy APP-AWARE-ROUTING
vSmart(config-apply-policy)# site-list SITE1
vSmart(config-apply-policy-site-list-SITE1)# app-route-policy APP-AWARE-ROUTING
vSmart(config-apply-policy)# commit
vEdge1# show policy from-vsmart
! Both APP-AWARE-ROUTING and PREFER-SITE1-PATH must appear
```
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] All five Viptela devices have a complete `system` block (host-name, system-ip, site-id where applicable, organization-name, vbond)
- [ ] vBond `vbond ... local` is configured and tunnel-interface is up on ge0/0
- [ ] vSmart tunnel-interface is up on eth1
- [ ] vEdge1 and vEdge2 have tunnel-interface on VPN 0 ge0/0
- [ ] `show control connections` shows vSmart, vBond, and vManage as `up` on both vEdges
- [ ] `show omp peers` on vSmart lists both vEdge1 and vEdge2
- [ ] `show bfd sessions` shows active sessions between vEdge1 and vEdge2
- [ ] VPN 1 LAN interfaces configured on both vEdges
- [ ] `show ip route vpn 1` on each vEdge shows remote site LAN via OMP
- [ ] `ping vpn 1` between sites succeeds 100%
- [ ] vSmart policy: site-lists, vpn-list, sla-class, control-policy, app-route-policy all committed
- [ ] `apply-policy` bound to correct site-lists with correct directions
- [ ] `show policy from-vsmart` on both vEdges shows both policy names
- [ ] Part B SD-Access questions answered (all 5 questions)

### Troubleshooting

- [ ] Ticket 1 injected, diagnosed (organization-name mismatch), and fixed
- [ ] Ticket 2 injected, diagnosed (vpn-list VPN reference wrong), and fixed
- [ ] Ticket 3 injected, diagnosed (apply-policy missing), and fixed
- [ ] `setup_lab.py` and `apply_solution.py` run successfully to confirm restore path works
