# Player View Summary Enhancements

Date: 2025-11-06 (updated 2025-11-07)  
Owner: Codex assistant

## Overview

The turn result payload's `player_view` field now exposes additional
UI-ready summaries so front-end surfaces can show key state signals
without bespoke data fetching. These values are derived from the
existing world state during turn assembly; no extra data is persisted.

## New fields

| Field | Type | Description |
|-------|------|-------------|
| `metrics_panel` | `object` | Snapshot of the main world meters (`order`, `morale`, `resources`, `knowledge`, `corruption`, `glitch`). Only numeric values are emitted. |
| `active_flags` | `string[]` | Up to eight truthy flags currently present in the state. Flags are trimmed strings, ordered as stored. |
| `npc_trust_overview` | `object[]` | Top five NPC trust entries sorted by trust score. Each entry is `{ "name": str, "trust": float }`. |
| `guardrail_notes` | `object[]` | Structured guardrail explanations. Each item is `{ "type": str, "message": str }` so callers can filter on note categories. |
| `npc_journal_recent` | `object[]` | Most recent NPC reaction journal entries (up to 5), each `{ "turn": int, "name": str, "intent": str, "entry": str }`. |
| `map_state` | `object` | Canonical snapshot `{ current_room, day, time, npc_positions[], structures[] }` shared between UI, telemetry and API consumers. |
| `npc_locations` | `object[]` | Flattened `npc_positions` list for legacy consumers; each `{ "id": str, "room": str }`. |
| `safe_function_history` | `object[]` | Canonical safe function executions `{ name, success, timestamp, metadata, effects?, summary?, guardrail_notes? }`. |
| `judge_feedback` | `string` | Short thematic sentence explaining the judge's latest penalty if any. |
| `fallback_strategy`, `fallback_summary` | `string` | Structured description of the veto fallback used when applicable. |

## Integration notes

* All fields are optional; clients should guard against their absence.
* `metrics_panel` is suitable for small dashboard widgets (radar,
  badges, etc.). Values respect the orchestrator's metric naming.
* `active_flags` is intentionally capped to eight entries to avoid
  overwhelming UI components.
* Trust entries are emitted as floats to preserve fractional scoring if
  the rules engine adopts it later.
* `guardrail_notes` matches the data surfaced in turn telemetry and
  `/telemetry/*` endpoints so UI/CLI stay consistent.
* `map_state` + `npc_locations` provide a canonical space model that
  safe-function logging, API responses, and the web UI now share.
* `safe_function_history` is pre-normalised; downstream renderers no
  longer have to parse executor-specific payloads.
* `/telemetry/events` (SSE) and `/telemetry/latest` (polling) replay the
  same planner + safe function telemetry, guardrail notes, and fallback
  summaries so dashboards stay in sync without extra wiring.

## Validation

* Running `py tools/profile_turn.py --turns 1 --include-turns --json`
  confirms that `player_view` now contains the new attributes with the
  expected structure. Since the data is derived on the fly, no additional
  state persistence occurs and snapshot size remains unchanged.
* SSE endpoint `GET /telemetry/events` streams the same structures used
  by the UI dashboards; polling fallback `GET /telemetry/latest`
  provides identical payloads for environments without `EventSource`.
