# Automation Lab 01 — Python Scripting and JSON Construction

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

**Exam Objective:** Blueprint 6.1 — Interpret basic Python components and scripts; Blueprint 6.2 — Construct valid JSON-encoded files — Automation and Programmability

This lab bridges on-box EEM automation (lab-00) and model-driven programmability via NETCONF and RESTCONF (labs 02–03). Before sending configuration payloads to a router's REST API, you must be able to read a Python script and understand what it will do, and construct syntactically correct JSON that the router will accept. The ENCOR exam tests both skills directly — you will be given Python code to interpret and JSON files to write or fix.

---

### Python Data Types for Network Automation

Python has six data types that appear constantly in networking scripts. Understanding each type is required before reading any API automation code.

| Type | Python Literal | JSON Equivalent | Example in Networking |
|------|---------------|-----------------|----------------------|
| `str` | `"GigabitEthernet1"` | `"GigabitEthernet1"` | Interface name, hostname |
| `int` | `30` | `30` | Prefix length, AS number |
| `bool` | `True` / `False` | `true` / `false` | Interface enabled state |
| `NoneType` | `None` | `null` | Missing value, unset field |
| `list` | `["Gi1", "Gi2"]` | `["Gi1", "Gi2"]` | Interface array, neighbor list |
| `dict` | `{"name": "Gi1"}` | `{"name": "Gi1"}` | Interface object, config block |
| `tuple` | `("admin", "pass")` | — | Auth credentials (Python-only) |

Python is dynamically typed — you do not declare types. You identify a type by looking at how a value is written:

```python
hostname   = "R1"               # str   — quotes
prefix_len = 30                 # int   — plain number
enabled    = True               # bool  — capital T or F, no quotes
missing    = None               # NoneType — capital N
interfaces = ["Gi1", "Gi2"]    # list  — square brackets
iface_data = {"name": "Gi1"}   # dict  — curly braces
auth       = ("admin", "pass") # tuple — round brackets
```

A dict stores key-value pairs accessed by key name:

```python
iface = {"name": "GigabitEthernet1", "enabled": True, "prefix-length": 30}
print(iface["name"])           # GigabitEthernet1
print(iface["enabled"])        # True
```

A list stores ordered items accessed by index (starting at 0):

```python
names = ["GigabitEthernet1", "Loopback0", "GigabitEthernet2"]
print(names[0])   # GigabitEthernet1
print(len(names)) # 3
```

---

### The requests Library — HTTP Methods and Response Handling

The `requests` library is the standard Python tool for making HTTP calls. RESTCONF uses standard HTTP (GET, PUT, PATCH, POST, DELETE) over HTTPS, so `requests` is the primary way Python scripts talk to a router's REST API.

```
import requests
```

**The four HTTP methods used with RESTCONF:**

| Method | requests call | Purpose |
|--------|--------------|---------|
| GET | `requests.get(url, ...)` | Retrieve config or operational data |
| PUT | `requests.put(url, json=payload, ...)` | Replace a resource |
| PATCH | `requests.patch(url, json=payload, ...)` | Merge into existing resource |
| POST | `requests.post(url, json=payload, ...)` | Create a new resource |
| DELETE | `requests.delete(url, ...)` | Remove a resource |

Every call returns a `Response` object:

```python
resp = requests.get(url, headers=headers, auth=auth, verify=False)

resp.status_code     # int — HTTP status (200, 401, 404, …)
resp.json()          # dict — parsed JSON body
resp.text            # str  — raw response body as text
resp.headers         # dict — HTTP response headers
```

`verify=False` disables TLS certificate validation — required in labs because EVE-NG nodes use self-signed certificates. Never use `verify=False` in production.

`auth=("admin", "Encor-API-2026")` passes HTTP Basic Authentication credentials as a tuple.

**Required headers for RESTCONF:**

```python
HEADERS = {
    "Accept":       "application/yang-data+json",
    "Content-Type": "application/yang-data+json",
}
```

Both headers are required. Without `Accept`, the router may return XML instead of JSON. Without `Content-Type` on PUT/POST/PATCH, the router will reject the request body.

**Error handling pattern:**

```python
try:
    resp = requests.get(url, headers=HEADERS, auth=AUTH, verify=False)
    resp.raise_for_status()          # raises HTTPError for 4xx/5xx
    data = resp.json()
except requests.exceptions.HTTPError as e:
    print(f"HTTP error: {e}")        # 401, 403, 404, etc.
except requests.exceptions.ConnectionError:
    print("Cannot connect to router") # HTTPS port not open
except json.JSONDecodeError:
    print("Invalid JSON in response") # response is not JSON
```

