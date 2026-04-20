# Lab 04: Automation Capstone — Full Protocol Mastery

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

**Exam Objective:** 4.6 Interpret Python scripts using libraries (requests, ncclient) | 6.1 Identify Python data types | 6.2 Construct Python scripts with JSON | 6.5 Interpret RESTCONF response codes (200, 201, 204, 400, 401, 404, 409) | 6.6 Configure and apply EEM applets

This capstone lab unifies the entire automation chapter into a single end-to-end challenge. You will stand up NETCONF and RESTCONF services from scratch on two CSR1000v routers, create EEM event triggers on a third IOSv router, and write Python scripts that interact with all three management planes simultaneously. The lab tests your ability to select the right tool (NETCONF for datastore-level operations, RESTCONF for REST-style resource management, EEM for local event-driven automation), interpret error responses, and reason about YANG data models — skills that appear consistently in ENCOR exam scenarios.

---

### NETCONF Architecture and Datastores

NETCONF (RFC 6241) is a network management protocol transported over SSH (port 830). It defines four standard operations — `get`, `get-config`, `edit-config`, and `commit` — plus optional extensions such as `lock`/`unlock` and `validate`. NETCONF organises configuration into named datastores:

| Datastore | Description |
|-----------|-------------|
| `running` | Active configuration currently in effect |
| `candidate` | Staging area — changes applied here are NOT active until `commit` |
| `startup` | Persisted config loaded at boot |

IOS-XE requires `netconf-yang feature candidate-datastore` to enable the candidate datastore. Without this, `edit-config` must target `running` directly, which skips the commit/rollback safety net.

NETCONF messages are encoded in XML and follow YANG models. The ietf-interfaces YANG module (`urn:ietf:params:xml:ns:yang:ietf-interfaces`) describes interfaces in a vendor-neutral way; `Cisco-IOS-XE-native` provides access to platform-specific constructs such as OSPF.

```xml
<!-- Minimal get-config request — running datastore, interfaces subtree filter -->
<rpc message-id="101" xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
  <get-config>
    <source><running/></source>
    <filter type="subtree">
      <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces"/>
    </filter>
  </get-config>
</rpc>
```

The ncclient Python library abstracts these XML envelopes. `manager.connect()` opens an SSH session and negotiates capabilities; `conn.get_config()`, `conn.edit_config()`, and `conn.commit()` map directly to NETCONF operations.

---

### RESTCONF Data Model and HTTP Verbs

RESTCONF (RFC 8040) exposes YANG-modelled data as a REST API over HTTPS (port 443). Each resource maps to a URL path under `/restconf/data/<module>:<container>/<key>`. IOS-XE requires three prerequisites: `ip http secure-server`, `ip http authentication local`, and `restconf`.

HTTP verbs map to RESTCONF semantics:

| Verb | RESTCONF Meaning | Typical Response |
|------|-----------------|-----------------|
| GET | Read resource | 200 OK |
| PUT | Create or replace resource | 201 Created or 204 No Content |
| PATCH | Partial update — merge fields | 204 No Content |
| POST | Create child resource (auto-keyed) | 201 Created |
| DELETE | Remove resource | 204 No Content |

Response codes signal specific error categories:

| Code | Meaning | Common Trigger |
|------|---------|----------------|
| 400 | Bad Request | Malformed JSON or invalid YANG |
| 401 | Unauthorized | Wrong credentials or auth not configured |
| 404 | Not Found | Resource path does not exist |
| 409 | Conflict | Resource already exists on POST |

RESTCONF payloads are JSON-encoded. The top-level key must include the module name: `"ietf-interfaces:interface"`, not just `"interface"`. The `Content-Type` and `Accept` headers must both be set to `application/yang-data+json`.

---

### EEM Applets — Event Detectors and Actions

Embedded Event Manager (EEM) is a local automation framework built into IOS and IOS-XE. Applets are the simplest EEM policy form — they are entirely configuration-based and require no Tcl or Python files. An applet pairs exactly one **event detector** with one or more **actions**.

