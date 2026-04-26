# Lab 01 — AAA Authentication and Authorization

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

**Exam Objective:** 5.1, 5.1.b — Infrastructure security: AAA authentication and authorization using local database; TACACS+ vs RADIUS characteristics

This lab builds on the SSH and local user accounts from lab-00 by adding the AAA framework on top. AAA (Authentication, Authorization, Accounting) replaces the ad-hoc `login local` line commands with a structured, policy-driven model. Understanding AAA is essential not just for the exam but for every enterprise device management scenario — it is the foundational mechanism behind TACACS+ and RADIUS.

### The AAA Framework

AAA stands for three independent security functions:

- **Authentication** — Verifies identity: who are you?
- **Authorization** — Enforces policy: what can you do?
- **Accounting** — Creates an audit trail: what did you do?

On Cisco IOS, the command `aaa new-model` activates the global AAA infrastructure. This is a global switch — once enabled, it affects every line on the device.

**The critical behavioral change:** Before `aaa new-model`, each line handles its own authentication (e.g., `login local`). After `aaa new-model`, AAA takes over all lines. Any line without an explicitly applied named method list falls back to the `default` list. If no `default` list is defined, the console and VTY lines may lock you out entirely.

Safe AAA enablement pattern — always define a safe default list simultaneously:

```
aaa new-model
!
aaa authentication login default local
```

Defining the `default` list before or with `aaa new-model` ensures the console and any unconfigured VTY lines continue to accept local credentials while you configure named lists for specific lines.

### Authentication Method Lists

A method list is an ordered sequence of authentication methods. IOS tries each method in order; it falls back to the next only when the current method is **unreachable** (e.g., a RADIUS server is down), not when credentials are rejected. Rejected credentials terminate authentication immediately — there is no fallback for a bad password.

| Method Keyword | Description |
|----------------|-------------|
| `local` | Local `username` database on the device |
| `local-case` | Same as `local` but case-sensitive usernames |
| `enable` | Enable secret as the password (no username prompt) |
| `none` | No authentication — any user gets in (dangerous) |
| `group tacacs+` | External TACACS+ server group |
| `group radius` | External RADIUS server group |
| `line` | Line password (the `password` command on the line) |

**Two categories of lists:**

- **Default list** (`default`): Applies to all lines that do not have an explicit named list applied.
- **Named list**: Created with any name (e.g., `SSH_AUTH`). Must be explicitly applied to a line with `login authentication <list-name>`. Unused if no line references it.

```
! Default list — covers console and any line without an explicit list
aaa authentication login default local

! Named list — used only by lines that reference it
aaa authentication login SSH_AUTH local

! Apply the named list to VTY lines
line vty 0 4
 login authentication SSH_AUTH
```

### Authorization

Authorization runs after authentication. It determines what an authenticated user is allowed to do.

**Exec authorization** controls whether the user receives an interactive EXEC shell. If exec authorization fails (e.g., the local database has no privilege assigned), the session is disconnected immediately after authentication. With `local` as the method, IOS reads the `privilege N` field from the matching `username` entry and starts the session at that privilege level.

**Command authorization** controls which commands can be executed at a given privilege level. With `local`, the privilege level field in the `username` entry determines what is allowed. With an external server like TACACS+, a per-command authorization request is sent for every command.

```
! Exec authorization — check local DB for privilege level
aaa authorization exec default local

! Command authorization for privilege-7 users
aaa authorization commands 7 default local
```

> **AAA exec authorization and privilege levels:** When `aaa authorization exec default local` is configured, IOS checks the `privilege` value of the authenticated username. If `username operator privilege 7` is defined, the operator gets a level-7 EXEC shell. Without exec authorization, all users start at level 1 (user EXEC) regardless of the `username privilege` setting.

### Accounting

Accounting records what authenticated users do. Records are sent to a configured accounting target (local database, TACACS+ server, or RADIUS server).

| Record Type | When Sent | Use |
|-------------|-----------|-----|
| `start-stop` | At session start AND at session end | Full audit trail with duration |
| `stop-only` | At session end only | Lighter load; less real-time visibility |
| `none` | Never | Disables accounting |

```
! Record exec session start and stop in the local database
aaa accounting exec default start-stop local
```

