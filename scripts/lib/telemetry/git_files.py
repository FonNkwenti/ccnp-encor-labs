from __future__ import annotations
import subprocess


def _run_git_diff_labs() -> str:
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD", "--", "labs/"],
        capture_output=True, text=True, check=True
    )
    return result.stdout


def _run_git_ls_others() -> str:
    result = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard", "--", "labs/"],
        capture_output=True, text=True, check=True
    )
    return result.stdout


def get_files_touched() -> list[str]:
    try:
        tracked = _run_git_diff_labs()
        untracked = _run_git_ls_others()
        return [f.strip() for f in (tracked + untracked).splitlines() if f.strip()]
    except Exception:
        return []
