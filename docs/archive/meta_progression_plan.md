# Meta Progression & Telemetry Blueprint

Last update: 2025-11-08  
Owner: Narrative Systems

## 1. Player Promise

Players finish a siege run with *persistent* recognition:

1. **Unlock Tracks** â€“ Completing specific tactical beats (e.g., â€œStabilize all map layers before turn 5â€) unlocks new tutorial overlays, safe-function allowances, or art swaps for later runs.
2. **Achievements** â€“ Lightweight badges tied to NPC loyalty, resource mastery, or event-chain handling. These surface in the UI recap and can be exported as short cards.
3. **Shareable Summary** â€“ Auto-generated card (text + key stats) that can be copied or posted.

The HUD/UI must hint at each track *mid-run* so choices feel consequential.

## 2. Data Model Additions

| Field | Description | Source |
| --- | --- | --- |
| `meta_progression.unlocks` | List of `{id, label, status, turn}` entries. Example: `unlock_safe_fn_batch` once the player survives 3 consecutive turns without glitch >70. | Derived from state flags (`unlock_*`) plus rule-based detectors. |
| `meta_progression.achievements` | `{id, label, tier, unlocked_turn}` rows keyed by `state["achievements"]` (list) or inferred from metrics (e.g., morale >80 + order >80 = â€œHarmonyâ€). | `state["achievements"]` (to be persisted) + helper heuristics. |
| `meta_progression.share_card` | `{ready: bool, summary: str, metrics: {...}}` object built from `result["summary_text"]`, `final_summary_cards`, and Turn HUD metrics. | TelemetryBuilder. |
| `telemetry.meta_progression` | Flattened metrics for dashboards: `unlocks_count`, `achievements_count`, `share_card_ready`. | TelemetryBuilder + telemetry_aggregate. |

## 3. Unlock & Achievement Rules (initial set)

| ID | Trigger | Reward |
|----|---------|--------|
| `unlock_map_mastery` | All map layers `status="active"` with threat levels <= medium for 2 consecutive turns (current implementation). | +1 extra `update_map_layer` call limit next campaign. |
| `unlock_loyalty_brief` | Maintain â‰¥2 NPCs with `trust >= 4` for 3 consecutive turns (acts as â€œwhole runâ€ proxy until full campaign tracking lands). | Adds extra tutorial hint referencing loyalty. |
| `achv_resource_anchor` | `morale`, `resources`, `order` all â‰¥60 (â‰¥80 yields gold tier). | Badge in recap + share card highlight. |
| `achv_event_conductor` | Resolve (remove) 3 scheduled events before their `trigger_turn`. | Unlocks alt event vignette. |

These rules must be deterministic so we can re-compute them when loading history (use telemetry CSV or `history/turn_X.json`).

## 4. UI Touchpoints

- **Mid-run HUD:** Add icon next to Turn HUD when a prerequisite is close (future work). For now, the `player_view.meta_progression` block lets UI devs render optional chips.
- **End-of-run Recap:** `post_game_recap` should include `meta_progression.share_card` text + achievements list.

## 5. Telemetry & Storage

| File | Update | Notes |
| --- | --- | --- |
| `fortress_director/orchestrator/state_services.py` | Add helper to build `meta_progression` structure from state/result (flags, achievements, HUD metrics). | Keeps logic centralized. |
| `fortress_director/orchestrator/telemetry_builder.py` | Attach `meta_progression` into `player_view` and `telemetry`. | Mirrors HUD data + ensures API clients see it. |
| `tools/telemetry_aggregate.py` | Add CSV columns: `meta_unlocks`, `meta_achievements`, `meta_share_card`. | Enables dashboards to chart progression adoption. |
| `tools/perf_watchdog.py` | Include meta stats in markdown so weekly KPI includes content adoption. | e.g., â€œUnlocks earned: Xâ€. |
| `fortress_director/api.py` | `/game/share-card` exposes unlocks/achievements/share-card for UI/clients. | Lightweight GET endpoint for dashboards or companion apps. |
| `fortress_director/scripts/cli.py` | `share_card` command prints the same payload for quick sharing. | Supports `--json` for automation. |

## 6. Implementation Order

1. **Data plumbing (this PR)** â€“ expose empty-but-typed structures so UI/tests pass even when no unlocks exist.
2. **Rule evaluation** â€“ extend state mutation functions to append to `state["achievements"]` or `state["meta_unlocks"]`.
3. **UI badges** â€“ render chips + shareable summary.
4. **Share/export** â€“ add CLI/API endpoints to export `share_card`.

## 7. Testing Strategy

- Unit tests for helper functions (meta panel builder) covering: empty state, unlock flags, achievements list, share card builder.
- Extend `tests/test_ui_smoke.py` and `tests/test_game_api.py` to assert `player_view.meta_progression`.
- Telemetry scripts: add fixture in `tests/test_tools_telemetry.py` (future) that ensures CSV rows include new columns.

## 8. Open Questions

- **Persistence:** Should unlocks survive across saves? Proposed: store in `state["meta_unlocks"]` and replicate into SQLite via existing sync.
- **Sharing medium:** For now, share card is text-only. Later we may emit structured data for HTML export.
- **Guardrails:** Need to ensure achievements donâ€™t reveal unreleased content on early turns; consider gating behind day/turn thresholds.

Document owners should update this file whenever rules or telemetry columns change.

## 9. Social Sharing Pipeline (Phase F scope)

Goal: turn every successful run into a ready-to-share artifact without hand-editing assets.

1. **Auto screenshot stage**
   - Run `python tools/share_card_pipeline.py` to export the share payload into `runs/share_cards/<timestamp>/`.
   - The script renders a lightweight `recap.html`, attempts a Playwright screenshot (`recap.png`) plus optional WebP conversion (via `cwebp`), and writes `share_card.json` + `summary.txt`.
   - `runs/share_cards/latest.txt` always mirrors the latest story hook + metrics so Ops can copy/paste if automation is skipped.

2. **Story summary assembly**
   - `StateServices` now emits `share_card.story_hook` and `share_card.metrics_list`; `fortress_director/scripts/cli.py share_card` surfaces the same data for quick previews.
   - The pipeline script stitches those fields into `summary.txt` and the recap HTML template, keeping text + metrics synchronized with the JSON payload.

3. **Distribution + ops checklist**
   - `ops/social_share_checklist.md` captures rate limits, webhook owners, and the weekly smoke-test routine.
   - `tools/share_card_pipeline.py` posts `{image_url, summary, story_hook, metrics, achievements}` to `discord_webhook` (hero channel) and `partner_webhook` (studio review) when URLs are provided.
   - Use `--dry-run --skip-screenshot` during smoke tests and log the result in `history/ui_playtests.md`.

4. **Telemetry + auditing**
   - Each share attempt appends an entry to `runs/share_cards/share_log.jsonl` **and** annotates the latest turn JSON with `telemetry.share_pipeline`.
   - `tools/perf_watchdog.py` reads the log so the KPI digest includes `Share cards posted: X (failures: Y)`.

These steps fulfill the Phase F roadmap ask to expand the social sharing pipeline with automatic screenshots, story summaries, and Discord/webhook visibility. Update this section whenever a new channel, format, or checklist item ships.