Local accounting stores records in memory (visible with `show aaa local user lockout` and debug). In production, accounting data flows to a TACACS+ or RADIUS server where it is stored permanently.

### TACACS+ vs RADIUS

Both protocols carry AAA data between the NAS (Network Access Server — the router or switch) and an external authentication server. The ENCOR exam tests you on their differences.

| Feature | TACACS+ | RADIUS |
|---------|---------|--------|
| Transport | TCP port 49 | UDP port 1812 (auth) / 1813 (acct) |
| Packet encryption | Full packet | Password field only |
| Command authorization | Yes — per-command | No — only session-level |
| Protocol origin | Cisco-developed | IETF standard (RFC 2865/2866) |
| Separation of AAA | Authentication, authorization, and accounting are separate | Authentication and authorization combined |
| Typical use case | Network device administration | User network access (Wi-Fi, VPN, 802.1X) |
| Attribute support | Proprietary Cisco AVPairs | Standard + vendor-specific attributes (VSAs) |

**Memory hook:** TACACS+ is for **device administration** (full encryption, per-command authorization). RADIUS is for **user access** (IETF standard, UDP, no per-command granularity).

> **Exam tip:** TACACS+ uses TCP — if the server is unreachable, the TCP connection fails and IOS falls back to the next method in the list. RADIUS uses UDP — IOS must wait for a timeout before declaring the server unreachable and falling back. This makes TACACS+ fail-over faster in a properly configured dual-server environment.

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| AAA new-model | Enable the global AAA framework; understand the line override behavior |
| Default method list | Create a safe fallback list to prevent lockout at AAA transition |
| Named method lists | Create and apply scope-limited authentication lists to VTY lines |
| Exec authorization | Enforce privilege-level assignment from the local database at login |
| Command authorization | Control which commands privilege-7 users can execute |
| AAA accounting | Record exec session start/stop events to the local accounting store |
| TACACS+ vs RADIUS | Identify protocol differences for exam AAA scenarios |

---

## 2. Topology & Scenario

**Scenario:** Meridian Financial has completed Phase 1 device hardening — local users with privilege levels, SSH, and session timeouts are in place on all devices. The security team now wants to formalize the authentication framework. The current `login local` configuration works, but it is not extensible: there is no audit trail, no ability to scope authentication methods per line type, and no framework to later bolt on a TACACS+ server without reconfiguring every line. Your task: enable AAA new-model on R1, create explicit authentication lists, scope the named list to VTY lines, configure authorization so privilege levels are enforced at login, and add accounting so session activity is tracked.

```
                    ┌────────────────────────────────┐
                    │              R1                │
                    │   (Primary Security Target)    │
                    │     Lo0: 1.1.1.1/32           │
                    └─────┬──────────────┬───────────┘
               Gi0/0      │              │      Gi0/1
          10.1.12.1/30    │              │  10.1.13.1/30
          2001:db8:12::1  │              │  2001:db8:13::1
                          │              │
          10.1.12.2/30    │              │  10.1.13.2/30
          2001:db8:12::2  │              │  2001:db8:13::2
               Gi0/0      │              │      Gi0/0
       ┌───────────────────┘              └────────────────────┐
       │                                                       │
┌──────┴──────────────────┐         ┌────────────────────────┴──┐
│          R2             │         │           R3               │
│   (Management Station)  │         │   (External/Untrusted)     │
│    Lo0: 2.2.2.2/32     │         │    Lo0: 3.3.3.3/32        │
└──────┬──────────────────┘         └──────────────────────┬────┘
  Gi0/1│ 10.1.23.1/30                          10.1.23.2/30│Gi0/1
  2001:db8:23::1│                        2001:db8:23::2│
       └────────────────────────────────────────────────────┘
                              10.1.23.0/30

    R1: Gi0/2                                    R2: Gi0/2
  192.168.10.1/24                            192.168.20.1/24
  SW1: Gi0/1                                  SW1: Gi0/2
         │                                         │
         └──────────────────┬──────────────────────┘
                            │
               ┌────────────┴────────────────────┐
               │            SW1                  │
               │       (Access Switch)           │
               │  VLAN 10 | VLAN 20 | VLAN 99    │
               │  Mgmt: 192.168.99.11/24         │
               └─────┬─────────────────┬─────────┘
               Gi0/3 │                 │ Gi1/0
                     │                 │
              ┌──────┘                 └──────┐
              │                               │
       ┌──────┴──────┐               ┌────────┴──────┐
       │    PC1      │               │     PC2       │
       │  (VLAN 10)  │               │  (VLAN 20)    │
       │192.168.10.10│               │192.168.20.10  │
       └─────────────┘               └───────────────┘
```

