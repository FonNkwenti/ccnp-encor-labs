# Automation Lab 00 — EEM Applets for On-Box Automation

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

**Exam Objective:** 6.6 — Construct an EEM applet to automate configuration, troubleshooting, or data collection | Topic: Automation and Programmability

Embedded Event Manager (EEM) is IOS's built-in event-driven automation engine. Instead of polling show commands or manually reacting to network events, you define applets that watch for conditions and automatically execute CLI commands or generate alerts when those conditions occur. This lab covers all three core EEM event types tested on the 350-401 exam: interface state tracking, scheduled cron timers, and syslog pattern matching.

---

### EEM Architecture — Events, Detectors, and Actions

EEM operates on a simple model: every applet has exactly one **event** (what to watch) and one or more **actions** (what to do when the event fires). The event detector runs continuously in the background; when the condition is met, IOS executes the actions in ascending numerical order.

```
event manager applet <NAME>
 event <detector-type> <parameters>     ! what to watch
 action 1.0 <action-type> <parameters>  ! first thing to do
 action 2.0 <action-type> <parameters>  ! second thing to do
 ...
```

Action numbers are decimals. They must be unique and are executed in ascending order. Gaps are allowed (1.0, 2.0, 10.0 is valid).

**The three event detectors on the ENCOR exam:**

| Detector | Syntax | Fires When |
|----------|--------|------------|
| `track N state down` | `event track 1 state down` | Tracked object transitions to down |
| `timer cron` | `event timer cron cron-entry "* * * * *"` | Cron schedule matches current time |
| `syslog pattern` | `event syslog pattern "FACILITY-SEV-MNEM"` | Syslog message matches regex |

---

### EEM Action Types

The three action types you need for the exam:

| Action | Syntax | Does |
|--------|--------|------|
| `syslog` | `action N.N syslog msg "text"` | Writes message to local syslog |
| `cli command` | `action N.N cli command "..."` | Executes a CLI command |
| `counter` | `action N.N counter name C op add value 1` | Increments/resets a named counter |

`cli command` is the most powerful — it can run any CLI command the router supports, including show commands, configuration commands, and file operations. The output is not displayed on the console; it appears in `show event manager history detail`.

**Interactive commands** (those that prompt for input) require the `pattern` keyword:

```
action 2.0 cli command "copy running-config startup-config" pattern "filename"
action 3.0 cli command ""
```

Here `pattern "filename"` tells EEM to wait until the string "filename" appears in the output before sending the next command (`""` = press Enter to accept the default).

---

### Object Tracking and EEM

The `track` event detector requires a pre-configured **tracking object**. A tracking object monitors a resource and reports an up/down state:

```
track 1 interface GigabitEthernet0/0 line-protocol
```

This creates track object 1 that monitors the line-protocol state of GigabitEthernet0/0. When the interface goes down, track 1 reports `down`, which triggers any EEM applet with `event track 1 state down`.

You can also track IP SLA results (`track 1 ip sla 1 reachability`), but interface line-protocol tracking is simpler and sufficient for this lab.

---

### The EEM Session Username — Critical Prerequisite

By default, EEM CLI actions run as an unprivileged user (privilege level 1). At privilege 1, `configure terminal` is rejected and most show commands are unavailable. Any applet that issues CLI commands will silently fail unless you set the EEM session username:

```
event manager session cli username admin
```

This single global command tells EEM to run all CLI actions as the local user `admin` (who is privilege 15 in this lab). Without it, applets register and fire, but their CLI actions produce no output and make no changes.

> This command is pre-configured in this lab. It is a common real-world misconfiguration that will be tested in the troubleshooting scenarios.

---

### Verifying and Monitoring EEM

| Command | What it Shows |
|---------|--------------|
| `show event manager policy registered` | All registered applets, their event type, and registration time |
| `show event manager history events` | Log of every event that fired (most recent at bottom) |
| `show event manager history detail` | Same as above plus all actions executed and their output |

Applets appear in `show event manager policy registered` immediately after configuration. If an applet does not appear, there is a syntax error in the `event` line.

