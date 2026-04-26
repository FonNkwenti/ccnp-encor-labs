# Lab 02: SD-WAN Data Plane and Application Policies

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

This lab completes the SD-WAN story started in labs 00 and 01. The control plane is up (lab-00), routing is flowing (lab-01), and now you focus on the data plane: the IPsec tunnels that carry user traffic, the BFD probes that measure path quality, and the application-aware routing (app-route) policies that steer traffic based on real-time measurements. Blueprint bullet 1.2.b is fully addressed here — you will be able to articulate both the power of SD-WAN (automatic rerouting, centralised policy) and its real-world limitations (controller dependency, scale complexity, certificate management).

---

### BFD Path Quality Monitoring

BFD (Bidirectional Forwarding Detection) in SD-WAN serves a dual purpose that distinguishes it from traditional routing BFD:

1. **Liveness detection** — confirms the IPsec tunnel is still reachable
2. **Path quality measurement** — measures loss, latency, and jitter per tunnel colour

BFD probes run continuously over each IPsec tunnel between vEdges. Every probe sample contributes to a rolling average. The app-route policy evaluates whether the current average meets a defined **SLA class** threshold:

| Metric | How Measured | Typical Threshold |
|--------|-------------|------------------|
| Loss (%) | Percentage of BFD probes lost | ≤ 5% |
| Latency (ms) | Round-trip time per probe | ≤ 150 ms |
| Jitter (ms) | Variation in RTT between probes | ≤ 30 ms |

If any metric exceeds the SLA threshold, the app-route policy can steer traffic to an alternative transport colour (e.g., from `default` to `biz-internet` or `mpls`). In this lab topology there is only one colour (`default`), so you observe the measurement mechanism without an actual failover path — the concept is the same in production.

```
vEdge1 ◄────── BFD probe (loss/latency/jitter) ──────► vEdge2
              IPsec tunnel over R-TRANSPORT
              (app-route policy evaluates metrics here)
```

---

### App-Route Policies

App-route policies are the SD-WAN implementation of **application-aware routing (AAR)**. They live on vSmart and are pushed to vEdges via OMP. Unlike control policies (which affect the OMP RIB), app-route policies affect which **TLOC/colour** is used for actual data forwarding.

The policy evaluation flow:
1. vEdge receives an app-route policy from vSmart via OMP
2. For each matched traffic flow, vEdge checks the BFD metrics for each available TLOC
3. If the preferred colour's metrics fall outside the SLA class, vEdge switches to the next eligible colour
4. When the preferred path recovers, traffic switches back (with a configurable hold-down)

```
app-route-policy APP-AWARE-ROUTING
 vpn-list VPN1                    ← which service VPN to apply to
  sequence 10
   match source-ip 0.0.0.0/0     ← all traffic in VPN 1
   action sla-class DEFAULT       ← must meet DEFAULT SLA thresholds
    preferred-color default       ← prefer the 'default' colour tunnel
```

An **SLA class** defines the threshold that triggers rerouting:
```
sla-class DEFAULT
 loss    5     ← reroute if loss > 5%
 latency 150   ← reroute if latency > 150 ms
 jitter  30    ← reroute if jitter > 30 ms
```

---

### Tunnel Statistics and the Data Plane Verification Stack

SD-WAN provides a layered set of data-plane verification commands. Use them in order from outermost to innermost:

| Layer | Command | What It Shows |
|-------|---------|--------------|
| BFD session | `show bfd sessions` | Tunnel liveness + path quality averages |
| IPsec SAs | `show ipsec inbound-connections` | Active security associations |
| Tunnel counters | `show tunnel statistics` | Bytes/packets per tunnel, errors |
| App-route stats | `show app-route stats` | Per-tunnel BFD sample counts and current SLA status |
| Policy from vSmart | `show policy from-vsmart` | Which app-route / control policies are active on this vEdge |

A healthy data plane shows: BFD `up`, active inbound/outbound IPsec SAs, non-zero tunnel byte counters, and the expected app-route policy listed in `show policy from-vsmart`.

---

### SD-WAN Benefits and Limitations — Complete Picture (1.2.b)

