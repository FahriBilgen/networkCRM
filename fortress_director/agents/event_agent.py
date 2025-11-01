from __future__ import annotations

import json
import logging
import random

"""Implementation of the Event Agent that talks to a local Ollama model."""
from typing import Any, Dict, Optional

from fortress_director.agents.base_agent import (
    BaseAgent,
    PromptTemplate,
    build_prompt_path,
    default_ollama_client,
    get_model_config,
)
from fortress_director.llm.ollama_client import OllamaClient
from fortress_director.settings import MAJOR_EVENT_MIN_INTERVAL, EVENT_DIVERSITY_POOL


class EventAgent(BaseAgent):
    LOGGER = logging.getLogger(__name__)
    """Creates short narrative scenes and diegetic player options."""

    def __init__(self, *, client: Optional[OllamaClient] = None) -> None:
        template = PromptTemplate(build_prompt_path("event_prompt.txt"))
        super().__init__(
            name="Event",
            prompt_template=template,
            model_config=get_model_config("event"),
            client=client or default_ollama_client("event"),
        )

    def generate(self, variables: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a turn event using the provided template variables. Injects forced
        novelty and rare incidents to break monotony. Logs every step.
        """
        self.LOGGER.info("EventAgent.generate called with variables: %s", variables)
        try:
            # Apply Judge feedback corrections if available
            judge_feedback = variables.get("judge_feedback", {})
            if judge_feedback and isinstance(judge_feedback, dict):
                variables = self._apply_judge_feedback(variables, judge_feedback)

            # --- Event diversity: select from pool to ensure variety ---
            # Prefer a numeric turn index if provided; fall back to 'day'.
            try:
                turn_idx = int(variables.get("turn_index", variables.get("day", 1)) or 1)
            except Exception:
                turn_idx = int(variables.get("day", 1) or 1)
            # Diversity selection: hash-based index to avoid simple cycles
            try:
                import hashlib

                h = hashlib.sha256(str(turn_idx).encode("utf-8")).digest()
                idx = h[0] % len(EVENT_DIVERSITY_POOL)
            except Exception:
                idx = turn_idx % len(EVENT_DIVERSITY_POOL)
            event_type = EVENT_DIVERSITY_POOL[idx]
            variables = dict(variables)
            variables["event_type"] = event_type
            variables["diversity_hint"] = (
                f"This event should be of type '{event_type}'. "
                "Focus on this theme while maintaining narrative coherence."
            )

            # --- Forced novelty and rare incident logic ---
            turn = turn_idx
            novelty_flag = variables.get("novelty_flag", False)
            # Force novelty on even turns OR occasionally via small probability
            # Increased small-probability to 20% to inject more rare incidents.
            force_novelty = novelty_flag or (turn % 2 == 0) or (random.random() < 0.2)
            if force_novelty:
                self.LOGGER.info(
                    "Injecting forced novelty/rare incident for turn %d", turn
                )
                variables = dict(variables)
                variables["novelty_directive"] = (
                    "IMPORTANT: This turn must introduce a new scene type, "
                    "break narrative repetition, and add a rare or unexpected "
                    "incident. Avoid repeating previous event structures."
                )
                # Add a rare incident to the pool
                rare_incidents = [
                    "a mysterious signal is received from the mountains",
                    "a long-lost villager returns with urgent news",
                    "a strange artifact is discovered near the wall",
                    "a sudden snowstorm engulfs the village",
                    "a secret tunnel is found beneath the keep",
                    "a wild animal stampede threatens the food stores",
                ]
                try:
                    h2 = hashlib.sha1(f"{turn}-rare".encode("utf-8")).digest()
                    ridx = h2[0] % len(rare_incidents)
                except Exception:
                    ridx = turn % len(rare_incidents)
                rare_incident = rare_incidents[ridx]
                variables["rare_incident"] = rare_incident

            # Reduce memory weighting but keep wider window to avoid repetition loops
            if "memory_layers" in variables and isinstance(
                variables["memory_layers"], list
            ):
                variables["memory_layers"] = variables["memory_layers"][-8:]
                # Provide explicit anti-repetition guidance to the model
                variables["avoid_repetition_hint"] = (
                    "Avoid reusing the same scene/motif unless a resolution meaningfully changes the outcome."
                )

            output = self.run(variables=variables)
            self.LOGGER.debug("Model returned: %s", output)

            # Enforce option diversity softly if the model repeats types
            try:
                opts = output.get("options") or []
                if isinstance(opts, list) and len(opts) >= 2:
                    seen = set()
                    target_cycle = [
                        "exploration",
                        "defense",
                        "trade",
                        "interaction",
                        "dialogue",
                    ]
                    ci = 0
                    for o in opts:
                        at = str(o.get("action_type", "")).strip().lower()
                        if at in seen or at not in target_cycle:
                            # assign next distinct type
                            while ci < len(target_cycle) and target_cycle[ci] in seen:
                                ci += 1
                            if ci < len(target_cycle):
                                o["action_type"] = target_cycle[ci]
                                # nudge text for clarity
                                txt = str(o.get("text", "")).strip()
                                if txt:
                                    o["text"] = f"{txt} (focus: {target_cycle[ci]})"
                                seen.add(target_cycle[ci])
                        else:
                            seen.add(at)
                    output["options"] = opts[:3]
            except Exception:
                pass

            # Light text variety: avoid repeating the same leading verb across options
            try:
                opts = output.get("options") or []
                if isinstance(opts, list) and len(opts) >= 2:
                    seen_verbs = set()
                    verb_map = {
                        "ask": "consult",
                        "search": "scan",
                        "offer": "assist",
                        "investigate": "probe",
                        "check": "inspect",
                        "talk": "speak",
                        "use": "deploy",
                    }
                    def _replace_leading_verb(text: str, alt: str) -> str:
                        parts = text.strip().split(maxsplit=1)
                        if not parts:
                            return text
                        if len(parts) == 1:
                            return alt.capitalize()
                        return f"{alt.capitalize()} {parts[1]}"
                    for i, o in enumerate(opts):
                        t = str(o.get("text", "")).strip()
                        if not t:
                            continue
                        first = t.split(maxsplit=1)[0].strip("\"' .,;:").lower()
                        if not first:
                            continue
                        if first in seen_verbs:
                            alt = verb_map.get(first, None)
                            if alt:
                                o["text"] = _replace_leading_verb(t, alt)
                        else:
                            seen_verbs.add(first)
                    output["options"] = opts
            except Exception:
                pass

            # Slightly increase major_event probability when continuity_weight is higher
            flags = variables.get("flags", []) or []
            continuity_weight = float(variables.get("continuity_weight", 0.0) or 0.0)
            raise_major = continuity_weight >= 0.6
            allow_major = variables.get(
                "allow_major", True
            )  # Throttle from orchestrator
            if (
                allow_major
                and ((turn % 3 == 0) or ("force_major_event" in flags) or raise_major)
                and not output.get("major_event", False)
            ):
                self.LOGGER.info("Forcing incident flag for turn %d", turn)
                output["major_event"] = True
                scene = output.get("scene", "")
                incidents = [
                    "a sudden fire breaks out",
                    "intruders are spotted",
                    "a betrayal unfolds",
                    "a discovery is made",
                ]
                incident = incidents[turn % len(incidents)]
                output["scene"] = f"{scene} Suddenly, {incident}!"

            # If model returns string, try to parse as JSON or create fallback
            if isinstance(output, str):
                try:
                    output = json.loads(output)
                except json.JSONDecodeError:
                    self.LOGGER.warning(
                        "Model returned invalid JSON, creating fallback: %s", output
                    )
                    output = self._create_fallback_event(output)

            if not isinstance(output, dict):
                self.LOGGER.error(
                    "Event agent must return a JSON object, got: %s", output
                )
                raise ValueError("Event agent must return a JSON object")
            norm = self._normalise_event(output)
            self.LOGGER.info("Normalized event output: %s", norm)
            # Safe function ekleme (örnek pattern) + düşük olasılıkta atmosfer düzenleme
            scene = norm.get("scene", "")
            safe_functions = norm.get("safe_functions", [])
            # Only append safe function calls as dicts, never as strings
            if "rain" in scene.lower():
                safe_functions.append(
                    {
                        "name": "change_weather",
                        "args": [],
                        "kwargs": {
                            "atmosphere": "rainy skies",
                            "sensory_details": "steady rainfall, damp air",
                        },
                        "metadata": {"source": "event_autoinject"},
                    }
                )
            if "fire" in scene.lower():
                safe_functions.append(
                    {
                        "name": "spawn_item",
                        "args": [],
                        "kwargs": {"item_id": "fire_extinguisher", "target": "nearby"},
                        "metadata": {"source": "event_autoinject"},
                    }
                )
            # Deterministic ~10% chance to inject change_weather as a dict
            try:
                basis = (scene or "").encode("utf-8")
                import hashlib

                bucket = int.from_bytes(
                    hashlib.sha256(basis).digest()[:1],
                    "big",
                )
                if bucket < 26:
                    # Avoid redundant weather changes if previous atmosphere already
                    # matches the deterministic suggestion. EventAgent receives
                    # previous world constraint as a JSON string from orchestrator.
                    prev_atmo = None
                    try:
                        import json as _json
                        prev_raw = variables.get("world_constraint_from_prev_turn")
                        if isinstance(prev_raw, str) and prev_raw.strip():
                            prev_parsed = _json.loads(prev_raw)
                            if isinstance(prev_parsed, dict):
                                prev_atmo = (prev_parsed.get("atmosphere") or "").strip()
                    except Exception:
                        prev_atmo = None
                    planned_atmo = "shifting winds"
                    if prev_atmo and prev_atmo.lower() == planned_atmo.lower():
                        # Skip injecting if it wouldn't visibly change anything
                        pass
                    else:
                        # Also ensure we don't duplicate an existing change_weather call
                        already_has_weather = any(
                            isinstance(sf, dict) and sf.get("name") == "change_weather"
                            for sf in safe_functions
                        )
                        if not already_has_weather:
                            safe_functions.append(
                                {
                                    "name": "change_weather",
                                    "args": [],
                                    "kwargs": {
                                        "atmosphere": planned_atmo,
                                        "sensory_details": "fleeting chills",
                                    },
                                    "metadata": {"source": "event_autoinject"},
                                }
                            )
            except Exception:
                pass
            norm["safe_functions"] = safe_functions
            return norm
        except Exception as exc:
            self.LOGGER.error(
                "Exception in EventAgent.generate: %s", exc, exc_info=True
            )
            raise

    def _normalise_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        scene = payload.get("scene")
        if not isinstance(scene, str):
            payload["scene"] = str(scene) if scene is not None else ""

        options = payload.get("options")
        if not isinstance(options, list):
            options = [] if options is None else [options]
        normalised_options = []
        for raw in options:
            if not isinstance(raw, dict):
                continue
            option = dict(raw)
            option_id = option.get("id")
            option_text = option.get("text")
            action_type = option.get("action_type")
            if not isinstance(option_id, str) or not option_id.strip():
                option_id = f"opt_{len(normalised_options) + 1}"
            if not isinstance(option_text, str) or not option_text.strip():
                option_text = "Unclear option"
            if not isinstance(action_type, str) or not action_type.strip():
                action_type = "talk"
            option["id"] = option_id.strip()
            option["text"] = option_text.strip()
            option["action_type"] = action_type.strip()
            normalised_options.append(option)

        # Ensure at least 4 unique action_types in options
        required_types = [
            ("exploration", "Explore the area for clues or resources."),
            ("item_use", "Use an item from your inventory."),
            ("diplomacy", "Attempt to negotiate or communicate diplomatically."),
            ("stealth", "Try to move unseen or eavesdrop."),
            ("observation", "Observe the environment for hidden details."),
            ("planning", "Formulate a plan for the next steps."),
            ("trade", "Trade supplies with a villager."),
            ("assistance", "Offer help to someone nearby."),
        ]
        existing_types = set(opt.get("action_type") for opt in normalised_options)
        idx = 1
        for action_type, text in required_types:
            if len(set(opt.get("action_type") for opt in normalised_options)) >= 4:
                break
            if action_type not in existing_types:
                normalised_options.append(
                    {
                        "id": f"auto_{action_type}_{idx}",
                        "text": text,
                        "action_type": action_type,
                    }
                )
                existing_types.add(action_type)
                idx += 1

        if not normalised_options:
            normalised_options.append(
                {
                    "id": "opt_1",
                    "text": "Observe the situation from the wall.",
                    "action_type": "explore",
                }
            )
        payload["options"] = normalised_options

        # Normalize major_event to a strict boolean
        major = payload.get("major_event", False)
        if isinstance(major, str):
            m = major.strip().lower()
            payload["major_event"] = m in ("true", "yes", "1")
        else:
            payload["major_event"] = bool(major)

        return payload

    def _create_fallback_event(self, text_output: str) -> Dict[str, Any]:
        """Create a fallback event when model doesn't return valid JSON."""
        return {
            "scene": f"At dawn, you stand at the entrance of Lornhaven. {text_output[:100]}...",
            "options": [
                {
                    "id": "observe",
                    "text": "Observe the surroundings carefully.",
                    "action_type": "observation",
                },
                {
                    "id": "approach_rhea",
                    "text": "Approach Rhea and ask about the situation.",
                    "action_type": "dialogue",
                },
                {
                    "id": "check_inventory",
                    "text": "Check your equipment and prepare.",
                    "action_type": "preparation",
                },
            ],
            "major_event": False,
            "safe_functions": [],
        }

    def _apply_judge_feedback(
        self, variables: Dict[str, Any], judge_feedback: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply Judge feedback corrections to prevent penalty/reward inconsistency."""
        corrected_vars = dict(variables)

        # If Judge applied penalty, ensure next event doesn't give automatic rewards
        penalty_type = judge_feedback.get("penalty_applied")
        if penalty_type:
            # Add constraint to prevent reward after penalty
            constraint = (
                f"IMPORTANT: Previous Judge penalty ({penalty_type}) applied. "
                "Do not provide automatic trust_delta or morale boosts in this event. "
                "Focus on neutral or challenging options only."
            )
            existing_context = corrected_vars.get("WORLD_CONTEXT", "")
            corrected_vars["WORLD_CONTEXT"] = f"{constraint}\n\n{existing_context}"

        # If tone_alignment was low, reinforce tone correction
        tone_alignment = judge_feedback.get("tone_alignment", 100)
        if tone_alignment < 70:
            tone_constraint = (
                "CRITICAL: Maintain consistent emotional tone. "
                "Do not shift from established atmosphere or character moods."
            )
            existing_context = corrected_vars.get("WORLD_CONTEXT", "")
            corrected_vars["WORLD_CONTEXT"] = f"{tone_constraint}\n\n{existing_context}"

        return corrected_vars