---

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| EEM applet construction | Writing event + ordered action blocks |
| Object tracking | Configuring and referencing track objects |
| Event detectors | Distinguishing track, cron, and syslog event types |
| EEM action types | Using syslog, cli command, and interactive patterns |
| EEM verification | Reading registered applets and execution history |
| On-box automation | Automating responses to network events without external tools |

---

## 2. Topology & Scenario

**Scenario:** You are a network engineer at Encor Enterprises. The operations team has requested automated responses to three recurring situations: when a critical uplink interface goes down (create a backup loopback for monitoring), daily config archiving (scheduled backup at midnight), and OSPF neighbor change detection (automatic neighbor table capture for the NOC).

Management has assigned R3 as the dedicated automation node — it runs IOSv and will host all EEM applets. R1 and R2 are CSR1000v routers that form the OSPF backbone; they are infrastructure for triggering events but are not the EEM host.

```
           ┌─────────────────────┐
           │         PC1         │
           │       (VPCS)        │
           │  192.168.10.10/24   │
           └──────────┬──────────┘
                      │ eth0
                      │ 192.168.10.10/24
                      │
                      │ 192.168.10.1/24
                      │ GigabitEthernet2
           ┌──────────┴──────────┐
           │          R1         │
           │     (CSR1000v)      │
           │  Lo0: 1.1.1.1/32    │
           └──────────┬──────────┘
                      │ GigabitEthernet1
                      │ 10.1.12.1/30
                      │
                      │ 10.1.12.2/30
                      │ GigabitEthernet1
           ┌──────────┴──────────┐
           │          R2         │
           │     (CSR1000v)      │
           │  Lo0: 2.2.2.2/32    │
           └──────────┬──────────┘
                      │ GigabitEthernet2
                      │ 10.1.23.1/30
                      │
                      │ 10.1.23.2/30
                      │ GigabitEthernet0/0
           ┌──────────┴──────────┐
           │          R3         │
           │  (IOSv / EEM Host)  │
           │  Lo0: 3.3.3.3/32    │
           └──────────┬──────────┘
                      │ GigabitEthernet0/1
                      │ 192.168.20.1/24
                      │
                      │ 192.168.20.10/24
                      │ eth0
           ┌──────────┴──────────┐
           │         PC2         │
           │       (VPCS)        │
           │  192.168.20.10/24   │
           └─────────────────────┘
```

**OSPF Area 0** runs on all three routers (R1, R2, R3). The R2–R3 OSPF adjacency is the event source for the MATCH-SYSLOG applet.

---

## 3. Hardware & Environment Specifications

### Cabling Table

| Link | Source | Source IP | Target | Target IP | Subnet |
|------|--------|-----------|--------|-----------|--------|
| L1 | R1 GigabitEthernet1 | 10.1.12.1/30 | R2 GigabitEthernet1 | 10.1.12.2/30 | 10.1.12.0/30 |
| L2 | R2 GigabitEthernet2 | 10.1.23.1/30 | R3 GigabitEthernet0/0 | 10.1.23.2/30 | 10.1.23.0/30 |
| L3 | R1 GigabitEthernet2 | 192.168.10.1/24 | PC1 eth0 | 192.168.10.10/24 | 192.168.10.0/24 |
| L4 | R3 GigabitEthernet0/1 | 192.168.20.1/24 | PC2 eth0 | 192.168.20.10/24 | 192.168.20.0/24 |

### Device Inventory

| Device | Platform | Role | Loopback0 |
|--------|----------|------|-----------|
| R1 | CSR1000v (IOS-XE 17.x) | OSPF backbone | 1.1.1.1/32 |
| R2 | CSR1000v (IOS-XE 17.x) | OSPF backbone | 2.2.2.2/32 |
| R3 | IOSv (IOS 15.9) | EEM automation host | 3.3.3.3/32 |
| PC1 | VPCS | Traffic source | — |
| PC2 | VPCS | Traffic destination | — |

### Console Access Table

| Device | Port | Connection Command |
|--------|------|--------------------|
| R1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R3 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| PC1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| PC2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |

---

## 4. Base Configuration

