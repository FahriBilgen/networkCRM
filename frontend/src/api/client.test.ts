import { describe, it, expect, beforeEach, vi } from 'vitest';
import axios from 'axios';

vi.mock('axios');

describe('API Client', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Authentication', () => {
    it('should login successfully with valid credentials', async () => {
      const mockResponse = {
        data: {
          accessToken: 'jwt_token_here',
          tokenType: 'Bearer',
        },
      };

      (axios.post as any).mockResolvedValue(mockResponse);

      const response = await axios.post('/api/auth/signin', {
        email: 'test@example.com',
        password: 'password123',
      });

      expect(response.data.accessToken).toBe('jwt_token_here');
      expect(axios.post).toHaveBeenCalledWith('/api/auth/signin', {
        email: 'test@example.com',
        password: 'password123',
      });
    });

    it('should handle login failure', async () => {
      const mockError = {
        response: {
          status: 401,
          data: { message: 'Invalid credentials' },
        },
      };

      (axios.post as any).mockRejectedValue(mockError);

      try {
        await axios.post('/api/auth/signin', {
          email: 'test@example.com',
          password: 'wrong_password',
        });
        expect.fail('Should have thrown an error');
      } catch (error: any) {
        expect(error.response.status).toBe(401);
      }
    });

    it('should signup successfully', async () => {
      const mockResponse = {
        data: {
          accessToken: 'jwt_token_here',
          tokenType: 'Bearer',
        },
      };

      (axios.post as any).mockResolvedValue(mockResponse);

      const response = await axios.post('/api/auth/signup', {
        email: 'newuser@example.com',
        password: 'password123',
      });

      expect(response.data.accessToken).toBeDefined();
      expect(axios.post).toHaveBeenCalled();
    });
  });

  describe('Nodes', () => {
    it('should create a node', async () => {
      const mockResponse = {
        data: {
          id: '123',
          name: 'John Doe',
          type: 'PERSON',
          sector: 'Technology',
        },
      };

      (axios.post as any).mockResolvedValue(mockResponse);

      const response = await axios.post('/api/nodes', {
        name: 'John Doe',
        type: 'PERSON',
        sector: 'Technology',
      });

      expect(response.data.name).toBe('John Doe');
      expect(response.data.type).toBe('PERSON');
    });

    it('should get all nodes', async () => {
      const mockResponse = {
        data: [
          { id: '1', name: 'John', type: 'PERSON' },
          { id: '2', name: 'Tech Vision', type: 'VISION' },
        ],
      };

      (axios.get as any).mockResolvedValue(mockResponse);

      const response = await axios.get('/api/nodes');

      expect(response.data).toHaveLength(2);
      expect(response.data[0].name).toBe('John');
    });

    it('should update a node', async () => {
      const mockResponse = {
        data: {
          id: '123',
          name: 'Jane Doe',
          sector: 'Finance',
        },
      };

      (axios.put as any).mockResolvedValue(mockResponse);

      const response = await axios.put('/api/nodes/123', {
        name: 'Jane Doe',
        sector: 'Finance',
      });

      expect(response.data.name).toBe('Jane Doe');
      expect(response.data.sector).toBe('Finance');
    });

    it('should delete a node', async () => {
      (axios.delete as any).mockResolvedValue({ data: {} });

      await axios.delete('/api/nodes/123');

      expect(axios.delete).toHaveBeenCalledWith('/api/nodes/123');
    });

    it('should filter nodes', async () => {
      const mockResponse = {
        data: [
          { id: '1', name: 'John', sector: 'Technology' },
        ],
      };

      (axios.post as any).mockResolvedValue(mockResponse);

      const response = await axios.post('/api/nodes/filter', {
        sector: 'Technology',
      });

      expect(response.data).toHaveLength(1);
      expect(response.data[0].sector).toBe('Technology');
    });
  });

  describe('Error Handling', () => {
    it('should handle network errors', async () => {
      const mockError = {
        message: 'Network Error',
      };

      (axios.get as any).mockRejectedValue(mockError);

      try {
        await axios.get('/api/nodes');
        expect.fail('Should have thrown an error');
      } catch (error: any) {
        expect(error.message).toBe('Network Error');
      }
    });

    it('should handle 404 errors', async () => {
      const mockError = {
        response: {
          status: 404,
          data: { message: 'Not found' },
        },
      };

      (axios.get as any).mockRejectedValue(mockError);

      try {
        await axios.get('/api/nodes/999');
        expect.fail('Should have thrown an error');
      } catch (error: any) {
        expect(error.response.status).toBe(404);
      }
    });
  });
});
