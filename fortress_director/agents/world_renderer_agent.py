"""World renderer agent that asks an LLM for narrative output."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Iterable, List

from fortress_director.core.state_archive import (
    StateArchive,
    inject_archive_to_prompt,
)
from fortress_director.llm.cache import LLMCache, get_default_cache
from fortress_director.llm.metrics_logger import log_llm_metrics
from fortress_director.llm.model_registry import get_registry
from fortress_director.llm.ollama_client import (
    OllamaClient,
    OllamaClientError,
    generate_with_timeout,
)
from fortress_director.llm.profiler import profile_llm_call
from fortress_director.llm.runtime_mode import is_llm_enabled
from fortress_director.prompts.utils import load_prompt_template, render_prompt
from fortress_director.settings import SETTINGS

if TYPE_CHECKING:  # pragma: no cover - typing only
    from fortress_director.narrative.event_graph import EventNode

LOGGER = logging.getLogger(__name__)
PROMPT_FILENAME = "world_renderer_prompt.txt"

WORLD_RENDERER_FEW_SHOTS: List[Dict[str, Any]] = [
    {
        "narrative_block": (
            "The watch fires flickered as Ila's scouts slipped back inside. "
            "Fresh lashings now brace the north wall, and the gale has yet to quiet."
        ),
        "npc_dialogues": [
            {
                "speaker": "Quartermaster Lysa",
                "line": "Resources dip, but the wall stands for one more night.",
            },
            {
                "speaker": "Watcher Bren",
                "line": "Stormlight hid our patrols perfectly.",
            },
        ],
        "atmosphere": {
            "mood": "tense",
            "visuals": "Rain streaks across shield banners while torches sputter.",
            "audio": "Low thunder rolls across the battlements.",
        },
    },
    {
        "narrative_block": (
            "Saboteurs cracked the raider hoist, sending carts crashing. "
            "Inside the courtyard, lanterns glow warm as soldiers finally exhale."
        ),
        "npc_dialogues": [
            {
                "speaker": "Engineer Tomas",
                "line": "Their lifts will take days to rebuild.",
            },
            {"speaker": "Scout Ila", "line": "Eastern alleys are clear—for now."},
        ],
        "atmosphere": {
            "mood": "resolute",
            "visuals": "Steam rises from rain-soaked stone as dawn hints at the horizon.",
        },
    },
]


class WorldRendererAgent:
    """Produces final narrative payloads using Ollama."""

    def __init__(
        self,
        *,
        llm_client: OllamaClient | None = None,
        model_key: str = "world_renderer",
        prompt_path: Path | str | None = None,
        use_llm: bool = True,
    ) -> None:
        registry = get_registry()
        self._agent_key = model_key
        try:
            self._model_config = registry.get(model_key)
        except KeyError:
            LOGGER.warning(
                "Unknown world renderer model key %s; using default.", model_key
            )
            self._agent_key = "world_renderer"
            self._model_config = registry.get(self._agent_key)
        client = llm_client or (OllamaClient() if use_llm else None)
        self._llm_client: OllamaClient | None = client
        self._llm_enabled = use_llm and self._llm_client is not None
        self._registry = registry
        template_override = prompt_path if prompt_path is None else Path(prompt_path)
        self._prompt_template = load_prompt_template(PROMPT_FILENAME, template_override)
        runtime_config = SETTINGS.llm_runtime
        self._cache_enabled = bool(runtime_config.enable_cache)
        self._metrics_enabled = bool(runtime_config.log_metrics)
        self._llm_timeout = float(runtime_config.timeout_seconds)
        self._llm_max_retries = int(runtime_config.max_retries)
        self._llm_cache: LLMCache = get_default_cache()

    def render(
        self,
        world_state: Dict[str, Any],
        executed_actions: List[Dict[str, Any]],
        *,
        threat_phase: str | None = None,
        event_seed: str | None = None,
        event_node: "EventNode" | None = None,
        world_tick_delta: Dict[str, Any] | None = None,
        archive: StateArchive | None = None,
        turn_number: int = 0,
    ) -> Dict[str, Any]:
        """Return descriptive text derived from state + executed actions."""

        event_tags = list(event_node.tags) if event_node else []
        combat_summary = self._summarize_combat_actions(executed_actions)
        prompt = self._build_prompt(
            world_state,
            executed_actions,
            threat_phase=threat_phase,
            event_seed=event_seed,
            event_node=event_node,
            world_tick_delta=world_tick_delta,
            combat_summary=combat_summary,
            archive=archive,
            turn_number=turn_number,
        )
        if self._llm_enabled and is_llm_enabled():
            try:
                raw = self._call_llm(prompt)
                payload = self._parse_output(raw)
                payload["atmosphere"] = self._ensure_atmosphere(
                    payload.get("atmosphere"),
                    world_state,
                    executed_actions,
                    event_tags=event_tags,
                    world_tick_delta=world_tick_delta,
                    combat_summary=combat_summary,
                )
                return payload
            except (
                OllamaClientError,
                ValueError,
                json.JSONDecodeError,
                TimeoutError,
                RuntimeError,
            ) as exc:
                LOGGER.warning("World renderer LLM fallback triggered: %s", exc)
        fallback_payload = self._fallback_render(
            world_state,
            executed_actions,
            event_node=event_node,
            world_tick_delta=world_tick_delta,
            combat_summary=combat_summary,
        )
        fallback_payload["atmosphere"] = self._ensure_atmosphere(
            fallback_payload.get("atmosphere"),
            world_state,
            executed_actions,
            event_tags=event_tags,
            world_tick_delta=world_tick_delta,
            combat_summary=combat_summary,
        )
        return fallback_payload

    def render_final(self, final_context: Dict[str, Any]) -> Dict[str, Any]:
        """Render the dedicated final cinematic block."""

        path_info = final_context.get("final_path") or {}
        world_context = final_context.get("world_context") or {}
        event_history = world_context.get("event_history") or []
        decision_summary = self._summarize_final_decisions(event_history)
        npc_fates = world_context.get("npc_outcomes") or []
        structure_report = world_context.get("structure_outcomes") or []
        resource_summary = world_context.get("resource_summary") or {}
        leadership_note = self._build_leadership_note(resource_summary, path_info)
        closing_paragraphs = self._build_closing_paragraphs(
            path_info, decision_summary, world_context
        )

        return {
            "title": path_info.get("title", "Final Sequence"),
            "subtitle": path_info.get("summary", ""),
            "final_path": path_info,
            "decision_summary": decision_summary,
            "npc_fates": npc_fates,
            "structure_report": structure_report,
            "resource_summary": resource_summary,
            "threat": world_context.get("threat"),
            "leadership_note": leadership_note,
            "closing_paragraphs": closing_paragraphs,
            "atmosphere": self._final_atmosphere(path_info),
        }

    def _build_prompt(
        self,
        world_state: Dict[str, Any],
        executed_actions: List[Dict[str, Any]],
        *,
        threat_phase: str | None = None,
        event_seed: str | None = None,
        event_node: "EventNode" | None = None,
        world_tick_delta: Dict[str, Any] | None = None,
        combat_summary: List[Dict[str, Any]] | None = None,
        archive: StateArchive | None = None,
        turn_number: int = 0,
    ) -> str:
        atmosphere_cues = self._extract_cues(world_state)
        node_tags = list(event_node.tags) if event_node else []
        combat_text = [entry["text"] for entry in (combat_summary or [])]
        replacements = {
            "WORLD_STATE": json.dumps(world_state, ensure_ascii=False, indent=2),
            "EXECUTED_ACTIONS": json.dumps(
                executed_actions, ensure_ascii=False, indent=2
            ),
            "ATMOSPHERE_CUES": json.dumps(
                atmosphere_cues, ensure_ascii=False, indent=2
            ),
            "FEW_SHOTS": json.dumps(
                WORLD_RENDERER_FEW_SHOTS, ensure_ascii=False, indent=2
            ),
            "CURRENT_THREAT_PHASE": threat_phase or "unknown",
            "EVENT_SEED": event_seed or "none",
            "EVENT_NODE_DESCRIPTION": (
                event_node.description if event_node else "No event cue."
            ),
            "EVENT_NODE_TAGS": json.dumps(node_tags, ensure_ascii=False, indent=2),
            "WORLD_TICK_DELTA": json.dumps(
                world_tick_delta or {}, ensure_ascii=False, indent=2
            ),
            "COMBAT_OUTCOMES": json.dumps(
                combat_text or [], ensure_ascii=False, indent=2
            ),
            "STRUCTURES_ON_FIRE": str(self._count_active_fires(world_state)),
        }
        prompt = render_prompt(self._prompt_template, replacements)
        # Inject archive context if available
        if archive is not None and turn_number > 0:
            prompt = inject_archive_to_prompt(archive, turn_number, prompt)
        return prompt

    def _call_llm(self, prompt: str) -> str:
        assert self._llm_client is not None  # guarded by _llm_enabled
        cache_key = None
        if self._cache_enabled:
            cache_key = self._llm_cache.make_key(
                self._agent_key,
                self._model_config.name,
                prompt,
            )
            cached = self._llm_cache.get(cache_key)
            if cached is not None:
                return str(cached)
        options = self._registry.build_generation_options(self._agent_key)

        def _invoke() -> Dict[str, Any]:
            return generate_with_timeout(
                self._llm_client,
                model=self._model_config.name,
                prompt=prompt,
                response_format="json",
                options=options,
                timeout_seconds=self._llm_timeout,
                max_retries=self._llm_max_retries,
            )

        response, metrics = profile_llm_call(
            self._agent_key,
            self._model_config.name,
            _invoke,
        )
        if self._metrics_enabled:
            log_llm_metrics(metrics)
        if not metrics.success:
            if metrics.error_type == "TimeoutError":
                raise TimeoutError("World renderer LLM call timed out.")
            raise RuntimeError(
                f"World renderer LLM call failed ({metrics.error_type or 'UnknownError'})"
            )
        raw = response.get("response") if isinstance(response, dict) else None
        if not raw and isinstance(response, dict):
            raw = response.get("message", {}).get("content")
        if not raw:
            raise ValueError("World renderer LLM returned an empty response.")
        raw_str = str(raw)
        if cache_key and self._cache_enabled:
            self._llm_cache.set(cache_key, raw_str)
        return raw_str

    def _parse_output(self, payload: str | Dict[str, Any]) -> Dict[str, Any]:
        candidate = json.loads(payload) if isinstance(payload, str) else dict(payload)
        narrative = candidate.get("narrative_block")
        if not isinstance(narrative, str) or not narrative.strip():
            raise ValueError("World renderer response missing narrative_block.")
        dialogues: List[Dict[str, str]] = []
        for entry in candidate.get("npc_dialogues", []) or []:
            if not isinstance(entry, dict):
                continue
            speaker = entry.get("speaker")
            line = entry.get("line")
            if speaker and line:
                dialogues.append({"speaker": str(speaker), "line": str(line)})
        if not dialogues:
            dialogues = [{"speaker": "Narrator", "line": "The turn passes quietly."}]
        atmosphere = candidate.get("atmosphere") or {}
        if not isinstance(atmosphere, dict):
            atmosphere = {}
        return {
            "narrative_block": narrative.strip(),
            "npc_dialogues": dialogues,
            "atmosphere": atmosphere,
        }

    def _ensure_atmosphere(
        self,
        atmosphere: Dict[str, Any] | None,
        world_state: Dict[str, Any],
        executed_actions: List[Dict[str, Any]],
        *,
        event_tags: List[str],
        world_tick_delta: Dict[str, Any] | None = None,
        combat_summary: List[Dict[str, Any]] | None = None,
    ) -> Dict[str, str]:
        fallback = self._build_default_atmosphere(
            world_state,
            executed_actions,
            event_tags=event_tags,
            world_tick_delta=world_tick_delta,
            combat_summary=combat_summary,
        )
        if not atmosphere or not isinstance(atmosphere, dict):
            return fallback
        merged: Dict[str, str] = {}
        for key in ("mood", "visuals", "audio"):
            value = atmosphere.get(key)
            if isinstance(value, str) and value.strip():
                merged[key] = value.strip()
            else:
                merged[key] = fallback[key]
        return merged

    def _fallback_render(
        self,
        world_state: Dict[str, Any],
        executed_actions: List[Dict[str, Any]],
        *,
        event_node: "EventNode" | None = None,
        world_tick_delta: Dict[str, Any] | None = None,
        combat_summary: List[Dict[str, Any]] | None = None,
    ) -> Dict[str, Any]:
        turn_index = int(world_state.get("turn", 0))
        stability = int(world_state.get("world", {}).get("stability", 50))
        resources = int(world_state.get("world", {}).get("resources", 75))
        action_summaries = [
            f"{idx + 1}. {action.get('function')} succeeded."
            for idx, action in enumerate(executed_actions)
        ]
        if not action_summaries:
            action_summaries.append("No major maneuvers executed.")
        narrative_parts: List[str] = []
        if event_node:
            narrative_parts.append(event_node.description)
        narrative_parts.append(
            f"Turn {turn_index} concludes with stability at {stability} and "
            f"resources at {resources}."
        )
        if world_tick_delta:
            food_consumed = int(world_tick_delta.get("food_consumed") or 0)
            if food_consumed:
                narrative_parts.append(
                    f"Storerooms lose {food_consumed} rations to the day's upkeep."
                )
            avg_fatigue = world_tick_delta.get("avg_fatigue")
            if isinstance(avg_fatigue, (int, float)) and avg_fatigue > 70:
                narrative_parts.append("Defenders move with heavy, exhausted steps.")
            narrative_parts.extend(world_tick_delta.get("events", []))
        if combat_summary:
            narrative_parts.append(combat_summary[0]["text"])
        narrative_parts.extend(action_summaries)
        narrative_block = " ".join(narrative_parts)
        npc_dialogues = [
            {
                "speaker": "Quartermaster Lysa",
                "line": "Stockpiles are "
                + ("secure." if resources >= 70 else "running low."),
            },
            {
                "speaker": "Watcher Bren",
                "line": "Stability is "
                + ("rising." if stability >= 60 else "still fragile."),
            },
        ]
        node_tags = list(event_node.tags) if event_node else []
        atmosphere = self._build_default_atmosphere(
            world_state,
            executed_actions,
            event_tags=node_tags,
            world_tick_delta=world_tick_delta,
            combat_summary=combat_summary,
        )
        return {
            "narrative_block": narrative_block,
            "npc_dialogues": npc_dialogues,
            "atmosphere": atmosphere,
        }

    def _extract_cues(self, world_state: Dict[str, Any]) -> Dict[str, Any]:
        world = world_state.get("world", {})
        cues = {
            "threat_level": world.get("threat_level"),
            "stability": world.get("stability"),
            "resources": world.get("resources"),
            "weather": world.get("weather_pattern") or world_state.get("weather"),
            "recent_log": world_state.get("log", []),
        }
        return cues

    def _build_default_atmosphere(
        self,
        world_state: Dict[str, Any],
        executed_actions: List[Dict[str, Any]],
        *,
        event_tags: List[str] | None = None,
        world_tick_delta: Dict[str, Any] | None = None,
        combat_summary: List[Dict[str, Any]] | None = None,
    ) -> Dict[str, str]:
        metrics = world_state.get("metrics") or {}
        order = self._metric_value(metrics.get("order"))
        morale = self._metric_value(metrics.get("morale"))
        corruption = self._metric_value(metrics.get("corruption"))
        if corruption >= 40:
            mood = "grim"
        elif order >= 65 or morale >= 65:
            mood = "hopeful"
        else:
            mood = "tense"

        action_names = {
            str(action.get("function") or "").lower()
            for action in executed_actions
            if isinstance(action, dict)
        }
        if action_names & {"reinforce_wall", "patch_wall_section", "repair_gate"}:
            visuals = "Fresh braces clamp the fortress walls while torchlight slices through the haze."
        elif action_names & {"adjust_metric", "allocate_food", "move_npc"}:
            visuals = "Orderly patrols sweep the battlements as banners ripple along the duvar-like ramparts."
        else:
            visuals = "Storm-dark fortress walls loom above damp stone and flickering beacon fires."

        if mood == "hopeful":
            audio = "Signal horns and distant cheers rise over fading cannon fire."
        elif mood == "grim":
            audio = (
                "Heavy cannon shots and grinding siege winches echo beyond the walls."
            )
        else:
            audio = "Boots crunch across wet stone while rain and far-off artillery drum steadily."
        stockpiles = world_state.get("stockpiles") or {}
        food_level = self._metric_value(stockpiles.get("food"))
        fires = self._count_active_fires(world_state)
        avg_fatigue = (
            world_tick_delta.get("avg_fatigue")
            if isinstance(world_tick_delta, dict)
            else None
        )
        if isinstance(avg_fatigue, (int, float)) and avg_fatigue > 70:
            mood = "weary"
            audio = "Hoarse orders and dragging boots mingle with the wind."
        if food_level < 20 or (
            world_tick_delta
            and world_tick_delta.get("food_consumed")
            and food_level < 40
        ):
            mood = "grim"
            visuals = (
                "Empty storerooms and ration lines stretch beneath fluttering pennants."
            )
        if fires:
            visuals = (
                "Smoke crawls over scorched stone while embers glow in shattered beams."
            )
            audio = "Crackling fires and collapsing beams punctuate the distant siege."
        casualty_load = 0
        for entry in combat_summary or []:
            outcome = entry.get("outcome") or {}
            casualty_load += int(outcome.get("attackers_casualties") or 0)
            casualty_load += int(outcome.get("defenders_casualties") or 0)
        if casualty_load >= 4 and fires == 0:
            mood = "dire"
            visuals = "Medics rush stretchers through soot as banners sag in the furnace glow."
            audio = "Low, urgent orders mingle with the groans of the wounded."
        tag_set = {str(tag).lower() for tag in (event_tags or []) if tag}
        if "battle" in tag_set:
            mood = "fierce"
            visuals = "Smoke and hot metal wash over shattered parapets as sparks fly."
            audio = "Clashing steel and shouted orders drown the wind."
        elif "sabotage" in tag_set:
            mood = "uneasy"
            visuals = (
                "Whispers drift through shadowed corridors while lanterns flicker low."
            )
            audio = "Soft footfalls and distant, hollow knocks betray hidden movements."
        elif "hope" in tag_set:
            mood = "hopeful"
            visuals = (
                "Sunlight breaks through soot clouds, warming banners and lifted faces."
            )
            audio = "Calm wind carries quiet cheers beneath steady drums."
        elif "collapse" in tag_set:
            mood = "dire"
            visuals = "Walls shake, rubble glows with firelight, and embers rain across the courtyard."
            audio = (
                "Stone groans, timbers crack, and roaring flames swallow every shout."
            )
        return {
            "mood": mood,
            "visuals": visuals,
            "audio": audio,
        }

    def _summarize_final_decisions(self, event_history: List[Dict[str, Any]]) -> str:
        if not event_history:
            return "The final choices blur into the roar of siege drums."
        snippets: List[str] = []
        for entry in event_history[-3:]:
            if not isinstance(entry, dict):
                continue
            for key in ("scene", "summary", "text", "description"):
                text = entry.get(key)
                if text:
                    snippets.append(str(text).strip())
                    break
        if not snippets:
            return "The final choices blur into the roar of siege drums."
        return " / ".join(snippets)

    def _build_leadership_note(
        self,
        resource_summary: Dict[str, Any],
        path_info: Dict[str, Any],
    ) -> str:
        morale = int(resource_summary.get("morale", 50))
        tone = str(path_info.get("tone") or "somber").lower()
        if morale >= 65:
            return "Command exits the finale resolute; alliances hold for another campaign."
        if morale <= 30:
            return "The commander records apologies alongside orders; every survivor feels the toll."
        if tone in {"tragic", "ominous"}:
            return "Leadership fractures under the strain, demanding urgent reforms."
        return "Leaders promise a brief respite before the next mobilization."

    def _build_closing_paragraphs(
        self,
        path_info: Dict[str, Any],
        decision_summary: str,
        world_context: Dict[str, Any],
    ) -> List[str]:
        threat = world_context.get("threat") or {}
        resource_summary = world_context.get("resource_summary") or {}
        paragraphs: List[str] = []
        paragraphs.append(
            path_info.get("summary") or "The finale concludes with uncertainty."
        )
        if decision_summary:
            paragraphs.append(f"The last turns: {decision_summary}.")
        else:
            paragraphs.append("Actions fall away into the hush before dawn.")
        paragraphs.append(
            "Morale {morale}, resources {resources}, threat phase {phase}.".format(
                morale=resource_summary.get("morale", 0),
                resources=resource_summary.get("resources", 0),
                phase=threat.get("phase", "unknown"),
            )
        )
        return paragraphs[:3]

    def _final_atmosphere(self, path_info: Dict[str, Any]) -> Dict[str, str]:
        tone = str(path_info.get("tone") or "somber").lower()
        if tone == "triumphant":
            mood = "uplifted"
            visuals = "Sunlight breaks over banners and drifting ash."
            audio = "Distant horns resolve into a victorious chorus."
        elif tone in {"defiant", "hopeful"}:
            mood = "resolute"
            visuals = "Armor gleams beside field fires while smoke thins toward dawn."
            audio = "Measured drums steady breathing as horns fade."
        elif tone in {"eerie", "ominous"}:
            mood = "unsettling"
            visuals = "Mirrored fog rolls through alleys, bending every ember's glow."
            audio = "A low electrical hum mingles with hushed choirs."
        else:
            mood = "somber"
            visuals = (
                "Charcoal clouds and lantern halos paint defenders in amber relief."
            )
            audio = "Muted bells answer the hush of exhausted troops."
        return {"mood": mood, "visuals": visuals, "audio": audio}

    def _summarize_combat_actions(
        self, executed_actions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        summaries: List[Dict[str, Any]] = []
        for action in executed_actions:
            effects = action.get("effects") or {}
            if not isinstance(effects, dict):
                continue
            combat = effects.get("combat")
            if not isinstance(combat, dict):
                continue
            outcome = combat.get("outcome") or {}
            attackers = int(outcome.get("attackers_casualties") or 0)
            defenders = int(outcome.get("defenders_casualties") or 0)
            structure = combat.get("structure") or {}
            structure_name = structure.get("id") or structure.get("kind")
            text = (
                f"{action.get('function', 'engagement')} reports "
                f"{attackers} attackers down vs {defenders} defenders"
            )
            if structure_name:
                text += f" near {structure_name}"
            summaries.append(
                {
                    "text": text,
                    "outcome": {
                        "attackers_casualties": attackers,
                        "defenders_casualties": defenders,
                        "structure_damage": int(outcome.get("structure_damage") or 0),
                    },
                }
            )
        return summaries

    def _count_active_fires(self, world_state: Dict[str, Any]) -> int:
        structures = world_state.get("structures")
        iterable: Iterable[Any]
        if isinstance(structures, dict):
            iterable = structures.values()
        elif isinstance(structures, list):
            iterable = structures
        else:
            iterable = []
        count = 0
        for entry in iterable:
            if isinstance(entry, dict) and entry.get("on_fire"):
                count += 1
        return count

    @staticmethod
    def _metric_value(value: Any) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0
