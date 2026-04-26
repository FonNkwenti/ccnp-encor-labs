# Lab 03: RESTCONF and REST API Interpretation

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

**Exam Objective:** 4.6 — Configure and verify NETCONF and RESTCONF; 6.5 — Interpret REST API response codes and results in payload using Cisco Catalyst Center and RESTCONF

RESTCONF brings the simplicity of REST APIs to network device configuration. Where NETCONF uses SSH (port 830) and XML-encoded payloads, RESTCONF uses HTTPS (port 443) and JSON — meaning the same YANG data models are accessible with nothing more than `curl` or the Python `requests` library. This lab teaches you to drive IOS-XE configuration through HTTP verbs, build JSON payloads from YANG schemas, and interpret the response codes that distinguish a created resource from a replaced one.

---

### RESTCONF Architecture and Transport

RESTCONF (RFC 8040) is an HTTP-based protocol that provides a REST API over the same YANG data models used by NETCONF. The key architectural properties are:

- **Transport:** HTTPS (TLS) — default port 443; the self-signed cert on IOS-XE requires `verify=False` in Python or `-k` with curl
- **Base path:** `/restconf` — everything under this prefix is RESTCONF; `/restconf/data` is the datastore root
- **Authentication:** HTTP Basic Auth (username:password Base64-encoded in the `Authorization` header)
- **Content negotiation:** `Accept` and `Content-Type` headers must be set to `application/yang-data+json` for JSON encoding

```
Student Workstation
        │
        │  HTTPS port 443
        ▼
  R1 (CSR1000v)
  ┌─────────────────────────────────────┐
  │  ip http secure-server              │
  │  ip http authentication local       │
  │  restconf                           │
  │                                     │
  │  /restconf/data/ietf-interfaces:... │
  └─────────────────────────────────────┘
```

IOS-XE requires three commands to activate RESTCONF:
1. `ip http secure-server` — enables HTTPS
2. `ip http authentication local` — validates credentials against local user database
3. `restconf` — loads the RESTCONF subsystem

---

### RESTCONF URL Structure and YANG Paths

Every RESTCONF URL is a direct mapping of the YANG tree:

```
https://<device>/restconf/data/<module>:<container>/<list>=<key>/<leaf>
```

| URL Component | YANG Concept | Example |
|---------------|-------------|---------|
| `/restconf/data` | Datastore root (running config) | — |
| `ietf-interfaces:interfaces` | Module name + top-level container | `ietf-interfaces` module, `interfaces` container |
| `/interface=Loopback30` | List entry with key | `interface` list, key `name=Loopback30` |
| `/ietf-ip:ipv4` | Augmenting module container | `ietf-ip` augments ietf-interfaces |

The YANG module name in the URL (`ietf-interfaces:`) is the same namespace prefix used in NETCONF XML filters. RESTCONF makes the module explicit in every URL, which is why RESTCONF URLs are self-describing.

> **Exam tip:** The colon separator (`module:node`) in a RESTCONF URL identifies the YANG module. When you see `/Cisco-IOS-XE-native:native/router/ospf=1`, you know the YANG model is `Cisco-IOS-XE-native`.

---

### HTTP Methods Mapped to YANG Operations

RESTCONF maps the five HTTP verbs to distinct YANG operations:

| HTTP Verb | YANG Operation | IOS-XE Behavior | Success Code |
|-----------|---------------|-----------------|-------------|
| GET | retrieve | Read config/state | 200 OK |
| PUT | replace | Create or fully replace a resource | 201 Created / 204 No Content |
| PATCH | merge | Merge into existing resource | 204 No Content |
| POST | create | Create new (fails if exists) | 201 Created |
| DELETE | remove | Remove resource | 204 No Content |

**PUT vs PATCH — the critical difference:**
- **PUT** replaces the entire resource. If you PUT an interface with only a description, the IP address is removed.
- **PATCH** merges your payload into the existing resource. Omitted fields are left unchanged.

```python
# PUT — sends entire interface object (replaces all fields)
requests.put(url, data=json.dumps(full_interface_payload), ...)

# PATCH — sends only the fields to change (merges into existing)
requests.patch(url, data=json.dumps({"name": "Loopback30", "description": "new"}), ...)
```

> **Exam tip:** PATCH is the safe choice when you only want to update one field. PUT is used when you want to guarantee the complete resource state.

---

### HTTP Response Codes

The RESTCONF response code tells you exactly what happened:

