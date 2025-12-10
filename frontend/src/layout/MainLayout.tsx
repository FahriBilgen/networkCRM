import type { PropsWithChildren } from 'react';
import { TopNav } from '../components/TopNav';
import '../styles/app.css';

export function MainLayout({ children }: PropsWithChildren) {
  return (
    <div className="app-shell">
      <TopNav />
      <div className="app-content">{children}</div>
    </div>
  );
}
