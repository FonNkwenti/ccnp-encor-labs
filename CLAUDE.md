# CCNP ENCOR (350-401) Lab Project

## Shared Context (Skills + Standards)

See .agent/skills/memory/CLAUDE.md for the foundation skills repository context.

## This Certification

- **Exam**: CCNP ENCOR (350-401)
- **Audience**: Network engineers preparing for the 350-401 exam
- **Platform**: EVE-NG on Dell Latitude 5540 (Intel/Windows)

## Project Structure

See conductor/product.md and conductor/workflow.md for detailed documentation.

## Active Work

- See conductor/tracks.md for the current chapter plan
- See labs/ for existing lab content
- Run git submodule status to check skills version

## Three-Phase Workflow

1. Phase 1 - Plan: Upload blueprint to blueprint/350-401/blueprint.md, then run exam-planner
2. Phase 2 - Spec: Run spec-creator per topic (review after each)
3. Phase 3 - Build: Run lab-workbook-creator one lab at a time (review after each)

## Common Commands

```bash
# Update skills to latest
git submodule update --remote .agent/skills
git add .agent/skills

# Run lab setup
python labs/<topic>/lab-NN-<slug>/setup_lab.py --host <eve-ng-ip>

# Run tests
pytest tests/ -v
```
