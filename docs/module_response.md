# Module 7: Response Compilation

## Purpose
Compile the complete processing results into a **final response** in multiple output formats: JSON, HTML, PDF, Markdown.

---

## Data Contract

**Input:** Complete `SystemState` after all modules have run.

**Output:**
```python
# Returns a dict with the compiled response
{
    "request_id": "uuid",
    "timestamp": "ISO-8601",
    "processing_time_seconds": 8.3,
    "input": {
        "type": "text",
        "original": "...",
        "detected_language": "mixed",
        "normalized": "..."
    },
    "entities": [
        {
            "entity": "அப்துல் கலாம்",
            "type": "PERSON",
            "subtypes": ["SCIENTIST", "POLITICIAN"],
            "confidence": 0.99,
            "position": {"start": 0, "end": 13, "text": "அப்துல் கலாம்"},
            "explanation": {
                "tamil": {"summary": "...", "detailed": "...", "key_points": [...]},
                "english": {"summary": "...", "detailed": "...", "key_points": [...]}
            },
            "verified_facts": {...},
            "sources": [...],
            "related_entities": [...],
            "validation": {
                "sources_consulted": 12,
                "fact_agreement_score": 0.96,
                "conflicts_found": 0
            }
        }
    ],
    "summary": {
        "total_entities": 2,
        "entity_types": {"PERSON": 1, "ORGANIZATION": 1},
        "average_confidence": 0.96,
        "processing_details": {
            "input_processing_time": 0.3,
            "transliteration_time": 0.1,
            "entity_extraction_time": 1.2,
            "research_time": 5.8,
            "explanation_time": 0.9,
            "total_api_calls": 24,
            "cache_hits": 1
        }
    }
}
```

---

## Files

### `modules/response/__init__.py`
Exports: `ResponseBuilder`

---

### `modules/response/builder.py` — ResponseBuilder

```python
class ResponseBuilder(BaseAgent):
    def __init__(self, db, config):
        super().__init__("response_builder", "response", db, config)
        self.formatters = {
            'json': JSONFormatter(),
            'html': HTMLFormatter(),
            'pdf': PDFFormatter(),
            'markdown': MarkdownFormatter()
        }
    
    async def execute(self, state: SystemState) -> SystemState:
        """Compile final response from state"""
        
        response = self._compile_response(state)
        
        # Store in processing_requests table
        await self._store_request(state, response)
        
        # Attach to state
        state['final_response'] = response
        state['processing_status'] = 'completed'
        
        return state
    
    def _compile_response(self, state) -> Dict:
        """Build the response dict from state"""
        
        total_time = time.time() - state['started_at_epoch']
        
        entities_output = []
        for entity in state['entities']:
            name = entity['text']
            knowledge = state['entity_knowledge'].get(name, {})
            explanation = state['explanations'].get(name, {})
            
            entities_output.append({
                'entity': name,
                'type': entity['type'],
                'confidence': entity['confidence'],
                'position': {'start': entity.get('start'), 'end': entity.get('end')},
                'explanation': explanation,
                'verified_facts': knowledge.get('verified_facts', {}),
                'sources': knowledge.get('sources_consulted', []),
                'related_entities': knowledge.get('related_entities', []),
                'validation': {
                    'sources_consulted': knowledge.get('source_count', 0),
                    'fact_agreement_score': knowledge.get('overall_confidence', 0),
                    'conflicts_found': 0
                }
            })
        
        return {
            'request_id': state['request_id'],
            'timestamp': datetime.now().isoformat(),
            'processing_time_seconds': round(total_time, 2),
            'input': {
                'type': state['input_type'],
                'detected_language': state['detected_language'],
                'scripts': state['detected_scripts']
            },
            'entities': entities_output,
            'summary': self._build_summary(state, entities_output, total_time),
            'metadata': {
                'processing_steps': state['processing_steps'],
                'errors': state['errors'],
                'warnings': state['warnings']
            }
        }
    
    def format(self, response: Dict, format_type: str = 'json') -> Any:
        """Format response in requested format"""
        formatter = self.formatters.get(format_type)
        if formatter:
            return formatter.format(response)
        return response
```

