'use client';

import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Loader2, AlertCircle, FileText, File, Download, FileX, Layers } from 'lucide-react';
import type { Source } from '@/types/chat';
import { useDocumentFetch, getDocumentUrl } from './hooks/useDocumentFetch';
import { PdfViewer } from './PdfViewer';

interface ChunkDocumentViewerProps {
  source: Source;
  defaultTab?: 'full' | 'chunks';
}

/**
 * Determines if the source should have its full document prefetched.
 * Prefetch strategy: PDF and Markdown local files only.
 * Web sources and other formats are fetched on-demand.
 */
function shouldPrefetch(source: Source): boolean {
  const isPdf = source.path.toLowerCase().endsWith('.pdf');
  const isMd = source.path.toLowerCase().endsWith('.md');
  const isLocal = !source.url; // Not a web source

  return (isPdf || isMd) && isLocal;
}

/**
 * Checks if the file format is unsupported for in-browser preview.
 * These formats will show a download button instead.
 */
function isUnsupportedFormat(path: string): boolean {
  return /\.(docx?|xlsx?|pptx?)$/i.test(path);
}

/**
 * Concatenate all chunks into a single markdown string with separators.
 */
function concatenateChunks(chunks: Source[]): string {
  if (!chunks?.length) return '';

  return chunks
    .map((chunk, index) => {
      const header = chunk.page_range
        ? `### Extrait ${index + 1} (${chunk.page_range}) — ${Math.round(chunk.similarity * 100)}%`
        : `### Extrait ${index + 1} — ${Math.round(chunk.similarity * 100)}%`;
      return `${header}\n\n${chunk.content || '*Contenu non disponible*'}`;
    })
    .join('\n\n---\n\n');
}

/**
 * ChunkDocumentViewer component displays a toggle between:
 * - "Full Document" view: Shows the complete source file (PRIORITY)
 * - "Chunks" view: Shows all RAG-retrieved chunks concatenated
 *
 * Features:
 * - Tab-based UI with Full Document as default
 * - Smart prefetch for PDF/MD files
 * - On-demand fetch for web sources
 * - Error handling with retry mechanism
 * - Download fallback for unsupported formats
 * - All chunks concatenated in second tab
 */
