# Lab 00 — Lines, Local Users, and SSH Hardening

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

**Exam Objective:** 5.1 — Describe network programmability concepts; 5.1.a — Infrastructure security: device access hardening (lines, local users, SSH)

This lab covers the first layer of Cisco device security: controlling who can connect, how they authenticate, and what they can do once authenticated. You will configure local user accounts with distinct privilege levels, lock down VTY lines to SSH-only, and generate RSA keys to enable SSHv2. These concepts form the mandatory foundation before any higher-layer security (AAA, ACLs, CoPP) can be built on top.

### Line Types and Their Role

Every IOS device has three categories of access lines:

- **Console (con 0):** Direct physical access via the RJ-45 or USB console port. Used for initial setup and emergency recovery. Independent of the network stack — works even when routing is broken.
- **Aux (aux 0):** Auxiliary port for dial-up modem access. Present on most routers but rarely used today. Disable it as a hardening step on production devices.
- **VTY (vty 0 4):** Virtual terminal lines for remote access over TCP/IP. This is how engineers SSH or Telnet to the device. IOS allocates VTY lines 0–4 (5 sessions) by default; some platforms support 0–15.

Line configuration controls authentication method, idle timeout, and allowed transport protocols:

```
line console 0
 login local           ! authenticate against local user database
 exec-timeout 10 0     ! disconnect after 10 minutes idle
 logging synchronous   ! prevent syslog messages from mangling input

line vty 0 4
 login local
 transport input ssh   ! SSH only — Telnet is rejected
 exec-timeout 5 0      ! VTY sessions time out faster
```

### Local Users and Privilege Levels

IOS assigns each user a privilege level at login. The level determines which EXEC commands are visible and executable:

| Level | Name | Default Access |
|-------|------|----------------|
| 0 | Least | `enable`, `disable`, `exit`, `help`, `logout` only |
| 1 | User EXEC | `ping`, `traceroute`, `show version`, basic show commands |
| 15 | Privileged EXEC | Full access — all commands including `configure terminal` |
| 2–14 | Custom | Defined by `privilege exec level N <command>` |

The `username` command assigns a privilege level at login:

```
username admin privilege 15 secret StrongPass!2026
username operator privilege 7 secret OpPass!2026
```

The `secret` keyword stores the password as a Type 5 (MD5) hash. Always prefer `secret` over `password` — `password` stores cleartext or a reversible Type 7 cipher.

### Custom Privilege Levels

To give an operator read-only access without exposing sensitive commands, assign specific show commands to level 7:

```
privilege exec level 7 show ip interface brief
privilege exec level 7 show interfaces
privilege exec level 7 show ip route
privilege exec level 7 ping
privilege exec level 7 traceroute
```

**Critical design decision:** Do not assign `show running-config` to the operator level. The running-config contains password hashes — even Type 5 hashes can be brute-forced offline. Operators do not need to see cryptographic credentials.

### SSH Version 2 and RSA Key Generation

SSH replaces Telnet by encrypting the session. IOS supports both SSHv1 (deprecated, vulnerable) and SSHv2. Prerequisites for SSHv2:

1. A hostname other than the default (`Router`)
2. A domain name — required for RSA key generation
3. An RSA key pair of at least 768 bits (2048 recommended)
4. `ip ssh version 2`

**Key generation order matters:**

```
! Step 1 — configure domain name (required for key generation)
ip domain-name encor-lab.local

! Step 2 — generate RSA keys IN EXEC MODE (not config mode)
R1# crypto key generate rsa modulus 2048

! Step 3 — enable SSHv2 (requires keys to exist)
ip ssh version 2
ip ssh time-out 60
ip ssh authentication-retries 3
ip ssh source-interface Loopback0
```

Attempting `ip ssh version 2` before generating keys is silently accepted but SSH will not function. Always generate keys first.

The `source-interface` setting forces SSH connections to originate from (and arrive on) a stable loopback address, making the connection predictable and firewall-filterable.

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| Line hardening | Configure console and VTY authentication, timeouts, and transport restrictions |
| Local user accounts | Create named users with privilege levels 15 and 7 using Type 5 secrets |
| Custom privilege levels | Assign specific EXEC commands to non-standard privilege levels |
| SSHv2 enablement | Generate RSA keys, enable version 2, configure timeout and retry parameters |
| SSH source interface | Bind SSH to a stable loopback to control session origin |
| Switch access hardening | Apply the same access controls to an IOSvL2 switch |

