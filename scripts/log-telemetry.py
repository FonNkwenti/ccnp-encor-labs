#!/usr/bin/env python3
"""
Claude Code hook entrypoint: fires after each Skill tool invocation.
Reads JSON payload from stdin, captures telemetry, appends to logs/telemetry.jsonl.
Never raises — all errors go to logs/telemetry-errors.log.
"""
from __future__ import annotations

import json
import sys
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

        invocation_id = str(uuid.uuid4())

        files = get_files_touched()
        context = resolve_lab_context(files_hint=files, skill_name=skill_name)
        usage = extract_usage(session_id) if session_id else {
            "input": 0, "output": 0, "cache_creation": 0, "cache_read": 0,
            "model": "unknown", "duration_seconds": 0.0,
        }
        duration = usage.get("duration_seconds", 0.0)

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
