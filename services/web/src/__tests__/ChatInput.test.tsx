import { render, screen, fireEvent } from '@testing-library/react';
import { ChatInput } from '@/components/chat/ChatInput';

// Mock the AgentSelector to avoid API calls in tests
jest.mock('@/components/chat/AgentSelector', () => ({
  AgentSelector: ({ selectedAgent }: { selectedAgent: string | null }) => (
    <div data-testid="agent-selector">{selectedAgent || 'rag'}</div>
  ),
}));

describe('ChatInput', () => {
  const mockOnSend = jest.fn();
  const mockOnSelectAgent = jest.fn();
  const defaultProps = {
    onSend: mockOnSend,
    selectedAgent: 'rag',
    onSelectAgent: mockOnSelectAgent,
  };

  beforeEach(() => {
    mockOnSend.mockClear();
    mockOnSelectAgent.mockClear();
  });

  it('renders input and button', () => {
    render(<ChatInput {...defaultProps} />);

    expect(screen.getByPlaceholderText('Écrivez votre message... (@agent)')).toBeInTheDocument();
    expect(screen.getByRole('button')).toBeInTheDocument();
  });

  it('calls onSend when clicking send button with valid input', () => {
    render(<ChatInput {...defaultProps} />);

    const input = screen.getByPlaceholderText('Écrivez votre message... (@agent)');
    fireEvent.change(input, { target: { value: 'Hello' } });
    fireEvent.click(screen.getByRole('button'));

    expect(mockOnSend).toHaveBeenCalledWith('Hello');
  });

  it('clears input after sending', () => {
    render(<ChatInput {...defaultProps} />);

    const input = screen.getByPlaceholderText('Écrivez votre message... (@agent)') as HTMLInputElement;
    fireEvent.change(input, { target: { value: 'Hello' } });
    fireEvent.click(screen.getByRole('button'));

    expect(input.value).toBe('');
  });

  it('does not send empty messages', () => {
    render(<ChatInput {...defaultProps} />);

    fireEvent.click(screen.getByRole('button'));

    expect(mockOnSend).not.toHaveBeenCalled();
  });

  it('does not send whitespace-only messages', () => {
    render(<ChatInput {...defaultProps} />);

    const input = screen.getByPlaceholderText('Écrivez votre message... (@agent)');
    fireEvent.change(input, { target: { value: '   ' } });
    fireEvent.click(screen.getByRole('button'));

    expect(mockOnSend).not.toHaveBeenCalled();
  });

  it('sends on Enter key press', () => {
    render(<ChatInput {...defaultProps} />);

    const input = screen.getByPlaceholderText('Écrivez votre message... (@agent)');
    fireEvent.change(input, { target: { value: 'Hello' } });
    fireEvent.keyDown(input, { key: 'Enter' });

    expect(mockOnSend).toHaveBeenCalledWith('Hello');
  });

  it('disables input when disabled prop is true', () => {
    render(<ChatInput {...defaultProps} disabled />);

    expect(screen.getByPlaceholderText('Écrivez votre message... (@agent)')).toBeDisabled();
    expect(screen.getByRole('button')).toBeDisabled();
  });

  it('renders agent selector', () => {
    render(<ChatInput {...defaultProps} />);
    expect(screen.getByTestId('agent-selector')).toBeInTheDocument();
  });

  it('switches agent when typing @weather mention', () => {
    render(<ChatInput {...defaultProps} />);

    const input = screen.getByPlaceholderText('Écrivez votre message... (@agent)') as HTMLInputElement;
    fireEvent.change(input, { target: { value: '@weather ' } });

    expect(mockOnSelectAgent).toHaveBeenCalledWith('weather');
    expect(input.value).toBe(''); // @mention removed from input
  });

  it('switches agent when typing @rag mention', () => {
    render(<ChatInput {...defaultProps} selectedAgent="weather" />);

    const input = screen.getByPlaceholderText('Écrivez votre message... (@agent)') as HTMLInputElement;
    fireEvent.change(input, { target: { value: '@rag ' } });

    expect(mockOnSelectAgent).toHaveBeenCalledWith('rag');
  });

  it('supports agent aliases like @meteo', () => {
    render(<ChatInput {...defaultProps} />);

    const input = screen.getByPlaceholderText('Écrivez votre message... (@agent)');
    fireEvent.change(input, { target: { value: '@meteo ' } });

    expect(mockOnSelectAgent).toHaveBeenCalledWith('weather');
  });

  it('shows autocomplete dropdown when typing @', () => {
    render(<ChatInput {...defaultProps} />);

    const input = screen.getByPlaceholderText('Écrivez votre message... (@agent)');
    fireEvent.change(input, { target: { value: '@' } });

    expect(screen.getByText('Agents')).toBeInTheDocument();
    expect(screen.getByText('RAG')).toBeInTheDocument();
    expect(screen.getByText('Météo')).toBeInTheDocument();
  });

  it('selects agent from autocomplete with Enter key', () => {
    render(<ChatInput {...defaultProps} />);

    const input = screen.getByPlaceholderText('Écrivez votre message... (@agent)');
    fireEvent.change(input, { target: { value: '@' } });
    fireEvent.keyDown(input, { key: 'ArrowDown' }); // Select weather
    fireEvent.keyDown(input, { key: 'Enter' });

    expect(mockOnSelectAgent).toHaveBeenCalledWith('weather');
  });

  it('shows error message for unknown agent', () => {
    render(<ChatInput {...defaultProps} />);

    const input = screen.getByPlaceholderText('Écrivez votre message... (@agent)');
    fireEvent.change(input, { target: { value: '@unknown ' } });

    expect(screen.getByText(/Agent "@unknown" inconnu/)).toBeInTheDocument();
    expect(mockOnSelectAgent).not.toHaveBeenCalled();
  });
});
