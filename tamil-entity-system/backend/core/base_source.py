"""
Abstract base class for all research source plugins.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from core.contracts import SourceConfig, SourceResult
from core.logger import get_logger


class BaseSourcePlugin(ABC):
    """Every research source (Wikipedia, Wikidata, custom, …) extends this."""

    def __init__(self, config: SourceConfig):
        self.config = config
        self.source_name = config.source_name
        self.logger = get_logger(f"source.{self.source_name}")

        # Stats
        self._total_queries = 0
        self._successful_queries = 0
        self._failed_queries = 0

    @abstractmethod
    async def search(self, entity_name: str, entity_type: str,
                     context: Optional[str] = None) -> SourceResult:
        """Query this source for information about an entity."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if the source is reachable and operational."""
        ...

    async def initialize(self) -> bool:
        """Optional one-time initialization (API key validation, etc.)."""
        return True

    async def shutdown(self) -> None:
        """Optional cleanup on shutdown."""
        pass

    def get_stats(self) -> Dict[str, Any]:
        """Return source performance stats."""
        success_rate = (
            self._successful_queries / self._total_queries
            if self._total_queries > 0 else 0.0
        )
        return {
            "source_name": self.source_name,
            "total_queries": self._total_queries,
            "successful_queries": self._successful_queries,
            "failed_queries": self._failed_queries,
            "success_rate": round(success_rate, 4),
        }

    def _record_success(self) -> None:
        self._total_queries += 1
        self._successful_queries += 1

    def _record_failure(self) -> None:
        self._total_queries += 1
        self._failed_queries += 1
