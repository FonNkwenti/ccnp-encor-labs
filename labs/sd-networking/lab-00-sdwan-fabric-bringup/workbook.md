# Lab 00: SD-WAN Fabric Bring-Up and Control Plane

**Topic:** SD-WAN and SD-Access | **Difficulty:** Foundation | **Time:** 90 minutes
**Blueprint:** 1.2 — Cisco Catalyst SD-WAN | 1.2.a — SD-WAN control and data plane elements

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

**Exam Objective:** 1.2 — Explain the working principles of the Cisco Catalyst SD-WAN solution; 1.2.a — SD-WAN control and data planes elements

Cisco Catalyst SD-WAN (formerly Viptela) transforms traditional hub-and-spoke WAN architectures into a software-driven fabric where the control plane is centralised and separated from the data plane. This lab walks through the foundational skill that every subsequent SD-WAN task depends on: bringing up the fabric from scratch. Without a functioning control plane — validated DTLS sessions, OMP peering, and device inventory in vManage — no routing, policy, or data plane work is possible.

---

### SD-WAN Architecture Overview

Cisco Catalyst SD-WAN is built around a strict separation between the **control plane**, the **management plane**, and the **data plane**. Each function is performed by a dedicated component:

| Plane | Component | Role |
|-------|-----------|------|
| Management | vManage | Centralised GUI/API for configuration, monitoring, and policy |
| Orchestration | vBond | First-contact authenticator; discovers and redirects all other components |
| Control | vSmart | OMP route reflector; pushes policies to vEdges |
| Data | vEdge | Branch CPE; builds IPsec tunnels, enforces policies locally |

The fabric operates over an existing WAN transport (internet, MPLS, 4G/LTE) — devices do not require dedicated circuits. R-TRANSPORT in this lab simulates that transport layer.

---

### Fabric Bring-Up Sequence

The bootstrap order is not optional — it is a hard protocol dependency:

```
1. vBond  ← configured first: knows the organization name, acts as the
             rendezvous point for all other components
2. vSmart ← registers with vBond; gets authenticated
3. vManage← registers with vBond; vSmart and vManage establish DTLS sessions
4. vEdge  ← contacts vBond for discovery; authenticated, then connects
             to vSmart (OMP) and vManage (NETCONF/HTTPS)
```

Every component must share the same `organization-name`. A mismatch at any point causes authentication failure and prevents the component from joining the fabric. Authentication is certificate-based; in lab environments, enterprise-root self-signed certificates are used.

---

### Control Plane Transport: DTLS and OMP

**DTLS (Datagram TLS)** is the transport for all SD-WAN control-plane sessions:
- vBond ↔ vSmart: DTLS tunnel for orchestration
- vBond ↔ vEdge: DTLS for initial discovery (temporary)
- vSmart ↔ vEdge: permanent DTLS tunnel for OMP

**OMP (Overlay Management Protocol)** runs over these DTLS sessions between vSmart and vEdges. It is conceptually similar to BGP:

| Feature | OMP | BGP |
|---------|-----|-----|
| Transport | DTLS (port 12346) | TCP (port 179) |
| Route types | `omp-route`, `tloc-route`, `service-route` | Unicast/multicast prefixes |
| Route reflector | vSmart | Route reflector router |
| Policy enforcement | vSmart pushes to vEdges | Distributed |

A **TLOC (Transport Location)** is the SD-WAN equivalent of a next-hop — it identifies a specific vEdge tunnel endpoint (system-ip + colour + encapsulation).

---

### VPN Structure in Viptela OS

Viptela OS uses **VPNs** (not VRFs) for traffic segmentation. Key VPNs in this lab:

| VPN | Purpose | Interfaces |
|-----|---------|-----------|
| VPN 0 | Transport VPN — WAN-facing, IPsec tunnels | ge0/0 (vEdges), eth1 (controllers) |
| VPN 1 | Service VPN — LAN-facing, user data (configured in lab-01) | ge0/1 (vEdges) |
| VPN 512 | Out-of-band management VPN | eth0 (vManage) |

VPN 0 is the only VPN active in this lab. The `tunnel-interface` sub-configuration under a VPN 0 interface enables SD-WAN functionality on that interface.

