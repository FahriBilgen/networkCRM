from __future__ import annotations

import logging
import re

"""Implementation of the World Agent using the Ollama client stack."""
from typing import Any, Dict, Optional

from fortress_director.agents.base_agent import (
    BaseAgent,
    PromptTemplate,
    build_prompt_path,
    default_ollama_client,
    get_model_config,
)
from fortress_director.llm.ollama_client import OllamaClient


class WorldAgent(BaseAgent):
    LOGGER = logging.getLogger(__name__)
    """Describes the atmosphere and sensory texture of the environment."""

    def __init__(self, *, client: Optional[OllamaClient] = None) -> None:
        template = PromptTemplate(build_prompt_path("world_prompt.txt"))
        super().__init__(
            name="World",
            prompt_template=template,
            model_config=get_model_config("world"),
            client=client or default_ollama_client("world"),
        )
        # Track motif repetition to prevent semantic drift
        self.motif_counter = {}  # word -> count in last 3 turns
        self.motif_ban_list = set()  # banned motifs

    def describe(self, variables: Dict[str, Any]) -> Dict[str, Any]:
        """
        Produce atmospheric context for the current turn, with forced novelty
        and diversity.
        """
        self.LOGGER.info("WorldAgent.describe called with variables: %s", variables)

        # --- Forced novelty and diversity logic ---
        turn = variables.get("turn") or variables.get("day") or 1
        force_variation = variables.get("force_world_variation", False)
        novelty_cycle = 2  # Every 2 turns, force novelty
        if (turn % novelty_cycle == 0) or force_variation:
            self.LOGGER.info("Injecting forced novelty/diversity for turn %s", turn)
            # Clear motif tracking to force new descriptions
            self.motif_counter.clear()
            self.motif_ban_list.clear()
            variables["forced_variation_prompt"] = (
                "IMPORTANT: Inject new atmospheric motifs, rotate "
                "environmental moods, and avoid repetition. Change the "
                "sensory focus and mood for this turn."
            )
            # Add a novelty flag for downstream agents
            variables["novelty_flag"] = True
            # Rotate environmental moods
            moods = [
                "tense",
                "hopeful",
                "foreboding",
                "restless",
                "melancholic",
                "resolute",
                "anxious",
                "determined",
                "uneasy",
                "vigilant",
            ]
            mood = moods[(turn // novelty_cycle) % len(moods)]
            variables["mood_hint"] = f"Atmospheric mood for this turn: {mood}."

        # Enforce time_of_day consistency to prevent semantic drift.
        time_of_day = variables.get("time")
        if not time_of_day:
            wc = variables.get("WORLD_CONTEXT", "")
            m = re.search(r"Time\s+([^\n]+)", wc)
            if m:
                time_of_day = m.group(1).strip()
            else:
                time_of_day = "morning"

        # Provide an explicit hint to the model to prefer the given time token.
        variables = dict(variables)
        # forbidden_times: mevcut zaman dışındaki tüm zamanlar
        all_times = ["dawn", "morning", "afternoon", "evening", "night", "midnight"]
        forbidden_times = [t for t in all_times if t != time_of_day]
        variables["forbidden_times"] = ", ".join(forbidden_times)
        variables.setdefault(
            "time_hint",
            f"Use the following time-of-day framing exactly: {time_of_day}. "
            f"Do not use words like {', '.join(forbidden_times)}.",
        )

        # Update motif counter and ban list
        self._update_motif_tracking(variables)

        max_retries = 2
        for attempt in range(max_retries):
            try:
                # Add banned motifs to variables to prevent repetition
                variables_with_bans = dict(variables)
                variables_with_bans["banned_motifs"] = list(self.motif_ban_list)

                result = self.run(variables=variables_with_bans)
                self.LOGGER.debug("Model returned: %s", result)
                if not isinstance(result, dict):
                    self.LOGGER.error(
                        "World agent must return a JSON object, got: %s", result
                    )
                    if attempt < max_retries - 1:
                        continue
                    raise ValueError("World agent must return a JSON object")

                # Validate time consistency in result; allow adjacent times
                # (evening<->night)
                if not self._validate_time_consistency(result, time_of_day):
                    self.LOGGER.warning("Time inconsistency detected, retrying...")
                    # If inconsistency is only with an adjacent period (e.g.,
                    # evening vs night), accept it
                    if self._is_adjacent_time(result, time_of_day):
                        self.LOGGER.info(
                            "Inconsistency is adjacent (acceptable): "
                            "accepting result for time=%s",
                            time_of_day,
                        )
                    elif attempt < max_retries - 1:
                        continue

                # Clean up text fields to remove encoding artifacts and typos
                for key in ["atmosphere", "sensory_details"]:
                    if key in result and isinstance(result[key], str):
                        # Remove non-printable chars and fix common typos
                        cleaned = re.sub(r"[^A-Za-z0-9\s'.,!?]", "", result[key])
                        # Fix contractions like "Dawn'thin" -> "Dawn thin"
                        cleaned = re.sub(r"(\w+)'t(\w+)", r"\1 \2", cleaned)
                        result[key] = cleaned.strip()

                # Validate required keys
                if "atmosphere" not in result or "sensory_details" not in result:
                    if attempt < max_retries - 1:
                        continue
                    raise ValueError("Missing required keys in world description")

                # Update motif tracking with successful result
                self._track_motifs_in_result(result)

                self.LOGGER.info("World description: %s", result)
                return result
            except Exception as e:
                self.LOGGER.warning("WorldAgent attempt %d failed: %s", attempt + 1, e)
                if attempt == max_retries - 1:
                    # Fallback to previous world constraint
                    prev_constraint = variables.get(
                        "world_constraint_from_prev_turn", {}
                    )
                    if isinstance(prev_constraint, dict):
                        fallback = {
                            "atmosphere": prev_constraint.get(
                                "atmosphere", "A somber dawn breaks."
                            ),
                            "sensory_details": prev_constraint.get(
                                "sensory_details", "The air is crisp and foreboding."
                            ),
                        }
                        self.LOGGER.warning(
                            "Using fallback world description: %s", fallback
                        )
                        return fallback
                    raise

    def _update_motif_tracking(self, variables: Dict[str, Any]) -> None:
        """Update motif counter from recent world context."""
        recent_events = variables.get("recent_events", "")
        if isinstance(recent_events, str):
            words = re.findall(r"\b\w+\b", recent_events.lower())
            for word in words:
                if len(word) > 3:  # Only track meaningful words
                    self.motif_counter[word] = self.motif_counter.get(word, 0) + 1
                    # Ban motifs that appear more than 2 times in 3 turns
                    if self.motif_counter[word] > 2:
                        self.motif_ban_list.add(word)

        # Keep only recent motifs (simulate 3-turn window)
        if len(self.motif_counter) > 50:
            # Remove oldest entries (simple FIFO)
            sorted_items = sorted(self.motif_counter.items(), key=lambda x: x[1])
            for word, _ in sorted_items[:10]:
                self.motif_counter.pop(word, None)

    def _validate_time_consistency(
        self, result: Dict[str, Any], time_of_day: str
    ) -> bool:
        """Check if result is consistent with the given time of day."""
        text = (
            f"{result.get('atmosphere', '')} {result.get('sensory_details', '')}"
        ).lower()

        # Define time indicators
        time_indicators = {
            "morning": ["dawn", "morning", "sunrise", "early light"],
            "afternoon": ["afternoon", "noon", "daylight", "midday"],
            "evening": ["evening", "dusk", "twilight", "sunset"],
            "night": ["night", "darkness", "midnight", "stars"],
        }

        # Semantic clusters: accept intra-cluster mentions as consistent
        cluster_map = {
            "dawn": "morning",
            "morning": "morning",
            "sunrise": "morning",
            "early light": "morning",
            "noon": "afternoon",
            "afternoon": "afternoon",
            "midday": "afternoon",
            "daylight": "afternoon",
            "evening": "evening",
            "dusk": "evening",
            "twilight": "evening",
            "sunset": "evening",
            "night": "night",
            "midnight": "night",
            "stars": "night",
            "darkness": "night",
        }

        # Check for conflicting time indicators
        # current_indicators = time_indicators.get(time_of_day, [])
        conflicting_times = []
        for other_time, indicators in time_indicators.items():
            if other_time != time_of_day:
                # Accept indicators that map to the same cluster as time_of_day
                filtered = []
                for indicator in indicators:
                    if indicator in text:
                        same_cluster = (
                            cluster_map.get(indicator) == cluster_map.get(time_of_day, time_of_day)
                        )
                        if not same_cluster:
                            filtered.append(indicator)
                if filtered:
                    conflicting_times.append(other_time)

        if conflicting_times:
            self.LOGGER.warning(
                f"Time inconsistency: {time_of_day} but found {conflicting_times} indicators"
            )
            return False
        return True

    def _is_adjacent_time(self, result: Dict[str, Any], time_of_day: str) -> bool:
        """Return True if the only conflict is with an adjacent time period.

        For example, 'evening' is adjacent to 'night' and should be
        accepted to reduce noisy retries from the language model.
        """
        text = f"{result.get('atmosphere', '')} {result.get('sensory_details', '')}".lower()
        time_indicators = {
            "morning": ["dawn", "morning", "sunrise", "early light"],
            "afternoon": ["afternoon", "noon", "daylight", "midday"],
            "evening": ["evening", "dusk", "twilight", "sunset"],
            "night": ["night", "darkness", "midnight", "stars"],
        }
        adjacent_map = {
            "morning": ["afternoon"],
            "afternoon": ["morning"],
            "evening": ["night"],
            "night": ["evening"],
        }
        candidates = []
        for other_time, indicators in time_indicators.items():
            if other_time == time_of_day:
                continue
            if any(ind in text for ind in indicators):
                candidates.append(other_time)
        # Accept only when the conflicting times are a subset of adjacent_map
        if not candidates:
            return False
        for c in candidates:
            if c not in adjacent_map.get(time_of_day, []):
                return False
        return True

    def _track_motifs_in_result(self, result: Dict[str, Any]) -> None:
        """Track motifs from successful result."""
        text = f"{result.get('atmosphere', '')} {result.get('sensory_details', '')}".lower()
        words = re.findall(r"\b\w+\b", text)
        for word in words:
            if len(word) > 3:
                self.motif_counter[word] = self.motif_counter.get(word, 0) + 1
