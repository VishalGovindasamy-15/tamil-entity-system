# Module 5: Entity Research

## Purpose
Deep research for each extracted entity using **tiered multi-source queries**. This is the **core intelligence** of the system. Each source is toggleable. Includes knowledge base caching, conflict resolution, source credibility tracking, and custom source plugin support.

---

## Data Contract

**Input:**
```python
state['entities']  # From Extraction module
# [{"text": "அப்துல் கலாம்", "type": "PERSON", "confidence": 0.95, ...}]
```

**Output:**
```python
state['entity_knowledge']  # Dict keyed by entity text
# {
#   "அப்துல் கலாம்": {
#     "entity_name": "அப்துல் கலாம்",
#     "entity_type": "PERSON",
#     "verified_facts": {
#       "full_name": {"value": "...", "confidence": 0.99, "sources": [...], "status": "verified"},
#       "birth_date": {"value": "1931-10-15", "confidence": 0.98, ...}
#     },
#     "sources_consulted": [{"type": "wikipedia", "url": "...", "credibility": 0.95, ...}],
#     "overall_confidence": 0.96,
#     "fact_count": 12,
#     "source_count": 5
#   }
# }
```

---

## Research Strategy

```
For each entity:
1. Check SQLite knowledge base → if fresh, return cached (FAST PATH)
2. Query Tier 1 sources (always, parallel)
3. Calculate confidence → if >= 0.90, STOP
4. Query Tier 2 sources (parallel)
5. Calculate confidence → if >= 0.85, STOP
6. Query Tier 3 sources (selective based on entity type)
7. Fallback to Tier 4 (LLM) if still insufficient
8. Synthesize: merge facts, resolve conflicts, calculate confidence
9. Store in knowledge base for future cache hits
```

---

## Files

### `modules/research/__init__.py`
Exports: `EntityResearchAgent`

---

### `modules/research/agent.py` — EntityResearchAgent

```python
class EntityResearchAgent(BaseAgent):
    def __init__(self, db, config, vector_store):
        super().__init__("entity_researcher", "research", db, config)
        self.sources = self._load_sources()
        self.synthesizer = InformationSynthesizer()
        self.plugin_manager = SourcePluginManager(db, config)
    
    def _load_sources(self) -> Dict[str, BaseSourcePlugin]:
        """Load enabled research sources from config"""
        # Config keys: research.sources.{name}.enabled, .tier, .credibility
    
    async def execute(self, state: SystemState) -> SystemState:
        entities = state['entities']
        
        # Research all entities in parallel
        tasks = [self.research_entity(e, state) for e in entities]
        results = await asyncio.gather(*tasks)
        
        for entity, result in zip(entities, results):
            state['entity_knowledge'][entity['text']] = result
        
        return state
    
    async def research_entity(self, entity, state) -> Dict:
        # 1. Check cache
        cached = await self._check_cache(entity['text'], entity['type'])
        if cached and self._is_fresh(cached, entity['type']):
            self.increment_cache_hits(state)
            await self._increment_search_count(cached['id'])
            return cached
        
        # 2. Tiered research
        all_results = {}
        
        # Tier 1 (always)
        tier1 = self._get_enabled_sources(tier=1)
        tier1_results = await self._query_sources(tier1, entity, state)
        all_results.update(tier1_results)
        
        conf = self.synthesizer.calculate_confidence(list(all_results.values()))
        
        # Tier 2 (if needed)
        if conf < self.config.get('research.confidence_threshold', 0.85):
            tier2 = self._get_enabled_sources(tier=2)
            tier2_results = await self._query_sources(tier2, entity, state)
            all_results.update(tier2_results)
            conf = self.synthesizer.calculate_confidence(list(all_results.values()))
        
        # Tier 3 (if still needed, selective)
        if conf < 0.75:
            tier3 = self._get_relevant_tier3(entity['type'])
            tier3_results = await self._query_sources(tier3, entity, state)
            all_results.update(tier3_results)
        
        # Tier 4 (LLM fallback)
        if conf < 0.60 and self.config.is_enabled('research.sources.llm_knowledge'):
            llm_result = await self._query_llm(entity, state)
            all_results['llm'] = llm_result
        
        # Custom sources
        custom_results = await self.plugin_manager.query_all(entity['text'], entity['type'])
        all_results.update(custom_results)
        
        # 3. Synthesize
        synthesized = await self.synthesizer.synthesize(entity['text'], entity['type'], all_results)
        
        # 4. Store
        await self._store_knowledge(entity['text'], entity['type'], synthesized)
        
        state['sources_accessed'] += len(all_results)
        return synthesized
    
    def _is_fresh(self, cached, entity_type) -> bool:
        """Freshness depends on entity type"""
        freshness_days = {
            'PERSON': 30, 'ORGANIZATION': 7, 'LOCATION': 14,
            'EVENT': 1, 'DATE': 365, 'OTHER': 7
        }
        max_age = freshness_days.get(entity_type, 7)
        age = (datetime.now() - cached['last_updated']).days
        return age < max_age
```

