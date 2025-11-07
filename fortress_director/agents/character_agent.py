from __future__ import annotations
from __future__ import annotations

import logging
from pathlib import Path

"""Implementation of the Character Agent for NPC reactions."""
from typing import Any, Dict, List, Optional

from fortress_director.agents.base_agent import (
    AgentOutputError,
    BaseAgent,
    PromptTemplate,
    build_prompt_path,
    default_ollama_client,
    get_model_config,
)
from fortress_director.llm.ollama_client import OllamaClient


MAX_SPEECH_LENGTH = 200


class CharacterAgent(BaseAgent):
    LOGGER = logging.getLogger(__name__)
    """Produces NPC intents, actions, dialogue, and mechanical effects."""
    ALLOWED_INTENTS = [
        "observe",
        "assist",
        "command",
        "plan",
        "inquire",
        "defend",
        "comfort",
        "warn",
        "recall",
        "improvise",
        "trade",
        "stealth",
        "inspire",
        "sabotage",
        "motivate",
        "protect",
        "explore",
    ]

    def __init__(
        self,
        *,
        client: Optional[OllamaClient] = None,
        prompt_path: Optional[Path] = None,
    ) -> None:
        template_path = prompt_path or build_prompt_path("character_prompt.txt")
        template = PromptTemplate(template_path)
        super().__init__(
            name="Character",
            prompt_template=template,
            model_config=get_model_config("character"),
            client=client or default_ollama_client("character"),
        )
        # Trust-based persona mapping for character development
        self.persona_map = {
            "Rhea": {
                "high_trust": {
                    "mood": "confident",
                    "communication": "direct",
                    "cooperation": "proactive",
                },
                "low_trust": {
                    "mood": "wary",
                    "communication": "guarded",
                    "cooperation": "cautious",
                },
                "neutral": {
                    "mood": "focused",
                    "communication": "practical",
                    "cooperation": "dutiful",
                },
            },
            "Boris": {
                "high_trust": {
                    "mood": "optimistic",
                    "communication": "encouraging",
                    "cooperation": "generous",
                },
                "low_trust": {
                    "mood": "suspicious",
                    "communication": "evasive",
                    "cooperation": "minimal",
                },
                "neutral": {
                    "mood": "calculating",
                    "communication": "pragmatic",
                    "cooperation": "fair",
                },
            },
        }
        # Track last intent for each NPC
        self.npc_last_intent = {}

    def react(self, variables: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate structured NPC reactions for the current turn. Injects forced Boris
        actions, emotional/intent variety, and occasional challenge/assist. Logs every step.
        """
        self.LOGGER.info("CharacterAgent.react called with variables: %s", variables)

        # --- Memory injection: recent events and last major event ---
        recent_events = variables.get("recent_events", [])
        last_major_event = variables.get("last_major_event", None)
        memory_injection = ""
        if recent_events:
            memory_injection += (
                "RECENT EVENTS: " + "; ".join(str(e) for e in recent_events) + "\n"
            )
        if last_major_event:
            memory_injection += f"LAST MAJOR EVENT: {last_major_event}\n"
        if memory_injection:
            variables["WORLD_CONTEXT"] = memory_injection + variables.get(
                "WORLD_CONTEXT", ""
            )

        # Emotional bellek: son birkaç diyalogu bağlamın başına ekle
        try:
            emotional_memory = variables.get("emotional_memory", []) or []
            if emotional_memory:
                recent_echoes = emotional_memory[-4:]
                echoes_text = "; ".join(
                    f"{item.get('name', 'Unknown')}: {str(item.get('speech', '')).strip()}"
                    for item in recent_echoes
                    if isinstance(item, dict)
                )
                if echoes_text:
                    variables["WORLD_CONTEXT"] = (
                        f"EMOTIONAL ECHOES: {echoes_text}\n\n"
                        + variables.get("WORLD_CONTEXT", "")
                    )
        except Exception:
            pass

        # Add trust-based persona guidance for character development
        variables = self._add_persona_guidance(variables)
        # Enforce variation if the same NPC intent repeats in recent memory
        variables = self._enforce_behavior_variation(variables)

        # Enforce intent variety: do not repeat previous intent for same NPC
        memory_layers = variables.get("memory_layers", []) or []
        npc_last_intent = {}
        for m in reversed(memory_layers):
            if isinstance(m, dict) and "name" in m and "intent" in m:
                npc_last_intent[m["name"]] = m["intent"]
            elif isinstance(m, str):
                # Try to parse simple string logs if present
                for npc in ("Rhea", "Boris"):
                    if npc in m:
                        for intent in self.ALLOWED_INTENTS:
                            if intent in m.lower():
                                npc_last_intent[npc] = intent
        # For each NPC, inject allowed_intents into WORLD_CONTEXT
        allowed_intents_note = "ALLOWED_INTENTS for this turn: " + ", ".join(
            self.ALLOWED_INTENTS
        )
        variables["WORLD_CONTEXT"] = (
            allowed_intents_note + "\n" + variables.get("WORLD_CONTEXT", "")
        )

        # --- Forced Boris and intent variety logic ---
        turn = variables.get("turn") or variables.get("day") or 1
        novelty_flag = variables.get("novelty_flag", False)
        force_boris = novelty_flag or (turn % 3 == 0)
        force_intent_variety = novelty_flag or (turn % 2 == 1)
        if force_boris or force_intent_variety:
            existing = variables.get("WORLD_CONTEXT", "")
            directives = []
            if force_boris:
                directives.append(
                    "NOTE: Boris must take a visible, active role this turn. "
                    "He should interact, trade, or challenge, not remain passive."
                )
            if force_intent_variety:
                directives.append(
                    "NOTE: All NPCs must show emotional or intent variety. "
                    "At least one should choose 'challenge' or 'assist' as intent."
                )
            variables["WORLD_CONTEXT"] = "\n\n".join(directives) + "\n\n" + existing

        try:
            result = self.run(variables=variables)
            self.LOGGER.debug("Model returned: %s", result)
            # Always wrap result as a list of entries
            if isinstance(result, list):
                entries = result
            elif isinstance(result, dict):
                # Single character object or dict with candidates
                if {"name", "intent", "action"}.issubset(result.keys()):
                    entries = [result]
                else:
                    # Try to extract from keys like 'characters', 'npcs', 'responses'
                    for key in ("characters", "npcs", "responses"):
                        candidates = result.get(key)
                        if isinstance(candidates, list):
                            entries = candidates
                            break
                    else:
                        snippet = str(result)[:200]
                        self.LOGGER.error("Agent output error: %s", snippet)
                        raise AgentOutputError(
                            "Character agent must return a JSON list; received: "
                            + snippet
                        )
            else:
                snippet = str(result)[:200]
                self.LOGGER.error("Agent output error: %s", snippet)
                raise AgentOutputError(
                    "Character agent must return a JSON list; received: " + snippet
                )

            out = self._normalise_entries(entries)
            # Value-driven autonomous behaviors: allow Rhea/Boris to break pattern
            # when conditions call for it (increases dramatic agency).
            try:
                metrics = variables.get("metrics") or {}
                morale = int(metrics.get("morale", 50))
                glitch = int(metrics.get("glitch", 0))
                order = int(metrics.get("order", 50))
                # If morale is low and glitch high, let Rhea propose a risky move
                if morale <= 30 and glitch >= 60:
                    out.append(
                        {
                            "name": "Rhea",
                            "intent": "improvise",
                            "action": "Defies protocol to scout the breach alone.",
                            "speech": "If hope is thin, I will cut a path for it.",
                            "effects": {"metric_changes": {"knowledge": 2, "order": -2}},
                            "safe_functions": [],
                        }
                    )
                # If order is low and morale decent, Boris forces structure
                if order <= 30 and morale >= 40:
                    out.append(
                        {
                            "name": "Boris",
                            "intent": "command",
                            "action": "Imposes ration rotations and guard schedules.",
                            "speech": "We bend now or break later—choose.",
                            "effects": {"metric_changes": {"order": 3, "morale": -1}},
                            "safe_functions": [],
                        }
                    )
            except Exception:
                pass
            # Enforce intent variety in output: do not allow same intent as previous turn for each NPC
            for entry in out:
                npc = entry.get("name")
                intent = entry.get("intent")
                if (
                    npc
                    and intent
                    and npc in npc_last_intent
                    and intent == npc_last_intent[npc]
                ):
                    # Pick a different allowed intent if repeated
                    for alt_intent in self.ALLOWED_INTENTS:
                        if alt_intent != intent:
                            entry["intent"] = alt_intent
                            break
                action = entry.get("action", "")
                safe_functions = entry.get("safe_functions", [])
                if "heal" in action.lower():
                    safe_functions.append("adjust_metric")
                if "build" in action.lower():
                    safe_functions.append("move_npc")
                entry["safe_functions"] = safe_functions

            # Ensure at least 5 unique intent/action types for agency diversity
            unique_intents = set(entry.get("intent") for entry in out)
            idx = 1
            for intent in self.ALLOWED_INTENTS:
                if len(unique_intents) >= 5:
                    break
                if intent not in unique_intents:
                    # Add a synthetic autonomous action for Rhea or Boris
                    npc_name = "Rhea" if idx % 2 == 1 else "Boris"
                    speech_text = (
                        f"{npc_name} shifts tactics with a {intent} maneuver."
                    )
                    out.append(
                        {
                            "name": npc_name,
                            "intent": intent,
                            "action": f"Autonomously performs {intent} action.",
                            "speech": speech_text,
                            "effects": {},
                            "safe_functions": [],
                        }
                    )
                    unique_intents.add(intent)
                    idx += 1
            self.LOGGER.info("Normalized output (list): %s", out)
            return out
        except Exception as exc:
            self.LOGGER.error(
                "Exception in CharacterAgent.react: %s", exc, exc_info=True
            )
            raise

    def _normalise_entries(
        self,
        entries: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        normalised: List[Dict[str, Any]] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            clone: Dict[str, Any] = dict(entry)
            for field in ("name", "intent", "action", "speech"):
                value = clone.get(field)
                if not isinstance(value, str):
                    if value is None:
                        clone[field] = "" if field != "name" else "Unknown"
                    else:
                        clone[field] = str(value)
                if field == "speech":
                    speech_text = clone[field].strip()
                    if speech_text and speech_text[-1] not in ".!?":
                        speech_text = f"{speech_text}."
                    if len(speech_text) < 10:
                        npc_name = clone.get("name") or "The defender"
                        speech_text = f"{npc_name} steels their resolve."
                    if len(speech_text) > MAX_SPEECH_LENGTH:
                        speech_text = speech_text[:MAX_SPEECH_LENGTH]
                    clone[field] = speech_text
            effects_raw = clone.get("effects")
            effects: Dict[str, Any] = (
                dict(effects_raw) if isinstance(effects_raw, dict) else {}
            )

            trust_delta = effects.get("trust_delta")
            # Clamp trust_delta strictly to -1, 0 or 1 so the RulesEngine
            # deterministic trust update can apply the intended small step.
            if isinstance(trust_delta, (int, float)):
                try:
                    tval = int(trust_delta)
                except (TypeError, ValueError):
                    effects.pop("trust_delta", None)
                else:
                    if tval > 0:
                        effects["trust_delta"] = 1
                    elif tval < 0:
                        effects["trust_delta"] = -1
                    else:
                        effects["trust_delta"] = 0
            else:
                effects.pop("trust_delta", None)

            # Replace flag_set with direct metric changes
            flag_set = effects.get("flag_set")
            if isinstance(flag_set, list):
                # Convert flags to metric effects when possible, but preserve
                # cleaned flag list if no metric changes detected.
                metric_changes = {}
                cleaned_flags: List[str] = []
                for flag in flag_set:
                    if isinstance(flag, str) and flag.strip():
                        text = flag.strip()
                        cleaned_flags.append(text)
                        if "vigilant" in text.lower():
                            metric_changes["order"] = metric_changes.get("order", 0) + 1
                        elif "morale" in text.lower():
                            metric_changes["morale"] = (
                                metric_changes.get("morale", 0) + 1
                            )
                    elif isinstance(flag, (int, float)):
                        cleaned_flags.append(str(flag))

                if metric_changes:
                    effects["metric_changes"] = metric_changes

                if cleaned_flags:
                    effects["flag_set"] = cleaned_flags
                else:
                    effects.pop("flag_set", None)
            else:
                effects.pop("flag_set", None)

            item_change = effects.get("item_change")
            if isinstance(item_change, dict):
                item = item_change.get("item")
                delta = item_change.get("delta")
                target = item_change.get("target")
                if not item or delta not in (-1, 1) or not target:
                    effects.pop("item_change", None)
                else:
                    effects["item_change"] = {
                        "item": str(item),
                        "delta": int(delta),
                        "target": str(target),
                    }
            else:
                effects.pop("item_change", None)

            status_change = effects.get("status_change")
            if isinstance(status_change, dict):
                target = status_change.get("target")
                status = status_change.get("status")
                duration = status_change.get("duration")
                if not target or not status:
                    effects.pop("status_change", None)
                else:
                    safe_duration = 0
                    if isinstance(duration, (int, float)):
                        safe_duration = int(duration)
                    effects["status_change"] = {
                        "target": str(target),
                        "status": str(status),
                        "duration": max(0, safe_duration),
                    }
            else:
                effects.pop("status_change", None)

            clone["effects"] = effects

            # Safe functions: normalize if present and valid
            safe_functions = clone.get("safe_functions")
            if isinstance(safe_functions, list):
                cleaned = []
                for sf in safe_functions:
                    if not isinstance(sf, dict):
                        continue
                    name = sf.get("name")
                    args = sf.get("args", [])
                    kwargs = sf.get("kwargs", {})
                    metadata = sf.get("metadata", {})
                    if not isinstance(name, str) or not name.strip():
                        continue
                    if not isinstance(args, list):
                        args = []
                    if not isinstance(kwargs, dict):
                        kwargs = {}
                    if not isinstance(metadata, dict):
                        metadata = {}
                    cleaned.append(
                        {
                            "name": name.strip(),
                            "args": args,
                            "kwargs": kwargs,
                            "metadata": metadata,
                        }
                    )
                if cleaned:
                    clone["safe_functions"] = cleaned
                else:
                    clone.pop("safe_functions", None)
            else:
                clone.pop("safe_functions", None)

            # Deterministic low-probability injection of a minor safe function
            # to ensure occasional system-level interactions (10% approx)
            if "safe_functions" not in clone or not clone["safe_functions"]:
                try:
                    basis = (
                        clone.get("name", "") + "|" + clone.get("action", "")
                    ).encode("utf-8")
                    import hashlib

                    bucket = (
                        int.from_bytes(hashlib.sha1(basis).digest()[:1], "big") % 10
                    )
                    if bucket == 0:
                        # Prefer small, safe adjustments
                        clone["safe_functions"] = [
                            {
                                "name": "adjust_metric",
                                "args": [],
                                "kwargs": {"metric": "order", "delta": 1},
                                "metadata": {"source": "character_autoinject"},
                            }
                        ]
                except Exception:
                    pass

            normalised.append(clone)
        return normalised

    def autonomous_action(
        self, npc_name: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate autonomous NPC actions when not reacting to player input.

        Args:
            npc_name: Name of the NPC taking autonomous action
            context: Game context including world state, relationships, etc.

        Returns:
            Dict with autonomous action details
        """
        self.LOGGER.info("Autonomous action for %s", npc_name)

        # Build context for autonomous decision
        variables = {
            "WORLD_CONTEXT": context.get("world_context", ""),
            "scene_short": f"Autonomous behavior for {npc_name} during {context.get('current_situation', 'normal operations')}",
            "player_choice": f"Autonomous action - {npc_name} acts independently",
            "atmosphere": context.get("atmosphere", ""),
            "sensory_details": context.get("sensory_details", ""),
            "char_brief": context.get("npc_personality", "neutral"),
            "relationship_summary_from_state": str(context.get("relationships", {})),
            "player_inventory_brief": "",
            "memory_layers": context.get("memory_layers", []),
        }

        try:
            result = self.run(variables=variables)
            self.LOGGER.debug("Autonomous action result: %s", result)

            # Normalize the result
            if isinstance(result, dict):
                return self._normalize_autonomous_action(result)
            elif isinstance(result, list) and result:
                return self._normalize_autonomous_action(result[0])

            # Fallback autonomous action
            return {
                "npc_name": npc_name,
                "action": "stand_guard",
                "reason": "Maintaining defensive position",
                "safe_functions": [],
            }

        except Exception as e:
            self.LOGGER.error("Autonomous failed for %s: %s", npc_name, e)
            return {
                "npc_name": npc_name,
                "action": "idle",
                "reason": "Unable to determine action",
                "safe_functions": [],
            }

    def _normalize_autonomous_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize autonomous action output."""
        normalized = {
            "npc_name": action.get("npc_name", "unknown"),
            "action": action.get("action", "idle"),
            "reason": action.get("reason", "No reason given"),
            "safe_functions": action.get("safe_functions", []),
        }

        # Add effects based on action type
        action_type = normalized["action"]
        effects = {}
        if "vigilant" in action_type or "stand" in action_type:
            effects["metric_changes"] = {"order": 1}
        elif "patrol" in action_type or "move" in action_type:
            effects["metric_changes"] = {"morale": 1}
        elif "boost" in action_type or "encourage" in action_type:
            effects["metric_changes"] = {"morale": 2}
        elif "manage" in action_type or "organize" in action_type:
            effects["metric_changes"] = {"resources": 1}

        if effects:
            normalized["effects"] = effects

        # Clean safe functions
        if normalized["safe_functions"]:
            cleaned = []
            for func in normalized["safe_functions"]:
                if isinstance(func, dict) and "name" in func:
                    cleaned.append(
                        {
                            "name": func["name"],
                            "args": func.get("args", []),
                            "kwargs": func.get("kwargs", {}),
                        }
                    )
            normalized["safe_functions"] = cleaned

        return normalized

    def _add_persona_guidance(self, variables: Dict[str, Any]) -> Dict[str, Any]:
        """Add trust-based persona guidance for character development."""
        enhanced_vars = dict(variables)

        # Extract NPC trust levels from context
        char_brief = variables.get("char_brief", "")
        npcs = []
        if "Rhea" in char_brief:
            npcs.append("Rhea")
        if "Boris" in char_brief or "Bor" in char_brief:
            npcs.append("Boris")

        persona_guidance = []
        for npc in npcs:
            # Parse trust level from relationship summary
            trust_level = "neutral"  # Default
            relationship_summary = variables.get("relationship_summary_from_state", "")
            if npc in relationship_summary:
                if (
                    "high trust" in relationship_summary.lower()
                    or "trust: 4" in relationship_summary
                    or "trust: 5" in relationship_summary
                ):
                    trust_level = "high_trust"
                elif (
                    "low trust" in relationship_summary.lower()
                    or "trust: 1" in relationship_summary
                    or "trust: 2" in relationship_summary
                ):
                    trust_level = "low_trust"
            persona = self.persona_map.get(npc, {}).get(trust_level, {})

            if persona:
                guidance = f"{npc} persona: {persona['mood']} mood, {persona['communication']} communication, {persona['cooperation']} cooperation."
                persona_guidance.append(guidance)

        if persona_guidance:
            existing_context = enhanced_vars.get("WORLD_CONTEXT", "")
            persona_text = "CHARACTER DEVELOPMENT GUIDANCE: " + " ".join(
                persona_guidance
            )
            # Style IDs to reinforce tone differences per character
            style_ids = []
            if "Rhea" in npcs:
                style_ids.append("Rhea=impulsive-emotional")
            if "Boris" in npcs:
                style_ids.append("Boris=analytical-formal")
            style_hint = "STYLE_ID: " + "; ".join(style_ids) if style_ids else ""
            enhanced_vars["WORLD_CONTEXT"] = (
                f"{persona_text}\n{style_hint}\n\n{existing_context}"
            )

        return enhanced_vars

    def _enforce_behavior_variation(self, variables: Dict[str, Any]) -> Dict[str, Any]:
        """If an NPC repeatedly uses the same intent, nudge the agent to vary.

        This inserts a short directive into WORLD_CONTEXT to push the model
        to produce an action (speak/move/assist) instead of repeated 'observe'.
        """
        enhanced = dict(variables)
        memory_layers = enhanced.get("memory_layers", []) or []
        # Quick heuristic: look for recent 'Observe' occurrences for Rhea/Boris
        for npc in ("Rhea", "Boris"):
            recent = [m for m in memory_layers if isinstance(m, str) and npc in m]
            # Count 'observe' mentions in recent entries
            obs_count = 0
            for m in recent[-4:]:
                if (
                    "observe" in m.lower()
                    or "stand guard" in m.lower()
                    or "vigil" in m.lower()
                ):
                    obs_count += 1
            if obs_count >= 2:
                # Add a strong constraint to force a different action next turn
                existing = enhanced.get("WORLD_CONTEXT", "")
                directive = (
                    f"NOTE: {npc} has repeatedly only observed recently ({obs_count} times). "
                    "For narrative variation, next behaviour should be an active verb: speak, move, assist, or challenge."
                )
                enhanced["WORLD_CONTEXT"] = directive + "\n\n" + existing
                self.LOGGER.info(
                    "Enforced behaviour variation for %s (count=%d)", npc, obs_count
                )
        return enhanced
