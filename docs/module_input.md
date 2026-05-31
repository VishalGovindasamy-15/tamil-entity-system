# Module 2: Input Orchestration

## Purpose
Accept **any input type** (text, image, PDF, audio, video, URL) and extract clean text. All processors are **configurable and toggleable** — if a processor is disabled or fails, the next one by priority takes over.

---

## Data Contract

**Input to this module:**
```python
state['input_type']     # 'text' | 'image' | 'pdf' | 'audio' | 'video' | 'url'
state['input_content']  # str (text/URL) or bytes/filepath (files)
state['input_metadata'] # {'filename': '...', 'size_bytes': ..., 'mime_type': '...'}
```

**Output from this module:**
```python
state['raw_text']                     # Extracted text
state['input_metadata']['quality_score']  # 0.0-1.0 quality assessment
state['detected_language']             # 'ta', 'en', 'mixed'
```

---

## Files

### `modules/input/__init__.py`
Exports: `InputCoordinator`

---

### `modules/input/coordinator.py` — InputProcessingAgent

The orchestrator for all input processing. Routes to the correct processor based on `input_type`, handles fallbacks.

```python
class InputCoordinator(BaseAgent):
    def __init__(self, db, config):
        super().__init__("input_coordinator", "input", db, config)
        self.processors = self._load_processors()
    
    def _load_processors(self) -> Dict[str, List[BaseInputProcessor]]:
        """Load all enabled processors, grouped by type, sorted by priority"""
        # Returns: {'image': [EasyOCRProcessor, TesseractProcessor], 'audio': [...], ...}
    
    async def execute(self, state: SystemState) -> SystemState:
        """Route to correct processor, handle fallbacks"""
        input_type = state['input_type']
        
        if input_type == 'text':
            state['raw_text'] = state['input_content']
        elif input_type in self.processors:
            state['raw_text'] = await self._process_with_fallback(input_type, state)
        else:
            # Error: unsupported or all processors disabled
            
        # Quality assessment
        state['input_metadata']['quality_score'] = self._assess_quality(state['raw_text'])
        
        # Language detection
        state['detected_language'] = self._detect_language(state['raw_text'])
        
        return state
    
    async def _process_with_fallback(self, input_type, state) -> str:
        """Try processors in priority order, fallback on failure"""
        processors = self.processors.get(input_type, [])
        
        for processor in processors:
            try:
                result = await processor.process(state['input_content'], **state['input_metadata'])
                if result.success and result.confidence >= 0.5:
                    self.log_step(state, f"Processed with {result.processor_name} (conf: {result.confidence})")
                    self.increment_api_calls(state, 1 if not processor.is_local else 0)
                    return result.text
            except Exception as e:
                self.log_error(state, f"{processor.processor_name} failed: {e}")
        
        self.log_error(state, f"All {input_type} processors failed")
        return ""
    
    def _assess_quality(self, text: str) -> float:
        """Simple text quality scorer"""
    
    def _detect_language(self, text: str) -> str:
        """Detect if Tamil, English, or mixed"""
```

**Tests (`tests/unit/test_input/test_coordinator.py`):**
- Test text input passes through directly
- Test image routing to OCR processors
- Test fallback: primary fails → secondary succeeds
- Test all processors disabled → warning, empty text
- Test quality assessment (good text → high score, garbage → low score)
- Test language detection (Tamil, English, mixed)

---

### `modules/input/text_processor.py`

Minimal — text input needs no processing. Just validation and cleanup.

```python
class TextProcessor(BaseInputProcessor):
    async def process(self, content: str, **kwargs) -> ProcessorResult:
        """Validate and clean text input"""
        # Strip whitespace, normalize unicode
        cleaned = unicodedata.normalize('NFC', content.strip())
        return ProcessorResult(
            success=True,
            text=cleaned,
            confidence=1.0,
            processor_name="text"
        )
```

**Tests:**
- Test whitespace stripping
- Test Unicode normalization (important for Tamil characters)
- Test empty input handling

---

### `modules/input/image_processor.py` — OCR Engines

Three configurable OCR processors:

