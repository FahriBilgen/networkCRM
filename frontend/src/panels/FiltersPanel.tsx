import { useState } from 'react';
import { filterNodes } from '../api/client';
import { NODE_TYPES } from '../types';
import type { NodeType } from '../types';
import { useAuthStore } from '../store/authStore';
import { useGraphStore } from '../store/graphStore';
import './FiltersPanel.css';

const sectors = ['Fintech', 'Marketing', 'AI', 'SaaS'];
const tags = ['mentor', 'yatirimci', 'growth', 'product'];
const typeOptions: { label: string; value: NodeType }[] = [
  { label: 'Kişiler', value: NODE_TYPES.PERSON },
  { label: 'Hedefler', value: NODE_TYPES.GOAL },
  { label: 'Projeler', value: NODE_TYPES.PROJECT },
  { label: 'Vizyondakiler', value: NODE_TYPES.VISION },
];

type MessageKind = 'info' | 'error';

export function FiltersPanel() {
  const token = useAuthStore((state) => state.token);
  const setFilteredNodeIds = useGraphStore((state) => state.setFilteredNodeIds);
  const clearFilteredNodeIds = useGraphStore((state) => state.clearFilteredNodeIds);
  const [sector, setSector] = useState('');
  const [minStrength, setMinStrength] = useState<number | ''>('');
  const [maxStrength, setMaxStrength] = useState<number | ''>('');
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [selectedTypes, setSelectedTypes] = useState<NodeType[]>(typeOptions.map((o) => o.value));
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [messageKind, setMessageKind] = useState<MessageKind>('info');
  const [summary, setSummary] = useState<string | null>(null);

  const toggleTag = (tag: string) => {
    setSelectedTags((prev) => (prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]));
  };

  const toggleType = (type: NodeType) => {
    setSelectedTypes((prev) => (prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type]));
  };

  const resetFilters = () => {
    setSector('');
    setMinStrength('');
    setMaxStrength('');
    setSelectedTags([]);
    setSelectedTypes(typeOptions.map((o) => o.value));
    setMessage(null);
    clearFilteredNodeIds();
    setSummary(null);
  };

  const handleFilter = async () => {
    setLoading(true);
    setMessage(null);
    try {
      const result = await filterNodes({
        sector: sector || undefined,
        minRelationshipStrength: minStrength === '' ? undefined : Number(minStrength),
        maxRelationshipStrength: maxStrength === '' ? undefined : Number(maxStrength),
        tags: selectedTags.length ? selectedTags : undefined,
        types: selectedTypes,
      });
      const ids = result.map((node) => node.id);
      setFilteredNodeIds(ids);
      setMessageKind('info');
      if (result.length === 0) {
        setMessage('Eşleşen node yok. Graph tüm nodları gri olarak gösteriyor.');
        setSummary(null);
      } else {
        setMessage(`${result.length} node eşleşti. Graph bu nodları parlak gösteriyor.`);
        const counts: Partial<Record<NodeType, number>> = {};
        result.forEach((node) => {
          counts[node.type] = (counts[node.type] ?? 0) + 1;
        });
        const detail = Object.entries(counts)
          .map(([type, count]) => `${type.toLowerCase()}: ${count}`)
          .join(' • ');
        setSummary(detail);
      }
    } catch (error) {
      console.warn('Filter request failed', error);
      setMessageKind('error');
      setMessage('Filtre çalıştırılırken hata oluştu.');
      clearFilteredNodeIds();
      setSummary(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="panel filters-panel">
      <header>
        <h3>Filtreler</h3>
        <button className="ghost-button" onClick={resetFilters} disabled={loading}>
          Temizle
        </button>
      </header>
      <div className="filter-group">
        <label htmlFor="sector">Sektör</label>
        <select id="sector" value={sector} onChange={(event) => setSector(event.target.value)}>
          <option value="">Tümü</option>
          {sectors.map((sectorOption) => (
            <option key={sectorOption}>{sectorOption}</option>
          ))}
        </select>
      </div>
      <div className="filter-group">
        <label>İlişki Gücü</label>
        <div className="range-group">
          <input
            type="number"
            min={0}
            max={5}
            placeholder="min"
            value={minStrength}
            onChange={(event) => setMinStrength(event.target.value === '' ? '' : Number(event.target.value))}
          />
          <span>-</span>
          <input
            type="number"
            min={0}
            max={5}
            placeholder="maks"
            value={maxStrength}
            onChange={(event) => setMaxStrength(event.target.value === '' ? '' : Number(event.target.value))}
          />
        </div>
      </div>
      <div className="filter-group">
        <label>Etiketler</label>
        <div className="tag-list">
          {tags.map((tag) => {
            const checked = selectedTags.includes(tag);
            return (
              <label key={tag}>
                <input type="checkbox" checked={checked} onChange={() => toggleTag(tag)} /> {tag}
              </label>
            );
          })}
        </div>
      </div>
      <div className="filter-group">
        <label>Node Tipi</label>
        <div className="tag-list">
          {typeOptions.map((type) => {
            const checked = selectedTypes.includes(type.value);
            return (
              <label key={type.value}>
                <input type="checkbox" checked={checked} onChange={() => toggleType(type.value)} /> {type.label}
              </label>
            );
          })}
        </div>
      </div>
      <footer>
        <button className="primary-button block" onClick={handleFilter} disabled={!token || loading}>
          {!token ? 'Giriş gerekli' : loading ? 'Uygulanıyor...' : 'Filtrele'}
        </button>
        {message && <p className={`filter-message ${messageKind}`}>{message}</p>}
        {summary && <p className="filter-summary">{summary}</p>}
      </footer>
    </div>
  );
}
