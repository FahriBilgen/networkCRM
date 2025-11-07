"""Safe function execution helpers extracted from the orchestrator."""
from __future__ import annotations

import ast
import logging
import time
from typing import Any, Dict, List, Optional, Set, Tuple

from fortress_director.codeaware.function_registry import (
    FunctionCall,
    FunctionNotRegisteredError,
    FunctionValidationError,
)

LOGGER = logging.getLogger(__name__)


class SafeFunctionExecutor:
    """Collects, normalizes, and runs safe function payloads."""

    def __init__(self, orchestrator: Any) -> None:
        self._orchestrator = orchestrator
        self._last_guardrail_stats: Dict[str, Any] = {}

    @property
    def last_guardrail_stats(self) -> Dict[str, Any]:
        return dict(self._last_guardrail_stats)

    def execute_queue(
        self,
        *,
        event_output: Dict[str, Any],
        character_output: List[Dict[str, Any]],
        world_output: Optional[Dict[str, Any]] = None,
        planner_calls: Optional[List[Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Execute any safe function requests emitted by agents."""

        calls = self._collect_safe_function_calls(
            event_output=event_output,
            character_output=character_output,
            world_output=world_output or {},
            planner_calls=planner_calls,
        )
        filtered_calls, guardrail_stats = self._apply_safe_function_guardrails(calls)
        self._last_guardrail_stats = guardrail_stats
        results: List[Dict[str, Any]] = []
        try:
            for payload, metadata in filtered_calls:
                timestamp_ms = int(time.time() * 1000)
                outcome = self._orchestrator.run_safe_function(
                    payload,
                    metadata=metadata,
                )
                entry_metadata = dict(metadata or {})
                results.append(
                    {
                        "name": payload.get("name", "unknown"),
                        "result": outcome,
                        "effects": outcome,
                        "metadata": entry_metadata,
                        "success": True,
                        "timestamp": timestamp_ms,
                        "summary": self._summarize_safe_function_call(payload),
                    }
                )
            return results
        except (FunctionValidationError, FunctionNotRegisteredError) as exc:
            LOGGER.error("Turn aborted due to safe function error: %s", exc)
            raise

    def _collect_safe_function_calls(
        self,
        *,
        event_output: Dict[str, Any],
        character_output: List[Dict[str, Any]],
        world_output: Dict[str, Any],
        planner_calls: Optional[List[Any]] = None,
    ) -> List[Tuple[Dict[str, Any], Dict[str, Any]]]:
        queue: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
        planner_ids: Set[int] = set()
        if planner_calls:
            try:
                planner_ids = {id(entry) for entry in planner_calls}
            except Exception:
                planner_ids = set()
        queue.extend(
            self._normalize_safe_function_entries(
                event_output.get("safe_functions"),
                source="event_agent",
                planner_ids=planner_ids,
            )
        )
        try:
            queue.extend(
                self._normalize_safe_function_entries(
                    world_output.get("safe_functions"),
                    source="world_agent",
                )
            )
        except Exception:
            pass
        for reaction in character_output:
            if not isinstance(reaction, dict):
                continue
            reaction_name = reaction.get("name", "unknown")
            if isinstance(reaction_name, str) and reaction_name.strip():
                source_label = f"character:{reaction_name.strip()}"
            else:
                source_label = "character:unknown"
            queue.extend(
                self._normalize_safe_function_entries(
                    reaction.get("safe_functions"),
                    source=source_label,
                )
            )
            try:
                state = self._orchestrator.state_store.snapshot()
                prev_world = state.get("world_constraint_from_prev_turn", {}) or {}
                prev_atmo = (prev_world.get("atmosphere") or "").strip()
                current_turn = int(state.get("turn", 0))
                last_weather_turn = int(
                    state.get("last_weather_change_turn", -9999) or -9999
                )
                filtered: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
                for payload, metadata in queue:
                    try:
                        if payload.get("name") == "change_weather":
                            kw = payload.get("kwargs", {}) or {}
                            new_atmo = (kw.get("atmosphere") or "").strip()
                            if (
                                new_atmo
                                and new_atmo.lower() == (prev_atmo or "").lower()
                            ) or (current_turn - last_weather_turn <= 4):
                                continue
                    except Exception:
                        pass
                    filtered.append((payload, metadata))
                queue = filtered
            except Exception:
                pass
        return queue

    def _normalize_safe_function_entries(
        self,
        entries: Any,
        *,
        source: str,
        planner_ids: Optional[Set[int]] = None,
    ) -> List[Tuple[Dict[str, Any], Dict[str, Any]]]:
        if not isinstance(entries, list):
            return []
        normalized: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
        for entry in entries:
            is_planner_origin = bool(planner_ids and id(entry) in planner_ids)
            if isinstance(entry, str):
                try:
                    node = ast.parse(entry, mode="eval").body
                    if not isinstance(node, ast.Call) or not isinstance(
                        node.func, ast.Name
                    ):
                        LOGGER.warning(
                            "Skipping invalid safe function expression: %r",
                            entry,
                        )
                        continue
                    func_name = node.func.id
                    args = [ast.literal_eval(arg) for arg in node.args]
                    kwargs = {
                        kw.arg: ast.literal_eval(kw.value)
                        for kw in node.keywords
                        if kw.arg is not None
                    }
                    payload: Dict[str, Any] = {"name": func_name}
                    normalized_kwargs = self._normalize_safe_function_kwargs(
                        func_name,
                        args,
                        kwargs,
                    )
                    if normalized_kwargs:
                        payload["kwargs"] = normalized_kwargs
                    remaining_args = [value for value in args if value is not None]
                    if remaining_args and func_name not in {
                        "change_weather",
                        "spawn_item",
                        "move_npc",
                    }:
                        payload["args"] = remaining_args
                    metadata: Dict[str, Any] = {"source": source}
                    if is_planner_origin:
                        metadata["planner_origin"] = True
                    normalized.append((payload, metadata))
                except Exception as exc:
                    LOGGER.warning(
                        "Skipping unparsable safe function call '%s': %s",
                        entry,
                        exc,
                    )
                    continue
            elif isinstance(entry, dict):
                raw_name = entry.get("name")
                if not isinstance(raw_name, str) or not raw_name.strip():
                    continue
                payload = {"name": raw_name.strip()}
                if "args" in entry:
                    payload["args"] = entry.get("args")
                if "kwargs" in entry:
                    payload["kwargs"] = entry.get("kwargs")
                entry_metadata = entry.get("metadata")
                payload_metadata: Dict[str, Any] = {}
                if isinstance(entry_metadata, dict):
                    payload_metadata = dict(entry_metadata)
                    payload["metadata"] = payload_metadata
                metadata = {"source": source}
                metadata.update(payload_metadata)
                if is_planner_origin:
                    metadata["planner_origin"] = True
                normalized.append((payload, metadata))
            elif isinstance(entry, FunctionCall):
                payload = {"name": entry.name, "args": entry.args, "kwargs": entry.kwargs}
                metadata = {"source": source}
                if is_planner_origin:
                    metadata["planner_origin"] = True
                normalized.append((payload, metadata))
            else:
                continue
        return normalized

    @staticmethod
    def _normalize_safe_function_kwargs(
        name: str,
        args: List[Any],
        kwargs: Dict[str, Any],
    ) -> Dict[str, Any]:
        def _as_text(value: Any) -> str:
            text = str(value) if value is not None else ""
            return text.strip()

        if name == "change_weather":
            atmosphere = kwargs.get("atmosphere")
            details = kwargs.get("sensory_details")
            if args:
                atmosphere = args[0]
                if len(args) > 1:
                    details = args[1]
            atmosphere_text = _as_text(atmosphere)
            if not atmosphere_text:
                raise ValueError("change_weather requires an atmosphere")
            details_text = _as_text(details) or "The weather shifts subtly."
            return {
                "atmosphere": atmosphere_text,
                "sensory_details": details_text,
            }

        if name == "spawn_item":
            item_id = kwargs.get("item_id")
            target = kwargs.get("target")
            if args:
                if len(args) > 0:
                    item_id = args[0]
                if len(args) > 1:
                    target = args[1]
            item_text = _as_text(item_id)
            target_text = _as_text(target)
            if not item_text or not target_text:
                raise ValueError("spawn_item requires item_id and target")
            return {
                "item_id": item_text,
                "target": target_text,
            }

        if name == "move_npc":
            npc_id = kwargs.get("npc_id") or kwargs.get("npc_name")
            location = kwargs.get("location") or kwargs.get("target")
            if args:
                if len(args) > 0:
                    npc_id = args[0]
                if len(args) > 1:
                    location = args[1]
            npc_text = _as_text(npc_id)
            location_text = _as_text(location)
            if not npc_text or not location_text:
                raise ValueError("move_npc requires npc identifier and location")
            return {
                "npc_id": npc_text,
                "location": location_text,
            }

        cleaned = {
            key: value for key, value in kwargs.items() if key and value is not None
        }
        return cleaned

    def _apply_safe_function_guardrails(
        self,
        calls: List[Tuple[Dict[str, Any], Dict[str, Any]]],
    ) -> Tuple[List[Tuple[Dict[str, Any], Dict[str, Any]]], Dict[str, Any]]:
        if not calls:
            return [], {
                "planner_lowered_wall_integrity": False,
                "world_wall_integrity_skipped": 0,
                "objective_urgency_skipped": [],
                "stockpile_collapsed": [],
            }

        planner_lowered_wall = False
        for payload, metadata in calls:
            if str(payload.get("name", "")) != "adjust_metric":
                continue
            kwargs = payload.get("kwargs") or {}
            metric = str(kwargs.get("metric", "")).strip().lower()
            if metric != "wall_integrity":
                continue
            delta_raw = kwargs.get("delta", 0)
            try:
                delta_val = float(delta_raw)
            except (TypeError, ValueError):
                continue
            if delta_val < 0 and metadata.get("planner_origin"):
                planner_lowered_wall = True
                break

        stats = {
            "planner_lowered_wall_integrity": planner_lowered_wall,
            "world_wall_integrity_skipped": 0,
            "objective_urgency_skipped": [],
            "stockpile_collapsed": set(),
        }
        filtered: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
        adjust_stockpile_sources: Dict[str, str] = {}
        objective_urgency_adjusted = False

        for payload, metadata in calls:
            name = str(payload.get("name", "")).strip()
            kwargs = payload.get("kwargs") or {}
            source = str(metadata.get("source", "unknown"))

            if (
                planner_lowered_wall
                and source == "world_agent"
                and name == "adjust_metric"
            ):
                metric = str(kwargs.get("metric", "")).strip().lower()
                if metric == "wall_integrity":
                    delta_raw = kwargs.get("delta", 0)
                    try:
                        delta_val = float(delta_raw)
                    except (TypeError, ValueError):
                        delta_val = 0
                    if delta_val < 0:
                        LOGGER.info(
                            "Skipping world_agent wall_integrity reduction; planner already applied one this turn.",
                        )
                        stats["world_wall_integrity_skipped"] += 1
                        continue

            if name == "adjust_stockpile":
                resource_id = kwargs.get("resource_id")
                resource_key = str(resource_id or "__unknown__").strip().lower()
                previous_source = adjust_stockpile_sources.get(resource_key)
                if previous_source is None:
                    adjust_stockpile_sources[resource_key] = source
                elif previous_source != source:
                    LOGGER.info(
                        "Collapsing duplicate adjust_stockpile on '%s' from '%s'; '%s' already adjusted this turn.",
                        resource_key,
                        source,
                        previous_source,
                    )
                    stats["stockpile_collapsed"].add(resource_key)
                    continue

            if name == "adjust_metric":
                metric = str(kwargs.get("metric", "")).strip().lower()
                if metric == "objective_urgency" and source.startswith("character:"):
                    if objective_urgency_adjusted:
                        LOGGER.info(
                            "Skipping additional objective_urgency adjustment from %s; already applied this turn.",
                            source,
                        )
                        stats["objective_urgency_skipped"].append(source)
                        continue
                    objective_urgency_adjusted = True

            filtered.append((payload, metadata))

        stats["stockpile_collapsed"] = sorted(stats["stockpile_collapsed"])
        stats["objective_urgency_skipped"] = sorted(
            set(stats["objective_urgency_skipped"])
        )

        return filtered, stats

    def _summarize_safe_function_call(self, payload: Dict[str, Any]) -> str:
        name = str(payload.get("name", "unknown"))
        kwargs = payload.get("kwargs") or {}
        if not isinstance(kwargs, dict):
            kwargs = {}
        interesting_keys = ("npc_id", "room", "metric", "delta", "resource_id", "amount")
        parts = []
        for key in interesting_keys:
            if key in kwargs:
                parts.append(f"{key}={kwargs[key]}")
        arg_summary = ", ".join(parts)
        if arg_summary:
            return f"{name}({arg_summary})"
        return name