export function ChunkDocumentViewer({ source, defaultTab = 'full' }: ChunkDocumentViewerProps) {
  const [activeTab, setActiveTab] = useState<'full' | 'chunks'>(defaultTab);
  const [retryCount, setRetryCount] = useState(0);

  const isPdf = source.path.toLowerCase().endsWith('.pdf');
  const isUnsupported = isUnsupportedFormat(source.path);
  const prefetch = shouldPrefetch(source);

  // Get all chunks (from allChunks array or just the single source.content)
  const allChunks = source.allChunks?.length ? source.allChunks : (source.content ? [source] : []);
  const hasChunks = allChunks.length > 0;
  const concatenatedContent = concatenateChunks(allChunks);

  // Fetch full document (with smart prefetch or on-demand)
  const { pdfUrl, mdContent, isLoading, error } = useDocumentFetch({
    path: source.path,
    isPdf,
    enabled: activeTab === 'full' || prefetch,
  });

  // Determine which tabs to show
  const hasFullDocument = !isUnsupported; // Assume available unless unsupported format

  // If neither chunks nor full document available, show error
  if (!hasChunks && isUnsupported) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-6 text-center bg-muted/20">
        <FileX className="h-10 w-10 text-muted-foreground mb-3" />
        <p className="font-semibold text-sm mb-2">Content not available</p>
        <p className="text-xs text-muted-foreground max-w-md mb-4">
          No chunk extract available, and this file format cannot be previewed in the browser.
        </p>
        <Button asChild variant="outline" size="sm">
          <a href={getDocumentUrl(source.path)} download>
            <Download className="mr-2 h-4 w-4" />
            Download {source.path.split('.').pop()?.toUpperCase()}
          </a>
        </Button>
      </div>
    );
  }

  const handleRetry = () => {
    setRetryCount(prev => prev + 1);
    // Trigger refetch by toggling away and back
    setActiveTab('chunks');
    setTimeout(() => setActiveTab('full'), 100);
  };

  return (
    <div className="h-full flex flex-col">
      {/* Tab Navigation */}
      <div className="flex items-center gap-2 border-b bg-muted/30 p-2">
        {hasFullDocument && (
          <Button
            variant={activeTab === 'full' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setActiveTab('full')}
            className="gap-1.5"
          >
            <File className="h-3.5 w-3.5" />
            Document
          </Button>
        )}

        {hasChunks && (
          <Button
            variant={activeTab === 'chunks' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setActiveTab('chunks')}
            className="gap-1.5"
          >
            <Layers className="h-3.5 w-3.5" />
            Extraits
            {allChunks.length > 1 && (
              <Badge variant="secondary" className="text-[10px] px-1 py-0 ml-1">
                {allChunks.length}
              </Badge>
            )}
          </Button>
        )}

        {/* Loading indicator */}
        {activeTab === 'full' && isLoading && (
          <Badge variant="secondary" className="text-[10px]">
            <Loader2 className="h-2.5 w-2.5 animate-spin mr-1" />
            Loading
          </Badge>
        )}

        {/* Error indicator */}
        {activeTab === 'full' && error && (
          <Badge variant="destructive" className="text-[10px]">
            Error
          </Badge>
        )}
      </div>

      {/* Content Area */}
      <div className="flex-1 relative overflow-hidden">
        {/* Full Document Tab (PRIMARY) */}
        {activeTab === 'full' && (
          <>
            {/* Loading State */}
            {isLoading && !pdfUrl && !mdContent && (
              <div className="h-full flex flex-col items-center justify-center text-muted-foreground">
                <Loader2 className="h-6 w-6 animate-spin mb-2" />
                <p className="text-sm">Chargement du document...</p>
              </div>
            )}

            {/* Error State */}
            {error && !pdfUrl && !mdContent && (
              <div className="h-full flex flex-col items-center justify-center p-6 text-center bg-muted/20">
                <AlertCircle className="h-10 w-10 text-destructive mb-3" />
                <p className="font-semibold text-sm mb-2">Échec du chargement</p>
                <p className="text-xs text-muted-foreground max-w-md mb-4">
                  {error}
                </p>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={handleRetry}>
                    Réessayer
                  </Button>
                  {retryCount >= 2 && (
                    <Button asChild variant="outline" size="sm">
                      <a href={getDocumentUrl(source.path)} download>
                        <Download className="mr-2 h-4 w-4" />
                        Télécharger
                      </a>
                    </Button>
                  )}
                </div>
              </div>
            )}

            {/* Unsupported Format State */}
            {isUnsupported && !isLoading && (
              <div className="h-full flex flex-col items-center justify-center p-6 text-center bg-muted/20">
                <FileX className="h-10 w-10 text-muted-foreground mb-3" />
                <p className="font-semibold text-sm mb-2">Format non supporté</p>
                <p className="text-xs text-muted-foreground max-w-md mb-4">
                  Ce format ({source.path.split('.').pop()?.toUpperCase()}) ne peut pas être affiché dans le navigateur.
                </p>
                <Button asChild variant="outline" size="sm">
                  <a href={getDocumentUrl(source.path)} download>
                    <Download className="mr-2 h-4 w-4" />
                    Télécharger {source.path.split('.').pop()?.toUpperCase()}
                  </a>
                </Button>
              </div>
            )}

            {/* PDF Viewer */}
            {isPdf && pdfUrl && !error && (
              <PdfViewer
                file={pdfUrl}
                pageNumber={source.page_number || 1}
                onLoadError={(err) => console.error('PDF load error:', err)}
              />
            )}

            {/* Markdown Viewer */}
            {!isPdf && mdContent && !error && !isUnsupported && (
              <div className="h-full overflow-auto bg-background">
                <div className="max-w-4xl mx-auto px-6 py-8">
                  <article className="
                    prose prose-sm dark:prose-invert max-w-none
                    prose-headings:font-semibold prose-headings:tracking-tight
                    prose-h1:text-2xl prose-h1:border-b prose-h1:pb-2 prose-h1:mb-4
                    prose-h2:text-xl prose-h2:mt-8 prose-h2:mb-3
                    prose-h3:text-lg prose-h3:mt-6 prose-h3:mb-2
                    prose-h4:text-base prose-h4:mt-4 prose-h4:mb-2
                    prose-p:leading-relaxed
                    prose-a:text-primary prose-code:text-foreground prose-pre:bg-muted
                    prose-strong:text-foreground prose-strong:font-semibold
                    prose-ul:my-4 prose-li:my-1
                    prose-table:text-sm prose-th:bg-muted/50
                  ">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {mdContent}
                    </ReactMarkdown>
                  </article>
                </div>
              </div>
            )}
          </>
        )}

        {/* All Chunks Tab (CONCATENATED) */}
        {activeTab === 'chunks' && hasChunks && (
          <div className="h-full overflow-auto bg-background">
            <div className="max-w-4xl mx-auto px-6 py-8">
              <article className="
                prose prose-sm dark:prose-invert max-w-none
                prose-headings:font-semibold prose-headings:tracking-tight
                prose-h1:text-2xl prose-h1:border-b prose-h1:pb-2 prose-h1:mb-4
                prose-h2:text-xl prose-h2:mt-8 prose-h2:mb-3
                prose-h3:text-lg prose-h3:mt-6 prose-h3:mb-2
                prose-h4:text-base prose-h4:mt-4 prose-h4:mb-2
                prose-p:leading-relaxed
                prose-a:text-primary prose-code:text-foreground prose-pre:bg-muted
                prose-strong:text-foreground prose-strong:font-semibold
                prose-ul:my-4 prose-li:my-1
                prose-table:text-sm prose-th:bg-muted/50
                prose-hr:my-6 prose-hr:border-border
              ">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {concatenatedContent}
                </ReactMarkdown>
              </article>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