| Code | Meaning | When It Occurs |
|------|---------|---------------|
| 200 OK | Data returned | GET request that found data |
| 201 Created | Resource created | POST or PUT created a new resource |
| 204 No Content | Success, no body | PUT/PATCH/DELETE that succeeded |
| 400 Bad Request | Malformed payload | Invalid JSON syntax or wrong YANG data type |
| 401 Unauthorized | Auth failed | Wrong username/password |
| 403 Forbidden | Auth OK, access denied | User lacks privilege for operation |
| 404 Not Found | Resource missing | URL path does not exist; interface not configured |
| 409 Conflict | Already exists | POST to create a resource that already exists |

> **Exam tip:** 204 No Content means success — the empty body is intentional. Don't interpret "no body" as an error.

---

### JSON Encoding in RESTCONF

RESTCONF payloads use JSON with YANG-qualified key names. The top-level key always includes the module prefix:

```json
{
  "ietf-interfaces:interface": {
    "name": "Loopback30",
    "type": "iana-if-type:softwareLoopback",
    "enabled": true,
    "ietf-ip:ipv4": {
      "address": [
        { "ip": "10.30.30.1", "prefix-length": 32 }
      ]
    }
  }
}
```

Key observations:
- **`"type"` uses YANG identity notation** — `iana-if-type:softwareLoopback` (not a plain string)
- **`"enabled"` is a JSON boolean** — `true`, not the string `"true"` (400 error if wrong type)
- **`"prefix-length"` is an integer** — `32`, not the string `"32"`
- **IPv6 is under `ietf-ip:ipv6`** — the same structure as `ietf-ip:ipv4`; both can coexist in one payload for dual-stack

---

### Catalyst Center and RESTCONF (Blueprint 6.5)

Cisco Catalyst Center (formerly DNA Center) exposes a REST API that follows similar principles to RESTCONF:
- **Authentication:** POST to `/api/system/v1/auth/token` → returns a JWT token used in `X-Auth-Token` headers
- **Device management:** `GET /api/v1/network-device` returns inventory; individual devices are managed by ID
- **Intent API:** Catalyst Center has a higher-level "Intent API" that abstracts device configuration into business intents (e.g., create VLAN, assign device to site) — you don't send raw YANG payloads

The exam may show a Catalyst Center REST API response and ask you to identify the meaning of a status code (200, 201, 400, 401, 404) or extract a value from a JSON payload. The same interpretation skills you develop in this lab apply directly.

```python
# Catalyst Center — get device list
headers = {"X-Auth-Token": token, "Content-Type": "application/json"}
r = requests.get("https://dnac/api/v1/network-device", headers=headers, verify=False)
devices = r.json()["response"]
for d in devices:
    print(d["hostname"], d["managementIpAddress"])
```

---

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| RESTCONF service enablement | Configure and verify `restconf`, `ip http secure-server`, `ip http authentication local` on IOS-XE |
| RESTCONF root exploration | Send GET to `/restconf` to discover available YANG capabilities |
| Interface retrieval | GET ietf-interfaces:interfaces and parse JSON response to extract names and addresses |
| Resource creation (PUT) | Build a dual-stack JSON payload and PUT a new loopback interface |
| Selective update (PATCH) | PATCH a single field without disturbing other interface properties |
| Resource deletion (DELETE) | DELETE a resource and verify 204 response |
| Response code interpretation | Identify and explain 200/201/204/400/401/404/409 in context |
| JSON payload construction | Build valid YANG-qualified JSON for RESTCONF operations |
| OSPF configuration via API | PATCH OSPF network statement using Cisco-IOS-XE-native YANG model |
| RESTCONF vs NETCONF comparison | Articulate transport, encoding, and use-case differences |

---

## 2. Topology & Scenario

**Enterprise Scenario:** Acme Corp's network operations team is piloting a model-driven automation initiative. After verifying NETCONF in Lab 02, management now wants the team to demonstrate that the same IOS-XE YANG models can be driven over HTTP — enabling integration with the existing REST-based tooling used by the application teams. Your job is to use RESTCONF to create and manage interfaces on R1, then use the API to add an OSPF network statement — all without touching the CLI.

```
              ┌─────────────────────────┐
              │           R1            │
              │    (Primary API target) │
              │   Lo0: 1.1.1.1/32       │
              └──────────┬──────────────┘
                         │ Gi1 10.1.12.1/30
                         │
                         │ Gi1 10.1.12.2/30
              ┌──────────┴──────────────┐
              │           R2            │
              │  (Secondary API target) │
              │   Lo0: 2.2.2.2/32       │
              └──────────┬──────────────┘
                         │ Gi2 10.1.23.1/30
                         │
                         │ Gi0/0 10.1.23.2/30
              ┌──────────┴──────────────┐
              │           R3            │
              │      (EEM host)         │
              │   Lo0: 3.3.3.3/32       │
              └──────┬──────────┬───────┘
           Gi0/1     │          │     Student Workstation
    192.168.20.1/24  │          │     (runs Python scripts
                     │          │      → HTTPS to R1/R2)
              ┌──────┘          └───────────────────────┐
           ┌──┴───┐                              ┌──────┴───┐
           │ PC2  │                              │   PC1    │
           │      │                              │          │
           └──────┘                  R1 Gi2 → 192.168.10.1/24
       192.168.20.10/24                      192.168.10.10/24
```