```python
class EasyOCRProcessor(BaseInputProcessor):
    """OCR using EasyOCR library (local, free)"""
    
    async def process(self, content: bytes | str, **kwargs) -> ProcessorResult:
        import easyocr
        reader = easyocr.Reader(['ta', 'en'])
        results = reader.readtext(content)
        text = ' '.join([r[1] for r in results])
        confidence = sum(r[2] for r in results) / len(results) if results else 0
        return ProcessorResult(success=True, text=text, confidence=confidence, processor_name="easyocr")
    
    is_local = True  # No API call


class GoogleVisionProcessor(BaseInputProcessor):
    """OCR using Google Cloud Vision API"""
    
    async def process(self, content: bytes | str, **kwargs) -> ProcessorResult:
        # Uses google-cloud-vision API
        # Requires GOOGLE_VISION_API_KEY
        ...
    
    is_local = False


class TesseractProcessor(BaseInputProcessor):
    """OCR using Tesseract (local, free)"""
    
    async def process(self, content: bytes | str, **kwargs) -> ProcessorResult:
        import pytesseract
        from PIL import Image
        image = Image.open(content) if isinstance(content, str) else Image.open(io.BytesIO(content))
        text = pytesseract.image_to_string(image, lang='tam+eng')
        return ProcessorResult(success=True, text=text, confidence=0.75, processor_name="tesseract")
    
    is_local = True
```

**Config:**
```yaml
input.image.processors.easyocr.enabled: true
input.image.processors.easyocr.priority: 1
input.image.processors.google_vision.enabled: false
input.image.processors.google_vision.priority: 2
input.image.processors.tesseract.enabled: true
input.image.processors.tesseract.priority: 3
```

**Tests (`tests/unit/test_input/test_image_processor.py`):**
- Test EasyOCR with sample Tamil image
- Test Tesseract with sample image
- Test Google Vision (mocked)
- Test with low-quality image (returns low confidence)
- Test with empty/invalid image

---

### `modules/input/pdf_processor.py`

```python
class PyMuPDFProcessor(BaseInputProcessor):
    """PDF text extraction using PyMuPDF (fitz)"""
    
    async def process(self, content: bytes | str, **kwargs) -> ProcessorResult:
        import fitz  # PyMuPDF
        doc = fitz.open(content if isinstance(content, str) else stream=content)
        text = ""
        for page in doc:
            text += page.get_text()
        # If no text (scanned PDF), fall through to OCR via coordinator
        return ProcessorResult(
            success=bool(text.strip()),
            text=text,
            confidence=0.95 if text.strip() else 0.0,
            processor_name="pymupdf",
            metadata={"page_count": len(doc)}
        )


class PdfPlumberProcessor(BaseInputProcessor):
    """PDF extraction using pdfplumber (better for tables)"""
    ...
```

**Tests:**
- Test text-based PDF extraction
- Test multi-page PDF
- Test scanned PDF (returns empty text, low confidence — triggers OCR fallback)

---

### `modules/input/audio_processor.py` — ASR Engines

```python
class WhisperProcessor(BaseInputProcessor):
    """Speech-to-text using OpenAI Whisper (local)"""
    
    async def process(self, content: bytes | str, **kwargs) -> ProcessorResult:
        import whisper
        model = whisper.load_model(self.config.get("model", "base"))
        result = model.transcribe(content, language="ta")
        return ProcessorResult(
            success=True,
            text=result["text"],
            confidence=0.85,
            processor_name="whisper",
            metadata={"language": result.get("language")}
        )
    
    is_local = True


class GoogleSpeechProcessor(BaseInputProcessor):
    """Google Cloud Speech-to-Text API"""
    ...


class AzureSpeechProcessor(BaseInputProcessor):
    """Azure Cognitive Services Speech"""
    ...
```

**Config:**
```yaml
input.audio.processors.whisper.enabled: true
input.audio.processors.whisper.model: "base"
input.audio.processors.whisper.language: "ta"
input.audio.processors.google_speech.enabled: false
input.audio.processors.azure_speech.enabled: false
```

**Tests:**
- Test Whisper with sample Tamil audio (mocked for CI)
- Test Google Speech (mocked)
- Test unsupported audio format handling

---

### `modules/input/video_processor.py`

