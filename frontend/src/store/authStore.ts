import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { setAuthToken, signIn, signUp } from '../api/client';

interface AuthState {
  token: string | null;
  email: string | null;
  loading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      email: null,
      loading: false,
      error: null,
      login: async (email: string, password: string) => {
        set({ loading: true, error: null });
        try {
          const { data } = await signIn(email, password);
          setAuthToken(data.accessToken);
          set({ token: data.accessToken, email, loading: false });
        } catch (error) {
          console.error('Login failed', error);
          set({ error: 'Giriş başarısız. Bilgileri kontrol edin.', loading: false, token: null });
          throw error;
        }
      },
      register: async (email: string, password: string) => {
        set({ loading: true, error: null });
        try {
          const { data } = await signUp(email, password);
          setAuthToken(data.accessToken);
          set({ token: data.accessToken, email, loading: false });
        } catch (error) {
          console.error('Registration failed', error);
          set({ error: 'Kayıt başarısız. E-posta kullanımda olabilir.', loading: false, token: null });
          throw error;
        }
      },
      logout: () => {
        setAuthToken(null);
        set({ token: null, email: null });
      },
    }),
    {
      name: 'auth-store',
      onRehydrateStorage: () => (state) => {
        if (state?.token) {
          setAuthToken(state.token);
        }
      },
    },
  ),
);