Key event detectors:

| Detector | Syntax | Use Case |
|----------|--------|----------|
| syslog | `event syslog pattern "<regex>"` | React to any log message |
| timer cron | `event timer cron cron-entry "<cron>"` | Scheduled tasks |
| track | `event track N state {up\|down}` | React to IP SLA/route state |
| cli | `event cli pattern "<cmd>"` | Intercept specific CLI commands |

Action numbering is significant — actions execute in ascending order. When an applet must issue CLI commands (e.g., `show` or `copy`), the session must have privilege-15 rights. `event manager session cli username admin` grants those rights globally and must be configured before applets that use `action N cli command`.

```
event manager session cli username admin
!
event manager applet OSPF-WATCH
 event syslog pattern "OSPF-5-ADJCHG"
 action 1.0 syslog msg "EEM: OSPF adjacency change detected"
 action 2.0 cli command "enable"
 action 3.0 cli command "show ip ospf neighbor"
```

> **Exam tip:** The syslog pattern uses a Tcl regular expression, not a simple substring. A pattern of `"OSPF-5-ADJCHG"` matches any log message containing that exact string. Anchoring with `^` or `$` is supported but rarely required in practice.

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| NETCONF provisioning | Enable NETCONF on IOS-XE, connect with ncclient, perform get-config / edit-config / commit |
| RESTCONF provisioning | Enable RESTCONF on IOS-XE, send GET / PUT / PATCH / DELETE with Python requests |
| EEM applet authoring | Write syslog-triggered and cron-triggered applets with CLI action sequences |
| YANG model navigation | Identify correct module URNs and JSON key prefixes for ietf-interfaces and Cisco-IOS-XE-native |
| Response code interpretation | Distinguish 200/201/204/400/401/404/409 and identify their causes from workbook exercises |
| Python data type identification | Trace requests and ncclient return values — dict, list, str, int, bool |
| JSON payload construction | Build valid ietf-interfaces and Cisco-IOS-XE-native YANG payloads |

---

## 2. Topology & Scenario

**Enterprise context:** Acme Corp is modernising its network operations team. The network operations centre (NOC) currently manages devices exclusively via CLI; leadership has mandated a shift to programmable interfaces. Your task is to retrofit three production routers — R1 and R2 (CSR1000v) and R3 (IOSv) — with programmatic management capabilities, validate all APIs end-to-end with Python scripts, and configure EEM automation on R3 to self-document OSPF events and nightly config backups.

IP addressing is pre-loaded. OSPF, APIs, SSH, and EEM are absent — you build the entire automation layer from scratch.

```
              ┌──────────────────────────────┐
              │             R1               │
              │   CSR1000v (IOS-XE)          │
              │   Lo0: 1.1.1.1/32            │
              │   NETCONF + RESTCONF target  │
              └──────────┬───────────────────┘
                         │ GigabitEthernet1
                         │ 10.1.12.1/30
                         │
                         │ 10.1.12.2/30
                         │ GigabitEthernet1
              ┌──────────┴───────────────────┐
              │             R2               │
              │   CSR1000v (IOS-XE)          │
              │   Lo0: 2.2.2.2/32            │
              │   NETCONF + RESTCONF target  │
              └──────────┬───────────────────┘
                         │ GigabitEthernet2
                         │ 10.1.23.1/30
                         │
                         │ 10.1.23.2/30
                         │ GigabitEthernet0/0
              ┌──────────┴───────────────────┐
              │             R3               │
              │   IOSv (IOS Classic)         │
              │   Lo0: 3.3.3.3/32            │
              │   EEM applet host            │
              └──────────────────────────────┘

PC1 ─── GigabitEthernet2 (192.168.10.1/24) ─── R1
PC2 ─── GigabitEthernet0/1 (192.168.20.1/24) ── R3
```

---

## 3. Hardware & Environment Specifications

**Cabling Table**

