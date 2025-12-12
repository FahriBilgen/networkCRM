import { useEffect, useMemo, useRef, useState, type Dispatch, type SetStateAction } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  type Edge,
  type Node,
  type NodeDragHandler,
  type NodeMouseHandler,
  type ReactFlowInstance,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { useSelectionStore } from '../store/selectionStore';
import { useGraphStore } from '../store/graphStore';
import { useGraphData } from '../hooks/useGraphData';
import { useRefreshStore } from '../store/dataRefreshStore';
import { useAuthStore } from '../store/authStore';
import { NODE_TYPES } from '../types';
import type { EdgeResponse, NodeResponse, NodeType } from '../types';
import { deleteFavoritePath, fetchFavoritePaths, importPersonsCsv, updateNode } from '../api/client';
import './GraphCanvas.css';
import { exportGraphElement, type GraphExportFormat } from '../utils/exportGraph';
import { buildNodeRequestPayload } from '../utils/nodePayload';
import { computeAutoLayout } from '../utils/autoLayout';
import { computeMindMapLayout } from '../utils/mindMapLayout';
import { computeClusterStats } from '../utils/graphClusters';
import { buildPathDisplay } from '../utils/pathInspector';

const sectorPalette = ['#0ea5e9', '#14b8a6', '#a78bfa', '#f472b6', '#fb923c', '#8b5cf6', '#facc15', '#22d3ee'];
const typeColors: Record<NodeType, string> = {
  [NODE_TYPES.VISION]: '#38bdf8',
  [NODE_TYPES.GOAL]: '#facc15',
  [NODE_TYPES.PROJECT]: '#a78bfa',
  [NODE_TYPES.PERSON]: '#22d3ee',
};

const edgeTypeLabels: Record<string, string> = {
  KNOWS: 'Tanıyor',
  SUPPORTS: 'Destekliyor',
  BELONGS_TO: 'Ait',
};

type PositionMap = Record<string, { x: number; y: number }>;

type ViewMode = 'CUSTOM' | 'MIND_MAP';

