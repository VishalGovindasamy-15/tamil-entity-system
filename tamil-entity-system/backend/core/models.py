"""
SQLite schema definitions and seed data for all 10 database tables.
"""

TABLES = {
    "learned_transliterations": """
        CREATE TABLE IF NOT EXISTS learned_transliterations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            roman_text TEXT NOT NULL UNIQUE,
            tamil_word TEXT NOT NULL,
            confidence REAL NOT NULL DEFAULT 0.0,
            source_apis TEXT DEFAULT '[]',
            usage_count INTEGER DEFAULT 1,
            last_used_at TEXT DEFAULT (datetime('now')),
            created_at TEXT DEFAULT (datetime('now'))
        )
    """,

    "entity_knowledge": """
        CREATE TABLE IF NOT EXISTS entity_knowledge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_name TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            language TEXT DEFAULT 'ta',
            verified_facts TEXT DEFAULT '{}',
            sources_consulted TEXT DEFAULT '[]',
            overall_confidence REAL DEFAULT 0.0,
            fact_count INTEGER DEFAULT 0,
            source_count INTEGER DEFAULT 0,
            related_entities TEXT DEFAULT '[]',
            last_updated_at TEXT DEFAULT (datetime('now')),
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(entity_name, language)
        )
    """,

    "source_credibility": """
        CREATE TABLE IF NOT EXISTS source_credibility (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_name TEXT NOT NULL UNIQUE,
            source_type TEXT NOT NULL,
            base_credibility REAL NOT NULL DEFAULT 0.70,
            current_credibility REAL NOT NULL DEFAULT 0.70,
            total_queries INTEGER DEFAULT 0,
            successful_queries INTEGER DEFAULT 0,
            failed_queries INTEGER DEFAULT 0,
            avg_response_time_ms INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            last_health_check TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """,

    "api_performance": """
        CREATE TABLE IF NOT EXISTS api_performance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            api_name TEXT NOT NULL,
            endpoint TEXT NOT NULL,
            method TEXT DEFAULT 'GET',
            status_code INTEGER,
            response_time_ms INTEGER NOT NULL,
            success INTEGER NOT NULL DEFAULT 1,
            error_message TEXT,
            request_size_bytes INTEGER DEFAULT 0,
            response_size_bytes INTEGER DEFAULT 0,
            recorded_at TEXT DEFAULT (datetime('now'))
        )
    """,

    "user_feedback": """
        CREATE TABLE IF NOT EXISTS user_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id TEXT NOT NULL,
            entity_name TEXT,
            feedback_type TEXT NOT NULL,
            rating INTEGER,
            correction TEXT,
            original_value TEXT,
            corrected_value TEXT,
            comment TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """,

    "processing_requests": """
        CREATE TABLE IF NOT EXISTS processing_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id TEXT NOT NULL UNIQUE,
            input_type TEXT NOT NULL,
            input_size_bytes INTEGER DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'pending',
            total_entities_found INTEGER DEFAULT 0,
            total_processing_time_ms INTEGER DEFAULT 0,
            total_api_calls INTEGER DEFAULT 0,
            total_cache_hits INTEGER DEFAULT 0,
            result_json TEXT,
            error_message TEXT,
            started_at TEXT DEFAULT (datetime('now')),
            completed_at TEXT
        )
    """,

    "agent_learning_log": """
        CREATE TABLE IF NOT EXISTS agent_learning_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_name TEXT NOT NULL,
            event_type TEXT NOT NULL,
            entity_name TEXT,
            old_value TEXT,
            new_value TEXT,
            confidence_change REAL DEFAULT 0.0,
            details TEXT DEFAULT '{}',
            created_at TEXT DEFAULT (datetime('now'))
        )
    """,

    "system_config": """
        CREATE TABLE IF NOT EXISTS system_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            config_key TEXT NOT NULL UNIQUE,
            category TEXT NOT NULL DEFAULT 'general',
            config_value TEXT NOT NULL,
            value_type TEXT NOT NULL DEFAULT 'string',
            description TEXT,
            updated_at TEXT DEFAULT (datetime('now')),
            created_at TEXT DEFAULT (datetime('now'))
        )
    """,

    "custom_sources": """
        CREATE TABLE IF NOT EXISTS custom_sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_name TEXT NOT NULL UNIQUE,
            source_type TEXT NOT NULL,
            config_json TEXT NOT NULL DEFAULT '{}',
            is_active INTEGER DEFAULT 1,
            credibility REAL DEFAULT 0.50,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """,

    "custom_input_processors": """
        CREATE TABLE IF NOT EXISTS custom_input_processors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            processor_name TEXT NOT NULL UNIQUE,
            processor_type TEXT NOT NULL,
            config_json TEXT NOT NULL DEFAULT '{}',
            is_active INTEGER DEFAULT 1,
            priority INTEGER DEFAULT 500,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """,
}


# Default config values seeded into system_config table on first run.
# Format: (config_key, category, config_value, value_type)
SEED_CONFIG = [
    ("processing.max_concurrent_entities", "processing", "10", "integer"),
    ("processing.request_timeout_seconds", "processing", "300", "integer"),
    ("processing.max_retries", "processing", "3", "integer"),
    ("processing.cache_ttl_days", "processing", "7", "integer"),
    ("transliteration.confidence_threshold", "transliteration", "0.85", "decimal"),
    ("extraction.confidence_threshold", "extraction", "0.85", "decimal"),
    ("extraction.use_ensemble", "extraction", "true", "boolean"),
    ("research.confidence_threshold", "research", "0.85", "decimal"),
    ("research.source_timeout_seconds", "research", "10", "integer"),
    ("research.min_sources_required", "research", "2", "integer"),
    ("explanation.min_word_count", "explanation", "400", "integer"),
    ("explanation.max_word_count", "explanation", "600", "integer"),
    ("explanation.hallucination_check", "explanation", "true", "boolean"),
    ("explanation.strict_retry", "explanation", "true", "boolean"),
]


# Built-in research sources seeded into source_credibility table.
# Format: (source_name, source_type, base_credibility, is_active)
SEED_SOURCES = [
    ("wikipedia", "reference", 0.95, True),
    ("wikidata", "reference", 0.98, True),
    ("dbpedia", "reference", 0.90, True),
    ("google_kg", "api", 0.90, False),
    ("web_search", "search", 0.70, True),
    ("news", "news", 0.75, False),
    ("youtube", "media", 0.60, False),
    ("tamil_sources", "reference", 0.85, True),
    ("government", "official", 0.95, False),
    ("academic", "academic", 0.90, False),
    ("llm_knowledge", "llm", 0.60, True),
]
