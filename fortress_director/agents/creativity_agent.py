from __future__ import annotations
import logging
import random
from typing import Any, Dict, Optional

from fortress_director.agents.base_agent import (
    BaseAgent,
    PromptTemplate,
    build_prompt_path,
    default_ollama_client,
    get_model_config,
)
from fortress_director.llm.ollama_client import OllamaClient
from fortress_director.settings import (
    CREATIVITY_MOTIF_INTERVAL,
    CREATIVITY_MOTIF_PROBABILITY,
    CREATIVITY_FORCE_SANDBOX,
    MAX_MOTIF_INJECTIONS_PER_WINDOW,
)

LOGGER = logging.getLogger(__name__)

MOTIF_TABLE = [
    "betrayal",
    "fire",
    "memory",
    "storm",
    "music",
    "echoes",
    "shadows",
    "festival",
    "loss",
    "mystery",
]

FALLBACK_TEMPLATES = [
    "The air grows tense with an unexpected twist.",
    "Shadows whisper secrets from the past.",
    "A sudden storm brews on the horizon.",
    "Echoes of forgotten melodies fill the air.",
    "The ground trembles with hidden power.",
    "Mysterious figures emerge from the mist.",
]


class CreativityAgent(BaseAgent):
    """
    Manipulates prompts and context to inject novelty, motifs, or
    style variation. Can use LLM for prompt rewriting or fallback to
    motif injection.
    """

    def __init__(
        self, *, client: Optional[OllamaClient] = None, use_llm: bool = True
    ) -> None:
        template = PromptTemplate(build_prompt_path("creativity_prompt.txt"))
        super().__init__(
            name="Creativity",
            prompt_template=template,
            model_config=(
                get_model_config("creativity")
                if use_llm
                else get_model_config("character")
            ),
            client=client or default_ollama_client("creativity"),
            expects_json=False,
        )
        self.use_llm = use_llm

    def enrich_event(
        self,
        event_output: Dict[str, Any],
        turn: int,
    ) -> Dict[str, Any]:
        """
            Optionally rewrite the event scene or inject a motif for novelty.
        If use_llm is True, use LLM to rewrite the scene. Otherwise inject
        motifs on a configurable interval as a fallback.
        Enhanced logging and stderr alerts for critical/fallback errors.
        """
        import sys

        event = dict(event_output)
        LOGGER.info(f"CreativityAgent.enrich_event called (turn={turn})")
        # Prefer LLM-based rewrites when available. If the orchestrator
        # signalled novelty via a novelty_flag or sandbox mode is enabled,
        # be more aggressive about rewrites.
        force_sandbox = bool(event.get("novelty_flag")) or (CREATIVITY_FORCE_SANDBOX)
        if self.use_llm:
            prompt_vars = {
                "scene": event.get("scene", ""),
                "options": str(event.get("options", [])),
                "turn": turn,
            }
            try:
                LOGGER.debug(f"CreativityAgent LLM prompt_vars: {prompt_vars}")
                rewritten = self.run(variables=prompt_vars)
                # Basic sanitize of assistant lead-in phrases + anti-meta guard
                if isinstance(rewritten, str):
                    clean = rewritten.strip()
                    for prefix in (
                        "Sure, here",
                        "Sure, here's",
                        "Sure, here is",
                        "Here is the rewritten",
                        "Here's the rewritten",
                    ):
                        if clean.startswith(prefix):
                            clean = clean[len(prefix) :].lstrip(" :\n")
                    meta_markers = (
                        "is the rewritten prompt",
                        "Write a story",
                        "Rewrite this prompt",
                        "As an AI",
                    )
                    if clean and not any(m.lower() in clean.lower() for m in meta_markers):
                        event["scene"] = clean
                        event["motif_injected"] = None
                        LOGGER.info("CreativityAgent LLM event rewrite applied.")
                        return event
                LOGGER.warning(
                    "CreativityAgent LLM returned empty/invalid or meta-like string."
                )
            except Exception as exc:
                LOGGER.warning("CreativityAgent LLM event rewrite failed: %s", exc)
                print(
                    f"[ALERT] CreativityAgent LLM event rewrite failed: {exc}",
                    file=sys.stderr,
                )
                # Fallback: use deterministic template instead of failing
                fallback_scene = random.choice(FALLBACK_TEMPLATES)
                event["scene"] = fallback_scene
                event["motif_injected"] = None
                LOGGER.info("CreativityAgent applied fallback template.")
                return event
        # Fallback: motif injection controlled by settings for frequency
        do_interval = (turn % CREATIVITY_MOTIF_INTERVAL) == 0
        if do_interval or force_sandbox:
            # Check window limit for motif injections
            recent_motifs = event.get("recent_motifs", [])
            recent_injections = sum(1 for m in recent_motifs[-5:] if m)  # Last 5 turns
            if recent_injections >= MAX_MOTIF_INJECTIONS_PER_WINDOW:
                LOGGER.debug("CreativityAgent: motif injection limit reached")
            else:
                # Use stochastic injection so motif variety remains unpredictable
                prob = float(CREATIVITY_MOTIF_PROBABILITY)
                roll = random.random()
                LOGGER.debug(
                    "CreativityAgent motif decision interval=%s force_sandbox=%s "
                    "roll=%.3f prob=%.3f",
                    do_interval,
                    force_sandbox,
                    roll,
                    prob,
                )
                if roll < prob or force_sandbox:
                    # Motif rotation: avoid repeating recent motifs
                    available_motifs = [
                        m for m in MOTIF_TABLE if m not in recent_motifs[-3:]
                    ]
                    if not available_motifs:
                        available_motifs = MOTIF_TABLE  # Fallback if all recent
                    motif = random.choice(available_motifs)
                    motifs = list(recent_motifs) + [motif]
                    event["recent_motifs"] = motifs[-10:]
                    event["motif_injected"] = motif
                    # Persist motif for a few turns so downstream systems
                    # and the EventAgent can honor a continuing motif thread.
                    event["motif_persist_for"] = 3
                    if "scene" in event:
                        event["scene"] = (
                            event.get("scene", "") + f" (Motif: {motif})"
                        ).strip()
                    LOGGER.info(f"CreativityAgent injected motif: {motif}")
                    print(
                        f"[INFO] CreativityAgent injected motif: {motif}",
                        file=sys.stderr,
                    )
                else:
                    LOGGER.debug("CreativityAgent: motif chance failed")
        else:
            LOGGER.debug("CreativityAgent: not interval; no motif injected")
        return event
