# CCIE Enterprise Infrastructure Lab Design — Research Notes

**Created:** 2026-04-19
**Context:** Research conducted while building CCNP ENCOR labs, capturing the approach and decisions for when CCIE EI lab work begins.
**Future repo:** `ccie-ei-labs` (separate from `ccnp-encor-labs`; see §7).

---

## 1. Purpose

Decide how to structure a CCIE Enterprise Infrastructure lab build, given an existing working pattern for CCNP ENCOR (per-technology labs generated from blueprints via `spec-creator` -> `lab-assembler` -> `fault-injector`). Two questions were in scope:

1. What does CCIE test in a given technology that CCNP ENCOR/ENARSI does not?
2. Should CCIE labs be per-domain (like CCNP) or a single mega-topology (like traditional CCIE workbooks)?

---

## 2. Scope of research

- BGP: gap between CCNP ENCOR + ENARSI coverage and CCIE EI v1.1 (with relevant SP v1.1 overlap)
- OSPF: same comparison
- Switching (L2, STP/MST, PVLAN, MC-LAG, VXLAN/EVPN): same comparison
- Lab architecture: per-technology vs single mega-topology
- Repository structure: one repo vs tier-per-repo

---

## 3. BGP — what CCIE adds over CCNP

**CCNP already covers:** eBGP/iBGP peering, path attributes (AS-path, LOCAL_PREF, MED, weight, origin), route reflectors, confederations (ENARSI), prefix/AS-path filtering, communities, conditional advertisement, BGP for IPv6, basic peer groups.

**CCIE adds:**

| Area | CCIE-specific content |
|---|---|
| Address families | VPNv4/VPNv6 (L3VPN), L2VPN EVPN, MVPN (MDT SAFI), 6PE/6VPE, Link-State AF (BGP-LS), Flowspec AF |
| Scaling | Peer **session** vs peer **policy** templates (not just peer groups), dynamic neighbors, multi-session TCP transport, BGP PIC edge/core |
| Convergence | Add-Path, Best External, Slow-Peer Detection, LLGR, diverse path, Optimal Route Reflection (ORR) |
| Policy depth | Hierarchical route-maps with `continue`, matching on extended/large communities, AIGP attribute, conditional match on RPKI state |
| Inter-domain | Inter-AS MPLS options A/B/C, Carrier-Supporting-Carrier, RT-Constraint (RFC 4684), Route Target rewrite, CsC + Inter-AS combinations |
| Segment Routing | BGP-LU (RFC 8277), SR Policy via BGP (draft-ietf-idr-sr-policy), Prefix-SID distribution through BGP-LS |
| Operations | BGP Monitoring Protocol (BMP), selective RIB download, dampening tuning, graceful-shutdown community (RFC 8326), TTL security beyond single-hop |
| EVPN | Type 1-5 routes, ESI/multihoming, ARP suppression, MAC mobility, L3 VNI with symmetric IRB |

---

## 4. OSPF — what CCIE adds over CCNP

**CCNP already covers:** areas, LSA types 1-7, virtual links, summarization, authentication, OSPFv3, basic redistribution.

**CCIE adds:**

- **Fast convergence engineering:** SPF throttle timers (`spf-start`, `spf-hold`, `spf-max`), LSA pacing, incremental/partial SPF, BFD single-hop and echo mode.
- **Loop-free alternates:** LFA, remote LFA (rLFA), **TI-LFA** with Segment Routing (dominant modern protection mechanism).
- **OSPF-SR extensions:** Prefix-SID and adjacency-SID advertisement in opaque LSAs (RFC 8665).
- **L3VPN interactions:** **sham-link** for backdoor prevention, Domain-ID manipulation, down-bit and VPN-route-tag loop prevention, `capability vrf-lite`.
- **NSSA deep dive:** P-bit manipulation, type-7-to-5 translation election, `no-summary` vs `no-redistribution`, best-ABR selection (RFC 3509).
- **Multi-process interaction:** two OSPF processes on the same router redistributing with administrative distance and tag-based loop prevention — a canonical CCIE trap.
- **Platform features:** prefix suppression, TTL security, NSR/GR/NSF, demand circuits, OSPF over DMVPN Phase 3 tuning (network type, priority, hello/dead).
- **Redistribution artistry:** mutual redistribution between OSPF <-> BGP <-> EIGRP using tags; CCNP teaches the concept, CCIE tests four-way mutual redistribution with suboptimal-routing correction.

---

## 5. Switching (L2 / Fabric) — what CCIE adds over CCNP

**CCNP already covers:** RSTP/MST basics, PortFast/BPDU Guard/Root Guard/Loop Guard/UDLD, LACP/PAgP, basic VTP, basic PVLAN, DHCP snooping, DAI.

**CCIE adds:**

