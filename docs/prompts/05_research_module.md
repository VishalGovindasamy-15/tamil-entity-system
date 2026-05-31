# PROMPT: Build Entity Research Module

## Context Files (Attach These)

Upload/attach these files before pasting this prompt:
1. `implementation_plan.md` — The master architecture document
2. `module_research.md` — Detailed spec for this module

Also make sure the **Core module code** already exists in the workspace at `tamil-entity-system/backend/core/` and `tamil-entity-system/backend/config/`.

---

## Prompt (Paste Everything Below)

---

You are building the **Entity Research Module** for a Tamil Entity Recognition system. This is the **most complex module** — it queries multiple research sources in tiers, synthesizes facts, resolves conflicts, and manages a knowledge cache.

### STEP 0: READ AND UNDERSTAND

1. Read **`implementation_plan.md`** — Focus on SystemState, SourceResult contract, research config section, and data flow.
2. Read **`module_research.md`** — Your complete spec with tiered strategy, source implementations, and synthesizer.
3. Read the **existing core module code**:
   - `backend/core/base_agent.py` — EntityResearchAgent extends BaseAgent
   - `backend/core/base_source.py` — All sources extend BaseSourcePlugin
   - `backend/core/contracts.py` — SourceResult, SourceConfig dataclasses
   - `backend/core/database.py` — For SQLite caching (entity_knowledge, source_credibility tables)
   - `backend/core/database.py` (VectorStore) — For ChromaDB embedding search
   - `backend/core/llm_client.py` — For LLM knowledge source
   - `backend/config/default_config.yaml` — research.sources section

### YOUR DATA CONTRACT

**What you receive (set by Extraction module):**
```python
state['entities']  # List of entity dicts
# [{"text": "அப்துல் கலாம்", "type": "PERSON", "confidence": 0.95, ...}]
```

**What you MUST set:**
```python
state['entity_knowledge']  # Dict keyed by entity text:
# {
#   "அப்துல் கலாம்": {
#     "entity_name": "அப்துல் கலாம்",
#     "entity_type": "PERSON",
#     "verified_facts": {
#       "full_name": {"value": "...", "confidence": 0.99, "sources": ["wikipedia", "wikidata"], "status": "verified"},
#       "birth_date": {"value": "1931-10-15", "confidence": 0.98, "sources": [...], "status": "verified"}
#     },
#     "sources_consulted": [{"type": "wikipedia", "url": "...", "credibility": 0.95}],
#     "overall_confidence": 0.96,
#     "fact_count": 12,
#     "source_count": 5
#   }
# }
state['sources_accessed']  # Increment by number of sources queried
```

**Who reads your output:** The Explanation module reads `state['entity_knowledge']` to generate explanations.

### TIERED RESEARCH STRATEGY

```
For each entity:
1. Check SQLite entity_knowledge table → if fresh cache exists, return it (FAST PATH)
2. Query Tier 1 sources (Wikipedia, Wikidata, DBpedia) — ALWAYS, in parallel
3. Calculate confidence → if >= 0.90, STOP (enough data)
4. Query Tier 2 sources (Google KG, Web Search, News) — in parallel
5. Calculate confidence → if >= 0.85, STOP
6. Query Tier 3 sources (YouTube, Tamil sources, Government, Academic) — selective by entity type
7. If confidence still < 0.60, query Tier 4 (LLM knowledge) — last resort
8. Synthesize: merge facts from all sources, resolve conflicts
9. Store result in entity_knowledge table for future cache hits
```

### FILES TO CREATE