**Tests:**
- Test response compilation from complete state
- Test with 0 entities → valid response, empty entities list
- Test with multiple entities → all included
- Test processing time calculation
- Test summary statistics

---

### `modules/response/json_formatter.py`

```python
class JSONFormatter:
    def format(self, response: Dict) -> str:
        return json.dumps(response, ensure_ascii=False, indent=2)
```

---

### `modules/response/html_formatter.py`

```python
class HTMLFormatter:
    def format(self, response: Dict) -> str:
        """Generate styled HTML report"""
        # Uses a simple template (Jinja2 or f-strings)
        html = f"""
        <!DOCTYPE html>
        <html lang="ta">
        <head>
            <meta charset="UTF-8">
            <title>Tamil Entity Recognition Report</title>
            <style>
                body {{ font-family: 'Noto Sans Tamil', sans-serif; ... }}
                .entity-card {{ border: 1px solid #ddd; padding: 16px; margin: 8px; ... }}
                .confidence {{ color: green; font-weight: bold; }}
                ...
            </style>
        </head>
        <body>
            <h1>Entity Recognition Report</h1>
            <p>Processing Time: {response['processing_time_seconds']}s</p>
            ...
            {self._render_entities(response['entities'])}
        </body>
        </html>
        """
        return html
```

---

### `modules/response/markdown_formatter.py`

```python
class MarkdownFormatter:
    def format(self, response: Dict) -> str:
        """Generate Markdown report"""
        
        lines = [
            f"# Tamil Entity Recognition Report",
            f"",
            f"**Processing Time:** {response['processing_time_seconds']}s",
            f"**Input Type:** {response['input']['type']}",
            f"**Total Entities:** {response['summary']['total_entities']}",
            f"",
            "---",
            ""
        ]
        
        for entity in response.get('entities', []):
            lines.append(f"## {entity['entity']} ({entity['type']})")
            lines.append(f"**Confidence:** {entity['confidence']:.0%}")
            lines.append("")
            
            # Tamil explanation
            tamil = entity.get('explanation', {}).get('tamil', {})
            if tamil and tamil.get('summary'):
                lines.append("### தமிழ் விளக்கம்")
                lines.append(tamil['summary'])
                lines.append("")
            
            # English explanation
            english = entity.get('explanation', {}).get('english', {})
            if english and english.get('summary'):
                lines.append("### English Explanation")
                lines.append(english['summary'])
                lines.append("")
            
            # Sources
            if entity.get('sources'):
                lines.append("### Sources")
                for src in entity['sources']:
                    lines.append(f"- {src.get('type', 'unknown')} (credibility: {src.get('credibility', 'N/A')})")
                lines.append("")
            
            lines.append("---")
            lines.append("")
        
        return '\n'.join(lines)
```

**Tests:**
- Test markdown output structure
- Test with entities → headers rendered
- Test with no entities → minimal valid output

---

### `modules/response/pdf_formatter.py`

```python
class PDFFormatter:
    def format(self, response: Dict) -> bytes:
        """Generate PDF report using reportlab or weasyprint"""
        # For prototype: convert HTML to PDF
        from weasyprint import HTML
        html = HTMLFormatter().format(response)
        return HTML(string=html).write_pdf()
```

---

## Module-Level Test (`tests/module/test_response_module.py`)

1. Complete state → JSON response with all fields
2. Complete state → HTML report renders properly
3. Empty entities → valid response structure
4. Multiple entities → summary stats correct
5. Format switching: JSON → HTML → PDF

---

## Dependencies

```
jinja2>=3.1.0         # HTML templating (optional, can use f-strings)
weasyprint>=60.0      # PDF generation (optional)
```