| Link | Device A | Interface A | IP A | IP B | Interface B | Device B | Subnet |
|------|----------|-------------|------|------|-------------|----------|--------|
| L1 | R1 | GigabitEthernet1 | 10.1.12.1/30 | 10.1.12.2/30 | GigabitEthernet1 | R2 | 10.1.12.0/30 |
| L2 | R2 | GigabitEthernet2 | 10.1.23.1/30 | 10.1.23.2/30 | GigabitEthernet0/0 | R3 | 10.1.23.0/30 |
| L3 | R1 | GigabitEthernet2 | 192.168.10.1/24 | 192.168.10.10/24 | eth0 | PC1 | 192.168.10.0/24 |
| L4 | R3 | GigabitEthernet0/1 | 192.168.20.1/24 | 192.168.20.10/24 | eth0 | PC2 | 192.168.20.0/24 |

**Console Access Table**

| Device | Role | Console Port | Connection Command |
|--------|------|--------------|--------------------|
| R1 | CSR1000v — NETCONF + RESTCONF | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R2 | CSR1000v — NETCONF + RESTCONF | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R3 | IOSv — EEM host | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| PC1 | VPCS endpoint | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| PC2 | VPCS endpoint | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |

**Software Requirements**

```bash
pip install ncclient requests
```

---

## 4. Base Configuration

The `initial-configs/` directory pre-loads IP addressing only. Everything below must be configured by the student.

**Pre-loaded on all routers:**
- Hostname, `no ip domain-lookup`, `ip domain-name encor-lab.local`
- `username admin privilege 15 secret Encor-API-2026`
- Loopback0 IP addresses
- All physical interface IP addresses and `no shutdown`
- Console and VTY lines with local authentication (transport input telnet)

**NOT pre-loaded (student must configure):**
- OSPF routing process and area assignments
- SSH (crypto key, `ip ssh version 2`, SSH transport on VTY)
- NETCONF subsystem (`netconf-yang`, candidate datastore feature)
- RESTCONF subsystem (`restconf`, secure HTTP server, HTTP authentication)
- EEM session CLI username
- EEM applets (both syslog-triggered and cron-triggered)

---

## 5. Lab Challenge: Full Protocol Mastery

> This is a capstone lab. No step-by-step guidance is provided.
> Configure the complete Automation solution from scratch — IP addressing is pre-configured; everything else is yours to build.
> All blueprint bullets for this chapter must be addressed.

### Objectives

- Configure OSPF process 1 on R1, R2, and R3 with router-IDs matching each router's Loopback0 address; advertise all loopbacks, transit links, and LAN subnets into area 0; suppress OSPF hellos on LAN-facing interfaces toward PC1 and PC2
- Generate RSA keys and enable SSHv2 on all three routers; set idle timeout to 60 seconds and limit authentication retries to 3; restrict VTY lines to SSH-only on all routers
- Enable the NETCONF subsystem and candidate datastore feature on R1 and R2 (port 830); confirm the NETCONF hello is returned when connecting with an SSH client using the `-s netconf` subsystem flag
- Enable HTTPS with local credential authentication and activate the RESTCONF subsystem on R1 and R2 (port 443); confirm the RESTCONF root resource returns JSON when queried
- Using `ncclient`, write a Python script targeting R1 (port 830) that: displays server capabilities, retrieves the running datastore scoped to the `ietf-interfaces` module, creates Loopback99 (99.99.99.99/32) via `edit-config` on the candidate datastore, commits the candidate, and demonstrates locking and unlocking the running datastore
- Using `requests`, write a Python script targeting R2 (port 443) that: confirms RESTCONF is active, lists all interfaces from the `ietf-interfaces` datastore, creates Loopback88 (88.88.88.88/32) via PUT, patches the Loopback88 description field, deletes Loopback88 and confirms 404 on a subsequent GET, and deliberately triggers response codes 200, 204, 400, 401, and 404 with an explanation of each
- Configure `event manager session cli username admin` on R3, then create applet `SYSLOG-MONITOR` triggered by any `OSPF-5-ADJCHG` syslog pattern that logs a custom EEM message and runs `show ip ospf neighbor`; create applet `BACKUP-CONFIG` on a cron schedule of `0 0 * * *` (midnight daily) that copies running-config to startup-config and logs a custom EEM message
- Construct a valid `ietf-interfaces` JSON payload (with correct module namespace prefix) that creates a loopback interface with an IPv4 address; construct a valid `Cisco-IOS-XE-native` JSON payload that adds an OSPF network statement using the `native → router → ospf → network` container hierarchy; identify the Python data types returned by `conn.server_capabilities` and the ncclient `RPCReply` object