---

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| SD-WAN component identification | Distinguish vManage, vSmart, vBond, vEdge roles in a given scenario |
| Fabric bootstrap sequencing | Configure components in the correct order: vBond → vSmart → vManage → vEdge |
| DTLS control-plane verification | Use `show control connections` to confirm authenticated sessions |
| OMP session verification | Use `show omp peers` and `show omp routes` to confirm overlay routing |
| vManage dashboard navigation | Read device inventory and control status from the management GUI |

---

## 2. Topology & Scenario

**Scenario:** ENCOR-LAB is migrating its branch WAN from a traditional hub-and-spoke MPLS
design to Cisco Catalyst SD-WAN. The network team has received new vManage, vSmart, vBond,
and vEdge 20.6.2 appliances. Your task is to perform the initial fabric bring-up: bootstrap
the three SD-WAN controllers, connect the two branch vEdges to the fabric, and confirm the
complete control plane is operational before the team proceeds with routing and policy
configuration in subsequent labs.

R-TRANSPORT is a pre-deployed IOSv router that simulates the ISP/transport backbone between
sites. It has IP addressing pre-configured and does not participate in the SD-WAN overlay.

```
    ┌────────────────┐    ┌────────────────┐    ┌─────────────────┐
    │    vManage     │    │    vSmart      │    │     vBond       │
    │   (NMS/GUI)    │    │  (Controller)  │    │ (Orchestrator)  │
    │ 172.16.0.1/24  │    │ 172.16.0.2/24  │    │  172.16.0.3/24  │
    │ sys: 10.10.10.1│    │ sys: 10.10.10.2│    │  sys:10.10.10.3 │
    └───────┬────────┘    └───────┬────────┘    └────────┬────────┘
       eth1 │                eth1 │                 ge0/0│
            │                    │                      │
            └──────────────────┬─┘                      │
                               │    172.16.0.0/24        │
                         Gi0/0 │ 172.16.0.254/24         │
               ┌───────────────┴─────────────────────────┘
               │              R-TRANSPORT                 │
               │          (ISP Simulation)                │
               │         Lo0: 9.9.9.9/32                  │
               └──────────────┬────────────────┬──────────┘
                    Gi0/1     │                │    Gi0/2
               172.16.1.254/24│                │172.16.2.254/24
                              │                │
               172.16.1.1/24  │                │  172.16.2.1/24
                         ge0/0│                │ge0/0
                   ┌──────────┴────┐    ┌──────┴────────────┐
                   │    vEdge1     │    │     vEdge2        │
                   │  (Branch 1)   │    │   (Branch 2)      │
                   │sys:10.10.10.11│    │ sys:10.10.10.12   │
                   │  site-id: 100 │    │  site-id: 200     │
                   └───────────────┘    └───────────────────┘
```

**Key dependency patterns:**
- All three controllers (vManage, vSmart, vBond) share the 172.16.0.0/24 transport subnet; R-TRANSPORT:Gi0/0 is the shared gateway at 172.16.0.254
- vEdge1 and vEdge2 are on separate /24 WAN subnets (172.16.1.0/24 and 172.16.2.0/24) connected to R-TRANSPORT:Gi0/1 and Gi0/2 respectively
- All devices use R-TRANSPORT as their default gateway for inter-site reachability — R-TRANSPORT is the simulated "internet"
- VPN 0 is the only active VPN in this lab; VPN 1 (LAN/service VPN) is introduced in lab-01

---

## 3. Hardware & Environment Specifications

### Device Specifications

| Device | Platform | RAM | vCPUs | Role |
|--------|---------|-----|-------|------|
| vManage | vtmgmt-20.6.2-001 | ~16 GB | 2 | SD-WAN NMS/Dashboard |
| vSmart | vtsmart-20.6.2 | ~4 GB | 1 | OMP Route Reflector/Policy |
| vBond | vtbond-20.6.2 | ~2 GB | 1 | Orchestrator/Authenticator |
| vEdge1 | vtedge-20.6.2 | ~2 GB | 1 | Branch Site 1 CPE |
| vEdge2 | vtedge-20.6.2 | ~2 GB | 1 | Branch Site 2 CPE |
| R-TRANSPORT | IOSv 15.9 (iosv) | 512 MB | 1 | ISP/Transport Simulation |

> **Note:** vManage requires approximately 16 GB RAM. Verify your EVE-NG host has
> sufficient capacity before starting the lab.

### Cabling Table

