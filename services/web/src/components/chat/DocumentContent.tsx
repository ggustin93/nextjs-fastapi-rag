'use client';

import { useState, useEffect } from 'react';
import dynamic from 'next/dynamic';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Loader2, AlertCircle } from 'lucide-react';
import type { Source } from '@/types/chat';
import { IframeViewer } from './IframeViewer';
import { PdfViewer } from './PdfViewer';

// Dynamic import for WorksiteMapViewer (Leaflet needs client-only)
const WorksiteMapViewer = dynamic(
  () => import('./WorksiteMapViewer').then(mod => mod.WorksiteMapViewer),
  { ssr: false, loading: () => <div className="h-full flex items-center justify-center"><Loader2 className="h-5 w-5 animate-spin" /></div> }
);

// Helper to clean API URLs
const getDocumentUrl = (path: string) => {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
  const cleanPath = path
    .replace(/^documents\//, '')
    .replace(/^data\//, '')
    .normalize('NFC');
  return `${baseUrl}/documents/${cleanPath.split('/').map(encodeURIComponent).join('/')}`;
};

export function DocumentContent({ source }: { source: Source; showControls?: boolean }) {
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [mdContent, setMdContent] = useState<string | null>(null);

  const isPdf = source.path.toLowerCase().endsWith('.pdf');

  // Data Fetch (skip for inline content)
  useEffect(() => {
    // Non-PDF with inline content: render directly without fetch
    if (!isPdf && source.content) {
      setMdContent(source.content);
      setIsLoading(false);
      return;
    }

    const controller = new AbortController();
    setIsLoading(true);
    setError(null);
    setMdContent(null);
    setPdfUrl(null);

    let currentBlobUrl: string | null = null;

    const fetchData = async () => {
      try {
        console.log("Fetching:", source.path);
        const res = await fetch(getDocumentUrl(source.path), { signal: controller.signal });

        if (!res.ok) throw new Error(`Status ${res.status}`);

        if (isPdf) {
          const blob = await res.blob();
          if (blob.size === 0) throw new Error("File empty");
          currentBlobUrl = URL.createObjectURL(blob);
          setPdfUrl(currentBlobUrl);
          setIsLoading(false);
        } else {
          const text = await res.text();
          setMdContent(text);
          setIsLoading(false);
        }
      } catch (err) {
        if (err instanceof Error && err.name !== 'AbortError') {
          console.error(err);
          setError(err.message);
          setIsLoading(false);
        }
      }
    };

    fetchData();

    return () => {
      controller.abort();
      // Cleanup blob URL to prevent memory leaks
      if (currentBlobUrl) {
        URL.revokeObjectURL(currentBlobUrl);
      }
    };
  }, [source.path, source.content, isPdf]);

  // Renderers
  const isWebSource = Boolean(source.url);
  const hasGeometry = Boolean(source.geometry);

  // Worksite map rendering (OSIRIS tool)
  if (hasGeometry && source.geometry) {
    return (
      <WorksiteMapViewer
        geometry={source.geometry}
        worksiteInfo={source.worksiteInfo}
      />
    );
  }

  if (error) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-6 text-destructive text-center">
        <AlertCircle className="h-8 w-8 mb-2" />
        <p className="font-semibold">Error loading document</p>
        <p className="text-xs mt-2 font-mono bg-muted p-2 rounded">{error}</p>
      </div>
    );
  }

  if (isLoading && !pdfUrl && !mdContent) {
    return (
      <div className="h-full flex items-center justify-center text-muted-foreground gap-2">
        <Loader2 className="h-5 w-5 animate-spin" /> Loading content...
      </div>
    );
  }

  // Web source with iframe support
  if (isWebSource && source.url && mdContent) {
    return (
      <IframeViewer
        url={source.url}
        markdownContent={mdContent}
        title={source.title}
      />
    );
  }

  // Regular markdown (non-web sources)
  if (!isPdf && !isWebSource && mdContent) {
    return (
      <div className="h-full overflow-auto p-6">
        <article className="prose prose-sm dark:prose-invert max-w-none">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{mdContent}</ReactMarkdown>
        </article>
      </div>
    );
  }

  // PDF rendering using native browser viewer
  if (isPdf && pdfUrl) {
    return (
      <PdfViewer
        file={pdfUrl}
        pageNumber={source.page_number || 1}
        onLoadError={(err) => setError(err.message)}
      />
    );
  }

  return null;
}
