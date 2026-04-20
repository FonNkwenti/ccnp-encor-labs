# Lab Build Telemetry — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automatically capture granular per-skill-call telemetry (tokens, model, advisor, files, timing) during every lab build and append it to `logs/telemetry.jsonl`.

**Architecture:** A `PostToolUse` hook in `.claude/settings.json` fires `scripts/log-telemetry.py` after each `Skill` tool invocation. The script reads hook context from stdin, extracts lab/chapter context from git, pulls token counts from Claude Code's session log files, and appends one JSONL entry per skill call. All errors are swallowed to `logs/telemetry-errors.log` — the build is never interrupted.

**Tech Stack:** Python 3 stdlib only (`json`, `subprocess`, `uuid`, `pathlib`, `datetime`). No pip dependencies. `pytest` for tests.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `scripts/log-telemetry.py` | Create | Main entrypoint — reads stdin, orchestrates all components, writes JSONL |
| `scripts/lib/__init__.py` | Create | Package marker |
| `scripts/lib/telemetry/__init__.py` | Create | Package marker |
| `scripts/lib/telemetry/context.py` | Create | Resolve lab name, chapter, phase from git branch / cwd |
| `scripts/lib/telemetry/git_files.py` | Create | Get list of files modified since skill started (git diff) |
| `scripts/lib/telemetry/session_log.py` | Create | Parse `~/.claude/projects/*/` JSONL to extract token usage for a session |
| `scripts/lib/telemetry/formatter.py` | Create | Build the final JSONL dict from all component outputs |
| `tests/__init__.py` | Create (if missing) | Package marker |
| `tests/telemetry/__init__.py` | Create | Package marker |
| `tests/telemetry/test_context.py` | Create | Unit tests for context resolver |
| `tests/telemetry/test_git_files.py` | Create | Unit tests for git file extractor |
| `tests/telemetry/test_session_log.py` | Create | Unit tests for session log reader |
| `tests/telemetry/test_formatter.py` | Create | Unit tests for JSONL formatter |
| `logs/README.md` | Create | Schema reference + query examples |
| `.gitignore` | Modify | Add `logs/telemetry.jsonl` and `logs/telemetry-errors.log` |
| `.claude/settings.json` | Modify | Add `PostToolUse` hook for `Skill` tool |

---

## Task 1: Spike — Discover Hook Payload and Session Log Format

**No TDD for a spike.** This task establishes facts that all other tasks depend on.

**Files:**
- Create (temporary): `scripts/_hook-spike.py`

- [ ] **Step 1.1: Add a minimal spike hook to settings.json**

Read `.claude/settings.json` and replace its contents with:

```json
{
  "enabledPlugins": {
    "commit-commands@claude-plugins-official": true
  },
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Skill",
        "hooks": [
          {
            "type": "command",
            "command": "python3 scripts/_hook-spike.py"
          }
        ]
      }
    ]
  }
}
```

- [ ] **Step 1.2: Create the spike script**

Create `scripts/_hook-spike.py`:

```python
#!/usr/bin/env python3
import json, sys, os
from pathlib import Path

payload = json.load(sys.stdin)

spike_out = Path("logs/_spike-payload.json")
spike_out.parent.mkdir(exist_ok=True)
spike_out.write_text(json.dumps(payload, indent=2))

# Also dump env vars
env_out = Path("logs/_spike-env.txt")
env_out.write_text("\n".join(f"{k}={v}" for k, v in sorted(os.environ.items())))
```

- [ ] **Step 1.3: Invoke any skill from Claude Code**

Run any skill (e.g., invoke `diagram` or `spec-creator` with a simple arg). This triggers the hook.

- [ ] **Step 1.4: Inspect the spike output**

```bash
cat logs/_spike-payload.json
cat logs/_spike-env.txt
```

Record exactly which fields are present. Expected shape (confirm or note differences):

```json
{
  "session_id": "...",
  "tool_name": "Skill",
  "tool_input": { "skill": "...", "args": "..." },
  "tool_response": "...",
  "event_type": "PostToolUse"
}
```

Key questions to answer:
- Is `session_id` present? What format?
- Is there a `timestamp` or `duration` field?
- Is there any token usage data in `tool_response`?
- What env vars does Claude Code set for the hook process?

- [ ] **Step 1.5: Find Claude Code's session log directory**

```bash
ls ~/.claude/projects/
```

