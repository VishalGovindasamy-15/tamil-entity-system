"""
SystemState TypedDict — the shared pipeline state flowing through every module.
"""
from typing import TypedDict, List, Dict, Any
from datetime import datetime, timezone
import uuid


class SystemState(TypedDict):
    """Pipeline state dictionary passed through every processing stage."""
    # Request identifiers
    request_id: str
    session_id: str
    started_at: str          # ISO-8601 timestamp
    started_at_epoch: float  # time.time() for duration calculation

    # Input
    input_type: str          # 'text' | 'image' | 'pdf' | 'audio' | 'video' | 'url'
    input_content: Any       # raw content or file path
    input_metadata: Dict[str, Any]

    # Processing control
    current_stage: str
    processing_status: str   # 'pending' | 'processing' | 'completed' | 'failed'

    # Text (output of Input module)
    raw_text: str
    normalized_text: str
    detected_language: str
    detected_scripts: List[str]

    # Transliteration (output of Transliteration module)
    transliteration_map: Dict[str, str]
    transliteration_confidence: Dict[str, float]

    # Entities (output of Extraction module)
    entities: List[Dict[str, Any]]

    # Knowledge (output of Research module)
    entity_knowledge: Dict[str, Dict[str, Any]]

    # Explanations (output of Explanation module)
    explanations: Dict[str, Dict[str, Any]]

    # Metrics
    processing_steps: List[str]
    api_calls_made: int
    cache_hits: int
    sources_accessed: int
    errors: List[Dict[str, Any]]
    warnings: List[str]
    stage_timings: Dict[str, float]

    # Quality
    overall_confidence: float
    quality_score: float

    # Config snapshot
    config: Dict[str, Any]

    # Final output (set by Response module)
    final_response: Dict[str, Any]


def create_initial_state(
    request_id: str,
    input_type: str,
    input_content: Any,
    input_metadata: Dict[str, Any] = None,
    config: Dict[str, Any] = None,
) -> SystemState:
    """Factory function to create a properly initialized state.

    Every field is set to a safe default so downstream modules never
    encounter missing keys.
    """
    import time

    now = datetime.now(timezone.utc)
    return SystemState(
        request_id=request_id,
        session_id=str(uuid.uuid4()),
        started_at=now.isoformat(),
        started_at_epoch=time.time(),
        input_type=input_type,
        input_content=input_content,
        input_metadata=input_metadata or {},
        current_stage="initialized",
        processing_status="pending",
        raw_text="",
        normalized_text="",
        detected_language="",
        detected_scripts=[],
        transliteration_map={},
        transliteration_confidence={},
        entities=[],
        entity_knowledge={},
        explanations={},
        processing_steps=[],
        api_calls_made=0,
        cache_hits=0,
        sources_accessed=0,
        errors=[],
        warnings=[],
        stage_timings={},
        overall_confidence=0.0,
        quality_score=0.0,
        config=config or {},
        final_response={},
    )