---

## 2. Topology & Scenario

**Scenario:** Meridian Financial has deployed three routers and an access switch in a new branch. No device hardening has been done — VTY lines accept Telnet with a shared password, there are no individual user accounts, and there is no audit trail. The security team has issued a hardening order before the branch goes live. Your task: configure local users, replace Telnet with SSHv2, set appropriate idle timeouts, and define a custom operator role with limited command access.

```
                    ┌────────────────────────────────┐
                    │              R1                │
                    │   (Primary Security Target)    │
                    │     Lo0: 1.1.1.1/32           │
                    └─────┬──────────────┬───────────┘
               Gi0/0      │              │      Gi0/1
          10.1.12.1/30    │              │  10.1.13.1/30
                          │              │
          10.1.12.2/30    │              │  10.1.13.2/30
               Gi0/0      │              │      Gi0/0
       ┌───────────────────┘              └────────────────────┐
       │                                                       │
┌──────┴──────────────────┐         ┌────────────────────────┴──┐
│          R2             │         │           R3               │
│   (Management Station)  │         │   (External/Untrusted)     │
│    Lo0: 2.2.2.2/32     │         │    Lo0: 3.3.3.3/32        │
└──────┬──────────────────┘         └──────────────────────┬────┘
  Gi0/1│ 10.1.23.1/30                          10.1.23.2/30│Gi0/1
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

**Device roles:**
- **R1** — Primary hardening target. All device access, line, and SSH configuration is applied here first.
- **R2** — Management station. Used to test SSH reachability to R1 after configuration.
- **R3** — Simulates an external/untrusted peer. SSH and Telnet attempts from R3 should be controlled.
- **SW1** — Access layer switch. Receives the same local user and line hardening as the routers. Its management VLAN 99 (192.168.99.11/24) has no upstream gateway — SW1 is console-managed for this lab.
- **PC1/PC2** — End hosts used as reachability test sources in later labs.

> **SW1 management note:** No router in this topology has an interface in the 192.168.99.0/24 subnet. SW1's VLAN 99 SVI is reachable by SSH only from a device directly in that subnet. For this lab, manage SW1 exclusively via the console port. SSH becomes reachable after the ACL lab adds routing context.

---

## 3. Hardware & Environment Specifications

| Device | Platform | RAM | Role |
|--------|----------|-----|------|
| R1 | IOSv (15.9) | 512 MB | Primary hardening target |
| R2 | IOSv (15.9) | 512 MB | Management station / SSH test source |
| R3 | IOSv (15.9) | 512 MB | External/untrusted peer |
| SW1 | IOSvL2 (15.2) | 512 MB | Access switch |
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

The following is **pre-loaded** via `setup_lab.py`. Students do not configure this:

- IP addressing on all router and switch interfaces
- OSPF process 1 in area 0 on R1, R2, and R3 (R1 and R2 have Gi0/2 passive)
- VLAN 10 (TRUSTED), VLAN 20 (UNTRUSTED), and VLAN 99 (MGMT) on SW1
- Switch access port assignments
- SW1 VLAN 99 SVI (192.168.99.11/24)
- VPCS addressing on PC1 and PC2

**NOT pre-configured:**

- Local user accounts
- Domain name
- RSA key pair
- SSH version or settings
- Console and VTY authentication
- Idle session timeouts
- Custom privilege level assignments

---

## 5. Lab Challenge: Core Implementation

> Configure complete device access hardening on R1, R2, R3, and SW1. IP addressing and OSPF routing are pre-configured; focus entirely on access security.

---

### Task 1: Create Local User Accounts

- Create a full-privilege administrator account named `admin` with privilege level 15 and secret `Encor-Admin-2026`.
- Create a restricted operator account named `operator` with privilege level 7 and secret `Encor-Oper-2026`.
- Use the most secure password storage method available (Type 5 hash).
- Apply the same accounts to R1, R2, R3, and SW1.

**Verification:** `show running-config | section username` — both users must appear with `secret` (not `password`). Confirm `admin` shows privilege 15 and `operator` shows privilege 7.

---

### Task 2: Define a Custom Operator Command Set

- Assign five read-only commands to privilege level 7 on R1: checking interface address status, viewing detailed interface counters, reading the routing table, running ping, and running traceroute.
- Do not include configuration display commands that expose password hashes.

**Verification:** Log in as `operator`. Confirm `show ip interface brief`, `show interfaces`, `show ip route`, `ping`, and `traceroute` succeed. Confirm `show running-config` is rejected with `% Invalid input detected`.

---

### Task 3: Harden the Console Line

- Configure the console line on R1 (and all devices) to authenticate against the local user database.
- Set an idle timeout of 10 minutes with zero seconds.
- Enable logging synchronous to prevent syslog messages from interrupting command input.

**Verification:** `show line con 0` — confirm `Login` shows `local` and `Idle EXEC` shows `00:10:00`.

---

### Task 4: Restrict VTY Lines to SSH-Only

- Configure VTY lines 0 through 4 on R1 (and all devices) to accept SSH connections only.
- Authenticate VTY sessions against the local user database.
- Set VTY idle timeout to 5 minutes.

**Verification:** From R2, attempt to Telnet to R1's loopback (1.1.1.1). Connection must be refused. This confirms Telnet is blocked.

---

### Task 5: Generate RSA Keys and Enable SSHv2

- Set the IP domain name to `encor-lab.local` on all devices.
- Generate a 2048-bit RSA key pair. **This command runs in privileged EXEC mode, not configuration mode.**
- Enable SSH version 2.
- Set the SSH negotiation timeout to 60 seconds and maximum authentication retries to 3.
- Bind SSH to the Loopback0 interface as the source.

**Verification:** `show ip ssh` — confirm `SSH Enabled - version 2.0`, `Authentication timeout: 60 secs`, `Authentication retries: 3`. From R2, SSH to R1's loopback as `admin` and verify login succeeds.

---

### Task 6: Harden SW1

- Apply the same local users, custom privilege level assignments, console/VTY hardening, and SSH settings to SW1.
- SW1 has no loopback interface — use `Vlan99` as the SSH source interface.
- Do not configure a default gateway on SW1 (no router has a 192.168.99.0/24 interface in this lab).

**Verification:** `show ip ssh` and `show running-config | section line` on SW1 confirm the same hardening as the routers. Note that SSH into SW1 will not succeed from R1 or R2 because VLAN 99 is isolated — this is expected.

---

## 6. Verification & Analysis

### Task 1 & 2 — User Accounts and Privilege Levels

```
R1# show running-config | section username
username admin privilege 15 secret 5 $1$...   ! ← Type 5 hash — not cleartext
username operator privilege 7 secret 5 $1$... ! ← privilege 7, not 15

