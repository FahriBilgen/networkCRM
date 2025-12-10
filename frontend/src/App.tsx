import { MainLayout } from './layout/MainLayout';
import { FiltersPanel } from './panels/FiltersPanel';
import { GraphCanvas } from './panels/GraphCanvas';
import { RightPanel } from './panels/RightPanel';
import { VisionTreePanel } from './panels/VisionTreePanel';

export function App() {
  return (
    <MainLayout>
      <aside className="left-panels">
        <VisionTreePanel />
        <FiltersPanel />
      </aside>
      <section className="graph-section">
        <GraphCanvas />
      </section>
      <aside>
        <RightPanel />
      </aside>
    </MainLayout>
  );
}
