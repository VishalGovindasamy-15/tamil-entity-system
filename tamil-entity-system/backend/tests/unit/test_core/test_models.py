"""Tests for core.models — schema definitions and seed data."""
import sqlite3

from core.models import TABLES, SEED_CONFIG, SEED_SOURCES


def test_all_ten_tables_defined():
    assert len(TABLES) == 10


def test_table_names():
    expected = {
        "learned_transliterations", "entity_knowledge", "source_credibility",
        "api_performance", "user_feedback", "processing_requests",
        "agent_learning_log", "system_config", "custom_sources",
        "custom_input_processors",
    }
    assert set(TABLES.keys()) == expected


def test_sql_statements_are_valid():
    """All CREATE TABLE statements must parse without error."""
    conn = sqlite3.connect(":memory:")
    for name, ddl in TABLES.items():
        try:
            conn.execute(ddl)
        except sqlite3.OperationalError as e:
            raise AssertionError(f"Invalid SQL for table '{name}': {e}") from e
    conn.close()


def test_seed_config_not_empty():
    assert len(SEED_CONFIG) > 0
    for entry in SEED_CONFIG:
        assert len(entry) == 4, f"Seed config entry should have 4 fields: {entry}"


def test_seed_sources_not_empty():
    assert len(SEED_SOURCES) > 0
    for entry in SEED_SOURCES:
        assert len(entry) == 4, f"Seed source entry should have 4 fields: {entry}"


def test_seed_sources_names_unique():
    names = [s[0] for s in SEED_SOURCES]
    assert len(names) == len(set(names)), "Duplicate source names in SEED_SOURCES"