export function GraphCanvas() {
  const { data, loading, error } = useGraphData();
  const selectNode = useSelectionStore((state) => state.selectNode);
  const selectedNode = useSelectionStore((state) => state.selectedNode);
  const graph = data;
  const filteredNodeIds = useGraphStore((state) => state.filteredNodeIds);
  const setFilteredNodeIds = useGraphStore((state) => state.setFilteredNodeIds);
  const clearFilteredNodeIds = useGraphStore((state) => state.clearFilteredNodeIds);
  const highlightPathNodeIds = useGraphStore((state) => state.highlightPathNodeIds);
  const clearHighlightPath = useGraphStore((state) => state.clearHighlightPath);
  const favoritePaths = useGraphStore((state) => state.favoritePaths);
  const applyFavoritePath = useGraphStore((state) => state.applyFavoritePath);
  const removeFavoritePath = useGraphStore((state) => state.removeFavoritePath);
  const setFavoritePaths = useGraphStore((state) => state.setFavoritePaths);
  const favoritePathsLoaded = useGraphStore((state) => state.favoritePathsLoaded);
  const setFavoritePathsLoaded = useGraphStore((state) => state.setFavoritePathsLoaded);
  const triggerGraphRefresh = useRefreshStore((state) => state.triggerGraphRefresh);
  const isAuthenticated = useAuthStore((state) => Boolean(state.token));

  const [positions, setPositions] = useState<PositionMap>({});
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; node: NodeResponse } | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [exportingFormat, setExportingFormat] = useState<GraphExportFormat | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);
  const [autoLayoutStatus, setAutoLayoutStatus] = useState<'idle' | 'running' | 'persisting'>('idle');
  const [autoLayoutError, setAutoLayoutError] = useState<string | null>(null);
  const canvasRef = useRef<HTMLDivElement | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>('CUSTOM');
  const reactFlowInstance = useRef<ReactFlowInstance | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [importingCsv, setImportingCsv] = useState(false);
  const [importError, setImportError] = useState<string | null>(null);

  const filteredSet = useMemo(() => {
    if (!filteredNodeIds) {
      return null;
    }
    return new Set(filteredNodeIds);
  }, [filteredNodeIds]);

  const mindMapPositions = useMemo(() => {
    if (viewMode !== 'MIND_MAP') {
      return {};
    }
    return computeMindMapLayout(graph.nodes, graph.links);
  }, [viewMode, graph.nodes, graph.links]);

  const highlightSet = useMemo(() => {
    if (!highlightPathNodeIds || highlightPathNodeIds.length === 0) {
      return null;
    }
    return new Set(highlightPathNodeIds);
  }, [highlightPathNodeIds]);

  const highlightEdgeSet = useMemo(() => {
    if (!highlightPathNodeIds || highlightPathNodeIds.length < 2) {
      return null;
    }
    const set = new Set<string>();
    for (let index = 0; index < highlightPathNodeIds.length - 1; index += 1) {
      const current = highlightPathNodeIds[index];
      const next = highlightPathNodeIds[index + 1];
      const edge = graph.links.find(
        (candidate) =>
          (candidate.sourceNodeId === current && candidate.targetNodeId === next) ||
          (candidate.sourceNodeId === next && candidate.targetNodeId === current),
      );
      if (edge) {
        set.add(edge.id);
      }
    }
    return set;
  }, [highlightPathNodeIds, graph.links]);

  const clusterStats = useMemo(() => computeClusterStats(graph.nodes, graph.links), [graph.nodes, graph.links]);
  const showClusterPanel = clusterStats.clusters.length > 1 || clusterStats.isolatedNodeIds.length > 0;
  const topClusters = clusterStats.clusters.slice(0, 3);
  const highlightDisplay = useMemo(
    () => buildPathDisplay(highlightPathNodeIds, graph.nodes),
    [highlightPathNodeIds, graph.nodes],
  );
  const showPathOverlay = highlightDisplay.length > 0 || favoritePaths.length > 0;

  const canDragNodes = isAuthenticated && viewMode === 'CUSTOM';

  useEffect(() => {
    setPositions((prev) => {
      const next: PositionMap = { ...prev };
      graph.nodes.forEach((node, index) => {
        const saved = extractPosition(node);
        if (saved) {
          next[node.id] = saved;
        } else if (!next[node.id]) {
          next[node.id] = defaultGridPosition(index);
        }
      });
      return next;
    });
  }, [graph.nodes]);

  useEffect(() => {
    if (!isAuthenticated || favoritePathsLoaded) {
      return;
    }
    fetchFavoritePaths()
      .then((paths) => setFavoritePaths(paths))
      .catch((err) => console.warn('Favorite paths could not be loaded', err))
      .finally(() => setFavoritePathsLoaded(true));
  }, [isAuthenticated, favoritePathsLoaded, setFavoritePaths, setFavoritePathsLoaded]);

  useEffect(() => {
    if (!isAuthenticated) {
      setFavoritePaths([]);
      setFavoritePathsLoaded(false);
    }
  }, [isAuthenticated, setFavoritePaths, setFavoritePathsLoaded]);

  const filterBannerText = filteredSet
    ? filteredSet.size === 0
      ? 'Eslesen node bulunamadi; graph tum nodlari gri olarak gosteriyor.'
      : `${filteredSet.size} node filtreyle eslesti; digerleri gri gosteriliyor.`
    : null;

  const filterStats = useMemo(() => {
    if (!filteredSet || filteredSet.size === 0) {
      return null;
    }
    const counts: Partial<Record<NodeType, number>> = {};
    graph.nodes.forEach((node) => {
      if (filteredSet.has(node.id)) {
        counts[node.type] = (counts[node.type] ?? 0) + 1;
      }
    });
    const entries = Object.entries(counts).filter(([, value]) => Boolean(value));
    if (entries.length === 0) {
      return null;
    }
    return entries.map(([type, count]) => `${type.toLowerCase()}: ${count}`).join(' | ');
  }, [filteredSet, graph.nodes]);

  const nodes = useMemo<Node[]>(() => {
    return graph.nodes.map((node, index) => {
      const color = node.sector ? colorForSector(node.sector) : typeColors[node.type] ?? '#22d3ee';
      const filterDim = filteredSet ? !filteredSet.has(node.id) : false;
      const highlightDim = highlightSet ? !highlightSet.has(node.id) : false;
      const isHighlighted = highlightSet ? highlightSet.has(node.id) : false;
      const isDimmed = filterDim || highlightDim;
      const borderWidth = isHighlighted ? 3 : 2;
      const basePosition =
        viewMode === 'MIND_MAP'
          ? mindMapPositions[node.id] ?? defaultGridPosition(index)
          : positions[node.id] ?? defaultGridPosition(index);
      return {
        id: node.id,
        data: { label: node.name },
        position: basePosition,
        style: {
          borderRadius: 12,
          padding: '8px 12px',
          border: `${borderWidth}px solid ${color}`,
          background: '#0f172a',
          color: '#f8fafc',
          opacity: isDimmed ? 0.25 : 1,
          boxShadow: isHighlighted ? '0 0 0 4px rgba(14,165,233,0.35)' : undefined,
        },
      };
    });
  }, [graph.nodes, filteredSet, positions, mindMapPositions, viewMode, highlightSet]);

  const edges = useMemo<Edge[]>(() => {
    return graph.links.map((edge) => {
      const filteredDim =
        filteredSet != null && (!filteredSet.has(edge.sourceNodeId) || !filteredSet.has(edge.targetNodeId));
      const highlighted = highlightEdgeSet ? highlightEdgeSet.has(edge.id) : false;
      const highlightDim = highlightEdgeSet ? !highlighted : false;
      const dimmed = filteredDim || highlightDim;
      return createEdge(edge, dimmed, highlighted);
    });
  }, [graph.links, filteredSet, highlightEdgeSet]);

  const handleContextMenu: NodeMouseHandler = (event, node) => {
    event.preventDefault();
    const found = graph.nodes.find((entry) => entry.id === node.id);
    if (!found) {
      return;
    }
    setContextMenu({
      x: event.clientX,
      y: event.clientY,
      node: found,
    });
  };

  const runSectorFilter = (sector?: string | null) => {
    if (!sector) {
      return;
    }
    const ids = graph.nodes
      .filter((candidate) => candidate.sector && candidate.sector.toLowerCase() === sector.toLowerCase())
      .map((candidate) => candidate.id);
    setFilteredNodeIds(ids);
    if (ids.length === 0) {
      setStatusMessage(`${sector} sektöründe kayıt bulunamadı.`);
    } else {
      setStatusMessage(`${sector} sektöründen ${ids.length} kayıt vurgulandı.`);
    }
  };

  const nodeDragHandler = useMemo(
    () =>
      createNodeDragHandler({
        graphNodes: graph.nodes,
        isAuthenticated,
        setPositions,
        setStatusMessage,
        triggerGraphRefresh,
      }),
    [graph.nodes, isAuthenticated, triggerGraphRefresh, setStatusMessage],
  );

  const handleExport = async (format: GraphExportFormat) => {
    if (!canvasRef.current) {
      setExportError('Ağ görseli bulunamadı.');
      return;
    }
    setExportError(null);
    setExportingFormat(format);
    try {
      const safeName = (selectedNode?.name || 'network-graph').replace(/\s+/g, '-').toLowerCase();
      await exportGraphElement(canvasRef.current, { format, fileName: safeName });
      setStatusMessage(`Ağ ${format.toUpperCase()} olarak kaydedildi.`);
    } catch (err) {
      console.warn('Graph export failed', err);
      setExportError('Dışa aktarma başarısız oldu.');
    } finally {
      setExportingFormat(null);
    }
  };

  const handleAutoLayout = async () => {
    if (viewMode !== 'CUSTOM') {
      return;
    }
    if (!graph?.nodes?.length) {
      return;
    }
    setAutoLayoutStatus('running');
    setAutoLayoutError(null);
    try {
      const layoutPositions = await computeAutoLayout(graph.nodes, graph.links);
      if (Object.keys(layoutPositions).length === 0) {
        setAutoLayoutStatus('idle');
        return;
      }
      setPositions((prev) => ({ ...prev, ...layoutPositions }));
      setStatusMessage('Otomatik düzen uygulandı.');
      if (isAuthenticated) {
        setAutoLayoutStatus('persisting');
        await persistLayout(layoutPositions);
        setStatusMessage('Otomatik düzen kaydedildi.');
        triggerGraphRefresh();
      }
      setAutoLayoutStatus('idle');
    } catch (err) {
      console.warn('Auto layout failed', err);
      setAutoLayoutError('Otomatik düzen başarısız oldu.');
      setAutoLayoutStatus('idle');
    }
  };

  const persistLayout = async (positionsMap: PositionMap) => {
    const entries = Object.entries(positionsMap);
    for (const [nodeId, position] of entries) {
      const found = graph.nodes.find((node) => node.id === nodeId);
      if (!found) {
        continue;
      }
      try {
        const payload = buildNodeRequestPayload(found, {
          properties: {
            ...(found.properties ?? {}),
            position,
          },
        });
        await updateNode(nodeId, payload);
      } catch (err) {
        console.warn('Failed to persist layout position', err);
        setAutoLayoutError('Bazi node pozisyonlari kaydedilemedi.');
      }
    }
  };

  const viewModeHint =
    viewMode === 'MIND_MAP' ? 'Mind-map modu acik: pozisyonlar kaydedilmez.' : null;

  const focusOnPath = () => {
    if (!highlightPathNodeIds || highlightPathNodeIds.length === 0 || !reactFlowInstance.current) {
      return;
    }
    reactFlowInstance.current.fitView({
      nodes: highlightPathNodeIds.map((id) => ({ id })),
      padding: 0.2,
      duration: 500,
    });
  };

  const handleFavoriteDelete = async (favoriteId: string) => {
    try {
      await deleteFavoritePath(favoriteId);
      removeFavoritePath(favoriteId);
      setStatusMessage('Favori silindi.');
    } catch (err) {
      console.warn('Favorite delete failed', err);
      setStatusMessage('Favori silinemedi.');
    }
  };

  const handleImportCsv = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    if (!event.target.files || event.target.files.length === 0) {
      return;
    }
    const file = event.target.files[0];
    setImportingCsv(true);
    setImportError(null);
    try {
      const result = await importPersonsCsv(file);
      setStatusMessage(`${result.created} kisi eklendi, ${result.skipped} atlandi.`);
      triggerGraphRefresh();
    } catch (err) {
      console.warn('CSV import failed', err);
      setImportError('CSV iceri aktarimi basarisiz oldu.');
    } finally {
      setImportingCsv(false);
      event.target.value = '';
    }
  };

  return (
    <div className="graph-canvas">
      <div className="graph-toolbar">
        <div className="toolbar-group">
          <span className="toolbar-label">Layout</span>
          <button
            type="button"
            className="ghost-button"
            onClick={handleAutoLayout}
            disabled={viewMode !== 'CUSTOM' || autoLayoutStatus !== 'idle'}
          >
            {autoLayoutStatus === 'running'
              ? 'Hesaplaniyor...'
              : autoLayoutStatus === 'persisting'
                ? 'Kaydediliyor...'
              : 'Auto Layout'}
          </button>
        </div>
        <div className="toolbar-group">
          <span className="toolbar-label">Import</span>
          <button type="button" className="ghost-button" onClick={handleImportCsv} disabled={importingCsv}>
            {importingCsv ? 'Yukleniyor...' : 'LinkedIn CSV'}
          </button>
        </div>
        {highlightPathNodeIds && highlightPathNodeIds.length > 0 && (
          <div className="toolbar-group highlight-indicator">
            <span className="toolbar-label">Path</span>
            <span className="toolbar-hint">{highlightPathNodeIds.length} node</span>
            <button type="button" className="ghost-button" onClick={clearHighlightPath}>
              Temizle
            </button>
          </div>
        )}
        <div className="toolbar-group view-mode-group">
          <span className="toolbar-label">Gorunum</span>
          <div className="view-toggle">
            <button
              type="button"
              className={`ghost-button ${viewMode === 'CUSTOM' ? 'active' : ''}`}
              onClick={() => setViewMode('CUSTOM')}
            >
              Serbest
            </button>
            <button
              type="button"
              className={`ghost-button ${viewMode === 'MIND_MAP' ? 'active' : ''}`}
              onClick={() => setViewMode('MIND_MAP')}
            >
              Mind Map
            </button>
          </div>
          {viewModeHint && <small className="toolbar-hint">{viewModeHint}</small>}
        </div>
        <div className="toolbar-group">
          <span className="toolbar-label">Export</span>
          <button
            type="button"
            className="ghost-button"
            onClick={() => handleExport('png')}
            disabled={exportingFormat !== null}
          >
            {exportingFormat === 'png' ? 'PNG hazirlaniyor...' : 'PNG'}
          </button>
          <button
            type="button"
            className="ghost-button"
            onClick={() => handleExport('pdf')}
            disabled={exportingFormat !== null}
          >
            {exportingFormat === 'pdf' ? 'PDF hazirlaniyor...' : 'PDF'}
          </button>
        </div>
        {(exportError || autoLayoutError || importError) && (
          <small className="toolbar-error">{exportError ?? autoLayoutError ?? importError}</small>
        )}
      </div>
      <input
        type="file"
        accept=".csv,text/csv"
        ref={fileInputRef}
        style={{ display: 'none' }}
        onChange={handleFileChange}
      />
      {error && <div className="graph-banner error">{error}</div>}
      {loading && <div className="graph-banner loading">Graph yukleniyor...</div>}
      {statusMessage && <div className="graph-banner success">{statusMessage}</div>}
      {filterBannerText && (
        <div className="graph-banner info">
          <span>{filterBannerText}</span>
          {filterStats && <span className="filter-stats">{filterStats}</span>}
          <button className="ghost-button" onClick={clearFilteredNodeIds}>
            Temizle
          </button>
        </div>
      )}
      {showClusterPanel && (
        <div className="cluster-panel">
          <div className="cluster-stats">
            <span>Cluster sayisi: {clusterStats.clusters.length}</span>
            <span>En buyuk cluster: {clusterStats.largestClusterSize} node</span>
            {clusterStats.isolatedNodeIds.length > 0 && (
              <button
                type="button"
                className="ghost-button"
                onClick={() => {
                  setFilteredNodeIds(clusterStats.isolatedNodeIds);
                  setStatusMessage(`${clusterStats.isolatedNodeIds.length} yalniz node gri disinda vurgulandi.`);
                }}
              >
                Yalniz {clusterStats.isolatedNodeIds.length} node
              </button>
            )}
          </div>
          {topClusters.length > 1 && (
            <div className="cluster-chip-row">
              {topClusters.map((cluster) => (
                <button
                  key={cluster.id}
                  type="button"
                  className="cluster-chip"
                  onClick={() => {
                    setFilteredNodeIds(cluster.nodeIds);
                    setStatusMessage(
                      `${cluster.size} node iceren cluster vurgulandi (${Object.keys(cluster.typeCounts).length} tip).`,
                    );
                  }}
                >
                  <strong>{cluster.size}</strong> node
                </button>
              ))}
            </div>
          )}
        </div>
      )}
      <div className="graph-flow-wrapper" ref={canvasRef}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodesDraggable={canDragNodes}
          onInit={(instance) => {
            reactFlowInstance.current = instance;
          }}
          onNodeClick={(_, node) => {
            const found = graph.nodes.find((entry) => entry.id === node.id) ?? null;
            selectNode(found);
          }}
          onNodeContextMenu={handleContextMenu}
          onNodeDragStop={nodeDragHandler}
          fitView
        >
          <Background />
          <MiniMap pannable zoomable />
          <Controls />
        </ReactFlow>
      </div>
      {contextMenu && (
        <div
          className="graph-context-menu"
          style={{ top: contextMenu.y, left: contextMenu.x }}
          onMouseLeave={() => setContextMenu(null)}
        >
          <button
            type="button"
            onClick={() => {
              selectNode(contextMenu.node);
              setContextMenu(null);
            }}
          >
            Detaylari ac
          </button>
          <button
            type="button"
            onClick={() => {
              selectNode(contextMenu.node);
              window.dispatchEvent(new CustomEvent('node-edit', { detail: contextMenu.node }));
              setContextMenu(null);
            }}
          >
            Duzenle
          </button>
          {contextMenu.node.sector && (
            <button
              type="button"
              onClick={() => {
                runSectorFilter(contextMenu.node.sector);
                setContextMenu(null);
              }}
            >
              {contextMenu.node.sector} filtresi
            </button>
          )}
        </div>
      )}
      {showPathOverlay && (
        <div className="path-inspector">
          {highlightDisplay.length > 0 && (
            <>
              <div className="path-inspector-header">
                <div>
                  <strong>Aktif Path</strong>
                  <small>{highlightDisplay.length} node</small>
                </div>
                <div className="path-inspector-actions">
                  <button type="button" className="ghost-button" onClick={focusOnPath}>
                    Path'e odaklan
                  </button>
                  <button type="button" className="ghost-button" onClick={clearHighlightPath}>
                    Temizle
                  </button>
                </div>
              </div>
              <ol>
                {highlightDisplay.map((entry, index) => (
                  <li key={entry.id}>
                    <span className="path-index">{index + 1}</span>
                    <div>
                      <strong>{entry.name}</strong>
                      <small>
                        {entry.type.toLowerCase()}
                        {entry.sector ? ` · ${entry.sector}` : ''}
                      </small>
                    </div>
                  </li>
                ))}
              </ol>
            </>
          )}
          {favoritePaths.length > 0 && (
            <div className="favorite-paths-block">
              <div className="path-inspector-header">
                <div>
                  <strong>Favoriler</strong>
                  <small>{favoritePaths.length} yol</small>
                </div>
              </div>
              <ul className="favorite-path-list">
                {favoritePaths.map((favorite) => (
                  <li key={favorite.id}>
                    <div>
                      <strong>{favorite.label}</strong>
                      <small>{favorite.nodeIds.length} kayıt</small>
                    </div>
                    <div className="favorite-actions">
                      <button
                        type="button"
                        className="ghost-button"
                        onClick={() => {
                          applyFavoritePath(favorite.id);
                          focusOnPath();
                        }}
                      >
                        Uygula
                      </button>
                      <button
                        type="button"
                        className="ghost-button danger"
                        onClick={() => handleFavoriteDelete(favorite.id)}
                      >
                        Favoriyi sil
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function createNodeDragHandler({
  graphNodes,
  isAuthenticated,
  setPositions,
  setStatusMessage,
  triggerGraphRefresh,
}: {
  graphNodes: NodeResponse[];
  isAuthenticated: boolean;
  setPositions: Dispatch<SetStateAction<PositionMap>>;
  setStatusMessage: Dispatch<SetStateAction<string | null>>;
  triggerGraphRefresh: () => void;
}): NodeDragHandler {
  return async (_event, node) => {
    if (!isAuthenticated) {
      return;
    }
    const found = graphNodes.find((entry) => entry.id === node.id);
    if (!found) {
      return;
    }
    const position = { x: node.position.x, y: node.position.y };
    setPositions((prev) => ({ ...prev, [node.id]: position }));
    try {
      const payload = buildNodeRequestPayload(found, {
        properties: {
          ...(found.properties ?? {}),
          position,
        },
      });
      await updateNode(node.id, payload);
      setStatusMessage('Kayıt pozisyonu kaydedildi.');
      triggerGraphRefresh();
    } catch (err) {
      console.warn('Failed to persist node position', err);
      setStatusMessage('Kayıt pozisyonu kaydedilemedi.');
    }
  };
}

export function strengthToStroke(value?: number | null) {
  if (value === undefined || value === null) {
    return 1.5;
  }
  return 1 + value * 0.6;
}

export function interactionOpacity(date?: string | null) {
  if (!date) {
    return 1;
  }
  const parsed = Date.parse(date);
  if (Number.isNaN(parsed)) {
    return 1;
  }
  const days = (Date.now() - parsed) / (1000 * 60 * 60 * 24);
  if (!Number.isFinite(days) || days <= 0) {
    return 1;
  }
  return Math.max(0.35, Math.min(1, 1 - days / 365));
}

export function createEdge(edge: EdgeResponse, dimmed = false, highlighted = false): Edge {
  const baseStrokeWidth = strengthToStroke(edge.relationshipStrength);
  const strokeWidth = highlighted ? Math.max(baseStrokeWidth, 3) : baseStrokeWidth;
  const baseOpacity = interactionOpacity(edge.lastInteractionDate);
  const opacity = highlighted ? 1 : dimmed ? Math.min(baseOpacity, 0.15) : baseOpacity;
  return {
    id: edge.id,
    source: edge.sourceNodeId,
    target: edge.targetNodeId,
    type: 'smoothstep',
    label: buildEdgeLabel(edge),
    style: {
      stroke: highlighted ? '#f472b6' : strokeForEdge(edge.type),
      strokeWidth,
      opacity,
    },
    labelBgPadding: [6, 3],
    labelBgBorderRadius: 4,
    animated:
      highlighted ||
      (edge.type === 'SUPPORTS' && (edge.relationshipStrength ?? 0) >= 3),
  };
}

export function buildEdgeLabel(edge: EdgeResponse) {
  const parts = [edgeTypeLabels[edge.type] || edge.type.toLowerCase()];
  if (edge.relationshipStrength !== undefined && edge.relationshipStrength !== null) {
    parts.push(`(${edge.relationshipStrength})`);
  }
  if (edge.lastInteractionDate) {
    parts.push(`@ ${edge.lastInteractionDate}`);
  }
  return parts.join(' ');
}

function strokeForEdge(edgeType: EdgeResponse['type']) {
  if (edgeType === 'SUPPORTS') {
    return '#10b981';
  }
  if (edgeType === 'BELONGS_TO') {
    return '#64748b';
  }
  return '#0ea5e9';
}

function colorForSector(sector: string) {
  const index = Math.abs(hashString(sector)) % sectorPalette.length;
  return sectorPalette[index];
}

function hashString(input: string) {
  let hash = 0;
  for (let i = 0; i < input.length; i += 1) {
    hash = (hash << 5) - hash + input.charCodeAt(i);
    hash |= 0;
  }
  return hash;
}

function extractPosition(node: NodeResponse): { x: number; y: number } | null {
  const props = node.properties as { position?: { x?: number; y?: number } } | null | undefined;
  const candidate = props?.position;
  if (
    candidate &&
    typeof candidate.x === 'number' &&
    typeof candidate.y === 'number' &&
    Number.isFinite(candidate.x) &&
    Number.isFinite(candidate.y)
  ) {
    return { x: candidate.x, y: candidate.y };
  }
  return null;
}

function defaultGridPosition(index: number) {
  return {
    x: (index % 3) * 220,
    y: Math.floor(index / 3) * 120,
  };
}