By the end of lab-02 you have personally observed every major SD-WAN benefit in this topology. Exam questions on 1.2.b ask for concise explanations — use the table below as your reference.

**Benefits:**
| Benefit | Lab Evidence |
|---------|-------------|
| Transport independence | vEdge tunnels over a simulated ISP; same config would work over MPLS or 4G |
| Centralised management | vManage provides single-pane visibility for all three labs |
| Automatic encryption | All VPN 1 traffic traverses IPsec tunnels with no per-flow config |
| Application-aware routing | App-route policy monitors BFD metrics and steers traffic automatically |
| Zero-touch provisioning | vEdges joined via vBond with no per-site manual config (lab-00) |
| Centralised policy push | One vSmart config change affects all vEdges simultaneously |

**Limitations:**
| Limitation | Why It Matters |
|------------|---------------|
| Controller dependency | vSmart outage freezes policy updates; existing routes persist |
| Single controller = SPOF | This lab has one vSmart — production requires HA pairs |
| Certificate management overhead | Onboarding requires valid certs; expiry causes fabric disruption |
| GUI-dependent operations | Many advanced features (templates, device groups) require vManage GUI |
| Scale complexity | Large deployments need multiple vSmarts, TLOC design, and regional controllers |

---

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| BFD metric interpretation | Read loss/latency/jitter from `show bfd sessions` and correlate to SLA class |
| App-route policy configuration | Define SLA class, app-route-policy, vpn-list, and apply-policy on vSmart |
| Tunnel statistics analysis | Use `show tunnel statistics` and `show app-route stats` for data-plane health |
| Policy verification | Confirm policy receipt on vEdges via `show policy from-vsmart` |
| SD-WAN benefits/limitations articulation | Answer 1.2.b exam questions with specific, evidence-backed statements |

---

## 2. Topology & Scenario

**Scenario:** With routing and LAN connectivity proven in lab-01, the ENCOR-LAB team
now needs to demonstrate application-aware routing to management. The goal is to
configure an app-route policy that monitors BFD path quality between the two vEdges and
automatically prefers the best-performing transport path. The team will also observe the
full data-plane verification workflow — from BFD sessions through tunnel statistics — and
document the SD-WAN solution's benefits and limitations for a management summary.

```
    ┌────────────────┐    ┌──────────────────────┐    ┌─────────────────┐
    │    vManage     │    │       vSmart          │    │     vBond       │
    │   (NMS/GUI)    │    │  (OMP + App-Route     │    │ (Orchestrator)  │
    │ 172.16.0.1/24  │    │   Policy Controller)  │    │  172.16.0.3/24  │
    └───────┬────────┘    └───────┬───────────────┘    └────────┬────────┘
       eth1 │                eth1 │ pushes APP-AWARE-ROUTING      │
            └──────────────────┬─┘ via OMP to vEdges              │
                               │     172.16.0.0/24                │
                         Gi0/0 │ 172.16.0.254/24                  │
               ┌───────────────┴──────────────────────────────────┘
               │              R-TRANSPORT                          │
               │          (ISP / Transport Sim)                    │
               └──────────────┬────────────────┬───────────────────┘
                    Gi0/1     │                │    Gi0/2
               172.16.1.254/24│                │172.16.2.254/24
                              │  IPsec + BFD   │
               172.16.1.1/24  │◄──────────────►│  172.16.2.1/24
                         ge0/0│  BFD probes     │ge0/0
                   ┌──────────┴────┐    ┌──────┴────────────┐
                   │    vEdge1     │    │     vEdge2        │
                   │  (Branch 1)   │    │   (Branch 2)      │
                   │sys:10.10.10.11│    │ sys:10.10.10.12   │
                   │ge0/1:         │    │ge0/1:             │
                   │192.168.1.1/24 │    │192.168.2.1/24     │
                   └───────────────┘    └───────────────────┘
                     VPN 1: app-route policy enforced here
```

**Key dependency patterns:**
- App-route policies are pushed from vSmart to vEdges via OMP — they appear in `show policy from-vsmart` on each vEdge
- BFD probes run between ge0/0 WAN interfaces (VPN 0) — they measure transport path quality
- The app-route policy is applied to VPN 1 traffic — it steers user data based on WAN path health
- In this 2-site / 1-colour topology, "preferred-color default" means the only available path is always the preferred path; the SLA mechanism is visible in the metrics even without an active failover event

