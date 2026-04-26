# Lessons Learned — ccnp-encor-labs

Running log of patterns and corrections applied during lab generation.
New entries at the top. Review at the start of each session.

---

## 2026-04-20 — Always update topology.drawio title even when reusing an unchanged topology

**Correction:** When Step 5a (reuse gate) copies `topology.drawio` verbatim from the
previous lab, the embedded diagram title in the `<mxCell id="title" value="...">` cell
was not being updated. The skill instruction said "do NOT update the embedded title."
User explicitly required the title be updated to reflect the current lab number and name.

**Rule:**
- When copying `topology.drawio` from lab N-1 to lab N (reuse gate passed), ALWAYS
  update the `value="..."` attribute of the `<mxCell id="title">` cell to match the
  current lab's title.
- Format: `Lab NN: <Topic> — <Subtitle>` (consistent with workbook.md H1).
- The skill's "do NOT update title" instruction is overridden by this user preference.

**Why:** Students see the diagram title first. A stale title ("Lab 03: RESTCONF...")
on a Lab 04 diagram creates confusion and appears as an authoring error.

**Touched:**
- `labs/automation/lab-04-capstone-config/topology/topology.drawio` — title corrected
  from "Lab 03: RESTCONF and REST API Interpretation" to "Lab 04: Automation Capstone — Full Protocol Mastery"
- This rule now applies to all future labs in all topics.

---

## 2026-04-18 — Fault injection scripts must not log the root cause

**Correction:** Fault injection scripts in `labs/<topic>/lab-NN-<slug>/scripts/fault-injection/`
were logging detailed root causes (e.g., "Wrong Access VLAN", "BGP route advertisement failed")
which revealed to students what to troubleshoot. Scripts should log only the scenario/ticket
reference to avoid tipping off the fault.

**Rule:**
- Fault injection log messages must follow the pattern:
  ```python
  logger.info(f"Fault Injection: Scenario {scenario_num}")
  # or
  logger.info(f"Fault Injection: Ticket {ticket_num}")
  ```
- Never include diagnostic details like root cause, misconfigured parameter, broken service, etc.
- The workbook.md maps each scenario/ticket to its actual fault; students discover it via
  troubleshooting, not script logs.

**Why:** The lab is a hands-on troubleshooting exercise. Logging root causes defeats the
learning objective by making the fault obvious rather than discoverable.

**Touched:**
- `fault-injector` skill: Updated template to use scenario-only logging
- All existing scripts in `labs/bgp/` and `labs/eigrp/` — already corrected manually

---

## 2026-04-18 — Copy `topology.drawio` when the topology is unchanged

**Correction:** Do not regenerate a lab's `topology.drawio` when the physical topology
(device set + link set) is identical to the previous lab's. Regenerating causes style
drift and burns tokens on a subagent that produces something that should be byte-identical
to what already exists.

**Rule:**
- Before Step 5 of `lab-assembler`, compare `baseline.yaml labs[N].devices` and
  the effective link set against lab N-1's.
- If both match exactly → `cp labs/<topic>/lab-(N-1)-.../topology/topology.drawio
  labs/<topic>/lab-NN-.../topology/topology.drawio`. Done.
- Only dispatch the drawio subagent when the device set or link set actually changed.
- When the topology only *slightly* changes (e.g. one extra router added to a triangle),
  have the subagent start from the sibling lab's `topology.drawio` and modify it — never
  from scratch. Style drift across a topic is the failure mode to avoid.

**Why:** Operator-applied style updates to a topology (colors, shapes, legend layout) are
expensive to recreate and easy to lose. A verbatim copy preserves every tweak.

**Touched:**
- `.agent/skills/lab-assembler/SKILL.md` — Step 5 split into 5a (reuse gate) and
  5b (generate fresh, with a "start from sibling" directive).
- `labs/multicast/lab-01-rp-discovery-and-igmpv3/topology/topology.drawio` — replaced the
  subagent-generated version with a verbatim copy of `lab-00-pim-sm-and-igmp`.

---

## 2026-04-16 — Operator provides `.unl`, not the generator

**Correction:** Stop auto-generating EVE-NG `.unl` files via `gen_unl.py`
during lab builds. Revert to the old workflow where the lab operator
manually exports the `.unl` from EVE-NG after verifying the topology.

**Rule:**
- Lab-builder agents produce `topology.drawio` and `topology/README.md` only.
- `labs/common/tools/gen_unl.py` is **deferred** — do not invoke as part
  of a routine build. Code kept for possible future refinement.
- The operator drops the exported `.unl` into `topology/` and commits it
  alongside the `.drawio` and README.
- `meta.yaml` still lists `topology/<lab>.unl` as a shipped file — just
  sourced manually.

**Why:** Generator output drifted from hand-built EVE-NG topologies
(interface ordering, link IDs, canvas layout). The operator export is the
canonical source of truth; the generator was creating extra review load
without buying correctness.

**Touched:** `.agent/skills/eve-ng/SKILL.md` §6.9 and §7; deprecation banner
added to `labs/common/tools/gen_unl.py` docstring.

---