Find the directory that corresponds to this project (it will be named after a hash of the project path). Open the most recent `.jsonl` file and look for usage fields:

```bash
# List project directories sorted by modification time
ls -lt ~/.claude/projects/ | head -5

# Find the right directory (contains recent .jsonl files)
ls ~/.claude/projects/<hash>/

# Inspect the most recent session log
tail -50 ~/.claude/projects/<hash>/*.jsonl | python3 -m json.tool 2>/dev/null | head -100
```

Record which fields contain token counts. Expected shape in session log entries:

```json
{
  "type": "assistant",
  "message": {
    "usage": {
      "input_tokens": 4250,
      "output_tokens": 1820,
      "cache_creation_input_tokens": 0,
      "cache_read_input_tokens": 0
    },
    "model": "claude-haiku-4-5-20251001"
  }
}
```

- [ ] **Step 1.6: Document spike findings**

Write a short note at `logs/_spike-notes.txt` recording:
1. Exact fields available in hook stdin payload
2. Session log directory path pattern
3. Exact field names for token counts in session log
4. Whether timing data is in the hook payload or must be computed externally

These findings drive the implementation in Tasks 3–5.

- [ ] **Step 1.7: Commit spike tooling (NOT the spike output)**

```bash
git add scripts/_hook-spike.py .claude/settings.json
git add logs/_spike-notes.txt
git commit -m "spike: discover hook payload and session log format"
```

---

## Task 2: Logs Directory and .gitignore

**Files:**
- Create: `logs/README.md`
- Modify: `.gitignore`

- [ ] **Step 2.1: Create logs directory with a .gitkeep**

```bash
mkdir -p logs
touch logs/.gitkeep
```

- [ ] **Step 2.2: Update .gitignore**

Add to `.gitignore`:

```
# Telemetry logs (large, machine-generated — gitignored by default)
logs/telemetry.jsonl
logs/telemetry-errors.log
logs/_spike-*.json
logs/_spike-*.txt
```

- [ ] **Step 2.3: Create logs/README.md**

Create `logs/README.md` with this exact content:

```markdown
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
```

- [ ] **Step 2.4: Commit**

```bash
git add logs/.gitkeep logs/README.md .gitignore
git commit -m "feat(telemetry): add logs directory and README"
```

---

## Task 3: Context Resolver — TDD

Resolves lab name, chapter slug, and build phase from the current git working directory.

**Files:**
- Create: `scripts/lib/__init__.py`
- Create: `scripts/lib/telemetry/__init__.py`
- Create: `scripts/lib/telemetry/context.py`
- Create: `tests/__init__.py`
- Create: `tests/telemetry/__init__.py`
- Create: `tests/telemetry/test_context.py`

- [ ] **Step 3.1: Write failing tests**

Create `tests/telemetry/test_context.py`:

```python
import pytest
from unittest.mock import patch
from scripts.lib.telemetry.context import resolve_lab_context


def test_resolves_chapter_from_lab_path():
    with patch("scripts.lib.telemetry.context._get_cwd", return_value="/repo/labs/ospf/lab-00-single-area-ospfv2"):
        ctx = resolve_lab_context()
    assert ctx["chapter"] == "ospf"


def test_resolves_lab_name_from_lab_path():
    with patch("scripts.lib.telemetry.context._get_cwd", return_value="/repo/labs/ospf/lab-00-single-area-ospfv2"):
        ctx = resolve_lab_context()
    assert ctx["name"] == "lab-00-single-area-ospfv2"


def test_resolves_phase_from_branch_name_spec():
    with patch("scripts.lib.telemetry.context._get_cwd", return_value="/repo/labs/ospf/lab-00-single-area-ospfv2"):
        with patch("scripts.lib.telemetry.context._get_branch", return_value="spec/ospf-lab-00"):
            ctx = resolve_lab_context()
    assert ctx["phase"] == "Phase 2 - Spec"


def test_resolves_phase_from_branch_name_build():
    with patch("scripts.lib.telemetry.context._get_cwd", return_value="/repo/labs/ospf/lab-00-single-area-ospfv2"):
        with patch("scripts.lib.telemetry.context._get_branch", return_value="feat/ospf-lab-00"):
            ctx = resolve_lab_context()
    assert ctx["phase"] == "Phase 3 - Build"


def test_resolves_phase_from_branch_name_plan():
    with patch("scripts.lib.telemetry.context._get_cwd", return_value="/repo/labs/ospf/lab-00-single-area-ospfv2"):
        with patch("scripts.lib.telemetry.context._get_branch", return_value="plan/ospf-lab-00"):
            ctx = resolve_lab_context()
    assert ctx["phase"] == "Phase 1 - Plan"


def test_unknown_chapter_when_not_in_labs_dir():
    with patch("scripts.lib.telemetry.context._get_cwd", return_value="/repo"):
        ctx = resolve_lab_context()
    assert ctx["chapter"] == "unknown"
    assert ctx["name"] == "unknown"


def test_unknown_phase_for_unrecognized_branch():
    with patch("scripts.lib.telemetry.context._get_cwd", return_value="/repo/labs/bgp/lab-01"):
        with patch("scripts.lib.telemetry.context._get_branch", return_value="docs/lab-progression-guide"):
            ctx = resolve_lab_context()
    assert ctx["phase"] == "unknown"
```

