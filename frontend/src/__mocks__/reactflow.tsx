import type { ReactNode } from "react";

export default function MockReactFlow({ children }: { children?: ReactNode }) {
  return <div data-testid="mock-react-flow">{children}</div>;
}

export const Background = () => null;
export const Controls = () => null;
export const MiniMap = () => null;
