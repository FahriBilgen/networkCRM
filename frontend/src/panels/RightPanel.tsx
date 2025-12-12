import { useSelectionStore } from '../store/selectionStore';
import { AiInsightPanel } from './AiInsightPanel';
import { NodeDetailPanel } from './NodeDetailPanel';
import './RightPanel.css';

export function RightPanel() {
  const { panelTab, setPanelTab } = useSelectionStore();

  return (
    <div className="right-panel">
      <div className="panel-tabs">
        <button
          className={panelTab === 'details' ? 'active' : ''}
          onClick={() => setPanelTab('details')}
        >
          Detaylar
        </button>
        <button className={panelTab === 'ai' ? 'active' : ''} onClick={() => setPanelTab('ai')}>
          Yapay Zeka
        </button>
      </div>
      <div className="panel-body">{panelTab === 'details' ? <NodeDetailPanel /> : <AiInsightPanel />}</div>
    </div>
  );
}
