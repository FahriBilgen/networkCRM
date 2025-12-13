import React from 'react';
import { render, fireEvent, waitFor, act } from '@testing-library/react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import HomeScreen from '../HomeScreen';
import AddNodeScreen from '../AddNodeScreen';
import NodeDetailScreen from '../NodeDetailScreen';
import { nodeService } from '../../services/nodeService';
import { useAuthStore } from '../../store/authStore';
import { PersonNode } from '../../types';

// Mock dependencies
jest.mock('../../services/nodeService');
jest.mock('../../store/authStore');

// Define Stack
const Stack = createNativeStackNavigator();

// Mock Component to wrap screens
const MockApp = () => (
  <NavigationContainer>
    <Stack.Navigator>
      <Stack.Screen name="Home" component={HomeScreen} />
      <Stack.Screen name="AddNode" component={AddNodeScreen} />
      <Stack.Screen name="NodeDetail" component={NodeDetailScreen} />
    </Stack.Navigator>
  </NavigationContainer>
);

describe('Full App Integration Flow', () => {
  const mockNode: PersonNode = {
    id: '123',
    type: 'PERSON',
    name: 'Test Person',
    sector: 'Technology',
    relationshipStrength: 3,
    tags: ['Developer'],
    notes: 'Test notes'
  };

  beforeEach(() => {
    jest.clearAllMocks();
    
    // Mock Auth
    (useAuthStore as unknown as jest.Mock).mockReturnValue({
      logout: jest.fn(),
      user: { fullName: 'Test User' },
    });

    // Mock NodeService default behaviors
    (nodeService.getAllNodes as jest.Mock).mockResolvedValue([]);
    (nodeService.createNode as jest.Mock).mockResolvedValue(mockNode);
    (nodeService.getNodeById as jest.Mock).mockResolvedValue(mockNode);
    (nodeService.updateNode as jest.Mock).mockResolvedValue({ ...mockNode, name: 'Updated Person' });
    (nodeService.deleteNode as jest.Mock).mockResolvedValue(undefined);
  });

  it('allows a user to create, view, and delete a person', async () => {
    // 1. Start at Home
    const { getByText, getByPlaceholderText, findByText, findAllByText } = render(<MockApp />);

    // Verify Home is loaded
    await findByText('Network');
    await findByText('Henüz kimse eklenmemiş.');

    // 2. Navigate to Add Node
    const fab = getByText('+');
    fireEvent.press(fab);

    // Verify Add Node Screen
    await findByText('Ad Soyad *');

    // 3. Fill Form
    fireEvent.changeText(getByPlaceholderText('Ahmet Yılmaz'), 'Test Person');
    fireEvent.changeText(getByPlaceholderText('Yazılım, Finans, Pazarlama...'), 'Technology');
    
    // Select Strength 3
    const strength3 = getByText('3');
    fireEvent.press(strength3);

    // 4. Save
    const saveButton = getByText('✓ Kaydet');
    
    // Mock Alert to auto-press the first button (usually "Tamam")
    jest.spyOn(require('react-native').Alert, 'alert').mockImplementation((title, message, buttons) => {
      if (buttons && buttons.length > 0) {
        buttons[0].onPress && buttons[0].onPress();
      }
    });

    // Update getAllNodes to return the new node when called next
    (nodeService.getAllNodes as jest.Mock).mockResolvedValue([mockNode]);

    fireEvent.press(saveButton);

    // 5. Verify returned to Home and list updated
    await waitFor(() => {
      expect(nodeService.createNode).toHaveBeenCalledWith(expect.objectContaining({
        name: 'Test Person',
        sector: 'Technology',
        relationshipStrength: 3,
        type: 'PERSON'
      }));
    });

    // Should see the new person in the list
    await findByText('Test Person');
    // Technology appears in filter chip and list item, so we expect at least one
    const techElements = await findAllByText('Technology');
    expect(techElements.length).toBeGreaterThan(0);

    // 6. View Details
    fireEvent.press(getByText('Test Person'));

    // Verify Detail Screen
    await findByText('⭐ İlişki Gücü: 3/5');
    await findByText('Test notes');

    // 6.5 Edit Flow
    const editButton = getByText('✏️ Düzenle');
    fireEvent.press(editButton);

    // Verify we are on Add/Edit screen
    await findByText('Ad Soyad *');
    
    // Change Name
    fireEvent.changeText(getByPlaceholderText('Ahmet Yılmaz'), 'Updated Person');
    
    // Save
    const updateButton = getByText('✓ Kaydet');
    fireEvent.press(updateButton);

    // Verify update called
    await waitFor(() => {
      expect(nodeService.updateNode).toHaveBeenCalledWith('123', expect.objectContaining({
        name: 'Updated Person'
      }));
    });

    // 7. Delete Flow
    // Mock Alert for Delete (Cancel, Sil) - we want the second button "Sil"
    const alertSpy = jest.spyOn(require('react-native').Alert, 'alert').mockImplementation((title, message, buttons) => {
        // For delete confirmation, usually the destructive action is the second one
        if (buttons && buttons.length > 1) {
            // Find the one with style 'destructive' or just the second one
            const deleteBtn = buttons.find(b => b.text === 'Sil') || buttons[1];
            deleteBtn.onPress && deleteBtn.onPress();
        }
    });

    // Find Delete button
    const deleteButton = getByText('🗑️ Sil');
    fireEvent.press(deleteButton);

    // Verify delete was called
    await waitFor(() => {
      expect(nodeService.deleteNode).toHaveBeenCalledWith('123');
    });

    // Verify returned to Home (we can check if "Network" header is visible again, though it might still be visible in Detail)
    // Best check is that we are back to a screen that has the FAB "+"
    await findByText('+');
  });
});