**OSPF Area 0** runs on all router-to-router links. R1 and R2 are CSR1000v (IOS-XE) and expose RESTCONF on port 443. R3 is IOSv and hosts EEM applets from Lab 00. All RESTCONF operations in this lab target **R1 (10.1.12.1)**.

---

## 3. Hardware & Environment Specifications

**Platform Requirements:**

| Device | Platform | Role | IOS-XE / IOS |
|--------|----------|------|--------------|
| R1 | Cisco CSR1000v | Primary RESTCONF target | IOS-XE 16.x+ |
| R2 | Cisco CSR1000v | Secondary RESTCONF target | IOS-XE 16.x+ |
| R3 | Cisco IOSv | EEM host | IOS 15.x |
| PC1 | VPCS | Traffic generator | — |
| PC2 | VPCS | Remote endpoint | — |

**Cabling Table:**

| Link | Source | Destination | Subnet |
|------|--------|-------------|--------|
| L1 | R1 Gi1 (10.1.12.1/30) | R2 Gi1 (10.1.12.2/30) | 10.1.12.0/30 |
| L2 | R2 Gi2 (10.1.23.1/30) | R3 Gi0/0 (10.1.23.2/30) | 10.1.23.0/30 |
| L3 | R1 Gi2 (192.168.10.1/24) | PC1 e0 (192.168.10.10/24) | 192.168.10.0/24 |
| L4 | R3 Gi0/1 (192.168.20.1/24) | PC2 e0 (192.168.20.10/24) | 192.168.20.0/24 |

**Console Access Table:**

| Device | Port | Connection Command |
|--------|------|--------------------|
| R1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R3 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| PC1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| PC2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |

**Python Requirements (workstation):**
```bash
pip install requests
```

---

## 4. Base Configuration

The following is **pre-loaded** on all devices via `setup_lab.py`:

**Pre-configured on R1 and R2:**
- Hostname, SSH v2, local user `admin` (privilege 15, secret `Encor-API-2026`)
- Interface IP addressing (Loopback0, Gi1, Gi2)
- OSPF process 1 with all router interfaces in area 0
- HTTPS service (`ip http secure-server`)
- HTTP local authentication
- RESTCONF subsystem
- NETCONF YANG (from Lab 02)

**Pre-configured on R3:**
- Hostname, SSH v2, local user `admin`
- Interface IP addressing
- OSPF process 1
- EEM applets: `TRACK-INTERFACE`, `BACKUP-CONFIG`, `MATCH-SYSLOG`

**NOT pre-configured (student configures or verifies via API):**
- Loopback30 interface (created via RESTCONF PUT in Task 3)
- Loopback30 description update (PATCH in Task 4)
- Loopback30 deletion (DELETE in Task 5)
- OSPF network statement for Loopback30 (PATCH in Task 7)

---

## 5. Lab Challenge: Core Implementation

### Task 1: Verify RESTCONF Service and Explore Capabilities

- Confirm the RESTCONF subsystem is active on R1 by checking the platform software YANG management service.
- From your workstation, send an HTTPS GET request to the RESTCONF root path (`/restconf`) on R1 using Python `requests` or `curl`. Disable TLS certificate verification since R1 uses a self-signed certificate.
- Identify the `ietf-restconf:restconf` key in the response and locate the `yang-library-version` field.
- Confirm that the `Accept` header must be set to `application/yang-data+json` for JSON responses.

**Verification:** `show platform software yang-management process` must show `restconf` in state `Running`. The RESTCONF root GET must return HTTP 200 with a JSON body containing `ietf-restconf:restconf`.

---

### Task 2: GET Interface List

- From your workstation, send a GET request to the ietf-interfaces datastore path to retrieve all configured interfaces on R1.
- Parse the JSON response and print a table showing each interface's name, admin status (`enabled`), and IPv4 address (if configured).
- Identify the YANG module prefix in the response key (`ietf-interfaces:interfaces`) and explain why it is present.

**Verification:** The GET must return HTTP 200. The parsed output must list at minimum `Loopback0`, `GigabitEthernet1`, and `GigabitEthernet2`. Run `python3 solutions/scripts/restconf_get.py` to compare your output.

---

