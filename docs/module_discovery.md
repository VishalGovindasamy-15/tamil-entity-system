# Module 3b: Candidate Entity Discovery

## Purpose
Discovers **unknown/novel Tamil entities** that traditional NER models miss. Sits between Transliteration and Extraction in the pipeline. Catches newly coined terms, compound words, and entities with no capitalization signal.

> [!IMPORTANT]
> This module is **fully optional**. When disabled, `candidate_entities` stays `[]` and the pipeline works exactly as before.

---

## Problem Solved

Traditional NER (spaCy, Stanza, Cloud) is trained on existing data. It **cannot** discover:
- Newly coined Tamil terms (`செந்தமிழ்ஏஐ`)
- Brand names with no training data
- Compound words fusing known morphemes
- Entities with zero contextual capitalization

**Example:**
```
நாளை செந்தமிழ்ஏஐ வெளியிடப்படுகிறது
```
Every NER model skips `செந்தமிழ்ஏஐ`. This module catches it.

---

## Pipeline Position

```
Input → Transliteration → [Candidate Discovery] → Extraction → Research → ...
```

- **Reads:** `state['normalized_text']`
- **Writes:** `state['candidate_entities']` (NEW field)
- **Extraction merger** combines NER entities + candidate entities

---

## Data Contract

**Input (from Transliteration):**
```python
state['normalized_text']  # Tamil/English text
```

**Output (new field):**
```python
state['candidate_entities']  # List of candidate dicts
# [
#   {
#     "text": "செந்தமிழ்ஏஐ",
#     "candidate_type": "UNKNOWN",
#     "discovery_methods": ["dictionary_mismatch", "compound_word"],
#     "confidence": 0.55,
#     "start": 5,
#     "end": 16,
#     "context": "நாளை செந்தமிழ்ஏஐ வெளியிடப்படுகிறது",
#     "reason": "Word not found in Tamil dictionary; compound structure detected"
#   }
# ]
```

---

## Files

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

---

## Configuration

```yaml
# Add to default_config.yaml
candidate_discovery:
  enabled: true
  min_confidence: 0.4           # Below this, discard candidate
  max_candidates_per_text: 20   # Safety cap
  strategies:
    dictionary_mismatch:
      enabled: true
      priority: 1
      wordlist_path: "data/tamil_wordlist.txt"  # Optional custom path
    compound_detection:
      enabled: true
      priority: 2
      min_length: 4              # Tamil chars minimum
    rare_word:
      enabled: true
      priority: 3
      min_word_length: 3         # Skip very short words
    noun_phrase:
      enabled: true
      priority: 4
    context_pattern:
      enabled: true
      priority: 5
```

---

## Strategy Specifications

### 1. `DictionaryMismatchStrategy`

Checks each word against a Tamil wordlist. Words NOT in the dictionary are candidates.

```python
class DictionaryMismatchStrategy:
    def __init__(self, config, wordlist):
        self.wordlist = wordlist  # Set of known Tamil words

    async def discover(self, words: List[str], text: str) -> List[Dict]:
        candidates = []
        for word in words:
            if self._is_tamil_word(word) and word not in self.wordlist:
                if not self._is_stopword(word) and len(word) >= self.min_length:
                    candidates.append({
                        "text": word,
                        "method": "dictionary_mismatch",
                        "confidence": 0.5,
                        "reason": "Word not found in Tamil dictionary"
                    })
        return candidates
```

**Wordlist source:** Bundle a basic Tamil wordlist (~30K-50K common words). Can be sourced from open datasets (Wiktionary Tamil dump, IIIT Hyderabad wordlist, or a simple frequency list).

**Exclusions:**
- Tamil stopwords (இது, அது, ஒரு, என், etc.)
- Numbers and punctuation
- Words < 2 Tamil characters
- English words (already handled by script detection)

---

### 2. `CompoundWordStrategy`

Detects unusually long or compound Tamil words that might be coined terms.

```python
class CompoundWordStrategy:
    TAMIL_CHAR_RANGE = range(0x0B80, 0x0BFF + 1)

    def _tamil_char_count(self, word: str) -> int:
        return sum(1 for c in word if ord(c) in self.TAMIL_CHAR_RANGE)

    async def discover(self, words: List[str], text: str) -> List[Dict]:
        candidates = []
        for word in words:
            tc = self._tamil_char_count(word)
            if tc >= self.min_length:
                # Check for mixed-script compounds (Tamil + English like செந்தமிழ்ஏஐ)
                has_mixed = self._has_mixed_morphemes(word)
                if tc > 8 or has_mixed:
                    candidates.append({
                        "text": word,
                        "method": "compound_word",
                        "confidence": 0.45 if not has_mixed else 0.6,
                        "reason": f"Compound word detected (length={tc}, mixed={has_mixed})"
                    })
        return candidates
```