- [ ] **Step 3.2: Run tests to confirm they fail**

```bash
pytest tests/telemetry/test_context.py -v
```

Expected: `ModuleNotFoundError` or `ImportError` — module doesn't exist yet.

- [ ] **Step 3.3: Create package markers**

```bash
touch scripts/lib/__init__.py
touch scripts/lib/telemetry/__init__.py
touch tests/__init__.py
touch tests/telemetry/__init__.py
```

- [ ] **Step 3.4: Implement context.py**

Create `scripts/lib/telemetry/context.py`:

```python
from __future__ import annotations
import subprocess
from pathlib import Path


def _get_cwd() -> str:
    return str(Path.cwd())


def _get_branch() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"


def resolve_lab_context() -> dict:
    cwd = _get_cwd()
    parts = Path(cwd).parts

    chapter = "unknown"
    name = "unknown"
    try:
        labs_idx = list(parts).index("labs")
        if labs_idx + 1 < len(parts):
            chapter = parts[labs_idx + 1]
        if labs_idx + 2 < len(parts):
            name = parts[labs_idx + 2]
    except ValueError:
        pass

    branch = _get_branch()
    if branch.startswith("spec/"):
        phase = "Phase 2 - Spec"
    elif branch.startswith("plan/"):
        phase = "Phase 1 - Plan"
    elif branch.startswith(("feat/", "fix/", "build/")):
        phase = "Phase 3 - Build"
    else:
        phase = "unknown"

    return {"chapter": chapter, "name": name, "phase": phase}
```

- [ ] **Step 3.5: Run tests to confirm they pass**

```bash
pytest tests/telemetry/test_context.py -v
```

Expected: all 7 tests PASS.

- [ ] **Step 3.6: Commit**

```bash
git add scripts/lib/__init__.py scripts/lib/telemetry/__init__.py \
        scripts/lib/telemetry/context.py \
        tests/__init__.py tests/telemetry/__init__.py \
        tests/telemetry/test_context.py
git commit -m "feat(telemetry): context resolver with TDD"
```

---

## Task 4: Git File Extractor — TDD

Gets the list of files modified since the skill invocation started using `git diff`.

**Files:**
- Create: `scripts/lib/telemetry/git_files.py`
- Create: `tests/telemetry/test_git_files.py`

- [ ] **Step 4.1: Write failing tests**

Create `tests/telemetry/test_git_files.py`:

```python
import pytest
from unittest.mock import patch
from scripts.lib.telemetry.git_files import get_files_touched


def test_returns_list_of_changed_files():
    mock_output = "labs/ospf/lab-00/spec.md\nlabs/ospf/lab-00/baseline.yaml\n"
    with patch("scripts.lib.telemetry.git_files._run_git_diff", return_value=mock_output):
        files = get_files_touched()
    assert files == ["labs/ospf/lab-00/spec.md", "labs/ospf/lab-00/baseline.yaml"]


def test_returns_empty_list_when_no_changes():
    with patch("scripts.lib.telemetry.git_files._run_git_diff", return_value=""):
        files = get_files_touched()
    assert files == []


def test_strips_whitespace_from_file_paths():
    mock_output = "  labs/ospf/lab-00/spec.md  \n"
    with patch("scripts.lib.telemetry.git_files._run_git_diff", return_value=mock_output):
        files = get_files_touched()
    assert files == ["labs/ospf/lab-00/spec.md"]


def test_returns_empty_list_on_git_error():
    with patch("scripts.lib.telemetry.git_files._run_git_diff", side_effect=Exception("git error")):
        files = get_files_touched()
    assert files == []
```

