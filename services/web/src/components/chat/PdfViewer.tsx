'use client';

import { useState, useEffect, useRef } from 'react';
import { Loader2, Download, ExternalLink, Search } from 'lucide-react';
import { Button } from '@/components/ui/button';

export interface PdfViewerProps {
  file: string;
  pageNumber?: number;
  onLoadSuccess?: (data: { numPages: number }) => void;
  onLoadError?: (error: Error) => void;
}

/**
 * Native browser PDF viewer using iframe.
 * The browser's built-in PDF viewer provides zoom, search (Ctrl+F), and navigation.
 */
export function PdfViewer({
  file,
  pageNumber = 1,
  onLoadSuccess,
  onLoadError,
}: PdfViewerProps) {
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  const pdfUrl = pageNumber > 1 ? `${file}#page=${pageNumber}` : file;

  useEffect(() => {
    setIsLoading(true);
    setHasError(false);
  }, [file, pageNumber]);

  const handleLoad = () => {
    setIsLoading(false);
    onLoadSuccess?.({ numPages: 1 });
  };

  const handleError = () => {
    setIsLoading(false);
    setHasError(true);
    onLoadError?.(new Error('Failed to load PDF'));
  };

  // Note: Browser security prevents programmatic Ctrl+F in iframes
  // Users must use native keyboard shortcut directly

  if (hasError) {
    return (
      <div className="flex flex-col items-center justify-center p-8 text-center gap-4 h-full bg-muted/30">
        <div>
          <p className="font-medium text-foreground">Unable to display PDF</p>
          <p className="text-sm text-muted-foreground mt-1">
            Your browser may not support embedded PDF viewing.
          </p>
        </div>
        <div className="flex gap-2">
          <Button asChild variant="outline" size="sm">
            <a href={file} target="_blank" rel="noopener noreferrer">
              <ExternalLink className="h-4 w-4 mr-2" />
              Open in new tab
            </a>
          </Button>
          <Button asChild variant="outline" size="sm">
            <a href={file} download>
              <Download className="h-4 w-4 mr-2" />
              Download
            </a>
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="relative w-full h-full min-h-[400px]">
      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center bg-background/80 z-10">
          <Loader2 className="animate-spin mr-2 h-5 w-5" />
          <span>Loading PDF...</span>
        </div>
      )}
      {/* Search hint - native PDF viewer supports Ctrl+F/Cmd+F */}
      {!isLoading && (
        <div className="absolute top-2 right-2 z-10 flex items-center gap-1.5 px-2.5 py-1.5 bg-background/90 backdrop-blur-sm rounded-md border shadow-sm text-xs text-muted-foreground">
          <Search className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">Search:</span>
          <kbd className="px-1.5 py-0.5 bg-muted rounded text-[10px] font-mono">
            {typeof navigator !== 'undefined' && navigator.platform?.includes('Mac') ? '⌘F' : 'Ctrl+F'}
          </kbd>
        </div>
      )}
      <iframe
        ref={iframeRef}
        src={pdfUrl}
        className="w-full h-full border-0"
        title="PDF Viewer"
        onLoad={handleLoad}
        onError={handleError}
      />
    </div>
  );
}
