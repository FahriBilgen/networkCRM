# Safe Function API Expansion Design

## Goals
- Enable agents to perform full-spectrum world management actions (movement, resource logistics, structural upkeep, story pacing) without bypassing deterministic safety.
- Maintain validator + rollback guarantees for every new capability.
- Provide meaningful metadata so downstream systems (UI, analytics, narration) can reflect changes immediately.

## Function Families

### 1. World & Environment
| Name | Args | Behaviour | Validator Highlights | Rollback Data |
|------|------|-----------|----------------------|---------------|
| `set_time_of_day` | `time_slot: str` | Update `state['time']` and append to history | Ensure value in enum {dawn, morning, noon, dusk, night}; prevent consecutive duplicates | Time + previous slot |
| `set_weather_pattern` | `pattern: str`, `duration: int` | Persist multi-turn weather lock; updates `_world_lock_until` | Validate pattern id; duration 1-6; ensures lock doesn't regress | Lock window metadata |
| `trigger_environment_hazard` | `hazard_id: str`, `severity: int` | Add entry to `state['environment_hazards']` with countdown | hazard_id non-empty; severity 1-5 | Hazard entry |

### 2. Structures & Defences
| Name | Args | Behaviour | Validator | Rollback |
|------|------|-----------|----------|----------|
| `reinforce_structure` | `structure_id: str`, `amount: int` | Increment durability metric; logs cause | structure exists; amount 1-5 | Durability snapshot |
| `repair_breach` | `section_id: str`, `resources_spent: int` | Consume resources; mark section status | ensures resources >= cost; status transitions valid | Section status + resource delta |
| `set_watcher_route` | `route_id: str`, `npc_ids: List[str]` | Assign route plan to watchers | route defined; npcs exist | Route assignment |

### 3. NPC & Faction Operations
| Name | Args | Behaviour | Validator | Rollback |
|------|------|-----------|----------|----------|
| `schedule_npc_activity` | `npc_id`, `activity`, `duration` | Append to `npc_schedule` queue | Activity in whitelist; duration 1-4 | Scheduled entry |
| `spawn_patrol` | `patrol_id`, `members: List[str]`, `path: List[str]` | Create patrol record for simulation tick | Validate rooms exist; member ids available | Patrol record |
| `resolve_combat` | `attacker`, `defender`, `outcome` | Update status/metrics based on template outcome | outcome in {attacker_win, defender_win, stalemate}; ensures NPCs exist | HP/status snapshot |
| `transfer_item` | `from_id`, `to_id`, `item_id` | Move item between inventories | Entities exist; item availability check | Both inventories |

### 4. Resources & Economy
| Name | Args | Behaviour | Validator | Rollback |
|------|------|-----------|----------|----------|
| `adjust_stockpile` | `resource_id`, `delta`, `cause` | Modify structured stockpile (wood, ore, food) | delta int; resource id valid; enforce floor 0 | Stockpile snapshot |
| `open_trade_route` | `route_id`, `risk`, `reward` | Register active trade route with timers | route unique; risk/reward bounds | Route record |
| `close_trade_route` | `route_id`, `reason` | Remove active route, log aftermath | route must exist | Removed route |

### 5. Narrative & Progression
| Name | Args | Behaviour | Validator | Rollback |
|------|------|-----------|----------|----------|
| `queue_major_event` | `event_id`, `trigger_turn` | Append to `state['scheduled_events']` | event template exists; trigger >= current_turn+1 | Scheduled entry |
| `advance_story_act` | `act_id`, `progression: float` | Update story progression meter; may unlock finale | act valid; progression 0-1; monotonic | Act progression |
| `lock_player_option` | `option_id`, `reason` | Prevent option from appearing next turns | option id non-empty; reason string | Lock entry |

## State Schema Impact
- Add new top-level sections: `environment_hazards`, `structures`, `npc_schedule`, `patrols`, `combat_log`, `stockpiles`, `trade_routes`, `scheduled_events`, `story_progress`.
- Provide helper accessors in `StateStore` for consistent default creation and deep copy handling.
- Track schema version in `state['schema_version']` to facilitate migration.

## Validators & Gas Budget
- Introduce `FunctionCallValidator` configuration to set per-family call limits per turn (e.g., max 2 structure edits, 3 resource adjustments).
- Extend validator to check cooldowns by consulting `state['sf_history']` entries.
- Update rollback system to store pre-call checkpoint metadata including function family for targeted rollback metrics.

## Testing Strategy
- Unit tests per new function ensuring validation errors, state mutations, rollback on failure.
- Integration test scenario: spawn patrol -> move -> resolve combat -> adjust stockpile -> queue major event; verify deterministic diff and logs.
- Live-model acceptance checklists: Event/Character agents produce new safe function payloads, executed end-to-end with real models.

## Open Considerations
- Need canonical list of structure IDs / resource IDs defined in settings or data JSON.
- Determine how combat outcomes affect metrics (morale, order, glitch) to keep consistency with RulesEngine.
- Ensure trade route risk ties into glitch or corruption metrics for systemic feedback.
