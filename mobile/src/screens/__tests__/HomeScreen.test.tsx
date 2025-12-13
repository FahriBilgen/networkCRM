import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import HomeScreen from '../HomeScreen';
import { nodeService } from '../../services/nodeService';
import { useAuthStore } from '../../store/authStore';
import { useNavigation } from '@react-navigation/native';

// Mock dependencies
jest.mock('../../services/nodeService');
jest.mock('../../store/authStore');

// Mock Navigation
jest.mock('@react-navigation/native', () => {
  const React = require('react');
  return {
    useNavigation: jest.fn(),
    useFocusEffect: (effect: any) => {
      React.useEffect(effect, []);
    },
  };
});

describe('HomeScreen', () => {
  const mockNodes = [
    { id: '1', type: 'PERSON', name: 'Alice', sector: 'Tech', relationshipStrength: 1, tags: ['CEO', 'Founder'] },
    { id: '2', type: 'PERSON', name: 'Bob', sector: 'Finance', relationshipStrength: 5, tags: ['Investor'] },
    { id: '3', type: 'PERSON', name: 'Charlie', sector: 'Tech', relationshipStrength: 3, tags: ['Developer'] },
    { id: '4', type: 'GOAL', name: 'Become Millionaire', sector: 'Finance' }, // Should be filtered out
  ];
  
  const mockNavigate = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    (nodeService.getAllNodes as jest.Mock).mockResolvedValue(mockNodes);
    (useAuthStore as unknown as jest.Mock).mockReturnValue({
      logout: jest.fn(),
      user: { fullName: 'Test User' },
    });
    (useNavigation as jest.Mock).mockReturnValue({
      navigate: mockNavigate,
    });
  });

  it('renders correctly and loads nodes', async () => {
    const { getByText } = render(<HomeScreen />);

    // Check header
    expect(getByText('Network')).toBeTruthy();

    // Check if nodes are loaded
    await waitFor(() => {
      expect(getByText('Alice')).toBeTruthy();
      expect(getByText('Bob')).toBeTruthy();
    }, { timeout: 3000 });
  });

  it('filters out non-person nodes', async () => {
    const { queryByText, getByText } = render(<HomeScreen />);

    await waitFor(() => {
      expect(getByText('Alice')).toBeTruthy();
      expect(queryByText('Become Millionaire')).toBeNull();
    });
  });

  it('filters nodes based on search query', async () => {
    const { getByPlaceholderText, getByText, queryByText } = render(<HomeScreen />);

    await waitFor(() => {
      expect(getByText('Alice')).toBeTruthy();
    });

    const searchInput = getByPlaceholderText('🔍 Ara (İsim, Sektör, Etiket)...');
    fireEvent.changeText(searchInput, 'Finance');

    await waitFor(() => {
      expect(getByText('Bob')).toBeTruthy();
      expect(queryByText('Alice')).toBeNull();
    });
  });

  it('filters nodes based on tags', async () => {
    const { getByPlaceholderText, getByText, queryByText } = render(<HomeScreen />);

    await waitFor(() => {
      expect(getByText('Alice')).toBeTruthy();
    });

    const searchInput = getByPlaceholderText('🔍 Ara (İsim, Sektör, Etiket)...');
    fireEvent.changeText(searchInput, 'Investor');

    await waitFor(() => {
      expect(getByText('Bob')).toBeTruthy();
      expect(queryByText('Alice')).toBeNull();
      expect(queryByText('Charlie')).toBeNull();
    });
  });

  it('filters nodes based on sector selection', async () => {
    const { getByText, getAllByText, queryByText } = render(<HomeScreen />);

    await waitFor(() => {
      expect(getByText('Alice')).toBeTruthy();
      expect(getByText('Bob')).toBeTruthy();
    });

    // Find and press 'Tech' sector chip
    // 'Tech' appears in the chip and in the list items. The chip should be the first one.
    const techTexts = getAllByText('Tech');
    const techChip = techTexts[0];
    fireEvent.press(techChip);

    await waitFor(() => {
      expect(getByText('Alice')).toBeTruthy();
      expect(getByText('Charlie')).toBeTruthy();
      expect(queryByText('Bob')).toBeNull();
    });

    // Press 'Tümü' to reset
    const allChip = getByText('Tümü');
    fireEvent.press(allChip);

    await waitFor(() => {
      expect(getByText('Bob')).toBeTruthy();
    });
  });

  it('sorts nodes by strength', async () => {
    const { getByText } = render(<HomeScreen />);

    await waitFor(() => {
      expect(getByText('Alice')).toBeTruthy();
    });

    // Initial state is sorted by strength, so button shows '⭐ Güç'
    const sortButton = getByText('⭐ Güç');
    fireEvent.press(sortButton);

    // Should now show '📝 İsim' (sorted by name)
    expect(getByText('📝 İsim')).toBeTruthy();
  });

  it('navigates to AddNode screen when FAB is pressed', async () => {
    const { getByText } = render(<HomeScreen />);
    
    const fab = getByText('+');
    fireEvent.press(fab);

    expect(mockNavigate).toHaveBeenCalledWith('AddNode');
  });
});