Video processing combines multiple steps:
1. Extract audio track → send to audio processor
2. Extract frames at intervals → send to image processor (OCR)
3. Check for embedded subtitles
4. Merge all text

```python
class VideoProcessor(BaseInputProcessor):
    def __init__(self, config, audio_processors, image_processors):
        self.audio_processors = audio_processors
        self.image_processors = image_processors
    
    async def process(self, content: str, **kwargs) -> ProcessorResult:
        # 1. Extract audio using ffmpeg
        audio_path = await self._extract_audio(content)
        
        # 2. Transcribe audio
        audio_text = await self._transcribe(audio_path)
        
        # 3. Extract key frames
        frames = await self._extract_frames(content, interval_seconds=5)
        
        # 4. OCR on frames
        frame_texts = await self._ocr_frames(frames)
        
        # 5. Check subtitles
        subtitle_text = await self._extract_subtitles(content)
        
        # 6. Merge all
        combined = self._merge_texts(audio_text, frame_texts, subtitle_text)
        
        return ProcessorResult(success=True, text=combined, confidence=0.80, processor_name="video")
```

**Tests:**
- Test audio extraction (mocked ffmpeg)
- Test frame extraction
- Test subtitle extraction
- Test text merging from multiple sources

---

### `modules/input/url_processor.py`

```python
class URLProcessor(BaseInputProcessor):
    async def process(self, content: str, **kwargs) -> ProcessorResult:
        url = content
        
        # Detect URL type
        if 'youtube.com' in url or 'youtu.be' in url:
            return await self._process_youtube(url)
        else:
            return await self._process_webpage(url)
    
    async def _process_webpage(self, url: str) -> ProcessorResult:
        """Scrape and extract text from webpage"""
        import httpx
        from bs4 import BeautifulSoup
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script/style
            for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
                tag.decompose()
            
            text = soup.get_text(separator=' ', strip=True)
        
        return ProcessorResult(success=True, text=text, confidence=0.85, processor_name="url_scraper")
    
    async def _process_youtube(self, url: str) -> ProcessorResult:
        """Extract YouTube transcript"""
        from youtube_transcript_api import YouTubeTranscriptApi
        
        video_id = self._extract_video_id(url)
        transcripts = YouTubeTranscriptApi.list_transcripts(video_id)
        
        # Try Tamil first, then English
        for lang in ['ta', 'en']:
            try:
                transcript = transcripts.find_transcript([lang])
                text = ' '.join([t['text'] for t in transcript.fetch()])
                return ProcessorResult(success=True, text=text, confidence=0.80, processor_name="youtube")
            except:
                continue
        
        return ProcessorResult(success=False, error_message="No transcript available")
```

**Tests:**
- Test webpage scraping (mocked HTTP)
- Test YouTube transcript extraction (mocked)
- Test invalid URL handling
- Test YouTube ID extraction

---

## Module-Level Test (`tests/module/test_input_module.py`)

Full flow tests:
1. **Text input** → direct passthrough, quality check
2. **Image input** → EasyOCR (primary) succeeds → returns text
3. **Image input** → EasyOCR disabled, Tesseract enabled → uses Tesseract
4. **Image input** → All disabled → returns empty text with warning
5. **PDF input** → text-based PDF → extracts text
6. **Audio input** → Whisper extracts Tamil speech
7. **URL input** → Webpage → scrapes text
8. **URL input** → YouTube URL → extracts transcript
9. **Quality assessment** → various text qualities
10. **Language detection** → Tamil, English, mixed

---

## Dependencies

```
easyocr>=1.7.0           # OCR (local)
pytesseract>=0.3.10      # OCR (local, requires tesseract binary)
Pillow>=10.0.0           # Image handling
PyMuPDF>=1.23.0          # PDF extraction
pdfplumber>=0.10.0       # PDF extraction (tables)
openai-whisper>=20231117 # ASR (local)
httpx>=0.25.0            # HTTP client
beautifulsoup4>=4.12.0   # HTML parsing
youtube-transcript-api>=0.6.0  # YouTube transcripts

# Optional (paid APIs)
# google-cloud-vision
# google-cloud-speech
# azure-cognitiveservices-speech
```