`raise_for_status()` converts a bad status code into a Python exception — without it, a 401 response returns silently and your script continues with a body that is not the data you expected.

---

### JSON Syntax — Objects, Arrays, and YANG Integration

JSON (JavaScript Object Notation) is the data format used by RESTCONF. It is a strict subset of JavaScript with six value types:

| JSON type | Syntax | Python equivalent |
|-----------|--------|------------------|
| string | `"double quotes only"` | `str` |
| number | `42` or `3.14` | `int` or `float` |
| boolean | `true` or `false` (lowercase) | `True` or `False` |
| null | `null` (lowercase) | `None` |
| array | `["a", "b", "c"]` | `list` |
| object | `{"key": "value"}` | `dict` |

A valid JSON object:

```json
{
  "name": "GigabitEthernet1",
  "prefix-length": 30,
  "enabled": true,
  "description": null,
  "address": ["10.1.12.1"]
}
```

**Common JSON syntax errors (exam targets):**

| Error | Wrong | Correct |
|-------|-------|---------|
| Single quotes | `{'name': 'Gi1'}` | `{"name": "Gi1"}` |
| Python bool | `"enabled": True` | `"enabled": true` |
| Python None | `"desc": None` | `"desc": null` |
| Trailing comma | `{"name": "Gi1",}` | `{"name": "Gi1"}` |
| Missing colon | `{"name" "Gi1"}` | `{"name": "Gi1"}` |
| Comments | `// not valid` | *(remove the comment)* |

**ietf-interfaces YANG structure:**

RESTCONF uses YANG data models. The ietf-interfaces model structures interface data as:

```json
{
  "ietf-interfaces:interface": {
    "name": "Loopback100",
    "description": "My loopback",
    "type": "iana-if-type:softwareLoopback",
    "enabled": true,
    "ietf-ip:ipv4": {
      "address": [
        { "ip": "10.100.100.1", "prefix-length": 32 }
      ]
    }
  }
}
```

Key naming conventions:
- The module prefix is always included: `ietf-interfaces:interface`, `iana-if-type:softwareLoopback`, `ietf-ip:ipv4`
- Interface type values: `iana-if-type:ethernetCsmacd` (physical), `iana-if-type:softwareLoopback` (loopback)
- `"enabled": true` — JSON boolean, not Python

---

### Python dict vs JSON — Critical Differences

These four differences cause the most failures when writing RESTCONF payloads:

| Feature | Python dict | JSON |
|---------|------------|------|
| Boolean true | `True` | `true` |
| Boolean false | `False` | `false` |
| Null / None | `None` | `null` |
| Quote character | Single `'` or double `"` | Double `"` only |
| Trailing comma | Allowed | **Not allowed** |
| Comments | `#` inline | **Not allowed** |

When Python's `json.dumps()` serialises a dict to a JSON string, it handles the conversion automatically (`True` → `true`, `None` → `null`). When you write JSON by hand, you must use JSON syntax.

```python
import json

py_dict = {"name": "Gi1", "enabled": True, "description": None}
json_str = json.dumps(py_dict, indent=2)
# Result:
# {
#   "name": "Gi1",
#   "enabled": true,
#   "description": null
# }
```

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| Python type identification | Read any variable or literal and name its type |
| requests library usage | Understand GET/POST and response handling |
| JSON construction | Write syntactically correct YANG-model JSON payloads |
| JSON parsing | Use `json.loads()` to extract values from API responses |
| JSON debugging | Identify and fix syntax errors in malformed JSON |
| RESTCONF prerequisites | Configure the HTTPS server and RESTCONF service on IOS-XE |

---

## 2. Topology & Scenario

The network team at Meridian Financial is building a Python-based automation toolchain to manage R1 and R2 programmatically. Before the team can run scripts against live routers, you have been asked to:

1. Review the draft scripts and verify they are correctly written
2. Construct the JSON payloads the scripts will send
3. Enable the RESTCONF API on R1 so the team can test their first live call

The physical topology is unchanged from lab-00. R1 and R2 are CSR1000v (IOS-XE) — IOS-XE is required for RESTCONF support. R3 hosts the EEM applets from the previous lab and is not touched in this lab.

