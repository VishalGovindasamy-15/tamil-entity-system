# PROMPT: Integration Testing — Wire All Modules Together

## Context Files (Attach These)

Upload/attach these files before pasting this prompt:
1. `implementation_plan.md` — The master architecture document
2. `integration_testing.md` — Detailed integration test spec

Also make sure **ALL code** exists in the workspace — all modules in `tamil-entity-system/backend/` must be built and their unit/module tests passing.

---

## Prompt (Paste Everything Below)

---

You are performing **integration testing** for a Tamil Entity Recognition system. All modules have been built independently by different team members. Your job is to:

1. Wire everything together
2. Fix any integration issues
3. Run the full test suite
4. Verify end-to-end data flow

### STEP 0: READ AND UNDERSTAND

1. Read **`implementation_plan.md`** — Focus on data flow, SystemState, and module dependency order.
2. Read **`integration_testing.md`** — Your complete test spec.
3. Read ALL the code in the workspace:
   - `backend/core/` — All core classes
   - `backend/config/` — Settings and YAML configs
   - `backend/modules/input/` — Input processing
   - `backend/modules/transliteration/` — Script detection + transliteration
   - `backend/modules/extraction/` — Entity extraction
   - `backend/modules/research/` — Entity research
   - `backend/modules/explanation/` — Explanation generation
   - `backend/modules/response/` — Response compilation
   - `backend/pipeline/orchestrator.py` — Pipeline
   - `backend/server/` — FastAPI server

### STEP 1: VERIFY IMPORTS AND WIRING

Check that the Pipeline Orchestrator correctly imports and instantiates all agents:
```python
# pipeline/orchestrator.py should import these:
from modules.input import InputCoordinator
from modules.transliteration import TransliterationAgent
from modules.extraction import EntityExtractionAgent
from modules.research import EntityResearchAgent
from modules.explanation import ExplanationAgent
from modules.response import ResponseBuilder
```

Fix any import errors, circular imports, or mismatched constructor signatures.

### STEP 2: VERIFY DATA FLOW CONTRACTS

Check that each module reads and writes the correct SystemState fields:

| Module | Reads | Writes |
|--------|-------|--------|
| Input | `input_type`, `input_content`, `input_metadata` | `raw_text`, `detected_language`, `input_metadata.quality_score` |
| Transliteration | `raw_text` | `normalized_text`, `detected_scripts`, `transliteration_map`, `transliteration_confidence` |
| Extraction | `normalized_text` | `entities` |
| Research | `entities` | `entity_knowledge`, `sources_accessed` |
| Explanation | `entity_knowledge` | `explanations` |
| Response | ALL fields | `final_response`, `processing_status` |

If any module reads a field name differently than what the previous module writes, FIX IT.

### STEP 3: CREATE INTEGRATION TEST FILES

```
backend/tests/
├── conftest.py                         # Shared fixtures
├── test_data.py                        # Sample Tamil texts + expected results
├── integration/
│   ├── __init__.py
│   ├── test_full_pipeline.py           # End-to-end pipeline tests
│   ├── test_api_endpoints.py           # API endpoint integration tests
│   ├── test_config_toggles.py          # Config toggling tests
│   ├── test_contracts.py               # Data contract validation
│   └── test_caching.py                 # Cache hit tests
```

**`conftest.py` must include these fixtures:**
```python
import pytest
import tempfile
import os

@pytest.fixture
async def test_db():
    """Temporary SQLite database for testing"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    db = Database(sqlite_path=db_path, chroma_path=tempfile.mkdtemp())
    await db.initialize()
    yield db
    await db.close()
    os.unlink(db_path)

@pytest.fixture
def test_config():
    """Load test_config.yaml (free APIs only)"""
    settings = Settings(config_path="config/test_config.yaml")
    settings.load()
    return settings

@pytest.fixture
def sample_state():
    """A pre-populated state for testing mid-pipeline modules"""
    return create_initial_state(
        request_id="test-123",
        input_type="text",
        input_content="அப்துல் கலாம் ஒரு விஞ்ஞானி",
        input_metadata={}
    )

@pytest.fixture
async def test_app(test_db, test_config):
    """FastAPI test app with test database"""
    from server.app import create_app
    app = create_app()
    app.state.db = test_db
    app.state.config = test_config
    yield app
```

