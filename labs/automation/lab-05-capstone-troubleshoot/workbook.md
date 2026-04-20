# Lab 05: Automation Capstone — Comprehensive Troubleshooting

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

**Exam Objectives:** 4.6, 6.1, 6.2, 6.5, 6.6 — Automation topic (all blueprint bullets)

This capstone troubleshooting lab validates every automation skill developed across Labs 00–04. You will diagnose and resolve five concurrent faults spanning NETCONF, RESTCONF, EEM, OSPF underlay, and Python API interaction. Unlike earlier labs where faults are injected after setup, the entire network loads in a broken state and you must restore full functionality using only `show` commands and your knowledge of how each protocol should work.

### NETCONF Architecture and Failure Modes

NETCONF operates over SSH on port 830. The IOS-XE process is enabled with `netconf-yang` and exposes capabilities during the initial hello exchange. The two most common failure modes are:

1. **Service not running** — `netconf-yang` is absent from the config, so port 830 is closed. An ncclient `manager.connect()` raises `NetconfSSHError: not connected`.
2. **Missing datastore capability** — NETCONF is running but `netconf-yang feature candidate-datastore` was not enabled. The hello exchange completes, but any `<edit-config>` targeting `<candidate/>` returns `<rpc-error>` with `<error-tag>operation-not-supported</error-tag>`.

```
R1# show netconf-yang status
netconf-yang: enabled
  netconf-yang candidate-datastore: enabled    ← must show "enabled"

R1# show netconf-yang sessions
R  NETCONF sessions: 0
   Pending sessions: 0
```

Key exam point: `show netconf-yang status` distinguishes between "service off" and "service on but feature missing."

### RESTCONF Authentication and HTTP Response Codes

RESTCONF runs over HTTPS (port 443). Three IOS-XE commands must all be present:

| Command | Role |
|---------|------|
| `ip http secure-server` | Enables HTTPS listener |
| `restconf` | Activates the RESTCONF endpoint at `/restconf` |
| `ip http authentication local` | Instructs the HTTP stack to use local user database |

If `ip http authentication local` is absent, the device has no configured authentication method for RESTCONF. Requests return **401 Unauthorized** regardless of what credentials are provided. This is the most common RESTCONF misconfiguration — the service is running and the endpoint is reachable, but every request fails.

HTTP response codes you must know:

| Code | Meaning | Typical RESTCONF Context |
|------|---------|--------------------------|
| 200 | OK | GET returned data successfully |
| 201 | Created | POST created a new resource |
| 204 | No Content | PUT/PATCH/DELETE succeeded (no body returned) |
| 400 | Bad Request | Malformed JSON or XML body |
| 401 | Unauthorized | Authentication failure or missing auth config |
| 404 | Not Found | Resource path does not exist |
| 409 | Conflict | Resource already exists (use PATCH instead of POST) |

### EEM Syslog Pattern Matching

EEM syslog event detection uses regex pattern matching against the IOS syslog message facility/severity/mnemonic string. The pattern `"OSPF-5-ADJCHG"` matches messages of the form `%OSPF-5-ADJCHG: Process 1, Nbr 2.2.2.2 on GigabitEthernet1 from LOADING to FULL`.

Common failure: the pattern string is wrong (wrong mnemonic, wrong facility, extra characters). The applet appears registered in `show event manager policy registered` but the applet counter never increments. You can test whether a pattern would match a known syslog message by examining it against the IOS `debug event manager` output, or by comparing the configured pattern to the expected syslog mnemonic from Cisco documentation.

```
R3# show event manager policy registered
No.  Class     Type    Event Type          Trap  Time Registered         Name
1    applet    system  syslog              Off   Mon Apr 20 00:00:00 2026 SYSLOG-MONITOR
 pattern {OSPF-5-ADJCHG}     ← must match this exactly
```

### OSPF Passive-Interface Behavior

`passive-interface` on a transit link is the most common OSPF troubleshooting scenario on ENCOR. When applied to a point-to-point link between two routers, it suppresses OSPF Hello packets on that interface. The neighbor relationship never forms, and neither router learns the other's routes or loopback. The interface still appears in `show ip interfaces brief` as up/up — it is only the OSPF neighbor formation that is blocked.

Diagnosis path: `show ip ospf neighbor` → missing neighbor → `show ip ospf interface Gi1` → "Passive" shown in state field.

### Controller-Based vs. Traditional Networking

