import pytest
from unittest.mock import patch
from scripts.lib.telemetry.git_files import get_files_touched


def test_returns_list_of_changed_files():
    mock_output = "labs/ospf/lab-00/spec.md\nlabs/ospf/lab-00/baseline.yaml\n"
    with patch("scripts.lib.telemetry.git_files._run_git_diff", return_value=mock_output):
        files = get_files_touched()
    assert files == ["labs/ospf/lab-00/spec.md", "labs/ospf/lab-00/baseline.yaml"]


def test_returns_empty_list_when_no_changes():
    with patch("scripts.lib.telemetry.git_files._run_git_diff", return_value=""):
        files = get_files_touched()
    assert files == []


def test_strips_whitespace_from_file_paths():
    mock_output = "  labs/ospf/lab-00/spec.md  \n"
    with patch("scripts.lib.telemetry.git_files._run_git_diff", return_value=mock_output):
        files = get_files_touched()
    assert files == ["labs/ospf/lab-00/spec.md"]


def test_returns_empty_list_on_git_error():
    with patch("scripts.lib.telemetry.git_files._run_git_diff", side_effect=Exception("git error")):
        files = get_files_touched()
    assert files == []