| Link | Source | Target | Subnet | Notes |
|------|--------|--------|--------|-------|
| L1 | vBond:ge0/0 | R-TRANSPORT:Gi0/0 | 172.16.0.0/24 | Shared controller transport segment |
| L2 | vSmart:eth1 | R-TRANSPORT:Gi0/0 | 172.16.0.0/24 | Same segment as L1 (bridge/hub) |
| L3 | vManage:eth1 | R-TRANSPORT:Gi0/0 | 172.16.0.0/24 | Same segment as L1 (bridge/hub) |
| L4 | vEdge1:ge0/0 | R-TRANSPORT:Gi0/1 | 172.16.1.0/24 | Branch 1 WAN transport |
| L5 | vEdge2:ge0/0 | R-TRANSPORT:Gi0/2 | 172.16.2.0/24 | Branch 2 WAN transport |

> **EVE-NG Setup Note:** Links L1, L2, and L3 all connect to the 172.16.0.0/24 network.
> In EVE-NG, connect vBond:ge0/0, vSmart:eth1, vManage:eth1, and R-TRANSPORT:Gi0/0 to
> the same network bridge (cloud or management network object) to create the shared segment.

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

The following is pre-configured in `initial-configs/` when you run `setup_lab.py`:

**Pre-configured (IP addressing only):**
- R-TRANSPORT: interface IP addresses on Gi0/0 (172.16.0.254/24), Gi0/1 (172.16.1.254/24), Gi0/2 (172.16.2.254/24); hostname
- vBond: VPN 0 interface ge0/0 IP address (172.16.0.3/24)
- vSmart: VPN 0 interface eth1 IP address (172.16.0.2/24)
- vManage: VPN 0 interface eth1 IP address (172.16.0.1/24); VPN 512 management interface
- vEdge1: VPN 0 interface ge0/0 IP address (172.16.1.1/24)
- vEdge2: VPN 0 interface ge0/0 IP address (172.16.2.1/24)

**NOT pre-configured (you configure these):**
- SD-WAN system identity on any device (system-ip, site-id, organization-name)
- vBond local designation
- DTLS tunnel interfaces on vBond, vSmart, vEdge1, vEdge2
- Default routes (VPN 0 gateway configuration)
- vManage, vSmart, vBond inter-controller DTLS sessions
- OMP peering between vEdges and vSmart
- R-TRANSPORT static routes for inter-subnet reachability

---

## 5. Lab Challenge: Core Implementation

### Task 1: Establish R-TRANSPORT as the ISP Backbone

R-TRANSPORT is the transport router connecting all SD-WAN components. It needs static
routes to ensure all 172.16.x.0/24 subnets are reachable from one another.

- Verify R-TRANSPORT has three active interfaces: one in 172.16.0.0/24, one in 172.16.1.0/24, one in 172.16.2.0/24.
- Confirm that all three subnets appear as directly connected in the routing table.
- Test reachability from R-TRANSPORT to all six device IP addresses using extended ping sourced from each interface.

**Verification:** `show ip route` must show three directly connected /24 subnets. `ping 172.16.0.1 source Gi0/0` and equivalent pings to 172.16.0.2, 172.16.0.3, 172.16.1.1, 172.16.2.1 must all succeed.

---

### Task 2: Bootstrap vBond — Organisation Identity and Local Orchestrator Role

vBond is the first SD-WAN component to configure. It must know the organisation name and declare itself as the local orchestrator before any other component can join the fabric.

- Configure the system identity on vBond: assign a system-ip from the 10.10.10.0/24 block, set the organisation name to `ENCOR-LAB`.
- Declare vBond as the local orchestrator by setting its own IP address as the vBond address.
- Configure the VPN 0 tunnel interface to allow DTLS connections from other components.
- Set a default route in VPN 0 pointing to R-TRANSPORT as the gateway.

**Verification:** `show control local-properties` must show the system-ip, organisation name, vBond address, and certificate serial. `show control connections` should show the device is listening (no peers yet at this stage).

---

### Task 3: Bootstrap vSmart — Controller Registration

vSmart is the OMP route reflector. It must register with vBond to receive the authenticated component list.

- Configure the system identity on vSmart: assign a system-ip and set the organisation name to `ENCOR-LAB` (must match vBond exactly).
- Configure the vBond address on vSmart so it knows where to register.
- Enable the VPN 0 tunnel interface on vSmart.
- Set a default route in VPN 0 toward R-TRANSPORT.

