-- ============================================================
-- PERSONA AUTOMATION DATABASE SCHEMA
-- Version: 1.0 | Created: 2026-04-01
-- ============================================================

-- WEBSITES: Sites web testés
CREATE TABLE IF NOT EXISTS websites (
    id TEXT PRIMARY KEY,
    url TEXT NOT NULL UNIQUE,
    domain TEXT NOT NULL,
    type TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- WEBSITE_ANALYSES: Analyses LLM des sites
CREATE TABLE IF NOT EXISTS website_analyses (
    id TEXT PRIMARY KEY,
    website_id TEXT NOT NULL,
    description TEXT,
    features_detected TEXT,
    llm_provider TEXT NOT NULL,
    llm_model TEXT,
    analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (website_id) REFERENCES websites(id)
);

-- GENERATION_SESSIONS: Sessions de génération
CREATE TABLE IF NOT EXISTS generation_sessions (
    id TEXT PRIMARY KEY,
    website_id TEXT NOT NULL,
    personas_requested INTEGER NOT NULL,
    personas_generated INTEGER NOT NULL,
    llm_provider TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (website_id) REFERENCES websites(id)
);

-- PERSONAS: Personas générés ou manuels
CREATE TABLE IF NOT EXISTS personas (
    id TEXT PRIMARY KEY,
    website_id TEXT NOT NULL,
    nom TEXT NOT NULL,
    type_persona TEXT,
    device TEXT DEFAULT 'desktop',
    vitesse TEXT DEFAULT 'moyenne',
    patience_sec INTEGER DEFAULT 30,
    objectif TEXT,
    json_file_path TEXT,
    generated_by_llm BOOLEAN DEFAULT 1,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (website_id) REFERENCES websites(id)
);

-- TEST_RUNS: Exécutions de tests
CREATE TABLE IF NOT EXISTS test_runs (
    id TEXT PRIMARY KEY,
    persona_id TEXT NOT NULL,
    llm_provider TEXT NOT NULL,
    llm_model TEXT NOT NULL,
    status TEXT NOT NULL,
    steps_count INTEGER DEFAULT 0,
    duration_sec REAL,
    vision_enabled BOOLEAN DEFAULT 0,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (persona_id) REFERENCES personas(id)
);

-- STEPS: Détails de chaque step (XAI)
CREATE TABLE IF NOT EXISTS steps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    step_number INTEGER NOT NULL,
    thought TEXT,
    action TEXT,
    action_input TEXT,
    result TEXT,
    is_error BOOLEAN DEFAULT 0,
    FOREIGN KEY (run_id) REFERENCES test_runs(id)
);
