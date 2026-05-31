# Module 8: Server (FastAPI)

## Purpose
FastAPI server exposing all functionality via REST API + WebSocket. Routes to the pipeline orchestrator and provides CRUD for all database tables.

---

## Files

### `server/app.py` — FastAPI Application

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

def create_app() -> FastAPI:
    app = FastAPI(
        title="Tamil Entity Recognition API",
        description="Identify and explain entities in Tamil content",
        version="1.0.0"
    )
    
    # CORS (allow frontend)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:3000"],
        allow_methods=["*"],
        allow_headers=["*"]
    )
    
    # Include routers
    from server.routes import process, entities, config, sources, feedback, db_admin, health
    app.include_router(process.router, prefix="/api")
    app.include_router(entities.router, prefix="/api")
    app.include_router(config.router, prefix="/api")
    app.include_router(sources.router, prefix="/api")
    app.include_router(feedback.router, prefix="/api")
    app.include_router(db_admin.router, prefix="/api")
    app.include_router(health.router, prefix="/api")
    
    # WebSocket
    from server.websocket import websocket_endpoint
    app.add_api_websocket_route("/ws/process/{request_id}", websocket_endpoint)
    
    # Startup/shutdown
    @app.on_event("startup")
    async def startup():
        app.state.db = Database(...)
        await app.state.db.initialize()
        app.state.config = Settings(...)
        app.state.config.load()
        app.state.pipeline = PipelineOrchestrator(app.state.db, app.state.config)
    
    @app.on_event("shutdown")
    async def shutdown():
        await app.state.db.close()
    
    return app
```

---

### `server/middleware.py` — CORS & Error Handling

```python
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import time
import traceback

