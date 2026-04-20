import json
import pytest
from scripts.lib.telemetry.formatter import build_entry


def _sample_entry():
    return build_entry(
        skill_name="spec-creator",
        invocation_id="test-uuid-1234",
        context={"chapter": "ospf", "name": "lab-00-single-area-ospfv2", "phase": "Phase 2 - Spec"},
        usage={"input": 4250, "output": 1820, "cache_creation": 0, "cache_read": 0, "model": "claude-haiku-4-5-20251001"},
        files_touched=["labs/ospf/lab-00/spec.md"],
        duration_seconds=87.4,
        success=True,
        error=None,
    )


def test_entry_is_valid_json():
    entry = _sample_entry()
    assert json.dumps(entry)


def test_entry_has_all_required_keys():
    entry = _sample_entry()
    assert "timestamp" in entry
    assert "lab" in entry
    assert "skill" in entry
    assert "model" in entry
    assert "tokens" in entry
    assert "advisor" in entry
    assert "files_touched" in entry
    assert "execution" in entry


def test_skill_fields_populated():
    entry = _sample_entry()
    assert entry["skill"]["name"] == "spec-creator"
    assert entry["skill"]["invocation_id"] == "test-uuid-1234"


def test_token_fields_populated():
    entry = _sample_entry()
    assert entry["tokens"]["input"] == 4250
    assert entry["tokens"]["output"] == 1820
    assert entry["tokens"]["cache_creation"] == 0
    assert entry["tokens"]["cache_read"] == 0


def test_execution_fields_populated():
    entry = _sample_entry()
    assert entry["execution"]["success"] is True
    assert entry["execution"]["error"] is None
    assert entry["execution"]["duration_seconds"] == 87.4


def test_error_entry_has_error_message():
    entry = build_entry(
        skill_name="spec-creator",
        invocation_id="test-uuid-9999",
        context={"chapter": "unknown", "name": "unknown", "phase": "unknown"},
        usage={"input": 0, "output": 0, "cache_creation": 0, "cache_read": 0, "model": "unknown"},
        files_touched=[],
        duration_seconds=3.2,
        success=False,
        error="Skill timed out",
    )
    assert entry["execution"]["success"] is False
    assert entry["execution"]["error"] == "Skill timed out"


def test_advisor_defaults_to_not_used():
    entry = _sample_entry()
    assert entry["advisor"]["used"] is False
    assert entry["advisor"]["savings_tokens"] == 0
    assert entry["advisor"]["cost_tokens"] == 0
