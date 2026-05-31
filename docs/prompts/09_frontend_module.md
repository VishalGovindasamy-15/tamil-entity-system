# PROMPT: Build Frontend Module (React)

## Context Files (Attach These)

Upload/attach these files before pasting this prompt:
1. `implementation_plan.md` — The master architecture document
2. `module_frontend.md` — Detailed spec for the frontend

The **backend server** should be running at `http://localhost:8000` (or will be soon). You can build the frontend in parallel since you know all the API endpoints.

---

## Prompt (Paste Everything Below)

---

You are building the **React Frontend** for a Tamil Entity Recognition system. The backend is a FastAPI server at `http://localhost:8000`. You will build a complete SPA with 6 pages, API integration, and WebSocket support for real-time processing updates.

### STEP 0: READ AND UNDERSTAND

1. Read **`implementation_plan.md`** — Focus on the API endpoints table and data flow.
2. Read **`module_frontend.md`** — Your complete spec with all pages, components, and API services.

### PROJECT SETUP

Initialize a Vite + React project:
```bash
cd tamil-entity-system
npx -y create-vite@latest frontend -- --template react
cd frontend
npm install react-router-dom@6 axios zustand
```

### DIRECTORY STRUCTURE

```
frontend/src/
├── components/
│   ├── layout/
│   │   ├── Navbar.jsx         # Top navigation with page links
│   │   ├── Sidebar.jsx        # Optional sidebar
│   │   └── Layout.jsx         # Main layout wrapper
│   ├── common/
│   │   ├── ToggleSwitch.jsx   # Reusable on/off toggle
│   │   ├── ConfidenceMeter.jsx # Visual confidence bar (0-100%)
│   │   ├── JsonViewer.jsx     # Collapsible JSON tree viewer
│   │   ├── DataGrid.jsx       # Reusable data table with sorting
│   │   ├── Pagination.jsx     # Page controls
│   │   ├── Modal.jsx          # Reusable modal dialog
│   │   ├── LoadingSpinner.jsx # Loading indicator
│   │   └── StatusBadge.jsx    # Colored status indicator
│   ├── home/
│   │   ├── TextInput.jsx      # Large textarea with Tamil font support
│   │   ├── FileUploader.jsx   # Drag-and-drop file upload
│   │   ├── URLInput.jsx       # URL input with validation
│   │   └── ProcessingStatus.jsx # Real-time stage progress via WebSocket
│   ├── results/
│   │   ├── EntityCard.jsx     # Entity display card with confidence
│   │   ├── ExplanationTabs.jsx # Tamil/English tab switcher
│   │   ├── FactsTable.jsx     # Verified facts display table
│   │   ├── SourcesList.jsx    # Source attribution with credibility
│   │   └── FeedbackBar.jsx    # Correct/Incorrect/Report buttons
│   ├── db/
│   │   ├── TableSelector.jsx  # Dropdown to pick DB table
│   │   ├── EditModal.jsx      # Row edit form in modal
│   │   └── RowDetails.jsx     # Expanded row view
│   └── config/
│       ├── ConfigSection.jsx  # Group of config items
│       └── ConfigItem.jsx     # Single toggleable config item
├── pages/
│   ├── HomePage.jsx           # Content submission
│   ├── ResultsPage.jsx        # Entity results display
│   ├── DBAdminPage.jsx        # Database browser
│   ├── ConfigPage.jsx         # Configuration management
│   ├── SourcesPage.jsx        # Research source management
│   └── StatsPage.jsx          # System statistics
├── services/
│   └── api.js                 # Axios API client
├── hooks/
│   ├── useProcessingStatus.js # WebSocket hook for real-time updates
│   └── useConfig.js           # Config fetching hook
├── stores/
│   └── appStore.js            # Zustand global state
├── styles/
│   └── index.css              # Global styles + Tamil font import
├── App.jsx                    # Router setup
└── main.jsx                   # Entry point
```

Also create these config files at the frontend root:

**`frontend/vite.config.js`** — API proxy (avoids CORS issues during dev):
```javascript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
    },
  },
})
```

**`frontend/.env`** — Environment config:
```
VITE_API_BASE=http://localhost:8000/api
VITE_WS_BASE=ws://localhost:8000/ws
```

### BACKEND API ENDPOINTS (your API contract)

The backend provides these endpoints at `http://localhost:8000`:

