const API_BASE = import.meta.env.VITE_API_BASE ?? "";
export async function runTurn(choiceId, sessionId) {
    const body = {};
    if (choiceId) {
        body.choice_id = choiceId;
    }
    if (sessionId) {
        body.session_id = sessionId;
    }
    return request("/api/run_turn", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(body)
    });
}
export async function fetchTurnTraces() {
    return request("/api/dev/turn_traces");
}
export async function fetchTurnTrace(turn) {
    return request(`/api/dev/turn_traces/${turn}`);
}
export async function fetchStatus() {
    return request("/api/status");
}
export async function updateLlmMode(useLlms) {
    return request("/api/status/llm_mode", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ use_llm: useLlms })
    });
}
export async function fetchPlayerActions() {
    return request("/api/player_actions");
}
export async function selectPlayerAction(actionId, params, sessionId) {
    return request("/api/select_action", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            action_id: actionId,
            params,
            session_id: sessionId
        })
    });
}
export async function resetForNewRun() {
    return request("/api/reset_for_new_run", {
        method: "POST"
    });
}
async function request(path, init) {
    const url = buildUrl(path);
    const response = await fetch(url, init);
    if (!response.ok) {
        const detail = await safeParseError(response);
        throw new Error(detail ?? `Request failed (${response.status})`);
    }
    return (await response.json());
}
function buildUrl(path) {
    const normalizedPath = path.startsWith("/") ? path : `/${path}`;
    if (!API_BASE) {
        return normalizedPath;
    }
    const trimmedBase = API_BASE.replace(/\/$/, "");
    return `${trimmedBase}${normalizedPath}`;
}
async function safeParseError(response) {
    try {
        const payload = await response.json();
        return payload.detail ?? JSON.stringify(payload);
    }
    catch {
        return response.statusText;
    }
}
