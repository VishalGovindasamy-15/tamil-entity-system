# Module 4: Entity Extraction

## Purpose
Extract named entities from normalized Tamil/English text using a **multi-model ensemble** approach. Models are configurable and toggleable. Includes entity merging, type normalization, context extraction, and abbreviation expansion.

---

## Data Contract

**Input:**
```python
state['normalized_text']  # From Transliteration module
```

**Output:**
```python
state['entities']  # List of entity dicts:
# [
#   {
#     "text": "அப்துல் கலாம்",
#     "type": "PERSON",
#     "confidence": 0.95,
#     "start": 0,
#     "end": 13,
#     "context": "...surrounding text...",
#     "sources": ["spacy", "stanza"],
#     "agreement_count": 2,
#     "expanded_form": null  # For abbreviations like ISRO
#   }
# ]
```

---

## Entity Type Taxonomy

| Type | Description | Examples |
|------|------------|---------|
| `PERSON` | People, deities, historical figures | அப்துல் கலாம், கிருஷ்ணா |
| `ORGANIZATION` | Companies, govt bodies, institutions | ISRO, TCS, IIT |
| `LOCATION` | Cities, countries, landmarks | சென்னை, இந்தியா |
| `DATE` | Dates, periods, festivals | 1947, தீபாவளி |
| `EVENT` | Historical events, ceremonies | சுதந்திரம் |
| `CONCEPT` | Technical terms, philosophical ideas | இயற்கணிதம் |
| `PRODUCT` | Brands, technologies | சந்திரயான் |
| `NATURAL` | Rivers, mountains | காவிரி, இமயமலை |
| `RELIGIOUS` | Temples, scriptures | மீனாட்சி கோவில் |
| `CULTURAL` | Art forms, traditions | பரதநாட்டியம் |
| `OTHER` | Unclassified entities | — |

---

## Files

### `modules/extraction/__init__.py`
Exports: `EntityExtractionAgent`

---

### `modules/extraction/agent.py` — EntityExtractionAgent

```python
class EntityExtractionAgent(BaseAgent):
    def __init__(self, db, config):
        super().__init__("entity_extractor", "ner", db, config)
        self.extractors = self._load_extractors()
        self.merger = EntityMerger()
        self.normalizer = EntityTypeNormalizer()
    
    def _load_extractors(self) -> List:
        """Load enabled NER extractors sorted by priority"""
        # Reads config: extraction.models.{name}.enabled and .priority
    
    async def execute(self, state: SystemState) -> SystemState:
        text = state['normalized_text']
        
        if not text or len(text.strip()) < 3:
            return state
        
        # 1. Run enabled extractors (primary ones in parallel)
        results = await self._extract_parallel(text, state)
        
        # 2. Check if LLM fallback needed
        avg_conf = self._avg_confidence(results)
        threshold = self.config.get('extraction.confidence_threshold', 0.85)
        
        if avg_conf < threshold and self.config.is_enabled('extraction.models.llm_fallback'):
            llm_result = await self.extractors['llm_fallback'].extract(text)
            results.append(llm_result)
        
        # 3. Merge overlapping entities across models
        merged = self.merger.merge(results)
        
        # 4. Enrich (context, abbreviation expansion)
        enriched = await self._enrich_entities(merged, text, state)
        
        state['entities'] = enriched
        return state
```

**Tests:**
- Test with simple Tamil text → entities extracted
- Test ensemble: spaCy + Stanza agree → high confidence
- Test LLM fallback triggered when primary models have low confidence
- Test no extractors enabled → returns empty list with warning
- Test deduplication of overlapping entities

---

### `modules/extraction/spacy_extractor.py`

```python
class SpacyExtractor:
    def __init__(self, config: Dict):
        self.enabled = config.get('enabled', True)
        self.model_name = config.get('model_name', 'xx_ent_wiki_sm')
        self.model = None
    
    async def initialize(self):
        import spacy
        self.model = spacy.load(self.model_name)
    
    async def extract(self, text: str) -> Dict:
        doc = self.model(text)
        entities = []
        for ent in doc.ents:
            entities.append({
                'text': ent.text,
                'type': ent.label_,
                'start': ent.start_char,
                'end': ent.end_char,
                'confidence': 0.85
            })
        return {'source': 'spacy', 'entities': entities, 'avg_confidence': 0.85}
```

**Tests:**
- Test extraction from English text
- Test extraction from Tamil text
- Test empty text
- Test model loading failure → graceful error

---

### `modules/extraction/stanza_extractor.py`

```python
class StanzaExtractor:
    def __init__(self, config: Dict):
        self.enabled = config.get('enabled', True)
        self.language = config.get('language', 'ta')
        self.pipeline = None
    
    async def initialize(self):
        import stanza
        stanza.download(self.language, processors='tokenize,ner')
        self.pipeline = stanza.Pipeline(self.language, processors='tokenize,ner')
    
    async def extract(self, text: str) -> Dict:
        doc = self.pipeline(text)
        entities = []
        for sentence in doc.sentences:
            for ent in sentence.ents:
                entities.append({
                    'text': ent.text,
                    'type': ent.type,
                    'start': ent.start_char,
                    'end': ent.end_char,
                    'confidence': 0.88
                })
        return {'source': 'stanza', 'entities': entities, 'avg_confidence': 0.88}
```

**Tests:**
- Test Tamil NER
- Test model download + pipeline creation
- Test entity type extraction