The following is pre-loaded on all devices via `setup_lab.py`:

**Pre-loaded on R1, R2, R3:**
- Hostname and domain name
- Local user `admin` at privilege 15
- SSH version 2 (RSA keys generated by setup script)
- IP addressing on all interfaces
- OSPF process 1 (area 0, all routers in full adjacency)

**Pre-loaded on R3 only:**
- EEM session username (`event manager session cli username admin`)
- Object track 1 (monitoring GigabitEthernet0/0 line-protocol)

**NOT pre-loaded — student configures in this lab:**
- EEM applets (TRACK-INTERFACE, BACKUP-CONFIG, MATCH-SYSLOG)

> **Note on OSPF pre-loading:** OSPF is pre-loaded as infrastructure because the MATCH-SYSLOG applet requires live OSPF adjacencies to trigger. The EEM session username and track object are also pre-loaded because they are prerequisite infrastructure, not lab tasks. Focus all your effort on the applet definitions.

---

## 5. Lab Challenge: Core Implementation

### Task 1: Interface-Tracking Applet

- On R3, create an EEM applet named **TRACK-INTERFACE**.
- The applet must fire when tracked object 1 transitions to the **down** state.
- When triggered, the applet must perform these actions in order:
  - Write a syslog message: `EEM: Tracked interface went DOWN`
  - Enter privileged EXEC mode
  - Enter global configuration mode
  - Create interface Loopback99
  - Assign IP address 99.99.99.99 with mask 255.255.255.255 to Loopback99
  - Exit configuration mode

**Verification:** `show event manager policy registered` must show TRACK-INTERFACE registered with event type `track` referencing track 1.

---

### Task 2: Scheduled Backup Applet

- On R3, create an EEM applet named **BACKUP-CONFIG**.
- The applet must fire on a cron schedule that runs at midnight every day (minute 0, hour 0, every day, every month, every weekday).
- When triggered, the applet must:
  - Enter privileged EXEC mode
  - Copy the running configuration to startup configuration (handle the filename prompt by accepting the default)
  - Write a syslog message: `EEM: Nightly config backup completed`

**Verification:** `show event manager policy registered` must show BACKUP-CONFIG registered with event type `timer cron` and the correct cron expression.

---

### Task 3: OSPF Adjacency Syslog Applet

- On R3, create an EEM applet named **MATCH-SYSLOG**.
- The applet must fire whenever a syslog message containing the string `OSPF-5-ADJCHG` appears.
- When triggered, the applet must:
  - Write a syslog message: `EEM: OSPF adjacency change detected`
  - Enter privileged EXEC mode
  - Execute a show command to capture the current OSPF neighbor table

**Verification:** `show event manager policy registered` must show MATCH-SYSLOG registered with event type `syslog` and pattern `OSPF-5-ADJCHG`.

---

### Task 4: Trigger and Verify All Applets

- Trigger MATCH-SYSLOG by resetting the OSPF process on R3. Confirm the applet fired by checking EEM event history and the syslog output.
- Trigger TRACK-INTERFACE by shutting down GigabitEthernet0/0 on R3. Confirm Loopback99 was created with the correct IP address.
- Verify BACKUP-CONFIG is registered (it fires at midnight — no manual trigger needed; confirm registration only).
- Restore GigabitEthernet0/0 to no shutdown after testing.

> **Note:** Shutting down GigabitEthernet0/0 will fire both TRACK-INTERFACE (track 1 goes down) AND MATCH-SYSLOG (OSPF adjacency drops). This is expected behavior — both applets trigger simultaneously. Similarly, resetting the OSPF process generates two adjacency events (down then up), so MATCH-SYSLOG fires twice per reset. This is correct.

**Verification:** `show event manager history events` shows recent TRACK-INTERFACE and MATCH-SYSLOG entries. `show interfaces loopback99` shows the interface with IP 99.99.99.99/32.

---

## 6. Verification & Analysis

### Task 1 — TRACK-INTERFACE Registered

