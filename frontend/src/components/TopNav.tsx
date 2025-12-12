import { useState } from 'react';
import type { KeyboardEvent } from 'react';
import { useAuthStore } from '../store/authStore';
import { useUiStore } from '../store/uiStore';
import { NODE_TYPES } from '../types';
import { useSearchStore } from '../store/searchStore';
import { useSelectionStore } from '../store/selectionStore';
import type { NodeResponse } from '../types';
import './TopNav.css';

export function TopNav() {
  const { email, logout } = useAuthStore();
  const openCreateModal = useUiStore((state) => state.openCreateModal);
  const { search, loading, query } = useSearchStore();
  const selectNode = useSelectionStore((state) => state.selectNode);
  const [input, setInput] = useState(query);

  const handleSearch = () => {
    search(input);
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter') {
      handleSearch();
    }
  };

  const handleSelect = (node: NodeResponse) => {
    selectNode(node);
  };

  return (
    <header className="top-nav">
      <div className="brand">
        <span className="brand-title">Network CRM</span>
        <span className="brand-subtitle">Graph + AI</span>
      </div>
      <div className="nav-actions">
        <div className="nav-search-wrapper">
          <input
            className="nav-search"
            placeholder="Kişi, hedef veya etiket ara"
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={handleKeyDown}
          />
          <button className="ghost-button" onClick={handleSearch} disabled={loading}>
            Ara
          </button>
        </div>
        <SearchFeedback onSelect={handleSelect} />
        <div className="nav-buttons">
          <button className="ghost-button" onClick={() => openCreateModal(NODE_TYPES.PERSON)}>
            Kişi Ekle
          </button>
          <button className="ghost-button" onClick={() => openCreateModal(NODE_TYPES.GOAL)}>
            Hedef Ekle
          </button>
          <button className="primary-button" onClick={() => openCreateModal(NODE_TYPES.VISION)}>
            Vizyon Ekle
          </button>
        </div>
        <div className="user-badge">
          <span className="avatar">{email?.slice(0, 2).toUpperCase()}</span>
          <div className="user-meta">
            <strong>{email}</strong>
            <small>Aktif</small>
          </div>
          <button className="ghost-button logout" onClick={logout}>
            Çıkış
          </button>
        </div>
      </div>
    </header>
  );
}

function SearchFeedback({ onSelect }: { onSelect: (node: NodeResponse) => void }) {
  const { results, query, error } = useSearchStore();
  if (!query.trim()) {
    return null;
  }
  if (error) {
    return <div className="search-feedback error">{error}</div>;
  }
  if (!results.length) {
    return <div className="search-feedback empty">Sonuç bulunamadı.</div>;
  }
  return (
    <div className="search-feedback">
      {results.slice(0, 3).map((node) => (
        <button key={node.id} className="search-result-chip" onClick={() => onSelect(node)}>
          {node.name || 'İsimsiz'}
        </button>
      ))}
      {results.length > 3 && <span className="muted">+{results.length - 3} daha</span>}
    </div>
  );
}
