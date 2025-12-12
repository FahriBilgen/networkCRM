import { useState } from 'react';
import type { FormEvent } from 'react';
import { useAuthStore } from '../store/authStore';
import './LoginOverlay.css';

export function LoginOverlay() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const { login, loading, error } = useAuthStore();

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    try {
      await login(email, password);
    } catch {
      /* error state handled in store */
    }
  };

  return (
    <div className="login-overlay">
      <form className="login-card" onSubmit={handleSubmit}>
        <h2>Network CRM</h2>
        <p>Devam etmek için giriş yapın</p>
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
          />
        </label>
        {error && <p className="error-text">{error}</p>}
        <button type="submit" disabled={loading}>
          {loading ? 'Giriş yapılıyor...' : 'Giriş Yap'}
        </button>
        <small>Test kullanıcıları için README’deki scripti kullanabilirsiniz.</small>
      </form>
    </div>
  );
}
