from __future__ import annotations
import subprocess
from pathlib import Path

_SKILL_PHASE_MAP = {
    "lab-assembler": "Phase 3 - Build",
    "build-labs": "Phase 3 - Build",
    "lab-builder": "Phase 3 - Build",
    "mega-capstone-creator": "Phase 3 - Build",
    "capstone": "Phase 3 - Build",
    "fault-injector": "Phase 3 - Build",
    "inject-faults": "Phase 3 - Build",
    "spec-creator": "Phase 2 - Spec",
    "create-spec": "Phase 2 - Spec",
    "exam-planner": "Phase 1 - Plan",
    "plan-exam": "Phase 1 - Plan",
}


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


def _extract_from_files(files: list[str]) -> tuple[str, str]:
    for f in files:
        parts = Path(f).parts
        try:
            labs_idx = list(parts).index("labs")
            if labs_idx + 2 < len(parts):
                return parts[labs_idx + 1], parts[labs_idx + 2]
        except ValueError:
            continue
    return "unknown", "unknown"


def _extract_from_cwd(cwd: str) -> tuple[str, str]:
    parts = Path(cwd).parts
    try:
        labs_idx = list(parts).index("labs")
        chapter = parts[labs_idx + 1] if labs_idx + 1 < len(parts) else "unknown"
        name = parts[labs_idx + 2] if labs_idx + 2 < len(parts) else "unknown"
        return chapter, name
    except ValueError:
        return "unknown", "unknown"


def resolve_lab_context(
    files_hint: list[str] | None = None,
    skill_name: str | None = None,
) -> dict:
    chapter, name = _extract_from_files(files_hint or [])
    if chapter == "unknown":
        chapter, name = _extract_from_cwd(_get_cwd())

    branch = _get_branch()
    if branch.startswith("spec/"):
        phase = "Phase 2 - Spec"
    elif branch.startswith("plan/"):
        phase = "Phase 1 - Plan"
    elif branch.startswith(("feat/", "fix/", "build/")):
        phase = "Phase 3 - Build"
    elif skill_name and skill_name in _SKILL_PHASE_MAP:
        phase = _SKILL_PHASE_MAP[skill_name]
    else:
        phase = "unknown"

    return {"chapter": chapter, "name": name, "phase": phase}
