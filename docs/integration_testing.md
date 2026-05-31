# Integration Testing

## Purpose
Validate that all modules work together correctly end-to-end. Tests cover the full pipeline, API endpoints, frontend-backend integration, and configuration toggling.

---

## Test Environment Setup

```python
# tests/conftest.py

import pytest
import asyncio
import tempfile
import os

@pytest.fixture
async def test_db():
    """Create a temporary SQLite database for testing"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    db = Database(sqlite_path=db_path, chroma_path=tempfile.mkdtemp())
    await db.initialize()
    yield db
    await db.close()
    os.unlink(db_path)

@pytest.fixture
def test_config():
    """Create a test config with only free/local APIs enabled"""
    config = Settings(config_path="config/test_config.yaml")
    config.load()
    return config

@pytest.fixture
async def test_pipeline(test_db, test_config):
    """Create a pipeline orchestrator for testing"""
    pipeline = PipelineOrchestrator(test_db, test_config)
    return pipeline

@pytest.fixture
async def test_app(test_db, test_config):
    """Create a FastAPI test app"""
    app = create_app()
    app.state.db = test_db
    app.state.config = test_config
    app.state.pipeline = PipelineOrchestrator(test_db, test_config)
    return app

@pytest.fixture
async def client(test_app):
    """Create an async HTTP test client"""
    from httpx import AsyncClient
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        yield client
```

---

## Test Config (`config/test_config.yaml`)

Minimal config using only free/local APIs for CI:

```yaml
llm:
  primary: "ollama"  # Or mock
  providers:
    ollama:
      enabled: true
      base_url: "http://localhost:11434"
      model: "llama3"

input:
  text:
    enabled: true
  image:
    processors:
      easyocr:
        enabled: true
        priority: 1
      tesseract:
        enabled: true
        priority: 2
  pdf:
    processors:
      pymupdf:
        enabled: true
  audio:
    processors:
      whisper:
        enabled: true
        model: "tiny"  # Smallest model for tests

extraction:
  models:
    spacy:
      enabled: true
    stanza:
      enabled: false  # Slow to load in CI
    llm_fallback:
      enabled: true

research:
  sources:
    wikipedia:
      enabled: true
    wikidata:
      enabled: true
    dbpedia:
      enabled: true
    web_search:
      enabled: true
      engine: "duckduckgo"
    # All paid APIs disabled for tests

explanation:
  hallucination_check: true
  strict_retry: false  # Save time in tests
```

---

## Sample Test Data

```python
# tests/test_data.py

TAMIL_TEXT_SAMPLES = {
    "simple_person": "அப்துல் கலாம் இந்தியாவின் முன்னாள் குடியரசுத் தலைவர் ஆவார்.",
    
    "mixed_content": "Abdul Kalam worked at ISRO before becoming India's president. "
                     "அவர் 1931 இல் ராமேஸ்வரத்தில் பிறந்தார்.",
    
    "roman_tamil": "naan oru tamilan. en oor Chennai. naan ISRO la velai paarthen.",
    
    "multiple_entities": "மகாத்மா காந்தி சென்னையில் காங்கிரஸ் கட்சி மாநாட்டில் கலந்துகொண்டார்.",
    
    "complex_text": """திருவள்ளுவர் எழுதிய திருக்குறள் தமிழ் இலக்கியத்தின் மகத்தான 
    படைப்பாகும். இது 1330 குறள்களைக் கொண்டது. அறத்துப்பால், பொருட்பால், 
    காமத்துப்பால் என மூன்று பிரிவுகளாக பிரிக்கப்பட்டுள்ளது.""",
    
    "entity_rich": "ISRO வின் சந்திரயான்-3 திட்டம் 2023 ஆகஸ்டு 23 அன்று "
                   "நிலவின் தென் துருவத்தில் வெற்றிகரமாக தரையிறங்கியது."
}

EXPECTED_ENTITIES = {
    "simple_person": [
        {"text": "அப்துல் கலாம்", "type": "PERSON"},
        {"text": "இந்தியா", "type": "LOCATION"}
    ],
    "entity_rich": [
        {"text": "ISRO", "type": "ORGANIZATION"},
        {"text": "சந்திரயான்-3", "type": "PRODUCT"},
        {"text": "நிலவு", "type": "NATURAL"}
    ]
}
```

---

## Integration Tests

### Test 1: Full Pipeline — Text Input

