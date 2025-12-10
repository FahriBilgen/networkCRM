# Testing & Performance Strategy

## Guiding Principles
- Prefer real model runs for acceptance but maintain fast deterministic suites for regression.
- Track token/time budgets per turn to ensure expanded mechanics remain practical.

## Test Layers
1. **Unit Tests**
   - Each new safe function: validation success/failure, state mutation, rollback on exception.
   - DirectorAgent logic: directives derived from sample states.
   - Judge cache + placeholder filtering behaviour.
2. **Integration Tests**
   - Multi-turn scenario (mocked models) verifying orchestrator flow with expanded features.
   - World state migrations from legacy schema to new schema.
   - Finale sequence progression (act advancement, major event queue, final resolution).
3. **Live Model Acceptance**
   - Guardrail dataset `acceptance_tests/model_guardrail.jsonl` captures Judge + safe-function regressions.
   - Script `tools/run_acceptance_suite.py` loads the dataset, runs Judge heuristics and safe function validators, and emits JSON suitable for CI/nightly alerts.
   - Collect transcripts/logs for manual QA.
   - HaftalÄ±k â€œlive pilotâ€ profilinde `python tools/perf_watchdog.py --turns 3 --live-models --reset-state --tag live_pilot --report-dir runs/perf_reports` komutu ile offline/online sÃ¼relerini karÅŸÄ±laÅŸtÄ±r; sonuÃ§larÄ± `docs/perf_live_pilot.md` akÄ±ÅŸÄ±na gÃ¶re yorumla.

## Performance Measurements
- Instrument orchestrator to log per-agent latency and tokens (if API provides data).
- Add profiling CLI `python fortress_director/scripts/cli.py profile --turns N` capturing average turn duration & safe function count.
- Define warning thresholds (e.g., >90s per turn or >10 safe function calls).
- Use `py tools/profile_state_io.py --iterations 50` to benchmark `StateStore.snapshot()` / `persist()` latency and validate the <50ms target.
- `py fortress_director/scripts/cli.py debug_state` artik `io_metrics` alaninda son 200 snapshot/persist orneklerinin ortalama/p95 degerlerini gosterir; `tools/telemetry_aggregate.py` bu metrikleri `snapshot_avg_ms`, `persist_p95_ms` kolonlarina yazar.
- Safe function calismalari icin `map_fn_latency_ms` ve `snapshot_batch_ms` kolonlari telemetry CSV'lerine eklendi; `tools/perf_watchdog.py` bu degerleri raporlayarak harita fonksiyonlarinin IO maliyetlerini takip etmeyi kolaylastirir.
- Mini regression script `tools/regression_runner.py` unit + integration testlerini tek komutla calistirip `runs/regressions/<tag>` altina log ve ozet kaydeder; `--dry-run` ile olasi komutlar incelenebilir.

## Tooling Additions
- Fixture generators under `tests/fixtures/` for world state snapshots and agent outputs.
- Lint rule / CI check ensuring prompt files stay within size/token bounds.
- Utility to diff world state before/after safe function batch for debugging.

## Automation Pipeline
- Local developer flow: run unit tests -> integration tests -> selective live acceptance.
- Optional CI tiers (once environment allows real model invocation): schedule nightly acceptance runs, archive logs.

