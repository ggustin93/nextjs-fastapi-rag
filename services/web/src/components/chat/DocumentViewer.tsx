'use client';

import { useState, useEffect, useMemo, useCallback } from 'react';
import dynamic from 'next/dynamic';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useMediaQuery } from '@/hooks/useMediaQuery';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { FileText, ChevronLeft, ChevronRight, ChevronDown, Loader2, ZoomIn, ZoomOut, Maximize2, Globe2, FileType, FileCode, Search, X, ExternalLink } from 'lucide-react';
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

/**
 * Format URL for compact display with intelligent truncation
 * - Short URLs: Show full (e.g., "example.com/page")
 * - Long URLs: Truncate middle (e.g., "example.com/.../page")
 * - Max length: ~40 characters
 */
const formatCompactUrl = (url: string): string => {
  try {
    const urlObj = new URL(url);
    const domain = urlObj.hostname.replace('www.', '');
    const path = urlObj.pathname + urlObj.search;

    // Remove trailing slash
    const cleanPath = path.endsWith('/') ? path.slice(0, -1) : path;

    // Full URL length check
    const fullUrl = domain + cleanPath;

    if (fullUrl.length <= 40) {
      return fullUrl;
    }

    // Truncate middle of path if too long
    const pathParts = cleanPath.split('/').filter(Boolean);
    if (pathParts.length > 2) {
      // Keep first and last segments, show "..." in middle
      return `${domain}/${pathParts[0]}/.../${pathParts[pathParts.length - 1]}`;
    }

    // If path is single long segment, truncate it
    if (cleanPath.length > 25) {
      return `${domain}${cleanPath.substring(0, 22)}...`;
    }

    return fullUrl;
  } catch {
    // Fallback for invalid URLs
    return url.substring(0, 40) + (url.length > 40 ? '...' : '');
  }
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
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [mdContent, setMdContent] = useState<string | null>(null);

  // Search State
  const [searchTerm, setSearchTerm] = useState<string>('');

  const isPdf = source.path.toLowerCase().endsWith('.pdf');

  // Escape regex special characters
  const escapeRegex = (text: string) => text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

  // Custom text renderer for search highlighting
  const customTextRenderer = useCallback(({ str }: { str: string }) => {
    if (!searchTerm) return str;

    const regex = new RegExp(`(${escapeRegex(searchTerm)})`, 'gi');
    const parts = str.split(regex);

    return parts
      .map((part) =>
        regex.test(part)
          ? `<mark style="background-color: #fef08a; padding: 2px;">${part}</mark>`
          : part
      )
      .join('');
  }, [searchTerm]);

  // Fetch Data
  useEffect(() => {
    if (!isOpen) return;

    const controller = new AbortController();
    setIsLoading(true);
    setError(null);
    setMdContent(null);

    let currentBlobUrl: string | null = null;

    const fetchData = async () => {
      try {
        const url = getDocumentUrl(source.path);
        const res = await fetch(url, { signal: controller.signal });

        if (!res.ok) throw new Error(`Status ${res.status}`);

        if (isPdf) {
          const blob = await res.blob();
          if (blob.size === 0) throw new Error("Empty file");
          currentBlobUrl = URL.createObjectURL(blob);
          setPdfUrl(currentBlobUrl);
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

    return () => {
      controller.abort();
      // Cleanup blob URL to prevent memory leaks
      if (currentBlobUrl) {
        URL.revokeObjectURL(currentBlobUrl);
      }
    };
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

    if (isLoading && !pdfUrl && !mdContent) {
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

    // PDF rendering with search support
    if (isPdf && pdfUrl) {
      return (
        <div className="flex justify-center bg-muted/30 p-4">
          <Document
            file={pdfUrl}
            onLoadSuccess={onDocumentLoadSuccess}
            onLoadError={(err) => setError(err.message)}
            loading={<div className="flex gap-2 p-4"><Loader2 className="animate-spin" /> Rendering PDF...</div>}
          >
            <Page
              pageNumber={pageNumber}
              scale={scale}
              renderTextLayer={true}
              customTextRenderer={customTextRenderer}
              renderAnnotationLayer={false}
            />
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
    <Button
      variant="ghost"
      size="sm"
      className="h-auto py-1 px-1.5 text-[11px] hover:bg-muted flex-col items-start"
      onClick={() => isDesktop && onOpenDocument?.(source)}
    >
      <div className="flex items-center w-full">
        {index && <span className="font-mono text-muted-foreground mr-1 text-[10px]">[{index}]</span>}
        {getTypeIcon()}
        <span className="truncate max-w-[200px]">{source.title}</span>
        {source.page_range && (
          <Badge variant="outline" className="ml-1 text-[9px] px-1 py-0">{source.page_range}</Badge>
        )}
        <Badge variant="secondary" className="ml-1 text-[9px] px-1 py-0">{Math.round(source.similarity * 100)}%</Badge>
      </div>

      {/* Clickable URL subtitle for web sources */}
      {source.url && (
        <a
          href={source.url}
          target="_blank"
          rel="noopener noreferrer"
          onClick={(e) => e.stopPropagation()} // Prevent triggering parent button's document viewer
          className="flex items-center gap-1 text-[10px] text-muted-foreground hover:text-foreground ml-5 mt-0.5 underline decoration-dotted underline-offset-2 transition-colors"
          aria-label={`Open ${source.url} in new tab`}
          title={source.url}
        >
          <span>{formatCompactUrl(source.url)}</span>
          <ExternalLink className="h-3 w-3" aria-hidden="true" />
        </a>
      )}
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

        {/* Search toolbar for PDFs */}
        {isPdf && !isLoading && !error && (
          <div className="px-4 py-2 border-b bg-muted/5 flex items-center gap-2">
            <Search className="h-4 w-4 text-muted-foreground" />
            <Input
              type="text"
              placeholder="Search in document..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="h-8 text-sm flex-1"
            />
            {searchTerm && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setSearchTerm('')}
                className="h-8 px-2"
              >
                <X className="h-4 w-4" />
              </Button>
            )}
          </div>
        )}

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