---

### 3. `RareWordStrategy`

Frequency-based: words that appear in the text but are uncommon.

```python
async def discover(self, words: List[str], text: str) -> List[Dict]:
    # Count frequency of each unique Tamil word
    freq = Counter(w for w in words if self._is_tamil(w))
    total = sum(freq.values())

    candidates = []
    for word, count in freq.items():
        ratio = count / total
        # Words that appear but aren't super common
        if 0.01 < ratio < 0.15 and len(word) >= self.min_length:
            candidates.append({
                "text": word,
                "method": "rare_word",
                "confidence": 0.35,
                "reason": f"Appears {count} times ({ratio:.2%} frequency)"
            })
    return candidates
```

---

### 4. `NounPhraseStrategy`

Uses Tamil grammatical patterns to find likely entity positions.

**Tamil entity signals:**
- Word before a **case suffix** (`-ஐ`, `-ை`, `-க்கு`, `-ல்`, `-இல்`, `-ின்`, `-உடன்`)
- Word before an **action verb** (`வெளியிடப்படுகிறது`, `தொடங்கியது`, `நிறுவப்பட்டது`)
- Word after **demonstratives** (`இந்த`, `அந்த`, `எந்த`)
- Word after **honorifics/titles** context

```python
CASE_SUFFIXES = ['ஐ', 'ை', 'க்கு', 'ல்', 'இல்', 'ின்', 'உடன்', 'ால்']
VERB_PATTERNS = ['படுகிறது', 'பட்டது', 'கிறது', 'கிறார்', 'ஆர்', 'ஆன']
DEMONSTRATIVES = ['இந்த', 'அந்த', 'எந்த', 'இது', 'அது']
```

---

### 5. `ContextPatternStrategy`

Detects entities by surrounding context patterns.

**Patterns:**
- `X வெளியிடப்படுகிறது` → X is being released (X = likely product/entity)
- `X நிறுவனம்` → X organization
- `X நிறுவனர்` → X founder (preceding word = person)
- `X என்ற` → "called X" (entity name)

---

## `CandidateDiscoveryAgent`

```python
class CandidateDiscoveryAgent(BaseAgent):
    """Discovers candidate entities using multiple strategies."""

    async def execute(self, state: SystemState) -> SystemState:
        if not self.config.is_enabled('candidate_discovery'):
            state['candidate_entities'] = []
            return state

        text = state['normalized_text']
        if not text.strip():
            state['candidate_entities'] = []
            return state

        words = self._tokenize(text)
        all_candidates = []

        # Run enabled strategies
        for strategy in self._get_enabled_strategies():
            try:
                candidates = await strategy.discover(words, text)
                all_candidates.extend(candidates)
            except Exception as e:
                self.log_warning(state, f"Strategy {strategy.name} failed: {e}")

        # Deduplicate and score
        merged = self.merger.merge(all_candidates, text)

        # Apply confidence threshold
        min_conf = self.config.get('candidate_discovery.min_confidence', 0.4)
        filtered = [c for c in merged if c['confidence'] >= min_conf]

        # Cap max candidates
        max_candidates = self.config.get('candidate_discovery.max_candidates_per_text', 20)
        filtered = sorted(filtered, key=lambda c: c['confidence'], reverse=True)[:max_candidates]

        state['candidate_entities'] = filtered
        self.log_step(state, f"Discovered {len(filtered)} candidate entities")
        return state
```

---

## `CandidateMerger`

Deduplicates candidates found by multiple strategies.

```python
class CandidateMerger:
    def merge(self, candidates: List[Dict], text: str) -> List[Dict]:
        # Group by text
        groups = defaultdict(list)
        for c in candidates:
            groups[c['text']].append(c)

        merged = []
        for entity_text, group in groups.items():
            methods = list(set(c['method'] for c in group))
            # More methods agreeing = higher confidence
            base_conf = max(c['confidence'] for c in group)
            bonus = min(0.2, 0.05 * (len(methods) - 1))
            merged.append({
                "text": entity_text,
                "candidate_type": "UNKNOWN",
                "discovery_methods": methods,
                "confidence": min(0.8, base_conf + bonus),
                "start": text.find(entity_text),
                "end": text.find(entity_text) + len(entity_text) if entity_text in text else -1,
                "context": self._extract_context(text, entity_text),
                "reason": "; ".join(c.get('reason', '') for c in group)
            })
        return merged
```

