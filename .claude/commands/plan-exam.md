---
description: Phase 1 - Read the blueprint and generate topic-plan.yaml + empty lab folders
argument-hint: (no args - reads blueprint/<exam-code>/blueprint.md)
---

You are running Phase 1 of the three-phase lab workflow: **exam planning**.

Advisory prerequisite checks (warn, do not block):
1. Locate `blueprint/` at the repo root. If it is missing, warn that bootstrap is incomplete and stop.
2. Find the exam-code subdirectory under `blueprint/` (e.g., `blueprint/300-410/`). If there is more than one, ask which to use.
3. Check that `blueprint/<exam-code>/blueprint.md` exists and is non-empty. If missing or empty, warn that the blueprint has not been uploaded yet and ask whether to proceed anyway.
4. If `specs/topic-plan.yaml` already exists, warn that re-running will overwrite or conflict with it and confirm before continuing.

Then read `.agent/skills/exam-planner/SKILL.md` and execute it end-to-end. The skill is responsible for:
- Parsing the full blueprint
- Writing `specs/topic-plan.yaml`
- Creating empty `labs/<topic>/` folders per the plan

When the topic plan is approved, **update `README.md`**:
1. Read the topic list from `specs/topic-plan.yaml`.
2. Find the `<!-- lab-index-start -->` / `<!-- lab-index-end -->` markers in `README.md`. If the markers are absent, append them at the end of the file.
3. Replace everything between the markers (inclusive of the placeholder line) with one section per topic, in plan order:

```
### <topic-slug>

> Spec not yet created — run `/create-spec <topic-slug>`
```

4. Write the updated `README.md` and commit it alongside `specs/topic-plan.yaml` and the empty `labs/` folders.

Finish by summarising the generated topic list and pointing the user at `/create-spec <topic-slug>` for Phase 2.
