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


SKILL_DURATION_LINES = [
    json.dumps({
        "type": "assistant",
        "uuid": "asst-uuid-001",
        "timestamp": "2026-04-20T07:00:00.000Z",
        "message": {
            "model": "claude-sonnet-4-6",
            "usage": {"input_tokens": 100, "output_tokens": 50,
                      "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0},
            "content": [
                {"type": "tool_use", "name": "Skill", "id": "toolu_abc",
                 "input": {"skill": "lab-assembler"}}
            ],
        },
    }),
    json.dumps({
        "type": "user",
        "uuid": "user-uuid-001",
        "timestamp": "2026-04-20T07:02:30.000Z",
        "sourceToolAssistantUUID": "asst-uuid-001",
        "toolUseResult": {"stdout": "done", "stderr": "", "interrupted": False},
        "message": {"content": [{"type": "tool_result", "tool_use_id": "toolu_abc"}]},
    }),
]


def test_extracts_skill_duration_from_session_log(tmp_path):
    session_id = "dur-session"
    project_dir = tmp_path / "projects" / "somehash"
    project_dir.mkdir(parents=True)
    (project_dir / f"{session_id}.jsonl").write_text("\n".join(SKILL_DURATION_LINES))

    with patch("scripts.lib.telemetry.session_log._find_project_dir", return_value=project_dir):
        result = extract_usage(session_id)

    assert result["duration_seconds"] == pytest.approx(150.0, rel=1e-3)


def test_duration_zero_when_no_skill_result(tmp_path):
    session_id = "no-result-session"
    project_dir = tmp_path / "projects" / "somehash"
    project_dir.mkdir(parents=True)
    (project_dir / f"{session_id}.jsonl").write_text("\n".join(SAMPLE_SESSION_LINES))

    with patch("scripts.lib.telemetry.session_log._find_project_dir", return_value=project_dir):
        result = extract_usage(session_id)

    assert result["duration_seconds"] == 0.0
