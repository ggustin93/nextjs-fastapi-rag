'use client';

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { FileText, ExternalLink } from 'lucide-react';
import type { Source } from '@/types/chat';

interface DocumentViewerProps {
  source: Source;
}

export function DocumentViewer({ source }: DocumentViewerProps) {
  const similarityPercent = Math.round(source.similarity * 100);

  // Build API URL for document - strip 'documents/' prefix if present
  const getDocumentUrl = (path: string) => {
    const cleanPath = path.replace(/^documents\//, '');
    return `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/documents/${cleanPath}`;
  };

  return (
    <Dialog>
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
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            {source.title}
          </DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div className="flex items-center justify-between text-sm text-muted-foreground">
            <span>Source: {source.path}</span>
            <Badge variant="outline">
              Pertinence: {similarityPercent}%
            </Badge>
          </div>
          <div className="border-t pt-4">
            <p className="text-sm text-muted-foreground">
              Ce document a été utilisé comme source pour générer la réponse.
            </p>
            <Button
              variant="outline"
              size="sm"
              className="mt-3"
              onClick={() => window.open(getDocumentUrl(source.path), '_blank')}
            >
              <ExternalLink className="h-4 w-4 mr-2" />
              Ouvrir le document original
            </Button>
          </div>
        </div>
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
