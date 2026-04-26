---
description: Tag a built lab with metadata (difficulty, blueprint refs, etc.)
argument-hint: <topic-slug>/<lab-id>
---

You are tagging an existing lab: `$ARGUMENTS`.

If `$ARGUMENTS` is empty, ask the user for the lab path and stop until they answer.

Advisory prerequisite checks (warn, do not block):
1. If `labs/$ARGUMENTS/` does not exist, warn and stop - there is nothing to tag.
2. If `labs/$ARGUMENTS/workbook.md` (or the equivalent deliverable produced by `lab-assembler`) is missing, warn that the lab does not look built yet and suggest `/build-lab $ARGUMENTS` first. Ask whether to proceed anyway.

Then read `.agent/skills/tag-lab/SKILL.md` and execute it for `$ARGUMENTS`.
