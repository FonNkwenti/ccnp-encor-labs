# Lab Build Telemetry — Design Spec

**Date:** 2026-04-20  
**Status:** Approved  
**Scope:** CCNP ENCOR lab project (`ccnp-encor-labs`)

---

## Problem

Token usage during lab builds is opaque. There is no visibility into which skills, models, or files consume the most tokens per build, per chapter, or across the project. This makes it impossible to identify redundant context, over-engineered skills, or expensive advisor calls that could be pruned to reduce cost.

---

## Goal

Capture granular, per-skill-call telemetry automatically on every lab build. Store it in a central JSONL file that can be queried for analytics during the project and migrated to SQLite at the end.

---

## Architecture

### Components

1. **Claude Code Hook** — fires after each skill completes (via `settings.json`)
2. **Haiku Telemetry Logger** (`scripts/log-telemetry.py`) — lightweight Python script, invoked by the hook, appends one JSONL entry per skill call
3. **Central Log** (`logs/telemetry.jsonl`) — append-only, grows across all builds
4. **Log Documentation** (`logs/README.md`) — schema reference, query examples, SQLite migration path

### Data Flow

```
Skill invoked
     │
     ▼
Skill completes (success or failure)
     │
     ▼
Claude Code fires `skill-completed` hook
     │
     ▼
scripts/log-telemetry.py (runs as Haiku)
     │   ├── Reads hook context (skill name, status, timing)
     │   ├── Queries Claude Code session API for token counts, model, advisor data
     │   ├── Extracts files modified (from git diff or session log)
     │   └── Resolves lab/chapter context (from git branch or CLAUDE.md)
     │
     ▼
Appends one JSONL entry to logs/telemetry.jsonl
```

---

## Hook Configuration

In `.claude/settings.json`:

```json
{
  "hooks": {
    "skill-completed": "python3 scripts/log-telemetry.py"
  }
}
```

The hook passes execution context (skill name, exit status, session ID, timing) as environment variables or stdin to the script.

---

## JSONL Schema

One JSON object per line. Each represents one skill invocation.

```json
{
  "timestamp": "2026-04-20T14:32:15Z",
  "lab": {
    "chapter": "ospf",
    "name": "lab-00-single-area-ospfv2",
    "phase": "Phase 2 - Spec"
  },
  "skill": {
    "name": "spec-creator",
    "invocation_id": "uuid"
  },
  "model": "claude-haiku-4-5-20251001",
  "tokens": {
    "input": 4250,
    "output": 1820,
    "cache_creation": 0,
    "cache_read": 0
  },
  "advisor": {
    "used": true,
    "savings_tokens": 450,
    "cost_tokens": 120
  },
  "files_touched": [
    "labs/ospf/lab-00-single-area-ospfv2/spec.md",
    "labs/ospf/lab-00-single-area-ospfv2/baseline.yaml"
  ],
  "execution": {
    "duration_seconds": 87.4,
    "success": true,
    "error": null
  }
}
```

### Field Reference

| Field | Description |
|---|---|
| `timestamp` | ISO 8601 UTC timestamp of skill completion |
| `lab.chapter` | Chapter slug (e.g., `ospf`, `bgp`, `switching`) |
| `lab.name` | Lab directory name |
| `lab.phase` | Phase 1 Plan / Phase 2 Spec / Phase 3 Build |
| `skill.name` | Skill identifier (e.g., `spec-creator`, `lab-assembler`) |
| `skill.invocation_id` | UUID for this specific call |
| `model` | Full model ID used for the skill |
| `tokens.input` | Input tokens consumed |
| `tokens.output` | Output tokens generated |
| `tokens.cache_creation` | Tokens written to prompt cache |
| `tokens.cache_read` | Tokens read from prompt cache (cost savings) |
| `advisor.used` | Whether Claude Advisor was invoked |
| `advisor.savings_tokens` | Estimated tokens saved by advisor |
| `advisor.cost_tokens` | Tokens the advisor itself consumed |
| `files_touched` | List of files modified during this skill call |
| `execution.duration_seconds` | Wall-clock time for the skill |
| `execution.success` | Boolean — did the skill complete without error |
| `execution.error` | Error message if `success` is false, else null |

---

## Telemetry Logger (`scripts/log-telemetry.py`)

Responsibilities:
- Read skill context from hook environment (skill name, status, timing)
- Query Claude Code session API for token counts, model ID, advisor data
- Resolve lab/chapter context from git branch name or local CLAUDE.md
- Extract files modified via `git diff --name-only HEAD`
- Generate a UUID for the invocation
- Format as JSONL and append to `logs/telemetry.jsonl`
- Exit cleanly on failure (never block the build)

The script is intentionally lightweight. No external dependencies beyond Python stdlib and `subprocess` for git. Runs on Haiku to minimize cost.

**Failure policy:** If the logger fails for any reason, it logs the error to `logs/telemetry-errors.log` and exits 0 — telemetry loss is acceptable, build interruption is not.

---

## Storage

```
logs/
├── telemetry.jsonl        # Central append-only log
├── telemetry-errors.log   # Logger errors only
└── README.md              # Schema reference + query examples
```

`logs/telemetry.jsonl` is gitignored by default to avoid committing potentially large log files. A flag to opt into committing can be added later.

---

## Analysis (JSONL queries)

With `jq` and Python available today:

```bash
# Total tokens per chapter
cat logs/telemetry.jsonl | jq -r '.lab.chapter' | sort | uniq -c | sort -rn

# Most expensive skills by input tokens
cat logs/telemetry.jsonl | jq -r '[.skill.name, .tokens.input] | @tsv' | \
  sort -t$'\t' -k2 -rn | head -10

# Advisor ROI (savings - cost)
cat logs/telemetry.jsonl | jq '[select(.advisor.used == true) | 
  (.advisor.savings_tokens - .advisor.cost_tokens)] | add'

# Labs with highest total token cost
cat logs/telemetry.jsonl | jq -r '[.lab.name, (.tokens.input + .tokens.output)] | @tsv' | \
  awk -F'\t' '{sum[$1]+=$2} END {for (k in sum) print sum[k], k}' | sort -rn
```

---

## Future: SQLite Migration

When ready, run a one-time import:

```python
import json, sqlite3

conn = sqlite3.connect("logs/telemetry.db")
# Create tables matching the JSONL schema
# Read telemetry.jsonl line by line and insert rows
# Build indexes on chapter, skill, model, timestamp
```

The flat JSONL schema maps directly to a normalized SQLite schema with a `builds` table, a `files_touched` table, and an `advisor_events` table.

---

## Risks & Open Questions

1. **Claude Code session API availability:** It is unconfirmed whether Claude Code exposes per-skill token counts via a session API accessible to hooks. If not, the fallback is to parse Claude Code's session log files or use `ANTHROPIC_API_KEY` to query usage directly. This must be validated in the implementation spike before building the logger.

2. **Hook timing:** The `skill-completed` hook must fire after the skill response is finalized so token counts are complete. If the hook fires mid-stream, we may need to add a brief delay or poll for session completion.

---

## Out of Scope

- Real-time cost dashboards (post-project SQLite analysis covers this)
- Per-student telemetry (setup_lab.py is student-facing, not instrumented)
- Cost estimation in USD (token counts are the raw metric; pricing varies by model)
- Telemetry for manual Claude Code interactions outside of skill invocations