Blueprint bullets 6.1 and 6.2 require conceptual understanding, not CLI configuration. Key distinctions:

| Dimension | Traditional | Controller-Based |
|-----------|-------------|------------------|
| Configuration plane | Distributed (per-device CLI) | Centralized (controller pushes policy) |
| Visibility | Per-device show commands | Single-pane dashboard (Catalyst Center / vManage) |
| Programmability | Netmiko / NETCONF / RESTCONF per device | Northbound REST API to controller |
| Change velocity | Human-in-the-loop per device | Automated intent-based push |
| Failure domain | Single device impact | Controller HA required |

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| NETCONF fault isolation | Distinguish "service not running" from "capability missing" |
| RESTCONF 401 diagnosis | Identify missing HTTP authentication configuration |
| EEM pattern debugging | Verify syslog event patterns match real IOS mnemonic strings |
| OSPF passive-interface troubleshooting | Isolate passive-interface as root cause of missing adjacency |
| Causal chain analysis | Recognize that Ticket 5 is a latent fault masked by Ticket 1 |
| JSON/YANG interpretation | Read and construct RESTCONF JSON payloads from scratch |
| HTTP response code interpretation | Map HTTP status codes to RESTCONF operational states |

---

## 2. Topology & Scenario

### Network Diagram

```
                    ┌─────────────────────┐
                    │         R1          │
                    │  CSR1000v (IOS-XE)  │
                    │  Lo0: 1.1.1.1/32    │
          ┌─────────┤                     ├─────────┐
          │         └─────────┬───────────┘         │
    PC1 (VPCS)          Gi1 (10.1.12.1/30)          │
    192.168.10.10/24          │                      │
    gw: 192.168.10.1          │ 10.1.12.0/30         │
    Gi2 (.1)                  │                      │
                        Gi1 (10.1.12.2/30)           │
                    ┌─────────┴───────────┐          │
                    │         R2          │          │
                    │  CSR1000v (IOS-XE)  │     Gi2 (192.168.10.0/24)
                    │  Lo0: 2.2.2.2/32    │
                    └─────────┬───────────┘
                        Gi2 (10.1.23.1/30)
                              │ 10.1.23.0/30
                        Gi0/0 (10.1.23.2/30)
                    ┌─────────┴───────────┐
                    │         R3          │
                    │   IOSv / EEM Host   │
                    │  Lo0: 3.3.3.3/32    │
                    └─────────┬───────────┘
                         Gi0/1 (.1)
                    192.168.20.0/24
                    PC2 (VPCS) .10
```

### Scenario

Your NOC has deployed a three-router automation platform for CCNP lab practice. The platform uses OSPF for underlay reachability, NETCONF and RESTCONF for programmatic device management on R1 and R2, and EEM applets on R3 for event-driven automation. After a change window last night, multiple reports have come in:

- The Python NETCONF monitoring script is failing at startup
- All RESTCONF requests to R2 are returning authentication errors
- The R3 EEM applet that logs OSPF adjacency changes has gone silent
- A student reports they cannot ping R3 from R1 at all
- After fixing the NETCONF issue, a second Python error has appeared

You have console and SSH access to all devices. Diagnose and restore the platform to full working order.

---

## 3. Hardware & Environment Specifications

### Physical Topology

| Link | Device A | Interface | Device B | Interface | Subnet |
|------|----------|-----------|----------|-----------|--------|
| L1 | R1 | Gi1 | R2 | Gi1 | 10.1.12.0/30 |
| L2 | R2 | Gi2 | R3 | Gi0/0 | 10.1.23.0/30 |
| L3 | R1 | Gi2 | PC1 | eth0 | 192.168.10.0/24 |
| L4 | R3 | Gi0/1 | PC2 | eth0 | 192.168.20.0/24 |

### Device Specifications

| Device | Platform | Role | Loopback0 |
|--------|----------|------|-----------|
| R1 | CSR1000v (IOS-XE) | API Gateway, NETCONF+RESTCONF | 1.1.1.1/32 |
| R2 | CSR1000v (IOS-XE) | RESTCONF target, OSPF transit | 2.2.2.2/32 |
| R3 | IOSv 15.9 | EEM host | 3.3.3.3/32 |
| PC1 | VPCS | End host | — |
| PC2 | VPCS | End host | — |

### Console Access Table

| Device | Port | Connection Command |
|--------|------|--------------------|
| R1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R3 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |

---

