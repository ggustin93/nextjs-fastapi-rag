import type { Source } from '@/types/chat';

describe('Source Type Interface', () => {
  it('accepts source with required fields only', () => {
    const source: Source = {
      title: 'Test Document',
      path: 'data/processed/test.pdf',
      similarity: 0.95,
    };

    expect(source.title).toBe('Test Document');
    expect(source.path).toBe('data/processed/test.pdf');
    expect(source.similarity).toBe(0.95);
  });

  it('accepts source with page_number', () => {
    const source: Source = {
      title: 'PDF Document',
      path: 'test.pdf',
      similarity: 0.88,
      page_number: 5,
    };

    expect(source.page_number).toBe(5);
  });

  it('accepts source with page_range', () => {
    const source: Source = {
      title: 'PDF Document',
      path: 'test.pdf',
      similarity: 0.88,
      page_range: 'p. 3-7',
    };

    expect(source.page_range).toBe('p. 3-7');
  });

  it('accepts source with both page_number and page_range', () => {
    const source: Source = {
      title: 'PDF Document',
      path: 'test.pdf',
      similarity: 0.88,
      page_number: 3,
      page_range: 'p. 3-7',
    };

    expect(source.page_number).toBe(3);
    expect(source.page_range).toBe('p. 3-7');
  });

  it('accepts source with url field', () => {
    const source: Source = {
      title: 'Web Document',
      path: 'scraped/doc.pdf',
      similarity: 0.90,
      url: 'https://example.com/doc.pdf',
      page_number: 10,
      page_range: 'p. 10-12',
    };

    expect(source.url).toBe('https://example.com/doc.pdf');
    expect(source.page_number).toBe(10);
  });

  it('page_number can be undefined', () => {
    const source: Source = {
      title: 'Document',
      path: 'doc.md',
      similarity: 0.85,
      page_number: undefined,
    };

    expect(source.page_number).toBeUndefined();
  });

  it('page_range can be undefined', () => {
    const source: Source = {
      title: 'Document',
      path: 'doc.md',
      similarity: 0.85,
      page_range: undefined,
    };

    expect(source.page_range).toBeUndefined();
  });

  it('accepts page_number as 0 for zero-indexed systems', () => {
    const source: Source = {
      title: 'Document',
      path: 'test.pdf',
      similarity: 0.95,
      page_number: 0,
      page_range: 'p. 0',
    };

    expect(source.page_number).toBe(0);
  });

  it('works with source deduplication logic', () => {
    // Simulate sources from API
    const sources: Source[] = [
      {
        title: 'Doc 1',
        path: 'test.pdf',
        similarity: 0.95,
        page_number: 5,
        page_range: 'p. 5',
      },
      {
        title: 'Doc 1',
        path: 'test.pdf',
        similarity: 0.88,
        page_number: 7,
        page_range: 'p. 7',
      },
    ];

    // Deduplication by path, keeping highest similarity
    const uniqueSources = sources.reduce((acc, source) => {
      const existing = acc.find((s) => s.path === source.path);
      if (!existing || source.similarity > existing.similarity) {
        return [...acc.filter((s) => s.path !== source.path), source];
      }
      return acc;
    }, [] as Source[]);

    expect(uniqueSources.length).toBe(1);
    expect(uniqueSources[0].similarity).toBe(0.95);
    expect(uniqueSources[0].page_number).toBe(5);
  });

  it('maintains type safety with optional fields', () => {
    // This test ensures TypeScript compilation catches type errors
    const validSource: Source = {
      title: 'Test',
      path: 'test.pdf',
      similarity: 0.9,
    };

    const validSourceWithPages: Source = {
      title: 'Test',
      path: 'test.pdf',
      similarity: 0.9,
      page_number: 5,
      page_range: 'p. 5',
    };

    // These should compile without errors
    expect(validSource.title).toBeDefined();
    expect(validSourceWithPages.page_number).toBeDefined();
  });

  it('page fields are optional and do not break existing code', () => {
    // Simulate legacy source objects without page fields
    const legacySource: Source = {
      title: 'Legacy Doc',
      path: 'legacy.pdf',
      similarity: 0.80,
    };

    // Should work without page fields
    expect(legacySource.page_number).toBeUndefined();
    expect(legacySource.page_range).toBeUndefined();
    expect(legacySource.title).toBe('Legacy Doc');
  });

  it('page fields do not interfere with url field', () => {
    const sourceWithAll: Source = {
      title: 'Complete Source',
      path: 'data/scraped/doc.pdf',
      similarity: 0.92,
      url: 'https://example.com/doc.pdf',
      page_number: 15,
      page_range: 'p. 15-18',
    };

    expect(sourceWithAll.url).toBe('https://example.com/doc.pdf');
    expect(sourceWithAll.page_number).toBe(15);
    expect(sourceWithAll.page_range).toBe('p. 15-18');
    expect(sourceWithAll.path).toBe('data/scraped/doc.pdf');
  });
});
