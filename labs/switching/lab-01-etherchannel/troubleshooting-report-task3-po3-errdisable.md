# Troubleshooting Report — Lab 01 EtherChannel, Task 3
## Po3 channel-misconfig err-disable on SW3

**Date:** 2026-04-17  
**Lab:** `labs/switching/lab-01-etherchannel`  
**Task:** Task 3 — Static EtherChannel Po3 (SW2 ↔ SW3)  
**Severity:** High — Po3 entirely down; SW2 ↔ SW3 path severed

---

## 1. Incident Summary

| Field | Detail |
|-------|--------|
| Symptom | SW3 Gi0/1 and Gi0/2 stuck in `err-disabled`; Po3 shows `SD` (standalone down) |
| Error log | `%PM-4-ERR_DISABLE: channel-misconfig (STP) error detected on Gi0/1` |
| Scope | Po3 only — Po1 (LACP) and Po2 (PAgP) were unaffected |
| Expected state | Po3 `SU`, both Gi0/1 and Gi0/2 showing `P` (bundled) |

---

## 2. Methodology Applied

**Selected: Divide and Conquer + Compare Configurations**

- The error message (`channel-misconfig STP`) immediately points to layer 2 EtherChannel/STP interaction — no need to start at layer 1
- Both sides of the bundle were checked simultaneously using Netmiko
- Running configs were compared against `solutions/SW2.cfg` and `solutions/SW3.cfg`

---

## 3. Diagnostic Log

### 3.1 Initial gather — SW3

```
SW3# show etherchannel summary
Group  Port-channel  Protocol    Ports
------+-------------+-----------+------------------------------
2      Po2(SU)         PAgP      Gi0/3(P)    Gi1/0(P)
3      Po3(SD)          -        Gi0/1(D)    Gi0/2(D)

SW3# show interfaces status
Gi0/1     TRUNK_TO_SW2_Gi0/3  err-disabled  trunk
Gi0/2     TRUNK_TO_SW2_Gi1/0  err-disabled  trunk
Po3                            err-disabled  trunk
```

**Finding:** Both Po3 members are err-disabled, and the Port-channel3 logical interface is also err-disabled.

### 3.2 SW3 member running config — confirmed correct

```
interface GigabitEthernet0/1
 channel-group 3 mode on        ! ← correct

interface GigabitEthernet0/2
 channel-group 3 mode on        ! ← correct
```

**Finding:** SW3 config is correct. Problem is not a misconfiguration on SW3's side at time of diagnosis.

### 3.3 Initial gather — SW2

```
SW2# show etherchannel summary
Group  Port-channel  Protocol    Ports
------+-------------+-----------+------------------------------
1      Po1(SU)         LACP      Gi0/1(P)    Gi0/2(P)
3      Po3(SU)          -        Gi0/3(P)    Gi1/0(P)

SW2# show interfaces status
Gi0/3     TRUNK_TO_SW3_Gi0/1  connected  trunk   ← healthy from SW2 view
Gi1/0     TRUNK_TO_SW3_Gi0/2  connected  trunk
Po3                            connected  trunk   ← SW2 reports Po3 up!
```

**Key observation:** SW2 reports Po3 `SU`. This is a static bundle — SW2 has no protocol to detect that the remote (SW3) is err-disabled. SW2 believes it is bundled simply because its ports are configured `mode on` and are physically up.

### 3.4 SW2 member running config — confirmed correct

```
interface GigabitEthernet0/3
 channel-group 3 mode on        ! ← correct

interface GigabitEthernet1/0
 channel-group 3 mode on        ! ← correct
```

### 3.5 Attempted first fix — bounce physical members on SW3

Bounced Gi0/1 and Gi0/2 (shutdown → no shutdown). Result: **err-disable re-triggered immediately** (<1 second):

```
*Apr 17 11:16:28.587: %PM-4-ERR_DISABLE: channel-misconfig (STP) error detected on Gi0/1, putting Gi0/1 in err-disable state
*Apr 17 11:16:28.587: %PM-4-ERR_DISABLE: channel-misconfig (STP) error detected on Gi0/2, putting Gi0/2 in err-disable state
```

**Analysis:** The Port-channel3 interface itself was in err-disable state. When Gi0/1 and Gi0/2 tried to join Po3, they were attaching to an err-disabled port-channel. IOS re-triggered the channel-misconfig error before the link could fully form.

### 3.6 Successful fix — clear Po3 err-disable first, then bounce members

```
SW3(config)# interface port-channel3
SW3(config-if)# shutdown
SW3(config-if)# no shutdown

*Apr 17 11:18:43.715: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/2, changed state to up
```

Then:

```
SW3(config)# interface range GigabitEthernet0/1 - 2
SW3(config-if-range)# shutdown
SW3(config-if-range)# no shutdown

*Apr 17 11:19:05.783: %LINEPROTO-5-UPDOWN: Line protocol on Interface Port-channel3, changed state to up
```

---

## 4. Root Cause Analysis

**Primary cause:** Static EtherChannel (`mode on`) was configured on SW3 **before** SW2 had its `channel-group 3 mode on` applied. During this window:

