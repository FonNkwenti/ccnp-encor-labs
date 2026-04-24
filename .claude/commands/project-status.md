---
description: Report the current phase and lab completion status for this exam repo
argument-hint: (no args)
---

Summarise where this exam repo currently sits in the three-phase workflow. Be concise - a short table and a one-line recommendation for the next command.

Gather this information:
1. **Blueprint**: does `blueprint/<exam-code>/blueprint.md` exist and is it non-empty?
2. **Phase 1 (plan)**: does `specs/topic-plan.yaml` exist? If yes, list the topic slugs it contains.
3. **Phase 2 (specs)**: for each topic slug, does `labs/<topic>/spec.md` and `labs/<topic>/baseline.yaml` exist?
4. **Phase 3 (builds)**: for each topic, list the lab folders under `labs/<topic>/` and whether each one has a workbook deliverable (e.g., `workbook.md`).
5. **Progress memo**: if `.agent/skills/memory/progress.md` exists, include its headline.
6. **Skills pin**: run `git submodule status .agent/skills` and report the pinned commit.

Then output a table with one row per topic, columns: `topic | spec? | labs built / total`. Finish with a single-line recommendation such as "Next: `/create-spec <topic>`" or "Next: `/build-lab <topic>/<lab-id>`" pointing at the earliest incomplete step.

Do not modify any files.