> **IPv6 note:** IPv6 addresses have been silently added to all router interfaces in this lab's base configuration. They are pre-configured and do not require student action. They are available for ACL testing in lab-02.

**Device roles:**
- **R1** — Primary hardening target. All AAA configuration is applied here.
- **R2** — Management station. Used to test SSH authentication to R1 after AAA configuration.
- **R3** — Simulates an external/untrusted peer. SSH from R3 tests authentication rejection.
- **SW1** — Access layer switch. AAA is not configured on SW1 in this lab; it retains `login local`.
- **PC1/PC2** — End hosts used as reachability sources in later labs.

---

## 3. Hardware & Environment Specifications

| Device | Platform | RAM | Role |
|--------|----------|-----|------|
| R1 | IOSv (15.9) | 512 MB | Primary AAA target |
| R2 | IOSv (15.9) | 512 MB | Management station / SSH test source |
| R3 | IOSv (15.9) | 512 MB | External/untrusted peer |
| SW1 | IOSvL2 (15.2) | 512 MB | Access switch (no AAA this lab) |
| PC1 | VPCS | — | Trusted user (VLAN 10) |
| PC2 | VPCS | — | Untrusted host (VLAN 20) |

**Cabling:**

| Link | Source | Destination | Subnet |
|------|--------|-------------|--------|
| L1 | R1 Gi0/0 | R2 Gi0/0 | 10.1.12.0/30 |
| L2 | R1 Gi0/1 | R3 Gi0/0 | 10.1.13.0/30 |
| L3 | R2 Gi0/1 | R3 Gi0/1 | 10.1.23.0/30 |
| L4 | R1 Gi0/2 | SW1 Gi0/1 | VLAN 10 — 192.168.10.0/24 |
| L5 | R2 Gi0/2 | SW1 Gi0/2 | VLAN 20 — 192.168.20.0/24 |
| L6 | PC1 | SW1 Gi0/3 | VLAN 10 |
| L7 | PC2 | SW1 Gi1/0 | VLAN 20 |

**Console Access Table:**

| Device | Port | Connection Command |
|--------|------|--------------------|
| R1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R3 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| SW1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| PC1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| PC2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |

---

## 4. Base Configuration

The following is **pre-loaded** via `setup_lab.py` (which pushes the lab-00 solutions):

- IP addressing on all router and switch interfaces
- IPv6 addressing on all router interfaces (silently pre-configured)
- OSPF process 1 in area 0 on R1, R2, and R3
- Local users: admin (privilege 15) and operator (privilege 7)
- Custom privilege level assignments (show ip interface brief, show interfaces, show ip route, ping, traceroute at level 7)
- SSH version 2 with timeout, retries, and source-interface configured on all routers and SW1
- Console and VTY line hardening (login local, exec-timeout, logging synchronous)
- VTY transport input ssh

**NOT pre-configured:**

- AAA framework
- Authentication method lists (default or named)
- Named method list applied to VTY lines
- Exec authorization
- Command authorization for privilege level 7
- AAA accounting

---

## 5. Lab Challenge: Core Implementation

### Task 1: Enable the AAA Framework

- Enable the global AAA framework on R1.
- At the same time, define the default authentication list to use the local user database — this prevents lockout on the console and any unconfigured lines after AAA takes over.

**Verification:** `show running-config | include aaa` must show `aaa new-model` and `aaa authentication login default local` both present.

---

### Task 2: Configure a Named Authentication Method List

- Create a named authentication list called **SSH_AUTH** on R1 that uses the local user database as its sole authentication method.

**Verification:** `show aaa method-lists authentication` must show an entry named `SSH_AUTH` with `LOCAL` as the method.

---

### Task 3: Apply Named Authentication to VTY Lines

- On R1, configure all VTY lines to use the **SSH_AUTH** method list instead of the default list.

