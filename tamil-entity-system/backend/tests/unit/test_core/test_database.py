"""Tests for core.database — Database and VectorStore."""
import pytest
import pytest_asyncio

from core.database import Database
from core.models import TABLES


@pytest.mark.asyncio
async def test_initialize_creates_all_tables(test_db):
    """All 10 tables must exist after initialize()."""
    tables = await test_db.fetchall(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )
    table_names = {r["name"] for r in tables}
    for expected in TABLES.keys():
        assert expected in table_names, f"Table '{expected}' not created"


@pytest.mark.asyncio
async def test_seed_config_inserted(test_db):
    """system_config table should contain seed data."""
    count = await test_db.fetchval("SELECT COUNT(*) FROM system_config")
    assert count > 0


@pytest.mark.asyncio
async def test_seed_sources_inserted(test_db):
    """source_credibility table should contain seed data."""
    count = await test_db.fetchval("SELECT COUNT(*) FROM source_credibility")
    assert count > 0


@pytest.mark.asyncio
async def test_execute_and_fetchone(test_db):
    """Basic insert and single-row fetch."""
    await test_db.execute(
        "INSERT INTO user_feedback (request_id, entity_name, feedback_type, rating) "
        "VALUES (?, ?, ?, ?)",
        "req-1", "entity-1", "correct", 5,
    )
    row = await test_db.fetchone(
        "SELECT * FROM user_feedback WHERE request_id = ?", "req-1"
    )
    assert row is not None
    assert row["rating"] == 5


@pytest.mark.asyncio
async def test_fetchall(test_db):
    """Insert multiple and fetch all."""
    for i in range(3):
        await test_db.execute(
            "INSERT INTO user_feedback (request_id, feedback_type) VALUES (?, ?)",
            f"req-{i}", "correct",
        )
    rows = await test_db.fetchall("SELECT * FROM user_feedback")
    assert len(rows) >= 3


@pytest.mark.asyncio
async def test_fetchval_returns_scalar(test_db):
    count = await test_db.fetchval("SELECT COUNT(*) FROM system_config")
    assert isinstance(count, int)


@pytest.mark.asyncio
async def test_fetchone_returns_none_for_missing(test_db):
    row = await test_db.fetchone(
        "SELECT * FROM user_feedback WHERE request_id = ?", "nonexistent"
    )
    assert row is None


@pytest.mark.asyncio
async def test_close_and_reopen(tmp_path):
    """Database can be closed and re-opened."""
    db_path = str(tmp_path / "reopen.db")
    db = Database(sqlite_path=db_path, chroma_path=str(tmp_path / "chroma"))
    await db.initialize()
    await db.execute(
        "INSERT INTO user_feedback (request_id, feedback_type) VALUES (?, ?)",
        "r1", "test",
    )
    await db.close()

    db2 = Database(sqlite_path=db_path, chroma_path=str(tmp_path / "chroma"))
    await db2.initialize()
    row = await db2.fetchone("SELECT * FROM user_feedback WHERE request_id = ?", "r1")
    assert row is not None
    await db2.close()
