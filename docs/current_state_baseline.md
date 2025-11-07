# Current Scenario Baseline

> Referans StateStore katmanı JSON + SQLite arasında sıcak/soguk ayrımı yapar; snapshot()/persist() çağrılarında <50 ms hedefi için `StateStore` ve `MetricManager` ölçümleri `metrics` blokları üzerinden izlenir.

## Safe Function Registry Snapshot (2025-11-02)
Name | Purpose | Notes on Validation / Side Effects
---- | ------- | ----------------------------------
change_weather | Persist new atmosphere & sensory details to `world_constraint_from_prev_turn` and track recent atmospheres. | Rejects positional args; requires non-empty strings; records `last_weather_change_turn`.
spawn_item | Add item to player inventory or named storage bucket. | Target defaults to player; ensures no duplicates.
move_npc | Update `npc_locations[npc_id]` with new room tag. | Requires strings for npc and location.
adjust_logic | Increment `scores.logic_score`. | No custom validator.
adjust_emotion | Increment `scores.emotion_score`. | No custom validator.
raise_corruption | Increment `scores.corruption`. | No custom validator.
advance_turn | Increment `current_turn`/`turn`. | Maintains monotonic turn values.
modify_resources | Apply delta through `MetricManager.modify_resources`. | Sanitises integer amount & cause string; logs metric change.
adjust_metric | Generic metric delta routed via `MetricManager.adjust_metric`. | Validates metric name + integer delta; records cause in log buffer.
move_room | Set `current_room`. | Requires room string.
set_flag | Append unique flag to `flags` list. | Enforces non-empty string.
clear_flag | Remove flag string if present. | Enforces non-empty string.
set_trust | Clamp `npc_trust[npc_id]` to 0-5. | Requires npc id + integer trust.
adjust_trust | Delta adjust trust with clamp 0-5. | Requires npc id + integer delta.
add_item_to_npc | Append item to `npc_items[npc_id]`. | Avoids duplicates.
remove_item_from_npc | Remove item from `npc_items[npc_id]`. | Safe if missing.
add_status | Append status dict `{status, duration}` to `status_effects[npc_id]`. | Duration coerced to int >=0.
remove_status | Filter status entries for npc. | Validator enforces strings.
spawn_npc | Add entry in `npc_locations` for new npc. | Requires npc id + location.
despawn_npc | Remove npc from locations/items/status registries. | Returns flag if removal happened.
move_and_take_item | Composite: optional move_npc then add_item_to_npc. | Validator allows optional location.
patrol_and_report | Composite: move npc along ring, adjust order metric, emit report metadata. | Uses internal `_get_next_room` helper.

## Persisted World State (DEFAULT_WORLD_STATE)
- campaign_id / turn_limit / current_turn / rng_seed
- scores: logic_score, emotion_score, corruption
- flags (list of scenario flags)
- memory_layers, active_layer, npc_fragments
- inventory (global), lore
- turn / day / time / current_room
- recent_events (list of event payloads)
- recent_motifs (list of motif ids)
- world_constraint_from_prev_turn {atmosphere, sensory_details}
- player {name, inventory, stats{resolve, empathy}, summary}
- character_summary (string), relationship_summary (string)
- metrics {order, morale, resources, knowledge, corruption, glitch, risk_applied_total, major_flag_set, major_events_triggered, major_event_last_turn}
- npc_trust (map)
- Drama governor internals: `_drama_window`, `_anomaly_active_until`, `_world_lock_until`, `_high_volatility_mode`

### Derived/transient fields created at runtime
- npc_locations, npc_items, status_effects, items, recent_world_atmospheres, last_weather_change_turn
- sf_history (per safe function usage), player_choice_history, memory_short / memory_long, persistent_motif, previous_judge_verdict

## Existing Automated Coverage
File | Focus
---- | -----
tests/test_safe_functions.py | Basic validation & execution of registered safe functions.
tests/test_safe_function_validation.py | Validator edge cases, error handling.
tests/test_safe_function_normalization.py | Input coercion for FunctionCall payloads.
tests/test_rollback_trigger.py | RollbackSystem behaviour during failing safe calls.
tests/test_codeaware_minimal.py | Registry smoke tests.
Additional integration tests (`test_orchestrator_*`, `test_logging_workflow.py`, etc.) indirectly exercise the safe function queue and world state updates.

## Baseline Observations
- Registry already supports item, status, trust, and basic macro helpers but lacks rich mechanics (structure integrity, quest progression, combat).
- World state merges JSON defaults with runtime expansions; no schema versioning in file yet.
- Agent prompts receive available function list but rarely emit calls, leading to fallback usage by orchestrator.
- Tests rely on deterministic snapshots; any schema expansion will need migration logic and updated fixtures.
- Metrics katmanı `MetricManager` üzerinden okunup `metrics` alanına yazılıyor; yeni özellikler eklenirken bu panonun güncel kalması gerekiyor.
