import { useEffect } from 'react';
import { MainLayout } from './layout/MainLayout';
import { FiltersPanel } from './panels/FiltersPanel';
import { GraphCanvas } from './panels/GraphCanvas';
import { RightPanel } from './panels/RightPanel';
import { VisionTreePanel } from './panels/VisionTreePanel';
import { LoginOverlay } from './components/LoginOverlay';
import { NodeModal } from './components/NodeModal';
import { useAuthStore } from './store/authStore';
import { useUiStore } from './store/uiStore';
import type { NodeResponse } from './types';

export function App() {
  const token = useAuthStore((state) => state.token);
  const openEditModal = useUiStore((state) => state.openEditModal);

  useEffect(() => {
    const handler = (event: Event) => {
      const customEvent = event as CustomEvent<NodeResponse>;
      if (customEvent.detail) {
        openEditModal(customEvent.detail);
      }
    };
    window.addEventListener('node-edit', handler);
    return () => {
      window.removeEventListener('node-edit', handler);
    };
  }, [openEditModal]);

  if (!token) {
    return <LoginOverlay />;
  }

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
      <NodeModal />
    </MainLayout>
  );
}