```
backend/modules/research/
├── __init__.py
├── agent.py                 # EntityResearchAgent — tiered orchestrator
├── sources/
│   ├── __init__.py
│   ├── wikipedia.py         # WikipediaSource — Tamil + English Wikipedia REST API
│   ├── wikidata.py          # WikidataSource — SPARQL queries for structured facts
│   ├── dbpedia.py           # DBpediaSource — RDF-based knowledge
│   ├── google_kg.py         # GoogleKGSource — Google Knowledge Graph API
│   ├── web_search.py        # WebSearchSource — DuckDuckGo (free) or Google Custom Search
│   ├── news.py              # NewsSource — NewsAPI or GNews
│   ├── youtube.py           # YouTubeSource — transcript search
│   ├── tamil_sources.py     # TamilSource — Tamil Virtual Academy, Project Madurai
│   ├── government.py        # GovernmentSource — TN/India gov portals
│   ├── academic.py          # AcademicSource — Google Scholar
│   └── llm_source.py        # LLMSource — Ask LLM for structured facts
├── synthesizer.py           # InformationSynthesizer — fact aggregation & conflict resolution
└── plugin_manager.py        # SourcePluginManager — custom source registration

backend/tests/unit/test_research/
├── __init__.py
├── test_agent.py
├── test_wikipedia.py
├── test_wikidata.py
├── test_dbpedia.py
├── test_google_kg.py
├── test_web_search.py
├── test_news.py
├── test_youtube.py
├── test_tamil_sources.py
├── test_government.py
├── test_academic.py
├── test_llm_source.py
├── test_synthesizer.py
└── test_plugin_manager.py

backend/tests/module/
└── test_research_module.py
```

### IMPLEMENTATION RULES

1. **Every source extends `BaseSourcePlugin`** from `core/base_source.py`. Each must implement:
   - `async def search(self, entity_name, entity_type, context=None) -> SourceResult`
   - `async def health_check(self) -> bool`
   - Return a `SourceResult` (from `core/contracts.py`)

2. **EntityResearchAgent** must:
   - Research all entities in parallel: `asyncio.gather(*[self.research_entity(e, state) for e in entities])`
   - For each entity, follow the tiered strategy above
   - Check config for each source: `self.config.is_enabled('research.sources.wikipedia')`
   - Respect timeouts from config: `research.source_timeout_seconds`

3. **Cache freshness depends on entity type:**
   ```python
   FRESHNESS_DAYS = {
       'PERSON': 30, 'ORGANIZATION': 7, 'LOCATION': 14,
       'EVENT': 1, 'DATE': 365, 'OTHER': 7
   }
   ```

4. **WikipediaSource** must query BOTH Tamil (ta.wikipedia.org) and English (en.wikipedia.org) using the REST API:
   ```
   https://{lang}.wikipedia.org/api/rest_v1/page/summary/{title}
   ```

5. **WikidataSource** must use SPARQL via the Wikidata Query Service:
   ```
   https://query.wikidata.org/sparql
   ```

6. **WebSearchSource** must support DuckDuckGo (default, free) and Google Custom Search (optional).

7. **InformationSynthesizer** conflict resolution:
   - Group facts by `fact_key` (e.g., "birth_date")
   - If all sources agree → `status: "verified"`, high confidence
   - If majority agrees → `status: "verified"`, pick majority value
   - If close split → `status: "uncertain"`, include alternatives
   - Weight by source credibility (from config + `source_credibility` table)

8. **SourcePluginManager** manages custom user-defined sources (stored in `custom_sources` DB table). Supports 3 types: Custom API, Custom Web Scraper, Custom Database.

9. **All HTTP calls use `httpx.AsyncClient`** with timeout handling.

### TESTING RULES

1. **Mock ALL HTTP calls** — Wikipedia, Wikidata, web search, etc.
2. **Test tiered escalation** — Tier 1 returns nothing → Tier 2 triggered
3. **Test cache hit** — second call returns cached, no API calls
4. **Test conflict resolution** — sources disagree, synthesizer picks correct winner
5. **Test all sources disabled** → empty knowledge with warning
6. Run:
   ```bash
   cd tamil-entity-system/backend
   pytest tests/unit/test_research/ -v
   pytest tests/module/test_research_module.py -v
   ```

### FINAL CHECKLIST

- [ ] All 11 source files created (wikipedia through llm_source)
- [ ] Each source returns proper SourceResult
- [ ] Tiered escalation works (Tier 1 → 2 → 3 → 4)
- [ ] Cache hit returns stored data without API calls
- [ ] Stale cache triggers re-research
- [ ] Conflict resolution handles agreements and disagreements
- [ ] All sources disabled → empty knowledge, no crash
- [ ] Plugin manager can register/remove custom sources
- [ ] All entities researched in parallel
- [ ] All tests pass
