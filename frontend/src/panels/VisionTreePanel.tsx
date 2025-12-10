import { mockVisionTree } from '../mock/data';
import { useSelectionStore } from '../store/selectionStore';
import { NODE_TYPES } from '../types';
import type { NodeType } from '../types';
import { useVisionTree } from '../hooks/useVisionTree';
import './VisionTreePanel.css';

export function VisionTreePanel() {
  const { data, loading, error } = useVisionTree();
  const selectNode = useSelectionStore((state) => state.selectNode);
  const tree = data ?? mockVisionTree;

  const handleSelect = (nodeId: string) => {
    const node =
      mockVisionTree.visions
        .flatMap((visionNode) => [
          visionNode.vision,
          ...visionNode.goals.map((g) => g.goal),
          ...visionNode.goals.flatMap((g) => g.projects),
        ])
        .find((n) => n.id === nodeId) ?? null;
    selectNode(node);
  };

  return (
    <div className="panel vision-tree-panel">
      <header>
        <h3>Vision / Goal / Project</h3>
      </header>
      <div className="vision-tree-scroll">
        {loading && <p>Yükleniyor...</p>}
        {error && <p className="error">{error}</p>}
        {tree.visions.map((vision) => (
          <div key={vision.vision.id} className="vision-block">
            <button className="vision-node" onClick={() => handleSelect(vision.vision.id)}>
              <span className="node-dot vision" />
              <div>
                <strong>{vision.vision.name}</strong>
                {vision.vision.description && <small>{vision.vision.description}</small>}
              </div>
            </button>
            <div className="goal-list">
              {vision.goals.map((goal) => (
                <div key={goal.goal.id} className="goal-block">
                  <button className="goal-node" onClick={() => handleSelect(goal.goal.id)}>
                    <span className="node-dot goal" />
                    <div>
                      <strong>{goal.goal.name}</strong>
                      {goal.goal.description && <small>{goal.goal.description}</small>}
                    </div>
                  </button>
                  <div className="project-list">
                    {goal.projects.map((project) => (
                      <button
                        key={project.id}
                        className="project-node"
                        onClick={() => handleSelect(project.id)}
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
        <p>Bir hedefi yeni bir vision&apos;a sürükleyip bıraktığınızda otomatik BELONGS_TO edge oluşturulacak.</p>
        <div className="legend">
          <LegendDot label="Vision" type={NODE_TYPES.VISION} />
          <LegendDot label="Goal" type={NODE_TYPES.GOAL} />
          <LegendDot label="Project" type={NODE_TYPES.PROJECT} />
        </div>
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