- [ ] **Step 4.2: Run tests to confirm they fail**

```bash
pytest tests/telemetry/test_git_files.py -v
```

Expected: `ImportError` — module doesn't exist yet.

- [ ] **Step 4.3: Implement git_files.py**

Create `scripts/lib/telemetry/git_files.py`:

```python
from __future__ import annotations
import subprocess


def _run_git_diff() -> str:
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD"],
        capture_output=True, text=True, check=True
    )
    return result.stdout


def get_files_touched() -> list[str]:
    try:
        raw = _run_git_diff()
        return [f.strip() for f in raw.splitlines() if f.strip()]
    except Exception:
        return []
```

- [ ] **Step 4.4: Run tests to confirm they pass**

```bash
pytest tests/telemetry/test_git_files.py -v
```

Expected: all 4 tests PASS.

- [ ] **Step 4.5: Commit**

```bash
git add scripts/lib/telemetry/git_files.py tests/telemetry/test_git_files.py
git commit -m "feat(telemetry): git file extractor with TDD"
```

---

## Task 5: Session Log Reader — TDD

Parses `~/.claude/projects/*/` JSONL files to extract token usage and model ID for the current session.

> **Note:** Update the field names below if the spike (Task 1) revealed different field names than expected. The exact fields in Claude Code session logs must match what the spike documented in `logs/_spike-notes.txt`.

**Files:**
- Create: `scripts/lib/telemetry/session_log.py`
- Create: `tests/telemetry/test_session_log.py`

- [ ] **Step 5.1: Write failing tests**

Create `tests/telemetry/test_session_log.py`:

```python
import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from scripts.lib.telemetry.session_log import extract_usage


SAMPLE_SESSION_LINES = [
    json.dumps({"type": "human", "message": {"content": "hello"}}),
    json.dumps({
        "type": "assistant",
        "message": {
            "model": "claude-haiku-4-5-20251001",
            "usage": {
                "input_tokens": 4250,
                "output_tokens": 1820,
                "cache_creation_input_tokens": 100,
                "cache_read_input_tokens": 200
            }
        }
    }),
]


def test_extracts_token_counts_from_last_assistant_turn(tmp_path):
    session_id = "test-session-abc123"
    project_dir = tmp_path / "projects" / "somehash"
    project_dir.mkdir(parents=True)
    log_file = project_dir / f"{session_id}.jsonl"
    log_file.write_text("\n".join(SAMPLE_SESSION_LINES))

    with patch("scripts.lib.telemetry.session_log._find_project_dir", return_value=project_dir):
        result = extract_usage(session_id)

    assert result["input"] == 4250
    assert result["output"] == 1820
    assert result["cache_creation"] == 100
    assert result["cache_read"] == 200


def test_extracts_model_from_last_assistant_turn(tmp_path):
    session_id = "test-session-abc123"
    project_dir = tmp_path / "projects" / "somehash"
    project_dir.mkdir(parents=True)
    log_file = project_dir / f"{session_id}.jsonl"
    log_file.write_text("\n".join(SAMPLE_SESSION_LINES))

    with patch("scripts.lib.telemetry.session_log._find_project_dir", return_value=project_dir):
        result = extract_usage(session_id)

    assert result["model"] == "claude-haiku-4-5-20251001"


def test_returns_zeros_when_session_not_found(tmp_path):
    with patch("scripts.lib.telemetry.session_log._find_project_dir", return_value=tmp_path / "missing"):
        result = extract_usage("nonexistent-session")

    assert result["input"] == 0
    assert result["output"] == 0
    assert result["model"] == "unknown"


def test_returns_zeros_on_malformed_log(tmp_path):
    session_id = "bad-session"
    project_dir = tmp_path / "projects" / "somehash"
    project_dir.mkdir(parents=True)
    log_file = project_dir / f"{session_id}.jsonl"
    log_file.write_text("not json at all\n{broken")

    with patch("scripts.lib.telemetry.session_log._find_project_dir", return_value=project_dir):
        result = extract_usage(session_id)

    assert result["input"] == 0
    assert result["model"] == "unknown"
```

- [ ] **Step 5.2: Run tests to confirm they fail**

```bash
pytest tests/telemetry/test_session_log.py -v
```

