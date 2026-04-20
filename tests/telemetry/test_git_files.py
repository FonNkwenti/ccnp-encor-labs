import pytest
from unittest.mock import patch
from scripts.lib.telemetry.git_files import get_files_touched


def test_returns_tracked_lab_files():
    with patch("scripts.lib.telemetry.git_files._run_git_diff_labs",
               return_value="labs/ospf/lab-00/spec.md\n"):
        with patch("scripts.lib.telemetry.git_files._run_git_ls_others",
                   return_value=""):
            files = get_files_touched()
    assert files == ["labs/ospf/lab-00/spec.md"]


def test_returns_untracked_new_lab_files():
    with patch("scripts.lib.telemetry.git_files._run_git_diff_labs",
               return_value=""):
        with patch("scripts.lib.telemetry.git_files._run_git_ls_others",
                   return_value="labs/automation/lab-05/workbook.md\n"):
            files = get_files_touched()
    assert files == ["labs/automation/lab-05/workbook.md"]


def test_combines_tracked_and_untracked():
    with patch("scripts.lib.telemetry.git_files._run_git_diff_labs",
               return_value="labs/ospf/lab-00/spec.md\n"):
        with patch("scripts.lib.telemetry.git_files._run_git_ls_others",
                   return_value="labs/ospf/lab-00/baseline.yaml\n"):
            files = get_files_touched()
    assert "labs/ospf/lab-00/spec.md" in files
    assert "labs/ospf/lab-00/baseline.yaml" in files


def test_returns_empty_list_when_no_changes():
    with patch("scripts.lib.telemetry.git_files._run_git_diff_labs", return_value=""):
        with patch("scripts.lib.telemetry.git_files._run_git_ls_others", return_value=""):
            files = get_files_touched()
    assert files == []


def test_strips_whitespace_from_file_paths():
    with patch("scripts.lib.telemetry.git_files._run_git_diff_labs",
               return_value="  labs/ospf/lab-00/spec.md  \n"):
        with patch("scripts.lib.telemetry.git_files._run_git_ls_others", return_value=""):
            files = get_files_touched()
    assert files == ["labs/ospf/lab-00/spec.md"]


def test_returns_empty_list_on_git_error():
    with patch("scripts.lib.telemetry.git_files._run_git_diff_labs",
               side_effect=Exception("git error")):
        files = get_files_touched()
    assert files == []
