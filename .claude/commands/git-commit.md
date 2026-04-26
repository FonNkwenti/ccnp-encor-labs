---
description: Stage, commit, and optionally push changes using project conventions
argument-hint: [files to stage, or empty to stage all tracked changes]
model: claude-haiku-4-5-20251001
allowed-tools: Bash
---

Stage and commit changes for this project. Run whenever work is ready to commit.

If `$ARGUMENTS` lists specific files, stage only those. If empty, stage all tracked modifications.

## Steps

1. Run in parallel:
   - `git status`
   - `git diff --stat HEAD`
   - `git log --oneline -5` (to match existing commit style)

2. Stage files:
   - If `$ARGUMENTS` lists paths: `git add <files>`
   - If `$ARGUMENTS` is empty: `git add -u` (tracked modifications only — no untracked files)
   - Never stage: `.env`, credentials, `*.pyc`, `__pycache__/`, lock files, `_verify_input.yaml`

3. Draft a conventional commit message:
   - Format: `<type>(<scope>): <subject>`
   - **Types**: `feat` / `fix` / `docs` / `refactor` / `chore` / `test`
   - **Scope** (optional): lab path for lab-specific changes (e.g. `ospf/lab-00`), skill name for skill changes (e.g. `drawio`), omit for repo-wide changes
   - **Subject**: imperative mood, lowercase, no trailing period, ≤72 chars
   - **Body** (when useful): one short paragraph explaining WHY, not WHAT
   - **Footer**: always end with `Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>`

4. Show the staged file list and the full commit message. Ask the user: **"Commit with this message? (y/n)"**

5. On confirmation: commit using a heredoc to preserve formatting:
   ```bash
   git commit -m "$(cat <<'EOF'
   <message here>
   EOF
   )"
   ```

6. After committing, ask: **"Push to origin/`<branch>`? (y/n)"** — never push without explicit confirmation.

7. On push confirmation: `git push origin <current-branch>`

## Commit message examples for this project

```
feat(ospf/lab-00): add single-area OSPFv2 lab package
fix(drawio): align cisco19 shapes with style-guide-reference
docs(memory): add artifact regeneration command reference
chore: sync skills submodule to latest hub commit
refactor(fault-injector): migrate templates to eve_ng.py shared library
feat(ospf/lab-01): add multi-area OSPF with stub areas
```

## Do not

- `git add -A` or `git add .` (picks up untracked junk)
- `git commit --amend` (creates history rewrite risk)
- `git push --force`
- Skip the confirmation steps
