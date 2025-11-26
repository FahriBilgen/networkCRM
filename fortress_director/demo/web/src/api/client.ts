import type {
  BackendStatusPayload,
  PlayerActionDefinition,
  ResetSessionResponsePayload,
  RunTurnResponsePayload,
  SelectActionResponsePayload,
  ThemeListResponsePayload,
  TurnTraceSummary
} from "../types/ui";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

export async function runTurn(choiceId?: string, sessionId?: string, themeId?: string): Promise<RunTurnResponsePayload> {
  const body: Record<string, unknown> = {};
  if (choiceId) {
    body.choice_id = choiceId;
  }
  if (sessionId) {
    body.session_id = sessionId;
  }
  if (themeId) {
    body.theme_id = themeId;
  }
  return request<RunTurnResponsePayload>("/api/run_turn", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(body)
  });
}

export async function fetchTurnTraces(): Promise<TurnTraceSummary[]> {
  return request<TurnTraceSummary[]>("/api/dev/turn_traces");
}

export async function fetchTurnTrace(turn: number): Promise<unknown> {
  return request<unknown>(`/api/dev/turn_traces/${turn}`);
}

export async function fetchStatus(): Promise<BackendStatusPayload> {
  return request<BackendStatusPayload>("/api/status");
}

export async function updateLlmMode(useLlms: boolean): Promise<BackendStatusPayload> {
  return request<BackendStatusPayload>("/api/status/llm_mode", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ use_llm: useLlms })
  });
}

export async function fetchPlayerActions(): Promise<PlayerActionDefinition[]> {
  return request<PlayerActionDefinition[]>("/api/player_actions");
}

export async function selectPlayerAction(
  actionId: string,
  params: Record<string, unknown>,
  sessionId?: string
): Promise<SelectActionResponsePayload> {
  return request<SelectActionResponsePayload>("/api/select_action", {
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

export async function resetForNewRun(themeId?: string): Promise<ResetSessionResponsePayload> {
  const payload = themeId ? JSON.stringify({ theme_id: themeId }) : undefined;
  return request<ResetSessionResponsePayload>("/api/reset_for_new_run", {
    method: "POST",
    headers: payload
      ? {
          "Content-Type": "application/json"
        }
      : undefined,
    body: payload
  });
}

export async function fetchThemes(): Promise<ThemeListResponsePayload> {
  return request<ThemeListResponsePayload>("/api/themes");
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const url = buildUrl(path);
  const response = await fetch(url, init);
  if (!response.ok) {
    const detail = await safeParseError(response);
    throw new Error(detail ?? `Request failed (${response.status})`);
  }
  return (await response.json()) as T;
}

function buildUrl(path: string): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  if (!API_BASE) {
    return normalizedPath;
  }
  const trimmedBase = API_BASE.replace(/\/$/, "");
  return `${trimmedBase}${normalizedPath}`;
}

async function safeParseError(response: Response): Promise<string | null> {
  try {
    const payload = await response.json();
    return payload.detail ?? JSON.stringify(payload);
  } catch {
    return response.statusText;
  }
}
