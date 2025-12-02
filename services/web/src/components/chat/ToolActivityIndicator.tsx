'use client';

import { Search, FileText, Brain, Sparkles } from 'lucide-react';

interface ToolActivityIndicatorProps {
  isActive?: boolean;
  currentTool?: string;
}

/**
 * Explicit tool activity indicator - shows what the AI is actually doing
 * Transparent about tool usage: "Uses search_knowledge_base...", "Thinking..."
 */
export function ToolActivityIndicator({
  isActive = true,
  currentTool
}: ToolActivityIndicatorProps) {
  if (!isActive) return null;

  // Determine icon and message based on tool
  const getToolDisplay = () => {
    if (currentTool?.includes('search') || currentTool?.includes('knowledge')) {
      return {
        icon: <Search className="h-3.5 w-3.5 animate-pulse" style={{ animationDuration: '1.5s' }} />,
        message: 'Uses search_knowledge_base...'
      };
    }
    if (currentTool?.includes('document') || currentTool?.includes('fetch')) {
      return {
        icon: <FileText className="h-3.5 w-3.5 animate-pulse" style={{ animationDuration: '1.5s' }} />,
        message: 'Retrieves documents...'
      };
    }
    if (currentTool?.includes('analyze') || currentTool?.includes('process')) {
      return {
        icon: <Sparkles className="h-3.5 w-3.5 animate-pulse" style={{ animationDuration: '1.5s' }} />,
        message: 'Analyzing content...'
      };
    }
    // Default: thinking/reasoning
    return {
      icon: <Brain className="h-3.5 w-3.5 animate-pulse" style={{ animationDuration: '1.5s' }} />,
      message: 'Thinking...'
    };
  };

  const { icon, message } = getToolDisplay();

  return (
    <div className="flex items-center gap-2.5 text-[13px] text-muted-foreground/80">
      {/* Tool icon */}
      <div className="text-primary/60">
        {icon}
      </div>

      {/* Explicit message about what's happening */}
      <span className="font-light tracking-wide animate-pulse" style={{ animationDuration: '2s' }}>
        {message}
      </span>
    </div>
  );
}
