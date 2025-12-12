import './Badge.css';

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'info' | 'success' | 'warning' | 'error';
  size?: 'small' | 'medium';
}

export function Badge({ children, variant = 'info', size = 'medium' }: BadgeProps) {
  return <span className={`badge badge--${variant} badge--${size}`}>{children}</span>;
}
