"""
Abstract base class for all input processors (OCR, ASR, PDF, …).
"""
from abc import ABC, abstractmethod
from typing import Any, Dict

from core.contracts import ProcessorResult
from core.logger import get_logger


class BaseInputProcessor(ABC):
    """Every input processor (EasyOCR, Whisper, etc.) extends this."""

    def __init__(self, processor_name: str, processor_type: str,
                 config: Dict[str, Any] = None):
        """
        Args:
            processor_name: Unique name (e.g. ``easyocr``).
            processor_type: Category (``image``, ``audio``, ``pdf``, …).
            config: Processor-specific config dict from YAML.
        """
        self.processor_name = processor_name
        self.processor_type = processor_type
        self.config = config or {}
        self.logger = get_logger(f"processor.{processor_name}")

    @abstractmethod
    async def process(self, content: Any, **kwargs) -> ProcessorResult:
        """Process input content and return extracted text."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if the processor is available."""
        ...

    def is_enabled(self) -> bool:
        """Check if this processor is enabled in its config."""
        return self.config.get("enabled", False)
