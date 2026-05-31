# PROMPT: Build Input Orchestration Module

## Context Files (Attach These)

Upload/attach these files before pasting this prompt:
1. `implementation_plan.md` — The master architecture document
2. `module_input.md` — Detailed spec for the Input module

Also make sure the **Core module code** already exists in the workspace at `tamil-entity-system/backend/core/` and `tamil-entity-system/backend/config/`. If it doesn't, ask the user to provide the core module files first.

---

## Prompt (Paste Everything Below)

---

You are building the **Input Orchestration Module** for a Tamil Entity Recognition system.

### STEP 0: READ AND UNDERSTAND

1. Read **`implementation_plan.md`** — Understand the full architecture, especially:
   - The `SystemState` TypedDict (what fields exist)
   - The configuration system (how to check if a processor is enabled)
   - The data flow (Input module is the FIRST processing stage)

2. Read **`module_input.md`** — This is your detailed spec. Implement every file listed.

3. Read the **existing core module code** in the workspace:
   - `backend/core/state.py` — To understand SystemState fields
   - `backend/core/base_agent.py` — Your InputCoordinator extends BaseAgent
   - `backend/core/base_processor.py` — All processors extend BaseInputProcessor
   - `backend/core/contracts.py` — Your processors return ProcessorResult
   - `backend/config/settings.py` — To understand how config.get() works
   - `backend/config/default_config.yaml` — To see which processors are configured

### YOUR DATA CONTRACT

**What you receive:**
```python
state['input_type']     # 'text' | 'image' | 'pdf' | 'audio' | 'video' | 'url'
state['input_content']  # str (text/URL) or bytes/filepath (files)
state['input_metadata'] # {'filename': '...', 'size_bytes': ..., 'mime_type': '...'}
```

**What you MUST set:**
```python
state['raw_text']                          # The extracted text (THIS IS CRITICAL — next module depends on it)
state['input_metadata']['quality_score']   # 0.0-1.0 quality assessment
state['detected_language']                 # 'ta', 'en', or 'mixed'
```

**What you must NOT modify:** Any other state fields. The next module (Transliteration) reads `state['raw_text']`.

### FILES TO CREATE

```
backend/modules/input/
├── __init__.py           # Exports: InputCoordinator
├── coordinator.py        # InputProcessingAgent — routes to correct processor, handles fallbacks
├── text_processor.py     # TextProcessor — validation and Unicode normalization
├── image_processor.py    # EasyOCRProcessor, GoogleVisionProcessor, TesseractProcessor
├── pdf_processor.py      # PyMuPDFProcessor, PdfPlumberProcessor
├── audio_processor.py    # WhisperProcessor, GoogleSpeechProcessor, AzureSpeechProcessor
├── video_processor.py    # VideoProcessor — extract audio + frames + subtitles
└── url_processor.py      # URLProcessor — web scraping + YouTube transcripts

backend/tests/unit/test_input/
├── __init__.py
├── test_coordinator.py
├── test_text_processor.py
├── test_image_processor.py
├── test_pdf_processor.py
├── test_audio_processor.py
├── test_video_processor.py
└── test_url_processor.py

backend/tests/module/
└── test_input_module.py
```

### IMPLEMENTATION RULES

1. **Every processor extends `BaseInputProcessor`** from `core/base_processor.py`. Each must implement:
   - `async def process(self, content, **kwargs) -> ProcessorResult`
   - `async def health_check(self) -> bool`

2. **InputCoordinator extends `BaseAgent`** from `core/base_agent.py`. It must:
   - Load all enabled processors from config using `self.config.get_enabled_processors(category)`
   - Sort processors by priority
   - Try processors in order, fallback on failure
   - Call `self.log_step(state, ...)` for each successful step
   - Call `self.log_error(state, ...)` for each failure
   - Call `self.increment_api_calls(state)` for non-local API calls

3. **Configuration-driven:** Every processor checks `self.is_enabled()` before running. If all processors for a type are disabled, return empty text with a warning (NOT an error/crash).

4. **Processor priority:** Read from config:
   ```yaml
   input.image.processors.easyocr.enabled: true
   input.image.processors.easyocr.priority: 1  # try first
   input.image.processors.tesseract.priority: 3  # try last
   ```

5. **Language detection:** Simple rule-based for prototype:
   - Check for Tamil Unicode range (U+0B80 to U+0BFF) → Tamil chars found
   - Check for ASCII alpha chars → English chars found
   - Both found → 'mixed', only Tamil → 'ta', only English → 'en'

6. **Quality assessment:** Simple heuristic:
   - Check text length, character ratio, gibberish detection
   - Return 0.0-1.0 score

7. **External dependencies:** Some processors need external libraries. Handle import errors gracefully:
   ```python
   try:
       import easyocr
   except ImportError:
       # Log warning, mark processor as unavailable
   ```

### TESTING RULES

1. **Mock external dependencies** (easyocr, whisper, pytesseract, etc.) in unit tests
2. **Test the coordinator's fallback logic** — primary fails → secondary picked up
3. **Test config toggling** — disable all OCR → empty text with warning
4. **Test each processor independently** with sample data
5. After all files created, run:
   ```bash
   cd tamil-entity-system/backend
   pytest tests/unit/test_input/ -v
   pytest tests/module/test_input_module.py -v
   ```
6. Fix any failures before declaring the module complete.

### FINAL CHECKLIST

- [ ] `coordinator.py` — InputCoordinator routes all 6 input types correctly
- [ ] `text_processor.py` — Unicode normalization, whitespace cleanup
- [ ] `image_processor.py` — 3 OCR engines, all toggleable
- [ ] `pdf_processor.py` — 2 PDF processors, scanned PDF detection
- [ ] `audio_processor.py` — 3 ASR engines, all toggleable
- [ ] `video_processor.py` — Extracts audio + frames + subtitles
- [ ] `url_processor.py` — Web scraping + YouTube transcript support
- [ ] All processors return `ProcessorResult` (from `core/contracts.py`)
- [ ] Fallback logic works (primary fails → secondary tries)
- [ ] All disabled → warning, not crash
- [ ] Language detection works for Tamil, English, mixed
- [ ] All unit tests pass
- [ ] Module test passes
