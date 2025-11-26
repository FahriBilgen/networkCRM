"""FastAPI surface for the lightweight turn pipeline."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple
from uuid import uuid4

try:  # pragma: no cover - exercised in runtime environment
    from fastapi import Body, FastAPI, HTTPException, Query
except ImportError:  # pragma: no cover - fallback for minimal test env
    from fastapi_stub import Body, FastAPI, Query  # type: ignore

    if TYPE_CHECKING:  # pragma: no cover
        from fastapi import HTTPException  # type: ignore
    else:

        class HTTPException(Exception):
            def __init__(self, status_code: int, detail: str) -> None:
                super().__init__(detail)
                self.status_code = status_code


from pydantic import BaseModel, Field
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from fortress_director.runtime import load_demo_config_if_exists
from fortress_director.settings import PROJECT_ROOT, SETTINGS

from fortress_director.core import (
    player_action_catalog,
    player_action_router,
    player_action_validator,
)
from fortress_director.core.state_store import GameState
from fortress_director.llm.model_registry import get_registry
from fortress_director.llm.ollama_client import (
    OllamaClient,
    OllamaClientConfig,
    OllamaClientError,
    generate_with_timeout,
)
from fortress_director.llm.runtime_mode import get_mode, is_llm_enabled, set_llm_enabled
from fortress_director.pipeline import turn_trace
from fortress_director.pipeline.turn_manager import run_turn
from fortress_director.themes.loader import BUILTIN_THEMES, load_theme_from_file
from fortress_director.themes.schema import ThemeConfig
from fortress_director.auth.middleware import JWTMiddleware
from fortress_director.auth.jwt_handler import create_access_token
from fortress_director.db.session_store import get_session_store
from fortress_director.utils.file_lock import (
    FileLock,
    session_lock_path,
)

API_VERSION = "0.1.0"
DEFAULT_THEME_ID = "siege_default"
app = FastAPI(title="Fortress Director UI API", version=API_VERSION)

# Add JWT middleware for authentication
app.add_middleware(JWTMiddleware)

# Attempt to load demo configuration if present in repository demo_build/
try:
    demo_cfg_path = PROJECT_ROOT.parent / "demo_build" / "demo_config.yaml"
    load_demo_config_if_exists(demo_cfg_path)
except Exception:
    # Non-fatal; demo config is optional and should not prevent startup
    pass

# If a UI distribution exists under demo_build/ui_dist, serve it as static files
dist_dir = PROJECT_ROOT.parent / "demo_build" / "ui_dist"
if dist_dir.exists():
    app.mount("/static", StaticFiles(directory=str(dist_dir)), name="static")
    # Serve versioned assets at /assets for compatibility with Vite's index.html
    assets_dir = dist_dir / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")
    # Serve favicon if present
    fav = dist_dir / "favicon.ico"
    if fav.exists():

        @app.get("/favicon.ico")
        def _favicon() -> FileResponse:  # pragma: no cover - convenience route
            return FileResponse(str(fav))


@app.get("/")
def serve_ui():
    index = dist_dir / "index.html"
    if index.exists():
        return FileResponse(str(index))
    raise HTTPException(
        status_code=404, detail="UI build not found; run the demo setup first"
    )


class RunTurnRequest(BaseModel):
    choice_id: Optional[str] = Field(default=None, alias="choice_id")
    session_id: Optional[str] = Field(default=None, alias="session_id")
    theme_id: Optional[str] = Field(default=None, alias="theme_id")

    class Config:
        populate_by_name = True


class ResetSessionRequest(BaseModel):
    theme_id: Optional[str] = Field(default=None, alias="theme_id")

    class Config:
        populate_by_name = True


class UpdateLLMModeRequest(BaseModel):
    use_llm: bool = Field(alias="use_llm")

    class Config:
        populate_by_name = True


class DialogueModel(BaseModel):
    speaker: str
    line: str


class GridCellModel(BaseModel):
    id: str
    x: int
    y: int
    entity_type: str = Field(alias="entityType")
    label: Optional[str] = None
    hostile: Optional[bool] = None

    class Config:
        populate_by_name = True


class HudModel(BaseModel):
    turn: int
    order: int
    morale: int
    resources: int
    glitch: int
    food: int = 0
    avg_morale: int = Field(default=0, alias="avgMorale")
    avg_fatigue: int = Field(default=0, alias="avgFatigue")

    class Config:
        allow_population_by_field_name = True


class EventLogEntryModel(BaseModel):
    id: str
    turn: int
    text: str


class RunTurnResponseModel(BaseModel):
    narrative: str
    ui_events: List[DialogueModel]
    state_delta: Dict[str, Any]
    player_options: List[Dict[str, Any]]
    options: List[Dict[str, Any]]
    executed_actions: List[Dict[str, Any]]
    hud: HudModel
    grid: List[GridCellModel]
    event_log: List[EventLogEntryModel]
    turn_number: int
    game_over: bool
    ending_id: Optional[str] = None
    atmosphere: Optional[Dict[str, Any]] = None
    trace_file: Optional[str] = None
    session_id: str
    player_action_context: Optional[Dict[str, Any]] = None
    threat_score: float
    threat_phase: str
    event_seed: Optional[str] = None
    event_node_id: Optional[str] = None
    event_node_description: Optional[str] = None
    event_node_is_final: bool = False
    world_tick_delta: Optional[Dict[str, Any]] = None
    combat_summary: Optional[List[Dict[str, Any]]] = None
    resources: Optional[Dict[str, Any]] = None
    npc_stats: Optional[Dict[str, Any]] = Field(default=None, alias="npcStats")
    npc_positions: Dict[str, Any] = Field(default_factory=dict)
    structures: Dict[str, Any] = Field(default_factory=dict)
    event_markers: List[Dict[str, Any]] = Field(default_factory=list)
    event_node: Optional[Dict[str, Any]] = None
    threat: Optional[Dict[str, Any]] = None
    final_payload: Optional[Dict[str, Any]] = None
    theme_id: str

    class Config:
        allow_population_by_field_name = True


class ResetSessionResponseModel(BaseModel):
    session_id: str
    narrative: str
    hud: HudModel
    grid: List[GridCellModel]
    event_log: List[EventLogEntryModel]
    npc_stats: Dict[str, Any]
    npc_positions: Dict[str, Any]
    structures: Dict[str, Any]
    event_markers: List[Dict[str, Any]]
    resources: Dict[str, Any]
    theme_id: str


class ThemeSummaryModel(BaseModel):
    id: str
    label: str
    description: str


class ThemeListResponseModel(BaseModel):
    themes: List[ThemeSummaryModel]


class PlayerActionModel(BaseModel):
    id: str
    label: str
    requires: List[str]
    safe_function: str
    args_map: Dict[str, Any]


class SelectActionRequest(BaseModel):
    session_id: Optional[str] = Field(default=None, alias="session_id")
    action_id: str
    params: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        populate_by_name = True


class LoginRequest(BaseModel):
    """Request body for creating a session and getting auth token."""

    player_name: str = Field(..., min_length=1, max_length=100)
    theme_id: Optional[str] = Field(default=DEFAULT_THEME_ID)


class AuthTokenResponse(BaseModel):
    """Response with session and auth token."""

    session_id: str
    token: str
    token_type: str = "bearer"
    theme_id: str


class SelectActionResponseModel(BaseModel):
    session_id: str
    player_action_context: Dict[str, Any]


class TraceSummaryModel(BaseModel):
    turn: int
    file: str
    modified_ts: Optional[float] = None


class SessionContext:
    def __init__(self, theme: ThemeConfig, session_id: Optional[str] = None) -> None:
        self.session_id = session_id
        self.game_state = GameState.from_theme_config(theme, session_id=session_id)
        self.player_action_context: Optional[Dict[str, Any]] = None
        self.theme_id: str = theme.id


class SessionManager:
    """Simple in-memory GameState manager keyed by session id."""

    def __init__(self) -> None:
        self._sessions: Dict[str, SessionContext] = {}

    def get_or_create(
        self,
        session_id: Optional[str],
        *,
        theme_id: Optional[str] = None,
    ) -> Tuple[str, SessionContext, bool]:
        if session_id and session_id in self._sessions:
            return session_id, self._sessions[session_id], False
        resolved_theme_id = theme_id or DEFAULT_THEME_ID
        theme = _get_theme_config(resolved_theme_id)
        new_id = session_id or uuid4().hex
        context = SessionContext(theme)
        self._sessions[new_id] = context
        return new_id, context, True

    def reset(
        self, theme_id: Optional[str] = None, session_id: Optional[str] = None
    ) -> Tuple[str, SessionContext]:
        """Create a brand new session context for replay runs."""

        resolved_theme_id = theme_id or DEFAULT_THEME_ID
        theme = _get_theme_config(resolved_theme_id)
        new_id = session_id or uuid4().hex
        context = SessionContext(theme, session_id=new_id)
        self._sessions[new_id] = context
        return new_id, context


_SESSION_MANAGER = SessionManager()


@app.post("/auth/login", response_model=AuthTokenResponse)
def login(request: LoginRequest) -> AuthTokenResponse:
    """Create a new session and issue an authentication token."""
    # Generate unique session ID for this login
    session_id = uuid4().hex
    session_id, _context = _SESSION_MANAGER.reset(
        theme_id=request.theme_id, session_id=session_id
    )
    token = create_access_token(session_id)

    # Record session in database
    session_store = get_session_store()
    session_store.record_session(
        session_id,
        request.theme_id or DEFAULT_THEME_ID,
    )

    return AuthTokenResponse(
        session_id=session_id,
        token=token,
        token_type="bearer",
        theme_id=request.theme_id or DEFAULT_THEME_ID,
    )


@app.post("/api/run_turn", response_model=RunTurnResponseModel)
def run_turn_endpoint(
    payload: RunTurnRequest = Body(...),
    session_query: Optional[str] = Query(default=None, alias="session_id"),
) -> RunTurnResponseModel:
    """Trigger a single turn and expose UI-friendly payload."""

    requested_session = payload.session_id or session_query
    requested_theme_id = payload.theme_id

    # Acquire session-specific lock
    lock_path = session_lock_path(
        requested_session or "", SETTINGS.project_root / "locks"
    )
    lock = FileLock(lock_path)

    with lock:
        session_id, session, created = _SESSION_MANAGER.get_or_create(
            requested_session,
            theme_id=requested_theme_id,
        )
        if (
            not created
            and requested_theme_id
            and requested_theme_id != session.theme_id
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Session theme mismatch; "
                    "start a new session for a different theme."
                ),
            )
        theme_id = session.theme_id
        theme = _get_theme_config(theme_id)
        game_state = session.game_state
        choice_payload = {"id": payload.choice_id} if payload.choice_id else None
        player_action_context = session.player_action_context
        try:
            result = run_turn(
                game_state,
                player_choice=choice_payload,
                player_action_context=player_action_context,
                theme=theme,
            )
        except Exception as exc:  # pragma: no cover
            raise HTTPException(
                status_code=500, detail=f"Turn execution failed: {exc}"
            ) from exc
        projection = game_state.get_projected_state()
        snapshot = game_state.snapshot()
        domain_snapshot = game_state.as_domain()
        npc_stats = _compute_npc_stats(game_state)
        hud = _build_hud(projection, snapshot, npc_stats)
        grid = _build_grid(projection)
        event_log = _build_event_log(projection)
        session.player_action_context = None
        threat_snapshot = result.threat_snapshot
        if threat_snapshot:
            threat_score = float(threat_snapshot.threat_score)
            threat_phase = threat_snapshot.phase
        else:
            threat_score = 0.0
            threat_phase = "unknown"
        combat_summary = _extract_combat_summary(result.executed_actions)
    return RunTurnResponseModel(
        narrative=result.narrative,
        ui_events=result.ui_events,
        state_delta=result.state_delta,
        player_options=result.player_options,
        options=result.player_options,
        executed_actions=result.executed_actions,
        atmosphere=result.atmosphere,
        hud=hud,
        grid=grid,
        event_log=event_log,
        turn_number=result.turn_number,
        game_over=game_state.game_over,
        ending_id=game_state.ending_id,
        trace_file=result.trace_file,
        session_id=session_id,
        player_action_context=player_action_context,
        threat_score=threat_score,
        threat_phase=threat_phase,
        event_seed=result.event_seed,
        event_node_id=result.event_node_id,
        event_node_description=result.event_node_description,
        event_node_is_final=result.event_node_is_final,
        world_tick_delta=result.world_tick_delta,
        combat_summary=combat_summary,
        resources=_build_resource_snapshot(snapshot),
        npc_stats=npc_stats,
        npc_positions=domain_snapshot.npc_positions(),
        structures=domain_snapshot.structure_integrities(),
        event_markers=domain_snapshot.event_list(),
        event_node=_build_event_node(
            result.event_node_id,
            result.event_node_description,
        ),
        threat={"score": threat_score, "phase": threat_phase},
        final_payload=result.final_payload,
        theme_id=theme_id,
    )

    return RunTurnResponseModel(
        narrative=result.narrative,
        ui_events=result.ui_events,
        state_delta=result.state_delta,
        player_options=result.player_options,
        options=result.player_options,
        executed_actions=result.executed_actions,
        atmosphere=result.atmosphere,
        hud=hud,
        grid=grid,
        event_log=event_log,
        turn_number=result.turn_number,
        game_over=game_state.game_over,
        ending_id=game_state.ending_id,
        trace_file=result.trace_file,
        session_id=session_id,
        player_action_context=player_action_context,
        threat_score=threat_score,
        threat_phase=threat_phase,
        event_seed=result.event_seed,
        event_node_id=result.event_node_id,
        event_node_description=result.event_node_description,
        event_node_is_final=result.event_node_is_final,
        world_tick_delta=result.world_tick_delta,
        combat_summary=combat_summary,
        resources=_build_resource_snapshot(snapshot),
        npc_stats=npc_stats,
        npc_positions=domain_snapshot.npc_positions(),
        structures=domain_snapshot.structure_integrities(),
        event_markers=domain_snapshot.event_list(),
        event_node=_build_event_node(
            result.event_node_id,
            result.event_node_description,
        ),
        threat={"score": threat_score, "phase": threat_phase},
        final_payload=result.final_payload,
        theme_id=theme_id,
    )


@app.get("/api/themes", response_model=ThemeListResponseModel)
def list_themes() -> ThemeListResponseModel:
    """Return the available theme packages."""

    catalog = _get_theme_catalog()
    summaries = [
        ThemeSummaryModel(
            id=theme.id,
            label=theme.label,
            description=theme.description,
        )
        for theme in sorted(catalog.values(), key=lambda entry: entry.id)
    ]
    return ThemeListResponseModel(themes=summaries)


@app.post("/api/reset_for_new_run", response_model=ResetSessionResponseModel)
def reset_for_new_run(
    payload: ResetSessionRequest | None = None,
) -> ResetSessionResponseModel:
    """Create a fresh GameState/session for replay runs."""

    theme_id = payload.theme_id if payload else None
    session_id, session = _SESSION_MANAGER.reset(theme_id=theme_id)
    game_state = session.game_state
    projection = game_state.get_projected_state()
    snapshot = game_state.snapshot()
    domain_snapshot = game_state.as_domain()
    npc_stats = _compute_npc_stats(game_state)
    hud = _build_hud(projection, snapshot, npc_stats)
    grid = _build_grid(projection)
    event_log = _build_event_log(projection)
    resources = _build_resource_snapshot(snapshot)
    return ResetSessionResponseModel(
        session_id=session_id,
        narrative="Session reset. A new siege takes shape.",
        hud=hud,
        grid=grid,
        event_log=event_log,
        npc_stats=npc_stats,
        npc_positions=domain_snapshot.npc_positions(),
        structures=domain_snapshot.structure_integrities(),
        event_markers=domain_snapshot.event_list(),
        resources=resources,
        theme_id=session.theme_id,
    )


def _build_hud(
    projection: Dict[str, Any],
    snapshot: Dict[str, Any],
    npc_stats: Dict[str, float],
) -> HudModel:
    metrics = projection.get("metrics") or {}
    stockpiles = snapshot.get("stockpiles") or {}
    return HudModel(
        turn=int(projection.get("turn", 0)),
        order=int(metrics.get("order") or 0),
        morale=int(metrics.get("morale") or 0),
        resources=int(
            metrics.get("resources")
            or projection.get("world", {}).get("resources", 0)
            or 0
        ),
        glitch=int(metrics.get("glitch") or 0),
        food=int(stockpiles.get("food") or 0),
        avg_morale=int(round(npc_stats.get("avg_morale", 0))),
        avg_fatigue=int(round(npc_stats.get("avg_fatigue", 0))),
    )


def _build_grid(projection: Dict[str, Any]) -> List[GridCellModel]:
    grid_cells: List[GridCellModel] = []
    for cell in projection.get("nearby_grid", []):
        try:
            raw_entity = cell.get("entity_type")
            if raw_entity:
                entity_type = str(raw_entity)
            else:
                entity_type = "npc" if cell.get("hostile") else "marker"

            id_val = cell.get("id") or f"{cell.get('x')}_{cell.get('y')}"

            grid_cells.append(
                GridCellModel(
                    id=str(id_val),
                    x=int(cell.get("x") or 0),
                    y=int(cell.get("y") or 0),
                    entityType=entity_type,
                    label=cell.get("room"),
                    hostile=bool(cell.get("hostile")),
                )
            )
        except (TypeError, ValueError):
            continue
    return grid_cells


def _build_event_log(projection: Dict[str, Any]) -> List[EventLogEntryModel]:
    turn = int(projection.get("turn", 0))
    entries: List[EventLogEntryModel] = []
    for idx, text in enumerate(projection.get("recent_events") or []):
        if not text:
            continue
        entries.append(
            EventLogEntryModel(
                id=f"{turn}-{idx}",
                turn=turn,
                text=str(text),
            ),
        )
    return entries


def _build_resource_snapshot(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    stockpiles = snapshot.get("stockpiles") or {}
    world = snapshot.get("world") or {}
    return {
        "food": int(stockpiles.get("food") or 0),
        "world_resources": int(world.get("resources") or 0),
    }


def _build_event_node(
    node_id: Optional[str], description: Optional[str]
) -> Optional[Dict[str, str]]:
    if not node_id and not description:
        return None
    return {
        "id": node_id or "unknown",
        "description": description or "",
    }


def _compute_npc_stats(game_state: GameState) -> Dict[str, float]:
    domain = game_state.as_domain()
    npcs = list(domain.npcs.values())
    if not npcs:
        return {"avg_morale": 0.0, "avg_fatigue": 0.0}
    morale_total = sum(max(0, min(100, npc.morale)) for npc in npcs)
    fatigue_total = sum(max(0, min(100, npc.fatigue)) for npc in npcs)
    count = len(npcs)
    return {
        "avg_morale": morale_total / count,
        "avg_fatigue": fatigue_total / count,
    }


def _extract_combat_summary(
    executed: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    summaries: List[Dict[str, Any]] = []
    for entry in executed or []:
        effects = entry.get("effects")
        if not isinstance(effects, dict):
            continue
        combat = effects.get("combat")
        if not isinstance(combat, dict):
            continue
        outcome = combat.get("outcome") or {}
        structure = combat.get("structure") or {}
        attackers = int(outcome.get("attackers_casualties") or 0)
        defenders = int(outcome.get("defenders_casualties") or 0)
        summaries.append(
            {
                "function": entry.get("function"),
                "attackers_casualties": attackers,
                "defenders_casualties": defenders,
                "structure_id": structure.get("id"),
            }
        )
    return summaries


@lru_cache(maxsize=1)
def _get_theme_catalog() -> Dict[str, ThemeConfig]:
    catalog: Dict[str, ThemeConfig] = {}
    for theme_id, path in BUILTIN_THEMES.items():
        catalog[theme_id] = load_theme_from_file(path)
    return catalog


def _get_theme_config(theme_id: str) -> ThemeConfig:
    catalog = _get_theme_catalog()
    try:
        return catalog[theme_id]
    except KeyError as exc:  # pragma: no cover - defensive
        raise HTTPException(
            status_code=404, detail=f"Unknown theme_id '{theme_id}'."
        ) from exc


@app.get("/api/dev/turn_traces", response_model=List[TraceSummaryModel])
def list_turn_traces() -> List[TraceSummaryModel]:
    """Return available trace summaries for debug tooling."""

    traces = turn_trace.list_traces()
    return [
        TraceSummaryModel(
            turn=item["turn"],
            file=item["file"],
            modified_ts=item["modified_ts"],
        )
        for item in traces
    ]


@app.get("/api/dev/turn_traces/{turn_id}", response_model=Dict[str, Any])
def get_turn_trace(turn_id: int) -> Dict[str, Any]:
    """Return the stored trace payload for *turn_id*."""

    try:
        return turn_trace.load_trace(turn_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def _build_status_payload(
    client: OllamaClient | None = None,
) -> Dict[str, Any]:
    registry = get_registry()
    # If LLMs are disabled, avoid performing any live checks to keep status fast.
    if not is_llm_enabled():
        return {
            "llm": {},
            "version": API_VERSION,
            "mode": get_mode(),
            "use_llm": is_llm_enabled(),
        }

    # Build an OllamaClient tuned for a quick models list probe.
    client = client or OllamaClient(
        OllamaClientConfig(
            base_url=SETTINGS.ollama_base_url, timeout=SETTINGS.llm_status_list_timeout
        )
    )
    llm_health: Dict[str, str] = {}

    # First, attempt to retrieve the model list from Ollama and normalize it.
    try:
        available_models = set(client.list_models())
    except Exception:
        available_models = set()

    for record in registry.list():
        model_name = record.config.name
        agent_key = record.agent
        if model_name not in available_models:
            # Model not present on the Ollama server
            llm_health[agent_key] = "not_listed"
            continue

        # If listed, perform a very short generate probe to confirm responsiveness.
        try:
            generate_with_timeout(
                client,
                model=model_name,
                prompt="ping",
                options={"num_predict": 1},
                timeout_seconds=SETTINGS.llm_status_probe_timeout,
                max_retries=0,
            )
        except Exception:
            llm_health[agent_key] = "offline"
        else:
            llm_health[agent_key] = "online"

    return {
        "llm": llm_health,
        "version": API_VERSION,
        "mode": get_mode(),
        "use_llm": is_llm_enabled(),
    }


@app.get("/api/status")
def get_status() -> Dict[str, Any]:
    """Return system health including LLM availability."""

    return _build_status_payload()


@app.post("/api/status/llm_mode")
def update_llm_mode(payload: UpdateLLMModeRequest) -> Dict[str, Any]:
    """Toggle whether agents use live LLMs or deterministic fallbacks."""

    set_llm_enabled(payload.use_llm)
    return _build_status_payload()


__all__ = ["app"]


@app.get("/api/player_actions", response_model=List[PlayerActionModel])
def list_player_actions() -> List[PlayerActionModel]:
    """Return the catalog of supported player actions."""

    actions = []
    for entry in player_action_catalog.load_actions():
        actions.append(PlayerActionModel(**entry))
    return actions


@app.post("/api/select_action", response_model=SelectActionResponseModel)
def select_player_action(
    payload: SelectActionRequest,
) -> SelectActionResponseModel:
    """Validate and queue a player action for the next turn."""

    session_id, session, _ = _SESSION_MANAGER.get_or_create(payload.session_id)
    try:
        sanitized_params = player_action_validator.validate_player_action(
            payload.action_id,
            payload.params,
            session.game_state,
        )
        catalog_entry = player_action_catalog.get_action_by_id(payload.action_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if catalog_entry is None:
        raise HTTPException(status_code=404, detail="Unknown action.")
    routed = player_action_router.route_player_action(
        payload.action_id, sanitized_params, catalog_entry
    )
    session.player_action_context = routed
    return SelectActionResponseModel(
        session_id=session_id,
        player_action_context=routed,
    )
