# Module 9: Frontend (React)

## Purpose
React SPA providing the user interface for content submission, entity result viewing, database management, configuration, and system monitoring.

---

## Technology

| Tool | Version | Purpose |
|------|---------|---------|
| React | 18+ | UI framework |
| Vite | 5+ | Build tool |
| React Router | 6+ | Navigation |
| Zustand | 4+ | State management (lightweight) |
| Axios | 1+ | API client |

---

## Pages & Components

### Page 1: Home / Submit (`/`)

**Features:**
- Text input area (large textarea for Tamil/English/mixed text)
- File upload zone (drag-and-drop, accepts: images, PDFs, audio, video)
- URL input field
- Output format selector (JSON, HTML, PDF, Markdown)
- Submit button
- Real-time processing status (via WebSocket)

**Components:**
```
HomePage
├── TextInput           # Large textarea with Tamil font support
├── FileUploader        # Drag-and-drop zone with file type icons
├── URLInput            # URL input with validation
├── FormatSelector      # Output format radio buttons
├── SubmitButton        # Submit with loading state
└── ProcessingStatus    # Real-time stage progress (WebSocket)
    ├── StageIndicator  # Current stage with icon + progress
    └── StageTimeline   # Visual timeline of all stages
```

---

### Page 2: Results (`/results/:requestId`)

**Features:**
- Input summary (what was submitted, language detected, scripts found)
- Entity list with cards
- Expandable entity details:
  - Tamil explanation (collapsible, with key points)
  - English explanation (collapsible, with key points)
  - Verified facts table
  - Source attribution (clickable URLs, credibility scores)
  - Confidence meter
  - Related entities (clickable links)
- Processing metrics (timing breakdown, API calls, cache hits)
- Feedback buttons (correct / incorrect / partial per entity)
- Export buttons (download as JSON / HTML / PDF)

**Components:**
```
ResultsPage
├── InputSummary            # What was submitted
├── EntityList
│   └── EntityCard          # One per entity
│       ├── EntityHeader    # Name, type badge, confidence meter
│       ├── ExplanationTabs # Tamil | English tabs
│       │   ├── TamilExplanation   # Full Tamil text + summary + key points
│       │   └── EnglishExplanation # Full English text + summary + key points
│       ├── FactsTable      # Verified facts with confidence
│       ├── SourcesList     # Source attribution with credibility
│       ├── RelatedEntities # Clickable related entities
│       └── FeedbackBar     # ✓ Correct | ✗ Incorrect | Report
├── ProcessingMetrics       # Timing, API calls, cache hits
└── ExportButtons           # JSON | HTML | PDF download
```

---

### Page 3: Database Admin (`/db`)

**Features:**
- Table selector (dropdown of all 10 tables)
- Data grid with:
  - Pagination (configurable per-page)
  - Column sorting (click header)
  - Search/filter bar
  - Row click to expand full details
  - Edit button per row → inline edit modal
  - Delete button per row → confirmation dialog
- Row count per table
- JSON viewer for JSONB fields

**Components:**
```
DBAdminPage
├── TableSelector          # Dropdown: entity_knowledge, learned_transliterations, etc.
├── SearchBar              # Filter rows by text
├── DataGrid
│   ├── GridHeader         # Column names, sortable
│   ├── GridRow            # Data row with actions
│   │   ├── JSONViewer     # Expandable JSON for JSONB columns
│   │   ├── EditButton     # Opens edit modal
│   │   └── DeleteButton   # Confirmation dialog
│   └── Pagination         # Page controls
├── EditModal              # Form for editing a row
└── TableStats             # Row count, last updated
```

**Tables accessible:**
1. `entity_knowledge` — Cached entity data
2. `learned_transliterations` — Roman→Tamil mappings
3. `source_credibility` — Source performance
4. `api_performance` — API metrics
5. `user_feedback` — User corrections
6. `processing_requests` — Request history
7. `agent_learning_log` — Learning events
8. `system_config` — Runtime config
9. `custom_sources` — Custom source plugins
10. `custom_input_processors` — Custom processors

---

### Page 4: Configuration (`/config`)