R1# show privilege
Current privilege level is 15                  ! ← while logged in as admin

! Login as operator and check:
R1# show privilege
Current privilege level is 7                   ! ← privilege level confirmed

R1# show running-config
% Invalid input detected at '^' marker.        ! ← show running-config blocked at level 7
```

### Task 3 — Console Line

```
R1# show line con 0
   Tty Line Speed  Timeout  User  Host(s)  Idle    Location
*     0    0   9600 00:10:00 admin          00:00:14
                   Capabilities: none
    Modem state: Ready
    Special Chars: Escape  Hold  Stop  Start  Disconnect  Activation
                    ^^X     none   -     -       none
    Stopbits: 1
    Databits: 8
    Parity: none
    Autobaud: no
    Line is not activated
    Transport input: none
    Transport output: pad telnet rlogin udptn v120 ssh
    Login: local                               ! ← must show "local"
    Idle EXEC timeout: 00:10:00                ! ← 10 min 0 sec
    Modem type is Unknown.
    Session limit is not set.
    Time since activation: never
    Editing is enabled.
    History is enabled, history size is 20.
    DNS resolution in show commands is enabled
    Full user help is disabled
    Allowed input transports are none.
    Allowed output transports are pad telnet rlogin udptn v120 ssh.
    No output characters are padded
    No special data dispatching characters
```

### Task 4 — VTY Transport Restriction

```
! From R2 — Telnet must be rejected
R2# telnet 1.1.1.1
Trying 1.1.1.1 ...
% Connection refused by remote host        ! ← transport input ssh blocks Telnet

