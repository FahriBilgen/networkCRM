# Finale Design Outline

## Narrative Structure
1. **Build-Up (Turns 1-4)**
   - Establish siege pressure, resource scarcity, NPC relationships.
   - DirectorAgent monitors metrics; if variance low, triggers drama mode.
2. **Escalation (Turns 5-7)**
   - Major events escalate (wall breaches, traitor reveal).
   - Safe functions emphasise structural repairs, patrol coordination, resource trades.
3. **Crisis (Turns 8-9)**
   - "The Wall Collapses" triggered via `queue_major_event` -> `resolve_collapse` safe function.
   - Player forced into high-stakes choices; metrics shift heavily.
4. **Resolution (Turn 10)**
   - Outcome determined by metrics (morale/order/resources) + story_progress.
   - Prepare epilogue branching (win / loss / bittersweet).

## Mechanics Mapping
- **Glitch Behaviour:** In crisis stage glitch volatility increases; allow Director to authorize `trigger_environment_hazard` for narrative glitches.
- **NPC Roles:**
  - Rhea: frontline scout -> can `schedule_npc_activity` to coordinate evacuations.
  - Boris: trade/funding -> manages `open_trade_route` / `transfer_item`.
- **Structures:** Western wall, inner gate, watchtower, granary. Each with durability metrics updated via safe functions.

## Finale Trigger Conditions
- `story_progress.act` reaches 0.75 + `major_events_triggered >= 2`.
- `queue_major_event('wall_collapse', trigger_turn=current_turn+1)`.
- DirectorAgent sets `finale_stage_hint` to `"prepare_finale"`.

## Player Feedback
- Update world descriptions to highlight structural states (cracks, reinforcements).
- Provide explicit consequences when safe functions trigger (e.g., "Reinforcements strengthen the western wall by 2.").
- Summaries mention trade-offs (resources spent vs morale boost).

## Epilogue Paths
- **Victory:** High morale/order; collapse contained; NPC survival counts high.
- **Pyrrhic:** Wall holds but high corruption/glitch; epilogue emphasises lingering anomalies.
- **Defeat:** Order or morale below threshold; evacuation fails.

## Implementation Notes
- Add templates for finale events in `data/` (structured JSON describing scenes, safe function requirements).
- Extend RulesEngine to interpret finale-specific flags and apply larger metric swings.
- Ensure safe function validators consider finale context (e.g., allow higher deltas during crisis).
