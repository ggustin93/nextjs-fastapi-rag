'use client';

import { useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  ChevronDown,
  ChevronRight,
  FileText,
  Globe2,
  FileType,
  Layers,
} from 'lucide-react';
import type { Source, GroupedSource } from '@/types/chat';

// --- Utility Functions ---

/**
 * Group sources by document path, preserving all chunks per document.
 * Returns groups sorted by highest chunk similarity (descending).
 */
export function groupSourcesByDocument(sources: Source[]): GroupedSource[] {
  if (!sources?.length) return [];

  const grouped = new Map<string, GroupedSource>();

  for (const source of sources) {
    const key = source.path;

    if (!grouped.has(key)) {
      grouped.set(key, {
        documentPath: key,
        title: source.title,
        url: source.url,
        maxSimilarity: source.similarity,
        chunks: [],
      });
    }

    const group = grouped.get(key)!;
    group.chunks.push(source);
    group.maxSimilarity = Math.max(group.maxSimilarity, source.similarity);
  }

  // Sort chunks within each group by similarity (desc)
  for (const group of grouped.values()) {
    group.chunks.sort((a, b) => b.similarity - a.similarity);
  }

  // Sort groups by max similarity (desc)
  const result = Array.from(grouped.values()).sort(
    (a, b) => b.maxSimilarity - a.maxSimilarity
  );

  return result;
}

/**
 * Filter sources (remove PDF-only externals) and group by document.
 * Limits to MAX_DOCUMENTS groups, but preserves ALL chunks per document.
 */
export function filterAndGroupSources(
  sources: Source[],
  citedIndices: number[],
  maxDocuments: number = 5
): GroupedSource[] {
  if (!sources?.length) return [];

  const citedSet = new Set(citedIndices);

  // Filter out PDF-only external references
  const validSources = sources.filter((source) => {
    const isPdfOnlyExternal =
      source.url?.toLowerCase().endsWith('.pdf') &&
      !source.content &&
      !source.metadata?.content;
    return !isPdfOnlyExternal;
  });

  // Mark cited sources
  const sourcesWithCitation = validSources.map((source, index) => ({
    ...source,
    _isCited: citedSet.has(index + 1),
  }));

  // Group all sources
  const allGroups = groupSourcesByDocument(sourcesWithCitation);

  // Separate cited and uncited groups
  const citedGroups = allGroups.filter((g) =>
    g.chunks.some((c) => (c as Source & { _isCited?: boolean })._isCited)
  );
  const uncitedGroups = allGroups.filter(
    (g) => !g.chunks.some((c) => (c as Source & { _isCited?: boolean })._isCited)
  );

  // Include all cited + top uncited up to maxDocuments
  const remainingSlots = Math.max(0, maxDocuments - citedGroups.length);
  return [...citedGroups, ...uncitedGroups.slice(0, remainingSlots)];
}

// --- Components ---

function SourceTypeIcon({ source }: { source: Source }) {
  if (source.url) return <Globe2 className="h-3 w-3 text-blue-500" />;
  if (source.path.toLowerCase().endsWith('.pdf'))
    return <FileType className="h-3 w-3 text-red-500" />;
  return <FileText className="h-3 w-3 text-green-500" />;
}

interface SimpleSourceCardProps {
  group: GroupedSource;
  onOpenDocument?: (source: Source) => void;
}

/**
 * Simplified source card - just shows icon, title, chunk count, and similarity.
 * When clicked, opens DocumentViewer with all chunks attached.
 */
function SimpleSourceCard({ group, onOpenDocument }: SimpleSourceCardProps) {
  const hasMultipleChunks = group.chunks.length > 1;
  const bestChunk = group.chunks[0];

  const handleClick = () => {
    if (!onOpenDocument) return;

    // Create source with all chunks attached for DocumentViewer
    const sourceWithChunks: Source = {
      ...bestChunk,
      allChunks: group.chunks,
    };
    onOpenDocument(sourceWithChunks);
  };

  return (
    <Button
      variant="ghost"
      size="sm"
      className="h-auto py-1.5 px-2 text-[11px] hover:bg-muted w-full justify-start"
      onClick={handleClick}
    >
      <div className="flex items-center gap-1.5 w-full min-w-0">
        <SourceTypeIcon source={bestChunk} />
        <span className="truncate font-medium">{group.title}</span>
        {hasMultipleChunks && (
          <Badge
            variant="outline"
            className="text-[9px] px-1 py-0 shrink-0 gap-0.5"
          >
            <Layers className="h-2.5 w-2.5" />
            {group.chunks.length}
          </Badge>
        )}
        <Badge variant="secondary" className="text-[9px] px-1 py-0 shrink-0 ml-auto">
          {Math.round(group.maxSimilarity * 100)}%
        </Badge>
      </div>
    </Button>
  );
}

// --- Main Export ---

interface GroupedSourcesListProps {
  sources: Source[];
  citedIndices?: number[];
  onOpenDocument?: (source: Source) => void;
  maxDocuments?: number;
}

export function GroupedSourcesList({
  sources,
  citedIndices = [],
  onOpenDocument,
  maxDocuments = 5,
}: GroupedSourcesListProps) {
  const [isExpanded, setIsExpanded] = useState(true);

  const groupedSources = filterAndGroupSources(
    sources,
    citedIndices,
    maxDocuments
  );

  if (!groupedSources.length) return null;

  // Count total chunks across all groups
  const totalChunks = groupedSources.reduce(
    (sum, g) => sum + g.chunks.length,
    0
  );

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
        <span>
          Sources ({groupedSources.length} docs, {totalChunks} extraits)
        </span>
      </button>

      {isExpanded && (
        <div className="flex flex-col gap-1">
          {groupedSources.map((group) => (
            <SimpleSourceCard
              key={group.documentPath}
              group={group}
              onOpenDocument={onOpenDocument}
            />
          ))}
        </div>
      )}
    </div>
  );
}
