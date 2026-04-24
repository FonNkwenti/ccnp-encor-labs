---
description: Phase 3 - Build one lab (workbook, configs, topology, scripts) from its spec
argument-hint: <topic-slug>/<lab-id>
---

You are running Phase 3 of the three-phase lab workflow: **lab build** for `$ARGUMENTS`.

If `$ARGUMENTS` is empty or not of the form `<topic-slug>/<lab-id>`, ask the user for the full path and stop until they answer.

Advisory prerequisite checks (warn, do not block):
1. If `labs/$ARGUMENTS/` does not exist, warn that the lab folder is missing and ask whether to create it.
2. If `labs/$ARGUMENTS/spec.md` does not exist, warn that Phase 2 has not run for this lab and suggest `/create-spec <topic-slug>`. Ask whether to proceed anyway.
3. If `labs/$ARGUMENTS/baseline.yaml` is missing, warn before proceeding.
4. If the workbook (`labs/$ARGUMENTS/workbook.md` or similar) already exists, warn that re-running will rewrite it and confirm.

Then read `.agent/skills/lab-assembler/SKILL.md` and execute it for `$ARGUMENTS`. Per `CLAUDE.md`, `lab-assembler` dispatches `drawio` and `fault-injector` as subagents at the appropriate steps - let it handle that; do not invoke those skills directly.

Note: this command builds **one** lab. To build every lab in a topic with a review gate between each, use `/build-topic <topic-slug>` instead (that routes to the `lab-builder` orchestrator).

When finished, stop for review and suggest `/tag-lab $ARGUMENTS` once the lab is approved.
