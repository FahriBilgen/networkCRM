import { useSelectionStore } from '../store/selectionStore';
import type { NodeType } from '../types';
import './NodeDetailPanel.css';

const typeLabels: Record<NodeType, string> = {
  PERSON: 'Kişi',
  VISION: 'Vision',
  GOAL: 'Goal',
  PROJECT: 'Project',
};

export function NodeDetailPanel() {
  const selectedNode = useSelectionStore((state) => state.selectedNode);

  if (!selectedNode) {
    return (
      <div className="panel node-detail-panel empty">
        <p>Graph üzerinden bir node seçtiğinizde detaylar burada görünecek.</p>
      </div>
    );
  }

  return (
    <div className="panel node-detail-panel">
      <header>
        <span className={`badge badge-${selectedNode.type.toLowerCase()}`}>{typeLabels[selectedNode.type]}</span>
        <h3>{selectedNode.name}</h3>
        {selectedNode.company && <p className="muted">{selectedNode.company}</p>}
      </header>
      {selectedNode.description && <p>{selectedNode.description}</p>}
      <section>
        <h4>Öznitelikler</h4>
        <dl>
          {selectedNode.sector && (
            <>
              <dt>Sektör</dt>
              <dd>{selectedNode.sector}</dd>
            </>
          )}
          {selectedNode.relationshipStrength !== undefined && (
            <>
              <dt>İlişki Gücü</dt>
              <dd>{selectedNode.relationshipStrength}/5</dd>
            </>
          )}
          {selectedNode.tags?.length && (
            <>
              <dt>Etiketler</dt>
              <dd className="tags">
                {selectedNode.tags.map((tag) => (
                  <span key={tag}>{tag}</span>
                ))}
              </dd>
            </>
          )}
          {selectedNode.dueDate && (
            <>
              <dt>Bitiş</dt>
              <dd>{selectedNode.dueDate}</dd>
            </>
          )}
        </dl>
      </section>
      <footer>
        <button className="primary-button block">Düzenle</button>
      </footer>
    </div>
  );
}
