'use client';

import { useState } from 'react';
import type { ToolCallMetadata } from '@/types/chat';
import { ChevronDown, ChevronRight, Clock, Zap, Map } from 'lucide-react';

// Tool metadata with enhanced visual identity
const toolMetadata: Record<string, {
  icon: string;
  displayName: string;
  description: string;
  color: string;
  bgColor: string;
  borderColor: string;
  iconBg: string;
  hasMapAction?: boolean;
}> = {
  get_weather: {
    icon: '🌤️',
    displayName: 'Weather API',
    description: 'Retrieved real-time weather data',
    color: 'text-sky-700',
    bgColor: 'bg-sky-50',
    borderColor: 'border-sky-200',
    iconBg: 'bg-sky-100',
  },
  search_knowledge_base: {
    icon: '📚',
    displayName: 'Knowledge Search',
    description: 'Searched internal knowledge base',
    color: 'text-indigo-700',
    bgColor: 'bg-indigo-50',
    borderColor: 'border-indigo-200',
    iconBg: 'bg-indigo-100',
  },
  get_worksite_info: {
    icon: '🚧',
    displayName: 'OSIRIS API',
    description: 'Retrieved Brussels worksite data',
    color: 'text-orange-700',
    bgColor: 'bg-orange-50',
    borderColor: 'border-orange-200',
    iconBg: 'bg-orange-100',
    hasMapAction: true,
  },
};

// Fallback for unknown tools
const defaultToolMetadata = {
  icon: '🔧',
  displayName: 'Tool',
  description: 'External tool execution',
  color: 'text-gray-700',
  bgColor: 'bg-gray-50',
  borderColor: 'border-gray-200',
  iconBg: 'bg-gray-100',
};

interface ToolCallBadgeProps {
  toolCalls?: ToolCallMetadata[];
  onViewMap?: (worksiteId: string) => void;
}

export function ToolCallBadge({ toolCalls, onViewMap }: ToolCallBadgeProps) {
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);
  const [loadingMap, setLoadingMap] = useState<number | null>(null);

  if (!toolCalls || toolCalls.length === 0) {
    return null;
  }

  return (
    <div className="mt-4 space-y-2">
      {/* Header badge for multiple tools */}
      {toolCalls.length > 1 && (
        <div className="flex items-center gap-2 text-xs text-gray-600 mb-2">
          <Zap className="w-3.5 h-3.5" />
          <span className="font-medium">{toolCalls.length} tools used</span>
        </div>
      )}

      {toolCalls.map((toolCall, index) => {
        const metadata = toolMetadata[toolCall.tool_name] || defaultToolMetadata;
        const isExpanded = expandedIndex === index;
        const hasArgs = toolCall.tool_args && Object.keys(toolCall.tool_args).length > 0;

        return (
          <div
            key={index}
            className={`
              rounded-lg border transition-all duration-200
              ${metadata.borderColor} ${metadata.bgColor}
              hover:shadow-sm
            `}
          >
            {/* Tool Header - Always Visible */}
            <button
              onClick={() => setExpandedIndex(isExpanded ? null : index)}
              className="w-full px-3 py-2.5 flex items-center gap-3 text-left"
            >
              {/* Icon */}
              <div className={`
                shrink-0 w-8 h-8 rounded-lg flex items-center justify-center
                ${metadata.iconBg}
              `}>
                <span className="text-lg leading-none">{metadata.icon}</span>
              </div>

              {/* Tool Info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className={`font-semibold text-sm ${metadata.color}`}>
                    {metadata.displayName}
                  </span>
                  {toolCall.execution_time_ms && (
                    <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs bg-white/60 text-gray-600">
                      <Clock className="w-3 h-3" />
                      {toolCall.execution_time_ms}ms
                    </span>
                  )}
                </div>
                <p className="text-xs text-gray-600 mt-0.5">
                  {metadata.description}
                </p>
              </div>

              {/* Expand/Collapse Icon */}
              {hasArgs && (
                <div className="shrink-0">
                  {isExpanded ? (
                    <ChevronDown className="w-4 h-4 text-gray-400" />
                  ) : (
                    <ChevronRight className="w-4 h-4 text-gray-400" />
                  )}
                </div>
              )}
            </button>

            {/* View Map Action for OSIRIS worksite tool */}
            {metadata.hasMapAction && onViewMap && Boolean(toolCall.tool_args?.worksite_id) && (
              <div className="px-3 pb-2">
                <button
                  onClick={() => {
                    setLoadingMap(index);
                    onViewMap(String(toolCall.tool_args.worksite_id));
                  }}
                  disabled={loadingMap === index}
                  className={`
                    flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium
                    transition-all duration-200
                    ${loadingMap === index
                      ? 'bg-orange-200 text-orange-500 cursor-wait'
                      : 'bg-orange-100 text-orange-700 hover:bg-orange-200 hover:shadow-sm'
                    }
                  `}
                >
                  <Map className="w-3.5 h-3.5" />
                  {loadingMap === index ? 'Loading...' : 'View Map'}
                </button>
              </div>
            )}

            {/* Expanded Arguments Section */}
            {isExpanded && hasArgs && (
              <div className="px-3 pb-3 pt-0">
                <div className="border-t border-gray-200/50 pt-2">
                  <div className="text-xs font-semibold text-gray-700 mb-2 flex items-center gap-1.5">
                    <span>Parameters</span>
                    <span className="text-gray-400">•</span>
                    <span className="font-normal text-gray-500">
                      {Object.keys(toolCall.tool_args).length} {Object.keys(toolCall.tool_args).length === 1 ? 'parameter' : 'parameters'}
                    </span>
                  </div>

                  {/* Pretty-printed arguments */}
                  <div className="bg-white/60 rounded-md p-3 border border-gray-200/50">
                    <dl className="space-y-2">
                      {Object.entries(toolCall.tool_args).map(([key, value]) => (
                        <div key={key} className="flex flex-col">
                          <dt className="text-xs font-mono font-semibold text-gray-700 mb-0.5">
                            {key}:
                          </dt>
                          <dd className="text-xs font-mono text-gray-600 pl-3 wrap-break-word">
                            {typeof value === 'object'
                              ? JSON.stringify(value, null, 2)
                              : String(value)}
                          </dd>
                        </div>
                      ))}
                    </dl>
                  </div>
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
