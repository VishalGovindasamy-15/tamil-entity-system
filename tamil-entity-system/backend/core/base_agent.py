"""
Base agent class that all processing agents extend.
Provides shared logging, metrics, and config helpers.
"""
from typing import Any
from datetime import datetime, timezone

from core.logger import get_logger

logger = get_logger(__name__)


class BaseAgent:
    """Abstract base for every pipeline agent.

    Sub-classes must override :meth:`execute`.
    """

    def __init__(self, agent_name: str, agent_type: str, db=None, config=None):
        """
        Args:
            agent_name: Human-readable agent name.
            agent_type: Category (input, transliteration, extraction, …).
            db: :class:`Database` instance (optional for unit tests).
            config: :class:`Settings` instance (optional for unit tests).
        """
        self.agent_name = agent_name
        self.agent_type = agent_type
        self.db = db
        self.config = config
        self.logger = get_logger(f"agent.{agent_name}")

    async def execute(self, state: dict) -> dict:
        """Process the state dict and return the (mutated) state.

        Sub-classes **must** override this method.
        """
        raise NotImplementedError(f"{self.agent_name} has not implemented execute()")

    # ── Logging helpers ─────────────────────────────────────────────

    def log_step(self, state: dict, message: str) -> None:
        """Append a timestamped processing step."""
        ts = datetime.now(timezone.utc).isoformat()
        entry = f"[{ts}] [{self.agent_name}] {message}"
        state.setdefault("processing_steps", []).append(entry)
        self.logger.info(message)

    def log_error(self, state: dict, error: str, details: Any = None) -> None:
        """Append a structured error entry."""
        ts = datetime.now(timezone.utc).isoformat()
        err = {
            "timestamp": ts,
            "agent": self.agent_name,
            "error": error,
            "details": str(details) if details else None,
        }
        state.setdefault("errors", []).append(err)
        self.logger.error("%s — %s", error, details)

    def log_warning(self, state: dict, message: str) -> None:
        """Append a warning string."""
        state.setdefault("warnings", []).append(f"[{self.agent_name}] {message}")
        self.logger.warning(message)

    # ── Metrics ─────────────────────────────────────────────────────

    def increment_api_calls(self, state: dict, count: int = 1) -> None:
        state["api_calls_made"] = state.get("api_calls_made", 0) + count

    def increment_cache_hits(self, state: dict, count: int = 1) -> None:
        state["cache_hits"] = state.get("cache_hits", 0) + count

    def increment_sources_accessed(self, state: dict, count: int = 1) -> None:
        state["sources_accessed"] = state.get("sources_accessed", 0) + count

    # ── Config helpers ──────────────────────────────────────────────

    async def get_config(self, key: str, default: Any = None) -> Any:
        """Get a config value with DB-override → YAML fallback."""
        # Try runtime DB override first
        if self.db:
            row = await self.db.fetchone(
                "SELECT config_value, value_type FROM system_config WHERE config_key = ?", key
            )
            if row:
                return self._cast_config_value(row["config_value"], row["value_type"])

        # Fall back to YAML config
        if self.config:
            return self.config.get(key, default)
        return default

    @staticmethod
    def _cast_config_value(value: str, value_type: str) -> Any:
        """Cast a string config value to the correct Python type."""
        if value_type == "integer":
            return int(value)
        elif value_type == "decimal":
            return float(value)
        elif value_type == "boolean":
            return value.lower() in ("true", "1", "yes")
        return value