### Task 3: Create Loopback30 with a Dual-Stack Payload (PUT)

- Construct a JSON payload using the `ietf-interfaces` YANG model to create `Loopback30` with:
  - IPv4 address `10.30.30.1/32`
  - IPv6 address `2001:db8:30::1/128`
  - Description: `RESTCONF Demo Interface`
- Send a PUT to the ietf-interfaces path for `interface=Loopback30`.
- Record the HTTP response code and explain the difference between receiving 201 vs 204.

**Verification:** HTTP 201 (first run) or 204 (subsequent run). On R1 CLI: `show interfaces Loopback30` must show the correct IPv4 address. `show ipv6 interface Loopback30` must show `2001:db8:30::1`.

---

### Task 4: Update the Interface Description (PATCH)

- Construct a minimal JSON payload containing only the interface name and a new description: `Updated via RESTCONF PATCH`.
- Send a PATCH to the Loopback30 resource path.
- Verify that the IPv4/IPv6 addresses are still intact (not removed by the PATCH).

**Verification:** HTTP 204. On R1 CLI: `show run interface Loopback30` must show the new description AND the original IP addresses intact.

---

### Task 5: Delete the Interface (DELETE)

- Send a DELETE request targeting the Loopback30 resource path.
- Confirm the response code is 204.
- Attempt to GET Loopback30 after deletion and confirm the 404 response.

**Verification:** DELETE returns 204. Subsequent GET to the same URL returns 404. On R1 CLI: `show interfaces Loopback30` returns an error or the interface is absent from `show ip interface brief`.

---

### Task 6: Interpret Response Codes

Using the `restconf_error_codes.py` script (or your own requests), deliberately trigger each of the following and record the exact status code:
- A successful read of an existing resource
- Creation of a new resource (Loopback31)
- Deletion of Loopback31
- A request with a malformed payload (wrong data type for `enabled`)
- Authentication failure (wrong password)
- A GET for a non-existent interface (Loopback999)

For each scenario, write one sentence explaining why that specific code was returned.

**Verification:** On first run you must observe 200, 201, 204, 400, 401, and 404. Run `python3 solutions/scripts/restconf_error_codes.py` to confirm. On a repeat run, 409 replaces 201 (Loopback31 already exists) and 404 replaces 204 for the DELETE (already gone).

---

### Task 7: Add an OSPF Network Statement via RESTCONF

- Re-create Loopback30 with IPv4 address `10.30.30.1/32` (use the PUT from Task 3).
- Using the `Cisco-IOS-XE-native` YANG model, send a PATCH to OSPF process 1 on R1 to add a network statement advertising `10.30.30.1/0.0.0.0` into area 0.
- Verify the change is reflected in both the RESTCONF GET response and the IOS CLI.

**Verification:** HTTP 204. `show run | section ospf` on R1 must include `network 10.30.30.1 0.0.0.0 area 0`. `show ip ospf database` must show an updated LSA for the new prefix.

---

## 6. Verification & Analysis

### Task 1 Verification — RESTCONF Service

```
R1# show platform software yang-management process
Confd Status       : Running
...
Restconf Status    : Running       ! ← must be Running, not Stopped
Netconf Status     : Running
```

```bash
# GET /restconf from workstation
curl -sku admin:Encor-API-2026 \
  -H "Accept: application/yang-data+json" \
  https://10.1.12.1/restconf | python3 -m json.tool
```

Expected response (trimmed):
```json
{
  "ietf-restconf:restconf": {
    "data": {},
    "operations": {},
    "yang-library-version": "2016-06-21"   ! ← confirms YANG library loaded
  }
}
```

---

### Task 2 Verification — GET Interface List

```bash
python3 solutions/scripts/restconf_get.py
```

Expected output:
```
Status: 200                                      ! ← 200 = data returned
Name                      Type                           Enabled    IPv4 Address
--------------------------------------------------------------------------------
Loopback0                 softwareLoopback               True       1.1.1.1/32    ! ← Lo0 present
GigabitEthernet1          ethernetCsmacd                 True       10.1.12.1/30  ! ← Gi1 correct IP
GigabitEthernet2          ethernetCsmacd                 True       192.168.10.1/24
```

---

### Task 3 Verification — PUT Loopback30

```bash
python3 solutions/scripts/restconf_put.py
```

```
Status: 201                                      ! ← 201 = newly created
[+] 201 Created — Loopback30 successfully created.
```

