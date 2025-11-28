'use client';

import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Card } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import type { ChatMessage as ChatMessageType, Source } from '@/types/chat';
import { SourcesList } from './DocumentViewer';
import { ToolCallBadge } from './ToolCallBadge';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

/**
 * Filter and sort sources to show:
 * 1. All cited sources (from [1], [2], etc. in response)
 * 2. Top 5 sources by similarity (backend already sorted)
 * 3. Deduplicate by path, maintain similarity order
 *
 * Optimized: O(n) single-pass algorithm, leverages backend pre-sorting
 */
function filterAndSortSources(
  sources: Source[],
  citedIndices: number[]
): Source[] {
  if (!sources?.length) return [];

  const citedSet = new Set(citedIndices);
  const seenPaths = new Map<string, Source>();
  const MAX_TOP_SOURCES = 5;

  // Backend already sorts by similarity desc - maintain order
  // Single pass: add cited sources + top 5 unique sources
  for (let i = 0; i < sources.length; i++) {
    const source = sources[i];
    const isCited = citedSet.has(i + 1);

    // Skip duplicates (keep first = highest similarity)
    if (seenPaths.has(source.path)) continue;

    // Add if cited OR if we need more top sources
    if (isCited || seenPaths.size < MAX_TOP_SOURCES) {
      seenPaths.set(source.path, source);
    }

    // Early exit: have all cited + enough top sources
    if (citedSet.size > 0 && seenPaths.size >= Math.max(citedSet.size, MAX_TOP_SOURCES)) {
      break;
    }
  }

  // Already in similarity order due to backend sorting
  return Array.from(seenPaths.values());
}

interface ChatMessageProps {
  message: ChatMessageType;
  onOpenDocument?: (source: Source) => void;
}

export function ChatMessage({ message, onOpenDocument }: ChatMessageProps) {
  const isUser = message.role === 'user';

  // Filter and sort sources before rendering
  const displaySources = filterAndSortSources(
    message.sources || [],
    message.citedIndices || []
  );

  return (
    <div
      className={cn(
        'flex gap-3 mb-4',
        isUser ? 'justify-end' : 'justify-start'
      )}
    >
      {!isUser && (
        <Avatar className="h-8 w-8 flex-shrink-0">
          <AvatarFallback className="bg-primary text-primary-foreground">
            AI
          </AvatarFallback>
        </Avatar>
      )}

      <Card
        className={cn(
          'px-4 py-3 max-w-[80%]',
          isUser
            ? 'bg-primary text-primary-foreground'
            : 'bg-muted'
        )}
      >
        {isUser ? (
          <p className="text-sm whitespace-pre-wrap break-words">
            {message.content}
          </p>
        ) : (
          <div className="prose prose-sm dark:prose-invert max-w-none">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                p: ({ node, children, ...rest }) => (
                  <p className="text-sm mb-2 last:mb-0" {...rest}>{children}</p>
                ),
                ul: ({ node, children, ...rest }) => (
                  <ul className="text-sm list-disc list-inside mb-2 space-y-1" {...rest}>{children}</ul>
                ),
                ol: ({ node, children, ...rest }) => (
                  <ol className="text-sm list-decimal list-inside mb-2 space-y-1" {...rest}>{children}</ol>
                ),
                li: ({ node, children, ...rest }) => (
                  <li className="text-sm" {...rest}>{children}</li>
                ),
                strong: ({ node, children, ...rest }) => (
                  <strong className="font-semibold" {...rest}>{children}</strong>
                ),
                em: ({ node, children, ...rest }) => (
                  <em className="italic" {...rest}>{children}</em>
                ),
                code: ({ node, children, className, ...rest }) => {
                  const isInline = !className;
                  return isInline ? (
                    <code className="bg-background/50 px-1 py-0.5 rounded text-xs font-mono" {...rest}>
                      {children}
                    </code>
                  ) : (
                    <code className="block bg-background/50 p-2 rounded text-xs font-mono overflow-x-auto" {...rest}>
                      {children}
                    </code>
                  );
                },
                pre: ({ node, children, ...rest }) => (
                  <pre className="bg-background/50 p-3 rounded-md overflow-x-auto mb-2" {...rest}>
                    {children}
                  </pre>
                ),
                blockquote: ({ node, children, ...rest }) => (
                  <blockquote className="border-l-2 border-primary/50 pl-3 italic text-sm mb-2" {...rest}>
                    {children}
                  </blockquote>
                ),
                h1: ({ node, children, ...rest }) => (
                  <span className="text-lg font-bold" {...rest}>{children}</span>
                ),
                h2: ({ node, children, ...rest }) => (
                  <span className="text-base font-bold" {...rest}>{children}</span>
                ),
                h3: ({ node, children, ...rest }) => (
                  <span className="text-sm font-bold" {...rest}>{children}</span>
                ),
                a: ({ node, href, children, ...rest }) => (
                  <a
                    href={href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary underline hover:no-underline"
                    {...rest}
                  >
                    {children}
                  </a>
                ),
                table: ({ node, children, ...rest }) => (
                  <div className="overflow-x-auto mb-2">
                    <table className="text-xs border-collapse w-full" {...rest}>
                      {children}
                    </table>
                  </div>
                ),
                th: ({ node, children, ...rest }) => (
                  <th className="border border-border px-2 py-1 bg-background/50 font-semibold text-left" {...rest}>
                    {children}
                  </th>
                ),
                td: ({ node, children, ...rest }) => (
                  <td className="border border-border px-2 py-1" {...rest}>
                    {children}
                  </td>
                ),
              }}
            >
              {message.content}
            </ReactMarkdown>
          </div>
        )}

        {!isUser && displaySources.length > 0 && (
          <SourcesList sources={displaySources} onOpenDocument={onOpenDocument} />
        )}

        {!isUser && (
          <ToolCallBadge toolCalls={message.toolCalls} />
        )}
      </Card>

      {isUser && (
        <Avatar className="h-8 w-8 flex-shrink-0">
          <AvatarFallback className="bg-secondary text-secondary-foreground">
            U
          </AvatarFallback>
        </Avatar>
      )}
    </div>
  );
}