```python
# tests/integration/test_full_pipeline.py

@pytest.mark.asyncio
async def test_text_pipeline_end_to_end(test_pipeline):
    """Complete pipeline: Tamil text → entities → research → explanations"""
    
    result = await test_pipeline.run(
        request_id="test-001",
        input_type="text",
        input_content=TAMIL_TEXT_SAMPLES["simple_person"],
        input_metadata={}
    )
    
    # Assertions
    assert result['processing_status'] != 'failed'
    assert len(result['entities']) > 0
    
    # Check entity found
    entity_names = [e['text'] for e in result['entities']]
    assert any('கலாம்' in name for name in entity_names)
    
    # Check explanations generated
    for entity in result['entities']:
        name = entity['text']
        if name in result['explanations']:
            explanation = result['explanations'][name]
            assert explanation.get('tamil') is not None or explanation.get('english') is not None
    
    # Check timing tracked
    assert 'input_processing' in result['stage_timings']
    assert 'entity_extraction' in result['stage_timings']
```

### Test 2: Full Pipeline — Mixed Content

```python
@pytest.mark.asyncio
async def test_mixed_content_pipeline(test_pipeline):
    """Pipeline handles mixed Tamil + English + Roman Tamil"""
    
    result = await test_pipeline.run(
        request_id="test-002",
        input_type="text",
        input_content=TAMIL_TEXT_SAMPLES["roman_tamil"],
        input_metadata={}
    )
    
    # Transliteration should have occurred
    assert len(result['transliteration_map']) > 0
    assert 'roman_tamil' in result['detected_scripts']
```

### Test 3: Full Pipeline — Image Input

```python
@pytest.mark.asyncio
async def test_image_pipeline(test_pipeline):
    """Pipeline: Image → OCR → entities → explanations"""
    
    # Use a test image with Tamil text
    result = await test_pipeline.run(
        request_id="test-003",
        input_type="image",
        input_content="tests/fixtures/tamil_text_image.png",
        input_metadata={"filename": "test.png"}
    )
    
    assert result['raw_text'] != ""  # OCR extracted text
    assert result['processing_status'] != 'failed'
```

### Test 4: Full Pipeline — URL Input

```python
@pytest.mark.asyncio
async def test_url_pipeline(test_pipeline):
    """Pipeline: URL → scrape → entities → explanations"""
    
    result = await test_pipeline.run(
        request_id="test-004",
        input_type="url",
        input_content="https://ta.wikipedia.org/wiki/அப்துல்_கலாம்",
        input_metadata={}
    )
    
    assert result['raw_text'] != ""
```

---

### Test 5: API Endpoint Integration

```python
# tests/integration/test_api_endpoints.py

@pytest.mark.asyncio
async def test_process_endpoint(client):
    """POST /api/process with text input"""
    
    response = await client.post("/api/process", data={
        "text": TAMIL_TEXT_SAMPLES["simple_person"],
        "output_format": "json"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "entities" in data
    assert "summary" in data
    assert data["summary"]["total_entities"] > 0


@pytest.mark.asyncio
async def test_entities_endpoint(client):
    """GET /api/entities after processing"""
    
    # First process something
    await client.post("/api/process", data={
        "text": TAMIL_TEXT_SAMPLES["simple_person"]
    })
    
    # Then list entities
    response = await client.get("/api/entities")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_config_endpoint(client):
    """GET and PUT /api/config"""
    
    # Get config
    response = await client.get("/api/config")
    assert response.status_code == 200
    config = response.json()
    assert "extraction" in config
    
    # Update config
    response = await client.put("/api/config/extraction.confidence_threshold", json={
        "value": "0.90"
    })
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_db_admin_endpoint(client):
    """GET /api/db/{table} — DB browser"""
    
    response = await client.get("/api/db/entity_knowledge", params={"page": 1, "per_page": 10})
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "rows" in data


@pytest.mark.asyncio
async def test_health_endpoint(client):
    """GET /api/health"""
    
    response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_stats_endpoint(client):
    """GET /api/stats"""
    
    response = await client.get("/api/stats")
    assert response.status_code == 200
    assert "total_requests" in response.json()
```

---

### Test 6: Configuration Toggle Tests