Expected: `ImportError` — module doesn't exist yet.

- [ ] **Step 5.3: Implement session_log.py**

Create `scripts/lib/telemetry/session_log.py`:

```python
from __future__ import annotations
import json
from pathlib import Path


_ZERO = {
    "input": 0, "output": 0,
    "cache_creation": 0, "cache_read": 0,
    "model": "unknown"
}


def _find_project_dir() -> Path:
    return Path.home() / ".claude" / "projects"


def extract_usage(session_id: str) -> dict:
    try:
        projects_root = _find_project_dir()
        if not projects_root.exists():
            return dict(_ZERO)

        # Search all project dirs for the session file
        log_file = None
        for project_dir in projects_root.iterdir():
            candidate = project_dir / f"{session_id}.jsonl"
            if candidate.exists():
                log_file = candidate
                break

        if log_file is None:
            return dict(_ZERO)

        last_usage = None
        last_model = "unknown"
        for line in log_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("type") == "assistant":
                msg = entry.get("message", {})
                usage = msg.get("usage", {})
                if usage:
                    last_usage = usage
                    last_model = msg.get("model", "unknown")

        if last_usage is None:
            return dict(_ZERO)

        return {
            "input": last_usage.get("input_tokens", 0),
            "output": last_usage.get("output_tokens", 0),
            "cache_creation": last_usage.get("cache_creation_input_tokens", 0),
            "cache_read": last_usage.get("cache_read_input_tokens", 0),
            "model": last_model,
        }
    except Exception:
        return dict(_ZERO)
```

- [ ] **Step 5.4: Run tests to confirm they pass**

```bash
pytest tests/telemetry/test_session_log.py -v
```

Expected: all 4 tests PASS.

- [ ] **Step 5.5: Commit**

```bash
git add scripts/lib/telemetry/session_log.py tests/telemetry/test_session_log.py
git commit -m "feat(telemetry): session log reader with TDD"
```

---

## Task 6: JSONL Formatter — TDD

Assembles the final JSONL dict from all components.

**Files:**
- Create: `scripts/lib/telemetry/formatter.py`
- Create: `tests/telemetry/test_formatter.py`

- [ ] **Step 6.1: Write failing tests**

Create `tests/telemetry/test_formatter.py`:

```python
import json
import pytest
from scripts.lib.telemetry.formatter import build_entry


def _sample_entry():
    return build_entry(
        skill_name="spec-creator",
        invocation_id="test-uuid-1234",
        context={"chapter": "ospf", "name": "lab-00-single-area-ospfv2", "phase": "Phase 2 - Spec"},
        usage={"input": 4250, "output": 1820, "cache_creation": 0, "cache_read": 0, "model": "claude-haiku-4-5-20251001"},
        files_touched=["labs/ospf/lab-00/spec.md"],
        duration_seconds=87.4,
        success=True,
        error=None,
    )


def test_entry_is_valid_json():
    entry = _sample_entry()
    assert json.dumps(entry)  # should not raise


def test_entry_has_all_required_keys():
    entry = _sample_entry()
    assert "timestamp" in entry
    assert "lab" in entry
    assert "skill" in entry
    assert "model" in entry
    assert "tokens" in entry
    assert "advisor" in entry
    assert "files_touched" in entry
    assert "execution" in entry


def test_skill_fields_populated():
    entry = _sample_entry()
    assert entry["skill"]["name"] == "spec-creator"
    assert entry["skill"]["invocation_id"] == "test-uuid-1234"


def test_token_fields_populated():
    entry = _sample_entry()
    assert entry["tokens"]["input"] == 4250
    assert entry["tokens"]["output"] == 1820
    assert entry["tokens"]["cache_creation"] == 0
    assert entry["tokens"]["cache_read"] == 0


def test_execution_fields_populated():
    entry = _sample_entry()
    assert entry["execution"]["success"] is True
    assert entry["execution"]["error"] is None
    assert entry["execution"]["duration_seconds"] == 87.4


def test_error_entry_has_error_message():
    entry = build_entry(
        skill_name="spec-creator",
        invocation_id="test-uuid-9999",
        context={"chapter": "unknown", "name": "unknown", "phase": "unknown"},
        usage={"input": 0, "output": 0, "cache_creation": 0, "cache_read": 0, "model": "unknown"},
        files_touched=[],
        duration_seconds=3.2,
        success=False,
        error="Skill timed out",
    )
    assert entry["execution"]["success"] is False
    assert entry["execution"]["error"] == "Skill timed out"


def test_advisor_defaults_to_not_used():
    entry = _sample_entry()
    assert entry["advisor"]["used"] is False
    assert entry["advisor"]["savings_tokens"] == 0
    assert entry["advisor"]["cost_tokens"] == 0
```

