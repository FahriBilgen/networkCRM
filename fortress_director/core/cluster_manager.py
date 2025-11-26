"""Function clustering system for context-aware safe function selection.

This module provides intelligent function filtering based on game state context,
ensuring that agents only see relevant functions for each turn.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, List, Set

from .function_registry import SafeFunctionMeta, SafeFunctionRegistry, load_defaults

LOGGER = logging.getLogger(__name__)


ProjectedState = Dict[str, Any]


class ClusterManager:
    """Manages function clustering and context-based filtering."""

    def __init__(self, metadata: Iterable[SafeFunctionMeta] | None = None) -> None:
        self._function_metadata: Dict[str, SafeFunctionMeta] = {}
        self._category_index: Dict[str, Set[str]] = {}
        dataset = metadata or load_defaults().values()
        for entry in dataset:
            self.register_metadata(entry)

    @classmethod
    def from_registry(cls, registry: SafeFunctionRegistry) -> "ClusterManager":
        """Convenience builder that seeds metadata from a registry."""

        return cls(registry.list_metadata())

    def register_metadata(self, meta: SafeFunctionMeta) -> None:
        """Register metadata for a safe function."""
        self._function_metadata[meta.name] = meta

        if meta.category:
            if meta.category not in self._category_index:
                self._category_index[meta.category] = set()
            self._category_index[meta.category].add(meta.name)

        LOGGER.debug(f"Registered metadata for function: {meta.name}")

    def get_relevant_functions(
        self,
        context: ProjectedState,
        max_count: int = 30,
    ) -> List[SafeFunctionMeta]:
        """Get relevant functions based on game state context.

        Args:
            context: Current game state snapshot (projected state)
            max_count: Maximum number of functions to return

        Returns:
            List of function metadata sorted by relevance
        """
        if not self._function_metadata:
            LOGGER.warning("No function metadata registered")
            return []

        # Extract context signals
        in_combat = self._detect_combat(context)
        needs_resources = self._detect_resource_shortage(context)
        has_map_event = self._detect_map_event(context)
        npc_interaction = self._detect_npc_interaction(context)

        # Collect relevant function names
        relevant_names: Set[str] = set()

        category_targets: Set[str] = set()
        if in_combat:
            category_targets.update({"combat", "npc", "structure"})
        if needs_resources:
            category_targets.update({"economy", "morale"})
        if has_map_event:
            category_targets.update({"event"})
        if npc_interaction:
            category_targets.update({"npc", "morale"})

        for category in category_targets:
            relevant_names.update(self._category_index.get(category, set()))

        # If no specific context, return high-priority generic functions
        if not relevant_names:
            relevant_names = set(self._function_metadata.keys())

        # Convert to metadata list and sort by priority
        result = [
            self._function_metadata[name]
            for name in relevant_names
            if name in self._function_metadata
        ]
        result.sort(key=lambda m: (m.category, m.name))

        # Limit to max_count
        return result[:max_count]

    def _detect_combat(self, context: ProjectedState) -> bool:
        """Detect if there's active combat in the context."""
        flags = context.get("flags", [])
        if "combat_active" in flags or "under_attack" in flags:
            return True

        # Check for hostile NPCs nearby
        npc_locations = context.get("npc_locations", [])
        for npc in npc_locations:
            if isinstance(npc, dict) and npc.get("hostile"):
                return True

        return False

    def _detect_resource_shortage(self, context: ProjectedState) -> bool:
        """Detect if there's resource shortage."""
        metrics = context.get("metrics", {})
        resources = metrics.get("resources", 100)
        morale = metrics.get("morale", 100)

        return resources < 30 or morale < 30

    def _detect_map_event(self, context: ProjectedState) -> bool:
        """Detect if there's an active map event."""
        map_layers = context.get("map_layers", {})
        for layer in map_layers.values():
            if isinstance(layer, dict):
                threat = layer.get("threat_level", "low")
                if threat in ("high", "critical"):
                    return True

        return False

    def _detect_npc_interaction(self, context: ProjectedState) -> bool:
        """Detect if NPC interaction is likely."""
        recent_events = context.get("recent_events", [])
        for event in recent_events[-3:]:
            if isinstance(event, str):
                if "talk" in event.lower() or "npc" in event.lower():
                    return True

        return False

    def get_functions_by_category(self, category: str) -> List[SafeFunctionMeta]:
        """Get all functions in a specific category."""
        function_names = self._category_index.get(category, set())
        return [
            self._function_metadata[name]
            for name in function_names
            if name in self._function_metadata
        ]

    def get_functions_by_tag(self, tag: str) -> List[SafeFunctionMeta]:
        """Legacy compatibility hook; tags are no longer supported."""

        return []
