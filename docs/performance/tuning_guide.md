# Performance & Tuning Guide

The Fortress Director turn loop mixes several subsystems: world state ticks, three LLM-backed agents (Director, Planner, Renderer), safe function execution, and rendering. Turn time is dominated by LLM latency, so instrumentation focuses on:

- The per-agent caches (`fortress_director.llm.cache.LLMCache`)
- Retry + timeout guards in `fortress_director.llm.ollama_client.generate_with_timeout`
- Turn-level telemetry emitted by `fortress_director.pipeline.turn_manager`

## Turn Duration Anatomy

1. **World tick + projections** update the `GameState` (~1–2 ms).
2. **Director** builds an intent prompt and (optionally) calls the LLM.
3. **Planner** validates/executes safe functions.
4. **Renderer** produces the narrative block.
5. **Trace + logging** persist outputs.

Each LLM call is wrapped by `profile_llm_call`, so `logs/llm_calls.log` contains the exact duration and success flag for every invocation. Turn-level summaries are stored in `logs/turn_perf.log` with the number of LLM calls and failures per turn.

## Runtime Config Knobs

`fortress_director/config/settings.yaml` exposes the key LLM runtime toggles:

```yaml
llm:
  runtime:
    timeout_seconds: 25   # Wall-clock timeout per LLM request
    cache_ttl_seconds: 300
    max_retries: 1        # Number of timeout retries
    enable_cache: true    # Skip repeated prompts when possible
    log_metrics: true     # Append metrics to logs/llm_calls.log
```

Adjust these values to balance stability and performance:

- Lower `timeout_seconds` + `max_retries` keep the pipeline responsive but may increase fallbacks.
- Disabling `enable_cache` is useful only when debugging prompt drift; otherwise keep it on to avoid repeated work.
- Set `log_metrics` to `false` when running in constrained environments without writable logs.

## Recommended Profiles

### Demo Mode

- `timeout_seconds`: 20
- `max_retries`: 0 (fail fast, rely on deterministic fallbacks)
- `enable_cache`: true
- `log_metrics`: true

### Heavy Profiling / Validation

- `timeout_seconds`: 40 (allow slower local models)
- `max_retries`: 1
- `enable_cache`: false (surface worst-case latency)
- `log_metrics`: true

## Benchmark & Reporting Commands

Run an end-to-end benchmark with optional LLM usage:

```bash
python scripts/benchmark_turns.py --num-turns 10 --use-llm
```

This writes `logs/benchmark_<timestamp>.json` and prints aggregate stats (total/avg/min/max turn duration plus LLM failure counts). For deterministic fallbacks use `--no-llm`.

Summarize historical LLM metrics:

```bash
python scripts/llm_perf_report.py
```

Optional `--log-path` lets you point at archived metrics files.

## Making Sense of the Logs

- **`logs/llm_calls.log`**: JSON lines with agent/model/duration/success. Feed into `scripts/llm_perf_report.py` or any log pipeline.
- **`logs/turn_perf.log`**: JSON lines per turn (`turn`, `duration_ms`, `llm_calls`, `llm_failures`, `phase`). Useful for spotting pacing issues and unstable phases.
- **`logs/benchmark_*.json`**: Full benchmark summaries you can diff between builds.

Use these artifacts to pinpoint regressions, tune timeout/caching, and validate improvements before demos.
