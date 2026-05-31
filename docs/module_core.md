# Module 1: Core — Shared Foundation

## Purpose
Provides the shared infrastructure that **all other modules** depend on: database connections, configuration loading, base classes, shared types, and logging.

> [!IMPORTANT]
> This module must be built **first**. All other modules import from `core/`.

---

## Files

### `core/__init__.py`
Exports all public symbols: `Database`, `VectorStore`, `BaseAgent`, `BaseSourcePlugin`, `BaseInputProcessor`, `SystemState`, `SourceResult`, `SourceConfig`, `ProcessorResult`, `LLMClient`, `get_logger`.

Note: `Settings` lives in `config/settings.py`, not in `core/`.

---

### `core/database.py` — SQLite + ChromaDB Manager

**Responsibilities:**
- Initialize SQLite database with all tables (from the schema)
- Initialize ChromaDB for vector storage
- Provide async CRUD helpers
- Auto-create tables on first run

**Key Functions:**
```python
class Database:
    def __init__(self, sqlite_path: str, chroma_path: str)
    async def initialize(self) -> None          # Create tables if not exist
    async def execute(self, sql, *params)        # Run SQL
    async def fetchone(self, sql, *params)       # Fetch single row
    async def fetchall(self, sql, *params)       # Fetch multiple rows
    async def fetchval(self, sql, *params)       # Fetch single value
    async def close(self)

class VectorStore:
    def __init__(self, chroma_path: str)
    def get_or_create_collection(self, name: str) -> Collection
    async def search(self, collection: str, query_text: str, limit: int, score_threshold: float) -> List[Dict]
    async def insert(self, collection: str, id: str, text: str, metadata: Dict)
```

**SQLite Tables Created:**
1. `learned_transliterations` — Roman→Tamil mappings with confidence
2. `entity_knowledge` — Cached entity research results
3. `source_credibility` — Source performance tracking
4. `api_performance` — API call metrics
5. `user_feedback` — User corrections and ratings
6. `processing_requests` — Request audit trail
7. `agent_learning_log` — Agent learning events
8. `system_config` — Runtime config overrides
9. `custom_sources` — Custom source plugin configs
10. `custom_input_processors` — Custom processor configs

> [!NOTE]
> SQLite doesn't support PostgreSQL-specific features (triggers with plpgsql, vector columns, hypertables). We adapt:
> - Triggers → application-level updates in the `Database` class
> - Vector columns → ChromaDB collections
> - JSONB → TEXT with JSON serialization
> - TimescaleDB → regular table with manual aggregation

**Tests (`tests/unit/test_core/test_database.py`):**
- Test table creation
- Test CRUD operations
- Test concurrent access (aiosqlite handles this)
- Test ChromaDB insert/search
- Test DB cleanup/close

---

### `core/models.py` — Schema Definitions

**Responsibilities:**
- Define all `CREATE TABLE` SQL statements as constants
- Seed data (default config values, default source credibility scores)

```python
TABLES = {
    "learned_transliterations": """CREATE TABLE IF NOT EXISTS ...""",
    "entity_knowledge": """CREATE TABLE IF NOT EXISTS ...""",
    # ... all 10 tables
}

SEED_CONFIG = [
    ("processing.max_concurrent_entities", "processing", "10", "integer"),
    ("transliteration.confidence_threshold", "transliteration", "0.85", "decimal"),
    # ... all defaults from idea.txt
]

SEED_SOURCES = [
    ("wikipedia", "reference", 0.95, True),
    ("wikidata", "reference", 0.98, True),
    # ... all built-in sources
]
```

**Tests:**
- Test that all SQL statements are valid (parse without error)
- Test seed data is complete

---

### `core/state.py` — SystemState Definition

**The shared pipeline state.** Every module reads from and writes to this dict.

