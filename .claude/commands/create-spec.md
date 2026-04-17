---
description: Generate lab spec + baseline.yaml for a topic from topic-plan.yaml (Phase 2)
argument-hint: <topic-slug> (must exist in specs/topic-plan.yaml)
---

Invoke the `spec-creator` skill to generate the spec and baseline for: $ARGUMENTS

If no topic is given, list topics available in `specs/topic-plan.yaml` and ask which one to spec. Pause for review after the spec is produced — do not continue to lab-builder automatically.
