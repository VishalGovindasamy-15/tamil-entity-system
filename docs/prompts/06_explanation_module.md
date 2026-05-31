# PROMPT: Build Explanation Generation Module

## Context Files (Attach These)

Upload/attach these files before pasting this prompt:
1. `implementation_plan.md` — The master architecture document
2. `module_explanation.md` — Detailed spec for this module

Also make sure the **Core module code** already exists in the workspace at `tamil-entity-system/backend/core/` and `tamil-entity-system/backend/config/`.

---

## Prompt (Paste Everything Below)

---

You are building the **Explanation Generation Module** for a Tamil Entity Recognition system. This module takes verified entity facts and generates **bilingual (Tamil + English) explanations** using LLM APIs, with hallucination detection and quality validation.

### STEP 0: READ AND UNDERSTAND

1. Read **`implementation_plan.md`** — Focus on SystemState, explanation format, and LLM config.
2. Read **`module_explanation.md`** — Your complete spec.
3. Read the **existing core module code**:
   - `backend/core/base_agent.py` — ExplanationAgent extends BaseAgent
   - `backend/core/llm_client.py` — Use `LLMClient.generate()` for text generation
   - `backend/config/default_config.yaml` — `explanation` and `llm` sections

### YOUR DATA CONTRACT

**What you receive (set by Research module):**
```python
state['entity_knowledge']  # Dict keyed by entity text
# {
#   "அப்துல் கலாம்": {
#     "entity_type": "PERSON",
#     "verified_facts": {
#       "full_name": {"value": "...", "confidence": 0.99, "sources": [...], "status": "verified"},
#       "birth_date": {"value": "1931-10-15", ...}
#     },
#     "overall_confidence": 0.96,
#     "fact_count": 12
#   }
# }
```

**What you MUST set:**
```python
state['explanations']  # Dict keyed by entity text
# {
#   "அப்துல் கலாம்": {
#     "tamil": {
#       "detailed": "400-600 words in Tamil...",
#       "summary": "2-3 sentences in Tamil",
#       "key_points": ["point1", "point2", "point3"],
#       "word_count": 487,
#       "quality": {"valid": true, "issues": [], "word_count": 487}
#     },
#     "english": {
#       "detailed": "400-600 words in English...",
#       "summary": "2-3 sentences",
#       "key_points": ["point1", "point2", "point3"],
#       "word_count": 512,
#       "quality": {"valid": true, "issues": [], "word_count": 512}
#     }
#   }
# }
```

**Who reads your output:** The Response module reads `state['explanations']` to build the final output.

### FILES TO CREATE

```
backend/modules/explanation/
├── __init__.py                 # Exports: ExplanationAgent
├── agent.py                    # ExplanationAgent — orchestrator
├── tamil_generator.py          # TamilExplanationGenerator — Tamil LLM prompt
├── english_generator.py        # EnglishExplanationGenerator — English LLM prompt
├── hallucination_checker.py    # HallucinationChecker — verify claims against facts
└── quality_validator.py        # QualityValidator — word count, script purity, key points

backend/tests/unit/test_explanation/
├── __init__.py
├── test_agent.py
├── test_tamil_generator.py
├── test_english_generator.py
├── test_hallucination_checker.py
└── test_quality_validator.py

backend/tests/module/
└── test_explanation_module.py
```

### IMPLEMENTATION RULES

1. **ExplanationAgent extends BaseAgent**. Its `execute(state)` must:
   - Generate explanations for ALL entities in parallel
   - For each entity: generate Tamil + English (2 LLM calls)
   - Run hallucination check if `explanation.hallucination_check` is true in config
   - If hallucinations found AND `explanation.strict_retry` is true → regenerate with strict mode
   - Run quality validation on all explanations
   - Call `self.increment_api_calls(state, count)` for each LLM call

2. **Tamil Generator** LLM prompt must:
   - Format verified facts as bullet points with confidence scores
   - Request 400-600 words in simple, clear Tamil
   - Request JSON output: `{"detailed": "...", "summary": "...", "key_points": [...]}`
   - Use temperature 0.5 (normal) or 0.3 (strict mode)
   - Include constraint: "Use ONLY the facts provided. Do not invent information."
   - In strict mode, add: "CRITICAL: ONLY use the facts provided. Do NOT add ANY information."

3. **English Generator** — Same structure as Tamil, but encyclopedic English style.

4. **Fact formatting for prompts:**
   ```python
   def _format_facts(self, facts):
       lines = []
       for key, fact in facts.items():
           value = fact.get('value', fact) if isinstance(fact, dict) else fact
           confidence = fact.get('confidence', 'N/A') if isinstance(fact, dict) else 'N/A'
           lines.append(f"- {key.replace('_', ' ').title()}: {value} (confidence: {confidence})")
       return '\n'.join(lines)
   ```

5. **HallucinationChecker** (rule-based for prototype):
   - Split explanation into sentences (split on `.!?।`)
   - For each sentence > 10 chars, check if any verified fact value or key appears in it
   - If a sentence has NO matching fact → flag as potential hallucination
   - Return `{'is_valid': bool, 'hallucinations': list, 'hallucination_count': int}`

6. **QualityValidator** checks:
   - Word count between `explanation.min_word_count` (400) and `explanation.max_word_count` (600)
   - For Tamil: English character ratio must be < 30%
   - At least 2 key points
   - Returns quality dict with `valid`, `issues`, and `word_count`

7. **Entity with no verified facts** → skip, return `{'tamil': None, 'english': None, 'error': 'No verified facts'}`

8. **JSON parsing from LLM:** Handle cases where LLM returns extra text around JSON:
   ```python
   # Try to extract JSON from response
   text = response.strip()
   if text.startswith('```'):
       text = text.split('```')[1].lstrip('json\n')
   data = json.loads(text)
   ```

### TESTING RULES

1. **Mock LLMClient.generate()** — return pre-built JSON responses
2. **Test hallucination detection** with explanation containing extra info
3. **Test quality validator** — too short, too long, too much English in Tamil
4. **Test strict retry flow** — hallucination found → regenerate
5. **Test entity with no facts** → skipped correctly
6. Run:
   ```bash
   cd tamil-entity-system/backend
   pytest tests/unit/test_explanation/ -v
   pytest tests/module/test_explanation_module.py -v
   ```

### FINAL CHECKLIST

- [ ] Tamil generator produces valid Tamil output (or mocked correctly)
- [ ] English generator produces encyclopedic English
- [ ] Hallucination checker flags unsupported claims
- [ ] Strict mode retry regenerates with lower temperature
- [ ] Quality validator catches short/long/impure explanations
- [ ] Entity with no facts → skipped, not crashed
- [ ] JSON parsing handles messy LLM output
- [ ] All explanations have ALL required fields (detailed, summary, key_points, word_count, quality)
- [ ] All tests pass
