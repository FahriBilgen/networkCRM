"""Planner agent responsible for building prompts and validating plans."""

from __future__ import annotations

import json
import logging
from copy import deepcopy
from typing import Any, Dict, Iterable, List, Sequence

from jsonschema import Draft7Validator, ValidationError

from fortress_director.core.cluster_manager import ClusterManager
from fortress_director.core.function_registry import (
    SafeFunctionMeta,
    SafeFunctionRegistry,
)
from fortress_director.core.state_archive import (
    StateArchive,
    inject_archive_to_prompt,
)
from fortress_director.core.state_store import GameState
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
from fortress_director.settings import SETTINGS

LOGGER = logging.getLogger(__name__)

MAX_PLAN_CALLS = 3
MAX_PLAN_GAS = 3
RAW_LOG_CHAR_LIMIT = 600
ERROR_LOG_CHAR_LIMIT = 200
PLANNER_GENERATION_OVERRIDES = {
    "temperature": 0.4,
    "top_p": 0.5,
    "top_k": 20,
    "num_predict": 192,
    "num_ctx": 4096,
}

PLANNER_PLAN_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["gas", "calls"],
    "properties": {
        "gas": {"type": "integer", "minimum": 1, "maximum": MAX_PLAN_GAS},
        "calls": {
            "type": "array",
            "minItems": 1,
            "maxItems": MAX_PLAN_CALLS,
            "items": {
                "type": "object",
                "required": ["name"],
                "properties": {
                    "name": {"type": "string", "minLength": 1},
                    "kwargs": {"type": "object"},
                    "args": {"type": "array"},
                    "metadata": {"type": "object"},
                },
                "additionalProperties": False,
            },
        },
    },
    "additionalProperties": False,
}

FEW_SHOT_EXAMPLES: List[Dict[str, Any]] = [
    {
        "description": "Reinforce the wall during a storm alert",
        "payload": {
            "gas": 1,
            "calls": [
                {
                    "name": "reinforce_wall",
                    "kwargs": {"structure_id": "western_wall", "amount": 2},
                },
                {
                    "name": "spawn_event_marker",
                    "kwargs": {
                        "marker_id": "storm_watch",
                        "x": 6,
                        "y": 1,
                        "severity": 2,
                    },
                },
            ],
        },
    },
    {
        "description": "Scout for intel and tighten order",
        "payload": {
            "gas": 1,
            "calls": [
                {
                    "name": "send_on_patrol",
                    "kwargs": {"npc_id": "rhea", "duration": 2},
                },
                {
                    "name": "adjust_metric",
                    "kwargs": {
                        "metric": "order",
                        "delta": 1,
                        "cause": "patrol_visibility",
                    },
                },
            ],
        },
    },
    {
        "description": "Stabilize food usage via rationing",
        "payload": {
            "gas": 1,
            "calls": [
                {
                    "name": "allocate_food",
                    "kwargs": {"amount": 4, "target": "barracks"},
                },
                {
                    "name": "log_message",
                    "kwargs": {"message": "Food sent to barracks."},
                },
            ],
        },
    },
]

PLAN_FORMAT_EXAMPLE = {
    "gas": 2,
    "calls": [
        {
            "name": "reinforce_wall",
            "kwargs": {"structure_id": "western_wall", "amount": 2},
        },
        {
            "name": "set_flag",
            "kwargs": {"flag": "planner_reserve"},
        },
    ],
}