**Tests:**
- Test cache hit path (fresh entity → returns cached)
- Test cache miss → full research pipeline
- Test stale cache → re-research
- Test tiered escalation (Tier 1 insufficient → Tier 2 triggered)
- Test all sources disabled → LLM fallback
- Test parallel entity research (3 entities at once)

---

### `modules/research/sources/wikipedia.py`

```python
class WikipediaSource(BaseSourcePlugin):
    """Wikipedia API for Tamil + English articles"""
    
    async def search(self, entity_name, entity_type, context=None) -> SourceResult:
        import httpx
        
        facts = {}
        
        # Query Tamil Wikipedia
        ta_data = await self._query_wiki(entity_name, lang='ta')
        if ta_data:
            facts['description_ta'] = ta_data.get('extract', '')
            facts.update(self._parse_infobox(ta_data))
        
        # Query English Wikipedia
        en_data = await self._query_wiki(entity_name, lang='en')
        if en_data:
            facts['description_en'] = en_data.get('extract', '')
            facts.update(self._parse_infobox(en_data))
        
        return SourceResult(
            success=bool(facts),
            entity_found=bool(facts),
            facts=facts,
            source_name='wikipedia',
            source_url=f"https://en.wikipedia.org/wiki/{entity_name}",
            source_credibility=0.95,
            confidence=0.90 if facts else 0.0
        )
    
    async def _query_wiki(self, title, lang='en') -> Optional[Dict]:
        """Query Wikipedia REST API"""
        url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{title}"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                return resp.json()
        return None
```

**Tests:**
- Test Tamil Wikipedia query (mocked)
- Test English Wikipedia query (mocked)
- Test entity not found → empty facts
- Test infobox parsing

---

### `modules/research/sources/wikidata.py`

```python
class WikidataSource(BaseSourcePlugin):
    """Wikidata SPARQL queries for structured facts"""
    
    SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
    
    async def search(self, entity_name, entity_type, context=None) -> SourceResult:
        # 1. Search for entity by label
        entity_id = await self._find_entity(entity_name)
        if not entity_id:
            return SourceResult(success=False, source_name='wikidata')
        
        # 2. Query structured facts
        facts = await self._get_entity_facts(entity_id)
        
        return SourceResult(
            success=True,
            entity_found=True,
            facts=facts,
            source_name='wikidata',
            source_url=f"https://www.wikidata.org/wiki/{entity_id}",
            source_credibility=0.98,
            confidence=0.95
        )
    
    async def _get_entity_facts(self, entity_id: str) -> Dict:
        """SPARQL query for common properties"""
        query = f"""
        SELECT ?property ?value WHERE {{
            wd:{entity_id} ?property ?value .
        }} LIMIT 50
        """
        # Parse results into fact dict
```

**Tests:**
- Test entity search by label
- Test SPARQL query
- Test property-to-fact mapping (birth_date, occupation, etc.)

---

### `modules/research/sources/dbpedia.py`

```python
class DBpediaSource(BaseSourcePlugin):
    """DBpedia for RDF-based knowledge"""
    
    async def search(self, entity_name, entity_type, context=None) -> SourceResult:
        url = f"https://dbpedia.org/data/{entity_name.replace(' ', '_')}.json"
        ...
```

---

### `modules/research/sources/web_search.py`

```python
class WebSearchSource(BaseSourcePlugin):
    """Web search via DuckDuckGo (free) or Google Custom Search"""
    
    async def search(self, entity_name, entity_type, context=None) -> SourceResult:
        engine = self.config.get('engine', 'duckduckgo')
        
        if engine == 'duckduckgo':
            return await self._search_ddg(entity_name)
        elif engine == 'google':
            return await self._search_google(entity_name)
```

