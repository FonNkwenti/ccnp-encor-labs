#!/usr/bin/env python3
"""Analyze telemetry logs to show token usage by skill and model."""

import json
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# Set UTF-8 encoding for Windows console
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

LOG_FILE = Path(__file__).resolve().parent.parent / "logs" / "telemetry.jsonl"


def analyze_logs():
    """Parse and analyze telemetry logs."""
    entries = []

    with open(LOG_FILE) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                entries.append(entry)
            except json.JSONDecodeError:
                continue

    if not entries:
        print("No valid entries in telemetry log")
        return

    # Group by skill
    by_skill = defaultdict(lambda: {
        "count": 0,
        "total_tokens": 0,
        "input": 0,
        "output": 0,
        "cache_creation": 0,
        "cache_read": 0,
        "total_cost": 0,
        "models": defaultdict(int),
    })

    print("═" * 100)
    print("TELEMETRY ANALYSIS")
    print("═" * 100)
    print()

    # Process entries
    for entry in entries:
        skill = entry["skill"]["name"]
        tokens = entry["tokens"]

        # Skip synthetic/zero entries
        if tokens["input"] == 0 and tokens["output"] == 0 and tokens["cache_creation"] == 0:
            continue

        total_toks = (tokens["input"] + tokens["output"] +
                      tokens["cache_creation"] + tokens["cache_read"])

        by_skill[skill]["count"] += 1
        by_skill[skill]["total_tokens"] += total_toks
        by_skill[skill]["input"] += tokens["input"]
        by_skill[skill]["output"] += tokens["output"]
        by_skill[skill]["cache_creation"] += tokens["cache_creation"]
        by_skill[skill]["cache_read"] += tokens["cache_read"]
        by_skill[skill]["total_cost"] += entry["cost_usd"]["total"]
        by_skill[skill]["models"][entry["model"]] += 1

    # Sort by total tokens (descending)
    sorted_skills = sorted(
        by_skill.items(),
        key=lambda x: x[1]["total_tokens"],
        reverse=True
    )

    print("SKILLS BY TOTAL TOKEN USAGE")
    print("─" * 100)
    print(f"{'Skill':<30} {'Calls':>6} {'Total Tokens':>15} {'Cost USD':>12} {'Avg Tokens/Call':>16}")
    print("─" * 100)

    for skill, stats in sorted_skills:
        avg_tokens = stats["total_tokens"] / stats["count"] if stats["count"] > 0 else 0
        print(f"{skill:<30} {stats['count']:>6} {stats['total_tokens']:>15,} ${stats['total_cost']:>11.6f} {avg_tokens:>16,.0f}")

    print()
    print("DETAILED TOKEN BREAKDOWN BY SKILL")
    print("─" * 100)

    for skill, stats in sorted_skills:
        print(f"\n{skill}")
        print(f"  Calls:              {stats['count']}")
        print(f"  Models used:        {', '.join(f'{m} ({c}x)' for m, c in stats['models'].items())}")
        print(f"  Total tokens:       {stats['total_tokens']:,}")
        print(f"    ├─ Input:         {stats['input']:,} ({100*stats['input']/stats['total_tokens']:.1f}%)")
        print(f"    ├─ Output:        {stats['output']:,} ({100*stats['output']/stats['total_tokens']:.1f}%)")
        print(f"    ├─ Cache created: {stats['cache_creation']:,} ({100*stats['cache_creation']/stats['total_tokens']:.1f}%)")
        print(f"    └─ Cache read:    {stats['cache_read']:,} ({100*stats['cache_read']/stats['total_tokens']:.1f}%)")
        print(f"  Total cost:         ${stats['total_cost']:.6f}")
        avg_cost = stats['total_cost'] / stats['total_tokens'] if stats['total_tokens'] > 0 else 0
        print(f"  Cost per token:     ${avg_cost:.8f}")

    print()
    print("INDIVIDUAL INVOCATIONS (MOST EXPENSIVE FIRST)")
    print("─" * 100)
    print(f"{'Timestamp':<25} {'Skill':<30} {'Total Tokens':>15} {'Cost':>12}")
    print("─" * 100)

    # Sort entries by cost (descending)
    sorted_entries = sorted(
        [e for e in entries if e["tokens"]["input"] > 0 or e["tokens"]["output"] > 0],
        key=lambda x: x["cost_usd"]["total"],
        reverse=True
    )

    for entry in sorted_entries:
        tokens = entry["tokens"]
        total_toks = (tokens["input"] + tokens["output"] +
                      tokens["cache_creation"] + tokens["cache_read"])
        ts = entry["timestamp"][:19]  # YYYY-MM-DDTHH:MM:SS
        print(f"{ts:<25} {entry['skill']['name']:<30} {total_toks:>15,} ${entry['cost_usd']['total']:>11.6f}")

    # Summary
    print()
    print("SUMMARY")
    print("─" * 100)
    total_tokens = sum(stats["total_tokens"] for stats in by_skill.values())
    total_cost = sum(stats["total_cost"] for stats in by_skill.values())
    total_calls = sum(stats["count"] for stats in by_skill.values())
    print(f"Total skill invocations: {total_calls}")
    print(f"Total tokens used:       {total_tokens:,}")
    print(f"Total cost:              ${total_cost:.6f}")
    print(f"Average tokens/call:     {total_tokens/total_calls:,.0f}")
    print(f"Average cost/call:       ${total_cost/total_calls:.6f}")


if __name__ == "__main__":
    analyze_logs()
