---
description: Build a mega-capstone lab that spans multiple topics
argument-hint: <capstone-slug>
---

You are building a **mega-capstone** lab: `$ARGUMENTS`.

If `$ARGUMENTS` is empty, ask the user for a capstone slug and stop until they answer.

Advisory prerequisite checks (warn, do not block):
1. If `specs/topic-plan.yaml` is missing, warn that the exam plan is not in place and suggest `/plan-exam`.
2. A capstone should sit on top of already-built per-topic labs. If most topics under `labs/` have no `workbook.md` yet, warn that building a capstone this early will produce weak coverage and confirm before proceeding.
3. If `labs/capstones/$ARGUMENTS/` already exists and is non-empty, warn and confirm.

Then read `.agent/skills/mega-capstone-creator/SKILL.md` and execute it for `$ARGUMENTS`.

When finished, stop for review and suggest `/tag-lab capstones/$ARGUMENTS` once approved.
