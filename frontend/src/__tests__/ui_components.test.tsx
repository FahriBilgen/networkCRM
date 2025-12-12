import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { EmptyState } from '../components/EmptyState';
import { Tooltip } from '../components/Tooltip';
import { Badge } from '../components/Badge';

describe('New UI Components', () => {
  describe('EmptyState', () => {
    it('renders title and description', () => {
      render(
        <EmptyState 
          icon="🚫" 
          title="No Data" 
          description="Please add some items" 
        />
      );
      expect(screen.getByText('No Data')).toBeTruthy();
      expect(screen.getByText('Please add some items')).toBeTruthy();
    });

    it('renders action button and handles click', () => {
      const handleClick = vi.fn();
      render(
        <EmptyState 
          icon="🚫" 
          title="No Data" 
          description="Desc" 
          action={{ label: 'Add Item', onClick: handleClick }} 
        />
      );
      
      const button = screen.getByText('Add Item');
      expect(button).toBeTruthy();
      fireEvent.click(button);
      expect(handleClick).toHaveBeenCalledTimes(1);
    });
  });

  describe('Tooltip', () => {
    it('renders children and content', () => {
      render(
        <Tooltip content="Tooltip Text">
          <button>Hover Me</button>
        </Tooltip>
      );
      expect(screen.getByText('Hover Me')).toBeTruthy();
      expect(screen.getByText('Tooltip Text')).toBeTruthy();
    });

    it('applies position class', () => {
      const { container } = render(
        <Tooltip content="Text" position="bottom">
          <button>Btn</button>
        </Tooltip>
      );
      expect(container.querySelector('.tooltip-bottom')).toBeTruthy();
    });
  });

  describe('Badge', () => {
    it('renders children', () => {
      render(<Badge>Status</Badge>);
      expect(screen.getByText('Status')).toBeTruthy();
    });

    it('applies variant and size classes', () => {
      const { container, rerender } = render(<Badge variant="success" size="small">Ok</Badge>);
      expect(container.querySelector('.badge--success')).toBeTruthy();
      expect(container.querySelector('.badge--small')).toBeTruthy();

      rerender(<Badge variant="error" size="medium">Fail</Badge>);
      expect(container.querySelector('.badge--error')).toBeTruthy();
      expect(container.querySelector('.badge--medium')).toBeTruthy();
    });
  });
});
