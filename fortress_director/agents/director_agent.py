"""Director agent that delegates intent generation to an LLM."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from fortress_director.core.threat_model import ThreatSnapshot
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

if TYPE_CHECKING:  # pragma: no cover - type hints only
    from fortress_director.narrative.event_graph import EventNode

LOGGER = logging.getLogger(__name__)
PROMPT_FILENAME = "director_prompt.txt"

DIRECTOR_FEW_SHOTS: List[Dict[str, Any]] = [
    {
        "scene_intent": {
            "focus": "stabilize",
            "summary": "Reinforce the north wall before the storm hits.",
            "turn": 5,
            "risk_budget": 1,
            "player_choice": "option_2",
            "notes": "Breach alarms keep morale shaky.",
        },
        "player_options": [
            {
                "id": "option_1",
                "label": "Dispatch masons",
                "text": "Rhea leads engineers to shore up the battered rampart.",
                "type": "defense",
            },
            {
                "id": "option_2",
                "label": "Scout raider tents",
                "text": "Send Ila to shadow raider reinforcements arriving at dusk.",
                "type": "recon",
            },
            {
                "id": "option_3",
                "label": "Quiet the courtyards",
                "text": "Hold a calm assembly to rebuild trust among civilians.",
                "type": "diplomacy",
            },
        ],
    },
    {
        "scene_intent": {
            "focus": "explore",
            "summary": "Probe the collapsed tunnels for smugglers.",
            "turn": 9,
            "risk_budget": 2,
            "player_choice": "option_3",
            "notes": "Resources healthy; leverage surprise.",
        },
        "player_options": [
            {
                "id": "option_1",
                "label": "Lead a lantern team",
                "text": "Personally escort scouts through the waterlogged passages.",
                "type": "recon",
            },
            {
                "id": "option_2",
                "label": "Bribe the tinkers",
                "text": "Trade spare crystals to recruit tunnel maps.",
                "type": "logistics",
            },
            {
                "id": "option_3",
                "label": "Stage a diversion",
                "text": "Trigger a bonfire at the east gate to pull raiders away.",
                "type": "wildcard",
            },
        ],
    },
    {
        "scene_intent": {
            "focus": "escalate",
            "summary": "Use the roaring winds to hide a counterstrike.",
            "turn": 12,
            "risk_budget": 3,
            "player_choice": None,
            "notes": "Morale is steady enough for a bold move.",
        },
        "player_options": [
            {
                "id": "option_1",
                "label": "Ride with Bren's outriders",
                "text": "Rush the enemy siege engines while the lightning storm masks you.",
                "type": "offense",
            },
            {
                "id": "option_2",
                "label": "Sabotage supply winches",
                "text": "Send infiltrators beneath the docks to burn their lifts.",
                "type": "stealth",
            },
            {
                "id": "option_3",
                "label": "Signal allied magi",
                "text": "Request a one-turn protective veil in exchange for relic shards.",
                "type": "diplomacy",
            },
        ],
    },
]

PHASE_FOCUS_MAP = {
    "calm": "explore",
    "rising": "investigate",
    "peak": "escalate",
    "collapse": "stabilize",
}

PHASE_OPTION_PRESETS: Dict[str, List[Dict[str, str]]] = {
    "calm": [
        {
            "label": "Scout hidden paths",
            "text": "Send rangers to quietly map neglected sally routes beyond the walls.",
            "type": "recon",
        },
        {
            "label": "Resequence supply ledgers",
            "text": "Audit granaries and redirect crates before complacency sets in.",
            "type": "logistics",
        },
        {
            "label": "Soothe courtyard unrest",
            "text": "Host a lantern-lit briefing to keep civilians steady.",
            "type": "diplomacy",
        },
    ],
    "rising": [
        {
            "label": "Stage counter-scouts",
            "text": "Shadow hostile patrols and capture intel before it spreads.",
            "type": "recon",
        },
        {
            "label": "Fortify chokepoints",
            "text": "Stack barricades and spare shields at the inner corridors.",
            "type": "defense",
        },
        {
            "label": "Seed diversion teams",
            "text": "Dispatch saboteurs to tamper with siege ladders overnight.",
            "type": "stealth",
        },
    ],
    "peak": [
        {
            "label": "Lead a shock sortie",
            "text": "Ride with outriders to punch a hole in the enemy lines.",
            "type": "offense",
        },
        {
            "label": "Emergency breach repairs",
            "text": "Drag carpenters and spellbinders to seal collapsing timber.",
            "type": "defense",
        },
        {
            "label": "Ignite artillery volleys",
            "text": "Unleash every remaining bolt thrower to keep pressure high.",
            "type": "artillery",
        },
    ],
    "collapse": [
        {
            "label": "Evacuate civilians inward",
            "text": "Pull families into the keep tunnels before the gates fall.",
            "type": "logistics",
        },
        {
            "label": "Hold the last ring",
            "text": "Post veterans on the inner steps and dig in for attrition.",
            "type": "defense",
        },
        {
            "label": "Signal final allies",
            "text": "Light the final flare to beg distant allies for aid.",
            "type": "diplomacy",
        },
    ],
}

EVENT_TAG_OPTION_PRESETS: Dict[str, List[Dict[str, str]]] = {
    "battle": [
        {
            "label": "Lead the counter charge",
            "text": "Rally outriders for a hammer blow into the breach.",
            "type": "offense",
        },
        {
            "label": "Anchor the shield wall",
            "text": "Fortify the chokepoint with heavy shields and bracing spears.",
            "type": "defense",
        },
        {
            "label": "Volley the siege lines",
            "text": "Order archers to rain fire on siege crews preparing for the rush.",
            "type": "ranged",
        },
    ],
    "sabotage": [
        {
            "label": "Disable lift gears",
            "text": "Insert saboteurs to jam the enemy hoist machinery.",
            "type": "stealth",
        },
        {
            "label": "Seed false orders",
            "text": "Leak forged courier messages to scramble raider coordination.",
            "type": "intrigue",
        },
        {
            "label": "Detonate tunnel charges",
            "text": "Prime the cistern tunnels to collapse under invading scouts.",
            "type": "demolition",
        },
    ],
    "hope": [
        {
            "label": "Stage a morale rally",
            "text": "Host a lantern assembly to remind civilians of the plan.",
            "type": "social",
        },
        {
            "label": "Escort reinforcements",
            "text": "Guide the arriving caravan safely through the ash storm.",
            "type": "logistics",
        },
        {
            "label": "Share victory rumors",
            "text": "Spread intel about allied victories to steady anxious squads.",
            "type": "diplomacy",
        },
    ],
    "collapse": [
        {
            "label": "Trigger the last stand",
            "text": "Call every veteran to the relic vault for a do-or-die defense.",
            "type": "offense",
        },
        {
            "label": "Evacuate vital archives",
            "text": "Shepherd knowledge keepers through the escape tunnels.",
            "type": "logistics",
        },
        {
            "label": "Barter surrender terms",
            "text": "Send envoys to stall for time while exits are secured.",
            "type": "diplomacy",
        },
    ],
}

ENDGAME_RECOMMENDATION_LABELS = {
    "heroic": "Lead the heroic stand",
    "strategic": "Attempt the strategic breakout",
    "desperate": "Fallback to the desperate lifeline",
}


class DirectorAgent:
    """Produces scene intent and player options by prompting an LLM."""

    def __init__(
        self,
        *,
        llm_client: OllamaClient | None = None,
        model_key: str = "director",
        prompt_path: Path | str | None = None,
        option_catalog: Optional[List[Dict[str, Any]]] = None,
        use_llm: bool = True,
    ) -> None:
        registry = get_registry()
        self._agent_key = model_key
        try:
            self._model_config = registry.get(model_key)
        except KeyError:
            LOGGER.warning(
                "Unknown model key %s; falling back to director defaults.", model_key
            )
            self._agent_key = "director"
            self._model_config = registry.get(self._agent_key)
        client = llm_client or (OllamaClient() if use_llm else None)
        self._llm_client: OllamaClient | None = client
        self._llm_enabled = use_llm and self._llm_client is not None
        self._registry = registry
        self.option_catalog = option_catalog
        template_override = prompt_path if prompt_path is None else Path(prompt_path)
        self._prompt_template = load_prompt_template(PROMPT_FILENAME, template_override)
        runtime_config = SETTINGS.llm_runtime
        self._cache_enabled = bool(runtime_config.enable_cache)
        self._metrics_enabled = bool(runtime_config.log_metrics)
        self._llm_timeout = float(runtime_config.timeout_seconds)
        self._llm_max_retries = int(runtime_config.max_retries)
        self._llm_cache: LLMCache = get_default_cache()

    def generate_intent(
        self,
        projected_state: Dict[str, Any],
        player_choice: Optional[str] = None,
        *,
        threat_snapshot: ThreatSnapshot | None = None,
        event_seed: str | None = None,
        endgame_directive: Dict[str, Any] | None = None,
        event_node: "EventNode" | None = None,
        archive: StateArchive | None = None,
        turn_number: int = 0,
    ) -> Dict[str, Any]:
        """Return a planning intent and UI options."""

        context = self._build_context(
            threat_snapshot, event_seed, endgame_directive, event_node
        )
        prompt = self._build_prompt(
            projected_state, player_choice, context, archive, turn_number
        )
        if self._llm_enabled and is_llm_enabled():
            try:
                raw = self._call_llm(prompt)
                return self._parse_output(raw, projected_state, player_choice, context)
            except (
                OllamaClientError,
                ValueError,
                json.JSONDecodeError,
                TimeoutError,
                RuntimeError,
            ) as exc:
                LOGGER.warning("Director LLM fallback triggered: %s", exc)
        return self._fallback_payload(projected_state, player_choice, context)

    def _build_context(
        self,
        threat_snapshot: ThreatSnapshot | None,
        event_seed: str | None,
        endgame_directive: Dict[str, Any] | None,
        event_node: "EventNode" | None,
    ) -> Dict[str, Any]:
        final_directive = dict(endgame_directive or {})
        snapshot_data = threat_snapshot
        node_payload = None
        if event_node is not None:
            node_payload = {
                "id": event_node.id,
                "description": event_node.description,
                "tags": list(event_node.tags),
                "is_final": bool(event_node.is_final),
            }
        return {
            "snapshot": snapshot_data,
            "phase": getattr(snapshot_data, "phase", None),
            "score": float(getattr(snapshot_data, "threat_score", 0.0) or 0.0),
            "event_seed": event_seed,
            "final_directive": final_directive,
            "final_trigger": bool(final_directive.get("final_trigger")),
            "event_node": node_payload,
        }

    def _build_prompt(
        self,
        projected_state: Dict[str, Any],
        player_choice: Optional[str],
        context: Dict[str, Any],
        archive: StateArchive | None = None,
        turn_number: int = 0,
    ) -> str:
        recent_events = projected_state.get("recent_events") or []
        metrics = projected_state.get("metrics") or {}
        threat_phase = context.get("phase") or "calm"
        threat_score = context.get("score") or 0.0
        final_directive = context.get("final_directive") or {"final_trigger": False}
        event_node = context.get("event_node") or {}
        replacements = {
            "PROJECTED_STATE": json.dumps(
                projected_state, ensure_ascii=False, indent=2
            ),
            "RECENT_EVENTS": json.dumps(recent_events, ensure_ascii=False, indent=2),
            "METRICS": json.dumps(metrics, ensure_ascii=False, indent=2),
            "PLAYER_CHOICE": json.dumps(player_choice),
            "FEW_SHOTS": json.dumps(DIRECTOR_FEW_SHOTS, ensure_ascii=False, indent=2),
            "CURRENT_THREAT_PHASE": str(threat_phase),
            "CURRENT_THREAT_SCORE": f"{threat_score:.2f}",
            "EVENT_SEED": json.dumps(context.get("event_seed") or "none"),
            "FINAL_DIRECTIVE": json.dumps(
                final_directive, ensure_ascii=False, indent=2
            ),
            "CURRENT_EVENT_NODE": event_node.get("id") or "unknown",
            "EVENT_NODE_DESCRIPTION": event_node.get("description")
            or "No active event node.",
            "EVENT_NODE_TAGS": json.dumps(
                event_node.get("tags") or [], ensure_ascii=False, indent=2
            ),
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
                raise TimeoutError("Director LLM call timed out.")
            raise RuntimeError(
                f"Director LLM call failed ({metrics.error_type or 'UnknownError'})"
            )
        raw = response.get("response") if isinstance(response, dict) else None
        if not raw and isinstance(response, dict):
            raw = response.get("message", {}).get("content")
        if not raw:
            raise ValueError("Director LLM returned an empty response.")
        raw_str = str(raw)
        if cache_key and self._cache_enabled:
            self._llm_cache.set(cache_key, raw_str)
        return raw_str

    def _parse_output(
        self,
        payload: str | Dict[str, Any],
        projected_state: Dict[str, Any],
        player_choice: Optional[str],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        # Be tolerant of several JSON shapes produced by LLMs or test mocks.
        if isinstance(payload, dict):
            candidate = dict(payload)
        else:
            cleaned = str(payload).strip()
            try:
                candidate = json.loads(cleaned)
            except json.JSONDecodeError:
                # Try to fix common issues: single quotes or double-encoded JSON.
                sanitized = cleaned.replace("'", '"')
                try:
                    candidate = json.loads(sanitized)
                except json.JSONDecodeError:
                    # Handle double-encoded JSON string like '"{...}"'
                    if sanitized.startswith('"') and sanitized.endswith('"'):
                        inner = sanitized[1:-1]
                        try:
                            candidate = json.loads(inner)
                        except json.JSONDecodeError:
                            raise
                    else:
                        raise
        scene_intent = candidate.get("scene_intent")
        options_payload = candidate.get("player_options")
        if not isinstance(scene_intent, dict):
            raise ValueError("scene_intent missing from Director response.")
        normalized_options = self._normalize_options(
            options_payload,
            projected_state,
            context,
        )
        threat_phase = context.get("phase")
        final_trigger = bool(context.get("final_trigger"))
        scene_intent.setdefault("turn", int(projected_state.get("turn", 0)))
        if player_choice is not None:
            scene_intent["player_choice"] = player_choice
        scene_intent.setdefault(
            "focus", self._infer_focus(projected_state, threat_phase)
        )
        scene_intent.setdefault("summary", f"Turn {scene_intent['turn']} directive.")
        scene_intent.setdefault(
            "risk_budget",
            self._risk_budget_for_phase(threat_phase, final_trigger),
        )
        scene_intent.setdefault("notes", self._compose_notes(context))
        if threat_phase:
            scene_intent.setdefault("threat_phase", threat_phase)
        event_seed = context.get("event_seed")
        if event_seed:
            scene_intent.setdefault("event_seed", event_seed)
        scene_intent.setdefault("threat_score", context.get("score"))
        if context.get("final_directive") is not None:
            scene_intent["final_directive"] = context.get("final_directive")
        return {
            "scene_intent": scene_intent,
            "player_options": normalized_options,
        }

    def _normalize_options(
        self,
        options_payload: Any,
        projected_state: Dict[str, Any],
        context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []
        if isinstance(options_payload, list):
            for idx, option in enumerate(options_payload):
                if not isinstance(option, dict):
                    continue
                label = option.get("label") or option.get("text")
                if not label:
                    continue
                identifier = (
                    option.get("id") or option.get("choice_id") or f"option_{idx + 1}"
                )
                normalized.append(
                    {
                        "id": str(identifier),
                        "label": str(label),
                        "text": option.get("text"),
                        "type": option.get("type") or option.get("category"),
                    },
                )
        if not normalized:
            normalized = self._build_options(projected_state, context)
        return normalized

    def _fallback_payload(
        self,
        projected_state: Dict[str, Any],
        player_choice: Optional[str],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        threat_phase = context.get("phase")
        final_trigger = bool(context.get("final_trigger"))
        focus = self._infer_focus(projected_state, threat_phase)
        turn_index = int(projected_state.get("turn", 0))
        scene_intent = {
            "focus": focus,
            "turn": turn_index,
            "player_choice": player_choice,
            "risk_budget": self._risk_budget_for_phase(threat_phase, final_trigger),
            "summary": f"Turn {turn_index} directive: {focus}.",
            "notes": self._compose_notes(context),
        }
        if threat_phase:
            scene_intent["threat_phase"] = threat_phase
        if context.get("event_seed"):
            scene_intent["event_seed"] = context.get("event_seed")
        scene_intent.setdefault("threat_score", context.get("score"))
        if context.get("final_directive") is not None:
            scene_intent["final_directive"] = context.get("final_directive")
        return {
            "scene_intent": scene_intent,
            "player_options": self._build_options(projected_state, context),
        }

    def _build_options(
        self,
        projected_state: Dict[str, Any],
        context: Dict[str, Any] | None = None,
    ) -> List[Dict[str, Any]]:
        context = context or {}
        if self.option_catalog:
            return list(self.option_catalog)
        if context.get("final_trigger"):
            return self._build_endgame_options(context)
        tag_templates = self._templates_for_event_tags(context.get("event_node"))
        threat_phase = context.get("phase") or self._phase_from_state(projected_state)
        templates = tag_templates or PHASE_OPTION_PRESETS.get(
            threat_phase, PHASE_OPTION_PRESETS["calm"]
        )
        options: List[Dict[str, Any]] = []
        for idx, template in enumerate(templates, start=1):
            options.append(
                {
                    "id": template.get("id") or f"option_{idx}",
                    "label": template.get("label"),
                    "text": template.get("text"),
                    "type": template.get("type"),
                }
            )
        return options

    def _templates_for_event_tags(
        self, event_node: Dict[str, Any] | None
    ) -> List[Dict[str, str]] | None:
        if not event_node:
            return None
        tags = event_node.get("tags") or []
        lowered = [str(tag).lower() for tag in tags]
        for tag in ("battle", "sabotage", "hope", "collapse"):
            if tag in lowered:
                return EVENT_TAG_OPTION_PRESETS[tag]
        return None

    def _build_endgame_options(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        directive = context.get("final_directive") or {}
        recommended = directive.get("recommended_path") or "heroic"
        heroic_label = ENDGAME_RECOMMENDATION_LABELS.get(
            recommended, ENDGAME_RECOMMENDATION_LABELS["heroic"]
        )
        return [
            {
                "id": "heroic_choice",
                "label": heroic_label,
                "text": "Rally the last vanguard for a heroic stand even if the odds are fatal.",
                "type": "offense",
            },
            {
                "id": "desperate_fallback",
                "label": "Desperate fallback corridor",
                "text": "Shepherd civilians and healers through the final escape tunnels.",
                "type": "logistics",
            },
        ]

    def _infer_focus(
        self,
        projected_state: Dict[str, Any],
        threat_phase: Optional[str] = None,
    ) -> str:
        if threat_phase:
            return PHASE_FOCUS_MAP.get(threat_phase, "stabilize")
        return self._phase_from_state(projected_state)

    def _phase_from_state(self, projected_state: Dict[str, Any]) -> str:
        world_state = projected_state.get("world", {})
        threat = str(world_state.get("threat_level", "stable")).lower()
        stability = int(world_state.get("stability", 50))
        if threat not in {"calm", "stable"} or stability < 50:
            return "stabilize"
        if stability > 70:
            return "explore"
        return "investigate"

    def _risk_budget_for_phase(
        self,
        threat_phase: Optional[str],
        final_trigger: bool,
    ) -> int:
        if final_trigger:
            return 3
        mapping = {"calm": 1, "rising": 2, "peak": 3, "collapse": 2}
        return mapping.get(threat_phase or "", 2)

    def _compose_notes(self, context: Dict[str, Any]) -> str:
        pieces: List[str] = []
        phase = context.get("phase")
        score = context.get("score")
        if phase is not None:
            pieces.append(f"Threat {phase} ({float(score or 0):.1f}).")
        event_seed = context.get("event_seed")
        if event_seed:
            pieces.append(f"Event cue: {event_seed}.")
        if context.get("final_trigger"):
            pieces.append("Endgame directive active.")
        if not pieces:
            return "LLM generated intent."
        return " ".join(pieces)