! From R2 — SSH must succeed
R2# ssh -l admin 1.1.1.1
Password:
R1>enable
R1#                                        ! ← SSH login with admin succeeds
```

### Task 5 — SSHv2 Status

```
R1# show ip ssh
SSH Enabled - version 2.0                  ! ← version 2 confirmed
Authentication timeout: 60 secs            ! ← matches ip ssh time-out 60
Authentication retries: 3                  ! ← matches ip ssh authentication-retries 3
Minimum expected Diffie Hellman key size : 1024 bits
IOS Keys in SECSH format(ssh-rsa, base64 encoded):
ssh-rsa AAAAB3NzaC1yc2EAAA...             ! ← RSA key present (confirms keygen ran)

R1# show crypto key mypubkey rsa
% Key pair was generated at: ...
Key name: R1.encor-lab.local               ! ← hostname.domainname format
 Usage: General Purpose Key
 Key is not exportable.
 Key Data:
  ...
 Key size (bits): 2048                     ! ← confirms 2048-bit modulus
```

### Task 5 — OSPF Still Functional After Hardening

```
R1# show ip ospf neighbor
Neighbor ID     Pri   State           Dead Time   Address         Interface
2.2.2.2           1   FULL/DR         00:00:39    10.1.12.2       GigabitEthernet0/0
3.3.3.3           1   FULL/BDR        00:00:32    10.1.13.2       GigabitEthernet0/1
! ← both neighbors FULL — line hardening has no effect on OSPF
```

---

## 7. Verification Cheatsheet

### Local User and Privilege Configuration

```
username <name> privilege <0-15> secret <password>
privilege exec level <N> <command>
```

| Command | Purpose |
|---------|---------|
| `username admin privilege 15 secret <pw>` | Full-access administrator account |
| `username operator privilege 7 secret <pw>` | Restricted operator at custom level |
| `privilege exec level 7 show ip interface brief` | Make command accessible at level 7+ |
| `show running-config \| section username` | Verify accounts and hash types |
| `show privilege` | Show current session privilege level |

> **Exam tip:** `secret` always wins over `password` if both exist. The `secret` keyword uses Type 5 (MD5) or Type 9 (scrypt on newer IOS-XE). Never use `password` in production.

### Line Hardening

```
line console 0
 login local
 exec-timeout <min> <sec>
 logging synchronous

line vty 0 4
 login local
 transport input ssh
 exec-timeout <min> <sec>
```

| Command | Purpose |
|---------|---------|
| `login local` | Authenticate against `username` database |
| `exec-timeout 10 0` | Disconnect after 10 min idle |
| `logging synchronous` | Prevent syslog from mangling input |
| `transport input ssh` | Block Telnet; SSH only |

> **Exam tip:** `transport input none` disables all remote access. `transport input all` permits both SSH and Telnet. The default (`transport input telnet`) allows only Telnet.

### SSH Configuration

```
ip domain-name <domain>
! In EXEC mode:
crypto key generate rsa modulus 2048
! Back in config mode:
ip ssh version 2
ip ssh time-out <seconds>
ip ssh authentication-retries <count>
ip ssh source-interface <interface>
```

| Command | Purpose |
|---------|---------|
| `ip domain-name encor-lab.local` | Required before key generation |
| `crypto key generate rsa modulus 2048` | Generate 2048-bit RSA pair (EXEC mode) |
| `ip ssh version 2` | Force SSHv2 only |
| `ip ssh time-out 60` | Negotiation timeout in seconds |
| `ip ssh authentication-retries 3` | Max failed attempts before disconnect |
| `ip ssh source-interface Loopback0` | Bind SSH to stable loopback |
| `crypto key zeroize rsa` | Delete RSA keys (SSH stops working) |

> **Exam tip:** The RSA key name is `hostname.domainname`. If you change either after key generation, generate new keys — the old ones remain bound to the old name.

### Verification Commands

| Command | What to Look For |
|---------|-----------------|
| `show ip ssh` | `SSH Enabled - version 2.0`; timeout and retry values |
| `show crypto key mypubkey rsa` | Key name (`hostname.domain`), key size (2048 bits) |
| `show running-config \| section username` | `secret 5` hash (not cleartext password) |
| `show line vty 0 4` | `Login: local`, `Transport input: ssh` |
| `show line con 0` | `Login: local`, `Idle EXEC timeout` |
| `show privilege` | Current session privilege level |
| `show users` | Active console and VTY sessions |
| `telnet <ip>` from remote device | Must show `Connection refused` after hardening |
| `ssh -l <user> <ip>` from remote device | Must succeed with correct credentials |

### Common SSH / Line Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| `SSH not enabled` in `show ip ssh` | No RSA keys — run `crypto key generate rsa` |
| `% No hostname specified` during keygen | Set `hostname` before generating keys |
| `% No domain name specified` during keygen | Set `ip domain-name` before generating keys |
| SSH version 1 shown despite `ip ssh version 2` | Keys generated before `ip ssh version 2` was configured — re-key |
| Telnet still accepted | `transport input all` or `transport input telnet` — change to `transport input ssh` |
| Login fails with correct password | `login` (not `login local`) on VTY — password-based auth, not local user |
| `show running-config` works for operator | `privilege exec level 15` assigned, or user was created at privilege 15 |
| SSH from VLAN 99 to SW1 fails | No gateway for 192.168.99.0/24 — SW1 is console-only in this lab |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge before reading these solutions!

### Task 1 & 2: Users and Custom Privilege Level

<details>
<summary>Click to view R1/R2/R3 Configuration</summary>

```bash
! Apply to R1, R2, and R3
username admin privilege 15 secret Encor-Admin-2026
username operator privilege 7 secret Encor-Oper-2026

