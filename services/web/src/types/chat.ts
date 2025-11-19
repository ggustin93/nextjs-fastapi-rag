export interface Source {
  title: string;
  path: string;
  similarity: number;
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
