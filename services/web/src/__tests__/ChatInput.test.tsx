import { render, screen, fireEvent } from '@testing-library/react';
import { ChatInput } from '@/components/chat/ChatInput';

describe('ChatInput', () => {
  const mockOnSend = jest.fn();

  beforeEach(() => {
    mockOnSend.mockClear();
  });

  it('renders input and button', () => {
    render(<ChatInput onSend={mockOnSend} />);

    expect(screen.getByPlaceholderText('Type your message...')).toBeInTheDocument();
    expect(screen.getByRole('button')).toBeInTheDocument();
  });

  it('calls onSend when clicking send button with valid input', () => {
    render(<ChatInput onSend={mockOnSend} />);

    const input = screen.getByPlaceholderText('Type your message...');
    fireEvent.change(input, { target: { value: 'Hello' } });
    fireEvent.click(screen.getByRole('button'));

    expect(mockOnSend).toHaveBeenCalledWith('Hello');
  });

  it('clears input after sending', () => {
    render(<ChatInput onSend={mockOnSend} />);

    const input = screen.getByPlaceholderText('Type your message...') as HTMLInputElement;
    fireEvent.change(input, { target: { value: 'Hello' } });
    fireEvent.click(screen.getByRole('button'));

    expect(input.value).toBe('');
  });

  it('does not send empty messages', () => {
    render(<ChatInput onSend={mockOnSend} />);

    fireEvent.click(screen.getByRole('button'));

    expect(mockOnSend).not.toHaveBeenCalled();
  });

  it('does not send whitespace-only messages', () => {
    render(<ChatInput onSend={mockOnSend} />);

    const input = screen.getByPlaceholderText('Type your message...');
    fireEvent.change(input, { target: { value: '   ' } });
    fireEvent.click(screen.getByRole('button'));

    expect(mockOnSend).not.toHaveBeenCalled();
  });

  it('sends on Enter key press', () => {
    render(<ChatInput onSend={mockOnSend} />);

    const input = screen.getByPlaceholderText('Type your message...');
    fireEvent.change(input, { target: { value: 'Hello' } });
    fireEvent.keyDown(input, { key: 'Enter' });

    expect(mockOnSend).toHaveBeenCalledWith('Hello');
  });

  it('disables input when disabled prop is true', () => {
    render(<ChatInput onSend={mockOnSend} disabled />);

    expect(screen.getByPlaceholderText('Type your message...')).toBeDisabled();
    expect(screen.getByRole('button')).toBeDisabled();
  });
});