```python
from typing import TypedDict, List, Dict, Any, Optional

class SystemState(TypedDict):
    request_id: str
    session_id: str
    started_at: str
    input_type: str
    input_content: Any
    input_metadata: Dict[str, Any]
    current_stage: str
    processing_status: str
    raw_text: str
    normalized_text: str
    detected_language: str
    detected_scripts: List[str]
    transliteration_map: Dict[str, str]
    transliteration_confidence: Dict[str, float]
    entities: List[Dict[str, Any]]
    entity_knowledge: Dict[str, Dict[str, Any]]
    explanations: Dict[str, Dict[str, Any]]
    processing_steps: List[str]
    api_calls_made: int
    cache_hits: int
    sources_accessed: int
    errors: List[Dict[str, Any]]
    warnings: List[str]
    stage_timings: Dict[str, float]
    overall_confidence: float
    quality_score: float
    config: Dict[str, Any]

def create_initial_state(
    request_id: str,
    input_type: str,
    input_content: Any,
    input_metadata: Dict[str, Any] = None,
    config: Dict[str, Any] = None
) -> SystemState:
    """Factory function to create a properly initialized state"""
    ...
```

**Tests:**
- Test `create_initial_state()` returns valid state with all keys
- Test state is mutable (can update fields)

---

### `core/contracts.py` — Shared Data Contracts

```python
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from enum import Enum

class SourceType(Enum):
    API = "api"
    WEB_SCRAPER = "web_scraper"
    DATABASE = "database"
    FILE_SYSTEM = "file_system"
    CUSTOM = "custom"

@dataclass
class SourceConfig:
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

@dataclass
class SourceResult:
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

@dataclass
class ProcessorResult:
    success: bool
    text: str = ""
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    processor_name: str = ""
    processing_time_ms: int = 0
```

**Tests:**
- Test dataclass creation with defaults
- Test serialization to/from dict

---

### `core/base_agent.py` — Base Agent Class

```python
class BaseAgent:
    def __init__(self, agent_name: str, agent_type: str, db: Database, config: Settings)
    
    async def execute(self, state: SystemState) -> SystemState
        # Override in subclasses
    
    def log_step(self, state: SystemState, message: str) -> None
    def log_error(self, state: SystemState, error: str, details: Any = None) -> None
    def increment_api_calls(self, state: SystemState, count: int = 1) -> None
    def increment_cache_hits(self, state: SystemState, count: int = 1) -> None
    
    async def get_config(self, key: str, default: Any = None) -> Any
        # Check runtime DB config, fallback to YAML config
```

**Tests:**
- Test `log_step` appends to `state['processing_steps']`
- Test `log_error` appends to `state['errors']`
- Test `get_config` with DB override and YAML fallback

---

### `core/base_source.py` — Base Source Plugin

Abstract base class for all research sources (built-in + custom).

```python
class BaseSourcePlugin(ABC):
    def __init__(self, config: SourceConfig)
    
    @abstractmethod
    async def search(self, entity_name: str, entity_type: str, context: Optional[str] = None) -> SourceResult
    
    @abstractmethod
    async def health_check(self) -> bool
    
    async def initialize(self) -> bool
    async def shutdown(self) -> None
    def get_stats(self) -> Dict[str, Any]
```

**Tests:**
- Test that concrete implementations must implement `search()` and `health_check()`
- Test stats tracking

---

### `core/base_processor.py` — Base Input Processor

Abstract base class for all input processors (OCR, ASR, PDF, etc.).

```python
class BaseInputProcessor(ABC):
    def __init__(self, processor_name: str, processor_type: str, config: Dict[str, Any])
    
    @abstractmethod
    async def process(self, content: Any, **kwargs) -> ProcessorResult
    
    @abstractmethod
    async def health_check(self) -> bool
    
    def is_enabled(self) -> bool  # Check config
```

**Tests:**
- Test interface enforcement
- Test `is_enabled()` reads from config

---

### `core/llm_client.py` — LLM Provider Wrapper

Shared LLM client used by **Extraction** (LLM fallback), **Research** (LLM source), and **Explanation** (generation). Routes to the configured provider.

