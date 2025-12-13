import { nodeService } from '../nodeService';
import api from '../api';

// Mock the api module
jest.mock('../api');

describe('nodeService', () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  it('getAllNodes should return a list of nodes', async () => {
    const mockNodes = [
      { id: '1', name: 'Test User', sector: 'IT' },
      { id: '2', name: 'Another User', sector: 'Finance' },
    ];
    (api.get as jest.Mock).mockResolvedValue({ data: mockNodes });

    const result = await nodeService.getAllNodes();

    expect(api.get).toHaveBeenCalledWith('/nodes');
    expect(result).toEqual(mockNodes);
  });

  it('createNode should post data and return the created node', async () => {
    const newNode = { name: 'New User', sector: 'IT' };
    const createdNode = { id: '3', ...newNode };
    (api.post as jest.Mock).mockResolvedValue({ data: createdNode });

    const result = await nodeService.createNode(newNode);

    expect(api.post).toHaveBeenCalledWith('/nodes', newNode);
    expect(result).toEqual(createdNode);
  });

  it('getNodeById should return a single node', async () => {
    const mockNode = { id: '1', name: 'Test User', sector: 'IT' };
    (api.get as jest.Mock).mockResolvedValue({ data: mockNode });

    const result = await nodeService.getNodeById('1');

    expect(api.get).toHaveBeenCalledWith('/nodes/1');
    expect(result).toEqual(mockNode);
  });
});
