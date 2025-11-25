-- Fortress Director - SQLite Database Schema
-- Initial schema for multi-user game state persistence
-- Created: 2025-11-26

-- ============================================================================
-- SESSIONS TABLE - Player game sessions
-- ============================================================================
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    player_name TEXT NOT NULL,
    theme_id TEXT DEFAULT 'siege_default',
    turn_limit INTEGER DEFAULT 7,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'active',  -- active, completed, lost, paused
    final_state JSONB,
    final_outcome TEXT,  -- win, loss, neutral
    metadata JSONB,  -- custom data per session
    
    -- Indexes for common queries
    CHECK (status IN ('active', 'completed', 'lost', 'paused'))
);

CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status);
CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON sessions(created_at);
CREATE INDEX IF NOT EXISTS idx_sessions_theme_id ON sessions(theme_id);

-- ============================================================================
-- GAME_TURNS TABLE - Turn-by-turn game progression
-- ============================================================================
CREATE TABLE IF NOT EXISTS game_turns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    turn_number INTEGER NOT NULL,
    state_snapshot JSONB NOT NULL,
    player_choice_id TEXT,
    player_choice_text TEXT,
    execution_time_ms INTEGER,
    agent_telemetry JSONB,  -- {event_agent: {time, success}, world_agent: {...}, ...}
    major_event_triggered BOOLEAN DEFAULT FALSE,
    narrative_summary TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    UNIQUE(session_id, turn_number),
    CHECK (turn_number >= 0),
    CHECK (execution_time_ms >= 0)
);

CREATE INDEX IF NOT EXISTS idx_game_turns_session_turn ON game_turns(session_id, turn_number);
CREATE INDEX IF NOT EXISTS idx_game_turns_created_at ON game_turns(created_at);

-- ============================================================================
-- CHECKPOINTS TABLE - Savepoints for rollback capability
-- ============================================================================
CREATE TABLE IF NOT EXISTS checkpoints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    turn_number INTEGER NOT NULL,
    state JSONB NOT NULL,
    reason TEXT NOT NULL,  -- 'manual', 'auto_backup', 'major_event', 'error_recovery'
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    CHECK (turn_number >= 0)
);

CREATE INDEX IF NOT EXISTS idx_checkpoints_session_turn ON checkpoints(session_id, turn_number);
CREATE INDEX IF NOT EXISTS idx_checkpoints_reason ON checkpoints(reason);

-- ============================================================================
-- SAFE_FUNCTION_CALLS TABLE - Audit trail of safe function executions
-- ============================================================================
CREATE TABLE IF NOT EXISTS safe_function_calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    turn_number INTEGER NOT NULL,
    function_name TEXT NOT NULL,
    parameters JSONB,
    result JSONB,
    success BOOLEAN DEFAULT TRUE,
    execution_time_ms INTEGER,
    error_message TEXT,
    caller_source TEXT,  -- 'event_agent', 'character_agent', 'director_agent'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    CHECK (execution_time_ms IS NULL OR execution_time_ms >= 0)
);

CREATE INDEX IF NOT EXISTS idx_safe_function_calls_session_turn ON safe_function_calls(session_id, turn_number);
CREATE INDEX IF NOT EXISTS idx_safe_function_calls_function_name ON safe_function_calls(function_name);
CREATE INDEX IF NOT EXISTS idx_safe_function_calls_success ON safe_function_calls(success);

-- ============================================================================
-- AUDIT_LOG TABLE - General event audit trail
-- ============================================================================
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    event_type TEXT NOT NULL,  -- 'session_created', 'turn_executed', 'reset', 'error', 'state_corrupted'
    severity TEXT DEFAULT 'INFO',  -- 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'
    details JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    CHECK (severity IN ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'))
);

CREATE INDEX IF NOT EXISTS idx_audit_log_session_type ON audit_log(session_id, event_type);
CREATE INDEX IF NOT EXISTS idx_audit_log_severity ON audit_log(severity);
CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON audit_log(created_at);

-- ============================================================================
-- METRICS TABLE - Performance and reliability metrics
-- ============================================================================
CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    turn_number INTEGER NOT NULL,
    metric_name TEXT NOT NULL,  -- 'turn_time_ms', 'event_agent_time_ms', 'fallback_used', 'safe_functions_count'
    metric_value REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_metrics_session_metric ON metrics(session_id, metric_name);
CREATE INDEX IF NOT EXISTS idx_metrics_created_at ON metrics(created_at);

-- ============================================================================
-- NPC_STATE TABLE - Current NPC state (compatibility with sync code)
-- ============================================================================
CREATE TABLE IF NOT EXISTS npc_state (
    npc_id TEXT PRIMARY KEY,
    state JSONB NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- NPC_STATES TABLE (Historical) - Track NPC-specific state changes
-- ============================================================================
CREATE TABLE IF NOT EXISTS npc_states (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    turn_number INTEGER NOT NULL,
    npc_id TEXT NOT NULL,
    npc_state JSONB,  -- {position, status, morale, corruption, etc.}
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    UNIQUE(session_id, turn_number, npc_id)
);

CREATE INDEX IF NOT EXISTS idx_npc_states_session_turn_npc ON npc_states(session_id, turn_number, npc_id);

-- ============================================================================
-- METADATA TABLE - Global game metadata (key-value store)
-- ============================================================================
CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- VERSION & METADATA
-- ============================================================================
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT OR IGNORE INTO schema_version (version, description) 
VALUES (1, 'Initial schema: sessions, game_turns, checkpoints, safe_function_calls, audit_log, metrics, npc_states');
