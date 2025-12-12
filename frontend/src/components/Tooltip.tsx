import './Tooltip.css';

interface TooltipProps {
  children: React.ReactNode;
  content: string;
  position?: 'top' | 'bottom' | 'left' | 'right';
}

export function Tooltip({ children, content, position = 'top' }: TooltipProps) {
  return (
    <div className={`tooltip-wrapper tooltip-${position}`}>
      {children}
      <div className="tooltip-content">{content}</div>
    </div>
  );
}
