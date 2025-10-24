"""Offline-friendly stand-in for the Ollama HTTP client."""
from __future__ import annotations

import json
from typing import Any, Dict, Iterable, Optional


class OfflineOllamaClient:
    """Return deterministic JSON payloads without performing network I/O."""

    def __init__(self, agent_key: str = "generic") -> None:
        self._agent_key = agent_key

    def generate(
        self,
        *,
        model: str,
        prompt: str,
        options: Optional[Dict[str, Any]] = None,
        response_format: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload = self._build_payload()
        return {"response": json.dumps(payload)}

    def chat(
        self,
        *,
        model: str,
        messages: Iterable[Dict[str, str]],
        options: Optional[Dict[str, Any]] = None,
        response_format: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload = self._build_payload()
        return {"response": json.dumps(payload)}

    def _build_payload(self) -> Any:
        if self._agent_key == "world":
            return {
                "atmosphere": "storm glare",
                "sensory_details": "hail rattles the stones",
            }
        if self._agent_key == "event":
            return {
                "scene": "Storm clouds gather over the western wall as watch fires hiss.",
                "options": [
                    {
                        "id": "opt_1",
                        "text": "Rally the nearby scouts to reinforce the gate.",
                        "action_type": "command",
                    },
                    {
                        "id": "opt_2",
                        "text": "Signal the keep for additional lantern oil.",
                        "action_type": "support",
                    },
                    {
                        "id": "opt_3",
                        "text": "Quietly observe the storm's strange rhythm.",
                        "action_type": "observe",
                    },
                ],
                "major_event": False,
                "safe_functions": [
                    {
                        "name": "change_weather",
                        "kwargs": {
                            "atmosphere": "electric storm",
                            "sensory_details": "lightning traces the parapets",
                        },
                        "metadata": {"origin": "event_stub"},
                    }
                ],
            }
        if self._agent_key == "character":
            return [
                {
                    "name": "Rhea",
                    "intent": "defend",
                    "action": "brace_shield",
                    "speech": "I'll keep the storm off the wall while you plan our next move.",
                    "effects": {
                        "trust_delta": 1,
                        "flag_set": ["storm_vigil"],
                    },
                    "safe_functions": [
                        {
                            "name": "spawn_item",
                            "kwargs": {
                                "item_id": "lantern_oil",
                                "target": "player",
                            },
                            "metadata": {"origin": "character_stub"},
                        }
                    ],
                }
            ]
        if self._agent_key == "judge":
            return {"consistent": True, "reason": "offline stub"}
        return {"response": "offline stub"}
