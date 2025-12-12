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
  createdAt?: string | null;
  updatedAt?: string | null;
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

export interface FavoritePathResponse {
  id: string;
  goalId: string;
  label: string;
  nodeIds: string[];
  createdAt?: string | null;
}

export interface FavoritePathRequest {
  goalId: string;
  label: string;
  nodeIds: string[];
}

export interface NodeImportResponse {
  processed: number;
  created: number;
  skipped: number;
  errors?: string[];
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
  reason?: string;
}

export interface GoalPathSuggestionResponse {
  goalId: string;
  suggestions: GoalPathSuggestion[];
}

export interface GoalPathSuggestion {
  person: NodeResponse;
  distance: number;
  pathNodeIds: string[];
}

export interface GoalNetworkDiagnostics {
  readiness: {
    level: 'strong' | 'medium' | 'weak';
    score: number;
    message: string;
    summary: string[];
  };
  sectorHighlights: string[];
  riskAlerts: string[];
}

export interface GoalNetworkDiagnosticsResponse extends GoalNetworkDiagnostics {
  goalId: string;
}

export interface RelationshipNudgeResponsePayload {
  nudges: RelationshipNudge[];
}

export interface RelationshipNudge {
  person: NodeResponse;
  edgeType: EdgeType;
  lastInteractionDate?: string | null;
  relationshipStrength?: number | null;
  targetName?: string | null;
  reasons: string[];
}

export interface NodeClassificationRequestPayload {
  name: string;
  description?: string | null;
  notes?: string | null;
  sector?: string | null;
  tags?: string[];
  priority?: number | null;
  status?: string | null;
  dueDate?: string | null;
  startDate?: string | null;
  endDate?: string | null;
}

export interface NodeClassificationResponsePayload {
  suggestedType: NodeType;
  confidence: number;
  scores: Partial<Record<NodeType, number>>;
  matchedSignals?: string[];
  rationale?: string | null;
}

export interface NodeSectorSuggestionRequestPayload {
  name: string;
  description?: string | null;
  notes?: string | null;
  tags?: string[];
}

export interface NodeSectorSuggestionResponsePayload {
  sector: string;
  confidence: number;
  matchedKeywords?: string[];
  rationale?: string | null;
}

export interface LinkPersonToGoalRequest {
  personId: string;
  relevanceScore?: number | null;
  relationshipStrength?: number | null;
  notes?: string | null;
  addedByUser?: boolean | null;
}

export interface NodeProximityResponse {
  nodeId: string;
  totalConnections: number;
  connectionCounts: Record<EdgeType, number>;
  neighbors: NeighborConnection[];
  influenceScore: number;
}

export interface NeighborConnection {
  edgeId: string;
  edgeType: EdgeType;
  outgoing: boolean;
  neighbor: NodeResponse;
  relationshipStrength?: number | null;
  lastInteractionDate?: string | null;
}

export interface NodeRequestPayload {
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