class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Global error handler — catches unhandled exceptions, returns JSON"""
    
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={
                    "error": str(e),
                    "detail": traceback.format_exc() if request.app.debug else None
                }
            )

class RequestTimingMiddleware(BaseHTTPMiddleware):
    """Add X-Process-Time header to all responses"""
    
    async def dispatch(self, request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        response.headers["X-Process-Time"] = f"{time.time() - start:.4f}"
        return response

# Used in app.py:
# app.add_middleware(ErrorHandlingMiddleware)
# app.add_middleware(RequestTimingMiddleware)
```

**Tests:**
- Test error middleware catches exceptions and returns JSON
- Test timing header is present on responses

---

### `server/routes/process.py` — Main Processing Endpoint

```python
router = APIRouter(tags=["Processing"])

@router.post("/process")
async def process_content(
    request: Request,
    text: Optional[str] = Form(None),
    url: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    output_format: str = Form("json")
):
    """
    Main processing endpoint.
    Accepts text, URL, or file upload (image/PDF/audio/video).
    """
    pipeline = request.app.state.pipeline
    
    # Determine input type
    if text:
        input_type, content = "text", text
    elif url:
        input_type, content = "url", url
    elif file:
        input_type = detect_file_type(file.content_type)  # image/pdf/audio/video
        content = await file.read()
    else:
        raise HTTPException(400, "No input provided")
    
    # Create request
    request_id = str(uuid.uuid4())
    
    # Run pipeline (async)
    result = await pipeline.run(
        request_id=request_id,
        input_type=input_type,
        input_content=content,
        input_metadata={"filename": file.filename if file else None}
    )
    
    # Format response
    formatted = pipeline.format_response(result, output_format)
    
    return JSONResponse(content=formatted)


@router.get("/process/{request_id}")
async def get_result(request_id: str, request: Request):
    """Get processing result by request ID"""
    db = request.app.state.db
    result = await db.fetchone(
        "SELECT * FROM processing_requests WHERE request_id = ?", request_id
    )
    if not result:
        raise HTTPException(404, "Request not found")
    return result
```

---

### `server/routes/entities.py` — Entity CRUD

```python
router = APIRouter(tags=["Entities"])

@router.get("/entities")
async def list_entities(
    request: Request,
    page: int = 1,
    per_page: int = 20,
    search: Optional[str] = None,
    entity_type: Optional[str] = None
):
    """List all known entities with filtering"""
    ...

@router.get("/entities/{entity_name}")
async def get_entity(entity_name: str, request: Request):
    """Get detailed entity knowledge"""
    ...

@router.delete("/entities/{entity_id}")
async def delete_entity(entity_id: int, request: Request):
    """Delete entity from knowledge base"""
    ...
```

---

### `server/routes/config.py` — Configuration Management

```python
router = APIRouter(tags=["Configuration"])

@router.get("/config")
async def get_config(request: Request):
    """Get current configuration"""
    return request.app.state.config.to_dict()

@router.put("/config/{key}")
async def update_config(key: str, value: str, request: Request):
    """Update a config value (stored in system_config DB table)"""
    db = request.app.state.db
    await db.execute(
        "INSERT OR REPLACE INTO system_config (config_key, config_value) VALUES (?, ?)",
        key, value
    )
    # Reload config
    request.app.state.config.set(key, value)
    return {"status": "updated", "key": key, "value": value}
```

---

### `server/routes/sources.py` — Source Management

```python
router = APIRouter(tags=["Sources"])

@router.get("/sources")
async def list_sources(request: Request):
    """List all research sources with their status and credibility"""
    ...

@router.post("/sources")
async def register_source(source_config: SourceRegistration, request: Request):
    """Register a custom source (API, web scraper, or database)"""
    ...

@router.put("/sources/{source_name}")
async def update_source(source_name: str, updates: Dict, request: Request):
    """Enable/disable a source, update config"""
    ...

@router.delete("/sources/{source_name}")
async def remove_source(source_name: str, request: Request):
    """Remove a custom source"""
    ...

@router.get("/sources/{source_name}/health")
async def check_source_health(source_name: str, request: Request):
    """Health check for a specific source"""
    ...
```

---

### `server/routes/feedback.py` — User Feedback

```python
router = APIRouter(tags=["Feedback"])

@router.post("/feedback")
async def submit_feedback(feedback: FeedbackSubmission, request: Request):
    """Submit user feedback on entity results"""
    ...

@router.get("/feedback")
async def list_feedback(request: Request, page: int = 1, per_page: int = 20):
    """List recent feedback"""
    ...
```

---

### `server/routes/db_admin.py` — Database Browser

```python
router = APIRouter(tags=["DB Admin"])

ALLOWED_TABLES = [
    "entity_knowledge", "learned_transliterations", "source_credibility",
    "api_performance", "user_feedback", "processing_requests",
    "agent_learning_log", "system_config", "custom_sources",
    "custom_input_processors"
]

@router.get("/db/{table}")
async def browse_table(
    table: str, request: Request,
    page: int = 1, per_page: int = 50,
    search: Optional[str] = None,
    sort_by: Optional[str] = None,
    sort_order: str = "desc"
):
    """Browse any DB table with pagination, search, and sorting"""
    if table not in ALLOWED_TABLES:
        raise HTTPException(400, f"Table '{table}' not accessible")
    
    offset = (page - 1) * per_page
    
    # Count total
    total = await db.fetchval(f"SELECT COUNT(*) FROM {table}")
    
    # Fetch page
    query = f"SELECT * FROM {table}"
    if sort_by:
        query += f" ORDER BY {sort_by} {sort_order}"
    query += f" LIMIT {per_page} OFFSET {offset}"
    
    rows = await db.fetchall(query)
    
    return {
        "table": table,
        "total": total,
        "page": page,
        "per_page": per_page,
        "rows": rows
    }

@router.get("/db/{table}/{row_id}")
async def get_row(table: str, row_id: int, request: Request):
    """Get single row"""
    ...

@router.put("/db/{table}/{row_id}")
async def update_row(table: str, row_id: int, updates: Dict, request: Request):
    """Update a row"""
    ...

@router.delete("/db/{table}/{row_id}")
async def delete_row(table: str, row_id: int, request: Request):
    """Delete a row"""
    ...

@router.get("/db")
async def list_tables(request: Request):
    """List all tables with row counts"""
    ...
```

---

### `server/routes/health.py`

```python
router = APIRouter(tags=["Health"])

@router.get("/health")
async def health_check(request: Request):
    """System health check"""
    return {
        "status": "healthy",
        "database": "connected",
        "uptime_seconds": ...,
        "version": "1.0.0"
    }

@router.get("/stats")
async def system_stats(request: Request):
    """Processing statistics"""
    db = request.app.state.db
    return {
        "total_requests": await db.fetchval("SELECT COUNT(*) FROM processing_requests"),
        "total_entities": await db.fetchval("SELECT COUNT(*) FROM entity_knowledge"),
        "total_transliterations": await db.fetchval("SELECT COUNT(*) FROM learned_transliterations"),
        "sources_active": await db.fetchval("SELECT COUNT(*) FROM source_credibility WHERE is_active = 1"),
        ...
    }
```

---

### `server/websocket.py` — Real-time Status

```python
from fastapi import WebSocket

# Active connections
connections: Dict[str, WebSocket] = {}

async def websocket_endpoint(websocket: WebSocket, request_id: str):
    await websocket.accept()
    connections[request_id] = websocket
    
    try:
        while True:
            await websocket.receive_text()  # Keep alive
    except WebSocketDisconnect:
        del connections[request_id]

async def send_status_update(request_id: str, stage: str, message: str, progress: float):
    """Called by pipeline to send real-time updates"""
    ws = connections.get(request_id)
    if ws:
        await ws.send_json({
            "request_id": request_id,
            "stage": stage,
            "message": message,
            "progress": progress,
            "timestamp": datetime.now().isoformat()
        })
```

---

### `pipeline/orchestrator.py` — Pipeline Orchestrator

```python
class PipelineOrchestrator:
    def __init__(self, db, config):
        self.db = db
        self.config = config
        
        # Initialize all modules
        self.input_coordinator = InputCoordinator(db, config)
        self.transliteration_agent = TransliterationAgent(db, config, vector_store)
        self.extraction_agent = EntityExtractionAgent(db, config)
        self.research_agent = EntityResearchAgent(db, config, vector_store)
        self.explanation_agent = ExplanationAgent(db, config, llm_client)
        self.response_builder = ResponseBuilder(db, config)
    
    async def run(self, request_id, input_type, input_content, input_metadata) -> Dict:
        """Run full pipeline"""
        
        state = create_initial_state(request_id, input_type, input_content, input_metadata)
        
        stages = [
            ("input_processing", self.input_coordinator),
            ("transliteration", self.transliteration_agent),
            ("entity_extraction", self.extraction_agent),
            ("entity_research", self.research_agent),
            ("explanation_generation", self.explanation_agent),
            ("response_compilation", self.response_builder),
        ]
        
        for stage_name, agent in stages:
            state['current_stage'] = stage_name
            start = time.time()
            
            try:
                # Send WebSocket update
                await send_status_update(request_id, stage_name, f"Starting {stage_name}", ...)
                
                state = await agent.execute(state)
                
                state['stage_timings'][stage_name] = time.time() - start
            except Exception as e:
                state['errors'].append({"stage": stage_name, "error": str(e)})
                state['processing_status'] = 'failed'
                break
        
        return state.get('final_response', state)
```

---

### `main.py` — Entry Point

```python
import uvicorn
from server.app import create_app

app = create_app()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
```

---

## Module-Level Test (`tests/module/test_server_module.py`)

Using `httpx.AsyncClient` with FastAPI's `TestClient`:

1. `POST /api/process` with text → full pipeline → JSON response
2. `POST /api/process` with file upload → processes correctly
3. `GET /api/entities` → lists entities
4. `GET /api/config` → returns config
5. `PUT /api/config/extraction.confidence_threshold` → updates config
6. `GET /api/sources` → lists sources with status
7. `POST /api/sources` → registers custom source
8. `GET /api/db/entity_knowledge` → browses table
9. `GET /api/health` → returns healthy status
10. `GET /api/stats` → returns statistics

---

## Dependencies

```
fastapi>=0.109.0
uvicorn>=0.25.0
python-multipart>=0.0.6    # File uploads
```