---

## 3. Hardware & Environment Specifications

### Device Specifications

| Device | Platform | Role | Change from Lab-01 |
|--------|---------|------|--------------------|
| vManage | vtmgmt-20.6.2-001 | NMS/Dashboard | None |
| vSmart | vtsmart-20.6.2 | OMP + App-Route Policy | **Add app-route policy + SLA class** |
| vBond | vtbond-20.6.2 | Orchestrator | None |
| vEdge1 | vtedge-20.6.2 | Branch Site 1 CPE | None (receives policy push) |
| vEdge2 | vtedge-20.6.2 | Branch Site 2 CPE | None (receives policy push) |
| R-TRANSPORT | IOSv 15.9 | ISP Simulation | None |

### Cabling Table

| Link | Source | Target | Subnet | Notes |
|------|--------|--------|--------|-------|
| L1–L3 | vBond/vSmart/vManage | R-TRANSPORT:Gi0/0 | 172.16.0.0/24 | Control plane (unchanged) |
| L4 | vEdge1:ge0/0 | R-TRANSPORT:Gi0/1 | 172.16.1.0/24 | BFD probes traverse this link |
| L5 | vEdge2:ge0/0 | R-TRANSPORT:Gi0/2 | 172.16.2.0/24 | BFD probes traverse this link |

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

`initial-configs/` for this lab is an **exact copy of lab-01 solutions** — the complete fabric with VPN 1 enabled on both vEdges and the `PREFER-SITE1-PATH` control policy active on vSmart.

**Pre-configured (from lab-01 solutions):**
- Complete SD-WAN fabric (all five components joined)
- VPN 1 active on vEdge1 (192.168.1.1/24) and vEdge2 (192.168.2.1/24)
- BFD sessions active between vEdge1 and vEdge2
- `PREFER-SITE1-PATH` control policy active on vSmart (applied to SITE2 out)
- End-to-end VPN 1 reachability proven

**NOT pre-configured (you configure these):**
- VPN-list definition for VPN 1
- SLA class with loss/latency/jitter thresholds
- App-route policy matching all VPN 1 traffic
- Application of the app-route policy to both site-lists

---

## 5. Lab Challenge: Core Implementation

### Task 1: Examine the Existing Data Plane Tunnels

Before adding any policy, audit the current data-plane state. This establishes a baseline you will compare to after app-route policy is applied.

- On vEdge1, examine all active BFD sessions and record the current loss, latency, and jitter values for the tunnel to vEdge2.
- On vEdge1, examine the tunnel statistics and note the current byte and packet counters.
- On vEdge1, examine the current app-route statistics to see the per-sample BFD measurement history.
- On vSmart, confirm there is no app-route policy yet in the active policy list.

**Verification:** `show bfd sessions` must show one active session to 10.10.10.12 with state `up`. `show tunnel statistics` must show non-zero byte counters. `show policy from-vsmart` on vEdge1 should show only the control policy from lab-01 (no app-route policy yet).

---

### Task 2: Define the VPN-List and SLA Class on vSmart

App-route policies reference a VPN-list (which service VPNs the policy applies to) and an SLA class (the quality thresholds that trigger rerouting). Define these building blocks before creating the policy itself.

- On vSmart, define a vpn-list named `VPN1` containing VPN 1.
- Define an SLA class named `DEFAULT` with the following thresholds: maximum loss 5%, maximum latency 150 ms, maximum jitter 30 ms.

**Verification:** `show running-config policy` on vSmart must show the `VPN1` vpn-list and the `DEFAULT` sla-class with the correct threshold values.

---

### Task 3: Create the App-Route Policy

With the building blocks in place, create the application-aware routing policy.

- On vSmart, create an app-route-policy named `APP-AWARE-ROUTING`.
- Add a sequence that matches all traffic in VPN 1 (source and destination both 0.0.0.0/0).
- Set the action to evaluate against the `DEFAULT` SLA class with the `default` transport colour as the preferred path.

**Verification:** `show running-config policy` on vSmart must show the complete `APP-AWARE-ROUTING` policy with the correct vpn-list, match criteria, and action referencing the `DEFAULT` sla-class.

