"""Tests for core.contracts."""
from core.contracts import (
    SourceType, SourceConfig, SourceResult, ProcessorResult,
)


# ── SourceType ──────────────────────────────────────────────────────

def test_source_type_values():
    assert SourceType.API.value == "api"
    assert SourceType.CUSTOM.value == "custom"


# ── SourceConfig ────────────────────────────────────────────────────

def test_source_config_defaults():
    cfg = SourceConfig(
        source_name="test",
        source_type=SourceType.API,
        supported_entity_types=["PERSON"],
        supported_languages=["ta"],
    )
    assert cfg.base_credibility == 0.70
    assert cfg.timeout_seconds == 10
    assert cfg.is_free is True
    assert cfg.enable_caching is True


def test_source_config_to_dict():
    cfg = SourceConfig("wiki", SourceType.API, ["PERSON"], ["ta"])
    d = cfg.to_dict()
    assert d["source_type"] == "api"
    assert d["source_name"] == "wiki"


def test_source_config_from_dict():
    d = {
        "source_name": "wiki",
        "source_type": "api",
        "supported_entity_types": ["PERSON"],
        "supported_languages": ["ta"],
        "base_credibility": 0.95,
    }
    cfg = SourceConfig.from_dict(d)
    assert cfg.source_type == SourceType.API
    assert cfg.base_credibility == 0.95


# ── SourceResult ────────────────────────────────────────────────────

def test_source_result_defaults():
    r = SourceResult(success=True)
    assert r.entity_found is False
    assert r.facts == {}
    assert r.source_name == ""
    assert r.error_message is None


def test_source_result_to_dict():
    r = SourceResult(success=True, source_name="wiki", confidence=0.9)
    d = r.to_dict()
    assert d["source_name"] == "wiki"
    assert d["confidence"] == 0.9


def test_source_result_from_dict():
    d = {"success": True, "source_name": "wiki", "confidence": 0.9}
    r = SourceResult.from_dict(d)
    assert r.source_name == "wiki"


# ── ProcessorResult ─────────────────────────────────────────────────

def test_processor_result_defaults():
    r = ProcessorResult(success=True)
    assert r.text == ""
    assert r.confidence == 0.0
    assert r.metadata == {}


def test_processor_result_roundtrip():
    r = ProcessorResult(success=True, text="hello", processor_name="ocr")
    d = r.to_dict()
    r2 = ProcessorResult.from_dict(d)
    assert r2.text == "hello"
    assert r2.processor_name == "ocr"
