const DEFAULT_GRID_SIZE = 12;
const DEFAULT_STATE = {
    turn: 0,
    resources: {
        food: 0,
        materials: 0,
        morale: 60
    },
    threat: {
        score: 0,
        phase: "calm"
    },
    npcPositions: {},
    structures: {},
    eventMarkers: [],
    lastCombatSummary: null,
    atmosphere: {
        mood: "Calm watch",
        visual: "Lanterns trace the ramparts",
        audio: "Distant wind"
    },
    eventNode: {
        id: "intro",
        description: "Awaiting first directive."
    }
};
export function createInitialGameState() {
    return cloneState(DEFAULT_STATE);
}
export function mergeStateFromBackend(previous, payload) {
    const delta = payload.state_delta;
    const nextTurn = resolveTurn(previous, payload);
    const nextResources = resolveResources(previous, payload);
    const nextThreat = resolveThreat(previous, payload);
    const npcSource = payload.npc_positions ?? delta?.npc_positions;
    const structureSource = payload.structures ?? delta?.structures;
    const markerSource = payload.event_markers ?? delta?.event_markers;
    const nextAtmosphere = normalizeAtmosphere(payload.atmosphere, previous.atmosphere);
    const nextEventNode = normalizeEventNode(payload.event_node, payload.event_node_id, payload.event_node_description, previous.eventNode);
    const nextCombatSummary = extractCombatSummary(payload.combat_summary, previous.lastCombatSummary);
    return {
        turn: nextTurn,
        resources: nextResources,
        threat: nextThreat,
        npcPositions: mergeNpcRecords(previous.npcPositions, npcSource),
        structures: mergeStructureRecords(previous.structures, structureSource),
        eventMarkers: markerSource ? normalizeEventMarkers(markerSource) : previous.eventMarkers,
        lastCombatSummary: nextCombatSummary,
        atmosphere: nextAtmosphere,
        eventNode: nextEventNode
    };
}
function resolveTurn(previous, payload) {
    const fromPayload = payload.turn ?? payload.turn_number ?? payload.hud?.turn;
    return typeof fromPayload === "number" ? Math.max(0, Math.floor(fromPayload)) : previous.turn;
}
function resolveResources(previous, payload) {
    const fromSnapshot = payload.resources;
    const hud = payload.hud;
    const nextFood = coerceNumber(fromSnapshot?.food ?? hud?.food ?? previous.resources.food);
    const nextMaterials = coerceNumber(fromSnapshot?.materials ??
        fromSnapshot?.world_resources ??
        hud?.resources ??
        previous.resources.materials);
    const nextMorale = coerceNumber(hud?.morale ?? fromSnapshot?.morale ?? previous.resources.morale);
    return {
        food: nextFood,
        materials: nextMaterials,
        morale: nextMorale
    };
}
function resolveThreat(previous, payload) {
    const snapshot = payload.threat;
    const scoreCandidate = snapshot?.score ?? payload.threat_score;
    const phaseCandidate = snapshot?.phase ?? payload.threat_phase;
    return {
        score: typeof scoreCandidate === "number" ? Number(scoreCandidate) : previous.threat.score,
        phase: typeof phaseCandidate === "string" ? phaseCandidate : previous.threat.phase
    };
}
function mergeNpcRecords(previous, incoming) {
    if (!incoming) {
        return { ...previous };
    }
    const next = { ...previous };
    for (const [id, payload] of Object.entries(incoming)) {
        next[id] = normalizeNpcState(id, payload);
    }
    return next;
}
function mergeStructureRecords(previous, incoming) {
    if (!incoming) {
        return { ...previous };
    }
    const next = { ...previous };
    for (const [id, payload] of Object.entries(incoming)) {
        next[id] = normalizeStructure(id, payload);
    }
    return next;
}
function normalizeNpcState(id, payload) {
    return {
        x: clamp(payload.x),
        y: clamp(payload.y),
        health: clampPercent(payload.health ?? 100),
        morale: clampPercent(payload.morale ?? 60),
        fatigue: clampPercent(payload.fatigue ?? 0),
        name: payload.name ?? id,
        role: payload.role,
        hostile: payload.hostile
    };
}
function normalizeStructure(id, payload) {
    return {
        id: payload.id ?? id,
        x: clamp(payload.x),
        y: clamp(payload.y),
        integrity: clampPercent(payload.integrity ?? 0),
        maxIntegrity: Math.max(1, payload.max_integrity ?? 100),
        on_fire: Boolean(payload.on_fire),
        kind: payload.kind,
        status: payload.status
    };
}
function normalizeEventMarkers(markers) {
    return markers
        .map((entry) => ({
        id: entry.id,
        x: clamp(entry.x),
        y: clamp(entry.y),
        severity: Math.max(1, entry.severity ?? 1),
        description: entry.description ?? "",
        entity_type: entry.entity_type
    }))
        .sort((a, b) => b.severity - a.severity);
}
function normalizeAtmosphere(descriptor, fallback) {
    if (!descriptor) {
        return { ...fallback };
    }
    const fallbackVisual = descriptor.visuals ?? fallback.visual;
    const rawVisual = descriptor?.visual;
    const visual = typeof rawVisual === "string" ? rawVisual : fallbackVisual;
    return {
        mood: descriptor.mood ?? fallback.mood,
        visual: typeof visual === "string" ? visual : fallback.visual,
        audio: descriptor.audio ?? fallback.audio
    };
}
function normalizeEventNode(node, legacyId, legacyDescription, fallback) {
    if (node && node.id) {
        return {
            id: node.id,
            description: node.description ?? fallback.description
        };
    }
    if (legacyId || legacyDescription) {
        return {
            id: legacyId ?? fallback.id,
            description: legacyDescription ?? fallback.description
        };
    }
    return { ...fallback };
}
function extractCombatSummary(entries, fallback) {
    if (!entries || entries.length === 0) {
        return fallback;
    }
    const latest = entries[entries.length - 1];
    const location = latest.structure_id ? ` @ ${latest.structure_id}` : "";
    return `Combat: attackers ${latest.attackers_casualties} / defenders ${latest.defenders_casualties}${location}`;
}
function clamp(value, limit = DEFAULT_GRID_SIZE) {
    if (typeof value !== "number" || Number.isNaN(value)) {
        return 0;
    }
    return Math.max(0, Math.min(limit - 1, Math.round(value)));
}
function clampPercent(value) {
    if (typeof value !== "number" || Number.isNaN(value)) {
        return 0;
    }
    return Math.max(0, Math.min(100, Math.round(value)));
}
function coerceNumber(value) {
    return typeof value === "number" && !Number.isNaN(value) ? value : 0;
}
function cloneState(state) {
    return {
        turn: state.turn,
        resources: { ...state.resources },
        threat: { ...state.threat },
        npcPositions: { ...state.npcPositions },
        structures: { ...state.structures },
        eventMarkers: [...state.eventMarkers],
        lastCombatSummary: state.lastCombatSummary,
        atmosphere: { ...state.atmosphere },
        eventNode: { ...state.eventNode }
    };
}
