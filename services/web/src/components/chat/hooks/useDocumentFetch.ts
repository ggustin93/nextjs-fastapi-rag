'use client';

import { useState, useEffect } from 'react';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

/**
 * Clean and build a document URL from a path
 */
export function getDocumentUrl(path: string): string {
  const cleanPath = path
    .replace(/^documents\//, '')
    .replace(/^data\//, '')
    .normalize('NFC');

  return `${API_BASE_URL}/documents/${cleanPath.split('/').map(encodeURIComponent).join('/')}`;
}

interface DocumentFetchState {
  pdfUrl: string | null;
  mdContent: string | null;
  isLoading: boolean;
  error: string | null;
}

interface UseDocumentFetchOptions {
  path: string;
  isPdf: boolean;
  enabled: boolean;
}

/**
 * Custom hook to fetch document content (PDF blob or markdown text)
 */
export function useDocumentFetch({ path, isPdf, enabled }: UseDocumentFetchOptions): DocumentFetchState {
  const [state, setState] = useState<DocumentFetchState>({
    pdfUrl: null,
    mdContent: null,
    isLoading: true,
    error: null,
  });

  useEffect(() => {
    if (!enabled) return;

    const controller = new AbortController();
    let blobUrl: string | null = null;

    setState({ pdfUrl: null, mdContent: null, isLoading: true, error: null });

    const fetchData = async () => {
      try {
        const url = getDocumentUrl(path);
        const res = await fetch(url, { signal: controller.signal });

        if (!res.ok) throw new Error(`Status ${res.status}`);

        if (isPdf) {
          const blob = await res.blob();
          if (blob.size === 0) throw new Error('Empty file');
          blobUrl = URL.createObjectURL(blob);
          setState((s) => ({ ...s, pdfUrl: blobUrl, isLoading: false }));
        } else {
          const text = await res.text();
          setState((s) => ({ ...s, mdContent: text, isLoading: false }));
        }
      } catch (err) {
        const error = err as Error;
        if (error.name !== 'AbortError') {
          setState((s) => ({ ...s, error: error.message || 'Error loading document', isLoading: false }));
        }
      }
    };

    fetchData();

    return () => {
      controller.abort();
      if (blobUrl) URL.revokeObjectURL(blobUrl);
    };
  }, [path, isPdf, enabled]);

  return state;
}
