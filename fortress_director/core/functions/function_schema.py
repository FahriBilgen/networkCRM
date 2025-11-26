from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class FunctionParam:
    """Schema definition for a safe function parameter."""

    name: str
    type: str  # "int", "str", "float", "npc_id", "coord", etc.
    required: bool = True


@dataclass
class SafeFunctionMeta:
    """Metadata used to describe a safe function entry."""

    name: str
    category: str  # combat, economy, morale, structure, event, npc, utility
    description: str
    params: List[FunctionParam] = field(default_factory=list)
    gas_cost: int = 1
    handler: Optional[Callable[..., Dict[str, Any]]] = None  # executor assigns
    planner_weight: float = 1.0
    enabled: bool = True
    theme_overrides: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def signature(self) -> str:
        """Convenience helper that returns a readable signature string."""

        parts = []
        for param in self.params:
            suffix = "" if param.required else "?"
            parts.append(f"{param.name}:{param.type}{suffix}")
        return f"{self.name}({', '.join(parts)})"
