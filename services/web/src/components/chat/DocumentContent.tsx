'use client';

import { useState, useEffect, useMemo } from 'react';
import dynamic from 'next/dynamic';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Button } from '@/components/ui/button';
import { Loader2, ChevronLeft, ChevronRight, ZoomIn, ZoomOut, Maximize2, AlertCircle } from 'lucide-react';
import type { Source } from '@/types/chat';
import { IframeViewer } from './IframeViewer';

import 'react-pdf/dist/Page/TextLayer.css';
import 'react-pdf/dist/Page/AnnotationLayer.css';

const Document = dynamic(() => import('react-pdf').then((mod) => mod.Document), { ssr: false });
const Page = dynamic(() => import('react-pdf').then((mod) => mod.Page), { ssr: false });

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
  const [numPages, setNumPages] = useState<number>(0);
  const [pageNumber, setPageNumber] = useState<number>(1);
  const [scale, setScale] = useState<number>(1.0);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [pdfData, setPdfData] = useState<ArrayBuffer | null>(null);
  const [mdContent, setMdContent] = useState<string | null>(null);

  const isPdf = source.path.toLowerCase().endsWith('.pdf');
  const file = useMemo(() => (pdfData ? { data: pdfData } : null), [pdfData]);

  // 1. Worker Init
  useEffect(() => {
    if (isPdf) {
      import('react-pdf').then((pdf) => {
        pdf.pdfjs.GlobalWorkerOptions.workerSrc =
          `https://unpkg.com/pdfjs-dist@${pdf.pdfjs.version}/build/pdf.worker.min.mjs`;
      });
    }
  }, [isPdf]);

  // 2. Data Fetch
  useEffect(() => {
    const controller = new AbortController();
    setIsLoading(true);
    setError(null);
    setPdfData(null);
    setMdContent(null);
    setPageNumber(1);

    const fetchData = async () => {
      try {
        console.log("Fetching:", source.path);
        const res = await fetch(getDocumentUrl(source.path), { signal: controller.signal });

        if (!res.ok) throw new Error(`Status ${res.status}`);

        if (isPdf) {
          const data = await res.arrayBuffer();
          if (data.byteLength === 0) throw new Error("File empty");
          setPdfData(data);
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
    return () => controller.abort();
  }, [source.path, isPdf]);

  // Renderers
  const isWebSource = Boolean(source.url);

  if (error) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-6 text-destructive text-center">
        <AlertCircle className="h-8 w-8 mb-2" />
        <p className="font-semibold">Error loading document</p>
        <p className="text-xs mt-2 font-mono bg-muted p-2 rounded">{error}</p>
      </div>
    );
  }

  if (isLoading && !pdfData && !mdContent) {
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

  // PDF rendering (unchanged)
  if (isPdf && pdfData) {
    return (
      <div className="h-full flex flex-col">
        <div className="flex-1 overflow-auto flex justify-center bg-muted/20 p-4">
          <Document
            file={file}
            onLoadSuccess={({ numPages }) => { setNumPages(numPages); setIsLoading(false); }}
            onLoadError={(err) => setError(err.message)}
            loading={<div className="flex items-center gap-2"><Loader2 className="animate-spin" /> Rendering...</div>}
            className="shadow-lg"
          >
            <Page pageNumber={pageNumber} scale={scale} renderTextLayer={false} renderAnnotationLayer={false} />
          </Document>
        </div>

        {!isLoading && (
          <div className="p-3 border-t flex justify-between items-center bg-background">
             <div className="flex gap-1">
              <Button variant="ghost" size="sm" onClick={() => setScale(s => Math.max(0.5, s - 0.25))}><ZoomOut className="h-4 w-4" /></Button>
              <Button variant="ghost" size="sm" onClick={() => setScale(1)}><Maximize2 className="h-4 w-4" /></Button>
              <Button variant="ghost" size="sm" onClick={() => setScale(s => Math.min(2, s + 0.25))}><ZoomIn className="h-4 w-4" /></Button>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={() => setPageNumber(p => Math.max(1, p - 1))} disabled={pageNumber <= 1}><ChevronLeft className="h-4 w-4" /></Button>
              <span className="text-sm font-medium w-16 text-center">{pageNumber} / {numPages}</span>
              <Button variant="outline" size="sm" onClick={() => setPageNumber(p => Math.min(numPages, p + 1))} disabled={pageNumber >= numPages}><ChevronRight className="h-4 w-4" /></Button>
            </div>
          </div>
        )}
      </div>
    );
  }

  return null;
}