---

### `modules/research/sources/` — Other Sources

Each follows the same pattern — implements `BaseSourcePlugin.search()`:
- `google_kg.py` — Google Knowledge Graph API
- `news.py` — NewsAPI / GNews
- `youtube.py` — YouTube transcript search
- `tamil_sources.py` — Tamil Virtual Academy, Project Madurai
- `government.py` — TN/India gov portals
- `academic.py` — Google Scholar
- `llm_source.py` — Ask LLM for structured facts about entity

---

### `modules/research/synthesizer.py` — Fact Aggregation & Conflict Resolution

```python
class InformationSynthesizer:
    async def synthesize(self, entity_name, entity_type, source_results) -> Dict:
        """Aggregate facts from all sources, resolve conflicts"""
        
        # 1. Collect all facts grouped by fact_key
        all_facts = self._collect_facts(source_results)
        
        # 2. Resolve each fact
        verified_facts = {}
        for fact_key, instances in all_facts.items():
            verified_facts[fact_key] = self._resolve_conflict(fact_key, instances)
        
        # 3. Build sources consulted list
        sources_consulted = self._build_sources_list(source_results)
        
        # 4. Calculate overall confidence
        overall_confidence = self._calculate_overall_confidence(verified_facts)
        
        return {
            'entity_name': entity_name,
            'entity_type': entity_type,
            'verified_facts': verified_facts,
            'sources_consulted': sources_consulted,
            'overall_confidence': overall_confidence,
            'fact_count': len(verified_facts),
            'source_count': len(sources_consulted)
        }
    
    def _resolve_conflict(self, fact_key, instances) -> Dict:
        """
        Conflict resolution:
        1. Group by value
        2. Weight by source credibility
        3. Count agreement
        4. If close scores → mark 'uncertain'
        5. If clear winner → mark 'verified'
        """
        ...
    
    def calculate_confidence(self, results) -> float:
        """Calculate combined confidence from source results (used for tier decisions)"""
        ...
```

**Tests (`tests/unit/test_research/test_synthesizer.py`):**
- Test all sources agree → verified, high confidence
- Test 2 vs 1 disagreement → majority wins
- Test close scores → marked uncertain with alternatives
- Test single source → lower confidence
- Test empty sources → 0 confidence
- Test overall confidence calculation

---

### `modules/research/plugin_manager.py` — Custom Source Manager

```python
class SourcePluginManager:
    """Manages custom user-defined sources from DB"""
    
    async def initialize(self):
        """Load custom sources from custom_sources table"""
    
    async def query_all(self, entity_name, entity_type) -> Dict[str, SourceResult]:
        """Query all relevant custom sources in parallel"""
    
    async def register_plugin(self, config, plugin_config) -> bool:
        """Register new custom source (API, web scraper, or database)"""
    
    async def remove_plugin(self, source_name) -> bool
    async def health_check_all(self) -> Dict[str, bool]
    async def get_plugin_stats(self) -> Dict[str, Any]
```

Supports 3 plugin types:
- **Custom API** — configurable endpoint, headers, body template, response parser
- **Custom Web Scraper** — URL template, CSS selectors
- **Custom Database** — connection string, query template, field mapping

**Tests:**
- Test plugin loading from DB
- Test custom API query (mocked)
- Test custom scraper (mocked)
- Test plugin registration via API
- Test plugin removal + deactivation

---

## Module-Level Test (`tests/module/test_research_module.py`)

1. Known entity (e.g., "India") → Wikipedia + Wikidata find it → verified facts
2. Unknown entity → all sources return nothing → low confidence
3. Cache hit → second request for same entity → uses cache, no API calls
4. Conflict resolution → sources disagree on a fact → consensus picks winner
5. Tiered escalation → Tier 1 finds nothing → Tier 2 queried
6. All sources disabled → returns empty knowledge with warning
7. Custom source registered → included in research pipeline

---

## Dependencies

```
httpx>=0.25.0             # HTTP client for all API calls
SPARQLWrapper>=2.0.0      # Wikidata SPARQL queries
beautifulsoup4>=4.12.0    # Web scraping
duckduckgo-search>=4.0    # Free web search
# google-api-python-client  # Optional: Google KG, Custom Search
# newsapi-python            # Optional: News API
# youtube-transcript-api    # Optional: YouTube
```
