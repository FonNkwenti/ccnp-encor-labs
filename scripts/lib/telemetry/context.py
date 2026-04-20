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