**Verification:** `show control connections` on vSmart must show a DTLS session to vBond with state `up`. `show omp peers` should be empty at this stage (no vEdges yet), but the OMP process must be running.

---

### Task 4: Bootstrap vManage — Management Plane Registration

vManage registers with vBond and establishes a NETCONF/HTTPS channel to vSmart.

- Configure the system identity on vManage: assign a system-ip and set the organisation name to `ENCOR-LAB`.
- Configure the vBond address on vManage.
- Set a default route in VPN 0 toward R-TRANSPORT.

**Verification:** From vManage CLI, `show control connections` must show connections to both vBond and vSmart. Access the vManage GUI at `https://172.16.0.1` — the dashboard should show vManage, vSmart, and vBond in the device inventory.

---

### Task 5: Onboard vEdge1 — Branch Site 1

vEdge1 represents Branch Site 1 (site-id 100). It connects to the fabric through the transport VPN.

- Configure the system identity on vEdge1: assign a system-ip, a site-id of `100`, and the organisation name `ENCOR-LAB`.
- Configure the vBond address on vEdge1 so it knows where to initiate contact.
- Enable the VPN 0 WAN tunnel interface with the correct IP address.
- Set a default route in VPN 0 pointing to R-TRANSPORT as the gateway.

**Verification:** `show control connections` on vEdge1 must show active sessions to vBond, vSmart, and vManage. `show omp peers` must show vSmart as an active OMP peer.

---

### Task 6: Onboard vEdge2 — Branch Site 2

vEdge2 represents Branch Site 2 (site-id 200). Repeat the same onboarding process for the second branch.

- Configure the system identity on vEdge2: assign a system-ip, a site-id of `200`, and the organisation name `ENCOR-LAB`.
- Configure the vBond address, VPN 0 tunnel interface, and default route.

**Verification:** `show control connections` on vEdge2 must show active sessions to vBond, vSmart, and vManage. `show omp peers` on both vEdge1 and vEdge2 must show vSmart as active.

---

### Task 7: Verify the Complete Control Plane

With all five SD-WAN components joined, perform a systematic verification sweep.

