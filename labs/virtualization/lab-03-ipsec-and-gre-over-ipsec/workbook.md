# Lab 03 — IPsec Tunnels and GRE over IPsec

## Table of Contents

1. [Concepts & Skills Covered](#1-concepts--skills-covered)
1a. [Mental Model: The Secret Letter Analogy](#1a-mental-model-the-secret-letter-analogy)
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

**Exam Objective:** 2.2, 2.2.b — Configure and verify data path virtualization technologies: GRE and IPsec tunneling (CCNP ENCOR 350-401)

This lab adds IPsec encryption to the tunnel overlay built in lab-02. You will configure a pure IPsec Virtual Tunnel Interface (VTI), then a GRE tunnel protected by an IPsec profile — two design patterns with different trade-offs. By the end, you will have three active overlays between R1 and R4, each using the same IKEv2 crypto infrastructure but with distinct forwarding behaviors.

### IKEv2 — Internet Key Exchange Version 2

IKEv2 is the modern standards-based protocol for establishing IPsec Security Associations (SAs). It replaces the two-phase IKEv1 model with a single exchange that is simpler, faster, and more resilient to DoS attacks.

IKEv2 configuration uses a four-tier hierarchy on IOS:

```
crypto ikev2 proposal <name>        ! algorithms: encryption, integrity, DH group
  encryption aes-cbc-256
  integrity sha256
  group 14

crypto ikev2 policy <name>          ! selects which proposals are acceptable
  proposal <proposal-name>

crypto ikev2 keyring <name>         ! maps a peer IP to a pre-shared key
  peer <label>
    address <peer-ip>
    pre-shared-key <key>

crypto ikev2 profile <name>         ! ties keyring to a peer identity + auth method
  match identity remote address <ip> <mask>
  authentication remote pre-share
  authentication local pre-share
  keyring local <keyring-name>
```

The profile is what gets referenced by the IPsec profile (`set ikev2-profile`). Both endpoints must mirror each other — R1 references R4's Loopback10 (`10.10.4.4`) in its keyring; R4 references R1's Loopback10 (`10.10.1.1`).

### IPsec Transform Set and Profile

An IPsec transform set specifies the data-plane encryption and integrity algorithms applied to ESP (Encapsulating Security Payload). An IPsec profile bundles the transform set with an IKEv2 profile for use on tunnel interfaces.

```
crypto ipsec transform-set <name> esp-aes 256 esp-sha256-hmac
 mode tunnel

crypto ipsec profile <name>
 set transform-set <ts-name>
 set ikev2-profile <ikev2-profile-name>
```

`mode tunnel` is the default for VTI-style configs. The profile name is referenced via `tunnel protection ipsec profile <name>` on the tunnel interface.

### IPsec VTI vs GRE-over-IPsec

| Feature | IPsec VTI (Tunnel1) | GRE-over-IPsec (Tunnel2) |
|---------|---------------------|--------------------------|
| Tunnel mode | `tunnel mode ipsec ipv4` | `tunnel mode gre ip` + `tunnel protection` |
| Multicast support | No — OSPF cannot form | Yes — OSPF hellos traverse the GRE wrapper |
| IPv6 inner payload | Limited | Yes — GRE carries any protocol |
| Overhead | ~52 bytes (ESP + outer IP) | ~72 bytes (GRE 24 + ESP 48) |
| Routing protocol | Static routes only | OSPF, EIGRP, BGP over the tunnel |
| Use case | Simple encrypted point-to-point | Hub-and-spoke with dynamic routing |

With GRE-over-IPsec: the packet stack is `[outer IP][GRE header][ESP][inner IP][payload]`. The GRE wrapper makes the encrypted payload look like a multicast-capable point-to-point link, enabling OSPF hello exchange.

### IKEv2 SA States

```
show crypto ikev2 sa detail
```

Key states to recognize:

| State | Meaning |
|-------|---------|
| `READY` | IKEv2 SA fully established, both sides authenticated |
| `DELETED` | SA torn down — check PSK mismatch, proposal mismatch, or reachability |
| No output | No IKE attempt yet — trigger traffic first |

**Skills this lab develops:**

| Skill | Description |
|-------|-------------|
| IKEv2 proposal/policy configuration | Define encryption, integrity, and DH group for key exchange |
| IKEv2 keyring management | Map peer loopback IPs to pre-shared keys |
| IKEv2 profile construction | Bind keyring and auth method to a peer identity |
| IPsec transform set | Configure ESP encryption and integrity for data plane |
| IPsec VTI configuration | Build `tunnel mode ipsec ipv4` interface with profile binding |
| GRE-over-IPsec | Apply `tunnel protection ipsec profile` to a GRE tunnel |
| Multi-overlay OSPF | Run separate OSPF processes per overlay type |
| IPsec SA verification | Read SA counters to confirm encryption is active |

---

## 1a. Mental Model: The Secret Letter Analogy

If the technical detail above feels abstract, this section builds a mental model you can anchor to. **Skip this section if you already feel confident in your understanding.**

### The Story: Two Spies Sending Secret Letters

Imagine **Agent Alice (R1)** and **Agent Bob (R4)** need to send secret letters through an untrusted postal network. Some workers are trustworthy (direct links), but they must pass through the **central post office (R3)**, which is exposed and monitored.

---

### **Phase 1: The Secret Agreement (IKEv2)**

Before they can send encrypted letters, Alice and Bob must agree on a cipher. They do this through a secure phone call:

```
┌──────────────────────────────────────────────────────────────────────┐
│                    THE IKEv2 HANDSHAKE                               │
│                  (Agreement on Encryption Keys)                       │
└──────────────────────────────────────────────────────────────────────┘

       Alice (R1)                                        Bob (R4)
         │                                                 │
         │                  INIT MESSAGE                   │
         ├────────────────────────────────────────────────>│
         │   "Hi Bob, here's my encryption preference"    │
         │   - Encryption: AES-256                        │
         │   - Integrity: SHA-256                         │
         │   - Group: 14 (2048-bit keys)                 │
         │                                                 │
         │                RESPONSE MESSAGE                │
         │<────────────────────────────────────────────────┤
         │   "Sounds good Alice, let's use those"         │
         │   (Bob confirms Alice's proposal)              │
         │                                                 │
         │          Both compute SHARED SECRET            │
         │          using IKEv2-KEYRING (PSK)             │
         │                                                 │
         │ ✓ IKE SA established (READY state)            │
         │   Now both have the same encryption key        │
         │                                                 │
```

**Key point:** The IKEv2 handshake is a one-way agreement process—both sides agree on *how* to encrypt, not *what* to encrypt yet. The PSK (pre-shared key) is the password they both know beforehand.

---

### **Phase 2: The Sealed Envelope Arrives (IPsec)**

Now that Alice and Bob agree on a cipher, Alice writes her secret letter and seals it with the agreed-upon encryption. IPsec is the envelope-sealing process:

```
┌──────────────────────────────────────────────────────────────────────┐
│              PACKET ENCRYPTION: PLAIN vs SEALED                       │
└──────────────────────────────────────────────────────────────────────┘

Plain Letter (No Encryption):
┌─────────────────────────────────────┐
│  Outer Address: Postal Office (R3)  │
├─────────────────────────────────────┤
│ Inner Address: Bob's Address (R4)   │
│ Message: "Meet at the bridge"       │  ← ANYONE can read this!
├─────────────────────────────────────┤
│ Signature: Alice                    │
└─────────────────────────────────────┘
           ↓ Postal worker can see everything inside


Sealed Letter (IPsec Encryption):
┌─────────────────────────────────────┐
│  Outer Address: Postal Office (R3)  │
├─────────────────────────────────────┤
│ ████████████████████████████████    │  ← ENCRYPTED payload
│ ████████████████████████████████    │    (postal worker sees garbage)
│ ████████████████████████████████    │
│ ESP Authentication Tag (MAC)        │
└─────────────────────────────────────┘
    ↓ Postal worker cannot see inside
      (only outer address matters)
```

**Key point:** IPsec encrypts the *entire* inner packet (Alice → Bob's message) but leaves the outer address (R1 → R4) visible so the postal office (R3) knows where to send it.

---

### **The Three Tunnel Types: Three Different Envelope Styles**

Now here's where it gets interesting. Alice and Bob can seal their letters three different ways:

#### **Option 1: Plain Letter (Tunnel0 — No Encryption)**
```
┌─────────────────────────────────────────────────────────────┐
│                   TUNNEL0: PLAIN GRE                        │
│              (No encryption, multicast OK)                   │
└─────────────────────────────────────────────────────────────┘

    [Outer IP: R1→R4]
         │
         ├─[GRE Wrapper: marks this as a tunnel]
         │
         └─[Inner IP: App payload]
              ↓
    Postal worker sees plain text
    ✓ Can forward multicast (like OSPF hellos)
    ✗ NO security
```

#### **Option 2: Sealed Direct (Tunnel1 — IPsec VTI)**
```
┌─────────────────────────────────────────────────────────────┐
│              TUNNEL1: IPsec VTI (Native IPsec)             │
│          (Pure encryption, NO multicast capability)         │
└─────────────────────────────────────────────────────────────┘

    [Outer IP: R1→R4]
         │
         ├─[ESP Header]
         │
         ├─[████ ENCRYPTED Inner IP + Payload ████]
         │
         └─[ESP Trailer + AUTH Tag (MAC)]
              ↓
    Postal worker sees gibberish (encrypted)
    ✓ Maximum security
    ✗ Cannot forward multicast (breaks OSPF)
    ✗ Requires static routes
```

#### **Option 3: Sealed Letter in Labeled Envelope (Tunnel2 — GRE-over-IPsec)**
```
┌─────────────────────────────────────────────────────────────┐
│          TUNNEL2: GRE-over-IPsec (Best of Both Worlds)      │
│    (Encryption + multicast support, more overhead)          │
└─────────────────────────────────────────────────────────────┘

    [Outer IP: R1→R4]
         │
         ├─[GRE Wrapper ← Labeled envelope, postal worker 
         │               can see it's a tunnel]
         │
         ├─[ESP Header]
         │
         ├─[████ ENCRYPTED Inner IP + Payload ████]
         │       (OSPF multicast lives here, just encrypted)
         │
         └─[ESP Trailer + AUTH Tag]
              ↓
    Postal worker sees:
      - Encrypted payload ✓
      - GRE header label ✓ (can forward multicasts!)
    ✓ Security + OSPF routing
    ⚠ Extra overhead (GRE 24B + IPsec 48B = 72B per packet)
```

---

### **The Complete Flow: How a Packet Travels**

```
┌────────────────────────────────────────────────────────────────┐
│                  ALICE SENDS TO BOB                            │
│         (Ping from R1 Tunnel1 to 10.4.4.5)                     │
└────────────────────────────────────────────────────────────────┘

Step 1: Alice prepares the message
┌──────────────────────────────────────────┐
│ Payload: ICMP Echo Request                │
│ Source: 172.16.15.1 (Tunnel1 addr)        │
│ Destination: 10.4.4.5 (Bob's loopback)    │
└──────────────────────────────────────────┘
       ↓ Encrypt with IKEv2-agreed key

Step 2: Wrap in IPsec (ESP)
┌──────────────────────────────────────────────────────────────┐
│ [Outer IP: 1.1.1.1 → 4.4.4.4] ← postal workers care         │
│ [ESP Header + Flags]                                          │
│ [████ ENCRYPTED [Inner: 172.16.15.1→10.4.4.5 + ICMP] ████]  │
│ [ESP Authentication Tag (HMAC-SHA256)]                       │
└──────────────────────────────────────────────────────────────┘
       ↓ Send out toward R3

Step 3: Postal worker (R3) forwards ciphertext
┌──────────────────────────────────────────┐
│ R3 sees only:                             │
│   - Outer IP: 1.1.1.1 → 4.4.4.4           │
│   - Payload: ████████ (encrypted)         │
│ R3 has NO idea what's inside              │
└──────────────────────────────────────────┘
       ↓ Packet reaches R4

Step 4: Bob receives and decrypts
┌──────────────────────────────────────────────────────────────┐
│ R4 sees ESP packet                                            │
│ → Checks: "Do I have an IPsec SA for 1.1.1.1?"              │
│   YES (IKEv2 established one earlier)                        │
│ → Decrypts payload with the agreed key                       │
│ → Verifies HMAC tag (ensures nobody altered it)              │
│ ────────────────────────────────────────┐                    │
│ Decrypted message now visible:          │                    │
│   Inner IP: 172.16.15.1 → 10.4.4.5      │                    │
│   Payload: ICMP Echo Request             │                    │
│ ────────────────────────────────────────┘                    │
│ → Delivers to Loopback2 (10.4.4.5)                           │
└──────────────────────────────────────────────────────────────┘
       ↓ OSPF and host processing

Step 5: Bob replies (reverse path)
┌──────────────────────────────────────────────────────────────┐
│ Reply originates: 10.4.4.5 → 172.16.15.1 (Tunnel1)           │
│ R4 routing: "172.16.15.1? That's Tunnel1"                   │
│ → Apply IPsec profile → Encrypt with same key                │
│ → Send to R1's loopback (4.4.4.4 → 1.1.1.1)                  │
│ Reaches R1, decrypts, reply delivered ✓                       │
└──────────────────────────────────────────────────────────────┘
```

---

### **Why This Matters: The SA (Security Association) State Machine**

```
┌─────────────────────────────────────────────────────────────┐
│            IKEv2 SA LIFECYCLE                               │
└─────────────────────────────────────────────────────────────┘

  No SA Exists
      │
      │ (Traffic arrives on Tunnel1)
      │ Triggers: "I need to talk to 4.4.4.4"
      │
      ▼
  ┌──────────────────────────┐
  │   INIT NEGOTIATION       │
  │ (IKEv2 INIT exchange)    │
  │ Both sides swap proposals│
  └──────────────────────────┘
      │
      ▼
  ┌──────────────────────────┐
  │   KEY GENERATION         │
  │ (DH group 14 computation)│
  │ Shared secret computed   │
  └──────────────────────────┘
      │
      ▼
  ┌──────────────────────────┐
  │   AUTHENTICATION         │
  │ (Pre-shared key verified)│
  │ Both sides prove they    │
  │ have the same PSK        │
  └──────────────────────────┘
      │
      ▼
  ┌──────────────────────────┐
  │   READY ✓                │
  │ (IPsec SA can now use    │
  │  the agreed keys)        │
  └──────────────────────────┘
      │
      ├─ Traffic encrypted/decrypted
      │  Counters incremented
      │
      ├─ If PSK mismatch detected
      │  │
      │  ▼
      │  DELETED (and retry)
      │
      └─ If idle timeout
         │
         ▼
         CLOSED (re-negotiate on next traffic)
```

---

### **Key Takeaways for Lab Success**

**IKEv2 is the handshake, IPsec is the encryption.** IKEv2 runs once when traffic first arrives and establishes agreed-upon keys. IPsec then encrypts every packet. The four-tier hierarchy (proposal → policy → keyring → profile) is Cisco's way of letting you mix-and-match components.

**VTI vs GRE-over-IPsec is a trade-off:** Native IPsec (VTI) is faster and simpler but kills multicast (so no dynamic routing). GRE-over-IPsec wraps the encrypted payload in a GRE header that OSPF sees as a normal link—multicast works, but overhead grows. This lab tests both by running two OSPF processes (2 and 3) over different overlays.

**The PSK mismatch fault is the most common lab failure** because IKEv2 silently fails if the pre-shared key doesn't match—the negotiation just gets deleted. You can't see it in `show crypto` until you send traffic first to trigger the exchange.

**VTI and plain GRE cannot share the same endpoint pair.** A VTI (`tunnel mode ipsec ipv4`) negotiates wildcard traffic selectors (`0.0.0.0/0 ↔ 0.0.0.0/0`) for its source/destination IP pair. Any unencrypted tunnel (like plain GRE) using the same src/dst will have its packets dropped with `%CRYPTO-4-RECVD_PKT_NOT_IPSEC`. This lab uses `Loopback10` as the dedicated IPsec anchor for Tunnel1 and Tunnel2, leaving `Loopback0` exclusively for Tunnel0. See `troubleshooting-reports/INC-20260421-ticket-002.md` for the full incident analysis.

---

## 2. Topology & Scenario

**Scenario:** The network team has completed the GRE overlay from lab-02. Security is now requiring that site-to-site traffic between HQ (R1) and the remote site (R4) be encrypted. The team must evaluate two options: a pure IPsec VTI for simplicity, and a GRE-over-IPsec tunnel that preserves dynamic routing capability. Both will be built simultaneously using the same IKEv2 key infrastructure so the security team can compare them directly. The shared transport router R3 must see only ciphertext — no inner payloads.

```
          ┌────────────────────────────────────────────────────────────────────┐
          │                     HQ Site (R1)                                   │
          │    ┌─────────────────────────────────────────────────────────┐     │
          │    │                      R1                                  │     │
          │    │               (HQ / Tunnel Head)                        │     │
          │    │ Lo0: 1.1.1.1    Lo10: 10.10.1.1                          │     │
          │    │ Tunnel0: 172.16.14.1   (plain GRE, src Lo0)             │     │
          │    │ Tunnel1: 172.16.15.1   (IPsec VTI, src Lo10)            │     │
          │    │ Tunnel2: 172.16.16.1   (GRE-over-IPsec, src Lo10)       │     │
          │    └───────┬─────────────────────────────────┬───────────────┘     │
          │            │ Gi0/0                           │ Gi0/1               │
          │            │ 10.0.13.1/30                    │ 10.0.12.1/30        │
          └────────────┼─────────────────────────────────┼─────────────────────┘
                       │                                 │
                       │ 10.0.13.2/30                    │ 10.0.12.2/30
                       │ Gi0/0                           │ Gi0/1
          ┌────────────┴───────────┐         ┌───────────┴────────────────┐
          │           R3           │         │            R2              │
          │   (Transport / Core)   │         │      (Branch Router)       │
          │    Lo0: 3.3.3.3        │         │    Lo0: 2.2.2.2            │
          └──────────┬─────────────┘         └────────────────────────────┘
                     │ Gi0/2
                     │ 10.0.34.1/30
                     │
                     │ 10.0.34.2/30
                     │ Gi0/0
          ┌──────────┴─────────────────────────────────────────────────────────┐
          │                           R4                                        │
          │                   (Remote Site Router)                              │
          │  Lo0: 4.4.4.4    Lo10: 10.10.4.4                                    │
          │  Lo1: 10.4.4.4   Lo2: 10.4.4.5   Lo3: 10.4.4.6                   │
          │  Tunnel0: 172.16.14.2 (src Lo0)                                   │
          │  Tunnel1: 172.16.15.2 (src Lo10)  Tunnel2: 172.16.16.2 (src Lo10)│
          └────────────────────────────────────────────────────────────────────┘

  Overlay paths (all traverse R3 underlay):
  ┌──────────────────────────────────────────────────────────────────────────┐
  │  Tunnel0  ─ ─ ─ ─ plain GRE        ─ ─ ─ ─  OSPF process 2 over it     │
  │  Tunnel1  ═══════ IPsec VTI         ═══════  static route to 10.4.4.5   │
  │  Tunnel2  ════╦══ GRE-over-IPsec    ════╦══  OSPF process 3 over it     │
  │               ╚══ encrypted GRE     ════╝                                │
  └──────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Hardware & Environment Specifications

**Platform:** EVE-NG (IOSv 15.9(3)M6) — IPsec/IKEv2 feature set included

| Link | Device A | Interface | IP A | Device B | Interface | IP B | Subnet |
|------|----------|-----------|------|----------|-----------|------|--------|
| L1 | R1 | Gi0/0 | 10.0.13.1/30 | R3 | Gi0/0 | 10.0.13.2/30 | 10.0.13.0/30 |
| L2 | R2 | Gi0/0 | 10.0.23.1/30 | R3 | Gi0/1 | 10.0.23.2/30 | 10.0.23.0/30 |
| L3 | R1 | Gi0/1 | 10.0.12.1/30 | R2 | Gi0/1 | 10.0.12.2/30 | 10.0.12.0/30 |
| L4 | R1 | Gi0/2 | 192.168.1.1/24 | PC1 | e0 | 192.168.1.10/24 | 192.168.1.0/24 |
| L5 | R2 | Gi0/2 | 192.168.2.1/24 | PC2 | e0 | 192.168.2.10/24 | 192.168.2.0/24 |
| L6 | R3 | Gi0/2 | 10.0.34.1/30 | R4 | Gi0/0 | 10.0.34.2/30 | 10.0.34.0/30 |

**Console Access Table:**

| Device | Port | Connection Command |
|--------|------|--------------------|
| R1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R3 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| R4 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| PC1 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |
| PC2 | (see EVE-NG UI) | `telnet <eve-ng-ip> <port>` |

---

## 4. Base Configuration

The following is pre-loaded from lab-02 solutions when you run `setup_lab.py`:

**Pre-configured on all devices:**
- Hostname and interface IP addressing (all physical links and loopbacks)
- OSPF process 1 (underlay) — all global-table links and loopbacks in area 0
- `ipv6 unicast-routing` enabled

**Pre-configured on R1 and R4:**
- Tunnel0 (plain GRE) between R1 Lo0 (1.1.1.1) and R4 Lo0 (4.4.4.4)
  - R1 Tunnel0: 172.16.14.1/30, IPv6 2001:db8:14::1/64
  - R4 Tunnel0: 172.16.14.2/30, IPv6 2001:db8:14::2/64
  - ip mtu 1400, ip tcp adjust-mss 1360
- OSPF process 2 over Tunnel0 — R4 Loopback1 (10.4.4.4/32) reachable from R1 via this overlay

**Pre-configured on R4 only:**
- Loopback1: 10.4.4.4/32 (plain GRE test prefix — already in OSPF process 2)

**NOT pre-configured (your lab objectives):**
- IKEv2 crypto infrastructure (proposal, policy, keyring, profile)
- IPsec transform set and IPsec profile
- Tunnel1 — IPsec VTI
- Tunnel2 — GRE-over-IPsec
- Loopback2 on R4 (10.4.4.5/32) — IPsec VTI test prefix
- Loopback3 on R4 (10.4.4.6/32) — GRE-over-IPsec test prefix
- OSPF process 3 over Tunnel2
- Static route to 10.4.4.5 via Tunnel1

---

## 5. Lab Challenge: Core Implementation

### Task 1: Build the IKEv2 Key Infrastructure

**Step 0 — Create the IPsec tunnel anchor loopback**

Before configuring IKEv2, create `Loopback10` on both R1 and R4. Tunnel1 (VTI) and Tunnel2 (GRE-over-IPsec) will source from this interface. Using a dedicated loopback ensures the VTI's wildcard IPsec SA covers only the `10.10.1.1 ↔ 10.10.4.4` endpoint pair — leaving Tunnel0's `1.1.1.1 ↔ 4.4.4.4` path unaffected by IPsec policy.

- R1: `interface Loopback10`, IP address `10.10.1.1/32`; add `network 10.10.1.1 0.0.0.0 area 0` under OSPF process 1
- R4: `interface Loopback10`, IP address `10.10.4.4/32`; add `network 10.10.4.4 0.0.0.0 area 0` under OSPF process 1

Verify Lo10 is reachable before proceeding: `ping 10.10.4.4 source Loopback10` from R1 should return 5/5.

> **Design note:** This is the unique-loopback pattern required for mixed plain/encrypted overlay topologies. See `troubleshooting-reports/INC-20260421-ticket-002.md` for the failure mode this prevents.

**Step 1 — Configure IKEv2 proposal, policy, keyring, and profile** on both R1 and R4. Use the following parameters:

- Proposal name: `IKEv2-PROP`; encryption: AES-256-CBC; integrity: SHA-256; DH group: 14
- Policy name: `IKEv2-POL`; reference the proposal above
- Keyring name: `IKEv2-KEYRING`; peer name on R1 is `R4` (address `10.10.4.4`); peer name on R4 is `R1` (address `10.10.1.1`)
- Pre-shared key on both sides: `LAB-PSK-2026`
- Profile name: `IKEv2-PROFILE`; match the remote peer by its Loopback10 /32; use pre-share authentication on both local and remote ends; reference the keyring above

**Verification:** `show crypto ikev2 proposal` on both routers should list `IKEv2-PROP` with correct algorithms. No IKEv2 SA will form yet — the profile is not attached to a tunnel interface.

---

### Task 2: Configure the IPsec Transform Set and Profile

Configure the data-plane encryption parameters that will be applied to both tunnels.

- Transform set name: `TS-AES256`; use ESP with AES-256 encryption and SHA-256 HMAC; mode: tunnel
- IPsec profile name: `IPSEC-PROFILE`; reference the transform set and the IKEv2 profile above

**Verification:** `show crypto ipsec transform-set` should list `TS-AES256` with both ESP-AES 256 and ESP-SHA256-HMAC.

---

### Task 3: Configure the IPsec VTI (Tunnel1)

Configure a Virtual Tunnel Interface between R1 and R4 for encrypted, unicast-only traffic.

- Interface: Tunnel1 on both routers
- Tunnel subnet: 172.16.15.0/30 (R1 takes .1, R4 takes .2)
- Source: Loopback10 on each router; destination: the far-end Loopback10 IP (`10.10.4.4` from R1, `10.10.1.1` from R4)
- Set the tunnel mode to native IPsec IPv4 (not GRE)
- Apply the IPsec profile to the tunnel interface

Also add a test prefix on R4: Loopback2 with the address 10.4.4.5/32. On R1, add a static host route pointing 10.4.4.5/32 toward R4's Tunnel1 address (172.16.15.2).

**Verification:** `show interface Tunnel1` should show line protocol UP. `show crypto ikev2 sa` should show a READY SA after sending traffic. `ping 10.4.4.5 source Tunnel1` from R1 should succeed and `show crypto ipsec sa` should show non-zero encrypted **and** decrypted packet counters. (Using source Tunnel1 ensures the reply is addressed to 172.16.15.1 — a connected route on R4 via Tunnel1 — so both directions are encrypted.)

---

### Task 4: Configure GRE over IPsec (Tunnel2)

Configure a GRE tunnel protected by the same IPsec profile on both R1 and R4.

- Interface: Tunnel2 on both routers
- Tunnel subnet: 172.16.16.0/30 (R1 takes .1, R4 takes .2); add IPv6 2001:db8:16::1/64 (R1) and ::2/64 (R4)
- Source: Loopback10; destination: far-end Loopback10 (`10.10.4.4` from R1, `10.10.1.1` from R4)
- Tunnel mode: GRE IP (not IPsec)
- Apply the IPsec profile as tunnel protection on both sides
- Set ip mtu 1400 and ip tcp adjust-mss 1360 (GRE + IPsec overhead)
- Set OSPF network type to point-to-point on the tunnel interface

**Verification:** `show interface Tunnel2` line protocol UP. `show crypto ipsec sa` should show a second SA with encrypted packet counters (separate from Tunnel1). Unlike Tunnel1, no static route is needed here — OSPF will handle it.

---

### Task 5: Run OSPF Process 3 over Tunnel2

Configure a dedicated OSPF process over the GRE-over-IPsec overlay to prove dynamic routing works through an encrypted GRE tunnel.

- Use OSPF process 3 on both R1 and R4
- Router ID: use the existing Loopback0 addresses (1.1.1.1 on R1, 4.4.4.4 on R4)
- Advertise the Tunnel2 subnet (172.16.16.0/30) in area 0 on both routers
- On R4, add Loopback3 (10.4.4.6/32) and advertise it in OSPF process 3 area 0

**Verification:** `show ip ospf neighbor` on Tunnel2 should show a FULL adjacency with R4. `show ip route ospf` on R1 should show 10.4.4.6/32 via 172.16.16.2. `ping 10.4.4.6 source Tunnel2` from R1 should succeed and `show crypto ipsec sa` on Tunnel2 should show non-zero encrypted **and** decrypted counters. (Using source Tunnel2 ensures R4's reply is addressed to 172.16.16.1 — a connected route via Tunnel2 — so both directions traverse the encrypted overlay.)

---

### Task 6: Verify the Three Overlays Are Independent

Confirm that each test prefix is reachable via exactly one overlay, and that R3 sees only encapsulated/encrypted traffic.

- From R1, ping 10.4.4.4 — should succeed via Tunnel0 (plain GRE, OSPF process 2)
- From R1, ping 10.4.4.5 — should succeed via Tunnel1 (IPsec VTI, static route)
- From R1, ping 10.4.4.6 — should succeed via Tunnel2 (GRE-over-IPsec, OSPF process 3)
- On R3, run `show ip route` — 10.4.4.4, 10.4.4.5, and 10.4.4.6 should NOT appear (they are overlay routes invisible to the transport)

**Verification:** `show ip route 10.4.4.4`, `show ip route 10.4.4.5`, `show ip route 10.4.4.6` on R1 should each show a different next-hop (Tunnel0, Tunnel1, Tunnel2 respectively). R3 `show ip route` should not contain any of these /32 prefixes.

---

## 6. Verification & Analysis

### Task 1 & 2 — IKEv2 and IPsec Profile

```
R1# show crypto ikev2 proposal
IKEv2 proposal: IKEv2-PROP
     Encryption : AES-CBC-256          ! ← must be AES-256
     Integrity  : SHA256               ! ← must be SHA256
     PRF        : SHA256
     DH Group   : DH_GROUP_2048_MODP/Group 14   ! ← DH group 14

R1# show crypto ipsec transform-set
Transform set default: { esp-aes esp-sha-hmac  }
   will negotiate = { Transport,  },

Transform set TS-AES256: { esp-256-aes esp-sha256-hmac  }   ! ← correct TS
   will negotiate = { Tunnel,  },                            ! ← mode tunnel
```

### Task 3 — IPsec VTI (Tunnel1)

```
R1# show interface Tunnel1
Tunnel1 is up, line protocol is up           ! ← both must be up
  Hardware is Tunnel
  Internet address is 172.16.15.1/30         ! ← correct address
  Tunnel source 10.10.1.1 (Loopback10), destination 10.10.4.4
  Tunnel protocol/transport IPSEC/IP         ! ← tunnel mode ipsec ipv4

R1# show crypto ikev2 sa
IPv4 Crypto IKEv2  SA

Tunnel-id Local                 Remote                fvrf/ivrf            Status
1         10.10.1.1/500         10.10.4.4/500         none/none            READY    ! ← READY means IKEv2 SA up

! Populate counters with: ping 10.4.4.5 source Tunnel1
R1# show crypto ipsec sa
interface: Tunnel1
    Crypto map tag: Tunnel1-head-0, local addr 10.10.1.1
   protected vrf: (none)
   local  ident (addr/mask/prot/port): (0.0.0.0/0.0.0.0/0/0)
   remote ident (addr/mask/prot/port): (0.0.0.0/0.0.0.0/0/0)
   current_peer 10.10.4.4 port 500
    #pkts encaps: 5, #pkts encrypt: 5, #pkts digest: 5   ! ← non-zero after ping source Tunnel1
    #pkts decaps: 5, #pkts decrypt: 5, #pkts verify: 5   ! ← non-zero: reply returns through Tunnel1
```

### Task 4 — GRE-over-IPsec (Tunnel2)

```
R1# show interface Tunnel2
Tunnel2 is up, line protocol is up           ! ← both must be up
  Internet address is 172.16.16.1/30
  Tunnel source 10.10.1.1 (Loopback10), destination 10.10.4.4
  Tunnel protocol/transport GRE/IP           ! ← still GRE, NOT IPsec here
  ...
  Tunnel protection via IPSec (profile "IPSEC-PROFILE")   ! ← profile applied
```

### Task 5 — OSPF Process 3 over Tunnel2

```
R1# show ip ospf neighbor
Neighbor ID     Pri   State           Dead Time   Address         Interface
4.4.4.4           0   FULL/  -        00:00:38    172.16.16.2     Tunnel2   ! ← FULL on Tunnel2

R1# show ip route ospf
      10.0.0.0/8 is variably subnetted
O        10.4.4.6/32 [110/11112] via 172.16.16.2, 00:00:30, Tunnel2   ! ← learned via Tunnel2
```

### Task 6 — Three Independent Overlays

```
R1# show ip route 10.4.4.4
Routing entry for 10.4.4.4/32
  Known via "ospf 2"                      ! ← OSPF process 2, plain GRE
  ...via 172.16.14.2, Tunnel0             ! ← next-hop on Tunnel0

R1# show ip route 10.4.4.5
Routing entry for 10.4.4.5/32
  Known via "static"                      ! ← static route
  ...via 172.16.15.2, Tunnel1             ! ← next-hop on Tunnel1

R1# show ip route 10.4.4.6
Routing entry for 10.4.4.6/32
  Known via "ospf 3"                      ! ← OSPF process 3, GRE-over-IPsec
  ...via 172.16.16.2, Tunnel2             ! ← next-hop on Tunnel2

R3# show ip route
[... underlay routes only — no 10.4.4.x entries ...]   ! ← overlay prefixes invisible to transport
```

---

## 7. Verification Cheatsheet

### IKEv2 Configuration

```
crypto ikev2 proposal <name>
 encryption aes-cbc-256
 integrity sha256
 group 14

crypto ikev2 policy <name>
 proposal <proposal-name>

crypto ikev2 keyring <name>
 peer <label>
  address <peer-loopback-ip>
  pre-shared-key <key>

crypto ikev2 profile <name>
 match identity remote address <peer-ip> 255.255.255.255
 authentication remote pre-share
 authentication local pre-share
 keyring local <keyring-name>
```

| Command | Purpose |
|---------|---------|
| `crypto ikev2 proposal <name>` | Define IKE encryption/integrity/DH parameters |
| `group 14` | DH group 2048-bit MODP — exam-relevant minimum for modern deployments |
| `match identity remote address` | Restrict profile to a specific peer IP |
| `authentication remote pre-share` | Remote peer authenticates with PSK |

> **Exam tip:** IKEv2 replaces both Phase 1 and Phase 2 from IKEv1. The IKEv2 profile is the single config object that controls peer identity, authentication, and keyring — there is no separate `isakmp policy`.

### IPsec Transform Set and Profile

```
crypto ipsec transform-set <name> esp-aes 256 esp-sha256-hmac
 mode tunnel

crypto ipsec profile <name>
 set transform-set <ts-name>
 set ikev2-profile <ikev2-profile-name>
```

| Command | Purpose |
|---------|---------|
| `esp-aes 256` | AES-256 data-plane encryption |
| `esp-sha256-hmac` | SHA-256 data integrity |
| `mode tunnel` | Encrypt entire IP packet (vs. transport mode which only encrypts payload) |
| `set ikev2-profile` | Bind IKEv2 key exchange to this data-plane profile |

### Tunnel Interface Configuration

```
interface Tunnel1                             ! IPsec VTI
 ip address 172.16.15.1 255.255.255.252
 tunnel source Loopback10
 tunnel destination 10.10.4.4
 tunnel mode ipsec ipv4
 tunnel protection ipsec profile IPSEC-PROFILE

interface Tunnel2                             ! GRE-over-IPsec
 ip address 172.16.16.1 255.255.255.252
 ip mtu 1400
 ip tcp adjust-mss 1360
 tunnel source Loopback10
 tunnel destination 10.10.4.4
 tunnel mode gre ip
 tunnel protection ipsec profile IPSEC-PROFILE
 ip ospf network point-to-point
```

| Command | Purpose |
|---------|---------|
| `tunnel mode ipsec ipv4` | Pure IPsec VTI — encrypted, no multicast |
| `tunnel mode gre ip` | GRE tunnel — add `tunnel protection` for encryption |
| `tunnel protection ipsec profile` | Apply IPsec to a GRE tunnel (GRE-over-IPsec) |
| `ip mtu 1400` | Reduce MTU to avoid fragmentation (GRE 24B + IPsec ~48B overhead) |

> **Exam tip:** `tunnel mode ipsec ipv4` and `tunnel protection ipsec profile` are mutually exclusive patterns. Putting `tunnel protection` on a GRE tunnel makes it GRE-over-IPsec. Putting `tunnel mode ipsec ipv4` makes it a pure IPsec VTI (no GRE wrapper).

### Verification Commands

| Command | What to Look For |
|---------|-----------------|
| `show crypto ikev2 sa` | Status = READY; both peers listed |
| `show crypto ikev2 sa detail` | Encryption/integrity algorithms match proposal |
| `show crypto ipsec sa` | `#pkts encrypt` and `#pkts decrypt` non-zero after traffic |
| `show interface Tunnel1` | Line protocol UP; `Tunnel protocol/transport IPSEC/IP` |
| `show interface Tunnel2` | Line protocol UP; `Tunnel protocol/transport GRE/IP`; `Tunnel protection via IPSec` |
| `show ip ospf neighbor` | Neighbor on Tunnel2 shows FULL/- (no DR election on p2p) |
| `show ip route ospf` | 10.4.4.6/32 via Tunnel2 (OSPF process 3) |
| `show ip route 10.4.4.5` | via 172.16.15.2, Tunnel1 (static) |
| `show crypto ikev2 stats` | Counts of successful IKEv2 exchanges |

### Common IPsec Failure Causes

| Symptom | Likely Cause |
|---------|-------------|
| Tunnel1/2 line protocol stays down | PSK mismatch — check both sides with `show crypto ikev2 proposal` |
| `show crypto ikev2 sa` shows no output | No traffic triggered IKE — send a ping first |
| IKEv2 SA shows DELETED immediately | PSK mismatch or proposal algorithm mismatch |
| Tunnel2 UP but OSPF neighbors won't form | `tunnel mode ipsec ipv4` used instead of `tunnel mode gre ip` + protection |
| OSPF forms on Tunnel2 but routes missing | Network statement missing for tunnel subnet or test prefix in OSPF process 3 |
| Ping to 10.4.4.5 fails from R1 | Static route missing (`ip route 10.4.4.5 255.255.255.255 172.16.15.2`) |

---

## 8. Solutions (Spoiler Alert!)

> Try to complete the lab challenge without looking at these steps first!

### Tasks 1 & 2: IKEv2 Infrastructure and IPsec Profile

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1 — Step 0: IPsec tunnel anchor
interface Loopback10
 description R1 IPsec tunnel anchor (dedicated to encrypted overlays)
 ip address 10.10.1.1 255.255.255.255
!
router ospf 1
 network 10.10.1.1 0.0.0.0 area 0

! R1 — IKEv2 proposal, policy, keyring, profile + IPsec profile
crypto ikev2 proposal IKEv2-PROP
 encryption aes-cbc-256
 integrity sha256
 group 14
!
crypto ikev2 policy IKEv2-POL
 proposal IKEv2-PROP
!
crypto ikev2 keyring IKEv2-KEYRING
 peer R4
  address 10.10.4.4
  pre-shared-key LAB-PSK-2026
!
crypto ikev2 profile IKEv2-PROFILE
 match identity remote address 10.10.4.4 255.255.255.255
 authentication remote pre-share
 authentication local pre-share
 keyring local IKEv2-KEYRING
!
crypto ipsec transform-set TS-AES256 esp-aes 256 esp-sha256-hmac
 mode tunnel
!
crypto ipsec profile IPSEC-PROFILE
 set transform-set TS-AES256
 set ikev2-profile IKEv2-PROFILE
```
</details>

<details>
<summary>Click to view R4 Configuration</summary>

```bash
! R4 — Step 0: IPsec tunnel anchor
interface Loopback10
 description R4 IPsec tunnel anchor (dedicated to encrypted overlays)
 ip address 10.10.4.4 255.255.255.255
!
router ospf 1
 network 10.10.4.4 0.0.0.0 area 0

! R4 — mirror of R1 with swapped peer address
crypto ikev2 proposal IKEv2-PROP
 encryption aes-cbc-256
 integrity sha256
 group 14
!
crypto ikev2 policy IKEv2-POL
 proposal IKEv2-PROP
!
crypto ikev2 keyring IKEv2-KEYRING
 peer R1
  address 10.10.1.1
  pre-shared-key LAB-PSK-2026
!
crypto ikev2 profile IKEv2-PROFILE
 match identity remote address 10.10.1.1 255.255.255.255
 authentication remote pre-share
 authentication local pre-share
 keyring local IKEv2-KEYRING
!
crypto ipsec transform-set TS-AES256 esp-aes 256 esp-sha256-hmac
 mode tunnel
!
crypto ipsec profile IPSEC-PROFILE
 set transform-set TS-AES256
 set ikev2-profile IKEv2-PROFILE
```
</details>

### Task 3: IPsec VTI (Tunnel1)

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1 — Tunnel1 IPsec VTI + static route for test prefix
interface Tunnel1
 ip address 172.16.15.1 255.255.255.252
 tunnel source Loopback10
 tunnel destination 10.10.4.4
 tunnel mode ipsec ipv4
 tunnel protection ipsec profile IPSEC-PROFILE
 no shutdown
!
ip route 10.4.4.5 255.255.255.255 172.16.15.2
```
</details>

<details>
<summary>Click to view R4 Configuration</summary>

```bash
! R4 — Tunnel1 + Loopback2 test prefix
interface Loopback2
 ip address 10.4.4.5 255.255.255.255
!
interface Tunnel1
 ip address 172.16.15.2 255.255.255.252
 tunnel source Loopback10
 tunnel destination 10.10.1.1
 tunnel mode ipsec ipv4
 tunnel protection ipsec profile IPSEC-PROFILE
 no shutdown
```
</details>

### Tasks 4 & 5: GRE-over-IPsec (Tunnel2) + OSPF Process 3

<details>
<summary>Click to view R1 Configuration</summary>

```bash
! R1 — Tunnel2 GRE-over-IPsec + OSPF process 3
interface Tunnel2
 ip address 172.16.16.1 255.255.255.252
 ipv6 address 2001:db8:16::1/64
 ip mtu 1400
 ip tcp adjust-mss 1360
 tunnel source Loopback10
 tunnel destination 10.10.4.4
 tunnel mode gre ip
 tunnel protection ipsec profile IPSEC-PROFILE
 ip ospf network point-to-point
 no shutdown
!
router ospf 3
 router-id 1.1.1.1
 network 172.16.16.0 0.0.0.3 area 0
```
</details>

<details>
<summary>Click to view R4 Configuration</summary>

```bash
! R4 — Tunnel2 + Lo3 test prefix + OSPF process 3
interface Loopback3
 ip address 10.4.4.6 255.255.255.255
!
interface Tunnel2
 ip address 172.16.16.2 255.255.255.252
 ipv6 address 2001:db8:16::2/64
 ip mtu 1400
 ip tcp adjust-mss 1360
 tunnel source Loopback10
 tunnel destination 10.10.1.1
 tunnel mode gre ip
 tunnel protection ipsec profile IPSEC-PROFILE
 ip ospf network point-to-point
 no shutdown
!
router ospf 3
 router-id 4.4.4.4
 network 172.16.16.0 0.0.0.3 area 0
 network 10.4.4.6 0.0.0.0 area 0
```
</details>

<details>
<summary>Click to view Verification Commands</summary>

```bash
show crypto ikev2 sa
show crypto ipsec sa
show ip ospf neighbor
show ip route ospf
ping 10.4.4.5 source Tunnel1
ping 10.4.4.6 source Tunnel2
show ip route 10.4.4.4
show ip route 10.4.4.5
show ip route 10.4.4.6
```
</details>

---

## 9. Troubleshooting Scenarios

Each ticket simulates a real-world fault. Inject the fault first, then diagnose and fix using only show commands.

### Workflow

```bash
python3 setup_lab.py                                   # reset to known-good
python3 scripts/fault-injection/inject_scenario_01.py  # Ticket 1
python3 scripts/fault-injection/apply_solution.py      # restore
```

---

### Ticket 1 — Both Encrypted Tunnels Refuse to Come Up

The network monitoring system reports that Tunnel1 and Tunnel2 are down. The plain GRE Tunnel0 is still operational. The change log shows a recent key rotation in the IKEv2 keyring on both sides.

**Inject:** `python3 scripts/fault-injection/inject_scenario_01.py`

**Success criteria:** Tunnel1 and Tunnel2 line protocol UP; `show crypto ikev2 sa` shows READY on both routers; pings to 10.4.4.5 and 10.4.4.6 succeed from R1.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! Step 1 — Check IKEv2 SA state
R1# show crypto ikev2 sa
! If no output, IKEv2 has not even attempted to negotiate.
! Send traffic to trigger IKE: ping 10.4.4.5 source loopback0

R1# show crypto ikev2 sa detail
! Look for AUTH_FAILED or DELETE in the status column

! Step 2 — Check IKEv2 diagnostics
R1# debug crypto ikev2 error
R1# ping 10.4.4.5 source loopback0
! "IKEv2:(SESSION ID = 1):Failed to verify PSK" → PSK mismatch

! Step 3 — Compare keyring on both sides
R1# show running-config | section ikev2 keyring
R4# show running-config | section ikev2 keyring
! The pre-shared-key values will differ
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! Fix on R1 — update PSK to match R4
crypto ikev2 keyring IKEv2-KEYRING
 peer R4
  pre-shared-key LAB-PSK-2026

! Fix on R4 (if also changed)
crypto ikev2 keyring IKEv2-KEYRING
 peer R1
  pre-shared-key LAB-PSK-2026

! Verify
R1# clear crypto ikev2 sa
R1# ping 10.4.4.5 source Tunnel1
R1# show crypto ikev2 sa
! Should show READY
```
</details>

---

### Ticket 2 — Tunnel2 Is Up but OSPF Neighbors Never Form

A junior engineer reports that Tunnel2 shows line protocol UP on both sides, but `show ip ospf neighbor` never shows R4 on the Tunnel2 interface. Tunnel1 and Tunnel0 are working correctly.

**Inject:** `python3 scripts/fault-injection/inject_scenario_02.py`

**Success criteria:** `show ip ospf neighbor` on R1 shows R4 in FULL state on Tunnel2; `show ip route ospf` shows 10.4.4.6/32 learned via Tunnel2; ping to 10.4.4.6 succeeds.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! Step 1 — Check tunnel mode on Tunnel2
R1# show interface Tunnel2
! Look at "Tunnel protocol/transport" line
! If it shows "IPSEC/IP" instead of "GRE/IP" → tunnel mode is wrong

! Step 2 — Confirm the problem
! IPsec VTI (tunnel mode ipsec ipv4) does not support multicast.
! OSPF uses 224.0.0.5/224.0.0.6 for hellos — these are multicast.
! On an IPsec VTI, multicast is not forwarded, so hellos are dropped.

! Step 3 — Check running config on R1
R1# show running-config interface Tunnel2
! If "tunnel mode ipsec ipv4" is present (and no "tunnel protection") → wrong mode
! Correct config should show: tunnel mode gre ip + tunnel protection ipsec profile
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! Fix on R1 — correct the tunnel mode
interface Tunnel2
 tunnel mode gre ip
 tunnel protection ipsec profile IPSEC-PROFILE

! Fix on R4 — same correction
interface Tunnel2
 tunnel mode gre ip
 tunnel protection ipsec profile IPSEC-PROFILE

! Verify
R1# show interface Tunnel2
! "Tunnel protocol/transport GRE/IP" and "Tunnel protection via IPSec"
R1# show ip ospf neighbor
! R4 should appear on Tunnel2 within ~40 seconds
```
</details>

---

### Ticket 3 — GRE-over-IPsec Tunnel Is Encrypted but 10.4.4.6 Is Unreachable

The security audit confirms that Tunnel2 traffic is encrypted (IPsec SA counters are increasing). OSPF neighbors on Tunnel2 also show FULL. However, `ping 10.4.4.6 source loopback0` from R1 fails and `show ip route 10.4.4.6` shows no entry.

**Inject:** `python3 scripts/fault-injection/inject_scenario_03.py`

**Success criteria:** `show ip route 10.4.4.6` on R1 shows the prefix via OSPF process 3 through Tunnel2; ping to 10.4.4.6 succeeds.

<details>
<summary>Click to view Diagnosis Steps</summary>

```bash
! Step 1 — Confirm OSPF process 3 neighbors and routes
R1# show ip ospf 3 neighbor
! Neighbor shows FULL — that confirms Tunnel2 and OSPF 3 are working

R1# show ip route ospf 3
! If 10.4.4.6 is missing despite FULL neighbor → R4 is not advertising it

! Step 2 — Check R4 OSPF process 3 config
R4# show ip ospf 3 database
! 10.4.4.6/32 LSA missing → network statement not configured on R4

! Step 3 — Check R4 running config
R4# show running-config | section ospf 3
! The "network 10.4.4.6 0.0.0.0 area 0" line will be absent
```
</details>

<details>
<summary>Click to view Fix</summary>

```bash
! Fix on R4 — add the missing network statement
router ospf 3
 network 10.4.4.6 0.0.0.0 area 0

! Verify on R1
R1# show ip route ospf
! 10.4.4.6/32 should appear via 172.16.16.2, Tunnel2
R1# ping 10.4.4.6 source Tunnel2
```
</details>

---

## 10. Lab Completion Checklist

### Core Implementation

- [ ] IKEv2 proposal `IKEv2-PROP` configured with AES-256-CBC, SHA-256, DH group 14
- [ ] IKEv2 policy `IKEv2-POL` referencing `IKEv2-PROP`
- [ ] IKEv2 keyring `IKEv2-KEYRING` with peer PSK on both R1 and R4
- [ ] IKEv2 profile `IKEv2-PROFILE` with `match identity remote address` and pre-share auth
- [ ] IPsec transform set `TS-AES256` with esp-aes 256 + esp-sha256-hmac, mode tunnel
- [ ] IPsec profile `IPSEC-PROFILE` referencing transform set and IKEv2 profile
- [ ] Tunnel1 (IPsec VTI) UP on R1 and R4, `show crypto ikev2 sa` shows READY
- [ ] `show crypto ipsec sa` shows non-zero encrypt/decrypt counters after ping to 10.4.4.5
- [ ] Tunnel2 (GRE-over-IPsec) UP on R1 and R4, `Tunnel protocol/transport GRE/IP` + protection
- [ ] OSPF process 3 forming FULL adjacency on Tunnel2 between R1 and R4
- [ ] `show ip route 10.4.4.4` → via Tunnel0 (plain GRE, OSPF process 2)
- [ ] `show ip route 10.4.4.5` → via Tunnel1 (IPsec VTI, static)
- [ ] `show ip route 10.4.4.6` → via Tunnel2 (GRE-over-IPsec, OSPF process 3)
- [ ] R3 `show ip route` does not contain 10.4.4.4, 10.4.4.5, or 10.4.4.6

### Troubleshooting

- [ ] Ticket 1: Diagnosed PSK mismatch; corrected keyring on both sides; IKEv2 SA shows READY
- [ ] Ticket 2: Diagnosed wrong tunnel mode on Tunnel2; corrected to GRE + protection; OSPF FULL
- [ ] Ticket 3: Diagnosed missing OSPF process 3 network statement on R4; added; 10.4.4.6 reachable
