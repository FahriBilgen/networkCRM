import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { exportGraphElement } from './exportGraph';

const addImageMock = vi.fn();
const saveMock = vi.fn();

vi.mock('html-to-image', () => ({
  toPng: vi.fn(() => Promise.resolve('data:image/png;base64,fake')),
}));

vi.mock('jspdf', () => ({
  default: vi.fn(() => ({
    internal: {
      pageSize: {
        getWidth: () => 800,
        getHeight: () => 600,
      },
    },
    addImage: addImageMock,
    save: saveMock,
  })),
}));

describe('exportGraphElement', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('downloads the graph as PNG by default', async () => {
    const element = document.createElement('div');
    element.getBoundingClientRect = () =>
      ({
        width: 500,
        height: 300,
        x: 0,
        y: 0,
        top: 0,
        left: 0,
        right: 500,
        bottom: 300,
        toJSON: () => ({}),
      }) as DOMRect;
    document.body.appendChild(element);
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});

    const result = await exportGraphElement(element);

    expect(result.format).toBe('png');
    expect(clickSpy).toHaveBeenCalled();
    clickSpy.mockRestore();
    document.body.removeChild(element);
  });

  it('creates a PDF when format is pdf', async () => {
    const element = document.createElement('div');
    element.getBoundingClientRect = () =>
      ({
        width: 600,
        height: 800,
        x: 0,
        y: 0,
        top: 0,
        left: 0,
        right: 600,
        bottom: 800,
        toJSON: () => ({}),
      }) as DOMRect;
    document.body.appendChild(element);

    const result = await exportGraphElement(element, { format: 'pdf', fileName: 'export-test' });

    expect(result.format).toBe('pdf');
    expect(addImageMock).toHaveBeenCalledWith(expect.any(String), 'PNG', 0, expect.any(Number), expect.any(Number), expect.any(Number));
    expect(saveMock).toHaveBeenCalledWith('export-test.pdf');
    document.body.removeChild(element);
  });
});