CLI confirmation:
```
R1# show interfaces Loopback30
Loopback30 is up, line protocol is up
  Description: RESTCONF Demo Interface               ! ← description set
  Internet address is 10.30.30.1/32                 ! ← IPv4 correct

R1# show ipv6 interface Loopback30
Loopback30 is up, line protocol is up
  IPv6 is enabled, link-local address is ...
  Global unicast address(es):
    2001:DB8:30::1, subnet is 2001:DB8:30::1/128    ! ← IPv6 correct
```

---

### Task 4 Verification — PATCH Description

```bash
python3 solutions/scripts/restconf_patch.py
```

```
Status: 204                                      ! ← 204 = merge succeeded
[+] 204 No Content — description updated successfully.
[*] Current description: 'Updated via RESTCONF PATCH'
```

CLI confirmation (IPs must be preserved):
```
R1# show run interface Loopback30
interface Loopback30
 description Updated via RESTCONF PATCH           ! ← new description
 ip address 10.30.30.1 255.255.255.255            ! ← IPv4 still intact
 ipv6 address 2001:DB8:30::1/128                  ! ← IPv6 still intact
```

---

### Task 5 Verification — DELETE

```bash
python3 solutions/scripts/restconf_delete.py
```

```
Status: 204                                      ! ← 204 = deleted
[+] 204 No Content — Loopback30 deleted successfully.
```

Subsequent GET must return 404:
```bash
curl -sku admin:Encor-API-2026 \
  -H "Accept: application/yang-data+json" \
  https://10.1.12.1/restconf/data/ietf-interfaces:interfaces/interface=Loopback30
# HTTP/1.1 404 Not Found                        ! ← resource is gone
```

---

### Task 6 Verification — Response Codes

```bash
python3 solutions/scripts/restconf_error_codes.py
```

```
--- 200 OK: GET existing interface ---
Status: 200  (200 = data returned)              ! ← 200 = resource found

--- 201 Created: POST to create Loopback31 ---
Status: 201  (201 = created; 409 = already exists)  ! ← 201 on first run

--- 204 No Content: DELETE Loopback31 ---
Status: 204  (204 = deleted; 404 = not found)   ! ← 204 = success, no body

--- 400 Bad Request: send malformed payload ---
Status: 400  (400 = server rejected the payload) ! ← wrong type for 'enabled'

--- 401 Unauthorized: wrong password ---
Status: 401  (401 = authentication failed)       ! ← bad credentials

--- 404 Not Found: GET non-existent interface ---
Status: 404  (404 = resource does not exist)     ! ← Loopback999 not configured
```

---

### Task 7 Verification — OSPF Network Statement

```bash
python3 solutions/scripts/restconf_ospf.py
```

```
Status: 204                                      ! ← 204 = network statement merged
[+] 204 No Content — OSPF network statement added.
```

CLI confirmation:
```
R1# show run | section ospf
router ospf 1
 router-id 1.1.1.1
 passive-interface GigabitEthernet2
 network 1.1.1.1 0.0.0.0 area 0
 network 10.1.12.0 0.0.0.3 area 0
 network 10.30.30.1 0.0.0.0 area 0     ! ← new entry added via RESTCONF
 network 192.168.10.0 0.0.0.255 area 0
```

---

## 7. Verification Cheatsheet

### RESTCONF Service Verification

```
show platform software yang-management process
show ip http server status
```

| Command | Purpose |
|---------|---------|
| `show platform software yang-management process` | Verify RESTCONF/NETCONF are Running |
| `show ip http server status` | Confirm HTTPS server is active |
| `show run \| include http\|restconf` | Review RESTCONF enablement config |

> **Exam tip:** `show platform software yang-management process` is the primary verification command for NETCONF/RESTCONF status on CSR1000v. "Running" means the process is listening; "Stopped" means the command is missing or failed.

---

### RESTCONF GET Requests

```
GET https://<router>/restconf
GET https://<router>/restconf/data/ietf-interfaces:interfaces
GET https://<router>/restconf/data/ietf-interfaces:interfaces/interface=<name>
GET https://<router>/restconf/data/Cisco-IOS-XE-native:native/router/ospf=1
```

| Command | What to Look For |
|---------|-----------------|
| GET `/restconf` | `yang-library-version` field confirms YANG is loaded |
| GET `ietf-interfaces:interfaces` | Interface list with names, types, addresses |
| GET `interface=Loopback30` | Specific interface config; 404 = not configured |
| GET `ospf=1` | OSPF process config in JSON |

---

### RESTCONF Write Operations

```
PUT    /restconf/data/ietf-interfaces:interfaces/interface=<name>
PATCH  /restconf/data/ietf-interfaces:interfaces/interface=<name>
DELETE /restconf/data/ietf-interfaces:interfaces/interface=<name>
POST   /restconf/data/ietf-interfaces:interfaces
PATCH  /restconf/data/Cisco-IOS-XE-native:native/router/ospf=1
```