- On vSmart, confirm both vEdges appear as OMP peers with state `up`.
- On vSmart, run `show omp tlocs` to confirm that TLOC routes from both vEdges are present.
- On each vEdge, confirm that the TLOC of the other vEdge is visible in the OMP TLOC table.
- On vManage CLI, run `show control connections` and confirm six total control sessions (vBond, vSmart, vEdge1, vEdge2 from vManage's perspective).

**Verification:** `show omp peers` on vSmart must show two entries (vEdge1 and vEdge2, both `up`). `show omp tlocs` on vSmart must show TLOCs for system-ip 10.10.10.11 and 10.10.10.12.

---

### Task 8: Explore vManage Dashboard

vManage is the single-pane-of-glass for SD-WAN operations. Familiarise yourself with the key panels before moving to labs that involve policy and data plane.

- Navigate to **Monitor > Network** — confirm all six devices appear in the inventory with a green status indicator.
- Navigate to **Monitor > WAN Edge** — confirm vEdge1 and vEdge2 show `Control Up` status.
- Locate the **Control Connections** panel for vEdge1 — confirm it shows active connections to vBond, vSmart, and vManage.
- Identify where you would push a device template (Configuration > Templates) — do not create one yet; this is orientation only.

**Verification:** All devices show green/`Up` status in the vManage dashboard. No red or yellow alerts present in the notification panel.

---

## 6. Verification & Analysis

### Task 1 — R-TRANSPORT Routing Table

```
R-TRANSPORT# show ip route
Codes: C - connected, S - static, R - RIP ...

      172.16.0.0/16 is variably subnetted, 6 subnets, 2 masks
C        172.16.0.0/24 is directly connected, GigabitEthernet0/0   ! ← controller subnet
C        172.16.0.254/32 is directly connected, GigabitEthernet0/0
C        172.16.1.0/24 is directly connected, GigabitEthernet0/1   ! ← vEdge1 WAN subnet
C        172.16.1.254/32 is directly connected, GigabitEthernet0/1
C        172.16.2.0/24 is directly connected, GigabitEthernet0/2   ! ← vEdge2 WAN subnet
C        172.16.2.254/32 is directly connected, GigabitEthernet0/2
```

All three transport subnets must appear as directly connected — no static routes needed on R-TRANSPORT since all SD-WAN component subnets are directly attached.

### Task 2 — vBond Control Properties and Connection State

```
vBond# show control local-properties
personality                       vbond
organization-name                 ENCOR-LAB              ! ← must match all other components
domain-id                         1
site-id                           0
device-id                         10.10.10.3             ! ← system-ip
system-ip                         10.10.10.3
vbond                             172.16.0.3             ! ← local vBond address (self)
certificate-status                Installed               ! ← certificate must be installed
```

### Task 3 — vSmart Control Connection to vBond

```
vSmart# show control connections
                                         PEER                          PEER
PEER    PEER PEER          PEER          PSEUDO PSEUDO
TYPE    PROT SYSTEM IP     LOCAL COLOR   KEY    PORT       LOCAL ADDRESS        REMOTE ADDRESS       DOMAIN ID UPTIME        PEER STATE
------  ---- ------------- ------------- ------ ---------- -------------------- -------------------- --------- ------------- ----------
vbond   dtls 0.0.0.0       default       0      12346      172.16.0.2           172.16.0.3           0         00:05:23      up         ! ← vBond session up
```

The peer type `vbond` with state `up` confirms vSmart has successfully authenticated with the orchestrator.

### Task 5/6 — vEdge Control Connections (Both Branches)

```
vEdge1# show control connections
PEER    PEER PEER          PEER          PSEUDO PSEUDO
TYPE    PROT SYSTEM IP     LOCAL COLOR   KEY    PORT       LOCAL ADDRESS        REMOTE ADDRESS       DOMAIN ID UPTIME        PEER STATE
------  ---- ------------- ------------- ------ ---------- -------------------- -------------------- --------- ------------- ----------
vbond   dtls 0.0.0.0       default       0      12346      172.16.1.1           172.16.0.3           0         00:03:10      up         ! ← vBond session up
vsmart  dtls 10.10.10.2    default       0      12346      172.16.1.1           172.16.0.2           1         00:02:45      up         ! ← vSmart (OMP) session up
vmanage dtls 10.10.10.1    default       0      12346      172.16.1.1           172.16.0.1           1         00:02:30      up         ! ← vManage (NETCONF) session up
```

All three sessions must be `up` before declaring vEdge1 fully onboarded.

### Task 7 — OMP Peer Table on vSmart

```
vSmart# show omp peers
PEER             TYPE    DOMAIN ID    STATE      UPTIME                            R/I/S
----------------------------------------------------------------------
10.10.10.11      vedge   1            up         00:04:12                          0/0/0  ! ← vEdge1 in OMP table
10.10.10.12      vedge   1            up         00:03:55                          0/0/0  ! ← vEdge2 in OMP table
```

Both vEdges must appear with state `up`. The R/I/S columns (Received/Installed/Sent routes) show 0/0/0 at this stage — no VPN 1 prefixes are advertised yet (that is lab-01).

### Task 7 — TLOC Table on vSmart

```
vSmart# show omp tlocs
Code:
------
C   -> chosen
I   -> installed
Red -> redistributed
Rej -> rejected
L   -> looped
R   -> resolved
S   -> stale
Ext -> extranet

                         TLOC                                        ADDRESS
IP               COLOR    ENCAP  FROM PEER            C I Rd Rej L R S Ext    IP
-----------------------------------------------------------------------------------------------------------------
10.10.10.11      default  ipsec  10.10.10.11          C I  -  -   -  -  -  -  172.16.1.1    ! ← vEdge1 TLOC
10.10.10.12      default  ipsec  10.10.10.12          C I  -  -   -  -  -  -  172.16.2.1    ! ← vEdge2 TLOC
```

Both TLOCs must appear as `C I` (chosen + installed). The `IP` column shows the physical WAN address associated with each TLOC — this is what vEdges use to build IPsec tunnels to each other (covered in lab-01).

---

## 7. Verification Cheatsheet

### SD-WAN System Identity Configuration

```
system
 host-name <HOSTNAME>
 system-ip  <10.10.10.X>
 site-id    <N>
 organization-name ENCOR-LAB
 vbond <172.16.0.3>          ! omit 'local' on non-vBond devices
```

| Command | Purpose |
|---------|---------|
| `system-ip` | Unique 32-bit router ID — like a loopback; must be unique per device |
| `site-id` | Groups vEdges into a site; all vEdges at same physical site share a site-id |
| `organization-name` | Must match exactly across ALL fabric components — case-sensitive |
| `vbond <ip> local` | vBond-only: declares itself as the orchestrator |

> **Exam tip:** The organisation name is the single most common source of fabric join failure. It is case-sensitive and must be identical on every component including the certificate.

### VPN 0 Tunnel Interface Configuration (vEdge / vSmart / vBond)

```
vpn 0
 interface ge0/0
  ip address <IP/PREFIX>
  tunnel-interface
   encapsulation ipsec
   allow-service all
  no shutdown
 ip route 0.0.0.0/0 <GATEWAY>
```

| Command | Purpose |
|---------|---------|
| `tunnel-interface` | Enables SD-WAN mode on the interface — makes it a TLOC endpoint |
| `encapsulation ipsec` | Sets IPsec as the data-plane encapsulation for this tunnel |
| `allow-service all` | Permits DTLS/OMP/NETCONF traffic on this interface (lab shortcut) |
| `ip route 0.0.0.0/0` | VPN 0 default route — must point to the transport gateway |

> **Exam tip:** Without `tunnel-interface`, the interface is a plain routed interface in VPN 0. The device cannot join the fabric.

### Control Connection Verification

| Command | What to Look For |
|---------|-----------------|
| `show control connections` | All expected peers listed with `up` state |
| `show control connections-history` | Diagnose flapping or rejected connections |
| `show control local-properties` | Confirm system-ip, org-name, certificate status |
| `show certificate serial` | Verify certificate is installed on the device |

### OMP Verification Commands

| Command | What to Look For |
|---------|-----------------|
| `show omp peers` | Each vEdge shows state `up` (on vSmart); vSmart shows `up` (on vEdge) |
| `show omp tlocs` | TLOCs for all remote vEdges present and `C I` (chosen + installed) |
| `show omp routes` | VPN 1 prefixes (empty in lab-00 — appears after lab-01) |
| `show omp summary` | OMP process status, number of routes in RIB/FIB |

### Common SD-WAN Fabric Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| Control connection stuck in `connect` state | Organisation name mismatch or wrong vBond IP |
| Certificate error in `show control connections-history` | Certificate not installed or org-name mismatch |
| vEdge shows vBond session up but no vSmart session | vSmart not yet registered with vBond |
| `show omp peers` empty on vSmart | vEdges not reachable to 172.16.0.2 via VPN 0 default route |
| vManage shows device as `unreachable` | NETCONF connection failed — check VPN 0 default route on vEdge |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these solutions first!

### Task 1 — R-TRANSPORT Configuration

<details>
<summary>Click to view R-TRANSPORT Configuration</summary>

```bash
! R-TRANSPORT — IOSv — IP addressing already pre-configured in initial-configs
! Verify that all interfaces are up and subnets are directly connected
! No additional static routes are required — all SD-WAN component subnets are directly attached

hostname R-TRANSPORT
no ip domain-lookup
!
interface GigabitEthernet0/0
 description Transport-Controllers-172.16.0.0/24
 ip address 172.16.0.254 255.255.255.0
 no shutdown
!
interface GigabitEthernet0/1
 description Transport-vEdge1-172.16.1.0/24
 ip address 172.16.1.254 255.255.255.0
 no shutdown
!
interface GigabitEthernet0/2
 description Transport-vEdge2-172.16.2.0/24
 ip address 172.16.2.254 255.255.255.0
 no shutdown
!
```
</details>

<details>
<summary>Click to view Verification</summary>

```bash
R-TRANSPORT# show ip interface brief
Interface          IP-Address       OK? Method Status   Protocol
GigabitEthernet0/0 172.16.0.254     YES manual up       up
GigabitEthernet0/1 172.16.1.254     YES manual up       up
GigabitEthernet0/2 172.16.2.254     YES manual up       up

R-TRANSPORT# ping 172.16.0.1     ! vManage
Success rate is 100 percent
R-TRANSPORT# ping 172.16.0.2     ! vSmart
Success rate is 100 percent
R-TRANSPORT# ping 172.16.0.3     ! vBond
Success rate is 100 percent
R-TRANSPORT# ping 172.16.1.1     ! vEdge1
Success rate is 100 percent
R-TRANSPORT# ping 172.16.2.1     ! vEdge2
Success rate is 100 percent
```
</details>

---

### Task 2 — Bootstrap vBond

<details>
<summary>Click to view vBond Configuration</summary>

```bash
! vBond — Viptela OS 20.6.2 — configure in config mode
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
<summary>Click to view Verification</summary>

```bash
vBond# show control local-properties
personality                       vbond
organization-name                 ENCOR-LAB
system-ip                         10.10.10.3
vbond                             172.16.0.3
certificate-status                Installed
```
</details>

---

### Task 3 — Bootstrap vSmart

<details>
<summary>Click to view vSmart Configuration</summary>

```bash
! vSmart — Viptela OS 20.6.2
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
<summary>Click to view Verification</summary>

```bash
vSmart# show control connections
PEER    PROT SYSTEM IP     STATE
vbond   dtls 0.0.0.0       up       ! ← vBond DTLS session established
```
</details>

---

### Task 4 — Bootstrap vManage

<details>
<summary>Click to view vManage Configuration</summary>

```bash
! vManage — Viptela OS 20.6.2
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

---

### Task 5 — Onboard vEdge1

<details>
<summary>Click to view vEdge1 Configuration</summary>

```bash
! vEdge1 — Viptela OS 20.6.2
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
commit
```
</details>

<details>
<summary>Click to view Verification</summary>

```bash
vEdge1# show control connections
PEER    PROT SYSTEM IP     STATE
vbond   dtls 0.0.0.0       up
vsmart  dtls 10.10.10.2    up    ! ← OMP session to vSmart established
vmanage dtls 10.10.10.1    up    ! ← NETCONF session to vManage established
```
</details>

---

### Task 6 — Onboard vEdge2

<details>
<summary>Click to view vEdge2 Configuration</summary>

```bash
! vEdge2 — Viptela OS 20.6.2
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
commit
```
</details>

---

### Task 7 — Control Plane Verification

<details>
<summary>Click to view Complete Verification Commands</summary>

```bash
! On vSmart — confirm both vEdges in OMP
vSmart# show omp peers
PEER             TYPE    STATE
10.10.10.11      vedge   up      ! ← vEdge1
10.10.10.12      vedge   up      ! ← vEdge2

! On vSmart — confirm TLOCs from both sites
vSmart# show omp tlocs
IP               COLOR    ENCAP  STATE
10.10.10.11      default  ipsec  C I    ! ← vEdge1 TLOC chosen+installed
10.10.10.12      default  ipsec  C I    ! ← vEdge2 TLOC chosen+installed

! On vEdge1 — confirm TLOC of remote vEdge visible
vEdge1# show omp tlocs
10.10.10.12      default  ipsec  C I    ! ← vEdge2 TLOC known to vEdge1
```
</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world SD-WAN fabric fault. Inject the fault first, then
diagnose and fix using only show commands.

### Workflow

```bash
python3 setup_lab.py                                   # reset to known-good (solutions state)
python3 scripts/fault-injection/inject_scenario_01.py  # Ticket 1
python3 scripts/fault-injection/apply_solution.py      # restore after each ticket
```

---

### Ticket 1 — vEdge1 Cannot Join the Fabric

The branch team at Site 1 reports that vEdge1 has been configured and powered on, but the
vManage dashboard shows it as offline. The NOC reports `show control connections` on vEdge1
shows the vBond session is stuck in `connect` state.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py`

**Success criteria:** `show control connections` on vEdge1 shows `up` sessions to vBond,
vSmart, and vManage. vEdge1 appears online in the vManage dashboard.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! Step 1 — Check control connection state on vEdge1
vEdge1# show control connections
PEER    PROT SYSTEM IP     STATE
vbond   dtls 0.0.0.0       connect    ! ← stuck in connect — cannot reach vBond

! Step 2 — Check control connection history for rejection details
vEdge1# show control connections-history
! Look for "certificate invalid" or "no route to host" messages

! Step 3 — Verify the vBond address configured on vEdge1
vEdge1# show control local-properties
vbond             172.16.0.4       ! ← WRONG: should be 172.16.0.3

! Step 4 — Verify reachability to actual vBond
vEdge1# ping vpn 0 172.16.0.3
! If ping succeeds, it's a config error (wrong vBond IP), not a reachability issue
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! Correct the vBond address on vEdge1
vEdge1# config
vEdge1(config)# system
vEdge1(config-system)# vbond 172.16.0.3
vEdge1(config-system)# commit

! Verify fix
vEdge1# show control connections
vbond   dtls 0.0.0.0       up
vsmart  dtls 10.10.10.2    up
vmanage dtls 10.10.10.1    up
```
</details>

---

### Ticket 2 — vSmart Shows No OMP Peers After Both vEdges Join

Both vEdges show their vBond session as `up`, but neither vEdge appears in `show omp peers`
on vSmart. The fabric appears to accept the vEdges initially, but OMP sessions never form.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py`

**Success criteria:** `show omp peers` on vSmart shows both 10.10.10.11 and 10.10.10.12 with
state `up`.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! Step 1 — Check OMP peers on vSmart
vSmart# show omp peers
! Empty — no peers listed

! Step 2 — Check control connections on vSmart
vSmart# show control connections
vbond   dtls 0.0.0.0       up
! vBond is up but no vEdges appear

! Step 3 — Check control connections-history on vEdge1
vEdge1# show control connections-history
! Look for "Security violation" or "org-name mismatch" in rejection reason

! Step 4 — Compare organization-name across devices
vEdge1# show control local-properties
organization-name    ENCOR-LABS      ! ← WRONG: extra 'S' — should be 'ENCOR-LAB'

vSmart# show control local-properties
organization-name    ENCOR-LAB       ! ← correct

! Mismatch confirmed: org-name must be identical on all devices
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! Fix organisation name on vEdge1 (and vEdge2 if also affected)
vEdge1# config
vEdge1(config)# system
vEdge1(config-system)# organization-name ENCOR-LAB
vEdge1(config-system)# commit

! Verify OMP peer formation on vSmart (allow 30–60 seconds for session to establish)
vSmart# show omp peers
10.10.10.11    vedge    up
10.10.10.12    vedge    up
```
</details>

---

### Ticket 3 — vSmart Control Connection to vBond Goes Down

The NOC receives an alert: vSmart control connection to vBond has dropped. vEdges are now
showing their vSmart OMP session as `down`. No configuration changes were made by the team.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py`

**Success criteria:** `show control connections` on vSmart shows vBond session as `up`.
`show omp peers` on vSmart returns to showing both vEdges as `up`.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! Step 1 — Check control connections on vSmart
vSmart# show control connections
vbond   dtls 0.0.0.0       down   ! ← vBond session dropped

! Step 2 — Test reachability from vSmart to vBond
vSmart# ping vpn 0 172.16.0.3
PING 172.16.0.3: 56 data bytes
ping: sendmsg: No route to host    ! ← no route — default route missing in VPN 0

! Step 3 — Check VPN 0 routing table on vSmart
vSmart# show ip route vpn 0
! No default route (0.0.0.0/0) present — it has been removed

! The default route in VPN 0 pointing to 172.16.0.254 is missing
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! Restore the default route in VPN 0 on vSmart
vSmart# config
vSmart(config)# vpn 0
vSmart(config-vpn-0)# ip route 0.0.0.0/0 172.16.0.254
vSmart(config-vpn-0)# commit

! Verify — allow 10–15 seconds for DTLS to re-establish
vSmart# show control connections
vbond   dtls 0.0.0.0       up

vSmart# show omp peers
10.10.10.11    vedge    up
10.10.10.12    vedge    up
```
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] R-TRANSPORT has three interfaces in the correct /24 subnets and all show `up/up`
- [ ] vBond configured with system-ip 10.10.10.3, org-name ENCOR-LAB, and `local` vBond designation
- [ ] vSmart shows `up` DTLS control connection to vBond
- [ ] vManage shows `up` connections to both vBond and vSmart
- [ ] vEdge1 shows three `up` control connections: vBond, vSmart, vManage
- [ ] vEdge2 shows three `up` control connections: vBond, vSmart, vManage
- [ ] `show omp peers` on vSmart shows both 10.10.10.11 and 10.10.10.12 as `up`
- [ ] `show omp tlocs` on vSmart shows TLOCs for both vEdges with state `C I`
- [ ] vManage dashboard shows all six devices with green/`Up` status

### Troubleshooting

- [ ] Ticket 1 resolved: vEdge1 rejoined fabric after wrong vBond address corrected
- [ ] Ticket 2 resolved: OMP peers restored after organisation name mismatch fixed
- [ ] Ticket 3 resolved: vSmart control connection restored after default route recovery
