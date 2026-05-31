"""
Shared pytest fixtures for Tamil Entity Recognition tests.
"""
import os
import tempfile

import pytest
import pytest_asyncio

import sys
# Ensure the backend directory is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.database import Database, VectorStore
from core.state import create_initial_state
from config.settings import Settings


@pytest_asyncio.fixture
async def test_db(tmp_path):
    """Temporary SQLite database for testing."""
    db_path = str(tmp_path / "test.db")
    chroma_path = str(tmp_path / "chroma")
    db = Database(sqlite_path=db_path, chroma_path=chroma_path)
    await db.initialize()
    yield db
    await db.close()


@pytest.fixture
def test_config():
    """Load test_config.yaml (free APIs only)."""
    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "test_config.yaml")
    settings = Settings(config_path=config_path)
    settings.load()
    return settings


@pytest.fixture
def default_config():
    """Load default_config.yaml."""
    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "default_config.yaml")
    settings = Settings(config_path=config_path)
    settings.load()
    return settings


@pytest.fixture
def sample_state():
    """A pre-populated initial state for testing."""
    return create_initial_state(
        request_id="test-req-001",
        input_type="text",
        input_content="அப்துல் கலாம் ஒரு விஞ்ஞானி",
        input_metadata={"source": "test"},
    )
