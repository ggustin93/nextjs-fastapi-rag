'use client';

import { useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { Trash2, Settings } from 'lucide-react';
import Link from 'next/link';
import { ChatMessage } from './ChatMessage';
import { ChatInput } from './ChatInput';
import { ToolActivityIndicator } from './ToolActivityIndicator';
import { LLMSelector } from './LLMSelector';
import { useChat } from '@/hooks/useChat';
import { AGENT_LIST } from './agentConfig';
import { cn } from '@/lib/utils';
import type { Source } from '@/types/chat';

interface ChatContainerProps {
  onOpenDocument?: (source: Source) => void;
}

export function ChatContainer({ onOpenDocument }: ChatContainerProps) {
  const { messages, isLoading, error, currentTool, selectedModel, setSelectedModel, selectedAgent, setSelectedAgent, sendMessage, clearMessages } = useChat();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <Card className="w-full h-full flex flex-col">
      <CardHeader className="flex flex-row items-center justify-between shrink-0">
        <CardTitle className="font-light tracking-wide">
          <span className="font-semibold">Osiris</span>
          <span className="text-muted-foreground/70"> AI Hub</span>
        </CardTitle>
        <div className="flex items-center gap-2">
          <LLMSelector selectedModel={selectedModel} onSelectModel={setSelectedModel} disabled={isLoading} />
          <Link href="/system">
            <Button variant="ghost" size="sm">
              <Settings className="h-4 w-4 mr-2" />
              System
            </Button>
          </Link>
          {messages.length > 0 && (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={clearMessages}
                    disabled={isLoading}
                    className="h-9 w-9"
                  >
                    <Trash2 className="h-4 w-4" />
                    <span className="sr-only">Effacer la conversation</span>
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>Effacer la conversation</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}
        </div>
      </CardHeader>

      <CardContent className="flex-1 flex flex-col overflow-hidden p-0">
        {/* Scrollable messages area */}
        <div className="flex-1 overflow-y-auto px-6 pt-6 pb-4">
          {messages.length === 0 ? (
            <div className="relative flex flex-col items-center justify-center h-full gap-8 px-8 animate-in fade-in duration-500">
              {/* Subtle geometric background */}
              <div
                className="absolute inset-0 opacity-[0.03] pointer-events-none"
                style={{
                  backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23000000' fill-opacity='1'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`,
                  backgroundSize: '60px 60px'
                }}
              />
              {/* Logo */}
              <div className="relative z-10 text-center space-y-3">
                <h2 className="text-3xl font-light tracking-wide">
                  <span className="font-semibold">Osiris</span>
                  <span className="text-muted-foreground/70"> AI Hub</span>
                </h2>
                <p className="text-muted-foreground text-sm font-light">
                  Assistance par agents spécialisés
                </p>
              </div>

              {/* Agent Cards Grid */}
              <div className="relative z-10 grid grid-cols-2 gap-3 w-full max-w-md">
                {AGENT_LIST.map((agent) => {
                  const IconComponent = agent.icon;
                  return (
                    <div
                      key={agent.id}
                      className="flex items-start gap-3 p-4 rounded-lg border bg-card hover:bg-accent/50 transition-colors"
                    >
                      <div className={cn("rounded-md p-2", agent.bgColor)}>
                        <IconComponent className={cn("h-4 w-4", agent.color)} />
                      </div>
                      <div className="space-y-0.5">
                        <p className="text-sm font-medium">{agent.name}</p>
                        <p className="text-xs text-muted-foreground">{agent.description}</p>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Hint */}
              <p className="relative z-10 text-xs text-muted-foreground/60">
                Tapez votre question ou utilisez @agent pour cibler un service
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {messages.map((message, index) => {
                // Don't render empty assistant message while loading (shows only Thinking indicator)
                const isEmptyAssistantWhileLoading =
                  isLoading &&
                  message.role === 'assistant' &&
                  !message.content &&
                  index === messages.length - 1;

                if (isEmptyAssistantWhileLoading) return null;

                return (
                  <div key={index} className="animate-in slide-in-from-bottom-2 fade-in duration-300">
                    <ChatMessage message={message} onOpenDocument={onOpenDocument} />
                  </div>
                );
              })}
              {isLoading && (
                <div className="animate-in fade-in duration-300">
                  <ToolActivityIndicator isActive={isLoading} currentTool={currentTool || undefined} />
                </div>
              )}
              {/* Invisible element to scroll to */}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {error && (
          <div className="bg-destructive/10 text-destructive px-6 py-2 text-sm shrink-0">
            {error}
          </div>
        )}

        <div className="shrink-0">
          <ChatInput
            onSend={sendMessage}
            disabled={isLoading}
            selectedAgent={selectedAgent}
            onSelectAgent={setSelectedAgent}
          />
        </div>
      </CardContent>
    </Card>
  );
}
