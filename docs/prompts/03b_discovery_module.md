# PROMPT: Build Candidate Entity Discovery Module

## Context Files (Attach These)

Upload/attach these files before pasting this prompt:
1. `implementation_plan.md` — The master architecture document
2. `module_discovery.md` — Detailed spec for this module

Also make sure the **Core module code** already exists in the workspace at `tamil-entity-system/backend/core/` and `tamil-entity-system/backend/config/`.

---

## Prompt (Paste Everything Below)

---

You are building the **Candidate Entity Discovery Module** for a Tamil Entity Recognition system. This is a **new module** that discovers unknown/novel Tamil entities that traditional NER models miss. It sits between Transliteration and Extraction in the pipeline.

### STEP 0: READ AND UNDERSTAND

1. Read **`implementation_plan.md`** — Focus on SystemState, pipeline flow, and the directory structure.
2. Read **`module_discovery.md`** — Your complete spec with all 5 strategies and the agent.
3. Read the **existing core module code**:
   - `backend/core/base_agent.py` — CandidateDiscoveryAgent extends BaseAgent
   - `backend/core/state.py` — SystemState fields (you read `normalized_text`, you write `candidate_entities`)
   - `backend/config/default_config.yaml` — The `candidate_discovery` config section

### YOUR DATA CONTRACT

**What you receive (from Transliteration module):**
```python
state['normalized_text']         # Tamil text (fully normalised)
state['detected_language']       # 'ta', 'en', 'mixed'
state['detected_scripts']        # ['tamil', 'english', ...]
state['transliteration_map']     # Roman → Tamil mappings
```

**What you MUST set:**
```python
state['candidate_entities'] = [
    {
        "text": "செந்தமிழ்ஏஐ",
        "candidate_type": "UNKNOWN",
        "discovery_methods": ["dictionary_mismatch", "compound_word"],
        "confidence": 0.55,
        "start": 5,
        "end": 16,
        "context": "நாளை செந்தமிழ்ஏஐ வெளியிடப்படுகிறது",
        "reason": "Word not found in Tamil dictionary; compound structure detected"
    }
]
```

### DIRECTORY STRUCTURE YOU CREATE

```
backend/modules/discovery/
├── __init__.py                  # Exports: CandidateDiscoveryAgent
├── agent.py                     # CandidateDiscoveryAgent — orchestrator
├── strategies/
│   ├── __init__.py
│   ├── dictionary_checker.py    # DictionaryMismatchStrategy
│   ├── compound_detector.py     # CompoundWordStrategy
│   ├── rare_word.py             # RareWordStrategy
│   ├── noun_phrase.py           # NounPhraseStrategy
│   └── context_pattern.py       # ContextPatternStrategy
├── tamil_wordlist.py            # Tamil dictionary/wordlist loader
└── candidate_merger.py          # Deduplicates and scores candidates

backend/tests/unit/test_discovery/
├── __init__.py
├── test_agent.py
├── test_dictionary_checker.py
├── test_compound_detector.py
├── test_rare_word.py
├── test_noun_phrase.py
├── test_context_pattern.py
└── test_candidate_merger.py

backend/tests/module/
└── test_discovery_module.py
```

### STEP 1: UNDERSTAND THE STRATEGIES

There are 5 discovery strategies. Each implements the same interface:

```python
class BaseDiscoveryStrategy:
    """All strategies implement this interface."""
    def __init__(self, name: str, config: Dict):
        self.name = name
        self.config = config

    async def discover(self, words: List[str], text: str) -> List[Dict]:
        """Return list of candidate dicts with: text, method, confidence, reason."""
        raise NotImplementedError
```

Strategies and their logic:

1. **DictionaryMismatchStrategy** — Word not in Tamil dictionary → candidate
   - Load Tamil wordlist (file or built-in ~500 words)
   - Skip stopwords, numbers, punctuation, very short words
   - Confidence: 0.5

2. **CompoundWordStrategy** — Unusually long or mixed-morpheme words → candidate
   - Count Tamil characters per word
   - Detect mixed-script compounds (Tamil + English fused)
   - Threshold: >8 Tamil chars or has mixed morphemes
   - Confidence: 0.45 (long) or 0.6 (mixed-script)

3. **RareWordStrategy** — Words with unusual frequency in the text → candidate
   - Count word frequencies in the input text
   - Words appearing at moderate frequency (not too common, not unique typos)
   - Confidence: 0.35

4. **NounPhraseStrategy** — Words in entity-like grammatical positions → candidate
   - Before case suffixes: `-ஐ`, `-ை`, `-க்கு`, `-ல்`, `-இல்`
   - After demonstratives: `இந்த`, `அந்த`, `எந்த`
   - Before action verbs
   - Confidence: 0.5

