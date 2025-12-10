import { useMemo } from 'react';
import ReactFlow, { Background, Controls, MiniMap } from 'reactflow';
import type { Edge, Node } from 'reactflow';
import 'reactflow/dist/style.css';
import { useSelectionStore } from '../store/selectionStore';
import { NODE_TYPES } from '../types';
import type { NodeType } from '../types';
import { useGraphData } from '../hooks/useGraphData';
import './GraphCanvas.css';

const typeColors: Record<NodeType, string> = {
  [NODE_TYPES.VISION]: '#38bdf8',
  [NODE_TYPES.GOAL]: '#facc15',
  [NODE_TYPES.PROJECT]: '#a78bfa',
  [NODE_TYPES.PERSON]: '#22d3ee',
};

export function GraphCanvas() {
  const { data, loading, error } = useGraphData();
  const selectNode = useSelectionStore((state) => state.selectNode);
  const graph = data;

  const nodes = useMemo<Node[]>(() => {
    return graph.nodes.map((node, index) => ({
      id: node.id,
      data: { label: node.name },
      position: {
        x: (index % 3) * 220,
        y: Math.floor(index / 3) * 120,
      },
      style: {
        borderRadius: 12,
        padding: '8px 12px',
        border: `2px solid ${typeColors[node.type]}`,
        background: '#0f172a',
        color: '#f8fafc',
      },
    }));
  }, [graph.nodes]);

  const edges = useMemo<Edge[]>(() => {
    return graph.links.map((edge) => ({
      id: edge.id,
      source: edge.sourceNodeId,
      target: edge.targetNodeId,
      type: 'smoothstep',
      label: edge.type.toLowerCase(),
      style: {
        stroke: edge.type === 'SUPPORTS' ? '#10b981' : '#64748b',
      },
      labelBgPadding: [6, 3],
      labelBgBorderRadius: 4,
      animated: edge.type === 'SUPPORTS',
    }));
  }, [graph.links]);

  return (
    <div className="graph-canvas">
      {error && <div className="graph-banner error">{error}</div>}
      {loading && <div className="graph-banner loading">Graph yükleniyor...</div>}
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodeClick={(_, node) => {
          const found = graph.nodes.find((n) => n.id === node.id) ?? null;
          selectNode(found);
        }}
        fitView
      >
        <Background />
        <MiniMap pannable zoomable />
        <Controls />
      </ReactFlow>
    </div>
  );
}
