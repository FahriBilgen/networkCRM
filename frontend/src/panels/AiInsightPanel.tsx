import { useEffect, useMemo, useState } from 'react';
import { fetchGoalSuggestions } from '../api/client';
import { mockGraphResponse } from '../mock/data';
import { useSelectionStore } from '../store/selectionStore';
import { NODE_TYPES } from '../types';
import type { GoalSuggestionResponse } from '../types';
import './AiInsightPanel.css';

type SuggestionDisplay = {
  id: string;
  name: string;
  sector?: string | null;
  score?: number | null;
};

export function AiInsightPanel() {
  const selectedNode = useSelectionStore((state) => state.selectedNode);
  const [suggestions, setSuggestions] = useState<GoalSuggestionResponse['suggestions']>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const supportsEdges = useMemo(() => {
    if (!selectedNode) {
      return [];
    }
    return mockGraphResponse.links.filter(
      (edge) => edge.type === 'SUPPORTS' && edge.targetNodeId === selectedNode.id,
    );
  }, [selectedNode]);

  useEffect(() => {
    let mounted = true;
    if (!selectedNode || selectedNode.type !== NODE_TYPES.GOAL) {
      setSuggestions([]);
      setError(null);
      return;
    }
    const goalId = selectedNode.id;

    async function loadSuggestions() {
      setLoading(true);
      setError(null);
      try {
        const response = await fetchGoalSuggestions(goalId);
        if (mounted) {
          setSuggestions(response.suggestions);
        }
      } catch (err) {
        console.warn('Goal suggestion request failed', err);
        if (mounted) {
          setError('AI önerileri alınamadı, mevcut bağlantılar gösteriliyor.');
          setSuggestions([]);
        }
      } finally {
        mounted && setLoading(false);
      }
    }

    loadSuggestions();
    return () => {
      mounted = false;
    };
  }, [selectedNode]);

  if (!selectedNode || selectedNode.type !== NODE_TYPES.GOAL) {
    return (
      <div className="panel ai-panel empty">
        <p>AI önerileri görmek için bir hedef seçin.</p>
      </div>
    );
  }

  const apiList: SuggestionDisplay[] = suggestions.map((item) => ({
    id: item.person.id,
    name: item.person.name,
    sector: item.person.sector,
    score: item.score,
  }));

  const fallbackList: SuggestionDisplay[] = supportsEdges.reduce<SuggestionDisplay[]>((acc, edge) => {
    const person = mockGraphResponse.nodes.find((node) => node.id === edge.sourceNodeId);
    if (!person) {
      return acc;
    }
    acc.push({
      id: edge.id,
      name: person.name,
      sector: person.sector,
      score: edge.relevanceScore ?? 0,
    });
    return acc;
  }, []);

  const listToRender = apiList.length > 0 ? apiList : fallbackList;

  return (
    <div className="panel ai-panel">
      <header>
        <h3>AI Insights</h3>
        <p className="muted">Hedef: {selectedNode.name}</p>
        {loading && <small>Öneriler yükleniyor...</small>}
        {error && <small className="error">{error}</small>}
      </header>
      <section>
        <h4>Önerilen Kişiler</h4>
        <ul className="suggestion-list">
          {listToRender.length === 0 && <p>Henüz öneri yok.</p>}
          {listToRender.map((item) => (
            <li key={item.id}>
              <div>
                <strong>{item.name}</strong>
                {item.sector && <small>{item.sector}</small>}
              </div>
              {typeof item.score === 'number' && (
                <span className="score">{(item.score * 100).toFixed(0)}%</span>
              )}
            </li>
          ))}
        </ul>
      </section>
      <section>
        <h4>Network Durumu</h4>
        <ul className="insight-list">
          <li>
            <span>Fintech sektöründe güçlü.</span>
            <strong>+2 destek</strong>
          </li>
          <li>
            <span>Marketing tarafı zayıf.</span>
            <strong>Eksik</strong>
          </li>
          <li>
            <span>Son 60 günde 1 kişiyle iletişim yok.</span>
            <strong>Uyarı</strong>
          </li>
        </ul>
      </section>
      <footer>
        <button className="primary-button block">AI Öneri Al</button>
      </footer>
    </div>
  );
}