5. **ContextPatternStrategy** — Words matching entity context patterns → candidate
   - "X வெளியிடப்படுகிறது" → X is being released → X is entity
   - "X நிறுவனம்" → X is an organisation
   - "X என்ற" → "called X" → X is entity name
   - Confidence: 0.55

### STEP 2: BUILD IN THIS ORDER

Create files in this exact order, testing each one:

1. `tamil_wordlist.py` — Load wordlist, fallback to built-in
   - Test: contains known Tamil words, doesn't contain random strings

2. `strategies/dictionary_checker.py` — Dictionary mismatch strategy
   - Test: unknown word detected, known word not detected, stopwords excluded

3. `strategies/compound_detector.py` — Compound word detection
   - Test: short word → skip, long word → candidate, mixed script → higher confidence

4. `strategies/rare_word.py` — Rare word frequency analysis
   - Test: common word → skip, moderate frequency → candidate

5. `strategies/noun_phrase.py` — Grammatical position analysis
   - Test: word before case suffix → candidate, random position → skip

6. `strategies/context_pattern.py` — Context pattern matching
   - Test: "X வெளியிடப்படுகிறது" → X is candidate

7. `candidate_merger.py` — Deduplicate and boost confidence
   - Test: same word from 2 strategies → merged, confidence boosted

8. `agent.py` — CandidateDiscoveryAgent orchestrator
   - Test: full flow with sample text, disabled module returns `[]`

### STEP 3: KEY IMPLEMENTATION RULES

1. **Tamil character detection**: Use Unicode range `0x0B80` to `0x0BFF` for Tamil characters.

2. **Tokenisation**: Split `normalized_text` on whitespace and punctuation. Keep word positions (start, end) for output.

3. **Tamil stopwords** — Hardcode a set of ~50 common Tamil function words to exclude:
   ```python
   TAMIL_STOPWORDS = {
       'இது', 'அது', 'ஒரு', 'என்', 'நான்', 'நீ', 'அவன்', 'அவள்',
       'அவர்', 'நாம்', 'இந்த', 'அந்த', 'எந்த', 'மற்றும்', 'ஆனால்',
       'என்று', 'போல்', 'வரை', 'பற்றி', 'மிக', 'மிகவும்', 'இங்கு',
       'அங்கு', 'எங்கு', 'எப்போது', 'யார்', 'எது', 'எதற்கு', 'ஏன்',
       'தான்', 'கூட', 'அல்லது', 'இல்லை', 'உள்ள', 'உள்ளது', 'என்ன',
       'ஆகும்', 'ஆகிய', 'போன்ற', 'முதல்', 'வரை', 'சில', 'பல',
   }
   ```

4. **Configurable**: Every strategy must check `config.is_enabled('candidate_discovery.strategies.<name>')` before running. If disabled, return `[]`.

5. **Fail-soft**: If a strategy raises an exception, log a warning and continue with the other strategies.

6. **No NER dependency**: This module does NOT import spaCy, Stanza, or any NER library. It uses only rule-based heuristics and wordlists.

### STEP 4: CRITICAL TEST CASES

```python
# 1. Unknown entity in context
text = "நாளை செந்தமிழ்ஏஐ வெளியிடப்படுகிறது"
# Expected: செந்தமிழ்ஏஐ discovered as candidate

# 2. All common words — no candidates
text = "நான் பள்ளிக்கு சென்றேன்"
# Expected: candidate_entities = [] (all known words)

# 3. Multiple unknown words
text = "டெக்டமிழ் மற்றும் தமிழ்கோடர் புதிய தளங்கள்"
# Expected: டெக்டமிழ் and தமிழ்கோடர் both discovered

# 4. Module disabled
config['candidate_discovery']['enabled'] = False
# Expected: candidate_entities = []

# 5. Empty text
state['normalized_text'] = ""
# Expected: candidate_entities = []
```

### STEP 5: RUN ALL TESTS

```bash
# Unit tests
python -m pytest tests/unit/test_discovery/ -v

# Module test
python -m pytest tests/module/test_discovery_module.py -v
```

### FINAL CHECKLIST

- [ ] All 10 files in `modules/discovery/` created
- [ ] `__init__.py` exports `CandidateDiscoveryAgent`
- [ ] All 5 strategies implement `discover(words, text) → List[Dict]`
- [ ] Tamil wordlist loads from file with built-in fallback
- [ ] Candidate merger deduplicates and boosts multi-strategy candidates
- [ ] Agent respects `candidate_discovery.enabled` config flag
- [ ] Agent handles empty text gracefully
- [ ] Each strategy is individually toggleable
- [ ] All unit tests pass
- [ ] Module test passes
- [ ] No NER library imports (rule-based only)