class PlannerAgent:
    """Planner that emits JSON-friendly safe function plans."""

    def __init__(
        self,
        *,
        function_registry: SafeFunctionRegistry | None = None,
        cluster_manager: ClusterManager | None = None,
        llm_client: OllamaClient | None = None,
        model_key: str = "planner",
        use_llm: bool = True,
    ) -> None:
        self._function_registry = function_registry or SafeFunctionRegistry()
        metadata_seed = list(self._function_registry.list_metadata())
        self._active_function_metadata: List[SafeFunctionMeta] = metadata_seed
        self._active_metadata_by_name = {meta.name: meta for meta in metadata_seed}
        self._cluster_manager = cluster_manager or ClusterManager(metadata_seed)
        self._schema_validator = Draft7Validator(PLANNER_PLAN_SCHEMA)
        self._last_projection: Dict[str, Any] | None = None
        self._model_registry = get_registry()
        self._agent_key = model_key
        try:
            self._model_config = self._model_registry.get(model_key)
        except KeyError:
            LOGGER.warning("Unknown planner model key %s; using default.", model_key)
            self._agent_key = "planner"
            self._model_config = self._model_registry.get(self._agent_key)
        client = llm_client or (OllamaClient() if use_llm else None)
        self._llm_client: OllamaClient | None = client
        self._llm_enabled = use_llm and self._llm_client is not None
        self._fallback_builders = {
            "adjust_metric": self._fallback_adjust_metric,
            "reinforce_wall": self._fallback_reinforce_wall,
            "move_npc": self._fallback_move_npc,
            "send_on_patrol": self._fallback_send_on_patrol,
            "spawn_event_marker": self._fallback_spawn_event_marker,
        }
        runtime_config = SETTINGS.llm_runtime
        self._cache_enabled = bool(runtime_config.enable_cache)
        self._metrics_enabled = bool(runtime_config.log_metrics)
        self._llm_timeout = float(runtime_config.timeout_seconds)
        self._llm_max_retries = int(runtime_config.max_retries)
        self._llm_cache: LLMCache = get_default_cache()

    def set_theme_metadata(
        self,
        metadata: Dict[str, SafeFunctionMeta] | None,
    ) -> None:
        """Update active function metadata using theme overrides."""

        if metadata:
            values = list(metadata.values())
        else:
            values = list(self._function_registry.list_metadata())
        self._active_function_metadata = values
        self._active_metadata_by_name = {meta.name: meta for meta in values}
        self._cluster_manager = ClusterManager(values)

    def plan_actions(
        self,
        projected_state: Dict[str, Any],
        scene_intent: Dict[str, Any],
        player_action_context: Dict[str, Any] | None = None,
        *,
        max_calls: int | None = None,
        archive: StateArchive | None = None,
        turn_number: int = 0,
    ) -> Dict[str, Any]:
        """Return validated planner actions for downstream execution."""

        call_limit = max_calls if max_calls is not None else MAX_PLAN_CALLS
        prompt = self.build_prompt(
            projected_state,
            scene_intent,
            call_limit=call_limit,
            player_action_context=player_action_context,
            archive=archive,
            turn_number=turn_number,
        )
        if self._llm_enabled and is_llm_enabled():
            try:
                raw_response = self._call_llm(prompt)
                validated_plan = self.validate_llm_output(raw_response)
            except (
                OllamaClientError,
                ValidationError,
                json.JSONDecodeError,
                ValueError,
                TimeoutError,
                RuntimeError,
            ) as exc:
                LOGGER.warning("Planner LLM fallback triggered: %s", exc)
                validated_plan = self.validate_llm_output(
                    self._build_fallback_plan(projected_state, scene_intent),
                )
        else:
            validated_plan = self.validate_llm_output(
                self._build_fallback_plan(projected_state, scene_intent),
            )
        validated_plan = self._enforce_required_calls(
            validated_plan, player_action_context
        )
        validated_plan = self._apply_call_limit(validated_plan, call_limit)
        actions = [
            {
                "function": call["name"],
                "args": dict(call.get("kwargs", {})),
            }
            for call in validated_plan["calls"]
        ]
        self._last_projection = deepcopy(projected_state)
        return {
            "prompt": prompt,
            "raw_plan": validated_plan,
            "planned_actions": actions,
        }

    def build_prompt(
        self,
        projected_state: Dict[str, Any],
        scene_intent: Dict[str, Any],
        *,
        max_functions: int = 12,
        call_limit: int | None = None,
        player_action_context: Dict[str, Any] | None = None,
        archive: StateArchive | None = None,
        turn_number: int = 0,
    ) -> str:
        """Compose a function-calling prompt given context + metadata."""
        relevant = self._cluster_manager.get_relevant_functions(
            projected_state, max_count=max_functions
        )
        if not relevant:
            metadata = list(self._active_function_metadata)
            relevant = metadata[:max_functions]

        state_delta = GameState.compute_state_delta(
            self._last_projection, projected_state
        )

        projected_state_json = json.dumps(projected_state, ensure_ascii=False)
        state_delta_json = json.dumps(state_delta, ensure_ascii=False)
        scene_intent_json = json.dumps(scene_intent, ensure_ascii=False)

        limit_text = call_limit or MAX_PLAN_CALLS
        prompt_sections = [
            "You are a deterministic planner focused on safe function calls.",
            "Respond with JSON that satisfies PLAN_FORMAT. Hard JSON rules:",
            f"- Max {limit_text} calls; no $schema fields; JSON only; no explanations.",
            f"Sadece JSON döndür; açıklama yazma; en fazla {limit_text} fonksiyon çağır.",
            "CRITICAL CONSTRAINTS:",
            f"- Max {limit_text} calls in the calls array.",
            "- No $schema field anywhere in your response.",
            "- Only JSON output. No markdown, no code fences.",
            "PLANNING RULES:",
            f"1) Aşağıdaki kategorilerden en fazla {limit_text} fonksiyon çağır.",
            "2) Sadece AVAILABLE_FUNCTIONS'teki isimleri kullan.",
            "3) NPC pozisyonu, duvar ve tehdit durumuna göre parametre seç.",
            "PROJECTED_STATE:",
            projected_state_json,
            "STATE_DELTA:",
            state_delta_json,
            "SCENE_INTENT:",
            scene_intent_json,
        ]
        if player_action_context:
            required_calls = player_action_context.get("required_calls") or []
            prompt_sections.extend(
                [
                    "THE PLAYER HAS SELECTED THE FOLLOWING ACTION:",
                    player_action_context.get("player_intent") or "",
                    "INCLUDE THE FOLLOWING CALLS:",
                    json.dumps(required_calls, ensure_ascii=False),
                    "DO NOT OMIT THESE CALLS.",
                ]
            )
        if relevant:
            prompt_sections.extend(
                [
                    "RECOMMENDED_FUNCTIONS:",
                    self._format_function_docs(relevant[:5]),
                ]
            )
        available_functions_doc = self._format_function_docs(
            self._active_function_metadata
        )
        prompt_sections.extend(
            [
                "AVAILABLE_FUNCTIONS:",
                available_functions_doc,
                "FEW-SHOT EXAMPLES:",
                self._format_examples(),
                "PLAN_FORMAT:",
                json.dumps(PLAN_FORMAT_EXAMPLE, ensure_ascii=False),
                (
                    "Important: Only output an object shaped like PLAN_FORMAT."
                    " Do not restate PLAN_FORMAT or mention schema fragments."
                ),
            ]
        )
        prompt = "\n".join(prompt_sections)
        # Inject archive context if available
        if archive is not None and turn_number > 0:
            prompt = inject_archive_to_prompt(archive, turn_number, prompt)
        return prompt

    def _call_llm(self, prompt: str) -> str:
        assert self._llm_client is not None  # guarded by _llm_enabled
        options = self._model_registry.build_generation_options(
            self._agent_key,
            overrides=PLANNER_GENERATION_OVERRIDES,
        )
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
                raise TimeoutError("Planner LLM call timed out.")
            raise RuntimeError(
                f"Planner LLM call failed ({metrics.error_type or 'UnknownError'})"
            )
        raw = response.get("response")
        if not raw:
            raw = response.get("message", {}).get("content")
        if not raw:
            raise ValueError("Planner LLM returned an empty response.")
        raw_str = str(raw)
        if cache_key and self._cache_enabled:
            self._llm_cache.set(cache_key, raw_str)
        LOGGER.debug(
            "planner_llm_raw_response (len=%d): %s",
            len(raw_str),
            raw_str[:500] if len(raw_str) > 500 else raw_str,
        )
        return raw_str

    def validate_llm_output(
        self,
        payload: str | Dict[str, Any],
    ) -> Dict[str, Any]:
        """Validate arbitrary planner output against the schema."""

        serialized = self._serialize_for_log(payload)
        debug_preview = self._truncate_for_log(serialized, RAW_LOG_CHAR_LIMIT)
        LOGGER.debug(
            "planner_validate_input (type=%s, len=%d)",
            type(payload).__name__,
            len(serialized),
        )
        LOGGER.debug("preview: %s", debug_preview)
        error_preview = self._truncate_for_log(serialized, ERROR_LOG_CHAR_LIMIT)
        try:
            raw_candidate = self._coerce_payload_to_mapping(payload)
        except json.JSONDecodeError as exc:
            LOGGER.error(
                "planner_invalid_json (line=%s, col=%s, msg=%s): %s",
                exc.lineno,
                exc.colno,
                exc.msg,
                error_preview,
            )
            raise

        if self._contains_schema_key(raw_candidate):
            LOGGER.error(
                "planner_invalid_schema_output (rejected $schema field): %s",
                error_preview,
            )
            raise ValueError("Planner response echoed forbidden $schema field.")

        calls_payload = raw_candidate.get("calls")
        if not isinstance(calls_payload, list) or not calls_payload:
            raise ValueError("Planner response must include at least one call.")
        for idx, call in enumerate(calls_payload):
            if not isinstance(call, dict):
                raise ValueError(f"Planner call #{idx + 1} is not an object.")

        gas_value = raw_candidate.get("gas")
        if isinstance(gas_value, (int, float)):
            gas = max(1, min(MAX_PLAN_GAS, int(gas_value)))
        else:
            gas = max(1, min(MAX_PLAN_GAS, len(calls_payload)))
            LOGGER.info("planner_gas_inferred call_count=%s", len(calls_payload))

        candidate = {"gas": gas, "calls": calls_payload}
        try:
            self._schema_validator.validate(candidate)
        except ValidationError as exc:
            LOGGER.error(
                "planner_schema_validation_error (path=%s, message=%s)",
                list(exc.path) if exc.path else "root",
                exc.message,
            )
            LOGGER.debug("schema preview: %s", error_preview)
            raise

        normalized_calls = [
            {
                "name": call["name"],
                "kwargs": dict(call.get("kwargs", {})),
            }
            for call in calls_payload
        ]
        for call in normalized_calls:
            meta = self._active_metadata_by_name.get(call["name"])
            if meta is None:
                raise ValueError(f"Unknown safe function requested: {call['name']}")
            self._validate_registry_params(meta, call["kwargs"])
        return {
            "gas": gas,
            "calls": normalized_calls,
        }

    def _serialize_for_log(self, payload: str | Dict[str, Any]) -> str:
        if isinstance(payload, str):
            return payload.strip()
        try:
            return json.dumps(payload, ensure_ascii=False)
        except TypeError:
            return str(payload)

    def _truncate_for_log(self, payload: str, limit: int) -> str:
        clean = payload.replace("\n", " ").strip()
        if len(clean) <= limit:
            return clean
        return f"{clean[:limit]}..."

    def _coerce_payload_to_mapping(
        self, payload: str | Dict[str, Any]
    ) -> Dict[str, Any]:
        if isinstance(payload, dict):
            candidate = dict(payload)
        else:
            cleaned = payload.strip()
            try:
                candidate = json.loads(cleaned)
                # Handle double-encoded JSON strings (e.g. '"{...}"')
                if isinstance(candidate, str):
                    candidate = json.loads(candidate)
            except json.JSONDecodeError:
                sanitized = cleaned.replace("'", '"')
                if sanitized != cleaned:
                    try:
                        candidate = json.loads(sanitized)
                        if isinstance(candidate, str):
                            candidate = json.loads(candidate)
                    except json.JSONDecodeError:
                        raise
                else:
                    raise
        if not isinstance(candidate, dict):
            raise ValueError("Planner response must be a JSON object.")
        return candidate

    def _contains_schema_key(self, payload: Any) -> bool:
        if isinstance(payload, dict):
            for key, value in payload.items():
                if str(key).strip() == "$schema":
                    return True
                if self._contains_schema_key(value):
                    return True
        elif isinstance(payload, list):
            for item in payload:
                if self._contains_schema_key(item):
                    return True
        return False

    def _build_fallback_plan(
        self,
        projected_state: Dict[str, Any],
        scene_intent: Dict[str, Any],
    ) -> Dict[str, Any]:
        relevant = self._cluster_manager.get_relevant_functions(
            projected_state,
            max_count=6,
        )
        chosen = self._pick_supported_function(relevant)
        builder = self._fallback_builders[chosen]
        primary_call = {
            "name": chosen,
            "kwargs": builder(projected_state, scene_intent),
        }
        lock_flag_base = scene_intent.get("player_choice") or "auto_lock"
        lock_flag = f"planner_lock_{lock_flag_base}"
        lock_call = {
            "name": "set_flag",
            "kwargs": {"flag": lock_flag},
        }
        calls = [primary_call, lock_call]
        return {
            "gas": max(1, len(calls)),
            "calls": calls,
        }

    def _enforce_required_calls(
        self,
        validated_plan: Dict[str, Any],
        player_action_context: Dict[str, Any] | None,
    ) -> Dict[str, Any]:
        if not player_action_context:
            return validated_plan
        _raw_calls = validated_plan.get("calls", [])
        calls = list(_raw_calls)
        required_calls = player_action_context.get("required_calls") or []
        for required in required_calls:
            fn_name = required.get("function")
            _raw_args = required.get("args", {})
            args = dict(_raw_args)
            found = False
            for existing in calls:
                if self._calls_match(existing, fn_name, args):
                    found = True
                    break
            if not found:
                calls.append({"name": fn_name, "kwargs": args})
        validated_plan["calls"] = calls
        _gas_base = int(validated_plan.get("gas") or 0)
        validated_plan["gas"] = max(_gas_base, len(calls))
        return validated_plan

    @staticmethod
    def _apply_call_limit(
        validated_plan: Dict[str, Any],
        limit: int,
    ) -> Dict[str, Any]:
        if limit <= 0:
            return validated_plan
        calls = list(validated_plan.get("calls") or [])
        trimmed = calls[:limit]
        if len(trimmed) != len(calls):
            validated_plan["calls"] = trimmed
        current_gas = int(validated_plan.get("gas") or 0)
        validated_plan["gas"] = max(len(trimmed), min(current_gas, limit))
        return validated_plan

    @staticmethod
    def _calls_match(
        candidate: Dict[str, Any], fn_name: str, args: Dict[str, Any]
    ) -> bool:
        if not isinstance(candidate, dict):
            return False
        if candidate.get("name") != fn_name:
            return False
        kwargs = candidate.get("kwargs")
        if not isinstance(kwargs, dict):
            return False
        return kwargs == args

    def _pick_supported_function(
        self,
        candidates: Sequence[SafeFunctionMeta],
    ) -> str:
        for meta in candidates:
            if meta.name in self._fallback_builders:
                return meta.name
        return "adjust_metric"

    def _fallback_adjust_metric(
        self,
        projected_state: Dict[str, Any],
        scene_intent: Dict[str, Any],
    ) -> Dict[str, Any]:
        focus = str(scene_intent.get("focus", "explore")).lower()
        metric = "order" if focus in {"stabilize", "defend"} else "knowledge"
        delta = 2 if metric == "order" else 1
        return {"metric": metric, "delta": delta, "cause": f"planner:{focus}"}

    def _fallback_reinforce_wall(
        self,
        projected_state: Dict[str, Any],
        scene_intent: Dict[str, Any],
    ) -> Dict[str, Any]:
        structure = self._infer_focus_room(projected_state) or "western_wall"
        amount = 2 if scene_intent.get("focus") == "stabilize" else 1
        return {"structure_id": structure, "amount": amount}

    def _fallback_move_npc(
        self,
        projected_state: Dict[str, Any],
        scene_intent: Dict[str, Any],
    ) -> Dict[str, Any]:
        npc_id = self._primary_npc_id(projected_state)
        destination = self._infer_focus_room(projected_state) or "courtyard"
        if scene_intent.get("focus") == "stabilize":
            destination = "battlements"
        coords = {
            "courtyard": (4, 4),
            "battlements": (6, 1),
            "gate": (5, 5),
        }.get(destination, (3, 3))
        return {
            "npc_id": npc_id,
            "x": coords[0],
            "y": coords[1],
            "room": destination,
        }

    def _fallback_send_on_patrol(
        self,
        projected_state: Dict[str, Any],
        _: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {"npc_id": self._primary_npc_id(projected_state), "duration": 2}

    def _fallback_spawn_event_marker(
        self,
        projected_state: Dict[str, Any],
        scene_intent: Dict[str, Any],
    ) -> Dict[str, Any]:
        turn_index = int(projected_state.get("turn", 0))
        _summary = scene_intent.get("summary")
        if _summary:
            summary = _summary
        else:
            summary = f"Turn {turn_index} directive."
        return {
            "marker_id": f"planner_marker_{turn_index}",
            "x": 2 + (turn_index % 3),
            "y": 2 + (turn_index % 2),
            "severity": 1,
            "description": summary[:160],
        }

    def _validate_registry_params(
        self,
        meta: SafeFunctionMeta,
        kwargs: Dict[str, Any],
    ) -> None:
        required = {param.name for param in meta.params if param.required}
        optional = {param.name for param in meta.params if not param.required}
        missing = [field for field in required if field not in kwargs]
        if missing:
            missing_s = ", ".join(sorted(missing))
            raise ValueError(f"{meta.name} missing parameter(s): {missing_s}")
        allowed = required | optional
        extras = [field for field in kwargs if field not in allowed]
        if extras:
            extras_s = ", ".join(sorted(extras))
            raise ValueError(
                f"{meta.name} received unexpected parameter(s): {extras_s}"
            )
        for param in meta.params:
            if param.name not in kwargs:
                continue
            if not self._param_type_matches(param.type, kwargs[param.name]):
                received_type = type(kwargs[param.name]).__name__
                left = f"{meta.name}.{param.name} expects {param.type}"
                right = f"got {received_type}"
                raise ValueError(left + " " + right)

    def _param_type_matches(self, declared: str, value: Any) -> bool:
        if declared in {"int", "integer"}:
            return isinstance(value, (int, float))
        if declared == "float":
            return isinstance(value, (int, float))
        if declared in {"str", "string", "npc_id"}:
            return isinstance(value, str) and value.strip() != ""
        if declared == "coord":
            if isinstance(value, dict):
                return "x" in value and "y" in value
            if isinstance(value, (list, tuple)) and len(value) >= 2:
                return True
            return False
        return True

    def _infer_focus_room(self, projected_state: Dict[str, Any]) -> str | None:
        for npc in projected_state.get("npc_focus", []):
            room = npc.get("room")
            if room:
                return str(room)
        return projected_state.get("world", {}).get("current_room")

    def _primary_npc_id(self, projected_state: Dict[str, Any]) -> str:
        for npc in projected_state.get("npc_focus", []):
            identifier = npc.get("id") or npc.get("name")
            if identifier:
                return str(identifier)
        return "rhea"

    def _format_function_docs(
        self,
        metadata: Iterable[SafeFunctionMeta],
    ) -> str:
        lines = []

        def _meta_sort(entry: SafeFunctionMeta):
            return (entry.category, entry.name)

        for meta in sorted(metadata, key=_meta_sort):
            signature = meta.signature()
            parts = [
                f"- {signature}",
                f"[{meta.category} | gas {meta.gas_cost}]",
                meta.description,
            ]
            lines.append(" ".join(parts))
        return "\n".join(lines)

    def _format_examples(self) -> str:
        lines = []
        for idx, example in enumerate(FEW_SHOT_EXAMPLES, start=1):
            lines.append(
                f"Example {idx} - {example['description']}:\n"
                f"{json.dumps(example['payload'], ensure_ascii=False)}",
            )
        return "\n".join(lines)
