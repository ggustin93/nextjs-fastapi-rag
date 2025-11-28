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

    expect(screen.getByText('Weather')).toBeInTheDocument();
    expect(screen.getByText('🌤️')).toBeInTheDocument();
    expect(screen.getByText('(150ms)')).toBeInTheDocument();
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
    expect(screen.getByText('(200ms)')).toBeInTheDocument();
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

    expect(screen.getByText('Weather')).toBeInTheDocument();
    expect(screen.getByText('Knowledge Search')).toBeInTheDocument();
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

    const badge = screen.getByText('Weather').closest('button');
    expect(badge).toBeInTheDocument();

    // Initially, arguments should not be visible
    expect(screen.queryByText('Arguments:')).not.toBeInTheDocument();

    // Click to expand
    fireEvent.click(badge!);
    expect(screen.getByText('Arguments:')).toBeInTheDocument();

    // Arguments should contain the tool args
    expect(screen.getByText(/location/)).toBeInTheDocument();
    expect(screen.getByText(/include_forecast/)).toBeInTheDocument();

    // Click again to collapse
    fireEvent.click(badge!);
    expect(screen.queryByText('Arguments:')).not.toBeInTheDocument();
  });

  it('should handle unknown tool names gracefully', () => {
    const toolCalls: ToolCallMetadata[] = [
      {
        tool_name: 'unknown_tool',
        tool_args: { param: 'value' },
        execution_time_ms: 100,
      },
    ];

    render(<ToolCallBadge toolCalls={toolCalls} />);

    // Should display the tool name as-is
    expect(screen.getByText('unknown_tool')).toBeInTheDocument();
    // Should show a generic tool icon
    expect(screen.getByText('🔧')).toBeInTheDocument();
  });

  it('should handle tool calls without execution time', () => {
    const toolCalls: ToolCallMetadata[] = [
      {
        tool_name: 'get_weather',
        tool_args: { location: 'Tokyo' },
      },
    ];

    render(<ToolCallBadge toolCalls={toolCalls} />);

    expect(screen.getByText('Weather')).toBeInTheDocument();
    // Should not show execution time
    expect(screen.queryByText(/\d+ms/)).not.toBeInTheDocument();
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

    const badge = screen.getByText('Weather').closest('button');
    expect(badge).toBeInTheDocument();

    // Click to try expanding
    fireEvent.click(badge!);

    // Should not show expandable arguments for empty args
    expect(screen.queryByText('Arguments:')).not.toBeInTheDocument();
  });
});
