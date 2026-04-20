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
        # Untracked first — skill builds create new files; pre-existing diffs follow
        untracked = _run_git_ls_others()
        tracked = _run_git_diff_labs()
        return [f.strip() for f in (untracked + tracked).splitlines() if f.strip()]
    except Exception:
        return []
