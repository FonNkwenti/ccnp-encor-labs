import pytest
from unittest.mock import patch
from scripts.lib.telemetry.context import resolve_lab_context


def test_resolves_chapter_from_lab_path():
    with patch("scripts.lib.telemetry.context._get_cwd", return_value="/repo/labs/ospf/lab-00-single-area-ospfv2"):
        ctx = resolve_lab_context()
    assert ctx["chapter"] == "ospf"


def test_resolves_lab_name_from_lab_path():
    with patch("scripts.lib.telemetry.context._get_cwd", return_value="/repo/labs/ospf/lab-00-single-area-ospfv2"):
        ctx = resolve_lab_context()
    assert ctx["name"] == "lab-00-single-area-ospfv2"


def test_files_hint_takes_priority_over_cwd():
    files = ["labs/automation/lab-05-capstone-troubleshoot/workbook.md"]
    with patch("scripts.lib.telemetry.context._get_cwd", return_value="/repo"):
        ctx = resolve_lab_context(files_hint=files)
    assert ctx["chapter"] == "automation"
    assert ctx["name"] == "lab-05-capstone-troubleshoot"


def test_falls_back_to_cwd_when_no_lab_in_files():
    files = ["tasks/todo.md", "docs/README.md"]
    with patch("scripts.lib.telemetry.context._get_cwd", return_value="/repo/labs/ospf/lab-00"):
        ctx = resolve_lab_context(files_hint=files)
    assert ctx["chapter"] == "ospf"
    assert ctx["name"] == "lab-00"


def test_resolves_phase_from_branch_name_spec():
    with patch("scripts.lib.telemetry.context._get_cwd", return_value="/repo/labs/ospf/lab-00-single-area-ospfv2"):
        with patch("scripts.lib.telemetry.context._get_branch", return_value="spec/ospf-lab-00"):
            ctx = resolve_lab_context()
    assert ctx["phase"] == "Phase 2 - Spec"


def test_resolves_phase_from_branch_name_build():
    with patch("scripts.lib.telemetry.context._get_cwd", return_value="/repo/labs/ospf/lab-00-single-area-ospfv2"):
        with patch("scripts.lib.telemetry.context._get_branch", return_value="feat/ospf-lab-00"):
            ctx = resolve_lab_context()
    assert ctx["phase"] == "Phase 3 - Build"


def test_resolves_phase_from_branch_name_plan():
    with patch("scripts.lib.telemetry.context._get_cwd", return_value="/repo/labs/ospf/lab-00-single-area-ospfv2"):
        with patch("scripts.lib.telemetry.context._get_branch", return_value="plan/ospf-lab-00"):
            ctx = resolve_lab_context()
    assert ctx["phase"] == "Phase 1 - Plan"


def test_phase_inferred_from_skill_name_when_branch_unrecognized():
    with patch("scripts.lib.telemetry.context._get_cwd", return_value="/repo"):
        with patch("scripts.lib.telemetry.context._get_branch", return_value="docs/lab-progression-guide"):
            ctx = resolve_lab_context(skill_name="lab-workbook-creator")
    assert ctx["phase"] == "Phase 3 - Build"


def test_phase_inferred_spec_creator():
    with patch("scripts.lib.telemetry.context._get_cwd", return_value="/repo"):
        with patch("scripts.lib.telemetry.context._get_branch", return_value="docs/something"):
            ctx = resolve_lab_context(skill_name="spec-creator")
    assert ctx["phase"] == "Phase 2 - Spec"


def test_unknown_chapter_when_not_in_labs_dir():
    with patch("scripts.lib.telemetry.context._get_cwd", return_value="/repo"):
        ctx = resolve_lab_context()
    assert ctx["chapter"] == "unknown"
    assert ctx["name"] == "unknown"


def test_unknown_phase_for_unrecognized_branch_and_skill():
    with patch("scripts.lib.telemetry.context._get_cwd", return_value="/repo/labs/bgp/lab-01"):
        with patch("scripts.lib.telemetry.context._get_branch", return_value="docs/lab-progression-guide"):
            ctx = resolve_lab_context(skill_name="diagram")
    assert ctx["phase"] == "unknown"
