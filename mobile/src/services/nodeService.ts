import api from './api';
import { PersonNode, CreatePersonRequest } from '../types';

export const nodeService = {
  getAllNodes: async (): Promise<PersonNode[]> => {
    const response = await api.get('/nodes');
    return response.data;
  },

  getNodeById: async (id: string): Promise<PersonNode> => {
    const response = await api.get(`/nodes/${id}`);
    return response.data;
  },

  createNode: async (data: CreatePersonRequest): Promise<PersonNode> => {
    const response = await api.post('/nodes', data);
    return response.data;
  },

  updateNode: async (id: string, data: Partial<CreatePersonRequest>): Promise<PersonNode> => {
    const response = await api.put(`/nodes/${id}`, data);
    return response.data;
  },

  deleteNode: async (id: string): Promise<void> => {
    await api.delete(`/nodes/${id}`);
  },
  
  searchNodes: async (query: string): Promise<PersonNode[]> => {
      const response = await api.get(`/nodes/filter`, { params: { q: query } });
      return response.data;
  }
};
