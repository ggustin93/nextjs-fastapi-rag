import type { ChatRequest, StreamEvent } from '@/types/chat';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

/**
 * Stream chat responses using Server-Sent Events
 * @param request Chat request with message
 * @param onEvent Callback for each SSE event
 */
export async function streamChat(
  request: ChatRequest,
  onEvent: (event: StreamEvent) => void
): Promise<void> {
  const response = await fetch(`${API_URL}/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  const reader = response.body?.getReader();
  const decoder = new TextDecoder();

  if (!reader) {
    throw new Error('No response body');
  }

  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();

      if (done) break;

      // Accumulate chunks in buffer to handle split events
      buffer += decoder.decode(value, { stream: true });

      // Parse SSE format: events are separated by "\n\n"
      const events = buffer.split('\n\n');
      buffer = events.pop() || ''; // Keep incomplete event in buffer

      for (const eventText of events) {
        if (!eventText.trim()) continue;

        let eventType: string | null = null;
        let data: string | null = null;

        for (const line of eventText.split('\n')) {
          if (line.startsWith('event:')) {
            eventType = line.slice(6).trim();
          } else if (line.startsWith('data:')) {
            data = line.slice(5).trim();
          }
        }

        if (eventType && data) {
          try {
            const parsed = JSON.parse(data);
            const event: StreamEvent = {
              type: eventType as StreamEvent['type'],
              content: parsed.content || '',
              sources: parsed.sources,
              cited_indices: parsed.cited_indices,
            };

            // Add tool_call specific fields
            if (eventType === 'tool_call') {
              event.tool_name = parsed.tool_name;
              event.tool_args = parsed.tool_args;
              event.execution_time_ms = parsed.execution_time_ms;
              event.tool_result = parsed.tool_result;
            }

            onEvent(event);
          } catch (e) {
            console.error('Failed to parse SSE data:', e);
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}
