# PROMPT: Build Response Compilation Module

## Context Files (Attach These)

Upload/attach these files before pasting this prompt:
1. `implementation_plan.md` — The master architecture document
2. `module_response.md` — Detailed spec for this module

Also make sure the **Core module code** already exists in the workspace at `tamil-entity-system/backend/core/` and `tamil-entity-system/backend/config/`.

---

## Prompt (Paste Everything Below)

---

You are building the **Response Compilation Module** for a Tamil Entity Recognition system. This is the final processing stage — it takes the complete SystemState (with entities, knowledge, and explanations) and compiles it into a structured response in multiple output formats.

### STEP 0: READ AND UNDERSTAND

1. Read **`implementation_plan.md`** — Focus on SystemState, response format, and the final output structure.
2. Read **`module_response.md`** — Your complete spec with formatters and output schema.
3. Read the **existing core module code**:
   - `backend/core/base_agent.py` — ResponseBuilder extends BaseAgent
   - `backend/core/state.py` — SystemState with ALL fields you'll read from
   - `backend/core/database.py` — Database class for storing to `processing_requests` table
   - `backend/config/default_config.yaml` — `response` section (enabled formats, include_sources, include_metrics)

### YOUR DATA CONTRACT

**What you receive (the COMPLETE state after all modules):**
```python
state['request_id']              # UUID string
state['input_type']              # 'text', 'image', etc.
state['detected_language']       # 'ta', 'en', 'mixed'
state['detected_scripts']       # ['tamil', 'english', ...]
state['entities']                # List of entity dicts
state['entity_knowledge']        # Dict of researched knowledge per entity
state['explanations']            # Dict of bilingual explanations per entity
state['processing_steps']        # List of log messages
state['api_calls_made']          # int
state['cache_hits']              # int
state['sources_accessed']        # int
state['errors']                  # List of error dicts
state['warnings']                # List of warning strings
state['stage_timings']           # Dict: stage_name → seconds
```

**What you MUST set:**
```python
state['final_response']     # The compiled response dict (see output format below)
state['processing_status']  # Set to 'completed'
```

**Also:** Store the request in the `processing_requests` SQLite table.

### FILES TO CREATE

```
backend/modules/response/
├── __init__.py              # Exports: ResponseBuilder
├── builder.py               # ResponseBuilder — compiles final response
├── json_formatter.py        # JSONFormatter — JSON string output
├── html_formatter.py        # HTMLFormatter — styled HTML report
├── markdown_formatter.py    # MarkdownFormatter — Markdown report
└── pdf_formatter.py         # PDFFormatter — PDF via HTML→PDF conversion

backend/tests/unit/test_response/
├── __init__.py
├── test_builder.py
├── test_json_formatter.py
├── test_html_formatter.py
├── test_markdown_formatter.py
└── test_pdf_formatter.py

backend/tests/module/
└── test_response_module.py
```

### IMPLEMENTATION RULES

1. **ResponseBuilder extends BaseAgent**. Its `execute(state)` must:
   - Call `_compile_response(state)` to build the response dict
   - Store the request in `processing_requests` table via `self.db`
   - Set `state['final_response'] = response`
   - Set `state['processing_status'] = 'completed'`
   - Return state

2. **Response dict format** (the `_compile_response` output):
   ```python
   {
       "request_id": state['request_id'],
       "timestamp": datetime.now().isoformat(),
       "processing_time_seconds": total_time,
       "input": {
           "type": state['input_type'],
           "detected_language": state['detected_language'],
           "scripts": state['detected_scripts']
       },
       "entities": [
           {
               "entity": name,
               "type": entity['type'],
               "confidence": entity['confidence'],
               "position": {"start": entity.get('start'), "end": entity.get('end')},
               "explanation": explanations.get(name, {}),
               "verified_facts": knowledge.get('verified_facts', {}),
               "sources": knowledge.get('sources_consulted', []),
               "validation": {
                   "sources_consulted": knowledge.get('source_count', 0),
                   "fact_agreement_score": knowledge.get('overall_confidence', 0),
               }
           }
           for entity in state['entities']
       ],
       "summary": {
           "total_entities": len(entities),
           "entity_types": count_by_type,
           "average_confidence": avg_confidence,
           "processing_details": {timing_breakdown + api_calls + cache_hits}
       },
       "metadata": {
           "processing_steps": state['processing_steps'],
           "errors": state['errors'],
           "warnings": state['warnings']
       }
   }
   ```

3. **`format(response, format_type)`** method routes to the correct formatter.

4. **HTMLFormatter**: Styled report with Tamil font support (`Noto Sans Tamil`), entity cards, confidence bars.

5. **MarkdownFormatter**: Structured markdown with headers, tables, and bullet points.

6. **PDFFormatter**: Convert HTML to PDF using `weasyprint`. If weasyprint is not installed, return an error message instead of crashing.

### TESTING RULES

1. **Create a mock complete state** with sample entities, knowledge, and explanations
2. **Test that all required fields exist** in compiled response
3. **Test with 0 entities** → valid response, empty entities list
4. **Test each formatter** produces valid output
5. Run:
   ```bash
   cd tamil-entity-system/backend
   pytest tests/unit/test_response/ -v
   pytest tests/module/test_response_module.py -v
   ```

### FINAL CHECKLIST

- [ ] `builder.py` compiles correct response from state
- [ ] JSON formatter produces valid JSON with Tamil chars (ensure_ascii=False)
- [ ] HTML formatter produces styled report with Tamil font
- [ ] Markdown formatter produces valid markdown
- [ ] PDF formatter works (or gracefully handles missing weasyprint)
- [ ] 0 entities → valid response, not crash
- [ ] Summary statistics are correct (entity counts, timing, API calls)
- [ ] Processing request stored in DB
- [ ] All tests pass