privilege exec level 7 show ip interface brief
privilege exec level 7 show interfaces
privilege exec level 7 show ip route
privilege exec level 7 ping
privilege exec level 7 traceroute
```
</details>

### Task 3 & 4: Console and VTY Lines

<details>
<summary>Click to view Line Configuration</summary>

```bash
! Apply to R1, R2, R3, and SW1
line console 0
 login local
 exec-timeout 10 0
 logging synchronous

line vty 0 4
 login local
 transport input ssh
 exec-timeout 5 0
```
</details>

### Task 5: RSA Keys and SSHv2

<details>
<summary>Click to view SSH Configuration</summary>

```bash
! Step 1 — config mode
ip domain-name encor-lab.local

! Step 2 — EXEC mode (exit configure terminal first)
! R1# crypto key generate rsa modulus 2048

! Step 3 — config mode
ip ssh version 2
ip ssh time-out 60
ip ssh authentication-retries 3
ip ssh source-interface Loopback0
```

> **Note:** `crypto key generate rsa modulus 2048` is an EXEC-mode command. Run it at the `R1#` prompt — NOT inside `configure terminal`. Configure `ip domain-name` first or the command will fail.
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show ip ssh
show crypto key mypubkey rsa
show running-config | section username
show line vty 0 4
! From R2:
ssh -l admin 1.1.1.1
telnet 1.1.1.1   ! must be refused
```
</details>

### Task 6: SW1 Hardening

<details>
<summary>Click to view SW1 Configuration</summary>

```bash
ip domain-name encor-lab.local

username admin privilege 15 secret Encor-Admin-2026
username operator privilege 7 secret Encor-Oper-2026

privilege exec level 7 show ip interface brief
privilege exec level 7 show interfaces
privilege exec level 7 show ip route
privilege exec level 7 ping
privilege exec level 7 traceroute

! EXEC mode:
! SW1# crypto key generate rsa modulus 2048

ip ssh version 2
ip ssh time-out 60
ip ssh authentication-retries 3
ip ssh source-interface Vlan99   ! SW1 has no loopback — use management SVI

line console 0
 login local
 exec-timeout 10 0
 logging synchronous

line vty 0 4
 login local
 transport input ssh
 exec-timeout 5 0
```

> **Note:** Do not add `ip default-gateway` to SW1. No router in this topology has an interface in the 192.168.99.0/24 subnet. SW1 is console-only for this lab.
</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. Inject the fault first, then diagnose and fix using only show commands and connectivity tests.

### Workflow

```bash
python3 setup_lab.py                                   # reset to known-good state
python3 scripts/fault-injection/inject_scenario_01.py  # Ticket 1
python3 scripts/fault-injection/apply_solution.py      # restore known-good state
```

---

### Ticket 1 — R2 Cannot Establish an SSH Session to R1

The network team reports that attempts to SSH to R1's loopback from R2 fail immediately. Telnet was confirmed to work before — now SSH is broken.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py`