**Success criteria:**

- `show ip ospf neighbor` on R2 shows two FULL adjacencies; all three loopbacks reachable via OSPF on every router
- `show ip ssh` on each router reports `SSH Enabled - version 2.0`; VTY lines refuse telnet
- `show netconf-yang sessions` and `show platform software yang-management process` confirm both subsystems active on R1 and R2
- NETCONF script exits without error; `show interfaces Loopback99` on R1 confirms the interface and address
- RESTCONF script exits without error; all expected status codes confirmed; `show interfaces Loopback88` on R2 shows no output after DELETE
- `show event manager policy registered` on R3 lists both applets; bouncing Gi0/0 produces the EEM syslog message in `show logging`
- Both JSON payloads submit without a 400 error; Python data type identifications are correct

---

## 6. Verification & Analysis

### OSPF Convergence

```
R2# show ip ospf neighbor

Neighbor ID     Pri   State           Dead Time   Address         Interface
1.1.1.1           1   FULL/DR         00:00:35    10.1.12.1       GigabitEthernet1  ! ← R1 adjacency
3.3.3.3           1   FULL/DR         00:00:36    10.1.23.2       GigabitEthernet2  ! ← R3 adjacency

R1# show ip route ospf
      2.0.0.0/32 is subnetted, 1 subnets
O        2.2.2.2 [110/2] via 10.1.12.2, 00:01:10, GigabitEthernet1   ! ← R2 loopback
      3.0.0.0/32 is subnetted, 1 subnets
O        3.3.3.3 [110/3] via 10.1.12.2, 00:01:10, GigabitEthernet1   ! ← R3 loopback via R2
      10.0.0.0/8 is variably subnetted, 4 subnets, 2 masks
O        10.1.23.0/30 [110/2] via 10.1.12.2, 00:01:10, GigabitEthernet1  ! ← R2-R3 transit
O        192.168.20.0/24 [110/3] via 10.1.12.2, 00:01:10, GigabitEthernet1  ! ← PC2 LAN
```

### NETCONF Session

```
R1# show netconf-yang sessions
R                                  -- (N)ETCONF, gRPC, gNMI
I                                  -- In
Number of sessions : 0             ! ← 0 active (no client connected currently)

! From host, confirm port 830 responds:
$ ssh -p 830 admin@10.1.12.1 -s netconf
<?xml version="1.0" encoding="UTF-8"?>
<hello xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
  <capabilities>
    <capability>urn:ietf:params:netconf:base:1.0</capability>
    <capability>urn:ietf:params:netconf:base:1.1</capability>      ! ← NETCONF 1.1 supported
    <capability>urn:ietf:params:netconf:capability:candidate:1.0</capability>  ! ← candidate datastore
```

### RESTCONF Service

```
R2# show platform software yang-management process
confd            : Running         ! ← YANG management daemon
nesd             : Running
syncfd           : Running
ncsshd           : Running
dmiauthd         : Running
nginx            : Running         ! ← HTTPS server for RESTCONF
ndbmand          : Running
pubd             : Running

! GET / returns RESTCONF root — confirms API path resolution
$ curl -sk -u admin:Encor-API-2026 https://10.1.12.2/restconf/ -H "Accept: application/yang-data+json"
{
  "ietf-restconf:restconf": {
    "data": {},
    "operations": {},
    "yang-library-version": "2016-06-21"   ! ← service active
  }
}
```

### EEM Applets