| Method | Path | Purpose | Request | Response |
|--------|------|---------|---------|----------|
| POST | /api/process | Process content | FormData: text/file/url + output_format | `{entities, summary, ...}` |
| GET | /api/process/{id} | Get result | — | Full result JSON |
| GET | /api/entities | List entities | ?page=1&per_page=20&search=&entity_type= | `[{entity objects}]` |
| GET | /api/entities/{name} | Entity detail | — | Full entity knowledge |
| DELETE | /api/entities/{id} | Delete entity | — | `{status: "deleted"}` |
| GET | /api/config | Get config | — | Full YAML config as JSON |
| PUT | /api/config/{key} | Update config | `{value: "..."}` | `{status: "updated"}` |
| GET | /api/sources | List sources | — | `[{source objects with status}]` |
| POST | /api/sources | Register source | Source config JSON | `{status: "registered"}` |
| PUT | /api/sources/{name} | Update source | `{enabled: bool, ...}` | `{status: "updated"}` |
| DELETE | /api/sources/{name} | Remove source | — | `{status: "removed"}` |
| POST | /api/feedback | Submit feedback | `{entity, rating, correction}` | `{status: "received"}` |
| GET | /api/feedback | List feedback | ?page=1&per_page=20 | `[{feedback objects}]` |
| GET | /api/db | List tables | — | `[{table, row_count}]` |
| GET | /api/db/{table} | Browse table | ?page=1&per_page=50&sort_by=&sort_order=desc | `{table, total, rows}` |
| PUT | /api/db/{table}/{id} | Update row | `{field: value, ...}` | `{status: "updated"}` |
| DELETE | /api/db/{table}/{id} | Delete row | — | `{status: "deleted"}` |
| GET | /api/health | Health check | — | `{status: "healthy"}` |
| GET | /api/stats | Statistics | — | `{total_requests, total_entities, ...}` |
| WS | /ws/process/{id} | Real-time updates | — | `{stage, message, progress}` |

### IMPLEMENTATION RULES

1. **API Service** (`services/api.js`):
   ```javascript
   import axios from 'axios';
   const API_BASE = import.meta.env.VITE_API_BASE || '/api';
   export const api = {
       process: (formData) => axios.post(`${API_BASE}/process`, formData),
       getResult: (requestId) => axios.get(`${API_BASE}/process/${requestId}`),
       // ... ALL endpoints listed above
   };
   ```

2. **WebSocket Hook** (`hooks/useProcessingStatus.js`):
   - Connect to `${import.meta.env.VITE_WS_BASE || 'ws://localhost:8000/ws'}/process/{requestId}`
   - Track current stage, progress percentage, and stage history
   - Auto-close on unmount
   - Return `{ status, stages, isConnected }`

3. **Home Page** — Content submission:
   - Large textarea with `font-family: 'Noto Sans Tamil', sans-serif`
   - Drag-and-drop file upload supporting: image/*, .pdf, audio/*, video/*
   - URL input with validation
   - Output format radio buttons (JSON, HTML, PDF, Markdown)
   - Submit button → calls POST /api/process → redirects to results page
   - ProcessingStatus component shows real-time stage progress via WebSocket

4. **Results Page** (`/results/:requestId`):
   - Entity cards with type badges, confidence meters
   - Expandable Tamil/English explanation tabs
   - Facts table with source attribution
   - Feedback buttons (correct/incorrect) per entity
   - Export buttons (download as JSON, HTML, PDF)

5. **DB Admin Page** (`/db`):
   - Table selector dropdown (10 tables)
   - DataGrid with pagination, sorting, search
   - Click row → expand details
   - Edit button → EditModal
   - Delete button → confirmation dialog
   - JSON viewer for complex fields

6. **Config Page** (`/config`):
   - Grouped sections: Input, Transliteration, Extraction, Research, Explanation
   - Toggle switches for each API/processor
   - Save button → calls PUT /api/config/{key} for each changed value
   - Reset button

7. **Sources Page** (`/sources`):
   - Source cards with status badges (healthy/unhealthy/disabled)
   - Credibility meter
   - Enable/disable toggle
   - Register new source form

8. **Stats Page** (`/stats`):
   - Big number cards (total requests, entities, etc.)
   - Recent requests table

### STYLING RULES

1. Import Tamil font in `index.css`:
   ```css
   @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Tamil:wght@400;600;700&family=Inter:wght@400;500;600;700&display=swap');
   ```

2. Use CSS variables for theming (dark mode support)
3. Modern card-based layout with subtle shadows
4. Color-coded entity type badges:
   - PERSON → blue, ORGANIZATION → purple, LOCATION → green, DATE → orange, EVENT → red
5. Smooth transitions and hover effects
6. Responsive layout (desktop + tablet)

### FINAL CHECKLIST

- [ ] All 6 pages render without errors
- [ ] Home page submits text, file, and URL inputs correctly
- [ ] Results page displays entities with Tamil + English explanations
- [ ] DB Admin page browses all 10 tables with pagination
- [ ] Config page toggles APIs and saves to backend
- [ ] Sources page lists and manages research sources
- [ ] Stats page shows system statistics
- [ ] WebSocket shows real-time processing progress
- [ ] Tamil text renders correctly with Noto Sans Tamil font
- [ ] API service covers all endpoints
- [ ] Design is modern, clean, and professional
