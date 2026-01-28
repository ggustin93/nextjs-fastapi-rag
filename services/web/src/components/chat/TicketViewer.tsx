'use client';

import { useMemo } from 'react';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import {
  User,
  UserCog,
  Bot,
  Calendar,
  Clock,
  Mail,
  FileText,
  Paperclip,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  EyeOff
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import type { TicketData, TicketArticle } from '@/types/chat';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useState } from 'react';

interface TicketViewerProps {
  ticketData: TicketData;
}

// Format date for display
function formatDate(dateStr?: string): string {
  if (!dateStr) return 'N/A';
  try {
    const date = new Date(dateStr);
    return date.toLocaleDateString('fr-FR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return dateStr;
  }
}

// Get priority badge color
function getPriorityColor(priority?: string): string {
  if (!priority) return 'text-muted-foreground';
  const p = priority.toLowerCase();
  if (p.includes('very high') || p.includes('5')) return 'text-red-600';
  if (p.includes('high') || p.includes('4')) return 'text-orange-500';
  if (p.includes('normal') || p.includes('3')) return 'text-yellow-600';
  if (p.includes('low') || p.includes('2')) return 'text-blue-500';
  if (p.includes('very low') || p.includes('1')) return 'text-gray-400';
  return 'text-muted-foreground';
}

// ============================================================================
// Email Body Transformation Pipeline
// ============================================================================
// Converts raw email content (HTML or plain text) to clean Markdown.
// The pipeline handles:
// 1. HTML to Markdown conversion
// 2. Bullet point normalization
// 3. URL and mailto link conversion
// 4. Contact label formatting
// 5. Noise removal (MS warnings, signatures, institutional blocks)
// 6. Signature detection and separation
// 7. Final whitespace cleanup
// ============================================================================

// ----------------------------------------------------------------------------
// Pattern Configuration
// ----------------------------------------------------------------------------

/** Contact-related labels that should be formatted prominently */
const CONTACT_LABELS = ['Email', 'E-mail', 'Web', 'Website', 'Site', 'Tél', 'Tel', 'Phone', 'Fax', 'Mobile', 'GSM'];

/** Important labels that should be bolded */
const IMPORTANT_LABELS = ['Attention', 'Important', 'Note'];

/** Patterns that indicate the start of an email signature */
const SIGNATURE_MARKERS: RegExp[] = [
  /^--\s*$/m,
  /^(Cordialement|Met vriendelijke groeten|Best regards|Kind regards|Bien à vous|Salutations),?\s*$/im,
];

/** HTML entity mappings for decoding */
const HTML_ENTITIES: Record<string, string> = {
  '&nbsp;': ' ',
  '&lt;': '<',
  '&gt;': '>',
  '&amp;': '&',
  '&quot;': '"',
  '&#39;': "'",
};

// ----------------------------------------------------------------------------
// HTML to Markdown Conversion
// ----------------------------------------------------------------------------

/**
 * Removes script and style blocks from HTML content.
 * These blocks can contain arbitrary content that shouldn't be displayed.
 */
function removeScriptAndStyleBlocks(html: string): string {
  return html
    .replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '')
    .replace(/<script[^>]*>[\s\S]*?<\/script>/gi, '');
}

/**
 * Converts HTML inline formatting tags to Markdown equivalents.
 * Must run before stripping remaining HTML tags.
 */
function convertHtmlFormattingToMarkdown(html: string): string {
  return html
    // Bold
    .replace(/<b>([^<]*)<\/b>/gi, '**$1**')
    .replace(/<strong>([^<]*)<\/strong>/gi, '**$1**')
    // Italic
    .replace(/<i>([^<]*)<\/i>/gi, '*$1*')
    .replace(/<em>([^<]*)<\/em>/gi, '*$1*')
    // Links - convert to markdown format [text](url)
    .replace(/<a[^>]+href=["']([^"']+)["'][^>]*>([^<]*)<\/a>/gi, '[$2]($1)')
    // Lists - convert to markdown bullets
    .replace(/<li[^>]*>([^<]*)<\/li>/gi, '- $1\n')
    .replace(/<\/?[ou]l[^>]*>/gi, '\n');
}

/**
 * Converts structural HTML elements to plain text with appropriate spacing.
 */