```
R3# show event manager policy registered
No.  Class     Type    Event Type          Trap  Time Registered         Name
1    applet    user    syslog              Off   Thu Apr 10 00:00:00     SYSLOG-MONITOR   ! ← applet 1
2    applet    user    timer cron          Off   Thu Apr 10 00:00:00     BACKUP-CONFIG    ! ← applet 2

! After bouncing Gi0/0 to trigger OSPF adjacency event:
R3# show logging | include EEM
Apr 10 00:01:12.345: %EEM-6-LOG: SYSLOG-MONITOR: EEM: OSPF adjacency change detected  ! ← EEM syslog fired
```

### Python Script Output (NETCONF)

```
[*] Connecting to 10.1.12.1:830 via NETCONF...
[+] NETCONF session established
[Task 1] NETCONF Server Capabilities
  urn:ietf:params:netconf:base:1.0
  urn:ietf:params:netconf:base:1.1
  urn:ietf:params:netconf:capability:candidate:1.0    ! ← candidate datastore present
  urn:ietf:params:yang:ietf-interfaces
  ...
[Task 3] edit-config — create Loopback99 on candidate datastore
[+] edit-config accepted by candidate datastore        ! ← no error = YANG payload valid
[Task 4] commit — push candidate to running
[+] Commit successful. Loopback99 is now in running config.
[+] All NETCONF tasks completed.

R1# show interfaces Loopback99
Loopback99 is up, line protocol is up
  Internet address is 99.99.99.99/32                   ! ← confirms edit-config + commit
```

---

## 7. Verification Cheatsheet

### OSPF Verification

```
router ospf 1
 router-id X.X.X.X
 passive-interface <LAN-interface>
 network <network> <wildcard> area 0
```

| Command | What to Look For |
|---------|-----------------|
| `show ip ospf neighbor` | FULL state for each expected peer |
| `show ip route ospf` | All remote loopbacks and subnets via OSPF (O) |
| `show ip ospf interface brief` | Interface included in OSPF, correct area |
| `show ip ospf` | Router ID, process ID, area count |

### SSH and Crypto

```
crypto key generate rsa modulus 2048
ip ssh version 2
ip ssh time-out 60
ip ssh authentication-retries 3
line vty 0 4
 transport input ssh
```

| Command | What to Look For |
|---------|-----------------|
| `show ip ssh` | `SSH Enabled - version 2.0` |
| `show users` | Active SSH sessions |

### NETCONF

```
netconf-yang
netconf-yang feature candidate-datastore
```

| Command | What to Look For |
|---------|-----------------|
| `show netconf-yang sessions` | Subsystem running; active session count |
| `show netconf-yang statistics` | Message counts per session |
| `debug netconf-yang all` | Full XML exchange (use sparingly) |

> **Exam tip:** `netconf-yang` alone activates the subsystem; `netconf-yang feature candidate-datastore` is a separate command required for staged commits. Missing the second command is a common cause of `edit-config target="candidate"` failures.

### RESTCONF

```
ip http secure-server
ip http authentication local
restconf
```

| Command | What to Look For |
|---------|-----------------|
| `show platform software yang-management process` | `nginx: Running` |
| `show running-config \| include restconf` | `restconf` line present |
| `show ip http server secure status` | HTTPS enabled |

> **Exam tip:** `ip http authentication local` is mandatory. Without it, all RESTCONF requests return 401 regardless of credentials, because the HTTP server has no authentication method configured.

### EEM Applets

```
event manager session cli username admin
!
event manager applet <NAME>
 event syslog pattern "<regex>"
 action N.N syslog msg "<text>"
 action N.N cli command "enable"
 action N.N cli command "<show-command>"
```

| Command | What to Look For |
|---------|-----------------|
| `show event manager policy registered` | Both applets listed with correct event type |
| `show event manager history events` | Trigger timestamps and action outcomes |
| `show logging \| include EEM` | Custom EEM syslog messages after trigger |

### Python NETCONF Reference (ncclient)

