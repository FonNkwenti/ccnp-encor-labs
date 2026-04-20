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
