"""Tests for core.base_source — BaseSourcePlugin ABC."""
import pytest

from core.base_source import BaseSourcePlugin
from core.contracts import SourceConfig, SourceResult, SourceType


class DummySource(BaseSourcePlugin):
    """Concrete implementation for testing."""

    async def search(self, entity_name, entity_type, context=None):
        self._record_success()
        return SourceResult(success=True, entity_found=True, source_name=self.source_name)

    async def health_check(self):
        return True


class FailingSource(BaseSourcePlugin):
    async def search(self, entity_name, entity_type, context=None):
        self._record_failure()
        return SourceResult(success=False, error_message="fail")

    async def health_check(self):
        return False


@pytest.fixture
def config():
    return SourceConfig(
        source_name="test_source",
        source_type=SourceType.API,
        supported_entity_types=["PERSON"],
        supported_languages=["ta"],
    )


def test_cannot_instantiate_abstract():
    """BaseSourcePlugin itself should not be instantiatable."""
    with pytest.raises(TypeError):
        BaseSourcePlugin(SourceConfig("x", SourceType.API, [], []))


@pytest.mark.asyncio
async def test_search_returns_source_result(config):
    src = DummySource(config)
    result = await src.search("test", "PERSON")
    assert result.success is True
    assert result.source_name == "test_source"


@pytest.mark.asyncio
async def test_health_check(config):
    src = DummySource(config)
    assert await src.health_check() is True

    fail = FailingSource(config)
    assert await fail.health_check() is False


@pytest.mark.asyncio
async def test_stats_tracking(config):
    src = DummySource(config)
    assert src.get_stats()["total_queries"] == 0

    await src.search("e", "PERSON")
    stats = src.get_stats()
    assert stats["total_queries"] == 1
    assert stats["successful_queries"] == 1


@pytest.mark.asyncio
async def test_failure_stats(config):
    src = FailingSource(config)
    await src.search("e", "PERSON")
    stats = src.get_stats()
    assert stats["failed_queries"] == 1


@pytest.mark.asyncio
async def test_initialize_default(config):
    src = DummySource(config)
    assert await src.initialize() is True


@pytest.mark.asyncio
async def test_shutdown_default(config):
    src = DummySource(config)
    await src.shutdown()  # should not raise
