from __future__ import annotations
from datetime import datetime, timezone

# Prices in USD per million tokens (as of 2026-04)
_PRICING: list[tuple[str, dict]] = [
    ("claude-opus-4",    {"input": 15.00, "output": 75.00, "cache_creation": 18.75, "cache_read": 1.50}),
    ("claude-sonnet-4",  {"input":  3.00, "output": 15.00, "cache_creation":  3.75, "cache_read": 0.30}),
    ("claude-haiku-4",   {"input":  0.80, "output":  4.00, "cache_creation":  1.00, "cache_read": 0.08}),
]


def _get_rates(model: str) -> dict | None:
    for prefix, rates in _PRICING:
        if model.startswith(prefix):
            return rates
    return None


def _compute_cost(tokens: dict, model: str) -> dict:
    rates = _get_rates(model)
    if rates is None:
        return {"input": 0.0, "output": 0.0, "cache_creation": 0.0, "cache_read": 0.0, "total": 0.0}
    per_m = 1_000_000
    c_input    = tokens["input"]           * rates["input"]           / per_m
    c_output   = tokens["output"]          * rates["output"]          / per_m
    c_creation = tokens["cache_creation"]  * rates["cache_creation"]  / per_m
    c_read     = tokens["cache_read"]      * rates["cache_read"]      / per_m
    return {
        "input":          round(c_input,    6),
        "output":         round(c_output,   6),
        "cache_creation": round(c_creation, 6),
        "cache_read":     round(c_read,     6),
        "total":          round(c_input + c_output + c_creation + c_read, 6),
    }


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
        "cost_usd": _compute_cost(
            {
                "input":          usage.get("input", 0),
                "output":         usage.get("output", 0),
                "cache_creation": usage.get("cache_creation", 0),
                "cache_read":     usage.get("cache_read", 0),
            },
            usage.get("model", ""),
        ),
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