---

### Task 4: Apply the App-Route Policy to Both Sites

Apply the app-route policy to both branch sites so that vEdge1 and vEdge2 both enforce path quality monitoring.

- In the `apply-policy` block on vSmart, add the `APP-AWARE-ROUTING` policy to the `SITE1` site-list.
- Also add `APP-AWARE-ROUTING` to the `SITE2` site-list (which already has the control policy from lab-01).
- Commit the configuration.

**Verification:** `show policy from-vsmart` on both vEdge1 and vEdge2 must list `APP-AWARE-ROUTING` as an active app-route policy. `show app-route stats` on each vEdge must show BFD sample data populating for the tunnel to the remote site.

---

### Task 5: Verify BFD Path Quality Metrics

With the app-route policy active, examine the detailed path quality data that drives automatic rerouting decisions.

- On vEdge1, examine `show app-route stats` and identify the mean loss, mean latency, and mean jitter values for the tunnel to vEdge2.
- Confirm that the current metrics are within the `DEFAULT` SLA thresholds (loss ≤ 5%, latency ≤ 150 ms, jitter ≤ 30 ms).
- Note the SLA compliance status in the output — it should show the tunnel as meeting the SLA.

**Verification:** `show app-route stats` on vEdge1 must show the 10.10.10.12 entry with mean loss, latency, and jitter values all within threshold. The SLA class compliance field must show `met`.

---

### Task 6: Observe Path Degradation Behaviour

Simulate path degradation by temporarily blocking traffic on R-TRANSPORT and observe how BFD metrics respond.

- On R-TRANSPORT, apply a temporary access-list to block all traffic between the two vEdge WAN subnets (172.16.1.0/24 and 172.16.2.0/24) for approximately 30 seconds, then remove it.
- While the block is active, observe `show bfd sessions` on vEdge1 and watch for loss to increase.
- After removing the block, confirm BFD sessions recover and metrics return to within-SLA values.

**Verification:** During the block, `show bfd sessions` on vEdge1 must show increasing loss % toward or above 5%. After the block is removed, state returns to `up` and loss drops back to 0%. `show app-route stats` will reflect the degradation window in its sample history.

---

### Task 7: Benefits and Limitations Summary

Prepare a concise analysis suitable for a management briefing — no CLI required.

- List three specific SD-WAN benefits that this three-lab sequence demonstrated directly (not theoretical).
- Identify two limitations that are visible in this lab topology (hint: one relates to redundancy, one relates to operations).
- Explain in one sentence WHY app-route policies execute on the vEdge rather than on the vSmart controller, and why that design choice matters for scale.

**Verification:** Review your answers against Section 1 (Benefits and Limitations tables). For the last point: app-route policies execute locally on vEdges so that data-plane steering decisions do not require a round-trip to the controller — this is the key scalability argument for centralized policy with distributed enforcement.

---

## 6. Verification & Analysis

### Task 1 — Baseline BFD Session State

```
vEdge1# show bfd sessions
                                      SOURCE TLOC      REMOTE TLOC
SYSTEM IP        SITE ID   STATE    COLOR    ENCAP    COLOR    ENCAP    SOURCE IP        REMOTE IP        DST PORT
---------- --------  -----    -------  ------   -------  ------   ---------        ----------       --------
10.10.10.12      200       up       default  ipsec    default  ipsec    172.16.1.1       172.16.2.1       12347   ! ← state must be 'up'
```

```
vEdge1# show app-route stats
Tunnel statistics:
  Remote System IP: 10.10.10.12   ! ← tunnel to vEdge2
  Mean loss: 0%                    ! ← baseline — 0 loss in lab environment
  Mean latency: 2 ms               ! ← typical for local EVE-NG lab
  Mean jitter: 1 ms                ! ← typical for local EVE-NG lab
  SLA class met: DEFAULT           ! ← within threshold before policy applied
```

### Task 4 — App-Route Policy Received on vEdges