## 4. Base Configuration

The following is pre-loaded by `setup_lab.py`. The network starts in a broken state.

**Pre-configured on all devices:**
- Hostname and `no ip domain-lookup`
- Local user `admin` (privilege 15)
- Interface IP addressing (all interfaces up/up)
- SSH version 2 with domain name and source interface

**Pre-configured on R1 and R2:**
- HTTPS server (`ip http secure-server`)
- RESTCONF process enabled
- NETCONF and candidate datastore (R2 only — see below)

**Pre-configured on R3:**
- EEM session CLI username
- Both EEM applets (SYSLOG-MONITOR and BACKUP-CONFIG)
- OSPF process (R2–R3 adjacency is the only working OSPF adjacency at startup)

**NOT working correctly at startup (symptoms only — no fault names):**
- NETCONF on R1 is not accepting connections
- RESTCONF on R2 is rejecting all requests
- R3's SYSLOG-MONITOR applet is not firing on OSPF events
- R1 cannot reach R3 (OSPF partial convergence)
- A secondary R1 NETCONF issue becomes visible after the first is resolved

---

## 5. Lab Challenge: Comprehensive Troubleshooting

> This is a capstone lab. The network is pre-broken.
> Diagnose and resolve 5+ concurrent faults spanning all blueprint bullets.
> No step-by-step guidance is provided — work from symptoms only.

### What You Are Given

