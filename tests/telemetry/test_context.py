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


def test_unknown_chapter_when_not_in_labs_dir():
    with patch("scripts.lib.telemetry.context._get_cwd", return_value="/repo"):
        ctx = resolve_lab_context()
    assert ctx["chapter"] == "unknown"
    assert ctx["name"] == "unknown"


def test_unknown_phase_for_unrecognized_branch():
    with patch("scripts.lib.telemetry.context._get_cwd", return_value="/repo/labs/bgp/lab-01"):
        with patch("scripts.lib.telemetry.context._get_branch", return_value="docs/lab-progression-guide"):
            ctx = resolve_lab_context()
    assert ctx["phase"] == "unknown"
