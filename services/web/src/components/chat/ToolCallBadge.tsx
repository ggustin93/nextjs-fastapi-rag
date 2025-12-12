'use client';

import { useState, useMemo } from 'react';
import type { ToolCallMetadata } from '@/types/chat';
import { ChevronDown, ChevronRight, Zap, Map, Code2 } from 'lucide-react';

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

// Grouped tool call with count
interface GroupedToolCall {
  tool_name: string;
  count: number;
  // Keep first call's data for display (args, etc.)
  firstCall: ToolCallMetadata;
  // All calls for expanded view
  allCalls: ToolCallMetadata[];
}

interface ToolCallBadgeProps {
  toolCalls?: ToolCallMetadata[];
  onViewMap?: (worksiteId: string) => Promise<void>;
}

export function ToolCallBadge({ toolCalls, onViewMap }: ToolCallBadgeProps) {
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);
  const [loadingMap, setLoadingMap] = useState<string | null>(null);
  // Track which tool responses are shown (by "groupIndex-callIndex")
  const [showResponse, setShowResponse] = useState<Set<string>>(new Set());

  // Group consecutive identical tool calls (preserves execution order)
  const groupedTools = useMemo((): GroupedToolCall[] => {
    if (!toolCalls || toolCalls.length === 0) return [];

    const groups: GroupedToolCall[] = [];

    toolCalls.forEach((call) => {
      const lastGroup = groups[groups.length - 1];

      // Group consecutive calls with same tool_name
      if (lastGroup && lastGroup.tool_name === call.tool_name) {
        lastGroup.count++;
        lastGroup.allCalls.push(call);
      } else {
        // New tool or different from previous → create new group
        groups.push({
          tool_name: call.tool_name,
          count: 1,
          firstCall: call,
          allCalls: [call],
        });
      }
    });

    return groups;
  }, [toolCalls]);

  if (groupedTools.length === 0) {
    return null;
  }

  const totalCalls = toolCalls?.length || 0;

  return (
    <div className="mt-4 space-y-2">
      {/* Header badge - show total if different from groups */}
      {totalCalls > 1 && (
        <div className="flex items-center gap-2 text-xs text-gray-500 mb-2">
          <Zap className="w-3.5 h-3.5" />
          <span className="font-medium">{totalCalls} tools used</span>
        </div>
      )}

      {groupedTools.map((group, index) => {
        const metadata = toolMetadata[group.tool_name] || defaultToolMetadata;

        // Debug: Log unknown tools to help identify mapping issues
        if (!toolMetadata[group.tool_name]) {
          console.warn(`[ToolCallBadge] Unknown tool: "${group.tool_name}", using fallback. Known tools:`, Object.keys(toolMetadata));
        }
        const isExpanded = expandedIndex === index;

        // Check if expandable (has args or has result)
        const hasArgs = group.allCalls.some(
          (call) => (call.tool_args && Object.keys(call.tool_args).length > 0) || call.tool_result
        );

        // For map action, get the worksite_id from first call that has it
        const worksiteCall = group.allCalls.find(
          (call) => call.tool_args?.worksite_id
        );
        const worksiteId = worksiteCall?.tool_args?.worksite_id as string | undefined;

        return (
          <div
            key={group.tool_name}
            className={`
              rounded-lg border transition-all duration-200
              ${metadata.borderColor} ${metadata.bgColor}
              hover:shadow-sm
            `}
          >
            {/* Tool Header */}
            <div className="flex items-center">
              {/* Clickable area for expand/collapse */}
              <button
                onClick={() => hasArgs && setExpandedIndex(isExpanded ? null : index)}
                className={`
                  flex-1 px-3 py-2.5 flex items-center gap-3 text-left
                  ${hasArgs ? 'cursor-pointer' : 'cursor-default'}
                `}
                disabled={!hasArgs}
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
                    {/* Count badge for multiple calls */}
                    {group.count > 1 && (
                      <span className={`
                        inline-flex items-center justify-center
                        px-1.5 py-0.5 rounded-full text-xs font-medium
                        ${metadata.iconBg} ${metadata.color}
                      `}>
                        ×{group.count}
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-gray-600 mt-0.5">
                    {metadata.description}
                  </p>
                </div>
              </button>

              {/* Right side actions */}
              <div className="flex items-center gap-2 pr-3">
                {/* View Map Action for OSIRIS worksite tool */}
                {metadata.hasMapAction && onViewMap && worksiteId && (
                  <button
                    onClick={async (e) => {
                      e.stopPropagation();
                      setLoadingMap(String(worksiteId));
                      try {
                        await onViewMap(String(worksiteId));
                      } finally {
                        setLoadingMap(null);
                      }
                    }}
                    disabled={loadingMap === String(worksiteId)}
                    className={`
                      flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-medium
                      transition-all duration-200
                      ${loadingMap === String(worksiteId)
                        ? 'bg-orange-200 text-orange-500 cursor-wait'
                        : 'bg-orange-100 text-orange-700 hover:bg-orange-200 hover:shadow-sm'
                      }
                    `}
                  >
                    <Map className="w-3.5 h-3.5" />
                    {loadingMap === String(worksiteId) ? 'Loading...' : 'View Map'}
                  </button>
                )}

                {/* JSON Response Toggle - subtle icon */}
                {group.allCalls.some(call => call.tool_result && call.tool_result.trim().length > 0) && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      const responseKey = `${index}-json`;
                      const newSet = new Set(showResponse);
                      if (showResponse.has(responseKey)) {
                        newSet.delete(responseKey);
                      } else {
                        newSet.add(responseKey);
                      }
                      setShowResponse(newSet);
                    }}
                    className={`
                      p-1.5 rounded transition-all duration-200
                      ${showResponse.has(`${index}-json`)
                        ? 'bg-violet-100 text-violet-600'
                        : 'text-gray-400 hover:text-violet-600 hover:bg-violet-50'
                      }
                    `}
                    title="View JSON response"
                  >
                    <Code2 className="w-4 h-4" />
                  </button>
                )}

                {/* Expand/Collapse Icon */}
                {hasArgs && (
                  <button
                    onClick={() => setExpandedIndex(isExpanded ? null : index)}
                    className="p-1 rounded hover:bg-black/5 transition-colors"
                  >
                    {isExpanded ? (
                      <ChevronDown className="w-4 h-4 text-gray-400" />
                    ) : (
                      <ChevronRight className="w-4 h-4 text-gray-400" />
                    )}
                  </button>
                )}
              </div>
            </div>

            {/* JSON Response Panel (from header icon) */}
            {showResponse.has(`${index}-json`) && (
              <div className="px-3 pb-3 pt-0">
                <div className="border-t border-gray-200/50 pt-2">
                  <div className="bg-gray-900 rounded-md p-3 border border-gray-700 overflow-x-auto max-h-64 overflow-y-auto">
                    <pre className="text-xs font-mono text-green-400 whitespace-pre-wrap break-words">
                      {group.allCalls.map((call, callIndex) => {
                        if (!call.tool_result) return null;
                        try {
                          const parsed = JSON.parse(call.tool_result);
                          // Extract raw_api_response if available (e.g., from OSIRIS tool)
                          const displayData = parsed.raw_api_response ?? parsed;
                          return (
                            <span key={callIndex}>
                              {group.count > 1 && <span className="text-gray-500">{`/* Call ${callIndex + 1} */\n`}</span>}
                              {JSON.stringify(displayData, null, 2)}
                              {callIndex < group.allCalls.length - 1 && '\n\n'}
                            </span>
                          );
                        } catch {
                          return (
                            <span key={callIndex}>
                              {group.count > 1 && <span className="text-gray-500">{`/* Call ${callIndex + 1} */\n`}</span>}
                              {call.tool_result}
                              {callIndex < group.allCalls.length - 1 && '\n\n'}
                            </span>
                          );
                        }
                      })}
                    </pre>
                  </div>
                </div>
              </div>
            )}

            {/* Expanded Arguments Section */}
            {isExpanded && hasArgs && (
              <div className="px-3 pb-3 pt-0">
                <div className="border-t border-gray-200/50 pt-2">
                  {group.allCalls.map((call, callIndex) => {
                    const hasToolArgs = call.tool_args && Object.keys(call.tool_args).length > 0;

                    if (!hasToolArgs) {
                      return null;
                    }

                    return (
                      <div key={callIndex} className="mb-3 last:mb-0">
                        {/* Show call number if multiple calls */}
                        {group.count > 1 && (
                          <div className="text-xs font-medium text-gray-500 mb-1">
                            Call {callIndex + 1}
                          </div>
                        )}

                        {/* Arguments */}
                        {hasToolArgs && (
                          <div className="bg-white/60 rounded-md p-3 border border-gray-200/50">
                            <dl className="space-y-2">
                              {Object.entries(call.tool_args).map(([key, value]) => (
                                <div key={key} className="flex flex-col">
                                  <dt className="text-xs font-mono font-semibold text-gray-700 mb-0.5">
                                    {key}:
                                  </dt>
                                  <dd className="text-xs font-mono text-gray-600 pl-3 break-words">
                                    {typeof value === 'object'
                                      ? JSON.stringify(value, null, 2)
                                      : String(value)}
                                  </dd>
                                </div>
                              ))}
                            </dl>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
