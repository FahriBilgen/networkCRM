import type { NodeRequestPayload, NodeResponse } from '../types';

export function buildNodeRequestPayload(
  node: NodeResponse,
  overrides?: Partial<NodeRequestPayload>,
): NodeRequestPayload {
  return {
    type: node.type,
    name: node.name ?? '',
    description: node.description ?? undefined,
    sector: node.sector ?? undefined,
    tags: node.tags ?? undefined,
    relationshipStrength: node.relationshipStrength ?? undefined,
    company: node.company ?? undefined,
    role: node.role ?? undefined,
    linkedinUrl: node.linkedinUrl ?? undefined,
    notes: node.notes ?? undefined,
    priority: node.priority ?? undefined,
    dueDate: node.dueDate ?? undefined,
    startDate: node.startDate ?? undefined,
    endDate: node.endDate ?? undefined,
    status: node.status ?? undefined,
    properties: {
      ...(node.properties ?? {}),
      ...(overrides?.properties ?? {}),
    },
    ...overrides,
  };
}
