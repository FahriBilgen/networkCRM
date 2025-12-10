# World Tick Simulation Overview

The world tick is a deterministic step that advances the siege even if the player
does nothing. It runs once every turn before the director builds the narrative
intent and it affects multiple subsystems:

## NPC Fatigue & Morale

- Every NPC gains +1 fatigue per tick (capped at 100). High fatigue tilts
  atmospheric cues toward exhaustion.
- Morale drifts by ±1 toward the neutral value of 50, so elated units cool off
  while shaken units regroup.
- Combat handlers add larger fatigue and morale swings immediately after a
  skirmish so attrition carries into the next tick.

## Food Consumption

- Food rations are consumed deterministically: `food -= max(1, npc_count // 2)`.
- Consumption is capped by what remains in the stockpile, and the tick summary
  reports how many rations were spent that turn.
- Low food levels push HUD indicators and renderer cues toward “hunger” phrasing.

## Structures on Fire

- Each burning structure loses 1–3 integrity per tick. Fires extinguish when
  integrity reaches zero.
- The tick summary lists any damaged structures and their integrity deltas so
  the renderer can describe smoke, ash, and crackling beams.

## Combat Engine Principles

- Melee engagements call `resolve_skirmish`, which computes combat power from
  skills, morale, and fatigue, then produces deterministic casualty counts,
  morale deltas, and optional structure damage.
- Safe function handlers apply those deltas to NPC health/morale, synchronize
  structures, and record metrics for the threat model.
- Combat summaries include per-skirmish casualties plus optional structure IDs
  so the UI and renderer can mention “Skirmish near inner_gate – 2 vs 3 casualties”.

## Metrics Tracking

- `metrics["combat"]` now tracks total skirmishes, friendly/enemy casualties,
  and the last skirmish’s casualty counts.
- ThreatModel recent hostility incorporates both the total number of skirmishes
  and last-turn casualties, making repeated fights visibly raise the threat curve.

## Turn Order

The full turn pipeline now runs in this fixed order:

1. `world_tick` (fatigue, morale, food, fires, passive events)
2. `threat_model`
3. `event_curve`
4. `event_graph`
5. `director`
6. `planner`
7. `executor`
8. `renderer`
9. final endgame checks

The UI surfaces the tick summary in the HUD (food, average morale/fatigue) and
in the log (“World Tick: 5 food consumed, avg fatigue 61”). Combat summaries
also feed the log and renderer to reinforce the sense of a living siege.
