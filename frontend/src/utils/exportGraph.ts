import { toPng } from 'html-to-image';
import jsPDF from 'jspdf';

export type GraphExportFormat = 'png' | 'pdf';

export interface GraphExportOptions {
  format?: GraphExportFormat;
  fileName?: string;
  backgroundColor?: string;
}

export async function exportGraphElement(element: HTMLElement, options?: GraphExportOptions) {
  const format = options?.format ?? 'png';
  const fileName = options?.fileName?.trim() || 'network-graph';
  const backgroundColor = options?.backgroundColor ?? '#020617';
  const bounds = element.getBoundingClientRect();
  const targetWidth = Math.max(1, Math.round(bounds.width || 800));
  const targetHeight = Math.max(1, Math.round(bounds.height || 600));
  const pixelRatio = typeof window !== 'undefined' && window.devicePixelRatio ? Math.min(2, window.devicePixelRatio) : 1;

  const dataUrl = await toPng(element, {
    backgroundColor,
    pixelRatio: pixelRatio < 1 ? 1 : pixelRatio,
    canvasWidth: targetWidth,
    canvasHeight: targetHeight,
  });

  if (format === 'png') {
    triggerDownload(dataUrl, `${fileName}.png`);
    return { format, dataUrl };
  }

  const orientation = targetWidth >= targetHeight ? 'landscape' : 'portrait';
  const pdf = new jsPDF({
    orientation,
    unit: 'px',
    format: [targetWidth, targetHeight],
    compress: true,
  });
  const pageWidth = pdf.internal.pageSize.getWidth();
  const pageHeight = pdf.internal.pageSize.getHeight();
  const computedHeight = (targetHeight / targetWidth) * pageWidth;
  const yOffset = Math.max(0, (pageHeight - computedHeight) / 2);
  pdf.addImage(dataUrl, 'PNG', 0, yOffset, pageWidth, computedHeight);
  pdf.save(`${fileName}.pdf`);
  return { format, dataUrl };
}

function triggerDownload(dataUrl: string, filename: string) {
  const link = document.createElement('a');
  link.href = dataUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}
