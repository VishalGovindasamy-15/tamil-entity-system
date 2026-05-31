"""
Core module — shared foundation for Tamil Entity Recognition.

All other modules import from this package.
"""
from core.database import Database, VectorStore
from core.base_agent import BaseAgent
from core.base_source import BaseSourcePlugin
from core.base_processor import BaseInputProcessor
from core.state import SystemState, create_initial_state
from core.contracts import SourceResult, SourceConfig, ProcessorResult, SourceType
from core.llm_client import LLMClient
from core.logger import get_logger, setup_logging

__all__ = [
    "Database",
    "VectorStore",
    "BaseAgent",
    "BaseSourcePlugin",
    "BaseInputProcessor",
    "SystemState",
    "create_initial_state",
    "SourceResult",
    "SourceConfig",
    "ProcessorResult",
    "SourceType",
    "LLMClient",
    "get_logger",
    "setup_logging",
]
