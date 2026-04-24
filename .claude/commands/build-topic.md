---
description: Phase 3 - Build every lab for a topic with a review gate between each
argument-hint: <topic-slug>
---

You are running Phase 3 of the three-phase lab workflow at the **topic level** for `$ARGUMENTS`. This uses the `lab-builder` orchestrator, which iterates every lab in `baseline.yaml labs[]` and pauses for user approval between each one.

If `$ARGUMENTS` is empty, ask the user which topic slug to build (offer the list from `specs/topic-plan.yaml` if available) and stop until they answer.

Advisory prerequisite checks (warn, do not block):
1. If `labs/$ARGUMENTS/spec.md` or `labs/$ARGUMENTS/baseline.yaml` is missing, warn that Phase 2 has not run for this topic and suggest `/create-spec $ARGUMENTS`. Ask whether to proceed anyway.
2. If any lab folder under `labs/$ARGUMENTS/` already contains a `workbook.md`, warn that those labs will be re-built (overwritten) and confirm before continuing.

Then read `.agent/skills/lab-builder/SKILL.md` and execute it for topic `$ARGUMENTS`. The orchestrator is responsible for:
- Parsing `labs[]` from `baseline.yaml`
- Invoking `lab-assembler` for each lab in order
- Enforcing the pause-for-review gate after each lab (do not skip these pauses, even if the user seems eager)
- Running the Step 3 validation checklist after all labs are approved

To build a single lab without the topic loop, use `/build-lab <topic>/<lab-id>` instead (that calls `lab-assembler` directly).
