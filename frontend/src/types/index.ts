export const NODE_TYPES = {
  PERSON: 'PERSON',
  GOAL: 'GOAL',
  PROJECT: 'PROJECT',
  VISION: 'VISION',
} as const;

export type NodeType = (typeof NODE_TYPES)[keyof typeof NODE_TYPES];

export const EDGE_TYPES = {
  KNOWS: 'KNOWS',
  SUPPORTS: 'SUPPORTS',
  BELONGS_TO: 'BELONGS_TO',
} as const;

export type EdgeType = (typeof EDGE_TYPES)[keyof typeof EDGE_TYPES];

export interface NodeResponse {
  id: string;
  type: NodeType;
  name: string;
  description?: string | null;
  sector?: string | null;
  tags?: string[];
  relationshipStrength?: number | null;
  company?: string | null;
  role?: string | null;
  linkedinUrl?: string | null;
  notes?: string | null;
  priority?: number | null;
  dueDate?: string | null;
  startDate?: string | null;
  endDate?: string | null;
  status?: string | null;
  properties?: Record<string, unknown> | null;
}

export interface EdgeResponse {
  id: string;
  sourceNodeId: string;
  targetNodeId: string;
  type: EdgeType;
  weight?: number | null;
  relationshipStrength?: number | null;
  relationshipType?: string | null;
  lastInteractionDate?: string | null;
  relevanceScore?: number | null;
  addedByUser?: boolean;
  notes?: string | null;
  sortOrder?: number | null;
}

export interface VisionTreeResponse {
  visions: VisionNode[];
}

export interface VisionNode {
  vision: NodeResponse;
  goals: GoalNode[];
}

export interface GoalNode {
  goal: NodeResponse;
  projects: NodeResponse[];
}

export interface GraphResponse {
  nodes: NodeResponse[];
  links: EdgeResponse[];
}

export interface NodeFilterRequest {
  type?: NodeType;
  types?: NodeType[];
  sector?: string;
  tags?: string[];
  minRelationshipStrength?: number;
  maxRelationshipStrength?: number;
  searchTerm?: string;
}

export interface GoalSuggestionResponse {
  goalId: string;
  suggestions: PersonSuggestion[];
}

export interface PersonSuggestion {
  person: NodeResponse;
  score: number;
}
