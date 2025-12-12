import { render, screen, fireEvent } from '@testing-library/react';
import { ToolCallBadge } from '../components/chat/ToolCallBadge';
import type { ToolCallMetadata } from '@/types/chat';

describe('ToolCallBadge', () => {
  it('should render nothing when no tool calls are provided', () => {
    const { container } = render(<ToolCallBadge />);
    expect(container.firstChild).toBeNull();
  });

  it('should render nothing when tool calls array is empty', () => {
    const { container } = render(<ToolCallBadge toolCalls={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it('should render weather tool badge with icon and name', () => {
    const toolCalls: ToolCallMetadata[] = [
      {
        tool_name: 'get_weather',
        tool_args: { location: 'Brussels' },
        execution_time_ms: 150,
      },
    ];

    render(<ToolCallBadge toolCalls={toolCalls} />);

    expect(screen.getByText('Weather API')).toBeInTheDocument();
    expect(screen.getByText('🌤️')).toBeInTheDocument();
    expect(screen.getByText('Retrieved real-time weather data')).toBeInTheDocument();
  });

  it('should render knowledge search tool badge', () => {
    const toolCalls: ToolCallMetadata[] = [
      {
        tool_name: 'search_knowledge_base',
        tool_args: { query: 'test query' },
        execution_time_ms: 200,
      },
    ];

    render(<ToolCallBadge toolCalls={toolCalls} />);

    expect(screen.getByText('Knowledge Search')).toBeInTheDocument();
    expect(screen.getByText('📚')).toBeInTheDocument();
    expect(screen.getByText('Searched internal knowledge base')).toBeInTheDocument();
  });

  it('should render multiple tool call badges', () => {
    const toolCalls: ToolCallMetadata[] = [
      {
        tool_name: 'get_weather',
        tool_args: { location: 'Paris' },
        execution_time_ms: 120,
      },
      {
        tool_name: 'search_knowledge_base',
        tool_args: { query: 'weather' },
        execution_time_ms: 180,
      },
    ];

    render(<ToolCallBadge toolCalls={toolCalls} />);

    expect(screen.getByText('Weather API')).toBeInTheDocument();
    expect(screen.getByText('Knowledge Search')).toBeInTheDocument();
    // Should show total tools count when multiple
    expect(screen.getByText('2 tools used')).toBeInTheDocument();
  });

  it('should show expandable tool arguments on click', () => {
    const toolCalls: ToolCallMetadata[] = [
      {
        tool_name: 'get_weather',
        tool_args: { location: 'London', include_forecast: true },
        execution_time_ms: 140,
      },
    ];

    render(<ToolCallBadge toolCalls={toolCalls} />);

    const badge = screen.getByText('Weather API').closest('button');
    expect(badge).toBeInTheDocument();

    // Initially, parameters should not be visible
    expect(screen.queryByText(/location:/)).not.toBeInTheDocument();

    // Click to expand
    fireEvent.click(badge!);

    // Parameters should contain the tool args (displayed as key: value)
    expect(screen.getByText(/location/)).toBeInTheDocument();
    expect(screen.getByText(/include_forecast/)).toBeInTheDocument();
    expect(screen.getByText(/London/)).toBeInTheDocument();

    // Click again to collapse
    fireEvent.click(badge!);
    expect(screen.queryByText(/location:/)).not.toBeInTheDocument();
  });

  it('should handle unknown tool names gracefully', () => {
    // Suppress console.warn for this test
    const warnSpy = jest.spyOn(console, 'warn').mockImplementation(() => {});

    const toolCalls: ToolCallMetadata[] = [
      {
        tool_name: 'unknown_tool',
        tool_args: { param: 'value' },
        execution_time_ms: 100,
      },
    ];

    render(<ToolCallBadge toolCalls={toolCalls} />);

    // Should display fallback display name for unknown tools
    expect(screen.getByText('Tool')).toBeInTheDocument();
    // Should show a generic tool icon
    expect(screen.getByText('🔧')).toBeInTheDocument();

    warnSpy.mockRestore();
  });

  it('should handle tool calls without execution time', () => {
    const toolCalls: ToolCallMetadata[] = [
      {
        tool_name: 'get_weather',
        tool_args: { location: 'Tokyo' },
      },
    ];

    render(<ToolCallBadge toolCalls={toolCalls} />);

    expect(screen.getByText('Weather API')).toBeInTheDocument();
    expect(screen.getByText('Retrieved real-time weather data')).toBeInTheDocument();
  });

  it('should handle tool calls with empty arguments', () => {
    const toolCalls: ToolCallMetadata[] = [
      {
        tool_name: 'get_weather',
        tool_args: {},
        execution_time_ms: 100,
      },
    ];

    render(<ToolCallBadge toolCalls={toolCalls} />);

    const badge = screen.getByText('Weather API').closest('button');
    expect(badge).toBeInTheDocument();

    // Click to try expanding - should not have expandable content for empty args
    fireEvent.click(badge!);

    // Should not show any parameter keys since args are empty
    expect(screen.queryByRole('definition')).not.toBeInTheDocument();
  });

  it('should group consecutive identical tool calls', () => {
    const toolCalls: ToolCallMetadata[] = [
      {
        tool_name: 'search_knowledge_base',
        tool_args: { query: 'first query' },
      },
      {
        tool_name: 'search_knowledge_base',
        tool_args: { query: 'second query' },
      },
    ];

    render(<ToolCallBadge toolCalls={toolCalls} />);

    // Should show ×2 badge for grouped calls
    expect(screen.getByText('×2')).toBeInTheDocument();
    // Should only have one Knowledge Search card
    expect(screen.getAllByText('Knowledge Search')).toHaveLength(1);
  });

  it('should render OSIRIS worksite tool badge', () => {
    const toolCalls: ToolCallMetadata[] = [
      {
        tool_name: 'get_worksite_info',
        tool_args: { worksite_id: '12345' },
      },
    ];

    render(<ToolCallBadge toolCalls={toolCalls} />);

    expect(screen.getByText('OSIRIS API')).toBeInTheDocument();
    expect(screen.getByText('🚧')).toBeInTheDocument();
    expect(screen.getByText('Retrieved Brussels worksite data')).toBeInTheDocument();
  });
});