```
               ┌─────────────────────────────┐
               │            PC1              │
               │           VPCS              │
               │  192.168.10.10/24           │
               └──────────────┬──────────────┘
                               │ eth0
                               │ 192.168.10.10/24
                               │
                               │ 192.168.10.1/24
                               │ Gi2
              ┌────────────────┴────────────────┐
              │              R1                 │
              │       CSR1000v (IOS-XE)         │
              │     Lo0: 1.1.1.1/32             │
              └──────────┬──────────────────────┘
                          │ Gi1
                          │ 10.1.12.1/30
                          │
                          │ 10.1.12.2/30
                          │ Gi1
              ┌───────────┴─────────────────────┐
              │              R2                 │
              │       CSR1000v (IOS-XE)         │
              │     Lo0: 2.2.2.2/32             │
              └──────────┬──────────────────────┘
                          │ Gi2
                          │ 10.1.23.1/30
                          │
                          │ 10.1.23.2/30
                          │ Gi0/0
              ┌───────────┴─────────────────────┐
              │              R3                 │
              │          IOSv / EEM             │
              │     Lo0: 3.3.3.3/32             │
              └──────────┬──────────────────────┘
                          │ Gi0/1
                          │ 192.168.20.1/24
                          │
                          │ 192.168.20.10/24
                          │ eth0
               ┌──────────┴──────────────────┐
               │            PC2              │
               │           VPCS              │
               │  192.168.20.10/24           │
               └─────────────────────────────┘
```

**Network addressing:**

| Link | Interface (R1 side) | IP (R1) | Interface (R2 side) | IP (R2) |
|------|--------------------|---------|--------------------|---------|
| R1–R2 | Gi1 | 10.1.12.1/30 | Gi1 | 10.1.12.2/30 |
| R2–R3 | Gi2 | 10.1.23.1/30 | Gi0/0 | 10.1.23.2/30 |
| R1–PC1 | Gi2 | 192.168.10.1/24 | — | 192.168.10.10/24 |
| R3–PC2 | Gi0/1 | 192.168.20.1/24 | — | 192.168.20.10/24 |

---

## 3. Hardware & Environment Specifications

### Device Inventory

| Device | Platform | IOS Version | Role |
|--------|---------|-------------|------|
| R1 | CSR1000v | IOS-XE 17.x | RESTCONF target |
| R2 | CSR1000v | IOS-XE 17.x | RESTCONF target |
| R3 | IOSv | IOS 15.9 | EEM host (no changes in this lab) |
| PC1 | VPCS | — | End host |
| PC2 | VPCS | — | End host |

### Cabling Table

| Connection | Source | Destination |
|-----------|--------|-------------|
| L1 | R1 GigabitEthernet1 | R2 GigabitEthernet1 |
| L2 | R2 GigabitEthernet2 | R3 GigabitEthernet0/0 |
| L3 | R1 GigabitEthernet2 | PC1 |
| L4 | R3 GigabitEthernet0/1 | PC2 |

### Console Access Table

| Device | Port | Connection Command |
|--------|------|--------------------|
| R1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R3 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| PC1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| PC2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |

### Workstation Requirements

Tasks 1–5 require only a text editor and Python 3.8+ on your workstation. No EVE-NG connection is needed for those tasks. Task 6 requires SSH or console access to R1.

Install the requests library before Task 2:
```bash
pip install requests
```

---

## 4. Base Configuration

The following is **pre-configured** on all devices via `setup_lab.py`:

- IP addressing on all interfaces (IPv4)
- OSPF area 0 — R1, R2, and R3 form full adjacencies
- SSH infrastructure — `ip ssh version 2`, `username admin`, `ip domain-name encor-lab.local`
- EEM applets on R3 (TRACK-INTERFACE, BACKUP-CONFIG, MATCH-SYSLOG) from lab-00
- Admin credential: `admin` / `Encor-API-2026`

The following is **NOT pre-configured** (you configure it in this lab):

- RESTCONF service on R1 and R2
- HTTPS web server on R1 and R2
- HTTP authentication method
- NETCONF service (covered in lab-02)

---

## 5. Lab Challenge: Core Implementation

> Tasks 1–5 are workbook exercises — no router interaction required. Read each script or JSON fragment carefully and answer the questions. Task 6 moves to the CLI.

---

### Task 1: Identify Python Data Types

Read **Script A** below. For each labelled variable, identify its Python data type.