| Command | Purpose |
|---------|---------|
| PUT `interface=<name>` | Create or fully replace interface |
| PATCH `interface=<name>` | Merge partial update (preserves unlisted fields) |
| DELETE `interface=<name>` | Remove interface entirely |
| POST `ietf-interfaces:interfaces` | Create new interface (409 if already exists) |
| PATCH `ospf=1` | Merge OSPF config (add network statements, change settings) |

> **Exam tip:** PUT and PATCH both return 204 on success for an existing resource. The difference is behavioral — PUT replaces, PATCH merges. Use PATCH when you want to change one field without resetting others.

---

### Required HTTP Headers

```python
headers = {
    "Accept": "application/yang-data+json",
    "Content-Type": "application/yang-data+json",
}
auth = ("admin", "Encor-API-2026")
```

| Header | Value | Required For |
|--------|-------|-------------|
| `Accept` | `application/yang-data+json` | All requests |
| `Content-Type` | `application/yang-data+json` | PUT, PATCH, POST |
| Authorization | Basic base64(user:pass) | All requests (set via `auth=` in requests) |

---

### Response Code Quick Reference

| Code | Meaning | Common Cause |
|------|---------|-------------|
| 200 OK | Data returned | Successful GET |
| 201 Created | Resource created | First PUT or POST for new resource |
| 204 No Content | Success, no body | PUT/PATCH/DELETE on existing resource |
| 400 Bad Request | Invalid payload | Wrong JSON type (`"true"` vs `true`), bad YANG path |
| 401 Unauthorized | Auth failed | Wrong password or missing Authorization header |
| 403 Forbidden | Auth OK, no permission | User privilege too low |
| 404 Not Found | Resource missing | Interface not configured, wrong URL |
| 409 Conflict | Already exists | POST to create a resource that already exists |

---

### Dual-Stack Interface JSON Template

```json
{
  "ietf-interfaces:interface": {
    "name": "<interface-name>",
    "description": "<optional>",
    "type": "iana-if-type:softwareLoopback",
    "enabled": true,
    "ietf-ip:ipv4": {
      "address": [{"ip": "<ipv4>", "prefix-length": <prefix>}]
    },
    "ietf-ip:ipv6": {
      "address": [{"ip": "<ipv6>", "prefix-length": <prefix>}]
    }
  }
}
```

| Field | Type | Notes |
|-------|------|-------|
| `"name"` | string | Must match the URL key (`interface=<name>`) |
| `"type"` | YANG identity | Always includes module prefix (`iana-if-type:`) |
| `"enabled"` | boolean | JSON `true`/`false` — not strings |
| `"prefix-length"` | integer | No quotes — `32` not `"32"` |

---

### RESTCONF vs NETCONF Quick Reference

| Property | RESTCONF | NETCONF |
|----------|----------|---------|
| Transport | HTTPS (port 443) | SSH (port 830) |
| Encoding | JSON (or XML) | XML only |
| Operations | HTTP verbs (GET/PUT/PATCH/POST/DELETE) | RPC messages (get, get-config, edit-config, commit) |
| Data model | Same YANG models | Same YANG models |
| Tools | curl, requests, Postman | ncclient, raw SSH |
| Candidate DS | Not supported | Supported (feature candidate-datastore) |
| Best for | REST-fluent teams, quick reads | Transactional changes, complex filters |

---

### Common RESTCONF Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| `ConnectionError` / `Connection refused` | `restconf` command missing, or `ip http secure-server` missing |
| `401 Unauthorized` | Wrong password; `ip http authentication local` missing; user not in local DB |
| `404 Not Found` | Wrong URL path; interface not configured; YANG module name typo |
| `400 Bad Request` | JSON type error (`"true"` instead of `true`); missing required field; namespace typo |
| `SSLError: certificate verify failed` | Missing `verify=False` in requests call or `-k` in curl |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Task 1: Verify RESTCONF Service

<details>
<summary>Click to view CLI Verification</summary>

```bash
! On R1 — verify all management processes are Running
R1# show platform software yang-management process
Confd Status       : Running
...
Restconf Status    : Running
Netconf Status     : Running

! Confirm HTTPS is active
R1# show ip http server status | include HTTP server status
HTTP secure server status: Enabled
```
</details>

<details>
<summary>Click to view RESTCONF Root GET</summary>

```bash
curl -sku admin:Encor-API-2026 \
  -H "Accept: application/yang-data+json" \
  https://10.1.12.1/restconf | python3 -m json.tool
```

Expected (trimmed):
```json
{
  "ietf-restconf:restconf": {
    "data": {},
    "operations": {},
    "yang-library-version": "2016-06-21"
  }
}
```
</details>

