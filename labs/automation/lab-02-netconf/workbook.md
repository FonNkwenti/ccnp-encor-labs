# Lab 02: NETCONF Configuration and Verification

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

**Exam Objective:** 4.6 — Configure and verify NETCONF and RESTCONF | Automation and Programmability

This lab introduces NETCONF (Network Configuration Protocol), the SSH-based, XML-encoded management protocol that underpins IOS-XE's model-driven programmability. You will enable NETCONF on two CSR1000v routers, exchange capabilities via the hello handshake, and use Python's ncclient library to retrieve configuration, create interfaces, query operational state, and stage changes through the candidate datastore — the four operations that distinguish NETCONF from CLI management.

### NETCONF Architecture

NETCONF (RFC 6241) is a network management protocol that operates over SSH using port 830. Unlike SNMP or CLI scraping, NETCONF is transaction-oriented: every operation is an explicit RPC with a structured XML request and response. The protocol has four layers:

| Layer | Function |
|-------|----------|
| Content | YANG-modeled data (what you're reading/writing) |
| Operations | RPCs — get, get-config, edit-config, commit, lock, unlock |
| Messages | XML envelope — `<rpc>` request, `<rpc-reply>` response |
| Transport | SSH subsystem "netconf" on port 830 |

On IOS-XE, the NETCONF subsystem is activated with `netconf-yang`. Once running, the device advertises its YANG model capabilities via the hello message — a list of URNs identifying every supported YANG module and feature.

**Hello exchange:** When a client opens an SSH session to port 830 with the `netconf` subsystem, both sides send a `<hello>` immediately. The device's hello lists its capabilities. The client sends its own hello. Only after both hellos are exchanged can RPCs begin. The session ends with a `</netconf:session>` closing tag.

### YANG Data Models and Datastores

YANG (RFC 7950) is the data modeling language that defines the structure, types, and constraints of configuration and operational data. IOS-XE ships with:

| Model Category | Examples | Use Case |
|----------------|----------|----------|
| IETF standards | `ietf-interfaces`, `ietf-ip`, `ietf-routing` | Vendor-neutral interface/IP config |
| Cisco native | `Cisco-IOS-XE-native` | Full IOS-XE CLI parity |
| Cisco operational | `Cisco-IOS-XE-ospf-oper`, `Cisco-IOS-XE-bgp-oper` | Read-only operational state |

NETCONF operates on **datastores** — named collections of configuration:

| Datastore | Description | Writable? |
|-----------|-------------|-----------|
| `running` | Active configuration | Yes (default) |
| `startup` | Config loaded at boot | Yes |
| `candidate` | Staging area for changes | Yes — requires feature flag |

The **candidate datastore** is the key feature unlocked by `netconf-yang feature candidate-datastore`. It lets you stage multiple edits, validate them, and then `commit` atomically to running. If something goes wrong before commit, you `discard-changes` and running is untouched. This is fundamentally safer than editing running directly.

### NETCONF Operations

| RPC | Datastore | Description |
|-----|-----------|-------------|
| `get` | Operational | Retrieve operational state (show command equivalent) |
| `get-config` | Any | Retrieve configuration from named datastore |
| `edit-config` | running / candidate | Create, modify, or delete configuration |
| `commit` | candidate→running | Apply staged candidate config to running |
| `discard-changes` | candidate | Rollback all staged changes |
| `lock` | Any | Prevent concurrent edits (exclusive lock) |
| `unlock` | Any | Release a previously acquired lock |
| `get-schema` | — | Retrieve the YANG module definition |

The `<filter>` element in get and get-config operations accepts two types:
- **subtree**: XPath-like tree path, selecting by element name and namespace
- **xpath**: Full XPath expression (requires capability advertisement)

### ncclient Python Library

ncclient is the standard Python library for NETCONF. It handles the SSH connection, hello exchange, message framing, and RPC serialization:

```python
from ncclient import manager

with manager.connect(
    host="10.1.12.1",
    port=830,
    username="admin",
    password="Encor-API-2026",
    hostkey_verify=False,          # disable host key check for lab
    device_params={"name": "csr"}, # tells ncclient we're connecting to IOS-XE
    timeout=30,
) as m:
    reply = m.get_config(source="running")
    print(reply.xml)               # raw XML response string
```

`device_params={"name": "csr"}` activates IOS-XE-specific quirks (like the `<nc:ok/>` namespace prefix in commit replies). Without it, ncclient may fail to parse valid IOS-XE responses.

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| NETCONF enablement | Configure `netconf-yang` and candidate datastore on IOS-XE |
| Hello exchange | Read and interpret device capability advertisements |
| ncclient get-config | Build subtree filters, parse XML replies with ElementTree |
| edit-config (running) | Create interfaces directly in running datastore |
| Candidate datastore workflow | lock → edit → commit → unlock |
| Operational data retrieval | Use `get` with Cisco-IOS-XE oper YANG models |
| NETCONF vs CLI comparison | Map RPC operations to equivalent show/config commands |

---

## 2. Topology & Scenario

**Scenario:** Globex Corp's network automation team has completed the Python and JSON foundations. The next step is hands-on NETCONF integration: both core routers (R1 and R2, CSR1000v) must be enabled as NETCONF endpoints so that the orchestration platform can retrieve interface state, push configurations, and query OSPF neighbor health without using the CLI. Your task is to enable the NETCONF YANG subsystem, verify it responds on port 830, and implement the four key operations the platform requires.

```
                         ┌──────────────────────────┐
                         │           R1             │
                         │    (CSR1000v / IOS-XE)   │
                         │  Lo0: 1.1.1.1/32         │
                         │  NETCONF: port 830        │
                         │  RESTCONF: port 443       │
                         └────┬───────────┬──────────┘
                              │ Gi1        │ Gi2
                    10.1.12.1/30│        192.168.10.1/24│
                              │           │
                    10.1.12.2/30│         │ 192.168.10.10/24
                              │ Gi1       │ eth0
                 ┌────────────┘      ┌────┴──────────────┐
                 │                   │        PC1        │
┌────────────────┴─────────┐         │  (VPCS)           │
│           R2             │         │  gw 192.168.10.1  │
│    (CSR1000v / IOS-XE)   │         └───────────────────┘
│  Lo0: 2.2.2.2/32         │
│  NETCONF: port 830        │
│  RESTCONF: port 443       │
└────────────┬─────────────┘
             │ Gi2
   10.1.23.1/30│
             │
   10.1.23.2/30│
             │ Gi0/0
┌────────────┴─────────────┐
│           R3             │
│    (IOSv / EEM Host)     │
│  Lo0: 3.3.3.3/32         │
│  No NETCONF (IOS classic) │
└────────────┬─────────────┘
             │ Gi0/1
   192.168.20.1/24│
             │
   192.168.20.10/24│ eth0
        ┌────┴──────────────┐
        │       PC2         │
        │  (VPCS)           │
        │  gw 192.168.20.1  │
        └───────────────────┘
```

**Key addresses:**

| Device | Interface | IPv4 Address |
|--------|-----------|-------------|
| R1 | Lo0 | 1.1.1.1/32 |
| R1 | Gi1 | 10.1.12.1/30 |
| R1 | Gi2 | 192.168.10.1/24 |
| R2 | Lo0 | 2.2.2.2/32 |
| R2 | Gi1 | 10.1.12.2/30 |
| R2 | Gi2 | 10.1.23.1/30 |
| R3 | Lo0 | 3.3.3.3/32 |
| R3 | Gi0/0 | 10.1.23.2/30 |
| R3 | Gi0/1 | 192.168.20.1/24 |
| PC1 | eth0 | 192.168.10.10/24 |
| PC2 | eth0 | 192.168.20.10/24 |

---

## 3. Hardware & Environment Specifications

| Link | Source | Destination | Subnet |
|------|--------|-------------|--------|
| L1 | R1 Gi1 | R2 Gi1 | 10.1.12.0/30 |
| L2 | R2 Gi2 | R3 Gi0/0 | 10.1.23.0/30 |
| L3 | R1 Gi2 | PC1 eth0 | 192.168.10.0/24 |
| L4 | R3 Gi0/1 | PC2 eth0 | 192.168.20.0/24 |

| Device | Platform | Role |
|--------|----------|------|
| R1 | CSR1000v (IOS-XE 17.x) | NETCONF/RESTCONF primary endpoint |
| R2 | CSR1000v (IOS-XE 17.x) | NETCONF/RESTCONF secondary endpoint |
| R3 | IOSv (IOS classic) | EEM host — no NETCONF |
| PC1 | VPCS | LAN endpoint |
| PC2 | VPCS | LAN endpoint |

**Console Access Table:**

| Device | Port | Connection Command |
|--------|------|--------------------|
| R1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R3 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| PC1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| PC2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |

**Workstation prerequisites:**

```
pip install ncclient
```

The ncclient library handles SSH transport, XML framing, and hello exchange. Python 3.8+ required.

---

## 4. Base Configuration

The `setup_lab.py` script pushes the following to each device. These are pre-configured when you start this lab:

**Pre-configured on R1 and R2:**
- Hostname and DNS lookup disabled
- Local user (admin, privilege 15) with SSH v2
- IP addressing on all interfaces (Loopback0, Gi1, Gi2)
- OSPF process 1, area 0, with router IDs and passive interfaces
- RESTCONF (`restconf`, `ip http secure-server`, `ip http authentication local`) — carried forward from lab-01

**Pre-configured on R3:**
- Hostname, SSH, OSPF as above
- All three EEM applets from lab-00 (TRACK-INTERFACE, BACKUP-CONFIG, MATCH-SYSLOG)
- Object tracking on Gi0/0

**NOT pre-configured (you configure these):**
- NETCONF YANG daemon on R1 and R2
- Candidate datastore feature on R1 and R2
- Any Loopback interfaces created via NETCONF

---

## 5. Lab Challenge: Core Implementation

### Task 1: Enable NETCONF on R1 and R2

- Enable the NETCONF YANG subsystem on both CSR1000v routers.
- Enable the candidate datastore feature so that edit-config can target the candidate datastore for staged changes.
- Confirm the YANG management process reports both `netconfd` and `nginx` as Running.

**Verification:** `show platform software yang-management process` must show `netconfd: Running` (and `nginx: Running` for RESTCONF) on both R1 and R2.

---

### Task 2: Confirm NETCONF SSH Connectivity

- From your workstation, open a raw SSH connection to R1 on port 830 using the `netconf` subsystem.
- Observe the hello message R1 sends — identify at least three YANG model URNs in the capabilities list.
- Identify the `urn:ietf:params:netconf:base:1.1` capability that signals NETCONF 1.1 framing support.
- Send the closing session tag to end the connection gracefully.

**Verification:** The SSH connection to port 830 succeeds; R1 immediately sends an XML `<hello>` element containing a `<capabilities>` list. The connection closes cleanly when you send `]]>]]>`.

---

### Task 3: Connect via ncclient and Inspect Capabilities

- Write a short Python script that connects to R1 using ncclient (port 830, SSH).
- Print the list of capabilities R1 advertised in the hello exchange.
- Identify which of the following are present: `ietf-interfaces`, `Cisco-IOS-XE-native`, `ietf-netconf-monitoring`.
- Confirm the session ID and NETCONF server version from the hello response.

**Verification:** `m.server_capabilities` must include at least `urn:ietf:params:xml:ns:yang:ietf-interfaces` and `urn:ietf:params:netconf:base:1.1`.

---

### Task 4: Retrieve Interface Configuration with get-config

- Using ncclient, send a `get-config` RPC to R1 targeting the running datastore.
- Include a subtree filter that selects only `ietf-interfaces:interfaces`.
- Parse the XML reply and print a table of interface names and IPv4 addresses.
- Repeat for the candidate datastore and confirm it mirrors running (no staged changes yet).

**Verification:** The output table must list Lo0 (1.1.1.1), Gi1 (10.1.12.1), and Gi2 (192.168.10.1) from the running datastore.

---

### Task 5: Create Loopback200 via edit-config (Running)

- Construct an XML payload using the `ietf-interfaces` YANG model to create Loopback200 with address 10.200.200.1/32.
- Set the interface type to `ianaift:softwareLoopback` and `enabled` to true.
- Send an `edit-config` RPC targeting the running datastore.
- Confirm the new interface appears on R1.

**Verification:** `show interfaces Loopback200` on R1 shows the interface is up/up with IP address 10.200.200.1. A follow-up `get-config` with an ietf-interfaces filter must include Loopback200 in the reply.

---

### Task 6: Retrieve OSPF Operational State via get

- Using ncclient, send a `get` RPC (not `get-config`) to R1 with a subtree filter targeting the `Cisco-IOS-XE-ospf-oper` YANG module.
- First, issue a `get-schema` RPC for `Cisco-IOS-XE-ospf-oper` to confirm the module is available and identify the root container name.
- Build a filter targeting `ospf-oper-data/ospf-state/.../ospf-neighbor` to retrieve OSPF neighbor entries.
- Print the neighbor router IDs, states, and dead-timer values from the XML response.

**Verification:** The response must list R2 (2.2.2.2) as a neighbor of R1 in Full state. Compare to `show ip ospf neighbor` on R1 to confirm the data matches.

---

### Task 7: Candidate Datastore — Lock, Stage, Commit, Unlock

- Lock the candidate datastore on R1 to prevent concurrent edits.
- Send an `edit-config` RPC targeting candidate to create Loopback201 (10.201.201.1/32).
- Confirm Loopback201 is NOT yet in running (it is staged only).
- Send a `commit` RPC to apply the candidate to running.
- Unlock the candidate datastore.
- Verify Loopback201 now appears in both running config and the router CLI.

**Verification:** Before commit — `get-config source=running` must NOT contain Loopback201. After commit — `get-config source=running` must contain Loopback201 and `show interfaces Loopback201` must show up/up on R1.

---

## 6. Verification & Analysis

### Task 1: YANG Management Process

```
R1# show platform software yang-management process
confd             : Running
nesd              : Running
syncfd            : Running
ncsshd            : Running     ! ← NETCONF SSH daemon — must be Running
dmiauthd          : Running
nginx             : Running     ! ← RESTCONF/HTTP daemon — must be Running
ndbmand           : Running
pubd              : Running

R1# show platform software yang-management process state
Total number of YANG-management processes: 8
                  Name      PID  State
                confd     4321  UP      ! ← config daemon
                ncsshd     4567  UP      ! ← netconf-yang SSH process
                 nginx     4789  UP      ! ← restconf process
```

### Task 2: Raw SSH Hello

```
$ ssh -s -p 830 admin@10.1.12.1 netconf
admin@10.1.12.1's password:
<?xml version="1.0" encoding="UTF-8"?>
<hello xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
  <capabilities>
    <capability>urn:ietf:params:netconf:base:1.0</capability>
    <capability>urn:ietf:params:netconf:base:1.1</capability>           ! ← NETCONF 1.1 confirmed
    <capability>urn:ietf:params:netconf:capability:candidate:1.0</capability>  ! ← candidate datastore
    <capability>urn:ietf:params:xml:ns:yang:ietf-interfaces?module=ietf-interfaces&amp;revision=2018-02-20</capability>  ! ← ietf-interfaces YANG
    <capability>http://cisco.com/ns/yang/Cisco-IOS-XE-native?module=Cisco-IOS-XE-native&amp;revision=2019-11-01</capability>
    ...
  </capabilities>
  <session-id>1</session-id>   ! ← session ID assigned by server
</hello>
]]>]]>
```

### Task 4: get-config Interface Table

```python
# Expected output from netconf_get_config.py
Interface                 IPv4 Address         Admin Status
------------------------------------------------------------
Loopback0                 1.1.1.1              up          ! ← Lo0 present
GigabitEthernet1          10.1.12.1            up          ! ← Gi1 present
GigabitEthernet2          192.168.10.1         up          ! ← Gi2 present
```

### Task 5: Loopback200 Verification

```
R1# show interfaces Loopback200
Loopback200 is up, line protocol is up        ! ← interface up/up
  Hardware is Loopback
  Description: Created via NETCONF             ! ← description from XML payload
  Internet address is 10.200.200.1/32          ! ← correct IP assigned
  MTU 65535 bytes, BW 8000000 Kbit/sec, DLY 5000 usec,

R1# show ip interface brief | include Loopback200
Loopback200            10.200.200.1    YES NVRAM  up                    up  ! ← active
```

get-config after edit:
```xml
<interface>
  <name>Loopback200</name>                        <!-- ← must appear -->
  <description>Created via NETCONF</description>
  <type xmlns:ianaift="...">ianaift:softwareLoopback</type>
  <enabled>true</enabled>
  <ipv4 xmlns="...">
    <address>
      <ip>10.200.200.1</ip>                       <!-- ← address confirmed -->
      <prefix-length>32</prefix-length>
    </address>
  </ipv4>
</interface>
```

### Task 6: OSPF Operational Data

```python
# Expected output from netconf_get_ospf.py
Neighbor ID        Interface             State           Dead Timer
-----------------------------------------------------------------
2.2.2.2            GigabitEthernet1      full            00:00:35   ! ← R2 as Full neighbor
```

Compare to CLI:
```
R1# show ip ospf neighbor
Neighbor ID     Pri   State           Dead Time   Address         Interface
2.2.2.2           1   FULL/DR         00:00:37    10.1.12.2       GigabitEthernet1  ! ← matches NETCONF output
```

### Task 7: Candidate Datastore Workflow

Pre-commit running check (Loopback201 absent):
```python
# get-config source=running — Loopback201 must NOT appear
<interfaces>
  <interface><name>Loopback0</name>...</interface>
  <interface><name>GigabitEthernet1</name>...</interface>
  <interface><name>GigabitEthernet2</name>...</interface>
  <interface><name>Loopback200</name>...</interface>
  <!-- No Loopback201 here — staged in candidate only -->   ! ← confirms pre-commit state
</interfaces>
```

Post-commit verification:
```
R1# show interfaces Loopback201
Loopback201 is up, line protocol is up         ! ← interface active after commit
  Internet address is 10.201.201.1/32           ! ← correct IP

R1# show running-config | include Loopback201
interface Loopback201                           ! ← in running config
 ip address 10.201.201.1 255.255.255.255
```

---

## 7. Verification Cheatsheet

### NETCONF Enablement (IOS-XE)

```
netconf-yang
netconf-yang feature candidate-datastore
```

| Command | Purpose |
|---------|---------|
| `netconf-yang` | Start the NETCONF YANG subsystem (SSH port 830) |
| `netconf-yang feature candidate-datastore` | Enable candidate datastore for staged config changes |

> **Exam tip:** `netconf-yang` is IOS-XE only. IOSv and classic IOS do not support it. On the exam, questions about NETCONF configuration always target IOS-XE (CSR1000v, Catalyst, ISR with XE).

### NETCONF Verification Commands

| Command | What to Look For |
|---------|-----------------|
| `show platform software yang-management process` | `ncsshd: Running` (NETCONF SSH) and `nginx: Running` (RESTCONF) |
| `show platform software yang-management process state` | All processes in UP state |
| `show netconf-yang sessions` | Active NETCONF client sessions |
| `show netconf-yang statistics` | RPC counts — confirms operations are being received |
| `show netconf-yang datastores` | Lists running, startup, candidate availability |

> **Exam tip:** `show netconf-yang sessions` is the primary command to confirm a client is connected. `show platform software yang-management process` confirms the daemon is running, but does not show active clients.

### ncclient Connection

```python
from ncclient import manager

m = manager.connect(
    host="<router-ip>",
    port=830,
    username="<user>",
    password="<pass>",
    hostkey_verify=False,
    device_params={"name": "csr"},
)
```

| Parameter | Purpose |
|-----------|---------|
| `port=830` | NETCONF SSH port (RFC 6242) |
| `hostkey_verify=False` | Disable SSH host key check (lab only) |
| `device_params={"name": "csr"}` | IOS-XE quirks handler |

### NETCONF Operations via ncclient

```python
# get-config with subtree filter
reply = m.get_config(source="running", filter=FILTER_XML)

# edit-config targeting running
reply = m.edit_config(target="running", config=CONFIG_XML)

# Candidate datastore workflow
m.lock(target="candidate")
m.edit_config(target="candidate", config=CONFIG_XML)
m.commit()
m.unlock(target="candidate")

# get (operational data)
reply = m.get(filter=FILTER_XML)

# get-schema
reply = m.get_schema("Cisco-IOS-XE-ospf-oper")
```

| Operation | Target | Description |
|-----------|--------|-------------|
| `get_config` | running / candidate / startup | Read configuration data |
| `edit_config` | running / candidate | Write configuration data |
| `commit()` | (candidate → running) | Apply staged changes |
| `discard_changes()` | candidate | Rollback staged changes |
| `lock(target=)` | Any datastore | Exclusive lock — prevents concurrent edits |
| `unlock(target=)` | Any datastore | Release lock |
| `get()` | Operational | Read live state (show command equivalent) |
| `get_schema()` | — | Retrieve YANG module definition |

> **Exam tip:** `get` vs `get-config` — `get-config` retrieves a datastore (config only). `get` retrieves operational state (running stats, neighbor tables, interface counters). On the exam, OSPF neighbor state = `get`. Interface config = `get-config`.

### XML Filter Structure

```xml
<filter type="subtree">
  <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces"/>
</filter>
```

| Filter Type | Syntax | Use Case |
|-------------|--------|----------|
| subtree | Tag + namespace selector | Most common — filter by YANG container |
| xpath | Full XPath expression | Requires `urn:ietf:params:netconf:capability:xpath:1.0` capability |

### Common NETCONF Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| SSH connection to port 830 refused | `netconf-yang` not configured |
| ncclient `AuthenticationError` | Wrong username/password, or user not privilege 15 |
| `edit-config` returns `access-denied` | User privilege too low (need privilege 15) |
| `lock` RPC fails with `operation-not-supported` | `netconf-yang feature candidate-datastore` not configured |
| `commit` RPC fails | Nothing in candidate to commit, or candidate datastore not enabled |
| `get` for Cisco oper model returns empty | Wrong YANG path — use `get-schema` to confirm module structure |
| `RPCError: lock denied` | Another session holds the lock — check `show netconf-yang sessions` |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Task 1: Enable NETCONF

<details>
<summary>Click to view R1 and R2 Configuration</summary>

```bash
! R1 (apply same commands on R2)
netconf-yang
netconf-yang feature candidate-datastore
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show platform software yang-management process
show platform software yang-management process state
show netconf-yang datastores
```
</details>

---

### Task 2: Raw SSH Hello

<details>
<summary>Click to view SSH Subsystem Command and Expected Hello</summary>

```bash
# From workstation
ssh -s -p 830 admin@10.1.12.1 netconf

# R1 sends hello immediately — look for:
# <capability>urn:ietf:params:netconf:capability:candidate:1.0</capability>
# <capability>urn:ietf:params:xml:ns:yang:ietf-interfaces?...

# To close gracefully, send:
]]>]]>
```
</details>

---

### Task 3: ncclient Capabilities

<details>
<summary>Click to view Python Script</summary>

```python
from ncclient import manager

with manager.connect(
    host="10.1.12.1", port=830,
    username="admin", password="Encor-API-2026",
    hostkey_verify=False, device_params={"name": "csr"},
) as m:
    print(f"Session ID: {m.session_id}")
    for cap in m.server_capabilities:
        if "ietf-interfaces" in cap or "Cisco-IOS-XE-native" in cap or "monitoring" in cap:
            print(f"  {cap}")
```
</details>

---

### Task 4: get-config Interface List

<details>
<summary>Click to view Solution Script</summary>

See `solutions/scripts/netconf_get_config.py` for the full annotated script.

Key elements:
```python
FILTER = """
<filter type="subtree">
  <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces"/>
</filter>
"""
reply = m.get_config(source="running", filter=FILTER)
```
</details>

---

### Task 5: Create Loopback200

<details>
<summary>Click to view XML Payload and ncclient Call</summary>

See `solutions/xml/loopback200_config.xml` for the full payload.
See `solutions/scripts/netconf_create_loopback.py` for the complete script.

Key structure:
```xml
<config>
  <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
    <interface>
      <name>Loopback200</name>
      <type xmlns:ianaift="urn:ietf:params:xml:ns:yang:iana-if-type">
        ianaift:softwareLoopback
      </type>
      <enabled>true</enabled>
      <ipv4 xmlns="urn:ietf:params:xml:ns:yang:ietf-ip">
        <address><ip>10.200.200.1</ip><prefix-length>32</prefix-length></address>
      </ipv4>
    </interface>
  </interfaces>
</config>
```

```python
reply = m.edit_config(target="running", config=CONFIG_XML)
assert reply.ok
```
</details>

---

### Task 6: OSPF Operational Data

<details>
<summary>Click to view get-schema and OSPF Filter</summary>

```python
# First: confirm the module and its root container
schema = m.get_schema("Cisco-IOS-XE-ospf-oper")
print(schema.data)   # look for: container ospf-oper-data { ...

# Then query operational state
OSPF_FILTER = """
<filter type="subtree">
  <ospf-oper-data xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-ospf-oper">
    <ospf-state>
      <ospf-instance>
        <ospf-area>
          <ospf-interface>
            <ospf-neighbor/>
          </ospf-interface>
        </ospf-area>
      </ospf-instance>
    </ospf-state>
  </ospf-oper-data>
</filter>
"""
reply = m.get(filter=OSPF_FILTER)
```

See `solutions/scripts/netconf_get_ospf.py` and `solutions/xml/ospf_neighbor_filter.xml`.
</details>

---

### Task 7: Candidate Datastore Workflow

<details>
<summary>Click to view Full Candidate Workflow Script</summary>

See `solutions/scripts/netconf_candidate.py` for the complete annotated script.

```python
m.lock(target="candidate")
try:
    m.edit_config(target="candidate", config=LOOPBACK201_CONFIG)
    m.commit()
finally:
    m.unlock(target="candidate")
```

The `try/finally` ensures unlock always runs even if commit fails.
</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world NETCONF fault. Inject the fault first, then diagnose and fix using only show commands and ncclient error messages.

> The troubleshooting scenarios require NETCONF to be configured on R1.
> Use `apply_solution.py` to reach the known-good state before injecting a fault.

### Workflow

```bash
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>   # restore known-good state
python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>  # Ticket 1
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>   # restore
```

---

### Ticket 1 — NETCONF Connections to R1 Are Refused

Your automation script ran successfully yesterday. This morning it cannot connect to R1 on port 830. All other network connectivity to R1 is intact — you can SSH to port 22 and reach R1's RESTCONF API.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>`

**Success criteria:** ncclient can connect to R1 on port 830 and complete a hello exchange. `show netconf-yang sessions` shows no errors.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Attempt ncclient connection — observe `SSHError: not connected` or similar
2. On R1: `show platform software yang-management process` — check for `ncsshd: NOT RUNNING`
3. `show running-config | include netconf` — look for missing `netconf-yang` line
4. Compare to baseline: `show running-config | section netconf` should show both `netconf-yang` lines
</details>

<details>
<summary>Click to view Fix</summary>

```
R1(config)# netconf-yang
```

Verify:
```
R1# show platform software yang-management process
ncsshd            : Running
```
</details>

---

### Ticket 2 — Python Script Connects but edit-config Returns Permission Denied

An intern reports that NETCONF connections succeed (the hello exchange completes and get-config works) but any attempt to create or modify configuration returns an `RPCError: access-denied`. The script worked last week.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py --host <eve-ng-ip>`

**Success criteria:** edit-config targeting running completes without error. Loopback200 can be created via NETCONF.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Run ncclient script — confirm hello succeeds, then observe RPCError on edit_config
2. On R1: `show running-config | include username` — check privilege level for admin user
3. NETCONF requires the authenticated user to have **privilege 15** for write operations
4. Compare: `username admin privilege 1 secret ...` is the fault — should be `privilege 15`
</details>

<details>
<summary>Click to view Fix</summary>

```
R1(config)# no username admin
R1(config)# username admin privilege 15 secret Encor-API-2026
```

Verify:
```
R1# show running-config | include username admin
username admin privilege 15 secret 9 ...
```
</details>

---

### Ticket 3 — Locking the Candidate Datastore Fails with operation-not-supported

The orchestration platform uses the candidate datastore workflow: lock → edit → commit → unlock. The lock RPC now returns an XML error `<error-tag>operation-not-supported</error-tag>`. Simple get-config and edit-config to running still work.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py --host <eve-ng-ip>`

**Success criteria:** `m.lock(target="candidate")` completes without error. The full candidate workflow (lock → edit-config to candidate → commit → unlock) succeeds and Loopback201 appears in running config.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Run `netconf_candidate.py` — observe `RPCError: operation-not-supported` on lock
2. On R1: `show netconf-yang datastores` — confirm candidate datastore is listed
3. If candidate is absent: `show running-config | include netconf-yang` — look for missing feature line
4. `urn:ietf:params:netconf:capability:candidate:1.0` must be in R1's hello capabilities
</details>

<details>
<summary>Click to view Fix</summary>

```
R1(config)# netconf-yang feature candidate-datastore
```

Verify:
```
R1# show netconf-yang datastores
Name: candidate
Locked-By-Session: none
```
Reconnect ncclient and confirm `urn:ietf:params:netconf:capability:candidate:1.0` appears in `m.server_capabilities`.
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] `netconf-yang` and `netconf-yang feature candidate-datastore` configured on R1 and R2
- [ ] `show platform software yang-management process` shows `ncsshd: Running` on both routers
- [ ] Raw SSH to port 830 succeeds; hello capabilities list visible
- [ ] ncclient connects to R1; `m.server_capabilities` includes `ietf-interfaces` and `candidate` URNs
- [ ] `get-config source=running` with ietf-interfaces filter lists Lo0, Gi1, Gi2
- [ ] Loopback200 (10.200.200.1/32) created via `edit-config target=running`; verified on router CLI
- [ ] `get` RPC returns OSPF neighbor data showing R2 in Full state
- [ ] Candidate workflow completed: lock → edit-config Loopback201 to candidate → confirm absent from running → commit → verify in running → unlock

### Troubleshooting

- [ ] Ticket 1 diagnosed and fixed (NETCONF service restored on R1)
- [ ] Ticket 2 diagnosed and fixed (edit-config permission restored)
- [ ] Ticket 3 diagnosed and fixed (candidate datastore restored)
