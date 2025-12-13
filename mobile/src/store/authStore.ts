import { create } from 'zustand';
import * as SecureStore from 'expo-secure-store';
import api from '../services/api';
import { AuthResponse, LoginRequest, RegisterRequest, User } from '../types';

interface AuthState {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  error: string | null;
  login: (data: LoginRequest) => Promise<void>;
  register: (data: RegisterRequest) => Promise<void>;
  logout: () => Promise<void>;
  loadUser: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: null,
  isLoading: true,
  error: null,

  login: async (credentials) => {
    set({ isLoading: true, error: null });
    try {
      const response = await api.post<AuthResponse>('/auth/login', credentials);
      const { token, user } = response.data;
      
      await SecureStore.setItemAsync('auth_token', token);
      // Store user info if needed, or just rely on state
      await SecureStore.setItemAsync('user_info', JSON.stringify(user));

      set({ user, token, isLoading: false });
    } catch (error: any) {
      set({ 
        error: error.response?.data?.message || 'Giriş başarısız', 
        isLoading: false 
      });
      throw error;
    }
  },

  register: async (data) => {
    set({ isLoading: true, error: null });
    try {
      const response = await api.post<AuthResponse>('/auth/register', data);
      const { token, user } = response.data;
      
      await SecureStore.setItemAsync('auth_token', token);
      await SecureStore.setItemAsync('user_info', JSON.stringify(user));

      set({ user, token, isLoading: false });
    } catch (error: any) {
      set({ 
        error: error.response?.data?.message || 'Kayıt başarısız', 
        isLoading: false 
      });
      throw error;
    }
  },

  logout: async () => {
    await SecureStore.deleteItemAsync('auth_token');
    await SecureStore.deleteItemAsync('user_info');
    set({ user: null, token: null });
  },

  loadUser: async () => {
    set({ isLoading: true });
    try {
      const token = await SecureStore.getItemAsync('auth_token');
      const userInfoStr = await SecureStore.getItemAsync('user_info');
      
      if (token && userInfoStr) {
        const user = JSON.parse(userInfoStr);
        // Optionally verify token with backend here: await api.get('/auth/me');
        set({ token, user, isLoading: false });
      } else {
        set({ token: null, user: null, isLoading: false });
      }
    } catch (error) {
      set({ token: null, user: null, isLoading: false });
    }
  },
}));