**Success criteria:** `ssh -l admin 1.1.1.1` from R2 succeeds and reaches R1's EXEC prompt. Telnet to 1.1.1.1 from R2 is still refused.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. From R2, attempt SSH to R1: `ssh -l admin 1.1.1.1` — note the exact error message.
2. On R1, run `show ip ssh` — check if SSH is enabled and what version is shown.
3. On R1, run `show line vty 0 4` — check `Transport input` field.
4. Look for `Transport input: telnet` (not `ssh`) — this is the fault.
5. Confirm: From R2, `telnet 1.1.1.1` succeeds (Telnet is allowed, SSH is blocked).
</details>

<details>
<summary>Click to view Fix</summary>

On R1:
```bash
line vty 0 4
 transport input ssh
```

Verify:
```bash
R1# show line vty 0 4
! Transport input should show: ssh

! From R2:
R2# ssh -l admin 1.1.1.1   ! must succeed
R2# telnet 1.1.1.1          ! must be refused
```
</details>

---

### Ticket 2 — Operator Account Has Unexpected Privileged Access

An operator logged in as `operator` and ran `show running-config`, exposing password hashes. The account should only have read-only access to interface status, routing, ping, and traceroute.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py`

**Success criteria:** User `operator` logs in and `show privilege` returns 7. `show running-config` is rejected. `show ip interface brief` succeeds.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. On R1, run `show running-config | section username` — note the privilege level assigned to `operator`.
2. The `operator` account shows `privilege 15` (should be 7) — this is the fault.
3. Also verify: `show privilege` after logging in as `operator` returns 15 instead of 7.
</details>

<details>
<summary>Click to view Fix</summary>

On R1:
```bash
no username operator
username operator privilege 7 secret Encor-Oper-2026
```

Verify:
```bash
R1# show running-config | section username
! operator must show privilege 7

! Login as operator, then:
R1> show privilege
Current privilege level is 7          ! must be 7, not 15

R1> show running-config
% Invalid input detected ...          ! must be rejected
```
</details>

---

### Ticket 3 — R1 VTY Lines Accept Telnet Connections

A security scan flagged R1 as responding to Telnet on port 23. Policy requires SSH-only access. Telnet should be rejected on all VTY lines.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py`

**Success criteria:** `telnet 1.1.1.1` from R2 is refused. `ssh -l admin 1.1.1.1` still succeeds.

<details>
<summary>Click to view Diagnosis Steps</summary>

1. From R2, attempt `telnet 1.1.1.1` — it connects (should be refused).
2. On R1, `show line vty 0 4` — check `Transport input` field.
3. The field shows `transport input all` (or `transport input telnet`) instead of `ssh` — this is the fault.
</details>

<details>
<summary>Click to view Fix</summary>

On R1:
```bash
line vty 0 4
 transport input ssh
```

Verify:
```bash
! From R2:
R2# telnet 1.1.1.1
% Connection refused by remote host    ! must be refused

R2# ssh -l admin 1.1.1.1
Password:
R1>                                    ! SSH still works
```
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] Local user `admin` created at privilege 15 with Type 5 secret on R1, R2, R3, SW1
- [ ] Local user `operator` created at privilege 7 with Type 5 secret on R1, R2, R3, SW1
- [ ] Five commands assigned to privilege level 7 (no `show running-config` included)
- [ ] Console line uses `login local`, exec-timeout 10 0, logging synchronous — all devices
- [ ] VTY lines 0-4 use `login local`, `transport input ssh`, exec-timeout 5 0 — all devices
- [ ] `ip domain-name encor-lab.local` configured on all devices
- [ ] RSA 2048-bit key generated (via EXEC mode `crypto key generate rsa modulus 2048`)
- [ ] `ip ssh version 2` enabled, timeout 60s, retries 3, source Loopback0 (routers) / Vlan99 (SW1)
- [ ] SSH from R2 to R1 succeeds as `admin`
- [ ] Telnet from R2 to R1 is refused
- [ ] `show privilege` returns 7 when logged in as `operator`
- [ ] `show running-config` rejected for `operator` user
- [ ] OSPF neighbors still FULL after all hardening applied

### Troubleshooting

- [ ] Ticket 1: Identified and fixed SSH transport fault on VTY lines
- [ ] Ticket 2: Identified and fixed over-privileged operator account
- [ ] Ticket 3: Identified and fixed Telnet exposure on VTY lines