---

## Integration Points (NO existing code changes needed at build time)

| Component | What Changes | When |
|-----------|-------------|------|
| `core/state.py` | Add `candidate_entities: List[Dict]` field + default `[]` | During integration (prompt 10) |
| `default_config.yaml` | Append `candidate_discovery` section | During integration (prompt 10) |
| `extraction/merger.py` | Accept `state['candidate_entities']` as extra input | During integration (prompt 10) |
| `pipeline/orchestrator.py` | Add Discovery stage between Transliteration and Extraction | During integration (prompt 10) |

> [!NOTE]
> All integration changes happen in **prompt 10 (integration)**. Each module is built independently. The Discovery module reads `normalized_text` and writes `candidate_entities`. The Extraction module's merger simply checks if `candidate_entities` exists and merges them in.

---

## Tamil Wordlist (`tamil_wordlist.py`)

```python
class TamilWordlist:
    """Loads and manages a Tamil word dictionary."""

    def __init__(self, wordlist_path: str = None):
        self._words: Set[str] = set()
        self._load(wordlist_path)

    def _load(self, path):
        if path and os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                self._words = {line.strip() for line in f if line.strip()}
        else:
            # Use built-in minimal wordlist
            self._words = self._builtin_wordlist()

    def _builtin_wordlist(self) -> Set[str]:
        """~500 most common Tamil words as fallback."""
        # Common verbs, nouns, adjectives, function words
        return {
            'இது', 'அது', 'ஒரு', 'என்', 'நான்', 'நீ', 'அவன்', 'அவள்',
            'அவர்', 'நாம்', 'வந்து', 'போய்', 'சென்று', 'இருக்கிறது',
            'செய்து', 'கொண்டு', 'பெரிய', 'சிறிய', 'நல்ல', 'புதிய',
            # ... expand to ~500 words
        }

    def contains(self, word: str) -> bool:
        return word in self._words

    def __contains__(self, word: str) -> bool:
        return self.contains(word)
```

> [!TIP]
> For better coverage, download a Tamil wordlist file and place it at `data/tamil_wordlist.txt`. The built-in list is a minimal fallback (~500 words). Open-source Tamil wordlists with 30K+ words are available from Wiktionary dumps and IIIT Hyderabad.

---

## Tests

### Unit Tests

| Test File | What It Tests |
|-----------|---------------|
| `test_dictionary_checker.py` | Known word → not candidate. Unknown word → candidate. Stopwords excluded. |
| `test_compound_detector.py` | Short words → skip. Long compound → candidate. Mixed-script → higher confidence. |
| `test_rare_word.py` | Very common → skip. Moderate frequency → candidate. |
| `test_noun_phrase.py` | Word before case suffix → candidate. Word after demonstrative → candidate. |
| `test_context_pattern.py` | "X வெளியிடப்படுகிறது" → X is candidate. |
| `test_candidate_merger.py` | Same word from 2 strategies → merged, confidence boosted. |
| `test_agent.py` | Full flow: text → strategies → merged candidates. Module disabled → empty list. |

### Module Test

```python
async def test_discovery_finds_unknown_entity():
    """செந்தமிழ்ஏஐ should be discovered as a candidate entity."""
    text = "நாளை செந்தமிழ்ஏஐ வெளியிடப்படுகிறது"
    # Run agent...
    candidates = state['candidate_entities']
    assert any(c['text'] == 'செந்தமிழ்ஏஐ' for c in candidates)

async def test_known_words_not_candidates():
    """Common Tamil words should NOT be flagged."""
    text = "நான் பள்ளிக்கு சென்றேன்"
    # Run agent...
    candidates = state['candidate_entities']
    assert len(candidates) == 0  # All words are common

async def test_module_disabled_returns_empty():
    """When candidate_discovery.enabled = false, return empty list."""
    # Disable in config...
    assert state['candidate_entities'] == []
```

---

## Dependencies

No new pip dependencies required. All strategies use:
- Python built-in `re`, `collections.Counter`
- Tamil Unicode range checks (same as script_detector)
- Optional: plain text wordlist file
