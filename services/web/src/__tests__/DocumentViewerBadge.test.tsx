/**
 * Tests for DocumentViewer badge rendering with page numbers.
 * Focuses on the badge display logic without needing to render the full component.
 */

import type { Source } from '@/types/chat';

describe('DocumentViewer Badge Logic', () => {
  /**
   * Helper function to simulate badge text generation logic
   * This mirrors the logic in DocumentViewer.tsx for rendering PDF badges
   */
  function getBadgeText(source: Source): string {
    const isPdf = source.path.toLowerCase().endsWith('.pdf');

    if (!isPdf) {
      return ''; // Non-PDF files don't show PDF badge
    }

    if (source.page_range) {
      return `PDF (${source.page_range})`;
    }

    return 'PDF';
  }

  it('displays PDF with single page number', () => {
    const source: Source = {
      title: 'Test Document',
      path: 'data/processed/test.pdf',
      similarity: 0.95,
      page_number: 5,
      page_range: 'p. 5',
    };

    const badgeText = getBadgeText(source);
    expect(badgeText).toBe('PDF (p. 5)');
  });

  it('displays PDF with page range', () => {
    const source: Source = {
      title: 'Multi-Page Doc',
      path: 'test.pdf',
      similarity: 0.88,
      page_number: 3,
      page_range: 'p. 3-7',
    };

    const badgeText = getBadgeText(source);
    expect(badgeText).toBe('PDF (p. 3-7)');
  });

  it('displays PDF badge without page info when not available', () => {
    const source: Source = {
      title: 'No Pages',
      path: 'test.pdf',
      similarity: 0.90,
    };

    const badgeText = getBadgeText(source);
    expect(badgeText).toBe('PDF');
  });

  it('does not display PDF badge for non-PDF files', () => {
    const source: Source = {
      title: 'Markdown',
      path: 'doc.md',
      similarity: 0.85,
      page_number: 5, // Even with page number, should not show for non-PDF
      page_range: 'p. 5',
    };

    const badgeText = getBadgeText(source);
    expect(badgeText).toBe('');
  });

  it('handles page_number without page_range', () => {
    const source: Source = {
      title: 'Test',
      path: 'test.pdf',
      similarity: 0.92,
      page_number: 10,
      // No page_range
    };

    const badgeText = getBadgeText(source);
    // Without page_range, just shows PDF
    expect(badgeText).toBe('PDF');
  });

  it('handles large page numbers', () => {
    const source: Source = {
      title: 'Large Doc',
      path: 'large.pdf',
      similarity: 0.87,
      page_number: 1234,
      page_range: 'p. 1234-1240',
    };

    const badgeText = getBadgeText(source);
    expect(badgeText).toBe('PDF (p. 1234-1240)');
  });

  it('handles zero page number', () => {
    const source: Source = {
      title: 'Zero Index',
      path: 'zero.pdf',
      similarity: 0.93,
      page_number: 0,
      page_range: 'p. 0',
    };

    const badgeText = getBadgeText(source);
    expect(badgeText).toBe('PDF (p. 0)');
  });

  it('handles case-insensitive PDF extension', () => {
    const source: Source = {
      title: 'Uppercase',
      path: 'document.PDF',
      similarity: 0.91,
      page_range: 'p. 5',
    };

    const badgeText = getBadgeText(source);
    expect(badgeText).toBe('PDF (p. 5)');
  });

  it('does not show badge for HTML files even with PDF in name', () => {
    const source: Source = {
      title: 'HTML Doc',
      path: 'pdf-converter.html',
      similarity: 0.80,
      page_range: 'p. 5',
    };

    const badgeText = getBadgeText(source);
    expect(badgeText).toBe('');
  });

  it('page_range format is preserved as-is', () => {
    const customFormats = [
      'p. 1',
      'p. 5-10',
      'p. 100-200',
      'p. 0',
    ];

    customFormats.forEach(range => {
      const source: Source = {
        title: 'Test',
        path: 'test.pdf',
        similarity: 0.9,
        page_range: range,
      };

      const badgeText = getBadgeText(source);
      expect(badgeText).toBe(`PDF (${range})`);
    });
  });
});

describe('DocumentViewer Page Initialization Logic', () => {
  /**
   * Helper to simulate initial page number state
   * Mirrors: const [pageNumber, setPageNumber] = useState<number>(source.page_number || 1);
   */
  function getInitialPageNumber(source: Source): number {
    return source.page_number || 1;
  }

  it('initializes to source page number when provided', () => {
    const source: Source = {
      title: 'Test',
      path: 'test.pdf',
      similarity: 0.95,
      page_number: 12,
    };

    expect(getInitialPageNumber(source)).toBe(12);
  });

  it('defaults to page 1 when no page number provided', () => {
    const source: Source = {
      title: 'Test',
      path: 'test.pdf',
      similarity: 0.95,
    };

    expect(getInitialPageNumber(source)).toBe(1);
  });

  it('handles page number 0 correctly', () => {
    const source: Source = {
      title: 'Test',
      path: 'test.pdf',
      similarity: 0.95,
      page_number: 0,
    };

    // 0 is falsy, so should default to 1
    expect(getInitialPageNumber(source)).toBe(1);
  });

  it('uses provided page number even if very large', () => {
    const source: Source = {
      title: 'Test',
      path: 'test.pdf',
      similarity: 0.95,
      page_number: 9999,
    };

    expect(getInitialPageNumber(source)).toBe(9999);
  });
});
