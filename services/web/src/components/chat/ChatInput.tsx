'use client';

import { useState, KeyboardEvent, ChangeEvent, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Send, Loader2 } from 'lucide-react';
import { AgentSelector } from './AgentSelector';
import { cn } from '@/lib/utils';

// Agent suggestions for autocomplete
const AGENT_SUGGESTIONS = [
  { id: 'rag', name: 'RAG', icon: '📚', keywords: ['rag', 'assistant', 'kb', 'knowledge'] },
  { id: 'weather', name: 'Météo', icon: '🌤️', keywords: ['weather', 'meteo', 'météo'] },
];

// Agent ID mapping (includes aliases)
const AGENT_ALIASES: Record<string, string> = {
  rag: 'rag',
  assistant: 'rag',
  default: 'rag',
  kb: 'rag',
  weather: 'weather',
  meteo: 'weather',
  météo: 'weather',
};

// Valid agent IDs for error feedback
const VALID_AGENT_IDS = new Set(Object.values(AGENT_ALIASES));

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  selectedAgent: string | null;
  onSelectAgent: (agentId: string) => void;
}

export function ChatInput({ onSend, disabled, selectedAgent, onSelectAgent }: ChatInputProps) {
  const [input, setInput] = useState('');
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [filteredAgents, setFilteredAgents] = useState(AGENT_SUGGESTIONS);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Filter agents based on input after @
  useEffect(() => {
    const mentionMatch = input.match(/^@([\w\u00C0-\u024F]*)$/i);
    if (mentionMatch) {
      const query = mentionMatch[1].toLowerCase();
      const filtered = AGENT_SUGGESTIONS.filter(agent =>
        agent.keywords.some(kw => kw.startsWith(query)) || agent.name.toLowerCase().startsWith(query)
      );
      setFilteredAgents(filtered.length > 0 ? filtered : AGENT_SUGGESTIONS);
      setShowSuggestions(true);
      setSelectedIndex(0);
    } else {
      setShowSuggestions(false);
    }
  }, [input]);

  const selectAgent = (agentId: string) => {
    onSelectAgent(agentId);
    setInput('');
    setShowSuggestions(false);
    inputRef.current?.focus();
  };

  const handleInputChange = (e: ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setErrorMessage(null); // Clear error on input change

    // Detect @agent pattern with space (complete mention)
    const mentionMatch = value.match(/^@([\w\u00C0-\u024F]+)\s/i);
    if (mentionMatch) {
      const mention = mentionMatch[1].toLowerCase();
      const agentId = AGENT_ALIASES[mention];

      if (agentId && agentId !== selectedAgent) {
        onSelectAgent(agentId);
        setInput(value.slice(mentionMatch[0].length));
        setShowSuggestions(false);
        return;
      } else if (!agentId) {
        // Unknown agent - show error feedback
        setErrorMessage(`Agent "@${mention}" inconnu. Utilisez @rag ou @weather`);
        setInput(value.slice(mentionMatch[0].length));
        setShowSuggestions(false);
        // Auto-clear error after 3 seconds
        setTimeout(() => setErrorMessage(null), 3000);
        return;
      }
    }

    setInput(value);
  };

  const handleSend = () => {
    if (input.trim() && !disabled) {
      onSend(input);
      setInput('');
      setShowSuggestions(false);
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (showSuggestions && filteredAgents.length > 0) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex(i => (i + 1) % filteredAgents.length);
        return;
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex(i => (i - 1 + filteredAgents.length) % filteredAgents.length);
        return;
      }
      if (e.key === 'Enter' || e.key === 'Tab') {
        e.preventDefault();
        selectAgent(filteredAgents[selectedIndex].id);
        return;
      }
      if (e.key === 'Escape') {
        e.preventDefault();
        setShowSuggestions(false);
        setInput('');
        return;
      }
    }

    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="relative flex items-center gap-2 border-t border-border bg-background shadow-lg px-4 py-4" suppressHydrationWarning>
      <AgentSelector
        selectedAgent={selectedAgent}
        onSelectAgent={onSelectAgent}
        disabled={disabled}
      />

      <div className="relative flex-1">
        <Input
          ref={inputRef}
          value={input}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          onBlur={() => setTimeout(() => setShowSuggestions(false), 150)}
          placeholder="Écrivez votre message... (@agent)"
          disabled={disabled}
          className="h-11 text-base"
        />

        {/* Agent autocomplete dropdown */}
        {showSuggestions && filteredAgents.length > 0 && (
          <div className="absolute bottom-full left-0 mb-2 w-56 bg-popover border border-border rounded-lg shadow-lg overflow-hidden animate-in fade-in slide-in-from-bottom-2 duration-150">
            <div className="p-1">
              <div className="px-2 py-1.5 text-xs text-muted-foreground font-medium">
                Agents
              </div>
              {filteredAgents.map((agent, index) => (
                <button
                  key={agent.id}
                  onMouseDown={(e) => {
                    e.preventDefault();
                    selectAgent(agent.id);
                  }}
                  onMouseEnter={() => setSelectedIndex(index)}
                  className={cn(
                    "w-full flex items-center gap-2.5 px-2 py-2 rounded-md text-left transition-colors",
                    index === selectedIndex ? "bg-accent text-accent-foreground" : "hover:bg-accent/50"
                  )}
                >
                  <span className="text-lg leading-none">{agent.icon}</span>
                  <span className="font-medium text-sm">{agent.name}</span>
                  <span className="ml-auto text-xs text-muted-foreground">@{agent.id}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Error message for unknown agents */}
        {errorMessage && (
          <div className="absolute bottom-full left-0 mb-2 px-3 py-2 bg-destructive/10 border border-destructive/20 text-destructive text-sm rounded-lg animate-in fade-in slide-in-from-bottom-2 duration-150">
            {errorMessage}
          </div>
        )}
      </div>

      <Button
        onClick={handleSend}
        disabled={disabled || !input.trim()}
        size="icon-lg"
        className="group transition-all duration-150 ease-in-out hover:scale-105 active:scale-95 shrink-0"
        suppressHydrationWarning
      >
        {disabled ? (
          <Loader2 className="h-5 w-5 animate-spin" />
        ) : (
          <Send className="h-5 w-5 group-hover:translate-x-0.5 transition-transform" />
        )}
      </Button>
    </div>
  );
}