- [ ] **Step 6.2: Run tests to confirm they fail**

```bash
pytest tests/telemetry/test_formatter.py -v
```

Expected: `ImportError` — module doesn't exist yet.

- [ ] **Step 6.3: Implement formatter.py**

Create `scripts/lib/telemetry/formatter.py`:

```python
from __future__ import annotations
from datetime import datetime, timezone


def build_entry(
    skill_name: str,
    invocation_id: str,
    context: dict,
    usage: dict,
    files_touched: list[str],
    duration_seconds: float,
    success: bool,
    error: str | None,
) -> dict:
    return {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "lab": {
            "chapter": context.get("chapter", "unknown"),
            "name": context.get("name", "unknown"),
            "phase": context.get("phase", "unknown"),
        },
        "skill": {
            "name": skill_name,
            "invocation_id": invocation_id,
        },
        "model": usage.get("model", "unknown"),
        "tokens": {
            "input": usage.get("input", 0),
            "output": usage.get("output", 0),
            "cache_creation": usage.get("cache_creation", 0),
            "cache_read": usage.get("cache_read", 0),
        },
        "advisor": {
            "used": False,
            "savings_tokens": 0,
            "cost_tokens": 0,
        },
        "files_touched": files_touched,
        "execution": {
            "duration_seconds": round(duration_seconds, 2),
            "success": success,
            "error": error,
        },
    }
```

- [ ] **Step 6.4: Run tests to confirm they pass**

```bash
pytest tests/telemetry/test_formatter.py -v
```

Expected: all 7 tests PASS.

- [ ] **Step 6.5: Run full test suite to confirm no regressions**

```bash
pytest tests/telemetry/ -v
```

Expected: all tests across all telemetry test files PASS.

- [ ] **Step 6.6: Commit**

```bash
git add scripts/lib/telemetry/formatter.py tests/telemetry/test_formatter.py
git commit -m "feat(telemetry): JSONL formatter with TDD"
```

---

## Task 7: Main Logger Entrypoint

Wires all components together. Reads stdin from hook, orchestrates components, appends JSONL, handles all errors.

**Files:**
- Create: `scripts/log-telemetry.py`

- [ ] **Step 7.1: Create the main logger**

Create `scripts/log-telemetry.py`:

```python
#!/usr/bin/env python3
"""
Claude Code hook entrypoint: fires after each Skill tool invocation.
Reads JSON payload from stdin, captures telemetry, appends to logs/telemetry.jsonl.
Never raises — all errors go to logs/telemetry-errors.log.
"""
from __future__ import annotations

import json
import sys
import time
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Allow imports from scripts/lib/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.lib.telemetry.context import resolve_lab_context
from scripts.lib.telemetry.git_files import get_files_touched
from scripts.lib.telemetry.session_log import extract_usage
from scripts.lib.telemetry.formatter import build_entry

LOG_FILE = Path(__file__).resolve().parent.parent / "logs" / "telemetry.jsonl"
ERR_FILE = Path(__file__).resolve().parent.parent / "logs" / "telemetry-errors.log"


def _log_error(msg: str) -> None:
    ERR_FILE.parent.mkdir(exist_ok=True)
    with ERR_FILE.open("a", encoding="utf-8") as f:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        f.write(f"[{ts}] {msg}\n")


def main() -> None:
    start_time = time.monotonic()

    try:
        payload = json.load(sys.stdin)
    except Exception as e:
        _log_error(f"Failed to parse hook stdin: {e}")
        return

    try:
        tool_input = payload.get("tool_input", {})
        skill_name = tool_input.get("skill", "unknown")
        session_id = payload.get("session_id", "")
        tool_response = payload.get("tool_response", "")

        success = True
        error_msg = None
        if isinstance(tool_response, str) and "error" in tool_response.lower():
            success = False
            error_msg = tool_response[:500]

        duration = round(time.monotonic() - start_time, 2)
        invocation_id = str(uuid.uuid4())

        context = resolve_lab_context()
        files = get_files_touched()
        usage = extract_usage(session_id) if session_id else {
            "input": 0, "output": 0, "cache_creation": 0, "cache_read": 0, "model": "unknown"
        }

        entry = build_entry(
            skill_name=skill_name,
            invocation_id=invocation_id,
            context=context,
            usage=usage,
            files_touched=files,
            duration_seconds=duration,
            success=success,
            error=error_msg,
        )

        LOG_FILE.parent.mkdir(exist_ok=True)
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    except Exception:
        _log_error(traceback.format_exc())


if __name__ == "__main__":
    main()
```

