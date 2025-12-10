# Player-Facing Theme & Prompt Backlog

Last update: 2025-11-08  
Context: UI HUD + tutorial flow are live (see `fortress_director/demo/web/index.html` and `history/ui_playtests.md`), so every new pack must state the *player fantasy*, the visible HUD deltas, and which map/NPC safe functions drive those beats.

## Snapshot Summary

| Rank | Pack | Player Goal | Map / NPC Hooks | Status |
|------|------|-------------|-----------------|--------|
| 1 | `orbital_frontier_v2` | Hold a decaying ring platform while choosing which sectors to seal or vent. | Heavy `update_map_layer` + `spawn_event_marker` usage to show hull breaches; `adjust_npc_role` to reassign EVA squads. | **Writing** |
| 2 | `deep_keep` | Survive underground sieges by juggling light, supply shafts, and NPC miners. | `move_npc`, `adjust_npc_role`, `spawn_event_marker` for collapses; tutorial nudges toward `schedule_npc_activity`. | **Briefs drafted** |
| 3 | `clockwork_revolt` | Lead a rebellion (or crackdown) inside a mechanical city with autonomous patrols. | Introduce scripted `NPCBehaviorEngine` templates + stacked `update_map_layer` pulses to visualize control zones. | **Discovery** |

Perf headroom: `runs/perf_reports/perf_report_20251107_182136.json` shows avg turn 0.15â€¯s and map-safe-function latency <2â€¯ms, so these hooks stay within budget.

---

## 1. Orbital Frontier v2 (Writing)

- **Player fantasy:** You command a battered orbital ring where breaches appear mid-turn. The HUD should highlight remaining habitat sectors, crew morale, and Judge tolerance for aggressive venting.
- **Hero moments to script:**
  1. **Sector triage:** Prompt offers to vent a deck vs. patch it. Use `update_map_layer` to flip `status` + `threat_level`, then show the diff pulse in the UI.
  2. **Anomaly chase:** Spawn warning markers via `spawn_event_marker` (`severity: danger`) with `metadata` referencing anomaly IDs so the UI map feed lists them.
  3. **Crew swaps:** `adjust_npc_role` reassigns EVA specialists between â€œHull Wardensâ€ and â€œData Splicersâ€. Guardrail copy must mention the NPC trust impact.
- **HUD hooks:** Extend tutorial overlay with a tip reminding the player that high `order` unlocks â€œEmergency Jettisonâ€ options; add Turn HUD judge tip referencing anomaly containment.
- **Validation path:**  
  - Content writers iterate prompts + safe function hints in `themes/orbital_frontier.json`.  
  - Run `python fortress_director/scripts/cli.py theme simulate orbital_frontier --turns 3 --random-choices`.  
  - Capture map diff pulses in browser, logging results under `history/ui_playtests.md`.

## 2. Deep Keep (Briefs Drafted)

- **Player fantasy:** Hold caverns beneath the fortress while NPC miners and torchbearers rotate. Lighting and supply lines are the visible stakes.
- **Map/NPC plan:**
  - `spawn_event_marker` to place â€œCave-Inâ€ timers with `expires_after_turns` so the UI warns when a shaft will collapse.
  - `adjust_npc_role` to switch NPCs between â€œMinerâ€, â€œTorchbearerâ€, and â€œScoutâ€; stance swaps change the NPC Behavior timeline cards.
  - Encourage planners to call `update_map_layer` to highlight â€œLitâ€ vs â€œShadowedâ€ tunnels; pair with Turn HUD risk indicators (â€œDarkness risingâ€).
  - Add BehaviorTemplate entries (via `fortress_director/utils/npc_behavior.py`) for rotating torch patrols so autonomous actions keep supplies moving even if the player hesitates.
- **Player guidance:** Tutorial overlay for turnâ€¯1 should explicitly say â€œUse `schedule_npc_activity` or the Torch Patrol will miss the south shaftâ€.
- **Validation path:**  
  - Build `themes/deep_keep.json` inheriting from siege defaults.  
  - Run `python tools/regression_runner.py --tag deep_keep` to ensure Judge prompts accept the darker tone.  
  - UI sweep: toggle `High Contrast` to check readability of subterranean palettes (record in `history/ui_playtests.md`).

## 3. Clockwork Revolt (Discovery)

- **Player fantasy:** Decide whether to ally with or suppress sentient machines inside a ticking metropolis.
- **Design spikes:**
  - Expand `NPCBehaviorEngine` templates with deterministic â€œClockwork Marshalâ€ patrols that queue `safe_functions` like `move_npc` + `update_map_layer` to claim districts.
  - Define new `map_state.layers` metadata fields (e.g., `gear_alignment`) so `MapDiffAdapter` surfaces mechanical control changes without flooding the feed.
  - Author prompts that mention *visible* guardrail outcomes (â€œAutomation backlashâ€ fallback summary) so failures feel diegetic.
  - Consider raising per-turn limits in `fortress_director/utils/safe_function_specs.py` for map functions during scripted set pieces, then enforce them via planner guardrails.
- **Blockers:** Need guardrail copy for â€œautomation ethicsâ€ plus schema extensions inside `themes/theme_schema.json` for mechanical factions.
- **Validation path:**  
  - Once briefs exist, run `python tools/perf_watchdog.py --turns 3 --tag clockwork --random-choice` to ensure stacked map updates stay <5â€¯ms.  
  - Compare telemetry CSV (`runs/latest_run/summary.csv`) columns `map_fn_latency_ms` and `map_fn_batches` between the rebellion vs. crackdown branches.

---

## Operational Notes

1. Whenever a pack moves forward, drop its regression artifacts under `runs/regressions/<pack>/` so telemetry diffs donâ€™t mix quests.
2. Cross-link discoveries with `docs/ui_accessibility_targets.md` and append screenshots or observations to `history/ui_playtests.md`.
3. Archive completed packs in `docs/story_packs.md` with player-facing summaries, not just engineering notes, so future audits keep the player goal visible.

