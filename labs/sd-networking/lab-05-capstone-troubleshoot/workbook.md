# Lab 05: SD-Networking Comprehensive Troubleshooting — Capstone II

## Table of Contents

1. [Concepts & Skills Covered](#1-concepts--skills-covered)
2. [Topology & Scenario](#2-topology--scenario)
3. [Hardware & Environment Specifications](#3-hardware--environment-specifications)
4. [Base Configuration](#4-base-configuration)
5. [Lab Challenge: Comprehensive Troubleshooting](#5-lab-challenge-comprehensive-troubleshooting)
6. [Verification & Analysis](#6-verification--analysis)
7. [Verification Cheatsheet](#7-verification-cheatsheet)
8. [Solutions (Spoiler Alert!)](#8-solutions-spoiler-alert)
9. [Troubleshooting Scenarios](#9-troubleshooting-scenarios)
10. [Lab Completion Checklist](#10-lab-completion-checklist)

---

## 1. Concepts & Skills Covered

**Exam Objective:** 1.2 — Describe SD-WAN architecture and components; 1.2.a — Orchestration plane (vBond); 1.2.b — Management plane (vManage) and Control plane (vSmart); 1.3 — Describe SD-Access architecture; 1.3.a — Describe SD-Access fabric roles; 1.3.b — Traditional campus interoperability with SD-Access

This capstone is a pure troubleshooting exercise. Five concurrent faults have been pre-loaded across multiple SD-WAN components. You receive a partially functioning network, a set of symptoms, and no hints about what was changed. Your task is to systematically diagnose and fix every fault using only show commands and your knowledge of how the SD-WAN fabric is supposed to work. The hybrid component asks you to apply the same diagnostic mindset to SD-Access architecture failure scenarios.

### SD-WAN Troubleshooting Methodology

Work from control plane outward to data plane. A fault at a lower layer masks all higher-layer symptoms:

```
Layer 1: Transport reachability (ping vpn 0)
    ↓
Layer 2: Control connections (show control connections)
    ↓
Layer 3: OMP peering (show omp peers)
    ↓
Layer 4: OMP route distribution (show omp routes, show ip route vpn 1)
    ↓
Layer 5: Data plane tunnels (show bfd sessions, show tunnel statistics)
    ↓
Layer 6: Policy enforcement (show policy from-vsmart)
    ↓
Layer 7: End-to-end application reachability (ping vpn 1)
```

Never jump to a higher layer until the layer below is confirmed healthy. A BFD session cannot form if OMP peering is down. OMP cannot peer if control connections are in `connect` state. Control connections cannot reach `up` state if the system block parameters do not match across devices.

### Key Fault Categories

**System block mismatches** are the most common fabric bring-up failure. Every device must agree on `organization-name` (case-sensitive string), `vbond` address, and must have unique `system-ip` values. A single wrong character in `organization-name` causes the fabric to reject the device with a certificate validation failure — `show control connections` will show the peer stuck in `connect` with no `up` state.

**Missing tunnel-interface** on a VPN 0 interface means the interface participates in L3 routing but cannot form IPsec tunnels. The device will show healthy control connections (control uses DTLS, not IPsec) but `show bfd sessions` will be empty for that device. IPsec tunnels and BFD sessions only form between interfaces that have `tunnel-interface encapsulation ipsec` configured.

**VPN 1 misconfiguration** breaks service connectivity silently. The control plane and data plane tunnels can both be healthy while users are completely unreachable if the VPN 1 LAN interface has a wrong IP or is missing entirely. The OMP will advertise whatever prefix the interface is configured with — if that prefix is wrong, the remote site learns the wrong route.

**Policy activation failures** occur when the `apply-policy` block is missing or incorrect. Policy definitions (`policy` block) are committed to vSmart but never distributed to vEdges until `apply-policy` binds them to site-lists with correct in/out direction. `show policy from-vsmart` on a vEdge will be empty.

**VPN-list scope errors** cause policies to appear installed (`show policy from-vsmart` shows the policy name) but the policy does not affect the expected traffic. If the `vpn-list` inside the policy references the wrong VPN number, neither the control policy nor the app-route policy will match any VPN 1 traffic.

### SD-Access Troubleshooting Approach

SD-Access faults are diagnosed by plane:
- **Underlay (IS-IS)**: check `show isis neighbors` on fabric nodes — if IS-IS adjacency is down, VXLAN encapsulation cannot reach the destination RLOC
- **Control plane (LISP)**: check `show lisp instance-id` and `show lisp map-cache` — if the EID-to-RLOC mapping is missing, the xTR cannot VXLAN-encapsulate toward the destination
- **Overlay (VXLAN/SGT)**: check `show vxlan` and Catalyst Center Assurance for client health — if VXLAN is up but traffic is dropped, a policy contract (SGT-based ACL) may be blocking it
- **Catalyst Center**: check the Assurance dashboard for client health score, issue correlation, and path trace visualization

**Skills this lab develops:**

| Skill | Description |
|-------|------------|
| Layered SD-WAN diagnosis | Work control plane → data plane → policy without skipping layers |
| System block auditing | Compare running-config system parameters against expected values |
| Tunnel-interface diagnosis | Distinguish DTLS-only (control) from IPsec (data) using show commands |
| OMP route tracing | Follow prefix advertisement from vEdge → vSmart → peer vEdge |
| Policy audit | Verify definition, vpn-list scope, and apply-policy binding independently |
| VPN 1 reachability testing | Use `ping vpn 1` to confirm service VPN connectivity post-fix |
| SD-Access failure scenario analysis | Map symptoms to correct fabric plane without hands-on access |

---

## 2. Topology & Scenario

**Scenario:** You are an escalation engineer called in to a regional enterprise whose SD-WAN fabric has been reported as "not working" after a maintenance window. The NOC gives you the following symptom summary:

- Site 1 (vEdge1) shows no connections on the SD-WAN dashboard
- No BFD sessions exist anywhere in the fabric
- Site 2 LAN is unreachable from Site 1, and vice versa
- Application-aware routing policies are not active on either edge
- A traceroute from Site 1 to Site 2 shows traffic entering the underlay but not being VXLAN-encapsulated

Your job: load the pre-broken configuration, diagnose all five faults, fix them in the correct order (bottom-up), and verify end-to-end fabric health.

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

                    IPsec Overlay Tunnel (VPN 0 — must be restored)
                    vEdge1 ◄────── BROKEN ──────────────────► vEdge2
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

> **Expected final state:** `show control connections` shows all peers `up` on all devices; `show bfd sessions` shows Site 1 ↔ Site 2 session `up`; `ping vpn 1 192.168.2.1` from vEdge1 succeeds 100%.

---

## 4. Base Configuration

`setup_lab.py` loads the pre-broken initial-configs onto all devices. The following is the **intended working state** — compare it against what you find to identify each fault.

**Known-good parameters:**

| Device | system-ip | site-id | org-name | vbond |
|--------|----------|--------|---------|-------|
| vManage | 10.10.10.1 | — | ENCOR-LAB | 172.16.0.3 |
| vSmart | 10.10.10.2 | — | ENCOR-LAB | 172.16.0.3 |
| vBond | 10.10.10.3 | — | ENCOR-LAB | 172.16.0.3 local |
| vEdge1 | 10.10.10.11 | 100 | ENCOR-LAB | 172.16.0.3 |
| vEdge2 | 10.10.10.12 | 200 | ENCOR-LAB | 172.16.0.3 |

**VPN 1 LAN addresses:**

| Device | VPN 1 Interface | Correct IP |
|--------|----------------|-----------|
| vEdge1 | ge0/1 | 192.168.1.1/24 |
| vEdge2 | ge0/1 | 192.168.2.1/24 |

**Policy parameters:**
- vpn-list VPN1 must reference `vpn 1` (not any other VPN number)
- `apply-policy` must bind PREFER-SITE1-PATH and APP-AWARE-ROUTING to their site-lists
- Site-list SITE1 = site-id 100; site-list SITE2 = site-id 200

---

## 5. Lab Challenge: Comprehensive Troubleshooting

> This is a capstone lab. The network is pre-broken.
> Diagnose and resolve 5+ concurrent faults spanning all blueprint bullets.
> No step-by-step guidance is provided — work from symptoms only.

**Constraints:**
- Use only show commands to diagnose — do not read initial-configs files
- Fix faults in bottom-up order (control plane before data plane before policy)
- After each fix, re-verify from that layer upward before proceeding
- Document each fault: what symptom led you to it, what the misconfiguration was, what you changed

**Part A — SD-WAN Troubleshooting (5 concurrent faults)**

Load the lab with `python3 setup_lab.py`, then diagnose and fix all faults until the following are true on every device:

- `show control connections` — all peers in `up` state (vEdge1, vEdge2, vSmart)
- `show omp peers` on vSmart — both vEdge1 and vEdge2 listed
- `show bfd sessions` on vEdge1 — vEdge2 session in `up` state
- `show ip route vpn 1` on vEdge1 — 192.168.2.0/24 via OMP
- `show ip route vpn 1` on vEdge2 — 192.168.1.0/24 via OMP
- `show policy from-vsmart` on both vEdges — both `APP-AWARE-ROUTING` and `PREFER-SITE1-PATH` present
- `ping vpn 1 192.168.2.1` from vEdge1 — 100% success
- `ping vpn 1 192.168.1.1` from vEdge2 — 100% success

**Part B — SD-Access Troubleshooting Scenarios (Conceptual)**

Answer each scenario in writing. These simulate conceptual troubleshooting questions on the 350-401 exam.

1. A Fabric Edge Node reports that a new endpoint's traffic is being dropped after it joins the fabric. `show lisp instance-id` on the Control Plane Node shows the EID registered but the Map-Cache on the originating xTR is empty. What is the most likely cause, and what command would you run to confirm?

2. An engineer adds a new VLAN to an SD-Access fabric via Catalyst Center (Provision → Fabric). After provisioning, endpoints in the new VLAN can reach other endpoints in the same VLAN but not endpoints in the Finance VLAN. `show vxlan` on the Fabric Edge Node shows the VXLAN tunnel as up. What plane and which component is most likely blocking traffic, and how is it enforced?

3. After a Fabric Border Node hardware failure and replacement, the new External Border Node is provisioned via Catalyst Center. However, endpoints inside the fabric cannot reach legacy servers in the traditional campus. IS-IS adjacency is up, VXLAN tunnels are established, and the Catalyst Center Assurance shows a path trace failure at the Border Node. Name the architectural component responsible for routing between the fabric VN and the external network, and describe the two-step Catalyst Center workflow to restore connectivity.

---

## 6. Verification & Analysis

### Layer-by-Layer Verification Sequence

Start at the bottom and work up. Each command confirms one layer.

**Layer 1 — Transport (expected: all reachable)**
```
vEdge1# ping vpn 0 172.16.0.3
Sending 5, 100-byte ICMP Echos to 172.16.0.3
!!!!!                               ! ← vBond must be reachable from VPN 0
```

**Layer 2 — Control connections (expected: all up)**
```
vEdge2# show control connections
PEER     TYPE    SYSTEM IP    STATE
vsmart   dtls    10.10.10.2   up      ! ← vSmart in "up" state
vbond    dtls    10.10.10.3   up      ! ← vBond in "up" state
vmanage  dtls    10.10.10.1   up      ! ← vManage in "up" state
```

**Layer 3 — OMP peering (expected: both vEdges listed on vSmart)**
```
vSmart# show omp peers
PEER             TYPE    CONNECTS
172.16.1.1       vedge   1          ! ← vEdge1 connected
172.16.2.1       vedge   1          ! ← vEdge2 connected
```

**Layer 4 — OMP routes (expected: VPN 1 prefix from each site)**
```
vEdge1# show ip route vpn 1
VPN  PREFIX             NEXTHOP       PROTOCOL
1    192.168.1.0/24     0.0.0.0       connected    ! ← local LAN
1    192.168.2.0/24     172.16.2.1    omp          ! ← site 2 via OMP (must be present)
```

**Layer 5 — BFD sessions (expected: Site 1 ↔ Site 2 session up)**
```
vEdge1# show bfd sessions
SYSTEM IP       SITE  STATE   PROTO   ENCAP
10.10.10.12     200   up      ipsec   ipv4         ! ← vEdge2 BFD up
```

**Layer 6 — Policy (expected: both policies installed)**
```
vEdge1# show policy from-vsmart
total policy from vsmart: 2
policy #1: APP-AWARE-ROUTING      ! ← must be present
policy #2: PREFER-SITE1-PATH      ! ← must be present
```

**Layer 7 — End-to-end reachability (expected: 100% success)**
```
vEdge1# ping vpn 1 192.168.2.1
!!!!!                              ! ← five successes
Success rate is 100 percent (5/5)
```

---

## 7. Verification Cheatsheet

### System Audit Commands

```
show system status
show running-config system
show control connections
show control local-properties
```

| Command | What to Look For |
|---------|-----------------|
| `show system status` | Verify system-ip, organization-name, vbond address match expected values |
| `show running-config system` | Full system block — compare vbond, org-name, site-id |
| `show control connections` | All peers must be `up` — any `connect` state needs diagnosis |
| `show control local-properties` | Local system-ip, org-name, color, DTLS port |

> **Exam tip:** `organization-name` is case-sensitive and must match exactly across all fabric components. A mismatch causes the device to be rejected at authentication — the error is indistinguishable from a certificate failure without checking both ends.

### Tunnel and BFD

```
show bfd sessions
show tunnel statistics
show ipsec outbound-connections
show interface ge0/0
```

| Command | What to Look For |
|---------|-----------------|
| `show bfd sessions` | `up` state between all vEdge pairs; empty = tunnel-interface missing |
| `show tunnel statistics` | TX/RX packets incrementing — confirms traffic flow |
| `show ipsec outbound-connections` | Active SAs; empty = VPN 0 tunnel-interface not configured |
| `show interface ge0/0` | Interface up/up; must have `tunnel-interface` block for IPsec |

### OMP and Routing

```
show omp peers
show omp routes
show ip route vpn 1
show omp tlocs
```

| Command | What to Look For |
|---------|-----------------|
| `show omp peers` | All vEdges connected on vSmart |
| `show omp routes` | VPN 1 prefixes for all sites; missing prefix = VPN 1 misconfigured on source vEdge |
| `show ip route vpn 1` | Remote site LAN via OMP (protocol = omp) |
| `show omp tlocs` | TLOC entries with transport color — confirms overlay reachability |

> **Exam tip:** If `show omp routes` on vSmart shows an unexpected prefix (e.g., 192.168.99.0/24 instead of 192.168.2.0/24), the vEdge advertising that prefix has the wrong VPN 1 interface IP. OMP advertises what the interface is actually configured with — it does not validate against expected values.

### Policy

```
show policy from-vsmart
show running-config policy
show running-config apply-policy
show app-route stats
```

| Command | What to Look For |
|---------|-----------------|
| `show policy from-vsmart` | Policy names present and count > 0; empty = apply-policy not committed |
| `show running-config policy` (vSmart) | vpn-list VPN1 must reference `vpn 1`, not any other |
| `show running-config apply-policy` (vSmart) | site-lists bound to correct policy names with in/out direction |
| `show app-route stats` | Per-path statistics; confirms SLA class is being evaluated |

### Verification Commands

| Command | What to Look For |
|---------|-----------------|
| `show control connections` | All peers `up` |
| `show omp peers` | Both vEdges on vSmart |
| `show bfd sessions` | Site pair session `up` |
| `show ip route vpn 1` | Correct remote LAN prefix via OMP |
| `show policy from-vsmart` | Both policy names present |
| `ping vpn 1 <remote-ip>` | 100% success |

### Common SD-WAN Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| vEdge control connections all stuck in `connect` | Wrong `vbond` IP or wrong `organization-name` in system block |
| Control connections up but BFD sessions empty | `tunnel-interface` missing on VPN 0 interface of one or both vEdges |
| OMP route shows unexpected prefix (e.g., /24 with wrong subnet) | VPN 1 interface on advertising vEdge has incorrect IP address |
| `show policy from-vsmart` empty on all vEdges | `apply-policy` block missing or not committed on vSmart |
| Policies show in `from-vsmart` but no traffic steering observed | `vpn-list` inside policy references wrong VPN number |
| Site 1 can ping Site 2 but wrong route taken | Control policy direction wrong (in vs out in apply-policy) |

---

## 8. Solutions (Spoiler Alert!)

> Diagnose the network yourself before reading. Each fault is independent — try to find all five before checking any answer.

### Fault A — vEdge1 Wrong vBond Address

<details>
<summary>Click to view Diagnosis and Fix</summary>

**Diagnosis:**
```bash
vEdge1# show control connections
! All peers stuck in "connect" — never reach "up"
vEdge1# show system status
! vbond: 172.16.0.99  ← wrong! expected 172.16.0.3
vEdge1# ping vpn 0 172.16.0.99
! Ping fails (no such host) — confirms wrong address
```

**Fix:**
```bash
vEdge1# config
vEdge1(config)# system
vEdge1(config-system)# vbond 172.16.0.3
vEdge1(config-system)# commit
vEdge1# show control connections
! All three peers should reach "up" within 30 seconds
```
</details>

---

### Fault B — vEdge2 Missing Tunnel-Interface

<details>
<summary>Click to view Diagnosis and Fix</summary>

**Diagnosis:**
```bash
vEdge2# show control connections
! vSmart, vBond, vManage all "up" — control plane is healthy
vEdge2# show bfd sessions
! Empty — no BFD sessions exist
vEdge1# show bfd sessions
! Empty — no session with vEdge2
vEdge2# show running-config vpn 0
! interface ge0/0 has ip address but NO tunnel-interface block
```

**Fix:**
```bash
vEdge2# config
vEdge2(config)# vpn 0
vEdge2(config-vpn-0)# interface ge0/0
vEdge2(config-vpn-0-if)# tunnel-interface
vEdge2(config-tunnel-if)# encapsulation ipsec
vEdge2(config-tunnel-if)# allow-service all
vEdge2(config-tunnel-if)# commit
vEdge2# show bfd sessions
! Session with vEdge1 should appear as "up"
```
</details>

---

### Fault C — vEdge2 Wrong VPN 1 IP Address

<details>
<summary>Click to view Diagnosis and Fix</summary>

**Diagnosis:**
```bash
vEdge1# show ip route vpn 1
! 192.168.99.0/24 via omp ← unexpected! expected 192.168.2.0/24
! 192.168.1.0/24 connected
vSmart# show omp routes vpn 1
! vEdge2 advertising 192.168.99.0/24 — wrong prefix
vEdge2# show running-config vpn 1
! interface ge0/1 ip address 192.168.99.1/24 ← should be 192.168.2.1/24
```

**Fix:**
```bash
vEdge2# config
vEdge2(config)# vpn 1
vEdge2(config-vpn-1)# interface ge0/1
vEdge2(config-vpn-1-if)# ip address 192.168.2.1/24
vEdge2(config-vpn-1-if)# commit
vEdge1# show ip route vpn 1
! 192.168.2.0/24 must now appear via OMP
```
</details>

---

### Fault D — vSmart Missing apply-policy

<details>
<summary>Click to view Diagnosis and Fix</summary>

**Diagnosis:**
```bash
vEdge1# show policy from-vsmart
! Empty — no policies installed
vEdge2# show policy from-vsmart
! Empty — no policies installed
vSmart# show running-config policy
! Policy definitions exist (site-list, vpn-list, sla-class, control-policy, app-route-policy all present)
vSmart# show running-config apply-policy
! Empty — no apply-policy block
```

**Fix:**
```bash
vSmart# config
vSmart(config)# apply-policy
vSmart(config-apply-policy)# site-list SITE2
vSmart(config-apply-policy-site-list)# control-policy PREFER-SITE1-PATH out
vSmart(config-apply-policy-site-list)# app-route-policy APP-AWARE-ROUTING
vSmart(config-apply-policy)# site-list SITE1
vSmart(config-apply-policy-site-list)# app-route-policy APP-AWARE-ROUTING
vSmart(config-apply-policy)# commit
vEdge1# show policy from-vsmart
! Two policies should appear — but check Fault E next
```
</details>

---

### Fault E — vSmart vpn-list References Wrong VPN

<details>
<summary>Click to view Diagnosis and Fix</summary>

**Diagnosis:**
```bash
vEdge1# show policy from-vsmart
! Policies listed but app-route not steering traffic correctly
vSmart# show running-config policy vpn-list VPN1
! vpn-list VPN1
!   vpn 2     ← wrong! should be vpn 1
```

**Fix:**
```bash
vSmart# config
vSmart(config)# policy
vSmart(config-policy)# vpn-list VPN1
vSmart(config-vpn-list)# no vpn 2
vSmart(config-vpn-list)# vpn 1
vSmart(config-vpn-list)# commit
vEdge1# show policy from-vsmart
! Policies present and now scoped correctly to VPN 1
vEdge1# ping vpn 1 192.168.2.1
! 100% success confirms all five faults resolved
```
</details>

---

### Part B — SD-Access Answer Key

<details>
<summary>Click to view SD-Access Troubleshooting Answers</summary>

**Question 1 — Empty Map-Cache despite EID registered on CPN:**

Most likely cause: the ITR (ingress Fabric Edge Node) has not yet sent a Map-Request, or the Map-Request was sent but the Map-Reply was dropped in transit (underlay IS-IS issue to the CPN's RLOC).

Confirm with: `show lisp instance-id <id> ipv4 map-cache` on the ITR — if the cache entry is missing or shows "no-match," the ITR never received the Map-Reply. Check `show isis neighbors` to confirm underlay adjacency between ITR and CPN is established.

**Question 2 — Same-VN reachable but cross-VN traffic dropped:**

The IS-IS underlay and VXLAN overlay are healthy (confirmed by `show vxlan` and successful same-VLAN traffic). The blocking is in the **policy plane** — specifically an SGT-based policy contract enforced at the **egress Fabric Edge Node**. The new VLAN was provisioned but no policy contract was created allowing it to reach the Finance SGT. The contract is enforced via a VXLAN-GPO Group Policy Option field — the Finance Edge Node drops packets from the unknown/untrusted SGT. Fix: in Catalyst Center → Policy → define a contract allowing the new VLAN's SGT to Finance SGT, then re-provision.

**Question 3 — Border Node replacement, endpoints inside fabric cannot reach legacy campus:**

The architectural component is the **fusion router** — it bridges the fabric VN (via IP Transit on the External Border Node) and the external VRF (traditional campus routing domain).

Two-step Catalyst Center workflow:
1. **Provision** → Fabric Domain → select the new External Border Node device → assign it the External Border Node role → configure the IP Transit network (BGP or OSPF peering toward the fusion router)
2. **Policy** → Virtual Networks → confirm the fabric VN is exported toward the IP Transit interface, and that the fusion router's return routes for fabric prefixes are accepted

After re-provisioning, confirm with Catalyst Center Assurance → Path Trace from the fabric endpoint to the legacy server — the path should exit at the External Border Node and traverse the fusion router.
</details>

---

## 9. Troubleshooting Scenarios

Five faults are pre-loaded via `setup_lab.py`. Work through them systematically using the layer-by-layer method from Section 7.

### Workflow

```bash
python3 setup_lab.py                                  # load pre-broken state
# ... diagnose and fix using show commands ...
python3 scripts/fault-injection/apply_solution.py     # restore known-good (if needed)
```

---

### Ticket 1 — vEdge1 Cannot Establish Any Control Connections

You log into vEdge1 and run `show control connections`. Every peer shows `connect` and never transitions to `up`. vEdge2, vSmart, and vManage all show healthy connections among themselves.

**Success criteria:** `show control connections` on vEdge1 shows vSmart, vBond, and vManage all in `up` state.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `show control connections` — confirm all peers stuck in `connect`
2. `ping vpn 0 172.16.0.3` — test transport reachability to vBond
3. `show system status` — check vbond address field
4. Compare vbond address against expected value (172.16.0.3)
5. Root cause: vbond address is 172.16.0.99 — vEdge1 sends DTLS to a non-existent host

</details>

<details>
<summary>Click to view Fix</summary>

```bash
vEdge1# config
vEdge1(config)# system
vEdge1(config-system)# vbond 172.16.0.3
vEdge1(config-system)# commit
vEdge1# show control connections
! Verify all three peers reach "up" state
```
</details>

---

### Ticket 2 — No BFD Sessions Exist — IPsec Tunnels Will Not Form

All control connections show `up`. `show omp peers` on vSmart lists both vEdges. But `show bfd sessions` is empty on both vEdges. Site-to-site pings in VPN 1 all fail.

**Success criteria:** `show bfd sessions` on vEdge1 shows a session with vEdge2 in `up` state.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `show control connections` — confirm `up` (control plane healthy)
2. `show bfd sessions` — empty on both vEdges
3. `show ipsec outbound-connections` — empty (confirms no IPsec SAs)
4. `show running-config vpn 0` on vEdge2 — inspect VPN 0 interface block
5. Root cause: `tunnel-interface` block missing from vEdge2 VPN 0 ge0/0 — interface participates in routing but cannot form IPsec tunnels

</details>

<details>
<summary>Click to view Fix</summary>

```bash
vEdge2# config
vEdge2(config)# vpn 0
vEdge2(config-vpn-0)# interface ge0/0
vEdge2(config-vpn-0-if)# tunnel-interface
vEdge2(config-tunnel-if)# encapsulation ipsec
vEdge2(config-tunnel-if)# allow-service all
vEdge2(config-tunnel-if)# commit
vEdge1# show bfd sessions
! vEdge2 session must appear as "up"
```
</details>

---

### Ticket 3 — Site 2 LAN Prefix Incorrect — VPN 1 Reachability Fails

BFD sessions are now up. `show ip route vpn 1` on vEdge1 shows a route from Site 2, but pinging the expected Site 2 LAN gateway (192.168.2.1) fails. The OMP route on vEdge1 points to an unexpected prefix.

**Success criteria:** `show ip route vpn 1` on vEdge1 shows 192.168.2.0/24 via OMP. `ping vpn 1 192.168.2.1` from vEdge1 succeeds.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `show ip route vpn 1` on vEdge1 — unexpected prefix from Site 2 (192.168.99.0/24 instead of 192.168.2.0/24)
2. `show omp routes vpn 1` on vSmart — confirm vEdge2 advertising wrong prefix
3. `show running-config vpn 1` on vEdge2 — check ge0/1 IP address
4. Root cause: ge0/1 IP is 192.168.99.1/24 instead of 192.168.2.1/24 — OMP advertises the configured prefix faithfully

</details>

<details>
<summary>Click to view Fix</summary>

```bash
vEdge2# config
vEdge2(config)# vpn 1
vEdge2(config-vpn-1)# interface ge0/1
vEdge2(config-vpn-1-if)# ip address 192.168.2.1/24
vEdge2(config-vpn-1-if)# commit
vEdge1# show ip route vpn 1
! 192.168.2.0/24 must appear via OMP
vEdge1# ping vpn 1 192.168.2.1
! 100% success confirms this fault is resolved
```
</details>

---

### Ticket 4 — No Policies Active on Any vEdge — QoS and Path Steering Absent

Control plane, BFD, and VPN 1 reachability are all healthy now. But the monitoring team reports zero QoS enforcement. `show policy from-vsmart` on both vEdges returns empty — no policies are installed.

**Success criteria:** `show policy from-vsmart` on vEdge1 and vEdge2 lists at least one policy name.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `show policy from-vsmart` on vEdge1 and vEdge2 — empty
2. `show running-config policy` on vSmart — policy definitions are committed (site-list, vpn-list, sla-class, etc.)
3. `show running-config apply-policy` on vSmart — **empty** (no apply-policy block)
4. Root cause: policy definitions exist but nothing binds them to site-lists — vSmart has no instruction to distribute policies to any site

</details>

<details>
<summary>Click to view Fix</summary>

```bash
vSmart# config
vSmart(config)# apply-policy
vSmart(config-apply-policy)# site-list SITE2
vSmart(config-apply-policy-site-list)# control-policy PREFER-SITE1-PATH out
vSmart(config-apply-policy-site-list)# app-route-policy APP-AWARE-ROUTING
vSmart(config-apply-policy)# site-list SITE1
vSmart(config-apply-policy-site-list)# app-route-policy APP-AWARE-ROUTING
vSmart(config-apply-policy)# commit
vEdge1# show policy from-vsmart
! Policies should appear — then proceed to Ticket 5
```
</details>

---

### Ticket 5 — Policies Installed But Application Traffic Steering Not Working

Policies now show in `show policy from-vsmart` on both vEdges. The control policy name appears. However, application-aware routing is not steering traffic correctly — all traffic follows the default path regardless of SLA class.

**Success criteria:** `show app-route stats` on vEdge1 shows SLA class evaluations being applied. Policies are scoped to the correct VPN.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `show policy from-vsmart` — policies listed (APP-AWARE-ROUTING, PREFER-SITE1-PATH)
2. `show app-route stats` — no SLA evaluations; zero packets matched
3. `show running-config policy vpn-list VPN1` on vSmart — shows `vpn 2` instead of `vpn 1`
4. Root cause: vpn-list VPN1 references vpn 2 — the app-route policy and control policy are scoped to VPN 2, which does not exist; no VPN 1 traffic matches

</details>

<details>
<summary>Click to view Fix</summary>

```bash
vSmart# config
vSmart(config)# policy
vSmart(config-policy)# vpn-list VPN1
vSmart(config-vpn-list)# no vpn 2
vSmart(config-vpn-list)# vpn 1
vSmart(config-vpn-list)# commit
vEdge1# show app-route stats
! SLA evaluations should now appear for VPN 1 traffic
vEdge1# ping vpn 1 192.168.2.1
! All 5 pings succeed — full fabric health restored
```
</details>

---

## 10. Lab Completion Checklist

### SD-WAN Troubleshooting

- [ ] Fault A diagnosed (wrong vbond address on vEdge1) and fixed
- [ ] `show control connections` shows all peers `up` on vEdge1
- [ ] Fault B diagnosed (missing tunnel-interface on vEdge2) and fixed
- [ ] `show bfd sessions` on vEdge1 shows vEdge2 session as `up`
- [ ] Fault C diagnosed (wrong VPN 1 IP on vEdge2) and fixed
- [ ] `show ip route vpn 1` on vEdge1 shows 192.168.2.0/24 via OMP
- [ ] `ping vpn 1 192.168.2.1` from vEdge1 succeeds 100%
- [ ] Fault D diagnosed (apply-policy missing on vSmart) and fixed
- [ ] `show policy from-vsmart` on both vEdges lists policies
- [ ] Fault E diagnosed (vpn-list VPN1 wrong VPN reference) and fixed
- [ ] `show app-route stats` shows SLA evaluations for VPN 1 traffic
- [ ] All five faults documented with symptom, root cause, and fix

### SD-Access Scenarios

- [ ] Question 1 answered (empty Map-Cache despite EID registered)
- [ ] Question 2 answered (cross-VN traffic dropped — SGT policy contract)
- [ ] Question 3 answered (Border Node replacement — fusion router + Catalyst Center workflow)

### Final Verification

- [ ] `python3 scripts/fault-injection/apply_solution.py` runs successfully
- [ ] All verification commands from Section 6 show expected output after fixes