```
R3# show event manager policy registered
No.  Class     Type    Event Type          Trap  Time Registered           Name
1    applet    system  track               Off   Mon Apr 19 10:00:00 2026  TRACK-INTERFACE  ! ← applet registered
 Event    : track 1 state down                                                              ! ← track 1, state down
 Action   : 001.0          syslog
            002.0          cli
            003.0          cli
            004.0          cli
            005.0          cli
            006.0          cli
```

### Task 2 — BACKUP-CONFIG Registered

```
R3# show event manager policy registered
No.  Class     Type    Event Type          Trap  Time Registered           Name
1    applet    system  track               Off   Mon Apr 19 10:00:00 2026  TRACK-INTERFACE
2    applet    system  timer cron          Off   Mon Apr 19 10:00:00 2026  BACKUP-CONFIG    ! ← applet registered
 Event    : cron entry 0 0 * * *                                                            ! ← midnight schedule
```

### Task 3 — MATCH-SYSLOG Registered

```
R3# show event manager policy registered
No.  Class     Type    Event Type          Trap  Time Registered           Name
1    applet    system  track               Off   Mon Apr 19 10:00:00 2026  TRACK-INTERFACE
2    applet    system  timer cron          Off   Mon Apr 19 10:00:00 2026  BACKUP-CONFIG
3    applet    system  syslog              Off   Mon Apr 19 10:00:00 2026  MATCH-SYSLOG     ! ← applet registered
 Event    : syslog pattern {OSPF-5-ADJCHG}                                                  ! ← exact pattern match
```

### Task 4 — Trigger MATCH-SYSLOG (Clear OSPF Process)

Trigger on R3: `clear ip ospf process` — answer Yes to confirm.

```
R3# show logging | include ADJCHG
%OSPF-5-ADJCHG: Process 1, Nbr 2.2.2.2 on GigabitEthernet0/0 from FULL to DOWN, Neighbor Down: Interface down or detached  ! ← adjacency drop fires MATCH-SYSLOG
%OSPF-5-ADJCHG: Process 1, Nbr 2.2.2.2 on GigabitEthernet0/0 from LOADING to FULL, Loading Done                            ! ← adjacency restore fires MATCH-SYSLOG again

R3# show logging | include EEM
%SYS-5-LOG_CONFIG_CHANGE: EEM: OSPF adjacency change detected  ! ← fires once per ADJCHG message (two total)

R3# show event manager history events
No.  Time                      Event Type    Name
1    Mon Apr 19 10:05:03 2026  syslog        MATCH-SYSLOG   ! ← first trigger (adjacency DOWN)
2    Mon Apr 19 10:05:07 2026  syslog        MATCH-SYSLOG   ! ← second trigger (adjacency UP)
```

> Expect **two** MATCH-SYSLOG triggers per `clear ip ospf process` — one when the adjacency drops and one when it re-forms.

### Task 4 — Trigger TRACK-INTERFACE (Shut Gi0/0)

On R3: `interface GigabitEthernet0/0` → `shutdown`

```
R3# show track 1
Track 1
  Interface GigabitEthernet0/0 Line Protocol
  Line protocol is Down                    ! ← track object reports down
    2 changes, last change 00:00:05

R3# show logging | include EEM
%SYS-5-LOG_CONFIG_CHANGE: EEM: Tracked interface went DOWN    ! ← TRACK-INTERFACE fired
%SYS-5-LOG_CONFIG_CHANGE: EEM: OSPF adjacency change detected ! ← MATCH-SYSLOG also fired (OSPF dropped)

R3# show interfaces loopback99
Loopback99 is up, line protocol is up
  Internet address is 99.99.99.99/32        ! ← backup loopback created with correct IP

R3# show event manager history events
No.  Time                      Event Type    Name
...
3    Mon Apr 19 10:10:02 2026  track         TRACK-INTERFACE ! ← applet fired when Gi0/0 went down
4    Mon Apr 19 10:10:02 2026  syslog        MATCH-SYSLOG    ! ← also fired (OSPF adjacency dropped)
```

> Both TRACK-INTERFACE and MATCH-SYSLOG fire when GigabitEthernet0/0 goes down. This is expected — the track object fires EEM immediately, and the OSPF adjacency loss generates an ADJCHG syslog that fires MATCH-SYSLOG.

