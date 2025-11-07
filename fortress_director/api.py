import json
import os
from copy import deepcopy

from fastapi import FastAPI, Body, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from typing import Dict, Any, List, Optional

from pydantic import ValidationError

from fortress_director.orchestrator.orchestrator import Orchestrator, StateStore
from fortress_director.llm.offline_client import OfflineOllamaClient
from fortress_director.agents.event_agent import EventAgent
from fortress_director.agents.world_agent import WorldAgent
from fortress_director.agents.character_agent import CharacterAgent
from fortress_director.agents.creativity_agent import CreativityAgent
from fortress_director.agents.director_agent import DirectorAgent
from fortress_director.agents.judge_agent import JudgeAgent
from fortress_director.agents.planner_agent import PlannerAgent
from fortress_director.codeaware.function_registry import SafeFunctionRegistry
from fortress_director.codeaware.function_validator import FunctionCallValidator
from fortress_director.codeaware.rollback_system import RollbackSystem
from fortress_director.rules.rules_engine import RulesEngine
from fortress_director.settings import DEFAULT_WORLD_STATE
from fortress_director.api_models import (
    ContractIndexResponse,
    ContractSchemaResponse,
    OptionsResponseModel,
    TurnResultModel,
)
from fortress_director.utils.telemetry_bus import TelemetryBus
from fortress_director.api_contracts import APIContractRegistry

API_VERSION = "v1"
app = FastAPI()
TELEMETRY_BUS = TelemetryBus()
CONTRACT_REGISTRY = APIContractRegistry(API_VERSION)

def _build_orchestrator() -> Orchestrator:
    """Build orchestrator. If FORTRESS_OFFLINE=1, use offline LLMs for tests."""
    if os.environ.get("FORTRESS_OFFLINE", "0") == "1":
        base = Path(__file__).resolve().parent / "_offline_runtime"
        base.mkdir(parents=True, exist_ok=True)
        world_path = base / "world_state.json"
        if not world_path.exists():
            world_path.write_text(json.dumps(DEFAULT_WORLD_STATE, indent=2), encoding="utf-8")
        db_path = base / "game_state.sqlite"
        state_store = StateStore(world_path, db_path=db_path)
        registry = SafeFunctionRegistry()
        validator = FunctionCallValidator(
            registry,
            max_calls_per_function=5,
            max_total_calls=20,
        )
        rollback = RollbackSystem(
            snapshot_provider=state_store.snapshot,
            restore_callback=state_store.persist,
            max_checkpoints=3,
        )
        runs_dir = base / "runs"
        runs_dir.mkdir(parents=True, exist_ok=True)
        offline_judge = JudgeAgent(client=OfflineOllamaClient(agent_key="judge"))
        rules_engine = RulesEngine(judge_agent=offline_judge, tolerance=1)
        orch = Orchestrator(
            state_store=state_store,
            event_agent=EventAgent(client=OfflineOllamaClient(agent_key="event")),
            world_agent=WorldAgent(client=OfflineOllamaClient(agent_key="world")),
            character_agent=CharacterAgent(client=OfflineOllamaClient(agent_key="character")),
            creativity_agent=CreativityAgent(
                client=OfflineOllamaClient(agent_key="creativity"),
                use_llm=False,
            ),
            planner_agent=PlannerAgent(client=OfflineOllamaClient(agent_key="planner")),
            director_agent=DirectorAgent(client=OfflineOllamaClient(agent_key="director")),
            judge_agent=offline_judge,
            rules_engine=rules_engine,
            function_registry=registry,
            function_validator=validator,
            rollback_system=rollback,
            runs_dir=runs_dir,
        )
        orch._register_default_safe_functions()
        orch.telemetry_bus = TELEMETRY_BUS
        orch.api_version = API_VERSION
        return orch
    # Default: real LLMs via Ollama
    orch = Orchestrator.build_default()
    orch.telemetry_bus = TELEMETRY_BUS
    orch.api_version = API_VERSION
    return orch

orchestrator = _build_orchestrator()
orchestrator.api_version = API_VERSION

# Serve a very basic UI under /ui
_UI_DIR = Path(__file__).resolve().parent / "ui"
if _UI_DIR.exists():
    app.mount("/ui", StaticFiles(directory=str(_UI_DIR), html=True), name="ui")


def _peek_options() -> List[Dict[str, Any]]:
    """Return current turn's options without committing state."""
    snap = orchestrator.state_store.snapshot()
    result = orchestrator.run_turn(player_choice_id=None)
    opts: List[Dict[str, Any]] = []
    raw = result.get("options") if isinstance(result, dict) else None
    if isinstance(raw, list):
        opts = [o for o in raw if isinstance(o, dict)]
    # restore snapshot
    orchestrator.state_store.persist(snap)
    return opts


