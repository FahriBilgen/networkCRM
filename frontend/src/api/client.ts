import axios from 'axios';
import type {
  GoalSuggestionResponse,
  GraphResponse,
  NodeFilterRequest,
  NodeResponse,
  VisionTreeResponse,
} from '../types';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8080/api',
  timeout: 8000,
});

export async function fetchGraph(): Promise<GraphResponse> {
  const { data } = await api.get<GraphResponse>('/graph');
  return data;
}

export async function fetchVisionTree(): Promise<VisionTreeResponse> {
  const { data } = await api.get<VisionTreeResponse>('/graph/vision-tree');
  return data;
}

export async function filterNodes(filter: NodeFilterRequest): Promise<NodeResponse[]> {
  const { data } = await api.get<NodeResponse[]>('/nodes/filter', { params: filter });
  return data;
}

export async function fetchGoalSuggestions(goalId: string, limit = 5): Promise<GoalSuggestionResponse> {
  const { data } = await api.get<GoalSuggestionResponse>(`/ai/goals/${goalId}/suggestions`, {
    params: { limit },
  });
  return data;
}