- **MST mastery:** multi-region boundaries, **PVST+ simulation check**, instance balancing, dispute mechanism, BPDU Filter global vs interface semantics, topology-change propagation across regions.
- **VTP v3:** primary/secondary servers, MST/PVLAN database, password hidden mode, takeover commands. ENCOR barely touches v3.
- **Private VLANs at L3:** promiscuous trunk, isolated trunk, SVI-to-secondary mapping, PVLAN on port-channels, interaction with HSRP.
- **Multi-chassis:** **StackWise Virtual (Cat 9K)**, vPC (Nexus), VSS — dual-active detection, MEC, orphan ports, peer-link vs peer-keepalive.
- **VXLAN / BGP-EVPN** (the dominant CCIE EI fabric topic):
  - Underlay with OSPF or IS-IS plus PIM (ASM/SSM) or ingress replication
  - NVE interfaces, VNI-to-VLAN mapping, L2VNI vs L3VNI
  - **Distributed anycast gateway** (same IP/MAC on every VTEP)
  - **Symmetric vs asymmetric IRB**
  - EVPN route types 2 (MAC/IP), 3 (IMET), 5 (IP prefix)
  - ARP suppression, MAC mobility sequence numbers
  - **VXLAN Multi-Site** with Border Gateways, selective flooding
- **L2 multicast:** IGMP snooping querier, proxy reporting, MLDv2 snooping, Multicast VLAN Registration (MVR).
- **Ethernet services:** 802.1ad Q-in-Q, L2 protocol tunneling, MACsec with MKA, Flex Links (enterprise niche).
- **Advanced security:** DHCP snooping Option 82 trust boundary behavior, source-guard with port-security interaction, 802.1X with MAB + Critical Auth + Low-Impact Mode.

---

## 6. Decision — lab architecture: three-tier hybrid

Neither per-technology labs alone nor a single mega-topology alone is sufficient. Per-technology labs teach fundamentals fast but miss integration effects; mega-topologies match the exam format but are overwhelming for learning and expensive to maintain. Layer them:

```
┌────────────────────────────────────────────────────────────┐
│ Tier 1 — Foundation (per-technology, CCNP-style)           │
│   One feature, one small topology, one clear outcome.      │
│   Goal: correct configuration under no time pressure.      │
└──────────────────────────┬─────────────────────────────────┘
                           │
            ┌──────────────┴──────────────┐
            ▼                             ▼
┌───────────────────────┐    ┌────────────────────────────┐
│ Tier 2 — Domain       │    │ Examples:                  │
│ integration labs      │    │  • "SP Core": ISIS+LDP+    │
│ (medium topology,     │    │    BGP-VPNv4+L3VPN+MVPN    │
│ 6-12 nodes,           │    │  • "DC Fabric": VXLAN-EVPN │
│ 2-3 interacting       │    │    + multi-site + anycast  │
│ technologies)         │    │  • "Campus": StackWise-V + │
└──────────┬────────────┘    │    MST + PVLAN + 802.1X    │
           │                 │  • "Transport": SR-MPLS +  │
           ▼                 │    TI-LFA + BGP-LS         │
┌──────────────────────────────────────────────────────────┐
│ Tier 3 — Capstone (single mega-topology, exam-scale)     │
│   20-30 nodes, frozen baseline, fault-injection tickets  │
│   and multi-domain configuration scenarios.              │
│   Goal: 8-hour exam simulation.                          │
└──────────────────────────────────────────────────────────┘
```

**Key dependency patterns:**

- Tier 2 labs **reuse Tier 1 component configs** as building blocks — compose, do not re-author. The existing `baseline.yaml` + `setup_lab.py` pattern already supports this if device roles are parameterized.
- Tier 3 has **exactly one frozen baseline per capstone**, with fault-injection scripts and config-ticket scripts as the only mutations. The existing `fault-injector` skill transfers directly; the topology just gets bigger.
- The mega-topology is **not a teaching tool** — it is an assessment tool. Trying to learn VXLAN inside it for the first time will fail; trying to prove VXLAN mastery by solving three interlocking tickets in 45 minutes is exactly the exam.

**Trade-off matrix for reference:**

| Dimension | Per-technology (Tier 1) | Mega-topology (Tier 3) |
|---|---|---|
| Learning curve | Gentle, isolates one variable | Overwhelming early on |
| Realism | Low — no cross-domain drift | High — matches exam and production |
| Build/maintain cost | Low per lab, high in aggregate | Very high; one broken node blocks many scenarios |
| Resource footprint | Fits a laptop | Often needs a server or cluster |
| Exam alignment (CCIE EI v1.1 Module 2) | Poor | Excellent |
| Integration skills | Missed | Central |
| Debugging muscle memory | Weak — you already know where the fault is | Strong — you must localize |
| Iteration speed when authoring | Fast | Slow (long boot, fragile) |
| Fault-injection reuse | Easy | Hard — coupling between tickets |

Tier 2 sits in the middle of both axes and is the bridge layer that traditional CCIE vendors hide inside their "technology workbooks."

---

## 7. Decision — repository structure: one repo per certification

