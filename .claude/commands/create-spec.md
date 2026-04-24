---
description: Phase 2 - Create spec.md and baseline.yaml for one topic
argument-hint: <topic-slug>
---

You are running Phase 2 of the three-phase lab workflow: **spec creation** for topic `$ARGUMENTS`.

If `$ARGUMENTS` is empty, ask the user which topic slug to spec (offer the list from `specs/topic-plan.yaml` if available) and stop until they answer.

Advisory prerequisite checks (warn, do not block):
1. If `specs/topic-plan.yaml` does not exist, warn that Phase 1 has not run and suggest `/plan-exam`. Ask whether to proceed anyway.
2. If the topic slug `$ARGUMENTS` is not listed in `specs/topic-plan.yaml`, warn that it was hand-added and confirm before continuing.
3. If `labs/$ARGUMENTS/` does not exist, warn and offer to create it.
4. If `labs/$ARGUMENTS/spec.md` or `labs/$ARGUMENTS/baseline.yaml` already exists, warn that re-running will rewrite them and confirm before continuing.

Then read `.agent/skills/spec-creator/SKILL.md` and execute it for topic `$ARGUMENTS`. The skill is responsible for:
- Producing `labs/$ARGUMENTS/spec.md`
- Producing `labs/$ARGUMENTS/baseline.yaml`

When the spec is approved, **update `README.md`**:
1. Read `labs/$ARGUMENTS/baseline.yaml` and extract the `labs[]` list — each entry's `folder` and `title` (or `name`) fields.
2. Find the `### $ARGUMENTS` section between the `<!-- lab-index-start -->` / `<!-- lab-index-end -->` markers in `README.md`.
3. Replace the "Spec not yet created" placeholder line with an unchecked checklist, one entry per lab in `baseline.yaml` order:

```
- [ ] `<lab.folder>` — <lab.title>
```

4. Leave all other `### <topic>` sections unchanged.
5. Write the updated `README.md` and commit it alongside `spec.md` and `baseline.yaml`.

Stop for review before moving to Phase 3. Point the user at `/build-lab $ARGUMENTS/<lab-id>` or `/build-topic $ARGUMENTS` once they approve.
