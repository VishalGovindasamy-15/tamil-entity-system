# PROMPT: Build Transliteration & Normalization Module

## Context Files (Attach These)

Upload/attach these files before pasting this prompt:
1. `implementation_plan.md` — The master architecture document
2. `module_transliteration.md` — Detailed spec for this module

Also make sure the **Core module code** already exists in the workspace at `tamil-entity-system/backend/core/` and `tamil-entity-system/backend/config/`.

---

## Prompt (Paste Everything Below)

---

You are building the **Transliteration & Normalization Module** for a Tamil Entity Recognition system.

### STEP 0: READ AND UNDERSTAND

1. Read **`implementation_plan.md`** — Focus on the SystemState, config system, and data flow.
2. Read **`module_transliteration.md`** — Your complete spec.
3. Read the **existing core module code**:
   - `backend/core/state.py` — SystemState fields
   - `backend/core/base_agent.py` — TransliterationAgent extends BaseAgent
   - `backend/core/database.py` — For SQLite cache reads/writes (learned_transliterations table)
   - `backend/core/database.py` (VectorStore class) — For ChromaDB fuzzy matching
   - `backend/config/settings.py` — How config.get() and is_enabled() work
   - `backend/config/default_config.yaml` — Transliteration section

### YOUR DATA CONTRACT

**What you receive (set by Input module):**
```python
state['raw_text']  # The extracted text from any input source
```

**What you MUST set:**
```python
state['normalized_text']               # Text with Roman Tamil converted to Tamil script
state['detected_scripts']              # ['tamil', 'english', 'roman_tamil'] — which scripts are present
state['transliteration_map']           # {'naan': 'நான்', 'ponen': 'போனேன்'} — all mappings used
state['transliteration_confidence']    # {'naan': 0.95, 'ponen': 0.88} — confidence per word
```

**What you must NOT modify:** `raw_text`, `input_type`, `input_metadata`, or any other existing fields.

**Who reads your output:** The Extraction module reads `state['normalized_text']` to find entities.

### FILES TO CREATE

```
backend/modules/transliteration/
├── __init__.py              # Exports: TransliterationAgent
├── agent.py                 # TransliterationAgent — main orchestrator
├── script_detector.py       # ScriptDetector — detects Tamil/English/Roman Tamil
├── transliterators.py       # GoogleTranslateTransliterator, IndicTransliterator, AI4BharatTransliterator
└── consensus.py             # ConsensusEngine — multi-API consensus voting

backend/tests/unit/test_transliteration/
├── __init__.py
├── test_agent.py
├── test_script_detector.py
├── test_transliterators.py
└── test_consensus.py

backend/tests/module/
└── test_transliteration_module.py
```

### IMPLEMENTATION RULES

1. **TransliterationAgent extends BaseAgent**. Its `execute(state)` method must:
   - Detect scripts using ScriptDetector
   - If no `roman_tamil` detected → set `normalized_text = raw_text` and return (fast path)
   - If Roman Tamil found → process each word:
     a. Check SQLite cache (`learned_transliterations` table) — if found, use cached, call `self.increment_cache_hits(state)`
     b. Check ChromaDB vector similarity (handles typos like "naaan" → matches "naan")
     c. Query enabled transliteration APIs in parallel
     d. Run consensus voting on API results
     e. Store the learned mapping in SQLite for future cache hits

2. **ScriptDetector** must:
   - Detect Tamil chars using Unicode range U+0B80–U+0BFF
   - Detect English chars (ASCII alpha < 128)
   - Detect Roman Tamil by checking phonetic patterns: `['aa', 'ee', 'oo', 'ai', 'au', 'zh', 'lla', 'nna', 'ndr', 'nth']`
   - Exclude common English stopwords from Roman Tamil detection (the, is, and, of, to, in, for, on, with, at)
   - `is_roman_tamil(word)` returns True/False for a single word
   - `detect(text)` returns list of detected scripts

3. **Transliterators** — Each is configurable via config:
   ```yaml
   transliteration.apis.google_translate.enabled: true
   transliteration.apis.google_translate.priority: 1
   ```
   - Each returns `{'source': 'name', 'tamil_word': 'நான்', 'confidence': 0.85}`
   - GoogleTranslateTransliterator: uses `googletrans` library
   - IndicTransliterator: uses `indic-transliteration` library (local, free, always works)
   - AI4BharatTransliterator: uses AI4Bharat API (optional)
   - Handle import errors gracefully

4. **ConsensusEngine**:
   - Group results by `tamil_word` value
   - Score each group: `agreement_count * avg_confidence`
   - Pick the highest scoring group
   - Return `{'tamil_word': '...', 'confidence': ..., 'agreement_count': ..., 'sources': [...]}`

5. **Database interactions:** Use the Database class from core:
   ```python
   # Read cache
   cached = await self.db.fetchone(
       "SELECT tamil_word, confidence FROM learned_transliterations WHERE roman_text = ?", word
   )
   # Write cache
   await self.db.execute(
       "INSERT OR REPLACE INTO learned_transliterations (roman_text, tamil_word, confidence, source_apis, usage_count) VALUES (?, ?, ?, ?, 1)",
       word, tamil_word, confidence, json.dumps(sources)
   )
   ```

6. **ChromaDB interactions:** Use VectorStore from core:
   ```python
   similar = await self.vector_store.search(
       collection="transliterations",
       query_text=word,
       limit=1,
       score_threshold=0.90
   )
   ```

### TESTING RULES

1. **Script detector tests are critical** — test with actual Tamil Unicode chars, English text, and Tanglish patterns
2. **Mock the transliteration APIs** (googletrans, indic-transliteration) in unit tests
3. **Test consensus logic** with various agreement/disagreement scenarios
4. **Test caching** — second call for same word hits DB, not APIs
5. Run:
   ```bash
   cd tamil-entity-system/backend
   pytest tests/unit/test_transliteration/ -v
   pytest tests/module/test_transliteration_module.py -v
   ```

### FINAL CHECKLIST

- [ ] Pure Tamil text → passthrough, no API calls, no errors
- [ ] Pure English text → passthrough, no transliteration
- [ ] Roman Tamil ("naan school ponen") → "நான் school போனேன்"
- [ ] Mixed text → only Roman Tamil words converted
- [ ] Cache hit path works (second call uses DB)
- [ ] All APIs disabled → returns original words with warning
- [ ] Consensus engine handles agreements and disagreements
- [ ] All tests pass