---

### `modules/extraction/cloud_extractor.py`

```python
class GoogleNLPExtractor:
    """Google Cloud Natural Language API for NER"""
    
    async def extract(self, text: str) -> Dict:
        from google.cloud import language_v1
        client = language_v1.LanguageServiceClient()
        document = language_v1.Document(content=text, type_=language_v1.Document.Type.PLAIN_TEXT)
        response = client.analyze_entities(request={'document': document})
        ...

class AzureNLPExtractor:
    """Azure Text Analytics for NER"""
    ...
```

**Tests:** (all mocked)
- Test Google NLP response parsing
- Test Azure response parsing
- Test API error handling

---

### `modules/extraction/llm_extractor.py`

```python
class LLMExtractor:
    """LLM-based entity extraction as fallback"""
    
    async def extract(self, text: str) -> Dict:
        prompt = """
        Extract all named entities from this Tamil/English text.
        Return JSON array:
        [{"text": "...", "type": "PERSON|ORGANIZATION|LOCATION|DATE|EVENT|CONCEPT|PRODUCT|OTHER",
          "start": int, "end": int, "confidence": 0.0-1.0, "reasoning": "..."}]
        
        Text: {text}
        
        Return ONLY valid JSON.
        """
        
        response = await self.llm.generate(prompt.format(text=text), temperature=0.1)
        entities = json.loads(response)
        return {'source': 'llm', 'entities': entities, 'avg_confidence': 0.75}
```

**Tests:**
- Test prompt construction
- Test JSON parsing of LLM response
- Test malformed JSON handling (retry logic)

---

### `modules/extraction/merger.py` — Entity Merge & Voting

```python
class EntityMerger:
    def merge(self, extraction_results: List[Dict]) -> List[Dict]:
        """Merge entities from multiple extractors"""
        
        # 1. Collect all entities with source tags
        all_entities = []
        for result in extraction_results:
            for entity in result['entities']:
                entity['_source'] = result['source']
                all_entities.append(entity)
        
        # 2. Group overlapping entities
        groups = self._group_overlapping(all_entities)
        
        # 3. For each group, vote on type and average confidence
        merged = []
        for group in groups:
            merged.append(self._resolve_group(group))
        
        return merged
    
    def _entities_overlap(self, e1, e2) -> bool:
        """Text match or position overlap"""
        if e1['text'].lower() == e2['text'].lower():
            return True
        if e1.get('start', -1) != -1 and e2.get('start', -1) != -1:
            return not (e1['end'] <= e2['start'] or e2['end'] <= e1['start'])
        return False
    
    def _resolve_group(self, group: List[Dict]) -> Dict:
        """Resolve a group of overlapping entities"""
        # Highest confidence entity as base
        base = max(group, key=lambda x: x.get('confidence', 0))
        
        # Type voting weighted by confidence
        type_votes = {}
        for e in group:
            t = e['type']
            type_votes[t] = type_votes.get(t, 0) + e.get('confidence', 0.5)
        
        best_type = max(type_votes, key=type_votes.get)
        avg_confidence = sum(e.get('confidence', 0.5) for e in group) / len(group)
        
        return {
            'text': base['text'],
            'type': best_type,
            'start': base.get('start', -1),
            'end': base.get('end', -1),
            'confidence': avg_confidence,
            'sources': list(set(e.get('_source', '') for e in group)),
            'agreement_count': len(group)
        }
```

**Tests:**
- Test exact text match merging
- Test position overlap merging
- Test type voting (2 say PERSON, 1 says ORG → PERSON wins)
- Test confidence averaging
- Test no overlap → entities stay separate

---

### `modules/extraction/normalizer.py`

```python
class EntityTypeNormalizer:
    MAPPING = {
        'PER': 'PERSON', 'PERSON': 'PERSON',
        'ORG': 'ORGANIZATION', 'ORGANIZATION': 'ORGANIZATION', 'COMPANY': 'ORGANIZATION',
        'GPE': 'LOCATION', 'LOC': 'LOCATION', 'LOCATION': 'LOCATION',
        'PLACE': 'LOCATION', 'CITY': 'LOCATION', 'COUNTRY': 'LOCATION',
        'DATE': 'DATE', 'TIME': 'TIME',
        'EVENT': 'EVENT',
        'PRODUCT': 'PRODUCT',
        'WORK_OF_ART': 'CULTURAL',
    }
    
    def normalize(self, label: str) -> str:
        return self.MAPPING.get(label.upper(), 'OTHER')
```

**Tests:**
- Test all known mappings
- Test unknown label → 'OTHER'
- Test case insensitivity

---

## Module-Level Test (`tests/module/test_extraction_module.py`)

1. Tamil text with known entities → all extracted correctly
2. Mixed Tamil-English text → entities from both languages
3. Ensemble: spaCy + Stanza → merged, higher confidence
4. LLM fallback: spaCy finds nothing → LLM finds entities
5. All models disabled → empty list, no crash
6. Abbreviation: "ISRO (Indian Space Research Organisation)" → expanded
7. Context extraction: entity surrounded by text → context captured

---

## Dependencies

```
spacy>=3.7.0             # NER model
xx_ent_wiki_sm           # spaCy multilingual model (python -m spacy download xx_ent_wiki_sm)
stanza>=1.7.0            # Tamil NER
# google-cloud-language  # Optional
# azure-ai-textanalytics # Optional
```
