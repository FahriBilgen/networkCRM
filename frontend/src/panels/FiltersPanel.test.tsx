import '@testing-library/jest-dom';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { describe, it, vi, beforeEach, expect } from 'vitest';
import { FiltersPanel } from './FiltersPanel';
import { filterNodes } from '../api/client';
import { useAuthStore } from '../store/authStore';

vi.mock('../api/client', () => ({
  filterNodes: vi.fn(() => Promise.resolve([{ id: '1' }])),
}));

function authenticate(token: string | null) {
  useAuthStore.setState({
    token,
    email: token ? 'test@example.com' : null,
    loading: false,
    error: null,
    login: async () => {},
    logout: () => {},
  });
}

describe('FiltersPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('disables filter button when not authenticated', () => {
    authenticate(null);
    render(<FiltersPanel />);
    const button = screen.getByRole('button', { name: /Giriş gerekli/i });
    expect(button).toBeDisabled();
  });

  it('submits filters when authenticated', async () => {
    authenticate('token');
    render(<FiltersPanel />);

    fireEvent.change(screen.getByLabelText(/Sektör/i), { target: { value: 'AI' } });
    fireEvent.change(screen.getByPlaceholderText('min'), { target: { value: '2' } });
    fireEvent.change(screen.getByPlaceholderText('maks'), { target: { value: '4' } });
    fireEvent.click(screen.getByLabelText(/mentor/i));
    fireEvent.click(screen.getByLabelText(/Hedefler/i));

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /Filtrele/i }));
    });

    expect(filterNodes).toHaveBeenCalledWith(
      expect.objectContaining({
        sector: 'AI',
        minRelationshipStrength: 2,
        maxRelationshipStrength: 4,
      }),
    );
    expect(screen.getByText(/node eşleşti/i)).toBeInTheDocument();
  });
});