---

### Task 2: GET Interface List

<details>
<summary>Click to view Python Script</summary>

```bash
python3 solutions/scripts/restconf_get.py
```

```python
import json, requests, urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

url = "https://10.1.12.1/restconf/data/ietf-interfaces:interfaces"
headers = {"Accept": "application/yang-data+json"}
r = requests.get(url, auth=("admin", "Encor-API-2026"), headers=headers, verify=False)
print(r.status_code)
data = r.json()
for iface in data["ietf-interfaces:interfaces"]["interface"]:
    print(iface["name"], iface.get("enabled"))
```
</details>

---

### Task 3: Create Loopback30 (PUT)

<details>
<summary>Click to view PUT Script and Payload</summary>

Payload (`solutions/json/loopback30_payload.json`):
```json
{
  "ietf-interfaces:interface": {
    "name": "Loopback30",
    "description": "RESTCONF Demo Interface",
    "type": "iana-if-type:softwareLoopback",
    "enabled": true,
    "ietf-ip:ipv4": {
      "address": [{"ip": "10.30.30.1", "prefix-length": 32}]
    },
    "ietf-ip:ipv6": {
      "address": [{"ip": "2001:db8:30::1", "prefix-length": 128}]
    }
  }
}
```

```bash
python3 solutions/scripts/restconf_put.py
# Expected: Status 201 (first run) or 204 (repeat run)
```
</details>

---

### Task 4: PATCH Description

<details>
<summary>Click to view PATCH Script</summary>

```bash
python3 solutions/scripts/restconf_patch.py
# Expected: Status 204
# R1# show run interface Loopback30 → description = "Updated via RESTCONF PATCH"
```
</details>

---

### Task 5: DELETE Loopback30

<details>
<summary>Click to view DELETE Script</summary>

```bash
python3 solutions/scripts/restconf_delete.py
# Expected: Status 204

# Verify deletion:
curl -sku admin:Encor-API-2026 \
  -H "Accept: application/yang-data+json" \
  https://10.1.12.1/restconf/data/ietf-interfaces:interfaces/interface=Loopback30
# Expected: HTTP 404
```
</details>

---

### Task 6: Response Code Scenarios

<details>
<summary>Click to view Error Code Demo Script</summary>

```bash
python3 solutions/scripts/restconf_error_codes.py
```

Each function in the script deliberately triggers one response code. Review the output comments to confirm you observed 200, 201, 204, 400, 401, and 404.
</details>

---

### Task 7: OSPF Network Statement via RESTCONF

<details>
<summary>Click to view OSPF PATCH Script</summary>

```bash
# First re-create Loopback30
python3 solutions/scripts/restconf_put.py

# Then add OSPF network statement
python3 solutions/scripts/restconf_ospf.py
# Expected: Status 204

# CLI verify:
# R1# show run | section ospf
# Look for: network 10.30.30.1 0.0.0.0 area 0
```

Payload (`solutions/json/ospf_network_payload.json`):
```json
{
  "Cisco-IOS-XE-ospf:ospf": [
    {
      "id": 1,
      "network": [
        {"ip": "10.30.30.1", "mask": "0.0.0.0", "area": 0}
      ]
    }
  ]
}
```
</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. Inject the fault first, then diagnose and fix using only show commands and RESTCONF/curl responses.

### Workflow

```bash
python3 setup_lab.py --host <eve-ng-ip>              # reset to known-good state
python3 scripts/fault-injection/inject_scenario_01.py  # Ticket 1
python3 scripts/fault-injection/apply_solution.py      # restore all devices
```

---

### Ticket 1 — Cannot Connect to R1 RESTCONF API

The network operations team reports that the automation pipeline's health check script is receiving a connection error when polling R1's RESTCONF endpoint. SSH to R1 works fine. The OSPF topology is fully converged.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py`

**Success criteria:** RESTCONF GET to `https://10.1.12.1/restconf` returns HTTP 200 with the RESTCONF root document.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
# 1. Confirm the symptom — connection refused or SSL error
curl -sku admin:Encor-API-2026 \
  -H "Accept: application/yang-data+json" \
  https://10.1.12.1/restconf
# Expected during fault: curl: (7) Failed to connect

# 2. Check YANG management service status on R1
R1# show platform software yang-management process
# Restconf Status: Stopped     ← key indicator

# 3. Check what is missing from running config
R1# show run | include restconf|http
# ip http secure-server
# ip http authentication local
# (restconf command is missing)
```
</details>

<details>
<summary>Click to view Fix</summary>

```
R1# configure terminal
R1(config)# restconf
R1(config)# end
R1# show platform software yang-management process
! Restconf Status: Running     ← restored
```

Re-test:
```bash
curl -sku admin:Encor-API-2026 -H "Accept: application/yang-data+json" \
  https://10.1.12.1/restconf