function convertStructuralHtmlToText(html: string): string {
  return html
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/<\/p>/gi, '\n\n')
    .replace(/<\/div>/gi, '\n')
    .replace(/<\/tr>/gi, '\n')
    .replace(/<\/td>/gi, ' | ')
    .replace(/<[^>]+>/g, ''); // Remove all remaining tags
}

/**
 * Decodes HTML entities to their character equivalents.
 */
function decodeHtmlEntities(text: string): string {
  let result = text;
  for (const [entity, char] of Object.entries(HTML_ENTITIES)) {
    result = result.replace(new RegExp(entity, 'g'), char);
  }
  return result;
}

/**
 * Full HTML to Markdown/text conversion pipeline.
 * Only applied to content detected as HTML.
 */
function convertHtmlToMarkdown(html: string): string {
  let result = html;
  result = removeScriptAndStyleBlocks(result);
  result = convertHtmlFormattingToMarkdown(result);
  result = convertStructuralHtmlToText(result);
  result = decodeHtmlEntities(result);
  return result;
}

/**
 * Detects if content is HTML based on body type or content patterns.
 */
function isHtmlContent(body: string, bodyType: string): boolean {
  return bodyType.includes('html') || body.includes('<html') || body.includes('<body');
}

// ----------------------------------------------------------------------------
// Bullet Point Normalization
// ----------------------------------------------------------------------------

/**
 * Converts various bullet characters (middle dots, bullets) to Markdown bullets.
 */
function normalizeBulletPoints(text: string): string {
  return text
    .replace(/^[·•]\s*/gm, '- ')
    .replace(/\n[·•]\s*/g, '\n- ');
}

// ----------------------------------------------------------------------------
// URL and Link Conversion
// ----------------------------------------------------------------------------

/**
 * Converts raw mailto: links to clickable Markdown format.
 */
function convertMailtoLinks(text: string): string {
  return text.replace(/\bmailto:([^\s<>\[\]()]+)/gi, '[$1](mailto:$1)');
}

/**
 * Converts raw URLs (not already in Markdown) to clickable Markdown links.
 * Uses negative lookbehind to avoid double-converting URLs already in [text](url) format.
 */
function convertRawUrls(text: string): string {
  return text.replace(/(?<!\]\()(https?:\/\/[^\s<>\[\]()]+)/gi, '[$1]($1)');
}

// ----------------------------------------------------------------------------
// Email Signature Cleanup
// ----------------------------------------------------------------------------

/**
 * Removes CID image references that won't display outside email client.
 * Also removes the linked URL when CID is followed by <url> (common in signatures).
 * Example: [cid:image001.png@01DC9068.3B3A3060]
 * Example: [cid:image001.png@...]<https://cornelis-solutions.be/logo> → removed entirely
 */
function removeCidReferences(text: string): string {
  // Remove CID with its linked URL as a unit: [cid:...]<url> → nothing
  let result = text.replace(/\[cid:[^\]]+\]<https?:\/\/[^>]+>/gi, '');
  // Remove standalone CID references
  result = result.replace(/\[cid:[^\]]+\]/gi, '');
  return result;
}

/**
 * Removes inline tel: links (often duplicates of nearby phone numbers).
 * Handles both bare tel: and <tel:...> formats to avoid orphan brackets.
 * Example: "T +32 (0)2 569 79 20<tel:+3225697920>" → "T +32 (0)2 569 79 20"
 * Example: "T +32 (0)2 569 79 20tel:+3225697920" → "T +32 (0)2 569 79 20"
 */
function cleanTelLinks(text: string): string {
  // Handle <tel:...> with angle brackets (most common in signatures)
  let result = text.replace(/<tel:\+?\d+>/gi, '');
  // Handle tel:... without brackets (fallback)
  result = result.replace(/\btel:\+?\d+/gi, '');
  return result;
}

/**
 * Converts [label]<url> patterns to proper Markdown links.
 * Example: [linkedin]<https://linkedin.com/...> → [linkedin](https://linkedin.com/...)
 */
function convertBracketLabelUrls(text: string): string {
  return text.replace(/\[([^\]]+)\]<(https?:\/\/[^>]+)>/gi, '[$1]($2)');
}

