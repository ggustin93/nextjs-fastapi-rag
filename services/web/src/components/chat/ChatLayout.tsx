'use client';

import { useState } from 'react';
import { useMediaQuery } from '@/hooks/useMediaQuery';
import { ResizablePanelGroup, ResizablePanel, ResizableHandle } from '@/components/ui/resizable';
import { ChatContainer } from './ChatContainer';
import { DocumentPanel } from './DocumentPanel';
import type { Source } from '@/types/chat';

export function ChatLayout() {
  const [isDocumentPanelOpen, setIsDocumentPanelOpen] = useState(false);
  const [currentDocument, setCurrentDocument] = useState<Source | null>(null);

  // Detect desktop (768px = md breakpoint)
  const isDesktop = useMediaQuery('(min-width: 768px)');

  const handleOpenDocument = (source: Source) => {
    setCurrentDocument(source);
    setIsDocumentPanelOpen(true);
  };

  const handleCloseDocument = () => {
    setIsDocumentPanelOpen(false);
    // Keep currentDocument for a moment to allow smooth transition
    setTimeout(() => setCurrentDocument(null), 300);
  };

  // Desktop: Unified layout that preserves chat state
  if (isDesktop) {
    return (
      <div className="h-screen w-screen flex">
        <ResizablePanelGroup
          direction="horizontal"
          autoSaveId="chat-document-panels"
        >
          {/* Chat Panel - always rendered to preserve state */}
          <ResizablePanel
            id="chat-panel"
            order={1}
            defaultSize={isDocumentPanelOpen ? 50 : 100}
            minSize={isDocumentPanelOpen ? 30 : 100}
            maxSize={isDocumentPanelOpen ? 70 : 100}
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
            defaultSize={50}
            collapsedSize={0}
            collapsible={true}
            minSize={30}
            maxSize={70}
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
