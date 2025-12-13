import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import AddNodeScreen from '../AddNodeScreen';
import { nodeService } from '../../services/nodeService';
import { Alert } from 'react-native';

// Mock dependencies
jest.mock('../../services/nodeService');

const mockGoBack = jest.fn();
const mockSetOptions = jest.fn();
const mockRoute = { params: {} };

jest.mock('@react-navigation/native', () => ({
  useNavigation: () => ({
    goBack: mockGoBack,
    setOptions: mockSetOptions,
  }),
  useRoute: () => mockRoute,
}));

// Mock Alert
jest.spyOn(Alert, 'alert');

describe('AddNodeScreen', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockRoute.params = {}; // Reset params
  });

  it('renders form fields correctly', () => {
    const { getByPlaceholderText, getByText } = render(<AddNodeScreen />);

    expect(getByText('Ad Soyad *')).toBeTruthy();
    expect(getByText('Sektör *')).toBeTruthy();
    expect(getByPlaceholderText('Ahmet Yılmaz')).toBeTruthy();
  });

  it('shows error alert if required fields are empty', () => {
    const { getByText } = render(<AddNodeScreen />);
    
    const saveButton = getByText('✓ Kaydet');
    fireEvent.press(saveButton);

    expect(Alert.alert).toHaveBeenCalledWith('Hata', 'İsim ve Sektör alanları zorunludur.');
    expect(nodeService.createNode).not.toHaveBeenCalled();
  });

  it('calls createNode and navigates back on success', async () => {
    const { getByPlaceholderText, getByText } = render(<AddNodeScreen />);

    fireEvent.changeText(getByPlaceholderText('Ahmet Yılmaz'), 'Mehmet Öz');
    fireEvent.changeText(getByPlaceholderText('Yazılım, Finans, Pazarlama...'), 'Sağlık');
    
    (nodeService.createNode as jest.Mock).mockResolvedValue({});

    const saveButton = getByText('✓ Kaydet');
    fireEvent.press(saveButton);

    await waitFor(() => {
      expect(nodeService.createNode).toHaveBeenCalledWith(expect.objectContaining({
        name: 'Mehmet Öz',
        sector: 'Sağlık',
        relationshipStrength: 1,
      }));
      
      // Check if success alert is shown
      expect(Alert.alert).toHaveBeenCalledWith(
        'Başarılı', 
        'Kişi başarıyla eklendi.', 
        expect.any(Array)
      );
    });
    
    // Simulate pressing "Tamam" on the alert
    const alertButtons = (Alert.alert as jest.Mock).mock.calls[0][2];
    alertButtons[0].onPress();
    
    expect(mockGoBack).toHaveBeenCalled();
  });

  it('pre-fills form and calls updateNode in edit mode', async () => {
    const mockNode = {
      id: '123',
      name: 'Existing User',
      sector: 'Tech',
      tags: ['Dev'],
      notes: 'Some notes',
      relationshipStrength: 3,
    };
    mockRoute.params = { node: mockNode };

    const { getByPlaceholderText, getByText } = render(<AddNodeScreen />);

    // Check if fields are pre-filled (checking value prop is tricky in RNTL sometimes, but we can check if update works)
    // Actually we can check if the input has the value
    expect(getByPlaceholderText('Ahmet Yılmaz').props.value).toBe('Existing User');

    // Change a value
    fireEvent.changeText(getByPlaceholderText('Ahmet Yılmaz'), 'Updated User');

    (nodeService.updateNode as jest.Mock).mockResolvedValue({});

    const saveButton = getByText('✓ Kaydet');
    fireEvent.press(saveButton);

    await waitFor(() => {
      expect(nodeService.updateNode).toHaveBeenCalledWith('123', expect.objectContaining({
        name: 'Updated User',
        sector: 'Tech',
        relationshipStrength: 3,
      }));
      
      expect(Alert.alert).toHaveBeenCalledWith(
        'Başarılı', 
        'Kişi güncellendi.', 
        expect.any(Array)
      );
    });
  });
});