/**
 * Converts domain<url> patterns to Markdown links.
 * Example: cornelis-solutions.be<https://cornelis-solutions.be/...> → [cornelis-solutions.be](https://...)
 */
function convertDomainUrls(text: string): string {
  return text.replace(/([a-z0-9-]+\.[a-z]{2,})<(https?:\/\/[^>]+)>/gi, '[$1]($2)');
}

/**
 * Converts standalone <url> patterns to Markdown links.
 * Must run AFTER convertBracketLabelUrls and convertDomainUrls.
 */
function convertAngleBracketUrls(text: string): string {
  return text.replace(/(?<![)\]])<(https?:\/\/[^>]+)>/gi, '[$1]($1)');
}

/**
 * Cleans up orphaned angle brackets from partial URL conversions.
 */
function cleanOrphanedBrackets(text: string): string {
  return text
    .replace(/>\s*\n/g, '\n')  // Remove trailing > before newlines
    .replace(/>\s*$/gm, '');   // Remove trailing > at end of lines
}

// ----------------------------------------------------------------------------
// Contact Label Formatting
// ----------------------------------------------------------------------------

/**
 * Separates contact labels that got merged onto the same line as other content.
 * Example: "some text Email:" becomes "some text\nEmail:"
 */
function separateMergedContactLabels(text: string): string {
  const labelPattern = CONTACT_LABELS.join('|');
  const regex = new RegExp(`(\\S)\\s+(${labelPattern})\\s*:`, 'gi');
  return text.replace(regex, '$1\n$2:');
}

/**
 * Normalizes contact labels missing colons before their values.
 * Example: "Email user@example.com" becomes "Email: user@example.com"
 */
function normalizeContactLabelColons(text: string): string {
  return text
    .replace(/\b(Email|E-mail)\s+(?!:)(\S+@\S+)/gi, '$1: $2')
    .replace(/\b(Web|Website|Site)\s+(?!:)(https?:\/\/\S+|\S+\.\S+)/gi, '$1: $2');
}

/**
 * Makes contact and important labels bold for better visibility.
 */
function boldifyLabels(text: string): string {
  const contactPattern = CONTACT_LABELS.join('|');
  const importantPattern = IMPORTANT_LABELS.join('|');

  return text
    .replace(new RegExp(`^(${contactPattern})\\s*:`, 'gim'), '**$1:**')
    .replace(new RegExp(`^(${importantPattern})\\s*[,:]`, 'gim'), '**$1:**');
}

// ----------------------------------------------------------------------------
// Noise Removal
// ----------------------------------------------------------------------------

/**
 * Removes numbered reference links like [1], [2], etc.
 */
function removeNumberedReferences(text: string): string {
  return text.replace(/\[\d+\]/g, '');
}

/**
 * Removes reference definitions at the bottom of emails.
 * These are typically numbered lists of mailto: or https: links.
 */
function removeReferenceDefinitions(text: string): string {
  return text
    .replace(/^\s*\d+\.\s*mailto:[^\n]+$/gm, '')
    .replace(/^\s*\d+\.\s*https?:[^\n]+$/gm, '');
}

/**
 * Removes Microsoft Outlook sender warnings.
 * These appear when receiving email from uncommon senders.
 */