**Verification:** SSH from R2 to R1 using the admin credentials must succeed and land at privilege level 15. SSH using the operator credentials must succeed and land at privilege level 7. SSH with incorrect credentials must be rejected after the configured number of retries.

---

### Task 4: Configure Exec and Command Authorization

- Enable exec authorization on R1 using the local database. This enforces that privilege levels defined in the `username` entries are applied at login.
- Enable command authorization for privilege level 7 operations using the local database. This ensures the operator's restricted command set is enforced by AAA, not just by the privilege-level assignment.

**Verification:** `show aaa method-lists authorization` must show both the exec and commands (level 7) entries with LOCAL as the method.

---

### Task 5: Configure AAA Accounting

- Enable exec session accounting on R1 using start-stop records stored in the local accounting database.

**Verification:** `show aaa accounting` must show the exec accounting configuration as active with start-stop records and the local method.

---

### Task 6: Verify End-to-End AAA Behavior

- SSH from R2 to R1 as the admin user. Confirm the session opens at privilege level 15 with all commands available.
- SSH from R2 to R1 as the operator user. Confirm the session opens at privilege level 7 with only the five authorized commands visible.
- Attempt SSH from R2 to R1 with a nonexistent username or wrong password. Confirm the authentication is rejected.

**Verification:** On R1, `show aaa sessions` and `show users` must reflect the active or recently completed sessions. The console `debug aaa authentication` can be used to observe authentication events (use `undebug all` to stop).

---

## 6. Verification & Analysis

### Task 1 — AAA Framework Enabled

```
R1# show running-config | include aaa
aaa new-model                              ! ← global AAA active
aaa authentication login default local    ! ← default list protects console
aaa authentication login SSH_AUTH local   ! ← named list for VTY (added in Task 2)
aaa authorization exec default local      ! ← exec auth (added in Task 4)
aaa authorization commands 7 default local  ! ← cmd auth level 7 (added in Task 4)
aaa accounting exec default start-stop local  ! ← accounting (added in Task 5)
```

### Task 2 — Named Method List

```
R1# show aaa method-lists authentication
authen queue=AAA_ML_AUTHEN_Q
  name=default valid=TRUE id=0
    Method list details:
    type=LOGIN
    flag=NONE
    methods=LOCAL                          ! ← default list uses local DB
  name=SSH_AUTH valid=TRUE id=1
    Method list details:
    type=LOGIN
    flag=NONE
    methods=LOCAL                          ! ← SSH_AUTH list uses local DB
```

### Task 3 — Named List Applied to VTY

```
R1# show running-config | section line vty
line vty 0 4
 login authentication SSH_AUTH            ! ← SSH_AUTH list applied here
 transport input ssh
 exec-timeout 5 0
```

SSH test from R2:
```
R2# ssh -l admin 1.1.1.1
Password:
R1#                                        ! ← privilege 15 (# prompt)

R2# ssh -l operator 1.1.1.1
Password:
R1#                                        ! ← privilege 7 (# prompt, custom level)

R2# ssh -l baduser 1.1.1.1
Password:
% Authentication failed.                   ! ← rejected after 3 retries
```

### Task 4 — Authorization

```
R1# show aaa method-lists authorization
author queue=AAA_ML_AUTHOR_Q
  name=default valid=TRUE id=0
    type=EXEC
    flag=NONE
    methods=LOCAL                          ! ← exec auth: privilege from username DB
  name=default valid=TRUE id=0
    type=COMMANDS level=7
    flag=NONE
    methods=LOCAL                          ! ← level-7 cmd auth: local enforcement
```

Operator session — only authorized commands visible:
```
R1> ?
  ping        Send echo messages             ! ← level-7 authorized
  show        Show running system information  ! ← level-7 authorized
  traceroute  Trace route to destination       ! ← level-7 authorized
  exit        Exit from the EXEC
  logout      Exit from the EXEC
```

### Task 5 — Accounting

```
R1# show aaa accounting
    Accounting method list name       : default
    Record type                       : start-stop     ! ← start and stop records
    Method                            : LOCAL          ! ← local accounting store
    Accounting type                   : EXEC
```

### Task 6 — End-to-End Behavior

