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
   - Script `tools/run_acceptance_suite.py` to execute predefined turns using actual Ollama models.
   - Collect transcripts/logs for manual QA.

## Performance Measurements
- Instrument orchestrator to log per-agent latency and tokens (if API provides data).
- Add profiling CLI `python fortress_director/cli.py profile --turns N` capturing average turn duration & safe function count.
- Define warning thresholds (e.g., >90s per turn or >10 safe function calls).

## Tooling Additions
- Fixture generators under `tests/fixtures/` for world state snapshots and agent outputs.
- Lint rule / CI check ensuring prompt files stay within size/token bounds.
- Utility to diff world state before/after safe function batch for debugging.

## Automation Pipeline
- Local developer flow: run unit tests -> integration tests -> selective live acceptance.
- Optional CI tiers (once environment allows real model invocation): schedule nightly acceptance runs, archive logs.
