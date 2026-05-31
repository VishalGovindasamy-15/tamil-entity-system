# PROMPT: Build Core Module

## Context Files (Attach These)

Upload/attach these files before pasting this prompt:
1. `implementation_plan.md` — The master architecture document
2. `module_core.md` — Detailed spec for the Core module

---

## Prompt (Paste Everything Below)

---

You are building the **Core module** for a Tamil Entity Recognition system. This is the foundational module — every other module in the system depends on the code you create here.

### YOUR TASK

Read the attached files carefully:
1. **`implementation_plan.md`** — Understand the full system architecture, directory structure, data flow, and configuration system.
2. **`module_core.md`** — This is your detailed spec. Implement **every file** listed in it.

### WORKSPACE SETUP

The project root is `tamil-entity-system/`. Create the following directory structure first:

```
tamil-entity-system/
├── backend/
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py
│   │   ├── default_config.yaml
│   │   └── test_config.yaml
│   ├── core/
│   │   ├── __init__.py
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── state.py
│   │   ├── contracts.py
│   │   ├── base_agent.py
│   │   ├── base_source.py
│   │   ├── base_processor.py
│   │   ├── llm_client.py
│   │   └── logger.py
│   ├── modules/
│   │   └── __init__.py            # Empty — parent package for all modules
│   ├── data/
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── unit/
│   │   │   └── test_core/
│   │   │       ├── __init__.py
│   │   │       ├── test_database.py
│   │   │       ├── test_models.py
│   │   │       ├── test_state.py
│   │   │       ├── test_contracts.py
│   │   │       ├── test_base_agent.py
│   │   │       ├── test_base_source.py
│   │   │       ├── test_base_processor.py
│   │   │       ├── test_settings.py
│   │   │       ├── test_llm_client.py
│   │   │       └── test_logger.py
│   │   └── module/
│   │       └── test_core_module.py   # Full module integration test
│   └── requirements.txt
```

### IMPLEMENTATION RULES

1. **Follow the spec exactly.** Every class, method, and function documented in `module_core.md` must be implemented.

2. **SystemState** (`core/state.py`): Use `TypedDict`. The `create_initial_state()` factory function must initialize ALL fields with proper defaults:
   - Strings → `""`
   - Lists → `[]`
   - Dicts → `{}`
   - Numbers → `0` or `0.0`
   - `processing_status` → `"pending"`
   - `started_at` → current ISO timestamp
   - `request_id` → the provided request_id

3. **Database** (`core/database.py`): Use `aiosqlite` for async SQLite. The `Database` class must:
   - Create ALL 10 tables from `core/models.py` on `initialize()`
   - Insert seed data on first run
   - Provide `execute()`, `fetchone()`, `fetchall()`, `fetchval()` helpers
   - VectorStore class uses ChromaDB

4. **Models** (`core/models.py`): Define all 10 CREATE TABLE statements as a dict. The tables are:
   - `learned_transliterations`, `entity_knowledge`, `source_credibility`, `api_performance`
   - `user_feedback`, `processing_requests`, `agent_learning_log`, `system_config`
   - `custom_sources`, `custom_input_processors`
   - Include SEED_CONFIG and SEED_SOURCES lists.

5. **Contracts** (`core/contracts.py`): Use `@dataclass` with `field(default_factory=...)` for mutable defaults. Include `SourceType` enum, `SourceConfig`, `SourceResult`, `ProcessorResult`.

6. **BaseAgent** (`core/base_agent.py`): Must have `execute()` method that takes `SystemState` and returns `SystemState`. Include `log_step()`, `log_error()`, `increment_api_calls()`, `increment_cache_hits()`, `get_config()`.

7. **BaseSourcePlugin** (`core/base_source.py`): ABC with abstract `search()` and `health_check()`.

8. **BaseInputProcessor** (`core/base_processor.py`): ABC with abstract `process()` and `health_check()`.

9. **LLMClient** (`core/llm_client.py`): Provider wrapper supporting Gemini, OpenAI, Claude, Ollama. Must have `generate()` method with primary/fallback routing. Use environment variables for API keys.

10. **Settings** (`config/settings.py`): Loads from `config/default_config.yaml`. Must support:
    - Dot-notation access: `settings.get("input.image.processors.easyocr.enabled")`
    - `is_enabled(key)` shorthand
    - `get_enabled_processors(category)` returns sorted by priority
    - `get_enabled_sources(tier)` returns filtered sources
    - `load_db_overrides(db)` loads runtime overrides from `system_config` table

11. **default_config.yaml**: Copy the FULL config from `implementation_plan.md` (the YAML block under "Configuration System"). This is critical — every other module reads from this config.

12. **test_config.yaml**: A minimal version with only free/local APIs enabled (EasyOCR, Tesseract, Whisper, spaCy, Wikipedia, Wikidata, DuckDuckGo, Ollama).

13. **requirements.txt**: Include all dependencies for the core module:
    ```
    aiosqlite>=0.19.0
    chromadb>=0.4.0
    pyyaml>=6.0
    httpx>=0.25.0
    google-generativeai>=0.3.0
    openai>=1.0.0
    anthropic>=0.18.0
    pytest>=7.4.0
    pytest-asyncio>=0.21.0
    ```

### TESTING RULES

After creating each file, create its corresponding test file. Tests must:
- Use `pytest` and `pytest-asyncio`
- Use temporary files for SQLite (not the real database)
- Test happy path, edge cases, and error handling
- Mock external APIs (LLM providers)

After ALL files are created, run:
```bash
cd tamil-entity-system/backend
pip install -r requirements.txt
pytest tests/unit/test_core/ -v
```

Fix any failures before declaring the module complete.

### FINAL CHECKLIST

Before you finish, verify:
- [ ] All 10 files in `core/` are created and working
- [ ] `config/settings.py` loads `default_config.yaml` correctly
- [ ] `config/default_config.yaml` has the FULL configuration
- [ ] `config/test_config.yaml` exists with minimal config
- [ ] `core/__init__.py` exports all public symbols
- [ ] `modules/__init__.py` exists (empty parent package)
- [ ] `create_initial_state()` returns a state with ALL required keys
- [ ] All unit tests pass (`pytest tests/unit/test_core/ -v`)
- [ ] Module test passes (`pytest tests/module/test_core_module.py -v`)
- [ ] `requirements.txt` is complete
