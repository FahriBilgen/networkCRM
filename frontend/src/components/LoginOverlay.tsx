import { useState } from 'react';
import type { FormEvent } from 'react';
import { useAuthStore } from '../store/authStore';
import './LoginOverlay.css';

export function LoginOverlay() {
  const [isRegistering, setIsRegistering] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const { login, register, loading, error } = useAuthStore();

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    try {
      if (isRegistering) {
        await register(email, password);
      } else {
        await login(email, password);
      }
    } catch {
      /* error state handled in store */
    }
  };

  return (
    <div className="login-overlay">
      <form className="login-card" onSubmit={handleSubmit}>
        <h2>Network CRM</h2>
        <p>{isRegistering ? 'Hesap oluşturun' : 'Devam etmek için giriş yapın'}</p>
        <label>
          E-posta
          <input value={email} onChange={(event) => setEmail(event.target.value)} type="email" required />
        </label>
        <label>
          Şifre
          <input
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            type="password"
            required
            minLength={isRegistering ? 6 : undefined}
          />
        </label>
        {error && <p className="error-text">{error}</p>}
        <button type="submit" disabled={loading}>
          {loading ? 'İşlem yapılıyor...' : (isRegistering ? 'Kayıt Ol' : 'Giriş Yap')}
        </button>
        
        <div className="auth-toggle">
          <button 
            type="button" 
            className="text-button" 
            onClick={() => {
              setIsRegistering(!isRegistering);
              useAuthStore.setState({ error: null });
            }}
          >
            {isRegistering ? 'Zaten hesabınız var mı? Giriş yapın' : 'Hesabınız yok mu? Kayıt olun'}
          </button>
        </div>
      </form>
    </div>
  );
}
