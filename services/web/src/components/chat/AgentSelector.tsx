'use client';

import { useState, useEffect, memo, useCallback } from 'react';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface Agent {
  id: string;
  name: string;
  icon: string;
  description: string;
}

interface AgentSelectorProps {
  selectedAgent: string | null;
  onSelectAgent: (agentId: string) => void;
  disabled?: boolean;
}

export const AgentSelector = memo(function AgentSelector({ selectedAgent, onSelectAgent, disabled = false }: AgentSelectorProps) {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const fetchAgents = async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
        const response = await fetch(`${apiUrl}/agents`);

        if (response.ok) {
          const data: Agent[] = await response.json();
          setAgents(data);

          // Default to 'rag' if no selection
          if (!selectedAgent && data.length > 0) {
            const defaultAgent = data.find(a => a.id === 'rag') || data[0];
            onSelectAgent(defaultAgent.id);
          }
        }
      } catch (error) {
        console.error('Failed to fetch agents:', error);
        // Fallback agents for offline
        setAgents([
          { id: 'rag', name: 'RAG', icon: '📚', description: 'Knowledge base + Osiris' },
          { id: 'weather', name: 'Météo', icon: '🌤️', description: 'Weather assistant' },
        ]);
      }
    };

    fetchAgents();
  }, [selectedAgent, onSelectAgent]);

  const currentAgent = agents.find(a => a.id === selectedAgent) || agents[0];

  if (agents.length === 0) return null;

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          disabled={disabled}
          className={cn(
            "h-9 px-2.5 gap-1.5 font-medium transition-all",
            "hover:bg-primary/10 hover:text-primary",
            "border border-transparent hover:border-primary/20",
            "rounded-full",
            open && "bg-primary/10 border-primary/20"
          )}
        >
          <span className="text-base leading-none">{currentAgent?.icon}</span>
          <span className="text-sm hidden sm:inline">{currentAgent?.name}</span>
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-48 p-1" align="start">
        <div className="flex flex-col gap-0.5">
          {agents.map((agent) => (
            <button
              key={agent.id}
              onClick={() => {
                onSelectAgent(agent.id);
                setOpen(false);
              }}
              className={cn(
                "flex items-center gap-2.5 px-3 py-2 rounded-md text-left transition-colors",
                "hover:bg-accent",
                selectedAgent === agent.id && "bg-primary/10 text-primary"
              )}
            >
              <span className="text-lg leading-none">{agent.icon}</span>
              <div className="flex flex-col min-w-0">
                <span className="font-medium text-sm">{agent.name}</span>
                <span className="text-xs text-muted-foreground truncate">{agent.description}</span>
              </div>
            </button>
          ))}
        </div>
      </PopoverContent>
    </Popover>
  );
});