```python
class LLMClient:
    def __init__(self, config: Dict):
        self.primary = config.get('llm.primary', 'gemini')
        self.fallback = config.get('llm.fallback', 'ollama')
        self.providers = self._init_providers(config)
    
    def _init_providers(self, config) -> Dict:
        """Initialize only enabled LLM providers"""
        providers = {}
        for name in ['gemini', 'openai', 'claude', 'ollama']:
            if config.get(f'llm.providers.{name}.enabled', False):
                providers[name] = self._create_provider(name, config)
        return providers
    
    def _create_provider(self, name, config):
        """Factory for provider-specific clients"""
        if name == 'gemini':
            import google.generativeai as genai
            genai.configure(api_key=os.getenv(config.get('llm.providers.gemini.api_key_env')))
            return genai.GenerativeModel(config.get('llm.providers.gemini.model'))
        elif name == 'openai':
            from openai import AsyncOpenAI
            return AsyncOpenAI(api_key=os.getenv(config.get('llm.providers.openai.api_key_env')))
        elif name == 'claude':
            import anthropic
            return anthropic.AsyncAnthropic(api_key=os.getenv(config.get('llm.providers.claude.api_key_env')))
        elif name == 'ollama':
            return {'base_url': config.get('llm.providers.ollama.base_url', 'http://localhost:11434'),
                    'model': config.get('llm.providers.ollama.model', 'llama3')}
    
    async def generate(self, prompt: str, temperature: float = 0.5, max_tokens: int = 1500) -> str:
        """Generate text using primary provider, fallback on error"""
        try:
            return await self._call_provider(self.primary, prompt, temperature, max_tokens)
        except Exception:
            if self.fallback and self.fallback != self.primary:
                return await self._call_provider(self.fallback, prompt, temperature, max_tokens)
            raise
    
    async def _call_provider(self, name, prompt, temperature, max_tokens) -> str:
        """Route to provider-specific API call"""
        provider = self.providers.get(name)
        if not provider:
            raise ValueError(f"LLM provider '{name}' not initialized")
        
        if name == 'gemini':
            response = provider.generate_content(prompt, generation_config={'temperature': temperature, 'max_output_tokens': max_tokens})
            return response.text
        elif name == 'openai':
            response = await provider.chat.completions.create(
                model=self.providers_config['openai']['model'],
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature, max_tokens=max_tokens
            )
            return response.choices[0].message.content
        elif name == 'claude':
            response = await provider.messages.create(
                model=self.providers_config['claude']['model'],
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature, max_tokens=max_tokens
            )
            return response.content[0].text
        elif name == 'ollama':
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{provider['base_url']}/api/generate",
                    json={'model': provider['model'], 'prompt': prompt, 'stream': False,
                          'options': {'temperature': temperature, 'num_predict': max_tokens}}
                )
                return resp.json()['response']
```

**Tests (`tests/unit/test_core/test_llm_client.py`):**
- Test provider initialization (only enabled ones loaded)
- Test `generate()` calls primary provider
- Test fallback on primary failure
- Test each provider call format (mocked)
- Test no providers enabled → clear error

---

### `config/settings.py` — Configuration Manager

> [!NOTE]
> This file lives in `config/` not `core/`, since it loads from `config/default_config.yaml`.

```python
class Settings:
    def __init__(self, config_path: str = "config/default_config.yaml")
    
    def load(self) -> None                           # Load YAML
    def get(self, key: str, default: Any = None) -> Any  # Dot-notation: "input.image.processors.easyocr.enabled"
    def set(self, key: str, value: Any) -> None      # Runtime update
    def is_enabled(self, key: str) -> bool            # Shorthand for get(key + ".enabled", False)
    def get_enabled_processors(self, category: str) -> List[Dict]  # Get all enabled processors sorted by priority
    def get_enabled_sources(self, tier: Optional[int] = None) -> List[Dict]  # Get enabled research sources
    def to_dict(self) -> Dict[str, Any]
    
    async def load_db_overrides(self, db: Database) -> None  # Load overrides from system_config table
```

**Tests (`tests/unit/test_core/test_settings.py`):**
- Test YAML loading
- Test dot-notation get/set
- Test `is_enabled()` for various paths
- Test `get_enabled_processors()` returns sorted by priority, only enabled ones
- Test DB override takes precedence over YAML

---

### `core/logger.py` — Logging Setup

```python
import logging

def get_logger(name: str) -> logging.Logger:
    """Get a configured logger with consistent formatting"""
    ...

def setup_logging(level: str = "INFO") -> None:
    """Configure root logging"""
    ...
```

**Tests:**
- Test logger creation
- Test log output format

---

## Module-Level Test (`tests/module/test_core_module.py`)

Tests the full core module working together:
1. Create `Settings` from YAML
2. Initialize `Database` (creates SQLite + all tables)
3. Create `VectorStore` (ChromaDB)
4. Verify all tables exist
5. Verify seed data inserted
6. Create a `SystemState` via factory
7. Test config DB override flow
8. Clean up (delete test DB files)

---

## Dependencies

```
aiosqlite>=0.19.0
chromadb>=0.4.0
pyyaml>=6.0
```
