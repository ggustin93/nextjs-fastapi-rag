'use client';

import { useState, useEffect, useMemo } from 'react';
import dynamic from 'next/dynamic';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useMediaQuery } from '@/hooks/useMediaQuery';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { FileText, ChevronLeft, ChevronRight, ChevronDown, Loader2, ZoomIn, ZoomOut, Maximize2, Globe2, FileType, FileCode } from 'lucide-react';
import type { Source } from '@/types/chat';
import { IframeViewer } from './IframeViewer';

// Styles
import 'react-pdf/dist/Page/TextLayer.css';
import 'react-pdf/dist/Page/AnnotationLayer.css';

// Configure PDF.js worker on the client only (avoid server-side evaluation that
// tries to access browser globals like `DOMMatrix` inside pdfjs-dist).
// We set this up in a useEffect below so the module isn't imported at module
// evaluation time on the server.

// Lazy load PDF components with proper options
const Document = dynamic(
  () => import('react-pdf').then((mod) => mod.Document),
  { ssr: false, loading: () => <div className="flex gap-2 p-4"><Loader2 className="animate-spin" /> Loading PDF...</div> }
);
const Page = dynamic(
  () => import('react-pdf').then((mod) => mod.Page),
  { ssr: false }
);

// Helper to clean API URLs
const getDocumentUrl = (path: string) => {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
  // Strip prefixes to ensure clean relative path
  const cleanPath = path
    .replace(/^documents\//, '')
    .replace(/^data\//, '')
    .normalize('NFC');

  return `${baseUrl}/documents/${cleanPath.split('/').map(encodeURIComponent).join('/')}`;
};

interface DocumentViewerProps {
  source: Source;
  index?: number;
  onOpenDocument?: (source: Source) => void;
}

export function DocumentViewer({ source, index, onOpenDocument }: DocumentViewerProps) {
  const isDesktop = useMediaQuery('(min-width: 768px)');
  const [isOpen, setIsOpen] = useState(false);

  // Viewer State
  const [numPages, setNumPages] = useState<number>(0);
  const [pageNumber, setPageNumber] = useState<number>(source.page_number || 1);
  const [scale, setScale] = useState<number>(1.0);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Data State
  const [pdfData, setPdfData] = useState<ArrayBuffer | null>(null);
  const [mdContent, setMdContent] = useState<string | null>(null);

  const isPdf = source.path.toLowerCase().endsWith('.pdf');
  const file = useMemo(() => (pdfData ? { data: pdfData } : null), [pdfData]);

  // Fetch Data
  useEffect(() => {
    if (!isOpen) return;

    const controller = new AbortController();
    setIsLoading(true);
    setError(null);
    setPdfData(null);
    setMdContent(null);

    const fetchData = async () => {
      try {
        const url = getDocumentUrl(source.path);
        const res = await fetch(url, { signal: controller.signal });

        if (!res.ok) throw new Error(`Status ${res.status}`);

        if (isPdf) {
          const data = await res.arrayBuffer();
          if (data.byteLength === 0) throw new Error("Empty file");
          setPdfData(data);
          // Note: isLoading stays true for PDF until React-PDF renders (onLoadSuccess)
        } else {
          const text = await res.text();
          setMdContent(text);
          setIsLoading(false);
        }
      } catch (err: unknown) {
        const error = err as Error;
        if (error.name !== 'AbortError') {
          setError(error.message || 'Error loading document');
          setIsLoading(false);
        }
      }
    };

    fetchData();
    return () => controller.abort();
  }, [isOpen, source.path, isPdf]);

  // Initialize PDF.js worker on the client when the viewer opens for a PDF.
  useEffect(() => {
    if (isPdf && isOpen) {
      import('react-pdf')
        .then((pdf) => {
          pdf.pdfjs.GlobalWorkerOptions.workerSrc =
            `https://unpkg.com/pdfjs-dist@${pdf.pdfjs.version}/build/pdf.worker.mjs`;
        })
        .catch((err) => {
          // Don't crash - just log worker init failures
          // (keeps server-side rendering safe if import somehow happens)

          console.warn('Failed to initialize pdfjs worker', err);
        });
    }
  }, [isPdf, isOpen]);

  // Auto-scroll to source page when modal opens
  useEffect(() => {
    if (isOpen && source.page_number) {
      setPageNumber(source.page_number);
    }
  }, [isOpen, source.page_number]);

  // Handlers
  const onDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
    setNumPages(numPages);
    setIsLoading(false); // PDF is ready visually
  };

  const renderContent = () => {
    const isWebSource = Boolean(source.url);

    if (error) return <div className="p-8 text-destructive text-center">{error}</div>;

    if (isLoading && !pdfData && !mdContent) {
      return (
        <div className="flex items-center gap-2 text-muted-foreground p-10">
          <Loader2 className="h-5 w-5 animate-spin" /> Retrieving document...
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
        <article className="prose prose-sm dark:prose-invert max-w-none p-6">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{mdContent}</ReactMarkdown>
        </article>
      );
    }

    // PDF rendering (unchanged)
    if (isPdf && pdfData) {
      return (
        <div className="flex justify-center bg-muted/30 p-4">
          <Document
            file={file}
            onLoadSuccess={onDocumentLoadSuccess}
            onLoadError={(err) => setError(err.message)}
            loading={<div className="flex gap-2 p-4"><Loader2 className="animate-spin" /> Rendering PDF...</div>}
          >
            <Page pageNumber={pageNumber} scale={scale} renderTextLayer={false} renderAnnotationLayer={false} />
          </Document>
        </div>
      );
    }
    return null;
  };

  // Helper function to get single type-specific icon
  const getTypeIcon = () => {
    if (source.url) {
      return <Globe2 className="h-3 w-3 mr-1 text-blue-500" />;
    }
    if (isPdf) {
      return <FileType className="h-3 w-3 mr-1 text-red-500" />;
    }
    return <FileCode className="h-3 w-3 mr-1 text-green-500" />;
  };

  // Button Trigger
  const TriggerButton = (
    <Button variant="ghost" size="sm" className="h-auto py-0.5 px-1.5 text-[11px] hover:bg-muted" onClick={() => isDesktop && onOpenDocument?.(source)}>
      {index && <span className="font-mono text-muted-foreground mr-1 text-[10px]">[{index}]</span>}
      {getTypeIcon()}
      <span className="truncate max-w-[200px]">{source.title}</span>
      <Badge variant="secondary" className="ml-1 text-[9px] px-1 py-0">{Math.round(source.similarity * 100)}%</Badge>
    </Button>
  );

  if (isDesktop && onOpenDocument) return TriggerButton;

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>{TriggerButton}</DialogTrigger>
      <DialogContent className="max-w-4xl h-[85vh] flex flex-col p-0 gap-0">
        <DialogHeader className="px-6 py-4 border-b">
          <DialogTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" /> {source.title}
          </DialogTitle>
        </DialogHeader>

        <div className="flex-1 overflow-auto">{renderContent()}</div>

        {isPdf && !isLoading && !error && (
          <div className="p-2 border-t bg-muted/10 flex justify-between items-center">
            <div className="flex gap-1">
              <Button variant="ghost" size="sm" onClick={() => setScale(s => Math.max(0.5, s - 0.25))}><ZoomOut className="h-4 w-4" /></Button>
              <Button variant="ghost" size="sm" onClick={() => setScale(1)}><Maximize2 className="h-4 w-4" /></Button>
              <Button variant="ghost" size="sm" onClick={() => setScale(s => Math.min(2, s + 0.25))}><ZoomIn className="h-4 w-4" /></Button>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={() => setPageNumber(p => Math.max(1, p - 1))} disabled={pageNumber <= 1}><ChevronLeft className="h-4 w-4" /></Button>
              <span className="text-sm">{pageNumber} / {numPages}</span>
              <Button variant="outline" size="sm" onClick={() => setPageNumber(p => Math.min(numPages, p + 1))} disabled={pageNumber >= numPages}><ChevronRight className="h-4 w-4" /></Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

interface SourcesListProps {
  sources: Source[];
  onOpenDocument?: (source: Source) => void;
}

export function SourcesList({ sources, onOpenDocument }: SourcesListProps) {
  const [isExpanded, setIsExpanded] = useState(true);

  if (!sources || sources.length === 0) return null;

  return (
    <div className="mt-3 pt-3 border-t border-border/50">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-1 text-xs text-muted-foreground mb-2 hover:text-foreground transition-colors"
      >
        {isExpanded ? (
          <ChevronDown className="h-3 w-3" />
        ) : (
          <ChevronRight className="h-3 w-3" />
        )}
        <span>Sources consultées ({sources.length})</span>
      </button>

      {isExpanded && (
        <div className="flex flex-wrap gap-1">
          {sources.map((source, index) => (
            <DocumentViewer
              key={index}
              source={source}
              index={index + 1}
              onOpenDocument={onOpenDocument}
            />
          ))}
        </div>
      )}
    </div>
  );
}
