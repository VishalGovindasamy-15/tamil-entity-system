# Module 3: Transliteration & Normalization

## Purpose
Detect script types in the input text (Tamil, English, Roman Tamil) and convert Roman Tamil (Tanglish) to proper Tamil script. Uses **multiple configurable APIs** with consensus voting and stores learned mappings for faster future lookups.

---

## Data Contract

**Input:**
```python
state['raw_text']  # From Input module
```

**Output:**
```python
state['normalized_text']               # Text with Roman Tamil converted to Tamil script
state['detected_scripts']              # ['tamil', 'english', 'roman_tamil']
state['transliteration_map']           # {'naan': 'நான்', 'ponen': 'போனேன்'}
state['transliteration_confidence']    # {'naan': 0.95, 'ponen': 0.88}
```

---

## Files

### `modules/transliteration/__init__.py`
Exports: `TransliterationAgent`

---

### `modules/transliteration/agent.py` — TransliterationAgent

Main orchestrator for transliteration.

```python
class TransliterationAgent(BaseAgent):
    def __init__(self, db, config, vector_store):
        super().__init__("transliterator", "language", db, config)
        self.vector_store = vector_store
        self.script_detector = ScriptDetector()
        self.transliterators = self._load_transliterators()
        self.consensus = ConsensusEngine()
    
    def _load_transliterators(self) -> List:
        """Load enabled transliteration APIs sorted by priority"""
    
    async def execute(self, state: SystemState) -> SystemState:
        text = state['raw_text']
        
        # 1. Detect scripts
        scripts = self.script_detector.detect(text)
        state['detected_scripts'] = scripts
        
        if 'roman_tamil' not in scripts:
            state['normalized_text'] = text
            return state
        
        # 2. Process word by word
        words = text.split()
        result_words = []
        
        for word in words:
            if self.script_detector.is_roman_tamil(word):
                tamil_word = await self._transliterate_word(word, state)
                result_words.append(tamil_word)
                state['transliteration_map'][word] = tamil_word
            else:
                result_words.append(word)
        
        state['normalized_text'] = ' '.join(result_words)
        return state
    
    async def _transliterate_word(self, word: str, state) -> str:
        """Multi-step transliteration with caching"""
        
        # Step 1: Check SQLite cache
        cached = await self._check_db_cache(word)
        if cached:
            self.increment_cache_hits(state)
            state['transliteration_confidence'][word] = cached['confidence']
            return cached['tamil_word']
        
        # Step 2: Check ChromaDB for fuzzy match (handles typos)
        similar = await self._check_vector_similarity(word)
        if similar:
            self.increment_cache_hits(state)
            return similar['tamil_word']
        
        # Step 3: Query enabled transliteration APIs
        api_results = await self._query_apis(word, state)
        
        # Step 4: Consensus voting
        consensus = self.consensus.resolve(api_results)
        
        # Step 5: Store learned mapping
        await self._store_mapping(word, consensus, api_results)
        
        state['transliteration_confidence'][word] = consensus['confidence']
        return consensus['tamil_word']
```

**Tests (`tests/unit/test_transliteration/test_agent.py`):**
- Test pure Tamil text → no transliteration, passthrough
- Test pure English text → no transliteration
- Test Roman Tamil → correctly transliterated
- Test mixed (Tamil + Roman Tamil + English) → only Roman Tamil converted
- Test cache hit path (DB lookup)
- Test vector similarity path (fuzzy match)
- Test API path → consensus → store
- Test all APIs disabled → returns original word with warning

---

### `modules/transliteration/script_detector.py`

```python
class ScriptDetector:
    # Tamil Unicode range: U+0B80 to U+0BFF
    TAMIL_RANGE = (0x0B80, 0x0BFF)
    
    # Common English words to exclude from Roman Tamil detection
    ENGLISH_STOPWORDS = {'the', 'is', 'and', 'of', 'to', 'in', 'for', 'on', 'with', 'at', ...}
    
    # Tamil phonetic patterns in Roman script
    TAMIL_PATTERNS = ['aa', 'ee', 'oo', 'ai', 'au', 'zh', 'lla', 'nna', 'ndr', 'nth', ...]
    
    def detect(self, text: str) -> List[str]:
        """Detect all scripts present in text"""
        scripts = set()
        
        for char in text:
            if self.TAMIL_RANGE[0] <= ord(char) <= self.TAMIL_RANGE[1]:
                scripts.add('tamil')
            elif char.isalpha() and ord(char) < 128:
                scripts.add('english')
        
        # Check if 'english' text contains Roman Tamil patterns
        if 'english' in scripts:
            words = [w for w in text.split() if w.isalpha() and w.lower() not in self.ENGLISH_STOPWORDS]
            roman_tamil_count = sum(1 for w in words if self._has_tamil_pattern(w))
            if roman_tamil_count > 0:
                scripts.add('roman_tamil')
        
        return list(scripts)
    
    def is_roman_tamil(self, word: str) -> bool:
        """Check if a single word is likely Roman Tamil"""
        if not word.isalpha():
            return False
        if word.lower() in self.ENGLISH_STOPWORDS:
            return False
        return self._has_tamil_pattern(word)
    
    def _has_tamil_pattern(self, word: str) -> bool:
        """Check if word contains Tamil phonetic patterns"""
        lower = word.lower()
        return any(p in lower for p in self.TAMIL_PATTERNS)
```