```
vEdge1# show policy from-vsmart
Centralized Policy
  vsmart-policy: PREFER-SITE1-PATH    ! ← control policy from lab-01 (still active)
  version:       1
  type:          control

  vsmart-policy: APP-AWARE-ROUTING    ! ← new app-route policy pushed from vSmart
  version:       1
  type:          appRoute             ! ← type must be 'appRoute' not 'control'
```

Both policies must appear. The `type` field distinguishes them: `control` for the OMP control policy, `appRoute` for the data-plane app-route policy.

### Task 5 — App-Route Statistics with SLA Evaluation

```
vEdge1# show app-route stats
Tunnel: 10.10.10.12
  Color: default / ipsec
  Total packets sent:  1200
  Total packets lost:  0                 ! ← 0 loss = 0% (within 5% threshold)
  Mean latency:        2 ms              ! ← well within 150 ms threshold
  Mean jitter:         1 ms              ! ← well within 30 ms threshold
  Number of probes:    120
  SLA: DEFAULT         met               ! ← 'met' confirms all thresholds satisfied
```

### Task 6 — BFD During Path Degradation

```
! While R-TRANSPORT ACL is active:
vEdge1# show bfd sessions
10.10.10.12    200    up    default    ipsec    172.16.1.1    172.16.2.1    ...
  ! Loss will climb as ACL drops BFD probes — watch the % field increase

! After ACL removal (10–15 seconds):
vEdge1# show bfd sessions
10.10.10.12    200    up    default    ipsec    ...   ! ← state returns to 'up', loss drops to 0%

! Post-recovery app-route stats will show the degradation window:
vEdge1# show app-route stats
  Total packets lost: 12    ! ← reflects the probes lost during the ACL window
  Mean loss: 2%             ! ← rolling average — will clear over subsequent samples
```

---

## 7. Verification Cheatsheet

### SLA Class Configuration

```
policy
 sla-class <NAME>
  loss    <0-100>
  latency <0-1000>
  jitter  <0-1000>
```

| Parameter | Description |
|-----------|-------------|
| `loss` | Maximum acceptable packet loss percentage (0–100) |
| `latency` | Maximum acceptable round-trip latency in milliseconds |
| `jitter` | Maximum acceptable jitter in milliseconds |

> **Exam tip:** All three thresholds are optional — omitting one means that metric is not evaluated for SLA compliance. For a latency-only SLA, configure only `latency`.

### App-Route Policy Configuration

```
policy
 vpn-list <NAME>
  vpn <N>
 !
 app-route-policy <POLICY-NAME>
  vpn-list <NAME>
   sequence <N>
    match
     source-ip <PREFIX>
     destination-ip <PREFIX>
    !
    action sla-class <SLA-NAME>
     preferred-color <COLOR>
    !
   !
  !
 !
!
apply-policy
 site-list <SITE>
  app-route-policy <POLICY-NAME>
 !
!
```

| Keyword | Purpose |
|---------|---------|
| `vpn-list` | Restricts the policy to specific service VPNs |
| `match source-ip / destination-ip` | Traffic selector — use 0.0.0.0/0 for all traffic |
| `action sla-class` | References an SLA class for quality evaluation |
| `preferred-color` | Which transport colour to prefer when SLA is met |
| `apply-policy` (no direction) | App-route policies have no `in`/`out` — applied per-site |

> **Exam tip:** App-route policies in `apply-policy` have NO direction keyword (`in`/`out`) — unlike control policies which require `out`. This is a common exam distractor.

### BFD and Data-Plane Verification

| Command | What to Look For |
|---------|-----------------|
| `show bfd sessions` | State `up`; loss/latency/jitter within SLA thresholds |
| `show app-route stats` | `SLA: <name> met` for active tunnels; sample count > 0 |
| `show tunnel statistics` | Non-zero bytes/packets on active tunnels |
| `show ipsec inbound-connections` | Active SA entries for all remote vEdge WAN IPs |
| `show policy from-vsmart` | Both control and app-route policies listed; types correct |
| `show policy from-vsmart detail` | Full policy content for verification |

