from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class GuardrailNote(BaseModel):
    type: str
    message: str


class NPCTrustEntry(BaseModel):
    name: str
    trust: float


class NPCJournalEntry(BaseModel):
    turn: Optional[int] = None
    name: Optional[str] = None
    intent: Optional[str] = None
    entry: Optional[str] = None


class NPCPosition(BaseModel):
    id: str
    room: Optional[str] = None


class StructureCard(BaseModel):
    id: str
    status: Optional[str] = None
    durability: Optional[int] = None
    max_durability: Optional[int] = None


class MapState(BaseModel):
    current_room: Optional[str] = None
    day: Optional[int] = None
    time: Optional[str] = None
    npc_positions: List[NPCPosition] = []
    structures: List[StructureCard] = []


class PlayerView(BaseModel):
    short_scene: Optional[str] = None
    short_world: Optional[str] = None
    options: List[Dict[str, Any]] = []
    primary_reaction: Optional[str] = None
    safe_functions: List[str] = []
    guardrail_notes: List[GuardrailNote] = []
    metrics_panel: Optional[Dict[str, float]] = None
    active_flags: List[str] = []
    npc_trust_overview: List[NPCTrustEntry] = []
    npc_journal_recent: List[NPCJournalEntry] = []
    fallback_strategy: Optional[str] = None
    fallback_summary: Optional[str] = None
    map_state: Optional[MapState] = None
    npc_locations: List[NPCPosition] = []
    safe_function_history: List[Dict[str, Any]] = []


class OptionModel(BaseModel):
    id: Optional[str] = None
    text: str
    action_type: Optional[str] = None
    tags: List[str] = []
    motifs: List[str] = []


class OptionsResponseModel(BaseModel):
    api_version: str
    options: List[OptionModel]


class SafeFunctionResultModel(BaseModel):
    name: str
    success: bool
    timestamp: Optional[float] = None
    metadata: Dict[str, Any] = {}
    effects: Optional[Any] = None
    summary: Optional[str] = None
    guardrail_notes: Optional[List[GuardrailNote]] = None


class TurnResultModel(BaseModel):
    api_version: str
    scene: Optional[str] = None
    options: List[OptionModel]
    player_view: Optional[PlayerView] = None
    safe_function_results: List[SafeFunctionResultModel]
    telemetry: Dict[str, Any]
    win_loss: Dict[str, Any]
    summary_text: Optional[str] = None
    final_summary: Optional[Any] = None
    final_summary_cards: Optional[Any] = None
    post_game_recap: Optional[Any] = None


class ContractIndexResponse(BaseModel):
    api_version: str
    contract_version: str
    components: List[str]


class ContractSchemaResponse(BaseModel):
    api_version: str
    contract_version: str
    component: str
    schema_document: Dict[str, Any] = Field(..., alias="schema")

    class Config:
        allow_population_by_field_name = True
