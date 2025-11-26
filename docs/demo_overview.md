# Siege Demo Overview

This note explains the `siege_demo_v1` scenario defined in `fortress_director/demo/demo_spec.json`. The demo spec drives GameState bootstrap, turn pacing, and ending selection.

## Demo Identity
- **ID:** `siege_demo_v1`
- **Scope:** 12 turn survival siege focused on wall integrity, morale, and threat.
- **Source of truth:** `demo_spec.json` holds map size, initial resources, NPC roster, highlights, and ending thresholds.

## Turn Structure
1. `turn_manager.run_turn` initializes GameState from the spec on the first call and locks turn counter to 1.
2. Each new turn increments `metrics["turn"]` before the agents plan actions.
3. After the 12th turn the ending evaluator picks good / neutral / bad, the state is marked as `game_over`, and the API reports the final outcome.

## Starting Metrics
- `turn`: 1
- `wall_integrity`: 100
- `food`: 40
- `morale`: 50
- `threat`: 20
- `npc_count`: 8 (two guards, a captain, an engineer, four civilians)

## Ending Conditions
- **Good:** wall integrity >= 40, morale >= 50, threat <= 40
- **Neutral:** wall integrity >= 20, morale >= 30, threat <= 60
- **Bad:** any other state (wall >= 0, morale >= 0, threat <= 999)

## Demo Highlights
- `npc_movement`: initial roster is split between the wall line and the inner courtyard so the Renderer can show patrols.
- `wall_damage` / `wall_repair`: driven by `metrics["wall_integrity"]` and the `fortress_wall` structure entry.
- `event_markers`: the planner/executor can add markers to spotlight breaches or supply drops on the tactical grid.
- `atmosphere_changes`: Renderer returns mood/lighting payloads every turn so UI transitions match the siege pressure.
- `resource_changes`: `metrics` and `world.resources` reflect food and morale shifts after each player choice.

This overview makes it easy to pitch the deterministic demo to stakeholders: one spec defines the experience, GameState builds directly from it, and the ending evaluator enforces the same thresholds used in this document.