```
R1# show users
    Line       User       Host(s)              Idle       Location
*  0 con 0                idle                 00:00:00
   2 vty 0     admin      10.1.12.2            00:00:08   ! ← admin session active
   3 vty 1     operator   10.1.12.2            00:00:05   ! ← operator session active
```

---

## 7. Verification Cheatsheet

### AAA Global Configuration

```
aaa new-model
!
aaa authentication login default <method1> [<method2>]
aaa authentication login <list-name> <method1> [<method2>]
!
aaa authorization exec default <method>
aaa authorization commands <level> default <method>
!
aaa accounting exec default start-stop <method>
```

| Command | Purpose |
|---------|---------|
| `aaa new-model` | Enable AAA — overrides all line-level login commands |
| `aaa authentication login default local` | Safe default: console uses local DB |
| `aaa authentication login SSH_AUTH local` | Named list for VTY lines |
| `aaa authorization exec default local` | Enforce privilege level from username DB |
| `aaa authorization commands 7 default local` | Restrict level-7 commands via AAA |
| `aaa accounting exec default start-stop local` | Record session open/close in local DB |

> **Exam tip:** Method list fallback occurs only when a method is *unreachable*, not when it *rejects* credentials. If RADIUS times out, IOS tries the next method. If RADIUS rejects the password, authentication fails immediately.

### Method List Application

```
line vty 0 4
 login authentication <list-name>
```

| Command | Purpose |
|---------|---------|
| `login authentication SSH_AUTH` | Apply named list to the line — overrides `default` |
| `no login authentication` | Revert to the `default` list |

> **Exam tip:** Lines without an explicit `login authentication` command use the `default` list. If there is no `default` list, the line may lock out. Always define a `default` list before enabling `aaa new-model`.

### Verification Commands

| Command | What to Look For |
|---------|-----------------|
| `show aaa method-lists authentication` | All defined lists and their methods |
| `show aaa method-lists authorization` | Exec and command authorization lists |
| `show aaa accounting` | Accounting configuration and record type |
| `show aaa sessions` | Active AAA sessions |
| `show users` | Currently connected users and their lines |
| `show running-config \| section aaa` | Full AAA config block |
| `show running-config \| section line vty` | Method list applied to VTY |
| `debug aaa authentication` | Real-time authentication events (stop with `undebug all`) |
| `debug aaa authorization` | Real-time authorization events |

### Common AAA Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| SSH rejected with correct credentials | VTY applies `SSH_AUTH` but the list was deleted or not created |
| Console locked out after `aaa new-model` | No `default` method list defined |
| Operator gets privilege 15 instead of 7 | `aaa authorization exec` not configured — no privilege enforcement |
| "% Authorization failed" at login | Exec authorization configured but `username` has no privilege field |
| Prompt shows `enable` password instead of username | Method list uses `enable` instead of `local` |
| Authentication loops — keeps asking for password | Method uses `none` on a line with `login authentication` set |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Task 1 & 2: AAA Framework and Method Lists

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1
aaa new-model
!
aaa authentication login default local
aaa authentication login SSH_AUTH local
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show running-config | include aaa
show aaa method-lists authentication
```
</details>

---

### Task 3: Apply Named Authentication to VTY Lines

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1
line vty 0 4
 login authentication SSH_AUTH
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show running-config | section line vty
! From R2:
ssh -l admin 1.1.1.1
ssh -l operator 1.1.1.1
```
</details>

---

### Task 4: Exec and Command Authorization

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1
aaa authorization exec default local
aaa authorization commands 7 default local
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show aaa method-lists authorization
! Log in as operator and run ? — only 5 commands visible
```
</details>

---

### Task 5: AAA Accounting

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1
aaa accounting exec default start-stop local
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show aaa accounting
```
</details>

---

### Task 6: Full Verified Solution

<details>
<summary>Click to view complete R1 AAA configuration</summary>

```bash
! R1 — complete AAA section (added on top of lab-00 solutions)
aaa new-model
!
aaa authentication login default local
aaa authentication login SSH_AUTH local
!
aaa authorization exec default local
aaa authorization commands 7 default local
!
aaa accounting exec default start-stop local
!
line vty 0 4
 login authentication SSH_AUTH
 transport input ssh
 exec-timeout 5 0
```
</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. Inject the fault first, then diagnose and fix using only show commands and test logins.

