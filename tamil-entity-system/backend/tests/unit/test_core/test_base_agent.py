"""Tests for core.base_agent."""
import pytest

from core.base_agent import BaseAgent
from core.state import create_initial_state


@pytest.fixture
def agent():
    return BaseAgent(agent_name="test_agent", agent_type="test")


@pytest.fixture
def state():
    return create_initial_state("req-1", "text", "hello")


def test_log_step_appends(agent, state):
    agent.log_step(state, "step one")
    assert len(state["processing_steps"]) == 1
    assert "step one" in state["processing_steps"][0]
    assert "test_agent" in state["processing_steps"][0]


def test_log_step_multiple(agent, state):
    agent.log_step(state, "step 1")
    agent.log_step(state, "step 2")
    assert len(state["processing_steps"]) == 2


def test_log_error_appends(agent, state):
    agent.log_error(state, "something broke", details={"code": 500})
    assert len(state["errors"]) == 1
    err = state["errors"][0]
    assert err["agent"] == "test_agent"
    assert err["error"] == "something broke"
    assert "500" in err["details"]


def test_log_warning_appends(agent, state):
    agent.log_warning(state, "watch out")
    assert len(state["warnings"]) == 1
    assert "watch out" in state["warnings"][0]


def test_increment_api_calls(agent, state):
    assert state["api_calls_made"] == 0
    agent.increment_api_calls(state)
    assert state["api_calls_made"] == 1
    agent.increment_api_calls(state, 3)
    assert state["api_calls_made"] == 4


def test_increment_cache_hits(agent, state):
    assert state["cache_hits"] == 0
    agent.increment_cache_hits(state, 2)
    assert state["cache_hits"] == 2


def test_increment_sources_accessed(agent, state):
    assert state["sources_accessed"] == 0
    agent.increment_sources_accessed(state)
    assert state["sources_accessed"] == 1


@pytest.mark.asyncio
async def test_execute_not_implemented(agent, state):
    with pytest.raises(NotImplementedError):
        await agent.execute(state)


@pytest.mark.asyncio
async def test_get_config_yaml_fallback(state):
    """When no DB is set, config falls back to Settings."""
    from config.settings import Settings
    import os

    config_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "config", "default_config.yaml")
    settings = Settings(config_path=config_path)
    settings.load()

    agent = BaseAgent("cfg_test", "test", db=None, config=settings)
    val = await agent.get_config("llm.primary", "none")
    assert val == "gemini"


@pytest.mark.asyncio
async def test_get_config_with_db_override(test_db):
    """DB override should take precedence over YAML."""
    from config.settings import Settings
    import os

    config_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "config", "default_config.yaml")
    settings = Settings(config_path=config_path)
    settings.load()

    # Insert a DB override
    await test_db.execute(
        "INSERT OR REPLACE INTO system_config (config_key, category, config_value, value_type) "
        "VALUES (?, ?, ?, ?)",
        "llm.primary", "llm", "openai", "string",
    )

    agent = BaseAgent("cfg_test2", "test", db=test_db, config=settings)
    val = await agent.get_config("llm.primary", "none")
    assert val == "openai"  # DB override wins


def test_cast_config_value():
    assert BaseAgent._cast_config_value("42", "integer") == 42
    assert BaseAgent._cast_config_value("0.85", "decimal") == 0.85
    assert BaseAgent._cast_config_value("true", "boolean") is True
    assert BaseAgent._cast_config_value("false", "boolean") is False
    assert BaseAgent._cast_config_value("hello", "string") == "hello"
