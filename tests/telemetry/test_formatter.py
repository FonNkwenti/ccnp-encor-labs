import json
import pytest
from scripts.lib.telemetry.formatter import build_entry, _compute_cost


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


def test_effort_level_captured_from_usage():
    entry = build_entry(
        skill_name="spec-creator",
        invocation_id="test-uuid-1234",
        context={"chapter": "ospf", "name": "lab-00", "phase": "Phase 2 - Spec"},
        usage={"input": 100, "output": 50, "cache_creation": 0, "cache_read": 0,
               "model": "claude-haiku-4-5-20251001", "speed": "fast"},
        files_touched=[],
        duration_seconds=10.0,
        success=True,
        error=None,
    )
    assert entry["effort_level"] == "fast"


def test_effort_level_defaults_to_unknown():
    entry = _sample_entry()
    assert entry["effort_level"] == "unknown"


def test_advisor_defaults_to_not_used():
    entry = _sample_entry()
    assert entry["advisor"]["used"] is False
    assert entry["advisor"]["savings_tokens"] == 0
    assert entry["advisor"]["cost_tokens"] == 0


def test_cost_usd_present_in_entry():
    entry = _sample_entry()
    assert "cost_usd" in entry
    assert "total" in entry["cost_usd"]


def test_cost_computed_for_haiku():
    # input: 4250 * $0.80/MTok, output: 1820 * $4.00/MTok
    tokens = {"input": 4250, "output": 1820, "cache_creation": 0, "cache_read": 0}
    cost = _compute_cost(tokens, "claude-haiku-4-5-20251001")
    assert cost["input"] == pytest.approx(0.0034, rel=1e-4)
    assert cost["output"] == pytest.approx(0.00728, rel=1e-4)
    assert cost["total"] == pytest.approx(0.01068, rel=1e-4)


def test_cost_computed_for_sonnet_with_cache():
    # cache_creation: 106416 * $3.75/MTok dominates
    tokens = {"input": 10, "output": 585, "cache_creation": 106416, "cache_read": 0}
    cost = _compute_cost(tokens, "claude-sonnet-4-6")
    assert cost["cache_creation"] == pytest.approx(0.39906, rel=1e-4)
    assert cost["total"] == pytest.approx(0.407865, rel=1e-4)


def test_cost_zero_for_unknown_model():
    tokens = {"input": 1000, "output": 500, "cache_creation": 0, "cache_read": 0}
    cost = _compute_cost(tokens, "unknown")
    assert cost["total"] == 0.0


def test_cost_usd_in_entry_matches_compute_cost():
    entry = build_entry(
        skill_name="lab-assembler",
        invocation_id="uuid-cost-test",
        context={"chapter": "ospf", "name": "lab-00", "phase": "Phase 3 - Build"},
        usage={"input": 4250, "output": 1820, "cache_creation": 0, "cache_read": 0,
               "model": "claude-haiku-4-5-20251001"},
        files_touched=[],
        duration_seconds=10.0,
        success=True,
        error=None,
    )
    assert entry["cost_usd"]["total"] == pytest.approx(0.01068, rel=1e-4)