```python
#!/usr/bin/env python3
# Script A — RESTCONF GET example

import requests, json, urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

ROUTER_IP    = "10.1.12.1"                    # (a)
AUTH         = ("admin", "Encor-API-2026")    # (b)
MAX_RETRIES  = 3                               # (c)
DEBUG        = True                            # (d)
EXCLUDED     = None                            # (e)
HEADERS      = {                               # (f)
    "Accept":       "application/yang-data+json",
    "Content-Type": "application/yang-data+json",
}
interface_names = []                           # (g)

def get_interfaces():
    url = f"https://{ROUTER_IP}/restconf/data/ietf-interfaces:interfaces"
    try:
        resp = requests.get(url, headers=HEADERS, auth=AUTH, verify=False)
        resp.raise_for_status()
        data       = resp.json()
        iface_list = data["ietf-interfaces:interfaces"]["interface"]
        for iface in iface_list:
            interface_names.append(iface["name"])
    except requests.exceptions.HTTPError as e:
        print(f"HTTP error: {e}")
    except requests.exceptions.ConnectionError:
        print("Cannot connect to router")
    except json.JSONDecodeError:
        print("Invalid JSON in response")
    return interface_names

if __name__ == "__main__":
    names = get_interfaces()
    print(f"Found {len(names)} interfaces: {names}")
```

Answer these questions in your notes:
- What is the data type of variable **(a)** `ROUTER_IP`?
- What is the data type of variable **(b)** `AUTH`?
- What is the data type of variable **(c)** `MAX_RETRIES`?
- What is the data type of variable **(d)** `DEBUG`?
- What is the data type of variable **(e)** `EXCLUDED`?
- What is the data type of variable **(f)** `HEADERS`?
- What is the data type of variable **(g)** `interface_names`?

**Verification:** Check your answers against Section 8 Solution 1 when done.

---

### Task 2: Trace a Python HTTP GET Script

Using **Script A** from Task 1, answer these questions:

- What HTTP method does `get_interfaces()` use?
- What is the full URL constructed when `ROUTER_IP = "10.1.12.1"`?
- What does `verify=False` do, and why is it used in a lab environment?
- What does `resp.raise_for_status()` do? What exception does it raise, and under what condition?
- Which exception is caught if the router is unreachable (port 443 not listening)?
- Which exception is caught if the router responds but returns non-JSON content?
- If the GET succeeds and `iface_list` contains two interfaces, what does `interface_names` contain at the end of the function?

**Verification:** Check your answers against Section 8 Solution 2 when done.

---

### Task 3: Construct a JSON Interface Payload

The automation team needs a JSON payload to create Loopback100 on R1 via a RESTCONF PUT request. Construct a valid JSON object that satisfies all of these requirements:

- Interface name: `Loopback100`
- Description: `Python Lab Interface`
- Interface type: software loopback (use the iana-if-type YANG identifier)
- Enabled state: `true` (JSON boolean)
- IPv4 address: `10.100.100.1`, prefix-length `32`
- IPv6 address: `2001:db8:100::1`, prefix-length `128`
- Use the `ietf-interfaces:interface` YANG model namespace as the root key
- Use `ietf-ip:ipv4` and `ietf-ip:ipv6` as the IP sub-object keys
- IPv4 and IPv6 addresses are each in an array named `address`

Write the complete JSON object in your notes.

**Verification:** Compare your JSON against Section 8 Solution 3. Validate JSON syntax with `python3 -c "import json; json.load(open('your_file.json'))"`.

---

### Task 4: Parse a JSON Response with json.loads()

The following Python string contains a RESTCONF GET response. Write a Python code block that:

1. Parses `SAMPLE_RESPONSE` into a Python dictionary using `json.loads()`
2. Navigates the nested structure to access the list of interfaces
3. For each interface, prints the name and its first IPv4 address

```python
SAMPLE_RESPONSE = """{
  "ietf-interfaces:interfaces": {
    "interface": [
      {
        "name": "GigabitEthernet1",
        "description": "To R2",
        "type": "iana-if-type:ethernetCsmacd",
        "enabled": true,
        "ietf-ip:ipv4": {
          "address": [{"ip": "10.1.12.1", "prefix-length": 30}]
        }
      },
      {
        "name": "Loopback0",
        "description": "",
        "type": "iana-if-type:softwareLoopback",
        "enabled": true,
        "ietf-ip:ipv4": {
          "address": [{"ip": "1.1.1.1", "prefix-length": 32}]
        }
      }
    ]
  }
}"""
```

Expected output when your code runs:
```
Name: GigabitEthernet1, IPv4: 10.1.12.1
Name: Loopback0, IPv4: 1.1.1.1
```

**Verification:** Run your code with `python3` and confirm the output matches. Compare against Section 8 Solution 4.

---

### Task 5: Identify and Fix JSON Syntax Errors

Each snippet below contains exactly one JSON syntax error. Identify the error and write the corrected version.

**Snippet A:**
```
{'name': 'Loopback0', 'enabled': true}
```

**Snippet B:**
```json
{
  "name": "GigabitEthernet1",
  "type": "iana-if-type:ethernetCsmacd",
}
```