# HTTP 200 — RESTCONF root document returned
```
</details>

---

### Ticket 2 — RESTCONF Returning 401 on All Requests

A developer reports that their RESTCONF script was working yesterday but now returns HTTP 401 on every request, including a simple GET. They have not changed the script. The credentials used are `admin / Encor-API-2026`.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py`

**Success criteria:** RESTCONF GET returns 200. The `admin` user authenticates successfully with password `Encor-API-2026`.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
# 1. Confirm 401 on workstation
curl -sku admin:Encor-API-2026 \
  -H "Accept: application/yang-data+json" \
  https://10.1.12.1/restconf/data/ietf-interfaces:interfaces
# HTTP/1.1 401 Unauthorized     ← confirms symptom

# 2. Try to SSH with the same credentials
ssh admin@10.1.12.1
# Permission denied (publickey,keyboard-interactive)  ← SSH also fails

# 3. Console in and check local user database
R1# show run | include username
# username admin privilege 15 secret <MODIFIED>   ← password was changed

# 4. Check if authentication method changed
R1# show run | include http authentication
# ip http authentication local  ← method correct; password is wrong
```
</details>

<details>
<summary>Click to view Fix</summary>

```
R1# configure terminal
R1(config)# no username admin
R1(config)# username admin privilege 15 secret Encor-API-2026
R1(config)# end
```

Re-test:
```bash
curl -sku admin:Encor-API-2026 -H "Accept: application/yang-data+json" \
  https://10.1.12.1/restconf/data/ietf-interfaces:interfaces
# HTTP 200
```
</details>

---

### Ticket 3 — RESTCONF Connections Fail with SSL Error

The NOC reports that `curl` to R1's RESTCONF API is returning `SSL connection error` even with the `-k` flag on some workstations. Python scripts throw `requests.exceptions.ConnectionError: ('Connection aborted.', RemoteDisconnected(...))`. SSH and NETCONF (port 830) work normally.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py`

**Success criteria:** RESTCONF HTTPS GET returns HTTP 200. No SSL errors.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
# 1. Confirm the symptom
curl -sku admin:Encor-API-2026 \
  -H "Accept: application/yang-data+json" \
  https://10.1.12.1/restconf
# curl: (35) OpenSSL SSL_connect: Connection reset by peer

# 2. Try plain HTTP to see if the server is up at all
curl -su admin:Encor-API-2026 http://10.1.12.1/restconf
# Either connection refused or redirect — confirms HTTPS is broken

# 3. Check HTTPS server status on R1
R1# show ip http server status | include secure
# HTTP secure server: Disabled     ← root cause found

# 4. Review config
R1# show run | include http
# ip http authentication local
# restconf
# (ip http secure-server is missing)
```
</details>

<details>
<summary>Click to view Fix</summary>

```
R1# configure terminal
R1(config)# ip http secure-server
R1(config)# end
R1# show ip http server status | include secure
! HTTP secure server: Enabled     ← restored
```

Re-test:
```bash
curl -sku admin:Encor-API-2026 -H "Accept: application/yang-data+json" \
  https://10.1.12.1/restconf
# HTTP 200
```
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] Task 1: RESTCONF service verified — `show platform software yang-management process` shows `Running`; GET `/restconf` returns 200
- [ ] Task 2: GET ietf-interfaces returns 200 with interface table; parsed output shows Loopback0, Gi1, Gi2
- [ ] Task 3: PUT Loopback30 with dual-stack payload; received 201 (or 204 on repeat); CLI confirms IPv4 `10.30.30.1/32` and IPv6 `2001:db8:30::1/128`
- [ ] Task 4: PATCH description returns 204; `show run interface Loopback30` shows new description AND original IPs intact
- [ ] Task 5: DELETE returns 204; subsequent GET returns 404; interface absent from CLI
- [ ] Task 6: All six response codes observed (200, 201, 204, 400, 401, 404); each explained in one sentence
- [ ] Task 7: OSPF PATCH returns 204; `show run | section ospf` includes `network 10.30.30.1 0.0.0.0 area 0`

### Troubleshooting

- [ ] Ticket 1: Diagnosed missing `restconf` command from `show platform software yang-management process`; RESTCONF restored to Running
- [ ] Ticket 2: Diagnosed incorrect password for `admin` user; RESTCONF GET returns 200 with correct credentials
- [ ] Ticket 3: Diagnosed missing `ip http secure-server`; HTTPS restored and RESTCONF accessible
