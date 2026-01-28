import { FileSearch, Ticket, Headphones, CloudSun, LucideIcon } from 'lucide-react';

/**
 * Centralized agent configuration for UI consistency across all components.
 * Used by: AgentSelector, ChatInput (@ mentions), Welcome cards
 */
export interface AgentConfig {
  id: string;
  name: string;
  icon: LucideIcon;
  color: string;
  bgColor: string;
  description: string;
  keywords: string[];
}

export const AGENT_CONFIG: Record<string, AgentConfig> = {
  rag: {
    id: 'rag',
    name: 'Documents',
    icon: FileSearch,
    color: 'text-blue-600',
    bgColor: 'bg-blue-500/10',
    description: 'Base documentaire',
    keywords: ['rag', 'documents', 'doc', 'kb', 'knowledge', 'recherche'],
  },
  otrs: {
    id: 'otrs',
    name: 'Tickets',
    icon: Ticket,
    color: 'text-orange-600',
    bgColor: 'bg-orange-500/10',
    description: 'Suivi OTRS',
    keywords: ['otrs', 'tickets', 'ticket', 'suivi'],
  },
  helpdesk: {
    id: 'helpdesk',
    name: 'Helpdesk',
    icon: Headphones,
    color: 'text-green-600',
    bgColor: 'bg-green-500/10',
    description: 'Support utilisateur',
    keywords: ['helpdesk', 'support', 'aide', 'osiris', 'cdco'],
  },
  weather: {
    id: 'weather',
    name: 'Météo',
    icon: CloudSun,
    color: 'text-sky-600',
    bgColor: 'bg-sky-500/10',
    description: 'Conditions actuelles',
    keywords: ['weather', 'meteo', 'météo', 'temps'],
  },
};

// Ordered list for UI display (welcome cards, dropdowns)
export const AGENT_LIST: AgentConfig[] = [
  AGENT_CONFIG.rag,
  AGENT_CONFIG.otrs,
  AGENT_CONFIG.helpdesk,
  AGENT_CONFIG.weather,
];

// Agent ID mapping (includes aliases for @ mentions)
export const AGENT_ALIASES: Record<string, string> = {
  // RAG / Documents
  rag: 'rag',
  assistant: 'rag',
  default: 'rag',
  kb: 'rag',
  documents: 'rag',
  doc: 'rag',
  // OTRS / Tickets
  otrs: 'otrs',
  'otrs-agent': 'otrs',
  tickets: 'otrs',
  ticket: 'otrs',
  // Helpdesk
  helpdesk: 'helpdesk',
  cdco: 'helpdesk',
  support: 'helpdesk',
  aide: 'helpdesk',
  // Weather / Météo
  weather: 'weather',
  meteo: 'weather',
  météo: 'weather',
};

// Get config by ID (handles aliases)
export function getAgentConfig(id: string): AgentConfig | undefined {
  const normalizedId = AGENT_ALIASES[id.toLowerCase()] || id.toLowerCase();
  return AGENT_CONFIG[normalizedId];
}
