"""
Shared data contracts used across all modules.
Defines SourceType, SourceConfig, SourceResult, and ProcessorResult.
"""
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional, List
from enum import Enum


class SourceType(Enum):
    """Types of research sources."""
    API = "api"
    WEB_SCRAPER = "web_scraper"
    DATABASE = "database"
    FILE_SYSTEM = "file_system"
    CUSTOM = "custom"


@dataclass
class SourceConfig:
    """Configuration for a research source plugin."""
    source_name: str
    source_type: SourceType
    supported_entity_types: List[str]
    supported_languages: List[str]
    base_credibility: float = 0.70
    timeout_seconds: int = 10
    requires_auth: bool = False
    auth_type: Optional[str] = None
    is_free: bool = True
    cost_per_call: float = 0.0
    priority: int = 500
    enable_caching: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict with enum conversion."""
        d = asdict(self)
        d["source_type"] = self.source_type.value
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SourceConfig":
        """Deserialize from dict."""
        data = dict(data)
        if isinstance(data.get("source_type"), str):
            data["source_type"] = SourceType(data["source_type"])
        return cls(**data)


@dataclass
class SourceResult:
    """Result returned by a research source query."""
    success: bool
    entity_found: bool = False
    facts: Dict[str, Any] = field(default_factory=dict)
    source_name: str = ""
    source_url: Optional[str] = None
    source_credibility: float = 0.5
    confidence: float = 0.5
    raw_data: Optional[Any] = None
    response_time_ms: int = 0
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SourceResult":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ProcessorResult:
    """Result returned by an input processor."""
    success: bool
    text: str = ""
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    processor_name: str = ""
    processing_time_ms: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProcessorResult":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
