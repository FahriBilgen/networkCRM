import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { LoadingSpinner } from './LoadingSpinner';

describe('LoadingSpinner', () => {
  it('renders spinner without message', () => {
    render(<LoadingSpinner />);
    const spinner = screen.getByRole('status');
    expect(spinner).toBeTruthy();
  });

  it('renders spinner with message', () => {
    const message = 'Loading...';
    render(<LoadingSpinner message={message} />);
    expect(screen.getByText(message)).toBeTruthy();
  });

  it('applies size classes correctly', () => {
    const { rerender, container } = render(<LoadingSpinner size="small" />);
    expect(container.querySelector('.loading-spinner--small')).toBeTruthy();

    rerender(<LoadingSpinner size="large" />);
    expect(container.querySelector('.loading-spinner--large')).toBeTruthy();
  });

  it('defaults to medium size', () => {
    const { container } = render(<LoadingSpinner />);
    expect(container.querySelector('.loading-spinner--medium')).toBeTruthy();
  });
});