| Operation | ncclient Call | Notes |
|-----------|--------------|-------|
| Connect | `manager.connect(host, port=830, ...)` | `device_params={"name": "iosxe"}` |
| Get running | `conn.get_config(source="running")` | Add `filter=("subtree", xml)` to scope |
| Edit candidate | `conn.edit_config(target="candidate", config=xml)` | |
| Commit | `conn.commit()` | Moves candidate → running |
| Lock | `conn.lock("running")` | Use as context manager |
| Unlock | `conn.unlock("running")` | Auto-released by context manager |

### Python RESTCONF Reference (requests)

| Operation | requests Call | Expected Code |
|-----------|--------------|---------------|
| GET | `requests.get(url, auth=AUTH, headers=H, verify=False)` | 200 |
| PUT | `requests.put(url, auth=AUTH, headers=H, json=payload, verify=False)` | 201 or 204 |
| PATCH | `requests.patch(url, auth=AUTH, headers=H, json=payload, verify=False)` | 204 |
| DELETE | `requests.delete(url, auth=AUTH, headers=H, verify=False)` | 204 |
| POST | `requests.post(url, auth=AUTH, headers=H, json=payload, verify=False)` | 201 |

### Wildcard Mask Quick Reference

| Subnet Mask | Wildcard Mask | Common Use |
|-------------|---------------|------------|
| /32 | 0.0.0.0 | Host route (Loopback) |
| /30 | 0.0.0.3 | Point-to-point link |
| /29 | 0.0.0.7 | Small transit segment |
| /24 | 0.0.0.255 | LAN segment |

### Common Automation Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| NETCONF connection refused on port 830 | `netconf-yang` not configured |
| `edit-config` fails with capability error | `netconf-yang feature candidate-datastore` missing |
| RESTCONF 401 on all requests | `ip http authentication local` missing |
| RESTCONF 404 on valid path | `ip http secure-server` or `restconf` not configured |
| RESTCONF 400 on PUT | JSON key missing module prefix (e.g., `"interface"` instead of `"ietf-interfaces:interface"`) |
| EEM applet not triggering | Wrong syslog pattern regex; `event manager session cli username` missing for CLI actions |
| EEM syslog action fails | Applet lacks `action N cli command "enable"` before privileged commands |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### OSPF Underlay

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1
crypto key generate rsa modulus 2048
ip ssh version 2
ip ssh time-out 60
ip ssh authentication-retries 3
ip ssh source-interface Loopback0
!
router ospf 1
 router-id 1.1.1.1
 passive-interface GigabitEthernet2
 network 1.1.1.1 0.0.0.0 area 0
 network 10.1.12.0 0.0.0.3 area 0
 network 192.168.10.0 0.0.0.255 area 0
!
line vty 0 4
 transport input ssh
```
</details>

<details>
<summary>Click to view R2 Configuration</summary>

```bash
! R2
crypto key generate rsa modulus 2048
ip ssh version 2
ip ssh time-out 60
ip ssh authentication-retries 3
ip ssh source-interface Loopback0
!
router ospf 1
 router-id 2.2.2.2
 network 2.2.2.2 0.0.0.0 area 0
 network 10.1.12.0 0.0.0.3 area 0
 network 10.1.23.0 0.0.0.3 area 0
!
line vty 0 4
 transport input ssh
```
</details>

<details>
<summary>Click to view R3 Configuration</summary>

```bash
! R3
crypto key generate rsa modulus 2048
ip ssh version 2
ip ssh time-out 60
ip ssh authentication-retries 3
!
router ospf 1
 router-id 3.3.3.3
 passive-interface GigabitEthernet0/1
 network 3.3.3.3 0.0.0.0 area 0
 network 10.1.23.0 0.0.0.3 area 0
 network 192.168.20.0 0.0.0.255 area 0
!
line vty 0 4
 transport input ssh
