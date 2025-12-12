import { useMemo, useState } from 'react';
import { moveGoal, moveProject } from '../api/client';
import { mockVisionTree } from '../mock/data';
import { useSelectionStore } from '../store/selectionStore';
import { NODE_TYPES } from '../types';
import type { NodeResponse, NodeType } from '../types';
import { useVisionTree } from '../hooks/useVisionTree';
import { useRefreshStore } from '../store/dataRefreshStore';
import { useAuthStore } from '../store/authStore';
import { useGraphStore } from '../store/graphStore';
import './VisionTreePanel.css';

type DragItem = { id: string; type: NodeType } | null;

export function VisionTreePanel() {
  const { data, loading, error } = useVisionTree();
  const selectNode = useSelectionStore((state) => state.selectNode);
  const tree = data ?? mockVisionTree;
  const [dragItem, setDragItem] = useState<DragItem>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const triggerGraphRefresh = useRefreshStore((state) => state.triggerGraphRefresh);
  const triggerVisionRefresh = useRefreshStore((state) => state.triggerVisionRefresh);
  const isAuthenticated = useAuthStore((state) => Boolean(state.token));
  const filteredNodeIds = useGraphStore((state) => state.filteredNodeIds);

  const filteredSet = useMemo(() => {
    if (!filteredNodeIds) {
      return null;
    }
    return new Set(filteredNodeIds);
  }, [filteredNodeIds]);

  const isDimmed = (nodeId: string) => (filteredSet ? !filteredSet.has(nodeId) : false);

  const flattenedNodes = useMemo(() => {
    const nodes: NodeResponse[] = [];
    tree.visions.forEach((visionNode) => {
      nodes.push(visionNode.vision);
      visionNode.goals.forEach((goalNode) => {
        nodes.push(goalNode.goal);
        nodes.push(...goalNode.projects);
      });
    });
    return nodes;
  }, [tree]);

  const matchedVisions = useMemo(() => {
    if (!filteredSet) {
      return tree.visions;
    }
    return tree.visions.filter((vision) => {
      if (filteredSet.has(vision.vision.id)) {
        return true;
      }
      return vision.goals.some((goal) => {
        if (filteredSet.has(goal.goal.id)) {
          return true;
        }
        return goal.projects.some((project) => filteredSet.has(project.id));
      });
    });
  }, [tree.visions, filteredSet]);

  const goalIsVisible = (goalNode: NodeResponse, projects: NodeResponse[]) => {
    if (!filteredSet) {
      return true;
    }
    if (filteredSet.has(goalNode.id)) {
      return true;
    }
    return projects.some((project) => filteredSet.has(project.id));
  };

  const filteredProjects = (projects: NodeResponse[]) => {
    if (!filteredSet) {
      return projects;
    }
    return projects.filter((project) => filteredSet.has(project.id));
  };

  const filterSummary = useMemo(() => {
    if (!filteredSet || filteredSet.size === 0) {
      return null;
    }
    const stats: Partial<Record<NodeType, number>> = {};
    flattenedNodes.forEach((node) => {
      if (filteredSet.has(node.id)) {
        stats[node.type] = (stats[node.type] ?? 0) + 1;
      }
    });
    const entries = Object.entries(stats);
    if (!entries.length) {
      return null;
    }
    return entries.map(([type, count]) => `${type.toLowerCase()}: ${count}`).join(' • ');
  }, [filteredSet, flattenedNodes]);

  const handleSelect = (nodeId: string) => {
    const node = flattenedNodes.find((entry) => entry.id === nodeId) ?? null;
    selectNode(node);
  };

  const resetDrag = () => setDragItem(null);

  const handleDragStart = (item: DragItem) => {
    if (!isAuthenticated || !item) {
      return;
    }
    setDragItem(item);
    setStatusMessage(null);
  };

  const handleVisionDrop = async (visionId: string, sortOrder: number) => {
    if (!dragItem || dragItem.type !== NODE_TYPES.GOAL) {
      return;
    }
    try {
      await moveGoal(dragItem.id, visionId, sortOrder);
      setStatusMessage('Hedef yeni vision altına taşındı.');
      triggerVisionRefresh();
      triggerGraphRefresh();
    } catch (err) {
      console.warn('Goal move failed', err);
      setStatusMessage('Hedef taşınamadı.');
    } finally {
      resetDrag();
    }
  };

  const handleGoalDrop = async (goalId: string, sortOrder: number) => {
    if (!dragItem || dragItem.type !== NODE_TYPES.PROJECT) {
      return;
    }
    try {
      await moveProject(dragItem.id, goalId, sortOrder);
      setStatusMessage('Proje yeni hedef altına taşındı.');
      triggerVisionRefresh();
      triggerGraphRefresh();
    } catch (err) {
      console.warn('Project move failed', err);
      setStatusMessage('Proje taşınamadı.');
    } finally {
      resetDrag();
    }
  };

  const allowDropForVision = dragItem?.type === NODE_TYPES.GOAL;
  const allowDropForGoal = dragItem?.type === NODE_TYPES.PROJECT;

  return (
    <div className="panel vision-tree-panel">
      <header>
        <h3>Vision / Goal / Project</h3>
        {filterSummary && <p className="vision-filter-summary">{filterSummary}</p>}
      </header>
      <div className="vision-tree-scroll">
        {loading && <p>Yükleniyor...</p>}
        {error && <p className="error">{error}</p>}
        {!loading && !error && matchedVisions.length === 0 && (
          <p className="muted">Filtre ile eşleşen vision/goal bulunamadı.</p>
        )}
        {matchedVisions.map((vision) => (
          <div
            key={vision.vision.id}
            className="vision-block"
            data-testid={`vision-${vision.vision.id}`}
            onDragOver={(event) => {
              if (allowDropForVision) {
                event.preventDefault();
              }
            }}
            onDrop={(event) => {
              if (!allowDropForVision) {
                return;
              }
              event.preventDefault();
              handleVisionDrop(vision.vision.id, vision.goals.length);
            }}
          >
            <button
              className={`vision-node${isDimmed(vision.vision.id) ? ' dimmed' : ''}`}
              onClick={() => handleSelect(vision.vision.id)}
            >
              <span className="node-dot vision" />
              <div>
                <strong>{vision.vision.name}</strong>
                {vision.vision.description && <small>{vision.vision.description}</small>}
              </div>
            </button>
            <div className="goal-list">
              {vision.goals
                .filter((goal) => goalIsVisible(goal.goal, goal.projects))
                .map((goal) => (
                  <div
                    key={goal.goal.id}
                    className="goal-block"
                    onDragOver={(event) => {
                      if (allowDropForGoal) {
                        event.preventDefault();
                      }
                    }}
                    onDrop={(event) => {
                      if (!allowDropForGoal) {
                        return;
                      }
                      event.preventDefault();
                      handleGoalDrop(goal.goal.id, goal.projects.length);
                    }}
                  >
                    <button
                      className={`goal-node${isDimmed(goal.goal.id) ? ' dimmed' : ''}`}
                      onClick={() => handleSelect(goal.goal.id)}
                      draggable={isAuthenticated}
                      onDragStart={() =>
                        handleDragStart({
                          id: goal.goal.id,
                          type: NODE_TYPES.GOAL,
                        })
                      }
                      onDragEnd={resetDrag}
                    >
                      <span className="node-dot goal" />
                      <div>
                        <strong>{goal.goal.name}</strong>
                        {goal.goal.description && <small>{goal.goal.description}</small>}
                      </div>
                    </button>
                    <div className="project-list">
                      {filteredProjects(goal.projects).map((project) => (
                        <button
                          key={project.id}
                          className={`project-node${isDimmed(project.id) ? ' dimmed' : ''}`}
                          onClick={() => handleSelect(project.id)}
                          draggable={isAuthenticated}
                          onDragStart={() =>
                            handleDragStart({
                              id: project.id,
                              type: NODE_TYPES.PROJECT,
                            })
                          }
                          onDragEnd={resetDrag}
                        >
                          <span className="node-dot project" />
                          <div>
                            <strong>{project.name}</strong>
                            {project.status && <small>{project.status}</small>}
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
            </div>
          </div>
        ))}
      </div>
      <div className="vision-tree-footer">
        <p>
          Bir hedefi yeni bir vision&apos;a sürükleyip bıraktığınızda BELONGS_TO bağlantısı güncellenecek. Projeler de
          aynı şekilde hedef seviyesine taşınabilir.
        </p>
        <div className="legend">
          <LegendDot label="Vision" type={NODE_TYPES.VISION} />
          <LegendDot label="Goal" type={NODE_TYPES.GOAL} />
          <LegendDot label="Project" type={NODE_TYPES.PROJECT} />
        </div>
        {statusMessage && <p className="status">{statusMessage}</p>}
      </div>
    </div>
  );
}

function LegendDot({ label, type }: { label: string; type: NodeType }) {
  return (
    <span className="legend-dot">
      <span className={`node-dot ${type.toLowerCase()}`} />
      {label}
    </span>
  );
}