**Features:**
- Grouped config sections (Input, Transliteration, Extraction, Research, Explanation)
- Toggle switches for each API/processor
- Priority ordering (drag-and-drop or number input)
- API key fields (masked, with test button)
- Save button (persists to DB)
- Reset to defaults button

**Components:**
```
ConfigPage
├── ConfigSection          # One per group (Input, Transliteration, etc.)
│   ├── SectionHeader      # Group title
│   └── ConfigItem         # One per configurable item
│       ├── ToggleSwitch   # Enable/disable
│       ├── PriorityInput  # Number input for priority
│       ├── APIKeyInput    # Masked input + test button
│       └── ValueInput     # For thresholds, limits, etc.
├── SaveButton
└── ResetButton
```

**Config groups:**
- **Input Processors**: Toggle EasyOCR, Google Vision, Tesseract, Whisper, etc.
- **Transliteration APIs**: Toggle Google Translate, Indic, AI4Bharat
- **NER Models**: Toggle spaCy, Stanza, Google NLP, LLM fallback
- **Research Sources**: Toggle Wikipedia, Wikidata, DBpedia, DuckDuckGo, etc. by tier
- **Explanation**: Word count limits, hallucination check toggle
- **LLM Provider**: Select primary LLM (Gemini/GPT/Claude/Ollama)

---

### Page 5: Sources (`/sources`)

**Features:**
- List all research sources (built-in + custom)
- Status indicator (healthy/unhealthy/disabled)
- Credibility score
- Performance stats (success rate, avg response time)
- Register new custom source (API/Web Scraper/Database form)
- Health check button per source
- Enable/disable toggle

**Components:**
```
SourcesPage
├── SourceList
│   └── SourceCard
│       ├── StatusBadge
│       ├── CredibilityMeter
│       ├── StatsRow          # Success rate, response time
│       ├── ToggleSwitch      # Enable/disable
│       └── HealthCheckButton
├── RegisterSourceForm
│   ├── TypeSelector          # API | Web Scraper | Database
│   ├── APIConfigForm         # Endpoint, method, headers, etc.
│   ├── ScraperConfigForm     # URL template, selectors
│   └── DatabaseConfigForm    # Connection string, query
└── SourcePerformanceChart    # Optional: chart of credibility over time
```

---

### Page 6: Stats & Monitoring (`/stats`)

**Features:**
- Total requests processed
- Total entities in knowledge base
- Total transliterations learned
- Active sources count
- Recent processing requests (table)
- Entity type distribution (pie chart or bar)
- Average processing time

**Components:**
```
StatsPage
├── StatCards               # Big number cards
│   ├── TotalRequests
│   ├── TotalEntities
│   ├── TotalTransliterations
│   └── ActiveSources
├── RecentRequests          # Table of last 20 requests
├── EntityTypeChart         # Distribution chart
└── PerformanceChart        # Processing time trends
```

---

## API Service Layer (`src/services/`)

```javascript
// services/api.js
import axios from 'axios';

const API_BASE = 'http://localhost:8000/api';

export const api = {
  // Processing
  process: (formData) => axios.post(`${API_BASE}/process`, formData),
  getResult: (requestId) => axios.get(`${API_BASE}/process/${requestId}`),
  
  // Entities
  listEntities: (params) => axios.get(`${API_BASE}/entities`, { params }),
  getEntity: (name) => axios.get(`${API_BASE}/entities/${encodeURIComponent(name)}`),
  deleteEntity: (id) => axios.delete(`${API_BASE}/entities/${id}`),
  
  // Config
  getConfig: () => axios.get(`${API_BASE}/config`),
  updateConfig: (key, value) => axios.put(`${API_BASE}/config/${key}`, { value }),
  
  // Sources
  listSources: () => axios.get(`${API_BASE}/sources`),
  registerSource: (config) => axios.post(`${API_BASE}/sources`, config),
  updateSource: (name, updates) => axios.put(`${API_BASE}/sources/${name}`, updates),
  removeSource: (name) => axios.delete(`${API_BASE}/sources/${name}`),
  
  // Feedback
  submitFeedback: (feedback) => axios.post(`${API_BASE}/feedback`, feedback),
  
  // DB Admin
  listTables: () => axios.get(`${API_BASE}/db`),
  browseTable: (table, params) => axios.get(`${API_BASE}/db/${table}`, { params }),
  getRow: (table, id) => axios.get(`${API_BASE}/db/${table}/${id}`),
  updateRow: (table, id, data) => axios.put(`${API_BASE}/db/${table}/${id}`, data),
  deleteRow: (table, id) => axios.delete(`${API_BASE}/db/${table}/${id}`),
  
  // Health
  health: () => axios.get(`${API_BASE}/health`),
  stats: () => axios.get(`${API_BASE}/stats`),
};
```