```
</details>

---

### NETCONF and RESTCONF on R1 and R2

<details>
<summary>Click to view R1 and R2 API Configuration</summary>

```bash
! R1 and R2 — apply identical block to both
ip http secure-server
ip http authentication local
!
restconf
!
netconf-yang
netconf-yang feature candidate-datastore
```
</details>

---

### Python NETCONF Script

<details>
<summary>Click to view capstone_netconf.py</summary>

See `solutions/scripts/capstone_netconf.py` for the full implementation.

Key operations:
1. `manager.connect(host, port=830, device_params={"name": "iosxe"})` — open session
2. `conn.get_config(source="running", filter=("subtree", filter_xml))` — read interfaces
3. `conn.edit_config(target="candidate", config=LOOPBACK99_CONFIG)` — stage change
4. `conn.commit()` — activate
5. `with conn.locked("running"): ...` — lock/unlock as context manager
</details>

---

### Python RESTCONF Script

<details>
<summary>Click to view capstone_restconf.py</summary>

See `solutions/scripts/capstone_restconf.py` for the full implementation.

Key patterns:
- Headers: `{"Accept": "application/yang-data+json", "Content-Type": "application/yang-data+json"}`
- Payload top-level key: `"ietf-interfaces:interface"` (module prefix required)
- 400: send `data="not-json"` (wrong content type forces parse error)
- 401: use `auth=("baduser", "badpass")`
- 404: request a path that does not exist
</details>

---

### EEM Applets on R3

<details>
<summary>Click to view R3 EEM Configuration</summary>

```bash
! R3
event manager session cli username admin
!
event manager applet SYSLOG-MONITOR
 event syslog pattern "OSPF-5-ADJCHG"
 action 1.0 syslog msg "EEM: OSPF adjacency change detected"
 action 2.0 cli command "enable"
 action 3.0 cli command "show ip ospf neighbor"
!
event manager applet BACKUP-CONFIG
 event timer cron cron-entry "0 0 * * *"
 action 1.0 cli command "enable"
 action 2.0 cli command "copy running-config startup-config" pattern "filename"
 action 3.0 cli command ""
 action 4.0 syslog msg "EEM: Nightly config backup completed"
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show event manager policy registered
show event manager history events
show logging | include EEM
! Trigger SYSLOG-MONITOR:
interface GigabitEthernet0/0
 shutdown
 no shutdown
```
</details>

---

### JSON Payload Construction

<details>
<summary>Click to view ietf-interfaces Loopback Payload</summary>

```json
{
  "ietf-interfaces:interface": {
    "name": "Loopback99",
    "description": "NETCONF-created interface",
    "type": "iana-if-type:softwareLoopback",
    "enabled": true,
    "ietf-ip:ipv4": {
      "address": [
        {
          "ip": "99.99.99.99",
          "prefix-length": 32
        }
      ]
    }
  }
}
```

Python data types returned by ncclient:
- `conn.server_capabilities` → `list` of `str`
- XML response element values → `str` (all YANG leaf values are strings in XML)
- `conn.get_config()` returns an `ncclient.operations.rpc.RPCReply` object; `.xml` property → `str`
</details>

<details>
<summary>Click to view Cisco-IOS-XE-native OSPF Payload</summary>

```json
{
  "Cisco-IOS-XE-native:native": {
    "router": {
      "Cisco-IOS-XE-ospf:ospf": [
        {
          "id": 1,
          "network": [
            {
              "ip": "10.1.12.0",
              "mask": "0.0.0.3",
              "area": "0"
            }
          ]
        }
      ]
    }
  }
}
```
</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. Inject the fault first, then
diagnose and fix using only show commands and the symptoms provided.

### Workflow

```bash
python3 setup_lab.py --host <eve-ng-ip>                        # reset to known-good
python3 scripts/fault-injection/inject_scenario_01.py          # Ticket 1
python3 scripts/fault-injection/apply_solution.py              # restore
```

---

### Ticket 1 — Python Script to R1 Hangs and Never Completes

A junior engineer reports that `capstone_netconf.py` stalls indefinitely when targeting R1. No error is printed; the script simply never returns.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py`

