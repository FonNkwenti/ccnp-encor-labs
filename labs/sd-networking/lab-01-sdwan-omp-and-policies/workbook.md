# Lab 01: OMP Routing and Control Policies

**Topic:** SD-WAN and SD-Access | **Difficulty:** Intermediate | **Time:** 90 minutes
**Blueprint:** 1.2 — Cisco Catalyst SD-WAN | 1.2.a — SD-WAN control and data plane elements | 1.2.b — Benefits and limitations

---

## Table of Contents

1. [Concepts & Skills Covered](#1-concepts--skills-covered)
2. [Topology & Scenario](#2-topology--scenario)
3. [Hardware & Environment Specifications](#3-hardware--environment-specifications)
4. [Base Configuration](#4-base-configuration)
5. [Lab Challenge: Core Implementation](#5-lab-challenge-core-implementation)
6. [Verification & Analysis](#6-verification--analysis)
7. [Verification Cheatsheet](#7-verification-cheatsheet)
8. [Solutions (Spoiler Alert!)](#8-solutions-spoiler-alert)
9. [Troubleshooting Scenarios](#9-troubleshooting-scenarios)
10. [Lab Completion Checklist](#10-lab-completion-checklist)

---

## 1. Concepts & Skills Covered

**Exam Objective:** 1.2 — Cisco Catalyst SD-WAN working principles; 1.2.a — SD-WAN control and data plane elements; 1.2.b — Benefits and limitations of Catalyst SD-WAN

With the fabric control plane operational from lab-00, this lab focuses on the next layer: making user traffic flow across the overlay. You will configure service VPNs on both branch vEdges, watch OMP distribute LAN prefixes across the fabric, observe automatic IPsec tunnel formation, and implement your first centralised control policy on vSmart. Blueprint bullet 1.2.b is introduced here — understanding WHY centralized policy is powerful, and WHY a single vSmart is also a risk, are both exam-testable concepts.

---

### OMP Route Types and the Viptela RIB

OMP is the SD-WAN overlay routing protocol. vSmart acts as a route reflector — it receives all OMP routes from vEdges, applies policy, and reflects them back. There is no direct OMP adjacency between vEdge peers; all routes flow through vSmart.

OMP carries three distinct route types, each with different semantics:

| Route Type | Analogous To | What It Carries |
|-----------|-------------|----------------|
| `omp-route` | BGP NLRI | Service VPN prefix (e.g., 192.168.1.0/24) + TLOC list |
| `tloc-route` | BGP next-hop | vEdge tunnel endpoint identity (system-ip + color + encap) |
| `service-route` | BGP extended community | Service chaining information (firewall, IPS, etc.) |

When vEdge1 brings up VPN 1 with a LAN subnet, it automatically advertises an `omp-route` for 192.168.1.0/24, associating it with its own TLOC (10.10.10.11 / default / ipsec). vSmart reflects this to vEdge2. vEdge2 installs it in its OMP RIB as a reachable prefix via vEdge1's TLOC.

---

### IPsec Tunnel Formation (Data Plane)

IPsec tunnels between vEdges form **automatically** once both sides have exchanged TLOCs via OMP. No manual IPsec configuration is required — the TLOC exchange tells each vEdge where the other's tunnel endpoint is.

The process:
1. vEdge1 and vEdge2 each advertise their TLOC to vSmart via OMP
2. vSmart reflects each TLOC to the other vEdge
3. Each vEdge builds an IPsec SA directly to the other's TLOC IP (172.16.1.1 ↔ 172.16.2.1)
4. BFD probes begin running over the IPsec tunnel to monitor path quality

```
vEdge1 (172.16.1.1)  ←── IPsec over R-TRANSPORT ───→  vEdge2 (172.16.2.1)
     VPN 1: 192.168.1.0/24                              VPN 1: 192.168.2.0/24
```

The `show bfd sessions` command shows the active BFD sessions per tunnel. BFD probing is what SD-WAN uses for application-aware routing decisions (covered in lab-02).

---

### Centralised Control Policies

Control policies run on vSmart and manipulate **OMP route attributes** before they are reflected to vEdges. They do not touch data-plane packets — they only shape which routes vEdges see and with what attributes.

Key OMP attributes a control policy can set or filter:

| Attribute | Effect |
|-----------|--------|
| `preference` | Higher preference = preferred route (default 100; higher wins) |
| `metric` | Influences path selection within a site |
| `tag` | Marks routes for filtering elsewhere |
| `tloc` | Rewrites the next-hop TLOC to force a specific path |
| `accept` / `reject` | Adds or withdraws a route from the OMP RIB |

Control policies use a **match/action** structure identical in concept to route-maps:
```
control-policy PREFER-SITE1-PATH
 sequence 10
  match route
   site-list SITE1          ← match routes sourced from site-id 100
  action accept
   set preference 200       ← set preference to 200 (above default 100)
 default-action accept      ← pass all other routes unchanged
```

The policy is then applied at an `apply-policy` block targeting specific sites and a direction (`in` = filter what vSmart receives; `out` = filter what vSmart sends to a site).

---

### Benefits and Limitations of Catalyst SD-WAN (Blueprint 1.2.b)

**Benefits** — the exam expects you to articulate these concisely:

| Benefit | Explanation |
|---------|-------------|
| Transport independence | Runs over any IP transport — internet, MPLS, 4G/LTE simultaneously |
| Centralised policy | One vSmart push changes routing for the entire WAN instantly |
| Application-aware routing | BFD metrics drive per-application path steering |
| Zero-touch provisioning | vEdges self-register via vBond; no manual per-site config |
| Encryption by default | All data-plane traffic is IPsec-encrypted, regardless of transport |

**Limitations** — equally testable on the exam:

| Limitation | Explanation |
|------------|-------------|
| Controller dependency | vSmart failure stops OMP updates; existing routes persist but policy changes cannot be pushed |
| Certificate management | Onboarding fails if certificates expire or org-name mismatches |
| Single vSmart = SPOF | In this lab topology, one vSmart controller is a single point of failure for the entire overlay |
| Scale complexity | Large deployments require multiple vSmarts, controllers HA, and careful TLOC design |
| GUI-heavy operations | Many day-2 tasks are GUI-only in vManage; CLI verification requires separate access |

---

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| VPN 1 configuration | Enable service VPN on vEdges to carry user traffic |
| OMP route verification | Read `show omp routes` to confirm prefix advertisement and reflection |
| IPsec tunnel inspection | Use `show bfd sessions` and `show ipsec inbound-connections` to confirm tunnel state |
| Control policy authoring | Write a match/action control policy and apply it to a site-list |
| Benefits/limitations articulation | Explain SD-WAN trade-offs for exam scenario questions |

---

## 2. Topology & Scenario

**Scenario:** The ENCOR-LAB SD-WAN fabric is up (lab-00 complete). The network team now
needs to enable LAN-side connectivity between the two branch sites. vEdge1 (Branch 1,
192.168.1.0/24) and vEdge2 (Branch 2, 192.168.2.0/24) must exchange prefixes via OMP and
establish encrypted IPsec tunnels for inter-site traffic. After proving end-to-end
reachability, the team wants to demonstrate centralised policy by steering Site 2's
preferred path toward Site 1 using a vSmart control policy.

```
    ┌────────────────┐    ┌────────────────┐    ┌─────────────────┐
    │    vManage     │    │    vSmart      │    │     vBond       │
    │   (NMS/GUI)    │    │  (Controller)  │    │ (Orchestrator)  │
    │ 172.16.0.1/24  │    │ 172.16.0.2/24  │    │  172.16.0.3/24  │
    └───────┬────────┘    └───────┬────────┘    └────────┬────────┘
       eth1 │                eth1 │ OMP reflects          │ ge0/0
            │                    │ LAN prefixes           │
            └──────────────────┬─┘                        │
                               │     172.16.0.0/24         │
                         Gi0/0 │ 172.16.0.254/24           │
               ┌───────────────┴──────────────────────────┘
               │              R-TRANSPORT                  │
               │          (ISP Simulation)                 │
               └──────────────┬────────────────┬───────────┘
                    Gi0/1     │                │    Gi0/2
               172.16.1.254/24│                │172.16.2.254/24
                              │  IPsec tunnel  │
               172.16.1.1/24  │◄──────────────►│  172.16.2.1/24
                         ge0/0│                │ge0/0
                   ┌──────────┴────┐    ┌──────┴────────────┐
                   │    vEdge1     │    │     vEdge2        │
                   │  (Branch 1)   │    │   (Branch 2)      │
                   │sys:10.10.10.11│    │ sys:10.10.10.12   │
                   │  site-id: 100 │    │  site-id: 200     │
                   │ge0/1:         │    │ge0/1:             │
                   │192.168.1.1/24 │    │192.168.2.1/24     │
                   └───────────────┘    └───────────────────┘
                     VPN 1 LAN               VPN 1 LAN
                   192.168.1.0/24         192.168.2.0/24
```

**Key dependency patterns:**
- VPN 1 interfaces (ge0/1) are new in this lab — they carry LAN user traffic and advertise prefixes into OMP
- The IPsec tunnel (shown as ◄──►) forms automatically between ge0/0 WAN interfaces once TLOCs are exchanged via OMP — no manual IPsec config required
- The control policy runs on vSmart and sets `preference 200` for Site 1 routes advertised to Site 2 — making those routes preferred over any future alternative paths
- R-TRANSPORT remains unchanged; it is not aware of the SD-WAN overlay

---

## 3. Hardware & Environment Specifications

### Device Specifications

| Device | Platform | Role | Change from Lab-00 |
|--------|---------|------|--------------------|
| vManage | vtmgmt-20.6.2-001 | NMS/Dashboard | None |
| vSmart | vtsmart-20.6.2 | OMP Route Reflector + Policy | **Add control policy** |
| vBond | vtbond-20.6.2 | Orchestrator | None |
| vEdge1 | vtedge-20.6.2 | Branch Site 1 CPE | **Add VPN 1** |
| vEdge2 | vtedge-20.6.2 | Branch Site 2 CPE | **Add VPN 1** |
| R-TRANSPORT | IOSv 15.9 | ISP Simulation | None |

### Cabling Table

| Link | Source | Target | Subnet | Notes |
|------|--------|--------|--------|-------|
| L1–L3 | vBond/vSmart/vManage | R-TRANSPORT:Gi0/0 | 172.16.0.0/24 | Control plane (unchanged) |
| L4 | vEdge1:ge0/0 | R-TRANSPORT:Gi0/1 | 172.16.1.0/24 | VPN 0 WAN (unchanged) |
| L5 | vEdge2:ge0/0 | R-TRANSPORT:Gi0/2 | 172.16.2.0/24 | VPN 0 WAN (unchanged) |
| — | vEdge1:ge0/1 | (LAN host or loopback) | 192.168.1.0/24 | VPN 1 LAN — new |
| — | vEdge2:ge0/1 | (LAN host or loopback) | 192.168.2.0/24 | VPN 1 LAN — new |

> **Note:** In this EVE-NG lab, ge0/1 on each vEdge connects to the LAN segment but no
> host devices are deployed. Reachability is tested using `ping vpn 1` from each vEdge's
> own LAN interface address, sourced from the VPN 1 context.

### Console Access Table

| Device | Port | Connection Command |
|--------|------|--------------------|
| vManage | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| vSmart | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| vBond | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| vEdge1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| vEdge2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R-TRANSPORT | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |

---

## 4. Base Configuration

`initial-configs/` for this lab is an **exact copy of lab-00 solutions** — the complete
SD-WAN fabric bring-up state. When you run `setup_lab.py` (R-TRANSPORT only) and manually
apply Viptela configs, the fabric starts fully operational.

**Pre-configured (from lab-00 solutions):**
- Complete fabric control plane: vBond, vSmart, vManage, vEdge1, vEdge2 all joined
- VPN 0 tunnel interfaces on all SD-WAN devices
- OMP peering between both vEdges and vSmart
- R-TRANSPORT providing transport connectivity

**NOT pre-configured (you configure these in this lab):**
- VPN 1 (service VPN) on vEdge1 and vEdge2
- LAN interface configuration in VPN 1
- OMP prefix advertisement for LAN subnets
- Control policy on vSmart
- Policy application to site-lists

---

## 5. Lab Challenge: Core Implementation

### Task 1: Configure VPN 1 on vEdge1 (Branch Site 1)

VPN 1 is the service VPN that carries user LAN traffic. It is separate from VPN 0 (transport) and completely isolated from it within the vEdge.

- Enable VPN 1 on vEdge1 and configure the LAN-facing interface with the site 1 LAN address from the addressing plan (192.168.1.0/24 block, host address .1).
- The interface does not need a tunnel-interface sub-configuration — VPN 1 is a service VPN, not a transport VPN.
- Ensure the interface is administratively up.

**Verification:** `show omp routes` on vEdge1 must show 192.168.1.0/24 as a locally originated prefix. `show omp routes` on vSmart must show 192.168.1.0/24 as received from 10.10.10.11.

---

### Task 2: Configure VPN 1 on vEdge2 (Branch Site 2)

Repeat the VPN 1 configuration for Branch Site 2.

- Enable VPN 1 on vEdge2 and configure the LAN-facing interface with the site 2 LAN address (192.168.2.0/24 block, host address .1).
- Ensure the interface is up.

**Verification:** `show omp routes` on vSmart must show both 192.168.1.0/24 (from site 100) and 192.168.2.0/24 (from site 200). `show omp routes` on vEdge1 must show 192.168.2.0/24 reflected from vSmart.

---

### Task 3: Verify IPsec Tunnel Establishment

With both vEdges advertising TLOCs and LAN prefixes, the data-plane IPsec tunnel forms automatically.

- On vEdge1, confirm that a BFD session to vEdge2 (10.10.10.12) is active.
- On vEdge2, confirm that a BFD session to vEdge1 (10.10.10.11) is active.
- Confirm that the IPsec tunnel state shows `up` on both sides.

**Verification:** `show bfd sessions` on each vEdge must show one active session to the remote vEdge with state `up`. `show ipsec inbound-connections` must show an active SA entry for the remote vEdge's tunnel IP.

---

### Task 4: Test End-to-End LAN Reachability

With VPN 1 configured and IPsec tunnels up, prove that user traffic can traverse the overlay.

- From vEdge1, ping the VPN 1 LAN IP of vEdge2 (192.168.2.1) in the VPN 1 context.
- From vEdge2, ping the VPN 1 LAN IP of vEdge1 (192.168.1.1) in the VPN 1 context.

**Verification:** Both `ping vpn 1 192.168.2.1` (from vEdge1) and `ping vpn 1 192.168.1.1` (from vEdge2) must return 100% success rate.

---

### Task 5: Create a Centralised Control Policy on vSmart

The network team wants to demonstrate that vSmart can influence routing decisions from a central point. Create a control policy that sets a higher preference on routes originating from site-id 100 (Branch 1).

- On vSmart, define a site-list named `SITE1` containing site-id 100, and a site-list named `SITE2` containing site-id 200.
- Create a control policy named `PREFER-SITE1-PATH` that matches routes originating from the `SITE1` site-list and sets the OMP preference to 200.
- Set the default action of the policy to accept all other routes unchanged.

**Verification:** `show policy from-vsmart` on vEdge2 must show the `PREFER-SITE1-PATH` policy active. (Policy is not yet applied to a site in this task — apply in Task 6.)

---

### Task 6: Apply the Policy and Verify Path Preference

Apply the control policy to Site 2 in the outbound direction on vSmart, then verify the effect on vEdge2's OMP routing table.

- Apply the `PREFER-SITE1-PATH` policy to the `SITE2` site-list in the outbound direction — this means vSmart applies the policy when sending routes *to* Site 2.
- On vEdge2, check the OMP route table and confirm that the route to 192.168.1.0/24 now shows preference 200 instead of the default 100.

**Verification:** `show omp routes vpn 1` on vEdge2 must show 192.168.1.0/24 with `preference: 200`. `show policy from-vsmart` on vEdge2 must list the active policy.

---

### Task 7: Benefits and Limitations Analysis

This task is a knowledge-check exercise — no CLI configuration required.

- Identify two specific benefits of SD-WAN that this lab demonstrated (centralised policy, automatic IPsec, transport independence, etc.).
- Identify the single-point-of-failure risk present in this lab topology and explain how production deployments mitigate it.
- Explain why a control policy applied in the `out` direction on vSmart affects what the *receiving* vEdge sees, not what the *advertising* vEdge sent.

**Verification:** Review your answers against Section 1 (Benefits and Limitations table). The exam will ask for 2–3 bullet concise answers.

---

## 6. Verification & Analysis

### Task 1/2 — OMP Routes on vSmart (Both Prefixes Reflected)

```
vSmart# show omp routes
Code:
C   -> chosen
I   -> installed
Red -> redistributed
Rej -> rejected
L   -> looped
R   -> resolved
S   -> stale
Ext -> extranet
Inv -> invalid
U   -> TLOC unresolved

                                            PATH                   ATTRIBUTE
VPN    PREFIX              FROM PEER        ID  LABEL    STATUS    TYPE       TLOC IP          COLOR    ENCAP  PREFERENCE
-------------------------------------------------------------------------------------------------------------------------------
1      192.168.1.0/24      10.10.10.11      1   1003     C I       installed  10.10.10.11      default  ipsec  100   ! ← Site 1 prefix from vEdge1
1      192.168.2.0/24      10.10.10.12      1   1003     C I       installed  10.10.10.12      default  ipsec  100   ! ← Site 2 prefix from vEdge2
```

Both prefixes must appear with status `C I` (chosen and installed). The TLOC IP column identifies which vEdge originated the route.

### Task 3 — BFD Sessions on vEdge1

```
vEdge1# show bfd sessions
                                      SOURCE TLOC      REMOTE TLOC
SYSTEM IP        SITE ID   STATE    COLOR    ENCAP    COLOR    ENCAP    SOURCE IP        REMOTE IP        DST PORT
---------- --------  -----    -------  ------   -------  ------   ---------        ----------       --------
10.10.10.12      200       up       default  ipsec    default  ipsec    172.16.1.1       172.16.2.1       12347   ! ← vEdge2 BFD session up
```

State must be `up`. The SOURCE IP and REMOTE IP show the physical WAN addresses the IPsec tunnel uses. BFD polls every 1 second by default — `up` within 10–15 seconds of TLOC exchange.

### Task 4 — End-to-End LAN Ping

```
vEdge1# ping vpn 1 192.168.2.1
Ping in VPN 1
PING 192.168.2.1 (192.168.2.1) 56(84) bytes of data.
64 bytes from 192.168.2.1: icmp_seq=1 ttl=64 time=2.4 ms   ! ← reply received over IPsec tunnel
64 bytes from 192.168.2.1: icmp_seq=2 ttl=64 time=1.9 ms
64 bytes from 192.168.2.1: icmp_seq=3 ttl=64 time=2.1 ms
^C
--- 192.168.2.1 ping statistics ---
3 packets transmitted, 3 received, 0% packet loss, time 2002ms   ! ← 0% loss required
```

### Task 6 — OMP Route Preference After Policy Applied

```
vEdge2# show omp routes vpn 1
VPN    PREFIX              FROM PEER    STATE    PREFERENCE    TLOC IP
------ ------------------- ------------ -------- ------------- ----------------
1      192.168.1.0/24      10.10.10.2   C I      200           10.10.10.11   ! ← preference raised to 200 by PREFER-SITE1-PATH policy
1      192.168.2.0/24      10.10.10.2   C I      100           10.10.10.12   ! ← local route stays at default preference 100
```

The key difference: 192.168.1.0/24 shows `preference 200` (raised from default 100 by the control policy). The `FROM PEER` is `10.10.10.2` (vSmart) — confirming vSmart reflected the route with the policy attribute applied.

### Task 6 — Policy Verification on vEdge2

```
vEdge2# show policy from-vsmart
Centralized Policy
  vsmart-policy: PREFER-SITE1-PATH   ! ← policy name pushed from vSmart
  version:       1
  type:          control             ! ← control policy (not data policy)

vEdge2# show policy from-vsmart detail
...
  sequence 10 match route site-list SITE1
  action accept set preference 200
  default-action accept
```

---

## 7. Verification Cheatsheet

### VPN 1 Service Configuration

```
vpn 1
 interface ge0/1
  ip address <IP/PREFIX>
  no shutdown
```

| Command | Purpose |
|---------|---------|
| `vpn 1` | Service VPN for user traffic — completely isolated from VPN 0 |
| `ip address` | LAN-side IP in VPN 1 context (Viptela CIDR notation) |
| No `tunnel-interface` | Service VPNs do not get tunnel config — that is VPN 0 only |

> **Exam tip:** VPN 1 prefixes are **automatically** advertised into OMP once the interface is up — no `network` statement or redistribution is needed. This is a key SD-WAN simplification vs. traditional routing.

### OMP Verification Commands

| Command | What to Look For |
|---------|-----------------|
| `show omp routes` | All VPN 1 prefixes with status `C I` (chosen + installed) |
| `show omp routes vpn 1` | Filter to VPN 1 only; check `preference` field after policy |
| `show omp tlocs` | Remote TLOC entries with `C I` status |
| `show omp peers` | vSmart peering state — must remain `up` |
| `show omp summary` | Total routes received, sent, and installed in OMP RIB |

### BFD and IPsec Tunnel Verification

| Command | What to Look For |
|---------|-----------------|
| `show bfd sessions` | Remote vEdge entry with state `up` |
| `show ipsec inbound-connections` | Active SA entries for remote vEdge WAN IPs |
| `show ipsec outbound-connections` | Outbound SA entries; check encryption algorithm |
| `show tunnel statistics` | Bytes/packets sent and received per tunnel |

### Control Policy Syntax

```
policy
 site-list <NAME>
  site-id <N>
 !
 control-policy <POLICY-NAME>
  sequence <N>
   match route
    site-list <NAME>
   !
   action accept
    set preference <VALUE>
   !
  !
  default-action accept
 !
!
apply-policy
 site-list <TARGET-SITE>
  control-policy <POLICY-NAME> out
 !
!
```

| Keyword | Purpose |
|---------|---------|
| `site-list` | Groups site-ids for policy matching |
| `match route` | Matches OMP routes (omp-route type) |
| `set preference` | Raises or lowers OMP preference (higher = preferred) |
| `out` direction | Policy applied to routes vSmart sends TO the target site |
| `in` direction | Policy applied to routes vSmart RECEIVES FROM the target site |

> **Exam tip:** Control policy `out` direction is the most common — it controls what each site's vEdge *sees* in its OMP table. Think of it as vSmart filtering its advertisement to a specific site.

### Common SD-WAN OMP/Policy Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| VPN 1 prefix not in `show omp routes` on vSmart | VPN 1 interface `no shutdown` missing, or VPN 1 not configured |
| BFD session stuck in `init` | IPsec tunnel not forming — check VPN 0 reachability between vEdges |
| `show policy from-vsmart` empty on vEdge | `apply-policy` block not committed on vSmart |
| Preference still 100 after policy applied | Policy direction wrong (`in` instead of `out`), or wrong site-list |
| OMP routes missing after vSmart reboot | OMP reconverges automatically — wait 30–60 seconds |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these solutions first!

### Task 1 — VPN 1 on vEdge1

<details>
<summary>Click to view vEdge1 Configuration</summary>

```bash
! vEdge1 — add VPN 1 service configuration
config
 vpn 1
  interface ge0/1
   ip address 192.168.1.1/24
   no shutdown
  !
 !
commit
```
</details>

<details>
<summary>Click to view Verification</summary>

```bash
vEdge1# show omp routes
1    192.168.1.0/24    10.10.10.11    C I    100    10.10.10.11    ! ← locally originated
```
</details>

---

### Task 2 — VPN 1 on vEdge2

<details>
<summary>Click to view vEdge2 Configuration</summary>

```bash
! vEdge2 — add VPN 1 service configuration
config
 vpn 1
  interface ge0/1
   ip address 192.168.2.1/24
   no shutdown
  !
 !
commit
```
</details>

<details>
<summary>Click to view Verification</summary>

```bash
vSmart# show omp routes
1    192.168.1.0/24    10.10.10.11    C I    100    10.10.10.11    ! ← from vEdge1
1    192.168.2.0/24    10.10.10.12    C I    100    10.10.10.12    ! ← from vEdge2
```
</details>

---

### Task 3 — IPsec Tunnel Verification

<details>
<summary>Click to view Verification Commands</summary>

```bash
vEdge1# show bfd sessions
10.10.10.12    200    up    default    ipsec    172.16.1.1    172.16.2.1    ! ← BFD to vEdge2 up

vEdge1# show ipsec inbound-connections
Source IP         Destination IP    SPI        Encryption      State
172.16.2.1        172.16.1.1        0xabcd1234 AES-256-GCM     active   ! ← active SA from vEdge2
```
</details>

---

### Task 4 — End-to-End LAN Reachability

<details>
<summary>Click to view Verification</summary>

```bash
vEdge1# ping vpn 1 192.168.2.1
3 packets transmitted, 3 received, 0% packet loss   ! ← must be 0% loss

vEdge2# ping vpn 1 192.168.1.1
3 packets transmitted, 3 received, 0% packet loss   ! ← must be 0% loss
```
</details>

---

### Task 5/6 — Control Policy on vSmart

<details>
<summary>Click to view vSmart Policy Configuration</summary>

```bash
! vSmart — add control policy
config
 policy
  site-list SITE1
   site-id 100
  !
  site-list SITE2
   site-id 200
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
 !
 apply-policy
  site-list SITE2
   control-policy PREFER-SITE1-PATH out
  !
 !
commit
```
</details>

<details>
<summary>Click to view Verification</summary>

```bash
vEdge2# show omp routes vpn 1
1    192.168.1.0/24    10.10.10.2    C I    200    10.10.10.11    ! ← preference 200 (raised by policy)
1    192.168.2.0/24    10.10.10.2    C I    100    10.10.10.12    ! ← preference 100 (default, unchanged)

vEdge2# show policy from-vsmart
vsmart-policy: PREFER-SITE1-PATH    ! ← policy name confirmed
type: control
```
</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world SD-WAN routing or policy fault. Inject the fault first,
then diagnose and fix using only show commands.

### Workflow

```bash
python3 setup_lab.py                                   # reset to known-good (solutions state)
python3 scripts/fault-injection/inject_scenario_01.py  # Ticket 1
python3 scripts/fault-injection/apply_solution.py      # restore after each ticket
```

---

### Ticket 1 — vSmart Shows Only One VPN 1 Prefix

After both vEdges were configured, a technician verifies `show omp routes` on vSmart and
finds only 192.168.1.0/24 present. The 192.168.2.0/24 subnet from Branch 2 is completely
missing from the OMP table.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py`

**Success criteria:** `show omp routes` on vSmart shows both 192.168.1.0/24 and 192.168.2.0/24 with status `C I`.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! Step 1 — Check OMP routes on vSmart
vSmart# show omp routes
1    192.168.1.0/24    10.10.10.11    C I    100    ...
! 192.168.2.0/24 missing

! Step 2 — Check VPN 1 interface state on vEdge2
vEdge2# show interface vpn 1
ge0/1   192.168.2.1/24   admin-state: down   oper-state: down   ! ← interface is down

! Step 3 — Check if VPN 1 is configured on vEdge2
vEdge2# show running-config vpn 1
 interface ge0/1
  ip address 192.168.2.1/24
  ! no "no shutdown" — interface is administratively down

! The VPN 1 interface ge0/1 on vEdge2 is missing the no-shutdown command
! OMP will not advertise a prefix for an interface that is down
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
vEdge2# config
vEdge2(config)# vpn 1
vEdge2(config-vpn-1)# interface ge0/1
vEdge2(config-if)# no shutdown
vEdge2(config-if)# commit

! Verify — allow 10–15 seconds for OMP to advertise the prefix
vSmart# show omp routes
1    192.168.1.0/24    10.10.10.11    C I    100    ...
1    192.168.2.0/24    10.10.10.12    C I    100    ...    ! ← now present
```
</details>

---

### Ticket 2 — Site-to-Site Ping Fails Despite OMP Routes Present

Both VPN 1 prefixes show as `C I` in the OMP route table on vSmart. vEdge1 shows
192.168.2.0/24 in its local OMP table. However, `ping vpn 1 192.168.2.1` from vEdge1
fails with 100% packet loss.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py`

**Success criteria:** `ping vpn 1 192.168.2.1` from vEdge1 succeeds with 0% packet loss. `show bfd sessions` on vEdge1 shows vEdge2 session as `up`.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! Step 1 — OMP routes look fine
vEdge1# show omp routes vpn 1
1    192.168.2.0/24    10.10.10.2    C I    100    10.10.10.12    ! ← route present

! Step 2 — Check BFD session state
vEdge1# show bfd sessions
10.10.10.12    200    down    default    ipsec    172.16.1.1    172.16.2.1    ! ← BFD down

! Step 3 — BFD is down means the IPsec tunnel is down
! Check VPN 0 reachability to vEdge2's WAN IP
vEdge1# ping vpn 0 172.16.2.1
ping: sendmsg: No route to host    ! ← cannot reach vEdge2 WAN IP

! Step 4 — Check VPN 0 routing table
vEdge1# show ip route vpn 0
! No default route 0.0.0.0/0 — it has been removed

! Conclusion: VPN 0 default route on vEdge1 is missing → cannot reach vEdge2 transport IP
! → IPsec tunnel cannot form → BFD down → data plane fails (despite control plane routes)
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
vEdge1# config
vEdge1(config)# vpn 0
vEdge1(config-vpn-0)# ip route 0.0.0.0/0 172.16.1.254
vEdge1(config-vpn-0)# commit

! Allow 10–15 seconds for BFD to come up
vEdge1# show bfd sessions
10.10.10.12    200    up    ...    ! ← BFD restored

vEdge1# ping vpn 1 192.168.2.1
3 packets transmitted, 3 received, 0% packet loss   ! ← data plane restored
```
</details>

---

### Ticket 3 — Control Policy Shows No Effect on vEdge2 OMP Table

The team applied the `PREFER-SITE1-PATH` policy but `show omp routes vpn 1` on vEdge2
still shows 192.168.1.0/24 with preference 100 instead of 200. The policy appears to be
configured on vSmart but is not taking effect.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py`

**Success criteria:** `show omp routes vpn 1` on vEdge2 shows 192.168.1.0/24 with `preference: 200`. `show policy from-vsmart` on vEdge2 lists the active policy.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! Step 1 — Check policy on vSmart
vSmart# show running-config policy
 control-policy PREFER-SITE1-PATH
  ...
  (policy definition looks correct)

! Step 2 — Check apply-policy block on vSmart
vSmart# show running-config apply-policy
 apply-policy
  site-list SITE1
   control-policy PREFER-SITE1-PATH out   ! ← WRONG: applied to SITE1, not SITE2
  !

! Step 3 — Confirm the effect on vEdge2
vEdge2# show policy from-vsmart
! Empty — no policy active on vEdge2

! Step 4 — Verify vEdge1's OMP table (it IS receiving the policy, incorrectly)
vEdge1# show policy from-vsmart
vsmart-policy: PREFER-SITE1-PATH    ! ← policy pushed to vEdge1 instead of vEdge2

! Conclusion: apply-policy targets SITE1 instead of SITE2
! The policy should affect what Site 2 receives (apply to SITE2 out)
! Currently it affects what Site 1 receives (apply to SITE1 out)
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
vSmart# config
vSmart(config)# apply-policy
vSmart(config-apply-policy)# no site-list SITE1
vSmart(config-apply-policy)# site-list SITE2
vSmart(config-apply-policy-site)# control-policy PREFER-SITE1-PATH out
vSmart(config-apply-policy-site)# commit

! Verify on vEdge2
vEdge2# show omp routes vpn 1
1    192.168.1.0/24    ...    preference: 200    ! ← policy now effective on correct site

vEdge2# show policy from-vsmart
vsmart-policy: PREFER-SITE1-PATH    ! ← active on vEdge2
```
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] VPN 1 configured on vEdge1 with ge0/1 at 192.168.1.1/24 (interface up)
- [ ] VPN 1 configured on vEdge2 with ge0/1 at 192.168.2.1/24 (interface up)
- [ ] `show omp routes` on vSmart shows both 192.168.1.0/24 and 192.168.2.0/24 as `C I`
- [ ] `show bfd sessions` on vEdge1 shows vEdge2 session as `up`
- [ ] `show bfd sessions` on vEdge2 shows vEdge1 session as `up`
- [ ] `ping vpn 1 192.168.2.1` from vEdge1 succeeds with 0% packet loss
- [ ] `ping vpn 1 192.168.1.1` from vEdge2 succeeds with 0% packet loss
- [ ] `PREFER-SITE1-PATH` policy committed on vSmart with correct site-list targets
- [ ] `show omp routes vpn 1` on vEdge2 shows 192.168.1.0/24 with preference 200
- [ ] `show policy from-vsmart` on vEdge2 lists the active policy

### Troubleshooting

- [ ] Ticket 1 resolved: VPN 1 prefix restored after interface brought up on vEdge2
- [ ] Ticket 2 resolved: BFD and data plane restored after missing VPN 0 default route fixed
- [ ] Ticket 3 resolved: Policy effect confirmed on vEdge2 after apply-policy corrected to SITE2
