"""
Database managers for SQLite (relational) and ChromaDB (vector).
"""
import json
from typing import Any, Dict, List, Optional

import aiosqlite

from core.logger import get_logger
from core.models import TABLES, SEED_CONFIG, SEED_SOURCES

logger = get_logger(__name__)


class Database:
    """Async SQLite database with auto-table creation and seed data."""

    def __init__(self, sqlite_path: str = "data/tamil_entity.db",
                 chroma_path: str = "data/chroma_data"):
        self.sqlite_path = sqlite_path
        self.chroma_path = chroma_path
        self._conn: Optional[aiosqlite.Connection] = None

    async def initialize(self) -> None:
        """Open the connection, create all tables, and insert seed data."""
        self._conn = await aiosqlite.connect(self.sqlite_path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA journal_mode=WAL")
        await self._conn.execute("PRAGMA foreign_keys=ON")

        for table_name, ddl in TABLES.items():
            await self._conn.execute(ddl)
        await self._conn.commit()

        await self._seed_data()
        logger.info("Database initialized at %s (%d tables)", self.sqlite_path, len(TABLES))

    async def _seed_data(self) -> None:
        """Insert default config and source data (skip if already present)."""
        # Seed system_config
        for key, category, value, vtype in SEED_CONFIG:
            await self._conn.execute(
                "INSERT OR IGNORE INTO system_config (config_key, category, config_value, value_type) "
                "VALUES (?, ?, ?, ?)",
                (key, category, value, vtype),
            )
        # Seed source_credibility
        for name, stype, credibility, active in SEED_SOURCES:
            await self._conn.execute(
                "INSERT OR IGNORE INTO source_credibility "
                "(source_name, source_type, base_credibility, current_credibility, is_active) "
                "VALUES (?, ?, ?, ?, ?)",
                (name, stype, credibility, credibility, int(active)),
            )
        await self._conn.commit()

    # ── CRUD helpers ────────────────────────────────────────────────

    async def execute(self, sql: str, *params) -> None:
        """Execute a write query."""
        await self._conn.execute(sql, params)
        await self._conn.commit()

    async def fetchone(self, sql: str, *params) -> Optional[Dict[str, Any]]:
        """Fetch a single row as a dict."""
        cursor = await self._conn.execute(sql, params)
        row = await cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    async def fetchall(self, sql: str, *params) -> List[Dict[str, Any]]:
        """Fetch all rows as a list of dicts."""
        cursor = await self._conn.execute(sql, params)
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def fetchval(self, sql: str, *params) -> Any:
        """Fetch a single scalar value."""
        cursor = await self._conn.execute(sql, params)
        row = await cursor.fetchone()
        if row is None:
            return None
        return row[0]

    async def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            await self._conn.close()
            self._conn = None
            logger.info("Database connection closed")


class VectorStore:
    """ChromaDB wrapper for embedding-based similarity search."""

    def __init__(self, chroma_path: str = "data/chroma_data"):
        import chromadb
        from chromadb.config import Settings as ChromaSettings

        self._client = chromadb.Client(ChromaSettings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=chroma_path,
            anonymized_telemetry=False,
        ))
        self.chroma_path = chroma_path
        self._collections: Dict[str, Any] = {}
        logger.info("VectorStore initialized at %s", chroma_path)

    def get_or_create_collection(self, name: str):
        """Get or create a named collection."""
        if name not in self._collections:
            self._collections[name] = self._client.get_or_create_collection(name=name)
        return self._collections[name]

    async def search(self, collection: str, query_text: str,
                     limit: int = 5, score_threshold: float = 0.7) -> List[Dict]:
        """Search for similar texts in a collection.

        Returns list of dicts with 'id', 'text', 'metadata', 'distance'.
        """
        coll = self.get_or_create_collection(collection)
        try:
            results = coll.query(query_texts=[query_text], n_results=limit)
        except Exception:
            return []

        matches = []
        if results and results.get("ids") and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                distance = results["distances"][0][i] if results.get("distances") else 1.0
                # ChromaDB returns L2 distance; lower = more similar
                similarity = max(0.0, 1.0 - distance)
                if similarity >= score_threshold:
                    matches.append({
                        "id": doc_id,
                        "text": results["documents"][0][i] if results.get("documents") else "",
                        "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                        "distance": distance,
                        "similarity": similarity,
                    })
        return matches

    async def insert(self, collection: str, id: str, text: str,
                     metadata: Dict = None) -> None:
        """Insert a document into a collection."""
        coll = self.get_or_create_collection(collection)
        coll.upsert(ids=[id], documents=[text], metadatas=[metadata or {}])