**Success criteria:** `capstone_netconf.py --host 10.1.12.1` completes successfully and Loopback99 appears in `show interfaces`.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Check whether the NETCONF subsystem is active: `show netconf-yang sessions` — if the command is unrecognised, the subsystem is disabled.
2. Check whether SSH port 830 is responding: `ssh -p 830 admin@10.1.12.1 -s netconf` — a timeout means no listener on 830.
3. Check the running config: `show running-config | include netconf` — if no `netconf-yang` line exists, the service was removed.
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! R1
netconf-yang
netconf-yang feature candidate-datastore
```

Confirm: `show netconf-yang sessions` returns without error. Re-run the script.
</details>

---

### Ticket 2 — API Calls to R2 Fail Without Returning Any Data

Automated monitoring scripts that previously worked against R2 now return a non-2xx status instantly. The network team confirms R2 is reachable via ping and SSH.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py`

**Success criteria:** `capstone_restconf.py --host 10.1.12.2` completes all tasks with expected 200/204 responses.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Test RESTCONF manually: `curl -sk -u admin:Encor-API-2026 https://10.1.12.2/restconf/ -H "Accept: application/yang-data+json"` — note the status code.
2. If 401: check `show running-config | include http authentication` — missing `ip http authentication local` means no auth method is configured.
3. Check whether `restconf` is still present: `show running-config | include restconf`.
4. Check HTTPS server: `show ip http server secure status` — look for "HTTPS server status: Enabled".
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! R2
ip http authentication local
```

Confirm: curl returns 200 with RESTCONF root JSON. Re-run the Python script.
</details>

---

### Ticket 3 — EEM-Triggered Syslog Messages Absent from R3 Log

An OSPF adjacency event occurred on R3 (confirmed in `show logging`), but the expected EEM custom syslog message was not produced. The cron-based backup applet also produced no output when it last ran.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py`

**Success criteria:** Bouncing R3 Gi0/0 produces `%EEM-6-LOG: SYSLOG-MONITOR: EEM: OSPF adjacency change detected` in `show logging`.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Check applet registration: `show event manager policy registered` — if SYSLOG-MONITOR is absent or shows a different event type, the applet definition was changed.
2. Check the syslog pattern: `show running-config | section event manager applet SYSLOG-MONITOR` — the pattern must match the OSPF adjacency syslog string `OSPF-5-ADJCHG`.
3. Check event history for failures: `show event manager history events` — look for "policy-error" entries.
4. Confirm `event manager session cli username admin` is present: required for CLI actions inside applets.
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! R3
no event manager applet SYSLOG-MONITOR
event manager applet SYSLOG-MONITOR
 event syslog pattern "OSPF-5-ADJCHG"
 action 1.0 syslog msg "EEM: OSPF adjacency change detected"
 action 2.0 cli command "enable"
 action 3.0 cli command "show ip ospf neighbor"
```

Bounce Gi0/0 and confirm EEM syslog fires.
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] OSPF process 1 converged — all three routers show FULL adjacencies
- [ ] All loopbacks (1.1.1.1, 2.2.2.2, 3.3.3.3) reachable from every router via OSPF
- [ ] SSHv2 enabled on R1, R2, R3 — VTY accepts SSH only
- [ ] `netconf-yang` and candidate datastore enabled on R1 and R2
- [ ] RESTCONF enabled on R1 and R2 — `show platform software yang-management process` shows nginx running
- [ ] `capstone_netconf.py` completes successfully — Loopback99 visible on R1
- [ ] `capstone_restconf.py` completes successfully — all expected status codes confirmed
- [ ] EEM applet SYSLOG-MONITOR registered on R3 — fires on OSPF adjacency change
- [ ] EEM applet BACKUP-CONFIG registered on R3 — cron entry `0 0 * * *`
- [ ] ietf-interfaces JSON payload constructed and submitted without 400 error
- [ ] Cisco-IOS-XE-native OSPF JSON payload constructed correctly

### Troubleshooting

- [ ] Ticket 1 diagnosed and resolved — NETCONF script completes
- [ ] Ticket 2 diagnosed and resolved — RESTCONF returns 200 responses
- [ ] Ticket 3 diagnosed and resolved — EEM syslog fires on adjacency change
