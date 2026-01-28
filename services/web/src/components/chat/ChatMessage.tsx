'use client';

import { useState, useCallback, useMemo } from 'react';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Card } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import type { ChatMessage as ChatMessageType, Source, TicketData } from '@/types/chat';
import { GroupedSourcesList } from './GroupedSourcesList';
import { ToolCallBadge } from './ToolCallBadge';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

// Regex to match ticket numbers: #2025121610000123 or Ticket #2025121610000123
const TICKET_NUMBER_REGEX = /(?:Ticket\s*)?#(\d{10,})/gi;

// Component to render text with clickable ticket numbers
interface TicketLinkTextProps {
  children: string;
  onTicketClick?: (ticketNumber: string) => void;
}

function TicketLinkText({ children, onTicketClick }: TicketLinkTextProps) {
  if (typeof children !== 'string' || !onTicketClick) {
    return <>{children}</>;
  }

  const parts: (string | JSX.Element)[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  // Reset regex state
  TICKET_NUMBER_REGEX.lastIndex = 0;

  while ((match = TICKET_NUMBER_REGEX.exec(children)) !== null) {
    // Add text before match
    if (match.index > lastIndex) {
      parts.push(children.slice(lastIndex, match.index));
    }

    const ticketNumber = match[1]; // The captured group (digits only)
    const fullMatch = match[0]; // The full match including "Ticket #" or just "#"

    parts.push(
      <button
        key={`ticket-${match.index}`}
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          onTicketClick(ticketNumber);
        }}
        className="inline-flex items-center text-primary hover:underline font-medium cursor-pointer bg-transparent border-none p-0"
        title={`Voir le ticket ${ticketNumber}`}
      >
        🎫 {fullMatch}
      </button>
    );

    lastIndex = TICKET_NUMBER_REGEX.lastIndex;
  }

  // Add remaining text
  if (lastIndex < children.length) {
    parts.push(children.slice(lastIndex));
  }

  return <>{parts.length > 0 ? parts : children}</>;
}

interface ChatMessageProps {
  message: ChatMessageType;
  onOpenDocument?: (source: Source) => void;
}

export function ChatMessage({ message, onOpenDocument }: ChatMessageProps) {
  const isUser = message.role === 'user';
  const [mapError, setMapError] = useState<string | null>(null);
  const [ticketError, setTicketError] = useState<string | null>(null);

  // Handle "View Ticket" action for OTRS ticket tool
  const handleViewTicket = useCallback(async (ticketId: string, webUrl: string) => {
    if (!onOpenDocument) return;

    setTicketError(null);
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

    try {
      // Fetch ticket data from API (includes articles for thread view)
      const response = await fetch(`${baseUrl}/tickets/${ticketId}`);

      if (!response.ok) {
        if (response.status === 404) {
          setTicketError(`Ticket ${ticketId} not found`);
          return;
        }
        throw new Error(`API error: ${response.status}`);
      }

      const ticketData: TicketData = await response.json();

      // Create a Source with ticket data for DocumentPanel
      const ticketSource: Source = {
        title: `Ticket #${ticketData.ticket_number}`,
        path: `ticket://${ticketId}`,
        similarity: 1.0,
        ticketData: ticketData,
      };

      onOpenDocument(ticketSource);
    } catch (error) {
      console.error('Failed to fetch ticket data:', error);
      setTicketError('Failed to load ticket data');
    }
  }, [onOpenDocument]);

  // Handle ticket click from inline text (just ticket number, no webUrl needed)
  const handleTicketNumberClick = useCallback(async (ticketNumber: string) => {
    // Use ticket number as ID - the backend now supports TicketNumber lookup
    await handleViewTicket(ticketNumber, '');
  }, [handleViewTicket]);

  // Handle "View Map" action for OSIRIS worksite tool
  const handleViewMap = useCallback(async (worksiteId: string) => {
    if (!onOpenDocument) return;

    setMapError(null);
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

    try {
      const response = await fetch(`${baseUrl}/worksites/${worksiteId}/geometry`);

      if (!response.ok) {
        if (response.status === 404) {
          setMapError(`Worksite ${worksiteId} not found`);
          return;
        }
        throw new Error(`API error: ${response.status}`);
      }

      const data = await response.json();

      // Create a Source with geometry for DocumentPanel
      const mapSource: Source = {
        title: data.label_fr || data.label_nl || `Worksite ${worksiteId}`,
        path: `worksite://${worksiteId}`,
        similarity: 1.0,
        geometry: data.geometry,
        worksiteInfo: {
          id_ws: data.id_ws,
          label_fr: data.label_fr,
          label_nl: data.label_nl,
          status_fr: data.status_fr,
          status_nl: data.status_nl,
          road_impl_fr: data.road_impl_fr,
          road_impl_nl: data.road_impl_nl,
          pgm_start_date: data.pgm_start_date,
          pgm_end_date: data.pgm_end_date,
        },
      };

      onOpenDocument(mapSource);
    } catch (error) {
      console.error('Failed to fetch worksite geometry:', error);
      setMapError('Failed to load map data');
    }
  }, [onOpenDocument]);

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
          <div className="prose prose-sm dark:prose-invert max-w-none text-foreground">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                // Custom text renderer to make ticket numbers clickable
                text: ({ node, ...rest }) => {
                  const value = (node as { value?: string })?.value || '';
                  return (
                    <TicketLinkText onTicketClick={handleTicketNumberClick}>
                      {value}
                    </TicketLinkText>
                  );
                },
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
                    <code className="bg-background/50 px-1 py-0.5 rounded text-xs font-mono text-foreground" {...rest}>
                      {children}
                    </code>
                  ) : (
                    <code className="block text-xs font-mono text-foreground whitespace-pre-wrap break-words" {...rest}>
                      {children}
                    </code>
                  );
                },
                pre: ({ node, children, ...rest }) => (
                  <pre className="bg-background/50 p-3 rounded-md mb-2 text-foreground whitespace-pre-wrap break-words font-sans text-sm" {...rest}>
                    {children}
                  </pre>
                ),
                blockquote: ({ node, children, ...rest }) => (
                  <blockquote className="border-l-2 border-primary/50 pl-3 italic text-sm mb-2 text-foreground" {...rest}>
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

        {/* Tool Calls with View Map and View Ticket actions */}
        {!isUser && message.toolCalls && message.toolCalls.length > 0 && (
          <ToolCallBadge
            toolCalls={message.toolCalls}
            onViewMap={handleViewMap}
            onViewTicket={handleViewTicket}
          />
        )}

        {/* Map loading error display */}
        {mapError && (
          <div className="mt-2 px-3 py-2 bg-red-50 border border-red-200 rounded-md text-xs text-red-700">
            {mapError}
          </div>
        )}

        {/* Ticket loading error display */}
        {ticketError && (
          <div className="mt-2 px-3 py-2 bg-red-50 border border-red-200 rounded-md text-xs text-red-700">
            {ticketError}
          </div>
        )}

        {/* Grouped sources with multi-chunk display */}
        {!isUser && message.sources && message.sources.length > 0 && (
          <GroupedSourcesList
            sources={message.sources}
            citedIndices={message.citedIndices}
            onOpenDocument={onOpenDocument}
          />
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
