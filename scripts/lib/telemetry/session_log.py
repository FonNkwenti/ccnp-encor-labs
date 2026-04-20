from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path


_ZERO = {
    "input": 0, "output": 0,
    "cache_creation": 0, "cache_read": 0,
    "model": "unknown", "speed": "unknown",
    "duration_seconds": 0.0,
}


def _parse_ts(ts: str) -> float:
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()


def _find_project_dir() -> Path:
    # Claude Code names project dirs by replacing path separators with dashes.
    # Windows: C:\Users\...\project → C--Users-...-project
    # Unix:    /home/user/project   → home-user-project
    cwd = str(Path.cwd())
    dir_name = cwd.replace(":", "-").replace("\\", "-").replace("/", "-").lstrip("-")
    return Path.home() / ".claude" / "projects" / dir_name


def extract_usage(session_id: str) -> dict:
    try:
        log_file = _find_project_dir() / f"{session_id}.jsonl"
        if not log_file.exists():
            return dict(_ZERO)

        last_usage = None
        last_model = "unknown"
        # uuid -> timestamp for assistant entries that contain a Skill tool_use
        skill_call_ts: dict[str, float] = {}

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
                for c in msg.get("content", []):
                    if isinstance(c, dict) and c.get("type") == "tool_use" and c.get("name") == "Skill":
                        ts = entry.get("timestamp", "")
                        if ts and entry.get("uuid"):
                            skill_call_ts[entry["uuid"]] = _parse_ts(ts)

        # Walk again to find tool results that close a Skill call
        last_duration = 0.0
        for line in log_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("type") == "user" and entry.get("sourceToolAssistantUUID"):
                src = entry["sourceToolAssistantUUID"]
                if src in skill_call_ts:
                    end_ts = entry.get("timestamp", "")
                    if end_ts:
                        last_duration = round(_parse_ts(end_ts) - skill_call_ts[src], 2)

        if last_usage is None:
            return dict(_ZERO)

        return {
            "input": last_usage.get("input_tokens", 0),
            "output": last_usage.get("output_tokens", 0),
            "cache_creation": last_usage.get("cache_creation_input_tokens", 0),
            "cache_read": last_usage.get("cache_read_input_tokens", 0),
            "model": last_model,
            "speed": last_usage.get("speed", "unknown"),
            "duration_seconds": last_duration,
        }
    except Exception:
        return dict(_ZERO)
