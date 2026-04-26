# Lab Build Telemetry Logs

This directory contains telemetry captured automatically during lab builds.

## Files

| File | Description |
|---|---|
| `telemetry.jsonl` | Central append-only log — one JSON object per skill invocation |
| `telemetry-errors.log` | Logger errors only (never stops a build) |

Both files are gitignored. To capture them for analysis, copy them out or opt into committing locally.

## JSONL Schema

Each line is a JSON object:

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
  "effort_level": "standard",
  "tokens": {
    "input": 4250,
    "output": 1820,
    "cache_creation": 0,
    "cache_read": 0
  },
  "advisor": {
    "used": false,
    "savings_tokens": 0,
    "cost_tokens": 0
  },
  "files_touched": [
    "labs/ospf/lab-00-single-area-ospfv2/spec.md"
  ],
  "execution": {
    "duration_seconds": 87.4,
    "success": true,
    "error": null
  }
}
```

## Common Queries (jq)

```bash
# Total tokens per chapter
cat logs/telemetry.jsonl | jq -r '.lab.chapter' | sort | uniq -c | sort -rn

# Most expensive skills by input tokens
cat logs/telemetry.jsonl | jq -r '[.skill.name, .tokens.input] | @tsv' \
  | sort -t$'\t' -k2 -rn | head -10

# Labs with highest total token cost
cat logs/telemetry.jsonl | jq -r '[.lab.name, (.tokens.input + .tokens.output)] | @tsv' \
  | awk -F'\t' '{sum[$1]+=$2} END {for (k in sum) print sum[k], k}' | sort -rn

# Advisor ROI (savings - cost)
cat logs/telemetry.jsonl | jq '[select(.advisor.used == true) |
  (.advisor.savings_tokens - .advisor.cost_tokens)] | add'

# Failed skill invocations
cat logs/telemetry.jsonl | jq 'select(.execution.success == false)'
```

## Future: SQLite Migration

When ready, import with:

```python
import json, sqlite3

conn = sqlite3.connect("logs/telemetry.db")
# See docs/superpowers/specs/2026-04-20-lab-telemetry-design.md for schema
with open("logs/telemetry.jsonl") as f:
    for line in f:
        row = json.loads(line)
        # INSERT into normalized tables: builds, files_touched, advisor_events
```
