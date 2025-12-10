'use client';

import { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Loader2, AlertCircle, Globe, FileText } from 'lucide-react';

interface IframeViewerProps {
  url: string;
  markdownContent: string;
  title: string;
  defaultTab?: 'iframe' | 'markdown';
  onFallback?: () => void;
}

export function IframeViewer({ url, markdownContent, title, defaultTab = 'iframe', onFallback }: IframeViewerProps) {
  const [loadingState, setLoadingState] = useState<'loading' | 'loaded' | 'error'>('loading');
  const [activeTab, setActiveTab] = useState<'iframe' | 'markdown'>(defaultTab);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  // 10-second timeout detection
  useEffect(() => {
    if (loadingState !== 'loading') return;

    const timeout = setTimeout(() => {
      if (loadingState === 'loading') {
        console.warn(`Iframe timeout for ${url}`);
        setLoadingState('error');
        setActiveTab('markdown');
        onFallback?.();
      }
    }, 10000);

    return () => clearTimeout(timeout);
  }, [loadingState, url, onFallback]);

  // Error detection
  const handleIframeError = () => {
    console.error(`Iframe loading error for ${url}`);
    setLoadingState('error');
    setActiveTab('markdown');
    onFallback?.();
  };

  // Success detection
  const handleIframeLoad = () => {
    setLoadingState('loaded');
  };

  return (
    <div className="h-full flex flex-col">
      {/* Tab Navigation */}
      <div className="flex items-center gap-2 border-b bg-muted/30 p-2">
        <Button
          variant={activeTab === 'iframe' ? 'default' : 'ghost'}
          size="sm"
          onClick={() => setActiveTab('iframe')}
          disabled={loadingState === 'error'}
          className="gap-1.5"
        >
          <Globe className="h-3.5 w-3.5" />
          Original Site
        </Button>
        <Button
          variant={activeTab === 'markdown' ? 'default' : 'ghost'}
          size="sm"
          onClick={() => setActiveTab('markdown')}
          className="gap-1.5"
        >
          <FileText className="h-3.5 w-3.5" />
          Markdown Content
        </Button>
        {loadingState === 'error' && (
          <Badge variant="destructive" className="ml-auto text-[10px]">
            Iframe blocked
          </Badge>
        )}
      </div>

      {/* Content Area */}
      <div className="flex-1 relative overflow-hidden">
        {activeTab === 'iframe' && (
          <>
            {/* Loading State */}
            {loadingState === 'loading' && (
              <div className="absolute inset-0 flex items-center justify-center bg-background/80 backdrop-blur-sm z-10">
                <div className="flex flex-col items-center gap-2 text-muted-foreground">
                  <Loader2 className="h-6 w-6 animate-spin" />
                  <p className="text-sm">Loading original site...</p>
                </div>
              </div>
            )}

            {/* Error State */}
            {loadingState === 'error' && (
              <div className="h-full flex flex-col items-center justify-center p-6 text-center bg-muted/20">
                <AlertCircle className="h-10 w-10 text-destructive mb-3" />
                <p className="font-semibold text-sm mb-2">Unable to display original site</p>
                <p className="text-xs text-muted-foreground max-w-md mb-4">
                  The website blocks iframe embedding (X-Frame-Options or CSP).
                  The content is available in the Markdown Content tab.
                </p>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setActiveTab('markdown')}
                >
                  View Markdown Content
                </Button>
              </div>
            )}

            {/* Iframe */}
            <iframe
              ref={iframeRef}
              src={url}
              sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
              onLoad={handleIframeLoad}
              onError={handleIframeError}
              className="w-full h-full border-0"
              title={title}
              loading="lazy"
            />
          </>
        )}

        {activeTab === 'markdown' && (
          <div className="h-full overflow-auto bg-background">
            <div className="max-w-4xl mx-auto px-6 py-8">
              <article className="prose prose-sm dark:prose-invert max-w-none prose-headings:font-semibold prose-a:text-primary prose-code:text-foreground prose-pre:bg-muted">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{markdownContent}</ReactMarkdown>
              </article>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
