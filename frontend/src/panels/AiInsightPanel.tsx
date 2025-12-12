import { useEffect, useMemo, useState } from 'react';
import { fetchGoalDiagnostics, fetchGoalSuggestions, fetchRelationshipNudges } from '../api/client';
import { useSelectionStore } from '../store/selectionStore';
import { NODE_TYPES, EDGE_TYPES } from '../types';
import type { GoalSuggestionResponse, GoalNetworkDiagnostics, RelationshipNudge } from '../types';
import { useGraphStore } from '../store/graphStore';
import './AiInsightPanel.css';
import { buildGoalNetworkDiagnostics } from '../utils/goalDiagnostics';

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
  const [diagnostics, setDiagnostics] = useState<GoalNetworkDiagnostics | null>(null);
  const [diagnosticsSource, setDiagnosticsSource] = useState<'server' | 'local' | null>(null);
  const [diagnosticsError, setDiagnosticsError] = useState<string | null>(null);
  const [nudges, setNudges] = useState<RelationshipNudge[]>([]);
  const [nudgesError, setNudgesError] = useState<string | null>(null);
  const graph = useGraphStore((state) => state.graph);

  const supportsEdges = useMemo(() => {
    if (!selectedNode || !graph) {
      return [];
    }
    return graph.links.filter(
      (edge) => edge.type === EDGE_TYPES.SUPPORTS && edge.targetNodeId === selectedNode.id,
    );
  }, [graph, selectedNode]);

  const localDiagnostics = useMemo(() => {
    if (!graph || !selectedNode || selectedNode.type !== NODE_TYPES.GOAL) {
      return null;
    }
    return buildGoalNetworkDiagnostics(graph.nodes, supportsEdges);
  }, [graph, selectedNode, supportsEdges]);

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

  useEffect(() => {
    let mounted = true;
    if (!selectedNode || selectedNode.type !== NODE_TYPES.GOAL) {
      setDiagnostics(null);
      setDiagnosticsSource(null);
      setDiagnosticsError(null);
      return;
    }
    const goalId = selectedNode.id;
    setDiagnostics(null);
    setDiagnosticsSource(null);
    setDiagnosticsError(null);

    fetchGoalDiagnostics(goalId)
      .then((response) => {
        if (!mounted) {
          return;
        }
        setDiagnostics({
          readiness: response.readiness,
          sectorHighlights: response.sectorHighlights,
          riskAlerts: response.riskAlerts,
        });
        setDiagnosticsSource('server');
      })
      .catch((err) => {
        console.warn('Goal diagnostics request failed', err);
        if (!mounted) {
          return;
        }
        if (localDiagnostics) {
          setDiagnostics(localDiagnostics);
          setDiagnosticsSource('local');
          setDiagnosticsError('Sunucu analizi alinamadi; yerel graph verisi kullaniliyor.');
        } else {
          setDiagnostics(null);
          setDiagnosticsSource(null);
          setDiagnosticsError('Analiz icin yeterli veri yok.');
        }
      });

    return () => {
      mounted = false;
    };
  }, [selectedNode?.id, selectedNode?.type, localDiagnostics]);

  useEffect(() => {
    let mounted = true;
    if (!selectedNode || selectedNode.type !== NODE_TYPES.GOAL) {
      setNudges([]);
      setNudgesError(null);
      return;
    }
    setNudgesError(null);
    fetchRelationshipNudges(5)
      .then((response) => {
        if (!mounted) {
          return;
        }
        setNudges(response.nudges);
      })
      .catch((err) => {
        console.warn('Relationship nudge request failed', err);
        if (mounted) {
          setNudges([]);
          setNudgesError('Iliski hatirlatmalari alinamadi.');
        }
      });
    return () => {
      mounted = false;
    };
  }, [selectedNode?.id, selectedNode?.type]);

  if (!selectedNode || selectedNode.type !== NODE_TYPES.GOAL) {
    return (
      <div className="panel ai-panel empty">
        <p>AI önerilerini görmek için bir hedef seçin.</p>
      </div>
    );
  }

  const apiList: SuggestionDisplay[] = suggestions.map((item) => ({
    id: item.person.id,
    name: item.person.name,
    sector: item.person.sector,
    score: item.score,
  }));

  const fallbackList: SuggestionDisplay[] = supportsEdges
    .reduce<SuggestionDisplay[]>((acc, edge) => {
      const person = graph.nodes.find((node) => node.id === edge.sourceNodeId);
      if (!person) {
        return acc;
      }
      acc.push({
        id: edge.id,
        name: person.name ?? 'İsimsiz',
        sector: person.sector ?? undefined,
        score: edge.relevanceScore ?? undefined,
      });
      return acc;
    }, [])
    .sort((a, b) => (b.score ?? 0) - (a.score ?? 0));

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
      <section className="network-insights">
        <h4>Network Durumu</h4>
        {diagnosticsSource && (
          <small className="muted">
            {diagnosticsSource === 'server' ? 'AI analizi' : 'Yerel graph analizi'}
          </small>
        )}
        {diagnosticsError && <small className="error">{diagnosticsError}</small>}
        {diagnostics ? (
          <>
            <div className={`readiness-pill ${diagnostics.readiness.level}`}>
              <div>
                <strong>{diagnostics.readiness.message}</strong>
                <small>Skor: {(diagnostics.readiness.score * 100).toFixed(0)}%</small>
              </div>
            </div>
            <ul className="insight-list">
              {diagnostics.readiness.summary.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          </>
        ) : (
          <p className="muted">Analiz icin yeterli veri yok.</p>
        )}
      </section>
      <section>
        <h4>Sektor Analizi</h4>
        <ul className="insight-list">
          {!diagnostics && <li>Veri bekleniyor.</li>}
          {diagnostics?.sectorHighlights.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </section>
      <section>
        <h4>Risk Uyarilari</h4>
        <ul className="insight-list warning">
          {!diagnostics && <li>Uyarilar icin destek verisi bekleniyor.</li>}
          {diagnostics?.riskAlerts.map((item, index) => (
            <li key={`${item}-${index}`}>{item}</li>
          ))}
        </ul>
      </section>
      <section>
        <h4>Iliski Hatirlatmalari</h4>
        {nudgesError && <small className="error">{nudgesError}</small>}
        <ul className="nudge-list">
          {nudges.length === 0 && <li>Hatirlatma yok.</li>}
          {nudges.map((nudge) => (
            <li key={`${nudge.person.id}-${nudge.edgeType}-${nudge.targetName ?? 'none'}`}>
              <div className="nudge-header">
                <strong>{nudge.person.name}</strong>
                {nudge.targetName && <small>{nudge.targetName}</small>}
              </div>
              <ul>
                {nudge.reasons.map((reason) => (
                  <li key={reason}>{reason}</li>
                ))}
              </ul>
            </li>
          ))}
        </ul>
      </section>
      <footer>
        <button className="primary-button block">AI Önerisi Al</button>
      </footer>
    </div>
  );
}
