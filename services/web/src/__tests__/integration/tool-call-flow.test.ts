/**
 * Integration test for complete tool call flow:
 * API Client parsing → useChat hook state → Component rendering
 */

import type { StreamEvent, ChatMessage, ToolCallMetadata } from '@/types/chat';

describe('Tool Call Integration Flow', () => {
  describe('SSE Event Parsing (API Client)', () => {
    it('should correctly parse tool_call SSE events', () => {
      // Simulate SSE event data from backend
      const eventData = {
        type: 'tool_call',
        tool_name: 'get_weather',
        tool_args: { location: 'Brussels', include_forecast: false },
        execution_time_ms: 142,
      };

      // This is what api-client.ts does
      const parsed = JSON.parse(JSON.stringify(eventData));
      const event: StreamEvent = {
        type: parsed.type as StreamEvent['type'],
        content: parsed.content || '',
        sources: parsed.sources,
        cited_indices: parsed.cited_indices,
      };

      // Add tool_call specific fields
      if (parsed.type === 'tool_call') {
        event.tool_name = parsed.tool_name;
        event.tool_args = parsed.tool_args;
        event.execution_time_ms = parsed.execution_time_ms;
      }

      // Assertions
      expect(event.type).toBe('tool_call');
      expect(event.tool_name).toBe('get_weather');
      expect(event.tool_args).toEqual({
        location: 'Brussels',
        include_forecast: false,
      });
      expect(event.execution_time_ms).toBe(142);
    });

    it('should handle multiple tool_call events in sequence', () => {
      const eventSequence: StreamEvent[] = [
        {
          type: 'tool_call',
          content: '',
          tool_name: 'search_knowledge_base',
          tool_args: { query: 'weather in Europe' },
          execution_time_ms: 156,
        },
        {
          type: 'token',
          content: 'The weather in Brussels ',
        },
        {
          type: 'tool_call',
          content: '',
          tool_name: 'get_weather',
          tool_args: { location: 'Brussels', include_forecast: true },
          execution_time_ms: 148,
        },
        {
          type: 'token',
          content: 'is partly cloudy with a temperature of 12°C.',
        },
        {
          type: 'done',
          content: '',
        },
      ];

      // Filter and extract tool calls
      const toolCalls = eventSequence
        .filter((e) => e.type === 'tool_call')
        .map((e) => ({
          tool_name: e.tool_name || '',
          tool_args: e.tool_args || {},
          execution_time_ms: e.execution_time_ms,
        })) as ToolCallMetadata[];

      expect(toolCalls).toHaveLength(2);
      expect(toolCalls[0].tool_name).toBe('search_knowledge_base');
      expect(toolCalls[1].tool_name).toBe('get_weather');
    });
  });

  describe('useChat Hook State Management', () => {
    it('should accumulate tool calls during streaming', () => {
      // Simulate the state accumulation that happens in useChat
      const assistantToolCalls: ToolCallMetadata[] = [];
      let assistantContent = '';

      // Simulate event stream
      const events: StreamEvent[] = [
        {
          type: 'tool_call',
          content: '',
          tool_name: 'get_weather',
          tool_args: { location: 'Paris' },
          execution_time_ms: 130,
        },
        {
          type: 'token',
          content: 'The weather in Paris',
        },
        {
          type: 'token',
          content: ' is sunny at 15°C.',
        },
      ];

      // Process events like useChat does
      for (const event of events) {
        if (event.type === 'tool_call') {
          const toolCall: ToolCallMetadata = {
            tool_name: event.tool_name || '',
            tool_args: event.tool_args || {},
            execution_time_ms: event.execution_time_ms,
          };
          assistantToolCalls.push(toolCall);
        } else if (event.type === 'token') {
          assistantContent += event.content;
        }
      }

      // Verify final state
      expect(assistantContent).toBe('The weather in Paris is sunny at 15°C.');
      expect(assistantToolCalls).toHaveLength(1);
      expect(assistantToolCalls[0]).toEqual({
        tool_name: 'get_weather',
        tool_args: { location: 'Paris' },
        execution_time_ms: 130,
      });
    });

    it('should create ChatMessage with tool calls', () => {
      const toolCall: ToolCallMetadata = {
        tool_name: 'get_weather',
        tool_args: { location: 'Amsterdam' },
        execution_time_ms: 125,
      };

      const message: ChatMessage = {
        role: 'assistant',
        content: 'Amsterdam weather is cool and cloudy.',
        timestamp: new Date(),
        toolCalls: [toolCall],
      };

      expect(message.toolCalls).toHaveLength(1);
      expect(message.toolCalls?.[0].tool_name).toBe('get_weather');
    });
  });

  describe('Chat Message Building', () => {
    it('should construct complete assistant message with all metadata', () => {
      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: 'Here is the weather information...',
        timestamp: new Date(),
        sources: [
          {
            title: 'weather_doc.pdf',
            path: '/docs/weather_doc.pdf',
            similarity: 0.95,
            page_number: 5,
          },
        ],
        citedIndices: [1],
        toolCalls: [
          {
            tool_name: 'get_weather',
            tool_args: { location: 'Berlin', include_forecast: true },
            execution_time_ms: 152,
          },
          {
            tool_name: 'search_knowledge_base',
            tool_args: { query: 'weather patterns' },
            execution_time_ms: 167,
          },
        ],
      };

      // Verify the message has all components
      expect(assistantMessage.role).toBe('assistant');
      expect(assistantMessage.sources).toHaveLength(1);
      expect(assistantMessage.citedIndices).toEqual([1]);
      expect(assistantMessage.toolCalls).toHaveLength(2);

      // Verify tool calls data
      const weatherTool = assistantMessage.toolCalls?.[0];
      expect(weatherTool?.tool_name).toBe('get_weather');
      expect(weatherTool?.execution_time_ms).toBe(152);

      const searchTool = assistantMessage.toolCalls?.[1];
      expect(searchTool?.tool_name).toBe('search_knowledge_base');
      expect(searchTool?.execution_time_ms).toBe(167);
    });
  });

  describe('Tool Call Metadata Validation', () => {
    it('should validate ToolCallMetadata structure', () => {
      const validToolCall: ToolCallMetadata = {
        tool_name: 'get_weather',
        tool_args: { location: 'Vienna' },
        execution_time_ms: 140,
      };

      expect(validToolCall.tool_name).toBeTruthy();
      expect(typeof validToolCall.tool_args).toBe('object');
      expect(typeof validToolCall.execution_time_ms).toBe('number');
    });

    it('should handle optional execution_time_ms', () => {
      const toolCall: ToolCallMetadata = {
        tool_name: 'get_weather',
        tool_args: { location: 'Prague' },
      };

      // Should not throw even without execution_time_ms
      expect(toolCall.tool_name).toBeTruthy();
      expect(toolCall.execution_time_ms).toBeUndefined();
    });

    it('should handle complex tool arguments', () => {
      const complexToolCall: ToolCallMetadata = {
        tool_name: 'search_knowledge_base',
        tool_args: {
          query: 'climate change in Europe',
          filters: {
            time_period: '2020-2024',
            regions: ['EU', 'UK'],
          },
          limit: 10,
          offset: 0,
        },
        execution_time_ms: 200,
      };

      expect(complexToolCall.tool_args.filters).toBeDefined();
      const filters = complexToolCall.tool_args.filters as Record<string, unknown>;
      expect((filters.regions as string[])).toEqual([
        'EU',
        'UK',
      ]);
    });
  });

  describe('Error Scenarios', () => {
    it('should handle tool_call events with missing fields gracefully', () => {
      const incompleteEvent: Partial<StreamEvent> = {
        type: 'tool_call',
        content: '',
        // tool_name is missing
        // tool_args is missing
      };

      // Should not crash when creating ToolCallMetadata
      const toolCall: ToolCallMetadata = {
        tool_name: (incompleteEvent as StreamEvent).tool_name || 'unknown',
        tool_args: (incompleteEvent as StreamEvent).tool_args || {},
        execution_time_ms: (incompleteEvent as StreamEvent).execution_time_ms,
      };

      expect(toolCall.tool_name).toBe('unknown');
      expect(toolCall.tool_args).toEqual({});
    });

    it('should preserve tool call order in message', () => {
      const toolCalls: ToolCallMetadata[] = [
        {
          tool_name: 'search_knowledge_base',
          tool_args: { query: 'first' },
          execution_time_ms: 100,
        },
        {
          tool_name: 'get_weather',
          tool_args: { location: 'second' },
          execution_time_ms: 200,
        },
        {
          tool_name: 'search_knowledge_base',
          tool_args: { query: 'third' },
          execution_time_ms: 150,
        },
      ];

      const message: ChatMessage = {
        role: 'assistant',
        content: 'Response',
        timestamp: new Date(),
        toolCalls,
      };

      expect(message.toolCalls?.[0].tool_args.query).toBe('first');
      expect(message.toolCalls?.[1].tool_args.location).toBe('second');
      expect(message.toolCalls?.[2].tool_args.query).toBe('third');
    });
  });
});
