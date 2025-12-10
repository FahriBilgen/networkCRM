import { EDGE_TYPES, NODE_TYPES } from '../types';
import type { GraphResponse, NodeResponse, VisionTreeResponse } from '../types';

export const mockVisionTree: VisionTreeResponse = {
  visions: [
    {
      vision: {
        id: 'vision-1',
        type: NODE_TYPES.VISION,
        name: 'Girişimi Ticarileştirmek',
        description: '12 ay içinde pazara açılmak',
        priority: 5,
      },
      goals: [
        {
          goal: {
            id: 'goal-1',
            type: NODE_TYPES.GOAL,
            name: 'MVP lansmanı',
            description: 'İlk kullanıcıların edinilmesi',
            dueDate: '2025-06-01',
          },
          projects: [
            {
              id: 'project-1',
              type: NODE_TYPES.PROJECT,
              name: 'Onboarding akışı',
              status: 'IN_PROGRESS',
            },
            {
              id: 'project-2',
              type: NODE_TYPES.PROJECT,
              name: 'Beta kullanıcı listesi',
              status: 'TODO',
            },
          ],
        },
        {
          goal: {
            id: 'goal-2',
            type: NODE_TYPES.GOAL,
            name: 'Network genişletme',
            description: 'Mentor ve yatırımcı havuzu',
          },
          projects: [
            {
              id: 'project-3',
              type: NODE_TYPES.PROJECT,
              name: 'Yatırımcı buluşmaları',
              status: 'PLANNED',
            },
          ],
        },
      ],
    },
  ],
};

const visionNode: NodeResponse = {
  id: 'vision-1',
  type: NODE_TYPES.VISION,
  name: 'Girişimi Ticarileştirmek',
};

const goalNode: NodeResponse = {
  id: 'goal-1',
  type: NODE_TYPES.GOAL,
  name: 'MVP lansmanı',
};

const projectNode: NodeResponse = {
  id: 'project-1',
  type: NODE_TYPES.PROJECT,
  name: 'Onboarding akışı',
};

const personNodes: NodeResponse[] = [
  {
    id: 'person-1',
    type: NODE_TYPES.PERSON,
    name: 'Ahmet Yılmaz',
    sector: 'Fintech',
    relationshipStrength: 4,
    tags: ['mentor', 'yatırımcı'],
  },
  {
    id: 'person-2',
    type: NODE_TYPES.PERSON,
    name: 'Deniz Kara',
    sector: 'Marketing',
    relationshipStrength: 3,
    tags: ['growth'],
  },
];

export const mockGraphResponse: GraphResponse = {
  nodes: [visionNode, goalNode, projectNode, ...personNodes],
  links: [
    {
      id: 'edge-vision-goal',
      sourceNodeId: goalNode.id,
      targetNodeId: visionNode.id,
      type: EDGE_TYPES.BELONGS_TO,
      sortOrder: 1,
    },
    {
      id: 'edge-project-goal',
      sourceNodeId: projectNode.id,
      targetNodeId: goalNode.id,
      type: EDGE_TYPES.BELONGS_TO,
      sortOrder: 1,
    },
    {
      id: 'edge-person-goal',
      sourceNodeId: personNodes[0].id,
      targetNodeId: goalNode.id,
      type: EDGE_TYPES.SUPPORTS,
      relevanceScore: 0.82,
    },
    {
      id: 'edge-person-person',
      sourceNodeId: personNodes[0].id,
      targetNodeId: personNodes[1].id,
      type: EDGE_TYPES.KNOWS,
      relationshipStrength: 3,
    },
  ],
};
