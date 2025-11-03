-- Fortress Director SQLite schema (v1)
-- Captures high-value slices of the JSON world state for analytics/debugging.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS metadata (
	key TEXT PRIMARY KEY,
	value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS npc_state (
	npc_id TEXT PRIMARY KEY,
	name TEXT,
	template TEXT,
	location TEXT,
	status TEXT,
	trust INTEGER DEFAULT 0,
	last_updated_turn INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS structure_state (
	structure_id TEXT PRIMARY KEY,
	durability INTEGER NOT NULL,
	max_durability INTEGER NOT NULL,
	status TEXT,
	last_repaired_turn INTEGER,
	last_reinforced_turn INTEGER
);

CREATE TABLE IF NOT EXISTS stockpiles (
	resource_id TEXT PRIMARY KEY,
	quantity INTEGER NOT NULL,
	last_updated_turn INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS trade_routes (
	route_id TEXT PRIMARY KEY,
	status TEXT NOT NULL,
	risk INTEGER NOT NULL,
	reward INTEGER NOT NULL,
	opened_turn INTEGER,
	closed_turn INTEGER,
	last_reason TEXT
);

CREATE TABLE IF NOT EXISTS scheduled_events (
	event_id TEXT PRIMARY KEY,
	trigger_turn INTEGER NOT NULL,
	status TEXT DEFAULT 'scheduled'
);

CREATE TABLE IF NOT EXISTS timeline_events (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	turn INTEGER NOT NULL,
	event_type TEXT NOT NULL,
	payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS hazard_log (
	hazard_id TEXT,
	turn INTEGER NOT NULL,
	severity INTEGER NOT NULL,
	duration INTEGER NOT NULL,
	PRIMARY KEY (hazard_id, turn)
);

CREATE TABLE IF NOT EXISTS combat_log (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	turn INTEGER NOT NULL,
	attacker TEXT NOT NULL,
	defender TEXT NOT NULL,
	outcome TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS story_progress (
	act TEXT PRIMARY KEY,
	progress REAL NOT NULL,
	last_updated_turn INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_timeline_turn ON timeline_events (turn);
CREATE INDEX IF NOT EXISTS idx_hazard_turn ON hazard_log (turn);
CREATE INDEX IF NOT EXISTS idx_combat_turn ON combat_log (turn);
