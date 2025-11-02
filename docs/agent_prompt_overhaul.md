# Agent Prompt Overhaul Blueprint

## Objectives
- Ensure every agent outputs actionable directives, including `safe_functions`, with minimal retries.
- Embed long-term pacing (acts, finale build-up) via dedicated Director layer.
- Provide explicit schema reminders, examples, and guardrails to reduce invalid JSON and meta responses.

## Agents & Roles

### DirectorAgent (New)
- **Purpose:** Evaluate world state before each turn to adjust strategic levers (risk budget, major event plan, structural priorities).
- **Inputs:** Metrics snapshot, flags, scheduled events, story progression, recent glitches, trade routes.
- **Outputs:** JSON payload with fields:
  - `directives`: list of high-level instructions (e.g., `"prioritise_structure_repairs"`).
  - `forced_safe_functions`: optional list of deterministic function calls (for guaranteed actions like `set_time_of_day`).
  - `risk_budget_adjustment`: integer.
  - `finale_stage_hint`: optional string for upcoming act.
- **Prompt Notes:** Provide world summary and emphasise deterministic format, limit to <= 3 directives, reference valid safe function names.

### EventAgent
- Include `directives` from Director in context.
- Add prompt section: "If the scene requires environment or structural updates, include up to 2 safe function calls." Provide JSON example with `safe_functions` entry like:
```json
{
  "safe_functions": [
    {
      "name": "reinforce_structure",
      "kwargs": {
        "structure_id": "western_wall",
        "amount": 2
      },
      "metadata": {
        "reason": "enemy siege pressure"
      }
    }
  ]
}
```
- Emphasise novelty enforcement: include recent events summary, highlight penalties for repetition.

### PlannerAgent (Existing)
- Expand to interpret Director directives: break down into step plan for CharacterAgent.
- Output fields: `plan_steps`, `recommended_safe_functions`, `npc_focus`. Provide sample JSON.

### CreativityAgent
- Add fallback instructions: if unsure, rewrite scene by restating conflicts, injecting motif from `creative_pool`. Provide rules to avoid returning empty string; fallback if tokens < 20 characters.
- Add `novelty_triggers` output to feed EventAgent on next turn (e.g., `{"motif_hint": "betrayal"}`).

### CharacterAgent
- Provide template emphasising `speech` max 180 chars, require `effects` and optional `safe_functions`. Example of using `transfer_item` or `schedule_npc_activity`.
- Accept `plan_steps` from Planner; for each step decide whether to execute via safe function.

### JudgeAgent
- Extend prompt with ability to suggest corrections in structured form:
```json
{
  "consistent": false,
  "reason": "Combat outcome contradicts prior injuries",
  "suggestions": [
    {
      "type": "safe_function",
      "name": "resolve_combat",
      "kwargs": {"attacker": "rhea", "defender": "palisade_raiders", "outcome": "stalemate"}
    }
  ]
}
```
- Ensure `suggestions` optional; orchestrator will detect and feed back to Planner/Event if present.

## Prompt File Updates
- Files to revise: `prompts/event_prompt.txt`, `prompts/world_prompt.txt`, `prompts/character_prompt.txt`, `prompts/planner_prompt.txt`, `prompts/creativity_prompt.txt`, `prompts/judge_prompt.txt`.
- For each: add context blocks with available safe functions, remind of schema, limit to <= 3 suggestions.
- Document example prompts/responses in `docs/prompt_examples/*.md` for QA.

## Validation & Testing
- Dry run with local Ollama models after each prompt update; verify JSON parsing success.
- Record real-model transcripts for regression (store under `fortress_director/logs/` with timestamps).
- Automate prompt regression test: script sends canned context to agent, asserts presence of `safe_functions` when directives indicate structural change.
