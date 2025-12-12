'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { streamChat } from '@/lib/api-client';
import type { ChatMessage, Source, ToolCallMetadata } from '@/types/chat';

// Generate a unique session ID
function generateSessionId(): string {
  return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

const STORAGE_KEY = 'chat-history';

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentTool, setCurrentTool] = useState<string | null>(null);
  const [selectedModel, setSelectedModel] = useState<string | null>(null);
  const [selectedAgent, setSelectedAgent] = useState<string | null>('rag');
  const sessionIdRef = useRef<string>(generateSessionId());

  // Load messages from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        // Convert timestamp strings back to Date objects
        const messagesWithDates = parsed.map((msg: ChatMessage) => ({
          ...msg,
          timestamp: new Date(msg.timestamp),
        }));
        setMessages(messagesWithDates);
      }
    } catch (err) {
      console.error('Failed to load chat history:', err);
    }
  }, []);

  // Save messages to localStorage whenever they change
  useEffect(() => {
    if (messages.length > 0) {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(messages));
      } catch (err) {
        console.error('Failed to save chat history:', err);
      }
    }
  }, [messages]);

  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim() || isLoading) return;

    // Add user message
    const userMessage: ChatMessage = {
      role: 'user',
      content,
      timestamp: new Date(),
    };

    // FIX: Create assistant message IMMEDIATELY to prevent race conditions
    // This ensures sources/tool_call events always have a message to update
    const initialAssistantMessage: ChatMessage = {
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      sources: [],
      citedIndices: [],
      toolCalls: [],  // Explicitly initialize to prevent persistence from previous messages
    };

    setMessages((prev) => [...prev, userMessage, initialAssistantMessage]);
    setIsLoading(true);
    setError(null);

    try {
      // Prepend @agent mention if a specific agent is selected (backend parses this)
      const messageWithAgent = selectedAgent && selectedAgent !== 'rag'
        ? `@${selectedAgent} ${content}`
        : content;

      await streamChat(
        { message: messageWithAgent, session_id: sessionIdRef.current, model: selectedModel || undefined },
        (event) => {
          if (event.type === 'token') {
            // Append token to assistant message using functional update
            setMessages((prev) => {
              const lastMessage = prev[prev.length - 1];
              if (lastMessage && lastMessage.role === 'assistant') {
                return prev.slice(0, -1).concat({
                  ...lastMessage,
                  content: lastMessage.content + event.content,
                });
              }
              return prev;
            });
          } else if (event.type === 'sources' && event.sources) {
            // Update the assistant message with sources and cited indices
            setMessages((prev) => {
              const lastMessage = prev[prev.length - 1];
              if (lastMessage && lastMessage.role === 'assistant') {
                return prev.slice(0, -1).concat({
                  ...lastMessage,
                  sources: event.sources,
                  citedIndices: event.cited_indices || [],
                });
              }
              return prev;
            });
          } else if (event.type === 'tool_call') {
            // Update current tool for the indicator
            setCurrentTool(event.tool_name || null);

            // Capture tool call metadata
            const toolCall: ToolCallMetadata = {
              tool_name: event.tool_name || '',
              tool_args: event.tool_args || {},
              execution_time_ms: event.execution_time_ms,
              tool_result: event.tool_result,  // Include raw result for debug display
            };

            // Update the assistant message with tool calls
            setMessages((prev) => {
              const lastMessage = prev[prev.length - 1];
              if (lastMessage && lastMessage.role === 'assistant') {
                const existingToolCalls = lastMessage.toolCalls || [];
                return prev.slice(0, -1).concat({
                  ...lastMessage,
                  toolCalls: [...existingToolCalls, toolCall],
                });
              }
              return prev;
            });
          } else if (event.type === 'done') {
            // Stream completed successfully - nothing special needed
            // The assistant message is already in place
          } else if (event.type === 'error') {
            setError(event.content || 'An error occurred');
          }
        }
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send message');
    } finally {
      setIsLoading(false);
      setCurrentTool(null); // Clear current tool when done
    }
  }, [isLoading, selectedModel, selectedAgent]);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setError(null);
    // Clear localStorage
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch (err) {
      console.error('Failed to clear chat history:', err);
    }
    // Generate new session ID when clearing messages
    sessionIdRef.current = generateSessionId();
  }, []);

  return {
    messages,
    isLoading,
    error,
    currentTool,
    selectedModel,
    setSelectedModel,
    selectedAgent,
    setSelectedAgent,
    sendMessage,
    clearMessages,
  };
}