**Snippet C:**
```json
{
  "name": "GigabitEthernet2",
  "enabled": False,
  "description": None
}
```

**Snippet D:**
```json
{
  "name" "Loopback1",
  "prefix-length": 32
}
```

**Verification:** Validate each corrected snippet with `python3 -c "import json; print(json.loads('''<snippet>'''))"`. Compare against Section 8 Solution 5.

---

### Task 6: Enable RESTCONF API Access on R1

The Python scripts from Tasks 1–4 target `https://10.1.12.1` — R1's RESTCONF endpoint. For those scripts to work, the HTTPS server and RESTCONF service must be enabled on R1.

- Enable the HTTPS web server on R1
- Configure the HTTP server to use local authentication
- Enable the RESTCONF service on R1
- Verify the YANG management processes are running

**Verification:** `show platform software yang-management process` must show `restconfd` in the running state. `show running-config | include http` and `show running-config | include restconf` must show the three commands you configured.

---

## 6. Verification & Analysis

### Task 1 Expected Answers

| Variable | Data Type |
|----------|-----------|
| `ROUTER_IP` | `str` |
| `AUTH` | `tuple` |
| `MAX_RETRIES` | `int` |
| `DEBUG` | `bool` |
| `EXCLUDED` | `NoneType` |
| `HEADERS` | `dict` |
| `interface_names` | `list` |

### Task 2 Expected Answers

| Question | Answer |
|----------|--------|
| HTTP method | GET |
| Full URL | `https://10.1.12.1/restconf/data/ietf-interfaces:interfaces` |
| `verify=False` | Disables TLS certificate validation — lab routers use self-signed certs |
| `raise_for_status()` | Raises `HTTPError` if `status_code >= 400` |
| Unreachable exception | `requests.exceptions.ConnectionError` |
| Non-JSON exception | `json.JSONDecodeError` |
| `interface_names` after 2 interfaces | A list with two interface name strings, e.g. `["GigabitEthernet1", "Loopback0"]` |

### Task 3 Expected JSON

See Section 8 Solution 3 for the complete correct payload.

Key points to verify:
- Root key must be `"ietf-interfaces:interface"` (singular, not plural)
- `"enabled": true` — lowercase, no quotes
- `"type": "iana-if-type:softwareLoopback"` — exact YANG identifier
- Both IPv4 and IPv6 addresses are arrays: `"address": [{ ... }]`
- `"prefix-length"` not `"prefix_length"` or `"mask"`

### Task 4 Expected Output

```
Name: GigabitEthernet1, IPv4: 10.1.12.1
Name: Loopback0, IPv4: 1.1.1.1
```

Key navigation path:
```python
data["ietf-interfaces:interfaces"]["interface"]  # list of interface dicts
iface["ietf-ip:ipv4"]["address"][0]["ip"]         # first IPv4 address
```

### Task 5 Expected Fixes

| Snippet | Error | Fix |
|---------|-------|-----|
| A | Single quotes used instead of double quotes | Replace `'` with `"` throughout |
| B | Trailing comma after last key-value pair | Remove `,` after `"ethernetCsmacd"` |
| C | Python `False` and `None` instead of JSON `false` and `null` | `False` → `false`, `None` → `null` |
| D | Missing `:` between key and value | Add `:` after `"name"` |

### Task 6 Verification Output

```
R1# show platform software yang-management process
confd            : Running                          ! ← NETCONF/RESTCONF daemon
nesd             : Running
syncfd           : Running
ncsshd           : Running
dmiauthd         : Running
nginx            : Running                          ! ← HTTPS reverse proxy for RESTCONF
ndbmand          : Running
pubd             : Running
restconfd        : Running                          ! ← RESTCONF service — must be Running

R1# show running-config | include http
ip http secure-server                               ! ← HTTPS enabled
ip http authentication local                        ! ← local user database for auth

R1# show running-config | include restconf
restconf                                            ! ← RESTCONF service enabled
```

---

## 7. Verification Cheatsheet

### Python Data Type Identification

```
str     : "quoted string"
int     : 42
float   : 3.14
bool    : True  /  False          (capital first letter in Python)
NoneType: None                    (capital N in Python)
list    : [item1, item2]          (square brackets)
dict    : {"key": "value"}        (curly braces, colon separator)
tuple   : ("a", "b")              (round brackets, usually 2 items)
```

| Type | How to identify | Common use |
|------|----------------|------------|
| `str` | Quotes around value | Interface names, IPs, hostnames |
| `int` | Plain integer, no quotes | Prefix-length, AS number, port |
| `bool` | `True` or `False` (Python) | Interface enabled, admin state |
| `NoneType` | `None` | Unset / optional field |
| `list` | `[...]` | Array of interfaces, neighbors |
| `dict` | `{...}` | Config block, JSON object |
| `tuple` | `(...)` | Auth credentials |

