"""Tests for core.state."""
from core.state import SystemState, create_initial_state


def test_create_initial_state_returns_all_keys():
    state = create_initial_state(
        request_id="r1",
        input_type="text",
        input_content="hello",
    )
    # Every SystemState key must be present
    expected_keys = [
        "request_id", "session_id", "started_at", "started_at_epoch",
        "input_type", "input_content", "input_metadata",
        "current_stage", "processing_status",
        "raw_text", "normalized_text", "detected_language", "detected_scripts",
        "transliteration_map", "transliteration_confidence",
        "candidate_entities",
        "entities", "entity_knowledge", "explanations",
        "processing_steps", "api_calls_made", "cache_hits", "sources_accessed",
        "errors", "warnings", "stage_timings",
        "overall_confidence", "quality_score", "config", "final_response",
    ]
    for key in expected_keys:
        assert key in state, f"Missing key: {key}"


def test_create_initial_state_defaults():
    state = create_initial_state("r2", "image", b"bytes")
    assert state["request_id"] == "r2"
    assert state["input_type"] == "image"
    assert state["processing_status"] == "pending"
    assert state["current_stage"] == "initialized"
    assert state["raw_text"] == ""
    assert state["entities"] == []
    assert state["api_calls_made"] == 0
    assert state["cache_hits"] == 0
    assert state["overall_confidence"] == 0.0


def test_create_initial_state_with_metadata():
    state = create_initial_state("r3", "text", "data", input_metadata={"foo": "bar"})
    assert state["input_metadata"] == {"foo": "bar"}


def test_state_is_mutable():
    state = create_initial_state("r4", "text", "data")
    state["raw_text"] = "updated"
    state["entities"].append({"text": "entity"})
    assert state["raw_text"] == "updated"
    assert len(state["entities"]) == 1


def test_create_initial_state_with_config():
    state = create_initial_state("r5", "text", "data", config={"key": "val"})
    assert state["config"] == {"key": "val"}


def test_create_initial_state_has_valid_timestamps():
    state = create_initial_state("r6", "text", "data")
    assert state["started_at"]  # ISO string
    assert state["started_at_epoch"] > 0
    assert state["session_id"]  # UUID string
