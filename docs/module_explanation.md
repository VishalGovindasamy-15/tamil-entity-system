# Module 6: Explanation Generation

## Purpose
Generate detailed **bilingual explanations** (Tamil + English, 400-600 words each) for each entity based on verified facts. Includes **hallucination detection**, quality validation, and strict mode retry.

---

## Data Contract

**Input:**
```python
state['entity_knowledge']  # From Research module
# {"அப்துல் கலாம்": {"verified_facts": {...}, "entity_type": "PERSON", ...}}
```

**Output:**
```python
state['explanations']
# {
#   "அப்துல் கலாம்": {
#     "tamil": {
#       "detailed": "400-600 words in Tamil...",
#       "summary": "2-3 sentences in Tamil",
#       "key_points": ["point1", "point2", "point3"],
#       "word_count": 487
#     },
#     "english": {
#       "detailed": "400-600 words in English...",
#       "summary": "2-3 sentences",
#       "key_points": ["point1", "point2", "point3"],
#       "word_count": 512
#     }
#   }
# }
```

---

## Files

### `modules/explanation/__init__.py`
Exports: `ExplanationAgent`

---

### `modules/explanation/agent.py` — ExplanationAgent

```python
class ExplanationAgent(BaseAgent):
    def __init__(self, db, config, llm_client):
        super().__init__("explanation_generator", "explanation", db, config)
        self.llm = llm_client
        self.tamil_gen = TamilExplanationGenerator(llm_client, config)
        self.english_gen = EnglishExplanationGenerator(llm_client, config)
        self.hallucination_checker = HallucinationChecker(llm_client)
        self.quality_validator = QualityValidator(config)
    
    async def execute(self, state: SystemState) -> SystemState:
        knowledge = state['entity_knowledge']
        
        # Generate explanations in parallel
        tasks = [
            self._generate_for_entity(name, data, state)
            for name, data in knowledge.items()
        ]
        results = await asyncio.gather(*tasks)
        
        for name, result in zip(knowledge.keys(), results):
            state['explanations'][name] = result
        
        return state
    
    async def _generate_for_entity(self, name, knowledge, state) -> Dict:
        facts = knowledge.get('verified_facts', {})
        entity_type = knowledge.get('entity_type', 'OTHER')
        
        if not facts:
            return {'tamil': None, 'english': None, 'error': 'No verified facts'}
        
        # Generate both
        tamil = await self.tamil_gen.generate(name, entity_type, facts)
        english = await self.english_gen.generate(name, entity_type, facts)
        self.increment_api_calls(state, 2)
        
        # Hallucination check
        if self.config.get('explanation.hallucination_check', True):
            tamil_valid = await self.hallucination_checker.check(tamil['detailed'], facts, 'tamil')
            english_valid = await self.hallucination_checker.check(english['detailed'], facts, 'english')
            
            # Retry with strict mode if hallucinations found
            if not tamil_valid['is_valid'] and self.config.get('explanation.strict_retry', True):
                self.log_step(state, f"Regenerating Tamil explanation (hallucinations found)")
                tamil = await self.tamil_gen.generate(name, entity_type, facts, strict=True)
                self.increment_api_calls(state)
            
            if not english_valid['is_valid'] and self.config.get('explanation.strict_retry', True):
                self.log_step(state, f"Regenerating English explanation (hallucinations found)")
                english = await self.english_gen.generate(name, entity_type, facts, strict=True)
                self.increment_api_calls(state)
        
        # Quality validation
        tamil = self.quality_validator.validate(tamil, 'tamil')
        english = self.quality_validator.validate(english, 'english')
        
        return {'tamil': tamil, 'english': english}
```

**Tests:**
- Test successful generation for entity with facts
- Test entity with no facts → skipped
- Test hallucination detected → strict mode retry
- Test quality validation (word count check)
- Test parallel generation for multiple entities

---

### `modules/explanation/tamil_generator.py`

```python
class TamilExplanationGenerator:
    def __init__(self, llm_client, config):
        self.llm = llm_client
        self.config = config
    
    async def generate(self, entity_name, entity_type, facts, strict=False) -> Dict:
        facts_str = self._format_facts(facts)
        
        constraint = (
            "CRITICAL: ONLY use the facts provided. Do NOT add ANY information. "
            "If unsure, write 'தெரியவில்லை'. Every sentence must come from a fact."
            if strict else
            "Use ONLY the facts provided. Do not invent information."
        )
        
        prompt = f"""
You are an expert Tamil content writer creating educational explanations.

Entity: {entity_name}
Type: {entity_type}

VERIFIED FACTS:
{facts_str}

{constraint}

Write a comprehensive Tamil explanation (400-600 words) about {entity_name}.

Requirements:
1. Clear, simple Tamil for students
2. Start with who/what they are
3. Explain significance
4. Include key achievements
5. Respectful tone for people
6. Prefer native Tamil words
7. ONLY use provided facts

Return JSON:
{{"detailed": "...", "summary": "...", "key_points": ["...", "...", "..."]}}

Return ONLY valid JSON.
"""
        
        response = await self.llm.generate(
            prompt=prompt,
            temperature=0.3 if strict else 0.5,
            max_tokens=1500
        )
        
        data = json.loads(response.strip())
        data['word_count'] = len(data['detailed'].split())
        return data
    
    def _format_facts(self, facts: Dict) -> str:
        lines = []
        for key, fact in facts.items():
            value = fact.get('value', fact) if isinstance(fact, dict) else fact
            confidence = fact.get('confidence', 'N/A') if isinstance(fact, dict) else 'N/A'
            formatted_key = key.replace('_', ' ').title()
            lines.append(f"- {formatted_key}: {value} (confidence: {confidence})")
        return '\n'.join(lines)
```

