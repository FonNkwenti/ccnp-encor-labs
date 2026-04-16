#!/usr/bin/env python3
"""
Register foundation skills with Claude Code.

Claude Code's `Skill` tool discovers skills under `.claude/skills/<name>/SKILL.md`.
This project's skills live at `.agent/skills/<name>/SKILL.md` (git submodule).
To make the Skill tool find them without duplicating files, we create a junction
(Windows) or symlink (POSIX) for each skill directory.

Run once after fresh clone or after `git submodule update`. Safe to re-run.

Usage:
    python3 scripts/register-skills.py
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    src = root / ".agent" / "skills"
    dst = root / ".claude" / "skills"

    if not src.is_dir():
        print(f"[!] Skill source not found: {src}", file=sys.stderr)
        print("    Run: git submodule update --init --recursive", file=sys.stderr)
        return 1

    skills = sorted(
        p.name for p in src.iterdir()
        if p.is_dir() and (p / "SKILL.md").is_file()
    )
    if not skills:
        print(f"[!] No skills (SKILL.md files) found under {src}", file=sys.stderr)
        return 1

    dst.mkdir(parents=True, exist_ok=True)
    is_windows = sys.platform.startswith("win")
    ok, fail = 0, 0

    for name in skills:
        link = dst / name
        target = src / name
        if link.exists() or link.is_symlink():
            print(f"[=] {name}: already registered")
            ok += 1
            continue
        try:
            if is_windows:
                subprocess.run(
                    ["cmd", "/c", "mklink", "/J", str(link), str(target)],
                    check=True, capture_output=True, text=True,
                )
            else:
                os.symlink(target, link, target_is_directory=True)
            print(f"[+] {name}: linked -> {target}")
            ok += 1
        except Exception as exc:
            print(f"[!] {name}: failed -- {exc}", file=sys.stderr)
            fail += 1

    print()
    print(f"Registered {ok} skill(s). {fail} failure(s).")
    print("Note: Claude Code picks up new skills on the next session start.")
    return 0 if fail == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