> **Exam tip:** The ENCOR exam shows Python snippets and asks you to identify data types. Tuples look like lists but use round brackets. Dicts look like JSON but allow single quotes and Python booleans.

### requests Module Syntax

```
import requests

resp = requests.get(url, headers=HEADERS, auth=AUTH, verify=False)
resp = requests.put(url, headers=HEADERS, auth=AUTH, json=payload, verify=False)
resp = requests.patch(url, headers=HEADERS, auth=AUTH, json=payload, verify=False)
resp = requests.post(url, headers=HEADERS, auth=AUTH, json=payload, verify=False)
resp = requests.delete(url, headers=HEADERS, auth=AUTH, verify=False)
```

| Attribute / Method | Purpose |
|-------------------|---------|
| `resp.status_code` | HTTP response code (200, 201, 401, 404, …) |
| `resp.json()` | Parse response body as JSON → Python dict |
| `resp.text` | Raw response body as string |
| `resp.raise_for_status()` | Raise `HTTPError` if `status_code >= 400` |
| `verify=False` | Disable TLS cert validation (lab use only) |
| `auth=("user", "pass")` | HTTP Basic Auth via tuple |

> **Exam tip:** `raise_for_status()` does NOT print the error — it raises an exception. You must catch `requests.exceptions.HTTPError` to handle it. Without it, a 401 response returns silently.

### JSON Syntax Rules

```
{
  "string_key":  "string_value",
  "int_key":     42,
  "bool_key":    true,
  "null_key":    null,
  "array_key":   ["item1", "item2"],
  "object_key":  { "nested": "value" }
}
```

| Rule | Details |
|------|---------|
| Keys | Always double-quoted strings |
| Strings | Double quotes only — single quotes are invalid |
| Booleans | `true` and `false` — lowercase, no quotes |
| Null | `null` — lowercase, no quotes |
| Trailing commas | Not allowed after last element |
| Comments | Not allowed in JSON |

### Python vs JSON Quick Reference

| Feature | Python dict | JSON |
|---------|------------|------|
| True | `True` | `true` |
| False | `False` | `false` |
| Null | `None` | `null` |
| Strings | `'single'` or `"double"` | `"double"` only |
| Trailing comma | Allowed | Not allowed |
| Convert dict to JSON | `json.dumps(d)` | — |
| Parse JSON string | — | `json.loads(s)` |

### RESTCONF YANG Namespace Reference

| Interface type | YANG value |
|---------------|------------|
| Physical Ethernet | `iana-if-type:ethernetCsmacd` |
| Loopback | `iana-if-type:softwareLoopback` |
| GRE tunnel | `iana-if-type:tunnel` |

| JSON key | Path in ietf-interfaces |
|----------|------------------------|
| Interface list | `["ietf-interfaces:interfaces"]["interface"]` |
| Interface name | `iface["name"]` |
| IPv4 address | `iface["ietf-ip:ipv4"]["address"][0]["ip"]` |
| IPv6 address | `iface["ietf-ip:ipv6"]["address"][0]["ip"]` |

### RESTCONF Prerequisites — IOS-XE

```
ip http secure-server
ip http authentication local
restconf
```

| Command | Purpose |
|---------|---------|
| `ip http secure-server` | Enable HTTPS server (required for RESTCONF) |
| `ip http authentication local` | Authenticate API requests against local user DB |
| `restconf` | Enable RESTCONF service |

### Verification Commands

| Command | What to Look For |
|---------|-----------------|
| `show platform software yang-management process` | `restconfd` and `nginx` both show `Running` |
| `show running-config \| include http` | `ip http secure-server` and `ip http authentication local` present |
| `show running-config \| include restconf` | `restconf` present |
| `python3 -c "import json; json.load(open('f.json'))"` | No output = valid JSON; `JSONDecodeError` = syntax error |
| `python3 -m json.tool < file.json` | Reformatted JSON output = valid; error = invalid |

### Common Automation Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| `SSLError: Max retries exceeded` | `ip http secure-server` not configured |
| HTTP 401 Unauthorized | User does not have privilege 15, or wrong password |
| HTTP 403 Forbidden | User authenticated but lacks authorization |
| HTTP 404 Not Found | Wrong YANG path in URL |
| HTTP 400 Bad Request | Malformed JSON payload (syntax error or wrong YANG schema) |
| `ConnectionError` | RESTCONF not enabled (`restconf` missing) or port 443 blocked |
| `JSONDecodeError` | Wrong `Accept` header — router returned XML instead of JSON |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Solution 1: Python Data Types