- R1 (CSR1000v): RESTCONF is functional. NETCONF has at least one fault. OSPF is partially converged — R1 does not have an OSPF adjacency with R2.
- R2 (CSR1000v): NETCONF is fully functional. RESTCONF is running but authentication is broken. OSPF is partially converged — R2–R3 adjacency is UP, but R1–R2 is DOWN.
- R3 (IOSv): OSPF is fully converged (from R3's perspective: R2 is its only neighbor and that adjacency is up). Both EEM applets are registered. BACKUP-CONFIG is working. SYSLOG-MONITOR is registered but never fires.
- All interface IPs are correct and all interfaces are up/up.
- Credentials: username `admin`, password `Encor-API-2026`.

### What You Must Achieve

All of the following must be true before this lab is complete:

**Network connectivity:**
- OSPF area 0 fully converged: all three routers have complete routing tables including 1.1.1.1/32, 2.2.2.2/32, and 3.3.3.3/32
- PC1 can ping PC2 end-to-end

**NETCONF on R1:**
- Port 830 accepts SSH connections
- `manager.connect()` completes successfully in an ncclient script
- `<edit-config>` targeting the `<candidate/>` datastore succeeds without capability errors

**RESTCONF on R2:**
- `GET https://<R2-IP>/restconf/data/ietf-interfaces:interfaces` returns HTTP 200 with JSON body
- Credentials `admin / Encor-API-2026` are accepted

**EEM on R3:**
- SYSLOG-MONITOR applet fires when an OSPF adjacency state change occurs
- `show event manager history events` shows at least one SYSLOG-MONITOR execution

**Python and JSON interpretation exercises:**

After fixing the network, answer the following in a text scratch file or verbally to yourself:

1. The following RESTCONF response was returned. What HTTP verb was used, and what does the status code indicate?
   ```
   HTTP/1.1 204 No Content
   Content-Type: application/yang-data+json
   ```
   *Answer: PATCH or PUT/DELETE — 204 means the operation succeeded but no data is returned in the body.*

2. Construct a valid RESTCONF JSON body to create a new Loopback interface named `Loopback77` with IP address `77.77.77.77/32` on R1, targeting the `ietf-interfaces` YANG model. The request should use PUT method.

3. You run the following Python snippet. What does `capabilities` contain, and what should you check it for to confirm candidate datastore support?
   ```python
   with manager.connect(host="1.1.1.1", port=830, ...) as m:
       capabilities = list(m.server_capabilities)
   ```
   *Answer: `capabilities` is a list of URN strings from the server hello. Look for `urn:ietf:params:netconf:capability:candidate:1.0`.*

### Rules of Engagement

- Diagnose using only `show` commands (no reading `initial-configs/` or `solutions/`)
- Fix using configuration commands derived from your diagnosis
- Tickets may depend on each other — fix in the order that makes sense
- Use `python3 scripts/fault-injection/apply_solution.py` only to verify your fix or reset after the session

---

## 6. Verification & Analysis

Working state expected outputs for all repaired faults.

### OSPF Full Convergence

```
R1# show ip ospf neighbor
Neighbor ID     Pri   State           Dead Time   Address         Interface
2.2.2.2           0   FULL/  -        00:00:35    10.1.12.2       GigabitEthernet1   ! ← R2 must be FULL

R1# show ip route ospf
      2.0.0.0/32 is subnetted, 1 subnets
O        2.2.2.2 [110/2] via 10.1.12.2, 00:01:00, GigabitEthernet1      ! ← R2 Lo0
      3.0.0.0/32 is subnetted, 1 subnets
O        3.3.3.3 [110/3] via 10.1.12.2, 00:01:00, GigabitEthernet1      ! ← R3 Lo0 reachable via R2
      10.0.0.0/8 is variably subnetted, 4 subnets, 2 masks
O        10.1.23.0/30 [110/2] via 10.1.12.2, 00:01:00, GigabitEthernet1  ! ← R2-R3 segment
      192.168.20.0/24 [110/3] via 10.1.12.2, 00:01:00, GigabitEthernet1  ! ← PC2 network

R2# show ip ospf neighbor
Neighbor ID     Pri   State           Dead Time   Address         Interface
1.1.1.1           0   FULL/  -        00:00:38    10.1.12.1       GigabitEthernet1   ! ← R1 FULL
3.3.3.3           0   FULL/  -        00:00:36    10.1.23.2       GigabitEthernet2   ! ← R3 FULL
```

### R2 OSPF Interface State (passive-interface fault cleared)

```
R2# show ip ospf interface GigabitEthernet1
GigabitEthernet1 is up, line protocol is up
  Internet Address 10.1.12.2/30, Area 0, Attached via Network Statement
  Process ID 1, Router ID 2.2.2.2, Network Type POINT_TO_POINT, Cost: 1
  Transmit Delay is 1 sec, State POINT_TO_POINT   ! ← must NOT show "Passive"
  Timer intervals configured, Hello 10, Dead 40, Wait 40, Retransmit 5
```

### NETCONF on R1 (both faults resolved)

```
R1# show netconf-yang status
netconf-yang: enabled                              ! ← must be "enabled"
  netconf-yang candidate-datastore: enabled        ! ← must be "enabled"

R1# show netconf-yang sessions
R  NETCONF sessions: 0
   Pending sessions: 0
```

Python test (run after fix):
```python
from ncclient import manager
with manager.connect(
    host="1.1.1.1", port=830,
    username="admin", password="Encor-API-2026",
    hostkey_verify=False,
    device_params={"name": "iosxe"}
) as m:
    print("Connected:", m.connected)                    # ! must print True
    caps = list(m.server_capabilities)
    cand = [c for c in caps if "candidate" in c]
    print("Candidate DS:", cand)                        # ! must show candidate URN
```

### RESTCONF on R2 (authentication restored)

```
R2# show running-config | include http
ip http secure-server
ip http authentication local      ! ← must be present
restconf
```

HTTP test:
```bash
curl -k -u admin:Encor-API-2026 \
  https://2.2.2.2/restconf/data/ietf-interfaces:interfaces \
  -H "Accept: application/yang-data+json"
# Expected: HTTP 200 with JSON body beginning {"ietf-interfaces:interfaces": ...}
```

### EEM SYSLOG-MONITOR on R3 (pattern corrected)

```
R3# show event manager policy registered
No.  Class     Type    Event Type          Trap  Time Registered         Name
1    applet    system  syslog              Off   ...                     SYSLOG-MONITOR
 pattern {OSPF-5-ADJCHG}   ! ← must match this exact mnemonic string
2    applet    system  timer cron          Off   ...                     BACKUP-CONFIG
 cron entry {0 0 * * *}

R3# show event manager history events
No.  Time                    Event         Name
1    Mon Apr 20 ...          syslog        SYSLOG-MONITOR    ! ← must appear after adjacency flap
```

---

## 7. Verification Cheatsheet

### OSPF Diagnostics

```
show ip ospf neighbor
show ip ospf interface <interface>
show ip route ospf
debug ip ospf adj
```

| Command | What to Look For |
|---------|-----------------|
| `show ip ospf neighbor` | All expected neighbors in FULL state |
| `show ip ospf interface Gi1` | State must NOT be "Passive" on transit links |
| `show ip route ospf` | All remote loopbacks and subnets present |

> **Exam tip:** `show ip ospf interface` is the definitive command to confirm whether passive-interface is active. `show ip ospf neighbor` only shows the absence of a neighbor — it does not explain why.

### NETCONF Diagnostics

```
show netconf-yang status
show netconf-yang sessions
show netconf-yang statistics
```

| Command | What to Look For |
|---------|-----------------|
| `show netconf-yang status` | `netconf-yang: enabled` AND `candidate-datastore: enabled` |
| `show netconf-yang sessions` | Active sessions listed when Python script connects |

```
! Minimal working IOS-XE NETCONF config
netconf-yang
netconf-yang feature candidate-datastore
```

> **Exam tip:** NETCONF requires two separate commands on IOS-XE: `netconf-yang` (starts the service) and `netconf-yang feature candidate-datastore` (enables the writable candidate datastore). One without the other is a partial configuration.

### RESTCONF Diagnostics

```
show running-config | include http
show running-config | include restconf
show ip http server status
show ip http secure-server status
```

| Command | What to Look For |
|---------|-----------------|
| `show run \| include http` | `ip http secure-server` AND `ip http authentication local` present |
| `show run \| include restconf` | `restconf` global command present |

```
! Minimal working RESTCONF config
ip http secure-server
ip http authentication local
restconf
```

### EEM Diagnostics

```
show event manager policy registered
show event manager history events
show event manager environment
debug event manager
```

| Command | What to Look For |
|---------|-----------------|
| `show event manager policy registered` | Applet listed, pattern string correct |
| `show event manager history events` | Applet execution entries appear after trigger event |

> **Exam tip:** An EEM syslog applet can be registered but silently broken if the `event syslog pattern` string does not match any real IOS syslog message. Always compare the pattern against the exact `%FACILITY-SEVERITY-MNEMONIC` format of the intended trigger message.

### HTTP Response Code Quick Reference

| Code | Meaning | Action |
|------|---------|--------|
| 200 | OK — data returned | Read response body |
| 204 | No Content — operation succeeded | Confirm change in `show run` |
| 400 | Bad Request | Check JSON body structure |
| 401 | Unauthorized | Check `ip http authentication local` |
| 404 | Not Found | Check resource path and YANG module name |
| 409 | Conflict | Resource exists; use PATCH not PUT |

### Common Automation Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| `NetconfSSHError: not connected` | `netconf-yang` not configured |
| `<error-tag>operation-not-supported</error-tag>` | `netconf-yang feature candidate-datastore` missing |
| RESTCONF HTTP 401 | `ip http authentication local` missing |
| RESTCONF HTTP 404 | Wrong YANG module name or path in URL |
| EEM applet registered but never fires | `event syslog pattern` string does not match real messages |
| OSPF neighbor missing on p2p link | `passive-interface` on transit interface |

---

## 8. Solutions (Spoiler Alert!)

> Try to resolve all tickets before reading these solutions.

### Ticket 1 — R1 NETCONF Connection Refused

<details>
<summary>Click to view R1 Fix</summary>

```bash
R1# configure terminal
R1(config)# netconf-yang
R1(config)# end
```

Verification:
```bash
R1# show netconf-yang status
netconf-yang: enabled
```

</details>

### Ticket 2 — R2 RESTCONF Returns 401

<details>
<summary>Click to view R2 Fix</summary>

```bash
R2# configure terminal
R2(config)# ip http authentication local
R2(config)# end
```

Verification:
```bash
R2# show running-config | include http
ip http secure-server
ip http authentication local   ! must be present
restconf
```

</details>

### Ticket 3 — R3 EEM SYSLOG-MONITOR Never Fires

<details>
<summary>Click to view R3 Fix</summary>

```bash
R3# configure terminal
R3(config)# no event manager applet SYSLOG-MONITOR
R3(config)# event manager applet SYSLOG-MONITOR
R3(config-applet)# event syslog pattern "OSPF-5-ADJCHG"
R3(config-applet)# action 1.0 syslog msg "EEM: OSPF adjacency change detected"
R3(config-applet)# action 2.0 cli command "enable"
R3(config-applet)# action 3.0 cli command "show ip ospf neighbor"
R3(config-applet)# end
```

Verification:
```bash
R3# show event manager policy registered
 pattern {OSPF-5-ADJCHG}   ! must match this exactly
```

</details>

### Ticket 4 — R1 Cannot Reach R3

<details>
<summary>Click to view R2 Fix</summary>

```bash
R2# configure terminal
R2(config)# router ospf 1
R2(config-router)# no passive-interface GigabitEthernet1
R2(config-router)# end
```

Verification:
```bash
R2# show ip ospf neighbor
! Must show both 1.1.1.1 (R1) and 3.3.3.3 (R3) in FULL state

R1# show ip route ospf
! Must include 3.3.3.3/32 via R2
```

</details>

### Ticket 5 — R1 NETCONF edit-config Fails With Capability Error

<details>
<summary>Click to view R1 Fix</summary>

This ticket is only visible after Ticket 1 is resolved. Once `netconf-yang` is running,
`edit-config` operations targeting the candidate datastore fail because
`netconf-yang feature candidate-datastore` was never re-enabled.

```bash
R1# configure terminal
R1(config)# netconf-yang feature candidate-datastore
R1(config)# end
```

Verification:
```bash
R1# show netconf-yang status
netconf-yang: enabled
  netconf-yang candidate-datastore: enabled   ! must show enabled
```

</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
R1# show netconf-yang status
R1# show ip ospf neighbor
R2# show ip ospf neighbor
R2# show running-config | include http
R3# show event manager policy registered
R3# show event manager history events
```

</details>

---

## 9. Troubleshooting Scenarios

All faults are pre-loaded by `setup_lab.py`. There are no per-ticket inject scripts — the entire broken state is the starting point.

### Workflow

```bash
python3 setup_lab.py --host <eve-ng-ip>                          # loads all 5 faults
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>  # restore when done
```

---

### Ticket 1 — NETCONF Python Script Fails — Connection Refused on Port 830

Your Python NETCONF monitoring script connects to R1 but immediately throws:
`NetconfSSHError: [Errno 111] Connection refused` before any YANG operations run.
You have confirmed that R1's management interface is reachable via SSH on port 22.

**Success criteria:** An ncclient `manager.connect()` to `1.1.1.1:830` completes without error.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `R1# show netconf-yang status` — if output is blank or shows "disabled", the service is not running.
2. `R1# show running-config | include netconf` — confirms whether `netconf-yang` is present.
3. Port 830 is an SSH sub-service started by `netconf-yang`. No command = no listener.

</details>

<details>
<summary>Click to view Fix</summary>

```bash
R1(config)# netconf-yang
```

After applying, `show netconf-yang status` must show `netconf-yang: enabled`.

</details>

---

### Ticket 2 — R2 RESTCONF Returns 401 Unauthorized on All Requests

Every RESTCONF GET to R2 returns HTTP 401, including with correct credentials. The HTTPS server is running and port 443 is reachable from your management workstation.

**Success criteria:** `GET /restconf/data/ietf-interfaces:interfaces` on R2 returns HTTP 200 with `admin:Encor-API-2026`.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `R2# show running-config | include http` — look for all three required lines: `ip http secure-server`, `ip http authentication local`, `restconf`.
2. If `ip http authentication local` is missing, the HTTP stack has no method to validate credentials — every request is rejected.
3. `show ip http secure-server status` confirms the HTTPS listener is active.

</details>

<details>
<summary>Click to view Fix</summary>

```bash
R2(config)# ip http authentication local
```

After applying, retry the curl/requests GET — response code must be 200.

</details>

---

### Ticket 3 — R3 EEM SYSLOG-MONITOR Applet Never Triggers

The SYSLOG-MONITOR applet is registered and visible in `show event manager policy registered`, but the history shows zero executions even though OSPF adjacency flaps have occurred on the network.

**Success criteria:** After an OSPF adjacency change on R3, `show event manager history events` shows a SYSLOG-MONITOR entry.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `R3# show event manager policy registered` — inspect the `pattern {}` field carefully.
2. Compare the pattern string to the exact syslog mnemonic format: `%OSPF-5-ADJCHG`. The EEM pattern must match `OSPF-5-ADJCHG` within the message.
3. If the pattern contains any incorrect text (wrong mnemonic, wrong facility name), the applet will never fire on real OSPF messages even though it is syntactically valid.
4. To trigger a test event after fixing: `R3(config)# no router ospf 1` then re-add it — this will generate an `%OSPF-5-ADJCHG` syslog.

</details>

<details>
<summary>Click to view Fix</summary>

```bash
R3(config)# no event manager applet SYSLOG-MONITOR
R3(config)# event manager applet SYSLOG-MONITOR
R3(config-applet)# event syslog pattern "OSPF-5-ADJCHG"
R3(config-applet)# action 1.0 syslog msg "EEM: OSPF adjacency change detected"
R3(config-applet)# action 2.0 cli command "enable"
R3(config-applet)# action 3.0 cli command "show ip ospf neighbor"
R3(config-applet)# end
```

</details>

---

### Ticket 4 — R1 Cannot Reach R3 or Any Route Beyond R2

R1 has no OSPF routes to 3.3.3.3/32 or the 10.1.23.0/30 segment. The R1–R2 link is physically up and IPs are correct. R2 and R3 can reach each other fine.

**Success criteria:** `R1# ping 3.3.3.3 source Loopback0` succeeds. `show ip ospf neighbor` on R1 shows R2 in FULL state.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `R1# show ip ospf neighbor` — R2 is absent.
2. `R1# show ip ospf interface GigabitEthernet1` — if GigabitEthernet1 shows as "Passive", Hellos are suppressed and the neighbor will never form.
3. `R2# show ip ospf interface GigabitEthernet1` — check from R2's perspective. If R2's Gi1 is passive, it will not send Hellos to R1 either.
4. `R2# show running-config | section ospf` — look for `passive-interface GigabitEthernet1` under the OSPF process.

</details>

<details>
<summary>Click to view Fix</summary>

```bash
R2(config)# router ospf 1
R2(config-router)# no passive-interface GigabitEthernet1
```

Verify: `R2# show ip ospf neighbor` must show both R1 and R3 in FULL state within 40 seconds.

</details>

---

### Ticket 5 — R1 NETCONF edit-config Fails With Unsupported Capability Error

After resolving Ticket 1, your Python script connects to R1 successfully. However, every `<edit-config>` operation targeting the `<candidate/>` datastore raises:

```
ncclient.operations.rpc.RPCError: <error-tag>operation-not-supported</error-tag>
```

The `<get-config>` against `<running/>` works fine.

**Success criteria:** `<edit-config>` targeting `<candidate/>` succeeds. `show netconf-yang status` shows `candidate-datastore: enabled`.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. `R1# show netconf-yang status` — look for `netconf-yang candidate-datastore: enabled`. If absent or showing "disabled", the feature was not re-enabled when NETCONF was restored.
2. In the Python script, check `list(m.server_capabilities)` for the string `urn:ietf:params:netconf:capability:candidate:1.0`. If missing, the device has not advertised candidate support.
3. Root cause: `netconf-yang feature candidate-datastore` is a separate command from `netconf-yang`. Re-enabling `netconf-yang` (Ticket 1 fix) does not automatically restore the candidate datastore feature.

</details>

<details>
<summary>Click to view Fix</summary>

```bash
R1(config)# netconf-yang feature candidate-datastore
```

Verify: `R1# show netconf-yang status` must show both lines enabled.

</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] OSPF fully converged — all three routers show each other as FULL neighbors
- [ ] R1 can ping 3.3.3.3 from Loopback0
- [ ] PC1 can ping PC2 end-to-end
- [ ] R1 NETCONF service is enabled (`show netconf-yang status`)
- [ ] R1 candidate datastore is enabled (`show netconf-yang status`)
- [ ] ncclient `manager.connect()` to R1:830 succeeds in Python
- [ ] ncclient `<edit-config>` to R1 candidate datastore succeeds
- [ ] R2 RESTCONF returns HTTP 200 with valid JSON (`ip http authentication local` present)
- [ ] R3 SYSLOG-MONITOR pattern matches `OSPF-5-ADJCHG` exactly
- [ ] R3 EEM history shows at least one SYSLOG-MONITOR execution

### Troubleshooting

- [ ] Ticket 1 resolved: R1 NETCONF connection accepted
- [ ] Ticket 2 resolved: R2 RESTCONF authentication working
- [ ] Ticket 3 resolved: R3 EEM SYSLOG-MONITOR applet triggers on OSPF events
- [ ] Ticket 4 resolved: R1–R2 OSPF adjacency restored, R1 has full routing table
- [ ] Ticket 5 resolved: R1 NETCONF candidate datastore available for edit-config

### Python and API Interpretation

- [ ] Identified that HTTP 204 indicates a successful write with no response body
- [ ] Constructed a valid RESTCONF JSON PUT payload for a new Loopback interface
- [ ] Explained the difference between controller-based and traditional per-device management
- [ ] Located the candidate datastore capability URN in ncclient server_capabilities list
