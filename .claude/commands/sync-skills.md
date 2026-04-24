---
description: Update the .agent/skills submodule to the latest hub commit
argument-hint: (no args)
allowed-tools: Bash
---

Update the shared skills submodule to the latest commit on its tracked branch.

Steps:
1. Run `git submodule status .agent/skills` and report the current pinned commit.
2. Run `git submodule update --remote .agent/skills` to pull the latest.
3. Run `git submodule status .agent/skills` again and report the new commit.
4. If the commit changed, run `git -C .agent/skills log --oneline <old>..<new>` and summarise what was updated.
5. If there is a change, stage `.agent/skills` and show the user the exact `git commit -m` line to run, but do **not** commit without their confirmation (per global policy, skills-repo pins are important enough to review).

Do not push.
