"""Ollama local LLM integration for Fortress Director agents.

Provides adapters for DirectorAgent, PlannerAgent, WorldRendererAgent to work
with locally-running Ollama models (Mistral 7B, Phi-3 Mini, Gemma 2B).
"""

import json
import logging
from typing import Optional, Dict, Any, List
import requests

logger = logging.getLogger(__name__)


class OllamaClient:
    """Client for local Ollama LLM inference."""

    def __init__(self, base_url: str = "http://localhost:11434"):
        """Initialize Ollama client.

        Args:
            base_url: Ollama server URL (default: localhost:11434)
        """
        self.base_url = base_url
        self.generate_url = f"{base_url}/api/generate"
        self.pull_url = f"{base_url}/api/pull"

    def is_available(self) -> bool:
        """Check if Ollama server is running."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            return response.status_code == 200
        except Exception:
            return False

    def generate(
        self,
        model: str,
        prompt: str,
        max_tokens: int = 500,
        temperature: float = 0.7,
    ) -> Optional[str]:
        """Generate response from Ollama model.

        Args:
            model: Model name (e.g., 'mistral', 'phi', 'gemma')
            prompt: Input prompt
            max_tokens: Max tokens in response
            temperature: Sampling temperature

        Returns:
            Generated text or None if failed
        """
        try:
            payload = {
                "model": model,
                "prompt": prompt,
                "num_predict": max_tokens,
                "temperature": temperature,
                "stream": False,
            }

            response = requests.post(self.generate_url, json=payload, timeout=60)
            response.raise_for_status()

            result = response.json()
            return result.get("response", "").strip()

        except requests.exceptions.Timeout:
            logger.error(f"Timeout calling Ollama for model {model}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama request failed: {e}")
            return None

    def pull_model(self, model: str) -> bool:
        """Pull model from Ollama registry.

        Args:
            model: Model name to pull

        Returns:
            True if successful, False otherwise
        """
        try:
            payload = {"name": model}
            response = requests.post(self.pull_url, json=payload, timeout=300)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Failed to pull model {model}: {e}")
            return False


class DirectorAgentOllama:
    """DirectorAgent using Ollama local LLM."""

    def __init__(self, client: OllamaClient, model: str = "mistral"):
        """Initialize DirectorAgent with Ollama.

        Args:
            client: OllamaClient instance
            model: Model name (default: mistral for 7B variant)
        """
        self.client = client
        self.model = model

    def generate_scene_with_choices(
        self, archive_context: str, world_state: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Generate game scene with 3 diegetic choices.

        Args:
            archive_context: Injected archive context
            world_state: Current world state

        Returns:
            Dict with scene, choices, or None if failed
        """
        prompt = f"""You are a game director for a fortress defense narrative.

{archive_context}

Based on the above context, generate:
1. A vivid scene description (2-3 sentences)
2. Three diegetic choices the player can make

Respond in JSON format:
{{
    "scene": "description here",
    "choices": [
        {{"choice": "option 1"}},
        {{"choice": "option 2"}},
        {{"choice": "option 3"}}
    ]
}}"""

        response = self.client.generate(
            self.model, prompt, max_tokens=300, temperature=0.8
        )

        if not response:
            return None

        try:
            # Extract JSON from response
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                return json.loads(json_str)
        except json.JSONDecodeError:
            logger.warning("Failed to parse DirectorAgent JSON response")

        return None


class PlannerAgentOllama:
    """PlannerAgent using Ollama local LLM."""

    def __init__(self, client: OllamaClient, model: str = "phi"):
        """Initialize PlannerAgent with Ollama.

        Args:
            client: OllamaClient instance
            model: Model name (default: phi for Phi-3 Mini)
        """
        self.client = client
        self.model = model

    def decide_strategy(
        self, archive_context: str, player_choice: str
    ) -> Optional[Dict[str, Any]]:
        """Decide NPC/world response to player choice.

        Args:
            archive_context: Injected archive context
            player_choice: Player's chosen action

        Returns:
            Dict with strategy, npc_reactions, or None if failed
        """
        prompt = f"""You are a strategic planner for NPC responses in a fortress defense game.

{archive_context}

Player chose: {player_choice}

Determine the NPC/world response. Consider:
- Current threat level
- NPC morale and fatigue
- Available resources
- Strategic advantages

Respond in JSON format:
{{
    "strategy": "brief strategic decision",
    "actions": ["action 1", "action 2"],
    "threat_change": -0.1
}}"""

        response = self.client.generate(
            self.model, prompt, max_tokens=250, temperature=0.7
        )

        if not response:
            return None

        try:
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                return json.loads(json_str)
        except json.JSONDecodeError:
            logger.warning("Failed to parse PlannerAgent JSON response")

        return None


class WorldRendererOllama:
    """WorldRendererAgent using Ollama local LLM."""

    def __init__(self, client: OllamaClient, model: str = "gemma"):
        """Initialize WorldRendererAgent with Ollama.

        Args:
            client: OllamaClient instance
            model: Model name (default: gemma for 2B variant)
        """
        self.client = client
        self.model = model

    def render_atmosphere(
        self, archive_context: str, narrative_phase: str
    ) -> Optional[str]:
        """Render world atmosphere and sensory descriptions.

        Args:
            archive_context: Injected archive context
            narrative_phase: Current narrative phase (exposition, rising, climax, etc)

        Returns:
            Atmospheric description or None if failed
        """
        prompt = f"""You are a world renderer for a fortress defense narrative.

{archive_context}

Current phase: {narrative_phase}

Generate atmospheric description (3-4 sentences) focusing on:
- Sensory details (sights, sounds, smells)
- Environmental changes
- Mood and tension

Keep it immersive and diegetic."""

        response = self.client.generate(
            self.model, prompt, max_tokens=200, temperature=0.9
        )

        return response if response else None


class OllamaAgentPipeline:
    """Orchestrates DirectorAgent → PlannerAgent → WorldRenderer flow."""

    def __init__(self, client: Optional[OllamaClient] = None):
        """Initialize pipeline.

        Args:
            client: OllamaClient instance (creates default if None)
        """
        self.client = client or OllamaClient()
        self.director = DirectorAgentOllama(self.client, "mistral")
        self.planner = PlannerAgentOllama(self.client, "phi")
        self.renderer = WorldRendererOllama(self.client, "gemma")

    def execute_turn(
        self,
        archive_context: str,
        world_state: Dict[str, Any],
        player_choice: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Execute full turn with all agents.

        Args:
            archive_context: Injected archive context
            world_state: Current world state
            player_choice: Optional previous player choice

        Returns:
            Turn result with scene, choices, reactions, or None if failed
        """
        turn_result = {"turn": world_state.get("turn", 0)}

        # Generate scene
        scene_result = self.director.generate_scene_with_choices(
            archive_context, world_state
        )
        if not scene_result:
            return None
        turn_result["scene"] = scene_result.get("scene")
        turn_result["choices"] = scene_result.get("choices")

        # If player made a choice, get planner response
        if player_choice:
            strategy = self.planner.decide_strategy(archive_context, player_choice)
            if strategy:
                turn_result["strategy"] = strategy.get("strategy")
                turn_result["actions"] = strategy.get("actions", [])
                turn_result["threat_change"] = strategy.get("threat_change", 0)

        # Render atmosphere
        narrative_phase = world_state.get("narrative_phase", "exposition")
        atmosphere = self.renderer.render_atmosphere(archive_context, narrative_phase)
        if atmosphere:
            turn_result["atmosphere"] = atmosphere

        return turn_result
