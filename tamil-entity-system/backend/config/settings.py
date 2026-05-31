"""
Configuration manager — loads YAML, supports dot-notation access,
and merges runtime DB overrides.
"""
import os
from typing import Any, Dict, List, Optional

import yaml

from core.logger import get_logger

logger = get_logger(__name__)


class Settings:
    """Hierarchical configuration with YAML → ENV → DB override support.

    Priority (highest wins):
        1. ``system_config`` DB table (runtime overrides)
        2. ``default_config.yaml`` (file-based defaults)
    """

    def __init__(self, config_path: str = "config/default_config.yaml"):
        self.config_path = config_path
        self._data: Dict[str, Any] = {}

    # ── Loading ─────────────────────────────────────────────────────

    def load(self) -> None:
        """Load the YAML config file into memory."""
        if not os.path.exists(self.config_path):
            logger.warning("Config file not found: %s — using empty config", self.config_path)
            self._data = {}
            return

        with open(self.config_path, "r", encoding="utf-8") as fh:
            self._data = yaml.safe_load(fh) or {}

        logger.info("Loaded config from %s (%d top-level keys)", self.config_path, len(self._data))

    # ── Dot-notation access ─────────────────────────────────────────

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a value using dot-notation (e.g. ``input.image.processors.easyocr.enabled``)."""
        parts = key.split(".")
        node: Any = self._data
        for part in parts:
            if isinstance(node, dict):
                node = node.get(part)
            else:
                return default
            if node is None:
                return default
        return node

    def set(self, key: str, value: Any) -> None:
        """Set a value at a dot-notation path (creates intermediate dicts)."""
        parts = key.split(".")
        node = self._data
        for part in parts[:-1]:
            if part not in node or not isinstance(node[part], dict):
                node[part] = {}
            node = node[part]
        node[parts[-1]] = value

    # ── Convenience helpers ─────────────────────────────────────────

    def is_enabled(self, key: str) -> bool:
        """Shorthand for ``get(key + '.enabled', False)``."""
        val = self.get(f"{key}.enabled", False)
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            return val.lower() in ("true", "1", "yes")
        return bool(val)

    def get_enabled_processors(self, category: str) -> List[Dict[str, Any]]:
        """Return enabled processors for a category, sorted by priority.

        Args:
            category: e.g. ``input.image``, ``input.audio``.

        Returns:
            List of processor config dicts, each extended with a ``name`` key.
        """
        processors_dict = self.get(f"{category}.processors", {})
        if not isinstance(processors_dict, dict):
            return []

        result = []
        for name, conf in processors_dict.items():
            if isinstance(conf, dict) and conf.get("enabled", False):
                entry = dict(conf)
                entry["name"] = name
                result.append(entry)

        result.sort(key=lambda p: p.get("priority", 999))
        return result

    def get_enabled_sources(self, tier: Optional[int] = None) -> List[Dict[str, Any]]:
        """Return enabled research sources, optionally filtered by tier.

        Returns:
            List of source config dicts, each extended with a ``name`` key.
        """
        sources_dict = self.get("research.sources", {})
        if not isinstance(sources_dict, dict):
            return []

        result = []
        for name, conf in sources_dict.items():
            if isinstance(conf, dict) and conf.get("enabled", False):
                if tier is not None and conf.get("tier") != tier:
                    continue
                entry = dict(conf)
                entry["name"] = name
                result.append(entry)

        result.sort(key=lambda s: s.get("tier", 999))
        return result

    def to_dict(self) -> Dict[str, Any]:
        """Return the full config as a plain dict (deep copy)."""
        import copy
        return copy.deepcopy(self._data)

    # ── DB overrides ────────────────────────────────────────────────

    async def load_db_overrides(self, db) -> None:
        """Merge runtime overrides from the ``system_config`` DB table.

        DB values take precedence over YAML values.
        """
        rows = await db.fetchall("SELECT config_key, config_value, value_type FROM system_config")
        count = 0
        for row in rows:
            key = row["config_key"]
            value = self._cast(row["config_value"], row["value_type"])
            self.set(key, value)
            count += 1

        if count:
            logger.info("Applied %d DB config overrides", count)

    @staticmethod
    def _cast(value: str, value_type: str) -> Any:
        if value_type == "integer":
            return int(value)
        elif value_type == "decimal":
            return float(value)
        elif value_type == "boolean":
            return value.lower() in ("true", "1", "yes")
        return value
