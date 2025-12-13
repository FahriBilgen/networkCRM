import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import NodeDetailScreen from '../NodeDetailScreen';
import { nodeService } from '../../services/nodeService';
import { Alert } from 'react-native';

// Mock dependencies
jest.mock('../../services/nodeService');

const mockNavigate = jest.fn();
const mockGoBack = jest.fn();
const mockRoute = { params: { nodeId: '123', node: { id: '123', name: 'Test', sector: 'IT' } } };

jest.mock('@react-navigation/native', () => {
  const React = require('react');
  return {
    useNavigation: () => ({
      navigate: mockNavigate,
      goBack: mockGoBack,
    }),
    useRoute: () => mockRoute,
    useFocusEffect: (effect: any) => {
      React.useEffect(effect, []);
    },
  };
});

// Mock Alert
jest.spyOn(Alert, 'alert');

describe('NodeDetailScreen', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (nodeService.getNodeById as jest.Mock).mockResolvedValue(mockRoute.params.node);
  });

  it('navigates to Edit screen when Edit button is pressed', () => {
    const { getByText } = render(<NodeDetailScreen />);
    
    const editButton = getByText('✏️ Düzenle');
    fireEvent.press(editButton);

    expect(mockNavigate).toHaveBeenCalledWith('AddNode', { node: mockRoute.params.node });
  });

  it('shows confirmation and deletes node when Delete button is pressed', async () => {
    const { getByText } = render(<NodeDetailScreen />);
    
    const deleteButton = getByText('🗑️ Sil');
    fireEvent.press(deleteButton);

    expect(Alert.alert).toHaveBeenCalledWith(
      'Kişiyi Sil',
      expect.any(String),
      expect.any(Array)
    );

    // Simulate confirming delete
    const alertButtons = (Alert.alert as jest.Mock).mock.calls[0][2];
    const deleteAction = alertButtons.find((b: any) => b.text === 'Sil');
    
    (nodeService.deleteNode as jest.Mock).mockResolvedValue({});
    
    await deleteAction.onPress();

    expect(nodeService.deleteNode).toHaveBeenCalledWith('123');
    expect(mockGoBack).toHaveBeenCalled();
  });
});
