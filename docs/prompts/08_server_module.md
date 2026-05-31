# PROMPT: Build Server Module (FastAPI + Pipeline)

## Context Files (Attach These)

Upload/attach these files before pasting this prompt:
1. `implementation_plan.md` — The master architecture document
2. `module_server.md` — Detailed spec for this module

Also make sure the **Core module code** already exists in the workspace at `tamil-entity-system/backend/core/` and `tamil-entity-system/backend/config/`. All processing modules (input, transliteration, extraction, research, explanation, response) should also be in place at `backend/modules/`.

---

## Prompt (Paste Everything Below)

---

You are building the **Server Module** for a Tamil Entity Recognition system. This includes the FastAPI application, all REST API routes, WebSocket for real-time updates, and the Pipeline Orchestrator that chains all processing modules together.

### STEP 0: READ AND UNDERSTAND

1. Read **`implementation_plan.md`** — Focus on the API endpoints table, data flow diagram, and directory structure.
2. Read **`module_server.md`** — Your complete spec with all routes and the orchestrator.
3. Read the **existing code** in the workspace:
   - `backend/core/` — All core classes (Database, VectorStore, Settings, BaseAgent, LLMClient, etc.)
   - `backend/core/llm_client.py` — LLMClient initialization (app.py creates this for ExplanationAgent)
   - `backend/core/database.py` — Database + VectorStore classes (app.py creates both at startup)
   - `backend/config/default_config.yaml` — Full configuration
   - `backend/modules/input/coordinator.py` — InputCoordinator class
   - `backend/modules/transliteration/agent.py` — TransliterationAgent class
   - `backend/modules/discovery/agent.py` — CandidateDiscoveryAgent class (optional, check if enabled)
   - `backend/modules/extraction/agent.py` — EntityExtractionAgent class
   - `backend/modules/research/agent.py` — EntityResearchAgent class
   - `backend/modules/explanation/agent.py` — ExplanationAgent class
   - `backend/modules/response/builder.py` — ResponseBuilder class
   
   You need to understand the constructor signatures and `execute(state)` method of each agent to wire them together in the orchestrator.

### FILES TO CREATE

```
backend/pipeline/
├── __init__.py
└── orchestrator.py          # PipelineOrchestrator — chains all modules

backend/server/
├── __init__.py
├── app.py                   # FastAPI app factory with startup/shutdown
├── middleware.py             # ErrorHandlingMiddleware, RequestTimingMiddleware
├── websocket.py              # WebSocket for real-time status updates
└── routes/
    ├── __init__.py
    ├── process.py            # POST /api/process, GET /api/process/{id}
    ├── entities.py           # GET/DELETE /api/entities
    ├── config.py             # GET/PUT /api/config
    ├── sources.py            # GET/POST/PUT/DELETE /api/sources
    ├── feedback.py           # POST/GET /api/feedback
    ├── db_admin.py           # GET/PUT/DELETE /api/db/{table}
    └── health.py             # GET /api/health, GET /api/stats

backend/main.py               # Entry point: uvicorn runner

backend/tests/module/
└── test_server_module.py
```

### IMPLEMENTATION RULES

1. **Pipeline Orchestrator** (`pipeline/orchestrator.py`):
   - Initialize ALL module agents in constructor
   - `run(request_id, input_type, input_content, input_metadata)` method:
     a. Create initial state via `create_initial_state()`
     b. Execute each stage in order: Input → Transliteration → Discovery (if enabled) → Extraction → Research → Explanation → Response
     c. Time each stage, store in `state['stage_timings']`
     d. Send WebSocket updates at each stage transition
     e. On error: log to `state['errors']`, set `state['processing_status'] = 'failed'`, break pipeline
     f. Return `state.get('final_response', state)`
   - The orchestrator must import and instantiate agents:
     ```python
     from modules.input import InputCoordinator
     from modules.transliteration import TransliterationAgent
     from modules.extraction import EntityExtractionAgent
     from modules.research import EntityResearchAgent
     from modules.explanation import ExplanationAgent
     from modules.response import ResponseBuilder
     ```

2. **FastAPI app** (`server/app.py`):
   - Use `create_app()` factory function
   - Add CORS middleware (allow localhost:5173 and localhost:3000)
   - Add custom middleware (ErrorHandling, RequestTiming)
   - Include all route routers with `/api` prefix
   - Add WebSocket route at `/ws/process/{request_id}`
   - `startup` event: initialize Database, Settings, LLMClient, VectorStore, PipelineOrchestrator
   - `shutdown` event: close database connection
   - Store everything on `app.state`

3. **POST /api/process** — The main endpoint:
   - Accepts: `text` (Form), `url` (Form), `file` (UploadFile), `output_format` (Form, default "json")
   - Detect input type from content/file mime type
   - Generate request_id as UUID
   - Run pipeline
   - Format response in requested format
   - Return JSON response

4. **DB Admin routes** (`/api/db/{table}`):
   - ALLOWED_TABLES: list of all 10 table names
   - Reject requests for tables not in the list
   - Support pagination (page, per_page), search, sorting
   - Support GET (browse), GET (single row), PUT (update), DELETE (delete)

5. **WebSocket** (`server/websocket.py`):
   - Track active connections by request_id
   - `send_status_update(request_id, stage, message, progress)` function
   - Pipeline orchestrator calls this at each stage

6. **Middleware** (`server/middleware.py`):
   - `ErrorHandlingMiddleware`: catch unhandled exceptions → return JSON error
   - `RequestTimingMiddleware`: add `X-Process-Time` header

7. **main.py**:
   ```python
   import uvicorn
   from server.app import create_app
   app = create_app()
   if __name__ == "__main__":
       uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
   ```

### API ENDPOINTS TABLE (implement ALL of these)

| Method | Path | Purpose |
|--------|------|---------|
| POST | /api/process | Main processing |
| GET | /api/process/{request_id} | Get result |
| WS | /ws/process/{request_id} | Real-time status |
| GET | /api/entities | List entities |
| GET | /api/entities/{name} | Entity details |
| DELETE | /api/entities/{id} | Delete entity |
| GET | /api/config | Get config |
| PUT | /api/config/{key} | Update config |
| GET | /api/sources | List sources |
| POST | /api/sources | Register source |
| PUT | /api/sources/{name} | Update source |
| DELETE | /api/sources/{name} | Remove source |
| POST | /api/feedback | Submit feedback |
| GET | /api/feedback | List feedback |
| GET | /api/db | List tables |
| GET | /api/db/{table} | Browse table |
| GET | /api/db/{table}/{id} | Get row |
| PUT | /api/db/{table}/{id} | Update row |
| DELETE | /api/db/{table}/{id} | Delete row |
| GET | /api/health | Health check |
| GET | /api/stats | Statistics |

### TESTING RULES

1. Use `httpx.AsyncClient` with FastAPI's TestClient
2. Test POST /api/process with text input
3. Test GET /api/health returns 200
4. Test GET /api/config returns config dict
5. Test GET /api/db/{table} with valid and invalid table names
6. Run:
   ```bash
   cd tamil-entity-system/backend
   pytest tests/module/test_server_module.py -v
   ```

### FINAL CHECKLIST

- [ ] Pipeline orchestrator chains all 6 modules correctly
- [ ] All 21 API endpoints implemented
- [ ] POST /api/process handles text, file upload, and URL
- [ ] WebSocket sends stage updates during processing
- [ ] DB admin restricts access to allowed tables only
- [ ] Error middleware catches and formats exceptions
- [ ] CORS allows frontend origins
- [ ] main.py starts the server
- [ ] All tests pass