<details>
<summary>Click to view answers</summary>

| Variable | Data Type | Reason |
|----------|-----------|--------|
| `ROUTER_IP = "10.1.12.1"` | `str` | Quoted string literal |
| `AUTH = ("admin", "Encor-API-2026")` | `tuple` | Round brackets, two items |
| `MAX_RETRIES = 3` | `int` | Plain integer, no quotes |
| `DEBUG = True` | `bool` | Capital-T `True` keyword |
| `EXCLUDED = None` | `NoneType` | Capital-N `None` keyword |
| `HEADERS = {...}` | `dict` | Curly braces, colon separators |
| `interface_names = []` | `list` | Square brackets, initially empty |

</details>

### Solution 2: Tracing the HTTP GET Script

<details>
<summary>Click to view answers</summary>

| Question | Answer |
|----------|--------|
| HTTP method | `GET` — `requests.get()` |
| Full URL | `https://10.1.12.1/restconf/data/ietf-interfaces:interfaces` |
| `verify=False` | Skips TLS certificate validation. Lab routers use self-signed certificates that Python's SSL library would reject by default. |
| `raise_for_status()` | Raises `requests.exceptions.HTTPError` if `resp.status_code` is 400 or higher. This converts silent HTTP errors into Python exceptions. |
| Unreachable | `requests.exceptions.ConnectionError` — TCP/HTTPS connection could not be established |
| Non-JSON response | `json.JSONDecodeError` — `resp.json()` internally calls `json.loads()`, which raises this if the body is not valid JSON (e.g., the router returned an HTML error page) |
| `interface_names` after 2 interfaces | `["GigabitEthernet1", "Loopback0"]` — the name string of each interface dict was appended |

</details>

### Solution 3: JSON Interface Payload

<details>
<summary>Click to view complete JSON payload</summary>

```json
{
  "ietf-interfaces:interface": {
    "name": "Loopback100",
    "description": "Python Lab Interface",
    "type": "iana-if-type:softwareLoopback",
    "enabled": true,
    "ietf-ip:ipv4": {
      "address": [
        {
          "ip": "10.100.100.1",
          "prefix-length": 32
        }
      ]
    },
    "ietf-ip:ipv6": {
      "address": [
        {
          "ip": "2001:db8:100::1",
          "prefix-length": 128
        }
      ]
    }
  }
}
```

This file is also saved at `solutions/json/interface_payload.json`.

**Common mistakes:**
- Using `"ietf-interfaces:interfaces"` (plural) instead of `"ietf-interfaces:interface"` (singular) as root — plural is the collection; singular is a single interface
- Writing `"enabled": True` (Python) instead of `"enabled": true` (JSON)
- Writing `"prefix_length"` with underscore instead of `"prefix-length"` with hyphen

</details>

### Solution 4: Parse JSON Response

<details>
<summary>Click to view Python parsing code</summary>

```python
import json

data       = json.loads(SAMPLE_RESPONSE)
interfaces = data["ietf-interfaces:interfaces"]["interface"]

for iface in interfaces:
    name      = iface["name"]
    ipv4_addr = iface["ietf-ip:ipv4"]["address"][0]["ip"]
    print(f"Name: {name}, IPv4: {ipv4_addr}")
```

Output:
```
Name: GigabitEthernet1, IPv4: 10.1.12.1
Name: Loopback0, IPv4: 1.1.1.1
```

The full solution is saved at `solutions/scripts/parse_response.py`.

</details>

### Solution 5: Malformed JSON Fixes

<details>
<summary>Click to view corrected snippets</summary>

**Snippet A — Single quotes:**
```json
{"name": "Loopback0", "enabled": true}
```
Fix: Replace all `'` with `"`.

**Snippet B — Trailing comma:**
```json
{
  "name": "GigabitEthernet1",
  "type": "iana-if-type:ethernetCsmacd"
}
```
Fix: Remove the `,` after `"ethernetCsmacd"`.

**Snippet C — Python bool/None:**
```json
{
  "name": "GigabitEthernet2",
  "enabled": false,
  "description": null
}
```
Fix: `False` → `false`, `None` → `null`.

**Snippet D — Missing colon:**
```json
{
  "name": "Loopback1",
  "prefix-length": 32
}
```
Fix: Add `:` between `"name"` and `"Loopback1"`.

The corrected versions are saved at `solutions/json/malformed_fixed.json`.

</details>

