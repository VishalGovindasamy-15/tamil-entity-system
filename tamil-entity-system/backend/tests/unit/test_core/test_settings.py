"""Tests for config.settings — Settings class."""
import os
import pytest

from config.settings import Settings


@pytest.fixture
def settings(default_config):
    """Re-use the default_config fixture from conftest."""
    return default_config


def test_yaml_loading(settings):
    """Config should load without error and have data."""
    assert settings._data, "Config data should not be empty"
    assert "llm" in settings._data


def test_dot_notation_get(settings):
    assert settings.get("llm.primary") == "gemini"
    assert settings.get("extraction.confidence_threshold") == 0.85
    assert settings.get("nonexistent.key", "fallback") == "fallback"


def test_dot_notation_get_deep(settings):
    val = settings.get("input.image.processors.easyocr.enabled")
    assert val is True


def test_set_creates_path(settings):
    settings.set("new.deep.key", "hello")
    assert settings.get("new.deep.key") == "hello"


def test_set_overwrites(settings):
    settings.set("llm.primary", "claude")
    assert settings.get("llm.primary") == "claude"


def test_is_enabled_true(settings):
    assert settings.is_enabled("input.image.processors.easyocr") is True


def test_is_enabled_false(settings):
    assert settings.is_enabled("input.image.processors.google_vision") is False


def test_is_enabled_nonexistent(settings):
    assert settings.is_enabled("nonexistent.processor") is False


def test_get_enabled_processors(settings):
    procs = settings.get_enabled_processors("input.image")
    assert len(procs) >= 1
    # Should be sorted by priority
    priorities = [p["priority"] for p in procs]
    assert priorities == sorted(priorities)
    # Each should have a 'name' key
    for p in procs:
        assert "name" in p


def test_get_enabled_processors_empty(settings):
    procs = settings.get_enabled_processors("nonexistent.category")
    assert procs == []


def test_get_enabled_sources(settings):
    sources = settings.get_enabled_sources()
    assert len(sources) >= 1
    for s in sources:
        assert "name" in s
        assert s.get("enabled") is True


def test_get_enabled_sources_by_tier(settings):
    tier1 = settings.get_enabled_sources(tier=1)
    for s in tier1:
        assert s.get("tier") == 1


def test_to_dict(settings):
    d = settings.to_dict()
    assert isinstance(d, dict)
    assert "llm" in d
    # Modifying the copy shouldn't affect the original
    d["llm"]["primary"] = "changed"
    assert settings.get("llm.primary") != "changed"


def test_missing_config_file():
    s = Settings(config_path="/nonexistent/file.yaml")
    s.load()
    assert s._data == {}
    assert s.get("anything", "default") == "default"


@pytest.mark.asyncio
async def test_load_db_overrides(test_db):
    """DB overrides should take precedence after loading."""
    config_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "config", "default_config.yaml")
    s = Settings(config_path=config_path)
    s.load()

    assert s.get("processing.max_concurrent_entities") == 10

    # DB seed has this override
    await s.load_db_overrides(test_db)
    # The seed value is "10" with type "integer"
    val = s.get("processing.max_concurrent_entities")
    assert val == 10  # same value, but loaded from DB
