# Lessons Learned — ccnp-encor-labs

Running log of patterns and corrections applied during lab generation.
New entries at the top. Review at the start of each session.

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
