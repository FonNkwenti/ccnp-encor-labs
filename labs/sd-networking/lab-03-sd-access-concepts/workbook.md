# Lab 03: SD-Access Architecture and Campus Integration

## Table of Contents

1. [Concepts & Skills Covered](#1-concepts--skills-covered)
2. [Architecture Overview](#2-architecture-overview)
3. [Study Environment](#3-study-environment)
4. [Prerequisites](#4-prerequisites)
5. [Lab Challenge: Core Implementation](#5-lab-challenge-core-implementation)
6. [Verification & Analysis](#6-verification--analysis)
7. [Verification Cheatsheet](#7-verification-cheatsheet)
8. [Solutions (Spoiler Alert!)](#8-solutions-spoiler-alert)
9. [Troubleshooting Scenarios](#9-troubleshooting-scenarios)
10. [Lab Completion Checklist](#10-lab-completion-checklist)

---

## 1. Concepts & Skills Covered

**Exam Objective:** 1.3 — Explain the working principles of the Cisco SD-Access solution; 1.3.a — SD-Access control and data plane elements; 1.3.b — Traditional campus interoperating with SD-Access (SD-WAN and SD-Access — CCNP ENCOR 350-401)

This is a reference workbook. SD-Access requires Catalyst Center and Cisco ISE — neither is available in EVE-NG on this platform. Instead of CLI tasks, this lab builds the architectural understanding required to answer exam questions on SD-Access fabric roles, encapsulation, and campus integration. Mastery of these concepts is assessed directly in the 350-401 blueprint and forms the conceptual foundation for the capstone labs.

---

### SD-Access Architecture — Three-Layer Model

SD-Access is a policy-based network architecture that automates the deployment and management of campus networks. It separates the network into three distinct planes:

**Underlay Network**

The underlay is a traditional routed Layer 3 network used exclusively for transporting the VXLAN overlay. SD-Access underlay uses IS-IS as the routing protocol (not OSPF or EIGRP) because IS-IS is protocol-independent and can route over any network layer. Every device in the fabric must have IP reachability to every other device at the underlay layer.

Key underlay characteristics:
- IS-IS for loop-free, fast-converging L3 routing
- No Spanning Tree Protocol — all links routed, not bridged
- Optimized MTU (typically 9100 bytes) for VXLAN overhead (50+ byte header)
- PnP (Plug and Play) or LAN Automation for zero-touch provisioning

**Overlay Network**

The overlay carries end-user traffic encapsulated in VXLAN-GPO (Virtual Extensible LAN with Group Policy Option). Each virtual network (VN) maps to a unique VNI (VXLAN Network Identifier), providing Layer 2 and Layer 3 segmentation across the routed underlay.

```
VXLAN-GPO Frame Structure:
┌────────────────────────────────────────────────────────────────┐
│  Outer Ethernet  │  Outer IP (Underlay) │  UDP 4789  │  VXLAN  │
│     Header       │  RLOC → RLOC         │            │  Header │
├────────────────────────────────────────────────────────────────┤
│  VNI (24-bit)  │  SGT (16-bit, GPO)  │  Inner Ethernet + Payload│
└────────────────────────────────────────────────────────────────┘
```

The GPO (Group Policy Option) field carries the SGT (Scalable Group Tag), a 16-bit value that encodes the security policy group of the originating endpoint. This allows policy enforcement anywhere in the fabric without relying on IP addresses.

**Control Plane**

SD-Access uses LISP (Locator/ID Separation Protocol) as its control plane for host tracking. LISP separates endpoint identity (EID — the endpoint's IP/MAC address) from its location (RLOC — the IP address of the fabric node hosting the endpoint).

```
LISP Roles:
┌─────────────────────────────────────────────────────────────┐
│ Map Server (MS)   — stores EID-to-RLOC mappings             │
│ Map Resolver (MR) — answers map requests from ITRs          │
│ ITR (Ingress TR)  — encapsulates traffic, queries MS/MR     │
│ ETR (Egress TR)   — decapsulates traffic, registers EIDs    │
│ xTR               — device acting as both ITR and ETR       │
│ PxTR              — proxy xTR for non-LISP sites            │
└─────────────────────────────────────────────────────────────┘
```

When an endpoint moves or connects, the fabric Edge Node (acting as xTR) registers its EID with the Control Plane Node (acting as MS/MR). Traffic to that endpoint is resolved via a LISP map-request/reply exchange before VXLAN encapsulation.

---

### Fabric Node Roles

Every physical device in an SD-Access fabric performs one or more of these roles:

| Role | Function | LISP Role | Typical Device |
|------|----------|-----------|----------------|
| **Control Plane Node (CPN)** | Hosts the LISP Map Server and Map Resolver. Maintains the EID-to-RLOC database for the entire fabric. All Edge Nodes register their connected endpoints here. | MS + MR | Catalyst 9000 switch (dedicated) |
| **Fabric Border Node** | Connects the SD-Access fabric to external networks. Three subtypes: External Border (connects to WAN/internet), Internal Border (connects to core/data center), Default Border (catch-all). Performs SGT-to-IP translation for non-fabric endpoints. | PxTR | Catalyst 9000 switch |
| **Fabric Edge Node** | Connects endpoints (wired users, servers) to the fabric. Responsible for endpoint registration (ETR function) and traffic encapsulation/decapsulation (xTR). Applies SGT via 802.1X/MAB via ISE. | xTR | Catalyst 9000 switch |
| **Fabric WLC** | Integrates wireless clients into the SD-Access fabric. The AP CAPWAP tunnel terminates at the WLC, which registers wireless clients as EIDs. Traffic enters the fabric as if from a wired Edge Node. | xTR | Catalyst 9800 |
| **Intermediate Node** | Provides pure underlay routing — IS-IS only. Does not participate in the LISP overlay. Connects Edge Nodes to Border Nodes via the routed underlay. | None | Catalyst 9000 distribution/core |

> **Exam key:** The Control Plane Node is separate from the Data Plane. CPN handles LISP lookups; Edge Nodes handle the actual VXLAN encapsulation. This separation is fundamental to SD-Access's scalability.

---

### SGT-Based Segmentation

Scalable Group Tags (SGTs) are 16-bit values assigned to endpoints based on their identity (authentication result from ISE). SGTs replace IP-based ACLs for policy enforcement in SD-Access.

```
SGT Policy Flow:
1. Endpoint connects to Edge Node
2. 802.1X / MAB authentication → ISE assigns SGT (e.g., SGT 10 = "Employee")
3. Edge Node tags the VXLAN-GPO header with SGT 10
4. Fabric carries the SGT transparently end-to-end
5. Destination Edge Node enforces SGACL: "Can SGT 10 reach SGT 20?"
6. Catalyst Center distributes SGACL policy to all enforcement points
```

SGT advantages over IP-based ACLs:
- Policy follows the user, not the IP address
- Single policy matrix instead of per-VLAN ACLs
- Scales to large campus with centralized Catalyst Center management
- Works across roaming (wireless → wired) without policy changes

---

### Traditional Campus Interoperability (Blueprint 1.3.b)

SD-Access can coexist with existing "brownfield" campus networks that do not run LISP/VXLAN. Integration relies on specific node types and transit mechanisms.

**Fusion Router**

The fusion router connects the SD-Access fabric to external network segments (traditional VLANs, routed campus core, WAN). It acts as a routing boundary between the fabric VNs (VRFs) and the external routing domain.

```
                    ┌──────────────────────────────────┐
                    │      SD-Access Fabric            │
                    │                                  │
         VN-A (VRF) │      Border Node                │
         ──────────►│      (External)                 │── Trunk ──► Fusion Router
         VN-B (VRF) │                                  │
                    └──────────────────────────────────┘
                                                         │
                                              ┌──────────┴──────────┐
                                              │   Traditional Campus │
                                              │   VLANs / VRFs       │
                                              └──────────────────────┘
```

Each VN in the fabric maps to a sub-interface (dot1q) on the fusion router. The fusion router redistributes routes between the fabric VRFs and the traditional routing domain.

**Transit Options**

| Transit Type | Description | Use Case |
|-------------|-------------|----------|
| **IP Transit** | Standard routing between fabric and external via Border Node. No VXLAN/LISP beyond the Border. | WAN, data center, internet |
| **SD-Access Transit** | Extends VXLAN tunnel across WAN to connect fabric islands. LISP control plane spans sites. Requires SDA-capable WAN. | Multi-site campus over MPLS/SD-WAN |
| **SDA over SD-WAN** | SD-Access fabric uses SD-WAN as the WAN transport. SD-WAN provides SLA-aware transport; SD-Access provides SGT policy. | Enterprise campus + branch integration |

**Brownfield Deployment Considerations**

When deploying SD-Access into an existing campus:
- Non-fabric VLANs coexist until migrated — fusion router bridges the gap
- SGT enforcement cannot extend to non-fabric devices (no VXLAN GPO)
- ISE must be pre-deployed for 802.1X — this is a prerequisite
- Catalyst Center requires DNA Advantage license tier
- LISP/VXLAN underlay changes may require hardware upgrade (Catalyst 9000 family)

---

### Catalyst Center Workflows

Catalyst Center (formerly DNA Center) provides the single-pane-of-glass for SD-Access. Its workflow is organized into four phases:

| Phase | Function | Key Actions |
|-------|----------|-------------|
| **Design** | Define the network hierarchy and settings | Create sites, buildings, floors; configure network settings (DNS, NTP, AAA, DHCP) per site |
| **Policy** | Define segmentation and access policy | Create Virtual Networks (VNs / VRFs), define Scalable Groups (SGTs), create Group-Based Access Control (GBAC) policy contracts |
| **Provision** | Deploy fabric and push configs to devices | Discover devices, assign to fabric roles (CPN, Border, Edge), add to fabric domain, push underlay/overlay config |
| **Assurance** | Monitor health and detect issues | Client health score, device health, network health timeline, issue correlation, AI/ML-driven root cause analysis |

> **Exam key:** Catalyst Center does NOT replace the CLI — it generates and pushes CLI configurations to devices. Show commands run via SSH still work. Assurance uses telemetry (gRPC streaming) rather than SNMP polling.

---

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| SD-Access architecture analysis | Identify underlay/overlay/control plane separation and explain each layer's role |
| Fabric role identification | Assign correct roles (CPN, Border, Edge, WLC) given a topology description |
| LISP operation | Trace EID registration, map-request/reply exchange, and VXLAN encapsulation flow |
| SGT policy tracing | Follow an endpoint from authentication through SGT assignment to policy enforcement |
| Campus integration design | Identify correct transit type and fusion router placement for brownfield integration |
| Exam question interpretation | Map scenario descriptions to the correct SD-Access architecture component |

---

## 2. Architecture Overview

> This lab has no physical topology — SD-Access requires Catalyst Center + ISE, which are not available in EVE-NG. The diagram below shows the logical SD-Access fabric architecture.

### SD-Access Logical Fabric Architecture

```
                         ┌──────────────────────────────┐
                         │       Catalyst Center        │
                         │  (Management + Orchestration) │
                         │  Design │ Policy │ Provision  │
                         │         │ Assurance            │
                         └──────────────────────────────┘
                                        │ REST API / gRPC
                         ┌──────────────┴───────────────┐
                         │         Cisco ISE             │
                         │  (AAA / SGT Assignment / RBAC)│
                         └──────────────────────────────┘
                                        │ pxGrid / RADIUS
             ┌──────────────────────────┼───────────────────────────┐
             │                          │                           │
    ┌────────┴─────────┐     ┌──────────┴──────────┐     ┌─────────┴──────────┐
    │  Control Plane   │     │    Border Node      │     │   Fabric WLC       │
    │     Node (CPN)   │     │  (External/Default) │     │  (Wireless Fabric) │
    │  LISP MS + MR    │     │  Gateway to WAN/DC  │     │  AP anchor for SGT │
    └────────┬─────────┘     └──────────┬──────────┘     └─────────┬──────────┘
             │                          │                           │
             │              ┌───────────┴───────────────────────────┘
             │              │          IS-IS Underlay Fabric
             │    ┌─────────┴───────────────────────────────┐
             │    │         Intermediate Nodes              │
             │    │    (Pure underlay / IS-IS routing)      │
             │    └─────────┬────────────────┬──────────────┘
             │              │                │
    ┌─────────┴────────┐    │    ┌───────────┴──────────┐
    │  Fabric Edge     │◄───┘    │  Fabric Edge Node    │
    │  Node (xTR)      │         │  (xTR)               │
    │  EID Registration│         │  EID Registration    │
    │  VXLAN xTR       │         │  VXLAN xTR           │
    └──────────────────┘         └──────────────────────┘
          │                              │
    ┌─────┴──────┐               ┌───────┴──────┐
    │  Wired     │               │  Wireless    │
    │  Endpoints │               │  Clients     │
    │ (SGT via   │               │  (SGT via    │
    │  802.1X)   │               │  WLC/ISE)    │
    └────────────┘               └──────────────┘
```

### SD-Access vs Traditional Campus

```
Traditional Campus:                SD-Access Campus:
┌─────────────────┐               ┌─────────────────────────────┐
│ Core Switch     │               │ Border Node (External/Int)  │
│ (L3, VLANs)    │               │ (Connects fabric to WAN/DC) │
└────────┬────────┘               └───────────┬─────────────────┘
         │ STP                                │ IS-IS (no STP)
┌────────┴────────┐               ┌───────────┴─────────────────┐
│ Dist Switch     │               │ Intermediate/Edge Nodes     │
│ (VLAN trunk)   │               │ (VXLAN xTR, LISP ETR/ITR)   │
└────────┬────────┘               └───────────┬─────────────────┘
         │ Access VLANs                        │ VXLAN-GPO tunnels
┌────────┴────────┐               ┌───────────┴─────────────────┐
│ Access Switch   │               │ Fabric Edge Nodes           │
│ (Port VLAN)    │               │ (EID registration, SGT)     │
└─────────────────┘               └─────────────────────────────┘
Policy: IP ACLs per VLAN           Policy: SGT matrix, central Catalyst Center
```

### Brownfield Integration — Fusion Router Pattern

```
                    ┌──────────────────────────────────┐
                    │       SD-Access Fabric            │
                    │                                  │
                    │  ┌──────────────────────────┐   │
                    │  │  External Border Node    │   │
                    │  │  (VN-A VRF, VN-B VRF)  │   │
                    │  └──────────────┬───────────┘   │
                    └─────────────────┼────────────────┘
                                      │ 802.1Q trunk (sub-interfaces per VN)
                              ┌───────┴───────┐
                              │  Fusion Router │
                              │  VN-A ↔ VRF-A │
                              │  VN-B ↔ VRF-B │
                              └───────┬───────┘
                                      │ Traditional routing
                              ┌───────┴───────────────────┐
                              │  Traditional Campus Core   │
                              │  (VLANs, OSPF, no LISP)  │
                              └───────────────────────────┘
```

---

## 3. Study Environment

> This lab requires no EVE-NG topology. All tasks are conceptual — study architecture diagrams, trace packet flows, and answer exam-style questions.

**What you need:**
- This workbook
- Access to Cisco dCloud SD-Access sandbox (optional — for Catalyst Center GUI exploration)
- Cisco DevNet SD-Access learning labs (optional)

**Time estimate:** 60 minutes

**No console access required.** There are no devices to configure.

---

## 4. Prerequisites

**Concepts you should already understand before starting:**

- SD-WAN architecture (labs 00–02) — SD-Access and SD-WAN are complementary but separate solutions
- VRF fundamentals — SD-Access Virtual Networks map directly to VRFs
- 802.1X/MAB authentication flow — ISE integration is required for SGT assignment
- Basic VXLAN concepts — VTEP, VNI, encapsulation overhead
- BGP fundamentals — LISP uses similar concepts (EID = prefix, RLOC = next-hop)

**What is NOT pre-configured:**

- No topology exists for this lab — it is a reference-only workbook
- No initial device configuration
- No routing protocols to verify

---

## 5. Lab Challenge: Core Implementation

> This is a reference lab. Tasks are conceptual — study the architecture, trace the flows, and answer the exam-style questions below. No CLI configuration is required.

### Task 1: SD-Access Architecture Mapping

- Study Section 1's three-layer model (underlay, overlay, control plane) until you can draw it from memory.
- For each layer, identify: the protocol used, the purpose it serves, and what would break if that layer failed.
- List the five fabric node roles and describe what each one does in one sentence.

**Verification:** Answer without referring to notes — "What does a Fabric Edge Node do, and what LISP role does it perform?"

---

### Task 2: LISP Host Tracking Flow

- Trace the sequence of events when a new endpoint (IP: 10.1.1.100) connects to a Fabric Edge Node and sends its first packet to 10.2.2.200 on a remote Edge Node.
- Identify which devices act as ETR, ITR, MS, and MR during this exchange.
- Explain what is stored in the LISP mapping database and where it is stored.
- Describe what happens when the endpoint roams to a different Edge Node.

**Verification:** Draw the LISP map-register → map-request → map-reply → data encapsulation sequence as a timeline with device labels.

---

### Task 3: SGT Policy Tracing

- An employee connects via 802.1X and ISE assigns SGT 10 ("Employee"). A printer is assigned SGT 30 ("Printers").
- Trace the SGT assignment from authentication through to the VXLAN-GPO header.
- Identify where the SGACL policy is enforced (source Edge Node, destination Edge Node, or both).
- Describe how the policy would change if the employee moved from wired to wireless.

**Verification:** Answer — "At which point in the packet flow is the VXLAN-GPO SGT field written, and which device enforces the SGACL?"

---

### Task 4: Fabric Role Identification

Given the following topology description, identify the role each device should be assigned:

- SW-A: Connected to WAN router, has routes to external internet and data center
- SW-B: Hosts the LISP map server/resolver database, no end users connected
- SW-C and SW-D: Connect access-layer devices (PCs, IP phones, printers) via access ports
- SW-E: Provides backbone switching between SW-A, SW-B, SW-C, and SW-D with no user ports
- WLC-1: Terminates CAPWAP from 50 APs across the building

Assign each device its SD-Access fabric role and explain your reasoning.

**Verification:** Compare your assignments against the Section 8 solutions.

---

### Task 5: Brownfield Integration Design

A university has an existing campus with 200 VLANs managed via traditional trunking and OSPF. They want to deploy SD-Access in the new building while keeping existing buildings operational.

- Identify which transit type is most appropriate.
- Describe the role and placement of the fusion router.
- Explain what policy limitations exist for endpoints in the traditional buildings.
- List three prerequisites that must be in place before deploying SD-Access fabric nodes.

**Verification:** Answer — "What device bridges the policy gap between the SD-Access fabric VNs and the traditional campus VLANs, and how does it do it?"

---

### Task 6: Catalyst Center Workflow Sequencing

A network engineer is deploying SD-Access in a new campus site. Place the following actions in the correct Catalyst Center workflow order:

1. Define Scalable Groups and assign policy contracts between them
2. Add Catalyst Center to Cisco ISE as a pxGrid subscriber
3. Create a building and floor in the network hierarchy
4. Enable the fabric domain and assign devices to fabric roles
5. Configure NTP and DNS settings for the site
6. Run the Path Trace tool to verify end-to-end connectivity
7. Discover devices using IP range discovery
8. Create Virtual Networks (VNs) for Employee and Guest traffic

**Verification:** Correct sequence matches Section 8 solution. Identify which Catalyst Center workflow phase each action belongs to.

---

### Task 7: SD-WAN vs SD-Access Comparison

This question type appears frequently on the 350-401 exam. Compare the two architectures:

- For each dimension in the table below, fill in the correct answer for both SD-WAN and SD-Access:

| Dimension | SD-WAN | SD-Access |
|-----------|--------|-----------|
| Primary use case | ? | ? |
| Management platform | ? | ? |
| Data plane encapsulation | ? | ? |
| Control plane protocol | ? | ? |
| Policy distribution | ? | ? |
| Key hardware requirement | ? | ? |
| What it replaces | ? | ? |

**Verification:** All 7 rows completed correctly. Check against Section 8 solutions.

---

## 6. Verification & Analysis

> No CLI output to verify in a reference lab. This section contains concept-verification questions that confirm deep understanding.

### Architecture Understanding

**Q: Why does SD-Access use IS-IS for the underlay instead of OSPF?**

Expected answer: IS-IS is protocol-independent (can route IPv4, IPv6, or MAC-based addresses), has faster convergence characteristics, and aligns with Cisco's LAN Automation tooling. OSPF is also technically feasible but IS-IS is the SD-Access design standard. IS-IS runs directly over Layer 2 (not IP), so it can bootstrap the underlay before IP addressing is finalized.

```
Comparison:
IS-IS underlay:  L2 PDUs → no IP adjacency needed to start → supports LAN Automation bootstrap
OSPF underlay:   IP required → manual IP assignment needed before adjacency → slower ZTP
```

**Q: What happens to traffic flow if the Control Plane Node goes offline?**

Expected answer: New endpoint registrations and LISP map lookups will fail. Existing flows with cached LISP mappings continue until the cache expires (typically 60 seconds for negative cache, longer for active mappings). Endpoints that have been communicating recently will continue briefly; new endpoints or roaming endpoints cannot be reached. This is why production deployments use redundant CPN pairs. ! ← single CPN = single point of failure (exam trap)

**Q: How is a Scalable Group Tag (SGT) carried end-to-end?**

Expected answer: The Edge Node writes the SGT into the VXLAN-GPO Group Policy field during encapsulation. The 16-bit value travels inside the VXLAN header across the underlay. At the destination Edge Node, the SGACL is evaluated before decapsulating and forwarding to the endpoint. The SGT is transparent to intermediate/underlay devices. ! ← SGT is in the VXLAN header, not the inner frame

---

### Fabric Role Verification

**Q: What is the difference between an External Border Node and an Internal Border Node?**

```
External Border Node:                   Internal Border Node:
─────────────────────────────────────   ──────────────────────────────────────────
Connects fabric to untrusted external   Connects fabric to known trusted internal
networks (internet, WAN provider)       networks (data center, server farm)
Default route only (0.0.0.0/0)          Specific routes for internal subnets
SGT → DMVPN/MPLS (loses SGT)           Can maintain SGT via TrustSec inline
Default gateway for unknown dests       Named internal routing handoff
```
! ← exam asks which border type provides the default route to internet — always External Border

**Q: Can a single physical switch perform multiple fabric roles simultaneously?**

Expected answer: Yes. In small deployments, a single Catalyst 9000 can be CPN + Border Node simultaneously. Edge Nodes typically run as pure xTRs. Fabric WLC is always separate hardware. Intermediate Nodes are pure underlay and cannot combine with overlay roles. ! ← combining CPN + Border is common in small sites, but not recommended at scale

---

### Campus Integration Verification

**Q: A traditional campus router connects to the SD-Access fabric via the fusion router. An SD-Access endpoint (SGT 10) sends traffic to a traditional campus server. What policy is applied?**

```
SD-Access Endpoint  →  Edge Node  →  Border Node  →  Fusion Router  →  Traditional Server
     (SGT 10)           (VXLAN)       (decap, VRF)    (route inter-VRF)   (no SGT)
Policy applied:        SGACL at       None (no SGT    ACL on Fusion     None
                     dest Edge        beyond Border)  (if configured)
```
! ← SGT enforcement stops at the Border Node — traditional devices cannot enforce SGACL (exam fact)

---

## 7. Verification Cheatsheet

> These commands are shown in reference format — run these on actual Catalyst Center-managed SD-Access devices during lab or production validation.

### LISP Control Plane Verification

```
show lisp instance-id <vni> ipv4
show lisp service ipv4 map-cache
show lisp service ipv4 database
show lisp session
```

| Command | What to Look For |
|---------|-----------------|
| `show lisp instance-id <vni> ipv4` | EID-table, RLOC mapping count, locator status |
| `show lisp service ipv4 map-cache` | Cached EID-to-RLOC entries on Edge Nodes |
| `show lisp service ipv4 database` | Locally registered EIDs (Edge Node → shows connected endpoints) |
| `show lisp session` | Active LISP sessions between Edge Nodes and CPN |

> **Exam tip:** `show lisp service ipv4 database` is run on the ETR (Edge Node) and shows what that node has registered. `show lisp service ipv4 map-cache` is run on the ITR and shows what it has learned.

---

### VXLAN / Fabric Overlay Verification

```
show nve peers
show nve vni
show vxlan interface
show tunnel interface nve1
```

| Command | What to Look For |
|---------|-----------------|
| `show nve peers` | Active VTEP peers with state "UP", RLOC addresses |
| `show nve vni` | VNI-to-VRF/BD mapping, MCAST mode vs IR (ingress replication) |
| `show vxlan interface` | VTEP source IP, VNI assignments per interface |

> **Exam tip:** Ingress Replication (IR/unicast) mode is used in SD-Access VXLAN — NOT multicast. This is the opposite of data center VXLAN defaults.

---

### SGT and Policy Verification

```
show cts role-based sgt-map
show cts role-based permissions
show cts interface brief
show platform software fed switch active security-fed sgacl
```

| Command | What to Look For |
|---------|-----------------|
| `show cts role-based sgt-map` | IP-to-SGT mappings on the local device |
| `show cts role-based permissions` | SGACL policy matrix (source SGT → dest SGT → ACL name) |
| `show cts interface brief` | TrustSec state per interface — CTS enabled, SGT propagation mode |

---

### Catalyst Center / Fabric Status

```
show sdaccess fabric device-tracking database
show ip route vrf <vn-vrf>
show fabric forwarding module l2 address-table
show fabric forwarding rib l3 route-table
```

| Command | What to Look For |
|---------|-----------------|
| `show sdaccess fabric device-tracking database` | All known endpoints with SGT and RLOC |
| `show ip route vrf <vn-vrf>` | Routes within a specific Virtual Network |

---

### Common SD-Access Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| Endpoints cannot communicate within the same VN | LISP map-request failing — CPN unreachable or EID not registered |
| New endpoint unreachable, existing flows work | Control Plane Node down — cache still valid, new lookups fail |
| SGT enforcement not working | SGACL policy not distributed by Catalyst Center — check Provision step |
| Traffic not routed between VNs | Fusion router not configured, or VN-to-VRF mapping missing on Border Node |
| WLC clients cannot access fabric resources | Fabric WLC not added to fabric domain in Catalyst Center |
| IS-IS adjacency not forming | MTU mismatch — underlay MTU must be ≥9100 for VXLAN overhead |
| Catalyst Center cannot provision device | Device not discovered, or wrong platform (non-Catalyst 9000) |
| SGT not carried to traditional campus | Expected behavior — SGT stops at Border Node; fusion router uses IP ACLs |

---

## 8. Solutions (Spoiler Alert!)

> Review these only after completing the tasks in Section 5.

### Task 4: Fabric Role Identification — Solution

<details>
<summary>Click to view Role Assignments</summary>

| Device | Assigned Role | Reasoning |
|--------|--------------|-----------|
| SW-A | External Border Node | Connects to WAN router and external internet/DC. Handles IP Transit. |
| SW-B | Control Plane Node (CPN) | Hosts LISP MS/MR, no end users. Dedicated to control plane database. |
| SW-C, SW-D | Fabric Edge Nodes | Connect end users via access ports. Act as xTR (ETR + ITR). Register EIDs to CPN. |
| SW-E | Intermediate Node | No user ports, pure underlay (IS-IS). Connects other fabric nodes. |
| WLC-1 | Fabric WLC | Terminates CAPWAP, registers wireless EIDs, applies SGT to wireless clients. |

</details>

---

### Task 5: Brownfield Integration Design — Solution

<details>
<summary>Click to view Integration Design</summary>

**Transit type:** IP Transit — standard routing between SD-Access fabric and traditional campus via Border Node.

**Fusion router placement:** Between the SD-Access External Border Node (connected via 802.1Q trunk with sub-interfaces per VN) and the traditional campus core router.

**Policy limitations:** Endpoints in traditional buildings cannot receive or enforce SGT-based policy. The SGACL stops at the Border Node. The fusion router can apply traditional IP ACLs, but SGT value is lost.

**Three prerequisites:**
1. Cisco ISE deployed and integrated with Catalyst Center (required for 802.1X and SGT assignment)
2. Catalyst Center deployed with DNA Advantage license
3. Catalyst 9000 hardware at fabric node positions (Edge, Border, CPN require Catalyst 9000 series)

</details>

---

### Task 6: Catalyst Center Workflow Sequence — Solution

<details>
<summary>Click to view Correct Sequence</summary>

```
Phase       Step  Action
──────────────────────────────────────────────────────────────────────
Design        2   Add Catalyst Center to ISE as pxGrid subscriber (prerequisite)
Design        3   Create building and floor in network hierarchy
Design        5   Configure NTP and DNS settings for the site
Policy        8   Create Virtual Networks (VNs) for Employee and Guest
Policy        1   Define Scalable Groups and assign policy contracts
Provision     7   Discover devices using IP range discovery
Provision     4   Enable fabric domain and assign devices to fabric roles
Assurance     6   Run Path Trace to verify end-to-end connectivity
```

Note: ISE integration (step 2) is technically done before Design but within the Catalyst Center setup workflow. Discover (step 7) can happen after Design but must precede Provision.

</details>

---

### Task 7: SD-WAN vs SD-Access Comparison — Solution

<details>
<summary>Click to view Completed Comparison Table</summary>

| Dimension | SD-WAN | SD-Access |
|-----------|--------|-----------|
| Primary use case | WAN connectivity between branches over multiple transports | Campus LAN segmentation, policy, and automation |
| Management platform | vManage (Catalyst SD-WAN Manager) | Catalyst Center (formerly DNA Center) |
| Data plane encapsulation | IPsec (between vEdges) | VXLAN-GPO (between fabric nodes) |
| Control plane protocol | OMP (Overlay Management Protocol) | LISP (Locator/ID Separation Protocol) |
| Policy distribution | vSmart pushes control/data policies to vEdges | Catalyst Center pushes SGACL/VN config to fabric nodes |
| Key hardware requirement | vEdge / Catalyst SD-WAN router | Catalyst 9000 switches + ISE + Catalyst Center |
| What it replaces | Traditional MPLS/VPN, DMVPN, iWAN | Traditional campus VLAN-based access + IBNS/TrustSec silos |

</details>

---

## 9. Troubleshooting Scenarios

> Reference-format labs use scenario-based questions instead of fault injection scripts. Read each scenario, diagnose the root cause, and explain the fix before revealing the answer.

---

### Ticket 1 — New Employees Cannot Reach the Internet After SD-Access Deployment

The network team has successfully deployed SD-Access fabric in the new building. Wired employees authenticate via 802.1X and receive SGT 10. They can reach other employees within the fabric (same VN) but cannot reach the internet or the traditional data center.

**Success criteria:** Employees with SGT 10 can reach the internet and data center servers.

<details>
<summary>Click to view Diagnosis Steps</summary>

Work through these questions:
1. Can employees reach other employees in the same VN? (If yes, LISP and VXLAN are working.)
2. Can the Border Node ping the fusion router?
3. Is there a default route configured on the fusion router pointing toward the internet/WAN?
4. Is the VN-to-VRF mapping configured on the External Border Node?
5. Is there a sub-interface on the fusion router for the Employee VN?

Key command on Border Node: `show ip route vrf <employee-vn-vrf>`
Key command on fusion router: `show ip route` and `show ip interface brief`

</details>

<details>
<summary>Click to view Fix</summary>

**Root cause:** The fusion router's sub-interface for the Employee VN was not configured, or the External Border Node's IP Transit configuration is missing.

**Fix:**
1. On the External Border Node: configure IP Transit in Catalyst Center (Provision → Fabric → Border Node → IP Transit settings).
2. On the fusion router: add sub-interface for the Employee VN's VRF with the correct 802.1Q encapsulation matching the Border Node trunk.
3. Add a default route from the fusion router toward the internet gateway.
4. Verify: Employee endpoints should receive a default route via LISP/OMP from the Border Node.

**Key fact:** SGT does not affect routing. If the routing path (Border → Fusion → Internet) is correct, SGT 10 traffic flows regardless of SGACL. The routing issue is independent of policy.

</details>

---

### Ticket 2 — Wireless Clients See Degraded Experience After Fabric WLC Addition

After integrating the Catalyst 9800 Fabric WLC into the SD-Access domain, wireless clients authenticate successfully and receive an IP address. However, client health scores in Catalyst Center Assurance show "Poor" for all wireless clients, and some clients intermittently drop traffic.

**Success criteria:** Wireless clients show "Good" health in Catalyst Center Assurance; traffic is stable.

<details>
<summary>Click to view Diagnosis Steps</summary>

Work through these questions:
1. Is the WLC added to the fabric domain in Catalyst Center (Provision → Fabric → Wireless)?
2. Are the APs connected to Edge Nodes (not Intermediate Nodes)?
3. Is the underlay MTU set to ≥9100 on links between APs' Edge Nodes and the WLC's uplink?
4. Is the CAPWAP tunnel MTU aligned with the VXLAN overhead?
5. Are wireless clients receiving the correct SGT from ISE?

Key check: `show ap config general <ap-name>` — CAPWAP state should be "Joined"
Key check: `show nve peers` on the WLC's fabric Edge Node — should show peer RLOCs

</details>

<details>
<summary>Click to view Fix</summary>

**Root cause:** MTU mismatch on the underlay links. VXLAN adds ~50 bytes of overhead; CAPWAP adds another ~54 bytes. Without jumbo frames on the underlay (MTU ≥ 9100), packets are silently dropped or fragmented, causing intermittent connectivity and poor health scores.

**Fix:**
1. Enable jumbo frames (MTU 9100) on all underlay interfaces (IS-IS links between fabric nodes).
2. Set the system MTU on all Catalyst 9000 switches: `system mtu 9100`.
3. Verify: `show interfaces <uplink>` — MTU should show 9100.
4. After MTU fix, verify Assurance shows health improvement within 5 minutes (telemetry interval).

**Key fact:** MTU issues are the #1 cause of intermittent VXLAN fabric problems. Assurance's AI engine typically flags "MTU mismatch" in the Issues dashboard if enough data is collected.

</details>

---

### Ticket 3 — Contractor Endpoints Can Access Employee Resources Despite Policy Restriction

The security team has defined an SGACL contract: SGT 20 (Contractors) is denied access to SGT 10 (Employees). The policy shows as active in Catalyst Center. However, security audit logs confirm contractor endpoints (SGT 20) are still accessing employee file shares.

**Success criteria:** All contractor-to-employee traffic is denied at the fabric level.

<details>
<summary>Click to view Diagnosis Steps</summary>

Work through these questions:
1. Is the SGACL policy provisioned (pushed from Catalyst Center to Edge Nodes)?
2. Run `show cts role-based sgt-map` on the destination Edge Node — is SGT 10 mapped correctly to the employee IP range?
3. Run `show cts role-based permissions from 20 to 10` — does the SGACL appear?
4. Is the employee file server connected to a fabric Edge Node, or to a traditional switch outside the fabric?
5. Is the Contractor authentication actually assigning SGT 20, or is it falling through to an untagged default?

</details>

<details>
<summary>Click to view Fix</summary>

**Root cause (most likely):** The employee file server is connected to a switch outside the SD-Access fabric (traditional campus). SGT enforcement stops at the Border Node — the SGACL is never evaluated for traffic destined to non-fabric endpoints.

**Fix:**
- **If server is outside fabric:** Deploy IP-based ACL on the fusion router for contractor-to-server traffic as an interim measure. Migrate the server to a fabric Edge Node port to enable SGACL enforcement.
- **If server is inside fabric:** Check that Catalyst Center has pushed the SGACL to the destination Edge Node. Run `show platform software fed switch active security-fed sgacl` to verify hardware programming.
- **If SGT is not being assigned:** Verify ISE authorization policy — contractor endpoints must match a rule that assigns SGT 20 explicitly.

**Key fact:** SGT-based policy only works end-to-end when both source and destination are inside the SD-Access fabric. This is the most common exam scenario testing understanding of policy limitations.

</details>

---

## 10. Lab Completion Checklist

### Core Concepts

- [ ] Drew the SD-Access three-layer model (underlay/overlay/control plane) from memory
- [ ] Correctly identified all five fabric node roles and their LISP functions
- [ ] Traced the full LISP map-register → map-request → map-reply → VXLAN encapsulation sequence
- [ ] Traced an SGT from 802.1X authentication through VXLAN-GPO to SGACL enforcement
- [ ] Completed the Fabric Role Identification exercise (Task 4) with all assignments correct
- [ ] Described the fusion router's function and placement in a brownfield deployment
- [ ] Correctly sequenced the Catalyst Center Design → Policy → Provision → Assurance workflow
- [ ] Completed the SD-WAN vs SD-Access comparison table (Task 7) with all 7 rows correct

### Troubleshooting Scenarios

- [ ] Diagnosed Ticket 1 (internet unreachable) and identified the fusion router / IP Transit root cause
- [ ] Diagnosed Ticket 2 (wireless degradation) and identified the MTU/jumbo frame root cause
- [ ] Diagnosed Ticket 3 (policy bypass) and identified the non-fabric server root cause

### Exam Readiness

- [ ] Can explain why SGT enforcement stops at the Border Node for non-fabric destinations
- [ ] Can distinguish between LISP roles (MS, MR, ITR, ETR, xTR, PxTR) and which fabric node performs each
- [ ] Can explain the difference between IP Transit and SD-Access Transit for multi-site deployments
- [ ] Can identify the correct Catalyst Center workflow phase for any given deployment action
