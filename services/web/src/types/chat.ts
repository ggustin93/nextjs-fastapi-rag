// Worksite geometry from OSIRIS API
export interface WorksiteGeometry {
  type: 'MultiPolygon' | 'Polygon';
  coordinates: number[][][][] | number[][][];
}

// Worksite info from OSIRIS tool
export interface WorksiteInfo {
  id_ws: string;
  label_fr?: string;
  label_nl?: string;
  status_fr?: string;
  status_nl?: string;
  road_impl_fr?: string;
  road_impl_nl?: string;
  pgm_start_date?: string;
  pgm_end_date?: string;
}

export interface Source {
  title: string;
  path: string;
  similarity: number;
  url?: string;              // Original URL for scraped web content
  content?: string;          // Inline content (non-PDF sources render without fetch)
  metadata?: {               // Full metadata for future use
    url?: string;
    source?: string;
    category?: string;
    language?: string;
    crawled_at?: string;
    [key: string]: unknown;  // Allow additional metadata fields with unknown type
  };
  // PDF page number support
  page_number?: number;      // First page (for auto-scroll)
  page_range?: string;       // Formatted range (e.g., "p. 5-7" or "p. 5")
  // Worksite map support (OSIRIS tool)
  geometry?: WorksiteGeometry;
  worksiteInfo?: WorksiteInfo;
}

export interface ToolCallMetadata {
  tool_name: string;
  tool_args: Record<string, unknown>;
  execution_time_ms?: number;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  sources?: Source[];
  citedIndices?: number[];  // 1-based indices of sources cited in response
  toolCalls?: ToolCallMetadata[];  // Tools called during this message
}

export interface ChatRequest {
  message: string;
  session_id?: string;
  model?: string;
}

export interface StreamEvent {
  type: 'token' | 'done' | 'error' | 'sources' | 'tool_call';
  content: string;
  sources?: Source[];
  cited_indices?: number[];  // 1-based indices from backend (snake_case from API)
  tool_name?: string;
  tool_args?: Record<string, unknown>;
  execution_time_ms?: number;
}
