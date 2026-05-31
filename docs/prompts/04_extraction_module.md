# PROMPT: Build Entity Extraction Module

## Context Files (Attach These)

Upload/attach these files before pasting this prompt:
1. `implementation_plan.md` — The master architecture document
2. `module_extraction.md` — Detailed spec for this module

Also make sure the **Core module code** already exists in the workspace at `tamil-entity-system/backend/core/` and `tamil-entity-system/backend/config/`.

---

## Prompt (Paste Everything Below)

---

You are building the **Entity Extraction Module** for a Tamil Entity Recognition system.

### STEP 0: READ AND UNDERSTAND

1. Read **`implementation_plan.md`** — Focus on SystemState, entity format, and config system.
2. Read **`module_extraction.md`** — Your complete spec with entity type taxonomy, merger logic, and normalizer mappings.
3. Read the **existing core module code**:
   - `backend/core/state.py` — SystemState fields
   - `backend/core/base_agent.py` — EntityExtractionAgent extends BaseAgent
   - `backend/core/contracts.py` — Data contracts
   - `backend/core/llm_client.py` — LLM client for fallback extraction
   - `backend/config/default_config.yaml` — extraction section

### YOUR DATA CONTRACT

**What you receive (set by Transliteration module):**
```python
state['normalized_text']  # Tamil/English text with all Roman Tamil already converted
```

**What you MUST set:**
```python
state['entities']  # List of entity dicts, each containing:
# {
#   "text": "அப்துல் கலாம்",        # The entity text as it appears
#   "type": "PERSON",                # Normalized type from taxonomy
#   "confidence": 0.95,              # 0.0-1.0
#   "start": 0,                      # Character position start (-1 if unknown)
#   "end": 13,                       # Character position end (-1 if unknown)
#   "context": "surrounding text",   # ~50 chars around the entity
#   "sources": ["spacy", "stanza"],  # Which NER models found it
#   "agreement_count": 2,            # How many models agreed
#   "expanded_form": null             # For abbreviations like ISRO → "Indian Space Research Organisation"
# }
```

**Who reads your output:** The Research module reads `state['entities']` to research each entity.

### ENTITY TYPE TAXONOMY (must use these exact type strings)

| Type | Maps From |
|------|-----------|
| `PERSON` | PER, PERSON |
| `ORGANIZATION` | ORG, ORGANIZATION, COMPANY |
| `LOCATION` | GPE, LOC, LOCATION, PLACE, CITY, COUNTRY |
| `DATE` | DATE |
| `TIME` | TIME |
| `EVENT` | EVENT |
| `CONCEPT` | CONCEPT |
| `PRODUCT` | PRODUCT |
| `NATURAL` | NATURAL |
| `RELIGIOUS` | RELIGIOUS |
| `CULTURAL` | WORK_OF_ART, CULTURAL |
| `OTHER` | anything else |

### FILES TO CREATE

```
backend/modules/extraction/
├── __init__.py              # Exports: EntityExtractionAgent
├── agent.py                 # EntityExtractionAgent — multi-model orchestrator
├── spacy_extractor.py       # SpacyExtractor — spaCy multilingual NER
├── stanza_extractor.py      # StanzaExtractor — Stanza Tamil NER
├── cloud_extractor.py       # GoogleNLPExtractor, AzureNLPExtractor
├── llm_extractor.py         # LLMExtractor — LLM-based fallback with JSON prompt
├── merger.py                # EntityMerger — overlap detection, voting, deduplication
└── normalizer.py            # EntityTypeNormalizer — maps labels to unified taxonomy

backend/tests/unit/test_extraction/
├── __init__.py
├── test_agent.py
├── test_spacy_extractor.py
├── test_stanza_extractor.py
├── test_cloud_extractor.py
├── test_llm_extractor.py
├── test_merger.py
└── test_normalizer.py

backend/tests/module/
└── test_extraction_module.py
```

### IMPLEMENTATION RULES

1. **EntityExtractionAgent extends BaseAgent**. Its `execute(state)` method must:
   - Load enabled extractors from config (`extraction.models.{name}.enabled`)
   - Run enabled primary extractors in parallel using `asyncio.gather()`
   - Calculate average confidence across results
   - If avg confidence < threshold (`extraction.confidence_threshold`) AND llm_fallback is enabled → run LLMExtractor
   - Merge all results using EntityMerger
   - Normalize types using EntityTypeNormalizer
   - Enrich with context (50 chars around each entity)

2. **Each extractor** returns the same format:
   ```python
   {'source': 'spacy', 'entities': [...], 'avg_confidence': 0.85}
   ```

3. **LLMExtractor** uses `LLMClient.generate()` from core with a structured JSON prompt:
   - Prompt asks for JSON array output
   - Parse with `json.loads()`, handle malformed JSON with retry (up to 2 retries)
   - Temperature: 0.1 (deterministic)

4. **EntityMerger** logic:
   - Two entities overlap if they have the same `text` (case-insensitive) OR their character positions overlap
   - Group overlapping entities
   - For each group: pick best text (highest confidence), vote on type (weighted by confidence), average confidence, collect all sources
   - Non-overlapping entities stay separate

5. **EntityTypeNormalizer**: Simple dict lookup. Unknown labels → "OTHER".

6. **Context extraction**: For each entity, extract `text[max(0, start-25):end+25]` as surrounding context.

7. **Config checking:**
   ```python
   if self.config.is_enabled('extraction.models.spacy'):
       # Use spacy
   ```

### TESTING RULES

1. **Mock spaCy and Stanza** in unit tests (don't require model downloads)
2. **Test merger thoroughly** — overlap detection, voting, deduplication
3. **Test normalizer** — all known label mappings + unknown → OTHER
4. **Test LLM extractor** — prompt construction, JSON parsing, malformed JSON handling
5. Run:
   ```bash
   cd tamil-entity-system/backend
   pytest tests/unit/test_extraction/ -v
   pytest tests/module/test_extraction_module.py -v
   ```

### FINAL CHECKLIST

- [ ] spaCy extractor works (with mock in tests)
- [ ] Stanza extractor works (with mock in tests)
- [ ] LLM fallback triggers when primary confidence is low
- [ ] LLM fallback handles malformed JSON gracefully
- [ ] Merger correctly deduplicates overlapping entities
- [ ] Merger voting picks correct type when models disagree
- [ ] Normalizer maps all known labels correctly
- [ ] All models disabled → empty entities list with warning, no crash
- [ ] Context extraction works
- [ ] All entities have ALL required fields
- [ ] All tests pass
