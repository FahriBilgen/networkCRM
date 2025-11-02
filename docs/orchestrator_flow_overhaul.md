# Orchestrator Flow Overhaul

## Objectives
- Reduce redundant Judge calls, prioritise impactful reactions.
- Integrate DirectorAgent decisions prior to EventAgent to steer narrative arcs.
- Enforce safe function quotas and retry logic without breaking determinism.

## Proposed Turn Sequence
1. **State Snapshot & Metrics** (unchanged) – compute glitch, recovery, determine final turn.
2. **Director Stage (new):**
   - Provide summary to DirectorAgent.
   - Apply returned `forced_safe_functions` immediately (before world/event generation).
   - Store `directives`, `risk_budget_adjustment`, `finale_stage_hint` in state.
3. **WorldAgent** – receives directives + safe function results for context.
4. **EventAgent** – sees directives, novelty flags, allowed safe function count, persistent motifs.
5. **CreativityAgent** – ensures enriched scene; fallback if invalid.
6. **PlannerAgent** – processes directives + event output, yields `plan_steps` and recommended safe functions.
7. **CharacterAgent** – executes plan; may emit safe functions.
8. **Judge Loop** – deduplicated evaluation:
   - Filter `character_output` by unique `(name, intent, action, speech)`.
   - Skip placeholder/autonomous entries lacking effects or speech.
   - Cache verdict by hash to prevent repeat calls within same turn.
9. **RulesEngine** – apply validated effects; incorporate Judge suggestions if provided.
10. **Safe Function Queue Execution** – merge from event/character/world/planner outputs; enforce limits (max 5 per turn, per-family caps).
11. **Post-SF World Refresh** – if environment-changing function ran, optionally re-run WorldAgent describe in lightweight mode.
12. **State Persist, Logging** – update runs dir, logs, summary.

## Safe Function Execution Policy
- Collect calls from agents with metadata `source` (event/character/planner/director/judge_suggestion).
- Validate per-turn quotas using `FunctionCallValidator` extensions.
- If queue empty and directives demanded action, raise warning (no fallback auto-call).
- On validation failure, rollback to last checkpoint and mark turn as `error_recovered` for analytics.

## Judge Deduplication Mechanism
- Maintain `judge_cache` dict keyed by SHA256 of `scene + action + speech + choice`.
- Before calling JudgeAgent, check cache; reuse verdict if available.
- If Judge returns `suggestions`, store in `state['judge_suggestions']` for next turn planning.

## Metrics & Glitch Adjustments
- Replace hard floor with easing function: `glitch = max(floor, prev_glitch + delta)` where `floor` increases slowly with drama mode.
- Align summary text to reflect glitch effects (no more "routine day" when anomalies occur).

## Error Handling & Retries
- If any agent returns invalid JSON: attempt once more (if model call allowed) else fail turn gracefully and log.
- Provide instrumentation counters for `invalid_json_retries`, `safe_function_denied`, `judge_cache_hits`.

## Implementation Steps
1. Add DirectorAgent class & integration into orchestrator.
2. Implement safe function quota logic + metadata tracking.
3. Introduce judge cache + placeholder filtering.
4. Update glitch handling and summary generation.
5. Adjust turn result payload to include `directives`, `safe_function_results`, `judge_suggestions` for transparency.