After testing, restore the interface: `interface GigabitEthernet0/0` → `no shutdown`

---

## 7. Verification Cheatsheet

### EEM Applet Configuration

```
event manager applet <NAME>
 event track <N> state {down | up | change}
 event timer cron cron-entry "<min hr day month weekday>"
 event syslog pattern "<regex-string>"
 action <N.N> syslog msg "<message>"
 action <N.N> cli command "<ios-command>"
 action <N.N> cli command "<interactive-cmd>" pattern "<wait-string>"
 action <N.N> cli command "<response>"
```

| Command | Purpose |
|---------|---------|
| `event manager applet NAME` | Define/enter an EEM applet |
| `event track N state down` | Fire when track object N transitions to down |
| `event timer cron cron-entry "..."` | Fire on cron schedule |
| `event syslog pattern "..."` | Fire when syslog matches regex |
| `action N.N syslog msg "..."` | Write message to syslog |
| `action N.N cli command "..."` | Execute CLI command |
| `no event manager applet NAME` | Remove an applet |

> **Exam tip:** Action numbers are arbitrary decimals — the execution order is ascending numeric, not definition order. Gaps are legal and useful for inserting steps later.

### Object Tracking

```
track <N> interface <intf> line-protocol
track <N> ip sla <sla-id> reachability
 delay down <sec> up <sec>
```

| Command | Purpose |
|---------|---------|
| `track N interface X line-protocol` | Track interface line-protocol state |
| `track N ip sla N reachability` | Track IP SLA operation reachability |
| `delay down 10 up 10` | Dampen state changes (seconds before notifying) |

> **Exam tip:** The track object must exist before EEM can reference it. On IOSv 15.9, an EEM applet with a non-existent track number will register but never fire — it won't error at configuration time.

### EEM Session Configuration

```
event manager session cli username <username>
```

| Command | Purpose |
|---------|---------|
| `event manager session cli username admin` | Run CLI actions as the specified user (inherits privilege level) |

> **Exam tip:** Without `event manager session cli username`, all CLI actions run at privilege 1. The applet fires and the history shows it ran, but `configure terminal` is rejected and no changes are made. This is a common silent failure.

### Verification Commands

| Command | What to Look For |
|---------|-----------------|
| `show event manager policy registered` | All applets registered, event type, and name |
| `show event manager history events` | List of every event that fired with timestamp |
| `show event manager history detail` | All actions executed and their CLI output |
| `show track N` | Current state of tracking object N |
| `show logging` | Syslog messages including EEM-generated entries |

### Cron Expression Quick Reference

| Expression | Fires |
|------------|-------|
| `0 0 * * *` | Midnight every day |
| `0 * * * *` | Top of every hour |
| `*/5 * * * *` | Every 5 minutes |
| `0 9 * * 1-5` | 9:00 AM weekdays |

Format: `<minute> <hour> <day-of-month> <month> <day-of-week>`

### Common EEM Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| Applet not in `show event manager policy registered` | Syntax error in `event` line |
| Applet registered but never fires | Wrong track number / wrong syslog pattern / cron schedule not reached |
| Applet fires but no changes made | Missing `event manager session cli username` |
| CLI action fails silently | Privilege too low — check session username |
| Interactive command hangs | Missing `pattern` keyword or wrong pattern string |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Task 1: Interface-Tracking Applet

<details>
<summary>Click to view R3 Configuration</summary>

```bash
! R3
event manager applet TRACK-INTERFACE
 event track 1 state down
 action 1.0 syslog msg "EEM: Tracked interface went DOWN"
 action 2.0 cli command "enable"
 action 3.0 cli command "configure terminal"
 action 4.0 cli command "interface loopback99"
 action 5.0 cli command "ip address 99.99.99.99 255.255.255.255"
 action 6.0 cli command "end"
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show event manager policy registered
! Look for: TRACK-INTERFACE registered with event type "track", event track 1 state down
```
</details>

---

### Task 2: Scheduled Backup Applet

<details>
<summary>Click to view R3 Configuration</summary>