### Common App-Route / Data-Plane Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| `show policy from-vsmart` shows no app-route policy | `apply-policy` block missing or not committed on vSmart |
| App-route policy present but `show app-route stats` empty | VPN-list references wrong VPN number |
| BFD session state `down` after policy applied | Transport reachability issue — VPN 0 default route missing |
| `SLA: DEFAULT not met` immediately | Thresholds too aggressive for lab environment (e.g., loss 0%) |
| vEdge not receiving policy after vSmart commit | OMP reconvergence delay — wait 30–60 seconds and retry |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these solutions first!

### Task 1 — Baseline Examination

<details>
<summary>Click to view Baseline Verification Commands</summary>

```bash
! On vEdge1 — before adding app-route policy
vEdge1# show bfd sessions
10.10.10.12    200    up    default    ipsec    172.16.1.1    172.16.2.1

vEdge1# show tunnel statistics
Remote TLOC IP: 172.16.2.1
Bytes sent: 98304     ! ← non-zero confirms active tunnel
Bytes received: 94208

vEdge1# show app-route stats
! Minimal data before policy is applied

vEdge1# show policy from-vsmart
vsmart-policy: PREFER-SITE1-PATH    type: control    ! ← only control policy, no app-route yet
```
</details>

---

### Task 2/3 — VPN-List, SLA Class, and App-Route Policy on vSmart

<details>
<summary>Click to view vSmart Configuration</summary>

```bash
! vSmart — add vpn-list, sla-class, and app-route-policy
config
 policy
  vpn-list VPN1
   vpn 1
  !
  sla-class DEFAULT
   loss    5
   latency 150
   jitter  30
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
commit
```
</details>

---

### Task 4 — Apply Policy to Both Sites

<details>
<summary>Click to view Apply-Policy Configuration</summary>

```bash
! vSmart — update apply-policy block for both sites
config
 apply-policy
  site-list SITE1
   app-route-policy APP-AWARE-ROUTING
  !
  site-list SITE2
   app-route-policy APP-AWARE-ROUTING
  !
 !
commit
```

> Note: SITE2 already has `control-policy PREFER-SITE1-PATH out` from lab-01.
> Adding the app-route policy to SITE2 does not remove the existing control policy.
</details>

<details>
<summary>Click to view Verification</summary>

```bash
vEdge1# show policy from-vsmart
vsmart-policy: PREFER-SITE1-PATH    type: control       ! ← lab-01 policy still active
vsmart-policy: APP-AWARE-ROUTING    type: appRoute       ! ← new app-route policy active

vEdge2# show policy from-vsmart
vsmart-policy: PREFER-SITE1-PATH    type: control
vsmart-policy: APP-AWARE-ROUTING    type: appRoute
```
</details>

---

### Task 6 — Path Degradation Simulation on R-TRANSPORT

<details>
<summary>Click to view R-TRANSPORT ACL Commands</summary>

```bash
! R-TRANSPORT — apply temporary ACL to simulate path degradation
R-TRANSPORT# config terminal
R-TRANSPORT(config)# ip access-list extended BLOCK-VEDGE
R-TRANSPORT(config-ext-nacl)# deny ip 172.16.1.0 0.0.0.255 172.16.2.0 0.0.0.255
R-TRANSPORT(config-ext-nacl)# deny ip 172.16.2.0 0.0.0.255 172.16.1.0 0.0.0.255
R-TRANSPORT(config-ext-nacl)# permit ip any any
R-TRANSPORT(config-ext-nacl)# exit
R-TRANSPORT(config)# interface GigabitEthernet0/1
R-TRANSPORT(config-if)# ip access-group BLOCK-VEDGE in
R-TRANSPORT(config-if)# exit

! Observe BFD loss increase on vEdge1 (run repeatedly for ~30 seconds)
! vEdge1# show bfd sessions   (watch loss % climb)

! Remove ACL after 30 seconds
R-TRANSPORT(config)# interface GigabitEthernet0/1
R-TRANSPORT(config-if)# no ip access-group BLOCK-VEDGE in
R-TRANSPORT(config-if)# exit
R-TRANSPORT(config)# no ip access-list extended BLOCK-VEDGE
```
</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world SD-WAN data-plane or policy fault. Inject the fault
first, then diagnose and fix using only show commands.

### Workflow

```bash
python3 setup_lab.py                                   # reset to known-good (solutions state)
python3 scripts/fault-injection/inject_scenario_01.py  # Ticket 1
python3 scripts/fault-injection/apply_solution.py      # restore after each ticket
```

