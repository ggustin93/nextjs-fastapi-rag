'use client';

import { useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Trash2, MessageSquare } from 'lucide-react';
import { ChatMessage } from './ChatMessage';
import { ChatInput } from './ChatInput';
import { useChat } from '@/hooks/useChat';
import type { Source } from '@/types/chat';

interface ChatContainerProps {
  onOpenDocument?: (source: Source) => void;
}

export function ChatContainer({ onOpenDocument }: ChatContainerProps) {
  const { messages, isLoading, error, sendMessage, clearMessages } = useChat();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <Card className="w-full h-full flex flex-col">
      <CardHeader className="flex flex-row items-center justify-between flex-shrink-0">
        <CardTitle>Agent RAG Docling</CardTitle>
        {messages.length > 0 && (
          <Button
            variant="outline"
            size="sm"
            onClick={clearMessages}
            disabled={isLoading}
          >
            <Trash2 className="h-4 w-4 mr-2" />
            Effacer la conversation
          </Button>
        )}
      </CardHeader>

      <CardContent className="flex-1 flex flex-col overflow-hidden p-0">
        {/* Scrollable messages area */}
        <div className="flex-1 overflow-y-auto px-6 pt-6 pb-4">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full gap-6 px-8 animate-in fade-in duration-500">
              {/* Icon */}
              <div className="rounded-full bg-primary/10 p-6">
                <MessageSquare className="h-12 w-12 text-primary" />
              </div>

              {/* Title + Description */}
              <div className="text-center space-y-2 max-w-md">
                <h2 className="text-xl font-semibold">Bienvenue sur l'Agent RAG</h2>
                <p className="text-muted-foreground text-sm">
                  Posez des questions sur vos documents et obtenez des réponses IA avec sources
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              {messages.map((message, index) => (
                <div key={index} className="animate-in slide-in-from-bottom-2 fade-in duration-300">
                  <ChatMessage message={message} onOpenDocument={onOpenDocument} />
                </div>
              ))}
              {isLoading && (
                <div className="flex items-center gap-2 text-muted-foreground text-sm animate-in fade-in duration-200">
                  <div className="flex gap-1">
                    <span className="h-2 w-2 bg-current rounded-full animate-bounce [animation-delay:-0.3s]" />
                    <span className="h-2 w-2 bg-current rounded-full animate-bounce [animation-delay:-0.15s]" />
                    <span className="h-2 w-2 bg-current rounded-full animate-bounce" />
                  </div>
                  <span>Réflexion en cours...</span>
                </div>
              )}
              {/* Invisible element to scroll to */}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {error && (
          <div className="bg-destructive/10 text-destructive px-6 py-2 text-sm flex-shrink-0">
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
