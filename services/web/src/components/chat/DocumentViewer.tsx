'use client';

import { useState, useEffect, useMemo } from 'react';
import dynamic from 'next/dynamic';

// Import react-pdf styles for TextLayer and AnnotationLayer
import 'react-pdf/dist/Page/TextLayer.css';
import 'react-pdf/dist/Page/AnnotationLayer.css';

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { FileText, ChevronLeft, ChevronRight, Loader2, ZoomIn, ZoomOut, Maximize2 } from 'lucide-react';
import type { Source } from '@/types/chat';

// Dynamically import react-pdf components to avoid SSR issues
const Document = dynamic(
  () => import('react-pdf').then((mod) => mod.Document),
  { ssr: false }
);

const Page = dynamic(
  () => import('react-pdf').then((mod) => mod.Page),
  { ssr: false }
);

interface DocumentViewerProps {
  source: Source;
}

export function DocumentViewer({ source }: DocumentViewerProps) {
  const [numPages, setNumPages] = useState<number>(0);
  const [pageNumber, setPageNumber] = useState<number>(1);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isWorkerReady, setIsWorkerReady] = useState<boolean>(false);
  const [scale, setScale] = useState<number>(1.0);
  const [pdfData, setPdfData] = useState<ArrayBuffer | null>(null);

  const zoomIn = () => setScale((s) => Math.min(2.0, s + 0.25));
  const zoomOut = () => setScale((s) => Math.max(0.5, s - 0.25));
  const resetZoom = () => setScale(1.0);

  const similarityPercent = Math.round(source.similarity * 100);

  // Memoize file prop to avoid unnecessary reloads
  const file = useMemo(() => (pdfData ? { data: pdfData } : null), [pdfData]);

  // Configure PDF.js worker on client side only
  useEffect(() => {
    import('react-pdf').then((reactPdf) => {
      reactPdf.pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${reactPdf.pdfjs.version}/build/pdf.worker.min.mjs`;
      setIsWorkerReady(true);
    });
  }, []);

  // Fetch PDF data when dialog opens
  const fetchPdf = async (url: string) => {
    try {
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      const data = await response.arrayBuffer();
      setPdfData(data);
    } catch (err) {
      console.error('PDF fetch error:', err);
      setError(`Erreur de chargement: ${err instanceof Error ? err.message : 'Unknown error'}\n\nURL: ${url}`);
      setIsLoading(false);
    }
  };

  // Build API URL for document - strip 'documents/' prefix if present
  const getDocumentUrl = (path: string) => {
    const cleanPath = path.replace(/^documents\//, '');
    // Encode path components to handle spaces and special characters
    const encodedPath = cleanPath.split('/').map(encodeURIComponent).join('/');
    return `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/documents/${encodedPath}`;
  };

  const onDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
    setNumPages(numPages);
    setIsLoading(false);
    setError(null);
  };

  const onDocumentLoadError = (err: Error) => {
    setIsLoading(false);
    const url = getDocumentUrl(source.path);
    console.error('PDF load error:', { error: err.message, url, path: source.path });
    setError(`${err.message || 'Erreur de chargement'}\n\nURL: ${url}`);
  };

  const goToPrevPage = () => setPageNumber((p) => Math.max(1, p - 1));
  const goToNextPage = () => setPageNumber((p) => Math.min(numPages, p + 1));

  // Reset state when dialog opens
  const handleOpenChange = (open: boolean) => {
    if (open) {
      setPageNumber(1);
      setIsLoading(true);
      setError(null);
      setScale(1.0);
      setPdfData(null);
      // Fetch PDF data
      const url = getDocumentUrl(source.path);
      fetchPdf(url);
    }
  };

  return (
    <Dialog onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className="h-auto py-1 px-2 text-xs hover:bg-muted"
        >
          <FileText className="h-3 w-3 mr-1" />
          {source.title}
          <Badge variant="secondary" className="ml-2 text-[10px] px-1">
            {similarityPercent}%
          </Badge>
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-6xl max-h-[95vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            {source.title}
            <Badge variant="outline" className="ml-auto">
              Pertinence: {similarityPercent}%
            </Badge>
          </DialogTitle>
        </DialogHeader>

        {/* PDF Viewer */}
        <div className="flex-1 overflow-auto border rounded-md bg-muted/30 flex items-center justify-center min-h-[600px]">
          {error ? (
            <div className="text-center p-8 text-destructive max-w-md">
              <p className="font-medium">Erreur de chargement</p>
              <p className="text-sm text-muted-foreground mt-1 whitespace-pre-wrap break-all">{error}</p>
            </div>
          ) : !isWorkerReady || !pdfData ? (
            <div className="flex items-center gap-2 text-muted-foreground">
              <Loader2 className="h-5 w-5 animate-spin" />
              {!isWorkerReady ? 'Initialisation...' : 'Chargement du PDF...'}
            </div>
          ) : (
            <Document
              file={file}
              onLoadSuccess={onDocumentLoadSuccess}
              onLoadError={onDocumentLoadError}
              loading={
                <div className="flex items-center gap-2 text-muted-foreground">
                  <Loader2 className="h-5 w-5 animate-spin" />
                  Rendu du PDF...
                </div>
              }
            >
              <Page
                pageNumber={pageNumber}
                scale={scale}
                loading={
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Chargement de la page...
                  </div>
                }
              />
            </Document>
          )}
        </div>

        {/* Navigation and Zoom Controls */}
        {!error && numPages > 0 && (
          <div className="flex items-center justify-between pt-4 border-t">
            {/* Zoom Controls */}
            <div className="flex items-center gap-1">
              <Button
                variant="outline"
                size="sm"
                onClick={zoomOut}
                disabled={scale <= 0.5 || isLoading}
                title="Zoom arrière"
              >
                <ZoomOut className="h-4 w-4" />
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={resetZoom}
                disabled={isLoading}
                title="Réinitialiser le zoom"
              >
                <Maximize2 className="h-4 w-4" />
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={zoomIn}
                disabled={scale >= 2.0 || isLoading}
                title="Zoom avant"
              >
                <ZoomIn className="h-4 w-4" />
              </Button>
              <span className="text-xs text-muted-foreground ml-2">
                {Math.round(scale * 100)}%
              </span>
            </div>

            {/* Page Navigation */}
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={goToPrevPage}
                disabled={pageNumber <= 1 || isLoading}
              >
                <ChevronLeft className="h-4 w-4 mr-1" />
                Précédent
              </Button>
              <span className="text-sm text-muted-foreground">
                Page {pageNumber} / {numPages}
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={goToNextPage}
                disabled={pageNumber >= numPages || isLoading}
              >
                Suivant
                <ChevronRight className="h-4 w-4 ml-1" />
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

interface SourcesListProps {
  sources: Source[];
}

export function SourcesList({ sources }: SourcesListProps) {
  if (!sources || sources.length === 0) return null;

  return (
    <div className="mt-3 pt-3 border-t border-border/50">
      <p className="text-xs text-muted-foreground mb-2">Sources consultées:</p>
      <div className="flex flex-wrap gap-1">
        {sources.map((source, index) => (
          <DocumentViewer key={index} source={source} />
        ))}
      </div>
    </div>
  );
}