**Decision:** one Git repo per certification (`ccnp-encor-labs`, `ccie-ei-labs`, etc.), with tiers as top-level directories inside. Do not split tiers across repos.

**Why one repo (not three):**

| Concern | One repo, tiered dirs | Tier-per-repo |
|---|---|---|
| Skills submodule (`.agent/skills`) | Included once | Duplicated or pulled via a 4th "shared" repo |
| Scripts (`setup_lab.py`, `register-skills.py`) | Shared | Duplicated or extracted |
| Cross-tier references | Plain relative paths | Submodule pins, brittle |
| Refactoring a convention | One PR | Three PRs, coordinated |
| Clone size | Larger, but YAML/Python is tiny; EVE-NG images are not in git | Smaller each, total is larger |
| Independent versioning | Git tags per tier (`foundation-v1.0`, `capstone-v1.0`) | Native, but rarely needed |
| Audience separation | Directory READMEs + landing doc | Natural, but cosmetic |
| Publishing to students | One clone, one `CLAUDE.md`, one onboarding | Three clones, three setups |

**Why two repos (not one mega-repo with CCNP+CCIE+CCIE-SP):** CCNP and CCIE have different audiences, different blueprints, and may be published or licensed separately. The certification boundary is real; the tier boundary is not.

**Proposed layout for `ccie-ei-labs`:**

```
ccie-ei-labs/                     (one repo per certification)
├── .agent/skills/                (same submodule used today)
├── conductor/
│   ├── product.md
│   ├── workflow.md
│   └── tracks.md
├── blueprint/ccie-ei/blueprint.md
├── scripts/                      (shared setup/register/validation)
├── labs/
│   ├── foundation/               (Tier 1 — per-technology, CCNP-style)
│   │   ├── bgp/lab-01-…/
│   │   ├── ospf/lab-02-…/
│   │   └── switching/lab-03-…/
│   ├── integration/              (Tier 2 — domain-level, 6-12 nodes)
│   │   ├── sp-core/lab-01-mpls-l3vpn-…/
│   │   ├── dc-fabric/lab-01-vxlan-evpn-multisite/
│   │   └── transport/lab-01-sr-mpls-tilfa/
│   └── capstone/                 (Tier 3 — exam-scale)
│       ├── mock-01-full-8h/
│       └── mock-02-module2-scenario/
└── CLAUDE.md                     (one source of truth for conventions)
```

**The single exception that would justify splitting tiers across repos:** if Tier 1 foundations will be open-sourced while Tier 3 capstones will be sold or restricted, the public/private boundary becomes a licensing boundary, not a technical one. Only split then.

---

## 8. Open questions and next steps when CCIE work begins

- **Hardware:** the Dell Latitude 5540 is likely insufficient for Tier 3 (20-30 nodes). Plan for a rented lab (INE, CML-on-cloud) or a dedicated server (used ProLiant/R630-class) before starting Tier 3. Tier 1 and most of Tier 2 should still fit locally.
- **Tier-2 generator skill:** the current skill stack has `spec-creator` (one feature, one lab) and `mega-capstone-creator` (full blueprint, one mega-lab). A Tier-2 generator is missing — something that produces a 6-12 node integration lab covering 2-3 technologies in one domain. Design this skill before starting Tier 2.
- **Blueprint ingestion:** capture the CCIE EI v1.1 blueprint to `blueprint/ccie-ei/blueprint.md` before running `exam-planner`. Unlike CCNP, it must be split per tier — `exam-planner` may need a `--tier` flag.
- **Skill reuse:** `spec-creator`, `lab-assembler`, `fault-injector`, `mega-capstone-creator`, `tag-lab`, `drawio`, and `eve-ng` all transfer directly. Only the tier-2 generator is net-new.
- **Publishing strategy:** decide early whether Tier 1 may be public (marketing, GitHub stars) while Tier 3 stays private. This is the one decision that could flip the repo structure from §7.
- **CCIE SP vs EI:** if both certifications are eventually in scope, they should be separate repos (`ccie-ei-labs`, `ccie-sp-labs`) that share only the skills submodule. Do not attempt to unify them.

---

## 9. Reference: technologies explicitly flagged for deeper gap analysis later

When CCIE work starts, revisit these before authoring the blueprint split:

- BGP EVPN (Type 1-5, multi-homing, multi-site) — belongs in both Tier 2 DC Fabric and Tier 3 capstone.
- SR-MPLS with TI-LFA — belongs in Tier 2 Transport and Tier 3.
- OSPF sham-link and multi-process mutual redistribution — Tier 2 SP Core.
- StackWise Virtual + MST + PVLAN + 802.1X — Tier 2 Campus.
- Inter-AS MPLS options A/B/C — Tier 2 SP Core, revisited in Tier 3.
- DMVPN Phase 3 with OSPF/EIGRP/BGP tuning — Tier 2 WAN (not yet sketched above; add when planning).