```bash
! R3
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
! Look for: BACKUP-CONFIG registered with event type "timer cron", cron entry 0 0 * * *
```
</details>

---

### Task 3: OSPF Adjacency Syslog Applet

<details>
<summary>Click to view R3 Configuration</summary>

```bash
! R3
event manager applet MATCH-SYSLOG
 event syslog pattern "OSPF-5-ADJCHG"
 action 1.0 syslog msg "EEM: OSPF adjacency change detected"
 action 2.0 cli command "enable"
 action 3.0 cli command "show ip ospf neighbor"
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show event manager policy registered
! Look for: MATCH-SYSLOG registered with event type "syslog", pattern {OSPF-5-ADJCHG}
```
</details>

---

### Task 4: Trigger and Verify

<details>
<summary>Click to view Trigger Sequence</summary>

```bash
! Step 1 — Trigger MATCH-SYSLOG (OSPF adjacency change)
R3# clear ip ospf process       ! answer Yes
R3# show event manager history events   ! expect 2 MATCH-SYSLOG entries
R3# show logging | include EEM          ! see "OSPF adjacency change detected" twice

! Step 2 — Trigger TRACK-INTERFACE (interface down)
R3# configure terminal
R3(config)# interface GigabitEthernet0/0
R3(config-if)# shutdown
R3(config-if)# end
R3# show track 1                        ! track state: Down
R3# show interfaces loopback99          ! Loopback99 up, IP 99.99.99.99/32
R3# show event manager history events   ! expect TRACK-INTERFACE entry

! Step 3 — Restore
R3# configure terminal
R3(config)# interface GigabitEthernet0/0
R3(config-if)# no shutdown
R3(config-if)# end
```
</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. Inject the fault first, then diagnose and fix using only show commands.

### Workflow

```bash
python3 setup_lab.py --host <eve-ng-ip>                           # reset to known-good
python3 scripts/fault-injection/inject_scenario_01.py --host <ip> # Ticket 1
python3 scripts/fault-injection/apply_solution.py --host <ip>     # restore
```

---

### Ticket 1 — GigabitEthernet0/0 Goes Down but No EEM Response

You shut down GigabitEthernet0/0 on R3 to test the tracking applet. No syslog message appears from EEM and Loopback99 is never created. The TRACK-INTERFACE applet is visible in `show event manager policy registered`.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip>`

**Success criteria:** Shutting down GigabitEthernet0/0 causes the EEM syslog message `EEM: Tracked interface went DOWN` to appear and Loopback99 to be created with IP 99.99.99.99/32.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! Step 1 — Confirm the applet is registered
R3# show event manager policy registered
! Look for TRACK-INTERFACE — it will be there, but read the event line carefully

! Step 2 — Read the event line
! The policy registered output will show which track number the applet references
! Compare this with the track objects that actually exist

! Step 3 — Check existing track objects
R3# show track
! If the applet references track 99 but show track only shows track 1,
! the applet is watching for an object that doesn't exist and will never fire

! Step 4 — Correlate
! show event manager policy registered → event track 99 state down
! show track → only track 1 exists
! Conclusion: track number mismatch — the applet will never fire
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
R3# configure terminal
R3(config)# event manager applet TRACK-INTERFACE
R3(config-applet)# no event track 99 state down
R3(config-applet)# event track 1 state down
R3(config-applet)# end
R3# show event manager policy registered
! Confirm: event track 1 state down
```
</details>

---

### Ticket 2 — OSPF Adjacency Changes but EEM Never Logs Them