- [ ] **Step 7.2: Make the script executable**

```bash
chmod +x scripts/log-telemetry.py
```

- [ ] **Step 7.3: Smoke test the script manually**

```bash
echo '{"session_id": "test-123", "tool_name": "Skill", "tool_input": {"skill": "spec-creator", "args": ""}, "tool_response": "done"}' \
  | python3 scripts/log-telemetry.py

cat logs/telemetry.jsonl
```

Expected: one JSON line in `logs/telemetry.jsonl` with `skill.name == "spec-creator"`, valid structure, no errors in `logs/telemetry-errors.log`.

- [ ] **Step 7.4: Commit**

```bash
git add scripts/log-telemetry.py
git commit -m "feat(telemetry): main logger entrypoint"
```

---

## Task 8: Hook Configuration

Wire the logger into Claude Code's `PostToolUse` hook.

**Files:**
- Modify: `.claude/settings.json`

- [ ] **Step 8.1: Update settings.json**

Replace `.claude/settings.json` with:

```json
{
  "enabledPlugins": {
    "commit-commands@claude-plugins-official": true
  },
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Skill",
        "hooks": [
          {
            "type": "command",
            "command": "python3 scripts/log-telemetry.py"
          }
        ]
      }
    ]
  }
}
```

> **Important:** If the spike (Task 1) revealed that the hook payload structure differs from what `log-telemetry.py` expects, update the field references in `scripts/log-telemetry.py` `main()` before this step.

- [ ] **Step 8.2: Commit**

```bash
git add .claude/settings.json
git commit -m "feat(telemetry): configure PostToolUse hook for Skill tool"
```

---

## Task 9: Integration Test

Verify the full end-to-end flow with a real skill invocation.

- [ ] **Step 9.1: Start a fresh Claude Code session**

Open Claude Code in this project directory. The hook will be active on session start.

- [ ] **Step 9.2: Invoke any skill**

Run any quick skill (e.g., `diagram` or ask Claude Code to invoke `tag-lab`).

- [ ] **Step 9.3: Verify telemetry was captured**

```bash
# Check a log entry was created
cat logs/telemetry.jsonl | python3 -m json.tool

# Confirm expected fields
cat logs/telemetry.jsonl | python3 -c "
import json, sys
entry = json.loads(sys.stdin.readline())
print('skill:', entry['skill']['name'])
print('chapter:', entry['lab']['chapter'])
print('model:', entry['model'])
print('input tokens:', entry['tokens']['input'])
print('success:', entry['execution']['success'])
"
```

Expected: output shows the skill name, a chapter (or "unknown" if not in a lab directory), a model string, and a token count > 0 (or 0 if session log fallback didn't find data — check `logs/_spike-notes.txt` for whether token data was accessible).

- [ ] **Step 9.4: Check for logger errors**

```bash
cat logs/telemetry-errors.log 2>/dev/null || echo "No errors — clean run"
```

Expected: "No errors — clean run" or the file is empty.

- [ ] **Step 9.5: Clean up spike artifacts**

```bash
rm -f scripts/_hook-spike.py logs/_spike-payload.json logs/_spike-env.txt
git add -u
git commit -m "chore: remove spike artifacts"
```

- [ ] **Step 9.6: Final commit — tag completion**

```bash
git add .
git commit -m "feat(telemetry): complete lab build telemetry system"
```

---

## Post-Implementation Note on Token Data

If the spike (Task 1) reveals that session logs do NOT store per-skill token counts (only session-level totals), the telemetry entries will have accurate `input` and `output` totals for the whole session but not per-skill isolation. In that case, add a `note` field to each entry:

```json
"tokens": {
  "input": 4250,
  "output": 1820,
  "note": "session-total, not per-skill"
}
```

This is still useful for relative comparisons across labs and chapters. Per-skill isolation can be approximated by diffing consecutive session-total snapshots.
