"""
Module-level integration test for the Core module.

Tests that all core components work together:
Settings → Database → VectorStore → SystemState → BaseAgent
"""
import os
import pytest

from core.database import Database, VectorStore
from core.state import create_initial_state
from core.models import TABLES
from core.base_agent import BaseAgent
from core.contracts import SourceConfig, SourceResult, ProcessorResult, SourceType
from core.logger import get_logger
from config.settings import Settings


@pytest.mark.asyncio
async def test_full_core_integration(tmp_path):
    """End-to-end: load config → init DB → create state → run agent helpers."""

    # 1. Load Settings from YAML
    config_path = os.path.join(os.path.dirname(__file__), "..", "..", "config", "default_config.yaml")
    settings = Settings(config_path=config_path)
    settings.load()
    assert settings.get("llm.primary") == "gemini"

    # 2. Initialise Database
    db_path = str(tmp_path / "integration.db")
    chroma_path = str(tmp_path / "chroma")
    db = Database(sqlite_path=db_path, chroma_path=chroma_path)
    await db.initialize()

    # 3. Verify all 10 tables exist
    tables = await db.fetchall(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )
    table_names = {r["name"] for r in tables}
    for t in TABLES.keys():
        assert t in table_names, f"Missing table: {t}"

    # 4. Verify seed data
    config_count = await db.fetchval("SELECT COUNT(*) FROM system_config")
    assert config_count > 0
    source_count = await db.fetchval("SELECT COUNT(*) FROM source_credibility")
    assert source_count > 0

    # 5. Create SystemState
    state = create_initial_state(
        request_id="integration-test-001",
        input_type="text",
        input_content="அப்துல் கலாம் ஒரு விஞ்ஞானி",
        input_metadata={"source": "test"},
        config=settings.to_dict(),
    )
    assert state["request_id"] == "integration-test-001"
    assert state["processing_status"] == "pending"

    # 6. Load DB overrides
    await settings.load_db_overrides(db)

    # 7. Use BaseAgent with DB + config
    agent = BaseAgent("integration_agent", "test", db=db, config=settings)
    agent.log_step(state, "Integration test started")
    agent.increment_api_calls(state, 2)
    agent.increment_cache_hits(state)

    assert len(state["processing_steps"]) == 1
    assert state["api_calls_made"] == 2
    assert state["cache_hits"] == 1

    # 8. Test get_config with DB override
    val = await agent.get_config("processing.max_concurrent_entities", 5)
    assert isinstance(val, int)

    # 9. Test contracts
    cfg = SourceConfig("wiki", SourceType.API, ["PERSON"], ["ta"], base_credibility=0.95)
    assert cfg.to_dict()["source_type"] == "api"

    result = SourceResult(success=True, source_name="wiki", confidence=0.9)
    assert result.to_dict()["confidence"] == 0.9

    proc = ProcessorResult(success=True, text="test", processor_name="ocr")
    assert proc.to_dict()["text"] == "test"

    # 10. Test logger
    log = get_logger("integration_test")
    log.info("Integration test passed")

    # 11. Test enabled processors from config
    procs = settings.get_enabled_processors("input.image")
    assert len(procs) >= 1
    assert all("name" in p for p in procs)

    # 12. Test enabled sources from config
    sources = settings.get_enabled_sources(tier=1)
    assert len(sources) >= 1

    # Cleanup
    await db.close()
