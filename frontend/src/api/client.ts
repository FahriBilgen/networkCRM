import axios from 'axios';
import type {
  EdgeResponse,
  FavoritePathRequest,
  FavoritePathResponse,
  GoalNetworkDiagnosticsResponse,
  GoalSuggestionResponse,
  GoalPathSuggestionResponse,
  GraphResponse,
  NodeImportResponse,
  NodeClassificationRequestPayload,
  NodeClassificationResponsePayload,
  NodeSectorSuggestionRequestPayload,
  NodeSectorSuggestionResponsePayload,
  RelationshipNudgeResponsePayload,
  LinkPersonToGoalRequest,
  NodeFilterRequest,
  NodeProximityResponse,
  NodeRequestPayload,
  NodeResponse,
  VisionTreeResponse,
} from '../types';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8080/api',
  timeout: 8000,
});

let authToken: string | null = null;

export function setAuthToken(token: string | null) {
  authToken = token;
}

api.interceptors.request.use((config) => {
  if (authToken) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${authToken}`;
  }
  return config;
});

export async function fetchGraph(): Promise<GraphResponse> {
  const { data } = await api.get<GraphResponse>('/graph');
  return data;
}

export async function fetchVisionTree(): Promise<VisionTreeResponse> {
  const { data } = await api.get<VisionTreeResponse>('/graph/vision-tree');
  return data;
}

export async function fetchNodeProximity(nodeId: string): Promise<NodeProximityResponse> {
  const { data } = await api.get<NodeProximityResponse>(`/nodes/${nodeId}/proximity`);
  return data;
}

export async function filterNodes(filter: NodeFilterRequest): Promise<NodeResponse[]> {
  const { data } = await api.get<NodeResponse[]>('/nodes/filter', { params: filter });
  return data;
}

export async function searchNodes(query: string): Promise<NodeResponse[]> {
  if (!query.trim()) {
    return [];
  }
  const { data } = await api.get<NodeResponse[]>('/nodes/filter', {
    params: {
      q: query,
    },
  });
  return data;
}

export async function fetchGoalSuggestions(goalId: string, limit = 5): Promise<GoalSuggestionResponse> {
  const { data } = await api.get<GoalSuggestionResponse>(`/ai/goals/${goalId}/suggestions`, {
    params: { limit },
  });
  return data;
}

export async function fetchGoalPathSuggestions(
  goalId: string,
  params?: { maxDepth?: number; limit?: number },
): Promise<GoalPathSuggestionResponse> {
  const { data } = await api.get<GoalPathSuggestionResponse>(`/goals/${goalId}/path-suggestions`, {
    params,
  });
  return data;
}

export async function fetchGoalDiagnostics(goalId: string): Promise<GoalNetworkDiagnosticsResponse> {
  const { data } = await api.get<GoalNetworkDiagnosticsResponse>(`/ai/goals/${goalId}/diagnostics`);
  return data;
}

export async function fetchRelationshipNudges(limit = 5): Promise<RelationshipNudgeResponsePayload> {
  const { data } = await api.get<RelationshipNudgeResponsePayload>('/ai/nudges', { params: { limit } });
  return data;
}

export async function classifyNodeCandidate(
  payload: NodeClassificationRequestPayload,
): Promise<NodeClassificationResponsePayload> {
  const { data } = await api.post<NodeClassificationResponsePayload>('/ai/nodes/classify', payload);
  return data;
}

export async function suggestNodeSector(
  payload: NodeSectorSuggestionRequestPayload,
): Promise<NodeSectorSuggestionResponsePayload> {
  const { data } = await api.post<NodeSectorSuggestionResponsePayload>('/ai/nodes/sector-suggest', payload);
  return data;
}

export async function linkPersonToGoal(goalId: string, payload: LinkPersonToGoalRequest) {
  const { data } = await api.post<EdgeResponse>(`/ai/goals/${goalId}/link-person`, payload);
  return data;
}

export async function signIn(email: string, password: string) {
  return api.post<{ accessToken: string }>('/auth/signin', { email, password });
}

export async function createNode(payload: NodeRequestPayload) {
  const { data } = await api.post<NodeResponse>('/nodes', payload);
  return data;
}

export async function updateNode(id: string, payload: NodeRequestPayload) {
  const { data } = await api.put<NodeResponse>(`/nodes/${id}`, payload);
  return data;
}

export async function deleteNode(id: string) {
  await api.delete(`/nodes/${id}`);
}

export async function fetchFavoritePaths(): Promise<FavoritePathResponse[]> {
  const { data } = await api.get<FavoritePathResponse[]>('/favorites');
  return data;
}

export async function createFavoritePath(payload: FavoritePathRequest): Promise<FavoritePathResponse> {
  const { data } = await api.post<FavoritePathResponse>('/favorites', payload);
  return data;
}

export async function deleteFavoritePath(favoriteId: string) {
  await api.delete(`/favorites/${favoriteId}`);
}

export async function importPersonsCsv(file: File): Promise<NodeImportResponse> {
  const formData = new FormData();
  formData.append('file', file);
  const { data } = await api.post<NodeImportResponse>('/nodes/import/csv', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

export async function moveGoal(goalId: string, targetVisionId: string, sortOrder?: number | null) {
  await api.post(`/goals/${goalId}/move`, {
    targetNodeId: targetVisionId,
    sortOrder: sortOrder ?? 0,
  });
}

export async function moveProject(projectId: string, targetGoalId: string, sortOrder?: number | null) {
  await api.post(`/projects/${projectId}/move`, {
    targetNodeId: targetGoalId,
    sortOrder: sortOrder ?? 0,
  });
}

export { api };
