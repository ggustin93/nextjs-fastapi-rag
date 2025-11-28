export interface Source {
  title: string;
  path: string;
  similarity: number;
  url?: string;              // Original URL for scraped web content
  metadata?: {               // Full metadata for future use
    url?: string;
    source?: string;
    category?: string;
    language?: string;
    crawled_at?: string;
    [key: string]: any;
  };
  // PDF page number support
  page_number?: number;      // First page (for auto-scroll)
  page_range?: string;       // Formatted range (e.g., "p. 5-7" or "p. 5")
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  sources?: Source[];
}

export interface ChatRequest {
  message: string;
  session_id?: string;
}

export interface StreamEvent {
  type: 'token' | 'done' | 'error' | 'sources';
  content: string;
  sources?: Source[];
}