---

### Ticket 1 — App-Route Policy Missing from Both vEdges

After committing the app-route policy on vSmart, the NOC reports that `show policy
from-vsmart` on both vEdge1 and vEdge2 shows only the control policy from lab-01 — the
`APP-AWARE-ROUTING` policy is not appearing despite being visible in vSmart running-config.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py`

**Success criteria:** `show policy from-vsmart` on both vEdge1 and vEdge2 lists `APP-AWARE-ROUTING` with type `appRoute`. `show app-route stats` populates with BFD sample data.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! Step 1 — Confirm policy exists on vSmart
vSmart# show running-config policy
 app-route-policy APP-AWARE-ROUTING
  ...    ! ← policy definition is present

! Step 2 — Check apply-policy block on vSmart
vSmart# show running-config apply-policy
 apply-policy
  site-list SITE2
   control-policy PREFER-SITE1-PATH out
   ! APP-AWARE-ROUTING is missing from SITE2 apply block
  !
  ! SITE1 has no app-route-policy entry either

! Step 3 — Confirm effect on vEdge1
vEdge1# show policy from-vsmart
vsmart-policy: PREFER-SITE1-PATH    type: control    ! ← only this, APP-AWARE-ROUTING absent

! Conclusion: app-route policy was defined but never added to apply-policy for any site
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
vSmart# config
vSmart(config)# apply-policy
vSmart(config-apply-policy)# site-list SITE1
vSmart(config-apply-policy-site)# app-route-policy APP-AWARE-ROUTING
vSmart(config-apply-policy-site)# exit
vSmart(config-apply-policy)# site-list SITE2
vSmart(config-apply-policy-site)# app-route-policy APP-AWARE-ROUTING
vSmart(config-apply-policy-site)# commit

! Allow 30 seconds for OMP to push to vEdges
vEdge1# show policy from-vsmart
vsmart-policy: APP-AWARE-ROUTING    type: appRoute    ! ← now present
vEdge2# show policy from-vsmart
vsmart-policy: APP-AWARE-ROUTING    type: appRoute    ! ← now present
```
</details>

---

### Ticket 2 — App-Route Policy Present but show app-route stats Is Empty

Both vEdges show `APP-AWARE-ROUTING` in `show policy from-vsmart`, but `show app-route
stats` on both vEdges returns no tunnel data. BFD sessions are still `up` and VPN 1 pings
succeed, but the app-route policy appears to be evaluating nothing.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py`

**Success criteria:** `show app-route stats` on vEdge1 shows BFD sample data for the tunnel to 10.10.10.12 with `SLA: DEFAULT met`.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! Step 1 — Confirm app-route policy is received
vEdge1# show policy from-vsmart
vsmart-policy: APP-AWARE-ROUTING    type: appRoute    ! ← policy present

! Step 2 — Check app-route stats
vEdge1# show app-route stats
! Empty — no tunnel entries

! Step 3 — Check the vpn-list definition on vSmart
vSmart# show running-config policy
 vpn-list VPN1
  vpn 2    ! ← WRONG: should be vpn 1

! Step 4 — Confirm traffic in VPN 1 is not being evaluated
vEdge1# show app-route stats vpn 1
! Still empty — the policy only evaluates VPN 2, not VPN 1

! Conclusion: vpn-list VPN1 references vpn 2 instead of vpn 1 — policy scope mismatch
```
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

! Allow OMP reconvergence (30 seconds)
vEdge1# show app-route stats
Tunnel: 10.10.10.12
  Mean loss: 0%
  Mean latency: 2 ms
  SLA: DEFAULT met    ! ← app-route now evaluating VPN 1 traffic
```
</details>

---

### Ticket 3 — BFD Shows Up but Tunnel Statistics Show Zero Bytes

The NOC reports an anomaly: `show bfd sessions` on vEdge2 shows the tunnel to vEdge1 as
`up`, but `show tunnel statistics` shows 0 bytes sent and 0 bytes received on that tunnel.
VPN 1 pings from vEdge2 to 192.168.1.1 are also failing.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py`

