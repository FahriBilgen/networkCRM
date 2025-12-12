import { useEffect, useMemo, useState } from 'react';
import {
  createFavoritePath,
  deleteFavoritePath,
  deleteNode,
  fetchGoalPathSuggestions,
  fetchNodeProximity,
  filterNodes,
  linkPersonToGoal,
  updateNode,
} from '../api/client';
import { useSelectionStore } from '../store/selectionStore';
import { useRefreshStore } from '../store/dataRefreshStore';
import { useUiStore } from '../store/uiStore';
import { useAuthStore } from '../store/authStore';
import { useGraphStore } from '../store/graphStore';
import { NODE_TYPES } from '../types';
import type { GoalPathSuggestion, NodeProximityResponse, NodeResponse, NodeType } from '../types';
import './NodeDetailPanel.css';
import { buildNodeRequestPayload } from '../utils/nodePayload';
import { computeGoalPathSuggestions } from '../utils/goalPathSuggestions';

const typeLabels: Record<NodeType, string> = {
  PERSON: 'Kisi',
  VISION: 'Vision',
  GOAL: 'Goal',
  PROJECT: 'Project',
};

export function NodeDetailPanel() {
  const selectedNode = useSelectionStore((state) => state.selectedNode);
  const selectNode = useSelectionStore((state) => state.selectNode);
  const openEditModal = useUiStore((state) => state.openEditModal);
  const triggerGraphRefresh = useRefreshStore((state) => state.triggerGraphRefresh);
  const triggerVisionRefresh = useRefreshStore((state) => state.triggerVisionRefresh);
  const isAuthenticated = useAuthStore((state) => Boolean(state.token));
  const graph = useGraphStore((state) => state.graph);
  const setGraph = useGraphStore((state) => state.setGraph);
  const filteredNodeIds = useGraphStore((state) => state.filteredNodeIds);
  const setFilteredNodeIds = useGraphStore((state) => state.setFilteredNodeIds);
  const clearFilteredNodeIds = useGraphStore((state) => state.clearFilteredNodeIds);
  const setHighlightPath = useGraphStore((state) => state.setHighlightPath);
  const clearHighlightPath = useGraphStore((state) => state.clearHighlightPath);
  const favoritePaths = useGraphStore((state) => state.favoritePaths);
  const addFavoritePath = useGraphStore((state) => state.addFavoritePath);
  const removeFavoritePath = useGraphStore((state) => state.removeFavoritePath);
  const applyFavoritePath = useGraphStore((state) => state.applyFavoritePath);

  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [peopleOptions, setPeopleOptions] = useState<NodeResponse[]>([]);
  const [peopleLoading, setPeopleLoading] = useState(false);
  const [peopleError, setPeopleError] = useState<string | null>(null);
  const [linkPersonId, setLinkPersonId] = useState('');
  const [linkStrength, setLinkStrength] = useState<number | ''>('');
  const [linkNotes, setLinkNotes] = useState('');
  const [linkSubmitting, setLinkSubmitting] = useState(false);
  const [linkFeedback, setLinkFeedback] = useState<string | null>(null);
  const [linkError, setLinkError] = useState<string | null>(null);
  const [proximity, setProximity] = useState<NodeProximityResponse | null>(null);
  const [proximityLoading, setProximityLoading] = useState(false);
  const [proximityError, setProximityError] = useState<string | null>(null);
  const [proximityKey, setProximityKey] = useState(0);
  const [timelineNote, setTimelineNote] = useState('');
  const [timelineDate, setTimelineDate] = useState(() => defaultTimelineDate());
  const [timelineSaving, setTimelineSaving] = useState(false);
  const [timelineError, setTimelineError] = useState<string | null>(null);
  const [timelineFeedback, setTimelineFeedback] = useState<string | null>(null);
  const [pathFeedback, setPathFeedback] = useState<string | null>(null);
  const [pathError, setPathError] = useState<string | null>(null);
  const [pathSuggestions, setPathSuggestions] = useState<GoalPathSuggestion[]>([]);
  const [pathLoading, setPathLoading] = useState(false);
  const [pathSource, setPathSource] = useState<'local' | 'server'>('local');

  const refreshProximity = () => setProximityKey((prev) => prev + 1);
  const timelineEntries = useMemo(() => extractTimelineEntries(selectedNode), [selectedNode]);

  useEffect(() => {
    if (!selectedNode || selectedNode.type !== NODE_TYPES.GOAL || !isAuthenticated) {
      setPeopleOptions([]);
      setPeopleLoading(false);
      setPeopleError(null);
      setLinkPersonId('');
      setLinkStrength('');
      setLinkNotes('');
      setLinkFeedback(null);
      setLinkError(null);
      return;
    }

    setPeopleLoading(true);
    setPeopleError(null);
    filterNodes({ type: NODE_TYPES.PERSON })
      .then((data) => {
        setPeopleOptions(data);
      })
      .catch((err) => {
        console.warn('Unable to load people for linking', err);
        setPeopleError('Kisiler getirilemedi.');
      })
      .finally(() => setPeopleLoading(false));
  }, [selectedNode, isAuthenticated]);

  useEffect(() => {
    if (!selectedNode || !isAuthenticated) {
      setProximity(null);
      setProximityError(null);
      setProximityLoading(false);
      return;
    }
    setProximityLoading(true);
    setProximityError(null);
    fetchNodeProximity(selectedNode.id)
      .then((data) => setProximity(data))
      .catch((err) => {
        console.warn('Unable to load proximity insight', err);
        setProximityError('Yakinlik verisi getirilemedi.');
      })
      .finally(() => setProximityLoading(false));
  }, [selectedNode, isAuthenticated, proximityKey]);

  useEffect(() => {
    setTimelineNote('');
    setTimelineDate(defaultTimelineDate());
    setTimelineError(null);
    setTimelineFeedback(null);
    setPathFeedback(null);
    setPathError(null);
    setPathSuggestions([]);
    setPathSource('local');
    setPathLoading(false);
  }, [selectedNode?.id]);

  useEffect(() => {
    if (!selectedNode || selectedNode.type !== NODE_TYPES.GOAL) {
      clearHighlightPath();
    }
  }, [selectedNode?.id, selectedNode?.type, clearHighlightPath]);

  const nodeMap = useMemo(() => {
    if (!graph?.nodes) {
      return new Map<string, NodeResponse>();
    }
    return new Map(graph.nodes.map((node) => [node.id, node]));
  }, [graph]);

  const fallbackPathSuggestions = useMemo(() => {
    if (!graph || !selectedNode || selectedNode.type !== NODE_TYPES.GOAL) {
      return [];
    }
    return computeGoalPathSuggestions({
      goalId: selectedNode.id,
      graph,
      maxDepth: 3,
      maxSuggestions: 4,
    });
  }, [graph, selectedNode]);

  useEffect(() => {
    if (!selectedNode || selectedNode.type !== NODE_TYPES.GOAL) {
      setPathSuggestions([]);
      setPathSource('local');
      return;
    }
    setPathSuggestions(fallbackPathSuggestions);
    setPathSource('local');
  }, [fallbackPathSuggestions, selectedNode?.id, selectedNode?.type]);

  useEffect(() => {
    if (!selectedNode || selectedNode.type !== NODE_TYPES.GOAL || !isAuthenticated) {
      if (!isAuthenticated) {
        setPathError(null);
      }
      setPathLoading(false);
      return;
    }

    let cancelled = false;
    setPathLoading(true);
    setPathError(null);

    fetchGoalPathSuggestions(selectedNode.id, { maxDepth: 3, limit: 4 })
      .then((response) => {
        if (cancelled) {
          return;
        }
        if (response?.suggestions?.length) {
          setPathSuggestions(response.suggestions);
        } else {
          setPathSuggestions([]);
        }
        setPathSource('server');
      })
      .catch((err) => {
        if (cancelled) {
          return;
        }
        console.warn('Goal path suggestions unavailable', err);
        setPathSuggestions(fallbackPathSuggestions);
        setPathSource('local');
        setPathError('Sunucu onerileri getirilemedi; yerel graph analizi kullaniliyor.');
      })
      .finally(() => {
        if (!cancelled) {
          setPathLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [selectedNode?.id, selectedNode?.type, isAuthenticated, fallbackPathSuggestions]);

  const goalFavoritePaths = useMemo(() => {
    if (!favoritePaths?.length || !selectedNode || selectedNode.type !== NODE_TYPES.GOAL) {
      return [];
    }
    return favoritePaths.filter((fav) => !fav.goalId || fav.goalId === selectedNode.id);
  }, [favoritePaths, selectedNode]);

  const highlightBySector = () => {
    if (!selectedNode?.sector || !graph?.nodes?.length) {
      return;
    }
    const target = selectedNode.sector.toLowerCase();
    const ids = graph.nodes
      .filter((node) => node.sector?.toLowerCase() === target)
      .map((node) => node.id);
    setFilteredNodeIds(ids);
  };

  const highlightByTag = (tag: string) => {
    if (!graph?.nodes?.length) {
      return;
    }
    const lowered = tag.toLowerCase();
    const ids = graph.nodes
      .filter((node) => node.tags?.some((nodeTag) => nodeTag.toLowerCase() === lowered))
      .map((node) => node.id);
    setFilteredNodeIds(ids);
  };

  if (!selectedNode) {
    return (
      <div className="panel node-detail-panel empty">
        <p>Graph uzerinden bir node sectiginizde detaylar burada gorunecek.</p>
      </div>
    );
  }

  const matchesFilter = !filteredNodeIds || filteredNodeIds.includes(selectedNode.id);
  const filterHint = filteredNodeIds
    ? matchesFilter
      ? 'Bu node filtre sonucunda vurgulaniyor.'
      : 'Bu node filtre kriterlerine uymuyor; graph uzerinde gri gosteriliyor.'
    : null;

  const handleLinkSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!selectedNode) {
      return;
    }
    if (!linkPersonId) {
      setLinkError('Lutfen bir kisi secin.');
      return;
    }

    setLinkSubmitting(true);
    setLinkFeedback(null);
    setLinkError(null);
    try {
      const payload = {
        personId: linkPersonId,
        relationshipStrength: linkStrength === '' ? undefined : linkStrength,
        notes: linkNotes ? linkNotes : undefined,
        addedByUser: true,
      };
      await linkPersonToGoal(selectedNode.id, payload);
      setLinkFeedback('Baglanti kaydedildi.');
      setLinkPersonId('');
      setLinkStrength('');
      setLinkNotes('');
      triggerGraphRefresh();
      refreshProximity();
    } catch (err) {
      console.warn('Failed to create SUPPORTS edge', err);
      setLinkError('Baglanti olusturulamadi.');
    } finally {
      setLinkSubmitting(false);
    }
  };

  const persistTimelineEntries = async (nextTimeline: TimelineEntry[], successMessage: string) => {
    if (!selectedNode || selectedNode.type !== NODE_TYPES.PERSON) {
      return false;
    }
    setTimelineSaving(true);
    setTimelineError(null);
    setTimelineFeedback(null);
    try {
      const payload = buildNodeRequestPayload(selectedNode, {
        properties: {
          ...(selectedNode.properties ?? {}),
          timeline: nextTimeline,
        },
      });
      const updated = await updateNode(selectedNode.id, payload);
      const mergedNode: NodeResponse = {
        ...selectedNode,
        ...updated,
        properties: payload.properties,
      };
      selectNode(mergedNode);
      if (graph) {
        setGraph({
          ...graph,
          nodes: graph.nodes.map((node) => (node.id === mergedNode.id ? mergedNode : node)),
        });
      }
      setTimelineFeedback(successMessage);
      triggerGraphRefresh();
      return true;
    } catch (err) {
      console.warn('Failed to persist timeline change', err);
      setTimelineError('Timeline kaydi kaydedilemedi.');
      return false;
    } finally {
      setTimelineSaving(false);
    }
  };

  const handleTimelineSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!selectedNode || selectedNode.type !== NODE_TYPES.PERSON) {
      return;
    }
    const trimmed = timelineNote.trim();
    if (!trimmed) {
      setTimelineError('Bir not girin.');
      return;
    }
    const entry = createTimelineEntry(trimmed, timelineDate);
    const nextTimeline = [entry, ...timelineEntries].slice(0, 25);
    const success = await persistTimelineEntries(nextTimeline, 'Timeline kaydi eklendi.');
    if (success) {
      setTimelineNote('');
      setTimelineDate(defaultTimelineDate());
    }
  };

  const handleTimelineRemove = async (entryId: string) => {
    if (!selectedNode || selectedNode.type !== NODE_TYPES.PERSON) {
      return;
    }
    const nextTimeline = timelineEntries.filter((entry) => entry.id !== entryId);
    await persistTimelineEntries(nextTimeline, 'Timeline kaydi silindi.');
  };

  const formatPath = (pathIds: string[]) => {
    return pathIds
      .map((id) => nodeMap.get(id)?.name ?? id)
      .join(' → ');
  };

  const handleFavoriteAdd = async (suggestion: GoalPathSuggestion) => {
    if (!selectedNode) {
      return;
    }
    const label = `${selectedNode.name ?? 'Hedef'} -> ${suggestion.person.name ?? 'Path'}`;
    setPathError(null);
    setPathFeedback(null);
    try {
      const response = await createFavoritePath({
        goalId: selectedNode.id,
        label,
        nodeIds: suggestion.pathNodeIds,
      });
      addFavoritePath(response);
      setPathFeedback('Favorilere eklendi.');
    } catch (err) {
      console.warn('Favorite path create failed', err);
      setPathError('Favori kaydedilemedi.');
    }
  };

  const handleFavoriteRemove = async (favoriteId: string) => {
    setPathError(null);
    setPathFeedback(null);
    try {
      await deleteFavoritePath(favoriteId);
      removeFavoritePath(favoriteId);
      setPathFeedback('Favori silindi.');
    } catch (err) {
      console.warn('Favorite path delete failed', err);
      setPathError('Favori silinemedi.');
    }
  };

  return (
    <div className="panel node-detail-panel">
      <header>
        <span className={`badge badge-${selectedNode.type.toLowerCase()}`}>{typeLabels[selectedNode.type]}</span>
        <h3>{selectedNode.name}</h3>
        {selectedNode.company && <p className="muted">{selectedNode.company}</p>}
      </header>
      {filterHint && (
        <div className={`filter-alert ${matchesFilter ? 'active' : 'dimmed'}`}>
          <span>{filterHint}</span>
          <button className="ghost-button" onClick={clearFilteredNodeIds}>
            Filtreyi temizle
          </button>
        </div>
      )}
      {selectedNode.description && <p>{selectedNode.description}</p>}
      <section>
        <h4>Ozet nitelikler</h4>
        <dl>
          {selectedNode.sector && (
            <>
              <dt>Sektor</dt>
              <dd>
                <div className="value-with-action">
                  <span>{selectedNode.sector}</span>
                  <button type="button" className="chip-button secondary" onClick={highlightBySector}>
                    Grafikte vurgula
                  </button>
                </div>
              </dd>
            </>
          )}
          {selectedNode.relationshipStrength !== undefined && (
            <>
              <dt>Iliski Gucu</dt>
              <dd>{selectedNode.relationshipStrength}/5</dd>
            </>
          )}
          {selectedNode.tags?.length ? (
            <>
              <dt>Etiketler</dt>
              <dd className="tags">
                {selectedNode.tags.map((tag) => (
                  <button type="button" key={tag} className="chip-button" onClick={() => highlightByTag(tag)}>
                    {tag}
                  </button>
                ))}
              </dd>
            </>
          ) : null}
          {selectedNode.dueDate && (
            <>
              <dt>Bitis</dt>
              <dd>{selectedNode.dueDate}</dd>
            </>
          )}
        </dl>
      </section>

      {selectedNode.type === NODE_TYPES.PERSON && (
        <section className="timeline-section">
          <h4>Zaman Cizelgesi</h4>
          {isAuthenticated ? (
            <form className="timeline-form" onSubmit={handleTimelineSubmit}>
              <label>
                Tarih
                <input
                  type="date"
                  value={timelineDate}
                  onChange={(event) => setTimelineDate(event.target.value)}
                />
              </label>
              <label>
                Not
                <textarea
                  rows={2}
                  value={timelineNote}
                  onChange={(event) => setTimelineNote(event.target.value)}
                  placeholder="Son gorusme notu..."
                />
              </label>
              <button className="ghost-button" type="submit" disabled={timelineSaving || !timelineNote.trim()}>
                {timelineSaving ? 'Kaydediliyor...' : 'Kaydi ekle'}
              </button>
              {timelineError && <small className="error-text">{timelineError}</small>}
              {timelineFeedback && <small className="success-text">{timelineFeedback}</small>}
            </form>
          ) : (
            <p className={timelineEntries.length === 0 ? 'muted' : ''}>Not eklemek icin giris yapin.</p>
          )}
          <ul className="timeline-list">
            {timelineEntries.length === 0 && <li>Henuz zaman bazli kayit yok.</li>}
            {timelineEntries.map((entry) => (
              <li key={entry.id}>
                <div className="timeline-meta">
                  <span className="timeline-date">{entry.date}</span>
                  {isAuthenticated && (
                    <button
                      type="button"
                      className="ghost-button danger"
                      onClick={() => handleTimelineRemove(entry.id)}
                      disabled={timelineSaving}
                    >
                      Kaydi Sil
                    </button>
                  )}
                </div>
                <p>{entry.note}</p>
              </li>
            ))}
          </ul>
        </section>
      )}

      {selectedNode.type === NODE_TYPES.GOAL && (
        <section className="link-section">
          <h4>Kisiyi hedefe bagla</h4>
          {!isAuthenticated ? (
            <p className="muted">Bu islemi yapabilmek icin giris yapin.</p>
          ) : (
            <form className="link-form" onSubmit={handleLinkSubmit}>
              <label>
                Kisi
                <select
                  value={linkPersonId}
                  onChange={(event) => setLinkPersonId(event.target.value)}
                  disabled={peopleLoading || peopleOptions.length === 0}
                >
                  <option value="">Bir kisi secin</option>
                  {peopleOptions.map((person) => (
                    <option key={person.id} value={person.id}>
                      {person.name ?? 'Isimsiz Kisi'}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Iliski Gucu (0-5)
                <input
                  type="number"
                  min={0}
                  max={5}
                  value={linkStrength}
                  onChange={(event) =>
                    setLinkStrength(event.target.value === '' ? '' : Number(event.target.value))
                  }
                />
              </label>
              <label>
                Not
                <textarea value={linkNotes} onChange={(event) => setLinkNotes(event.target.value)} rows={2} />
              </label>
              <button className="primary-button" type="submit" disabled={linkSubmitting || !linkPersonId}>
                {linkSubmitting ? 'Baglaniyor...' : 'Baglanti Olustur'}
              </button>
              {peopleLoading && <small>Liste yukleniyor...</small>}
              {peopleError && <small className="error-text">{peopleError}</small>}
              {linkError && <small className="error-text">{linkError}</small>}
              {linkFeedback && <small className="success-text">{linkFeedback}</small>}
            </form>
          )}
        </section>
      )}

      {selectedNode.type === NODE_TYPES.GOAL && (pathSuggestions.length > 0 || pathLoading) && (
        <section className="path-section">
          <div className="path-section-header">
            <h4>Path-based oneriler</h4>
            {pathLoading ? (
              <small>Yukleniyor...</small>
            ) : (
              <small className="muted">{pathSource === 'server' ? 'Sunucu analizi' : 'Yerel graph analizi'}</small>
            )}
          </div>
          <p className="muted">Bu hedefe 2-3 adimda erisilebilecek kisiler.</p>
          {pathFeedback && <small className="success-text">{pathFeedback}</small>}
          {pathError && <small className="error-text">{pathError}</small>}
          <ul className="path-list">
            {pathSuggestions.map((suggestion) => (
              <li key={suggestion.person.id}>
                <div className="path-header">
                  <div>
                    <strong>{suggestion.person.name ?? 'Isimsiz Kisi'}</strong>
                    {suggestion.person.sector && <small>{suggestion.person.sector}</small>}
                  </div>
                  <span className="path-distance">{suggestion.distance}-hop</span>
                </div>
                <p className="path-sequence">{formatPath(suggestion.pathNodeIds)}</p>
                <div className="path-actions">
                  <button
                    type="button"
                    className="chip-button secondary"
                    onClick={() => setHighlightPath(suggestion.pathNodeIds)}
                  >
                    Grafikte goster
                  </button>
                  <button
                    type="button"
                    className="chip-button secondary"
                    onClick={() => handleFavoriteAdd(suggestion)}
                  >
                    Favorilere ekle
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}

      {selectedNode.type === NODE_TYPES.GOAL && goalFavoritePaths.length > 0 && (
        <section className="favorite-paths">
          <h4>Favori patikalar</h4>
          <ul className="favorite-path-list">
            {goalFavoritePaths.map((favorite) => (
              <li key={favorite.id}>
                <div>
                  <strong>{favorite.label}</strong>
                  <small>{favorite.nodeIds.length} node</small>
                </div>
                <div className="path-actions">
                  <button
                    type="button"
                    className="chip-button secondary"
                    onClick={() => applyFavoritePath(favorite.id)}
                  >
                    Goster
                  </button>
                  <button
                    type="button"
                    className="chip-button danger"
                    onClick={() => handleFavoriteRemove(favorite.id)}
                  >
                    Favoriyi sil
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}

      {isAuthenticated && (
        <section className="proximity-section">
          <h4>1-Hop Yakinlik</h4>
          {proximityLoading && <p className="muted">Hesaplaniyor...</p>}
          {proximityError && <p className="error-text">{proximityError}</p>}
          {proximity && (
            <div className="proximity-card">
              <p>
                Toplam baglanti: <strong>{proximity.totalConnections}</strong>
              </p>
              <p>
                Influence skoru: <strong>{proximity.influenceScore.toFixed(2)}</strong>
              </p>
              {proximity.connectionCounts && Object.keys(proximity.connectionCounts).length > 0 && (
                <div className="proximity-counts">
                  {Object.entries(proximity.connectionCounts).map(([edgeType, count]) => (
                    <span key={edgeType}>
                      {edgeType}: <strong>{count}</strong>
                    </span>
                  ))}
                </div>
              )}
              <ul className="proximity-list">
                {proximity.neighbors.length === 0 && <li>Baglanti bulunamadi.</li>}
                {proximity.neighbors.slice(0, 5).map((neighbor) => (
                  <li key={neighbor.edgeId} className="neighbor-item">
                    <div className="neighbor-line">
                      <div>
                        <strong>{neighbor.neighbor.name ?? 'Isimsiz Kisi'}</strong> ({neighbor.neighbor.type})
                      </div>
                      <span className="edge-pill">
                        {neighbor.outgoing ? '->' : '<-'} {neighbor.edgeType}
                      </span>
                    </div>
                    {(neighbor.relationshipStrength !== undefined || neighbor.lastInteractionDate) && (
                      <div className="neighbor-meta">
                        {neighbor.relationshipStrength !== undefined && neighbor.relationshipStrength !== null && (
                          <span className="neighbor-meta-chip">Iliski gucu: {neighbor.relationshipStrength}/5</span>
                        )}
                        {neighbor.lastInteractionDate && (
                          <span className="neighbor-meta-chip">Son iletisim: {neighbor.lastInteractionDate}</span>
                        )}
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>
      )}

      <footer className="detail-footer">
        <button className="primary-button" onClick={() => openEditModal(selectedNode)}>
          Duzenle
        </button>
        <button
          className="ghost-button danger"
          onClick={async () => {
            if (!selectedNode?.id) return;
            if (!window.confirm('Bu kaydi silmek istediginize emin misiniz?')) return;
            try {
              await deleteNode(selectedNode.id);
              triggerGraphRefresh();
              triggerVisionRefresh();
              selectNode(null);
              setDeleteError(null);
            } catch {
              setDeleteError('Silme islemi basarisiz oldu.');
            }
          }}
        >
          Sil
        </button>
      </footer>
      {deleteError && <p className="error-text">{deleteError}</p>}
    </div>
  );
}

type TimelineEntry = {
  id: string;
  date: string;
  note: string;
};

function extractTimelineEntries(node: NodeResponse | null): TimelineEntry[] {
  if (!node?.properties) {
    return [];
  }
  const raw = (node.properties as { timeline?: unknown }).timeline;
  if (!Array.isArray(raw)) {
    return [];
  }
  return raw
    .map((entry) => normalizeTimelineEntry(entry))
    .filter((entry): entry is TimelineEntry => Boolean(entry))
    .sort((a, b) => Date.parse(b.date) - Date.parse(a.date));
}

function normalizeTimelineEntry(entry: unknown): TimelineEntry | null {
  if (!entry || typeof entry !== 'object') {
    return null;
  }
  const record = entry as { id?: unknown; date?: unknown; note?: unknown; text?: unknown; content?: unknown };
  const noteSource = [record.note, record.text, record.content].find((value) => typeof value === 'string');
  const note = (noteSource as string | undefined)?.trim();
  if (!note) {
    return null;
  }
  const date =
    typeof record.date === 'string' && record.date.trim() ? record.date.trim() : defaultTimelineDate();
  return {
    id:
      typeof record.id === 'string'
        ? record.id
        : `tl-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    date,
    note,
  };
}

function defaultTimelineDate() {
  return new Date().toISOString().slice(0, 10);
}

function createTimelineEntry(note: string, date?: string): TimelineEntry {
  const id =
    typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
      ? crypto.randomUUID()
      : `tl-${Date.now()}`;
  const sanitizedDate = date && date.trim() ? date : defaultTimelineDate();
  return {
    id,
    date: sanitizedDate,
    note,
  };
}