### Solution 6: Enable RESTCONF on R1

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1 — enable RESTCONF API access
ip http secure-server
ip http authentication local
restconf
```

</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show platform software yang-management process
show running-config | include http
show running-config | include restconf
```

</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. Inject the fault first, then diagnose and fix using only show commands and your Python/JSON knowledge.

### Workflow

```bash
# The troubleshooting scenarios require RESTCONF to be configured on R1.
# Use apply_solution.py to reach the pre-fault baseline (not setup_lab.py).
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>      # restore to solution state
python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>  # Ticket 1
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>      # restore after each ticket
```

---

### Ticket 1 — Python Script Throws an SSL Connection Error to R1

The automation team reports their Python script crashes immediately with an SSL error when targeting R1. The script has not changed since it last worked.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>`

**Success criteria:** `requests.get("https://10.1.12.1/restconf/data/ietf-interfaces:interfaces", ...)` returns HTTP 200, and `show platform software yang-management process` shows all processes in the Running state.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Run `show ip http server status` on R1 — look at the "HTTP secure server" line.
2. Run `show ip http server secure status` on R1 — check if HTTPS is enabled.
3. Run `show running-config | include http` — verify both `ip http secure-server` and `ip http authentication local` are present.
4. Run `show platform software yang-management process` — check whether `nginx` (the HTTPS reverse proxy) is in the Running state.

The SSL error means the TCP connection on port 443 is refused or the SSL handshake fails — both caused by the HTTPS server being disabled.

</details>

<details>
<summary>Click to view Fix</summary>

```bash
R1# configure terminal
R1(config)# ip http secure-server
R1(config)# end
```

Re-run the Python script. It should return HTTP 200 and a JSON body.

</details>

---

### Ticket 2 — Python Script Returns HTTP 401 Unauthorized from R1

A new team member updated the R1 configuration and now all API calls return 401. The Python script's credentials have not changed.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py --host <eve-ng-ip>`

**Success criteria:** A requests.get() call to R1's RESTCONF endpoint returns HTTP 200, not 401.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Run `show running-config | include username` on R1 — check the admin user's privilege level.
2. RESTCONF requires privilege level 15 to access the API. A lower privilege returns 401 Unauthorized.
3. Confirm `ip http authentication local` is still present: `show running-config | include http`.
4. If both are present but auth still fails, verify the password matches what the script uses: `admin` / `Encor-API-2026`.

</details>

<details>
<summary>Click to view Fix</summary>

```bash
R1# configure terminal
R1(config)# no username admin
R1(config)# username admin privilege 15 secret Encor-API-2026
R1(config)# end
```

The admin user must have privilege 15 for RESTCONF authentication to succeed.

</details>

---

### Ticket 3 — Python Script Cannot Reach R1's RESTCONF Endpoint (Connection Refused)

The Python script reports a `ConnectionError` when trying to reach `https://10.1.12.1`. The HTTPS server appears to be up.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py --host <eve-ng-ip>`

**Success criteria:** `show platform software yang-management process` shows `restconfd` in the Running state, and the Python script returns HTTP 200.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Run `show platform software yang-management process` on R1 — look specifically for the `restconfd` row.
2. Run `show running-config | include restconf` — verify the `restconf` global command is present.
3. Run `show running-config | include http` — confirm `ip http secure-server` and `ip http authentication local` are both present.
4. The HTTPS server (`nginx`) may be running while RESTCONF itself is disabled — these are separate services. A running nginx with no restconfd means HTTPS connects but returns 503 or connection refused on the RESTCONF path.

</details>

<details>
<summary>Click to view Fix</summary>

```bash
R1# configure terminal
R1(config)# restconf
R1(config)# end
```

After enabling, allow 5–10 seconds for `restconfd` to start. Verify with `show platform software yang-management process`.

</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] Task 1: Identified all seven variable data types in Script A correctly
- [ ] Task 2: Correctly answered all seven Script A tracing questions
- [ ] Task 3: Constructed a valid ietf-interfaces JSON payload for Loopback100 with IPv4 and IPv6
- [ ] Task 4: Written Python code that parses SAMPLE_RESPONSE and prints name + IPv4 for each interface
- [ ] Task 5: Identified and fixed all four JSON syntax errors
- [ ] Task 6: RESTCONF enabled on R1 — `show platform software yang-management process` shows `restconfd: Running`

### Troubleshooting

- [ ] Ticket 1: Diagnosed and resolved the SSL connection failure on R1
- [ ] Ticket 2: Diagnosed and resolved the HTTP 401 Unauthorized error on R1
- [ ] Ticket 3: Diagnosed and resolved the RESTCONF connection failure on R1