```python
# tests/integration/test_config_toggles.py

@pytest.mark.asyncio
async def test_disable_all_ocr(test_pipeline, test_config):
    """Disabling all OCR engines → image input returns warning, no crash"""
    
    test_config.set("input.image.processors.easyocr.enabled", False)
    test_config.set("input.image.processors.tesseract.enabled", False)
    test_config.set("input.image.processors.google_vision.enabled", False)
    
    result = await test_pipeline.run(
        request_id="test-toggle-1",
        input_type="image",
        input_content="tests/fixtures/tamil_text_image.png",
        input_metadata={}
    )
    
    assert result['raw_text'] == ""
    assert len(result['warnings']) > 0  # Warning about no processors


@pytest.mark.asyncio
async def test_disable_all_research(test_pipeline, test_config):
    """Disabling all research sources → entities found but no explanations"""
    
    # Disable all sources
    for source in ['wikipedia', 'wikidata', 'dbpedia', 'web_search', 'llm_knowledge']:
        test_config.set(f"research.sources.{source}.enabled", False)
    
    result = await test_pipeline.run(
        request_id="test-toggle-2",
        input_type="text",
        input_content=TAMIL_TEXT_SAMPLES["simple_person"],
        input_metadata={}
    )
    
    # Entities should still be extracted
    assert len(result['entities']) > 0
    # But knowledge should be empty/minimal
    for name, knowledge in result['entity_knowledge'].items():
        assert knowledge.get('source_count', 0) == 0


@pytest.mark.asyncio
async def test_switch_ner_model(test_pipeline, test_config):
    """Switch from spaCy to LLM-only extraction → still works"""
    
    test_config.set("extraction.models.spacy.enabled", False)
    test_config.set("extraction.models.stanza.enabled", False)
    test_config.set("extraction.models.llm_fallback.enabled", True)
    
    result = await test_pipeline.run(
        request_id="test-toggle-3",
        input_type="text",
        input_content=TAMIL_TEXT_SAMPLES["entity_rich"],
        input_metadata={}
    )
    
    assert len(result['entities']) > 0
```

---

### Test 7: Data Contract Validation

```python
# tests/integration/test_contracts.py

@pytest.mark.asyncio
async def test_state_contracts(test_pipeline):
    """Verify state has all required fields after each stage"""
    
    result = await test_pipeline.run(
        request_id="test-contract-1",
        input_type="text",
        input_content=TAMIL_TEXT_SAMPLES["simple_person"],
        input_metadata={}
    )
    
    # Input module output
    assert 'raw_text' in result
    assert 'detected_language' in result
    
    # Transliteration module output
    assert 'normalized_text' in result
    assert 'detected_scripts' in result
    assert 'transliteration_map' in result
    
    # Extraction module output
    assert 'entities' in result
    assert isinstance(result['entities'], list)
    for entity in result['entities']:
        assert 'text' in entity
        assert 'type' in entity
        assert 'confidence' in entity
    
    # Research module output
    assert 'entity_knowledge' in result
    for name, knowledge in result['entity_knowledge'].items():
        assert 'verified_facts' in knowledge
        assert 'overall_confidence' in knowledge
    
    # Explanation module output
    assert 'explanations' in result
    
    # Metrics
    assert 'processing_steps' in result
    assert 'api_calls_made' in result
    assert 'stage_timings' in result
```

---

### Test 8: Caching & Learning Tests

```python
# tests/integration/test_caching.py

@pytest.mark.asyncio
async def test_cache_hit_on_repeat(test_pipeline):
    """Second request for same entity should hit cache"""
    
    # First request
    result1 = await test_pipeline.run(
        request_id="test-cache-1",
        input_type="text",
        input_content=TAMIL_TEXT_SAMPLES["simple_person"],
        input_metadata={}
    )
    api_calls_1 = result1['api_calls_made']
    
    # Second request (same text)
    result2 = await test_pipeline.run(
        request_id="test-cache-2",
        input_type="text",
        input_content=TAMIL_TEXT_SAMPLES["simple_person"],
        input_metadata={}
    )
    api_calls_2 = result2['api_calls_made']
    
    # Second should use fewer API calls (cache hits)
    assert result2['cache_hits'] > result1['cache_hits']
    assert api_calls_2 <= api_calls_1
```

---

## Test Matrix

| Test | Input Type | Modules Tested | Config | Expected |
|------|-----------|----------------|--------|----------|
| E2E Tamil text | text | All 7 | Default | Entities + explanations |
| E2E mixed text | text | All 7 | Default | Transliteration + entities |
| E2E image | image | All 7 | EasyOCR on | OCR → entities |
| E2E URL | url | All 7 | Default | Scrape → entities |
| API text | text | Server + All | Default | 200, JSON response |
| API image upload | image | Server + All | Default | 200, JSON response |
| Config toggle: OCR off | image | Input | All OCR disabled | Empty text, warning |
| Config toggle: NER off | text | Extraction | All NER disabled | No entities |
| Config toggle: sources off | text | Research | All disabled | No knowledge |
| Cache hit | text | Research | Default | Fewer API calls |
| DB Admin | — | Server | — | Tables browseable |
| Health check | — | Server | — | Healthy status |

---

## Running Tests

```bash
# Run all unit tests
pytest tests/unit/ -v

# Run module tests
pytest tests/module/ -v

# Run integration tests (requires Ollama running for LLM)
pytest tests/integration/ -v

# Run everything
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=backend --cov-report=html
```

---

## Test Fixtures

Place these in `tests/fixtures/`:
- `tamil_text_image.png` — Image with Tamil text for OCR testing
- `sample.pdf` — PDF with Tamil content
- `sample_audio.wav` — Short Tamil speech clip
- `test_config.yaml` — Minimal test configuration