def _assert_contract_version(version: str) -> None:
    if version != API_VERSION:
        raise HTTPException(status_code=404, detail=f"unknown schema version '{version}'")


@app.post("/motif/update")
def update_motif(new_motif: str = Body(..., embed=True)):
    orchestrator.update_motif(new_motif)
    return {"status": "success", "motif": new_motif, "api_version": API_VERSION}


@app.post("/character/update")
def update_character(
    name: str = Body(...),
    summary: str = Body(...),
    stats: dict = Body(None),
    inventory: list = Body(None),
):
    orchestrator.update_character(name, summary, stats, inventory)
    return {"status": "success", "character": name, "api_version": API_VERSION}


@app.post("/prompt/update")
def update_prompt(
    agent: str = Body(...),
    new_prompt: str = Body(...),
    persist_to_file: bool = Body(True),
):
    orchestrator.update_prompt(agent, new_prompt, persist_to_file)
    return {"status": "success", "agent": agent, "api_version": API_VERSION}


@app.post("/safe_function/mutate")
def mutate_safe_function(name: str = Body(...), remove: bool = Body(False)):
    # For demo, only support removal via API
    orchestrator.mutate_safe_function(name, remove=remove)
    return {
        "status": "success",
        "name": name,
        "removed": remove,
        "api_version": API_VERSION,
    }


@app.post("/game/reset")
def reset_game():
    try:
        orchestrator.state_store.persist(deepcopy(DEFAULT_WORLD_STATE))
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=500, detail=f"reset failed: {exc}")
    return {"status": "ok", "message": "world reset", "api_version": API_VERSION}


@app.get("/game/state")
def get_state():
    try:
        summary = orchestrator.state_store.summary()
        summary["api_version"] = API_VERSION
        return summary
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=500, detail=f"state fetch failed: {exc}")


@app.get("/game/options", response_model=OptionsResponseModel)
def get_options():
    try:
        payload = OptionsResponseModel(
            api_version=API_VERSION,
            options=_peek_options(),
        )
        return payload
    except ValidationError as exc:
        raise HTTPException(
            status_code=500,
            detail={"error": "options validation failed", "details": exc.errors()},
        )
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=500, detail=f"options fetch failed: {exc}")


@app.post("/game/turn", response_model=TurnResultModel)
def play_turn(choice_id: Optional[str] = Body(None, embed=True)):
    try:
        result = orchestrator.run_turn(player_choice_id=choice_id)
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=500, detail=f"turn failed: {exc}")
    result["api_version"] = API_VERSION
    return TurnResultModel.parse_obj(result)


@app.get("/telemetry/latest")
def telemetry_latest() -> Dict[str, Any]:
    return {"api_version": API_VERSION, "event": TELEMETRY_BUS.latest()}


@app.get("/telemetry/events")
async def telemetry_events():
    async def event_stream():
        async for payload in TELEMETRY_BUS.stream():
            yield f"data: {json.dumps(payload)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/")
def root_index():
    # Hint to use the UI
    if _UI_DIR.exists():
        return HTMLResponse(
            """
        <html>
          <head><title>Fortress Director</title></head>
          <body>
            <p>Open the <a href=\"/ui/\">basic UI</a> to play.</p>
          </body>
        </html>
        """
        )
    return {"message": "Fortress Director API. Visit /game/* or mount UI under /ui."}


@app.get("/health")
def health() -> Dict[str, Any]:
    try:
        st = orchestrator.state_store.summary()
        return {"status": "ok", "state": st}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


@app.get("/api/version")
def api_version() -> Dict[str, str]:
    return {"api_version": API_VERSION}


@app.get("/api/schema/{version}", response_model=ContractIndexResponse)
def api_contract_index(version: str) -> ContractIndexResponse:
    _assert_contract_version(version)
    return ContractIndexResponse(
        api_version=API_VERSION,
        contract_version=version,
        components=CONTRACT_REGISTRY.list_components(),
    )


@app.get(
    "/api/schema/{version}/{component}",
    response_model=ContractSchemaResponse,
)
def api_contract_schema(version: str, component: str) -> ContractSchemaResponse:
    _assert_contract_version(version)
    component_key = component.lower()
    try:
        schema = CONTRACT_REGISTRY.get_schema(component_key)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc
    return ContractSchemaResponse(
        api_version=API_VERSION,
        contract_version=version,
        component=component_key,
        schema_document=schema,
    )