**`test_data.py` must include:**
```python
# Sample Tamil texts for testing
SAMPLE_TAMIL_TEXT = "அப்துல் கலாம் இந்தியாவின் 11வது குடியரசுத் தலைவர் ஆவார்"
SAMPLE_MIXED_TEXT = "Abdul Kalam was born in ராமேஸ்வரம்"
SAMPLE_ROMAN_TAMIL = "naan school ponen"
SAMPLE_ENGLISH_TEXT = "The Taj Mahal is in Agra"
SAMPLE_EMPTY_TEXT = ""

# Expected entity types
EXPECTED_PERSON = "PERSON"
EXPECTED_LOCATION = "LOCATION"
EXPECTED_ORGANIZATION = "ORGANIZATION"
```

### STEP 4: WRITE AND RUN TESTS

Create these integration tests:

1. **test_full_pipeline.py:**
   - Tamil text → full pipeline → entities + explanations returned
   - Mixed Tamil/English text → transliteration + extraction works
   - Roman Tamil text → transliterated, then entities extracted
   - Empty text → no crash, empty entities

2. **test_api_endpoints.py:**
   - POST /api/process with text → 200, response has entities
   - POST /api/process with file → 200
   - GET /api/health → 200, status "healthy"
   - GET /api/config → 200, has config keys
   - GET /api/db/entity_knowledge → 200, has rows array
   - PUT /api/config/key → 200, value updated
   - Invalid table name → 400

3. **test_config_toggles.py:**
   - Disable all OCR engines → image input returns empty text
   - Disable all NER models → no entities extracted, no crash
   - Disable all research sources → empty knowledge, no crash
   - Switch LLM provider → still works

4. **test_contracts.py:**
   - After pipeline run, verify ALL SystemState fields exist
   - Verify entities have all required fields (text, type, confidence, sources)
   - Verify entity_knowledge has verified_facts dict
   - Verify explanations have tamil and english sections

5. **test_caching.py:**
   - First request → API calls made
   - Second identical request → cache hits increased, fewer API calls

### STEP 5: RUN EVERYTHING

```bash
cd tamil-entity-system/backend

# 1. Run all unit tests first
pytest tests/unit/ -v

# 2. Run module tests
pytest tests/module/ -v

# 3. Run integration tests
pytest tests/integration/ -v

# 4. Run everything with coverage
pytest tests/ -v --tb=short
```

### STEP 6: FIX ALL FAILURES

For each test failure:
1. Read the error message
2. Identify which module has the bug
3. Fix the code
4. Re-run the test

Common integration issues to look for:
- **Import errors**: Module A imports from Module B incorrectly
- **Field name mismatches**: Module A writes `state['raw_text']` but Module B reads `state['text']`
- **Constructor signature mismatches**: Orchestrator passes wrong args to agent constructors
- **Config key mismatches**: Code checks `config.is_enabled('spacy')` but config has `extraction.models.spacy.enabled`
- **Missing __init__.py exports**: Module's `__init__.py` doesn't export the correct class
- **Async/await issues**: Forgetting `await` on async methods

### STEP 7: CREATE README.md

Create `tamil-entity-system/README.md` with:
- Project title and description
- Quick start instructions (how to install + run backend + run frontend)
- Directory structure overview
- Available API endpoints
- Configuration guide (how to toggle APIs)
- Testing guide (`pytest tests/ -v`)
- Team contributors list

### FINAL CHECKLIST

- [ ] All imports resolve correctly (no import errors)
- [ ] Pipeline orchestrator chains all 6 modules
- [ ] Data flows correctly through all stages (verified by contract tests)
- [ ] Full pipeline works end-to-end with Tamil text
- [ ] All API endpoints respond correctly
- [ ] Config toggling doesn't crash the pipeline
- [ ] Caching works (second request is faster)
- [ ] All unit tests pass
- [ ] All module tests pass
- [ ] All integration tests pass
- [ ] Server starts without errors: `python main.py`
- [ ] README.md created
