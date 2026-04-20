import json
import pytest
from unittest.mock import patch
from pathlib import Path
from scripts.lib.telemetry.session_log import extract_usage


SAMPLE_SESSION_LINES = [
    json.dumps({"type": "human", "message": {"content": "hello"}}),
    json.dumps({
        "type": "assistant",
        "message": {
            "model": "claude-haiku-4-5-20251001",
            "usage": {
                "input_tokens": 4250,
                "output_tokens": 1820,
                "cache_creation_input_tokens": 100,
                "cache_read_input_tokens": 200,
                "speed": "fast"
            }
        }
    }),
]


def test_extracts_token_counts_from_last_assistant_turn(tmp_path):
    session_id = "test-session-abc123"
    project_dir = tmp_path / "projects" / "somehash"
    project_dir.mkdir(parents=True)
    log_file = project_dir / f"{session_id}.jsonl"
    log_file.write_text("\n".join(SAMPLE_SESSION_LINES))

    with patch("scripts.lib.telemetry.session_log._find_project_dir", return_value=project_dir):
        result = extract_usage(session_id)

    assert result["input"] == 4250
    assert result["output"] == 1820
    assert result["cache_creation"] == 100
    assert result["cache_read"] == 200


def test_extracts_model_from_last_assistant_turn(tmp_path):
    session_id = "test-session-abc123"
    project_dir = tmp_path / "projects" / "somehash"
    project_dir.mkdir(parents=True)
    log_file = project_dir / f"{session_id}.jsonl"
    log_file.write_text("\n".join(SAMPLE_SESSION_LINES))

    with patch("scripts.lib.telemetry.session_log._find_project_dir", return_value=project_dir):
        result = extract_usage(session_id)

    assert result["model"] == "claude-haiku-4-5-20251001"


def test_extracts_speed_from_last_assistant_turn(tmp_path):
    session_id = "test-session-abc123"
    project_dir = tmp_path / "projects" / "somehash"
    project_dir.mkdir(parents=True)
    log_file = project_dir / f"{session_id}.jsonl"
    log_file.write_text("\n".join(SAMPLE_SESSION_LINES))

    with patch("scripts.lib.telemetry.session_log._find_project_dir", return_value=project_dir):
        result = extract_usage(session_id)

    assert result["speed"] == "fast"


def test_returns_zeros_when_session_not_found(tmp_path):
    with patch("scripts.lib.telemetry.session_log._find_project_dir", return_value=tmp_path / "missing"):
        result = extract_usage("nonexistent-session")

    assert result["input"] == 0
    assert result["output"] == 0
    assert result["model"] == "unknown"


def test_returns_zeros_on_malformed_log(tmp_path):
    session_id = "bad-session"
    project_dir = tmp_path / "projects" / "somehash"
    project_dir.mkdir(parents=True)
    log_file = project_dir / f"{session_id}.jsonl"
    log_file.write_text("not json at all\n{broken")

    with patch("scripts.lib.telemetry.session_log._find_project_dir", return_value=project_dir):
        result = extract_usage(session_id)

    assert result["input"] == 0
    assert result["model"] == "unknown"
