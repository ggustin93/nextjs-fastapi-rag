'use client';

import { useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Trash2 } from 'lucide-react';
import { ChatMessage } from './ChatMessage';
import { ChatInput } from './ChatInput';
import { useChat } from '@/hooks/useChat';

export function ChatContainer() {
  const { messages, isLoading, error, sendMessage, clearMessages } = useChat();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <Card className="w-full max-w-4xl mx-auto h-[80vh] flex flex-col">
      <CardHeader className="flex flex-row items-center justify-between flex-shrink-0">
        <CardTitle>Docling RAG Agent</CardTitle>
        {messages.length > 0 && (
          <Button
            variant="outline"
            size="sm"
            onClick={clearMessages}
            disabled={isLoading}
          >
            <Trash2 className="h-4 w-4 mr-2" />
            Clear Chat
          </Button>
        )}
      </CardHeader>

      <CardContent className="flex-1 flex flex-col gap-4 overflow-hidden min-h-0 p-0 px-6 pb-6">
        {/* Scrollable messages area */}
        <div className="flex-1 overflow-y-auto min-h-0 pr-4">
          {messages.length === 0 ? (
            <div className="flex items-center justify-center h-full text-muted-foreground">
              <p>Start a conversation with the RAG agent</p>
            </div>
          ) : (
            <div className="space-y-4 py-4">
              {messages.map((message, index) => (
                <ChatMessage key={index} message={message} />
              ))}
              {isLoading && (
                <div className="flex items-center gap-2 text-muted-foreground text-sm">
                  <div className="animate-pulse">Thinking...</div>
                </div>
              )}
              {/* Invisible element to scroll to */}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {error && (
          <div className="bg-destructive/10 text-destructive px-4 py-2 rounded-md text-sm flex-shrink-0">
            {error}
          </div>
        )}

        <div className="flex-shrink-0">
          <ChatInput onSend={sendMessage} disabled={isLoading} />
        </div>
      </CardContent>
    </Card>
  );
}
