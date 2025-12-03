'use client';

import { useState, useEffect } from 'react';
import dynamic from 'next/dynamic';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useMediaQuery } from '@/hooks/useMediaQuery';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  FileText, ChevronDown, ChevronRight,
  Loader2,
  Globe2, FileType, FileCode, ExternalLink
} from 'lucide-react';
import type { Source } from '@/types/chat';
import { IframeViewer } from './IframeViewer';
import { useDocumentFetch } from './hooks/useDocumentFetch';
import { formatCompactUrl } from './utils/formatUrl';
import type { PdfViewerProps } from './PdfViewer';

const PdfViewer = dynamic<PdfViewerProps>(
  () => import('./PdfViewer').then((mod) => mod.PdfViewer),
  { ssr: false, loading: () => <LoadingSpinner message="Loading PDF viewer..." /> }
);

// --- Shared Components ---

function LoadingSpinner({ message }: { message: string }) {
  return (
    <div className="flex items-center gap-2 text-muted-foreground p-8">
      <Loader2 className="h-5 w-5 animate-spin" />
      {message}
    </div>
  );
}

function ErrorDisplay({ message }: { message: string }) {
  return <div className="p-8 text-destructive text-center">{message}</div>;
}

function SourceTypeIcon({ source }: { source: Source }) {
  if (source.url) return <Globe2 className="h-3 w-3 mr-1 text-blue-500" />;
  if (source.path.toLowerCase().endsWith('.pdf')) return <FileType className="h-3 w-3 mr-1 text-red-500" />;
  return <FileCode className="h-3 w-3 mr-1 text-green-500" />;
}

// --- Main Component ---

interface DocumentViewerProps {
  source: Source;
  index?: number;
  onOpenDocument?: (source: Source) => void;
}

export function DocumentViewer({ source, index, onOpenDocument }: DocumentViewerProps) {
  const isDesktop = useMediaQuery('(min-width: 768px)');
  const [isOpen, setIsOpen] = useState(false);

  // Viewer state
  const [numPages, setNumPages] = useState(0);
  const [pageNumber, setPageNumber] = useState(source.page_number || 1);

  const isPdf = source.path.toLowerCase().endsWith('.pdf');
  const isWebSource = Boolean(source.url);

  // Fetch document content
  const { pdfUrl, mdContent, isLoading, error } = useDocumentFetch({
    path: source.path,
    isPdf,
    enabled: isOpen,
  });

  // Auto-scroll to source page when modal opens
  useEffect(() => {
    if (isOpen && source.page_number) setPageNumber(source.page_number);
  }, [isOpen, source.page_number]);

  // --- Render Helpers ---

  const renderContent = () => {
    if (error) return <ErrorDisplay message={error} />;
    if (isLoading) return <LoadingSpinner message="Retrieving document..." />;

    // Web source with iframe
    if (isWebSource && source.url && mdContent) {
      return <IframeViewer url={source.url} markdownContent={mdContent} title={source.title} />;
    }

    // Regular markdown
    if (!isPdf && !isWebSource && mdContent) {
      return (
        <article className="prose prose-sm dark:prose-invert max-w-none p-6">
          <Markdown remarkPlugins={[remarkGfm]}>{mdContent}</Markdown>
        </article>
      );
    }

    // PDF
    if (isPdf && pdfUrl) {
      return (
        <div className="flex justify-center bg-muted/30 p-4 h-full">
          <PdfViewer
            file={pdfUrl}
            pageNumber={pageNumber}
            onLoadSuccess={({ numPages }) => setNumPages(numPages)}
            onLoadError={(err) => console.error('PDF load error:', err)}
          />
        </div>
      );
    }

    return null;
  };

  // --- Trigger Button ---

  // Extract domain from URL
  const getDomain = (url: string) => {
    try {
      return new URL(url).hostname.replace('www.', '');
    } catch {
      return url;
    }
  };

  const TriggerButton = (
    <Button
      variant="ghost"
      size="sm"
      className="h-auto py-1 px-1.5 text-[11px] hover:bg-muted w-full"
      onClick={() => isDesktop && onOpenDocument?.(source)}
    >
      <div className="flex items-center justify-between w-full gap-2">
        <div className="flex items-center min-w-0">
          {index && <span className="font-mono text-muted-foreground mr-1 text-[10px]">[{index}]</span>}
          <SourceTypeIcon source={source} />
          <span className="truncate max-w-[200px]">{source.title}</span>
          {source.page_range && <Badge variant="outline" className="ml-1 text-[9px] px-1 py-0">{source.page_range}</Badge>}
          <Badge variant="secondary" className="ml-1 text-[9px] px-1 py-0">{Math.round(source.similarity * 100)}%</Badge>
        </div>
        {source.url && (
          <a
            href={source.url}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="flex items-center gap-1 text-[10px] text-muted-foreground hover:text-foreground transition-colors shrink-0"
            title={source.url}
          >
            <span className="truncate max-w-[120px]">{getDomain(source.url)}</span>
            <ExternalLink className="h-3 w-3 shrink-0" />
          </a>
        )}
      </div>
    </Button>
  );

  // Desktop: delegate to parent sidebar
  if (isDesktop && onOpenDocument) return TriggerButton;

  // Mobile: use dialog
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
      </DialogContent>
    </Dialog>
  );
}

// --- Sources List ---

interface SourcesListProps {
  sources: Source[];
  onOpenDocument?: (source: Source) => void;
}

export function SourcesList({ sources, onOpenDocument }: SourcesListProps) {
  const [isExpanded, setIsExpanded] = useState(true);

  if (!sources?.length) return null;

  return (
    <div className="mt-3 pt-3 border-t border-border/50">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-1 text-xs text-muted-foreground mb-2 hover:text-foreground transition-colors"
      >
        {isExpanded ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
        <span>Sources consultées ({sources.length})</span>
      </button>

      {isExpanded && (
        <div className="flex flex-col gap-1.5">
          {sources.map((source, i) => (
            <DocumentViewer key={i} source={source} index={i + 1} onOpenDocument={onOpenDocument} />
          ))}
        </div>
      )}
    </div>
  );
}