**Tests (`tests/unit/test_transliteration/test_script_detector.py`):**
- Test pure Tamil detection
- Test pure English detection
- Test Roman Tamil detection (e.g., "naan", "vanakkam", "eppadi")
- Test mixed script detection
- Test English stopwords not flagged as Roman Tamil
- Test numbers and punctuation ignored
- Test edge cases: single character, empty string

---

### `modules/transliteration/transliterators.py`

Configurable transliteration API implementations.

```python
class GoogleTranslateTransliterator:
    """Uses Google Translate API for transliteration"""
    
    def __init__(self, config: Dict):
        self.enabled = config.get('enabled', True)
        self.priority = config.get('priority', 1)
    
    async def transliterate(self, word: str) -> Dict:
        from googletrans import Translator
        translator = Translator()
        result = translator.translate(word, src='en', dest='ta')
        return {
            'source': 'google_translate',
            'tamil_word': result.text,
            'confidence': 0.85
        }


class IndicTransliterator:
    """Uses indic-transliteration library (local, free)"""
    
    async def transliterate(self, word: str) -> Dict:
        from indic_transliteration import sanscript
        tamil = sanscript.transliterate(word, sanscript.ITRANS, sanscript.TAMIL)
        return {
            'source': 'indic_transliteration',
            'tamil_word': tamil,
            'confidence': 0.80
        }


class AI4BharatTransliterator:
    """Uses AI4Bharat IndicTrans API"""
    
    async def transliterate(self, word: str) -> Dict:
        # API call to AI4Bharat
        ...
```

**Config:**
```yaml
transliteration.apis.google_translate.enabled: true
transliteration.apis.google_translate.priority: 1
transliteration.apis.indic_transliteration.enabled: true
transliteration.apis.indic_transliteration.priority: 2
transliteration.apis.ai4bharat.enabled: false
transliteration.apis.ai4bharat.priority: 3
```

**Tests (`tests/unit/test_transliteration/test_transliterators.py`):**
- Test Google Translate (mocked for CI)
- Test Indic Transliteration (local, can run in CI)
- Test AI4Bharat (mocked)
- Test each returns correct format `{source, tamil_word, confidence}`
- Test disabled API skipped

---

### `modules/transliteration/consensus.py`

```python
class ConsensusEngine:
    def resolve(self, results: List[Dict]) -> Dict:
        """Find consensus among multiple transliteration results"""
        
        if not results:
            return {'tamil_word': '', 'confidence': 0.0, 'agreement_count': 0}
        
        # Group by result
        groups = {}
        for r in results:
            tamil = r['tamil_word']
            groups.setdefault(tamil, []).append(r)
        
        # Score each group: count * avg_confidence
        scored = {}
        for tamil, items in groups.items():
            avg_conf = sum(i['confidence'] for i in items) / len(items)
            scored[tamil] = {
                'tamil_word': tamil,
                'confidence': avg_conf,
                'agreement_count': len(items),
                'sources': [i['source'] for i in items]
            }
        
        # Pick highest scoring
        best = max(scored.values(), key=lambda x: (x['agreement_count'], x['confidence']))
        return best
```

**Tests (`tests/unit/test_transliteration/test_consensus.py`):**
- Test single result → returns it
- Test 3 results agreeing → high confidence
- Test 2 vs 1 disagreement → majority wins
- Test all different → highest confidence wins
- Test empty input → returns empty with 0 confidence

---

## Module-Level Test (`tests/module/test_transliteration_module.py`)

1. Pure Tamil text → passthrough, no API calls
2. "naan school ponen" → transliterates "naan" and "ponen" to Tamil, keeps "school"
3. Test caching: second call for same word hits DB cache
4. Test with all APIs disabled → returns original words
5. Test consensus with 2 APIs agreeing, 1 disagreeing
6. Test ChromaDB fuzzy match for typos (e.g., "naaan" → finds "naan" mapping)

---

## Dependencies

```
googletrans==4.0.0-rc1     # Google Translate (free)
indic-transliteration>=2.3 # Local transliteration library
# ai4bharat (optional)
```
