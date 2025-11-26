# Event Graph — Design and Behavior

This document describes the `EventNode` / `EventGraph` system used in the demo and pipeline.

Overview
- `EventNode`: lightweight dataclass with `id`, `description`, `tags`, `next` (mapping of signals -> node id), and `is_final` flag.
- `EventGraph`: given a current node, returns the next node using deterministic, seeded weighted selection.

Determinism
- The selection seed is computed from the game snapshot: `turn + order * 17`.
- Given identical snapshots (turn/order), the chosen next node is deterministic.

Weights & Tag Boosts
- Base weight is `1.0 + 0.25 * len(tags)`.
- Additional boosts:
  - If `threat_phase == "collapse"` and node has `collapse` tag, weight += 2.5
  - If morale < 25 and node has `despair` tag, weight += 1.5
  - If resources > 40 and node has `hope` tag, weight += 1.5

Demo Graph
- The canonical demo graph is defined in `fortress_director.narrative.demo_graph` and exposes `DEMO_EVENT_GRAPH`.
- Entry node: `node_intro`. Final node: `node_final` (has `is_final=True`).

Integration Notes
- `TurnManager` advances the event node each turn and persists the `last_event_node` in `GameState`.
- `DirectorAgent` and `WorldRendererAgent` accept `event_node` and `event_seed` context for prompt generation.

Testing
- See `tests/narrative/` for focused unit tests verifying dataclass defaults, deterministic selection, and demo graph loading.
# Event Graph Overview

The event graph is the spine of the new dramatic pacing system. Instead of
rolling purely on random cues, every turn advances through a curated sequence of
`EventNode` beats that describe what the fortress drama should highlight next.

Each node carries:

- **id** - canonical identifier shared across the Director, Planner, and UI.
- **description** - prose snippet injected into prompts and the turn log.
- **tags** - narrative markers such as `battle`, `sabotage`, `hope`, `collapse`,
  or `despair` that drive option palettes and renderer atmosphere.
- **next** - mapping of condition labels to the id of the next node.
- **is_final** - marks the terminating node that forces endgame handling.

## Selecting the Next Node

The `EventGraph` looks at three pieces of state when advancing:

1. **Threat phase** - nodes tagged with `collapse` get a heavy weight during the
   threat model's collapse phase.
2. **Morale / resources** - low morale (< 25) promotes `despair` nodes while
   strong resources (> 40) promote `hope` nodes.
3. **Deterministic seed** - `turn + (order * 17)` seeds a weighted roll so
   results remain reproducible for a given save.

All of the node ids listed in `current_node.next` become candidates. Their tags
modify weights, then the deterministic roll selects the next beat.

## Graph Finalization

When the selected node's `is_final` flag is true, the EndgameDetector triggers
immediately with a reason of `Reached final graph node`. The node's tags steer
the recommended endgame tone:

- `collapse` -> `desperate`
- `hope` -> `heroic`
- `battle` -> `strategic`

UI surfaces the final node description and immediately opens the final screen.

## Demo Graph Flow

The bundled demo graph contains 11 nodes:

```
node_intro -> node_scout_activity -> node_minor_breach -> node_reinforcement
           \-> node_sabotage <-/
node_major_assault -> node_wall_collapse -> node_last_stand
                                         \-> node_negotiation -> node_final
node_escape_plan --/
```

Branches focus on sabotage detours, reinforcement swings, or morale pivots into
escape planning. Every subsystem (Director, Planner, Renderer, UI) now reads the
same graph context, giving the demo a deliberate beginning -> rise -> peak ->
collapse -> finale arc.