---

## WebSocket Hook

```javascript
// hooks/useProcessingStatus.js
export function useProcessingStatus(requestId) {
  const [status, setStatus] = useState(null);
  const [stages, setStages] = useState([]);
  
  useEffect(() => {
    if (!requestId) return;
    
    const ws = new WebSocket(`ws://localhost:8000/ws/process/${requestId}`);
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setStatus(data);
      setStages(prev => [...prev, data]);
    };
    
    return () => ws.close();
  }, [requestId]);
  
  return { status, stages };
}
```

---

## Directory Structure

```
frontend/
├── public/
│   └── index.html
├── src/
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Navbar.jsx
│   │   │   ├── Sidebar.jsx
│   │   │   └── Layout.jsx
│   │   ├── common/
│   │   │   ├── ToggleSwitch.jsx
│   │   │   ├── ConfidenceMeter.jsx
│   │   │   ├── JsonViewer.jsx
│   │   │   ├── DataGrid.jsx
│   │   │   ├── Pagination.jsx
│   │   │   ├── Modal.jsx
│   │   │   ├── LoadingSpinner.jsx
│   │   │   └── StatusBadge.jsx
│   │   ├── home/
│   │   │   ├── TextInput.jsx
│   │   │   ├── FileUploader.jsx
│   │   │   ├── URLInput.jsx
│   │   │   └── ProcessingStatus.jsx
│   │   ├── results/
│   │   │   ├── EntityCard.jsx
│   │   │   ├── ExplanationTabs.jsx
│   │   │   ├── FactsTable.jsx
│   │   │   ├── SourcesList.jsx
│   │   │   └── FeedbackBar.jsx
│   │   ├── db/
│   │   │   ├── TableSelector.jsx
│   │   │   ├── EditModal.jsx
│   │   │   └── RowDetails.jsx
│   │   └── config/
│   │       ├── ConfigSection.jsx
│   │       └── ConfigItem.jsx
│   ├── pages/
│   │   ├── HomePage.jsx
│   │   ├── ResultsPage.jsx
│   │   ├── DBAdminPage.jsx
│   │   ├── ConfigPage.jsx
│   │   ├── SourcesPage.jsx
│   │   └── StatsPage.jsx
│   ├── services/
│   │   └── api.js
│   ├── hooks/
│   │   ├── useProcessingStatus.js
│   │   └── useConfig.js
│   ├── stores/
│   │   └── appStore.js          # Zustand store
│   ├── styles/
│   │   └── index.css            # Global styles, Tamil fonts
│   ├── App.jsx
│   └── main.jsx
├── package.json
└── vite.config.js
```

---

## Styling Notes

- **Tamil font**: Import `Noto Sans Tamil` from Google Fonts
- **Design**: Clean, modern, card-based layout
- **Responsive**: Works on desktop and tablet
- **Dark mode**: Optional toggle
- **Color scheme**: Professional blues/grays with accent colors for entity types

---

## Module-Level Test

Frontend testing with:
1. **Manual testing** — Run dev server, submit Tamil text, verify results display
2. **Component rendering** — Each page renders without errors
3. **API integration** — Mock API responses, verify data binding
4. **WebSocket** — Verify real-time status updates
5. **DB Admin** — Browse, edit, delete rows

---

## Dependencies

```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "axios": "^1.6.0",
    "zustand": "^4.4.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.2.0",
    "vite": "^5.0.0"
  }
}
```
