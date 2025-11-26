from __future__ import annotations

from typing import Any, Dict

from fortress_director.core.function_registry import bind_handler, load_defaults
from fortress_director.core.state_store import GameState

load_defaults()


def _response(
    log: str,
    *,
    status: str = "applied",
    metrics: Dict[str, int] | None = None,
    effects: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    return {
        "status": status,
        "log": log,
        "metrics": metrics or {},
        "effects": effects or {},
    }


def inspire_troops_handler(
    game_state: GameState, speech: str, bonus: int | None = None
) -> Dict[str, Any]:
    boost = max(1, int(bonus or 2))
    morale = game_state.adjust_metric("morale", boost)
    log = f"Inspiration delivered: {speech}"
    return _response(
        log,
        metrics={"morale": boost},
        effects={"morale": morale},
    )


def calm_civilians_handler(
    game_state: GameState, zone: str, effort: int
) -> Dict[str, Any]:
    reduction = -max(1, int(effort))
    panic_value = game_state.adjust_metric("panic", reduction)
    log = f"Civilian calming teams deployed to {zone}."
    return _response(
        log,
        metrics={"panic": reduction},
        effects={"zone": zone, "panic": panic_value},
    )


def hold_speech_handler(
    game_state: GameState, topic: str, audience: str
) -> Dict[str, Any]:
    morale = game_state.adjust_metric("morale", 2)
    log = f"Court speech on '{topic}' for {audience}."
    return _response(log, metrics={"morale": 2}, effects={"morale": morale})


def punish_treason_handler(
    game_state: GameState, npc_id: str, severity: int
) -> Dict[str, Any]:
    morale_hit = -max(1, int(severity))
    threat_delta = -1
    game_state.adjust_metric("morale", morale_hit)
    game_state.adjust_metric("threat", threat_delta)
    log = f"{npc_id} punished for treason. Morale {morale_hit}, threat {threat_delta}."
    return _response(log, metrics={"morale": morale_hit, "threat": threat_delta})


def reward_bravery_handler(
    game_state: GameState, npc_id: str, reward: str
) -> Dict[str, Any]:
    morale = game_state.adjust_metric("morale", 1)
    log = f"{npc_id} rewarded with {reward}."
    return _response(log, metrics={"morale": 1}, effects={"morale": morale})


def celebrate_small_victory_handler(
    game_state: GameState, location: str
) -> Dict[str, Any]:
    game_state.add_state_tag(f"victory_{location}")
    morale = game_state.adjust_metric("morale", 1)
    log = f"Celebration held at {location}."
    return _response(log, metrics={"morale": 1}, effects={"morale": morale})


def reduce_panic_handler(
    game_state: GameState, zone: str, amount: int
) -> Dict[str, Any]:
    delta = -abs(int(amount))
    panic = game_state.adjust_metric("panic", delta)
    log = f"Panic reduced by {abs(delta)} in {zone}."
    return _response(log, metrics={"panic": delta}, effects={"panic": panic})


def hold_council_meeting_handler(game_state: GameState, agenda: str) -> Dict[str, Any]:
    game_state.add_log_entry(f"Council meeting agenda: {agenda}")
    log = f"Council convened to discuss {agenda}."
    return _response(log)


def comfort_wounded_handler(
    game_state: GameState, ward: str, care: int
) -> Dict[str, Any]:
    boost = max(1, int(care))
    morale = game_state.adjust_metric("morale", boost)
    log = f"Wounded comforted in {ward} (+{boost} morale)."
    return _response(log, metrics={"morale": boost}, effects={"morale": morale})


def assign_morale_officer_handler(
    game_state: GameState, npc_id: str, sector: str
) -> Dict[str, Any]:
    game_state.set_flag(f"morale_officer_{sector}")
    log = f"{npc_id} assigned as morale officer for {sector}."
    return _response(log, effects={"npc_id": npc_id, "sector": sector})


bind_handler("inspire_troops", inspire_troops_handler)
bind_handler("calm_civilians", calm_civilians_handler)
bind_handler("hold_speech", hold_speech_handler)
bind_handler("punish_treason", punish_treason_handler)
bind_handler("reward_bravery", reward_bravery_handler)
bind_handler("celebrate_small_victory", celebrate_small_victory_handler)
bind_handler("reduce_panic", reduce_panic_handler)
bind_handler("hold_council_meeting", hold_council_meeting_handler)
bind_handler("comfort_wounded", comfort_wounded_handler)
bind_handler("assign_morale_officer", assign_morale_officer_handler)