**Tests:**
- Test prompt construction (facts formatted correctly)
- Test JSON parsing of response
- Test strict mode uses lower temperature
- Test word count calculation

---

### `modules/explanation/english_generator.py`

Same structure as Tamil generator, but with encyclopedic English prompt:
- Formal, encyclopedic style
- Includes historical context
- Objective tone
- 400-600 words

---

### `modules/explanation/hallucination_checker.py`

```python
class HallucinationChecker:
    def __init__(self, llm_client):
        self.llm = llm_client
    
    async def check(self, explanation_text, verified_facts, language) -> Dict:
        """Check if explanation contains information not in verified facts"""
        
        # Option 1: Rule-based check (fast, for prototype)
        claims = self._extract_claims_simple(explanation_text)
        
        hallucinations = []
        for claim in claims:
            if not self._is_supported(claim, verified_facts):
                hallucinations.append(claim)
        
        return {
            'is_valid': len(hallucinations) == 0,
            'hallucinations': hallucinations,
            'hallucination_count': len(hallucinations)
        }
    
    def _extract_claims_simple(self, text: str) -> List[str]:
        """Simple claim extraction: split by sentences"""
        import re
        sentences = re.split(r'[.!?।]', text)
        return [s.strip() for s in sentences if len(s.strip()) > 10]
    
    def _is_supported(self, claim: str, facts: Dict) -> bool:
        """Check if claim is supported by any verified fact"""
        for fact_key, fact_data in facts.items():
            value = str(fact_data.get('value', '')) if isinstance(fact_data, dict) else str(fact_data)
            # Simple substring/keyword check
            if value.lower() in claim.lower() or fact_key.replace('_', ' ') in claim.lower():
                return True
        return False
```

**Tests:**
- Test explanation using only verified facts → valid
- Test explanation with extra info → hallucination detected
- Test claim extraction from Tamil text
- Test claim extraction from English text
- Test edge case: very short explanation

---

### `modules/explanation/quality_validator.py`

```python
class QualityValidator:
    def __init__(self, config):
        self.min_words = config.get('explanation.min_word_count', 400)
        self.max_words = config.get('explanation.max_word_count', 600)
    
    def validate(self, explanation: Dict, language: str) -> Dict:
        """Add quality metadata to explanation"""
        
        if not explanation or 'detailed' not in explanation:
            explanation['quality'] = {'valid': False, 'reason': 'Missing content'}
            return explanation
        
        word_count = len(explanation['detailed'].split())
        
        issues = []
        if word_count < self.min_words:
            issues.append(f"Too short ({word_count} words, min {self.min_words})")
        if word_count > self.max_words:
            issues.append(f"Too long ({word_count} words, max {self.max_words})")
        
        # Tamil-specific: check for excessive English in Tamil explanation
        if language == 'tamil':
            english_ratio = self._english_ratio(explanation['detailed'])
            if english_ratio > 0.3:
                issues.append(f"Too much English ({english_ratio:.0%})")
        
        # Check key_points exist
        if not explanation.get('key_points') or len(explanation['key_points']) < 2:
            issues.append("Insufficient key points")
        
        explanation['quality'] = {
            'valid': len(issues) == 0,
            'issues': issues,
            'word_count': word_count
        }
        
        return explanation
    
    def _english_ratio(self, text: str) -> float:
        """Calculate ratio of English characters in text"""
        english_chars = sum(1 for c in text if c.isalpha() and ord(c) < 128)
        total_chars = sum(1 for c in text if c.isalpha())
        return english_chars / total_chars if total_chars > 0 else 0
```

**Tests:**
- Test valid explanation passes
- Test too short → issue flagged
- Test too long → issue flagged
- Test Tamil with too much English → issue flagged
- Test missing key points → issue flagged

---

## Module-Level Test (`tests/module/test_explanation_module.py`)

1. Entity with rich facts → generates Tamil + English explanations
2. Entity with few facts → shorter but valid explanations
3. Entity with no facts → skipped with error message
4. Hallucination check → explanation with fabricated fact → caught, regenerated
5. Quality check → word count validation works
6. Parallel generation for 3 entities simultaneously
7. LLM returns invalid JSON → error handling, retry

---

## Dependencies

```
# LLM clients (configurable, at least one required)
google-generativeai>=0.3.0   # Gemini
openai>=1.0.0                 # GPT-4
anthropic>=0.18.0             # Claude
# ollama (via HTTP, no pip package needed)
```
