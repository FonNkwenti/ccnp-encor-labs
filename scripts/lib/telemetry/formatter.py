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
        "effort_level": usage.get("speed", "unknown"),
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