### Workflow

```bash
python3 setup_lab.py --host <eve-ng-ip>                          # reset to known-good
python3 scripts/fault-injection/apply_solution.py --host <ip>   # push full solution
python3 scripts/fault-injection/inject_scenario_01.py --host <ip>  # Ticket 1
python3 scripts/fault-injection/apply_solution.py --host <ip>   # restore between tickets
```

---

### Ticket 1 — R1 Rejects SSH Logins Despite Correct Credentials

The network operations team reports that all SSH sessions to R1 are failing with "Authentication failed" even for the admin account. The console is unaffected. The issue started after a junior engineer made changes to R1 this morning.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>`

**Success criteria:** SSH from R2 to R1 succeeds with admin and operator credentials.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. SSH from R2 to R1 — confirm "Authentication failed" behavior.
2. Console into R1.
3. `show running-config | include aaa authentication` — look for `SSH_AUTH` method list.
4. `show running-config | section line vty` — confirm VTY uses `login authentication SSH_AUTH`.
5. `show aaa method-lists authentication` — check whether `SSH_AUTH` appears.
6. Root cause: VTY line references `SSH_AUTH`, but the method list no longer exists. When a referenced method list is missing, IOS rejects all authentication on that line.
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! R1
aaa authentication login SSH_AUTH local
```

Verify: SSH from R2 to R1 with admin credentials → succeeds.
</details>

---

### Ticket 2 — R1 Console Accepts Any Login Without Checking Credentials

A security audit found that the console port on R1 is not enforcing password authentication — anyone who connects to the console gets immediate access. The VTY lines are unaffected.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py --host <eve-ng-ip>`

**Success criteria:** The console requires valid admin or operator credentials to access R1.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. Connect to R1 via console — confirm no password prompt appears.
2. `show running-config | include aaa authentication login default` — look for the method used by the default list.
3. Root cause: `aaa authentication login default none` means no authentication is required. Any user who connects is admitted without a password. The default list applies to the console since no named list is applied to `line console 0`.
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! R1
aaa authentication login default local
```

Verify: Connect to console — a Username/Password prompt appears. Invalid credentials are rejected.
</details>

---

### Ticket 3 — R1 VTY Prompts for a Single Password Instead of Username and Password

Users report that SSH to R1 prompts only for a password — there is no username prompt. Entering the admin password does not work. The console is unaffected.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py --host <eve-ng-ip>`

**Success criteria:** SSH to R1 prompts for username and password; admin and operator credentials work correctly.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. SSH from R2 to R1 — observe a bare `Password:` prompt (no `Username:` prompt).
2. Console into R1.
3. `show running-config | include aaa authentication login SSH_AUTH` — check the method.
4. Root cause: `aaa authentication login SSH_AUTH enable` uses the enable secret as the password. SSH clients do send a username, but the `enable` method ignores it and prompts for the enable secret only. The admin/operator passwords are not checked because the method is `enable`, not `local`.
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! R1
no aaa authentication login SSH_AUTH enable
aaa authentication login SSH_AUTH local
```

Verify: SSH from R2 prompts for username and password; admin and operator accounts work.
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] `aaa new-model` is active on R1
- [ ] `aaa authentication login default local` is defined (console protected)
- [ ] `aaa authentication login SSH_AUTH local` is defined
- [ ] VTY lines 0–4 use `login authentication SSH_AUTH`
- [ ] `aaa authorization exec default local` is configured
- [ ] `aaa authorization commands 7 default local` is configured
- [ ] `aaa accounting exec default start-stop local` is configured
- [ ] SSH from R2 to R1 as admin → privilege 15 shell
- [ ] SSH from R2 to R1 as operator → privilege 7 shell with limited commands
- [ ] SSH with invalid credentials → rejected

### Troubleshooting

- [ ] Ticket 1: Diagnosed missing SSH_AUTH method list; restored `aaa authentication login SSH_AUTH local`
- [ ] Ticket 2: Diagnosed `default none` bypass; restored `aaa authentication login default local`
- [ ] Ticket 3: Diagnosed `SSH_AUTH enable` method; restored `aaa authentication login SSH_AUTH local`
