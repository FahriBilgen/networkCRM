# Theme & Prompt Backlog

Last update: 2025-11-07

## Input Signals

- `runs/perf_reports/perf_report_20251107_182136.json` shows the latest perf watchdog snapshot (avg turn 0.15 s, storage ops <1 ms, peak memory 551,304 bytes), so we have latency headroom for richer prompt branches.
- `runs/regressions/test_regression/summary.json` and `runs/regressions/test_regression2/summary.json` confirm that the regression harness executed without failures (current suites were skipped), so we can safely queue new writer work before re-enabling heavy suites.
- `tools/telemetry_report.py` output from the sandbox runs is clean (veto rate <1%), meaning Judge prompts do not block new content right now.

## Priority Queue (Q4 2025)

| Rank | Pack / Prompt Track | Status | Notes |
|------|---------------------|--------|-------|
| 1 | `orbital_frontier_v2` | Ready for writing | Needs glitch/anomaly prompt variants plus NPC trust differentials to avoid repeating motif slots 2 and 4. |
| 2 | `deep_keep` (siege extension) | Briefs drafted | Extends siege_default with subterranean rooms; requires new fallback text and resource pressure prompts. |
| 3 | `clockwork_revolt` (new pack) | Discovery | High-risk theme with parallel Judge + FunctionValidator instrumentation; depends on new guardrail cues. |

## Item Detail

### 1. Orbital Frontier v2
- Expand `themes/orbital_frontier.json` with two extra event prompt overrides focused on anomaly containment.
- Add trust delta summaries to the turn intro panel so the UI can showcase faction alignment changes that surfaced in the last regression output.
- Validation: `python fortress_director/cli.py theme simulate orbital_frontier --turns 3 --random-choices` plus `python tools/telemetry_report.py --run runs/profile_* --turns 15` before requesting review.

### 2. Deep Keep (Siege Extension)
- Build a sibling JSON to `themes/siege_default.json` that inherits base siege but overrides `world_state_overrides` for underground supply tracking.
- Scriptwriters need fresh fallback prompt trios for moral/tactical/supply angles so Judge veto recovery does not repeat existing siege text.
- Validation: run the regression suite with `python tools/regression_runner.py --tag deep_keep` to capture Judge veto deltas; compare against `runs/regressions/test_regression/summary.json`.

### 3. Clockwork Revolt
- New pack that leans on safe-function heavy turns; requires raising FunctionRegistry gas ceilings and drafting guardrail copy describing automation rebellion stakes.
- Depends on telemetry showing acceptable safe-function failure rate; rerun `python tools/perf_watchdog.py --turns 3 --tag clockwork` when prompts are ready.
- Blocker: guardrail narrative copy plus schema extensions for mechanical factions (to be added under `themes/theme_schema.json`).

## Operational Checklist

1. When any backlog item moves to implementation, append a regression run under `runs/regressions/<pack_name>` so the telemetry job can pick up new baselines.
2. Sync this file during sprint planning alongside `docs/story_packs.md`; the weekly GitHub Action (`weekly-kpi.yml`) drops perf snapshots that should be cited here.
3. Archive closed items inside `docs/story_packs.md` once the pack ships to reduce noise in this active queue.
