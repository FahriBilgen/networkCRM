# Theme Authoring Guide

This guide covers everything needed to create a standalone theme/scenario pack
that the Fortress Director runtime can load at turn time.

## ThemeConfig Schema

Each theme ships as a JSON document that matches the dataclasses under
`fortress_director.themes.schema`. The top level structure looks like:

```json
{
  "id": "siege_default",
  "label": "Siege of Lornhaven",
  "description": "One line market copy.",
  "map": { "width": 8, "height": 8, "layout": [["wall", "yard"]] },
  "npcs": [{ "id": "marshal_edda", "name": "Marshal Edda", "role": "commander", "x": 4, "y": 3 }],
  "initial_metrics": {
    "turn": 1,
    "turn_limit": 12,
    "wall_integrity": 70,
    "morale": 60,
    "resources": 55
  },
  "event_graph_file": "siege_default_graph.json",
  "safe_function_overrides": { "reinforce_wall": { "gas_cost": 2 } },
  "endings": [
    { "id": "victory", "label": "Hold the Wall", "conditions": { "wall_integrity_min": 60 } }
  ]
}
```

Required keys:

- `id`, `label`, `description`: unique identifiers for registry display.
- `map`: `width`, `height`, and a `layout` grid of tile ids.
- `npcs`: list of `ThemeNpcSpec` objects with coordinates.
- `initial_metrics`: seed values merged into `GameState.metrics`.
- `event_graph_file`: relative or absolute path to the event graph JSON/YAML.
- `safe_function_overrides`: optional tuning map (function name -> overrides).
- `endings`: ordered list of `ThemeEndingSpec` entries for the evaluator.

## Map Layout Format

The `layout` array is interpreted as rows of tile ids (strings). Tiles can be
semantic identifiers like `wall`, `tower`, `yard`, `shield`, or any string used
by your UI. Layout dimensions must match `map.width` and `map.height`. The
player spawn defaults to the center tile and inherits the tile id as the room
name so agents can reason about the starting area.

## NPC Definition Guidelines

Every NPC entry needs a stable `id` plus `name`, `role`, and absolute `x`/`y`
coordinates. Optional `tags` help the planner reason about certain roles (for
example `"leader"`, `"synthetic"`, `"logistics"`). NPCs are spawned in
`GameState.npc_locations` exactly as defined, so additional metadata such as
`hostile` or `stance` may also be provided if needed.

## Event Graph Format

Event graphs are described in separate JSON or YAML files referenced by
`event_graph_file`. The file must contain:

```json
{
  "entry_id": "start",
  "nodes": [
    {
      "id": "start",
      "description": "Opening beat",
      "tags": ["calm"],
      "next": { "default": "escalation" }
    }
  ]
}
```

`entry_id` identifies the first node. Each node includes a `description`, an
optional list of `tags`, and a `next` mapping (choice -> next node id). Nodes
can also set `is_final: true` to mark an ending beat. The
`narrative.theme_graph_loader` helper reads this format and produces an
`EventGraph` instance for the turn manager.

## Ending Conditions

`ThemeEndingSpec.conditions` defines numeric thresholds checked in order. The
ending evaluator supports:

- `wall_integrity_min`
- `morale_min`
- `threat_max`
- `resources_min`
- `npc_survival_min_ratio`
- `structure_integrity_min_ratio`

If an ending's conditions all pass for the current `GameState`, that ending id
is returned. If none match the fallback id (`fallback_default`) is used. Author
endings from most specific to broadest to keep behavior predictable.

## Safe Function Overrides

Each safe function can be tuned per theme by overriding `gas_cost`,
`planner_weight`, or `enabled`. Example:

```json
"safe_function_overrides": {
  "reinforce_wall": { "gas_cost": 2, "planner_weight": 1.3 },
  "deploy_archers": { "enabled": false }
}
```

Overrides are merged with any global metadata and applied before planner
selection. Disabling a function removes it from the planner's consideration for
that theme.

## Embedding Through the Engine API

External games can embed the director loop by instantiating
`fortress_director.engine.api.FortressDirectorEngine`. The wrapper exposes:

```python
from fortress_director.engine.api import FortressDirectorEngine

engine = FortressDirectorEngine("siege_default")
engine.inject_external_event({"type": "battle_started", "label": "North gate"})
delta = engine.run_turn({"id": "hold_position"})
```

- `get_state_snapshot()` returns a compact dict with metrics, NPC positions, and
  structures.
- `inject_external_event(event_dict)` queues host-side events (rain, reinforcements).
- `run_turn(player_choice=None)` advances the narrative and returns a delta with
  `npc_positions`, `structures`, `markers`, `atmosphere`, and suggested host
  events. The delta also echoes processed external events for synchronization.

With this interface a strategy or RPG host can treat the director as a black box
that consumes high-level events and produces dramatic beats plus suggested UI
effects, all without modifying the engine core.
