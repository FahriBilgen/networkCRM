-- Archive Persistence Schema
-- Extends main schema.sql to support StateArchive persistence
-- Created: 2025-11-26

-- ============================================================================
-- ARCHIVE_METADATA TABLE - Session archive metadata
-- ============================================================================
CREATE TABLE IF NOT EXISTS archive_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL UNIQUE,
    version INTEGER DEFAULT 1,
    last_saved_turn INTEGER DEFAULT 0,
    last_saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    max_current_turns INTEGER DEFAULT 6,
    max_recent_history INTEGER DEFAULT 10,
    archive_interval INTEGER DEFAULT 10,
    
    FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_archive_metadata_session ON archive_metadata(session_id);

-- ============================================================================
-- ARCHIVE_TURNS TABLE - Full/delta turn snapshots for archive tiers
-- ============================================================================
CREATE TABLE IF NOT EXISTS archive_turns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    turn_number INTEGER NOT NULL,
    tier TEXT NOT NULL,  -- current, recent, archive
    snapshot_type TEXT NOT NULL,  -- full, delta, summary
    data JSONB NOT NULL,
    compressed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    UNIQUE(session_id, turn_number, tier),
    CHECK (tier IN ('current', 'recent', 'archive')),
    CHECK (snapshot_type IN ('full', 'delta', 'summary'))
);

CREATE INDEX IF NOT EXISTS idx_archive_turns_session_turn ON archive_turns(session_id, turn_number);
CREATE INDEX IF NOT EXISTS idx_archive_turns_session_tier ON archive_turns(session_id, tier);

-- ============================================================================
-- ARCHIVE_SUMMARIES TABLE - Compressed summaries (every 10 turns)
-- ============================================================================
CREATE TABLE IF NOT EXISTS archive_summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    summary_range_start INTEGER NOT NULL,
    summary_range_end INTEGER NOT NULL,
    major_events TEXT,  -- JSON array of event strings
    npc_status JSONB,   -- NPC name → {morale, fatigue, position, status}
    threat_trend JSONB, -- {started, current, trend}
    world_state JSONB,  -- Compressed world state snapshot
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    UNIQUE(session_id, summary_range_start, summary_range_end)
);

CREATE INDEX IF NOT EXISTS idx_archive_summaries_session_range ON archive_summaries(session_id, summary_range_start, summary_range_end);

-- ============================================================================
-- ARCHIVE_THREATS TABLE - Threat model timeline for consistency
-- ============================================================================
CREATE TABLE IF NOT EXISTS archive_threats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    turn_number INTEGER NOT NULL,
    base_threat REAL,
    escalation REAL,
    morale INTEGER,
    resources INTEGER,
    recent_hostility INTEGER,
    threat_score REAL,
    phase TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    UNIQUE(session_id, turn_number)
);

CREATE INDEX IF NOT EXISTS idx_archive_threats_session_turn ON archive_threats(session_id, turn_number);

-- ============================================================================
-- ARCHIVE_NPCS TABLE - NPC status history for character consistency
-- ============================================================================
CREATE TABLE IF NOT EXISTS archive_npcs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    turn_number INTEGER NOT NULL,
    npc_id TEXT NOT NULL,
    npc_name TEXT,
    morale INTEGER,
    fatigue INTEGER,
    position JSONB,  -- {x, y}
    status TEXT,  -- active, wounded, resting, dead
    last_action TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    UNIQUE(session_id, turn_number, npc_id)
);

CREATE INDEX IF NOT EXISTS idx_archive_npcs_session ON archive_npcs(session_id);
CREATE INDEX IF NOT EXISTS idx_archive_npcs_session_turn ON archive_npcs(session_id, turn_number);
CREATE INDEX IF NOT EXISTS idx_archive_npcs_npc_id ON archive_npcs(npc_id);

-- ============================================================================
-- Migration indicator
-- ============================================================================
CREATE TABLE IF NOT EXISTS schema_migrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version TEXT NOT NULL UNIQUE,
    migration_name TEXT NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT OR IGNORE INTO schema_migrations (version, migration_name)
VALUES ('20251126_archive_persistence', 'Archive persistence schema');