- SW3 Gi0/1 and Gi0/2 came up in static bundle mode, both forwarding as part of (what SW3 thought was) Po3
- SW2 still had Gi0/3 and Gi1/0 as **individual trunks** — not bundled
- From SW3's STP perspective: two physical ports, both forwarding, both leading to the same upstream bridge (SW2) — STP detects a forwarding loop
- STP triggered `channel-misconfig` err-disable on the physical interfaces AND the Port-channel3 interface

**Secondary complication:** Simply bouncing the physical member interfaces was insufficient because the Port-channel3 logical interface was itself in err-disable state. IOS re-triggered err-disable on the physical ports the moment they tried to rejoin the still-errored port-channel.

**Why SW2 showed Po3 SU:** Static mode has **no negotiation protocol**. SW2 cannot detect that the remote end is err-disabled. It reports Po3 as `SU` purely based on its own port states being up and configured `mode on`. This is a known characteristic — and exam trap — of static EtherChannel.

**Exam relevance (ENCOR 3.1.b):** This is the canonical `channel-misconfig` failure mode for static EtherChannel. The IOS err-disable mechanism protects against STP loops when one side is in `mode on` and the other is not yet bundled. The two-level err-disable (physical + port-channel) is a subtlety that trips up engineers who only bounce the physical members without clearing the port-channel.

---

## 5. Resolution Actions

Executed on SW3 in this sequence:

```bash
! Step 1: Clear the Port-channel3 err-disable state
SW3(config)# interface port-channel3
SW3(config-if)# shutdown
SW3(config-if)# no shutdown

! Step 2: Bounce the physical member interfaces
SW3(config)# interface range GigabitEthernet0/1 - 2
SW3(config-if-range)# shutdown
SW3(config-if-range)# no shutdown
```

No changes were required on SW2 — its configuration was already correct.

---

## 6. Verification

```
SW3# show etherchannel summary
Group  Port-channel  Protocol    Ports
------+-------------+-----------+------------------------------
2      Po2(SU)         PAgP      Gi0/3(P)    Gi1/0(P)
3      Po3(SU)          -        Gi0/1(P)    Gi0/2(P)    ← RESOLVED

SW3# show interfaces status
Gi0/1     TRUNK_TO_SW2_Gi0/3  connected  trunk  a-full  auto
Gi0/2     TRUNK_TO_SW2_Gi1/0  connected  trunk  a-full  auto
Po3                            connected  trunk  a-full  auto
```

All success criteria met:
- [x] Po3 shows `SU` (Layer 2, in use)
- [x] Gi0/1 shows `P` (bundled)
- [x] Gi0/2 shows `P` (bundled)
- [x] No `err-disabled` interfaces on SW3
- [x] Protocol column shows `-` (correct for static mode — no negotiation protocol)

---

## 7. Lessons Learned

### Lesson 1: Static EtherChannel (`mode on`) — always configure both ends simultaneously

Static mode has no negotiation. The moment one side comes up in `mode on` without the other side bundled, STP fires `channel-misconfig` and err-disables the ports. Best practice: paste the `channel-group N mode on` commands on both switches in the same maintenance window before the links are active, or pre-configure on both sides before the cables go in.

> **Exam tip:** Static `mode on` is the only EtherChannel mode with no tolerance for sequencing. LACP and PAgP will patiently wait for the remote to come up. Static will err-disable the moment it detects a non-bundle condition.

### Lesson 2: err-disable is two-level — check the port-channel, not just the members

When physical members are err-disabled, the port-channel logical interface also enters err-disable. Bouncing only the physical members will not resolve the condition — they will immediately re-trigger the err-disable because they are joining an already-errored port-channel. The correct sequence:

1. `shutdown` → `no shutdown` on the **port-channel interface** first
2. Then `shutdown` → `no shutdown` on the **physical member interfaces**

### Lesson 3: Static mode hides remote failures from the local side

SW2 reported Po3 `SU` even though SW3 was completely err-disabled. Static mode (`mode on`) trusts configuration, not link state negotiation. Always verify both ends independently when troubleshooting a static bundle.

### Lesson 4: `show errdisable recovery` before bouncing

Before bouncing any err-disabled interface, check `show errdisable recovery`. If automatic recovery is disabled (as it was here — `channel-misconfig (STP): Disabled`), the interface will NOT recover on its own and must be manually bounced. If the root cause isn't fixed before the bounce, the err-disable will immediately re-trigger.

---

## 8. Prevention

For future static EtherChannel configurations in this lab series:

```bash
! On BOTH switches — configure in the same step, both ends before links activate

! SW2
interface range GigabitEthernet0/3 , GigabitEthernet1/0
 channel-group 3 mode on

! SW3
interface range GigabitEthernet0/1 - 2
 channel-group 3 mode on
```

To enable automatic recovery (optional, not required for the lab):

```bash
! On all switches — allows automatic recovery from channel-misconfig after 300s
errdisable recovery cause channel-misconfig
errdisable recovery interval 300
```

---

*Report generated: 2026-04-17 | Lab: ccnp-encor-labs/labs/switching/lab-01-etherchannel*
