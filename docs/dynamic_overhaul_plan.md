# Fortress Director Dynamic Overhaul Plan

## 1. Safe Function API Expansion
- Inventory current registry (change_weather, spawn_item, move_npc, etc.) and document behaviour/validators.
- Identify missing mechanics: NPC navigation (path checkpoints, zones), structure integrity, resource pipelines, quest progression, combat resolution, anomaly triggers.
- Design new safe functions grouped by domain:
  - `world_state`: weather gradients, time-of-day locks, environmental hazards.
  - `npc`: spawn/despawn, schedule assignment, move_to_zone, engage_target.
  - `resources`: adjust_stockpile, trade_transaction, craft_item.
  - `structure`: reinforce_wall, repair_breach, set_trap.
  - `story`: queue_major_event, unlock_lore, flag_finale_stage.
- For each function define: signature, validator rules, rollback data snapshot requirements, gas budget cost, side-effect logging.
- Update `SafeFunctionRegistry` defaults, validators, and rollback tests; add coverage for chain execution and failure rollback.

## 2. World State & Persistence Model
- Draft revised JSON schema: separate sections for `world`, `actors`, `structures`, `quests`, `timeline`, `metrics`, `glitch_state`.
- Extend SQLite schema (`db/schema.sql`) to mirror high-value data: npc table (id, template, location, status), structure table, active quest table, timeline events.
- Plan migration strategy: version flag in world_state, migration script that upgrades existing saves without data loss.
- Implement repository utilities for snapshot diffing and validation to ensure deterministic writes.

## 3. Prompt & Agent Updates
- EventAgent prompt: include safe function examples per event type, emphasise limited count (max 2 per turn) and narrative justification fields.
- Planner/Director agent (new or expanded): maintain act/beat structure, track risk budget, spawn directives, final act triggers.
- CharacterAgent prompt: require explicit `effects` map and optional `safe_functions` for actions (e.g., move_npc, adjust_trust). Provide schema reminder and sample response.
- CreativityAgent fallback: if model output invalid, invoke deterministic remix (synonym swap, motif insertion) before returning to orchestrator.
- JudgeAgent feedback: allow structured guidance back to upstream agents (e.g., suggest alternative safe function usage) without re-running model on duplicates.

## 4. Orchestrator Flow & Performance Controls
- Insert reaction deduplication layer: hash `(intent, action, speech)` to avoid repeated Judge calls; skip placeholders.
- Update turn pipeline to enforce safe function quotas (max per turn) and record actual usage for analytics.
- Introduce Director stage before EventAgent: evaluate long-term plan, adjust flags (finale pacing, major event timeline).
- Modify glitch handling: progressive ramp instead of floor jump; align player-facing messaging with mechanics.
- Implement retry/alert when agents fail to produce required fields (e.g., safe_functions missing) before fallback injection.

## 5. Testing & Tooling
- Expand unit tests for new safe functions, validators, rollback behaviour.
- Add integration suite covering: multi-function turns, dynamic NPC movement, quest progression, finale trigger path.
- Create stub LLM outputs in `tests/fixtures` to simulate agent responses with safe function payloads.
- Add profiling script to measure token usage/time per turn with mocked models; set thresholds for acceptance.

## 6. Player Experience & Finale Design
- Define feedback mapping: every mechanic change updates narrative/log entries (e.g., structure repairs reflected in world description).
- Establish dynamic quest arcs synchronized with final act (Day 3 collapse) including branching outcomes based on metrics.
- Outline multi-stage finale: build-up, crisis, resolution, epilogue; map required safe function operations and prompts for each stage.
- Consider surface layer (CLI/UI) enhancements: highlight active quests, NPC movements, major events timelines.

## 7. Implementation Sequencing
1. Document current registry and state schema (Sections 1-2) → baseline tests.
2. Introduce Director agent + prompt revisions (Section 3) with mock outputs.
3. Expand safe functions and orchestrator flow adjustments (Sections 1 & 4) alongside tests.
4. Update persistence layer and migrations (Section 2).
5. Integrate finale design, quest arcs, and UX updates (Section 6).
6. Run profiling, tuning, and regression suite (Section 5), iterate.

## 8. Open Questions
- What is acceptable per-turn latency budget after expansion?
- Should combat/resource computation stay LLM-driven or move to deterministic subsystems?
- How to expose sandbox controls for designers to script bespoke events without code changes?
