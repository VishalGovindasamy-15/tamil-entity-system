"""Tests for core.base_processor — BaseInputProcessor ABC."""
import pytest

from core.base_processor import BaseInputProcessor
from core.contracts import ProcessorResult


class DummyProcessor(BaseInputProcessor):
    """Concrete implementation for testing."""

    async def process(self, content, **kwargs):
        return ProcessorResult(success=True, text=str(content), processor_name=self.processor_name)

    async def health_check(self):
        return True


def test_cannot_instantiate_abstract():
    with pytest.raises(TypeError):
        BaseInputProcessor("x", "text")


def test_is_enabled_reads_config():
    proc = DummyProcessor("ocr", "image", config={"enabled": True, "priority": 1})
    assert proc.is_enabled() is True

    proc2 = DummyProcessor("ocr2", "image", config={"enabled": False})
    assert proc2.is_enabled() is False

    proc3 = DummyProcessor("ocr3", "image", config={})
    assert proc3.is_enabled() is False


@pytest.mark.asyncio
async def test_process_returns_processor_result():
    proc = DummyProcessor("test_proc", "text", config={"enabled": True})
    result = await proc.process("hello world")
    assert result.success is True
    assert result.text == "hello world"
    assert result.processor_name == "test_proc"


@pytest.mark.asyncio
async def test_health_check():
    proc = DummyProcessor("test_proc", "text")
    assert await proc.health_check() is True


def test_processor_attributes():
    proc = DummyProcessor("easyocr", "image", config={"enabled": True, "priority": 1})
    assert proc.processor_name == "easyocr"
    assert proc.processor_type == "image"