**Success criteria:** `show tunnel statistics` on vEdge2 shows non-zero byte counters. `ping vpn 1 192.168.1.1` from vEdge2 succeeds with 0% packet loss.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! Step 1 — BFD appears up, but tunnel bytes are zero
vEdge2# show bfd sessions
10.10.10.11    100    up    default    ipsec    172.16.2.1    172.16.1.1    ! ← up

vEdge2# show tunnel statistics
Remote TLOC IP: 172.16.1.1
Bytes sent:     0    ! ← zero bytes — data plane not using this tunnel
Bytes received: 0

! Step 2 — VPN 1 ping fails
vEdge2# ping vpn 1 192.168.1.1
100% packet loss

! Step 3 — Check OMP route for 192.168.1.0/24 on vEdge2
vEdge2# show omp routes vpn 1
! No entry for 192.168.1.0/24 — route is missing from vEdge2's OMP table

! Step 4 — Check vSmart OMP routes
vSmart# show omp routes
1    192.168.1.0/24    10.10.10.11    C I    200    10.10.10.11    ! ← route present on vSmart
! But vSmart is not reflecting it to vEdge2...

! Step 5 — Check OMP peers on vSmart
vSmart# show omp peers
10.10.10.11    vedge    up
10.10.10.12    vedge    down    ! ← vEdge2 OMP session is down

! Step 6 — Check control connections on vEdge2
vEdge2# show control connections
vbond    dtls    0.0.0.0      up
vsmart   dtls    10.10.10.2   down    ! ← DTLS to vSmart is down

! Step 7 — Check VPN 0 routing on vEdge2
vEdge2# show ip route vpn 0
! Default route 0.0.0.0/0 missing — cannot reach vSmart at 172.16.0.2

! Conclusion: VPN 0 default route removed on vEdge2 → cannot reach vSmart →
! OMP session down → no route reflection → VPN 1 reachability fails
! BFD appears up because it uses the direct vEdge-to-vEdge IPsec path (not via vSmart)
! but without OMP routes, data plane cannot forward VPN 1 traffic
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
vEdge2# config
vEdge2(config)# vpn 0
vEdge2(config-vpn-0)# ip route 0.0.0.0/0 172.16.2.254
vEdge2(config-vpn-0)# commit

! Allow OMP to reconverge (30–60 seconds)
vEdge2# show control connections
vsmart    dtls    10.10.10.2    up    ! ← OMP session restored

vEdge2# show omp routes vpn 1
1    192.168.1.0/24    ...    C I    200    10.10.10.11    ! ← route reflected again

vEdge2# ping vpn 1 192.168.1.1
3 packets transmitted, 3 received, 0% packet loss    ! ← data plane restored

vEdge2# show tunnel statistics
Bytes sent: 3360    ! ← non-zero; tunnel carrying traffic again
```
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] `show bfd sessions` on vEdge1 shows vEdge2 tunnel as `up` with non-zero byte counters in `show tunnel statistics`
- [ ] `VPN1` vpn-list and `DEFAULT` sla-class committed on vSmart with correct threshold values (loss 5%, latency 150 ms, jitter 30 ms)
- [ ] `APP-AWARE-ROUTING` app-route policy created with sequence matching all VPN 1 traffic and referencing `DEFAULT` sla-class
- [ ] Policy applied to both `SITE1` and `SITE2` site-lists in `apply-policy` block (no direction keyword)
- [ ] `show policy from-vsmart` on vEdge1 shows `APP-AWARE-ROUTING` with type `appRoute`
- [ ] `show policy from-vsmart` on vEdge2 shows `APP-AWARE-ROUTING` with type `appRoute`
- [ ] `show app-route stats` on both vEdges shows tunnel data with `SLA: DEFAULT met`
- [ ] Path degradation simulation performed: BFD loss increase observed during R-TRANSPORT ACL, recovery confirmed after ACL removal

### Troubleshooting

- [ ] Ticket 1 resolved: app-route policy appearing on both vEdges after apply-policy corrected
- [ ] Ticket 2 resolved: app-route stats populated after vpn-list corrected to vpn 1
- [ ] Ticket 3 resolved: VPN 1 reachability restored and tunnel bytes non-zero after VPN 0 default route re-added to vEdge2
