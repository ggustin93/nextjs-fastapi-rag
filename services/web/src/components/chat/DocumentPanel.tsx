'use client';

import { FileText, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { DocumentContent } from './DocumentContent';
import type { Source } from '@/types/chat';

interface DocumentPanelProps {
  source: Source;
  onClose: () => void;
}

export function DocumentPanel({ source, onClose }: DocumentPanelProps) {
  const similarityPercent = Math.round(source.similarity * 100);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="flex items-center gap-2 min-w-0 flex-1">
          <FileText className="h-5 w-5 shrink-0" />
          <h2 className="font-semibold text-sm truncate">{source.title}</h2>
          {source.page_range && (
            <Badge variant="secondary" className="shrink-0 text-[10px]">
              {source.page_range}
            </Badge>
          )}
          <Badge variant="outline" className="ml-auto shrink-0">
            Pertinence: {similarityPercent}%
          </Badge>
        </div>
        <Button
          variant="ghost"
          size="icon"
          onClick={onClose}
          className="ml-2 shrink-0"
          title="Fermer le panneau"
        >
          <X className="h-4 w-4" />
        </Button>
      </div>

      {/* Document Content */}
      <div className="flex-1 overflow-hidden px-6 py-4">
        <DocumentContent source={source} showControls={true} />
      </div>
    </div>
  );
}