The NOC reports that OSPF adjacency flaps have been observed in `show logging` but the MATCH-SYSLOG applet has no entries in EEM event history. The applet is registered and has the correct actions.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py --host <eve-ng-ip>`

**Success criteria:** After clearing the OSPF process (`clear ip ospf process`), `show event manager history events` shows MATCH-SYSLOG firing and `show logging` shows `EEM: OSPF adjacency change detected`.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! Step 1 — Confirm the applet is registered
R3# show event manager policy registered
! Read the syslog pattern exactly — it must match what IOS actually logs

! Step 2 — Check what IOS actually logs for OSPF adjacency changes
R3# show logging | include OSPF
! You will see messages like:
!   %OSPF-5-ADJCHG: Process 1, Nbr 2.2.2.2 ...
! The mnemonic in the syslog is: OSPF-5-ADJCHG

! Step 3 — Compare pattern to actual message
! If the registered pattern shows "OSPF-5-ADJCHANGE" but the syslog shows "OSPF-5-ADJCHG",
! the regex will never match and the applet will never fire.
! "ADJCHG" ≠ "ADJCHANGE"

! Step 4 — Generate a test event and confirm no history entry
R3# clear ip ospf process        ! answer Yes
R3# show event manager history events
! MATCH-SYSLOG will not appear — confirms pattern mismatch
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
R3# configure terminal
R3(config)# event manager applet MATCH-SYSLOG
R3(config-applet)# no event syslog pattern "OSPF-5-ADJCHANGE"
R3(config-applet)# event syslog pattern "OSPF-5-ADJCHG"
R3(config-applet)# end
R3# clear ip ospf process
R3# show event manager history events
! Confirm MATCH-SYSLOG appears twice (adjacency down + up)
```
</details>

---

### Ticket 3 — TRACK-INTERFACE Fires but Loopback99 Has No IP Address

You shut down GigabitEthernet0/0 on R3. The syslog shows `EEM: Tracked interface went DOWN` confirming the applet fired. But `show interfaces loopback99` shows the interface was created with no IP address.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py --host <eve-ng-ip>`

**Success criteria:** Shutting down GigabitEthernet0/0 creates Loopback99 with IP address 99.99.99.99/32.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! Step 1 — Confirm the applet fired
R3# show event manager history events
! TRACK-INTERFACE entry is present — applet did fire

! Step 2 — Check the loopback interface
R3# show interfaces loopback99
! Interface exists and is up, but no "Internet address is" line
! Loopback99 was created (action 4.0 ran) but has no IP address

! Step 3 — Inspect the applet's action list
R3# show running-config | section event manager applet TRACK-INTERFACE
! Read every action line. The action that assigns the IP address (action 5.0)
! may be missing from the applet body.
! Without action 5.0, the applet creates the interface but skips the ip address command.

! Step 4 — Confirm missing action
! Expected: action 5.0 cli command "ip address 99.99.99.99 255.255.255.255"
! If action 5.0 is absent, that is the fault.
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! First — remove the loopback created without an IP
R3# configure terminal
R3(config)# no interface loopback99

! Fix the applet — add the missing action
R3(config)# event manager applet TRACK-INTERFACE
R3(config-applet)# action 5.0 cli command "ip address 99.99.99.99 255.255.255.255"
R3(config-applet)# end

! Verify the applet has all 6 actions
R3# show running-config | section event manager applet TRACK-INTERFACE

! Re-test: shut down Gi0/0 and confirm Loopback99 has the correct IP
R3# configure terminal
R3(config)# interface GigabitEthernet0/0
R3(config-if)# shutdown
R3(config-if)# end
R3# show interfaces loopback99
! Expect: Internet address is 99.99.99.99/32
```
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] TRACK-INTERFACE applet registered: `event track 1 state down`
- [ ] BACKUP-CONFIG applet registered: `event timer cron cron-entry "0 0 * * *"`
- [ ] MATCH-SYSLOG applet registered: `event syslog pattern "OSPF-5-ADJCHG"`
- [ ] All three applets visible in `show event manager policy registered`
- [ ] MATCH-SYSLOG fires after `clear ip ospf process` (two entries in history)
- [ ] TRACK-INTERFACE fires after shutting down GigabitEthernet0/0
- [ ] Loopback99 created with IP 99.99.99.99/32 after trigger
- [ ] GigabitEthernet0/0 restored (`no shutdown`)

### Troubleshooting

- [ ] Ticket 1: TRACK-INTERFACE fires correctly after correcting the track number
- [ ] Ticket 2: MATCH-SYSLOG fires after correcting the syslog pattern
- [ ] Ticket 3: Loopback99 created with correct IP after restoring missing action