function removeMicrosoftWarnings(text: string): string {
  return text
    .replace(/\[?Vous n'obtenez pas souvent[\s\S]*?Découvrez pourquoi c'est important\]?/gi, '')
    .replace(/\[?You don't often get email from[\s\S]*?Learn why this is important\]?/gi, '');
}

/**
 * Converts email forwarding markers to clean horizontal rules.
 */
function cleanForwardingMarkers(text: string): string {
  return text
    .replace(/^-{3,}\s*(Message transféré|Forwarded message|Original Message)\s*-{3,}.*$/gim, '\n---\n')
    .replace(/^_{3,}\s*$/gm, '\n---\n');
}

/**
 * Removes email chain headers (De:, From:, Envoyé:, etc.).
 * These appear when emails are forwarded or replied to.
 */
function cleanEmailChainHeaders(text: string): string {
  return text.replace(
    /^(De|From)\s*:\s*[^\n]+\n(Envoyé|Sent)\s*:\s*[^\n]+\n(À|To)\s*:\s*[^\n]+\n(Cc\s*:\s*[^\n]+\n)?(Objet|Subject)\s*:\s*[^\n]+$/gim,
    '\n---\n'
  );
}

/**
 * Cleans up table noise from Osiris system (repeated separators, empty cells).
 */
function cleanOsirisTableNoise(text: string): string {
  return text
    .replace(/\|[-\s|]+\|/g, '')
    .replace(/^\s*\|\s*\|\s*$/gm, '');
}


/**
 * Truncates content after institutional signature markers.
 * Simple approach: detect marker, keep only what's before it.
 */
const INSTITUTIONAL_SIGNATURE_MARKERS = [
  'Het team van het Competentie Centrum Osiris',
  'Le CdCO',
  'Le CDCO',
  'Het CdCO',
  'Het CDCO',
];

function truncateAtInstitutionalSignature(text: string): string {
  let cutIndex = -1;

  for (const marker of INSTITUTIONAL_SIGNATURE_MARKERS) {
    const index = text.indexOf(marker);
    if (index !== -1 && (cutIndex === -1 || index < cutIndex)) {
      cutIndex = index;
    }
  }

  // Only cut if marker found and there's content before it
  if (cutIndex > 50) {
    return text.slice(0, cutIndex).trim();
  }

  return text;
}

// ----------------------------------------------------------------------------
// Markdown Formatting Helpers
// ----------------------------------------------------------------------------

/**
 * Ensures blank lines before bullet lists for proper Markdown rendering.
 */
function ensureBlankLinesBeforeLists(text: string): string {
  return text.replace(/([^\n])\n(- )/g, '$1\n\n$2');
}

/**
 * Normalizes signature separators (dashes/underscores) to standard horizontal rules.
 */
function normalizeSignatureSeparators(text: string): string {
  return text.replace(/^[-_]{5,}\s*$/gm, '---');
}

// ----------------------------------------------------------------------------
// Signature Detection and Separation
// ----------------------------------------------------------------------------

/**
 * Detects signature position and adds a visual separator if appropriate.
 * Only adds separator if there's substantial content both before and after.
 */
function detectAndSeparateSignature(text: string): string {
  let signatureIndex = -1;

  for (const pattern of SIGNATURE_MARKERS) {
    const match = text.match(pattern);
    if (match && match.index !== undefined) {
      if (signatureIndex === -1 || match.index < signatureIndex) {
        signatureIndex = match.index;
      }
    }
  }

  // Only add separator if signature is found with substantial content on both sides
  const MIN_CONTENT_BEFORE = 50;
  const MIN_CONTENT_AFTER = 20;

  if (signatureIndex > MIN_CONTENT_BEFORE && signatureIndex < text.length - MIN_CONTENT_AFTER) {
    const beforeSig = text.slice(0, signatureIndex).trim();
    const afterSig = text.slice(signatureIndex).trim();
    return `${beforeSig}\n\n---\n\n${afterSig}`;
  }

  return text;
}

// ----------------------------------------------------------------------------
// Final Cleanup
// ----------------------------------------------------------------------------

/**
 * Reduces excessive newlines to maximum of two consecutive.
 */
function normalizeNewlines(text: string): string {
  return text.replace(/\n{3,}/g, '\n\n');
}

/**
 * Trims lines and removes empty-only line sequences.
 */
function cleanupWhitespace(text: string): string {
  return text
    .split('\n')
    .map(line => line.trimEnd())
    .filter((line, index, arr) => {
      // Keep non-empty lines
      if (line.trim()) return true;
      // Keep single empty line between content
      if (index > 0 && arr[index - 1]?.trim()) return true;
      return false;
    })
    .join('\n')
    .trim();
}

// ----------------------------------------------------------------------------
// Main Transformation Pipeline
// ----------------------------------------------------------------------------

/**
 * Cleans email body content by applying a series of transformations.
 * Converts HTML to Markdown, normalizes formatting, and removes noise.
 *
 * @param body - The raw email body content
 * @param bodyType - The content type (e.g., 'text/html', 'text/plain')
 * @returns Cleaned Markdown-formatted text
 */
function cleanEmailBody(body: string, bodyType: string): string {
  let result = body;

  // Phase 1: HTML to Markdown conversion (conditional)
  if (isHtmlContent(result, bodyType)) {
    result = convertHtmlToMarkdown(result);
  }

  // Phase 2: Bullet point normalization
  result = normalizeBulletPoints(result);

  // Phase 2.5: Email signature cleanup (MUST run before Phase 3 link conversion)
  result = removeCidReferences(result);
  result = cleanTelLinks(result);
  result = convertBracketLabelUrls(result);
  result = convertDomainUrls(result);
  result = convertAngleBracketUrls(result);
  result = cleanOrphanedBrackets(result);

  // Phase 3: Link conversion
  result = convertMailtoLinks(result);
  result = convertRawUrls(result);

  // Phase 4: Contact label formatting
  result = separateMergedContactLabels(result);
  result = normalizeContactLabelColons(result);
  result = boldifyLabels(result);

  // Phase 5: Reference and noise removal
  result = removeNumberedReferences(result);
  result = removeReferenceDefinitions(result);
  result = removeMicrosoftWarnings(result);
  result = cleanForwardingMarkers(result);
  result = cleanEmailChainHeaders(result);
  result = cleanOsirisTableNoise(result);
  result = truncateAtInstitutionalSignature(result);

  // Phase 6: Markdown formatting
  result = ensureBlankLinesBeforeLists(result);
  result = normalizeSignatureSeparators(result);

  // Phase 7: Signature detection
  result = detectAndSeparateSignature(result);

  // Phase 8: Final cleanup
  result = normalizeNewlines(result);
  result = cleanupWhitespace(result);

  return result;
}

// Ticket Header Component
function TicketHeader({ ticket }: { ticket: TicketData }) {
  return (
    <div className="bg-muted/50 rounded-lg p-3 sm:p-4 mb-4">
      <div className="mb-3">
        <div className="flex items-start justify-between gap-2 mb-1">
          <h2 className="text-base sm:text-lg font-semibold line-clamp-2 sm:truncate flex-1 min-w-0">{ticket.title || 'No Title'}</h2>
          {ticket.web_url && (
            <a
              href={ticket.web_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-muted-foreground hover:text-primary transition-colors flex-shrink-0"
              title="Ouvrir dans OTRS"
            >
              <ExternalLink className="h-4 w-4" />
            </a>
          )}
        </div>
        <div className="flex items-center gap-2 text-xs sm:text-sm text-muted-foreground">
          <span>Ticket #{ticket.ticket_number}</span>
          <span className="text-muted-foreground/50">•</span>
          <span className="capitalize">{ticket.state || 'Unknown'}</span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-x-3 gap-y-2 text-sm">
        <div className="min-w-0">
          <span className="text-muted-foreground block text-xs uppercase tracking-wide mb-0.5">Queue</span>
          <span className="font-medium text-xs sm:text-sm truncate block" title={ticket.queue}>{ticket.queue || 'N/A'}</span>
        </div>
        <div className="min-w-0">
          <span className="text-muted-foreground block text-xs uppercase tracking-wide mb-0.5">Priority</span>
          <span className={cn('font-medium text-xs sm:text-sm', getPriorityColor(ticket.priority))}>
            {ticket.priority || 'N/A'}
          </span>
        </div>
        <div className="min-w-0">
          <span className="text-muted-foreground block text-xs uppercase tracking-wide mb-0.5">Owner</span>
          <span className="font-medium text-xs sm:text-sm truncate block" title={ticket.owner}>{ticket.owner || 'Unassigned'}</span>
        </div>
        <div className="min-w-0">
          <span className="text-muted-foreground block text-xs uppercase tracking-wide mb-0.5">Customer</span>
          <span className="font-medium text-xs sm:text-sm truncate block" title={ticket.customer_email || ticket.customer_user}>
            {ticket.customer_user || ticket.customer_email || 'N/A'}
          </span>
        </div>
      </div>

      <Separator className="my-3" />

      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
        <div className="flex items-center gap-1">
          <Calendar className="h-3 w-3 flex-shrink-0" />
          <span className="whitespace-nowrap">Créé: {formatDate(ticket.created)}</span>
        </div>
        <div className="flex items-center gap-1">
          <Clock className="h-3 w-3 flex-shrink-0" />
          <span className="whitespace-nowrap">MAJ: {formatDate(ticket.changed)}</span>
        </div>
      </div>
    </div>
  );
}

// Single Article Component
function ArticleItem({ article, isLast }: { article: TicketArticle; isLast: boolean }) {
  const [isExpanded, setIsExpanded] = useState(true);

  const isCustomer = article.sender_type === 'customer';
  const isSystem = article.sender_type === 'system';

  // Clean body using the transformation pipeline
  const cleanBody = useMemo(() => {
    return cleanEmailBody(article.body, article.body_type);
  }, [article.body, article.body_type]);

  return (
    <div className={cn(
      'relative',
      !isLast && 'pb-4'
    )}>
      {/* Timeline connector */}
      {!isLast && (
        <div className="absolute left-5 top-12 bottom-0 w-px bg-border" />
      )}

      <Card className={cn(
        'p-4 transition-colors',
        isCustomer ? 'bg-blue-50/50 dark:bg-blue-950/20 border-blue-200/50' :
        isSystem ? 'bg-gray-50/50 dark:bg-gray-950/20 border-gray-200/50' :
        'bg-green-50/50 dark:bg-green-950/20 border-green-200/50'
      )}>
        {/* Header */}
        <div className="flex items-start gap-3">
          {/* Avatar */}
          <div className={cn(
            'w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 text-white font-medium',
            isCustomer ? 'bg-blue-500' :
            isSystem ? 'bg-gray-400' :
            'bg-green-500'
          )}>
            {isCustomer ? <User className="h-5 w-5" /> :
             isSystem ? <Bot className="h-5 w-5" /> :
             <UserCog className="h-5 w-5" />}
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            {/* From/To/Subject header */}
            <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-1 sm:gap-2 mb-2">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1 flex-wrap">
                  <span className={cn(
                    'text-xs px-2 py-0.5 rounded-full font-medium flex-shrink-0',
                    isCustomer ? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300' :
                    isSystem ? 'bg-gray-100 text-gray-700 dark:bg-gray-900 dark:text-gray-300' :
                    'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300'
                  )}>
                    {isCustomer ? 'Client' : isSystem ? 'Système' : 'Agent'}
                  </span>
                  <span className="text-xs sm:text-sm font-medium truncate" title={article.from_address}>
                    {article.from_address || 'Unknown Sender'}
                  </span>
                </div>
                {article.subject && (
                  <p className="text-xs sm:text-sm font-semibold text-foreground truncate" title={article.subject}>
                    {article.subject}
                  </p>
                )}
              </div>

              <div className="flex items-center gap-2 flex-shrink-0">
                <span className="text-xs text-muted-foreground whitespace-nowrap">
                  {formatDate(article.created)}
                </span>
                <button
                  onClick={() => setIsExpanded(!isExpanded)}
                  className="p-1 hover:bg-muted rounded transition-colors"
                >
                  {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                </button>
              </div>
            </div>

            {/* Recipients */}
            {isExpanded && (article.to_addresses.length > 0 || article.cc_addresses.length > 0) && (
              <div className="text-xs text-muted-foreground mb-2 space-y-0.5">
                {article.to_addresses.length > 0 && (
                  <p className="truncate" title={article.to_addresses.join(', ')}>
                    <span className="font-medium">To:</span> {article.to_addresses.join(', ')}
                  </p>
                )}
                {article.cc_addresses.length > 0 && (
                  <p className="truncate" title={article.cc_addresses.join(', ')}>
                    <span className="font-medium">Cc:</span> {article.cc_addresses.join(', ')}
                  </p>
                )}
              </div>
            )}

            {/* Body */}
            {isExpanded && (
              <div className="mt-3 prose prose-sm dark:prose-invert max-w-none
                prose-p:my-2 prose-p:leading-relaxed
                prose-pre:bg-muted prose-pre:text-foreground
                prose-code:bg-muted prose-code:text-foreground prose-code:px-1 prose-code:rounded
                prose-hr:my-3 prose-hr:border-muted-foreground/30
                prose-ul:my-2 prose-ul:list-disc prose-ul:pl-5
                prose-li:my-1 prose-li:marker:text-foreground prose-li:marker:font-bold
              ">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{
                    a: ({ href, children }) => (
                      <a
                        href={href}
                        target={href?.startsWith('mailto:') ? undefined : '_blank'}
                        rel="noopener noreferrer"
                        className="text-primary underline hover:no-underline break-all"
                      >
                        {children}
                      </a>
                    ),
                    hr: () => (
                      <hr className="my-3 border-muted-foreground/30" />
                    ),
                  }}
                >
                  {cleanBody}
                </ReactMarkdown>
              </div>
            )}

            {/* Attachments */}
            {isExpanded && article.attachments.length > 0 && (
              <div className="mt-3 pt-3 border-t border-border/50">
                <div className="flex items-center gap-1 text-xs text-muted-foreground mb-2">
                  <Paperclip className="h-3 w-3" />
                  <span>{article.attachments.length} attachment(s)</span>
                </div>
                <div className="flex flex-wrap gap-2">
                  {article.attachments.map((att) => (
                    <div
                      key={att.attachment_id}
                      className="flex items-center gap-2 px-2 py-1 bg-muted rounded text-xs"
                      title={`${att.filename} (${att.content_type})`}
                    >
                      <FileText className="h-3 w-3" />
                      <span className="truncate max-w-[150px]">{att.filename}</span>
                      {att.file_size && (
                        <span className="text-muted-foreground">
                          ({Math.round(att.file_size / 1024)}KB)
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </Card>
    </div>
  );
}

// Main TicketViewer Component
export function TicketViewer({ ticketData }: TicketViewerProps) {
  const [hideSystemMessages, setHideSystemMessages] = useState(false);

  const filteredArticles = useMemo(() => {
    if (!hideSystemMessages) return ticketData.articles;
    return ticketData.articles.filter(article => article.sender_type !== 'system');
  }, [ticketData.articles, hideSystemMessages]);

  const systemMessageCount = useMemo(() => {
    return ticketData.articles.filter(article => article.sender_type === 'system').length;
  }, [ticketData.articles]);

  return (
    <div className="h-full overflow-auto bg-background">
      <div className="max-w-4xl mx-auto px-2 sm:px-4 py-4 sm:py-6">
        {/* Ticket Header */}
        <TicketHeader ticket={ticketData} />

        {/* Articles Thread */}
        <div className="mb-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <Mail className="h-4 w-4" />
              Conversation ({hideSystemMessages && systemMessageCount > 0
                ? `${filteredArticles.length}/${ticketData.articles.length}`
                : ticketData.articles.length} message{(hideSystemMessages ? filteredArticles.length : ticketData.articles.length) !== 1 ? 's' : ''})
            </h3>

            {systemMessageCount > 0 && (
              <Button
                variant={hideSystemMessages ? 'default' : 'ghost'}
                size="sm"
                onClick={() => setHideSystemMessages(!hideSystemMessages)}
                className="gap-1.5 h-7 text-xs"
                title={hideSystemMessages ? 'Afficher les messages système' : 'Masquer les messages système'}
              >
                {hideSystemMessages ? <Bot className="h-3.5 w-3.5" /> : <EyeOff className="h-3.5 w-3.5" />}
                {hideSystemMessages ? 'Afficher Système' : 'Masquer Système'}
                <Badge variant="secondary" className="text-[10px] px-1 py-0 ml-0.5">
                  {systemMessageCount}
                </Badge>
              </Button>
            )}
          </div>

          {filteredArticles.length === 0 ? (
            <Card className="p-8 text-center text-muted-foreground">
              <Mail className="h-8 w-8 mx-auto mb-2 opacity-50" />
              <p>{hideSystemMessages && systemMessageCount > 0
                ? `${systemMessageCount} message${systemMessageCount !== 1 ? 's' : ''} système masqué${systemMessageCount !== 1 ? 's' : ''}.`
                : 'Aucun message dans ce ticket.'
              }</p>
              {hideSystemMessages && systemMessageCount > 0 && (
                <Button
                  variant="link"
                  size="sm"
                  onClick={() => setHideSystemMessages(false)}
                  className="mt-2"
                >
                  Afficher tous les messages
                </Button>
              )}
            </Card>
          ) : (
            <div className="space-y-0">
              {filteredArticles.map((article, index) => (
                <ArticleItem
                  key={article.article_id}
                  article={article}
                  isLast={index === filteredArticles.length - 1}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
