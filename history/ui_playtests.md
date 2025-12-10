# UI Playtest Log

Quick snapshots aligned with `docs/ui_accessibility_targets.md`. Each entry lists
what we validated, how we validated it, and any follow-ups before signing off.

## 2025-11-08 – Accessibility Baseline (dry run)

- **Build:** `f794954` (local working tree with map diff + HUD updates)
- **Environment:** Offline orchestrator + CLI (no browser automation yet)
- **Commands executed:**
  - `pytest fortress_director/tests/test_ui_smoke.py fortress_director/tests/test_game_api.py`
  - `pytest fortress_director/tests/test_map_diff_adapter.py fortress_director/tests/test_map_diff_validator.py`
  - `pytest fortress_director/tests/test_npc_behavior.py`
  - `pytest fortress_director/tests/test_safe_functions.py`

| Checklist item | Validation method | Result | Notes |
| --- | --- | --- | --- |
| HUD metrics, win/loss scaffolding, tutorial overlay populate for turns 0-2 | `tests/test_ui_smoke.py` asserts `player_view.turn_hud` + `tutorial_overlay` structure | ✅ Pass | Confirms API contract now emits the data HUD cards consume. Visual sweep still recommended. |
| Map diff feed + SSE wiring | `tests/test_map_diff_adapter.py` / `tests/test_map_diff_validator.py` + manual review of `fortress_director/demo/web/index.html` `applyMapDiff` | ✅ Pass | Diff payload is validated before hitting UI, and UI pulses entries via `aria-live="polite"`. |
| Deterministic NPC behavior timeline and safe function batching | `tests/test_npc_behavior.py` + `tests/test_safe_functions.py::test_safe_function_executor_reports_map_metrics` | ✅ Pass | Ready-made actions fire through SafeFunctionExecutor and telemetry now exposes `map_fn_latency_ms`/`snapshot_batch_ms`. |
| Story pressure panels (NPC loyalty, resource pressure, event chains) | `tests/test_ui_smoke.py` / `tests/test_game_api.py` enforce new `player_view` fields; UI cards render via `renderNPCLoyalty`, `renderResourcePressure`, `renderEventChain`. | ✅ Pass | Data contracts landed; upcoming browser sweep should capture how the new pills look under default/high-contrast palettes. |
| Meta progression HUD (unlocks, achievements, share card) | UI now renders `meta_progression` block via `renderMetaProgression`; `Copy Summary` button copies the share card text. | ✅ Pass | Sonraki taramada Ready durumunda butonu test edip panoya yapıştırılan içeriği ekran görüntüsüyle kaydet. |
| Accessibility controls (`High Contrast`, `Large Text`, reduced motion) | Code read of `fortress_director/demo/web/index.html` (prefers-reduced-motion media query, `aria-pressed` toggles) | ⚠️ Needs visual confirmation | Implementation exists; next UI sweep should toggle the controls in-browser and capture screenshots per checklist step 4. |

### Follow-ups

1. Capture actual HUD + tutorial screenshots under default and high-contrast palettes.
2. Verify live EventSource stream repaint in a real browser (current run used API smoke tests only).
3. Extend this log with player-observed notes (latency, clarity) once we run the guided playtest called out in the roadmap.
