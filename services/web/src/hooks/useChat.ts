'use client';

import { useState, useCallback, useRef } from 'react';
import { streamChat } from '@/lib/api-client';
import type { ChatMessage, Source } from '@/types/chat';

// Generate a unique session ID
function generateSessionId(): string {
  return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const sessionIdRef = useRef<string>(generateSessionId());

  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim() || isLoading) return;

    // Add user message
    const userMessage: ChatMessage = {
      role: 'user',
      content,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);
    setError(null);

    // Prepare assistant message
    let assistantContent = '';
    let assistantSources: Source[] = [];
    let citedIndices: number[] = [];

    try {
      await streamChat(
        { message: content, session_id: sessionIdRef.current },
        (event) => {
          if (event.type === 'token') {
            // Append token to assistant message
            assistantContent += event.content;

            // Update messages with current assistant response
            setMessages((prev) => {
              const lastMessage = prev[prev.length - 1];

              if (lastMessage && lastMessage.role === 'assistant') {
                // Update existing assistant message
                return prev.slice(0, -1).concat({
                  ...lastMessage,
                  content: assistantContent,
                  sources: assistantSources,
                  citedIndices,
                });
              } else {
                // Create new assistant message
                return prev.concat({
                  role: 'assistant',
                  content: assistantContent,
                  timestamp: new Date(),
                  sources: assistantSources,
                  citedIndices,
                });
              }
            });
          } else if (event.type === 'sources' && event.sources) {
            // Capture sources and cited indices from backend
            assistantSources = event.sources;
            citedIndices = event.cited_indices || [];

            // Update the assistant message with sources and cited indices
            setMessages((prev) => {
              const lastMessage = prev[prev.length - 1];
              if (lastMessage && lastMessage.role === 'assistant') {
                return prev.slice(0, -1).concat({
                  ...lastMessage,
                  sources: assistantSources,
                  citedIndices,
                });
              }
              return prev;
            });
          } else if (event.type === 'error') {
            setError(event.content || 'An error occurred');
          }
        }
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send message');
    } finally {
      setIsLoading(false);
    }
  }, [isLoading]);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setError(null);
    // Generate new session ID when clearing messages
    sessionIdRef.current = generateSessionId();
  }, []);

  return {
    messages,
    isLoading,
    error,
    sendMessage,
    clearMessages,
  };
}
