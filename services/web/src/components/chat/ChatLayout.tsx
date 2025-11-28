'use client';

import { useState, useEffect } from 'react';
import { useMediaQuery } from '@/hooks/useMediaQuery';
import { ResizablePanelGroup, ResizablePanel, ResizableHandle } from '@/components/ui/resizable';
import { ChatContainer } from './ChatContainer';
import { DocumentPanel } from './DocumentPanel';
import type { Source } from '@/types/chat';

export function ChatLayout() {
  const [isDocumentPanelOpen, setIsDocumentPanelOpen] = useState(false);
  const [currentDocument, setCurrentDocument] = useState<Source | null>(null);
  const [isMounted, setIsMounted] = useState(false);

  // Detect desktop (768px = md breakpoint)
  const isDesktop = useMediaQuery('(min-width: 768px)');

  // Prevent hydration mismatch by only rendering after mount
  // This is a valid pattern for SSR hydration fixes per React docs
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setIsMounted(true);
  }, []);

  const handleOpenDocument = (source: Source) => {
    // Clear any cached panel sizes to ensure 50/50 split
    if (typeof window !== 'undefined') {
      const keys = Object.keys(localStorage);
      keys.forEach(key => {
        if (key.includes('react-resizable-panels') && key.includes('chat-document-panels')) {
          localStorage.removeItem(key);
        }
      });
    }
    setCurrentDocument(source);
    setIsDocumentPanelOpen(true);
  };

  const handleCloseDocument = () => {
    setIsDocumentPanelOpen(false);
    // Keep currentDocument for a moment to allow smooth transition
    setTimeout(() => setCurrentDocument(null), 300);
  };

  // Prevent hydration mismatch: render mobile layout on server, switch to desktop after mount
  if (!isMounted) {
    // Server-side: always render mobile layout to avoid hydration mismatch
    return (
      <div className="h-screen w-screen flex flex-col">
        <div className="flex-1 overflow-hidden">
          <ChatContainer onOpenDocument={handleOpenDocument} />
        </div>
      </div>
    );
  }

  // Client-side after mount: render appropriate layout based on screen size
  if (isDesktop) {
    return (
      <div className="h-screen w-screen flex">
        <ResizablePanelGroup
          direction="horizontal"
        >
          {/* Chat Panel - always rendered to preserve state */}
          <ResizablePanel
            id="chat-panel"
            order={1}
            defaultSize={isDocumentPanelOpen ? 30 : 100}
            minSize={isDocumentPanelOpen ? 20 : 100}
            maxSize={isDocumentPanelOpen ? 50 : 100}
            className={isDocumentPanelOpen ? 'px-6' : 'flex items-center justify-center px-8'}
          >
            <div className={isDocumentPanelOpen ? 'h-full' : 'w-full max-w-4xl h-[80vh]'}>
              <ChatContainer onOpenDocument={handleOpenDocument} />
            </div>
          </ResizablePanel>

          {/* Resizable Handle - always rendered but hidden when panel closed */}
          <ResizableHandle
            withHandle
            className={isDocumentPanelOpen ? 'hover:bg-accent transition-colors' : 'hidden'}
          />

          {/* Document Panel - always rendered to avoid react-resizable-panels errors */}
          <ResizablePanel
            id="document-panel"
            order={2}
            defaultSize={70}
            collapsedSize={0}
            collapsible={true}
            minSize={50}
            maxSize={80}
            className={isDocumentPanelOpen ? '' : 'hidden'}
          >
            {currentDocument && (
              <DocumentPanel
                source={currentDocument}
                onClose={handleCloseDocument}
              />
            )}
          </ResizablePanel>
        </ResizablePanelGroup>
      </div>
    );
  }

  // Mobile: Simple container (ChatContainer handles modal internally)
  return (
    <div className="h-screen w-screen">
      <ChatContainer onOpenDocument={handleOpenDocument} />
    </div>
  );
}
