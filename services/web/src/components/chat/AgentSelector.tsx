'use client';

import { useState, useEffect, memo } from 'react';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { AGENT_CONFIG, AGENT_LIST, getAgentConfig } from './agentConfig';

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
        // Fallback to AGENT_LIST config
        setAgents(AGENT_LIST.map(a => ({
          id: a.id,
          name: a.name,
          icon: '',
          description: a.description,
        })));
      }
    };

    fetchAgents();
  }, [selectedAgent, onSelectAgent]);

  const currentAgent = agents.find(a => a.id === selectedAgent) || agents[0];
  const currentConfig = currentAgent ? getAgentConfig(currentAgent.id) : null;

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
          {currentConfig ? (
            <>
              <currentConfig.icon className={cn("h-4 w-4", currentConfig.color)} />
              <span className="text-sm hidden sm:inline">{currentConfig.name}</span>
            </>
          ) : (
            <span className="text-sm">{currentAgent?.name}</span>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-52 p-1 z-50" align="start">
        <div className="flex flex-col gap-0.5">
          {agents.map((agent) => {
            const config = getAgentConfig(agent.id);
            const IconComponent = config?.icon;

            return (
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
                {config && IconComponent ? (
                  <div className={cn("rounded-md p-1.5", config.bgColor)}>
                    <IconComponent className={cn("h-4 w-4", config.color)} />
                  </div>
                ) : (
                  <div className="rounded-md p-1.5 bg-muted">
                    <span className="text-sm">{agent.icon || '?'}</span>
                  </div>
                )}
                <div className="flex flex-col min-w-0">
                  <span className="font-medium text-sm">{config?.name || agent.name}</span>
                  <span className="text-xs text-muted-foreground truncate">
                    {config?.description || agent.description}
                  </span>
                </div>
              </button>
            );
          })}
        </div>
      </PopoverContent>
    </Popover>
  );
});
